"""Cycle 45947662468 — re-derive the post-hydration recheck delivery contract.

Every number published in results/product/post_hydration_recheck/CYCLE_45947662468.json
and reports/product/CYCLE_45947662468.md must be reproducible from the committed
tree with the product's own instruments.  This file is the next auditor's entry
point; it does not mint a gate and does not cite unadjudicated work as accepted.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from product.query import counter_evidence_span as ces  # noqa: E402

RUN = "45947662468"
RECHECK_ART = ROOT / "results/product/post_hydration_recheck" / f"CYCLE_{RUN}.json"
PROBE_ART = ROOT / "results/product/counter_content_family" / f"CYCLE_{RUN}.json"
STATE = json.loads((ROOT / "state/product.json").read_text(encoding="utf-8"))


def _load_module(rel: str, name: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _load_json(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_instrument_reproduces_the_committed_artifact():
    mod = _load_module("product/post_hydration_recheck_probe.py", "phr_probe")
    committed = json.loads(RECHECK_ART.read_text(encoding="utf-8"))
    fresh = mod.run(RUN, 68)
    for key in ("schema", "run_id", "direction_version", "reproduction",
                "fresh_family", "family_probe_link", "success", "claim_ceiling"):
        assert fresh[key] == committed[key], key
    assert committed["generated_at"]  # publication timestamp, not a measurement


def test_all_reported_success_flags_are_true():
    rec = json.loads(RECHECK_ART.read_text(encoding="utf-8"))
    assert rec["success"] and all(rec["success"].values()), rec["success"]


def test_defective_row_before_after_and_sound_row_are_rederived():
    rec = json.loads(RECHECK_ART.read_text(encoding="utf-8"))
    rep = rec["reproduction"]
    assert rep["defective_row"]["before"]["counter_evidence_verified"] is True
    assert rep["defective_row"]["before"]["frozen_defects"] == ["D2_letterhead_zone"]
    assert rep["defective_row"]["stage1_span_record_present"] is True
    after = rep["defective_row"]["after"]
    assert after["counter_evidence_verified"] is False
    assert after["counter_evidence_unevidenced"] is True
    assert after["counter_evidence_unevidenced_reason"] == "d2_letterhead_zone"
    assert after["counter_evidence"] == rep["defective_row"]["before"]["counter_evidence"]
    assert rep["sound_row"]["after"]["decision_id"] == "bstger_SK.2023.49"
    assert rep["sound_row"]["after"]["counter_evidence_verified"] is True
    assert rep["sound_row"]["after"]["frozen_defects"] == []
    assert rep["geometry_unchanged"] is True
    p = rep["provenance"]
    assert p["version"] == ces.CONTENT_RECHECK_VERSION == "counter_content_recheck/1"
    assert p["n_downgraded"] == 1 and p["source_stage"] == 1
    assert p["defects"] == ["D2_letterhead_zone"]


def test_fresh_family_bundles_carry_the_recheck_and_no_defective_verified_rows():
    rec = json.loads(RECHECK_ART.read_text(encoding="utf-8"))
    entries = rec["fresh_family"]
    assert len(entries) == 6  # four offline + server served + first-page render
    for entry in entries:
        path = ROOT / entry["path"]
        assert _sha(path) == entry["sha256"], entry["path"]
        doc = json.loads(path.read_text(encoding="utf-8"))
        verified = [d for d in doc["decisions"]
                    if d.get("counter_evidence_verified") is True]
        assert len(verified) == entry["n_verified"]
        assert entry["verified_defective_ids"] == [
            d["decision_id"] for d in verified
            if ces.frozen_content_defects(d.get("counter_evidence") or "", d)
        ]
        enriched = "first_page.bundle.json" not in entry["path"]
        if enriched:
            assert entry["recheck_version"] == ces.CONTENT_RECHECK_VERSION
            assert entry["recheck_n_downgraded"] == 0


def test_family_probe_link_matches_the_committed_probe_bytes():
    rec = json.loads(RECHECK_ART.read_text(encoding="utf-8"))
    link = rec["family_probe_link"]
    assert _sha(ROOT / link["artifact"]) == link["sha256"]
    probe = json.loads((ROOT / link["artifact"]).read_text(encoding="utf-8"))
    assert link["fixed_path_totals"] == probe["fixed_path_family"]["totals"]
    assert link["false_reject_count"] == probe["false_reject_count"] == 0
    assert link["ordered_work_2_success_rule"] == probe["ordered_work_2_success_rule"]
    assert link["ordered_work_2_success_rule"]["met"] is True
    h = link["fixed_path_totals"]["defect_histogram"]
    assert (h["D2_letterhead_zone"], h["D3_markup_residue"],
            h["D4_language_marker_mismatch"]) == (0, 0, 0)
    guarded = link["guarded_arm_yield_on_packet_v3"]
    assert guarded and set(guarded) == {"de-kapitalverletzung", "fr-bail-entretien",
                                        "it-responsabilita-medica"}
    for key, value in guarded.items():
        arm = probe["packet_v3_reemission"]["bundles"][key]
        assert value == arm["current_guarded"]["yield"]
        assert value >= arm["accepted_guarded"]["yield"]


def test_frozen_predicate_provenance_is_unchanged():
    rec = json.loads(RECHECK_ART.read_text(encoding="utf-8"))
    p = rec["reproduction"]["provenance"]["content_filter"]
    assert p == ces.content_filter_provenance()
    assert p["predicate_source_sha256"] == (
        "aac86527e5e54f0f9c527daac7ff1016d5124731b8ce673797520ff3dd53067d")
    assert ces.LETTERHEAD_ZONE_OFFSET_MAX == 400
    assert ces.MIN_MARKER_HITS == 3


def test_state_pointer_and_fail_closed_posture_are_honest():
    assert STATE["direction_version"] == 68
    assert STATE["accepted_run_id"] == "CYCLE_40284658455"
    assert STATE["accepted_commit"] == (
        "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83")
    gate = _load_json("results/audit/product/CYCLE_40284658455_GATE.json")
    assert gate["gate"] == "PASS" and gate["safe_to_integrate"] is True
    assert gate["required_fixes"] == []
    block = STATE["cycle_45947662468"]
    assert block["status"] == "PRODUCER_DELIVERED_UNADJUDICATED"
    assert block["continue_recommended"] is True
    for flag in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                 "ready_for_owner_session"):
        assert STATE[flag] is False, flag
    assert STATE["continue_recommended"] is True
    assert any("post_hydration" in ref for ref in STATE["evidence_refs"][-12:])
    assert STATE["capabilities"]["post_hydration_content_recheck"] is True


def test_no_producer_minted_audit_gate_for_this_run():
    assert not (ROOT / f"results/audit/product/CYCLE_{RUN}_GATE.json").exists()
    assert not (ROOT / f"reports/audit/product/CYCLE_{RUN}.md").exists()
