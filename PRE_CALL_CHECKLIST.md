---
title: CINDER — Pre-Call Checklist for FORWARD/UNMC meeting
project: CINDER
call_date: 2026-05-26 (Tuesday) 1:00 PM CDT
attendees:
  - Andras Hangyal, PharmD (2OPMD, PI)
  - Dylan McCapes (2OPMD, informatics architecture)
  - Kaleb Michaud, PhD (FORWARD Co-Director, UNMC; senior author)
  - Adam Cornish (UNMC, head of IT; data delivery)
  - Rebecca Schumacher (FORWARD, executive director)
status: PRE-CALL — drives work between now (2026-05-23) and the 5/26 call; aligned to PROTOCOL_DRAFT_v3 §13 + IMPLEMENTATION_PLAN.md Phase 4
date: 2026-05-23
companion_to:
  - IMPLEMENTATION_PLAN.md
  - PROTOCOL_DRAFT_v3.md (§13 pre-delivery checklist)
  - Andras email "Updates needed from you before Tuesday's call" (2026-05-23)
---

# CINDER Pre-Call Checklist — Tuesday 5/26 with Kaleb / Adam / Rebecca

This document drives the next 72 hours: response to Andras (Sun evening), optional Monday sync, Tuesday call. Every item below has an explicit acceptance criterion. Items are **ordered by what blocks what**, mirroring Andras's framing.

Andras's terminology mapped to the implementation plan: **F2 regression harness** = IMPLEMENTATION_PLAN Phase 4 (reference implementations) + Phase 4.H (test harness). **F4-CASE-01 / F4-CASE-04** = specific case-instantiations on the 632-event noarcs PTV under Phase 4.D (per-patient detection orchestration).

---

## Section 1 — Andras's six asks

### 1. PTV noarcs reference — *tonight-blocker*

**What.** Share the real-EHR 632-event PTV from the 2026-04-23 deliverable, in the noarcs format (`ptv.2.1-indexed-v1-noarcs`), with `metadata.code_index` intact. Schema doc as fallback if the file is awkward to share.

**Acceptance criteria.**
- [ ] 632-event file confirmed to be noarcs format (not legacy with-arcs); if with-arcs, regeneration plan stated and ETA given
- [ ] File transmitted to Andras via secure channel (not email attachment) by Saturday evening 2026-05-23
- [ ] Schema doc for `ptv.2.1-indexed-v1-noarcs` shared in parallel — covers field definitions, `metadata.code_index` bucket structure (`drugs`, `rxnorm`, `icd`, `labs`, `loinc`), connascence kinds, annotation slots
- [ ] PII scrubbing audit confirmed — `metadata.pii_scrubbed` block present in the file
- [ ] Filename + SHA-256 checksum recorded in `governance/pre_registration_log.md`

**Why this is tonight-blocker.** Andras names F4-CASE-01 and F4-CASE-04 instantiation as downstream — those cases can't be built without the reference fixture.

---

### 2. F2 regression harness status

**What.** Honest status report against the four F2 checkpoints. Even a partial harness is enough for Tuesday — the goal is "absorbs intake debugging when the slice lands," not "all green."

**Acceptance criteria.** Each checkpoint reports green / yellow / red plus a one-line state:

| Checkpoint | Green criterion | Status |
|---|---|---|
| Schemas validated | `flare_event`, `uc_annotation`, `derivation_chain`, `escalation_event` JSON Schemas exist; `jsonschema` validates the 5-patient + 632-event fixtures | [ ] |
| `bayes.py` vendored + runs on noarcs PTV | 2ndOpinionMD-MVP commit `00eaa9eb` math layer imports cleanly into `cinder/bayes/`; `bayesian_update_uc` produces same `point_estimate` / `band_90` / `spec_hash` on 632-event PTV as MVP baseline | [ ] |
| §4.6 matching rule on synthetic | `analysis/matching_rule/matcher.py` produces deterministic flareEvent counts on the 5-patient cohort; tie-break on Stack Level deterministic | [ ] |
| End-to-end smoke (PTV → detection → flareEvent → matching → kappa) | Synthetic-exemplar input produces a posterior CI on Cohen's kappa via `analysis/bayesian_concordance/model.py` | [ ] |

**Defensible posture for Tuesday.** First two checkpoints green, third in-progress, fourth not yet started. Don't oversell.

**Honest current state (2026-05-23).** Repo has IMPLEMENTATION_PLAN only (commit `5a053d7`). Phase 0 scaffold not yet committed. **Goal between now and Tuesday: get checkpoints 1 + 2 to green.**

---

### 3. Synthetic exemplar regeneration on noarcs

**What.** Confirm the 04/23 with-arcs synthetic exemplars regeneration on the noarcs format is folded into the F2 build sequence.

**Acceptance criteria.**
- [ ] Regeneration script committed to `fixtures/synthetic_5patient/regenerate.py` (or equivalent), deterministic seed, idempotent
- [ ] Output validates against `ptv.2.1-indexed-v1-noarcs` schema
- [ ] **Regression check**: `bayesian_update_uc` produces bit-identical posteriors on the same patient through with-arcs and noarcs versions (`point_estimate`, `band_90`, `spec_hash`, `evidence_event_ids`); recorded as a CI test
- [ ] Folded into IMPLEMENTATION_PLAN Phase 4.H regression baseline; old with-arcs exemplars retired explicitly so no stale artifacts

**Why this matters.** A format-only change should be invariant to the math layer. If posteriors shift, that's a real bug — better caught now on synthetic data than after FORWARD intake.

---

### 4. Data ingestion readiness — early June arrival target

**What.** Receiving-side state report. Smallest meaningful question: *can we convert a single FORWARD WebQuest export into a schema-validated PTV record with a `metadata.pii_scrubbed` audit trail?*

**Acceptance criteria.** Status report against six items:

| Item | Owner | Acceptance |
|---|---|---|
| DUA executed (UNMC standard, Option B, 2OPMD LLC receiving entity) | Andras | [ ] Signed by ~2026-05-30 to keep early-June delivery on track |
| 2OPMD analytic environment provisioned + locked | Dylan | [ ] HIPAA-compliant env stood up; access list final; backups configured |
| 27-rule PII scrubbing pipeline live | Dylan | [ ] Pipeline runs on test input; `metadata.pii_scrubbed` audit block populates correctly per §9.4 |
| FORWARD WebQuest format adapter | Dylan | [ ] Stub adapter consumes mock CSV/JSON and emits PTV records; even with hardcoded mappings, demonstrates we can ingest |
| First-5-PTV sanity-check pipeline | Dylan | [ ] Test plan that compares production PTVs against synthetic-exemplar baselines for sanity (event counts, code-index density, instrument coverage) |
| End-to-end runs on adapter output | Dylan | [ ] `bayes.py` runs on a PTV produced by the adapter without errors |

**Honest current state (2026-05-23).** All six items not yet started in `cinder-study`. The 27-rule scrubbing exists in 2ndOpinionMD-MVP and can be lifted. The adapter is the most realistic Sat-Sun deliverable to bring to the call.

---

### 5. Read on Tuesday — what to ask Adam for

**What.** Concrete asks for Adam Cornish on data format, field selection, delivery mechanics. **This is the highest-leverage item on the call** — Adam owns the technical export side and his choices ripple through every downstream phase.

**Acceptance criteria.** A one-page brief Andras can table at the call. See **Section 2** below for the full content. Brief must address:

- [ ] Data format (encoding, dates, file structure, missing-data convention)
- [ ] Field selection — PROs, medications, comparators, demographics, wave metadata, exclusions
- [ ] Delivery mechanics (channel, cadence, naming, checksums, anonymization audit)
- [ ] Volume confirmation (N, waves/patient, total record estimate)

---

### 6. Walk-in concerns — what Andras should know before Tuesday

**What.** Five risks ranked by surface-likelihood at the call. See **Section 3** below.

**Acceptance criteria.**
- [ ] Each of the 5 risks rehearsed with Andras before the call (Monday sync if needed)
- [ ] Andras has a one-line answer ready for each in case it surfaces

---

## Section 2 — Adam asks (concrete data spec)

This is the one-pager Andras tables at the call. Cite chapter-and-verse from the protocol if pushed.

### Data format

| Item | Ask | Protocol anchor |
|---|---|---|
| Encoding | UTF-8 | n/a (industry standard) |
| Dates | ISO 8601 (`YYYY-MM-DD`); explicit timezone (UTC or America/Chicago — pick one) | §0 wave / window definitions |
| File structure | **Parquet preferred** (typed nulls, smaller, faster); CSV acceptable with explicit type schema; JSON only if needed for nested medication records | §4.1 receipt format |
| Per-wave vs aggregate | **Single export with `wave_number` + `wave_date` columns** preferred over per-wave files | §0 wave |
| Missing-data convention | NULL (Parquet) or empty string (CSV); **distinguish missing-not-reported vs never-asked** | §4.7 signal density (drives Aim 2 H2.2) |

### Field selection — PROs (must-have, item-level)

Per §4.4 MCID thresholds — item-level scores needed so we can audit Δ, not just totals:

| Instrument | Required fields | §4.4 MCID Δ |
|---|---|---|
| HAQ-II | All 8 items + total | ≥ 0.22 |
| Pain VAS | Raw 0-100 score | ≥ 20 |
| Patient Global VAS | Raw 0-100 score | ≥ 20 (also drives §4.6 OMERACT comparator) |
| RAPID3 | Composite + sub-domain scores (function, pain, patient global) | ≥ 3.6 (sub-domains needed for §4.4 RAPID3-overlap clarification) |

### Field selection — medications (per §4.5 escalation taxonomy)

- [ ] Drug name + RxNorm code
- [ ] Therapy class (DMARD / biologic / tsDMARD / corticosteroid / other)
- [ ] Start date, stop date, dose, frequency, route
- [ ] **Distinct fields for oral vs parenteral corticosteroid** (§4.5 maintenance-vs-rescue rule)
- [ ] New-prescription flag distinct from dose-change flag (§4.5 distinguishes initiation, dose increase, switch, bridge)
- [ ] Prednisone-equivalent dose if FORWARD computes it (otherwise we compute post-receipt)

### Field selection — comparators

**Clinician-rated flare (H1.1 reference standard):**
- [ ] Does FORWARD have a clinician-rated flare flag? In what wave-level field?
- [ ] If derived from physician notes — what's the extraction reliability? (Affects H1.1 floor.)
- [ ] Confidence / certainty annotation if any

**Mollard 2026 smartphone signature (H1.3):**
- [ ] Which subset of FORWARD enrollees has smartphone follow-up?
- [ ] Is the Mollard signature included as a derived field, or must we reconstruct?
- [ ] If reconstruction required: this becomes a sensitivity analysis decision; flag for Kaleb to route

### Field selection — demographics (cohort strata for `fetch_mkg_bayes_prior`)

- [ ] Age **at each wave** (not just enrollment — age bands shift)
- [ ] Sex
- [ ] ICD diagnosis code(s) per wave
- [ ] Race/ethnicity if available (fairness audit per strategy doc §7.2)

### Field selection — wave metadata + exclusions

- [ ] Per-instrument item-level missingness (signal density, §4.7)
- [ ] Continuous corticosteroid baseline indicator (§3.2 exclusion)
- [ ] Secondary autoimmune diagnosis (SLE, PsA primary) (§3.2 exclusion)
- [ ] Death / withdrawal / registry exit dates (§3.2 exclusion)

### Delivery mechanics

| Item | Ask |
|---|---|
| Channel | SFTP preferred; encrypted bucket acceptable; **never email** |
| Cadence | One-shot for N=50 cohort with §3.1 opening clause to N=200 / N=500 if FORWARD offers extension |
| File naming | `forward_cinder_v1_wave{N}_{YYYYMMDD}.parquet` or similar — wave + version stamp |
| Integrity | SHA-256 checksum per file |
| Anonymization audit | Adam confirms 27-rule scrubbing satisfied at source per §9.4; export includes `metadata.pii_scrubbed` provenance block |

### Volume confirmation

- [ ] Confirmed N=50 for primary cohort under DUA Option B
- [ ] Expected 4-6 waves per patient (per §6.1 simulation)
- [ ] Rough total record volume estimate so we can size the analytic environment

---

## Section 3 — Five things Andras should know before walking in

Ranked by likelihood of surfacing uncomfortably at the call.

### Risk 1 — Calendar pressure is real

**Surface.** §13 v3.0-FINAL gate was 2026-05-20. Today is 5/23 — three days past. Kaleb preliminary is 5/31 (8 days). ACR submission is 6/9 (17 days, needs the v3.0-FINAL commit hash for the supplemental field per §9.5).

**One-line answer if it surfaces.** "Protocol is functionally final; the v3.0-FINAL tag goes in this week pending the §13 confirmations from Dylan." Then keep moving.

### Risk 2 — DUA timing is the actual critical path

**Surface.** If early-June data is the target, the DUA needs to execute by ~2026-05-30. If Adam is technically ready and Rebecca is governance-aligned but the DUA isn't signed, none of the rest matters.

**One-line answer.** "We're tracking a 5/30 DUA execution date; can we confirm that's still on track from FORWARD's side?" Direct, specific, gives the room a number to work toward.

### Risk 3 — Mollard comparator is the technical wildcard

**Surface.** §1.6 + §4.8 frame Mollard 2026 as one of three triangulated comparators. But operationalizing it on the FORWARD smartphone subset requires either (a) Mollard's exact algorithm or (b) a reasonable reimplementation. Neither is in scope yet.

**Two-path answer.** "Either Mollard collaborates on this directly, or we demote to a smartphone-subgroup sensitivity analysis. Either is fine; what's not fine is leaving it ambiguous."

### Risk 4 — OMERACT comparator depends on Patient Global VAS field resolution

**Surface.** §4.6 OMERACT comparator = escalation in M4.A category within ±90 days AND Patient Global VAS Δ ≥ 20 in the same or immediately prior wave. If Adam's export only carries the wave-current value without wave-adjacent comparability, the indeterminate rate balloons and the comparator gets noisy.

**One-line answer.** "We need Patient Global VAS at every wave with consistent comparability — confirm that's the export shape." Easy ask.

### Risk 5 — IP posture will come up; Adam hasn't seen it before

**Surface.** §10 IP posture distinguishes open analysis pipeline (this repo) from proprietary EoH modules (M2/M3/M6/M9/M62/M63). Adam may ask "where can I see the code." Kaleb has seen this framing in KALEB_BRIEF_v2; Adam has not.

**One-line answer.** "Open analysis code, schemas, statistical methods, and comparators are public on GitHub at v3.0-FINAL tag time. The EoH proprietary modules sit in 2OPMD's private package, referenced by stable interface. Blinded external re-run is the alternative replication pathway." Then point at the cinder-study repo URL.

---

## Section 4 — Pre-call work plan

| Window | What | Owner | Acceptance |
|---|---|---|---|
| Sat 2026-05-23 evening | PTV noarcs file shared with Andras (item 1) | Dylan | File transmitted via secure channel + schema doc + checksum logged |
| Sat 2026-05-23 evening | This checklist + IMPLEMENTATION_PLAN.md update committed | Dylan | Pushed to `cinder-study` main |
| Sat 2026-05-23 evening | Phase 0 scaffold initial commit (`pyproject.toml`, schemas/, governance/, .gitignore, README) | Dylan | F2 checkpoint 1 (schemas) green |
| Sun 2026-05-24 | Vendor `bayes.py` + `uc.py` + `mkg_priors.py` from 2ndOpinionMD-MVP into `cinder/bayes/` | Dylan | F2 checkpoint 2 (vendored math layer) green; regression test passes on 632-event PTV |
| Sun 2026-05-24 evening | Response to Andras sent (covers items 1-6) | Dylan | Email out by Sunday 8 PM PT |
| Mon 2026-05-25 | Optional Andras sync — rehearse Section 3 risks, confirm Adam-asks one-pager | Andras + Dylan | Monday sync called or skipped explicitly |
| Tue 2026-05-26 1 PM CDT | FORWARD/UNMC call | Andras leads; Dylan support | Section 2 Adam asks tabled; Section 3 risks not blockers |

---

## Section 5 — After-call follow-ups

Anticipated items to track post-call (don't pre-commit; this is a placeholder for whatever surfaces):

- [ ] Adam delivers data-format spec confirmation (with revisions if FORWARD's export differs from the asks)
- [ ] DUA execution timeline locked
- [ ] Mollard comparator path decided (collaboration vs sensitivity-analysis)
- [ ] Field-selection gaps surfaced and triaged
- [ ] Any §4.6 / §4.7 / §4.5 protocol revisions required by FORWARD field reality
- [ ] v3.0-FINAL tag triggered on confirmation of remaining §13 items

---

## Honest state of the world (2026-05-23, 2 PM PT)

For internal calibration only — not for Andras's email body.

**What's actually done:**
- IMPLEMENTATION_PLAN.md committed at `5a053d7` and pushed to `cinder-study` main
- Bayesian engine analysis complete (mapped MVP commit `00eaa9eb` to CINDER reuse path)
- Test harness inheritance plan (q11-q13 + h11-h13 + c01-c04) drafted in IMPLEMENTATION_PLAN Phase 4.H

**What's not yet done in `cinder-study`:**
- Phase 0 repo scaffold (no `pyproject.toml`, no schemas/, no CI)
- `bayes.py` not yet vendored
- 27-rule PII scrubbing pipeline not lifted from 2ndOpinionMD-MVP
- 632-event PTV not yet present in `cinder-study/fixtures/`
- No tests committed
- §13 confirmation memos (matching rule, OMERACT, PyMC) not yet drafted

**What's not yet done outside `cinder-study`:**
- DUA not yet executed
- v3.0-FINAL not yet tagged (gate was 5/20)
- ACR abstract submission not yet locked

**Implication.** The Sun-evening response to Andras + Mon-Tue work is a real sprint. Doable but tight. The honest framing in the response is: "Plan is in. Phase 0 scaffold landing this weekend. F2 checkpoints 1-2 will be green by Tuesday. Adam-asks brief attached."
