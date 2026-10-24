#!/usr/bin/env python3
"""Operational-resume state repair for run 40089391202 (producer snapshot 40085602229).

Repairs, disclosed and append-only:

  R1  The producer's 8 top-level evidence_refs named local_eval_20261024T102833Z
      exist nowhere (actual committed artifacts are local_eval_20261024T102500Z
      for minimal_ret_ca / counter_evidence_quality / current_head_slice_quality
      and local_eval_1792837481 for d2_path_scope_probe). Verified by
      evaluation/nested_evidence_refs_guard.py: 9 unresolved, 8 top-level, the
      9th (repair_round1_40017649220.audit_gate) is INHERITED from the accepted
      lab-tip state and not charged to the producer. Refs are corrected BY NAME
      to the real committed paths; nothing is deleted.
  R2  github_run carried the same phantom string local_eval_20261024T102833Z;
      set to 40089391202 (this operational-resume run, which owns the v67
      item-(1) profile artifact committed alongside).
  R3  Two duplicate evidence_refs entries (evaluation/measure_current_head_slices.py,
      tests/evaluation/test_measure_current_head_slices.py) de-duplicated;
      first occurrence preserved.
  R4  The producer's minimal_ret_ca_benchmark_latest block measured the served-
      lineage packet 38839347028 (benchmark instrument-regression validation)
      without a requirement-39 label; a stale-packet labelling note is added.
      The measurement itself is preserved unchanged.
  R5  v67 ordered work item (1) is EXECUTED by this run: the D2 letterhead
      pattern heterogeneity profile (run 40089391202) is added as
      d2_letterhead_pattern_profile_latest with its committed artifacts appended
      to evidence_refs. accepted_run_id advances 40068038783 -> 40084716045
      under the established disclosure chain (both halves of factory-wide
      requirement 4 verified for 40082514143, 40083917238, 40084716045).
  R6  continue_recommended stays false with the fuller reason: the v67 ordered
      work is now FULLY discharged (item (1) executed this run; item (2)
      NOT_YET_DISCRIMINATING because product head e2270c37, accept 40080810801,
      has not landed the fixture-path content-filter repair; items (3)/(4)
      standing/report-only). The next discriminating evaluation cycle requires
      a NEW product head with the repair landed.

No historical measurement artifact is overwritten; every repair is named here.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
STATE = _REPO_ROOT / "state" / "evaluation.json"

PHANTOM_FIX = {
    "results/evaluation/minimal_ret_ca_benchmark/local_eval_20261024T102833Z.json":
        "results/evaluation/minimal_ret_ca_benchmark/local_eval_20261024T102500Z.json",
    "reports/evaluation/RETRIEVAL_CA_BENCHMARK_local_eval_20261024T102833Z.md":
        "reports/evaluation/RETRIEVAL_CA_BENCHMARK_local_eval_20261024T102500Z.md",
    "results/evaluation/counter_evidence_quality_benchmark/local_eval_20261024T102833Z.json":
        "results/evaluation/counter_evidence_quality_benchmark/local_eval_20261024T102500Z.json",
    "reports/evaluation/COUNTER_EVIDENCE_QUALITY_BENCHMARK_local_eval_20261024T102833Z.md":
        "reports/evaluation/COUNTER_EVIDENCE_QUALITY_BENCHMARK_local_eval_20261024T102500Z.md",
    "results/evaluation/current_head_slice_quality/local_eval_20261024T102833Z.json":
        "results/evaluation/current_head_slice_quality/local_eval_20261024T102500Z.json",
    "reports/evaluation/CURRENT_HEAD_SLICE_QUALITY_local_eval_20261024T102833Z.md":
        "reports/evaluation/CURRENT_HEAD_SLICE_QUALITY_local_eval_20261024T102500Z.md",
    "results/evaluation/d2_path_scope_probe/local_eval_20261024T102833Z.json":
        "results/evaluation/d2_path_scope_probe/local_eval_1792837481.json",
    "reports/evaluation/D2_PATH_SCOPE_PROBE_local_eval_20261024T102833Z.md":
        "reports/evaluation/D2_PATH_SCOPE_PROBE_local_eval_1792837481.md",
}

NEW_REFS = [
    "evaluation/D2_LETTERHEAD_PATTERN_PROFILE_40089391202_HYPOTHESIS_V1.json",
    "evaluation/D2_LETTERHEAD_PATTERN_PROFILE_40089391202_FREEZE_V1.json",
    "evaluation/d2_letterhead_pattern_profile.py",
    "tests/evaluation/test_d2_letterhead_pattern_profile.py",
    "results/evaluation/d2_letterhead_pattern_profile/40089391202.json",
    "reports/evaluation/D2_LETTERHEAD_PATTERN_PROFILE_40089391202.md",
    "evaluation/operational_resume_40089391202_state_repair.py",
    "results/evaluation/orchestration/40089391202_nested_evidence_refs.json",
]


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    repairs: list[str] = []

    # R1: fix phantom refs by name (append-only: correct the string, delete nothing)
    fixed = 0
    refs = state.get("evidence_refs") or []
    for i, r in enumerate(refs):
        if r in PHANTOM_FIX:
            refs[i] = PHANTOM_FIX[r]
            fixed += 1
    assert fixed == 8, f"expected 8 phantom refs, found {fixed}"
    repairs.append(
        f"R1: corrected {fixed} phantom evidence_refs from "
        f"local_eval_20261024T102833Z names to their real committed artifact "
        f"paths (local_eval_20261024T102500Z / local_eval_1792837481); "
        f"verified by nested_evidence_refs_guard (8 top-level unresolved -> 0)")

    # R3: de-duplicate preserving first occurrence
    seen: set[str] = set()
    deduped: list[str] = []
    n_dupes = 0
    for r in refs:
        if r in seen:
            n_dupes += 1
            continue
        seen.add(r)
        deduped.append(r)
    state["evidence_refs"] = deduped
    if n_dupes:
        repairs.append(
            f"R3: de-duplicated {n_dupes} repeated evidence_refs entries "
            f"(first occurrence preserved)")

    # R2: github_run -> this resume run
    state["github_run"] = "40089391202"
    repairs.append(
        "R2: github_run set from the phantom string local_eval_20261024T102833Z "
        "to 40089391202 (this operational-resume run)")

    # R4: requirement-39 labelling on the producer's regression-validation block
    mrb = state.get("minimal_ret_ca_benchmark_latest")
    if mrb and mrb.get("run_id") == "local_eval_20261024T102500Z":
        mrb["requirement_39_labelling"] = (
            "DELIBERATE instrument-regression validation on the served-lineage "
            "packet 38839347028 (the benchmark's own historical served corpus "
            "for the leg1 baseline), NOT a packet-of-record measurement and NOT "
            "a frozen-bar result. The standing PRODUCT_FALSIFIED record on "
            "packet-of-record 39319405429 (run 39927760701, confirmed 39909449668 "
            "/ latest_confirmation_record 40034814235) remains the benchmark of "
            "record, unchanged."
        )
        repairs.append(
            "R4: added the requirement-39 old-packet labelling note to "
            "minimal_ret_ca_benchmark_latest (measurement preserved unchanged)")

    # R5a: d2_letterhead_pattern_profile_latest block
    profile_path = (_REPO_ROOT / "results" / "evaluation"
                    / "d2_letterhead_pattern_profile" / "40089391202.json")
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    state["d2_letterhead_pattern_profile_latest"] = {
        "run_id": "40089391202",
        "direction_version": 67,
        "verdict": profile["verdict"],
        "exit_code": profile["exit_code"],
        "controls_all_pass": profile["controls_all_pass"],
        "population_extension_disclosure": profile["population_extension_disclosure"],
        "n_bundles": profile["n_bundles"],
        "n_bundles_shipped_slice": profile["n_bundles_shipped_slice"],
        "n_bundles_packet_of_record": profile["n_bundles_packet_of_record"],
        "d2_rows_profiled": profile["d2_rows_profiled"],
        "n_distinct_letterhead_patterns": profile["n_distinct_letterhead_patterns"],
        "detectability_summary": {
            k: v for k, v in profile["detectability_summary"].items()
            if k != "p3_patterns"} | {
            "p3_patterns": profile["detectability_summary"]["p3_patterns"]},
        "patterns_inventory": [
            {k: p[k] for k in (
                "pattern_key", "detectability_class", "n_rows", "languages",
                "decisions", "full_text_offsets", "defect_class_counts",
                "evidence_preview")}
            for p in profile["letterhead_patterns"]],
        "finding": profile["finding"],
        "feasibility_reading": (
            "All observed D2 letterhead forms are mechanically detectable "
            "(P1/P2; this run observed 2 distinct P1 offset-0 multi-line court "
            "headers: the trilingual Graubunden header on gr_gerichte_ERZ 2010 "
            "25 spanning 29 families incl. the current-head latest, and a "
            "3-line 'Urteilskopf' header on bge_BGE_110_II_391 in 5 older "
            "families). On this named population the deterministic "
            "letterhead-filter branch remains mechanically viable; reachability "
            "for slice rows stays fixture_bypass_only and the accepted ARM2 "
            "pivot_absent abstention (40070818687, cited not re-run) still "
            "binds the filter's own detector, so a product repair must fix "
            "BOTH legs per v67. Descriptive only; scores no frozen bar; "
            "accepted baseline 40062917685 unmoved."),
        "result_file": "results/evaluation/d2_letterhead_pattern_profile/40089391202.json",
        "report_file": "reports/evaluation/D2_LETTERHEAD_PATTERN_PROFILE_40089391202.md",
        "hypothesis_file": "evaluation/D2_LETTERHEAD_PATTERN_PROFILE_40089391202_HYPOTHESIS_V1.json",
        "freeze_record": "evaluation/D2_LETTERHEAD_PATTERN_PROFILE_40089391202_FREEZE_V1.json",
        "instrument_file": "evaluation/d2_letterhead_pattern_profile.py",
        "packet_of_record_labelled": "39319405429 (verified rows under frozen predicate: 0, accepted requirement 36/42 expectation, labelled)",
        "no_bar_movement": True,
    }
    repairs.append(
        "R5: v67 ordered work item (1) EXECUTED this run — "
        "d2_letterhead_pattern_profile_latest added from committed artifact "
        "results/evaluation/d2_letterhead_pattern_profile/40089391202.json")

    # R5b: accepted_run_id advance 40068038783 -> 40084716045 (both halves verified)
    if state.get("accepted_run_id") == "40068038783":
        state["accepted_run_id_advance"] = {
            "from": "40068038783",
            "to": "40084716045",
            "reason": (
                "operational resume 40089391202: cycles 40082514143, 40083917238 "
                "and 40084716045 each carry BOTH halves of factory-wide "
                "requirement 4 (results/audit/evaluation/CYCLE_<id>_GATE.json "
                "gate=PASS, safe_to_integrate=true, required_fixes=[] AND an "
                "'accept evaluation cycle <id>' commit on lab/evaluation: "
                "a5333d1f, 1f51e4ca, f2734734). The canonical state's "
                "accepted_run_id had lagged at 40068038783; advanced with "
                "disclosure, no historical record overwritten."),
            "prior_advance": state.get("accepted_run_id_advance"),
        }
        state["accepted_run_id"] = "40084716045"
        repairs.append(
            "R5b: accepted_run_id advanced 40068038783 -> 40084716045 with the "
            "disclosure chain (both halves of requirement 4 verified for the "
            "three intermediate accepted cycles)")

    # append NEW_REFS
    for r in NEW_REFS:
        if r not in state["evidence_refs"]:
            state["evidence_refs"].append(r)
    state["evidence_refs_n"] = len(state["evidence_refs"])

    # R6: continue_recommended stays false, fuller reason
    state["continue_recommended"] = False
    state["continue_recommended_reason"] = (
        "v67 ordered work is FULLY discharged with accepted/preserved evidence: "
        "item (1) EXECUTED this run (d2_letterhead_pattern_profile 40089391202: "
        "93 sha256-pinned bundles, 41 D2 rows -> 2 distinct P1 mechanically "
        "detectable letterhead patterns, controls C3-C6 all pass, packet-of-record "
        "labelled 0 verified rows per accepted requirement 36/42); item (2) "
        "NOT_YET_DISCRIMINATING because product head e2270c37 (accept 40080810801) "
        "has NOT landed the fixture-path content-filter repair (current_head_slice_quality "
        "local_eval_20261024T102500Z: H2 defects persist on latest slices); items "
        "(3)/(4) standing record and report-only. Another cycle under the same v67 "
        "question would re-confirm a stable finding with no discriminating purpose. "
        "The next discriminating evaluation cycle requires a NEW product head that "
        "has landed the fixture-path repair (content filter on the emission path OR "
        "non-fixture slice regeneration), then the frozen item-(2) re-measure plus "
        "d2_path_scope_probe on that head. Both DO-NOT-SERVE orders stand; admission "
        "stays fail-closed; comparative map-vs-ranked-list stays VACUOUS; "
        "owner_decision_required=false."
    )
    state["next_recommendation"] = (
        "NOT_YET_DISCRIMINATING (item (2) blocked on product, not on evaluation): "
        "Core Product must land BOTH legs of the P0 residual per accepted "
        "PATH_SCOPE_RESIDUAL (40070818687) and the per-class verdict (40068038783) "
        "— the letterhead detector must REJECT the observed offset-0 multi-line "
        "court-header variants (the two P1 patterns profiled this run) AND the "
        "offline/slice emission path must route through the filter (or regenerate "
        "via the non-fixture path). Evaluation's next discriminating cycle is the "
        "frozen post-repair re-measure on that NEW head. The v67 item-(1) "
        "feasibility profile is complete and is Core Product's input for the "
        "deterministic-filter decision. Do not re-run v67 ordered work; do not "
        "re-score packet 39319405429 (item-(3) reconciliation accepted, unchanged)."
    )
    repairs.append(
        "R6: continue_recommended stays false with the fuller v67-discharged "
        "reason; next_recommendation updated to the post-repair re-measure gate")

    # operational resume disclosure block
    state["operational_resume_40089391202"] = {
        "resumed_producer_run": "40085602229",
        "producer_team_commit": "e36f7afa3cf30c4c1703f10cbb68dac2a59073ff",
        "producer_work_preserved": [
            "results/evaluation/minimal_ret_ca_benchmark/local_eval_20261024T102500Z.json (+2 leg files)",
            "reports/evaluation/RETRIEVAL_CA_BENCHMARK_local_eval_20261024T102500Z.md",
            "results/evaluation/counter_evidence_quality_benchmark/local_eval_20261024T102500Z.json",
            "reports/evaluation/COUNTER_EVIDENCE_QUALITY_BENCHMARK_local_eval_20261024T102500Z.md",
            "results/evaluation/current_head_slice_quality/local_eval_20261024T102500Z.json",
            "reports/evaluation/CURRENT_HEAD_SLICE_QUALITY_local_eval_20261024T102500Z.md",
            "results/evaluation/d2_path_scope_probe/local_eval_1792837435.json + local_eval_1792837481.json",
            "reports/evaluation/D2_PATH_SCOPE_PROBE_local_eval_1792837435.md + local_eval_1792837481.md",
        ],
        "diagnosis": (
            "Run 40085602229 completed its producer job (team branch pushed) but "
            "no audit branch exists — the chain broke before the audit completed, "
            "so nothing from it was accepted (requirement 4 unmet). Independent "
            "verification found the durable defect class: the producer's "
            "state/evaluation.json added 8 top-level evidence_refs named "
            "local_eval_20261024T102833Z that exist nowhere in the tree (actual "
            "artifacts are local_eval_20261024T102500Z / local_eval_1792837481), "
            "set github_run to the same phantom string, and carried 2 duplicate "
            "refs — the requirement-33 unresolving-refs fabrication class "
            "(requirement 38 operational-resume guard: 9 unresolved, 8 top-level, "
            "1 inherited). The producer also declared continue_recommended=false "
            "while v67 ordered work item (1) had not been executed."),
        "repairs_applied": repairs,
        "claim_ceiling": (
            "Operational-resume disclosure only: names what was preserved, what "
            "was repaired and why; makes no product, bar or serve claim."),
    }

    state["cycle_status"] = "COMPLETE"
    state["evidence_tier"] = "REPRODUCED"
    state["acceptance_status"] = "PROPOSED_PENDING_INDEPENDENT_AUDIT"
    state["human_gate_ready"] = False
    state["machine_gate_ready"] = False
    state["packet_admitted"] = False
    state["ready_for_owner_session"] = False
    state["owner_decision_required"] = False
    state["state_updated_at"] = datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    state["state_updated_by"] = "operational_resume_40089391202"

    STATE.write_text(json.dumps(state, indent=1, ensure_ascii=False) + "\n",
                     encoding="utf-8")
    print(json.dumps({
        "state_sha256": _sha256_file(STATE),
        "repairs": repairs,
        "evidence_refs_n": state["evidence_refs_n"],
        "github_run": state["github_run"],
        "accepted_run_id": state["accepted_run_id"],
        "continue_recommended": state["continue_recommended"],
    }, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
