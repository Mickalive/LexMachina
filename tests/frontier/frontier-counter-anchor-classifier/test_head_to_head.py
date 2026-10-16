"""Integration: the full head-to-head on the served packet 38839347028.

Runs the candidate head-to-head against the incumbent on the SAME 65 rows in
the SAME run under the FROZEN rubric, and pins the charter's acceptance
outcomes:

  * the frozen rubric sha256 is the accepted hash (acceptance 1);
  * the incumbent's accepted 5/65 = 0.0769 is reproduced byte-identically
    against LABEL_HALF.json (acceptance 4);
  * the candidate is strictly better with INVERTED == 0 (acceptance 3, 4);
  * both non-vacuity controls score STRICTLY BELOW the candidate
    (acceptance 5).

Skips gracefully when the read-only accepted product mount is not present.
"""

from __future__ import annotations

import os

import pytest

from conftest import (
    ACCEPTED_LABEL_HALF,
    RULES_PATH,
    SERVED_BUNDLES_DIR,
)

pytestmark = pytest.mark.skipif(
    not os.path.isdir(SERVED_BUNDLES_DIR),
    reason="accepted product mount not present; integration test skipped",
)

from frontier_counter_anchor_classifier import run_head_to_head  # noqa: E402

FROZEN = "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"


@pytest.fixture(scope="module")
def report(tmp_path_factory):
    out = tmp_path_factory.mktemp("h2h") / "HEAD_TO_HEAD.json"
    return run_head_to_head.run(
        rules_path=RULES_PATH,
        bundles_dir=SERVED_BUNDLES_DIR,
        accepted_label_half_path=ACCEPTED_LABEL_HALF,
        out_path=str(out),
    )


def test_frozen_rubric_hash(report):
    assert report["rules_sha256"] == FROZEN
    assert report["rules_byte_identity_ok"] is True


def test_incumbent_reproduced_byte_identical(report):
    inc = report["incumbent"]
    assert inc["n_scored"] == 65
    assert inc["n_supported"] == 5
    assert inc["support_rate"] == pytest.approx(0.0769, abs=1e-3)
    assert inc["accepted_result_reproduced"] is True
    cmp = inc["accepted_comparison"]
    assert cmp["n_rows_divergent"] == 0
    assert cmp["only_in_accepted"] == []
    assert cmp["only_in_reproduced"] == []


def test_candidate_strictly_better(report):
    h2h = report["head_to_head"]
    assert h2h["same_rows_same_run"] is True
    assert h2h["incumbent_support_rate"] == pytest.approx(0.0769, abs=1e-3)
    assert h2h["candidate_support_rate_among_emitted"] == 1.0
    assert h2h["candidate_strictly_better_on_support"] is True
    assert h2h["incumbent_INVERTED"] == 0
    assert h2h["candidate_INVERTED"] == 0
    # the trade is published side by side, not hidden
    assert h2h["candidate_abstention_count"] == 60
    assert h2h["candidate_yield"] == 5
    assert h2h["incumbent_yield"] == 65


def test_candidate_emits_only_frozen_supported_rows(report):
    cand = report["candidate"]
    assert cand["n_emitted"] == 5
    assert cand["n_abstained"] == 60
    assert cand["candidate_defect_classes"] == {"SUPPORTED": 5}
    # every emitted label is supported by the frozen rubric
    assert cand["n_candidate_labels_supported"] == 5


def test_non_vacuity_controls_strictly_below(report):
    nv = report["non_vacuity"]
    cand_rate = nv["candidate_support_rate"]
    assert cand_rate == 1.0
    assert nv["inverted_label_control"]["support_rate"] < cand_rate
    assert nv["swapped_evidence_control"]["support_rate"] < cand_rate
    assert nv["all_controls_strictly_below_candidate"] is True
    assert nv["tie_would_void_run"] is False
    # the candidate's gate also refuses the control rows
    for row in nv["inverted_label_control"]["candidate_gate_on_these_rows"]:
        assert row["label"] == "ABSTAIN"
    for row in nv["swapped_evidence_control"]["candidate_gate_on_these_rows"]:
        assert row["label"] == "ABSTAIN"


def test_per_bundle_counts_present(report):
    bundles = {b["qid"]: b for b in report["bundles"]}
    assert set(bundles) == {"de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica"}
    assert bundles["de-kapitalverletzung"]["n_scored"] == 25
    assert bundles["fr-bail-entretien"]["n_scored"] == 15
    assert bundles["it-responsabilita-medica"]["n_scored"] == 25
    # INVERTED is reported per bundle and overall (acceptance 3)
    for b in report["bundles"]:
        assert "INVERTED" in b["defect_classes"] or b["defect_classes"].get("INVERTED", 0) == 0
    assert report["overall"]["INVERTED_incumbent"] == 0
    assert report["overall"]["INVERTED_candidate"] == 0
