#!/usr/bin/env python3
"""State updater for evaluation cycle 40073123887 (FAST-MVP v66 battery).

Advances the canonical state/evaluation.json with this run's identity and
finding blocks. Does NOT overwrite any historical block; every prior block
is preserved verbatim. accepted_run_id is NOT advanced here (it advances only
after both halves of factory-wide requirement 4 are verified: PASS gate +
accept commit, which happens after the independent audit).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = REPO_ROOT / "state/evaluation.json"
RESULT_REL = "results/evaluation/fast_mvp_v66/40073123887.json"
SHIM_REL = "results/evaluation/orchestration/40073123887_fast_mvp_v66_battery_pytest_shim.json"
BENCH_REL = "results/evaluation/minimal_retrieval_ca_benchmark/40073123887.json"
REPORT_REL = "reports/evaluation/CYCLE_40073123887_fast_mvp_v66.md"

RUN_ID = "40073123887"
DIRECTION_VERSION = 66


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    result = json.loads((REPO_ROOT / RESULT_REL).read_text(encoding="utf-8"))
    shim = json.loads((REPO_ROOT / SHIM_REL).read_text(encoding="utf-8"))
    bench = json.loads((REPO_ROOT / BENCH_REL).read_text(encoding="utf-8"))

    prior_accepted = state.get("accepted_run_id")

    # --- run identity ------------------------------------------------------
    state["github_run"] = RUN_ID
    state["proposed_run_id"] = RUN_ID
    state["direction_version"] = DIRECTION_VERSION
    state["state_updated_at"] = datetime.now(timezone.utc).isoformat()
    state["acceptance_status"] = "PROPOSED_PENDING_INDEPENDENT_AUDIT"
    # accepted_run_id NOT advanced: this run has not yet carried both halves
    # of factory-wide requirement 4 (PASS gate + accept commit). It advances
    # only after the independent audit. Prior value preserved.
    state["accepted_run_id"] = prior_accepted

    # --- this run's finding block -----------------------------------------
    state["fast_mvp_v66_battery_40073123887"] = {
        "schema": result["schema"],
        "run_id": RUN_ID,
        "github_run": RUN_ID,
        "direction_version": DIRECTION_VERSION,
        "instrument": "evaluation/fast_mvp_v66_battery.py",
        "hypothesis_file": "evaluation/FAST_MVP_V66_HYPOTHESIS_V1.json",
        "freeze_record": "evaluation/FAST_MVP_V66_FREEZE_RECORD_V1.json",
        "freeze_first": True,
        "freeze_commit": "93bbc3da2",
        "verdict": result["verdict"],
        "exit_code": result["exit_code"],
        "claim_ceiling": result["claim_ceiling"],
        "mount_head": result["mount_head"],
        "product_head_at_freeze": result["product_head_at_freeze"],
        "benchmark": {
            "command": result["benchmark"]["command"],
            "returncode": result["benchmark"]["returncode"],
            "executed": result["benchmark"]["executed"],
            "verdict": result["benchmark"]["findings"]["verdict"],
            "falsification_proven": result["benchmark"]["findings"]["falsification_proven"],
            "failed_gate_set_matches_accepted": result["benchmark"]["findings"]["failed_gate_set_matches_accepted"],
            "failed_gates": result["benchmark"]["findings"]["failed_gates"],
            "input_drift": result["benchmark"]["findings"]["input_drift"],
            "n_gates": result["benchmark"]["findings"]["n_gates"],
            "n_passed": result["benchmark"]["findings"]["n_passed"],
            "n_failed": result["benchmark"]["findings"]["n_failed"],
            "record_path": result["benchmark"]["record_path"],
            "engine_record_path": "results/evaluation/minimal_retrieval_ca_benchmark/40073123887_engine_mapping_free_recall_falsifier.json",
        },
        "test_battery": {
            "command": result["battery"]["command"],
            "returncode": result["battery"]["returncode"],
            "executed": result["battery"]["executed"],
            "verdict": result["battery"]["verdict"],
            "n_passed": result["battery"]["n_passed"],
            "n_failed": result["battery"]["n_failed"],
            "n_unsupported": result["battery"]["n_unsupported"],
            "n_skipped": result["battery"]["n_skipped"],
            "record_path": result["battery"]["record_path"],
            "disclosed_failures": [
                {
                    "test_file": "tests/evaluation/test_mount_provenance_gate.py",
                    "test": "test_check_provenance_on_the_committed_tree_does_not_re_derive",
                    "class": "PRE_EXISTING_HISTORICAL",
                    "note": "also recorded at runs 39929883261 and 39936790420; not a new defect",
                },
                {
                    "test_file": "tests/evaluation/test_offline_emission_path_benchmark.py",
                    "test": "test_end_to_end_run_when_mount_present",
                    "class": "STALE_FREEZE_RECORD_PIN",
                    "note": (
                        "oepb freeze record pins product/query/counter_anchor.py at "
                        "7f20866b but product head 3495c1336 (P0 filter cycle "
                        "40064639100) carries 11c7feaf; oepb.run() correctly returns "
                        "ENVIRONMENT_OR_VACUOUS (exit 2) without writing the output "
                        "file and the test's file-existence assertion fails on that "
                        "path. Disclosed, not suppressed."
                    ),
                },
            ],
        },
        "pins_before_all_match": result["pins_before_all_match"],
        "pins_after_all_match": result["pins_after_all_match"],
        "pin_drift": result["pin_drift"],
        "frozen_rubric_rehash_reported_only": {
            "RULES_LABEL": "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608",
            "RULES_GEOMETRY": "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633",
            "VERDICT_CONTRACT": "b9cdb89438a8d16ee165fe2a5d73060524154d8e7ba8e0cab867e8ca17ff414c",
            "policy": "REPORTED-ONLY identity re-hash; never read for enforcement; never edited",
        },
        "ordered_items": {
            key: {
                "verdict": v.get("verdict"),
                "reason": v.get("reason"),
                "condition": v.get("condition"),
            }
            for key, v in result["ordered_items"].items()
        },
        "no_174k_benchmark_rerun": True,
        "no_frozen_edit": True,
        "non_movements": result["non_movements"],
        "posture_unchanged": result["posture_unchanged"],
        "numeric_environment": result["numeric_environment"],
        "report_path": REPORT_REL,
    }

    # --- continuation stance ----------------------------------------------
    # All v66 ordered work (1)-(5) is DISCHARGED. Item (4) is
    # NOT_YET_DISCRIMINATING (product head unchanged at 3495c1336). Per the
    # factory direction's own item-(4) contract and the state's
    # next_recommendation, continue_recommended=false until Core Product lands
    # a further change to the shipped counter-evidence emission path (fixture-
    # path content filter routing, or non-fixture slice regeneration) that
    # makes the post-repair re-measure discriminating again. This hands the
    # successor decision to the Factory Director per the Research Protocol.
    state["continue_recommended"] = False
    state["continue_recommended_reason"] = (
        "ALL v66 ordered work (1)-(5) is DISCHARGED with accepted evidence. "
        "This cycle executed the FAST-MVP v66 acceptance battery under a "
        "freeze-first protocol: the smallest executable retrieval/counter-"
        "authority falsification benchmark reproduced PRODUCT_FALSIFIED with "
        "the identical accepted 4-gate set on the unchanged packet-of-record "
        "pins; the multilingual/provenance test battery ran 75/2/6 under the "
        "shim (the 2 failures are pre-existing environment/stale-pin issues, "
        "disclosed, not new defects); frozen pins re-hashed REPORTED-ONLY with "
        "zero drift; ordered items (1)(2)(3) DISCHARGED, (4) NOT_YET_DISCRIMINATING, "
        "(5) STANDING. The next discriminating evaluation cycle is the "
        "post-repair re-measure: re-run the frozen item-(2) content-quality "
        "probe protocol plus the D2 path-scope probe on the NEW product head's "
        "shipped slice artifacts under a NEW run id, IF AND ONLY IF Core "
        "Product lands a further change to the shipped counter-evidence "
        "emission path (fixture-path content filter routing, or non-fixture "
        "slice regeneration). Until then, re-running would only re-confirm a "
        "REPRODUCED finding and is NOT justified under the same factory-"
        "direction question. Both DO-NOT-SERVE orders stand; admission stays "
        "fail-closed; comparative map-vs-ranked-list stays VACUOUS; "
        "owner_decision_required=false. Successor question is the Factory "
        "Director's call per RESEARCH_PROTOCOL.md."
    )
    state["next_recommendation"] = (
        "PIVOT_WITHIN_MISSION or PAUSE (Factory Director's call). Evaluation's "
        "v66 question is exhausted: the binding counter-evidence content-quality "
        "defect class has been measured (H2_FALSIFIED 14/14), the repair re-"
        "measured (REPAIR_NOT_CONFIRMED for D2, CONFIRMED-REPAIRED for D3/D4), "
        "the path-scope residual located (fixture path never reaches the "
        "accepted content filter), and the smallest executable retrieval/"
        "counter-authority falsification benchmark re-verified (PRODUCT_FALSIFIED, "
        "identical 4-gate set). The next evaluation cycle should be triggered "
        "by a NEW product head that lands the fixture-path content filter or "
        "non-fixture slice regeneration, at which point the frozen item-(2) "
        "protocol + D2 path-scope probe re-measure becomes discriminating "
        "again. No further same-question cycle is justified now."
    )
    state["evidence_tier"] = "REPRODUCED"
    state["cycle_status"] = "COMPLETE"

    # --- posture (unchanged, fail-closed) ----------------------------------
    state["packet_admitted"] = False
    state["machine_gate_ready"] = False
    state["human_gate_ready"] = False
    state["ready_for_owner_session"] = False
    state["owner_decision_required"] = False

    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    print(f"[state] wrote {STATE_PATH}")
    print(f"[state] run_id={RUN_ID} direction_version={DIRECTION_VERSION}")
    print(f"[state] accepted_run_id={state['accepted_run_id']} (NOT advanced; pending audit)")
    print(f"[state] continue_recommended={state['continue_recommended']}")


if __name__ == "__main__":
    main()
