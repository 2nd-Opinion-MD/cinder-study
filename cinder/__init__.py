"""CINDER — Co-occurrence INference for Disease Escalation in Rheumatology.

Open analysis pipeline package. Per protocol §10, this package holds:
- Open Bayesian conjugate kernels (vendored from 2ndOpinionMD-MVP commit 00eaa9eb)
- Open UncertaintyCarrier dataclass and serializers
- Open MKG-prior lookup with weak-prior fallback

Proprietary EoH modules (M2/M3/M6/M9/M62/M63) are NOT in this package; they
are imported from the 2OPMD private package by stable interface only.
"""

__version__ = "0.1.0-dev"
