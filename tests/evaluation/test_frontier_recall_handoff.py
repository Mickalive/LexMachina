"""Tests for the frontier-recall handoff consumption instrument.

Pins the v57 ordered duty contract: this lane publishes the accepted
frontier-query-concept-recall numbers BESIDE its own accepted records, every
divergence is a headline, and a drifted pinned input is exit 2 (never a silent
re-pin).  Pure-logic checks run without the frontier mount; the end-to-end
check runs offline against committed bytes and degrades to exit 2 when the
ephemeral mount is absent (which is an environment reading, never a pass).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation.frontier_recall_handoff import (  # noqa: E402
    SCHEMA, VERDICT_DIVERGENCE, VERDICT_ENVIRONMENT, VERDICT_NO_DIVERGENCE,
    compare_coverage, compare_recall, extract_frontier_coverage,
    extract_lane_eval_coverage, extract_lane_product_coverage, verify_inputs,
)

HYP = _REPO_ROOT / "evaluation/FRONTIER_RECALL_HANDOFF_HYPOTHESIS_V1.json"


def test_hypothesis_is_frozen_with_exit_rules():
    hyp = json.loads(HYP.read_text(encoding="utf-8"))
    assert hyp["schema"] == "lex-evaluation-frontier-recall-handoff-hypothesis/1"
    assert set(hyp["success_rule"]) == {"exit_0", "exit_1", "exit_2", "no_weakening"}
    assert len(hyp["inputs"]) == 10
    assert "pre_observed_at_design" in hyp
    assert "DISCLOSED PRE-OBSERVED" in hyp["pre_observed_at_design"]["disclosure"]


def test_verify_inputs_flags_digest_drift_and_missing():
    with tempfile.TemporaryDirectory() as td:
        body = b"payload"
        good = Path(td) / "good.json"
        good.write_bytes(body)
        sha = hashlib.sha256(body).hexdigest()
        hypothesis = {"inputs": {
            "good": {"path": str(good), "sha256": sha},
            "drifted": {"path": str(good), "sha256": "0" * 64},
            "missing": {"path": str(Path(td) / "nope.json"), "sha256": sha},
        }}
        resolved, problems = verify_inputs(hypothesis)
        assert list(resolved) == ["good"]
        assert len(problems) == 2
        assert any("drift" in p for p in problems)
        assert any("missing" in p for p in problems)


def test_compare_coverage_no_divergence_when_all_sides_agree():
    lane_eval = {"q1": {"n_rows": 3, "concepts": ["a", "b"],
                        "under_covered": ["b"]}}
    lane_product = {"q1": {"concepts": ["a", "b"], "under_covered": ["b"]}}
    frontier = {"q1": {"n_rows": 3, "concepts": ["a", "b"], "under_covered": ["b"]}}
    # the frozen cell list iterates the three canonical questions; missing ones
    # must show up as divergences, so feed all three identically
    for qid in ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica"):
        lane_eval[qid] = dict(lane_eval["q1"])
        lane_product[qid] = dict(lane_product["q1"])
        frontier[qid] = dict(frontier["q1"])
    out = compare_coverage(lane_eval, lane_product, frontier)
    assert out["n_divergences"] == 0
    assert out["divergences"] == []
    assert VERDICT_NO_DIVERGENCE  # vocabulary still exported


def test_compare_coverage_names_product_side_subset_as_divergence():
    lane_eval = {qid: {"n_rows": 3, "concepts": ["a", "b", "c"],
                       "under_covered": []}
                 for qid in ("de-kapitalverletzung", "fr-bail-entretien",
                             "it-responsabilita-medica")}
    lane_product = {qid: {"concepts": ["a", "b"], "under_covered": []}
                    for qid in lane_eval}
    frontier = {qid: {"n_rows": 3, "concepts": ["a", "b", "c"], "under_covered": []}
                for qid in lane_eval}
    out = compare_coverage(lane_eval, lane_product, frontier)
    assert out["n_divergences"] == 3  # one per question
    assert any("product_side_concept_extraction" in d for d in out["divergences"])
    subset_cells = [c for c in out["cells"]
                    if c["cell"] == "product_side_concepts_vs_eval_side"]
    assert all(c["product_is_subset_of_eval"] is True for c in subset_cells)


def test_compare_recall_headlines_a_single_cell_divergence():
    keys = [(s, l) for s in ("corporate-criminal-liability", "business-judgment-rule",
                             "petty-theft-dismissal", "rent-default")
            for l in ("de", "fr", "it")]
    lane = {}
    for slug, lang in keys:
        if slug == "rent-default":
            # the frozen benchmark carries no authority set for rent-default:
            # the lane cell is not_measurable with empty hits
            lane[(slug, lang)] = {"passed": None, "hits": []}
        else:
            lane[(slug, lang)] = {
                "passed": lang == "de",
                "hits": ["x"] if lang == "de" else []}
    frontier = {k: {"measurable": k[0] != "rent-default",
                    "hits": list(lane[k]["hits"])}
                for k in keys}
    frontier[("corporate-criminal-liability", "de")]["hits"] = ["x", "y"]
    out = compare_recall(lane, lane, frontier)
    assert out["n_divergences"] == 1
    assert "corporate-criminal-liability::de" in out["divergences"][0]


def test_extractors_roundtrip_on_synthetic_records():
    sam = {"gates": [
        {"gate": "question_native_concept_coverage::de-kapitalverletzung",
         "measured": {"n_bundle_rows": 2, "concepts": ["a", "b"],
                      "concepts_with_zero_rows": ["b"]}},
        {"gate": "unrelated::gate", "measured": {}}]}
    got = extract_lane_eval_coverage(sam)
    assert got["de-kapitalverletzung"] == {"n_rows": 2, "concepts": ["a", "b"],
                                           "under_covered": ["b"]}
    handoff = {"bundles": [{"bundle": "de-kapitalverletzung",
                            "bundle_sha256": "ff",
                            "after": {"measured_query_concepts": ["a"],
                                      "measured_query_concepts_under_covered": []}}]}
    got = extract_lane_product_coverage(handoff)
    assert got["de-kapitalverletzung"]["concepts"] == ["a"]
    harness = {"served_questions": {"de-kapitalverletzung": {
        "A0_baseline_shipped": {"n_rows": 2, "concepts": ["a", "b"],
                                "under_covered": ["b"]}}}}
    got = extract_frontier_coverage(harness)
    assert got["de-kapitalverletzung"]["under_covered"] == ["b"]


def test_end_to_end_offline_against_committed_bytes():
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "rec.json"
        report_dir = Path(td) / "reports"
        proc = subprocess.run(
            [sys.executable, "-m", "evaluation.frontier_recall_handoff",
             "--run-id", "pytest_scratch", "--out", str(out),
             "--report-dir", str(report_dir)],
            cwd=str(_REPO_ROOT), capture_output=True, text=True, timeout=300)
        assert proc.returncode in (0, 1, 2), proc.stderr[-400:]
        assert out.is_file(), "instrument must persist a record even on exit 2"
        rec = json.loads(out.read_text(encoding="utf-8"))
        assert rec["schema"] == SCHEMA
        if proc.returncode == 2:
            # frontier mount absent or drifted: an environment reading, never a pass
            assert rec["verdict"] == VERDICT_ENVIRONMENT
            assert rec["input_digest_problems"]
        else:
            assert rec["verdict"] in (VERDICT_NO_DIVERGENCE, VERDICT_DIVERGENCE)
            assert rec["claim_ceiling"]
            assert rec["human_gate_ready"] is False
            assert rec["owner_decision_required"] is False
            # the frontier outcome is copied, never adjudicated here
            assert "copy_only_note" in rec["frontier_outcome_copy"]
        scratch_marker = Path(td) / "reports"
        assert scratch_marker.exists()


def test_verdict_vocabulary_is_frozen():
    assert VERDICT_NO_DIVERGENCE == "CONSUMED_NO_DIVERGENCE"
    assert VERDICT_DIVERGENCE == "DIVERGENCE_HEADLINE"
    assert VERDICT_ENVIRONMENT == "ENVIRONMENT"
