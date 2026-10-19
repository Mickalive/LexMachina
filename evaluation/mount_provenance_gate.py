#!/usr/bin/env python3
"""Mount-provenance gate: make ``product_mount_head`` a RE-DERIVED fact, not a typed string.

WHY THIS EXISTS
---------------
Factory-wide requirement 29 names the binding operational defect class of this
factory: *a published claim does not reproduce from the committed tree*.  This
instrument exists because the resumed cycle 39231573047 found that defect class
live in run 39225862749's own headline provenance.

``evaluation/mapping_free_recall_falsifier.py`` records

    "product_mount_head": mount_head(mount)      # evaluation/mapping_free_recall_falsifier.py:597

and the freeze record records a hand-typed

    "mount_head_at_freeze": "577efeb8..."        # MAPPING_FREE_RECALL_FALSIFIER_FREEZE_RECORD.json:24

Both say ``577efeb836757b0b0eee22f7bc2436c52e2addbb``.  Recomputed on the live
mount in this cycle that string is **49cc4bea1c612a94882a9d3590eabb914b316cdc**.
The two are different commits, six generations apart, and ``577efeb8`` is dated
2026-10-19T05:01:18Z while the producer run started at 08:52:20Z - after five
later ``lab/product`` commits already existed.

The important part is WHAT IS AND IS NOT AFFECTED, and this instrument separates
the two explicitly rather than collapsing them:

* **the measurements** are pinned by content digest, not by head string.  All 14
  frozen mount inputs re-hash identical at the live mount, so the falsifier's
  numbers still reproduce.  This gate re-derives that.
* **the provenance string** does not reproduce.  A head string is a claim about
  *which tree was measured*; if it cannot be re-derived it may not be quoted.

So this gate publishes exactly two verdicts and never merges them:

    PIN_VERDICT       - do the frozen measured bytes still reproduce?
    PROVENANCE_VERDICT - does every recorded mount-head claim re-derive?

READ-ONLY BY CONSTRUCTION
-------------------------
This module never writes, edits, moves or deletes a frozen artefact, a result
record, a state file, a report or a bar.  Its only write is the NEW record named
by ``--out``.  It introduces NO threshold, NO bar and NO pass rule of its own:
agreement is exact string equality and digest equality, and nothing else.

GRADING (factory-wide requirement 33 forbids publishing an un-reproducible
number as if it were re-derived):

    MEASURED   - recomputed here from the live mount or from a committed file.
    CANDIDATE  - consistent with the evidence but NOT established; carries the
                 reason it cannot be established from this lane.

Every exit path writes its record, because a refusal that writes no artifact
cannot be re-derived from the committed tree (the defect this lane already
repaired once in cycle 39225862749).

Exit codes
----------
0  PROVENANCE_VERIFIED       - pins reproduce AND every recorded head re-derives.
1  PROVENANCE_UNREPRODUCIBLE - at least one recorded head does not re-derive.
2  NOT_MEASURED              - mount or freeze record unreadable.  Never a pass.
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
DEFAULT_MOUNT = "/tmp/lex_accepted/product"
FREEZE_RECORD = "evaluation/MAPPING_FREE_RECALL_FALSIFIER_FREEZE_RECORD.json"

# Every artifact this gate re-reads.  Listed explicitly so an added or renamed
# artifact cannot silently escape the audit: the gate's coverage is the point.
PROVENANCE_SOURCES: tuple[tuple[str, str], ...] = (
    ("evaluation/MAPPING_FREE_RECALL_FALSIFIER_FREEZE_RECORD.json", "frozen_mount_input_digests_before_execution.mount_head_at_freeze"),
    ("results/evaluation/mapping_free_recall_falsifier/39225862749.json", "product_mount_head"),
    ("state/evaluation.json", "mapping_free_recall_falsifier.product_mount_head"),
    ("reports/evaluation/CYCLE_39225862749.md", "prose:'- Product mount:' line"),
)

CLAIM_CEILING = (
    "This gate establishes ONE thing: whether the mount-provenance claims recorded by "
    "cycle 39225862749 re-derive from the live accepted-product mount, and separately whether "
    "the frozen measured bytes still reproduce. It does NOT re-measure retrieval, does NOT move "
    "or re-derive any frozen bar, does NOT edit any frozen artefact or result record, does NOT "
    "certify admission of any packet, does NOT lift either DO-NOT-SERVE order, does NOT claim the "
    "map helps a jurist, and does NOT authorise an owner session. human_gate_ready stays false."
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str, cwd: str | Path | None = None) -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(cwd or REPO_ROOT), *args],
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def live_mount_head(mount: Path) -> str | None:
    return _git("rev-parse", "HEAD", cwd=mount)


def commit_facts(sha: str) -> dict[str, Any]:
    """MEASURED facts about a commit that the gate can compute locally."""
    if not sha or len(sha) != 40:
        return {"resolvable": False, "reason": "not a 40-hex sha"}
    subject = _git("log", "--format=%s", "-1", sha)
    if subject is None:
        return {"resolvable": False,
                "reason": "commit is not present in this repository's object store "
                          "(the lane checkout is shallow; see report). Provenance CANNOT be "
                          "established from here."}
    return {"resolvable": True, "subject": subject,
            "committed_at": _git("log", "--format=%cI", "-1", sha)}


def generations_behind(sha: str, head: str) -> int | None:
    """MEASURED commit-distance from ``sha`` to ``head`` along first-parent."""
    if not sha or not head or sha == head:
        return 0 if sha == head else None
    out = _git("rev-list", "--count", f"{sha}..{head}")
    try:
        return int(out) if out is not None else None
    except ValueError:
        return None


def check_pins(mount: Path, pins: dict[str, Any]) -> dict[str, Any]:
    """MEASURED: do the frozen measured bytes still reproduce at the live mount?"""
    rows, n_match, n_drift, n_missing = [], 0, 0, 0
    for rel, want in sorted(pins.items()):
        if rel in ("mount", "mount_head_at_freeze") or not isinstance(want, str) or len(want) != 64:
            continue
        target = mount / rel
        if not target.exists():
            rows.append({"path": rel, "status": "MISSING", "want": want}); n_missing += 1; continue
        got = _sha256(target)
        ok = got == want
        n_match += ok; n_drift += (not ok)
        rows.append({"path": rel, "status": "MATCH" if ok else "DRIFT",
                     "want": want, "got": got})
    return {"n_pins": n_match + n_drift + n_missing, "n_match": n_match,
            "n_drift": n_drift, "n_missing": n_missing, "pins": rows,
            "verdict": "PIN_VERDICT_VERIFIED" if not (n_drift or n_missing) else "PIN_VERDICT_BROKEN"}


def _read_value(rel: str, pointer: str) -> Any:
    """Return the recorded head string at ``pointer`` inside ``rel``."""
    p = REPO_ROOT / rel
    if not p.exists():
        return None
    if rel.endswith(".md"):
        for line in p.read_text(errors="replace").splitlines():
            if "Product mount:" in line:
                for tok in line.replace("`", " ").split():
                    if len(tok) == 40 and all(c in "0123456789abcdef" for c in tok):
                        return tok
        return None
    node: Any = json.loads(p.read_text())
    for key in pointer.split("."):
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node


def check_provenance(mount: Path, head: str | None) -> dict[str, Any]:
    """MEASURED: does every recorded mount-head claim re-derive from the live mount?"""
    rows, n_ok, n_bad, n_absent = [], 0, 0, 0
    for rel, pointer in PROVENANCE_SOURCES:
        val = _read_value(rel, pointer)
        if not val:
            rows.append({"source": rel, "pointer": pointer, "status": "ABSENT",
                         "note": "no value recorded at this pointer in the committed tree"})
            n_absent += 1; continue
        matches = (val == head)
        n_ok += matches; n_bad += (not matches)
        facts = commit_facts(val)
        row: dict[str, Any] = {
            "source": rel, "pointer": pointer, "recorded": val,
            "live_mount_head": head, "matches_live": matches,
            "commit_resolvable_here": facts.get("resolvable"),
            "commit_subject": facts.get("subject"),
            "commit_committed_at": facts.get("committed_at"),
            "generations_behind_live": generations_behind(val, head) if head else None,
            "unresolvable_reason": facts.get("reason"),
        }
        row["status"] = "RE_DERIVES" if matches else "DOES_NOT_RE_DERIVE"
        rows.append(row)
    verdict = ("PROVENANCE_VERIFIED" if not n_bad
               else "PROVENANCE_UNREPRODUCIBLE")
    return {"n_claims": n_ok + n_bad + n_absent, "n_re_derive": n_ok,
            "n_do_not_re_derive": n_bad, "n_absent": n_absent,
            "live_mount_head": head, "claims": rows, "verdict": verdict}


def run(run_id: str, out: Path, mount: Path) -> tuple[int, dict[str, Any]]:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    record: dict[str, Any] = {
        "schema": "lex-evaluation-mount-provenance-gate/1", "lane": "evaluation",
        "direction_version": 57, "run_id": run_id, "generated_at_utc": stamp,
        "instrument": "evaluation/mount_provenance_gate.py",
        "resumes_run": "39225862749",
        "mount": str(mount), "read_only": True,
        "claim_ceiling": CLAIM_CEILING,
        "numeric_environment": {
            "python": sys.version.split()[0],
            "platform": sys.platform,
            "repo_is_shallow": (REPO_ROOT / ".git" / "shallow").exists(),
            "note": "This gate performs no numeric linear algebra and asserts no "
                    "cross-machine byte identity; it compares sha256 digests and exact strings.",
        },
        "human_gate_ready": False, "machine_gate_ready": False, "packet_admitted": False,
        "ready_for_owner_session": False, "owner_decision_required": False,
    }

    if not mount.is_dir():
        record.update(verdict="NOT_MEASURED", exit_code=2,
                      reason=f"mount {mount} absent; provenance is UNMEASURED, never a pass",
                      pin_verdict=None, provenance_verdict=None)
        _emit(out, record); return 2, record

    fr_rel = REPO_ROOT / FREEZE_RECORD
    if not fr_rel.exists():
        record.update(verdict="NOT_MEASURED", exit_code=2,
                      reason=f"freeze record {FREEZE_RECORD} absent; nothing to pin",
                      pin_verdict=None, provenance_verdict=None)
        _emit(out, record); return 2, record

    fr = json.loads(fr_rel.read_text())
    pins = fr.get("frozen_mount_input_digests_before_execution", {}) or {}
    head = live_mount_head(mount)

    pin_verdict = check_pins(mount, pins)
    prov_verdict = check_provenance(mount, head)

    record["freeze_record"] = {"path": FREEZE_RECORD, "sha256": _sha256(fr_rel)}
    record["live_mount_head"] = head
    record["live_mount_head_subject"] = _git("log", "--format=%s", "-1", head) if head else None
    record["pin_verdict"] = pin_verdict
    record["provenance_verdict"] = prov_verdict

    # The two verdicts are published together and NEVER merged. A head string is
    # a claim about WHICH tree was measured; a pin is the measured content.
    if prov_verdict["verdict"] == "PROVENANCE_UNREPRODUCIBLE":
        verdict, code = "PROVENANCE_UNREPRODUCIBLE", 1
    elif pin_verdict["verdict"] == "PIN_VERDICT_BROKEN":
        verdict, code = "PIN_VERDICT_BROKEN", 1
    else:
        verdict, code = "PROVENANCE_VERIFIED", 0
    record["verdict"] = verdict
    record["exit_code"] = code
    record["measurements_reproduce"] = pin_verdict["verdict"] == "PIN_VERDICT_VERIFIED"
    record["provenance_reproduces"] = prov_verdict["verdict"] == "PROVENANCE_VERIFIED"
    _emit(out, record)
    return code, record


def _emit(out: Path, record: dict[str, Any]) -> None:
    """Every exit path writes. A refusal with no artifact is not re-derivable."""
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2, sort_keys=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", "local"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--mount", default=DEFAULT_MOUNT)
    args = ap.parse_args(argv)
    out = Path(args.out) if args.out else (
        REPO_ROOT / "results" / "evaluation" / "mount_provenance_gate" / f"{args.run_id}.json")
    code, rec = run(args.run_id, out, Path(args.mount))
    pv = rec.get("pin_verdict") or {}
    qv = rec.get("provenance_verdict") or {}
    print(json.dumps({
        "verdict": rec.get("verdict"), "exit_code": code,
        "live_mount_head": rec.get("live_mount_head"),
        "pins": f"{pv.get('n_match')}/{pv.get('n_pins')}",
        "pin_verdict": pv.get("verdict"),
        "head_claims": f"{qv.get('n_re_derive')}/{qv.get('n_claims')} re-derive",
        "provenance_verdict": qv.get("verdict"),
        "measurements_reproduce": rec.get("measurements_reproduce"),
        "provenance_reproduces": rec.get("provenance_reproduces"),
        "record": str(out),
    }, indent=1))
    return code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())