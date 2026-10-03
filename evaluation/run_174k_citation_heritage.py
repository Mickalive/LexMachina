#!/usr/bin/env python3
"""
Run Citation Heritage Benchmark at 174k scale for all TF-IDF embeddings.

Optimized version using vectorized operations.
"""

import json
import numpy as np
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple
from sklearn.metrics import roc_auc_score
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
EMBEDDINGS_DIR = Path("/tmp/lex_accepted/legal-distance/evaluation/results/174k/embeddings")
CITATION_PAIRS_FILE = Path("/tmp/lex_accepted/legal-distance/evaluation/results/174k_citation_heritage/citation_pairs_174k.json")
METADATA_FILE = EMBEDDINGS_DIR / "metadata.json"
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/evaluation")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# TF-IDF embedding files to test
TFIDF_EMBEDDINGS = [
    "cited_decisions_tfidf.npy",
    "cited_decisions_tfidf_outcome_hybrid_0.5.npy",
    "cited_decisions_tfidf_outcome_hybrid_0.7.npy",
    "full_text_tfidf_light.npy",
    "outcome_tfidf.npy",
    "regeste_tfidf.npy",
    "regeste_full_text_hybrid_0.5.npy",
    "regeste_full_text_hybrid_0.7.npy",
]

# Frozen parameters
GLOBAL_SEED = 42
AUC_THRESHOLD = 0.65
MAX_POSITIVE = 1000  # Limit for speed
MAX_NEGATIVE = 2000  # Limit for speed

def load_metadata() -> Tuple[List[str], Dict[str, int]]:
    """Load metadata and return decision_ids list and index mapping."""
    with open(METADATA_FILE) as f:
        metadata = json.load(f)
    
    decision_ids = [m["decision_id"] for m in metadata]
    id_to_idx = {did: i for i, did in enumerate(decision_ids)}
    logger.info(f"Loaded metadata for {len(decision_ids)} decisions")
    return decision_ids, id_to_idx

def load_citation_pairs() -> List[Tuple[str, str]]:
    """Load citation pairs from the frozen pair pool."""
    with open(CITATION_PAIRS_FILE) as f:
        data = json.load(f)
    
    positive_pairs = data["positive_pairs"]
    logger.info(f"Loaded {len(positive_pairs)} positive citation pairs")
    return positive_pairs

def load_embeddings(embedding_file: str) -> np.ndarray:
    """Load embeddings."""
    filepath = EMBEDDINGS_DIR / embedding_file
    logger.info(f"Loading embeddings from {filepath}")
    embeddings = np.load(filepath)
    logger.info(f"Embeddings shape: {embeddings.shape}")
    return embeddings

def compute_similarities_batch(embeddings: np.ndarray, pairs: List[Tuple[int, int]]) -> np.ndarray:
    """Compute cosine similarities for multiple pairs at once using vectorization."""
    idx1 = np.array([p[0] for p in pairs])
    idx2 = np.array([p[1] for p in pairs])
    
    emb1 = embeddings[idx1]
    emb2 = embeddings[idx2]
    
    # Normalize
    norm1 = np.linalg.norm(emb1, axis=1, keepdims=True)
    norm2 = np.linalg.norm(emb2, axis=1, keepdims=True)
    norm1[norm1 == 0] = 1.0
    norm2[norm2 == 0] = 1.0
    
    emb1_norm = emb1 / norm1
    emb2_norm = emb2 / norm2
    
    # Cosine similarity = dot product of normalized vectors
    similarities = np.sum(emb1_norm * emb2_norm, axis=1)
    return similarities

def run_citation_heritage(
    embedding_file: str,
    positive_pairs: List[Tuple[str, str]],
    id_to_idx: Dict[str, int],
    embeddings: np.ndarray,
) -> Dict[str, Any]:
    """Run citation heritage benchmark with vectorized operations."""
    np.random.seed(GLOBAL_SEED)
    
    # Filter pairs where both decisions have embeddings
    valid_pairs = []
    for d1, d2 in positive_pairs:
        if d1 in id_to_idx and d2 in id_to_idx:
            valid_pairs.append((id_to_idx[d1], id_to_idx[d2]))
    
    logger.info(f"Valid positive pairs: {len(valid_pairs)}")
    
    if len(valid_pairs) == 0:
        return {"error": "No valid positive pairs found", "status": "ERROR"}
    
    # Sample positive pairs
    if len(valid_pairs) > MAX_POSITIVE:
        np.random.shuffle(valid_pairs)
        valid_pairs = valid_pairs[:MAX_POSITIVE]
    
    # Generate negative pairs
    n_decisions = embeddings.shape[0]
    positive_set = set(tuple(sorted(p)) for p in valid_pairs)
    
    negative_pairs = []
    attempts = 0
    max_attempts = MAX_NEGATIVE * 20
    
    while len(negative_pairs) < MAX_NEGATIVE and attempts < max_attempts:
        idx1, idx2 = np.random.choice(n_decisions, 2, replace=False)
        pair_key = tuple(sorted([idx1, idx2]))
        if pair_key not in positive_set:
            negative_pairs.append((int(idx1), int(idx2)))
        attempts += 1
    
    logger.info(f"Generated {len(negative_pairs)} negative pairs (attempts: {attempts})")
    
    # Compute similarities using vectorized operations
    pos_sims = compute_similarities_batch(embeddings, valid_pairs)
    neg_sims = compute_similarities_batch(embeddings, negative_pairs)
    
    # Compute AUC-ROC
    y_true = np.concatenate([np.ones(len(pos_sims)), np.zeros(len(neg_sims))])
    y_scores = np.concatenate([pos_sims, neg_sims])
    
    auc_roc = float(roc_auc_score(y_true, y_scores))
    pos_mean = float(np.mean(pos_sims))
    neg_mean = float(np.mean(neg_sims))
    gap = pos_mean - neg_mean
    
    return {
        "auc_roc": auc_roc,
        "positive_mean_sim": pos_mean,
        "negative_mean_sim": neg_mean,
        "mean_similarity_gap": gap,
        "num_positive_pairs": len(pos_sims),
        "num_negative_pairs": len(neg_sims),
        "status": "PASSED" if auc_roc >= AUC_THRESHOLD else "FAILED",
        "threshold": AUC_THRESHOLD,
    }

def main():
    logger.info("Starting 174k Citation Heritage Benchmark (optimized)")
    start_time = time.time()
    
    # Load metadata and citation pairs
    decision_ids, id_to_idx = load_metadata()
    positive_pairs = load_citation_pairs()
    
    results = {}
    
    for emb_file in TFIDF_EMBEDDINGS:
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing: {emb_file}")
        logger.info(f"{'='*60}")
        
        try:
            embeddings = load_embeddings(emb_file)
            result = run_citation_heritage(emb_file, positive_pairs, id_to_idx, embeddings)
            results[emb_file.replace('.npy', '')] = result
            
            logger.info(f"  AUC-ROC: {result['auc_roc']:.4f} ({result['status']})")
            logger.info(f"  Pos mean sim: {result['positive_mean_sim']:.4f}")
            logger.info(f"  Neg mean sim: {result['negative_mean_sim']:.4f}")
            logger.info(f"  Gap: {result['mean_similarity_gap']:.4f}")
            
        except Exception as e:
            logger.error(f"Error processing {emb_file}: {e}")
            results[emb_file.replace('.npy', '')] = {"error": str(e), "status": "ERROR"}
    
    # Save results
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    output_file = OUTPUT_DIR / f"citation_heritage_174k_tfidf_{timestamp}.json"
    with open(output_file, 'w') as f:
        json.dump({
            "run_info": {
                "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                "direction_version": 29,
                "total_decisions": len(decision_ids),
                "total_positive_pairs": len(positive_pairs),
                "auc_threshold": AUC_THRESHOLD,
                "global_seed": GLOBAL_SEED,
                "max_positive_sampled": MAX_POSITIVE,
                "max_negative_sampled": MAX_NEGATIVE,
            },
            "results": results
        }, f, indent=2)
    
    # Also save as latest
    latest_file = OUTPUT_DIR / "citation_heritage_174k_tfidf_latest.json"
    with open(latest_file, 'w') as f:
        json.dump({
            "run_info": {
                "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                "direction_version": 29,
                "total_decisions": len(decision_ids),
                "total_positive_pairs": len(positive_pairs),
                "auc_threshold": AUC_THRESHOLD,
                "global_seed": GLOBAL_SEED,
                "max_positive_sampled": MAX_POSITIVE,
                "max_negative_sampled": MAX_NEGATIVE,
            },
            "results": results
        }, f, indent=2)
    
    logger.info(f"\nResults saved to {output_file}")
    logger.info(f"Total duration: {time.time() - start_time:.2f}s")
    
    # Print summary
    print("\n" + "="*80)
    print("CITATION HERITAGE 174k TF-IDF SUMMARY")
    print("="*80)
    for name, result in results.items():
        if "error" in result:
            print(f"  {name}: ERROR - {result['error']}")
        else:
            status = "✓ PASS" if result["status"] == "PASSED" else "✗ FAIL"
            print(f"  {name}: AUC={result['auc_roc']:.4f} {status}")

if __name__ == "__main__":
    main()