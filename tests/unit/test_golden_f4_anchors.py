"""Golden anchors CASE-01 / 04 / 06 / 08 — F4 variant-0 fixtures for VAL-2026-003."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

import pandas as pd
from jsonschema import Draft202012Validator

from cinder.ingest.forward_webquest_adapter import ForwardFieldSpec, load_forward_wave_csvs
from cinder.synthetic.field_spec import field_spec_hash
from cinder.synthetic.f4._common import f4_seed
from cinder.synthetic.m4_arithmetic import (
    domains_crossing_mcid,
    escalation_within_window,
    should_detect_predicates,
)

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "fixtures" / "golden"
SCHEMA = json.loads((ROOT / "schemas" / "answer_sheet.schema.json").read_text(encoding="utf-8"))

V1_CASES = ("CASE-01", "CASE-04", "CASE-06", "CASE-08")

# SHA-256 pins — bump only when intentionally regenerating goldens.
EXPECTED_SHA256 = {
    "CASE-01/pro_long.csv": "a2c2f018fbd73b0d713480f803e80649757d8b2465122fbcd809a3c98c01b5cc",
    "CASE-01/medications.csv": "987e1c57e835ee135d6f658fbcc91a4bdd49e25030879aee4cc96ff36d9cdb76",
    "CASE-01/demographics.csv": "683d88155283a693daca39fd9b421e7d77d2f5df289730ceea93dc0a8568a29e",
    "CASE-01/answer_sheet.json": "43bee036c2239c6a24376b55ab130b7bf5c99df8d847795d27f8379689881556",
    "CASE-04/pro_long.csv": "e16c3137cbe4f8f031ac12c722d0a74625c3eda1bd9730d5cef01c1b324cb884",
    "CASE-04/medications.csv": "f91f5c63a02528151faca08f437cd090983b631a5f222d9c7bd61951ac59b263",
    "CASE-04/demographics.csv": "249b88ef56aed3f9770fc0745fadd831c163d950ee57ab443899ca81abde7068",
    "CASE-04/answer_sheet.json": "c2b9e3d657ff49369009d45febadfd61dc3d03e93cb7b0208f7f7d0ecf9bdd1f",
    "CASE-06/pro_long.csv": "a1b84bfcc1458ae452d95d83eb60fca2f62b93c33289c63b1b8d04e9eda363c0",
    "CASE-06/medications.csv": "eafc3fbbdaf5e7a23b134c8b07a7a6d3e9c1371d1aa9a03fe6d701294d0c345d",
    "CASE-06/demographics.csv": "d37129d5fd32068f3c7fd3f7479c86f91662b6117de3de422ba9919f77d8fde1",
    "CASE-06/answer_sheet.json": "aef783f4b956d15af2a46b6eb4a4efd332f27d380939c7e87066be95d90b6b83",
    "CASE-08/pro_long.csv": "42c29220e51f9a740737645ac1d3ee0eba771c2337e05653e1c15952f5ee95dd",
    "CASE-08/medications.csv": "8b8b62f5cd54ee4128ef77d3ac1dde1c4e7085d5a66389264b45ebb23136e67e",
    "CASE-08/demographics.csv": "1584d6e30ae8ec9f65349400191f940d1fe1c1131d7c4056ba314144c5529d32",
    "CASE-08/answer_sheet.json": "51376260150d6649c6f9248333035fde5e26161a02e1fbe0eabdd76d1f62e616",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(case_id: str) -> tuple[pd.DataFrame, dict]:
    d = GOLDEN / case_id
    pro = pd.read_csv(d / "pro_long.csv")
    doc = json.loads((d / "answer_sheet.json").read_text(encoding="utf-8"))
    return pro, doc


def _wave_scores(pro: pd.DataFrame, wave: int) -> dict[str, float]:
    sub = pro[pro["wave_number"] == wave]
    return {r.instrument: float(r.score) for r in sub.itertuples()}


def _patient(doc: dict) -> dict:
    return doc["patients"][0]


def _wave(doc: dict, wave_number: int) -> dict:
    patient = _patient(doc)
    return next(w for w in patient["per_wave"] if w["wave_number"] == wave_number)


def test_golden_files_exist() -> None:
    for case_id in V1_CASES:
        for name in ("pro_long.csv", "medications.csv", "demographics.csv", "answer_sheet.json"):
            assert (GOLDEN / case_id / name).is_file(), f"missing {case_id}/{name}"


def test_answer_sheets_validate() -> None:
    spec = ForwardFieldSpec()
    Draft202012Validator.check_schema(SCHEMA)
    for case_id in V1_CASES:
        doc = json.loads((GOLDEN / case_id / "answer_sheet.json").read_text(encoding="utf-8"))
        errors = sorted(Draft202012Validator(SCHEMA).iter_errors(doc), key=lambda e: e.path)
        assert not errors, errors[0].message if errors else ""
        assert doc["provenance"]["synthetic"] is True
        assert doc["provenance"]["field_spec_hash"] == field_spec_hash(spec)
        assert doc["provenance"]["seed"] == f4_seed(case_id, 0)
        assert _patient(doc)["patient_id"] == case_id


def test_case_01_axiom_invisible_golden() -> None:
    pro, doc = _load("CASE-01")
    w2 = _wave(doc, 2)
    assert w2["expected_M4_outcome"] == "axiom_invisible"
    assert w2["escalation_event"] is None
    prev, curr = _wave_scores(pro, 1), _wave_scores(pro, 2)
    shifted = domains_crossing_mcid(prev, curr)
    assert len(shifted) >= 2
    assert not should_detect_predicates(shifted, False)


def test_case_04_comorbidity_golden() -> None:
    pro, doc = _load("CASE-04")
    patient = _patient(doc)
    assert patient["comorbidity_flags"] == ["fibromyalgia"]
    w2 = _wave(doc, 2)
    assert w2["flare_driver"] == "comorbidity_driven"
    assert w2["expected_UC_behavior"] == "flag_discordance"
    assert "HAQ-II" not in w2["pro_domains_shifted"]
    prev, curr = _wave_scores(pro, 1), _wave_scores(pro, 2)
    shifted = domains_crossing_mcid(prev, curr)
    assert set(shifted) == set(w2["pro_domains_shifted"])
    assert not should_detect_predicates(shifted, False)


def test_case_06_temporal_golden() -> None:
    pro, doc = _load("CASE-06")
    w2 = _wave(doc, 2)
    assert w2["miss_reason"] == "temporal_linkage_missed"
    assert w2["escalation_event"] is not None
    wave_date = dt.date.fromisoformat(str(pro.loc[pro["wave_number"] == 2, "wave_date"].iloc[0]))
    esc_date = dt.date.fromisoformat(w2["escalation_event"]["date"])
    assert not escalation_within_window(wave_date, [esc_date])


def test_case_08_baseline_masking_golden() -> None:
    doc = json.loads((GOLDEN / "CASE-08" / "answer_sheet.json").read_text(encoding="utf-8"))
    last = _wave(doc, 5)
    assert last["true_flare"] is True
    assert last["miss_reason"] == "baseline_masking"
    for w in _patient(doc)["per_wave"]:
        assert len(w["pro_domains_shifted"]) < 2


def test_adapter_round_trip() -> None:
    spec = ForwardFieldSpec()
    for case_id in V1_CASES:
        d = GOLDEN / case_id
        records = load_forward_wave_csvs(
            pro_long_csv=d / "pro_long.csv",
            medications_csv=d / "medications.csv",
            demographics_csv=d / "demographics.csv",
            spec=spec,
            wave_export_id=f"golden_{case_id}",
        )
        assert len(records) == 1


def test_sha256_pins_recorded() -> None:
    computed = {rel: _sha256(GOLDEN / rel) for rel in EXPECTED_SHA256}
    if any(v == "PLACEHOLDER" for v in EXPECTED_SHA256.values()):
        lines = "\n".join(f'    "{k}": "{v}",' for k, v in computed.items())
        raise AssertionError(f"Update EXPECTED_SHA256 in test_golden_f4_anchors.py:\n{lines}")
    for rel, digest in EXPECTED_SHA256.items():
        assert computed[rel] == digest, rel
