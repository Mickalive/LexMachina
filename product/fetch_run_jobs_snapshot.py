#!/usr/bin/env python3
"""Capture a public GitHub Actions run/jobs snapshot for an operational resume.

Why this exists
---------------
Every operational resume of this lane has to answer "why did the previous run
stop before a gate?".  The answer has to come from a *committed* snapshot, not
from prose: the run record, every job, every step conclusion and duration, and
the check-run annotations.  Annotations are public even when job logs are not
(the logs endpoint answers HTTP 403 ``Must have admin rights to Repository``
for the runner's own ``actions: write`` token - observed on run 43357207555),
and they are what turns "mechanism unobserved" into an observed
``LEX_WORK_QUANTUM_EXPIRED`` / ``exit code 78`` fact.

Logs are also reachable: the earlier ``HTTP 403 Must have admin rights to
Repository`` observation for this endpoint came from sending the checkout's
``basic`` extraheader, not from the endpoint's policy.  With the ``token``
scheme and without forwarding credentials to the storage redirect the job log
downloads at HTTP 200, so this tool captures redacted logs as well - and the
``logs_endpoint_status`` field then records 200, which is what
:func:`product.audit_step_diagnosis.classify` needs before it may say the
log-level cause is readable.

What it does
------------
* reads credentials from the checkout's own git HTTP extraheader (or
  ``GITHUB_TOKEN`` / ``GH_TOKEN``); the token is used for the request and is
  NEVER written to the artifact;
* fetches the run, its jobs (with per-step conclusions and timestamps) and the
  check-run annotations for every job;
* probes the job-logs endpoint and records only the HTTP status code, because
  "logs downloadable: yes/no" changes how :func:`product.audit_step_diagnosis.classify`
  words its mechanism claim;
* fails closed: a non-2xx API answer raises instead of writing a half-empty
  snapshot that later looks like evidence.

Usage
-----
    python3 product/fetch_run_jobs_snapshot.py --run-id 43357207555 \\
        --note "audit job died before a gate" \\
        --out results/product/orchestration/CYCLE_43357207555_run_jobs_raw.json
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "github-actions-run-jobs-snapshot/1"
REPO_RE = re.compile(r"^https://api\.github\.com/repos/([^/]+)/([^/]+)")
FUZZY = 60  # seconds of clock skew tolerated between run and job timestamps


def repo_slug() -> str:
    """``owner/name`` from the checkout, so the tool is never pinned to one fork."""
    env = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if env.count("/") == 1:
        return env
    url = _git("config", "--get", "remote.origin.url").stdout.strip()
    match = re.search(r"github\.com[:/]([^/]+/[^/.]+?)(?:\.git)?$", url)
    if match:
        return match.group(1)
    raise SystemExit(f"cannot determine the GitHub repository from {url!r}")


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True,
                          text=True, check=False)


def api_token() -> str:
    """Token from the checkout's git config, then the standard env vars."""
    header = _git("config", "--get",
                  "http.https://github.com/.extraheader").stdout or ""
    match = re.search(r"basic\s+(\S+)", header, re.IGNORECASE)
    if match:
        try:
            decoded = base64.b64decode(match.group(1)).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            decoded = ""
        if ":" in decoded:
            _, token = decoded.split(":", 1)
            if token:
                return token
    for name in ("GITHUB_TOKEN", "GH_TOKEN", "LEX_GITHUB_TOKEN"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    raise SystemExit(
        "no GitHub token available: git http.extraheader and GITHUB_TOKEN/"
        "GH_TOKEN are all empty; refusing to write an annotation-free "
        "snapshot that would read as 'mechanism unobserved'")


def _request(url: str, token: str) -> tuple[int, bytes]:
    req = urllib.request.Request(
        url, headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "lexmachina-product-resume",
        })
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:  # HTTP status is data, not a crash
        return exc.code, exc.read() or b""
    except urllib.error.URLError as exc:  # network failure is a hard stop
        raise SystemExit(f"network failure fetching {url}: {exc.reason}")


def _json(url: str, token: str) -> dict[str, Any]:
    status, body = _request(url, token)
    if status != 200:
        raise SystemExit(
            f"GET {url} -> HTTP {status}: "
            f"{body[:300].decode('utf-8', 'replace')}")
    data = json.loads(body)
    if not isinstance(data, dict):
        raise SystemExit(f"GET {url} returned a non-object payload")
    return data


def _annotations(job: dict, token: str, repo: str) -> list[dict]:
    """Check-run annotations for ``job``; job id doubles as the check-run id.

    Annotations are the only public channel that carries the wrapper's
    ``LEX_WORK_QUANTUM_EXPIRED`` / ``exit code`` lines.  An endpoint failure
    is recorded as an empty list - never guessed at - because
    :func:`product.audit_step_diagnosis.classify` reports
    ``annotations_available=false`` honestly in that case.
    """
    status, body = _request(
        f"https://api.github.com/repos/{repo}/check-runs/{job['id']}/annotations",
        token)
    if status != 200:
        return []
    rows = json.loads(body)
    if not isinstance(rows, list):
        return []
    keep = ("annotation_level", "message", "path", "start_line", "end_line")
    return [{k: row.get(k) for k in keep if k in row} for row in rows
            if isinstance(row, dict)]


class _StripAuthOnRedirect(urllib.request.HTTPRedirectHandler):
    """Do not forward the API credential to the storage redirect target.

    Without this, urllib replays ``Authorization: token ...`` onto the
    pre-signed blob URL and Azure answers ``AuthenticationFailed`` (HTTP 403),
    which is indistinguishable from "logs are admin-only" unless you look at
    the XML body.  ``curl`` never made this mistake because it drops the
    header across hosts by default.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        new_req = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new_req is not None:
            for key in list(new_req.headers):
                if key.lower() == "authorization":
                    del new_req.headers[key]
        return new_req


def _logs_fetch(job: dict, token: str, repo: str) -> tuple[int, bytes]:
    """Download a job log.

    Two quirks of this endpoint are load-bearing and are handled explicitly
    instead of being reported as "logs are admin-only":

    * the API answer must use the ``token`` scheme (``Bearer`` and the
      checkout's ``basic`` extraheader are both rejected: 401/403);
    * the API answers with a redirect to blob storage, and credentials must
      NOT be forwarded to that second host (Azure answers
      ``AuthenticationFailed`` when they are), which is what a plain
      ``urllib`` redirect looks like from the outside.
    """
    url = f"https://api.github.com/repos/{repo}/actions/jobs/{job['id']}/logs"
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "lexmachina-product-resume",
    })
    opener = urllib.request.build_opener(_StripAuthOnRedirect())
    try:
        with opener.open(req, timeout=60) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        if exc.code in (301, 302, 307, 308):
            location = exc.headers.get("Location")
            if location:
                plain = urllib.request.Request(location, headers={
                    "User-Agent": "lexmachina-product-resume"})
                try:
                    with urllib.request.urlopen(plain, timeout=60) as resp:
                        return resp.status, resp.read()
                except urllib.error.HTTPError as inner:  # signed URL expired
                    return inner.code, b""
        return exc.code, exc.read() or b""
    except urllib.error.URLError as exc:
        raise SystemExit(f"network failure fetching {url}: {exc.reason}")


SECRET_RE = re.compile(
    r"gh[somp]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+|Bearer\s+\S+|"
    r"AUTHORIZATION:\s*\S+\s*\S+", re.IGNORECASE)


def redact(text: str) -> tuple[str, int]:
    """Strip credential-shaped substrings; return the text and hit count."""
    text, hits = SECRET_RE.subn("<REDACTED-CREDENTIAL>", text)
    return text, hits


def snapshot(run_id: str, note: str = "", token: str | None = None) -> dict:
    token = token or api_token()
    repo = repo_slug()
    base = f"https://api.github.com/repos/{repo}/actions"
    run = _json(f"{base}/runs/{run_id}", token)
    jobs_payload = _json(f"{base}/runs/{run_id}/jobs?per_page=100", token)
    jobs = []
    annotations: dict[str, list[dict]] = {}
    logs_status = None
    for job in jobs_payload.get("jobs", []):
        jobs.append({k: job.get(k) for k in (
            "id", "run_id", "workflow_name", "head_branch", "head_sha",
            "run_url", "run_attempt", "node_id", "status", "conclusion",
            "started_at", "completed_at", "url", "html_url", "name", "steps")})
        annotations[str(job["id"])] = _annotations(job, token, repo)
        if logs_status is None:
            logs_status, _ = _logs_fetch(job, token, repo)
    record = {
        "schema": SCHEMA,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fetched_from": f"https://api.github.com/repos/{repo}"
                        f"/actions/runs/{run_id}",
        "fetched_via": "GitHub REST actions API with the runner's own git "
                       "HTTP extraheader token, by resuming producer run "
                       f"{os.environ.get('GITHUB_RUN_ID', 'unknown')}",
        "artifact_note": note or (
            "Raw run/jobs snapshot captured so the resume diagnosis can "
            "classify the orchestration outcome from committed bytes."),
        "logs_endpoint_status": logs_status,
        "token_material_in_artifact": False,
        "annotations": annotations,
        "run": {k: run.get(k) for k in (
            "id", "name", "status", "conclusion", "created_at", "updated_at",
            "head_sha", "head_branch", "event", "run_attempt", "path")},
        "jobs": jobs,
    }
    # Fail closed on the one thing this tool must never do: leak a credential.
    blob = json.dumps(record)
    if "ghs_" in blob or "gho_" in blob or "github_pat_" in blob:
        raise SystemExit("refusing to write: a token string leaked into the "
                         "snapshot payload")
    return record


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--note", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--logs-dir", default=None,
                    help="also write redacted job logs into this directory")
    args = ap.parse_args(argv)
    rec = snapshot(args.run_id, args.note)
    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    if args.logs_dir:
        token = api_token()
        repo = repo_slug()
        log_dir = Path(args.logs_dir)
        if not log_dir.is_absolute():
            log_dir = ROOT / log_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        manifest = []
        for job in rec["jobs"]:
            status, body = _logs_fetch(job, token, repo)
            entry = {"job_id": job["id"], "job_name": job["name"],
                     "http_status": status}
            if status == 200 and body:
                name = f"{job['name'].replace(' ', '_')}.log"
                text, hits = redact(body.decode("utf-8", "replace"))
                (log_dir / name).write_text(text, encoding="utf-8")
                # ``bytes`` must be the on-disk UTF-8 size, not the character
                # count: runner logs carry non-ASCII box/ANSI glyphs, so the
                # two differ and a published byte count would not reproduce.
                entry.update(file=name,
                             bytes=len(text.encode("utf-8")),
                             redactions=hits)
            manifest.append(entry)
        (log_dir / "MANIFEST.json").write_text(
            json.dumps({"schema": "product-job-log-capture/1",
                        "run_id": args.run_id, "logs": manifest}, indent=2)
            + "\n", encoding="utf-8")
        print(f"logs -> {log_dir}: "
              f"{sum(1 for e in manifest if e.get('file'))} of "
              f"{len(manifest)} jobs captured")
    try:
        shown = out.relative_to(ROOT)
    except ValueError:
        shown = out
    print(f"wrote {shown}: run={rec['run']['status']}/{rec['run']['conclusion']} "
          f"jobs={len(rec['jobs'])} "
          f"annotated_jobs={sum(1 for v in rec['annotations'].values() if v)} "
          f"logs_endpoint_status={rec['logs_endpoint_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
