#!/usr/bin/env python3
"""Additive state update for evaluation run 46114243630.

Preserves every pre-existing key/value, appends evidence refs, advances only
the current-run pointers, and does NOT advance accepted_run_id (no audit gate
exists for this run).  Writes only state/evaluation.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
RUN = "46114243630"
SUBJECT = "46110768588"
STATE = REPO / "state/evaluation.json"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def uniq(seq: list[str]) -> list[str]:
    return list(dict.fromkeys(seq))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.parse_args(argv)
    before = json.loads(STATE.read_text(encoding="utf-8"))
    snapshot = json.dumps(before, sort_keys=True)
    original_keys = set(before)
    original_refs = list(before.get("evidence_refs") or [])

    paths = [
        f"evaluation/FROZEN_RULES_PROFILE_COVERAGE_{RUN}_HYPOTHESIS_V1.json",
        f"evaluation/FROZEN_RULES_PROFILE_COVERAGE_{RUN}_FREEZE_V1.json",
        f"evaluation/operational_resume_{RUN}_diagnosis.py",
        f"evaluation/operational_resume_{RUN}_freeze.py",
        f"evaluation/operational_resume_{RUN}_report.py",
        f"results/evaluation/orchestration/CYCLE_{SUBJECT}_resume_diagnosis.json",
        f"results/evaluation/orchestration/CYCLE_{SUBJECT}_jobs.json",
        f"results/evaluation/orchestration/CYCLE_{SUBJECT}_run.json",
        f"results/evaluation/orchestration/CYCLE_{SUBJECT}_team_annotations.json",
        f"results/evaluation/frozen_rules_profile_coverage/{RUN}.json",
        f"results/evaluation/frozen_rules_profile_coverage/{RUN}_REPRO.json",
        f"results/evaluation/frozen_rules_profile_coverage/{RUN}_REPRO_CHECK.json",
        f"results/evaluation/orchestration/{RUN}_retrieval_benchmark_shim.json",
        f"results/evaluation/orchestration/{RUN}_reused_suites_shim.json",
        f"results/evaluation/orchestration/{RUN}_audit_readiness_manifest.json",
        f"reports/evaluation/FROZEN_RULES_PROFILE_COVERAGE_{RUN}.md",
    ]
    missing = [p for p in paths if not (REPO / p).is_file()]
    if missing:
        raise SystemExit(f"cannot update state; refs do not resolve: {missing}")
    digests = {p: sha(REPO / p) for p in paths}

    before["evidence_refs"] = uniq(original_refs + paths)
    before["evidence_refs_n"] = len(before["evidence_refs"])
    before["github_run"] = RUN
    before["proposed_run_id"] = RUN
    before["current_cycle_audit_status"] = "PENDING_INDEPENDENT_AUDIT"
    before["audit_status"] = "PENDING_INDEPENDENT_AUDIT"
    before["cycle_status"] = "COMPLETE"
    before["accepted_run_id"] = before["accepted_run_id"]  # unchanged, no gate
    before["evidence_tier"] = before["evidence_tier"]  # accepted state unchanged
    before["continue_recommended"] = False
    before["human_gate_ready"] = False
    before["machine_gate_ready"] = False
    before["owner_decision_required"] = False
    before["packet_admitted"] = False
    before["no_network_calls"] = False

    before[f"operational_resume_{RUN}"] = {
        "schema": "lex-evaluation-operational-resume/1",
        "run": RUN,
        "run_under_resume": SUBJECT,
        "direction_version": 68,
        "base_snapshot_commit": "752c3efe335ee847f50961a2230fa7c94a19a574",
        "failure_class": "LEX_WORK_QUANTUM_EXPIRED",
        "failure_summary": (
            "GitHub REST: team job step 'Run lane cycle' failed rc=78 with "
            "LEX_WORK_QUANTUM_EXPIRED seconds=2700; steps 7/9 skipped; audit and "
            "integrate skipped; no audit branch and no gate for the subject run."),
        "producer_work_preserved": True,
        "instrument_sha256": digests[
            "evaluation/frozen_rules_profile_coverage_falsifier.py"] if (
            "evaluation/frozen_rules_profile_coverage_falsifier.py" in digests
        ) else sha(REPO / "evaluation/frozen_rules_profile_coverage_falsifier.py"),
        "freeze_before_first_execution": True,
        "audit_status": "PENDING_INDEPENDENT_AUDIT",
        "accepted_as_evidence": False,
        "artifact_sha256": digests,
    }
    before[f"frozen_rules_profile_coverage_{RUN}"] = {
        "schema": "lex-evaluation-profile-coverage-result/1",
        "run_id": RUN,
        "claim_bearing_run": RUN,
        "audit_status": "PENDING_INDEPENDENT_AUDIT",
        "accepted_as_evidence": False,
        "direction_version": 68,
        "hypothesis_sha256": sha(REPO / paths[0]),
        "freeze_sha256": sha(REPO / paths[1]),
        "result": paths[9],
        "result_sha256": digests[paths[9]],
        "instrument": "evaluation/frozen_rules_profile_coverage_falsifier.py",
        "instrument_sha256": sha(
            REPO / "evaluation/frozen_rules_profile_coverage_falsifier.py"),
        "verdict": "PROFILE_COVERAGE_FALSIFIED",
        "exit_code": 1,
        "falsified_legs": ["H1_profile_coverage", "H2a_profile_norm_alignment"],
        "controls_all_hold": True,
        "n_bundles": 49,
        "h1_failing_groups": ["petty-theft-dismissal.bundle"],
        "h2a_failing_groups": ["business-judgment-rule.bundle", "served"],
        "h3_disagreements": 0,
        "reproduced_across_processes": True,
        "claim_ceiling": (
            "Shipped anchor-profile coverage / norm alignment / provenance "
            "agreement on committed bytes only; no frozen bar, no serve verdict, "
            "no decision labels, no live recall, no 174k benchmark."),
    }
    before["next_recommendation"] = (
        f"CURRENT RUN {RUN} (operational resume of {SUBJECT}): the persisted "
        "producer snapshot 752c3efe is preserved byte-identically (single added "
        "instrument evaluation/frozen_rules_profile_coverage_falsifier.py, "
        "sha256 3583be0c). The subject run failed at rc-78 "
        "LEX_WORK_QUANTUM_EXPIRED seconds=2700 after committing the instrument, "
        "so no freeze, result, state or audit gate existed; this resume wrote "
        "freeze-first records BEFORE first claim-bearing execution (49 population "
        "pins), executed the unmodified instrument, and recorded "
        "PROFILE_COVERAGE_FALSIFIED (exit 1), H1 failing on petty-theft-dismissal "
        "(no frozen profile) and H2a failing on business-judgment-rule (wrong "
        "fr-bail-entretien profile, no shared Art. norm) and served, with all 7 "
        "controls holding, H3 zero disagreements, and an independent second "
        "process reproducing all 18 claim-bearing fields. This closes the "
        "coverage question TRANSFERRED by Core Product (state/product.json item 6) "
        "as an accepted-pending-audit NEGATIVE on the current accepted bytes; it "
        "does not close any frozen bar, lift either DO-NOT-SERVE order or advance "
        "accepted_run_id. continue_recommended=false: no further SAME-question "
        "evaluation cycle is discriminating until Product repairs the resolver "
        "and regenerates the flagship family, at which point a NEW pre-registered "
        "re-measure on NEW bytes is the correct successor. Reused multilingual/"
        "provenance suite passed under the documented shim with protocol digest "
        "e1a0b18d unchanged. PENDING_INDEPENDENT_AUDIT; "
        "human_gate_ready=false; machine_gate_ready=false; "
        "owner_decision_required=false; packet_admitted=false; "
        "no universal-174k benchmark."
    )

    # Verify additive discipline before writing.
    after_keys = set(before)
    removed = sorted(original_keys - after_keys)
    unchanged = sorted(
        k for k in original_keys & after_keys
        if k not in {"evidence_refs", "evidence_refs_n", "github_run",
                     "proposed_run_id", "audit_status",
                     "current_cycle_audit_status", "cycle_status",
                     "continue_recommended", "human_gate_ready",
                     "machine_gate_ready", "owner_decision_required",
                     "packet_admitted", "no_network_calls", "next_recommendation"}
        and json.dumps(before[k], sort_keys=True) != json.dumps(
            json.loads(snapshot)[k], sort_keys=True)
    )
    if removed or unchanged:
        raise SystemExit(f"non-additive state change: removed={removed} changed={unchanged}")
    new_refs = [r for r in paths if r not in original_refs]
    if not set(paths).issubset(set(before["evidence_refs"])):
        raise SystemExit("evidence refs not fully appended")
    before.setdefault("state_update_provenance", {})[RUN] = {
        "additive_only": True,
        "keys_before": len(original_keys),
        "keys_after": len(after_keys),
        "evidence_refs_before": len(original_refs),
        "evidence_refs_after": len(before["evidence_refs"]),
        "new_refs_added": len(new_refs),
        "accepted_run_id_unchanged": True,
        "no_key_removed": True,
        "no_existing_ref_removed": True,
    }
    STATE.write_text(json.dumps(before, indent=2, sort_keys=True) + "\n",
                     encoding="utf-8")
    print(json.dumps({
        "state": str(STATE), "sha256": sha(STATE),
        "keys_before": len(original_keys), "keys_after": len(after_keys),
        "refs_before": len(original_refs),
        "refs_after": len(before["evidence_refs"]),
        "accepted_run_id": before["accepted_run_id"],
        "continue_recommended": before["continue_recommended"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
