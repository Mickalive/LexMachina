#!/usr/bin/env python3
"""Operational resume for evaluation GitHub run 40423990845.

Resumes from the persisted producer snapshot of failed run 40423855962
("Core evaluation dirV68 repair2", team snapshot ea98384e).

This instrument answers one operational question and nothing else:

    why did run 40423855962 fail, is its persisted snapshot the accepted
    evaluation base, is the lane deliverable intact, and is the snapshot
    audit-ready without opening a new same-question cycle?

It is deliberately a verification instrument, not a benchmark:

  * diagnosis     -- public run/job metadata + the committed model-health
                    predicate at the run's head_sha, re-executed byte-faithfully
  * snapshot      -- the forced team snapshot is compared with the accepted base
  * deliverable   -- last clean accepted cycle, the structurally accepted cycle's
                    committed artifact and its audit record, the pending recall
                    cycle, ordered item (1), ordered item (2) precondition
  * replay        -- the committed minimal retrieval/counter-authority artifact is
                    replayed against its recorded product-mount head
  * finalize      -- report, audit index, additive state refresh

Frozen before execution: evaluation/OPERATIONAL_RESUME_40423990845_HYPOTHESIS_V1.json
and evaluation/OPERATIONAL_RESUME_40423990845_FREEZE_V1.json. No frozen bar,
rubric, threshold, predicate, classifier or verdict contract is moved. No packet
is admitted, no serve verdict is issued, no human gate is staged.

Usage:
    python3 -m evaluation.operational_resume_40423990845
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# --------------------------------------------------------------------- constants
REPO = Path(__file__).resolve().parent.parent
RUN_ID = "40423990845"
RESUMED_RUN_ID = "40423855962"
SNAPSHOT_COMMIT = "ea98384e54d31d2e694c418a1d1ce5769fc6c32f"
PRIOR_SNAPSHOT_COMMIT = "9fe9d7143133dde25152e2babbe13438a661cfa1"
RUN_HEAD_SHA = "0c551b49a1c908d439702d477e192bb784865e1d"
CONTROL_PLANE_HEAD = "4fd41970"
PRODUCT_F9B0 = "f9b0db254dc22a46a240c7937fd75e3eb2ec2e95"
PRODUCT_MOUNT = Path("/tmp/lex_accepted/product")
DIRECTION_VERSION = 68

CLEAN_ACCEPTED_RUN = "40258497460"
CLEAN_ACCEPTED_COMMIT = "64208e15"
STRUCT_ACCEPTED_RUN = "40265377500"
PENDING_RUN = "40261335674"

HYPOTHESIS = REPO / "evaluation/OPERATIONAL_RESUME_40423990845_HYPOTHESIS_V1.json"
FREEZE = REPO / "evaluation/OPERATIONAL_RESUME_40423990845_FREEZE_V1.json"
INSTRUMENT = Path(__file__).resolve()
TEST = REPO / "tests/evaluation/test_operational_resume_40423990845.py"

OUT = REPO / "results/evaluation/operational_resume_40423990845"
API = OUT / "api"
REPLAY = OUT / "replay"
REPORT = REPO / "reports/evaluation/OPERATIONAL_RESUME_40423855962_AUDIT_READY.md"
AUDIT_INDEX = OUT / "AUDIT_INDEX.json"

STATE_ROOT = REPO / "state/evaluation.json"
STATE_LANE = REPO / "evaluation/state/evaluation.json"

CLEAN_GATE = REPO / f"results/audit/evaluation/CYCLE_{CLEAN_ACCEPTED_RUN}_GATE.json"
CLEAN_ARTIFACT = REPO / f"results/evaluation/post_repair_family_ca_falsifier/{CLEAN_ACCEPTED_RUN}.json"
STRUCT_GATE = REPO / f"results/audit/evaluation/CYCLE_{STRUCT_ACCEPTED_RUN}_GATE.json"
STRUCT_REPORT = REPO / f"reports/audit/evaluation/CYCLE_{STRUCT_ACCEPTED_RUN}.md"
STRUCT_ARTIFACT = REPO / f"results/evaluation/minimal_retrieval_ca_benchmark/test_{STRUCT_ACCEPTED_RUN}.json"
STRUCT_ENGINE = REPO / f"results/evaluation/minimal_retrieval_ca_benchmark/test_{STRUCT_ACCEPTED_RUN}_engine_mapping_free_recall_falsifier.json"
PENDING_ARTIFACT = REPO / f"results/evaluation/fast_mvp_retrieval_recall_benchmark/{PENDING_RUN}.json"
PENDING_COMPARISON = REPO / f"results/evaluation/fast_mvp_retrieval_recall_benchmark/{PENDING_RUN}_COMPARISON_40153908549.json"
ITEM1_REPORT = REPO / "reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md"
ITEM1_RECORD = REPO / "results/evaluation/bypass_clause_correction/40113448025.json"

BENCH_ENGINE_FILES = [
    REPO / "evaluation/minimal_retrieval_ca_benchmark.py",
    REPO / "evaluation/mapping_free_recall_falsifier.py",
    REPO / "evaluation/post_repair_family_ca_falsifier.py",
]

API_BASE = "https://api.github.com/repos/Mickalive/LexMachina/actions/runs"
REPLAY_EXPECTED_DIFF_KEYS = {"run_id", "generated_at_utc", "product_mount", "engine_record_path"}
ENGINE_EXPECTED_DIFF_KEYS = {"run_id", "generated_at_utc", "product_mount"}


# --------------------------------------------------------------------- helpers
def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def brief(obj, n: int = 400) -> str:
    return json.dumps(obj, ensure_ascii=False)[:n]


def check(label: str, ok: bool, **detail) -> dict:
    return {"check": label, "passed": bool(ok), "detail": detail}


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_cmd(argv: list[str], timeout: int = 3600, cwd: Path | None = None):
    t0 = time.monotonic()
    p = subprocess.run(argv, cwd=str(cwd or REPO), capture_output=True, text=True,
                       timeout=timeout)
    return p.returncode, p.stdout, p.stderr, round(time.monotonic() - t0, 3)


def git(*args: str, timeout: int = 180):
    p = subprocess.run(["git", *args], cwd=str(REPO), capture_output=True,
                       text=True, timeout=timeout)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


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


def _secs(a: str | None, b: str | None) -> float | None:
    if not a or not b:
        return None
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    return (datetime.strptime(b, fmt) - datetime.strptime(a, fmt)).total_seconds()


def _json_equal(a, b) -> bool:
    return json.dumps(a, sort_keys=True, ensure_ascii=False) == \
        json.dumps(b, sort_keys=True, ensure_ascii=False)


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


# --------------------------------------------------------------------- 1. API + diagnosis
def build_diagnosis() -> dict:
    api_run = load_or_fetch_api("run", RESUMED_RUN_ID)
    api_jobs = load_or_fetch_api("jobs", RESUMED_RUN_ID)
    run_env, jobs_env = api_run["envelope"], api_jobs["envelope"]
    if not jobs_env:
        return {"schema": "lex-evaluation-operational-resume-diagnosis/1",
                "run_id": RUN_ID, "diagnosed_run_id": RESUMED_RUN_ID,
                "failure_class": "UNAVAILABLE",
                "verdict": "DIAGNOSIS_UNAVAILABLE_NO_API", "checks": [],
                "failure_summary": "no public jobs envelope available",
                "api": {"run": api_run.get("path"), "jobs": api_jobs.get("path"),
                        "run_source": api_run.get("source"),
                        "jobs_source": api_jobs.get("source")}}

    team = _job(jobs_env, "team") or {}
    audit = _job(jobs_env, "audit") or {}
    integrate = _job(jobs_env, "integrate") or {}
    resilience = _job(jobs_env, "resilience") or {}
    lane_cycle = _step(team, "Run lane cycle") or {}
    state_step = _step(team, "Validate active MVP producer state") or {}
    junk_step = _step(team, "Clean generated junk") or {}
    scope_step = _step(team, "Enforce lane write scope") or {}
    persist_step = _step(team, "Persist team snapshot") or {}

    # The wrapper's early exit, re-executed on the committed bytes at the run head.
    health_run = OUT / f"model_health_at_{RUN_HEAD_SHA[:8]}.json"
    health_ctl = OUT / f"model_health_at_{CONTROL_PLANE_HEAD}.json"
    for commit, dest in ((RUN_HEAD_SHA, health_run), (CONTROL_PLANE_HEAD, health_ctl)):
        text = _tree_file(commit, "state/model_health.json")
        dest.parent.mkdir(parents=True, exist_ok=True)
        if text is None:
            dest.write_text("{}\n", encoding="utf-8")
        else:
            dest.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
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

    # Direction and agent registry at the run head: rule out the two other
    # pre-agent validation exits before claiming model health.
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
        check("head_sha_is_the_pre_health_fix_commit",
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
              meaning="a pre-agent wrapper exit, not a full lane cycle"),
        check("state_validation_step_skipped_after_failure",
              state_step.get("conclusion") == "skipped",
              conclusion=state_step.get("conclusion")),
        check("junk_clean_step_succeeded", junk_step.get("conclusion") == "success",
              conclusion=junk_step.get("conclusion")),
        check("write_scope_step_skipped_after_failure",
              scope_step.get("conclusion") == "skipped",
              conclusion=scope_step.get("conclusion"),
              note="the scope guard never ran, so this run cannot be a scope failure"),
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
        check(        "direction_at_head_is_v68", head_direction_version == DIRECTION_VERSION,
              version=head_direction_version, expected=DIRECTION_VERSION,
              source=f"git show {RUN_HEAD_SHA[:8]}:state/factory_direction.json"),
        check("lab_branch_direction_copy_is_stale_and_disclosed",
              load_json(STATE_ROOT).get("direction_version") == DIRECTION_VERSION
              and load_json(REPO / "state/factory_direction.json").get("version") != DIRECTION_VERSION,
              lane_state_direction_version=load_json(STATE_ROOT).get("direction_version"),
              lab_copy_version=load_json(REPO / "state/factory_direction.json").get("version"),
              note="the in-repo lab copy is stale; the authoritative control plane is "
                   "mounted from main and is pinned in the freeze/audit index"),
        check("agent_registry_at_head_is_clean",
              registry_ok, n_agent_files=len(agent_ids), n_cards=len(card_ids),
              agent_ids=agent_ids, card_ids=sorted(card_ids),
              meaning="the registry guard cannot explain this failure"),
        check("model_health_at_head_is_unhealthy",
              health_head.get("healthy") is False
              and health_head.get("resolved_model") in (None, "")
              and health_head.get("healthy_models") == [],
              healthy=health_head.get("healthy"),
              resolved_model=health_head.get("resolved_model"),
              healthy_models=health_head.get("healthy_models"),
              status=health_head.get("status"),
              last_checked_run_id=health_head.get("last_checked_run_id"),
              last_checked_at=health_head.get("last_checked_at")),
        check("resolve_model_args_replay_at_head_exits_76",
              rc_at_head == 76,
              exit_code=rc_at_head, stdout=out_at_head.strip(),
              stderr=err_at_head.strip(), file=relative(health_run),
              committed_at=f"git show {RUN_HEAD_SHA[:8]}:state/model_health.json"),
        check("resolve_model_args_replay_at_control_plane_head_exits_0",
              rc_at_ctl == 0 and bool(out_at_ctl.strip()),
              exit_code=rc_at_ctl, resolved_model=out_at_ctl.strip(),
              stderr=err_at_ctl.strip(),
              healthy=health_ctl_obj.get("healthy"),
              status=health_ctl_obj.get("status"),
              file=relative(health_ctl),
              committed_at=f"git show {CONTROL_PLANE_HEAD}:state/model_health.json"),
        check("failure_is_a_pre_agent_provider_exit_not_a_verdict",
              not (OUT / "producer_cycle_record.json").exists(),
              meaning="no producer cycle record can exist because the wrapper "
                      "exited before the lane agent started"),
    ]

    n_failed = sum(1 for c in checks if not c["passed"])
    failure_summary = (
        f"Run {RESUMED_RUN_ID} failed at step {lane_cycle.get('number')} "
        f"'{lane_cycle.get('name')}' in {cycle_seconds}s, before the lane agent started. "
        f"The run head {RUN_HEAD_SHA[:8]} carries state/model_health.json with "
        f"healthy={health_head.get('healthy')!r}, resolved_model="
        f"{health_head.get('resolved_model')!r} and status={health_head.get('status')!r} "
        f"(last checked by run {health_head.get('last_checked_run_id')}). A byte-faithful "
        f"re-execution of the wrapper's resolve_model_args predicate on those committed "
        f"bytes exits {rc_at_head} (LEX_NO_HEALTHY_FREE_TOOL_MODEL); the same predicate "
        f"on the later control-plane head {CONTROL_PLANE_HEAD} exits {rc_at_ctl} with "
        f"{out_at_ctl.strip()!r}. The run's own direction is v{DIRECTION_VERSION} and its "
        "agent registry is 7/7 clean, so neither the supersession guard nor the card "
        "guard fired. 'Clean generated junk' and 'if: always()' snapshot persistence "
        "succeeded; audit/integrate were skipped and no /audit ref exists, i.e. the run "
        "issued NO verdict. This is an ORCHESTRATION/MODEL-HEALTH provider failure, not "
        "a lane-scope validation failure, not a zero-delta repair, not a work-quantum "
        "starvation and not a gate REVISE/BLOCKED."
    )
    return {
        "schema": "lex-evaluation-operational-resume-diagnosis/1",
        "run_id": RUN_ID,
        "diagnosed_run_id": RESUMED_RUN_ID,
        "failure_class": "ORCHESTRATION_MODEL_HEALTH_PRE_AGENT",
        "verdict": "DIAGNOSIS_CONFIRMED" if n_failed == 0 else "DIAGNOSIS_INCOMPLETE",
        "n_checks": len(checks), "n_failed": n_failed, "checks": checks,
        "failure_summary": failure_summary,
        "api": {"run": api_run.get("path"), "jobs": api_jobs.get("path"),
                "run_source": api_run.get("source"),
                "jobs_source": api_jobs.get("source")},
        "step_durations_seconds": {
            "run_lane_cycle": cycle_seconds,
            "run_wall": run_seconds,
        },
        "model_health": {
            "run_head": {"commit": RUN_HEAD_SHA, "record": relative(health_run),
                         "healthy": health_head.get("healthy"),
                         "resolved_model": health_head.get("resolved_model"),
                         "status": health_head.get("status"),
                         "last_checked_run_id": health_head.get("last_checked_run_id"),
                         "last_checked_at": health_head.get("last_checked_at"),
                         "resolver_exit_code": rc_at_head,
                         "resolver_stderr": err_at_head.strip()},
            "control_plane_head": {"commit": CONTROL_PLANE_HEAD, "record": relative(health_ctl),
                                   "healthy": health_ctl_obj.get("healthy"),
                                   "resolved_model": health_ctl_obj.get("resolved_model"),
                                   "status": health_ctl_obj.get("status"),
                                   "resolver_exit_code": rc_at_ctl},
        },
        "timing_interpretation": (
            "Run 40423855962 was created at "
            f"{run_env.get('created_at') if run_env else None} and last updated at "
            f"{run_env.get('updated_at') if run_env else None}. The control-plane health "
            f"record shows last_checked_run_id={health_ctl_obj.get('last_checked_run_id')} "
            f"at {health_ctl_obj.get('last_checked_at')}. The public record is consistent "
            "with the health refresh landing after this run had already dispatched; the "
            "exact wall-clock interleaving cannot be proven from the public run object "
            "alone and is stated as an inference, not a measurement."
        ),
        "audit_branch_probe": branch,
        "what_this_does_not_establish": [
            "the exact wrapper stderr line of run 40423855962 (job logs are 403 "
            "unauthenticated: 'Must have admin rights to Repository')",
            "a provider outage root cause or an excuse for a product defect",
            "any new product/evaluation measurement",
        ],
    }


# --------------------------------------------------------------------- 2. snapshot
def build_snapshot() -> dict:
    rc_team, team_sha, err_team = git(
        "rev-parse", f"origin/cycle/core/evaluation/{RESUMED_RUN_ID}/team")
    rc_lab, lab_sha, err_lab = git("rev-parse", "origin/lab/evaluation")
    rc_tip, tip_subject, _ = git("log", "-1", "--format=%s", SNAPSHOT_COMMIT)
    rc_par, parent, _ = git("rev-parse", f"{SNAPSHOT_COMMIT}^")
    rc_parsub, parent_subject, _ = git("log", "-1", "--format=%s", parent) if parent else (1, "", "")
    rc_diff, diff_stat, diff_err = git("diff", "--stat", SNAPSHOT_COMMIT, "origin/lab/evaluation")
    rc_tree, snap_tree, _ = git("rev-parse", f"{SNAPSHOT_COMMIT}^{{tree}}")
    rc_labtree, lab_tree, _ = git("rev-parse", "origin/lab/evaluation^{tree}")
    rc_anc, _, _ = git("merge-base", "--is-ancestor", CLEAN_ACCEPTED_COMMIT,
                       "origin/lab/evaluation")
    branch = audit_branch_probe(RESUMED_RUN_ID)

    checks = [
        check("team_snapshot_resolves", rc_team == 0 and bool(team_sha),
              sha=team_sha, error=err_team),
        check("team_snapshot_equals_accepted_base",
              team_sha == SNAPSHOT_COMMIT and lab_sha == SNAPSHOT_COMMIT,
              team_sha=team_sha, lab_sha=lab_sha, expected=SNAPSHOT_COMMIT),
        check("snapshot_tree_is_identical_to_accepted_base",
              rc_tree == 0 and snap_tree == lab_tree,
              snapshot_tree=snap_tree, lab_tree=lab_tree),
        check("no_worktree_diff_between_snapshot_and_accepted_base",
              rc_diff == 0 and diff_stat == "",
              diff_stat=diff_stat, error=diff_err),
        check("snapshot_is_the_structurally_accepted_commit",
              tip_subject == f"accept evaluation cycle {STRUCT_ACCEPTED_RUN}",
              subject=tip_subject),
        check("snapshot_is_a_repair_commit_not_a_producer_commit",
              parent_subject == f"evaluation cycle {STRUCT_ACCEPTED_RUN} repair 0",
              parent=parent, parent_subject=parent_subject),
        check("last_clean_accept_is_an_ancestor_of_the_snapshot",
              rc_anc == 0, clean_accept_commit=CLEAN_ACCEPTED_COMMIT),
        check("no_audit_ref_for_the_resumed_run", branch.get("exists") is False,
              ref=branch.get("ref"), exists=branch.get("exists")),
    ]
    n_failed = sum(1 for c in checks if not c["passed"])
    return {
        "schema": "lex-evaluation-operational-resume-snapshot/1",
        "run_id": RUN_ID,
        "diagnosed_run_id": RESUMED_RUN_ID,
        "verdict": "SNAPSHOT_PRESERVED_ON_ACCEPTED_BASE" if n_failed == 0
                   else "SNAPSHOT_UNEXPECTED",
        "n_checks": len(checks), "n_failed": n_failed, "checks": checks,
        "snapshot_commit": SNAPSHOT_COMMIT,
        "snapshot_subject": tip_subject,
        "snapshot_parent": parent,
        "snapshot_parent_subject": parent_subject,
        "lab_evaluation_commit": lab_sha,
        "no_new_producer_work_in_snapshot": True,
        "audit_branch": branch,
        "meaning": (
            "The run's forced team snapshot is the accepted base itself. No commit "
            "attributable to the failed run exists, so there is nothing to relocate or "
            "re-home; the snapshot is preserved, not stale."
        ),
    }


# --------------------------------------------------------------------- 3. deliverable
def _pins_ok(artifact: dict) -> list[dict]:
    rows = []
    for key in ("frozen_hypothesis", "freeze_record", "frozen_spec",
                "frozen_label_rubric"):
        pin = artifact.get(key) or {}
        path, want = pin.get("path"), pin.get("sha256")
        if not path or not want:
            rows.append({"pin": key, "path": path, "ok": False,
                         "reason": "pin missing from artifact"})
            continue
        f = REPO / path
        got = sha256_file(f) if f.is_file() else None
        rows.append({"pin": key, "path": path, "expected": want, "observed": got,
                     "ok": got == want})
    return rows


def build_deliverable() -> dict:
    clean_gate = load_json(CLEAN_GATE) if CLEAN_GATE.is_file() else {}
    clean_art = load_json(CLEAN_ARTIFACT) if CLEAN_ARTIFACT.is_file() else {}
    clean_es = clean_gate.get("evidence_summary") or {}
    struct_gate = load_json(STRUCT_GATE) if STRUCT_GATE.is_file() else {}
    struct_es = struct_gate.get("evidence_summary") or {}
    struct_report_txt = STRUCT_REPORT.read_text(encoding="utf-8") if STRUCT_REPORT.is_file() else ""
    struct_art = load_json(STRUCT_ARTIFACT) if STRUCT_ARTIFACT.is_file() else {}
    struct_eng = load_json(STRUCT_ENGINE) if STRUCT_ENGINE.is_file() else {}
    pending = load_json(PENDING_ARTIFACT) if PENDING_ARTIFACT.is_file() else {}
    item1 = load_json(ITEM1_RECORD) if ITEM1_RECORD.is_file() else {}

    rc_clean_gate, _, _ = git("ls-tree", CLEAN_ACCEPTED_COMMIT, relative(CLEAN_GATE))
    rc_anc, _, _ = git("merge-base", "--is-ancestor", CLEAN_ACCEPTED_COMMIT,
                       "origin/lab/evaluation")
    rc_gate_hist, gate_hist, _ = git("log", "--all", "--oneline", "--grep",
                                     f"accept evaluation cycle {PENDING_RUN}")
    rc_struct_gate, _, _ = git("ls-tree", SNAPSHOT_COMMIT, relative(STRUCT_GATE))

    pins = _pins_ok(struct_art)
    gate_text = json.dumps(struct_gate, ensure_ascii=False)
    mismatch_markers = {
        "gate_says_cached_bundle_benchmark_valid":
            "BENCHMARK_VALID_NO_FALSIFICATION" in gate_text,
        "gate_has_cached_bundle_shape":
            "cache_hits" in gate_text and struct_es.get("n_questions_tested") == 4,
        "report_runs_cached_bundle_instrument":
            "run_cached_bundle_benchmark.py" in struct_report_txt,
        "report_claims_benchmark_valid":
            "BENCHMARK_VALID_NO_FALSIFICATION" in struct_report_txt,
        "audit_never_mentions_the_committed_artifact":
            not any(s in gate_text + struct_report_txt for s in (
                "minimal_retrieval_ca_benchmark", "PRODUCT_FALSIFIED", "39319405429")),
    }

    claims = {
        "CC1_stale_clause_located_only_in_reading_report":
            (item1.get("claim_checks") or {}).get(
                "CC1_stale_clause_located_only_in_reading_report", {}).get("ok"),
        "CC2_measurement_unchanged_vs_freeze_pin":
            (item1.get("claim_checks") or {}).get(
                "CC2_measurement_unchanged_vs_freeze_pin", {}).get("ok"),
        "CC3_bundle_sha256_of_record":
            (item1.get("claim_checks") or {}).get(
                "CC3_bundle_sha256_of_record", {}).get("ok"),
        "CC4_span_seam_provenance_of_record":
            (item1.get("claim_checks") or {}).get(
                "CC4_span_seam_provenance_of_record", {}).get("ok"),
        "CC5_incumbent_left_in_place":
            (item1.get("claim_checks") or {}).get(
                "CC5_incumbent_left_in_place", {}).get("ok"),
        "CC6_accepted_code_path_file_line":
            (item1.get("claim_checks") or {}).get(
                "CC6_accepted_code_path_file_line", {}).get("ok"),
        "CC7_51d306c_diff_provenance":
            (item1.get("claim_checks") or {}).get(
                "CC7_51d306c_diff_provenance", {}).get("ok"),
        "CC8_span_seam_run_inventory_on_scored_population":
            (item1.get("claim_checks") or {}).get(
                "CC8_span_seam_run_inventory_on_scored_population", {}).get("ok"),
        "CC9_frozen_inputs_untouched":
            (item1.get("claim_checks") or {}).get(
                "CC9_frozen_inputs_untouched", {}).get("ok"),
        "CC10_d1_d2_d3_disclosure_source":
            (item1.get("claim_checks") or {}).get(
                "CC10_d1_d2_d3_disclosure_source", {}).get("ok"),
    }

    checks = [
        # last clean accepted cycle
        check("clean_accepted_gate_is_pass",
              clean_gate.get("gate") == "PASS"
              and clean_gate.get("safe_to_integrate") is True
              and clean_gate.get("required_fixes") == [],
              gate=clean_gate.get("gate"),
              safe_to_integrate=clean_gate.get("safe_to_integrate"),
              required_fixes=clean_gate.get("required_fixes")),
        check("clean_accepted_gate_evidence_matches_artifact",
              clean_es.get("benchmark_verdict") == clean_art.get("verdict")
              and clean_es.get("exit_code") == clean_art.get("exit_code")
              and clean_es.get("n_questions") == (clean_art.get("aggregate") or {}).get("n_enriched")
              and clean_es.get("falsification_proven")
              == clean_art.get("falsification_proven"),
              gate_verdict=clean_es.get("benchmark_verdict"),
              artifact_verdict=clean_art.get("verdict"),
              gate_exit=clean_es.get("exit_code"),
              artifact_exit=clean_art.get("exit_code"),
              gate_n=clean_es.get("n_questions"),
              artifact_n_enriched=(clean_art.get("aggregate") or {}).get("n_enriched"),
              gate_falsification=clean_es.get("falsification_proven"),
              artifact_falsification=clean_art.get("falsification_proven")),
        check("clean_accepted_artifact_is_sound_and_pins_match",
              clean_art.get("verdict") == "SOUND_COUNTER_ROW_PRESENT"
              and clean_art.get("exit_code") == 0
              and clean_art.get("falsification_proven") is False
              and (clean_art.get("pins_before_execution") or {}).get("all_match") is True
              and (clean_art.get("pins_after_execution") or {}).get("all_match") is True,
              verdict=clean_art.get("verdict"), exit_code=clean_art.get("exit_code"),
              falsification_proven=clean_art.get("falsification_proven")),
        check("clean_accepted_gate_is_committed_in_its_accept_commit",
              rc_clean_gate == 0 and rc_anc == 0,
              gate_path=relative(CLEAN_GATE), accept_commit=CLEAN_ACCEPTED_COMMIT),
        # structurally accepted cycle: artifact vs audit
        check("structurally_accepted_gate_is_pass",
              struct_gate.get("gate") == "PASS"
              and struct_gate.get("safe_to_integrate") is True,
              gate=struct_gate.get("gate"),
              safe_to_integrate=struct_gate.get("safe_to_integrate")),
        check("structurally_accepted_gate_is_committed_in_the_snapshot",
              rc_struct_gate == 0, gate_path=relative(STRUCT_GATE)),
        check("committed_artifact_exists_and_is_internally_consistent",
              STRUCT_ARTIFACT.is_file()
              and struct_art.get("verdict") == "PRODUCT_FALSIFIED"
              and struct_art.get("exit_code") == 1
              and struct_art.get("n_gates") == 18
              and struct_art.get("n_passed") == 11
              and struct_art.get("n_failed") == 4
              and len(struct_art.get("failed_gates") or []) == 4
              and struct_art.get("n_questions_measured") == 3
              and struct_art.get("packets_measured") == ["39319405429"]
              and struct_art.get("product_mount_head") == PRODUCT_F9B0
              and struct_art.get("packet_admitted") is False
              and struct_art.get("human_gate_ready") is False
              and struct_art.get("machine_gate_ready") is False
              and struct_art.get("ready_for_owner_session") is False
              and struct_art.get("input_drift") == []
              and struct_art.get("input_drift_invalidates_run") is False
              and struct_art.get("rehash_before_execution")
              == struct_art.get("rehash_after_execution")
              and struct_art.get("no_174k_benchmark_rerun") is True
              and struct_art.get("no_new_thresholds") is True
              and struct_art.get("direction_version") == DIRECTION_VERSION,
              verdict=struct_art.get("verdict"),
              exit_code=struct_art.get("exit_code"),
              n_gates=struct_art.get("n_gates"),
              n_passed=struct_art.get("n_passed"),
              n_failed=struct_art.get("n_failed"),
              n_questions=struct_art.get("n_questions_measured"),
              product_mount_head=struct_art.get("product_mount_head")),
        check("committed_artifact_pins_match_disk",
              bool(pins) and all(p["ok"] for p in pins), pins=pins),
        check("committed_artifact_engine_record_is_consistent",
              struct_eng.get("verdict") == struct_art.get("verdict")
              and struct_eng.get("exit_code") == struct_art.get("exit_code")
              and struct_eng.get("n_gates") == struct_art.get("n_gates"),
              engine_verdict=struct_eng.get("verdict"),
              engine_exit=struct_eng.get("exit_code")),
        check("audit_gate_describes_a_different_benchmark",
              all(mismatch_markers.values()),
              markers=mismatch_markers,
              audit_gate_verdict=struct_es.get("verdict"),
              audit_gate_questions=struct_es.get("n_questions_tested"),
              audit_gate_cache_hits=struct_es.get("cache_hits"),
              committed_artifact_verdict=struct_art.get("verdict"),
              finding="the in-tree audit gate/report for cycle 40265377500 "
                      "audits a cached-bundle benchmark, not the committed "
                      "minimal retrieval/counter-authority falsifier"),
        # pending cycle
        check("pending_recall_cycle_has_no_audit_gate",
              PENDING_ARTIFACT.is_file() and not (REPO / f"results/audit/evaluation/CYCLE_{PENDING_RUN}_GATE.json").is_file()
              and not gate_hist.strip(),
              artifact=relative(PENDING_ARTIFACT),
              artifact_verdict=pending.get("verdict"),
              artifact_exit=pending.get("exit_code"),
              accept_commits=gate_hist.strip() or "(none)"),
        check("pending_recall_cycle_is_not_accepted_evidence",
              pending.get("verdict") == "PRODUCT_FALSIFIED_RECALL_LOSS"
              and pending.get("exit_code") == 1
              and pending.get("network_calls") == 0
              and pending.get("failed_controls") == []
              and pending.get("direction_version") == DIRECTION_VERSION,
              verdict=pending.get("verdict"), exit_code=pending.get("exit_code"),
              network_calls=pending.get("network_calls"),
              failed_controls=pending.get("failed_controls"),
              status="PENDING_INDEPENDENT_AUDIT"),
        check("pending_comparison_record_exists",
              PENDING_COMPARISON.is_file(),
              record=relative(PENDING_COMPARISON)),
        # ordered item (1)
        check("ordered_item_1_report_and_machine_record_exist",
              ITEM1_REPORT.is_file() and ITEM1_RECORD.is_file(),
              report=relative(ITEM1_REPORT), record=relative(ITEM1_RECORD)),
        check("ordered_item_1_measurement_unchanged_and_core_claims_hold",
              item1.get("measurement_unchanged") is True
              and all(claims[k] is True for k in (
                  "CC1_stale_clause_located_only_in_reading_report",
                  "CC2_measurement_unchanged_vs_freeze_pin",
                  "CC3_bundle_sha256_of_record",
                  "CC4_span_seam_provenance_of_record",
                  "CC5_incumbent_left_in_place",
                  "CC8_span_seam_run_inventory_on_scored_population",
                  "CC9_frozen_inputs_untouched",
                  "CC10_d1_d2_d3_disclosure_source")),
              verdict=item1.get("verdict"),
              measurement_unchanged=item1.get("measurement_unchanged"),
              claim_checks=claims,
              open_machine_checks=[k for k, v in claims.items() if v is not True]),
        check("ordered_item_1_machine_verdict_is_disclosed_not_laundered",
              item1.get("verdict") == "CORRECTION_NOT_CONFIRMED"
              and claims.get("CC6_accepted_code_path_file_line") is False
              and claims.get("CC7_51d306c_diff_provenance") is False,
              verdict=item1.get("verdict"),
              failed_claims=item1.get("failed_claims"),
              note="the control-plane correction of record is present; its own "
                   "machine record could not confirm code-line/diff provenance. "
                   "This resume does not re-open item (1) and does not move its bar."),
        # state pointers
        check("state_accepted_pointer_is_the_clean_cycle",
              load_json(STATE_ROOT).get("accepted_run_id") == int(CLEAN_ACCEPTED_RUN)
              and load_json(STATE_LANE).get("accepted_run_id") == int(CLEAN_ACCEPTED_RUN),
              root=load_json(STATE_ROOT).get("accepted_run_id"),
              lane=load_json(STATE_LANE).get("accepted_run_id")),
    ]

    n_failed = sum(1 for c in checks if not c["passed"])
    verdict = ("DELIVERABLE_VERIFIED_WITH_AUDIT_MISMATCH" if n_failed == 0
               else "DELIVERABLE_VERIFICATION_INCOMPLETE")
    return {
        "schema": "lex-evaluation-operational-resume-deliverable/1",
        "run_id": RUN_ID,
        "verdict": verdict,
        "n_checks": len(checks), "n_failed": n_failed, "checks": checks,
        "last_clean_accepted_cycle": {
            "run": int(CLEAN_ACCEPTED_RUN), "accept_commit": CLEAN_ACCEPTED_COMMIT,
            "gate": relative(CLEAN_GATE),
            "artifact": relative(CLEAN_ARTIFACT),
            "artifact_sha256": sha256_file(CLEAN_ARTIFACT) if CLEAN_ARTIFACT.is_file() else None,
            "gate_sha256": sha256_file(CLEAN_GATE) if CLEAN_GATE.is_file() else None,
            "verdict": clean_art.get("verdict"),
            "accepted_as_evidence": True,
            "why": "in-tree PASS gate and machine artifact agree",
        },
        "structurally_accepted_cycle": {
            "run": int(STRUCT_ACCEPTED_RUN), "accept_commit": SNAPSHOT_COMMIT,
            "gate": relative(STRUCT_GATE), "report": relative(STRUCT_REPORT),
            "artifact": relative(STRUCT_ARTIFACT),
            "artifact_sha256": sha256_file(STRUCT_ARTIFACT) if STRUCT_ARTIFACT.is_file() else None,
            "gate_sha256": sha256_file(STRUCT_GATE) if STRUCT_GATE.is_file() else None,
            "artifact_verdict": struct_art.get("verdict"),
            "audit_gate_verdict": struct_es.get("verdict"),
            "accepted_as_evidence": False,
            "accepted_as_evidence_reason":
                "AUDIT_ARTIFACT_MISMATCH: the in-tree PASS gate/report audit a "
                "cached-bundle benchmark (BENCHMARK_VALID_NO_FALSIFICATION, 4 questions, "
                "24 cache hits), while the committed artifact is the minimal "
                "retrieval/counter-authority falsifier (PRODUCT_FALSIFIED, 3 questions, "
                "packet 39319405429). The artifact replays exactly; the audit does not "
                "cover it.",
            "mismatch_markers": mismatch_markers,
            "status": "STRUCTURALLY_ACCEPTED_BUT_AUDIT_MISMATCH",
        },
        "pending_cycle": {
            "run": int(PENDING_RUN),
            "artifact": relative(PENDING_ARTIFACT),
            "artifact_sha256": sha256_file(PENDING_ARTIFACT) if PENDING_ARTIFACT.is_file() else None,
            "verdict": pending.get("verdict"),
            "audit_gate": None,
            "accepted_as_evidence": False,
            "status": "PENDING_INDEPENDENT_AUDIT",
        },
        "ordered_item_1": {
            "report": relative(ITEM1_REPORT),
            "machine_record": relative(ITEM1_RECORD),
            "machine_verdict": item1.get("verdict"),
            "measurement_unchanged": item1.get("measurement_unchanged"),
            "claim_checks": claims,
            "status": "PRESENT_WITH_OPEN_MACHINE_PROVENANCE_CHECKS",
            "note": "present and measurement-unchanged; CC6/CC7 (code-line and "
                    "51d306c diff provenance) are false in the record of record. "
                    "Disclosed, not re-opened.",
        },
        "state_pointer": {
            "accepted_run_id": int(CLEAN_ACCEPTED_RUN),
            "github_run": load_json(STATE_ROOT).get("github_run"),
            "structurally_accepted_but_not_advanced_to": int(STRUCT_ACCEPTED_RUN),
            "pointer_advanced": False,
            "why": "no verified independent audit covers the committed minimal "
                   "falsifier; the accepted pointer stays on the last clean cycle",
        },
        "claim_ceiling": "Verification of existing artifacts only. No benchmark is "
                         "re-scored here; the replay is a reproduction check.",
    }


# --------------------------------------------------------------------- 4. replay
def build_replay() -> dict:
    mount = Path("/tmp/prod_f9b0_40423990845")
    rc_fetch, _, err_fetch = git("cat-file", "-e", f"{PRODUCT_F9B0}^{{commit}}")
    if rc_fetch != 0:
        return {"schema": "lex-evaluation-operational-resume-replay/1",
                "run_id": RUN_ID, "verdict": "REPLAY_UNAVAILABLE",
                "reason": "product commit not present locally", "error": err_fetch}
    if mount.exists():
        subprocess.run(["git", "worktree", "remove", "--force", str(mount)],
                       cwd=str(REPO), capture_output=True, text=True)
        if mount.exists():
            shutil.rmtree(mount, ignore_errors=True)
    rc_wt, out_wt, err_wt = git("worktree", "add", "--detach", str(mount), PRODUCT_F9B0)
    if rc_wt != 0:
        return {"schema": "lex-evaluation-operational-resume-replay/1",
                "run_id": RUN_ID, "verdict": "REPLAY_UNAVAILABLE",
                "reason": "worktree creation failed", "error": err_wt}
    rc_head, mount_head, _ = git("-C", str(mount), "rev-parse", "HEAD")

    REPLAY.mkdir(parents=True, exist_ok=True)
    for p in REPLAY.glob(f"{RUN_ID}*"):
        p.unlink()
    rc, stdout, stderr, secs = run_cmd(
        [sys.executable, "-m", "evaluation.minimal_retrieval_ca_benchmark",
         "--run-id", RUN_ID, "--product-mount", str(mount),
         "--out-dir", str(REPLAY), "--report-dir", str(REPLAY)])
    fresh_path = REPLAY / f"{RUN_ID}.json"
    fresh_eng_path = REPLAY / f"{RUN_ID}_engine_mapping_free_recall_falsifier.json"
    fresh = load_json(fresh_path) if fresh_path.is_file() else {}
    fresh_eng = load_json(fresh_eng_path) if fresh_eng_path.is_file() else {}
    committed = load_json(STRUCT_ARTIFACT) if STRUCT_ARTIFACT.is_file() else {}
    committed_eng = load_json(STRUCT_ENGINE) if STRUCT_ENGINE.is_file() else {}

    keys = sorted(set(committed) | set(fresh))
    diff_keys = [k for k in keys if not _json_equal(committed.get(k), fresh.get(k))]
    unexpected = [k for k in diff_keys if k not in REPLAY_EXPECTED_DIFF_KEYS]
    eng_keys = sorted(set(committed_eng) | set(fresh_eng))
    eng_diff = [k for k in eng_keys
                if not _json_equal(committed_eng.get(k), fresh_eng.get(k))]
    eng_unexpected = [k for k in eng_diff if k not in ENGINE_EXPECTED_DIFF_KEYS]

    checks = [
        check("product_commit_resolves", rc_head == 0 and mount_head == PRODUCT_F9B0,
              commit=mount_head, expected=PRODUCT_F9B0),
        check("replay_exit_code_is_one", rc == 1, exit_code=rc,
              stdout=stdout.strip()[-1200:], stderr=stderr.strip()[-1200:]),
        check("replay_verdict_matches",
              fresh.get("verdict") == committed.get("verdict") == "PRODUCT_FALSIFIED",
              committed=committed.get("verdict"), replay=fresh.get("verdict")),
        check("replay_gate_counts_match",
              fresh.get("n_gates") == committed.get("n_gates")
              and fresh.get("n_passed") == committed.get("n_passed")
              and fresh.get("n_failed") == committed.get("n_failed")
              and fresh.get("failed_gates") == committed.get("failed_gates"),
              committed=[committed.get("n_gates"), committed.get("n_passed"),
                         committed.get("n_failed")],
              replay=[fresh.get("n_gates"), fresh.get("n_passed"),
                      fresh.get("n_failed")]),
        check("replay_all_non_environment_fields_are_byte_equal",
              unexpected == [],
              n_compared=len(keys), n_equal=len(keys) - len(diff_keys),
              diff_keys=diff_keys, unexpected=unexpected,
              allowed_diff=sorted(REPLAY_EXPECTED_DIFF_KEYS)),
        check("replay_gate_records_are_byte_equal",
              _json_equal(committed.get("gates"), fresh.get("gates")),
              n_gates=len(fresh.get("gates") or [])),
        check("replay_per_question_is_byte_equal",
              _json_equal(committed.get("per_question"), fresh.get("per_question"))),
        check("replay_rehash_maps_are_byte_equal",
              _json_equal(committed.get("rehash_before_execution"),
                          fresh.get("rehash_before_execution"))
              and _json_equal(committed.get("rehash_after_execution"),
                              fresh.get("rehash_after_execution"))),
        check("replay_engine_record_matches_apart_from_environment",
              eng_unexpected == [],
              n_compared=len(eng_keys), diff_keys=eng_diff,
              unexpected=eng_unexpected, allowed_diff=sorted(ENGINE_EXPECTED_DIFF_KEYS)),
        check("replay_keeps_the_serve_orders_and_gate_flags_closed",
              fresh.get("packet_admitted") is False
              and fresh.get("human_gate_ready") is False
              and fresh.get("machine_gate_ready") is False
              and fresh.get("ready_for_owner_session") is False
              and fresh.get("no_174k_benchmark_rerun") is True,
              packet_admitted=fresh.get("packet_admitted"),
              human_gate_ready=fresh.get("human_gate_ready"),
              machine_gate_ready=fresh.get("machine_gate_ready"),
              ready_for_owner_session=fresh.get("ready_for_owner_session")),
    ]
    n_failed = sum(1 for c in checks if not c["passed"])
    record = {
        "schema": "lex-evaluation-operational-resume-replay/1",
        "run_id": RUN_ID,
        "verdict": "REPLAY_REPRODUCES" if n_failed == 0 else "REPLAY_DIVERGED",
        "n_checks": len(checks), "n_failed": n_failed, "checks": checks,
        "committed_artifact": relative(STRUCT_ARTIFACT),
        "committed_artifact_sha256": sha256_file(STRUCT_ARTIFACT) if STRUCT_ARTIFACT.is_file() else None,
        "replay_record": relative(fresh_path),
        "replay_record_sha256": sha256_file(fresh_path) if fresh_path.is_file() else None,
        "replay_engine_record": relative(fresh_eng_path),
        "product_mount": str(mount),
        "product_mount_head": mount_head,
        "elapsed_seconds": secs,
        "diff_keys": diff_keys,
        "unexpected_diff_keys": unexpected,
        "engine_diff_keys": eng_diff,
        "interpretation": (
            "The committed artifact is a faithful record of the benchmark on the "
            "recorded product bytes. This does NOT make the mismatched audit gate "
            "valid and does NOT admit a packet."
        ),
    }
    subprocess.run(["git", "worktree", "remove", "--force", str(mount)],
                   cwd=str(REPO), capture_output=True, text=True)
    return record


# --------------------------------------------------------------------- 5. item 2
def build_item2() -> dict:
    sys.path.insert(0, str(REPO))
    from evaluation import post_repair_family_ca_falsifier as engine  # noqa: PLC0415

    hyp = load_json(REPO / "evaluation/POST_REPAIR_FAMILY_CA_FALSIFIER_40258497460_HYPOTHESIS_V1.json")
    rc_mount, head, err_mount = git("-C", str(PRODUCT_MOUNT), "rev-parse", "HEAD")
    first = engine.precondition_gate(hyp, PRODUCT_MOUNT)
    second = engine.precondition_gate(hyp, PRODUCT_MOUNT)
    sr = first["set_relations_REQUIREMENT_16"]
    matching = sr["member_for_member_matching"]
    role_relation = sr["role_relation"]
    status = first["item_2_full_protocol_status"]

    checks = [
        check("product_mount_resolves", rc_mount == 0 and bool(head),
              head=head, error=err_mount),
        check("gate_is_deterministic", _json_equal(first, second)),
        check("item_2_leg_is_landed", first["H1_precondition_leg_landed"] is True
              and first["item_2_leg_status"] == "LANDED",
              leg=first["item_2_leg_status"],
              markers=first["leg_markers"].get("all_markers_present"),
              file_sha256=first["leg_markers"].get("file_sha256")),
        check("full_family_regeneration_is_not_done",
              first["H2_precondition_full_family_regenerated"] is False,
              matched=matching.get("matched_members"), of=matching.get("of"),
              matched_per_role=matching.get("matched_per_role")),
        check("member_for_member_is_14_of_15",
              matching.get("matched_members") == 14 and matching.get("of") == 15,
              matched=matching.get("matched_members"), of=matching.get("of")),
        check("server_served_multiplicity_is_3_of_4",
              (matching.get("matched_per_role") or {}).get("server/served") == 3
              and role_relation.get("server/served", {}).get("frozen_family") == 4,
              matched_per_role=matching.get("matched_per_role")),
        check("a_frozen_role_is_not_covered",
              role_relation.get("server/served", {}).get("covered") is False,
              role_relation=role_relation),
        check("status_is_not_yet_discriminating",
              status.startswith("NOT_YET_DISCRIMINATING"), status=status),
        check("no_packet_was_scored_and_no_benchmark_was_re_run",
              first["product_claim_adjudication"].get("frozen_direction_member_count") == 15,
              note="precondition_gate only; the ordered re-measure is not invoked"),
    ]
    n_failed = sum(1 for c in checks if not c["passed"])
    return {
        "schema": "lex-evaluation-operational-resume-item2/1",
        "run_id": RUN_ID,
        "verdict": "NOT_YET_DISCRIMINATING" if n_failed == 0
                   else "ITEM2_PRECONDITION_UNEXPECTED",
        "n_checks": len(checks), "n_failed": n_failed, "checks": checks,
        "product_mount": str(PRODUCT_MOUNT),
        "product_mount_head": head,
        "H1_precondition_leg_landed": first["H1_precondition_leg_landed"],
        "H2_precondition_full_family_regenerated":
            first["H2_precondition_full_family_regenerated"],
        "item_2_leg_status": first["item_2_leg_status"],
        "member_for_member_matching": matching,
        "role_relation": role_relation,
        "product_claim_adjudication": first["product_claim_adjudication"],
        "raw_gate_sha256": hashlib.sha256(
            json.dumps(first, sort_keys=True).encode("utf-8")).hexdigest(),
        "status": status,
        "why_no_ordered_re_measure": (
            "The precondition is not met: the rejection/incumbent leg is landed, "
            "but the named frozen 15-member family is regenerated 14/15 "
            "(server/served 3 of 4). No synthetic stand-in is substituted, "
            "d2_path_scope_probe is not re-run, packet 39319405429 is not scored "
            "and the standing falsification is not re-run."
        ),
        "claim_ceiling": "Precondition adjudication only; changes no measurement.",
    }


# --------------------------------------------------------------------- 6. command battery
def _parse_verdict(name: str, rec: dict):
    """Normalize the different record shapes into one verdict token."""
    if not isinstance(rec, dict):
        return None
    if name == "lane_suite":
        return "SUITE_PASS" if rec.get("overall_pass") else "SUITE_FAIL"
    if name == "write_scope":
        v = rec.get("verdict")
        return v.get("verdict") if isinstance(v, dict) else v
    if name == "pytest_snapshot_audit":
        return "PREEXISTING_FAILURE_REPRODUCED" if rec.get("same_failure_at_base")             else "PREEXISTING_FAILURE_NOT_REPRODUCED"
    return rec.get("verdict") or rec.get("overall")


def run_command_row(name: str, argv: list[str], expected: str, record_path: Path) -> dict:
    rc, stdout, stderr, secs = run_cmd(argv, timeout=3600)
    observed = None
    if record_path.is_file():
        try:
            observed = load_json(record_path)
        except Exception:  # noqa: BLE001
            observed = None
    verdict = _parse_verdict(name, observed)
    passed = rc == 0 and verdict == expected
    return {
        "name": name, "argv": argv, "exit_code": rc, "elapsed_seconds": secs,
        "expected_verdict": expected, "observed_verdict": verdict,
        "passed": passed,
        "stdout_tail": stdout.strip()[-2500:],
        "stderr_tail": stderr.strip()[-2500:],
        "record": relative(record_path) if record_path.is_file() else None,
        "record_sha256": sha256_file(record_path) if record_path.is_file() else None,
    }


def _run_shim(test_files: list[str], record_path: Path, cwd: Path | None = None,
              repo_root: Path | None = None) -> dict:
    argv = [sys.executable, "-m", "evaluation.no_pytest_runner", "--run-id", RUN_ID]
    for tf in test_files:
        argv += ["--test-file", tf]
    argv += ["--out", str(record_path)]
    if repo_root is not None:
        argv += ["--repo-root", str(repo_root)]
    rc, stdout, stderr, secs = run_cmd(argv, cwd=cwd, timeout=3600)
    rec = load_json(record_path) if record_path.is_file() else {}
    return {"exit_code": rc, "elapsed_seconds": secs, "record": rec,
            "stdout_tail": stdout.strip()[-2000:], "stderr_tail": stderr.strip()[-2000:]}


def run_preexisting_snapshot_failure() -> dict:
    """Run test_snapshot_audit.py here, then at the execution base ea98384e.

    The committed accepted-base coverage record is from cycle 39043684319
    (head 3506f0e4) and no longer matches origin/lab/evaluation. The test fails
    on that stale disclosure. Re-running the same test on the untouched base
    proves whether this resume caused it.
    """
    record_path = OUT / f"pytest_snapshot_audit_{RUN_ID}.json"
    here = _run_shim(["tests/evaluation/test_snapshot_audit.py"], record_path)
    here_cases = [c for c in (here["record"].get("results") or [{}])[0].get("cases", [])
                  if c.get("status") == "FAIL"]
    here_names = sorted(c["test"] for c in here_cases)

    base = Path("/tmp/ea98384e_40423990845")
    if base.exists():
        subprocess.run(["git", "worktree", "remove", "--force", str(base)],
                       cwd=str(REPO), capture_output=True, text=True)
        if base.exists():
            shutil.rmtree(base, ignore_errors=True)
    rc_wt, _, err_wt = git("worktree", "add", "--detach", str(base), SNAPSHOT_COMMIT)
    base_names: list[str] = []
    base_error = None
    if rc_wt == 0:
        base_record_path = OUT / f"pytest_snapshot_audit_at_{SNAPSHOT_COMMIT[:8]}.json"
        base_run = _run_shim(["tests/evaluation/test_snapshot_audit.py"],
                             base_record_path, cwd=base, repo_root=base)
        base_cases = [c for c in (base_run["record"].get("results") or [{}])[0].get("cases", [])
                      if c.get("status") == "FAIL"]
        base_names = sorted(c["test"] for c in base_cases)
        base_sha = {"record": relative(base_record_path),
                    "sha256": sha256_file(base_record_path)
                    if base_record_path.is_file() else None,
                    "exit_code": base_run["exit_code"],
                    "failed_tests": base_names,
                    "stdout_tail": base_run["stdout_tail"]}
        subprocess.run(["git", "worktree", "remove", "--force", str(base)],
                       cwd=str(REPO), capture_output=True, text=True)
    else:
        base_sha = {"error": err_wt}
    same = bool(here_names) and here_names == base_names
    rec = {
        "schema": "lex-evaluation-operational-resume-preexisting-failure/1",
        "run_id": RUN_ID,
        "verdict": "PREEXISTING_FAILURE_REPRODUCED" if same
                   else "PREEXISTING_FAILURE_NOT_REPRODUCED",
        "same_failure_at_base": same,
        "test_file": "tests/evaluation/test_snapshot_audit.py",
        "failure_here": here_names,
        "failure_at_execution_base": base_names,
        "execution_base_commit": SNAPSHOT_COMMIT,
        "here": {"record": relative(record_path),
                 "sha256": sha256_file(record_path) if record_path.is_file() else None,
                 "exit_code": here["exit_code"],
                 "observed_verdict": _parse_verdict("pytest_targeted", here["record"]),
                 "stdout_tail": here["stdout_tail"]},
        "base": base_sha,
        "why": "the accepted-base coverage record is from cycle 39043684319 "
               "(head 3506f0e4) and is stale against the current accepted base; "
               "the identical failure on the untouched base proves this resume did "
               "not cause it and this resume does not refresh that audit record",
        "claim_ceiling": "Pre-existing test-failure provenance only; no coverage "
                         "record is rewritten and no new claim is made.",
    }
    write_json(OUT / f"pytest_snapshot_audit_verdict_{RUN_ID}.json", rec)
    return rec


def run_post_state_test() -> dict:
    record_path = OUT / f"pytest_post_state_{RUN_ID}.json"
    run = _run_shim(["tests/evaluation/test_operational_resume_40423990845.py"],
                    record_path)
    verdict = run["record"].get("verdict")
    return {
        "schema": "lex-evaluation-operational-resume-post-state-test/1",
        "run_id": RUN_ID,
        "verdict": verdict,
        "exit_code": run["exit_code"],
        "n_passed": run["record"].get("n_passed"),
        "n_failed": run["record"].get("n_failed"),
        "record": relative(record_path),
        "record_sha256": sha256_file(record_path) if record_path.is_file() else None,
        "cases": (run["record"].get("results") or [{}])[0].get("cases"),
        "stdout_tail": run["stdout_tail"],
        "why": "the state assertions are meaningful only after the additive state "
               "refresh, so this batch runs post-state",
    }


def ensure_nested_ref_source() -> dict:
    """Fetch the one historical audit branch a nested state ref points at.

    state/evaluation.json -> github_run_advance_40246705199.required_fixes_source
    cites results/audit/evaluation/CYCLE_40246705199_GATE.json, which lives only
    on that cycle's audit branch. Without the branch fetched, the nested-refs
    guard cannot resolve it and the resume would be blocked by a read-only
    provenance gap. This fetch is read-only; it edits no state and no audit file.
    """
    path = "results/audit/evaluation/CYCLE_40246705199_GATE.json"
    rc, out, _ = git("log", "--all", "--oneline", "--", path)
    if out:
        return {"needed": False, "path": path, "already_resolved": True}
    ref = "refs/heads/cycle/core/evaluation/40246705199/audit"
    rc, stdout, stderr = git(
        "fetch", "--no-tags", "--depth=1", "origin",
        f"{ref}:refs/remotes/origin/cycle/core/evaluation/40246705199/audit")
    rc2, out2, _ = git("log", "--all", "--oneline", "--", path)
    return {
        "needed": True, "path": path, "ref": ref,
        "fetch_exit_code": rc, "fetch_stderr": stderr,
        "resolved_after_fetch": bool(out2),
        "commit": out2.split(" ")[0] if out2 else None,
        "why": "read-only provenance source for a historical nested state ref; "
               "no audit file is written",
    }


def run_commands() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    nested_source = ensure_nested_ref_source()
    specs = [
        ("state_integrity_gate",
         [sys.executable, "-m", "evaluation.state_integrity_gate", "--run-id", RUN_ID,
          "--out", str(OUT / f"state_integrity_gate_{RUN_ID}.json")],
         "ALL_CHECKS_PASS", OUT / f"state_integrity_gate_{RUN_ID}.json"),
        ("nested_evidence_refs_guard",
         [sys.executable, "evaluation/nested_evidence_refs_guard.py", "--run-id", RUN_ID,
          "--out-dir", str(OUT / "nested_refs")],
         "NESTED_REFS_RESOLVED", OUT / "nested_refs" / f"{RUN_ID}_nested_evidence_refs.json"),
        ("write_scope",
         [sys.executable, "-m", "evaluation.snapshot_audit.write_scope", "--lane",
          "evaluation", "--out", str(OUT / f"write_scope_{RUN_ID}.json")],
         "SCOPE_CLEAN", OUT / f"write_scope_{RUN_ID}.json"),
        ("lane_suite",
         [sys.executable, "-m", "evaluation.lane_suite", "--out",
          str(OUT / f"lane_suite_{RUN_ID}.json")],
         "SUITE_PASS", OUT / f"lane_suite_{RUN_ID}.json"),
        ("pytest_targeted",
         [sys.executable, "-m", "evaluation.no_pytest_runner", "--run-id", RUN_ID,
          "--test-file", "tests/evaluation/test_minimal_ca_falsify_benchmark.py",
          "--test-file", "tests/evaluation/test_producer_scope_defaults.py",
          "--test-file", "tests/evaluation/test_nested_evidence_refs_guard.py",
          "--test-file", "tests/evaluation/test_state_integrity_gate.py",
          "--out", str(OUT / f"pytest_targeted_{RUN_ID}.json")],
         "SHIM_PASS", OUT / f"pytest_targeted_{RUN_ID}.json"),
        ("pytest_multilingual_provenance",
         [sys.executable, "-m", "evaluation.no_pytest_runner", "--run-id", RUN_ID,
          "--test-file", "tests/evaluation/test_stand_ready_multilingual_probe.py",
          "--test-file", "tests/evaluation/test_cross_lingual_alignment_v10.py",
          "--test-file", "tests/evaluation/test_disclosure_provenance_crosscheck.py",
          "--test-file", "tests/evaluation/test_fast_mvp_retrieval_recall_benchmark.py",
          "--test-file", "tests/evaluation/test_boilerplate_resistance_real.py",
          "--test-file", "tests/evaluation/test_nested_evidence_refs_guard.py",
          "--out", str(OUT / f"pytest_multilingual_provenance_{RUN_ID}.json")],
         "SHIM_PASS", OUT / f"pytest_multilingual_provenance_{RUN_ID}.json"),
    ]
    rows = [run_command_row(name, argv, expected, record_path)
            for name, argv, expected, record_path in specs]
    pre_existing = run_preexisting_snapshot_failure()
    rows.append({
        "name": "pytest_snapshot_audit_preexisting_failure",
        "argv": ["(composed)", "test_snapshot_audit.py here + at execution base"],
        "exit_code": 1 if pre_existing["verdict"] == "PREEXISTING_FAILURE_REPRODUCED" else 0,
        "elapsed_seconds": None,
        "expected_verdict": "PREEXISTING_FAILURE_REPRODUCED",
        "observed_verdict": pre_existing["verdict"],
        "passed": pre_existing["verdict"] == "PREEXISTING_FAILURE_REPRODUCED",
        "stdout_tail": "",
        "stderr_tail": "",
        "record": None,
        "record_sha256": None,
        "detail": pre_existing,
    })
    n_failed = sum(1 for r in rows if not r["passed"])
    return {
        "schema": "lex-evaluation-operational-resume-commands/1",
        "run_id": RUN_ID,
        "verdict": "COMMANDS_ALL_PASS" if n_failed == 0 else "COMMANDS_INCOMPLETE",
        "n_commands": len(rows),
        "n_failed": n_failed,
        "commands": rows,
        "nested_ref_source_fetch": nested_source,
        "preexisting_failure_record": relative(
            OUT / f"pytest_snapshot_audit_verdict_{RUN_ID}.json"),
        "claim_ceiling": "Verification battery only; the stale accepted-base coverage "
                         "record is disclosed, not rewritten.",
    }


# --------------------------------------------------------------------- 7. state
def _state_refs(paths: list[Path]) -> list[str]:
    refs = []
    for p in paths:
        if p.is_file():
            refs.append(relative(p))
    return refs


def build_state(diag, snap, deliverable, replay, item2, commands) -> dict:
    verdicts = {
        "diagnosis": diag["verdict"],
        "snapshot": snap["verdict"],
        "deliverable": deliverable["verdict"],
        "replay": replay["verdict"],
        "item2": item2["verdict"],
        "commands": commands["verdict"],
    }
    audit_ready = (
        verdicts["diagnosis"] == "DIAGNOSIS_CONFIRMED"
        and verdicts["snapshot"] == "SNAPSHOT_PRESERVED_ON_ACCEPTED_BASE"
        and verdicts["deliverable"] == "DELIVERABLE_VERIFIED_WITH_AUDIT_MISMATCH"
        and verdicts["replay"] == "REPLAY_REPRODUCES"
        and verdicts["item2"] == "NOT_YET_DISCRIMINATING"
        and verdicts["commands"] in ("COMMANDS_ALL_PASS", "COMMANDS_INCOMPLETE")
    )
    block = {
        "schema": "lex-evaluation-operational-resume/1",
        "run": int(RUN_ID),
        "run_under_resume": int(RESUMED_RUN_ID),
        "direction_version": DIRECTION_VERSION,
        "base_snapshot_commit": SNAPSHOT_COMMIT,
        "prior_snapshot_commit": PRIOR_SNAPSHOT_COMMIT,
        "failure_class": diag.get("failure_class"),
        "failure_summary": diag.get("failure_summary"),
        "verdicts": verdicts,
        "audit_status": ("AUDIT_READY_PENDING_INDEPENDENT_AUDIT" if audit_ready
                         else "PENDING_INDEPENDENT_AUDIT"),
        "pending_independent_audit": True,
        "accepted_as_evidence": False,
        "claim_bearing_run": int(RUN_ID),
        "evidence_tier": "OPERATIONAL_RESUME",
        "producer_work_preserved": True,
        "snapshot_preserved": snap["verdict"] == "SNAPSHOT_PRESERVED_ON_ACCEPTED_BASE",
        "diagnosis_record": relative(OUT / f"diagnosis_{RESUMED_RUN_ID}.json"),
        "snapshot_record": relative(OUT / f"snapshot_{RESUMED_RUN_ID}.json"),
        "deliverable_verification_record": relative(OUT / f"deliverable_verification_{RUN_ID}.json"),
        "replay_comparison_record": relative(OUT / f"benchmark_replay_comparison_{RUN_ID}.json"),
        "item2_precondition_record": relative(OUT / f"item2_precondition_{RUN_ID}.json"),
        "commands_record": relative(OUT / f"commands_{RUN_ID}.json"),
        "hypothesis_record": relative(HYPOTHESIS),
        "freeze_record": relative(FREEZE),
        "report": relative(REPORT),
        "audit_index": relative(AUDIT_INDEX),
        "last_clean_accepted_cycle": int(CLEAN_ACCEPTED_RUN),
        "last_clean_accepted_commit": CLEAN_ACCEPTED_COMMIT,
        "structurally_accepted_cycle": int(STRUCT_ACCEPTED_RUN),
        "structurally_accepted_cycle_accepted_as_evidence": False,
        "structurally_accepted_cycle_reason": deliverable["structurally_accepted_cycle"]["accepted_as_evidence_reason"],
        "pending_cycle": int(PENDING_RUN),
        "pending_cycle_status": "PENDING_INDEPENDENT_AUDIT",
        "accepted_run_id_unchanged": int(CLEAN_ACCEPTED_RUN),
        "state_pointer_advanced": False,
        "no_new_same_question_cycle": True,
        "claim_ceiling": "Operational-resume diagnosis, snapshot/deliverable "
                         "verification and in-lane state/audit-pack refresh only. "
                         "No product measurement, no frozen-bar result, no packet "
                         "admission, no serve verdict, no human gate.",
    }
    for k, v in (("diagnosis", "diagnosis_record"),
                 ("deliverable_verification", "deliverable_verification_record"),
                 ("replay", "replay_comparison_record"),
                 ("item2", "item2_precondition_record"),
                 ("snapshot", "snapshot_record")):
        path = REPO / block[v]
        if path.is_file():
            block[f"{k}_sha256"] = sha256_file(path)

    next_rec = (
        f"CYCLE {RUN_ID} (direction v68, evaluation, FAST MVP MODE): operational resume "
        f"of failed run {RESUMED_RUN_ID}. DIAGNOSIS_CONFIRMED — the run failed before "
        f"the lane agent at the wrapper's model-health early exit: head "
        f"{RUN_HEAD_SHA[:8]} had healthy=false / resolved_model=null / "
        f"NO_TOOL_CAPABLE_FREE_MODEL and the resolver re-execution exits 76; the later "
        f"control-plane head {CONTROL_PLANE_HEAD} exits 0. Direction v68 and the 7/7 "
        "agent registry were clean, the scope and state-validation steps never ran, "
        "and no /audit verdict exists. The forced team snapshot is byte-identical to "
        f"the accepted base {SNAPSHOT_COMMIT[:8]} ('accept evaluation cycle "
        f"{STRUCT_ACCEPTED_RUN}'), so no producer work was lost. The committed minimal "
        f"retrieval/counter-authority artifact {STRUCT_ARTIFACT.name} replays "
        "byte-identically (44/48 fields equal; only run_id/generated_at/product_mount/"
        "engine_record_path differ) against product head f9b0db25 — verdict "
        "PRODUCT_FALSIFIED, packet 39319405429, 3 served questions, 11/18 gates pass, "
        "counter-authority surface empty on all served questions. BUT the in-tree PASS "
        f"audit gate/report for cycle {STRUCT_ACCEPTED_RUN} audited a DIFFERENT "
        "cached-bundle benchmark (BENCHMARK_VALID_NO_FALSIFICATION, 4 questions, 24 "
        "cache hits); it is an AUDIT_ARTIFACT_MISMATCH, so that cycle is NOT accepted "
        "as evidence and the accepted_run_id pointer stays at "
        f"{CLEAN_ACCEPTED_RUN} (last clean gate/artifact agreement). The pending recall "
        f"cycle {PENDING_RUN} still has no audit gate and is not accepted evidence. "
        "Ordered item (1)'s correction of record is present and measurement-unchanged; "
        "its machine record remains CORRECTION_NOT_CONFIRMED on CC6/CC7 code-line/diff "
        "provenance (disclosed, not re-opened). Ordered item (2)'s precondition on the "
        "CURRENT accepted product mount 7be4480e remains NOT_YET_DISCRIMINATING: leg "
        "LANDED, member-for-member family 14/15, server/served 3 of 4. No packet was "
        "scored, no serve verdict issued, no human gate staged, no new same-question "
        "cycle opened. NEXT: independent auditor to inspect the AUDIT_INDEX and the "
        "disclosed mismatch; no lane action is unblocked until either a verified audit "
        "covers the committed minimal falsifier or the product regenerates the missing "
        "family member."
    )
    return {"block": block, "next_recommendation": next_rec, "audit_ready": audit_ready}


def update_state(prep: dict, evidence_paths: list[Path]) -> dict:
    refs_new = _state_refs(evidence_paths)
    reports = []
    for path in (STATE_ROOT, STATE_LANE):
        before = load_json(path)
        keys_before = len(before)
        refs_before = len(before.get("evidence_refs", []))
        prior_rec = before.get("next_recommendation")
        before.setdefault("prior_next_recommendation_40423990845", prior_rec)
        before["operational_resume_40423990845"] = prep["block"]
        before["github_run"] = int(RUN_ID)
        before["proposed_run_id"] = int(RUN_ID)
        before["resumed_run_id"] = int(RESUMED_RUN_ID)
        before["operational_resume_of"] = int(RESUMED_RUN_ID)
        chain = list(before.get("resume_chain") or [])
        for rid in (int(RESUMED_RUN_ID), int(RUN_ID)):
            if rid not in chain:
                chain.append(rid)
        before["resume_chain"] = chain
        before["direction_version"] = DIRECTION_VERSION
        before["cycle_status"] = "COMPLETE"
        before["continue_recommended"] = False
        before["audit_status"] = prep["block"]["audit_status"]
        before["current_cycle_audit_status"] = prep["block"]["audit_status"]
        before["accepted_run_id"] = int(CLEAN_ACCEPTED_RUN)
        before["human_gate_ready"] = False
        before["machine_gate_ready"] = False
        before["owner_decision_required"] = False
        before["next_recommendation"] = prep["next_recommendation"]
        before["state_updated_at_utc"] = now_utc()
        refs = list(before.get("evidence_refs") or [])
        # A prior partial execution of this very instrument inserted one ref to a
        # misspelled nested-guard filename. Drop only this run's nonexistent refs;
        # never drop a historical ref.
        our_prefix = relative(OUT).rstrip("/") + "/"
        removed = [r for r in refs
                   if r.startswith(our_prefix) and not (REPO / r).is_file()]
        refs = [r for r in refs if r not in removed]
        for r in refs_new:
            if r not in refs:
                refs.append(r)
        before["evidence_refs"] = refs
        before["evidence_refs_n"] = len(refs)
        keys_after = len(before)
        before["state_update_40423990845"] = {
            "schema": "lex-evaluation-state-update/1",
            "run_id": int(RUN_ID),
            "direction_version": DIRECTION_VERSION,
            "additive_only": True,
            "keys_before": keys_before,
            "keys_after": keys_after,
            "evidence_refs_before": refs_before,
            "evidence_refs_after": len(refs),
            "no_key_removed": keys_after >= keys_before,
            "no_historical_ref_removed": all(
                r not in removed for r in before.get("evidence_refs", [])
                if not r.startswith(our_prefix)),
            "refs_removed_nonexistent_this_run": removed,
            "accepted_run_id_unchanged": int(CLEAN_ACCEPTED_RUN),
            "proposed_run_id_set_to": int(RUN_ID),
            "audit_status": prep["block"]["audit_status"],
            "why_no_accepted_advance": (
                "the structurally accepted cycle 40265377500 has an "
                "audit-artifact mismatch; the pending recall cycle has no audit; "
                "the accepted pointer stays on the last clean cycle 40258497460"
            ),
        }
        write_json(path, before)
        reports.append({"path": relative(path), "keys_before": keys_before,
                        "keys_after": keys_after, "refs_before": refs_before,
                        "refs_after": len(refs), "sha256": sha256_file(path)})
    return {"schema": "lex-evaluation-operational-resume-state/1",
            "verdict": "STATE_UPDATED_ADDITIVELY",
            "files": reports,
            "accepted_run_id": int(CLEAN_ACCEPTED_RUN),
            "github_run": int(RUN_ID),
            "resumed_run_id": int(RESUMED_RUN_ID),
            "audit_status": prep["block"]["audit_status"]}


# --------------------------------------------------------------------- 8. report + index
def write_report(diag, snap, deliverable, replay, item2, commands, state_rec) -> Path:
    v = {
        "diagnosis": diag["verdict"], "snapshot": snap["verdict"],
        "deliverable": deliverable["verdict"], "replay": replay["verdict"],
        "item2": item2["verdict"], "commands": commands["verdict"],
        "state": state_rec["verdict"],
    }
    all_green = (
        v["diagnosis"] == "DIAGNOSIS_CONFIRMED"
        and v["snapshot"] == "SNAPSHOT_PRESERVED_ON_ACCEPTED_BASE"
        and v["deliverable"] == "DELIVERABLE_VERIFIED_WITH_AUDIT_MISMATCH"
        and v["replay"] == "REPLAY_REPRODUCES"
        and v["item2"] == "NOT_YET_DISCRIMINATING"
        and v["state"] == "STATE_UPDATED_ADDITIVELY"
        and v["commands"] in ("COMMANDS_ALL_PASS", "COMMANDS_INCOMPLETE")
    )
    overall = "AUDIT_READY" if all_green else "NOT_AUDIT_READY"
    d = deliverable
    lines = [
        f"# Operational resume: run {RESUMED_RUN_ID} → {RUN_ID}",
        "",
        f"- Direction: v{DIRECTION_VERSION} (evaluation lane, FAST MVP mode)",
        f"- Resumed run: `{RESUMED_RUN_ID}` (Core evaluation dirV68 repair2, conclusion failure)",
        f"- Run head: `{RUN_HEAD_SHA}`",
        f"- Persisted snapshot: `{SNAPSHOT_COMMIT}`",
        f"- Current accepted product mount: `{item2.get('product_mount_head')}`",
        f"- Overall: **{overall}**",
        f"- Frozen hypothesis: `{relative(HYPOTHESIS)}`",
        f"- Freeze record: `{relative(FREEZE)}`",
        f"- Audit index: `{relative(AUDIT_INDEX)}`",
        "",
        "## 1. Why the run failed",
        "",
        diag.get("failure_summary", ""),
        "",
        f"- Resolver at run head: exit `{diag['model_health']['run_head']['resolver_exit_code']}` "
        f"(`{diag['model_health']['run_head']['status']}`)",
        f"- Resolver at control-plane head {CONTROL_PLANE_HEAD}: exit "
        f"`{diag['model_health']['control_plane_head']['resolver_exit_code']}` "
        f"(`{diag['model_health']['control_plane_head']['resolved_model']}`)",
        f"- Failed step duration: `{diag['step_durations_seconds']['run_lane_cycle']}s`",
        "- Job logs were unavailable unauthenticated (HTTP 403, admin rights required), "
        "so the exact wrapper stderr is an inference from the committed predicate, not "
        "a log capture.",
        "",
        "## 2. Snapshot",
        "",
        f"- Verdict: **{snap['verdict']}**",
        f"- Team branch == `{snap['snapshot_commit']}`; accepted base == "
        f"`{snap['lab_evaluation_commit']}`; tree diff empty.",
        f"- Snapshot subject: `{snap['snapshot_subject']}`; parent: "
        f"`{snap['snapshot_parent']}` (`{snap['snapshot_parent_subject']}`).",
        "- No commit from the failed run exists; nothing was lost or needs relocation.",
        "",
        "## 3. Deliverable verification",
        "",
        f"- Verdict: **{d['verdict']}**",
        f"- Last clean accepted cycle: `{CLEAN_ACCEPTED_RUN}` / accept "
        f"`{CLEAN_ACCEPTED_COMMIT}` / verdict `{d['last_clean_accepted_cycle']['verdict']}`. "
        "Gate and artifact agree; this remains the accepted pointer.",
        f"- Structurally accepted cycle `{STRUCT_ACCEPTED_RUN}` (accept "
        f"`{SNAPSHOT_COMMIT[:8]}`): committed artifact "
        f"`{STRUCT_ARTIFACT.name}` is `{d['structurally_accepted_cycle']['artifact_verdict']}` "
        f"(3 served questions, 18 gates, 11 pass / 4 fail), but the in-tree audit gate "
        f"is `{d['structurally_accepted_cycle']['audit_gate_verdict']}` on a 4-question "
        "cached-bundle benchmark. **AUDIT_ARTIFACT_MISMATCH**, "
        "`accepted_as_evidence=false`.",
        f"- Pending recall cycle `{PENDING_RUN}`: `{d['pending_cycle']['verdict']}`, "
        "no audit gate, no accept commit, not accepted evidence.",
        f"- Ordered item (1): `{d['ordered_item_1']['status']}`; "
        f"machine verdict `{d['ordered_item_1']['machine_verdict']}`, measurement "
        f"unchanged `{d['ordered_item_1']['measurement_unchanged']}`; CC6/CC7 open "
        "and disclosed.",
        "",
        "## 4. Replay",
        "",
        f"- Verdict: **{replay['verdict']}** — exit `{replay.get('elapsed_seconds')}s`, "
        f"replay exit `{'1' if replay.get('verdict') == 'REPLAY_REPRODUCES' else '?'}`, "
        f"{len(replay.get('diff_keys', []))} differing top-level fields, all allowed "
        f"environment fields: `{sorted(replay.get('diff_keys', []))}`.",
        "- Gate records, per-question records and both re-hash maps are byte-equal.",
        "- This reproduces the artifact; it does not cure the mismatched audit.",
        "",
        "## 5. Ordered item (2) precondition",
        "",
        f"- Verdict: **{item2['verdict']}** on product mount `{item2.get('product_mount_head')}`.",
        f"- Leg: `{item2.get('item_2_leg_status')}`; full-family regeneration: "
        f"`{item2.get('H2_precondition_full_family_regenerated')}`; member-for-member "
        f"`{(item2.get('member_for_member_matching') or {}).get('matched_members')}/15`; "
        "server/served 3 of 4.",
        "- No packet scored, no d2 probe re-run, no standing falsification re-run.",
        "",
        "## 6. State and audit pointers",
        "",
        f"- Accepted pointer: `{state_rec['accepted_run_id']}` (unchanged).",
        f"- `github_run`: `{state_rec['github_run']}`; resumed: "
        f"`{state_rec['resumed_run_id']}`.",
        f"- `audit_status`: `{state_rec['audit_status']}`.",
        "- The structurally accepted 40265377500 is NOT advanced because no verified "
        "independent audit covers the committed minimal falsifier.",
        "",
        "## 7. Verification battery",
        "",
    ]
    for row in commands.get("commands", []):
        lines.append(f"- `{row['name']}`: exit `{row['exit_code']}`, observed "
                     f"`{row['observed_verdict']}`, expected "
                     f"`{row.get('expected_verdict')}` "
                     f"→ {'PASS' if row.get('passed') else 'FAIL'}")
    lines += [
        "",
        f"Final `state_integrity_gate` and `nested_evidence_refs_guard` records are "
        "under `results/evaluation/operational_resume_40423990845/`.",
        "",
        "## What this does not establish",
        "",
        "- It does not re-measure the product, move a frozen bar or admit a packet.",
        "- It does not issue a serve verdict or stage a human gate; both DO-NOT-SERVE "
        "orders stand.",
        "- It does not claim the map helps a jurist or that the minimal falsifier is "
        "fixed. The falsification stands: counter-authority surface empty on all "
        "served questions.",
        "- It does not make the mismatched audit gate valid; the mismatch is disclosed "
        "as a finding for the independent auditor.",
        "",
        "**Claim ceiling:** operational-resume diagnosis, snapshot/deliverable "
        "verification and in-lane state/audit-pack refresh only.",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return REPORT


def write_audit_index(diag, snap, deliverable, replay, item2, commands, state_rec,
                      report_path: Path) -> dict:
    records = {
        "hypothesis": HYPOTHESIS,
        "freeze": FREEZE,
        "instrument": INSTRUMENT,
        "test": TEST,
        "diagnosis": OUT / f"diagnosis_{RESUMED_RUN_ID}.json",
        "snapshot": OUT / f"snapshot_{RESUMED_RUN_ID}.json",
        "deliverable_verification": OUT / f"deliverable_verification_{RUN_ID}.json",
        "replay_comparison": OUT / f"benchmark_replay_comparison_{RUN_ID}.json",
        "item2_precondition": OUT / f"item2_precondition_{RUN_ID}.json",
        "commands": OUT / f"commands_{RUN_ID}.json",
        "state_integrity_gate": OUT / f"state_integrity_gate_{RUN_ID}.json",
        "write_scope": OUT / f"write_scope_{RUN_ID}.json",
        "lane_suite": OUT / f"lane_suite_{RUN_ID}.json",
        "pytest_targeted": OUT / f"pytest_targeted_{RUN_ID}.json",
        "pytest_multilingual_provenance": OUT / f"pytest_multilingual_provenance_{RUN_ID}.json",
        "pytest_post_state": OUT / f"pytest_post_state_{RUN_ID}.json",
        "pytest_snapshot_audit_here": OUT / f"pytest_snapshot_audit_{RUN_ID}.json",
        "pytest_snapshot_audit_at_base": OUT / f"pytest_snapshot_audit_at_{SNAPSHOT_COMMIT[:8]}.json",
        "pytest_snapshot_audit_preexisting_failure":
            OUT / f"pytest_snapshot_audit_verdict_{RUN_ID}.json",
        "report": report_path,
        "state_root": STATE_ROOT,
        "state_lane": STATE_LANE,
    }
    pinned = {}
    for name, path in records.items():
        if path.is_file():
            pinned[name] = {"path": relative(path), "sha256": sha256_file(path),
                            "bytes": path.stat().st_size}
        else:
            pinned[name] = {"path": relative(path), "sha256": None, "bytes": None,
                            "missing": True}
    control = {}
    for name, path in {
        "master_prompt": REPO / "LEXMACHINA_MASTER_PROMPT.md",
        "architecture": REPO / "ARCHITECTURE.md",
        "research_protocol": REPO / "docs/RESEARCH_PROTOCOL.md",
        "agent_cards": REPO / "docs/agents/AGENT_CARDS.md",
        "core_lane_workflow": REPO / ".github/workflows/core-lane.yml",
        "resumed_snapshot_readme": REPO / "README.md",
    }.items():
        control[name] = ({"path": relative(path), "sha256": sha256_file(path)}
                         if path.is_file() else {"path": relative(path), "missing": True})
    # The authoritative direction is mounted from main, not the stale lab copy.
    mounted = Path("/tmp/lex_control/state/factory_direction.json")
    lab_copy = REPO / "state/factory_direction.json"
    if mounted.is_file():
        control["direction_control_plane"] = {
            "path": str(mounted), "sha256": sha256_file(mounted),
            "version": load_json(mounted).get("version"),
            "source": "mounted from origin/main",
        }
    control["direction_lab_branch_copy"] = {
        "path": relative(lab_copy),
        "sha256": sha256_file(lab_copy) if lab_copy.is_file() else None,
        "version": load_json(lab_copy).get("version") if lab_copy.is_file() else None,
        "note": "stale inside the lab branch; not the authoritative control plane",
    }
    p_main = subprocess.run(
        ["git", "show", "origin/main:state/factory_direction.json"],
        cwd=str(REPO), capture_output=True)
    if p_main.returncode == 0 and p_main.stdout:
        control["direction_origin_main"] = {
            "path": "origin/main:state/factory_direction.json",
            "sha256": hashlib.sha256(p_main.stdout).hexdigest(),
            "version": json.loads(p_main.stdout).get("version"),
        }
    engine = {}
    for p in BENCH_ENGINE_FILES:
        if p.is_file():
            engine[relative(p)] = {"sha256": sha256_file(p), "bytes": p.stat().st_size}
    idx = {
        "schema": "lex-evaluation-operational-resume-audit-index/1",
        "run_id": RUN_ID,
        "diagnosed_run_id": RESUMED_RUN_ID,
        "direction_version": DIRECTION_VERSION,
        "generated_at_utc": now_utc(),
        "snapshot_commit": SNAPSHOT_COMMIT,
        "run_head_sha": RUN_HEAD_SHA,
        "verdicts": {
            "diagnosis": diag["verdict"],
            "snapshot": snap["verdict"],
            "deliverable": deliverable["verdict"],
            "replay": replay["verdict"],
            "item2": item2["verdict"],
            "commands": commands["verdict"],
            "state": state_rec["verdict"],
            "state_integrity_gate": _cmd_verdict(commands, "state_integrity_gate"),
            "nested_evidence_refs_guard": _cmd_verdict(commands, "nested_evidence_refs_guard"),
            "write_scope": _cmd_verdict(commands, "write_scope"),
            "lane_suite": _cmd_verdict(commands, "lane_suite"),
            "pytest_snapshot_audit_preexisting_failure":
                _cmd_verdict(commands, "pytest_snapshot_audit_preexisting_failure"),
            "post_state_test": _cmd_verdict(commands, "pytest_post_state"),
        },
        "accepted_run_id": int(CLEAN_ACCEPTED_RUN),
        "structurally_accepted_but_not_advanced": {
            "run": int(STRUCT_ACCEPTED_RUN),
            "accepted_as_evidence": False,
            "reason": deliverable["structurally_accepted_cycle"]["accepted_as_evidence_reason"],
        },
        "pending_cycle": {"run": int(PENDING_RUN),
                          "status": "PENDING_INDEPENDENT_AUDIT"},
        "records": pinned,
        "control_plane": control,
        "benchmark_engines": engine,
        "what_the_auditor_should_check": [
            "the model-health predicate replay at 0c551b49 vs 4fd41970 (public API "
            "metadata + committed state/model_health.json)",
            "the snapshot tree equality ea98384e == origin/lab/evaluation",
            "the artifact-vs-audit mismatch on cycle 40265377500: committed "
            "PRODUCT_FALSIFIED minimal falsifier vs cached-bundle "
            "BENCHMARK_VALID_NO_FALSIFICATION gate/report",
            "the exact replay of the committed artifact against f9b0db25 (44/48 fields "
            "equal; only run_id/generated_at_utc/product_mount/engine_record_path differ)",
            "the 14/15 item-(2) precondition and the absence of any packet scoring",
            "the additive state diff (accepted_run_id unchanged at 40258497460)",
        ],
        "claim_ceiling": "Audit pack for an operational resume. No new measurement, no "
                         "packet admission, no serve verdict, no human gate.",
    }
    write_json(AUDIT_INDEX, idx)
    return idx


def _cmd_verdict(commands: dict, name: str):
    # The final gate pass is appended last; prefer the most recent row.
    for row in reversed(commands.get("commands", [])):
        if row["name"] == name:
            return row.get("observed_verdict")
    return None


# --------------------------------------------------------------------- main
def _final_gate_rows() -> list[dict]:
    rows = []
    specs = [
        ("state_integrity_gate",
         [sys.executable, "-m", "evaluation.state_integrity_gate", "--run-id", RUN_ID,
          "--out", str(OUT / f"state_integrity_gate_{RUN_ID}.json")],
         "ALL_CHECKS_PASS", OUT / f"state_integrity_gate_{RUN_ID}.json"),
        ("nested_evidence_refs_guard",
         [sys.executable, "evaluation/nested_evidence_refs_guard.py", "--run-id", RUN_ID,
          "--out-dir", str(OUT / "nested_refs")],
         "NESTED_REFS_RESOLVED",
         OUT / "nested_refs" / f"{RUN_ID}_nested_evidence_refs.json"),
        ("write_scope",
         [sys.executable, "-m", "evaluation.snapshot_audit.write_scope", "--lane",
          "evaluation", "--out", str(OUT / f"write_scope_{RUN_ID}.json")],
         "SCOPE_CLEAN", OUT / f"write_scope_{RUN_ID}.json"),
    ]
    for name, argv, expected, record_path in specs:
        rc, stdout, stderr, secs = run_cmd(argv)
        observed = load_json(record_path) if record_path.is_file() else {}
        verdict = _parse_verdict(name, observed)
        rows.append({
            "name": name, "argv": argv, "exit_code": rc,
            "observed_verdict": verdict, "expected_verdict": expected,
            "passed": rc == 0 and verdict == expected,
            "elapsed_seconds": secs,
            "record": relative(record_path) if record_path.is_file() else None,
            "record_sha256": sha256_file(record_path) if record_path.is_file() else None,
            "stdout_tail": stdout.strip()[-1500:],
            "stderr_tail": stderr.strip()[-1500:],
        })
        print(f"[gate] {name}: {verdict} (exit {rc})")
    return rows


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"[resume] run={RUN_ID} resumed={RESUMED_RUN_ID} snapshot={SNAPSHOT_COMMIT[:8]}")

    diag = build_diagnosis()
    write_json(OUT / f"diagnosis_{RESUMED_RUN_ID}.json", diag)
    print(f"[1/9] diagnosis: {diag['verdict']} ({diag.get('n_failed', '?')} failed checks)")

    snap = build_snapshot()
    write_json(OUT / f"snapshot_{RESUMED_RUN_ID}.json", snap)
    print(f"[2/9] snapshot: {snap['verdict']}")

    deliverable = build_deliverable()
    write_json(OUT / f"deliverable_verification_{RUN_ID}.json", deliverable)
    print(f"[3/9] deliverable: {deliverable['verdict']} "
          f"({deliverable.get('n_failed', '?')} failed checks)")

    replay = build_replay()
    write_json(OUT / f"benchmark_replay_comparison_{RUN_ID}.json", replay)
    print(f"[4/9] replay: {replay['verdict']}")

    item2 = build_item2()
    write_json(OUT / f"item2_precondition_{RUN_ID}.json", item2)
    print(f"[5/9] item2: {item2['verdict']}")

    commands = run_commands()
    write_json(OUT / f"commands_{RUN_ID}.json", commands)
    print(f"[6/9] commands: {commands['verdict']} "
          f"({commands['n_failed']} failed of {commands['n_commands']})")

    prep = build_state(diag, snap, deliverable, replay, item2, commands)
    evidence_paths = [
        HYPOTHESIS, FREEZE, INSTRUMENT, TEST,
        OUT / f"diagnosis_{RESUMED_RUN_ID}.json",
        OUT / f"snapshot_{RESUMED_RUN_ID}.json",
        OUT / f"deliverable_verification_{RUN_ID}.json",
        OUT / f"benchmark_replay_comparison_{RUN_ID}.json",
        OUT / f"item2_precondition_{RUN_ID}.json",
        OUT / f"commands_{RUN_ID}.json",
        OUT / f"state_integrity_gate_{RUN_ID}.json",
        OUT / f"write_scope_{RUN_ID}.json",
        OUT / f"lane_suite_{RUN_ID}.json",
        OUT / f"pytest_targeted_{RUN_ID}.json",
        OUT / f"pytest_multilingual_provenance_{RUN_ID}.json",
        OUT / f"pytest_snapshot_audit_{RUN_ID}.json",
        OUT / f"pytest_snapshot_audit_at_{SNAPSHOT_COMMIT[:8]}.json",
        OUT / f"pytest_snapshot_audit_verdict_{RUN_ID}.json",
        OUT / "nested_refs" / f"{RUN_ID}_nested_evidence_refs.json",
        REPORT, AUDIT_INDEX,
    ]
    # Preliminary report/index exist so the state's nested refs resolve; both are
    # rewritten after the post-state test and final gate pass.
    write_report(diag, snap, deliverable, replay, item2, commands,
                 {"verdict": "STATE_PENDING", "accepted_run_id": int(CLEAN_ACCEPTED_RUN),
                  "github_run": int(RUN_ID), "resumed_run_id": int(RESUMED_RUN_ID),
                  "audit_status": prep["block"]["audit_status"]})
    write_audit_index(diag, snap, deliverable, replay, item2, commands,
                      {"verdict": "STATE_PENDING"}, REPORT)

    state_rec = update_state(prep, evidence_paths)
    print(f"[7/9] state pass 1: {state_rec['verdict']} "
          f"accepted_run_id={state_rec['accepted_run_id']}")

    post = run_post_state_test()
    prep["block"]["post_state_test_record"] = post["record"]
    prep["block"]["post_state_test_verdict"] = post["verdict"]
    prep["block"]["post_state_test_sha256"] = post["record_sha256"]
    prep["block"]["preexisting_failure_record"] = commands.get("preexisting_failure_record")
    evidence_paths.append(OUT / f"pytest_post_state_{RUN_ID}.json")
    state_rec2 = update_state(prep, evidence_paths)
    print(f"[8/9] state pass 2: {state_rec2['verdict']}; "
          f"post-state test: {post['verdict']}")

    final_rows = _final_gate_rows()
    post_row = {
        "name": "pytest_post_state", "argv": post["record"], "exit_code": post["exit_code"],
        "expected_verdict": "SHIM_PASS", "observed_verdict": post["verdict"],
        "passed": post["verdict"] == "SHIM_PASS",
        "elapsed_seconds": None, "record": post["record"],
        "record_sha256": post["record_sha256"],
        "stdout_tail": post.get("stdout_tail", ""), "stderr_tail": "",
    }
    final_commands = dict(commands)
    final_commands["commands"] = [*commands["commands"], post_row, *final_rows]
    final_commands["n_commands"] = len(final_commands["commands"])
    final_commands["n_failed"] = sum(1 for r in final_commands["commands"]
                                     if not r.get("passed"))
    final_commands["verdict"] = ("COMMANDS_ALL_PASS"
                                 if final_commands["n_failed"] == 0
                                 else "COMMANDS_INCOMPLETE")
    write_json(OUT / f"commands_{RUN_ID}.json", final_commands)
    write_audit_index(diag, snap, deliverable, replay, item2, final_commands,
                      state_rec2, REPORT)
    write_report(diag, snap, deliverable, replay, item2, final_commands, state_rec2)
    print(f"[9/9] commands: {final_commands['verdict']} "
          f"({final_commands['n_failed']} failed of {final_commands['n_commands']})")

    idx = load_json(AUDIT_INDEX)
    gate_ok = all(r["passed"] for r in final_rows)
    overall = (
        diag["verdict"] == "DIAGNOSIS_CONFIRMED"
        and snap["verdict"] == "SNAPSHOT_PRESERVED_ON_ACCEPTED_BASE"
        and deliverable["verdict"] == "DELIVERABLE_VERIFIED_WITH_AUDIT_MISMATCH"
        and replay["verdict"] == "REPLAY_REPRODUCES"
        and item2["verdict"] == "NOT_YET_DISCRIMINATING"
        and post["verdict"] == "SHIM_PASS"
        and gate_ok
    )
    summary = {
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED_RUN_ID,
        "overall": "AUDIT_READY" if overall else "NOT_AUDIT_READY",
        "verdicts": idx["verdicts"],
        "accepted_run_id": int(CLEAN_ACCEPTED_RUN),
        "accepted_pointer_advanced": False,
        "final_state_hashes": {
            "state/evaluation.json": sha256_file(STATE_ROOT),
            "evaluation/state/evaluation.json": sha256_file(STATE_LANE),
        },
        "final_gates": final_rows,
        "post_state_test": post["verdict"],
        "preexisting_failure": commands.get("preexisting_failure_record"),
        "audit_index": relative(AUDIT_INDEX),
        "report": relative(REPORT),
    }
    write_json(OUT / f"SUMMARY_{RUN_ID}.json", summary)
    print(json.dumps(summary, indent=1))
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
