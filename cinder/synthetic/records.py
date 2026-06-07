"""records.py - the typed in-memory cohort contract shared across the package.

These dataclasses are the single row-shape that `cohort` populates, `emit_csv` writes,
and `answer_sheet` binds its ground truth to. Keeping them here (rather than inside
`cohort`) lets the Sprint-0 emit/contract path and the Sprint-4 orchestrator share one
definition, so the CSV columns and the answer-sheet bindings can never silently drift
apart from each other.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(slots=True)
class PROObservation:
    """One PRO measurement at one wave (`pro_long.csv` row, minus patient/wave keys)."""

    instrument: str  # one of field_spec.INSTRUMENTS (+ optional RAPID3 subscores)
    score: float


@dataclass(slots=True)
class Wave:
    """A single assessment wave for a patient (semi-annual cadence, §A3)."""

    wave_number: int
    wave_date: date
    observations: list[PROObservation] = field(default_factory=list)


@dataclass(slots=True)
class MedEvent:
    """One medication record (`medications.csv` row, minus patient key).

    `route` is mandatory and constrained to {"oral", "parenteral"} (C4) - it drives the
    downstream §4.5 maintenance-vs-rescue state machine. `stop_date` is None when ongoing.
    """

    drug_name: str
    rxnorm: str
    dose: float
    dose_unit: str
    route: str  # "oral" | "parenteral"
    start_date: date
    stop_date: date | None = None


@dataclass(slots=True)
class PatientRecord:
    """A complete synthetic patient: demographics + longitudinal PRO waves + med stream.

    Mirrors the three CSV outputs (§6.1-§6.3). The matching per-patient ground truth lives
    in the answer sheet (`answer_sheet.PatientAnswer`), keyed by the same `patient_id`.
    """

    patient_id: str
    sex: str  # "F" | "M"
    ra_seropositivity: str  # "seropositive" | "seronegative" (string, NOT bool - C5)
    ra_diagnosis_date: date
    waves: list[Wave] = field(default_factory=list)
    medications: list[MedEvent] = field(default_factory=list)
