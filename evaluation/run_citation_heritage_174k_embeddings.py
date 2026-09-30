#!/usr/bin/env python3
"""
Run citation_heritage benchmark on 174k TF-IDF embeddings using the frozen citation pairs.
This validates the citation_heritage benchmark at full 174k scale.
"""
import json
import sys
import time
import numpy as np
import logging
from pathlib import Path
from collections import Counter

sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina')
from evaluation.scalable_nn import build_scalable_nn, batched_adversarial_language_dominance, batched_jurist_pairwise_preference

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
EMBEDDINGS_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k/embeddings")
METADATA_PATH = Path("/home/runner/work/LexMachina/LexMachina/evaluation/data/174k/metadata_174k.json")
CITATION_PAIRS_PATH = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k_citation_heritage/citation_pairs_174k.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k_citation_heritage")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Representations to evaluate (TF-IDF family at 174k)
REPRESENTATIONS = {
    'cited_decisions_tfidf': 'cited_decisions_tfidf.npy',
    'outcome_tfidf': 'outcome_tfidf.npy',
    'regeste_tfidf': 'regeste_tfidf.npy',
    'full_text_tfidf_light': 'full_text_tfidf_light.npy',
    'cited_decisions_tfidf_outcome_hybrid_0.5': 'cited_decisions_tfidf_outcome_hybrid_0.5.npy',
    'cited_decisions_tfidf_outcome_hybrid_0.7': 'cited_decisions_tfidf_outcome_hybrid_0.7.npy',
    'regeste_full_text_hybrid_0.5': 'regeste_full_text_hybrid_0.5.npy',
    'regeste_full_text_hybrid_0.7': 'regeste_full_text_hybrid_0.7.npy',
}

FROZEN_SEED = 42
K_NEIGHBORS = 10  # For citation heritage we use k=10 for recall@10
RECALL_THRESHOLD = 0.2  # Frozen threshold from evaluation_v3_config.json

def load_metadata():
    """Load 174k metadata and create decision_id -> index mapping."""
    logger.info(f"Loading metadata from {METADATA_PATH}")
    with open(METADATA_PATH, 'r') as f:
        metadata = json.load(f)
    did_to_idx = {m['decision_id']: i for i, m in enumerate(metadata)}
    logger.info(f"Loaded {len(metadata)} decisions")
    return metadata, did_to_idx

def load_citation_pairs():
    """Load frozen citation pairs."""
    logger.info(f"Loading citation pairs from {CITATION_PAIRS_PATH}")
    with open(CITATION_PAIRS_PATH, 'r') as f:
        pairs_data = json.load(f)
    
    positive_pairs = [tuple(p) for p in pairs_data['positive_pairs']]
    negative_pairs = [tuple(p) for p in pairs_data['negative_pairs']]
    
    logger.info(f"Loaded {len(positive_pairs)} positive pairs, {len(negative_pairs)} negative pairs")
    return positive_pairs, negative_pairs

def run_citation_heritage_on_embeddings(embeddings, metadata, did_to_idx, positive_pairs, negative_pairs):
    """
    Run citation heritage benchmark: AUC-ROC on citation pairs vs random pairs.
    
    This tests whether decisions sharing citations are closer in embedding space.
    """
    # Build HNSW index for full corpus
    logger.info("Building HNSW index for citation heritage...")
    nn = build_scalable_nn(embeddings, n_neighbors=K_NEIGHBORS, force_exact=False)
    
    # Compute similarities for positive pairs
    logger.info("Computing similarities for positive pairs...")
    pos_sims = []
    for did1, did2 in positive_pairs:
        if did1 in did_to_idx and did2 in did_to_idx:
            idx1 = did_to_idx[did1]
            idx2 = did_to_idx[did2]
            # Cosine similarity
            v1 = embeddings[idx1]
            v2 = embeddings[idx2]
            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)
            if norm1 > 0 and norm2 > 0:
                sim = np.dot(v1, v2) / (norm1 * norm2)
                pos_sims.append(sim)
    
    # Compute similarities for negative pairs
    logger.info("Computing similarities for negative pairs...")
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
    
    logger.info(f"Positive similarities: {len(pos_sims)}, mean={np.mean(pos_sims):.4f}")
    logger.info(f"Negative similarities: {len(neg_sims)}, mean={np.mean(neg_sims):.4f}")
    
    # Compute AUC-ROC
    from sklearn.metrics import roc_auc_score
    y_true = np.concatenate([np.ones(len(pos_sims)), np.zeros(len(neg_sims))])
    y_score = np.concatenate([pos_sims, neg_sims])
    auc_roc = roc_auc_score(y_true, y_score)
    
    # Also compute recall@10 using nearest neighbors
    logger.info("Computing recall@10...")
    # For each decision in positive pairs, check if its cited partner is in top-10
    all_neighbors = nn.kneighbors(n_neighbors=K_NEIGHBORS)[1]
    
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
        recall = found / min(len(cited_set), K_NEIGHBORS) if cited_set else 0
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
        'recall_at_10_status': 'PASS' if mean_recall_at_10 >= RECALL_THRESHOLD else 'FAIL',
        'auc_roc_status': 'PASS' if auc_roc >= 0.65 else 'FAIL',
        'threshold_auc': 0.65,
        'threshold_recall': RECALL_THRESHOLD,
        'backend': nn.backend
    }

def main():
    t0 = time.time()
    logger.info("=" * 70)
    logger.info("CITATION_HERITAGE BENCHMARK AT 174K SCALE (TF-IDF FAMILY)")
    logger.info("=" * 70)
    
    # Load data
    metadata, did_to_idx = load_metadata()
    positive_pairs, negative_pairs = load_citation_pairs()
    
    out = {
        "run_id": f"citation_heritage_174k_tfidf_{int(time.time())}",
        "direction_version": 29,
        "seed": FROZEN_SEED,
        "k_neighbors": K_NEIGHBORS,
        "recall_threshold": RECALL_THRESHOLD,
        "per_representation": {},
    }
    
    for name, fname in REPRESENTATIONS.items():
        logger.info(f"\nProcessing {name}...")
        try:
            emb_path = EMBEDDINGS_DIR / fname
            embeddings = np.load(emb_path, mmap_mode='r')
            logger.info(f"  Loaded {embeddings.shape}")
            
            # Align embeddings with metadata
            if embeddings.shape[0] > len(metadata):
                logger.info(f"  Trimming embeddings from {embeddings.shape[0]} to {len(metadata)}")
                embeddings = embeddings[:len(metadata)]
            elif embeddings.shape[0] < len(metadata):
                logger.error(f"  Embedding/metadata length mismatch: {embeddings.shape[0]} < {len(metadata)}")
                out["per_representation"][name] = {"error": f"embedding/metadata length mismatch"}
                continue
            
            result = run_citation_heritage_on_embeddings(
                embeddings, metadata, did_to_idx, positive_pairs, negative_pairs
            )
            out["per_representation"][name] = result
            
            logger.info(f"  {name}: AUC-ROC={result['auc_roc']:.4f} ({result['auc_roc_status']}), "
                       f"Recall@10={result['recall_at_10']:.4f} ({result['recall_at_10_status']})")
            
        except Exception as e:
            logger.error(f"  Error on {name}: {e}")
            import traceback
            traceback.print_exc()
            out["per_representation"][name] = {"error": str(e)}
    
    out["total_duration_seconds"] = round(time.time() - t0, 2)
    
    # Save
    output_file = OUTPUT_DIR / f"citation_heritage_174k_tfidf_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(out, f, indent=2, default=str)
    
    latest_file = OUTPUT_DIR / "citation_heritage_174k_tfidf_latest.json"
    with open(latest_file, 'w') as f:
        json.dump(out, f, indent=2, default=str)
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("CITATION_HERITAGE 174K TF-IDF - SUMMARY")
    logger.info("=" * 70)
    for name, d in out["per_representation"].items():
        if "error" in d:
            logger.info(f"  {name}: ERROR - {d['error']}")
        else:
            logger.info(f"  {name}: AUC-ROC={d['auc_roc']:.4f} ({d['auc_roc_status']}), "
                       f"Recall@10={d['recall_at_10']:.4f} ({d['recall_at_10_status']})")
    
    logger.info(f"Total duration: {out['total_duration_seconds']}s")
    logger.info(f"Results saved to: {output_file}")
    logger.info("=" * 70)
    
    return out

if __name__ == "__main__":
    main()
