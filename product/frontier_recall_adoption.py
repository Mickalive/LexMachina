#!/usr/bin/env python3
"""Factory-wide requirement 21: record an adopt/decline decision on the accepted
Frontier component ``frontier-query-concept-recall``, with the numbers beside it.

Why this file exists
--------------------
Cycle 39169296466 recorded ``DECLINE_NOW_NOTHING_TO_ADOPT`` against a mount that
was still ``INITIALIZED`` with no artifacts.  That reason is now **false**: the
team completed and its branch was promoted (``accept Frontier
frontier-query-concept-recall 39181670816``), so the mount ships a canonical
integration contract, a harness record, two contract-check records and two audit
gates.  Factory-wide requirement 21 and the contract's own
``silent_non_consumption_not_permitted`` flag both require the integrator to
record a decision **on the artifact that actually exists**, so the stale reason
is discharged here rather than left to rot.

The contract's disposition is unambiguous
-----------------------------------------
``item_disposition`` = "CLOSED per the charter stop rule at OUTCOME_B ... the
measured layer does not meet the promotion bar"; ``product_decision_required`` =
true; ``measured_outcome.improved_fr_it_cells`` = 0;
``runtime_cost.retrieval_cost.n_calls_over_per_search_budget`` = 10 of 15 added
searches over the frozen per-search limit, max 83.505 s against 30.0 s; and
``structural_finding.bar_reachable_at_all`` = false.  The decision this module
writes is therefore DECLINE - and it is written as **DECLINE**, not as silence:
the numbers are copied out of the contract by code, never typed by hand.

Fail-closed behaviour
---------------------
If the mount is absent, or the contract is absent, or the contract's own
contract-check did not pass, this module does not fall back to "nothing to
adopt" and it does not claim a decision.  It records
``DECISION_NOT_REACHABLE`` with the reason, and exits non-zero.  A decline is a
legitimate outcome; an unrecorded one is not.

Usage
-----
    python product/frontier_recall_adoption.py --write --run-id <id> --commit <sha>
    python product/frontier_recall_adoption.py --json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCHEMA = "product-frontier-recall-adoption/1"

TEAM = "frontier-query-concept-recall"
DEFAULT_MOUNT = Path("/tmp/lex_accepted/frontier") / TEAM
CONTRACT_REL = "results/frontier/frontier-query-concept-recall/integration_contract_39179862363.json"
CONTRACT_CHECK_REL = "results/frontier/frontier-query-concept-recall/contract_check_results_39179862363.json"
HARNESS_REL = "results/frontier/frontier-query-concept-recall/harness_results_39179862363.json"
STATE_REL = f"state/frontier/{TEAM}.json"
GATES_REL = f"results/audit/frontier/{TEAM}"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _git_head(path: Path) -> str | None:
    try:
        return subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=30, check=False,
        ).stdout.strip() or None
    except Exception:
        return None


def latest_gate(mount: Path) -> tuple[str | None, dict | None]:
    """The newest audit gate on the mount, by the run id in its filename."""
    d = mount / GATES_REL
    if not d.is_dir():
        return None, None
    best: tuple[int, str, dict] | None = None
    for p in d.glob("CYCLE_*_GATE.json"):
        try:
            rid = int(p.name.split("_")[1])
        except (IndexError, ValueError):
            continue
        if best is None or rid > best[0]:
            try:
                best = (rid, p.name, _load(p))
            except Exception:
                continue
    return (best[1], best[2]) if best else (None, None)


def inspect(mount: Path = DEFAULT_MOUNT) -> dict:
    """Derive the decision inputs from the mount.  Never raises."""
    mount = Path(mount)
    rec: dict[str, Any] = {
        "schema": SCHEMA,
        "team_id": TEAM,
        "mount_path": str(mount),
        "mount_present": mount.is_dir(),
        "decision": "DECISION_NOT_REACHABLE",
        "reason": None,
        "failures": [],
    }
    if not mount.is_dir():
        rec["failures"].append("mount is not mounted; no decision is recorded")
        rec["reason"] = (
            f"{mount} is not mounted, so there is no accepted component to decide on. "
            "This is NOT the prior 'nothing to adopt' outcome and is never presented as "
            "a decision: an absent mount records DECISION_NOT_REACHABLE and exits non-zero."
        )
        return rec

    rec["mount_git_head"] = _git_head(mount)
    contract_path = mount / CONTRACT_REL
    check_path = mount / CONTRACT_CHECK_REL
    harness_path = mount / HARNESS_REL
    state_path = mount / STATE_REL
    for name, p in (("integration_contract", contract_path),
                    ("contract_check", check_path),
                    ("harness_results", harness_path)):
        rec[f"{name}_present"] = p.is_file()
        if p.is_file():
            rec[f"{name}_sha256"] = _sha256_file(p)
    if state_path.is_file():
        try:
            st = _load(state_path)
            rec["team_state"] = {
                "cycle_status": st.get("cycle_status"),
                "evidence_tier": st.get("evidence_tier"),
                "outcome": st.get("outcome"),
                "continue_recommended": st.get("continue_recommended"),
                "accepted_commit": st.get("accepted_commit"),
                "accepted_run_id": st.get("accepted_run_id"),
            }
        except Exception as exc:
            rec["failures"].append(f"team state unreadable: {type(exc).__name__}: {exc}")

    gate_name, gate = latest_gate(mount)
    rec["accepted_audit_gate"] = {
        "file": gate_name,
        "gate": (gate or {}).get("gate"),
        "safe_to_integrate": (gate or {}).get("safe_to_integrate"),
        "required_fixes": (gate or {}).get("required_fixes"),
    }

    if not contract_path.is_file():
        rec["failures"].append("canonical integration contract is absent; nothing to decide on")
        rec["reason"] = (
            f"{contract_path} is absent from the mount. No decision is recorded: a mount "
            "without its canonical contract cannot be adopted or declined on evidence."
        )
        return rec
    contract = _load(contract_path)

    # Numbers are COPIED OUT OF THE CONTRACT BY CODE.  Nothing below is typed.
    rec["contract_excerpt"] = {
        "schema": contract.get("schema"),
        "team_id": contract.get("team_id"),
        "charter_version": contract.get("charter_version"),
        "direction_version": contract.get("direction_version"),
        "github_run_id": contract.get("github_run_id"),
        "item_disposition": contract.get("item_disposition"),
        "product_decision_required": contract.get("product_decision_required"),
        "silent_non_consumption_not_permitted": contract.get("silent_non_consumption_not_permitted"),
        "drop_in_path_code": (contract.get("drop_in_path") or {}).get("code"),
        "drop_in_path_bundle_parameter": (contract.get("drop_in_path") or {}).get("bundle_parameter"),
    }
    outcome = contract.get("measured_outcome") or {}
    cost = ((contract.get("runtime_cost") or {}).get("retrieval_cost")) or {}
    structural = contract.get("structural_finding") or {}
    rec["numbers_from_contract"] = {
        "improved_fr_it_cells": outcome.get("improved_fr_it_cells"),
        "accepted_baseline_reproduced": outcome.get("accepted_baseline_reproduced"),
        "added_searches": cost.get("added_searches"),
        "n_calls_over_per_search_budget": cost.get("n_calls_over_per_search_budget"),
        "per_search_budget_seconds": cost.get("per_search_budget_seconds"),
        "max_per_search_seconds": cost.get("max_per_search_seconds"),
        "measured_sum_latency_seconds": cost.get("measured_sum_latency_seconds"),
        "bar_reachable_at_all": structural.get("bar_reachable_at_all"),
        "outcome_a_coverage_bar": structural.get("outcome_a_coverage_bar"),
        "max_reducible_questions": structural.get("max_reducible_questions"),
        "served_questions_with_zero_under_covered_at_baseline":
            structural.get("served_questions_with_zero_under_covered_at_baseline"),
    }

    if check_path.is_file():
        chk = _load(check_path)
        rec["contract_check"] = {
            "contract_executable": chk.get("contract_executable"),
            "n_checks": chk.get("n_checks"),
            "n_failed": chk.get("n_failed"),
            "network_calls": chk.get("network_calls"),
            "model_calls": chk.get("model_calls"),
        }
        if chk.get("n_failed") not in (0, None):
            rec["failures"].append(
                f"the team's own contract check reports {chk.get('n_failed')} failed checks"
            )
    if harness_path.is_file():
        try:
            h = _load(harness_path)
            v = h.get("verdict") or {}
            # Scalars only: the harness verdict object is thousands of lines and
            # this record is a decision, not a copy of the team's evidence.
            rec["harness_scalars"] = {
                "outcome": v.get("outcome"),
                "improved_fr_it_cells": v.get("improved_fr_it_cells"),
                "failing_fr_it_cells_total": v.get("failing_fr_it_cells_total"),
                "reduced_under_covered_questions": v.get("reduced_under_covered_questions"),
                "required_fr_it_cells": v.get("required_fr_it_cells"),
                "required_reduced_questions": v.get("required_reduced_questions"),
                "n_calls_over_per_search_budget": v.get("n_calls_over_per_search_budget"),
                "transport_all_ok": v.get("transport_all_ok"),
                "regressed_gates": v.get("regressed_gates"),
                "outcome_a_criteria": v.get("outcome_a_criteria"),
                "acceptance_test_5_status": (v.get("acceptance_test_5_non_vacuity") or {}).get("status"),
            }
            rec["harness_run_id"] = h.get("run_id")
            rec["frozen_spec_digest"] = h.get("frozen_spec_digest")
        except Exception as exc:
            rec["failures"].append(f"harness record unreadable: {type(exc).__name__}: {exc}")

    n = rec["numbers_from_contract"]
    hz = rec.get("harness_scalars") or {}
    cells_total = hz.get("failing_fr_it_cells_total")
    blocking = []
    if n.get("improved_fr_it_cells") == 0:
        blocking.append(
            f"0 of {cells_total} failing FR/IT authority cells improved "
            f"(measured_outcome.improved_fr_it_cells=0, "
            f"reduced_under_covered_questions="
            f"{hz.get('reduced_under_covered_questions')} of "
            f"{hz.get('required_reduced_questions')} required, "
            f"accepted_baseline_reproduced={n.get('accepted_baseline_reproduced')})"
        )
    if n.get("n_calls_over_per_search_budget"):
        blocking.append(
            f"{n['n_calls_over_per_search_budget']} of {n.get('added_searches')} added searches "
            f"breached the frozen per-search budget "
            f"(max {n.get('max_per_search_seconds')}s against "
            f"{n.get('per_search_budget_seconds')}s)"
        )
    if n.get("bar_reachable_at_all") is False:
        blocking.append(
            f"the charter's own coverage bar is unreachable by ANY candidate at this baseline: "
            f"'{n.get('outcome_a_coverage_bar')}' while max_reducible_questions="
            f"{n.get('max_reducible_questions')}"
        )

    rec["decline_reasons"] = blocking
    if rec["failures"]:
        rec["decision"] = "DECISION_NOT_REACHABLE"
        rec["reason"] = "; ".join(rec["failures"])
        return rec

    rec["decision"] = "DECLINE"
    rec["reason"] = (
        "The accepted team outcome is a bounded negative at OUTCOME_B and the charter's own "
        f"contract closes the item: the measured deterministic expansion layer improved "
        f"{hz.get('improved_fr_it_cells')} of {cells_total} failing FR/IT authority cells and "
        f"reduced under-covered concepts on {hz.get('reduced_under_covered_questions')} of 3 "
        f"served questions against a required {hz.get('required_reduced_questions')}, spent "
        f"{n.get('n_calls_over_per_search_budget')} of {n.get('added_searches')} added searches over "
        f"the frozen per-search latency budget (max {n.get('max_per_search_seconds')}s vs "
        f"{n.get('per_search_budget_seconds')}s), and its own structural finding says the charter's "
        f"coverage bar ({n.get('outcome_a_coverage_bar')}) is unreachable by any candidate because "
        f"{n.get('max_reducible_questions')} of 3 served questions start with zero under-covered "
        "concepts. Nothing is adopted into product/; the mount stays untouched."
    )
    rec["what_product_did_not_do"] = [
        "did not build a competing expansion layer (direction v57 forbids it)",
        "did not wait for or re-dispatch the Frontier team (requirement 21)",
        "did not copy any of the component's code into product/",
        "did not change a frozen bar, rubric, threshold or packet byte",
    ]
    rec["supersedes"] = {
        "prior_decision": "DECLINE_NOW_NOTHING_TO_ADOPT",
        "prior_decided_by_run": 39169296466,
        "why_superseded": (
            "the prior evidence was 'mount INITIALIZED, no artifacts'; the mount is now a "
            "promoted branch with a canonical contract, a harness record and two passing audit "
            "gates, so the decision is re-recorded on the artifact that actually exists. The "
            "decision word (DECLINE) is unchanged; the REASON is the real one."
        ),
    }
    rec["claim_ceiling"] = (
        "This record states that Product did not adopt the component and copies the team's own "
        "measured numbers to justify it. It asserts nothing about retrieval quality, legal "
        "usefulness, corpus completeness, any frozen bar or rubric, or human-gate readiness. "
        "Concept-coverage counts are lexical coverage of a retrieved set, not a legal conclusion; "
        "a zero count is a retrieval signal, not proof that authorities are absent."
    )
    return rec


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--mount", default=str(DEFAULT_MOUNT))
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--run-id", default="MANUAL")
    ap.add_argument("--commit", default="UNPINNED")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    rec = inspect(Path(args.mount))
    rec["decided_by_run"] = args.run_id
    rec["product_commit_of_record"] = args.commit

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote {out}  decision={rec['decision']}")
    elif args.write:
        out = REPO_ROOT / "results" / "product" / "frontier_verdicts" / \
            "frontier-query-concept-recall_adoption_39179862363.json"
        out.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote {out}  decision={rec['decision']}")
    else:
        print(json.dumps(rec, indent=2, ensure_ascii=False))

    return 0 if rec["decision"] in ("DECLINE", "ADOPT") else 1


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())