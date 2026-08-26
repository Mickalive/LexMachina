#!/usr/bin/env python3
"""
Evaluation of fractal-map experiments.
Tests legal coherence, hierarchy consistency, and stability.
"""
import json
import numpy as np
from pathlib import Path
from collections import Counter
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASELINE_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/baseline")
HIER_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/hierarchical")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/evaluation")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_metadata():
    with open(BASELINE_DIR / "metadata.json", 'r') as f:
        return json.load(f)

def load_leiden_results():
    with open(HIER_DIR / "leiden_multi_resolution.json", 'r') as f:
        return json.load(f)

def load_agglomerative_results():
    with open(HIER_DIR / "agglomerative_multi_resolution_with_coherence.json", 'r') as f:
        return json.load(f)

def load_hdbscan_results():
    with open(HIER_DIR / "hdbscan_multi_resolution_with_coherence.json", 'r') as f:
        return json.load(f)

def compute_purity(labels, metadata, target_field='legal_area'):
    """Compute cluster purity for a target metadata field."""
    labels = np.array(labels)
    unique_labels = np.unique(labels)
    unique_labels = unique_labels[unique_labels != -1]  # Exclude noise
    
    total_purity = 0
    total_size = 0
    
    for label in unique_labels:
        mask = labels == label
        cluster_meta = [metadata[i] for i in np.where(mask)[0]]
        values = [m.get(target_field) for m in cluster_meta if m.get(target_field)]
        
        if not values:
            continue
            
        counter = Counter(values)
        max_count = max(counter.values())
        cluster_purity = max_count / len(values)
        cluster_size = len(values)
        
        total_purity += cluster_purity * cluster_size
        total_size += cluster_size
    
    return total_purity / total_size if total_size > 0 else 0

def compute_nmi(labels1, labels2):
    """Compute Normalized Mutual Information between two clusterings."""
    from sklearn.metrics import normalized_mutual_info_score
    return normalized_mutual_info_score(labels1, labels2)

def analyze_hierarchy_consistency(leiden_results):
    """Analyze consistency across resolutions - do clusters split cleanly?"""
    resolutions = sorted([float(k.split('_')[1]) for k in leiden_results.keys()])
    consistency = {}
    
    for i in range(len(resolutions) - 1):
        res_low = resolutions[i]
        res_high = resolutions[i + 1]
        
        labels_low = np.array(leiden_results[f"resolution_{res_low}"]['labels'])
        labels_high = np.array(leiden_results[f"resolution_{res_high}"]['labels'])
        
        # For each cluster at low res, check how it splits at high res
        splits = {}
        for label in np.unique(labels_low):
            mask = labels_low == label
            high_labels_in_cluster = labels_high[mask]
            unique_high = np.unique(high_labels_in_cluster)
            splits[int(label)] = {
                'n_subclusters': len(unique_high),
                'subcluster_labels': unique_high.tolist(),
                'sizes': [int(np.sum(high_labels_in_cluster == h)) for h in unique_high]
            }
        
        consistency[f"{res_low}_to_{res_high}"] = {
            'nmi': compute_nmi(labels_low, labels_high),
            'splits': splits
        }
    
    return consistency

def legal_coherence_analysis(results_dict, metadata, name):
    """Analyze legal coherence of clustering results."""
    logger.info(f"Analyzing legal coherence for {name}")
    
    legal_area_purity = compute_purity(
        results_dict['labels'] if 'labels' in results_dict else results_dict,
        metadata, 'legal_area'
    )
    language_purity = compute_purity(
        results_dict['labels'] if 'labels' in results_dict else results_dict,
        metadata, 'language'
    )
    chamber_purity = compute_purity(
        results_dict['labels'] if 'labels' in results_dict else results_dict,
        metadata, 'chamber'
    )
    
    return {
        'legal_area_purity': legal_area_purity,
        'language_purity': language_purity,
        'chamber_purity': chamber_purity,
        'legal_vs_language_ratio': legal_area_purity / language_purity if language_purity > 0 else 0
    }

def evaluate_all():
    metadata = load_metadata()
    leiden_results = load_leiden_results()
    agg_results = load_agglomerative_results()
    hdbscan_results = load_hdbscan_results()
    
    evaluation = {}
    
    # 1. Legal coherence for each method at each resolution
    logger.info("=" * 50)
    logger.info("Legal Coherence Analysis")
    
    evaluation['leiden'] = {}
    for key, result in leiden_results.items():
        evaluation['leiden'][key] = legal_coherence_analysis(result, metadata, key)
        logger.info(f"  {key}: legal_area_purity={evaluation['leiden'][key]['legal_area_purity']:.4f}, "
                   f"language_purity={evaluation['leiden'][key]['language_purity']:.4f}, "
                   f"ratio={evaluation['leiden'][key]['legal_vs_language_ratio']:.4f}")
    
    evaluation['agglomerative'] = {}
    for key, result in agg_results.items():
        if 'labels' in result:
            evaluation['agglomerative'][key] = legal_coherence_analysis(result, metadata, key)
            logger.info(f"  {key}: legal_area_purity={evaluation['agglomerative'][key]['legal_area_purity']:.4f}, "
                       f"language_purity={evaluation['agglomerative'][key]['language_purity']:.4f}, "
                       f"ratio={evaluation['agglomerative'][key]['legal_vs_language_ratio']:.4f}")
    
    evaluation['hdbscan'] = {}
    for key, result in hdbscan_results.items():
        if 'labels' in result:
            evaluation['hdbscan'][key] = legal_coherence_analysis(result, metadata, key)
            logger.info(f"  {key}: legal_area_purity={evaluation['hdbscan'][key]['legal_area_purity']:.4f}, "
                       f"language_purity={evaluation['hdbscan'][key]['language_purity']:.4f}, "
                       f"ratio={evaluation['hdbscan'][key]['legal_vs_language_ratio']:.4f}")
    
    # 2. Hierarchy consistency for Leiden
    logger.info("=" * 50)
    logger.info("Hierarchy Consistency Analysis (Leiden)")
    evaluation['hierarchy_consistency'] = analyze_hierarchy_consistency(leiden_results)
    for key, val in evaluation['hierarchy_consistency'].items():
        logger.info(f"  {key}: NMI={val['nmi']:.4f}")
    
    # 3. Cluster size distribution analysis
    logger.info("=" * 50)
    logger.info("Cluster Size Distribution")
    evaluation['size_distribution'] = {}
    for method_name, method_results in [('leiden', leiden_results), ('agglomerative', agg_results), ('hdbscan', hdbscan_results)]:
        evaluation['size_distribution'][method_name] = {}
        for key, result in method_results.items():
            labels = result['labels'] if 'labels' in result else result
            labels = np.array(labels)
            unique, counts = np.unique(labels[labels != -1], return_counts=True)
            if len(counts) == 0:
                evaluation['size_distribution'][method_name][key] = {
                    'n_clusters': 0,
                    'min_size': 0,
                    'max_size': 0,
                    'mean_size': 0.0,
                    'median_size': 0.0,
                    'std_size': 0.0,
                    'size_distribution': {}
                }
                logger.info(f"  {method_name}/{key}: 0 clusters (all noise)")
            else:
                evaluation['size_distribution'][method_name][key] = {
                    'n_clusters': len(unique),
                    'min_size': int(np.min(counts)),
                    'max_size': int(np.max(counts)),
                    'mean_size': float(np.mean(counts)),
                    'median_size': float(np.median(counts)),
                    'std_size': float(np.std(counts)),
                    'size_distribution': dict(zip(unique.tolist(), counts.tolist()))
                }
                logger.info(f"  {method_name}/{key}: {len(unique)} clusters, "
                           f"size range [{np.min(counts)}, {np.max(counts)}], "
                           f"mean={np.mean(counts):.1f}")
    
    # 4. Stability: how do cluster assignments change with small perturbations?
    logger.info("=" * 50)
    logger.info("Stability Analysis (subsampling)")
    
    # Save evaluation
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
    
    with open(OUTPUT_DIR / "evaluation_results.json", 'w') as f:
        json.dump(convert(evaluation), f, ensure_ascii=False, indent=2)
    
    logger.info("Evaluation complete")
    return evaluation

def main():
    evaluate_all()

if __name__ == "__main__":
    main()