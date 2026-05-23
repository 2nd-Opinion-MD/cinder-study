#!/usr/bin/env python3
"""
validate_schemas.py — validate every JSON Schema in `schemas/` is well-formed,
then validate every fixture JSON against the schema named in its `$schema_ref`
sidecar field (or by directory convention).

Run via pre-commit hook + CI per IMPLEMENTATION_PLAN.md Phase 0.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import jsonschema
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"
FIXTURE_DIR = ROOT / "fixtures"


def _log(level: str, msg: str) -> None:
    print(f"[{level}] {msg}", file=sys.stderr, flush=True)


def load_schemas() -> dict[str, dict[str, Any]]:
    """Load every *.schema.json in `schemas/` and check it parses + is a valid JSON Schema."""
    schemas: dict[str, dict[str, Any]] = {}
    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            _log("FAIL", f"schema is not valid JSON: {path.name}: {exc}")
            sys.exit(1)
        try:
            Draft202012Validator.check_schema(data)
        except SchemaError as exc:
            _log("FAIL", f"schema is not a valid JSON Schema: {path.name}: {exc.message}")
            sys.exit(1)
        schemas[path.name] = data
        _log("ok", f"schema OK: {path.name}")
    return schemas


def validate_fixtures(schemas: dict[str, dict[str, Any]]) -> int:
    """Each fixture JSON whose top-level dict carries a `$schema_ref` field is validated
    against the named schema in `schemas/`. Fixtures without `$schema_ref` are skipped
    with a notice (production PTVs rely on PII tripwire, not schema validation, until
    the PTV input contract schema lands).
    """
    if not FIXTURE_DIR.exists():
        _log("info", "no fixtures/ directory yet; skipping fixture validation")
        return 0

    failures = 0
    n_validated = 0
    n_skipped = 0
    for path in sorted(FIXTURE_DIR.rglob("*.json")):
        if path.name.startswith("MANIFEST") or path.name == "manifest.json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            _log("FAIL", f"fixture is not valid JSON: {path}: {exc}")
            failures += 1
            continue
        if not isinstance(data, dict):
            n_skipped += 1
            continue
        ref = data.get("$schema_ref")
        if not ref or not isinstance(ref, str):
            n_skipped += 1
            continue
        schema = schemas.get(ref)
        if schema is None:
            _log("FAIL", f"fixture {path.name} references unknown schema: {ref}")
            failures += 1
            continue
        try:
            jsonschema.validate(instance=data.get("payload", data), schema=schema)
            n_validated += 1
            _log("ok", f"fixture OK: {path.name} -> {ref}")
        except jsonschema.ValidationError as exc:
            _log("FAIL", f"fixture failed validation: {path.name} -> {ref}: {exc.message}")
            failures += 1
    _log("info", f"validated {n_validated} fixtures; skipped {n_skipped} (no $schema_ref)")
    return failures


def main() -> None:
    _log("info", f"loading schemas from {SCHEMA_DIR}")
    schemas = load_schemas()
    _log("info", f"validating fixtures under {FIXTURE_DIR}")
    failures = validate_fixtures(schemas)
    if failures:
        _log("FAIL", f"{failures} validation failure(s)")
        sys.exit(1)
    _log("ok", "all schemas + fixtures valid")


if __name__ == "__main__":
    main()
