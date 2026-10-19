"""Acceptance test (8): the integration contract for Core Product.

Product is the integrator.  This file states the exact drop-in path, the exact
additive query variants and provenance entries, the runtime cost, and the
disclosure text each outcome implies -- including the zero-row case -- plus the
claim ceiling in force.  Product decides adoption or decline under factory-wide
requirement 21 and records the decision; silent non-consumption is not permitted.
"""
from __future__ import annotations

import json
from pathlib import Path

TEAM_DIR = Path(__file__).resolve().parents[2] / "results/frontier/frontier-concept-seed-recall"

CLAIM_CEILING = (
    "No artifact may assert that a map helps a jurist, that any authority is "
    "absent from the corpus, that any frozen bar is met or moved, or that any packet "
    "is fit to serve. Usefulness remains the human product gate's question and "
    "admission remains fail-closed. Concept-coverage counts are lexical coverage of a "
    "retrieved set, not a legal conclusion; a zero count is a retrieval signal, not "
    "proof of corpus absence.")

ZERO_ROW_DISCLOSURE = (
    "A natural-language search for the missing concept returned no rows - a retrieval "
    "signal, not proof of corpus absence.")


def build(run_id: int, results: dict) -> dict:
    m = results["measurement"]
    per_unit = m["per_unit"]
    de = per_unit.get("served::de-kapitalverletzung") or {}
    v = results["verdict"]

    variants = []
    for uid, u in sorted(per_unit.items()):
        for s in u.get("A1_searches") or []:
            variants.append({
                "unit_id": uid,
                "concept": s["query_key"].split("::")[-1],
                "query": s["query"],
                "n_results": s["n_results"],
                "rows_carrying_its_concept": s.get("rows_carrying_its_concept"),
                "status": s["status"],
            })

    return {
        "schema": "frontier-concept-seed-recall/integration-contract/1",
        "team_id": "frontier-concept-seed-recall",
        "charter_version": results["charter_version"],
        "run_id": run_id,
        "outcome": v["outcome"],
        "audience": "Core Product (integrator). This is an OFFER, not an adoption. "
                    "Product records ADOPT or DECLINE under factory-wide requirement 21; "
                    "silent non-consumption is not permitted.",
        "what_this_is": (
            "ONE deterministic, additive, free, in-budget retrieval arm behind the "
            "EXISTING bundle seam. It adds natural-language full-sentence query "
            "variants for the question's own frozen under-covered core concepts and "
            "nothing else. It does NOT rebuild the retrieval adapter, the cache, "
            "pagination, normalisation, dedup, the classifier, the abstention contract, "
            "the geometry, clustering or layout, and it issues no counter-authority "
            "label."),
        "what_this_is_not": (
            "It is NOT the declined term-list layer of frontier-query-concept-recall. "
            "That layer is CLOSED, is not re-run, re-scored or improved here, and its "
            "accepted OUTCOME_B record is published beside this one, never in place of "
            "it. Its one measured bounded cause is quoted verbatim below and is not "
            "softened by this run."),
        "exact_drop_in_path": {
            "seam": "product/query/pipeline.py, the query-variant loop that already "
                    "carries provenance.query_variants[] with kind/language_filter/"
                    "terms_added/terms_added_from/note, and the searches[] list that "
                    "already records variant_id/kind/language_filter/page/offset/limit.",
            "step_1": "import frontier.frontier-concept-seed-recall.nlcs and call "
                      "build_variant(question_text, target_language, concept) once per "
                      "under-covered concept. It is pure, offline, deterministic and "
                      "issues no network and no model call.",
            "step_2": "append the returned query string to the SAME variant list the "
                      "shipped baseline already uses, with "
                      "kind='nl_concept_seeded', language_filter=null (identical to "
                      "the shipped baseline's own search), and the existing "
                      "target/page_size/max_pages_per_variant budget.",
            "step_3": "no other change. The adapter, the content-addressed cache "
                      "(same request_key derivation, verified to reproduce committed "
                      "envelope keys byte-for-byte), pagination, normalisation and dedup "
                      "are untouched.",
            "step_4": "emit the additive provenance object below. Every field is "
                      "additive and backwards-compatible with query_result_bundle v1.0 "
                      "(bundle_version, query, query_variants, answer, decisions, "
                      "clusters, relations, provenance are all unchanged in name and "
                      "meaning).",
        },
        "additive_provenance_entry": {
            "channel": "nl_concept_seeded",
            "fields": {
                "concept": "the accepted question concept this variant seeds",
                "surface_form": "that concept's own spelling in the accepted question text",
                "morph_variants": "its deterministic morphological forms",
                "template_id": "NLCS-1",
                "model_calls": 0,
                "network_calls": "inherited from the adapter, not from this layer",
            },
            "example": {
                "concept": "uberwachungspflicht",
                "surface_form": "Überwachungspflicht",
                "morph_variants": ["Überwachungspflicht", "Überwachungspflichten",
                                   "Ueberwachungspflicht", "Uberwachungspflicht"],
                "template_id": "NLCS-1",
            },
            "contract_note": "a decision that arrived through this channel keeps its "
                             "existing provenance string and gains this entry; nothing is "
                             "re-ranked out of existence, re-labelled or dropped",
        },
        "measured_effect": {
            "coverage_axis": {
                "outcome": "NO EFFECT",
                "de_kapitalverletzung_under_covered_before": ["kapitalverletzung",
                                                              "uberwachungspflicht"],
                "de_kapitalverletzung_under_covered_after": ["kapitalverletzung",
                                                             "uberwachungspflicht"],
                "rows_added_to_pool": (de.get("A1_union") or {}).get("n_rows", 0)
                                       - (de.get("A0_baseline_shipped") or {}).get(
                                           "n_rows", 0),
                "rows_carrying_the_concept_added": 0,
            },
            "recall_axis": {
                "outcome": "ONE RECOVERY",
                "cell": "corporate-criminal-liability::fr",
                "accepted_gate_before": "FAIL 0/2 (bge_BGE_142_IV_333, bger_6B_124_2016)",
                "gate_after": "PASS 1/2 (bge_BGE_142_IV_333 recovered; "
                              "bger_6B_124_2016 still missing)",
                "recovered_ids": v["headline"]["recovered_frozen_authority_ids"],
                "recovery_disclosure": v.get("recovery_disclosure"),
                "read_this_before_adopting": (
                    "The recovered authority was ALREADY present in two accepted pools "
                    "of the same benchmark -- baseline:corporate-criminal-liability:de "
                    "and counter:corporate-criminal-liability:de. 'Recovered' means "
                    "absent from THIS (fr) cell and present after the arm ran; it is NOT "
                    "a claim that the authority was unknown to the factory. The decision "
                    "that satisfies the fr cell is itself a GERMAN-language decision "
                    "(bge_142 IV 333, BGE 142 IV 333), because the accepted gate selects "
                    "a per-language cell by the QUERY's language, not by each row's own "
                    "language. Product should read this as a cross-language QUERY "
                    "robustness gain on one cell, not as one new authority entering the "
                    "corpus."),
                "independently_confirmed_by": "the accepted "
                    "evaluation.retrieval_gate.gates.evaluate on the accepted frozen "
                    "spec flipped authority::baseline_lang_recall::"
                    "corporate-criminal-liability::fr from FAIL to PASS on the same pool",
                "still_zero_cells": [
                    uid for uid, u in sorted(per_unit.items())
                    if u["kind"] == "frozen_recall"
                    and not (u.get("authority_recall") or {}).get("delta", {})
                    .get("improved")],
                "ids_still_missing_everywhere": sorted({
                    i for u in per_unit.values() if u["kind"] == "frozen_recall"
                    for i in (u.get("authority_recall") or {}).get("A1_union", {})
                    .get("missing", [])}),
            },
            "frozen_gate_nonregression": {
                "gates_passing_in_accepted_record":
                    results["frozen_gate_nonregression"]["n_passing_accepted"],
                "regressions": results["frozen_gate_nonregression"]["regressions"],
                "improvements": results["frozen_gate_nonregression"]["improvements"],
                "second_pass_replay": {
                    "n_replayed": results["frozen_gate_nonregression"]
                    ["second_pass_replay"]["n_replayed"],
                    "all_identical": results["frozen_gate_nonregression"]
                    ["second_pass_replay"]["all_identical"],
                },
                "frozen_files_modified": [],
            },
            "regression_suite": {
                "n_checks": results["regression_suite"]["n_checks"],
                "n_passed": results["regression_suite"]["n_passed"],
                "n_failed": results["regression_suite"]["n_failed"],
            },
        },
        "runtime_cost": {
            "added_searches_in_this_run": len(variants),
            "added_searches_per_question_at_adoption": "one per under-covered concept, "
                "capped at 2 in this measurement; in practice 0 for a question whose "
                "retrieved set already covers all of its concepts (fr-bail-entretien and "
                "it-responsabilita-medica fired ZERO added searches)",
            "endpoint": "https://mcp.opencaselaw.ch/api/decisions (free, no key)",
            "parameters_identical_to_baseline": "limit=50, offset=0, sort=relevance, "
                "fields=full, include_pinpoint=false, NO language filter -- the head-to-"
                "head differs in the query string and nothing else",
            "cost_per_call": "zero owner cost; no paid API, no model call, no provisioning",
            "latency_measured": {
                "per_search_budget_seconds": m["budget"]["per_search_budget_seconds"],
                "calls_over_per_search_budget":
                    m["budget"]["calls_over_per_search_budget"],
                "max_measured_call_seconds": m["budget"]["max_call_latency_seconds"],
                "per_pass": m["budget"]["per_pass"],
                "note": "the live cost was paid once, when the variant strings were "
                        "first minted; the claim-bearing replay of this run used "
                        f"network_calls={m['budget']['network_calls']}",
            },
        },
        "variants_measured": variants,
        "disclosure_text_by_outcome": {
            "if_adopted_and_the_concept_is_still_under_covered": ZERO_ROW_DISCLOSURE,
            "if_adopted_and_the_concept_is_covered": "a natural-language search for the "
                "question's missing core concept added N rows carrying that concept to "
                "the retrieved set",
            "if_declined": "Core Product records a DECLINE of the natural-language "
                "concept-seeded arm and the accepted admission-disclosure posture "
                "remains in force unchanged; the measurement stands as evidence either "
                "way and is not softened by the decline",
            "standing_disclosure": "concept-coverage counts are lexical coverage of a "
                "retrieved set, not a legal conclusion",
        },
        "the_measurement_that_most_matters_to_product": {
            "finding": "the corpus-side diagnostic contradicts the simple reading of the "
                "predecessor's accepted bounded cause",
            "predecessor_cause_verbatim": "TERM-ONLY EXPANSION QUERIES ARE TOO NARROW "
                "FOR THE OPENCASELAW RELEVANCE INDEX",
            "measured": [
                {"query": "Überwachungspflicht (the shortest possible query, A4 "
                          "diagnostic, NOT a candidate arm)",
                 "http_status": 200, "rows_returned": 50,
                 "rows_carrying_uberwachungspflicht": 28},
                {"query": "the full natural-language question PLUS the apposition "
                          "'Überwachungspflicht (Überwachungspflichten, Ueberwachungspflicht, "
                          "Uberwachungspflicht)' (A1 candidate arm)",
                 "http_status": 200, "rows_returned": 50,
                 "rows_carrying_uberwachungspflicht": 0},
            ],
            "reading": "at least 28 retrievable Swiss decisions carry "
                "'Überwachungspflicht', and the NARROWEST query finds them while the "
                "LONG natural-language query that contains the same word finds none. The "
                "gap is therefore not 'term queries are too narrow'; adding the concept "
                "to a long question SUPPRESSES it in the relevance ranking. This is a "
                "retrieval signal about query LENGTH, not a statement that the corpus "
                "lacks the concept, and it points Product at a short concept-focused "
                "query as an additional variant rather than at a longer sentence.",
            "limit": "the A4 bare-term queries are a DIAGNOSTIC, are not eligible for "
                "OUTCOME_A, are not an adoptable arm, and must not be presented as a "
                "candidate result. They were not built on; they are reported.",
        },
        "acceptance_test_8_requirements": {
            "exact_drop_in_path": True,
            "additive_query_variants_and_provenance_entries": True,
            "runtime_cost": True,
            "disclosure_text_per_outcome_including_zero_row": True,
            "claim_ceiling_in_force": True,
            "product_decides_and_records": "REQUIRED. Under factory-wide requirement 21 "
                "Product records ADOPT or DECLINE. Silent non-consumption is not "
                "permitted.",
        },
        "claim_ceiling": CLAIM_CEILING,
        "stop_rule": (
            "The charter ends at this FIRST outcome. No threshold, phrasing or prompt "
            "tuning follows. This team must NOT grow into classifier, abstention, layout "
            "or geometry work, prompt engineering, benchmark construction, a product "
            "patch or a second hypothesis. Any further work on this capability is a NEW "
            "charter with its OWN frozen rules, published beside this record."),
    }


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", required=True)
    args = ap.parse_args(argv)
    res = json.loads((TEAM_DIR / f"harness_results_{args.run_id}.json")
                     .read_text(encoding="utf-8"))
    out = TEAM_DIR / f"integration_contract_{args.run_id}.json"
    out.write_text(json.dumps(build(int(args.run_id), res), ensure_ascii=False,
                              indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(str(out))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())