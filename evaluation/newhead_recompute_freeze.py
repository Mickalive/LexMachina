#!/usr/bin/env python3
"""Write the FROZEN protocol + population manifests for run 39027041693.

Run ONCE, before any frozen instrument is executed on the new Product head.
Its own output is committed; the commit sha is recorded in the freeze file.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

LANE = Path("/home/runner/work/LexMachina/LexMachina")
sys.path.insert(0, str(LANE))
from evaluation.newhead_recompute import packet_population, sha256_file  # noqa: E402
from evaluation.reality_gate import frozen as reality_frozen  # noqa: E402

RUN_ID = "39027041693"
PRODUCT = Path("/tmp/lex_accepted/product")
OUT = LANE / "results" / "evaluation" / "newhead_recompute_39027041693"
FREEZE = OUT / "freeze"
FREEZE.mkdir(parents=True, exist_ok=True)

# The two frozen invocations. A is the byte-identical incumbent CLI of runs
# 38920872324 / 38934722443 / 38945976309 / 39018005027; B adds the bundle roots
# the new Product head ships. The FROZEN SPEC is identical in both.
INCUMBENT_EVIDENCE = PRODUCT / "results/product/reality_check"
B_INCUMBENT = [PRODUCT / "results/product/gate_packet/38839347028/questions",
               PRODUCT / "results/product/adversarial_retrieval/38828034436"]
B_EXTRA = [PRODUCT / "results/product/offline_slice",
           PRODUCT / "results/product/clickable_slice",
           PRODUCT / "results/product/progressive_slice",
           PRODUCT / "results/product/gate_rehearsal",
           PRODUCT / "results/product/latency_budget",
           PRODUCT / "results/product/human_gate_sessions_simulated",
           PRODUCT / "results/product/gate_packet/38799024807/questions",
           PRODUCT / "results/product/gate_packet/38812599575/questions",
           PRODUCT / "results/product/gate_packet/38838116453/questions",
           PRODUCT / "results/product/gate_packet/offline_machinery_rehearsal/questions"]


def manifest_for(dirs: list[Path], evidence: Path) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    root = PRODUCT.resolve()
    paths: list[Path] = sorted(evidence.glob("*.json")) if evidence.is_dir() else []
    for d in dirs:
        if d.is_dir():
            paths += sorted(d.glob("*.json"))
    for p in sorted(set(paths)):
        rows.append((str(p.relative_to(root)), sha256_file(p)))
    return rows


def write_tsv(path: Path, rows: list[tuple[str, str]]) -> str:
    path.write_text("".join(f"{p}\t{s}\n" for p, s in rows), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_head() -> str:
    try:
        return subprocess.run(["git", "-C", str(LANE), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "UNAVAILABLE"


def main() -> int:
    rows_a = manifest_for(B_INCUMBENT, INCUMBENT_EVIDENCE)
    rows_b = manifest_for(B_INCUMBENT + B_EXTRA, INCUMBENT_EVIDENCE)
    sha_a = write_tsv(FREEZE / f"POPULATION_{RUN_ID}_A.tsv", rows_a)
    sha_b = write_tsv(FREEZE / f"POPULATION_{RUN_ID}_B.tsv", rows_b)

    pop = packet_population(PRODUCT)
    baseline = json.loads((LANE / "results/evaluation/newhead_recompute_39027041693"
                           / "served_packet_baseline_39027041693.json").read_text(encoding="utf-8"))

    prior = json.loads((LANE / "results/evaluation/reality_benchmark/39018005027.json")
                       .read_text(encoding="utf-8"))
    movable_fail_incumbent = sorted(
        str(a["artifact"]) for a in prior["artifacts"]
        for g in a.get("gates", []) if g.get("gate") == "structural::counter_classifications_supported"
        and g.get("passed") is False)

    product_state = json.loads((PRODUCT / "state/product.json").read_text(encoding="utf-8"))
    product_state_sha = sha256_file(PRODUCT / "state/product.json")

    freeze = {
        "schema": "lex-evaluation-frozen-hypothesis/newhead-recompute/1",
        "run_id": RUN_ID,
        "lane": "evaluation",
        "direction_version": 52,
        "frozen_at_utc": "2026-10-17",
        "frozen_before_execution": True,
        "frozen_before_record_written": True,
        "frozen_commit_note": (
            "This file and both population manifests are committed BEFORE "
            "`python -m evaluation.reality_gate.run_benchmark` is executed for "
            f"run {RUN_ID} and before `python -m evaluation.newhead_recompute` runs "
            "in trigger mode. Nothing below may change after execution; a change "
            "invalidates the run."),
        "git_head_at_freeze": git_head(),
        "lane_question_anchored_to": (
            "state/factory_direction.json lanes.evaluation.question (v52) deliverables "
            "(1), (4), (5) and (7). The v50 gate-building question is DISCHARGED and "
            "was not reopened: the two frozen-bar gates already exist and are accepted."),
        "question": (
            "Product head moved to cc719eebf 'accept product cycle 39019268074'. Does that "
            "new head move any of the only three deliverables still open to Core "
            "Evaluation under direction v52, and does the frozen reality benchmark "
            "ff57f556 applied per-artifact to it produce a verdict the product may cite?"),
        "trigger_event": {
            "previous_product_head_seen_by_this_lane": (
                "cc719eebf was created 2026-10-17T09:54:48Z; this lane's last accepted "
                "cycle 39020603510 wrote state at 09:45:39Z, i.e. BEFORE that accept "
                "commit existed. Product bytes are therefore new to this lane."),
            "new_claim_bearing_artifacts_observed_pre_freeze": {
                "durable_live_ci_reality_run": (
                    "results/product/reality_check/summary_ci_39011220761.json - mode=live, "
                    "evidence_tier=CI_TEAM_JOB_LIVE, all_legs_passed=true, 4/4 legs, "
                    "business-judgment-rule carries recall::citation_controlling_authority "
                    "passed=true, run_head_sha 807844c7d173a2652061bdc17d2cde9054de0011, "
                    "head_sha 3077b274f7e52d972fdd2f42b472c13849f545d8."),
                "eight_offline_fixture_summaries": (
                    "summary_fixture_*.json 06:53Z..09:14Z and their 4-per-run leg reports; "
                    "each declares frozen_gates_evaluated=[] and a claim_ceiling that no "
                    "fixture result may be cited as a green frozen leg."),
                "new_bundle_roots": [str(p) for p in B_EXTRA],
            },
            "served_packet_claim_population": {
                "n_files": pop["n_files"],
                "n_packet_dirs": pop["packet_dirs"],
                "state_product_json_sha256": pop["manifest"].get("state/product.json"),
                "state_product_json_state_updated_by_run": product_state.get("state_updated_by_run"),
                "state_product_json_state_updated_at": product_state.get("state_updated_at"),
                "state_product_json_cycle_status_head": str(product_state.get("cycle_status"))[:120],
            },
        },
        "baseline_under_test": (
            "The incumbent accepted record results/evaluation/reality_benchmark/39018005027.json "
            "(113 artifacts) produced by the byte-identical incumbent CLI, and the accepted "
            "label-lineage sweep record 39020603510_sweep.json for the served-packet bars."),
        "frozen_instruments_not_touched": {
            "reality_frozen_benchmark_sha256": reality_frozen.FROZEN_SHA256,
            "reality_frozen_benchmark_on_disk": "evaluation/reality_gate/frozen_benchmark.json",
            "gate_contract_sha256": "06781743c2686fa63a6652ad61c8d63381cfa707f5fd6682a50b9027470d2492",
            "rules_label_sha256": "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608",
            "rules_geometry_sha256": "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633",
            "statement": (
                "No threshold, rubric, bar or spec is created, re-derived, re-tuned or "
                "clarified by this cycle. The only new code is measurement and set "
                "comparison over the frozen instruments' own outputs."),
        },
        "invocations": {
            "A": {
                "purpose": "byte-identical incumbent CLI; isolates the effect of the new head on the incumbent population",
                "evidence_dir": str(INCUMBENT_EVIDENCE),
                "extra_bundle_dirs": [str(p) for p in B_INCUMBENT],
                "population_n": len(rows_a),
                "population_manifest": str(FREEZE / f"POPULATION_{RUN_ID}_A.tsv"),
                "population_manifest_sha256": sha_a,
            },
            "B": {
                "purpose": "the same frozen spec over the bundle roots the new head ships",
                "evidence_dir": str(INCUMBENT_EVIDENCE),
                "extra_bundle_dirs": [str(p) for p in B_INCUMBENT + B_EXTRA],
                "population_n": len(rows_b),
                "population_manifest": str(FREEZE / f"POPULATION_{RUN_ID}_B.tsv"),
                "population_manifest_sha256": sha_b,
            },
            "delta_A_to_B": {
                "added_paths": sorted({p for p, _ in rows_b} - {p for p, _ in rows_a}),
                "n_added": len({p for p, _ in rows_b} - {p for p, _ in rows_a}),
                "n_dropped": len({p for p, _ in rows_a} - {p for p, _ in rows_b}),
                "n_changed": sum(1 for p, s in rows_a if dict(rows_b).get(p) not in (None, s)),
            },
        },
        "incumbent_movable_gate_failures": movable_fail_incumbent,
        "incumbent_movable_gate_failure_n": len(movable_fail_incumbent),
        "served_packet_baseline_manifest_ref": (
            "results/evaluation/newhead_recompute_39027041693/served_packet_baseline_39027041693.json"),
        "served_packet_baseline_manifest_sha256": hashlib.sha256(
            (LANE / "results/evaluation/newhead_recompute_39027041693"
             / "served_packet_baseline_39027041693.json").read_bytes()).hexdigest(),
        "served_packet_baseline_files": len(baseline.get("manifest", {})),
        "hypotheses": {
            "H1_recompute_happens": (
                "Delivery: the new head's claim population is recomputed per-artifact with the "
                "frozen spec ff57f556, in both invocations, and both records are committed."),
            "H2_bjr_recall_reproduces_on_the_new_durable_ci_leg": {
                "statement": (
                    "The NEW durable live CI leg report "
                    "business-judgment-rule_live_ci-39011220761_20261017T072527Z.json passes "
                    "recall::citation_controlling_authority under the frozen spec, reproducing "
                    "the 39018005027 finding on a different, independently produced artifact."),
                "direction": "must hold",
                "if_false": "Product's durable-run recall claim does not reproduce; that is a "
                            "PRODUCT falsification and is reported as such, not absorbed.",
            },
            "H3_zero_verdict_drift_on_the_incumbent_population": {
                "statement": "Under the byte-identical incumbent CLI (invocation A), every "
                             "artifact common to 39018005027 and this run keeps an identical "
                             "artifact_passed verdict.",
                "direction": "must hold",
                "if_false": "the frozen instrument is not verdict-stable on unchanged bytes, "
                            "which invalidates every per-artifact claim built on it.",
            },
            "H4_overall_pass_stays_false": {
                "statement": "overall_pass stays false in both invocations.",
                "direction": "expected, NOT a success criterion",
                "note": "overall_pass is structurally pinned false by append-only preserved "
                        "negatives (13 immutable legacy failures). It is reported, never hunted.",
            },
            "H5_movable_gate_failure_set_is_a_superset_not_a_cardinality_match": {
                "statement": (
                    "The set of artifacts failing structural::counter_classifications_supported "
                    "under invocation B CONTAINS the 6 incumbent failures, all of which are "
                    "byte-identical artifacts, and this containment is proven by sha set "
                    "relation, never by matching counts."),
                "direction": "must hold",
                "if_false": "an incumbent failure was mutated or dropped, which is a more "
                            "serious finding than any counter-label movement.",
            },
            "H6_at_least_one_new_bundle_fails_the_movable_gate": {
                "statement": (
                    "At least one full bundle NEW on this head FAILS "
                    "structural::counter_classifications_supported under invocation B."),
                "direction": "PREDICTION, may be falsified",
                "pre_freeze_basis": (
                    "Packets 38799024807 and 38812599575 score 0/7 and 1/9 supported rows "
                    "under the ACCEPTED frozen label rubric 4457e971 (measured and recorded in "
                    "the accepted sweep 39020603510_sweep.json, read as ACCEPTED EVIDENCE "
                    "before this freeze). Their bundles are now in the recompute population. "
                    "The two predicates are different (evidence/uncertainty plumbing vs full "
                    "rubric support), so this is a genuine prediction and not an identity."),
                "if_false": (
                    "reported as a falsified prediction. It would mean the new offline/slice "
                    "bundles carry no unsupported counter rows, which narrows where the "
                    "counter-label bar can still be moved; it is NOT a pass for the product."),
            },
            "H7_zero_delta_recompute_is_refused": {
                "statement": (
                    "The direction item (1) trigger, executed as a set relation against the "
                    "pinned served-packet baseline manifest, returns NO_NEW_PACKET, and "
                    "therefore this cycle issues NO packet_admission_conformance run and NO "
                    "re-run of either frozen bar over the served lineage."),
                "direction": "must hold",
                "if_false": "ADJUDICATE_REQUIRED, in which case deliverables (2) and (3) fire "
                            "in this same cycle and the recompute is not the last word.",
            },
            "H8_fixture_summaries_cannot_manufacture_a_frozen_green": {
                "statement": (
                    "The 8 offline fixture summaries and their leg reports are recorded with no "
                    "frozen verdict (artifact_passed is None) or are otherwise never allowed to "
                    "contribute a PASS to any frozen gate; a fixture artifact's own claim_ceiling "
                    "forbids citing it as a green frozen leg."),
                "direction": "must hold",
                "if_false": "the frozen benchmark would be manufacturing a green from an "
                            "artifact that disclaims it, which is a falsification of the gate.",
            },
        },
        "success_rule_frozen": (
            "NEWHEAD_RECOMPUTE_DELIVERED iff H1 AND H2 AND H3 AND H5 AND H7 AND H8. "
            "H4 is reported and expected false. H6 is a pre-registered prediction that may be "
            "falsified without invalidating the run. H5 is evaluated as a SET RELATION with "
            "both differences reported, never by matching cardinalities."),
        "metric": (
            "per-artifact artifact_passed from the frozen runner; per-gate outcome lists for "
            "every gate the frozen spec defines; sha set relations between populations and "
            "between failure sets; exit codes of the frozen entry point."),
        "not_touched": [
            "evaluation/reality_gate/frozen_benchmark.json (digest ff57f556...)",
            "evaluation/reality_gate/GATE_CONTRACT.json (digest 06781743...)",
            "evaluation/reality_gate/gates.py thresholds (all read from GATE_CONTRACT)",
            "evaluation/frozen_bars/RULES_LABEL.json (4457e971...)",
            "evaluation/frozen_bars/RULES_GEOMETRY.json (a7452748...)",
            "evaluation/frozen_bars/label_gate.py / geometry_gate.py",
            "any 174k artifact or benchmark",
            "any accepted record from an earlier cycle",
        ],
        "claim_ceiling": (
            "This cycle may say: the new Product head was recomputed per-artifact under the "
            "frozen instrument, X artifacts agree/disagree with the incumbent verdict, the "
            "movable-gate failure set is S (by sha set relation), the served-packet population "
            "is/is not byte-identical, and a pre-registered prediction held or did not. It may "
            "NOT say: any absolute bar is met, the packet is admissible, the map is useful to "
            "a jurist, human_gate_ready, machine_gate_ready, or that a fixture or local run is "
            "durable. human_gate_ready stays false."),
        "honest_pre_freeze_disclosure": (
            "Observed BEFORE this freeze, and disclosed: the product mount file listing, the "
            "sha manifests written here, the served-packet set relation, Product's "
            "state/product.json (state_updated_by_run, state_updated_at, cycle_status), the "
            "contents of summary_ci_39011220761.json and summary_fixture_20261017T091455Z.json, "
            "and the ACCEPTED sweep record 39020603510_sweep.json including its 0/7 and 1/9 "
            "per-packet support numbers used as the stated basis of H6. NOT observed before "
            "this freeze: any output of the frozen runner on the new head, any output of "
            "evaluation.newhead_recompute, and the contents of any offline/clickable/"
            "progressive-slice bundle payload. Those bundle roots were added to invocation B "
            "by PATH ONLY, chosen from the directory names the product ships, and their gate "
            "payloads were not read."),
        "also_executed_this_cycle_under_already_frozen_contracts": [
            "python -m evaluation.newhead_recompute --mode trigger (direction item (1) "
            "condition executed as a set relation; no frozen instrument is re-derived)",
            "python -m evaluation.lane_suite (repeat-invariance sub-check added, N and "
            "tolerance frozen in the suite source before the run)",
        ],
    }
    path = FREEZE / f"FROZEN_HYPOTHESIS_{RUN_ID}.json"
    path.write_text(json.dumps(freeze, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {path} (sha256 {sha256_file(path)})")
    print(f"population A n={len(rows_a)} sha={sha_a}")
    print(f"population B n={len(rows_b)} sha={sha_b}")
    print(f"incumbent movable-gate failures n={len(movable_fail_incumbent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())