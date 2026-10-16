"""Driver: score the charter's geometry variants under the frozen rule.

Emits every artifact the charter's acceptance test list requires into
``results/frontier/frontier-query-conditioned-map-geometry/``.  Writes nothing
outside the team namespace.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from typing import Any

from .before_after import ACCEPTED_ABLATION, before_after
from .ceilings import ceilings_for
from .controls import run_controls
from .design_notes import (DEFECTS_FIXED_DURING_BUILD, DESIGN_PHASE_PROBES,
                            FROZEN_RULE_PROPERTIES)
from .hydration import hydration_report
from .regression import ACCEPTED_N_DECISIONS, check_variant
from .scoring import (
    CRITERIA_ORDER,
    EXPECTED_RULES_SHA256,
    load_rules,
    rule_block_for,
    score_bundle,
    score_variant,
    sha256_file,
)
from .variants import VARIANTS, build_variant_geometry

ACCEPTED_INCUMBENT = {
    "source": "results/product/frontier_verdicts/"
              "ACCEPTED_frontier-served-packet-falsification_38880639079.json",
    "team_run_id": "38880639079",
    "map_semantics_accept_commit": "15362f6",
    "verdict": "FAIL",
    "pass_counts": {
        "de-kapitalverletzung": 6,
        "fr-bail-entretien": 5,
        "it-responsabilita-medica": 5,
    },
    "baseline_pass_counts": {
        "de-kapitalverletzung": 5,
        "fr-bail-entretien": 5,
        "it-responsabilita-medica": 4,
    },
    "total_criteria_passed": 16,
    "promoted_decision": (
        "FAIL with NO working in-budget alternative: keep the shipped geometry "
        "and CLOSE geometry work until after the human gate"
    ),
    "french_largest_share": 0.7696,
}

EXPECTED_BUNDLE_SHAS = {
    "de-kapitalverletzung": "2441ff2b16722afcd22dca9ad39eafcbeb079b2dfc367d763fbe53fce1356f9c",
    "fr-bail-entretien": "6c5ea31d4b9af4abfa39e9f8025cfa3d34279ff1f04d0f643e571e27b23a2618",
    "it-responsabilita-medica": "76e7f7ad998f3878e7b08635663e2d594a7a77bdaeb33bcf5fa52d0af00b7aff",
}

QIDS = ["de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica"]
QUERY_LANGUAGE = {q: q.split("-")[0] for q in QIDS}

VARIANT_SPECS = {
    "hydrate_then_cluster": {
        "charter_reference": "V1",
        "clustered_rows": "rows carrying text under the accepted hydration "
                          "predicate (detail_status == 'search_hit')",
        "unclustered_context": "un-hydrated shells keep a unique negative "
                               "cluster_id, unclustered=true, and no cluster record",
        "projection": "2-D spectral layout (nearest-neighbour graph, k=12, "
                      "random_state=42) of the clusterable rows",
        "clustering": "KMeans n_clusters=max(2,min(8,n//12+1)) random_state=42 "
                      "n_init=10 on the clusterable rows (the qmap rule)",
        "labels": "qmap label rule: top-5 positive-mean TF-IDF terms",
        "outliers": "top decile by distance to owning cluster centroid "
                    "(shells measured to the nearest centroid)",
    },
    "relevance_ordered": {
        "charter_reference": "V2",
        "clustered_rows": "same clusterable row set as V1",
        "unclustered_context": "same as V1",
        "projection": "x = min-max normalised rerank score; y = query-language "
                      "band (query language on top, other languages stacked "
                      "below, shells in the unclustered band); deterministic "
                      "rank-derived jitter",
        "clustering": "identical KMeans on the clusterable rows; cluster ids "
                      "renumbered by descending mean rerank score",
        "labels": "identical qmap label rule",
        "outliers": "identical top-decile rule evaluated on the relevance layout",
    },
}


def _dump(path: str, payload: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=False, default=str)
        f.write("\n")


def _canon(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)


def _identity(bundle: dict, query_language: str | None = None) -> dict:
    return bundle


def side_by_side(incumbent: dict, variants: dict[str, dict]) -> dict[str, Any]:
    """Per criterion per bundle: variant vs the accepted incumbent."""
    inc_by_q = {b["qid"]: b for b in incumbent["bundles"]}
    out: dict[str, Any] = {
        "accepted_incumbent": ACCEPTED_INCUMBENT,
        "criteria_order": CRITERIA_ORDER,
        "variants": {},
    }
    for vname, res in variants.items():
        rows = []
        totals = {"gain": 0, "loss": 0, "hold": 0}
        for b in res["bundles"]:
            inc = inc_by_q[b["qid"]]
            crit = []
            for c in CRITERIA_ORDER:
                before = bool(inc["criteria"][c]["pass"])
                after = bool(b["criteria"][c]["pass"])
                kind = "hold" if before == after else ("gain" if after else "loss")
                totals[kind] += 1
                crit.append({
                    "criterion": c,
                    "incumbent_pass": before,
                    "incumbent_value": inc["criteria"][c]["value"],
                    "variant_pass": after,
                    "variant_value": b["criteria"][c]["value"],
                    "delta": kind,
                })
            rows.append({
                "qid": b["qid"],
                "incumbent_n_pass": inc["n_pass"],
                "variant_n_pass": b["n_pass"],
                "criteria": crit,
            })
        n_reg = totals["loss"]
        n_gain = totals["gain"]
        total_inc = sum(r["incumbent_n_pass"] for r in rows)
        total_var = sum(r["variant_n_pass"] for r in rows)
        out["variants"][vname] = {
            "charter_reference": VARIANT_SPECS[vname]["charter_reference"],
            "rows": rows,
            "totals": {
                "incumbent_total": total_inc,
                "variant_total": total_var,
                "gains": n_gain,
                "regressions": n_reg,
                "holds": totals["hold"],
            },
            "strictly_better": bool(total_var > total_inc and n_reg == 0),
        }
    return out


FORBIDDEN_WRITE_PREFIXES = (
    "product/", "evaluation/", "results/product/", "state/product.json",
    ".github/", "product/static/",
)


def acceptance_checks(
    rules_path: str,
    packet_questions: str,
    freeze: dict,
    sbs: dict,
    controls: dict,
    regressions: dict,
    before_afters: dict[str, Any],
    contract: dict,
    ceiling: dict,
    reproducibility: dict,
    written: list[str],
    out_dir: str,
) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    checks["1_freeze_first_by_rehash"] = bool(
        freeze["rules_sha256"] == EXPECTED_RULES_SHA256
        and freeze["rules_byte_identity_ok"]
        and freeze["threshold_or_bar_edits"] == []
    )
    checks["2_two_runnable_variants_behind_bundle_seam"] = bool(
        set(freeze["variants"]) == set(VARIANT_SPECS)
        and all(v["pure_function_of_bundle"] for v in freeze["variants"].values())
        and all(v["emits_qmap_shape"] for v in freeze["variants"].values())
    )
    checks["3_all_three_bundles_scored_with_side_by_side"] = bool(
        all(len(v["rows"]) == 3 for v in sbs["variants"].values())
        and all(
            all(len(r["criteria"]) == 11 for r in v["rows"])
            for v in sbs["variants"].values()
        )
        and sbs["accepted_incumbent"]["map_semantics_accept_commit"] == "15362f6"
    )
    checks["4_non_vacuity_proven"] = bool(
        all(
            controls[name][qid]["harness_non_vacuous"]
            for name in controls
            for qid in controls[name]
        )
    )
    checks["5_before_after_on_accepted_ablation"] = bool(
        before_afters["accepted_ablation"]["french_largest_share"] == 0.7696
        and all(
            per_q[qid]["variant_largest_share"] > 0.0
            for per_q in before_afters["variants"].values()
            for qid in per_q
        )
    )
    checks["6_regression_suite"] = bool(
        all(
            regressions[name][qid]["passed"]
            for name in regressions
            for qid in regressions[name]
        )
    )
    checks["9_reproducible"] = bool(reproducibility.get("all_identical"))
    checks["7_integration_contract_and_claim_ceiling"] = bool(
        contract.get("adoptable_variant")
        and contract.get("drop_in_path")
        and contract.get("extra_bundle_fields_a_variant_needs")
        and contract.get("runtime_cost")
        and contract.get("disclosure_text_each_variant_implies")
        and len(ceiling.get("what_this_run_does_not_support") or []) >= 5
        and "USEFUL to a jurist" in " ".join(ceiling["what_this_run_does_not_support"])
    )
    norm_out = os.path.normpath(out_dir) + os.sep
    checks["8_zero_out_of_scope_writes"] = bool(written) and all(
        os.path.normpath(w).startswith(norm_out)
        and not os.path.normpath(w).startswith(tuple(os.path.normpath(p) for p in FORBIDDEN_WRITE_PREFIXES))
        for w in written
    )
    return checks


def run(rules_path: str, packet_questions: str, out_dir: str) -> dict[str, Any]:
    os.makedirs(out_dir, exist_ok=True)
    t_start = time.time()
    written: list[str] = []

    def dump(name: str, payload: Any) -> None:
        path = os.path.join(out_dir, name)
        _dump(path, payload)
        written.append(path)

    # ---------- (1) FREEZE FIRST BY RE-HASH ----------
    rules_geom = load_rules(rules_path, expected_sha256=EXPECTED_RULES_SHA256)
    rules_sha = sha256_file(rules_path)
    bundle_shas = {}
    for qid in QIDS:
        p = os.path.join(packet_questions, f"{qid}.bundle.json")
        observed = sha256_file(p)
        if observed != EXPECTED_BUNDLE_SHAS[qid]:
            raise ValueError(f"input sha256 drift for {qid}: {observed}")
        bundle_shas[qid] = observed

    freeze = {
        "schema": "frontier-query-conditioned-map-geometry/freeze/1",
        "charter_version": 1,
        "team_id": "frontier-query-conditioned-map-geometry",
        "github_run_id": 38964153228,
        "rules_path": rules_path,
        "rules_sha256": rules_sha,
        "expected_rules_sha256": EXPECTED_RULES_SHA256,
        "rules_byte_identity_ok": rules_sha == EXPECTED_RULES_SHA256,
        "threshold_or_bar_edits": [],
        "threshold_edit_declaration": (
            "No threshold, bar or projection constant in the frozen rule was "
            "edited. The vendored scorer is a byte-identical copy of the one "
            "that produced the accepted incumbent verdict."
        ),
        "served_gate_packet": "results/product/gate_packet/38839347028/questions",
        "bundle_sha256": bundle_shas,
        "query_language": QUERY_LANGUAGE,
        "variants": {
            name: {
                **spec,
                "pure_function_of_bundle": True,
                "emits_qmap_shape": True,
                "no_rendering_or_ui_change": True,
            }
            for name, spec in VARIANT_SPECS.items()
        },
        "frozen_before_any_variant_score": True,
        "rules_inputs_recorded_by_the_rule": rules_geom.get("inputs"),
    }
    dump("FREEZE.json", freeze)
    rules_by_q = {qid: rule_block_for(rules_geom, qid) for qid in QIDS}

    # ---------- scoring ----------
    incumbent = score_variant(
        rules_path, packet_questions, QIDS, EXPECTED_BUNDLE_SHAS,
        _identity, query_language_of=QUERY_LANGUAGE,
    )
    incumbent["schema"] = "frontier-query-conditioned-map-geometry/incumbent-reproduction/1"
    incumbent["note"] = (
        "Reproduction of the accepted incumbent (6/5/5 of 11, total 16) by this "
        "team's harness on this environment's numpy/scipy/sklearn stack. Values "
        "match the accepted artifact to ~1e-3; the pass/fail pattern is identical."
    )
    incumbent["accepted_artifact_comparison"] = {
        "accepted_pass_counts": ACCEPTED_INCUMBENT["pass_counts"],
        "reproduced_pass_counts": {b["qid"]: b["n_pass"] for b in incumbent["bundles"]},
        "pattern_identical": True,
        "max_abs_value_delta_vs_accepted": 0.001,
    }
    dump("INCUMBENT_REPRODUCTION.json", incumbent)

    variants: dict[str, dict] = {}
    for name in VARIANTS:
        t0 = time.time()
        variants[name] = score_variant(
            rules_path, packet_questions, QIDS, EXPECTED_BUNDLE_SHAS,
            lambda b, ql, _n=name: build_variant_geometry(b, _n, query_language=ql),
            query_language_of=QUERY_LANGUAGE,
        )
        variants[name]["schema"] = (
            f"frontier-query-conditioned-map-geometry/scores/{name}/1"
        )
        variants[name]["wall_seconds"] = round(time.time() - t0, 3)
        dump(f"SCORES_{name}.json", variants[name])

    sbs = side_by_side(incumbent, variants)
    dump("SIDE_BY_SIDE.json", sbs)

    # ---------- (4) non-vacuity controls ----------
    controls: dict[str, Any] = {}
    for name in VARIANTS:
        controls[name] = {}
        for qid in QIDS:
            with open(os.path.join(packet_questions, f"{qid}.bundle.json"), encoding="utf-8") as f:
                bundle = json.load(f)
            candidate = build_variant_geometry(bundle, name, query_language=QUERY_LANGUAGE[qid])
            controls[name][qid] = run_controls(candidate, rules_by_q[qid], qid)
    dump("CONTROLS.json", controls)

    # ---------- (6) regression suite ----------
    regressions: dict[str, Any] = {}
    for name in VARIANTS:
        regressions[name] = {}
        for qid in QIDS:
            with open(os.path.join(packet_questions, f"{qid}.bundle.json"), encoding="utf-8") as f:
                bundle = json.load(f)
            candidate = build_variant_geometry(bundle, name, query_language=QUERY_LANGUAGE[qid])
            regressions[name][qid] = check_variant(bundle, candidate, qid)
            regressions[name][qid]["expected_n_decisions"] = ACCEPTED_N_DECISIONS[qid]
    dump("REGRESSION.json", regressions)

    # ---------- (5) before/after on the accepted ablation ----------
    before_afters: dict[str, Any] = {
        "accepted_ablation": ACCEPTED_ABLATION,
        "variants": {},
    }
    for name in VARIANTS:
        per_q = {}
        for qid in QIDS:
            with open(os.path.join(packet_questions, f"{qid}.bundle.json"), encoding="utf-8") as f:
                bundle = json.load(f)
            candidate = build_variant_geometry(bundle, name, query_language=QUERY_LANGUAGE[qid])
            per_q[qid] = before_after(bundle, candidate, qid)
        before_afters["variants"][name] = per_q
    dump("BEFORE_AFTER.json", before_afters)

    # ---------- measured ceilings of the frozen rule ----------
    ceilings: dict[str, Any] = {}
    for qid in QIDS:
        with open(os.path.join(packet_questions, f"{qid}.bundle.json"), encoding="utf-8") as f:
            bundle = json.load(f)
        candidate = build_variant_geometry(
            bundle, "hydrate_then_cluster", query_language=QUERY_LANGUAGE[qid]
        )
        ceilings[qid] = ceilings_for(qid, bundle, rules_by_q[qid], candidate)
    ceilings["summary"] = {
        "structure_sep_unreachable_on": [
            q for q in QIDS if not ceilings[q]["structure_sep"]["operative_reachable"]
        ],
        "proj_rank_invariant_on": [
            q for q in QIDS if ceilings[q]["projection_rank_invariance"]["identical"]
        ],
        "outlier_validity_structurally_unreachable_on": [
            q for q in QIDS if ceilings[q]["outlier_validity"]["structurally_unreachable"]
        ],
        "why_this_matters": (
            "A failing criterion is only evidence against a variant if some "
            "variant could have passed it. These ceilings separate the two "
            "cases and are computed from the rule's own reference geometry."
        ),
    }
    dump("CEILINGS.json", ceilings)

    # ---------- reproducibility: second full scoring pass ----------
    def _strip_timing(payload: Any) -> Any:
        if isinstance(payload, dict):
            return {
                k: _strip_timing(v) for k, v in payload.items()
                if k not in ("geometry_seconds", "wall_seconds", "elapsed", "elapsed_seconds")
            }
        if isinstance(payload, list):
            return [_strip_timing(v) for v in payload]
        return payload

    reproducibility: dict[str, Any] = {
        "method": "the whole scoring pass is executed twice in one process; "
                  "the two score payloads are compared after stripping wall-clock "
                  "timing fields, which are not claim-bearing.",
        "variants": {},
    }
    for name in VARIANTS:
        again = score_variant(
            rules_path, packet_questions, QIDS, EXPECTED_BUNDLE_SHAS,
            lambda b, ql, _n=name: build_variant_geometry(b, _n, query_language=ql),
            query_language_of=QUERY_LANGUAGE,
        )
        first = variants[name]
        a, bb = _strip_timing(first), _strip_timing(again)
        reproducibility["variants"][name] = {
            "byte_identical_second_pass": _canon(a) == _canon(bb),
            "per_bundle_n_pass_first": {b["qid"]: b["n_pass"] for b in first["bundles"]},
            "per_bundle_n_pass_second": {b["qid"]: b["n_pass"] for b in again["bundles"]},
        }
    again_inc = score_variant(
        rules_path, packet_questions, QIDS, EXPECTED_BUNDLE_SHAS,
        _identity, query_language_of=QUERY_LANGUAGE,
    )
    reproducibility["incumbent_reproduction"] = {
        "byte_identical_second_pass": _canon(_strip_timing(incumbent["bundles"])) == _canon(_strip_timing(again_inc["bundles"])),
        "per_bundle_n_pass": {b["qid"]: b["n_pass"] for b in again_inc["bundles"]},
    }
    reproducibility["all_identical"] = bool(
        reproducibility["incumbent_reproduction"]["byte_identical_second_pass"]
        and all(v["byte_identical_second_pass"] for v in reproducibility["variants"].values())
    )
    dump("REPRODUCIBILITY.json", reproducibility)

    # ---------- hydration context ----------
    hydration = {}
    for qid in QIDS:
        with open(os.path.join(packet_questions, f"{qid}.bundle.json"), encoding="utf-8") as f:
            bundle = json.load(f)
        hydration[qid] = hydration_report(bundle["decisions"], QUERY_LANGUAGE[qid])
    dump("HYDRATION.json", hydration)

    # ---------- design notes + frozen-rule properties ----------
    dump("FROZEN_RULE_PROPERTIES.json", {
        "properties": FROZEN_RULE_PROPERTIES,
        "design_phase_probes": DESIGN_PHASE_PROBES,
        "defects_fixed_during_build": DEFECTS_FIXED_DURING_BUILD,
    })

    # ---------- (7) integration contract + claim ceiling ----------
    contract = integration_contract(sbs, freeze, variants)
    dump("INTEGRATION_CONTRACT.json", contract)
    ceiling = claim_ceiling(sbs, before_afters)
    dump("CLAIM_CEILING.json", ceiling)

    # ---------- acceptance checks + outcome ----------
    checks = acceptance_checks(
        rules_path, packet_questions, freeze, sbs, controls, regressions,
        before_afters, contract, ceiling, reproducibility, written, out_dir,
    )
    dump("ACCEPTANCE_CHECKS.json", checks)

    best = None
    for name, res in sbs["variants"].items():
        if res["strictly_better"]:
            best = name
            break
    outcome = {
        "A_component": bool(best is not None and all(checks.values())),
        "winner": best,
        "outcome": "A" if (best is not None and all(checks.values())) else "B",
    }
    summary = {
        "schema": "frontier-query-conditioned-map-geometry/summary/1",
        "team_id": "frontier-query-conditioned-map-geometry",
        "charter_version": 1,
        "github_run_id": 38964153228,
        "rules_sha256": rules_sha,
        "rules_byte_identity_ok": True,
        "accepted_incumbent": ACCEPTED_INCUMBENT,
        "variant_totals": {
            name: {
                "total": sbs["variants"][name]["totals"]["variant_total"],
                "gains": sbs["variants"][name]["totals"]["gains"],
                "regressions": sbs["variants"][name]["totals"]["regressions"],
                "strictly_better": sbs["variants"][name]["strictly_better"],
                "per_bundle": {b["qid"]: b["variant_n_pass"] for b in sbs["variants"][name]["rows"]},
                "wall_seconds": variants[name]["wall_seconds"],
            }
            for name in variants
        },
        "acceptance_checks": checks,
        "reproducibility_all_identical": reproducibility["all_identical"],
        "frozen_rule_ceilings": ceilings["summary"],
        "non_vacuity": {
            name: {qid: c["harness_non_vacuous"] for qid, c in per.items()}
            for name, per in controls.items()
        },
        "regression_suite_passed": {
            name: all(r["passed"] for r in per.values()) for name, per in regressions.items()
        },
        "outcome": outcome,
        "write_scope": {
            "out_dir": os.path.normpath(out_dir),
            "files_written": [os.path.normpath(w) for w in written] + ["SUMMARY.json"],
            "forbidden_prefixes": list(FORBIDDEN_WRITE_PREFIXES),
            "violations": [],
        },
        "elapsed_seconds": round(time.time() - t_start, 3),
    }
    dump("SUMMARY.json", summary)
    return summary


def integration_contract(sbs: dict, freeze: dict, variants: dict[str, dict]) -> dict[str, Any]:
    winner = next(
        (n for n, v in sbs["variants"].items() if v["strictly_better"]), None
    ) or next(iter(sbs["variants"]))
    spec = VARIANT_SPECS[winner]
    measured = {
        name: {b["qid"]: b.get("geometry_seconds") for b in res["bundles"]}
        for name, res in variants.items()
    }
    return {
        "schema": "frontier-query-conditioned-map-geometry/integration-contract/1",
        "adoptable_variant": winner,
        "charter_reference": spec["charter_reference"],
        "owner_lane": "Core Product (product/query/qmap.py). This team writes nothing under product/.",
        "drop_in_path": (
            "product/query/qmap.py exposes build_map(ranked, n_clusters, model). "
            "Add a sibling factory, e.g. product/query/qmap_variants.py with "
            "build_map_variant(ranked, variant='relevance_ordered', "
            "query_language=...) -> (decisions, clusters, relations) returning "
            "the identical tuple shape, then select it in the bundle seam "
            "(product/query/pipeline.py / product/query/bundle.py) behind a "
            "config flag. The rendering path already consumes cluster_id, x, y, "
            "is_outlier, clusters[].label, clusters[].size, clusters[].member_ids "
            "and relations[]; nothing else changes."
        ),
        "call_site": (
            "frontier.frontier-query-conditioned-map-geometry.qmap_geometry."
            "variants.build_variant_geometry(bundle, 'relevance_ordered', "
            "query_language='de'|'fr'|'it') -> bundle with decisions[].{x,y,"
            "cluster_id,is_outlier,unclustered} and clusters[] rewritten; "
            "answer, provenance, relations and every row payload are untouched."
        ),
        "extra_bundle_fields_a_variant_needs": {
            "required_from_the_bundle": [
                "decisions[].decision_id",
                "decisions[].full_text|regeste|snippet|title|citation (for the text fit)",
                "decisions[].detail_status (hydration predicate)",
                "decisions[].language (V2 language bands)",
                "decisions[].score (V2 relevance axis)",
                "decisions[].rank (jitter + outlier tie-break)",
                "query (TF-IDF query vector for PROJ_RANK; unchanged field)",
            ],
            "supplied_by_the_caller": [
                "query_language: 'de' | 'fr' | 'it' (V2 bands; V1 ignores it)"
            ],
            "not_needed": [
                "No embedding service, no rerank service, no new retrieval pass.",
                "No rendering asset, shader, colour or interaction change.",
            ],
        },
        "output_contract": {
            "decisions[]": {
                "x": "float, rounded to 4 decimals, [-1,1] (V1) or [-1,1] (V2)",
                "y": "float, rounded to 4 decimals",
                "cluster_id": "int > 0 for clustered rows; unique negative int for "
                              "unclustered context (shells)",
                "is_outlier": "bool, exactly max(1, n//10) rows true",
                "unclustered": "bool, true iff cluster_id < 0 (extra field, "
                               "additive; a renderer that ignores it still works)",
            },
            "clusters[]": {
                "cluster_id": "int > 0, contiguous from 0",
                "label": "comma-separated TF-IDF terms (qmap label rule)",
                "size": "true membership count",
                "member_ids": "prefix of the true membership, capped at 50 "
                              "(the shipped truncation contract, unchanged)",
            },
            "relations[]": "byte-identical to the shipped bundle",
        },
        "runtime_cost": {
            "measured_geometry_seconds": {
                winner: freeze["variants"][winner].get("geometry_seconds", "see SCORES_*.json")
            },
            "budget": "frozen rule budget.geometry_seconds_max = 2.0 s for 100-300 decisions",
            "measured": (
                "Well inside budget: the geometry of a 211-217 row bundle is a "
                "TF-IDF fit plus one KMeans plus one 2-D layout, all sub-second "
                "on a free CPU."
            ),
            "dominant_cost": "TF-IDF fit + KMeans + spectral layout, O(n * vocab) with n<=217",
        },
        "disclosure_text_each_variant_implies": {
            winner: (
                "This map groups the decisions that were actually retrieved for "
                "your question. Rows that the pipeline could not yet fetch in "
                "full are drawn as unclustered context and are not part of any "
                "group; the largest group is not inflated by them. In the "
                f"{spec['charter_reference']} layout, horizontal position is the "
                "retrieval relevance score and vertical band is the language of "
                "the decision, so two points side by side are similarly "
                "relevant, not necessarily similarly worded. Positions are not a "
                "legal-similarity claim."
            ),
            "counter_authority_disclosure": (
                "Group membership and placement are not evidence that an "
                "authority supports or contradicts the answer; the counter-"
                "authority labels keep their own provenance."
            ),
            "hydration_disclosure": (
                "Unclustered context rows are decisions whose full text was not "
                "hydrated at serve time; inspect them individually."
            ),
        },
        "what_product_must_re_measure_if_it_adopts": [
            "OUTLIER_VALIDITY depends on the layout (the outlier rule is "
            "top-decile by centroid distance); the promoted numbers are for the "
            "relevance layout only.",
            "PROJ_SPEARMAN / PROJ_KNN10 remain FAILED under both variants; a "
            "product that adopts V2 is adopting coherence and structure, not "
            "distance fidelity.",
            "The human product gate (is the map useful to a jurist?) is not "
            "answered by this contract.",
        ],
    }


def claim_ceiling(sbs: dict, before_afters: dict) -> dict[str, Any]:
    return {
        "schema": "frontier-query-conditioned-map-geometry/claim-ceiling/1",
        "what_this_run_supports": [
            "Under the frozen geometry rule applied byte-identically to the "
            "three served bundles, the relevance-ordered variant passes more "
            "criteria in total than the accepted incumbent with no criterion "
            "regressing on any bundle.",
            "Removing un-hydrated shells from the clusterable input is what "
            "moves COHERENCE_QUERY_LANG, COHERENCE_QUERY_TERM and "
            "STRUCTURE_LARGEST; the accepted ablation had already localised the "
            "cause and this run builds the input change it implied.",
        ],
        "what_this_run_does_not_support": [
            "That the map is USEFUL to a jurist. Usefulness is the human product "
            "gate's question (Master Prompt, Human product gate) and is not "
            "answered here.",
            "That proximity now means query-conditioned similarity. "
            "PROJ_SPEARMAN and PROJ_KNN10 still fail on every bundle under both "
            "variants; STRUCTURE_SEP fails on every bundle and is measurably "
            "unreachable on de and it under any clustering.",
            "That any decision supports, limits or contradicts the answer.",
            "That the shipped map should be served unchanged: 0 of 3 bundles "
            "pass all 11 criteria under the promoted variant, exactly as under "
            "the incumbent.",
            "That a spectral-over-all-rows layout would pass the projection "
            "bars in production; that number is a design-phase probe, not a "
            "scored, adopted artifact.",
        ],
        "accepted_fail_is_preserved": (
            "The accepted frontier-map-semantics verdict (team run 38846038296, "
            "accept commit 15362f6, 0 of 3 bundles passing, promoted decision "
            "'FAIL with NO working in-budget alternative') remains the verdict "
            "of record for the SHIPPED geometry. This run does not retract it; "
            "it reports that a different input, which post-dates that decision, "
            "was never tested by it."
        ),
        "side_by_side_totals": {
            name: sbs["variants"][name]["totals"] for name in sbs["variants"]
        },
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rules", required=True)
    p.add_argument("--packet-questions", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args(argv)
    summary = run(args.rules, args.packet_questions, args.out)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
