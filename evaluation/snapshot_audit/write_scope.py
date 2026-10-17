"""Producer write-scope gate (stdlib only, no network, no Product import).

WHY THIS EXISTS
---------------
Run 38982176936 (core evaluation, dirV50) died at the workflow step
"Enforce lane write scope" (team job 117245339430, step 9, conclusion
failure; audit + integrate skipped; resilience re-dispatched this resume).
The step's only non-zero exit path is `exit 3` after classifying working-tree
entries with the case patterns below.  The producer workspace contained two
audit-of-record paths (`results/audit/evaluation/CYCLE_38982176936_GATE.json`,
`reports/audit/evaluation/CYCLE_38982176936.md`) which are NOT in the allowed
set for a PRODUCER, so the chain never reached an independent audit and the
deliverable was never promoted.

This module makes that step executable INSIDE the lane so the failure is
reproducible and pre-flightable:

    python -m evaluation.snapshot_audit.write_scope --lane evaluation
    python -m evaluation.snapshot_audit.write_scope --lane evaluation \\
        --porcelain-file saved_porcelain.txt
    python -m evaluation.snapshot_audit.write_scope --lane evaluation \\
        --repro-from-git HEAD~1 HEAD

FIDELITY
--------
The classifier is a byte-faithful port of `.github/workflows/core-lane.yml`
step "Enforce lane write scope" (read from origin/main at run time of
record; .github/** is control-plane scope and is NOT edited here):
  * entry path = porcelain line with the first 3 characters stripped
    (bash `${line:3}` over `git status --porcelain -uall` output);
  * allowed: <code>/*, tests/<lane>/*, results/<lane>/*, reports/<lane>/*,
    state/<lane>.json, data/<lane>/*, and the empty path;
  * requirements.txt / pyproject.toml / uv.lock are allowed for the product
    lane only;
  * everything else is BAD.
The only modeled difference from the live step is ordering: the workflow's
"Clean generated junk" step deletes __pycache__ / *.pyc / *.pyo before the
scope step, so THIS module ignores exactly those junk classes (and nothing
else — e.g. .pytest_cache is NOT ignored, because the workflow would not
delete it either).

Exit codes: 0 = scope clean, 1 = scope violation (BAD list printed), 2 =
environment/input error.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "lex-evaluation-write-scope/1"

# core-lane.yml "Clean generated junk" step; modeled as pre-step-9 ordering.
JUNK_SUFFIXES = (".pyc", ".pyo")
JUNK_DIR_PARTS = ("__pycache__",)

_LANE_CODE = {
    "corpus": "corpus",
    "legal-distance": "legal_distance",
    "fractal-map": "fractal_map",
    "evaluation": "evaluation",
    "product": "product",
}
_PRODUCT_ONLY_ALLOWED = ("requirements.txt", "pyproject.toml", "uv.lock")


def is_junk(path: str) -> bool:
    """True for files the workflow's junk-clean step deletes before step 9."""
    parts = Path(path).parts
    if any(p in JUNK_DIR_PARTS for p in parts):
        return True
    return path.endswith(JUNK_SUFFIXES)


def classify_path(path: str, lane: str) -> bool:
    """True iff the workflow's step-9 case statement would allow `path`."""
    if path == "":
        return True
    code = _LANE_CODE[lane]
    allowed = (
        path.startswith(f"{code}/")
        or path.startswith(f"tests/{lane}/")
        or path.startswith(f"results/{lane}/")
        or path.startswith(f"reports/{lane}/")
        or path == f"state/{lane}.json"
        or path.startswith(f"data/{lane}/")
    )
    if allowed:
        return True
    if lane == "product" and path in _PRODUCT_ONLY_ALLOWED:
        return True
    return False


def split_porcelain(line: str) -> str:
    """Bash `${line:3}` on a `git status --porcelain -uall` line."""
    return line[3:].rstrip("\n")


def evaluate_porcelain(lines: list[str], lane: str,
                       drop_junk: bool = True) -> dict:
    """Classify porcelain lines; returns the verdict payload."""
    if lane not in _LANE_CODE:
        raise ValueError(f"unknown lane {lane!r}")
    entries, bad, junk_dropped = [], [], []
    for raw in lines:
        if not raw.strip():
            continue
        path = split_porcelain(raw)
        if drop_junk and is_junk(path):
            junk_dropped.append(path)
            continue
        ok = classify_path(path, lane)
        entries.append({"porcelain": raw.rstrip("\n"), "path": path,
                        "allowed": ok})
        if not ok:
            bad.append(path)
    return {
        "schema": SCHEMA,
        "lane": lane,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "workflow_step": "Enforce lane write scope (.github/workflows/core-lane.yml, control plane, read-only)",
        "model": ("faithful port of the step's case patterns; __pycache__/ *.pyc *.pyo "
                  "modeled as already removed by the preceding 'Clean generated junk' step"),
        "n_entries": len(entries),
        "n_bad": len(bad),
        "bad_paths": bad,
        "junk_dropped": sorted(set(junk_dropped)),
        "verdict": "SCOPE_CLEAN" if not bad else "SCOPE_VIOLATION",
        "scope_clean": not bad,
        "entries": entries,
    }


def live_porcelain(repo_root: Path) -> list[str]:
    proc = subprocess.run(["git", "status", "--porcelain", "-uall"],
                          cwd=str(repo_root), capture_output=True, text=True, check=True)
    return proc.stdout.splitlines()


def reconstruct_snapshot_porcelain(repo_root: Path, base_sha: str,
                                   snapshot_sha: str) -> dict:
    """Reconstruct the untracked entries the scope step saw on a failed run.

    Step 9 runs BEFORE 'Persist team snapshot' (which does `git add -A; git
    commit`), so every path the snapshot commit ADDED was untracked working
    tree state at step 9 and appears in `git status --porcelain -uall` as an
    entry whose path component is the added path.  Reconstruction:
      added = git diff --name-status base..snapshot  (status A/R/C/M)
    Modifications of already-tracked in-scope files are scope-irrelevant
    (they stay inside their allowed prefix) but are still recorded.
    """
    diff = subprocess.run(
        ["git", "diff", "--name-status", f"{base_sha}..{snapshot_sha}"],
        cwd=str(repo_root), capture_output=True, text=True, check=True).stdout
    added, modified = [], []
    for line in diff.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status, path = parts[0], parts[-1]
        if status.startswith("A") or status.startswith("R") or status.startswith("C"):
            added.append(path)
        else:
            modified.append(path)
    lines = [f"?? {p}" for p in added]
    return {"base_sha": base_sha, "snapshot_sha": snapshot_sha,
            "added_paths": added, "modified_paths": modified,
            "porcelain_lines": lines}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--lane", default="evaluation")
    ap.add_argument("--repo-root", default=str(Path.cwd()))
    ap.add_argument("--porcelain-file", default=None,
                    help="classify a saved `git status --porcelain -uall` dump instead of the live tree")
    ap.add_argument("--repro-from-git", nargs=2, metavar=("BASE_SHA", "SNAPSHOT_SHA"),
                    default=None, help="reconstruct a failed run's untracked additions and classify them")
    ap.add_argument("--out", default=None, help="optional JSON output path")
    args = ap.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    try:
        if args.repro_from_git:
            rec = reconstruct_snapshot_porcelain(repo_root, *args.repro_from_git)
            verdict = evaluate_porcelain(rec["porcelain_lines"], args.lane)
            payload = {"schema": SCHEMA, "mode": "repro-from-git",
                       "reconstruction": rec, "verdict": verdict}
        elif args.porcelain_file:
            lines = Path(args.porcelain_file).read_text(encoding="utf-8").splitlines()
            verdict = evaluate_porcelain(lines, args.lane)
            payload = {"schema": SCHEMA, "mode": "porcelain-file",
                       "porcelain_file": args.porcelain_file, "verdict": verdict}
        else:
            verdict = evaluate_porcelain(live_porcelain(repo_root), args.lane)
            payload = {"schema": SCHEMA, "mode": "live", "repo_root": str(repo_root),
                       "verdict": verdict}
    except ValueError as exc:
        print(f"write_scope: {exc}", file=sys.stderr)
        return 2

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                                  encoding="utf-8")

    v = payload["verdict"]
    print(f"write scope [{args.lane}]: {v['verdict']} "
          f"({v['n_entries']} entries, {v['n_bad']} bad, "
          f"{len(v['junk_dropped'])} junk dropped)")
    for p in v["bad_paths"]:
        print(f"  BAD {p}")
    if args.out:
        print(f"record: {args.out}")
    return 0 if v["scope_clean"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
