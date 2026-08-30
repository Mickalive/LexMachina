#!/usr/bin/env python3
"""
Product Integration Verification — Evaluation v11

Cross-references all product-integrated map modes against accepted
evaluation adversarial standards. Identifies:
1. Representations in product but NOT evaluated
2. Representations evaluated but NOT in product
3. EXPLORATORY representations lacking adversarial validation
4. Product lane metrics consistency with accepted evaluation state

Frozen harness v3: seed=42, config_hash=4323f833fa72366a
Adversarial thresholds: LangDom < 0.85, JuristPref > 0.5, CrossLang > 0.2, ClusterCoherence > 0.7

Hypothesis: All ACCEPTED product-integrated representations pass adversarial gates.
Baseline: Frozen evaluation harness v3 accepted metrics from state/evaluation.json.
Decision: Which representations should be promoted/demoted in product map modes.
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

# Paths
WORKSPACE = Path("/home/runner/work/LexMachina/LexMachina")
ACCEPTED_ROOT = Path("/tmp/lex_accepted")

# Frozen adversarial thresholds
ADVERSARIAL_THRESHOLDS = {
    "language_dominance": 0.85,
    "jurist_pairwise": 0.5,
    "cross_lang_recall": 0.2,
    "cluster_coherence": 0.7,
}

def load_accepted_evaluation():
    """Load accepted evaluation state with all metrics."""
    state_path = WORKSPACE / "state" / "evaluation.json"
    with open(state_path) as f:
        state = json.load(f)
    return state

def load_product_state():
    """Load product lane state."""
    product_path = ACCEPTED_ROOT / "product" / "state" / "product.json"
    if product_path.exists():
        with open(product_path) as f:
            return json.load(f)
    
    # Fallback to workspace
    product_path = WORKSPACE / "product" / "state" / "product.json"
    if product_path.exists():
        with open(product_path) as f:
            return json.load(f)
    
    return None

def extract_product_representations(product_state):
    """Extract all representation names from product state."""
    if not product_state:
        return []
    
    reps = set()
    metrics = product_state.get("metrics_summary", {})
    
    # Extract from map_representations list
    for rep in metrics.get("map_representations", []):
        reps.add(rep)
    
    # Extract from metrics_summary keys that have evaluation data
    for key in metrics:
        if isinstance(metrics[key], dict) and "evidence_tier" in metrics[key]:
            reps.add(key)
    
    return sorted(reps)

def map_product_to_evaluation_name(product_name):
    """Map product representation names to evaluation names."""
    mapping = {
        "center_projected_64dim_hierarchical": "center_projected_64dim",
        "center_projected": "center_projected_768",
        "linear_metric_best": "linear_metric_epoch4",
        "mahalanobis_best": "mahalanobis_metric_epoch4",
        "hybrid_stabilized_best": "hybrid_stabilized_epoch1",
        "cited_decisions_tfidf": "cited_decisions_tfidf",
        "following_alpha0.3": "following_alpha0.3",
        "criticizing_alpha0.3": "criticizing_alpha0.3",
        "citing_alpha0.3": "citing_alpha0.3",
        "cited_decisions_tfidf_hybrid_cp64_0.7": "cited_decisions_tfidf_proc_pairs_hybrid_cdtf64_0.7",
        "cited_decisions_tfidf_hybrid_cp64_0.5": None,  # May not have direct eval
        "cited_decisions_tfidf_hybrid_cp64_0.3": None,
        "cited_decisions_tfidf_hybrid_cp768_0.7": None,  # Evaluated but not in frozen harness v3
    }
    return mapping.get(product_name, product_name)

def verify_adversarial_gates(metrics, name):
    """Check if representation passes all adversarial gates."""
    results = {}
    
    # Language dominance
    ld = metrics.get("adversarial_language_dominance", 0)
    ld_pass = ld < ADVERSARIAL_THRESHOLDS["language_dominance"]
    results["language_dominance"] = {
        "value": ld,
        "threshold": ADVERSARIAL_THRESHOLDS["language_dominance"],
        "pass": ld_pass,
    }
    
    # Jurist pairwise preference
    jp = metrics.get("jurist_pairwise_preference", 0)
    jp_pass = jp > ADVERSARIAL_THRESHOLDS["jurist_pairwise"]
    results["jurist_pairwise"] = {
        "value": jp,
        "threshold": ADVERSARIAL_THRESHOLDS["jurist_pairwise"],
        "pass": jp_pass,
    }
    
    # Cross-language retrieval
    clr = metrics.get("cross_language_retrieval", 0)
    clr_pass = clr > ADVERSARIAL_THRESHOLDS["cross_lang_recall"] if clr > 0 else None
    results["cross_lang_recall"] = {
        "value": clr,
        "threshold": ADVERSARIAL_THRESHOLDS["cross_lang_recall"],
        "pass": clr_pass,
    }
    
    # Cluster coherence
    cc = metrics.get("jurivoc_level_1_nmi", 0)
    cc_pass = cc > ADVERSARIAL_THRESHOLDS["cluster_coherence"] if cc > 0 else None
    results["cluster_coherence"] = {
        "value": cc,
        "threshold": ADVERSARIAL_THRESHOLDS["cluster_coherence"],
        "pass": cc_pass,
    }
    
    # Overall verdict
    both_adversarial = ld_pass and jp_pass
    results["both_adversarial_pass"] = both_adversarial
    results["verdict"] = "PASS" if both_adversarial else "FAIL"
    
    return results

def main():
    print("=" * 80)
    print("PRODUCT INTEGRATION VERIFICATION — Evaluation v11")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"Frozen Harness v3: seed=42, config_hash=4323f833fa72366a")
    print("=" * 80)
    
    # Load states
    eval_state = load_accepted_evaluation()
    product_state = load_product_state()
    
    # Extract representations
    product_reps = extract_product_representations(product_state)
    eval_metrics = eval_state.get("validation_metrics", {})
    eval_reps = set(eval_metrics.keys())
    
    print(f"\nProduct representations: {len(product_reps)}")
    print(f"Evaluation representations: {len(eval_reps)}")
    
    # Cross-reference
    product_set = set(product_reps)
    eval_set = eval_reps.copy()
    
    # Map product names to evaluation names
    product_to_eval = {}
    for rep in product_reps:
        eval_name = map_product_to_evaluation_name(rep)
        if eval_name:
            product_to_eval[rep] = eval_name
    
    # Find gaps
    in_product_not_evaluated = []
    in_eval_not_product = []
    explored_not_evaluated = []
    
    for rep in product_reps:
        eval_name = product_to_eval.get(rep)
        if eval_name is None or eval_name not in eval_set:
            # Check if it's a known non-evaluated representation
            if rep in ["concat_center_tfidf", "baseline", "hdbscan", "hierarchical_leiden", 
                       "true_hierarchical_leiden", "debiased_citation_blended", "fractal_map_7res",
                       "hybrid_alpha_0_3", "hybrid_alpha_0_5", "legal_issues_outcomes"]:
                explored_not_evaluated.append(rep)
            else:
                in_product_not_evaluated.append(rep)
    
    for rep in eval_set:
        # Find if any product rep maps to this
        found = False
        for prod_rep, eval_name in product_to_eval.items():
            if eval_name == rep:
                found = True
                break
        if not found and rep not in ["multilingual_e5_small_pretrained"]:  # Known optional
            in_eval_not_product.append(rep)
    
    print(f"\n--- GAP ANALYSIS ---")
    print(f"Representations in product but NOT evaluated: {len(in_product_not_evaluated)}")
    for rep in in_product_not_evaluated:
        print(f"  - {rep}")
    
    print(f"EXPLORATORY representations without adversarial validation: {len(explored_not_evaluated)}")
    for rep in explored_not_evaluated:
        print(f"  - {rep}")
    
    print(f"Representations evaluated but NOT in product: {len(in_eval_not_product)}")
    for rep in in_eval_not_product:
        print(f"  - {rep}")
    
    # Verify adversarial gates for all evaluated representations
    print(f"\n--- ADVERSARIAL GATE VERIFICATION ---")
    gate_results = {}
    for rep_name, metrics in eval_metrics.items():
        gate_results[rep_name] = verify_adversarial_gates(metrics, rep_name)
        verdict = gate_results[rep_name]["verdict"]
        ld = gate_results[rep_name]["language_dominance"]["value"]
        jp = gate_results[rep_name]["jurist_pairwise"]["value"]
        status = "✅" if verdict == "PASS" else "❌"
        print(f"  {status} {rep_name}: LangDom={ld:.4f}, JuristPref={jp:.4f} → {verdict}")
    
    # Summary
    pass_count = sum(1 for g in gate_results.values() if g["verdict"] == "PASS")
    fail_count = sum(1 for g in gate_results.values() if g["verdict"] == "FAIL")
    
    print(f"\n--- SUMMARY ---")
    print(f"Total evaluated: {len(gate_results)}")
    print(f"PASS: {pass_count} ({100*pass_count/len(gate_results):.1f}%)")
    print(f"FAIL: {fail_count} ({100*fail_count/len(gate_results):.1f}%)")
    
    # Check consistency with accepted state
    accepted_both_pass = eval_state.get("baseline_comparison", {})
    print(f"\n--- CONSISTENCY CHECK ---")
    print(f"Accepted state continue_recommended: {eval_state.get('continue_recommended')}")
    print(f"Accepted state next_recommendation: {eval_state.get('next_recommendation')}")
    print(f"Accepted state evidence_tier: {eval_state.get('evidence_tier')}")
    
    # Product-specific checks
    if product_state:
        prod_metrics = product_state.get("metrics_summary", {})
        print(f"\nProduct tests passed: {prod_metrics.get('tests_passed', 'unknown')}/{prod_metrics.get('total_tests', 'unknown')}")
        print(f"Product map representations: {len(prod_metrics.get('map_representations', []))}")
        print(f"Product next_recommendation: {product_state.get('next_recommendation', 'unknown')}")
    
    # Write results
    results = {
        "run_id": f"product_integration_verification_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "factory_direction_version": 10,
        "config_hash": "4323f833fa72366a",
        "global_seed": 42,
        "product_representations_count": len(product_reps),
        "evaluation_representations_count": len(eval_reps),
        "gaps": {
            "in_product_not_evaluated": in_product_not_evaluated,
            "explored_not_evaluated": explored_not_evaluated,
            "in_eval_not_product": in_eval_not_product,
        },
        "adversarial_gate_results": gate_results,
        "summary": {
            "total_evaluated": len(gate_results),
            "pass_count": pass_count,
            "fail_count": fail_count,
            "pass_rate": f"{100*pass_count/len(gate_results):.1f}%",
        },
        "verdict": "PASS" if fail_count == 0 else "PARTIAL_PASS",
    }
    
    output_path = WORKSPACE / "results" / "evaluation" / "product_integration_verification_v11.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults written to: {output_path}")
    
    # Return overall verdict
    if fail_count == 0:
        print("\n✅ ALL REPRESENTATIONS PASS ADVERSARIAL GATES")
        return 0
    else:
        print(f"\n⚠️  {fail_count} REPRESENTATION(S) FAIL ADVERSARIAL GATES")
        return 1

if __name__ == "__main__":
    sys.exit(main())
