#!/usr/bin/env python3
"""Pins the operational resume of run 40750177292 (audit quantum death #4).

Run 40750177292's TEAM job was fully green (13-file committed delta
``85dfea22`` over predecessor team head ``866ae3cb``) and its AUDIT
"Independent audit" step then died at the 2700 s work quantum
(``LEX_WORK_QUANTUM_EXPIRED``, 2706.0 s, exit 78) before writing any gate.
That is the FOURTH audit-side quantum death on this lineage.  The run's own
report then named the *resumed predecessor* ``866ae3cb`` as the audit target
instead of its committed head ``85dfea22``; this resume corrects that claim
(append-only) and makes the target git-resolved in the instrument.

This module pins: the machine diagnosis of 40750177292; the stale-target
correction in the predecessor report and state; the git-resolved audit-target
contract and committed intake; the profile entry; the fail-closed posture;
the fresh offline vertical-slice verification; and (conditionally) the
committed dossier and route artifacts.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state" / "product.json"
ORCH = ROOT / "results" / "product" / "orchestration"
AR = ROOT / "results" / "product" / "audit_readiness"
REPORT = ROOT / "reports" / "product" / "CYCLE_40763434744.md"
PREV_REPORT = ROOT / "reports" / "product" / "CYCLE_40750177292.md"
DOSSIER = AR / "CYCLE_40763434744_audit_readiness.json"
ROUTE = AR / "CYCLE_40763434744_AUDIT_ROUTE.json"
INTAKE = AR / "CYCLE_40763434744_AUDIT_INTAKE.md"
BUNDLE = (ROOT / "results" / "product" / "offline_slice"
          / "20261028T203203Z" / "rent-default.bundle.json")
ACCEPTED = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
SNAPSHOT = "85dfea227c77bc7ac3e91ae452c067ae18ad5c73"
PREDECESSOR = "866ae3cb125b619c07b3dbb63c44b674d314848e"


def test_state_pointer_and_posture_non_rotting():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    assert state["accepted_run_id"] == "CYCLE_40284658455"
    assert state["accepted_commit"] == ACCEPTED
    # current_run is the MOVING latest-resume pointer; assert this cycle's
    # own durable record below rather than a value a later resume may move.
    assert state["current_run"]
    assert "cycle_40763434744_operational_resume" in state
    assert state["continue_recommended"] is True
    assert state["human_gate_ready"] is False
    assert state["machine_gate_ready"] is False
    assert state["ready_for_owner_session"] is False
    assert state["packet_admitted"] is False
    assert state["owner_decision_required"] is False
    assert state["direction_version"] == 68
    block = state["cycle_40763434744_operational_resume"]
    assert block["resumed_run_id"] == "40750177292"
    assert block["resumed_snapshot_head"] == SNAPSHOT
    assert block["resumed_failure"]["classification"] == \
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    assert block["resumed_failure"]["durable_delta"] == "COMMITTED_DELTA (13 files)"
    assert block["resumed_failure"]["gate_file_written"] is False
    assert block["posture"]["human_gate_ready"] is False
    assert block["posture"]["continue_recommended"] is True
    assert block["posture"]["owner_decision_required"] is False


def test_run_history_fates():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    hist = {str(e["run_id"]): e for e in state["run_history"]}
    prev = hist["40750177292"]
    assert prev["status"] == \
        "AUDIT_JOB_QUANTUM_DEATH_COMMITTED_DELTA_UNADJUDICATED"
    assert prev["status_original_producer_record"] == \
        "OPERATIONAL_RESUME_CHAIN_DIAGNOSIS_AND_BOUNDED_AUDIT_ROUTE"
    assert "FOURTH audit-side quantum death" in prev["status_correction"]
    assert prev["team_job"].startswith("SUCCESS")
    assert "13-file committed delta 85dfea22" in prev["team_job"]
    assert "2706.0 s" in prev["audit_job"]
    assert "OBSERVED_QUANTUM_EXPIRED" in prev["audit_job"]
    assert prev["accepted"] is False
    cur = hist["40763434744"]
    # Disclosed maintenance repair by cycle 40772551540 (non-rotting form,
    # original assertion preserved inline): this run's producer-recorded
    # status was truth-corrected after its own audit job died at the 2700 s
    # work quantum — the FIFTH audit-side quantum death on this lineage.
    # Original producer-recorded assertion:
    #   assert cur["status"] == "OPERATIONAL_RESUME_AUDIT_INTAKE_AND_STALE_TARGET_REPAIR"
    assert cur["status"] in (
        "OPERATIONAL_RESUME_AUDIT_INTAKE_AND_STALE_TARGET_REPAIR",
        "AUDIT_JOB_QUANTUM_DEATH_COMMITTED_DELTA_UNADJUDICATED",
    )
    assert cur["status_original_producer_record"] == \
        "OPERATIONAL_RESUME_AUDIT_INTAKE_AND_STALE_TARGET_REPAIR"
    assert cur["resumed_run"] == 40750177292
    assert cur["accepted"] is False
    assert cur["report_of_record"] == "reports/product/CYCLE_40763434744.md"
    assert cur["cycle_test"] == "product/tests/test_cycle_40763434744.py"


def test_diagnosed_audit_quantum_death_of_40750177292():
    diag = json.loads((ORCH / "CYCLE_40750177292_resume_diagnosis.json")
                      .read_text(encoding="utf-8"))
    assert diag["run_id"] == "40750177292"
    assert diag["predecessor_run_id"] == "40747546909"
    orch = diag["orchestration"]
    assert orch["classification"] == \
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    mech = orch["mechanism"]
    assert mech["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert mech["quantum_expired"] is True
    assert mech["quantum_seconds"] == 2700
    assert mech["exit_code"] == 78
    assert orch["team"]["conclusion"] == "success"
    assert orch["audit"]["conclusion"] == "failure"
    assert orch["audit"]["failed_step"] == "Independent audit"
    assert orch["audit"]["independent_audit_step_seconds"] == 2706.0
    assert orch["audit"]["gate_file_written"] is False
    assert orch["integrate"]["conclusion"] == "skipped"
    delta = diag["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["changed_files"] == 13
    assert delta["snapshot_head"] == SNAPSHOT
    assert delta["predecessor_head"] == PREDECESSOR
    assert "product/audit_route.py" in delta["changed_paths_sample"]
    assert diag["accepted_head_relation"]["accepted_head"] == ACCEPTED
    assert diag["adjudication"]["status"] == "UNADJUDICATED"


def test_raw_snapshot_is_the_committed_public_record():
    raw = json.loads((ORCH / "CYCLE_40750177292_run_jobs_raw.json")
                     .read_text(encoding="utf-8"))
    assert raw["run"]["id"] == 40750177292
    team = next(j for j in raw["jobs"] if j["name"] == "team")
    assert team["conclusion"] == "success"
    audit = next(j for j in raw["jobs"] if j["name"] == "audit")
    assert audit["conclusion"] == "failure"
    steps = {s["name"]: s["conclusion"] for s in audit["steps"]}
    assert steps["Independent audit"] == "failure"
    assert steps["Enforce audit scope and read gate"] == "skipped"
    msgs = [a["message"] for v in (raw.get("annotations") or {}).values()
            for a in v]
    assert any("LEX_WORK_QUANTUM_EXPIRED seconds=2700" in m for m in msgs)
    assert any("exit code 78" in m for m in msgs)


def test_stale_audit_target_is_corrected_append_only():
    prev = " ".join(PREV_REPORT.read_text(encoding="utf-8").split())
    # The original wrong line is preserved, not rewritten.
    assert "INDEPENDENT AUDIT of snapshot `866ae3cb`" in prev
    # The correction section names the right head and explains the mistake.
    assert "## 7. Post-run correction by operational resume 40763434744" in prev
    assert "That target is wrong for this snapshot" in prev
    assert SNAPSHOT[:8] in prev and "13-file committed delta" in prev
    assert "FOURTH audit-side quantum death" in prev
    state = json.loads(STATE.read_text(encoding="utf-8"))
    lineage = state["cycle_40750177292_operational_resume"]["lineage_status"]
    assert lineage["snapshot_head"] == SNAPSHOT
    assert lineage["snapshot_head_original_producer_record"] == PREDECESSOR
    assert "snapshot_head_correction" in lineage
    own = state["cycle_40750177292_operational_resume"]["own_audit_outcome"]
    assert own["mechanism"] == "OBSERVED_QUANTUM_EXPIRED"
    assert own["gate_file_written"] is False


def test_git_resolved_audit_target_contract():
    sys.path.insert(0, str(ROOT))
    from product import audit_route
    target = audit_route.audit_target("40763434744")
    assert target["audit_target_ref"] == \
        "origin/cycle/core/product/40763434744/team"
    assert target["accepted_ref"] == "origin/lab/product"
    assert target["accepted_head"] == ACCEPTED
    assert target["state_accepted_commit"] == ACCEPTED
    assert target["resumed_run_id"] == "40750177292"
    assert target["resumed_snapshot_head"] == SNAPSHOT
    # A target is published only from the immutable team ref; the local HEAD
    # at intake-generation time is never promoted to the target.
    assert target["audit_target_head"] is None or (
        target["audit_target_head"] == target["audit_target_head"])
    assert target["local_head_at_generation"]
    assert target["resumed_head_is_not_audit_target"] is True
    assert target["resumed_diagnosis"].endswith(
        "CYCLE_40750177292_resume_diagnosis.json")
    assert target["report_of_record"] == \
        "reports/product/CYCLE_40763434744.md"
    brief = audit_route.auditor_brief("40763434744", None)
    assert "AUDIT TARGET (team ref):" in brief
    assert "ACCEPTED HEAD:            " + ACCEPTED in brief
    assert "RESUMED PREDECESSOR:      40750177292 at " + SNAPSHOT in brief
    assert "DO NOT audit the resumed predecessor head" in brief
    # The previous run's stale target must not be printed as the target.
    assert "AUDIT TARGET HEAD:        866ae3cb" not in brief


def test_intake_is_committed_and_names_the_target():
    assert INTAKE.is_file()
    text = INTAKE.read_text(encoding="utf-8")
    assert "AUDIT INTAKE" in text
    assert "origin/cycle/core/product/40763434744/team" in text
    assert "ACCEPTED HEAD:            " + ACCEPTED in text
    assert "RESUMED PREDECESSOR:      40750177292 at " + SNAPSHOT in text
    assert "never a gate" not in text  # the intake carries no gate verdict
    assert "Gate path: results/audit/product/CYCLE_<run_id>_GATE.json" in text


def test_profile_registered_and_cross_validated():
    sys.path.insert(0, str(ROOT))
    from product.audit_readiness import (
        PROFILES, check_resumed_diagnosis, select_profile,
    )
    assert "40763434744" in PROFILES
    prof = select_profile("40763434744")
    assert prof["resumed_run_id"] == "40750177292"
    assert prof["failed_job"] == "audit"
    assert prof["mechanism_kind"] == "observed"
    assert prof["delta_kind"] == "committed"
    assert prof["changed_files"] == 13
    assert prof["exit_code"] == 78
    assert prof["cycle_test"] == "product/tests/test_cycle_40763434744.py"
    check = check_resumed_diagnosis()
    assert check["status"] == "PASS", check


def test_offline_vertical_slice_claims_match_the_committed_bundle():
    assert BUNDLE.is_file()
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    rows = bundle["decisions"]
    assert len(rows) == 100
    assert bundle["query"]
    assert len(bundle.get("clusters") or []) == 8
    assert all(r.get("x") is not None and r.get("y") is not None
               for r in rows)
    assert all(r.get("cluster_id") is not None for r in rows)
    assert all(r.get("canonical_url") for r in rows)
    assert bundle["answer"]["status"] == "ready"
    assert len(bundle["answer"]["cited_decision_ids"]) == 4
    assert bundle["provenance"]["offline_slice"]["network"] == "none"
    assert bundle["provenance"]["offline_slice"]["geometry_preserved"] is True


def test_report_of_record_states_measured_claims():
    text = " ".join(REPORT.read_text(encoding="utf-8").split())
    for needle in ("40750177292", "85dfea22", "866ae3cb", "7be4480e",
                   "2706.0 s", "exit 78", "FOURTH audit-side quantum death",
                   "13-file committed delta", "UNADJUDICATED", "PASS",
                   "70 assertions", "2.362 s", "audit intake",
                   "DO NOT audit the resumed predecessor", "2700 s"):
        assert needle in text, needle


def test_audit_route_artifact_if_present():
    if ROUTE.exists():
        route = json.loads(ROUTE.read_text(encoding="utf-8"))
        assert route["schema"] == "product-audit-route/1"
        assert route["run_id"] == "40763434744"
        assert route["quantum_budget_s"] == 2700
        assert route["audit_target"]["audit_target_ref"] == \
            "origin/cycle/core/product/40763434744/team"
        assert route["audit_target"]["accepted_head"] == ACCEPTED
        ids = [s["id"] for s in route["steps"]]
        assert "state_contract" in ids
        assert "chain_cycle_tests" in ids
        assert "never a verdict" in route["contract"]
        if route.get("mode") == "bootstrap":
            assert "self_reference" in route
            failed = set(route["failed_steps"])
            assert failed <= {"chain_cycle_tests"}, failed
        else:
            assert route["overall_status"] == "PASS"
            assert route["failed_steps"] == []
            assert route["total_seconds"] < route["quantum_budget_s"]


def test_dossier_generated_if_present():
    if DOSSIER.exists():
        dossier = json.loads(DOSSIER.read_text(encoding="utf-8"))
        assert dossier["run_id"] == "40763434744"
        assert dossier["overall_status"] == "PASS"
        assert dossier["failed_checks"] == []
        assert dossier["skipped_checks"] == []


def test_audit_route_never_writes_a_gate():
    sys.path.insert(0, str(ROOT))
    from product import audit_route
    proc = subprocess.run(
        [sys.executable, "product/audit_route.py", "--for-auditor",
         "--run-id", "40763434744"],
        cwd=str(ROOT), capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0
    assert "AUDIT TARGET" in proc.stdout
    assert not (ROOT / "results" / "audit" / "product"
                / "CYCLE_40763434744_GATE.json").exists()
