"""Population-level behaviour preservation for the 38970902524 repairs.

The accepted Outcome A measurement must be UNCHANGED by the repairs, and the
repaired harness must now cover the FULL 65-row population where the old one
covered 61 unique decision_id keys.

This is the anti-post-hoc-tuning guard: if a future edit to the gate, the
status mapping or the comparison silently moved a number on the accepted
population, these tests fail instead of quietly rewriting accepted evidence.

Skips gracefully when the read-only accepted product mount or the accepted
LABEL_HALF.json is not present.
"""

from __future__ import annotations

import os

import pytest

from conftest import ACCEPTED_LABEL_HALF, RULES_PATH, SERVED_BUNDLES_DIR

pytestmark = pytest.mark.skipif(
    not os.path.isdir(SERVED_BUNDLES_DIR) or not os.path.exists(ACCEPTED_LABEL_HALF),
    reason="accepted product mount or LABEL_HALF.json not present; skipped",
)

from frontier_counter_anchor_classifier import run_head_to_head  # noqa: E402

FROZEN = "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"

#: The accepted Outcome A numbers.  Frozen here as an independent pin so the
#: repairs cannot move them.
ACCEPTED_INCUMBENT_SUPPORT_RATE = 0.07692307692307693
ACCEPTED_N_SCORED = 65
ACCEPTED_N_SUPPORTED = 5
ACCEPTED_CANDIDATE_EMITTED = 5
ACCEPTED_CANDIDATE_ABSTAINED = 60
ACCEPTED_ABSTENTION_REASONS = {
    "evidence_absent": 16,
    "no_domain_anchor": 2,
    "no_intent_marker": 4,
    "pivot_absent": 38,
}
ACCEPTED_DUPLICATE_DECISION_IDS = {
    "bge_105 II 114",
    "bge_131 III 459",
    "bge_135 III 556",
    "bge_140 II 112",
}


@pytest.fixture(scope="module")
def report(tmp_path_factory):
    out = tmp_path_factory.mktemp("h2h_r2") / "HEAD_TO_HEAD_R2.json"
    return run_head_to_head.run(
        rules_path=RULES_PATH,
        bundles_dir=SERVED_BUNDLES_DIR,
        accepted_label_half_path=ACCEPTED_LABEL_HALF,
        out_path=str(out),
    )


def test_frozen_rubric_untouched_by_this_cycle(report):
    assert report["rules_sha256"] == FROZEN
    assert report["rules_byte_identity_ok"] is True


def test_incumbent_measurement_unchanged(report):
    inc = report["incumbent"]
    assert inc["n_scored"] == ACCEPTED_N_SCORED
    assert inc["n_supported"] == ACCEPTED_N_SUPPORTED
    assert inc["support_rate"] == pytest.approx(ACCEPTED_INCUMBENT_SUPPORT_RATE)
    assert inc["INVERTED"] == 0


def test_candidate_measurement_unchanged_by_the_status_repair(report):
    cand = report["candidate"]
    assert cand["n_rows"] == 65
    assert cand["n_emitted"] == ACCEPTED_CANDIDATE_EMITTED
    assert cand["n_abstained"] == ACCEPTED_CANDIDATE_ABSTAINED
    assert cand["candidate_support_rate"] == pytest.approx(1.0)
    assert cand["candidate_INVERTED"] == 0
    assert cand["abstention_reasons"] == ACCEPTED_ABSTENTION_REASONS
    assert cand["yield"] == pytest.approx(ACCEPTED_N_SUPPORTED / 65)


def test_unmapped_status_path_is_unreachable_on_this_population(report):
    """Proves, rather than asserts, that the advisory-E repair is
    behaviour-preserving HERE: every issued counter_status on the measured
    population is one the component maps, so no row is diverted."""
    cand = report["candidate"]
    assert cand["unmapped_counter_statuses_present"] == []
    assert cand["issued_counter_statuses_present"] == {
        "candidate-contrary": 11,
        "candidate-limiting": 45,
        "contrary_or_exception": 9,
    }


def test_accepted_comparison_now_covers_all_65_rows(report):
    """Advisory D: coverage was 61 of 65.  It must now be 65 of 65, with the
    duplicates reported instead of silently absorbed."""
    cmp = report["incumbent"]["accepted_comparison"]
    assert cmp["n_accepted_rows"] == 65
    assert cmp["n_reproduced_rows"] == 65
    assert cmp["n_rows_matched"] == 65
    assert cmp["n_rows_divergent"] == 0
    assert cmp["n_accepted_unique_decision_id_keys"] == 61
    assert set(cmp["duplicate_decision_ids_in_population"]) == ACCEPTED_DUPLICATE_DECISION_IDS
    assert cmp["coverage_is_full_population"] is True
    assert cmp["reproduced_byte_identical_verdicts"] is True


def test_non_vacuity_controls_still_strictly_below(report):
    nv = report["non_vacuity"]
    cand_support = nv["candidate_support_rate"]
    assert nv["inverted_label_control"]["support_rate"] < cand_support
    assert nv["swapped_evidence_control"]["support_rate"] < cand_support
    assert nv["all_controls_strictly_below_candidate"] is True


def test_swapped_control_gate_reasons_are_pivot_absent(report):
    """Advisory C: the true reason the gate refuses the swapped-evidence
    control.  Pinned here so the published reason cannot drift."""
    reasons = {
        r["control_id"]: r["reason_code"]
        for r in report["non_vacuity"]["swapped_evidence_control"]["candidate_gate_on_these_rows"]
    }
    assert reasons
    assert set(reasons.values()) == {"pivot_absent"}


def test_inverted_control_gate_reason_is_polarity_inverted(report):
    reasons = {
        r["inject_id"]: r["reason_code"]
        for r in report["non_vacuity"]["inverted_label_control"]["candidate_gate_on_these_rows"]
    }
    assert set(reasons.values()) == {"polarity_inverted"}


def test_headline_head_to_head_unchanged(report):
    h2h = report["head_to_head"]
    assert h2h["incumbent_support_rate"] == pytest.approx(ACCEPTED_INCUMBENT_SUPPORT_RATE)
    assert h2h["candidate_support_rate_among_emitted"] == pytest.approx(1.0)
    assert h2h["candidate_strictly_better_on_support"] is True
    assert h2h["candidate_abstention_count"] == 60


def test_run_is_not_written_over_the_accepted_claim_artifact(tmp_path_factory):
    """The accepted HEAD_TO_HEAD.json must never be the default output."""
    import inspect
    from frontier_counter_anchor_classifier import run_head_to_head as h
    src = inspect.getsource(h.main)
    assert "HEAD_TO_HEAD_R2_38970902524.json" in src
    assert os.path.exists(RULES_PATH)