"""F4 dial-in tests — V1 four families."""

from __future__ import annotations

import datetime as dt

import pytest

from cinder.synthetic.f4.instantiate import instantiate_f4_case
from cinder.synthetic.flares import domains_shifted
from cinder.synthetic.m4_arithmetic import escalation_within_window, should_detect_predicates
from cinder.synthetic.params import default_params


def _wave_date(record, wave_number: int) -> dt.date:
    return next(w.wave_date for w in record.waves if w.wave_number == wave_number)


@pytest.mark.parametrize("case_id", ["CASE-01", "CASE-04", "CASE-06", "CASE-08"])
@pytest.mark.parametrize("variant_seed", [0, 7, 19])
def test_v1_instantiate_smoke(case_id: str, variant_seed: int) -> None:
    record, answer = instantiate_f4_case(case_id, variant_seed)
    assert record.patient_id == f"{case_id}-v{variant_seed:02d}"
    assert answer.patient_id == record.patient_id
    assert len(record.waves) == 6
    assert len(answer.per_wave) == 6


def test_case_04_comorbidity_discordance() -> None:
    record, answer = instantiate_f4_case("CASE-04", 0)
    assert answer.comorbidity_flags
    assert answer.phenotype_tier == "masked_minority"
    comorbid_waves = [
        w for w in answer.per_wave if w.flare_driver == "comorbidity_driven"
    ]
    assert comorbid_waves, "expected at least one comorbidity-driven wave"
    w = comorbid_waves[0]
    assert w.expected_M4_outcome == "should_miss_by_design"
    assert w.miss_reason == "comorbidity_driven"
    assert w.expected_UC_behavior == "flag_discordance"
    assert "HAQ-II" not in w.pro_domains_shifted
    assert len(w.pro_domains_shifted) >= 1
    assert not should_detect_predicates(w.pro_domains_shifted, False)


def test_case_01_axiom_invisible() -> None:
    record, answer = instantiate_f4_case("CASE-01", 0)
    flare_waves = [w for w in answer.per_wave if w.true_flare]
    assert len(flare_waves) == 1
    fw = flare_waves[0]
    assert fw.expected_M4_outcome == "axiom_invisible"
    assert fw.escalation_event is None
    assert len(fw.pro_domains_shifted) >= 2
    assert not should_detect_predicates(fw.pro_domains_shifted, False)


def test_case_06_temporal_linkage_missed() -> None:
    record, answer = instantiate_f4_case("CASE-06", 0)
    flare_waves = [w for w in answer.per_wave if w.true_flare]
    assert len(flare_waves) == 1
    fw = flare_waves[0]
    assert fw.expected_M4_outcome == "should_miss_by_design"
    assert fw.miss_reason == "temporal_linkage_missed"
    assert len(fw.pro_domains_shifted) >= 2
    assert fw.escalation_event is not None
    wave_date = _wave_date(record, fw.wave_number)
    esc_date = dt.date.fromisoformat(fw.escalation_event["date"])
    assert not escalation_within_window(wave_date, [esc_date])
    assert not should_detect_predicates(fw.pro_domains_shifted, False)


def test_case_08_slow_drift_sub_mcid_steps() -> None:
    _, answer = instantiate_f4_case("CASE-08", 0)
    params = default_params()
    assert answer.phenotype_tier == "adversarial"
    last = answer.per_wave[-1]
    assert last.true_flare is True
    assert last.miss_reason == "baseline_masking"
    assert last.expected_M4_outcome == "should_miss_by_design"
    # Answer sheet uses latent true values — no wave should show ≥2 domain crossings.
    for w in answer.per_wave:
        assert len(w.pro_domains_shifted) < 2
    # Final wave may show a single-domain step; cumulative drift is on the patient arc.
    assert len(last.pro_domains_shifted) <= 1


def test_case_08_variants_all_pass() -> None:
    for v in range(20):
        instantiate_f4_case("CASE-08", v)
