"""Cycle 40500024808 (operational resume of 40499737748): what this run claims.

Every assertion here is checked against a committed artifact or the live lane
state; nothing is copied out of the report. The report quotes the diagnosis
artifact, and this module is what keeps that quote from rotting.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EXECUTING_RUN_ID = 40500024808
RESUMED_RUN_ID = 40499737748
PREDECESSOR_RUN_ID = 40493520783
SNAPSHOT_HEAD = "d16c79c1a0c5adcf3d88a15bbeff79e9eb2a60f4"
ACCEPTED_RUN_ID = "CYCLE_40284658455"
ACCEPTED_COMMIT = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"

STATE = ROOT / "state" / "product.json"
REPORT = ROOT / "reports" / "product" / "CYCLE_40500024808.md"
DIAG = ROOT / "results" / "product" / "orchestration" / \
    "CYCLE_40500024808_resume_diagnosis.json"
RAW_RESUMED = ROOT / "results" / "product" / "orchestration" / \
    f"CYCLE_{RESUMED_RUN_ID}_run_jobs_raw.json"
RAW_PRED = ROOT / "results" / "product" / "orchestration" / \
    f"CYCLE_{PREDECESSOR_RUN_ID}_run_jobs_raw.json"
KEY_DIFF = ROOT / "results" / "product" / "orchestration" / \
    "CYCLE_40500024808_state_key_diff.json"


def _state() -> dict:
    return json.loads(STATE.read_text(encoding="utf-8"))


def _diag() -> dict:
    return json.loads(DIAG.read_text(encoding="utf-8"))


def test_the_orchestration_diagnosis_is_committed_and_uses_public_payloads() -> None:
    raw = json.loads(RAW_RESUMED.read_text(encoding="utf-8"))
    assert raw["logs_endpoint_status"] == 403, (
        "the diagnosis may not imply a log-level cause: the logs endpoint is "
        "the reason the cause stays UNOBSERVED")
    team = next(j for j in raw["jobs"] if j["name"] == "team")
    assert team["conclusion"] == "failure"
    assert {j["name"]: j["conclusion"] for j in raw["jobs"]}["audit"] == "skipped"


def test_the_resumed_run_died_before_it_could_do_any_work() -> None:
    """16.0 s is the measured fact that separates this leg from the others."""
    runs = {r["run_id"]: r for r in _diag()["runs"]}
    resumed = runs[str(RESUMED_RUN_ID)]
    assert resumed["failed_step"] == "Run lane cycle"
    assert resumed["exit_code_from_annotations"] == 1
    assert resumed["wrapper_sentinel_annotation"] is False
    assert resumed["run_lane_cycle_seconds"] == 16.0
    assert resumed["slot_selection"]["selected_model"] == "opencode/beam-free"
    # The two full-session runs in the same line are the discriminating control.
    assert runs[str(PREDECESSOR_RUN_ID)]["exit_code_from_annotations"] == 78
    assert runs[str(PREDECESSOR_RUN_ID)]["run_lane_cycle_seconds"] == 2704.0
    assert runs["40491258620"]["exit_code_from_annotations"] == 67
    assert _diag()["recomputed_observations"]["under_30s_failures"] == [
        "40490645980", "40490967419", "40493217504", str(RESUMED_RUN_ID)]


def test_the_classification_is_derived_from_the_evidence_not_hard_coded() -> None:
    """A new run with a new exit code must be able to change the label."""
    from product import streak_slot_diagnosis as ssd
    base = json.loads(RAW_RESUMED.read_text(encoding="utf-8"))
    team = next(j for j in base["jobs"] if j["name"] == "team")

    def entry(run_id: str, exit_code: int | None, seconds: float | None) -> dict:
        return {"run_id": run_id, "exit_code_from_annotations": exit_code,
                "run_lane_cycle_seconds": seconds, "failed_step": "Run lane cycle"}

    fast = [entry("a", 1, 16.0)]
    assert "pre-session child deaths" in ssd._classification(fast)
    zero = [entry("a", 67, 781.0)]
    assert "zero-delta repair guards" in ssd._classification(zero)
    quantum = [entry("a", 78, 2704.0)]
    assert "work-quantum expiries" in ssd._classification(quantum)
    assert ssd._classification([]) == "EMPTY_STREAK"
    # The published artifact carries the derived label for the real chain.
    label = _diag()["classification"]
    assert str(RESUMED_RUN_ID) in label and "pre-session child deaths" in label
    # Duration parsing reads the public payload, and rounds to tenths.
    assert ssd._step_seconds(team, "Run lane cycle") == 16.0
    assert ssd._step_seconds(team, "Persist team snapshot") == 5.0


def test_the_snapshot_is_recorded_as_zero_delta_and_not_as_progress() -> None:
    st = _state()
    blk = st[f"cycle_{EXECUTING_RUN_ID}_operational_resume"]
    assert blk["resumed_run"] == RESUMED_RUN_ID
    assert blk["predecessor_run_id"] == PREDECESSOR_RUN_ID
    assert blk["resumed_snapshot_head"] == SNAPSHOT_HEAD
    assert blk["snapshot_relation"].startswith("ZERO_DURABLE_DELTA")
    assert blk["accepted_this_cycle"] is False
    assert blk["adjudication"].startswith("UNADJUDICATED")
    assert blk["orchestration_failure_of_record"]["step_seconds"] == 16.0
    assert blk["orchestration_failure_of_record"]["log_level_cause"] == "UNOBSERVED"
    assert "NOT proven causation" in blk["orchestration_failure_of_record"][
        "slot_selection"]["association_not_causation"]


def test_the_state_stays_fail_closed_and_the_accepted_pointer_is_intact() -> None:
    st = _state()
    assert int(st["current_cycle_run_id"]) == EXECUTING_RUN_ID
    assert st["direction_version"] == 68
    assert st["continue_recommended"] is True
    for key in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                "ready_for_owner_session", "owner_decision_required"):
        assert st[key] is False, key
    assert st["accepted_run_id"] == ACCEPTED_RUN_ID
    assert st["accepted_commit"] == ACCEPTED_COMMIT
    from product.state_contract import accepted_pointer_evidence
    assert accepted_pointer_evidence(st, ROOT)["problems"] == []
    hits = [h for h in st["run_history"] if str(h.get("run_id")) == str(EXECUTING_RUN_ID)]
    assert len(hits) == 1, "exactly one history entry for this run"


def test_every_evidence_ref_this_run_added_resolves() -> None:
    st = _state()
    added = [
        "results/product/orchestration/CYCLE_40499737748_run_jobs_raw.json",
        "results/product/orchestration/CYCLE_40493520783_run_jobs_raw.json",
        "results/product/orchestration/CYCLE_40500024808_resume_diagnosis.json",
        "results/product/orchestration/CYCLE_40500024808_state_key_diff.json",
        "product/tests/test_cycle_40500024808.py",
        "reports/product/CYCLE_40500024808.md",
    ]
    for ref in added:
        assert ref in st["evidence_refs"], ref
        assert (ROOT / ref).exists(), f"dangling evidence ref: {ref}"
    assert REPORT.is_file()


def test_the_state_register_merge_added_without_losing_anything() -> None:
    before = json.loads(subprocess.run(  # noqa: S603
        ["git", "show", "HEAD:state/product.json"], cwd=str(ROOT),
        capture_output=True, text=True, check=True).stdout)
    after = _state()
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    art = json.loads(KEY_DIFF.read_text(encoding="utf-8"))
    assert art["top_level_keys_removed"] == []
    assert removed == [], f"the restore lost keys: {removed}"
    assert art["top_level_keys_added_by_state_register_restore_apply"] == [
        "cycle_39422322667_vertical_slice_delivery",
        "repair_39048942749_d1_d2_a2",
        "repair_39051003925_f1_f2_f3",
        "repair_39169296466_round1",
        "state_register_restoration_39651573572",
        "state_register_restoration_39674781875",
        "state_register_restoration_39689729561",
        "supersedes_claims",
    ]
    assert art["top_level_keys_added_by_this_cycle"] == [
        f"cycle_{EXECUTING_RUN_ID}_operational_resume"]
    assert set(added) == set(art["top_level_keys_added_by_state_register_restore_apply"]
                             + art["top_level_keys_added_by_this_cycle"])
    assert set(after["verification"]) - set(before["verification"]) == set(
        art["verification_keys_added"])
    assert set(before["verification"]) - set(after["verification"]) == set()


def test_the_register_restore_instrument_still_reports_pass() -> None:
    proc = subprocess.run(  # noqa: S603
        [sys.executable, "product/state_register_restore.py", "--check"],
        cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "state register: PASS" in proc.stdout
