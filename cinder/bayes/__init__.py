"""cinder.bayes — vendored Bayesian kernel layer.

Vendored from `2ndOpinionMD-MVP` commit `00eaa9eb` per IMPLEMENTATION_PLAN.md
"Reusable foundation" section (Option A). Source modules:

- `kernels.py` ← `server/ptv_toolkit/bayes.py` (closed-form conjugate kernels +
  LikelihoodSpec executor + bayesian_update_uc primitive).
- `uc.py` ← `server/eoh/uc.py` (UncertaintyCarrier dataclass, serializers,
  confidence_from_band, canonical_spec_hash).
- `mkg_priors.py` ← `server/scripts/mkg_retrieval_harness.py::fetch_mkg_bayes_prior`
  (population-prior lookup with weak fallback).

Phase 4 of the implementation plan vendors these in. This `__init__.py` will
re-export the public API once the modules land. Until then it is a placeholder
to register the package.
"""
