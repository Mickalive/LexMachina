"""Unit tests for the D2 path-scope probe (run 40070818687).

Synthetic fixtures only: no product regeneration, no network, no frozen-bar
scoring.  These tests pin the frozen decision rule and the controls so the
claim-bearing run cannot silently change its own verdict logic.
"""
from __future__ import annotations

import json
from pathlib import Path

from evaluation.d2_path_scope_probe import (
    TARGET_DECISION,
    _find_lines,
    compute_verdict,
    controls,
    score_bundle_file,
)

LETTERHEAD = (
    "Kantonsgericht von Graubünden\nDretgira chantunala dal Grischun\n"
    "Tribunale cantonale dei Grigioni\n____"
)
BODY = (
    "Im Oberschulhaus X wird der Unterricht um 8:15 Uhr fortgesetzt. "
    "Der angeklagte Mieter hatte die Mietzinse per 1. Januar 2012 erhöht."
)


def _bundle(rows, span_prov=None):
    doc = {"query": "q", "decisions": rows, "provenance": {}}
    if span_prov is not None:
        doc["provenance"]["counter_evidence_span"] = span_prov
    return doc


def _write(tmp_path: Path, doc: dict) -> Path:
    p = tmp_path / "b.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    return p


def test_controls_non_vacuity_and_digests():
    ctl = controls()
    assert ctl["C3"]["passed"], ctl["C3"]
    assert ctl["C4"]["passed"], ctl["C4"]
    assert ctl["C5"]["passed"], ctl["C5"]
    assert "D2_letterhead_zone" in ctl["C5"]["letterhead_defects"]
    assert "D2_letterhead_zone" not in ctl["C5"]["mid_defects"]


def test_score_bundle_flags_letterhead_and_reports_span_provenance(tmp_path):
    rows = [
        {
            "decision_id": TARGET_DECISION,
            "counter_status": "candidate-limiting",
            "counter_evidence": LETTERHEAD,
            "counter_evidence_verified": True,
            "language": "de",
            "full_text": LETTERHEAD + BODY,
            "full_text_status": "lazy",
        },
        {
            "decision_id": "clean_row",
            "counter_status": "cited",
            "counter_evidence": BODY,
            "counter_evidence_verified": True,
            "language": "de",
            "full_text": LETTERHEAD + ("\n" * 80) + ("K" * 400) + BODY,
            "full_text_status": "lazy",
        },
    ]
    p = _write(tmp_path, _bundle(rows))
    score = score_bundle_file(p)
    assert score["n_verified"] == 2
    assert score["n_verified_with_defects"] == 1
    assert score["defective_decision_ids"] == [TARGET_DECISION]
    assert score["defect_histogram"] == {"D2_letterhead_zone": 1}
    assert score["bundle_level_counter_evidence_span_present"] is False


def test_score_bundle_reports_span_seam_provenance_when_present(tmp_path):
    p = _write(tmp_path, _bundle([], span_prov={"applied": True, "n_selected": 1}))
    score = score_bundle_file(p)
    assert score["bundle_level_counter_evidence_span_present"] is True
    assert score["bundle_level_counter_evidence_span"]["applied"] is True


def test_verdict_path_scope_when_d2_persists_and_seam_absent():
    arm1_score = {
        "verified_rows": [
            {"decision_id": TARGET_DECISION, "defects": ["D2_letterhead_zone"],
             "evidence_head": LETTERHEAD, "detail": {"first_offset": 0}},
        ],
        "bundle_level_counter_evidence_span_present": False,
    }
    v = compute_verdict(arm1_score, {"outcome": "FILTER_REJECTS_ROW"}, LETTERHEAD)
    assert v["verdict"] == "PATH_SCOPE_RESIDUAL"
    assert v["arm1_target_d2_present"] is True
    assert v["arm1_span_seam_provenance_present"] is False


def test_verdict_stale_artifact_when_d2_cleared_and_seam_present():
    arm1_score = {
        "verified_rows": [
            {"decision_id": TARGET_DECISION, "defects": [], "evidence_head": BODY,
             "detail": {"first_offset": 400}},
        ],
        "bundle_level_counter_evidence_span_present": True,
    }
    v = compute_verdict(arm1_score, {"outcome": "FILTER_REQUOTES_ROW"}, LETTERHEAD)
    assert v["verdict"] == "STALE_ARTIFACT_RESIDUAL"


def test_verdict_mixed_when_evidence_contradicts_both_branches():
    arm1_score = {
        "verified_rows": [
            {"decision_id": TARGET_DECISION, "defects": ["D2_letterhead_zone"],
             "evidence_head": LETTERHEAD, "detail": {"first_offset": 0}},
        ],
        "bundle_level_counter_evidence_span_present": True,
    }
    v = compute_verdict(arm1_score, {"outcome": "FILTER_LEAVES_ROW"}, LETTERHEAD)
    assert v["verdict"] == "MIXED_OR_INCONCLUSIVE"


def test_find_lines_locates_pipeline_gate_snippets(tmp_path):
    f = tmp_path / "pipeline.py"
    f.write_text(
        "line1\n"
        "    if not fixture_generation and adversarial_retrieval:\n"
        "        audited = apply_verified_span_selection(\n"
        "            audited,\n",
        encoding="utf-8",
    )
    hits = _find_lines(f, (
        "if not fixture_generation and adversarial_retrieval:",
        "audited = apply_verified_span_selection(",
    ))
    assert [h["line"] for h in hits] == [2, 3]
    assert hits[0]["file"] == "pipeline.py"
