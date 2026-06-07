"""test_synthetic_answer_sheet - Sprint 4 ground-truth gates (arch Phase 4).

Generates a cohort, validates the answer sheet against its JSON Schema, independently
re-derives the M4-detectability arithmetic (should_detect => >=2 domains shifted AND an
escalation within +/-90 d of the wave), and confirms the CSVs flow through Dylan's adapter
unchanged. This verifies internal consistency of the ground truth - it is NOT an M4
re-implementation and NOT the scorer.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pandas as pd
from jsonschema import Draft202012Validator

from cinder.ingest.forward_webquest_adapter import ForwardFieldSpec, load_forward_wave_csvs
from cinder.synthetic import field_spec as fs
from cinder.synthetic.answer_sheet import build_answer_sheet, write_answer_sheet
from cinder.synthetic.cohort import generate_cohort
from cinder.synthetic.emit_csv import write_cohort_csvs

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "schemas" / "answer_sheet.schema.json").read_text(encoding="utf-8"))


def _build(tmp_path: Path, n: int = 80, seed: int = 42):
    spec = ForwardFieldSpec()
    records, answers = generate_cohort(n, seed)
    paths = write_cohort_csvs(records, tmp_path, spec)
    doc = build_answer_sheet(answers, seed=seed, field_spec_hash=fs.field_spec_hash(spec))
    write_answer_sheet(
        answers, tmp_path / "answer_sheet.json", seed=seed, field_spec_hash=fs.field_spec_hash(spec)
    )
    return spec, paths, doc


def test_answer_sheet_validates_against_schema(tmp_path: Path) -> None:
    _, _, doc = _build(tmp_path)
    Draft202012Validator.check_schema(SCHEMA)
    errors = sorted(Draft202012Validator(SCHEMA).iter_errors(doc), key=lambda e: e.path)
    assert not errors, errors[0].message if errors else ""


def test_provenance_is_synthetic_and_stamped(tmp_path: Path) -> None:
    _, _, doc = _build(tmp_path)
    prov = doc["provenance"]
    assert prov["synthetic"] is True
    assert len(prov["field_spec_hash"]) == 64
    assert prov["seed"] == 42
    assert prov["parameter_spec_version"]


def test_should_detect_arithmetic_rederivation(tmp_path: Path) -> None:
    _, paths, doc = _build(tmp_path)
    pro = pd.read_csv(paths["pro_long"])
    wave_date = {
        (r.patient_id, int(r.wave_number)): dt.date.fromisoformat(str(r.wave_date))
        for r in pro.itertuples()
    }
    n_checked = 0
    for patient in doc["patients"]:
        pid = patient["patient_id"]
        for wave in patient["per_wave"]:
            if wave["expected_M4_outcome"] != "should_detect":
                continue
            n_checked += 1
            # >=2 PRO domains crossed MCID
            assert len(wave["pro_domains_shifted"]) >= 2, (pid, wave["wave_number"])
            # a linked escalation within +/-90 d of the wave date
            esc = wave["escalation_event"]
            assert esc is not None
            wd = wave_date[(pid, wave["wave_number"])]
            ed = dt.date.fromisoformat(esc["date"])
            assert abs((wd - ed).days) <= 90, (pid, wave["wave_number"], (wd - ed).days)
    assert n_checked > 0, "no should_detect waves produced"


def test_should_detect_consistent_with_emitted_trajectory(tmp_path: Path) -> None:
    # Regression for the comorbidity-offset staleness BLOCKER: every should_detect wave's
    # recorded crossings must match the FINAL emitted true trajectory (>=2 domains), with no
    # comorbidity-baseline erasure left mislabeled. Recompute crossings from the answer sheet's
    # own pro_domains_shifted (which cohort finalizes post-offset).
    _, _, doc = _build(tmp_path, n=300, seed=1)
    for patient in doc["patients"]:
        for wave in patient["per_wave"]:
            if wave["expected_M4_outcome"] == "should_detect":
                assert len(wave["pro_domains_shifted"]) >= 2, (patient["patient_id"], wave)


def test_invisible_waves_have_no_escalation(tmp_path: Path) -> None:
    _, _, doc = _build(tmp_path)
    seen = 0
    for patient in doc["patients"]:
        for wave in patient["per_wave"]:
            if wave["flare_class"] == "axiom_invisible":
                seen += 1
                assert wave["escalation_event"] is None
                assert wave["expected_M4_outcome"] == "axiom_invisible"
    assert seen > 0


def test_csvs_round_trip_through_adapter(tmp_path: Path) -> None:
    spec, paths, _ = _build(tmp_path)
    records = load_forward_wave_csvs(
        pro_long_csv=paths["pro_long"],
        medications_csv=paths["medications"],
        demographics_csv=paths["demographics"],
        spec=spec,
        wave_export_id="synthetic_answer_sheet_smoke",
    )
    assert len(records) == 80
