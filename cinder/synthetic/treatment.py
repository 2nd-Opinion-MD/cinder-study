"""treatment.py - maintenance DMARDs + M4.A escalation emission (§6, M4.A/M4.D).

`medications.csv` stays raw FORWARD-export shape: the generator never writes an
``escalationClass`` column (that is derived downstream by M4.D from dose/route/dates/
context). Instead the generator emits GC courses whose *features* drive M4.D to the
intended class, and records the PLANTED class + confidence in the answer sheet (ground
truth). Features the generator controls (per M4.D rules): course duration (start->stop),
route, dose, concurrent DMARD init/switch, and prior GC history.

Never emit M4.A exclusions as anchors: refills, NSAID/opioid additions, first-line-at-dx,
gc_maintenance, gc_taper.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np

from cinder.synthetic.records import MedEvent

__all__ = ["ANCHOR_CLASSES", "EscalationFact", "emit_escalation", "emit_maintenance_dmard"]

#: rxnorm-anchored mini drug dictionary (seed-confirmed rxnorms).
_DMARDS = {
    "methotrexate": ("8261", 15.0, "mg", "oral"),
    "hydroxychloroquine": ("5521", 400.0, "mg", "oral"),
    "sulfasalazine": ("9524", 1000.0, "mg", "oral"),
}
_BIOLOGICS = {
    "adalimumab": ("327361", 40.0, "mg", "parenteral"),
    "etanercept": ("214555", 50.0, "mg", "parenteral"),
    "tofacitinib": ("1492189", 5.0, "mg", "oral"),  # tsDMARD (oral)
}

#: Planted classes that M4.D marks as escalation anchors (drive should_detect).
ANCHOR_CLASSES = frozenset(
    {
        "gc_rescue_burst",
        "gc_bridge_initiation",
        "dose_increase",
        "dmard_initiation",
        "therapy_switch",
    }
)
#: Non-anchor classes (M4.D ignores) - never linked to a visible flare.
NON_ANCHOR_CLASSES = frozenset({"gc_maintenance", "gc_taper"})


@dataclass(slots=True)
class EscalationFact:
    """Answer-sheet ground truth for one planted escalation (§6.4 escalation_event)."""

    escalation_class: str
    classification_confidence: str  # "high" | "low"
    candidate_classes: list[str] = field(default_factory=list)
    route: str = "oral"
    event_type: str = ""
    date_: date | None = None
    is_anchor: bool = True


def emit_maintenance_dmard(rng: np.random.Generator, dx_date: date) -> MedEvent:
    """A maintenance csDMARD present from before the study window (not an anchor)."""
    name = ("methotrexate", "hydroxychloroquine", "sulfasalazine")[rng.integers(0, 3)]
    rxnorm, dose, unit, route = _DMARDS[name]
    start = dx_date + timedelta(days=int(rng.integers(30, 200)))
    return MedEvent(name, rxnorm, dose, unit, route, start, None)


def emit_escalation(
    rng: np.random.Generator, planted_class: str, flare_date: date
) -> tuple[list[MedEvent], EscalationFact]:
    """Emit the med event(s) whose features drive M4.D to ``planted_class``.

    The escalation is placed within +/-90 d of ``flare_date`` (M4.C bidirectional window);
    we offset a few days before the PRO wave so the steroid/biologic precedes the captured
    shift (as in the seed exemplars).
    """
    offset = int(rng.integers(3, 25))
    start = flare_date - timedelta(days=offset)

    if planted_class == "gc_rescue_burst":
        dur = int(rng.integers(7, 22))  # <=21 d
        dose = float(rng.choice([10, 15, 20]))
        meds = [
            MedEvent("prednisone", "8640", dose, "mg", "oral", start, start + timedelta(days=dur))
        ]
        return meds, EscalationFact("gc_rescue_burst", "high", [], "oral", "steroid_rescue", start)

    if planted_class == "gc_bridge_initiation":
        # New tapered/time-limited oral course WITH a concurrent DMARD change -> high conf.
        dur = int(rng.integers(28, 56))
        meds = [
            MedEvent("prednisone", "8640", 10.0, "mg", "oral", start, start + timedelta(days=dur))
        ]
        bname = ("adalimumab", "etanercept", "tofacitinib")[rng.integers(0, 3)]
        brx, bdose, bunit, broute = _BIOLOGICS[bname]
        meds.append(
            MedEvent(
                bname,
                brx,
                bdose,
                bunit,
                broute,
                start + timedelta(days=int(rng.integers(0, 7))),
                None,
            )
        )
        return meds, EscalationFact(
            "gc_bridge_initiation", "high", [], "oral", "bridge_therapy", start
        )

    if planted_class == "gc_bridge_ambiguous":
        # Prolonged oral GC, sparse context (no taper, no concurrent DMARD) -> low confidence.
        dur = int(rng.integers(40, 70))
        meds = [
            MedEvent("prednisone", "8640", 10.0, "mg", "oral", start, start + timedelta(days=dur))
        ]
        return meds, EscalationFact(
            "gc_bridge_initiation",
            "low",
            ["gc_bridge_initiation", "gc_maintenance"],
            "oral",
            "bridge_therapy",
            start,
        )

    if planted_class == "dose_increase":
        meds = [MedEvent("methotrexate", "8261", 25.0, "mg", "oral", start, None)]
        return meds, EscalationFact("dose_increase", "high", [], "oral", "dose_increase", start)

    if planted_class == "dmard_initiation":
        bname = ("adalimumab", "etanercept", "tofacitinib")[rng.integers(0, 3)]
        brx, bdose, bunit, broute = _BIOLOGICS[bname]
        meds = [MedEvent(bname, brx, bdose, bunit, broute, start, None)]
        return meds, EscalationFact(
            "dmard_initiation", "high", [], broute, "dmard_initiation", start
        )

    if planted_class == "therapy_switch":
        bname = ("adalimumab", "etanercept", "tofacitinib")[rng.integers(0, 3)]
        brx, bdose, bunit, broute = _BIOLOGICS[bname]
        meds = [MedEvent(bname, brx, bdose, bunit, broute, start, None)]
        return meds, EscalationFact("therapy_switch", "high", [], broute, "therapy_switch", start)

    raise ValueError(f"unknown planted escalation class: {planted_class}")
