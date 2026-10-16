"""Prove the freeze ordering from git commit times (charter acceptance test 1).

The charter forbids relying on a hand-written ``frozen_at_utc`` field: the proof
must come from commit times.  This module compares

  * the commit that introduced RULES.json (the freeze), and
  * the commit that introduced the scored results,

and writes a FREEZE_PROOF.json next to the results.  It also re-hashes every
frozen input against the accepted mount, so the proof covers both halves of
"the rubric was frozen before any label was scored on these bytes".

    python3 -m frontier_counter_label_integrity.verify_freeze \\
        --repo-root . --out results/frontier/frontier-counter-label-integrity
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess

FREEZE_RELPATH = "results/frontier/frontier-counter-label-integrity/RULES.json"
RESULT_RELPATHS = (
    "results/frontier/frontier-counter-label-integrity/REPORT.json",
    "results/frontier/frontier-counter-label-integrity/NON_VACUITY.json",
)


def _git(repo_root: str, *args: str, binary: bool = False):
    proc = subprocess.run(["git", "-C", repo_root, *args], check=True, capture_output=True)
    return proc.stdout if binary else proc.stdout.decode("utf-8")


def _first_commit_touching(repo_root: str, relpath: str) -> dict | None:
    """Oldest commit that introduced the file (root commit of the path)."""
    out = _git(repo_root, "log", "--reverse", "--format=%H\t%cI\t%s", "--", relpath).strip()
    if not out:
        return None
    sha, iso, subject = out.splitlines()[0].split("\t", 2)
    return {"commit": sha, "committed_at": iso, "subject": subject, "path": relpath}


def _blob_sha256(repo_root: str, relpath: str, commit: str) -> str:
    blob = _git(repo_root, "cat-file", "blob", f"{commit}:{relpath}", binary=True)
    return hashlib.sha256(blob).hexdigest()


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_proof(repo_root: str, rules_path: str | None = None) -> dict:
    rules_path = rules_path or os.path.join(repo_root, FREEZE_RELPATH)
    with open(rules_path, "rb") as fh:
        rules = json.loads(fh.read().decode("utf-8"))

    freeze = _first_commit_touching(repo_root, FREEZE_RELPATH)
    scored = [c for c in (_first_commit_touching(repo_root, p) for p in RESULT_RELPATHS) if c]
    with open(rules_path, "rb") as fh:
        working_sha = hashlib.sha256(fh.read()).hexdigest()

    inputs = []
    for entry in rules["inputs"]:
        path = entry["product_mount_path"]
        observed = _sha256_file(path) if os.path.exists(path) else None
        inputs.append({
            "relpath_under_results_product": entry["relpath_under_results_product"],
            "population": entry["population"],
            "frozen_sha256": entry["sha256"],
            "observed_sha256": observed,
            "matches": observed == entry["sha256"],
            "content_sha256_from_admissibility": entry.get("content_sha256"),
        })

    freeze_at = freeze["committed_at"] if freeze else None
    results_at = max((c["committed_at"] for c in scored), default=None)
    ordered = bool(freeze_at and results_at and freeze_at <= results_at)

    return {
        "schema": "frontier-counter-label-integrity/freeze-proof/1",
        "team_id": rules["team_id"],
        "charter_version": rules["charter_version"],
        "freeze_commit": freeze,
        "results_commits": scored,
        "freeze_committed_at": freeze_at,
        "results_committed_at": results_at,
        "freeze_precedes_results": ordered,
        "rules_sha256_working_tree": working_sha,
        "rules_sha256_at_freeze_commit": _blob_sha256(repo_root, FREEZE_RELPATH, freeze["commit"]) if freeze else None,
        "rules_unchanged_since_freeze": (
            bool(freeze) and _blob_sha256(repo_root, FREEZE_RELPATH, freeze["commit"]) == working_sha
        ),
        "inputs": inputs,
        "all_inputs_match_frozen_sha256": all(i["matches"] for i in inputs),
        "ordering_evidence": "git commit times only; no frozen_at_utc field is written anywhere",
        "verdict_evidence_note": (
            "RULES.json is committed before any report that scores a label. Any later edit to "
            "RULES.json changes rules_unchanged_since_freeze to false and invalidates the run."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="verify-freeze")
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--rules", default=None)
    ap.add_argument("--out", default="results/frontier/frontier-counter-label-integrity")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    repo_root = os.path.abspath(args.repo_root)
    proof = build_proof(repo_root, args.rules)
    os.makedirs(os.path.abspath(args.out), exist_ok=True)
    target = os.path.join(args.out, "FREEZE_PROOF.json")
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(proof, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    if not args.quiet:
        print(f"freeze_precedes_results {proof['freeze_precedes_results']}")
        print(f"rules_unchanged_since_freeze {proof['rules_unchanged_since_freeze']}")
        print(f"all_inputs_match_frozen_sha256 {proof['all_inputs_match_frozen_sha256']}")
        print(f"wrote {target}")
    ok = proof["freeze_precedes_results"] and proof["rules_unchanged_since_freeze"] \
        and proof["all_inputs_match_frozen_sha256"]
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())