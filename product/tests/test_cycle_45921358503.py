"""Operational resume 45921358503: fifth failure mode and stale-pointer repair.

The failed snapshot 45921135544 began on the accepted base 7be4480e with a
healthy free model.  Its team job passed validation, peer mount and OpenCode
install, then ``Run lane cycle`` failed in 17 s with exit 1.  State validation,
write-scope enforcement, audit and integrate were skipped and the team ref
stayed byte-identical to its predecessor (ZERO_DURABLE_DELTA).  The logs
endpoint returned HTTP 403, so no quantum expiry, gateway rejection or scope
violation is asserted: the provider-level cause is UNOBSERVED.

The snapshot also carried a reproducible, deterministic validation defect:
``test_cycle_40284658455.py`` still pinned the pre-acceptance pointer and
asserted that its own gate must not exist.  This test locks both diagnoses,
the first-class ``observed_agent_step`` mechanism, the supersession amendment,
the accepted-pointer advance, and the bounded runnable verification.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from product import audit_readiness as ar  # noqa: E402
from product.state_contract import accepted_pointer_evidence  # noqa: E402

RUN_ID = "45921358503"
RESUMED_RUN_ID = "45921135544"
ACCEPTED_RUN = "40284658455"
ACCEPTED_SHA = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
PRIOR_ACCEPTED_SHA = "5adaa66d4ad2b9702cd023bfd49d743667f9e638"

STATE = ROOT / "state" / "product.json"
RAW = ROOT / "results" / "product" / "orchestration" / (
    f"CYCLE_{RESUMED_RUN_ID}_run_jobs_raw.json")
DIAG = ROOT / "results" / "product" / "orchestration" / (
    f"CYCLE_{RUN_ID}_resume_diagnosis.json")
SMOKE = ROOT / "results" / "product" / "progressive_smoke" / (
    f"CYCLE_{RUN_ID}_progressive_smoke.json")
REPORT = ROOT / "reports" / "product" / f"CYCLE_{RUN_ID}.md"
GATE = ROOT / "results" / "audit" / "product" / f"CYCLE_{RUN_ID}_GATE.json"
AUDIT_REPORT = ROOT / "reports" / "audit" / "product" / f"CYCLE_{RUN_ID}.md"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_raw_snapshot_records_the_observed_agent_step_failure():
    raw = _load(RAW)
    assert raw["run"]["id"] == int(RESUMED_RUN_ID)
    assert raw["run"]["conclusion"] == "failure"
    assert raw["run"]["head_sha"].startswith("b61d486d")
    team = next(j for j in raw["jobs"] if j["name"] == "team")
    steps = {s["name"]: s["conclusion"] for s in team["steps"]}
    assert team["conclusion"] == "failure"
    assert steps["Validate lane and initialize working base"] == "success"
    assert steps["Mount accepted peer evidence"] == "success"
    assert steps["Install Ox/OpenCode"] == "success"
    assert steps["Run lane cycle"] == "failure"
    assert steps["Validate active MVP producer state"] == "skipped"
    assert steps["Enforce lane write scope"] == "skipped"
    assert steps["Persist team snapshot"] == "success"
    annotation = raw["annotations"][0]
    assert annotation["message"] == "Process completed with exit code 1."
    assert raw["logs_endpoint"]["observed_status"] == 403
    assert raw["logs_endpoint"]["log_text_available"] is False
    assert raw["remote_refs_at_diagnosis"]["lab_product"] == ACCEPTED_SHA
    assert raw["remote_refs_at_diagnosis"]["team_45921135544"] == ACCEPTED_SHA


def test_diagnosis_pins_fifth_mechanism_and_zero_durable_delta():
    diag = _load(DIAG)
    assert diag["run_id"] == RESUMED_RUN_ID
    assert diag["resumed_by_run_id"] == RUN_ID
    assert diag["predecessor_run_id"] == ACCEPTED_RUN
    orch = diag["orchestration"]
    assert orch["classification"] == "TEAM_JOB_AGENT_STEP_FAILED_NO_GATE"
    assert orch["failed_job"] == "team"
    assert orch["failed_step"] == "Run lane cycle"
    mech = orch["mechanism"]
    assert mech["status"] == "OBSERVED_AGENT_STEP_FAILED_ZERO_DELTA"
    assert mech["logs_available"] is False
    assert mech["logs_endpoint_status"] == 403
    assert mech["quantum_expired"] is False
    assert mech["lane_cycle_step_conclusion"] == "failure"
    assert mech["exit_code"] == 1
    assert mech["failure_cause"] == "UNOBSERVED"
    assert orch["audit"]["skipped"] is True
    assert orch["audit"]["gate_file_written"] is False
    assert orch["model_health"]["healthy"] is True

    delta = diag["durable_delta"]
    assert delta["classification"] == "ZERO_DURABLE_DELTA"
    assert delta["changed_files"] == 0
    assert delta["snapshot_head"] == delta["predecessor_head"] == ACCEPTED_SHA
    assert diag["adjudication"] == {
        "status": "UNADJUDICATED",
        "accepted": False,
        "claim_ceiling": (
            "OPERATIONAL-RESUME AND AUDIT-READINESS EVIDENCE ONLY. No live "
            "retrieval, legal usefulness, frozen bar, serve verdict, "
            "acceptance or human-gate readiness is asserted."
        ),
    }


def test_stale_pointer_validation_defect_is_recorded_and_repaired():
    diag = _load(DIAG)
    defect = diag["validation_failure_on_snapshot"]
    assert defect["classification"] == "SUPERSESSION_STALE_HISTORICAL_TEST"
    assert "2 failed, 6 passed" in defect["observed_before_repair"]
    assert "CYCLE_40284658455_GATE.json" in defect["failures"][0]["error"]
    assert PRIOR_ACCEPTED_SHA in defect["failures"][1]["error"]
    assert defect["not_claimed_as_remote_cause"] is True
    assert "SUPERSESSION AMENDMENT" in defect["repaired_by"]

    historical = (ROOT / "product" / "tests"
                  / "test_cycle_40284658455.py").read_text(encoding="utf-8")
    assert "SUPERSESSION AMENDMENT" in historical
    assert "accepted_pointer_evidence(st, ROOT)" in historical
    assert "assert not (ROOT / \"results\" / \"audit\" / \"product\" /\n                f\"CYCLE_{EXECUTING_RUN_ID}_GATE.json\").exists()" not in historical


def test_state_advances_pointer_and_attribution_without_posture_drift():
    st = _load(STATE)
    assert st["current_cycle_run_id"] == int(RUN_ID)
    assert st["accepted_run_id"] == f"CYCLE_{ACCEPTED_RUN}"
    assert st["accepted_commit"] == ACCEPTED_SHA
    evidence = accepted_pointer_evidence(st, ROOT)
    assert evidence["problems"] == [], evidence
    assert evidence["gate_ok"] is True
    assert evidence["accept_commit_present"] is True
    head = subprocess.run(
        ["git", "ls-remote", "--heads", "origin", "refs/heads/lab/product"],
        cwd=str(ROOT), capture_output=True, text=True, check=True).stdout.strip()
    assert head.startswith(ACCEPTED_SHA), (head, ACCEPTED_SHA)

    blk = st["cycle_45921358503_operational_resume"]
    assert blk["run_id"] == int(RUN_ID)
    assert blk["resumed_snapshot"]["run_id"] == int(RESUMED_RUN_ID)
    assert blk["mechanism_kind"] == "observed_agent_step"
    assert blk["accepted_pointer"]["accepted_commit"] == ACCEPTED_SHA
    assert blk["bundle_bytes_written"] is False
    assert blk["frozen_bar_scored"] is False
    for key in ("continue_recommended", "human_gate_ready",
                "machine_gate_ready", "packet_admitted",
                "ready_for_owner_session", "direction_version"):
        if key == "continue_recommended":
            assert st[key] is True
        elif key == "direction_version":
            assert st[key] == 68
        else:
            assert st[key] is False

    hist = {str(h.get("run_id")): h for h in st["run_history"] or []}
    assert hist[RESUMED_RUN_ID]["status"] == "TEAM_JOB_AGENT_STEP_FAILED_NO_GATE"
    assert hist[RUN_ID]["status"] == "OPERATIONAL_RESUME_AUDIT_READINESS_REPAIR"
    assert hist[ACCEPTED_RUN]["audit_gate"] == "PASS_ACCEPTED_BY_LATER_CYCLE"


def test_audit_readiness_models_this_mechanism_as_first_class():
    prof = ar.select_profile(RUN_ID)
    assert prof["resumed_run_id"] == RESUMED_RUN_ID
    assert prof["predecessor_run_id"] == ACCEPTED_RUN
    assert prof["mechanism_kind"] == "observed_agent_step"
    assert prof["classification"] == "TEAM_JOB_AGENT_STEP_FAILED_NO_GATE"
    assert prof["failed_step"] == "Run lane cycle"
    assert prof["exit_code"] == 1
    assert prof["delta_kind"] == "zero"
    assert prof["cycle_test"] == "product/tests/test_cycle_45921358503.py"
    assert ar.select_profile(RESUMED_RUN_ID)["cycle_test"] == (
        "product/tests/test_cycle_45921358503.py")

    ar.PROFILE.clear()
    ar.PROFILE.update(prof)
    check = ar.check_resumed_diagnosis()
    assert check["status"] == "PASS", check
    assert check["detail"]["mechanism_kind"] == "observed_agent_step"
    assert check["detail"]["problems"] == []

    try:
        ar.select_profile("99999999999")
    except SystemExit:
        pass
    else:  # pragma: no cover - defensive
        raise AssertionError("select_profile must fail closed on unknown runs")


def test_runnable_slice_and_producer_audit_namespace_are_verified():
    smoke = _load(SMOKE)
    assert smoke["verdict"] == "PASS"
    assert smoke["checks_passed"] == smoke["checks_total"] == 23
    timings = smoke["timings_s"]
    assert timings["server_boot_s"] < 3.0
    assert timings["start_s"] < 1.0
    assert not GATE.exists() and not AUDIT_REPORT.exists()
    text = REPORT.read_text(encoding="utf-8")
    assert RUN_ID in text and RESUMED_RUN_ID in text
    assert "UNOBSERVED" in text
    assert "observed_agent_step" in text
    assert "SUPERSESSION" in text.upper() or "supersession" in text
