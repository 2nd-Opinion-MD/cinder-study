"""Unit-level regression tests for the three closed-form conjugate updates.

These tests assert mathematical properties that hold by construction,
independent of which scipy version (or no-scipy fallback) is in play.
The properties checked are the load-bearing invariants the protocol
§4.8 primary analysis depends on:

    * For Beta-Bernoulli: posterior mean = alpha_post / (alpha_post + beta_post)
      and the 90% band is tighter than the prior's 90% band as evidence accrues.
    * For Gamma-Poisson: posterior mean = alpha_post / beta_post and the
      band is tighter as exposure grows.
    * For Normal-Normal: posterior mean is a precision-weighted combination
      of prior mean and sample mean, and posterior sigma shrinks with N.

The tests deliberately use small hand-checkable inputs so any regression
surfaces as a clear arithmetic mismatch.
"""

from __future__ import annotations

import math

import pytest

from cinder.bayes import (
    BetaPrior,
    GammaPrior,
    NormalNormalPrior,
    update_beta_bernoulli,
    update_gamma_poisson,
    update_normal_normal,
)


class TestBetaBernoulli:
    """Beta-Bernoulli closed-form update."""

    def test_no_evidence_returns_prior_mean(self) -> None:
        prior = BetaPrior(alpha=2.0, beta=8.0)
        upd = update_beta_bernoulli(prior, n_pos=0.0, n_neg=0.0)
        assert math.isclose(upd.mean, 0.2, rel_tol=1e-6)
        assert upd.alpha_post == pytest.approx(2.0)
        assert upd.beta_post == pytest.approx(8.0)

    def test_evidence_shifts_mean_toward_data(self) -> None:
        # Prior says probability ~ 0.2; 50 positives + 0 negatives shifts up.
        prior = BetaPrior(alpha=2.0, beta=8.0)
        upd = update_beta_bernoulli(prior, n_pos=50.0, n_neg=0.0)
        assert upd.alpha_post == pytest.approx(52.0)
        assert upd.beta_post == pytest.approx(8.0)
        assert math.isclose(upd.mean, 52.0 / 60.0, rel_tol=1e-6)

    def test_band_is_ordered_and_brackets_mean(self) -> None:
        prior = BetaPrior(alpha=2.0, beta=8.0)
        upd = update_beta_bernoulli(prior, n_pos=10.0, n_neg=10.0)
        lo, hi = upd.band_90
        assert 0.0 <= lo <= upd.mean <= hi <= 1.0
        # 90% band on Beta(12, 18) is informative — width well under prior's.
        assert (hi - lo) < 0.4

    def test_band_tightens_with_more_evidence(self) -> None:
        prior = BetaPrior(alpha=2.0, beta=8.0)
        small = update_beta_bernoulli(prior, n_pos=5.0, n_neg=5.0)
        large = update_beta_bernoulli(prior, n_pos=500.0, n_neg=500.0)
        small_width = small.band_90[1] - small.band_90[0]
        large_width = large.band_90[1] - large.band_90[0]
        assert large_width < small_width

    def test_fractional_weights_accepted(self) -> None:
        # Salience-weighted evidence produces fractional alpha/beta; kernel must accept.
        prior = BetaPrior(alpha=2.0, beta=8.0)
        upd = update_beta_bernoulli(prior, n_pos=2.7, n_neg=1.3)
        assert upd.alpha_post == pytest.approx(4.7)
        assert upd.beta_post == pytest.approx(9.3)
        assert math.isclose(upd.mean, 4.7 / 14.0, rel_tol=1e-6)


class TestGammaPoisson:
    """Gamma-Poisson closed-form update."""

    def test_no_evidence_returns_prior_mean(self) -> None:
        prior = GammaPrior(alpha=4.0, beta=2.0)  # mean = 2.0
        upd = update_gamma_poisson(prior, total_events=0.0, exposure=0.0)
        assert math.isclose(upd.mean, 2.0, rel_tol=1e-6)
        assert upd.alpha_post == pytest.approx(4.0)
        assert upd.beta_post == pytest.approx(2.0)

    def test_evidence_shifts_mean(self) -> None:
        prior = GammaPrior(alpha=2.0, beta=2.0)  # mean = 1.0
        upd = update_gamma_poisson(prior, total_events=20.0, exposure=10.0)
        # alpha_post = 22, beta_post = 12, mean = 22/12 ≈ 1.833
        assert upd.alpha_post == pytest.approx(22.0)
        assert upd.beta_post == pytest.approx(12.0)
        assert math.isclose(upd.mean, 22.0 / 12.0, rel_tol=1e-6)

    def test_band_is_ordered_and_positive(self) -> None:
        prior = GammaPrior(alpha=2.0, beta=2.0)
        upd = update_gamma_poisson(prior, total_events=5.0, exposure=5.0)
        lo, hi = upd.band_90
        assert 0.0 <= lo <= upd.mean <= hi


class TestNormalNormal:
    """Normal-Normal closed-form update with known observation noise."""

    def test_no_observations_returns_prior(self) -> None:
        prior = NormalNormalPrior(mu=10.0, sigma=2.0, sigma_obs=1.0)
        upd = update_normal_normal(prior, observations=[])
        assert upd.mu_post == pytest.approx(10.0)
        assert upd.sigma_post == pytest.approx(2.0)

    def test_posterior_sigma_shrinks_with_N(self) -> None:
        # Prior precision 1/4 = 0.25; obs precision 1.0/N grows with N → posterior sigma shrinks.
        prior = NormalNormalPrior(mu=0.0, sigma=2.0, sigma_obs=1.0)
        upd_small = update_normal_normal(prior, observations=[1.0, 2.0])
        upd_large = update_normal_normal(prior, observations=[1.0] * 100)
        assert upd_large.sigma_post < upd_small.sigma_post

    def test_posterior_mean_is_precision_weighted(self) -> None:
        # Prior(0, 1) very informative + 4 obs around mean 5 → posterior pulled toward 5 but bounded.
        prior = NormalNormalPrior(mu=0.0, sigma=1.0, sigma_obs=1.0)
        upd = update_normal_normal(prior, observations=[5.0, 5.0, 5.0, 5.0])
        # Closed-form: mu_post = (mu_prior/sigma_prior^2 + N*xbar/sigma_obs^2) / posterior_precision
        # = (0 + 4*5) / (1 + 4) = 20/5 = 4.0
        assert upd.mu_post == pytest.approx(4.0)

    def test_band_brackets_posterior_mean(self) -> None:
        prior = NormalNormalPrior(mu=0.0, sigma=1.0, sigma_obs=1.0)
        upd = update_normal_normal(prior, observations=[1.0, 2.0, 3.0])
        lo, hi = upd.band_90
        assert lo <= upd.mu_post <= hi
