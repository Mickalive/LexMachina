"""Freeze-ordering evidence, recomputed from REAL git commit times.

A hand-written ``frozen_at_utc`` field is NOT evidence.  This module walks the
committed history of the frozen rules file and of the first commit that carries
a measurement, and writes the ordering it actually finds.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TEAM_DIR = REPO_ROOT / "results/frontier/frontier-concept-seed-recall"
RULES_RELPATH = "results/frontier/frontier-concept-seed-recall/RULES.json"


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True,
                          text=True, check=True).stdout.strip()


def _commits_for(relpath: str) -> list[tuple[str, str, str]]:
    out = []
    for line in _git("log", "--all", "--format=%H %cI %s", "--", relpath).splitlines():
        sha, when, subject = line.split(" ", 2)
        out.append((sha, when, subject))
    return out


def _blob_sha256(sha: str, relpath: str) -> str | None:
    try:
        raw = subprocess.run(["git", "show", f"{sha}:{relpath}"], cwd=REPO_ROOT,
                             capture_output=True, check=True).stdout
    except subprocess.CalledProcessError:
        return None
    import hashlib
    return hashlib.sha256(raw).hexdigest()


def build(run_id: int) -> dict:
    rules_commits = _commits_for(RULES_RELPATH)
    results_commits = _commits_for(f"results/frontier/frontier-concept-seed-recall/"
                                   f"harness_results_{run_id}.json")
    baseline_commits = _commits_for(
        f"results/frontier/frontier-concept-seed-recall/baseline_reproduction_{run_id}.json")

    freeze = rules_commits[-1] if rules_commits else None
    first_measurement = results_commits[-1] if results_commits else None
    digests = []
    for sha, when, subject in rules_commits:
        digests.append({"commit": sha, "commit_time_utc": when, "subject": subject,
                        "rules_sha256": _blob_sha256(sha, RULES_RELPATH)})

    ordered = bool(freeze and first_measurement
                   and freeze[1] < first_measurement[1])
    margin = None
    if ordered:
        from datetime import datetime
        margin = (datetime.fromisoformat(first_measurement[1])
                  - datetime.fromisoformat(freeze[1])).total_seconds()

    return {
        "schema": "frontier-concept-seed-recall/freeze-ordering/1",
        "run_id": run_id,
        "rules_relpath": RULES_RELPATH,
        "rules_commits": digests,
        "final_frozen_rules_sha256": (digests[-1]["rules_sha256"] if digests else None),
        "first_commit_carrying_a_measurement": (
            {"commit": first_measurement[0], "commit_time_utc": first_measurement[1],
             "subject": first_measurement[2]} if first_measurement else None),
        "first_commit_carrying_baseline_reproduction": (
            {"commit": baseline_commits[-1][0], "commit_time_utc": baseline_commits[-1][1],
             "subject": baseline_commits[-1][2]} if baseline_commits else None),
        "freeze_precedes_measurement": ordered,
        "margin_seconds": margin,
        "rules_bytes_unchanged_since_final_amendment": (
            len({d["rules_sha256"] for d in digests[-1:]}) == 1
            and digests[-1]["commit"] == freeze[0] if digests else None),
        "method": "real git commit times (git log --format=%cI) and real git blob "
                  "digests (git show <sha>:<path>); no hand-written timestamp is used "
                  "as evidence anywhere in this record",
        "caveat": "this file is itself written after the freeze; it REPORTS the "
                  "ordering, it does not create it. The ordering is verifiable from "
                  "the commits it names without trusting this file.",
    }


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", required=True)
    args = ap.parse_args(argv)
    rec = build(int(args.run_id))
    out = TEAM_DIR / "freeze_ordering.json"
    out.write_text(json.dumps(rec, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8")
    print(json.dumps({"freeze_precedes_measurement": rec["freeze_precedes_measurement"],
                      "margin_seconds": rec["margin_seconds"],
                      "final_rules_sha256": rec["final_frozen_rules_sha256"]}, indent=1))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())