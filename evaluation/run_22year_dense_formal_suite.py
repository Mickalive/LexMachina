#!/usr/bin/env python3
"""
Evaluation Lane - 22-Year Dense Formal Suite (144k decisions, 2000-2021)
Runs the formal benchmark suite on 22-year dense linear combinations.
Independently verifies legal-distance results for linear_citation_concat and linear_hybrid05_concat.
"""

import json
import numpy as np
import logging
import time
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from collections import Counter, defaultdict
from datetime import datetime
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
    assign_branch,
    LANGUAGE_DOMINANCE_THRESHOLD,
    JURIST_PAIRWISE_THRESHOLD,
    CROSS_LANG_RECALL_THRESHOLD,
    CLUSTER_COHERENCE_THRESHOLD,
    K_NEIGHBORS_LANG_DOM_FROZEN,
    K_NEIGHBORS_JURIST_FROZEN,
    K_NEIGHBORS_CROSS_LANG_FROZEN,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
DENSE_CHECKPOINTS_DIR = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints")
TFIDF_EMBEDDINGS_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k/embeddings")
FULL_METADATA_PATH = Path("/home/runner/work/LexMachina/LexMachina/evaluation/data/174k/metadata_174k.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k/formal_suite/22year_dense_linear")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

COMPLETED_YEARS = list(range(2000, 2022))  # 2000-2021 inclusive (22 years)

def load_dense_embeddings_subset(full_metadata: List[Dict], years: List[int]) -> Tuple[np.ndarray, List[Dict]]:
    """Load dense embeddings for specified years and assemble in full metadata order."""
    logger.info(f"Loading dense embeddings for years {years[0]}-{years[-1]}...")
    
    # Build decision_id -> index mapping for full metadata
    full_id_to_idx = {m['decision_id']: i for i, m in enumerate(full_metadata)}
    
    # Collect all decision_ids for the target years
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
    
    logger.info(f"Total target decisions from checkpoints: {len(target_ids)}")
    
    # Filter full metadata to only target decisions, preserving order
    subset_metadata = []
    subset_indices = []
    
    for i, m in enumerate(full_metadata):
        if m['decision_id'] in target_ids:
            subset_metadata.append(m)
            subset_indices.append(i)
    
    logger.info(f"Subset metadata count (in full metadata order): {len(subset_metadata)} (expected {len(target_ids)})")
    
    # Now assemble embeddings in the same order as subset_metadata
    # Build a lookup: decision_id -> (year, local_index)
    id_to_year_local = {}
    for year in years:
        meta = year_meta[year]
        for local_idx, m in enumerate(meta):
            id_to_year_local[m['decision_id']] = (year, local_idx)
    
    # Assemble embeddings
    dim = year_emb[years[0]].shape[1]
    embeddings_subset = np.zeros((len(subset_metadata), dim), dtype=np.float32)
    
    for i, m in enumerate(subset_metadata):
        year, local_idx = id_to_year_local[m['decision_id']]
        embeddings_subset[i] = year_emb[year][local_idx]
    
    logger.info(f"Assembled dense embeddings shape: {embeddings_subset.shape}")
    
    return embeddings_subset, subset_metadata


def load_tfidf_for_subset(tfidf_filename: str, subset_metadata: List[Dict], full_metadata: List[Dict]) -> np.ndarray:
    """Load TF-IDF embeddings for the subset decisions."""
    logger.info(f"Loading {tfidf_filename} for subset...")
    
    # Load full TF-IDF
    tfidf_path = TFIDF_EMBEDDINGS_DIR / tfidf_filename
    tfidf = np.load(tfidf_path, mmap_mode='r')
    logger.info(f"Full TF-IDF shape: {tfidf.shape}")
    
    # Build decision_id -> index mapping for full metadata
    full_id_to_idx = {m['decision_id']: i for i, m in enumerate(full_metadata)}
    
    # Extract embeddings for subset
    n_subset = len(subset_metadata)
    tfidf_dim = tfidf.shape[1]
    subset_tfidf = np.zeros((n_subset, tfidf_dim), dtype=np.float32)
    
    for i, m in enumerate(subset_metadata):
        full_idx = full_id_to_idx[m['decision_id']]
        subset_tfidf[i] = tfidf[full_idx]
    
    logger.info(f"Extracted subset TF-IDF shape: {subset_tfidf.shape}")
    return subset_tfidf


def create_center_projected_64(dense_emb: np.ndarray, metadata: List[Dict]) -> np.ndarray:
    """Apply language center projection and PCA to 64 dim."""
    logger.info("Applying language center projection to dense embeddings...")
    languages = [m.get('language', 'de') for m in metadata]
    unique_langs = sorted(set(languages))
    centers = {}
    for lang in unique_langs:
        mask = np.array([l == lang for l in languages])
        if np.sum(mask) > 0:
            centers[lang] = dense_emb[mask].mean(axis=0)
    
    dense_cp = np.copy(dense_emb)
    for i, lang in enumerate(languages):
        if lang in centers:
            dense_cp[i] = dense_emb[i] - centers[lang]
    
    # L2 normalize
    norms = np.linalg.norm(dense_cp, axis=1, keepdims=True)
    norms[norms == 0] = 1
    dense_cp = dense_cp / norms
    logger.info(f"Center-projected dense shape: {dense_cp.shape}")
    
    # Apply PCA to 64 dim
    logger.info("Applying PCA to 64 dimensions...")
    pca = PCA(n_components=64, random_state=GLOBAL_SEED)
    dense_cp_64 = pca.fit_transform(dense_cp)
    dense_cp_64 = normalize(dense_cp_64, norm='l2', axis=1)
    logger.info(f"Dense CP 64 shape: {dense_cp_64.shape}, explained var: {pca.explained_variance_ratio_.sum():.4f}")
    
    return dense_cp_64


def create_concat(dense_emb: np.ndarray, citation_emb: np.ndarray) -> np.ndarray:
    """Concatenate dense and citation embeddings."""
    logger.info(f"Concatenating: dense {dense_emb.shape} + citation {citation_emb.shape}")
    concat = np.hstack([dense_emb, citation_emb])
    logger.info(f"Concatenated shape: {concat.shape}")
    return concat


def run_citation_heritage_on_subset(embeddings: np.ndarray, subset_metadata: List[Dict], name: str) -> Dict[str, Any]:
    """Run citation heritage benchmark on subset using frozen 174k citation pairs."""
    logger.info(f"  Running citation heritage on {name}...")
    
    # Load frozen citation pairs
    CITATION_PAIRS_PATH = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k_citation_heritage/citation_pairs_174k.json")
    with open(CITATION_PAIRS_PATH, 'r') as f:
        pairs_data = json.load(f)
    
    positive_pairs = [tuple(p) for p in pairs_data['positive_pairs']]
    negative_pairs = [tuple(p) for p in pairs_data['negative_pairs']]
    
    # Build decision_id -> index mapping for subset
    did_to_idx = {m['decision_id']: i for i, m in enumerate(subset_metadata)}
    
    # Compute similarities for positive pairs
    pos_sims = []
    for did1, did2 in positive_pairs:
        if did1 in did_to_idx and did2 in did_to_idx:
            idx1 = did_to_idx[did1]
            idx2 = did_to_idx[did2]
            v1 = embeddings[idx1]
            v2 = embeddings[idx2]
            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)
            if norm1 > 0 and norm2 > 0:
                sim = np.dot(v1, v2) / (norm1 * norm2)
                pos_sims.append(sim)
    
    # Compute similarities for negative pairs
    neg_sims = []
    for did1, did2 in negative_pairs:
        if did1 in did_to_idx and did2 in did_to_idx:
            idx1 = did_to_idx[did1]
            idx2 = did_to_idx[did2]
            v1 = embeddings[idx1]
            v2 = embeddings[idx2]
            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)
            if norm1 > 0 and norm2 > 0:
                sim = np.dot(v1, v2) / (norm1 * norm2)
                neg_sims.append(sim)
    
    pos_sims = np.array(pos_sims)
    neg_sims = np.array(neg_sims)
    
    logger.info(f"  Positive similarities: {len(pos_sims)}, mean={np.mean(pos_sims) if len(pos_sims) > 0 else 0:.4f}")
    logger.info(f"  Negative similarities: {len(neg_sims)}, mean={np.mean(neg_sims) if len(neg_sims) > 0 else 0:.4f}")
    
    if len(pos_sims) == 0 or len(neg_sims) == 0:
        return {
            'auc_roc': 0.0,
            'recall_at_10': 0.0,
            'num_positive_pairs': len(pos_sims),
            'num_negative_pairs': len(neg_sims),
            'status': 'INSUFFICIENT_PAIRS',
            'note': 'Not enough positive/negative pairs in this subset'
        }
    
    # Compute AUC-ROC
    from sklearn.metrics import roc_auc_score
    y_true = np.concatenate([np.ones(len(pos_sims)), np.zeros(len(neg_sims))])
    y_score = np.concatenate([pos_sims, neg_sims])
    auc_roc = roc_auc_score(y_true, y_score)
    
    # Compute recall@10 using exact k-NN
    from sklearn.neighbors import NearestNeighbors
    nn = NearestNeighbors(n_neighbors=10, metric='cosine')
    nn.fit(embeddings)
    all_neighbors = nn.kneighbors(n_neighbors=10)[1]
    
    # Build adjacency: decision -> set of cited decisions
    cited_map = {}
    for did1, did2 in positive_pairs:
        if did1 not in cited_map:
            cited_map[did1] = set()
        cited_map[did1].add(did2)
        if did2 not in cited_map:
            cited_map[did2] = set()
        cited_map[did2].add(did1)
    
    recall_10_sum = 0
    recall_10_count = 0
    for did, cited_set in cited_map.items():
        if did not in did_to_idx:
            continue
        idx = did_to_idx[did]
        neighbors = all_neighbors[idx]
        found = sum(1 for c in cited_set if c in did_to_idx and did_to_idx[c] in neighbors)
        recall = found / min(len(cited_set), 10) if cited_set else 0
        recall_10_sum += recall
        recall_10_count += 1
    
    mean_recall_at_10 = recall_10_sum / recall_10_count if recall_10_count > 0 else 0
    
    return {
        'auc_roc': float(auc_roc),
        'auc_roc_status': 'PASS' if auc_roc >= 0.65 else 'FAIL',
        'recall_at_10': float(mean_recall_at_10),
        'recall_at_10_status': 'PASS' if mean_recall_at_10 >= 0.2 else 'FAIL',
        'num_positive_pairs': int(len(pos_sims)),
        'num_negative_pairs': int(len(neg_sims)),
        'threshold_auc': 0.65,
        'threshold_recall': 0.2,
    }


def run_v17b_label_normalization_on_subset(embeddings: np.ndarray, subset_metadata: List[Dict], name: str) -> Dict[str, Any]:
    """Run v17b label normalization test on subset."""
    logger.info(f"  Running v17b label normalization on {name}...")
    
    from evaluation.experiments.legal_area_normalize import normalize_legal_area
    
    # Create raw and normalized labels
    raw_labels = [m.get('legal_area', 'unknown') for m in subset_metadata]
    normalized_labels = [normalize_legal_area(l) for l in raw_labels]
    
    n_normalized = sum(1 for r, n in zip(raw_labels, normalized_labels) if r != n)
    logger.info(f"  Labels normalized: {n_normalized}/{len(subset_metadata)} ({100*n_normalized/len(subset_metadata):.1f}%)")
    
    # Convert to integer labels
    raw_unique = sorted(set(raw_labels))
    raw_to_idx = {v: i for i, v in enumerate(raw_unique)}
    raw_int = np.array([raw_to_idx[v] for v in raw_labels])
    
    norm_unique = sorted(set(normalized_labels))
    norm_to_idx = {v: i for i, v in enumerate(norm_unique)}
    norm_int = np.array([norm_to_idx[v] for v in normalized_labels])
    
    def run_benchmarks(labels, label_type):
        """Run hierarchy coherence, zoom coherence, legal_area clustering."""
        # Use sample for speed
        np.random.seed(GLOBAL_SEED)
        n_sample = min(15000, len(embeddings))
        sample_indices = np.random.choice(len(embeddings), n_sample, replace=False)
        sample_emb = embeddings[sample_indices]
        sample_labels = labels[sample_indices]
        
        # Hierarchy coherence (16 clusters)
        from sklearn.cluster import KMeans
        from sklearn.metrics import normalized_mutual_info_score, adjusted_rand_score
        
        n_areas = len(np.unique(sample_labels))
        kmeans = KMeans(n_clusters=min(16, n_areas), random_state=GLOBAL_SEED, n_init=10)
        cluster_labels = kmeans.fit_predict(sample_emb)
        
        nmi = normalized_mutual_info_score(sample_labels, cluster_labels)
        ari = adjusted_rand_score(sample_labels, cluster_labels)
        
        # Purity
        purity_sum = 0
        for c in range(min(16, n_areas)):
            mask = cluster_labels == c
            if mask.sum() == 0:
                continue
            gt_in_cluster = sample_labels[mask]
            most_common = np.bincount(gt_in_cluster).max()
            purity_sum += most_common
        purity = purity_sum / n_sample
        
        # Zoom coherence (coarse=4, fine=16)
        kmeans_coarse = KMeans(n_clusters=4, random_state=GLOBAL_SEED, n_init=10)
        coarse_labels = kmeans_coarse.fit_predict(sample_emb)
        
        kmeans_fine = KMeans(n_clusters=16, random_state=GLOBAL_SEED, n_init=10)
        fine_labels = kmeans_fine.fit_predict(sample_emb)
        
        nesting_violations = 0
        for c in range(16):
            mask = fine_labels == c
            if mask.sum() == 0:
                continue
            coarse_in_fine = coarse_labels[mask]
            if len(np.unique(coarse_in_fine)) > 1:
                nesting_violations += 1
        
        nesting_score = 1.0 - (nesting_violations / 16)
        fine_nmi = normalized_mutual_info_score(sample_labels, fine_labels)
        coarse_nmi = normalized_mutual_info_score(sample_labels, coarse_labels)
        
        # Legal area clustering (n_areas clusters)
        kmeans_la = KMeans(n_clusters=n_areas, random_state=GLOBAL_SEED, n_init=10)
        la_labels = kmeans_la.fit_predict(sample_emb)
        la_nmi = normalized_mutual_info_score(sample_labels, la_labels)
        la_ari = adjusted_rand_score(sample_labels, la_labels)
        
        la_purity_sum = 0
        for c in range(n_areas):
            mask = la_labels == c
            if mask.sum() == 0:
                continue
            gt_in_cluster = sample_labels[mask]
            most_common = np.bincount(gt_in_cluster).max()
            la_purity_sum += most_common
        la_purity = la_purity_sum / n_sample
        
        return {
            'hierarchy_coherence': {'best_purity': purity, 'nmi': float(nmi), 'ari': float(ari)},
            'zoom_coherence': {'fine_purity': float(fine_nmi), 'nesting_score': float(nesting_score), 'coarse_nmi': float(coarse_nmi)},
            'legal_area_clustering': {'overall_purity': float(la_purity), 'nmi': float(la_nmi), 'num_areas': n_areas},
        }
    
    raw_res = run_benchmarks(raw_int, "raw")
    norm_res = run_benchmarks(norm_int, "normalized")
    
    def ratio(a, b):
        return round((a / b), 4) if b else None
    
    return {
        'raw': raw_res,
        'normalized': norm_res,
        'purity_ratios_norm_over_raw': {
            'hierarchy': ratio(norm_res["hierarchy_coherence"]["best_purity"], raw_res["hierarchy_coherence"]["best_purity"]),
            'zoom_fine': ratio(norm_res["zoom_coherence"]["fine_purity"], raw_res["zoom_coherence"]["fine_purity"]),
            'legal_area': ratio(norm_res["legal_area_clustering"]["overall_purity"], raw_res["legal_area_clustering"]["overall_purity"]),
        },
        'norm_num_areas': norm_res["legal_area_clustering"]["num_areas"],
        'n_labels_normalized': n_normalized,
    }


def main():
    logger.info("=" * 70)
    logger.info(f"Evaluation Lane - 22-Year Dense Linear Combinations Formal Suite")
    logger.info(f"Scale: 22 years (2000-2021), ~144k decisions")
    logger.info(f"Using {EVALUATION_VERSION} with HNSW artifact fix")
    logger.info("=" * 70)
    
    # Load full metadata
    logger.info("\n1. Loading full 174k metadata...")
    with open(FULL_METADATA_PATH) as f:
        full_metadata = json.load(f)
    logger.info(f"Full metadata: {len(full_metadata)} decisions")
    
    # Load 22-year dense embeddings and create center_projected_64
    logger.info("\n2. Loading 22-year dense embeddings and creating center_projected_64...")
    dense_emb, subset_metadata = load_dense_embeddings_subset(full_metadata, COMPLETED_YEARS)
    dense_cp_64 = create_center_projected_64(dense_emb, subset_metadata)
    
    # Load TF-IDF embeddings for subset
    logger.info("\n3. Loading TF-IDF embeddings for 22-year subset...")
    citation_tfidf_raw = load_tfidf_for_subset("cited_decisions_tfidf.npy", subset_metadata, full_metadata)
    citation_tfidf_hybrid = load_tfidf_for_subset("cited_decisions_tfidf_outcome_hybrid_0.5.npy", subset_metadata, full_metadata)
    
    # Create linear combinations
    logger.info("\n4. Creating linear combinations...")
    linear_citation_concat = create_concat(dense_cp_64, citation_tfidf_raw)
    linear_hybrid05_concat = create_concat(dense_cp_64, citation_tfidf_hybrid)
    
    # Representations to evaluate
    representations = {
        'center_projected_64_22year': dense_cp_64,
        'cited_decisions_tfidf_dense_22year': citation_tfidf_raw,
        'cited_decisions_tfidf_outcome_hybrid_0.5_22year': citation_tfidf_hybrid,
        'linear_citation_concat_22year': linear_citation_concat,
        'linear_hybrid05_concat_22year': linear_hybrid05_concat,
    }
    
    # Evaluate each representation
    logger.info("\n5. Running formal suite evaluations...")
    all_results = {}
    
    for name, embeddings in representations.items():
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"Evaluating: {name} ({embeddings.shape})")
            logger.info(f"{'='*60}")
            
            result = evaluate_representation(name, embeddings, subset_metadata)
            all_results[name] = result
            
            if 'error' in result:
                logger.error(f"  {name}: ERROR - {result['error']}")
            else:
                adv = result['adversarial']
                logger.info(f"  {name}: verdict={result['verdict']}, "
                           f"lang_dom={adv['language_dominance_score']:.4f} "
                           f"({'PASS' if adv['adversarial_language_dominance']['status']=='PASS' else 'FAIL'}), "
                           f"jurist_pref={adv['jurist_preference_rate']:.4f} "
                           f"({'PASS' if adv['jurist_pairwise_preference']['status']=='PASS' else 'FAIL'}), "
                           f"backend={adv.get('backend', 'N/A')}, subset={adv.get('subset_size', 'N/A')}")
        
        except Exception as e:
            logger.error(f"  {name}: ERROR - {e}")
            import traceback
            traceback.print_exc()
            all_results[name] = {'name': name, 'error': str(e), 'verdict': 'ERROR'}
    
    # Run citation heritage on each
    logger.info("\n6. Running citation heritage benchmarks...")
    for name, embeddings in representations.items():
        if name in all_results and 'error' not in all_results[name]:
            try:
                ch_result = run_citation_heritage_on_subset(embeddings, subset_metadata, name)
                all_results[name]['citation_heritage'] = ch_result
                logger.info(f"  {name}: AUC-ROC={ch_result['auc_roc']:.4f} ({ch_result['auc_roc_status']}), "
                           f"Recall@10={ch_result['recall_at_10']:.4f} ({ch_result['recall_at_10_status']}), "
                           f"pos_pairs={ch_result['num_positive_pairs']}")
            except Exception as e:
                logger.error(f"  {name} citation heritage error: {e}")
                all_results[name]['citation_heritage'] = {'error': str(e)}
    
    # Run v17b label normalization on each
    logger.info("\n7. Running v17b label normalization benchmarks...")
    for name, embeddings in representations.items():
        if name in all_results and 'error' not in all_results[name]:
            try:
                v17b_result = run_v17b_label_normalization_on_subset(embeddings, subset_metadata, name)
                all_results[name]['v17b_label_normalization'] = v17b_result
                ratios = v17b_result['purity_ratios_norm_over_raw']
                logger.info(f"  {name}: ratios hierarchy={ratios['hierarchy']:.4f}, "
                           f"zoom_fine={ratios['zoom_fine']:.4f}, legal_area={ratios['legal_area']:.4f}")
            except Exception as e:
                logger.error(f"  {name} v17b error: {e}")
                all_results[name]['v17b_label_normalization'] = {'error': str(e)}
    
    # Save all results
    output_file = OUTPUT_DIR / f"evaluation_22year_dense_linear_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    latest_file = OUTPUT_DIR / "evaluation_22year_dense_linear_latest.json"
    with open(latest_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Generate summary report
    logger.info("\n" + "=" * 100)
    logger.info("EVALUATION 22-YEAR DENSE LINEAR COMBINATIONS - SUMMARY")
    logger.info("=" * 100)
    
    logger.info(f"\n{'Representation':<45} {'Verdict':<7} {'LangDom':>7} {'LD-P':>4} {'Jurist':>7} {'JP-P':>4} {'Both':>4} {'Dim':>5}")
    logger.info("-" * 95)
    
    def sort_key(item):
        name, res = item
        if 'error' in res:
            return (0, 0, 1.0)
        both = res['adversarial']['both_pass']
        jurist = res['adversarial']['jurist_preference_rate']
        lang_dom = res['adversarial']['language_dominance_score']
        return (both, jurist, -lang_dom)
    
    sorted_results = sorted(all_results.items(), key=sort_key, reverse=True)
    
    for name, res in sorted_results:
        if 'error' in res:
            logger.info(f"{name:<45} {'ERROR':<7} {'N/A':>7} {'N/A':>4} {'N/A':>7} {'N/A':>4} {'N/A':>4} {'N/A':>5}")
            continue
        
        adv = res['adversarial']
        ld = adv['language_dominance_score']
        jp = adv['jurist_preference_rate']
        ld_pass = "✓" if adv['adversarial_language_dominance']['status'] == 'PASS' else "✗"
        jp_pass = "✓" if adv['jurist_pairwise_preference']['status'] == 'PASS' else "✗"
        both = "✓" if adv['both_pass'] else "✗"
        dim = res['embedding_shape'][1]
        
        logger.info(f"{name:<45} {res['verdict']:<7} {ld:>7.4f} {ld_pass:>4} {jp:>7.4f} {jp_pass:>4} {both:>4} {dim:>5}")
    
    # Citation heritage summary
    logger.info("\n\nCITATION HERITAGE SUMMARY:")
    logger.info(f"{'Representation':<45} {'AUC-ROC':>8} {'Status':>6} {'Recall@10':>10} {'Status':>6} {'Pos Pairs':>10}")
    logger.info("-" * 90)
    for name, res in sorted_results:
        if 'error' in res or 'citation_heritage' not in res:
            continue
        ch = res['citation_heritage']
        if 'error' in ch:
            logger.info(f"{name:<45} {'ERROR':>8} {'N/A':>6} {'N/A':>10} {'N/A':>6} {'N/A':>10}")
        else:
            logger.info(f"{name:<45} {ch['auc_roc']:>8.4f} {ch['auc_roc_status']:>6} {ch['recall_at_10']:>10.4f} {ch['recall_at_10_status']:>6} {ch['num_positive_pairs']:>10}")
    
    # v17b summary
    logger.info("\n\nV17B LABEL NORMALIZATION SUMMARY:")
    logger.info(f"{'Representation':<45} {'Hierarchy':>10} {'Zoom Fine':>10} {'Legal Area':>10} {'Norm Areas':>10}")
    logger.info("-" * 85)
    for name, res in sorted_results:
        if 'error' in res or 'v17b_label_normalization' not in res:
            continue
        v17b = res['v17b_label_normalization']
        if 'error' in v17b:
            logger.info(f"{name:<45} {'ERROR':>10} {'ERROR':>10} {'ERROR':>10} {'N/A':>10}")
        else:
            ratios = v17b['purity_ratios_norm_over_raw']
            logger.info(f"{name:<45} {ratios['hierarchy']:>10.4f} {ratios['zoom_fine']:>10.4f} {ratios['legal_area']:>10.4f} {v17b['norm_num_areas']:>10}")
    
    # Best representation
    valid_results = {k: v for k, v in all_results.items() if 'error' not in v and v['adversarial']['both_pass']}
    if valid_results:
        best = max(valid_results.items(), key=lambda x: (x[1]['adversarial']['jurist_preference_rate'],
                                                          -x[1]['adversarial']['language_dominance_score']))
        logger.info(f"\n🏆 BEST REPRESENTATION (passing both adversarial gates): {best[0]}")
        logger.info(f"   Language dominance: {best[1]['adversarial']['language_dominance_score']:.4f}")
        logger.info(f"   Jurist preference: {best[1]['adversarial']['jurist_preference_rate']:.4f}")
        logger.info(f"   Dim: {best[1]['embedding_shape'][1]}")
    
    logger.info(f"\nResults saved to: {output_file}")
    logger.info("=" * 100)
    
    return all_results


if __name__ == "__main__":
    main()