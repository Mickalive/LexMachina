"""Cycle 43566223678: operational resume of producer snapshot 43561447112.

Locks the resume diagnosis, the two validation repairs and the lane
deliverable. It is intentionally a bounded, offline test: it reads committed
artifacts and never starts a server, fetches a ref or re-runs retrieval.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

EXECUTING_RUN_ID = "43566223678"
RESUMED_RUN_ID = "43561447112"
PREDECESSOR_RUN_ID = "43561269343"
SNAPSHOT_HEAD = "c627010182a9769478b3c4daaa0b055c567b176d"
PREDECESSOR_HEAD = "e82aabdecbcf8c2a00652501cb351baf9ebc367a"

ORCH = ROOT / "results" / "product" / "orchestration"
RAW = ORCH / f"CYCLE_{RESUMED_RUN_ID}_run_jobs_raw.json"
DIAG = ORCH / f"CYCLE_{RESUMED_RUN_ID}_resume_diagnosis.json"
LOGS = ORCH / f"CYCLE_{RESUMED_RUN_ID}_job_logs"
STATE = ROOT / "state" / "product.json"
FAMILY = (ROOT / "results" / "product" / "counter_content_family"
          / f"CYCLE_{EXECUTING_RUN_ID}.json")
SLICE = ROOT / "results" / "product" / "offline_slice" / f"{EXECUTING_RUN_ID}_verify"
SMOKE = (ROOT / "results" / "product" / "progressive_smoke"
         / f"CYCLE_{EXECUTING_RUN_ID}_progressive_smoke.json")
MANIFEST = (ROOT / "results" / "product"
            / f"CYCLE_{EXECUTING_RUN_ID}_cache_manifest.json")
REPORT = ROOT / "reports" / "product" / f"CYCLE_{EXECUTING_RUN_ID}.md"
GATE = ROOT / "results" / "audit" / "product" / "CYCLE_40284658455_GATE.json"

ACCEPTED_REF = "origin/lab/product"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True,
                          text=True, check=True).stdout.strip()


def test_resume_diagnosis_is_observed_committed_and_unadjudicated():
    diag = _load(DIAG)
    assert diag["run_id"] == RESUMED_RUN_ID
    assert diag["predecessor_run_id"] == PREDECESSOR_RUN_ID
    orch = diag["orchestration"]
    assert orch["classification"] == "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    mechanism = orch["mechanism"]
    assert mechanism["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert mechanism["quantum_expired"] is True
    assert mechanism["quantum_seconds"] == 2700
    assert mechanism["exit_code"] == 78
    assert orch["audit"]["gate_file_written"] is False
    assert orch["audit"]["failed_step"] == "Independent audit"

    delta = diag["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["snapshot_head"] == SNAPSHOT_HEAD
    assert delta["predecessor_head"] == PREDECESSOR_HEAD
    assert delta["changed_files"] == 28
    assert delta["changed_paths_sample"]
    assert all("results/product/query_cache/" in p
               for p in delta["changed_paths_sample"])

    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["accepted"] is False
    assert diag["adjudication"]["audit"]["gate_file_present"] is False


def test_public_run_evidence_and_audit_log_are_committed():
    raw = _load(RAW)
    assert raw["run"]["id"] == int(RESUMED_RUN_ID)
    assert raw["run"]["conclusion"] == "failure"
    jobs = {j["name"]: j for j in raw["jobs"]}
    assert jobs["team"]["conclusion"] == "success"
    assert jobs["audit"]["conclusion"] == "failure"
    assert (LOGS / "MANIFEST.json").is_file()
    audit_log = (LOGS / "audit.log").read_text(encoding="utf-8")
    assert "LEX_WORK_QUANTUM_EXPIRED seconds=2700" in audit_log
    assert "exit code 78" in audit_log
    manifest = _load(LOGS / "MANIFEST.json")
    audit = next(e for e in manifest["logs"] if e["job_name"] == "audit")
    assert audit["http_status"] == 200


def test_state_records_the_resume_and_removes_dangling_pointers():
    state = _load(STATE)
    assert str(state["current_cycle_run_id"]) == EXECUTING_RUN_ID
    block = state[f"cycle_{EXECUTING_RUN_ID}_operational_resume"]
    assert str(block["run_id"]) == EXECUTING_RUN_ID
    assert block["resumed_snapshot"]["run_id"] == int(RESUMED_RUN_ID)
    assert block["resumed_snapshot"]["team_head"] == SNAPSHOT_HEAD
    assert block["resumed_snapshot"]["predecessor_head"] == PREDECESSOR_HEAD
    assert block["orchestration_failure_diagnosis"]["classification"] == (
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE")
    assert block["orchestration_failure_diagnosis"]["mechanism"] == (
        "OBSERVED_QUANTUM_EXPIRED")

    for name, rel in block["artifacts"].items():
        if name == "audit_readiness":
            # Written by the dossier run that executes this test; it need not
            # exist yet, but if it does it must be a real file.
            if (ROOT / rel).exists():
                assert (ROOT / rel).is_file(), name
            continue
        if name in ("job_logs_dir", "slice") or rel.endswith("/"):
            assert (ROOT / rel).is_dir(), name
        else:
            assert (ROOT / rel).is_file(), name

    # The historical 43550578572 block must not present a missing path as an
    # artifact. Its report/dossier were never written by that failed run.
    old = state["cycle_43550578572_operational_resume"]["artifacts"]
    assert old["report"] is None
    assert old["audit_readiness"] is None
    assert "NOT_COMMITTED" in old["report_status"]
    assert "NOT_COMMITTED" in old["audit_readiness_status"]

    # The unsupported 43555660841 "audit readiness overall_status PASS" prose
    # is not repeated by this cycle.
    recommendation = state["next_recommendation"]
    assert EXECUTING_RUN_ID in recommendation
    assert "Snapshot audit-ready: PASS" not in recommendation


def test_cache_snapshot_in_force_is_this_run_and_intact():
    sys.path.insert(0, str(ROOT / "product"))
    import cache_rewrite_attribution as cra

    newest = cra.newest_snapshot()
    assert newest is not None
    assert newest.name == MANIFEST.name
    payload = _load(newest)
    entries = {str(e["path"]): str(e["sha256"])
               for e in payload.get("entries") or []}
    tree = cra.current_tree_integrity(entries)
    assert tree["intact"], tree
    assert tree["n_entries"] == 1066

    # Historical snapshots are preserved, never rewritten.
    assert (ROOT / "results" / "product"
            / "CYCLE_43389158171_cache_manifest.json").is_file()
    assert (ROOT / "results" / "product"
            / "CYCLE_38759730609_cache_manifest.json").is_file()


def test_content_family_counts_and_d2_flip():
    family = _load(FAMILY)
    totals = family["fixed_path_family"]["totals"]
    assert totals["n_bundles"] == 49
    assert totals["n_decisions"] == 4900
    assert totals["n_verified"] == 55
    assert totals["n_verified_defective"] == 0
    assert all(v == 0 for v in totals["defect_histogram"].values())
    assert family["false_reject_count"] == 0
    assert family["confirmed_set"]["still_verified"] is True
    assert family["ordered_work_2_success_rule"]["met"] is True
    assert family["ordered_work_2_full_success_rule"]["met"] is True

    before = _load(ROOT / "results" / "product" / "offline_slice"
                   / "20261024T142517Z" / "rent-default.bundle.json")
    after = _load(ROOT / "results" / "product" / "offline_slice"
                  / "20261025T070356Z" / "rent-default.bundle.json")
    decision = "gr_gerichte_ERZ 2010 25"
    b = next(r for r in before["decisions"] if r["decision_id"] == decision)
    a = next(r for r in after["decisions"] if r["decision_id"] == decision)
    assert b["counter_evidence_verified"] is True
    assert a["counter_evidence_verified"] is False
    assert a["counter_evidence_unevidenced_reason"] == "pivot_absent"


def test_offline_slice_and_progressive_smoke_pass():
    summary = _load(SLICE / "summary.json")
    assert summary["verified"] is True
    assert summary["page_contract"] is True
    assert summary["degraded"] is False
    assert summary["stats"]["geometry_preserved_by_enrich"] is True
    assert summary["stats"]["fixture_replay_cache_misses"] == 0
    assert summary["stats"]["n_decisions"] == 100
    assert summary["stats"]["n_clusters"] == 8
    assert summary["stats"]["answer_status"] == "ready"

    smoke = _load(SMOKE)
    assert smoke["verdict"] == "PASS"
    assert smoke["checks_passed"] == smoke["checks_total"] == 23
    assert smoke["failures"] == []


def test_reports_and_accepted_pointer_are_recorded():
    assert REPORT.is_file()
    report = REPORT.read_text(encoding="utf-8")
    assert EXECUTING_RUN_ID in report
    assert RESUMED_RUN_ID in report
    assert "UNADJUDICATED" in report

    state = _load(STATE)
    assert state["accepted_run_id"] == "CYCLE_40284658455"
    assert state["accepted_commit"] == (
        "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83")
    for flag in ("human_gate_ready", "machine_gate_ready",
                 "packet_admitted", "ready_for_owner_session"):
        assert state[flag] is False, flag
    assert state["continue_recommended"] is True

    gate = _load(GATE)
    assert gate["gate"] == "PASS"
    assert gate["safe_to_integrate"] is True
    assert gate["required_fixes"] == []


def test_committed_gate_matches_accepted_ref_when_available():
    ref = subprocess.run(["git", "rev-parse", "--verify", "--quiet",
                          ACCEPTED_REF], cwd=str(ROOT), capture_output=True,
                         text=True)
    if ref.returncode != 0:
        pytest.skip(f"{ACCEPTED_REF} is not available in this checkout")
    committed = _git("show", f"{ACCEPTED_REF}:results/audit/product/"
                             "CYCLE_40284658455_GATE.json")
    local = GATE.read_text(encoding="utf-8").strip()
    assert hashlib.sha256(committed.encode()).hexdigest() == (
        hashlib.sha256(local.encode()).hexdigest())
    assert committed == local
