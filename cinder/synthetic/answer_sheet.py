"""answer_sheet.py - the ground-truth scoring key (§6.4 / §9 schema) + provenance.

One record per patient with per-wave ground truth (true_flare, flare class/driver, the PRO
domains that crossed MCID, the linked escalation with its planted M4.D class/confidence, and
the expected M4 + UC behavior). This is the scoring key the downstream harness grades the
REAL M4 against - the generator never re-implements M4 here. Every answer sheet carries
``synthetic: true`` provenance with the spec version, field-spec hash, and seed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cinder.synthetic import GENERATOR_VERSION, PARAMETER_SPEC_VERSION, SYNTHETIC
from cinder.synthetic.treatment import EscalationFact

__all__ = [
    "PatientAnswer",
    "WaveAnswer",
    "build_answer_sheet",
    "escalation_to_dict",
    "write_answer_sheet",
]


@dataclass(slots=True)
class WaveAnswer:
    """Per-wave ground truth (one element of a patient's ``per_wave`` list)."""

    wave_number: int
    true_flare: bool
    flare_class: str | None  # axiom_visible | axiom_invisible | null
    flare_driver: str | None  # RA_primary | RA_codominant | comorbidity_driven | non_RA | null
    pro_domains_shifted: list[str]
    expected_M4_outcome: str | None  # noqa: N815 - schema key (§6.4)
    expected_UC_behavior: str | None  # noqa: N815 - schema key (§6.4)
    escalation_event: dict[str, Any] | None = None
    miss_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "wave_number": self.wave_number,
            "true_flare": self.true_flare,
            "flare_class": self.flare_class,
            "flare_driver": self.flare_driver,
            "pro_domains_shifted": self.pro_domains_shifted,
            "escalation_event": self.escalation_event,
            "expected_M4_outcome": self.expected_M4_outcome,
            "expected_UC_behavior": self.expected_UC_behavior,
            "miss_reason": self.miss_reason,
        }


@dataclass(slots=True)
class PatientAnswer:
    """One patient's ground truth."""

    patient_id: str
    phenotype_tier: str  # clean | co_dominant | masked_minority | adversarial
    comorbidity_flags: list[str]
    disease_activity_state: str  # remission | low | moderate | high
    per_wave: list[WaveAnswer] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "patient_id": self.patient_id,
            "phenotype_tier": self.phenotype_tier,
            "comorbidity_flags": self.comorbidity_flags,
            "disease_activity_state": self.disease_activity_state,
            "per_wave": [w.to_dict() for w in self.per_wave],
        }


def escalation_to_dict(fact: EscalationFact) -> dict[str, Any]:
    """Serialize an EscalationFact to the §6.4 escalation_event block."""
    return {
        "type": fact.event_type,
        "route": fact.route,
        "date": fact.date_.isoformat() if fact.date_ else None,
        "escalation_class": fact.escalation_class,
        "classification_confidence": fact.classification_confidence,
        "candidate_classes": fact.candidate_classes,
    }


def build_answer_sheet(
    patients: list[PatientAnswer], *, seed: int, field_spec_hash: str
) -> dict[str, Any]:
    """Assemble the full answer-sheet document with provenance (synthetic:true)."""
    return {
        "provenance": {
            "synthetic": SYNTHETIC,
            "generator_version": GENERATOR_VERSION,
            "parameter_spec_version": PARAMETER_SPEC_VERSION,
            "field_spec_hash": field_spec_hash,
            "seed": seed,
            # The expected_M4_outcome / pro_domains_shifted labels are defined on the LATENT
            # TRUE values (what was planted, post all signal). The real M4 is scored against
            # these labels using the NOISY observed CSVs: an ICC-noise-hidden flare is a true
            # false negative counted against sensitivity, not a labeling error. This is the
            # scoring contract - the answer sheet is ground truth, not an M4 oracle.
            "ground_truth_basis": "latent_true_values",
        },
        "patients": [p.to_dict() for p in patients],
    }


def write_answer_sheet(
    patients: list[PatientAnswer], path: Path, *, seed: int, field_spec_hash: str
) -> Path:
    """Write the answer sheet as deterministic, sorted JSON."""
    doc = build_answer_sheet(patients, seed=seed, field_spec_hash=field_spec_hash)
    Path(path).write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return Path(path)
