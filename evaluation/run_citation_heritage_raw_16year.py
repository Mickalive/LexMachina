#!/usr/bin/env python3
"""
Run citation_heritage benchmark on RAW 16-year partial dense embeddings (2000-2015).
Uses the frozen 137k pair pool to evaluate citation proximity preservation.
"""

import json
import numpy as np
import logging
import sys
from pathlib import Path
from sklearn.metrics import roc_auc_score
from typing import List, Tuple, Dict, Set

sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina')
from evaluation.run_174k_formal_suite import load_evaluation_metadata
from evaluation.scalable_nn import build_scalable_nn

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
DENSE_CHECKPOINTS_DIR = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints")
CITATION_PAIRS_PATH = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k_citation_heritage")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

COMPLETED_YEARS = list(range(2000, 2016))  # 2000-2015 inclusive
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
    if not chamber:
        return "unknown"
    if chamber in CHAMBER_TO_BRANCH:
        return CHAMBER_TO_BRANCH[chamber]
    chamber_lower = chamber.lower()
    if "öffentlich" in chamber_lower or "public" in chamber_lower:
        return "oeffentliches_recht"
    if "zivil" in chamber_lower or "civil" in chamber_lower:
        return "zivilrecht"
    if "straf" in chamber_lower or "pénal" in chamber_lower or "penal" in chamber_lower:
        return "strafrecht"
    if "sozial" in chamber_lower or "social" in chamber_lower:
        return "sozialversicherungsrecht"
    return "unknown"


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
    
    logger.info(f"Total target decisions: {len(target_ids)}")
    
    subset_metadata = []
    for i, m in enumerate(full_metadata):
        if m['decision_id'] in target_ids:
            subset_metadata.append(m)
    
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


def load_frozen_pairs() -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    """Load the frozen positive and negative citation pairs."""
    logger.info(f"Loading frozen pairs from {CITATION_PAIRS_PATH}")
    with open(CITATION_PAIRS_PATH) as f:
        data = json.load(f)
    
    positive_pairs = [tuple(p) for p in data['positive_pairs']]
    negative_pairs = [tuple(p) for p in data['negative_pairs']]
    
    logger.info(f"Frozen pairs: {len(positive_pairs)} positive, {len(negative_pairs)} negative")
    return positive_pairs, negative_pairs


def filter_pairs_to_subset(
    positive_pairs: List[Tuple[str, str]], 
    negative_pairs: List[Tuple[str, str]],
    subset_dids: Set[str]
) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    """Filter pairs to only include decisions in the subset."""
    pos_filtered = [(a, b) for a, b in positive_pairs if a in subset_dids and b in subset_dids]
    neg_filtered = [(a, b) for a, b in negative_pairs if a in subset_dids and b in subset_dids]
    
    logger.info(f"Filtered pairs: {len(pos_filtered)} positive, {len(neg_filtered)} negative")
    return pos_filtered, neg_filtered


def compute_similarities_batch(
    embeddings: np.ndarray,
    did_to_idx: Dict[str, int],
    pairs: List[Tuple[str, str]]
) -> np.ndarray:
    """Compute cosine similarities for pairs using vectorized operations."""
    idx_a = np.array([did_to_idx[a] for a, b in pairs if a in did_to_idx and b in did_to_idx])
    idx_b = np.array([did_to_idx[b] for a, b in pairs if a in did_to_idx and b in did_to_idx])
    
    if len(idx_a) == 0:
        return np.array([])
    
    emb_a = embeddings[idx_a]
    emb_b = embeddings[idx_b]
    
    norms_a = np.linalg.norm(emb_a, axis=1, keepdims=True)
    norms_b = np.linalg.norm(emb_b, axis=1, keepdims=True)
    emb_a_norm = emb_a / np.maximum(norms_a, 1e-10)
    emb_b_norm = emb_b / np.maximum(norms_b, 1e-10)
    
    sims = np.sum(emb_a_norm * emb_b_norm, axis=1)
    return sims


def evaluate_citation_heritage_fast(
    name: str,
    embeddings: np.ndarray,
    subset_metadata: List[Dict],
    positive_pairs: List[Tuple[str, str]],
    negative_pairs: List[Tuple[str, str]]
) -> Dict:
    """Run citation_heritage evaluation on a representation using HNSW for recall."""
    logger.info(f"\nEvaluating citation_heritage for {name}...")
    logger.info(f"Embeddings shape: {embeddings.shape}")
    
    # Build decision_id -> index mapping for the subset
    did_to_idx = {m['decision_id']: i for i, m in enumerate(subset_metadata)}
    subset_dids = set(did_to_idx.keys())
    
    # Filter pairs to subset
    pos_filtered, neg_filtered = filter_pairs_to_subset(positive_pairs, negative_pairs, subset_dids)
    
    if len(pos_filtered) == 0:
        logger.warning(f"No positive pairs in subset for {name}")
        return {
            'name': name,
            'status': 'INSUFFICIENT_PAIRS',
            'positive_pairs_in_subset': 0,
            'negative_pairs_in_subset': len(neg_filtered)
        }
    
    # Compute similarities for AUC (vectorized)
    logger.info(f"Computing similarities for AUC ({len(pos_filtered)} pos, {len(neg_filtered)} neg)...")
    pos_sims = compute_similarities_batch(embeddings, did_to_idx, pos_filtered)
    neg_sims = compute_similarities_batch(embeddings, did_to_idx, neg_filtered)
    
    # Compute AUC-ROC
    y_true = np.concatenate([np.ones(len(pos_sims)), np.zeros(len(neg_sims))])
    y_scores = np.concatenate([pos_sims, neg_sims])
    auc = roc_auc_score(y_true, y_scores)
    
    # Compute recall@10 using HNSW (efficient k-NN)
    logger.info("Building HNSW index for recall@10...")
    nn = build_scalable_nn(embeddings, n_neighbors=10, force_exact=False)
    logger.info(f"Built {nn.backend} index")
    
    # Sample queries for recall
    n_queries = min(1000, len(pos_filtered))
    query_indices = np.random.choice(len(pos_filtered), n_queries, replace=False)
    
    recall_at_10 = 0
    for idx in query_indices:
        source, target = pos_filtered[idx]
        source_idx = did_to_idx[source]
        target_idx = did_to_idx[target]
        
        # Query HNSW
        neighbors, _ = nn.kneighbors(embeddings[source_idx:source_idx+1], n_neighbors=11)  # +1 for self
        neighbor_indices = neighbors[0][1:]  # Exclude self
        
        if target_idx in neighbor_indices:
            recall_at_10 += 1
    
    recall_at_10 /= n_queries
    
    logger.info(f"  AUC-ROC: {auc:.4f}")
    logger.info(f"  Recall@10: {recall_at_10:.4f} (using {nn.backend})")
    
    return {
        'name': name,
        'status': 'COMPLETE',
        'auc_roc': float(auc),
        'recall_at_10': float(recall_at_10),
        'positive_pairs_evaluated': len(pos_filtered),
        'negative_pairs_evaluated': len(neg_filtered),
        'n_queries_recall': n_queries,
        'recall_backend': nn.backend,
        'thresholds': {'auc_min': 0.65, 'recall_at_10_min': 0.2},
        'pass_auc': auc >= 0.65,
        'pass_recall': recall_at_10 >= 0.2
    }


def center_project(emb: np.ndarray, dim: int) -> np.ndarray:
    """Center embeddings and project to target dimension via PCA."""
    centered = emb - emb.mean(axis=0, keepdims=True)
    from sklearn.decomposition import PCA
    pca = PCA(n_components=dim, random_state=42)
    projected = pca.fit_transform(centered)
    norms = np.linalg.norm(projected, axis=1, keepdims=True)
    projected = projected / np.maximum(norms, 1e-10)
    return projected.astype(np.float32)


def main():
    logger.info("=" * 70)
    logger.info("CITATION_HERITAGE ON RAW 16-YEAR PARTIAL DENSE EMBEDDINGS (2000-2015)")
    logger.info("=" * 70)
    
    # Load full metadata
    logger.info("Loading full 174k metadata...")
    full_metadata = load_evaluation_metadata()
    logger.info(f"Full metadata: {len(full_metadata)} decisions")
    
    # Load partial dense embeddings (2000-2015)
    logger.info("Loading partial dense embeddings (2000-2015)...")
    embeddings_raw, subset_metadata = load_dense_embeddings_subset(full_metadata, COMPLETED_YEARS)
    logger.info(f"Raw embeddings: {embeddings_raw.shape}")
    
    # Load frozen pairs
    positive_pairs, negative_pairs = load_frozen_pairs()
    
    # Evaluate RAW embeddings
    logger.info(f"\n{'='*50}")
    logger.info(f"Evaluating RAW 768dim...")
    result_raw = evaluate_citation_heritage_fast(
        f"raw_multilingual_e5_768dim_partial_2000_2015",
        embeddings_raw,
        subset_metadata,
        positive_pairs,
        negative_pairs
    )
    
    output_file = OUTPUT_DIR / f"citation_heritage_raw_multilingual_e5_768dim_partial_2000_2015.json"
    with open(output_file, "w") as f:
        json.dump(result_raw, f, indent=2)
    logger.info(f"Saved to {output_file}")
    
    # Evaluate center-projected versions
    for dim in [768, 128, 64]:
        logger.info(f"\n{'='*50}")
        logger.info(f"Computing center-projected {dim}dim...")
        emb_proj = center_project(embeddings_raw, dim)
        logger.info(f"Center-projected shape: {emb_proj.shape}")
        
        result_proj = evaluate_citation_heritage_fast(
            f"center_projected_{dim}dim_partial_2000_2015",
            emb_proj,
            subset_metadata,
            positive_pairs,
            negative_pairs
        )
        
        output_file = OUTPUT_DIR / f"citation_heritage_center_projected_{dim}dim_partial_2000_2015.json"
        with open(output_file, "w") as f:
            json.dump(result_proj, f, indent=2)
        logger.info(f"Saved to {output_file}")
    
    logger.info("\n" + "=" * 70)
    logger.info("CITATION_HERITAGE RAW 16-YEAR PARTIAL DENSE EVALUATION COMPLETE")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()