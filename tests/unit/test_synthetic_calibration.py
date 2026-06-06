"""test_synthetic_calibration - Sprint 1 statistical-realism gates (arch Phase 1).

Consolidates the arch-named test_correlations / test_icc / test_baselines into one cohort
fixture (a mixture cohort is generated once, then the §2/§3/§4 targets are asserted against
it). Targets carry tolerance bands because finite-sample AR(1), clipping at instrument
bounds, and C8 rounding perturb the closed-form values.
"""

from __future__ import annotations

import numpy as np

from cinder.synthetic.instruments import map_to_instruments
from cinder.synthetic.latent import draw_latent_trajectory
from cinder.synthetic.params import default_params
from cinder.synthetic.rng import CohortRNG

N_PATIENTS = 1000
N_WAVES = 6


def _generate_pool(
    n_patients: int = N_PATIENTS, seed: int = 7, force_state: str | None = None
) -> dict[str, np.ndarray]:
    """Generate a routine-care mixture cohort; pool all patient-wave observations.

    ``force_state`` pins every patient to one disease-activity state - used for the ICC
    test, where between-state spread would otherwise inflate var(true) and overstate
    test-retest reliability (§3 is a within-patient property).
    """
    params = default_params()
    rng = CohortRNG(seed)
    states = list(params.state_mixture.weights)
    weights = np.array([params.state_mixture.weights[s] for s in states])
    weights = weights / weights.sum()
    chooser = np.random.default_rng(seed + 1)
    if force_state is not None:
        assigned = np.full(n_patients, states.index(force_state))
    else:
        assigned = chooser.choice(len(states), size=n_patients, p=weights)

    haq, pain, pga, fn, rapid3 = [], [], [], [], []
    true_haq, true_pain, true_pga = [], [], []
    per_patient_state, per_patient_haq_mean = [], []
    for i in range(n_patients):
        state = states[assigned[i]]
        baseline = params.baselines[state]
        gen = rng.patient(i)
        traj = draw_latent_trajectory(gen, N_WAVES, state_level=0.0, corr=params.correlation)
        series = map_to_instruments(gen, traj, baseline, params.icc)
        haq.extend(w.haq_ii for w in series.waves)
        pain.extend(w.pain_vas for w in series.waves)
        pga.extend(w.pga_vas for w in series.waves)
        fn.extend(w.rapid3_fn for w in series.waves)
        rapid3.extend(w.rapid3 for w in series.waves)
        true_haq.extend(series.true_haq.tolist())
        true_pain.extend(series.true_pain.tolist())
        true_pga.extend(series.true_pga.tolist())
        per_patient_state.append(state)
        per_patient_haq_mean.append(float(np.mean([w.haq_ii for w in series.waves])))
    return {
        "haq": np.array(haq),
        "pain": np.array(pain),
        "pga": np.array(pga),
        "fn": np.array(fn),
        "rapid3": np.array(rapid3),
        "true_haq": np.array(true_haq),
        "true_pain": np.array(true_pain),
        "true_pga": np.array(true_pga),
        "state": np.array(per_patient_state),
        "patient_haq_mean": np.array(per_patient_haq_mean),
    }


def _corr(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.corrcoef(a, b)[0, 1])


def _icc(true: np.ndarray, obs: np.ndarray) -> float:
    """Reliability = var(true) / (var(true) + var(measurement error)), pooled."""
    err = obs - true
    vt = float(np.var(true))
    ve = float(np.var(err))
    return vt / (vt + ve)


def test_corr_pain_pga_above_floor() -> None:
    pool = _generate_pool()
    r = _corr(pool["pain"], pool["pga"])
    assert r >= 0.70, f"corr(Pain,PGA)={r:.3f} below 0.70 floor (§4)"


def test_corr_pga_haq_moderate() -> None:
    pool = _generate_pool()
    r = _corr(pool["pga"], pool["haq"])
    assert 0.55 <= r <= 0.75, f"corr(PGA,HAQ)={r:.3f} outside moderate band ~0.64 (§4)"


def test_haq_carries_more_independent_variance() -> None:
    # corr(Pain,PGA) should exceed corr(PGA,HAQ): HAQ has the independent functional term.
    pool = _generate_pool()
    assert _corr(pool["pain"], pool["pga"]) > _corr(pool["pga"], pool["haq"])


def test_icc_within_tolerance() -> None:
    # §3 test-retest reliability is a within-patient property: measure on a single-state
    # cohort so between-state true spread does not inflate var(true).
    pool = _generate_pool(force_state="moderate")
    params = default_params()
    assert abs(_icc(pool["true_haq"], pool["haq"]) - params.icc.haq) <= 0.04
    assert abs(_icc(pool["true_pain"], pool["pain"]) - params.icc.pain) <= 0.04
    assert abs(_icc(pool["true_pga"], pool["pga"]) - params.icc.pga) <= 0.04


def test_state_baselines_ordered_and_anchored() -> None:
    pool = _generate_pool()
    params = default_params()
    means = {
        s: float(np.mean(pool["patient_haq_mean"][pool["state"] == s]))
        for s in params.state_mixture.weights
    }
    # Monotone in disease-activity state.
    assert means["remission"] < means["low"] < means["moderate"] < means["high"]
    # Moderate/high HAQ anchored to §2 (clipping is minimal in these states).
    assert abs(means["moderate"] - params.baselines["moderate"].haq_mean) <= 0.20
    assert abs(means["high"] - params.baselines["high"].haq_mean) <= 0.20


def test_rapid3_is_computed_not_drawn() -> None:
    # RAPID3 must equal round(FN + Pain/10 + PGA/10, 1) exactly - never an independent draw.
    pool = _generate_pool(n_patients=200)
    recomputed = np.round(
        pool["fn"] + np.round(pool["pain"] / 10.0, 1) + np.round(pool["pga"] / 10.0, 1), 1
    )
    assert np.allclose(pool["rapid3"], recomputed, atol=0.05)


def test_rapid3_lands_in_pincus_bands() -> None:
    # Population RAPID3 should span the Pincus bands, not collapse to one (§2/§5.1).
    pool = _generate_pool()
    r = pool["rapid3"]
    assert r.min() >= 0.0 and r.max() <= 30.0
    frac_high = float(np.mean(r > 12))
    frac_rem = float(np.mean(r <= 3))
    assert frac_high > 0.05, f"too few high-severity RAPID3 ({frac_high:.2%})"
    assert frac_rem > 0.02, f"no remission-band RAPID3 ({frac_rem:.2%})"
