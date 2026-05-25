"""Unit tests for analysis.simulation.kappa_ci_simulator.

Three tiers:

1.  **Cohen's kappa correctness** — closed-form 2x2 sanity checks.
2.  **Data-generating model fidelity** — the simulator's iid joint-
    distribution sampler must produce kappa-hat unbiased for true_kappa
    at large N. Cohen's pooled kappa is biased under patient-level
    prevalence heterogeneity, so the simulator deliberately models iid
    observations and applies ICC as a post-hoc design-effect inflation
    on the SE (standard sample-size derivation for clustered binary
    outcomes; matches the §4.8 hierarchical PyMC posterior under flat
    priors).
3.  **Determinism + design-effect + power monotonicity.**
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from analysis.simulation.kappa_ci_simulator import (
    KAPPA_THRESHOLD_H11,
    KappaCISimulationConfig,
    _phi,
    compute_cohens_kappa,
    design_effect_factor,
    run_kappa_simulation,
    simulate_one_replicate,
)

# --------------------------------------------------------------------------- #
# Cohen's kappa
# --------------------------------------------------------------------------- #


def test_cohens_kappa_perfect_agreement_is_one() -> None:
    a = np.array([1, 0, 1, 1, 0, 0, 1, 0])
    assert compute_cohens_kappa(a, a) == pytest.approx(1.0)


def test_cohens_kappa_perfect_disagreement_is_negative() -> None:
    a = np.array([1, 0, 1, 0, 1, 0, 1, 0])
    b = 1 - a
    k = compute_cohens_kappa(a, b)
    assert k == pytest.approx(-1.0)


def test_cohens_kappa_independent_raters_is_near_zero() -> None:
    rng = np.random.default_rng(0)
    n = 50_000
    a = rng.binomial(1, 0.3, size=n)
    b = rng.binomial(1, 0.3, size=n)
    k = compute_cohens_kappa(a, b)
    assert abs(k) < 4 / math.sqrt(n)


def test_cohens_kappa_handles_degenerate_marginals() -> None:
    a = np.array([1, 1, 1, 1])
    assert compute_cohens_kappa(a, a) == 0.0  # both always 1 -> p_e = 1


def test_cohens_kappa_empty_array_returns_nan() -> None:
    a = np.array([], dtype=np.int8)
    assert math.isnan(compute_cohens_kappa(a, a))


def test_cohens_kappa_shape_mismatch_raises() -> None:
    with pytest.raises(ValueError):
        compute_cohens_kappa(np.array([1, 0]), np.array([1, 0, 1]))


# --------------------------------------------------------------------------- #
# Data-generating model fidelity
# --------------------------------------------------------------------------- #


def test_simulator_recovers_true_kappa_at_kappa_zero() -> None:
    cfg = KappaCISimulationConfig(
        n_patients=200,
        waves_per_patient=4,
        true_kappa=0.001,  # __post_init__ requires kappa in [0,1]
        marginal_prevalence=0.20,
        icc=0.10,
        n_replicates=400,
        seed=2026,
    )
    r = run_kappa_simulation(cfg)
    # n_total = 800, kappa_sd_iid ~ 0.04 -> SE on the mean of 400 reps ~ 0.002
    assert abs(r.kappa_hat_mean - 0.001) < 0.01


def test_simulator_recovers_true_kappa_at_moderate_value() -> None:
    cfg = KappaCISimulationConfig(
        n_patients=200,
        waves_per_patient=4,
        true_kappa=0.55,
        marginal_prevalence=0.25,
        icc=0.30,
        n_replicates=400,
        seed=2026,
    )
    r = run_kappa_simulation(cfg)
    # ICC is post-hoc inflation only; the iid Monte Carlo recovers 0.55.
    assert abs(r.kappa_hat_mean - 0.55) < 0.01


def test_simulator_recovers_true_kappa_high() -> None:
    cfg = KappaCISimulationConfig(
        n_patients=100,
        waves_per_patient=8,
        true_kappa=0.80,
        marginal_prevalence=0.20,
        icc=0.30,
        n_replicates=400,
        seed=2026,
    )
    r = run_kappa_simulation(cfg)
    assert abs(r.kappa_hat_mean - 0.80) < 0.01


def test_iid_se_scales_inversely_with_sqrt_n() -> None:
    """Doubling N at fixed everything-else should shrink iid SE by ~sqrt(2)."""
    base_kwargs = {
        "waves_per_patient": 4,
        "true_kappa": 0.65,
        "marginal_prevalence": 0.20,
        "icc": 0.10,
        "n_replicates": 1500,
        "seed": 2026,
    }
    r_50 = run_kappa_simulation(KappaCISimulationConfig(**base_kwargs, n_patients=50))
    r_200 = run_kappa_simulation(KappaCISimulationConfig(**base_kwargs, n_patients=200))
    ratio = r_50.kappa_hat_sd_iid / r_200.kappa_hat_sd_iid
    # sqrt(200/50) = 2.0; expect ratio ~2.0 within Monte Carlo tolerance.
    assert 1.7 < ratio < 2.3


def test_design_effect_inflates_clustered_se_correctly() -> None:
    """Clustered SE = iid SE * sqrt(1 + (m-1)*ICC)."""
    cfg = KappaCISimulationConfig(
        n_patients=50,
        waves_per_patient=4,
        true_kappa=0.6,
        marginal_prevalence=0.20,
        icc=0.30,
        n_replicates=2000,
        seed=2026,
    )
    r = run_kappa_simulation(cfg)
    expected_deff = math.sqrt(1 + 3 * 0.30)  # = sqrt(1.9) ~= 1.378
    assert abs(r.design_effect_factor - expected_deff) < 1e-9
    assert r.kappa_hat_sd_clustered == pytest.approx(r.kappa_hat_sd_iid * expected_deff, rel=1e-9)


def test_design_effect_at_zero_icc_is_one() -> None:
    cfg = KappaCISimulationConfig(
        n_patients=30,
        waves_per_patient=4,
        true_kappa=0.5,
        marginal_prevalence=0.2,
        icc=0.0,
        n_replicates=400,
        seed=2026,
    )
    r = run_kappa_simulation(cfg)
    assert r.design_effect_factor == 1.0
    assert r.kappa_hat_sd_clustered == r.kappa_hat_sd_iid


def test_design_effect_factor_helper() -> None:
    assert design_effect_factor(waves_per_patient=4, icc=0.0) == 1.0
    assert design_effect_factor(waves_per_patient=4, icc=0.30) == pytest.approx(math.sqrt(1.9))
    assert design_effect_factor(waves_per_patient=1, icc=0.5) == 1.0  # m=1: no inflation


# --------------------------------------------------------------------------- #
# Determinism, boundary, validation
# --------------------------------------------------------------------------- #


def test_run_kappa_simulation_is_deterministic() -> None:
    cfg = KappaCISimulationConfig(
        n_patients=30,
        waves_per_patient=4,
        true_kappa=0.5,
        marginal_prevalence=0.2,
        icc=0.2,
        n_replicates=200,
        seed=2026,
    )
    a = run_kappa_simulation(cfg)
    b = run_kappa_simulation(cfg)
    assert a.kappa_hat_mean == b.kappa_hat_mean
    assert a.kappa_hat_sd_iid == b.kappa_hat_sd_iid
    assert a.kappa_hat_sd_clustered == b.kappa_hat_sd_clustered
    assert a.power_h11 == b.power_h11


def test_different_seeds_produce_different_outputs() -> None:
    base_kwargs = {
        "n_patients": 30,
        "waves_per_patient": 4,
        "true_kappa": 0.5,
        "marginal_prevalence": 0.2,
        "icc": 0.2,
        "n_replicates": 200,
    }
    a = run_kappa_simulation(KappaCISimulationConfig(**base_kwargs, seed=2026))
    b = run_kappa_simulation(KappaCISimulationConfig(**base_kwargs, seed=42))
    assert a.kappa_hat_mean != b.kappa_hat_mean


def test_invalid_n_patients_raises() -> None:
    with pytest.raises(ValueError):
        KappaCISimulationConfig(
            n_patients=0,
            waves_per_patient=4,
            true_kappa=0.5,
            marginal_prevalence=0.2,
            icc=0.2,
        )


def test_invalid_kappa_raises() -> None:
    with pytest.raises(ValueError):
        KappaCISimulationConfig(
            n_patients=10,
            waves_per_patient=4,
            true_kappa=1.5,
            marginal_prevalence=0.2,
            icc=0.2,
        )


def test_invalid_prevalence_raises() -> None:
    with pytest.raises(ValueError):
        KappaCISimulationConfig(
            n_patients=10,
            waves_per_patient=4,
            true_kappa=0.5,
            marginal_prevalence=0.0,
            icc=0.2,
        )


def test_invalid_icc_raises() -> None:
    with pytest.raises(ValueError):
        KappaCISimulationConfig(
            n_patients=10,
            waves_per_patient=4,
            true_kappa=0.5,
            marginal_prevalence=0.2,
            icc=1.0,
        )


def test_phi_matches_known_values() -> None:
    assert _phi(0.0) == pytest.approx(0.5, abs=1e-12)
    assert _phi(1.0) == pytest.approx(0.8413447460685429, abs=1e-9)
    assert _phi(-1.0) == pytest.approx(0.15865525393145707, abs=1e-9)
    assert _phi(0.8416212335729143) == pytest.approx(0.80, abs=1e-6)


def test_simulate_one_replicate_returns_correct_shape() -> None:
    rng = np.random.default_rng(2026)
    comp, cin, k = simulate_one_replicate(
        rng=rng,
        n_patients=10,
        waves_per_patient=3,
        true_kappa=0.5,
        marginal_prev=0.2,
    )
    assert comp.shape == (30,)
    assert cin.shape == (30,)
    assert -1.0 <= k <= 1.0


def test_threshold_constant_matches_protocol() -> None:
    """Sanity check: the H1.1 threshold is 0.40 per IMPLEMENTATION_PLAN §6."""
    assert KAPPA_THRESHOLD_H11 == 0.40


# --------------------------------------------------------------------------- #
# Power monotonicity (should always hold under the §6 framing)
# --------------------------------------------------------------------------- #


def test_power_increases_with_n_at_fixed_kappa() -> None:
    base_kwargs = {
        "waves_per_patient": 4,
        "true_kappa": 0.55,
        "marginal_prevalence": 0.20,
        "icc": 0.20,
        "n_replicates": 1500,
        "seed": 2026,
    }
    r_25 = run_kappa_simulation(KappaCISimulationConfig(**base_kwargs, n_patients=25))
    r_100 = run_kappa_simulation(KappaCISimulationConfig(**base_kwargs, n_patients=100))
    assert r_100.power_h11 >= r_25.power_h11


def test_power_increases_with_kappa_at_fixed_n() -> None:
    base_kwargs = {
        "n_patients": 50,
        "waves_per_patient": 4,
        "marginal_prevalence": 0.20,
        "icc": 0.20,
        "n_replicates": 1500,
        "seed": 2026,
    }
    r_low = run_kappa_simulation(KappaCISimulationConfig(**base_kwargs, true_kappa=0.45))
    r_high = run_kappa_simulation(KappaCISimulationConfig(**base_kwargs, true_kappa=0.75))
    assert r_high.power_h11 > r_low.power_h11


def test_power_decreases_with_higher_icc_at_fixed_n_and_kappa() -> None:
    """Higher ICC inflates SE, so H1.1 power should decrease (or stay same)."""
    base_kwargs = {
        "n_patients": 50,
        "waves_per_patient": 4,
        "true_kappa": 0.55,
        "marginal_prevalence": 0.20,
        "n_replicates": 2000,
        "seed": 2026,
    }
    r_low_icc = run_kappa_simulation(KappaCISimulationConfig(**base_kwargs, icc=0.05))
    r_high_icc = run_kappa_simulation(KappaCISimulationConfig(**base_kwargs, icc=0.40))
    assert r_high_icc.power_h11 <= r_low_icc.power_h11
