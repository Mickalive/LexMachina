"""Cycle 43138476983: operational resume of snapshot 43134567769.

Run 43134567769 was a producer reset from ``lab/product`` that the workflow's
own zero-delta guard rejected (``LEX_ZERO_DELTA_REPAIR``, exit 67) after ~34
minutes: it re-published the predecessor's exact tree, so the snapshot carried
no durable delta. Its predecessor 43124268728 had a fully green team job with a
one-file helper but its independent audit consumed the whole 2700 s work
quantum (``LEX_WORK_QUANTUM_EXPIRED``, exit 78) before any gate.

While resuming, this cycle found that a real 310-file producer snapshot
(``8fd1b421``, run 42996172250) had been stranded by subsequent zero-delta
resets: 191 ``cycle/core/product/4309*`` team refs all point at it, and its
public run record is pruned (HTTP 404). This cycle restores that lineage into
the resumed snapshot and reverts the predecessor's unverified mtime-based
bundle substitution.

These tests pin, against the committed bytes:

1. snapshot 43134567769's zero-delta/exit-67 orchestration facts, and that its
   durable delta is proven ZERO from the two team refs;
2. predecessor 43124268728's audit-quantum/exit-78 failure and its one-file
   delta (the helper this cycle reverts);
3. the stranded 42996172250 lineage's 310-file committed delta, its
   raw-unavailable/UNOBSERVED mechanism, and that it is now an ancestor of HEAD;
4. the helper's absence, so the accepted fixture-replay measurement path is
   what ships;
5. the restored vertical slice's committed bundles and this cycle's smoke;
6. state hygiene: rows for the chain and this cycle, the resume state block,
   unchanged accepted pointer and fail-closed posture.

No frozen bar, rubric, threshold, serve verdict or audit namespace is touched;
this test writes nothing outside pytest's own output.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "product"
for _p in (str(PRODUCT), str(ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, str(_p))

ORCH = ROOT / "results/product/orchestration"
STATE = ROOT / "state/product.json"
REPORT = ROOT / "reports/product/CYCLE_43138476983.md"
SMOKE = ROOT / "results/product/progressive_smoke" / (
    "CYCLE_43138476983_progressive_smoke.json")

EXECUTING = 43138476983
RESUMED = 43134567769
PREDECESSOR = 43124268728
STRANDED = 42996172250

SNAPSHOT_HEAD = "ebf58be988f85feae9a4b6c00b08e46f015e0558"
STRANDED_HEAD = "8fd1b421ae702af81e5039546daa072775bd675d"
ACCEPTED_HEAD = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _diag(run_id: int) -> dict:
    return _load(ORCH / f"CYCLE_{run_id}_resume_diagnosis.json")


def _raw(run_id: int) -> dict:
    return _load(ORCH / f"CYCLE_{run_id}_run_jobs_raw.json")


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(ROOT),
                          capture_output=True, text=True, check=False)


def test_43134567769_is_zero_delta_and_the_guard_is_observed():
    raw = _raw(RESUMED)
    assert raw["schema"] == "product-run-jobs-raw/2"
    assert raw["fetched_by_run"] == EXECUTING
    assert raw["run"]["id"] == RESUMED
    assert raw["run"]["conclusion"] == "failure"
    jobs = {j["name"]: j for j in raw["jobs"]}
    assert len(raw["jobs"]) == 4
    steps = {s["name"]: s["conclusion"] for s in jobs["team"]["steps"]}
    assert jobs["team"]["conclusion"] == "failure"
    assert steps["Run lane cycle"] == "failure"
    assert steps["Validate active MVP producer state"] == "skipped"
    assert steps["Enforce lane write scope"] == "skipped"
    assert steps["Persist team snapshot"] == "success"
    assert jobs["audit"]["conclusion"] == "skipped"
    assert jobs["integrate"]["conclusion"] == "skipped"
    assert jobs["resilience"]["conclusion"] == "success"

    block = raw["check_run_annotations_by_job_id"][str(jobs["team"]["id"])]
    messages = [row[-1] for row in block["annotations"]]
    assert any("LEX_ZERO_DELTA_REPAIR" in m for m in messages)
    assert any("exit code 67" in m for m in messages)

    diag = _diag(RESUMED)
    assert diag["run_id"] == str(RESUMED)
    assert diag["predecessor_run_id"] == str(PREDECESSOR)
    orch = diag["orchestration"]
    assert orch["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    mechanism = orch["mechanism"]
    assert mechanism["status"] == "OBSERVED_ZERO_DELTA_GUARD"
    assert mechanism["zero_delta_repair"] is True
    assert mechanism["exit_code"] == 67
    assert mechanism["quantum_expired"] is False
    assert orch["audit"]["gate_file_written"] is False
    delta = diag["durable_delta"]
    assert delta["classification"] == "ZERO_DURABLE_DELTA"
    assert delta["changed_files"] == 0
    assert delta["snapshot_head"] == SNAPSHOT_HEAD
    assert delta["snapshot_head"] == delta["predecessor_head"]
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["accepted"] is False
    assert diag["raw_snapshot_sha256"] == hashlib.sha256(
        (ORCH / f"CYCLE_{RESUMED}_run_jobs_raw.json").read_bytes()).hexdigest()


def test_predecessor_audit_quantum_and_one_file_delta():
    raw = _raw(PREDECESSOR)
    jobs = {j["name"]: j for j in raw["jobs"]}
    team_steps = {s["name"]: s["conclusion"] for s in jobs["team"]["steps"]}
    assert jobs["team"]["conclusion"] == "success"
    assert team_steps["Run lane cycle"] == "success"
    assert team_steps["Validate active MVP producer state"] == "success"
    assert team_steps["Enforce lane write scope"] == "success"
    assert team_steps["Persist team snapshot"] == "success"

    audit_steps = {s["name"]: s["conclusion"] for s in jobs["audit"]["steps"]}
    assert jobs["audit"]["conclusion"] == "failure"
    assert audit_steps["Independent audit"] == "failure"
    assert audit_steps["Enforce audit scope and read gate"] == "skipped"
    assert audit_steps["Persist audit snapshot"] == "skipped"
    assert jobs["integrate"]["conclusion"] == "skipped"

    block = raw["check_run_annotations_by_job_id"][str(jobs["audit"]["id"])]
    messages = [row[-1] for row in block["annotations"]]
    assert any("LEX_WORK_QUANTUM_EXPIRED seconds=2700" in m for m in messages)
    assert any("exit code 78" in m for m in messages)

    diag = _diag(PREDECESSOR)
    orch = diag["orchestration"]
    assert orch["classification"] == "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    assert orch["mechanism"]["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert orch["mechanism"]["quantum_expired"] is True
    assert orch["mechanism"]["quantum_seconds"] == 2700
    assert orch["mechanism"]["exit_code"] == 78
    assert orch["audit"]["gate_file_written"] is False
    delta = diag["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["changed_files"] == 1
    assert delta["changed_paths_sample"] == [
        "product/query/counter_surface_known.py"]
    assert delta["snapshot_head"] == SNAPSHOT_HEAD
    assert diag["adjudication"]["status"] == "UNADJUDICATED"


def test_stranded_42996172250_lineage_is_diagnosed_and_restored():
    diag = _diag(STRANDED)
    assert diag["run_id"] == str(STRANDED)
    assert diag["raw_snapshot"] is None
    orch = diag["orchestration"]
    assert orch["classification"] == "RAW_SNAPSHOT_UNAVAILABLE"
    assert orch["mechanism_unobserved"] is True
    assert "mechanism" not in orch
    delta = diag["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["snapshot_head"] == STRANDED_HEAD
    assert delta["predecessor_head"] == ACCEPTED_HEAD
    assert delta["changed_files"] == 310
    assert "product/minimal_vertical_slice.py" in delta["changed_paths_sample"]
    assert diag["adjudication"]["status"] == "UNADJUDICATED"

    # The lineage is now an ancestor of this cycle's HEAD; the merge and the
    # revert are the two commits that reconciled it with the resumed snapshot.
    assert _git("merge-base", "--is-ancestor", STRANDED_HEAD, "HEAD").returncode == 0
    subjects = _git("log", "--format=%s", f"{STRANDED_HEAD}..HEAD").stdout
    assert "restore stranded producer lineage 42996172250" in subjects
    assert "revert unverified accepted-bundle substitution" in subjects


def test_unverified_bundle_substitution_is_gone():
    from product.query import counter_surface_known as csk

    assert not hasattr(csk, "_accepted_bundle")
    source = (ROOT / "product/query/counter_surface_known.py").read_text(
        encoding="utf-8")
    assert "_accepted_bundle" not in source
    assert "_ACCEPTED_SLICE_DIR" not in source


def test_restored_slice_bundles_validate():
    from product.query.bundle import validate_bundle

    for slug in ("rent-default", "petty-theft-dismissal",
                 "corporate-criminal-liability", "business-judgment-rule"):
        path = (ROOT / "results/product/offline_slice"
                / "CYCLE_42794322956" / f"{slug}.bundle.json")
        bundle = _load(path)
        validate_bundle(bundle)
        assert len(bundle["decisions"]) >= 100
        assert len(bundle["clusters"]) >= 8


def test_progressive_smoke_artifact_for_this_run():
    art = _load(SMOKE)
    assert str(art["run_id"]) == str(EXECUTING)
    assert art["verdict"] == "PASS"
    assert art["checks_passed"] == art["checks_total"] == 23
    timings = art["timings_s"]
    assert timings["server_boot_s"] < 3.0
    assert timings["start_s"] < 1.0


def test_state_hygiene_this_cycle():
    state = _load(STATE)
    assert state["current_cycle_run_id"] == EXECUTING
    assert state["direction_version"] == 68
    assert state["cycle_status"] == "COMPLETE"
    history_ids = {r.get("run_id") for r in state["run_history"]}
    for run_id in (PREDECESSOR, RESUMED, STRANDED, EXECUTING):
        assert run_id in history_ids, run_id

    block = state["cycle_43138476983_operational_resume"]
    assert block["run_id"] == EXECUTING
    assert block["resumed_run"] == str(RESUMED)
    assert block["predecessor_run_id"] == PREDECESSOR
    assert block["direction_version"] == 68
    assert block["mode"].startswith("OPERATIONAL RESUME")
    assert block["orchestration_failure_of_record"]["classification"] == (
        "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE")
    assert block["orchestration_failure_of_record"]["mechanism"] == (
        "OBSERVED_ZERO_DELTA_GUARD")
    assert block["stranded_lineage"]["commit"] == STRANDED_HEAD
    assert block["stranded_lineage"]["changed_files"] == 310
    assert block["stranded_lineage"]["mechanism"] == "UNOBSERVED"

    # Accepted pointer unchanged: no run after 40284658455 has both halves of
    # requirement 4.
    assert state["accepted_run_id"] == "CYCLE_40284658455"
    assert state["accepted_commit"] == ACCEPTED_HEAD
    for flag in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                 "ready_for_owner_session"):
        assert state[flag] is False, flag
    assert state["continue_recommended"] is True


def test_no_producer_minted_gate_for_this_run():
    assert not (ROOT / "results/audit/product"
                / f"CYCLE_{EXECUTING}_GATE.json").exists()
    assert not (ROOT / "reports/audit/product"
                / f"CYCLE_{EXECUTING}.md").exists()


def test_report_names_the_chain_and_the_claim_ceiling():
    text = REPORT.read_text(encoding="utf-8")
    for token in (str(EXECUTING), str(RESUMED), str(PREDECESSOR),
                  str(STRANDED), STRANDED_HEAD):
        assert token in text, token
    assert "LEX_ZERO_DELTA_REPAIR" in text
    assert "LEX_WORK_QUANTUM_EXPIRED" in text
    assert "UNADJUDICATED" in text
    assert "UNOBSERVED" in text
