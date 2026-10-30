#!/usr/bin/env python3
"""Pins the operational resume of the 40985854750 snapshot by 40990419541.

Run 40985854750 wrote a 90-file SUBSTANTIVE delta at 6128caee and then its
lane-cycle (producer) agent was stopped by the workflow's own 2700 s work
quantum (2704.0 s, exit 78, LEX_WORK_QUANTUM_EXPIRED pid=2501).  State
validation and write scope were skipped, the always-run persist step published
the already-written tree, and audit/integrate were skipped, so no gate exists
and the run is UNADJUDICATED.

This cycle preserves that snapshot, proves the failure and the durable delta
from committed evidence, re-verifies the inherited v68 deliverable (three
fresh full-chain live slices, two offline slices, the 69-bundle content family
and the progressive smoke), and re-keys state/report/test/profile/dossier/
route/intake to 40990419541.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state" / "product.json"
ORCH = ROOT / "results" / "product" / "orchestration"
AR = ROOT / "results" / "product" / "audit_readiness"
REPORT = ROOT / "reports" / "product" / "CYCLE_40990419541.md"
RAW = ORCH / "CYCLE_40985854750_run_jobs_raw.json"
FLAT = ORCH / "CYCLE_40985854750_audit_step_diagnosis.json"
DIAG = ORCH / "CYCLE_40985854750_resume_diagnosis.json"
DELTA = ORCH / "CYCLE_40985854750_delta_substance.json"
CONTENT_FAMILY = (ROOT / "results" / "product" / "counter_content_family"
                  / "CYCLE_40990419541.json")
SMOKE = (ROOT / "results" / "product" / "progressive_smoke"
         / "CYCLE_40990419541_progressive_smoke.json")
SLICE_ROOT = ROOT / "results" / "product" / "offline_slice"
LIVE_ROOT = ROOT / "results" / "product" / "live_slice"
STAGE_DISCLOSURE = (ROOT / "results" / "product" / "live_slice_stages"
                    / "STAGE_DISCLOSURE_AMENDMENT.json")
DOSSIER = AR / "CYCLE_40990419541_audit_readiness.json"
ROUTE = AR / "CYCLE_40990419541_AUDIT_ROUTE.json"
INTAKE = AR / "CYCLE_40990419541_AUDIT_INTAKE.md"
RUN = "40990419541"
RESUME = "40985854750"
PRED_RUN = "40977042308"
SNAPSHOT = "6128caee40dd61945c5fb41b9e1bac8dd5233acf"
PREVSNAP = "94027ff580dea1aeb82a99fe213b870d355879fe"
ACCEPTED = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"

LIVE_SLICES = {
    "20261030T013827Z": {
        "n_decisions": 158,
        "counter_status_bearing_rows": 19,
        "local_map_s": 0.1997,
        "upstream_retrieval_s": 28.4197,
    },
    "20261030T015422Z": {
        "n_decisions": 108,
        "counter_status_bearing_rows": 17,
        "local_map_s": 0.1842,
        "upstream_retrieval_s": 20.8099,
    },
    "40977042308_test": {
        "n_decisions": 108,
        "counter_status_bearing_rows": 18,
        "local_map_s": 0.1859,
        "upstream_retrieval_s": 25.809,
    },
}


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_state_pointer_posture_and_append_only_blocks():
    state = _json(STATE)
    assert state["accepted_run_id"] == "CYCLE_40284658455"
    assert state["accepted_commit"] == ACCEPTED
    assert state["current_cycle_run_id"] == RUN
    assert state["current_run"] == RUN
    assert state["current_run_id"] == RUN
    assert state["direction_version"] == 68
    assert state["cycle_status"] == "COMPLETE"
    assert state["continue_recommended"] is True
    assert state["human_gate_ready"] is False
    assert state["machine_gate_ready"] is False
    assert state["ready_for_owner_session"] is False
    assert state["packet_admitted"] is False
    assert state["owner_decision_required"] is False
    block = state["cycle_40990419541_operational_resume"]
    assert block["run_id"] == RUN
    assert block["resumed_run_id"] == RESUME
    assert block["predecessor_run_id"] == PRED_RUN
    assert block["resumed_snapshot_head"] == SNAPSHOT
    assert block["predecessor_snapshot_head"] == PREVSNAP
    assert block["diagnosis_of_resumed"] == \
        "results/product/orchestration/CYCLE_40985854750_resume_diagnosis.json"
    rf = block["resumed_failure"]
    assert rf["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert "2704.0 s" in rf["team_job"]
    assert "exit 78" in rf["team_job"]
    assert "OBSERVED_QUANTUM_EXPIRED" in rf["mechanism"]
    assert "pid=2501" in rf["mechanism"]
    assert "not a product defect" in rf["mechanism"]
    assert rf["gate_file_written"] is False
    assert rf["adjudication"] == "UNADJUDICATED"
    assert "COMMITTED_DELTA" in rf["durable_delta"]
    assert "90 changed files" in rf["durable_delta"]
    assert "15 substantive" in rf["durable_delta"]
    pf = block["predecessor_failure"]
    assert pf["classification"] == \
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    assert "2704.0 s" in pf["audit_job"]
    assert "LEX_WORK_QUANTUM_EXPIRED" in pf["audit_job"]
    assert pf["gate_file_written"] is False
    assert pf["adjudication"] == "UNADJUDICATED"
    assert block["snapshot_audit_readiness"]["state_advanced"] is True
    assert block["posture"]["continue_recommended"] is True
    assert block["posture"]["human_gate_ready"] is False
    assert state["audit_route"]["artifact"] == \
        "results/product/audit_readiness/CYCLE_40990419541_AUDIT_ROUTE.json"
    # Append-only predecessors and their reports must survive.
    assert state["cycle_40863791646_operational_resume"]
    assert state["cycle_40858799166_operational_resume"]
    assert state["cycle_40840720468_operational_resume"]
    assert (ROOT / "reports" / "product" / "CYCLE_40863791646.md").is_file()


def test_run_history_chain_is_append_only():
    state = _json(STATE)
    hist = {str(e.get("run_id")): e for e in state["run_history"]}
    for run_id in (PRED_RUN, RESUME, RUN):
        assert run_id in hist, run_id
    pred = hist[PRED_RUN]
    assert pred["accepted"] is False
    assert "TEAM_GREEN" in pred["status"]
    assert "SUCCESS" in pred["team_job"]
    assert "2704.0 s" in pred["audit_job"]
    assert "OBSERVED_QUANTUM_EXPIRED" in pred["audit_job"]
    assert pred["audit_gate"] == "NONE_YET"
    res = hist[RESUME]
    assert res["accepted"] is False
    assert "QUANTUM_DEATH" in res["status"]
    assert "2704.0 s" in res["team_job"]
    assert "exit 78" in res["team_job"]
    assert "OBSERVED_QUANTUM_EXPIRED" in res["team_job"]
    assert "pid=2501" in res["team_job"]
    assert res["audit_job"] == "skipped (team job did not succeed)"
    assert "90 changed files" in res["durable_delta"]
    cur = hist[RUN]
    assert cur["status"] == \
        "TEAM_JOB_LANE_CYCLE_QUANTUM_DEATH_RESUME_FRESH_SLICES_REVERIFIED_" \
        "AUDIT_READY_UNADJUDICATED"
    assert cur["resumed_run"] == RESUME
    assert cur["accepted"] is False
    assert cur["accepted_commit"] == ACCEPTED
    assert cur["report_of_record"] == "reports/product/CYCLE_40990419541.md"
    assert cur["cycle_test"] == "product/tests/test_cycle_40990419541.py"
    assert cur["audit_gate"] == "NONE_YET"
    # Earlier history stays append-only.
    assert "40863791646" in hist and "40858799166" in hist


def test_orchestration_failure_is_observed_quantum_expiry():
    for path in (RAW, FLAT, DIAG, DELTA):
        assert path.is_file(), path
    flat = _json(FLAT)
    assert flat["run_id"] == RESUME
    assert flat["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    mech = flat["mechanism"]
    assert mech["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert mech["quantum_expired"] is True
    assert mech["quantum_seconds"] == 2700
    assert mech["exit_code"] == 78
    assert mech["logs_endpoint_status"] == 403
    assert flat["audit"]["conclusion"] == "skipped"
    assert flat["audit"]["gate_file_written"] is False
    assert flat["team"]["failed_step"] == "Run lane cycle"
    assert flat["team"]["failed_step_seconds"] == 2704.0
    assert flat["team"]["producer_state_validation_step_conclusion"] == "skipped"
    assert flat["team"]["write_scope_step_conclusion"] == "skipped"
    assert flat["team"]["team_snapshot_persisted_after_failed_team_job"] is True
    diag = _json(DIAG)
    assert diag["run_id"] == RESUME
    assert diag["predecessor_run_id"] == PRED_RUN
    assert diag["durable_delta"]["classification"] == "COMMITTED_DELTA"
    assert diag["durable_delta"]["changed_files"] == 90
    assert diag["durable_delta"]["snapshot_head"] == SNAPSHOT
    assert diag["durable_delta"]["predecessor_head"] == PREVSNAP
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["accepted"] is False
    delta = _json(DELTA)
    assert delta["changed_files"] == 90
    assert delta["delta_substance"] == "SUBSTANTIVE"
    assert delta["product_work"] is True
    assert delta["counts"]["results_artifact"] == 15
    assert delta["counts"]["cache_timestamp_only"] == 26
    assert delta["counts"]["cache_content"] == 49
    assert any("live_slice/20261030T013827Z.json" in p
               for p in delta["substantive_files"])
    assert any("STAGE_DISCLOSURE_AMENDMENT.json" in p
               for p in delta["substantive_files"])


def test_fresh_live_slices_cover_the_full_chain():
    disclosure = _json(STAGE_DISCLOSURE)
    assert disclosure["failures"] == []
    by_run = {r["run_id"]: r for r in disclosure["records"]}
    for stamp, expected in LIVE_SLICES.items():
        record = _json(LIVE_ROOT / f"{stamp}.json")
        assert record["verdict"] == "PASS"
        assert record["mode"] == "full_chain"
        assert record["n_failed_checks"] == []
        assert record["stages_executed"] == {
            "answer": True,
            "canonical_chain": True,
            "counter_authority": True,
            "enrichment_attempted": True,
            "enrichment_completed": True,
            "map": True,
            "retrieval": True,
        }
        assert record["checks"]["canonical_chain_ran"] is True
        assert record["checks"]["every_row_has_a_source_link"] is True
        assert record["checks"]["every_row_has_xy"] is True
        assert record["checks"]["enrichment_never_moved_a_point_already_on_the_map"] is True
        assert record["checks"]["page_contract_ok"] is True
        assert record["map"]["n_decisions"] == expected["n_decisions"]
        assert record["map"]["n_clusters"] == 8
        assert record["map"]["geometry_preserved_by_enrich"] is True
        assert record["map"]["n_points_moved_by_enrichment"] == 0
        assert record["counters"]["counter_status_bearing_rows"] == \
            expected["counter_status_bearing_rows"]
        assert record["timing_s"]["local_map_s"] == expected["local_map_s"]
        assert record["timing_s"]["upstream_retrieval_s"] == \
            expected["upstream_retrieval_s"]
        assert record["page_contract"]["ok"] is True
        assert record["page_contract"]["message"] == "PASS 76 assertions"
        assert record["answer"]["status"] == "ready"
        # The stage-disclosure amendment agrees with the record's own bytes.
        entry = by_run[stamp]
        assert entry["agrees_with_its_own_bytes"] is True
        assert entry["classification"] == "STAGED"
        assert entry["verdict_published"] == "PASS"
        assert entry["effective_verdict"] == "PASS"
        assert entry["n_decisions"] == expected["n_decisions"]


def test_offline_slices_and_preserved_page_contract_artifact():
    for stamp in ("20261030T013520Z", "20261030T014313Z"):
        summary = _json(SLICE_ROOT / stamp / "summary.json")
        bundle = _json(SLICE_ROOT / stamp / "rent-default.bundle.json")
        assert summary["mode"] == "full_loop"
        assert summary["verified"] is True
        assert summary["degraded"] is False
        stats = summary["stats"]
        assert stats["fixture_replay"]["network"] == "none"
        assert stats["fixture_replay_cache_misses"] == 0
        assert stats["n_decisions"] == 100
        assert stats["n_clusters"] == 8
        assert stats["rows_with_canonical_url"] == 100
        assert stats["rows_with_source_link"] == 100
        assert stats["rows_with_xy"] == 100
        assert stats["geometry_preserved_by_enrich"] is True
        assert stats["answer_status"] == "ready"
        assert len(bundle["decisions"]) == 100
    first = _json(SLICE_ROOT / "20261030T013520Z" / "summary.json")
    assert first["page_contract"] is True
    assert first["page_contract_detail"] == "PASS 70 assertions"
    second = _json(SLICE_ROOT / "20261030T014313Z" / "summary.json")
    # Preserved historical artifact: the node verifier did not run when this
    # summary was written (empty detail).  It is not rewritten here; the
    # report records the re-verification against the unchanged bundle bytes.
    assert second["page_contract"] is False
    assert second["page_contract_detail"] == ""
    if shutil.which("node"):
        proc = subprocess.run(
            ["node", "product/verify_query_page.js",
             str(SLICE_ROOT / "20261030T014313Z" / "rent-default.bundle.json")],
            cwd=str(ROOT), capture_output=True, text=True, timeout=120,
            check=False)
        assert proc.returncode == 0, proc.stderr[-2000:]
        assert "PASS 70 assertions" in proc.stdout


def test_content_family_and_smoke_reverified():
    fam = _json(CONTENT_FAMILY)
    assert fam["run_id"] == RUN
    totals = fam["fixed_path_family"]["totals"]
    assert totals["n_bundles"] == 69
    assert totals["n_decisions"] == 6900
    assert totals["n_verified"] == 97
    assert totals["n_verified_defective"] == 0
    assert totals["defect_histogram"] == {
        "D1_empty_evidence": 0,
        "D2_letterhead_zone": 0,
        "D3_markup_residue": 0,
        "D4_language_marker_mismatch": 0,
    }
    assert fam["false_reject_count"] == 0
    assert fam["ordered_work_2_success_rule"]["met"] is True
    assert fam["ordered_work_2_full_success_rule"]["met"] is True
    assert fam["ordered_work_2_full_success_rule"]["packet_v3_bytes_unchanged"] is True
    assert fam["confirmed_set"]["present"] is True
    assert fam["confirmed_set"]["still_verified"] is True
    assert fam["confirmed_set"]["defects"] == []
    smoke = _json(SMOKE)
    assert smoke["run_id"] == RUN
    assert smoke["checks_passed"] == smoke["checks_total"] == 23
    assert all(c["ok"] for c in smoke["checks"])
    assert smoke["checks"][0]["check"] == "health_query_mode"


def test_report_test_and_audit_surface_are_addressable():
    assert REPORT.is_file()
    text = REPORT.read_text(encoding="utf-8")
    assert "CYCLE_40284658455" in text
    assert "DO-NOT-SERVE" in text
    assert "UNADJUDICATED" in text
    assert "2704.0 s" in text
    assert "90 changed files" in text
    for path in (DOSSIER, ROUTE, INTAKE,
                 ROOT / "product" / "tests" / "test_cycle_40990419541.py"):
        assert path.is_file(), path
