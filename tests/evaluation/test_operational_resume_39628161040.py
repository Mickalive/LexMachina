"""Tests for the run-39628161040 operational-resume verification.

Standard-library only, plain zero-argument ``test_*`` functions: runnable under
pytest AND under the lane's no-pytest shim (evaluation/no_pytest_runner.py).

These tests assert identity pins, the frozen reproduction, state provenance and
snapshot hygiene.  They re-derive no threshold and assert nothing about the
legal status of any decision.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "evaluation"))

import operational_resume_39628161040 as resume  # noqa: E402


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _record():
    return load(REPO / resume.OUT_RELPATH)


def _hygiene():
    return _record()["snapshot_hygiene"]


# --------------------------------------------------------------------------- #
# freeze-first
# --------------------------------------------------------------------------- #
def test_freeze_record_present_and_declares_before_execution():
    freeze = load(REPO / resume.FREEZE_RELPATH)
    assert freeze["frozen_before_this_run_executed_any_claim_bearing_measurement"]
    assert freeze["run_id"] == resume.RUN_ID
    assert freeze["resumed_snapshot_run_id"] == resume.SNAPSHOT_RUN_ID


def test_freeze_pins_the_original_hypothesis():
    freeze = load(REPO / resume.FREEZE_RELPATH)
    assert (freeze["reproduction_target"]["frozen_hypothesis_sha256"]
            == sha256_file(REPO / resume.HYPOTHESIS_RELPATH))


def test_all_frozen_pins_still_hold():
    freeze = load(REPO / resume.FREEZE_RELPATH)
    pins = resume.check_pins(freeze)
    assert pins["all_hold"], pins


def test_producer_record_is_not_overwritten():
    freeze = load(REPO / resume.FREEZE_RELPATH)
    assert (sha256_file(REPO / resume.PRODUCER_RECORD_RELPATH)
            == freeze["reproduction_target"]["producer_record_sha256"])


# --------------------------------------------------------------------------- #
# reproduction
# --------------------------------------------------------------------------- #
def test_lane_record_has_its_own_run_id():
    producer = load(REPO / resume.PRODUCER_RECORD_RELPATH)
    lane = load(REPO / resume.LANE_RECORD_RELPATH)
    assert lane["run_id"] == resume.RUN_ID
    assert producer["run_id"] == resume.PRODUCER_RUN_ID


def test_zero_divergence_and_headline():
    comparison = resume.compare_records(
        load(REPO / resume.PRODUCER_RECORD_RELPATH),
        load(REPO / resume.LANE_RECORD_RELPATH))
    assert comparison["n_divergent"] == 0
    assert comparison["headline"].startswith("ZERO_DIVERGENCE_ACROSS_")
    assert comparison["n_comparable"] == comparison["n_match"]


def test_verdict_and_falsifier_gates_reproduce():
    producer = load(REPO / resume.PRODUCER_RECORD_RELPATH)
    lane = load(REPO / resume.LANE_RECORD_RELPATH)
    assert lane["verdict"] == "FAIL_PRODUCT_CACHE_PARITY"
    assert lane["exit_code"] == 1
    assert lane["falsification_gates"] == producer["falsification_gates"]
    assert len(lane["falsification_gates"]) == 7


def test_non_vacuity_and_v3_leg_reproduce():
    lane = load(REPO / resume.LANE_RECORD_RELPATH)
    assert lane["non_vacuity"]["all_hold"] is True
    assert (lane["v3_multilingual_provenance_reuse"]["verdict"]
            == "PARTIAL_MISS")


def test_comparison_is_deterministic():
    comparison = resume.compare_records(
        load(REPO / resume.PRODUCER_RECORD_RELPATH),
        load(REPO / resume.LANE_RECORD_RELPATH))
    again = resume.compare_records(
        load(REPO / resume.PRODUCER_RECORD_RELPATH),
        load(REPO / resume.LANE_RECORD_RELPATH))
    assert (json.dumps(again, sort_keys=True)
            == json.dumps(comparison, sort_keys=True))


# --------------------------------------------------------------------------- #
# snapshot hygiene
# --------------------------------------------------------------------------- #
def test_only_two_out_of_scope_paths_and_both_labelled():
    hygiene = _hygiene()
    paths = sorted(e["path"] for e in hygiene["out_of_scope"])
    assert paths == [
        "reports/audit/evaluation/CYCLE_39626323381.md",
        "results/audit/evaluation/CYCLE_39626323381_GATE.json",
    ]
    for entry in hygiene["out_of_scope"]:
        assert entry["label"] == resume.OUT_OF_SCOPE_LABEL
        assert len(entry["sha256_working_tree"]) == 64


def test_out_of_scope_files_are_not_deleted():
    for entry in _hygiene()["out_of_scope"]:
        assert (REPO / entry["path"]).is_file(), entry["path"]


def test_in_scope_delta_is_only_state():
    assert [e["path"] for e in _hygiene()["in_scope"]] == [
        "state/evaluation.json"]


def test_all_changed_paths_accounted_for():
    hygiene = _hygiene()
    assert hygiene["all_accounted"]
    assert hygiene["this_cycle_writes_outside_scope"] is False


# --------------------------------------------------------------------------- #
# state provenance
# --------------------------------------------------------------------------- #
def test_run_ids_are_attributed_to_their_producers():
    state = load(REPO / resume.STATE_RELPATH)
    # benchmark_result is the minimal-CA benchmark, produced/verified by 39471603258
    assert state["benchmark_result"]["run_id"] == "39471603258"
    # the product-cache parity falsifier names its producer and reproduction
    assert state["product_cache_parity"]["run_id"] == resume.PRODUCER_RUN_ID
    assert (state["product_cache_parity"]["reproduction_run_id"]
            == resume.RUN_ID)
    assert state["multilingual_provenance_reuse"]["run_id"] == "39471603258"
    assert state["accepted_run_id"] == "39581086634"


def test_fail_closed_flags_stay_false():
    state = load(REPO / resume.STATE_RELPATH)
    record = _record()
    for key in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                "ready_for_owner_session", "owner_decision_required"):
        assert state[key] is False, key
        assert record["state_flags"][key] is False, key


def test_do_not_serve_orders_stand():
    state = load(REPO / resume.STATE_RELPATH)
    assert _record()["state_flags"]["do_not_serve_orders_stand"] is True
    assert state["standing_orders_confirmed"]["do_not_serve_38839347028"] is True
    assert (state["standing_orders_confirmed"][
        "do_not_serve_unchanged_rebuilt_39027045675"] is True)


def test_state_provenance_verifier_holds():
    assert resume.state_provenance()["all_hold"]


# --------------------------------------------------------------------------- #
# orchestration diagnosis
# --------------------------------------------------------------------------- #
def test_producer_failed_in_the_agent_step():
    diag = _record()["orchestration"]["runs"]
    failed = diag[resume.PRODUCER_RUN_ID]["failed_steps"]
    assert {"job": "team", "step": "Run lane cycle", "number": 6} in failed
    assert diag[resume.PRODUCER_RUN_ID]["audit_conclusion"] == "skipped"


def test_failed_resume_failed_the_scope_guard():
    diag = _record()["orchestration"]["runs"]
    failed = diag[resume.SNAPSHOT_RUN_ID]["failed_steps"]
    assert {"job": "team", "step": "Enforce lane write scope",
            "number": 9} in failed


def test_job_evidence_is_retained():
    ev = load(REPO / resume.JOB_EVIDENCE_RELPATH)
    for rid in (resume.PRODUCER_RUN_ID, resume.SNAPSHOT_RUN_ID):
        assert rid in ev["runs"]


# --------------------------------------------------------------------------- #
# committed verification record
# --------------------------------------------------------------------------- #
def test_verdict_and_exit():
    record = _record()
    assert record["verdict"] == "RESUME_VERIFIED_AND_REPAIRED"
    assert record["exit_code"] == 0


def test_pins_and_mount_hold():
    record = _record()
    assert record["pins"]["all_hold"]
    assert record["product_mount"]["all_hold"]


def test_claim_ceiling_forbids_owner_and_bar_claims():
    ceiling = _record()["claim_ceiling"]
    for needle in ("authorises NO owner question",
                   "does NOT lift either DO-NOT-SERVE order",
                   "REPORTED-ONLY", "never a pass"):
        assert needle in ceiling
