"""CASE-08 — slow drift / baseline masking (sub-MCID steps, cumulative worsening)."""

from __future__ import annotations

from cinder.synthetic.answer_sheet import WaveAnswer
from cinder.synthetic.comorbidity import ComorbidityAssignment
from cinder.synthetic.f4._common import assemble_f4_patient, f4_rng, wave_dates_f4
from cinder.synthetic.flares import domains_shifted, plant_slow_drift
from cinder.synthetic.instruments import map_to_instruments
from cinder.synthetic.latent import draw_latent_trajectory
from cinder.synthetic.params import GeneratorParams, default_params

__all__ = ["build_case_08"]


def build_case_08(
    variant_seed: int,
    *,
    n_waves: int = 6,
    params: GeneratorParams | None = None,
) -> tuple:
    params = params or default_params()
    gen = f4_rng("CASE-08", variant_seed)
    state = "low"
    baseline = params.baselines[state]
    wave_dates = wave_dates_f4(gen, n_waves, params, start_jitter_days=variant_seed * 11)

    traj = draw_latent_trajectory(gen, n_waves, 0.0, params.correlation)
    plant_slow_drift(traj, baseline, params)
    series = map_to_instruments(gen, traj, baseline, params.icc)
    trues = list(zip(series.true_haq, series.true_pain, series.true_pga, strict=True))

    last = n_waves - 1
    cumulative_pain = trues[last][1] - trues[0][1]
    cumulative_pga = trues[last][2] - trues[0][2]
    last_step_shifted = domains_shifted(trues[last - 1], trues[last], params)

    extra = {
        last: WaveAnswer(
            wave_number=last,
            true_flare=True,
            flare_class=None,
            flare_driver="RA_primary",
            pro_domains_shifted=last_step_shifted,
            expected_M4_outcome="should_miss_by_design",
            expected_UC_behavior="widen",
            miss_reason="baseline_masking",
        )
    }

    record, answer = assemble_f4_patient(
        "CASE-08",
        variant_seed,
        state=state,
        n_waves=n_waves,
        comorbid=ComorbidityAssignment(),
        traj=traj,
        wave_dates=wave_dates,
        med_events=[],
        flares=[],
        phenotype_tier="adversarial",
        params=params,
        extra_per_wave=extra,
    )

    # Sanity: cumulative drift exceeds MCID; per-step on final wave stays sub-MCID.
    assert cumulative_pain >= params.mcid.pain_vas, "CASE-08 cumulative pain drift too small"
    assert cumulative_pga >= params.mcid.pga_vas, "CASE-08 cumulative PGA drift too small"
    assert len(last_step_shifted) < 2, "CASE-08 final step should not cross ≥2 domains"

    return record, answer
