# §13.5 Confirmation — Repository scaffold + open schemas published

Status: **in progress** (this commit lands the scaffold; CI green-light pending first push).

## Question

> §13.5 — Repository scaffold + open schemas published. Is `cinder-study` set up with the canonical directory layout, the four published JSON Schemas, the open Bayesian kernel layer (vendored), CI green on Linux + Windows, pre-commit + PII tripwire active, and the LICENSE / README / pyproject in place?

## Answer

| Sub-item | State (2026-05-23 PM) | Evidence |
|---|---|---|
| Canonical directory layout per IMPLEMENTATION_PLAN.md "Repository topology" | ✅ landed this commit | `cinder/`, `analysis/`, `schemas/`, `fixtures/`, `governance/`, `docs/`, `tests/`, `scripts/`, `data_request/`, `notebooks/` |
| Four published JSON Schemas | ✅ landed | `schemas/uc_annotation.schema.json`, `schemas/flare_event.schema.json`, `schemas/escalation_event.schema.json`, `schemas/derivation_chain.schema.json` |
| PTV input contract schema | ✅ landed (2026-05-23 follow-up) | `schemas/ptv_input.schema.json`. The 632-event reference fixture validates against it. 17 regression tests in `tests/unit/test_ptv_input_schema.py` cover positive (real fixture, minimal PTV, FORWARD PRO event with cinder_pro block) and negative (missing pii_scrubbed, missing card, malformed UUID, invalid timestamp, invalid PRO instrument, negative salience, etc.) cases. |
| Vendored Bayesian kernel layer (`cinder.bayes`) | 🔶 placeholder package only — vendoring scheduled for Phase 4 | `cinder/bayes/__init__.py` placeholder; vendoring source `2ndOpinionMD-MVP@00eaa9eb` |
| `pyproject.toml` with deps + dev + sampling + notebook extras | ✅ landed | `pyproject.toml` |
| `.gitignore` with PII deny patterns | ✅ landed | `.gitignore` |
| `LICENSE` (MIT) with §10 IP scope note | ✅ landed | `LICENSE` |
| `README.md` with §10 IP posture + replicability commitment | ✅ landed | `README.md` |
| Pre-commit config (ruff format/check, mypy, jsonschema, PII tripwire) | ✅ landed | `.pre-commit-config.yaml` |
| GitHub Actions CI on Linux + Windows × Python 3.11 + 3.12 | ✅ landed | `.github/workflows/ci.yml` |
| `scripts/validate_schemas.py` | ✅ landed | `scripts/validate_schemas.py` |
| `scripts/pii_tripwire.py` | ✅ landed | `scripts/pii_tripwire.py` |
| Real-EHR 632-event reference fixture (PII-scrubbed, audited, manifested) | ✅ landed | `fixtures/real_ehr_632event/ptv_real_ehr_632event_v1_noarcs_scrubbed.json` |
| Phase 0 smoke tests (package import + schema self-validation + PII tripwire behavior) | ✅ landed | `tests/unit/test_scaffold.py`, `tests/unit/test_pii_tripwire.py` |
| Governance scaffolding (pre-registration log + PII scrub audit policy) | ✅ landed | `governance/pre_registration_log.md`, `governance/pii_scrub_audit.md` |
| Data-request directory with FORWARD/UNMC pre-call positioning | ✅ landed | `data_request/README.md` |

## Evidence

- This commit hash (filled at commit time): `<FILL>`
- Local pytest run (Phase 0 smoke): expected ✅ on first invocation post-`pip install -e ".[dev]"`
- CI green-light: pending first push to GitHub remote
- PII tripwire behavior: 7 unit tests asserting both blocks (residual tokens, missing scrub-provenance) and passes (real fixture, valid scrub-provenance, non-PTV JSON)

## Open items before §13.5 can be fully closed

1. **First green CI run** on Linux + Windows × Python 3.11 + 3.12 — requires push to GitHub. Target: 2026-05-25.
2. **Vendor copy of `bayes.py` / `uc.py` / `fetch_mkg_bayes_prior` into `cinder/bayes/`** — Phase 4 work. Decision is locked (Option A, pinned at MVP commit `00eaa9eb` per IMPLEMENTATION_PLAN.md "Decisions locked" table). Code copy itself is the next forward step after PTV input contract schema (which landed 2026-05-23) but does not block §13.5 closure since §13.5 is the scaffold-level checkpoint.

## Approval

| Role | Name | Date | Commit |
|---|---|---|---|
| Implementer | Dylan McCapes | 2026-05-23 | `<FILL>` |
| Senior approver | Andras Hangyal | pending | — |
