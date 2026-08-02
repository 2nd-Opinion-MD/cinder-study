"""CASE-04 — comorbidity-driven false-positive guard (Pain/PGA up, HAQ flat, no flare)."""

from __future__ import annotations

from cinder.synthetic.comorbidity import ComorbidityAssignment, apply_comorbidity_offset
from cinder.synthetic.f4._common import assemble_f4_patient, f4_rng, wave_dates_f4
from cinder.synthetic.latent import draw_latent_trajectory
from cinder.synthetic.params import GeneratorParams, default_params

__all__ = ["build_case_04"]


def _comorbidity_flags(variant_seed: int) -> list[str]:
    mode = variant_seed % 3
    if mode == 0:
        return ["fibromyalgia"]
    if mode == 1:
        return ["depression"]
    return ["fibromyalgia", "depression"]


def build_case_04(
    variant_seed: int,
    *,
    n_waves: int = 6,
    params: GeneratorParams | None = None,
) -> tuple:
    params = params or default_params()
    gen = f4_rng("CASE-04", variant_seed)
    state = "low"
    baseline = params.baselines[state]
    wave_dates = wave_dates_f4(gen, n_waves, params, start_jitter_days=variant_seed * 3)
    elevated_wave = 2 + (variant_seed % 3)  # waves 2, 3, or 4

    comorbid = ComorbidityAssignment(flags=_comorbidity_flags(variant_seed))
    traj = draw_latent_trajectory(gen, n_waves, 0.0, params.correlation)
    apply_comorbidity_offset(
        gen,
        traj,
        baseline.pain_sd,
        baseline.pga_sd,
        comorbid,
        params.comorbidity,
        elevated_waves=[elevated_wave],
    )
    # Force Pain/PGA MCID crossing vs prior wave; pin HAQ flat (discordance signature).
    if elevated_wave >= 1:
        pain_units = (params.mcid.pain_vas + 3.0) / baseline.pain_sd
        pga_units = (params.mcid.pga_vas + 3.0) / baseline.pga_sd
        traj.pain_struct[elevated_wave] = traj.pain_struct[elevated_wave - 1] + pain_units
        traj.pga_struct[elevated_wave] = traj.pga_struct[elevated_wave - 1] + pga_units
        traj.haq_struct[elevated_wave] = traj.haq_struct[elevated_wave - 1]

    return assemble_f4_patient(
        "CASE-04",
        variant_seed,
        state=state,
        n_waves=n_waves,
        comorbid=comorbid,
        traj=traj,
        wave_dates=wave_dates,
        med_events=[],
        flares=[],
        phenotype_tier="masked_minority",
        params=params,
    )
