#!/usr/bin/env python3
"""
Assemble and save linear_hybrid05_concat embeddings for 19-year subset (2000-2018).
Then run citation_heritage evaluation on this subset.
"""

import json
import numpy as np
import logging
import time
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple

sys.path.insert(0, '/tmp/lex_accepted/evaluation/evaluation')
sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina')

from run_174k_formal_suite import (
    GLOBAL_SEED,
)

from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
DENSE_CHECKPOINTS_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/174k_dense_embeddings/checkpoints")
TFIDF_EMBEDDINGS_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k/embeddings")
FULL_METADATA_PATH = Path("/home/runner/work/LexMachina/LexMachina/evaluation/data/174k/metadata_174k.json")
CITATION_PAIRS_PATH = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k_citation_heritage/citation_pairs_174k.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/174k_dense_embeddings/linear_combinations_19year")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

COMPLETED_YEARS = list(range(2000, 2019))  # 2000-2018 inclusive (19 years)


def load_dense_embeddings_subset(full_metadata: List[Dict], years: List[int]) -> Tuple[np.ndarray, List[Dict]]:
    """Load dense embeddings for specified years and assemble in full metadata order."""
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
    
    logger.info(f"Total target decisions from checkpoints: {len(target_ids)}")
    
    subset_metadata = []
    for i, m in enumerate(full_metadata):
        if m['decision_id'] in target_ids:
            subset_metadata.append(m)
    
    logger.info(f"Subset metadata count (in full metadata order): {len(subset_metadata)} (expected {len(target_ids)})")
    
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
    
    logger.info(f"Assembled dense embeddings shape: {embeddings_subset.shape}")
    
    return embeddings_subset, subset_metadata


def load_tfidf_for_subset(tfidf_filename: str, subset_metadata: List[Dict], full_metadata: List[Dict]) -> np.ndarray:
    """Load TF-IDF embeddings for the subset decisions."""
    logger.info(f"Loading {tfidf_filename} for subset...")
    
    tfidf_path = TFIDF_EMBEDDINGS_DIR / tfidf_filename
    tfidf = np.load(tfidf_path, mmap_mode='r')
    logger.info(f"Full TF-IDF shape: {tfidf.shape}")
    
    full_id_to_idx = {m['decision_id']: i for i, m in enumerate(full_metadata)}
    
    n_subset = len(subset_metadata)
    tfidf_dim = tfidf.shape[1]
    subset_tfidf = np.zeros((n_subset, tfidf_dim), dtype=np.float32)
    
    for i, m in enumerate(subset_metadata):
        full_idx = full_id_to_idx[m['decision_id']]
        subset_tfidf[i] = tfidf[full_idx]
    
    logger.info(f"Extracted subset TF-IDF shape: {subset_tfidf.shape}")
    return subset_tfidf


def apply_language_center_projection(embeddings: np.ndarray, metadata: List[Dict]) -> np.ndarray:
    """Apply language center projection and L2 normalize."""
    languages = [m.get('language', 'de') for m in metadata]
    unique_langs = sorted(set(languages))
    centers = {}
    for lang in unique_langs:
        mask = np.array([l == lang for l in languages])
        if np.sum(mask) > 0:
            centers[lang] = embeddings[mask].mean(axis=0)
    
    debiased = np.copy(embeddings)
    for i, lang in enumerate(languages):
        if lang in centers:
            debiased[i] = embeddings[i] - centers[lang]
    
    norms = np.linalg.norm(debiased, axis=1, keepdims=True)
    norms[norms == 0] = 1
    debiased = debiased / norms
    
    return debiased


def apply_pca_64(embeddings: np.ndarray) -> Tuple[np.ndarray, float]:
    """Apply PCA to 64 dimensions and L2 normalize."""
    pca = PCA(n_components=64, random_state=GLOBAL_SEED)
    embeddings_64 = pca.fit_transform(embeddings)
    embeddings_64 = normalize(embeddings_64, norm='l2', axis=1)
    explained_var = pca.explained_variance_ratio_.sum()
    
    return embeddings_64, explained_var


def run_citation_heritage_on_subset(embeddings: np.ndarray, subset_metadata: List[Dict], 
                                    full_metadata: List[Dict], citation_pairs_path: Path) -> Dict[str, Any]:
    """
    Run citation heritage benchmark on a subset of decisions.
    Filters citation pairs to only include decisions in the subset.
    """
    logger.info("Running citation_heritage on subset...")
    
    # Load citation pairs
    with open(citation_pairs_path, 'r') as f:
        pairs_data = json.load(f)
    
    positive_pairs = [tuple(p) for p in pairs_data['positive_pairs']]
    negative_pairs = [tuple(p) for p in pairs_data['negative_pairs']]
    
    # Create subset decision_id -> index mapping
    subset_did_to_idx = {m['decision_id']: i for i, m in enumerate(subset_metadata)}
    subset_ids = set(subset_did_to_idx.keys())
    
    # Filter pairs: keep pairs where at least one decision is in subset
    # For positive pairs, we need both to compute similarity, but for recall we need the adjacency
    pos_pairs_subset = [(d1, d2) for d1, d2 in positive_pairs if d1 in subset_ids and d2 in subset_ids]
    # For negative pairs, we need both in subset for similarity computation
    neg_pairs_subset = [(d1, d2) for d1, d2 in negative_pairs if d1 in subset_ids and d2 in subset_ids]
    
    # Also build adjacency for recall computation (decisions in subset that cite or are cited by decisions in subset)
    cited_map = {}
    for did1, did2 in positive_pairs:
        if did1 in subset_ids and did2 in subset_ids:
            if did1 not in cited_map:
                cited_map[did1] = set()
            cited_map[did1].add(did2)
            if did2 not in cited_map:
                cited_map[did2] = set()
            cited_map[did2].add(did1)
    
    logger.info(f"Positive pairs in subset (both in subset): {len(pos_pairs_subset)} / {len(positive_pairs)}")
    logger.info(f"Negative pairs in subset (both in subset): {len(neg_pairs_subset)} / {len(negative_pairs)}")
    logger.info(f"Citation adjacency decisions in subset: {len(cited_map)}")
    
    if len(pos_pairs_subset) < 10 or len(neg_pairs_subset) < 10:
        logger.warning("Too few pairs in subset for meaningful evaluation")
        return {"error": "insufficient pairs in subset"}
    
    # Compute similarities for positive pairs (both in subset)
    logger.info("Computing similarities for positive pairs...")
    pos_sims = []
    for did1, did2 in pos_pairs_subset:
        idx1 = subset_did_to_idx[did1]
        idx2 = subset_did_to_idx[did2]
        v1 = embeddings[idx1]
        v2 = embeddings[idx2]
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 > 0 and norm2 > 0:
            sim = np.dot(v1, v2) / (norm1 * norm2)
            pos_sims.append(sim)
    
    # Compute similarities for negative pairs (both in subset)
    logger.info("Computing similarities for negative pairs...")
    neg_sims = []
    for did1, did2 in neg_pairs_subset:
        idx1 = subset_did_to_idx[did1]
        idx2 = subset_did_to_idx[did2]
        v1 = embeddings[idx1]
        v2 = embeddings[idx2]
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 > 0 and norm2 > 0:
            sim = np.dot(v1, v2) / (norm1 * norm2)
            neg_sims.append(sim)
    
    pos_sims = np.array(pos_sims)
    neg_sims = np.array(neg_sims)
    
    logger.info(f"Positive similarities: {len(pos_sims)}, mean={np.mean(pos_sims):.4f}")
    logger.info(f"Negative similarities: {len(neg_sims)}, mean={np.mean(neg_sims):.4f}")
    
    # Compute AUC-ROC
    from sklearn.metrics import roc_auc_score
    y_true = np.concatenate([np.ones(len(pos_sims)), np.zeros(len(neg_sims))])
    y_score = np.concatenate([pos_sims, neg_sims])
    auc_roc = roc_auc_score(y_true, y_score)
    
    # Compute recall@10 using exact k-NN
    from sklearn.neighbors import NearestNeighbors
    nn = NearestNeighbors(n_neighbors=10, metric='cosine', algorithm='brute')
    nn.fit(embeddings)
    all_neighbors = nn.kneighbors(n_neighbors=10, return_distance=False)
    
    recall_10_sum = 0
    recall_10_count = 0
    for did, cited_set in cited_map.items():
        idx = subset_did_to_idx[did]
        neighbors = all_neighbors[idx]
        found = sum(1 for c in cited_set if c in subset_did_to_idx and subset_did_to_idx[c] in neighbors)
        recall = found / min(len(cited_set), 10) if cited_set else 0
        recall_10_sum += recall
        recall_10_count += 1
    
    mean_recall_at_10 = recall_10_sum / recall_10_count if recall_10_count > 0 else 0
    
    return {
        'auc_roc': float(auc_roc),
        'positive_mean_similarity': float(np.mean(pos_sims)),
        'negative_mean_similarity': float(np.mean(neg_sims)),
        'similarity_gap': float(np.mean(pos_sims) - np.mean(neg_sims)),
        'num_positive_pairs': len(pos_sims),
        'num_negative_pairs': len(neg_sims),
        'recall_at_10': float(mean_recall_at_10),
        'recall_at_10_status': 'PASS' if mean_recall_at_10 >= 0.2 else 'FAIL',
        'auc_roc_status': 'PASS' if auc_roc >= 0.65 else 'FAIL',
        'threshold_auc': 0.65,
        'threshold_recall': 0.2,
        'backend': 'sklearn_exact',
    }


def main():
    logger.info("=" * 70)
    logger.info("ASSEMBLE 19-YEAR LINEAR_HYBRID05_CONCAT AND RUN CITATION_HERITAGE")
    logger.info("=" * 70)
    
    # Load full metadata
    logger.info("Loading full 174k metadata...")
    with open(FULL_METADATA_PATH) as f:
        full_metadata = json.load(f)
    logger.info(f"Full metadata: {len(full_metadata)} decisions")
    
    # Load 19-year dense embeddings
    logger.info("\n=== Loading 19-year dense embeddings ===")
    dense_emb, subset_metadata = load_dense_embeddings_subset(full_metadata, COMPLETED_YEARS)
    
    # Apply language center projection to dense embeddings
    logger.info("Applying language center projection to dense embeddings...")
    dense_cp = apply_language_center_projection(dense_emb, subset_metadata)
    logger.info(f"Center-projected dense shape: {dense_cp.shape}")
    
    # Apply PCA to 64 dim
    logger.info("Applying PCA to 64 dimensions...")
    dense_cp_64, explained_var = apply_pca_64(dense_cp)
    logger.info(f"Dense CP 64 shape: {dense_cp_64.shape}, explained var: {explained_var:.4f}")
    
    # Load citation TF-IDF for subset
    logger.info("\n=== Loading citation TF-IDF for 19-year subset ===")
    citation_tfidf_hybrid05 = load_tfidf_for_subset("cited_decisions_tfidf_outcome_hybrid_0.5.npy", subset_metadata, full_metadata)
    
    # Create linear_hybrid05_concat (64 + 128 = 192 dim)
    logger.info("\n=== Creating linear_hybrid05_concat ===")
    linear_hybrid05_concat = np.hstack([dense_cp_64, citation_tfidf_hybrid05])
    logger.info(f"Concatenated shape: {linear_hybrid05_concat.shape}")
    
    # Save the embeddings
    emb_path = OUTPUT_DIR / "linear_hybrid05_concat_19year.npy"
    np.save(emb_path, linear_hybrid05_concat.astype(np.float32))
    logger.info(f"Saved linear_hybrid05_concat_19year to {emb_path}")
    
    # Save subset metadata
    meta_path = OUTPUT_DIR / "metadata_19year.json"
    with open(meta_path, 'w') as f:
        json.dump(subset_metadata, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved 19-year subset metadata to {meta_path}")
    
    # Run citation heritage on this subset
    logger.info("\n=== Running citation_heritage on 19-year linear_hybrid05_concat ===")
    citation_result = run_citation_heritage_on_subset(
        linear_hybrid05_concat, subset_metadata, full_metadata, CITATION_PAIRS_PATH
    )
    
    # Save citation heritage result
    citation_out = {
        "representation": "linear_hybrid05_concat_19year",
        "embedding_shape": list(linear_hybrid05_concat.shape),
        "n_decisions": len(subset_metadata),
        "citation_heritage": citation_result,
        "timestamp": time.time(),
    }
    
    citation_output = OUTPUT_DIR / "linear_hybrid05_concat_19year_citation_heritage.json"
    with open(citation_output, 'w') as f:
        json.dump(citation_out, f, indent=2, default=str)
    
    logger.info(f"\nCitation heritage result: {citation_result}")
    logger.info(f"Saved to {citation_output}")
    
    logger.info("=" * 70)
    logger.info("COMPLETE")
    logger.info("=" * 70)
    
    return citation_out


if __name__ == "__main__":
    main()