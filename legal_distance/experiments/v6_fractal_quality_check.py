#!/usr/bin/env python3
"""
Quick fractal quality check on top adversarial performers.
Check if signal_outcome_tfidf overclusters like pure citation roles.
"""

import sys
import json
import numpy as np
import logging
from pathlib import Path
from typing import Dict, List, Any
from collections import Counter, defaultdict
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize
from sklearn.metrics import normalized_mutual_info_score
from sklearn.cluster import KMeans

sys.path.insert(0, '/tmp/lex_accepted/fractal-map/fractal_map/hierarchical')
from hierarchical_zoom_validation import hierarchical_leiden, compute_branch_purity_per_cluster

def compute_branch_purity(labels, metadata):
    from collections import Counter
    unique_labels = np.unique(labels[labels != -1])
    if len(unique_labels) == 0:
        return 0.0
    total = 0
    correct = 0
    for label in unique_labels:
        mask = labels == label
        cluster_branches = [metadata[i].get('branch') for i in np.where(mask)[0]]
        cluster_branches = [b for b in cluster_branches if b and b != 'null']
        if cluster_branches:
            most_common = Counter(cluster_branches).most_common(1)[0][1]
            correct += most_common
            total += len(cluster_branches)
    return correct / total if total > 0 else 0.0

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

SIGNAL_EMBEDDINGS_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/signal_ablation_embeddings")
CENTER_PROJECTED_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full")

def load_metadata():
    metadata_path = Path("/tmp/lex_accepted/fractal-map/results/fractal_map/baseline/metadata.json")
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    CHAMBER_TO_BRANCH = {
        "I. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
        "II. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
        "III. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
        "IV. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
        "I. Zivilrechtliche Abteilung": "zivilrecht",
        "II. Zivilrechtliche Abteilung": "zivilrecht",
        "I. Strafrechtliche Abteilung": "strafrecht",
        "II. Strafrechtliche Abteilung": "strafrecht",
        "II. sozialrechtliche Abteilung": "sozialversicherungsrecht",
        "IIe Cour de droit social": "sozialversicherungsrecht",
        "Ire Cour de droit public": "oeffentliches_recht",
        "IIe Cour de droit public": "oeffentliches_recht",
        "Ire Cour de droit civil": "zivilrecht",
        "IIe Cour de droit civil": "zivilrecht",
        "Ire Cour de droit pénal": "strafrecht",
        "IIe Cour de droit pénal": "strafrecht",
    }
    def assign_branch(chamber: str) -> str:
        if chamber in CHAMBER_TO_BRANCH: return CHAMBER_TO_BRANCH[chamber]
        chamber_lower = chamber.lower()
        if "öffentlich" in chamber_lower or "public" in chamber_lower: return "oeffentliches_recht"
        if "zivil" in chamber_lower or "civil" in chamber_lower: return "zivilrecht"
        if "straf" in chamber_lower or "pénal" in chamber_lower or "penal" in chamber_lower: return "strafrecht"
        if "sozial" in chamber_lower or "social" in chamber_lower: return "sozialversicherungsrecht"
        return "unknown"
    for meta in metadata:
        chamber = meta.get("chamber", "")
        meta['branch'] = assign_branch(chamber)
        if 'language' not in meta: meta['language'] = meta.get('language', 'de')
    return metadata

def run_fractal_quality(embeddings, metadata, name):
    logger.info(f"\n=== Fractal Quality: {name} ===")
    result = hierarchical_leiden(embeddings, metadata, coarse_res=0.5, sub_res=3.0)
    hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine = result
    
    n_fine = len(set(hierarchical_labels[hierarchical_labels != -1]))
    n_coarse = len(set(coarse_labels[coarse_labels != -1]))
    
    coarse_purities = compute_branch_purity_per_cluster(coarse_labels, metadata)
    coarse_overall = compute_branch_purity(coarse_labels, metadata)
    fine_purities = compute_branch_purity_per_cluster(hierarchical_labels, metadata)
    fine_overall = compute_branch_purity(hierarchical_labels, metadata)
    
    total_improvements = 0
    total_deteriorations = 0
    total_no_change = 0
    for coarse_id in sorted(coarse_to_fine.keys()):
        fine_ids = coarse_to_fine[coarse_id]
        if not fine_ids: continue
        coarse_pur = coarse_purities.get(coarse_id, 0)
        fine_purs = [fine_purities.get(fid, 0) for fid in fine_ids]
        improvements = sum(1 for fp in fine_purs if fp > coarse_pur + 0.01)
        deteriorations = sum(1 for fp in fine_purs if fp < coarse_pur - 0.01)
        no_change = len(fine_purs) - improvements - deteriorations
        total_improvements += improvements
        total_deteriorations += deteriorations
        total_no_change += no_change
    
    overall_improvement = fine_overall - coarse_overall
    total_fine = total_improvements + total_deteriorations + total_no_change
    improvement_rate = total_improvements / total_fine if total_fine > 0 else 0
    
    legal_areas = [metadata[i].get('legal_area', '') for i in range(len(metadata))]
    legal_areas = [la if la else 'unknown' for la in legal_areas]
    nmi = normalized_mutual_info_score(legal_areas, hierarchical_labels)
    
    logger.info(f"  Coarse clusters: {n_coarse}, Fine clusters: {n_fine}")
    logger.info(f"  Coarse purity: {coarse_overall:.4f}, Fine purity: {fine_overall:.4f}")
    logger.info(f"  Overall improvement: {overall_improvement:+.4f}")
    logger.info(f"  Improvement rate: {improvement_rate:.1%} ({total_improvements}/{total_fine})")
    logger.info(f"  Legal area NMI: {nmi:.4f}")
    
    # Check overclustering
    if n_coarse == 1 and n_fine > 500:
        logger.warning(f"  ⚠️ OVERCLUSTERING: 1 coarse → {n_fine} fine clusters!")
    
    return {
        'name': name,
        'n_coarse': n_coarse,
        'n_fine': n_fine,
        'coarse_purity': float(coarse_overall),
        'fine_purity': float(fine_overall),
        'improvement_rate': float(improvement_rate),
        'legal_area_nmi': float(nmi),
        'overclustering': n_coarse == 1 and n_fine > 500
    }

def main():
    metadata = load_metadata()
    
    # Test top adversarial performers
    test_names = [
        'center_projected_reference',
        'signal_outcome_tfidf',
        'hybrid_cited_decisions_0.3',
        'hybrid_norm_refs_0.3',
        'hybrid_legal_area_0.3',
    ]
    
    # Load center_projected reference
    cp_path = CENTER_PROJECTED_DIR / "embeddings_center_projected.npy"
    cp_metadata_path = CENTER_PROJECTED_DIR / "metadata.json"
    with open(cp_metadata_path) as f:
        cp_metadata = json.load(f)
    center_projected = np.load(cp_path)
    cp_by_id = {m['decision_id']: i for i, m in enumerate(cp_metadata)}
    eval_ids = [m['decision_id'] for m in metadata]
    valid_ids = [did for did in eval_ids if did in cp_by_id]
    valid_cp_indices = [cp_by_id[did] for did in valid_ids]
    center_projected_aligned = center_projected[valid_cp_indices]
    metadata_aligned = [m for m in metadata if m['decision_id'] in cp_by_id]
    
    all_embeddings = {
        'center_projected_reference': center_projected_aligned,
    }
    
    for name in test_names[1:]:
        path = SIGNAL_EMBEDDINGS_DIR / f"{name}.npy"
        if path.exists():
            emb = np.load(path)
            if emb.shape[0] > len(metadata_aligned):
                emb = emb[:len(metadata_aligned)]
            all_embeddings[name] = emb
    
    results = {}
    for name, emb in all_embeddings.items():
        results[name] = run_fractal_quality(emb, metadata_aligned, name)
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("FRACTAL QUALITY SUMMARY")
    logger.info("="*80)
    for name, r in results.items():
        overcluster = " ⚠️ OVERCLUSTER" if r['overclustering'] else ""
        logger.info(f"{name:<40} C={r['n_coarse']:>3} F={r['n_fine']:>4} ImpRate={r['improvement_rate']:.1%} NMI={r['legal_area_nmi']:.4f}{overcluster}")

if __name__ == "__main__":
    main()
