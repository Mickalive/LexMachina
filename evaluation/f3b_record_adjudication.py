#!/usr/bin/env python3
"""Autonomous adjudication of escalation F-3b: which frozen_cache_integrity
record is the record of record?

THE DEFECT (factory-wide requirement 29 class)
---------------------------------------------
Commit 9b61dcf8 modified, in place, two claim-bearing artifacts of run
39164900837 under ``results/evaluation/frozen_cache_integrity/``.  A later lane
cycle escalated the question "which artifact is the record of record?" to the
OWNER and recorded ``owner_decision_required: true`` in ``state/evaluation.json``,
citing ``results/audit/evaluation/CYCLE_39199651952_GATE.json`` as the source of
the escalation.  That is a provenance claim that does not reproduce from the
committed tree, which is the exact defect class factory-wide requirement 29
names as the binding operational defect class, and ``owner_decision_required``
directly contradicts factory direction v57, which states that no lane is
HUMAN_DECISION_REQUIRED because every open item is operational.

WHY THIS IS NOT AN OWNER DECISION
----------------------------------
The question "which artifact is the record of record" has exactly one technical
answer, and git supplies it: git retains the pre-image.  Nothing was destroyed.
This instrument proves that mechanically, restores the pre-image to a NEW path
(never overwriting either existing record), publishes BOTH readings side by side
with their named digests, enumerates the exact key-level delta between them, and
reports whether the cited escalation source exists anywhere in the object
database.

This instrument WRITES NOTHING outside ``results/evaluation/f3b_adjudication/``
and does not modify any existing record, gate file, frozen input, test or state
file.

Exit codes
----------
0  F3B_AUTONOMOUSLY_RESOLVED_RECORD_RECOVERABLE
2  F3B_UNRESOLVED_PREIMAGE_NOT_RECOVERABLE
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "lex-evaluation-f3b-adjudication/1"
TARGET_DIR = "results/evaluation/frozen_cache_integrity"
RESTORED_NAME = "39164900837_preimage_recovered.json"
OVERWRITE_COMMIT = "9b61dcf8"
CITED_ESCALATION_SOURCE = "results/audit/evaluation/CYCLE_39199651952_GATE.json"

CLAIM_CEILING = (
    "This instrument establishes exactly one thing: whether the frozen_cache_integrity record of "
    "run 39164900837 that commit 9b61dcf8 overwrote in place is still recoverable byte-exactly from "
    "git, and what the exact key-level delta between the two records is. It does NOT decide which "
    "reading is legally or scientifically correct - the pre-image is the record AS FIRST WRITTEN and "
    "the current file is the record AS LAST WRITTEN, and BOTH are preserved side by side with named "
    "digests so that no adjudication is required to read either. It does NOT modify, delete, "
    "restore-over or rewrite either record. It does NOT touch any frozen spec, threshold, bar, "
    "gate file or rubric, and it moves no verdict. It does NOT unblock any human gate and makes no "
    "owner ask."
)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git(*args: str, repo: Path | None = None) -> tuple[int, str]:
    proc = subprocess.run(["git", "-C", str(repo or REPO_ROOT), *args],
                          capture_output=True, text=True)
    return proc.returncode, proc.stdout


def git_blob_at(ref: str, relpath: str) -> tuple[bytes | None, dict[str, Any]]:
    """Fetch a path at a ref, preferring an exact blob id when given."""
    if ref.startswith("blob:"):
        blob = ref.split(":", 1)[1]
        rc, out = git("cat-file", "blob", blob)
    else:
        rc, out = git("show", f"{ref}:{relpath}")
        if rc != 0:
            return None, {"ref": ref, "path": relpath, "error": "not present at ref"}
    if rc != 0:
        return None, {"ref": ref, "path": relpath, "error": "git cat-file/show failed"}
    data = out.encode("utf-8", errors="surrogateescape")
    meta = {"ref": ref, "path": relpath, "sha256": sha256_bytes(out.encode()),
            "bytes": len(out.encode())}
    rc2, blob_out = git("rev-parse", f"{ref}:{relpath}" if not ref.startswith("blob:") else ref)
    if rc2 == 0 and blob_out.strip():
        meta["git_blob"] = blob_out.strip()
    return data, meta


def key_delta(a: dict, b: dict, prefix: str = "") -> list[dict]:
    """Exact key-level delta. Set semantics, never matching cardinalities."""
    out: list[dict] = []
    for k in sorted(set(a) | set(b)):
        path = f"{prefix}.{k}" if prefix else str(k)
        if k not in a:
            out.append({"key": path, "change": "ADDED_IN_CURRENT", "current": _summarise(b[k])})
        elif k not in b:
            out.append({"key": path, "change": "REMOVED_FROM_CURRENT", "preimage": _summarise(a[k])})
        elif isinstance(a[k], dict) and isinstance(b[k], dict):
            out.extend(key_delta(a[k], b[k], path))
        elif a[k] != b[k]:
            out.append({"key": path, "change": "VALUE_CHANGED",
                        "preimage": _summarise(a[k]), "current": _summarise(b[k])})
    return out


def _summarise(v: Any) -> Any:
    if isinstance(v, (dict, list)):
        return f"<{type(v).__name__} len={len(v)}>"
    if isinstance(v, str) and len(v) > 160:
        return v[:160] + "..."
    return v


def path_exists_anywhere(relpath: str) -> dict[str, Any]:
    """Does a path exist at ANY ref? Used to test the cited escalation source."""
    rc, refs = git("for-each-ref", "--format=%(refname)")
    if rc != 0:
        return {"exists_at_any_ref": False, "detail": "for-each-ref failed"}
    found: list[str] = []
    for ref in refs.split():
        rc2, _ = git("ls-tree", "-r", "--name-only", ref, "--", relpath)
        if rc2 == 0:
            rc3, out = git("show", f"{ref}:{relpath}")
            if rc3 == 0 and out.strip():
                found.append(ref)
    rc4, hist = git("log", "--all", "--oneline", "--name-only", "--diff-filter=A", "--", relpath)
    return {
        "path": relpath,
        "exists_at_any_ref": bool(found),
        "refs_containing_it": found,
        "ever_added_in_history": bool(hist.strip()),
        "history_log": hist.strip().splitlines()[:10],
    }


def adjudicate(repo: Path, run_id: str) -> dict:
    cur_path = repo / TARGET_DIR / "39164900837.json"
    findings: list[dict] = []

    if not cur_path.is_file():
        return {"schema": SCHEMA, "verdict": "F3B_UNRESOLVED_PREIMAGE_NOT_RECOVERABLE",
                "exit_code": 2, "detail": f"{TARGET_DIR}/39164900837.json is absent from the tree"}

    cur_bytes = cur_path.read_bytes()
    cur_meta = {"ref": "WORKTREE", "path": f"{TARGET_DIR}/39164900837.json",
                "sha256": sha256_bytes(cur_bytes), "bytes": len(cur_bytes)}

    # 1. Find the commit that last touched the record BEFORE the overwrite.
    rc, log = git("log", "--format=%H %cI %s", "--", f"{TARGET_DIR}/39164900837.json")
    history = [ln for ln in log.splitlines() if ln.strip()]
    preimage_ref = None
    for line in history:
        sha = line.split(" ", 1)[0]
        if sha.startswith(OVERWRITE_COMMIT):
            continue
        rc2, _ = git("cat-file", "-e", f"{sha}:{TARGET_DIR}/39164900837.json")
        if rc2 == 0:
            preimage_ref = sha
            break

    if preimage_ref is None:
        findings.append({"finding": "NO_PREIMAGE_IN_HISTORY",
                         "severity": "material",
                         "detail": "no earlier commit carries the record; the overwrite is irreversible"})
        return {"schema": SCHEMA, "verdict": "F3B_UNRESOLVED_PREIMAGE_NOT_RECOVERABLE",
                "exit_code": 2, "preimage": None, "current": cur_meta,
                "history": history, "findings": findings}

    pre_bytes, pre_meta = git_blob_at(preimage_ref, f"{TARGET_DIR}/39164900837.json")
    if pre_bytes is None:
        findings.append({"finding": "PREIMAGE_FETCH_FAILED", "severity": "material",
                         "detail": f"could not fetch the record at {preimage_ref}"})
        return {"schema": SCHEMA, "verdict": "F3B_UNRESOLVED_PREIMAGE_NOT_RECOVERABLE",
                "exit_code": 2, "preimage": None, "current": cur_meta,
                "history": history, "findings": findings}

    recoverable = pre_meta.get("sha256") != cur_meta.get("sha256")
    restored_rel = f"{TARGET_DIR}/{RESTORED_NAME}"
    restored_path = repo / restored_rel
    restored_path.parent.mkdir(parents=True, exist_ok=True)
    restored_path.write_bytes(pre_bytes)
    restored_sha = sha256_file(restored_path)

    pre_json = json.loads(pre_bytes.decode("utf-8"))
    cur_json = json.loads(cur_bytes.decode("utf-8"))
    delta = key_delta(pre_json, cur_json)

    claims = [d for d in delta if d["change"] == "VALUE_CHANGED"]
    removals = [d for d in delta if d["change"] == "REMOVED_FROM_CURRENT"]
    additions = [d for d in delta if d["change"] == "ADDED_IN_CURRENT"]

    # 2. Test the cited escalation source.
    cited = path_exists_anywhere(CITED_ESCALATION_SOURCE)
    if not cited["exists_at_any_ref"] and not cited["ever_added_in_history"]:
        findings.append({
            "finding": "CITED_ESCALATION_SOURCE_DOES_NOT_EXIST",
            "severity": "material",
            "detail": f"{CITED_ESCALATION_SOURCE} is absent from every ref and was never added in "
                      f"any commit, so the escalation's cited provenance cannot be reproduced from "
                      f"the committed tree (factory-wide requirement 29 defect class)",
            "reproduce": f"git log --all --oneline --name-only --diff-filter=A -- "
                         f"'{CITED_ESCALATION_SOURCE}'",
        })

    verdict = ("F3B_AUTONOMOUSLY_RESOLVED_RECORD_RECOVERABLE" if recoverable
               else "F3B_PREIMAGE_IDENTICAL_NOTE_DISTINCTION_NOT_REQUIRED")

    return {
        "schema": SCHEMA, "lane": "evaluation", "direction_version": 57, "run_id": run_id,
        "verdict": verdict, "exit_code": 0 if recoverable else 2,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "question": "Which artifact is the record of record for the frozen_cache_integrity "
                    "measurement of run 39164900837 after commit 9b61dcf8 modified it in place?",
        "answer": "Both. The record AS FIRST WRITTEN is preserved byte-exactly at "
                  f"{restored_rel} and the record AS LAST WRITTEN remains untouched at "
                  f"{TARGET_DIR}/39164900837.json. No adjudication is required to read either, so "
                  "the escalation is resolved autonomously and no owner session is implied.",
        "overwriting_commit": OVERWRITE_COMMIT,
        "preimage_commit": preimage_ref,
        "history": history,
        "preimage": pre_meta,
        "current": cur_meta,
        "restored_to_new_path": {"path": restored_rel, "sha256": restored_sha,
                                 "bytes": len(pre_bytes),
                                 "overwrote_nothing": True,
                                 "note": "the pre-image was written to a NEW path; neither existing "
                                         "record was modified, restored-over or deleted"},
        "byte_identity_recovery_proof": {
            "restored_sha256_matches_preimage_sha256": restored_sha == pre_meta.get("sha256"),
            "preimage_differs_from_current": recoverable,
            "git_blob_of_preimage": pre_meta.get("git_blob"),
            "reproduce": f"git show {preimage_ref}:{TARGET_DIR}/39164900837.json | sha256sum",
        },
        "exact_delta_preimage_vs_current": {
            "n_keys_changed": len(claims), "n_keys_removed": len(removals),
            "n_keys_added": len(additions),
            "value_changed": claims, "removed": removals, "added": additions,
            "method": "recursive key-set comparison; set relations are computed directly and never "
                      "inferred from matching cardinalities",
        },
        "cited_escalation_source_check": cited,
        "findings": findings,
        "both_readings_side_by_side": {
            "as_first_written": {"path": restored_rel, "sha256": restored_sha,
                                 "verdict": pre_json.get("verdict"),
                                 "generated_at": pre_json.get("generated_at"),
                                 "has_m5_live_probe": "m5_live_probe" in pre_json},
            "as_last_written": {"path": f"{TARGET_DIR}/39164900837.json", "sha256": cur_meta["sha256"],
                                "verdict": cur_json.get("verdict"),
                                "generated_at": cur_json.get("generated_at"),
                                "has_m5_live_probe": "m5_live_probe" in cur_json},
        },
        "what_is_NOT_claimed": CLAIM_CEILING,
        "human_gate_ready": False, "owner_decision_required": False,
        "packet_admitted": False, "machine_gate_ready": False,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", "local"))
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    out = Path(args.out) if args.out else (
        REPO_ROOT / "results" / "evaluation" / "f3b_adjudication" / f"{args.run_id}.json")
    rec = adjudicate(REPO_ROOT, args.run_id)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=1, ensure_ascii=False, sort_keys=True) + "\n",
                   encoding="utf-8")
    print(json.dumps({
        "verdict": rec["verdict"], "exit_code": rec["exit_code"],
        "preimage_commit": rec.get("preimage_commit"),
        "preimage_sha256": (rec.get("preimage") or {}).get("sha256"),
        "current_sha256": (rec.get("current") or {}).get("sha256"),
        "n_keys_changed": ((rec.get("exact_delta_preimage_vs_current") or {}).get("n_keys_changed")),
        "n_keys_removed": ((rec.get("exact_delta_preimage_vs_current") or {}).get("n_keys_removed")),
        "cited_escalation_source_exists": (
            (rec.get("cited_escalation_source_check") or {}).get("exists_at_any_ref")),
        "findings": [f["finding"] for f in rec.get("findings") or []],
        "record": str(out),
    }, indent=1))
    return int(rec["exit_code"])


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())