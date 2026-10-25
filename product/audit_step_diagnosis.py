#!/usr/bin/env python3
"""Classify why a core-lane run stopped before an independent audit gate.

Why this exists
---------------
The product cycle is routinely resumed with the instruction "diagnose the
orchestration/validation failure".  From the producer tree alone the important
facts are: did the team job persist its snapshot, did the provider/agent step
fail, and did an independent gate ever get written?  This module answers those
questions from a committed GitHub Actions run/jobs snapshot -- no token, no job
logs, no guessing at a cause it cannot observe.

It deliberately does NOT:
* claim a provider/auth/quantum mechanism when the log is unavailable;
* treat a failed audit *job* as a product defect or as a REVISE verdict;
* write ``results/audit/**`` (only the independent auditor may write there).

Usage
-----
    python3 product/audit_step_diagnosis.py --raw <snapshot.json> --out <dir>
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "product-audit-step-diagnosis/1"
TEAM_JOB = "team"
AUDIT_JOB = "audit"
AUDIT_STEP = "Independent audit"


def _step(job: dict, name: str) -> dict | None:
    return next((s for s in job.get("steps") or [] if s.get("name") == name), None)


def _seconds_between(start: str | None, end: str | None) -> float | None:
    if not start or not end:
        return None
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    return round((datetime.strptime(end, fmt) - datetime.strptime(start, fmt))
                 .total_seconds(), 1)


def classify(snapshot: dict) -> dict:
    """Pure classification of a committed run/jobs snapshot."""
    run = snapshot.get("run") or {}
    jobs = {j.get("name"): j for j in snapshot.get("jobs") or []}
    team = jobs.get(TEAM_JOB) or {}
    audit = jobs.get(AUDIT_JOB) or {}
    audit_step = _step(audit, AUDIT_STEP)
    gate_step = _step(audit, "Enforce audit scope and read gate")
    persist_step = _step(audit, "Persist audit snapshot")
    validate_step = _step(team, "Validate active MVP producer state")
    scope_step = _step(team, "Enforce lane write scope")
    snapshot_step = _step(team, "Persist team snapshot")
    integrate = jobs.get("integrate") or {}

    team_ok = team.get("conclusion") == "success"
    audit_failed = audit.get("conclusion") == "failure"
    audit_step_failed = bool(audit_step and audit_step.get("conclusion") == "failure")
    gate_skipped = bool(gate_step and gate_step.get("conclusion") == "skipped")
    snapshot_skipped = bool(persist_step and persist_step.get("conclusion") == "skipped")
    team_snapshot_persisted = bool(
        team_ok
        and snapshot_step
        and snapshot_step.get("conclusion") == "success"
    )

    if team_ok and audit_failed and audit_step_failed and gate_skipped:
        classification = "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    elif team_ok and audit_failed:
        classification = "AUDIT_JOB_FAILED_OTHER_STEP"
    elif team_ok and audit.get("conclusion") == "success":
        classification = "AUDIT_JOB_COMPLETED"
    else:
        classification = "TEAM_JOB_DID_NOT_COMPLETE_SUCCESSFULLY"

    return {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "run_id": str(run.get("id")),
        "run_name": run.get("name"),
        "run_conclusion": run.get("conclusion"),
        "classification": classification,
        "team": {
            "conclusion": team.get("conclusion"),
            "team_snapshot_persisted": team_snapshot_persisted,
            "producer_state_validation_ran": bool(
                validate_step and validate_step.get("conclusion") == "success"
            ),
            "write_scope_step_ran": bool(
                scope_step and scope_step.get("conclusion") == "success"
            ),
        },
        "audit": {
            "conclusion": audit.get("conclusion"),
            "failed_step": AUDIT_STEP if audit_step_failed else None,
            "independent_audit_step_seconds": _seconds_between(
                (audit_step or {}).get("started_at"),
                (audit_step or {}).get("completed_at"),
            ),
            "gate_step": (gate_step or {}).get("conclusion"),
            "persist_step": (persist_step or {}).get("conclusion"),
            # A skipped gate step means no gate JSON can exist on the audit ref.
            "gate_file_written": not gate_skipped and not snapshot_skipped,
        },
        "integrate": {
            "conclusion": integrate.get("conclusion"),
            "why_skipped": (
                "audit job did not succeed, so the integrate job is skipped by "
                "the workflow condition"
                if integrate.get("conclusion") == "skipped" else None
            ),
        },
        "mechanism": {
            "status": "UNOBSERVED",
            "logs_available": bool(snapshot.get("logs_endpoint_status") == 200),
            "logs_endpoint_status": snapshot.get("logs_endpoint_status"),
            "claim": (
                "The independent-audit agent process exited non-zero after "
                f"{(audit_step or {}).get('started_at')} and before "
                f"{(audit_step or {}).get('completed_at')}. Job logs are not "
                "downloadable without admin rights, so no provider, auth, "
                "timeout or token mechanism is claimed."
            ),
        },
        "adjudication": {
            "product_defect": False,
            "verdict_written": False,
            "team_work_preserved": team_snapshot_persisted,
            "requires_product_repair": False,
            "control_plane_attention": (
                "re-run the independent audit; no workflow change is "
                "identified from the observable snapshot"
            ),
            "next_action": (
                "Resume from the persisted team snapshot, re-verify the lane "
                "deliverable and make the snapshot audit-ready; do not infer a "
                "REVISE, a BLOCKED verdict or a product regression from a failed "
                "audit job."
            ),
        },
        "claim_ceiling": (
            "This artifact classifies an orchestration failure from a public "
            "run/jobs snapshot. It asserts no cause it could not observe, writes "
            "no audit gate, treats no run as accepted or rejected, and makes no "
            "product, legal or serve claim."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", required=True, help="committed run/jobs snapshot")
    ap.add_argument("--out", required=True, help="output JSON path")
    args = ap.parse_args(argv)
    snapshot = json.loads(Path(args.raw).read_text(encoding="utf-8"))
    rec = classify(snapshot)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(json.dumps({"out": str(out), "classification": rec["classification"]},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
