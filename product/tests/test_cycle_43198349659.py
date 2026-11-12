"""Cycle 43198349659: operational resume of the 43189571965 producer snapshot.

The team job for run 43189571965 was green on all ten steps, but its
independent audit step again consumed the 2700 s work quantum and failed with
``LEX_WORK_QUANTUM_EXPIRED`` / exit 78 before writing a gate.  The snapshot
(``ff137f2f``) therefore survives UNADJUDICATED.  This resume:

* captures the run's own public run/jobs+annotations snapshot and classifies
  the orchestration failure from it;
* re-verifies the inherited vertical slice from committed bytes under an armed
  socket trap;
* publishes a bounded audit packet (claim -> artifact sha256 -> command) so the
  next auditor does not spend its quantum rediscovering the snapshot;
* advances only the *current* cycle pointer, never the accepted pointer.

The tests below assert those facts from committed artifacts.  No network, no
frozen gate, no legal-usefulness or performance claim.
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

EXECUTING_RUN = "43198349659"
RESUMED_RUN = "43189571965"
PREDECESSOR_RUN = "43180882004"
SNAPSHOT_HEAD = "ff137f2f83f7a8f1cd0928f11cf17831ef4fc132"
PREDECESSOR_HEAD = "542627d05479518afebff7f206084cc0b8b15259"
ACCEPTED_RUN = "CYCLE_40284658455"
ACCEPTED_HEAD = "7be4480e"

ORCH = ROOT / "results" / "product" / "orchestration"
RAW = ORCH / f"CYCLE_{RESUMED_RUN}_run_jobs_raw.json"
DIAG = ORCH / f"CYCLE_{RESUMED_RUN}_resume_diagnosis.json"
PRED_DIAG = ORCH / f"CYCLE_{PREDECESSOR_RUN}_resume_diagnosis.json"
PRED_RAW = ORCH / f"CYCLE_{PREDECESSOR_RUN}_run_jobs_raw.json"

PACKET = ROOT / "results" / "product" / "audit_packet" / f"CYCLE_{EXECUTING_RUN}.json"
CYCLE_REPORT = ROOT / "reports" / "product" / f"CYCLE_{EXECUTING_RUN}.md"

SNAPSHOT_RESULTS = ROOT / "results" / "product" / "vertical_slice_results_20261112T160000Z.json"
SNAPSHOT_BUNDLE = ROOT / "results" / "product" / "bundle_20261112T160000Z.json"
SLICE_DIR = ROOT / "results" / "product" / "vertical_slice" / f"CYCLE_{RESUMED_RUN}"
SLICE_SUMMARY = SLICE_DIR / "summary.json"
SLICE_BUNDLE = SLICE_DIR / "rent-default.bundle.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_generator():
    spec = importlib.util.spec_from_file_location(
        "vertical_slice_snapshot_generator_43198349659",
        PRODUCT / "vertical_slice.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------- #
# 1. Orchestration facts of the resumed run, from its own public snapshot.
# --------------------------------------------------------------------------- #

def test_raw_snapshot_is_for_the_resumed_run_and_records_the_quantum():
    raw = _load(RAW)
    assert raw["schema"] == "product-run-jobs-raw/2"
    assert raw["fetched_by_run"] == int(EXECUTING_RUN)
    assert raw["run"]["id"] == int(RESUMED_RUN)
    assert PREDECESSOR_RUN in raw["runs"]

    jobs = {job["name"]: job for job in raw["jobs"]}
    team_steps = {step["name"]: step for step in jobs["team"]["steps"]}
    assert jobs["team"]["conclusion"] == "success"
    for step in ("Run lane cycle", "Validate active MVP producer state",
                 "Enforce lane write scope", "Persist team snapshot"):
        assert team_steps[step]["conclusion"] == "success", step

    audit = jobs["audit"]
    assert audit["conclusion"] == "failure"
    audit_steps = {step["name"]: step for step in audit["steps"]}
    assert audit_steps["Independent audit"]["conclusion"] == "failure"
    assert audit_steps["Enforce audit scope and read gate"]["conclusion"] == "skipped"
    assert audit_steps["Persist audit snapshot"]["conclusion"] == "skipped"
    assert jobs["integrate"]["conclusion"] == "skipped"

    messages = [str(m) for block in raw["check_run_annotations_by_job_id"].values()
                for m in (block.get("annotations") or [])]
    assert any("LEX_WORK_QUANTUM_EXPIRED seconds=2700" in m for m in messages)
    assert any("exit code 78" in m for m in messages)


def test_diagnosis_classifies_the_orchestration_and_proves_the_delta():
    diag = _load(DIAG)
    assert diag["run_id"] == RESUMED_RUN
    assert diag["predecessor_run_id"] == PREDECESSOR_RUN
    orch = diag["orchestration"]
    assert orch["classification"] == "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    assert orch["team"]["conclusion"] == "success"
    assert orch["team"]["producer_state_validation_step_conclusion"] == "success"
    assert orch["team"]["write_scope_step_conclusion"] == "success"
    assert orch["audit"]["failed_step"] == "Independent audit"
    assert orch["audit"]["gate_file_written"] is False
    assert orch["mechanism"]["quantum_expired"] is True
    assert orch["mechanism"]["quantum_seconds"] == 2700
    assert orch["mechanism"]["exit_code"] == 78
    assert diag["raw_snapshot_sha256"] == _sha(RAW)
    assert diag["adjudication"]["status"] == "UNADJUDICATED"

    delta = diag["durable_delta"]
    assert delta["snapshot_head"] == SNAPSHOT_HEAD
    assert delta["predecessor_head"] == PREDECESSOR_HEAD
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["changed_files"] == 12
    assert "product/audit_readiness.py" in delta["changed_paths_sample"]

    pred = _load(PRED_DIAG)
    assert pred["run_id"] == PREDECESSOR_RUN
    assert pred["raw_snapshot_sha256"] == _sha(PRED_RAW)
    assert pred["orchestration"]["mechanism"]["quantum_expired"] is True
    assert pred["durable_delta"]["changed_files"] == 4


# --------------------------------------------------------------------------- #
# 2. The inherited vertical slice re-derives from committed bytes.
# --------------------------------------------------------------------------- #

def test_inherited_snapshot_artifacts_are_preserved_byte_identically():
    assert _sha(SNAPSHOT_BUNDLE) == (
        "a28a43d618d1dda365222b56ef851b5c3d68d468cd9747eb1a590f0352d373e8")
    assert _sha(SNAPSHOT_RESULTS) == (
        "0c7af6b774d51a97f7f5aab71c172494baf4e82f2fb39ffce2b50510fd9c90f7")


def test_snapshot_generator_reproduces_its_committed_result(monkeypatch):
    def _no_network(*_a, **_k):  # pragma: no cover - any attempt fails the test
        raise AssertionError("vertical slice attempted network access")

    monkeypatch.setattr(socket.socket, "connect", _no_network)
    module = _load_generator()
    fresh = module.vertical_slice(
        "Kündigung Mietvertrag Mietrecht", top_n=120,
        retrieval_mode="offline", fixture_generation=True)

    committed = _load(SNAPSHOT_RESULTS)
    assert fresh["phase"] == committed["phase"] == "complete"
    assert fresh["mapped_decisions"] == committed["n_decisions"] == 120
    assert fresh["n_clusters"] == committed["n_clusters"] == 8
    assert fresh["n_relations"] == committed["n_relations"] == 11
    assert fresh["counter_status_dist"] == committed["counter_status_dist"]
    assert (fresh["content_coverage"]["by_state"]
            == committed["content_coverage"]["by_state"])

    decisions = fresh["bundle"]["decisions"]
    ids = {d["decision_id"] for d in decisions}
    assert len(ids) == 120
    for row in decisions:
        assert row.get("canonical_url"), row["decision_id"]
        assert isinstance(row.get("x"), (int, float)), row["decision_id"]
        assert isinstance(row.get("y"), (int, float)), row["decision_id"]
        assert row.get("cluster_id") is not None, row["decision_id"]
    answer_ids = (fresh["bundle"].get("answer") or {}).get("cited_decision_ids") or []
    assert answer_ids and set(answer_ids) <= ids

    # The v68 rejection/incumbent leg is inherited accepted work: every
    # verified counter row carries non-empty, non-letterhead evidence.
    verified = [d for d in decisions if d.get("counter_evidence_verified")]
    assert verified
    assert all((d.get("counter_evidence") or "").strip() for d in verified)
    assert not any(
        (d.get("counter_evidence") or "").lstrip().lower().startswith("gr_gerichte")
        for d in verified)

    def signature(payload):
        return sorted(
            (d["decision_id"], d.get("cluster_id"), d.get("counter_status"),
             d.get("counter_evidence_verified"),
             round(d.get("x") or 0.0, 6), round(d.get("y") or 0.0, 6))
            for d in payload["decisions"])

    assert signature(fresh["bundle"]) == signature(_load(SNAPSHOT_BUNDLE))


def test_inherited_run_scoped_slice_is_a_verified_full_loop_artifact():
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
    assert stats["geometry_preserved_by_enrich"] is True
    assert stats["rows_with_xy"] == stats["rows_with_cluster_id"] == 120
    assert stats["rows_with_canonical_url"] == 120
    assert stats["fixture_replay"]["network"] == "none"
    assert stats["adapter_transport_attempts"] == 0

    bundle = _load(SLICE_BUNDLE)
    assert bundle["provenance"]["offline_slice"]["network"] == "none"
    ids = {d["decision_id"] for d in bundle["decisions"]}
    assert set(bundle["answer"]["cited_decision_ids"]) <= ids


# --------------------------------------------------------------------------- #
# 3. The bounded audit packet: claim -> artifact sha256 -> command.
# --------------------------------------------------------------------------- #

def test_audit_packet_is_derivable_and_verifies_without_network():
    import audit_packet as ap

    committed = _load(PACKET)
    fresh = ap.build_packet(
        executing_run_id=EXECUTING_RUN, resumed_run_id=RESUMED_RUN,
        predecessor_run_id=PREDECESSOR_RUN, direction_version=68)
    # Everything except the generation timestamp is a pure function of the
    # committed tree, so the packet cannot drift away from its evidence.
    committed.pop("generated_at", None)
    fresh.pop("generated_at", None)
    assert fresh == committed

    result = ap.verify_packet(committed, run_commands=False)
    assert result["status"] == "PASS", result["failures"]
    assert result["claims_checked"] == len(committed["claims"])
    assert result["failures"] == []
    assert committed["forbidden_verdict_keys_present"] == []
    for key in ap.FORBIDDEN_VERDICT_KEYS:
        assert key not in committed
    # Bounded: the whole fast path is hash + assertion work, and the optional
    # command budget stays inside the audit's own 2700 s quantum.
    assert result["elapsed_seconds"] < 5.0
    assert committed["bounded_total_seconds"] < 120.0
    assert committed["audit_entrypoint"].endswith("--run-commands")
    assert any(c["id"] == "cycle_reproduction" for c in committed["commands"])

    # Every named artifact resolves and hashes; no claim may be artifact-free
    # unless it is an explicit absence claim.
    for claim in committed["claims"]:
        if claim["id"] == "audit_namespace_untouched":
            assert claim["artifact"] is None
            continue
        path = ROOT / claim["artifact"]
        assert path.is_file(), claim["id"]
        assert _sha(path) == claim["sha256"], claim["id"]


def test_audit_packet_does_not_write_the_auditor_namespace():
    assert not (ROOT / "results" / "audit" / "product"
                / f"CYCLE_{EXECUTING_RUN}_GATE.json").exists()
    assert not (ROOT / "reports" / "audit" / "product"
                / f"CYCLE_{EXECUTING_RUN}.md").exists()


# --------------------------------------------------------------------------- #
# 4. State bookkeeping and fail-closed posture.
# --------------------------------------------------------------------------- #

def test_state_records_this_resume_without_moving_the_accepted_pointer():
    state = _load(ROOT / "state" / "product.json")
    assert state["lane"] == "product"
    assert state["direction_version"] == 68
    assert state["cycle_status"] != "INITIALIZED"
    # A later resume may advance the pointer; the run_history row below pins
    # this cycle's attribution exactly.
    assert state["current_cycle_run_id"] >= int(EXECUTING_RUN)
    assert state["continue_recommended"] is True
    assert state["human_gate_ready"] is False
    assert state["ready_for_owner_session"] is False
    assert state["machine_gate_ready"] is False
    assert state["packet_admitted"] is False
    assert state["accepted_run_id"] == ACCEPTED_RUN
    assert state["accepted_commit"].startswith(ACCEPTED_HEAD)

    block = state["cycle_43198349659_operational_resume"]
    assert block["resumed_run_id"] == int(RESUMED_RUN)
    assert block["predecessor_run_id"] == int(PREDECESSOR_RUN)
    assert block["verdict"] == "PROPOSED"
    assert block["audit_gate"] == "NONE_ON_ANY_REF"
    assert block["gate_minted"] is False
    assert block["accepted_pointer_unchanged"] is True
    assert block["direction_version"] == 68
    assert block["snapshot_head"] == SNAPSHOT_HEAD
    assert block["diagnosis"] == str(DIAG.relative_to(ROOT))
    assert block["audit_packet"] == str(PACKET.relative_to(ROOT))

    rows = {int(row["run_id"]): row for row in state["run_history"]}
    for run_id in (PREDECESSOR_RUN, RESUMED_RUN, EXECUTING_RUN):
        assert int(run_id) in rows, run_id
    # Historical rows are append-only: the resumed run's own row keeps the
    # audit_gate value it was written with. This cycle's row records that no
    # gate exists yet.
    assert rows[int(EXECUTING_RUN)]["audit_gate"] == "NONE_YET"
    assert rows[int(EXECUTING_RUN)]["status"].startswith(
        "OPERATIONAL_RESUME_SNAPSHOT_43189571965")


@pytest.mark.parametrize("half", ["gate", "accept"])
def test_accepted_pointer_halves_are_read_not_re_measured(half):
    if half == "gate":
        proc = subprocess.run(
            ["git", "show",
             f"origin/lab/product:results/audit/product/{ACCEPTED_RUN}_GATE.json"],
            cwd=ROOT, capture_output=True, text=True)
        if proc.returncode != 0:
            pytest.skip("origin/lab/product not available in this checkout")
        payload = json.loads(proc.stdout)
        assert payload["gate"] == "PASS"
        assert payload["safe_to_integrate"] is True
        assert payload["required_fixes"] == []
    else:
        proc = subprocess.run(["git", "log", "origin/lab/product", "--oneline",
                               "-1"], cwd=ROOT, capture_output=True, text=True)
        if proc.returncode != 0:
            pytest.skip("origin/lab/product not available in this checkout")
        assert proc.stdout.startswith(ACCEPTED_HEAD)
        assert f"accept product cycle {ACCEPTED_RUN.removeprefix('CYCLE_')}" in proc.stdout


# --------------------------------------------------------------------------- #
# 5. The report of record states the evidence, the ceiling and the entrypoint.
# --------------------------------------------------------------------------- #

def test_report_states_the_evidence_and_the_audit_entrypoint():
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
        "audit packet",
        "No gate was minted",
    ):
        assert token in report, token
