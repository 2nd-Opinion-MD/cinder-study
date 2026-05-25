"""Port of the MVP's q11/q12/q13 tool-routing harness questions.

Source: ``server/scripts/ptv_toolkit_questions.json`` at MVP commit
``00eaa9eb``. Vendored copy in
``tests/regression/fixtures/ptv_toolkit_questions_AT_00eaa9eb.json``.

Each question in the source declares an ``expected_route``,
``expected_primary_tool``, ``expected_args_shape``, and
``must_have_any`` keyword list. In the MVP the chatbot emits a routing
trace that the harness asserted against; here we don't have the
chatbot, so we assert the kernel-level equivalent: that calling
``bayesian_update_uc`` with the question's declared ``hypothesis_id``
against the 632-event real-EHR fixture produces an
``UncertaintyCarrier`` whose ``hypothesis_id``, ``method``, ``prior``,
``posterior_params``, and ``basis`` text contain the structural shape
the chatbot's routing-layer assertions would have checked.

These three questions have ``expected_route == "bayesian_update"`` and
each picks a different built-in hypothesis. Together they exercise all
three of the Phase-1 default hypotheses (``flare_30d``,
``progression_3mo``, ``taper_safety``).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from cinder.bayes import (
    DEFAULT_HYPOTHESIS_PRIORS,
    UncertaintyCarrier,
    bayesian_update_uc,
    load_graph,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FIXTURE_PTV = (
    _REPO_ROOT / "fixtures" / "real_ehr_632event" / "ptv_real_ehr_632event_v1_noarcs_scrubbed.json"
)
_HARNESS_QUESTIONS = (
    Path(__file__).resolve().parent / "fixtures" / "ptv_toolkit_questions_AT_00eaa9eb.json"
)


def _load_bayes_questions() -> list[dict[str, Any]]:
    """Return only the three q11/q12/q13 Bayesian-routing questions."""
    questions = json.loads(_HARNESS_QUESTIONS.read_text(encoding="utf-8"))
    return [q for q in questions if q.get("expected_route") == "bayesian_update"]


@pytest.fixture(scope="module")
def gh():
    """Module-scoped GraphHandle on the 632-event real-EHR fixture."""
    return load_graph(_FIXTURE_PTV)


@pytest.fixture(scope="module")
def bayes_questions() -> list[dict[str, Any]]:
    qs = _load_bayes_questions()
    # Sanity: vendoring at 00eaa9eb is supposed to add exactly q11/q12/q13.
    assert len(qs) == 3, (
        f"Expected exactly 3 bayesian_update questions in the vendored "
        f"harness JSON, got {len(qs)}: {[q['id'] for q in qs]}"
    )
    return qs


def test_q11_q12_q13_all_target_known_hypotheses(bayes_questions: list[dict[str, Any]]) -> None:
    """Each question's hypothesis_id must be one of the three Phase-1 defaults."""
    expected_hypotheses = set(DEFAULT_HYPOTHESIS_PRIORS.keys())
    for q in bayes_questions:
        hid = q["expected_args_shape"]["hypothesis_id"]
        assert hid in expected_hypotheses, (
            f"Question {q['id']} targets {hid!r}, which is not in "
            f"DEFAULT_HYPOTHESIS_PRIORS={sorted(expected_hypotheses)}."
        )


def test_q11_q12_q13_cover_all_three_default_hypotheses(
    bayes_questions: list[dict[str, Any]],
) -> None:
    """Together the three questions must cover all three default hypotheses."""
    targeted = {q["expected_args_shape"]["hypothesis_id"] for q in bayes_questions}
    assert targeted == set(DEFAULT_HYPOTHESIS_PRIORS.keys())


@pytest.mark.parametrize(
    "question_id",
    ["q11_bayes_flare_30d", "q12_bayes_progression_3mo", "q13_bayes_taper_safety"],
)
def test_per_question_uc_is_well_formed(
    gh, bayes_questions: list[dict[str, Any]], question_id: str
) -> None:
    """Running the kernel against the fixture produces a well-formed UC.

    Asserts the structural shape the MVP's tool-routing assertions implied
    via ``expected_route=bayesian_update`` and ``expected_primary_tool=bayesian_update_uc``.
    """
    by_id = {q["id"]: q for q in bayes_questions}
    q = by_id[question_id]
    hid = q["expected_args_shape"]["hypothesis_id"]

    uc = bayesian_update_uc(gh, hypothesis_id=hid)

    assert isinstance(uc, UncertaintyCarrier), (
        f"bayesian_update_uc must return UncertaintyCarrier; got {type(uc)}"
    )
    assert uc.hypothesis_id == hid
    assert uc.method.startswith("beta_conjugate"), (
        f"Phase-1 hypotheses are Beta-Bernoulli; got method={uc.method!r}"
    )

    # Beta posterior — point estimate must be a valid probability.
    assert 0.0 <= uc.point_estimate <= 1.0
    # Band must be a length-2 ordered tuple bracketing the point estimate.
    assert len(uc.band_90) == 2
    assert uc.band_90[0] <= uc.point_estimate <= uc.band_90[1]
    assert 0.0 <= uc.band_90[0] <= uc.band_90[1] <= 1.0

    # Confidence is a 0..1 score.
    assert 0.0 <= uc.confidence <= 1.0

    # Prior provenance must be present and tagged "weak" pre-Phase-6.
    assert uc.prior, "UC must carry a non-empty prior block"
    assert uc.prior.get("source") == "weak", (
        "Pre-Phase-6 priors must be weak; MKG-informed priors land in Phase 6."
    )

    # spec_hash present and deterministic shape.
    assert uc.spec_hash and uc.spec_hash.startswith("uc_")

    # Posterior params reflect the Beta family.
    assert "alpha" in uc.posterior_params
    assert "beta" in uc.posterior_params
    assert uc.posterior_params["alpha"] > 0
    assert uc.posterior_params["beta"] > 0


@pytest.mark.parametrize(
    "question_id",
    ["q11_bayes_flare_30d", "q12_bayes_progression_3mo", "q13_bayes_taper_safety"],
)
def test_per_question_basis_carries_must_have_keywords(
    gh, bayes_questions: list[dict[str, Any]], question_id: str
) -> None:
    """The UC's basis text must contain the question's must_have_any keywords.

    This is the kernel-level equivalent of the MVP's chatbot-output keyword
    assertion: the deterministic kernel doesn't produce a chatbot answer, but
    its ``basis`` and the surrounding response shape (hypothesis_id + method
    + posterior_params) collectively carry the keywords the must_have_any
    list was checking for. We assert that at least one keyword from
    must_have_any appears somewhere in the UC's serialized handoff block.
    """
    by_id = {q["id"]: q for q in bayes_questions}
    q = by_id[question_id]
    hid = q["expected_args_shape"]["hypothesis_id"]
    must_have_any = q.get("must_have_any") or []
    assert must_have_any, f"Question {question_id} must declare a must_have_any list; got empty."

    uc = bayesian_update_uc(gh, hypothesis_id=hid)
    handoff = uc.to_handoff_block()
    blob = json.dumps(handoff, sort_keys=True).lower()

    # At least one of the question's must_have_any keywords must appear.
    matched = [kw for kw in must_have_any if kw.lower() in blob]
    assert matched, (
        f"None of {must_have_any!r} appeared in UC handoff block for "
        f"question {question_id}. Handoff blob keys: {list(handoff.get('uc', {}).keys())}"
    )


def test_kernel_is_deterministic(gh) -> None:
    """Two calls on the same inputs must produce bit-identical UCs.

    This is the load-bearing replicator-friendly property the protocol
    §10 commitment depends on.
    """
    uc1 = bayesian_update_uc(gh, hypothesis_id="flare_30d")
    uc2 = bayesian_update_uc(gh, hypothesis_id="flare_30d")
    assert uc1.to_dict() == uc2.to_dict()
    assert uc1.spec_hash == uc2.spec_hash
