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
import re
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

#: Bumped only when a key is REMOVED or its meaning changes.  ``diagnosis`` was
#: added additively in cycle 39087917357, so older committed artifacts stay
#: valid under the same schema and are never rewritten to match.
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
    "TEAM_JOB_CANCELLED",
    "NO_AUDIT_JOB",
    "UNOBSERVABLE",
)

#: Keys a core-lane artifact must NEVER carry: a gate decision or an owner-session
#: flag.  This belongs with the artifact schema, not in the ledger module: a
#: caller that publishes "the artifact carries no gate" consumes this list, and
#: the ledger module that verifies it must not itself look like a gate consumer.
FORBIDDEN_VERDICT_KEYS = (
    "gate",
    "safe_to_integrate",
    "human_gate_ready",
    "ready_for_owner_session",
    "packet_admitted",
)


def forbidden_verdict_keys(data: dict) -> list[str]:
    """Keys of ``data`` that no core-lane artifact is allowed to carry."""
    return [k for k in FORBIDDEN_VERDICT_KEYS if k in data]


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


def classify(*, observation: dict | None, jobs: dict, steps: list[dict],
             team_branch_exists: bool | None = None) -> dict:
    """Name the death class of a core-lane run. Pure function of its record.

    ``team_branch_exists`` is the ONE fact this function cannot read out of a job
    record: a cancelled producer can still have committed its deliverable and
    pushed ``cycle/core/<lane>/<run>/team``.  Whether the snapshot survived is a
    property of the REMOTE BRANCH, so it is passed in (and published) rather than
    inferred from the job's ``conclusion``, which a cancellation flips to a value
    that would otherwise read as "produced nothing".
    """
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
    if team == "cancelled":
        klass = "TEAM_JOB_CANCELLED"
        why = (
            "the producer job was cancelled (by the Actions bot or the platform), "
            "so the audit never became eligible. Unlike a failure this carries no "
            "wrapper exit code; the producing snapshot may still have survived, "
            "and that is read from the team branch, never from this conclusion."
        )
    elif team in ("failure", "timed_out"):
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
        # A succeeded producer trivially survived; a failed OR cancelled one is
        # decided by whether its snapshot branch was actually pushed, never by
        # the job conclusion alone (39087917357: team 'cancelled', branch exists).
        "producing_snapshot_survived": bool(team == "success" or team_branch_exists is True),
        "team_branch_exists": team_branch_exists,
        "verdict_exists": klass not in (
            "UNOBSERVABLE",
            "NO_AUDIT_JOB",
            "TEAM_JOB_FAILED",
            "TEAM_JOB_CANCELLED",
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


# --------------------------------------------------------------------------
# Narrowing the cause space: public annotations + wrapper preflight replay
#
# Cycle 39086926860's audit job died in 16 s with no gate, and the step's
# ``conclusion`` alone ("failure") is shared by five mutually exclusive wrapper
# exits.  Job LOGS are admin-only over the public API (HTTP 403), but two OTHER
# records are public and were not being read:
#
#   1. the check-run ANNOTATIONS the runner attaches (``Process completed with
#      exit code N``), which pin the wrapper's exit code exactly;
#   2. the wrapper's own fail-fast PREFLIGHT (registry card check, model-health
#      check), which the lane can replay locally against the same inputs.
#
# Together those two turn "something in the audit step failed" into a short,
# machine-checkable list of surviving branches.  Nothing here edits .github/**;
# it only reads them.
# --------------------------------------------------------------------------

#: Named non-zero exits of ``.github/scripts/run-ox-with-retry.sh``.  ``rc`` is
#: what the wrapper's own ``exit`` statements produce, so an observed exit code
#: that is not listed can only have come from the generic branch (opencode's own
#: return code passed through untouched).
WRAPPER_EXIT_BRANCHES = (
    {"rc": 78, "name": "LEX_WORK_QUANTUM_EXPIRED",
     "produced_by": "the in-wrapper work-quantum watchdog",
     "requires": "the agent step ran at least WORK_QUANTUM_SECONDS"},
    {"rc": 67, "name": "LEX_ZERO_DELTA_REPAIR",
     "produced_by": "the zero-delta guard after a SUCCESSFUL agent run",
     "requires": "REPAIR_INTENT is set AND the agent exited 0 AND HEAD unchanged AND an empty git status"},
    {"rc": 75, "name": "TRANSIENT_RETRIES_EXHAUSTED",
     "produced_by": "retry loop exhaustion / network stall handling",
     "requires": "at least one attempt carried a transient network signature"},
    {"rc": 64, "name": "AGENT_CARD_MISSING", "produced_by": "validate_registry",
     "requires": "an agent file without exactly one canonical card"},
    {"rc": 65, "name": "AGENT_CARD_DISABLED", "produced_by": "validate_registry",
     "requires": "the requested agent card carries status=LEGACY_DISABLED"},
    {"rc": 66, "name": "AGENT_REGISTRY_MISMATCH", "produced_by": "validate_registry",
     "requires": "a card id with no agent file, or a card count != 1"},
    {"rc": 76, "name": "MODEL_HEALTH_UNUSABLE", "produced_by": "resolve_model_args",
     "requires": "model_health.json missing, healthy != true, or no resolved model"},
    {"rc": 77, "name": "MODEL_ARGUMENT_MISSING", "produced_by": "resolve_model_args",
     "requires": "the invocation did not pass --model"},
)

_EXIT_CODE_RE = re.compile(r"Process completed with exit code (-?\d+)")


def observe_annotations(run_id: int | str, repo: str = DEFAULT_REPO,
                        fetch: Callable = http_fetch) -> list[dict]:
    """Public check-run annotations for every job of one run (network).

    The lane cannot read job LOGS (they are admin-only and answer HTTP 403), so
    an exit code used to be unattributable from here.  The annotations the
    runner attaches to the check run ARE public, and they carry the literal
    ``Process completed with exit code N`` line.  That is the one number needed
    to split the wrapper's mutually exclusive exits.

    Never fatal: an unreachable API yields ``[]``, which is recorded as
    "not collected" rather than as "no annotations exist".
    """
    url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/jobs?per_page=100"
    try:
        status, payload = fetch(url)
    except Exception:  # pragma: no cover - network resilience, never fatal
        return []
    if status != 200 or not isinstance(payload, dict):
        return []
    rows: list[dict] = []
    for job in payload.get("jobs") or []:
        if not isinstance(job, dict) or not job.get("id"):
            continue
        try:
            a_status, a_payload = fetch(
                f"https://api.github.com/repos/{repo}/check-runs/{job['id']}/annotations"
                "?per_page=100"
            )
        except Exception:  # pragma: no cover - network resilience, never fatal
            continue
        if a_status != 200 or not isinstance(a_payload, list):
            continue
        for ann in a_payload:
            if not isinstance(ann, dict):
                continue
            rows.append({
                "job_id": job.get("id"),
                "job": job.get("name"),
                "job_conclusion": job.get("conclusion"),
                "annotation_level": ann.get("annotation_level"),
                "message": (ann.get("message") or "").strip(),
            })
    return rows


def parse_exit_code(annotations: list[dict]) -> dict:
    """Pull the wrapper's exit code out of the annotations.  Pure function.

    Returns ``{"exit_code": int|None, "evidence": str}``.  When several jobs
    annotate an exit code, only the code on a job that CONCLUDED failure is
    accepted, because a skipped/successful job's code is not the failure.
    """
    failing = [a for a in annotations if a.get("job_conclusion") in ("failure", "timed_out")]
    pool = failing or list(annotations)
    for ann in pool:
        match = _EXIT_CODE_RE.search(ann.get("message") or "")
        if match:
            return {"exit_code": int(match.group(1)),
                    "evidence": (f"{ann.get('job')} job annotation: "
                                 f"{match.group(0)!r}")}
    return {"exit_code": None,
            "evidence": "no annotation carried a 'Process completed with exit code' line"}


def read_wrapper_retry_params(root: Path = REPO_ROOT) -> dict:
    """Read the retry loop's own constants out of the wrapper (never hard-coded)."""
    import re as _re

    script = root / ".github" / "scripts" / "run-ox-with-retry.sh"
    try:
        text = script.read_text(encoding="utf-8")
    except OSError:
        return {"source": "absent", "max_attempts": None, "retry_delay_s": None}
    ma = _re.search(r'MAX_ATTEMPTS="\$\{OX_MAX_ATTEMPTS:-(\d+)\}"', text)
    rd = _re.search(r'RETRY_DELAY="\$\{OX_RETRY_DELAY_SECONDS:-(\d+)\}"', text)
    return {"source": str(script),
            "max_attempts": int(ma.group(1)) if ma else None,
            "retry_delay_s": int(rd.group(1)) if rd else None}


def wrapper_exit_candidates(rc: int | None, *, step_duration_s: float | None,
                            quantum_s: int, retry: dict | None = None) -> dict:
    """Which wrapper exits can still explain an observed exit code.  Pure function.

    Two independent exclusions are applied and BOTH are published:

    * **code exclusion** — each named exit emits its own fixed code, so a
      different observed code rules it out outright;
    * **arithmetic exclusion** — a branch cannot have fired before the time it
      needs (the quantum needs ``quantum_s``; the retry loop needs one
      ``retry_delay_s`` sleep per extra attempt).

    A branch is only reported as surviving when it survives BOTH.
    """
    retry = retry or {}
    delay = retry.get("retry_delay_s")
    max_attempts = retry.get("max_attempts")
    candidates = []
    for branch in WRAPPER_EXIT_BRANCHES:
        reasons_out, reasons_in = [], []
        if rc is None:
            reasons_out.append("no exit code observed")
        elif rc != branch["rc"]:
            reasons_out.append(f"observed exit code {rc} != this branch's fixed code {branch['rc']}")
        else:
            reasons_in.append(f"observed exit code matches this branch's fixed code {rc}")

        if branch["rc"] == 78 and isinstance(step_duration_s, (int, float)) \
                and step_duration_s < quantum_s:
            reasons_out.append(
                f"the step ran {step_duration_s} s < quantum {quantum_s} s, so the "
                "watchdog had not fired yet")
        if branch["rc"] == 75 and isinstance(delay, int) \
                and isinstance(step_duration_s, (int, float)) \
                and step_duration_s < delay:
            reasons_out.append(
                f"the step ran {step_duration_s} s < one retry delay of {delay} s, so "
                "the retry loop cannot have exhausted its attempts")
        if branch["rc"] == 75 and isinstance(delay, int) and isinstance(max_attempts, int) \
                and isinstance(step_duration_s, (int, float)) \
                and step_duration_s < (max_attempts - 1) * delay:
            reasons_in.append(
                f"{max_attempts} attempts x {delay} s delay cannot fit inside "
                f"{step_duration_s} s, so at most one attempt ran")

        candidates.append({
            "branch": branch["name"],
            "rc": branch["rc"],
            "produced_by": branch["produced_by"],
            "requires": branch["requires"],
            "ruled_out": bool(reasons_out),
            "ruled_out_evidence": reasons_out,
            "consistent_evidence": reasons_in,
        })

    surviving = [c["branch"] for c in candidates if not c["ruled_out"]]
    generic = rc is not None and rc not in {b["rc"] for b in WRAPPER_EXIT_BRANCHES}
    return {
        "exit_code": rc,
        "quantum_s": quantum_s,
        "retry_params": retry,
        "step_duration_s": step_duration_s,
        "named_branches": candidates,
        "surviving_named_branches": surviving,
        "generic_passthrough_possible": bool(generic),
        "generic_passthrough_note": (
            f"exit code {rc} is not one of the wrapper's own fixed codes, so it can only "
            "have come from the wrapper's `exit \"$rc\"` passthrough of opencode's own "
            "return code (the 'OpenCode failed without transient signature' branch) "
            "or from `restore_overlay || exit 1` on an otherwise clean run"
        ) if generic else None,
        "claim_ceiling": (
            "This narrows which wrapper exit COULD have produced the observed code. It "
            "does not name opencode's internal error: job logs stay admin-only, so the "
            "innermost cause is not attributable from the lane."
        ),
    }


def replay_wrapper_preflight(control_dir: Path, agents_dir: Path,
                             requested_agent: str = "independent_auditor") -> dict:
    """Re-run the wrapper's two fail-fast preflights locally.  Local, no network.

    ``validate_registry`` and ``resolve_model_args`` are the only wrapper exits
    that fire BEFORE opencode is launched, so replaying them against the same
    inputs the run saw either reproduces the failure (exit 64/65/66/76/77) or
    rules those exits out with a concrete, checkable result instead of prose.
    """
    registry_problems, cards = [], {}
    registry = control_dir / "docs" / "agents" / "AGENT_CARDS.md"
    try:
        registry_text = registry.read_text(encoding="utf-8")
    except OSError as exc:
        registry_text = None
        registry_problems.append(f"missing canonical registry: {exc}")

    agent_files = sorted(p for p in agents_dir.glob("*.md")) if agents_dir.is_dir() else []
    if not agent_files:
        registry_problems.append(f"no agent definitions under {agents_dir}")
    if registry_text is not None:
        for path in agent_files:
            agent_id = path.stem
            count = registry_text.count(f"<!-- AGENT_CARD: {agent_id} ")
            cards[agent_id] = count
            if count != 1:
                registry_problems.append(
                    f"agent {agent_id} has {count} cards; expected 1")
        for card_id in re.findall(r"^<!-- AGENT_CARD:\s+(\S+)", registry_text, re.M):
            if not (agents_dir / f"{card_id}.md").is_file():
                registry_problems.append(f"card {card_id} has no agent definition")
        marker = re.search(
            rf"<!-- AGENT_CARD:\s+{re.escape(requested_agent)}\s+[^\n]*", registry_text)
        if not marker:
            registry_problems.append(f"{requested_agent} lacks a canonical card")
        elif "status=LEGACY_DISABLED" in marker.group(0):
            registry_problems.append(f"{requested_agent} is disabled")

    model_path = control_dir / "state" / "model_health.json"
    model_problems = []
    model_record: dict[str, Any] = {"path": str(model_path)}
    try:
        health = json.loads(model_path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - missing/corrupt file
        health = None
        model_problems.append(f"LEX_MODEL_HEALTH_MISSING ({exc})")
    if health is not None:
        model_record.update({
            "healthy": health.get("healthy"),
            "resolved_model": health.get("resolved_model"),
            "using_fallback": health.get("using_fallback"),
            "last_checked_at": health.get("last_checked_at"),
            "last_checked_run_id": health.get("last_checked_run_id"),
        })
        if health.get("healthy") is not True or not health.get("resolved_model"):
            model_problems.append("LEX_NO_HEALTHY_FREE_TOOL_MODEL")

    if registry_problems:
        would_exit: int | None = 64 if "lacks a canonical card" in " ".join(registry_problems) \
            else 65 if any("disabled" in p for p in registry_problems) else 66
    elif model_problems:
        would_exit = 76
    else:
        would_exit = None

    return {
        "requested_agent": requested_agent,
        "registry": {"pass": not registry_problems, "problems": registry_problems,
                     "card_counts": cards, "agent_dir": str(agents_dir),
                     "registry_path": str(registry)},
        "model_health": {"pass": not model_problems, "problems": model_problems,
                         "record": model_record},
        "would_exit": would_exit,
        "all_pass": not registry_problems and not model_problems,
        "claim_ceiling": (
            "A local replay of the wrapper's preflight against the control-plane inputs. "
            "It reproduces or rules out the pre-opencode exits (64/65/66/76/77) only; it "
            "says nothing about failures inside opencode."
        ),
    }


def diagnose(*, annotations: list[dict], steps: list[dict], quantum_s: int,
             preflight: dict, annotations_collected: bool = False) -> dict:
    """Join the public exit-code evidence with the preflight replay.  Pure function."""
    exit_info = parse_exit_code(annotations) if annotations else {
        "exit_code": None, "evidence": "annotations were not collected for this report"}
    agent_step = next(
        (s for s in steps if (s.get("job") or "").lower() == "audit"
         and "independent audit" in (s.get("step") or "").lower()), None)
    duration = agent_step.get("duration_s") if agent_step else None
    candidates = wrapper_exit_candidates(exit_info["exit_code"], step_duration_s=duration,
                                         quantum_s=quantum_s,
                                         retry=read_wrapper_retry_params())
    preflight_rules_out = []
    preflight_keeps_open = []
    if preflight.get("all_pass"):
        preflight_rules_out = [64, 65, 66, 76, 77]
        preflight_keeps_open = []
    elif preflight.get("would_exit") is not None:
        preflight_keeps_open = [preflight["would_exit"]]
    for cand in candidates["named_branches"]:
        # Corroboration is recorded even when the exit code ALREADY ruled the
        # branch out: two independent exclusions agreeing is stronger evidence
        # than either one alone, and a reader must see both.  When the OBSERVED
        # code IS this branch's code, the exit code outranks the replay (the
        # inputs may have changed since the run), so the disagreement is
        # disclosed instead of being used to rule the branch out.
        if cand["rc"] in preflight_rules_out:
            if cand["ruled_out"]:
                cand["preflight_rules_out"] = True
                cand["ruled_out_evidence"].append(
                    "the wrapper's own preflight replays clean locally (registry + model "
                    "health), so this pre-opencode exit did not fire")
            else:
                cand["preflight_rules_out"] = False
                cand["consistent_evidence"].append(
                    "the local preflight replay passes today while the observed exit code "
                    "IS this branch's code; the replay inputs may differ from the inputs "
                    "the run saw, so the exit code decides and this branch stays open")
        else:
            cand["preflight_rules_out"] = False
            if cand["rc"] in preflight_keeps_open and not cand["ruled_out"]:
                cand["consistent_evidence"].append(
                    "the local preflight replay FAILS the same way, so this exit is still open")
    candidates["surviving_named_branches"] = [
        c["branch"] for c in candidates["named_branches"] if not c["ruled_out"]]
    return {
        "annotations_collected": annotations_collected,
        "annotations": annotations,
        "exit_code": exit_info["exit_code"],
        "exit_code_evidence": exit_info["evidence"],
        "audit_agent_step_duration_s": duration,
        "preflight": preflight,
        "candidates": candidates,
    }


def _remote_branch_exists(ref: str, repo: str = DEFAULT_REPO) -> bool | None:
    """Is ``ref`` present on the remote?  ``None`` when it cannot be observed.

    Network-tolerant by construction: ``git ls-remote`` may fail, and a failure
    must read as UNKNOWN rather than as "branch absent", so a cancelled run is
    never mislabelled as having lost its snapshot.
    """
    import subprocess  # local import: only this probe shells out

    try:
        out = subprocess.run(  # noqa: S603
            ["git", "ls-remote", "--exit-code", "--heads",
             "https://github.com/" + repo, ref],
            capture_output=True, text=True, timeout=30, check=False,
        )
    except Exception:  # pragma: no cover - network resilience, never fatal
        return None
    if out.returncode not in (0, 2):  # 0 = found; 2 = ls-remote --exit-code: absent
        return None
    return out.returncode == 0 and bool(out.stdout.strip())


def _audit_branch_exists(run_id: int | str, lane: str = "product",
                         repo: str = DEFAULT_REPO) -> bool | None:
    """Does the remote carry the audit branch for this run?  ``None`` if unknown.

    A cancelled audit never runs 'Persist audit snapshot', so the ABSENCE of the
    branch is the durable corroboration that no gate file was written — and it is
    also the single most useful fact for the next dispatch (the work is pending,
    not rejected).
    """
    return _remote_branch_exists(f"refs/heads/cycle/core/{lane}/{run_id}/audit", repo)


def _team_branch_exists(run_id: int | str, lane: str = "product",
                        repo: str = DEFAULT_REPO) -> bool | None:
    """Does the remote carry the PRODUCER snapshot branch for this run?

    The producer's keep-branch name mirrors the workflow's "Persist team
    snapshot" step.  Its presence is what makes a cancelled team job's product
    recoverable, so it — not the job conclusion — decides whether the snapshot
    survived.
    """
    return _remote_branch_exists(f"refs/heads/cycle/core/{lane}/{run_id}/team", repo)


def default_control_dir() -> Path:
    """Where the wrapper would stage the control plane from (``stage_control``).

    The harness mount is authoritative when present; otherwise the checkout's
    own copy of the same files is the honest fallback, and which one was used is
    published with the result rather than assumed.
    """
    mounted = Path("/tmp/lex_control")
    if (mounted / "state").is_dir():
        return mounted
    return REPO_ROOT


def wrapper_script_sources(root: Path = REPO_ROOT) -> dict:
    """Where each wrapper number actually came from.  Published, never assumed.

    ``run-ox-with-retry.sh`` re-executes ``origin/main``'s copy of itself when
    the checkout's copy differs, so a locally-read number can be the FALLBACK
    constant rather than the script's.  A reader must be able to tell those two
    apart instead of being told "read from the wrapper".
    """
    script = root / ".github" / "scripts" / "run-ox-with-retry.sh"
    try:
        text = script.read_text(encoding="utf-8")
    except OSError:
        return {"script": str(script), "present": False,
                "quantum_source": "default_fallback (script absent)",
                "retry_source": "default_fallback (script absent)"}
    return {
        "script": str(script),
        "present": True,
        "quantum_source": "script"
        if 'WORK_QUANTUM_SECONDS="${LEX_AGENT_QUANTUM_SECONDS:' in text
        else "default_fallback (this checkout's copy has no WORK_QUANTUM_SECONDS; "
             "origin/main's copy does, and the wrapper re-executes main's copy at "
             "runtime, so the fallback value 2700 equals main's script value)",
        "retry_source": "script" if 'MAX_ATTEMPTS="${OX_MAX_ATTEMPTS:' in text
        else "default_fallback (script absent or missing MAX_ATTEMPTS)",
    }


def build_report(run_id: int | str, *, repo: str = DEFAULT_REPO,
                 lane: str = "product", steps: list[dict] | None = None,
                 annotations: list[dict] | None = None) -> dict:
    """Full, publishable record for one run. Network-tolerant by construction.

    ``annotations`` defaults to ``None`` meaning *not collected*, which keeps
    this function's network surface exactly what it was before the ``diagnosis``
    key existed.  The CLI passes real annotations so the published artifact
    carries the public exit-code evidence.
    """
    # The two remote branches are read FIRST: they are the observation that no
    # REST record contains, and the producer branch is what decides whether a
    # cancelled team job's product survived.
    team_branch_exists = _team_branch_exists(run_id, lane, repo)
    audit_branch_exists = _audit_branch_exists(run_id, lane, repo)

    try:
        observation = observe_run(run_id, repo=repo)
    except RunNotFound as exc:
        observation = {"run_id": int(run_id), "resolvable": False, "error": str(exc)}
    except Exception as exc:  # pragma: no cover - network resilience, never fatal
        observation = {"run_id": int(run_id), "resolvable": False, "error": repr(exc)}

    quantum_s = read_wrapper_quantum()
    if observation.get("resolvable") is False:
        verdict = {"class": "UNOBSERVABLE", "why": str(observation.get("error")),
                   "evidence": [], "producing_snapshot_survived": team_branch_exists is True,
                   "team_branch_exists": team_branch_exists, "verdict_exists": False}
        jobs: dict[str, Any] = {}
        step_rows: list[dict] = []
    else:
        jobs = observe_jobs(run_id, repo=repo)
        step_rows = steps if steps is not None else observe_steps(run_id, repo=repo)
        verdict = classify(observation=observation, jobs=jobs, steps=step_rows,
                           team_branch_exists=team_branch_exists)

    control = default_control_dir()
    diagnosis = diagnose(
        annotations=list(annotations or []),
        steps=step_rows,
        quantum_s=quantum_s,
        preflight=replay_wrapper_preflight(control, REPO_ROOT / ".opencode" / "agents"),
        annotations_collected=annotations is not None,
    )
    diagnosis["control_plane_source"] = str(control)

    return {
        "schema": SCHEMA,
        "run_id": int(run_id),
        "lane": lane,
        "observation": observation,
        "job_conclusions": jobs,
        "team_branch_exists": team_branch_exists,
        "audit_branch_exists": audit_branch_exists,
        "quantum_analysis": quantum_analysis(step_rows, quantum_s),
        "wrapper_script": wrapper_script_sources(),
        "steps": step_rows,
        "classification": verdict,
        "diagnosis": diagnosis,
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
    ap.add_argument("--no-annotations", action="store_true",
                    help="skip the public check-run annotation fetch (exit code becomes unknown)")
    args = ap.parse_args(argv)

    ann = None if args.no_annotations else observe_annotations(args.run_id)
    report = build_report(args.run_id, lane=args.lane, annotations=ann)
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
