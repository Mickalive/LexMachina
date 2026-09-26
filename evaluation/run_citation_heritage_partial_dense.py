#!/usr/bin/env python3
"""
Run citation_heritage benchmark on partial dense embeddings (2000-2015).
"""

import json
import numpy as np
import logging
from pathlib import Path
from typing import List, Dict
from sklearn.metrics import roc_auc_score

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
PAIRS_PATH = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k_citation_heritage/citation_pairs_174k.json")
EMBEDDING_PATH = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k/dense_partial_2000_2015/dense_partial_2000_2015_eval_latest.json")
METADATA_PATH = Path("/home/runner/work/LexMachina/LexMachina/evaluation/data/174k/metadata_174k.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k_citation_heritage")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def run_citation_heritage_on_subset(embeddings: np.ndarray, subset_metadata: List[Dict], pairs_data: Dict) -> Dict:
    """Run citation heritage on a subset of decisions that have embeddings."""
    
    # Build decision_id -> index in subset
    did_to_subset_idx = {m['decision_id']: i for i, m in enumerate(subset_metadata)}
    
    positive_pairs = pairs_data['positive_pairs']
    negative_pairs = pairs_data['negative_pairs']
    
    # Filter pairs to only include decisions in our subset
    pos_filtered = []
    for did1, did2 in positive_pairs:
        if did1 in did_to_subset_idx and did2 in did_to_subset_idx:
            pos_filtered.append((did_to_subset_idx[did1], did_to_subset_idx[did2]))
    
    neg_filtered = []
    for did1, did2 in negative_pairs:
        if did1 in did_to_subset_idx and did2 in did_to_subset_idx:
            neg_filtered.append((did_to_subset_idx[did1], did_to_subset_idx[did2]))
    
    logger.info(f"Positive pairs in subset: {len(pos_filtered)}/{len(positive_pairs)}")
    logger.info(f"Negative pairs in subset: {len(neg_filtered)}/{len(negative_pairs)}")
    
    if len(pos_filtered) < 10 or len(neg_filtered) < 10:
        logger.warning("Insufficient pairs in subset for meaningful evaluation")
        return {
            'status': 'INSUFFICIENT_PAIRS',
            'positive_pairs_in_subset': len(pos_filtered),
            'negative_pairs_in_subset': len(neg_filtered),
        }
    
    # Compute similarities for positive pairs
    pos_sims = []
    for i, j in pos_filtered:
        # Cosine similarity
        sim = np.dot(embeddings[i], embeddings[j]) / (np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[j]))
        pos_sims.append(sim)
    
    # Compute similarities for negative pairs
    neg_sims = []
    for i, j in neg_filtered:
        sim = np.dot(embeddings[i], embeddings[j]) / (np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[j]))
        neg_sims.append(sim)
    
    # AUC-ROC
    y_true = [1] * len(pos_sims) + [0] * len(neg_sims)
    y_score = pos_sims + neg_sims
    auc_roc = roc_auc_score(y_true, y_score)
    
    # Positive recall@10: for each positive pair, check if target is in top-10 of source
    # Build k-NN graph for subset
    from sklearn.neighbors import NearestNeighbors
    nn = NearestNeighbors(n_neighbors=min(11, len(embeddings)), metric='cosine', algorithm='brute', n_jobs=-1)
    nn.fit(embeddings)
    distances, indices = nn.kneighbors(embeddings)
    
    # Exclude self
    indices = indices[:, 1:]
    
    pos_recall = 0
    for i, j in pos_filtered:
        if j in indices[i][:10]:
            pos_recall += 1
    pos_recall_at_10 = pos_recall / len(pos_filtered)
    
    # Also compute nn_citation_rate: fraction of top-10 neighbors that are cited decisions
    # For each decision, count how many of its top-10 are in its citation set
    total_cited_in_top10 = 0
    total_top10 = 0
    
    # Build citation set for each decision in subset
    citation_sets = {}
    for i, j in pos_filtered:
        if i not in citation_sets:
            citation_sets[i] = set()
        citation_sets[i].add(j)
    
    for i in range(len(embeddings)):
        if i in citation_sets:
            cited_in_top10 = sum(1 for n in indices[i][:10] if n in citation_sets[i])
            total_cited_in_top10 += cited_in_top10
            total_top10 += min(10, len(indices[i]))
    
    nn_citation_rate = total_cited_in_top10 / total_top10 if total_top10 > 0 else 0
    
    return {
        'status': 'PASS' if auc_roc >= 0.65 else 'FAIL',
        'auc_roc': float(auc_roc),
        'positive_recall_at_10': float(pos_recall_at_10),
        'nn_citation_rate_at_10': float(nn_citation_rate),
        'positive_pairs': len(pos_filtered),
        'negative_pairs': len(neg_filtered),
        'pos_mean_sim': float(np.mean(pos_sims)),
        'neg_mean_sim': float(np.mean(neg_sims)),
        'similarity_gap': float(np.mean(pos_sims) - np.mean(neg_sims)),
        'threshold_auc': 0.65,
    }


def main():
    logger.info("=" * 70)
    logger.info("RUN CITATION_HERITAGE ON PARTIAL DENSE EMBEDDINGS (2000-2015)")
    logger.info("=" * 70)
    
    # Load citation pairs
    with open(PAIRS_PATH) as f:
        pairs_data = json.load(f)
    
    # Load metadata and filter for 2000-2015
    with open(METADATA_PATH) as f:
        full_metadata = json.load(f)
    
    subset_metadata = [m for m in full_metadata if 2000 <= int(m.get('year', 0)) <= 2015]
    logger.info(f"Subset metadata: {len(subset_metadata)} decisions (years 2000-2015)")
    
    # Load embeddings from the evaluation result
    with open(EMBEDDING_PATH) as f:
        eval_result = json.load(f)
    
    # The evaluation result doesn't save embeddings, need to reload them
    # Re-assemble embeddings
    import sys
    sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina')
    from evaluation.evaluate_174k_dense_partial import load_dense_embeddings_subset, COMPLETED_YEARS
    
    embeddings, assembled_metadata = load_dense_embeddings_subset(full_metadata, COMPLETED_YEARS)
    logger.info(f"Embeddings shape: {embeddings.shape}")
    
    # Run citation heritage
    result = run_citation_heritage_on_subset(embeddings, assembled_metadata, pairs_data)
    
    # Save result
    output_file = OUTPUT_DIR / "citation_heritage_multilingual_e5_768dim_partial_2000_2015.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    logger.info(f"\nResult saved to: {output_file}")
    logger.info(f"Result: {json.dumps(result, indent=2)}")


if __name__ == "__main__":
    main()