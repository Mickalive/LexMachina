#!/usr/bin/env python3
"""Capture the *public* GitHub Actions run/jobs record for one core-lane run.

Why this exists
---------------
Every operational-resume cycle in this lane needs to answer "why did the run
stop before an independent gate?".  The diagnosis modules
(:mod:`product.audit_step_diagnosis`, :mod:`product.resume_snapshot_diagnosis`)
only answer that from a **committed** run/jobs snapshot; they deliberately never
guess a mechanism they cannot observe.  Capturing the snapshot therefore has to
be a repeatable product step, not a one-off hand fetch.

What it records (all public, unauthenticated):
  * the run record (status/conclusion/name/head_sha);
  * every job with its steps (name/status/conclusion/numbers);
  * the public check-run annotations of failing jobs - GitHub exposes these
    without admin rights even when the *logs* endpoint needs authentication, so
    "lane crossed protected scope: exit code 3" and "LEX_WORK_QUANTUM_EXPIRED"
    become observed evidence instead of speculation;
  * the honest HTTP status of the job-logs endpoint, so a later report can say
    exactly which surface was readable.

What it never does: invent a cause, write ``results/audit/**``, mint a gate, or
label a run accepted/rejected.

Usage
-----
    python3 product/fetch_run_jobs_snapshot.py --run-id 44683121773 \\
        --fetched-by-run 44683945698 \\
        --out results/product/orchestration/CYCLE_44683121773_run_jobs_raw.json
"""
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_REPO = "Mickalive/LexMachina"
HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "lexmachina-product-snapshot/1.0",
}
API = "https://api.github.com"


def _get(url: str, timeout: float = 25.0):
    """Return ``(status, payload)``.  ``payload`` is ``None`` on any failure."""
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            try:
                return resp.status, json.loads(body)
            except ValueError:
                return resp.status, None
    except urllib.error.HTTPError as exc:  # 403/404/... are data, not crashes
        return exc.code, None
    except Exception as exc:  # network/DNS/timeout -> record, never guess
        return f"{type(exc).__name__}", None


def capture(run_id: int, repo: str = DEFAULT_REPO) -> dict:
    base = f"{API}/repos/{repo}/actions/runs/{run_id}"
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    run_status, run = _get(base)
    jobs_status, jobs_doc = _get(base + "/jobs?per_page=100")
    jobs = list((jobs_doc or {}).get("jobs") or [])

    annotations: dict[str, list] = {}
    for job in jobs:
        if job.get("conclusion") in ("success", "skipped", None):
            continue
        check_url = job.get("check_run_url")
        if not check_url:
            continue
        st, ann = _get(check_url + "/annotations")
        if isinstance(ann, list):
            annotations[str(job.get("id"))] = [
                {
                    "annotation_level": a.get("annotation_level"),
                    "message": a.get("message"),
                    "path": a.get("path"),
                    "start_line": a.get("start_line"),
                    "raw_details": a.get("raw_details"),
                }
                for a in ann
                if isinstance(a, dict)
            ]

    # The logs endpoint is deliberately probed but never required: it answers
    # 401/403 for unauthenticated callers on this repository, which is exactly
    # why annotations + step conclusions are the durable evidence surface.
    logs_status, _ = _get(base + "/logs", timeout=15.0)

    return {
        "schema": "github-run-jobs-snapshot/1",
        "source": f"{base}/jobs",
        "fetched_by_run": None,  # filled by main()
        "fetched_at": fetched_at,
        "authenticated": False,
        "run_id": run_id,
        "run_http_status": run_status,
        "jobs_http_status": jobs_status,
        "logs_endpoint_status": logs_status,
        "logs_endpoint_note": (
            "job-logs endpoint probed unauthenticated; a non-200 status means "
            "job log bodies are not part of the evidence surface and the "
            "diagnosis must rest on run/jobs/annotations only"
        ),
        "run": run,
        "jobs": jobs,
        "annotations": annotations,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", required=True, type=int)
    ap.add_argument("--fetched-by-run", required=True, type=int)
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    snap = capture(args.run_id, args.repo)
    if not snap["run"]:
        print(
            json.dumps(
                {
                    "error": "run record unreachable",
                    "run_http_status": snap["run_http_status"],
                }
            )
        )
        return 2
    snap["fetched_by_run"] = args.fetched_by_run

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snap, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")

    steps_failed = [
        s.get("name")
        for j in snap["jobs"]
        for s in (j.get("steps") or [])
        if s.get("conclusion") == "failure"
    ]
    print(json.dumps({
        "out": str(out),
        "run_id": snap["run_id"],
        "conclusion": (snap["run"] or {}).get("conclusion"),
        "jobs": {j.get("name"): j.get("conclusion") for j in snap["jobs"]},
        "failed_steps": steps_failed,
        "annotation_messages": [
            m for msgs in snap["annotations"].values() for m in
            [a.get("message") for a in msgs]
        ],
        "logs_endpoint_status": snap["logs_endpoint_status"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
