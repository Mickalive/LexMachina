#!/usr/bin/env python3
"""Persist the public run/jobs/annotation snapshot for one core-lane run.

Why this exists
---------------
Every ``audit_readiness`` profile cross-checks a resume diagnosis against a
COMMITTED public job snapshot: if the snapshot is not in the tree, the dossier
can only assert the mechanism in prose and the independent auditor has to
re-fetch it (or, when the API is unreachable or the job logs answer HTTP 403,
guess).  Those snapshots used to be produced by ad-hoc per-cycle snippets, so
the artifact existed but the *command that produced it* did not.  This module
is that command.

What it records (and what it deliberately does not)
---------------------------------------------------
* the run record, every job and every step conclusion;
* the public check-run annotations of every job (the only public carrier of
  the wrapper's ``Process completed with exit code N`` line, because the job
  LOGS endpoint answers HTTP 403 without admin rights);
* the observed status of the logs endpoint, so "logs unavailable" is evidence
  rather than an assumption;
* the free-model health record at the run's head sha and the remote lane refs,
  best effort — a failed probe is recorded as ``null`` with a reason, never as
  "no such thing".

It never writes an audit path, never mint a gate and never classifies a run:
classification belongs to :mod:`product.orchestration_evidence`.

Usage
-----
    python3 product/run_jobs_snapshot.py --run-id 45921358503 --write
    python3 product/run_jobs_snapshot.py --run-id 45921358503        # dry run
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from product.ci_run_evidence import (  # noqa: E402  (path bootstrap above)
    DEFAULT_REPO,
    RunNotFound,
    http_fetch,
)

#: Bumped only when a key is REMOVED or its meaning changes.  The committed
#: snapshots written before this module existed used the same shape, so older
#: artifacts stay valid under this schema.
SCHEMA = "product-run-jobs-snapshot/1"
DEFAULT_OUT_DIR = REPO_ROOT / "results" / "product" / "orchestration"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_json(url: str, fetch=http_fetch) -> tuple[int, Any]:
    try:
        return fetch(url)
    except Exception as exc:  # network resilience: recorded, never fatal
        return 0, {"error": repr(exc)}


def observe_jobs_payload(run_id: int | str, repo: str = DEFAULT_REPO,
                         fetch=http_fetch) -> tuple[int, Any]:
    """The FULL jobs payload (steps included), not just name -> conclusion."""
    return fetch_json(
        f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/jobs?per_page=100",
        fetch,
    )


def collect_annotations(jobs: list[dict], repo: str = DEFAULT_REPO,
                        fetch=http_fetch) -> dict[str, list[dict]]:
    """``{job id: [annotation, ...]}`` for every job of the run.

    Keyed by job id rather than job name so a re-run of the same job name
    cannot silently merge two jobs' evidence.
    """
    out: dict[str, list[dict]] = {}
    for job in jobs:
        job_id = job.get("id")
        if not job_id:
            continue
        status, payload = fetch_json(
            f"https://api.github.com/repos/{repo}/check-runs/{job_id}/annotations"
            "?per_page=100",
            fetch,
        )
        out[str(job_id)] = payload if status == 200 and isinstance(payload, list) else []
    return out


def observe_logs_endpoint(run_id: int | str, repo: str = DEFAULT_REPO,
                          fetch=http_fetch) -> dict[str, Any]:
    url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/logs"
    status, _ = fetch_json(url, fetch)
    return {
        "url": url,
        "observed_status": status,
        "log_text_available": status == 200,
    }


def observe_model_health(head_sha: str | None, repo: str = DEFAULT_REPO,
                         fetch=http_fetch) -> dict[str, Any] | None:
    if not head_sha:
        return None
    url = (f"https://raw.githubusercontent.com/{repo}/{head_sha}/"
           "state/model_health.json")
    status, payload = fetch_json(url, fetch)
    if status != 200 or not isinstance(payload, dict):
        return None
    return payload


def observe_remote_refs(run_id: int | str, lane: str = "product",
                        repo: str = DEFAULT_REPO) -> dict[str, str]:
    """Remote lane refs at diagnosis time.  ``""`` means absent, not unknown."""
    out: dict[str, str] = {}
    try:
        proc = subprocess.run(  # noqa: S603
            ["git", "ls-remote", "--heads",
             f"https://github.com/{repo}", f"refs/heads/lab/{lane}"],
            capture_output=True, text=True, timeout=45, check=False,
        )
        out[f"lab_{lane}"] = (proc.stdout.split()[0] if proc.returncode == 0
                              and proc.stdout.split() else "")
    except Exception:  # network resilience: recorded as unknown below
        out[f"lab_{lane}"] = ""
    for suffix in ("", "-attempt-1"):
        ref = f"refs/heads/cycle/core/{lane}/{run_id}/team{suffix}"
        key = f"team{suffix}_{run_id}"
        try:
            proc = subprocess.run(  # noqa: S603
                ["git", "ls-remote", "--heads",
                 f"https://github.com/{repo}", ref],
                capture_output=True, text=True, timeout=45, check=False,
            )
            out[key] = (proc.stdout.split()[0] if proc.returncode == 0
                        and proc.stdout.split() else "")
        except Exception:
            out[key] = ""
    out[f"audit_{run_id}"] = ""
    try:
        proc = subprocess.run(  # noqa: S603
            ["git", "ls-remote", "--heads", f"https://github.com/{repo}",
             f"refs/heads/cycle/core/{lane}/{run_id}/audit"],
            capture_output=True, text=True, timeout=45, check=False,
        )
        if proc.returncode == 0 and proc.stdout.split():
            out[f"audit_{run_id}"] = proc.stdout.split()[0]
    except Exception:
        pass
    return out


def build_snapshot(run_id: int | str, *, repo: str = DEFAULT_REPO,
                   lane: str = "product", fetch=http_fetch) -> dict[str, Any]:
    """Assemble the committed snapshot.  Never raises on a probe failure."""
    source_urls = [
        f"https://api.github.com/repos/{repo}/actions/runs/{run_id}",
        f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/jobs?per_page=100",
    ]
    status, run_payload = fetch_json(
        f"https://api.github.com/repos/{repo}/actions/runs/{run_id}", fetch)
    if status == 404:
        raise RunNotFound(f"run {run_id} is not resolvable (HTTP 404)")
    if status != 200 or not isinstance(run_payload, dict):
        raise RuntimeError(f"GitHub API returned HTTP {status} for run {run_id}")

    j_status, jobs_payload = observe_jobs_payload(run_id, repo=repo, fetch=fetch)
    jobs = (jobs_payload or {}).get("jobs") if isinstance(jobs_payload, dict) else None
    jobs = jobs if isinstance(jobs, list) else []
    for job in jobs:
        source_urls.append(
            f"https://api.github.com/repos/{repo}/check-runs/{job.get('id')}/annotations")

    annotations = collect_annotations(jobs, repo=repo, fetch=fetch)
    head_sha = run_payload.get("head_sha")
    return {
        "schema": SCHEMA,
        "run_id": str(run_id),
        "fetched_at": _now(),
        "fetched_via": ("unauthenticated GitHub REST API through "
                        "product.run_jobs_snapshot.http_fetch"),
        "source_urls": source_urls,
        "run": {
            "id": run_payload.get("id"),
            "name": run_payload.get("name"),
            "run_number": run_payload.get("run_number"),
            "event": run_payload.get("event"),
            "status": run_payload.get("status"),
            "conclusion": run_payload.get("conclusion"),
            "created_at": run_payload.get("created_at"),
            "updated_at": run_payload.get("updated_at"),
            "head_branch": run_payload.get("head_branch"),
            "head_sha": head_sha,
            "head_commit_message": ((run_payload.get("head_commit") or {})
                                    .get("message")),
        },
        "jobs": [
            {
                "id": job.get("id"),
                "name": job.get("name"),
                "status": job.get("status"),
                "conclusion": job.get("conclusion"),
                "started_at": job.get("started_at"),
                "completed_at": job.get("completed_at"),
                "steps": [
                    {
                        "number": step.get("number"),
                        "name": step.get("name"),
                        "conclusion": step.get("conclusion"),
                        "started_at": step.get("started_at"),
                        "completed_at": step.get("completed_at"),
                    }
                    for step in job.get("steps") or []
                ],
            }
            for job in jobs
        ],
        "annotations": annotations,
        "jobs_endpoint_status": j_status,
        "logs_endpoint": observe_logs_endpoint(run_id, repo=repo, fetch=fetch),
        "model_health_at_dispatch": observe_model_health(head_sha, repo=repo,
                                                         fetch=fetch),
        "remote_refs_at_diagnosis": observe_remote_refs(run_id, lane=lane,
                                                        repo=repo),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--lane", default="product")
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--out", default=None,
                    help="default: results/product/orchestration/"
                         "CYCLE_<run_id>_run_jobs_raw.json")
    ap.add_argument("--write", action="store_true",
                    help="write the artifact (default: dry run)")
    args = ap.parse_args(argv)

    snapshot = build_snapshot(args.run_id, repo=args.repo, lane=args.lane)
    text = json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n"
    if args.write:
        out = Path(args.out) if args.out else (
            DEFAULT_OUT_DIR / f"CYCLE_{args.run_id}_run_jobs_raw.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"wrote {out}", file=sys.stderr)
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
