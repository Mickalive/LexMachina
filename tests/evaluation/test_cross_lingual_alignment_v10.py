#!/usr/bin/env python3
"""
Regression test for evaluation v10 cross-lingual alignment key findings.

Verifies the critical findings from the cross-lingual alignment investigation
on frozen harness v3 (seed=42).
"""

import json
import numpy as np
from pathlib import Path

TOLERANCE = 1e-3

# Key expected results from accepted state (evaluation v10)
KEY_FINDINGS = {
    # Proc Pairs is lossless for cited_decisions_tfidf
    "cited_decisions_tfidf_proc_pairs": {
        "lang_dom": 0.6088,
        "jurist_pref": 0.6881,
        "jurivoc_l0": 0.2549,
        "scale_stability": 0.5950,
        "verdict": "PASS",
        "both_adversarial_pass": True,
    },
    # Joint PCA reduces Jurivoc L0 by ~48%
    "cited_decisions_tfidf_joint_pca": {
        "lang_dom": 0.6153,
        "jurist_pref": 0.6806,
        "jurivoc_l0": 0.1333,  # ~48% reduction from 0.254
        "scale_stability": 0.5908,
        "verdict": "PASS",
        "both_adversarial_pass": True,
    },
    # Single Procrustes is catastrophic
    "cited_decisions_tfidf_procrustes": {
        "lang_dom": 0.7160,
        "jurist_pref": 0.3611,
        "jurivoc_l0": 0.1175,
        "scale_stability": 0.6208,
        "verdict": "FAIL",
        "both_adversarial_pass": False,
    },
    # Best 64-dim hybrid
    "cited_decisions_tfidf_proc_pairs_hybrid_cdtf64_0.7": {
        "lang_dom": 0.6085,
        "jurist_pref": 0.6872,
        "jurivoc_l0": 0.1429,
        "scale_stability": 0.5967,
        "verdict": "PASS",
        "both_adversarial_pass": True,
    },
    # Outcome hybrids overfit (high jurist, low jurivoc, zero scale)
    "section_outcome_proc_pairs": {
        "lang_dom": 0.4831,
        "jurist_pref": 0.8782,
        "jurivoc_l0": 0.0073,
        "scale_stability": 0.0000,
        "verdict": "PASS",
        "both_adversarial_pass": True,
    },
}


def load_v10_results() -> dict:
    """Load evaluation v10 cross-lingual alignment results."""
    results_path = Path("evaluation/results/v3_extended/evaluation_v10_cross_lingual_alignment_results.json")
    if not results_path.exists():
        raise FileNotFoundError(f"Results not found at {results_path}")
    
    with open(results_path) as f:
        return json.load(f)


def test_cross_lingual_findings():
    """Test key cross-lingual alignment findings."""
    print("Loading evaluation v10 cross-lingual alignment results...")
    results = load_v10_results()
    
    all_errors = []
    
    for name, expected in KEY_FINDINGS.items():
        if name not in results:
            all_errors.append(f"{name}: MISSING from results")
            continue
        
        current = results[name]
        errors = []
        
        if 'error' in current:
            errors.append(f"{name}: ERROR - {current.get('error')}")
        
        # Compare key metrics
        curr_adv = current.get('adversarial', {})
        curr_jurivoc = current.get('jurivoc_alignment', {})
        curr_scale = current.get('scale_stability', {})
        
        curr_ld = curr_adv.get('language_dominance_score', 0)
        if abs(curr_ld - expected['lang_dom']) > TOLERANCE:
            errors.append(f"  lang_dom: current={curr_ld:.4f}, expected={expected['lang_dom']:.4f}")
        
        curr_jp = curr_adv.get('jurist_preference_rate', 0)
        if abs(curr_jp - expected['jurist_pref']) > TOLERANCE:
            errors.append(f"  jurist_pref: current={curr_jp:.4f}, expected={expected['jurist_pref']:.4f}")
        
        curr_jv = curr_jurivoc.get('level_0_nmi', 0)
        if abs(curr_jv - expected['jurivoc_l0']) > TOLERANCE:
            errors.append(f"  jurivoc_l0: current={curr_jv:.4f}, expected={expected['jurivoc_l0']:.4f}")
        
        curr_sc = curr_scale.get('mean_neighbor_overlap', 0)
        if abs(curr_sc - expected['scale_stability']) > TOLERANCE:
            errors.append(f"  scale_stability: current={curr_sc:.4f}, expected={expected['scale_stability']:.4f}")
        
        curr_verdict = current.get('verdict', '')
        if curr_verdict != expected['verdict']:
            errors.append(f"  verdict: current={curr_verdict}, expected={expected['verdict']}")
        
        curr_both = curr_adv.get('both_pass', False)
        if curr_both != expected['both_adversarial_pass']:
            errors.append(f"  both_adversarial_pass: current={curr_both}, expected={expected['both_adversarial_pass']}")
        
        if errors:
            all_errors.append(f"{name}:")
            for e in errors:
                all_errors.append(f"  - {e}")
            print(f"  ✗ {name}: MISMATCH")
        else:
            print(f"  ✓ {name}: VERIFIED")
    
    # Additional structural assertions
    print("\n--- Structural Assertions ---")
    
    # 1. Proc Pairs should be lossless (match base cited_decisions_tfidf within tolerance)
    if 'cited_decisions_tfidf' in results and 'cited_decisions_tfidf_proc_pairs' in results:
        base = results['cited_decisions_tfidf']
        proc = results['cited_decisions_tfidf_proc_pairs']
        
        base_ld = base.get('adversarial', {}).get('language_dominance_score', 0)
        proc_ld = proc.get('adversarial', {}).get('language_dominance_score', 0)
        base_jp = base.get('adversarial', {}).get('jurist_preference_rate', 0)
        proc_jp = proc.get('adversarial', {}).get('jurist_preference_rate', 0)
        
        if abs(base_ld - proc_ld) > TOLERANCE or abs(base_jp - proc_jp) > TOLERANCE:
            all_errors.append(f"Proc Pairs NOT lossless: base_ld={base_ld:.4f} vs proc_ld={proc_ld:.4f}, base_jp={base_jp:.4f} vs proc_jp={proc_jp:.4f}")
            print(f"  ✗ Proc Pairs losslessness: FAILED")
        else:
            print(f"  ✓ Proc Pairs losslessness: VERIFIED (identical metrics)")
    
    # 2. Joint PCA should reduce Jurivoc L0 by ~48%
    if 'cited_decisions_tfidf' in results and 'cited_decisions_tfidf_joint_pca' in results:
        base_jv = results['cited_decisions_tfidf'].get('jurivoc_alignment', {}).get('level_0_nmi', 0)
        jpca_jv = results['cited_decisions_tfidf_joint_pca'].get('jurivoc_alignment', {}).get('level_0_nmi', 0)
        reduction = (base_jv - jpca_jv) / base_jv if base_jv > 0 else 0
        
        if abs(reduction - 0.48) > 0.10:  # Allow 10% tolerance on the 48% claim
            all_errors.append(f"Joint PCA Jurivoc L0 reduction: expected ~48%, got {reduction:.1%}")
            print(f"  ✗ Joint PCA Jurivoc reduction: {reduction:.1%} (expected ~48%)")
        else:
            print(f"  ✓ Joint PCA Jurivoc L0 reduction: {reduction:.1%} (matches ~48%)")
    
    # 3. Section outcome embeddings (2-dim) should have near-zero Jurivoc L0 and zero scale stability
    # These are the "pure" outcome embeddings without cited_decisions_tfidf
    section_outcome_reps = [k for k in results.keys() if k.startswith('section_outcome') and 'hybrid' not in k]
    for rep in section_outcome_reps:
        r = results[rep]
        jv = r.get('jurivoc_alignment', {}).get('level_0_nmi', 0)
        sc = r.get('scale_stability', {}).get('mean_neighbor_overlap', 0)
        if jv > 0.2 or sc > 0.1:
            all_errors.append(f"{rep}: section outcome has unexpected legal structure (jurivoc_l0={jv:.4f}, scale={sc:.4f})")
            print(f"  ✗ {rep}: unexpected legal structure")
        else:
            print(f"  ✓ {rep}: overfit confirmed (jurivoc_l0={jv:.4f}, scale={sc:.4f})")
    
    print(f"\n{'='*60}")
    if all_errors:
        print(f"FAILED: {len(all_errors)} issue(s) found")
        for e in all_errors:
            print(f"  - {e}")
        return False
    else:
        print(f"PASSED: All cross-lingual alignment key findings VERIFIED")
        return True


if __name__ == "__main__":
    success = test_cross_lingual_findings()
    exit(0 if success else 1)