"""cli.py - command-line entrypoint for the Track-1 generator.

    python -m cinder.synthetic.generate --n 200 --seed 42 --out <dir> \\
        [--emit-rapid3-subscores] [--materialize-ptv]

Writes the three FORWARD-export-shaped CSVs + answer_sheet.json into ``--out``. With
``--materialize-ptv`` it additionally runs Dylan's adapter to emit PTV-noarcs JSON (the
optional Sprint-5 wrapper). All output is synthetic and provenance-stamped.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from cinder.synthetic import field_spec as fs
from cinder.synthetic.answer_sheet import write_answer_sheet
from cinder.synthetic.cohort import generate_cohort
from cinder.synthetic.emit_csv import write_cohort_csvs

__all__ = ["build_parser", "main"]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m cinder.synthetic.generate",
        description="Generate a synthetic Track-1 RA cohort (CSVs + ground-truth answer sheet).",
    )
    p.add_argument("--n", type=int, default=200, help="number of patients")
    p.add_argument("--seed", type=int, default=42, help="top-level RNG seed (deterministic)")
    p.add_argument("--out", type=Path, required=True, help="output directory")
    p.add_argument(
        "--emit-rapid3-subscores", action="store_true", help="also emit RAPID3 FN/PN/PtGA rows"
    )
    p.add_argument(
        "--materialize-ptv", action="store_true", help="also write PTV-noarcs JSON via the adapter"
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    spec = fs.ForwardFieldSpec()
    records, answers = generate_cohort(
        args.n, args.seed, emit_rapid3_subscores=args.emit_rapid3_subscores
    )

    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    paths = write_cohort_csvs(records, out, spec)
    write_answer_sheet(
        answers, out / "answer_sheet.json", seed=args.seed, field_spec_hash=fs.field_spec_hash(spec)
    )

    print(f"synthetic cohort: {len(records)} patients, seed={args.seed} -> {out}")
    for name, path in paths.items():
        print(f"  {name}: {path.name}")
    print("  answer_sheet: answer_sheet.json")

    if args.materialize_ptv:
        from cinder.synthetic.ptv_materialize import materialize_ptv

        ptv_path = materialize_ptv(paths, out / "ptv_noarcs.json", spec)
        print(f"  ptv: {ptv_path.name}")
    return 0
