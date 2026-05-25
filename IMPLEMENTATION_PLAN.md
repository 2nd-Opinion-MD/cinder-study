---
title: CINDER — Implementation Plan
project: CINDER (Co-occurrence INference for Disease Escalation in Rheumatology)
owner: Dylan McCapes
companion_to: PROTOCOL_DRAFT_v3.md (§13 pre-delivery checklist)
status: PLAN — phased work breakdown for the cinder-study repository
date: 2026-05-23 (revised — adds 5/26 FORWARD/UNMC call, calendar slip acknowledged)
gating_deadlines:
  - "Dylan §13 confirmations + deliverables back to Andras: 2026-05-15 (TARGET — slipped, replaced by 5/26 call deliverables)"
  - "v3.0-FINAL tagged + committed: 2026-05-20 (GATE — slipped, in flight)"
  - "FORWARD/UNMC working call (Kaleb / Adam Cornish / Rebecca Schumacher): 2026-05-26 1 PM CDT"
  - "Kaleb preliminary delivery: 2026-05-31 (Andras-led)"
  - "ACR Convergence abstract submission: 2026-06-09 (needs frozen commit hash)"
  - "SBIR Phase I to NIAMS: 2026-09-05 (joint, non-extendable)"
stakeholders:
  - "Andras Hangyal, PharmD — 2OPMD, PI"
  - "Dylan McCapes — 2OPMD, informatics architecture (this repo's primary owner)"
  - "Kaleb Michaud, PhD — FORWARD Co-Director, UNMC; senior author"
  - "Adam Cornish — UNMC, head of IT; data delivery technical owner (new 2026-05-23)"
  - "Rebecca Schumacher — FORWARD, executive director (new 2026-05-23)"
ip_posture: §10 — EoH modules M2 / M3 / M6 / M9 / M62 / M63 are 2OPMD proprietary and live in a private package; this repository holds open inputs, outputs, statistical methods, comparator implementations, and derivation-chain schemas. Replicability commitment is methodological + governance-chain transparency, not source-level module disclosure.
terminology_map:
  - "Andras 'F2 regression harness' = IMPLEMENTATION_PLAN Phase 4 (reference implementations) + Phase 4.H (test harness)"
  - "Andras 'F4-CASE-01 / F4-CASE-04' = case-instantiations on the 632-event noarcs PTV under Phase 4.D (per-patient detection orchestration)"
  - "Andras 'noarcs synthetic exemplar regen' = Phase 4 fixture refresh on `ptv.2.1-indexed-v1-noarcs` schema"
---

# CINDER Implementation Plan

This is the phased work breakdown for everything Dylan owns in the `cinder-study` repository between handoff (2026-05-03) and SBIR submission (2026-09-05). It is structured around the §13 pre-delivery checklist as the immediate gate, then the ACR-abstract / Kaleb-preliminary / SBIR-preliminary-data milestones in sequence.

Each phase names: **inputs**, **deliverables**, **owner / collaborator touchpoints**, **acceptance criteria**, and **target window**.

> **Calendar status as of 2026-05-23.** Original §13 confirmation target (5/15) and v3.0-FINAL gate (5/20) have slipped. New near-term anchor is the **2026-05-26 FORWARD/UNMC working call** with Kaleb Michaud, Adam Cornish (UNMC IT head), and Rebecca Schumacher (FORWARD ED). See **`PRE_CALL_CHECKLIST.md`** for the call-specific deliverables, Adam-asks one-pager, and pre-call work plan. The 5/26 call now drives Phase 0 scaffold completion (this weekend) and F2 checkpoints 1+2 to green by Tuesday.

---

## Repository topology (target end-state for Phase 0)

The structure below mirrors the §13 item-5 minimum scaffold and adds the schemas / tests / governance directories the protocol implies.

```
cinder-study/
├── PROTOCOL_v3.0-FINAL.md              ← copied from handoff at v3.0-FINAL tag time
├── PROTOCOL_v3.0-FINAL.pdf             ← copied from handoff at v3.0-FINAL tag time
├── README.md                           ← what this is, who runs it, §10 IP posture
├── IMPLEMENTATION_PLAN.md              ← this document
├── LICENSE                             ← MIT for analysis code; proprietary modules excluded
├── CITATION.cff
├── pyproject.toml                      ← PyMC + ArviZ + numpy + pandas + jsonschema + pytest
├── .gitignore
├── .pre-commit-config.yaml
├── .github/
│   └── workflows/
│       └── ci.yml                      ← lint + tests + schema validation on PRs
├── cinder/
│   └── bayes/                          ← vendored from 2ndOpinionMD-MVP (Option A)
│       ├── kernels.py                  ← bayes.py: Beta-Bernoulli / Gamma-Poisson / Normal-Normal
│       ├── uc.py                       ← UncertaintyCarrier dataclass + serializers (uc.v1.bayes)
│       ├── mkg_priors.py               ← fetch_mkg_bayes_prior + weak-prior fallback
│       ├── tests/                      ← MVP regression tests + CINDER additions (c01-c04)
│       └── harness/
│           ├── ptv_toolkit_questions_cinder.json      ← q11-q13 inherited + c01-c04 CINDER additions
│           └── session_harness_questions_cinder.json  ← h11-h13 inherited + CINDER FORWARD questions
├── analysis/
│   ├── simulation/                     ← §6.1 PyMC sample-size simulation
│   │   ├── run_simulation.py
│   │   ├── inputs.yaml                 ← table from §6.1 with Dylan-confirmed values
│   │   └── results/
│   │       └── kappa_ci_width.md       ← actual posterior CI width output
│   ├── detection/                      ← §4.4 per-patient detection (uses cinder.bayes)
│   │   ├── cinder_likelihood_spec.yaml ← §4.4 MCID-anchored rules (HAQ ≥ 0.22, VAS ≥ 20, RAPID3 ≥ 3.6)
│   │   ├── detect_flare.py             ← batch driver: M2→M3→M6 → bayesian_update_uc → UC
│   │   ├── forward_priors.py           ← adapter on cinder.bayes.mkg_priors for FORWARD strata
│   │   └── tests/
│   ├── matching_rule/                  ← §4.6 reproducible 1:1 comparator matching
│   │   ├── matcher.py
│   │   ├── omeract_comparator.py       ← §4.6 OMERACT operational specification
│   │   ├── mollard_comparator.py       ← Mollard 2026 smartphone comparator alignment stub
│   │   └── tests/
│   ├── bayesian_concordance/           ← §4.8 hierarchical concordance model (H1.1) — PyMC layer
│   │   ├── model.py
│   │   ├── sensitivity_freq.py         ← Sensitivity Analysis 1 (frequentist mixed-effects)
│   │   ├── sensitivity_cohort.py       ← Sensitivity Analysis 2 (registry-representative)
│   │   ├── sensitivity_window.py       ← Sensitivity Analysis 3 (±60 / ±120 day windows)
│   │   └── tests/
│   ├── uc_aim2/                        ← Aim 2 H2.1 / H2.2 / H2.3 posterior tests
│   │   ├── widening.py
│   │   ├── anticipation.py
│   │   ├── suppression.py
│   │   └── tests/
│   └── recurrent_events/               ← §4.10 recurrent-event handling
├── schemas/                            ← all open schemas (JSON Schema)
│   ├── ptv.2.1-indexed-v1-noarcs.json  ← Dylan's existing PTV schema, mirrored here
│   ├── flare_event.schema.json         ← confirmed flareEvent record (§0 / §4.6)
│   ├── uc_annotation.schema.json       ← 5-component UC bundle (§4.7)
│   ├── derivation_chain.schema.json    ← §4.9 M63 GlassBox output format
│   └── escalation_event.schema.json    ← §4.5 / M4.A categorized escalation event
├── fixtures/
│   ├── synthetic_5patient/             ← from 2026-04-23 Dylan deliverable
│   └── synthetic_632event/             ← real-EHR-derived schema-validated PTV
├── data_request/
│   └── DUA_FORWARD_OptionB.md          ← Andras owns; placeholder in this repo
├── governance/
│   ├── pii_scrubbing_27rule.md         ← §4.1 / §9.4 audit description
│   └── pre_registration_log.md         ← §9.5 commit-hash record
└── docs/
    ├── confirmation_matching_rule.md   ← §13 item 4.6.a
    ├── confirmation_omeract.md         ← §13 item 4.6.b
    ├── confirmation_software.md        ← §13 item 4.8
    └── aetherion_response_log.md       ← optional v4-candidate edit queue
```

Module-internal logic for M2 / M3 / M6 / M9 / M62 / M63 is **not** in this repo. The schemas describe the *contract surfaces* (inputs/outputs); the proprietary package satisfies them.

---

## Reusable foundation from `2ndOpinionMD-MVP`

A working closed-form Bayesian engine already exists at `c:\2OPMD\2ndOpinionMD-MVP`, implementing the strategy at `reports/STRATEGY_BAYESIAN_PTV_UC_20260423.md`. Commit `00eaa9eb` (2026-05-05) shipped it; CINDER reuses it rather than re-implementing.

| 2ndOpinionMD-MVP component | Path | What it gives CINDER |
|---|---|---|
| Conjugate kernels (Beta-Bernoulli, Gamma-Poisson, Normal-Normal) | `server/ptv_toolkit/bayes.py` | §4.7 UC posterior math; closed-form per-patient updates with deterministic Python (no MCMC, scipy-optional) |
| `LikelihoodSpec` declarative DSL | `server/ptv_toolkit/bayes.py` | §4.4 PRO-domain shift detection rules expressible as JSON (`event_type`, `instrument_keys`, `value_delta_above`, `status_flag_in`, `weight_by="salience"`) |
| Default likelihood specs (`flare_30d`, `progression_3mo`, `taper_safety`) | `server/ptv_toolkit/bayes.py::DEFAULT_LIKELIHOOD_SPECS` | Starting point for CINDER's MCID-anchored rules; some thresholds need tightening to match §4.4 exactly (see "Phase 4.B revisions" below) |
| `UncertaintyCarrier` dataclass + serializers | `server/eoh/uc.py` | §4.7 UC bundle (5 components: signal density / evidence strength / anticipation / widening / refusal) and §4.9 derivation-chain output; schema version `uc.v1.bayes`; `to_handoff_block()` produces the `posteriors[]` envelope |
| `confidence_from_band` + `canonical_spec_hash` | `server/eoh/uc.py` | sha256 spec lineage (`spec_hash`) and the 0-1 confidence summary on band width |
| `bayesian_update_uc` tool registration | `server/ptv_toolkit/tools.py` | Same `(gh, args) -> dict` envelope as other graph tools; CINDER pipeline can call by name |
| MKG-prior lookup with weak fallback | `server/scripts/mkg_retrieval_harness.py::fetch_mkg_bayes_prior` | §4.3 prior sourcing: walks `public.mkg_bayes_priors` from most-specific (`icd_family × age_band × sex × phenotype × disease_cluster`) to least-specific; returns `None` on miss so caller falls back to weak default; safe on missing table / DB error |
| Probe-side `_bayes_phase` orchestration | `server/scripts/forward_probe_gap_report_chatbot.py` (lines 1245-1374) | Reference for the gate → cohort-strata → prior-lookup → kernel-call → handoff-block pattern |
| Two-lane MKG retrieval (semantic ANN + Postgres FTS) with per-source coverage pinning | `server/scripts/mkg_retrieval_harness.py::run_query` | Pattern (not direct dependency) for any future evidence-retrieval surface CINDER might need beyond FORWARD PTVs |

**What CINDER reuses directly.** The kernel layer (`bayes.py`), the UC dataclass (`uc.py`), and the MKG-prior lookup function are vendored or referenced as a private dependency. Two options:

- **Option A (preferred): Vendor as `cinder/bayes/`.** Copy the three modules into this repo as a small open package. License-compatible since the math layer was always intended to be open per strategy doc §5.1 (proprietary modules are M2/M3/M6/M9/M62/M63, not the kernels). Keeps CINDER self-contained for external replication and the §10 commitment clean.
- **Option B: Reference as `2opmd-bayes` private package.** Same layout the EoH proprietary modules use. Lighter-weight repository, but external replicators can't run the open analyses without 2OPMD package access — partially undermines §10's "open methods" commitment.

Default plan is **Option A**. Confirm with Andras before Phase 4.

**Boundary clarification for §10 IP table.** The closed-form Bayesian kernels are *not* M2/M3/M6/M9/M62/M63. They sit between the proprietary modules:

```
PTV (open schema)
  → M2 baseline fit (proprietary)
  → M3 stability bands + stack levels (proprietary)
  → M6 escalation routing (proprietary)
  → bayes.py kernels + likelihood spec (open)        ← CINDER's evidence-conditioning math
  → UC posterior (open schema)
  → M9 suppression / M62 governance (proprietary)
  → M63 derivation chain (open output schema)
  → flareEvent record (open schema)
```

This keeps the §10 IP table internally consistent: open math at the inference layer; closed reasoning at the patient-modeling and governance layers.

---

## Phase 0 — Repository scaffold and dev environment

**Window.** 2026-05-06 → 2026-05-09 (3 days, parallelizable with Phase 1)

**Inputs.**
- Empty `cinder-study/` git repo on `main`, no commits
- PROTOCOL_DRAFT_v3.md + PROTOCOL_DRAFT_v3.pdf from handoff package
- §10 IP posture (drives README + LICENSE language)
- §13 item 5 (minimum directory layout)

**Deliverables.**
1. Directory tree per "Repository topology" above committed as initial commit
2. `pyproject.toml` (Python ≥ 3.11) declaring: `pymc`, `arviz`, `numpy`, `pandas`, `scipy` (optional fast path for `bayes.py` ppf), `jsonschema`, `pyyaml`, `pytest`, `pytest-cov`, `ruff`, `mypy`, `nutpie` (optional NUTS sampler). The vendored `bayes.py` works without scipy via Acklam / regularized-incomplete-beta / Wilson-Hilferty fallbacks; scipy is opt-in for speed.
3. `README.md` reflecting §10 IP posture: methods open, EoH modules proprietary, blinded external re-run pathway as the reproducibility commitment
4. `LICENSE` — MIT for the analysis code in this repo; explicit note that proprietary modules are not covered
5. `.pre-commit-config.yaml` (ruff format/lint, mypy, jsonschema validation on `schemas/`)
6. `.github/workflows/ci.yml` — runs ruff, mypy, pytest, and `jsonschema` validation of fixtures against schemas
7. `data_request/DUA_FORWARD_OptionB.md` — placeholder marking Andras ownership
8. `governance/pre_registration_log.md` — empty template waiting for the v3.0-FINAL hash

**Acceptance criteria.**
- `pip install -e .[dev]` succeeds on a clean Windows env
- `pre-commit run --all-files` passes
- `pytest -q` passes (no tests yet, but framework runs)
- `gh repo create` (or equivalent) executed; `main` is the default branch; remote pushed; repo is public-facing per §13 item 5
- README explicitly names the §10 blinded external re-run pathway

**Notes.**
- PROTOCOL_v3.0-FINAL.md / .pdf are **not** copied in until Phase 3 (after Andras approves v3.0-FINAL). During Phase 0–2 the repo holds only this plan + scaffolding.
- Initial commit message: `chore: scaffold cinder-study per PROTOCOL_DRAFT_v3 §13`.

---

## Phase 1 — §13 confirmations to Andras

**Window.** 2026-05-08 → 2026-05-12 (parallelizable with Phase 0; gates Phase 3)

**Inputs.**
- PROTOCOL_DRAFT_v3.md §4.6 (Comparator Event Matching Rule + OMERACT operational specification)
- PROTOCOL_DRAFT_v3.md §4.8 (PyMC commitment)
- Dylan's existing PTV schema `ptv.2.1-indexed-v1-noarcs` from the 2026-04-23 deliverable
- Dylan's prior PTV-3agent run notes (windowing collapse risk surfaced there)
- FORWARD export field documentation (whatever's available pre-DUA via Sofia / Kaleb communications)

**Deliverables.**

### 1.A — `docs/confirmation_matching_rule.md` (§13 item: §4.6 matching rule)
A short memo stating one of:
- **Yes — implementable as written.** Map each rule clause to PTV schema fields; cite exact field names.
- **Yes with caveats.** Same mapping plus a named gap (e.g., sparse-data subgroup behavior, windowing collapse on the 3-agent run pattern).
- **Gap — needs revision.** Concrete description of where the rule breaks operationally; proposed redraft.

The memo must address every sub-rule of §4.6: unit of analysis, 1:1 matching, unmatched detections, unmatched comparators, tie-breaking, cross-comparator alignment.

### 1.B — `docs/confirmation_omeract.md` (§13 item: §4.6 OMERACT spec)
Confirm the OMERACT operational specification can be executed against the FORWARD export Sofia provides. Specifically address:
- Patient Global VAS shift detection (≥ 20-point worsening) in the available wave granularity
- Medication-change field resolution against the §4.5 escalation taxonomy (DMARD initiation, biologic, tsDMARD, corticosteroid rescue burst, dose increase, therapy switch, bridge therapy)
- Maintenance-vs-rescue rule (§4.5) implementability from medication record fields
- The indeterminate classification handling (escalation present but Patient Global VAS worsening absent or undocumented)

### 1.C — `docs/confirmation_software.md` (§13 item: §4.8 PyMC)
One-line answer: PyMC confirmed, OR Stan preferred (with rationale, before GitHub scaffold is committed). If PyMC, also confirm sampler (NUTS via `nutpie` vs default), random seeds policy, and ArviZ for posterior summaries.

**Owner.** Dylan (drafts); Andras (receives).

**Acceptance criteria.**
- All three memos delivered to Andras by 2026-05-15 (target)
- Any "gap" surfaced in 1.A or 1.B is flagged loudly (not buried) so the protocol can revise §4.6 before v3.0-FINAL tag
- `confirmation_software.md` is a single-line yes or a clean rationale (not a debate)

**Touchpoints.**
- If 1.A or 1.B surface a real gap: Andras + Dylan revise §4.6 before Phase 3 (v3.0-FINAL tag). This may push the 2026-05-20 gate by ≤ 5 days; flag immediately.

---

## Phase 2 — §6.1 sample-size simulation (deliverable)

**Window.** 2026-05-08 → 2026-05-15 (parallelizable with Phase 1)

**Inputs.**
- §6.1 simulation design specification table:

| Simulation parameter | Assumed value | Source |
|---|---|---|
| Evaluable post-warmup windows per patient | 4–6 | FORWARD semi-annual cadence; min 4-wave entry criterion |
| Flare base rate | 0.25–0.35 per patient per 24-month window | Mollard 2026 anchor + 50% inflation for data dominance |
| Comparator flare prevalence | 0.30–0.40 | Primary clinician-rated comparator; conservative |
| Prior family | Beta(2, 5) on kappa | Weakly informative, mild prior toward fair agreement |
| Simulation draws | 10,000 (target) | Standard for Bayesian interval-width planning |
| Interval width summary rule | 97.5th − 2.5th percentile of posterior kappa | Full credible interval width |

- Mollard 2026 PRO distribution / event rate parameters Dylan has already seen
- §6 decision rule: H1.1 supported if posterior probability that kappa > 0.40 is ≥ 0.80

**Two-layer simulation.** The CINDER protocol has two distinct Bayesian surfaces, and the simulation respects the split:

1. **Per-patient detection layer** (closed-form Beta-Bernoulli over PRO-shift evidence). Reuses the vendored `bayes.py::update_beta_bernoulli` + a CINDER-tuned `LikelihoodSpec` matching §4.4 MCIDs exactly. Deterministic, ≤ 50 ms per patient per hypothesis (per strategy doc §9 latency target).
2. **Population concordance layer** (Bayesian hierarchical model on Cohen's kappa). PyMC. This is the §6 + §4.8 primary analysis surface — the level at which the H1.1 decision rule lives. NUTS sampling, 10,000 draws.

The simulation generates synthetic patient-wave data, runs the per-patient layer to produce flareEvent records, classifies them against simulated clinician-rated comparators per the §4.6 matching rule, then feeds the resulting 2×2 agreement table into the PyMC population layer. This mirrors what the production pipeline does on real FORWARD data — the simulation IS the pipeline, just on synthetic inputs.

**Deliverables.**
1. `analysis/simulation/inputs.yaml` — exact parameter values (within or replacing the ranges above), with citation field per parameter
2. `analysis/simulation/run_simulation.py` — reproducible script: deterministic seed, generates the data-generating process per the §6.1 table, runs the per-patient detection layer via `bayes.py`, produces flareEvent records, runs the §4.6 1:1 matching rule against simulated comparator events, runs 10,000 PyMC draws on the kappa-generating concordance scenario, produces posterior interval widths
3. `analysis/simulation/results/kappa_ci_width.md` — actual posterior CI width at N=50, plus the N=200 / N=500 scaling check (expected ≈ 0.07 / ≈ 0.05)
4. `analysis/simulation/tests/test_simulation_reproducibility.py` — verifies bit-stable output with fixed seed for both layers
5. **Patch decision memo to Andras**: if width changes materially (> ± 0.05) from the protocol's 0.15 estimate, propose §6 revisions (decision rule, sample-size justification, abstract numbers)

**Acceptance criteria.**
- Script runs end-to-end on a clean env in ≤ 15 minutes on a workstation
- Posterior CI width reported with 4-decimal precision and comparison delta against the 0.15 protocol number
- Reproducibility test passes on Linux + Windows
- If the H1.1 decision rule (posterior probability ≥ 0.80 that kappa > 0.40) needs revision under the actual simulation, a single-paragraph memo to Andras flags this **before** Phase 3 freeze

**Risks / fallbacks.**
- If PyMC NUTS sampler diverges on the prior + Beta(2,5) configuration, fall back to the analytical posterior for the 2x2 agreement table (Bayesian beta-binomial) and document the simplification
- If the FORWARD-derived event-rate priors are tighter than the §6.1 ranges, run the simulation under the tighter priors and document both

---

## Phase 3 — v3.0-FINAL tag and pre-registration commit hash

**Window.** 2026-05-15 → 2026-05-20 (gate)

**Inputs.**
- Andras review of Phase 1 confirmation memos
- Phase 2 simulation results + any §6 revision agreed on
- Andras-owned §13 items: FLAME → Smolen 2016 substitution confirm/override; authorship + ICMJE order; COI statements; v3.0-FINAL approval

**Deliverables.**
1. `PROTOCOL_v3.0-FINAL.md` — final protocol text incorporating any Phase 1 / Phase 2 driven edits, committed to repo
2. `PROTOCOL_v3.0-FINAL.pdf` — typeset version (Andras owns the typeset; this commit just receives it)
3. Git tag `v3.0-FINAL` annotated with the §13 checklist sign-off
4. `governance/pre_registration_log.md` updated with:
   - The exact `v3.0-FINAL` commit SHA-1 hash
   - The repo URL
   - Tag timestamp (UTC)
   - All five §13 Dylan items marked complete with links to Phase 1 / Phase 2 deliverables
5. Hash + tag delivered to Andras for §9.5 insertion and ACR abstract supplemental field

**Acceptance criteria.**
- Tag `v3.0-FINAL` exists and is signed (gpg-signed if practical, otherwise annotated)
- Commit hash is reproducible from `git rev-parse v3.0-FINAL`
- README's pre-registration section cites the hash
- All §13 boxes ticked OR explicitly deferred with Andras sign-off

**Risk.**
- Slip from 2026-05-20 to ~2026-05-25 is tolerable for ACR (deadline 2026-06-09) but compresses Phase 4 prep time. If slip > 5 days, escalate.

---

## Phase 4 — Reference implementations on synthetic exemplars

**Window.** 2026-05-20 → DUA execution date (variable; T+0 anchor for Phase 5)

**Inputs.**
- Tagged v3.0-FINAL protocol
- Existing synthetic exemplars: 5-patient cohort + 632-event real-EHR PTV (from 2026-04-23 Dylan deliverable)
- PTV schema `ptv.2.1-indexed-v1-noarcs`
- Phase 1.A and 1.B confirmation memos as the implementation contract
- **Vendored from `2ndOpinionMD-MVP`**: `bayes.py`, `uc.py`, `fetch_mkg_bayes_prior` (per "Reusable foundation" section)

**Deliverables.**

### 4.A — Vendored Bayesian kernel layer (`cinder/bayes/`) — ✅ landed 2026-05-25

Vendored from `2ndOpinionMD-MVP` at locked commit `00eaa9eb` per the "Decisions locked" table:

- `cinder/bayes/uc.py` ← `server/eoh/uc.py` (verbatim; vendoring banner only)
- `cinder/bayes/graph.py` ← `server/ptv_toolkit/graph.py` (verbatim; vendoring banner only)
- `cinder/bayes/kernels.py` ← `server/ptv_toolkit/bayes.py` (renamed to avoid shadowing the package; `from server.eoh.uc import ...` rewritten to `from .uc import ...`; otherwise verbatim)
- `cinder/bayes/mkg_retrieval.py` ← `fetch_mkg_bayes_prior` extracted from `server/scripts/mkg_retrieval_harness.py`. CINDER-specific DSN env var resolution (`CINDER_MKG_DSN`, `MKG_DSN`, `DATABASE_URL` — MVP-internal vars deliberately not consulted) and stdlib logger replacing the MVP's emoji-prefixed `_log` warning. Pre-Phase-6 returns `None` → kernel falls back to weak priors per `DEFAULT_HYPOTHESIS_PRIORS`.
- `cinder/bayes/__init__.py` — public API surface + `VENDORED_AT_COMMIT = "00eaa9eb"` constant
- `cinder/bayes/PROVENANCE.md` — vendoring contract: source mapping, edit log, re-vendoring procedure, EoH-handshake stub policy (handshakes live at orchestration layer, not kernel; deliberately not vendored), weak-prior fallback policy

**F2 regression harness landed alongside** (`tests/regression/`):
- `test_bayes_kernels_unit.py` — closed-form posterior properties: posterior-mean correctness, band-tightening with evidence, fractional-weight handling
- `test_bayes_harness_q11_q13.py` — ports MVP `ptv_toolkit_questions.json` q11/q12/q13 as data-driven pytest assertions; covers all three default hypotheses (`flare_30d`, `progression_3mo`, `taper_safety`) against the 632-event fixture
- `test_bayes_harness_h11_h13.py` — ports MVP `forward_probe_gap_session_harness_questions.json` h11/h12/h13 conversational probes as kernel-level artifact assertions; symmetric `to_dict`/`from_dict` round-trip + asymmetric `to_handoff_block` shape verification
- Determinism test: two runs on the same fixture produce bit-identical UCs (the §10 replicator-friendly invariant)

**Verification:** 61/61 tests passing (35 prior + 26 new); 0 lint errors; `from cinder.bayes import bayesian_update_uc, load_graph` smoke test produces `flare_30d: point=0.20, band=(0.041, 0.4291), conf=moderate (0.612), spec_hash=uc_9cd77d1becd57da7` against the real-EHR fixture under weak priors (no MKG DSN set, expected pre-Phase-6 behavior).

### 4.B — Open schemas (`schemas/`)

**Reused from MVP** (vendored or schema-aligned):
- UC bundle structure already exists at `server/eoh/uc.py` (`uc.v1.bayes` schema). CINDER adopts it directly via `to_handoff_block()` and `to_legacy_annotation()` round-trips.
- LikelihoodSpec JSON shape already documented in `bayes.py` module docstring.

**New for CINDER**:
- `flare_event.schema.json` — confirmed flareEvent: domain shift bundle, escalation bundle, temporal offset, UC annotations (in `uc.v1.bayes` format), M63 derivation chain reference
- `uc_annotation.schema.json` — formalizes the `uc.v1.bayes` bundle as a published JSON Schema; adds the §4.7 5-component mapping (signal density, evidence strength, anticipation flag, widening flag, refusal flag) on top of the existing `point_estimate` / `band_90` / `confidence` core
- `derivation_chain.schema.json` — M63 GlassBox output: inputs, intermediate flags, governance gates passed, UC component values, `spec_hash` from `canonical_spec_hash`
- `escalation_event.schema.json` — §4.5 categorized escalation event with M6 arbitration metadata
- All schemas validate against the 5-patient + 632-event fixtures via CI

### 4.C — CINDER-tuned likelihood specs (`analysis/detection/`)

The MVP `DEFAULT_LIKELIHOOD_SPECS["flare_30d"]` is a working draft, but its thresholds don't exactly match CINDER §4.4. Tighten them for the CINDER detection layer:

| PRO domain | Instrument | MVP rule (current) | CINDER §4.4 (target) | Action |
|---|---|---|---|---|
| Functional status | HAQ-II | `value_delta_above: 0.22` | ≥ 0.22 | matches; keep |
| Pain | Pain VAS | `value_delta_above: 15.0` (vas_pain) | ≥ 20 | tighten to 20 |
| Patient global | Patient Global VAS | `value_delta_above: 20.0` (vas_global) | ≥ 20 | matches; keep |
| Composite | RAPID3 | not in MVP rules | ≥ 3.6 | add |

Deliverable: `analysis/detection/cinder_likelihood_spec.yaml` — the canonical CINDER `flare_30d` likelihood spec with §4.4 thresholds verbatim, plus the §4.4 RAPID3-overlap clarification (RAPID3 evaluated as composite, not double-counted with HAQ-II / Pain VAS / Patient Global VAS components). Versioned (`spec_hash` deterministic), and included in every flareEvent's `basis` field via the existing `bayes.py` machinery.

### 4.D — Comparator matching rule (`analysis/matching_rule/`) — net-new

These don't exist in the MVP; they are CINDER-specific:
- `matcher.py` — implements §4.6: unit of analysis, ±90-day window, 1:1 matching, tie-breaking on Stack Level then temporal proximity, unmatched event accounting
- `omeract_comparator.py` — implements §4.6 OMERACT spec: escalation in M4.A category within ±90 days AND Patient Global VAS ≥ 20-point worsening; indeterminate handling
- `mollard_comparator.py` — Mollard 2026 smartphone signature alignment: daily-granularity timestamps collapsed to nearest semi-annual FORWARD wave
- Tests: synthetic exemplar produces expected flareEvent records under each comparator

### 4.E — Per-patient detection orchestration (`analysis/detection/`)

Reuses `bayes.py::bayesian_update_uc` and the MKG-prior lookup pattern from MVP. New CINDER-specific glue:
- `detect_flare.py` — for each patient × wave: assemble working set from `M2 baseline → M3 stability bands → M6 escalation`, call `bayesian_update_uc(gh, hypothesis_id="flare_30d", evidence_event_ids=working_set, prior=mkg_prior or weak_default, likelihood_spec=cinder_v3_spec)`, collect UC; this is the equivalent of the MVP `_bayes_phase` but as a batch driver for validation rather than a chatbot phase
- `forward_priors.py` — adapter that calls `fetch_mkg_bayes_prior(hypothesis_id="flare_30d", cohort_strata={icd_family, age_band, sex})` against a CINDER-specific priors table (`public.cinder_bayes_priors` or sidecar JSON), with weak `Beta(2,8)` fallback per strategy doc §6 phase 1
- The MVP's `_bayes_gate` 8B classifier is **not** ported — CINDER batch validation runs every wave through the kernel deterministically, no LLM gate

### 4.F — Population concordance analysis (`analysis/bayesian_concordance/`) — PyMC layer

This is the §4.8 primary analysis surface; it runs *on top of* the per-patient flareEvent records produced by Phase 4.D. PyMC, not closed-form (the inference target is hierarchical kappa with patient random effects):
- `model.py` — §4.8 hierarchical model with patient-level random effects on detection concordance; outcome = agreement between flareEvent records and clinician-rated flares; Cohen's kappa, sensitivity, specificity, PPV, NPV with 95% posterior credible intervals; weakly informative priors anchored on Mollard 2026 + 50% expansion; posterior predictive checks
- `sensitivity_freq.py` — Sensitivity Analysis 1: event-level binary classification with mixed-effects logistic regression, random patient intercepts, 0.5 classification threshold
- `sensitivity_cohort.py` — Sensitivity Analysis 2: model applied to registry-representative cohort with zero-escalation patients as true-negative observations
- `sensitivity_window.py` — Sensitivity Analysis 3: ±60-day and ±120-day window robustness checks
- All four runnable on the synthetic exemplar with deterministic seeds

### 4.G — Aim 2 UC analyses (`analysis/uc_aim2/`)

Reuses the `UncertaintyCarrier.posterior_params` and `band_90` fields directly from the per-patient kernel output:
- `anticipation.py` — H2.1: proportion of confirmed flares preceded by UC widening in prior K=2 waves vs stable-window null. UC widening = `band_90` width increase > 20% vs patient's stable-window mean width (per §4.7).
- `widening.py` — H2.2: proportion of high-missingness windows showing UC widening vs low-missingness null. Missingness computed from PTV `metadata.code_index` density per §4.7 signal-density definition.
- `suppression.py` — H2.3: proportion of stable windows with no UC widening vs flare-preceding-window null
- Each uses the §4.7 numerical thresholds verbatim (K=2 waves, ≥ 50% missingness, > 20% relative posterior width increase)

### 4.H — Recurrent events (`analysis/recurrent_events/`)
- `episode_classifier.py` — §4.10: inter-flare interval > 90 days → independent event; within 90 days of confirmed flare → continuation of episode
- Reports recurrence interval, episode duration, independent flare count per patient

### 4.I — Test harness for the vendored Bayesian layer

The MVP ships two overlapping harness test surfaces. CINDER inherits them both and adds CINDER-specific extensions.

#### Inherited from MVP (regression baseline at commit `00eaa9eb`)

**Toolkit harness (`ptv_toolkit_questions.json` — q11-q13)** — per-tool route + assertion tests:

| ID | Question | `expected_route` | `expected_primary_tool` | `expected_args_shape` | `must_have_any` |
|---|---|---|---|---|---|
| `q11_bayes_flare_30d` | "What is the posterior probability of a disease flare in the next 30 days, with a 90% credible interval and the events that drove the update?" | `bayesian_update` | `bayesian_update_uc` | `{hypothesis_id: "flare_30d"}` | `["flare","posterior","band","credible"]` |
| `q12_bayes_progression_3mo` | "Will this patient progress in the next 3 months? Give me a Bayesian posterior with 90% band and cite the evidence_event_ids." | `bayesian_update` | `bayesian_update_uc` | `{hypothesis_id: "progression_3mo"}` | `["progression","posterior","band"]` |
| `q13_bayes_taper_safety` | "Is it safe to attempt a DMARD taper now? Compute a posterior over taper safety and report the 90% credible interval and prior source." | `bayesian_update` | `bayesian_update_uc` | `{hypothesis_id: "taper_safety"}` | `["taper","posterior","band","prior"]` |

**Session harness (`forward_probe_gap_session_harness_questions.json` — h11-h13)** — end-to-end conversational surface:

| ID | Question |
|---|---|
| `h11_bayes_flare` | "Give me the posterior probability that this patient flares in the next 30 days, with a 90% credible interval and the evidence event_ids that drove the update." |
| `h12_bayes_progression` | "Compute a Bayesian posterior over disease progression in the next 3 months. Report the point estimate, 90% band, prior source, and the events used as evidence." |
| `h13_bayes_taper` | "Is it safe to attempt a DMARD taper at the most recent timepoint? I want a posterior probability of safe taper, the 90% credible interval, and a regime-change check on the evidence." |

These three session questions are structurally richer than the toolkit probes: h12 explicitly requests `prior source`, h13 requests a `regime-change check`. Both requirements map directly onto UC fields the vendored layer already produces (`prior.source` and the `band_90` widening criterion).

#### CINDER-specific additions

The MVP hypotheses work on single-patient PTV graphs; CINDER needs batch-validation analogues that run against FORWARD-derived PTVs and compare against protocol-specified comparators. Four CINDER test additions:

| CINDER test ID | Adapts | What's different |
|---|---|---|
| `c01_flare_detection_cinder_spec` | `q11_bayes_flare_30d` | Same kernel, but uses `cinder_likelihood_spec.yaml` (§4.4 MCID thresholds: Pain VAS Δ ≥ 20, RAPID3 Δ ≥ 3.6) rather than MVP defaults; asserts `point_estimate` changes from MVP default when RAPID3 evidence present |
| `c02_matching_rule_smoke` | — (net-new) | Runs the §4.6 1:1 matching rule on the 5-patient synthetic cohort; pins expected flareEvent count, Stack Level tie-break outcome, and unmatched-event counts |
| `c03_omeract_comparator_smoke` | — (net-new) | Runs the §4.6 OMERACT comparator on the 5-patient cohort; asserts expected indeterminate rate under the Patient Global VAS ≥ 20 threshold |
| `c04_regime_change_widening` | `h13_bayes_taper` (regime-change check) | Asserts that a synthetic patient with ≥ 50% PRO missingness in K=2 prior waves produces `band_90` width > 20% above that patient's stable-window baseline (H2.2 null reference logic) |

`c04_regime_change_widening` doubles as the Phase 4.F / Aim 2 H2.2 acceptance test, closing the loop between the h13 session-harness intent and the §4.7 widening definition.

**Acceptance criteria.**
- All sub-deliverables runnable on the 632-event synthetic PTV without proprietary EoH module access (M2/M3/M6/M9/M62/M63 are imported from the 2OPMD private package; this repo references them by stable interface but does not implement them; the open kernels and UC dataclass live here per Option A in "Reusable foundation")
- `bayesian_update_uc` on the 632-event PTV produces the same `point_estimate`, `band_90`, `spec_hash`, and `evidence_event_ids` as the MVP at commit `00eaa9eb` (regression against q11/q12/q13 assertions)
- `c01_flare_detection_cinder_spec` produces a **different** `point_estimate` from the MVP default when RAPID3 events are present — confirming the §4.4-tuned spec is actually doing something, not silently falling back to MVP defaults
- `c02` and `c03` comparator tests produce deterministic, bit-stable output on the 5-patient synthetic cohort
- `c04_regime_change_widening` passes with the high-missingness synthetic patient
- `pytest --cov` shows ≥ 80% coverage on `analysis/` and `cinder/bayes/`
- Schemas + fixtures pass `jsonschema` validation in CI

**Notes / IP boundary.**
- This phase consumes the EoH module outputs but does **not** reimplement them. The proprietary package exposes:
  - `eoh.m2.fit_baseline(ptv) -> BaselineParameters`
  - `eoh.m3.compute_terrain(baseline) -> StabilityBands, StackLevels`
  - `eoh.m6.route_escalation(med_record) -> EscalationEvents`
  - `eoh.m9.suppress(...) -> PauseFlag`
  - `eoh.m62.handshake(...) -> GovernanceVerdict`
  - `eoh.m63.derive(...) -> DerivationChain`
- This repo's tests stub those interfaces with deterministic fakes for CI.

---

## Phase 5 — DUA execution and first production PTVs

**Window.** Anchored on DUA execution date (T+0); deliverables T+0 → T+2 days

**Inputs.**
- Executed DUA (UNMC standard, Option B, 2OPMD LLC receiving entity, Andras PI) — owned by Andras
- FORWARD WebQuest semi-annual wave export (CSV/JSON per FORWARD standard)
- 27-rule PII scrubbing pipeline (already implemented per §4.1; integrated here)

**Deliverables.**
1. Data ingestion adapter under `analysis/ingestion/` that consumes the FORWARD export format and produces PTV-format records validated against `ptv.2.1-indexed-v1-noarcs`
2. PII scrubbing audit baked into `metadata.pii_scrubbed` for every PTV (§9.4)
3. First 5 production PTV graphs delivered to Andras for review
4. Sanity check: production PTVs round-trip through Phase 4 reference pipeline and produce sensible flareEvent counts (compared against synthetic-exemplar baseline)

**Acceptance criteria.**
- Zero PII fields detected in the analytic environment (audit trail in `metadata.pii_scrubbed` for every record)
- All PTVs validate against the published schema
- First 5 PTVs reviewed and signed off by Andras within T+2 days

**Risk.**
- DUA execution is on Andras + UNMC critical path; not under Dylan's direct control. Phase 5 cannot start until DUA is signed.

---

## Phase 6 — Aim 1 preliminary analysis (T+0 → T+30 days post-DUA)

**Window.** T+0 → T+30 days from DUA execution (per §7 timeline)

**Inputs.**
- Full FORWARD-derived PTV cohort (Phase 5 output)
- Phase 4 reference implementations
- Tagged v3.0-FINAL protocol

**Deliverables.**
1. M2 chronic baseline + M3 stability band fits across the full cohort (proprietary modules called; outputs schema-validated)
2. M6 escalation event extraction across full medication record
3. §4.6 comparator matching rule applied across all three comparators
4. §4.8 Bayesian primary analysis: posterior credible intervals on kappa, sensitivity, specificity, PPV, NPV against clinician-rated comparator
5. Sensitivity Analyses 1 (frequentist), 2 (registry-representative cohort), 3 (±60 / ±120 day windows) executed
6. Comparator triangulation: same metrics against Mollard signature + OMERACT operational implementation
7. H1.1 / H1.2 / H1.3 results memo to Andras

**Acceptance criteria.**
- All hypothesis decisions reported as full posterior distributions (not point estimates)
- H1.1 explicit posterior probability that kappa > 0.40 reported
- H1.2 sensitivity-above-physician-global-only baseline computed
- H1.3 set-overlap analysis (CINDER ∩ Mollard, CINDER \ Mollard, Mollard \ CINDER) reported
- All flareEvent records carry full M63 derivation chains
- Disagreements characterized rather than averaged away (§4.8)

---

## Phase 7 — Aim 2 preliminary analysis (T+30 → T+45 days post-DUA)

**Window.** T+30 → T+45 days from DUA execution

**Deliverables.**
1. UC anticipation rate across confirmed flares vs stable-window null (H2.1)
2. UC honest-widening rate across high-missingness windows vs low-missingness null (H2.2)
3. UC suppression rate across stable windows vs flare-preceding-window null (H2.3)
4. Each hypothesis evaluated as posterior probability ≥ 0.80 against pre-specified null reference (§2 thresholds)
5. Aim 2 results memo to Andras

**Acceptance criteria.**
- Each H2.x reported as posterior probability statement with full credible interval
- Stable-window / high-missingness / flare-preceding-window operational definitions cited verbatim from §4.7
- Refusal-rate descriptive analysis included as part of the UC governance trace

---

## Phase 8 — Kaleb preliminary delivery (2026-05-31)

**Window.** Up to 2026-05-31

**Owner.** Andras (delivers); Dylan (provides results package)

**Inputs.**
- Phase 6 + Phase 7 results, OR — if DUA timing has not allowed Phase 6/7 to complete by 2026-05-31 — Phase 4 reference-implementation results on synthetic exemplars + simulation outputs as preliminary stake

**Deliverables (Dylan's contribution).**
1. Results notebook (`docs/kaleb_preliminary_results.ipynb` or equivalent rendered HTML) summarizing whatever has run by 2026-05-31
2. Figures package: posterior densities for kappa, sensitivity, specificity; comparator triangulation overlap diagrams; UC anticipation / widening / suppression rates
3. Selected derivation-chain examples demonstrating §4.9 traceability
4. Honest reporting on what the preliminary stake covers (synthetic-exemplar vs production-data) and what is still pending

**Acceptance criteria.**
- Andras-approved before any artifact reaches Kaleb
- KALEB_BRIEF_v2 framing respected: "internal only; no external delivery from me without your consent"
- §10 IP posture honored in any released figures (no module-internal logic exposed)

---

## Phase 9 — ACR Convergence 2026 abstract submission (2026-06-09)

**Window.** Up to 2026-06-09 (deadline)

**Owner.** Andras (submits)

**Dylan's contributions.**
1. Confirm the ACR_ABSTRACT_v2 numerical bindings still match v3.0-FINAL after any Phase 1/2 edits
2. Provide the v3.0-FINAL commit hash + repo URL for the supplemental field (§9.5)
3. If Phase 6 has produced anything by 2026-06-09, decide jointly with Andras whether the abstract upgrades from "Anticipated Results" framing to actual preliminary results

**Acceptance criteria.**
- Hash + tag visible in the abstract submission supplemental field
- Authorship list mirrors §12 (Hangyal co-first, McCapes co-first, Michaud senior)

---

## Phase 10 — SBIR Phase I preliminary data narrative (deadline 2026-09-05)

**Window.** Drafting from 2026-08-15; submission via ASSIST by 2026-09-05 (non-extendable)

**Owner.** Joint (Andras leads narrative; Dylan provides preliminary data sections)

**Dylan's contributions.**
1. Phase 6 + Phase 7 results, finalized
2. Preliminary Data narrative: Aim 1 / Aim 2 results, comparator triangulation, UC governance behavior
3. Innovation section support: terrain-aware detection figures, derivation-chain examples
4. Methods: condensed PROTOCOL_v3.0-FINAL §4 + §5 + §6 for SBIR page limits

**Acceptance criteria.**
- All claims in Preliminary Data trace to Phase 6/7 deliverables with derivation chains
- §10 IP posture honored — no proprietary module internals disclosed in the application
- Submitted via ASSIST by 2026-09-05

---

## Cross-cutting concerns

### Pre-registration discipline (§9.5)
The v3.0-FINAL commit hash (Phase 3) is the pre-registration anchor. After tagging:
- No retroactive edits to hypotheses, decision rules, primary analysis specification, or comparator matching rule
- Any v4-candidate edits surfaced post-tag go into `docs/aetherion_response_log.md` as v4 candidates per the handoff guidance, **not** as silent v3 patches
- The `governance/pre_registration_log.md` is the authoritative timestamp record

### Reproducibility commitment (§10)
What this repo guarantees:
- All open code runs end-to-end on a clean env with documented dependencies
- All schemas validate the released event records
- All statistical analyses are deterministic given the input data and seeds
- The blinded external re-run pathway is documented as the alternative mechanistic-replication channel

What this repo does **not** guarantee:
- Source-level access to M2 / M3 / M6 / M9 / M62 / M63 internals (per §10 IP table)

### Testing and CI
- `pytest` runs on every PR
- `mypy` strict on `analysis/` and `schemas/`
- Schema validation runs on every fixture change
- Reproducibility test (Phase 2) pins simulation output bit-for-bit with fixed seed
- Synthetic-exemplar regression test (Phase 4) pins flareEvent record output bit-for-bit

### Dependencies and versioning
- Python ≥ 3.11 (matches PyMC 5.x recommended runtime)
- Pin major versions in `pyproject.toml`; allow patch updates
- Lock file (`uv.lock` or `poetry.lock`) committed for production reproducibility
- EoH proprietary package referenced as a private dependency with pinned version

### Communication cadence
- Slack thread for §13 confirmations and v4-candidate flagging
- Markdown patches preferred over freeform descriptions for any protocol-text revisions
- Single-line "yes, fine as drafted" is acceptable for confirmations per the handoff

---

## Critical-path summary

| Phase | Window | Gates | Dependency |
|---|---|---|---|
| 0 — Scaffold | 2026-05-06 → 2026-05-09 | — | None; can start immediately |
| 1 — §13 confirmations | 2026-05-08 → 2026-05-12 | Gates Phase 3 | None; reads protocol + Dylan's prior PTV work |
| 2 — Sample-size simulation | 2026-05-08 → 2026-05-15 | Gates Phase 3 (if width changes materially) | Phase 0 (PyMC env) |
| 3 — v3.0-FINAL tag | 2026-05-15 → 2026-05-20 | Gates Phase 4 + ACR submission | Phases 1, 2; Andras sign-off |
| 4 — Reference implementations | 2026-05-20 → DUA T+0 | Gates Phase 6/7 | Phase 3 |
| 5 — DUA + first PTVs | T+0 → T+2 days | Gates Phase 6/7 | DUA executed (Andras + UNMC) |
| 6 — Aim 1 preliminary | T+0 → T+30 days | Gates Phase 8/9/10 | Phase 5 |
| 7 — Aim 2 preliminary | T+30 → T+45 days | Gates Phase 8/9/10 | Phase 6 |
| 8 — Kaleb preliminary | by 2026-05-31 | — | Best-available evidence |
| 9 — ACR abstract | by 2026-06-09 | — | Phase 3 commit hash |
| 10 — SBIR submission | by 2026-09-05 | — | Phases 6, 7 |

The hard gate is Phase 3 (v3.0-FINAL tag by 2026-05-20). Phases 0–2 are the work that gets there. Everything after is execution against a frozen protocol.

---

## Decisions locked (2026-05-23)

Calendar pressure does not allow another round-trip on these items before the 5/26 call. Dylan has made the call on items 6 and 8 below using the default plan, and on the PTV input contract schema (newly added). Andras can countermand any of these on Monday with no rework cost beyond a one-paragraph plan amendment; doing nothing means the defaults stand.

| # | Decision | Locked at | Rationale |
|---|---|---|---|
| **6. Bayesian-engine vendoring** | **Option A — vendor `bayes.py` / `uc.py` / `fetch_mkg_bayes_prior` into `cinder/bayes/`** | 2026-05-23 | (a) §10 commits CINDER to "open methods" — Option B's private-package model directly conflicts with that. (b) Strategy doc §5.1 always intended the kernel layer to be open. (c) License compatibility is internal-to-internal MIT; no friction. (d) Code volume is small and stable: `bayes.py` ~1,020 lines, `uc.py` ~ similar order, `fetch_mkg_bayes_prior` is a single function. (e) Self-contained replication is the §10 commitment to Kaleb. |
| **8. MVP commit baseline** | **Pin at `00eaa9eb` (2026-05-05) for `protocol-v3.0-FINAL`. Re-evaluate upgrades per CINDER minor release; never auto-track HEAD.** | 2026-05-23 | Pre-registration immutability — the protocol commit hash submitted to ACR must point to a Bayesian engine that doesn't change underneath us. Upgrade evaluation cadence is "post-tag, before next minor release." |
| **PTV input contract schema** | **Published as `schemas/ptv_input.schema.json`** | 2026-05-23 | Strict on the small core that `bayes.py` actually reads (events, annotations.{card,salience,status_flags,value}, timestamps, metadata.pii_scrubbed); permissive (`additionalProperties: true`) on index sidecars (`metadata.index/entities/code_index`) since they're tooling outputs that grow. Includes a `cinder_pro` annotation slot for FORWARD PRO score fields (`instrument`, `score`, `wave_number`, `wave_date`, `delta_from_baseline`, `exceeds_band`) per §4.4. The 632-event reference fixture validates against this schema as of this commit; 17 PTV-schema regression tests in `tests/unit/test_ptv_input_schema.py` exercise both positive and negative cases. |

## Open questions for Andras

The remaining items where Dylan would still benefit from a single-line yes/no:

1. **Repo visibility.** Public from initial commit (per §13 item 5 "public-facing repo")? Or private until v3.0-FINAL tag, then flipped public? Public-from-day-zero is what the §13 language reads as.
2. **License scope.** MIT for the analysis code is the recommended default; the `LICENSE` file in this commit assumes MIT. Confirm before push to remote.
3. **Hosting.** GitHub vs alternative (GitLab, internal)? §13 references "GitHub repository scaffold" so GitHub is presumed; CI workflow assumes GitHub Actions.
4. **CI runner matrix.** Currently configured for `ubuntu-latest` + `windows-latest` × Python 3.11 + 3.12. Confirm or trim.
5. **Phase 8 fallback.** If DUA has not executed by 2026-05-31, is the Kaleb preliminary delivery synthetic-exemplar-based (with that limitation explicitly named)? Default plan assumes yes.
7. **§4.4 RAPID3 threshold.** Protocol §4.4 names ≥ 3.6 as the RAPID3 MCID; the MVP `flare_30d` likelihood spec doesn't include RAPID3 as a separate rule. Confirm the §4.4 number is canonical (vs. e.g. 3.0 or 3.8 in some published literature) so Phase 4.B encodes the exact threshold without a second revision.

(Items 6 and 8 from the prior list are now in "Decisions locked" above.)

A single-line "yes, fine as drafted" on the remaining six items unblocks Phase 4 vendoring.
