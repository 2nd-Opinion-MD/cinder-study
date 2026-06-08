"""params.py - typed parameter dataclasses mirroring the literature-cited spec.

Every value here traces to `CINDER_synthetic_generator_parameters_v1_1.md` (§1-§7),
which cites published RA cohort literature inline. Defaults are the starting calibration;
Sprint 1 verifies the emergent cohort against the §2 baselines, §3 ICCs, and §4
correlations and tunes the loadings/noise within these structures. Nothing here is drawn
independently of `field_spec` precision (C8) or M4 mechanics (C7).
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: Disease-activity states, ordered low -> high burden (§2).
STATES: tuple[str, ...] = ("remission", "low", "moderate", "high")


@dataclass(frozen=True, slots=True)
class DemographicsParams:
    """§1 - established-RA routine-care profile (ARAMIS/QUEST-RA/AMBRA)."""

    female_proportion: float = 0.72  # ARAMIS ~72%, AMBRA 70%
    seropositive_proportion: float = 0.70  # demographics.csv ra_seropositivity ~70% positive
    age_median: float = 58.0  # established RA, ARAMIS
    age_sd: float = 12.0
    disease_duration_median_yr: float = 8.0  # ARAMIS established cohort


@dataclass(frozen=True, slots=True)
class StateMixture:
    """§2 - routine-care disease-activity mixture (tune against FORWARD, §10)."""

    weights: dict[str, float] = field(
        default_factory=lambda: {"remission": 0.10, "low": 0.15, "moderate": 0.40, "high": 0.35}
    )


@dataclass(frozen=True, slots=True)
class StateBaseline:
    """§2 - state-conditioned instrument mean/SD in native units (HAQ 0-3, VAS 0-100)."""

    haq_mean: float
    haq_sd: float
    pain_mean: float
    pain_sd: float
    pga_mean: float
    pga_sd: float


def _default_baselines() -> dict[str, StateBaseline]:
    # Anchored to §2: routine HAQ-DI mean 1.18 (SD 0.79), PGA 28.8 (SD 24.8); active HAQ 1.6
    # (SD 0.7), Pain 62.7 (SD 22.8), PGA 63.9 (SD 22.0). Intermediate states interpolate.
    return {
        "remission": StateBaseline(0.40, 0.40, 15.0, 12.0, 15.0, 12.0),
        "low": StateBaseline(0.80, 0.55, 28.0, 18.0, 28.8, 18.0),
        "moderate": StateBaseline(1.18, 0.79, 45.0, 22.0, 45.0, 22.0),
        "high": StateBaseline(1.60, 0.70, 62.7, 22.8, 63.9, 22.0),
    }


@dataclass(frozen=True, slots=True)
class MeasurementICC:
    """§3 - test-retest ICC noise floor (Pincus 2009). Lower ICC -> noisier instrument."""

    haq: float = 0.90  # 0.897-0.961
    pain: float = 0.742
    pga: float = 0.702


@dataclass(frozen=True, slots=True)
class CorrelationStructure:
    """§4 - the covariance backbone (latent disease burden + AR(1) trajectory)."""

    target_corr_pain_pga: float = 0.70  # PGA best explained by VAS pain (adj R² up to 0.77)
    target_corr_pga_haq: float = 0.64  # adj R² ~0.41 -> r ~0.64
    beta_pain: float = 1.0  # heavy loading on shared latent L
    beta_pga: float = 1.0  # heavy loading on shared latent L
    beta_haq: float = 0.70  # moderate; HAQ carries extra independent variance (eta)
    rho_latent: float = 0.65  # AR(1) on L, wave-to-wave (0.6-0.7)
    rho_function: float = 0.80  # AR(1) on the sticky functional component η ("HAQ lags")


@dataclass(frozen=True, slots=True)
class MCID:
    """M4.B minimal-clinically-important-difference thresholds (worsening direction, C7)."""

    haq_ii: float = 0.22  # flare-associated HAQ shift mean 0.25 sits just over this
    pain_vas: float = 20.0
    pga_vas: float = 20.0


@dataclass(frozen=True, slots=True)
class FlareParams:
    """§5 - flare epidemiology and the visible/invisible measurement gap."""

    invisible_fraction: float = 0.35  # ~30-40% of true flares carry no escalation (Mollard)
    marginal_haq_excursion_mean: float = 0.25  # BeSt: flare HAQ shift ~0.25 vs MCID 0.22
    marginal_haq_excursion_sd: float = 0.12  # mode just over threshold, tail of severe flares
    base_flare_rate_per_wave: float = 0.30  # planted true-flare probability at eligible waves
    slow_drift_fraction: float = 0.10  # secondary loss-of-response trajectories (F4-CASE-08)
    min_lookback_wave: int = 2  # trajectory-sufficiency: detectable flares only at wave >= 2 (R3)


@dataclass(frozen=True, slots=True)
class ComorbidityParams:
    """§7 - the masking engine (FM/depression inflate Pain/PGA without inflammation)."""

    assign_fraction: float = 0.28  # ~20-35% carry a comorbidity flag
    fm_prevalence: float = 0.21  # pooled 18-24%
    depression_prevalence: float = 0.24  # 18-30%
    pain_offset_mean: float = 18.0  # additive Pain VAS elevation, no escalation
    pga_offset_mean: float = 16.0  # additive PGA elevation, no escalation
    # Extra Pain/PGA volatility on elevated waves, applied as additive Gaussian noise on the
    # STRUCTURAL channels with SD = (extra_volatility - 1.0) in standardized units (so 1.0 = no
    # extra volatility). NOT a multiplier on the §3 measurement-noise floor.
    extra_volatility: float = 1.4


@dataclass(frozen=True, slots=True)
class WaveParams:
    """§A3 - semi-annual cadence with modest jitter."""

    interval_days: int = 180
    jitter_days: int = 10
    min_waves: int = 4
    max_waves: int = 8
    default_waves: int = 4  # seed = 4


@dataclass(frozen=True, slots=True)
class GeneratorParams:
    """Top-level aggregate - the full Track-1 parameter set."""

    demographics: DemographicsParams = field(default_factory=DemographicsParams)
    state_mixture: StateMixture = field(default_factory=StateMixture)
    baselines: dict[str, StateBaseline] = field(default_factory=_default_baselines)
    icc: MeasurementICC = field(default_factory=MeasurementICC)
    correlation: CorrelationStructure = field(default_factory=CorrelationStructure)
    mcid: MCID = field(default_factory=MCID)
    flares: FlareParams = field(default_factory=FlareParams)
    comorbidity: ComorbidityParams = field(default_factory=ComorbidityParams)
    waves: WaveParams = field(default_factory=WaveParams)


def default_params() -> GeneratorParams:
    """Return the literature-default parameter set."""
    return GeneratorParams()
