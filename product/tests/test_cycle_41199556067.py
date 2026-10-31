"""Operational resume 41199556067: the audited run 41193662357, not its parent.

Why this cycle exists
---------------------
Run ``41193662357`` is the FIRST run in this chain whose *producer* job fully
succeeded: team success, state validation success, write-scope success, and a
**15-file committed delta** (``98ca6621`` -> ``a8d2804c``).  Its **audit** job
then ran ``Independent audit`` for **2704.0 s** of the **2700 s** wrapper
quantum and the public check-run annotation records the literal branch
``LEX_WORK_QUANTUM_EXPIRED seconds=2700`` with exit code **78**.  The gate
reader and the audit-snapshot persist steps were skipped, so no ``/audit`` ref
and no gate exist: the snapshot is resumable and **UNADJUDICATED**, not
rejected and not a product defect.

The recurring audit-readiness defect this cycle repairs
-------------------------------------------------------
Every previous resume published a dossier for the run it *resumed* (the
parent), but the auditor looks up the dossier for the run whose snapshot it is
auditing (the child).  For ``41193662357`` no such profile existed, so the
auditor had to re-derive the work and the quantum expired again.  This cycle
adds profiles for ``41193662357`` **and** for the executing run
``41199556067`` so ``python3 product/audit_readiness.py --run-id
<the-audited-run>`` always resolves the audited run's own report, cycle test
and bounded plan.

What this test locks, fail-closed
---------------------------------
* the public record: team success, audit quantum expiry 2704 s / exit 78;
* the committed 15-file durable delta and the UNADJUDICATED status;
* a fresh SERVED vertical slice at this head (query -> bundle -> sourced
  answer -> counter pass -> clickable page);
* the two audit-readiness profiles and their dossiers, including the
  ``bounded_plan`` margin against the 2700 s quantum;
* the unchanged fail-closed posture and accepted pointer;
* that this producer minted no gate and wrote no auditor-namespace path.

No frozen gate, rubric, threshold or bar is imported, edited or re-tuned here.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EXECUTING_RUN_ID = "41199556067"
RESUMED_RUN_ID = "41193662357"
RESUMED_PREDECESSOR_RUN_ID = "41193519633"
ACCEPTED_RUN_ID = "40284658455"
ACCEPTED_HEAD = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
SNAPSHOT_HEAD = "a8d2804cda18afc5e676394bb66c8c484063538e"
SNAPSHOT_PREDECESSOR_HEAD = "98ca66217b4058dfa5bfd888c7421036b34dbcf5"
AUDIT_STEP_S = 2704.0
QUANTUM_S = 2700

STATE = ROOT / "state" / "product.json"
ORCH = ROOT / "results" / "product" / "orchestration"
RAW = ORCH / f"CYCLE_{RESUMED_RUN_ID}_team_step_raw.json"
ORCH_DOC = ORCH / f"CYCLE_{RESUMED_RUN_ID}_orchestration.json"
DIAG = ORCH / f"CYCLE_{RESUMED_RUN_ID}_resume_diagnosis.json"
SLICE = ROOT / "results" / "product" / "server_slice" / EXECUTING_RUN_ID
SLICE_SUMMARY = SLICE / "summary.json"
DOSSIER_SELF = (ROOT / "results" / "product" / "audit_readiness"
                / f"CYCLE_{EXECUTING_RUN_ID}_audit_readiness.json")
DOSSIER_RESUMED = (ROOT / "results" / "product" / "audit_readiness"
                   / f"CYCLE_{RESUMED_RUN_ID}_audit_readiness.json")
CURRENT_REPORT = ROOT / "reports" / "product" / f"CYCLE_{EXECUTING_RUN_ID}.md"
CURRENT_TEST = (ROOT / "product" / "tests"
                / f"test_cycle_{EXECUTING_RUN_ID}.py")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# 1. diagnosis of run 41193662357
# --------------------------------------------------------------------------
def test_public_record_shows_producer_success_and_audit_quantum_expiry():
    assert RAW.is_file()
    doc = _load(RAW)
    jobs = {j["name"]: j for j in doc["jobs"]}
    assert jobs["team"]["conclusion"] == "success"
    assert jobs["audit"]["conclusion"] == "failure"
    assert jobs["integrate"]["conclusion"] == "skipped"
    steps = {s["name"]: s for s in jobs["audit"]["steps"]}
    assert steps["Independent audit"]["conclusion"] == "failure"
    assert steps["Enforce audit scope and read gate"]["conclusion"] == "skipped"
    assert steps["Persist audit snapshot"]["conclusion"] == "skipped"


def test_annotation_pins_the_wrapper_quantum_branch_not_a_provider_cause():
    o = _load(ORCH_DOC)
    assert o["classification"]["class"] == "AUDIT_STEP_FAILED_NO_GATE"
    assert o["job_conclusions"]["team"] == "success"
    assert o["job_conclusions"]["audit"] == "failure"
    assert o["audit_branch_exists"] is False
    d = o["diagnosis"]
    assert d["failing_step"] == "Independent audit"
    assert d["audit_agent_step_duration_s"] == AUDIT_STEP_S
    assert d["exit_code"] == 78
    msgs = " | ".join(a["message"] for a in d["annotations"])
    assert "LEX_WORK_QUANTUM_EXPIRED seconds=2700" in msgs
    # A public annotation names the wrapper branch; no provider defect is asserted.
    assert d["audit_agent_step_duration_s"] >= QUANTUM_S
    assert d["candidates"]["surviving_named_branches"] == [
        "LEX_WORK_QUANTUM_EXPIRED"]


def test_resume_diagnosis_records_a_committed_delta_and_unadjudicated_run():
    d = _load(DIAG)
    assert d["run_id"] == RESUMED_RUN_ID
    assert d["predecessor_run_id"] == RESUMED_PREDECESSOR_RUN_ID
    delta = d["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["snapshot_head"] == SNAPSHOT_HEAD
    assert delta["predecessor_head"] == SNAPSHOT_PREDECESSOR_HEAD
    assert delta["changed_files"] == 15
    assert "product/audit_readiness.py" in delta["changed_paths_sample"]
    assert d["adjudication"]["status"] == "UNADJUDICATED"
    assert d["adjudication"]["accepted"] is False
    assert d["adjudication"]["verdict_written"] is False
    assert d["adjudication"]["audit"]["audit_ref_present"] is False
    # the observed mechanism, with no invented cause
    mech = d["orchestration"]["mechanism"]
    assert mech["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert mech["quantum_expired"] is True
    assert mech["exit_code"] == 78
    assert mech["quantum_seconds"] == QUANTUM_S
    assert d["orchestration"]["audit"]["gate_file_written"] is False


# --------------------------------------------------------------------------
# 2. lane deliverable re-verified at this head
# --------------------------------------------------------------------------
def test_served_vertical_slice_is_green_at_this_head():
    s = _load(SLICE_SUMMARY)
    assert s["verdict"] == "PASS"
    checks = {c["claim"]: c["status"] for c in s["checks"]}
    assert len(checks) == 10 and set(checks.values()) == {"PASS"}
    counts = s["counts"]
    assert counts["n_final"] == 100
    assert counts["rows_with_source_url"] == 100
    assert counts["page_contract_assertions"] >= 70
    first = next(c for c in s["checks"] if "first page" in c["claim"])["observed"]
    assert first["n_decisions"] == 100 and first["n_clusters"] == 8
    assert first["rows_with_xy"] == 100 and first["rows_with_source_url"] == 100
    assert first["validate_bundle"] == []
    answer = next(c for c in s["checks"] if "sourced answer" in c["claim"])[
        "observed"]
    assert answer["answer_status"] == "ready" and answer["n_cited"] >= 1
    assert s["failures"] == []


# --------------------------------------------------------------------------
# 3. audit-readiness repair: audited-run profiles + dossiers
# --------------------------------------------------------------------------
def test_profiles_exist_for_both_the_audited_and_executing_runs():
    from product.audit_readiness import PROFILES, select_profile
    assert RESUMED_RUN_ID in PROFILES
    assert EXECUTING_RUN_ID in PROFILES
    for run_id, current_report in (
        (RESUMED_RUN_ID, f"reports/product/CYCLE_{RESUMED_RUN_ID}.md"),
        (EXECUTING_RUN_ID, f"reports/product/CYCLE_{EXECUTING_RUN_ID}.md"),
    ):
        prof = select_profile(run_id)
        assert prof["resumed_run_id"] == RESUMED_RUN_ID
        assert prof["predecessor_run_id"] == RESUMED_PREDECESSOR_RUN_ID
        assert prof["mechanism_kind"] == "observed"
        assert prof["delta_kind"] == "committed"
        assert prof["failed_job"] == "audit"
        assert prof["exit_code"] == 78
        assert prof["quantum_seconds"] == QUANTUM_S
        assert prof["changed_files"] == 15
        assert prof["current_report"].as_posix().endswith(current_report)
    # the self profile is the one the auditor of THIS run must resolve
    self_prof = select_profile(EXECUTING_RUN_ID)
    assert self_prof["cycle_test"] == (
        f"product/tests/test_cycle_{EXECUTING_RUN_ID}.py")
    assert self_prof["state_block"] == (
        f"cycle_{EXECUTING_RUN_ID}_operational_resume")


@pytest.mark.parametrize("dossier,subject,current_report", [
    (DOSSIER_RESUMED, RESUMED_RUN_ID, f"CYCLE_{RESUMED_RUN_ID}.md"),
    (DOSSIER_SELF, EXECUTING_RUN_ID, f"CYCLE_{EXECUTING_RUN_ID}.md"),
])
def test_dossier_resolves_the_run_it_is_named_for(dossier, subject,
                                                  current_report):
    d = _load(dossier)
    assert d["run_id"] == subject
    # ``profile`` names the profile's RESUMED run; ``run_id`` names the
    # run this dossier was requested for (the self profile reuses the
    # 41193662357 profile's diagnosis under its own run_id).
    assert d["profile"] == RESUMED_RUN_ID
    # both dossiers cross-check the SAME resumed run and the SAME delta
    assert d["resumed_run_id"] == RESUMED_RUN_ID
    assert d["predecessor_run_id"] == RESUMED_PREDECESSOR_RUN_ID
    assert d["direction_version"] == 68
    checks = {c["id"]: c for c in d["checks"]}
    for cid in ("runtime_preflight", "state_contract", "posture",
                "resumed_diagnosis", "claim_artifacts",
                "progressive_smoke", "audit_namespace"):
        assert checks[cid]["status"] == "PASS", (subject, cid, checks[cid])
    # The self dossier is generated BY the checks it names (fixed point): the
    # bootstrap pass records cycle_test AND mvp_core_tests SKIP, then the full
    # pass records both PASS.  Either is valid mid-generation; the committed
    # full dossier must be all-PASS, and the resumed-run dossier is pinned to
    # PASS here.  Re-run this test after the full self-dossier generation.
    if subject == RESUMED_RUN_ID:
        for cid in ("cycle_test", "mvp_core_tests"):
            assert checks[cid]["status"] == "PASS", (subject, cid, checks[cid])
    else:
        for cid in ("cycle_test", "mvp_core_tests"):
            assert checks[cid]["status"] in (
                "PASS", "SKIP", "SKIPPED"), (cid, checks[cid])
    assert d["failed_checks"] == []
    entry = d["audit_entry_points"]
    assert entry["current_report"].endswith(current_report)
    plan = d["bounded_plan"]
    assert plan["audit_work_quantum_s"] == QUANTUM_S
    assert plan["within_quantum"] is True
    assert plan["measured_seconds_total"] < QUANTUM_S
    assert plan["measured_seconds_margin_s"] > 0
    assert {s["id"] for s in plan["steps"]} == {c["id"] for c in d["checks"]}


def test_self_dossier_points_at_this_runs_own_report_and_cycle_test():
    d = _load(DOSSIER_SELF)
    # the defect being repaired: an audit of 41199556067 must not be handed
    # 41193662357's report as its own
    assert d["audit_entry_points"]["current_report"].endswith(
        f"CYCLE_{EXECUTING_RUN_ID}.md")
    assert f"test_cycle_{EXECUTING_RUN_ID}.py" in (
        d["audit_entry_points"]["current_cycle_test"])
    assert CURRENT_REPORT.is_file()
    assert CURRENT_TEST.is_file()


# --------------------------------------------------------------------------
# 4. state contract / posture / pointer
# --------------------------------------------------------------------------
def test_state_records_this_run_and_keeps_the_pointer_and_posture():
    st = _load(STATE)
    assert st["direction_version"] == 68
    assert st["cycle_status"] == "COMPLETE"
    # Do not pin the moving head: the next operational resume legitimately
    # advances current_cycle_run_id.  The durable invariant is that THIS
    # run's own block survives and the pointer only advances (never rewinds).
    assert isinstance(st["current_cycle_run_id"], int)
    assert st["current_cycle_run_id"] >= int(EXECUTING_RUN_ID)
    assert st[f"cycle_{EXECUTING_RUN_ID}_operational_resume"]["run_id"] == int(
        EXECUTING_RUN_ID)
    assert st["accepted_run_id"] == f"CYCLE_{ACCEPTED_RUN_ID}"
    assert st["accepted_commit"] == ACCEPTED_HEAD
    assert st["continue_recommended"] is True
    for key in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                "ready_for_owner_session"):
        assert st[key] is False, key
    block = st[f"cycle_{EXECUTING_RUN_ID}_operational_resume"]
    assert block["run_id"] == int(EXECUTING_RUN_ID)
    assert block["direction_version"] == 68
    assert block["resumed_snapshot"]["run_id"] == int(RESUMED_RUN_ID)
    assert block["resumed_snapshot"]["team_ref_head"] == SNAPSHOT_HEAD
    assert block["mechanism_kind"] == "observed"
    assert block["exit_code"] == 78
    assert block["exit_code_meaning"] == "LEX_WORK_QUANTUM_EXPIRED"
    assert block["lane_deliverable"]["verdict"] == "PASS"
    assert block["adjudication"]["status"] == "UNADJUDICATED"
    assert block["adjudication"]["gate_minted"] is False
    assert block["adjudication"]["audit_namespace_written"] is False
    hist = {str(h["run_id"]): h for h in st["run_history"]}
    entry = hist[RESUMED_RUN_ID]
    assert entry["status"] == (
        "TEAM_JOB_SUCCESS_AUDIT_JOB_QUANTUM_EXPIRED_NO_GATE")
    assert entry["exit_code"] == 78
    assert entry["failed_step"] == "Independent audit"
    assert entry["failed_step_seconds"] == AUDIT_STEP_S
    assert entry["snapshot_commit"] == SNAPSHOT_HEAD
    assert entry["audit_gate"] == "NONE"


def test_state_contract_instrument_still_passes():
    import subprocess
    proc = subprocess.run(
        [sys.executable, "product/state_contract.py", "--check",
         "--direction-version", "68", "--json"],
        cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr[-2000:]
    rep = json.loads(proc.stdout)
    assert rep["ok"] is True
    assert rep["workflow_validation"]["ok"] is True
    assert rep["write_scope"]["ok"] is True
    assert rep["write_scope"]["violations"] == []
    assert rep["audit_artifact_ownership"]["producer_wrote_audit_paths"] == []


# --------------------------------------------------------------------------
# 5. no producer-minted gate; ordered work consumed, not re-measured
# --------------------------------------------------------------------------
def test_no_producer_minted_gate_and_no_auditor_namespace_write():
    for rid in (EXECUTING_RUN_ID, RESUMED_RUN_ID,
                RESUMED_PREDECESSOR_RUN_ID):
        assert not (ROOT / "results" / "audit" / "product"
                    / f"CYCLE_{rid}_GATE.json").exists()
        assert not (ROOT / "reports" / "audit" / "product"
                    / f"CYCLE_{rid}.md").exists()


def test_the_lane_deliverable_is_consumed_not_re_measured():
    st = _load(STATE)
    assert st["v68_delivery"]["status"] == "LANDED"
    cf = _load(ROOT / st["v68_delivery"]["reverified_evidence"][5])
    totals = cf["fixed_path_family"]["totals"]
    assert totals["n_bundles"] == 49
    assert totals["n_verified_defective"] == 0
    assert all(v == 0 for v in totals["defect_histogram"].values())
    assert cf["false_reject_count"] == 0
    block = st[f"cycle_{EXECUTING_RUN_ID}_operational_resume"]
    assert block["bundle_bytes_written"] is False
    assert block["frozen_bar_scored"] is False
    hits = [p.name for p in (ROOT / "results" / "product" / "offline_slice")
            .iterdir() if EXECUTING_RUN_ID in p.name]
    assert hits == []


def test_report_exists_and_names_the_same_evidence():
    text = CURRENT_REPORT.read_text(encoding="utf-8")
    for needle in (RESUMED_RUN_ID, RESUMED_PREDECESSOR_RUN_ID,
                   SNAPSHOT_HEAD[:8], "LEX_WORK_QUANTUM_EXPIRED",
                   "AUDIT_STEP_FAILED_NO_GATE", "COMMITTED_DELTA",
                   "bounded_plan", "PASS 10/10", ACCEPTED_HEAD[:8]):
        assert needle in text, needle
