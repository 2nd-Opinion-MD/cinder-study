#!/usr/bin/env python3
"""Export F4 V1 variant-0 patients to fixtures/golden/CASE-*/.

Writes pro_long.csv, medications.csv, demographics.csv, answer_sheet.json
for each V1 case (CASE-01, CASE-04, CASE-06, CASE-08) at variant_seed=0.

Patient IDs in goldens use the case id (e.g. CASE-01) without the -v00 suffix.
Answer-sheet provenance seed is f4_seed(case_id, 0).

Usage:
    python scripts/export_f4_golden_fixtures.py
    python scripts/export_f4_golden_fixtures.py --case CASE-04
    python scripts/export_f4_golden_fixtures.py --root /path/to/cinder-study
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cinder.synthetic import field_spec as fs  # noqa: E402
from cinder.synthetic.answer_sheet import write_answer_sheet  # noqa: E402
from cinder.synthetic.emit_csv import write_cohort_csvs  # noqa: E402
from cinder.synthetic.f4._common import f4_seed  # noqa: E402
from cinder.synthetic.f4.catalog import V1_CASES  # noqa: E402
from cinder.synthetic.f4.instantiate import instantiate_f4_case  # noqa: E402


def export_case(case_id: str, golden_root: Path, *, n_waves: int = 6) -> Path:
    """Write one CASE-* golden directory; return the output path."""
    record, answer = instantiate_f4_case(case_id, 0, n_waves=n_waves)
    record.patient_id = case_id
    answer.patient_id = case_id

    out = golden_root / case_id
    out.mkdir(parents=True, exist_ok=True)
    spec = fs.ForwardFieldSpec()
    write_cohort_csvs([record], out, spec)
    write_answer_sheet(
        [answer],
        out / "answer_sheet.json",
        seed=f4_seed(case_id, 0),
        field_spec_hash=fs.field_spec_hash(spec),
    )
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Export F4 variant-0 golden fixtures.")
    p.add_argument("--root", type=Path, default=ROOT, help="cinder-study repo root")
    p.add_argument("--case", action="append", help="export one case (repeatable)")
    p.add_argument("--waves", type=int, default=6, help="waves per patient")
    args = p.parse_args(argv)

    golden_root = args.root / "fixtures" / "golden"
    cases = [c.case_id for c in V1_CASES]
    if args.case:
        unknown = set(args.case) - set(cases)
        if unknown:
            p.error(f"unknown case(s): {sorted(unknown)}")
        cases = args.case

    for case_id in cases:
        out = export_case(case_id, golden_root, n_waves=args.waves)
        print(f"exported {case_id} variant-0 -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
