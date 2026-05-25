"""cinder.bayes — vendored Bayesian kernel layer.

Vendored from ``2ndOpinionMD-MVP`` commit ``00eaa9eb`` per
``IMPLEMENTATION_PLAN.md`` "Decisions locked" (Option A). The kernel is the
deterministic, closed-form Python layer that produces per-patient posterior
``UncertaintyCarrier`` objects from a noarcs-shape PTV. No MCMC, no LLM I/O,
no tensors — every output is a function of inputs, so two runs on the same
evidence return identical posteriors.

The PyMC + ArviZ population-concordance and Aim 2 hierarchical layers
(per protocol §4.8) consume these per-patient UCs as inputs; they are NOT
in this package and live under ``analysis/concordance/`` and
``analysis/aim2/`` (Phase 7 work).

See ``cinder/bayes/PROVENANCE.md`` for the vendoring contract, the
re-vendoring procedure, the EoH stub policy, and the weak-prior fallback
semantics.

Public API
----------

Top-level primitive::

    from cinder.bayes import bayesian_update_uc, UncertaintyCarrier
    from cinder.bayes.graph import load_graph

    gh = load_graph("fixtures/real_ehr_632event/ptv_real_ehr_632event_v1_noarcs_scrubbed.json")
    uc = bayesian_update_uc(gh, hypothesis_id="flare_30d")
    print(uc.point_estimate, uc.band_90, uc.confidence_label)

Built-in hypotheses (Phase-1, weak priors): ``flare_30d``,
``progression_3mo``, ``taper_safety``. Each carries a default
``LikelihoodSpec`` that walks events and accumulates Beta-Bernoulli
evidence. Override the prior or the spec by passing them as kwargs.

MKG-informed priors (Phase 6, FORWARD-derived) are looked up via
``cinder.bayes.mkg_retrieval.fetch_mkg_bayes_prior``. Until that data
lands, the function returns ``None`` and the kernel uses the documented
weak priors per ``DEFAULT_HYPOTHESIS_PRIORS``.
"""

from __future__ import annotations

from .graph import GraphHandle, load_graph
from .kernels import (
    DEFAULT_HYPOTHESIS_PRIORS,
    BetaPrior,
    BetaUpdate,
    GammaPrior,
    GammaUpdate,
    LikelihoodSpec,
    NormalNormalPrior,
    NormalNormalUpdate,
    apply_likelihood_spec,
    bayesian_update_uc,
    default_likelihood_spec_for,
    update_beta_bernoulli,
    update_gamma_poisson,
    update_normal_normal,
)
from .mkg_retrieval import fetch_mkg_bayes_prior
from .uc import (
    UC_SCHEMA_VERSION,
    UncertaintyCarrier,
    canonical_spec_hash,
    confidence_from_band,
    confidence_label,
    render_handoff_posteriors,
)

__all__ = [  # noqa: RUF022 — grouped by surface (vendoring, primitive, kernels, DSL, priors, UC, MKG); not alpha
    # Vendoring identity
    "VENDORED_FROM",
    "VENDORED_AT_COMMIT",
    # Top-level primitive
    "bayesian_update_uc",
    # Graph loader
    "GraphHandle",
    "load_graph",
    # Conjugate updates
    "update_beta_bernoulli",
    "update_gamma_poisson",
    "update_normal_normal",
    # Likelihood DSL
    "LikelihoodSpec",
    "apply_likelihood_spec",
    "default_likelihood_spec_for",
    # Priors
    "BetaPrior",
    "GammaPrior",
    "NormalNormalPrior",
    "DEFAULT_HYPOTHESIS_PRIORS",
    # Update result containers
    "BetaUpdate",
    "GammaUpdate",
    "NormalNormalUpdate",
    # UncertaintyCarrier + helpers
    "UncertaintyCarrier",
    "UC_SCHEMA_VERSION",
    "confidence_from_band",
    "confidence_label",
    "canonical_spec_hash",
    "render_handoff_posteriors",
    # MKG prior lookup
    "fetch_mkg_bayes_prior",
]

VENDORED_FROM = "2ndOpinionMD-MVP"
VENDORED_AT_COMMIT = "00eaa9eb"
