# `cinder.bayes` — vendoring provenance

## Source

| Field | Value |
|---|---|
| Source repository | `2ndOpinionMD-MVP` (private 2OPMD repo) |
| Source commit | `00eaa9eb1e3511a354c0559f90b4db60e94aea09` |
| Source commit short SHA | `00eaa9eb` |
| Source commit subject | *Add Bayesian UC reasoning + demo-mode verbose logging* |
| Source commit date | 2026-04-23 |
| Vendoring date | 2026-05-25 |
| Vendoring decision | Option A — pinned source-code copy (per `IMPLEMENTATION_PLAN.md` "Decisions locked", 2026-05-23) |
| Vendoring rationale | `docs/confirmation_software.md` §13.4 + `IMPLEMENTATION_PLAN.md` Phase 4.A |

## File map (source → destination)

| Source path (at `00eaa9eb`) | Destination path (in cinder-study) | Edits made |
|---|---|---|
| `server/eoh/uc.py` | `cinder/bayes/uc.py` | Vendoring banner only; no logic edits. |
| `server/ptv_toolkit/graph.py` | `cinder/bayes/graph.py` | Vendoring banner only; no logic edits. |
| `server/ptv_toolkit/bayes.py` | `cinder/bayes/kernels.py` | (a) renamed file to avoid shadowing the `cinder.bayes` package; (b) rewrote `from server.eoh.uc import ...` → `from .uc import ...`; (c) vendoring banner. No logic edits. |
| `server/scripts/mkg_retrieval_harness.py::fetch_mkg_bayes_prior` (lines 480–581) | `cinder/bayes/mkg_retrieval.py` | (a) extracted the single function from a much-larger MVP harness script; (b) DSN env-var lookup constrained to CINDER-specific names (`CINDER_MKG_DSN`, `MKG_DSN`, `DATABASE_URL`); MVP-internal vars (`SYNC_DATABASE_URL`, `POSTGRES_URL`) deliberately not consulted; (c) `_log("⚠️", ...)` warning replaced with stdlib `logging.getLogger("cinder.bayes.mkg")` warning. Function signature, return semantics, and SQL preserved exactly. |

## Re-vendoring procedure

If a future protocol amendment changes the locked commit pin, re-vendor with:

```powershell
# Windows PowerShell, from cinder-study root
$pin = "<new-pin>"
$mvp = "..\2ndOpinionMD-MVP"
cd $mvp
cmd /c "git show ${pin}:server/eoh/uc.py > ..\cinder-study\cinder\bayes\uc.py"
cmd /c "git show ${pin}:server/ptv_toolkit/graph.py > ..\cinder-study\cinder\bayes\graph.py"
cmd /c "git show ${pin}:server/ptv_toolkit/bayes.py > ..\cinder-study\cinder\bayes\kernels.py"
cd ..\cinder-study
# Reapply: kernels.py header banner + import rewrite
# Reapply: uc.py header banner
# Reapply: graph.py header banner
# Reapply mkg_retrieval.py changes manually (the MVP source script is large
# and changes around the function are routine; do not blanket-replace).
```

After re-vendoring, run the full test suite (`pytest -q`) and confirm
that the regression tests in `tests/regression/test_bayes_harness_*.py` and
`tests/regression/test_bayes_kernels_unit.py` still pass. Update this file's
"Source commit" row, the `VENDORED_AT_COMMIT` constant in `cinder/bayes/__init__.py`,
and the `IMPLEMENTATION_PLAN.md` "Decisions locked" table to record the
new pin in the same commit.

## EoH module handshake policy

The MVP's Bayesian kernel layer is, at the kernel level, **self-contained**.
It does not embed M62 OM↔CGH propositionality checks, M9 reflex-suppression
hooks, or other EoH module handshakes. Those handshakes live in higher-level
2OPMD MVP code (the agent orchestration layer in `server/ptv_toolkit/agent.py`,
`server/ptv_toolkit/handoff.py`, and `server/ptv_toolkit/registry.py`) which
is **not** vendored.

CINDER calls `bayesian_update_uc` directly. The protocol §4.7 governance
invariants (propositionality, suppression-first, no-promotion-without-provenance,
refusal supremacy) are enforced at the CINDER analysis-orchestration layer
(`analysis/detection/`, Phase 4.D and Phase 6) — they are not the kernel's
responsibility. The kernel's contract is: produce a deterministic posterior
UC from a deterministic input (PTV graph + hypothesis_id + optional prior +
optional likelihood_spec). The orchestration layer decides whether to publish,
suppress, or refuse based on the UC's `confidence`, `band_90`, and `basis`.

This design keeps the pre-registered analytic core (the kernel) frozen at
`00eaa9eb` while letting the CINDER-specific governance layer evolve under
its own version stamp.

## Weak-prior fallback policy

Until FORWARD-derived priors land in Phase 6, `fetch_mkg_bayes_prior` returns
`None` for every call (no DB env var set, or the DB / table doesn't exist),
and the kernel falls back to the weak priors documented in
`DEFAULT_HYPOTHESIS_PRIORS` (`kernels.py`):

| Hypothesis | Weak prior | Mean |
|---|---|---|
| `flare_30d` | Beta(2.0, 8.0) | 0.20 |
| `progression_3mo` | Beta(1.5, 8.5) | 0.15 |
| `taper_safety` | Beta(6.0, 4.0) | 0.60 |

These are the priors the §6.1 sample-size simulation runs against per protocol
§4.8 (and per Aetherion Major 5 review note: priors are weakly informative,
anchored on Mollard 2026 point estimates expanded by 50 percent to allow data
dominance). Switching to MKG-informed priors post-Phase-6 is a configuration
change (set `CINDER_MKG_DSN`, populate `public.mkg_bayes_priors`), not a
code change.

## What is NOT vendored

The following MVP files were touched by `00eaa9eb` but are deliberately
**not** vendored, because they belong to the MVP's agent orchestration layer
or its production demo wiring, not to the deterministic kernel:

- `server/ptv_toolkit/__init__.py` (exports for the MVP toolkit, not relevant to CINDER)
- `server/ptv_toolkit/agent.py` (chatbot agent loop)
- `server/ptv_toolkit/handoff.py` (handoff schema between probe and gap agents)
- `server/ptv_toolkit/registry.py` (tool registry for the chatbot)
- `server/ptv_toolkit/tools.py` (tool dispatch)
- `server/scripts/forward_probe_gap_report_chatbot.py` (the chatbot itself)
- `server/scripts/mkg_retrieval_harness.py` (only the `fetch_mkg_bayes_prior` function is vendored from this file)

The harness JSONs (`forward_probe_gap_session_harness_questions.json` and
`ptv_toolkit_questions.json`) are vendored as test inputs in
`tests/regression/`, not as runtime code — see those test files'
docstrings for the question-to-assertion mapping.

## Verification

The vendored kernel is verified by the regression tests in
`tests/regression/test_bayes_harness_q11_q13.py` and
`tests/regression/test_bayes_harness_h11_h13.py`, which port the MVP's
q11/q12/q13 + h11/h12/h13 conversational test questions into pytest
assertions against the 632-event real-EHR fixture in
`fixtures/real_ehr_632event/`. The unit tests for the closed-form updates
themselves are in `tests/regression/test_bayes_kernels_unit.py`.

All tests are deterministic (no random seeds; the kernel is fully closed-form)
and run on the CI matrix (Ubuntu + Windows × Python 3.11 + 3.12).
