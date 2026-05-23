"""CINDER analysis package — open statistical pipelines.

Sub-packages (populated in later phases):
- `analysis.simulation` — §6.1 sample-size simulation (two-layer: vendored Beta-
  Bernoulli + PyMC hierarchical kappa).
- `analysis.detection` — §4.4 / §4.6 per-patient flare detection orchestration.
- `analysis.matching` — §4.6 1:1 comparator matching rule.
- `analysis.concordance` — §4.8 hierarchical kappa model + frequentist sensitivity.
- `analysis.aim2` — §4.7 Aim 2 anticipation/widening UC analyses.
"""
