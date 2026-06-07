---
title: §13.4 Confirmation — Statistical Software Platform (§4.8)
status: confirmed
phase: 1
gate: §13.4
date: 2026-05-24
implementer: Dylan McCapes
senior_approver: Andras Hangyal (pending)
---

# §13.4 Confirmation — Statistical Software Platform

## Question (verbatim §13.4)

> Dylan confirms PyMC as the implementation platform (per §4.8).

## Answer

**PyMC confirmed.** No Stan, no JAGS, no edward2. Two-layer architecture: closed-form conjugate kernels for the per-patient detection layer (vendored from `2ndOpinionMD-MVP@00eaa9eb` per locked decision in `IMPLEMENTATION_PLAN.md` "Decisions locked"); PyMC for the population concordance and Aim 2 hierarchical layers.

This memo also pins three implementation choices §4.8 leaves under-specified: sampler, random seed policy, and posterior-summary toolchain.

## Evidence

### Why PyMC (and not Stan)

Protocol §4.8 commits explicitly: *"Software: PyMC."* This was the resolution of `Review Minor 1`, which previously read "PyMC or Stan" and was tightened to "PyMC" before the v3 freeze. The decision is recorded in the v3 audit trail: changelog line 36, `"§4.8: replaced 'PyMC or Stan' with PyMC [Review Minor 1]; fixed sensitivity analysis to agreement-oriented specification [Review Major 5]"`.

Operational reasons that backed the decision (for future replicators reading this memo):

1. **Python homogeneity.** The vendored Bayesian kernel layer (closed-form Beta-Bernoulli, Gamma-Poisson, Normal-Normal) is Python; the FORWARD ingest tooling is Python; the M2/M3/M6/M9/M62/M63 EoH module interfaces are Python. Adding R/Stan would multiply the language boundary count and the surface area for replicator setup. PyMC keeps the entire pipeline single-language.
2. **PyTensor / JAX backend optionality.** PyMC ≥ 5 supports both PyTensor (default) and JAX backends. JAX is available if §6.1 simulation throughput becomes a bottleneck (10,000 draws is currently within reach of the default PyTensor backend on a workstation; JAX is an opt-in optimization, not a v3.0-FINAL requirement).
3. **ArviZ ecosystem.** Posterior summaries, credible intervals, posterior predictive checks, divergence diagnostics, trace plots — all standard PyMC + ArviZ companions. The §6 / §6.1 deliverable ("97.5th − 2.5th percentile of posterior kappa") maps directly to `arviz.summary(idata, hdi_prob=0.95)`.
4. **Replicability commitment.** §10's blinded external re-run pathway requires that an external auditor can re-execute the analysis; Python + PyMC has lower replicator friction than R + Stan + rstan, particularly across the Linux/Windows CI matrix.

**No Stan branch.** If PyMC is later found to have a hard limitation (e.g., a non-conjugate model that NUTS cannot sample efficiently), the right escalation is `nutpie` (a faster NUTS implementation that wraps PyMC's compiled posterior-log-density function) — not Stan. `nutpie` is already declared in `pyproject.toml` `[sampling]` extras as an opt-in dependency.

### Sampler choice

**Decision: default NUTS via `pm.sample()` for v3.0-FINAL pre-registration; `nutpie` opt-in for production scale-up.**

PyMC's default sampler since 5.x is NUTS with adaptive step size and adaptive mass matrix, sampling via `pm.sample(draws=N, tune=T, chains=4, target_accept=0.9, ...)`. For the §6.1 simulation (10,000 draws on a hierarchical Beta-Bernoulli concordance model with patient-level random effects), the default sampler is more than sufficient.

`nutpie` is a Rust-based NUTS implementation that compiles the posterior log-density to LLVM and samples 3-10x faster than PyMC's default backend on hierarchical models. Listed in `pyproject.toml::project.optional-dependencies.sampling` as an opt-in. **Not** required for v3.0-FINAL; **may be** swapped in transparently for Phase 2 simulation runs if wall-clock becomes a constraint, recorded in `analysis/simulation/inputs.yaml::sampler` for traceability.

The sampler choice is invariant for the protocol's Bayesian inference (both produce posterior draws from the same target distribution); only wall-clock changes.

### Random seed policy

**Decision: `seed = 2026` pinned globally for the v3.0-FINAL protocol; recorded in `analysis/simulation/inputs.yaml`.**

The protocol §6.1 specifies 10,000 simulation draws but does not pin a random seed. For pre-registration to be meaningful (reproducible posterior CI widths reported in §6 with 4-decimal precision per Phase 2 acceptance criteria), the seed must be pinned.

| Surface | Seed handling |
|---|---|
| `analysis/simulation/run_simulation.py` | `numpy.random.default_rng(2026)` at the top of the script; passed explicitly to every random-data-generating call |
| `pm.sample(..., random_seed=2026, ...)` | Pinned at the same value, fed into PyMC's NUTS initialization |
| `analysis/simulation/inputs.yaml` | `seed: 2026` declared, with comment `"Pinned at v3.0-FINAL; do not change without protocol amendment + governance log entry"` |
| Reproducibility test (Phase 2 deliverable 4) | `tests/regression/test_simulation_reproducibility.py` re-runs the simulation with seed=2026 and asserts bit-stable output across runs |

Seed 2026 chosen for unambiguous reading; not stochastically meaningful. Any future seed change requires:
1. Protocol amendment (in `governance/pre_registration_log.md` amendment procedure).
2. Re-running §6 sample-size simulation under new seed.
3. Updating §6 numeric results if posterior CI width shifts > 0.005 absolute.

### Posterior-summary toolchain

**Decision: ArviZ for all posterior summaries, credible intervals, posterior predictive checks, and trace diagnostics.**

ArviZ is the standard companion to PyMC and is declared in `pyproject.toml::project.dependencies` (not optional). It produces:

| Protocol requirement | ArviZ entry point |
|---|---|
| §6.1 "97.5th − 2.5th percentile of posterior kappa" interval width | `az.hdi(idata, hdi_prob=0.95)` for HDI; or manual `np.quantile(..., [0.025, 0.975])` for the explicit equal-tail interval |
| §4.8 "posterior credible intervals reported on Cohen's kappa, sensitivity, specificity, PPV, NPV" | `az.summary(idata, var_names=["kappa", "sensitivity", "specificity", "ppv", "npv"], hdi_prob=0.95)` |
| §4.8 "posterior predictive checks are reported as a routine diagnostic" | `pm.sample_posterior_predictive` + `az.plot_ppc` |
| Aim 2 "posterior probability ≥ 0.80 that the target proportion exceeds its null reference" | `(idata.posterior["proportion"] > null_ref).mean().item()` direct posterior probability computation |
| §6 H1.1 decision rule "posterior probability that kappa > 0.40 is ≥ 0.80" | `(idata.posterior["kappa"] > 0.40).mean().item()` |

ArviZ outputs are saved as NetCDF (`idata.to_netcdf("analysis/simulation/results/idata.nc")`) for full fidelity, plus markdown tables for human reading. NetCDF format is open, language-agnostic, and replicator-friendly per §10.

### Software versions for v3.0-FINAL

`pyproject.toml` currently declares lower-bound version specifiers (`>=` rather than `==`). Per the pinning policy in `VENV.md`, this becomes:

| Package | Lower bound (Phase 0–3) | v3.0-FINAL pin (Phase 3) |
|---|---|---|
| `pymc` | `>=5.10` | exact pin via `requirements.lock.txt` |
| `arviz` | `>=0.17` | exact pin |
| `numpy` | `>=1.26` | exact pin |
| `scipy` | `>=1.11` | exact pin |
| `pandas` | `>=2.1` | exact pin |
| `nutpie` (optional) | `>=0.13` | exact pin if used |

The v3.0-FINAL tag commit will include `requirements.lock.txt` (output of `pip freeze` against a known-green CI run on Linux + Windows × Python 3.11 + 3.12). External replicators reproducing the pre-registered analysis install from the lock file; bug-fix updates to dependencies between v3.0-FINAL and v3.1 are tracked as protocol amendments in `governance/pre_registration_log.md`.

## Net assessment

**§13.4 confirmed.** Software is PyMC + ArviZ. Sampler is default NUTS for pre-registration with `nutpie` as an opt-in performance escape hatch. Seed is `2026`. Versions become bit-stable at v3.0-FINAL via `requirements.lock.txt`.

This memo is complete. No FORWARD-side or Adam-side dependencies. No protocol revision is needed.

The only outstanding work tied to this gate is the actual Phase 2 simulation execution (which produces the §6 numeric update and the H1.1 decision-rule re-confirmation under simulated data). That work is gated on the Phase 4 Bayes vendoring (locked decision; vendoring is the next forward step per `IMPLEMENTATION_PLAN.md`).

## Proposed code path

```
analysis/
  simulation/
    inputs.yaml                              # pinned parameters incl. seed=2026, sampler choice
    run_simulation.py                        # entry point; uses PyMC + cinder.bayes
    posterior_summary.py                     # ArviZ wrappers for §6 + §4.8 outputs
    results/
      idata.nc                               # NetCDF posterior draws (full fidelity)
      kappa_ci_width.md                      # human-readable §6 update
  concordance/
    hierarchical_kappa.py                    # PyMC model spec (Beta(2,5) prior, patient REs)
    sensitivity_frequentist.py               # Sensitivity Analysis 1 (mixed-effects logistic)
tests/
  regression/
    test_simulation_reproducibility.py       # bit-stable output under seed=2026
pyproject.toml
  # pinning policy: lower-bound -> exact at v3.0-FINAL
requirements.lock.txt                        # NEW at v3.0-FINAL tag time
```

## Approval

| Role | Name | Date | Commit |
|---|---|---|---|
| Implementer | Dylan McCapes | 2026-05-24 | `<FILL AT COMMIT>` |
| Senior approver | Andras Hangyal | pending | — |
