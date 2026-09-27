#!/usr/bin/env python3
"""
Evaluate center_projected 64dim and 128dim on 16-year partial (2000-2015).
Optimized: skips boilerplate resistance on full corpus (known to fail for all).
"""

import json
import numpy as np
import logging
import time
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import Counter
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics import normalized_mutual_info_score, adjusted_rand_score
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize

sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina')
from evaluation.run_174k_formal_suite import (
    evaluate_representation,
    load_evaluation_metadata,
    prepare_metadata,
    get_adversarial_subsample,
    run_full_corpus_benchmarks_hnsw,
    run_adversarial_benchmarks_exact,
    run_cross_language_benchmarks,
    run_jurist_usability_benchmarks,
    EVALUATION_VERSION,
    GLOBAL_SEED,
    ADVERSARIAL_SUBSAMPLE,
    TEMPORAL_STABILITY_SUBSAMPLE,
    HIERARCHY_FAMILY_SUBSAMPLE,
    CHAMBER_TO_BRANCH,
    assign_branch,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
DENSE_CHECKPOINTS_DIR = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints")
FULL_METADATA_PATH = Path("/home/runner/work/LexMachina/LexMachina/evaluation/data/174k/metadata_174k.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k/center_projected_partial_2000_2015")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

COMPLETED_YEARS = list(range(2000, 2016))  # 2000-2015 inclusive


def load_dense_embeddings_subset(full_metadata: List[Dict], years: List[int]) -> Tuple[np.ndarray, List[Dict]]:
    logger.info(f"Loading dense embeddings for years {years[0]}-{years[-1]}...")
    
    full_id_to_idx = {m['decision_id']: i for i, m in enumerate(full_metadata)}
    
    target_ids = set()
    year_meta = {}
    year_emb = {}
    
    for year in years:
        meta_path = DENSE_CHECKPOINTS_DIR / f"metadata_{year}.json"
        emb_path = DENSE_CHECKPOINTS_DIR / f"embeddings_{year}.npy"
        
        with open(meta_path) as f:
            meta = json.load(f)
        emb = np.load(emb_path)
        
        year_meta[year] = meta
        year_emb[year] = emb
        
        for m in meta:
            target_ids.add(m['decision_id'])
    
    logger.info(f"Total target decisions: {len(target_ids)}")
    
    subset_metadata = []
    subset_indices = []
    
    for i, m in enumerate(full_metadata):
        if m['decision_id'] in target_ids:
            subset_metadata.append(m)
            subset_indices.append(i)
    
    logger.info(f"Subset metadata count: {len(subset_metadata)} (expected {len(target_ids)})")
    
    id_to_year_local = {}
    for year in years:
        meta = year_meta[year]
        for local_idx, m in enumerate(meta):
            id_to_year_local[m['decision_id']] = (year, local_idx)
    
    dim = year_emb[years[0]].shape[1]
    embeddings_subset = np.zeros((len(subset_metadata), dim), dtype=np.float32)
    
    for i, m in enumerate(subset_metadata):
        year, local_idx = id_to_year_local[m['decision_id']]
        embeddings_subset[i] = year_emb[year][local_idx]
    
    logger.info(f"Assembled embeddings shape: {embeddings_subset.shape}")
    
    return embeddings_subset, subset_metadata


def center_project(embeddings: np.ndarray, metadata: List[Dict]) -> np.ndarray:
    languages = sorted(set(m.get('language', 'de') for m in metadata))
    centers = {}
    for lang in languages:
        mask = np.array([m.get('language', 'de') == lang for m in metadata])
        if np.sum(mask) > 0:
            centers[lang] = embeddings[mask].mean(axis=0)
    
    debiased = np.copy(embeddings)
    for i, m in enumerate(metadata):
        lang = m.get('language', 'de')
        if lang in centers:
            debiased[i] = embeddings[i] - centers[lang]
    
    norms = np.linalg.norm(debiased, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return debiased / norms


def project_to_dim(emb: np.ndarray, target_dim: int) -> np.ndarray:
    n_samples, n_features = emb.shape
    if n_features <= target_dim:
        if n_features < target_dim:
            padding = np.zeros((n_samples, target_dim - n_features))
            return np.concatenate([emb, padding], axis=1)
        return emb
    if n_samples < target_dim + 1:
        return emb[:, :target_dim]
    pca = PCA(n_components=target_dim, random_state=GLOBAL_SEED)
    projected = pca.fit_transform(emb)
    return normalize(projected, norm='l2', axis=1)


def evaluate_representation_fast(name: str, embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Any]:
    """Fast evaluation skipping boilerplate resistance on full corpus."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Evaluating (FAST): {name}")
    logger.info(f"Shape: {embeddings.shape}")
    logger.info(f"{'='*60}")
    
    start_time = time.time()
    
    branches, languages, chambers, valid_indices, valid_mask = prepare_metadata(metadata)
    rep_valid = embeddings[valid_indices]
    meta_valid = [metadata[i] for i in valid_indices]
    
    logger.info(f"Valid decisions (known branch): {len(rep_valid)} / {len(embeddings)}")
    
    # Adversarial benchmarks (EXACT k-NN on valid subset)
    logger.info("Running adversarial benchmarks (EXACT k-NN)...")
    adv_results = run_adversarial_benchmarks_exact(embeddings, metadata)
    
    # Cross-language benchmarks (EXACT k-NN on valid subset)
    logger.info("Running cross-language benchmarks (EXACT k-NN)...")
    cross_lang_results = run_cross_language_benchmarks(embeddings, metadata)
    
    # Jurist usability benchmarks (EXACT k-NN on valid subset)
    logger.info("Running jurist usability benchmarks (EXACT k-NN)...")
    jurist_results = run_jurist_usability_benchmarks(embeddings, metadata)
    
    # Full-corpus scale benchmarks - HNSW on subsamples (SKIP boilerplate)
    logger.info("Running full-corpus scale benchmarks (HNSW on subsamples, skipping boilerplate)...")
    full_corpus_results = run_full_corpus_benchmarks_hnsw_fast(embeddings, metadata)
    
    duration = time.time() - start_time
    
    both_adv_pass = adv_results['both_pass']
    verdict = "PASS" if both_adv_pass else "FAIL"
    
    return {
        'name': name,
        'embedding_shape': list(embeddings.shape),
        'duration_seconds': duration,
        'adversarial': adv_results,
        'cross_language': cross_lang_results,
        'jurist_usability': jurist_results,
        'full_corpus': full_corpus_results,
        'verdict': verdict,
        'both_adversarial_pass': both_adv_pass,
    }


def run_full_corpus_benchmarks_hnsw_fast(embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Any]:
    """Run full-corpus scale benchmarks using sklearn exact (no boilerplate)."""
    logger.info("  Running full-corpus scale benchmarks with sklearn exact (no boilerplate)...")
    
    branches_all = np.array([assign_branch(m.get("chamber")) for m in metadata])
    languages_all = np.array([m.get("language", "unknown") for m in metadata])
    valid_mask_full = branches_all != "unknown"
    valid_indices_all = np.where(valid_mask_full)[0]
    
    results = {}
    
    # Build exact NN index on full corpus
    nn_full = NearestNeighbors(n_neighbors=max(20, 10, 10)+1, metric='cosine')
    nn_full.fit(embeddings)
    logger.info(f"  Built exact NN index for {embeddings.shape[0]} decisions")
    
    # Citation heritage - run separately
    results['citation_heritage'] = {'status': 'RUN_SEPARATELY', 'note': 'Run via validate_citation_heritage_174k.py on frozen 137k pair pool'}
    
    # Scale stability (temporal) - on 30k subsample
    logger.info("  Running scale stability (temporal) on 30k subsample...")
    np.random.seed(GLOBAL_SEED)
    n = embeddings.shape[0]
    temporal_indices = np.random.choice(n, min(TEMPORAL_STABILITY_SUBSAMPLE, n), replace=False)
    temporal_emb = embeddings[temporal_indices]
    temporal_meta = [metadata[i] for i in temporal_indices]
    
    nn_temp = NearestNeighbors(n_neighbors=11, metric='cosine')
    nn_temp.fit(temporal_emb)
    _, temp_neighbors = nn_temp.kneighbors(temporal_emb)
    temp_neighbors = temp_neighbors[:, 1:]
    
    # Compare with full corpus neighbors
    _, full_neighbors = nn_full.kneighbors(temporal_emb)
    full_neighbors = full_neighbors[:, 1:]
    
    overlaps = []
    for i in range(len(temporal_indices)):
        full_set = set(full_neighbors[i])
        temp_set = set(temp_neighbors[i])
        overlap = len(full_set & temp_set) / len(full_set) if len(full_set) > 0 else 0
        overlaps.append(overlap)
    
    results['temporal_stability'] = {
        'mean_neighbor_overlap': float(np.mean(overlaps)),
        'std_neighbor_overlap': float(np.std(overlaps)),
        'n_test_points': len(temporal_indices),
        'status': 'PASS' if np.mean(overlaps) > 0.5 else 'FAIL',
        'backend': 'sklearn_exact',
        'subsample_size': len(temporal_indices),
    }
    
    # Hierarchy family benchmarks - on 15k subsample stratified by branch
    logger.info("  Running hierarchy family benchmarks on 15k subsample...")
    if len(valid_indices_all) > HIERARCHY_FAMILY_SUBSAMPLE:
        branch_labels = branches_all[valid_indices_all]
        unique_branches = np.unique(branch_labels)
        stratified_indices = []
        per_branch = HIERARCHY_FAMILY_SUBSAMPLE // len(unique_branches)
        for branch in unique_branches:
            branch_mask = branch_labels == branch
            branch_indices = valid_indices_all[branch_mask]
            if len(branch_indices) > per_branch:
                np.random.seed(GLOBAL_SEED + hash(branch) % 1000)
                selected = np.random.choice(branch_indices, per_branch, replace=False)
            else:
                selected = branch_indices
            stratified_indices.extend(selected)
        hierarchy_indices = np.array(stratified_indices[:HIERARCHY_FAMILY_SUBSAMPLE])
    else:
        hierarchy_indices = valid_indices_all
    
    hierarchy_emb = embeddings[hierarchy_indices]
    hierarchy_meta = [metadata[i] for i in hierarchy_indices]
    hierarchy_branches = branches_all[hierarchy_indices]
    hierarchy_languages = languages_all[hierarchy_indices]
    
    nn_hierarchy = NearestNeighbors(n_neighbors=max(20, 10)+1, metric='cosine')
    nn_hierarchy.fit(hierarchy_emb)
    
    # Hierarchy coherence (Jurivoc proxy)
    legal_areas = [m.get('legal_area', 'unknown') for m in hierarchy_meta]
    legal_areas = [la if la and la != 'null' else 'unknown' for la in legal_areas]
    
    kmeans_l0 = KMeans(n_clusters=4, random_state=GLOBAL_SEED, n_init=10)
    labels_l0 = kmeans_l0.fit_predict(hierarchy_emb)
    nmi_l0 = normalized_mutual_info_score(hierarchy_branches, labels_l0)
    
    kmeans_l1 = KMeans(n_clusters=16, random_state=GLOBAL_SEED, n_init=10)
    labels_l1 = kmeans_l1.fit_predict(hierarchy_emb)
    nmi_l1 = normalized_mutual_info_score(legal_areas, labels_l1)
    
    # Nesting score
    nesting_score = 0.0
    for l0_cluster in range(4):
        mask = labels_l0 == l0_cluster
        if np.sum(mask) > 0:
            l1_subclusters = labels_l1[mask]
            subcluster_purities = []
            for sub in np.unique(l1_subclusters):
                sub_mask = (labels_l1 == sub)
                if np.sum(sub_mask) > 0:
                    branch_in_sub = [hierarchy_branches[i] for i in np.where(sub_mask)[0]]
                    majority = Counter(branch_in_sub).most_common(1)[0][1]
                    subcluster_purities.append(majority / len(branch_in_sub))
            if subcluster_purities:
                nesting_score += np.mean(subcluster_purities)
    nesting_score /= 4
    
    results['hierarchy_coherence'] = {
        'level_0_nmi': float(nmi_l0),
        'level_1_nmi': float(nmi_l1),
        'nesting_score': float(nesting_score),
        'status': 'PASS' if nmi_l0 > 0.3 and nmi_l1 > 0.2 else 'FAIL',
        'backend': 'sklearn_exact',
        'subsample_size': len(hierarchy_indices),
    }
    
    # Cluster coherence
    kmeans = KMeans(n_clusters=16, random_state=GLOBAL_SEED, n_init=10)
    cluster_labels = kmeans.fit_predict(hierarchy_emb)
    
    branch_purities = []
    lang_purities = []
    for c in range(16):
        mask = cluster_labels == c
        if np.sum(mask) == 0:
            continue
        cluster_branches = hierarchy_branches[mask]
        cluster_langs = hierarchy_languages[mask]
        
        if len(cluster_branches) > 0:
            branch_counts = Counter(cluster_branches)
            branch_purity = max(branch_counts.values()) / len(cluster_branches)
            branch_purities.append(branch_purity)
        
        if len(cluster_langs) > 0:
            lang_counts = Counter(cluster_langs)
            lang_purity = max(lang_counts.values()) / len(cluster_langs)
            lang_purities.append(lang_purity)
    
    mean_purity = np.mean(branch_purities) if branch_purities else 0
    mean_lang_purity = np.mean(lang_purities) if lang_purities else 0
    nmi = normalized_mutual_info_score(hierarchy_branches, cluster_labels)
    
    results['cluster_coherence'] = {
        'status': 'PASS' if mean_purity > 0.7 else 'FAIL',
        'n_clusters': 16,
        'mean_branch_purity': round(float(mean_purity), 4),
        'branch_nmi': round(float(nmi), 4),
        'mean_language_purity': round(float(mean_lang_purity), 4),
        'cluster_purities': [round(p, 4) for p in branch_purities],
        'backend': 'sklearn_exact',
    }
    
    # Cross-language retrieval (full)
    unique_langs = list(set(hierarchy_languages))
    recalls = []
    _, h_neighbors = nn_hierarchy.kneighbors(hierarchy_emb)
    h_neighbors = h_neighbors[:, 1:]
    
    for source_lang in unique_langs:
        source_mask = np.array([l == source_lang for l in hierarchy_languages])
        source_indices = np.where(source_mask)[0]
        
        if len(source_indices) == 0:
            continue
        
        for target_lang in unique_langs:
            if source_lang == target_lang:
                continue
            
            target_mask = np.array([l == target_lang for l in hierarchy_languages])
            target_indices = set(np.where(target_mask)[0])
            
            if len(target_indices) == 0:
                continue
            
            hits = 0
            for src_idx in source_indices:
                src_branch = hierarchy_branches[src_idx]
                neighbor_branches = hierarchy_branches[h_neighbors[src_idx]]
                neighbor_langs = hierarchy_languages[h_neighbors[src_idx]]
                
                for nb, nl in zip(neighbor_branches, neighbor_langs):
                    if nl == target_lang and nb == src_branch:
                        hits += 1
                        break
            
            recall = hits / len(source_indices) if len(source_indices) > 0 else 0
            recalls.append(recall)
    
    mean_recall = np.mean(recalls) if recalls else 0
    
    results['cross_language_retrieval_full'] = {
        'mean_cross_language_recall_at_k': float(mean_recall),
        'status': 'PASS' if mean_recall > 0.2 else 'FAIL',
        'backend': 'sklearn_exact',
    }
    
    # SKIP boilerplate resistance (known to fail for all representations at this scale)
    results['boilerplate_resistance'] = {
        'status': 'SKIPPED',
        'note': 'Boilerplate resistance known to fail for all representations; skipped for speed. See raw multilingual-e5 evaluation for reference (-0.93).'
    }
    
    return results


def main():
    # Load full metadata
    logger.info("Loading full 174k metadata...")
    with open(FULL_METADATA_PATH) as f:
        full_metadata = json.load(f)
    logger.info(f"Full metadata: {len(full_metadata)} decisions")
    
    # Load and assemble dense embeddings for years 2000-2015
    embeddings_raw, subset_metadata = load_dense_embeddings_subset(full_metadata, COMPLETED_YEARS)
    
    # Create center_projected version
    logger.info("Creating center_projected version...")
    embeddings_cp = center_project(embeddings_raw, subset_metadata)
    
    # Create 64-dim and 128-dim versions
    logger.info("Creating 64-dim version...")
    embeddings_cp_64 = project_to_dim(embeddings_cp, 64)
    
    logger.info("Creating 128-dim version...")
    embeddings_cp_128 = project_to_dim(embeddings_cp, 128)
    
    # Evaluate 64dim and 128dim versions (768dim already done)
    representations = {
        'center_projected_64dim_partial_2000_2015': embeddings_cp_64,
        'center_projected_128dim_partial_2000_2015': embeddings_cp_128,
    }
    
    all_results = {}
    
    for name, emb in representations.items():
        result = evaluate_representation_fast(name, emb, subset_metadata)
        all_results[name] = result
        
        # Save individual result
        from datetime import datetime
        output_file = OUTPUT_DIR / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        # Print summary
        if 'error' not in result:
            adv = result['adversarial']
            logger.info(f"\n{'='*70}")
            logger.info(f"SUMMARY: {name}")
            logger.info(f"{'='*70}")
            logger.info(f"Verdict: {result['verdict']}")
            logger.info(f"Language dominance: {adv['language_dominance_score']:.4f} ({adv['adversarial_language_dominance']['status']})")
            logger.info(f"Jurist preference: {adv['jurist_preference_rate']:.4f} ({adv['jurist_pairwise_preference']['status']})")
            logger.info(f"Both adversarial pass: {adv['both_pass']}")
            logger.info(f"Backend: {adv.get('backend', 'N/A')}")
            logger.info(f"Subset size: {adv.get('subset_size', 'N/A')}")
    
    # Save combined results (including the already-saved 768dim)
    # Load existing 768dim result
    existing_768 = None
    for f in OUTPUT_DIR.glob("center_projected_768dim_partial_2000_2015_*.json"):
        with open(f) as fp:
            existing_768 = json.load(fp)
        break
    
    combined_results = {}
    if existing_768:
        combined_results['center_projected_768dim_partial_2000_2015'] = existing_768
    combined_results.update(all_results)
    
    from datetime import datetime
    combined_file = OUTPUT_DIR / f"center_projected_16year_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(combined_file, 'w') as f:
        json.dump(combined_results, f, indent=2, default=str)
    
    latest_file = OUTPUT_DIR / "center_projected_16year_eval_latest.json"
    with open(latest_file, 'w') as f:
        json.dump(combined_results, f, indent=2, default=str)
    
    logger.info(f"\nCombined results saved to: {combined_file}")
    logger.info(f"Latest symlink: {latest_file}")
    
    # Overall summary
    logger.info("\n" + "=" * 80)
    logger.info("CENTER_PROJECTED 16-YEAR PARTIAL EVALUATION SUMMARY (Years 2000-2015)")
    logger.info("=" * 80)
    
    for name, result in combined_results.items():
        if 'error' in result:
            logger.info(f"\n{name}: ERROR - {result['error']}")
            continue
            
        adv = result['adversarial']
        cross = result.get('cross_language', {})
        jurist = result.get('jurist_usability', {})
        full = result.get('full_corpus', {})
        
        logger.info(f"\n--- {name} ---")
        logger.info(f"Verdict: {result['verdict']}")
        logger.info(f"Both adversarial pass: {result['both_adversarial_pass']}")
        logger.info(f"  Language Dominance: {adv['language_dominance_score']:.4f} ({adv['adversarial_language_dominance']['status']})")
        logger.info(f"  Jurist Pairwise: {adv['jurist_preference_rate']:.4f} ({adv['jurist_pairwise_preference']['status']})")
        
        if cross:
            cl_nq = cross.get('cross_language_neighbor_quality', {})
            zscl = cross.get('zero_shot_cross_language_transfer', {})
            lsrq = cross.get('language_specific_representation_quality', {})
            logger.info(f"  Cross-Lang Neighbor Quality: gap={cl_nq.get('invariance_gap', 'N/A'):.4f} ({cl_nq.get('status', 'N/A')})")
            logger.info(f"  Zero-Shot Transfer: gap={zscl.get('transfer_gap', 'N/A'):.4f} ({zscl.get('status', 'N/A')})")
            logger.info(f"  Lang-Specific Quality: mean_nmi={lsrq.get('mean_nmi', 'N/A'):.4f} ({lsrq.get('status', 'N/A')})")
        
        if jurist:
            cc = jurist.get('cluster_coherence_rating', {})
            clr = jurist.get('cross_language_retrieval', {})
            logger.info(f"  Cluster Coherence: branch_purity={cc.get('mean_branch_purity', 'N/A'):.4f} ({cc.get('status', 'N/A')})")
            logger.info(f"  Cross-Lang Retrieval: recall={clr.get('mean_cross_language_recall_at_k', 'N/A'):.4f} ({clr.get('status', 'N/A')})")
        
        if full:
            hc = full.get('hierarchy_coherence', {})
            ts = full.get('temporal_stability', {})
            cc_full = full.get('cluster_coherence', {})
            clr_full = full.get('cross_language_retrieval_full', {})
            bp = full.get('boilerplate_resistance', {})
            logger.info(f"  Hierarchy Level 0 NMI: {hc.get('level_0_nmi', 'N/A'):.4f}")
            logger.info(f"  Hierarchy Level 1 NMI: {hc.get('level_1_nmi', 'N/A'):.4f}")
            logger.info(f"  Nesting Score: {hc.get('nesting_score', 'N/A'):.4f}")
            logger.info(f"  Scale Stability: {ts.get('mean_neighbor_overlap', 'N/A'):.4f}")
            logger.info(f"  Cluster Coherence (15k): branch_purity={cc_full.get('mean_branch_purity', 'N/A'):.4f} ({cc_full.get('status', 'N/A')})")
            logger.info(f"  Cross-Lang Retrieval (15k): recall={clr_full.get('mean_cross_language_recall_at_k', 'N/A'):.4f} ({clr_full.get('status', 'N/A')})")
            logger.info(f"  Boilerplate: {bp.get('status', 'N/A')}")
    
    # Find best representation
    valid_results = {k: v for k, v in combined_results.items() if 'error' not in v and v['both_adversarial_pass']}
    if valid_results:
        best = max(valid_results.items(), key=lambda x: (x[1]['adversarial']['jurist_preference_rate'],
                                                         -x[1]['adversarial']['language_dominance_score']))
        logger.info(f"\n🏆 BEST REPRESENTATION (passing both adversarial gates): {best[0]}")
    else:
        logger.info("\n⚠️  NO REPRESENTATION PASSES BOTH ADVERSARIAL GATES")
    
    logger.info("=" * 80)
    
    return combined_results


if __name__ == "__main__":
    main()