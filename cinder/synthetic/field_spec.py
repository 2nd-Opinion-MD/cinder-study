"""field_spec.py - SINGLE source of truth for output column names (C1, A2, R1).

The generator and the answer sheet both bind their column names HERE, and `field_spec`
re-exports Dylan's :class:`ForwardFieldSpec` from the ingest adapter so the synthetic
cohort exercises the exact same column contract the real FORWARD export will. If Adam
Cornish later confirms different FORWARD field names, Dylan updates the dataclass and
both the generator and the answer sheet move together - the contract test
(`test_synthetic_columns_contract`) fails on any divergence. Never hard-code column
names anywhere else in the package.
"""

from __future__ import annotations

import hashlib
import json

from cinder.ingest.forward_webquest_adapter import ForwardFieldSpec

__all__ = [
    "INSTRUMENTS",
    "RAPID3_SUBSCORES",
    "ForwardFieldSpec",
    "demographics_columns",
    "field_spec_hash",
    "format_dose",
    "format_score",
    "medications_columns",
    "pro_long_columns",
]

#: Canonical PRO instruments emitted by Track 1 (C3). RAPID3 is a composite (computed,
#: never drawn - §4 construct rule). Subscores are optional (default off).
INSTRUMENTS: tuple[str, ...] = ("HAQ-II", "PainVAS", "PatientGlobalVAS", "RAPID3")
RAPID3_SUBSCORES: tuple[str, ...] = ("RAPID3_FN", "RAPID3_PN", "RAPID3_PtGA")

#: Numeric display precision LOCKED from the seed exemplars (C8):
#:   HAQ-II -> 1 dp; PainVAS / PatientGlobalVAS -> 0 dp emitted as float ".0";
#:   RAPID3 (+ subscores) -> 1 dp. Drives emit_csv formatting so output byte-matches seed.
_SCORE_DECIMALS: dict[str, int] = {
    "HAQ-II": 1,
    "PainVAS": 1,  # value rounded to integer, formatted with one trailing ".0" (seed shape)
    "PatientGlobalVAS": 1,
    "RAPID3": 1,
    "RAPID3_FN": 1,
    "RAPID3_PN": 1,
    "RAPID3_PtGA": 1,
}
#: Instruments rounded to whole units before the ".0" display (PainVAS / PGA, C8).
_WHOLE_UNIT_INSTRUMENTS: frozenset[str] = frozenset({"PainVAS", "PatientGlobalVAS"})


def pro_long_columns(spec: ForwardFieldSpec) -> list[str]:
    """Ordered `pro_long.csv` header, read from the dataclass (§6.1)."""
    return [
        spec.pro_patient_id_col,
        spec.pro_wave_number_col,
        spec.pro_wave_date_col,
        spec.pro_instrument_col,
        spec.pro_score_col,
    ]


def medications_columns(spec: ForwardFieldSpec) -> list[str]:
    """Ordered `medications.csv` header, read from the dataclass (§6.2)."""
    return [
        spec.med_patient_id_col,
        spec.med_drug_name_col,
        spec.med_rxnorm_col,
        spec.med_dose_col,
        spec.med_dose_unit_col,
        spec.med_route_col,
        spec.med_start_date_col,
        spec.med_stop_date_col,
    ]


def demographics_columns(spec: ForwardFieldSpec) -> list[str]:
    """Ordered `demographics.csv` header, read from the dataclass (§6.3)."""
    return [
        spec.demo_patient_id_col,
        spec.demo_sex_col,
        spec.demo_ra_seropositivity_col,
        spec.demo_ra_diagnosis_date_col,
    ]


def format_score(instrument: str, value: float) -> str:
    """Format a PRO score for CSV emission per the C8 seed-locked precision."""
    if instrument in _WHOLE_UNIT_INSTRUMENTS:
        return f"{round(value):.1f}"  # whole unit, one trailing decimal: 50 -> "50.0"
    decimals = _SCORE_DECIMALS.get(instrument, 1)
    return f"{round(value, decimals):.{decimals}f}"


def format_dose(value: float) -> str:
    """Format a medication dose as a float with one decimal (seed shape: 15 -> "15.0")."""
    return f"{float(value):.1f}"


def field_spec_hash(spec: ForwardFieldSpec) -> str:
    """Stable sha256 over the active column names - stamped into answer-sheet provenance.

    Lets a downstream reader prove which column binding produced a given answer sheet
    (the R1 coupling guard, made auditable).
    """
    payload = json.dumps(
        {
            "pro_long": pro_long_columns(spec),
            "medications": medications_columns(spec),
            "demographics": demographics_columns(spec),
            "instruments": list(INSTRUMENTS),
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
