"""F4 adversarial dial-in cases for VAL-2026-003 S2.

Track-2 hand-dialed patients. Separate from Track-1 bulk parametric generation.
V1 minimum: CASE-01, CASE-04, CASE-06, CASE-08.
"""

from cinder.synthetic.f4.catalog import V1_CASES, CaseSpec
from cinder.synthetic.f4.instantiate import instantiate_f4_case

__all__ = ["V1_CASES", "CaseSpec", "instantiate_f4_case"]
