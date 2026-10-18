#!/usr/bin/env python3
"""Orchestration/validation probe: what actually happened to a dispatched lane run.

WHY THIS EXISTS
---------------
Direction v57 (item 2) names the lane's remaining work as "consume the Product
handoff", and audit ``CYCLE_39122016679`` F3 forbids pausing before that
consumption.  Every time this lane has been unable to produce a discriminating
measurement it has not been because the product moved - it has been because the
orchestration killed the run.  Run ``39167798884`` (repair round 1 of
``39164900837``) died with zero durable delta, the team job reported non-success,
the audit job was therefore SKIPPED, and no gate file was written.  Run
``39173551486`` - the producer snapshot this cycle resumes from - presents exactly
the same shape.

A SKIPPED audit job reports ``status=completed`` and is indistinguishable from a
PASS if nobody looks, so the lane needs an instrument, not an anecdote.

WHAT THIS MEASURES (all of it from git, never from a log line in prose)
-----------------------------------------------------------------------
1.  the tip of the dispatched snapshot branch;
2.  whether any commit reachable from that tip carries the run id;
3.  whether any TRACKED FILE in that tip's tree carries the run id;
4.  whether an audit gate file for that run exists in the tree;
5.  the previous tip of the same lineage, so "zero delta" is a *comparison* and
    not an assertion;
6.  the derived class, from the truth table in :func:`classify`.

It measures ORCHESTRATION, never the product.  A run that delivers nothing
teaches the factory nothing about retrieval, labels, geometry or the query map,
and this probe refuses to let that silence be recorded as a result.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

SCHEMA = "lex-evaluation-orchestration-probe/1"
GATE_REL = "results/audit/evaluation/CYCLE_{run_id}_GATE.json"

#: The truth table.  Deliberately data, not prose: an auditor can check the
#: classification against four booleans without reading this module's logic.
CLASSES = {
    "TEAM_JOB_ZERO_COMMIT__AUDIT_SKIPPED__NO_GATE_FILE":
        "the snapshot tip is unchanged from the lineage's previous tip and no "
        "tracked file references the run id: the producer delivered nothing, so "
        "needs.team was not success, the audit job was skipped and no gate "
        "exists. A skipped audit job reports status=completed; this class exists "
        "so that is never read as an audit that ran.",
    "TEAM_JOB_DELIVERED__AUDIT_GATE_PRESENT":
        "tracked files reference the run id and its gate file is in the tree: the "
        "run is deliverable and was audited.",
    "TEAM_JOB_DELIVERED__AUDIT_GATE_ABSENT":
        "tracked files reference the run id but no gate file exists: the run "
        "delivered and the audit did not produce a verdict for it.",
    "TEAM_JOB_DELIVERED__RUN_ID_ONLY_IN_COMMIT_MESSAGE":
        "a commit carries the run id but no tracked file does: the persist step "
        "recorded the cycle while the tree itself was unchanged.",
}


def _git(*args: str) -> tuple[int, str]:
    proc = subprocess.run(["git", "-C", str(_REPO_ROOT), *args],
                          capture_output=True, text=True)
    return proc.returncode, proc.stdout.strip()


def _rev(ref: str) -> str | None:
    rc, out = _git("rev-parse", "--verify", "--quiet", ref)
    return out if rc == 0 and out else None


def _tree_sha(ref: str) -> str | None:
    rc, out = _git("rev-parse", "--verify", "--quiet", f"{ref}^{{tree}}")
    return out if rc == 0 and out else None


def _subject(ref: str) -> dict | None:
    rc, out = _git("log", "-1", "--format=%H%x09%h%x09%aI%x09%an%x09%s", ref)
    if rc != 0 or not out:
        return None
    full, short, when, author, subject = out.split("\t", 4)
    return {"commit": full, "short": short, "committed_at": when,
            "author": author, "subject": subject}


def _commits_naming(run_id: str) -> list[dict]:
    rc, out = _git("log", "--all", f"--grep={run_id}", "--format=%H%x09%h%x09%aI%x09%s")
    if rc != 0 or not out:
        return []
    rows = []
    for line in out.splitlines():
        full, short, when, subject = line.split("\t", 3)
        rows.append({"commit": full, "short": short, "committed_at": when,
                     "subject": subject})
    return rows


def _tracked_files_naming(run_id: str, ref: str) -> list[str]:
    proc = subprocess.run(["git", "-C", str(_REPO_ROOT), "grep", "-l",
                           run_id, ref, "--"],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        return []
    hits = []
    for line in proc.stdout.splitlines():
        # `git grep <pat> <ref> --` prints "<ref>:<path>"
        _, _, path = line.partition(":")
        hits.append(path)
    return sorted(hits)


def _gate_present(run_id: str, ref: str) -> bool:
    rc, _ = _git("cat-file", "-e", f"{ref}:{GATE_REL.format(run_id=run_id)}")
    return rc == 0


def classify(*, tip_moved: bool, files_name_run: bool,
             commit_names_run: bool, gate_present: bool) -> str:
    if not tip_moved:
        if commit_names_run:
            return "TEAM_JOB_DELIVERED__RUN_ID_ONLY_IN_COMMIT_MESSAGE"
        return "TEAM_JOB_ZERO_COMMIT__AUDIT_SKIPPED__NO_GATE_FILE"
    if commit_names_run and not files_name_run:
        # The realistic non-delta shape: the persist step added a cycle commit
        # whose tree differs only in files that do not mention the run id. Cycle
        # 39173770080 measured exactly this (five pytest_local artifacts churned
        # by the lane's own suite), so it is a class, not a hypothetical.
        return "TEAM_JOB_DELIVERED__RUN_ID_ONLY_IN_COMMIT_MESSAGE"
    if not gate_present:
        return "TEAM_JOB_DELIVERED__AUDIT_GATE_ABSENT"
    return "TEAM_JOB_DELIVERED__AUDIT_GATE_PRESENT"


def previous_tip(tip: str, run_id: str) -> str | None:
    """The tip the dispatched branch was seeded from.

    Derived, not remembered: the dispatched branch's own history tells us.  A
    zero-delta persist step force-pushes the SAME commit, so the lineage tip is
    whatever this branch pointed at before the dispatch.  The nearest commit
    that does not carry this run id is that seed; if the run id appears nowhere,
    the seed is the branch tip's own first-parent walk to the newest commit that
    predates the dispatch.
    """
    rc, out = _git("rev-list", "--first-parent", tip)
    if rc != 0:
        return None
    commits = [c for c in out.splitlines() if c]
    for commit in commits:
        rc, subject = _git("log", "-1", "--format=%s", commit)
        if rc == 0 and run_id not in subject:
            return commit
    return None


def probe(run_id: str, branch: str) -> dict:
    tip = _rev(branch)
    if tip is None:
        return {"schema": SCHEMA, "run_id": run_id, "branch": branch,
                "verdict": "BRANCH_ABSENT",
                "detail": f"no such ref: {branch}"}
    tree = _tree_sha(tip)
    seed = previous_tip(tip, run_id)
    seed_tree = _tree_sha(seed) if seed else None
    tip_moved = bool(seed) and seed_tree != tree
    files = _tracked_files_naming(run_id, tip)
    commits = _commits_naming(run_id)
    gate = _gate_present(run_id, tip)
    klass = classify(tip_moved=tip_moved, files_name_run=bool(files),
                     commit_names_run=bool(commits), gate_present=gate)
    return {
        "schema": SCHEMA,
        "run_id": run_id,
        "branch": branch,
        "branch_tip": tip,
        "branch_tree_sha256_of_git_tree": tree,
        "lineage_seed_commit": seed,
        "lineage_seed_tree": seed_tree,
        "tip_moved_versus_seed": tip_moved,
        "tip_subject": _subject(tip),
        "commits_naming_run_id": commits,
        "n_commits_naming_run_id": len(commits),
        "tracked_files_naming_run_id": files,
        "n_tracked_files_naming_run_id": len(files),
        "audit_gate_path": GATE_REL.format(run_id=run_id),
        "audit_gate_present": gate,
        "derived_class": klass,
        "class_glossary": CLASSES,
        "durable_delta": {
            "files_changed_versus_seed": (
                _git("diff", "--name-only", f"{seed}", f"{tip}")[1].splitlines()
                if seed else []),
        },
        "claim_ceiling": (
            "Orchestration only. A zero-delta run says nothing about retrieval, "
            "counter-authority recall, label soundness, geometry soundness or "
            "jurist usefulness, and is never recorded as a product or "
            "instrument result."),
        "measured_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def self_test() -> dict:
    """The probe against its own truth table.

    A diagnostic that cannot be shown to discriminate is an anecdote.  Every row
    is a synthetic input to :func:`classify`; the expected class is fixed here,
    before the probe is used on a real run.
    """
    cases = [
        {"tip_moved": False, "files_name_run": False, "commit_names_run": False,
         "gate_present": False, "expected": "TEAM_JOB_ZERO_COMMIT__AUDIT_SKIPPED__NO_GATE_FILE"},
        {"tip_moved": True, "files_name_run": True, "commit_names_run": True,
         "gate_present": True, "expected": "TEAM_JOB_DELIVERED__AUDIT_GATE_PRESENT"},
        {"tip_moved": True, "files_name_run": True, "commit_names_run": True,
         "gate_present": False, "expected": "TEAM_JOB_DELIVERED__AUDIT_GATE_ABSENT"},
        {"tip_moved": True, "files_name_run": False, "commit_names_run": True,
         "gate_present": False, "expected": "TEAM_JOB_DELIVERED__RUN_ID_ONLY_IN_COMMIT_MESSAGE"},
    ]
    observed = []
    ok = True
    for case in cases:
        got = classify(tip_moved=case["tip_moved"], files_name_run=case["files_name_run"],
                       commit_names_run=case["commit_names_run"],
                       gate_present=case["gate_present"])
        passed = got == case["expected"]
        ok = ok and passed
        observed.append({**case, "observed": got, "passed": passed})
    return {"schema": "lex-evaluation-orchestration-probe-selftest/1",
            "cases": observed, "all_passed": ok}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--branch", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest and not args.run_id:
        report = self_test()
        print(json.dumps(report, indent=1))
        return 0 if report["all_passed"] else 1
    branch = args.branch or f"refs/heads/cycle/core/evaluation/{args.run_id}/team"
    report = probe(args.run_id, branch)
    report["selftest"] = self_test()
    if args.out:
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print(json.dumps(report, indent=1))
    return 0 if report["derived_class"] != "BRANCH_ABSENT" else 2


if __name__ == "__main__":
    raise SystemExit(main())