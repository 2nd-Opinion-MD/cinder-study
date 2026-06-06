"""latent.py - Layer A: the latent disease-burden factor model + AR(1) trajectory (§4).

The three primary PROs are NOT independent; they co-move off a shared latent disease
burden ``L``. This module produces, per patient, a wave-indexed array of standardized
*structural true states* for pain, PGA, and HAQ (mean 0, unit-ish variance in standardized
space). Layer B (`instruments.py`) maps these to instrument units and imposes the §3 ICC
measurement-noise floor.

Design (arch §5.1):
  - ``L[w]`` evolves as AR(1): ``L[w] = rho * L[w-1] + sqrt(1 - rho^2) * z``, baseline level
    set by the patient's disease-activity state. Flare excursions and slow drift are ADDED
    to ``L`` over their windows (done in `flares.py`, Sprint 2) - this module exposes the
    clean trajectory.
  - ``pain_struct`` and ``pga_struct`` load heavily on ``L`` (high beta) -> their correlation
    is high (~0.7+).
  - ``haq_struct`` loads moderately on ``L`` PLUS a sticky independent functional component
    ``eta`` (its own slower AR(1)) -> HAQ carries visibly more independent variance and lags.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from cinder.synthetic.params import CorrelationStructure

__all__ = ["LatentTrajectory", "draw_latent_trajectory"]


@dataclass(slots=True)
class LatentTrajectory:
    """Standardized structural true states per wave (pre-measurement, pre-units)."""

    latent: np.ndarray  # L[w] - shared disease burden, standardized
    pain_struct: np.ndarray  # standardized structural pain state
    pga_struct: np.ndarray  # standardized structural global state
    haq_struct: np.ndarray  # standardized structural function state (carries eta)
    function_latent: np.ndarray  # the sticky functional component eta[w] (drives RAPID3 FN)


def _ar1(rng: np.random.Generator, n: int, rho: float, level: float = 0.0) -> np.ndarray:
    """An AR(1) path of length ``n`` with stationary unit variance, offset by ``level``.

    ``x[0] = level + z0`` ; ``x[w] = level + rho*(x[w-1]-level) + sqrt(1-rho^2)*z``.
    """
    out = np.empty(n, dtype=float)
    innov = rng.standard_normal(n)
    out[0] = level + innov[0]
    scale = float(np.sqrt(max(0.0, 1.0 - rho * rho)))
    for w in range(1, n):
        out[w] = level + rho * (out[w - 1] - level) + scale * innov[w]
    return out


def draw_latent_trajectory(
    rng: np.random.Generator,
    n_waves: int,
    state_level: float,
    corr: CorrelationStructure,
) -> LatentTrajectory:
    """Draw one patient's standardized structural trajectory.

    ``state_level`` is the standardized baseline offset for the patient's disease-activity
    state (e.g. high-activity patients sit higher on ``L``). Heavy loadings on ``L`` for
    pain/PGA produce their tight coupling; HAQ mixes a moderate ``L`` loading with the
    independent functional component ``eta`` so it lags and carries extra variance.
    """
    latent = _ar1(rng, n_waves, corr.rho_latent, level=state_level)
    eta = _ar1(rng, n_waves, corr.rho_function, level=state_level)

    # Independent measurement-free structural residuals (small, fixed at calibration).
    eps_pain = rng.standard_normal(n_waves) * _STRUCT_RESIDUAL_SD
    eps_pga = rng.standard_normal(n_waves) * _STRUCT_RESIDUAL_SD
    eps_haq = rng.standard_normal(n_waves) * _STRUCT_RESIDUAL_SD

    pain_struct = corr.beta_pain * latent + eps_pain
    pga_struct = corr.beta_pga * latent + eps_pga
    # HAQ: moderate shared loading + sticky independent functional component.
    haq_struct = corr.beta_haq * latent + _ETA_WEIGHT * eta + eps_haq

    return LatentTrajectory(
        latent=latent,
        pain_struct=pain_struct,
        pga_struct=pga_struct,
        haq_struct=haq_struct,
        function_latent=eta,
    )


#: Small structural residual SD - kept tight because the §3 ICC floor caps the OBSERVED
#: pain/PGA correlation at sqrt(ICC_pain*ICC_pga) ~= 0.72, so clearing the >=0.70 checkpoint
#: requires near-unity structural coupling (pain/PGA ride L almost exactly). Calibrated in
#: the Sprint-1 property tests.
_STRUCT_RESIDUAL_SD = 0.08
#: Weight on the independent functional component for HAQ - sets how much extra independent
#: variance HAQ carries relative to pain/PGA (the "function lags / is stickier" property).
#: With beta_haq=0.82 this leaves HAQ ~35% independent variance vs pain/PGA's ~1%.
_ETA_WEIGHT = 0.60
