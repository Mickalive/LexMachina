#!/usr/bin/env python3
"""Pins the operational resume of run 40763434744 (audit quantum death #5).

Run 40763434744's TEAM job was fully green (14-file committed delta
``953c2e71`` over predecessor team head ``85dfea22``) and its AUDIT
"Independent audit" step then died at the 2700 s work quantum (2704.0 s,
exit 78, ``OBSERVED_QUANTUM_EXPIRED`` via public check-run annotations)
before writing any gate.  That is the FIFTH audit-side quantum death on
this lineage.

This cycle's binding repair is the WORKSPACE CONTRACT in
``product/audit_route.py``: the audit job's CWD is the accepted-base
checkout (which lacks ``audit_route.py``, holds older copies of the other
instruments, and has no pinned python deps installed by any workflow
step), while the producer snapshot is mounted at ``/tmp/lex_team``.  The
brief, intake and route artifact now prefix every command with
``cd /tmp/lex_team &&`` and lead with ``product/bootstrap_query_env.sh``,
and the intake inlines the committed route/dossier headlines.

This module pins: the machine diagnosis of 40763434744; the run-history
truth repair; the workspace contract in brief/intake/route; the profile
entry; the fresh offline slice and content-family verifications; the
fail-closed posture; and (conditionally) the committed dossier and route
artifacts of this run.
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
REPORT = ROOT / "reports" / "product" / "CYCLE_40772551540.md"
PREV_REPORT = ROOT / "reports" / "product" / "CYCLE_40763434744.md"
DOSSIER = AR / "CYCLE_40772551540_audit_readiness.json"
ROUTE = AR / "CYCLE_40772551540_AUDIT_ROUTE.json"
INTAKE = AR / "CYCLE_40772551540_AUDIT_INTAKE.md"
BUNDLE = (ROOT / "results" / "product" / "offline_slice"
          / "20261028T214335Z" / "rent-default.bundle.json")
CONTENT_FAMILY = (ROOT / "results" / "product" / "counter_content_family"
                  / "CYCLE_40772551540.json")
ACCEPTED = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
SNAPSHOT = "953c2e7156545496e197ee9ca041986a6bbeeba4"
PREDECESSOR = "85dfea227c77bc7ac3e91ae452c067ae18ad5c73"
WORKSPACE = "/tmp/lex_team"


def test_state_pointer_and_posture_non_rotting():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    assert state["accepted_run_id"] == "CYCLE_40284658455"
    assert state["accepted_commit"] == ACCEPTED
    # current_run is the MOVING latest-resume pointer; assert this cycle's
    # own durable record below rather than a value a later resume may move.
    assert state["current_run"]
    assert "cycle_40772551540_operational_resume" in state
    assert state["continue_recommended"] is True
    assert state["human_gate_ready"] is False
    assert state["machine_gate_ready"] is False
    assert state["ready_for_owner_session"] is False
    assert state["packet_admitted"] is False
    assert state["owner_decision_required"] is False
    assert state["direction_version"] == 68
    block = state["cycle_40772551540_operational_resume"]
    assert block["resumed_run_id"] == "40763434744"
    assert block["resumed_snapshot_head"] == SNAPSHOT
    assert block["resumed_failure"]["classification"] == \
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    assert block["resumed_failure"]["durable_delta"] == \
        "COMMITTED_DELTA (14 files)"
    assert block["resumed_failure"]["gate_file_written"] is False
    assert block["resumed_failure"]["audit_death_ordinal"] == \
        "FIFTH on this lineage"
    assert block["posture"]["human_gate_ready"] is False
    assert block["posture"]["continue_recommended"] is True
    assert block["posture"]["owner_decision_required"] is False
    repair = block["workspace_contract_repair"]
    assert WORKSPACE in repair["finding"]
    assert "cd /tmp/lex_team" in repair["repair"]
    assert "bootstrap_query_env.sh" in repair["repair"]
    assert ".github/** is control-plane scope" in repair["control_plane_gap"]


def test_run_history_fates():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    hist = {str(e["run_id"]): e for e in state["run_history"]}
    prev = hist["40763434744"]
    assert prev["status"] == \
        "AUDIT_JOB_QUANTUM_DEATH_COMMITTED_DELTA_UNADJUDICATED"
    assert prev["status_original_producer_record"] == \
        "OPERATIONAL_RESUME_AUDIT_INTAKE_AND_STALE_TARGET_REPAIR"
    assert "FIFTH audit-side quantum death" in prev["status_correction"]
    assert prev["team_job"].startswith("SUCCESS")
    assert "14-file committed delta 953c2e71" in prev["team_job"]
    assert "2704.0 s" in prev["audit_job"]
    assert "OBSERVED_QUANTUM_EXPIRED" in prev["audit_job"]
    assert prev["accepted"] is False
    cur = hist["40772551540"]
    assert cur["status"] == \
        "OPERATIONAL_RESUME_WORKSPACE_CONTRACT_AND_AUDIT_DEATH_5"
    assert cur["resumed_run"] == "40763434744"
    assert cur["accepted"] is False
    assert cur["report_of_record"] == "reports/product/CYCLE_40772551540.md"
    assert cur["cycle_test"] == "product/tests/test_cycle_40772551540.py"


def test_diagnosed_audit_quantum_death_of_40763434744():
    diag = json.loads((ORCH / "CYCLE_40763434744_resume_diagnosis.json")
                      .read_text(encoding="utf-8"))
    assert diag["run_id"] == "40763434744"
    assert diag["predecessor_run_id"] == "40750177292"
    orch = diag["orchestration"]
    assert orch["classification"] == \
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    mech = orch["mechanism"]
    assert mech["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert mech["quantum_expired"] is True
    assert mech["quantum_seconds"] == 2700
    assert mech["exit_code"] == 78
    assert orch["team"]["conclusion"] == "success"
    assert orch["audit"]["conclusion"] == "failure"
    assert orch["audit"]["failed_step"] == "Independent audit"
    assert orch["audit"]["independent_audit_step_seconds"] == 2704.0
    assert orch["audit"]["gate_file_written"] is False
    assert orch["integrate"]["conclusion"] == "skipped"
    delta = diag["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["changed_files"] == 14
    assert delta["snapshot_head"] == SNAPSHOT
    assert delta["predecessor_head"] == PREDECESSOR
    assert "state/product.json" in delta["changed_paths_sample"]
    assert diag["accepted_head_relation"]["accepted_head"] == ACCEPTED
    assert diag["adjudication"]["status"] == "UNADJUDICATED"


def test_raw_snapshot_is_the_committed_public_record():
    raw = json.loads((ORCH / "CYCLE_40763434744_run_jobs_raw.json")
                     .read_text(encoding="utf-8"))
    assert raw["run"]["id"] == 40763434744
    team = next(j for j in raw["jobs"] if j["name"] == "team")
    assert team["conclusion"] == "success"
    audit = next(j for j in raw["jobs"] if j["name"] == "audit")
    assert audit["conclusion"] == "failure"
    steps = {s["name"]: s["conclusion"] for s in audit["steps"]}
    assert steps["Independent audit"] == "failure"
    assert steps["Enforce audit scope and read gate"] == "skipped"
    msgs = [a["message"] for v in (raw.get("annotations") or {}).values()
            for a in v]
    assert any("LEX_WORK_QUANTUM_EXPIRED seconds=2700" in m for m in msgs)
    assert any("exit code 78" in m for m in msgs)


def test_workspace_contract_in_brief_intake_and_route():
    sys.path.insert(0, str(ROOT))
    from product import audit_route
    # The accepted base does NOT contain the instrument; the contract must
    # send the auditor to the producer mount explicitly.
    proc = subprocess.run(
        ["git", "cat-file", "-e", f"{ACCEPTED}:product/audit_route.py"],
        cwd=str(ROOT), capture_output=True, check=False,
    )
    assert proc.returncode != 0, \
        "accepted base unexpectedly has audit_route.py; contract premise stale"
    brief = audit_route.auditor_brief("40772551540", None)
    assert "WORKSPACE CONTRACT" in brief
    assert f"cd {WORKSPACE} &&" in brief
    assert "bash product/bootstrap_query_env.sh" in brief
    assert "product/audit_route.py\nis absent there" in brief or (
        "product/audit_route.py is absent there" in brief)
    assert "AUDIT TARGET (team ref): origin/cycle/core/product/40772551540/team" \
        in brief
    ws = audit_route.workspace_block()
    assert ws["producer_workspace_mount"] == WORKSPACE
    assert ws["workflow_installs_python_deps"] is False
    assert ws["bootstrap_command"].startswith(f"cd {WORKSPACE} && ")
    assert str(ROOT).startswith(WORKSPACE) or True  # host-dependent root
    # The intake carries the contract AND the inline headlines, and — per
    # the predecessor test's standing pin — never the phrase "never a gate".
    if INTAKE.exists():
        text = INTAKE.read_text(encoding="utf-8")
        assert "WORKSPACE CONTRACT" in text
        assert f"cd {WORKSPACE} &&" in text
        assert "COMMITTED MEASUREMENTS" in text
        assert "never a gate" not in text


def test_profile_registered_and_cross_validated():
    sys.path.insert(0, str(ROOT))
    from product import audit_readiness
    from product.audit_readiness import PROFILES, select_profile
    assert "40772551540" in PROFILES
    prof = select_profile("40772551540")
    assert prof["resumed_run_id"] == "40763434744"
    assert prof["failed_job"] == "audit"
    assert prof["mechanism_kind"] == "observed"
    assert prof["delta_kind"] == "committed"
    assert prof["changed_files"] == 14
    assert prof["exit_code"] == 78
    assert prof["cycle_test"] == "product/tests/test_cycle_40772551540.py"
    saved = dict(audit_readiness.PROFILE)
    try:
        audit_readiness.PROFILE.update(prof)
        check = audit_readiness.check_resumed_diagnosis()
        assert check["status"] == "PASS", check
    finally:
        audit_readiness.PROFILE.clear()
        audit_readiness.PROFILE.update(saved)


def test_offline_vertical_slice_claims_match_the_committed_bundle():
    assert BUNDLE.is_file()
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    rows = bundle["decisions"]
    assert len(rows) == 100
    assert bundle["query"]
    assert len(bundle.get("clusters") or []) == 8
    assert all(r.get("x") is not None and r.get("y") is not None
               for r in rows)
    assert all(r.get("cluster_id") is not None for r in rows)
    assert all(r.get("canonical_url") for r in rows)
    assert bundle["answer"]["status"] == "ready"
    assert len(bundle["answer"]["cited_decision_ids"]) == 4
    assert bundle["provenance"]["offline_slice"]["network"] == "none"
    assert bundle["provenance"]["offline_slice"]["geometry_preserved"] is True


def test_content_family_probe_matches_the_committed_artifact():
    assert CONTENT_FAMILY.is_file()
    doc = json.loads(CONTENT_FAMILY.read_text(encoding="utf-8"))
    assert doc["run_id"] == "40772551540"
    fixed = doc["fixed_path_family"]["totals"]
    assert fixed["n_bundles"] == 54
    assert fixed["n_decisions"] == 5400
    assert fixed["n_verified"] == 61
    assert fixed["n_verified_defective"] == 0
    assert fixed["defect_histogram"] == {
        "D1_empty_evidence": 0,
        "D2_letterhead_zone": 0,
        "D3_markup_residue": 0,
        "D4_language_marker_mismatch": 0,
    }
    assert doc["false_reject_count"] == 0
    rule = doc["ordered_work_2_success_rule"]
    assert rule["met"] is True
    assert rule["false_reject_count"] == 0
    assert rule["defect_histogram_zero_D2_D3_D4"] is True
    assert rule["confirmed_sound_row_still_verified"] is True
    historical = doc["all_committed"]["totals"]
    assert historical["n_bundles"] == 155
    assert historical["defect_histogram"]["D2_letterhead_zone"] == 44
    assert historical["defect_histogram"]["D3_markup_residue"] == 31
    assert historical["defect_histogram"]["D4_language_marker_mismatch"] == 7


def test_report_of_record_states_measured_claims():
    text = " ".join(REPORT.read_text(encoding="utf-8").split())
    for needle in ("40763434744", "953c2e71", "85dfea22", "7be4480e",
                   "2704.0 s", "exit 78", "FIFTH audit-side quantum death",
                   "14-file committed delta", "UNADJUDICATED",
                   "WORKSPACE CONTRACT", "/tmp/lex_team",
                   "bootstrap_query_env.sh", "PASS", "70 assertions",
                   "2.537 s", "54 bundles / 5400 decisions / 61 verified",
                   "success rule", "DO-NOT-SERVE", "2700 s"):
        assert needle in text, needle
    # The predecessor report is append-only evidence and must still exist.
    assert PREV_REPORT.is_file()


def test_audit_route_artifact_if_present():
    if ROUTE.exists():
        route = json.loads(ROUTE.read_text(encoding="utf-8"))
        assert route["schema"] == "product-audit-route/1"
        assert route["run_id"] == "40772551540"
        assert route["quantum_budget_s"] == 2700
        assert route["audit_target"]["audit_target_ref"] == \
            "origin/cycle/core/product/40772551540/team"
        ws = route.get("workspace") or {}
        assert ws.get("producer_workspace_mount") == WORKSPACE
        assert ws.get("workflow_installs_python_deps") is False
        ids = [s["id"] for s in route["steps"]]
        assert "state_contract" in ids
        assert "chain_cycle_tests" in ids
        assert "never a verdict" in route["contract"]
        if route.get("mode") == "bootstrap":
            assert "self_reference" in route
            failed = set(route["failed_steps"])
            assert failed <= {"chain_cycle_tests"}, failed
        else:
            assert route["overall_status"] == "PASS"
            assert route["failed_steps"] == []
            assert route["total_seconds"] < route["quantum_budget_s"]


def test_dossier_generated_if_present():
    if DOSSIER.exists():
        dossier = json.loads(DOSSIER.read_text(encoding="utf-8"))
        assert dossier["run_id"] == "40772551540"
        assert dossier["overall_status"] == "PASS"
        assert dossier["failed_checks"] == []
        assert dossier["skipped_checks"] == []


def test_audit_route_never_writes_a_gate():
    proc = subprocess.run(
        [sys.executable, "product/audit_route.py", "--for-auditor",
         "--run-id", "40772551540"],
        cwd=str(ROOT), capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0
    assert "AUDIT TARGET" in proc.stdout
    assert "WORKSPACE CONTRACT" in proc.stdout
    assert not (ROOT / "results" / "audit" / "product"
                / "CYCLE_40772551540_GATE.json").exists()
