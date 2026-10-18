#!/usr/bin/env python3
"""Is direction-v57 Item 2 CONSUMABLE right now, and if not, what exactly blocks it?

WHY THIS FILE EXISTS
--------------------
Direction v57 item 2 is the only work this lane may not do on its own initiative:
*consume, do not pre-empt* the accepted Product handoff
``question_native_coverage_39113690481`` by falsifying-or-passing the ordered
``query_concepts_under_covered`` admission warning on the exact served bytes.
Cycles 39164900837 and 39167917715 both executed that falsifier against the
accepted product head ``bcb12177...`` and both recorded
``FAIL_NOT_LANDED`` - the ordered disclosure is still absent there.

Re-executing it a third time against the same bytes would be a zero-delta
re-observation of a result the lane already holds, and a zero-delta cycle is
invalid.  It is also the failure mode the direction warns about: pretending to
consume a handoff that cannot be consumed.

So the lane needs a *gate in front of* the consumption, derived from git and
from the bytes, that answers one question and names the blocking object:

    has the accepted product head moved since the last executed falsification?

* **unchanged** -> the served bytes and the product code are the same ones the
  last run already falsified.  Status ``HANDOFF_OPEN__BLOCKED_ON_PRODUCT``,
  and the correct action is NO re-execution.
* **moved** -> consumption is possible, and
  ``evaluation/coverage_finding_falsification.py`` is HEAD-PINNED: it refuses
  to run against any head other than the one frozen in
  ``COVERAGE_FINDING_FALSIFICATION_HYPOTHESIS_V1.json``.  So the next step is
  named explicitly: re-freeze the hypothesis against the new head and re-hash
  the served bundle/admissibility digests BEFORE executing anything.

The status is a gate, never a pass.  ``READY_TO_CONSUME`` is not a claim that
the handoff was satisfied; only an executed falsification record can say that.

NO NETWORK.  NO PRODUCT CODE IS IMPORTED.  NO FROZEN FILE IS WRITTEN.
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

SCHEMA = "lex-evaluation-coverage-handoff-status/1"
RECORD_SCHEMA = "lex-coverage-finding-falsification/1"
RECORD_GLOB = "results/evaluation/coverage_finding_falsification/*.json"
FALSIFIER = "evaluation/coverage_finding_falsification.py"

STATUS_BLOCKED = "HANDOFF_OPEN__BLOCKED_ON_PRODUCT__DO_NOT_RE_EXECUTE"
STATUS_READY = "READY_TO_CONSUME__RE_FREEZE_THE_FALSIFIER_FIRST"
STATUS_MOUNT_ABSENT = "MOUNT_ABSENT__STATUS_UNKNOWN"
STATUS_NO_RECORD = "NO_EXECUTED_FALSIFICATION_RECORD"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head(root: Path) -> str | None:
    proc = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                          capture_output=True, text=True)
    return proc.stdout.strip() if proc.returncode == 0 else None


def latest_falsification_record(repo: Path) -> dict | None:
    """Newest committed falsification record, selected by its own schema."""
    best = None
    for path in sorted(repo.glob(RECORD_GLOB)):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict) or data.get("schema") != RECORD_SCHEMA:
            continue
        if best is None or str(data.get("generated_at", "")) > str(best[1].get("generated_at", "")):
            best = (path, data)
    return {"path": best[0], "record": best[1]} if best else None


def derive_status(*, prior_head: str | None, current_head: str | None,
                  mount_present: bool) -> str:
    if not mount_present or current_head is None:
        return STATUS_MOUNT_ABSENT
    if prior_head is None:
        return STATUS_NO_RECORD
    return STATUS_BLOCKED if current_head == prior_head else STATUS_READY


def next_command(run_id: str, status: str, prior_head: str | None) -> str:
    if status == STATUS_READY:
        return (
            f"1) re-freeze: copy evaluation/COVERAGE_FINDING_FALSIFICATION_HYPOTHESIS_V1.json "
            f"to V2, set FROZEN_PRODUCT_HEAD and served_byte_digests_frozen to the NEW head "
            f"{'(prior ' + prior_head[:12] + ' -> now new)' if prior_head else ''}, "
            f"and bump FROZEN_PRODUCT_HEAD in {FALSIFIER} - freeze BEFORE execution; "
            f"2) execute: python -m evaluation.coverage_finding_falsification "
            f"--run-id <run> --out results/evaluation/coverage_finding_falsification/<run>.json "
            f"3) publish the before/after admission records side by side.")
    if status == STATUS_BLOCKED:
        return ("DO NOT re-execute. The accepted product head is unchanged, so the "
                "served bytes and the product code are the ones run <prior> already "
                "falsified (FAIL_NOT_LANDED). Re-running would be a zero-delta "
                "re-observation. The blocking object is Product's ordered fix in "
                "product/query/gate_admissibility.py: under_covered is still only "
                "surfaced inside the blocking answer_cites_nothing branch.")
    if status == STATUS_MOUNT_ABSENT:
        return ("accepted product mount absent; the handoff status is UNKNOWN, not PASS. "
                "Mount /tmp/lex_accepted/product and re-run this probe.")
    return ("an executed falsification record is required before a status can exist; "
            f"run: python -m {FALSIFIER} --run-id <run> --out "
            f"results/evaluation/coverage_finding_falsification/<run>.json")


def probe(repo: Path, product_root: Path, run_id: str) -> dict:
    mount_present = (product_root / ".git").exists()
    current_head = _git_head(product_root) if mount_present else None
    latest = latest_falsification_record(repo)
    prior_head = latest["record"].get("accepted_product_head") if latest else None
    status = derive_status(prior_head=prior_head, current_head=current_head,
                           mount_present=mount_present)

    prior = None
    if latest:
        verdict = latest["record"].get("verdict") or {}
        bundles = latest["record"].get("bundles") or []
        prior = {
            "record": str(latest["path"].relative_to(repo)),
            "record_sha256": _sha256(_REPO_ROOT / latest["path"].relative_to(repo)),
            "generated_at": latest["record"].get("generated_at"),
            "accepted_product_head": prior_head,
            "S1_pass_all_bundles_match_predicate": verdict.get("S1_pass_all_bundles_match_predicate"),
            "S2_outcome": verdict.get("S2_outcome"),
            "failing_bundles": verdict.get("failing_bundles"),
            "per_bundle_outcomes": {b.get("bundle"): b.get("outcome") for b in bundles},
        }

    return {
        "schema": SCHEMA,
        "run_id": run_id,
        "lane": "evaluation",
        "direction_version": int(json.loads(
            (repo / "state/evaluation.json").read_text(encoding="utf-8"))["direction_version"]),
        "measured_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "handoff_under_test": ("question_native_coverage_39113690481 -> emit an admission "
                               "finding (severity warning) whenever "
                               "measured.query_concepts_under_covered is non-empty"),
        "product_mount": str(product_root),
        "product_mount_present": mount_present,
        "current_product_head": current_head,
        "prior_product_head": prior_head,
        "product_head_moved": bool(prior_head and current_head and prior_head != current_head),
        "last_executed_falsification": prior,
        "status": status,
        "executed_this_cycle": False,
        "why_not_executed": (
            "direction v57 item 2 forbids pre-empting the handoff, and the "
            "falsifier is head-pinned; re-running against an unchanged head "
            "would be a zero-delta re-observation."),
        "next_command": next_command(run_id, status, prior_head),
        "claim_ceiling": (
            "A GATE, never a verdict on the handoff. READY_TO_CONSUME says the "
            "inputs moved and the falsifier may be re-frozen and run; it does "
            "NOT say the ordered disclosure exists, and it is never a pass of "
            "Item 2. Only an executed falsification record can move Item 2."),
        "selftest": selftest(),
    }


def selftest() -> dict:
    """Non-vacuity: the status must actually flip when the head moves."""
    cases = [
        {"prior_head": "a" * 40, "current_head": "a" * 40, "mount_present": True,
         "expected": STATUS_BLOCKED},
        {"prior_head": "a" * 40, "current_head": "b" * 40, "mount_present": True,
         "expected": STATUS_READY},
        {"prior_head": "a" * 40, "current_head": None, "mount_present": False,
         "expected": STATUS_MOUNT_ABSENT},
        {"prior_head": None, "current_head": "b" * 40, "mount_present": True,
         "expected": STATUS_NO_RECORD},
    ]
    observed = []
    for case in cases:
        got = derive_status(prior_head=case["prior_head"],
                            current_head=case["current_head"],
                            mount_present=case["mount_present"])
        observed.append({**case, "observed": got, "passed": got == case["expected"]})
    # the blocked status must never emit an execute command
    blocked_cmd = next_command("x", STATUS_BLOCKED, "a" * 40)
    observed.append({"case": "blocked_status_does_not_emit_an_execute_command",
                     "observed": blocked_cmd[:24],
                     "passed": "DO NOT re-execute" in blocked_cmd})
    return {"schema": "lex-evaluation-coverage-handoff-status-selftest/1",
            "cases": observed,
            "all_passed": all(c["passed"] for c in observed)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", default="local")
    ap.add_argument("--product-root", default="/tmp/lex_accepted/product")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    report = probe(_REPO_ROOT, Path(args.product_root), args.run_id)
    if args.out:
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print(json.dumps({k: report[k] for k in
                      ("schema", "status", "current_product_head", "prior_product_head",
                       "product_head_moved", "executed_this_cycle")}, indent=1))
    return 0 if report["selftest"]["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())