#!/usr/bin/env python3
"""
Test TF-IDF embeddings at optimal resolution range (coarse to medium)
to find the sweet spot for legal navigation without fragmentation.
"""

import numpy as np
import json
from pathlib import Path
from typing import Dict, List
from sklearn.cluster import AgglomerativeClustering
import warnings
warnings.filterwarnings('ignore')


def compute_nesting_score(labels_coarse: np.ndarray, labels_fine: np.ndarray) -> float:
    n = len(labels_coarse)
    fine_to_coarse = {}
    for i in range(n):
        fc = labels_fine[i]
        cc = labels_coarse[i]
        if fc not in fine_to_coarse:
            fine_to_coarse[fc] = {}
        fine_to_coarse[fc][cc] = fine_to_coarse[fc].get(cc, 0) + 1
    nested = sum(1 for cc_counts in fine_to_coarse.values() if len(cc_counts) == 1)
    return nested / len(fine_to_coarse) if fine_to_coarse else 0.0


def compute_legal_purity(labels: np.ndarray, metadata: List[Dict], field: str) -> float:
    n = len(labels)
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
        total_purity += max(value_counts.values())
        total_size += len(cluster_values)
    return total_purity / total_size if total_size > 0 else 0.0


def test_tfidf_at_resolutions():
    """Test TF-IDF embeddings at various cluster count ranges."""
    
    # Load TF-IDF embeddings
    tfidf_path = '/tmp/lex_accepted/product/product/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings/cited_decisions_tfidf_outcome_hybrid_0.5.npy'
    tfidf_embeddings = np.load(tfidf_path, mmap_mode='r')
    print(f"Full TF-IDF shape: {tfidf_embeddings.shape}")
    
    # Load metadata
    with open('/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json', 'r') as f:
        metadata_174k = json.load(f)
    
    # Sample 20000 (larger sample for better statistics)
    n_total = min(tfidf_embeddings.shape[0], len(metadata_174k))
    sample_size = 20000
    sample_indices = np.linspace(0, n_total-1, sample_size, dtype=int)
    tfidf_sample = tfidf_embeddings[sample_indices]
    metadata_sample = [metadata_174k[i] for i in sample_indices]
    print(f"Sampled {sample_size} decisions")
    
    # Test different cluster count ranges
    # Coarse: 2-128 clusters (corpus -> domain level)
    # Medium: 256-1000 clusters (subdomain level)  
    # Fine: 2000-5000 clusters (microcluster level)
    
    ranges = {
        'coarse': [2, 4, 8, 16, 32, 64, 128],
        'medium': [256, 512, 1024, 2048],
        'fine': [4096, 8192, 16384],
        'full': [2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384]
    }
    
    for range_name, n_clusters_list in ranges.items():
        print(f"\n{'='*60}")
        print(f"TF-IDF cited_outcome_hybrid_0.5 - {range_name} range ({len(n_clusters_list)} levels)")
        print(f"{'='*60}")
        
        results = {}
        prev_labels = None
        
        for n_clusters in n_clusters_list:
            if n_clusters >= sample_size:
                continue
            clustering = AgglomerativeClustering(
                n_clusters=n_clusters,
                linkage='ward',
                metric='euclidean',
                compute_full_tree=True
            )
            labels = clustering.fit_predict(tfidf_sample)
            
            if prev_labels is not None:
                nesting = compute_nesting_score(prev_labels, labels)
                if nesting < 1.0:
                    print(f"  WARNING: Nesting not perfect ({nesting:.4f}) at {n_clusters}")
            
            results[n_clusters] = {
                'labels': labels,
                'n_clusters': len(np.unique(labels)),
                'cluster_sizes': np.bincount(labels).tolist(),
                'median_size': np.median(np.bincount(labels)),
                'singleton_fraction': np.sum(np.bincount(labels) == 1) / len(labels)
            }
            prev_labels = labels.copy()
        
        # Print summary
        for nc in sorted(results.keys()):
            r = results[nc]
            # Legal purities
            branch_pur = compute_legal_purity(r['labels'], metadata_sample, 'branch')
            area_pur = compute_legal_purity(r['labels'], metadata_sample, 'legal_area')
            lang_pur = compute_legal_purity(r['labels'], metadata_sample, 'language')
            chamber_pur = compute_legal_purity(r['labels'], metadata_sample, 'chamber')
            print(f"  n={nc:5d}: median_size={r['median_size']:6.1f}, "
                  f"singleton={r['singleton_fraction']:.4f}, "
                  f"branch={branch_pur:.3f}, area={area_pur:.3f}, "
                  f"lang={lang_pur:.3f}, chamber={chamber_pur:.3f}")
        
        # Compute zoom coherence for this range
        n_clusters_sorted = sorted(results.keys())
        labels_list = [results[nc]['labels'] for nc in n_clusters_sorted]
        nesting_scores = []
        for i in range(len(labels_list) - 1):
            nesting_scores.append(compute_nesting_score(labels_list[i], labels_list[i+1]))
        
        improvement_rate = sum(1 for s in nesting_scores if s > 0.5) / len(nesting_scores) if nesting_scores else 0
        min_nesting = min(nesting_scores) if nesting_scores else 1.0
        singleton_fine = results[n_clusters_sorted[-1]]['singleton_fraction']
        median_fine = results[n_clusters_sorted[-1]]['median_size']
        
        print(f"\n  Zoom Quality: improvement_rate={improvement_rate:.2f}, "
              f"min_nesting={min_nesting:.4f}, "
              f"singleton_fine={singleton_fine:.4f}, median_fine={median_fine:.1f}")
        
        # Check v26 pass/fail
        passes = (min_nesting >= 0.99 and improvement_rate > 0.5 and 
                  singleton_fine < 0.99 and median_fine > 1)
        print(f"  v26 Verdict: {'PASS' if passes else 'FAIL'}")
        
        # Legal purity monotonicity
        for field in ['branch', 'legal_area', 'language', 'chamber']:
            purities = [compute_legal_purity(results[nc]['labels'], metadata_sample, field) 
                       for nc in n_clusters_sorted]
            improvements = sum(1 for i in range(len(purities)-1) if purities[i+1] >= purities[i])
            mono = improvements / (len(purities)-1) if len(purities) > 1 else 0
            print(f"  {field} monotonic: {mono:.2f} (purities: {[f'{p:.3f}' for p in purities]})")


def test_tfidf_modes_comparison():
    """Compare different TF-IDF modes at a fixed medium resolution."""
    
    modes = {
        'cited_decisions_tfidf': 'cited_decisions_tfidf.npy',
        'outcome_tfidf': 'outcome_tfidf.npy',
        'cited_outcome_hybrid_0.5': 'cited_decisions_tfidf_outcome_hybrid_0.5.npy',
        'cited_outcome_hybrid_0.7': 'cited_decisions_tfidf_outcome_hybrid_0.7.npy',
        'regeste_tfidf': 'regeste_tfidf.npy',
        'full_text_tfidf_light': 'full_text_tfidf_light.npy',
        'regeste_full_text_hybrid_0.5': 'regeste_full_text_hybrid_0.5.npy',
        'regeste_full_text_hybrid_0.7': 'regeste_full_text_hybrid_0.7.npy',
    }
    
    base_path = '/tmp/lex_accepted/product/product/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings/'
    
    with open('/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json', 'r') as f:
        metadata_174k = json.load(f)
    
    sample_size = 15000
    n_total = 175440
    sample_indices = np.linspace(0, n_total-1, sample_size, dtype=int)
    metadata_sample = [metadata_174k[i] for i in sample_indices]
    
    # Test at medium resolution: 512 clusters (subdomain level)
    n_clusters = 512
    
    print(f"\n{'='*60}")
    print(f"TF-IDF MODE COMPARISON at n_clusters={n_clusters} (subdomain level)")
    print(f"{'='*60}")
    
    for mode_name, filename in modes.items():
        path = base_path + filename
        embeddings = np.load(path, mmap_mode='r')
        sample = embeddings[sample_indices]
        
        clustering = AgglomerativeClustering(
            n_clusters=n_clusters,
            linkage='ward',
            metric='euclidean',
            compute_full_tree=True
        )
        labels = clustering.fit_predict(sample)
        
        branch_pur = compute_legal_purity(labels, metadata_sample, 'branch')
        area_pur = compute_legal_purity(labels, metadata_sample, 'legal_area')
        lang_pur = compute_legal_purity(labels, metadata_sample, 'language')
        chamber_pur = compute_legal_purity(labels, metadata_sample, 'chamber')
        median_size = np.median(np.bincount(labels))
        singleton_frac = np.sum(np.bincount(labels) == 1) / len(labels)
        
        print(f"  {mode_name:35s}: branch={branch_pur:.3f}, area={area_pur:.3f}, "
              f"lang={lang_pur:.3f}, chamber={chamber_pur:.3f}, "
              f"median={median_size:.1f}, singleton={singleton_frac:.4f}")


if __name__ == '__main__':
    test_tfidf_at_resolutions()
    test_tfidf_modes_comparison()