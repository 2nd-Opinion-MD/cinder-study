---
title: §13.3 Confirmation — OMERACT Comparator Operational Specification (§4.6)
status: confirmed_with_caveats
phase: 1
gate: §13.3
date: 2026-05-24
implementer: Dylan McCapes
senior_approver: Andras Hangyal (pending)
---

# §13.3 Confirmation — OMERACT Comparator Operational Specification

## Question (verbatim §13.3)

> Dylan confirms the §4.6 OMERACT specification is implementable from FORWARD Patient Global VAS and medication fields.

## Answer

**Yes — implementable as written, conditional on three FORWARD field characteristics that Adam Cornish should confirm on the 2026-05-26 call.**

The OMERACT spec is the cleanest of the three comparators — it derives entirely from FORWARD data fields (no third-party data, no derived signal that requires algorithmic reconstruction). The three conditional fields are all in our standard ask list.

## Evidence — what the spec requires

Protocol §4.6 OMERACT operational specification (verbatim):

> An observation window is classified as a comparator flare event if (1) a care escalation event in any M4.A category occurred within the ±90-day window AND (2) Patient Global VAS exceeded the prior-wave value by ≥ 20 points in the same wave or the immediately adjacent prior wave.

Plus:

> Cases where escalation is present but Patient Global VAS worsening is absent or undocumented are classified as indeterminate and excluded from OMERACT comparator concordance calculations (not counted as flare or non-flare); they are reported as a separate indeterminate rate.

Three FORWARD field requirements derive from this:

| FORWARD field requirement | Used for | Risk if unavailable |
|---|---|---|
| Patient Global VAS (0–100), every wave, comparable wave-to-wave | Sub-clause (2): the ≥ 20-point worsening test against prior-wave value | Indeterminate rate balloons; OMERACT degrades to noise |
| Medication start/stop dates with RxNorm + dose + route | Sub-clause (1): M4.A escalation taxonomy classification per §4.5 | Cannot extract escalation events at all; OMERACT collapses |
| Distinct oral vs parenteral corticosteroid fields, with prednisone-equivalent dose | §4.5 maintenance-vs-rescue rule | Rescue bursts incorrectly classified as maintenance escalations |

## Sub-question 1: Patient Global VAS shift detection in available wave granularity

**Protocol requirement.** ≥ 20-point worsening from prior-wave value, evaluated *in the same wave or the immediately adjacent prior wave* relative to the escalation event.

**Implementation.** The OMERACT detector reads Patient Global VAS scores at every wave for every patient and computes Δ = `vas[wave_n] - vas[wave_{n-1}]`. If Δ ≥ 20, the wave triggers the OMERACT criterion (2). Wave granularity is FORWARD's native semi-annual cadence (per §0 wave definition); §4.4 MCID Δ ≥ 20 is the same threshold the per-patient detection layer uses, so the comparator and the detector compute on identical input shape.

**PTV schema mapping.** Patient Global VAS scores land in:

```json
events.<eid>.annotations.cinder_pro.{
  "instrument": "PatientGlobalVAS",
  "score": <number>,
  "wave_number": <int>,
  "wave_date": "YYYY-MM-DD",
  "delta_from_baseline": <number|null>,
  "exceeds_band": <boolean|null>
}
```

Per `schemas/ptv_input.schema.json` (Phase 0 commit). The OMERACT detector reads `score` + `wave_number` directly; M3-derived `delta_from_baseline` and `exceeds_band` are optional metadata that the OMERACT logic does **not** depend on (deliberately — OMERACT is the simpler, purely-FORWARD comparator).

**Wave-adjacency definition.** "Immediately adjacent prior wave" = the wave with the largest `wave_date` < target wave's `wave_date`. Trivial sort and lookup.

**Caveat A (Adam-dependent).** Two FORWARD-side conditions must hold:
1. **Coverage.** Patient Global VAS recorded at every wave for every patient. If FORWARD allows wave-level missingness for VAS (some patients skip questionnaire items), the indeterminate rate climbs.
2. **Comparability.** Wave-to-wave VAS values must be in the same scale. Standard FORWARD instrument; should be invariant. Risk is purely a data-completeness question.

**Recommendation.** Tuesday ask to Adam: *"What's the wave-level non-response rate for Patient Global VAS? Is it consistent across the requested 4-6 wave window per patient?"* If non-response > 30% in any wave, OMERACT comparator's signal-to-noise degrades; if > 50%, OMERACT becomes uninformative and protocol §5.2 needs micro-revision (demote OMERACT to descriptive only).

## Sub-question 2: Medication-change field resolution against §4.5 escalation taxonomy

**Protocol requirement.** Each medication record must be classifiable into one of the seven M4.A categories: DMARD initiation, biologic initiation, tsDMARD initiation, corticosteroid rescue burst, dose increase, therapy switch, bridge therapy.

**Implementation.** The classifier reads three fields per medication record:

| Required field | Used for |
|---|---|
| Drug name + RxNorm code | Therapy class lookup (DMARD vs biologic vs tsDMARD vs corticosteroid vs other) via the existing `metadata.code_index.rxnorm` and `metadata.entities` lookups in the PTV schema, plus a static drug-class table in `analysis/detection/drug_class_lookup.yaml` (Phase 4.D) |
| Start date | Initiation classification (no prior record of same drug → initiation; vs continuation) |
| End date / stop date | Therapy switch detection (drug A ends within ±30 days of drug B starts of the same therapy class → switch) |

**Schema mapping.** All three required fields are already first-class in `schemas/escalation_event.schema.json::drug.{name, rxnorm_code, therapy_class, dose, dose_unit, frequency, route}` plus `is_initiation`, `is_dose_change`, and `escalation_date` at the top level. Phase 0 schema work anticipated this.

**Caveat B (Adam-dependent).** Two FORWARD-side conditions must hold:
1. **RxNorm coverage.** Medications coded with RxNorm (or a mappable internal code). PRE_CALL_CHECKLIST §2 line 145 confirms this is on the ask list.
2. **Date completeness.** Start date present on every medication record. Stop date present when applicable (drug discontinued or switched). PRE_CALL_CHECKLIST §2 line 146 confirms this is on the ask list.

**Recommendation.** Tuesday ask to Adam: *"For medication records — coded with RxNorm directly, or with an internal code we'd need a crosswalk for? And are start/stop dates present at row-level granularity?"* If RxNorm is missing, we ask for the FORWARD internal-code crosswalk; if missing-stop-dates are common (some drugs are recorded as ongoing without explicit stop), we operationalize "no stop date" as "active through the most recent wave date" — that's a documented assumption, not a blocker.

## Sub-question 3: Maintenance-vs-rescue rule (§4.5) implementability

**Protocol requirement (§4.5, verbatim).**

> In the FORWARD medication export, corticosteroid rescue bursts are operationalized as oral prednisone (or equivalent) doses ≥ 10 mg/day for ≤ 14 days, OR parenteral corticosteroid administration, occurring in a wave where the prior two waves show either no corticosteroid use or a dose below the rescue threshold. Continuous maintenance regimens are flagged when prednisone-equivalent doses ≤ 7.5 mg/day appear in three or more consecutive prior semi-annual waves without documented dose change; these are excluded from the escalation event category.

**Implementation.** Encoded as a state machine in `analysis/detection/maintenance_vs_rescue.py` (Phase 4.D) reading the patient's full corticosteroid medication history per wave. State transitions:

```
NONE → MAINTENANCE  (≤7.5 mg/day for ≥3 consecutive waves)
NONE → RESCUE       (≥10 mg/day for ≤14 days OR parenteral)
MAINTENANCE → RESCUE (dose increase to ≥10 mg/day after stable maintenance)
RESCUE → MAINTENANCE (dose drop to ≤7.5 mg/day for ≥3 waves)
ANY → AMBIGUOUS     (mid-state increase or decrease)
```

The state machine emits `escalation_event.schema.json::maintenance_vs_rescue.classification: enum["rescue_burst","maintenance_regimen","ambiguous_resolved","not_applicable"]`. Ambiguous events are routed via M6 arbitration per §4.5 (proprietary 2OPMD logic; arbitration outcome recorded in `m6_arbitration_label`).

**Schema mapping.** All required fields are already in `escalation_event.schema.json::maintenance_vs_rescue` (Phase 0 commit anticipated this).

**Caveat C (Adam-dependent).** The implementation requires:
1. **Distinct oral vs parenteral corticosteroid fields.** PRE_CALL_CHECKLIST §2 line 149 confirms this is on the ask list.
2. **Dose with units (mg/day).** PRE_CALL_CHECKLIST §2 line 148 confirms this is on the ask list.
3. **Prednisone-equivalent dose.** Optional — if FORWARD provides it, we use it directly; if not, we compute it post-receipt using a static drug-equivalence table (`analysis/detection/steroid_equivalents.yaml`). Either way, this is not a blocker.

**Recommendation.** Tuesday ask to Adam: *"For corticosteroids — distinct fields for oral vs parenteral? And does FORWARD record prednisone-equivalent doses, or do we compute that?"* Fallback (compute equivalents post-receipt) is straightforward; only the oral vs parenteral distinction is a real dependency.

## Sub-question 4: Indeterminate classification handling

**Protocol requirement.** Cases where escalation is present but Patient Global VAS worsening is absent or undocumented → indeterminate, excluded from OMERACT concordance, reported as separate rate.

**Implementation.** Three-way classifier in `analysis/matching/omeract_comparator.py`:

```python
def classify_omeract(window) -> Literal["flare", "no_flare", "indeterminate"]:
    has_escalation = bool(window.escalation_events)
    vas_data = window.patient_global_vas_history
    if not has_escalation:
        return "no_flare"
    if vas_data is None or vas_data.has_gaps_in_window():
        return "indeterminate"  # absent or undocumented
    if vas_data.delta_from_prior_wave >= 20:
        return "flare"
    return "no_flare"  # escalation but no VAS worsening
```

`flare_event.schema.json::comparator_matches.omeract.indeterminate: boolean` flags the indeterminate case explicitly; the indeterminate rate (count of indeterminate windows / total windows with escalation) is reported in `analysis/matching/omeract_indeterminate_rate.md` (Phase 4.C).

**No gap.** Schema and analysis paths are already designed in.

## Net assessment

The §4.6 OMERACT specification is **structurally sound and code-implementable as written**. All three caveats (A: VAS coverage, B: medication field resolution, C: oral/parenteral distinction) are deliverable in Adam's standard FORWARD export shape; none has identified a likely "no" answer.

The single highest-risk caveat is **Caveat A's coverage assumption**: if FORWARD's wave-level Patient Global VAS non-response rate is high, the indeterminate rate of OMERACT can swallow the comparator. This is the same risk surfaced in `PRE_CALL_CHECKLIST.md` §3 Risk 4. Tuesday call resolves it.

**Recommend tagging §13.3 as confirmed** and proceeding to Phase 3 once Adam's Tuesday answer confirms the three conditions. No protocol revision is needed under any branch where (A) coverage > 70%, (B) RxNorm or crosswalk available, (C) oral/parenteral distinction present.

## Proposed code path

```
analysis/
  matching/
    omeract_comparator.py           # three-way classifier (flare/no_flare/indeterminate)
    omeract_indeterminate_rate.md   # post-Phase-4 report
  detection/
    drug_class_lookup.yaml          # static RxNorm → therapy class table
    maintenance_vs_rescue.py        # §4.5 state machine
    steroid_equivalents.yaml        # static prednisone-equivalent dose table (fallback if FORWARD doesn't compute)
schemas/
  (no new schemas needed — flare_event + escalation_event already cover OMERACT outputs)
```

## Approval

| Role | Name | Date | Commit |
|---|---|---|---|
| Implementer | Dylan McCapes | 2026-05-24 | `<FILL AT COMMIT>` |
| Senior approver | Andras Hangyal | pending | — |
