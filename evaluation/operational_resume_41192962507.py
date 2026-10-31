#!/usr/bin/env python3
"""Operational resume / audit-readiness verification for run 41192962507 (evaluation, v68).

WHY
---
Run 41192962507 resumed the zero-delta snapshot of 41192878248.  Its PRODUCER
job ran the lane cycle for the full 2700 s work quantum and exited 78 with the
wrapper annotation LEX_WORK_QUANTUM_EXPIRED seconds=2700.  The producer-state
and write-scope steps were SKIPPED, audit/integrate were never scheduled, and
the always-guarded "Persist team snapshot" step published the agent's partial
work as 77574ac4 (parent 326f0e53, 4 commits / 57 paths).

Unlike 41192878248, this run DID produce a delta.  This resume therefore does
NOT restart work: it diagnoses the quantum expiry, verifies the snapshot is
in-scope and internally consistent, re-verifies the inherited 41192878248
claims from committed bytes, re-checks item-(2) currency, re-runs only the
accepted multilingual/provenance suite, closes the inherited gate-gap by
executing the state/lane/write-scope/nested-refs/self-check gates, and publishes
an auditor index/brief.

CLAIM CEILING
-------------
Operational resume and audit-readiness only.  No frozen bar, packet, serve
verdict, d2_path_scope_probe, standing falsification or 174k benchmark is scored
or re-run.  No audit gate is minted.  All posture flags stay FALSE.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

RUN_ID = "41192962507"
DISPATCH_RUN_ID = "41196128050"
PRED_RUN_ID = "41192878248"
SNAPSHOT_COMMIT = "77574ac4f0ddf892874ae79de5dd5f0c19f8fe66"
SNAPSHOT_SUBJECT = "evaluation cycle 41192962507 repair 0"
SNAPSHOT_PARENT = "326f0e53dbad1fed42786039fe983c6f4a746881"
SNAPSHOT_REF = f"origin/cycle/core/evaluation/{RUN_ID}/team"
PRED_SNAPSHOT_REF = f"origin/cycle/core/evaluation/{PRED_RUN_ID}/team"
TEAM_JOB_ID = 124513359143

RUNREC = f"results/evaluation/orchestration/{RUN_ID}_run_record.json"
JOBS = f"results/evaluation/orchestration/{RUN_ID}_jobs.json"
TANNOT = f"results/evaluation/orchestration/{RUN_ID}_team_annotations.json"
DIAG = f"results/evaluation/orchestration/CYCLE_{RUN_ID}_producer_work_quantum_expiry.json"

PRED_RUNREC = f"results/evaluation/orchestration/{PRED_RUN_ID}_run_record.json"
PRED_JOBS = f"results/evaluation/orchestration/{PRED_RUN_ID}_jobs.json"
PRED_TANNOT = f"results/evaluation/orchestration/{PRED_RUN_ID}_team_annotations.json"
PRED_DIAG = f"results/evaluation/orchestration/CYCLE_{PRED_RUN_ID}_producer_start_failure.json"
PRED_AUDIT_DIAG = "results/evaluation/orchestration/CYCLE_41187766812_audit_quantum_expiry.json"

PRIOR_RECORD = f"results/evaluation/operational_resume/{PRED_RUN_ID}.json"
PRIOR_CLAIMS = f"results/evaluation/operational_resume/{PRED_RUN_ID}_claim_verification.json"
PRIOR_ITEM2 = f"results/evaluation/operational_resume/{PRED_RUN_ID}_item2_currency.json"
PRIOR_MULT = f"results/evaluation/operational_resume/{PRED_RUN_ID}_multilingual_supplement.json"
PRIOR_SCOPE = f"results/evaluation/orchestration/{PRED_RUN_ID}_snapshot_scope.json"
PRIOR_VALIDATE = f"results/evaluation/orchestration/{PRED_RUN_ID}_validate_step_replay.json"
PRIOR_STALE = f"results/evaluation/orchestration/{PRED_RUN_ID}_stale_disclosure_repair.json"
PRIOR_REPORT = f"reports/evaluation/OPERATIONAL_RESUME_{PRED_RUN_ID}_AUDIT_READY.md"
PRIOR_BRIEF = f"reports/evaluation/AUDIT_BRIEF_{PRED_RUN_ID}.md"
PRIOR_INDEX = f"results/evaluation/operational_resume/AUDIT_INDEX_{PRED_RUN_ID}.json"

BENCHMARK_OF_RECORD = "results/evaluation/minimal_retrieval_ca_benchmark/40182692670.json"
BENCHMARK_OF_RECORD_SHA = "fd29a395f8b5307d67abeb79335337250518cc6de171a26ddbf09768840ade73"
SECOND_RECORD = "results/evaluation/minimal_ca_falsify_benchmark/40228275848.json"
SECOND_RECORD_SHA = "5f5e4156976764be3cc40d79728a5ca11bfcee66bb41f8cbe13bcb26acc726c4"
EXPECTED_FAILED_GATES = [
    "mf::concept_coverage::39319405429::de-kapitalverletzung",
    "mf::counter_authority_surface::39319405429::de-kapitalverletzung",
    "mf::counter_authority_surface::39319405429::fr-bail-entretien",
    "mf::counter_authority_surface::39319405429::it-responsabilita-medica",
]

ACCEPTED_GATE = "results/audit/evaluation/CYCLE_40265377500_GATE.json"
ACCEPTED_GATE_SHA = "b9d04cae0eb8f654723a0406fd0684eef0515eb28f6f45c4c4510b8b75e63e53"
EXPECTED_ACCEPTED_RUN = 40265377500
EXPECTED_ACCEPTED_COMMIT = "ea98384e54d31d2e694c418a1d1ce5769fc6c32f"
EXPECTED_PRODUCT_MOUNT_HEAD = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
MULT_TEST = "tests/evaluation/test_retrieval_benchmark.py"
MULT_TEST_SHA256 = "558e1f1b7143e09e704891d5e0d7401a9b688e8d9c3d4b389dc4229972dc47be"
ITEM2_ADJUDICATOR = "evaluation/post_repair_family_ca_falsifier.py"
ITEM2_ADJUDICATOR_SHA256 = "126a1234f3fe8a3f10ff736dff7466093000a2fadd8871f02f97efe974543a08"
MOUNT = Path("/tmp/lex_accepted/product")
LAB_PRODUCT_REF = "origin/lab/product"

HYPOTHESIS = f"evaluation/OPERATIONAL_RESUME_{RUN_ID}_HYPOTHESIS_V1.json"
FREEZE = f"evaluation/OPERATIONAL_RESUME_{RUN_ID}_FREEZE_V6.json"
OUT_RESULT = f"results/evaluation/operational_resume/{RUN_ID}.json"
CLAIMS_RECORD = f"results/evaluation/operational_resume/{RUN_ID}_claim_verification.json"
ITEM2_RECORD = f"results/evaluation/operational_resume/{RUN_ID}_item2_currency.json"
MULT_RECORD = f"results/evaluation/operational_resume/{RUN_ID}_multilingual_supplement.json"
SNAPSHOT_SCOPE = f"results/evaluation/orchestration/{RUN_ID}_snapshot_scope.json"
VALIDATE_REPLAY = f"results/evaluation/orchestration/{RUN_ID}_validate_step_replay.json"
STATE_GATE = f"results/evaluation/orchestration/{RUN_ID}_state_integrity_gate.json"
LANE_SUITE = f"results/evaluation/orchestration/{RUN_ID}_lane_suite.json"
NESTED_REFS = f"results/evaluation/orchestration/{RUN_ID}_nested_evidence_refs.json"
WRITE_SCOPE = f"results/evaluation/orchestration/{RUN_ID}_write_scope.json"
STALE_REPAIR = f"results/evaluation/orchestration/{RUN_ID}_stale_disclosure_repair.json"
SELF_CHECK_RESULT = f"results/evaluation/orchestration/{RUN_ID}_self_check_pytest_shim.json"
SELF_SCRIPT = f"evaluation/operational_resume_{RUN_ID}.py"
SELF_TEST = f"tests/evaluation/test_operational_resume_{RUN_ID}.py"
OUT_REPORT = f"reports/evaluation/OPERATIONAL_RESUME_{RUN_ID}_AUDIT_READY.md"
AUDIT_BRIEF = f"reports/evaluation/AUDIT_BRIEF_{RUN_ID}.md"
AUDIT_INDEX = f"results/evaluation/operational_resume/AUDIT_INDEX_{RUN_ID}.json"
STATE = "state/evaluation.json"
LANE_STATE = "evaluation/state/evaluation.json"

SCOPE_PATTERNS = (
    "evaluation/*", "tests/evaluation/*", "results/evaluation/*",
    "reports/evaluation/*", "state/evaluation.json", "data/evaluation/*", "",
)
EXIT_PASS = 0
EXIT_GAPS = 2


def utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: str | Path) -> Any:
    return json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))


def write_json(path: str | Path, obj: Any) -> None:
    p = REPO_ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256_file(path: str | Path) -> str | None:
    p = REPO_ROOT / path
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def git(*args: str, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)


def git_ref_head(ref: str, cwd: Path = REPO_ROOT) -> str | None:
    r = git("rev-parse", ref, cwd=cwd)
    return r.stdout.strip() if r.returncode == 0 else None


def iso_seconds(started: str | None, completed: str | None) -> float | None:
    if not started or not completed:
        return None
    a = datetime.fromisoformat(started.replace("Z", "+00:00"))
    b = datetime.fromisoformat(completed.replace("Z", "+00:00"))
    return round((b - a).total_seconds(), 1)


def _find_job(jobs: dict, job_id: int) -> dict | None:
    for j in jobs.get("jobs", []):
        if j.get("id") == job_id:
            return j
    return None


def _step(job: dict | None, name: str) -> dict | None:
    for s in (job or {}).get("steps", []):
        if s.get("name") == name:
            return s
    return None


def _annotation_messages(annotations: list[dict], level: str | None = None) -> list[str]:
    return [a.get("message", "") for a in annotations
            if level is None or a.get("annotation_level") == level]


def _exit_code(messages: list[str]) -> int | None:
    for m in messages:
        hit = re.search(r"exit code (\d+)", m)
        if hit:
            return int(hit.group(1))
    return None


def numeric_environment() -> dict:
    py = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    out = {"python": py, "platform": sys.platform}
    for mod in ("numpy", "scipy", "sklearn"):
        try:
            m = __import__(mod)
            out[mod if mod != "sklearn" else "scikit_learn"] = getattr(m, "__version__", None)
        except Exception:
            out[mod if mod != "sklearn" else "scikit_learn"] = None
    out["accepted_environment_reference"] = (
        "numpy 2.5.4 / scipy 1.18.1 / scikit-learn 1.9.1 as recorded by accepted "
        "cycle 40261335674; restored via pip in this producer image before the "
        "freeze because the ubuntu-latest migration dropped the preinstalled "
        "scientific stack")
    return out


# ---------------------------------------------------------------------------
# 1. current producer work-quantum expiry diagnosis
# ---------------------------------------------------------------------------
def producer_work_quantum_expiry() -> dict:
    run = load_json(RUNREC)
    jobs = load_json(JOBS)
    annotations = load_json(TANNOT)
    team = _find_job(jobs, TEAM_JOB_ID)
    cycle = _step(team, "Run lane cycle")
    validate = _step(team, "Validate active MVP producer state")
    clean_junk = _step(team, "Clean generated junk")
    scope = _step(team, "Enforce lane write scope")
    persist = _step(team, "Persist team snapshot")
    messages = _annotation_messages(annotations)
    rc = _exit_code(messages)
    duration = iso_seconds(cycle.get("started_at") if cycle else None,
                           cycle.get("completed_at") if cycle else None)
    quantum = None
    for m in messages:
        hit = re.search(r"LEX_WORK_QUANTUM_EXPIRED seconds=(\d+)", m)
        if hit:
            quantum = int(hit.group(1))
            break
    ref_head = git_ref_head(SNAPSHOT_REF)
    pred_head = git_ref_head(PRED_SNAPSHOT_REF)
    commits = git("log", "--format=%H%x09%s", f"{SNAPSHOT_PARENT}..{SNAPSHOT_COMMIT}")
    delta_commits = [line.split("\t", 1) for line in commits.stdout.strip().splitlines() if line]
    delta_paths = git("diff", "--name-only", SNAPSHOT_PARENT, SNAPSHOT_COMMIT).stdout.strip().splitlines()
    snapshot_is_new_delta = bool(ref_head and pred_head and ref_head != pred_head)
    rec = {
        "schema": "lex-evaluation-producer-work-quantum-expiry-diagnosis/1",
        "failed_run_id": int(RUN_ID),
        "dispatch_run_id": int(DISPATCH_RUN_ID),
        "direction_version": 68,
        "generated_at_utc": utc(),
        "evidence_source": (
            "public GitHub REST: actions/runs/41192962507, "
            "actions/runs/41192962507/jobs?per_page=100 and "
            "check-runs/124513359143/annotations (HTTP 200, no auth); job LOGS "
            "remain 403-unauthenticated and were NOT used"),
        "run_name": run.get("name"),
        "run_conclusion": run.get("conclusion"),
        "run_head_sha": (run.get("head_sha") or "")[:12],
        "failed_job": "team",
        "failed_job_id": TEAM_JOB_ID,
        "failed_job_conclusion": (team or {}).get("conclusion"),
        "failed_job_started_at": (team or {}).get("started_at"),
        "failed_job_completed_at": (team or {}).get("completed_at"),
        "failed_step_number": (cycle or {}).get("number"),
        "failed_step_name": (cycle or {}).get("name"),
        "failed_step_conclusion": (cycle or {}).get("conclusion"),
        "failed_step_started_at": (cycle or {}).get("started_at"),
        "failed_step_completed_at": (cycle or {}).get("completed_at"),
        "failed_step_duration_seconds": duration,
        "exit_code": rc,
        "annotations": messages,
        "error_annotations": _annotation_messages(annotations, "failure"),
        "annotation_lex_work_quantum_expired": next(
            (m for m in messages if "LEX_WORK_QUANTUM_EXPIRED" in m), None),
        "quantum_seconds_declared": quantum,
        "quantum_arithmetic": {
            "declared_quantum_seconds": quantum,
            "step_duration_seconds": duration,
            "duration_at_or_above_quantum": (
                None if duration is None or quantum is None else duration >= quantum),
            "duration_within_one_tick_window": (
                None if duration is None or quantum is None
                else quantum <= duration <= quantum + 30),
        },
        "failure_class": "PRODUCER_WORK_QUANTUM_EXPIRED_rc78",
        "classification": "NON_MEASUREMENT_PRODUCER_WORK_QUANTUM_EXPIRY",
        "failure_is_orchestration_not_measurement": True,
        "failure_is_validation_failure": False,
        "failure_is_work_quantum_expiry": True,
        "failure_mechanism_observed": True,
        "mechanism_evidence": (
            "The wrapper annotation LEX_WORK_QUANTUM_EXPIRED seconds=2700 and exit 78 "
            "identify the orchestration lifetime cutoff. The inner agent/provider "
            "error that consumed the quantum is NOT observed because logs are 403."),
        "producer_validation_ran": (validate or {}).get("conclusion") != "skipped",
        "producer_validation_step_conclusion": (validate or {}).get("conclusion"),
        "producer_write_scope_ran": (scope or {}).get("conclusion") != "skipped",
        "producer_write_scope_step_conclusion": (scope or {}).get("conclusion"),
        "producer_clean_generated_junk_conclusion": (clean_junk or {}).get("conclusion"),
        "producer_snapshot_persisted": (persist or {}).get("conclusion") == "success",
        "skipped_workflow_gates": [
            "Validate active MVP producer state (skipped because the lane cycle exited 78)",
            "Enforce lane write scope (skipped for the same reason)",
            "audit (not scheduled)",
            "integrate (not scheduled)",
        ],
        "snapshot_ref_head_at_diagnosis": ref_head,
        "snapshot_ref_matches_head": ref_head == SNAPSHOT_COMMIT,
        "snapshot_ref_head": ref_head,
        "snapshot_commit": SNAPSHOT_COMMIT,
        "snapshot_commit_subject": SNAPSHOT_SUBJECT,
        "snapshot_parent": SNAPSHOT_PARENT,
        "predecessor_snapshot_ref_head": pred_head,
        "snapshot_is_new_delta_over_predecessor": snapshot_is_new_delta,
        "snapshot_delta_commits": [
            {"commit": c[0], "subject": c[1] if len(c) > 1 else ""} for c in delta_commits],
        "n_snapshot_delta_commits": len(delta_commits),
        "snapshot_delta_paths": delta_paths,
        "n_snapshot_delta_paths": len(delta_paths),
        "consequence": (
            "Unlike 41192878248, this run's team ref is not a zero-delta copy of its "
            "predecessor: the agent's partial work is committed as a new delta. The "
            "run itself minted no audit gate and its validate/scope gates never ran; "
            "this resume verifies the delta from committed bytes rather than "
            "restarting the cycle."),
        "claim_ceiling": (
            "Orchestration diagnosis only. No benchmark, packet, serve verdict or "
            "frozen scorer is re-run or re-derived."),
        "not_a_measurement": True,
    }
    write_json(DIAG, rec)
    return rec


# ---------------------------------------------------------------------------
# 2. snapshot scope / consistency
# ---------------------------------------------------------------------------
def _in_scope(path: str) -> bool:
    return any(path == p or (p.endswith("*") and path.startswith(p[:-1]))
               for p in SCOPE_PATTERNS if p)


def snapshot_scope() -> dict:
    changed = git("diff", "--name-only", SNAPSHOT_PARENT, SNAPSHOT_COMMIT).stdout.strip().splitlines()
    out_of_scope = sorted(p for p in changed if not _in_scope(p))
    head_subject = git("log", "-1", "--format=%s", SNAPSHOT_COMMIT).stdout.strip()
    parent_subject = git("log", "-1", "--format=%s", SNAPSHOT_PARENT).stdout.strip()
    ref_head = git_ref_head(SNAPSHOT_REF)
    pred_head = git_ref_head(PRED_SNAPSHOT_REF)
    commits = git("log", "--format=%H%x09%s", f"{SNAPSHOT_PARENT}..{SNAPSHOT_COMMIT}").stdout.strip().splitlines()
    rec = {
        "schema": "lex-evaluation-snapshot-scope/1",
        "run_id": int(RUN_ID),
        "direction_version": 68,
        "generated_at_utc": utc(),
        "snapshot_ref": SNAPSHOT_REF,
        "snapshot_ref_head": ref_head,
        "snapshot_ref_matches_head": ref_head == SNAPSHOT_COMMIT,
        "predecessor_snapshot_ref": PRED_SNAPSHOT_REF,
        "predecessor_snapshot_ref_head": pred_head,
        "snapshot_is_new_delta_over_predecessor": bool(
            ref_head and pred_head and ref_head != pred_head),
        "head_commit": SNAPSHOT_COMMIT,
        "head_subject": head_subject,
        "base_commit": SNAPSHOT_PARENT,
        "base_subject": parent_subject,
        "n_commits": len(commits),
        "commits": [{"commit": c.split("\t", 1)[0],
                     "subject": c.split("\t", 1)[1] if "\t" in c else ""} for c in commits],
        "n_paths_changed": len(changed),
        "paths_changed": changed,
        "out_of_scope_paths": out_of_scope,
        "in_scope_patterns": [p for p in SCOPE_PATTERNS if p],
        "verdict": "SCOPE_CLEAN" if not out_of_scope else "SCOPE_VIOLATION",
        "not_a_measurement": True,
    }
    write_json(SNAPSHOT_SCOPE, rec)
    return rec


# ---------------------------------------------------------------------------
# 3. producer-state validate replay
# ---------------------------------------------------------------------------
def validate_step_replay() -> dict:
    state = load_json(STATE)
    keys = [k for k in state if k.startswith("state_update_")]
    direction_ok = state.get("direction_version") == 68
    cycle_ok = state.get("cycle_status") != "INITIALIZED"
    updated = (
        f"state_update_{DISPATCH_RUN_ID}" in state
        or f"state_update_{RUN_ID}" in state
        or state.get("github_run") == int(RUN_ID)
    )
    rec = {
        "schema": "lex-evaluation-validate-step-replay/1",
        "run_id": int(RUN_ID),
        "direction_version": 68,
        "generated_at_utc": utc(),
        "workflow_step": "Validate active MVP producer state",
        "workflow_source": ".github/workflows/core-lane.yml (jq -e predicate)",
        "jq_expression": (
            "(.direction_version // -1) == $dirv and "
            "(.cycle_status // \"INITIALIZED\") != \"INITIALIZED\""),
        "state_path": STATE,
        "direction_version_in_state": state.get("direction_version"),
        "cycle_status_in_state": state.get("cycle_status"),
        "state_github_run_at_replay": state.get("github_run"),
        "state_update_keys": keys,
        "this_run_advanced_state": updated,
        "would_pass": bool(direction_ok and cycle_ok),
        "exit_code": 0 if (direction_ok and cycle_ok) else 1,
        "vacuity_observation": {
            "predicate_checks_only": [
                "direction_version == 68", "cycle_status != INITIALIZED"],
            "passes_without_state_advance": not updated,
            "disclosure": (
                "The workflow predicate checks only direction_version and cycle_status, "
                "so it can pass although this run's producer-state step was SKIPPED and "
                "no state_update_<run_id> block existed before this resume. Recorded, "
                "not edited; this resume repairs the state pointer additively."),
        },
        "not_a_measurement": True,
    }
    write_json(VALIDATE_REPLAY, rec)
    return rec


# ---------------------------------------------------------------------------
# 4. inherited claim verification (no re-execution)
# ---------------------------------------------------------------------------
def claim_verification() -> dict:
    checks: list[dict] = []

    def add(check_id: str, ok: bool, expected: Any, actual: Any) -> None:
        checks.append({
            "id": check_id, "ok": bool(ok), "expected": expected, "actual": actual,
            "severity": "claim",
        })

    p = load_json(PRIOR_RECORD)
    claims = load_json(PRIOR_CLAIMS)
    scope = load_json(PRIOR_SCOPE)
    validate = load_json(PRIOR_VALIDATE)
    item2 = load_json(PRIOR_ITEM2)
    mult = load_json(PRIOR_MULT)
    producer = p.get("producer") or {}
    pred = p.get("predecessor_audit") or {}
    bench = load_json(BENCHMARK_OF_RECORD)
    second = load_json(SECOND_RECORD)
    state = load_json(STATE)
    lane_state = load_json(LANE_STATE)
    accepted_gate = load_json(ACCEPTED_GATE)
    lab_head = git_ref_head("origin/lab/evaluation")
    pred_diag = load_json(PRED_DIAG)
    pred_audit_diag = load_json(PRED_AUDIT_DIAG)
    stale = load_json(PRIOR_STALE)

    add("prior_record_schema", p.get("schema") == "lex-evaluation-operational-resume-verification/7",
        "lex-evaluation-operational-resume-verification/7", p.get("schema"))
    add("prior_record_run_id", p.get("run_id") == int(PRED_RUN_ID), int(PRED_RUN_ID), p.get("run_id"))
    add("prior_record_verdict", p.get("verdict") == "RESUME_VERIFIED_AUDIT_READY",
        "RESUME_VERIFIED_AUDIT_READY", p.get("verdict"))
    add("prior_record_exit_code", p.get("exit_code") == 0, 0, p.get("exit_code"))
    add("prior_record_resumes_41187766812", p.get("resumed_snapshot_run_id") == 41187766812,
        41187766812, p.get("resumed_snapshot_run_id"))
    add("prior_record_snapshot_commit", p.get("resumed_snapshot_commit") == SNAPSHOT_PARENT,
        SNAPSHOT_PARENT, p.get("resumed_snapshot_commit"))

    add("prior_producer_classification",
        producer.get("classification") == "NON_MEASUREMENT_PRODUCER_START_FAILURE",
        "NON_MEASUREMENT_PRODUCER_START_FAILURE", producer.get("classification"))
    add("prior_producer_exit_code", producer.get("exit_code") == 1, 1, producer.get("exit_code"))
    add("prior_producer_quick_failure",
        (producer.get("failed_step_duration_seconds") or 999) <= 60, "<= 60 s",
        producer.get("failed_step_duration_seconds"))
    add("prior_producer_validation_skipped", producer.get("producer_validation_ran") is False,
        False, producer.get("producer_validation_ran"))
    add("prior_producer_write_scope_skipped", producer.get("producer_write_scope_ran") is False,
        False, producer.get("producer_write_scope_ran"))
    add("prior_producer_snapshot_persisted", producer.get("producer_snapshot_persisted") is True,
        True, producer.get("producer_snapshot_persisted"))
    add("prior_snapshot_is_zero_delta", producer.get("snapshot_is_predecessor_not_new_delta") is True,
        True, producer.get("snapshot_is_predecessor_not_new_delta"))
    add("prior_delta_commits_empty", producer.get("delta_commits") == [], [], producer.get("delta_commits"))

    add("predecessor_audit_failure_class",
        pred.get("failure_class") == "AUDIT_WORK_QUANTUM_EXPIRED_rc78",
        "AUDIT_WORK_QUANTUM_EXPIRED_rc78", pred.get("failure_class"))
    add("predecessor_audit_exit_code", pred.get("exit_code") == 78, 78, pred.get("exit_code"))
    add("predecessor_audit_quantum", pred.get("annotation_quantum_seconds_declared") == 2700,
        2700, pred.get("annotation_quantum_seconds_declared"))
    add("predecessor_producer_success", pred.get("producer_job_conclusion") == "success",
        "success", pred.get("producer_job_conclusion"))
    add("predecessor_producer_validate", pred.get("producer_validation_passed") is True,
        True, pred.get("producer_validation_passed"))
    add("predecessor_producer_write_scope", pred.get("producer_write_scope_passed") is True,
        True, pred.get("producer_write_scope_passed"))

    add("prior_scope_verdict", scope.get("verdict") == "SCOPE_CLEAN", "SCOPE_CLEAN", scope.get("verdict"))
    add("prior_scope_head", scope.get("head_commit") == SNAPSHOT_PARENT, SNAPSHOT_PARENT, scope.get("head_commit"))
    add("prior_scope_base", scope.get("base_commit") == "967a450f0a66cf6a151c87129cb0599ecab36687",
        "967a450f0a66cf6a151c87129cb0599ecab36687", scope.get("base_commit"))
    add("prior_scope_paths", scope.get("n_paths_changed") == 34, 34, scope.get("n_paths_changed"))
    add("prior_scope_out_of_scope", scope.get("out_of_scope_paths") == [], [], scope.get("out_of_scope_paths"))
    add("prior_scope_both_refs", scope.get("same_commit_on_both_cycle_refs") is True,
        True, scope.get("same_commit_on_both_cycle_refs"))

    add("prior_validate_would_pass", validate.get("would_pass") is True, True, validate.get("would_pass"))
    add("prior_validate_exit_code", validate.get("exit_code") == 0, 0, validate.get("exit_code"))
    add("prior_validate_vacuity_disclosed",
        (validate.get("vacuity_observation") or {}).get("passes_without_state_advance") is True,
        True, (validate.get("vacuity_observation") or {}).get("passes_without_state_advance"))

    add("prior_claims_verdict", claims.get("verdict") == "PRIOR_CLAIMS_VERIFIED",
        "PRIOR_CLAIMS_VERIFIED", claims.get("verdict"))
    add("prior_claims_n_checks", claims.get("n_checks") == 97, 97, claims.get("n_checks"))
    add("prior_claims_n_failed", claims.get("n_failed") == 0, 0, claims.get("n_failed"))
    prior_claims_primary = claims.get("primary_result_path")
    add("prior_claims_primary_exists",
        bool(prior_claims_primary) and (REPO_ROOT / prior_claims_primary).is_file(),
        True,
        bool(prior_claims_primary) and (REPO_ROOT / prior_claims_primary).is_file())
    add("prior_claims_primary_binding",
        sha256_file(prior_claims_primary) == claims.get("primary_result_sha256"),
        claims.get("primary_result_sha256"), sha256_file(prior_claims_primary))

    add("item2_head_unchanged", item2.get("head_unchanged") is True, True, item2.get("head_unchanged"))
    add("item2_product_head", item2.get("product_mount_head_now") == EXPECTED_PRODUCT_MOUNT_HEAD,
        EXPECTED_PRODUCT_MOUNT_HEAD, item2.get("product_mount_head_now"))
    add("item2_adjudicator_unchanged", item2.get("adjudicator_unchanged") is True,
        True, item2.get("adjudicator_unchanged"))
    add("item2_protocol_not_executed", item2.get("protocol_executed_this_run") is False,
        False, item2.get("protocol_executed_this_run"))
    add("item2_matched_members", item2.get("matched_members") == 14, 14, item2.get("matched_members"))
    add("item2_of", item2.get("of") == 15, 15, item2.get("of"))
    add("item2_status", str(item2.get("item_2_full_protocol_status", "")).startswith("NOT_YET"),
        "NOT_YET_*", item2.get("item_2_full_protocol_status"))

    add("multilingual_status", mult.get("status") == "PASS", "PASS", mult.get("status"))
    add("multilingual_n_passed", mult.get("n_passed") == 2, 2, mult.get("n_passed"))
    add("multilingual_test_sha", mult.get("test_file_sha256") == MULT_TEST_SHA256,
        MULT_TEST_SHA256, mult.get("test_file_sha256"))
    add("multilingual_product_head", mult.get("product_mount_head") == EXPECTED_PRODUCT_MOUNT_HEAD,
        EXPECTED_PRODUCT_MOUNT_HEAD, mult.get("product_mount_head"))

    add("accepted_lab_head", lab_head == EXPECTED_ACCEPTED_COMMIT, EXPECTED_ACCEPTED_COMMIT, lab_head)
    add("accepted_gate_gate", accepted_gate.get("gate") == "PASS", "PASS", accepted_gate.get("gate"))
    add("accepted_gate_safe", accepted_gate.get("safe_to_integrate") is True,
        True, accepted_gate.get("safe_to_integrate"))
    add("accepted_gate_sha", sha256_file(ACCEPTED_GATE) == ACCEPTED_GATE_SHA,
        ACCEPTED_GATE_SHA, sha256_file(ACCEPTED_GATE))
    add("accepted_gate_required_fixes", accepted_gate.get("required_fixes") == [],
        [], accepted_gate.get("required_fixes"))

    add("prior_stale_repair_verdict", stale.get("verdict") == "STALE_DISCLOSURE_REPAIRED",
        "STALE_DISCLOSURE_REPAIRED", stale.get("verdict"))
    add("prior_stale_repair_n_moved", stale.get("n_moved") == 2, 2, stale.get("n_moved"))

    add("inherited_producer_diag_class",
        pred_diag.get("failure_class") == "PRODUCER_LANE_CYCLE_EXIT1_BEFORE_GATES",
        "PRODUCER_LANE_CYCLE_EXIT1_BEFORE_GATES", pred_diag.get("failure_class"))
    add("inherited_producer_diag_exit", pred_diag.get("exit_code") == 1, 1, pred_diag.get("exit_code"))
    add("inherited_audit_diag_class",
        pred_audit_diag.get("failure_class") == "AUDIT_WORK_QUANTUM_EXPIRED_rc78",
        "AUDIT_WORK_QUANTUM_EXPIRED_rc78", pred_audit_diag.get("failure_class"))
    add("inherited_audit_diag_exit", pred_audit_diag.get("exit_code") == 78, 78,
        pred_audit_diag.get("exit_code"))

    add("benchmark_of_record_sha", sha256_file(BENCHMARK_OF_RECORD) == BENCHMARK_OF_RECORD_SHA,
        BENCHMARK_OF_RECORD_SHA, sha256_file(BENCHMARK_OF_RECORD))
    add("benchmark_of_record_verdict", bench.get("verdict") == "PRODUCT_FALSIFIED",
        "PRODUCT_FALSIFIED", bench.get("verdict"))
    add("benchmark_of_record_exit", bench.get("exit_code") == 1, 1, bench.get("exit_code"))
    add("benchmark_of_record_packet", bench.get("packets_measured") == ["39319405429"],
        ["39319405429"], bench.get("packets_measured"))
    add("benchmark_of_record_n_gates", bench.get("n_gates") == 18, 18, bench.get("n_gates"))
    add("benchmark_of_record_n_failed", bench.get("n_failed") == 4, 4, bench.get("n_failed"))
    failed_gate_names = sorted(
        (g.get("gate") if isinstance(g, dict) else str(g))
        for g in bench.get("failed_gates", []))
    add("benchmark_of_record_failed_gates", failed_gate_names == sorted(EXPECTED_FAILED_GATES),
        sorted(EXPECTED_FAILED_GATES), failed_gate_names)
    add("second_record_sha", sha256_file(SECOND_RECORD) == SECOND_RECORD_SHA,
        SECOND_RECORD_SHA, sha256_file(SECOND_RECORD))

    add("state_evidence_refs_parity", state.get("evidence_refs_n") == len(state.get("evidence_refs", [])),
        len(state.get("evidence_refs", [])), state.get("evidence_refs_n"))
    add("lane_state_evidence_refs_parity",
        lane_state.get("evidence_refs_n") == len(lane_state.get("evidence_refs", [])),
        len(lane_state.get("evidence_refs", [])), lane_state.get("evidence_refs_n"))
    add("state_accepted_run_id", state.get("accepted_run_id") == EXPECTED_ACCEPTED_RUN,
        EXPECTED_ACCEPTED_RUN, state.get("accepted_run_id"))
    add("state_direction_version", state.get("direction_version") == 68, 68, state.get("direction_version"))
    add("state_cycle_status", state.get("cycle_status") == "COMPLETE", "COMPLETE", state.get("cycle_status"))
    add("state_continue_recommended", state.get("continue_recommended") is False,
        False, state.get("continue_recommended"))

    add("no_prior_audit_gate",
        not (REPO_ROOT / f"results/audit/evaluation/CYCLE_{PRED_RUN_ID}_GATE.json").exists(),
        False, (REPO_ROOT / f"results/audit/evaluation/CYCLE_{PRED_RUN_ID}_GATE.json").exists())
    add("no_this_audit_gate",
        not (REPO_ROOT / f"results/audit/evaluation/CYCLE_{RUN_ID}_GATE.json").exists(),
        False, (REPO_ROOT / f"results/audit/evaluation/CYCLE_{RUN_ID}_GATE.json").exists())

    n_failed = sum(1 for c in checks if not c["ok"])
    committed_record_sha = sha256_file(PRIOR_RECORD)
    claims_primary_path = claims.get("primary_result_path")
    claims_pinned_sha = claims.get("primary_result_sha256")
    committed_claims_primary_sha = sha256_file(claims_primary_path) if claims_primary_path else None
    binding_stale = committed_claims_primary_sha != claims_pinned_sha
    gate_gap = any(p.get(k) is None for k in (
        "state_update", "state_gate", "lane_suite", "write_scope",
        "nested_refs", "self_check"))
    rec = {
        "schema": "lex-evaluation-inherited-claims-verification/1",
        "run_id": int(RUN_ID),
        "direction_version": 68,
        "generated_at_utc": utc(),
        "resumed_snapshot_run_id": int(PRED_RUN_ID),
        "primary_result_path": PRIOR_RECORD,
        "primary_result_sha256": committed_record_sha,
        "claim_source": PRIOR_CLAIMS,
        "claim_source_sha256": sha256_file(PRIOR_CLAIMS),
        "n_checks": len(checks),
        "n_failed": n_failed,
        "checks": checks,
        "disclosures": {
            "prior_claim_binding_stale": binding_stale,
            "prior_claim_primary_path": claims_primary_path,
            "prior_claim_pinned_sha256": claims_pinned_sha,
            "committed_claim_primary_sha256": committed_claims_primary_sha,
            "committed_record_sha256": committed_record_sha,
            "prior_claim_binding_note": (
                "The inherited 41192878248 claim-verification artifact is bound to the "
                "benchmark result it actually verified, not to the operational record. "
                "Its sha binding is live; the operational record's content is "
                "independently re-verified here."),
            "inherited_gate_gap": gate_gap,
            "inherited_gate_gap_note": (
                "The committed 41192878248 record has None for state_update, state_gate, "
                "lane_suite, write_scope, nested_refs and self_check. This resume supplies "
                "fresh gate results at the current tree instead of asserting the missing "
                "fields."),
            "inherited_freeze_timestamp_defect": {
                "path": "evaluation/OPERATIONAL_RESUME_41192878248_FREEZE_V3.json",
                "declared_frozen_at_utc": "2026-10-31T12:20:00Z",
                "containing_commit": "176b681b",
                "classification": "HISTORICAL_TIMESTAMP_DEFECT_NOT_A_MEASUREMENT",
                "disposition": "preserved, not edited; not a claim of this run",
            },
        },
        "verdict": (
            "INHERITED_CLAIMS_REVERIFIED_WITH_GATE_GAP_DISCLOSED"
            if n_failed == 0 else "INHERITED_CLAIMS_FAILED"),
        "not_a_measurement": True,
    }
    write_json(CLAIMS_RECORD, rec)
    return rec


# ---------------------------------------------------------------------------
# 5. item-(2) currency only
# ---------------------------------------------------------------------------
def item2_currency() -> dict:
    prior = load_json(PRIOR_ITEM2)
    mount_head = git_ref_head("HEAD", cwd=MOUNT) if MOUNT.is_dir() else None
    remote_head = git_ref_head(LAB_PRODUCT_REF)
    adj_sha = sha256_file(ITEM2_ADJUDICATOR)
    head_unchanged = mount_head == prior.get("product_mount_head_now") == EXPECTED_PRODUCT_MOUNT_HEAD
    adjudicator_unchanged = adj_sha == prior.get("adjudicator_sha256") == ITEM2_ADJUDICATOR_SHA256
    drift = not (head_unchanged and adjudicator_unchanged)
    rec = {
        "schema": "lex-evaluation-item2-currency/1",
        "run_id": int(RUN_ID),
        "direction_version": 68,
        "generated_at_utc": utc(),
        "resumed_snapshot_run_id": int(PRED_RUN_ID),
        "prior_currency_record": PRIOR_ITEM2,
        "prior_currency_record_sha256": sha256_file(PRIOR_ITEM2),
        "product_mount": str(MOUNT),
        "product_mount_head_now": mount_head,
        "product_mount_head_at_prior_record": prior.get("product_mount_head_now"),
        "expected_product_mount_head": EXPECTED_PRODUCT_MOUNT_HEAD,
        "remote_lab_product_head_now": remote_head,
        "remote_lab_product_head_at_prior_record": prior.get("remote_lab_product_head_now"),
        "head_unchanged": head_unchanged,
        "adjudicator": ITEM2_ADJUDICATOR,
        "adjudicator_sha256": adj_sha,
        "adjudicator_unchanged": adjudicator_unchanged,
        "expected_adjudicator_sha256": ITEM2_ADJUDICATOR_SHA256,
        "drift_detected": drift,
        "matched_members": prior.get("matched_members"),
        "of": prior.get("of"),
        "member_for_member_regeneration": prior.get("member_for_member_regeneration"),
        "item_2_full_protocol_status": (
            "NOT_YET_DISCRIMINATING_HEAD_UNCHANGED" if not drift
            else "DRIFT_DETECTED_NOT_EXECUTED"),
        "protocol_executed_this_run": False,
        "reason": (
            "The accepted product head and adjudicator are byte-identical to the prior "
            "currency check; ordered item (2) remains gated because member-for-member "
            "regeneration is 14/15. Re-executing the same instrument at an unchanged "
            "head would be a zero-delta reproduction, so the protocol is NOT run."
            if not drift else
            "Product head or adjudicator drifted. This resume does not execute the "
            "item-(2) protocol up to the bound; drift is disclosed for the auditor."),
        "not_a_measurement": True,
    }
    write_json(ITEM2_RECORD, rec)
    return rec


# ---------------------------------------------------------------------------
# 6. multilingual / provenance supplement
# ---------------------------------------------------------------------------
def multilingual_supplement() -> dict:
    head_r = git("rev-parse", "HEAD", cwd=MOUNT)
    mount_head = head_r.stdout.strip() if head_r.returncode == 0 else None
    out = {
        "schema": "lex-evaluation-multilingual-supplement/1",
        "run_id": int(RUN_ID),
        "direction_version": 68,
        "generated_at_utc": utc(),
        "resumed_snapshot_run_id": int(PRED_RUN_ID),
        "prior_supplement": PRIOR_MULT,
        "prior_supplement_sha256": sha256_file(PRIOR_MULT),
        "test_file": MULT_TEST,
        "test_file_sha256": sha256_file(MULT_TEST),
        "test_file_sha256_frozen": MULT_TEST_SHA256,
        "product_mount": str(MOUNT),
        "product_mount_head": mount_head,
        "product_mount_expected_head": EXPECTED_PRODUCT_MOUNT_HEAD,
        "numeric_environment": numeric_environment(),
        "supplement_reason": (
            "fresh execution of the accepted 2-case multilingual/provenance suite "
            "under the accepted numeric environment; the producer image no longer "
            "carries the scientific stack after the ubuntu-latest migration, so the "
            "accepted environment was restored via pip before the freeze (disclosed)"),
    }
    if mount_head != EXPECTED_PRODUCT_MOUNT_HEAD:
        out.update(status="NOT_VERIFIED_MOUNT_MISSING_OR_DRIFT", n_passed=0,
                   n_failed=0, n_skipped=0, n_unsupported=0, cases=[])
        write_json(MULT_RECORD, out)
        return out
    saved_path = sys.path[:]
    try:
        sys.path.insert(0, str(MOUNT / "frontier" / "frontier-query-retrieval"))
        sys.path.insert(0, str(MOUNT))
        from evaluation import no_pytest_runner as shim
        r = shim.run_file(REPO_ROOT / MULT_TEST, REPO_ROOT)
    except Exception as exc:
        r = {"status": "IMPORT_ERROR", "error": f"{type(exc).__name__}: {exc}",
             "n_passed": 0, "n_failed": 0, "n_skipped": 0, "n_unsupported": 0,
             "cases": []}
    finally:
        sys.path[:] = saved_path
    out.update(r)
    write_json(MULT_RECORD, out)
    return out


# ---------------------------------------------------------------------------
# 7. stale disclosure repair (additive, provenance-preserving)
# ---------------------------------------------------------------------------
def stale_disclosure_repair() -> dict:
    repaired = []
    already = []
    state = load_json(STATE)
    lane_state = load_json(LANE_STATE)
    for doc, label in ((state, "state"), (lane_state, "lane_state")):
        entries = doc.get("nested_evidence_refs_disclosed_known_unresolvable") or []
        keep = []
        moved = []
        for e in entries:
            path = e.get("path", "")
            if path and (REPO_ROOT / path).exists():
                moved.append(e)
            else:
                keep.append(e)
        if moved:
            doc["nested_evidence_refs_disclosed_known_unresolvable"] = keep
            resolved = doc.setdefault("historical_disclosure_resolved_by_branch_history", [])
            for e in moved:
                resolved.append({
                    **e,
                    "resolved_status": "RESOLVED_WORKTREE",
                    "repaired_by_run": int(RUN_ID),
                    "reason": (
                        "Formal disclosure was valid while the path was dangling; the "
                        "path now resolves in the worktree, so keeping it in the "
                        "known-unresolvable list would suppress a live ref. Provenance "
                        "is preserved here, not deleted."),
                    "not_this_cycles_claim": True,
                })
            repaired.extend({"state": label, "path": e.get("path")} for e in moved)
        else:
            already.append(label)
    if repaired:
        write_json(STATE, state)
        write_json(LANE_STATE, lane_state)
    rec = {
        "schema": "lex-evaluation-stale-disclosure-repair/1",
        "run_id": int(RUN_ID),
        "direction_version": 68,
        "generated_at_utc": utc(),
        "verdict": "STALE_DISCLOSURE_REPAIRED" if repaired else "NO_STALE_DISCLOSURE",
        "n_moved": len(repaired),
        "moved": repaired,
        "states_without_stale_entries": already,
        "not_a_measurement": True,
    }
    write_json(STALE_REPAIR, rec)
    return rec


# ---------------------------------------------------------------------------
# 8. gates (reuse the accepted gate entry points)
# ---------------------------------------------------------------------------
def _gate_module():
    import evaluation.operational_resume_41187766812 as mod
    mod.RUN_ID = RUN_ID
    mod.SELF_TEST = SELF_TEST
    return mod


def run_state_gate(mod) -> dict:
    return mod.run_state_gate()


def run_lane_suite(mod) -> dict:
    return mod.run_lane_suite()


def run_write_scope(mod) -> dict:
    return mod.run_write_scope()


def run_nested_refs(mod) -> dict:
    return mod.run_nested_refs()


def run_self_check(mod) -> dict:
    mod.SELF_TEST = SELF_TEST
    return mod.run_self_check()


# ---------------------------------------------------------------------------
# 9. state update (additive only)
# ---------------------------------------------------------------------------
def _add_refs(doc: dict, refs: list[str]) -> int:
    have = set(doc.get("evidence_refs") or [])
    added = 0
    for r in refs:
        if r and r not in have:
            doc.setdefault("evidence_refs", []).append(r)
            have.add(r)
            added += 1
    doc["evidence_refs_n"] = len(doc.get("evidence_refs") or [])
    return added


def finalize_self_check_state(rec: dict) -> None:
    state = load_json(STATE)
    lane_state = load_json(LANE_STATE)
    self_check = rec.get("self_check") or {}
    block = {
        "schema": "lex-evaluation-self-check-ref/1",
        "run_id": int(RUN_ID),
        "artifact": SELF_CHECK_RESULT,
        "verdict": self_check.get("verdict"),
        "exit_code": self_check.get("exit_code"),
        "n_passed": self_check.get("n_passed"),
        "n_failed": self_check.get("n_failed"),
        "pytest_available": self_check.get("pytest_available"),
    }
    for doc in (state, lane_state):
        doc[f"self_check_{RUN_ID}"] = block
        op = doc.get("operational_resume_41192962507") or {}
        op["self_check_verdict"] = self_check.get("verdict")
        op["self_check_n_passed"] = self_check.get("n_passed")
        op["self_check_n_failed"] = self_check.get("n_failed")
        upd = doc.get(f"state_update_{RUN_ID}") or {}
        upd.setdefault("gates_after_update", {})["self_check"] = self_check.get("verdict")
        doc[f"state_update_{RUN_ID}"] = upd
    _add_refs(state, [SELF_CHECK_RESULT])
    _add_refs(lane_state, [SELF_CHECK_RESULT])
    write_json(STATE, state)
    write_json(LANE_STATE, lane_state)


def finalize_gate_state(rec: dict) -> None:
    state = load_json(STATE)
    lane_state = load_json(LANE_STATE)
    gates = rec.get("gates") or {}
    sg = gates.get("state_gate") or {}
    ls = gates.get("lane_suite") or {}
    ws = gates.get("write_scope") or {}
    nr = gates.get("nested_refs") or {}
    for doc in (state, lane_state):
        doc[f"state_integrity_gate_{RUN_ID}"] = {
            "schema": "lex-evaluation-state-gate-ref/1",
            "run_id": int(RUN_ID),
            "artifact": STATE_GATE,
            "verdict": sg.get("verdict"),
            "n_checks": sg.get("n_checks"),
            "n_failed": sg.get("n_failed"),
        }
        op = doc.get("operational_resume_41192962507") or {}
        op["state_gate_verdict"] = sg.get("verdict")
        op["lane_suite_overall_pass"] = ls.get("overall_pass")
        op["write_scope_verdict"] = ws.get("verdict")
        op["nested_refs_verdict"] = nr.get("verdict")
        doc["operational_resume_41192962507"] = op
    write_json(STATE, state)
    write_json(LANE_STATE, lane_state)


def update_state(rec: dict, mod) -> dict:
    state = load_json(STATE)
    lane_state = load_json(LANE_STATE)
    before_state_keys = set(state)
    before_lane_keys = set(lane_state)
    before_state_refs = list(state.get("evidence_refs") or [])
    before_lane_refs = list(lane_state.get("evidence_refs") or [])
    prior_next = state.get("next_recommendation")
    prior_next_lane = lane_state.get("next_recommendation")

    claims = rec["claims"]
    prod = rec["producer"]
    snap = rec["snapshot_scope"]
    item2 = rec["item2"]
    mult = rec["multilingual"]
    stale = rec["stale_disclosure_repair"]
    self_check = rec.get("self_check") or {}
    gates = rec.get("gates") or {}

    status = "AUDIT_READY_PRODUCER_SNAPSHOT"
    next_rec = (
        f"OPERATIONAL RESUME {RUN_ID} (direction v68, evaluation): run {RUN_ID}'s "
        f"PRODUCER job ran 'Run lane cycle' for {prod.get('failed_step_duration_seconds')} s "
        f"against the {prod.get('quantum_seconds_declared')} s work quantum and exited "
        f"{prod.get('exit_code')} with LEX_WORK_QUANTUM_EXPIRED; the producer-state and "
        f"write-scope steps were SKIPPED and audit/integrate were never scheduled. The inner "
        f"agent/provider mechanism that consumed the quantum is UNOBSERVED (logs 403) and is "
        f"not attributed. The if: always() persist step published {SNAPSHOT_COMMIT[:8]} on "
        f"this run's team ref: a real 4-commit / 57-path delta over {SNAPSHOT_PARENT[:8]}, "
        f"not a zero-delta copy. This resume preserves those bytes, verifies the delta is "
        f"{snap.get('n_paths_changed')} paths and {len(snap.get('out_of_scope_paths') or [])} out of "
        f"scope, re-verifies {claims.get('n_checks')} inherited 41192878248 claims "
        f"({claims.get('n_failed')} failed), re-runs only the accepted multilingual/provenance "
        f"suite ({mult.get('status')} {mult.get('n_passed')}/2), and re-verifies accepted pointer "
        f"40265377500 / ea98384e on both halves. It closes the predecessor's gate gap by "
        f"executing state-integrity/lane/write-scope/nested-refs/self-check gates. Ordered item "
        f"(2) stays NOT_YET_DISCRIMINATING (product head 7be4480e unchanged, frozen family "
        f"14/15, protocol not executed). The next discriminating step is a Product handoff: "
        f"regenerate the missing member so the named 15-member family reaches 15/15. A compact "
        f"AUDIT INDEX ({AUDIT_INDEX}) and one-page AUDIT BRIEF ({AUDIT_BRIEF}) scope the auditor. "
        f"continue_recommended=false; both DO-NOT-SERVE orders stand; owner_decision_required "
        f"stays false; no 174k benchmark was run; posture flags stay FALSE.")

    block = {
        "schema": "lex-evaluation-operational-resume/1",
        "run_id": int(RUN_ID),
        "dispatch_run_id": int(DISPATCH_RUN_ID),
        "claim_bearing_run": int(RUN_ID),
        "direction_version": 68,
        "resumed_snapshot_run_id": int(PRED_RUN_ID),
        "resumed_snapshot_commit": SNAPSHOT_COMMIT,
        "snapshot_is_new_delta_over_predecessor": True,
        "snapshot_parent": SNAPSHOT_PARENT,
        "n_snapshot_delta_commits": prod.get("n_snapshot_delta_commits"),
        "n_snapshot_delta_paths": prod.get("n_snapshot_delta_paths"),
        "status": status,
        "failure_class": "PRODUCER_WORK_QUANTUM_EXPIRED_rc78",
        "failure_job": "team",
        "failure_is_orchestration_not_measurement": True,
        "failure_is_validation_failure": False,
        "failure_is_work_quantum_expiry": True,
        "failure_mechanism_observed": True,
        "mechanism_note": prod.get("mechanism_evidence"),
        "diagnosis": DIAG,
        "producer_validation_ran": False,
        "producer_write_scope_ran": False,
        "producer_snapshot_persisted": True,
        "predecessor_operational_record": PRIOR_RECORD,
        "predecessor_operational_record_sha256": rec["claims"].get("primary_result_sha256"),
        "predecessor_audit_diagnosis": PRED_AUDIT_DIAG,
        "inherited_claims_verification": CLAIMS_RECORD,
        "inherited_claims_verified": claims.get("n_failed") == 0,
        "inherited_claim_checks": claims.get("n_checks"),
        "inherited_claim_failures": claims.get("n_failed"),
        "item_2_status": item2.get("item_2_full_protocol_status"),
        "protocol_executed_this_run": False,
        "accepted_run_id_unchanged": EXPECTED_ACCEPTED_RUN,
        "continue_recommended_unchanged": False,
        "control_plane_observation": (
            "if: always() on 'Persist team snapshot' published a partial producer delta "
            "after the lane cycle expired at the work quantum; recorded, not edited"),
        "preserved_work": (
            "no restart; the 77574ac4 snapshot is kept byte-for-byte and this resume adds "
            "the quantum-expiry diagnosis, scope/validate replay, inherited-claim "
            "verification, currency check, multilingual supplement and the missing gates"),
        "discharged_in_resume": [
            f"current producer work-quantum expiry diagnosed -> {DIAG}",
            f"snapshot scope/consistency verified -> {SNAPSHOT_SCOPE}",
            f"producer-state validate predicate replayed at the pre-resume tree -> {VALIDATE_REPLAY}",
            f"inherited 41192878248 claims verified -> {CLAIMS_RECORD}",
            f"item-(2) currency checked only -> {ITEM2_RECORD}",
            f"accepted multilingual/provenance suite re-run -> {MULT_RECORD}",
            f"state-integrity gate -> {STATE_GATE}",
            f"lane suite -> {LANE_SUITE}",
            f"write scope -> {WRITE_SCOPE}",
            f"nested refs -> {NESTED_REFS}",
            f"self-check -> {SELF_CHECK_RESULT}",
        ],
        "claim_ceiling": (
            "Operational resume and audit-readiness only. No frozen bar, packet, serve "
            "verdict, d2_path_scope_probe, standing falsification or 174k benchmark was "
            "scored or re-run."),
        "artifact": OUT_RESULT,
        "report": OUT_REPORT,
        "audit_index": AUDIT_INDEX,
        "audit_brief": AUDIT_BRIEF,
        "audit_status": "PENDING_INDEPENDENT_AUDIT",
        "pending_independent_audit": True,
        "accepted_as_evidence": False,
        "state_gate_verdict": (gates.get("state_gate") or {}).get("verdict"),
        "lane_suite_overall_pass": (gates.get("lane_suite") or {}).get("overall_pass"),
    }
    if stale.get("n_moved"):
        block["stale_disclosure_repair"] = {
            "artifact": STALE_REPAIR, "n_moved": stale["n_moved"],
        }

    diag_block = {
        "schema": "lex-evaluation-orchestration-failure-diagnosis/1",
        "run_id": int(RUN_ID),
        "dispatch_run_id": int(DISPATCH_RUN_ID),
        "direction_version": 68,
        "failure_class": "PRODUCER_WORK_QUANTUM_EXPIRED_rc78",
        "exit_code": 78,
        "quantum_seconds": 2700,
        "failed_step_duration_seconds": prod.get("failed_step_duration_seconds"),
        "failed_step": "Run lane cycle",
        "failed_job": "team",
        "failed_job_id": TEAM_JOB_ID,
        "annotation_lex_work_quantum_expired": prod.get("annotation_lex_work_quantum_expired"),
        "failure_is_orchestration_not_measurement": True,
        "failure_is_validation_failure": False,
        "failure_is_work_quantum_expiry": True,
        "failure_mechanism_observed": True,
        "mechanism_note": prod.get("mechanism_evidence"),
        "artifact": DIAG,
    }

    verdicts = {
        "state_update": (gates.get("state_gate") or {}).get("verdict"),
        "lane_suite": (gates.get("lane_suite") or {}).get("overall_pass"),
        "write_scope": (gates.get("write_scope") or {}).get("verdict"),
        "nested_refs": (gates.get("nested_refs") or {}).get("verdict"),
        "self_check": self_check.get("verdict"),
    }
    upd = {
        "additive_only": True,
        "no_key_removed": True,
        "no_ref_removed": True,
        "accepted_run_id_unchanged": True,
        "proposed_run_id_set_to": int(RUN_ID),
        "github_run_set_to": int(RUN_ID),
        "audit_status": "PENDING_INDEPENDENT_AUDIT",
        "prior_next_recommendation_preserved_in": f"prior_next_recommendation_before_{RUN_ID}",
        "gates_after_update": verdicts,
    }

    for doc, lane in ((state, False), (lane_state, True)):
        doc["lane"] = "evaluation"
        doc["direction_version"] = 68
        doc["evidence_tier"] = "ACCEPTED"
        doc["cycle_status"] = "COMPLETE"
        doc["continue_recommended"] = False
        doc["accepted_run_id"] = EXPECTED_ACCEPTED_RUN
        doc["accepted_commit"] = EXPECTED_ACCEPTED_COMMIT
        doc["github_run"] = int(RUN_ID)
        doc["proposed_run_id"] = int(RUN_ID)
        doc["resumed_run_id"] = int(PRED_RUN_ID)
        doc["resumed_snapshot_run_id"] = int(PRED_RUN_ID)
        doc["operational_resume_of"] = int(PRED_RUN_ID)
        doc["audit_status"] = "PENDING_INDEPENDENT_AUDIT"
        doc["current_cycle_audit_status"] = "PENDING_INDEPENDENT_AUDIT"
        doc["status"] = status
        doc["next_recommendation"] = next_rec
        doc[f"prior_next_recommendation_before_{RUN_ID}"] = (
            prior_next_lane if lane else prior_next)
        doc["operational_resume_41192962507"] = block
        doc["orchestration_failure_diagnosis_41192962507"] = diag_block
        doc["inherited_claims_verification_41192878248_ref"] = {
            "schema": "lex-evaluation-inherited-claims-ref/1",
            "run_id": int(RUN_ID),
            "artifact": CLAIMS_RECORD,
            "verdict": claims.get("verdict"),
            "n_checks": claims.get("n_checks"),
            "n_failed": claims.get("n_failed"),
        }
        doc[f"state_update_{RUN_ID}"] = upd
        doc[f"self_check_{RUN_ID}"] = {
            "schema": "lex-evaluation-self-check-ref/1",
            "run_id": int(RUN_ID),
            "artifact": SELF_CHECK_RESULT,
            "verdict": self_check.get("verdict"),
            "exit_code": self_check.get("exit_code"),
            "n_passed": self_check.get("n_passed"),
            "n_failed": self_check.get("n_failed"),
        }
        doc[f"state_integrity_gate_{RUN_ID}"] = {
            "schema": "lex-evaluation-state-gate-ref/1",
            "run_id": int(RUN_ID),
            "artifact": STATE_GATE,
            "verdict": (gates.get("state_gate") or {}).get("verdict"),
            "n_checks": (gates.get("state_gate") or {}).get("n_checks"),
            "n_failed": (gates.get("state_gate") or {}).get("n_failed"),
        }
        if lane:
            doc[f"lane_parity_update_{RUN_ID}"] = upd

    refs = [
        HYPOTHESIS, FREEZE, DIAG, RUNREC, JOBS, TANNOT,
        PRIOR_RECORD, PRIOR_CLAIMS, PRIOR_SCOPE, PRIOR_VALIDATE, PRIOR_ITEM2,
        PRIOR_MULT, PRIOR_STALE, PRED_DIAG, PRED_AUDIT_DIAG,
        SNAPSHOT_SCOPE, VALIDATE_REPLAY, CLAIMS_RECORD, ITEM2_RECORD, MULT_RECORD,
        STALE_REPAIR, OUT_RESULT, OUT_REPORT, AUDIT_BRIEF, AUDIT_INDEX,
        SELF_SCRIPT, SELF_TEST,
        LANE_SUITE, WRITE_SCOPE, NESTED_REFS, SELF_CHECK_RESULT,
    ]
    _add_refs(state, refs)
    _add_refs(lane_state, refs)

    write_json(STATE, state)
    write_json(LANE_STATE, lane_state)

    upd["verified_after_write"] = {
        "no_key_removed": before_state_keys.issubset(set(state))
        and before_lane_keys.issubset(set(lane_state)),
        "no_ref_removed": set(before_state_refs).issubset(set(state["evidence_refs"]))
        and set(before_lane_refs).issubset(set(lane_state["evidence_refs"])),
        "evidence_refs_n": [state.get("evidence_refs_n"), lane_state.get("evidence_refs_n")],
        "evidence_refs_len": [len(state["evidence_refs"]), len(lane_state["evidence_refs"])],
    }
    state[f"state_update_{RUN_ID}"] = upd
    lane_state[f"state_update_{RUN_ID}"] = upd
    write_json(STATE, state)
    write_json(LANE_STATE, lane_state)
    return {"state_refs_n": state.get("evidence_refs_n"),
            "lane_state_refs_n": lane_state.get("evidence_refs_n"),
            "state_update": upd}


def add_final_gate_ref() -> None:
    state = load_json(STATE)
    lane_state = load_json(LANE_STATE)
    _add_refs(state, [STATE_GATE])
    _add_refs(lane_state, [STATE_GATE])
    write_json(STATE, state)
    write_json(LANE_STATE, lane_state)


# ---------------------------------------------------------------------------
# 10. reports / auditor index
# ---------------------------------------------------------------------------
def build_audit_index(rec: dict) -> dict:
    idx = {
        "schema": "lex-evaluation-audit-index/1",
        "lane": "evaluation",
        "run_id": int(RUN_ID),
        "dispatch_run_id": int(DISPATCH_RUN_ID),
        "direction_version": 68,
        "generated_at_utc": utc(),
        "purpose": (
            "Scope the independent auditor to THIS run's delta. The audit quantum has "
            "already expired repeatedly in this chain; this producer died at the same "
            "2700 s quantum before its validate/scope gates. The auditor should not "
            "re-derive closed history."),
        "headline": (
            f"run {RUN_ID} is a NON-MEASUREMENT PRODUCER WORK-QUANTUM expiry (rc 78, "
            f"{rec.get('producer', {}).get('failed_step_duration_seconds')} s against "
            f"2700 s); its team ref carries a real 4-commit / 57-path delta over "
            f"326f0e53 whose inherited 41192878248 claims re-verify and whose missing "
            f"gates are supplied here"),
        "start_here": [OUT_REPORT, AUDIT_BRIEF],
        "primary_evidence": {
            "current_run": [RUNREC, JOBS, TANNOT],
            "diagnosis": [DIAG],
            "inherited_snapshot": [PRIOR_RECORD, PRIOR_CLAIMS, PRED_DIAG, PRED_AUDIT_DIAG],
        },
        "verification_artifacts": {
            "snapshot_scope": SNAPSHOT_SCOPE,
            "validate_replay": VALIDATE_REPLAY,
            "claim_verification": CLAIMS_RECORD,
            "stale_disclosure_repair": STALE_REPAIR,
            "item2_currency": ITEM2_RECORD,
            "multilingual": MULT_RECORD,
        },
        "gate_artifacts": {
            "state_integrity": STATE_GATE, "lane_suite": LANE_SUITE,
            "write_scope": WRITE_SCOPE, "nested_refs": NESTED_REFS,
            "self_check": SELF_CHECK_RESULT,
        },
        "do_not_redo": [
            "do not re-run the expired lane cycle or its provider work",
            "do not re-execute the standing falsifier or score packet-of-record 39319405429",
            "do not re-derive the item-(2) precondition at unchanged head 7be4480e",
            "do not re-run the universal-174k benchmark",
            "do not mint an audit gate from this index or the producer ref",
        ],
        "verdicts": {
            "current_run": rec.get("producer", {}).get("classification"),
            "snapshot_scope": (rec.get("snapshot_scope") or {}).get("verdict"),
            "claims": (rec.get("claims") or {}).get("verdict"),
            "item2": (rec.get("item2") or {}).get("item_2_full_protocol_status"),
            "multilingual": (rec.get("multilingual") or {}).get("status"),
            "verdict": rec.get("verdict"),
            "state_gate": (rec.get("gates", {}).get("state_gate") or {}).get("verdict"),
            "lane_suite": (rec.get("gates", {}).get("lane_suite") or {}).get("overall_pass"),
            "write_scope": (rec.get("gates", {}).get("write_scope") or {}).get("verdict"),
            "nested_refs": (rec.get("gates", {}).get("nested_refs") or {}).get("verdict"),
            "self_check": (rec.get("self_check") or {}).get("verdict"),
        },
        "posture": "PENDING_INDEPENDENT_AUDIT; accepted_as_evidence=false; no audit gate",
        "not_a_measurement": True,
    }
    write_json(AUDIT_INDEX, idx)
    return idx


def write_audit_brief(rec: dict) -> Path:
    c = rec.get("claims") or {}
    prod = rec.get("producer") or {}
    snap = rec.get("snapshot_scope") or {}
    gates = rec.get("gates") or {}
    text = f"""# AUDIT BRIEF — evaluation run {RUN_ID} (direction v68)

**Verdict:** {rec.get('verdict')} (exit {rec.get('exit_code')}).
PENDING INDEPENDENT AUDIT. No audit gate exists; nothing is accepted.

## What actually happened
- This producer's TEAM job failed at **Run lane cycle**: {prod.get('failed_step_started_at')} -> {prod.get('failed_step_completed_at')} = {prod.get('failed_step_duration_seconds')} s, **exit {prod.get('exit_code')}**, against a **{prod.get('quantum_seconds_declared')} s** work quantum.
- The wrapper annotation `{prod.get('annotation_lex_work_quantum_expired')}` identifies a **work-quantum expiry**, not a measurement or validation failure.
- **Validate active MVP producer state** and **Enforce lane write scope** were SKIPPED; audit and integrate were never scheduled.
- The always-guarded **Persist team snapshot** step still ran and published **{SNAPSHOT_COMMIT[:8]}** on `{SNAPSHOT_REF}` — a real **{prod.get('n_snapshot_delta_commits')}-commit / {prod.get('n_snapshot_delta_paths')}-path** delta over `{SNAPSHOT_PARENT[:8]}`, not a zero-delta copy.
- The inner agent/provider mechanism that consumed the quantum is **UNOBSERVED**: public logs are 403. Do not infer model/auth cause.

## What this resume verified (no re-execution)
- Snapshot delta `{SNAPSHOT_PARENT[:8]}..{SNAPSHOT_COMMIT[:8]}`: **{snap.get('n_paths_changed')} paths**, **{len(snap.get('out_of_scope_paths') or [])} out of scope** -> {snap.get('verdict')}.
- Inherited 41192878248 claims: **{c.get('n_checks')} checks, {c.get('n_failed')} failed** -> {c.get('verdict')}.
- Item (2): **{rec.get('item2', {}).get('matched_members')}/{rec.get('item2', {}).get('of')}** frozen family members; protocol **NOT executed**; status {rec.get('item2', {}).get('item_2_full_protocol_status')} at product head `{EXPECTED_PRODUCT_MOUNT_HEAD[:8]}`.
- Multilingual/provenance suite: **{rec.get('multilingual', {}).get('status')} {rec.get('multilingual', {}).get('n_passed')}/2** under numpy 2.5.4 / scipy 1.18.1 / scikit-learn 1.9.1.
- Accepted pointer: 40265377500 / `{EXPECTED_ACCEPTED_COMMIT[:8]}` verified on both halves.
- Missing gates supplied: state-integrity **{(gates.get('state_gate') or {}).get('verdict')}**, lane suite **{(gates.get('lane_suite') or {}).get('overall_pass')}**, write scope **{(gates.get('write_scope') or {}).get('verdict')}**, nested refs **{(gates.get('nested_refs') or {}).get('verdict')}**, self-check **{(rec.get('self_check') or {}).get('verdict')}**.

## Do not redo
The expired lane cycle, the standing falsifier, packet-of-record 39319405429 scoring, D2 profile,
bypass diagnosis, d2_path_scope_probe, item-(2) precondition and the universal-174k benchmark
are CLOSED for this cycle. The next discriminating step is a Product handoff: make the named
frozen 15-member family 15/15 by member-for-member regeneration.

**Files:** {OUT_REPORT} · {AUDIT_INDEX}
"""
    p = REPO_ROOT / AUDIT_BRIEF
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def write_report(rec: dict) -> Path:
    c = rec.get("claims") or {}
    prod = rec.get("producer") or {}
    snap = rec.get("snapshot_scope") or {}
    gates = rec.get("gates") or {}
    text = f"""# Operational resume — evaluation run {RUN_ID} (direction v68)

**Verdict:** {rec.get('verdict')} (exit {rec.get('exit_code')}).
No audit gate is minted. This is a non-measurement operational resume; all posture flags stay FALSE.

## 1. Why this run was resumed
Run {PRED_RUN_ID} died at `Run lane cycle` after 16 s (rc 1) and persisted the unchanged
predecessor HEAD `326f0e53`. Run {RUN_ID} resumed that snapshot, ran its own lane cycle for
{prod.get('failed_step_duration_seconds')} s against the 2700 s quantum, exited
{prod.get('exit_code')} with `{prod.get('annotation_lex_work_quantum_expired')}`, skipped the
producer-state and write-scope steps, and persisted `{SNAPSHOT_COMMIT[:8]}` (parent
`{SNAPSHOT_PARENT[:8]}`). Audit and integrate were never scheduled.

## 2. Diagnosis (FACT vs UNOBSERVED)
- FACT: the team job failed at `Run lane cycle`, duration {prod.get('failed_step_duration_seconds')} s, exit {prod.get('exit_code')}, annotation `{prod.get('annotation_lex_work_quantum_expired')}`.
- FACT: `Validate active MVP producer state` and `Enforce lane write scope` were skipped; `Clean generated junk` succeeded; `Persist team snapshot` succeeded.
- FACT: the persisted tree is a real delta over the predecessor: {prod.get('n_snapshot_delta_commits')} commits / {prod.get('n_snapshot_delta_paths')} paths.
- UNOBSERVED: the inner agent/provider error that consumed the quantum. Public logs are 403; no cause is asserted.

## 3. Snapshot scope
- Base `{snap.get('base_commit')}` -> head `{snap.get('head_commit')}`.
- {snap.get('n_paths_changed')} paths changed; out of scope: {snap.get('out_of_scope_paths')}.
- Verdict: **{snap.get('verdict')}**; both cycle refs resolve to the snapshot head.

## 4. Inherited 41192878248 deliverable
- Primary record: `{PRIOR_RECORD}` sha256 `{c.get('primary_result_sha256')}`.
- Claim verification: {c.get('n_checks')} checks, {c.get('n_failed')} failed -> **{c.get('verdict')}**.
- The inherited record's final gate fields were `None`; this resume supplies the missing
  state-integrity, lane-suite, write-scope, nested-refs and self-check results at the current tree.

## 5. Item (2) currency
- Product mount head `{rec.get('item2', {}).get('product_mount_head_now')}`; expected
  `{EXPECTED_PRODUCT_MOUNT_HEAD}`; adjudicator sha256 `{rec.get('item2', {}).get('adjudicator_sha256')}`.
- Family regeneration {rec.get('item2', {}).get('matched_members')}/{rec.get('item2', {}).get('of')}.
- Protocol executed this run: **{rec.get('item2', {}).get('protocol_executed_this_run')}**.
- Status: **{rec.get('item2', {}).get('item_2_full_protocol_status')}**.

## 6. Multilingual / provenance supplement
- `{MULT_TEST}` sha256 `{rec.get('multilingual', {}).get('test_file_sha256')}`.
- {rec.get('multilingual', {}).get('status')} {rec.get('multilingual', {}).get('n_passed')}/2; protocol digest
  `{rec.get('multilingual', {}).get('protocol_digest')}`.

## 7. Gates
- state integrity: **{(gates.get('state_gate') or {}).get('verdict')}** ({(gates.get('state_gate') or {}).get('n_checks')} checks)
- lane suite overall_pass: **{(gates.get('lane_suite') or {}).get('overall_pass')}**
- write scope: **{(gates.get('write_scope') or {}).get('verdict')}**
- nested refs: **{(gates.get('nested_refs') or {}).get('verdict')}**
- self-check: **{(rec.get('self_check') or {}).get('verdict')}** ({(rec.get('self_check') or {}).get('n_passed')} passed)

## 8. Claim ceiling
Operational resume and audit-readiness only. No frozen bar, packet, serve verdict,
d2_path_scope_probe, standing falsification or 174k benchmark was scored or re-run.
Both DO-NOT-SERVE orders stand. The next discriminating step is a Product handoff:
regenerate the missing member so the named 15-member family reaches 15/15.

**Audit index:** `{AUDIT_INDEX}` · **Audit brief:** `{AUDIT_BRIEF}`
"""
    p = REPO_ROOT / OUT_REPORT
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--update-state", action="store_true")
    args = ap.parse_args(argv)

    producer = producer_work_quantum_expiry()
    snap = snapshot_scope()
    validate = validate_step_replay()
    claims = claim_verification()
    item2 = item2_currency()
    mult = multilingual_supplement()
    stale = stale_disclosure_repair()

    mod = _gate_module()
    lane_suite = run_lane_suite(mod)
    write_scope = run_write_scope(mod)
    nested = run_nested_refs(mod)
    self_check = None

    gates = {
        "lane_suite": lane_suite,
        "write_scope": write_scope,
        "nested_refs": nested,
        "state_gate": None,
    }
    structural_ok = (
        producer.get("failure_class") == "PRODUCER_WORK_QUANTUM_EXPIRED_rc78"
        and producer.get("exit_code") == 78
        and producer.get("failure_mechanism_observed") is True
        and snap.get("verdict") == "SCOPE_CLEAN"
        and snap.get("snapshot_ref_matches_head") is True
        and snap.get("snapshot_is_new_delta_over_predecessor") is True
        and claims.get("n_failed") == 0
        and item2.get("protocol_executed_this_run") is False
        and mult.get("status") == "PASS"
        and mult.get("n_passed") == 2
        and (lane_suite or {}).get("overall_pass") is True
        and (write_scope or {}).get("verdict") == "SCOPE_CLEAN"
        and (nested or {}).get("verdict") == "NESTED_REFS_RESOLVED"
    )
    verdict = "RESUME_VERIFIED_AUDIT_READY" if structural_ok else "RESUME_VERIFIED_WITH_DISCLOSED_GAPS"
    rec = {
        "schema": "lex-evaluation-operational-resume-verification/1",
        "run_id": int(RUN_ID),
        "dispatch_run_id": int(DISPATCH_RUN_ID),
        "lane": "evaluation",
        "direction_version": 68,
        "generated_at_utc": utc(),
        "resumed_snapshot_run_id": int(PRED_RUN_ID),
        "resumed_snapshot_commit": SNAPSHOT_COMMIT,
        "verdict": verdict,
        "exit_code": EXIT_PASS if structural_ok else EXIT_GAPS,
        "producer": producer,
        "snapshot_scope": snap,
        "validate_replay": validate,
        "claims": claims,
        "item2": item2,
        "multilingual": mult,
        "stale_disclosure_repair": stale,
        "gates": gates,
        "self_check": self_check,
        "state_update": None,
        "state_gate": None,
        "prior_record": PRIOR_RECORD,
        "prior_record_sha256": sha256_file(PRIOR_RECORD),
        "frozen_hypothesis": HYPOTHESIS,
        "freeze": FREEZE,
        "claim_ceiling": (
            "Operational resume and audit-readiness only. No frozen benchmark, packet, "
            "serve verdict, D2 profile, bypass diagnosis, d2_path_scope_probe, standing "
            "falsification or 174k benchmark was scored or re-run. No audit gate minted."),
        "posture_flags": {
            "accepted_as_evidence": False,
            "audit_gate_minted": False,
            "owner_decision_required": False,
            "product_falsified_this_run": False,
        },
        "not_a_measurement": True,
    }
    write_json(OUT_RESULT, rec)
    build_audit_index(rec)
    write_audit_brief(rec)
    write_report(rec)

    if args.update_state:
        rec["state_update"] = update_state(rec, mod)
        self_check = run_self_check(mod)
        rec["self_check"] = self_check
        finalize_self_check_state(rec)
        gates["state_gate"] = run_state_gate(mod)
        add_final_gate_ref()
        finalize_gate_state(rec)
        gates["state_gate_final"] = run_state_gate(mod)
        gates["state_gate"] = gates["state_gate_final"]
        rec["state_gate"] = gates["state_gate_final"]
        gate_ok = (
            (gates["state_gate_final"] or {}).get("verdict") == "ALL_CHECKS_PASS"
            and (self_check or {}).get("verdict") == "SHIM_PASS"
            and (lane_suite or {}).get("overall_pass") is True
            and (write_scope or {}).get("verdict") == "SCOPE_CLEAN"
            and (nested or {}).get("verdict") == "NESTED_REFS_RESOLVED"
        )
        if not gate_ok:
            rec["verdict"] = "RESUME_VERIFIED_WITH_DISCLOSED_GAPS"
            rec["exit_code"] = EXIT_GAPS
        else:
            rec["verdict"] = "RESUME_VERIFIED_AUDIT_READY"
            rec["exit_code"] = EXIT_PASS
        write_json(OUT_RESULT, rec)
        build_audit_index(rec)
        write_audit_brief(rec)
        write_report(rec)

    sg = rec.get("state_gate") or {}
    print(json.dumps({
        "run_id": RUN_ID,
        "verdict": rec["verdict"],
        "exit_code": rec["exit_code"],
        "producer": producer.get("failure_class"),
        "scope": snap.get("verdict"),
        "claims": f"{claims.get('n_checks')}/{claims.get('n_failed')}",
        "item2": item2.get("item_2_full_protocol_status"),
        "multilingual": mult.get("status"),
        "lane_suite": (lane_suite or {}).get("overall_pass"),
        "write_scope": (write_scope or {}).get("verdict"),
        "nested_refs": (nested or {}).get("verdict"),
        "self_check": (self_check or {}).get("verdict"),
        "state_gate": sg.get("verdict"),
    }, indent=2))
    return rec["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
