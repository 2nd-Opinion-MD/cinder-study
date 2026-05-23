# CINDER

**Co-occurrence INference for Disease Escalation in Rheumatology**

A FORWARD-registry validation of the 2OPMD Flare Axiom with Uncertainty Carrier governance and patient-specific terrain modeling.

> **Status (2026-05-23).** Pre-DUA. Repository scaffold landing this week ahead of the 2026-05-26 FORWARD/UNMC working call. Protocol is at `v3.0-DRAFT`; tag goes to `v3.0-FINAL` once the §13 pre-delivery checklist closes. See [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) and [`PRE_CALL_CHECKLIST.md`](PRE_CALL_CHECKLIST.md).

---

## What this repository contains

This is the **open analysis pipeline** for the CINDER study. Per protocol §10, the repository holds:

- **Open schemas** — `flare_event`, `uc_annotation`, `derivation_chain`, `escalation_event`, plus the PTV input contract
- **Open statistical methods** — Bayesian hierarchical concordance model, frequentist mixed-effects sensitivity analysis, comparator triangulation
- **Open comparator implementations** — §4.6 1:1 matching rule, §4.6 OMERACT operationalization, Mollard 2026 smartphone signature alignment
- **Open derivation-chain output format** — §4.9 M63 GlassBox compliance trace
- **Open Bayesian kernel layer** — closed-form Beta-Bernoulli / Gamma-Poisson / Normal-Normal updates with `LikelihoodSpec` DSL (vendored from `2ndOpinionMD-MVP` commit `00eaa9eb` per `IMPLEMENTATION_PLAN.md` "Reusable foundation" section)

The proprietary EoH modules (M2 Chronic Baseline Mode, M3 Terrain Index Engine, M6 Escalation Router, M9 Reflex Suppression Core, M62 Orbit Mode ↔ Clinical Governance Handshake, M63 GlassBox Derivation Contract) are **not** in this repository. They live in 2OPMD's private package and are referenced by stable interface only.

## Replicability commitment

The reproducibility commitment is **methodological + governance-chain transparency**, not source-level module disclosure. External groups can:

1. Reproduce the validation analyses on the released event outputs by running the same statistical models on the same flareEvent records
2. Validate that all derivation chains conform to the published M63 schema
3. Inspect every prior, likelihood spec, and posterior parameter in every UC bundle (`uc.v1.bayes` schema)

For full mechanistic replication, a **blinded external re-run pathway** is available by arrangement: 2OPMD will execute the detection pipeline under third-party auditor supervision on held-out patient data, with derivation chains released for audit verification. This pathway does not require module disclosure and satisfies hostile-reviewer reproducibility requirements.

See **PROTOCOL_v3.0-FINAL §10** for the full IP table and replicability posture.

## Quickstart

```bash
git clone https://github.com/<org>/cinder-study
cd cinder-study
python -m venv .venv && . .venv/Scripts/activate  # on Windows; .venv/bin/activate on Linux/macOS
pip install -e ".[dev]"
pre-commit install
pytest -q
```

## Repository layout

See `IMPLEMENTATION_PLAN.md` "Repository topology" section for the canonical structure. Key directories:

- `cinder/bayes/` — vendored conjugate kernels + UC dataclass + MKG-prior lookup
- `analysis/` — simulation, detection, matching, concordance, Aim 2 UC analyses
- `schemas/` — published JSON Schemas
- `fixtures/` — synthetic and (PII-scrubbed) reference PTVs
- `governance/` — pre-registration log, PII-scrubbing audit description
- `docs/` — §13 confirmation memos and confirmation logs

## Authorship & governance

- **Co-first authors (equal contribution):** Andras Hangyal, PharmD (2OPMD); Dylan McCapes (2OPMD)
- **Senior author:** Kaleb Michaud, PhD (FORWARD Co-Director, UNMC)
- **DUA:** UNMC standard pathway, Option B (anonymized at source, 2OPMD LLC receiving entity)
- **HIPAA:** Waiver in place; 27-rule scrubbing pipeline applied to every PTV before any cross-machine transit; audit provenance retained in `metadata.pii_scrubbed`
- **Pre-registration:** ACR Convergence 2026 abstract (deadline 2026-06-09); v3.0-FINAL commit hash recorded in `governance/pre_registration_log.md` and the abstract supplemental field

## Citation

When citing this work pre-publication, cite the protocol commit hash:

```
CINDER Study Protocol v3.0-FINAL. 2OPMD LLC, 2026.
Repository: <repo URL>
Commit: <SHA-1 from governance/pre_registration_log.md>
```

A formal CITATION.cff lands at v3.0-FINAL tag time.

## License

Code in this repository is released under the **MIT License** (see `LICENSE`). The license covers analysis code, schemas, comparator implementations, and the vendored Bayesian kernel layer. It does **not** cover the proprietary EoH modules referenced by interface. See protocol §10 for the full IP posture.
