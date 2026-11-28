#!/usr/bin/env python3
"""Deterministic state update for evaluation cycle 46128771785.

Only state/evaluation.json is modified. The cycle is an operational
discrimination gate, so accepted_run_id is NOT advanced and no evidence tier is
upgraded; this script refuses to run twice by checking the proposed run id.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
STATE = REPO_ROOT / "state/evaluation.json"
RUN_ID = "46128771785"

NEW_REFS = [
    "evaluation/v68_discrimination_gate.py",
    "tests/evaluation/test_v68_discrimination_gate.py",
    "results/evaluation/v68_discrimination_gate/46128771785.json",
    "results/evaluation/v68_discrimination_gate/46128771785_gate_test_shim.json",
    "reports/evaluation/CYCLE_46128771785.md",
]

NEXT_RECOMMENDATION = (
    "CYCLE 46128771785 (direction v68, evaluation, FAST MVP MODE): OPERATIONAL "
    "DISCRIMINATION_GATE, NOT evidence. A compact executable instrument "
    "(evaluation/v68_discrimination_gate.py, sha 47d174d6) re-checked, from "
    "committed git objects at origin/lab/product (never from the mount or state "
    "prose), whether either v68 re-open condition holds. Product head advanced "
    "5fb312e4 -> 7be4480e (accept 40284658455; both halves of requirement 4 "
    "verified: CYCLE_40284658455_GATE.json gate=PASS safe_to_integrate=true "
    "required_fixes=[] and HEAD subject 'accept product cycle 40284658455'), but "
    "product/query/{retrieval,qmap,relevance,pipeline,counter_evidence_span}.py "
    "git blobs are byte-identical, so retrieval_reranking_code_changed=false; the "
    "FROZEN precondition_gate reused from accepted "
    "evaluation/post_repair_family_ca_falsifier.py gives H1=true, H2=false and "
    "member-for-member family matching 14/15 (offline/rent-default 11, "
    "server/served 3 of 4, parity false), so the family was not regenerated. "
    "VERDICT NOT_YET_DISCRIMINATING: no frozen bench re-run, no packet scored, no "
    "bar moved, no synthetic stand-in, no network retrieval/model/paid-API call, "
    "no 174k rerun. Frozen retrieval-recall pins re-hashed and matched "
    "(hypothesis a9fe256c, amendments ce1a481d/13f2eca1, spec 187b0e54, protocol "
    "e1a0b18d); nine standing claim-bearing records resolve; reused "
    "multilingual/provenance suite tests/evaluation/test_retrieval_benchmark.py "
    "SHIM_PASS 2/2 with the frozen protocol digest e1a0b18d reproduced, recall "
    "suite SHIM_PASS 7/7, 0 failed/0 unsupported, test files unedited; product "
    "and frontier packages plus 202 offline OCL fixture envelopes materialised "
    "from git into a temp dir only. Environment numpy 2.5.5/scipy 1.18.1/"
    "sklearn 1.9.1 (installed this cycle), no BLAS/thread pin, no cross-machine "
    "byte-identity claim. ORDERED WORK: (1) DISCHARGED and NOT re-run - the "
    "accepted correction of record (reports/evaluation/"
    "BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md, result "
    "40113448025, accepted cycle 40133253347) is restated in the report: "
    "pipeline.py:1339/1343 span seam, bundle sha256 6eee1149, applied=true, "
    "n_selected=0, pivot_absent abstention on gr_gerichte_ERZ 2010 25, defective "
    "incumbent still verified, 4/5 unchanged; (2) NOT_YET_DISCRIMINATING; (3) "
    "standing PRODUCT_FALSIFIED record on packet-of-record 39319405429 KEPT; (4) "
    "three non-blocking CYCLE_39965089504_GATE.json fixes reported verbatim, not "
    "silently; (5) no re-derivation. Provenance disclosure: run 40261335674 is "
    "PENDING_INDEPENDENT_AUDIT and is NOT accepted evidence; this cycle does not "
    "re-adjudicate accept commit ea98384e (40265377500, gate PASS) and does NOT "
    "advance accepted_run_id. continue_recommended=false: no further "
    "same-question cycle until Core Product changes retrieval/reranking code or "
    "brings the frozen family to 15/15; re-running this gate on unchanged bytes "
    "would itself be operational. Both DO-NOT-SERVE orders stand; "
    "packet_admitted=false; machine_gate_ready=false; human_gate_ready=false; "
    "ready_for_owner_session=false; owner_decision_required=false. "
    "PENDING_INDEPENDENT_AUDIT; accepted_as_evidence=false."
)


def main() -> None:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    if str(state.get("proposed_run_id")) == RUN_ID:
        raise SystemExit("state already updated for this run; refusing to rewrite")
    refs = list(state.get("evidence_refs") or [])
    for ref in NEW_REFS:
        if not (STATE.parent.parent / ref).exists():
            raise SystemExit(f"missing evidence artifact: {ref}")
        if ref not in refs:
            refs.append(ref)
    state["evidence_refs"] = refs
    state["evidence_refs_n"] = len(refs)
    state["direction_version"] = 68
    state["cycle_status"] = "COMPLETE"
    state["evidence_tier"] = "ACCEPTED"
    state["continue_recommended"] = False
    state["proposed_run_id"] = RUN_ID
    state["github_run"] = RUN_ID
    state["audit_status"] = "PENDING_INDEPENDENT_AUDIT"
    state["current_cycle_audit_status"] = "PENDING_INDEPENDENT_AUDIT"
    state["accepted_as_evidence"] = False
    state["next_recommendation"] = NEXT_RECOMMENDATION
    state["v68_discrimination_gate_46128771785"] = {
        "role": "OPERATIONAL_DISCRIMINATION_GATE_NOT_EVIDENCE",
        "verdict": "NOT_YET_DISCRIMINATING",
        "product_head": "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83",
        "product_accepted_cycle": "40284658455",
        "product_requirement4_both_halves": True,
        "retrieval_reranking_code_changed": False,
        "family_matched": 14,
        "family_of": 15,
        "H2_precondition_full_family_regenerated": False,
        "frozen_pins_all_match": True,
        "standing_records_all_resolve": True,
        "reused_tests_shim_pass": True,
        "frozen_benchmark_rerun": False,
        "no_bar_edit": True,
        "no_174k_rerun": True,
        "result": "results/evaluation/v68_discrimination_gate/46128771785.json",
        "result_sha256": "2053be2ece43f7007861f17015bde0c189482808590c7831b14a4463c256fbae",
    }
    state["pin_drift_disclosure_46128771785"] = (
        "direction_version pin was already 68 at the accepted head; the v67 -> "
        "v68 advance is applied under this lane's disclosed convention and is "
        "not a defect or a frozen edit")
    state["provenance_disclosure_46128771785"] = (
        "accepted_run_id stays 40258497460. Run 40261335674 is "
        "PENDING_INDEPENDENT_AUDIT (no accept commit) and is not accepted "
        "evidence. Accept commit ea98384e (40265377500, gate PASS) is not "
        "re-adjudicated by this operational cycle.")
    state["human_gate_ready"] = False
    state["machine_gate_ready"] = False
    state["owner_decision_required"] = False
    STATE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    print(f"state updated: proposed_run_id={state['proposed_run_id']} "
          f"accepted_run_id={state['accepted_run_id']} "
          f"evidence_refs_n={state['evidence_refs_n']}")


if __name__ == "__main__":
    main()
