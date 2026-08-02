"""CASE-06 — temporal-sampling failure (PRO + escalation exist, ±90d linkage missed)."""

from __future__ import annotations

from cinder.synthetic.comorbidity import ComorbidityAssignment
from cinder.synthetic.f4._common import assemble_f4_patient, f4_rng, wave_dates_f4
from cinder.synthetic.flares import plant_visible_flare_at
from cinder.synthetic.latent import draw_latent_trajectory
from cinder.synthetic.params import GeneratorParams, default_params

__all__ = ["build_case_06"]

# Escalation placed 120d before wave — outside M4.C ±90d window.
_OUT_OF_WINDOW_DAYS = 120


def build_case_06(
    variant_seed: int,
    *,
    n_waves: int = 6,
    params: GeneratorParams | None = None,
) -> tuple:
    params = params or default_params()
    gen = f4_rng("CASE-06", variant_seed)
    state = "moderate"
    wave_dates = wave_dates_f4(gen, n_waves, params, start_jitter_days=variant_seed * 7)
    flare_wave = 2 + (variant_seed % 3)
    planted_class = ("gc_rescue_burst", "dose_increase", "dmard_initiation")[
        variant_seed % 3
    ]

    traj = draw_latent_trajectory(gen, n_waves, 0.0, params.correlation)
    flare, meds = plant_visible_flare_at(
        gen,
        traj,
        params.baselines[state],
        params,
        flare_wave,
        wave_dates,
        driver="RA_primary",
        planted_class=planted_class,
        window_offset_days=_OUT_OF_WINDOW_DAYS,
    )

    return assemble_f4_patient(
        "CASE-06",
        variant_seed,
        state=state,
        n_waves=n_waves,
        comorbid=ComorbidityAssignment(),
        traj=traj,
        wave_dates=wave_dates,
        med_events=meds,
        flares=[flare],
        phenotype_tier="adversarial",
        params=params,
    )
