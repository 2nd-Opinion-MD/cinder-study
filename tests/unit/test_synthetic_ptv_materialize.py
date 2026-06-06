"""test_synthetic_ptv_materialize - Sprint 5 integration wrapper (arch Phase 5, M4-independent).

The real M4 module lives in 2OPMD's private EoH package and is not importable here, so the
M4-dependent scoring half of Phase 5 is out of scope for this repo. This test exercises the
half that needs no M4: the synthetic CSVs flow through Dylan's adapter to valid PTV-noarcs,
and the CLI --materialize-ptv path runs end-to-end.
"""

from __future__ import annotations

import json
from pathlib import Path

from cinder.ingest.forward_webquest_adapter import ForwardFieldSpec
from cinder.synthetic.cli import main
from cinder.synthetic.cohort import generate_cohort
from cinder.synthetic.emit_csv import write_cohort_csvs
from cinder.synthetic.ptv_materialize import materialize_ptv


def test_materialize_produces_one_record_per_patient(tmp_path: Path) -> None:
    spec = ForwardFieldSpec()
    records, _ = generate_cohort(40, seed=42)
    paths = write_cohort_csvs(records, tmp_path, spec)
    out = materialize_ptv(paths, tmp_path / "ptv_noarcs.json", spec)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["synthetic"] is True
    assert payload["schema"] == "ptv.2.1-indexed-v1-noarcs"
    assert len(payload["records"]) == 40


def test_cli_materialize_ptv_end_to_end(tmp_path: Path) -> None:
    rc = main(["--n", "20", "--seed", "7", "--out", str(tmp_path), "--materialize-ptv"])
    assert rc == 0
    assert (tmp_path / "ptv_noarcs.json").exists()
    assert (tmp_path / "answer_sheet.json").exists()
    for name in ("pro_long", "medications", "demographics"):
        assert (tmp_path / f"{name}.csv").exists()
