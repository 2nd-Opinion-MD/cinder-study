"""
kappa_ci_simulator.py — Monte Carlo simulator for §6 sample-size prework.

Generates paired binary classifications (CINDER detection vs comparator)
under a Beta-Binomial patient mixture with symmetric marginals and
target Cohen's kappa, then computes the empirical sampling distribution
of kappa-hat across replicates. Reports posterior-CI width (asymptotic
normal approximation) and operating power against the §6 H1.1 decision
rule (`P(kappa > 0.40) >= 0.80` per IMPLEMENTATION_PLAN.md §6).

Determinism contract
--------------------

The simulator is deterministic given a seed. Two runs with the same
``KappaCISimulationConfig`` produce bit-identical
``KappaCISimulationResult`` outputs. This is what couples the prework
estimate to the §13.4 reproducibility commitment (seed=2026 is the
default per `confirmation_software.md`).

Mathematical model
------------------

The data-generating model is the **iid baseline** for paired binary
classification under symmetric marginals at prevalence ``p`` with target
Cohen's kappa::

    P(both 1)                  = p^2       + kappa * p * (1 - p)
    P(both 0)                  = (1 - p)^2 + kappa * p * (1 - p)
    P(comparator=1, cinder=0)  = p * (1 - p) * (1 - kappa)
    P(comparator=0, cinder=1)  = p * (1 - p) * (1 - kappa)

These four probabilities sum to 1 under symmetric marginals (the kappa
terms cancel in the cross-categories). At ``kappa=0`` this collapses to
independent Bernoulli(p); at ``kappa=1`` it is perfect agreement.

For each of ``M`` Monte Carlo replicates, the simulator draws
``n_patients * waves_per_patient`` iid samples from this joint
distribution and computes Cohen's kappa on the pooled 2x2 contingency.
The empirical SD of kappa-hat across replicates is the iid sampling
error.

Why iid (not Beta-Binomial patient mixture)?
---------------------------------------------

Cohen's pooled kappa is **not invariant to patient-level prevalence
heterogeneity**: when individual patients have very different
prevalences, the pooled marginals shift in a way that biases pooled
kappa-hat above the true within-patient kappa. The §4.8 protocol uses
**hierarchical kappa with patient random effects** (in PyMC) to handle
this correctly — that model estimates the population-mean agreement
parameter without the pooled-Cohen bias.

For the §6 sample-size **prework**, the simpler iid model plus a
post-hoc **design-effect inflation factor** matches the asymptotic-
normal credible-interval width that the §4.8 hierarchical PyMC model
produces under flat priors at large N. This is the textbook
sample-size derivation for clustered binary outcomes:

    SE_clustered = SE_iid * sqrt(1 + (m - 1) * ICC)

where ``m = waves_per_patient`` and ``ICC`` is the within-patient
intra-class correlation. The simulator reports both ``SE_iid`` (from
the empirical Monte Carlo) and ``SE_clustered`` (after multiplying by
the design-effect factor for the ``icc`` config field). The Phase 4.F
deliverable replaces this approximation with explicit PyMC NUTS
sampling on the hierarchical model.

Operating power
---------------

For the §6 H1.1 decision rule (`P(kappa > 0.40) >= 0.80`), under the
asymptotic normal credible-interval approximation::

    P(kappa > 0.40 | data) ~= 1 - Phi((0.40 - kappa_hat) / SE_kappa)

The decision rule fires when this exceeds 0.80, equivalently::

    kappa_hat - 0.84 * SE_kappa >= 0.40

The simulator reports the empirical fraction of replicates where this
fires as ``power_h11``. ``SE_kappa`` is the empirical SD across
replicates (the simulator does not use a per-replicate analytical SE
formula because the empirical SD is the more honest estimate at the
sample sizes considered).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np

__all__ = [
    "KAPPA_THRESHOLD_H11",
    "KAPPA_THRESHOLD_PROBABILITY_H11",
    "KappaCISimulationConfig",
    "KappaCISimulationResult",
    "_phi",
    "compute_cohens_kappa",
    "design_effect_factor",
    "run_kappa_simulation",
    "simulate_one_replicate",
]

KAPPA_THRESHOLD_H11 = 0.40
"""§6 H1.1 decision threshold: validation succeeds if posterior P(kappa > 0.40) is high.

Source: IMPLEMENTATION_PLAN.md §6 / governance/pre_registration_log.md.
"""

KAPPA_THRESHOLD_PROBABILITY_H11 = 0.80
"""§6 H1.1 posterior-probability threshold: P(kappa > 0.40) must be >= 0.80."""

# z critical for one-sided 80% normal probability:
# Phi(z) = 0.80 -> z = 0.8416212335729143  (used to determine when the
# decision rule is satisfied: kappa_hat - z * SE >= threshold).
_Z_FOR_80_PERCENT_PROB = 0.8416212335729143


def _phi(x: float) -> float:
    """Standard normal CDF using stdlib erf (no scipy dependency)."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


@dataclass(frozen=True)
class KappaCISimulationConfig:
    """Pinned configuration for a single (N, kappa, ICC) simulation cell."""

    n_patients: int
    waves_per_patient: int
    true_kappa: float
    marginal_prevalence: float
    icc: float
    n_replicates: int = 2000
    seed: int = 2026

    def __post_init__(self) -> None:
        if self.n_patients < 1:
            raise ValueError("n_patients must be >= 1")
        if self.waves_per_patient < 1:
            raise ValueError("waves_per_patient must be >= 1")
        if not 0.0 <= self.true_kappa <= 1.0:
            raise ValueError(f"true_kappa must be in [0,1], got {self.true_kappa}")
        if not 0.0 < self.marginal_prevalence < 1.0:
            raise ValueError(
                f"marginal_prevalence must be in (0,1), got {self.marginal_prevalence}"
            )
        if not 0.0 <= self.icc < 1.0:
            raise ValueError(f"icc must be in [0,1), got {self.icc}")
        # Joint-probability non-negativity: P(both 1) = p^2 + kappa*p*(1-p) needs >= 0
        # which is satisfied for kappa >= -p/(1-p); always true for kappa >= 0.
        if self.n_replicates < 2:
            raise ValueError("n_replicates must be >= 2 to compute SD")


@dataclass(frozen=True)
class KappaCISimulationResult:
    """Summary of a single simulation cell.

    Two SE / CI flavors are reported:

    * ``*_iid`` — the empirical iid sampling error on Cohen's kappa from
      the Monte Carlo (no clustering inflation). This is what you'd
      observe if every wave were an independent observation.
    * ``*_clustered`` — the iid SE inflated by the design-effect factor
      ``sqrt(1 + (m - 1) * ICC)``. This matches the asymptotic-normal
      credible-interval width the §4.8 hierarchical PyMC model produces
      at the configured ``icc``. **This is the headline number for the
      call.**
    """

    config: KappaCISimulationConfig
    # iid Monte Carlo
    kappa_hat_mean: float
    kappa_hat_sd_iid: float
    kappa_hat_q025_iid: float
    kappa_hat_q500_iid: float
    kappa_hat_q975_iid: float
    ci_full_width_95_iid: float
    ci_half_width_95_iid: float
    # Cluster-adjusted (design-effect inflated)
    design_effect_factor: float
    kappa_hat_sd_clustered: float
    ci_full_width_95_clustered: float
    ci_half_width_95_clustered: float
    # Operating characteristics under the cluster-adjusted SE
    power_h11: float
    posterior_prob_above_threshold_mean: float
    # Bookkeeping
    n_total_observations: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_table_row(self) -> dict[str, Any]:
        """Flat dict suitable for a Markdown / DataFrame row."""
        c = self.config
        return {
            "n_patients": c.n_patients,
            "waves_per_patient": c.waves_per_patient,
            "true_kappa": c.true_kappa,
            "icc": c.icc,
            "marginal_prevalence": c.marginal_prevalence,
            "n_total_obs": self.n_total_observations,
            "kappa_hat_mean": round(self.kappa_hat_mean, 4),
            "kappa_hat_sd_iid": round(self.kappa_hat_sd_iid, 4),
            "design_effect": round(self.design_effect_factor, 3),
            "kappa_hat_sd_clustered": round(self.kappa_hat_sd_clustered, 4),
            "ci_full_width_95_iid": round(self.ci_full_width_95_iid, 4),
            "ci_full_width_95_clustered": round(self.ci_full_width_95_clustered, 4),
            "ci_half_width_95_clustered": round(self.ci_half_width_95_clustered, 4),
            "power_h11": round(self.power_h11, 3),
            "p_above_0_40_mean": round(self.posterior_prob_above_threshold_mean, 3),
        }


# --------------------------------------------------------------------------- #
# Cohen's kappa
# --------------------------------------------------------------------------- #


def compute_cohens_kappa(comparator: np.ndarray, cinder: np.ndarray) -> float:
    """Cohen's kappa for paired binary classifications.

    Returns ``0.0`` when ``p_e == 1`` (degenerate marginals; both raters
    always say the same thing). Returns ``nan`` only if inputs are empty.
    """
    if comparator.shape != cinder.shape:
        raise ValueError("comparator and cinder arrays must be the same shape")
    if comparator.size == 0:
        return float("nan")
    n = comparator.size
    a = int(np.sum((comparator == 1) & (cinder == 1)))
    d = int(np.sum((comparator == 0) & (cinder == 0)))
    p_o = (a + d) / n
    p_yes_comp = float(np.mean(comparator))
    p_yes_cin = float(np.mean(cinder))
    p_e = p_yes_comp * p_yes_cin + (1.0 - p_yes_comp) * (1.0 - p_yes_cin)
    if p_e >= 1.0 - 1e-12:
        return 0.0
    return (p_o - p_e) / (1.0 - p_e)


# --------------------------------------------------------------------------- #
# Design-effect factor for clustered SE inflation
# --------------------------------------------------------------------------- #


def design_effect_factor(*, waves_per_patient: int, icc: float) -> float:
    """Multiplicative design-effect factor for clustered binary outcomes.

    Standard formula: ``sqrt(1 + (m - 1) * ICC)`` where ``m`` is the
    cluster size (waves per patient) and ``ICC`` is the within-cluster
    correlation. At ``icc=0`` this is 1 (no inflation, iid recovery).
    """
    if waves_per_patient < 1:
        raise ValueError("waves_per_patient must be >= 1")
    if not 0.0 <= icc < 1.0:
        raise ValueError(f"icc must be in [0,1), got {icc}")
    return math.sqrt(1.0 + (waves_per_patient - 1) * icc)


# --------------------------------------------------------------------------- #
# Per-replicate simulation
# --------------------------------------------------------------------------- #


def simulate_one_replicate(
    *,
    rng: np.random.Generator,
    n_patients: int,
    waves_per_patient: int,
    true_kappa: float,
    marginal_prev: float,
) -> tuple[np.ndarray, np.ndarray, float]:
    """One Monte Carlo replicate (iid baseline; ICC handled post-hoc).

    Generates ``n_patients * waves_per_patient`` iid samples from the
    symmetric-marginal joint distribution at ``(true_kappa,
    marginal_prev)`` and returns ``(comparator, cinder, kappa_hat)``.
    """
    n_obs = n_patients * waves_per_patient
    p = marginal_prev

    # Joint probabilities (symmetric marginals; constant across observations).
    p_both_1 = p**2 + true_kappa * p * (1.0 - p)
    p_both_0 = (1.0 - p) ** 2 + true_kappa * p * (1.0 - p)
    p_comp1_cin0 = p * (1.0 - p) * (1.0 - true_kappa)
    # p_comp0_cin1 = same as p_comp1_cin0 by symmetry

    # Cumulative thresholds for inverse-CDF sampling per observation.
    cum1 = p_both_1
    cum2 = p_both_1 + p_both_0
    cum3 = cum2 + p_comp1_cin0
    # cum4 = 1.0 by construction

    u = rng.random(n_obs)
    comparator = np.zeros(n_obs, dtype=np.int8)
    cinder = np.zeros(n_obs, dtype=np.int8)

    mask_both_1 = u < cum1
    mask_both_0 = (u >= cum1) & (u < cum2)
    mask_c1k0 = (u >= cum2) & (u < cum3)
    # mask_c0k1 = u >= cum3 (everything else)

    comparator[mask_both_1] = 1
    cinder[mask_both_1] = 1
    # both_0: leave as zeros
    comparator[mask_c1k0] = 1
    cinder[mask_c1k0] = 0
    comparator[~(mask_both_1 | mask_both_0 | mask_c1k0)] = 0
    cinder[~(mask_both_1 | mask_both_0 | mask_c1k0)] = 1

    kappa_hat = compute_cohens_kappa(comparator, cinder)
    return comparator, cinder, kappa_hat


# --------------------------------------------------------------------------- #
# Top-level simulation runner
# --------------------------------------------------------------------------- #


def run_kappa_simulation(config: KappaCISimulationConfig) -> KappaCISimulationResult:
    """Run the iid Monte Carlo and apply design-effect inflation for the
    cluster-adjusted SE / CI / power.
    """
    rng = np.random.default_rng(config.seed)
    kappas = np.empty(config.n_replicates, dtype=np.float64)
    for r in range(config.n_replicates):
        _, _, kappas[r] = simulate_one_replicate(
            rng=rng,
            n_patients=config.n_patients,
            waves_per_patient=config.waves_per_patient,
            true_kappa=config.true_kappa,
            marginal_prev=config.marginal_prevalence,
        )

    kappa_mean = float(np.mean(kappas))
    kappa_sd_iid = float(np.std(kappas, ddof=1))
    q025, q500, q975 = (float(x) for x in np.quantile(kappas, [0.025, 0.5, 0.975]))
    ci_full_iid = q975 - q025
    ci_half_iid = ci_full_iid / 2.0

    # Cluster-adjusted SE / CI via the standard design-effect formula.
    deff = design_effect_factor(
        waves_per_patient=config.waves_per_patient,
        icc=config.icc,
    )
    kappa_sd_clustered = kappa_sd_iid * deff
    # Asymptotic-normal CrI: width ~ 2 * 1.96 * SE.
    ci_full_clustered = 2.0 * 1.959963984540054 * kappa_sd_clustered
    ci_half_clustered = ci_full_clustered / 2.0

    # Operating power against H1.1, using the *cluster-adjusted* SE
    # (which is what the §4.8 hierarchical PyMC model would produce).
    if kappa_sd_clustered > 0.0:
        # The observed kappa-hat distribution is approximately
        # Normal(true_kappa, kappa_sd_clustered) under the §4.8 model.
        # We measure power as the fraction of replicate-scaled draws
        # under which the H1.1 decision rule fires. To do this honestly
        # without a separate Monte Carlo loop, rescale each iid
        # replicate's kappa-hat to the clustered sampling distribution
        # by inflating its deviation from the mean by deff:
        kappas_clustered_scaled = kappa_mean + (kappas - kappa_mean) * deff
        decision_fired = (
            kappas_clustered_scaled - _Z_FOR_80_PERCENT_PROB * kappa_sd_clustered
            >= KAPPA_THRESHOLD_H11
        )
        power = float(np.mean(decision_fired))
        z_per_rep = (kappas_clustered_scaled - KAPPA_THRESHOLD_H11) / kappa_sd_clustered
        post_prob_per_rep = np.array([_phi(z) for z in z_per_rep])
        post_prob_mean = float(np.mean(post_prob_per_rep))
    else:
        power = 1.0 if kappa_mean >= KAPPA_THRESHOLD_H11 else 0.0
        post_prob_mean = 1.0 if kappa_mean >= KAPPA_THRESHOLD_H11 else 0.0

    return KappaCISimulationResult(
        config=config,
        kappa_hat_mean=kappa_mean,
        kappa_hat_sd_iid=kappa_sd_iid,
        kappa_hat_q025_iid=q025,
        kappa_hat_q500_iid=q500,
        kappa_hat_q975_iid=q975,
        ci_full_width_95_iid=ci_full_iid,
        ci_half_width_95_iid=ci_half_iid,
        design_effect_factor=deff,
        kappa_hat_sd_clustered=kappa_sd_clustered,
        ci_full_width_95_clustered=ci_full_clustered,
        ci_half_width_95_clustered=ci_half_clustered,
        power_h11=power,
        posterior_prob_above_threshold_mean=post_prob_mean,
        n_total_observations=config.n_patients * config.waves_per_patient,
        metadata={
            "decision_rule": (
                f"P(kappa > {KAPPA_THRESHOLD_H11}) >= "
                f"{KAPPA_THRESHOLD_PROBABILITY_H11} (asymptotic normal CrI; "
                f"design-effect inflated)"
            ),
            "z_for_80_percent": _Z_FOR_80_PERCENT_PROB,
            "design_effect_formula": "sqrt(1 + (waves - 1) * icc)",
        },
    )
