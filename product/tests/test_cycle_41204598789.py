"""Cycle 41204598789: bound the audit scope instead of resuming a chain.

Why this cycle exists
---------------------
Run ``41199556067`` again produced a green served slice but its **audit job
expired the 2700 s work quantum** (``Independent audit`` 2704.0 s, exit 78,
``LEX_WORK_QUANTUM_EXPIRED seconds=2700 pid=2543``), so the gate reader and
audit-persist steps were skipped and no ``/audit`` ref exists.  The persisted
team ref carried **10 unaccepted commits and 103 changed files / 74,122
insertions** over the accepted base ``7be4480e``; three audits in a row tried
to re-derive that chain and ran out of time.

This cycle re-bases the snapshot on the accepted base, carries only the current
delta, and publishes explicit scope instruments:

* ``product/audit_chain.py`` — stdlib ``git`` scope manifest (`--verify`);
* ``product/AUDIT_START_HERE.md`` — the bounded audit order;
* a ``41204598789`` self-profile and dossier in ``product/audit_readiness.py``.

What this test locks, fail-closed
---------------------------------
* the public record of 41199556067: team success, audit quantum expiry;
* the committed 13-file delta and UNADJUDICATED status;
* that the snapshot is NOT an accumulated chain (no carried commit, no
  out-of-scope path, no auditor-namespace write, no gate);
* a fresh SERVED vertical slice at this head (query -> bundle -> sourced
  answer -> counter pass -> clickable page);
* the self-dossier, its bounded plan and its dynamic chain-scope check;
* the unchanged accepted pointer and fail-closed posture.

No frozen gate, rubric, threshold or bar is imported, edited or re-tuned here.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EXECUTING_RUN_ID = "41204598789"
RESUMED_RUN_ID = "41199556067"
RESUMED_PREDECESSOR_RUN_ID = "41193662357"
ACCEPTED_RUN_ID = "40284658455"
ACCEPTED_HEAD = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
RESUMED_HEAD = "d137f9c970747ad70dc7c42045ae5998496498da"
RESUMED_PREDECESSOR_HEAD = "a8d2804cda18afc5e676394bb66c8c484063538e"
AUDIT_STEP_S = 2704.0
QUANTUM_S = 2700
CARRIED_COMMITS = 10
CARRIED_FILES = 103
CARRIED_INSERTIONS = 74122

STATE = ROOT / "state" / "product.json"
ORCH = ROOT / "results" / "product" / "orchestration"
RAW = ORCH / f"CYCLE_{RESUMED_RUN_ID}_team_step_raw.json"
ORCH_DOC = ORCH / f"CYCLE_{RESUMED_RUN_ID}_orchestration.json"
DIAG = ORCH / f"CYCLE_{RESUMED_RUN_ID}_resume_diagnosis.json"
SLICE = ROOT / "results" / "product" / "server_slice" / EXECUTING_RUN_ID
SLICE_SUMMARY = SLICE / "summary.json"
DOSSIER = (ROOT / "results" / "product" / "audit_readiness"
           / f"CYCLE_{EXECUTING_RUN_ID}_audit_readiness.json")
CURRENT_REPORT = ROOT / "reports" / "product" / f"CYCLE_{EXECUTING_RUN_ID}.md"
CURRENT_TEST = (ROOT / "product" / "tests"
                / f"test_cycle_{EXECUTING_RUN_ID}.py")
AUDIT_START = ROOT / "product" / "AUDIT_START_HERE.md"
CHAIN_TOOL = ROOT / "product" / "audit_chain.py"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# 1. diagnosis of run 41199556067
# --------------------------------------------------------------------------
def test_public_record_shows_producer_success_and_audit_quantum_expiry():
    assert RAW.is_file()
    doc = _load(RAW)
    jobs = {j["name"]: j for j in doc["jobs"]}
    assert jobs["team"]["conclusion"] == "success"
    assert jobs["audit"]["conclusion"] == "failure"
    assert jobs["integrate"]["conclusion"] == "skipped"
    steps = {s["name"]: s for s in jobs["audit"]["steps"]}
    assert steps["Independent audit"]["conclusion"] == "failure"
    assert steps["Enforce audit scope and read gate"]["conclusion"] == "skipped"
    assert steps["Persist audit snapshot"]["conclusion"] == "skipped"


def test_annotation_pins_the_wrapper_quantum_branch_not_a_provider_cause():
    o = _load(ORCH_DOC)
    assert o["classification"]["class"] == "AUDIT_STEP_FAILED_NO_GATE"
    assert o["job_conclusions"]["team"] == "success"
    assert o["job_conclusions"]["audit"] == "failure"
    assert o["audit_branch_exists"] is False
    d = o["diagnosis"]
    assert d["failing_step"] == "Independent audit"
    assert d["audit_agent_step_duration_s"] == AUDIT_STEP_S
    assert d["exit_code"] == 78
    msgs = " | ".join(a["message"] for a in d["annotations"])
    assert "LEX_WORK_QUANTUM_EXPIRED seconds=2700" in msgs
    assert d["audit_agent_step_duration_s"] >= QUANTUM_S


def test_resume_diagnosis_records_a_committed_delta_and_unadjudicated_run():
    d = _load(DIAG)
    assert d["run_id"] == RESUMED_RUN_ID
    assert d["predecessor_run_id"] == RESUMED_PREDECESSOR_RUN_ID
    delta = d["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["snapshot_head"] == RESUMED_HEAD
    assert delta["predecessor_head"] == RESUMED_PREDECESSOR_HEAD
    assert delta["changed_files"] == 13
    assert "product/audit_readiness.py" in delta["changed_paths_sample"]
    snap = _load(STATE)["cycle_41204598789_operational_resume"]
    assert snap["snapshot_policy"]["carried_chain_commits"] == CARRIED_COMMITS
    assert snap["snapshot_policy"]["carried_chain_changed_files"] == CARRIED_FILES
    assert snap["snapshot_policy"]["carried_chain_insertions"] == CARRIED_INSERTIONS
    assert d["adjudication"]["status"] == "UNADJUDICATED"
    assert d["adjudication"]["accepted"] is False
    assert d["adjudication"]["verdict_written"] is False
    mech = d["orchestration"]["mechanism"]
    assert mech["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert mech["quantum_expired"] is True
    assert mech["exit_code"] == 78
    assert mech["quantum_seconds"] == QUANTUM_S
    assert d["orchestration"]["audit"]["gate_file_written"] is False


# --------------------------------------------------------------------------
# 2. audit scope is one clean delta, not an accumulated chain
# --------------------------------------------------------------------------
@pytest.mark.parametrize("run_id", [EXECUTING_RUN_ID])
def test_chain_scope_is_clean_and_bounded(run_id):
    from product.audit_chain import build
    rec = build(ROOT, run_id, 68)
    assert rec["accepted_base"]["resolved_ref"] == "origin/lab/product"
    assert rec["accepted_base"]["head"] == ACCEPTED_HEAD
    assert rec["accepted_base"]["is_ancestor_of_head"] is True
    # Before the first commit the current delta is the worktree; after it the
    # commit subject carries the run id.  Either is a bounded current delta.
    assert rec["scope_classification"] in (
        "CLEAN_SINGLE_CYCLE", "UNCOMMITTED_BUILD"), rec["scope_classification"]
    assert rec["snapshot"]["carried_unadjudicated_commits"] == 0
    assert rec["overall_status"] == "PASS", rec["failed_checks"]
    assert rec["failed_checks"] == []
    for commit in rec["snapshot"].get("commits", []):
        assert commit["attribution"] == "CURRENT_CYCLE"
    if rec["scope_classification"] == "CLEAN_SINGLE_CYCLE":
        assert rec["snapshot"]["current_cycle_commits"] >= 1
        assert rec["snapshot"]["diff_stat"]["files"] > 0
        assert rec["snapshot"]["diff_stat"]["insertions"] > 0
    else:
        assert rec["worktree_changed_paths"], "uncommitted build has no delta"
    # nothing outside the product write scope, nothing in the auditor namespace
    assert not [
        p for p in rec["snapshot"]["changed_paths"]
        if not (p == "state/product.json" or p.startswith((
            "product/", "tests/product/", "results/product/",
            "reports/product/", "data/product/")))
    ]
    assert not [p for p in rec["snapshot"]["changed_paths"]
                if p.startswith(("results/audit/product/",
                                 "reports/audit/product/"))]


def test_chain_tool_cli_verifies_and_exposes_the_entrypoint():
    assert CHAIN_TOOL.is_file()
    proc = subprocess.run(
        [sys.executable, "product/audit_chain.py", "--verify",
         "--run-id", EXECUTING_RUN_ID],
        cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr[-2000:]
    rec = json.loads(proc.stdout)
    assert rec["schema"] == "product-audit-chain-scope/1"
    assert rec["overall_status"] == "PASS"
    assert rec["scope_classification"] in (
        "CLEAN_SINGLE_CYCLE", "UNCOMMITTED_BUILD")
    assert rec["failed_checks"] == []
    assert "measured_seconds" in rec
    assert rec["measured_seconds"] < 10


def test_audit_start_here_names_the_fast_bounded_order():
    text = AUDIT_START.read_text(encoding="utf-8")
    for needle in ("AUDIT START HERE", EXECUTING_RUN_ID, "audit_chain.py",
                   "audit_readiness.py", "41199556067", "2700", "74,122",
                   "Do not re-audit", "Claim ceiling"):
        assert needle in text, needle


# --------------------------------------------------------------------------
# 3. lane deliverable re-verified at this head
# --------------------------------------------------------------------------
def test_served_vertical_slice_is_green_at_this_head():
    s = _load(SLICE_SUMMARY)
    assert s["verdict"] == "PASS"
    checks = {c["claim"]: c["status"] for c in s["checks"]}
    assert len(checks) == 10 and set(checks.values()) == {"PASS"}
    counts = s["counts"]
    assert counts["n_final"] == 100
    assert counts["rows_with_source_url"] == 100
    assert counts["page_contract_assertions"] >= 70
    first = next(c for c in s["checks"] if "first page" in c["claim"])["observed"]
    assert first["n_decisions"] == 100 and first["n_clusters"] == 8
    assert first["rows_with_xy"] == 100 and first["rows_with_source_url"] == 100
    assert first["validate_bundle"] == []
    answer = next(c for c in s["checks"] if "sourced answer" in c["claim"])[
        "observed"]
    assert answer["answer_status"] == "ready" and answer["n_cited"] >= 1
    assert s["failures"] == []


# --------------------------------------------------------------------------
# 4. self-dossier + bounded plan
# --------------------------------------------------------------------------
def test_self_profile_exists_and_resolves_this_run():
    from product.audit_readiness import PROFILES, select_profile
    assert EXECUTING_RUN_ID in PROFILES
    prof = select_profile(EXECUTING_RUN_ID)
    assert prof["resumed_run_id"] == RESUMED_RUN_ID
    assert prof["predecessor_run_id"] == RESUMED_PREDECESSOR_RUN_ID
    assert prof["mechanism_kind"] == "observed"
    assert prof["delta_kind"] == "committed"
    assert prof["failed_job"] == "audit"
    assert prof["exit_code"] == 78
    assert prof["quantum_seconds"] == QUANTUM_S
    assert prof["changed_files"] == 13
    assert prof["current_report"].as_posix().endswith(
        f"reports/product/CYCLE_{EXECUTING_RUN_ID}.md")
    assert prof["cycle_test"] == (
        f"product/tests/test_cycle_{EXECUTING_RUN_ID}.py")
    assert prof["state_block"] == (
        f"cycle_{EXECUTING_RUN_ID}_operational_resume")


def test_self_dossier_resolves_the_run_it_is_named_for():
    assert DOSSIER.is_file()
    d = _load(DOSSIER)
    assert d["run_id"] == EXECUTING_RUN_ID
    assert d["profile"] == EXECUTING_RUN_ID
    assert d["resumed_run_id"] == RESUMED_RUN_ID
    assert d["predecessor_run_id"] == RESUMED_PREDECESSOR_RUN_ID
    assert d["direction_version"] == 68
    checks = {c["id"]: c for c in d["checks"]}
    for cid in ("runtime_preflight", "state_contract", "chain_scope",
                "posture", "resumed_diagnosis", "claim_artifacts",
                "progressive_smoke", "audit_namespace"):
        assert checks[cid]["status"] == "PASS", (cid, checks[cid])
    # During the bootstrap pass the cycle test / MVP core run is skipped; the
    # committed full dossier records both as PASS.
    for cid in ("cycle_test", "mvp_core_tests"):
        assert checks[cid]["status"] in ("PASS", "SKIP", "SKIPPED")
    assert d["failed_checks"] == []
    entry = d["audit_entry_points"]
    assert entry["start_here"] == "product/AUDIT_START_HERE.md"
    assert entry["current_report"].endswith(f"CYCLE_{EXECUTING_RUN_ID}.md")
    assert f"test_cycle_{EXECUTING_RUN_ID}.py" in entry["current_cycle_test"]
    assert "--verify" in entry["fast_scope_verify_seconds"]
    plan = d["bounded_plan"]
    assert plan["audit_work_quantum_s"] == QUANTUM_S
    assert plan["within_quantum"] is True
    assert plan["measured_seconds_total"] < QUANTUM_S
    assert plan["measured_seconds_margin_s"] > 0
    assert {s["id"] for s in plan["steps"]} == {c["id"] for c in d["checks"]}


# --------------------------------------------------------------------------
# 5. state contract / posture / pointer
# --------------------------------------------------------------------------
def test_state_records_this_run_and_keeps_the_pointer_and_posture():
    st = _load(STATE)
    assert st["direction_version"] == 68
    assert st["cycle_status"] == "COMPLETE"
    # Do not pin the moving head: a later resume may advance it further.
    assert isinstance(st["current_cycle_run_id"], int)
    assert st["current_cycle_run_id"] >= int(EXECUTING_RUN_ID)
    assert st["accepted_run_id"] == f"CYCLE_{ACCEPTED_RUN_ID}"
    assert st["accepted_commit"] == ACCEPTED_HEAD
    assert st["continue_recommended"] is True
    for key in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                "ready_for_owner_session"):
        assert st[key] is False, key
    block = st[f"cycle_{EXECUTING_RUN_ID}_operational_resume"]
    assert block["run_id"] == int(EXECUTING_RUN_ID)
    assert block["direction_version"] == 68
    assert block["resumed_snapshot"]["run_id"] == int(RESUMED_RUN_ID)
    assert block["resumed_snapshot"]["team_ref_head"] == RESUMED_HEAD
    assert block["resumed_snapshot"]["predecessor_run_id"] == int(
        RESUMED_PREDECESSOR_RUN_ID)
    assert block["mechanism_kind"] == "observed"
    assert block["exit_code"] == 78
    assert block["exit_code_meaning"] == "LEX_WORK_QUANTUM_EXPIRED"
    assert block["audit_readiness_repair"]["chain_scope_instrument"] == (
        "product/audit_chain.py")
    assert block["audit_readiness_repair"]["audit_start_here"] == (
        "product/AUDIT_START_HERE.md")
    assert block["lane_deliverable"]["verdict"] == "PASS"
    assert block["lane_deliverable"]["checks"] == "10/10"
    assert block["snapshot_policy"]["chain_excluded_from_audit_scope"] is True
    assert block["adjudication"]["status"] == "UNADJUDICATED"
    assert block["adjudication"]["gate_minted"] is False
    assert block["adjudication"]["audit_namespace_written"] is False
    hist = {str(h["run_id"]): h for h in st["run_history"]}
    entry = hist[RESUMED_RUN_ID]
    assert entry["status"] == (
        "TEAM_JOB_SUCCESS_AUDIT_JOB_QUANTUM_EXPIRED_NO_GATE")
    assert entry["exit_code"] == 78
    assert entry["failed_step"] == "Independent audit"
    assert entry["failed_step_seconds"] == AUDIT_STEP_S
    assert entry["snapshot_commit"] == RESUMED_HEAD
    assert entry["audit_gate"] == "NONE"


def test_state_contract_instrument_still_passes():
    proc = subprocess.run(
        [sys.executable, "product/state_contract.py", "--check",
         "--direction-version", "68", "--json"],
        cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr[-2000:]
    rep = json.loads(proc.stdout)
    assert rep["ok"] is True
    assert rep["workflow_validation"]["ok"] is True
    assert rep["write_scope"]["ok"] is True
    assert rep["write_scope"]["violations"] == []
    assert rep["audit_artifact_ownership"]["producer_wrote_audit_paths"] == []


# --------------------------------------------------------------------------
# 6. no producer-minted gate; ordered work consumed, not re-measured
# --------------------------------------------------------------------------
def test_no_producer_minted_gate_and_no_auditor_namespace_write():
    for rid in (EXECUTING_RUN_ID, RESUMED_RUN_ID,
                RESUMED_PREDECESSOR_RUN_ID):
        assert not (ROOT / "results" / "audit" / "product"
                    / f"CYCLE_{rid}_GATE.json").exists()
        assert not (ROOT / "reports" / "audit" / "product"
                    / f"CYCLE_{rid}.md").exists()


def test_the_lane_deliverable_is_consumed_not_re_measured():
    st = _load(STATE)
    assert st["v68_delivery"]["status"] == "LANDED"
    cf = _load(ROOT / st["v68_delivery"]["reverified_evidence"][5])
    totals = cf["fixed_path_family"]["totals"]
    assert totals["n_bundles"] == 49
    assert totals["n_verified_defective"] == 0
    assert all(v == 0 for v in totals["defect_histogram"].values())
    assert cf["false_reject_count"] == 0
    block = st[f"cycle_{EXECUTING_RUN_ID}_operational_resume"]
    assert block["bundle_bytes_written"] is False
    assert block["frozen_bar_scored"] is False
    hits = [p.name for p in (ROOT / "results" / "product" / "offline_slice")
            .iterdir() if EXECUTING_RUN_ID in p.name]
    assert hits == []


def test_report_exists_and_names_the_same_evidence():
    text = CURRENT_REPORT.read_text(encoding="utf-8")
    for needle in (RESUMED_RUN_ID, RESUMED_PREDECESSOR_RUN_ID,
                   RESUMED_HEAD[:8], "LEX_WORK_QUANTUM_EXPIRED",
                   "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE",
                   "COMMITTED_DELTA", "bounded", "PASS 10/10",
                   ACCEPTED_HEAD[:8], "10 unaccepted commits", "103 changed files",
                   "74,122"):
        assert needle in text, needle
