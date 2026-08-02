"""F4 catalog smoke — V1 four families locked."""

from __future__ import annotations

import pytest

from cinder.synthetic.f4.catalog import V1_CASES
from cinder.synthetic.f4.instantiate import instantiate_f4_case


def test_v1_case_ids() -> None:
    assert [c.case_id for c in V1_CASES] == ["CASE-01", "CASE-04", "CASE-06", "CASE-08"]


def test_instantiate_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="not in V1"):
        instantiate_f4_case("CASE-99")


def test_instantiate_rejects_bad_variant() -> None:
    with pytest.raises(ValueError, match="variant_seed"):
        instantiate_f4_case("CASE-04", 20)


@pytest.mark.parametrize("case_id", ["CASE-01", "CASE-04", "CASE-06", "CASE-08"])
def test_v1_cases_instantiate(case_id: str) -> None:
    record, answer = instantiate_f4_case(case_id, 0)
    assert record.patient_id.startswith(case_id)
