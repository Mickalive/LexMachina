#!/usr/bin/env python3
"""Measure the audit-starvation dispatch ledger for one core-lane run population.

    python -m evaluation.quantum_death_ledger --run-id <run_id> [--capture]

WHY THIS MODULE EXISTS
======================
Direction v56 states this lane's blocker plainly: the audit job is gated on
``needs.team.result == 'success'``, and producer steps die. Every diagnosis of
that class already recorded on this branch is the POST_DELIVERY variant -- the
producer wrote its whole deliverable and was killed at ~2703-2704 s by the work
quantum before it could exit 0 (``orchestration_diagnosis_39064497606.json`` F4,
``..._39072968899.json``, ``..._39076123103.json``, ``..._39092033997.json``).

Run 39134286491 is a different measured class and the difference is not a matter
of degree. Its producer step also ran 2704 s and failed, but the workflow's OWN
``Persist team snapshot`` step (core-lane.yml:146-161 -- ``git switch -C``,
``git add -A``, ``git commit ... || true``, ``git push --force``) SUCCEEDED and
left both ``cycle/core/evaluation/39134286491/team`` and its ``team-attempt-1``
sibling at ``904aff83``, byte-identical to the accepted lane head. ``git add -A``
found nothing to stage, so the persisted snapshot carries ZERO delta. Calling that
"post-delivery" would aim the control-plane remedy at the wrong half of the
population.

WHAT IT MEASURES (and what it does NOT)
=======================================
For each run id in a population frozen BEFORE execution it records:

* the team job's step-6 duration and conclusion (public REST ``/jobs``);
* whether the producer created a commit at all, read from the persisted team
  ref's head commit subject, and that commit's file list;
* whether the audit job RAN, and whether a gate of record exists on origin;
* the resulting classification under the definitions frozen in
  ``evaluation/QUANTUM_DEATH_LEDGER_HYPOTHESIS.json``.

It never adjudicates a packet, never moves a frozen bar, never re-runs any frozen
instrument, and never edits a rubric, threshold, benchmark or recorded verdict.

TWO MEASUREMENT CORRECTIONS THIS MODULE CARRIES, BOTH DISCLOSED
==============================================================
1. ``audit_ran`` reads the audit job's ``conclusion``, NOT its ``status``. GitHub
   reports a SKIPPED job as ``status=completed, conclusion=skipped``; a
   status-based predicate therefore reports every skipped audit as having run.
   The first execution of this instrument on 2026-10-18 used the status-based
   predicate and is WRONG on that column for every run in the population; its
   figures are preserved in ``superseded_first_execution`` of the record.
2. The persisted-tree facts are read from GIT, not from the REST commit
   endpoint. The unauthenticated public REST API allows 60 requests/hour and was
   exhausted (HTTP 403, ``remaining=0``) during the first execution; a ledger
   whose tree column depends on that endpoint is not reproducible. The commit
   subject and file list are properties of the same remote git objects, so the
   git route measures the same fact without the rate limit.

NETWORK
=======
``--capture`` reads the public unauthenticated REST API once and writes a raw
envelope under ``results/evaluation/orchestration/``. A later run with no flag
REPLAYS that committed envelope and needs no network at all, so the verdict is
re-derivable offline and byte-identically. Job logs are HTTP 403 without admin
rights and are never requested; every statement about WHY a step ended is
therefore an INFERENCE from measured duration arithmetic plus the persisted
tree, and is labelled as such in the record.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "lex-evaluation-quantum-death-ledger/1"

HYPOTHESIS_PATH = "evaluation/QUANTUM_DEATH_LEDGER_HYPOTHESIS.json"
CAPTURE_DIR = "results/evaluation/orchestration"
REPO = "Mickalive/LexMachina"
API = "https://api.github.com"

#: The producer step, by its literal workflow step name (core-lane.yml:104).
PRODUCER_STEP = "Run lane cycle"

#: The work quantum recorded in factory-wide requirement 10 for the deaths this
#: ledger re-measures. A failed step at >= this duration is a quantum death; the
#: arithmetic, not a log line, is the evidence.
QUANTUM_SECONDS = 2700


# --------------------------------------------------------------------------- git


def _git(args, cwd, timeout=120):
    try:
        return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True,
                              text=True, timeout=timeout, check=False)
    except Exception:  # pragma: no cover - environment dependent
        return None


def resolve_team_head(run_id: str, repo_root: Path):
    out = _git(["ls-remote", "origin", f"refs/heads/cycle/core/evaluation/{run_id}/team"],
               repo_root)
    if out is None or out.returncode != 0:
        return None, "git ls-remote failed"
    parts = out.stdout.strip().split()
    if not parts:
        return None, "team ref absent on origin"
    return parts[0], None


def ensure_object(sha: str, repo_root: Path) -> bool:
    if _git(["cat-file", "-e", f"{sha}^{{commit}}"], repo_root).returncode == 0:
        return True
    _git(["fetch", "--no-tags", "--depth=1", "origin", sha], repo_root)
    return _git(["cat-file", "-e", f"{sha}^{{commit}}"], repo_root).returncode == 0


def measure_persisted_tree(run_id: str, repo_root: Path) -> dict:
    """Read the producer commit, or its ABSENCE, from the persisted team ref."""
    res: dict = {"team_ref": f"cycle/core/evaluation/{run_id}/team"}
    head, err = resolve_team_head(run_id, repo_root)
    if head is None:
        res.update(available=False, unavailable=err or "team ref unresolvable")
        return res
    res["team_head"] = head
    if not ensure_object(head, repo_root):
        res.update(available=False, unavailable="team head object not fetchable")
        return res
    res["available"] = True
    res["source"] = "git object read from origin (not REST) -- see module docstring correction 2"

    subject = _git(["log", "-1", "--format=%s", head], repo_root).stdout.strip()
    res["head_commit_subject"] = subject
    res["head_commit_authored_at"] = _git(["log", "-1", "--format=%aI", head],
                                          repo_root).stdout.strip()
    res["head_commit_committer"] = _git(["log", "-1", "--format=%cn <%ce>", head],
                                        repo_root).stdout.strip()
    res["head_commit_parent"] = _git(["log", "-1", "--format=%P", head],
                                     repo_root).stdout.strip().split()[:1]
    res["head_commit_matches_workflow_template"] = subject.startswith(
        f"evaluation cycle {run_id}")
    res["delta_basis"] = ("files changed by the head commit against its FIRST parent; this is "
                          "not the delta over the lane base the dispatch started from")
    res["producer_commit_present"] = res["head_commit_matches_workflow_template"]
    if res["producer_commit_present"]:
        files = [f for f in _git(
            ["show", "--pretty=format:", "--name-only", head], repo_root
        ).stdout.splitlines() if f.strip()]
        res["persisted_delta_file_count"] = len(files)
        res["persisted_delta_files"] = files
    else:
        res["persisted_delta_file_count"] = 0
        res["persisted_delta_files"] = []
        res["reading"] = ("the persist step's 'git add -A' staged nothing and its "
                          "'git commit ... || true' was a no-op: the persisted snapshot is "
                          "the lane base itself, so this run delivered no durable delta")
    return res


# --------------------------------------------------------------------------- rest


def _rest(path: str, timeout=30.0):
    req = urllib.request.Request(API + path, headers={
        "Accept": "application/vnd.github+json", "User-Agent": "lex-evaluation-ledger"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, None
    except Exception:
        return None, None


def _ts(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _duration_s(start, end):
    a, b = _ts(start), _ts(end)
    return None if (a is None or b is None) else int((b - a).total_seconds())


def capture_rest(run_ids, repo_root: Path, out_dir: Path) -> dict:
    """Capture the public REST job facts once; they become committed evidence."""
    out_dir.mkdir(parents=True, exist_ok=True)
    envelope = {"schema": SCHEMA + "-raw-capture/1", "repo": REPO,
                "captured_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "runs": {}, "http": {}}
    for rid in run_ids:
        entry = {}
        status, run = _rest(f"/repos/{REPO}/actions/runs/{rid}")
        envelope["http"][f"runs/{rid}"] = status
        entry["run_status"] = status
        if status == 200 and run:
            entry["run"] = {k: run.get(k) for k in
                            ("name", "event", "conclusion", "head_sha", "run_attempt",
                             "created_at", "updated_at")}
        status, jobs = _rest(f"/repos/{REPO}/actions/runs/{rid}/jobs?per_page=100")
        envelope["http"][f"jobs/{rid}"] = status
        entry["jobs_status"] = status
        if status == 200 and jobs:
            entry["jobs"] = [{"name": j.get("name"), "status": j.get("status"),
                              "conclusion": j.get("conclusion"),
                              "started_at": j.get("started_at"),
                              "completed_at": j.get("completed_at"),
                              "steps": [{"number": s.get("number"), "name": s.get("name"),
                                         "conclusion": s.get("conclusion"),
                                         "started_at": s.get("started_at"),
                                         "completed_at": s.get("completed_at")}
                                        for s in (j.get("steps") or [])]}
                             for j in jobs.get("jobs", [])]
        envelope["runs"][rid] = entry
        print(f"  captured {rid}: run HTTP {entry['run_status']}, jobs HTTP {entry['jobs_status']}")
    path = out_dir / "rest_job_capture.json"
    path.write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return envelope


def load_capture(repo_root: Path, run_ids) -> dict | None:
    path = repo_root / CAPTURE_DIR / "rest_job_capture.json"
    if not path.exists():
        return None
    env = json.loads(path.read_text(encoding="utf-8"))
    return env if all(r in env.get("runs", {}) for r in run_ids) else None


def measure_job_facts(rid: str, entry: dict | None) -> dict:
    """Job/step facts from a captured envelope. UNMEASURED is never a negative."""
    out = {"run_id": rid}
    if entry is None or entry.get("run_status") != 200:
        out["facts_available"] = False
        out["unavailable"] = f"run envelope HTTP {entry.get('run_status') if entry else 'ABSENT'}"
        return out
    out["facts_available"] = True
    out.update({f"run_{k}": v for k, v in (entry.get("run") or {}).items()})
    jobs = entry.get("jobs") or []
    out["audit_ran"] = any(j.get("name") == "audit"
                           and j.get("conclusion") in ("success", "failure") for j in jobs)
    out["integrate_ran"] = any(j.get("name") == "integrate"
                               and j.get("conclusion") in ("success", "failure") for j in jobs)
    audit = next((j for j in jobs if j.get("name") == "audit"), None)
    out["audit_job"] = ({k: audit.get(k) for k in ("status", "conclusion")}
                        if audit else {"status": "ABSENT_FROM_RUN"})
    team = next((j for j in jobs if j.get("name") == "team"), None)
    step6 = None
    if team:
        step6 = next((s for s in (team.get("steps") or []) if s.get("name") == PRODUCER_STEP), None)
    if step6 is None:
        out["producer_step"] = {"available": False,
                                "note": "team job or producer step absent from the envelope"}
    else:
        out["producer_step"] = {
            "available": True,
            "conclusion": step6.get("conclusion"),
            "started_at": step6.get("started_at"),
            "completed_at": step6.get("completed_at"),
            "duration_s": _duration_s(step6.get("started_at"), step6.get("completed_at")),
        }
    return out


# ---------------------------------------------------------------------- classify


def resolve_attempt_ref(run_id: str, repo_root: Path):
    """Supplementary: the workflow also force-pushes an -attempt-N sibling ref."""
    out = _git(["ls-remote", "origin", f"refs/heads/cycle/core/evaluation/{run_id}/team-attempt-*"],
               repo_root)
    refs = {}
    if out is not None and out.returncode == 0:
        for line in out.stdout.strip().splitlines():
            parts = line.split()
            if len(parts) == 2:
                refs[parts[1].rsplit("/", 1)[-1]] = parts[0]
    return refs


def classify(run: dict) -> str:
    if not run.get("facts_available"):
        return "NOT_CLASSIFIED"
    step = run.get("producer_step") or {}
    tree = run.get("persisted_tree") or {}
    if not (step.get("available") and tree.get("available")):
        return "NOT_CLASSIFIED"
    quantum = (step.get("conclusion") == "failure"
               and (step.get("duration_s") or 0) >= QUANTUM_SECONDS)
    if quantum and tree.get("producer_commit_present"):
        return "POST_DELIVERY_QUANTUM_DEATH"
    if quantum and not tree.get("producer_commit_present"):
        return "ZERO_DELTA_QUANTUM_DEATH"
    if step.get("conclusion") == "failure":
        return "OTHER_FAILURE"
    return "PRODUCER_SUCCESS"


def gate_ref_exists(run_id: str, repo_root: Path) -> bool:
    out = _git(["ls-remote", "origin", f"refs/heads/cycle/core/evaluation/{run_id}/audit"],
               repo_root)
    return bool(out and out.returncode == 0 and out.stdout.strip())


def execute(run_id: str, repo_root: Path, envelope: dict) -> dict:
    hyp = json.loads((repo_root / HYPOTHESIS_PATH).read_text(encoding="utf-8"))
    population = list(hyp["population_frozen"]["run_ids"])
    rows = []
    for rid in population:
        run = measure_job_facts(rid, envelope.get("runs", {}).get(rid))
        run["persisted_tree"] = measure_persisted_tree(rid, repo_root)
        run["gate_ref_on_origin"] = gate_ref_exists(rid, repo_root)
        run["classification"] = classify(run)
        run["attempt_refs_on_origin"] = resolve_attempt_ref(rid, repo_root)
        rows.append(run)

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["classification"]] = counts.get(row["classification"], 0) + 1

    deaths = [r for r in rows if r["classification"].endswith("QUANTUM_DEATH")]
    supported = (counts.get("POST_DELIVERY_QUANTUM_DEATH", 0) >= 1
                 and counts.get("ZERO_DELTA_QUANTUM_DEATH", 0) >= 1
                 and all(r.get("audit_ran") is False for r in deaths))
    return {
        "schema": SCHEMA,
        "lane": "evaluation",
        "run_id": run_id,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_path": HYPOTHESIS_PATH,
        "rest_capture_path": f"{CAPTURE_DIR}/rest_job_capture.json",
        "frozen_population_n": len(population),
        "frozen_population": population,
        "quantum_seconds": QUANTUM_SECONDS,
        "producer_step_name": PRODUCER_STEP,
        "measurement_corrections": {
            "audit_ran_reads_conclusion_not_status": (
                "GitHub reports a SKIPPED job as status=completed, conclusion=skipped. The "
                "first execution used the status predicate and is WRONG on audit_ran for "
                "every run; see superseded_first_execution."),
            "persisted_tree_read_from_git_not_rest": (
                "the unauthenticated public REST API allows 60 requests/hour and returned "
                "HTTP 403 (remaining=0) during the first execution; the same commit subject "
                "and file list are read from the origin git object instead."),
        },
        "superseded_first_execution": {
            "produced_at_utc": "2026-10-18T14:59:00Z",
            "h1_verdict": "REFUTED",
            "classification_counts": {"POST_DELIVERY_QUANTUM_DEATH": 1,
                                     "ZERO_DELTA_QUANTUM_DEATH": 1,
                                     "PRODUCER_SUCCESS": 10, "NOT_CLASSIFIED": 2},
            "why_superseded": ("the audit_ran column was computed from job STATUS, so all 14 "
                               "runs reported audit_ran=true including the 4 quantum deaths "
                               "whose audit job was SKIPPED; and the persisted-tree column "
                               "depended on the rate-limited REST commit endpoint, which left "
                               "2 of 14 runs NOT_CLASSIFIED. Both columns are re-measured "
                               "here. The four classification labels that were correct then "
               " (39104154685 POST_DELIVERY, 39106938175 ZERO_DELTA) are unchanged."),
            "preserved": True,
        },
        "rows": rows,
        "classification_counts": counts,
        "column_limitations": {
            "persisted_delta_files_measure": (
                "files changed by the persisted team ref's HEAD COMMIT against its first "
                "parent. It is NOT the delta over the lane base the dispatch started from, "
                "and it must not be read as one."),
            "rows_where_the_delta_column_is_uninformative": [
                {"run_id": r["run_id"],
                 "reason": ("head commit subject does not match the workflow template "
                            f"'evaluation cycle {r['run_id']} repair N' (core-lane.yml:159); "
                            "the agent authored its own subject, so producer_commit_present "
                            "reads false even though the run delivered"),
                 "head_commit_subject": r["persisted_tree"].get("head_commit_subject"),
                 "classification": r["classification"],
                 "affects_h1": False,
                 "why_affects_h1_false": (
                     "the flag is only consulted on the failed-step branch; this row's "
                     "producer step concluded success, so its classification is PRODUCER_"
                     "SUCCESS regardless")}
                for r in rows
                if r["persisted_tree"].get("available")
                and not r["persisted_tree"].get("head_commit_matches_workflow_template")
                and r["classification"] == "PRODUCER_SUCCESS"
            ],
            "rows_whose_head_commit_is_a_whole_tree": [
                {"run_id": r["run_id"], "file_count": r["persisted_tree"].get(
                    "persisted_delta_file_count"),
                 "head_commit_parent": r["persisted_tree"].get("head_commit_parent"),
                 "reason": ("a file count of this size against one parent is consistent with "
                            "a head whose first parent is a different base than the lane "
                            "head; it is FLAGGED and NOT reconciled to a lane-base delta "
                            "here")}
                for r in rows
                if (r["persisted_tree"].get("persisted_delta_file_count") or 0) > 100
            ],
        },
        "success_rule": hyp["success_rule_frozen"]["rule"],
        "h1_verdict": "SUPPORTED" if supported else "REFUTED",
        "claim_ceiling": (
            "MEASURED-OPERATIONS ONLY. This ledger classifies dispatches of ONE core lane "
            "under ONE direction version inside ONE day from the public REST job envelope and "
            "the persisted team refs on origin. It is not a benchmark, it adjudicates no "
            "packet, it moves no frozen bar or threshold, it accepts no Frontier verdict, it "
            "does not change human_gate_ready, and it certifies nothing about jurist "
            "usefulness. Job logs are HTTP 403 unauthenticated and were never read, so every "
            "statement about WHY a producer step ended is an inference from the measured "
            "duration arithmetic plus the persisted tree, never a read log line."
        ),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--capture", action="store_true",
                    help="capture the public REST job envelope, then measure")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    hyp = json.loads((repo_root / HYPOTHESIS_PATH).read_text(encoding="utf-8"))
    run_ids = list(hyp["population_frozen"]["run_ids"])

    envelope = None if args.capture else load_capture(repo_root, run_ids)
    if envelope is None:
        print(f"capturing public REST job envelope for {len(run_ids)} runs ...")
        envelope = capture_rest(run_ids, repo_root, repo_root / CAPTURE_DIR)
    else:
        print(f"replaying committed REST envelope {CAPTURE_DIR}/rest_job_capture.json")

    record = execute(args.run_id, repo_root, envelope)
    measured = sum(1 for r in record["rows"] if r.get("facts_available"))
    if measured == 0:
        print(json.dumps(record, indent=2, sort_keys=True))
        return 2

    out = Path(args.out) if args.out else repo_root / (
        f"{CAPTURE_DIR}/{args.run_id}_quantum_death_ledger.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"quantum-death ledger: {record['h1_verdict']}  {record['classification_counts']}")
    for row in record["rows"]:
        step = row.get("producer_step") or {}
        print(f"  {row['run_id']}  {row['classification']:<28} step6={step.get('duration_s')}s "
              f"{step.get('conclusion')} audit_ran={row.get('audit_ran')} "
              f"delta_files={row['persisted_tree'].get('persisted_delta_file_count')}")
    print(f"record: {out}")
    return 0 if record["h1_verdict"] == "SUPPORTED" else 1


if __name__ == "__main__":
    sys.exit(main())