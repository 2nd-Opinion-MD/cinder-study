"""Unit tests for cinder.ingest.forward_webquest_adapter (Phase 4.A.2 stub).

These tests exercise the receiving-side adapter against the synthetic
mock CSVs in ``tests/unit/fixtures/forward_mock_wave/``. They validate
that:

* The adapter's per-patient PTV outputs validate against
  ``schemas/ptv_input.schema.json``.
* The patient UUID generation is deterministic (same FORWARD native id
  always maps to the same UUID).
* The adapter is byte-deterministic (two runs on the same inputs
  produce identical PTVs modulo ``built_at``, which we strip for the
  comparison).
* The PRO event annotations carry the §4.4 ``cinder_pro`` block.
* The medication events carry RxNorm + dose + route fields.
* The schema-required ``metadata.pii_scrubbed`` provenance is populated
  so the PII tripwire (``scripts/pii_tripwire.py``) accepts the emit.

The Phase 4.E real-FORWARD ingest will replace these mocks with a slice
from Adam Cornish's FORWARD/UNMC export; the adapter API and tests will
both stay the same.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import jsonschema
import pandas as pd
import pytest

from cinder.ingest.forward_webquest_adapter import (
    FORWARD_WAVE_EXPORT_VERSION,
    NAMESPACE_FORWARD,
    ForwardFieldSpec,
    forward_export_to_ptv_records,
    load_forward_wave_csvs,
    patient_uuid_for,
)

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "schemas" / "ptv_input.schema.json").read_text(encoding="utf-8"))
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "forward_mock_wave"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _validate(instance: dict) -> None:
    jsonschema.validate(instance=instance, schema=SCHEMA)


def _load_records() -> dict[str, dict]:
    return load_forward_wave_csvs(
        pro_long_csv=FIXTURE_DIR / "pro_long.csv",
        medications_csv=FIXTURE_DIR / "medications.csv",
        demographics_csv=FIXTURE_DIR / "demographics.csv",
        wave_export_id="forward_mock_wave",
    )


# --------------------------------------------------------------------------- #
# Identity / determinism
# --------------------------------------------------------------------------- #


def test_namespace_constant_is_pinned() -> None:
    """Reproducibility hinges on this UUID5 namespace being pinned forever."""
    assert str(NAMESPACE_FORWARD) == "9c0f7e4a-5b3e-4a8b-9d2f-7e6a8c5b3e4a"


def test_patient_uuid_is_deterministic() -> None:
    a = patient_uuid_for("FWD-MOCK-001")
    b = patient_uuid_for("FWD-MOCK-001")
    assert a == b
    assert patient_uuid_for("FWD-MOCK-001") != patient_uuid_for("FWD-MOCK-002")


def test_patient_uuid_matches_schema_pattern() -> None:
    uuid_str = patient_uuid_for("FWD-MOCK-001")
    import re

    assert re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        uuid_str,
    )


def test_patient_uuid_rejects_blank() -> None:
    with pytest.raises(ValueError):
        patient_uuid_for("")
    with pytest.raises(ValueError):
        patient_uuid_for("   ")


def test_two_runs_produce_identical_ptv_modulo_built_at() -> None:
    """Determinism: same inputs -> same PTV (event ids, metadata, etc)."""
    run_1 = _load_records()
    run_2 = _load_records()
    assert set(run_1) == set(run_2)
    for puuid in run_1:
        a = copy.deepcopy(run_1[puuid])
        b = copy.deepcopy(run_2[puuid])
        a.pop("built_at", None)
        b.pop("built_at", None)
        assert a == b


# --------------------------------------------------------------------------- #
# Schema validation
# --------------------------------------------------------------------------- #


def test_each_emitted_ptv_validates_against_schema() -> None:
    records = _load_records()
    assert len(records) == 2  # mock has 2 patients
    for puuid, ptv in records.items():
        _validate(ptv)
        assert ptv["patient_id"] == puuid
        assert ptv["$schema_ref"] == "ptv_input.schema.json"


def test_metadata_pii_scrubbed_block_satisfies_tripwire_shape() -> None:
    """The PII tripwire requires `scrubber` + `scrubbed_at`. The schema requires
    those plus `format: date` on `scrubbed_at`. Validate both jointly here.
    """
    records = _load_records()
    ptv = next(iter(records.values()))
    scrub = ptv["metadata"]["pii_scrubbed"]
    assert scrub["scrubber"]
    assert scrub["scrubbed_at"]
    # ISO date shape, not date-time.
    assert len(scrub["scrubbed_at"]) == 10
    assert scrub["scrubbed_at"][4] == "-" and scrub["scrubbed_at"][7] == "-"


# --------------------------------------------------------------------------- #
# Event content shape
# --------------------------------------------------------------------------- #


def test_pro_events_carry_cinder_pro_block() -> None:
    """Every `event_type=pro` event must carry §4.4 detection inputs."""
    records = _load_records()
    saw_pro_events = 0
    for ptv in records.values():
        for ev in ptv["events"].values():
            if ev["event_type"] != "pro":
                continue
            saw_pro_events += 1
            cp = ev["annotations"]["cinder_pro"]
            assert cp["instrument"] in {
                "HAQ-II",
                "PainVAS",
                "PatientGlobalVAS",
                "RAPID3",
                "RAPID3_FN",
                "RAPID3_PN",
                "RAPID3_PtGA",
            }
            assert isinstance(cp["score"], float)
            assert isinstance(cp["wave_number"], int)
            assert cp["wave_number"] >= 1
            # ISO date.
            assert len(cp["wave_date"]) == 10
            # Stub does not yet populate these (M2/M3 dependency, Phase 4.E).
            assert cp["delta_from_baseline"] is None
            assert cp["exceeds_band"] is None
    # 2 patients * 4 waves * 4 instruments = 32 PRO events
    assert saw_pro_events == 32


def test_one_pro_wave_envelope_per_wave() -> None:
    records = _load_records()
    for ptv in records.values():
        wave_envs = [e for e in ptv["events"].values() if e["event_type"] == "pro_wave"]
        # Each mock patient has 4 waves.
        assert len(wave_envs) == 4
        # Wave envelope timestamps are unique (one per wave).
        assert len({e["timestamp"] for e in wave_envs}) == 4


def test_medication_events_carry_rxnorm_and_route() -> None:
    records = _load_records()
    p001_uuid = patient_uuid_for("FWD-MOCK-001")
    p001 = records[p001_uuid]
    meds = [e for e in p001["events"].values() if e["event_type"] == "medication"]
    # Patient 001 has 3 medication rows in the mock.
    assert len(meds) == 3
    drugs = {e["annotations"]["drug_name"] for e in meds}
    assert {"methotrexate", "prednisone", "adalimumab"} <= drugs
    # RxNorm + route propagated.
    pred = next(e for e in meds if e["annotations"]["drug_name"] == "prednisone")
    assert pred["annotations"]["rxnorm"] == "8640"
    assert "oral" in pred["annotations"]["status_flags"]
    adali = next(e for e in meds if e["annotations"]["drug_name"] == "adalimumab")
    assert "parenteral" in adali["annotations"]["status_flags"]


def test_metadata_forward_block_summarizes_export() -> None:
    records = _load_records()
    p001_uuid = patient_uuid_for("FWD-MOCK-001")
    md = records[p001_uuid]["metadata"]["pro"]["forward"]
    assert md["wave_export_version"] == FORWARD_WAVE_EXPORT_VERSION
    assert md["wave_count"] == 4
    assert md["wave_date_range"] == {"start": "2024-01-15", "end": "2025-07-22"}
    assert set(md["instruments_present"]) == {
        "HAQ-II",
        "PainVAS",
        "PatientGlobalVAS",
        "RAPID3",
    }


def test_demographics_propagated() -> None:
    records = _load_records()
    p001 = records[patient_uuid_for("FWD-MOCK-001")]
    assert p001["metadata"]["patient"]["sex"] == "F"
    assert p001["metadata"]["patient"]["ra_seropositivity"] == "seropositive"
    assert p001["metadata"]["patient"]["ra_diagnosis_date"] == "2019-03-12"
    assert p001["metadata"]["patient"]["dob"] == "[DOB_REDACTED]"


# --------------------------------------------------------------------------- #
# Field-spec swap (the Wednesday-after-Tuesday motion)
# --------------------------------------------------------------------------- #


def test_field_spec_swap_works_for_renamed_columns() -> None:
    """Demonstrates the Wednesday motion: Adam confirms his column names,
    we instantiate ForwardFieldSpec with them, and the same adapter path
    absorbs the real wave.
    """
    pro = pd.read_csv(FIXTURE_DIR / "pro_long.csv").rename(
        columns={
            "patient_id": "fwd_subject_id",
            "wave_number": "round_idx",
            "wave_date": "round_completed_on",
            "instrument": "pro_form",
            "score": "pro_score",
        }
    )
    meds = pd.read_csv(FIXTURE_DIR / "medications.csv")
    demo = pd.read_csv(FIXTURE_DIR / "demographics.csv")

    spec = ForwardFieldSpec(
        pro_patient_id_col="fwd_subject_id",
        pro_wave_number_col="round_idx",
        pro_wave_date_col="round_completed_on",
        pro_instrument_col="pro_form",
        pro_score_col="pro_score",
    )

    records = forward_export_to_ptv_records(
        pro_long=pro,
        medications=meds,
        demographics=demo,
        spec=spec,
        wave_export_id="forward_mock_wave_renamed",
    )
    assert len(records) == 2
    for ptv in records.values():
        _validate(ptv)


def test_instrument_normalization_handles_lowercase() -> None:
    """FORWARD's PRO column may carry case variations; normalizer handles them."""
    pro = pd.DataFrame(
        [
            {
                "patient_id": "FWD-MOCK-001",
                "wave_number": 1,
                "wave_date": "2024-01-15",
                "instrument": "haq-ii",
                "score": 0.5,
            },
            {
                "patient_id": "FWD-MOCK-001",
                "wave_number": 1,
                "wave_date": "2024-01-15",
                "instrument": "Pain_VAS",
                "score": 30,
            },
        ]
    )
    records = forward_export_to_ptv_records(
        pro_long=pro,
        medications=pd.DataFrame(
            columns=[
                "patient_id",
                "drug_name",
                "rxnorm",
                "dose",
                "dose_unit",
                "route",
                "start_date",
                "stop_date",
            ]
        ),
        demographics=pd.DataFrame(columns=["patient_id"]),
    )
    ptv = next(iter(records.values()))
    instruments = {
        e["annotations"]["cinder_pro"]["instrument"]
        for e in ptv["events"].values()
        if e["event_type"] == "pro"
    }
    assert instruments == {"HAQ-II", "PainVAS"}


def test_malformed_rows_are_silently_skipped_in_stub() -> None:
    """Stub policy: malformed rows are dropped. Phase 4.E adapter will log them."""
    pro = pd.DataFrame(
        [
            {
                "patient_id": "FWD-MOCK-001",
                "wave_number": 1,
                "wave_date": "2024-01-15",
                "instrument": "HAQ-II",
                "score": 0.5,
            },
            {
                "patient_id": "FWD-MOCK-001",
                "wave_number": 1,
                "wave_date": "2024-01-15",
                "instrument": "DAS28",  # not in cinder_pro enum
                "score": 3.2,
            },
            {
                "patient_id": "FWD-MOCK-001",
                "wave_number": None,  # malformed
                "wave_date": "2024-01-15",
                "instrument": "PainVAS",
                "score": 30,
            },
        ]
    )
    records = forward_export_to_ptv_records(
        pro_long=pro,
        medications=pd.DataFrame(
            columns=[
                "patient_id",
                "drug_name",
                "rxnorm",
                "dose",
                "dose_unit",
                "route",
                "start_date",
                "stop_date",
            ]
        ),
        demographics=pd.DataFrame(columns=["patient_id"]),
    )
    ptv = next(iter(records.values()))
    pro_events = [e for e in ptv["events"].values() if e["event_type"] == "pro"]
    # Only the HAQ-II row survived.
    assert len(pro_events) == 1
    assert pro_events[0]["annotations"]["cinder_pro"]["instrument"] == "HAQ-II"
