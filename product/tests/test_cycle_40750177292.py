#!/usr/bin/env python3
"""Pins the operational resume of run 40747546909 (rc-67 zero-delta misroute).

Run 40737328834's TEAM job was fully green (7-file committed delta
866ae3cb over df6c81fb) and its AUDIT "Independent audit" step then died
at the 2700 s work quantum (exit 78, 2707.0 s — the THIRD audit-side
quantum death on this lineage).  The workflow then re-dispatched a
PRODUCER repair round as run 40747546909; the producer correctly found
nothing to add to the already audit-ready snapshot, so the rc-67
LEX_ZERO_DELTA_REPAIR guard fired (requirement 10: "the producer found
nothing to do" — NOT a product defect) and the team ref was published
byte-identical to 866ae3cb.

This module pins: both machine diagnoses; the instrument upgrade that
classifies the rc-67 sentinel as OBSERVED (was UNOBSERVED); the PROFILES
entries; the state truth-repair of 40737328834's producer-recorded status
(original preserved); the bounded audit-route instrument and its
committed artifact; the fail-closed posture; and the two-half accepted
pointer.
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
REPORT = ROOT / "reports" / "product" / "CYCLE_40750177292.md"
DOSSIER = AR / "CYCLE_40750177292_audit_readiness.json"
ROUTE = AR / "CYCLE_40750177292_AUDIT_ROUTE.json"
ACCEPTED = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
SNAPSHOT = "866ae3cb125b619c07b3dbb63c44b674d314848e"
PREDECESSOR = "df6c81fb0cf7829cb0b5a19bee121f907685b228"


def test_state_pointer_and_posture_non_rotting():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    assert state["accepted_run_id"] == "CYCLE_40284658455"
    assert state["accepted_commit"] == ACCEPTED
    # current_run is the MOVING latest-resume pointer. The original pin
    #     assert state["current_run"] == "40750177292"
    # was correct when recorded but rots on every later resume; this is the
    # chain's standard non-rotting maintenance repair (same form used since
    # CYCLE_40718103891 in test_cycle_40682733879.py). This cycle's own
    # durable record is NOT current_run; it is the cycle block asserted below.
    assert state["current_run"]  # truthy, non-empty
    assert "cycle_40750177292_operational_resume" in state
    assert "cycle_40747546909_operational_resume" in state
    assert state["continue_recommended"] is True
    assert state["human_gate_ready"] is False
    assert state["machine_gate_ready"] is False
    assert state["ready_for_owner_session"] is False
    assert state["packet_admitted"] is False
    assert state["owner_decision_required"] is False
    assert state["direction_version"] == 68
    block = state["cycle_40750177292_operational_resume"]
    assert block["resumed_run_id"] == "40747546909"
    assert block["resumed_death"]["classification"] == \
        "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert "OBSERVED_ZERO_DELTA_REPAIR_GUARD_EXIT_67" in \
        block["resumed_death"]["mechanism"]
    assert block["posture"]["continue_recommended"] is True
    assert block["posture"]["human_gate_ready"] is False
    # The bounded audit route is pinned in state so any auditor reading
    # state sees it without exploring the tree.
    route_field = state["audit_route"]
    assert route_field["instrument"] == "product/audit_route.py"
    assert route_field["quantum_budget_s"] == 2700
    assert any("audit_route.py" in c for c in route_field["commands"])
    assert state["capabilities"]["bounded_audit_route"].startswith(
        "product/audit_route.py")


def test_run_history_fates():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    hist = {str(e["run_id"]): e for e in state["run_history"]}
    # The producer-recorded status of 40737328834 predates its own audit
    # death; this cycle corrected it and preserved the original inline.
    entry = hist["40737328834"]
    assert entry["status"] == \
        "AUDIT_JOB_QUANTUM_DEATH_COMMITTED_DELTA_UNADJUDICATED"
    assert entry["status_original_producer_record"] == \
        "OPERATIONAL_RESUME_VERIFY_AND_AUDIT_READINESS"
    assert entry["team_job"].startswith("SUCCESS")
    assert "OBSERVED_QUANTUM_EXPIRED" in entry["audit_job"]
    assert hist["40737328834"]["resumed_run"] == 40726216925
    assert hist["40737328834"]["accepted"] is False
    # The rc-67 misroute run is first-class in the chain record.
    rc67 = hist["40747546909"]
    assert rc67["status"] == \
        "ZERO_DURABLE_DELTA_RC67_GUARD_PRODUCER_REREDISPATCH_MISROUTE_UNADJUDICATED"
    assert rc67["resumed_run"] == 40737328834
    assert rc67["accepted"] is False
    assert "LEX_ZERO_DELTA_REPAIR" in rc67["summary"]
    assert "requirement 10" in rc67["summary"]
    cur = hist["40750177292"]
    # The producer-recorded status below was written before this run's own
    # audit job died; operational resume 40763434744 truth-corrected it from
    # the committed public raw and preserved the original inline. A historical
    # test may not keep asserting the pre-death claim.
    #     assert cur["status"] == \
    #         "OPERATIONAL_RESUME_CHAIN_DIAGNOSIS_AND_BOUNDED_AUDIT_ROUTE"
    assert cur["status"] == \
        "AUDIT_JOB_QUANTUM_DEATH_COMMITTED_DELTA_UNADJUDICATED"
    assert cur["status_original_producer_record"] == \
        "OPERATIONAL_RESUME_CHAIN_DIAGNOSIS_AND_BOUNDED_AUDIT_ROUTE"
    assert cur["resumed_run"] == 40747546909
    assert cur["accepted"] is False
    assert cur["report_of_record"] == "reports/product/CYCLE_40750177292.md"


def test_diagnosed_audit_quantum_death_of_40737328834():
    diag = json.loads((ORCH / "CYCLE_40737328834_resume_diagnosis.json")
                      .read_text(encoding="utf-8"))
    assert diag["run_id"] == "40737328834"
    assert diag["predecessor_run_id"] == "40726216925"
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
    assert orch["audit"]["independent_audit_step_seconds"] == 2707.0
    assert orch["audit"]["gate_file_written"] is False
    delta = diag["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["changed_files"] == 7
    assert delta["snapshot_head"] == SNAPSHOT
    assert delta["predecessor_head"] == PREDECESSOR
    assert diag["adjudication"]["status"] == "UNADJUDICATED"


def test_diagnosed_rc67_zero_delta_misroute_of_40747546909():
    diag = json.loads((ORCH / "CYCLE_40747546909_resume_diagnosis.json")
                      .read_text(encoding="utf-8"))
    assert diag["run_id"] == "40747546909"
    assert diag["predecessor_run_id"] == "40737328834"
    orch = diag["orchestration"]
    assert orch["classification"] == \
        "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    mech = orch["mechanism"]
    assert mech["status"] == "OBSERVED_ZERO_DELTA_REPAIR_GUARD_EXIT_67"
    assert mech["quantum_expired"] is False
    assert mech["exit_code"] == 67
    assert "requirement 10" in mech["claim"]
    assert orch["team"]["conclusion"] == "failure"
    assert orch["team"]["failed_step"] == "Run lane cycle"
    assert orch["team"]["team_snapshot_persisted_after_failed_team_job"] \
        is True
    assert orch["audit"]["conclusion"] == "skipped"
    assert orch["audit"]["gate_file_written"] is False
    delta = diag["durable_delta"]
    assert delta["classification"] == "ZERO_DURABLE_DELTA"
    assert delta["changed_files"] == 0
    assert delta["snapshot_head"] == delta["predecessor_head"] == SNAPSHOT
    assert diag["adjudication"]["status"] == "UNADJUDICATED"


def test_raw_snapshots():
    raw74 = json.loads((ORCH / "CYCLE_40747546909_run_jobs_raw.json")
                       .read_text(encoding="utf-8"))
    assert raw74["run"]["id"] == 40747546909
    team = next(j for j in raw74["jobs"] if j["name"] == "team")
    assert team["conclusion"] == "failure"
    msgs = [a["message"] for v in (raw74.get("annotations") or {}).values()
            for a in v]
    assert any("LEX_ZERO_DELTA_REPAIR" in m for m in msgs)
    assert any("exit code 67" in m for m in msgs)
    raw84 = json.loads((ORCH / "CYCLE_40737328834_run_jobs_raw.json")
                       .read_text(encoding="utf-8"))
    assert raw84["run"]["id"] == 40737328834
    audit = next(j for j in raw84["jobs"] if j["name"] == "audit")
    assert audit["conclusion"] == "failure"
    msgs84 = [a["message"] for v in (raw84.get("annotations") or {}).values()
              for a in v]
    assert any("LEX_WORK_QUANTUM_EXPIRED seconds=2700" in m for m in msgs84)
    assert any("exit code 78" in m for m in msgs84)


def test_rc67_instrument_upgrade_classifies_observed():
    sys.path.insert(0, str(ROOT))
    from product.audit_step_diagnosis import classify
    raw = json.loads((ORCH / "CYCLE_40747546909_run_jobs_raw.json")
                     .read_text(encoding="utf-8"))
    out = classify(raw)
    assert out["mechanism"]["status"] == \
        "OBSERVED_ZERO_DELTA_REPAIR_GUARD_EXIT_67"
    assert out["mechanism"]["exit_code"] == 67


def test_profiles_registered_and_cross_validated():
    sys.path.insert(0, str(ROOT))
    from product.audit_readiness import (
        PROFILES, check_resumed_diagnosis, select_profile,
    )
    assert "40747546909" in PROFILES
    assert "40750177292" in PROFILES
    prof = select_profile("40750177292")
    assert prof["resumed_run_id"] == "40747546909"
    assert prof["failed_job"] == "team"
    assert prof["mechanism_kind"] == "observed_zero_delta_guard"
    assert prof["delta_kind"] == "zero"
    assert prof["exit_code"] == 67
    assert prof["cycle_test"] == "product/tests/test_cycle_40750177292.py"
    # The new mechanism kind must cross-validate against the committed
    # raw + diagnosis artifacts, not just parse.
    check = check_resumed_diagnosis()
    assert check["status"] == "PASS", check
    # The prior cycle's own profile is preserved in role.
    old = select_profile("40737328834")
    assert old["resumed_run_id"] == "40726216925"
    assert old["failed_job"] == "audit"


def test_audit_route_instrument_contract():
    sys.path.insert(0, str(ROOT))
    from product import audit_route
    assert audit_route.QUANTUM_BUDGET_S == 2700
    tests = audit_route.chain_cycle_tests("40750177292")
    assert "product/tests/test_cycle_40750177292.py" in tests
    assert len(tests) >= 2
    brief = audit_route.auditor_brief("40750177292", None)
    assert "INDEPENDENT AUDIT" in brief
    assert "audit_route.py" in brief
    assert "UPPERCASE" in brief
    # --for-auditor prints the brief and writes nothing.
    proc = subprocess.run(
        [sys.executable, "product/audit_route.py", "--for-auditor",
         "--run-id", "40750177292"],
        cwd=str(ROOT), capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0
    assert "INDEPENDENT AUDIT" in proc.stdout


def test_audit_route_artifact_if_present():
    if ROUTE.exists():
        route = json.loads(ROUTE.read_text(encoding="utf-8"))
        assert route["schema"] == "product-audit-route/1"
        assert route["run_id"] == "40750177292"
        assert route["quantum_budget_s"] == 2700
        ids = [s["id"] for s in route["steps"]]
        assert "state_contract" in ids
        assert "chain_cycle_tests" in ids
        # The route is a readiness instrument, never a verdict.
        assert "never a verdict" in route["contract"]
        if route.get("mode") == "bootstrap":
            # First-generation artifact (fixpoint break): structure + every
            # non-self-referential step must be green; the immediately
            # following non-bootstrap run verifies it through the excluded
            # test and writes the strict-PASS record.
            assert "self_reference" in route
            failed = set(route["failed_steps"])
            assert failed <= {"chain_cycle_tests"}, failed
            for s in route["steps"]:
                if s["id"] == "chain_cycle_tests":
                    continue
                assert s["status"] in ("PASS", "SKIP"), (s["id"], s["status"])
        else:
            assert route["overall_status"] == "PASS"
            assert route["failed_steps"] == []
            assert route["total_seconds"] < route["quantum_budget_s"]


def test_report_exists_and_states_the_fates():
    assert REPORT.is_file()
    text = REPORT.read_text(encoding="utf-8")
    for needle in ("40737328834", "40747546909", "40750177292",
                   "OBSERVED_QUANTUM_EXPIRED",
                   "OBSERVED_ZERO_DELTA_REPAIR_GUARD_EXIT_67",
                   "LEX_ZERO_DELTA_REPAIR", "866ae3cb", "df6c81fb",
                   "7be4480e", "UNADJUDICATED", "audit_route",
                   "2700", "INDEPENDENT AUDIT"):
        assert needle in text, needle


def test_dossier_generated_if_present():
    if DOSSIER.exists():
        dossier = json.loads(DOSSIER.read_text(encoding="utf-8"))
        assert dossier["run_id"] == "40750177292"
        assert dossier["overall_status"] == "PASS"
        assert dossier["failed_checks"] == []
