"""CASE-01 — escalation-absent true flare (axiom_invisible; FWD-002 family)."""

from __future__ import annotations

from cinder.synthetic.comorbidity import ComorbidityAssignment
from cinder.synthetic.f4._common import assemble_f4_patient, f4_rng, wave_dates_f4
from cinder.synthetic.flares import plant_invisible_flare_at
from cinder.synthetic.latent import draw_latent_trajectory
from cinder.synthetic.params import GeneratorParams, default_params

__all__ = ["build_case_01"]


def build_case_01(
    variant_seed: int,
    *,
    n_waves: int = 6,
    params: GeneratorParams | None = None,
) -> tuple:
    params = params or default_params()
    gen = f4_rng("CASE-01", variant_seed)
    state = "low"
    wave_dates = wave_dates_f4(gen, n_waves, params, start_jitter_days=variant_seed * 5)
    flare_wave = 2 + (variant_seed % 2)  # wave 2 or 3 (always >= min lookback)

    traj = draw_latent_trajectory(gen, n_waves, 0.0, params.correlation)
    flare = plant_invisible_flare_at(
        gen, traj, params.baselines[state], params, flare_wave, driver="RA_primary"
    )

    return assemble_f4_patient(
        "CASE-01",
        variant_seed,
        state=state,
        n_waves=n_waves,
        comorbid=ComorbidityAssignment(),
        traj=traj,
        wave_dates=wave_dates,
        med_events=[],
        flares=[flare],
        phenotype_tier="clean",
        params=params,
    )
