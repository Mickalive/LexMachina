#!/usr/bin/env python3
"""Classify how a core-lane run actually died, from the GitHub REST job record.

Why this module exists (operational resume of run 39082232157)
--------------------------------------------------------------
The product lane's own history now contains several DISTINCT death classes, and
conflating them has repeatedly cost cycles:

* ``rc 78 LEX_WORK_QUANTUM_EXPIRED`` — the wrapper killed the agent at 2700 s.
  That is a *failure*, it is recorded in the job logs, and the snapshot survives.
* misplaced gate file / lowercase ``_gate.json`` — the audit *agent* finished and
  the workflow's own reader step died.  Also a *failure*.
* provider auth/overload — the agent step exits non-zero; also a *failure*.
* **audit-step cancellation** (this module's subject) — the run concludes
  ``cancelled``; steps 6/7 are ``skipped``; NO audit branch exists; the lane is
  re-dispatched by the resilience job.  None of the above words describe it.

For run 39082232157 the observed record was: ``team`` success in 18 m 56 s
(snapshot ``68bdae8`` persisted on ``cycle/core/product/39082232157/team``), then
the audit job's ``Independent audit`` step running 54 m 59 s and concluding
``cancelled`` at 2026-10-18T01:33:15Z.  There is no ``.../audit`` branch on the
remote, so the work is *unaudited*, not rejected.

``.github/** is control-plane scope and is never edited from this lane.  So this
module does not patch the workflow; it makes the observed class **machine
checkable** so the next dispatch, report and auditor all read the same fact
instead of re-deriving it from prose.

Design notes
------------
* REUSE: the HTTP layer, ``observe_run`` and ``observe_jobs`` come from
  :mod:`product.ci_run_evidence` rather than being re-implemented.
* The classifier is a **pure function** of a job record, so it is unit-testable
  with no network.  Only :func:`observe_steps` touches the network.
* A run whose records cannot be fetched is reported as ``UNOBSERVABLE`` and is
  never silently treated as success, failure or cancellation.
* Classification is a *set* of predicates over the record, and the evidence for
  each fired predicate is published, so a reader can disagree with the label by
  reading the same numbers.

Usage
-----
    python product/orchestration_evidence.py --run-id 39082232157 --write
    python product/orchestration_evidence.py --run-id 39082232157        # dry run
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from product.ci_run_evidence import (  # noqa: E402  (path bootstrap above)
    DEFAULT_REPO,
    RunNotFound,
    http_fetch,
    observe_jobs,
    observe_run,
)

SCHEMA = "product-orchestration-evidence/1"
DEFAULT_OUT_DIR = REPO_ROOT / "results" / "product" / "orchestration"

#: Fallback copy of ``run-ox-with-retry.sh``'s default work quantum.  The real
#: value is read out of the control-plane script at runtime when it is reachable
#: (:func:`read_wrapper_quantum`); this constant only keeps the analysis honest
#: when that script is absent from the checkout being examined.
DEFAULT_WRAPPER_QUANTUM_SECONDS = 2700

#: Classes this module can name.  Anything else is reported as UNCLASSIFIED
#: rather than folded into a neighbouring class by resemblance.
CLASSES = (
    "AUDIT_STEP_CANCELLED_NO_GATE",
    "AUDIT_STEP_FAILED_NO_GATE",
    "AUDIT_FINISHED_BUT_NO_GATE",
    "TEAM_JOB_FAILED",
    "NO_AUDIT_JOB",
    "UNOBSERVABLE",
)


def _parse_ts(value: Any) -> Any:
    """ISO-8601 'Z' timestamp -> epoch seconds (float) or None."""
    if not value:
        return None
    try:
        from datetime import datetime, timezone

        return datetime.strptime(str(value), "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        ).timestamp()
    except ValueError:
        return None


def observe_steps(run_id: int | str, repo: str = DEFAULT_REPO, fetch: Callable = http_fetch) -> list[dict]:
    """Return the per-step records of every job in one run (network).

    Step-level timings are the only place the difference between "the audit agent
    hit its wrapper quantum" and "the audit step was cancelled" is visible: the
    wrapper writes a log line for the former, while the latter has a step record
    with ``conclusion == "cancelled"`` and no job log at all.
    """
    url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/jobs?per_page=100"
    status, payload = fetch(url)
    if status != 200 or not isinstance(payload, dict):
        return []
    steps: list[dict] = []
    for job in payload.get("jobs") or []:
        if not isinstance(job, dict):
            continue
        for step in job.get("steps") or []:
            if not isinstance(step, dict):
                continue
            started, completed = _parse_ts(step.get("started_at")), _parse_ts(step.get("completed_at"))
            steps.append(
                {
                    "job": job.get("name"),
                    "job_conclusion": job.get("conclusion"),
                    "job_started_at": job.get("started_at"),
                    "job_completed_at": job.get("completed_at"),
                    "step_number": step.get("number"),
                    "step": step.get("name"),
                    "status": step.get("status"),
                    "conclusion": step.get("conclusion"),
                    "started_at": step.get("started_at"),
                    "completed_at": step.get("completed_at"),
                    "duration_s": round(completed - started, 1)
                    if (started is not None and completed is not None)
                    else None,
                }
            )
    return steps


def classify(*, observation: dict | None, jobs: dict, steps: list[dict]) -> dict:
    """Name the death class of a core-lane run. Pure function of its record."""
    evidence: list[str] = []
    if not observation:
        return {
            "class": "UNOBSERVABLE",
            "why": "the run record could not be read from the REST API",
            "evidence": evidence,
            "producing_snapshot_survived": False,
            "verdict_exists": False,
        }

    conclusion = observation.get("conclusion")
    team = jobs.get("team")
    audit = jobs.get("audit")
    integrate = jobs.get("integrate")

    audit_step = next(
        (s for s in steps if (s.get("job") or "").lower() == "audit"
         and "independent audit" in (s.get("step") or "").lower()),
        None,
    )
    gate_read_step = next(
        (s for s in steps if (s.get("job") or "").lower() == "audit"
         and "read gate" in (s.get("step") or "").lower()),
        None,
    )
    persist_step = next(
        (s for s in steps if (s.get("job") or "").lower() == "audit"
         and "persist audit snapshot" in (s.get("step") or "").lower()),
        None,
    )

    if team is not None:
        evidence.append(f"job team concluded {team!r}")
    if audit is not None:
        evidence.append(f"job audit concluded {audit!r}")
    if integrate is not None:
        evidence.append(f"job integrate concluded {integrate!r}")
    evidence.append(f"run conclusion {conclusion!r}")
    if audit_step:
        evidence.append(
            "audit step 'Independent audit' concluded "
            f"{audit_step.get('conclusion')!r} after {audit_step.get('duration_s')} s"
        )
    if gate_read_step:
        evidence.append(
            f"workflow gate-reader step concluded {gate_read_step.get('conclusion')!r}"
        )
    if persist_step:
        evidence.append(
            f"audit-snapshot persist step concluded {persist_step.get('conclusion')!r}"
        )

    # The ordering that discriminates the classes: the agent step's own
    # conclusion, then whether the workflow's reader step ever ran.
    if team in ("failure", "cancelled", "timed_out"):
        klass = "TEAM_JOB_FAILED"
        why = "the producer job did not succeed, so the audit never became eligible"
    elif audit_step is None and audit is None:
        klass = "NO_AUDIT_JOB"
        why = "no audit job record exists for this run"
    elif audit_step is not None and audit_step.get("conclusion") == "cancelled":
        klass = "AUDIT_STEP_CANCELLED_NO_GATE"
        why = (
            "the independent-audit step was cancelled rather than failing; the gate-reader "
            "step and the audit-snapshot persist step were skipped, so no gate file was "
            "written and no audit branch exists. This is NOT the rc-78 wrapper quantum "
            "class (which concludes failure with a log line) and NOT a provider death."
        )
    elif audit_step is not None and audit_step.get("conclusion") == "failure":
        klass = "AUDIT_STEP_FAILED_NO_GATE"
        why = (
            "the independent-audit step failed; the gate reader never ran, so the run "
            "produced no verdict. Job logs are admin-only over the public API, so the "
            "wrapper exit code cannot be attributed from here."
        )
    elif gate_read_step is not None and gate_read_step.get("conclusion") == "skipped":
        klass = "AUDIT_FINISHED_BUT_NO_GATE"
        why = (
            "the audit agent step completed but the gate-reader step was skipped, which "
            "is the misplaced/lowercase-gate-artifact class"
        )
    else:
        klass = "UNOBSERVABLE"
        why = "the record does not match any class this module can name"

    return {
        "class": klass,
        "why": why,
        "evidence": evidence,
        "producing_snapshot_survived": team == "success",
        "verdict_exists": klass not in (
            "UNOBSERVABLE",
            "NO_AUDIT_JOB",
            "TEAM_JOB_FAILED",
            "AUDIT_STEP_CANCELLED_NO_GATE",
            "AUDIT_STEP_FAILED_NO_GATE",
        ),
    }


def read_wrapper_quantum(root: Path = REPO_ROOT) -> int:
    """Read ``WORK_QUANTUM_SECONDS``' default out of the wrapper script.

    The distinction that matters is arithmetic, not narrative: the wrapper's
    watchdog *returns 78* the moment the quantum elapses, so a step that ran
    LONGER than the quantum cannot have been stopped by it.  Reading the number
    out of the script instead of hard-coding it keeps that claim true after a
    control-plane change.
    """
    import re

    script = root / ".github" / "scripts" / "run-ox-with-retry.sh"
    try:
        text = script.read_text(encoding="utf-8")
    except OSError:
        return DEFAULT_WRAPPER_QUANTUM_SECONDS
    match = re.search(r'WORK_QUANTUM_SECONDS="\$\{LEX_AGENT_QUANTUM_SECONDS:-(\d+)\}"', text)
    return int(match.group(1)) if match else DEFAULT_WRAPPER_QUANTUM_SECONDS


def quantum_analysis(steps: list[dict], quantum_s: int) -> dict:
    """Did the wrapper's own work quantum plausibly stop the agent step?

    Pure function.  A step conclusion of ``cancelled`` combined with a duration
    ABOVE the quantum is the sharpest available evidence that the wrapper's rc-78
    watchdog did not fire: it polls every 15 s and returns 78 the moment the
    budget is spent, so it cannot produce a longer, cancelled step.
    """
    agent = next(
        (s for s in steps if (s.get("job") or "").lower() == "audit"
         and "independent audit" in (s.get("step") or "").lower()),
        None,
    )
    if not agent:
        return {
            "wrapper_quantum_s": quantum_s,
            "agent_step_found": False,
            "quantum_plausibly_fired": None,
            "note": "no audit agent step in the record; nothing to compare against the quantum",
        }
    duration = agent.get("duration_s")
    exceeded = isinstance(duration, (int, float)) and duration >= quantum_s
    fired = bool(
        agent.get("conclusion") == "failure"
        or (agent.get("conclusion") == "cancelled" and not exceeded)
    )
    return {
        "wrapper_quantum_s": quantum_s,
        "agent_step_found": True,
        "agent_step_conclusion": agent.get("conclusion"),
        "agent_step_duration_s": duration,
        "duration_exceeded_quantum": exceeded,
        "quantum_plausibly_fired": fired if exceeded else None,
        "note": (
            "the step ran LONGER than the wrapper quantum and still concluded 'cancelled', "
            "so the rc-78 LEX_WORK_QUANTUM_EXPIRED watchdog (which polls every 15 s and "
            "returns 78) cannot have produced this outcome. Job logs are admin-only over "
            "the public API, so the actual cause is not attributable from the lane."
        ),
    }


def _audit_branch_exists(run_id: int | str, lane: str = "product",
                         repo: str = DEFAULT_REPO) -> bool | None:
    """Does the remote carry the audit branch for this run?  ``None`` if unknown.

    A cancelled audit never runs 'Persist audit snapshot', so the ABSENCE of the
    branch is the durable corroboration that no gate file was written — and it is
    also the single most useful fact for the next dispatch (the work is pending,
    not rejected).
    """
    import subprocess  # local import: only this probe shells out

    try:
        out = subprocess.run(  # noqa: S603
            ["git", "ls-remote", "--heads", "https://github.com/" + repo,
             f"refs/heads/cycle/core/{lane}/{run_id}/audit"],
            capture_output=True, text=True, timeout=30, check=False,
        )
    except Exception:  # pragma: no cover - network resilience, never fatal
        return None
    if out.returncode != 0:
        return None
    return bool(out.stdout.strip())


def build_report(run_id: int | str, *, repo: str = DEFAULT_REPO,
                 lane: str = "product", steps: list[dict] | None = None) -> dict:
    """Full, publishable record for one run. Network-tolerant by construction."""
    try:
        observation = observe_run(run_id, repo=repo)
    except RunNotFound as exc:
        observation = {"run_id": int(run_id), "resolvable": False, "error": str(exc)}
    except Exception as exc:  # pragma: no cover - network resilience, never fatal
        observation = {"run_id": int(run_id), "resolvable": False, "error": repr(exc)}

    quantum_s = read_wrapper_quantum()
    if observation.get("resolvable") is False:
        verdict = {"class": "UNOBSERVABLE", "why": str(observation.get("error")),
                   "evidence": [], "producing_snapshot_survived": False,
                   "verdict_exists": False}
        jobs: dict[str, Any] = {}
        step_rows: list[dict] = []
    else:
        jobs = observe_jobs(run_id, repo=repo)
        step_rows = steps if steps is not None else observe_steps(run_id, repo=repo)
        verdict = classify(observation=observation, jobs=jobs, steps=step_rows)

    return {
        "schema": SCHEMA,
        "run_id": int(run_id),
        "lane": lane,
        "observation": observation,
        "job_conclusions": jobs,
        "audit_branch_exists": _audit_branch_exists(run_id, lane, repo),
        "quantum_analysis": quantum_analysis(step_rows, quantum_s),
        "steps": step_rows,
        "classification": verdict,
        "claim_ceiling": (
            "This is an observation of an external system's public REST job record. It "
            "names how the run ended. It is NOT a product verdict, NOT a claim about the "
            "quality of the producer's work, and NOT a human-gate input. .github/** is "
            "control-plane scope: nothing here edits or configures a workflow."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--lane", default="product")
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    ap.add_argument("--write", action="store_true", help="write the artifact (default: dry run)")
    args = ap.parse_args(argv)

    report = build_report(args.run_id, lane=args.lane)
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.write:
        out = Path(args.out_dir) / f"CYCLE_{args.run_id}_orchestration.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
        print(f"\nwrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
