#!/usr/bin/env python3
"""
Legal Distance Lane v6 - Evaluate Rebuilt Citation Role Embeddings

Tests the rebuilt citation role embeddings (following, distinguishing, overruling, 
criticizing, citing, all_weighted) against adversarial benchmarks and integrates 
with center_projected baseline.

Uses the rebuilt embeddings from v6_citation_roles_rebuild.py
"""

import json
import numpy as np
import logging
from pathlib import Path
from typing import Dict, List, Any
from collections import Counter

import sys
sys.path.insert(0, '/tmp/lex_accepted/fractal-map/fractal_map/hierarchical')
sys.path.insert(0, '/tmp/lex_accepted/evaluation/evaluation')
sys.path.insert(0, '/tmp/lex_accepted/evaluation/evaluation/tests')

from hierarchical_leiden import load_metadata_with_branch, leiden_clustering, compute_branch_purity
from hierarchical_zoom_validation import hierarchical_leiden, compute_branch_purity_per_cluster
from cross_language_benchmarks import adversarial_language_dominance
from jurist_usability import simulate_pairwise_preference, prepare_metadata
from sklearn.metrics import normalized_mutual_info_score
from sklearn.preprocessing import normalize

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
CENTER_PROJECTED_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full")
REBUILT_ROLES_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v6/citation_roles_rebuilt")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v6/citation_roles_rebuilt_eval")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_center_projected_1000() -> tuple:
    """Load center_projected 64-dim embeddings for 1000 decisions."""
    emb_path = CENTER_PROJECTED_DIR / 'embeddings_center_projected_64.npy'
    meta_path = CENTER_PROJECTED_DIR / 'metadata.json'
    
    embeddings = np.load(emb_path)[:1000]
    with open(meta_path, 'r') as f:
        metadata = json.load(f)[:1000]
    
    logger.info(f"Loaded center_projected_64 (first 1000): {embeddings.shape}")
    return embeddings, metadata

def load_rebuilt_role_embeddings() -> Dict[str, np.ndarray]:
    """Load all rebuilt citation role embeddings."""
    roles = {}
    for role in ['following', 'distinguishing', 'overruling', 'criticizing', 'citing', 'all_weighted']:
        path = REBUILT_ROLES_DIR / f'citation_role_{role}_rebuilt.npy'
        if path.exists():
            roles[role] = np.load(path)
            logger.info(f"Loaded {role}: {roles[role].shape}")
        else:
            logger.warning(f"Missing: {path}")
    return roles

def evaluate_on_adversarial_benchmarks(embeddings: np.ndarray, metadata: List[Dict], name: str) -> Dict:
    """Run adversarial benchmarks: language dominance and jurist pairwise preference."""
    logger.info(f"\n--- Adversarial Benchmarks: {name} ---")
    
    # Language dominance
    adv_results = adversarial_language_dominance(embeddings, metadata)
    lang_dom = adv_results['mean_language_dominance']
    lang_status = adv_results['status']
    
    # Jurist pairwise preference
    branches, languages, chambers, valid_indices = prepare_metadata(metadata)
    rep_valid = embeddings[valid_indices]
    jurist_results = simulate_pairwise_preference(rep_valid, branches, languages)
    jurist_pref = jurist_results['jurist_would_succeed_rate']
    jurist_status = jurist_results['status']
    
    both_pass = (lang_dom < 0.85) and (jurist_pref > 0.5)
    
    logger.info(f"  Language dominance: {lang_dom:.4f} ({lang_status}) {'✅' if lang_dom < 0.85 else '❌'}")
    logger.info(f"  Jurist preference: {jurist_pref:.4f} ({jurist_status}) {'✅' if jurist_pref > 0.5 else '❌'}")
    logger.info(f"  BOTH PASS: {'✅' if both_pass else '❌'}")
    
    return {
        'language_dominance': float(lang_dom),
        'language_dominance_status': lang_status,
        'jurist_preference': float(jurist_pref),
        'jurist_status': jurist_status,
        'adversarial_both_pass': both_pass,
    }

def evaluate_with_fractal_harness(embeddings: np.ndarray, metadata: List[Dict], name: str) -> Dict:
    """Evaluate using validated fractal-map harness."""
    logger.info(f"\n--- Fractal-Map Harness: {name} ---")
    
    hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine = hierarchical_leiden(
        embeddings, metadata, coarse_res=0.5, sub_res=3.0
    )
    
    n_fine = len(set(hierarchical_labels[hierarchical_labels != -1]))
    n_coarse = len(set(coarse_labels[coarse_labels != -1]))
    
    coarse_purities = compute_branch_purity_per_cluster(coarse_labels, metadata)
    coarse_overall = compute_branch_purity(coarse_labels, metadata)
    
    fine_purities = compute_branch_purity_per_cluster(hierarchical_labels, metadata)
    fine_overall = compute_branch_purity(hierarchical_labels, metadata)
    
    total_improvements = 0
    total_deteriorations = 0
    total_no_change = 0
    zoom_results = {}
    
    for coarse_id in sorted(coarse_to_fine.keys()):
        fine_ids = coarse_to_fine[coarse_id]
        if not fine_ids:
            continue
        coarse_pur = coarse_purities.get(coarse_id, 0)
        fine_purs = [fine_purities.get(fid, 0) for fid in fine_ids]
        fine_mean = np.mean(fine_purs) if fine_purs else 0
        improvements = sum(1 for fp in fine_purs if fp > coarse_pur + 0.01)
        deteriorations = sum(1 for fp in fine_purs if fp < coarse_pur - 0.01)
        no_change = len(fine_purs) - improvements - deteriorations
        total_improvements += improvements
        total_deteriorations += deteriorations
        total_no_change += no_change
        
        coarse_mask = coarse_labels == coarse_id
        coarse_branches = [metadata[i].get('branch') for i in np.where(coarse_mask)[0]]
        coarse_branches = [b for b in coarse_branches if b and b != 'null']
        coarse_dom = Counter(coarse_branches).most_common(1)[0][0] if coarse_branches else "unknown"
        
        zoom_results[int(coarse_id)] = {
            'coarse_size': int(np.sum(coarse_mask)),
            'coarse_purity': float(coarse_pur),
            'coarse_dominant_branch': coarse_dom,
            'n_fine_clusters': len(fine_ids),
            'fine_purity_mean': float(fine_mean),
            'improvement': float(fine_mean - coarse_pur),
            'improvements': improvements,
            'deteriorations': deteriorations,
            'no_change': no_change,
        }
    
    overall_improvement = fine_overall - coarse_overall
    total_fine = total_improvements + total_deteriorations + total_no_change
    improvement_rate = total_improvements / total_fine if total_fine > 0 else 0
    
    legal_areas = [metadata[i].get('legal_area', '') for i in range(len(metadata))]
    legal_areas = [la if la else 'unknown' for la in legal_areas]
    nmi = normalized_mutual_info_score(legal_areas, hierarchical_labels)
    
    flat_labels, _ = leiden_clustering(embeddings, resolution=3.0)
    flat_purity = compute_branch_purity(flat_labels, metadata)
    
    verdict = "PASS" if improvement_rate > 0.5 and overall_improvement > 0 else "PARTIAL" if improvement_rate > 0.3 else "FAIL"
    
    logger.info(f"  Coarse: {n_coarse}, Fine: {n_fine}")
    logger.info(f"  Coarse purity: {coarse_overall:.4f}, Fine purity: {fine_overall:.4f}")
    logger.info(f"  Improvement: {overall_improvement:+.4f} ({improvement_rate:.1%})")
    logger.info(f"  Legal area NMI: {nmi:.4f}")
    logger.info(f"  Hierarchical advantage: {fine_overall - flat_purity:+.4f}")
    logger.info(f"  Verdict: {verdict}")
    
    return {
        'n_coarse_clusters': n_coarse,
        'n_fine_clusters': n_fine,
        'coarse_purity': float(coarse_overall),
        'fine_purity': float(fine_overall),
        'overall_improvement': float(overall_improvement),
        'improvement_pct': float(overall_improvement / coarse_overall * 100) if coarse_overall > 0 else 0,
        'total_improvements': int(total_improvements),
        'total_deteriorations': int(total_deteriorations),
        'total_no_change': int(total_no_change),
        'improvement_rate': float(improvement_rate),
        'legal_area_nmi': float(nmi),
        'flat_purity': float(flat_purity),
        'hierarchical_advantage': float(fine_overall - flat_purity),
        'verdict': verdict,
        'zoom_results': zoom_results,
    }

def create_hybrid(legal_emb: np.ndarray, baseline_emb: np.ndarray, alpha: float) -> np.ndarray:
    """Create hybrid: alpha * legal + (1-alpha) * baseline."""
    legal_norm = normalize(legal_emb, norm='l2', axis=1)
    baseline_norm = normalize(baseline_emb, norm='l2', axis=1)
    hybrid = alpha * legal_norm + (1 - alpha) * baseline_norm
    return normalize(hybrid, norm='l2', axis=1)

def main():
    logger.info("=" * 70)
    logger.info("Legal Distance v6 - Evaluate Rebuilt Citation Role Embeddings")
    logger.info("Testing role embeddings with resolved court decision citations")
    logger.info("=" * 70)
    
    # 1. Load center_projected baseline (1000 decisions, 64-dim)
    logger.info("\n1. Loading center_projected baseline (1000, 64-dim)...")
    baseline_emb, metadata = load_center_projected_1000()
    
    # 2. Load rebuilt citation role embeddings
    logger.info("\n2. Loading rebuilt citation role embeddings...")
    role_embeddings = load_rebuilt_role_embeddings()
    
    # 3. Evaluate center_projected baseline first
    logger.info("\n" + "="*70)
    logger.info("BASELINE: center_projected_64")
    logger.info("="*70)
    
    baseline_adv = evaluate_on_adversarial_benchmarks(baseline_emb, metadata, "center_projected_64")
    baseline_fractal = evaluate_with_fractal_harness(baseline_emb, metadata, "center_projected_64")
    
    baseline_results = {
        'name': 'center_projected_64',
        'adversarial': baseline_adv,
        'fractal': baseline_fractal,
    }
    
    # 4. Evaluate each rebuilt citation role embedding
    all_results = {'center_projected_64': baseline_results}
    
    for role_name, role_emb in role_embeddings.items():
        logger.info(f"\n{'='*70}")
        logger.info(f"TESTING: {role_name}")
        logger.info(f"Shape: {role_emb.shape}")
        logger.info("="*70)
        
        # Adversarial benchmarks
        adv_results = evaluate_on_adversarial_benchmarks(role_emb, metadata, role_name)
        
        # Fractal-map harness
        fractal_results = evaluate_with_fractal_harness(role_emb, metadata, role_name)
        
        role_results = {
            'name': role_name,
            'embedding_shape': list(role_emb.shape),
            'adversarial': adv_results,
            'fractal': fractal_results,
        }
        all_results[role_name] = role_results
        
        # 5. Test hybrids with center_projected
        for alpha in [0.3, 0.5, 0.7]:
            logger.info(f"\n--- Hybrid: {role_name} @ alpha={alpha} ---")
            hybrid_emb = create_hybrid(role_emb, baseline_emb, alpha)
            
            hybrid_adv = evaluate_on_adversarial_benchmarks(hybrid_emb, metadata, f"{role_name}_alpha{alpha}")
            hybrid_fractal = evaluate_with_fractal_harness(hybrid_emb, metadata, f"{role_name}_alpha{alpha}")
            
            hybrid_results = {
                'name': f"{role_name}_alpha{alpha}",
                'alpha': alpha,
                'adversarial': hybrid_adv,
                'fractal': hybrid_fractal,
            }
            all_results[f"{role_name}_alpha{alpha}"] = hybrid_results
    
    # 6. Summary comparison
    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY: ADVERSARIAL BENCHMARKS")
    logger.info("=" * 80)
    logger.info(f"{'Experiment':<35} {'LangDom':>8} {'Jurist':>8} {'Both':>6}")
    logger.info("-" * 60)
    
    for name, res in all_results.items():
        adv = res['adversarial']
        ld = adv['language_dominance']
        jp = adv['jurist_preference']
        both = "✅" if adv['adversarial_both_pass'] else "❌"
        ld_sym = "✅" if ld < 0.85 else "❌"
        jp_sym = "✅" if jp > 0.5 else "❌"
        logger.info(f"{name:<35} {ld:.4f}{ld_sym} {jp:.4f}{jp_sym} {both:>6}")
    
    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY: FRACTAL-MAP HARNESS")
    logger.info("=" * 80)
    logger.info(f"{'Experiment':<35} {'Coarse':>7} {'Fine':>7} {'ImpRate':>8} {'NMI':>7} {'Verdict':>8}")
    logger.info("-" * 75)
    
    baseline_fine = all_results['center_projected_64']['fractal']['fine_purity']
    baseline_nmi = all_results['center_projected_64']['fractal']['legal_area_nmi']
    
    for name, res in all_results.items():
        if name == 'center_projected_64':
            continue
        fr = res['fractal']
        coarse = fr['coarse_purity']
        fine = fr['fine_purity']
        imp_rate = fr['improvement_rate']
        nmi = fr['legal_area_nmi']
        verdict = fr['verdict']
        
        fine_delta = fine - baseline_fine
        nmi_delta = nmi - baseline_nmi
        
        logger.info(f"{name:<35} {coarse:.3f}  {fine:.3f}  {imp_rate:.1%}  {nmi:.3f}  {verdict:>8}  (Δfine={fine_delta:+.3f}, ΔNMI={nmi_delta:+.3f})")
    
    # 7. Key findings
    logger.info("\n" + "=" * 80)
    logger.info("KEY FINDINGS")
    logger.info("=" * 80)
    
    # Best role embedding on adversarial
    role_only = {k: v for k, v in all_results.items() if '_alpha' not in k and k != 'center_projected_64'}
    if role_only:
        best_adv_role = max(role_only.items(), key=lambda x: (x[1]['adversarial']['adversarial_both_pass'], 
                                                                x[1]['adversarial']['jurist_preference'],
                                                                -x[1]['adversarial']['language_dominance']))
        logger.info(f"Best role on adversarial: {best_adv_role[0]} (both_pass={best_adv_role[1]['adversarial']['adversarial_both_pass']}, "
                    f"jurist={best_adv_role[1]['adversarial']['jurist_preference']:.4f}, "
                    f"lang_dom={best_adv_role[1]['adversarial']['language_dominance']:.4f})")
        
        best_fractal_role = max(role_only.items(), key=lambda x: x[1]['fractal']['fine_purity'])
        logger.info(f"Best role on fine purity: {best_fractal_role[0]} (fine={best_fractal_role[1]['fractal']['fine_purity']:.4f}, "
                    f"NMI={best_fractal_role[1]['fractal']['legal_area_nmi']:.4f})")
    
    # Best hybrid
    hybrids = {k: v for k, v in all_results.items() if '_alpha' in k}
    if hybrids:
        best_adv_hybrid = max(hybrids.items(), key=lambda x: (x[1]['adversarial']['adversarial_both_pass'],
                                                                x[1]['adversarial']['jurist_preference'],
                                                                -x[1]['adversarial']['language_dominance']))
        logger.info(f"Best hybrid on adversarial: {best_adv_hybrid[0]} (both_pass={best_adv_hybrid[1]['adversarial']['adversarial_both_pass']}, "
                    f"jurist={best_adv_hybrid[1]['adversarial']['jurist_preference']:.4f}, "
                    f"lang_dom={best_adv_hybrid[1]['adversarial']['language_dominance']:.4f})")
        
        best_fractal_hybrid = max(hybrids.items(), key=lambda x: x[1]['fractal']['fine_purity'])
        logger.info(f"Best hybrid on fine purity: {best_fractal_hybrid[0]} (fine={best_fractal_hybrid[1]['fractal']['fine_purity']:.4f}, "
                    f"NMI={best_fractal_hybrid[1]['fractal']['legal_area_nmi']:.4f})")
    
    # Which improve over baseline
    logger.info("\nImproving over center_projected baseline (fine_purity):")
    for name, res in all_results.items():
        if name == 'center_projected_64':
            continue
        delta = res['fractal']['fine_purity'] - baseline_fine
        if delta > 0.01:
            logger.info(f"  {name}: Δ={delta:+.4f}")
    
    logger.info("\nImproving over center_projected baseline (legal_area_NMI):")
    for name, res in all_results.items():
        if name == 'center_projected_64':
            continue
        delta = res['fractal']['legal_area_nmi'] - baseline_nmi
        if delta > 0.01:
            logger.info(f"  {name}: Δ={delta:+.4f}")
    
    # 8. Save results
    with open(OUTPUT_DIR / "citation_roles_rebuilt_eval_all_results.json", 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    logger.info(f"\nResults saved to {OUTPUT_DIR / 'citation_roles_rebuilt_eval_all_results.json'}")
    logger.info("\n=== Rebuilt Citation Role Evaluation Complete ===")
    return all_results

if __name__ == "__main__":
    main()