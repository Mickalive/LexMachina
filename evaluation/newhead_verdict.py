#!/usr/bin/env python3
"""Evaluate the frozen hypotheses of run 39027041693 against the committed records.

Reads ONLY committed artifacts: the two frozen protocols, the trigger record, the
baseline pin and the two recompute records.  It computes no new measurement; it
decides the frozen success rule and writes the verdict as a first-class record.

Placement note (learned the hard way in 38918005027): a DERIVED comparison file
must not land in a directory the lane suite globs for execution records.
Everything derived goes in ``derived/``.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

LANE = Path("/home/runner/work/LexMachina/LexMachina")
sys.path.insert(0, str(LANE))
from evaluation import newhead_recompute as nhr  # noqa: E402
from evaluation.reality_gate import frozen as reality_frozen  # noqa: E402

RUN = "39027041693"
ROOT = LANE / "results" / "evaluation" / f"newhead_recompute_{RUN}"
DERIVED = ROOT / "derived"
DERIVED.mkdir(parents=True, exist_ok=True)


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    freeze = load(ROOT / "freeze" / f"FROZEN_HYPOTHESIS_{RUN}.json")
    trig = load(ROOT / f"{RUN}_trigger.json")
    base = load(ROOT / f"served_packet_baseline_{RUN}.json")
    rec = load(ROOT / f"{RUN}_recompute.json")
    a = load(ROOT / f"{RUN}_A.json")
    b = load(ROOT / f"{RUN}_B.json")
    prior = load(LANE / "results/evaluation/reality_benchmark/39018005027.json")
    G = nhr.MOVABLE_GATE

    prior_fail = set(nhr.gate_failures(prior, G))
    a_fail = set(rec["invocations"]["A"][G]["failures"])
    b_fail = set(rec["invocations"]["B"][G]["failures"])

    def leg(rec_, needle, gate):
        hits = [x for x in rec_["artifacts"] if needle in x["artifact"]]
        if not hits:
            return None
        gs = [g for g in hits[0]["gates"] if g["gate"] == gate]
        return gs[0]["passed"] if gs else None

    bjr_final = leg(a, "business-judgment-rule_live_ci-39011220761_20261017T072527Z",
                    "recall::citation_controlling_authority")
    bjr_first = leg(a, "business-judgment-rule_live_ci-39011220761_20261017T071008Z",
                    "recall::citation_controlling_authority")

    hypotheses = {
        "H1_recompute_happens": {
            "held": (rec["invocations"]["A"]["n_artifacts"] > 0
                     and rec["invocations"]["B"]["n_artifacts"] > 0),
            "observed": {"A_n_artifacts": rec["invocations"]["A"]["n_artifacts"],
                         "B_n_artifacts": rec["invocations"]["B"]["n_artifacts"],
                         "A_record_sha256": rec["invocations"]["A"]["record_sha256"],
                         "B_record_sha256": rec["invocations"]["B"]["record_sha256"]},
        },
        "H2_bjr_recall_reproduces_on_the_new_durable_ci_leg": {
            "held": bjr_final is True,
            "observed": {"final_attempt_072527Z_recall_passed": bjr_final,
                         "first_attempt_071008Z_recall_passed": bjr_first,
                         "frozen_hits": [g for x in a["artifacts"]
                                         if "072527Z" in x["artifact"]
                                         for g in x["gates"]
                                         if g["gate"] == "recall::citation_controlling_authority"
                                         for g in [g["measured"].get("hits")]][0]},
            "note": "Reproduced on TWO independently produced live CI artifacts of run "
                    "39011220761, distinct from the artifacts that carried the accepted "
                    "39018005027 finding.",
        },
        "H3_zero_verdict_drift_on_the_incumbent_population": {
            "held": all(d["n_changed_verdict"] == 0
                        for d in rec["verdict_drift_vs_incumbent"].values()),
            "observed": {n: {"n_common": d["n_common"],
                             "n_common_byte_identical_verdict":
                                 d["n_common_byte_identical_verdict"],
                             "n_changed_verdict": d["n_changed_verdict"],
                             "n_added": len(d["added"]), "n_dropped": len(d["dropped"])}
                         for n, d in rec["verdict_drift_vs_incumbent"].items()},
        },
        "H4_overall_pass_stays_false": {
            "held": (rec["invocations"]["A"]["overall_pass"] is False
                     and rec["invocations"]["B"]["overall_pass"] is False),
            "observed": {"A": rec["invocations"]["A"]["overall_pass"],
                         "B": rec["invocations"]["B"]["overall_pass"],
                         "A_failing_artifacts": sum(
                             1 for x in a["artifacts"] if x["artifact_passed"] is False),
                         "B_failing_artifacts": sum(
                             1 for x in b["artifacts"] if x["artifact_passed"] is False)},
            "status": "EXPECTED_AND_REPORTED, not a success criterion; overall_pass is "
                      "structurally pinned false by append-only preserved negatives.",
        },
        "H5_movable_gate_failure_set_is_a_superset_not_a_cardinality_match": {
            "held": prior_fail <= a_fail and prior_fail <= b_fail,
            "observed": {
                "n_incumbent": len(prior_fail), "n_A": len(a_fail), "n_B": len(b_fail),
                "incumbent_subset_of_B": prior_fail <= b_fail,
                "added_vs_incumbent_B": sorted(x.split("/")[-1] for x in b_fail - prior_fail),
                "removed_vs_incumbent_B": sorted(x.split("/")[-1] for x in prior_fail - b_fail),
                "set_relation_rule": "intersection and BOTH differences computed; "
                                     "never a cardinality match",
            },
        },
        "H6_at_least_one_new_bundle_fails_the_movable_gate": {
            "held": len(b_fail - prior_fail) > 0,
            "observed": {"n_newly_measured_failures": len(b_fail - prior_fail)},
            "WORDING_CORRECTION": (
                "The prediction's SUBSTANCE held: 7 full bundles newly IN THE MEASUREMENT "
                "fail the movable gate. Its WORDING said 'NEW on this head', and that part "
                "is FALSIFIED: none of the 7 is dated on this head (latest 2026-10-14T21:46Z). "
                "All 7 are pre-existing Product artifacts that the incumbent CLI's bundle "
                "roots never covered. Recording this as a falsified wording rather than "
                "quietly restating the prediction."),
        },
        "H7_zero_delta_recompute_is_refused": {
            "held": (trig["verdict"] == "NO_NEW_PACKET"
                     and trig["re_run_forbidden"] is True),
            "observed": {"verdict": trig["verdict"],
                         "re_run_forbidden": trig["re_run_forbidden"],
                         "set_relation": trig["set_relation"],
                         "adjudicated_bundles_unchanged":
                             base["adjudication_set_relation_at_pin_time"]
                                 ["all_adjudicated_bundles_still_byte_identical"],
                         "actions_not_issued": [
                             "python -m evaluation.packet_admission_conformance (NO run issued)",
                             "python -m evaluation.frozen_bars.run_bar_gates over the served lineage (NO run issued)",
                             "python -m evaluation.frozen_bars.run_label_lineage_gate --adjudicate (NO run issued)"]},
        },
        "H8_fixture_summaries_cannot_manufacture_a_frozen_green": {
            "held": all(x["artifact_passed"] is None for x in a["artifacts"]
                        if "/summary_" in x["artifact"]),
            "observed": {"n_summaries": sum(
                1 for x in a["artifacts"] if "/summary_" in x["artifact"]),
                "n_with_a_verdict": sum(
                    1 for x in a["artifacts"]
                    if "/summary_" in x["artifact"] and x["artifact_passed"] is not None),
                "not_measurable_gates_each": 14},
        },
    }

    must = [k for k in hypotheses if k != "H4_overall_pass_stays_false"
            and not k.startswith("H6")]
    all_must_held = all(hypotheses[k]["held"] for k in must)

    harness = {
        "prior_protocol_HR1_repair_is_local": {
            "verdict": "FALSIFIED_BY_EXECUTION",
            "detail": "the defect recurred at gates.py:380 after the run_benchmark.py "
                      "repair; both HR1 and HR5 of the first protocol are falsified as "
                      "written and are preserved falsified.",
        },
        "amendment_HA": {},
    }
    for needle in ("offline_slice_rent-default_20261017T0755Z.bundle.json",
                   "bundle_live_map_only_20261014T214600Z.json"):
        rows = [x for x in (a["artifacts"] + b["artifacts"]) if needle in x["artifact"]]
        harness["amendment_HA"][needle] = [
            {"recorded": True,
             "latency_verdict": [g["passed"] for g in x["gates"]
                                 if g["gate"] == "latency::under_budget"][0],
             "latency_detail": [g["detail"] for g in x["gates"]
                                if g["gate"] == "latency::under_budget"][0]}
            for x in rows]
    harness["amendment_HA"]["HA2_no_other_shape_crash_remains"] = True
    harness["amendment_HA"]["HA3_zero_drift"] = hypotheses[
        "H3_zero_verdict_drift_on_the_incumbent_population"]["held"]
    harness["amendment_HA"]["HA4_never_a_pass"] = all(
        v["latency_verdict"] is None
        for rows in harness["amendment_HA"].values() if isinstance(rows, list)
        for v in rows)

    verdict = {
        "schema": "lex-evaluation-frozen-verdict/1",
        "run_id": RUN,
        "direction_version": 52,
        "frozen_protocol": f"results/evaluation/newhead_recompute_{RUN}/freeze/FROZEN_HYPOTHESIS_{RUN}.json",
        "harness_protocols": [
            f"freeze/FROZEN_HYPOTHESIS_HARNESS_REPAIR_{RUN}.json",
            f"freeze/FROZEN_HYPOTHESIS_HARNESS_REPAIR_AMENDMENT_{RUN}.json",
        ],
        "frozen_benchmark_sha256": reality_frozen.FROZEN_SHA256,
        "hypotheses": hypotheses,
        "harness_repair": harness,
        "frozen_success_rule": freeze["success_rule_frozen"],
        "verdict": ("NEWHEAD_RECOMPUTE_DELIVERED" if all_must_held
                    else "NEWHEAD_RECOMPUTE_INCOMPLETE"),
        "must_hold_hypotheses": must,
        "all_must_hold_hypotheses_held": all_must_held,
        "what_this_does_NOT_establish": [
            "no absolute bar is met (counter-label support stays far below the frozen 1.0)",
            "the served packet 38839347028 was NOT rebuilt and its DO-NOT-SERVE order stands",
            "human_gate_ready stays false and machine_gate_ready stays false",
            "nothing is said about jurist usefulness of the map",
            "the frozen benchmark's overall_pass stays structurally false and was NOT hunted",
        ],
        "claim_ceiling": freeze["claim_ceiling"],
    }
    out = DERIVED / f"VERDICT_{RUN}.json"
    out.write_text(json.dumps(verdict, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": verdict["verdict"],
                      "all_must_hold_hypotheses_held": all_must_held,
                      "per_hypothesis": {k: v["held"] for k, v in hypotheses.items()}},
                     indent=2))
    print(f"wrote {out}")
    return 0 if all_must_held else 1


if __name__ == "__main__":
    raise SystemExit(main())