---
title: Synthetic exemplar regeneration plan (with-arcs → noarcs)
status: planned
phase: 4
date: 2026-05-24
implementer: Dylan McCapes
addresses: Andras pre-call ask #3 (2026-05-23 email)
---

# Synthetic exemplar regeneration plan

## Context

The 2026-04-23 deliverable to Kaleb included a 5-patient synthetic PRO cohort built by `2ndOpinionMD-MVP/server/scripts/gen_forward_exemplar.py` and emitted under the `ptv.2.1-forward-exemplar` schema variant — a hierarchical **with-arcs** shape. The five patients are:

| Patient | Cohort role | Source file |
|---|---|---|
| P1 | Early responder | `ptv_synth_P1_early_responder.json` |
| P2 | Single-flare escalation | `ptv_synth_P2_escalation_single_flare.json` |
| P3 | Cycler with multiple flares | `ptv_synth_P3_cycler_multi_flare.json` |
| P4 | Subclinical flare, UC wins | `ptv_synth_P4_subclinical_flare_uc_wins.json` |
| P5 | Honest uncertainty under missingness | `ptv_synth_P5_honest_uncertainty_missing.json` |

The CINDER ingest contract is `ptv.2.1-indexed-v1-noarcs` (per `schemas/ptv_input.schema.json`, Phase 0 commit). The 632-event real-EHR reference fixture validates against it. The synthetic cohort does **not** validate against it — the top-level `arcs` object and the arc-grouped event nesting are not part of the noarcs contract.

Andras's 2026-05-23 ask #3:

> The 04/23 with-arcs synthetic exemplars need regeneration on noarcs as part of F2. Confirm this is folded into your build sequence so we're not surprised by stale artifacts later.

This memo confirms it is folded in, names where in the build sequence it lands, and specifies acceptance criteria so the regenerated artifacts can be verified against the same five clinical scenarios the original cohort encoded.

## What needs to change in the schema shape

| with-arcs (old) | noarcs (new) | Transformation |
|---|---|---|
| `root.arcs.<arc_id>.event_ids: [...]` | `root.events.<event_id>: {...}` | Flatten: each event is a top-level keyed entry; arc membership is dropped |
| Arc-level `name`, `summary`, `open_questions`, `cross_arc_edges` | `metadata.entities.<entity_key>` (where applicable) and per-event `connascence` arrays | Convert arc bookkeeping into per-event connascence relations; preserve narrative summaries on the entity registry only when they correspond to a canonical entity (e.g., `icd:m05`) |
| `root.events.<eid>.arc_membership: [arc_id, ...]` | `root.events.<eid>.connascence.same_chapter: [peer_eid, ...]` | Convert arc co-membership into the existing `connascence.same_chapter` relation kind already present in noarcs |
| `cross_arc_edges` between arcs | Per-event `connascence.<relation_kind>: [peer_eid, ...]` for the shared events | Edge groups become per-event peer arrays; the relation kind is preserved (`pro_shift`, `flare_window`, `therapy_episode`, `caused_by`, `in_workup_for`) |
| Top-level `arcs` key | (removed) | Drop entirely |
| `metadata.schema_version: "ptv.2.1-forward-exemplar"` | `metadata.schema_version: "ptv.2.1-indexed-v1-noarcs"` | Re-tag |
| `metadata.synthetic: true`, `metadata.disclaimer: "..."`, `metadata.generator.seed: <int>` | Same — preserved verbatim | Synthetic provenance is part of the regenerated artifact identity |

Connascence relation kinds present in the source cohort (`pro_shift`, `flare_window`, `therapy_episode`, `in_workup_for`, `caused_by`) are all permitted in `ptv_input.schema.json::events.<eid>.connascence` (the schema is permissive on relation kind because they are extractor-defined). No schema amendment is required.

## What does **not** change

- **Patient IDs, event IDs, dates, PRO scores, medication records.** All clinical content is preserved verbatim. The five clinical scenarios encoded in the cohort (early responder, escalation flare, cycler, subclinical flare, honest uncertainty under missingness) are properties of the event-level data, not of the arc structure.
- **Determinism.** Seeds per patient (`metadata.generator.seed`) are preserved. Re-running the regenerator with the same seeds produces bit-identical output.
- **PII status.** Synthetic cohort has no PII to scrub; `metadata.pii_scrubbed` is added to satisfy `schemas/ptv_input.schema.json` and the PII tripwire, with `scrubber: "synthetic_no_pii"` and an integer `rules_applied: 0`. This is documented in the regenerator code and in the manifest.

## Implementation path

The regenerator lives in CINDER, not in the MVP repo, so the synthetic cohort becomes part of the open replication corpus per §10. Two-stage approach:

### Stage A — emit-side adapter (`scripts/regenerate_synthetic_exemplars.py`)

A single Python script in `cinder-study/scripts/`. Inputs: the five with-arcs JSON files (preserved as read-only inputs in `fixtures/synthetic_5pt_with_arcs_20260423/`). Outputs: five noarcs JSON files in `fixtures/synthetic_5pt/`. The script:

1. Loads each with-arcs PTV.
2. Walks `arcs` to extract co-membership relations.
3. Reshapes `events` into the flat `{<event_id>: {...}}` keying.
4. Writes per-event `connascence` arrays from arc co-membership and `cross_arc_edges`.
5. Re-tags `metadata.schema_version` and adds the synthetic-no-PII tripwire block.
6. Validates the output against `schemas/ptv_input.schema.json`.
7. Emits a per-file diff manifest (`fixtures/synthetic_5pt/REGENERATION_MANIFEST.md`) recording (a) source file SHA-256, (b) output file SHA-256, (c) event count, (d) connascence relation count, (e) regenerator commit hash.

This is a one-shot transform. The script is ~150 lines, runnable in seconds, and is itself a CINDER artifact — not a 2OPMD MVP script.

### Stage B — verification harness (`tests/regression/test_synthetic_exemplars.py`)

For each of the five regenerated noarcs PTVs:

1. Validates against `schemas/ptv_input.schema.json` (already ensured by Stage A; this test is the regression backstop).
2. Asserts the event count matches the source (no events dropped).
3. Asserts the patient IDs, event IDs, dates, and PRO scores match the source verbatim.
4. Once the Bayes layer is vendored (Phase 4.A), runs `cinder.bayes` against each PTV and asserts the resulting posterior matches a recorded fixture-stable baseline (deterministic under `seed=2026`). This is the "F2 regression harness on synthetic data" — the per-patient detection layer running on every cohort member with a stable, replayable answer.

Stage B step 4 is the part that depends on Bayes vendoring. Stages A through B-step-3 do not.

## Schedule

The plan slots into the build sequence after Bayes vendoring (locked decision per `IMPLEMENTATION_PLAN.md` "Decisions locked"). Specifically:

| Sequence | Phase | Item | Synthetic-cohort dependency |
|---|---|---|---|
| 1 | Phase 4.A | Vendor `cinder.bayes` from `2ndOpinionMD-MVP@00eaa9eb` | none |
| 2 | Phase 4.B | F2 regression harness on the 632-event real-EHR fixture | none |
| 3 | **Phase 4.D** | **Run `regenerate_synthetic_exemplars.py`; commit `fixtures/synthetic_5pt/`** | this memo |
| 4 | Phase 4.D | Extend F2 regression harness to the 5-patient synthetic cohort | step 3 done |
| 5 | Phase 2 | §6 sample-size simulation runs against the regenerated cohort | step 4 done |

Stage A runs on a 24-hour clock once Bayes vendoring lands. Stage B step 4 (posterior baseline) runs on a 72-hour clock after Stage A.

## Stale-artifact prevention

Three mechanisms prevent the with-arcs and noarcs synthetic artifacts from getting confused downstream:

1. **Filesystem segregation.** `fixtures/synthetic_5pt_with_arcs_20260423/` (frozen, read-only inputs) versus `fixtures/synthetic_5pt/` (live noarcs outputs). The directory name itself encodes the schema variant.
2. **`.gitignore` glob protection.** A pattern `*_with_arcs_*` is added to `.gitignore` to guard against accidental commits of with-arcs artifacts elsewhere in the tree (the frozen input directory is an explicit `!fixtures/synthetic_5pt_with_arcs_20260423/` un-ignore).
3. **Per-file schema self-tag.** Every regenerated noarcs PTV carries `$schema_ref: "ptv_input.schema.json"` (per `ptv_input.schema.json` optional self-tag field), so `scripts/validate_schemas.py` dispatches the correct validator and rejects any with-arcs file that strays into a noarcs path.

## Acceptance criteria (Phase 4.D close)

The synthetic exemplar regeneration is closed when all of the following are true:

- `scripts/regenerate_synthetic_exemplars.py` exists and is invoked in CI.
- All five regenerated PTVs validate against `schemas/ptv_input.schema.json` (`scripts/validate_schemas.py fixtures/synthetic_5pt/`).
- `tests/regression/test_synthetic_exemplars.py` passes Stage B steps 1-3 (event count, patient IDs, scores).
- Once Phase 4.A is in: Stage B step 4 records a baseline posterior per patient under `seed=2026` and a regression test re-asserts bit-stable output.
- `fixtures/synthetic_5pt/REGENERATION_MANIFEST.md` records source/output SHA-256 pairs for all five patients.
- `governance/pre_registration_log.md` Phase 4 row references this memo as completed.

## Why this is folded into Phase 4 and not earlier

Two reasons. First, the regenerated cohort is most useful as input to the F2 regression harness, which itself depends on `cinder.bayes` being vendored — there is no value in regenerating a cohort that has nothing to consume it yet. Second, regenerating now would produce an artifact pinned to the current schema, but the schema is still mutable until v3.0-FINAL tag (e.g., the §13.2/§13.3 caveats from the Tuesday FORWARD/UNMC call could still force a `cinder_pro` micro-revision). Regenerating once after Bayes vendoring and after v3.0-FINAL tag avoids one round of artifact churn.

The trade-off is that the synthetic cohort is unavailable in noarcs form until late Phase 4. For Andras's pre-call concern ("we're not surprised by stale artifacts later"), the answer is: the artifacts are already segregated by directory and `.gitignore`-protected, and the regeneration is a documented, scheduled, and verifiable step — not a thing that gets discovered three months from now.

## Approval

| Role | Name | Date | Commit |
|---|---|---|---|
| Implementer | Dylan McCapes | 2026-05-24 | `<FILL AT COMMIT>` |
| Senior approver | Andras Hangyal | pending | — |
