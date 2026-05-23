# §13.5 Confirmation — Repository scaffold + open schemas published

Status: **in progress** (this commit lands the scaffold; CI green-light pending first push).

## Question

> §13.5 — Repository scaffold + open schemas published. Is `cinder-study` set up with the canonical directory layout, the four published JSON Schemas, the open Bayesian kernel layer (vendored), CI green on Linux + Windows, pre-commit + PII tripwire active, and the LICENSE / README / pyproject in place?

## Answer

| Sub-item | State (2026-05-23 PM) | Evidence |
|---|---|---|
| Canonical directory layout per IMPLEMENTATION_PLAN.md "Repository topology" | ✅ landed this commit | `cinder/`, `analysis/`, `schemas/`, `fixtures/`, `governance/`, `docs/`, `tests/`, `scripts/`, `data_request/`, `notebooks/` |
| Four published JSON Schemas | ✅ landed | `schemas/uc_annotation.schema.json`, `schemas/flare_event.schema.json`, `schemas/escalation_event.schema.json`, `schemas/derivation_chain.schema.json` |
| PTV input contract schema | 🔶 deferred to Phase 1 | Will be added when `cinder.bayes` vendoring lands |
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
2. **PTV input contract schema** — deferred to Phase 1 alongside the vendored `cinder.bayes` package; not strictly required for §13.5 since the four published schemas listed in §10 are landed.
3. **Andras Option A vs Option B vendoring decision** — still open. This memo assumes Option A (vendor source) per the IMPLEMENTATION_PLAN.md default.

## Approval

| Role | Name | Date | Commit |
|---|---|---|---|
| Implementer | Dylan McCapes | 2026-05-23 | `<FILL>` |
| Senior approver | Andras Hangyal | pending | — |
