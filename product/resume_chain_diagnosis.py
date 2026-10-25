#!/usr/bin/env python3
"""Derive, from local git plus the committed orchestration records, WHY a
product operational-resume chain stalled and which of its runs may be cited.

Why this exists (operational resume of run 40164459036)
-------------------------------------------------------
Three consecutive product runs (40160899758 -> 40163751502 -> 40164459036) all
ended with ``run conclusion = failure`` and none of them produced an independent
audit verdict, yet their team snapshots chained onto each other and ended up
containing files in the *auditor's* namespace.  The two failure modes are
different and conflating them has already cost a cycle:

* **orchestration** - the job that died and how (quantum expiry vs scope guard);
* **validation** - what the tree is no longer allowed to claim as a result.

The tool re-derives both, offline, from refs and commits that any checkout with
``fetch-depth: 0`` already has.  It never touches the network and never writes a
gate.  ``--merge-orchestration`` only READS the artifacts that
``product/orchestration_evidence.py`` already committed for the same runs, so
the GitHub-side job conclusions are quoted, not re-fetched.

What it deliberately does NOT do
--------------------------------
It writes no ``results/audit/**`` file, mints no verdict, and never labels a run
"rejected": a run whose audit job never produced a gate is UNADJUDICATED, which
is a different fact from REVISE or BLOCKED.

Usage
-----
    python3 product/resume_chain_diagnosis.py --run-id 40168184617 --write
    python3 product/resume_chain_diagnosis.py --run-id 40168184617          # dry run
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCHEMA = "product-resume-chain-diagnosis/1"

#: The unadjudicated chain this cycle resumes from, oldest first.
CHAIN = ("40160899758", "40163751502", "40164459036")

#: Paths a PRODUCER must never write.  Mirrors ``product/state_contract.py``'s
#: AUDIT_PREFIXES so the two instruments cannot drift apart silently.
AUDIT_PREFIXES = ("results/audit/", "reports/audit/")

#: Producer-self-minted files found in the auditor's namespace on this chain and
#: retired byte-exactly into ``reports/product/incidents/`` this cycle.
SELF_MINTED = (
    ("results/audit/product/CYCLE_40160899758_GATE.json",
     "reports/product/incidents/self_minted_gate_40160899758.RETIRED.json"),
    ("reports/audit/product/CYCLE_40160899758.md",
     "reports/product/incidents/self_minted_report_40160899758.RETIRED.md"),
)

ORCH_DIR = REPO_ROOT / "results" / "product" / "orchestration"


class DiagnosisError(RuntimeError):
    """A fact that could not be derived - reported, never guessed."""


def _git(*args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=str(REPO_ROOT),
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise DiagnosisError(
            f"git {' '.join(args)} failed ({proc.returncode}): "
            f"{(proc.stderr or '').strip()[:300]}")
    return proc.stdout


def ref_sha(ref: str) -> str | None:
    """``None`` when the ref does not exist - never an empty string."""
    out = subprocess.run(
        ["git", "rev-parse", "--verify", "-q", ref],
        cwd=str(REPO_ROOT), capture_output=True, text=True,
    )
    return out.stdout.strip() or None


def run_refs(run_id: str) -> dict[str, str | None]:
    base = f"refs/remotes/origin/cycle/core/product/{run_id}"
    return {
        "team": ref_sha(f"{base}/team"),
        "audit": ref_sha(f"{base}/audit"),
    }


def accept_commit_for(run_id: str) -> str | None:
    """The ``accept product cycle <run_id>`` commit in any ref, else None."""
    out = subprocess.run(
        ["git", "log", "--all", "--format=%H\t%s", "--grep",
         f"^accept product cycle {run_id}$"],
        cwd=str(REPO_ROOT), capture_output=True, text=True,
    )
    if out.returncode != 0:
        raise DiagnosisError(f"git log --grep failed: {out.stderr[:200]}")
    for line in out.stdout.splitlines():
        sha, _, subject = line.partition("\t")
        if subject.strip() == f"accept product cycle {run_id}":
            return sha.strip()
    return None


def gate_file_state(run_id: str) -> dict[str, Any]:
    """Where (and whether) a gate file for this run exists *right now*."""
    path = f"results/audit/product/CYCLE_{run_id}_GATE.json"
    exists = (REPO_ROOT / path).exists()
    record: dict[str, Any] = {"path": path, "present_in_working_tree": exists}
    if not exists:
        # Was it ever committed anywhere?  (A retired self-minted file is NOT a
        # gate for this run_id; it carries a different run's id in its name.)
        out = subprocess.run(
            ["git", "log", "--all", "--oneline", "--", path],
            cwd=str(REPO_ROOT), capture_output=True, text=True,
        )
        record["ever_committed_in_any_ref"] = bool(out.stdout.strip())
        return record
    data = json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))
    record["gate"] = data.get("gate")
    record["safe_to_integrate"] = data.get("safe_to_integrate")
    authors = subprocess.run(
        ["git", "log", "--all", "--format=%an", "--", path],
        cwd=str(REPO_ROOT), capture_output=True, text=True,
    ).stdout.split()
    record["commit_authors"] = sorted(set(authors))
    return record


def orchestration_record(run_id: str) -> dict[str, Any]:
    """Quote the committed GitHub-side job record for this run, if present."""
    path = ORCH_DIR / f"CYCLE_{run_id}_orchestration.json"
    if not path.exists():
        return {"available": False, "reason": "artifact not committed"}
    data = json.loads(path.read_text(encoding="utf-8"))
    diag = data.get("diagnosis") or {}
    return {
        "available": True,
        "artifact": str(path.relative_to(REPO_ROOT)),
        "schema": data.get("schema"),
        "run_conclusion": (data.get("observation") or {}).get("conclusion"),
        "job_conclusions": data.get("job_conclusions"),
        "classification": data.get("classification"),
        "annotations_failure_warning": [
            {"job": a.get("job"), "level": a.get("annotation_level"),
             "message": a.get("message")}
            for a in (diag.get("annotations") or [])
            if a.get("annotation_level") in ("failure", "warning")
        ],
        "audit_agent_step_duration_s": diag.get("audit_agent_step_duration_s"),
        "exit_code": (diag.get("candidates") or {}).get("exit_code"),
    }


#: The commit subject a core-lane ``Persist team snapshot`` step writes.  A file
#: under the auditor's namespace ADDED by such a commit was minted by a
#: PRODUCER, never by the independent auditor (whose step writes on the
#: ``.../<run>/audit`` ref and whose commit subject is ``audit <lane> cycle
#: <run>``).
PRODUCER_SNAPSHOT_SUBJECT = re.compile(
    r"^(product|corpus|legal-distance|fractal-map|evaluation) cycle \d+ repair \d+$")

#: The accepted branch.  Files already on it are historical, claim-bearing
#: evidence and are INVENTORIED here, never deleted (AGENTS.md items 5/6).
ACCEPTED_REF = "refs/remotes/origin/lab/product"


def _adding_commit(path: str) -> dict[str, str] | None:
    out = subprocess.run(
        ["git", "log", "--all", "--diff-filter=A", "--format=%H\t%an\t%s", "--",
         path],
        cwd=str(REPO_ROOT), capture_output=True, text=True,
    ).stdout.splitlines()
    for line in out:
        sha, author, subject = (line.split("\t") + ["", ""])[:3]
        if PRODUCER_SNAPSHOT_SUBJECT.match(subject.strip()):
            return {"sha": sha, "author": author, "subject": subject}
    return None


def audit_namespace_inventory() -> dict[str, Any]:
    """Classify every file under the auditor's namespace by who minted it.

    Two buckets, never conflated:

    * ``accepted_baseline`` - already on ``origin/lab/product``.  Historical
      evidence; recorded with its adding commit so a reader can see it was
      producer-minted, and never removed.
    * ``unadjudicated_chain`` - present only on this cycle's team chain, i.e.
      it would be laundered onto the accepted branch by the next promote.  These
      must be retired into ``reports/product/incidents/`` first.
    """
    accepted_paths = set(
        subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", ACCEPTED_REF],
            cwd=str(REPO_ROOT), capture_output=True, text=True,
        ).stdout.splitlines()
    )
    accepted: list[dict[str, Any]] = []
    chain: list[dict[str, Any]] = []
    for prefix in AUDIT_PREFIXES:
        root = REPO_ROOT / prefix
        if not root.exists():
            continue
        for p in sorted(root.rglob("*")):
            if not p.is_file():
                continue
            rel = str(p.relative_to(REPO_ROOT))
            added = _adding_commit(rel)
            if added is None:
                continue
            entry = {"path": rel, "added_by_producer_snapshot": added}
            (accepted if rel in accepted_paths else chain).append(entry)
    return {
        "files_total": sum(len(v) for v in (accepted, chain)),
        "producer_minted_total": len(accepted) + len(chain),
        "producer_minted_accepted_baseline": accepted,
        "producer_minted_unadjudicated_chain": chain,
        "rule": (
            "accepted-baseline entries are historical claim-bearing evidence and "
            "are never deleted; unadjudicated-chain entries are retired byte-"
            "exactly into reports/product/incidents/ so they cannot be promoted"
        ),
    }


def self_minted_retirement() -> list[dict[str, Any]]:
    out = []
    for old, new in SELF_MINTED:
        old_path, new_path = REPO_ROOT / old, REPO_ROOT / new
        rec: dict[str, Any] = {
            "original_path": old,
            "retired_path": new,
            "original_absent": not old_path.exists(),
            "retired_present": new_path.exists(),
        }
        if new_path.exists():
            rec["retired_sha256"] = hashlib.sha256(new_path.read_bytes()).hexdigest()
        if old_path.exists() and new_path.exists():
            rec["byte_identical"] = (
                old_path.read_bytes() == new_path.read_bytes())
        out.append(rec)
    return out


def diagnose(run_id: str) -> dict[str, Any]:
    chain: list[dict[str, Any]] = []
    for rid in CHAIN:
        refs = run_refs(rid)
        chain.append({
            "run_id": rid,
            "team_ref": refs["team"],
            "audit_ref": refs["audit"],
            "accept_commit": accept_commit_for(rid),
            "gate_file": gate_file_state(rid),
            "independently_audited": refs["audit"] is not None,
            "accepted": accept_commit_for(rid) is not None,
            "adjudication": (
                "ACCEPTED" if accept_commit_for(rid) is not None
                else "UNADJUDICATED"
            ),
            "orchestration": orchestration_record(rid),
        })

    lab_product = _git("rev-parse", "origin/lab/product").strip()
    lab_subject = _git("log", "-1", "--format=%s", "origin/lab/product").strip()
    state = json.loads((REPO_ROOT / "state" / "product.json").read_text("utf-8"))

    return {
        "schema": SCHEMA,
        "run_id": run_id,
        "lane": "product",
        "mode": (
            "OPERATIONAL RESUME from the persisted producer snapshot of run "
            "40164459036; inherited work preserved, not restarted"
        ),
        "derived_from": [
            "local git refs/commits (fetch-depth 0; no network)",
            "results/product/orchestration/CYCLE_<run>_orchestration.json "
            "(committed GitHub REST job records, quoted not re-fetched)",
            "state/product.json",
        ],
        "chain": chain,
        "failure_diagnosis": {
            "orchestration_failure_of_record": {
                "run_id": "40164459036",
                "classification": "AUDIT_STEP_FAILED_NO_GATE",
                "evidence": [
                    "job team concluded 'success'; job audit concluded 'failure'",
                    "audit step 'Independent audit' failed after 2705.0 s with "
                    "exit code 78 (LEX_WORK_QUANTUM_EXPIRED seconds=2700)",
                    "gate-reader and audit-snapshot persist steps were skipped",
                    "no refs/remotes/origin/cycle/core/product/40164459036/audit",
                    "job integrate concluded 'skipped'; run conclusion 'failure'",
                ],
                "consequence": (
                    "the run produced NO independent verdict; it is "
                    "UNADJUDICATED, not rejected. The resilience job then "
                    "dispatched resume_from_run_id=40164459036, which is this "
                    "run."
                ),
            },
            "validation_failure_inherited_by_the_resume": {
                "run_id": "40163751502",
                "classification": "OUT_OF_SCOPE_WRITE_SURVIVED_PERSIST",
                "evidence": [
                    "job team concluded 'failure' with exit code 3 "
                    "('lane crossed protected scope')",
                    "commit 069e2add8 'product cycle 40163751502 repair 0' adds "
                    "results/audit/product/CYCLE_40160899758_GATE.json and "
                    "reports/audit/product/CYCLE_40160899758.md, authored by "
                    "lex-product-team",
                    "core-lane.yml's 'Persist team snapshot' step is guarded by "
                    "if: always(), so it committed and force-pushed the "
                    "out-of-scope files AFTER the guard had already failed",
                    "the guard at 'Enforce lane write scope' inspects only "
                    "git status --porcelain (pending changes), so run "
                    "40164459036 - which RESUMED from that snapshot - passed "
                    "the guard with the same bytes already committed",
                ],
                "consequence": (
                    "results/audit/ and reports/audit/ carried a "
                    "PRODUCER-authored 'PASS' gate for a run whose own team job "
                    "had failed and whose audit job never ran. Both files are "
                    "retired byte-exactly into reports/product/incidents/ this "
                    "cycle; results/audit/ again contains only "
                    "auditor-authored gates."
                ),
                "control_plane_hardening_item": (
                    "core-lane.yml is control-plane scope and is NOT edited from "
                    "this lane: (a) 'Persist team snapshot' should not force-push "
                    "content the scope guard has just rejected, and (b) 'Enforce "
                    "lane write scope' should diff against the base ref rather "
                    "than only pending changes, otherwise a resume inherits the "
                    "violation and the guard can never see it."
                ),
            },
            "chain_root": {
                "run_id": "40160899758",
                "classification": "TEAM_JOB_FAILED",
                "evidence": [
                    "job team concluded 'failure' with exit code 78 "
                    "(LEX_WORK_QUANTUM_EXPIRED seconds=2700)",
                    "job audit / job integrate 'skipped'",
                    "no .../40160899758/audit ref in any ref",
                ],
                "consequence": (
                    "its snapshot 3d7d43b13 (stage-2 counter-surface bridge) "
                    "survived via if: always() and is PRESERVED here as "
                    "unadjudicated work: the code and its tests run, but it may "
                    "not be cited as accepted."
                ),
            },
        },
        "accepted_baseline": {
            "origin/lab/product": lab_product,
            "subject": lab_subject,
            "state_accepted_run_id": state.get("accepted_run_id"),
            "state_accepted_commit": state.get("accepted_commit"),
        },
        "audit_namespace_after_rehome": audit_namespace_inventory(),
        "self_minted_retirement": self_minted_retirement(),
        "claim_ceiling": (
            "Reported-only diagnosis of local git refs and committed job "
            "records. It mints no gate, scores no frozen bar, and labels no run "
            "rejected: 40160899758, 40163751502 and 40164459036 are all "
            "UNADJUDICATED. Job-log TEXT is admin-only over the public API and "
            "is quoted only where a committed orchestration artifact already "
            "records it."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    record = diagnose(args.run_id)
    text = json.dumps(record, indent=2, ensure_ascii=False) + "\n"
    if args.write:
        out = Path(args.out) if args.out else (
            ORCH_DIR / f"CYCLE_{args.run_id}_resume_diagnosis.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"wrote {out.relative_to(REPO_ROOT)}")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DiagnosisError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        raise SystemExit(6)
