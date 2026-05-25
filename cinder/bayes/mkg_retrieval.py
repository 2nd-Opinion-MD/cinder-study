"""
mkg_retrieval.py — population-prior lookup for the Bayesian kernel layer.

CINDER vendoring note. The function ``fetch_mkg_bayes_prior`` is vendored
from ``2ndOpinionMD-MVP/server/scripts/mkg_retrieval_harness.py`` at locked
commit 00eaa9eb. The function signature and return semantics
(deterministic ``None`` on any failure, dict with ``family`` / prior
parameters / ``source: "mkg"`` provenance on success) are preserved
exactly.

The two CINDER-specific changes from the MVP version are:

  1. Database connection string env-var lookup uses CINDER-specific names
     (``CINDER_MKG_DSN``, then ``MKG_DSN``) before falling back to the
     generic Postgres env vars (``DATABASE_URL``, etc.). The 2OPMD MVP
     production DSN env vars (``SYNC_DATABASE_URL``, ``POSTGRES_URL``)
     are deliberately NOT consulted — CINDER must not silently connect to
     the MVP demo Postgres if the script happens to run on a workstation
     that has those vars set.
  2. The MVP's ``_log("⚠️", ...)`` warning emitter is replaced with a
     stdlib ``logging.getLogger("cinder.bayes.mkg")`` warning. This keeps
     the same observable behavior (a one-line warning on DB error, then
     return ``None``) but routes it through CINDER's logging chain.

Pre-Phase-6 behavior. Until FORWARD-derived priors are computed and
populated into the ``public.mkg_bayes_priors`` sidecar table (Phase 6
work, gated on Tuesday 2026-05-26 FORWARD/UNMC field confirmations), this
function returns ``None`` for every call. The kernel layer then falls
back to the weak priors documented in ``DEFAULT_HYPOTHESIS_PRIORS``
(``kernels.py``) — Beta(2,8) for ``flare_30d``, Beta(1.5,8.5) for
``progression_3mo``, Beta(6,4) for ``taper_safety``. This is the
intended pre-data behavior; the §6.1 sample-size simulation runs against
these weak priors per protocol §4.8.

Post-Phase-6, the function will hit the MKG sidecar table (or whatever
replicator-friendly equivalent we settle on; see PROVENANCE.md) and
return informative priors. Switching is a configuration change, not a
code change.

----- Original docstring (verbatim, function-level) ---------------------

Look up a population prior for ``hypothesis_id`` in the MKG sidecar table.

``cohort_strata`` is a dict of stratum keys (``icd_family``, ``age_band``,
``sex``); only keys with non-null values are used, and lookup walks from
most-specific (all keys) to least-specific (no keys) until a row matches.

Returns a dict with ``family`` / ``alpha`` / ``beta`` / ``mu`` / ``sigma``
fields plus ``source: "mkg"`` and provenance breadcrumbs, or ``None``.

This function is **safe**: any DB error or missing table returns ``None``
so callers can fall back to weak priors deterministically.
"""

from __future__ import annotations

import json
import logging
import os
from itertools import combinations
from typing import Any

__all__ = ["MKG_PRIORS_TABLE", "fetch_mkg_bayes_prior"]

_log = logging.getLogger("cinder.bayes.mkg")

MKG_PRIORS_TABLE = "public.mkg_bayes_priors"

_CINDER_DSN_ENV_VARS = ("CINDER_MKG_DSN", "MKG_DSN", "DATABASE_URL")


def _resolve_dsn(dsn_override: str | None) -> str | None:
    """Pick a Postgres DSN from the explicit override, then CINDER env vars.

    Deliberately does NOT consult MVP-internal env vars
    (``SYNC_DATABASE_URL``, ``POSTGRES_URL``) so a workstation that runs
    both repos can't have CINDER silently grab the MVP demo DSN.
    """
    if dsn_override and dsn_override.strip():
        return dsn_override.strip()
    for var in _CINDER_DSN_ENV_VARS:
        val = os.environ.get(var)
        if val and val.strip():
            return val.strip()
    return None


def fetch_mkg_bayes_prior(
    hypothesis_id: str,
    *,
    cohort_strata: dict[str, Any] | None = None,
    dsn: str | None = None,
) -> dict[str, Any] | None:
    """Return an MKG-derived prior override dict, or ``None`` for weak fallback.

    Pre-Phase-6 the DB table does not exist; this returns ``None`` cleanly
    and the kernel falls back to ``DEFAULT_HYPOTHESIS_PRIORS``.
    """
    if not hypothesis_id:
        return None

    try:
        import psycopg
        from psycopg.rows import dict_row
    except Exception:
        return None

    target_dsn = _resolve_dsn(dsn)
    if not target_dsn:
        return None

    strata = {k: v for k, v in (cohort_strata or {}).items() if v is not None and str(v).strip()}
    candidates: list[dict[str, Any]] = []
    keys = sorted(strata.keys())
    n = len(keys)
    for r in range(n, -1, -1):
        for combo in combinations(keys, r):
            candidates.append({k: strata[k] for k in combo})

    try:
        with (
            psycopg.connect(target_dsn, row_factory=dict_row) as conn,
            conn.cursor() as cur,
        ):
            cur.execute("SET statement_timeout = '5s';")
            cur.execute(
                "SELECT to_regclass(%s) IS NOT NULL AS exists",
                (MKG_PRIORS_TABLE,),
            )
            row0 = cur.fetchone() or {}
            if not row0.get("exists"):
                return None
            for cand in candidates:
                sql = (
                    f"SELECT family, alpha, beta, mu, sigma, sigma_obs, "
                    f"source, notes, cohort_strata, version, updated_at "
                    f"FROM {MKG_PRIORS_TABLE} "
                    f"WHERE hypothesis_id = %s AND cohort_strata = %s::jsonb "
                    f"ORDER BY updated_at DESC NULLS LAST LIMIT 1"
                )
                cur.execute(sql, (hypothesis_id, json.dumps(cand, sort_keys=True)))
                row = cur.fetchone()
                if row:
                    out = {
                        "family": str(row.get("family") or "beta"),
                        "alpha": (float(row["alpha"]) if row.get("alpha") is not None else None),
                        "beta": (float(row["beta"]) if row.get("beta") is not None else None),
                        "mu": (float(row["mu"]) if row.get("mu") is not None else None),
                        "sigma": (float(row["sigma"]) if row.get("sigma") is not None else None),
                        "sigma_obs": (
                            float(row["sigma_obs"]) if row.get("sigma_obs") is not None else None
                        ),
                        "source": str(row.get("source") or "mkg"),
                        "notes": (
                            f"MKG prior version={row.get('version')!r} "
                            f"strata={row.get('cohort_strata')!r} "
                            f"updated_at={row.get('updated_at')!r}"
                        ),
                    }
                    return {k: v for k, v in out.items() if v is not None}
    except Exception as exc:
        _log.warning("fetch_mkg_bayes_prior: %s", exc)
        return None
    return None
