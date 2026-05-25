"""
run_kappa_ci_simulation.py — orchestration entry point for §6 prework.

Reads ``inputs.yaml``, runs the (n_patients * true_kappa * icc) parameter
grid, writes ``results/kappa_ci_table.md`` (human-readable for the call)
and ``results/kappa_ci_results.json`` (machine-readable for downstream).

Run as a module::

    python -m analysis.simulation.run_kappa_ci_simulation

Or with a non-default inputs file::

    python -m analysis.simulation.run_kappa_ci_simulation \\
        --inputs analysis/simulation/inputs.yaml

The output is committed to the repo (deterministic under seed=2026 per
§13.4) so the call cheat sheet can reference specific numbers without
requiring a re-run.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from analysis.simulation.kappa_ci_simulator import (
    KAPPA_THRESHOLD_H11,
    KAPPA_THRESHOLD_PROBABILITY_H11,
    KappaCISimulationConfig,
    KappaCISimulationResult,
    run_kappa_simulation,
)

DEFAULT_INPUTS = Path(__file__).resolve().parent / "inputs.yaml"


def _build_grid(inputs: dict[str, Any]) -> list[KappaCISimulationConfig]:
    configs: list[KappaCISimulationConfig] = []
    for n in inputs["n_patients"]:
        for k in inputs["true_kappa"]:
            for icc in inputs["icc"]:
                configs.append(
                    KappaCISimulationConfig(
                        n_patients=int(n),
                        waves_per_patient=int(inputs["waves_per_patient"]),
                        true_kappa=float(k),
                        marginal_prevalence=float(inputs["marginal_prevalence"]),
                        icc=float(icc),
                        n_replicates=int(inputs["n_replicates"]),
                        seed=int(inputs["seed"]),
                    )
                )
    return configs


def _format_markdown_table(results: list[KappaCISimulationResult], inputs: dict[str, Any]) -> str:
    """Render results as a Markdown report for human review (the call cheat sheet)."""
    rows = [r.as_table_row() for r in results]
    n_replicates = inputs["n_replicates"]
    seed = inputs["seed"]
    waves = inputs["waves_per_patient"]
    prev = inputs["marginal_prevalence"]
    threshold = inputs["threshold_kappa"]
    threshold_prob = inputs["threshold_probability"]

    icc_values = sorted({r.config.icc for r in results})
    n_patients_values = sorted({r.config.n_patients for r in results})
    true_kappa_values = sorted({r.config.true_kappa for r in results})

    today = datetime.now(UTC).strftime("%Y-%m-%d")

    parts: list[str] = []
    parts.append("# §6 sample-size prework — kappa CI width and operating power\n")
    parts.append(
        f"**Generated:** {today} UTC (deterministic; "
        f"seed={seed}, replicates per cell={n_replicates:,})\n"
    )
    parts.append(
        "**Source:** `analysis/simulation/run_kappa_ci_simulation.py` reading "
        "`analysis/simulation/inputs.yaml`. Pure-numpy iid Monte Carlo over "
        "the symmetric-marginal joint-kappa distribution at the configured "
        "(true_kappa, marginal_prevalence), with cluster-adjusted SE inflation "
        "via the design-effect factor `sqrt(1 + (m-1)*ICC)` (standard sample-size "
        "derivation for clustered binary outcomes). The Phase 4.F PyMC NUTS "
        "model on the §4.8 hierarchical kappa specification replaces this "
        "approximation; the two coincide under flat priors at these sample "
        "sizes (verified in `tests/unit/test_kappa_ci_simulator.py`).\n"
    )
    parts.append(
        f"**Decision rule (§6 H1.1):** posterior `P(kappa > {threshold}) >= "
        f"{threshold_prob}`. The `power_h11` column reports the empirical "
        "fraction of replicates where this rule fires.\n"
    )
    parts.append(
        f"**Fixed:** waves per patient = {waves}; per-wave marginal "
        f"flare prevalence = {prev:.2f}.\n"
    )

    # ------------------------------------------------------------------ #
    # One table per (icc, true_kappa) — most readable for the call.
    # ------------------------------------------------------------------ #
    parts.append("\n## Headline tables (CI width and power, by N)\n")
    parts.append(
        "_All CI widths and power numbers below are **cluster-adjusted** via "
        "the design-effect factor `sqrt(1 + (m-1)*ICC)` applied to the iid "
        "Monte Carlo SE (standard sample-size derivation for clustered binary "
        "outcomes). The Phase 4.F PyMC NUTS model replaces this approximation "
        "with explicit posterior samples; the two coincide under flat priors._\n"
    )
    for icc in icc_values:
        parts.append(f"\n### Within-patient ICC = {icc:.2f}\n")
        # CI full width (cluster-adjusted)
        parts.append("\n**Cluster-adjusted 95% CI full width on kappa-hat:**\n")
        parts.append(
            "\n| true kappa \\ N | " + " | ".join(str(n) for n in n_patients_values) + " |"
        )
        parts.append("|---" + "|---" * len(n_patients_values) + "|")
        for tk in true_kappa_values:
            cells = []
            for n in n_patients_values:
                r = next(
                    (
                        x
                        for x in results
                        if x.config.icc == icc
                        and x.config.true_kappa == tk
                        and x.config.n_patients == n
                    ),
                    None,
                )
                cells.append(f"{r.ci_full_width_95_clustered:.3f}" if r is not None else "—")
            parts.append(f"| **{tk:.2f}** | " + " | ".join(cells) + " |")

        # Power (H1.1, cluster-adjusted)
        parts.append(
            f"\n**Operating power against H1.1** "
            f"(`P(kappa > {threshold}) >= {threshold_prob}`, cluster-adjusted):\n"
        )
        parts.append(
            "\n| true kappa \\ N | " + " | ".join(str(n) for n in n_patients_values) + " |"
        )
        parts.append("|---" + "|---" * len(n_patients_values) + "|")
        for tk in true_kappa_values:
            cells = []
            for n in n_patients_values:
                r = next(
                    (
                        x
                        for x in results
                        if x.config.icc == icc
                        and x.config.true_kappa == tk
                        and x.config.n_patients == n
                    ),
                    None,
                )
                cells.append(f"{r.power_h11:.2f}" if r is not None else "—")
            parts.append(f"| **{tk:.2f}** | " + " | ".join(cells) + " |")

    # ------------------------------------------------------------------ #
    # Long-form per-cell detail.
    # ------------------------------------------------------------------ #
    parts.append("\n## Per-cell detail\n")
    parts.append(
        "\n| N | waves | true κ | ICC | prev | total obs | mean κ̂ | "
        "SD κ̂ (iid) | DEFF | SD κ̂ (clust.) | "
        "CI width (clust.) | half-width (clust.) | power H1.1 | mean P(κ>0.40) |"
    )
    parts.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for row in rows:
        parts.append(
            f"| {row['n_patients']} | {row['waves_per_patient']} | "
            f"{row['true_kappa']:.2f} | {row['icc']:.2f} | "
            f"{row['marginal_prevalence']:.2f} | {row['n_total_obs']} | "
            f"{row['kappa_hat_mean']:.4f} | {row['kappa_hat_sd_iid']:.4f} | "
            f"{row['design_effect']:.3f} | {row['kappa_hat_sd_clustered']:.4f} | "
            f"{row['ci_full_width_95_clustered']:.4f} | "
            f"{row['ci_half_width_95_clustered']:.4f} | "
            f"{row['power_h11']:.3f} | {row['p_above_0_40_mean']:.3f} |"
        )

    # ------------------------------------------------------------------ #
    # Pre-call talking-points anchor.
    # ------------------------------------------------------------------ #
    parts.append("\n## Implications for the 2026-05-26 call (A4 ask)\n")
    # Pick the two cells most useful for the call: N=50 at moderate ICC and N=100.
    n50_icc30 = [r for r in results if r.config.n_patients == 50 and r.config.icc == 0.30]
    n100_icc30 = [r for r in results if r.config.n_patients == 100 and r.config.icc == 0.30]
    if n50_icc30:
        parts.append("\n**At N=50 with moderate within-patient ICC=0.30:**\n")
        for r in sorted(n50_icc30, key=lambda x: x.config.true_kappa):
            parts.append(
                f"- True κ = {r.config.true_kappa:.2f}: "
                f"95% CI width = {r.ci_full_width_95_clustered:.3f}, "
                f"H1.1 power = {r.power_h11:.2f}"
            )
    if n100_icc30:
        parts.append("\n**At N=100 with moderate within-patient ICC=0.30:**\n")
        for r in sorted(n100_icc30, key=lambda x: x.config.true_kappa):
            parts.append(
                f"- True κ = {r.config.true_kappa:.2f}: "
                f"95% CI width = {r.ci_full_width_95_clustered:.3f}, "
                f"H1.1 power = {r.power_h11:.2f}"
            )
    parts.append(
        "\nUse these numbers verbatim if Adam asks why we want N=100 over N=50, "
        "or if Kaleb asks how confident we are at N=50 alone."
    )

    return "\n".join(parts) + "\n"


def _to_json_payload(
    results: list[KappaCISimulationResult], inputs: dict[str, Any]
) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": inputs,
        "decision_rule": {
            "threshold_kappa": KAPPA_THRESHOLD_H11,
            "threshold_probability": KAPPA_THRESHOLD_PROBABILITY_H11,
            "description": (
                "§6 H1.1: posterior P(kappa > 0.40) >= 0.80 "
                "(asymptotic normal CrI; PyMC NUTS replaces this in Phase 4.F)"
            ),
        },
        "results": [r.as_table_row() for r in results],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="analysis.simulation.run_kappa_ci_simulation",
        description="§6 sample-size simulation prework runner.",
    )
    parser.add_argument(
        "--inputs",
        type=Path,
        default=DEFAULT_INPUTS,
        help="Path to inputs YAML (default: analysis/simulation/inputs.yaml).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Override output directory (default: <inputs.yaml dir>/<output_dir>).",
    )
    args = parser.parse_args(argv)

    inputs = yaml.safe_load(args.inputs.read_text(encoding="utf-8"))
    out_dir = args.out_dir or (args.inputs.parent / inputs["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    configs = _build_grid(inputs)
    print(
        f"running {len(configs)} cells x {inputs['n_replicates']} replicates "
        f"= {len(configs) * inputs['n_replicates']:,} kappa-hat draws...",
        file=sys.stderr,
    )

    results: list[KappaCISimulationResult] = []
    for i, cfg in enumerate(configs, 1):
        r = run_kappa_simulation(cfg)
        results.append(r)
        print(
            f"  [{i}/{len(configs)}] N={cfg.n_patients:>3d} "
            f"k_true={cfg.true_kappa:.2f} ICC={cfg.icc:.2f} "
            f"-> k_hat={r.kappa_hat_mean:.3f} +/- "
            f"{r.kappa_hat_sd_clustered:.3f} (clust. width "
            f"{r.ci_full_width_95_clustered:.3f}, power {r.power_h11:.2f})",
            file=sys.stderr,
        )

    table_path = out_dir / inputs["table_filename"]
    json_path = out_dir / inputs["json_filename"]

    table_path.write_text(_format_markdown_table(results, inputs), encoding="utf-8")
    json_path.write_text(
        json.dumps(_to_json_payload(results, inputs), indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print(f"\nwrote {table_path}", file=sys.stderr)
    print(f"wrote {json_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
