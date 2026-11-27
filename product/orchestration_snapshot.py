#!/usr/bin/env python3
"""Fetch a public GitHub Actions run/jobs snapshot for a product operational resume.

Why this exists
---------------
Operational-resume cycles need to distinguish an audit quantum death, a producer
step failure, a scope violation and an unobserved stop.  Those verdicts must be
derived from the run's own public job record, not from prose.  This instrument
writes the bounded ``github-actions-run-jobs-snapshot/1`` artifact the
audit-readiness profiles consume, including check-run annotations when the public
endpoint serves them and the HTTP status of the logs endpoint when it does not.

It is read-only with respect to GitHub and writes only a product-owned artifact.
It never writes an auditor-namespace path, mint a gate or score a frozen bar.

Usage
-----
    python3 product/orchestration_snapshot.py --run-id 45965956701 \\
        --out results/product/orchestration/CYCLE_45965956701_run_jobs_raw.json
"""
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "github-actions-run-jobs-snapshot/1"
DEFAULT_REPO = "Mickalive/LexMachina"
USER_AGENT = "lexmachina-operational-resume/1"


def _get(url: str) -> tuple[int, Any]:
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json",
                 "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, None


def _seconds(start: str | None, end: str | None) -> float:
    if not start or not end:
        return 0.0
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    a = datetime.strptime(start, fmt).replace(tzinfo=timezone.utc)
    b = datetime.strptime(end, fmt).replace(tzinfo=timezone.utc)
    return float(int((b - a).total_seconds()))


def build_snapshot(run_id: str, repo: str = DEFAULT_REPO,
                   note: str = "") -> dict[str, Any]:
    base = f"https://api.github.com/repos/{repo}"
    run_url = f"{base}/actions/runs/{run_id}"
    jobs_url = f"{run_url}/jobs?per_page=100"
    logs_url = f"{run_url}/logs"

    status_run, run_body = _get(run_url)
    status_jobs, jobs_body = _get(jobs_url)
    if status_run != 200 or status_jobs != 200:
        raise SystemExit(
            f"public run/jobs record unavailable: run={status_run} jobs={status_jobs}")

    # The logs endpoint is usually closed to an unauthenticated producer.  Its
    # status is recorded, never upgraded into a log-line claim.
    logs_status, _ = _get(logs_url)

    run = {
        k: (run_body or {}).get(k)
        for k in ("id", "node_id", "head_sha", "run_attempt", "event",
                  "status", "conclusion", "workflow_id", "display_title",
                  "created_at", "updated_at")
    }
    jobs: list[dict[str, Any]] = []
    annotation_statuses: dict[str, int] = {}
    annotations: dict[str, Any] = {}
    for raw_job in (jobs_body or {}).get("jobs") or []:
        steps = []
        for raw_step in raw_job.get("steps") or []:
            step = dict(raw_step)
            step["seconds"] = _seconds(step.get("started_at"),
                                       step.get("completed_at"))
            steps.append(step)
        jobs.append({
            "id": raw_job.get("id"),
            "name": raw_job.get("name"),
            "status": raw_job.get("status"),
            "conclusion": raw_job.get("conclusion"),
            "started_at": raw_job.get("started_at"),
            "completed_at": raw_job.get("completed_at"),
            "seconds": _seconds(raw_job.get("started_at"),
                                raw_job.get("completed_at")),
            "html_url": raw_job.get("html_url"),
            "steps": steps,
        })
        if raw_job.get("check_run_url"):
            astatus, abody = _get(f"{raw_job['check_run_url']}/annotations")
            annotation_statuses[str(raw_job.get("name"))] = astatus
            if astatus == 200:
                annotations[str(raw_job.get("name"))] = abody

    return {
        "schema": SCHEMA,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fetched_from": run_url,
        "fetched_via": (
            "public GitHub REST actions API, read by an operational-resume "
            "producer; no authenticated log or check-run content is claimed"),
        "artifact_note": note,
        "logs_endpoint_status": logs_status,
        "annotations_endpoint_status": annotation_statuses.get("audit"),
        "annotations_endpoint_statuses": annotation_statuses,
        "annotations": annotations.get("audit", []),
        "run": run,
        "jobs": jobs,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--note", default="")
    args = ap.parse_args(argv)
    doc = build_snapshot(args.run_id, repo=args.repo, note=args.note)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(json.dumps({
        "out": str(out),
        "run": doc["run"]["id"],
        "conclusion": doc["run"]["conclusion"],
        "jobs": {j["name"]: j["conclusion"] for j in doc["jobs"]},
        "logs_endpoint_status": doc["logs_endpoint_status"],
        "annotations_endpoint_status": doc["annotations_endpoint_status"],
        "annotation_messages": [a.get("message") for a in doc["annotations"]],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
