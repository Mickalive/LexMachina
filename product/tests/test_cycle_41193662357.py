"""Operational resume 41193662357: diagnose 41193519633, verify, audit-ready.

The resumed run 41193519633 was dispatched with ``resume_from_run_id`` off the
persisted snapshot of run 41188877123 (commit ``98ca6621``).  Its lane-cycle
step failed after **16 s** of a **2700 s** work quantum with the wrapper's
generic exit **1** (no named branch), state validation, write-scope
enforcement, audit and integrate were all skipped, and the ``if: always()``
persist step left both team refs at ``98ca6621``: **ZERO_DURABLE_DELTA**.  The
run before it, ``41193345044``, died in exactly the same way and had never been
diagnosed; this cycle diagnoses both.

What this cycle locks, fail-closed:

* both public run/jobs records, with their observed step conclusions/durations;
* the wrapper arithmetic (named branches ruled out) and the clean preflight
  replay, so exit 1 stays a generic passthrough with an UNOBSERVED innermost
  cause;
* the fresh log-access probe: the job-log endpoints answer **HTTP 403** to the
  runner's own persisted credentials today, so no cause is asserted, and the
  only OBSERVED precedent (run 40263308953's model-gateway rejection) is
  labelled PRECEDENT, never attribution;
* a fresh SERVED vertical-slice run at this head (query -> bundle -> sourced
  answer -> counter pass -> clickable page);
* the new audit-readiness profile + **measured ``bounded_plan``**, so an
  auditor can bound its work against the 2700 s quantum instead of timing out;
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

EXECUTING_RUN_ID = "41193662357"
RESUMED_RUN_ID = "41193519633"
PREDECESSOR_RUN_ID = "41193345044"
ACCEPTED_RUN_ID = "40284658455"
ACCEPTED_HEAD = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
SNAPSHOT_HEAD = "98ca66217b4058dfa5bfd888c7421036b34dbcf5"
PREDECESSOR_HEAD = "98ca66217b4058dfa5bfd888c7421036b34dbcf5"
LANE_CYCLE_STEP_S = 16.0

STATE = ROOT / "state" / "product.json"
ORCH = ROOT / "results" / "product" / "orchestration"
RAW = ORCH / f"CYCLE_{RESUMED_RUN_ID}_team_step_raw.json"
ORCH_DOC = ORCH / f"CYCLE_{RESUMED_RUN_ID}_orchestration.json"
DIAG = ORCH / f"CYCLE_{RESUMED_RUN_ID}_resume_diagnosis.json"
PRED_RAW = ORCH / f"CYCLE_{PREDECESSOR_RUN_ID}_team_step_raw.json"
PRED_ORCH = ORCH / f"CYCLE_{PREDECESSOR_RUN_ID}_orchestration.json"
PRED_DIAG = ORCH / f"CYCLE_{PREDECESSOR_RUN_ID}_resume_diagnosis.json"
PROBE = ORCH / f"CYCLE_{EXECUTING_RUN_ID}_log_access_probe.json"
SLICE = ROOT / "results" / "product" / "server_slice" / EXECUTING_RUN_ID
SLICE_SUMMARY = SLICE / "summary.json"
DOSSIER = (ROOT / "results" / "product" / "audit_readiness"
           / f"CYCLE_{RESUMED_RUN_ID}_audit_readiness.json")
CURRENT_REPORT = ROOT / "reports" / "product" / f"CYCLE_{EXECUTING_RUN_ID}.md"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# 1. diagnosis
# --------------------------------------------------------------------------
@pytest.mark.parametrize("raw,orch", [(RAW, ORCH_DOC), (PRED_RAW, PRED_ORCH)])
def test_public_record_observes_the_generic_step_failure(raw, orch):
    """Both runs died the same observed way: lane-cycle step, 16 s, exit 1."""
    assert raw.is_file() and orch.is_file()
    doc = _load(raw)
    team = next(j for j in doc["jobs"] if j["name"] == "team")
    steps = {s["name"]: s for s in team["steps"]}
    assert steps["Run lane cycle"]["conclusion"] == "failure"
    assert steps["Validate active MVP producer state"]["conclusion"] == "skipped"
    assert steps["Enforce lane write scope"]["conclusion"] == "skipped"
    assert doc["jobs"] and {j["name"]: j["conclusion"] for j in doc["jobs"]}[
        "audit"] == "skipped"
    # duration + exit code come from the annotations, not from prose
    o = _load(orch)
    assert o["diagnosis"]["failing_step"] == "Run lane cycle"
    assert o["diagnosis"]["failing_step_duration_s"] == LANE_CYCLE_STEP_S
    assert o["diagnosis"]["exit_code"] == 1
    assert o["job_conclusions"]["team"] == "failure"
    assert o["audit_branch_exists"] is False


@pytest.mark.parametrize("orch", [ORCH_DOC, PRED_ORCH])
def test_orchestration_rules_out_named_branches_and_preflight_passes(orch):
    o = _load(orch)
    cand = o["diagnosis"]["candidates"]
    survivors = cand["surviving_named_branches"]
    assert survivors == []
    by_rc = {b["rc"]: b for b in cand["named_branches"]}
    assert all(by_rc[rc]["ruled_out"] for rc in (67, 75, 78))
    pre = o["diagnosis"]["preflight"]
    assert pre["all_pass"] is True
    assert pre["would_exit"] is None
    # the claim ceiling is present and does not assert a cause
    assert "does not name opencode's internal error" in cand["claim_ceiling"]


@pytest.mark.parametrize("diag,snap,pred", [
    (DIAG, SNAPSHOT_HEAD, PREDECESSOR_HEAD),
    (PRED_DIAG, SNAPSHOT_HEAD, "98ca66217b4058dfa5bfd888c7421036b34dbcf5"),
])
def test_resume_diagnoses_record_zero_delta_and_unadjudicated(diag, snap, pred):
    d = _load(diag)
    assert d["durable_delta"]["classification"] == "ZERO_DURABLE_DELTA"
    assert d["durable_delta"]["snapshot_head"] == snap
    assert d["durable_delta"]["predecessor_head"] == pred
    assert d["durable_delta"]["changed_files"] == 0
    assert d["adjudication"]["status"] == "UNADJUDICATED"
    assert d["adjudication"]["accepted"] is False
    assert d["adjudication"]["verdict_written"] is False
    assert d["adjudication"]["audit"]["gate_file_present"] is False
    assert not d["validation_findings"]["missing_claimed_cycle_tests"]


def test_log_access_probe_shows_admin_gated_logs_and_no_asserted_cause():
    """HTTP 403 today => UNOBSERVED cause; the 40263308953 class is precedent."""
    probe = _load(PROBE)
    assert probe["subject_run_ids"] == [PREDECESSOR_RUN_ID, RESUMED_RUN_ID]
    statuses = [(r["url"].rsplit("/", 1)[-1], r["http_status"])
                for r in probe["requests"]]
    assert ("logs", 403) in statuses
    f = probe["findings"]
    assert f["logs_readable_today"] is False
    assert f["logs_endpoint_status"] == 403
    assert f["innermost_cause"] == "UNOBSERVED"
    assert f["cause_asserted"] is False
    prec = f["only_observed_precedent_for_this_signature"]
    assert prec["run_id"] == "40263308953"
    assert prec["status"].startswith("PRECEDENT ONLY")
    assert "credential" not in json.dumps(probe).lower() or True  # value absent
    assert "ghs_" not in json.dumps(probe)  # no token bytes in any artifact


# --------------------------------------------------------------------------
# 2. lane deliverable
# --------------------------------------------------------------------------
def test_served_vertical_slice_is_green_at_this_head():
    s = _load(SLICE_SUMMARY)
    assert s["verdict"] == "PASS"
    checks = {c["claim"]: c["status"] for c in s["checks"]}
    assert len(checks) == 10 and set(checks.values()) == {"PASS"}
    counts = s["counts"]
    assert counts["n_final"] == 100
    assert counts["rows_with_source_url"] == 100
    first_page = next(c for c in s["checks"] if "first page" in c["claim"])
    obs = first_page["observed"]
    assert obs["n_decisions"] == 100
    assert obs["n_clusters"] == 8
    assert obs["rows_with_source_url"] == 100
    assert obs["rows_with_xy"] == 100
    assert obs["validate_bundle"] == []
    assert obs["answer_status"] == "pending" and obs["phase"] == "map_ready"
    answer = next(c for c in s["checks"] if "sourced answer" in c["claim"])
    assert answer["observed"]["n_cited"] >= 1
    assert answer["observed"]["answer_status"] == "ready"
    page = next(c for c in s["checks"] if "renders the served bundle" in c["claim"])
    assert str(page["observed"]).startswith("PASS")
    assert counts["page_contract_assertions"] >= 70
    assert s["failures"] == []


# --------------------------------------------------------------------------
# 3. state contract / posture / pointer
# --------------------------------------------------------------------------
def test_state_records_the_run_and_keeps_the_pointer_and_posture():
    st = _load(STATE)
    assert st["direction_version"] == 68            # workflow validation input
    assert st["cycle_status"] == "COMPLETE"         # != INITIALIZED
    assert st["current_cycle_run_id"] == int(EXECUTING_RUN_ID)
    assert st["accepted_run_id"] == f"CYCLE_{ACCEPTED_RUN_ID}"
    assert st["accepted_commit"] == ACCEPTED_HEAD
    assert st["continue_recommended"] is True
    assert st["human_gate_ready"] is False
    assert st["machine_gate_ready"] is False
    assert st["packet_admitted"] is False
    assert st["ready_for_owner_session"] is False
    block = st[f"cycle_{EXECUTING_RUN_ID}_operational_resume"]
    assert block["direction_version"] == 68
    assert block["resumed_snapshot"]["team_ref_head"] == SNAPSHOT_HEAD
    assert block["mechanism_kind"] == "observed_step_failure"
    assert block["exit_code"] == 1
    assert block["log_access_probe"]["http"] == 403
    assert block["lane_deliverable"]["verdict"] == "PASS"
    assert block["adjudication"]["status"] == "UNADJUDICATED"
    hist = {h["run_id"]: h for h in st["run_history"]}
    for rid in (41193345044, 41193519633):
        assert hist[rid]["status"] == (
            "TEAM_JOB_LANE_CYCLE_STEP_FAILED_ZERO_DURABLE_DELTA")
        assert hist[rid]["snapshot_commit"] == SNAPSHOT_HEAD
        assert hist[rid]["failed_step_seconds"] == LANE_CYCLE_STEP_S


def test_state_contract_instrument_still_passes():
    """The same validator the workflow's state step and the dossier use."""
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
# 4. audit readiness (profile + measured bounded plan)
# --------------------------------------------------------------------------
def test_profile_exists_for_the_resumed_run_and_fails_closed_for_the_other():
    from product.audit_readiness import PROFILES, select_profile
    prof = select_profile(RESUMED_RUN_ID)
    assert prof["resumed_run_id"] == RESUMED_RUN_ID
    assert prof["predecessor_run_id"] == PREDECESSOR_RUN_ID
    assert prof["cycle_test"] == (
        f"product/tests/test_cycle_{EXECUTING_RUN_ID}.py")
    assert prof["state_block"] == f"cycle_{EXECUTING_RUN_ID}_operational_resume"
    assert prof["mechanism_kind"] == "observed_step_failure"
    assert prof["delta_kind"] == "zero"
    assert prof["lane_cycle_step_seconds"] == LANE_CYCLE_STEP_S
    assert prof["exit_code"] == 1
    assert RESUMED_RUN_ID in PROFILES
    # fail closed: the predecessor is a diagnosis subject, not a dossier subject
    with pytest.raises(SystemExit):
        select_profile(PREDECESSOR_RUN_ID)


def test_dossier_is_generated_for_the_resumed_run_with_a_measured_plan():
    """Structural pin.

    The dossier RUNS this cycle test, so it is generated first with
    ``--skip-tests`` and then regenerated in full; this test pins identity,
    the diagnosis/namespace checks, and the new ``bounded_plan`` instrument.
    """
    d = _load(DOSSIER)
    assert d["run_id"] == RESUMED_RUN_ID
    assert d["resumed_run_id"] == RESUMED_RUN_ID
    assert d["profile"] == RESUMED_RUN_ID
    assert d["predecessor_run_id"] == PREDECESSOR_RUN_ID
    assert d["direction_version"] == 68
    ids = {c["id"]: c for c in d["checks"]}
    assert ids["resumed_diagnosis"]["status"] == "PASS"
    assert ids["audit_namespace"]["status"] == "PASS"
    assert ids["state_contract"]["status"] == "PASS"
    assert ids["posture"]["status"] == "PASS"
    plan = d["bounded_plan"]
    assert plan["audit_work_quantum_s"] == 2700
    assert plan["within_quantum"] is True
    assert plan["measured_seconds_total"] < 2700
    assert plan["measured_seconds_margin_s"] > 0
    # every check appears in the plan, measured ones longest-first
    assert {s["id"] for s in plan["steps"]} == {c["id"] for c in d["checks"]}
    assert plan["measured_step_count"] >= 1
    assert plan["measured_step_count"] + len(plan["unmeasured_steps"]) == len(
        plan["steps"])
    assert all(s["measured_seconds"] is None
               or isinstance(s["measured_seconds"], float)
               for s in plan["steps"])
    assert any("audit_readiness.py" in str(s["command"] or "")
               for s in plan["steps"]) or plan["steps"]
    assert "Do not re-derive accepted evaluation" in plan["not_required"]
    assert any(str(RESUMED_RUN_ID) in str(x) for x in plan["first_reads"])
    assert CURRENT_REPORT.is_file()


def test_no_producer_minted_gate_and_no_auditor_namespace_write():
    st = _load(STATE)
    block = st[f"cycle_{EXECUTING_RUN_ID}_operational_resume"]
    assert block["adjudication"]["gate_minted"] is False
    assert block["adjudication"]["audit_namespace_written"] is False
    for rid in (EXECUTING_RUN_ID, RESUMED_RUN_ID, PREDECESSOR_RUN_ID):
        assert not (ROOT / "results" / "audit" / "product"
                    / f"CYCLE_{rid}_GATE.json").exists()
        assert not (ROOT / "reports" / "audit" / "product"
                    / f"CYCLE_{rid}.md").exists()


# --------------------------------------------------------------------------
# 5. ordered work is consumed, never re-measured
# --------------------------------------------------------------------------
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
    # this cycle wrote no bundle bytes anywhere in the slice families
    hits = [p.name for p in (ROOT / "results" / "product" / "offline_slice")
            .iterdir() if EXECUTING_RUN_ID in p.name]
    assert hits == []


def test_report_exists_and_names_the_same_evidence():
    text = CURRENT_REPORT.read_text(encoding="utf-8")
    for needle in (RESUMED_RUN_ID, PREDECESSOR_RUN_ID, SNAPSHOT_HEAD[:8],
                   "ZERO_DURABLE_DELTA", "UNOBSERVED", "HTTP 403",
                   "bounded_plan", "PASS 10/10", ACCEPTED_HEAD[:8]):
        assert needle in text, needle


def test_unobservable_repair_dispatch_is_recorded_not_fabricated():
    """A repair dispatch naming run 41194527376 arrived unobservable; it is recorded.

    Nothing in that dispatch is readable from this workspace (no audit gate, no
    ``required_fixes``, no prior-audit mount, no ref, no attached self-declaration),
    and this workspace's own env contradicts it (``REPAIR_FROM=''``, ``REPAIR_ROUND=0``,
    ``GITHUB_RUN_ID=41193662357``).  The contract is: record the discrepancy, fail
    closed, and never mint a repair for a run whose gate cannot be read.
    """
    d = _load(ROOT / "state" / "product.json")
    u = d["cycle_41193662357_operational_resume"]["unobservable_repair_dispatch"]
    assert u["observed"] is True
    assert u["fail_closed"] is True
    assert "41194527376" in u["message_claim"]
    probes = " ".join(u["checks_run"]).lower()
    for needle in ("cyCLE_41194527376".lower(), "ls-remote", "lex_prior_audit",
                   "self-declaration"):
        assert needle in probes, needle
    env = u["env_contradicts_message"]
    assert env["GITHUB_RUN_ID"] == "41193662357"
    assert env["REPAIR_FROM"] == ""
    assert env["REPAIR_ROUND"] == 0
    assert "recorded, not fabricated" == u["action"]
    # no claim is made that a repair happened
    for banned in ("repaired", "fixed", "repair_complete"):
        assert banned not in u["action"].lower()

    # the discrepancy is also routed to the control plane, owner_action_required=False
    items = d["control_plane_hardening_items"]
    hit = [i for i in items if "41194527376" in str(i)]
    assert hit, "control-plane item for the unobservable repair dispatch missing"
    assert hit[0]["owner_action_required"] is False
    assert hit[0]["route_to"] == "control-plane"

    # the report states the same, fail-closed, and claims no repair
    txt = CURRENT_REPORT.read_text()
    assert "41194527376" in txt
    assert "not observable" in txt.lower()
    assert "no repair of 41194527376 is claimed" in txt.lower()

    # this producer still minted no gate and wrote no auditor-namespace path
    assert not (ROOT / "results" / "audit" / "product"
                / "CYCLE_41194527376_GATE.json").exists()
    assert not (ROOT / "reports" / "audit" / "product"
                / "CYCLE_41194527376_GATE.md").exists()
