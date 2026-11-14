"""Publish a bounded manifest of the unaccepted delta an auditor must review.

Why this exists
---------------
An operational resume carries a tree that no independent gate has adjudicated.
The auditor's own work quantum is finite (the lane has repeatedly died at
``LEX_WORK_QUANTUM_EXPIRED seconds=2700``), so handing it a prose summary of a
300+ file diff is wasteful: it spends its budget rediscovering which paths are
product code, which are generated evidence and which are historical reports.

This instrument does *not* adjudicate anything. It reads the git diff between
the accepted head and the snapshot head and emits a deterministic, reviewable
inventory: counts by top-level directory and by change kind, the product-code
paths (the only paths a human would read line by line), the tests added or
changed, and the generated results/report/state paths that are evidence rather
than code. The frozen predicates and the accepted pointer are never touched.

Usage
-----
    python3 product/unaccepted_delta_manifest.py \\
        --base 7be4480e --head 5de296f8 \\
        --out results/product/audit_readiness/CYCLE_43572985556_unaccepted_delta.json \\
        --check
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "product-unaccepted-delta-manifest/1"
CLAIM_CEILING = (
    "INVENTORY ONLY: this manifest enumerates the unaccepted git delta between "
    "the accepted head and the snapshot head. It makes no correctness, legal, "
    "frozen-bar, serve or acceptance claim; the independent auditor remains the "
    "only source of a gate."
)


def _git(*args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True,
                          text=True, check=True)
    return proc.stdout


def _rev(ref: str) -> str:
    return _git("rev-parse", "--verify", f"{ref}^{{commit}}").strip()


def _name_status(base: str, head: str) -> list[dict[str, str]]:
    """Return ``[{"status","path"}]`` for the base..head diff.

    ``--no-renames`` keeps the inventory stable: a rename is one add plus one
    delete, never a path the auditor has to resolve across two commits.
    """
    out = _git("diff", "--no-renames", "--name-status", f"{base}..{head}")
    rows: list[dict[str, str]] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        status, path = line.split("\t", 1)
        rows.append({"status": status[0], "path": path})
    return rows


def _top(path: str) -> str:
    return path.split("/", 1)[0] if "/" in path else "(root)"


def build_manifest(base: str, head: str) -> dict[str, Any]:
    base_commit = _rev(base)
    head_commit = _rev(head)
    merge_base = _git("merge-base", base_commit, head_commit).strip() or None
    rows = _name_status(base_commit, head_commit)
    by_top = Counter(_top(r["path"]) for r in rows)
    by_status = Counter(r["status"] for r in rows)
    product = [r for r in rows if r["path"].startswith("product/")]
    tests = [r for r in product if r["path"].startswith("product/tests/")]
    code = [r for r in product if not r["path"].startswith("product/tests/")]
    reports = [r for r in rows if r["path"].startswith("reports/")]
    state = [r for r in rows if r["path"].startswith("state/")]
    results = [r for r in rows if r["path"].startswith("results/")]
    return {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "base_ref": base,
        "base_commit": base_commit,
        "head_ref": head,
        "head_commit": head_commit,
        "merge_base": merge_base,
        "changed_files": len(rows),
        "by_status": {k: by_status[k] for k in sorted(by_status)},
        "by_top_level": {k: by_top[k] for k in sorted(by_top)},
        "deleted_paths": [r["path"] for r in rows if r["status"] == "D"],
        "product_code_paths": sorted(code, key=lambda r: r["path"]),
        "test_paths": sorted(tests, key=lambda r: r["path"]),
        "report_paths": sorted((r["path"] for r in reports)),
        "state_paths": sorted((r["path"] for r in state)),
        "generated_results": {
            "n_paths": len(results),
            "note": (
                "generated evidence under results/; the auditor verifies it "
                "against the committed instruments listed in the dossier, it is "
                "not read as prose"
            ),
        },
        "claim_ceiling": CLAIM_CEILING,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", required=True,
                    help="accepted ref/commit (e.g. origin/lab/product)")
    ap.add_argument("--head", required=True,
                    help="snapshot ref/commit under audit")
    ap.add_argument("--out", default=None)
    ap.add_argument("--check", action="store_true",
                    help="fail closed if the diff is empty or the merge base "
                         "is not the base commit")
    args = ap.parse_args(argv)

    manifest = build_manifest(args.base, args.head)
    if args.out:
        out = Path(args.out)
        if not out.is_absolute():
            out = ROOT / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8")
        print(f"manifest -> {out}")

    problems = []
    if manifest["changed_files"] == 0:
        problems.append("empty_delta")
    if manifest["merge_base"] != manifest["base_commit"]:
        problems.append("base_not_merge_base")
    if not manifest["product_code_paths"] and not manifest["test_paths"]:
        problems.append("no_product_paths")
    summary = {
        "changed_files": manifest["changed_files"],
        "by_status": manifest["by_status"],
        "by_top_level": manifest["by_top_level"],
        "product_paths": len(manifest["product_code_paths"]),
        "test_paths": len(manifest["test_paths"]),
        "problems": problems,
    }
    print(json.dumps(summary, indent=2))
    if args.check and problems:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
