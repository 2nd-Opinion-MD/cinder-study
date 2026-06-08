"""cohort.py - the orchestrator (§5 end-to-end).

For each patient: draw demographics -> disease-activity state -> latent trajectory -> plant
flares -> apply comorbidity masking -> map to instruments -> assemble a `PatientRecord` (the
three CSVs) and a `PatientAnswer` (per-wave ground truth). Deterministic under a single seed
(C6): every draw comes from the patient's `CohortRNG` substream in fixed order, and all dates
derive from a fixed base date (no wall-clock).
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np

from cinder.synthetic.answer_sheet import PatientAnswer, WaveAnswer, escalation_to_dict
from cinder.synthetic.comorbidity import apply_comorbidity_offset, assign_comorbidity
from cinder.synthetic.flares import PlantedFlare, domains_shifted, plant_flares
from cinder.synthetic.instruments import WaveScores, map_to_instruments
from cinder.synthetic.latent import draw_latent_trajectory
from cinder.synthetic.params import GeneratorParams, default_params
from cinder.synthetic.records import MedEvent, PatientRecord, PROObservation, Wave
from cinder.synthetic.rng import CohortRNG
from cinder.synthetic.treatment import emit_maintenance_dmard

__all__ = ["generate_cohort"]

#: Fixed study-start anchor - keeps wave dates deterministic (no wall-clock).
_BASE_DATE = date(2020, 1, 15)


def _choose_state(gen: np.random.Generator, params: GeneratorParams) -> str:
    states = list(params.state_mixture.weights)
    w = np.array([params.state_mixture.weights[s] for s in states])
    return str(gen.choice(states, p=w / w.sum()))


def _wave_dates(gen: np.random.Generator, n: int, params: GeneratorParams) -> list[date]:
    start = _BASE_DATE + timedelta(days=int(gen.integers(0, 120)))
    dates = [start]
    for _ in range(1, n):
        step = params.waves.interval_days + int(
            gen.integers(-params.waves.jitter_days, params.waves.jitter_days + 1)
        )
        dates.append(dates[-1] + timedelta(days=step))
    return dates


def _pro_rows(scores: WaveScores, emit_subscores: bool) -> list[PROObservation]:
    rows = [
        PROObservation("HAQ-II", scores.haq_ii),
        PROObservation("PainVAS", scores.pain_vas),
        PROObservation("PatientGlobalVAS", scores.pga_vas),
        PROObservation("RAPID3", scores.rapid3),
    ]
    if emit_subscores:
        rows += [
            PROObservation("RAPID3_FN", scores.rapid3_fn),
            PROObservation("RAPID3_PN", scores.rapid3_pn),
            PROObservation("RAPID3_PtGA", scores.rapid3_ptga),
        ]
    return rows


def _flare_answer(
    w: int,
    fl: PlantedFlare,
    final_shifted: list[str],
    cur_true: tuple[float, float, float],
    is_comorbid: bool,
    params: GeneratorParams,
) -> WaveAnswer:
    """Build a flare wave's answer, re-deriving the outcome from the FINAL crossings.

    A planted RA flare is ``should_detect`` only if it crosses >=2 PRO domains on BOTH the
    RA-intrinsic trajectory (``fl.pro_domains_shifted``, pre-comorbidity-offset) AND the emitted
    trajectory (``final_shifted``, post-offset), carries a linked anchor escalation, and has
    sufficient lookback (R3). Requiring both crossings closes two failure modes symmetrically:

      * comorbidity baseline elevation COMPRESSES a real >=2-domain flare below threshold on
        the emitted trajectory -> ``masked_by_comorbidity`` (a true miss, not a labeling error);
      * comorbidity baseline elevation MANUFACTURES an apparent >=2-domain crossing on a wave
        whose inflammatory flare is itself subthreshold -> ``comorbidity_confounded`` (banking
        it would be a non-inflammatory false positive, so M4 should miss by design).

    Otherwise it is an honest ``should_miss_by_design`` with the reason it could not be
    detected: insufficient_lookback, pro_ceiling_saturation, masked_by_comorbidity,
    comorbidity_confounded, or subthreshold. Invisible flares stay ``axiom_invisible``.
    """
    if fl.flare_class == "axiom_invisible":
        return WaveAnswer(
            wave_number=w,
            true_flare=True,
            flare_class="axiom_invisible",
            flare_driver=fl.flare_driver,
            pro_domains_shifted=final_shifted,
            expected_M4_outcome="axiom_invisible",
            expected_UC_behavior="widen",
            miss_reason=None,
        )
    esc = fl.escalation
    # RA-intrinsic crossings: what the flare did to the trajectory BEFORE any comorbidity
    # offset. final_shifted is the post-offset (emitted) crossing the CSVs reflect.
    intrinsic_shifted = fl.pro_domains_shifted
    if w < params.flares.min_lookback_wave:
        outcome, miss = "should_miss_by_design", "insufficient_lookback"
    elif len(intrinsic_shifted) >= 2:
        # The inflammatory flare itself crosses >=2 domains; detectable UNLESS comorbidity
        # baseline elevation has since compressed the emitted wave-to-wave delta below the line.
        if len(final_shifted) >= 2:
            outcome, miss = "should_detect", None
        else:
            outcome, miss = "should_miss_by_design", "masked_by_comorbidity"
    elif cur_true[1] >= 99.0 or cur_true[2] >= 99.0:
        outcome, miss = "should_miss_by_design", "pro_ceiling_saturation"
    elif is_comorbid and len(final_shifted) >= 2:
        # Apparent >=2-domain crossing is driven by non-inflammatory comorbidity elevation, not
        # the (subthreshold) RA flare. Detecting it would be a false positive -> miss by design.
        outcome, miss = "should_miss_by_design", "comorbidity_confounded"
    else:
        outcome, miss = "should_miss_by_design", "subthreshold"
    uc = "widen" if (esc is not None and esc.classification_confidence == "low") else "stable"
    return WaveAnswer(
        wave_number=w,
        true_flare=True,
        flare_class="axiom_visible",
        flare_driver=fl.flare_driver,
        pro_domains_shifted=final_shifted,
        expected_M4_outcome=outcome,
        expected_UC_behavior=uc,
        escalation_event=escalation_to_dict(esc) if esc else None,
        miss_reason=miss,
    )


def generate_cohort(
    n: int, seed: int, *, emit_rapid3_subscores: bool = False, params: GeneratorParams | None = None
) -> tuple[list[PatientRecord], list[PatientAnswer]]:
    """Generate ``n`` patients deterministically; return (records, answers)."""
    params = params or default_params()
    rng = CohortRNG(seed)
    records: list[PatientRecord] = []
    answers: list[PatientAnswer] = []

    for i in range(n):
        gen = rng.patient(i)
        pid = f"SYN-{i + 1:06d}"
        state = _choose_state(gen, params)
        baseline = params.baselines[state]
        sex = "F" if gen.random() < params.demographics.female_proportion else "M"
        sero = (
            "seropositive"
            if gen.random() < params.demographics.seropositive_proportion
            else "seronegative"
        )
        n_waves = int(gen.integers(params.waves.min_waves, params.waves.max_waves + 1))
        wave_dates = _wave_dates(gen, n_waves, params)
        dur_days = int(
            max(1.0, gen.normal(params.demographics.disease_duration_median_yr, 4.0)) * 365
        )
        dx_date = wave_dates[0] - timedelta(days=dur_days)

        comorbid = assign_comorbidity(gen, params.comorbidity)
        driver = "RA_codominant" if comorbid.is_comorbid else "RA_primary"
        traj = draw_latent_trajectory(gen, n_waves, 0.0, params.correlation)
        plan = plant_flares(gen, traj, baseline, params, wave_dates, driver=driver)
        apply_comorbidity_offset(
            gen, traj, baseline.pain_sd, baseline.pga_sd, comorbid, params.comorbidity
        )
        series = map_to_instruments(gen, traj, baseline, params.icc)

        # --- PatientRecord (the three CSVs) ---
        waves = [
            Wave(w, wave_dates[w], _pro_rows(series.waves[w], emit_rapid3_subscores))
            for w in range(n_waves)
        ]
        meds: list[MedEvent] = [emit_maintenance_dmard(gen, dx_date), *plan.med_events]
        records.append(PatientRecord(pid, sex, sero, dx_date, waves, meds))

        # --- PatientAnswer (per-wave ground truth) ---
        flares_by_wave = {f.wave_number: f for f in plan.flares}
        trues = list(zip(series.true_haq, series.true_pain, series.true_pga, strict=True))
        has_flare = bool(plan.flares)
        tier = (
            "clean"
            if not comorbid.is_comorbid
            else ("co_dominant" if has_flare else "masked_minority")
        )
        per_wave: list[WaveAnswer] = []
        for w in range(n_waves):
            # Crossings are FINALIZED here, on the post-comorbidity-offset true values that the
            # emitted CSVs reflect - never the pre-offset values plant_flares computed. This
            # keeps the answer sheet self-consistent with the trajectory and lets a real flare
            # masked by comorbidity baseline elevation read as an honest should_miss.
            final_shifted = domains_shifted(trues[w - 1], trues[w], params) if w >= 1 else []
            if w in flares_by_wave:
                fl = flares_by_wave[w]
                per_wave.append(
                    _flare_answer(w, fl, final_shifted, trues[w], comorbid.is_comorbid, params)
                )
            elif w in comorbid.elevated_waves and w >= 1:
                discordant = ("HAQ-II" not in final_shifted) and bool(final_shifted)
                per_wave.append(
                    WaveAnswer(
                        wave_number=w,
                        true_flare=False,
                        flare_class=None,
                        flare_driver="comorbidity_driven",
                        pro_domains_shifted=final_shifted,
                        expected_M4_outcome="should_miss_by_design",
                        expected_UC_behavior="flag_discordance" if discordant else "widen",
                        miss_reason="comorbidity_driven",
                    )
                )
            else:
                per_wave.append(
                    WaveAnswer(
                        wave_number=w,
                        true_flare=False,
                        flare_class=None,
                        flare_driver=None,
                        pro_domains_shifted=[],
                        expected_M4_outcome=None,
                        expected_UC_behavior="stable",
                    )
                )
        answers.append(PatientAnswer(pid, tier, list(comorbid.flags), state, per_wave))

    return records, answers
