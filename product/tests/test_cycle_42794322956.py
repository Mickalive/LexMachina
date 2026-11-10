"""Cycle 42794322956: resume of zero-delta snapshot 42793313084.

These tests pin, against the committed bytes, what this cycle claims:

1. the snapshot's orchestration diagnosis is reproducible from the committed
   raw run/jobs+annotation snapshot (lane-cycle exit 67 with the public
   ``LEX_ZERO_DELTA_REPAIR`` annotation, state-validation/write-scope skipped,
   always-run persist step published the predecessor's exact tree, no gate);
2. the offline replay fallback turns the frozen French questions into full
   query_result_bundles without a network (the pre-fix exact-cache miss raised
   ``RuntimeError: OpenCaseLaw retrieval returned no decisions``);
3. the audit-readiness module carries a profile for BOTH the snapshot run and
   this run, and the diagnosis' zero-delta mechanism is a first-class kind;
4. state hygiene: ``current_cycle_run_id`` names this run, the chain runs are
   in ``run_history``, the accepted pointer is untouched and every fail-closed
   posture flag stays FALSE with ``continue_recommended`` true.

No frozen bar, rubric, threshold, verdict contract or audit namespace is
touched; this test writes nothing outside pytest's own output.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "product"
for _p in (str(PRODUCT), str(ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, str(_p))

RAW = ROOT / "results/product/orchestration/CYCLE_42793313084_run_jobs_raw.json"
DIAG = ROOT / "results/product/orchestration/CYCLE_42793313084_resume_diagnosis.json"
SLICES = ROOT / "results/product/offline_slice/CYCLE_42794322956"
STATE = ROOT / "state/product.json"
REPORT = ROOT / "reports/product/CYCLE_42794322956.md"
PIPELINE = PRODUCT / "query/pipeline.py"
SLICE_RUNNER = PRODUCT / "run_frozen_offline_slices.py"


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_raw_snapshot_pins_the_snapshot_orchestration_facts():
    raw = _load(RAW)
    assert raw["schema"] == "product-run-jobs-snapshot/1"
    assert raw["fetched_by_run"] == 42794322956
    assert raw["run"]["id"] == 42793313084
    assert raw["run"]["conclusion"] == "failure"
    jobs = {j["name"]: j for j in raw["jobs"]}
    steps = {s["name"]: s["conclusion"] for s in jobs["team"]["steps"]}
    assert steps["Run lane cycle"] == "failure"
    assert steps["Validate active MVP producer state"] == "skipped"
    assert steps["Enforce lane write scope"] == "skipped"
    assert steps["Persist team snapshot"] == "success"
    assert jobs["audit"]["conclusion"] == "skipped"
    assert jobs["integrate"]["conclusion"] == "skipped"
    ann = raw["check_run_annotations_by_job_id"][str(jobs["team"]["id"])]
    messages = [row["message"] for row in ann]
    assert any("LEX_ZERO_DELTA_REPAIR" in m for m in messages)
    assert any("exit code 67" in m for m in messages)
    # the seven-run chain is on the record.  ``runs[*].head_sha`` is the
    # workflow dispatch sha on main, not the team ref; the durable tree is
    # pinned by the diagnosis' git-ref delta, so the raw test only pins the
    # chain membership and the public annotations.
    chain = raw["runs"]
    assert "42792990432" in chain and "42782011364" in chain
    assert len(chain) == 7
    by_run = {row["run_id"]: row for row in raw["chain_of_record"]}
    assert by_run[42790448478]["jobs"]["team"]["annotations"][1] == \
        "LEX_ZERO_DELTA_REPAIR"
    assert by_run[42782011364]["jobs"]["audit"]["conclusion"] == "failure"
    assert any("LEX_WORK_QUANTUM_EXPIRED seconds=2700 pid=2592" in m
               for m in by_run[42782011364]["jobs"]["audit"]["annotations"])
    assert by_run[42793313084]["jobs"]["team"]["annotations"][1] == \
        "LEX_ZERO_DELTA_REPAIR"


def test_raw_snapshot_reclassifies_to_the_committed_diagnosis():
    """The committed diagnosis must be reproducible from the committed raw."""
    import audit_step_diagnosis as asd

    cls = asd.classify(_load(RAW))
    diag = _load(DIAG)["orchestration"]
    assert cls["classification"] == diag["classification"]
    assert cls["mechanism"]["status"] == "OBSERVED_ZERO_DELTA_GUARD"
    assert cls["mechanism"]["zero_delta_repair"] is True
    assert cls["mechanism"]["exit_code"] == 67
    assert cls["mechanism"]["quantum_expired"] is False
    assert cls["observed_failure"]["zero_delta_message"] == \
        "LEX_ZERO_DELTA_REPAIR"


def test_diagnosis_is_consistent_with_raw_and_the_profile():
    diag = _load(DIAG)
    raw = _load(RAW)
    assert diag["schema"] == "product-resume-snapshot-diagnosis/1"
    assert diag["run_id"] == "42793313084"
    assert diag["predecessor_run_id"] == "42792990432"
    assert diag["raw_snapshot_sha256"] == _sha(RAW)
    orch = diag["orchestration"]
    assert orch["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    mech = orch["mechanism"]
    assert mech["status"] == "OBSERVED_ZERO_DELTA_GUARD"
    assert mech["zero_delta_repair"] is True
    assert mech["exit_code"] == 67
    assert mech["quantum_expired"] is False
    assert orch["team"]["failed_step"] == "Run lane cycle"
    assert orch["audit"]["conclusion"] == "skipped"
    assert orch["audit"]["gate_file_written"] is False
    delta = diag["durable_delta"]
    assert delta["classification"] == "ZERO_DURABLE_DELTA"
    assert delta["changed_files"] == 0
    assert delta["snapshot_head"] == delta["predecessor_head"]
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["accepted"] is False

    import audit_readiness as ar
    snap = ar.select_profile("42793313084")
    cur = ar.select_profile("42794322956")
    assert snap["resumed_run_id"] == "42793313084"
    assert snap["predecessor_run_id"] == diag["predecessor_run_id"]
    assert snap["mechanism_kind"] == "observed_zero_delta"
    assert snap["delta_kind"] == "zero"
    assert snap["exit_code"] == mech["exit_code"]
    assert cur == snap
    assert Path(snap["current_report"]) == REPORT
    assert Path(snap["cycle_test"]).is_file()


def test_offline_frozen_question_slices_are_complete_and_network_free():
    summary = _load(SLICES / "summary.json")
    assert summary["run_id"] == "42794322956"
    assert summary["mode"] == "offline"
    assert summary["all_ok"] is True
    assert len(summary["slices"]) == 4
    for row in summary["slices"]:
        assert row["ok"] is True
        assert row["n_decisions"] >= 100
        assert row["n_clusters"] >= 2
        assert row["n_counter_authorities"] >= 1
        assert row["n_answer_citations"] >= 1
        assert row["answer_citations_closed"] is True
        assert row["rows_with_source_link"] == row["n_decisions"]
        assert "socket.connect trapped" in row["network"]
        assert row["validation_errors"] == []
    # the pre-fix exact-cache miss is the reason the fallback exists
    by_slug = {row["slug"]: row for row in summary["slices"]}
    assert by_slug["rent-default"]["replay_source"] == \
        "product_query_cache_question_match_replay"
    assert by_slug["rent-default"]["question_match"]["exact_hits"] == 0
    assert by_slug["rent-default"]["question_match"]["question_matches"] > 0

    bundle = _load(SLICES / "rent-default.bundle.json")
    assert bundle["bundle_version"]
    assert len(bundle["decisions"]) == by_slug["rent-default"]["n_decisions"]
    assert len(bundle["clusters"]) == by_slug["rent-default"]["n_clusters"]
    cited = set(bundle["answer"]["cited_decision_ids"])
    retrieved = {d["decision_id"] for d in bundle["decisions"]}
    assert cited <= retrieved and cited
    assert bundle["provenance"]["mode"] == "offline"

    assert PIPELINE.is_file() and SLICE_RUNNER.is_file()
    assert "_question_match_replay" in PIPELINE.read_text(encoding="utf-8")
    assert "product_offline_replay" in PIPELINE.read_text(encoding="utf-8")


def test_state_hygiene_and_posture():
    st = _load(STATE)
    assert st["current_cycle_run_id"] == 42794322956
    block = st["cycle_42794322956_operational_resume"]
    assert block["run_id"] == 42794322956
    assert block["resumed_run"] == "42793313084"
    assert block["direction_version"] == 68
    assert block["orchestration_failure_of_record"]["classification"] == \
        "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    history = {row["run_id"]: row for row in st["run_history"]}
    for run_id in (42781684618, 42782011364, 42790448478, 42792235162,
                   42792579346, 42792990432, 42793313084, 42794322956):
        assert run_id in history, run_id
    assert st["accepted_run_id"] == "CYCLE_40284658455"
    assert st["accepted_commit"] == \
        "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
    assert st["continue_recommended"] is True
    for flag in ("human_gate_ready", "machine_gate_ready",
                 "packet_admitted", "ready_for_owner_session"):
        assert st[flag] is False, flag
