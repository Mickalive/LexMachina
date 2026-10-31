"""Operational resume 41152471808: audit-readiness repair of failed run 41149776023.

The failed run was a *fresh* v68 product cycle, not an audit or repair: its
team job died at ``Run lane cycle`` after 1670 s of a 2700 s work quantum and
left the team ref byte-identical to the accepted base 7be4480e.  This test
locks the resume's diagnosis and its repairs fail-closed:

* the failure is recorded from the PUBLIC run/jobs snapshot (step conclusions
  and timings) while the log-level cause stays UNOBSERVED because the logs
  endpoint answered HTTP 403 - no cause is invented;
* the durable delta over the accepted base is ZERO and the run is
  UNADJUDICATED (no /audit ref, no gate);
* the accepted pointer now names CYCLE_40284658455 / 7be4480e, and BOTH
  halves of factory-wide requirement 4 verify for it;
* the post-acceptance tree is self-consistent: the previous cycle test no
  longer asserts its own run has no gate, and the audit-readiness instrument
  models this fifth failure mode as ``observed_step_failure``;
* the vertical slice still runs from fixture bytes and produces a
  source-linked, clickable map with finite coordinates and >=2 clusters;
* posture stays fail-closed and the direction version stays 68.
"""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

EXECUTING_RUN_ID = "41152471808"
RESUMED_RUN_ID = "41149776023"
PREDECESSOR_RUN_ID = "40284658455"
ACCEPTED_HEAD = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"

STATE = ROOT / "state" / "product.json"
ORCH = ROOT / "results" / "product" / "orchestration"
RAW = ORCH / f"CYCLE_{RESUMED_RUN_ID}_team_step_raw.json"
DIAG = ORCH / f"CYCLE_{RESUMED_RUN_ID}_resume_diagnosis.json"
GATE = ROOT / "results" / "audit" / "product" / f"CYCLE_{PREDECESSOR_RUN_ID}_GATE.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(ROOT), capture_output=True, text=True,
        check=True).stdout.strip()


def test_public_snapshot_records_the_step_failure_without_inventing_a_cause():
    raw = _load(RAW)
    assert raw["schema"] == "github-actions-run-jobs-snapshot/1"
    assert raw["logs_endpoint_status"] == 403
    assert raw["run"]["id"] == int(RESUMED_RUN_ID)
    assert raw["run"]["conclusion"] == "failure"
    team = next(j for j in raw["jobs"] if j["name"] == "team")
    steps = {s["name"]: s for s in team["steps"]}
    assert steps["Run lane cycle"]["conclusion"] == "failure"
    assert steps["Validate active MVP producer state"]["conclusion"] == "skipped"
    assert steps["Enforce lane write scope"]["conclusion"] == "skipped"
    # The step ran below the 2700 s wrapper quantum, so a quantum-expiry
    # narrative would be false.
    from datetime import datetime
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    run_s = (datetime.strptime(steps["Run lane cycle"]["completed_at"], fmt)
             - datetime.strptime(steps["Run lane cycle"]["started_at"], fmt)
             ).total_seconds()
    assert run_s == 1670
    assert run_s < 2700
    # GitHub does not expose a step exit_code in this snapshot; the diagnosis
    # stores null rather than guessing one.
    assert steps["Run lane cycle"].get("exit_code") is None


def test_diagnosis_records_zero_delta_and_unadjudicated_status():
    diag = _load(DIAG)
    assert diag["run_id"] == RESUMED_RUN_ID
    assert diag["resumed_by_run_id"] == EXECUTING_RUN_ID
    assert diag["predecessor_run_id"] == PREDECESSOR_RUN_ID
    orch = diag["orchestration"]
    assert orch["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert orch["failed_step"] == "Run lane cycle"
    mech = orch["mechanism"]
    assert mech["status"] == "OBSERVED_LANE_CYCLE_STEP_FAILED"
    assert mech["logs_available"] is False
    assert mech["logs_endpoint_status"] == 403
    assert mech["quantum_expired"] is False
    assert mech["lane_cycle_step_conclusion"] == "failure"
    assert orch["audit"]["skipped"] is True
    assert orch["audit"]["gate_file_written"] is False
    delta = diag["durable_delta"]
    assert delta["classification"] == "ZERO_DURABLE_DELTA"
    assert delta["changed_files"] == 0
    assert delta["snapshot_head"] == delta["predecessor_head"] == ACCEPTED_HEAD
    assert diag["adjudication"] == {
        "status": "UNADJUDICATED", "accepted": False,
        "audit_ref_exists": False, "reason": diag["adjudication"]["reason"]}


def test_state_advances_the_pointer_and_attributes_the_executing_run():
    st = _load(STATE)
    assert st["direction_version"] == 68
    # SUPERSEDED ASSERTION, preserved in git history: this test once required
    # current_cycle_run_id == 41152471808.  Every later operational resume
    # legitimately moves that pointer forward, so pinning it made a historical
    # cycle test fail on every subsequent cycle - the exact defect class this
    # cycle repaired in product/tests/test_cycle_40284658455.py.  What must stay
    # true is THIS cycle's historical attribution block: it names itself as the
    # executing run and 41149776023 as the snapshot it diagnosed, and its two
    # committed evidence files still exist on the tree.
    block = st["cycle_41152471808_operational_resume"]
    assert block["run_id"] == int(EXECUTING_RUN_ID)
    assert block["resumed_snapshot"]["run_id"] == int(RESUMED_RUN_ID)
    assert (ROOT / block["diagnosis"]).is_file()
    assert (ROOT / block["raw_snapshot"]).is_file()
    # The accepted pointer is a moving target for the same reason: a later
    # accept supersedes it.  When it still names the run THIS cycle accepted,
    # its commit must be the accept commit whose containment is verified below.
    if st["accepted_run_id"] == f"CYCLE_{PREDECESSOR_RUN_ID}":
        assert st["accepted_commit"] == ACCEPTED_HEAD
    from product.state_contract import accepted_pointer_evidence
    ev = accepted_pointer_evidence(st, ROOT)
    assert not ev["problems"], ev
    assert ev["gate_ok"] and ev["accept_commit_present"]
    # The accept commit must be CONTAINED in accepted-branch history, not equal
    # to a moving head.  Use the fetched accepted branch when present, else the
    # tree under test (the accepted snapshot or a descendant of it).
    ref = "HEAD"
    try:
        _git("rev-parse", "--verify", "origin/lab/product")
        ref = "origin/lab/product"
    except subprocess.CalledProcessError:
        pass
    _git("merge-base", "--is-ancestor", ACCEPTED_HEAD, ref)
    assert _load(GATE)["gate"] == "PASS"
    hist = {str(h.get("run_id")): h for h in st.get("run_history") or []}
    assert hist[PREDECESSOR_RUN_ID]["status"] == "ACCEPTED"
    assert hist[RESUMED_RUN_ID]["status"].startswith("TEAM_JOB_LANE_CYCLE_STEP_FAILED")
    assert hist[EXECUTING_RUN_ID]["audit_gate"] == "NONE_YET"
    for key, expected in (
        ("continue_recommended", True),
        ("human_gate_ready", False),
        ("machine_gate_ready", False),
        ("packet_admitted", False),
        ("ready_for_owner_session", False),
    ):
        assert st[key] is expected or st[key] == expected, (key, st[key])
    block = st["cycle_41152471808_operational_resume"]
    assert block["resumed_snapshot"]["run_id"] == int(RESUMED_RUN_ID)
    assert (ROOT / block["diagnosis"]).is_file()
    assert (ROOT / block["raw_snapshot"]).is_file()


def test_previous_cycle_test_is_green_on_the_post_acceptance_tree():
    # The defect this resume repairs: the 40284658455 test asserted its own run
    # had no gate and that the accepted pointer was its predecessor, both false
    # after integration.  Re-run it here so the accepted tree cannot rot.
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q",
         "product/tests/test_cycle_40284658455.py"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=300)
    assert proc.returncode == 0, proc.stdout[-4000:] + proc.stderr[-4000:]


def test_audit_readiness_models_the_fifth_mechanism_kind():
    from product import audit_readiness as ar
    prof = ar.select_profile(EXECUTING_RUN_ID)
    assert prof["mechanism_kind"] == "observed_step_failure"
    assert prof["resumed_run_id"] == RESUMED_RUN_ID
    assert prof["delta_kind"] == "zero"
    assert prof["cycle_test"] == "product/tests/test_cycle_41152471808.py"
    assert prof["exit_code"] is None
    # Unknown run ids still fail closed.
    try:
        ar.select_profile("99999999999")
    except SystemExit:
        pass
    else:  # pragma: no cover - defensive
        raise AssertionError("select_profile must fail closed on unknown runs")


def test_vertical_slice_still_produces_a_source_linked_clickable_map():
    with tempfile.TemporaryDirectory(prefix="slice-41152471808-") as tmp:
        proc = subprocess.run(
            [sys.executable, "product/offline_slice.py",
             "--slug", "rent-default", "--top-n", "100",
             "--no-enrich", "--verify", "--quiet", "--out", tmp],
            cwd=str(ROOT), capture_output=True, text=True, timeout=300)
        assert proc.returncode == 0, proc.stdout[-4000:] + proc.stderr[-4000:]
        bundle_path = Path(tmp) / "rent-default.bundle.json"
        bundle = _load(bundle_path)
        rows = bundle.get("decisions") or []
        assert len(rows) >= 40
        assert all(r.get("canonical_url") for r in rows)
        assert all(isinstance(r.get("x"), (int, float))
                   and isinstance(r.get("y"), (int, float)) for r in rows)
        assert len({r.get("cluster_id") for r in rows}) >= 2
        assert any(str(r.get("language") or "") for r in rows)
        summary = _load(Path(tmp) / "summary.json")
        assert summary["verified"] is True
        assert summary["page_contract"] is True
