#!/usr/bin/env python3
"""Why are consecutive product cycles still unadjudicated?  One machine answer.

A single run's diagnosis (:mod:`product.resume_snapshot_diagnosis`,
:mod:`product.audit_step_diagnosis`) answers "why did *this* run stop before a
gate".  This module answers the question the lane is actually stuck on: across
the persisted chain of product cycles since the last accepted head, *which*
failure mode hit *which* run, and does each run's committed delta violate the
workflow's lane write scope?  That second half is the one that can only be
answered from git, not from the run record: ``Enforce lane write scope`` exits 3
on the uncommitted tree, so the annotation says only "lane crossed protected
scope:" and never names the path.

Evidence surfaces, all local or public:
  * the committed ``CYCLE_<run>_run_jobs_raw.json`` snapshots (see
    :mod:`product.fetch_run_jobs_snapshot``) -> job/step conclusions,
    exit codes, quantum-expiry annotations;
  * local git refs ``origin/cycle/<lane>/<run>/{team,audit}`` and
    ``origin/lab/<lane>`` -> durable delta, scope violations, adjudication;
  * :mod:`product.state_contract` for the scope predicate itself, so the
    producer and this instrument agree with the workflow byte for byte.

It never fetches (a missing ref is reported as missing), never writes
``results/audit/**``, never mints a gate and never labels a run accepted.

Usage
-----
    python3 product/orchestration_chain.py \\
        --runs 44661217001,44669305676,44675979766,44682634688,44682877714,44683121773 \\
        --out results/product/orchestration/CYCLE_44683945698_chain_diagnosis.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from product import audit_step_diagnosis as asd  # noqa: E402
from product import state_contract as sc  # noqa: E402

ORCH = REPO_ROOT / "results" / "product" / "orchestration"


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(REPO_ROOT),
                          capture_output=True, text=True, check=False)


def _ref_sha(ref: str) -> str | None:
    out = _git("rev-parse", "--verify", "--quiet", ref)
    return out.stdout.strip() or None if out.returncode == 0 else None


def _delta_paths(base: str, head: str) -> list[str]:
    out = _git("diff", "--name-only", base, head)
    if out.returncode != 0:
        return []
    return [p.strip() for p in out.stdout.splitlines() if p.strip()]


def _has_accept_commit(lane: str, run_id: str, accepted_ref: str) -> bool:
    needle = f"accept {lane} cycle {run_id}"
    out = _git("log", "--format=%s", "-n", "50", accepted_ref)
    return any(line.strip() == needle for line in out.stdout.splitlines())


def diagnose(runs: list[str], lane: str = "product",
             accepted_ref: str = "origin/lab/product",
             raw_dir: Path = ORCH) -> dict:
    previous_head: str | None = _ref_sha(accepted_ref)
    accepted_head = previous_head
    entries = []
    for run_id in runs:
        team_ref = f"origin/cycle/core/{lane}/{run_id}/team"
        audit_ref = f"origin/cycle/core/{lane}/{run_id}/audit"
        team_sha = _ref_sha(team_ref)
        audit_sha = _ref_sha(audit_ref)

        raw_path = raw_dir / f"CYCLE_{run_id}_run_jobs_raw.json"
        orchestration = None
        if raw_path.is_file():
            try:
                orchestration = asd.classify(
                    json.loads(raw_path.read_text(encoding="utf-8")))
            except (ValueError, KeyError) as exc:
                orchestration = {"error": f"raw snapshot unreadable: {exc}"}

        delta_base = previous_head
        paths: list[str] = []
        if team_sha and delta_base:
            paths = _delta_paths(delta_base, team_sha)
        elif team_sha and not delta_base:
            paths = _delta_paths(team_sha, team_sha)
        violations = sc.scope_violations(paths)
        audit_ns = sc.audit_artifact_violations(paths)

        entry = {
            "run_id": run_id,
            "raw_snapshot": str(raw_path.relative_to(REPO_ROOT))
            if raw_path.is_file() else None,
            "orchestration": None if orchestration is None else {
                "classification": orchestration.get("classification"),
                "failed_team_step": (orchestration.get("team") or {}).get("failed_step"),
                "failed_audit_step": (orchestration.get("audit") or {}).get("failed_step"),
                "gate_file_written_by_workflow":
                    (orchestration.get("audit") or {}).get("gate_file_written"),
                "exit_code": (orchestration.get("mechanism") or {}).get("exit_code"),
                "quantum_expired": (orchestration.get("mechanism") or {}).get("quantum_expired"),
                "quantum_seconds": (orchestration.get("mechanism") or {}).get("quantum_seconds"),
                "annotations_available": (orchestration.get("mechanism") or {}).get("annotations_available"),
                "logs_endpoint_status": (orchestration.get("mechanism") or {}).get("logs_endpoint_status"),
            },
            "team_ref": team_ref,
            "team_sha": team_sha,
            "delta_base": delta_base,
            "delta_path_count": len(paths),
            "delta_paths": paths,
            "write_scope_violations": violations,
            "audit_namespace_writes": audit_ns,
            "write_scope_exit_would_be": 3 if violations else 0,
            "audit_ref_exists": audit_sha is not None,
            "audit_sha": audit_sha,
            "accept_commit_on_accepted_ref":
                _has_accept_commit(lane, run_id, accepted_ref)
            if accepted_head else False,
        }
        entry["adjudication"] = (
            "ACCEPTED"
            if entry["accept_commit_on_accepted_ref"] and audit_sha
            else "UNADJUDICATED"
        )
        entries.append(entry)
        if team_sha:
            previous_head = team_sha

    unadjudicated = [e["run_id"] for e in entries if e["adjudication"] == "UNADJUDICATED"]
    scope_failures = [
        {"run_id": e["run_id"], "violations": e["write_scope_violations"]}
        for e in entries if e["write_scope_violations"]
    ]
    quantum_audits = [
        e["run_id"] for e in entries
        if (e["orchestration"] or {}).get("quantum_expired")
        and (e["orchestration"] or {}).get("failed_audit_step")
    ]
    return {
        "schema": "product-orchestration-chain-diagnosis/1",
        "lane": lane,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "accepted_ref": accepted_ref,
        "accepted_ref_sha": accepted_head,
        "runs": entries,
        "summary": {
            "runs_diagnosed": len(entries),
            "accepted": [e["run_id"] for e in entries
                         if e["adjudication"] == "ACCEPTED"],
            "unadjudicated": unadjudicated,
            "runs_failing_write_scope": scope_failures,
            "runs_whose_audit_hit_work_quantum": quantum_audits,
            "all_runs_have_public_run_jobs_evidence": all(
                e["raw_snapshot"] for e in entries),
        },
        "claim_ceiling": (
            "Reported-only classification of committed run/jobs snapshots and "
            "local git refs. It writes no audit gate, mints no verdict, edits "
            "no frozen bar, and treats no run as accepted or rejected beyond "
            "the two observable halves of factory-wide requirement 4."
        ),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", required=True,
                    help="comma-separated run ids in chronological order")
    ap.add_argument("--lane", default="product")
    ap.add_argument("--accepted-ref", default="origin/lab/product")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    runs = [r.strip() for r in args.runs.split(",") if r.strip()]
    rec = diagnose(runs, args.lane, args.accepted_ref)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(json.dumps({"out": str(out), **rec["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
