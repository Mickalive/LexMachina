#!/usr/bin/env python3
"""
Run citation_heritage benchmark at 174k scale on TF-IDF production representations.
Uses the frozen citation pairs from validate_citation_heritage_174k.py.
"""

import json
import sys
import time
import numpy as np
import logging
from pathlib import Path
from sklearn.metrics import roc_auc_score
from collections import defaultdict

# Add scalable_nn for fast HNSW
sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina/evaluation')
from scalable_nn import build_scalable_nn

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
EMBEDDINGS_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k/embeddings")
PAIRS_PATH = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k_citation_heritage/citation_pairs_174k.json")
METADATA_PATH = EMBEDDINGS_DIR / "metadata.json"
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k_citation_heritage/embedding_results")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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

GLOBAL_SEED = 42

def load_citation_pairs():
    """Load the frozen citation pairs."""
    logger.info(f"Loading citation pairs from {PAIRS_PATH}")
    with open(PAIRS_PATH) as f:
        pairs_data = json.load(f)
    
    positive_pairs = [tuple(p) for p in pairs_data['positive_pairs']]
    negative_pairs = [tuple(p) for p in pairs_data['negative_pairs']]
    
    logger.info(f"Loaded {len(positive_pairs)} positive pairs, {len(negative_pairs)} negative pairs")
    return positive_pairs, negative_pairs, pairs_data

def load_metadata_and_build_did_index():
    """Load metadata and build decision_id -> index mapping."""
    logger.info(f"Loading metadata from {METADATA_PATH}")
    with open(METADATA_PATH) as f:
        metadata = json.load(f)
    
    did_to_idx = {m['decision_id']: i for i, m in enumerate(metadata)}
    logger.info(f"Loaded {len(metadata)} decisions, {len(did_to_idx)} unique decision_ids")
    return metadata, did_to_idx

def run_citation_heritage_on_embeddings(embeddings, metadata, did_to_idx, positive_pairs, negative_pairs):
    """
    Run citation_heritage benchmark: AUC-ROC on citation pairs vs random pairs.
    
    Positive pairs = decisions sharing citations (direct or shared)
    Negative pairs = random decision pairs with no citation relationship
    """
    logger.info("Building HNSW index for fast similarity computation...")
    nn_index = build_scalable_nn(embeddings, n_neighbors=11, force_exact=False)
    logger.info(f"Built {nn_index.backend} index for {embeddings.shape[0]} decisions")
    
    # Compute similarities for positive pairs
    positive_similarities = []
    for did1, did2 in positive_pairs:
        if did1 in did_to_idx and did2 in did_to_idx:
            idx1, idx2 = did_to_idx[did1], did_to_idx[did2]
            # Cosine similarity (embeddings are already normalized in build_scalable_nn)
            v1 = nn_index._normalized[idx1]
            v2 = nn_index._normalized[idx2]
            sim = np.dot(v1, v2)
            positive_similarities.append(sim)
    
    # Compute similarities for negative pairs
    negative_similarities = []
    for did1, did2 in negative_pairs:
        if did1 in did_to_idx and did2 in did_to_idx:
            idx1, idx2 = did_to_idx[did1], did_to_idx[did2]
            v1 = nn_index._normalized[idx1]
            v2 = nn_index._normalized[idx2]
            sim = np.dot(v1, v2)
            negative_similarities.append(sim)
    
    logger.info(f"Valid positive pairs: {len(positive_similarities)}")
    logger.info(f"Valid negative pairs: {len(negative_similarities)}")
    
    # AUC-ROC computation
    y_true = [1] * len(positive_similarities) + [0] * len(negative_similarities)
    y_scores = positive_similarities + negative_similarities
    auc_roc = roc_auc_score(y_true, y_scores)
    
    # Mean similarities
    pos_mean = np.mean(positive_similarities) if positive_similarities else 0
    neg_mean = np.mean(negative_similarities) if negative_similarities else 0
    similarity_gap = pos_mean - neg_mean
    
    # Also compute nearest neighbor citation rate using HNSW
    _, nn_indices = nn_index.kneighbors(n_neighbors=10)
    
    # Build citation partner lookup
    citation_partners = defaultdict(set)
    for did1, did2 in positive_pairs:
        if did1 in did_to_idx and did2 in did_to_idx:
            citation_partners[did_to_idx[did1]].add(did_to_idx[did2])
            citation_partners[did_to_idx[did2]].add(did_to_idx[did1])
    
    nn_citation_count = 0
    nn_total = 0
    for idx, partners in citation_partners.items():
        if partners:
            nn_total += 1
            if partners & set(nn_indices[idx]):
                nn_citation_count += 1
    
    nn_citation_rate = nn_citation_count / nn_total if nn_total > 0 else 0
    
    return {
        'auc_roc': float(auc_roc),
        'positive_pairs': len(positive_similarities),
        'negative_pairs': len(negative_similarities),
        'positive_mean_similarity': float(pos_mean),
        'negative_mean_similarity': float(neg_mean),
        'similarity_gap': float(similarity_gap),
        'nn_citation_rate': float(nn_citation_rate),
        'nn_citation_count': nn_citation_count,
        'nn_total_decisions': nn_total,
        'threshold': 0.65,
        'status': 'PASS' if auc_roc >= 0.65 else 'FAIL',
        'note': 'Citation heritage: AUC-ROC on citation pairs vs random pairs. Threshold 0.65.',
        'backend': nn_index.backend
    }

def main():
    logger.info("=" * 70)
    logger.info("CITATION HERITAGE BENCHMARK AT 174K ON TF-IDF EMBEDDINGS")
    logger.info("=" * 70)
    
    # Load citation pairs
    positive_pairs, negative_pairs, pairs_data = load_citation_pairs()
    
    # Load metadata and build decision_id index
    metadata, did_to_idx = load_metadata_and_build_did_index()
    
    # Evaluate each representation
    all_results = {}
    
    for name, fname in REPRESENTATIONS.items():
        logger.info(f"\n{'='*60}")
        logger.info(f"Evaluating: {name}")
        logger.info(f"{'='*60}")
        
        try:
            emb_path = EMBEDDINGS_DIR / fname
            embeddings = np.load(emb_path, mmap_mode='r')
            logger.info(f"Loaded {name}: {embeddings.shape}")
            
            # Align with metadata
            n_meta = len(metadata)
            if embeddings.shape[0] != n_meta:
                logger.warning(f"Shape mismatch: embeddings {embeddings.shape[0]} vs metadata {n_meta}")
                if embeddings.shape[0] > n_meta:
                    embeddings = embeddings[:n_meta]
                else:
                    raise ValueError(f"Embeddings smaller than metadata: {embeddings.shape[0]} < {n_meta}")
            
            start = time.time()
            result = run_citation_heritage_on_embeddings(embeddings, metadata, did_to_idx, positive_pairs, negative_pairs)
            duration = time.time() - start
            
            result['name'] = name
            result['embedding_shape'] = list(embeddings.shape)
            result['duration_seconds'] = duration
            
            all_results[name] = result
            
            logger.info(f"  {name}: AUC-ROC={result['auc_roc']:.4f} ({result['status']}), "
                       f"pos_mean={result['positive_mean_similarity']:.4f}, "
                       f"neg_mean={result['negative_mean_similarity']:.4f}, "
                       f"gap={result['similarity_gap']:.4f}, "
                       f"nn_cite_rate={result['nn_citation_rate']:.4f}")
        
        except Exception as e:
            logger.error(f"  {name}: ERROR - {e}")
            import traceback
            traceback.print_exc()
            all_results[name] = {
                'name': name,
                'error': str(e),
                'status': 'ERROR'
            }
    
    # Save results
    from datetime import datetime
    output_file = OUTPUT_DIR / f"citation_heritage_174k_tfidf_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    latest_file = OUTPUT_DIR / "citation_heritage_174k_tfidf_latest.json"
    with open(latest_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Summary
    logger.info("\n" + "=" * 90)
    logger.info("CITATION HERITAGE 174K - TF-IDF REPRESENTATIONS SUMMARY")
    logger.info("=" * 90)
    logger.info(f"{'Representation':<45} {'AUC-ROC':>8} {'Status':>6} {'PosMean':>8} {'NegMean':>8} {'Gap':>8} {'NN-Cite':>8}")
    logger.info("-" * 90)
    
    for name, res in sorted(all_results.items()):
        if 'error' in res:
            logger.info(f"{name:<45} {'ERROR':>8} {'ERROR':>6}")
            continue
        logger.info(f"{name:<45} {res['auc_roc']:>8.4f} {res['status']:>6} "
                   f"{res['positive_mean_similarity']:>8.4f} {res['negative_mean_similarity']:>8.4f} "
                   f"{res['similarity_gap']:>8.4f} {res['nn_citation_rate']:>8.4f}")
    
    # Production default
    prod_default = 'cited_decisions_tfidf_outcome_hybrid_0.5'
    if prod_default in all_results and 'error' not in all_results[prod_default]:
        ref = all_results[prod_default]
        logger.info(f"\n📏 PRODUCTION DEFAULT ({prod_default}):")
        logger.info(f"   AUC-ROC: {ref['auc_roc']:.4f} ({ref['status']})")
        logger.info(f"   Similarity gap: {ref['similarity_gap']:.4f}")
        logger.info(f"   NN citation rate: {ref['nn_citation_rate']:.4f}")
    
    logger.info(f"\nResults saved to: {output_file}")
    logger.info("=" * 90)
    
    return all_results

if __name__ == "__main__":
    main()