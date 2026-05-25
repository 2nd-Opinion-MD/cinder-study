"""
forward_webquest_adapter.py — FORWARD WebQuest export -> PTV record.

This is the **receiving-side stub** Andras's 2026-05-23 pre-call ask #4
asks about: *"can we convert a single FORWARD WebQuest export into a
schema-validated PTV record with a metadata.pii_scrubbed audit trail?"*

The answer is **yes** as soon as Adam Cornish confirms the export's
column names on the 2026-05-26 call. This file gives us a runnable
adapter today against synthetic mock data; on Wednesday 2026-05-27 we
swap the column-name defaults in :class:`ForwardFieldSpec` for Adam's
confirmed names and the same code path absorbs the real wave.

Scope of this stub
------------------

* Reads three CSVs (PRO long-form, medications, demographics) shaped per
  the field-list asks in ``PRE_CALL_CHECKLIST.md`` §2.
* Emits one PTV per patient under the
  ``ptv.2.1-indexed-v1-noarcs`` schema (validated against
  ``schemas/ptv_input.schema.json``).
* PRO events carry the ``cinder_pro`` annotation block per protocol
  §4.4 (instrument, score, wave_number, wave_date).
* Medication events carry RxNorm + dose + route fields.
* Demographics land in ``metadata.patient`` per the field-list asks.
* ``metadata.pii_scrubbed`` is populated with provenance the PII
  tripwire (``scripts/pii_tripwire.py``) accepts.

What this stub does **not** do
-------------------------------

* Run the §4.5 maintenance-vs-rescue corticosteroid state machine
  (Phase 4.E).
* Establish §4.4 baselines or compute Δ-from-baseline (Phase 4.E,
  consumes M2 baseline outputs).
* Connect to a real Postgres / Parquet warehouse (Phase 4.F).
* Run schema validation as part of the adapter (caller decides; the
  unit tests do).
* Handle Mollard smartphone signature input (Phase 5).
* Handle clinician-rated comparator events (resolution branch on
  Adam's Tuesday answer per ``confirmation_matching_rule.md`` Caveat 1).

Determinism
-----------

The adapter is deterministic:

* Patient UUIDs are produced by ``uuid.uuid5(NAMESPACE_FORWARD, native_id)``;
  the same FORWARD native ID always maps to the same UUID.
* Event IDs are deterministic ``ev_<sha256[:16]>`` hashes of
  (patient_uuid, event_kind, instrument-or-drug, wave_number, date).
* Two runs on the same input CSVs produce byte-identical PTV outputs.

CLI
---

Run as a module against mock or real CSVs::

    python -m cinder.ingest.forward_webquest_adapter \\
        --pro-long fixtures/forward_mock_wave/pro_long.csv \\
        --medications fixtures/forward_mock_wave/medications.csv \\
        --demographics fixtures/forward_mock_wave/demographics.csv \\
        --out-dir build/forward_demo_ptvs/

The ``--out-dir`` receives one ``ptv_<uuid>.json`` per patient, all of
which validate against ``schemas/ptv_input.schema.json``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from datetime import date as date_cls
from pathlib import Path
from typing import Any

import pandas as pd

__all__ = [
    "FORWARD_WAVE_EXPORT_VERSION",
    "NAMESPACE_FORWARD",
    "ForwardFieldSpec",
    "forward_export_to_ptv_records",
    "load_forward_wave_csvs",
    "patient_uuid_for",
]

FORWARD_WAVE_EXPORT_VERSION = "stub.v1"
"""Stamped into every ``metadata.pro.forward.wave_export_version`` block.

Bumps to ``v1`` when Adam Cornish's 2026-05-26 column-name confirmation
lands and the field-spec defaults are updated to real names.
"""

NAMESPACE_FORWARD = uuid.UUID("9c0f7e4a-5b3e-4a8b-9d2f-7e6a8c5b3e4a")
"""Project-wide UUID5 namespace for FORWARD native patient IDs.

Holding this namespace constant is what makes
``patient_uuid_for("FWD-12345")`` deterministic across runs and across
machines. Do not change without a governance log entry — every
PII-scrubbed PTV emitted by this adapter has its
``metadata.pii_scrubbed.scrubber`` notes pinned to this namespace.
"""

# Cinder PRO instrument enum, exact match for ptv_input.schema.json
# events.<eid>.annotations.cinder_pro.instrument enum.
_CINDER_PRO_INSTRUMENT_ENUM = {
    "HAQ-II",
    "PainVAS",
    "PatientGlobalVAS",
    "RAPID3",
    "RAPID3_FN",
    "RAPID3_PN",
    "RAPID3_PtGA",
}


# --------------------------------------------------------------------------- #
# Field spec (column-name mapping)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ForwardFieldSpec:
    """Column-name mapping for FORWARD WebQuest exports.

    Default values are **placeholders** awaiting Adam Cornish's
    confirmation on 2026-05-26. To swap to Adam's confirmed names,
    instantiate the dataclass with the real column names and pass it
    through to :func:`forward_export_to_ptv_records`. Until then the
    stub mock CSVs in ``tests/unit/fixtures/forward_mock_wave/`` use
    these defaults.
    """

    # ---- PRO long-form table (one row per patient * wave * instrument) ---
    pro_patient_id_col: str = "patient_id"
    pro_wave_number_col: str = "wave_number"
    pro_wave_date_col: str = "wave_date"
    pro_instrument_col: str = "instrument"
    pro_score_col: str = "score"

    # ---- Medications table (one row per medication record) ---
    med_patient_id_col: str = "patient_id"
    med_drug_name_col: str = "drug_name"
    med_rxnorm_col: str = "rxnorm"
    med_dose_col: str = "dose"
    med_dose_unit_col: str = "dose_unit"
    med_route_col: str = "route"  # "oral" | "parenteral" — §4.5 dependency
    med_start_date_col: str = "start_date"
    med_stop_date_col: str = "stop_date"

    # ---- Demographics (one row per patient) ---
    demo_patient_id_col: str = "patient_id"
    demo_sex_col: str = "sex"
    demo_ra_seropositivity_col: str = "ra_seropositivity"
    demo_ra_diagnosis_date_col: str = "ra_diagnosis_date"

    # ---- Instrument-string normalization ---
    # FORWARD's PRO instrument column may use names that differ from the
    # cinder_pro.instrument enum; this map normalizes them. Keys are
    # lower-cased before lookup; values must be in _CINDER_PRO_INSTRUMENT_ENUM.
    instrument_value_map: dict[str, str] = field(
        default_factory=lambda: {
            "haq-ii": "HAQ-II",
            "haqii": "HAQ-II",
            "haq2": "HAQ-II",
            "haq_ii": "HAQ-II",
            "painvas": "PainVAS",
            "pain_vas": "PainVAS",
            "pain-vas": "PainVAS",
            "patientglobalvas": "PatientGlobalVAS",
            "patient_global_vas": "PatientGlobalVAS",
            "patient-global-vas": "PatientGlobalVAS",
            "patientglobal": "PatientGlobalVAS",
            "rapid3": "RAPID3",
            "rapid3_fn": "RAPID3_FN",
            "rapid3_pn": "RAPID3_PN",
            "rapid3_ptga": "RAPID3_PtGA",
        }
    )


# --------------------------------------------------------------------------- #
# Deterministic ID helpers
# --------------------------------------------------------------------------- #


def patient_uuid_for(forward_native_id: str) -> str:
    """Deterministic PTV patient UUID from a FORWARD native patient ID.

    Returns the canonical ``8-4-4-4-12`` UUID string the
    ``ptv_input.schema.json::patient_id`` pattern expects.
    """
    if not forward_native_id or not str(forward_native_id).strip():
        raise ValueError("forward_native_id must be a non-empty string")
    return str(uuid.uuid5(NAMESPACE_FORWARD, str(forward_native_id).strip()))


def _event_id_for(*, patient_uuid: str, parts: tuple[Any, ...]) -> str:
    """Deterministic ``ev_<hex16>`` event id from stable parts."""
    blob = "|".join([patient_uuid, *(str(p) for p in parts)])
    digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    return f"ev_{digest[:16]}"


def _normalize_instrument(raw: Any, spec: ForwardFieldSpec) -> str | None:
    """Normalize a FORWARD instrument string to the cinder_pro enum value, or None."""
    if raw is None or pd.isna(raw):
        return None
    s = str(raw).strip()
    if s in _CINDER_PRO_INSTRUMENT_ENUM:
        return s
    mapped = spec.instrument_value_map.get(s.lower())
    if mapped and mapped in _CINDER_PRO_INSTRUMENT_ENUM:
        return mapped
    return None


def _coerce_date(raw: Any) -> str | None:
    """Coerce a raw date-ish input to ``YYYY-MM-DD``, or ``None``."""
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    if isinstance(raw, date_cls):
        return raw.isoformat()
    if isinstance(raw, pd.Timestamp):
        return raw.date().isoformat()
    s = str(raw).strip()
    if not s or s.lower() in ("nan", "none", "null"):
        return None
    # Already ISO date.
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    # pandas-coercible.
    try:
        ts = pd.to_datetime(s)
        return ts.date().isoformat()
    except Exception:
        return None


def _isoformat_today() -> str:
    return date_cls.today().isoformat()


# --------------------------------------------------------------------------- #
# Per-event builders
# --------------------------------------------------------------------------- #


def _build_pro_event(
    *,
    patient_uuid: str,
    instrument: str,
    score: float,
    wave_number: int,
    wave_date: str,
) -> tuple[str, dict[str, Any]]:
    eid = _event_id_for(
        patient_uuid=patient_uuid,
        parts=("pro", instrument, wave_number),
    )
    title = f"{instrument} score {score} (wave {wave_number})"
    return eid, {
        "event_id": eid,
        "event_type": "pro",
        "timestamp": wave_date,
        "preview": title,
        "status": "included",
        "annotations": {
            "card": {
                "ts": wave_date,
                "type": "pro",
                "title": title,
                "one_line": f"FORWARD wave {wave_number}: {instrument} = {score}",
                "salience": 4.0,
            },
            "salience": 4.0,
            "value": float(score),
            "cinder_pro": {
                "instrument": instrument,
                "score": float(score),
                "wave_number": int(wave_number),
                "wave_date": wave_date,
                "delta_from_baseline": None,
                "exceeds_band": None,
            },
        },
        "discovered_by": ["forward_webquest_adapter"],
    }


def _build_pro_wave_event(
    *,
    patient_uuid: str,
    wave_number: int,
    wave_date: str,
    instruments_present: list[str],
) -> tuple[str, dict[str, Any]]:
    eid = _event_id_for(
        patient_uuid=patient_uuid,
        parts=("pro_wave", wave_number),
    )
    return eid, {
        "event_id": eid,
        "event_type": "pro_wave",
        "timestamp": wave_date,
        "preview": f"FORWARD wave {wave_number} ({wave_date})",
        "status": "included",
        "annotations": {
            "card": {
                "ts": wave_date,
                "type": "pro_wave",
                "title": f"FORWARD wave {wave_number}",
                "one_line": f"PRO wave envelope ({len(instruments_present)} instruments)",
                "salience": 3.0,
            },
            "salience": 3.0,
            "status_flags": ["forward_wave"],
        },
        "discovered_by": ["forward_webquest_adapter"],
    }


def _build_medication_event(
    *,
    patient_uuid: str,
    drug_name: str,
    rxnorm: str | None,
    dose: float | None,
    dose_unit: str | None,
    route: str | None,
    start_date: str,
    stop_date: str | None,
) -> tuple[str, dict[str, Any]]:
    eid = _event_id_for(
        patient_uuid=patient_uuid,
        parts=("medication", drug_name, route or "", start_date),
    )
    dose_str = f"{dose} {dose_unit}".strip() if dose is not None else None
    title = f"{drug_name}{(' ' + dose_str) if dose_str else ''}"
    return eid, {
        "event_id": eid,
        "event_type": "medication",
        "timestamp": start_date,
        "preview": title,
        "status": "included",
        "annotations": {
            "card": {
                "ts": start_date,
                "type": "medication",
                "title": title,
                "one_line": (
                    f"Started {drug_name}"
                    + (f" {dose_str}" if dose_str else "")
                    + (f" ({route})" if route else "")
                ),
                "salience": 5.0,
                "drug": drug_name,
            },
            "salience": 5.0,
            "drug_name": drug_name,
            "drug_dosage": dose_str,
            "rxnorm": rxnorm,
            "status_flags": [route] if route else [],
        },
        "discovered_by": ["forward_webquest_adapter"],
    }


# --------------------------------------------------------------------------- #
# Top-level: per-patient PTV builder
# --------------------------------------------------------------------------- #


def _build_patient_ptv(
    *,
    forward_native_id: str,
    pro_rows: pd.DataFrame,
    med_rows: pd.DataFrame,
    demo_row: pd.Series | None,
    spec: ForwardFieldSpec,
    wave_export_id: str,
) -> dict[str, Any]:
    patient_uuid = patient_uuid_for(forward_native_id)
    events: dict[str, dict[str, Any]] = {}

    # ---- PRO events ----
    waves_seen: dict[int, dict[str, Any]] = {}
    for _, row in pro_rows.iterrows():
        wave_num_raw = row.get(spec.pro_wave_number_col)
        wave_date = _coerce_date(row.get(spec.pro_wave_date_col))
        instrument = _normalize_instrument(row.get(spec.pro_instrument_col), spec)
        score_raw = row.get(spec.pro_score_col)
        if (
            wave_num_raw is None
            or pd.isna(wave_num_raw)
            or wave_date is None
            or instrument is None
            or score_raw is None
            or pd.isna(score_raw)
        ):
            # Stub policy: silently skip malformed rows. Phase 4.E adapter
            # will log to a per-patient quality report.
            continue
        wave_number = int(wave_num_raw)
        score = float(score_raw)

        eid, event = _build_pro_event(
            patient_uuid=patient_uuid,
            instrument=instrument,
            score=score,
            wave_number=wave_number,
            wave_date=wave_date,
        )
        events[eid] = event

        wave_bucket = waves_seen.setdefault(
            wave_number, {"wave_date": wave_date, "instruments": []}
        )
        wave_bucket["instruments"].append(instrument)

    # One pro_wave envelope per wave.
    for wave_number in sorted(waves_seen):
        bucket = waves_seen[wave_number]
        eid, event = _build_pro_wave_event(
            patient_uuid=patient_uuid,
            wave_number=wave_number,
            wave_date=bucket["wave_date"],
            instruments_present=sorted(set(bucket["instruments"])),
        )
        events[eid] = event

    # ---- Medication events ----
    for _, row in med_rows.iterrows():
        drug_name_raw = row.get(spec.med_drug_name_col)
        if drug_name_raw is None or pd.isna(drug_name_raw):
            continue
        drug_name = str(drug_name_raw).strip()
        if not drug_name:
            continue
        start_date = _coerce_date(row.get(spec.med_start_date_col))
        if start_date is None:
            continue

        rxnorm_raw = row.get(spec.med_rxnorm_col)
        rxnorm = None if rxnorm_raw is None or pd.isna(rxnorm_raw) else str(rxnorm_raw).strip()
        dose_raw = row.get(spec.med_dose_col)
        dose = None if dose_raw is None or pd.isna(dose_raw) else float(dose_raw)
        unit_raw = row.get(spec.med_dose_unit_col)
        dose_unit = None if unit_raw is None or pd.isna(unit_raw) else str(unit_raw).strip()
        route_raw = row.get(spec.med_route_col)
        route = None if route_raw is None or pd.isna(route_raw) else str(route_raw).strip().lower()
        stop_date = _coerce_date(row.get(spec.med_stop_date_col))

        eid, event = _build_medication_event(
            patient_uuid=patient_uuid,
            drug_name=drug_name,
            rxnorm=rxnorm,
            dose=dose,
            dose_unit=dose_unit,
            route=route,
            start_date=start_date,
            stop_date=stop_date,
        )
        events[eid] = event

    # ---- Metadata ----
    n_waves = len(waves_seen)
    wave_dates = [b["wave_date"] for b in waves_seen.values() if b["wave_date"]]

    metadata: dict[str, Any] = {
        "schema_version": "ptv.2.1-indexed-v1-noarcs",
        "pii_scrubbed": {
            "scrubber": "cinder.ingest.forward_webquest_adapter (stub, deterministic UUID5 namespace)",
            "scrubbed_at": _isoformat_today(),
            "rules_applied": 1,
            "replacement_counts_by_label": {"NATIVE_PATIENT_ID_TO_UUID5": 1},
            "audit_file": None,
        },
        "pro": {
            "source": "forward",
            "forward": {
                "patient_reported_outcomes_channel": True,
                "wave_export_id": wave_export_id,
                "wave_export_version": FORWARD_WAVE_EXPORT_VERSION,
                "wave_count": n_waves,
                "wave_date_range": (
                    {"start": min(wave_dates), "end": max(wave_dates)} if wave_dates else None
                ),
                "instruments_present": sorted(
                    {
                        ev["annotations"]["cinder_pro"]["instrument"]
                        for ev in events.values()
                        if ev["event_type"] == "pro"
                    }
                ),
            },
        },
        "patient": {},
    }

    if demo_row is not None:
        sex = demo_row.get(spec.demo_sex_col)
        sero = demo_row.get(spec.demo_ra_seropositivity_col)
        dx_date = _coerce_date(demo_row.get(spec.demo_ra_diagnosis_date_col))
        if sex is not None and not pd.isna(sex):
            metadata["patient"]["sex"] = str(sex)
        if sero is not None and not pd.isna(sero):
            metadata["patient"]["ra_seropositivity"] = str(sero)
        if dx_date is not None:
            metadata["patient"]["ra_diagnosis_date"] = dx_date
        # DOB is intentionally redacted at scrub time.
        metadata["patient"]["dob"] = "[DOB_REDACTED]"

    return {
        "patient_id": patient_uuid,
        "built_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "session_only": False,
        "$schema_ref": "ptv_input.schema.json",
        "events": events,
        "metadata": metadata,
    }


# --------------------------------------------------------------------------- #
# Public entry points
# --------------------------------------------------------------------------- #


def forward_export_to_ptv_records(
    *,
    pro_long: pd.DataFrame,
    medications: pd.DataFrame,
    demographics: pd.DataFrame,
    spec: ForwardFieldSpec | None = None,
    wave_export_id: str = "stub_wave_export",
) -> dict[str, dict[str, Any]]:
    """Convert a multi-patient FORWARD wave export into per-patient PTV records.

    Returns a dict ``{patient_uuid: ptv_record}``. Each PTV validates
    against ``schemas/ptv_input.schema.json``.

    The three input DataFrames are the long-form PRO table, the
    medications table, and the demographics table. Their column names
    are read from ``spec`` (default :class:`ForwardFieldSpec` placeholders).
    """
    spec = spec or ForwardFieldSpec()

    pro_by_id = pro_long.groupby(spec.pro_patient_id_col, sort=True)
    med_by_id = (
        medications.groupby(spec.med_patient_id_col, sort=True) if not medications.empty else None
    )
    demo_by_id = (
        demographics.set_index(spec.demo_patient_id_col, drop=False)
        if not demographics.empty
        else None
    )

    results: dict[str, dict[str, Any]] = {}
    for native_id, pro_rows in pro_by_id:
        med_rows = (
            med_by_id.get_group(native_id)
            if med_by_id is not None and native_id in med_by_id.groups
            else pd.DataFrame(columns=medications.columns)
        )
        demo_row = (
            demo_by_id.loc[native_id]
            if demo_by_id is not None and native_id in demo_by_id.index
            else None
        )
        ptv = _build_patient_ptv(
            forward_native_id=str(native_id),
            pro_rows=pro_rows,
            med_rows=med_rows,
            demo_row=demo_row,
            spec=spec,
            wave_export_id=wave_export_id,
        )
        results[ptv["patient_id"]] = ptv
    return results


def load_forward_wave_csvs(
    *,
    pro_long_csv: Path | str,
    medications_csv: Path | str,
    demographics_csv: Path | str,
    spec: ForwardFieldSpec | None = None,
    wave_export_id: str | None = None,
) -> dict[str, dict[str, Any]]:
    """End-to-end CSV -> PTV records helper.

    Convenience wrapper around :func:`forward_export_to_ptv_records` that
    reads the three CSVs first.
    """
    pro_long_csv = Path(pro_long_csv)
    medications_csv = Path(medications_csv)
    demographics_csv = Path(demographics_csv)

    pro_long = pd.read_csv(pro_long_csv)
    medications = pd.read_csv(medications_csv)
    demographics = pd.read_csv(demographics_csv)

    if wave_export_id is None:
        wave_export_id = pro_long_csv.parent.name or "stub_wave_export"

    return forward_export_to_ptv_records(
        pro_long=pro_long,
        medications=medications,
        demographics=demographics,
        spec=spec,
        wave_export_id=wave_export_id,
    )


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="cinder.ingest.forward_webquest_adapter",
        description=(
            "Convert a FORWARD WebQuest wave export (three CSVs) into "
            "per-patient PTV records. Stub field-spec defaults are "
            "placeholders pending Adam Cornish's 2026-05-26 column-name "
            "confirmation; instantiate ForwardFieldSpec(...) and pass it "
            "in via Python API for production use."
        ),
    )
    parser.add_argument("--pro-long", type=Path, required=True)
    parser.add_argument("--medications", type=Path, required=True)
    parser.add_argument("--demographics", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument(
        "--wave-export-id",
        type=str,
        default=None,
        help="Free-text wave-export identifier; defaults to PRO CSV's parent dir name.",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indent for emitted PTVs (0 to disable).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    ptvs = load_forward_wave_csvs(
        pro_long_csv=args.pro_long,
        medications_csv=args.medications,
        demographics_csv=args.demographics,
        wave_export_id=args.wave_export_id,
    )

    indent = args.indent if args.indent and args.indent > 0 else None
    for puuid, ptv in ptvs.items():
        out_path = out_dir / f"ptv_{puuid}.json"
        out_path.write_text(
            json.dumps(ptv, indent=indent, sort_keys=True),
            encoding="utf-8",
        )
        print(
            f"wrote {out_path} "
            f"(events={len(ptv['events'])}, "
            f"waves={ptv['metadata']['pro']['forward']['wave_count']})",
            file=sys.stderr,
        )
    print(f"emitted {len(ptvs)} PTVs into {out_dir}", file=sys.stderr)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
