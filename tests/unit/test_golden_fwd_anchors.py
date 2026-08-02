"""Golden anchors FWD-001 / FWD-002 — Phase 1 exit criterion for VAL-2026-003."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

import pandas as pd
from jsonschema import Draft202012Validator

from cinder.ingest.forward_webquest_adapter import ForwardFieldSpec, load_forward_wave_csvs
from cinder.synthetic.field_spec import field_spec_hash
from cinder.synthetic.m4_arithmetic import (
    domains_crossing_mcid,
    escalation_within_window,
    should_detect_predicates,
)

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "fixtures" / "golden"
SCHEMA = json.loads((ROOT / "schemas" / "answer_sheet.schema.json").read_text(encoding="utf-8"))

# SHA-256 pins — bump only when intentionally regenerating goldens.
EXPECTED_SHA256 = {
    "FWD-001/pro_long.csv": "87dc9b5c465dc1e82113fc7a4ba972cc8b19ef4ae28f50e41ea7643c9468d9a0",
    "FWD-001/medications.csv": "460a920b968e20f66420b92056a8e718d99bc3646714175c5282af63fee481af",
    "FWD-001/demographics.csv": "a414159d1365cb05522fb496cbdf1699c47c1f7a15ae24f41db1bda0514a3a09",
    "FWD-001/answer_sheet.json": "05739e1f5bed1f49ac401b6a2e869090cac971f64f44d36362265b6bdd75f95c",
    "FWD-002/pro_long.csv": "8e664f6fa2488b2c4ccf45f3fec4760538a6dafb6a1ab7882cf60e8efcb84031",
    "FWD-002/medications.csv": "08a89c1e05664f0be4135e6d52149fea1a41bf57fb5a82369ed735b12dcf9ac4",
    "FWD-002/demographics.csv": "96bdb65d9ea03f91732069dac3bb7b267e49a3871a1654750c98d6e485037129",
    "FWD-002/answer_sheet.json": "127a38deaee3bcfa0b52772dd762ad50ca2ba70da429bbeccd48bc87037a52cf",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _wave_scores(pro: pd.DataFrame, wave: int) -> dict[str, float]:
    sub = pro[pro["wave_number"] == wave]
    return {r.instrument: float(r.score) for r in sub.itertuples()}


def test_golden_files_exist() -> None:
    for pid in ("FWD-001", "FWD-002"):
        for name in ("pro_long.csv", "medications.csv", "demographics.csv", "answer_sheet.json"):
            assert (GOLDEN / pid / name).is_file(), f"missing {pid}/{name}"


def test_answer_sheets_validate() -> None:
    Draft202012Validator.check_schema(SCHEMA)
    for pid in ("FWD-001", "FWD-002"):
        doc = json.loads((GOLDEN / pid / "answer_sheet.json").read_text(encoding="utf-8"))
        errors = sorted(Draft202012Validator(SCHEMA).iter_errors(doc), key=lambda e: e.path)
        assert not errors, errors[0].message if errors else ""
        assert doc["provenance"]["synthetic"] is True
        assert doc["provenance"]["field_spec_hash"] == field_spec_hash(ForwardFieldSpec())


def test_fwd001_should_detect_arithmetic() -> None:
    pro = pd.read_csv(GOLDEN / "FWD-001" / "pro_long.csv")
    doc = json.loads((GOLDEN / "FWD-001" / "answer_sheet.json").read_text(encoding="utf-8"))
    patient = doc["patients"][0]
    w2 = next(w for w in patient["per_wave"] if w["wave_number"] == 2)
    assert w2["expected_M4_outcome"] == "should_detect"
    prev, curr = _wave_scores(pro, 1), _wave_scores(pro, 2)
    shifted = domains_crossing_mcid(prev, curr)
    assert set(shifted) == set(w2["pro_domains_shifted"])
    assert len(shifted) >= 2
    esc_date = dt.date.fromisoformat(w2["escalation_event"]["date"])
    wave_date = dt.date.fromisoformat(
        str(pro.loc[pro["wave_number"] == 2, "wave_date"].iloc[0])
    )
    assert escalation_within_window(wave_date, [esc_date])
    assert should_detect_predicates(shifted, True)


def test_fwd002_axiom_invisible_no_escalation() -> None:
    pro = pd.read_csv(GOLDEN / "FWD-002" / "pro_long.csv")
    doc = json.loads((GOLDEN / "FWD-002" / "answer_sheet.json").read_text(encoding="utf-8"))
    patient = doc["patients"][0]
    w2 = next(w for w in patient["per_wave"] if w["wave_number"] == 2)
    assert w2["expected_M4_outcome"] == "axiom_invisible"
    assert w2["expected_UC_behavior"] == "widen"
    assert w2["escalation_event"] is None
    prev, curr = _wave_scores(pro, 1), _wave_scores(pro, 2)
    shifted = domains_crossing_mcid(prev, curr)
    assert len(shifted) >= 2
    # PRO crosses MCID but without escalation → not should_detect
    assert not should_detect_predicates(shifted, False)


def test_adapter_round_trip() -> None:
    spec = ForwardFieldSpec()
    for pid in ("FWD-001", "FWD-002"):
        d = GOLDEN / pid
        records = load_forward_wave_csvs(
            pro_long_csv=d / "pro_long.csv",
            medications_csv=d / "medications.csv",
            demographics_csv=d / "demographics.csv",
            spec=spec,
            wave_export_id=f"golden_{pid}",
        )
        assert len(records) == 1


def test_sha256_pins_recorded() -> None:
    """Print / assert pins. First run fills EXPECTED; CI locks them."""
    computed = {rel: _sha256(GOLDEN / rel) for rel in EXPECTED_SHA256}
    # If placeholders remain, fail with the computed table so we can paste pins.
    if any(v == "PLACEHOLDER" for v in EXPECTED_SHA256.values()):
        lines = "\n".join(f'    "{k}": "{v}",' for k, v in computed.items())
        raise AssertionError(f"Update EXPECTED_SHA256 in test_golden_fwd_anchors.py:\n{lines}")
    for rel, digest in EXPECTED_SHA256.items():
        assert computed[rel] == digest, rel
