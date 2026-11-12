"""Cycle 43189571965: operational resume of the 43180882004 producer snapshot.

This is a diagnosis + re-verification cycle for a FAST-MVP producer snapshot
whose team job was green but whose independent audit consumed the 2700 s work
quantum and wrote no gate.  The tests below pin, from committed bytes:

* the orchestration facts of the two-run chain (43172256761 -> 43180882004);
* the snapshot's vertical-slice artifact and its generator, re-derived with
  ``socket.connect`` booby-trapped;
* the run-scoped shipped ``offline_slice`` artifact this resume publishes;
* the state bookkeeping and the fail-closed posture;
* the correction of record for the snapshot report's overclaims.

No network, no frozen gate, no legal-usefulness claim.
"""
from __future__ import annotations

import importlib.util
import json
import socket
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "product"
for _p in (str(PRODUCT), str(ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

EXECUTING_RUN = "43189571965"
RESUMED_RUN = "43180882004"
PREDECESSOR_RUN = "43172256761"
SNAPSHOT_HEAD = "542627d05479518afebff7f206084cc0b8b15259"
PREDECESSOR_HEAD = "e37a7ad7fb7ee2d219abbd4f92a71c0c0daa1a70"
ACCEPTED_RUN = "CYCLE_40284658455"
ACCEPTED_HEAD = "7be4480e"

ORCH = ROOT / "results" / "product" / "orchestration"
RAW = ORCH / f"CYCLE_{RESUMED_RUN}_run_jobs_raw.json"
DIAG = ORCH / f"CYCLE_{RESUMED_RUN}_resume_diagnosis.json"
PRED_RAW = ORCH / f"CYCLE_{PREDECESSOR_RUN}_run_jobs_raw.json"
PRED_DIAG = ORCH / f"CYCLE_{PREDECESSOR_RUN}_resume_diagnosis.json"
SNAPSHOT_RESULTS = ROOT / "results" / "product" / "vertical_slice_results_20261112T160000Z.json"
SNAPSHOT_BUNDLE = ROOT / "results" / "product" / "bundle_20261112T160000Z.json"
SNAPSHOT_REPORT = ROOT / "reports" / "product" / "vertical_slice_report_20261112T160000Z.md"
CORRECTION = ROOT / "reports" / "product" / "vertical_slice_report_20261112T160000Z.CORRECTION.md"
CYCLE_REPORT = ROOT / "reports" / "product" / f"CYCLE_{EXECUTING_RUN}.md"
SLICE_DIR = ROOT / "results" / "product" / "vertical_slice" / f"CYCLE_{EXECUTING_RUN}"
SLICE_SUMMARY = SLICE_DIR / "summary.json"
SLICE_BUNDLE = SLICE_DIR / "rent-default.bundle.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_generator():
    spec = importlib.util.spec_from_file_location(
        "vertical_slice_snapshot_generator", PRODUCT / "vertical_slice.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------- #
# 1. Orchestration facts of the resumed chain.
# --------------------------------------------------------------------------- #

def test_raw_snapshot_is_for_the_resumed_run_and_records_the_quantum():
    raw = _load(RAW)
    assert raw["schema"] == "product-run-jobs-raw/2"
    assert raw["fetched_by_run"] == int(EXECUTING_RUN)
    assert raw["run"]["id"] == int(RESUMED_RUN)
    # The history run is captured inside the same raw artifact, not inferred.
    assert PREDECESSOR_RUN in raw["runs"]

    jobs = {job["name"]: job for job in raw["jobs"]}
    team_steps = {step["name"]: step for step in jobs["team"]["steps"]}
    assert jobs["team"]["conclusion"] == "success"
    for step in (
        "Run lane cycle",
        "Validate active MVP producer state",
        "Enforce lane write scope",
        "Persist team snapshot",
    ):
        assert team_steps[step]["conclusion"] == "success", step

    audit = jobs["audit"]
    assert audit["conclusion"] == "failure"
    audit_steps = {step["name"]: step for step in audit["steps"]}
    assert audit_steps["Independent audit"]["conclusion"] == "failure"
    assert audit_steps["Enforce audit scope and read gate"]["conclusion"] == "skipped"
    assert audit_steps["Persist audit snapshot"]["conclusion"] == "skipped"
    assert jobs["integrate"]["conclusion"] == "skipped"

    messages = [row[-1] for row in raw["check_run_annotations_by_job_id"][
        str(audit["id"])]["annotations"]]
    assert any("LEX_WORK_QUANTUM_EXPIRED seconds=2700" in m for m in messages)
    assert any("exit code 78" in m for m in messages)


def test_diagnosis_classifies_orchestration_and_proves_the_delta():
    diag = _load(DIAG)
    assert diag["run_id"] == RESUMED_RUN
    assert diag["predecessor_run_id"] == PREDECESSOR_RUN
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    orch = diag["orchestration"]
    assert orch["classification"] == "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    assert orch["team"]["producer_state_validation_step_conclusion"] == "success"
    assert orch["team"]["write_scope_step_conclusion"] == "success"
    assert orch["audit"]["failed_step"] == "Independent audit"
    assert orch["audit"]["gate_file_written"] is False
    assert orch["mechanism"]["quantum_expired"] is True
    assert orch["mechanism"]["quantum_seconds"] == 2700
    assert orch["mechanism"]["exit_code"] == 78
    # The diagnosis hashes the very raw artifact it consumes.
    assert diag["raw_snapshot_sha256"] == _sha(RAW)

    delta = diag["durable_delta"]
    assert delta["snapshot_head"] == SNAPSHOT_HEAD
    assert delta["predecessor_head"] == PREDECESSOR_HEAD
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["changed_files"] == 4
    assert "product/vertical_slice.py" in delta["changed_paths_sample"]

    pred = _load(PRED_DIAG)
    assert pred["run_id"] == PREDECESSOR_RUN
    assert pred["raw_snapshot_sha256"] == _sha(PRED_RAW)
    assert pred["orchestration"]["mechanism"]["quantum_seconds"] == 2700
    assert pred["orchestration"]["mechanism"]["exit_code"] == 78
    assert pred["durable_delta"]["snapshot_head"] == PREDECESSOR_HEAD
    assert pred["durable_delta"]["classification"] == "COMMITTED_DELTA"
    assert pred["durable_delta"]["changed_files"] == 2
    assert any("offline_slice" in p for p in pred["durable_delta"]["changed_paths_sample"])


# --------------------------------------------------------------------------- #
# 2. The snapshot's own vertical slice reproduces from committed bytes.
# --------------------------------------------------------------------------- #

def test_snapshot_artifacts_are_preserved_byte_identically():
    assert _sha(SNAPSHOT_BUNDLE) == (
        "a28a43d618d1dda365222b56ef851b5c3d68d468cd9747eb1a590f0352d373e8")
    assert _sha(SNAPSHOT_RESULTS) == (
        "0c7af6b774d51a97f7f5aab71c172494baf4e82f2fb39ffce2b50510fd9c90f7")
    assert _sha(SNAPSHOT_REPORT) == (
        "de5471d649fd2511149e130ce5c2daed8c015b052f2df70c77a22b6b6ed39a36")


def test_snapshot_generator_reproduces_its_committed_bundle(monkeypatch):
    def _no_network(*_a, **_k):  # pragma: no cover - any attempt fails the test
        raise AssertionError("vertical slice attempted network access")

    monkeypatch.setattr(socket.socket, "connect", _no_network)
    module = _load_generator()
    fresh = module.vertical_slice(
        "Kündigung Mietvertrag Mietrecht", top_n=120,
        retrieval_mode="offline", fixture_generation=True)

    assert fresh["phase"] == "complete"
    assert fresh["mapped_decisions"] == 120
    assert fresh["n_clusters"] == 8
    assert fresh["n_relations"] == 11
    assert fresh["counter_status_dist"] == {
        "cited": 2, "candidate-limiting": 4, "none": 114}
    assert fresh["content_coverage"]["by_state"] == {
        "full_text": 25, "regeste": 68, "snippet": 16, "pointer": 11}

    bundle = fresh["bundle"]
    decisions = bundle["decisions"]
    ids = {d["decision_id"] for d in decisions}
    assert len(ids) == 120
    assert bundle["provenance"]["counter_evidence_span"]["applied"] is True
    for row in decisions:
        assert row.get("canonical_url"), row["decision_id"]
        assert isinstance(row.get("x"), (int, float)), row["decision_id"]
        assert isinstance(row.get("y"), (int, float)), row["decision_id"]
        assert row.get("cluster_id") is not None, row["decision_id"]
    answer_ids = (bundle.get("answer") or {}).get("cited_decision_ids") or []
    assert answer_ids and set(answer_ids) <= ids
    # The v68 rejection/incumbent leg: no verified counter row may carry empty
    # evidence, and no defective letterhead row may remain verified.
    verified = [d for d in decisions if d.get("counter_evidence_verified")]
    assert verified, "the snapshot carries verified counter evidence"
    assert all((d.get("counter_evidence") or "").strip() for d in verified)
    assert not any(
        (d.get("counter_evidence") or "").lstrip().lower().startswith("gr_gerichte")
        for d in verified)

    committed = _load(SNAPSHOT_BUNDLE)

    def signature(payload):
        return sorted(
            (d["decision_id"], d.get("cluster_id"), d.get("counter_status"),
             d.get("counter_evidence_verified"),
             round(d.get("x") or 0.0, 6), round(d.get("y") or 0.0, 6))
            for d in payload["decisions"]
        )

    assert signature(bundle) == signature(committed)
    assert bundle["answer"]["cited_decision_ids"] == committed["answer"]["cited_decision_ids"]


# --------------------------------------------------------------------------- #
# 3. The run-scoped shipped slice this resume publishes.
# --------------------------------------------------------------------------- #

def test_run_scoped_slice_is_verified_full_loop_and_reproducible(monkeypatch, tmp_path):
    summary = _load(SLICE_SUMMARY)
    assert summary["verified"] is True
    assert summary["mode"] == "full_loop"
    assert summary["page_contract"] is True
    assert summary["page_contract_detail"].startswith("PASS")
    assert summary["degraded"] is False
    assert "OFFLINE WIRING EVIDENCE ONLY" in summary["claim_ceiling"]
    stats = summary["stats"]
    assert stats["n_decisions"] == 120
    assert stats["n_clusters"] == 8
    assert stats["enriched"] is True
    assert stats["answer_status"] == "ready"
    assert stats["cited_decision_ids"] >= 1
    assert stats["geometry_preserved_by_enrich"] is True
    assert stats["rows_with_xy"] == stats["rows_with_cluster_id"] == 120
    assert stats["rows_with_canonical_url"] == 120
    assert stats["fixture_replay"]["network"] == "none"
    assert stats["adapter_transport_attempts"] == 0

    bundle = _load(SLICE_BUNDLE)
    assert bundle["provenance"]["offline_slice"]["network"] == "none"
    ids = {d["decision_id"] for d in bundle["decisions"]}
    assert set(bundle["answer"]["cited_decision_ids"]) <= ids

    # Re-run the shipped entry point into a temp directory and compare the
    # measured fields, not the wall-clock latency.
    def _no_network(*_a, **_k):  # pragma: no cover
        raise AssertionError("offline slice attempted network access")

    monkeypatch.setattr(socket.socket, "connect", _no_network)
    import offline_slice as ofs

    rc = ofs.main(["--slug", "rent-default", "--top-n", "120",
                   "--out", str(tmp_path), "--verify", "--quiet"])
    assert rc == 0
    fresh = _load(tmp_path / "summary.json")
    fresh_stats = fresh["stats"]
    for key in ("n_decisions", "n_clusters", "rows_with_xy",
                "rows_with_cluster_id", "rows_with_canonical_url",
                "answer_status", "cited_decision_ids",
                "geometry_preserved_by_enrich", "counter_status_bearing_rows"):
        assert fresh_stats[key] == stats[key], key
    fresh_bundle = _load(tmp_path / "rent-default.bundle.json")
    assert sorted(d["decision_id"] for d in fresh_bundle["decisions"]) == sorted(ids)


# --------------------------------------------------------------------------- #
# 4. State bookkeeping and fail-closed posture.
# --------------------------------------------------------------------------- #

def test_state_records_this_resume_without_moving_the_accepted_pointer():
    state = _load(ROOT / "state" / "product.json")
    assert state["lane"] == "product"
    assert state["direction_version"] == 68
    assert state["cycle_status"] != "INITIALIZED"
    # Later operational resumes legitimately advance the current-cycle pointer
    # past this cycle; the append-only run_history row below keeps this cycle's
    # attribution exact (established convention in
    # test_cycle_40259640985_resume.py).
    assert state["current_cycle_run_id"] >= int(EXECUTING_RUN)
    assert state["continue_recommended"] is True
    assert state["human_gate_ready"] is False
    assert state["ready_for_owner_session"] is False
    assert state["machine_gate_ready"] is False
    assert state["packet_admitted"] is False
    assert state["accepted_run_id"] == ACCEPTED_RUN
    assert state["accepted_commit"].startswith(ACCEPTED_HEAD)

    block = state["cycle_43189571965_operational_resume"]
    assert block["resumed_run_id"] == int(RESUMED_RUN)
    assert block["predecessor_run_id"] == int(PREDECESSOR_RUN)
    assert block["verdict"] == "PROPOSED"
    assert block["audit_gate"] == "NONE_ON_ANY_REF"
    assert block["gate_minted"] is False
    assert block["accepted_pointer_unchanged"] is True
    assert block["direction_version"] == 68
    assert block["snapshot_head"] == SNAPSHOT_HEAD
    assert block["diagnosis"] == str(DIAG.relative_to(ROOT))
    assert block["slice"]["verified"] is True
    assert block["slice"]["page_contract"] is True
    assert block["slice"]["n_decisions"] == 120
    assert block["slice"]["n_verified_defective"] == 0

    rows = {int(row["run_id"]): row for row in state["run_history"]}
    for run_id in (PREDECESSOR_RUN, RESUMED_RUN, EXECUTING_RUN):
        assert int(run_id) in rows, run_id
    assert rows[int(RESUMED_RUN)]["audit_gate"] == "NONE_ON_ANY_REF"
    assert rows[int(RESUMED_RUN)]["status"].startswith(
        "TEAM_GREEN_AUDIT_QUANTUM_NO_GATE")


def test_accepted_pointer_is_verified_in_state_and_not_re_measured_here():
    # Reading the accepted tree is read-only; the gate file and the accept
    # commit must both be present for the pointer to count (requirement 4).
    gate = subprocess.run(
        ["git", "show",
         f"origin/lab/product:results/audit/product/{ACCEPTED_RUN}_GATE.json"],
        cwd=ROOT, capture_output=True, text=True)
    if gate.returncode != 0:
        pytest.skip("origin/lab/product not available in this checkout")
    payload = json.loads(gate.stdout)
    assert payload["gate"] == "PASS"
    assert payload["safe_to_integrate"] is True
    assert payload["required_fixes"] == []


# --------------------------------------------------------------------------- #
# 5. Report of record and the correction of the snapshot's overclaims.
# --------------------------------------------------------------------------- #

def test_report_and_correction_state_the_evidence_and_the_ceiling():
    report = CYCLE_REPORT.read_text(encoding="utf-8")
    for token in (
        EXECUTING_RUN,
        RESUMED_RUN,
        PREDECESSOR_RUN,
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE",
        "LEX_WORK_QUANTUM_EXPIRED",
        "UNADJUDICATED",
        "PROPOSED",
        "NONE_ON_ANY_REF",
        "OFFLINE WIRING EVIDENCE ONLY",
        "No gate was minted",
        "accepted pointer",
    ):
        assert token in report, token

    correction = CORRECTION.read_text(encoding="utf-8")
    old_report = SNAPSHOT_REPORT.read_text(encoding="utf-8")
    assert "All QUERY_MAP_MVP core requirements satisfied" in old_report
    assert "All QUERY_MAP_MVP core requirements satisfied" in correction
    assert "withdrawn" in correction.lower()
    assert "/tmp/lex_control/state/product.json" in correction
    assert "state/product.json" in correction
    # The correction is append-only: it never rewrites the historical report.
    assert _sha(SNAPSHOT_REPORT) == (
        "de5471d649fd2511149e130ce5c2daed8c015b052f2df70c77a22b6b6ed39a36")
