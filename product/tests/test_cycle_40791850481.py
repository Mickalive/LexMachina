#!/usr/bin/env python3
"""Pins the operational resume of run 40791850481.

Run 40791850481 was repair round 0 of the unadjudicated cycle 40783679367.
Its TEAM job was fully green and its own delta over the repair base
``c73d9d84`` is SUBSTANTIVE (17 files carrying the completed
40783679367-cycle deliverable; the 25-file CACHE_REFRESH belonged to the
prior run).  Its AUDIT "Independent audit" step then died at the 2700 s work
quantum (2705.0 s, exit 78, ``OBSERVED_QUANTUM_EXPIRED`` via public
check-run annotations) before writing any gate.

The validation defect this cycle repairs is run-id addressability: the
snapshot labelled every artifact with the repaired cycle id ``40783679367``
while the workflow refs are keyed by ``40791850481``, so ``audit_route.py
--run-id 40791850481`` named a report and a dossier that did not exist.  This
module pins the diagnosis, the repair and the new self-label guard.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state" / "product.json"
ORCH = ROOT / "results" / "product" / "orchestration"
AR = ROOT / "results" / "product" / "audit_readiness"
REPORT = ROOT / "reports" / "product" / "CYCLE_40791850481.md"
PREV_REPORT = ROOT / "reports" / "product" / "CYCLE_40783679367.md"
DIAG = ORCH / "CYCLE_40791850481_resume_diagnosis.json"
RAW = ORCH / "CYCLE_40791850481_run_jobs_raw.json"
DELTA = ORCH / "CYCLE_40791850481_delta_substance.json"
DOSSIER = AR / "CYCLE_40791850481_audit_readiness.json"
ROUTE = AR / "CYCLE_40791850481_AUDIT_ROUTE.json"
INTAKE = AR / "CYCLE_40791850481_AUDIT_INTAKE.md"
CONTENT_FAMILY = (ROOT / "results" / "product" / "counter_content_family"
                  / "CYCLE_40791850481.json")
RENT = (ROOT / "results" / "product" / "offline_slice"
        / "20261029T012410Z" / "rent-default.bundle.json")
BIZ = (ROOT / "results" / "product" / "offline_slice"
       / "20261029T012416Z" / "business-judgment-rule.bundle.json")
ACCEPTED = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
SNAPSHOT = "7af0eb1bdcff8a7234e935db8035436466450b5c"
BASE = "c73d9d848018e56d2d2ec3a5d53f9791688ae376"
RUN = "40791850481"


def test_state_pointer_and_posture_non_rotting():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    assert state["accepted_run_id"] == "CYCLE_40284658455"
    assert state["accepted_commit"] == ACCEPTED
    assert state["current_run"]
    assert state["cycle_40791850481_operational_resume"]
    assert state["current_cycle_run_id"] == RUN
    assert state["current_run"] == RUN
    assert state["continue_recommended"] is True
    assert state["human_gate_ready"] is False
    assert state["machine_gate_ready"] is False
    assert state["ready_for_owner_session"] is False
    assert state["packet_admitted"] is False
    assert state["owner_decision_required"] is False
    assert state["direction_version"] == 68
    block = state["cycle_40791850481_operational_resume"]
    assert block["resumed_run_id"] == "40783679367"
    assert block["diagnosis_of_resumed"] == \
        "results/product/orchestration/CYCLE_40791850481_resume_diagnosis.json"
    assert block["resumed_failure"]["classification"] == \
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    assert block["resumed_failure"]["gate_file_written"] is False
    assert block["resumed_failure"]["adjudication"] == "UNADJUDICATED"
    assert block["validation_defect"]["classification"] == \
        "REPAIR_DISPATCH_SNAPSHOT_NOT_ADDRESSABLE_BY_OWN_RUN_ID"
    assert block["validation_defect"]["product_defect"] is False
    assert block["snapshot_audit_readiness"]["state_advanced"] is True
    assert state["audit_route"]["artifact"] == \
        "results/product/audit_readiness/CYCLE_40791850481_AUDIT_ROUTE.json"
    # The repaired cycle's append-only block must survive.
    assert state["cycle_40783679367_operational_resume"]


def test_run_history_entry_and_append_only_predecessor():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    hist = {str(e["run_id"]): e for e in state["run_history"]}
    cur = hist[RUN]
    assert cur["status"] == \
        "AUDIT_JOB_QUANTUM_DEATH_SUBSTANTIVE_DELTA_LABEL_REPAIRED_UNADJUDICATED"
    assert cur["resumed_run"] == "40783679367"
    assert cur["accepted"] is False
    assert cur["accepted_commit"] == ACCEPTED
    assert cur["report_of_record"] == \
        "reports/product/CYCLE_40791850481.md"
    assert cur["cycle_test"] == \
        "product/tests/test_cycle_40791850481.py"
    assert cur["team_job"].startswith("SUCCESS")
    assert "17-file" in cur["team_job"]
    assert "2705.0 s" in cur["audit_job"]
    assert "OBSERVED_QUANTUM_EXPIRED" in cur["audit_job"]
    assert "40783679367" in hist


def test_diagnosed_audit_quantum_death():
    diag = json.loads(DIAG.read_text(encoding="utf-8"))
    assert diag["run_id"] == RUN
    assert diag["predecessor_run_id"] == "40783679367"
    orch = diag["orchestration"]
    assert orch["classification"] == \
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    mech = orch["mechanism"]
    assert mech["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert mech["quantum_expired"] is True
    assert mech["quantum_seconds"] == 2700
    assert mech["exit_code"] == 78
    assert mech["logs_available"] is False
    assert mech["logs_endpoint_status"] == 403
    assert orch["team"]["conclusion"] == "success"
    assert orch["team"]["producer_state_validation_step_conclusion"] == \
        "success"
    assert orch["team"]["write_scope_step_conclusion"] == "success"
    assert orch["audit"]["failed_step"] == "Independent audit"
    assert orch["audit"]["independent_audit_step_seconds"] == 2705.0
    assert orch["audit"]["gate_file_written"] is False
    assert orch["integrate"]["conclusion"] == "skipped"
    delta = diag["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["delta_substance"] == "SUBSTANTIVE"
    assert delta["product_work"] is True
    assert delta["changed_files"] == 17
    assert delta["snapshot_head"] == SNAPSHOT
    assert delta["base_head"] == BASE
    assert len(delta["changed_paths_sample"]) == 17
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["snapshot_self_label"]["status"] == \
        "MISMATCH_REPAIRED_THIS_CYCLE"


def test_raw_snapshot_is_the_committed_public_record():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    assert raw["run"]["id"] == int(RUN)
    team = next(j for j in raw["jobs"] if j["name"] == "team")
    assert team["conclusion"] == "success"
    audit = next(j for j in raw["jobs"] if j["name"] == "audit")
    assert audit["conclusion"] == "failure"
    steps = {s["name"]: s["conclusion"] for s in audit["steps"]}
    assert steps["Independent audit"] == "failure"
    assert steps["Enforce audit scope and read gate"] == "skipped"
    assert steps["Persist audit snapshot"] == "skipped"
    msgs = [a["message"] for v in (raw.get("annotations") or {}).values()
            for a in v]
    assert any("LEX_WORK_QUANTUM_EXPIRED seconds=2700" in m for m in msgs)
    assert any("exit code 78" in m for m in msgs)


def test_delta_substance_artifact_is_this_runs_own_delta():
    doc = json.loads(DELTA.read_text(encoding="utf-8"))
    assert doc["run_id"] == RUN
    assert doc["head"]["sha"] == SNAPSHOT
    assert doc["base"]["sha"] == BASE
    assert doc["changed_files"] == 17
    assert doc["delta_substance"] == "SUBSTANTIVE"
    assert doc["product_work"] is True
    assert doc["cache_timestamp_only_count"] == 0
    assert doc["cache_content_count"] == 0
    assert len(doc["substantive_files"]) == 17


def test_profile_registered_and_cross_validated():
    sys.path.insert(0, str(ROOT))
    from product.audit_readiness import PROFILES, select_profile
    assert RUN in PROFILES
    prof = select_profile(RUN)
    assert prof["resumed_run_id"] == RUN
    assert prof["predecessor_run_id"] == "40783679367"
    assert prof["failed_job"] == "audit"
    assert prof["mechanism_kind"] == "observed"
    assert prof["delta_kind"] == "committed"
    assert prof["changed_files"] == 17
    assert prof["exit_code"] == 78
    assert prof["quantum_seconds"] == 2700
    assert prof["state_block"] == "cycle_40791850481_operational_resume"


def test_self_label_guard_blocks_an_unaddressable_run():
    sys.path.insert(0, str(ROOT))
    from product.audit_route import audit_target, auditor_brief
    aligned = audit_target(RUN)
    assert aligned["cycle_block_present"] is True
    assert "report" not in aligned["missing_artifacts"]
    assert "diagnosis" not in aligned["missing_artifacts"]
    # The route artifact cannot exist during its own first generation and the
    # dossier is generated separately; once both are committed the snapshot
    # must be fully aligned. This keeps the first-generation fixpoint honest
    # without weakening the committed-state assertion.
    if ROUTE.exists() and DOSSIER.exists():
        assert aligned["self_label_status"] == "ALIGNED"
        assert aligned["missing_artifacts"] == []
    unknown = audit_target("99999999999")
    assert unknown["self_label_status"] != "ALIGNED"
    assert unknown["cycle_block_present"] is False
    assert "report" in unknown["missing_artifacts"]
    brief = auditor_brief("99999999999", None)
    assert "SNAPSHOT SELF-LABEL GUARD" in brief
    assert "ABSENT" in brief
    assert aligned["artifact_paths"]["report"] == \
        "reports/product/CYCLE_40791850481.md"


def test_report_and_claims_match_the_committed_artifacts():
    assert REPORT.is_file()
    text = " ".join(REPORT.read_text(encoding="utf-8").split())
    for needle in (RUN, "40783679367", SNAPSHOT[:8], BASE[:8], ACCEPTED[:8],
                   "2705.0 s", "exit code 78", "LEX_WORK_QUANTUM_EXPIRED",
                   "pid=2495", "17 files", "SUBSTANTIVE", "UNADJUDICATED",
                   "self_label_status", "ABSENT", "PASS",
                   "2.512 s", "70 assertions", "6.369 s", "71 assertions",
                   "58 bundles / 5800 decisions / 67 verified",
                   "0 defective", "false rejects on the confirmed set", "DO-NOT-SERVE"):
        assert needle in text, needle
    assert PREV_REPORT.is_file()


def test_content_family_matches_committed_artifact():
    assert CONTENT_FAMILY.is_file()
    doc = json.loads(CONTENT_FAMILY.read_text(encoding="utf-8"))
    assert doc["run_id"] == RUN
    assert doc["direction_version"] == 68
    fixed = doc["fixed_path_family"]["totals"]
    assert fixed["n_bundles"] == 58
    assert fixed["n_decisions"] == 5800
    assert fixed["n_verified"] == 67
    assert fixed["n_verified_defective"] == 0
    assert fixed["defect_histogram"] == {
        "D1_empty_evidence": 0,
        "D2_letterhead_zone": 0,
        "D3_markup_residue": 0,
        "D4_language_marker_mismatch": 0,
    }
    assert doc["false_reject_count"] == 0
    assert doc["ordered_work_2_success_rule"]["met"] is True


def test_fresh_offline_slices_are_the_committed_bytes():
    for path, cited, assertions in ((RENT, 4, 70), (BIZ, 3, 71)):
        assert path.is_file()
        bundle = json.loads(path.read_text(encoding="utf-8"))
        summary = json.loads(path.with_name("summary.json").read_text(
            encoding="utf-8"))
        assert len(bundle["decisions"]) == 100
        assert len(bundle.get("clusters") or []) == 8
        assert bundle["answer"]["status"] == "ready"
        assert len(bundle["answer"]["cited_decision_ids"]) == cited
        assert bundle["provenance"]["offline_slice"]["network"] == "none"
        assert bundle["provenance"]["offline_slice"][
            "geometry_preserved"] is True
        assert summary["page_contract"] is True
        assert summary["page_contract_detail"] == f"PASS {assertions} assertions"
        assert summary["stats"]["fixture_replay"]["network"] == "none"


def test_audit_route_artifact_if_present():
    if ROUTE.exists():
        route = json.loads(ROUTE.read_text(encoding="utf-8"))
        assert route["schema"] == "product-audit-route/1"
        assert route["run_id"] == RUN
        assert route["quantum_budget_s"] == 2700
        assert route["audit_target"]["audit_target_ref"] == \
            f"origin/cycle/core/product/{RUN}/team"
        label = route["snapshot_self_label"]["status"]
        assert label in ("ALIGNED", "ALIGNED_AFTER_WRITE")
        if label == "ALIGNED_AFTER_WRITE":
            assert route["snapshot_self_label"]["missing_artifacts"] == \
                ["route"]
        ids = [s["id"] for s in route["steps"]]
        assert "snapshot_self_label" in ids
        assert "state_contract" in ids
        assert "chain_cycle_tests" in ids
        assert "never a verdict" in route["contract"]
        if route.get("mode") != "bootstrap":
            assert route["overall_status"] == "PASS"
            assert route["failed_steps"] == []
            assert route["total_seconds"] < route["quantum_budget_s"]


def test_dossier_generated_if_present():
    if DOSSIER.exists():
        dossier = json.loads(DOSSIER.read_text(encoding="utf-8"))
        assert dossier["run_id"] == RUN
        assert dossier["overall_status"] == "PASS"
        assert dossier["failed_checks"] == []
        assert dossier["skipped_checks"] == []


def test_audit_brief_never_mints_a_gate():
    proc = subprocess.run(
        [sys.executable, "product/audit_route.py", "--for-auditor",
         "--run-id", RUN],
        cwd=str(ROOT), capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0
    assert "AUDIT TARGET" in proc.stdout
    assert "PRESENT" in proc.stdout
    assert not (ROOT / "results" / "audit" / "product"
                / f"CYCLE_{RUN}_GATE.json").exists()
    assert INTAKE.is_file()
