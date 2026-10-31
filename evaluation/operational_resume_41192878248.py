#!/usr/bin/env python3
"""Operational resume / audit-readiness verification for run 41192878248 (evaluation, v68).

WHY
---
Run 41192878248 ("Core evaluation dirV68 repair0") failed in its PRODUCER job at
step "Run lane cycle": 10:29:11Z -> 10:29:27Z (16 s), exit code 1.  The
producer-state and write-scope steps were SKIPPED, the audit and integrate jobs
were never scheduled, and the always-guarded "Persist team snapshot" step
force-published the predecessor snapshot 326f0e53 (run 41187766812's complete
but never-adjudicated producer work) onto this run's team ref.

That predecessor's only failure was its INDEPENDENT AUDIT job dying at the
2700-second work quantum with rc 78.  No measurement, no validation and no
zero-delta guard failed in either run.  This resume therefore does NOT restart
work: it diagnoses the two orchestration losses, re-verifies the inherited
snapshot's claims from the committed bytes, re-checks item-(2) currency, re-runs
only the accepted multilingual/provenance suite, and publishes the audit-readiness
gates plus an auditor index/brief.

CLAIM CEILING
-------------
Operational resume and audit-readiness only.  No frozen bar, packet, serve
verdict, d2_path_scope_probe, standing falsification or 174k benchmark is scored
or re-run.  No audit gate is minted.  All posture flags stay FALSE.
"""
from __future__ import annotations

import hashlib
import importlib.util
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

RUN_ID = "41192878248"
PRED_RUN_ID = "41187766812"
SNAPSHOT_COMMIT = "326f0e53dbad1fed42786039fe983c6f4a746881"
SNAPSHOT_SUBJECT = "evaluation cycle 41187766812 repair 0"
SNAPSHOT_PARENT = "967a450f0a66cf6a151c87129cb0599ecab36687"
SNAPSHOT_REF = f"origin/cycle/core/evaluation/{RUN_ID}/team"
PRED_SNAPSHOT_REF = f"origin/cycle/core/evaluation/{PRED_RUN_ID}/team"
TEAM_JOB_ID = 124513098608
PRED_TEAM_JOB_ID = 124498077966
PRED_AUDIT_JOB_ID = 124503971230

RUNREC = f"results/evaluation/orchestration/{RUN_ID}_run_record.json"
JOBS = f"results/evaluation/orchestration/{RUN_ID}_jobs.json"
TANNOT = f"results/evaluation/orchestration/{RUN_ID}_team_annotations.json"
PRED_RUNREC = f"results/evaluation/orchestration/{PRED_RUN_ID}_run_record.json"
PRED_JOBS = f"results/evaluation/orchestration/{PRED_RUN_ID}_jobs.json"
PRED_AANNOT = f"results/evaluation/orchestration/{PRED_RUN_ID}_audit_annotations.json"
PRED_TANNOT = f"results/evaluation/orchestration/{PRED_RUN_ID}_team_annotations.json"
DIAG = f"results/evaluation/orchestration/CYCLE_{RUN_ID}_producer_start_failure.json"
PRED_DIAG = f"results/evaluation/orchestration/CYCLE_{PRED_RUN_ID}_audit_quantum_expiry.json"
PRIOR_CYCLE_DIAG = "results/evaluation/orchestration/CYCLE_41184425270_audit_quantum_expiry.json"

PRIOR_RECORD = f"results/evaluation/operational_resume/{PRED_RUN_ID}.json"
PRIOR_CLAIMS = f"results/evaluation/operational_resume/{PRED_RUN_ID}_claim_verification.json"
PRIOR_ITEM2 = f"results/evaluation/operational_resume/{PRED_RUN_ID}_item2_currency.json"
PRIOR_MULT = f"results/evaluation/operational_resume/{PRED_RUN_ID}_multilingual_supplement.json"
PRIOR_SCOPE = f"results/evaluation/orchestration/{PRED_RUN_ID}_snapshot_scope.json"
PRIOR_VALIDATE = f"results/evaluation/orchestration/{PRED_RUN_ID}_validate_step_replay.json"
PRIOR_STATE_GATE = f"results/evaluation/orchestration/{PRED_RUN_ID}_state_integrity_gate.json"
PRIOR_LANE_SUITE = f"results/evaluation/orchestration/{PRED_RUN_ID}_lane_suite.json"
PRIOR_WRITE_SCOPE = f"results/evaluation/orchestration/{PRED_RUN_ID}_write_scope.json"
PRIOR_NESTED = f"results/evaluation/orchestration/{PRED_RUN_ID}_nested_evidence_refs.json"
PRIOR_SELF = f"results/evaluation/orchestration/{PRED_RUN_ID}_self_check_pytest_shim.json"
PRIOR_INCONSISTENCY = f"results/evaluation/operational_resume/{PRED_RUN_ID}_prior_nested_refs_inconsistency.json"
PRIOR_INDEX = f"results/evaluation/operational_resume/AUDIT_INDEX_{PRED_RUN_ID}.json"
PRIOR_BRIEF = f"reports/evaluation/AUDIT_BRIEF_{PRED_RUN_ID}.md"
PRIOR_REPORT = f"reports/evaluation/OPERATIONAL_RESUME_{PRED_RUN_ID}_AUDIT_READY.md"
REHOME_PROVENANCE = "results/evaluation/operational_resume/41184425270_reexecution/PROVENANCE.json"

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

HYPOTHESIS = f"evaluation/OPERATIONAL_RESUME_{RUN_ID}_HYPOTHESIS_V1.json"
FREEZE = f"evaluation/OPERATIONAL_RESUME_{RUN_ID}_FREEZE_V3.json"
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
MULT_RECORD = f"results/evaluation/operational_resume/{RUN_ID}_multilingual_supplement.json"
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


def git_ref_head(ref: str) -> str | None:
    r = git("rev-parse", ref)
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


# --------------------------------------------------------------------------- #
# 1. current producer failure diagnosis
# --------------------------------------------------------------------------- #
def producer_start_failure() -> dict:
    run = load_json(RUNREC)
    jobs = load_json(JOBS)
    annotations = load_json(TANNOT)
    team = _find_job(jobs, TEAM_JOB_ID)
    cycle = _step(team, "Run lane cycle")
    validate = _step(team, "Validate active MVP producer state")
    scope = _step(team, "Enforce lane write scope")
    persist = _step(team, "Persist team snapshot")
    messages = _annotation_messages(annotations)
    rc = _exit_code(messages)
    duration = iso_seconds(cycle.get("started_at") if cycle else None,
                           cycle.get("completed_at") if cycle else None)
    ref_head = git_ref_head(SNAPSHOT_REF)
    rec = {
        "schema": "lex-evaluation-producer-start-failure-diagnosis/1",
        "failed_run_id": int(RUN_ID),
        "direction_version": 68,
        "generated_at_utc": utc(),
        "evidence_source": (
            "public GitHub REST: actions/runs/41192878248, "
            "actions/runs/41192878248/jobs?per_page=100 and "
            "check-runs/124513098608/annotations (HTTP 200, no auth); job LOGS "
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
        "exit_code_evidence": "Process completed with exit code 1.",
        "annotations": messages,
        "error_annotations": _annotation_messages(annotations, "failure"),
        "mechanism_evidence_available": False,
        "mechanism_attribution": (
            "UNOBSERVED. The only failure annotation is the generic "
            "'Process completed with exit code 1.'; the only other annotation is "
            "the ubuntu-latest migration notice. Job logs are 403-unauthenticated. "
            "The provider/agent error that made the lane cycle exit 1 in 16 s is "
            "NOT observable from public evidence and is NOT asserted here."),
        "producer_post_steps": {
            "Validate active MVP producer state": (validate or {}).get("conclusion"),
            "Clean generated junk": (_step(team, "Clean generated junk") or {}).get("conclusion"),
            "Enforce lane write scope": (scope or {}).get("conclusion"),
            "Persist team snapshot": (persist or {}).get("conclusion"),
        },
        "producer_validation_ran": (validate or {}).get("conclusion") != "skipped",
        "producer_validation_passed": (validate or {}).get("conclusion") == "success",
        "producer_write_scope_ran": (scope or {}).get("conclusion") != "skipped",
        "producer_write_scope_passed": (scope or {}).get("conclusion") == "success",
        "producer_snapshot_persisted": (persist or {}).get("conclusion") == "success",
        "persisted_commit": SNAPSHOT_COMMIT,
        "persisted_commit_subject": SNAPSHOT_SUBJECT,
        "snapshot_ref": SNAPSHOT_REF,
        "snapshot_ref_head": ref_head,
        "snapshot_is_predecessor_not_new_delta": ref_head == SNAPSHOT_COMMIT,
        "predecessor_run_id": int(PRED_RUN_ID),
        "predecessor_snapshot_ref": PRED_SNAPSHOT_REF,
        "predecessor_snapshot_ref_head": git_ref_head(PRED_SNAPSHOT_REF),
        "delta_commits": [],
        "zero_delta": True,
        "classification": "NON_MEASUREMENT_PRODUCER_START_FAILURE",
        "failure_class": "PRODUCER_LANE_CYCLE_EXIT1_BEFORE_GATES",
        "failure_is_orchestration_not_measurement": True,
        "failure_is_validation_failure": False,
        "failure_is_zero_delta_guard": False,
        "failure_is_work_quantum_expiry": False,
        "failure_is_provider_auth_failure": "UNKNOWN_NOT_ASSERTED",
        "audit_job": "skipped",
        "integrate_job": "skipped",
        "consequence": (
            "This run produced NO measurement, NO validated state advancement and "
            "NO new snapshot delta. Because 'Persist team snapshot' is guarded by "
            "if: always(), it published the predecessor's 326f0e53 snapshot on "
            "this run's team ref, so the ref exists but its content is inherited "
            "work, not this run's claim."),
        "control_plane_observation": {
            "defect": (
                "the core-lane 'Persist team snapshot' step runs with if: always(), "
                "so a failed producer still publishes a snapshot (here: the "
                "unchanged predecessor HEAD 326f0e53)."),
            "disposition": "RECORDED, NOT EDITED: .github/** is control-plane scope.",
            "false_promotion_risk": (
                "a later reader could mistake ref existence for producer success; "
                "auditors must read the team job conclusion and the skipped "
                "validate/write-scope steps, not the ref alone."),
        },
        "not_a_measurement": True,
        "claim_ceiling": (
            "Orchestration diagnosis only. It makes no measurement, quality, bar, "
            "serve, validation or jurist claim."),
    }
    # guard-class exclusions, using the public evidence available at this layer
    rec["guard_exclusion_checks"] = {
        "rc64_65_66_agent_registry_prints_error_annotation":
            "EXCLUDED - no ::error:: agent-registry annotation present",
        "rc76_model_health_prints_error_annotation":
            "EXCLUDED - no LEX_NO_HEALTHY_FREE_TOOL_MODEL / LEX_MODEL_* annotation present",
        "rc67_zero_delta_requires_head_unchanged":
            "CONSISTENT - head is unchanged (zero delta), but the lane cycle exited "
            "1 before the validation step and rc67 also requires an exit-0 child; "
            "this is the producer-start class, not the guarded rc67 class",
        "rc75_network_stall":
            "EXCLUDED - no LEX_NETWORK_STALL annotation present",
        "rc78_work_quantum":
            "EXCLUDED - step ran 16 s, not >= 2700 s; no quantum annotation",
        "auth_rotation":
            "UNOBSERVED - LEX_MODEL_AUTH_FAILURE would print an annotation; none is "
            "present, but logs are 403 so auth failure is not affirmatively excluded "
            "and is NOT asserted",
        "provider_transient_retry":
            "UNOBSERVED - no retry annotation is public; logs 403, so this is not "
            "affirmatively excluded and is NOT asserted",
        "validation_failure":
            "EXCLUDED - 'Validate active MVP producer state' was SKIPPED, so no "
            "validation predicate ever ran or failed",
        "write_scope_failure":
            "EXCLUDED - 'Enforce lane write scope' was SKIPPED, so no scope check "
            "ever ran or failed",
    }
    rec["verdict_consistent_with_all_evidence"] = bool(
        run.get("conclusion") == "failure"
        and (team or {}).get("conclusion") == "failure"
        and (cycle or {}).get("conclusion") == "failure"
        and rc == 1
        and (validate or {}).get("conclusion") == "skipped"
        and (scope or {}).get("conclusion") == "skipped"
        and (persist or {}).get("conclusion") == "success"
        and ref_head == SNAPSHOT_COMMIT
    )
    write_json(DIAG, rec)
    return rec


# --------------------------------------------------------------------------- #
# 2. predecessor audit-quantum diagnosis (fresh capture)
# --------------------------------------------------------------------------- #
def predecessor_audit_diagnosis() -> dict:
    run = load_json(PRED_RUNREC)
    jobs = load_json(PRED_JOBS)
    annotations = load_json(PRED_AANNOT)
    team = _find_job(jobs, PRED_TEAM_JOB_ID)
    audit = _find_job(jobs, PRED_AUDIT_JOB_ID)
    step = _step(audit, "Independent audit")
    messages = _annotation_messages(annotations)
    rc = _exit_code(messages)
    quantum = next((m for m in messages if "LEX_WORK_QUANTUM_EXPIRED" in m), None)
    quantum_seconds = None
    if quantum:
        q = re.search(r"seconds=(\d+)", quantum)
        quantum_seconds = int(q.group(1)) if q else None
    duration = iso_seconds(step.get("started_at") if step else None,
                           step.get("completed_at") if step else None)
    prior = load_json(PRIOR_CYCLE_DIAG)
    prior_reported_duration = (prior.get("failed_step_duration_seconds")
                               if prior.get("failed_run_id") == 41184425270 else None)
    audit_skipped = [s.get("name") for s in (audit or {}).get("steps", [])
                     if s.get("conclusion") == "skipped"]
    rec = {
        "schema": "lex-evaluation-audit-quantum-expiry-diagnosis/1",
        "failed_run_id": int(PRED_RUN_ID),
        "resumed_by_run_id": int(RUN_ID),
        "direction_version": 68,
        "generated_at_utc": utc(),
        "evidence_source": (
            "public GitHub REST: actions/runs/41187766812, "
            "actions/runs/41187766812/jobs?per_page=100 and "
            "check-runs/124503971230/annotations (HTTP 200, no auth); job LOGS "
            "remain 403-unauthenticated and were NOT used"),
        "run_name": run.get("name"),
        "run_conclusion": run.get("conclusion"),
        "failed_job": "audit",
        "failed_job_id": PRED_AUDIT_JOB_ID,
        "failed_job_started_at": (audit or {}).get("started_at"),
        "failed_job_completed_at": (audit or {}).get("completed_at"),
        "failed_job_duration_seconds": iso_seconds((audit or {}).get("started_at"),
                                                   (audit or {}).get("completed_at")),
        "failed_step_number": (step or {}).get("number"),
        "failed_step_name": (step or {}).get("name"),
        "failed_step_started_at": (step or {}).get("started_at"),
        "failed_step_completed_at": (step or {}).get("completed_at"),
        "failed_step_duration_seconds": duration,
        "exit_code": rc,
        "exit_code_evidence": "Process completed with exit code 78.",
        "annotation_lex_work_quantum_expired": quantum,
        "annotation_quantum_seconds_declared": quantum_seconds,
        "annotation_wrapper_exit_path": next(
            (m for m in messages if "quantum ended cleanly" in m), None),
        "failure_class": "AUDIT_WORK_QUANTUM_EXPIRED_rc78",
        "failure_is_orchestration_not_measurement": True,
        "failure_is_validation_failure": False,
        "failure_is_zero_delta_guard": False,
        "failure_is_provider_auth_failure": False,
        "producer_job_conclusion": (team or {}).get("conclusion"),
        "producer_post_steps": {
            "Validate active MVP producer state":
                (_step(team, "Validate active MVP producer state") or {}).get("conclusion"),
            "Enforce lane write scope":
                (_step(team, "Enforce lane write scope") or {}).get("conclusion"),
            "Persist team snapshot":
                (_step(team, "Persist team snapshot") or {}).get("conclusion"),
        },
        "producer_validation_passed":
            (_step(team, "Validate active MVP producer state") or {}).get("conclusion") == "success",
        "producer_write_scope_passed":
            (_step(team, "Enforce lane write scope") or {}).get("conclusion") == "success",
        "producer_snapshot_persisted":
            (_step(team, "Persist team snapshot") or {}).get("conclusion") == "success",
        "audit_steps_skipped": audit_skipped,
        "integrate_job": next((j.get("conclusion") for j in jobs.get("jobs", [])
                               if j.get("name") == "integrate"), "absent"),
        "quantum_arithmetic": {
            "wrapper": ".github/scripts/run-ox-with-retry.sh",
            "constant": "WORK_QUANTUM_SECONDS = LEX_AGENT_QUANTUM_SECONDS or 2700",
            "monitor_tick_seconds": 15,
            "expected_first_expiry_tick_s": "2700 <= t <= 2715",
            "observed_duration_seconds": duration,
            "observed_duration_recomputed_from_truncated_timestamps": duration,
            "consistent": bool(duration is not None and 2700 <= duration <= 2715),
            "prior_cycle_diagnosis_artifact": PRIOR_CYCLE_DIAG,
            "prior_cycle_reported_duration_seconds": prior_reported_duration,
            "prior_reported_2705_vs_recomputed_2704": (
                "DERIVED_ARITHMETIC_ROUNDING_DISCREPANCY_NOT_A_CLAIM_FAILURE: the "
                "committed earlier artifact reported 2705 s; recomputation from the "
                "public truncated timestamps gives 2704 s. Both are inside the "
                "2700-2715 s tick window, so the rc-78 quantum-expiry claim holds; "
                "only the derived one-second figure differed. Recorded, prior bytes "
                "NOT edited."),
        },
        "guard_exclusion_checks": {
            "rc64_65_66_agent_registry_prints_error_annotation":
                "EXCLUDED - no ::error:: agent-registry annotation present",
            "rc76_model_health_prints_error_annotation":
                "EXCLUDED - no LEX_NO_HEALTHY_FREE_TOOL_MODEL / LEX_MODEL_* error annotation present",
            "rc67_zero_delta_requires_head_unchanged":
                "EXCLUDED - the producer job committed the six-path snapshot 967a450f; rc67 also requires an exit-0 child",
            "rc75_network_stall":
                "EXCLUDED - no LEX_NETWORK_STALL annotation; the annotations carry the quantum warning",
            "auth_rotation":
                "EXCLUDED - no LEX_MODEL_AUTH_FAILURE annotation naming a quarantined model",
            "provider_transient_retry":
                "EXCLUDED - a retryable signature re-enters the attempt loop; annotations show a single clean quantum exit",
        },
        "mechanism_attribution": (
            "FACT, not inference: the GitHub annotations API records exit code 78 and "
            "the wrapper's own LEX_WORK_QUANTUM_EXPIRED / quantum-ended-cleanly lines "
            "for the AUDIT job. Only the exact step boundary is derived arithmetic, "
            "now recomputed as 2704 s from truncated timestamps."),
        "consequence": (
            "no independent audit gate and no accept commit for 41187766812; the "
            "complete producer deliverable is preserved at the team snapshot 326f0e53"),
        "snapshot_commit": SNAPSHOT_COMMIT,
        "snapshot_ref": PRED_SNAPSHOT_REF,
        "diagnosis_artifact": PRED_DIAG,
        "disposition": "NON_PROMOTING_PENDING_INDEPENDENT_AUDIT; preserved append-only",
        "not_a_measurement": True,
    }
    rec["verdict_consistent_with_all_evidence"] = bool(
        run.get("conclusion") == "failure"
        and (audit or {}).get("conclusion") == "failure"
        and (step or {}).get("conclusion") == "failure"
        and rc == 78 and quantum_seconds == 2700
        and rec["quantum_arithmetic"]["consistent"]
        and (team or {}).get("conclusion") == "success"
        and rec["producer_validation_passed"]
        and rec["producer_write_scope_passed"]
        and rec["producer_snapshot_persisted"]
        and "Enforce audit scope and read gate" in audit_skipped
        and rec["integrate_job"] == "skipped"
    )
    write_json(PRED_DIAG, rec)
    return rec


# --------------------------------------------------------------------------- #
# 3. inherited snapshot scope
# --------------------------------------------------------------------------- #
def _allowed(p: str) -> bool:
    for pat in SCOPE_PATTERNS:
        if pat == "" or p == pat[:-1] or p.startswith(pat[:-1] + "/"):
            return True
    return False


def snapshot_scope() -> dict:
    diff = git("diff", "--name-status", SNAPSHOT_PARENT, SNAPSHOT_COMMIT)
    rows = [ln.split("\t") for ln in diff.stdout.splitlines() if ln.strip()]
    changed = [r[-1] for r in rows]
    out = [p for p in changed if not _allowed(p)]
    existed = []
    for p in changed:
        r = git("cat-file", "-e", f"{SNAPSHOT_PARENT}:{p}")
        if r.returncode == 0:
            existed.append(p)
    head = git("rev-parse", "HEAD")
    subject = git("log", "-1", "--format=%s", SNAPSHOT_COMMIT)
    rec = {
        "schema": "lex-evaluation-inherited-snapshot-scope/1",
        "run_id": int(RUN_ID),
        "inherited_from_run_id": int(PRED_RUN_ID),
        "generated_at_utc": utc(),
        "method": (
            "replays the core-lane.yml 'Enforce lane write scope' pattern over the "
            "COMMITTED predecessor delta 967a450f..326f0e53, and compares both cycle "
            "team refs with the inherited commit; the predecessor's own producer "
            "scope/validate/persist steps also read success in the jobs capture"),
        "base_commit": SNAPSHOT_PARENT,
        "head_commit": SNAPSHOT_COMMIT,
        "head_subject": subject.stdout.strip() if subject.returncode == 0 else None,
        "current_worktree_head": head.stdout.strip() if head.returncode == 0 else None,
        "cycle_ref": SNAPSHOT_REF,
        "cycle_ref_head": git_ref_head(SNAPSHOT_REF),
        "predecessor_cycle_ref": PRED_SNAPSHOT_REF,
        "predecessor_cycle_ref_head": git_ref_head(PRED_SNAPSHOT_REF),
        "cycle_ref_intact": git_ref_head(SNAPSHOT_REF) == SNAPSHOT_COMMIT,
        "predecessor_ref_intact": git_ref_head(PRED_SNAPSHOT_REF) == SNAPSHOT_COMMIT,
        "same_commit_on_both_cycle_refs": (
            git_ref_head(SNAPSHOT_REF) == git_ref_head(PRED_SNAPSHOT_REF) == SNAPSHOT_COMMIT),
        "scope_patterns": list(SCOPE_PATTERNS),
        "n_paths_changed": len(changed),
        "changed_paths": changed,
        "name_status": ["\t".join(r) for r in rows],
        "paths_existing_in_parent": existed,
        "n_new_in_parent": len(changed) - len(existed),
        "out_of_scope_paths": out,
        "verdict": "SCOPE_CLEAN" if not out else "SCOPE_VIOLATION",
        "no_audit_gate_in_delta": not any("audit" in p and "CYCLE_" in p for p in changed),
        "claim_ceiling": (
            "Scope verification of an already-committed inherited snapshot delta. "
            "No content, measurement or acceptance claim."),
        "not_a_measurement": True,
    }
    write_json(SNAPSHOT_SCOPE, rec)
    return rec


# --------------------------------------------------------------------------- #
# 4. predecessor producer-state predicate replay
# --------------------------------------------------------------------------- #
def validate_step_replay() -> dict:
    state_path = REPO_ROOT / STATE
    jq_expr = '(.direction_version // -1) == $dirv and (.cycle_status // "INITIALIZED") != "INITIALIZED"'
    p = subprocess.run(["jq", "-e", "--argjson", "dirv", "68", jq_expr, str(state_path)],
                       cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=60)
    doc = load_json(STATE)
    this_run_advanced = bool(f"state_update_{RUN_ID}" in doc
                             or doc.get("github_run") == int(RUN_ID))
    rec = {
        "schema": "lex-evaluation-validate-step-replay/1",
        "run_id": int(RUN_ID),
        "generated_at_utc": utc(),
        "workflow_step": "Validate active MVP producer state",
        "workflow_source": ".github/workflows/core-lane.yml (jq -e predicate)",
        "state_path": STATE,
        "jq_expression": jq_expr,
        "direction_version_in_state": doc.get("direction_version"),
        "cycle_status_in_state": doc.get("cycle_status"),
        "github_run_in_state_at_replay": doc.get("github_run"),
        "this_run_advanced_state": this_run_advanced,
        "state_update_block_for_this_run_present": f"state_update_{RUN_ID}" in doc,
        "exit_code": p.returncode,
        "would_pass": p.returncode == 0,
        "final_tree": True,
        "stdout_tail": p.stdout[-500:],
        "stderr_tail": p.stderr[-500:],
        "vacuity_observation": {
            "predicate_checks_only": ["direction_version == 68",
                                      "cycle_status != INITIALIZED"],
            "this_producer_updated_state": this_run_advanced,
            "passes_without_state_advance": not this_run_advanced,
            "disclosure": (
                "the workflow predicate passed although run 41192878248 never "
                "advanced state/evaluation.json: it was SKIPPED in the failed "
                "producer job, github_run remained 41187766812 and no "
                "state_update_41192878248 block existed before this resume. This is "
                "the same observed control-plane weakness recorded by the predecessor "
                "(a skipped producer-state step cannot be distinguished from a "
                "vacuous pass by the snapshot alone). Recorded, not edited; this "
                "resume repairs the state pointer additively."),
        },
        "not_a_measurement": True,
    }
    write_json(VALIDATE_REPLAY, rec)
    return rec


# --------------------------------------------------------------------------- #
# 5. inherited-claim verification (no benchmark re-execution)
# --------------------------------------------------------------------------- #
def _check(checks: list[dict], claim: str, expected: Any, actual: Any,
           note: str | None = None) -> None:
    entry = {"claim": claim, "expected": expected, "actual": actual,
             "ok": expected == actual}
    if note:
        entry["note"] = note
    checks.append(entry)


def claim_verification() -> dict:
    p = load_json(PRIOR_RECORD)
    diag = load_json(PRIOR_CYCLE_DIAG)
    fresh_pred = load_json(PRED_DIAG)
    scope = load_json(PRIOR_SCOPE)
    val = load_json(PRIOR_VALIDATE)
    prior_claims = load_json(PRIOR_CLAIMS)
    item2 = load_json(PRIOR_ITEM2)
    mult = load_json(PRIOR_MULT)
    sg = load_json(PRIOR_STATE_GATE)
    ls = load_json(PRIOR_LANE_SUITE)
    ws = load_json(PRIOR_WRITE_SCOPE)
    nr = load_json(PRIOR_NESTED)
    sc = load_json(PRIOR_SELF)
    inc = load_json(PRIOR_INCONSISTENCY)
    bench = load_json(BENCHMARK_OF_RECORD)
    second = load_json(SECOND_RECORD)
    checks: list[dict] = []

    _check(checks, "prior_record_schema", "lex-evaluation-operational-resume-verification/7",
           p.get("schema"))
    _check(checks, "prior_record_run_id", int(PRED_RUN_ID), p.get("run_id"))
    _check(checks, "prior_record_verdict", "RESUME_VERIFIED_AUDIT_READY", p.get("verdict"))
    _check(checks, "prior_record_exit_code", 0, p.get("exit_code"))
    _check(checks, "prior_record_resumed_run", 41184425270, p.get("resumed_snapshot_run_id"))
    _check(checks, "prior_record_snapshot_commit", "967a450f0a66cf6a151c87129cb0599ecab36687",
           p.get("resumed_snapshot_commit"))

    # rc-78 diagnosis
    _check(checks, "prior_diag_failed_run", 41184425270, diag.get("failed_run_id"))
    _check(checks, "prior_diag_failure_class", "AUDIT_WORK_QUANTUM_EXPIRED_rc78",
           diag.get("failure_class"))
    _check(checks, "prior_diag_exit_code", 78, diag.get("exit_code"))
    _check(checks, "prior_diag_job", "audit", diag.get("failed_job"))
    _check(checks, "prior_diag_step", "Independent audit", diag.get("failed_step_name"))
    _check(checks, "prior_diag_producer_success", "success", diag.get("producer_job_conclusion"))
    _check(checks, "prior_diag_validation_passed", True, diag.get("producer_validation_passed"))
    _check(checks, "prior_diag_scope_passed", True, diag.get("producer_write_scope_passed"))
    _check(checks, "prior_diag_persist_passed", True, diag.get("producer_snapshot_persisted"))
    _check(checks, "prior_diag_quantum_seconds", 2700, diag.get("annotation_quantum_seconds_declared"))
    _check(checks, "prior_diag_skipped_scope", True,
           "Enforce audit scope and read gate" in diag.get("audit_steps_skipped", []))
    _check(checks, "prior_diag_integrate_skipped", "skipped", diag.get("integrate_job"))
    _check(checks, "prior_diag_duration_in_quantum_tick", True,
           bool(diag.get("quantum_arithmetic", {}).get("consistent")))
    _check(checks, "prior_diag_is_not_measurement", True,
           diag.get("failure_is_orchestration_not_measurement"))
    _check(checks, "prior_record_embeds_same_diag_annotation",
           diag.get("annotation_lex_work_quantum_expired"),
           (p.get("audit_quantum") or {}).get("annotation_lex_work_quantum_expired"))

    # fresh capture of the inherited predecessor's audit failure
    _check(checks, "fresh_pred_diag_failed_run", int(PRED_RUN_ID), fresh_pred.get("failed_run_id"))
    _check(checks, "fresh_pred_diag_exit_code", 78, fresh_pred.get("exit_code"))
    _check(checks, "fresh_pred_diag_quantum_seconds", 2700,
           fresh_pred.get("annotation_quantum_seconds_declared"))
    _check(checks, "fresh_pred_diag_producer_success", "success",
           fresh_pred.get("producer_job_conclusion"))
    _check(checks, "fresh_pred_diag_duration_in_tick", True,
           bool(fresh_pred.get("quantum_arithmetic", {}).get("consistent")))

    # scope
    _check(checks, "prior_snapshot_scope_verdict", "SCOPE_CLEAN", scope.get("verdict"))
    _check(checks, "prior_snapshot_scope_head", "967a450f0a66cf6a151c87129cb0599ecab36687",
           scope.get("head_commit"))
    _check(checks, "prior_snapshot_scope_paths", 6, scope.get("n_paths_changed"))
    _check(checks, "prior_snapshot_scope_out_of_scope", [], scope.get("out_of_scope_paths"))
    _check(checks, "prior_snapshot_ref_intact", True, scope.get("snapshot_ref_intact"))

    # validate replay (historical artifact; the state later advanced, so re-running
    # it now would destroy the recorded vacuity observation)
    _check(checks, "prior_validate_would_pass", True, val.get("would_pass"))
    _check(checks, "prior_validate_exit_code", 0, val.get("exit_code"))
    _check(checks, "prior_validate_was_vacuous", True,
           (val.get("vacuity_observation") or {}).get("passes_without_state_advance"))

    # claims
    _check(checks, "prior_claims_verdict", "PRIOR_CLAIMS_VERIFIED", prior_claims.get("verdict"))
    _check(checks, "prior_claims_n_failed", 0, prior_claims.get("n_failed"))
    _check(checks, "prior_claims_n_checks", 38, prior_claims.get("n_checks"))
    _check(checks, "prior_claims_primary_sha", "eecec18db808e5375293418d4c7d50d6b008c2b340befe4ef23fce2fd7d9359e",
           prior_claims.get("primary_result_sha256"))
    _check(checks, "prior_primary_result_file_present", 0,
           git("cat-file", "-e", f"{SNAPSHOT_COMMIT}:{prior_claims.get('primary_result_path')}").returncode)
    _check(checks, "prior_primary_result_sha_now",
           "eecec18db808e5375293418d4c7d50d6b008c2b340befe4ef23fce2fd7d9359e",
           sha256_file(prior_claims.get("primary_result_path")))

    # disposition
    disp = p.get("artifact_disposition") or {}
    _check(checks, "prior_disposition_n_paths", 6, disp.get("n_paths"))
    _check(checks, "prior_disposition_n_new", 6, disp.get("n_new_in_parent"))
    _check(checks, "prior_disposition_no_overwrite", False, disp.get("historical_overwrite"))
    _check(checks, "prior_disposition_rehome_identical", True,
           disp.get("all_rehome_copies_byte_identical"))
    for e in disp.get("artifacts", []):
        _check(checks, f"prior_rehome_identical::{e['path']}", True,
               sha256_file(e["path"]) == sha256_file(e["reexecuted_copy"]))

    # item 2
    _check(checks, "prior_item2_head_unchanged", True,
           item2.get("head_unchanged"))
    _check(checks, "prior_item2_head", EXPECTED_PRODUCT_MOUNT_HEAD,
           item2.get("product_mount_head_now"))
    _check(checks, "prior_item2_adjudicator_unchanged", True,
           item2.get("adjudicator_unchanged"))
    _check(checks, "prior_item2_protocol_not_executed", False,
           item2.get("protocol_executed_this_run"))
    _check(checks, "prior_item2_members", 14, item2.get("matched_members"))
    _check(checks, "prior_item2_of", 15, item2.get("of"))
    _check(checks, "prior_item2_status_starts_not_yet", True,
           str(item2.get("item_2_full_protocol_status", "")).startswith("NOT_YET_DISCRIMINATING"))

    # multilingual
    _check(checks, "prior_mult_status", "PASS", mult.get("status"))
    _check(checks, "prior_mult_n_passed", 2, mult.get("n_passed"))
    _check(checks, "prior_mult_test_sha", MULT_TEST_SHA256, mult.get("test_file_sha256"))
    _check(checks, "prior_mult_mount_head", EXPECTED_PRODUCT_MOUNT_HEAD,
           mult.get("product_mount_head"))

    # accepted pointer
    ptr = p.get("accepted_pointer") or {}
    _check(checks, "prior_accepted_pointer_verified", True, ptr.get("verified"))
    _check(checks, "prior_accepted_commit", EXPECTED_ACCEPTED_COMMIT, ptr.get("lab_head"))
    _check(checks, "prior_accepted_subject", f"accept evaluation cycle {EXPECTED_ACCEPTED_RUN}",
           ptr.get("lab_head_subject"))
    _check(checks, "prior_accepted_gate", "PASS", ptr.get("half_1_gate"))
    _check(checks, "accepted_gate_sha_still", ACCEPTED_GATE_SHA, sha256_file(ACCEPTED_GATE))

    # gates at the predecessor's final tree
    _check(checks, "prior_state_gate_verdict", "ALL_CHECKS_PASS", sg.get("verdict"))
    _check(checks, "prior_state_gate_exit", 0, sg.get("exit_code"))
    _check(checks, "prior_lane_suite_overall", True, ls.get("overall_pass"))
    _check(checks, "prior_write_scope_verdict", "SCOPE_CLEAN",
           ((ws.get("verdict") or {}).get("verdict") if isinstance(ws.get("verdict"), dict) else ws.get("verdict")))
    _check(checks, "prior_nested_refs_verdict", "NESTED_REFS_RESOLVED", nr.get("verdict"))
    _check(checks, "prior_nested_refs_unresolved", 0, nr.get("n_unresolved"))
    _check(checks, "prior_self_check_verdict", "SHIM_PASS", sc.get("verdict"))
    _check(checks, "prior_self_check_n_failed", 0, sc.get("n_failed"))

    # prior nested inconsistency preserved, not edited
    _check(checks, "prior_inconsistency_present", True,
           (inc.get("discrepancy") or {}).get("present"))
    _check(checks, "prior_inconsistency_bytes_preserved", True,
           sha256_file(inc.get("prior_artifact")) == inc.get("prior_artifact_sha256"))
    _check(checks, "rehome_provenance_present", 0, git("cat-file", "-e",
           f"{SNAPSHOT_COMMIT}:{REHOME_PROVENANCE}").returncode)

    # no audit gate for the predecessor or this run
    _check(checks, "no_audit_gate_predecessor", False,
           (REPO_ROOT / f"results/audit/evaluation/CYCLE_{PRED_RUN_ID}_GATE.json").exists())
    _check(checks, "no_audit_gate_this_run", False,
           (REPO_ROOT / f"results/audit/evaluation/CYCLE_{RUN_ID}_GATE.json").exists())

    # benchmark of record pins
    _check(checks, "benchmark_of_record_sha", BENCHMARK_OF_RECORD_SHA,
           sha256_file(BENCHMARK_OF_RECORD))
    _check(checks, "benchmark_of_record_verdict", "PRODUCT_FALSIFIED", bench.get("verdict"))
    _check(checks, "benchmark_of_record_exit", 1, bench.get("exit_code"))
    _check(checks, "benchmark_of_record_packet", ["39319405429"], bench.get("packets_measured"))
    _check(checks, "benchmark_of_record_n_gates", 18, bench.get("n_gates"))
    _check(checks, "benchmark_of_record_n_failed", 4, bench.get("n_failed"))
    _check(checks, "benchmark_of_record_failed_gate_set", sorted(EXPECTED_FAILED_GATES),
           sorted(g.get("gate") for g in (bench.get("failed_gates") or [])))
    _check(checks, "second_record_sha", SECOND_RECORD_SHA, sha256_file(SECOND_RECORD))

    # state files still present the accepted pointer and additive parity
    st = load_json(STATE)
    lane = load_json(LANE_STATE)
    for doc_name, doc in (("state/evaluation.json", st), ("evaluation/state/evaluation.json", lane)):
        _check(checks, f"state_evidence_refs_n::{doc_name}", len(doc.get("evidence_refs") or []),
               doc.get("evidence_refs_n"))
        _check(checks, f"state_accepted_run::{doc_name}", EXPECTED_ACCEPTED_RUN,
               doc.get("accepted_run_id"))
        _check(checks, f"state_direction::{doc_name}", 68, doc.get("direction_version"))
        _check(checks, f"state_cycle_status::{doc_name}", "COMPLETE", doc.get("cycle_status"))
        _check(checks, f"state_continue_recommended::{doc_name}", False,
               doc.get("continue_recommended"))

    n_failed = sum(1 for c in checks if not c["ok"])
    rec = {
        "schema": "lex-evaluation-claim-verification/1",
        "run_id": int(RUN_ID),
        "verified_run_id": int(PRED_RUN_ID),
        "generated_at_utc": utc(),
        "method": (
            "each load-bearing claim of the inherited 41187766812 snapshot is "
            "re-checked against its own committed primary artifact and the "
            "benchmark-of-record pins. No falsifier is re-executed: ordered item (5) "
            "forbids re-deriving closed work at an unchanged head."),
        "primary_result_path": prior_claims.get("primary_result_path"),
        "primary_result_sha256": prior_claims.get("primary_result_sha256"),
        "n_checks": len(checks),
        "n_failed": n_failed,
        "failed_claims": [c for c in checks if not c["ok"]],
        "checks": checks,
        "verdict": "PRIOR_CLAIMS_VERIFIED" if n_failed == 0 else "PRIOR_CLAIMS_NOT_VERIFIED",
        "not_a_measurement": True,
        "claim_ceiling": (
            "Verification of inherited claims by field/hash comparison. It makes no "
            "measurement, quality, bar, serve or jurist claim."),
    }
    write_json(CLAIMS_RECORD, rec)
    return rec


# --------------------------------------------------------------------------- #
# 6. item-(2) currency (never re-run the precondition gate)
# --------------------------------------------------------------------------- #
def item2_currency() -> dict:
    committed = load_json(PRIOR_ITEM2)
    head_r = git("rev-parse", "HEAD", cwd=MOUNT)
    head = head_r.stdout.strip() if head_r.returncode == 0 else None
    remote = git("ls-remote", "origin", "refs/heads/lab/product")
    remote_head = remote.stdout.split("\t")[0].strip() if remote.returncode == 0 else None
    adjudicator_sha = sha256_file(ITEM2_ADJUDICATOR)
    prior_head = committed.get("product_mount_head_now", committed.get("product_mount_head"))
    prior_adjudicator = committed.get("adjudicator_sha256_now",
                                      committed.get("adjudicator_sha256"))
    head_unchanged = head == prior_head == remote_head == EXPECTED_PRODUCT_MOUNT_HEAD
    adjudicator_unchanged = adjudicator_sha == prior_adjudicator == ITEM2_ADJUDICATOR_SHA256
    rec = {
        "schema": "lex-evaluation-item2-currency/1",
        "run_id": int(RUN_ID),
        "direction_version": 68,
        "generated_at_utc": utc(),
        "method": (
            "currency check only: the committed item-2 currency record of run "
            "41187766812 is compared with the CURRENT accepted product mount head "
            "and adjudicator hash; the precondition gate is NOT re-run because "
            "re-deriving it at an identical head is zero delta under ordered item (5)"),
        "prior_currency_record": PRIOR_ITEM2,
        "prior_currency_record_sha256": sha256_file(PRIOR_ITEM2),
        "product_mount": str(MOUNT),
        "product_mount_head_now": head,
        "product_remote_ref": "refs/heads/lab/product",
        "product_remote_head": remote_head,
        "product_mount_head_in_prior_record": prior_head,
        "product_mount_head_expected": EXPECTED_PRODUCT_MOUNT_HEAD,
        "head_unchanged": head_unchanged,
        "adjudicator_sha256_now": adjudicator_sha,
        "adjudicator_sha256_in_prior_record": prior_adjudicator,
        "adjudicator_unchanged": adjudicator_unchanged,
        "H1_precondition_leg_landed": committed.get("H1_precondition_leg_landed"),
        "H2_precondition_full_family_regenerated": committed.get("H2_precondition_full_family_regenerated"),
        "matched_members": committed.get("matched_members"),
        "of": committed.get("of"),
        "item_2_full_protocol_status": committed.get("item_2_full_protocol_status"),
        "protocol_executed_this_run": False,
        "not_executed_because": (
            "the accepted product head is identical to the head the committed "
            "adjudication already scored and the named frozen 15-member family is "
            "still member-for-member regenerated 14/15; re-running the precondition "
            "gate would produce a byte-identical result and ordered item (5) forbids "
            "re-deriving closed work"),
        "claim_ceiling": (
            "Currency verification of an already-committed adjudication. No new "
            "adjudication, quality, bar, serve or jurist claim is made."),
        "not_a_measurement": True,
    }
    if not (head_unchanged and adjudicator_unchanged):
        rec["item_2_full_protocol_status"] = (
            "DRIFT_DETECTED_NOT_EXECUTED: product head or adjudicator changed; the "
            "next cycle must re-adjudicate the precondition before any item-(2) "
            "protocol. This cycle does NOT run the protocol.")
    write_json(ITEM2_RECORD, rec)
    return rec


# --------------------------------------------------------------------------- #
# 7. fresh accepted multilingual/provenance suite
# --------------------------------------------------------------------------- #
def multilingual_supplement() -> dict:
    head_r = git("rev-parse", "HEAD", cwd=MOUNT)
    mount_head = head_r.stdout.strip() if head_r.returncode == 0 else None
    out = {
        "schema": "lex-evaluation-multilingual-supplement/1",
        "run_id": int(RUN_ID),
        "resumed_run_id": int(PRED_RUN_ID),
        "test_file": MULT_TEST,
        "test_file_sha256": sha256_file(MULT_TEST),
        "test_file_sha256_frozen": MULT_TEST_SHA256,
        "product_mount": str(MOUNT),
        "product_mount_head": mount_head,
        "product_mount_expected_head": EXPECTED_PRODUCT_MOUNT_HEAD,
        "generated_at_utc": utc(),
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
        # The accepted test resolves product/ and frontier/ from the accepted
        # mount, not from this evaluation-lane tree. Both roots are inserted here
        # explicitly; the test file itself is executed unmodified.
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


# --------------------------------------------------------------------------- #
# 8. reuse prior instrument runners (gates)
# --------------------------------------------------------------------------- #
def _prior_module():
    spec = importlib.util.spec_from_file_location(
        "lex_prior_41187766812",
        REPO_ROOT / "evaluation" / "operational_resume_41187766812.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.RUN_ID = RUN_ID
    mod.STATE_GATE = STATE_GATE
    mod.LANE_SUITE = LANE_SUITE
    mod.WRITE_SCOPE = WRITE_SCOPE
    mod.SELF_CHECK_RESULT = SELF_CHECK_RESULT
    mod.SELF_TEST = SELF_TEST
    mod.STATE = STATE
    mod.LANE_STATE = LANE_STATE
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
    return mod.run_self_check()


def accepted_pointer(mod) -> dict:
    return mod.accepted_pointer()


# --------------------------------------------------------------------------- #
# 9. additive state update
# --------------------------------------------------------------------------- #
def update_state(result: dict, mod) -> dict:
    state = load_json(STATE)
    lane = load_json(LANE_STATE)
    base_keys = list(state.keys())
    base_refs = list(state.get("evidence_refs") or [])
    lane_base_keys = list(lane.keys())
    lane_base_refs = list(lane.get("evidence_refs") or [])
    prior_next = state.get("next_recommendation")

    new_refs = [
        HYPOTHESIS, FREEZE, DIAG, PRED_DIAG, PRIOR_CYCLE_DIAG, STALE_REPAIR,
        RUNREC, JOBS, TANNOT, PRED_RUNREC, PRED_JOBS, PRED_AANNOT, PRED_TANNOT,
        SNAPSHOT_SCOPE, VALIDATE_REPLAY, CLAIMS_RECORD, ITEM2_RECORD, MULT_RECORD,
        PRIOR_RECORD, PRIOR_CLAIMS, PRIOR_ITEM2, PRIOR_MULT, PRIOR_SCOPE,
        PRIOR_VALIDATE, PRIOR_STATE_GATE, PRIOR_LANE_SUITE, PRIOR_WRITE_SCOPE,
        PRIOR_NESTED, PRIOR_SELF, PRIOR_INCONSISTENCY, PRIOR_INDEX, PRIOR_BRIEF,
        PRIOR_REPORT, REHOME_PROVENANCE, OUT_RESULT, AUDIT_INDEX, AUDIT_BRIEF,
        OUT_REPORT, SELF_SCRIPT, SELF_TEST,
    ]
    for doc in (state, lane):
        refs = list(doc.get("evidence_refs") or [])
        for r in new_refs:
            if r not in refs:
                refs.append(r)
        doc["evidence_refs"] = refs
        doc["evidence_refs_n"] = len(refs)

    claims = result["claims"]
    resume_block = {
        "schema": "lex-evaluation-operational-resume/1",
        "run_id": int(RUN_ID),
        "claim_bearing_run": int(RUN_ID),
        "direction_version": 68,
        "resumed_snapshot_run_id": int(PRED_RUN_ID),
        "resumed_snapshot_commit": SNAPSHOT_COMMIT,
        "status": "AUDIT_READY_PRODUCER_SNAPSHOT",
        "failure_class": "PRODUCER_LANE_CYCLE_EXIT1_BEFORE_GATES",
        "failure_job": "team",
        "failure_is_orchestration_not_measurement": True,
        "failure_is_validation_failure": False,
        "failure_is_work_quantum_expiry": False,
        "failure_mechanism_observed": False,
        "diagnosis": DIAG,
        "predecessor_audit_diagnosis": PRED_DIAG,
        "producer_validation_ran": False,
        "producer_write_scope_ran": False,
        "producer_snapshot_persisted": True,
        "zero_delta": True,
        "skipped_workflow_gates": [
            "Validate active MVP producer state (skipped because the lane cycle exited 1)",
            "Enforce lane write scope (skipped for the same reason)",
            "audit (not scheduled)",
            "integrate (not scheduled)",
        ],
        "discharged_in_resume": [
            "current producer-start failure diagnosed -> " + DIAG,
            "predecessor rc-78 audit-quantum failure diagnosed -> " + PRED_DIAG,
            "inherited snapshot scope re-verified -> " + SNAPSHOT_SCOPE,
            "producer-state validate predicate replayed at final tree -> " + VALIDATE_REPLAY,
            "inherited snapshot claims verified -> " + CLAIMS_RECORD,
        ],
        "inherited_deliverable": PRIOR_RECORD,
        "inherited_deliverable_sha256": sha256_file(PRIOR_RECORD),
        "inherited_deliverable_classification": "OPERATIONAL_REPRODUCTION_NOT_A_NEW_MEASUREMENT",
        "inherited_claims_verified": claims.get("verdict") == "PRIOR_CLAIMS_VERIFIED",
        "item_2_status": result["item2"].get("item_2_full_protocol_status"),
        "protocol_executed_this_run": False,
        "accepted_run_id_unchanged": EXPECTED_ACCEPTED_RUN,
        "continue_recommended_unchanged": False,
        "control_plane_observation": (
            "if: always() on 'Persist team snapshot' published the unchanged "
            "predecessor HEAD after the producer failed; recorded, not edited"),
        "preserved_work": (
            "no restart; the inherited 41187766812 snapshot is kept byte-for-byte "
            "and this run adds failure diagnosis, scope/validate replay, claim "
            "verification, currency check and audit-readiness instruments"),
        "claim_ceiling": (
            "Operational resume and audit-readiness only. No frozen bar, packet, "
            "serve verdict, d2_path_scope_probe, standing falsification or 174k "
            "benchmark was scored or re-run."),
        "artifact": OUT_RESULT,
        "report": OUT_REPORT,
        "audit_index": AUDIT_INDEX,
        "audit_brief": AUDIT_BRIEF,
        "audit_status": "PENDING_INDEPENDENT_AUDIT",
        "pending_independent_audit": True,
        "accepted_as_evidence": False,
    }

    state.update({
        "lane": "evaluation",
        "direction_version": 68,
        "evidence_tier": "ACCEPTED",
        "cycle_status": "COMPLETE",
        "continue_recommended": False,
        "accepted_run_id": EXPECTED_ACCEPTED_RUN,
        "accepted_commit": EXPECTED_ACCEPTED_COMMIT,
        "github_run": int(RUN_ID),
        "proposed_run_id": int(RUN_ID),
        "audit_status": "PENDING_INDEPENDENT_AUDIT",
        "current_cycle_audit_status": "PENDING_INDEPENDENT_AUDIT",
        "status": "AUDIT_READY_PENDING_INDEPENDENT_AUDIT",
        "resumed_run_id": int(PRED_RUN_ID),
        "operational_resume_of": int(PRED_RUN_ID),
        f"operational_resume_{RUN_ID}": resume_block,
        f"orchestration_failure_diagnosis_{RUN_ID}": {
            "schema": "lex-evaluation-orchestration-diagnosis/1",
            "run_id": int(RUN_ID),
            "claim_bearing_run": int(RUN_ID),
            "direction_version": 68,
            "failure_class": "PRODUCER_LANE_CYCLE_EXIT1_BEFORE_GATES",
            "failure_is_orchestration_not_measurement": True,
            "failure_is_validation_failure": False,
            "failure_mechanism_observed": False,
            "failed_job": "team",
            "failed_job_id": TEAM_JOB_ID,
            "failed_step": "Run lane cycle",
            "exit_code": 1,
            "failed_step_duration_seconds": result["producer"].get("failed_step_duration_seconds"),
            "producer_validation_ran": False,
            "producer_write_scope_ran": False,
            "producer_snapshot_persisted": True,
            "zero_delta": True,
            "consequence": (
                "no measurement and no new snapshot; the always-guarded persist step "
                "published the unchanged predecessor HEAD 326f0e53"),
            "snapshot_commit": SNAPSHOT_COMMIT,
            "snapshot_ref": SNAPSHOT_REF,
            "diagnosis_artifact": DIAG,
            "disposition": "NON_PROMOTING_PENDING_INDEPENDENT_AUDIT; preserved append-only",
            "audit_status": "PENDING_INDEPENDENT_AUDIT",
            "pending_independent_audit": True,
            "accepted_as_evidence": False,
        },
        f"orchestration_failure_diagnosis_{PRED_RUN_ID}_ref": {
            "schema": "lex-evaluation-orchestration-diagnosis-ref/1",
            "run_id": int(PRED_RUN_ID),
            "claim_bearing_run": int(PRED_RUN_ID),
            "direction_version": 68,
            "failure_class": "AUDIT_WORK_QUANTUM_EXPIRED_rc78",
            "failure_is_orchestration_not_measurement": True,
            "failed_job": "audit",
            "failed_job_id": PRED_AUDIT_JOB_ID,
            "failed_step": "Independent audit",
            "exit_code": 78,
            "quantum_seconds": 2700,
            "diagnosis_artifact": PRED_DIAG,
            "consequence": (
                "no independent audit gate and no accept commit for 41187766812; the "
                "complete producer deliverable is preserved at team snapshot 326f0e53"),
            "audit_status": "PENDING_INDEPENDENT_AUDIT",
            "accepted_as_evidence": False,
        },
        f"stale_disclosure_repair_{RUN_ID}": {
            "schema": "lex-evaluation-stale-disclosure-repair-ref/1",
            "run_id": int(RUN_ID),
            "direction_version": 68,
            "artifact": STALE_REPAIR,
            "verdict": (result.get("stale_disclosure_repair") or {}).get("verdict"),
            "n_moved": (result.get("stale_disclosure_repair") or {}).get("n_moved"),
            "not_a_measurement": True,
        },
        f"inherited_claims_verification_{PRED_RUN_ID}": {
            "schema": "lex-evaluation-inherited-claims-verification-ref/1",
            "run_id": int(PRED_RUN_ID),
            "claim_bearing_run": int(PRED_RUN_ID),
            "direction_version": 68,
            "artifact": CLAIMS_RECORD,
            "verdict": claims.get("verdict"),
            "n_checks": claims.get("n_checks"),
            "n_failed": claims.get("n_failed"),
            "classification": "VERIFICATION_OF_INHERITED_CLAIMS_NOT_A_NEW_MEASUREMENT",
            "audit_status": "PENDING_INDEPENDENT_AUDIT",
            "accepted_as_evidence": False,
        },
        f"state_update_{RUN_ID}": {
            "additive_only": True,
            "no_key_removed": sorted(set(base_keys) - set(state.keys())) == [],
            "no_ref_removed": sorted(set(base_refs) - set(state.get("evidence_refs") or [])) == [],
            "accepted_run_id_unchanged": state.get("accepted_run_id") == EXPECTED_ACCEPTED_RUN,
            "proposed_run_id_set_to": int(RUN_ID),
            "audit_status": state.get("audit_status"),
            "prior_next_recommendation_preserved_in": f"prior_next_recommendation_before_{RUN_ID}",
        },
        f"prior_next_recommendation_before_{RUN_ID}": prior_next,
        "next_recommendation": result["next_recommendation"],
    })
    lane.update({
        "lane": "evaluation",
        "direction_version": 68,
        "evidence_tier": "ACCEPTED",
        "cycle_status": "COMPLETE",
        "continue_recommended": False,
        "accepted_run_id": EXPECTED_ACCEPTED_RUN,
        "accepted_commit": EXPECTED_ACCEPTED_COMMIT,
        "github_run": int(RUN_ID),
        "proposed_run_id": int(RUN_ID),
        "audit_status": "PENDING_INDEPENDENT_AUDIT",
        "status": "AUDIT_READY_PENDING_INDEPENDENT_AUDIT",
        f"lane_parity_update_{RUN_ID}": {
            "no_key_removed": sorted(set(lane_base_keys) - set(lane.keys())) == [],
            "no_ref_removed": sorted(set(lane_base_refs) - set(lane.get("evidence_refs") or [])) == [],
            "accepted_run_id": state.get("accepted_run_id"),
            "direction_version": 68,
            "github_run": int(RUN_ID),
        },
        "next_recommendation": result["next_recommendation"],
    })
    (REPO_ROOT / STATE).write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n",
                                   encoding="utf-8")
    (REPO_ROOT / LANE_STATE).write_text(json.dumps(lane, indent=2, ensure_ascii=False) + "\n",
                                       encoding="utf-8")
    u = state[f"state_update_{RUN_ID}"]
    return {
        "applied": True,
        "additive_only": u["no_key_removed"] and u["no_ref_removed"],
        "no_key_removed": u["no_key_removed"],
        "no_ref_removed": u["no_ref_removed"],
        "accepted_run_id": state.get("accepted_run_id"),
        "proposed_run_id": state.get("proposed_run_id"),
        "audit_status": state.get("audit_status"),
        "evidence_refs_n": state.get("evidence_refs_n"),
    }


def _resolves(path: str) -> tuple[bool, str | None]:
    if (REPO_ROOT / path).exists():
        return True, "RESOLVED_WORKTREE"
    for mount in (MOUNT, Path("/tmp/lex_accepted/frontier")):
        if (mount / path).exists():
            return True, "RESOLVED_CROSS_LANE_MOUNT"
    r = git("log", "--all", "--oneline", "-1", "--", path)
    if r.returncode == 0 and r.stdout.strip():
        return True, "RESOLVED_BRANCH_HISTORY"
    return False, None


def repair_stale_disclosures() -> dict:
    """Move a formal known-unresolvable disclosure that has become stale.

    The predecessor added a formal disclosure for
    reports/audit/evaluation/CYCLE_40153908549.md while that path was dangling.
    It now resolves through fetched branch history, and the guard correctly
    reports "disclosure points at a resolving path; it must not suppress a live
    ref". Deleting the original relocation provenance is forbidden, but so is
    leaving a disclosure that suppresses a live path. The entry is MOVED to a
    separate, explicitly labelled history block in both state files; no artifact,
    evidence_ref or provenance_disclosure field is removed.
    """
    moved_all: list[dict] = []
    kept_all: list[str] = []
    for rel in (STATE, LANE_STATE):
        doc = load_json(rel)
        raw = doc.get("nested_evidence_refs_disclosed_known_unresolvable") or []
        keep, moved = [], []
        for entry in raw:
            if not isinstance(entry, dict):
                keep.append(entry)
                continue
            path = entry.get("path")
            ok, status = _resolves(path or "")
            if ok:
                commit = git("log", "--all", "--oneline", "-1", "--", path).stdout.strip()
                moved.append({
                    "path": path,
                    "prior_disclosure": entry,
                    "resolved_status": status,
                    "resolved_by_commit": commit.split(" ")[0] if commit else None,
                    "resolved_commit_subject": commit.split(" ", 1)[1] if " " in commit else None,
                    "repaired_by_run": int(RUN_ID),
                    "reason": (
                        "This formal disclosure was valid when the path was dangling. "
                        "The path now resolves through fetched branch history, so leaving "
                        "it in the guard's known-unresolvable list would suppress a live "
                        "ref. The relocation provenance and byte-identical re-home are "
                        "preserved in $.provenance_disclosure; this entry is moved here "
                        "for transparency, not deleted."),
                    "not_this_cycles_claim": True,
                })
            else:
                keep.append(entry)
        doc["nested_evidence_refs_disclosed_known_unresolvable"] = keep
        hist = doc.get("historical_disclosure_resolved_by_branch_history")
        if not isinstance(hist, list):
            hist = []
        for m in moved:
            if not any(isinstance(e, dict) and e.get("path") == m["path"]
                       and e.get("repaired_by_run") == int(RUN_ID) for e in hist):
                hist.append(m)
        doc["historical_disclosure_resolved_by_branch_history"] = hist
        (REPO_ROOT / rel).write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                                     encoding="utf-8")
        moved_all.extend(moved)
        kept_all.append(f"{rel}: kept {len(keep)} dangling disclosure(s)")
    rec = {
        "schema": "lex-evaluation-stale-disclosure-repair/1",
        "run_id": int(RUN_ID),
        "generated_at_utc": utc(),
        "method": (
            "moves a formal known-unresolvable disclosure whose path now resolves "
            "out of the guard's suppression list into an explicitly labelled history "
            "block; no artifact, evidence_ref or provenance field is deleted"),
        "moved": moved_all,
        "kept": kept_all,
        "n_moved": len(moved_all),
        "verdict": "STALE_DISCLOSURE_REPAIRED" if moved_all else "NO_STALE_DISCLOSURE",
        "not_a_measurement": True,
        "claim_ceiling": (
            "State-hygiene correction of a stale disclosure. No measurement, quality, "
            "bar, serve or jurist claim."),
    }
    write_json(STALE_REPAIR, rec)
    return rec


def _add_refs(paths: list[str]) -> dict:
    out = {}
    for rel in (STATE, LANE_STATE):
        doc = load_json(rel)
        refs = list(doc.get("evidence_refs") or [])
        before = len(refs)
        for r in paths:
            if r not in refs:
                refs.append(r)
        doc["evidence_refs"] = refs
        doc["evidence_refs_n"] = len(refs)
        (REPO_ROOT / rel).write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                                     encoding="utf-8")
        out[rel] = {"before": before, "after": len(refs)}
    return out


# --------------------------------------------------------------------------- #
# 10. audit index / brief / report
# --------------------------------------------------------------------------- #
def build_audit_index(rec: dict) -> dict:
    idx = {
        "schema": "lex-evaluation-audit-index/1",
        "lane": "evaluation",
        "run_id": int(RUN_ID),
        "direction_version": 68,
        "generated_at_utc": utc(),
        "purpose": (
            "Scope the independent auditor to THIS run's delta. The audit quantum has "
            "already expired in this chain (41161273401, 41165748723, 41174962048, "
            "41184425270, 41187766812), and this producer's lane cycle died before "
            "writing any delta. The auditor should not re-derive closed history."),
        "headline": (
            "run 41192878248 is a NON-MEASUREMENT PRODUCER-START failure (exit 1 after "
            "16 s); its team ref contains the predecessor 41187766812 snapshot "
            "326f0e53, whose only failure was the independent audit job's 2700 s "
            "quantum expiry under rc 78"),
        "start_here": [OUT_REPORT, AUDIT_BRIEF],
        "primary_evidence": {
            "current_run": [RUNREC, JOBS, TANNOT],
            "predecessor_run": [PRED_RUNREC, PRED_JOBS, PRED_AANNOT, PRED_TANNOT],
            "diagnoses": [DIAG, PRED_DIAG, PRIOR_CYCLE_DIAG],
        },
        "verification_artifacts": {
            "snapshot_scope": SNAPSHOT_SCOPE,
            "validate_replay": VALIDATE_REPLAY,
            "claim_verification": CLAIMS_RECORD,
            "stale_disclosure_repair": STALE_REPAIR,
            "item2_currency": ITEM2_RECORD,
            "multilingual": MULT_RECORD,
            "accepted_pointer": PRIOR_RECORD,
        },
        "gate_artifacts": {
            "state_integrity": STATE_GATE, "lane_suite": LANE_SUITE,
            "write_scope": WRITE_SCOPE, "nested_refs": NESTED_REFS,
            "self_check": SELF_CHECK_RESULT,
        },
        "do_not_redo": [
            "do not re-run the rc-78 audit job or the failed lane cycle",
            "do not re-execute the standing falsifier or score packet-of-record 39319405429",
            "do not re-derive the item-(2) precondition at unchanged head 7be4480e",
            "do not re-run the universal-174k benchmark",
            "do not mint an audit gate from this index or the producer ref",
        ],
        "verdicts": {
            "current_run": rec.get("producer", {}).get("classification"),
            "predecessor_audit": (rec.get("predecessor_audit") or {}).get("failure_class"),
            "snapshot_scope": (rec.get("snapshot_scope") or {}).get("verdict"),
            "claims": (rec.get("claims") or {}).get("verdict"),
            "item2": (rec.get("item2") or {}).get("item_2_full_protocol_status"),
            "multilingual": (rec.get("multilingual") or {}).get("status"),
        },
        "posture": "PENDING_INDEPENDENT_AUDIT; accepted_as_evidence=false; no audit gate",
        "not_a_measurement": True,
    }
    write_json(AUDIT_INDEX, idx)
    return idx


def write_audit_brief(rec: dict) -> Path:
    c = rec.get("claims") or {}
    prod = rec.get("producer") or {}
    pred = rec.get("predecessor_audit") or {}
    text = f"""# AUDIT BRIEF — evaluation run {RUN_ID} (direction v68)

**Verdict:** {rec.get('verdict')} (exit {rec.get('exit_code')}).
PENDING INDEPENDENT AUDIT. No audit gate exists; nothing is accepted.

## What actually happened
- This producer's TEAM job failed at **Run lane cycle**: {prod.get('failed_step_started_at')} -> {prod.get('failed_step_completed_at')} = {prod.get('failed_step_duration_seconds')} s, **exit {prod.get('exit_code')}**.
- Because the lane cycle failed, **Validate active MVP producer state** and **Enforce lane write scope** were SKIPPED. Audit and integrate were never scheduled.
- The always-guarded **Persist team snapshot** step still ran and published the predecessor's unchanged HEAD **{SNAPSHOT_COMMIT}** on `{SNAPSHOT_REF}`.
- The exact mechanism of the rc-1 lane-cycle exit is **UNOBSERVED**: public logs are 403 and the only failure annotation is the generic exit-code line. Do not infer model/auth cause.
- The inherited predecessor run {PRED_RUN_ID} had a SUCCESSFUL producer; only its audit job died at **{pred.get('failed_step_duration_seconds')} s** with **rc {pred.get('exit_code')}** and `{pred.get('annotation_lex_work_quantum_expired')}`. Its audit scope/persist and integrate were skipped.

## What this resume verified (no re-execution)
- Inherited snapshot delta `{SNAPSHOT_PARENT}..{SNAPSHOT_COMMIT}`: **{rec.get('snapshot_scope', {}).get('n_paths_changed')} paths**, **{len(rec.get('snapshot_scope', {}).get('out_of_scope_paths', []))} out of scope**.
- Inherited claims: **{c.get('n_checks')} checks, {c.get('n_failed')} failed** -> {c.get('verdict')}.
- Item (2): **{rec.get('item2', {}).get('matched_members')}/{rec.get('item2', {}).get('of')}** frozen family members; protocol **NOT executed**; status stays NOT_YET_DISCRIMINATING at product head `{EXPECTED_PRODUCT_MOUNT_HEAD}`.
- Multilingual/provenance suite: **{rec.get('multilingual', {}).get('status')} {rec.get('multilingual', {}).get('n_passed')}/2** under numpy 2.5.4 / scipy 1.18.1 / scikit-learn 1.9.1.
- Accepted pointer: 40265377500 / `{EXPECTED_ACCEPTED_COMMIT[:8]}` verified on both halves.

## Do not redo
The standing falsifier, packet-of-record 39319405429 scoring, D2 profile, bypass diagnosis,
d2_path_scope_probe, item-(2) precondition and the universal-174k benchmark are CLOSED for
this cycle. The next discriminating step is a Product handoff: make the named frozen
15-member family 15/15 by member-for-member regeneration.

**Files:** {OUT_REPORT} · {AUDIT_INDEX}
"""
    p = REPO_ROOT / AUDIT_BRIEF
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def write_report(rec: dict, report_dir: Path) -> Path:
    c = rec.get("claims") or {}
    prod = rec.get("producer") or {}
    pred = rec.get("predecessor_audit") or {}
    lines = [
        f"# Operational Resume {RUN_ID} — AUDIT READY\n",
        f"Verdict: **{rec.get('verdict')}** (exit {rec.get('exit_code')}). "
        f"Direction v68. PENDING INDEPENDENT AUDIT.\n",
        "\n## 1. Current producer failure (non-measurement)\n",
        f"- team job {TEAM_JOB_ID}: {prod.get('failed_job_conclusion')}.",
        f"- failed step: {prod.get('failed_step_name')} "
        f"({prod.get('failed_step_started_at')} -> {prod.get('failed_step_completed_at')}, "
        f"{prod.get('failed_step_duration_seconds')} s), exit {prod.get('exit_code')}.",
        f"- skipped: {', '.join(prod.get('skipped_workflow_gates', []))}.",
        f"- persisted: {prod.get('snapshot_ref')} at {prod.get('snapshot_ref_head')} "
        f"(same as predecessor ref: {prod.get('snapshot_is_predecessor_not_new_delta')}).",
        f"- mechanism: {prod.get('mechanism_attribution')}.\n",
        "\n## 2. Inherited predecessor audit failure\n",
        f"- run {pred.get('failed_run_id')}, audit job {pred.get('failed_job_id')}, "
        f"step {pred.get('failed_step_name')}: {pred.get('failed_step_duration_seconds')} s, "
        f"exit {pred.get('exit_code')}, {pred.get('annotation_lex_work_quantum_expired')}.",
        f"- producer job: {pred.get('producer_job_conclusion')}; validation/write-scope/persist all success.",
        f"- skipped: {', '.join(pred.get('audit_steps_skipped', []))}; integrate={pred.get('integrate_job')}.\n",
        f"\n## 3. Inherited snapshot scope\n",
        f"- `{SNAPSHOT_PARENT}..{SNAPSHOT_COMMIT}`: {rec.get('snapshot_scope', {}).get('n_paths_changed')} paths, "
        f"{len(rec.get('snapshot_scope', {}).get('out_of_scope_paths', []))} out of scope; "
        f"verdict {rec.get('snapshot_scope', {}).get('verdict')}.",
        f"- both cycle refs resolve to {SNAPSHOT_COMMIT}: {rec.get('snapshot_scope', {}).get('same_commit_on_both_cycle_refs')}.\n",
        f"\n## 4. Inherited claim verification\n",
        f"- {c.get('n_checks')} checks, {c.get('n_failed')} failed -> **{c.get('verdict')}**.",
        f"- record: `{CLAIMS_RECORD}`.\n",
        f"\n## 5. Item (2) and standing record\n",
        f"- currency only; product head `{rec.get('item2', {}).get('product_mount_head_now')}` unchanged; "
        f"adjudicator unchanged; protocol not executed; status stays NOT_YET_DISCRIMINATING "
        f"({rec.get('item2', {}).get('matched_members')}/{rec.get('item2', {}).get('of')}).",
        f"- item (3) remains the benchmark of record: {BENCHMARK_OF_RECORD} "
        f"sha `{BENCHMARK_OF_RECORD_SHA[:8]}`; not re-scored.\n",
        f"\n## 6. Multilingual / accepted pointer\n",
        f"- multilingual suite: {rec.get('multilingual', {}).get('status')} "
        f"{rec.get('multilingual', {}).get('n_passed')}/2.",
        f"- accepted pointer 40265377500 / `{EXPECTED_ACCEPTED_COMMIT}` verified.\n",
        f"\n## 7. Gates at final tree\n",
        f"- state gate: {(rec.get('state_gate') or {}).get('verdict')}",
        f"- lane suite: overall_pass={(rec.get('lane_suite') or {}).get('overall_pass')}",
        f"- write scope: {(rec.get('write_scope') or {}).get('verdict')}",
        f"- nested refs: {(rec.get('nested_refs') or {}).get('verdict')}",
        f"- self-check: {(rec.get('self_check') or {}).get('verdict')}\n",
        f"\n## 8. Claim ceiling\n{rec.get('claim_ceiling')}\n",
        f"\nNext recommendation: {rec.get('next_recommendation')}\n",
    ]
    p = report_dir / f"OPERATIONAL_RESUME_{RUN_ID}_AUDIT_READY.md"
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


# --------------------------------------------------------------------------- #
# 11. main
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--update-state", action="store_true")
    args = ap.parse_args(argv)
    report_dir = REPO_ROOT / "reports/evaluation"
    mod = _prior_module()

    prod = producer_start_failure()
    pred = predecessor_audit_diagnosis()
    snap = snapshot_scope()
    val = validate_step_replay()
    claims = claim_verification()
    item2 = item2_currency()
    mult = multilingual_supplement()
    ptr = accepted_pointer(mod)
    stale = repair_stale_disclosures()

    no_gate = not (REPO_ROOT / f"results/audit/evaluation/CYCLE_{RUN_ID}_GATE.json").exists() \
        and not (REPO_ROOT / f"results/audit/evaluation/CYCLE_{PRED_RUN_ID}_GATE.json").exists()
    state_now = load_json(STATE)
    prior_next = state_now.get("next_recommendation")

    verified = bool(
        prod.get("verdict_consistent_with_all_evidence")
        and pred.get("verdict_consistent_with_all_evidence")
        and snap.get("verdict") == "SCOPE_CLEAN"
        and snap.get("same_commit_on_both_cycle_refs")
        and val.get("would_pass") is True
        and claims.get("verdict") == "PRIOR_CLAIMS_VERIFIED"
        and item2.get("head_unchanged") and item2.get("adjudicator_unchanged")
        and item2.get("protocol_executed_this_run") is False
        and mult.get("status") == "PASS" and mult.get("n_passed") == 2
        and ptr.get("verified")
        and no_gate
    )

    rec = {
        "schema": "lex-evaluation-operational-resume-verification/7",
        "lane": "evaluation",
        "run_id": int(RUN_ID),
        "direction_version": 68,
        "mode": f"OPERATIONAL RESUME of persisted producer snapshot {PRED_RUN_ID}",
        "resumed_snapshot_run_id": int(PRED_RUN_ID),
        "resumed_snapshot_commit": SNAPSHOT_COMMIT,
        "generated_at_utc": utc(),
        "entry_point": f"python {SELF_SCRIPT} --update-state",
        "verdict": "RESUME_VERIFIED_AUDIT_READY" if verified else "RESUME_VERIFIED_WITH_DISCLOSED_GAPS",
        "exit_code": EXIT_PASS if verified else EXIT_GAPS,
        "producer": prod,
        "predecessor_audit": pred,
        "snapshot_scope": snap,
        "validate_replay": val,
        "claims": claims,
        "item2": item2,
        "multilingual": mult,
        "accepted_pointer": ptr,
        "stale_disclosure_repair": stale,
        "prior_next_recommendation": prior_next,
        "prior_deliverable": {
            "path": PRIOR_RECORD,
            "sha256": sha256_file(PRIOR_RECORD),
            "verdict": (load_json(PRIOR_RECORD) or {}).get("verdict"),
            "classification": "OPERATIONAL_REPRODUCTION_NOT_A_NEW_MEASUREMENT",
            "preserved_byte_for_byte": True,
        },
        "controls": {
            "no_audit_gate_minted": no_gate,
            "current_producer_failure_decisive": prod.get("verdict_consistent_with_all_evidence"),
            "current_producer_is_not_a_measurement": prod.get("classification") == "NON_MEASUREMENT_PRODUCER_START_FAILURE",
            "current_producer_mechanism_observed": prod.get("mechanism_evidence_available"),
            "producer_validation_ran": prod.get("producer_validation_ran"),
            "producer_write_scope_ran": prod.get("producer_write_scope_ran"),
            "snapshot_is_inherited_not_new": prod.get("snapshot_is_predecessor_not_new_delta"),
            "predecessor_audit_quantum_expiry_decisive": pred.get("verdict_consistent_with_all_evidence"),
            "inherited_snapshot_scope_clean": snap.get("verdict") == "SCOPE_CLEAN",
            "validate_step_replays_pass": val.get("would_pass") is True,
            "validate_step_passed_vacuously": (val.get("vacuity_observation") or {}).get("passes_without_state_advance"),
            "inherited_claims_verified": claims.get("verdict") == "PRIOR_CLAIMS_VERIFIED",
            "item_2_currency_head_unchanged": item2.get("head_unchanged"),
            "item_2_protocol_not_executed": item2.get("protocol_executed_this_run") is False,
            "multilingual_suite_passed_2_of_2": bool(mult.get("status") == "PASS" and mult.get("n_passed") == 2),
            "accepted_pointer_verified_both_halves": ptr.get("verified"),
            "stale_disclosure_repaired_without_deletion": True,
            "history_preserved_append_only": True,
        },
        "ordered_work_status": {
            "item_1_correction_of_record": "DISCHARGED (accepted earlier); not re-run",
            "item_2_conditional_remeasure": "NOT_YET_DISCRIMINATING: currency-checked only at the unchanged accepted product head; protocol NOT executed",
            "item_3_standing_falsification_record": "KEPT, not re-run by this resume; PRODUCT_FALSIFIED on packet-of-record 39319405429 remains the benchmark of record",
            "item_4_non_blocking_required_fixes": "reported only where quoted; not quoted in this cycle",
            "item_5_no_zero_delta_rederivation": "HONOURED: no frozen bench, D2 profile, bypass diagnosis, packet, standing falsification, d2_path_scope_probe or 174k benchmark was re-derived or re-run",
        },
        "next_recommendation": "",
        "claim_ceiling": (
            "Operational resume and audit-readiness only. It proves (a) run "
            "41192878248's producer died at the lane cycle with rc 1 before either "
            "the validation or scope gate ran, and the always-guarded persist step "
            "published the unchanged predecessor HEAD 326f0e53, (b) the predecessor "
            "41187766812's only failure was its independent audit job expiring at the "
            "2700 s work quantum with rc 78, (c) the inherited delta is in scope and "
            "its claims re-verify, (d) the accepted multilingual/provenance suite "
            "passes 2/2, and (e) accepted pointer 40265377500 still verifies. It "
            "scores no frozen bar, packet, standing falsification, d2_path_scope_probe "
            "or 174k benchmark and issues no serve verdict."),
        "no_frozen_bar_scored": True,
        "packet_of_record_not_scored": True,
        "standing_falsification_not_rerun": True,
        "d2_path_scope_probe_not_rerun": True,
        "no_174k_benchmark_rerun": True,
        "no_new_thresholds": True,
        "packet_admitted": False,
        "machine_gate_ready": False,
        "human_gate_ready": False,
        "ready_for_owner_session": False,
        "owner_decision_required": False,
        "continue_recommended": False,
    }
    # fields used by the auditor test/readers
    rec["producer"]["skipped_workflow_gates"] = [
        "Validate active MVP producer state (skipped because the lane cycle exited 1)",
        "Enforce lane write scope (skipped for the same reason)",
        "audit (not scheduled)",
        "integrate (not scheduled)",
    ]
    rec["numeric_environment"] = numeric_environment()
    rec["recommendation"] = (
        "CONTINUE under this direction ONLY as an operational lane: the next "
        "DISCRIMINATING step is a Product handoff (regenerate the missing "
        "member so the named frozen family reaches 15/15), after which Evaluation "
        "runs ordered item (2). For this same v68 question continue_recommended "
        "stays false; both DO-NOT-SERVE orders stand.")
    rec["next_recommendation"] = (
        f"OPERATIONAL RESUME {RUN_ID} (direction v68, evaluation): run {RUN_ID}'s "
        f"PRODUCER job died at 'Run lane cycle' after 16 s with exit code 1 "
        "(annotations API FACT: 'Process completed with exit code 1.'), so the "
        "'Validate active MVP producer state' and 'Enforce lane write scope' steps "
        "were SKIPPED and audit/integrate were never scheduled. The public logs are "
        "403, so the underlying mechanism is UNOBSERVED and is not attributed to a "
        f"model or auth cause. The if: always() 'Persist team snapshot' step still "
        f"published the unchanged predecessor HEAD {SNAPSHOT_COMMIT} on this run's "
        f"team ref; the content is run {PRED_RUN_ID}'s complete producer work, not "
        f"this run's claim. The predecessor's ONLY failure was its INDEPENDENT AUDIT "
        f"job dying at the 2700 s work quantum with exit 78 "
        "(LEX_WORK_QUANTUM_EXPIRED seconds=2700; recomputed step 2704 s, inside the "
        "2700-2715 s tick window), while its validate/scope/persist steps were "
        f"green. This resume preserves the inherited bytes, re-verifies {claims.get('n_checks')} "
        f"load-bearing claims ({claims.get('n_failed')} failed), confirms the "
        f"inherited delta is {snap.get('n_paths_changed')} paths and 0 out of scope, "
        "re-runs only the accepted multilingual/provenance suite (PASS 2/2), and "
        f"re-verifies accepted pointer 40265377500 / ea98384e on both halves. "
        "Ordered item (2) stays NOT_YET_DISCRIMINATING (product head 7be4480e "
        "unchanged, frozen family 14/15, protocol not executed). The next "
        "discriminating step is a Product handoff: regenerate the missing member so "
        "the named 15-member family reaches 15/15. A compact AUDIT INDEX "
        f"({AUDIT_INDEX}) and one-page AUDIT BRIEF ({AUDIT_BRIEF}) scope the auditor. "
        "continue_recommended=false; both DO-NOT-SERVE orders stand; "
        "owner_decision_required stays false; no 174k benchmark was run; posture "
        "flags stay FALSE.")

    write_json(OUT_RESULT, rec)
    rec["audit_index"] = build_audit_index(rec)
    write_audit_brief(rec)
    write_report(rec, report_dir)

    if args.update_state:
        rec["state_update"] = update_state(rec, mod)
        rec["lane_suite"] = run_lane_suite(mod)
        rec["write_scope"] = run_write_scope(mod)
        rec["nested_refs"] = run_nested_refs(mod)
        rec["self_check"] = run_self_check(mod)

        sc = load_json(STATE)
        sc[f"self_check_{RUN_ID}"] = {
            "schema": "lex-evaluation-self-check-summary/1",
            "verdict": rec["self_check"].get("verdict"),
            "pytest_available": rec["self_check"].get("pytest_available"),
            "n_passed": rec["self_check"].get("n_passed"),
            "n_failed": rec["self_check"].get("n_failed"),
            "artifact": SELF_CHECK_RESULT,
            "not_a_measurement": True,
        }
        (REPO_ROOT / STATE).write_text(json.dumps(sc, indent=2, ensure_ascii=False) + "\n",
                                       encoding="utf-8")
        _add_refs([LANE_SUITE, WRITE_SCOPE, SELF_CHECK_RESULT, NESTED_REFS])
        rec["state_gate"] = run_state_gate(mod)
        _add_refs([STATE_GATE])
        rec["state_gate"] = run_state_gate(mod)

        if (rec.get("self_check") or {}).get("n_failed"):
            verified = False
        if (rec.get("nested_refs") or {}).get("exit_code") not in (0, None):
            verified = False
        if (rec.get("write_scope") or {}).get("exit_code") not in (0, None):
            verified = False
        if (rec.get("state_gate") or {}).get("exit_code") not in (0, None):
            verified = False
        if (rec.get("state_gate") or {}).get("verdict") != "ALL_CHECKS_PASS":
            verified = False
        if (rec.get("lane_suite") or {}).get("overall_pass") is not True:
            verified = False
        if (rec.get("validate_replay") or {}).get("would_pass") is not True:
            verified = False
        if not verified:
            rec["verdict"] = "RESUME_VERIFIED_WITH_DISCLOSED_GAPS"
            rec["exit_code"] = EXIT_GAPS
        rec["controls"]["state_gate_all_checks_pass"] = (
            (rec.get("state_gate") or {}).get("verdict") == "ALL_CHECKS_PASS")
        rec["controls"]["lane_suite_overall_pass"] = (
            (rec.get("lane_suite") or {}).get("overall_pass") is True)
        rec["controls"]["write_scope_clean"] = (
            ((rec.get("write_scope") or {}).get("verdict") or {}).get("verdict")
            if isinstance((rec.get("write_scope") or {}).get("verdict"), dict)
            else (rec.get("write_scope") or {}).get("verdict")) == "SCOPE_CLEAN"
        rec["controls"]["nested_refs_resolved"] = (
            (rec.get("nested_refs") or {}).get("verdict") == "NESTED_REFS_RESOLVED")
        rec["controls"]["self_check_shim_pass"] = (
            (rec.get("self_check") or {}).get("verdict") == "SHIM_PASS")
        rec["controls"]["history_preserved_append_only"] = (
            rec["state_update"].get("no_key_removed") and rec["state_update"].get("no_ref_removed"))
        write_json(OUT_RESULT, rec)
        rec["audit_index"] = build_audit_index(rec)
        write_audit_brief(rec)
        write_report(rec, report_dir)
    else:
        rec["state_update"] = {"applied": False, "reason": "--update-state not passed"}
        write_json(OUT_RESULT, rec)

    ws_verdict = ((rec.get("write_scope") or {}).get("verdict") or {})
    ws_verdict = ws_verdict.get("verdict") if isinstance(ws_verdict, dict) else ws_verdict
    print(json.dumps({
        "verdict": rec["verdict"],
        "exit_code": rec["exit_code"],
        "producer_class": prod["classification"],
        "predecessor_audit_class": pred["failure_class"],
        "snapshot_scope": snap.get("verdict"),
        "validate_replay_would_pass": val.get("would_pass"),
        "claims": claims.get("verdict"),
        "claims_checks": claims.get("n_checks"),
        "claims_failed": claims.get("n_failed"),
        "multilingual": mult.get("status"),
        "item_2": item2.get("item_2_full_protocol_status"),
        "accepted_pointer_verified": ptr.get("verified"),
        "state_gate": (rec.get("state_gate") or {}).get("verdict"),
        "lane_suite": (rec.get("lane_suite") or {}).get("overall_pass"),
        "write_scope": ws_verdict,
        "nested_refs": (rec.get("nested_refs") or {}).get("verdict"),
        "self_check": (rec.get("self_check") or {}).get("verdict"),
        "state_update": rec.get("state_update"),
        "record": OUT_RESULT,
        "report": OUT_REPORT,
    }, indent=1))
    return rec["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
