"""test_synthetic_comorbidity - Sprint 3 masking gates (arch Phase 3).

Asserts the §7 masking mechanism: comorbid waves elevate Pain/PGA WITHOUT touching HAQ
(the discordance signature) and without any escalation event, so M4-as-specified would not
fire (a detection there would be a false positive). Validated by comparing the identical
trajectory with and without the comorbidity offset.
"""

from __future__ import annotations

import copy

import numpy as np

from cinder.synthetic.comorbidity import (
    apply_comorbidity_offset,
    assign_comorbidity,
)
from cinder.synthetic.flares import domains_shifted
from cinder.synthetic.instruments import map_to_instruments
from cinder.synthetic.latent import draw_latent_trajectory
from cinder.synthetic.params import default_params
from cinder.synthetic.rng import CohortRNG

N_PATIENTS = 600
N_WAVES = 6


def _pairs():
    """Yield (assignment, series_without, series_with, baseline) for comorbid patients."""
    params = default_params()
    rng = CohortRNG(202)
    out = []
    n_comorbid = 0
    for i in range(N_PATIENTS):
        gen = rng.patient(i)
        baseline = params.baselines["low"]  # routine-care state where masking matters most
        traj = draw_latent_trajectory(gen, N_WAVES, 0.0, params.correlation)
        assignment = assign_comorbidity(gen, params.comorbidity)
        if not assignment.is_comorbid:
            continue
        n_comorbid += 1
        traj_with = copy.deepcopy(traj)
        apply_comorbidity_offset(
            gen, traj_with, baseline.pain_sd, baseline.pga_sd, assignment, params.comorbidity
        )
        s_without = map_to_instruments(gen, traj, baseline, params.icc)
        s_with = map_to_instruments(gen, traj_with, baseline, params.icc)
        out.append((assignment, s_without, s_with, baseline))
    return params, out, n_comorbid


def test_assignment_fraction_in_range() -> None:
    _, _, n_comorbid = _pairs()
    frac = n_comorbid / N_PATIENTS
    assert 0.20 <= frac <= 0.35, f"comorbidity assignment {frac:.1%} outside ~20-35% (§7)"


def test_flags_are_valid_subsets() -> None:
    _, pairs, _ = _pairs()
    valid = {"fibromyalgia", "depression"}
    for assignment, *_ in pairs:
        assert assignment.flags
        assert set(assignment.flags) <= valid


def test_comorbidity_elevates_pain_pga_not_haq() -> None:
    _, pairs, _ = _pairs()
    haq_untouched = True
    pain_elevated, pga_elevated = [], []
    for assignment, without, with_, _ in pairs:
        # HAQ true values must be byte-identical (offset never touches HAQ / L).
        if not np.allclose(without.true_haq, with_.true_haq):
            haq_untouched = False
        for w in assignment.elevated_waves:
            pain_elevated.append(with_.true_pain[w] >= without.true_pain[w])
            pga_elevated.append(with_.true_pga[w] >= without.true_pga[w])
    assert haq_untouched, "comorbidity offset altered HAQ - discordance signature broken"
    assert np.mean(pain_elevated) > 0.95
    assert np.mean(pga_elevated) > 0.95


def test_discordance_signature_present() -> None:
    # Among comorbid patients there exist waves where Pain/PGA cross MCID but HAQ does not -
    # the false-positive signature M4 must resist.
    params, pairs, _ = _pairs()
    discordant = 0
    for _assignment, _without, with_, _ in pairs:
        trues = list(zip(with_.true_haq, with_.true_pain, with_.true_pga, strict=True))
        for w in range(1, N_WAVES):
            shifted = domains_shifted(trues[w - 1], trues[w], params)
            pro_up = ("PainVAS" in shifted) or ("PatientGlobalVAS" in shifted)
            if pro_up and "HAQ-II" not in shifted:
                discordant += 1
    assert discordant > 0, "no Pain/PGA-up, HAQ-flat discordance waves generated"
