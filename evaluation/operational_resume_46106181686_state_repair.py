#!/usr/bin/env python3
"""Append-only state repair for operational resume run 46106181686.

Repairs exactly two pre-existing state-integrity defects and records this
resume under a new key. No historical claim-bearing key is rewritten.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RUN = 46106181686
SUBJECT = 46100599319
NEW_REFS = [
    "evaluation/OPERATIONAL_RESUME_46106181686_HYPOTHESIS_V1.json",
    "evaluation/OPERATIONAL_RESUME_46106181686_FREEZE_V1.json",
    "evaluation/operational_resume_46106181686.py",
    "results/evaluation/operational_resume_46106181686/api/run_46100599319_api.json",
    "results/evaluation/operational_resume_46106181686/api/jobs_46100599319_api.json",
    "results/evaluation/operational_resume_46106181686/diagnosis_46100599319.json",
    "results/evaluation/operational_resume_46106181686/deliverable_verification_46100599319.json",
    "results/evaluation/operational_resume_46106181686/state_integrity_gate_46106181686_pre.json",
    "reports/evaluation/OPERATIONAL_RESUME_46100599319_AUDIT_READY.md",
]


def main() -> None:
    root_path = REPO / "state" / "evaluation.json"
    lane_path = REPO / "evaluation" / "state" / "evaluation.json"
    root = json.loads(root_path.read_text(encoding="utf-8"))
    lane = json.loads(lane_path.read_text(encoding="utf-8"))

    # preserve the superseded next_recommendation verbatim, then append refs
    root.setdefault("prior_next_recommendation_46100599319", root["next_recommendation"])
    for st in (root, lane):
        refs = st.setdefault("evidence_refs", [])
        for ref in NEW_REFS:
            if ref not in refs:
                refs.append(ref)
        assert all((REPO / r).is_file() for r in refs), "unresolved evidence ref"
        st["evidence_refs_n"] = len(refs)
        # defect (b): root and lane run identity must agree
        st["github_run"] = RUN
        st["proposed_run_id"] = RUN

    # historical annotation: a pre-existing nested ref resolves to no in-tree
    # file. Disclose it through the guard's own known_unresolvable mechanism;
    # never create or edit an audit-namespace gate to make it resolve.
    hist_ref = "results/audit/evaluation/CYCLE_40246705199_GATE.json"
    root["known_unresolvable"] = [hist_ref]
    root["known_unresolvable_disclosure"] = {
        "first_disclosed_in_run": RUN,
        "why": "Historical producer-authored gate cited in github_run_advance_40246705199.required_fixes_source with an explicit mounted-copy annotation; no in-tree copy exists and none may be fabricated by this lane. Preserved verbatim, disclosed through the guard's own known-unresolvable mechanism, never deleted.",
        "resolution_policy": "disclose only; an independent auditor may supply provenance, a producer may not",
    }

    block = {
        "schema": "lex-evaluation-operational-resume/1",
        "lane": "evaluation", "direction_version": 68,
        "resume_run_id": RUN, "run_under_resume": SUBJECT,
        "claim_bearing_run": RUN,
        "producer_snapshot_commit": "39784cc02d5eb06915cab32bfc5e2647631de74a",
        "audit_status": "PENDING_INDEPENDENT_AUDIT",
        "pending_independent_audit": True,
        "accepted_as_evidence": False,
        "evidence_tier": "EXPLORATORY",
        "cycle_status": "COMPLETE",
        "producer_work_preserved": True,
        "mode": "FAST_MVP_OPERATIONAL_RESUME",
        "hypothesis": {"path": "evaluation/OPERATIONAL_RESUME_46106181686_HYPOTHESIS_V1.json",
                       "sha256": "3aec009f8d2a592483af51ce7dc188df7e796fa81f8666e1d7caff683f765563"},
        "freeze_record": {"path": "evaluation/OPERATIONAL_RESUME_46106181686_FREEZE_V1.json"},
        "instrument": "evaluation/operational_resume_46106181686.py",
        "diagnosis_record": "results/evaluation/operational_resume_46106181686/diagnosis_46100599319.json",
        "deliverable_verification_record": "results/evaluation/operational_resume_46106181686/deliverable_verification_46100599319.json",
        "api_envelopes": [
            "results/evaluation/operational_resume_46106181686/api/run_46100599319_api.json",
            "results/evaluation/operational_resume_46106181686/api/jobs_46100599319_api.json",
        ],
        "verdicts": {
            "orchestration": "AUDIT_AGENT_STEP_FAILURE_NOT_A_VERDICT",
            "deliverable": "DELIVERABLE_VERIFIED",
            "state_integrity_gate_before_repair": "AT_LEAST_ONE_CHECK_FAILED (evidence_refs_n_matches@state/evaluation.json; root_lane_parity@both)",
            "audit_readiness": "recorded in results/evaluation/operational_resume_46106181686/audit_readiness_46106181686.json",
        },
        "repairs": [
            "evidence_refs_n corrected to len(evidence_refs) in both state files; every ref is an existing file",
            "github_run and proposed_run_id synchronized to 46106181686 in both state files",
        ],
        "network_calls_this_resume": {
            "no_network_calls": False,
            "calls": ["unauthenticated public GitHub REST API GET for run 46100599319 and its jobs (orchestration provenance only)"],
            "scope": "no OpenCaseLaw, retrieval, model or paid-API call; no benchmark re-execution",
        },
        "no_frozen_edit": True,
        "no_benchmark_rerun": True,
        "no_174k_rerun": True,
        "no_audit_namespace_write": True,
        "posture": {
            "accepted_run_id": 40258497460,
            "direction_version": 68,
            "continue_recommended": False,
            "packet_admitted": False,
            "machine_gate_ready": False,
            "human_gate_ready": False,
            "ready_for_owner_session": False,
            "owner_decision_required": False,
            "do_not_serve_orders": "both stand",
        },
        "report": "reports/evaluation/OPERATIONAL_RESUME_46100599319_AUDIT_READY.md",
        "claim_ceiling": "Operational only: orchestration diagnosis, committed-byte deliverable verification and state-integrity repair of the persisted snapshot. No new measurement, no product re-score, no frozen edit, no serve verdict and no claim promotion.",
        "next_recommendation": "Audit-ready pending independent audit. The 46100599319 deliverable is verified as complete and pinned; its audit died in the agent step (no gate, no auditor commit). Both state-integrity defects are repaired. No same-question cycle: item (2) remains NOT_YET_DISCRIMINATING until Core Product changes the reranker or regenerates the 15th frozen-family member; the PRODUCT_FALSIFIED_RECALL_LOSS defect stays handed to Core Product.",
    }
    for st in (root, lane):
        st[f"operational_resume_{RUN}"] = block
        st["audit_status"] = "PENDING_INDEPENDENT_AUDIT"
    root["current_cycle_run_id"] = RUN
    root["resumed_run_id"] = SUBJECT
    root["prior_resumed_run_id_46100599319"] = 40232590665
    root["next_recommendation"] = block["next_recommendation"]
    lane["next_recommendation"] = block["next_recommendation"]

    for path, st in ((root_path, root), (lane_path, lane)):
        path.write_text(json.dumps(st, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "root_refs_n": root["evidence_refs_n"], "lane_refs_n": lane["evidence_refs_n"],
        "root_github_run": root["github_run"], "lane_github_run": lane["github_run"],
        "new_block": f"operational_resume_{RUN}",
    }, indent=2))


if __name__ == "__main__":
    main()
