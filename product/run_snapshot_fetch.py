#!/usr/bin/env python3
"""Capture a public GitHub Actions run/jobs/annotation snapshot.

Why this exists
---------------
Operational resumes in this lane are required to diagnose an orchestration
failure from committed evidence, not from a narrative.  Earlier cycles did that
by fetching the public REST endpoints with a throwaway script and committing the
result as ``CYCLE_<run>_run_jobs_raw.json``.  The throwaway nature caused exactly
the defect this module removes: run 42794322956 regenerated its raw snapshot
after writing its diagnosis and its self-test, leaving a diagnosis that pinned a
sha the committed raw no longer had.

This module is the reproducible capture step.  It fetches:

* the run object, jobs (including step conclusions/timings) for a primary run
  and any number of history runs;
* the public check-run annotations for every captured job (attributed by
  check-run id == job id);
* the chain-of-record blocks the resume diagnosis and audit-readiness dossier
  consume.

It writes only ``product-run-jobs-raw/2`` JSON.  It does not classify, does not
write a gate and makes no product claim; ``audit_step_diagnosis`` and
``resume_snapshot_diagnosis`` do the interpretation.

Usage
-----
    python3 product/run_snapshot_fetch.py \\
        --run-id 42808654760 --history-run-id 42798377691 \\
        --fetched-by-run 42809155715 \\
        --out results/product/orchestration/CYCLE_42808654760_run_jobs_raw.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
DEFAULT_REPO = os.environ.get("LEX_GITHUB_REPO", "Mickalive/LexMachina")
SCHEMA = "product-run-jobs-raw/2"

Fetch = Callable[[str], tuple[int, Any]]
ATTRIBUTION_NOTE = (
    "Annotations are attributed by check-run id == job id; each block belongs "
    "to exactly one job."
)
CLAIM_CEILING = (
    "Orchestration facts only: job/step conclusions, timings and public "
    "check-run annotations. Writes no gate and makes no product or legal claim."
)

_RUN_FIELDS = (
    "id", "name", "status", "conclusion", "head_branch", "head_sha", "path",
    "event", "created_at", "updated_at", "run_number", "check_suite_id",
    "html_url",
)
_JOB_FIELDS = (
    "id", "name", "status", "conclusion", "started_at", "completed_at",
    "html_url", "check_run_id", "check_suite_id", "run_id",
)
_STEP_FIELDS = (
    "name", "status", "conclusion", "number", "started_at", "completed_at",
)


def _http_fetch(url: str, timeout: float = 20.0) -> tuple[int, Any]:
    """Indirection so tests can inject a deterministic fetcher."""
    from product.ci_run_evidence import http_fetch
    return http_fetch(url, timeout=timeout)


def _pick(payload: dict, fields: tuple[str, ...]) -> dict:
    return {key: payload.get(key) for key in fields}


def _run_summary(payload: dict) -> dict:
    return _pick(payload, _RUN_FIELDS)


def _job_summary(payload: dict) -> dict:
    out = _pick(payload, _JOB_FIELDS)
    out["steps"] = [_pick(step, _STEP_FIELDS) for step in payload.get("steps") or []]
    return out


def _annotations(job: dict, *, repo: str, fetch: Fetch) -> list[list[str]]:
    job_id = job.get("id")
    if not job_id:
        return []
    status, payload = fetch(
        f"https://api.github.com/repos/{repo}/check-runs/{job_id}/annotations"
        "?per_page=100"
    )
    if status != 200 or not isinstance(payload, list):
        return []
    rows: list[list[str]] = []
    for item in payload:
        if isinstance(item, dict) and item.get("message") is not None:
            rows.append([str(item.get("annotation_level") or ""),
                         str(item["message"])])
        elif isinstance(item, (list, tuple)) and item:
            rows.append([str(item[0]), str(item[-1])])
        elif isinstance(item, str):
            rows.append(["", item])
    return rows


def _failed_skipped(job: dict) -> tuple[list[str], list[str]]:
    failed, skipped = [], []
    for step in job.get("steps") or []:
        if step.get("conclusion") == "failure":
            failed.append(str(step.get("name")))
        elif step.get("conclusion") == "skipped":
            skipped.append(str(step.get("name")))
    return failed, skipped


def _annotation_messages(annotations: list[list[str]]) -> list[str]:
    return [row[-1] for row in annotations if row]


def _order_runs(runs: dict[str, dict]) -> list[dict]:
    return sorted(
        runs.values(),
        key=lambda row: (row.get("created_at") or "", int(row.get("id") or 0)),
    )


def build_snapshot(
    primary_run_id: int | str,
    *,
    fetched_by_run: int | str,
    history_run_ids: tuple[int | str, ...] = (),
    fetch: Fetch | None = None,
    repo: str = DEFAULT_REPO,
    fetched_at: str | None = None,
    chain_note: str | None = None,
) -> dict[str, Any]:
    """Fetch and return the canonical raw run/jobs snapshot.

    The primary run owns ``run``/``jobs``/``check_run_annotations_by_job_id``
    because the diagnosis classifies exactly that run.  History runs are
    included only in ``runs`` and ``chain_of_record``.  A history run that no
    longer resolves (HTTP 404 after housekeeper pruning) is recorded in
    ``fetch_failures`` and skipped; the primary run must resolve.
    """
    fetch = fetch or _http_fetch
    primary = int(primary_run_id)
    requested: list[int] = []
    for run_id in (*history_run_ids, primary_run_id):
        rid = int(run_id)
        if rid not in requested:
            requested.append(rid)

    runs: dict[str, dict] = {}
    jobs_by_run: dict[str, list[dict]] = {}
    annotations_by_run_job: dict[str, dict[str, list[list[str]]]] = {}
    fetch_failures: list[dict] = []

    for rid in requested:
        status, payload = fetch(
            f"https://api.github.com/repos/{repo}/actions/runs/{rid}"
        )
        if status != 200 or not isinstance(payload, dict):
            if rid == primary:
                raise RuntimeError(f"cannot fetch primary run {rid}: HTTP {status}")
            fetch_failures.append({"run_id": rid, "what": "run", "status": status})
            continue
        runs[str(rid)] = _run_summary(payload)
        status, jobs_payload = fetch(
            f"https://api.github.com/repos/{repo}/actions/runs/{rid}/jobs?per_page=100"
        )
        if status != 200 or not isinstance(jobs_payload, dict):
            fetch_failures.append({"run_id": rid, "what": "jobs", "status": status})
            jobs_by_run[str(rid)] = []
            annotations_by_run_job[str(rid)] = {}
            continue
        jobs = [_job_summary(job) for job in jobs_payload.get("jobs") or []]
        jobs_by_run[str(rid)] = jobs
        annotations_by_run_job[str(rid)] = {
            str(job.get("id")): _annotations(job, repo=repo, fetch=fetch)
            for job in jobs
        }

    ordered = _order_runs(runs)
    primary_key = str(primary)
    primary_run = runs[primary_key]
    primary_jobs = jobs_by_run.get(primary_key, [])
    primary_annotations = annotations_by_run_job.get(primary_key, {})

    annotation_blocks: dict[str, dict] = {}
    for job in primary_jobs:
        job_id = str(job.get("id"))
        annotation_blocks[job_id] = {
            "job_name": job.get("name"),
            "run_id": job.get("run_id"),
            "conclusion": job.get("conclusion"),
            "annotations": primary_annotations.get(job_id, []),
            "started": job.get("started_at"),
            "completed": job.get("completed_at"),
        }

    chain_of_record: list[dict] = []
    for run in ordered:
        rid = str(run.get("id"))
        jobs_block: dict[str, dict] = {}
        for job in jobs_by_run.get(rid, []):
            failed, skipped = _failed_skipped(job)
            jobs_block[str(job.get("name"))] = {
                "conclusion": job.get("conclusion"),
                "failed_steps": failed,
                "skipped_steps": skipped,
                "annotations": _annotation_messages(
                    annotations_by_run_job.get(rid, {}).get(str(job.get("id")), [])
                ),
            }
        chain_of_record.append({
            "run_id": int(rid),
            "conclusion": run.get("conclusion"),
            "head_sha": run.get("head_sha"),
            "jobs": jobs_block,
        })

    if chain_note is None:
        chain_note = (
            "Fetched by run_snapshot_fetch.py from the same public "
            "unauthenticated REST endpoints as the per-job snapshot; "
            "annotations are attributed per job id."
        )

    return {
        "schema": SCHEMA,
        "fetched_at": fetched_at or datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "fetched_by_run": int(fetched_by_run),
        "source": (
            f"https://api.github.com/repos/{repo}/actions/runs/{primary} "
            "(public REST, unauthenticated)"
        ),
        "runs": runs,
        "run": primary_run,
        "jobs": primary_jobs,
        "check_run_annotations_by_job_id": annotation_blocks,
        "attribution_note": ATTRIBUTION_NOTE,
        "claim_ceiling": CLAIM_CEILING,
        "chain_of_record": chain_of_record,
        "chain_note": chain_note,
        "fetch_failures": fetch_failures,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--history-run-id", action="append", default=[],
                    help="additional run id for runs/chain_of_record (repeatable)")
    ap.add_argument("--fetched-by-run", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--chain-note", default=None)
    args = ap.parse_args(argv)

    snapshot = build_snapshot(
        args.run_id,
        fetched_by_run=args.fetched_by_run,
        history_run_ids=tuple(args.history_run_id),
        chain_note=args.chain_note,
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(json.dumps({
        "out": str(out),
        "schema": snapshot["schema"],
        "run_id": snapshot["run"]["id"],
        "jobs": len(snapshot["jobs"]),
        "chain_runs": len(snapshot["chain_of_record"]),
        "fetch_failures": snapshot["fetch_failures"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
