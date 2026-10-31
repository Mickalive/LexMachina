"""Operational resume 41179957652: diagnose 41176811677 and re-verify the slice.

The resumed run 41176811677 was dispatched off the persisted snapshot of run
41172922015 (commit ``f2c9cf72``).  Its lane-cycle step ran **2705 s** of a
**2700 s** work quantum and the public check-run annotation carries the literal
branch ``LEX_WORK_QUANTUM_EXPIRED seconds=2700`` with exit code **78**.  The
downstream validation and write-scope steps were skipped, audit/integrate were
skipped, and both team refs stayed at ``f2c9cf72``, so the run added zero
durable delta.

What this cycle locks, fail-closed:

* the public record of 41176811677 (2705 s, exit 78, quantum annotation,
  validation and write-scope steps skipped, audit/integrate skipped, HTTP 403
  logs);
* the **annotation-reader repair**: ``observe_raw_snapshot`` writes ``annotations``
  as a flat list, but ``_job_annotations`` only read a job-keyed mapping, so the
  committed quantum annotation was silently ``UNOBSERVED``.  The repair reads
  the flat list by exact job id/name and never attributes a nameless entry;
* a fresh SERVED vertical-slice run at this head (query -> bundle -> sourced
  answer -> counter pass -> clickable page), re-derived from its own artifact;
* the unchanged fail-closed posture, the unchanged accepted pointer, and that
  this producer minted no gate and wrote no auditor-namespace path.
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

EXECUTING_RUN_ID = "41179957652"
RESUMED_RUN_ID = "41176811677"
PREDECESSOR_RUN_ID = "41172922015"
ACCEPTED_RUN_ID = "40284658455"
ACCEPTED_HEAD = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
SNAPSHOT_HEAD = "f2c9cf724bebdc883caa33e623896784a9cad679"

STATE = ROOT / "state" / "product.json"
ORCH = ROOT / "results" / "product" / "orchestration"
RAW = ORCH / f"CYCLE_{RESUMED_RUN_ID}_team_step_raw.json"
ORCH_DOC = ORCH / f"CYCLE_{RESUMED_RUN_ID}_orchestration.json"
DIAG = ORCH / f"CYCLE_{RESUMED_RUN_ID}_resume_diagnosis.json"
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

def test_public_record_observes_the_work_quantum_expiry():
    raw = _load(RAW)
    assert raw["schema"] == "github-actions-run-jobs-snapshot/1"
    assert raw["logs_endpoint_status"] == 403
    assert raw["run"]["id"] == int(RESUMED_RUN_ID)
    assert raw["run"]["conclusion"] == "failure"
    team = next(j for j in raw["jobs"] if j["name"] == "team")
    assert team["conclusion"] == "failure"
    steps = {s["name"]: s for s in team["steps"]}
    assert steps["Run lane cycle"]["conclusion"] == "failure"
    assert _step_seconds(steps["Run lane cycle"]) == 2705.0
    assert _step_seconds(steps["Run lane cycle"]) > 2700  # a quantum death
    assert steps["Validate active MVP producer state"]["conclusion"] == "skipped"
    assert steps["Enforce lane write scope"]["conclusion"] == "skipped"
    messages = [a["message"] for a in raw.get("annotations") or []]
    assert "Process completed with exit code 78." in messages
    # Unlike 41172772289 (generic exit 1, UNOBSERVED), this run's public
    # annotation names the wrapper branch and the quantum explicitly.
    assert any("LEX_WORK_QUANTUM_EXPIRED seconds=2700" in m for m in messages)
    audit = next(j for j in raw["jobs"] if j["name"] == "audit")
    assert audit["conclusion"] == "skipped"


def test_orchestration_document_leaves_only_the_quantum_branch():
    doc = _load(ORCH_DOC)
    assert doc["run_id"] == int(RESUMED_RUN_ID)
    assert doc["classification"]["class"] == "TEAM_JOB_FAILED"
    assert doc["job_conclusions"] == {
        "team": "failure", "audit": "skipped", "integrate": "skipped",
        "resilience": "success",
    }
    diag = doc["diagnosis"]
    assert diag["exit_code"] == 78
    assert diag["failing_step"] == "Run lane cycle"
    assert diag["failing_step_duration_s"] == 2705.0
    assert diag["candidates"]["surviving_named_branches"] == [
        "LEX_WORK_QUANTUM_EXPIRED"
    ]
    branches = {b["branch"]: b for b in diag["candidates"]["named_branches"]}
    assert branches["LEX_WORK_QUANTUM_EXPIRED"]["ruled_out"] is False
    for name, branch in branches.items():
        if name != "LEX_WORK_QUANTUM_EXPIRED":
            assert branch["ruled_out"] is True, branch
    assert doc["team_branch_exists"] is True
    assert doc["audit_branch_exists"] is False


def test_resume_diagnosis_records_zero_delta_and_unadjudicated_status():
    diag = _load(DIAG)
    assert diag["run_id"] == RESUMED_RUN_ID
    assert diag["predecessor_run_id"] == PREDECESSOR_RUN_ID
    orch = diag["orchestration"]
    assert orch["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    team = orch["team"]
    assert team["failed_step"] == "Run lane cycle"
    assert team["failed_step_seconds"] == 2705.0
    assert team["producer_state_validation_step_conclusion"] == "skipped"
    assert team["write_scope_step_conclusion"] == "skipped"
    assert team["team_snapshot_step_conclusion"] == "success"
    assert orch["audit"]["gate_file_written"] is False
    assert orch["audit"]["conclusion"] == "skipped"
    observed = orch["observed_failure"]
    assert observed["annotations_available"] is True
    assert observed["quantum_expired"] is True
    assert observed["quantum_seconds"] == 2700
    assert observed["exit_code"] == 78
    mech = orch["mechanism"]
    assert mech["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert mech["annotations_available"] is True
    assert mech["logs_available"] is False
    assert mech["logs_endpoint_status"] == 403
    assert mech["quantum_expired"] is True
    assert mech["quantum_seconds"] == 2700
    assert mech["exit_code"] == 78
    delta = diag["durable_delta"]
    assert delta["classification"] == "ZERO_DURABLE_DELTA"
    assert delta["changed_files"] == 0
    assert delta["snapshot_head"] == delta["predecessor_head"] == SNAPSHOT_HEAD
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["accepted"] is False
    assert diag["validation_findings"]["missing_claimed_cycle_tests"] == []
    assert diag["validation_findings"]["runtime_preflight"]["ok"] is True


def test_flat_annotation_reader_repair_is_exact_and_never_guesses():
    """The defect this cycle repaired, pinned as a regression.

    Before the repair the committed flat list was invisible, so the same raw
    snapshot classified as ``UNOBSERVED`` with ``exit_code=None``.  The reader
    must now return the team annotations and must NOT attribute a nameless
    entry to the job being classified.
    """
    from product.audit_step_diagnosis import _job_annotations

    raw = _load(RAW)
    team = next(j for j in raw["jobs"] if j["name"] == "team")
    audit = next(j for j in raw["jobs"] if j["name"] == "audit")

    team_ann = _job_annotations(raw, team)
    team_msgs = [a["message"] for a in team_ann]
    assert "Process completed with exit code 78." in team_msgs
    assert any("LEX_WORK_QUANTUM_EXPIRED seconds=2700" in m for m in team_msgs)

    # A skipped job has no annotations of its own; the reader must not lend it
    # the failing job's messages.
    audit_msgs = [a["message"] for a in _job_annotations(raw, audit)]
    assert not any("LEX_WORK_QUANTUM_EXPIRED" in m for m in audit_msgs)

    # A flat entry that names no job is excluded rather than attributed.
    nameless = {"annotations": [{"message": "unattributed"}]}
    assert _job_annotations(nameless, team) == []


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
    assert entry["exit_code"] == 78
    assert entry["exit_code_meaning"] == "LEX_WORK_QUANTUM_EXPIRED"
    assert entry["failed_step_seconds"] == 2705.0
    assert entry["snapshot_commit"] == SNAPSHOT_HEAD
    assert entry["audit_gate"] == "NONE"

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


def test_audit_readiness_profile_pins_observed_quantum_expiry():
    from product import audit_readiness as ar
    prof = ar.select_profile(RESUMED_RUN_ID)
    assert prof["mechanism_kind"] == "observed"
    assert prof["exit_code"] == 78
    assert prof["quantum_seconds"] == 2700
    assert prof["delta_kind"] == "zero"
    assert prof["failed_job"] == "team"
    assert prof["state_block"] == f"cycle_{EXECUTING_RUN_ID}_operational_resume"
    assert prof["cycle_test"] == f"product/tests/test_cycle_{EXECUTING_RUN_ID}.py"
    assert prof["current_report"] == CURRENT_REPORT
    try:
        ar.select_profile("99999999999")
    except SystemExit:
        pass
    else:  # pragma: no cover - defensive
        raise AssertionError("unknown run id must not inherit another profile")


def test_audit_readiness_dossier_is_recorded_for_the_resumed_run():
    """Structural pin only.

    The dossier is the instrument that RUNS this cycle test, so asserting its
    own ``overall_status == PASS`` here would be circular (first generation
    would always see the previous FAIL).  Its PASS is reported by the dossier
    run itself; this test pins the run/profile identity and the two checks that
    make the snapshot checkable without re-deriving it.
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
