"""test_synthetic_flares - Sprint 2 planting gates (arch Phase 2).

Generates a flare-planted cohort and asserts the §5 planting mechanics: visible flares
cross MCID in >=2 domains AND carry an in-window anchor-class escalation; invisible flares
have no escalation; the invisible:visible ratio is ~30-40%; the modal HAQ excursion is
marginal; the GC escalation-ambiguous probe family is present; and the trajectory-
sufficiency rule (R3) labels under-lookback flares should_miss_by_design.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np

from cinder.synthetic.flares import plant_flares
from cinder.synthetic.instruments import map_to_instruments
from cinder.synthetic.latent import draw_latent_trajectory
from cinder.synthetic.params import default_params
from cinder.synthetic.rng import CohortRNG
from cinder.synthetic.treatment import ANCHOR_CLASSES, NON_ANCHOR_CLASSES

N_PATIENTS = 600
N_WAVES = 6


def _wave_dates(n: int) -> list[date]:
    return [date(2020, 1, 15) + timedelta(days=180 * w) for w in range(n)]


def _run():
    params = default_params()
    rng = CohortRNG(101)
    wave_dates = _wave_dates(N_WAVES)
    all_flares, all_visible_cross, haq_excursions = [], [], []
    for i in range(N_PATIENTS):
        gen = rng.patient(i)
        baseline = params.baselines["moderate"]
        traj = draw_latent_trajectory(gen, N_WAVES, 0.0, params.correlation)
        plan = plant_flares(gen, traj, baseline, params, wave_dates, driver="RA_primary")
        post = map_to_instruments(gen, traj, baseline, params.icc)
        for fl in plan.flares:
            w = fl.wave_number
            if (
                w >= 1
                and fl.flare_class == "axiom_visible"
                and fl.expected_M4_outcome == "should_detect"
            ):
                # pro_domains_shifted is computed in-generator on the true values.
                all_visible_cross.append(len(fl.pro_domains_shifted) >= 2)
                haq_excursions.append(post.true_haq[w] - post.true_haq[w - 1])
            all_flares.append(fl)
    return params, all_flares, all_visible_cross, haq_excursions


def test_visible_flares_cross_two_domains() -> None:
    _, _, visible_cross, _ = _run()
    assert visible_cross, "no should_detect flares generated"
    rate = float(np.mean(visible_cross))
    assert rate >= 0.95, f"only {rate:.1%} of should_detect flares cross >=2 domains"


def test_visible_flares_have_anchor_escalation() -> None:
    _, flares, _, _ = _run()
    visible = [f for f in flares if f.flare_class == "axiom_visible"]
    assert visible
    for f in visible:
        assert f.escalation is not None
        assert f.escalation.escalation_class in ANCHOR_CLASSES
        assert f.escalation.escalation_class not in NON_ANCHOR_CLASSES


def test_invisible_flares_have_no_escalation() -> None:
    _, flares, _, _ = _run()
    invisible = [f for f in flares if f.flare_class == "axiom_invisible"]
    assert invisible
    for f in invisible:
        assert f.escalation is None
        assert f.expected_M4_outcome == "axiom_invisible"
        assert f.expected_UC_behavior == "widen"


def test_invisible_to_visible_ratio() -> None:
    _, flares, _, _ = _run()
    n_inv = sum(f.flare_class == "axiom_invisible" for f in flares)
    n_vis = sum(f.flare_class == "axiom_visible" for f in flares)
    frac = n_inv / (n_inv + n_vis)
    assert 0.28 <= frac <= 0.45, f"invisible fraction {frac:.1%} outside ~30-40% (§5)"


def test_modal_haq_excursion_is_marginal() -> None:
    _, _, _, haq_exc = _run()
    arr = np.array(haq_exc)
    # The bulk of should_detect flares are marginal: median HAQ excursion in a low band,
    # with a suprathreshold tail (mean > median).
    assert np.median(arr) <= 0.6, f"median HAQ excursion {np.median(arr):.2f} not marginal"
    assert arr.max() > 0.7, "no suprathreshold (severe) HAQ excursions in the tail"


def test_ambiguous_probe_family_present() -> None:
    _, flares, _, _ = _run()
    low = [
        f
        for f in flares
        if f.escalation is not None and f.escalation.classification_confidence == "low"
    ]
    assert low, "no escalation-ambiguous (low-confidence) probe flares planted"
    for f in low:
        assert f.expected_UC_behavior == "widen"
        assert f.escalation.candidate_classes  # candidates populated when low confidence


def test_trajectory_sufficiency_under_lookback() -> None:
    _, flares, _, _ = _run()
    early = [f for f in flares if f.wave_number < 2 and f.flare_class == "axiom_visible"]
    for f in early:
        assert f.expected_M4_outcome == "should_miss_by_design"
        assert f.miss_reason == "insufficient_lookback"
