"""Cycle 44642568448 — v68 rejection/incumbent per-row reason accuracy.

The shipped fixed-path bundles record ``pivot_absent`` as the downgrade reason
for every defective incumbent, because that was the frozen label gate's
abstention reason at generation time.  ``pivot_absent`` is truthful about the
gate but hides the *content* cause: the row was rejected because its incumbent
evidence fails a frozen D2/D3/D4 predicate (or is not verbatim-grounded).

This cycle makes the per-row reason name the real content cause and publishes
content-fail rows the seam meets while they are already unverified under
``defective_already_unverified`` (never under ``retained_content_sound``).

Contract pinned here (direction v68 ordered work (1)):

* the four accepted-falsifier defective decisions are downgraded with their
  TRUE defect reason, and the one sound row stays verified/sound;
* a content-fail row that is already ``verified=false`` is published with its
  defects instead of disappearing;
* the frozen label gate's own ``abstention_reasons`` are untouched
  (``pivot_absent`` stays published) — this cycle changes the *recorded cause*
  of the content rejection, not the gate decision;
* the full-family probe still reads D2=D3=D4=0 on the 49 fixed-path bundles,
  false rejects 0, sound row retained;
* state stays fail-closed (``continue_recommended=true``; every gate flag
  false).

No frozen gate, rubric, threshold, bar or verdict contract is edited.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from product.query import counter_evidence_span as ces  # noqa: E402
import product.counter_incumbent_reason_probe as probe  # noqa: E402

RUN_ID = "44642568448"
ARTIFACT = ROOT / "results" / "product" / "counter_incumbent_reason" / (
    f"CYCLE_{RUN_ID}.json")
FAMILY = ROOT / "results" / "product" / "counter_content_family" / (
    f"CYCLE_{RUN_ID}.json")
STATE = ROOT / "state" / "product.json"

FIXED_LETTERHEAD = (
    "results/product/offline_slice/20261025T070356Z/rent-default.bundle.json")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_probe_marks_every_defect_reason_as_the_content_cause():
    rec = probe.run(run_id=RUN_ID)
    assert rec["checks"]["all_met"] is True
    rows = {r["decision_id"]: r for r in rec["defective_rows"]}
    assert set(rows) == {did for _rel, did, _d in probe.DEFECTIVE}
    for did, row in rows.items():
        assert row["before"]["counter_evidence_verified"] is True
        assert row["after"]["counter_evidence_verified"] is False
        assert row["after"]["counter_evidence_unevidenced"] is True
        reason = row["after"]["counter_evidence_unevidenced_reason"]
        assert reason == ces._DEFECT_REASON[row["expected_defects"][0]], (
            f"{did}: reason {reason!r} must name the frozen content defect")
        assert reason != "pivot_absent", (
            "the gate abstention reason must not masquerade as the content cause")
        assert row["record"]["defects"] == row["expected_defects"]
    sound = rec["sound_row"]
    assert sound["after"]["counter_evidence_verified"] is True
    assert sound["before"]["defects"] == []
    assert sound["retained_content_sound"] is not None


def test_gate_abstention_reasons_are_unchanged_by_the_reason_repair():
    rec = probe.run(run_id=RUN_ID)
    for row in rec["defective_rows"]:
        if row["gate_applied"]:
            # the frozen label gate's own published reasons are untouched
            assert row["gate_abstention_reasons"]
        else:
            # no frozen profile for this query: the content-only leg runs and
            # says so, claiming no gate abstention at all
            assert row["content_filter_leg"] == "content_only_no_anchor_profile"
            assert row["gate_abstention_reasons"] is None


def test_content_fail_rows_already_unverified_are_published_not_retained():
    doc = _load(ROOT / FIXED_LETTERHEAD)
    before = next(d for d in doc["decisions"]
                  if d.get("decision_id") == "gr_gerichte_ERZ 2010 25")
    assert before.get("counter_evidence_verified") is False
    out = ces.apply_verified_span_selection(
        copy.deepcopy(doc), qid=(doc.get("provenance") or {}).get("qid"))
    prov = out["provenance"]["counter_evidence_span"]
    rec = next(r for r in prov["defective_already_unverified"]
               if r["decision_id"] == "gr_gerichte_ERZ 2010 25")
    assert rec["reason_code"] == "d2_letterhead_zone"
    assert rec["defects"] == ["D2_letterhead_zone"]
    assert rec["leg"] == "seam_abstention_defective_already_unverified"
    assert "gr_gerichte_ERZ 2010 25" not in [
        r["decision_id"] for r in prov["retained_content_sound"]]
    assert prov["n_downgraded"] == 0  # there was no verified flag to flip


def test_committed_probe_artifact_matches_a_fresh_run():
    assert ARTIFACT.is_file()
    committed = _load(ARTIFACT)
    fresh = probe.run(run_id=RUN_ID)
    committed.pop("generated_at", None)
    fresh.pop("generated_at", None)
    assert committed == fresh


def test_full_family_probe_still_meets_the_ordered_work_2_rule():
    rec = _load(FAMILY)
    assert rec["fixed_path_family"]["totals"]["n_bundles"] == 49
    hist = rec["fixed_path_family"]["totals"]["defect_histogram"]
    assert hist["D2_letterhead_zone"] == 0
    assert hist["D3_markup_residue"] == 0
    assert hist["D4_language_marker_mismatch"] == 0
    assert rec["false_reject_count"] == 0
    assert rec["confirmed_set"]["decision_id"] == "bstger_SK.2023.49"
    assert rec["confirmed_set"]["still_verified"] is True
    assert rec["ordered_work_2_success_rule"]["met"] is True


def test_state_stays_fail_closed_and_names_this_cycle():
    st = _load(STATE)
    assert st["lane"] == "product"
    assert st["direction_version"] == 68
    assert st["continue_recommended"] is True
    assert st["human_gate_ready"] is False
    assert st["machine_gate_ready"] is False
    assert st["packet_admitted"] is False
    assert st["ready_for_owner_session"] is False
    assert str(st["current_cycle_run_id"]) == RUN_ID
    assert "CYCLE_40284658455" in st["accepted_run_id"]
