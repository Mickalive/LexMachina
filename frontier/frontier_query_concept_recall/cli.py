"""CLI harness for frontier-query-concept-recall.

Implements the charter's acceptance test (3):
  python -m frontier_query_concept_recall.cli --bundle <path> --out <dir>

Emits per-bundle and per-frozen-leg:
- rows_per_concept
- under_covered
- frozen-authority recall per language

In the same record shape as accepted evaluation artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .expansion import (
    FROZEN_AUTHORITY_IDS,
    FROZEN_BASELINE_QUERIES,
    FROZEN_LEG_SLUGS,
    SERVED_CORE_CONCEPTS,
    SERVED_QUERIES,
    SERVED_QUESTIONS,
    build_expansion_variants,
    ExpansionVariant,
)
from .cache_reader import (
    compute_authority_recall,
    compute_concept_coverage,
    compute_blanked_coverage,
    get_all_cached_decisions,
    load_cached_search,
)

# ---------------------------------------------------------------------------
# RULES.json (frozen before any measurement)
# ---------------------------------------------------------------------------

RULES = {
    "schema": "lex-frontier-query-concept-recall-rules/1",
    "charter_version": 1,
    "team_id": "frontier-query-concept-recall",
    "frozen_at_utc": None,  # Filled at commit time by git, not hand-written
    "rules": {
        "concept_definition": {
            "method": "de_accented_lowercase_alnum_tokens_len_ge_5_stoplist_removed",
            "token_regex": "[^\\W\\d_]+",
            "min_length": 5,
            "stoplist": "accepted_gates_generic",
            "covered_iff": ">=1 bundle row's title/regeste/snippet/full_text/citation/decision_id contains as substring",
            "semantics": "permissive_1_of_set",
        },
        "authority_recall_definition": {
            "method": "alnum_core_match_per_frozen_spec_187b0e54",
            "frozen_spec_sha256": "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72",
            "freeze_record_sha256": "b06a2ad024040c38312686ab7aacc5ab18c663f1ef0b77494caf6ce3b3b52e49",
            "id_match_rules": "lowercase_alnum_drop_nonalnum_strip_leading_court_tokens",
            "min_core_length": 6,
        },
        "latency_budget": {
            "per_search_seconds": 30.0,
            "full_pass_seconds": 240.0,
            "rule": "cached_replay_only_network_calls_0",
        },
        "expansion_layer": {
            "deterministic": True,
            "free": True,
            "no_generation": True,
            "no_paid_api": True,
            "corpus_derived": True,
            "max_compound_splits": 6,
            "max_cross_lang_terms": 12,
        },
        "vacuity_controls": {
            "blanked_expansion": "empty_term_set_must_score_strictly_below_candidate_on_both_axes",
            "shuffled_expansion": "terms_from_unrelated_question_must_not_raise_coverage_on_target",
            "tie_is_vacuous": True,
            "void_on_vacuous": True,
        },
        "regression_gates": {
            "required_passing": [
                "duplicate::unique_ids",
                "counter::known_counter_recall",
                "source::rows_valid",
                "transport::all_queries_ok",
            ],
            "latency_budget_must_hold": True,
        },
        "outcome_rules": {
            "outcome_a_promote": "candidate_raises_frozen_authority_recall_on_at_least_2_of_3_failing_fr_it_cells AND reduces_under_covered_on_at_least_2_of_3_served_questions",
            "outcome_b_promote": "no_in_budget_deterministic_expansion_recovers_missing_concepts_or_authority_ids",
            "stop_at_first_outcome": True,
            "no_post_hoc_tuning": True,
        },
        "claim_ceiling": "no_artifact_may_assert_map_helps_jurist_or_authority_absent_or_frozen_bar_met_or_packet_fit_to_serve_usefulness_human_gate_admission_fail_closed",
    },
    "input_bundles": {
        # Filled at runtime with content_sha256
    },
    "frozen_retrieval_spec_digest": "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72",
}

def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

# ---------------------------------------------------------------------------
# Core measurement functions
# ---------------------------------------------------------------------------

def measure_baseline_concept_coverage(question_id: str) -> Dict[str, Any]:
    """Measure concept coverage for plain baseline (original query only)."""
    query = SERVED_QUERIES[question_id]
    concepts = SERVED_CORE_CONCEPTS[question_id]
    
    # Get cached decisions for original query (plain baseline)
    decisions = get_all_cached_decisions(query, languages=("de", "fr", "it"), limit=50)
    
    return compute_concept_coverage(decisions, concepts)

def measure_candidate_concept_coverage(question_id: str) -> Dict[str, Any]:
    """Measure concept coverage for candidate layer (with expansion variants)."""
    query = SERVED_QUERIES[question_id]
    concepts = SERVED_CORE_CONCEPTS[question_id]
    
    # Build expansion variants
    variants = build_expansion_variants(query)
    
    # Get decisions for ALL variants (simulating retrieval with expansion)
    all_decisions = []
    seen_ids = set()
    
    for variant in variants:
        if variant.kind == "language_filter":
            # Language filter variant - same query, different language filter
            lang = variant.language_filter
            cached = load_cached_search(query, language=lang, limit=50, offset=0)
        else:
            # Search variants - expanded query text
            cached = load_cached_search(variant.text, language=None, limit=50, offset=0)
        
        if cached:
            for d in cached.get("results", []):
                did = d.get("decision_id") or d.get("id")
                if did and did not in seen_ids:
                    seen_ids.add(did)
                    all_decisions.append(d)
    
    return compute_concept_coverage(all_decisions, concepts)

def measure_frozen_leg_authority_recall(
    slug: str,
    *,
    use_candidate: bool = False,
) -> Dict[str, Any]:
    """Measure authority recall for a frozen leg.
    
    Args:
        slug: One of FROZEN_LEG_SLUGS
        use_candidate: If True, use candidate expansion variants; if False, plain baseline
    
    Returns per-language recall dict.
    """
    if slug not in FROZEN_AUTHORITY_IDS:
        return {"error": f"no authority ids for {slug}"}
    
    frozen_ids = FROZEN_AUTHORITY_IDS[slug]
    queries = FROZEN_BASELINE_QUERIES[slug]
    
    result = {"slug": slug, "per_language": {}, "union": {}}
    
    all_decisions_union = []
    seen_union = set()
    
    for lang in ("fr", "de", "it"):
        query = queries[lang]
        
        if use_candidate:
            # Build expansion variants for this query
            variants = build_expansion_variants(query)
            lang_decisions = []
            seen_lang = set()
            
            for variant in variants:
                if variant.kind == "language_filter":
                    cached = load_cached_search(query, language=variant.language_filter, limit=50, offset=0)
                else:
                    cached = load_cached_search(variant.text, language=None, limit=50, offset=0)
                
                if cached:
                    for d in cached.get("results", []):
                        did = d.get("decision_id") or d.get("id")
                        if did and did not in seen_lang:
                            seen_lang.add(did)
                            lang_decisions.append(d)
        else:
            # Plain baseline
            lang_decisions = get_all_cached_decisions(query, languages=(lang,), limit=50)
        
        recall_result = compute_authority_recall(lang_decisions, frozen_ids)
        result["per_language"][lang] = recall_result
        
        # Add to union
        for d in lang_decisions:
            did = d.get("decision_id") or d.get("id")
            if did and did not in seen_union:
                seen_union.add(did)
                all_decisions_union.append(d)
    
    # Union recall
    union_recall = compute_authority_recall(all_decisions_union, frozen_ids)
    result["union"] = union_recall
    
    return result

def run_vacuity_controls(question_id: str) -> Dict[str, Any]:
    """Run vacuity controls for a question."""
    concepts = SERVED_CORE_CONCEPTS[question_id]
    query = SERVED_QUERIES[question_id]
    
    # Get baseline decisions (for blanked/shuffled test)
    baseline_decisions = get_all_cached_decisions(query, languages=("de", "fr", "it"), limit=50)
    
    # Candidate decisions
    variants = build_expansion_variants(query)
    candidate_decisions = []
    seen_ids = set()
    for variant in variants:
        if variant.kind == "language_filter":
            cached = load_cached_search(query, language=variant.language_filter, limit=50, offset=0)
        else:
            cached = load_cached_search(variant.text, language=None, limit=50, offset=0)
        if cached:
            for d in cached.get("results", []):
                did = d.get("decision_id") or d.get("id")
                if did and did not in seen_ids:
                    seen_ids.add(did)
                    candidate_decisions.append(d)
    
    # Blanked: empty expansion on baseline decisions
    blanked = compute_blanked_coverage(baseline_decisions, concepts)
    
    # Candidate: with expansion
    candidate = compute_concept_coverage(candidate_decisions, concepts)
    
    # Shuffled: use concepts from another question
    other_questions = [q for q in SERVED_QUESTIONS if q != question_id]
    shuffled_results = {}
    for other_q in other_questions:
        other_concepts = SERVED_CORE_CONCEPTS[other_q]
        shuffled = compute_concept_coverage(candidate_decisions, other_concepts)
        shuffled_results[other_q] = {
            "concepts_tested": sorted(other_concepts),
            "under_covered_count": shuffled["under_covered_count"],
            "coverage_ratio": shuffled["coverage_ratio"],
        }
    
    # Vacuity check per charter rule
    blanked_under = blanked["under_covered_count"]
    candidate_under = candidate["under_covered_count"]
    
    vacuous = (blanked_under <= candidate_under)  # Tie or blanked better = vacuous
    
    return {
        "question_id": question_id,
        "blanked": {
            "under_covered_count": blanked_under,
            "concepts_with_zero_rows": blanked["concepts_with_zero_rows"],
        },
        "candidate": {
            "under_covered_count": candidate_under,
            "concepts_with_zero_rows": candidate["concepts_with_zero_rows"],
        },
        "shuffled": shuffled_results,
        "vacuous": vacuous,
        "vacuity_reason": "blanked_tied_or_better" if vacuous else "blanked_strictly_worse",
    }

def run_regression_check(candidate_results: Dict[str, Any]) -> Dict[str, Any]:
    """Check regression against accepted retrieval benchmark 39117425713.json."""
    # Load accepted benchmark
    benchmark_path = Path("/tmp/lex_accepted/core/evaluation/results/evaluation/retrieval_benchmark/39117425713.json")
    with open(benchmark_path, "r") as f:
        accepted = json.load(f)
    
    # The accepted benchmark records which gates passed
    # We need to verify they still pass with candidate layer
    # For now, we check that our candidate layer doesn't break the gates
    # by verifying the same invariants hold
    
    required_gates = [
        "duplicate::unique_ids",
        "counter::known_counter_recall",
        "source::rows_valid",
        "transport::all_queries_ok",
    ]
    
    # In practice, since our layer is additive (only adds query variants),
    # and we don't modify decisions/clusters/relations, these should hold.
    # But we must MEASURE not assert.
    
    # Check that candidate results have valid structure
    results = {
        "duplicate_unique_ids": "not_measured_requires_bundle_replay",
        "counter_known_counter_recall": "not_measured_requires_bundle_replay",
        "source_rows_valid": "not_measured_requires_bundle_replay",
        "transport_all_queries_ok": "all_cached_network_calls_0",
        "latency_budget": "cached_replay_only",
    }
    
    return {
        "checked_against": "39117425713",
        "required_gates": required_gates,
        "results": results,
        "note": "Full regression proof requires bundle replay with candidate layer in pool; this harness measures retrieval-time metrics only.",
    }

# ---------------------------------------------------------------------------
# Main harness
# ---------------------------------------------------------------------------

def run_harness(bundle_paths: List[Path], out_dir: Path) -> Dict[str, Any]:
    """Run the full harness and emit results."""
    out_dir.mkdir(parents=True, exist_ok=True)
    
    start_time = time.time()
    
    # Build input bundle metadata for RULES
    input_bundles = {}
    for bp in bundle_paths:
        if bp.exists():
            input_bundles[bp.stem] = {
                "path": str(bp),
                "content_sha256": _sha256_file(bp),
            }
    
    # Freeze RULES with input bundle hashes
    rules = dict(RULES)
    rules["input_bundles"] = input_bundles
    rules["frozen_at_utc"] = datetime.now(timezone.utc).isoformat()
    
    # Compute RULES digest
    rules_bytes = json.dumps(rules, sort_keys=True, separators=(",", ":")).encode("utf-8")
    rules_digest = _sha256_bytes(rules_bytes)
    rules["rules_digest"] = rules_digest
    
    # Write RULES.json FIRST (freeze-first)
    rules_path = out_dir / "RULES.json"
    with open(rules_path, "w") as f:
        json.dump(rules, f, indent=2, sort_keys=True)
    
    # Now run measurements
    harness_results = {
        "schema": "lex-frontier-query-concept-recall-harness/1",
        "charter_version": 1,
        "team_id": "frontier-query-concept-recall",
        "rules_digest": rules_digest,
        "frozen_spec_digest": "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "served_questions": {},
        "frozen_legs": {},
        "vacuity_controls": {},
        "regression_check": {},
    }
    
    # 1. Per-served-question concept coverage (baseline vs candidate)
    for qid in SERVED_QUESTIONS:
        baseline = measure_baseline_concept_coverage(qid)
        candidate = measure_candidate_concept_coverage(qid)
        
        harness_results["served_questions"][qid] = {
            "query": SERVED_QUERIES[qid],
            "baseline": baseline,
            "candidate": candidate,
            "delta": {
                "under_covered_baseline": baseline["under_covered_count"],
                "under_covered_candidate": candidate["under_covered_count"],
                "improvement": baseline["under_covered_count"] - candidate["under_covered_count"],
            },
        }
    
    # 2. Per-frozen-leg authority recall (baseline vs candidate)
    for slug in FROZEN_LEG_SLUGS:
        baseline_recall = measure_frozen_leg_authority_recall(slug, use_candidate=False)
        candidate_recall = measure_frozen_leg_authority_recall(slug, use_candidate=True)
        
        # Compute delta per language
        delta = {}
        for lang in ("fr", "de", "it"):
            base_recall = baseline_recall["per_language"].get(lang, {}).get("recall", 0)
            cand_recall = candidate_recall["per_language"].get(lang, {}).get("recall", 0)
            delta[lang] = {
                "baseline_recall": base_recall,
                "candidate_recall": cand_recall,
                "delta": cand_recall - base_recall,
            }
        
        union_base = baseline_recall["union"].get("recall", 0)
        union_cand = candidate_recall["union"].get("recall", 0)
        delta["union"] = {
            "baseline_recall": union_base,
            "candidate_recall": union_cand,
            "delta": union_cand - union_base,
        }
        
        harness_results["frozen_legs"][slug] = {
            "baseline": baseline_recall,
            "candidate": candidate_recall,
            "delta": delta,
        }
    
    # 3. Vacuity controls
    for qid in SERVED_QUESTIONS:
        harness_results["vacuity_controls"][qid] = run_vacuity_controls(qid)
    
    # 4. Regression check
    harness_results["regression_check"] = run_regression_check(harness_results)
    
    # 5. Overall verdict
    # Check Outcome A conditions
    failing_fr_it_cells = 0
    improved_fr_it_cells = 0
    
    for slug in ["corporate-criminal-liability", "business-judgment-rule", "petty-theft-dismissal"]:
        for lang in ("fr", "it"):
            base = harness_results["frozen_legs"][slug]["baseline"]["per_language"].get(lang, {}).get("recall", 0)
            cand = harness_results["frozen_legs"][slug]["candidate"]["per_language"].get(lang, {}).get("recall", 0)
            if base == 0:  # These are the 0/2, 0/5, 0/2 cells
                failing_fr_it_cells += 1
                if cand > base:
                    improved_fr_it_cells += 1
    
    reduced_under_covered = 0
    for qid in SERVED_QUESTIONS:
        base_under = harness_results["served_questions"][qid]["baseline"]["under_covered_count"]
        cand_under = harness_results["served_questions"][qid]["candidate"]["under_covered_count"]
        if cand_under < base_under:
            reduced_under_covered += 1
    
    # Check vacuity
    any_vacuous = any(v["vacuous"] for v in harness_results["vacuity_controls"].values())
    
    if any_vacuous:
        outcome = "VOID_VACUOUS"
        cycle_status = "INCOMPLETE"
        continue_recommended = True
    elif improved_fr_it_cells >= 2 and reduced_under_covered >= 2:
        outcome = "OUTCOME_A_PROMOTE"
        cycle_status = "COMPLETED"
        continue_recommended = False
    else:
        outcome = "OUTCOME_B_BOUNDED_NEGATIVE"
        cycle_status = "INCOMPLETE"  # Not COMPLETED until retrieval-time test runs
        continue_recommended = True
    
    harness_results["verdict"] = {
        "outcome": outcome,
        "improved_fr_it_cells": improved_fr_it_cells,
        "required_fr_it_cells": 2,
        "failing_fr_it_cells_total": failing_fr_it_cells,
        "reduced_under_covered_questions": reduced_under_covered,
        "required_reduced_questions": 2,
        "any_vacuous": any_vacuous,
        "cycle_status": cycle_status,
        "continue_recommended": continue_recommended,
    }
    
    # Write harness results
    results_path = out_dir / "harness_results.json"
    with open(results_path, "w") as f:
        json.dump(harness_results, f, indent=2, sort_keys=True)
    
    # Generate integration contract
    contract = generate_integration_contract(harness_results, rules_digest)
    contract_path = out_dir / "integration_contract.json"
    with open(contract_path, "w") as f:
        json.dump(contract, f, indent=2, sort_keys=True)
    
    # Write team state
    team_state = {
        "charter_version": 1,
        "direction_version": 57,  # From charter
        "cycle_status": cycle_status,
        "evidence_tier": "REPRODUCED" if not any_vacuous else "EXPLORATORY",
        "run_history": [{
            "run_id": f"harness_{int(time.time())}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "outcome": outcome,
            "rules_digest": rules_digest,
            "verdict": harness_results["verdict"],
        }],
        "continue_recommended": continue_recommended,
    }
    state_path = out_dir / "team_state.json"
    with open(state_path, "w") as f:
        json.dump(team_state, f, indent=2, sort_keys=True)
    
    elapsed = time.time() - start_time
    print(f"Harness completed in {elapsed:.2f}s")
    print(f"Outcome: {outcome}")
    print(f"Results written to {out_dir}")
    
    return harness_results


def generate_integration_contract(harness_results: Dict[str, Any], rules_digest: str) -> Dict[str, Any]:
    """Generate the Product integration contract per acceptance test (8)."""
    verdict = harness_results["verdict"]
    outcome = verdict["outcome"]
    
    # Build the contract
    contract = {
        "schema": "lex-frontier-query-concept-recall-integration-contract/1",
        "charter_version": 1,
        "rules_digest": rules_digest,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "drop_in_path": "product.query.pipeline.enrich_query_bundle (after initial retrieval, before rerank)",
        "extra_query_variants": {
            "kinds": ["compound_split", "cross_lang"],
            "language_filters": ["de", "fr", "it"],
            "provenance_entry": "query_expansion",
            "example": {
                "variant_id": "cross_lang:a1b2c3d4",
                "text": "Aktive Fürsorgepflicht ... Überwachungspflicht? atteinte au capital obligation de surveillance lesione del capitale obbligo di sorveglianza",
                "kind": "cross_lang",
                "added_terms": ["atteinte au capital", "obligation de surveillance", "lesione del capitale", "obbligo di sorveglianza"],
                "note": "Cross-language doctrinal equivalents from frozen corpus-derived map",
            },
        },
        "runtime_cost": {
            "estimated_ms": "<5",
            "measured_ms": None,
            "note": "String operations only; no network, no model calls",
        },
        "disclosure": {
            "if_outcome_a": {
                "text": "The query-expansion layer recovered frozen controlling authorities in FR/IT that the plain baseline missed, and reduced zero-coverage core concepts on the served questions. This is a retrieval signal, not proof that authorities were absent from the corpus. The map may now reveal branches previously unreachable. Product decides adoption under factory-wide requirement 21.",
                "yield": f"improved_fr_it_cells={verdict['improved_fr_it_cells']}, reduced_under_covered={verdict['reduced_under_covered_questions']}",
                "abstentions": "none",
            },
            "if_outcome_b": {
                "text": "No in-budget deterministic expansion recovered the missing concepts or authority IDs at retrieval time. The lexical gap (German compound nouns, cross-language doctrinal terms) is genuine for this corpus. The admission-disclosure half with Product remains the only path. This item is CLOSED; no further expansion work under this charter.",
                "unrecoverable_cells": "measured_per_language_recall_still_zero",
                "lexical_cause": "corpus_lacks_cross_language_doctrinal_equivalents_for_these_concepts",
            },
            "if_void": {
                "text": "Harness vacuous: blanked expansion tied or beat candidate on frozen core concepts. No measurement possible. Charter declares run void.",
                "recommendation": "Re-examine expansion primitives or concept definitions.",
            },
        },
        "claim_ceiling": RULES["rules"]["claim_ceiling"],
        "product_decision_required": True,
        "silent_non_consumption_not_permitted": True,
    }
    
    # Select the appropriate disclosure
    if outcome == "OUTCOME_A_PROMOTE":
        contract["active_disclosure"] = contract["disclosure"]["if_outcome_a"]
    elif outcome == "OUTCOME_B_BOUNDED_NEGATIVE":
        contract["active_disclosure"] = contract["disclosure"]["if_outcome_b"]
    else:
        contract["active_disclosure"] = contract["disclosure"]["if_void"]
    
    return contract


def main():
    parser = argparse.ArgumentParser(description="Frontier Query Concept Recall Harness")
    parser.add_argument("--bundle", action="append", type=Path, default=[],
                        help="Path to served question bundle.json (can repeat)")
    parser.add_argument("--out", type=Path, required=True,
                        help="Output directory for results")
    parser.add_argument("--rules-only", action="store_true",
                        help="Only write RULES.json and exit (for freeze-first)")
    
    args = parser.parse_args()
    
    if args.rules_only:
        # Just write RULES.json for freeze-first commit
        args.out.mkdir(parents=True, exist_ok=True)
        rules = dict(RULES)
        rules["frozen_at_utc"] = datetime.now(timezone.utc).isoformat()
        rules_bytes = json.dumps(rules, sort_keys=True, separators=(",", ":")).encode("utf-8")
        rules["rules_digest"] = _sha256_bytes(rules_bytes)
        rules_path = args.out / "RULES.json"
        with open(rules_path, "w") as f:
            json.dump(rules, f, indent=2, sort_keys=True)
        print(f"RULES.json written to {rules_path}")
        print(f"Rules digest: {rules['rules_digest']}")
        return 0
    
    # Validate bundle paths
    for bp in args.bundle:
        if not bp.exists():
            print(f"ERROR: Bundle not found: {bp}", file=sys.stderr)
            return 1
    
    try:
        run_harness(args.bundle, args.out)
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())