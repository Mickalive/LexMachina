#!/usr/bin/env python3
"""Capture a committed ``github-actions-run-jobs-snapshot/1`` for one core-lane run.

Why this exists
---------------
Every operational-resume cycle needs the same first artefact: a *raw* run/jobs
snapshot of the run that stopped before an audit gate, because
:mod:`product.audit_step_diagnosis` classifies an orchestration failure from a
committed snapshot rather than from prose.  Until now that snapshot was typed in
by hand each cycle, which is exactly how a hand-edited conclusion gets published.

This module makes the capture one reproducible command:

* reads the same three public endpoints the lane already knows how to read
  (``actions/runs``, ``actions/runs/<id>/jobs`` and ``check-runs/<id>/annotations``
  - the ones :func:`product.orchestration_evidence.observe_annotations` uses)
  with :data:`product.ci_run_evidence.DEFAULT_REPO` as the default repository;
* attaches the workflow's persisted runner credentials when they are present so
  the job-logs endpoint is observed rather than guessed, and stays a public-API
  fetch when they are not;
* records ``fetched_via``, ``fetched_at`` and the exact endpoint it read, so a
  later reader can tell a captured fact from an inference.

It NEVER writes ``results/audit/**``, never mints a gate and never labels a run
accepted, rejected or adjudicated.  It only stores what the API answered.

Usage
-----
    python3 product/fetch_run_snapshot.py --run-id 46125190884 \\
        --out results/product/orchestration/CYCLE_46125190884_run_jobs_raw.json

    # offline/unit mode: feed a captured payload, no network
    python3 product/fetch_run_snapshot.py --run-id 1 --payload payload.json \\
        --out /tmp/snap.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from product.ci_run_evidence import DEFAULT_REPO  # noqa: E402

SCHEMA = "github-actions-run-jobs-snapshot/1"
Fetch = Callable[[str], tuple[int, Any]]

#: Run fields the classifier and the dossier actually read.  Kept as an explicit
#: allow-list so an API field addition never silently widens the artefact.
RUN_FIELDS = (
    "id", "node_id", "head_sha", "head_branch", "run_attempt", "event",
    "status", "conclusion", "workflow_id", "workflow_name", "display_title",
    "created_at", "updated_at", "path",
)
JOB_FIELDS = (
    "id", "run_id", "name", "status", "conclusion", "started_at",
    "completed_at",
)
STEP_FIELDS = (
    "name", "status", "conclusion", "number", "started_at", "completed_at",
)


class _AuthSafeRedirect(urllib.request.HTTPRedirectHandler):
    """Follow redirects like curl: never forward Authorization cross-host.

    ``actions/jobs/<id>/logs`` answers ``302`` to an Azure blob URL.  Forwarding
    the GitHub token there makes Azure answer ``401/403`` and hides the fact that
    the logs really are downloadable, so the observed status would be wrong in
    exactly the direction that matters for a diagnosis.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is None:
            return None
        old_host = urllib.parse.urlparse(req.full_url).netloc
        new_host = urllib.parse.urlparse(newurl).netloc
        if old_host and new_host and old_host != new_host:
            for store in (new.headers, new.unredirected_hdrs):
                for key in list(store):
                    if key.lower() == "authorization":
                        store.pop(key)
        return new


def _credential_configs() -> list[Path]:
    """Git configs where the workflow checkout stores its API credential."""
    dirs: list[Path] = []
    temp = os.environ.get("RUNNER_TEMP")
    if temp:
        dirs.append(Path(temp))
    # The runner's workspace temp dir, independent of RUNNER_TEMP.
    dirs.append(Path("/home/runner/work/_temp"))
    seen: set[Path] = set()
    out: list[Path] = []
    for directory in dirs:
        if directory in seen or not directory.is_dir():
            continue
        seen.add(directory)
        out.extend(sorted(directory.glob("git-credentials-*.config")))
    return out


def _runner_credentials() -> str | None:
    """Return the ``AUTHORIZATION`` extraheader the workflow checkout installed.

    GitHub Actions stores it as a basic-auth extraheader in a per-workspace git
    config.  The header is used only to build an in-process request: it is
    never printed and never written to a repository file.
    """
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        return f"Bearer {token}"
    for cfg in _credential_configs():
        try:
            text = cfg.read_text(encoding="utf-8", errors="replace")
        except OSError:  # pragma: no cover - unreadable temp file
            continue
        match = re.search(r"extraheader\s*=\s*AUTHORIZATION:\s*(.+)", text)
        if match:
            # Return the header VALUE only (``basic <b64>``); the caller sets
            # the ``Authorization`` header name itself.
            return match.group(1).strip()
    return None


def _build_fetch() -> tuple[Fetch, dict[str, Any]]:
    """Authenticated-or-public fetch returning ``(status, payload)``."""
    auth = _runner_credentials()
    meta = {"authenticated": bool(auth),
            "source": ("runner_persisted_credentials" if auth
                       and not (os.environ.get("GH_TOKEN")
                                or os.environ.get("GITHUB_TOKEN"))
                       else "token_env" if auth else "public_api")}

    def fetch(url: str, timeout: float = 25.0) -> tuple[int, Any]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "lexmachina-run-snapshot",
        }
        if auth:
            headers["Authorization"] = auth
        request = urllib.request.Request(url, headers=headers)
        opener = urllib.request.build_opener(_AuthSafeRedirect())
        try:
            with opener.open(request, timeout=timeout) as response:  # noqa: S310
                body = response.read().decode("utf-8", errors="replace")
                status = response.status
        except urllib.error.HTTPError as exc:
            return exc.code, {}
        except Exception as exc:  # noqa: BLE001 - recorded, never fatal
            return 0, {"error": f"{type(exc).__name__}: {exc}"}
        try:
            return status, json.loads(body)
        except json.JSONDecodeError:
            return status, {"_non_json": True, "_bytes": len(body)}

    return fetch, meta


def _probe_logs(fetch: Fetch, url: str) -> int | None:
    """HTTP status of the job-logs endpoint, without keeping the body."""
    status, _ = fetch(url)
    return status if status else None


def build_snapshot(run_id: int | str, repo: str = DEFAULT_REPO,
                   fetch: Fetch | None = None) -> dict[str, Any]:
    """Assemble the snapshot from live API responses (network)."""
    if fetch is None:
        fetch, auth_meta = _build_fetch()
    else:
        auth_meta = {"authenticated": None, "source": "injected_fetch"}
    run_status, run_payload = fetch(
        f"https://api.github.com/repos/{repo}/actions/runs/{run_id}")
    if run_status != 200 or not isinstance(run_payload, dict):
        raise SystemExit(f"cannot read run {run_id}: HTTP {run_status}")
    jobs_status, jobs_payload = fetch(
        f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/jobs"
        "?per_page=100")
    if jobs_status != 200 or not isinstance(jobs_payload, dict):
        raise SystemExit(f"cannot read jobs for {run_id}: HTTP {jobs_status}")

    jobs_out: list[dict[str, Any]] = []
    annotations: dict[str, list[dict[str, Any]]] = {}
    logs_status: int | None = None
    for job in jobs_payload.get("jobs") or []:
        if not isinstance(job, dict):
            continue
        row = {key: job.get(key) for key in JOB_FIELDS}
        row["steps"] = [
            {key: step.get(key) for key in STEP_FIELDS}
            for step in (job.get("steps") or []) if isinstance(step, dict)
        ]
        jobs_out.append(row)
        job_id = job.get("id")
        if not job_id:
            continue
        ann_status, ann_payload = fetch(
            f"https://api.github.com/repos/{repo}/check-runs/{job_id}/annotations"
            "?per_page=100")
        if ann_status == 200 and isinstance(ann_payload, list):
            annotations[str(job_id)] = [
                {"level": a.get("level"),
                 "message": (a.get("message") or "").strip(),
                 "annotation_level": a.get("annotation_level")}
                for a in ann_payload if isinstance(a, dict)
            ]
        # Observe the logs endpoint on the first job that actually failed;
        # a successful job's logs are not what a diagnosis needs.
        if logs_status is None and job.get("conclusion") == "failure":
            logs_status = _probe_logs(
                fetch, f"https://api.github.com/repos/{repo}/actions/jobs/"
                       f"{job_id}/logs")

    return {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"),
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fetched_from": (f"https://api.github.com/repos/{repo}/actions/runs/"
                         f"{run_id}"),
        "fetched_via": (
            "product/fetch_run_snapshot.py --run-id "
            f"{run_id} (GitHub REST actions API; {auth_meta['source']})"),
        "auth": auth_meta,
        "http_status": {"run": run_status, "jobs": jobs_status},
        "logs_endpoint_status": logs_status,
        "artifact_note": (
            "Raw public run/jobs snapshot for an operationally failed "
            f"core-lane run {run_id}.  Captured verbatim by "
            "product/fetch_run_snapshot.py; no conclusion, annotation or "
            "mechanism is inferred here."
        ),
        "run": {key: run_payload.get(key) for key in RUN_FIELDS},
        "jobs": jobs_out,
        "annotations": annotations,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--out", required=True)
    ap.add_argument("--payload", default=None,
                    help="previously captured {run, jobs, annotations} "
                         "payload; skips the network")
    args = ap.parse_args(argv)

    if args.payload:
        source = json.loads(Path(args.payload).read_text(encoding="utf-8"))
        snapshot = {
            "schema": SCHEMA,
            "generated_at": datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"),
            "fetched_at": source.get("fetched_at"),
            "fetched_from": source.get(
                "fetched_from",
                f"https://api.github.com/repos/{args.repo}/actions/runs/"
                f"{args.run_id}"),
            "fetched_via": source.get("fetched_via", "supplied --payload"),
            "auth": {"authenticated": None, "source": "supplied_payload"},
            "http_status": source.get("http_status"),
            "logs_endpoint_status": source.get("logs_endpoint_status"),
            "artifact_note": source.get(
                "artifact_note", "payload-supplied raw run/jobs snapshot"),
            "run": {key: source.get("run", {}).get(key) for key in RUN_FIELDS},
            "jobs": source.get("jobs"),
            "annotations": source.get("annotations"),
        }
    else:
        snapshot = build_snapshot(args.run_id, repo=args.repo)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(json.dumps({
        "out": str(out),
        "run_id": snapshot["run"].get("id"),
        "conclusion": snapshot["run"].get("conclusion"),
        "jobs": [j.get("name") for j in snapshot.get("jobs") or []],
        "annotated_jobs": sorted(snapshot.get("annotations") or {}),
        "logs_endpoint_status": snapshot.get("logs_endpoint_status"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
