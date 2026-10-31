"""Operational resume 41188877123: diagnose 41188733592 and re-verify the slice.

The resumed run 41188733592 was dispatched off the persisted snapshot of run
41184474509 (commit ``980f880b``).  Its lane-cycle step failed after **17 s** of
a **2700 s** work quantum with the wrapper's generic exit **1** (no named
branch), both validation steps and audit/integrate were skipped, and the
``if: always()`` persist step left both team refs at ``980f880b``:
**ZERO_DURABLE_DELTA**.

The predecessor 41184474509 is why that snapshot was never audited: its team
job succeeded and committed an artifact-only delta, then its audit job died at
``Independent audit`` after **2705 s** of the same 2700 s quantum
(``LEX_WORK_QUANTUM_EXPIRED``, exit **78**) and the gate reader was skipped.

What this cycle locks, fail-closed:

* both public records above, with their observed step conclusions/durations;
* the **audit-instrument repair**: ``check_audit_namespace`` no longer counts
  the ACCEPTED run's committed gate as a producer mint (the false FAIL the
  41184474509 snapshot committed), while every non-accepted checked run id and
  every pending audit path still fails closed;
* a fresh SERVED vertical-slice run at this head (query -> bundle -> sourced
  answer -> counter pass -> clickable page), re-derived from its own artifact;
* the unchanged fail-closed posture and accepted pointer;
* that this producer minted no gate and wrote no auditor-namespace path.

No frozen gate, rubric, threshold or bar is imported, edited or re-tuned here.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EXECUTING_RUN_ID = "41188877123"
RESUMED_RUN_ID = "41188733592"
PREDECESSOR_RUN_ID = "41184474509"
ACCEPTED_RUN_ID = "40284658455"
ACCEPTED_HEAD = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
SNAPSHOT_HEAD = "980f880b60e9417f87343f3287db6265f9970949"

STATE = ROOT / "state" / "product.json"
ORCH = ROOT / "results" / "product" / "orchestration"
RAW = ORCH / f"CYCLE_{RESUMED_RUN_ID}_team_step_raw.json"
ORCH_DOC = ORCH / f"CYCLE_{RESUMED_RUN_ID}_orchestration.json"
DIAG = ORCH / f"CYCLE_{RESUMED_RUN_ID}_resume_diagnosis.json"
PREDECESSOR_RAW = ORCH / f"CYCLE_{PREDECESSOR_RUN_ID}_team_step_raw.json"
PREDECESSOR_ORCH = ORCH / f"CYCLE_{PREDECESSOR_RUN_ID}_orchestration.json"
SLICE = ROOT / "results" / "product" / "server_slice" / EXECUTING_RUN_ID
SLICE_SUMMARY = SLICE / "summary.json"
CURRENT_REPORT = ROOT / "reports" / "product" / f"CYCLE_{EXECUTING_RUN_ID}.md"
DOSSIER = (ROOT / "results" / "product" / "audit_readiness"
           / f"CYCLE_{RESUMED_RUN_ID}_audit_readiness.json")

FMT = "%Y-%m-%dT%H:%M:%SZ"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _step_seconds(step: dict) -> float:
    return (datetime.strptime(step["completed_at"], FMT)
            - datetime.strptime(step["started_at"], FMT)).total_seconds()


# --------------------------------------------------------------------------
# the orchestration failure we were asked to diagnose
# --------------------------------------------------------------------------

def test_public_record_observes_the_generic_step_failure():
    raw = _load(RAW)
    assert raw["schema"] == "github-actions-run-jobs-snapshot/1"
    assert raw["logs_endpoint_status"] == 403
    assert raw["run"]["id"] == int(RESUMED_RUN_ID)
    assert raw["run"]["conclusion"] == "failure"
    team = next(j for j in raw["jobs"] if j["name"] == "team")
    assert team["conclusion"] == "failure"
    steps = {s["name"]: s for s in team["steps"]}
    assert steps["Run lane cycle"]["conclusion"] == "failure"
    assert _step_seconds(steps["Run lane cycle"]) == 17.0
    assert _step_seconds(steps["Run lane cycle"]) < 2700  # not a quantum death
    assert steps["Validate active MVP producer state"]["conclusion"] == "skipped"
    assert steps["Enforce lane write scope"]["conclusion"] == "skipped"
    assert steps["Persist team snapshot"]["conclusion"] == "success"
    messages = [a["message"] for a in raw.get("annotations") or []]
    assert "Process completed with exit code 1." in messages
    # Generic passthrough: unlike 41176811677, no wrapper branch name here.
    assert not any("LEX_WORK_QUANTUM_EXPIRED" in m for m in messages)
    assert not any("LEX_ZERO_DELTA_REPAIR" in m for m in messages)
    audit = next(j for j in raw["jobs"] if j["name"] == "audit")
    assert audit["conclusion"] == "skipped"


def test_orchestration_document_rules_out_named_branches():
    doc = _load(ORCH_DOC)
    assert doc["run_id"] == int(RESUMED_RUN_ID)
    assert doc["classification"]["class"] == "TEAM_JOB_FAILED"
    assert doc["job_conclusions"] == {
        "team": "failure", "audit": "skipped", "integrate": "skipped",
        "resilience": "success",
    }
    diag = doc["diagnosis"]
    assert diag["exit_code"] == 1
    assert diag["failing_step"] == "Run lane cycle"
    assert diag["failing_step_duration_s"] == 17.0
    branches = {b["branch"]: b for b in diag["candidates"]["named_branches"]}
    assert branches["LEX_WORK_QUANTUM_EXPIRED"]["ruled_out"] is True
    assert branches["LEX_ZERO_DELTA_REPAIR"]["ruled_out"] is True
    assert diag["candidates"]["surviving_named_branches"] == []


def test_resume_diagnosis_records_zero_delta_and_unadjudicated_status():
    diag = _load(DIAG)
    assert diag["run_id"] == RESUMED_RUN_ID
    assert diag["predecessor_run_id"] == PREDECESSOR_RUN_ID
    orch = diag["orchestration"]
    assert orch["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    team = orch["team"]
    assert team["failed_step"] == "Run lane cycle"
    assert team["failed_step_seconds"] == 17.0
    assert team["producer_state_validation_step_conclusion"] == "skipped"
    assert team["write_scope_step_conclusion"] == "skipped"
    assert team["team_snapshot_step_conclusion"] == "success"
    assert orch["audit"]["gate_file_written"] is False
    assert orch["audit"]["conclusion"] == "skipped"
    observed = orch["observed_failure"]
    assert observed["exit_code"] == 1
    assert observed["quantum_expired"] is False
    assert diag["durable_delta"]["classification"] == "ZERO_DURABLE_DELTA"
    assert diag["durable_delta"]["changed_files"] == 0
    assert diag["durable_delta"]["snapshot_head"] == SNAPSHOT_HEAD
    assert diag["durable_delta"]["predecessor_head"] == SNAPSHOT_HEAD
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["accepted"] is False


def test_predecessor_audit_died_at_the_work_quantum():
    raw = _load(PREDECESSOR_RAW)
    assert raw["run"]["id"] == int(PREDECESSOR_RUN_ID)
    team = next(j for j in raw["jobs"] if j["name"] == "team")
    audit = next(j for j in raw["jobs"] if j["name"] == "audit")
    assert team["conclusion"] == "success"
    assert audit["conclusion"] == "failure"
    steps = {s["name"]: s for s in audit["steps"]}
    assert steps["Independent audit"]["conclusion"] == "failure"
    assert _step_seconds(steps["Independent audit"]) == 2705.0
    assert steps["Enforce audit scope and read gate"]["conclusion"] == "skipped"
    messages = [a["message"] for a in raw.get("annotations") or []
                if a.get("job") == "audit"]
    assert "Process completed with exit code 78." in messages
    assert any("LEX_WORK_QUANTUM_EXPIRED seconds=2700" in m for m in messages)
    doc = _load(PREDECESSOR_ORCH)
    assert doc["classification"]["class"] == "AUDIT_STEP_FAILED_NO_GATE"
    assert doc["classification"]["verdict_exists"] is False
    assert doc["diagnosis"]["exit_code"] == 78
    assert doc["diagnosis"]["failing_step"] == "Independent audit"
    assert doc["diagnosis"]["failing_step_duration_s"] == 2705.0


# --------------------------------------------------------------------------
# the audit-instrument repair (the false FAIL this cycle removes)
# --------------------------------------------------------------------------

def test_audit_namespace_ignores_the_accepted_gate_but_flags_a_resumed_gate(
        tmp_path, monkeypatch):
    from product import audit_readiness as ar

    (tmp_path / "results" / "audit" / "product").mkdir(parents=True)
    (tmp_path / "reports" / "audit" / "product").mkdir(parents=True)
    # The accepted base legitimately contains the auditor's own gate/report.
    (tmp_path / "results" / "audit" / "product"
     / f"CYCLE_{ACCEPTED_RUN_ID}_GATE.json").write_text("{}", encoding="utf-8")
    (tmp_path / "reports" / "audit" / "product"
     / f"CYCLE_{ACCEPTED_RUN_ID}.md").write_text("x", encoding="utf-8")

    monkeypatch.setattr(ar, "ROOT", tmp_path)
    monkeypatch.setattr(
        ar, "load_state",
        lambda: {"accepted_run_id": f"CYCLE_{ACCEPTED_RUN_ID}"},
    )

    ok = ar.check_audit_namespace(ACCEPTED_RUN_ID, "40283048553")
    assert ok["status"] == "PASS", ok
    assert ok["detail"]["suspect_paths"] == []

    # A gate/report for the resumed (failed) run is still a producer mint.
    (tmp_path / "results" / "audit" / "product"
     / f"CYCLE_{RESUMED_RUN_ID}_GATE.json").write_text("{}", encoding="utf-8")
    bad = ar.check_audit_namespace(RESUMED_RUN_ID, RESUMED_RUN_ID)
    assert bad["status"] == "FAIL"
    assert any(RESUMED_RUN_ID in p for p in bad["detail"]["suspect_paths"])

    # The pure helper never puts the accepted run id in the checked set.
    assert ar.audit_namespace_ids(
        ACCEPTED_RUN_ID, "40283048553", f"CYCLE_{ACCEPTED_RUN_ID}"
    ) == ["40283048553"]


# --------------------------------------------------------------------------
# the lane deliverable, verified at this head rather than asserted
# --------------------------------------------------------------------------

def test_served_vertical_slice_is_green_at_this_head():
    summary = _load(SLICE_SUMMARY)
    assert summary["schema"] == "product-server-slice/1"
    assert summary["verdict"] == "PASS"
    assert summary["failures"] == []
    assert len(summary["checks"]) == 10
    assert all(c["status"] == "PASS" for c in summary["checks"])
    counts = summary["counts"]
    assert counts["n_first_page"] == counts["n_final"] == 100
    assert counts["n_clusters_final"] == 8
    assert counts["n_cited"] >= 1
    assert counts["counter_authorities"] >= 1
    assert counts["counter_status_bearing_rows"] >= 1
    assert counts["rows_with_source_url"] == counts["n_final"]
    assert counts["page_contract_assertions"] >= 60
    assert summary["timing_s"]["total_s"] < 60  # local overhead, fixture mode
    assert (SLICE / "served.bundle.json").is_file()
    assert (SLICE / "first_page.bundle.json").is_file()


# --------------------------------------------------------------------------
# state, posture, and no self-minted gate
# --------------------------------------------------------------------------

def test_state_records_the_run_and_keeps_the_pointer_and_posture():
    st = _load(STATE)
    assert st["direction_version"] == 68
    assert st["accepted_run_id"] == f"CYCLE_{ACCEPTED_RUN_ID}"
    assert st["accepted_commit"] == ACCEPTED_HEAD
    from product.state_contract import accepted_pointer_evidence
    ev = accepted_pointer_evidence(st, ROOT)
    assert not ev["problems"], ev
    assert ev["gate_ok"] and ev["accept_commit_present"]

    hist = {str(h.get("run_id")): h for h in st.get("run_history") or []}
    entry = hist[RESUMED_RUN_ID]
    assert entry["status"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_ZERO_DURABLE_DELTA"
    assert entry["exit_code"] == 1
    assert entry["failed_step_seconds"] == 17.0
    assert entry["snapshot_commit"] == SNAPSHOT_HEAD
    assert entry["audit_gate"] == "NONE"
    pred = hist[PREDECESSOR_RUN_ID]
    assert pred["status"] == "TEAM_JOB_SUCCESS_AUDIT_JOB_QUANTUM_EXPIRED_NO_GATE"
    assert pred["exit_code"] == 78
    assert pred["failed_step_seconds"] == 2705.0

    block = st[f"cycle_{EXECUTING_RUN_ID}_operational_resume"]
    assert block["run_id"] == int(EXECUTING_RUN_ID)
    assert block["resumed_snapshot"]["run_id"] == int(RESUMED_RUN_ID)
    assert block["resumed_snapshot"]["team_ref_head"] == SNAPSHOT_HEAD
    assert block["lane_deliverable"]["status"] == "VERIFIED_AT_THIS_HEAD"
    assert (ROOT / block["diagnosis"]).is_file()
    assert (ROOT / block["raw_snapshot"]).is_file()
    assert (ROOT / block["report"]).is_file()
    assert (ROOT / block["lane_deliverable"]["served_slice"]).is_dir()
    assert (ROOT / block["lane_deliverable"]["artifact"]).is_file()
    assert block["adjudication"]["status"] == "UNADJUDICATED"
    for key, expected in (
        ("continue_recommended", True),
        ("human_gate_ready", False),
        ("machine_gate_ready", False),
        ("packet_admitted", False),
        ("ready_for_owner_session", False),
    ):
        assert st[key] == expected, (key, st[key])


def test_audit_readiness_profile_pins_the_observed_step_failure():
    from product import audit_readiness as ar
    prof = ar.select_profile(RESUMED_RUN_ID)
    assert prof["mechanism_kind"] == "observed_step_failure"
    assert prof["exit_code"] == 1
    assert prof["quantum_seconds"] == 2700
    assert prof["lane_cycle_step_seconds"] == 17.0
    assert prof["delta_kind"] == "zero"
    assert prof["failed_job"] == "team"
    assert prof["state_block"] == f"cycle_{EXECUTING_RUN_ID}_operational_resume"
    assert prof["cycle_test"] == f"product/tests/test_cycle_{EXECUTING_RUN_ID}.py"
    assert prof["current_report"] == CURRENT_REPORT


def test_audit_readiness_dossier_is_recorded_for_the_resumed_run():
    """Structural pin.

    The dossier is the instrument that RUNS this cycle test, so the dossier is
    generated first with ``--skip-tests`` and then re-generated in full; this
    test pins the identity and the two checks that make the snapshot checkable
    without re-deriving accepted work.
    """
    dossier = _load(DOSSIER)
    assert dossier["run_id"] == RESUMED_RUN_ID
    assert dossier["resumed_run_id"] == RESUMED_RUN_ID
    assert dossier["profile"] == RESUMED_RUN_ID
    assert dossier["predecessor_run_id"] == PREDECESSOR_RUN_ID
    ids = {c["id"]: c for c in dossier["checks"]}
    assert ids["resumed_diagnosis"]["status"] == "PASS"
    assert ids["audit_namespace"]["status"] == "PASS"
    assert CURRENT_REPORT.is_file()


def test_no_producer_minted_gate_and_no_auditor_namespace_write():
    st = _load(STATE)
    block = st[f"cycle_{EXECUTING_RUN_ID}_operational_resume"]
    assert block["adjudication"]["gate_minted"] is False
    assert block["adjudication"]["audit_namespace_written"] is False
    assert not (ROOT / "results" / "audit" / "product"
                / f"CYCLE_{EXECUTING_RUN_ID}_GATE.json").exists()
    assert not (ROOT / "results" / "audit" / "product"
                / f"CYCLE_{RESUMED_RUN_ID}_GATE.json").exists()


def test_the_lane_deliverable_is_consumed_not_re_measured():
    """Ordered work (1)/(2) stay accepted evidence; this cycle re-measures neither."""
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
