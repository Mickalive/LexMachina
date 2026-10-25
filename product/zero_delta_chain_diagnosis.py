#!/usr/bin/env python3
"""Derive, offline from git refs, which runs of a product resume chain produced
zero durable delta and why the chain is UNADJUDICATED, plus which committed
deltas contain out-of-scope paths.

Why this exists (operational resume of run 40181378979)
-------------------------------------------------------
Runs 40173935166 and 40181378979 both ended with their team snapshot refs
pointing at their PREDECESSOR's commit - zero files added, zero files changed -
and the run concluded failure.  The factory-wide requirements record this class:
rc-67 ``LEX_ZERO_DELTA_REPAIR`` fires when HEAD is unchanged and the working
tree is empty and means "the producer found nothing to do", not "the lane is
broken" (requirement 10); a provider death (rc-78 quantum, auth failure, model
overload) leaves the same observable and is NOT a verdict (requirement 20).
Without GitHub job-log access the two are indistinguishable from refs alone,
so this instrument classifies only what the refs prove and never invents a
mechanism.

What it deliberately does NOT do
--------------------------------
It writes no gate, mints no verdict, labels no run "rejected" (a run without an
audit gate is UNADJUDICATED - a different fact), and never touches the network.

Usage
-----
    python3 product/zero_delta_chain_diagnosis.py --run-id 40182739499 --write
    python3 product/zero_delta_chain_diagnosis.py --run-id 40182739499   # dry
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

SCHEMA = "product-zero-delta-chain-diagnosis/1"

#: The chain this resume diagnoses, oldest first: (run_id, team_snapshot_ref).
CHAIN = [
    ("40168184617", "refs/remotes/origin/cycle/core/product/40168184617/team"),
    ("40170987954", "refs/remotes/origin/cycle/core/product/40170987954/team"),
    ("40173935166", "refs/remotes/origin/cycle/core/product/40173935166/team"),
    ("40176984119", "refs/remotes/origin/cycle/core/product/40176984119/team"),
    ("40181378979", "refs/remotes/origin/cycle/core/product/40181378979/team"),
]

#: Product lane write scope (factory output layout + lane directive).
WRITE_SCOPE_PREFIXES = (
    "product/",
    "tests/product/",
    "results/product/",
    "reports/product/",
    "state/product.json",
)

#: Root files that are legitimately part of the accepted branch's tree.
LEGITIMATE_ROOT_PY = ("test_server.py", "test_server_progressive.py",
                      "sync_174k_artifacts.py")


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(REPO_ROOT),
                          capture_output=True, text=True)


def _rev(ref: str) -> str | None:
    p = _git("rev-parse", "--verify", "--quiet", ref)
    return p.stdout.strip() if p.returncode == 0 else None


def _out_of_scope_paths(commit: str) -> tuple[list[str], list[str]]:
    """(out_of_scope_paths, modified_legitimate_root_files) for one commit."""
    parent = _git("rev-parse", f"{commit}^").stdout.strip()
    if not parent:
        return [], []
    p = _git("diff", "--name-only", "--diff-filter=ACMR", parent, commit)
    bad: list[str] = []
    root_modified: list[str] = []
    for path in p.stdout.splitlines():
        path = path.strip()
        if not path:
            continue
        if path.startswith(WRITE_SCOPE_PREFIXES):
            continue
        # Root-level scratch: any root file outside the accepted root inventory.
        if "/" not in path:
            if path in LEGITIMATE_ROOT_PY:
                root_modified.append(path)
            elif not path.startswith("."):
                bad.append(path)
            continue
        if path.startswith(("results/audit/", "reports/audit/")):
            bad.append(path)  # auditor namespace - producers never write there
    return bad, root_modified


def run(run_id: str) -> dict:
    rows = []
    prev_head: str | None = None
    for chain_run, ref in CHAIN:
        head = _rev(ref)
        entry: dict = {"run_id": chain_run, "snapshot_ref": ref,
                       "snapshot_head": head}
        if head is None:
            entry["classification"] = "REF_ABSENT"
        elif prev_head is not None and head == prev_head:
            entry["classification"] = "ZERO_DURABLE_DELTA"
            entry["predecessor_head"] = prev_head
            entry["meaning"] = (
                "the producer committed nothing; from refs alone this is "
                "rc-67 LEX_ZERO_DELTA_REPAIR or a producer death - both are "
                "orchestration outcomes, NOT product defects and NOT verdicts")
        elif prev_head is not None and head != prev_head:
            entry["classification"] = "COMMITTED_DELTA"
            entry["predecessor_head"] = prev_head
            entry["delta_files"] = int(_git("diff", "--name-only",
                                            prev_head, head).stdout.count("\n"))
            bad, root_mod = _out_of_scope_paths(head)
            entry["out_of_scope_paths"] = bad
            entry["modified_legitimate_root_files"] = root_mod
        else:
            entry["classification"] = "CHAIN_ORIGIN"
        rows.append(entry)
        if head:
            prev_head = head

    n_zero = sum(1 for r in rows if r["classification"] == "ZERO_DURABLE_DELTA")
    n_scope = sum(len(r.get("out_of_scope_paths") or []) for r in rows)
    n_root = sum(len(r.get("modified_legitimate_root_files") or []) for r in rows)
    return {
        "schema": SCHEMA,
        "run_id": run_id,
        "direction_version": 68,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "chain": rows,
        "totals": {"runs": len(rows), "zero_delta_runs": n_zero,
                   "out_of_scope_paths_committed": n_scope,
                   "legitimate_root_files_modified": n_root},
        "adjudication": (
            "None of the chain runs carries an independent audit gate on this "
            "ref set; every run here is UNADJUDICATED - not accepted, not "
            "rejected. Acceptance still requires both halves of factory-wide "
            "requirement 4."),
        "repair_note": (
            "Out-of-scope paths committed by 40170987954 were retired "
            "byte-exactly by this resume cycle into "
            "reports/product/incidents/out_of_scope_40170987954_scratch/ "
            "(see its MANIFEST.json); this diagnosis records the pre-repair "
            "state from the committed history."),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    rec = run(args.run_id)
    text = json.dumps(rec, indent=2, ensure_ascii=False) + "\n"
    if args.write:
        out = Path(args.out or (REPO_ROOT / "results/product/orchestration" /
                                f"CYCLE_{args.run_id}_resume_diagnosis.json"))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"wrote {out}")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
