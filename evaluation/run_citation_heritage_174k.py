#!/usr/bin/env python3
"""
Run citation_heritage benchmark at 174k scale on TF-IDF family representations.
Uses the frozen citation pairs from validate_citation_heritage_174k.py.
"""

import json
import numpy as np
import logging
import time
from pathlib import Path
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics import roc_auc_score, average_precision_score

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Configuration
EMBEDDINGS_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k/embeddings")
CITATION_PAIRS_PATH = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k_citation_heritage/citation_pairs_174k.json")
METADATA_PATH = EMBEDDINGS_DIR / "metadata.json"
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k_citation_heritage/benchmark")
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

FROZEN_SEED = 42
K_NEIGHBORS = 20

np.random.seed(FROZEN_SEED)

def load_citation_pairs():
    with open(CITATION_PAIRS_PATH) as f:
        data = json.load(f)
    positive_pairs = set(tuple(p) for p in data['positive_pairs'])
    negative_pairs = set(tuple(p) for p in data['negative_pairs'])
    logger.info(f"Loaded {len(positive_pairs)} positive pairs, {len(negative_pairs)} negative pairs")
    return positive_pairs, negative_pairs, data

def load_metadata():
    with open(METADATA_PATH) as f:
        metadata = json.load(f)
    did_to_idx = {m['decision_id']: i for i, m in enumerate(metadata)}
    logger.info(f"Loaded metadata for {len(metadata)} decisions")
    return metadata, did_to_idx

def load_embedding(name):
    path = EMBEDDINGS_DIR / REPRESENTATIONS[name]
    if not path.exists():
        raise FileNotFoundError(f"Embedding not found: {path}")
    emb = np.load(path, mmap_mode='r')
    logger.info(f"Loaded {name}: {emb.shape}")
    return emb

def run_citation_heritage_benchmark(embeddings, metadata, did_to_idx, positive_pairs, negative_pairs):
    """Run citation heritage benchmark using exact k-NN."""
    logger.info("Building exact k-NN index...")
    nn = NearestNeighbors(n_neighbors=K_NEIGHBORS + 1, metric='cosine')
    nn.fit(embeddings)
    _, indices = nn.kneighbors(embeddings)
    neighbors = indices[:, 1:]  # Exclude self
    
    # Build neighbor sets for fast lookup
    neighbor_sets = [set(n) for n in neighbors]
    
    # Evaluate positive pairs
    pos_scores = []
    pos_found = 0
    for did1, did2 in positive_pairs:
        if did1 in did_to_idx and did2 in did_to_idx:
            idx1 = did_to_idx[did1]
            idx2 = did_to_idx[did2]
            found = idx2 in neighbor_sets[idx1]
            pos_scores.append(1.0 if found else 0.0)
            if found:
                pos_found += 1
    
    # Evaluate negative pairs
    neg_scores = []
    neg_found = 0
    for did1, did2 in negative_pairs:
        if did1 in did_to_idx and did2 in did_to_idx:
            idx1 = did_to_idx[did1]
            idx2 = did_to_idx[did2]
            found = idx2 in neighbor_sets[idx1]
            neg_scores.append(1.0 if found else 0.0)
            if found:
                neg_found += 1
    
    # Create labels and scores for AUC/AP
    y_true = [1] * len(pos_scores) + [0] * len(neg_scores)
    y_scores = pos_scores + neg_scores
    
    if len(set(y_true)) > 1:
        auc = roc_auc_score(y_true, y_scores)
        ap = average_precision_score(y_true, y_scores)
    else:
        auc = 0.5
        ap = 0.0
    
    pos_rate = pos_found / len(pos_scores) if pos_scores else 0
    neg_rate = neg_found / len(neg_scores) if neg_scores else 0
    
    return {
        'auc': float(auc),
        'average_precision': float(ap),
        'positive_recall_at_k': float(pos_rate),
        'negative_rate_at_k': float(neg_rate),
        'positive_pairs_evaluated': len(pos_scores),
        'negative_pairs_evaluated': len(neg_scores),
        'positive_found': pos_found,
        'negative_found': neg_found,
        'k': K_NEIGHBORS,
    }

def main():
    logger.info("=" * 70)
    logger.info("CITATION_HERITAGE BENCHMARK AT 174K (TF-IDF FAMILY)")
    logger.info("=" * 70)
    
    # Load citation pairs
    positive_pairs, negative_pairs, pairs_data = load_citation_pairs()
    
    # Load metadata
    metadata, did_to_idx = load_metadata()
    
    # Verify embeddings exist
    for name, fname in REPRESENTATIONS.items():
        path = EMBEDDINGS_DIR / fname
        if not path.exists():
            logger.error(f"Missing embedding: {path}")
            return
    
    all_results = {
        'run_id': f'citation_heritage_174k_{int(time.time())}',
        'direction_version': 27,
        'seed': FROZEN_SEED,
        'k_neighbors': K_NEIGHBORS,
        'citation_pairs_info': {
            'positive_pairs_total': len(positive_pairs),
            'negative_pairs_total': len(negative_pairs),
            'coverage': pairs_data.get('coverage', {}),
        },
        'per_representation': {},
    }
    
    for name in REPRESENTATIONS.keys():
        logger.info(f"\nEvaluating {name}...")
        try:
            embeddings = load_embedding(name)
            
            # Verify shape matches metadata
            if embeddings.shape[0] != len(metadata):
                logger.warning(f"  Shape mismatch: embeddings {embeddings.shape[0]} vs metadata {len(metadata)}")
                if embeddings.shape[0] > len(metadata):
                    embeddings = embeddings[:len(metadata)]
                else:
                    all_results['per_representation'][name] = {'error': 'embedding/metadata length mismatch'}
                    continue
            
            result = run_citation_heritage_benchmark(embeddings, metadata, did_to_idx, positive_pairs, negative_pairs)
            all_results['per_representation'][name] = result
            
            logger.info(f"  {name}: AUC={result['auc']:.4f}, AP={result['average_precision']:.4f}, "
                       f"pos_recall@20={result['positive_recall_at_k']:.4f}, neg_rate={result['negative_rate_at_k']:.4f}")
            
        except Exception as e:
            logger.error(f"  {name}: ERROR - {e}")
            import traceback
            traceback.print_exc()
            all_results['per_representation'][name] = {'error': str(e)}
    
    # Save results
    output_file = OUTPUT_DIR / f"citation_heritage_174k_tfidf_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    latest_file = OUTPUT_DIR / "citation_heritage_174k_tfidf_latest.json"
    with open(latest_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("CITATION_HERITAGE 174K SUMMARY")
    logger.info("=" * 70)
    logger.info(f"{'Representation':<45} {'AUC':>6} {'AP':>6} {'Pos@20':>7} {'Neg@20':>7}")
    logger.info("-" * 70)
    
    for name, res in all_results['per_representation'].items():
        if 'error' in res:
            logger.info(f"{name:<45} {'ERROR':>6} {'ERROR':>6} {'ERROR':>7} {'ERROR':>7}")
        else:
            logger.info(f"{name:<45} {res['auc']:>6.4f} {res['average_precision']:>6.4f} "
                       f"{res['positive_recall_at_k']:>7.4f} {res['negative_rate_at_k']:>7.4f}")
    
    logger.info(f"\nResults saved to: {output_file}")
    logger.info("=" * 70)
    
    return all_results

if __name__ == "__main__":
    main()