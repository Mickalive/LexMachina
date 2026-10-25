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
* treat a failed audit *or team* job as a product defect or as a verdict;
* write ``results/audit/**`` (only the independent auditor may write there).

The ``team`` block reports the persist step's OWN conclusion.  This matters
because the workflow guards that step with ``if: always()``: a failed producer
still publishes its (possibly unchanged) tree to the team ref, so "team job
failed" must never be reported as "no snapshot exists".  Whether that snapshot
carries a durable delta is a separate, git-ref fact and is deliberately not
inferred here.

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
    # The workflow guards "Persist team snapshot" with `if: always()`, so the
    # step conclusion is the FACT about the snapshot, independent of whether
    # the team job succeeded.  Reporting it as `team_ok and persist_ok` hides
    # the always-publish behaviour that lets a failed producer's (empty) tree
    # reach the team ref anyway.
    team_snapshot_persisted = bool(
        snapshot_step and snapshot_step.get("conclusion") == "success"
    )
    failed_team_step = next(
        (s for s in team.get("steps") or [] if s.get("conclusion") == "failure"),
        None,
    )
    audit_skipped = audit.get("conclusion") == "skipped"

    if not team_ok and failed_team_step and audit_skipped:
        if failed_team_step.get("name") == "Run lane cycle":
            classification = "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
        else:
            classification = "TEAM_JOB_FAILED_OTHER_STEP"
    elif team_ok and audit_failed and audit_step_failed and gate_skipped:
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
            "team_snapshot_step_conclusion": (snapshot_step or {}).get(
                "conclusion"
            ),
            "team_snapshot_persisted_after_failed_team_job": bool(
                not team_ok and team_snapshot_persisted
            ),
            "failed_step": (failed_team_step or {}).get("name"),
            "failed_step_seconds": _seconds_between(
                (failed_team_step or {}).get("started_at"),
                (failed_team_step or {}).get("completed_at"),
            ),
            "producer_state_validation_ran": bool(
                validate_step and validate_step.get("conclusion") == "success"
            ),
            "producer_state_validation_step_conclusion": (validate_step or {}).get(
                "conclusion"
            ),
            "write_scope_step_ran": bool(
                scope_step and scope_step.get("conclusion") == "success"
            ),
            "write_scope_step_conclusion": (scope_step or {}).get("conclusion"),
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
            # Only a gate step that actually ran and succeeded can have
            # written a gate JSON.  A skipped audit job has no gate steps at
            # all, so "not skipped" is not evidence that a gate exists.
            "gate_file_written": bool(
                gate_step and gate_step.get("conclusion") == "success"
            ),
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
                (
                    "The lane-cycle agent process exited non-zero after "
                    f"{(failed_team_step or {}).get('started_at')} and before "
                    f"{(failed_team_step or {}).get('completed_at')}. The "
                    "workflow's 'Persist team snapshot' step is guarded by "
                    "`if: always()` and concluded "
                    f"{(snapshot_step or {}).get('conclusion')!r}, so the team "
                    "ref can be published with ZERO durable delta. Job logs are "
                    "not downloadable without admin rights, so no provider, "
                    "auth, timeout or token mechanism is claimed."
                )
                if not team_ok else (
                    "The independent-audit agent process exited non-zero after "
                    f"{(audit_step or {}).get('started_at')} and before "
                    f"{(audit_step or {}).get('completed_at')}. Job logs are not "
                    "downloadable without admin rights, so no provider, auth, "
                    "timeout or token mechanism is claimed."
                )
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
                if team_ok else (
                    "resume from the persisted snapshot and verify whether it "
                    "carries a durable delta; `if: always()` can publish a "
                    "failed producer's unchanged tree, which the producer-side "
                    "scope and validation steps never get to reject"
                )
            ),
            "next_action": (
                "Resume from the persisted team snapshot, re-verify the lane "
                "deliverable and make the snapshot audit-ready; do not infer a "
                "REVISE, a BLOCKED verdict or a product regression from a failed "
                "audit job."
                if team_ok else (
                    "Resume from the persisted team snapshot, prove whether it "
                    "has a durable delta against its predecessor, re-verify the "
                    "lane deliverable and make the snapshot audit-ready; do not "
                    "infer a REVISE, a BLOCKED verdict or a product regression "
                    "from a failed producer step."
                )
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
