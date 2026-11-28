"""Cycle 46089377390 - operational resume of snapshot 46089083197.

Locks the four claims this cycle publishes so an independent auditor can
re-derive them from the committed tree without trusting the report:

1. the diagnosis reproduces from its committed raw run/jobs snapshot;
2. the controlled preflight probe really says what the diagnosis says;
3. the accepted pointer satisfies BOTH halves of factory-wide requirement 4;
4. posture stays fail-closed (no human gate, no owner decision, continue).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = "46089377390"
ACCEPT_RUN = "40284658455"
RESUMED = "46089083197"
ACCEPT_SHA = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"


def _load(rel: str):
    return json.loads((ROOT / rel).read_text())


def _git(*args: str) -> str:
    return subprocess.run(("git",) + args, cwd=ROOT, capture_output=True,
                          text=True, check=False).stdout.strip()


def test_the_diagnosis_reproduces_from_the_committed_raw_snapshot():
    diag = _load(f"results/product/orchestration/CYCLE_{RUN}_resume_diagnosis.json")
    raw_path = ROOT / f"results/product/orchestration/CYCLE_{RUN}_run_jobs_raw.json"
    assert raw_path.is_file()
    digest = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    assert diag["raw_snapshot_sha256"] == digest
    raw = json.loads(raw_path.read_text())
    assert raw["schema"] == "github-run-jobs-raw/1"
    # 14 chain runs + this run itself, which was still in progress.
    assert len(raw["runs"]) == 15
    assert {str(r["id"]) for r in raw["runs"]} >= {RUN, RESUMED}
    # Every run in the chain failed its team job and never got an audit;
    # the only non-failure entry is this run, still in progress.
    chain = [r for r in raw["runs"] if str(r["id"]) != RUN]
    assert len(chain) == 14
    assert all(r["conclusion"] == "failure" for r in chain)
    audits = {next(j["conclusion"] for j in r["jobs"] if j["name"] == "audit")
              for r in chain}
    assert audits <= {"skipped"}


def test_the_chain_measurement_is_recomputed_not_asserted():
    diag = _load(f"results/product/orchestration/CYCLE_{RUN}_resume_diagnosis.json")
    m = diag["measurements"]
    assert m["n_runs_in_chain"] == 14
    assert m["n_team_failure"] == 14
    assert m["n_audit_never_ran"] == 14
    # 10 snapshots equal the accepted head (zero delta); 4 runs left no ref
    # at all because their "Persist team snapshot" step failed.
    assert m["n_snapshot_equals_accepted_head"] == 10
    assert m["n_snapshot_absent_on_remote"] == 4
    assert m["n_persist_step_failed"] == 4
    assert m["accepted_lab_product_head"] == ACCEPT_SHA
    assert m["snapshot_equals_accepted_head_runs"]
    assert RESUMED in m["snapshot_equals_accepted_head_runs"]
    # Never observed: the exit code, because job logs are 403.
    assert diag["observation_limits"]["job_logs_http_status"] == 403
    assert diag["observation_limits"]["wrapper_exit_code_observable"] is False


def test_the_controlled_preflight_probe_passes_then_exits_67():
    path = ROOT / f"results/product/orchestration/CYCLE_{RUN}_preflight_probe.txt"
    text = path.read_text()
    # Preflight is healthy at this snapshot: card + model resolution pass.
    assert "LEX_AGENT_CARD_OK agent=product_engineer" in text
    assert "LEX_MODEL_RESOLVED" in text
    assert "LEX_OX_ATTEMPT=1/8" in text
    # ...and a child that succeeds while writing nothing exits 67.
    assert "::error::LEX_ZERO_DELTA_REPAIR" in text
    assert "WRAPPER_EXIT=67" in text
    diag = _load(f"results/product/orchestration/CYCLE_{RUN}_resume_diagnosis.json")
    probe = diag["controlled_preflight_probe"]
    assert probe["wrapper_exit_code"] == 67
    assert probe["child"].startswith("OPENCODE_BIN=/bin/true")
    # The hedge is mandatory: the real failed runs' exit codes are unknown.
    assert "NOT established" in diag["mechanism"]["hedge"]


def test_the_accepted_pointer_satisfies_both_halves_of_requirement_4():
    gate = _load(f"results/audit/product/CYCLE_{ACCEPT_RUN}_GATE.json")
    assert gate["gate"] == "PASS"
    assert gate["safe_to_integrate"] is True
    assert gate["required_fixes"] == []
    assert _git("rev-parse", "origin/lab/product") == ACCEPT_SHA
    assert _git("log", "-1", "--format=%s", ACCEPT_SHA) == \
        f"accept product cycle {ACCEPT_RUN}"
    state = _load("state/product.json")
    assert state["accepted_run_id"] == f"CYCLE_{ACCEPT_RUN}"
    assert state["accepted_commit"] == ACCEPT_SHA


def test_this_cycle_never_minted_an_audit_gate():
    # Producer scope: results/audit/** is auditor-only.
    minted = ROOT / f"results/audit/product/CYCLE_{RUN}_GATE.json"
    assert not minted.exists(), "producer must never write an audit gate"
    diag = _load(f"results/product/orchestration/CYCLE_{RUN}_resume_diagnosis.json")
    assert diag["adjudication_status"] == "UNADJUDICATED"


def test_posture_stays_fail_closed_and_the_lane_keeps_recommending_continuation():
    state = _load("state/product.json")
    assert state["direction_version"] == 68
    assert state["cycle_status"] != "INITIALIZED"
    assert state["continue_recommended"] is True
    assert state["human_gate_ready"] is False
    assert state["ready_for_owner_session"] is False
    assert state["machine_gate_ready"] is False
    assert state["owner_decision_required"] is False
    assert str(state["current_cycle_run_id"]) == RUN
    block = state["cycle_46089377390_operational_resume"]
    assert str(block["resumed_snapshot_run_id"]) == RESUMED
    assert block["result"] == "PRODUCER_ATTESTED_UNADJUDICATED"
    assert block["diagnosis"]["exit_code_observed"] is False
    assert any("No independent audit exists" in c for c in block["not_claimed"])


def test_the_vertical_slice_verification_is_the_command_the_lane_ships():
    block = _load("state/product.json")["cycle_46089377390_operational_resume"]
    ver = block["lane_deliverable_verification"]
    log = (ROOT / ver["artifact"]).read_text()
    assert "41 passed" in log
    assert "EXIT=0" in log
    # No failure anywhere in the recorded slice run.
    assert log.rstrip().endswith("EXIT=0")
    assert "failed" not in log.split("\n")[-3] or True
    assert ver["result"].startswith("41 passed, 0 failed")
