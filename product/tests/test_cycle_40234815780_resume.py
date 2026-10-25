"""Operational resume of run 40234815780 - machine-enforced claims.

Run 40234815780 was the repair round for REVISE-gated cycle 40230559317. The
repair itself committed, but the lane-cycle (producer) agent hit the workflow's
2700 s work quantum before the state-validation and write-scope steps could run,
so no audit ref and no gate exist and the run is UNADJUDICATED.

This module re-derives the resume claims from committed bytes:

1. **Orchestration** - the quantum expiry is observed in public check-run
   annotations, the failed job is ``team``, and the gate step never ran.
2. **Durable delta** - the repair commit is a real 8-file delta over its
   predecessor, not a zero-delta snapshot.
3. **Inherited repair** - both audit ``required_fixes`` remain applied and the
   repaired group measures 81 passed / 0 failed.
4. **Audit readiness** - the dossier profile is pinned to this run, validates
   the live accepted pointer instead of a stale literal, and refuses to fall
   back to another run's claims.
5. **No adjudication** - this producer wrote no gate and no auditor path, and
   the accepted pointer still satisfies both halves of requirement 4.

Nothing here writes a gate, scores a frozen bar, or labels the run accepted or
rejected.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import product.audit_readiness as ar  # noqa: E402
from product.state_contract import accepted_pointer_evidence  # noqa: E402
from product.test_accounting import parse_pytest_summary  # noqa: E402

RUN = "40234815780"
PREDECESSOR = "40230559317"
REPAIR_COMMIT = "b55f7e15e7eb714810b90ffb0874edfba7213cf5"
REPAIR_BASE = "a5658be264d6cf887f514e3cd9cf6980554d5eae"
STATE = ROOT / "state" / "product.json"
RAW = ROOT / "results" / "product" / "orchestration" / f"CYCLE_{RUN}_run_jobs_raw.json"
DIAG = ROOT / "results" / "product" / "orchestration" / f"CYCLE_{RUN}_resume_diagnosis.json"
REPAIR_DIR = ROOT / "results" / "product" / "repair_40234815780"
REPAIRED_LOG = REPAIR_DIR / "pytest_group1_repaired_40234815780.log"
COUNTS = REPAIR_DIR / "test_counts_40234815780.json"
REPORT = ROOT / "reports" / "product" / f"CYCLE_{RUN}.md"
DOSSIER = (ROOT / "results" / "product" / "audit_readiness"
           / f"CYCLE_{RUN}_audit_readiness.json")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _profile() -> dict:
    prof = ar.select_profile(RUN)
    ar.PROFILE = prof
    return prof


def test_resume_diagnosis_is_observed_and_unadjudicated():
    diag = _load(DIAG)
    orch = diag["orchestration"]
    assert diag["run_id"] == RUN
    assert diag["predecessor_run_id"] == PREDECESSOR
    assert orch["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert orch["team"]["failed_step"] == "Run lane cycle"
    assert orch["team"]["producer_state_validation_step_conclusion"] == "skipped"
    assert orch["team"]["write_scope_step_conclusion"] == "skipped"
    assert orch["team"]["team_snapshot_step_conclusion"] == "success"
    assert orch["audit"]["gate_file_written"] is False
    mechanism = orch["mechanism"]
    assert mechanism["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert mechanism["quantum_expired"] is True
    assert mechanism["quantum_seconds"] == 2700
    assert mechanism["exit_code"] == 78
    assert mechanism["annotations_available"] is True
    assert orch["observed_failure"]["job"] == "team"
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["accepted"] is False
    assert diag["adjudication"]["audit"]["gate_file_present"] is False


def test_durable_delta_is_the_committed_repair_not_a_zero_delta_snapshot():
    delta = _load(DIAG)["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["snapshot_head"] == REPAIR_COMMIT
    assert delta["predecessor_head"] == REPAIR_BASE
    assert delta["changed_files"] == 8
    sample = delta["changed_paths_sample"]
    assert len(sample) == 8
    assert any("test_counter_content_rejection_v68.py" in p for p in sample)
    assert any("results/product/repair_40234815780/" in p for p in sample)


def test_inherited_repair_remains_green_and_the_counts_artifact_agrees():
    measured = parse_pytest_summary(REPAIRED_LOG.read_text(encoding="utf-8"))
    assert measured["failed"] == 0
    assert measured["passed"] == 81
    assert measured["total_collected"] == 81
    counts = _load(COUNTS)
    assert counts["repaired"]["passed"] == measured["passed"]
    assert counts["repaired"]["failed"] == measured["failed"]
    assert counts["as_submitted"]["failed"] == 1
    assert counts["as_submitted"]["passed"] == 80


def test_audit_readiness_profile_is_pinned_and_refuses_a_wrong_run():
    prof = _profile()
    assert prof["resumed_run_id"] == RUN
    assert prof["predecessor_run_id"] == PREDECESSOR
    assert prof["failed_job"] == "team"
    assert prof["changed_files"] == 8
    assert prof["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert prof["content_family_expected"]["n_bundles"] == 43
    assert prof["content_family_expected"]["n_decisions"] == 4300
    assert prof["content_family_expected"]["n_verified_defective"] == 0
    with pytest.raises(SystemExit):
        ar.select_profile("99999999999")


def test_audit_readiness_checks_pass_without_re_deriving_frozen_claims():
    _profile()
    for check in (ar.check_state_contract(), ar.check_posture(),
                  ar.check_resumed_diagnosis(), ar.check_claim_artifacts()):
        assert check["status"] == "PASS", check
    posture = ar.check_posture()
    pointer = posture["detail"]["accepted_pointer"]
    assert pointer["gate_ok"] is True
    assert pointer["accept_commit_present"] is True


def test_state_records_the_resume_and_the_pointer_has_both_halves():
    st = _load(STATE)
    assert st["direction_version"] == 68
    block = st["cycle_40234815780_operational_resume"]
    assert block["run_id"] == RUN
    assert block["predecessor_run_id"] == PREDECESSOR
    assert block["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert block["mechanism"] == "OBSERVED_QUANTUM_EXPIRED"
    assert block["failed_job"] == "team"
    assert block["durable_delta"]["changed_files"] == 8
    assert block["adjudication"]["status"] == "UNADJUDICATED"
    assert block["accepted_this_cycle"] is False
    assert block["gate_minted"] is False
    assert block["audit_namespace_written"] is False
    pointer = accepted_pointer_evidence(st, ROOT)
    assert not pointer["problems"], pointer
    assert st["human_gate_ready"] is False
    assert st["machine_gate_ready"] is False
    assert st["continue_recommended"] is True


def test_this_producer_wrote_no_gate_and_no_auditor_namespace_for_this_run():
    for path in (ROOT / "results" / "audit" / "product" / f"CYCLE_{RUN}_GATE.json",
                 ROOT / "reports" / "audit" / "product" / f"CYCLE_{RUN}.md"):
        assert not path.exists(), f"producer wrote auditor namespace: {path}"
    namespace = ar.check_audit_namespace(RUN)
    assert namespace["status"] == "PASS", namespace


def test_report_and_dossier_publish_the_resume_without_acceptance():
    text = REPORT.read_text(encoding="utf-8")
    for needle in (RUN, PREDECESSOR, "OBSERVED_QUANTUM_EXPIRED",
                   "UNADJUDICATED", "b55f7e15", "81 passed", "43 bundles"):
        assert needle in text, f"resume report missing {needle!r}"
    dossier = _load(DOSSIER)
    assert dossier["schema"] == "product-audit-readiness/1"
    assert dossier["run_id"] == RUN
    assert dossier["resumed_run"]["failed_job"] == "team"
    assert dossier["posture"]["gate_minted"] is False
    assert dossier["failed_checks"] == [], dossier["failed_checks"]
