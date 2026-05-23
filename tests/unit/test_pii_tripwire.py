"""Tests for `scripts/pii_tripwire.py` — the last line of defense against
committing unscrubbed PTV data. Proves both detection (residual PII tokens
trigger a block) and the scrubbed-fixture path (the real 632-event reference
PTV passes the gate).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import pii_tripwire  # noqa: E402


def _ptv(metadata: dict | None = None) -> dict:
    return {
        "events": {"e1": {"event_id": "e1"}},
        "metadata": metadata or {},
    }


def test_pii_token_detected_full_name(tmp_path: Path) -> None:
    f = tmp_path / "leak.json"
    f.write_text(
        json.dumps(_ptv({"pii_scrubbed": {"scrubber": "x", "scrubbed_at": "2026-04-23"}})).replace(
            "e1", "Norman Eric Roberts visited"
        ),
        encoding="utf-8",
    )
    assert pii_tripwire.check_file(f) is False


def test_pii_token_detected_mrn(tmp_path: Path) -> None:
    f = tmp_path / "leak_mrn.json"
    f.write_text("MRN: 110005992681\n", encoding="utf-8")
    assert pii_tripwire.check_file(f) is False


def test_pii_token_detected_dob_iso(tmp_path: Path) -> None:
    f = tmp_path / "leak_dob.json"
    f.write_text("dob 1947-08-17 here", encoding="utf-8")
    assert pii_tripwire.check_file(f) is False


def test_unscrubbed_ptv_blocked(tmp_path: Path) -> None:
    """A PTV-shaped file lacking metadata.pii_scrubbed must be blocked."""
    f = tmp_path / "unscrubbed.json"
    f.write_text(json.dumps(_ptv({})), encoding="utf-8")
    assert pii_tripwire.check_file(f) is False


def test_scrubbed_ptv_passes(tmp_path: Path) -> None:
    f = tmp_path / "ok.json"
    f.write_text(
        json.dumps(
            _ptv({"pii_scrubbed": {"scrubber": "scrub_real_ptv.py", "scrubbed_at": "2026-04-23"}})
        ),
        encoding="utf-8",
    )
    assert pii_tripwire.check_file(f) is True


def test_non_ptv_json_passes(tmp_path: Path) -> None:
    f = tmp_path / "other.json"
    f.write_text(json.dumps({"hello": "world"}), encoding="utf-8")
    assert pii_tripwire.check_file(f) is True


def test_real_632event_fixture_passes() -> None:
    """The real-EHR reference PTV at fixtures/real_ehr_632event/ is the
    canonical positive case. If this fails, the scrub provenance was lost in
    transit.
    """
    fixture = (
        ROOT / "fixtures" / "real_ehr_632event" / "ptv_real_ehr_632event_v1_noarcs_scrubbed.json"
    )
    if not fixture.exists():
        pytest.skip("fixture not yet copied in (Phase 0 in progress)")
    assert pii_tripwire.check_file(fixture) is True
