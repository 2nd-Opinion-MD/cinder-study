---
title: §13.2 Confirmation — Comparator Event Matching Rule (§4.6)
status: confirmed_with_caveats
phase: 1
gate: §13.2
date: 2026-05-24
implementer: Dylan McCapes
senior_approver: Andras Hangyal (pending)
---

# §13.2 Confirmation — Comparator Event Matching Rule

## Question (verbatim §13.2)

> Dylan confirms operational implementation of the §4.6 matching rule is consistent with the PTV schema and available FORWARD export fields.

## Answer

**Yes — implementable as written, with two named caveats both contingent on Adam Cornish's 2026-05-26 confirmations.**

The §4.6 rule decomposes into six operationally distinct sub-rules. Each maps cleanly onto the published `schemas/flare_event.schema.json` and `schemas/ptv_input.schema.json` contract. The matching logic itself lands in `analysis/matching/match_comparators.py` (Phase 4.C). No protocol revision is required.

## Evidence

### Sub-rule 1: Unit of analysis (±90-day observation window)

**Protocol text.** *"The unit of analysis is the observation window: a ±90-day interval centered on a candidate signal event."*

**Implementation.** Date arithmetic on `events.{event_id}.timestamp` (ISO 8601 per `ptv_input.schema.json`). Candidate signal events anchor windows; comparator events are evaluated for membership in `[t - 90d, t + 90d]`. The window size is parameterized per `flare_event.schema.json::window_size_days` (`enum: [60, 90, 120]`) so primary (90) and sensitivity (60, 120) windows share the same matching code path. Verifiable: 462 of 632 events in the reference PTV carry valid ISO dates; the remaining 168 (`unknown`) and 2 (`[DOB_REDACTED]`) are non-anchorable and excluded from window evaluation per §4.4 candidate-signal definition (which requires a wave-anchored timestamp).

**No gap.**

### Sub-rule 2: One-to-one matching, primary vs secondary

**Protocol text.** *"Each CINDER flareEvent is matched to at most one comparator reference event per comparator. If multiple comparator reference events fall within the same detection window, the temporally nearest is designated the primary match; remaining events within the window are recorded as secondary associations in the exploratory log only."*

**Implementation.** `flare_event.schema.json::comparator_matches.{clinician_rated, omeract, mollard_smartphone}` already encodes the primary/secondary split via `matched: bool` + `comparator_event_id: string|null` + `match_offset_days: integer|null`. Secondary associations are recorded in `escalation_bundle.secondary_escalation_event_ids: array<string>`. The matching algorithm is:

```
for each detection D in cinder_flare_events:
  candidates = comparator_events
              .filter(|t_C - t_D| <= 90)
              .sort_by(|t_C - t_D|)
  primary = candidates[0] if candidates else None
  secondary = candidates[1:]
```

Deterministic, ≤O(N·M) where N = detection count and M = comparator count per window. Acceptable for N ≈ 50 patients × 4-6 waves × few candidates per wave.

**No gap.**

### Sub-rule 3: Unmatched detections → false positives

**Protocol text.** *"Unmatched CINDER detections (CINDER fires; comparator is silent) are counted as false positives in sensitivity/specificity tables and as potential additional detections in the exploratory disagreement characterization."*

**Implementation.** A flareEvent record with `comparator_matches.<comparator>.matched = false` flows into both:
- The 2×2 agreement table fed to the §4.8 PyMC concordance model (counted as FP under that comparator's reference standard).
- The exploratory disagreement log (`analysis/aim2/disagreement_characterization.py`, Phase 7) for descriptive analysis per §5.2 ("disagreement is characterized rather than averaged away," §4.8 comparator triangulation).

**No gap.**

### Sub-rule 4: Unmatched comparators → misses

**Protocol text.** *"Unmatched comparator events (comparator fires; CINDER is silent) are counted as misses in sensitivity analysis."*

**Implementation.** Inverse of sub-rule 3: comparator events with no detection within ±90 days produce a "miss" row in the 2×2 table (FN). Schema-wise, these don't generate a `flare_event.schema.json` record (since no CINDER detection happened); they're tracked in a parallel `unmatched_comparator_events` log written by `analysis/matching/match_comparators.py`.

**No gap** — but flag: the unmatched-comparator log is a new artifact not yet schematized. Recommend adding `schemas/unmatched_comparator.schema.json` in Phase 4.C alongside `match_comparators.py`. Trivial schema (date, comparator type, source event ID, reason for unmatched).

### Sub-rule 5: Tie-breaking (Stack Level → temporal proximity)

**Protocol text.** *"When two CINDER candidate signal events fall within the same escalation window, the event with the higher Stack Level (more domains shifted above band) is designated primary. Ties on Stack Level are broken by temporal proximity to the escalation event."*

**Implementation.** `flare_event.schema.json::domain_shift_bundle.stack_level: integer (≥2)` and `temporal_offset_days: integer` are the two fields the tie-breaker reads. Algorithm:

```
candidates_for_escalation_E = cinder_flare_events
  .filter(|t_C - t_E| <= 90)
  .sort_by(stack_level desc, |t_C - t_E| asc)
primary = candidates[0]
```

**No gap.**

### Sub-rule 6: Cross-comparator alignment

**Protocol text.** *"The same ±90-day windowing logic applies across all three comparators. The Mollard smartphone comparator uses daily-granularity native timestamps; Mollard events are collapsed to the nearest semi-annual FORWARD wave for alignment with the PRO-based matching rule. OMERACT comparator events are derived from FORWARD data fields directly."*

**Implementation.**
- **Clinician-rated.** Direct: comparator events come from a FORWARD field (asks line 156, pending Adam confirmation). Single ±90 window per detection.
- **OMERACT.** Derived from FORWARD `Patient Global VAS` + `escalation event` fields per §4.6 OMERACT spec. Implementation lives in `analysis/matching/omeract_comparator.py`. See `confirmation_omeract.md` for the operational specification.
- **Mollard smartphone.** Two-step: (a) daily-granularity smartphone events are aggregated into wave-equivalent buckets; (b) wave-bucket events feed the same ±90-day matching engine. The collapse is `wave_bucket = nearest_forward_wave_date(smartphone_event_date)`. `flare_event.schema.json::comparator_matches.mollard_smartphone.applicable: boolean` flags subgroup membership.

**No gap on the matching logic itself.** Two named caveats below.

## Caveats (Adam-dependent)

### Caveat 1: Clinician-rated comparator — FORWARD field availability TBD

**Problem.** §4.6 sub-rule 1 (clinician-rated comparator) assumes a wave-level "clinician-rated flare" flag in the FORWARD export. `PRE_CALL_CHECKLIST.md` §2 line 156 explicitly raises this as an Adam ask: *"Does FORWARD have a clinician-rated flare flag? In what wave-level field?"*

**Three branches.**
1. **FORWARD has a single clinician-rated flare field** → direct mapping to `comparator_matches.clinician_rated`. No protocol change.
2. **FORWARD has component fields** (e.g., physician global assessment + tender/swollen joint counts + DAS28) but no aggregate flare flag → CINDER derives a clinician-rated flag from these per a documented operational rule (e.g., DAS28 > 5.1, or PhGA Δ ≥ 20 with concomitant medication change). Document derivation in `docs/clinician_comparator_derivation.md`. Protocol §4.6 amended once via micro-revision before v3.0-FINAL tag.
3. **FORWARD has neither** → primary comparator collapses to OMERACT-only; H1.1 reframed against OMERACT as primary reference rather than clinician-rated. Protocol §1.4 + §4.8 + §5.1 require revision. **This is a material change.** Surface to Andras immediately if Adam reports this on Tuesday.

**Recommendation.** Tuesday call ask to Adam: *"What's the wave-level data structure for clinician assessment of disease activity? Is there a discrete flare flag, or do we derive one?"* That single question selects the branch.

### Caveat 2: Mollard smartphone subgroup size unknown

**Problem.** §4.6 sub-rule 6 + §4.8 comparator triangulation assume a non-trivial smartphone-equipped subgroup within FORWARD. `PRE_CALL_CHECKLIST.md` §2 lines 161-162 raise this: *"Which subset of FORWARD enrollees has smartphone follow-up?"* Subgroup size determines whether Mollard is a primary comparator (≥ 30 patients with adequate smartphone density) or a sensitivity-analysis aside.

**Three branches.**
1. **Subgroup ≥ 30 patients with regular smartphone density** → Mollard runs as a third primary comparator per §4.8 triangulation as written. No protocol change.
2. **Subgroup < 30 patients** → Mollard demoted to a §4.8 Sensitivity Analysis 4 (smartphone subgroup) and removed from primary triangulation. Protocol §4.8 + §5.2 micro-revision.
3. **Subgroup ≈ 0** → Mollard removed entirely; comparator triangulation becomes two-way (clinician-rated + OMERACT). Protocol §4.8 + §5.2 + §1.4 revision.

**Recommendation.** Tuesday call ask to Adam: *"How many FORWARD participants have smartphone follow-up data with daily granularity over the analysis window?"* That number drives the branch selection. Independent of branch, the matching rule code path is the same; only the comparator's primary/sensitivity-analysis status changes.

## Net assessment

The §4.6 matching rule is **structurally sound and code-implementable as written**. Both caveats are about which comparator(s) feed the matching engine, not about the matching logic itself. Caveat 2 (Mollard subgroup) is low risk for the protocol's primary endpoint — the core H1.1 hypothesis stands on clinician-rated concordance. Caveat 1 (clinician-rated field) is the only one that could force material §1.4/§4.8/§5.1 revisions before v3.0-FINAL, and only under branch 3.

**Recommend tagging §13.2 as confirmed** and proceeding to Phase 3 once Adam's Tuesday answer resolves the two caveats. If branch 3 fires on Caveat 1, halt and revise; otherwise proceed.

## Proposed code path (for §10 open-implementation commitment)

```
analysis/
  matching/
    __init__.py
    match_comparators.py           # entry point; dispatches per comparator
    clinician_rated_comparator.py  # branches 1/2/3 of Caveat 1
    omeract_comparator.py          # see confirmation_omeract.md
    mollard_collapse.py            # daily → wave bucket transformation
    tie_breaker.py                 # Stack Level + temporal proximity
schemas/
  unmatched_comparator.schema.json # NEW; flagged in sub-rule 4
```

## Approval

| Role | Name | Date | Commit |
|---|---|---|---|
| Implementer | Dylan McCapes | 2026-05-24 | `<FILL AT COMMIT>` |
| Senior approver | Andras Hangyal | pending | — |
