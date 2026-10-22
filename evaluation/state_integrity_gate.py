#!/usr/bin/env python3
"""State-integrity gate for the evaluation lane's claim path.

Discharges the six required fixes of independent audit CYCLE_39751745107
(gate REVISE) as a permanent, executable instrument rather than a one-off
hand edit:

  1/2. ``evidence_refs_n`` must equal ``len(evidence_refs)`` in both state files
       (the rejected cycle shipped 118/108 and 92/84).
  3.  every ``evidence_refs`` entry must resolve in the committed tree
       (the rejected cycle shipped the non-existent
       ``reports/evaluation/CYCLE_39684675951.md``).
  4.  the top-level ``evidence_refs`` key must carry the canonical two-space
       indentation (the rejected cycle lost it in the root state).
  5/6. no block may promote a claim_bearing_run from the frozen cutoff onward
       without either an in-tree independent audit gate or an explicit
       pending-independent-audit / accepted_as_evidence=false disclosure
       (the rejected cycle promoted unaudited run 39732040165 as ACCEPTED).

The spec (checks, thresholds, cutoff, exit codes) is frozen in
``evaluation/STATE_INTEGRITY_GATE_SPEC_V1.json`` and re-hashed before each
run.  This instrument is a STATE-CLAIM gate: it never touches a packet,
a frozen rubric, a bar or a verdict contract, and it re-derives none of them.

Exit codes (frozen): 0 all checks pass; 1 at least one check failed;
2 environment error (unreadable state/spec/tree - never a pass, never a fail).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = REPO_ROOT / "evaluation" / "STATE_INTEGRITY_GATE_SPEC_V1.json"
ROOT_STATE = REPO_ROOT / "state" / "evaluation.json"
LANE_STATE = REPO_ROOT / "evaluation" / "state" / "evaluation.json"
GATE_TEMPLATE = "results/audit/evaluation/CYCLE_{run}_GATE.json"

SCHEMA = "lex-evaluation-state-integrity-gate/1"

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_ENV = 2


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check_evidence_refs_n_matches(label: str, state: dict) -> dict:
    refs = state.get("evidence_refs")
    n = state.get("evidence_refs_n")
    if not isinstance(refs, list):
        return {"check": "evidence_refs_n_matches", "file": label, "passed": False,
                "observed": "evidence_refs missing or not a list", "expected": "list"}
    ok = (n == len(refs))
    return {"check": "evidence_refs_n_matches", "file": label, "passed": ok,
            "observed": {"evidence_refs_n": n, "len_evidence_refs": len(refs)},
            "expected": {"evidence_refs_n": len(refs)}}


def check_evidence_refs_resolve(label: str, state: dict, repo_root: Path) -> dict:
    refs = state.get("evidence_refs") or []
    missing = []
    for r in refs:
        cand = str(r).split(" ")[0].rstrip(",")
        if not (repo_root / cand).is_file():
            missing.append(r)
    return {"check": "evidence_refs_resolve", "file": label, "passed": not missing,
            "observed": {"n_refs": len(refs), "non_file_refs": missing},
            "expected": "every ref is an existing file in the committed tree "
                        "(directories do not count, matching the lane's "
                        "test_evidence_refs_exist contract)"}


def check_evidence_refs_canonical_indent(label: str, raw: str) -> dict:
    bad_lines = []
    for i, line in enumerate(raw.splitlines(), 1):
        if re.match(r'^"evidence_refs":\s*\[', line):
            if not line.startswith('  "evidence_refs"'):
                bad_lines.append({"line": i, "content": line[:60]})
    return {"check": "evidence_refs_canonical_indent", "file": label,
            "passed": not bad_lines,
            "observed": {"offending_lines": bad_lines},
            "expected": 'top-level "evidence_refs" line starts with two spaces'}


def _iter_claim_bearing_blocks(state: dict):
    """Yield (block_path, block) for every dict carrying claim_bearing_run."""
    def walk(node, path):
        if isinstance(node, dict):
            if "claim_bearing_run" in node:
                yield path, node
            for k, v in node.items():
                yield from walk(v, f"{path}/{k}" if path else k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                yield from walk(v, f"{path}[{i}]")
    yield from walk(state, "")


def check_no_unaudited_promotion(label: str, state: dict, repo_root: Path,
                                 cutoff: str) -> dict:
    cutoff_int = int(cutoff)
    inventory, failures = [], []
    for path, block in _iter_claim_bearing_blocks(state):
        run = str(block.get("claim_bearing_run"))
        gate_rel = GATE_TEMPLATE.format(run=run)
        gate_exists = (repo_root / gate_rel).exists()
        disclosed = (
            block.get("audit_status") == "PENDING_INDEPENDENT_AUDIT"
            or block.get("pending_independent_audit") is True
            or block.get("accepted_as_evidence") is False
            or ("audit_gate" in block) or ("audit_run_id" in block)
        )
        try:
            in_scope = int(re.sub(r"\D", "", run)[:12] or "0") >= cutoff_int
        except ValueError:
            in_scope = False
        row = {"block": path, "claim_bearing_run": run,
               "audit_gate_in_tree": gate_exists,
               "audit_disclosure_present": disclosed,
               "in_failing_scope": in_scope}
        inventory.append(row)
        if in_scope and not (gate_exists or disclosed):
            failures.append(row)
    return {"check": "no_unaudited_promotion", "file": label,
            "passed": not failures,
            "observed": {"frozen_cutoff_run": cutoff, "failures": failures,
                         "inventory": inventory},
            "expected": "no in-scope block promotes an unaudited run without disclosure"}


def check_accepted_run_audited(label: str, state: dict, repo_root: Path) -> dict:
    run = str(state.get("accepted_run_id"))
    gate_rel = GATE_TEMPLATE.format(run=run)
    exists = (repo_root / gate_rel).exists()
    return {"check": "accepted_run_audited", "file": label, "passed": exists,
            "observed": {"accepted_run_id": run, "gate_file": gate_rel,
                         "exists": exists},
            "expected": "accepted_run_id has an in-tree audit gate"}


def check_root_lane_parity(root: dict, lane: dict) -> dict:
    fields = ["accepted_run_id", "direction_version", "github_run"]
    diffs = {}
    for f in fields:
        if root.get(f) != lane.get(f):
            diffs[f] = {"root": root.get(f), "lane": lane.get(f)}
    return {"check": "root_lane_parity", "file": "both", "passed": not diffs,
            "observed": {"differences": diffs},
            "expected": "accepted_run_id, direction_version, github_run identical"}


def run(repo_root: Path = REPO_ROOT, spec_path: Path = SPEC_PATH) -> tuple[int, dict]:
    try:
        spec = _load(spec_path)
        root_path = repo_root / "state" / "evaluation.json"
        lane_path = repo_root / "evaluation" / "state" / "evaluation.json"
        root_raw = root_path.read_text(encoding="utf-8")
        lane_raw = lane_path.read_text(encoding="utf-8")
        root = json.loads(root_raw)
        lane = json.loads(lane_raw)
    except Exception as exc:  # environment error: never pass, never fail
        return EXIT_ENV, {"schema": SCHEMA, "verdict": "ENVIRONMENT_ERROR",
                          "exit_code": EXIT_ENV, "error": repr(exc)}

    cutoff = next(c["frozen_promotion_cutoff_run"] for c in spec["checks"]
                  if c["id"] == "no_unaudited_promotion")

    checks = [
        check_evidence_refs_n_matches("state/evaluation.json", root),
        check_evidence_refs_n_matches("evaluation/state/evaluation.json", lane),
        check_evidence_refs_resolve("state/evaluation.json", root, repo_root),
        check_evidence_refs_resolve("evaluation/state/evaluation.json", lane, repo_root),
        check_evidence_refs_canonical_indent("state/evaluation.json", root_raw),
        check_evidence_refs_canonical_indent("evaluation/state/evaluation.json", lane_raw),
        check_no_unaudited_promotion("state/evaluation.json", root, repo_root, cutoff),
        check_no_unaudited_promotion("evaluation/state/evaluation.json", lane, repo_root, cutoff),
        check_accepted_run_audited("state/evaluation.json", root, repo_root),
        check_accepted_run_audited("evaluation/state/evaluation.json", lane, repo_root),
        check_root_lane_parity(root, lane),
    ]
    failed = [c for c in checks if not c["passed"]]
    verdict = "ALL_CHECKS_PASS" if not failed else "AT_LEAST_ONE_CHECK_FAILED"
    code = EXIT_PASS if not failed else EXIT_FAIL
    try:
        spec_display = str(spec_path.relative_to(repo_root))
    except ValueError:
        spec_display = str(spec_path)
    out = {
        "schema": SCHEMA,
        "verdict": verdict,
        "exit_code": code,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "spec_path": spec_display,
        "spec_sha256": sha256_file(spec_path),
        "n_checks": len(checks),
        "n_passed": len(checks) - len(failed),
        "n_failed": len(failed),
        "failed_checks": [c["check"] + "@" + c["file"] for c in failed],
        "checks": checks,
        "claim_ceiling": (
            "This gate establishes exactly one thing: whether the lane's two state "
            "files and their claim-bearing blocks are internally consistent and "
            "free of the six defect classes named by audit CYCLE_39751745107. It "
            "does NOT re-score, move or re-derive any frozen absolute LABEL_SOUND / "
            "GEOMETRY_SOUND bar (REPORTED-ONLY, unmet on the v3 bytes); it does NOT "
            "lift any DO-NOT-SERVE order; it does NOT certify packet admission; it "
            "does NOT audit any measurement's numbers; it does NOT claim the map "
            "helps a jurist; it runs no universal-174k benchmark."
        ),
    }
    return code, out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--out", default=None,
                    help="write the full JSON record here (dirs created)")
    args = ap.parse_args(argv)
    code, out = run()
    if args.run_id:
        out["run_id"] = args.run_id
    if args.out:
        p = Path(args.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(out, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                     encoding="utf-8")
    print(json.dumps({"verdict": out.get("verdict"), "exit_code": code,
                      "n_checks": out.get("n_checks"), "n_failed": out.get("n_failed"),
                      "failed_checks": out.get("failed_checks"),
                      "record": args.out}, indent=1))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
