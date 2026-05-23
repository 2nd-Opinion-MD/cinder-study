"""Regression tests for the PTV input contract schema.

The 632-event reference fixture is the canonical positive case. The negative
cases assert that the schema enforces what `cinder.bayes` actually relies on:
events must have an event_id, event_type, timestamp, and annotations.card;
metadata.pii_scrubbed must be present (this is what couples to pii_tripwire.py).
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "schemas" / "ptv_input.schema.json").read_text(encoding="utf-8"))
FIXTURE_PATH = (
    ROOT / "fixtures" / "real_ehr_632event" / "ptv_real_ehr_632event_v1_noarcs_scrubbed.json"
)


def _validate(instance: dict) -> None:
    jsonschema.validate(instance=instance, schema=SCHEMA)


def _minimal_ptv() -> dict:
    """Smallest PTV that satisfies the schema. Used as a base for negative cases."""
    return {
        "events": {
            "ev_001": {
                "event_id": "ev_001",
                "event_type": "diagnosis",
                "timestamp": "2025-01-15",
                "annotations": {
                    "card": {
                        "type": "diagnosis",
                        "title": "Rheumatoid arthritis",
                    },
                },
            },
        },
        "metadata": {
            "pii_scrubbed": {
                "scrubber": "scrub_real_ptv.py",
                "scrubbed_at": "2026-04-23",
            },
        },
        "patient_id": "46860f06-e0a5-42d4-af9f-4dd8caa666f0",
    }


def test_minimal_ptv_validates() -> None:
    _validate(_minimal_ptv())


def test_real_632event_fixture_validates() -> None:
    """The canonical real-EHR reference PTV must validate. Skip if not yet copied."""
    if not FIXTURE_PATH.exists():
        pytest.skip("reference fixture not copied (Phase 0 in progress)")
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    _validate(data)
    assert len(data["events"]) == 632
    assert data["metadata"]["pii_scrubbed"]["scrubber"] == "server/scripts/scrub_real_ptv.py"


def test_missing_pii_scrubbed_block_rejected() -> None:
    """PTV without metadata.pii_scrubbed must fail. This is what couples the
    schema to scripts/pii_tripwire.py at the structural level.
    """
    bad = _minimal_ptv()
    bad["metadata"].pop("pii_scrubbed")
    with pytest.raises(jsonschema.ValidationError):
        _validate(bad)


def test_pii_scrubbed_missing_scrubber_rejected() -> None:
    bad = _minimal_ptv()
    bad["metadata"]["pii_scrubbed"].pop("scrubber")
    with pytest.raises(jsonschema.ValidationError):
        _validate(bad)


def test_event_missing_annotations_rejected() -> None:
    bad = _minimal_ptv()
    bad["events"]["ev_001"].pop("annotations")
    with pytest.raises(jsonschema.ValidationError):
        _validate(bad)


def test_event_missing_card_rejected() -> None:
    bad = _minimal_ptv()
    bad["events"]["ev_001"]["annotations"].pop("card")
    with pytest.raises(jsonschema.ValidationError):
        _validate(bad)


def test_event_invalid_timestamp_rejected() -> None:
    bad = _minimal_ptv()
    bad["events"]["ev_001"]["timestamp"] = (
        "January 15, 2025"  # not ISO, not 'unknown', not redacted
    )
    with pytest.raises(jsonschema.ValidationError):
        _validate(bad)


def test_event_unknown_timestamp_accepted() -> None:
    ok = _minimal_ptv()
    ok["events"]["ev_001"]["timestamp"] = "unknown"
    _validate(ok)


def test_event_redacted_timestamp_accepted() -> None:
    """`[DOB_REDACTED]` and similar tokens emitted by the scrubber must validate."""
    ok = _minimal_ptv()
    ok["events"]["ev_001"]["timestamp"] = "[DOB_REDACTED]"
    _validate(ok)


def test_invalid_patient_id_rejected() -> None:
    bad = _minimal_ptv()
    bad["patient_id"] = "not-a-uuid"
    with pytest.raises(jsonschema.ValidationError):
        _validate(bad)


def test_negative_salience_rejected() -> None:
    bad = _minimal_ptv()
    bad["events"]["ev_001"]["annotations"]["salience"] = -1.0
    with pytest.raises(jsonschema.ValidationError):
        _validate(bad)


def test_pro_event_with_cinder_pro_block_validates() -> None:
    """Forward-derived PRO events must carry the §4.4 detection inputs."""
    ok = _minimal_ptv()
    ok["events"]["pro_w12_haq"] = {
        "event_id": "pro_w12_haq",
        "event_type": "pro_wave",
        "timestamp": "2025-06-15",
        "annotations": {
            "card": {"type": "pro_wave", "title": "HAQ-II wave 12"},
            "cinder_pro": {
                "instrument": "HAQ-II",
                "score": 1.4,
                "wave_number": 12,
                "wave_date": "2025-06-15",
                "delta_from_baseline": 0.3,
                "exceeds_band": True,
            },
        },
    }
    _validate(ok)


def test_pro_event_with_invalid_instrument_rejected() -> None:
    bad = _minimal_ptv()
    bad["events"]["pro_bad"] = {
        "event_id": "pro_bad",
        "event_type": "pro_wave",
        "timestamp": "2025-06-15",
        "annotations": {
            "card": {"type": "pro_wave", "title": "x"},
            "cinder_pro": {
                "instrument": "DAS28",  # not in §4.4 instrument set
                "score": 3.2,
                "wave_number": 12,
                "wave_date": "2025-06-15",
            },
        },
    }
    with pytest.raises(jsonschema.ValidationError):
        _validate(bad)


def test_drug_entity_key_with_hyphens_validates() -> None:
    """Drug entity keys legitimately contain hyphens (e.g. combination drugs)."""
    ok = _minimal_ptv()
    ok["events"]["ev_001"]["annotations"]["entity_keys"] = [
        "drug:hydrocodone-acetaminophen",
        "drug:trimethoprim-sulfamethoxazole",
        "icd:m05_79",
    ]
    _validate(ok)


def test_no_mutation_of_input_during_validation() -> None:
    """Sanity check: jsonschema must not mutate the instance."""
    instance = _minimal_ptv()
    snapshot = copy.deepcopy(instance)
    _validate(instance)
    assert instance == snapshot
