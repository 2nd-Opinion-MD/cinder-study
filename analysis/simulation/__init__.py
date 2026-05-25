"""analysis.simulation — protocol §6 sample-size and power simulation.

Pre-Phase-4.F deliverable layer that supplies the §6 / §6.1 expected
posterior CI width on Cohen's kappa under the §4.8 hierarchical concordance
model, parameterized by:

* ``n_patients``: cohort size
* ``waves_per_patient``: number of FORWARD semi-annual waves observed per
  patient (default 4 for a 2-year window)
* ``true_kappa``: the latent true agreement between CINDER detection and
  the comparator (clinician-rated, OMERACT, or Mollard)
* ``marginal_prevalence``: per-wave flare prevalence under the comparator
* ``icc``: within-patient intra-class correlation (Beta-Binomial mixture)

Module organization:

* ``kappa_ci_simulator`` — the Monte Carlo core. Generates synthetic
  paired binary observations under a Beta-Binomial patient mixture with
  symmetric-marginal joint kappa, computes Cohen's kappa per replicate,
  and returns power / CI-width summary statistics.
* ``run_kappa_ci_simulation`` — orchestration. Reads ``inputs.yaml``,
  runs the parameter grid, writes ``results/kappa_ci_table.md`` and
  ``results/kappa_ci_results.json``.
* ``inputs.yaml`` — pinned parameter grid (seed=2026 per §13.4 confirmation).

Phase 4.F PyMC layer (``analysis/concordance/``) replaces the asymptotic
normal credible-interval approximation used here with explicit NUTS
sampling on the hierarchical model. The two are equivalent under flat
priors and large N; the asymptotic approximation here is appropriate
for the **prework** estimate, not the final §6 deliverable.
"""
