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
import re
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "product-audit-step-diagnosis/1"
TEAM_JOB = "team"
AUDIT_JOB = "audit"
AUDIT_STEP = "Independent audit"
QUANTUM_RE = re.compile(r"LEX_WORK_QUANTUM_EXPIRED\s+seconds=(\d+)")
EXIT_CODE_RE = re.compile(r"exit code\s+(\d+)", re.IGNORECASE)


def _step(job: dict, name: str) -> dict | None:
    return next((s for s in job.get("steps") or [] if s.get("name") == name), None)


def _seconds_between(start: str | None, end: str | None) -> float | None:
    if not start or not end:
        return None
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    return round((datetime.strptime(end, fmt) - datetime.strptime(start, fmt))
                 .total_seconds(), 1)


def _job_annotations(snapshot: dict, job: dict) -> list[dict]:
    """Return the check-run annotations for ``job`` from a committed snapshot.

    Three layouts are accepted because the raw snapshots were captured by
    different code paths:

    * ``snapshot["annotations"][<job id>]`` - a job-keyed mapping;
    * a FLAT ``snapshot["annotations"]`` list - what
      ``orchestration_evidence.observe_raw_snapshot`` actually writes (each
      entry carries ``job``/``job_id``).  Until cycle 41179957652 this layout
      was silently unreadable, so a run whose public annotation carried
      ``LEX_WORK_QUANTUM_EXPIRED seconds=2700`` and exit code 78 was classified
      as mechanism ``UNOBSERVED``.  That is a reader defect, not missing
      evidence: the annotations were committed beside the steps all along.
    * a job-local ``job["annotations"]`` list.

    Anything else is treated as "not captured", never guessed.  Flat entries
    are attributed ONLY by an exact job id or job name; an entry that names no
    job is excluded rather than attributed to whichever job is being classified.
    """
    ann = snapshot.get("annotations")
    if isinstance(ann, dict):
        for key in (str(job.get("id")), job.get("id")):
            if key in ann and isinstance(ann[key], list):
                return ann[key]
    if isinstance(ann, list):
        job_id = job.get("id")
        job_name = job.get("name")
        matched = [
            a for a in ann
            if isinstance(a, dict) and (
                (job_id is not None and a.get("job_id") == job_id)
                or (job_name is not None and a.get("job") == job_name)
            )
        ]
        if matched:
            return matched
    job_ann = job.get("annotations")
    if isinstance(job_ann, list):
        return job_ann
    return []


def _failure_annotations(snapshot: dict, team: dict, audit: dict,
                         audit_step_failed: bool, failed_team_step: dict | None
                         ) -> dict:
    """Extract the *observable* failure annotations, if the snapshot has them.

    GitHub check-run annotations are public even when job logs require admin
    rights.  The workflow's own 45-minute agent wrapper announces
    ``LEX_WORK_QUANTUM_EXPIRED seconds=2700`` and exit code 78, so a quantum
    expiry can be stated as observed evidence instead of "mechanism unknown".
    """
    if audit_step_failed:
        job_name, job = AUDIT_JOB, audit
    elif failed_team_step is not None:
        job_name, job = TEAM_JOB, team
    else:
        job_name, job = None, {}
    messages = [
        str(a.get("message") or "")
        for a in _job_annotations(snapshot, job)
        if isinstance(a, dict)
    ]
    quantum_seconds = None
    exit_code = None
    quantum_message = None
    for message in messages:
        m = QUANTUM_RE.search(message)
        if m:
            quantum_seconds = int(m.group(1))
            quantum_message = message.strip()
        e = EXIT_CODE_RE.search(message)
        if e and exit_code is None:
            exit_code = int(e.group(1))
    return {
        "source": (
            "github_actions_check_run_annotations" if messages else "none"
        ),
        "annotations_available": bool(messages),
        "job": job_name,
        "exit_code": exit_code,
        "quantum_expired": quantum_seconds is not None,
        "quantum_seconds": quantum_seconds,
        "quantum_message": quantum_message,
        "messages": messages,
    }


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
    annotations = _failure_annotations(
        snapshot, team, audit, audit_step_failed, failed_team_step
    )
    quantum_seconds = annotations.get("quantum_seconds")
    quantum_expired = bool(annotations.get("quantum_expired"))
    # HTTP 200 on the run-jobs logs endpoint means the producing cycle (or a
    # later resume holding the producer token) actually downloaded the job
    # logs; "not downloadable" is then a false sentence, see the branch below.
    logs_available = bool(snapshot.get("logs_endpoint_status") == 200)

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

    audit_step_seconds = _seconds_between(
        (audit_step or {}).get("started_at"),
        (audit_step or {}).get("completed_at"),
    )
    failed_team_step_seconds = _seconds_between(
        (failed_team_step or {}).get("started_at"),
        (failed_team_step or {}).get("completed_at"),
    )
    if quantum_expired:
        who = ("the independent-audit agent" if failed_team_step is None
               else "the lane-cycle (producer) agent")
        mechanism_status = "OBSERVED_QUANTUM_EXPIRED"
        mechanism_claim = (
            "The agent was stopped by the workflow's own work quantum: the "
            f"public check-run annotation reads "
            f"{annotations.get('quantum_message')!r}"
            + (f" with exit code {annotations.get('exit_code')}"
               if annotations.get("exit_code") is not None else "")
            + f" after {audit_step_seconds or failed_team_step_seconds} s. "
            + (
                "No gate was written because the quantum ended before the "
                "agent could write one."
                if failed_team_step is None
                else "The producer was stopped before the workflow's state "
                     "validation and write-scope steps could run, so those "
                     "steps report 'skipped'; the always-run persist step "
                     "then published the tree it had."
            )
            + " No provider or auth cause is claimed."
        )
    elif not team_ok:
        # The mechanism block's vocabulary used to be binary: observed quantum
        # expiry, or UNOBSERVED with a claim that "job logs are not
        # downloadable without admin rights".  Producer cycles 40263308953 and
        # 40263483436 falsified the second half: with the producer token the
        # logs endpoint answers HTTP 200 and the cause is readable (model
        # gateway rejected the request parameter ``permissions``).  When the
        # snapshot records that the logs WERE fetched, claiming "not
        # downloadable" would publish a false sentence, and the status says so
        # honestly: the orchestration facts are observed, no quantum expiry
        # occurred, and the log-level cause belongs to the committed
        # lane-cycle log-evidence artifact (product/lane_cycle_log_evidence.py)
        # rather than to this instrument.
        mechanism_status = ("OBSERVED_LOGS_AVAILABLE_NO_QUANTUM"
                            if logs_available else "UNOBSERVED")
        if logs_available:
            mechanism_claim = (
                "The lane-cycle agent process exited non-zero after "
                f"{(failed_team_step or {}).get('started_at')} and before "
                f"{(failed_team_step or {}).get('completed_at')}. The "
                "workflow's 'Persist team snapshot' step is guarded by "
                "`if: always()` and concluded "
                f"{(snapshot_step or {}).get('conclusion')!r}, so the team "
                "ref can be published with ZERO durable delta. The job logs "
                "WERE downloadable in the producing cycle (HTTP "
                f"{snapshot.get('logs_endpoint_status')}) and are committed "
                "beside this diagnosis, so the log-level cause is observable "
                "and is classified by the lane-cycle log-evidence artifact "
                "built with product/lane_cycle_log_evidence.py. This "
                "instrument reports only the orchestration facts (step "
                "conclusions, durations) and observed no work-quantum expiry "
                "(quantum_expired=false); no provider, auth or token cause "
                "is asserted here."
            )
        else:
            mechanism_claim = (
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
    else:
        mechanism_status = ("OBSERVED_LOGS_AVAILABLE_NO_QUANTUM"
                            if logs_available else "UNOBSERVED")
        mechanism_claim = (
            "The independent-audit agent process exited non-zero after "
            f"{(audit_step or {}).get('started_at')} and before "
            f"{(audit_step or {}).get('completed_at')}. "
            + (
                f"Job logs were downloadable (HTTP "
                f"{snapshot.get('logs_endpoint_status')}) and are committed "
                "beside this diagnosis; the log-level cause is classified by "
                "the lane-cycle log-evidence artifact."
                if logs_available else
                "Job logs are not downloadable without admin rights, so no "
                "provider, auth, timeout or token mechanism is claimed."
            )
        )

    if quantum_expired:
        # Name the agent that actually hit the quantum.  Both jobs run the
        # same 2700 s wrapper, so attributing a *team*-job expiry to "the
        # independent-audit agent" would be a false attribution of the kind
        # requirement 33 forbids; the failed job is observable from the
        # snapshot and is stated instead.  The audit-job wording is kept
        # byte-identical to the artifacts already committed for run
        # 40196023042 so a re-classification of that snapshot still compares
        # equal to its evidence of record.
        if failed_team_step is None:
            control_plane_attention = (
                "the independent-audit agent consumed the entire agent work "
                f"quantum ({quantum_seconds} s) before writing a gate. This is "
                "a control-plane budget/turnaround fact, not a product defect; "
                "a bounded audit-readiness dossier is published so the next "
                "audit does not have to re-derive the slice. .github/** is "
                "control-plane scope and is recorded, never edited from a lane."
            )
        else:
            control_plane_attention = (
                "the lane-cycle (producer) agent consumed the entire agent "
                f"work quantum ({quantum_seconds} s) before its cycle could "
                "finish, so the workflow's state-validation and write-scope "
                "steps were skipped and the always-run persist step published "
                "the tree it had. This is a control-plane budget/turnaround "
                "fact, not a product defect; a bounded audit-readiness dossier "
                "is published so the next audit does not have to re-derive the "
                "slice. .github/** is control-plane scope and is recorded, "
                "never edited from a lane."
            )
        next_action = (
            "Resume from the persisted team snapshot, consume the bounded "
            "audit-readiness dossier, and re-run the independent audit; do not "
            "infer a REVISE, BLOCKED verdict or a product regression from a "
            "quantum expiry."
        )
    elif team_ok:
        control_plane_attention = (
            "re-run the independent audit; no workflow change is identified "
            "from the observable snapshot"
        )
        next_action = (
            "Resume from the persisted team snapshot, re-verify the lane "
            "deliverable and make the snapshot audit-ready; do not infer a "
            "REVISE, a BLOCKED verdict or a product regression from a failed "
            "audit job."
        )
    else:
        control_plane_attention = (
            "resume from the persisted snapshot and verify whether it "
            "carries a durable delta; `if: always()` can publish a "
            "failed producer's unchanged tree, which the producer-side "
            "scope and validation steps never get to reject"
        )
        next_action = (
            "Resume from the persisted team snapshot, prove whether it "
            "has a durable delta against its predecessor, re-verify the "
            "lane deliverable and make the snapshot audit-ready; do not "
            "infer a REVISE, a BLOCKED verdict or a product regression "
            "from a failed producer step."
        )

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
            "independent_audit_step_seconds": audit_step_seconds,
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
            "status": mechanism_status,
            "logs_available": bool(snapshot.get("logs_endpoint_status") == 200),
            "logs_endpoint_status": snapshot.get("logs_endpoint_status"),
            "annotations_available": annotations.get("annotations_available"),
            "quantum_expired": quantum_expired,
            "quantum_seconds": quantum_seconds,
            "exit_code": annotations.get("exit_code"),
            "claim": mechanism_claim,
        },
        "observed_failure": annotations,
        "adjudication": {
            "product_defect": False,
            "verdict_written": False,
            "team_work_preserved": team_snapshot_persisted,
            "requires_product_repair": False,
            "control_plane_attention": control_plane_attention,
            "next_action": next_action,
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
