"""comorbidity.py - the masking engine (§7): FM/depression inflate Pain/PGA, not HAQ.

Fibromyalgia and depression elevate patient-reported Pain VAS and Patient Global without a
corresponding inflammatory escalation - central sensitization and distress, not synovitis.
The mechanism is an additive offset (plus extra volatility) on the Pain and PGA channels
ONLY, applied OUTSIDE the latent burden ``L`` and WITHOUT any escalation event. HAQ is left
untouched, which produces the discordance signature (Pain/PGA up, HAQ flat) that M4 must NOT
read as a flare. A detection on these waves is scored a false positive.

The generator assigns comorbidity flags to ~20-35% of patients (§7 prevalences) and records,
for affected waves, ``flare_driver=comorbidity_driven`` / ``expected_M4_outcome=
should_miss_by_design`` / ``expected_UC_behavior=widen|flag_discordance``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from cinder.synthetic.latent import LatentTrajectory
from cinder.synthetic.params import ComorbidityParams

__all__ = ["ComorbidityAssignment", "apply_comorbidity_offset", "assign_comorbidity"]


@dataclass(slots=True)
class ComorbidityAssignment:
    """Which comorbidities a patient carries and which waves show driven elevation."""

    flags: list[str] = field(default_factory=list)  # [] | [fibromyalgia] | [depression] | both
    elevated_waves: list[int] = field(default_factory=list)

    @property
    def is_comorbid(self) -> bool:
        return bool(self.flags)


def assign_comorbidity(
    rng: np.random.Generator, params: ComorbidityParams
) -> ComorbidityAssignment:
    """Draw a patient's comorbidity flags (FM and/or depression) per §7 prevalences."""
    if rng.random() >= params.assign_fraction:
        return ComorbidityAssignment()
    flags: list[str] = []
    # Conditional on being in the comorbid fraction, draw which condition(s); guarantee >=1.
    if rng.random() < params.fm_prevalence / (params.fm_prevalence + params.depression_prevalence):
        flags.append("fibromyalgia")
    if rng.random() < 0.5:
        flags.append("depression")
    if not flags:
        flags.append("fibromyalgia")
    return ComorbidityAssignment(flags=flags)


def apply_comorbidity_offset(
    rng: np.random.Generator,
    traj: LatentTrajectory,
    baseline_pain_sd: float,
    baseline_pga_sd: float,
    assignment: ComorbidityAssignment,
    params: ComorbidityParams,
) -> None:
    """Add the comorbidity offset to Pain/PGA struct on a subset of waves (HAQ untouched).

    The offset is converted from native units to structural units (divide by the channel SD)
    so it adds the right number of VAS points after the affine map, plus extra structural
    volatility drawn as additive Gaussian noise with SD = ``extra_volatility - 1.0`` (in the
    same standardized structural units; ``extra_volatility == 1.0`` adds none). A comorbid
    patient shows the elevation on a random subset of waves (chronic but fluctuating distress);
    those waves are recorded as ``comorbidity_driven`` ground truth. ``L`` and HAQ are never
    touched, so the discordance signature is preserved and no escalation is emitted for these
    waves.
    """
    if not assignment.is_comorbid:
        return
    n = traj.pain_struct.shape[0]
    # Each wave independently shows driven elevation with moderate probability.
    elevated = [w for w in range(n) if rng.random() < 0.5]
    pain_off = params.pain_offset_mean / baseline_pain_sd
    pga_off = params.pga_offset_mean / baseline_pga_sd
    vol_sd = params.extra_volatility - 1.0  # additive structural-noise SD (see params docstring)
    for w in elevated:
        # Additive offset + extra structural volatility on Pain/PGA channels only (NOT through
        # L, no HAQ), so the Pain/PGA-up, HAQ-flat discordance signature is preserved.
        traj.pain_struct[w] += pain_off + rng.normal(0.0, vol_sd)
        traj.pga_struct[w] += pga_off + rng.normal(0.0, vol_sd)
    assignment.elevated_waves = elevated
