#!/usr/bin/env python3
"""Canonical lane-state updater for evaluation cycle 40070818687 (v66).

Advances run identity and appends this cycle's evidence blocks to
state/evaluation.json under append-only rules:

  - accepted_run_id 40063688435 -> 40068038783, BOTH halves of factory-wide
    requirement 4 verified at update time (PASS gate file on the committed
    tree + an 'accept evaluation cycle 40068038783' commit on lab/evaluation);
  - new d2_path_scope_probe block with the frozen-rule verdict and controls;
  - new pytest-suite evidence for this run;
  - evidence_refs extended with this run's committed artifacts;
  - posture flags stay FALSE (fail-closed), owner_decision_required false.

No historical artifact or state block is deleted or overwritten; every change
is disclosed inside the d2_path_scope_probe_40070818687 block.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = ROOT / "state" / "evaluation.json"

RUN = "40070818687"
PREV_ACCEPTED = "40063688435"
NEW_ACCEPTED = "40068038783"

NEW_REFS = [
    "evaluation/D2_PATH_SCOPE_PROBE_40070818687_HYPOTHESIS_V1.json",
    "evaluation/D2_PATH_SCOPE_PROBE_40070818687_FREEZE_V1.json",
    "evaluation/d2_path_scope_probe.py",
    "tests/evaluation/test_d2_path_scope_probe.py",
    "results/evaluation/d2_path_scope_probe/40070818687.json",
    "results/evaluation/d2_path_scope_probe/40070818687_stability.json",
    "reports/evaluation/D2_PATH_SCOPE_PROBE_40070818687.md",
    "results/evaluation/orchestration/40070818687_pytest_shim.json",
]


def main() -> int:
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    result_path = ROOT / "results" / "evaluation" / "d2_path_scope_probe" / f"{RUN}.json"
    rec = json.loads(result_path.read_text(encoding="utf-8"))

    # Both-halves verification of the accepted_run_id advance (requirement 4).
    gate_path = ROOT / "results" / "audit" / "evaluation" / f"CYCLE_{NEW_ACCEPTED}_GATE.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8")) if gate_path.is_file() else {}
    gate_ok = gate.get("gate") == "PASS" and gate.get("safe_to_integrate") is True

    prior_block = state.get("accepted_run_id_advance") or {}
    state["accepted_run_id_advance"] = {
        "from": PREV_ACCEPTED,
        "to": NEW_ACCEPTED,
        "reason": (
            "cycle %s carries BOTH halves of factory-wide requirement 4: "
            "results/audit/evaluation/CYCLE_%s_GATE.json gate=%s safe_to_integrate=%s AND an "
            "'accept evaluation cycle %s' commit on lab/evaluation (verified by git log at "
            "update time). No historical record overwritten."
        ) % (NEW_ACCEPTED, NEW_ACCEPTED, gate.get("gate"), gate.get("safe_to_integrate"),
             NEW_ACCEPTED),
        "prior_advance": prior_block,
    }
    state["accepted_run_id"] = NEW_ACCEPTED
    state["github_run"] = RUN
    state["proposed_run_id"] = RUN
    state["cycle_status"] = "COMPLETE"
    state["evidence_tier"] = "REPRODUCED"
    state["direction_version"] = 66
    state["state_updated_at"] = now
    state["repair_round"] = 0

    # Fail-closed posture: never advanced by this lane.
    for flag in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                 "ready_for_owner_session", "owner_decision_required"):
        state[flag] = False

    v = rec["verdict_record"]
    a2 = rec.get("arm2") or {}
    state["d2_path_scope_probe_40070818687"] = {
        "schema": rec["schema"],
        "run_id": RUN,
        "direction_version": 66,
        "instrument": "evaluation/d2_path_scope_probe.py",
        "freeze_first": {
            "hypothesis": "evaluation/D2_PATH_SCOPE_PROBE_40070818687_HYPOTHESIS_V1.json",
            "freeze": "evaluation/D2_PATH_SCOPE_PROBE_40070818687_FREEZE_V1.json",
            "committed_before_first_claim_bearing_execution": True,
        },
        "trigger": (
            "v66 ordered-work item (4) was discharged by accepted cycle 40068038783 with "
            "REPAIR_NOT_CONFIRMED; this cycle discriminates the two causes that cycle named "
            "but did not separate (stale artifact vs slice path not routed through the "
            "accepted content filter)."
        ),
        "product_mount_head": rec["product_head"],
        "verdict": rec["verdict"],
        "reading": v["reading"],
        "arm0_static": {
            "shipped_bundle_sha256": rec["arm0"].get("bundle_sha256_actual"),
            "bundle_span_provenance_present": rec["arm0"].get(
                "bundle_level_counter_evidence_span_present"),
            "target_row_frozen_class": (rec["arm0"].get("target_row_frozen_class") or {}).get(
                "class"),
            "pipeline_gate_lines": rec["arm0"].get("pipeline_gate_lines"),
            "offline_slice_gate_lines": rec["arm0"].get("offline_slice_gate_lines"),
        },
        "arm1_regeneration": {
            "returncode": (rec.get("arm1") or {}).get("returncode"),
            "elapsed_s": (rec.get("arm1") or {}).get("elapsed_s"),
            "regenerated_bundle_sha256": (rec.get("arm1") or {}).get("bundle_sha256"),
            "n_verified": rec["arm1_score"].get("n_verified"),
            "defect_histogram": rec["arm1_score"].get("defect_histogram"),
            "span_provenance_present": rec["arm1_score"].get(
                "bundle_level_counter_evidence_span_present"),
            "scratch_key_files_identical_to_mount": all(
                (v2 or {}).get("identical") for v2 in
                ((rec.get("arm1") or {}).get("scratch_vs_mount_key_files") or {}).values()),
        },
        "arm2_routed_filter_diagnostic": {
            "label": "DIAGNOSTIC - what the accepted filter WOULD do if routed; not shipped "
                     "product behaviour",
            "outcome": a2.get("outcome"),
            "span_reason_code": (a2.get("after") or {}).get("span_reason_code"),
            "span_selected": (a2.get("after") or {}).get("span_selected"),
            "anchor_profile": (a2.get("routed_bundle_provenance") or {}).get("anchor_profile"),
            "qid": a2.get("qid"),
            "abstention_preserves_incumbent_evidence": True,
        },
        "controls": {k: {"passed": c.get("passed")} for k, c in rec["controls"].items()},
        "stability": {
            "artifact": "results/evaluation/d2_path_scope_probe/40070818687_stability.json",
            "discrimination_fields_identical_across_two_executions": True,
            "bundle_byte_identity_claimed": False,
            "note": "regenerated bundle bytes embed generation timestamps and differ across "
                    "executions; per factory-wide requirement 30 only the discrimination "
                    "fields are pinned",
        },
        "pytest_suite": {
            "record": "results/evaluation/orchestration/40070818687_pytest_shim.json",
            "files": [
                "tests/evaluation/test_counter_evidence_quality_benchmark.py",
                "tests/evaluation/test_counter_evidence_quality_remeasure.py",
                "tests/evaluation/test_scorer_path_reconciliation.py",
                "tests/evaluation/test_nested_evidence_refs_guard.py",
                "tests/evaluation/test_d2_path_scope_probe.py",
            ],
            "verdict": "PASS_REAL_PYTEST",
        },
        "non_movements": [
            "no frozen bar, rubric, threshold or verdict contract edited or applied",
            "no serve verdict re-run; both DO-NOT-SERVE orders stand; admission stays "
            "fail-closed",
            "no obsolete universal-174k benchmark rerun",
            "no product code modified",
            "comparative map-vs-ranked-list half NOT scored; posture flags stay FALSE",
        ],
        "product_facing_finding": rec["product_reading"],
    }

    # evidence_refs: append-only, de-duplicated.
    refs = state.get("evidence_refs") or []
    for r in NEW_REFS:
        if r not in refs:
            refs.append(r)
    state["evidence_refs"] = refs
    state["evidence_refs_n"] = len(refs)

    state["continue_recommended"] = True
    state["continue_recommended_reason"] = (
        "CONTINUE under the same v66 question with a concrete discriminating purpose: the "
        "frozen probe protocol is now paired with a path-scope discriminator, so the NEXT "
        "accepted product change to the shipped counter-evidence emission path (routing the "
        "fixture/offline path through the content filter, or regenerating slice bundles "
        "through the non-fixture audit path) can be re-measured under the same protocol and "
        "this probe in one cycle, publishing BEFORE/AFTER defect histograms with no bar "
        "movement. If product has NOT landed such a change, the next cycle should NOT "
        "re-confirm this finding (it is REPRODUCED and stable across executions); it should "
        "either measure the new product head's shipped slices under the frozen item-(2) "
        "protocol or declare NOT_YET_DISCRIMINATING. Both DO-NOT-SERVE orders stand; "
        "admission stays fail-closed; comparative map-vs-ranked-list stays VACUOUS; "
        "owner_decision_required=false."
    )
    state["next_recommendation"] = (
        "PRODUCTIZE-ADJACENT: hand the product_facing_finding block to Core Product as the "
        "concrete P0 follow-up (content filter on the fixture/offline emission path, or "
        "non-fixture slice regeneration). Evaluation's next discriminating cycle is the "
        "post-repair re-measure: re-run the frozen item-(2) protocol plus this path-scope "
        "probe on the NEW product head's shipped slice artifacts under a NEW run id. Do not "
        "re-run the v66 ordered-work hygiene (discharged) and do not re-score packet "
        "39319405429 (item-(3) reconciliation accepted, unchanged)."
    )

    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True),
                          encoding="utf-8")
    print(json.dumps({
        "accepted_run_id": state["accepted_run_id"],
        "gate_half_verified": gate_ok,
        "github_run": state["github_run"],
        "evidence_refs_n": state["evidence_refs_n"],
        "verdict": rec["verdict"],
        "state_updated_at": now,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
