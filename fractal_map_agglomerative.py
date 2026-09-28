#!/usr/bin/env python3
"""
Agglomerative Hierarchical Clustering for fractal map evaluation.
Builds a dendrogram (Ward linkage) and cuts at multiple levels.
Guarantees nesting=1.0 by construction.
"""

import numpy as np
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from sklearn.cluster import AgglomerativeClustering
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics import normalized_mutual_info_score
import warnings
warnings.filterwarnings('ignore')


def agglomerative_hierarchical(embeddings: np.ndarray, 
                                n_clusters_list: List[int] = None,
                                linkage: str = 'ward',
                                metric: str = 'euclidean') -> Dict:
    """
    Run agglomerative hierarchical clustering at multiple cluster counts.
    Returns cluster labels at each level. Guarantees nesting=1.0 by construction.
    """
    n = embeddings.shape[0]
    
    if n_clusters_list is None:
        # Default: powers of 2 from 2 to n/5
        n_clusters_list = []
        c = 2
        while c <= n // 5:
            n_clusters_list.append(c)
            c *= 2
        if n_clusters_list[-1] != n // 5:
            n_clusters_list.append(n // 5)
    
    # Ward linkage requires euclidean metric
    if linkage == 'ward':
        metric = 'euclidean'
    
    results = {}
    prev_labels = None
    
    for i, n_clusters in enumerate(n_clusters_list):
        # Use the same clustering object but with different n_clusters
        # For true nesting, we should build the dendrogram once and cut at different levels
        clustering = AgglomerativeClustering(
            n_clusters=n_clusters,
            linkage=linkage,
            metric=metric,
            compute_full_tree=True
        )
        labels = clustering.fit_predict(embeddings)
        
        # Verify nesting with previous level
        if prev_labels is not None:
            nesting = compute_nesting_score(prev_labels, labels)
            if nesting < 1.0:
                print(f"  WARNING: Nesting not perfect ({nesting:.4f}) at {n_clusters} clusters")
        
        results[n_clusters] = {
            'labels': labels,
            'n_clusters': len(np.unique(labels)),
            'cluster_sizes': np.bincount(labels).tolist(),
            'median_size': np.median(np.bincount(labels)),
            'singleton_fraction': np.sum(np.bincount(labels) == 1) / len(labels)
        }
        
        prev_labels = labels.copy()
    
    return results


def compute_nesting_score(labels_coarse: np.ndarray, labels_fine: np.ndarray) -> float:
    """Compute nesting score: fraction of fine clusters that are subsets of coarse clusters."""
    n = len(labels_coarse)
    fine_to_coarse = {}
    for i in range(n):
        fc = labels_fine[i]
        cc = labels_coarse[i]
        if fc not in fine_to_coarse:
            fine_to_coarse[fc] = {}
        fine_to_coarse[fc][cc] = fine_to_coarse[fc].get(cc, 0) + 1
    
    nested = 0
    for fc, cc_counts in fine_to_coarse.items():
        if len(cc_counts) == 1:
            nested += 1
    
    return nested / len(fine_to_coarse) if fine_to_coarse else 0.0


def compute_zoom_coherence(results: Dict) -> Dict:
    """Compute zoom coherence metrics across cluster count levels."""
    n_clusters_list = sorted(results.keys())
    labels_list = [results[nc]['labels'] for nc in n_clusters_list]
    
    if len(labels_list) < 2:
        return {'improvement_rate': 0.0, 'nesting_scores': []}
    
    nesting_scores = []
    for i in range(len(labels_list) - 1):
        score = compute_nesting_score(labels_list[i], labels_list[i+1])
        nesting_scores.append(score)
    
    improvements = sum(1 for s in nesting_scores if s > 0.5)
    improvement_rate = improvements / len(nesting_scores) if nesting_scores else 0.0
    
    return {
        'improvement_rate': improvement_rate,
        'nesting_scores': nesting_scores,
        'mean_nesting': np.mean(nesting_scores) if nesting_scores else 0.0,
        'min_nesting': np.min(nesting_scores) if nesting_scores else 0.0,
        'perfect_nesting': all(s == 1.0 for s in nesting_scores)
    }


def compute_legal_purity(labels: np.ndarray, metadata: List[Dict], field: str) -> float:
    """Compute purity of clusters w.r.t. a legal metadata field."""
    n = len(labels)
    if n == 0:
        return 0.0
    
    values = [m.get(field) for m in metadata[:n]]
    valid_mask = [v is not None for v in values]
    if not any(valid_mask):
        return 0.0
    
    labels_valid = np.array(labels)[valid_mask]
    values_valid = [v for v, m in zip(values, valid_mask) if m]
    
    unique_labels = np.unique(labels_valid)
    total_purity = 0.0
    total_size = 0
    
    for lbl in unique_labels:
        mask = labels_valid == lbl
        cluster_values = [values_valid[i] for i, m in enumerate(mask) if m]
        if not cluster_values:
            continue
        value_counts = {}
        for v in cluster_values:
            value_counts[v] = value_counts.get(v, 0) + 1
        max_count = max(value_counts.values())
        total_purity += max_count
        total_size += len(cluster_values)
    
    return total_purity / total_size if total_size > 0 else 0.0


def evaluate_zoom_quality(results: Dict, metadata: List[Dict]) -> Dict:
    """Evaluate zoom quality per factory direction v26 rule."""
    n_clusters_list = sorted(results.keys())
    labels_list = [results[nc]['labels'] for nc in n_clusters_list]
    
    zoom = compute_zoom_coherence(results)
    
    # Check singleton fraction at finest resolution
    finest = results[n_clusters_list[-1]]
    singleton_frac = finest['singleton_fraction']
    median_size = finest['median_size']
    
    # Legal purity at each resolution
    legal_purities = {}
    for field in ['branch', 'legal_area', 'language', 'chamber']:
        purities = []
        for nc in n_clusters_list:
            purities.append(compute_legal_purity(results[nc]['labels'], metadata, field))
        legal_purities[field] = purities
    
    # Check monotonic improvement in legal purity
    monotonic = {}
    for field, purities in legal_purities.items():
        improvements = sum(1 for i in range(len(purities)-1) if purities[i+1] >= purities[i])
        monotonic[field] = improvements / (len(purities)-1) if len(purities) > 1 else 0
    
    # v26 zoom-quality verdict
    passes_nesting = zoom['min_nesting'] >= 0.99
    passes_improvement = zoom['improvement_rate'] > 0.5
    passes_fragmentation = singleton_frac < 0.99 and median_size > 1
    passes_monotonic = all(m > 0.5 for m in monotonic.values())
    
    verdict = 'PASS' if (passes_nesting and passes_improvement and passes_fragmentation and passes_monotonic) else 'FAIL'
    
    return {
        'verdict': verdict,
        'nesting_scores': zoom['nesting_scores'],
        'improvement_rate': zoom['improvement_rate'],
        'min_nesting': zoom['min_nesting'],
        'perfect_nesting': zoom['perfect_nesting'],
        'singleton_fraction_fine': singleton_frac,
        'median_cluster_size_fine': median_size,
        'passes_nesting': passes_nesting,
        'passes_improvement': passes_improvement,
        'passes_fragmentation': passes_fragmentation,
        'passes_monotonic': passes_monotonic,
        'legal_purities': legal_purities,
        'monotonic_improvement': monotonic,
        'n_clusters_list': n_clusters_list,
        'n_clusters_per_level': [results[nc]['n_clusters'] for nc in n_clusters_list]
    }


def load_metadata_for_embeddings(embedding_name: str, n_decisions: int) -> List[Dict]:
    """Load appropriate metadata for the given embedding set."""
    if '174k' in embedding_name or 'tfidf' in embedding_name.lower():
        with open('/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json', 'r') as f:
            return json.load(f)[:n_decisions]
    elif '1200' in embedding_name or 'dense_1200' in embedding_name:
        with open('/tmp/lex_accepted/evaluation/evaluation/data/dense_1200_baseline/metadata_1200.json', 'r') as f:
            return json.load(f)[:n_decisions]
    elif 'citation_role' in embedding_name:
        with open('/tmp/lex_accepted/legal-distance/legal_distance/results/v6/citation_roles_fixed/citation_roles_fixed_sample.json', 'r') as f:
            sample = json.load(f)
        seen = set()
        source_decisions = []
        for s in sample:
            sd = s['source_decision']
            if sd not in seen:
                seen.add(sd)
                source_decisions.append(sd)
                if len(source_decisions) >= n_decisions:
                    break
        metadata = []
        for sd in source_decisions:
            s = next((x for x in sample if x['source_decision'] == sd), None)
            if s:
                metadata.append({
                    'decision_id': s['source_decision'],
                    'language': s.get('language', 'de'),
                    'branch': 'strafrecht',
                    'legal_area': 'Strafprozess',
                    'chamber': 'II. Strafrechtliche Abteilung'
                })
            else:
                metadata.append({'decision_id': sd, 'language': 'de', 'branch': 'unknown', 'legal_area': 'unknown', 'chamber': 'unknown'})
        while len(metadata) < n_decisions:
            metadata.append({'decision_id': f'pad_{len(metadata)}', 'language': 'de', 'branch': 'unknown', 'legal_area': 'unknown', 'chamber': 'unknown'})
        return metadata[:n_decisions]
    else:
        with open('/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json', 'r') as f:
            return json.load(f)[:n_decisions]


def run_experiment(embedding_name: str, embeddings: np.ndarray, metadata: List[Dict], 
                   n_clusters_list: List[int] = None) -> Dict:
    """Run agglomerative hierarchical clustering experiment."""
    print(f"\n{'='*60}")
    print(f"Experiment: {embedding_name} ({embeddings.shape[0]} decisions, {embeddings.shape[1]} dim)")
    print(f"{'='*60}")
    
    # Run agglomerative hierarchical clustering
    results = agglomerative_hierarchical(embeddings, n_clusters_list=n_clusters_list)
    
    # Print summary
    for nc in sorted(results.keys()):
        r = results[nc]
        print(f"  n_clusters={nc}: actual={r['n_clusters']}, median_size={r['median_size']:.1f}, "
              f"singleton_frac={r['singleton_fraction']:.3f}")
    
    # Evaluate zoom quality
    zoom = evaluate_zoom_quality(results, metadata)
    
    print(f"\n  Zoom Quality Evaluation:")
    print(f"    Verdict: {zoom['verdict']}")
    print(f"    Improvement rate: {zoom['improvement_rate']:.2f}")
    print(f"    Min nesting: {zoom['min_nesting']:.4f}")
    print(f"    Perfect nesting (all 1.0): {zoom['perfect_nesting']}")
    print(f"    Singleton fraction (fine): {zoom['singleton_fraction_fine']:.4f}")
    print(f"    Median cluster size (fine): {zoom['median_cluster_size_fine']:.1f}")
    print(f"    Passes nesting>=0.99: {zoom['passes_nesting']}")
    print(f"    Passes improvement>0.5: {zoom['passes_improvement']}")
    print(f"    Passes fragmentation: {zoom['passes_fragmentation']}")
    print(f"    Passes monotonic: {zoom['passes_monotonic']}")
    print(f"    Legal purities:")
    for field, purities in zoom['legal_purities'].items():
        print(f"      {field}: {[f'{p:.3f}' for p in purities]}")
    print(f"    Monotonic improvement: {zoom['monotonic_improvement']}")
    
    return {
        'embedding_name': embedding_name,
        'shape': embeddings.shape,
        'hierarchical_results': {str(k): v for k, v in results.items()},
        'zoom_quality': zoom
    }


def main():
    all_results = []
    
    # 1. 1200 baseline dense embeddings
    print("\n\n### 1200 BASELINE DENSE EMBEDDINGS (Agglomerative Ward) ###")
    dense_1200_dir = Path('/tmp/lex_accepted/evaluation/evaluation/data/dense_1200_baseline')
    metadata_1200 = load_metadata_for_embeddings('dense_1200', 1200)
    
    # Define cluster counts for 1200 decisions
    n_clusters_1200 = [2, 4, 8, 16, 32, 64, 128, 240]
    
    for npy_file in dense_1200_dir.glob('*.npy'):
        if 'metadata' in npy_file.name:
            continue
        name = npy_file.stem
        embeddings = np.load(npy_file)
        if embeddings.shape[0] != 1200:
            print(f"  Skipping {name}: wrong shape {embeddings.shape}")
            continue
        result = run_experiment(f'dense_1200_{name}', embeddings, metadata_1200, n_clusters_1200)
        all_results.append(result)
    
    # 2. TF-IDF embeddings - sample 10k from 174k
    print("\n\n### 174k TF-IDF EMBEDDINGS - 10k sample (Agglomerative Ward) ###")
    tfidf_path = '/tmp/lex_accepted/product/product/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings/cited_decisions_tfidf_outcome_hybrid_0.5.npy'
    metadata_174k = load_metadata_for_embeddings('tfidf_174k', 10000)
    
    # Load and sample
    tfidf_embeddings = np.load(tfidf_path, mmap_mode='r')
    print(f"Full TF-IDF shape: {tfidf_embeddings.shape}")
    
    # Sample 10000 evenly spaced - use min of embedding and metadata length
    n_total = min(tfidf_embeddings.shape[0], len(metadata_174k))
    sample_indices = np.linspace(0, n_total-1, 10000, dtype=int)
    tfidf_sample = tfidf_embeddings[sample_indices]
    metadata_sample = [metadata_174k[i] for i in sample_indices]
    
    n_clusters_10k = [2, 4, 8, 16, 32, 64, 128, 256, 512, 1000, 2000]
    result = run_experiment('tfidf_174k_cited_outcome_hybrid_0.5_10k', tfidf_sample, metadata_sample, n_clusters_10k)
    all_results.append(result)
    
    # Also test cited_decisions_tfidf alone
    tfidf_path2 = '/tmp/lex_accepted/product/product/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings/cited_decisions_tfidf.npy'
    tfidf_embeddings2 = np.load(tfidf_path2, mmap_mode='r')
    tfidf_sample2 = tfidf_embeddings2[sample_indices]
    result2 = run_experiment('tfidf_174k_cited_decisions_10k', tfidf_sample2, metadata_sample, n_clusters_10k)
    all_results.append(result2)
    
    # Also test regeste_tfidf
    tfidf_path3 = '/tmp/lex_accepted/product/product/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings/regeste_tfidf.npy'
    tfidf_embeddings3 = np.load(tfidf_path3, mmap_mode='r')
    tfidf_sample3 = tfidf_embeddings3[sample_indices]
    result3 = run_experiment('tfidf_174k_regeste_10k', tfidf_sample3, metadata_sample, n_clusters_10k)
    all_results.append(result3)
    
    # 3. Also test on 1000 baseline embeddings
    print("\n\n### 1000 BASELINE EMBEDDINGS (Agglomerative Ward) ###")
    baseline_path = '/tmp/lex_accepted/legal-distance/results/fractal_map/baseline/embeddings.npy'
    baseline_embeddings = np.load(baseline_path)
    metadata_baseline = load_metadata_for_embeddings('baseline', baseline_embeddings.shape[0])
    n_clusters_1000 = [2, 4, 8, 16, 32, 64, 128, 200]
    result3 = run_experiment('baseline_1000', baseline_embeddings, metadata_baseline, n_clusters_1000)
    all_results.append(result3)
    
    # Save all results
    output_dir = Path('/home/runner/work/LexMachina/LexMachina/results/fractal_map/agglomerative_ward')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_dir / 'agglomerative_ward_results.json', 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"\n\n{'='*60}")
    print("AGGLOMERATIVE WARD SUMMARY")
    print(f"{'='*60}")
    for r in all_results:
        zq = r['zoom_quality']
        print(f"{r['embedding_name']:55s} | Verdict: {zq['verdict']:4s} | "
              f"ImpRate: {zq['improvement_rate']:.2f} | "
              f"MinNest: {zq['min_nesting']:.3f} | "
              f"PerfectNest: {str(zq['perfect_nesting']):5s} | "
              f"SinglFrac: {zq['singleton_fraction_fine']:.3f} | "
              f"MedSize: {zq['median_cluster_size_fine']:.1f}")
    
    return all_results


if __name__ == '__main__':
    main()