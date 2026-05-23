#!/usr/bin/env python3
"""
pii_tripwire.py — block any commit containing a PTV-shaped JSON that lacks a
verified `metadata.pii_scrubbed` block, OR that contains residual PII tokens
known from the 2026-04-23 source-PII inventory.

Per PROTOCOL_DRAFT_v3 §9.1 / §9.4, only PII-scrubbed PTVs may transit the
analytic environment. This hook is the last line of defense against accidentally
committing an unscrubbed file.

Wired into:
  - .pre-commit-config.yaml (pii-tripwire hook)
  - .github/workflows/ci.yml (PII tripwire step on every PR/push)

Exit codes:
  0  — no concerns
  1  — at least one file failed the tripwire (commit/PR blocked)
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable
from pathlib import Path

# Source-PII inventory from `2ndOpinionMD-MVP/server/scripts/scrub_real_ptv.py`.
# These are the exact tokens audited in SCRUB_AUDIT_NOARCS_20260423.txt as
# `RESULT: CLEAN` after scrubbing. Their *presence* in a committed file means
# scrubbing did not run or is corrupted.
PII_TOKEN_PATTERNS: list[tuple[str, str]] = [
    (r"\bNorman\b(?!\s*\[PATIENT\])", "name:first"),
    (r"\bRoberts\b(?!\s*\[PATIENT\])", "name:last"),
    (r"\bNormanEricRoberts\b", "name:squashed"),
    (r"\b110005992681\b", "id:mrn"),
    (r"\b8/17/1947\b", "dob:slash"),
    (r"\b1947-08-17\b", "dob:iso"),
    (r"\b925-210-8834\b", "phone"),
    (r"\b925\D?210\D?8834\b", "phone:alt"),
    (r"Via\s+Monte", "address:street"),
    (r"\bWalnut\s+Creek\b", "city"),
    (r"\bKaiser\s+Walnut\s+Creek\b", "facility"),
    (r"\bKen\s+Roberts\b", "family_member"),
    (r"NormanEricRoberts_decrypted", "source_filename"),
]


def _log(level: str, msg: str) -> None:
    print(f"[{level}] {msg}", file=sys.stderr, flush=True)


def _is_ptv_shaped(data: object) -> bool:
    """Heuristic: a PTV is a dict with `events` (dict or list) and `metadata`."""
    if not isinstance(data, dict):
        return False
    has_events = isinstance(data.get("events"), (dict, list))
    has_metadata = isinstance(data.get("metadata"), dict)
    return has_events and has_metadata


def _has_scrub_provenance(data: dict) -> bool:
    """Verify `metadata.pii_scrubbed` is populated with the expected provenance shape."""
    md = data.get("metadata") or {}
    scrub = md.get("pii_scrubbed") if isinstance(md, dict) else None
    if not isinstance(scrub, dict):
        return False
    return bool(scrub.get("scrubber")) and bool(scrub.get("scrubbed_at"))


def _scan_text_for_pii(text: str) -> list[tuple[str, str]]:
    """Return list of (matched_token, label) for every PII pattern that fires."""
    hits: list[tuple[str, str]] = []
    for pattern, label in PII_TOKEN_PATTERNS:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            hits.append((m.group(0), label))
    return hits


def check_file(path: Path) -> bool:
    """Return True if the file is OK to commit; False if the tripwire fires."""
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return True  # binary or unreadable — not a PTV JSON

    # Token scan first — fastest, catches anything regardless of file shape.
    pii_hits = _scan_text_for_pii(text)
    if pii_hits:
        _log("BLOCK", f"PII TRIPWIRE: {path}")
        for token, label in pii_hits:
            _log("  ", f"  matched {label}: {token!r}")
        return False

    # Shape check — block any unscrubbed PTV-shaped file.
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return True  # not JSON, not our concern

    if _is_ptv_shaped(data) and not _has_scrub_provenance(data):
        _log("BLOCK", f"PII TRIPWIRE: {path}")
        _log("  ", "  PTV-shaped JSON missing `metadata.pii_scrubbed` provenance block")
        return False

    return True


def iter_targets(args: list[str]) -> Iterable[Path]:
    """Pre-commit passes file paths; CI passes a directory. Handle both."""
    if not args:
        # Default: scan fixtures/ (CI mode without explicit args)
        yield from Path("fixtures").rglob("*.json")
        return
    for raw in args:
        p = Path(raw)
        if p.is_dir():
            yield from p.rglob("*.json")
        elif p.is_file() and p.suffix == ".json":
            yield p


def main() -> None:
    args = sys.argv[1:]
    failures = 0
    n = 0
    for target in iter_targets(args):
        n += 1
        if not check_file(target):
            failures += 1
    if failures:
        _log("FAIL", f"PII tripwire blocked {failures} of {n} file(s)")
        _log("STOP", "Commit/CI blocked. Re-run scrub_real_ptv.py or remove the file.")
        sys.exit(1)
    _log("ok", f"PII tripwire scanned {n} file(s) -- all clear")


if __name__ == "__main__":
    main()
