#!/usr/bin/env python3
"""Capture a public GitHub Actions run/jobs snapshot for orchestration diagnosis.

Why this exists
---------------
Operational resumes repeatedly need the same read-only facts about a failed
run: which job died, which step failed, whether the always-run persist step
published a tree, and what the public check-run annotations say.  Job *logs*
are admin-only (HTTP 403), but the run/jobs REST endpoints and the check-run
annotations are public.  Hand-copying those payloads is how the committed
snapshots drifted in shape between cycles.

This module makes the capture reproducible:

* ``build_snapshot`` is a pure function of already-fetched payloads, so every
  shape it publishes is unit-testable without network;
* ``fetch_snapshot`` performs the three unauthenticated GETs through the
  existing :mod:`product.ci_run_evidence` HTTP layer (no token, no logs);
* annotations are grouped by job id in the shape
  :mod:`product.audit_step_diagnosis` reads.

It writes no gate, asserts no cause, and labels no run accepted/rejected.

Usage
-----
    python3 product/capture_run_snapshot.py --run-id 40427889739 \\
        --out results/product/orchestration/CYCLE_40427889739_run_jobs_raw.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from product.ci_run_evidence import (  # noqa: E402
    DEFAULT_REPO,
    http_fetch,
)
from product.orchestration_evidence import observe_annotations  # noqa: E402

SCHEMA = "github-actions-run-jobs-snapshot/1"
RUN_KEYS = (
    "id", "name", "display_title", "event", "status", "conclusion",
    "created_at", "updated_at", "head_sha", "head_branch", "html_url",
)
STEP_KEYS = (
    "number", "name", "status", "conclusion", "started_at", "completed_at",
)
ANNOTATION_KEYS = ("job", "job_conclusion", "annotation_level", "message")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _project(row: dict, keys: tuple[str, ...]) -> dict[str, Any]:
    return {key: row.get(key) for key in keys if key in row}


def _jobs(payload: dict) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for job in payload.get("jobs") or []:
        if not isinstance(job, dict):
            continue
        row = _project(job, (
            "id", "name", "status", "conclusion", "started_at",
            "completed_at", "html_url",
        ))
        row["steps"] = [
            _project(step, STEP_KEYS)
            for step in job.get("steps") or []
            if isinstance(step, dict)
        ]
        out.append(row)
    return out


def _annotations(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        job_id = row.get("job_id")
        if job_id is None:
            continue
        out.setdefault(str(job_id), []).append(
            _project(row, ANNOTATION_KEYS))
    return out


def _logs_note(status: int | None) -> str:
    if status == 403:
        return (
            "Job logs require repository admin rights; the unauthenticated "
            "download returned HTTP 403. Step conclusions and public check-run "
            "annotations are observed; the log-level cause is not."
        )
    if status == 200:
        return (
            "The logs endpoint answered HTTP 200 for this capture; the byte "
            "stream is not stored in this snapshot. Only public step and "
            "annotation records are committed."
        )
    return (
        f"The logs endpoint answered HTTP {status}; no log body is stored. "
        "Only public step and annotation records are committed."
    )


def build_snapshot(
    run_payload: dict[str, Any],
    jobs_payload: dict[str, Any],
    annotation_rows: list[dict[str, Any]] | None,
    *,
    logs_status: int | None,
    source: str,
    fetched_at: str | None = None,
) -> dict[str, Any]:
    """Pure assembly of the committed snapshot shape."""
    run = _project(run_payload, RUN_KEYS)
    return {
        "schema": SCHEMA,
        "fetched_at": fetched_at or _now(),
        "source": source,
        "logs_endpoint_status": logs_status,
        "logs_endpoint_note": _logs_note(logs_status),
        "run": run,
        "jobs": _jobs(jobs_payload),
        "annotations": _annotations(annotation_rows or []),
    }


def fetch_snapshot(
    run_id: int | str,
    *,
    repo: str = DEFAULT_REPO,
    fetch: Callable[[str], tuple[int, dict]] = http_fetch,
) -> dict[str, Any]:
    """Fetch the public run/jobs/annotations record (never the log bodies)."""
    base = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}"
    run_status, run_payload = fetch(base)
    if run_status != 200 or not isinstance(run_payload, dict):
        raise RuntimeError(f"run {run_id} -> HTTP {run_status}")
    jobs_status, jobs_payload = fetch(f"{base}/jobs?per_page=100")
    if jobs_status != 200 or not isinstance(jobs_payload, dict):
        raise RuntimeError(f"run {run_id} jobs -> HTTP {jobs_status}")
    logs_status, _ = fetch(f"{base}/logs")
    annotations = observe_annotations(run_id, repo=repo, fetch=fetch)
    return build_snapshot(
        run_payload,
        jobs_payload,
        annotations,
        logs_status=logs_status,
        source=base,
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    snapshot = fetch_snapshot(args.run_id, repo=args.repo)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    jobs = [(j.get("name"), j.get("conclusion")) for j in snapshot["jobs"]]
    print(json.dumps({
        "out": str(out),
        "run": snapshot["run"].get("id"),
        "conclusion": snapshot["run"].get("conclusion"),
        "jobs": jobs,
        "logs_endpoint_status": snapshot["logs_endpoint_status"],
        "annotation_jobs": sorted(snapshot["annotations"]),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
