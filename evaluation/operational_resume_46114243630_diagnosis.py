#!/usr/bin/env python3
"""Operational-resume diagnosis for evaluation run 46110768588.

Fresh-context resume of run 46114243630.  This instrument does NOT re-run the
failed producer or any benchmark.  It records, from the public GitHub REST API
and the local git object store, WHY run 46110768588 left only a producer
snapshot and never produced an audit gate, then classifies that failure under
the factory-wide operational requirements (rc-78 LEX_WORK_QUANTUM_EXPIRED is
an orchestration limit, not a verdict, not a product defect and not a human
gate).

Writes only under results/evaluation/orchestration/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
API = "https://api.github.com/repos/Mickalive/LexMachina"
SUBJECT_RUN = "46110768588"
TEAM_JOB_ID = "140873582161"
SNAPSHOT_REF = "origin/cycle/core/evaluation/46110768588/team"
INSTRUMENT = "evaluation/frozen_rules_profile_coverage_falsifier.py"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def get_json(url: str) -> tuple[dict[str, Any] | list[Any], str, str]:
    req = urllib.request.Request(
        url, headers={"Accept": "application/vnd.github+json",
                      "User-Agent": "lexmachina-evaluation-resume"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
        return json.loads(raw), sha256_bytes(raw), resp.status


def git(*args: str) -> str:
    p = subprocess.run(["git", *args], cwd=REPO, capture_output=True,
                       text=True, timeout=30)
    if p.returncode != 0:
        return ""
    return p.stdout.strip()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", default="results/evaluation/orchestration")
    ap.add_argument("--offline-evidence", default=None,
                    help="directory holding previously captured API JSON, "
                         "used only if the live API is unavailable")
    args = ap.parse_args(argv)
    out_dir = REPO / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    sources: dict[str, dict[str, Any]] = {}
    for label, url in (
        ("run", f"{API}/actions/runs/{SUBJECT_RUN}"),
        ("jobs", f"{API}/actions/runs/{SUBJECT_RUN}/jobs?per_page=100"),
        ("team_annotations", f"{API}/check-runs/{TEAM_JOB_ID}/annotations"),
    ):
        try:
            payload, digest, status = get_json(url)
            mode = "LIVE_GITHUB_REST"
        except (urllib.error.URLError, TimeoutError) as exc:
            if not args.offline_evidence:
                raise
            cached = Path(args.offline_evidence) / f"{label}.json"
            raw = cached.read_bytes()
            payload, digest, mode = json.loads(raw), sha256_bytes(raw), "CACHED_API_EVIDENCE"
            status = "from-cache"
        sources[label] = {"url": url, "mode": mode, "http_status": status,
                          "payload_sha256": digest, "payload": payload}
        (out_dir / f"CYCLE_{SUBJECT_RUN}_{label}.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    run = sources["run"]["payload"]
    jobs_doc = sources["jobs"]["payload"]
    ann = sources["team_annotations"]["payload"]
    team_job = next((j for j in jobs_doc.get("jobs", [])
                     if j.get("name") == "team"), {})
    failing_steps = [s["name"] for s in team_job.get("steps", [])
                     if s.get("conclusion") == "failure"]
    skipped_steps = [s["name"] for s in team_job.get("steps", [])
                     if s.get("conclusion") == "skipped"]
    messages = [a.get("message", "") for a in ann]
    quantum_expired = any("LEX_WORK_QUANTUM_EXPIRED" in m for m in messages)
    rc78 = any("exit code 78" in m for m in messages)
    annotations = [
        {"level": a.get("annotation_level"), "message": a.get("message")}
        for a in ann
    ]

    snapshot_head = git("rev-parse", SNAPSHOT_REF)
    snap_subject = git("log", "-1", "--format=%s", SNAPSHOT_REF)
    snap_files = git("diff-tree", "--no-commit-id", "--name-only", "-r",
                     SNAPSHOT_REF).splitlines()
    instrument_sha = sha256_bytes((REPO / INSTRUMENT).read_bytes())
    audit_ref = git("rev-parse",
                    f"origin/cycle/core/evaluation/{SUBJECT_RUN}/audit")
    lab_head = git("rev-parse", "origin/lab/evaluation")

    diagnosis = {
        "schema": "lex-evaluation-operational-resume-diagnosis/1",
        "lane": "evaluation",
        "resume_run_id": "46114243630",
        "subject_run_id": SUBJECT_RUN,
        "direction_version": 68,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "failure_class": "LEX_WORK_QUANTUM_EXPIRED" if quantum_expired else "UNCLASSIFIED",
        "failure_detail": {
            "team_job_conclusion": team_job.get("conclusion"),
            "failing_steps": failing_steps,
            "skipped_steps": skipped_steps,
            "annotations": annotations,
            "rc78_observed": rc78,
            "quantum_seconds": next(
                (m.split("seconds=")[1].split()[0] for m in messages
                 if "seconds=" in m), None),
            "team_job_started_at": team_job.get("started_at"),
            "team_job_completed_at": team_job.get("completed_at"),
        },
        "orchestration_consequence": {
            "audit_job_conclusion": next(
                (j.get("conclusion") for j in jobs_doc.get("jobs", [])
                 if j.get("name") == "audit"), None),
            "integrate_job_conclusion": next(
                (j.get("conclusion") for j in jobs_doc.get("jobs", [])
                 if j.get("name") == "integrate"), None),
            "audit_branch_exists": bool(audit_ref),
            "audit_gate_path": f"results/audit/evaluation/CYCLE_{SUBJECT_RUN}_GATE.json",
            "promotion": "NONE - no audit gate, no accept commit for the subject run",
            "lab_evaluation_head": lab_head,
        },
        "persisted_producer_snapshot": {
            "ref": SNAPSHOT_REF,
            "head": snapshot_head,
            "subject": snap_subject,
            "files_added": snap_files,
            "instrument": INSTRUMENT,
            "instrument_sha256": instrument_sha,
            "preserved": snapshot_head == git("rev-parse", "HEAD")
                         or bool(snapshot_head),
            "missing_deliverables": [
                "freeze-first hypothesis record",
                "freeze record with population pins",
                "claim-bearing result artifact",
                "human-readable report",
                "additive state update",
            ],
        },
        "evidence_sources": {k: {kk: vv for kk, vv in v.items() if kk != "payload"}
                             for k, v in sources.items()},
        "classification_contract": (
            "Factory-wide requirements: an agent work-quantum expiry / provider "
            "rotation is an orchestration limit, NOT a verdict, NOT a product "
            "defect and NOT a human-gate problem. The team snapshot is valid "
            "completed work and must be preserved, not restarted."
        ),
        "claim_ceiling": (
            "This record establishes only the machine-observable cause of the "
            "subject run's missing gate and the inventory of the persisted "
            "snapshot. It scores no benchmark, moves no frozen bar, issues no "
            "serve verdict and adds no acceptance claim."
        ),
    }
    out = out_dir / f"CYCLE_{SUBJECT_RUN}_resume_diagnosis.json"
    out.write_text(json.dumps(diagnosis, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    print(json.dumps({
        "out": str(out), "sha256": sha256_bytes(out.read_bytes()),
        "failure_class": diagnosis["failure_class"],
        "audit_branch_exists": diagnosis["orchestration_consequence"]["audit_branch_exists"],
        "snapshot_head": snapshot_head, "instrument_sha256": instrument_sha,
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
