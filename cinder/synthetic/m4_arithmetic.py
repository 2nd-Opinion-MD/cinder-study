"""m4_arithmetic.py — pure M4.B / M4.C predicates for golden-anchor verification.

These re-derive answer-sheet expectations from emitted PRO trajectories and
escalation dates. They are NOT an M4 module re-implementation; they gate that
hand-crafted goldens stay arithmetically consistent with the protocol contract.
"""

from __future__ import annotations

import datetime as dt
from typing import Iterable

from cinder.synthetic.params import MCID

__all__ = [
    "domains_crossing_mcid",
    "escalation_within_window",
    "rapid3_from_observed",
    "should_detect_predicates",
]


def rapid3_from_observed(haq_ii: float, pain_vas: float, pga_vas: float) -> float:
    """Match ``instruments.map_to_instruments`` RAPID3 composite (computed, never drawn)."""
    fn = round(min(max(haq_ii * (10.0 / 3.0), 0.0), 10.0), 1)
    pn = round(min(max(pain_vas / 10.0, 0.0), 10.0), 1)
    ptga = round(min(max(pga_vas / 10.0, 0.0), 10.0), 1)
    return round(fn + pn + ptga, 1)


def domains_crossing_mcid(
    prev: dict[str, float],
    curr: dict[str, float],
    mcid: MCID | None = None,
) -> list[str]:
    """Return PRO domains whose worsening delta meets M4.B MCID (worsening direction)."""
    mcid = mcid or MCID()
    shifted: list[str] = []
    if curr["HAQ-II"] - prev["HAQ-II"] >= mcid.haq_ii:
        shifted.append("HAQ-II")
    if curr["PainVAS"] - prev["PainVAS"] >= mcid.pain_vas:
        shifted.append("PainVAS")
    if curr["PatientGlobalVAS"] - prev["PatientGlobalVAS"] >= mcid.pga_vas:
        shifted.append("PatientGlobalVAS")
    return shifted


def escalation_within_window(
    wave_date: dt.date,
    escalation_dates: Iterable[dt.date | None],
    *,
    window_days: int = 90,
) -> bool:
    """True if any escalation date falls within ±window_days of the wave date (M4.C)."""
    for ed in escalation_dates:
        if ed is None:
            continue
        if abs((wave_date - ed).days) <= window_days:
            return True
    return False


def should_detect_predicates(
    domains_shifted: list[str],
    has_in_window_escalation: bool,
) -> bool:
    """Axiom-visible detectability: ≥2 domains + escalation in ±90 d."""
    return len(domains_shifted) >= 2 and has_in_window_escalation
