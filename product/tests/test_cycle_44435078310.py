"""Operational resume 44435078310: rc-67 zero-delta repair of snapshot 44433859941.

Run 44433859941 (Core product dirV68 repair0) failed at ``Run lane cycle``
after 436 s and the public check-run annotation gave the wrapper's own verdict:
``LEX_ZERO_DELTA_REPAIR`` / exit 67. The always-run persist step published a
team ref byte-identical to predecessor 44426640158, so the durable delta is
zero. This test locks the fifth first-class mechanism (OBSERVED_ZERO_DELTA_REPAIR)
and keeps the run UNADJUDICATED with no producer-minted gate.

It also records the accepted-pointer repair: requirement 4's BOTH halves are
now present for 40284658455 (PASS gate plus ``accept product cycle 40284658455``
on lab/product), so state advances off the stale 40269774540 / 5adaa66d pointer.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

EXECUTING_RUN_ID = "44435078310"
RESUMED_RUN_ID = "44433859941"
PREDECESSOR_RUN_ID = "44426640158"
ACCEPTED_RUN_ID = "40284658455"
ACCEPTED_COMMIT = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"

STATE = ROOT / "state" / "product.json"
ORCH = ROOT / "results" / "product" / "orchestration"
RAW = ORCH / f"CYCLE_{RESUMED_RUN_ID}_team_step_raw.json"
DIAG = ORCH / f"CYCLE_{RESUMED_RUN_ID}_resume_diagnosis.json"
REPORT = ROOT / "reports" / "product" / f"CYCLE_{EXECUTING_RUN_ID}.md"
GATE = ROOT / "results" / "audit" / "product" / (
    f"CYCLE_{ACCEPTED_RUN_ID}_GATE.json")


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_public_snapshot_shows_rc67_zero_delta_at_the_lane_cycle_step():
    raw = _load(RAW)
    assert raw["schema"] == "product-actions-run-jobs-snapshot/1"
    assert raw["run"]["id"] == int(RESUMED_RUN_ID)
    assert raw["run"]["conclusion"] == "failure"
    assert raw["run"]["head_sha"].startswith("2aab7731")
    team = next(j for j in raw["jobs"] if j["name"] == "team")
    steps = {s["name"]: s["conclusion"] for s in team["steps"]}
    assert steps["Run lane cycle"] == "failure"
    assert steps["Persist team snapshot"] == "success"
    assert steps["Validate active MVP producer state"] == "skipped"
    assert team["conclusion"] == "failure"
    assert raw["logs_endpoint_status"] is None  # 403; do not claim full logs
    ann_text = json.dumps(raw["annotations"])
    assert "Process completed with exit code 67." in ann_text
    assert "LEX_ZERO_DELTA_REPAIR" in ann_text


def test_classifier_reproduces_the_observed_zero_delta_mechanism():
    from product import audit_step_diagnosis as asd

    fresh = asd.classify(_load(RAW))
    assert fresh["classification"] == (
        "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE")
    mech = fresh["mechanism"]
    assert mech["status"] == "OBSERVED_ZERO_DELTA_REPAIR"
    assert mech["exit_code"] == 67
    assert mech["quantum_expired"] is False
    assert mech["annotations_available"] is True
    assert "LEX_ZERO_DELTA_REPAIR" in mech["claim"]
    assert fresh["observed_failure"]["zero_delta_repair"] is True
    assert fresh["adjudication"]["product_defect"] is False
    assert fresh["adjudication"]["verdict_written"] is False
    # The generic 'not downloadable' UNOBSERVED claim stays intact for older
    # snapshots that have no annotation (append-only fixture compatibility).
    assert "not downloadable" in asd.classify({
        "schema": "product-actions-run-jobs-snapshot/1",
        "run": {"id": 1, "conclusion": "failure"},
        "jobs": [{"name": "team", "conclusion": "failure", "steps": []}],
        "annotations": {},
    })["mechanism"]["claim"]


def test_resume_diagnosis_proves_zero_durable_delta_and_no_verdict():
    diag = _load(DIAG)
    assert diag["run_id"] == RESUMED_RUN_ID
    assert diag["predecessor_run_id"] == PREDECESSOR_RUN_ID
    orch = diag["orchestration"]
    assert orch["mechanism"]["status"] == "OBSERVED_ZERO_DELTA_REPAIR"
    delta = diag["durable_delta"]
    assert delta["classification"] == "ZERO_DURABLE_DELTA"
    assert delta["changed_files"] == 0
    assert delta["snapshot_head"] == delta["predecessor_head"]
    assert delta["snapshot_head"].startswith("a591bbf8")
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["accepted"] is False
    assert diag["adjudication"]["audit"]["gate_file_present"] is False


def test_state_records_this_resume_and_the_accepted_pointer_repair():
    st = _load(STATE)
    assert st["current_cycle_run_id"] == int(EXECUTING_RUN_ID)
    assert st["accepted_run_id"] == f"CYCLE_{ACCEPTED_RUN_ID}"
    assert st["accepted_commit"] == ACCEPTED_COMMIT
    blk = st["cycle_44435078310_operational_resume"]
    assert blk["resumed_snapshot"]["run_id"] == int(RESUMED_RUN_ID)
    assert blk["predecessor_run_id"] == int(PREDECESSOR_RUN_ID)
    assert blk["mechanism"] == "OBSERVED_ZERO_DELTA_REPAIR"
    assert "UNADJUDICATED" in blk["status"].upper()
    assert (ROOT / blk["diagnosis"]).is_file()
    for key in ("continue_recommended",):
        assert st[key] is True
    for key in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                "ready_for_owner_session"):
        assert st[key] is False
    assert st["direction_version"] == 68
    hist = {str(h.get("run_id")): h for h in st["run_history"]}
    assert RESUMED_RUN_ID in hist
    assert "ZERO_DELTA" in hist[RESUMED_RUN_ID]["status"].upper()
    assert EXECUTING_RUN_ID in hist


def test_accepted_pointer_has_both_halves_of_requirement_4():
    gate = _load(GATE)
    assert gate["gate"] == "PASS"
    assert gate["safe_to_integrate"] is True
    assert gate["required_fixes"] == []
    head = subprocess.run(
        ["git", "ls-remote", "--heads", "origin", "refs/heads/lab/product"],
        cwd=str(ROOT), capture_output=True, text=True, check=True).stdout
    assert head.startswith(ACCEPTED_COMMIT), (head, ACCEPTED_COMMIT)


def test_audit_readiness_instrument_models_this_failure_mode():
    from product import audit_readiness as ar

    prof = ar.select_profile(EXECUTING_RUN_ID)
    assert prof["mechanism_kind"] == "observed_zero_delta"
    assert prof["resumed_run_id"] == RESUMED_RUN_ID
    assert prof["cycle_test"] == "product/tests/test_cycle_44435078310.py"
    # Alias for the resumed run id must resolve to the same executing profile.
    assert ar.select_profile(RESUMED_RUN_ID)["mechanism_kind"] == (
        "observed_zero_delta")
    dossier = _load(ROOT / "results" / "product" / "audit_readiness"
                    / "CYCLE_44435078310_audit_readiness.json")
    rec = next((c for c in dossier["checks"]
                if c["id"] == "resumed_diagnosis"), None)
    assert rec is not None and rec["status"] == "PASS", rec
    assert rec["detail"]["mechanism_kind"] == "observed_zero_delta"
    assert rec["detail"]["delta_kind"] == "zero"
    assert "zero-delta repair guard" in rec["title"]
    try:
        ar.select_profile("99999999999")
    except SystemExit:
        pass
    else:  # pragma: no cover - defensive
        raise AssertionError("select_profile must fail closed on unknown runs")


def test_no_gate_or_verdict_was_minted_for_either_run():
    for run in (EXECUTING_RUN_ID, RESUMED_RUN_ID):
        assert not (ROOT / "results" / "audit" / "product" / (
            f"CYCLE_{run}_GATE.json")).exists()
        refs = subprocess.run(
            ["git", "ls-remote", "--heads", "origin",
             f"refs/heads/cycle/core/product/{run}/audit"],
            cwd=str(ROOT), capture_output=True, text=True,
            check=True).stdout
        assert refs == "", f"unexpected /audit ref for {run}"


def test_report_of_record_names_the_mechanism_and_the_route_around():
    text = REPORT.read_text(encoding="utf-8")
    assert EXECUTING_RUN_ID in text
    assert RESUMED_RUN_ID in text
    assert "OBSERVED_ZERO_DELTA_REPAIR" in text
    assert "LEX_ZERO_DELTA_REPAIR" in text
    assert "UNADJUDICATED" in text
    assert "a591bbf8" in text
