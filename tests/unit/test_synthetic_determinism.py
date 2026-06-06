"""test_synthetic_determinism - Sprint 4 determinism gate (C6, arch Phase 4).

Same seed -> byte-identical CSVs and answer sheet. Different seed -> different output.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from cinder.ingest.forward_webquest_adapter import ForwardFieldSpec
from cinder.synthetic import field_spec as fs
from cinder.synthetic.answer_sheet import write_answer_sheet
from cinder.synthetic.cohort import generate_cohort
from cinder.synthetic.emit_csv import write_cohort_csvs


def _emit(tmp: Path, seed: int, n: int = 60) -> dict[str, str]:
    spec = ForwardFieldSpec()
    records, answers = generate_cohort(n, seed)
    paths = write_cohort_csvs(records, tmp, spec)
    write_answer_sheet(
        answers, tmp / "answer_sheet.json", seed=seed, field_spec_hash=fs.field_spec_hash(spec)
    )
    files = {**dict(paths), "answer_sheet": tmp / "answer_sheet.json"}
    return {name: hashlib.sha256(Path(p).read_bytes()).hexdigest() for name, p in files.items()}


def test_same_seed_byte_identical(tmp_path: Path) -> None:
    a = _emit(tmp_path / "a", 42)
    b = _emit(tmp_path / "b", 42)
    assert a == b, "same seed produced different output (non-deterministic)"


def test_different_seed_differs(tmp_path: Path) -> None:
    a = _emit(tmp_path / "a", 42)
    c = _emit(tmp_path / "c", 43)
    assert a["pro_long"] != c["pro_long"]
    assert a["answer_sheet"] != c["answer_sheet"]
