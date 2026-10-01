#!/usr/bin/env python3
"""
Run citation_heritage benchmark on 174k TF-IDF representations using frozen citation pairs.
Uses the 2,019/2,105 resolved citation IDs from corpus lane.
"""
import json
import numpy as np
import logging
import sys
from pathlib import Path
from sklearn.metrics import roc_auc_score

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
EMBEDDINGS_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k/embeddings")
CITATION_PAIRS = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k_citation_heritage/citation_pairs_174k.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k_citation_heritage")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# TF-IDF representations to evaluate
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

METADATA_PATH = EMBEDDINGS_DIR / "metadata.json"

def load_metadata():
    logger.info(f"Loading metadata from {METADATA_PATH}")
    with open(METADATA_PATH, 'r') as f:
        metadata = json.load(f)
    did_to_idx = {m['decision_id']: i for i, m in enumerate(metadata)}
    logger.info(f"Loaded {len(metadata)} decisions")
    return metadata, did_to_idx

def load_citation_pairs():
    logger.info(f"Loading citation pairs from {CITATION_PAIRS}")
    with open(CITATION_PAIRS, 'r') as f:
        data = json.load(f)
    positive_pairs = [tuple(p) for p in data['positive_pairs']]
    negative_pairs = [tuple(p) for p in data['negative_pairs']]
    logger.info(f"Positive pairs: {len(positive_pairs)}, Negative pairs: {len(negative_pairs)}")
    return positive_pairs, negative_pairs

def load_embedding(name):
    path = EMBEDDINGS_DIR / REPRESENTATIONS[name]
    if not path.exists():
        raise FileNotFoundError(f"Embedding not found: {path}")
    emb = np.load(path, mmap_mode='r')
    logger.info(f"Loaded {name}: {emb.shape}")
    return emb

def cosine_similarity(a, b):
    """Compute cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))

def run_citation_heritage(embeddings, did_to_idx, positive_pairs, negative_pairs):
    """Run citation heritage benchmark - AUC-ROC on citation pairs vs random pairs."""
    # Filter pairs where both decisions have embeddings
    valid_positive = [(d1, d2) for d1, d2 in positive_pairs if d1 in did_to_idx and d2 in did_to_idx]
    valid_negative = [(d1, d2) for d1, d2 in negative_pairs if d1 in did_to_idx and d2 in did_to_idx]
    
    logger.info(f"  Valid positive pairs: {len(valid_positive)}")
    logger.info(f"  Valid negative pairs: {len(valid_negative)}")
    
    if len(valid_positive) < 10 or len(valid_negative) < 10:
        return {'status': 'FAILED', 'error': 'Insufficient valid pairs'}
    
    # Compute similarities
    positive_scores = []
    for d1, d2 in valid_positive:
        sim = cosine_similarity(embeddings[did_to_idx[d1]], embeddings[did_to_idx[d2]])
        positive_scores.append(sim)
    
    negative_scores = []
    for d1, d2 in valid_negative:
        sim = cosine_similarity(embeddings[did_to_idx[d1]], embeddings[did_to_idx[d2]])
        negative_scores.append(sim)
    
    # Compute AUC-ROC
    y_true = [1] * len(positive_scores) + [0] * len(negative_scores)
    y_scores = positive_scores + negative_scores
    auc_roc = roc_auc_score(y_true, y_scores)
    
    metrics = {
        'auc_roc': float(auc_roc),
        'positive_mean_sim': float(np.mean(positive_scores)),
        'negative_mean_sim': float(np.mean(negative_scores)),
        'similarity_gap': float(np.mean(positive_scores) - np.mean(negative_scores)),
        'num_positive_pairs': len(valid_positive),
        'num_negative_pairs': len(valid_negative),
        'status': 'PASS' if auc_roc > 0.65 else 'FAIL'
    }
    
    return metrics

def main():
    logger.info("=" * 70)
    logger.info("CITATION_HERITAGE BENCHMARK AT 174K SCALE - TF-IDF REPRESENTATIONS")
    logger.info("=" * 70)
    
    # Load data
    metadata, did_to_idx = load_metadata()
    positive_pairs, negative_pairs = load_citation_pairs()
    
    all_results = {}
    
    for name in REPRESENTATIONS.keys():
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"Evaluating: {name}")
            logger.info(f"{'='*60}")
            
            embeddings = load_embedding(name)
            
            # Verify metadata alignment
            n_meta = len(metadata)
            if embeddings.shape[0] != n_meta:
                logger.warning(f"Shape mismatch: embeddings {embeddings.shape[0]} vs metadata {n_meta}")
                if embeddings.shape[0] > n_meta:
                    embeddings = embeddings[:n_meta]
                else:
                    all_results[name] = {'error': 'embedding/metadata length mismatch', 'status': 'ERROR'}
                    continue
            
            result = run_citation_heritage(embeddings, did_to_idx, positive_pairs, negative_pairs)
            all_results[name] = result
            
            if 'error' in result:
                logger.error(f"  {name}: ERROR - {result['error']}")
            else:
                logger.info(f"  {name}: AUC={result['auc_roc']:.4f} "
                           f"(pos_mean={result['positive_mean_sim']:.4f}, "
                           f"neg_mean={result['negative_mean_sim']:.4f}, "
                           f"gap={result['similarity_gap']:.4f}) "
                           f"[{result['status']}]")
            
        except Exception as e:
            logger.error(f"  {name}: ERROR - {e}")
            import traceback
            traceback.print_exc()
            all_results[name] = {'error': str(e), 'status': 'ERROR'}
    
    # Save results
    from datetime import datetime
    output_file = OUTPUT_DIR / f"citation_heritage_174k_tfidf_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    latest_file = OUTPUT_DIR / "citation_heritage_174k_tfidf_latest.json"
    with open(latest_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("CITATION_HERITAGE 174K TF-IDF SUMMARY")
    logger.info("=" * 70)
    
    for name, res in sorted(all_results.items(), key=lambda x: x[1].get('auc_roc', 0), reverse=True):
        if 'error' in res:
            logger.info(f"  {name:<45} ERROR")
        else:
            logger.info(f"  {name:<45} AUC={res['auc_roc']:.4f} [{res['status']}]")
    
    # Reference production default
    prod_default = 'cited_decisions_tfidf_outcome_hybrid_0.5'
    if prod_default in all_results and 'error' not in all_results[prod_default]:
        ref = all_results[prod_default]
        logger.info(f"\n📏 PRODUCTION DEFAULT ({prod_default}): AUC={ref['auc_roc']:.4f} [{ref['status']}]")
    
    logger.info(f"\nResults saved to: {output_file}")
    logger.info("=" * 70)
    
    return all_results

if __name__ == "__main__":
    main()
