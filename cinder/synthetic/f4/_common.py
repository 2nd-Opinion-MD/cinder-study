"""Shared F4 dial-in assembly — deterministic (PatientRecord, PatientAnswer) builder."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np

from cinder.synthetic.answer_sheet import PatientAnswer, WaveAnswer, escalation_to_dict
from cinder.synthetic.cohort import _flare_answer
from cinder.synthetic.comorbidity import ComorbidityAssignment
from cinder.synthetic.flares import PlantedFlare, domains_shifted
from cinder.synthetic.instruments import WaveScores, map_to_instruments
from cinder.synthetic.params import GeneratorParams, default_params
from cinder.synthetic.records import MedEvent, PROObservation, PatientRecord, Wave
from cinder.synthetic.rng import CohortRNG
from cinder.synthetic.m4_arithmetic import escalation_within_window
from cinder.synthetic.treatment import emit_maintenance_dmard

__all__ = [
    "assemble_f4_patient",
    "f4_patient_id",
    "f4_rng",
    "f4_seed",
    "wave_dates_f4",
]

_BASE_DATE = date(2020, 1, 15)
_CASE_BASE_SEED = {
    "CASE-01": 910_001,
    "CASE-04": 910_004,
    "CASE-06": 910_006,
    "CASE-08": 910_008,
}


def f4_seed(case_id: str, variant_seed: int) -> int:
    """Deterministic cohort seed for one F4 case × variant (0..19)."""
    base = _CASE_BASE_SEED[case_id]
    return base + variant_seed * 997


def f4_patient_id(case_id: str, variant_seed: int) -> str:
    return f"{case_id}-v{variant_seed:02d}"


def f4_rng(case_id: str, variant_seed: int) -> np.random.Generator:
    return CohortRNG(f4_seed(case_id, variant_seed)).patient(0)


def wave_dates_f4(
    gen: np.random.Generator,
    n_waves: int,
    params: GeneratorParams,
    *,
    start_jitter_days: int = 0,
) -> list[date]:
    start = _BASE_DATE + timedelta(days=int(start_jitter_days))
    dates = [start]
    for _ in range(1, n_waves):
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


def assemble_f4_patient(
    case_id: str,
    variant_seed: int,
    *,
    state: str,
    n_waves: int,
    comorbid: ComorbidityAssignment,
    traj,
    wave_dates: list[date],
    med_events: list[MedEvent],
    flares: list[PlantedFlare],
    phenotype_tier: str,
    params: GeneratorParams | None = None,
    emit_subscores: bool = False,
    extra_per_wave: dict[int, WaveAnswer] | None = None,
) -> tuple[PatientRecord, PatientAnswer]:
    """Map a dialed trajectory into the standard record + answer contract."""
    params = params or default_params()
    gen = f4_rng(case_id, variant_seed)
    pid = f4_patient_id(case_id, variant_seed)
    baseline = params.baselines[state]
    series = map_to_instruments(gen, traj, baseline, params.icc)

    sex = "F" if gen.random() < params.demographics.female_proportion else "M"
    sero = (
        "seropositive"
        if gen.random() < params.demographics.seropositive_proportion
        else "seronegative"
    )
    dur_days = int(
        max(1.0, gen.normal(params.demographics.disease_duration_median_yr, 4.0)) * 365
    )
    dx_date = wave_dates[0] - timedelta(days=dur_days)

    waves = [
        Wave(w, wave_dates[w], _pro_rows(series.waves[w], emit_subscores))
        for w in range(n_waves)
    ]
    meds = [emit_maintenance_dmard(gen, dx_date), *med_events]
    record = PatientRecord(pid, sex, sero, dx_date, waves, meds)

    flares_by_wave = {f.wave_number: f for f in flares}
    trues = list(zip(series.true_haq, series.true_pain, series.true_pga, strict=True))
    extra = extra_per_wave or {}
    per_wave: list[WaveAnswer] = []
    for w in range(n_waves):
        if w in extra:
            per_wave.append(extra[w])
            continue
        final_shifted = domains_shifted(trues[w - 1], trues[w], params) if w >= 1 else []
        if w in flares_by_wave:
            fl = flares_by_wave[w]
            per_wave.append(
                _flare_answer(
                    w, fl, final_shifted, trues[w], comorbid.is_comorbid, params, wave_dates[w]
                )
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

    answer = PatientAnswer(pid, phenotype_tier, list(comorbid.flags), state, per_wave)
    return record, answer
