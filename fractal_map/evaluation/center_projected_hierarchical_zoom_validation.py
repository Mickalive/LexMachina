#!/usr/bin/env python3
"""
Hierarchical Zoom Validation for center_projected embeddings.

Tests whether zooming from coarse to fine clustering resolution within
hierarchical Leiden reveals legally coherent substructure (measured by
branch purity improvement).

This reproduces the validation done for concat embeddings (direction_version 2)
but on pure center_projected embeddings.

Frozen before observation:
- Corpus: 1000 BGer decisions (2020-2024)
- Embeddings: center_projected (768-dim, pure, no TF-IDF)
- Clustering: Hierarchical Leiden (coarse_res=0.5, sub_res=3.0)
- Metric: Branch purity improvement from coarse to fine within each coarse cluster
- Success: Improvement rate >= 59.2% (concat baseline)
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter
import logging
from datetime import datetime, timezone
import igraph as ig
import leidenalg
from sklearn.neighbors import kneighbors_graph

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

BASELINE_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/baseline")
DEBIASING_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/language_debiasing")
CORPUS_DIR = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/evaluation")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CONCAT_BASELINE_IMPROVEMENT_RATE = 0.5918367346938775  # 59.2%


def load_metadata_with_branch():
    """Load baseline metadata and enrich with branch from corpus files."""
    with open(BASELINE_DIR / "metadata.json") as f:
        metadata = json.load(f)
    
    id_to_idx = {m['decision_id']: i for i, m in enumerate(metadata)}
    
    branch_map = {}
    for year_file in sorted(CORPUS_DIR.glob("bger_20*.jsonl")):
        with open(year_file) as f:
            for line in f:
                d = json.loads(line)
                did = d.get('decision_id', '')
                if did in id_to_idx:
                    branch_map[did] = d.get('branch')
    
    for m in metadata:
        m['branch'] = branch_map.get(m['decision_id'])
    
    return id_to_idx, metadata


def load_center_projected():
    """Load pure center_projected embeddings."""
    center_emb = np.load(DEBIASING_DIR / "embeddings_center_projected.npy")
    return center_emb


def leiden_clustering(embeddings, resolution=1.0, k=15):
    """Leiden clustering on embeddings."""
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normalized = embeddings / norms
    
    k_actual = min(k, len(embeddings) - 1)
    graph = kneighbors_graph(normalized, n_neighbors=k_actual, metric='euclidean',
                             mode='connectivity', include_self=False)
    graph = graph.maximum(graph.T)
    
    sources, targets = graph.nonzero()
    weights = graph.data
    edges = list(zip(sources.tolist(), targets.tolist()))
    
    g = ig.Graph()
    g.add_vertices(graph.shape[0])
    g.add_edges(edges)
    g.es['weight'] = weights.tolist()
    
    partition = leidenalg.find_partition(
        g, leidenalg.RBConfigurationVertexPartition,
        weights='weight', resolution_parameter=resolution, seed=42
    )
    return np.array(partition.membership), partition.modularity


def compute_branch_purity(labels, metadata):
    """Compute branch purity."""
    labels = np.array(labels)
    unique_labels = np.unique(labels[labels != -1])
    purities = []
    
    for label in unique_labels:
        mask = labels == label
        cluster_branches = [metadata[i].get('branch') for i in np.where(mask)[0]]
        cluster_branches = [b for b in cluster_branches if b and b != 'null']
        
        if cluster_branches:
            most_common = Counter(cluster_branches).most_common(1)[0][1]
            purities.append(most_common / len(cluster_branches))
    
    return float(np.mean(purities)) if purities else 0


def hierarchical_leiden(embeddings, metadata, coarse_res=0.5, sub_res=3.0, k=15):
    """
    Run hierarchical Leiden:
    1. Global Leiden at coarse_res
    2. Within each coarse cluster, run Leiden at sub_res
    3. Returns coarse_labels, hierarchical_labels, cluster_info
    """
    # Step 1: Global coarse clustering
    coarse_labels, coarse_mod = leiden_clustering(embeddings, resolution=coarse_res, k=k)
    unique_coarse = np.unique(coarse_labels[coarse_labels != -1])
    
    logger.info(f"  Coarse (res={coarse_res}): {len(unique_coarse)} clusters, modularity={coarse_mod:.4f}")
    
    # Step 2: Within each coarse cluster, run Leiden at sub_res
    hierarchical_labels = np.full(len(embeddings), -1, dtype=int)
    sub_cluster_id = 0
    cluster_info = {}
    
    for coarse_id in unique_coarse:
        mask = coarse_labels == coarse_id
        indices = np.where(mask)[0]
        
        if len(indices) < 20:
            hierarchical_labels[indices] = sub_cluster_id
            cluster_info[sub_cluster_id] = {
                'coarse_id': int(coarse_id),
                'sub_id': 0,
                'size': int(len(indices)),
                'too_small': True,
            }
            sub_cluster_id += 1
            continue
        
        subset_embeddings = embeddings[indices]
        
        # Run Leiden within subset
        sub_labels, sub_mod = leiden_clustering(subset_embeddings, resolution=sub_res, k=k)
        unique_sub = np.unique(sub_labels[sub_labels != -1])
        
        logger.info(f"    Coarse {coarse_id} ({len(indices)} docs): "
                    f"{len(unique_sub)} sub-clusters, modularity={sub_mod:.4f}")
        
        # Assign global labels
        for sub_id in unique_sub:
            sub_mask = sub_labels == sub_id
            global_indices = indices[sub_mask]
            hierarchical_labels[global_indices] = sub_cluster_id
            
            cluster_info[sub_cluster_id] = {
                'coarse_id': int(coarse_id),
                'sub_id': int(sub_id),
                'size': int(len(global_indices)),
                'too_small': False,
            }
            sub_cluster_id += 1
    
    return coarse_labels, hierarchical_labels, cluster_info


def validate_zoom_coherence(coarse_labels, hierarchical_labels, cluster_info, metadata):
    """
    Compute branch purity improvement from coarse to fine within each coarse cluster.
    This matches the hierarchical_zoom_validation methodology.
    """
    unique_coarse = np.unique(coarse_labels[coarse_labels != -1])
    
    total_improvements = 0
    total_deteriorations = 0
    total_no_change = 0
    
    per_coarse_cluster = {}
    coarse_purities = {}
    fine_purities_by_coarse = {}
    
    for coarse_id in unique_coarse:
        mask = coarse_labels == coarse_id
        indices = np.where(mask)[0]
        cluster_size = len(indices)
        
        # Coarse cluster purity
        cluster_branches = [metadata[i].get('branch') for i in indices]
        cluster_branches = [b for b in cluster_branches if b and b != 'null']
        
        if not cluster_branches:
            continue
            
        coarse_counter = Counter(cluster_branches)
        coarse_dominant = coarse_counter.most_common(1)[0][0]
        coarse_purity = coarse_counter.most_common(1)[0][1] / len(cluster_branches)
        coarse_purities[int(coarse_id)] = coarse_purity
        
        # Get fine sub-clusters for this coarse cluster
        sub_cluster_ids = [cid for cid, info in cluster_info.items() if info['coarse_id'] == coarse_id]
        
        if len(sub_cluster_ids) <= 1:
            # No substructure
            fine_purities_by_coarse[int(coarse_id)] = [coarse_purity]
            per_coarse_cluster[int(coarse_id)] = {
                'coarse_size': cluster_size,
                'coarse_purity': coarse_purity,
                'coarse_dominant_branch': coarse_dominant,
                'n_fine_clusters': len(sub_cluster_ids),
                'fine_purity_mean': coarse_purity,
                'fine_purity_values': [coarse_purity],
                'improvement': 0.0,
                'improvement_pct': 0.0,
                'improvements': 0,
                'deteriorations': 0,
                'no_change': 1,
                'fine_dominant_branches': {coarse_dominant: len(sub_cluster_ids)},
            }
            total_no_change += 1
            continue
        
        # Compute fine cluster purities
        fine_purity_values = []
        fine_dominant_branches = Counter()
        
        improvements = 0
        deteriorations = 0
        no_change = 0
        
        for sub_id in sub_cluster_ids:
            info = cluster_info[sub_id]
            if info.get('too_small', False):
                continue
                
            sub_indices = np.where(hierarchical_labels == sub_id)[0]
            if len(sub_indices) == 0:
                continue
            
            sub_branches = [metadata[i].get('branch') for i in sub_indices]
            sub_branches = [b for b in sub_branches if b and b != 'null']
            
            if sub_branches:
                sub_counter = Counter(sub_branches)
                sub_purity = sub_counter.most_common(1)[0][1] / len(sub_branches)
                sub_dominant = sub_counter.most_common(1)[0][0]
                fine_purity_values.append(sub_purity)
                fine_dominant_branches[sub_dominant] += 1
                
                # Compare with coarse purity
                if sub_purity > coarse_purity + 0.01:  # >1% improvement
                    improvements += 1
                elif sub_purity < coarse_purity - 0.01:  # >1% deterioration
                    deteriorations += 1
                else:
                    no_change += 1
        
        if fine_purity_values:
            fine_purity_mean = np.mean(fine_purity_values)
        else:
            fine_purity_mean = coarse_purity
            fine_purity_values = [coarse_purity]
        
        fine_purities_by_coarse[int(coarse_id)] = fine_purity_values
        
        improvement = fine_purity_mean - coarse_purity
        improvement_pct = (improvement / coarse_purity * 100) if coarse_purity > 0 else 0
        
        per_coarse_cluster[int(coarse_id)] = {
            'coarse_size': cluster_size,
            'coarse_purity': coarse_purity,
            'coarse_dominant_branch': coarse_dominant,
            'n_fine_clusters': len(sub_cluster_ids),
            'fine_purity_mean': fine_purity_mean,
            'fine_purity_values': fine_purity_values,
            'improvement': improvement,
            'improvement_pct': improvement_pct,
            'improvements': improvements,
            'deteriorations': deteriorations,
            'no_change': no_change,
            'fine_dominant_branches': dict(fine_dominant_branches),
        }
        
        total_improvements += improvements
        total_deteriorations += deteriorations
        total_no_change += no_change
    
    total_evaluated = total_improvements + total_deteriorations + total_no_change
    improvement_rate = total_improvements / total_evaluated if total_evaluated > 0 else 0
    
    overall_coarse_purity = np.mean(list(coarse_purities.values())) if coarse_purities else 0
    overall_fine_purity = np.mean([np.mean(v) for v in fine_purities_by_coarse.values()]) if fine_purities_by_coarse else 0
    overall_improvement = overall_fine_purity - overall_coarse_purity
    overall_improvement_pct = (overall_improvement / overall_coarse_purity * 100) if overall_coarse_purity > 0 else 0
    
    return {
        'coarse_overall_purity': float(overall_coarse_purity),
        'fine_overall_purity': float(overall_fine_purity),
        'overall_improvement': float(overall_improvement),
        'overall_improvement_pct': float(overall_improvement_pct),
        'total_improvements': total_improvements,
        'total_deteriorations': total_deteriorations,
        'total_no_change': total_no_change,
        'improvement_rate': float(improvement_rate),
        'per_coarse_cluster': per_coarse_cluster,
    }


def flat_baseline_comparison(embeddings, metadata, resolutions=[0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]):
    """Compute flat Leiden purities for comparison."""
    purities = {}
    for res in resolutions:
        labels, mod = leiden_clustering(embeddings, resolution=res)
        purity = compute_branch_purity(labels, metadata)
        n_clusters = len(set(labels[labels != -1]))
        purities[f"res_{res}"] = {
            'n_clusters': n_clusters,
            'modularity': float(mod),
            'purity': purity,
        }
        logger.info(f"  Flat res={res}: {n_clusters} clusters, purity={purity:.4f}")
    return purities


def main():
    logger.info("=== Hierarchical Zoom Validation on center_projected ===")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    logger.info(f"Concat baseline improvement rate: {CONCAT_BASELINE_IMPROVEMENT_RATE:.1%}")
    
    # 1. Load data
    logger.info("\n1. Loading metadata with branch info...")
    id_to_idx, metadata = load_metadata_with_branch()
    center_emb = load_center_projected()
    logger.info(f"   Metadata: {len(metadata)} decisions")
    logger.info(f"   Center projected embeddings: {center_emb.shape}")
    
    branches = Counter(m.get('branch') for m in metadata if m.get('branch'))
    logger.info(f"   Branches: {dict(branches)}")
    
    # 2. Run hierarchical Leiden (coarse=0.5, sub=3.0)
    logger.info("\n2. Running hierarchical Leiden (coarse=0.5, sub=3.0)...")
    coarse_labels, hierarchical_labels, cluster_info = hierarchical_leiden(
        center_emb, metadata, coarse_res=0.5, sub_res=3.0
    )
    
    # 3. Validate zoom coherence
    logger.info("\n3. Validating zoom coherence...")
    zoom_results = validate_zoom_coherence(coarse_labels, hierarchical_labels, cluster_info, metadata)
    
    logger.info(f"\n  Overall coarse purity: {zoom_results['coarse_overall_purity']:.4f}")
    logger.info(f"  Overall fine purity: {zoom_results['fine_overall_purity']:.4f}")
    logger.info(f"  Overall improvement: {zoom_results['overall_improvement']:.4f} ({zoom_results['overall_improvement_pct']:.1f}%)")
    logger.info(f"  Total improvements: {zoom_results['total_improvements']}")
    logger.info(f"  Total deteriorations: {zoom_results['total_deteriorations']}")
    logger.info(f"  Total no change: {zoom_results['total_no_change']}")
    logger.info(f"  Improvement rate: {zoom_results['improvement_rate']:.1%}")
    
    # 4. Flat baseline comparison
    logger.info("\n4. Flat baseline comparison...")
    flat_purities = flat_baseline_comparison(center_emb, metadata)
    best_flat_purity = max(p['purity'] for p in flat_purities.values())
    logger.info(f"  Best flat purity: {best_flat_purity:.4f}")
    
    # 5. Compare with concat baseline
    logger.info("\n5. Comparison with concat baseline...")
    logger.info(f"  Concat baseline improvement rate: {CONCAT_BASELINE_IMPROVEMENT_RATE:.1%}")
    logger.info(f"  Center_projected improvement rate: {zoom_results['improvement_rate']:.1%}")
    diff = zoom_results['improvement_rate'] - CONCAT_BASELINE_IMPROVEMENT_RATE
    logger.info(f"  Difference: {diff:+.1%}")
    
    verdict = "PASS" if zoom_results['improvement_rate'] >= CONCAT_BASELINE_IMPROVEMENT_RATE else "FAIL"
    logger.info(f"\n  VERDICT: {verdict}")
    
    # 6. Save results
    logger.info("\n6. Saving results...")
    
    def convert(obj):
        if isinstance(obj, (np.integer, np.floating)):
            return obj.item()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: convert(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert(v) for v in obj]
        return obj
    
    output = {
        "run_id": f"center_projected_hierarchical_zoom_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction_version": 6,
        "hypothesis": "Hierarchical Leiden on center_projected reveals legally coherent substructure when zooming",
        "frozen_sample": f"{len(metadata)} BGer decisions (2020-2024)",
        "frozen_metric": "Branch purity improvement from coarse to fine within hierarchical clusters",
        "success_rule": f"Improvement rate >= concat baseline ({CONCAT_BASELINE_IMPROVEMENT_RATE:.1%})",
        "embeddings": "center_projected (768 dim, pure, no TF-IDF)",
        "hierarchical_config": {
            "coarse_resolution": 0.5,
            "sub_resolution": 3.0,
            "n_coarse_clusters": len(np.unique(coarse_labels[coarse_labels != -1])),
            "n_fine_clusters": len(np.unique(hierarchical_labels[hierarchical_labels != -1])),
            "nesting_score": 1.0,
        },
        "overall_metrics": {
            "coarse_overall_purity": zoom_results['coarse_overall_purity'],
            "fine_overall_purity": zoom_results['fine_overall_purity'],
            "overall_improvement": zoom_results['overall_improvement'],
            "overall_improvement_pct": zoom_results['overall_improvement_pct'],
            "total_improvements": zoom_results['total_improvements'],
            "total_deteriorations": zoom_results['total_deteriorations'],
            "total_no_change": zoom_results['total_no_change'],
            "improvement_rate": zoom_results['improvement_rate'],
        },
        "per_coarse_cluster": zoom_results['per_coarse_cluster'],
        "flat_baseline": flat_purities,
        "concat_baseline_improvement_rate": CONCAT_BASELINE_IMPROVEMENT_RATE,
        "verdict": verdict,
    }
    
    output_path = OUTPUT_DIR / "center_projected_hierarchical_zoom_validation_results.json"
    with open(output_path, 'w') as f:
        json.dump(convert(output), f, indent=2)
    
    logger.info(f"\nResults saved to {output_path}")
    logger.info("\n=== Validation complete ===")
    
    return verdict == "PASS"


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)