"""Operational resume of run 39180276526 (resume run 39183749963).

The subject run DELIVERED and was NEVER AUDITED.  Its failure is an
orchestration/validation death (wrapper rc 78 at the 2700 s work quantum,
audit job gated off by `needs.team == success`), never a product, retrieval,
label, geometry or human-gate verdict.  Every assertion below is re-derived
from git, from the committed REST/log captures or from the committed records,
so the diagnosis cannot decay into a story, and every green here is bounded by
that claim ceiling.

POST-FREEZE ADDITION, like evaluation/retrieval_gate/id_hygiene.py: no gate is
added to any frozen verdict file, no accepted verdict is overwritten, and no
frozen benchmark, rubric, threshold, incumbent or success rule is touched.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation import orchestration_resume_probe as probe_mod  # noqa: E402
from evaluation.snapshot_audit import run_snapshot_audit as rsa  # noqa: E402

RUN_ID = "39183749963"
SUBJECT_RUN_ID = "39180276526"
SUBJECT_BRANCH = f"refs/remotes/origin/cycle/core/evaluation/{SUBJECT_RUN_ID}/team"
PRESERVED = "results/evaluation/snapshot_audit/39180276526_PRE_RESUME_READY_FALSE_20of21_PRESERVED.json"
PRESERVED_SHA256 = "65f8af2a01dcc5bd33dfaf3db1be83b97f2e6a6ec9794f061d3a1f8bce5a3f97"
SEED = "9a9df5bbd142e9b2f4c64bda646d49c3f28906be"


def _load(rel: str) -> dict:
    return json.loads((_REPO_ROOT / rel).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# H1 - delivered but unaudited
# --------------------------------------------------------------------------- #


def test_h1_record_states_the_delivered_unaudited_class():
    rec = _load(f"results/evaluation/orchestration/{RUN_ID}.json")
    assert rec["schema"] == probe_mod.SCHEMA
    assert rec["subject_run_id"] == SUBJECT_RUN_ID
    assert rec["derived_class"] == "TEAM_JOB_DELIVERED__AUDIT_GATE_ABSENT"
    assert rec["audit_gate_present"] is False
    assert rec["tip_moved_versus_seed"] is True
    assert rec["n_tracked_files_naming_run_id"] > 0
    assert rec["lineage_seed_commit"] == SEED
    assert rec["selftest"]["all_passed"] is True
    assert "Orchestration only" in rec["claim_ceiling"]


def test_h1_probe_rederives_live_from_git():
    """The committed class must be re-derivable, not asserted."""
    live = probe_mod.probe(SUBJECT_RUN_ID, SUBJECT_BRANCH)
    assert live["derived_class"] == "TEAM_JOB_DELIVERED__AUDIT_GATE_ABSENT"
    assert live["audit_gate_present"] is False
    assert live["tip_moved_versus_seed"] is True
    assert live["lineage_seed_commit"] == SEED


def test_h1_rest_capture_shows_what_skipped_what_failed_what_persisted():
    jobs = {j["name"]: j for j in _load(
        f"results/evaluation/orchestration/{RUN_ID}_rest_job_capture.json")["jobs"]}
    team = jobs["team"]
    assert team["conclusion"] == "failure"
    steps = {s["name"]: s["conclusion"] for s in team["steps"]}
    assert steps["Run lane cycle"] == "failure"
    # the snapshot persisted AFTER the death - that is why there is a resume
    assert steps["Persist team snapshot"] == "success"
    assert steps["Validate active MVP producer state"] == "skipped"
    assert steps["Enforce lane write scope"] == "skipped"
    assert jobs["audit"]["conclusion"] == "skipped"
    assert jobs["audit"]["steps"] == []
    assert jobs["integrate"]["conclusion"] == "skipped"


def test_h1_failure_log_quotes_the_rc78_work_quantum_token():
    text = (_REPO_ROOT / f"results/evaluation/orchestration/"
                         f"{RUN_ID}_step6_failure_log_capture.txt").read_text(
        encoding="utf-8", errors="replace")
    assert "LEX_WORK_QUANTUM_EXPIRED seconds=2700" in text
    assert "Process completed with exit code 78" in text


# --------------------------------------------------------------------------- #
# H2 - the subject readiness record was completed, and its pre-resume state kept
# --------------------------------------------------------------------------- #


def test_h2_preresume_record_preserved_byte_identically():
    path = _REPO_ROOT / PRESERVED
    assert path.is_file(), f"missing preserved pre-resume record: {PRESERVED}"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == PRESERVED_SHA256
    rec = json.loads(path.read_text(encoding="utf-8"))
    assert rec["run_id"] == SUBJECT_RUN_ID
    assert rec["ready_for_independent_audit"] is False
    assert rec["n_passed"] == 20 and rec["n_checks"] == 21
    assert rec["failing_checks"] == ["readiness_claims_match_record"]


def test_h2_subject_record_completed_to_ready_with_post_write_verified():
    rec = _load(f"results/evaluation/snapshot_audit/{SUBJECT_RUN_ID}.json")
    assert rec["run_id"] == SUBJECT_RUN_ID
    assert rec["n_passed"] == rec["n_checks"] == 21
    assert rec["ready_for_independent_audit"] is True
    assert rec["failing_checks"] == []
    assert rec["post_write_self_reference"]["status"] == "VERIFIED"
    assert rec["post_write_state_claim"]["status"] == "VERIFIED"
    assert rec["post_write_report_claim"]["status"] == "VERIFIED"


def test_h2_check18_environment_limit_reproduced_both_ways():
    repro = _load(f"results/evaluation/orchestration/"
                  f"{RUN_ID}_check18_environment_limit_repro.json")
    assert repro["holds"] is True
    assert repro["without_accepted_base_ref_in_scratch_repo"]["status"] == "FAIL"
    assert repro["without_accepted_base_ref_in_scratch_repo"]["environment_limited"] is True
    # with the accepted-base ref the same check re-derives and agrees
    assert repro["with_accepted_base_ref"]["status"] == "PASS"
    live = rsa.check_accepted_base_gate_coverage(_REPO_ROOT)
    assert live["status"] == "PASS", live.get("detail")


# --------------------------------------------------------------------------- #
# H3 - this resume run's own readiness record
# --------------------------------------------------------------------------- #


def test_h3_resume_record_is_ready_and_self_consistent():
    rec = _load(f"results/evaluation/snapshot_audit/{RUN_ID}.json")
    assert rec["run_id"] == RUN_ID
    assert rec["n_passed"] == rec["n_checks"] == 21
    assert rec["ready_for_independent_audit"] is True
    assert rec["failing_checks"] == []
    assert rec["post_write_self_reference"]["status"] == "VERIFIED"
    assert rec["post_write_state_claim"]["status"] == "VERIFIED"
    assert rec["post_write_report_claim"]["status"] == "VERIFIED"


def test_h3_state_block_repeats_the_resume_record_counts():
    state = _load("state/evaluation.json")
    block = state[f"snapshot_audit_{RUN_ID}"]
    rec = _load(f"results/evaluation/snapshot_audit/{RUN_ID}.json")
    assert block["verdict"] == "READY"
    assert block["n_passed"] == rec["n_passed"] == 21
    assert block["n_checks"] == rec["n_checks"] == 21
    assert block["ready_for_independent_audit"] is True
    assert block["record"] == f"results/evaluation/snapshot_audit/{RUN_ID}.json"
    assert state["direction_version"] == 57
    assert state["cycle_status"] != "INITIALIZED"


def test_h3_trigger_was_executed_not_asserted():
    rec = _load(f"results/evaluation/trigger_reconciliation/{RUN_ID}/"
                f"{RUN_ID}_reconciliation.json")
    assert rec["schema"] == "lex-evaluation-trigger-reconciliation/1"
    assert rec["trigger"]["verdict"] == "ADJUDICATE_REQUIRED"
    state = _load("state/evaluation.json")
    block = state[f"trigger_reconciliation_{RUN_ID}"]
    assert block["record"].endswith(f"{RUN_ID}_reconciliation.json")
    assert block["trigger_verdict"] == rec["trigger"]["verdict"]


def test_h3_frozen_hypothesis_pinned_the_frozen_inputs():
    hyp = _load("evaluation/V57_OPERATIONAL_RESUME_HYPOTHESIS_V2.json")
    assert hyp["schema"] == "lex-evaluation-frozen-hypothesis/1"
    assert hyp["run_id"] == RUN_ID
    assert hyp["direction_version"] == 57
    for rel, pinned in hyp["frozen_inputs_rehashed_not_rewritten"].items():
        assert hashlib.sha256((_REPO_ROOT / rel).read_bytes()).hexdigest() == pinned, rel


def test_h3_report_declares_the_post_write_statuses_it_records():
    text = (_REPO_ROOT / f"reports/evaluation/CYCLE_{RUN_ID}.md").read_text(
        encoding="utf-8", errors="replace")
    declared = rsa._report_declared_post_write(text)
    rec = _load(f"results/evaluation/snapshot_audit/{RUN_ID}.json")
    assert declared["post_write_self_reference"] == rec["post_write_self_reference"]["status"]
    assert declared["post_write_state_claim"] == rec["post_write_state_claim"]["status"]
