#!/usr/bin/env python3
"""Capture a public GitHub Actions run/jobs snapshot for an operational resume.

Why this exists
---------------
Operational-resume cycles classify *why* a run stopped before an independent
audit gate from a committed raw snapshot (``schema
github-actions-run-jobs-snapshot/1``), never from memory or inference.  The
repository is public, so the run record, per-job step conclusions and the
check-run annotations are fetchable WITHOUT a token; only the job *logs*
endpoint requires admin rights and is recorded as HTTP 403 when so.

What it does
------------
* ``GET /actions/runs/<id>``            -> ``run`` block
* ``GET /actions/runs/<id>/jobs``       -> ``jobs`` block (steps included)
* ``GET /check-runs/<job_id>/annotations`` per job -> ``annotations`` map
* probes ``GET /actions/jobs/<audit_job_id>/logs`` and records the status
  (403 on a public unauthenticated fetch is an observed fact, not a guess)

It never writes ``results/audit/**``, never mints a gate, and never classifies
a mechanism: that is ``product/audit_step_diagnosis.py``'s job, run over the
snapshot this tool commits.

Usage
-----
    python3 product/fetch_run_jobs_snapshot.py --run-id 44711032839 \\
        --out results/product/orchestration/CYCLE_44711032839_run_jobs_raw.json
"""
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://api.github.com/repos/Mickalive/LexMachina"
SCHEMA = "github-actions-run-jobs-snapshot/1"
UA = {"Accept": "application/vnd.github+json",
      "User-Agent": "lexmachina-operational-resume"}


def _get(path: str) -> tuple[int, object]:
    req = urllib.request.Request(API + path, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:  # 403/404 are observed facts
        return exc.code, None


def capture(run_id: str, *, note: str = "") -> dict:
    status, run = _get(f"/actions/runs/{run_id}")
    if run is None:
        raise SystemExit(f"run {run_id} not fetchable (HTTP {status})")
    status, jobs_doc = _get(f"/actions/runs/{run_id}/jobs?per_page=20")
    if jobs_doc is None:
        raise SystemExit(f"jobs for {run_id} not fetchable (HTTP {status})")
    jobs = jobs_doc.get("jobs") or []

    annotations: dict[str, list] = {}
    logs_status = None
    for job in jobs:
        jid = str(job.get("id"))
        a_status, ann = _get(f"/check-runs/{job['id']}/annotations")
        annotations[jid] = ann if isinstance(ann, list) else []
        if job.get("name") == "audit" and logs_status is None:
            # Probe the logs endpoint the way the workflow would: the status
            # code is the record (403 = admin required on a public repo).
            req = urllib.request.Request(
                f"{API}/actions/jobs/{job['id']}/logs", headers=UA)
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    logs_status = resp.status
            except urllib.error.HTTPError as exc:
                logs_status = exc.code

    team = next((j for j in jobs if j.get("name") == "team"), {})
    audit = next((j for j in jobs if j.get("name") == "audit"), {})
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "schema": SCHEMA,
        "fetched_at": now,
        "fetched_from": f"{API}/actions/runs/{run_id}",
        "fetched_via": (
            "GitHub REST actions API (unauthenticated; public repository) by "
            "the operational-resume producer; check-run annotations from "
            "GET /check-runs/<job_id>/annotations"
        ),
        "artifact_note": note or (
            f"Raw run/jobs snapshot of run {run_id}: team job "
            f"{team.get('conclusion')}, audit job {audit.get('conclusion')}. "
            "Classification of the failure mechanism is performed by "
            "product/audit_step_diagnosis.py over THIS file, never inferred "
            "here."
        ),
        "logs_endpoint_note": (
            f"GET /actions/jobs/<audit_job_id>/logs returned HTTP "
            f"{logs_status} from the unauthenticated producer environment; "
            "annotations remain public." if logs_status is not None else
            "logs endpoint not probed (no audit job)."
        ),
        "logs_endpoint_status": logs_status,
        "run": {
            k: run.get(k) for k in (
                "id", "name", "node_id", "run_number", "run_attempt",
                "workflow_name", "head_branch", "head_sha", "event", "status",
                "conclusion", "created_at", "updated_at", "run_started_at",
                "html_url", "display_title",
            )
        },
        "jobs": jobs,
        "annotations": annotations,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--note", default="")
    args = ap.parse_args(argv)
    snap = capture(str(args.run_id), note=args.note)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snap, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    audit = next((j for j in snap["jobs"] if j.get("name") == "audit"), {})
    print(json.dumps({
        "out": str(out),
        "run_conclusion": snap["run"].get("conclusion"),
        "team_conclusion": next(
            (j.get("conclusion") for j in snap["jobs"]
             if j.get("name") == "team"), None),
        "audit_conclusion": audit.get("conclusion"),
        "logs_endpoint_status": snap["logs_endpoint_status"],
        "n_annotation_jobs": sum(1 for v in snap["annotations"].values() if v),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
