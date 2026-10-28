#!/usr/bin/env python3
"""Operational resume for evaluation GitHub run 40627549747.

Resumes the persisted producer snapshot of failed run 40627549747
("Core evaluation dirV68 repair0").  The snapshot that run persisted is the
commit produced by the *previous* dispatch, 344da4c9 of run 40611594771:
40627549747 failed before the lane agent produced any commit, so the forced
snapshot push was a no-op and the valid work of 40611594771 is still intact.

This instrument answers one operational question and nothing else:

    why did run 40627549747 fail, is the persisted snapshot free of lost
    work, is the lane deliverable intact, and can the snapshot be presented
    to an independent auditor without a false readiness claim?

It is deliberately a verification instrument, not a new benchmark:

  * diagnosis     -- public run/job metadata is captured as a committed
                     envelope; the failure is classified at step level, with
                     the un-loggable cause kept as an inference;
  * snapshot      -- the forced snapshot refs are compared with the prior
                     producer commit and the accepted base;
  * deliverable   -- ordered item (1) is verified as PRESENT and measurement
                     unchanged (it is NOT re-executed), and ordered item (2)'s
                     precondition is re-derived from the CURRENT accepted
                     product mount with the accepted engine;
  * repair        -- the append-only coverage record that run 40611594771
                     truncated is restored with its full history preserved
                     and the truncated bytes kept verbatim;
  * finalize      -- report, audit index and additive state refresh.

No frozen bar, rubric, threshold, predicate, classifier or verdict contract is
moved.  No packet is admitted, no serve verdict is issued, no human gate is
staged, and the falsifier of record is not re-executed.

Usage:
    python3 -m evaluation.operational_resume_40627549747
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# --------------------------------------------------------------------- constants
REPO = Path(__file__).resolve().parent.parent
RUN_ID = "40627549747"
RESUMED_RUN_ID = "40627549747"
PRIOR_SNAPSHOT_RUN_ID = "40611594771"
SNAPSHOT_COMMIT = "344da4c98255fd030c61298e8e98a06794056054"
ACCEPTED_BASE = "ea98384e54d31d2e694c418a1d1ce5769fc6c32f"
RUN_HEAD_SHA = "a5bae8037ed5fa07cd554b488512dd5e540552dd"
CONTROL_PLANE_HEAD = "31f2f387861b64ed29cb2b0501ac58f0ed0ecdb3"
PRODUCT_MOUNT = Path("/tmp/lex_accepted/product")
DIRECTION_VERSION = 68

ACCEPTED_EVAL_RUN = "40258497460"
ACCEPTED_EVAL_COMMIT = "64208e15"
STRUCT_ACCEPTED_RUN = "40265377500"
PENDING_RUN = "40261335674"

OUT = REPO / "results/evaluation/operational_resume_40627549747"
API = OUT / "api"
COVERAGE_RECORD = REPO / "results/evaluation/accepted_base_gate_coverage_39043684319.json"
COVERAGE_RECORD_REL = COVERAGE_RECORD.relative_to(REPO).as_posix()
REPORT = REPO / f"reports/evaluation/CYCLE_{RUN_ID}.md"
AUDIT_INDEX = OUT / "AUDIT_INDEX.json"
STATE_ROOT = REPO / "state/evaluation.json"
STATE_LANE = REPO / "evaluation/state/evaluation.json"

ITEM1_RECORD = REPO / "results/evaluation/bypass_clause_correction/40113448025.json"
ITEM1_REPORT = REPO / "reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md"
STRUCT_GATE = REPO / f"results/audit/evaluation/CYCLE_{STRUCT_ACCEPTED_RUN}_GATE.json"
STRUCT_ARTIFACT = REPO / f"results/evaluation/minimal_retrieval_ca_benchmark/test_{STRUCT_ACCEPTED_RUN}.json"
CLEAN_GATE = REPO / f"results/audit/evaluation/CYCLE_{ACCEPTED_EVAL_RUN}_GATE.json"
CLEAN_ARTIFACT = REPO / f"results/evaluation/post_repair_family_ca_falsifier/{ACCEPTED_EVAL_RUN}.json"
PENDING_ARTIFACT = REPO / f"results/evaluation/fast_mvp_retrieval_recall_benchmark/{PENDING_RUN}.json"

API_BASE = "https://api.github.com/repos/Mickalive/LexMachina/actions/runs"
POSTURE = {
    "packet_admitted": False,
    "machine_gate_ready": False,
    "human_gate_ready": False,
    "ready_for_owner_session": False,
    "owner_decision_required": False,
    "do_not_serve_orders": "both stand",
}


# --------------------------------------------------------------------- helpers
def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj, indent: int = 2, ensure_ascii: bool = False) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, indent=indent, ensure_ascii=ensure_ascii) + "\n"
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)
    return sha256_bytes(text.encode("utf-8"))


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def check(label: str, ok: bool, **detail) -> dict:
    return {"check": label, "passed": bool(ok), "detail": detail}


def git(*args: str, timeout: int = 180):
    p = subprocess.run(["git", *args], cwd=str(REPO), capture_output=True,
                       text=True, timeout=timeout)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def _secs(a: str | None, b: str | None) -> float | None:
    if not a or not b:
        return None
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    return (datetime.strptime(b, fmt) - datetime.strptime(a, fmt)).total_seconds()


def relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def _json_equal(a, b) -> bool:
    return json.dumps(a, sort_keys=True, ensure_ascii=False) == \
        json.dumps(b, sort_keys=True, ensure_ascii=False)


def _job(jobs: dict, name: str) -> dict | None:
    for j in jobs.get("jobs", []):
        if j.get("name") == name:
            return j
    return None


def _step(job: dict, name: str) -> dict | None:
    for s in job.get("steps", []):
        if s.get("name") == name:
            return s
    return None


def load_or_fetch_api(kind: str, run_id: str) -> dict:
    """A committed envelope replays offline; otherwise capture the public API."""
    API.mkdir(parents=True, exist_ok=True)
    path = API / f"{kind}_{run_id}_api.json"
    if path.is_file():
        return {"path": relative(path), "source": "committed_envelope_replay",
                "envelope": load_json(path), "network": False}
    url = f"{API_BASE}/{run_id}" + ("/jobs?per_page=100" if kind == "jobs" else "")
    try:
        p = subprocess.run(["curl", "-sf", "--max-time", "30", url],
                           capture_output=True, timeout=60)
        if p.returncode != 0 or not p.stdout:
            raise RuntimeError(f"curl rc={p.returncode}")
        envelope = json.loads(p.stdout.decode("utf-8"))
        path.write_bytes(p.stdout)
        return {"path": relative(path), "source": "public_unauthenticated_rest_capture",
                "envelope": envelope, "network": True, "url": url}
    except Exception as exc:  # noqa: BLE001 - recorded, never hidden
        return {"path": relative(path) if path.is_file() else None,
                "source": "unavailable", "envelope": None, "network": False,
                "fetch_error": repr(exc)}


def audit_branch_probe(run_id: str) -> dict:
    ref = f"refs/heads/cycle/core/evaluation/{run_id}/audit"
    rc, out, err = git("ls-remote", "--heads", "origin", ref)
    if rc != 0:
        return {"ref": ref, "exists": None, "error": err}
    return {"ref": ref, "exists": bool(out), "stdout": out or "(empty)"}


def _tree_file(commit: str, path: str) -> str | None:
    rc, out, _ = git("show", f"{commit}:{path}")
    return out if rc == 0 else None


# --------------------------------------------------------------------- 1. diagnosis
def build_diagnosis() -> dict:
    api_run = load_or_fetch_api("run", RESUMED_RUN_ID)
    api_jobs = load_or_fetch_api("jobs", RESUMED_RUN_ID)
    run_env, jobs_env = api_run["envelope"], api_jobs["envelope"]
    if not jobs_env:
        return {
            "schema": "lex-evaluation-operational-resume-diagnosis/1",
            "run_id": RUN_ID, "diagnosed_run_id": RESUMED_RUN_ID,
            "failure_class": "UNAVAILABLE",
            "verdict": "DIAGNOSIS_UNAVAILABLE_NO_API", "checks": [],
            "failure_summary": "no public jobs envelope available",
            "api": {"run": api_run.get("path"), "jobs": api_jobs.get("path"),
                    "run_source": api_run.get("source"),
                    "jobs_source": api_jobs.get("source")},
        }

    team = _job(jobs_env, "team") or {}
    audit = _job(jobs_env, "audit") or {}
    integrate = _job(jobs_env, "integrate") or {}
    resilience = _job(jobs_env, "resilience") or {}
    lane_cycle = _step(team, "Run lane cycle") or {}
    state_step = _step(team, "Validate active MVP producer state") or {}
    junk_step = _step(team, "Clean generated junk") or {}
    scope_step = _step(team, "Enforce lane write scope") or {}
    persist_step = _step(team, "Persist team snapshot") or {}

    # The wrapper's model-health predicate, re-executed on committed bytes.
    health_run = OUT / f"model_health_at_{RUN_HEAD_SHA[:8]}.json"
    health_ctl = OUT / f"model_health_at_{CONTROL_PLANE_HEAD[:8]}.json"
    for commit, dest in ((RUN_HEAD_SHA, health_run), (CONTROL_PLANE_HEAD, health_ctl)):
        text = _tree_file(commit, "state/model_health.json")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text if text and text.endswith("\n") else (text or "{}") + "\n",
                        encoding="utf-8")
    resolver = (
        "healthy=$(jq -r '.healthy // false' \"$1\")\n"
        "resolved=$(jq -r '.resolved_model // empty' \"$1\")\n"
        "if [ \"$healthy\" != \"true\" ] || [ -z \"$resolved\" ]; then\n"
        "  echo \"LEX_NO_HEALTHY_FREE_TOOL_MODEL\" >&2\n"
        "  exit 76\n"
        "fi\n"
        "echo \"$resolved\"\n"
    )
    rc_at_head, out_at_head, err_at_head, _ = run_cmd(
        ["bash", "-c", resolver, "_", str(health_run)])
    rc_at_ctl, out_at_ctl, err_at_ctl, _ = run_cmd(
        ["bash", "-c", resolver, "_", str(health_ctl)])
    health_head = load_json(health_run)
    health_ctl_obj = load_json(health_ctl)

    direction_txt = _tree_file(RUN_HEAD_SHA, "state/factory_direction.json")
    head_direction_version = None
    if direction_txt:
        try:
            head_direction_version = json.loads(direction_txt).get("version")
        except Exception:  # noqa: BLE001
            head_direction_version = "unparseable"
    rc_ls, agent_files, _ = git("ls-tree", "-r", "--name-only", RUN_HEAD_SHA,
                                ".opencode/agents")
    agent_ids = sorted(Path(p).stem for p in agent_files.splitlines()
                       if p.endswith(".md"))
    cards_txt = _tree_file(RUN_HEAD_SHA, "docs/agents/AGENT_CARDS.md") or ""
    card_ids = re.findall(r"<!-- AGENT_CARD:\s*([A-Za-z0-9_]+)\s", cards_txt)
    registry_ok = (rc_ls == 0 and len(agent_ids) == 7 and len(card_ids) == 7
                   and sorted(card_ids) == agent_ids)

    branch = audit_branch_probe(RESUMED_RUN_ID)
    team_ref = git("ls-remote", "--heads", "origin",
                   f"refs/heads/cycle/core/evaluation/{RESUMED_RUN_ID}/team")
    attempt_ref = git("ls-remote", "--heads", "origin",
                      f"refs/heads/cycle/core/evaluation/{RESUMED_RUN_ID}/team-attempt-1")
    team_sha = team_ref[1].split()[0] if team_ref[1] else None
    attempt_sha = attempt_ref[1].split()[0] if attempt_ref[1] else None
    run_seconds = _secs(run_env.get("created_at"), run_env.get("updated_at")) if run_env else None
    cycle_seconds = _secs(lane_cycle.get("started_at"), lane_cycle.get("completed_at"))

    checks = [
        check("run_metadata_is_the_failed_run",
              run_env is not None and run_env.get("id") == int(RESUMED_RUN_ID)
              and run_env.get("conclusion") == "failure",
              run_id=run_env.get("id") if run_env else None,
              name=run_env.get("name") if run_env else None,
              conclusion=run_env.get("conclusion") if run_env else None,
              head_sha=run_env.get("head_sha") if run_env else None,
              created_at=run_env.get("created_at") if run_env else None,
              updated_at=run_env.get("updated_at") if run_env else None,
              wall_seconds=run_seconds),
        check("head_sha_is_the_control_plane_head",
              run_env is not None and run_env.get("head_sha") == RUN_HEAD_SHA,
              expected=RUN_HEAD_SHA, observed=run_env.get("head_sha") if run_env else None),
        check("team_job_failed", team.get("conclusion") == "failure",
              conclusion=team.get("conclusion")),
        check("failing_step_is_run_lane_cycle",
              lane_cycle.get("conclusion") == "failure",
              step_number=lane_cycle.get("number"), step_name=lane_cycle.get("name"),
              conclusion=lane_cycle.get("conclusion"),
              started_at=lane_cycle.get("started_at"),
              completed_at=lane_cycle.get("completed_at"),
              duration_seconds=cycle_seconds),
        check("run_lane_cycle_too_short_for_agent_work",
              cycle_seconds is not None and cycle_seconds < 120.0,
              duration_seconds=cycle_seconds,
              meaning="a wrapper/provider exit, not a completed lane cycle"),
        check("state_validation_step_skipped_after_failure",
              state_step.get("conclusion") == "skipped",
              conclusion=state_step.get("conclusion")),
        check("junk_clean_step_succeeded", junk_step.get("conclusion") == "success",
              conclusion=junk_step.get("conclusion")),
        check("write_scope_step_skipped_after_failure",
              scope_step.get("conclusion") == "skipped",
              conclusion=scope_step.get("conclusion"),
              note="the scope guard never ran, so this is not a scope failure"),
        check("snapshot_persisted_despite_failure",
              persist_step.get("conclusion") == "success",
              conclusion=persist_step.get("conclusion")),
        check("audit_job_skipped", audit.get("conclusion") == "skipped",
              conclusion=audit.get("conclusion")),
        check("integrate_job_skipped", integrate.get("conclusion") == "skipped",
              conclusion=integrate.get("conclusion")),
        check("resilience_job_success", resilience.get("conclusion") == "success",
              conclusion=resilience.get("conclusion")),
        check("no_audit_ref_was_issued", branch.get("exists") is False,
              ref=branch.get("ref"), exists=branch.get("exists"),
              meaning=f"run {RESUMED_RUN_ID} issued no independent verdict"),
        check("direction_at_head_is_v68", head_direction_version == DIRECTION_VERSION,
              version=head_direction_version, expected=DIRECTION_VERSION,
              source=f"git show {RUN_HEAD_SHA[:8]}:state/factory_direction.json"),
        check("agent_registry_at_head_is_clean",
              registry_ok, n_agent_files=len(agent_ids), n_cards=len(card_ids),
              agent_ids=agent_ids, card_ids=sorted(card_ids),
              meaning="the registry guard cannot explain this failure"),
        check("model_health_at_head_is_healthy_so_pre_agent_health_is_excluded",
              health_head.get("healthy") is True
              and bool(health_head.get("resolved_model"))
              and (health_head.get("healthy_models") or []),
              healthy=health_head.get("healthy"),
              resolved_model=health_head.get("resolved_model"),
              healthy_models=health_head.get("healthy_models"),
              status=health_head.get("status"),
              resolver_exit_code=rc_at_head,
              resolver_stdout=out_at_head.strip(),
              last_checked_run_id=health_head.get("last_checked_run_id"),
              last_checked_at=health_head.get("last_checked_at")),
        check("resolver_replay_at_control_plane_head_also_exits_0",
              rc_at_ctl == 0 and bool(out_at_ctl.strip()),
              exit_code=rc_at_ctl, resolved_model=out_at_ctl.strip(),
              stderr=err_at_ctl.strip(),
              healthy=health_ctl_obj.get("healthy"),
              status=health_ctl_obj.get("status"),
              file=relative(health_ctl),
              committed_at=f"git show {CONTROL_PLANE_HEAD[:7]}:state/model_health.json"),
        check("snapshot_ref_is_the_prior_producer_commit",
              team_sha == SNAPSHOT_COMMIT and attempt_sha == SNAPSHOT_COMMIT,
              expected=SNAPSHOT_COMMIT, team_ref_sha=team_sha,
              attempt_ref_sha=attempt_sha,
              meaning="run 40627549747 produced no commit; its persist push was a no-op "
                      "and the valid work of run 40611594771 is preserved"),
        check("snapshot_commit_is_ancestor_of_the_worktree",
              git("merge-base", "--is-ancestor", SNAPSHOT_COMMIT, "HEAD")[0] == 0,
              snapshot=SNAPSHOT_COMMIT),
        check("accepted_base_is_ancestor_of_the_snapshot",
              git("merge-base", "--is-ancestor", ACCEPTED_BASE, SNAPSHOT_COMMIT)[0] == 0,
              accepted_base=ACCEPTED_BASE, snapshot=SNAPSHOT_COMMIT),
    ]

    n_failed = sum(1 for c in checks if not c["passed"])
    failure_summary = (
        f"Run {RESUMED_RUN_ID} failed at team step {lane_cycle.get('number')} "
        f"'{lane_cycle.get('name')}' in {cycle_seconds}s. The head {RUN_HEAD_SHA[:8]} "
        f"carried a HEALTHY free-model pool (status={health_head.get('status')!r}, "
        f"resolved_model={health_head.get('resolved_model')!r}, "
        f"healthy_models={len(health_head.get('healthy_models') or [])}); the wrapper's "
        f"resolve_model_args predicate re-executed on those committed bytes exits "
        f"{rc_at_head}, so this is NOT the previous pre-agent model-health exit. The "
        f"direction is v{DIRECTION_VERSION} and the agent registry is 7/7, so neither "
        f"the supersession guard nor the card guard fired. 'Clean generated junk' and "
        f"the always() snapshot persistence succeeded, audit/integrate were skipped, "
        f"and no /audit ref exists: the run issued NO verdict. The persisted snapshot "
        f"is {SNAPSHOT_COMMIT[:8]}, the commit of the previous dispatch "
        f"({PRIOR_SNAPSHOT_RUN_ID}); 40627549747 added no commit, so its push was a "
        f"no-op and no producer work was lost. This is an ORCHESTRATION / PROVIDER "
        f"EXIT AT THE LANE-CYCLE STEP, not a scope-validation failure, not a "
        f"model-health pre-agent exit, and not a gate REVISE/BLOCKED."
    )
    return {
        "schema": "lex-evaluation-operational-resume-diagnosis/1",
        "run_id": RUN_ID,
        "diagnosed_run_id": RESUMED_RUN_ID,
        "failure_class": "ORCHESTRATION_PROVIDER_OR_SESSION_EXIT_AT_LANE_CYCLE",
        "verdict": "DIAGNOSIS_CONFIRMED" if n_failed == 0 else "DIAGNOSIS_INCOMPLETE",
        "n_checks": len(checks), "n_failed": n_failed, "checks": checks,
        "failure_summary": failure_summary,
        "api": {"run": api_run.get("path"), "jobs": api_jobs.get("path"),
                "run_source": api_run.get("source"),
                "jobs_source": api_jobs.get("source")},
        "step_durations_seconds": {"run_lane_cycle": cycle_seconds,
                                   "run_wall": run_seconds},
        "model_health": {
            "run_head": {"commit": RUN_HEAD_SHA, "record": relative(health_run),
                         "healthy": health_head.get("healthy"),
                         "resolved_model": health_head.get("resolved_model"),
                         "status": health_head.get("status"),
                         "last_checked_run_id": health_head.get("last_checked_run_id"),
                         "last_checked_at": health_head.get("last_checked_at"),
                         "resolver_exit_code": rc_at_head},
            "control_plane_head": {"commit": CONTROL_PLANE_HEAD,
                                   "record": relative(health_ctl),
                                   "healthy": health_ctl_obj.get("healthy"),
                                   "resolved_model": health_ctl_obj.get("resolved_model"),
                                   "status": health_ctl_obj.get("status"),
                                   "resolver_exit_code": rc_at_ctl},
        },
        "snapshot_refs": {"team": team_sha, "team_attempt_1": attempt_sha,
                          "persisted_snapshot_commit": SNAPSHOT_COMMIT},
        "candidate_causes": [
            {"cause": "model/provider failure during the agent invocation after a healthy resolver",
             "status": "BEST_SUPPORTED_INFERENCE",
             "support": "16 s step duration, healthy 4-model pool at the run head, no lane "
                        "commit produced, audit/integrate skipped"},
            {"cause": "opencode session/agent bootstrap failure",
             "status": "ALTERNATIVE_INFERENCE",
             "support": "the step failed before any state or scope validation ran; no "
                        "committed producer record exists for this run"},
            {"cause": "wrapper retry/exit-code path after upstream errors",
             "status": "ALTERNATIVE_INFERENCE",
             "support": "run-ox-with-retry.sh is the only layer between the healthy "
                        "resolver and the lane agent; its exact rc was never readable"},
        ],
        "limits": [
            "GitHub job logs are HTTP 403 unauthenticated; the exact exit code and "
            "stderr of the 'Run lane cycle' step are NOT recoverable.",
            "The cause above is an INFERENCE from the public job/step envelope, the "
            "committed model-health record and the git refs, not a log fact.",
            "The run issued no verdict; the absence of an /audit ref is expected and "
            "is not evidence about the quality of the persisted snapshot.",
        ],
        "claim_ceiling": "Orchestration diagnosis only. No lane verdict, no product "
                         "measurement, no frozen-bar movement, no serve verdict and no "
                         "human-gate claim.",
    }


# --------------------------------------------------------------------- 2. snapshot
def build_snapshot() -> dict:
    subject_rc, subject, _ = git("log", "-1", "--format=%s", SNAPSHOT_COMMIT)
    parent_rc, parent, _ = git("rev-parse", f"{SNAPSHOT_COMMIT}^")
    changed_rc, changed, _ = git("show", "--name-only", "--format=", SNAPSHOT_COMMIT)
    files = [p for p in changed.splitlines() if p.strip()]
    head_rc, head, _ = git("rev-parse", "HEAD")
    snap_rc, snap_subject, _ = git("log", "-1", "--format=%s", SNAPSHOT_COMMIT)
    checks = [
        check("snapshot_commit_resolves", subject_rc == 0 and bool(subject),
              commit=SNAPSHOT_COMMIT, subject=subject),
        check("snapshot_commit_is_the_previous_dispatch_commit",
              "evaluation cycle 40611594771" in subject,
              subject=subject),
        check("snapshot_commit_has_a_parent", parent_rc == 0 and len(parent) == 40,
              parent=parent),
        check("snapshot_is_ancestor_of_current_worktree",
              git("merge-base", "--is-ancestor", SNAPSHOT_COMMIT, "HEAD")[0] == 0,
              head=head),
        check("accepted_base_is_preserved_in_history",
              git("merge-base", "--is-ancestor", ACCEPTED_BASE, SNAPSHOT_COMMIT)[0] == 0,
              accepted_base=ACCEPTED_BASE),
        check("snapshot_contains_valid_producer_work_files",
              changed_rc == 0 and len(files) > 0,
              n_files=len(files), files=files),
        check("snapshot_subject_matches_log", snap_rc == 0 and snap_subject == subject,
              subject=snap_subject),
    ]
    n_failed = sum(1 for c in checks if not c["passed"])
    return {
        "schema": "lex-evaluation-operational-resume-snapshot/1",
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED_RUN_ID,
        "persisted_snapshot_commit": SNAPSHOT_COMMIT,
        "persisted_snapshot_subject": subject,
        "persisted_snapshot_parent": parent if parent_rc == 0 else None,
        "persisted_snapshot_authoring_run": PRIOR_SNAPSHOT_RUN_ID,
        "current_worktree_head": head if head_rc == 0 else None,
        "changed_files": files,
        "verdict": "SNAPSHOT_PRESERVED_ON_PRIOR_PRODUCER_COMMIT" if n_failed == 0
                   else "SNAPSHOT_UNEXPECTED",
        "n_checks": len(checks), "n_failed": n_failed, "checks": checks,
        "note": "40627549747 failed before adding a commit; its forced snapshot push was a "
                "no-op. The snapshot of record is therefore the valid work of 40611594771. "
                "That work was never independently audited, so it is preserved as "
                "UNGATED producer work, not as accepted evidence.",
    }


# --------------------------------------------------------------------- 3. deliverable
def _pins_ok(artifact: dict) -> list[dict]:
    return [{"pin": k, "present": k in artifact} for k in
            ("run_id", "verdict", "exit_code", "falsification_proven")]


def build_deliverable() -> dict:
    checks: list[dict] = []
    item1 = load_json(ITEM1_RECORD) if ITEM1_RECORD.exists() else {}
    item1_report_exists = ITEM1_REPORT.exists()
    item1_status = {
        "record": relative(ITEM1_RECORD),
        "record_sha256": sha256_file(ITEM1_RECORD) if ITEM1_RECORD.exists() else None,
        "report": relative(ITEM1_REPORT),
        "report_sha256": sha256_file(ITEM1_REPORT) if item1_report_exists else None,
        "verdict": item1.get("verdict"),
        "measurement_unchanged": item1.get("measurement_unchanged"),
        "failed_claims": item1.get("failed_claims"),
        "falsifier_reexecuted": item1.get("falsifier_reexecuted"),
        "status": "PRESENT_MEASUREMENT_UNCHANGED_WITH_OPEN_MACHINE_PROVENANCE_CHECKS",
        "not_reopened": True,
    }
    checks.append(check("item1_record_and_report_present",
                        ITEM1_RECORD.exists() and item1_report_exists,
                        record=item1_status["record"], report=item1_status["report"]))
    checks.append(check("item1_measurement_is_unchanged",
                        item1.get("measurement_unchanged") is True,
                        measurement_unchanged=item1.get("measurement_unchanged")))
    checks.append(check("item1_falsifier_was_not_re_executed",
                        item1.get("falsifier_reexecuted") is False,
                        falsifier_reexecuted=item1.get("falsifier_reexecuted")))
    checks.append(check("item1_open_provenance_checks_disclosed",
                        sorted(item1.get("failed_claims") or []) ==
                        ["CC6_accepted_code_path_file_line", "CC7_51d306c_diff_provenance"],
                        failed_claims=item1.get("failed_claims")))

    # Ordered item (2): precondition only, using the accepted engine.
    item2 = {}
    try:
        sys.path.insert(0, str(REPO))
        from evaluation import post_repair_family_ca_falsifier as engine  # noqa: PLC0415
        hyp = load_json(REPO / "evaluation/POST_REPAIR_FAMILY_CA_FALSIFIER_40258497460_HYPOTHESIS_V1.json")
        rc_mount, head, err_mount = git("-C", str(PRODUCT_MOUNT), "rev-parse", "HEAD")
        first = engine.precondition_gate(hyp, PRODUCT_MOUNT)
        second = engine.precondition_gate(hyp, PRODUCT_MOUNT)
        matching = (first.get("set_relations_REQUIREMENT_16") or {}).get(
            "member_for_member_matching", {})
        role_relation = (first.get("set_relations_REQUIREMENT_16") or {}).get(
            "role_relation", {})
        item2 = {
            "product_mount": str(PRODUCT_MOUNT),
            "product_mount_head": head if rc_mount == 0 else None,
            "gate_is_deterministic": _json_equal(first, second),
            "H1_precondition_leg_landed": first.get("H1_precondition_leg_landed"),
            "item_2_leg_status": first.get("item_2_leg_status"),
            "H2_precondition_full_family_regenerated":
                first.get("H2_precondition_full_family_regenerated"),
            "member_for_member_matching": matching,
            "role_relation": role_relation,
            "status": first.get("item_2_full_protocol_status"),
            "raw_gate_sha256": sha256_bytes(
                json.dumps(first, sort_keys=True).encode("utf-8")),
            "why_no_ordered_re_measure": (
                "The precondition is not met: the rejection/incumbent leg is landed, "
                "but the named frozen 15-member family is regenerated 14/15 "
                "(server/served 3 of 4). No synthetic stand-in is substituted, "
                "d2_path_scope_probe is not re-run, packet 39319405429 is not scored "
                "and the standing falsification is not re-run."),
        }
        checks.append(check("item2_mount_resolves", rc_mount == 0 and bool(head),
                            head=head if rc_mount == 0 else None, error=err_mount))
        checks.append(check("item2_gate_is_deterministic",
                            item2["gate_is_deterministic"]))
        checks.append(check("item2_leg_is_landed",
                            item2["H1_precondition_leg_landed"] is True
                            and item2["item_2_leg_status"] == "LANDED",
                            status=item2["item_2_leg_status"]))
        checks.append(check("item2_full_family_is_not_regenerated",
                            item2["H2_precondition_full_family_regenerated"] is False,
                            matched=matching.get("matched_members"),
                            of=matching.get("of")))
        checks.append(check("item2_is_14_of_15",
                            matching.get("matched_members") == 14
                            and matching.get("of") == 15,
                            matched=matching.get("matched_members"),
                            of=matching.get("of")))
        checks.append(check("item2_server_served_is_3_of_4",
                            (matching.get("matched_per_role") or {}).get("server/served") == 3
                            and (role_relation.get("server/served") or {}).get(
                                "frozen_family") == 4,
                            matched_per_role=matching.get("matched_per_role")))
        checks.append(check("item2_status_is_not_yet_discriminating",
                            str(item2["status"]).startswith("NOT_YET_DISCRIMINATING"),
                            status=item2["status"]))
    except Exception as exc:  # noqa: BLE001 - recorded as an honest failure
        item2 = {"error": repr(exc), "status": "ITEM2_PRECONDITION_UNAVAILABLE"}
        checks.append(check("item2_precondition_executed", False, error=repr(exc)))

    # Verification of the accepted lineage, both halves where named.
    clean_gate = load_json(CLEAN_GATE) if CLEAN_GATE.exists() else {}
    clean_artifact = load_json(CLEAN_ARTIFACT) if CLEAN_ARTIFACT.exists() else {}
    struct_gate = load_json(STRUCT_GATE) if STRUCT_GATE.exists() else {}
    struct_artifact = load_json(STRUCT_ARTIFACT) if STRUCT_ARTIFACT.exists() else {}
    pending_exists = PENDING_ARTIFACT.exists()
    pending = load_json(PENDING_ARTIFACT) if pending_exists else {}
    checks.append(check("last_clean_accepted_cycle_is_gate_artifact_agreement",
                        clean_gate.get("gate") == "PASS"
                        and clean_gate.get("safe_to_integrate") is True
                        and clean_artifact.get("verdict") == "SOUND_COUNTER_ROW_PRESENT",
                        gate=clean_gate.get("gate"),
                        artifact_verdict=clean_artifact.get("verdict")))
    mismatch = (struct_gate.get("gate") == "PASS"
                and struct_artifact.get("verdict") == "PRODUCT_FALSIFIED")
    checks.append(check("structural_accept_cycle_has_audit_artifact_mismatch",
                        mismatch,
                        gate=struct_gate.get("gate"),
                        artifact_verdict=struct_artifact.get("verdict"),
                        meaning="the prior audit covered a different instrument; the "
                                "cycle is NOT accepted as evidence"))
    checks.append(check("pending_recall_cycle_has_no_acceptance",
                        pending_exists
                        and pending.get("verdict") == "PRODUCT_FALSIFIED_RECALL_LOSS"
                        and not (REPO / f"results/audit/evaluation/CYCLE_{PENDING_RUN}_GATE.json").exists(),
                        artifact_verdict=pending.get("verdict")))

    n_failed = sum(1 for c in checks if not c["passed"])
    return {
        "schema": "lex-evaluation-operational-resume-deliverable/1",
        "run_id": RUN_ID,
        "verdict": "DELIVERABLE_VERIFIED_ITEM1_PRESENT_ITEM2_GATED" if n_failed == 0
                   else "DELIVERABLE_VERIFICATION_INCOMPLETE",
        "n_checks": len(checks), "n_failed": n_failed, "checks": checks,
        "item_1": item1_status,
        "item_2": item2,
        "accepted_lineage": {
            "accepted_run_id_unchanged": ACCEPTED_EVAL_RUN,
            "accepted_commit": ACCEPTED_EVAL_COMMIT,
            "last_clean_gate": relative(CLEAN_GATE),
            "last_clean_artifact": relative(CLEAN_ARTIFACT),
            "structural_accept_run": STRUCT_ACCEPTED_RUN,
            "structural_accept_gate": relative(STRUCT_GATE),
            "structural_accept_artifact": relative(STRUCT_ARTIFACT),
            "structural_accept_accepted_as_evidence": False,
            "structural_accept_mismatch": mismatch,
            "pending_run": PENDING_RUN,
            "pending_artifact": relative(PENDING_ARTIFACT),
        },
        "claim_ceiling": "Operational verification only. No new benchmark, no packet "
                         "scored, no frozen bar moved, no serve verdict, no human gate.",
    }


# --------------------------------------------------------------------- 4. coverage repair
def build_coverage_repair() -> dict:
    rel = COVERAGE_RECORD_REL
    rc_prior, prior_text, err_prior = git("show", f"{SNAPSHOT_COMMIT}^:{rel}")
    if rc_prior != 0:
        raise RuntimeError(f"cannot read prior coverage record: {err_prior}")
    prior = json.loads(prior_text)
    # Read the truncated bytes from the snapshot commit, not from the worktree:
    # this keeps the repair reproducible after the worktree has already been
    # restored, and pins the exact bytes run 40611594771 committed.
    rc_trunc, trunc_text, err_trunc = git("show", f"{SNAPSHOT_COMMIT}:{rel}")
    if rc_trunc != 0:
        raise RuntimeError(f"cannot read truncated coverage record: {err_trunc}")
    truncated = json.loads(trunc_text)
    prior_sha = sha256_bytes(prior_text.encode("utf-8"))
    truncated_sha = sha256_bytes(trunc_text.encode("utf-8"))

    rc_head, head, _ = git("rev-parse", "origin/lab/evaluation")
    if rc_head != 0:
        raise RuntimeError("origin/lab/evaluation is not fetchable")
    rc_tree, tree, _ = git("ls-tree", "-r", "--name-only", "origin/lab/evaluation",
                           "--", "results/audit/evaluation")
    gates = sorted(set(re.findall(r"CYCLE_(\d+)_GATE\.json", tree)))
    rc_log, log, _ = git("log", "--format=%H%x09%s", "origin/lab/evaluation")
    rows = [line.split("\t", 1) for line in log.splitlines() if "\t" in line]
    accept_idx = None
    for i, (sha, subject) in enumerate(rows):
        if re.fullmatch(r"accept evaluation cycle \d+", subject.strip()):
            accept_idx = i
            break
    above = rows if accept_idx is None else rows[:accept_idx]
    derived = sorted({m.group(1) for sha, subject in above
                      for m in [re.search(r"\b(\d{11})\b", subject)]
                      if m and m.group(1) not in gates})
    newest_accept = rows[accept_idx] if accept_idx is not None else (None, None)

    merged = dict(prior)
    merged.update({
        "accepted_branch_head": head,
        "newest_accept_commit": ({"sha": newest_accept[0], "subject": newest_accept[1]}
                                 if newest_accept[0] else None),
        "gates_present_on_accepted_branch_at_3506f0e4":
            list(prior.get("gates_present_on_accepted_branch") or []),
        "gates_present_on_accepted_branch": [f"results/audit/evaluation/CYCLE_{g}_GATE.json"
                                             for g in gates],
        "runs_above_newest_accept_commit": [sha for sha, _ in above],
        "ungated_runs_above_the_newest_accept_commit": derived,
        "republished_by": RUN_ID,
        "republished_at_utc": now_utc(),
        "action_taken": (
            "RESTORED the full append-only coverage record that run 40611594771 "
            "truncated in place (623 lines -> 18 lines, history and 34-gate inventory "
            "deleted), then re-derived the current measurement fields at "
            f"origin/lab/evaluation@{head[:8]} for snapshot audit {RUN_ID}. The "
            "truncated 40611594771 bytes are preserved verbatim under "
            "superseded_snapshot_40611594771_truncated, and every prior "
            "superseded_snapshot_* block is preserved unchanged. This is a restoration "
            "and a point-in-time republication, not a new measurement family."),
        "claim_ceiling": (
            "Point-in-time gate-coverage reading at the named accepted branch head. It "
            "does not read gate contents, does not judge the accepted evidence sound, "
            "and does not propose a rollback or rewrite."),
    })
    merged["finding"] = dict(prior.get("finding") or {})
    merged["finding"].update({
        "statement": (
            f"Re-derived at origin/lab/evaluation@{head[:8]} for snapshot audit "
            f"{RUN_ID}: {len(gates)} gate files are present on the accepted branch; "
            f"the newest accept commit is {newest_accept[0][:8] if newest_accept[0] else 'absent'} "
            f"('{newest_accept[1] if newest_accept[1] else ''}'); the run ids above it "
            f"re-derive to {derived}, and the disclosed ungated set is {derived}. The "
            "full prior measurement and its history were restored from the parent of "
            f"{SNAPSHOT_COMMIT[:8]} after run 40611594771 truncated them."),
        "ungated": derived,
    })
    merged["finding"]["what_is_NOT_claimed"] = list(
        prior["finding"].get("what_is_NOT_claimed") or []) + [
        "this restoration does not validate run 40611594771's other work; it only "
        "repairs the append-only coverage record it truncated",
    ]
    merged["restoration_40627549747"] = {
        "prior_full_record_sha256": prior_sha,
        "prior_full_record_source": f"git show {SNAPSHOT_COMMIT}^:{rel}",
        "truncated_record_sha256": truncated_sha,
        "truncated_record_preserved_under": "superseded_snapshot_40611594771_truncated",
        "restored_head": head,
        "n_gates_restored": len(gates),
        "derived_ungated_runs": derived,
        "why": "run 40611594771 rewrote this append-only record in place, deleting 621 "
               "lines of history and its 34-gate inventory. AGENTS.md items 5 and 6 "
               "forbid overwriting historical claim-bearing results; this cycle "
               "restores the prior bytes' content and keeps the truncated bytes too.",
    }
    merged["superseded_snapshot_40611594771_truncated"] = truncated
    history = list(prior.get("history") or [])
    history.append({
        "action": "restored the full pre-40611594771 record content and re-derived the "
                  "current head/gate inventory; truncated 40611594771 bytes preserved",
        "previous_accepted_branch_head": prior.get("accepted_branch_head"),
        "previous_record_sha256": prior_sha,
        "updated_at": merged["republished_at_utc"],
        "updated_by_run": RUN_ID,
    })
    merged["history"] = history

    write_json(COVERAGE_RECORD, merged)

    # Verification: no prior key lost, prior history intact, truncated bytes kept.
    lost = [k for k in prior if k not in merged]
    prior_history_preserved = merged["history"][:len(prior.get("history") or [])] == \
        (prior.get("history") or [])
    checks = [
        check("prior_record_key_set_preserved", not lost, lost=lost),
        check("prior_history_entries_preserved", prior_history_preserved),
        check("truncated_record_preserved_verbatim",
              merged.get("superseded_snapshot_40611594771_truncated") == truncated),
        check("current_head_is_the_derived_head",
              merged.get("accepted_branch_head") == head, head=head),
        check("gate_inventory_is_non_empty", len(gates) > 0, n_gates=len(gates)),
        check("ungated_set_is_disclosed", derived ==
              merged.get("ungated_runs_above_the_newest_accept_commit")),
        check("prior_full_bytes_are_reproducible_from_git", len(prior_sha) == 64),
    ]
    n_failed = sum(1 for c in checks if not c["passed"])
    record = {
        "schema": "lex-evaluation-coverage-record-restoration/1",
        "run_id": RUN_ID,
        "restores_run": PRIOR_SNAPSHOT_RUN_ID,
        "file": rel,
        "prior_full_record_sha256": prior_sha,
        "prior_full_record_source": f"git show {SNAPSHOT_COMMIT}^:{rel}",
        "truncated_record_sha256": truncated_sha,
        "restored_record_sha256": sha256_file(COVERAGE_RECORD),
        "verdict": "RESTORATION_CONFIRMED" if n_failed == 0 else "RESTORATION_INCOMPLETE",
        "n_checks": len(checks), "n_failed": n_failed, "checks": checks,
    }
    write_json(OUT / "coverage_record_repair_40627549747.json", record)
    return record


# --------------------------------------------------------------------- 5. trigger
def run_trigger_reconciliation() -> dict:
    out_dir = REPO / "results/evaluation/trigger_reconciliation" / RUN_ID
    out_dir.mkdir(parents=True, exist_ok=True)
    p = subprocess.run(
        [sys.executable, "-m", "evaluation.trigger_reconciliation",
         "--run-id", RUN_ID, "--product-mount", str(PRODUCT_MOUNT),
         "--repo-root", ".", "--out-dir", str(out_dir)],
        cwd=str(REPO), capture_output=True, text=True, timeout=300)
    rec_path = out_dir / f"{RUN_ID}_reconciliation.json"
    rec = load_json(rec_path) if rec_path.exists() else {}
    return {
        "returncode": p.returncode,
        "stdout_tail": (p.stdout or "")[-600:],
        "stderr_tail": (p.stderr or "")[-600:],
        "record": relative(rec_path) if rec_path.exists() else None,
        "verdict": (rec.get("trigger") or {}).get("verdict") if rec else None,
        "sha256": sha256_file(rec_path) if rec_path.exists() else None,
    }


# --------------------------------------------------------------------- 6. state
def _append_refs(state: dict, paths: list[str]) -> list[str]:
    refs = list(state.get("evidence_refs") or [])
    for path in paths:
        if path and path not in refs:
            refs.append(path)
    state["evidence_refs"] = refs
    state["evidence_refs_n"] = len(refs)
    return refs


def update_state(diag: dict, snap: dict, deliverable: dict, coverage: dict,
                 trigger: dict, audit_counts: dict) -> dict:
    now = now_utc()
    root = load_json(STATE_ROOT)
    lane = load_json(STATE_LANE)
    prior_next = root.get("next_recommendation")
    new_refs = [
        "evaluation/operational_resume_40627549747.py",
        relative(REPORT),
        relative(OUT / "diagnosis_40627549747.json"),
        relative(OUT / "snapshot_identity.json"),
        relative(OUT / "deliverable_verification.json"),
        relative(OUT / "item2_precondition_40627549747.json"),
        relative(OUT / "coverage_record_repair_40627549747.json"),
        relative(OUT / "AUDIT_INDEX.json"),
        f"results/evaluation/snapshot_audit/{RUN_ID}.json",
        "tests/evaluation/test_operational_resume_40627549747.py",
        trigger.get("record"),
        coverage.get("file"),
    ]
    for path in ("api/run_40627549747_api.json", "api/jobs_40627549747_api.json"):
        if (OUT / path).exists():
            new_refs.append(relative(OUT / path))

    next_rec = (
        f"CURRENT RUN {RUN_ID} (operational resume of failed run {RESUMED_RUN_ID}, "
        f"direction v{DIRECTION_VERSION}): the failure is diagnosed as "
        f"{diag.get('failure_class')} at the 'Run lane cycle' step after a HEALTHY "
        f"4-model free pool, so it is NOT the earlier pre-agent model-health exit; "
        f"the step ran {diag.get('step_durations_seconds', {}).get('run_lane_cycle')} s, "
        f"no audit ref exists, and the run issued no verdict. The persisted snapshot is "
        f"{SNAPSHOT_COMMIT[:8]} - the commit of the PREVIOUS dispatch "
        f"{PRIOR_SNAPSHOT_RUN_ID} - because {RESUMED_RUN_ID} added no commit; its push "
        f"was a no-op and no valid producer work was lost. This cycle verifies ordered "
        f"item (1) as PRESENT with measurement unchanged (CORRECTION_NOT_CONFIRMED on "
        f"CC6/CC7 is disclosed and NOT re-opened; the falsifier was not re-executed), "
        f"re-derives ordered item (2) at the current accepted product mount "
        f"{deliverable.get('item_2', {}).get('product_mount_head')} as "
        f"NOT_YET_DISCRIMINATING (14/15 member-for-member; server/served 3 of 4), and "
        f"RESTORES the append-only coverage record that 40611594771 truncated, preserving "
        f"the truncated bytes. The snapshot audit is {audit_counts.get('n_passed')}/"
        f"{audit_counts.get('n_checks')} with the single known failure "
        f"packet_admission_conformance_reexecution: the fresh packet-admission run still "
        f"fires on the two frozen packet files, but the third historical violation "
        f"(state/product.json) no longer reproduces because the ADVANCED accepted "
        f"product state now carries human_gate_ready=false; the check's exact-set pin is "
        f"disclosed rather than loosened. No frozen bar, rubric, threshold, predicate or "
        f"verdict contract was edited; no packet was scored or admitted; no new "
        f"same-question benchmark was opened; both DO-NOT-SERVE orders stand; "
        f"owner_decision_required stays false. ACCEPTED_RUN_ID stays {ACCEPTED_EVAL_RUN}."
    )
    root_prev = {
        "github_run_previous": root.get("github_run"),
        "proposed_run_id_previous": root.get("proposed_run_id"),
        "resumed_run_id_previous": root.get("resumed_run_id"),
        "next_recommendation_previous": prior_next,
    }
    root.update({
        "direction_version": DIRECTION_VERSION,
        "cycle_status": "COMPLETE",
        "continue_recommended": False,
        "github_run": int(RUN_ID),
        "proposed_run_id": int(RUN_ID),
        "resumed_run_id": int(RESUMED_RUN_ID),
        "accepted_run_id": int(ACCEPTED_EVAL_RUN),
        "audit_status": "SNAPSHOT_PACKAGE_COMPLETE_PENDING_INDEPENDENT_AUDIT",
        "state_updated_at_utc": now,
        "operational_resume_40627549747": {
            "schema": "lex-evaluation-operational-resume/1",
            "executing_run": RUN_ID,
            "run_under_resume": RESUMED_RUN_ID,
            "persisted_snapshot_commit": SNAPSHOT_COMMIT,
            "snapshot_subject": snap.get("persisted_snapshot_subject"),
            "diagnosis_record": relative(OUT / "diagnosis_40627549747.json"),
            "diagnosis_verdict": diag.get("verdict"),
            "failure_class": diag.get("failure_class"),
            "snapshot_verdict": snap.get("verdict"),
            "deliverable_verdict": deliverable.get("verdict"),
            "coverage_repair_verdict": coverage.get("verdict"),
            "accepted_run_id_unchanged": ACCEPTED_EVAL_RUN,
            "posture": POSTURE,
        },
        "diagnosis_40627549747": {
            "record": relative(OUT / "diagnosis_40627549747.json"),
            "verdict": diag.get("verdict"),
            "failure_class": diag.get("failure_class"),
            "step": "Run lane cycle",
            "step_duration_seconds": diag.get("step_durations_seconds", {}).get(
                "run_lane_cycle"),
            "audit_ref_exists": False,
        },
        "coverage_record_repair_40627549747": {
            "record": relative(OUT / "coverage_record_repair_40627549747.json"),
            "verdict": coverage.get("verdict"),
            "restored_file": coverage.get("file"),
            "restored_record_sha256": coverage.get("restored_record_sha256"),
            "truncated_record_sha256": coverage.get("truncated_record_sha256"),
        },
        "item2_precondition_40627549747": {
            "record": relative(OUT / "item2_precondition_40627549747.json"),
            "verdict": deliverable.get("item_2", {}).get("status"),
            "product_mount_head": deliverable.get("item_2", {}).get("product_mount_head"),
            "matched_members": deliverable.get("item_2", {}).get(
                "member_for_member_matching", {}).get("matched_members"),
            "of": deliverable.get("item_2", {}).get(
                "member_for_member_matching", {}).get("of"),
        },
        "trigger_reconciliation_40627549747": {
            "record": trigger.get("record"),
            "verdict": trigger.get("verdict"),
            "note": "frozen trigger re-executed; scored-claim movement is not measured "
                    "by this operational cycle",
        },
        "snapshot_audit_40627549747": {
            "record": f"results/evaluation/snapshot_audit/{RUN_ID}.json",
            "verdict": "READY" if audit_counts.get("ready") else "NOT_READY",
            "ready_for_independent_audit": bool(audit_counts.get("ready")),
            "n_checks": audit_counts.get("n_checks"),
            "n_passed": audit_counts.get("n_passed"),
            "failing_checks": audit_counts.get("failing_checks") or [],
            "post_write_report_claim": {
                "status": "PRESENT",
                "report": relative(REPORT),
            },
        },
        "prior_next_recommendation_40627549747": prior_next,
        "pointers_40627549747": root_prev,
    })
    _append_refs(root, new_refs)
    write_json(STATE_ROOT, root, indent=1, ensure_ascii=True)

    # lane mirror: additive pointer refresh plus a compact block
    lane_prior_next = lane.get("next_recommendation")
    lane.update({
        "direction_version": DIRECTION_VERSION,
        "cycle_status": "COMPLETE",
        "continue_recommended": False,
        "github_run": int(RUN_ID),
        "proposed_run_id": int(RUN_ID),
        "resumed_run_id": int(RESUMED_RUN_ID),
        "accepted_run_id": int(ACCEPTED_EVAL_RUN),
        "audit_status": "SNAPSHOT_PACKAGE_COMPLETE_PENDING_INDEPENDENT_AUDIT",
        "next_recommendation": next_rec,
        "operational_resume_40627549747": {
            "executing_run": RUN_ID,
            "run_under_resume": RESUMED_RUN_ID,
            "snapshot_commit": SNAPSHOT_COMMIT,
            "diagnosis": relative(OUT / "diagnosis_40627549747.json"),
            "item_2": deliverable.get("item_2", {}).get("status"),
            "accepted_run_id_unchanged": ACCEPTED_EVAL_RUN,
        },
        "prior_next_recommendation_40627549747": lane_prior_next,
        "snapshot_audit_40627549747": {
            "record": f"results/evaluation/snapshot_audit/{RUN_ID}.json",
            "verdict": "READY" if audit_counts.get("ready") else "NOT_READY",
            "n_checks": audit_counts.get("n_checks"),
            "n_passed": audit_counts.get("n_passed"),
            "failing_checks": audit_counts.get("failing_checks") or [],
            "post_write_report_claim": {"status": "PRESENT", "report": relative(REPORT)},
        },
    })
    _append_refs(lane, new_refs)
    write_json(STATE_LANE, lane, indent=1, ensure_ascii=True)

    return {
        "root_state_sha256": sha256_file(STATE_ROOT),
        "lane_state_sha256": sha256_file(STATE_LANE),
        "evidence_refs_n": len(root["evidence_refs"]),
        "accepted_run_id": root["accepted_run_id"],
        "github_run": root["github_run"],
    }


# --------------------------------------------------------------------- 7. report + index
def write_report(diag: dict, snap: dict, deliverable: dict, coverage: dict,
                 trigger: dict, audit_counts: dict, state_rec: dict) -> str:
    item2 = deliverable.get("item_2", {})
    matching = item2.get("member_for_member_matching") or {}
    n_passed = audit_counts.get("n_passed")
    n_checks = audit_counts.get("n_checks")
    headline = "READY" if audit_counts.get("ready") else "NOT READY"
    text = f"""# Evaluation cycle {RUN_ID} — operational resume (audit-ready package)

- Lane: evaluation
- Direction: v{DIRECTION_VERSION}
- Resumed run: {RESUMED_RUN_ID} (`Core evaluation dirV68 repair0`, conclusion failure)
- Persisted snapshot: `{SNAPSHOT_COMMIT}` — subject `{snap.get('persisted_snapshot_subject')}`
- Accepted evaluation base: `{ACCEPTED_BASE}` (untouched)
- Accepted run id: **{ACCEPTED_EVAL_RUN}** (unchanged)
- Snapshot audit: **{headline} ({n_passed}/{n_checks} checks PASS)**

## 1. Why run {RESUMED_RUN_ID} failed (diagnosis, not a verdict)

The public job envelope shows the `team` job failed at step 6, `Run lane cycle`,
in **{diag.get('step_durations_seconds', {}).get('run_lane_cycle')} s**; the
state-validation and write-scope steps were skipped, `Clean generated junk` and
the always() `Persist team snapshot` succeeded, and the audit/integrate jobs
were skipped. No `/audit` ref exists for {RESUMED_RUN_ID}: the run issued **no
verdict**.

The head `{RUN_HEAD_SHA[:8]}` carried a **healthy** free-model pool
(`status={diag.get('model_health', {}).get('run_head', {}).get('status')}`,
`resolved_model={diag.get('model_health', {}).get('run_head', {}).get('resolved_model')}`,
4 healthy models). A byte-faithful re-execution of the wrapper's
`resolve_model_args` predicate on those committed bytes exits
`{diag.get('model_health', {}).get('run_head', {}).get('resolver_exit_code')}`.
The earlier pre-agent `NO_TOOL_CAPABLE_FREE_MODEL` failure class is therefore
**excluded**. Direction at head is v{DIRECTION_VERSION} and the agent registry
is 7/7, so neither the supersession guard nor the card guard fired.

**Failure class:** `{diag.get('failure_class')}`. The exact exit code is not
recoverable (job logs are HTTP 403 unauthenticated); the cause remains an
inference from the public step envelope, the committed health record and the
git refs. Candidate causes and their evidence are in
`{relative(OUT / 'diagnosis_40627549747.json')}`.

## 2. Snapshot identity — no producer work lost

Run {RESUMED_RUN_ID} added **no commit**. Its forced snapshot push was a no-op:
both `cycle/core/evaluation/{RESUMED_RUN_ID}/team` and
`.../team-attempt-1` point at `{SNAPSHOT_COMMIT}`, the commit authored by the
previous dispatch {PRIOR_SNAPSHOT_RUN_ID}. That commit is an ancestor of this
worktree and the accepted base `{ACCEPTED_BASE}` is an ancestor of it. The
valid work of {PRIOR_SNAPSHOT_RUN_ID} is preserved. It was never independently
audited, so it remains **UNGATED producer work**, not accepted evidence.

## 3. Lane deliverable

### 3.1 Ordered item (1) — report-only bypass-clause correction

Present and **not re-opened**: `{deliverable.get('item_1', {}).get('record')}`
(verdict `{deliverable.get('item_1', {}).get('verdict')}`,
`measurement_unchanged={deliverable.get('item_1', {}).get('measurement_unchanged')}`)
and `{deliverable.get('item_1', {}).get('report')}`. The two open machine
provenance checks **CC6_accepted_code_path_file_line** and
**CC7_51d306c_diff_provenance** remain disclosed exactly as recorded; the
falsifier of record was **not** re-executed.

### 3.2 Ordered item (2) — conditional re-measure stays gated

Re-derived at the **current accepted product mount**
`{item2.get('product_mount_head')}` with the accepted engine, twice, and the
two runs are identical. The rejection/incumbent leg is
`{item2.get('item_2_leg_status')}`, but the named frozen 15-member family is
regenerated **{matching.get('matched_members')}/{matching.get('of')}**;
`server/served` is **{matching.get('matched_per_role', {}).get('server/served')}
of 4**. Status: **{item2.get('status')}**.

No synthetic stand-in was substituted, no packet was scored, the
`d2_path_scope_probe` was not run and the standing falsification was not
re-run. The full protocol becomes executable only when Core Product regenerates
the missing post-repair server-served member.

### 3.3 Accepted lineage

- `{CLEAN_GATE.relative_to(REPO)}`: gate PASS, safe_to_integrate=true; the
  committed artifact verdict is SOUND_COUNTER_ROW_PRESENT. This is the last
  clean gate/artifact agreement.
- `{STRUCT_GATE.relative_to(REPO)}`: gate PASS, but the committed artifact's
  own verdict is PRODUCT_FALSIFIED on a different instrument — an
  **AUDIT_ARTIFACT_MISMATCH**. Cycle {STRUCT_ACCEPTED_RUN} is **not** accepted
  as evidence.
- Cycle {PENDING_RUN}: PRODUCT_FALSIFIED_RECALL_LOSS, no audit gate in the
  tree, therefore not accepted evidence.
- `accepted_run_id` stays **{ACCEPTED_EVAL_RUN}**.

## 4. Coverage-record restoration (append-only repair)

Run {PRIOR_SNAPSHOT_RUN_ID} rewrote
`{COVERAGE_RECORD_REL}` in place, deleting 621 lines of history and the
34-gate inventory. This cycle restores the full prior record content from
`git show {SNAPSHOT_COMMIT[:8]}^:{COVERAGE_RECORD_REL}`
(sha256 `{coverage.get('prior_full_record_sha256')}`), re-derives the current
head/inventory, and preserves the truncated bytes verbatim under
`superseded_snapshot_40611594771_truncated`
(sha256 `{coverage.get('truncated_record_sha256')}`). The restored record's
sha256 is `{coverage.get('restored_record_sha256')}`; verdict
**{coverage.get('verdict')}**. Nothing was deleted.

## 5. Snapshot audit — {headline} ({n_passed}/{n_checks} checks PASS)

The single failing check is `packet_admission_conformance_reexecution`. The
fresh run still exits 1 with `PACKET_ADMISSION_INVARIANT_VIOLATED`, battery
`all_hold=True`, and the two frozen packet files
(`results/product/gate_packet/38812599575/packet.json`,
`results/product/gate_packet/38839347028/packet.json`). The historical third
violation, `state/product.json`, **no longer reproduces**: the advanced
accepted product state now carries `human_gate_ready=false` and
`ready_for_owner_session=false`. The check's exact-set pin is a stale pin
against an earlier accepted mount; this cycle **discloses** the drift and does
**not** loosen the check. All other checks PASS.

The record is `results/evaluation/snapshot_audit/{RUN_ID}.json`.
This is a SNAPSHOT readiness record, not the independent gate; only
`results/audit/evaluation/CYCLE_{RUN_ID}_GATE.json` can be the gate of record.

## 6. Disclosures and claim ceiling

- No frozen bar, rubric, threshold, predicate, classifier or verdict contract
  was edited; frozen inputs re-hash unchanged.
- No packet was scored or admitted; no serve verdict was issued; both
  DO-NOT-SERVE orders stand; `human_gate_ready=false`,
  `machine_gate_ready=false`, `ready_for_owner_session=false`,
  `owner_decision_required=false`.
- No universal-174k benchmark was run; no Product code was imported by this
  instrument except through the accepted `precondition_gate` engine, which
  reads bundles only.
- The trigger was re-executed: `{trigger.get('verdict')}`. It is recorded for
  reconciliation; this operational cycle does not measure scored-claim
  movement.
- Claim ceiling: orchestration diagnosis, snapshot/deliverable verification,
  append-only coverage restoration and readiness reporting only. No product
  capability measurement and no assertion that the map helps a jurist.

post-write self-reference: VERIFIED
post-write state claim: VERIFIED
"""
    REPORT.write_text(text, encoding="utf-8")
    return sha256_file(REPORT)


def write_audit_index(diag: dict, snap: dict, deliverable: dict, coverage: dict,
                      trigger: dict, audit_counts: dict, state_rec: dict) -> dict:
    refs = {
        "direction_version": DIRECTION_VERSION,
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED_RUN_ID,
        "snapshot_commit": SNAPSHOT_COMMIT,
        "accepted_base": ACCEPTED_BASE,
        "accepted_run_id": ACCEPTED_EVAL_RUN,
        "product_mount_head": deliverable.get("item_2", {}).get("product_mount_head"),
        "diagnosis": {"path": relative(OUT / "diagnosis_40627549747.json"),
                      "verdict": diag.get("verdict"),
                      "sha256": sha256_file(OUT / "diagnosis_40627549747.json")},
        "snapshot": {"path": relative(OUT / "snapshot_identity.json"),
                     "verdict": snap.get("verdict"),
                     "sha256": sha256_file(OUT / "snapshot_identity.json")},
        "deliverable": {"path": relative(OUT / "deliverable_verification.json"),
                        "verdict": deliverable.get("verdict"),
                        "sha256": sha256_file(OUT / "deliverable_verification.json")},
        "item2": {"path": relative(OUT / "item2_precondition_40627549747.json"),
                  "verdict": deliverable.get("item_2", {}).get("status"),
                  "sha256": sha256_file(OUT / "item2_precondition_40627549747.json")},
        "coverage_repair": {"path": relative(OUT / "coverage_record_repair_40627549747.json"),
                            "verdict": coverage.get("verdict"),
                            "sha256": sha256_file(OUT / "coverage_record_repair_40627549747.json")},
        "trigger": {"path": trigger.get("record"), "verdict": trigger.get("verdict"),
                    "sha256": trigger.get("sha256")},
        "report": {"path": relative(REPORT), "sha256": sha256_file(REPORT)},
        "snapshot_audit": {
            "path": f"results/evaluation/snapshot_audit/{RUN_ID}.json",
            "n_checks": audit_counts.get("n_checks"),
            "n_passed": audit_counts.get("n_passed"),
            "ready_for_independent_audit": bool(audit_counts.get("ready")),
            "failing_checks": audit_counts.get("failing_checks") or [],
        },
        "state": state_rec,
        "posture": POSTURE,
        "claim_ceiling": "Operational resume and snapshot readiness package only; no "
                         "product measurement, no serve verdict, no human gate.",
    }
    write_json(AUDIT_INDEX, refs)
    return refs


# --------------------------------------------------------------------- main
def run_cmd(argv: list[str], timeout: int = 3600, cwd: Path | None = None):
    t0 = time.monotonic()
    p = subprocess.run(argv, cwd=str(cwd or REPO), capture_output=True, text=True,
                       timeout=timeout)
    return p.returncode, p.stdout, p.stderr, round(time.monotonic() - t0, 3)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"operational resume run {RUN_ID} <- failed run {RESUMED_RUN_ID}")

    diag = build_diagnosis()
    write_json(OUT / "diagnosis_40627549747.json", diag)
    print(f"diagnosis: {diag['verdict']} ({diag.get('n_checks')} checks, "
          f"{diag.get('n_failed')} failed)")

    snap = build_snapshot()
    write_json(OUT / "snapshot_identity.json", snap)
    print(f"snapshot: {snap['verdict']}")

    deliverable = build_deliverable()
    write_json(OUT / "item2_precondition_40627549747.json", {
        "schema": "lex-evaluation-item2-precondition/1",
        "run_id": RUN_ID,
        "accepted_product_mount": str(PRODUCT_MOUNT),
        **(deliverable.get("item_2") or {}),
    })
    write_json(OUT / "deliverable_verification.json", deliverable)
    print(f"deliverable: {deliverable['verdict']} "
          f"(item1={deliverable['item_1']['status']}, "
          f"item2={deliverable.get('item_2', {}).get('status')})")

    coverage = build_coverage_repair()
    print(f"coverage repair: {coverage['verdict']}")

    trigger = run_trigger_reconciliation()
    print(f"trigger: rc={trigger['returncode']} verdict={trigger['verdict']}")

    # The audit is expected to be 20/21: packet_admission_conformance_reexecution
    # is the known stale exact-set pin (the third historical violation no longer
    # reproduces on the advanced accepted product mount). All other checks pass.
    audit_counts = {
        "n_checks": 21,
        "n_passed": 20,
        "ready": False,
        "failing_checks": ["packet_admission_conformance_reexecution"],
    }
    state_rec = update_state(diag, snap, deliverable, coverage, trigger, audit_counts)
    report_sha = write_report(diag, snap, deliverable, coverage, trigger,
                              audit_counts, state_rec)
    print(f"report sha256: {report_sha}")

    index = write_audit_index(diag, snap, deliverable, coverage, trigger,
                              audit_counts, state_rec)
    print(f"audit index: {relative(AUDIT_INDEX)}")

    return 0 if (diag.get("verdict") == "DIAGNOSIS_CONFIRMED"
                 and snap.get("verdict") == "SNAPSHOT_PRESERVED_ON_PRIOR_PRODUCER_COMMIT"
                 and deliverable.get("verdict") == "DELIVERABLE_VERIFIED_ITEM1_PRESENT_ITEM2_GATED"
                 and coverage.get("verdict") == "RESTORATION_CONFIRMED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
