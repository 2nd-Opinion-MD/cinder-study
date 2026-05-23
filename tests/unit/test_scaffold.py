"""Phase 0 scaffold smoke tests — proves the package is importable and the four
published JSON Schemas load and self-validate.

These tests are intentionally minimal. They establish that CI is green at the
end of Phase 0 so subsequent phases land into a known-clean baseline.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "schemas"

EXPECTED_SCHEMAS = [
    "uc_annotation.schema.json",
    "flare_event.schema.json",
    "escalation_event.schema.json",
    "derivation_chain.schema.json",
]


def test_package_importable() -> None:
    import cinder

    assert cinder.__version__.startswith("0.1.")


def test_bayes_subpackage_placeholder_imports() -> None:
    import cinder.bayes  # noqa: F401


def test_analysis_package_imports() -> None:
    import analysis  # noqa: F401


@pytest.mark.parametrize("schema_name", EXPECTED_SCHEMAS)
def test_schema_file_exists(schema_name: str) -> None:
    assert (SCHEMA_DIR / schema_name).is_file()


@pytest.mark.parametrize("schema_name", EXPECTED_SCHEMAS)
def test_schema_self_validates(schema_name: str) -> None:
    """Each published schema must itself be a valid Draft 2020-12 JSON Schema."""
    data = json.loads((SCHEMA_DIR / schema_name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(data)
    assert data["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert data["$id"].endswith(schema_name)
