# `.CINDER_VENV` — the project virtual environment

Glass-box principle: this repo's runtime is not a black box.

The CINDER virtual environment is named **`.CINDER_VENV`** (not the implicit `.venv` default) so the activated shell prompt makes it obvious which project you're in:

```
(.CINDER_VENV) debian-dylan@magnifying-ocean:/mnt/c/2OPMD/cinder-study$
```

If your prompt does not start with `(.CINDER_VENV) `, you are not in the right environment. Re-activate before running anything in this repo.

The convention applies equally on Windows PowerShell:

```
(.CINDER_VENV) PS C:\2OPMD\cinder-study>
```

## What is in it

The venv is **not committed** (`.gitignore` blocks `.CINDER_VENV/` and `.CINDER_VENV_*/`). The contract for what the venv must contain is `pyproject.toml`. Everything below is reproducible from a clean clone in under five minutes on a native filesystem; significantly slower over WSL-on-NTFS (see "Filesystem performance gotcha" below).

### Pre-flight tier (runs every CI job; ~30 packages, ~50 MB on disk)

The minimum needed to run the five Phase 0 gates (`pytest`, `validate_schemas.py`, `pii_tripwire.py`, `ruff check`, `ruff format --check`):

| Package | Pinned via | Used for |
|---|---|---|
| `jsonschema` | `pyproject.toml` deps | Schema validation (Draft 2020-12) |
| `pytest` | `pyproject.toml` `[dev]` extra | Test runner |
| `ruff` | `pyproject.toml` `[dev]` extra | Format + lint |

These three pull in `attrs`, `colorama`, `iniconfig`, `pluggy`, `Pygments`, `referencing`, `rpds-py`, `typing_extensions`, `jsonschema-specifications`, and `packaging` as transitive deps.

### Analysis tier (full `pyproject.toml` deps; ~150 packages, ~1.5 GB on disk)

Required for Phase 2+ analysis work. Heavy because PyMC pulls a numerical stack:

| Package | Used for | Phase |
|---|---|---|
| `numpy` | numerical foundation | all |
| `pandas` | tabular FORWARD wave handling | 1, 2, 4 |
| `scipy` | optional fast path for `bayes.py` (Acklam fallback works without) | 4 |
| `pymc` | hierarchical Bayesian concordance model (§4.8) | 2, 5 |
| `arviz` | posterior diagnostics, plots, summaries | 2, 5 |
| `pyyaml` | likelihood spec files (`cinder_likelihood_spec.yaml`) | 4 |
| `mypy` | type-checker (CI gate) | dev only |
| `pre-commit` | hook runner | dev only |
| `nutpie` (`[sampling]` extra) | optional faster NUTS sampler | 2 |
| `jupyter`, `ipykernel`, `matplotlib` (`[notebook]` extra) | exploratory notebooks | dev only |

The Phase 0 commit ships a venv configured at the **pre-flight tier** so the gates are runnable immediately. Promote to the analysis tier with `pip install -e ".[dev]"` (and optionally `".[sampling,notebook]"`) when you start Phase 2 simulation work.

## Setup — Windows PowerShell (recommended on this machine)

Native Windows venv. Fast install, fast pytest, no NTFS-via-WSL overhead.

```powershell
cd c:\2OPMD\cinder-study
py -3.12 -m venv .CINDER_VENV --prompt .CINDER_VENV
.\.CINDER_VENV\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install jsonschema pytest ruff   # pre-flight tier
# Promote to analysis tier when needed:
# python -m pip install -e ".[dev]"
```

Once activated, the prompt becomes `(.CINDER_VENV) PS C:\2OPMD\cinder-study>` and every command can drop the long path:

```powershell
pytest tests\ -q
python scripts\validate_schemas.py
python scripts\pii_tripwire.py fixtures\
ruff check .
ruff format --check .
```

To deactivate: `deactivate`.

If `Activate.ps1` is blocked by execution policy, run once: `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`.

## Setup — WSL / Debian / Linux (preferred prompt aesthetic)

Two paths. Pick the right one based on **where you are checking out the repo**.

### Path A — Repo on Linux native filesystem (recommended)

Fast in every dimension. Clone or copy the repo to your Linux home, then:

```bash
cd ~/cinder-study
python3 -m venv .CINDER_VENV --prompt .CINDER_VENV
source .CINDER_VENV/bin/activate
python -m pip install --upgrade pip
python -m pip install jsonschema pytest ruff      # pre-flight tier
# Promote to analysis tier when needed:
# python -m pip install -e ".[dev]"
```

Prompt becomes `(.CINDER_VENV) debian-dylan@magnifying-ocean:~/cinder-study$`.

Once activated:

```bash
pytest tests/ -q
python scripts/validate_schemas.py
python scripts/pii_tripwire.py fixtures/
ruff check .
ruff format --check .
```

To deactivate: `deactivate`.

### Path B — Repo on `/mnt/c/...` (current setup) — works but slow

WSL accessing NTFS through `9p` is the well-known performance pitfall ([Microsoft's own guidance](https://learn.microsoft.com/en-us/windows/wsl/filesystems#file-storage-and-performance-across-file-systems)). Empirically on this repo:

- Linux venv creation on `/mnt/c/2OPMD/cinder-study/`: **~5.5 minutes**
- `pip install jsonschema pytest ruff` over `/mnt/c/`: **>12 minutes, did not finish**
- Same operations on Windows-native or Linux-native filesystem: **<2 minutes total**

If you must stay on `/mnt/c/`, use the same commands as Path A but expect every pip operation and pytest run to be 5-10x slower than native. The runtime correctness is identical; only wall-clock time changes.

A reasonable hybrid pattern is to keep the repo on `/mnt/c/` (so PowerShell tooling, file watchers, IDE, and Git can all see it natively) and create the venv on Linux native filesystem, pointing it at the project via `pip install -e /mnt/c/2OPMD/cinder-study`:

```bash
mkdir -p ~/venvs && cd ~/venvs
python3 -m venv cinder --prompt .CINDER_VENV
source cinder/bin/activate
python -m pip install --upgrade pip
python -m pip install jsonschema pytest ruff
python -m pip install -e /mnt/c/2OPMD/cinder-study
```

This puts the venv on the fast Linux filesystem while leaving the source tree on Windows-readable NTFS. `.gitignore` already covers `.CINDER_VENV/` and `.CINDER_VENV_*/` so the venv is invisible to Git from either side.

## Why we do not commit the venv

1. **Platform-specific binaries.** Windows `.CINDER_VENV/` and Linux `.CINDER_VENV/` cannot share content — `python.exe` vs `python`, `Scripts/` vs `bin/`, compiled wheels for the wrong OS or architecture would silently corrupt downstream behavior.
2. **Size.** Analysis-tier venv is ~1.5 GB. Repo would 30x in size and Git operations would crawl.
3. **Reproducibility.** `pyproject.toml` is the contract; the venv is the cache. Anyone with `pyproject.toml` and a network connection can rebuild an identical venv. The venv on disk is one of many possible materializations of the contract.
4. **The point of glass-box is not "store everything," it is "let the operator inspect everything."** `pyproject.toml` is the open spec; `python -m pip list` shows the live state; this document explains the relationship. That is glass-box. Committing a binary opaque blob would be black-box.

## Pinning policy

Currently the dependencies in `pyproject.toml` use lower-bound version specifiers (`>=1.26`, `>=2.1`, …). This is intentional during Phase 0–3 to let bug-fix releases flow through without churn. At `protocol-v3.0-FINAL` tag time:

1. Run `pip freeze > requirements.lock.txt` against a known-green CI run.
2. Commit `requirements.lock.txt` alongside the protocol commit.
3. Update CI to install from the lock file for the pre-registered protocol.
4. Note the lock-file commit in `governance/pre_registration_log.md` so external replicators can get bit-stable behavior.

Until tag time, lower-bound specs are the policy.

## Troubleshooting

**"`.CINDER_VENV/bin/activate: No such file or directory`"** — You are in WSL/bash but the venv was created from PowerShell as a Windows venv. Activation scripts on Windows live under `Scripts/`, not `bin/`. Either delete the Windows venv and recreate as Linux per Path A, or keep it Windows and use PowerShell.

**"Pip install hangs over 10 minutes"** — You are almost certainly on WSL pointing at `/mnt/c/`. See "Path B" above. Move the venv (or the repo) to a Linux-native filesystem.

**"Wrong Python version"** — `pyproject.toml` requires `>=3.11`. Confirm with `python --version` after activation. On Windows, `py -3.12 -m venv` selects Python 3.12. On Debian 12 the system Python is 3.11.2 which satisfies the constraint.

**"`Activate.ps1` blocked by policy"** — Run once per shell or per machine: `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`.

**"Prompt doesn't show `(.CINDER_VENV)`"** — The activate script wasn't actually sourced. On bash use `source .CINDER_VENV/bin/activate` (not just running the file); on PowerShell use `.\.CINDER_VENV\Scripts\Activate.ps1` (with the leading `.\`); on cmd.exe use `.CINDER_VENV\Scripts\activate.bat`.
