"""Dial-in orchestrator for F4 adversarial cases.

``instantiate_f4_case(case_id, variant_seed)`` returns a deterministic
(PatientRecord, PatientAnswer) pair. V1 order: CASE-04, CASE-01, CASE-06, CASE-08.
"""

from __future__ import annotations

from typing import Any, Callable

from cinder.synthetic.f4.catalog import V1_CASES
from cinder.synthetic.f4.cases.case_01 import build_case_01
from cinder.synthetic.f4.cases.case_04 import build_case_04
from cinder.synthetic.f4.cases.case_06 import build_case_06
from cinder.synthetic.f4.cases.case_08 import build_case_08

__all__ = ["instantiate_f4_case"]

_BUILDERS: dict[str, Callable[..., tuple[Any, Any]]] = {
    "CASE-01": build_case_01,
    "CASE-04": build_case_04,
    "CASE-06": build_case_06,
    "CASE-08": build_case_08,
}


def instantiate_f4_case(
    case_id: str,
    variant_seed: int = 0,
    *,
    n_waves: int = 6,
) -> tuple[Any, Any]:
    """Return (PatientRecord, PatientAnswer) for one F4 case × variant."""
    known = {c.case_id for c in V1_CASES}
    if case_id not in known:
        raise ValueError(f"{case_id} not in V1 set {sorted(known)}")
    if not (0 <= variant_seed < 20):
        raise ValueError("variant_seed must be in 0..19 for VAL-003 S2")
    builder = _BUILDERS.get(case_id)
    if builder is None:
        raise NotImplementedError(f"{case_id} dial-in not implemented")
    return builder(variant_seed, n_waves=n_waves)
