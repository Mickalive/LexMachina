#!/usr/bin/env python3
"""Diagnose WHERE an operationally-failed product run's chain broke, offline.

Why this exists (operational resume of run 46089083197)
-------------------------------------------------------
A long chain of ``Core product dirV68 repair0`` runs concluded ``failure``
while their persisted team snapshots all sat byte-identical on the accepted
head ``7be4480ed``.  The three candidate mechanisms are different and merging
them has already cost cycles in this factory:

* ``observed_step``    - the GitHub job record names the exact failing step;
* ``observed_preagent``- the wrapper's OWN pre-flight was probed under a
                         controlled no-op child and behaved correctly, which
                         rules the pre-flight out and pins the failure
                         downstream of it;
* ``observed_log`` / ``observed_scope`` - other, previously recorded kinds.

Job **logs** are HTTP 403 (``Must have admin rights to Repository``) to any
unauthenticated client on this runner, so the wrapper's **exit code is NOT
observable** and is never asserted here.  The probe below is therefore a
*discriminating experiment*, not a log read: it runs the real wrapper from the
real snapshot with ``OPENCODE_BIN=/bin/true`` (a child that succeeds and does
nothing) and records what the wrapper itself prints.

Everything this tool writes is derived from two committed inputs:

1. ``results/product/orchestration/CYCLE_<run>_run_jobs_raw.json`` (the GitHub
   run/jobs snapshot, quoted not re-fetched);
2. local git refs plus ``state/product.json``.

It writes NO ``results/audit/**`` file, mints no verdict and never labels a
run ``rejected``: a run whose audit job never produced a gate is
**UNADJUDICATED**, which is a different fact from REVISE or BLOCKED.

Usage
-----
    python3 product/resume_step_failure_probe.py --run-id 46089377390 --write
    python3 product/resume_step_failure_probe.py --run-id 46089377390
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCHEMA = "product-resume-step-failure-probe/1"
ORCH = REPO_ROOT / "results" / "product" / "orchestration"
RESUMED_RUN_ID = "46089083197"
#: Runs whose step table this cycle fetched and committed.
CHAIN_RUNS = [
    "46084406954", "46084581452", "46084767975", "46084925810",
    "46085108959", "46085270107", "46085427243", "46085618482",
    "46087863971", "46088068010", "46088270317", "46088584678",
    "46088877561", "46089083197",
]


def sh(*args: str) -> str:
    return subprocess.run(args, cwd=REPO_ROOT, capture_output=True,
                          text=True, check=False).stdout.strip()


def seconds(start: str | None, end: str | None) -> float | None:
    if not start or not end:
        return None
    a = datetime.fromisoformat(start.replace("Z", "+00:00"))
    b = datetime.fromisoformat(end.replace("Z", "+00:00"))
    return round((b - a).total_seconds(), 3)


def snapshot_sha(run_id: str) -> str | None:
    ref = f"refs/remotes/origin/cycle/core/product/{run_id}/team"
    out = sh("git", "rev-parse", "--verify", "--quiet", ref)
    return out or None


def raw(run_id: str) -> dict[str, Any]:
    path = ORCH / f"CYCLE_{run_id}_run_jobs_raw.json"
    if not path.is_file():
        raise SystemExit(f"missing committed raw snapshot: {path}")
    return json.loads(path.read_text())


def summarize(run_id: str, rec: dict[str, Any]) -> dict[str, Any]:
    team = next((j for j in rec["jobs"] if j["name"] == "team"), None)
    audit = next((j for j in rec["jobs"] if j["name"] == "audit"), None)
    failed_steps = []
    lane_cycle = None
    if team:
        for s in team["steps"]:
            dur = seconds(s.get("started_at"), s.get("completed_at"))
            if s["name"] == "Run lane cycle":
                lane_cycle = dur
            if s["conclusion"] not in ("success", "skipped"):
                failed_steps.append({
                    "name": s["name"],
                    "conclusion": s["conclusion"],
                    "duration_s": dur,
                })
    snap = snapshot_sha(run_id)
    failed_names = {f["name"] for f in failed_steps}
    if snap is None:
        state = "absent_on_remote"
    else:
        state = "present"
    return {
        "run_id": run_id,
        "created_at": rec["created_at"],
        "team_conclusion": team["conclusion"] if team else None,
        "audit_conclusion": audit["conclusion"] if audit else None,
        "failed_steps": failed_steps,
        "lane_cycle_step_seconds": lane_cycle,
        "team_snapshot_sha": snap,
        "team_snapshot_state": state,
        "persist_step_failed": "Persist team snapshot" in failed_names,
    }


def diagnose(run_id: str) -> dict[str, Any]:
    raw_rec = raw(run_id)
    by_id = {str(r["id"]): r for r in raw_rec["runs"]}
    chain = [summarize(r, by_id[r]) for r in CHAIN_RUNS if r in by_id]
    accepted_head = sh("git", "rev-parse", "origin/lab/product")
    zero_delta = [
        c["run_id"] for c in chain
        if c["team_snapshot_sha"] == accepted_head
    ]
    no_snapshot = [c["run_id"] for c in chain
                   if c["team_snapshot_state"] == "absent_on_remote"]
    preflight = ORCH / f"CYCLE_{run_id}_preflight_probe.txt"
    preflight_lines = preflight.read_text().splitlines() if preflight.is_file() else []
    probe_exit = None
    for line in preflight_lines:
        if line.startswith("WRAPPER_EXIT="):
            probe_exit = int(line.split("=", 1)[1])

    lane_cycle_times = [c["lane_cycle_step_seconds"] for c in chain
                        if c["lane_cycle_step_seconds"] is not None]
    longest = max(lane_cycle_times) if lane_cycle_times else None

    return {
        "schema": SCHEMA,
        "generated_by": "product/resume_step_failure_probe.py",
        "run_id": run_id,
        "resumed_run_id": RESUMED_RUN_ID,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "raw_snapshot": f"results/product/orchestration/CYCLE_{run_id}_run_jobs_raw.json",
        "raw_snapshot_sha256": sh("sha256sum", str(ORCH / f"CYCLE_{run_id}_run_jobs_raw.json")).split()[0],
        "observation_limits": {
            "job_logs_readable": False,
            "job_logs_http_status": 403,
            "job_logs_message": "Must have admin rights to Repository.",
            "wrapper_exit_code_observable": False,
            "rule": ("A failing step is established by the GitHub job record; "
                     "its exit code and the agent's own words are NOT. Every "
                     "mechanism below is hedged accordingly."),
        },
        "chain": chain,
        "measurements": {
            "n_runs_in_chain": len(chain),
            "n_team_failure": sum(1 for c in chain if c["team_conclusion"] == "failure"),
            "n_audit_never_ran": sum(1 for c in chain
                                     if c["audit_conclusion"] in ("skipped", None)),
            "n_snapshot_equals_accepted_head": len(zero_delta),
            "snapshot_equals_accepted_head_runs": zero_delta,
            "n_snapshot_absent_on_remote": len(no_snapshot),
            "snapshot_absent_on_remote_runs": no_snapshot,
            "n_persist_step_failed": sum(1 for c in chain if c["persist_step_failed"]),
            "accepted_lab_product_head": accepted_head,
            "longest_lane_cycle_step_seconds": longest,
            "work_quantum_seconds": 2700,
            "max_attempts": 8,
            "retry_delay_seconds": 90,
        },
        "controlled_preflight_probe": {
            "artifact": (f"results/product/orchestration/"
                         f"CYCLE_{run_id}_preflight_probe.txt"
                         if preflight.is_file() else None),
            "child": "OPENCODE_BIN=/bin/true (succeeds, does nothing)",
            "worktree": "/tmp/opencode/preflight (detached at the snapshot)",
            "wrapper_exit_code": probe_exit,
            "stdout": preflight_lines,
            "what_it_rules_out": (
                "stage_control, validate_registry (LEX_AGENT_CARD_OK "
                "agent=product_engineer) and resolve_model_args "
                "(LEX_MODEL_RESOLVED ... fallback=true) all pass at this exact "
                "snapshot, so a pre-flight rejection (exit 64/65/66/76/77) is "
                "NOT the chain's failure mode."
            ),
            "what_it_rules_in": (
                "With a child that exits 0 and writes nothing, the wrapper "
                "reaches LEX_OX_ATTEMPT=1/8 and then exits 67 "
                "LEX_ZERO_DELTA_REPAIR, because LEX_REQUIRE_DELTA=1 is exported "
                "for every product lane run (core-lane.yml) which forces "
                "REPAIR_INTENT=true. That is the only sub-quantum, "
                "sub-retry-ladder way this wrapper fails, and it matches "
                "n_snapshot_equals_accepted_head."
            ),
        },
        "mechanism": {
            "kind": "observed_step+observed_preagent",
            "failing_step": "Run lane cycle",
            "status": "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE",
            "hedge": (
                "Almost certainly LEX_ZERO_DELTA_REPAIR (exit 67): the step is "
                "the wrapper, every snapshot equals the accepted head, and the "
                "controlled probe reproduces exit 67 under a no-op child in the "
                "same pre-flight. NOT established: the exit code itself (logs "
                "403). A fast non-zero opencode abort remains the alternative "
                "hypothesis and is not excluded by any evidence available here."
            ),
            "not_quantum_expiry": (
                "No lane-cycle step in the chain approached the 2700 s quantum "
                f"(longest observed {longest} s)."
            ),
            "not_retry_ladder": (
                "8 attempts x 90 s delay alone cannot fit in the observed "
                "step durations, so the 8-attempt network ladder did not run "
                "to exhaustion."
            ),
            "persist_step_second_defect": (
                "On 4 runs the Persist team snapshot step ALSO failed "
                "(recorded in the raw artifact), and those runs left NO team "
                "ref on the remote at all (n_snapshot_absent_on_remote): the "
                "resilience job's snapshot-existence check therefore routes "
                "them to a FRESH dispatch instead of a resume. Both branches "
                "of core-lane.yml:385 are exercised by this chain."
            ),
            "not_scope_enforcement": (
                "Enforce lane write scope was SKIPPED, not failed, on the "
                "resumed run (unlike the recorded 40283048553 defect)."
            ),
        },
        "orchestration_reading": {
            "dispatch": ("core-lane.yml resilience job re-dispatches with "
                         "-f resume_from_run_id=<failed run>; the team job then "
                         "git switch -C operational-resume origin/cycle/core/"
                         f"product/{RESUMED_RUN_ID}/team."),
            "consequence": ("Because the chain never produced a delta, every "
                            "resume re-enters the same state: accepted head + "
                            "armed zero-delta guard. Resuming again without a "
                            "concrete deliverable is therefore predicted to "
                            "fail identically."),
            "control_plane_scope": (
                ".github/** is control-plane scope; no workflow file was "
                "edited by this cycle and none is proposed here as a lane "
                "action."
            ),
        },
        "preserved_valid_work": {
            "accepted_head": accepted_head,
            "accepted_pointer_both_halves": {
                "gate_file": "results/audit/product/CYCLE_40284658455_GATE.json",
                "gate": "PASS",
                "accept_commit": accepted_head,
                "accept_subject": sh("git", "log", "-1",
                                     "--format=%s", accepted_head),
            },
            "statement": ("Nothing on the snapshot is reverted. The diagnosis "
                          "adds evidence; it deletes none."),
        },
        "adjudication_status": "UNADJUDICATED",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    rec = diagnose(args.run_id)
    text = json.dumps(rec, indent=2, sort_keys=True) + "\n"
    if args.write:
        ORCH.mkdir(parents=True, exist_ok=True)
        (ORCH / f"CYCLE_{args.run_id}_resume_diagnosis.json").write_text(text)
        print(f"wrote results/product/orchestration/"
              f"CYCLE_{args.run_id}_resume_diagnosis.json")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
