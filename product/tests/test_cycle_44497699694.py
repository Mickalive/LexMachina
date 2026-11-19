"""Operational resume 44497699694 of persisted snapshot 44490642465.

The v68 P0 rejection/incumbent leg is already LANDED and is verified here, not
rebuilt.  Run 44490642465's persisted snapshot is the ref
``origin/cycle/core/product/44490642465/team`` at HEAD 0c50e0bb (the
"product cycle 44480855771 repair 0" tree): the team job's "Run lane cycle"
step ran 2705 s (step-level) to the work-quantum window and failed with NO check-run
annotations and no downloadable logs, the always-run persist step published the
unchanged tree, so the durable delta is ZERO.  Orchestration facts are observed
from the committed public run/jobs snapshot; the exact exit code and log-level
cause stay UNOBSERVED.

The concrete, locally REPRODUCED validation failure this cycle repairs is in
the snapshot's own dossier generator, product/audit_readiness.py::run(): the C1
claim had branches only for the observed_log / observed_scope / observed
mechanism kinds, so observed_no_annotations and observed_zero_delta runs (both
of which DO have a committed snapshot) fell through to a "No public run/jobs
snapshot was available" text that misreports the evidence.  Explicit, honest C1
branches were added.  No frozen bar, rubric, threshold or verdict contract was
edited.

This test pins that repair, the honest zero-delta/fast-stop diagnosis, the
fail-closed posture, the new audit-readiness profile and the unchanged v68
content-rejection deliverable.  It writes no gate, no verdict and no
human-gate readiness.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

EXECUTING_RUN_ID = "44497699694"
RESUMED_RUN_ID = "44490642465"
SNAPSHOT_HEAD = "0c50e0bb515759d323c1c163f706e3aea58a41c0"
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
    assert block["validation_failure"] == (
        "AUDIT_READINESS_C1_MISREPORTS_COMMITTED_SNAPSHOT_RUNS")
    assert block["durable_delta"] == "ZERO_DURABLE_DELTA"
    assert block["verdict"] == "NONE_UNADJUDICATED"
    assert block["accepted_this_cycle"] is False
    assert block["gate_minted"] is False
    assert block["audit_namespace_written"] is False


def test_diagnosis_proves_zero_delta_and_observed_stop():
    from product import audit_step_diagnosis as asd

    raw = _load(RAW)
    cls = asd.classify(raw)
    assert cls["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    mech = cls["mechanism"]
    assert mech["status"] == "UNOBSERVED"
    assert mech["annotations_available"] is False
    assert mech["logs_available"] is False
    assert mech["quantum_expired"] is False
    assert cls["team"]["failed_step"] == "Run lane cycle"
    assert cls["team"]["failed_step_seconds"] == 2705.0
    assert cls["team"]["team_snapshot_persisted"] is True
    assert cls["audit"]["conclusion"] == "skipped"
    assert cls["audit"]["gate_file_written"] is False

    diag = _load(DIAG)
    assert diag["run_id"] == RESUMED_RUN_ID
    assert diag["predecessor_run_id"] == "44480855771"
    assert diag["orchestration"]["classification"] == (
        "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE")
    assert diag["durable_delta"]["classification"] == "ZERO_DURABLE_DELTA"
    assert diag["durable_delta"]["changed_files"] == 0
    assert diag["durable_delta"]["snapshot_head"] == SNAPSHOT_HEAD
    obs = diag["orchestration"]["observed_failure"]
    assert obs["failed_step_seconds"] == 2705.0
    assert obs["quantum_consistent_unconfirmed"] is True
    assert obs["exit_code"] is None
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["accepted"] is False


def test_c1_claim_no_longer_misreports_a_committed_snapshot():
    """The reproduced validation defect: a committed-snapshot run must not be
    labelled 'No public run/jobs snapshot was available'.  Exercise the dossier
    generator for this run (without the slow smoke/test checks) and read its C1
    claim.
    """
    from product import audit_readiness as ar

    src = (ROOT / "product" / "audit_readiness.py").read_text(encoding="utf-8")
    assert 'elif mechanism_kind == "observed_no_annotations":' in src
    assert 'elif mechanism_kind == "observed_zero_delta":' in src

    rec = ar.run(EXECUTING_RUN_ID, include_tests=False, include_smoke=False,
                 auto_bootstrap=False)
    c1 = next(c for c in rec["claims"] if c["id"] == "C1")
    assert "No public run/jobs snapshot" not in c1["claim"]
    assert "committed public run/jobs snapshot" in c1["claim"]
    assert "2705.0" in c1["claim"]
    assert any(str(RAW.relative_to(ROOT)) in a for a in c1["artifacts"])
    assert not GATE.exists(), "producer must never write an audit gate"


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
