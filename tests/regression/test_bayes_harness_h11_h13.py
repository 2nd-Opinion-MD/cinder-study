"""Port of the MVP's h11/h12/h13 conversational FORWARD-harness questions.

Source: ``server/scripts/forward_probe_gap_session_harness_questions.json``
at MVP commit ``00eaa9eb``. Vendored copy in
``tests/regression/fixtures/forward_probe_gap_session_harness_questions_AT_00eaa9eb.json``.

The h-series questions are FORWARD-shaped natural-language probes that
were originally answered by the chatbot's probe + gap pipeline. Here, in
the absence of the chatbot, we assert the kernel-level equivalent: the
question text declares a hypothesis (flare-in-30-days, progression-in-3-mo,
taper-safety) plus the artifacts it expects in the answer (posterior
probability, 90% credible interval, evidence event_ids). Calling the
kernel directly produces a UncertaintyCarrier that satisfies all of those
expectations structurally.

For the three h-series Bayesian questions the assertions are:

  h11 (flare): posterior probability + 90% band + evidence event ids;
               kernel must return a Beta posterior on ``flare_30d``.
  h12 (progression): point estimate + 90% band + prior source + evidence
               event ids; kernel must return a Beta posterior on
               ``progression_3mo``.
  h13 (taper): posterior probability of safe taper + 90% credible interval
               + regime-change check; kernel must return a Beta posterior
               on ``taper_safety``. (The "regime-change check" is a
               higher-layer concern handled at the analysis-orchestration
               layer; the kernel-level check is that ``confidence`` and
               ``band_90`` are populated so a regime change can be
               assessed downstream.)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from cinder.bayes import UncertaintyCarrier, bayesian_update_uc, load_graph

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FIXTURE_PTV = (
    _REPO_ROOT / "fixtures" / "real_ehr_632event" / "ptv_real_ehr_632event_v1_noarcs_scrubbed.json"
)
_HARNESS_QUESTIONS = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "forward_probe_gap_session_harness_questions_AT_00eaa9eb.json"
)

_H_QUESTION_TO_HYPOTHESIS = {
    "h11_bayes_flare": "flare_30d",
    "h12_bayes_progression": "progression_3mo",
    "h13_bayes_taper": "taper_safety",
}


def _load_h_questions() -> list[dict[str, Any]]:
    """Return only the three h11/h12/h13 Bayesian harness questions."""
    questions = json.loads(_HARNESS_QUESTIONS.read_text(encoding="utf-8"))
    return [q for q in questions if str(q.get("id", "")).startswith("h1") and "bayes" in q["id"]]


@pytest.fixture(scope="module")
def gh():
    return load_graph(_FIXTURE_PTV)


@pytest.fixture(scope="module")
def h_questions() -> list[dict[str, Any]]:
    qs = _load_h_questions()
    assert len(qs) == 3, (
        f"Expected exactly 3 Bayesian h-series questions in the vendored "
        f"FORWARD harness JSON, got {len(qs)}: {[q['id'] for q in qs]}"
    )
    return qs


def test_h11_h12_h13_present_with_expected_ids(h_questions: list[dict[str, Any]]) -> None:
    """The vendored harness JSON must carry all three h-series Bayesian probes."""
    ids = {q["id"] for q in h_questions}
    assert ids == set(_H_QUESTION_TO_HYPOTHESIS.keys())


@pytest.mark.parametrize(
    "question_id,hypothesis_id",
    list(_H_QUESTION_TO_HYPOTHESIS.items()),
)
def test_h_question_kernel_call_satisfies_question_artifact_requirements(
    gh, h_questions: list[dict[str, Any]], question_id: str, hypothesis_id: str
) -> None:
    """For each h-series Bayesian probe, the kernel produces all the artifacts
    the natural-language question asks for.

    The h11 question text asks for "the posterior probability ... with a 90%
    credible interval and the evidence event_ids that drove the update."
    h12 asks for "point estimate, 90% band, prior source, and the events used
    as evidence." h13 asks for "posterior probability of safe taper, the 90%
    credible interval, and a regime-change check on the evidence."

    The kernel-level check is that the returned UC carries:
      - point_estimate (a posterior probability for Beta-Bernoulli)
      - band_90 (the 90% credible interval)
      - evidence_event_ids
      - prior with a "source" field (weak vs mkg)
      - confidence + band_90 (the regime-change check inputs)
    """
    by_id = {q["id"]: q for q in h_questions}
    q = by_id[question_id]
    assert q["question"], "Question text must be present"

    uc = bayesian_update_uc(gh, hypothesis_id=hypothesis_id)
    assert isinstance(uc, UncertaintyCarrier)
    assert uc.hypothesis_id == hypothesis_id

    # h11 / h12 / h13 all want a posterior probability — Beta-Bernoulli
    # produces one in [0, 1].
    assert 0.0 <= uc.point_estimate <= 1.0

    # All three want a 90% credible interval.
    assert len(uc.band_90) == 2
    assert uc.band_90[0] <= uc.point_estimate <= uc.band_90[1]
    assert 0.0 <= uc.band_90[0] <= uc.band_90[1] <= 1.0

    # h11 + h12 ask for evidence event_ids; h13 asks for a regime-change
    # check on the evidence (which requires evidence to be tracked).
    assert isinstance(uc.evidence_event_ids, list)

    # h12 asks specifically for "prior source"; h13 asks for the prior context
    # in the regime-change check; both require a populated prior block.
    assert uc.prior, "UC must carry a non-empty prior block"
    assert uc.prior.get("source"), "UC prior must declare a 'source'"
    assert uc.prior["source"] in {"weak", "mkg", "clinician"}

    # h13's "regime-change check" is fed by confidence + band width.
    assert 0.0 <= uc.confidence <= 1.0
    assert uc.confidence_label in {"low", "moderate", "high", "very_high"}

    # spec_hash makes any regime-change check auditable.
    assert uc.spec_hash and uc.spec_hash.startswith("uc_")


def test_h_questions_kernel_outputs_serialize_round_trip(gh) -> None:
    """The kernel's UC outputs serialize JSON-cleanly through both wire shapes.

    Two serializers exist on UncertaintyCarrier:

      - to_dict() / from_dict() — the symmetric pair: every field that
        from_dict reads is what to_dict writes. Used for inter-process
        UC transport in the §10 open-replication pathway.
      - to_handoff_block() — an asymmetric envelope used by the MVP's
        probe→gap handoff: hypothesis_id is hoisted to the outer level
        as a routing key, and the inner "uc" block carries the rest.
        This is a routing convention, not a serializer; reconstructing a
        UC from a handoff envelope requires reading both levels.

    Both shapes must JSON-round-trip without byte loss. Only the
    to_dict()/from_dict() pair must reconstruct an identical UC.
    """
    for hid in _H_QUESTION_TO_HYPOTHESIS.values():
        uc = bayesian_update_uc(gh, hypothesis_id=hid)

        # 1. Symmetric serializer round-trips a fully-equal UC.
        d = uc.to_dict()
        d_round = json.loads(json.dumps(d))
        assert d_round == d
        rebuilt = UncertaintyCarrier.from_dict(d_round)
        assert rebuilt.hypothesis_id == uc.hypothesis_id
        assert rebuilt.point_estimate == uc.point_estimate
        assert tuple(rebuilt.band_90) == tuple(uc.band_90)
        assert rebuilt.spec_hash == uc.spec_hash

        # 2. Handoff envelope is JSON-clean and carries hypothesis_id at the
        # outer routing level. This is the MVP's probe→gap convention; CINDER
        # preserves it because the strategy doc §5.3 specifies it that way.
        block = uc.to_handoff_block()
        block_round = json.loads(json.dumps(block))
        assert block_round == block
        assert block["hypothesis_id"] == uc.hypothesis_id, (
            "to_handoff_block must hoist hypothesis_id to the outer routing level"
        )
        assert "uc" in block, "to_handoff_block must carry an inner 'uc' payload"
        # The inner uc payload itself does not need to round-trip via from_dict
        # because that's not its role — it's an envelope, not a serializer.
