"""Operational resume 44480855771 of persisted snapshot 44480512027.

The mediated P0 delivery (v68 rejection/incumbent leg) is already LANDED and is
verified here, not rebuilt.  Run 44480512027's persisted snapshot is byte-identical
to its predecessor (HEAD 5e48b511): the team job's "Run lane cycle" step failed
fast (16 s) with no check-run annotations and no downloadable logs, the always-run
persist step published the unchanged tree, so the durable delta is ZERO.  The
orchestration facts are observed; the log-level cause is not, and no provider,
auth or gateway mechanism is asserted.

The concrete, locally REPRODUCED validation failure this cycle repairs is in the
predecessor snapshot's own cycle test, product/tests/test_cycle_44471693612.py:
it named the conventional "origin/cycle/core/product/44464605045/team" ref,
which an operational-resume / audit checkout does not fetch, so it degraded to
REF_ABSENT and failed its self-check despite intact committed bytes.  The fix
names the present commit SHA (04e07eac), which proves the same 9-file
COMMITTED_DELTA without weakening any claim.

This test pins that repair, the honest zero-delta/fast-fail diagnosis, the
fail-closed posture, the new audit-readiness profile and the unchanged v68
content-rejection deliverable.  It writes no gate, no verdict and no human-gate
readiness.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

EXECUTING_RUN_ID = "44480855771"
RESUMED_RUN_ID = "44480512027"
SNAPSHOT_HEAD = "5e48b511239e6b6a7bb8c46e52c245c624d53d76"
ACCEPTED_RUN_ID = "CYCLE_40284658455"
ACCEPTED_COMMIT = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"

STATE = ROOT / "state" / "product.json"
DIAG = (ROOT / "results" / "product" / "orchestration"
        / f"CYCLE_{RESUMED_RUN_ID}_resume_diagnosis.json")
RAW = (ROOT / "results" / "product" / "orchestration"
       / f"CYCLE_{RESUMED_RUN_ID}_run_jobs_raw.json")
BEFORE = (ROOT / "results" / "product" / "offline_slice"
          / "20261024T142517Z" / "rent-default.bundle.json")
AFTER = (ROOT / "results" / "product" / "offline_slice"
         / "20261025T070356Z" / "rent-default.bundle.json")
REPORT = ROOT / "reports" / "product" / f"CYCLE_{EXECUTING_RUN_ID}.md"
REPAIRED_TEST = (ROOT / "product" / "tests"
                 / "test_cycle_44471693612.py")
GATE = ROOT / "results" / "audit" / "product" / (
    f"CYCLE_{EXECUTING_RUN_ID}_GATE.json")

D2_DECISION = "gr_gerichte_ERZ 2010 25"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_state_is_fail_closed_and_records_this_resume():
    st = _load(STATE)
    assert st["lane"] == "product"
    assert st["direction_version"] == 68
    assert st["current_cycle_run_id"] == int(EXECUTING_RUN_ID)
    assert st["accepted_run_id"] == ACCEPTED_RUN_ID
    assert st["accepted_commit"] == ACCEPTED_COMMIT
    assert st["continue_recommended"] is True
    for key in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                "ready_for_owner_session"):
        assert st[key] is False, key
    hist = [r for r in st["run_history"]
            if r.get("run_id") == int(EXECUTING_RUN_ID)]
    assert len(hist) == 1
    assert hist[0]["audit_gate"] == "NONE_YET"
    block = st[f"cycle_{EXECUTING_RUN_ID}_operational_resume"]
    assert block["status"] == "UNADJUDICATED_OPERATIONAL_RESUME"
    assert block["resumed_snapshot"]["run_id"] == int(RESUMED_RUN_ID)
    assert block["resumed_snapshot"]["head_sha"] == SNAPSHOT_HEAD[:8]
    assert block["mechanism"] == "OBSERVED_FAST_FAIL_NO_ANNOTATIONS"
    assert block["validation_failure"] == "OBSERVED_REF_ABSENT_IN_CYCLE_TEST"
    assert block["durable_delta"] == "ZERO_DURABLE_DELTA"
    assert block["verdict"] == "NONE_UNADJUDICATED"
    assert block["accepted_this_cycle"] is False
    assert block["gate_minted"] is False
    assert block["audit_namespace_written"] is False


def test_diagnosis_proves_zero_delta_and_observed_fast_fail():
    from product import audit_step_diagnosis as asd

    raw = _load(RAW)
    cls = asd.classify(raw)
    assert cls["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    mech = cls["mechanism"]
    assert mech["status"] == "UNOBSERVED"
    assert mech["annotations_available"] is False
    assert mech["quantum_expired"] is False
    assert cls["team"]["failed_step"] == "Run lane cycle"
    assert cls["team"]["failed_step_seconds"] == 16.0
    assert cls["team"]["team_snapshot_persisted"] is True
    assert cls["audit"]["conclusion"] == "skipped"
    assert cls["audit"]["gate_file_written"] is False

    diag = _load(DIAG)
    assert diag["run_id"] == RESUMED_RUN_ID
    assert diag["predecessor_run_id"] == "44471693612"
    assert diag["orchestration"]["classification"] == (
        "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE")
    assert diag["durable_delta"]["classification"] == "ZERO_DURABLE_DELTA"
    assert diag["durable_delta"]["changed_files"] == 0
    assert diag["durable_delta"]["snapshot_head"] == SNAPSHOT_HEAD
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["accepted"] is False


def test_validation_failure_is_repaired_and_still_green():
    """The predecessor snapshot's own cycle test degraded to REF_ABSENT on a
    resume checkout because it named an unfetched team ref.  It must now name a
    present commit SHA, keep every COMMITTED_DELTA claim assertion, and pass.
    """
    from product import resume_snapshot_diagnosis as rsd

    source = REPAIRED_TEST.read_text(encoding="utf-8")
    assert "origin/cycle/core/product/44464605045/team" not in source.split(
        "D2_DECISION")[0], "the fragile conventional ref must be gone"
    assert 'SNAPSHOT_REF = RESUMED_HEAD' in source
    assert "04e07eaceb230fcfd33feb891a75b5599b326830" in source

    # Same 9-file delta, now provable from the present commit SHA.
    delta = rsd._delta("04e07eaceb230fcfd33feb891a75b5599b326830",
                       "c3bd920c342b728f6d2ae29ed8f041a0fbdd968b")
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["changed_files"] == 9
    # The absent conventional ref must still honestly report REF_ABSENT.
    absent = rsd._delta("origin/cycle/core/product/44464605045/team",
                        "c3bd920c342b728f6d2ae29ed8f041a0fbdd968b")
    assert absent["classification"] == "REF_ABSENT"

    proc = subprocess.run(
        [sys.executable, "-m", "pytest", str(REPAIRED_TEST), "-q"],
        cwd=ROOT, capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:]


def test_audit_readiness_profile_pins_this_run_without_minting_a_gate():
    from product import audit_readiness as ar

    profile = ar.select_profile(EXECUTING_RUN_ID)
    assert profile["resumed_run_id"] == RESUMED_RUN_ID
    assert profile["mechanism_kind"] == "observed_no_annotations"
    assert profile["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert profile["delta_kind"] == "zero"
    assert profile["changed_files"] == 0
    assert profile["cycle_test"].endswith(
        f"test_cycle_{EXECUTING_RUN_ID}.py")
    assert profile["state_block"] == f"cycle_{EXECUTING_RUN_ID}_operational_resume"
    assert REPORT.is_file() and "UNADJUDICATED" in REPORT.read_text()
    assert not GATE.exists(), "producer must never write an audit gate"


def test_p0_rejection_leg_still_downgrades_the_letterhead_row():
    from product.query.counter_evidence_span import frozen_content_defects

    before_row = next(
        r for r in _load(BEFORE)["decisions"]
        if r["decision_id"] == D2_DECISION)
    after_row = next(
        r for r in _load(AFTER)["decisions"]
        if r["decision_id"] == D2_DECISION)
    assert before_row["counter_evidence_verified"] is True
    assert "D2_letterhead_zone" in frozen_content_defects(
        before_row["counter_evidence"], before_row)
    assert after_row["counter_evidence_verified"] is False
    assert after_row["counter_evidence_unevidenced"] is True
    assert after_row["counter_evidence_unevidenced_reason"] == "pivot_absent"


def test_content_family_still_proves_the_v68_rejection_leg():
    cf = _load(ROOT / "results" / "product" / "counter_content_family"
               / "CYCLE_40257275384.json")
    totals = cf["fixed_path_family"]["totals"]
    assert totals["n_bundles"] == 49
    assert totals["n_verified"] == 55
    assert totals["n_verified_defective"] == 0
    assert all(v == 0 for v in totals["defect_histogram"].values())
    assert cf["false_reject_count"] == 0
    assert cf["confirmed_set"]["still_verified"]
    assert cf["ordered_work_2_success_rule"]["met"] is True
    assert cf["ordered_work_2_full_success_rule"]["met"] is True
