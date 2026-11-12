"""Cycle 43162816979: operational resume of the audit-quantum producer chain.

This is a *diagnosis + re-verification* cycle, not a product-claim cycle.  The
tests pin the public run facts, the committed deltas, the functional routing
delta inherited from 43148316674, the shipped offline vertical slice for this
run, the state bookkeeping, and the honesty boundary (no gate was minted, the
accepted pointer did not move).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

EXECUTING_RUN = "43162816979"
RESUMED_RUN = "43156735934"
PREDECESSOR_RUN = "43148316674"

ACCEPTED_HEAD = "7be4480e"
PREVIOUS_REPORTED_RUN = "43138476983"
SNAPSHOT_HEAD = "85bf9c3f"
PREDECESSOR_HEAD = "e4e79714"

ORCH = ROOT / "results" / "product" / "orchestration"
SLICE = (
    ROOT / "results" / "product" / "offline_slice"
    / f"CYCLE_{EXECUTING_RUN}-rent-default"
)
SMOKE = (
    ROOT / "results" / "product" / "progressive_smoke"
    / f"CYCLE_{EXECUTING_RUN}_progressive_smoke.json"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _git(*args):
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout


def _diagnosis(run_id):
    return _load(ORCH / f"CYCLE_{run_id}_resume_diagnosis.json")


def _raw(run_id):
    return _load(ORCH / f"CYCLE_{run_id}_run_jobs_raw.json")


# --------------------------------------------------------------------------- #
# 1. Public run facts: every run in this chain stopped in the audit quantum.
# --------------------------------------------------------------------------- #

def test_resumed_snapshot_is_team_green_and_audit_quantum():
    raw = _raw(RESUMED_RUN)
    assert raw["fetched_by_run"] == int(EXECUTING_RUN)
    jobs = {job["name"]: job for job in raw["jobs"]}
    assert jobs["team"]["conclusion"] == "success"
    team_steps = {s["name"]: s for s in jobs["team"]["steps"]}
    assert team_steps["Persist team snapshot"]["conclusion"] == "success"
    assert team_steps["Validate active MVP producer state"]["conclusion"] == "success"
    assert jobs["audit"]["conclusion"] == "failure"
    audit_steps = {
        s["name"]: s for s in jobs["audit"]["steps"]
    }
    assert audit_steps["Independent audit"]["conclusion"] == "failure"
    assert audit_steps["Enforce audit scope and read gate"]["conclusion"] == "skipped"
    assert audit_steps["Persist audit snapshot"]["conclusion"] == "skipped"
    assert jobs["integrate"]["conclusion"] == "skipped"

    annotations = [
        row[-1]
        for row in raw["check_run_annotations_by_job_id"][
            str(jobs["audit"]["id"])
        ]["annotations"]
    ]
    assert "LEX_WORK_QUANTUM_EXPIRED seconds=2700 pid=2582" in annotations
    assert "Process completed with exit code 78." in annotations

    diag = _diagnosis(RESUMED_RUN)
    assert diag["orchestration"]["classification"] == (
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    )
    assert diag["orchestration"]["mechanism"]["status"] == (
        "OBSERVED_QUANTUM_EXPIRED"
    )
    assert diag["orchestration"]["mechanism"]["quantum_seconds"] == 2700
    assert diag["orchestration"]["mechanism"]["exit_code"] == 78
    assert diag["orchestration"]["audit"]["independent_audit_step_seconds"] == 2705.0
    assert diag["orchestration"]["audit"]["gate_file_written"] is False
    assert diag["orchestration"]["integrate"]["conclusion"] == "skipped"
    assert diag["durable_delta"]["classification"] == "COMMITTED_DELTA"
    assert diag["durable_delta"]["changed_files"] == 360
    assert diag["durable_delta"]["snapshot_head"].startswith(SNAPSHOT_HEAD)
    assert diag["durable_delta"]["predecessor_head"].startswith(ACCEPTED_HEAD)
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["accepted"] is False


def test_predecessor_run_shares_the_same_audit_quantum_mechanism():
    raw = _raw(PREDECESSOR_RUN)
    jobs = {job["name"]: job for job in raw["jobs"]}
    assert jobs["team"]["conclusion"] == "success"
    assert jobs["audit"]["conclusion"] == "failure"
    assert jobs["integrate"]["conclusion"] == "skipped"
    annotations = [
        row[-1]
        for row in raw["check_run_annotations_by_job_id"][
            str(jobs["audit"]["id"])
        ]["annotations"]
    ]
    assert "LEX_WORK_QUANTUM_EXPIRED seconds=2700 pid=2316" in annotations

    diag = _diagnosis(PREDECESSOR_RUN)
    assert diag["orchestration"]["classification"] == (
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    )
    assert diag["orchestration"]["audit"]["independent_audit_step_seconds"] == 2704.0
    assert diag["durable_delta"]["classification"] == "COMMITTED_DELTA"
    assert diag["durable_delta"]["changed_files"] == 355
    assert diag["durable_delta"]["snapshot_head"].startswith(PREDECESSOR_HEAD)
    assert diag["durable_delta"]["predecessor_head"].startswith(ACCEPTED_HEAD)


@pytest.mark.parametrize("run_id", [RESUMED_RUN, PREDECESSOR_RUN])
def test_diagnoses_are_content_hashed_to_their_raw(run_id):
    import hashlib

    raw_path = ORCH / f"CYCLE_{run_id}_run_jobs_raw.json"
    diag = _diagnosis(run_id)
    assert diag["raw_snapshot_sha256"] == hashlib.sha256(
        raw_path.read_bytes()
    ).hexdigest()
    assert diag["adjudication"]["audit"]["audit_ref_present"] is False
    assert diag["adjudication"]["audit"]["gate_file_present"] is False
    assert diag["adjudication"]["product_defect"] is False


# --------------------------------------------------------------------------- #
# 2. Committed deltas: the snapshot only adds caches over its predecessor.
# --------------------------------------------------------------------------- #

def test_snapshot_delta_over_predecessor_is_query_cache_only():
    names = _git(
        "diff", "--name-only", PREDECESSOR_HEAD, SNAPSHOT_HEAD
    ).splitlines()
    assert len(names) == 5
    assert all(
        name.startswith("results/product/query_cache/") for name in names
    )


def test_predecessor_delta_contains_the_span_routing_seam():
    names = set(_git(
        "diff", "--name-only", ACCEPTED_HEAD, PREDECESSOR_HEAD
    ).splitlines())
    assert "product/query/pipeline.py" in names
    assert "product/query/progressive.py" in names


# --------------------------------------------------------------------------- #
# 3. The routing delta is functional at both entry points today.
# --------------------------------------------------------------------------- #

def test_both_query_entry_points_route_the_verified_span_seam():
    from product.query import run_query_first_page, run_query_initial

    for bundle in (
        run_query_initial(
            "Kündigung Mietvertrag Mietrecht", top_n=40, retrieval_mode="fixture"
        ),
        run_query_first_page(
            "Kündigung Mietvertrag Mietrecht", top_n=40, retrieval_mode="fixture"
        ),
    ):
        prov = bundle["provenance"]["counter_evidence_span"]
        assert prov["applied"] is True
        assert prov["mode"] == "select"
        assert "verified verbatim" in prov["claim_ceiling"]
        surface = bundle["provenance"].get("counter_evidence_span_surface")
        if surface is not None:
            assert surface["geometry_touched"] is False
            assert surface["stage_1_provenance_block"] == (
                "provenance.counter_evidence_span (unchanged)"
            )


# --------------------------------------------------------------------------- #
# 4. Shipped offline vertical slice for this run: sound verified counters.
# --------------------------------------------------------------------------- #

def test_offline_slice_is_a_sound_clickable_map_with_sourced_counters():
    from product.query.bundle import validate_bundle
    from product.query.counter_evidence_span import frozen_content_defects

    payload = _load(SLICE / "rent-default.bundle.json")
    summary = _load(SLICE / "summary.json")
    assert validate_bundle(payload) == []
    assert len(payload["decisions"]) == 150
    assert len(payload["clusters"]) == 8

    for decision in payload["decisions"]:
        assert decision["cluster_id"] is not None
        assert decision["x"] is not None and decision["y"] is not None
        assert decision["canonical_url"].startswith("https://")

    answer = payload["answer"]
    assert answer["status"] == "ready"
    assert answer["method"] == "generative_audit_llm_v2"
    assert len(answer["cited_decision_ids"]) == 5

    provenance = payload["provenance"]
    stage1 = provenance["counter_evidence_span"]
    stage2 = provenance["counter_evidence_span_surface"]
    assert stage1["applied"] is True and stage1["mode"] == "select"
    assert stage1["n_candidates"] == 1 and stage1["n_selected"] == 0
    assert stage1["n_abstained"] == 1
    assert stage2["applied"] is True
    assert stage2["n_candidates"] == 12 and stage2["n_selected"] == 1
    assert stage2["n_abstained"] == 11

    verified = [
        d for d in payload["decisions"]
        if d.get("counter_evidence_verified") is True
    ]
    assert len(verified) == 2
    assert summary["stats"]["counter_rows"] == 2
    for decision in verified:
        assert decision["counter_evidence"].strip()
        assert frozen_content_defects(decision["counter_evidence"], decision) == []

    assert provenance["offline_slice"]["geometry_preserved"] is True
    assert provenance["offline_slice"]["network"] == "none"
    assert summary["stats"]["fixture_replay"]["network"] == "none"
    assert summary["stats"]["geometry_preserved_by_enrich"] is True
    assert summary["stats"]["rows_with_source_link"] == 150
    assert summary["verified"] is True
    assert summary["page_contract"] is True


# --------------------------------------------------------------------------- #
# 5. Progressive smoke and state bookkeeping.
# --------------------------------------------------------------------------- #

def test_progressive_smoke_for_this_cycle_is_green():
    smoke = _load(SMOKE)
    assert smoke["run_id"] == EXECUTING_RUN
    assert smoke["verdict"] == "PASS"
    assert smoke["failures"] == []
    assert smoke["checks_passed"] == smoke["checks_total"] == 23
    assert all(check["ok"] for check in smoke["checks"])
    assert smoke["timings_s"]["start_s"] < 2.0


def test_state_records_this_cycle_without_moving_the_accepted_pointer():
    state = _load(ROOT / "state" / "product.json")
    # Later cycles legitimately advance the pointer; only a regression below
    # this cycle's executing run would falsify this record.
    assert state["current_cycle_run_id"] >= int(EXECUTING_RUN), (
        "current_cycle_run_id regressed below this cycle's executing run")
    assert state["direction_version"] == 68
    assert state["human_gate_ready"] is False
    assert state["machine_gate_ready"] is False
    assert state["packet_admitted"] is False
    assert state["continue_recommended"] is True

    assert state["accepted_run_id"] == "CYCLE_40284658455"
    assert state["accepted_commit"].startswith(ACCEPTED_HEAD)

    rows = {row["run_id"]: row for row in state["run_history"]}
    for run_id in (int(PREDECESSOR_RUN), int(RESUMED_RUN), int(EXECUTING_RUN)):
        assert run_id in rows

    block = state["cycle_43162816979_operational_resume"]
    assert block["resumed_run_id"] == int(RESUMED_RUN)
    assert block["predecessor_run_id"] == int(PREDECESSOR_RUN)
    assert block["accepted_head"].startswith(ACCEPTED_HEAD)
    assert block["audit_gate"] == "NONE_ON_ANY_REF"
    assert block["gate_minted"] is False
    assert block["accepted_pointer_unchanged"] is True
    assert block["verdict"] == "PROPOSED"
    assert block["direction_version"] == 68
    assert block["offline_slice"]["n_decisions"] == 150
    assert block["offline_slice"]["n_verified_counters"] == 2
    assert block["offline_slice"]["n_verified_defective"] == 0


def test_report_states_the_claim_ceiling_and_the_chain():
    report = (
        ROOT / "reports" / "product" / f"CYCLE_{EXECUTING_RUN}.md"
    ).read_text(encoding="utf-8")
    for token in (
        RESUMED_RUN,
        PREDECESSOR_RUN,
        EXECUTING_RUN,
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE",
        "UNADJUDICATED",
        "PROPOSED",
        "NONE_ON_ANY_REF",
        "generative_audit_llm_v2",
        "OFFLINE WIRING EVIDENCE ONLY",
    ):
        assert token in report
    assert "no gate was minted" in report.lower()
