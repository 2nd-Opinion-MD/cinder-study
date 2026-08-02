"""F4 case catalog — VAL-2026-003 §2.4 failure-mode families."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CaseSpec:
    case_id: str
    family: str
    stress: str
    v1: bool


#: Full F4 library (10). V1 ships the four load-bearing families first.
ALL_CASES: tuple[CaseSpec, ...] = (
    CaseSpec("CASE-01", "Escalation-absent true flare", "Escalation criterion missing, PRO present", True),
    CaseSpec("CASE-02", "Escalation-absent true flare", "Variant of CASE-01", False),
    CaseSpec("CASE-03", "PRO-suppressed / sub-threshold", "PRO signal below gate", False),
    CaseSpec("CASE-04", "False-positive guard", "Comorbidity elevation that must NOT fire", True),
    CaseSpec("CASE-05", "PRO-suppressed / sub-threshold", "Variant of CASE-03", False),
    CaseSpec("CASE-06", "Temporal-sampling failure", "Signals exist, linkage missed (±90d)", True),
    CaseSpec("CASE-07", "Temporal-sampling failure", "Variant of CASE-06", False),
    CaseSpec("CASE-08", "Trajectory / baseline masking", "Slow drift absorbed by adaptive baseline", True),
    CaseSpec("CASE-09", "Stratification / equity", "Seronegative sensitivity parity", False),
    CaseSpec("CASE-10", "Inverse discordance", "Escalation present, PRO absent", False),
)

V1_CASES: tuple[CaseSpec, ...] = tuple(c for c in ALL_CASES if c.v1)

assert [c.case_id for c in V1_CASES] == ["CASE-01", "CASE-04", "CASE-06", "CASE-08"]
