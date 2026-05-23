# Notebooks

Exploratory notebooks. Stage notebooks here for inspection, prototyping, and figure rendering. Production analyses live in `analysis/` as importable Python modules.

## Conventions

1. **No PII in notebook outputs.** Cleared cell outputs before commit (or use `nbstripout`). The PII tripwire will scan notebooks too.
2. **Reference fixtures only.** Notebooks must read from `fixtures/` — never from local-only data paths.
3. **Reproducible.** Every notebook starts with a metadata cell stating: input fixture path + SHA-256, schema version, expected runtime, dependencies beyond `[notebook]` extras.
4. **Promotion path.** Once a notebook stabilizes, port the analysis logic into `analysis/` as testable modules and leave the notebook as a presentation layer that imports from the package.

## First notebooks (Phase 1+)

- `01_inspect_real_ehr_632event.ipynb` — load the reference PTV, render event-type histogram, escalation timeline, RAPID3-component coverage, and the section-header / chapter_id distribution. Used for FORWARD/UNMC walkthrough material.
- `02_bayes_baseline_demo.ipynb` — run vendored `bayesian_update_uc` on the reference PTV with weak prior + default likelihood spec; render posterior trace + UC handoff block.
- `03_simulation_priors.ipynb` — sandbox for §6.1 sample-size simulation parameter grid before locking into `analysis/simulation/`.
