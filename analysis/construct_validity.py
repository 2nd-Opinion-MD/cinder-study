"""construct_validity.py - compute + persist the synthetic cohort's construct-validity stats.

Deterministic. Generates a Track-1 cohort in-process and reports the quantities the
ACR instrument-validation abstract cites: inter-PRO correlations, a stable-window
test-retest reliability proxy per instrument, the axiom-invisible flare fraction
(designed-in vs realized), and the comorbidity-driven false-positive structure.

    python -m analysis.construct_validity --n 1000 --seed 42 --out analysis/results/construct_validity.json

Every number here is a property of synthetic data and is labeled as such.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from cinder.synthetic.cohort import generate_cohort

_INSTR = ["HAQ-II", "PainVAS", "PatientGlobalVAS", "RAPID3"]


def _wide(records):
    """Return {instrument: list[score]} aligned per patient-wave, plus stable-pair index."""
    cols: dict[str, list[float]] = {k: [] for k in _INSTR}
    for rec in records:
        for w in rec.waves:
            byname = {o.instrument: o.score for o in w.observations}
            for k in _INSTR:
                cols[k].append(float(byname[k]))
    return {k: np.array(v) for k, v in cols.items()}


def _retest(records, answers):
    """Stable-window test-retest proxy: Pearson r between consecutive waves where BOTH
    waves are ground-truth stable (no true flare, no comorbidity elevation)."""
    pairs = {k: ([], []) for k in _INSTR}
    for rec, ans in zip(records, answers, strict=True):
        stable = {wa.wave_number for wa in ans.per_wave
                  if not wa.true_flare and wa.expected_UC_behavior == "stable"}
        by_w = {w.wave_number: {o.instrument: o.score for o in w.observations} for w in rec.waves}
        for w in sorted(by_w):
            if w in stable and (w - 1) in stable:
                for k in _INSTR:
                    pairs[k][0].append(by_w[w - 1][k])
                    pairs[k][1].append(by_w[w][k])
    out = {}
    for k, (a, b) in pairs.items():
        out[k] = {"n_pairs": len(a),
                  "retest_r": round(float(np.corrcoef(a, b)[0, 1]), 3) if len(a) > 2 else None}
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=1000)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", type=Path, default=Path("analysis/results/construct_validity.json"))
    args = p.parse_args(argv)

    records, answers = generate_cohort(args.n, args.seed)
    cols = _wide(records)

    def r(a, b):
        return round(float(np.corrcoef(cols[a], cols[b])[0, 1]), 3)

    n_waves = sum(len(rec.waves) for rec in records)
    true_flares = [wa for ans in answers for wa in ans.per_wave if wa.true_flare]
    invisible = [wa for wa in true_flares if wa.flare_class == "axiom_invisible"]
    comorbid_pts = [ans for ans in answers if ans.comorbidity_flags]
    comorbid_fp = [wa for ans in answers for wa in ans.per_wave
                   if wa.flare_driver == "comorbidity_driven"]

    report = {
        "provenance": {"generator": "cinder.synthetic", "n_patients": args.n,
                       "seed": args.seed, "data_type": "SYNTHETIC (literature-parameterized)"},
        "cohort": {"n_patients": args.n, "n_patient_waves": n_waves,
                   "n_true_flares": len(true_flares),
                   "n_comorbid_patients": len(comorbid_pts),
                   "comorbid_fraction": round(len(comorbid_pts) / args.n, 3)},
        "inter_pro_correlation": {
            "pain_vs_pga": r("PainVAS", "PatientGlobalVAS"),
            "pga_vs_haq": r("PatientGlobalVAS", "HAQ-II"),
            "pain_vs_haq": r("PainVAS", "HAQ-II"),
            "targets": {"pain_vs_pga": 0.70, "pga_vs_haq": 0.64},
        },
        "test_retest_proxy": _retest(records, answers),
        "flare_gap": {
            "n_true_flares": len(true_flares),
            "n_axiom_invisible": len(invisible),
            "axiom_invisible_fraction": round(len(invisible) / len(true_flares), 3) if true_flares else None,
            "designed_target_range": [0.30, 0.40],
        },
        "comorbidity_false_positives": {
            "n_comorbidity_driven_waves": len(comorbid_fp),
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
