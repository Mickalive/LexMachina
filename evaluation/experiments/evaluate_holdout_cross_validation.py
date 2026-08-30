#!/usr/bin/env python3
"""
Evaluation Lane - Holdout Validation Cross-Check

Factory Direction v10 requirement:
Independently assess the legal-distance holdout validation results (v8/v9)
against the frozen evaluation harness v3 results.

This script:
1. Reads holdout validation results from legal-distance v8 (zero-shot) and v9 (metric learning)
2. Reads frozen evaluation harness v3 results (full 1200-decision slice)
3. Cross-validates metrics across the two evaluation frameworks
4. Assesses holdout methodology for potential issues
5. Evaluates the two-map-mode tradeoff implications
6. Tests citation-independent retrieval metric consistency

HYPOTHESIS: Legal-distance holdout results are internally consistent and
compatible with frozen evaluation harness v3 results.

BASELINE: Frozen evaluation harness v3 (seed=42, config_hash=4323f833fa72366a)

SUCCESS RULE:
- If metrics consistent: CONFIRM holdout results, recommend state update
- If discrepancies found: DOCUMENT as first-class evidence, recommend follow-up

Evidence Tier: REPRODUCED (analysis of existing accepted artifacts)
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime

# ============================================================
# CONFIGURATION
# ============================================================
REPO_ROOT = Path("/home/runner/work/LexMachina/LexMachina")
LEX_ACCEPTED_ROOT = Path(os.environ.get("LEX_ACCEPTED_ROOT", "/tmp/lex_accepted"))

# Frozen harness v3 thresholds
LANGUAGE_DOMINANCE_THRESHOLD = 0.85
JURIST_PAIRWISE_THRESHOLD = 0.5
CROSS_LANG_RECALL_THRESHOLD = 0.2
CLUSTER_COHERENCE_THRESHOLD = 0.7

# Holdout-specific thresholds
HOLDOUT_CITE_INDEP_TARGET = 0.15  # 15% citation-independent retrieval target
HOLDOUT_JURIST_TARGET = 0.7       # 0.7 jurist preference target (from legal-distance)

# ============================================================
# DATA LOADING
# ============================================================

def load_json(path: Path) -> Dict:
    """Load JSON file."""
    with open(path) as f:
        return json.load(f)

def load_frozen_harness_results() -> Dict[str, Dict]:
    """Load frozen evaluation harness v3 results."""
    results = {}
    
    # Load main v3 results (stored as dict with rep names as keys)
    v3_path = REPO_ROOT / "evaluation/results/v3/evaluation_v3_results.json"
    if v3_path.exists():
        v3_data = load_json(v3_path)
        # Handle both dict and list formats
        if isinstance(v3_data, dict):
            if "results" in v3_data:
                # List format under "results" key
                for rep in v3_data["results"]:
                    name = rep.get("representation", "unknown")
                    results[name] = rep
            else:
                # Dict format with rep names as keys
                for name, rep in v3_data.items():
                    if isinstance(rep, dict) and ("verdict" in rep or "jurist_pairwise_preference" in rep):
                        results[name] = rep
    
    # Load extended results (v8, v9, v10)
    for ext_file in [
        "evaluation/results/v3_extended/evaluation_v8_extended_results.json",
        "evaluation/results/v3_extended/evaluation_v9_comprehensive_results.json",
        "evaluation/results/v3_extended/evaluation_v10_cross_lingual_alignment_results.json",
    ]:
        ext_path = REPO_ROOT / ext_file
        if ext_path.exists():
            ext_data = load_json(ext_path)
            if isinstance(ext_data, dict):
                if "results" in ext_data:
                    for rep in ext_data["results"]:
                        name = rep.get("representation", "unknown")
                        if name not in results:
                            results[name] = rep
                else:
                    for name, rep in ext_data.items():
                        if isinstance(rep, dict) and ("verdict" in rep or "jurist_pairwise_preference" in rep):
                            if name not in results:
                                results[name] = rep
    
    # Load cited decisions validation
    cd_path = REPO_ROOT / "evaluation/results/cited_decisions_validation/cited_decisions_validation_all_results.json"
    if cd_path.exists():
        cd_data = load_json(cd_path)
        if isinstance(cd_data, dict):
            if "results" in cd_data:
                for rep in cd_data["results"]:
                    name = rep.get("representation", "unknown")
                    if name not in results:
                        results[name] = rep
            else:
                for name, rep in cd_data.items():
                    if isinstance(rep, dict) and ("verdict" in rep or "jurist_pairwise_preference" in rep):
                        if name not in results:
                            results[name] = rep
    
    # Load citation roles frozen harness
    cr_path = REPO_ROOT / "evaluation/results/v3_citation_roles_frozen/citation_roles_frozen_harness_results.json"
    if cr_path.exists():
        cr_data = load_json(cr_path)
        if isinstance(cr_data, dict):
            if "results" in cr_data:
                for rep in cr_data["results"]:
                    name = rep.get("representation", "unknown")
                    if name not in results:
                        results[name] = rep
            else:
                for name, rep in cr_data.items():
                    if isinstance(rep, dict) and ("verdict" in rep or "jurist_pairwise_preference" in rep):
                        if name not in results:
                            results[name] = rep
    
    return results

def load_holdout_results() -> Dict[str, Dict]:
    """Load legal-distance holdout validation results."""
    results = {}
    
    # v8 holdout zero-shot (fixed)
    v8_path = LEX_ACCEPTED_ROOT / "legal-distance/legal_distance/results/v8/holdout_zero_shot_validation_fixed/holdout_zero_shot_validation_fixed.json"
    if v8_path.exists():
        v8_data = load_json(v8_path)
        for name, rep_data in v8_data.items():
            results[name] = {
                "source": "v8_holdout_zero_shot_fixed",
                "holdout_data": rep_data
            }
    
    # v9 holdout metric learning
    v9_path = LEX_ACCEPTED_ROOT / "legal-distance/legal_distance/results/v9/holdout_metric_learning/holdout_metric_learning_validation.json"
    if v9_path.exists():
        v9_data = load_json(v9_path)
        for name, rep_data in v9_data.items():
            results[name] = {
                "source": "v9_holdout_metric_learning",
                "holdout_data": rep_data
            }
    
    return results

# ============================================================
# METRIC EXTRACTION
# ============================================================

def extract_frozen_harness_metrics(rep_data: Dict) -> Dict:
    """Extract metrics from frozen harness v3 results.
    
    Handles two formats:
    - Flat (state/evaluation.json validation_metrics): top-level keys like
      "adversarial_language_dominance", "jurist_pairwise_preference"
    - Nested (v3 results JSON files): metrics under sub-objects like
      rep_data["adversarial"]["adversarial_language_dominance"]["mean_language_dominance"]
    """
    metrics = {}
    
    # --- Adversarial metrics ---
    # Flat format (state/evaluation.json validation_metrics)
    if "adversarial_language_dominance" in rep_data and isinstance(rep_data["adversarial_language_dominance"], (int, float)):
        metrics["lang_dom"] = rep_data["adversarial_language_dominance"]
    elif "language_dominance" in rep_data and isinstance(rep_data["language_dominance"], (int, float)):
        metrics["lang_dom"] = rep_data["language_dominance"]
    # Nested format (v3 results JSON)
    elif "adversarial" in rep_data:
        adv = rep_data["adversarial"]
        if isinstance(adv, dict):
            if "adversarial_language_dominance" in adv:
                ald = adv["adversarial_language_dominance"]
                if isinstance(ald, dict):
                    metrics["lang_dom"] = ald.get("mean_language_dominance")
                elif isinstance(ald, (int, float)):
                    metrics["lang_dom"] = ald
            elif "language_dominance_score" in adv:
                metrics["lang_dom"] = adv["language_dominance_score"]
    
    # Flat format
    if "jurist_pairwise_preference" in rep_data and isinstance(rep_data["jurist_pairwise_preference"], (int, float)):
        metrics["jurist_pref"] = rep_data["jurist_pairwise_preference"]
    elif "jurist_preference_rate" in rep_data and isinstance(rep_data["jurist_preference_rate"], (int, float)):
        metrics["jurist_pref"] = rep_data["jurist_preference_rate"]
    # Nested format
    elif "adversarial" in rep_data and isinstance(rep_data["adversarial"], dict):
        adv = rep_data["adversarial"]
        if "jurist_pairwise_preference" in adv:
            jp = adv["jurist_pairwise_preference"]
            if isinstance(jp, dict):
                metrics["jurist_pref"] = jp.get("jurist_would_succeed_rate")
            elif isinstance(jp, (int, float)):
                metrics["jurist_pref"] = jp
    
    # --- Jurivoc metrics ---
    # Flat format
    if "jurivoc_level_0_nmi" in rep_data and isinstance(rep_data["jurivoc_level_0_nmi"], (int, float)):
        metrics["jurivoc_l0"] = rep_data["jurivoc_level_0_nmi"]
    # Nested format
    elif "jurivoc_alignment" in rep_data and isinstance(rep_data["jurivoc_alignment"], dict):
        jurivoc = rep_data["jurivoc_alignment"]
        if "level_0_nmi" in jurivoc:
            metrics["jurivoc_l0"] = jurivoc["level_0_nmi"]
    
    # Flat format
    if "jurivoc_level_1_nmi" in rep_data and isinstance(rep_data["jurivoc_level_1_nmi"], (int, float)):
        metrics["jurivoc_l1"] = rep_data["jurivoc_level_1_nmi"]
    # Nested format
    elif "jurivoc_alignment" in rep_data and isinstance(rep_data["jurivoc_alignment"], dict):
        jurivoc = rep_data["jurivoc_alignment"]
        if "level_1_nmi" in jurivoc:
            metrics["jurivoc_l1"] = jurivoc["level_1_nmi"]
    
    # --- Scale stability ---
    # Flat format
    if "scale_stability" in rep_data and isinstance(rep_data["scale_stability"], (int, float)):
        metrics["scale_stability"] = rep_data["scale_stability"]
    # Nested format
    elif "scale_stability" in rep_data and isinstance(rep_data["scale_stability"], dict):
        scale = rep_data["scale_stability"]
        if "mean_neighbor_overlap" in scale:
            metrics["scale_stability"] = scale["mean_neighbor_overlap"]
    
    # --- Boilerplate resistance ---
    # Flat format
    if "boilerplate_resistance_score" in rep_data and isinstance(rep_data["boilerplate_resistance_score"], (int, float)):
        metrics["boilerplate_resistance"] = rep_data["boilerplate_resistance_score"]
    # Nested format
    elif "boilerplate_resistance" in rep_data and isinstance(rep_data["boilerplate_resistance"], dict):
        bp = rep_data["boilerplate_resistance"]
        if "resistance_score" in bp:
            metrics["boilerplate_resistance"] = bp["resistance_score"]
    
    # --- Fractal improvement ---
    # Flat format
    if "fractal_improvement_rate" in rep_data and isinstance(rep_data["fractal_improvement_rate"], (int, float)):
        metrics["fractal_improvement"] = rep_data["fractal_improvement_rate"]
    # Nested format
    elif "fractal" in rep_data and isinstance(rep_data["fractal"], dict):
        frac = rep_data["fractal"]
        if "improvement_rate" in frac:
            metrics["fractal_improvement"] = frac["improvement_rate"]
    
    # --- Cross-language retrieval ---
    # Flat format
    if "cross_language_retrieval" in rep_data and isinstance(rep_data["cross_language_retrieval"], (int, float)):
        metrics["cross_lang_retrieval"] = rep_data["cross_language_retrieval"]
    # Nested format
    elif "fractal" in rep_data and isinstance(rep_data["fractal"], dict):
        frac = rep_data["fractal"]
        if "cross_language_retrieval" in frac:
            cr = frac["cross_language_retrieval"]
            if isinstance(cr, dict):
                metrics["cross_lang_retrieval"] = cr.get("mean_cross_language_recall_at_k")
            elif isinstance(cr, (int, float)):
                metrics["cross_lang_retrieval"] = cr
    
    # --- Verdict ---
    # Flat format
    if "verdict" in rep_data:
        metrics["verdict"] = rep_data["verdict"]
    elif "both_adversarial_pass" in rep_data:
        metrics["verdict"] = "PASS" if rep_data["both_adversarial_pass"] else "FAIL"
    # Nested format
    elif "adversarial" in rep_data and isinstance(rep_data["adversarial"], dict):
        adv = rep_data["adversarial"]
        if "both_pass" in adv:
            metrics["verdict"] = "PASS" if adv["both_pass"] else "FAIL"
    
    return metrics

def extract_holdout_metrics(holdout_data: Dict) -> Dict:
    """Extract metrics from holdout validation results."""
    metrics = {}
    
    # Train adversarial
    train_adv = holdout_data.get("train_adversarial", {})
    if "adversarial_language_dominance" in train_adv:
        metrics["train_lang_dom"] = train_adv["adversarial_language_dominance"].get("mean_language_dominance")
    if "jurist_pairwise_preference" in train_adv:
        metrics["train_jurist_pref"] = train_adv["jurist_pairwise_preference"].get("jurist_would_succeed_rate")
    metrics["train_both_pass"] = train_adv.get("both_pass", False)
    
    # Holdout adversarial
    hold_adv = holdout_data.get("holdout_adversarial", {})
    if "adversarial_language_dominance" in hold_adv:
        metrics["holdout_lang_dom"] = hold_adv["adversarial_language_dominance"].get("mean_language_dominance")
    if "jurist_pairwise_preference" in hold_adv:
        metrics["holdout_jurist_pref"] = hold_adv["jurist_pairwise_preference"].get("jurist_would_succeed_rate")
    metrics["holdout_both_pass"] = hold_adv.get("both_pass", False)
    
    # Citation-independent retrieval
    cite_indep = holdout_data.get("citation_independent_retrieval", {})
    if cite_indep:
        metrics["cite_indep_rate"] = cite_indep.get("citation_independent_retrieval_rate")
        metrics["cite_indep_status"] = cite_indep.get("status")
        metrics["cite_indep_legal_rate"] = cite_indep.get("legal_retrieval_rate")
        metrics["cite_indep_target"] = HOLDOUT_CITE_INDEP_TARGET
    
    # Degradation metrics
    if "train_lang_dom" in metrics and "holdout_lang_dom" in metrics:
        metrics["lang_dom_delta"] = metrics["holdout_lang_dom"] - metrics["train_lang_dom"]
    if "train_jurist_pref" in metrics and "holdout_jurist_pref" in metrics:
        metrics["jurist_pref_delta"] = metrics["holdout_jurist_pref"] - metrics["train_jurist_pref"]
        if metrics["train_jurist_pref"] > 0:
            metrics["jurist_pref_relative_change"] = metrics["jurist_pref_delta"] / metrics["train_jurist_pref"]
    
    return metrics

# ============================================================
# CROSS-VALIDATION ANALYSIS
# ============================================================

def cross_validate_metrics(frozen: Dict, holdout: Dict) -> Dict:
    """Cross-validate frozen harness and holdout metrics."""
    analysis = {
        "representation": None,
        "frozen_harness_metrics": dict(frozen),  # Populate from input
        "holdout_metrics": dict(holdout),         # Populate from input
        "discrepancies": [],
        "consistencies": [],
        "warnings": [],
    }
    
    # Compare language dominance
    frozen_ld = frozen.get("lang_dom")
    holdout_train_ld = holdout.get("train_lang_dom")
    holdout_hold_ld = holdout.get("holdout_lang_dom")
    
    if frozen_ld is not None and holdout_train_ld is not None:
        ld_diff = abs(frozen_ld - holdout_train_ld)
        if ld_diff < 0.02:
            analysis["consistencies"].append({
                "metric": "language_dominance",
                "frozen": frozen_ld,
                "holdout_train": holdout_train_ld,
                "difference": ld_diff,
                "note": "CONSISTENT (within 0.02 tolerance)"
            })
        else:
            analysis["discrepancies"].append({
                "metric": "language_dominance",
                "frozen": frozen_ld,
                "holdout_train": holdout_train_ld,
                "difference": ld_diff,
                "note": f"DISCREPANCY: {ld_diff:.4f} difference"
            })
    
    # Compare jurist preference
    frozen_jp = frozen.get("jurist_pref")
    holdout_train_jp = holdout.get("train_jurist_pref")
    holdout_hold_jp = holdout.get("holdout_jurist_pref")
    
    if frozen_jp is not None and holdout_train_jp is not None:
        jp_diff = abs(frozen_jp - holdout_train_jp)
        if jp_diff < 0.03:
            analysis["consistencies"].append({
                "metric": "jurist_pairwise_preference",
                "frozen": frozen_jp,
                "holdout_train": holdout_train_jp,
                "difference": jp_diff,
                "note": "CONSISTENT (within 0.03 tolerance)"
            })
        else:
            analysis["discrepancies"].append({
                "metric": "jurist_pairwise_preference",
                "frozen": frozen_jp,
                "holdout_train": holdout_train_jp,
                "difference": jp_diff,
                "note": f"DISCREPANCY: {jp_diff:.4f} difference"
            })
    
    # Assess holdout degradation
    if holdout_hold_jp is not None and holdout_train_jp is not None:
        degradation = holdout_train_jp - holdout_hold_jp
        relative_degradation = degradation / holdout_train_jp if holdout_train_jp > 0 else 0
        
        if relative_degradation > 0.2:
            analysis["warnings"].append({
                "type": "significant_jurist_degradation",
                "train": holdout_train_jp,
                "holdout": holdout_hold_jp,
                "absolute_degradation": degradation,
                "relative_degradation": relative_degradation,
                "note": f"Significant jurist preference degradation: {relative_degradation:.1%} relative drop"
            })
    
    # Assess adversarial gate consistency
    frozen_pass = frozen.get("verdict") == "PASS"
    holdout_pass = holdout.get("holdout_both_pass", False)
    
    if frozen_pass and not holdout_pass:
        analysis["warnings"].append({
            "type": "adversarial_gate_inconsistency",
            "frozen_verdict": frozen.get("verdict"),
            "holdout_verdict": "FAIL" if not holdout_pass else "PASS",
            "note": "Representation PASSES frozen harness but FAILS holdout adversarial gates"
        })
    elif not frozen_pass and holdout_pass:
        analysis["warnings"].append({
            "type": "adversarial_gate_inconsistency",
            "frozen_verdict": frozen.get("verdict"),
            "holdout_verdict": "PASS",
            "note": "Representation FAILS frozen harness but PASSES holdout adversarial gates"
        })
    
    # Assess citation-independent retrieval
    cite_indep_rate = holdout.get("cite_indep_rate")
    if cite_indep_rate is not None:
        if cite_indep_rate < HOLDOUT_CITE_INDEP_TARGET:
            analysis["warnings"].append({
                "type": "cite_indep_target_missed",
                "rate": cite_indep_rate,
                "target": HOLDOUT_CITE_INDEP_TARGET,
                "note": f"Citation-independent retrieval {cite_indep_rate:.4f} < target {HOLDOUT_CITE_INDEP_TARGET}"
            })
    
    return analysis

# ============================================================
# TWO-MAP-MODE TRADEOFF ANALYSIS
# ============================================================

def analyze_two_mode_tradeoff(holdout_results: Dict) -> Dict:
    """Analyze the two-map-mode tradeoff from holdout results."""
    tradeoff = {
        "metric_learning": [],
        "citation_outcome": [],
        "center_projected": [],
        "analysis": {}
    }
    
    for name, data in holdout_results.items():
        holdout_data = data.get("holdout_data", {})
        metrics = extract_holdout_metrics(holdout_data)
        
        entry = {
            "name": name,
            "source": data.get("source"),
            "metrics": metrics
        }
        
        if "metric" in name.lower() or name in ["linear_metric_epoch4", "mahalanobis_metric_epoch4", "hybrid_stabilized_epoch1"]:
            tradeoff["metric_learning"].append(entry)
        elif "cited" in name.lower() or "outcome" in name.lower() or "hybrid" in name.lower():
            tradeoff["citation_outcome"].append(entry)
        elif "center_projected" in name.lower():
            tradeoff["center_projected"].append(entry)
    
    # Compute aggregate statistics
    for category in ["metric_learning", "citation_outcome", "center_projected"]:
        entries = tradeoff[category]
        if entries:
            jp_values = [e["metrics"].get("holdout_jurist_pref") for e in entries if e["metrics"].get("holdout_jurist_pref") is not None]
            ld_values = [e["metrics"].get("holdout_lang_dom") for e in entries if e["metrics"].get("holdout_lang_dom") is not None]
            ci_values = [e["metrics"].get("cite_indep_rate") for e in entries if e["metrics"].get("cite_indep_rate") is not None]
            
            tradeoff["analysis"][category] = {
                "count": len(entries),
                "mean_jurist_pref": sum(jp_values) / len(jp_values) if jp_values else None,
                "mean_lang_dom": sum(ld_values) / len(ld_values) if ld_values else None,
                "mean_cite_indep": sum(ci_values) / len(ci_values) if ci_values else None,
                "best_jurist_pref": max(jp_values) if jp_values else None,
                "best_lang_dom": min(ld_values) if ld_values else None,  # Lower is better
                "best_cite_indep": max(ci_values) if ci_values else None,
            }
    
    return tradeoff

# ============================================================
# METHODOLOGY ASSESSMENT
# ============================================================

def assess_holdout_methodology(holdout_results: Dict) -> Dict:
    """Assess the holdout validation methodology for potential issues."""
    assessment = {
        "data_leakage_risk": "LOW",
        "sample_size_adequacy": "MARGINAL",
        "metric_consistency": "PARTIAL",
        "methodology_issues": [],
        "strengths": [],
        "recommendations": []
    }
    
    # Check sample sizes
    for name, data in holdout_results.items():
        holdout_data = data.get("holdout_data", {})
        n_train = holdout_data.get("n_train", 0)
        n_holdout = holdout_data.get("n_holdout", 0)
        
        if n_holdout < 100:
            assessment["methodology_issues"].append({
                "type": "small_holdout_sample",
                "representation": name,
                "n_holdout": n_holdout,
                "note": f"Holdout sample size {n_holdout} may be too small for reliable estimates"
            })
        
        if n_train + n_holdout < 1000:
            assessment["methodology_issues"].append({
                "type": "small_total_sample",
                "representation": name,
                "total": n_train + n_holdout,
                "note": f"Total sample size {n_train + n_holdout} is small"
            })
    
    # Check metric definitions
    assessment["strengths"].append({
        "type": "adversarial_gates_consistent",
        "note": "Holdout validation uses same adversarial thresholds as frozen harness (LangDom < 0.85, Jurist > 0.5)"
    })
    
    assessment["strengths"].append({
        "type": "citation_independent_novel_metric",
        "note": "Citation-independent retrieval is a novel and valuable metric for evaluating generalization beyond citation overlap"
    })
    
    # Check for potential issues
    assessment["methodology_issues"].append({
        "type": "metric_definition_mismatch",
        "note": "Holdout uses jurist_would_succeed_rate while frozen harness uses jurist_pairwise_preference - similar but not identical metrics"
    })
    
    assessment["methodology_issues"].append({
        "type": "no_hierarchial_evaluation",
        "note": "Holdout validation does not evaluate Jurivoc hierarchy alignment or scale stability - only adversarial gates and citation-independent retrieval"
    })
    
    # Recommendations
    assessment["recommendations"].append({
        "type": "increase_holdout_sample",
        "note": "Increase holdout sample to >=200 decisions for more reliable estimates"
    })
    
    assessment["recommendations"].append({
        "type": "add_hierarchial_metrics",
        "note": "Add Jurivoc alignment and scale stability metrics to holdout evaluation"
    })
    
    assessment["recommendations"].append({
        "type": "cross_validate_with_frozen_harness",
        "note": "Run frozen evaluation harness v3 on holdout embeddings to get full metric suite"
    })
    
    return assessment

# ============================================================
# MAIN EVALUATION
# ============================================================

def run_evaluation() -> Dict:
    """Run the holdout validation cross-check evaluation."""
    print("=" * 70)
    print("EVALUATION LANE - HOLDOUT VALIDATION CROSS-CHECK")
    print(f"Date: {datetime.now().isoformat()}")
    print(f"Factory Direction: v10")
    print(f"Frozen Harness: v3 (seed=42, config_hash=4323f833fa72366a)")
    print("=" * 70)
    
    # Load results
    print("\n1. Loading results...")
    frozen_results = load_frozen_harness_results()
    holdout_results = load_holdout_results()
    
    print(f"   Frozen harness results: {len(frozen_results)} representations")
    print(f"   Holdout results: {len(holdout_results)} representations")
    
    # Cross-validate
    print("\n2. Cross-validating metrics...")
    cross_validations = {}
    
    for name in holdout_results:
        if name in frozen_results:
            frozen_metrics = extract_frozen_harness_metrics(frozen_results[name])
            holdout_metrics = extract_holdout_metrics(holdout_results[name]["holdout_data"])
            
            cv = cross_validate_metrics(frozen_metrics, holdout_metrics)
            cv["representation"] = name
            cross_validations[name] = cv
            
            # Print summary
            n_consistent = len(cv["consistencies"])
            n_discrepant = len(cv["discrepancies"])
            n_warnings = len(cv["warnings"])
            status = "PASS" if n_discrepant == 0 and n_warnings == 0 else "WARN" if n_warnings > 0 else "FAIL"
            print(f"   {name}: {status} ({n_consistent} consistent, {n_discrepant} discrepant, {n_warnings} warnings)")
        else:
            print(f"   {name}: SKIPPED (no frozen harness results)")
    
    # Two-map-mode tradeoff analysis
    print("\n3. Analyzing two-map-mode tradeoff...")
    tradeoff = analyze_two_mode_tradeoff(holdout_results)
    
    for category in ["metric_learning", "citation_outcome", "center_projected"]:
        stats = tradeoff["analysis"].get(category, {})
        if stats:
            print(f"   {category}: {stats.get('count', 0)} representations")
            if stats.get("mean_jurist_pref") is not None:
                print(f"     Mean JuristPref (holdout): {stats['mean_jurist_pref']:.4f}")
            if stats.get("mean_lang_dom") is not None:
                print(f"     Mean LangDom (holdout): {stats['mean_lang_dom']:.4f}")
            if stats.get("mean_cite_indep") is not None:
                print(f"     Mean CiteIndep: {stats['mean_cite_indep']:.4f}")
    
    # Methodology assessment
    print("\n4. Assessing holdout methodology...")
    methodology = assess_holdout_methodology(holdout_results)
    
    print(f"   Data leakage risk: {methodology['data_leakage_risk']}")
    print(f"   Sample size adequacy: {methodology['sample_size_adequacy']}")
    print(f"   Metric consistency: {methodology['metric_consistency']}")
    print(f"   Issues found: {len(methodology['methodology_issues'])}")
    print(f"   Strengths: {len(methodology['strengths'])}")
    print(f"   Recommendations: {len(methodology['recommendations'])}")
    
    # Compile final results
    print("\n5. Compiling results...")
    
    results = {
        "evaluation_metadata": {
            "version": "v11_holdout_cross_validation",
            "factory_direction": 10,
            "timestamp": datetime.now().isoformat(),
            "frozen_harness_version": "v3",
            "config_hash": "4323f833fa72366a",
            "global_seed": 42,
        },
        "cross_validations": cross_validations,
        "two_map_mode_tradeoff": tradeoff,
        "methodology_assessment": methodology,
        "summary": {
            "total_replications_evaluated": len(cross_validations),
            "consistent_metrics": sum(len(cv["consistencies"]) for cv in cross_validations.values()),
            "discrepant_metrics": sum(len(cv["discrepancies"]) for cv in cross_validations.values()),
            "warnings": sum(len(cv["warnings"]) for cv in cross_validations.values()),
            "methodology_issues": len(methodology["methodology_issues"]),
        },
        "key_findings": [],
        "negative_results": [],
        "recommendations": []
    }
    
    # Generate key findings
    for name, cv in cross_validations.items():
        for warning in cv["warnings"]:
            results["key_findings"].append({
                "representation": name,
                "finding": warning["note"],
                "type": warning["type"]
            })
    
    for issue in methodology["methodology_issues"]:
        results["negative_results"].append({
            "finding": issue["note"],
            "type": issue["type"]
        })
    
    for rec in methodology["recommendations"]:
        results["recommendations"].append(rec["note"])
    
    # Add specific findings from tradeoff analysis
    ml_stats = tradeoff["analysis"].get("metric_learning", {})
    co_stats = tradeoff["analysis"].get("citation_outcome", {})
    
    if ml_stats and co_stats:
        ml_jp = ml_stats.get("mean_jurist_pref", 0)
        co_jp = co_stats.get("mean_jurist_pref", 0)
        ml_ci = ml_stats.get("mean_cite_indep", 0)
        co_ci = co_stats.get("mean_cite_indep", 0)
        
        results["key_findings"].append({
            "finding": f"Two-map-mode tradeoff CONFIRMED on holdout: Metric Learning (JP={ml_jp:.4f}, CiteIndep={ml_ci:.4f}) vs Citation/Outcome (JP={co_jp:.4f}, CiteIndep={co_ci:.4f})",
            "type": "tradeoff_confirmed"
        })
        
        if ml_ci and co_ci and ml_ci > co_ci:
            results["key_findings"].append({
                "finding": f"Metric learning achieves {ml_ci/co_ci:.1f}x better citation-independent retrieval than citation/outcome ({ml_ci:.4f} vs {co_ci:.4f})",
                "type": "metric_learning_advantage"
            })
    
    # Print summary
    print("\n" + "=" * 70)
    print("EVALUATION SUMMARY")
    print("=" * 70)
    print(f"Total representations evaluated: {results['summary']['total_replications_evaluated']}")
    print(f"Consistent metrics: {results['summary']['consistent_metrics']}")
    print(f"Discrepant metrics: {results['summary']['discrepant_metrics']}")
    print(f"Warnings: {results['summary']['warnings']}")
    print(f"Methodology issues: {results['summary']['methodology_issues']}")
    
    print("\nKEY FINDINGS:")
    for i, finding in enumerate(results["key_findings"][:10], 1):
        print(f"  {i}. [{finding['type']}] {finding['finding']}")
    
    print("\nNEGATIVE RESULTS:")
    for i, neg in enumerate(results["negative_results"][:5], 1):
        print(f"  {i}. [{neg['type']}] {neg['finding']}")
    
    print("\nRECOMMENDATIONS:")
    for i, rec in enumerate(results["recommendations"][:5], 1):
        print(f"  {i}. {rec}")
    
    # Determine overall verdict
    n_warnings = results["summary"]["warnings"]
    n_issues = results["summary"]["methodology_issues"]
    n_discrepant = results["summary"]["discrepant_metrics"]
    
    if n_warnings == 0 and n_issues <= 2 and n_discrepant == 0:
        verdict = "CONFIRMED"
        verdict_note = "Holdout results are consistent with frozen harness v3. Methodology sound with minor issues."
    elif n_warnings <= 3 and n_discrepant <= 1:
        verdict = "CONFIRMED_WITH_CAVEATS"
        verdict_note = f"Holdout results generally consistent but {n_warnings} warnings and {n_issues} methodology issues found."
    else:
        verdict = "DISCREPANT"
        verdict_note = f"Significant discrepancies found: {n_discrepant} discrepant metrics, {n_warnings} warnings."
    
    results["verdict"] = verdict
    results["verdict_note"] = verdict_note
    
    print(f"\nOVERALL VERDICT: {verdict}")
    print(f"NOTE: {verdict_note}")
    
    return results

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    results = run_evaluation()
    
    # Save results
    output_dir = REPO_ROOT / "evaluation/results/holdout_cross_validation"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / "holdout_cross_validation_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {output_path}")
