"""Cycle 42771257885: operational resume of producer snapshot 42764343815.

These tests pin, against the committed bytes, the four claims of this cycle:

1. the snapshot's orchestration diagnosis is reproducible from the committed
   raw run/jobs+annotation snapshot (team green, audit quantum exit 78, no
   gate, UNADJUDICATED) and the five-run chain is on the record;
2. the finished lane deliverable (``product/minimal_vertical_slice.py`` with
   its ``--mode`` seam) exists with its test and its offline artifact, whose
   recorded hashes match the committed files;
3. the audit-readiness module carries profiles for BOTH the snapshot run and
   this run, so a dossier invocation cannot fall back to another run's claims;
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

RAW = ROOT / "results/product/orchestration/CYCLE_42764343815_run_jobs_raw.json"
DIAG = ROOT / "results/product/orchestration/CYCLE_42764343815_resume_diagnosis.json"
ARTIFACT = ROOT / "results/product/vertical_slice/CYCLE_42771257885_minimal_slice.json"
STATE = ROOT / "state/product.json"
REPORT = ROOT / "reports/product/CYCLE_42771257885.md"
SLICE = PRODUCT / "minimal_vertical_slice.py"
SLICE_TEST = PRODUCT / "tests/test_minimal_vertical_slice.py"


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_raw_snapshot_pins_the_snapshot_orchestration_facts():
    raw = _load(RAW)
    assert raw["schema"] == "product-run-jobs-raw/2"
    assert raw["fetched_by_run"] == 42771257885
    run = raw["runs"]["42764343815"]
    assert run["conclusion"] == "failure"
    jobs = {j["name"]: j for j in raw["jobs"] if j["run_id"] == 42764343815}
    steps = {s["name"]: s["conclusion"] for s in jobs["team"]["steps"]}
    assert steps["Run lane cycle"] == "success"
    assert steps["Validate active MVP producer state"] == "success"
    assert steps["Enforce lane write scope"] == "success"
    assert steps["Persist team snapshot"] == "success"
    audit = {s["name"]: s["conclusion"] for s in jobs["audit"]["steps"]}
    assert audit["Independent audit"] == "failure"
    assert audit["Enforce audit scope and read gate"] == "skipped"
    assert audit["Persist audit snapshot"] == "skipped"
    ann = raw["check_run_annotations_by_job_id"][str(jobs["audit"]["id"])]
    msgs = [m for _, m in ann["annotations"]]
    assert any("LEX_WORK_QUANTUM_EXPIRED seconds=2700 pid=2302" in m
               for m in msgs)
    assert any("exit code 78" in m for m in msgs)
    # zero-delta guard exits in the chain, attributed by check-run id
    team_ann = {str(j["id"]): j for j in raw["jobs"]}
    zero_delta = [
        str(j["id"]) for j in raw["jobs"]
        if j["name"] == "team" and j["conclusion"] == "failure"
        and j["run_id"] in (42763518526, 42763865015)
    ]
    assert len(zero_delta) == 2
    for jid in zero_delta:
        messages = [m for _, m in
                    raw["check_run_annotations_by_job_id"][jid]["annotations"]]
        assert any("LEX_ZERO_DELTA_REPAIR" in m for m in messages), jid


def test_diagnosis_is_consistent_with_the_raw_snapshot_and_the_profile():
    diag = _load(DIAG)
    raw = _load(RAW)
    assert diag["schema"] == "product-resume-snapshot-diagnosis/1"
    assert diag["run_id"] == "42764343815"
    assert diag["predecessor_run_id"] == "42756474119"
    assert diag["raw_snapshot_sha256"] == _sha(RAW)
    orch = diag["orchestration"]
    assert orch["classification"] == "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    mech = orch["mechanism"]
    assert mech["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert mech["quantum_seconds"] == 2700 and mech["exit_code"] == 78
    assert orch["audit"]["gate_file_written"] is False
    assert diag["durable_delta"]["classification"] == "COMMITTED_DELTA"
    assert diag["durable_delta"]["changed_files"] == 2
    # the snapshot head is the persisted TEAM commit; the run's head_sha is
    # the workflow's own main base - they are different objects by design
    assert diag["durable_delta"]["snapshot_head"] == \
        "d5a2012b37f1aeec596ef869e29689edcc6a1a9d"
    assert diag["durable_delta"]["snapshot_head"] != raw["runs"]["42764343815"]["head_sha"]
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["accepted"] is False
    assert [c["run_id"] for c in orch["chain_of_record"]] == [
        "42750521657", "42756474119", "42763518526", "42763865015",
        "42764343815"]

    import audit_readiness as ar
    snap = ar.select_profile("42764343815")
    cur = ar.select_profile("42771257885")  # alias resolves to the same profile
    assert snap["resumed_run_id"] == "42764343815"
    assert snap["predecessor_run_id"] == diag["predecessor_run_id"]
    assert snap["changed_files"] == diag["durable_delta"]["changed_files"]
    assert snap["mechanism_kind"] == "observed"
    assert cur == snap
    assert Path(snap["current_report"]) == REPORT


def test_finished_slice_deliverable_is_tested_and_artifacted():
    assert SLICE.is_file() and SLICE_TEST.is_file()
    assert "--mode" in SLICE.read_text(encoding="utf-8")
    art = _load(ARTIFACT)
    assert art["run_id"] == "42771257885"
    assert art["execution"]["mode"] == "offline"
    assert art["execution"]["network_attempts"] == []
    assert art["test_run"]["exit_code"] == 0
    assert art["slice_sha256"] == _sha(SLICE)
    assert art["test_sha256"] == _sha(SLICE_TEST)
    out = art["output"]
    assert out["retrieval_mode"] == "offline"
    assert out["stages"] == {"retrieval": True, "map": True,
                             "answer": True, "counter_authority": True}
    assert set(out["answer"]["cited_decision_ids"]) <= set(out["decision_ids"])
    assert out["visualization"]["n_decisions"] == out["summary"]["n_decisions"]
    assert out["summary"]["n_decisions"] == 100
    assert out["summary"]["n_clusters"] == 8
    assert art["execution"]["wall_s"] < 2.0  # local cache-served geometry


def test_state_hygiene_and_fail_closed_posture():
    st = _load(STATE)
    # POINTER-PIN AMENDMENT (product cycle 42983901071), following
    # ``test_cycle_40263666190_resume.py``: later cycles legitimately
    # advance the pointer past this cycle's era; only regression below this
    # cycle's executing run is a defect.
    assert st["current_cycle_run_id"] >= 42771257885, (
        "current_cycle_run_id regressed below this cycle's executing run",
        st["current_cycle_run_id"])
    assert st["direction_version"] == 68
    hist = {h["run_id"]: h for h in st["run_history"]}
    for rid in (42750521657, 42756474119, 42763518526, 42763865015,
                42764343815, 42771257885):
        assert rid in hist, rid
    assert hist[42763518526]["status"] == "ZERO_DURABLE_DELTA_GUARD_EXIT_67"
    assert hist[42763865015]["status"] == "ZERO_DURABLE_DELTA_GUARD_EXIT_67"
    assert "QUANTUM" in hist[42764343815]["status"]
    assert hist[42764343815]["audit_gate"] == "NONE_ON_ANY_REF"
    block = st["cycle_42771257885_operational_resume"]
    assert block["resumed_run"] == "42764343815"
    assert block["adjudication"]["accepted"] is False
    # accepted pointer untouched by this resume
    assert st["accepted_run_id"] == "CYCLE_40284658455"
    assert st["accepted_commit"] == "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
    # fail-closed posture
    assert st["continue_recommended"] is True
    for flag in ("human_gate_ready", "machine_gate_ready",
                 "packet_admitted", "ready_for_owner_session"):
        assert st[flag] is False, flag
    assert REPORT.is_file()


def test_producer_minted_no_audit_gate():
    """No producer-written gate may exist for any run of this chain."""
    minted = list((ROOT / "results/audit/product").glob("CYCLE_427*_GATE.json"))
    ours = [p for p in minted if any(
        rid in p.name for rid in ("42750521657", "42756474119", "42763518526",
                                  "42763865015", "42764343815", "42771257885"))]
    assert ours == [], f"producer-minted gate: {ours}"
