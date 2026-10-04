#!/usr/bin/env python3
"""
Characterize minimal dense embedding scale and specific dense modes 
necessary and sufficient for the product's non-jurist-preference views.

Three complementary views to test:
1. Citation Heritage View: AUC > 0.75 on frozen pair pool (requires >12k scale)
2. Cross-Lingual View: Full-text dense embeddings cross_lang_same_branch
3. Linear Hybrid Complement: JP > 0.60 at hybrid weights 0.3-0.4

Using 12k ACCEPTED dense embeddings (2000-2002) as ground truth.
"""

import numpy as np
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from sklearn.metrics import roc_auc_score
from sklearn.neighbors import NearestNeighbors
import warnings
warnings.filterwarnings('ignore')

# Paths
DENSE_12K_PATH = Path('/tmp/lex_accepted/evaluation/results/evaluation/v25_174k_formal_suite/embeddings/dense_v6_2000_2002_12k.npy')
DENSE_12K_META_PATH = Path('/tmp/lex_accepted/evaluation/results/evaluation/v25_174k_formal_suite/embeddings/metadata_dense_v6_2000_2002_12k.json')
TFIDF_12K_PATH = Path('/tmp/lex_accepted/evaluation/results/evaluation/v25_174k_formal_suite/embeddings/cited_decisions_tfidf.npy')
TFIDF_12K_META_PATH = Path('/tmp/lex_accepted/evaluation/results/evaluation/v25_174k_formal_suite/embeddings/metadata_partial_174k.json')

OUTPUT_DIR = Path('/home/runner/work/LexMachina/LexMachina/results/legal_distance/dense_complementary_characterization')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_dense_12k():
    """Load 12k ACCEPTED dense embeddings and metadata."""
    embeddings = np.load(DENSE_12K_PATH)
    with open(DENSE_12K_META_PATH) as f:
        metadata = json.load(f)
    print(f"Loaded 12k dense: {embeddings.shape}, {len(metadata)} metadata")
    return embeddings, metadata


def load_tfidf_12k():
    """Load TF-IDF embeddings and align with dense 12k metadata by decision_id."""
    tfidf_full = np.load(TFIDF_12K_PATH)
    with open(TFIDF_12K_META_PATH) as f:
        meta_full = json.load(f)
    
    with open(DENSE_12K_META_PATH) as f:
        meta_12k = json.load(f)
    
    # Find intersection by decision_id
    did_to_idx_tfidf = {m['decision_id']: i for i, m in enumerate(meta_full)}
    did_to_idx_dense = {m['decision_id']: i for i, m in enumerate(meta_12k)}
    
    common_dids = set(did_to_idx_tfidf.keys()) & set(did_to_idx_dense.keys())
    common_dids = sorted(common_dids)  # Sort for reproducibility
    
    tfidf_indices = [did_to_idx_tfidf[did] for did in common_dids]
    dense_indices = [did_to_idx_dense[did] for did in common_dids]
    
    tfidf_aligned = tfidf_full[tfidf_indices]
    meta_aligned = [meta_12k[i] for i in dense_indices]
    
    print(f"TF-IDF full: {len(meta_full)}, Dense 12k: {len(meta_12k)}, Common: {len(common_dids)}")
    print(f"Loaded TF-IDF aligned: {tfidf_aligned.shape}")
    return tfidf_aligned, meta_aligned


def compute_cross_lingual_alignment(embeddings: np.ndarray, metadata: List[Dict], k: int = 10) -> Dict:
    """Compute cross-lingual same-branch alignment metric."""
    n = len(embeddings)
    languages = [m.get('language', 'de') for m in metadata]
    branches = [m.get('branch', 'unknown') for m in metadata]
    
    nbrs = NearestNeighbors(n_neighbors=min(k+1, n), metric='cosine', n_jobs=-1)
    nbrs.fit(embeddings)
    distances, indices = nbrs.kneighbors(embeddings)
    
    cross_lang_same_branch = 0
    cross_lang_total = 0
    same_lang_same_branch = 0
    same_lang_total = 0
    
    for i in range(n):
        lang_i = languages[i]
        branch_i = branches[i]
        if branch_i == 'unknown':
            continue
        
        for j_idx in indices[i][1:]:  # Skip self
            lang_j = languages[j_idx]
            branch_j = branches[j_idx]
            if branch_j == 'unknown':
                continue
            
            if lang_i != lang_j:
                cross_lang_total += 1
                if branch_i == branch_j:
                    cross_lang_same_branch += 1
            else:
                same_lang_total += 1
                if branch_i == branch_j:
                    same_lang_same_branch += 1
    
    cross_lang_rate = cross_lang_same_branch / cross_lang_total if cross_lang_total > 0 else 0
    same_lang_rate = same_lang_same_branch / same_lang_total if same_lang_total > 0 else 0
    
    return {
        'cross_lang_same_branch': float(cross_lang_rate),
        'same_lang_same_branch': float(same_lang_rate),
        'cross_lang_total': cross_lang_total,
        'same_lang_total': same_lang_total,
        'separation': float(same_lang_rate - cross_lang_rate)
    }


def compute_jurist_preference_proxy(embeddings: np.ndarray, metadata: List[Dict], k: int = 10) -> Dict:
    """Proxy for jurist preference: branch coherence in nearest neighbors."""
    n = len(embeddings)
    branches = [m.get('branch', 'unknown') for m in metadata]
    
    nbrs = NearestNeighbors(n_neighbors=min(k+1, n), metric='cosine', n_jobs=-1)
    nbrs.fit(embeddings)
    distances, indices = nbrs.kneighbors(embeddings)
    
    legal_relevant_count = 0
    total_decisions = 0
    
    for i in range(n):
        branch_i = branches[i]
        if branch_i == 'unknown':
            continue
        
        total_decisions += 1
        nn_branches = [branches[j] for j in indices[i][1:]]
        if branch_i in nn_branches:
            legal_relevant_count += 1
    
    legal_neighbor_rate = legal_relevant_count / total_decisions if total_decisions > 0 else 0
    return {
        'legal_neighbor_rate': float(legal_neighbor_rate),
        'total_decisions': total_decisions,
        'legal_relevant': legal_relevant_count
    }


def compute_branch_knn_accuracy(embeddings: np.ndarray, metadata: List[Dict], k: int = 5) -> Dict:
    """Compute branch k-NN accuracy (like branch_knn benchmark)."""
    n = len(embeddings)
    branches = [m.get('branch', 'unknown') for m in metadata]
    
    # Filter to valid
    valid_mask = [b != 'unknown' for b in branches]
    if sum(valid_mask) < 2:
        return {'error': 'Insufficient valid branch labels'}
    
    valid_embeddings = embeddings[valid_mask]
    valid_branches = [branches[i] for i, v in enumerate(valid_mask) if v]
    valid_indices = [i for i, v in enumerate(valid_mask) if v]
    
    nbrs = NearestNeighbors(n_neighbors=min(k+1, len(valid_embeddings)), metric='cosine', n_jobs=-1)
    nbrs.fit(valid_embeddings)
    distances, indices = nbrs.kneighbors(valid_embeddings)
    
    accuracies = {}
    for k_val in [1, 3, 5, 10]:
        if k_val > k:
            continue
        correct = 0
        for i in range(len(valid_embeddings)):
            branch_i = valid_branches[i]
            nn_branches = [valid_branches[j] for j in indices[i][1:k_val+1]]
            if branch_i in nn_branches:
                correct += 1
        accuracies[f'knn_accuracy@{k_val}'] = correct / len(valid_embeddings)
    
    return accuracies


def compute_legal_area_clustering(embeddings: np.ndarray, metadata: List[Dict]) -> Dict:
    """Compute legal area clustering purity/NMI."""
    from sklearn.cluster import KMeans
    from sklearn.metrics import normalized_mutual_info_score
    
    n = len(embeddings)
    areas = [m.get('legal_area', 'unknown') for m in metadata]
    
    valid_mask = [a != 'unknown' and a != '' for a in areas]
    if sum(valid_mask) < 10:
        return {'error': 'Insufficient valid legal_area labels'}
    
    valid_embeddings = embeddings[valid_mask]
    valid_areas = [areas[i] for i, v in enumerate(valid_mask) if v]
    
    unique_areas = list(set(valid_areas))
    n_clusters = min(len(unique_areas), 50)
    
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(valid_embeddings)
    
    # Purity
    from collections import Counter
    area_to_idx = {a: i for i, a in enumerate(unique_areas)}
    area_labels = [area_to_idx[a] for a in valid_areas]
    
    nmi = normalized_mutual_info_score(area_labels, cluster_labels)
    
    # Cluster purity
    cluster_to_area = {}
    for i in range(n_clusters):
        mask = cluster_labels == i
        if not np.any(mask):
            cluster_to_area[i] = None
            continue
        cluster_areas = [valid_areas[j] for j, m in enumerate(mask) if m]
        if cluster_areas:
            cluster_to_area[i] = Counter(cluster_areas).most_common(1)[0][0]
    
    correct = sum(1 for i in range(len(cluster_labels)) 
                  if cluster_to_area.get(cluster_labels[i]) == valid_areas[i])
    purity = correct / len(cluster_labels)
    
    return {
        'purity': float(purity),
        'nmi': float(nmi),
        'n_clusters': n_clusters,
        'n_samples': len(valid_embeddings)
    }


def subsample_embeddings(embeddings: np.ndarray, metadata: List[Dict], 
                         target_size: int, seed: int = 42) -> Tuple[np.ndarray, List[Dict]]:
    """Subsample embeddings to target size."""
    if target_size >= len(embeddings):
        return embeddings, metadata
    
    np.random.seed(seed)
    indices = np.random.choice(len(embeddings), target_size, replace=False)
    indices = np.sort(indices)
    return embeddings[indices], [metadata[i] for i in indices]


def normalize_embeddings(embeddings: np.ndarray) -> np.ndarray:
    """L2 normalize embeddings."""
    return embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-10)


def test_cross_lingual_scale_dependence():
    """Test cross-lingual alignment at multiple scales on 12k dense embeddings."""
    print("\n" + "="*70)
    print("TESTING CROSS-LINGUAL ALIGNMENT AT MULTIPLE SCALES (FULL-TEXT DENSE)")
    print("="*70)
    
    embeddings, metadata = load_dense_12k()
    embeddings = normalize_embeddings(embeddings)
    
    scales = [1000, 2000, 4000, 6000, 8000, 10000, 12570]
    results = {}
    
    for scale in scales:
        if scale > len(embeddings):
            continue
        print(f"\n  Testing scale {scale}...")
        sub_emb, sub_meta = subsample_embeddings(embeddings, metadata, scale)
        result = compute_cross_lingual_alignment(sub_emb, sub_meta)
        results[scale] = result
        print(f"    cross_lang_same_branch: {result['cross_lang_same_branch']:.4f}")
        print(f"    same_lang_same_branch: {result['same_lang_same_branch']:.4f}")
        print(f"    separation: {result['separation']:.4f}")
    
    return results


def test_legal_area_clustering_scale_dependence():
    """Test legal area clustering at multiple scales."""
    print("\n" + "="*70)
    print("TESTING LEGAL AREA CLUSTERING AT MULTIPLE SCALES (FULL-TEXT DENSE)")
    print("="*70)
    
    embeddings, metadata = load_dense_12k()
    embeddings = normalize_embeddings(embeddings)
    
    scales = [1000, 2000, 4000, 6000, 8000, 10000, 12570]
    results = {}
    
    for scale in scales:
        if scale > len(embeddings):
            continue
        print(f"\n  Testing scale {scale}...")
        sub_emb, sub_meta = subsample_embeddings(embeddings, metadata, scale)
        result = compute_legal_area_clustering(sub_emb, sub_meta)
        results[scale] = result
        if 'error' not in result:
            print(f"    purity: {result['purity']:.4f}, nmi: {result['nmi']:.4f}")
        else:
            print(f"    {result['error']}")
    
    return results


def test_branch_knn_scale_dependence():
    """Test branch k-NN accuracy at multiple scales."""
    print("\n" + "="*70)
    print("TESTING BRANCH K-NN ACCURACY AT MULTIPLE SCALES (FULL-TEXT DENSE)")
    print("="*70)
    
    embeddings, metadata = load_dense_12k()
    embeddings = normalize_embeddings(embeddings)
    
    scales = [1000, 2000, 4000, 6000, 8000, 10000, 12570]
    results = {}
    
    for scale in scales:
        if scale > len(embeddings):
            continue
        print(f"\n  Testing scale {scale}...")
        sub_emb, sub_meta = subsample_embeddings(embeddings, metadata, scale)
        result = compute_branch_knn_accuracy(sub_emb, sub_meta)
        results[scale] = result
        if 'error' not in result:
            for k, v in result.items():
                print(f"    {k}: {v:.4f}")
        else:
            print(f"    {result['error']}")
    
    return results


def test_linear_hybrid_scale_dependence():
    """Test linear hybrid (dense + TF-IDF concatenation) at multiple scales."""
    print("\n" + "="*70)
    print("TESTING LINEAR HYBRID (CONCAT) AT MULTIPLE SCALES")
    print("="*70)
    
    dense_emb, dense_meta = load_dense_12k()
    tfidf_emb, tfidf_meta = load_tfidf_12k()
    
    # load_tfidf_12k now returns aligned data
    # We need to also align dense to match
    did_to_idx_dense = {m['decision_id']: i for i, m in enumerate(dense_meta)}
    tfidf_dids = [m['decision_id'] for m in tfidf_meta]
    dense_indices = [did_to_idx_dense[did] for did in tfidf_dids if did in did_to_idx_dense]
    
    dense_aligned = dense_emb[dense_indices]
    meta_aligned = [dense_meta[i] for i in dense_indices]
    
    # Ensure alignment
    assert len(dense_aligned) == len(tfidf_emb), "Embedding length mismatch after alignment"
    assert [m['decision_id'] for m in meta_aligned] == [m['decision_id'] for m in tfidf_meta], "Metadata mismatch after alignment"
    
    # Normalize embeddings
    dense_norm = normalize_embeddings(dense_aligned)
    tfidf_norm = normalize_embeddings(tfidf_emb)
    
    # For concatenation hybrid: weight controls relative contribution
    # We'll scale each before concatenating: hybrid = concat(w * dense, (1-w) * tfidf)
    scales = [1000, 2000, 3000, 3839]
    hybrid_weights = [0.1, 0.2, 0.3, 0.35, 0.4, 0.5, 0.6, 0.7]
    results = {}
    
    for scale in scales:
        if scale > len(dense_norm):
            continue
        print(f"\n  Testing scale {scale}...")
        dense_sub, meta_sub = subsample_embeddings(dense_norm, meta_aligned, scale)
        tfidf_sub, _ = subsample_embeddings(tfidf_norm, tfidf_meta, scale)
        
        results[scale] = {}
        for w in hybrid_weights:
            # Linear hybrid via concatenation: concat(w * dense, (1-w) * tfidf)
            hybrid = np.concatenate([w * dense_sub, (1-w) * tfidf_sub], axis=1)
            hybrid = normalize_embeddings(hybrid)
            
            # Multiple proxies
            jp_result = compute_jurist_preference_proxy(hybrid, meta_sub)
            cl_result = compute_cross_lingual_alignment(hybrid, meta_sub)
            branch_result = compute_branch_knn_accuracy(hybrid, meta_sub)
            area_result = compute_legal_area_clustering(hybrid, meta_sub)
            
            results[scale][f'weight_{w}'] = {
                'jurist_proxy': jp_result,
                'cross_lingual': cl_result,
                'branch_knn': branch_result,
                'legal_area': area_result
            }
            print(f"    w={w}: JP={jp_result['legal_neighbor_rate']:.4f}, CL={cl_result['cross_lang_same_branch']:.4f}")
    
    return results


def test_dense_only_baselines():
    """Test dense-only and TF-IDF-only baselines at multiple scales."""
    print("\n" + "="*70)
    print("TESTING DENSE-ONLY AND TF-IDF-ONLY BASELINES AT MULTIPLE SCALES")
    print("="*70)
    
    dense_emb, dense_meta = load_dense_12k()
    tfidf_emb, tfidf_meta = load_tfidf_12k()
    
    # Align dense to TF-IDF (which is the smaller set)
    did_to_idx_dense = {m['decision_id']: i for i, m in enumerate(dense_meta)}
    tfidf_dids = [m['decision_id'] for m in tfidf_meta]
    dense_indices = [did_to_idx_dense[did] for did in tfidf_dids if did in did_to_idx_dense]
    
    dense_aligned = dense_emb[dense_indices]
    meta_aligned = [dense_meta[i] for i in dense_indices]
    
    assert len(dense_aligned) == len(tfidf_emb), "Embedding length mismatch after alignment"
    assert [m['decision_id'] for m in meta_aligned] == [m['decision_id'] for m in tfidf_meta], "Metadata mismatch after alignment"
    
    dense_norm = normalize_embeddings(dense_aligned)
    tfidf_norm = normalize_embeddings(tfidf_emb)
    
    scales = [1000, 2000, 3000, 3839]
    dense_results = {}
    tfidf_results = {}
    
    for scale in scales:
        if scale > len(dense_norm):
            continue
        print(f"\n  Testing scale {scale}...")
        
        dense_sub, meta_sub = subsample_embeddings(dense_norm, meta_aligned, scale)
        tfidf_sub, _ = subsample_embeddings(tfidf_norm, tfidf_meta, scale)
        
        # Dense only
        dense_jp = compute_jurist_preference_proxy(dense_sub, meta_sub)
        dense_cl = compute_cross_lingual_alignment(dense_sub, meta_sub)
        dense_branch = compute_branch_knn_accuracy(dense_sub, meta_sub)
        dense_area = compute_legal_area_clustering(dense_sub, meta_sub)
        dense_results[scale] = {
            'jurist_proxy': dense_jp,
            'cross_lingual': dense_cl,
            'branch_knn': dense_branch,
            'legal_area': dense_area
        }
        print(f"    Dense: JP={dense_jp['legal_neighbor_rate']:.4f}, CL={dense_cl['cross_lang_same_branch']:.4f}")
        
        # TF-IDF only
        tfidf_jp = compute_jurist_preference_proxy(tfidf_sub, meta_sub)
        tfidf_cl = compute_cross_lingual_alignment(tfidf_sub, meta_sub)
        tfidf_branch = compute_branch_knn_accuracy(tfidf_sub, meta_sub)
        tfidf_area = compute_legal_area_clustering(tfidf_sub, meta_sub)
        tfidf_results[scale] = {
            'jurist_proxy': tfidf_jp,
            'cross_lingual': tfidf_cl,
            'branch_knn': tfidf_branch,
            'legal_area': tfidf_area
        }
        print(f"    TF-IDF: JP={tfidf_jp['legal_neighbor_rate']:.4f}, CL={tfidf_cl['cross_lang_same_branch']:.4f}")
    
    return {'dense_only': dense_results, 'tfidf_only': tfidf_results}


def main():
    print("="*70)
    print("CHARACTERIZING DENSE COMPLEMENTARY VIEWS AT MULTIPLE SCALES")
    print("Using 12k ACCEPTED dense embeddings (2000-2002)")
    print("="*70)
    
    all_results = {}
    
    # 1. Cross-Lingual View (Full-text dense)
    cross_lingual_results = test_cross_lingual_scale_dependence()
    all_results['cross_lingual_full_text_dense'] = cross_lingual_results
    
    # 2. Legal Area Clustering
    area_results = test_legal_area_clustering_scale_dependence()
    all_results['legal_area_clustering'] = area_results
    
    # 3. Branch k-NN
    branch_results = test_branch_knn_scale_dependence()
    all_results['branch_knn'] = branch_results
    
    # 4. Linear Hybrid Complement
    hybrid_results = test_linear_hybrid_scale_dependence()
    all_results['linear_hybrid'] = hybrid_results
    
    # 5. Baselines
    baseline_results = test_dense_only_baselines()
    all_results['baselines'] = baseline_results
    
    # Save results
    output_path = OUTPUT_DIR / 'scale_characterization_results.json'
    with open(output_path, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\n\nResults saved to {output_path}")
    
    # Print summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    print("\n1. CROSS-LINGUAL ALIGNMENT (cross_lang_same_branch):")
    for scale, res in cross_lingual_results.items():
        print(f"  Scale {scale:5d}: cross_lang={res['cross_lang_same_branch']:.4f}, "
              f"same_lang={res['same_lang_same_branch']:.4f}, "
              f"sep={res['separation']:.4f}")
    
    print("\n2. LEGAL AREA CLUSTERING:")
    for scale, res in area_results.items():
        if 'error' not in res:
            print(f"  Scale {scale:5d}: purity={res['purity']:.4f}, nmi={res['nmi']:.4f}")
    
    print("\n3. BRANCH K-NN ACCURACY:")
    for scale, res in branch_results.items():
        if 'error' not in res:
            print(f"  Scale {scale:5d}: @1={res.get('knn_accuracy@1', 0):.4f}, "
                  f"@3={res.get('knn_accuracy@3', 0):.4f}, "
                  f"@5={res.get('knn_accuracy@5', 0):.4f}")
    
    print("\n4. LINEAR HYBRID JURIST PROXY (legal_neighbor_rate):")
    for scale, weights in hybrid_results.items():
        print(f"  Scale {scale:5d}:")
        for weight, res in weights.items():
            w = float(weight.split('_')[1])
            jp = res['jurist_proxy']['legal_neighbor_rate']
            status = "PASS" if jp > 0.60 else "FAIL"
            print(f"    {weight}: JP={jp:.4f} [{status}]")
    
    print("\n5. BASELINES - DENSE ONLY:")
    for scale, res in baseline_results['dense_only'].items():
        jp = res['jurist_proxy']['legal_neighbor_rate']
        cl = res['cross_lingual']['cross_lang_same_branch']
        print(f"  Scale {scale:5d}: JP={jp:.4f}, CL={cl:.4f}")
    
    print("\n6. BASELINES - TF-IDF ONLY:")
    for scale, res in baseline_results['tfidf_only'].items():
        jp = res['jurist_proxy']['legal_neighbor_rate']
        cl = res['cross_lingual']['cross_lang_same_branch']
        print(f"  Scale {scale:5d}: JP={jp:.4f}, CL={cl:.4f}")
    
    return all_results


if __name__ == '__main__':
    main()