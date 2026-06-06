"""flares.py - plant visible and invisible flares against M4 mechanics (§5).

A flare is a transient positive excursion ADDED to the structural trajectory over its wave,
sized so the resulting PRO deltas cross MCID in >=2 of the 3 primary domains (M4.B). The
excursion is pain/PGA-led with a marginal HAQ component (function lags) - so its modal HAQ
shift sits just over MCID 0.22 while pain/PGA carry the >=2-domain crossing (§8.2; this
reconciles the BeSt ~0.25 HAQ anchor with the 2-domain detection rule).

Two classes reflect the measurement gap (§5):
  - ``axiom_visible``   - excursion + a linked escalation event within +/-90 d -> should_detect.
  - ``axiom_invisible`` - excursion, no escalation (Mollard ~38%) -> M4 silent by design.

Trajectory-sufficiency (R3): should_detect flares need >=2 waves of lookback; a flare planted
earlier is labeled should_miss_by_design / insufficient_lookback.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import numpy as np

from cinder.synthetic.instruments import affine_true
from cinder.synthetic.latent import LatentTrajectory
from cinder.synthetic.params import GeneratorParams, StateBaseline
from cinder.synthetic.records import MedEvent
from cinder.synthetic.treatment import EscalationFact, emit_escalation

__all__ = ["FlarePlan", "PlantedFlare", "domains_shifted", "plant_flares"]

#: Visible-flare escalation-class draw (rescue burst is the most common anchor).
_VISIBLE_CLASS_WEIGHTS = {
    "gc_rescue_burst": 0.40,
    "gc_bridge_initiation": 0.18,
    "gc_bridge_ambiguous": 0.12,  # the escalation-ambiguous probe family (low confidence)
    "dose_increase": 0.12,
    "dmard_initiation": 0.10,
    "therapy_switch": 0.08,
}
_HAQ_PER_PAIN = 0.013  # HAQ-unit shift per pain-VAS unit during a flare (seed-anchored ratio)


@dataclass(slots=True)
class PlantedFlare:
    """Ground-truth record for one planted flare wave (answer-sheet per_wave row)."""

    wave_number: int
    true_flare: bool
    flare_class: str  # axiom_visible | axiom_invisible
    flare_driver: str  # RA_primary | RA_codominant | ...
    expected_M4_outcome: str  # noqa: N815 - answer-sheet schema key (§6.4); kept contract-faithful
    expected_UC_behavior: str  # noqa: N815 - answer-sheet schema key (§6.4); kept contract-faithful
    escalation: EscalationFact | None = None
    pro_domains_shifted: list[str] = field(default_factory=list)
    miss_reason: str | None = None


@dataclass(slots=True)
class FlarePlan:
    flares: list[PlantedFlare]
    med_events: list[MedEvent]


def _draw_pain_magnitude(rng: np.random.Generator, mcid_pain: float) -> float:
    """Pain-VAS excursion with mode just over MCID and a suprathreshold (severe) tail."""
    return float(mcid_pain + 2.0 + abs(rng.normal(0.0, 9.0)))


def domains_shifted(
    prev: tuple[float, float, float], cur: tuple[float, float, float], params: GeneratorParams
) -> list[str]:
    """Which primary domains crossed MCID in the worsening direction (HAQ, Pain, PGA)."""
    haq0, pain0, pga0 = prev
    haq1, pain1, pga1 = cur
    out = []
    if haq1 - haq0 >= params.mcid.haq_ii:
        out.append("HAQ-II")
    if pain1 - pain0 >= params.mcid.pain_vas:
        out.append("PainVAS")
    if pga1 - pga0 >= params.mcid.pga_vas:
        out.append("PatientGlobalVAS")
    return out


def _true_triplet(
    traj: LatentTrajectory, baseline: StateBaseline, w: int
) -> tuple[float, float, float]:
    """(HAQ, Pain, PGA) true (clipped) values at wave ``w`` - the values instruments emit."""
    return (
        float(affine_true(traj.haq_struct[w], baseline.haq_mean, baseline.haq_sd, 0.0, 3.0)),
        float(affine_true(traj.pain_struct[w], baseline.pain_mean, baseline.pain_sd, 0.0, 100.0)),
        float(affine_true(traj.pga_struct[w], baseline.pga_mean, baseline.pga_sd, 0.0, 100.0)),
    )


def _shifted_at(
    traj: LatentTrajectory, baseline: StateBaseline, params: GeneratorParams, w: int
) -> list[str]:
    """Domains crossing MCID at wave ``w`` vs ``w-1`` on the true values."""
    return domains_shifted(
        _true_triplet(traj, baseline, w - 1), _true_triplet(traj, baseline, w), params
    )


def plant_flares(
    rng: np.random.Generator,
    traj: LatentTrajectory,
    baseline: StateBaseline,
    params: GeneratorParams,
    wave_dates: list[date],
    driver: str = "RA_primary",
) -> FlarePlan:
    """Plant flares into ``traj`` (struct arrays modified in place); return ground truth.

    These facts carry the RA-intrinsic crossings/outcome (pre-comorbidity-offset). The cohort
    orchestrator RE-FINALIZES ``pro_domains_shifted`` and the outcome from the post-offset true
    values the CSVs reflect (`cohort._flare_answer`) - so a flare later masked by comorbidity
    baseline elevation becomes an honest should_miss. This function's labels are the clean-RA
    ground truth used directly only when no comorbidity offset is applied (e.g. unit tests).
    """
    n = traj.latent.shape[0]
    flares: list[PlantedFlare] = []
    meds: list[MedEvent] = []
    classes = list(_VISIBLE_CLASS_WEIGHTS)
    weights = np.array(list(_VISIBLE_CLASS_WEIGHTS.values()))
    weights = weights / weights.sum()

    last_flare_wave = -2
    for w in range(n):
        if rng.random() >= params.flares.base_flare_rate_per_wave:
            continue
        # Enforce a recovery gap: a flare is transient, so two consecutive waves never both
        # flare. Without this the prior-wave anchor ratchets PROs toward the ceiling and the
        # second flare cannot cross MCID (saturation).
        if w == last_flare_wave + 1:
            continue
        last_flare_wave = w

        # Size the excursion (pain-led; PGA co-moves; HAQ marginal). Anchor it to the prior
        # wave so the flare is a fresh worsening that reliably crosses MCID on the TRUE values
        # (a downward natural-trajectory swing cannot silently cancel a should_detect flare).
        pain_delta = _draw_pain_magnitude(rng, params.mcid.pain_vas)
        pga_delta = pain_delta * float(rng.uniform(0.9, 1.1))
        haq_delta = pain_delta * _HAQ_PER_PAIN * float(rng.uniform(0.8, 1.3))
        if w >= 1:
            traj.pain_struct[w] = (
                max(traj.pain_struct[w], traj.pain_struct[w - 1]) + pain_delta / baseline.pain_sd
            )
            traj.pga_struct[w] = (
                max(traj.pga_struct[w], traj.pga_struct[w - 1]) + pga_delta / baseline.pga_sd
            )
            traj.haq_struct[w] = (
                max(traj.haq_struct[w], traj.haq_struct[w - 1]) + haq_delta / baseline.haq_sd
            )
        else:
            traj.pain_struct[w] += pain_delta / baseline.pain_sd
            traj.pga_struct[w] += pga_delta / baseline.pga_sd
            traj.haq_struct[w] += haq_delta / baseline.haq_sd

        # Ground-truth crossings on the TRUE (pre-noise, clipped) values - the same affine map
        # the instruments emit. Computed here so ceiling-saturated flares are labeled honestly.
        shifted = _shifted_at(traj, baseline, params, w) if w >= 1 else []
        invisible = rng.random() < params.flares.invisible_fraction
        under_lookback = w < params.flares.min_lookback_wave

        if invisible:
            flares.append(
                PlantedFlare(
                    wave_number=w,
                    true_flare=True,
                    flare_class="axiom_invisible",
                    flare_driver=driver,
                    expected_M4_outcome="axiom_invisible",
                    expected_UC_behavior="widen",
                    pro_domains_shifted=shifted,
                )
            )
            continue

        # Visible: emit a linked escalation event within the M4.C window.
        planted_class = str(rng.choice(classes, p=weights))
        new_meds, fact = emit_escalation(rng, planted_class, wave_dates[w])
        meds.extend(new_meds)
        if under_lookback:
            outcome, miss = "should_miss_by_design", "insufficient_lookback"
        elif len(shifted) < 2:
            # PRO ceiling effect: patient already near the instrument ceiling, so a real flare
            # cannot produce a fresh >=2-domain crossing. M4 has the anchor but not the PRO
            # pattern -> correct non-detection (distinct from insufficient_lookback).
            outcome, miss = "should_miss_by_design", "pro_ceiling_saturation"
        else:
            outcome, miss = "should_detect", None
        uc = "widen" if fact.classification_confidence == "low" else "stable"
        flares.append(
            PlantedFlare(
                wave_number=w,
                true_flare=True,
                flare_class="axiom_visible",
                flare_driver=driver,
                expected_M4_outcome=outcome,
                expected_UC_behavior=uc,
                escalation=fact,
                pro_domains_shifted=shifted,
                miss_reason=miss,
            )
        )
    return FlarePlan(flares=flares, med_events=meds)
