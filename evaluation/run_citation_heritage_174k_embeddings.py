#!/usr/bin/env python3
"""
Run citation_heritage benchmark on 174k TF-IDF embeddings.
Uses the frozen 137k pair pool (positive/negative citation pairs) to evaluate
whether representations preserve citation proximity.
"""

import json
import numpy as np
import logging
import time
from pathlib import Path
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics import roc_auc_score, average_precision_score
import sys

sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina')
from evaluation.scalable_nn import build_scalable_nn

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
EMBEDDINGS_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k/embeddings")
CITATION_PAIRS = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k_citation_heritage/citation_pairs_174k.json")
METADATA_PATH = EMBEDDINGS_DIR / "metadata.json"
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k_citation_heritage")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Representations to evaluate
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

def load_metadata():
    """Load 174k metadata and create decision_id -> index mapping."""
    logger.info(f"Loading metadata from {METADATA_PATH}")
    with open(METADATA_PATH, 'r') as f:
        metadata = json.load(f)
    did_to_idx = {m['decision_id']: i for i, m in enumerate(metadata)}
    logger.info(f"Loaded {len(metadata)} decisions")
    return metadata, did_to_idx

def load_citation_pairs(did_to_idx):
    """Load citation pairs and filter to those where both decisions are in our corpus."""
    logger.info(f"Loading citation pairs from {CITATION_PAIRS}")
    with open(CITATION_PAIRS, 'r') as f:
        pairs_data = json.load(f)
    
    positive_pairs = pairs_data['positive_pairs']
    negative_pairs = pairs_data['negative_pairs']
    
    # Filter to pairs where both decisions are in our 174k corpus
    filtered_positive = []
    for a, b in positive_pairs:
        if a in did_to_idx and b in did_to_idx:
            filtered_positive.append((did_to_idx[a], did_to_idx[b]))
    
    filtered_negative = []
    for a, b in negative_pairs:
        if a in did_to_idx and b in did_to_idx:
            filtered_negative.append((did_to_idx[a], did_to_idx[b]))
    
    logger.info(f"Positive pairs: {len(positive_pairs)} -> {len(filtered_positive)} in corpus")
    logger.info(f"Negative pairs: {len(negative_pairs)} -> {len(filtered_negative)} in corpus")
    
    return filtered_positive, filtered_negative

def evaluate_citation_heritage(embeddings, positive_pairs, negative_pairs, name):
    """Evaluate citation heritage: do citing/cited decisions appear as neighbors?"""
    logger.info(f"  Evaluating citation heritage for {name}...")
    
    # Build NN index on full corpus
    nn = build_scalable_nn(embeddings, n_neighbors=100, force_exact=False)
    logger.info(f"  Built {nn.backend} index for {embeddings.shape[0]} decisions")
    
    # For each positive pair, check if they're in each other's top-k
    k_values = [5, 10, 20, 50, 100]
    results = {}
    
    # We'll sample a subset of pairs for efficiency at 174k scale
    n_positive = len(positive_pairs)
    sample_size = min(5000, n_positive)
    np.random.seed(42)
    pos_sample_indices = np.random.choice(n_positive, sample_size, replace=False)
    neg_sample_indices = np.random.choice(len(negative_pairs), sample_size, replace=False)
    
    for k in k_values:
        # Get k-NN for all decisions in sampled pairs
        all_indices = set()
        for idx in pos_sample_indices:
            all_indices.add(positive_pairs[idx][0])
            all_indices.add(positive_pairs[idx][1])
        for idx in neg_sample_indices:
            all_indices.add(negative_pairs[idx][0])
            all_indices.add(negative_pairs[idx][1])
        
        all_indices = list(all_indices)
        neighbor_indices = nn.kneighbors(embeddings[all_indices], n_neighbors=k+1)[1][:, 1:]
        neighbor_sets = {idx: set(neighbors) for idx, neighbors in zip(all_indices, neighbor_indices)}
        
        # Check positive pairs
        pos_recalled = 0
        for idx in pos_sample_indices:
            a, b = positive_pairs[idx]
            if b in neighbor_sets.get(a, set()) or a in neighbor_sets.get(b, set()):
                pos_recalled += 1
        
        # Check negative pairs (should NOT be neighbors)
        neg_recalled = 0
        for idx in neg_sample_indices:
            a, b = negative_pairs[idx]
            if b in neighbor_sets.get(a, set()) or a in neighbor_sets.get(b, set()):
                neg_recalled += 1
        
        pos_recall = pos_recalled / sample_size
        neg_recall = neg_recalled / sample_size
        
        # Compute AUC using distances
        # For a sample of pairs, get the distance between them
        pos_dists = []
        for idx in pos_sample_indices[:1000]:
            a, b = positive_pairs[idx]
            dist = 1 - np.dot(embeddings[a], embeddings[b])  # cosine distance
            pos_dists.append(dist)
        
        neg_dists = []
        for idx in neg_sample_indices[:1000]:
            a, b = negative_pairs[idx]
            dist = 1 - np.dot(embeddings[a], embeddings[b])
            neg_dists.append(dist)
        
        if pos_dists and neg_dists:
            y_true = [1] * len(pos_dists) + [0] * len(neg_dists)
            y_score = [-d for d in pos_dists + neg_dists]  # negative distance = similarity
            try:
                auc = roc_auc_score(y_true, y_score)
                ap = average_precision_score(y_true, y_score)
            except:
                auc = 0.5
                ap = 0.0
        else:
            auc = 0.5
            ap = 0.0
        
        results[f'k{k}'] = {
            'positive_recall': pos_recall,
            'negative_recall': neg_recall,
            'precision': pos_recall / (pos_recall + neg_recall) if (pos_recall + neg_recall) > 0 else 0,
            'auc': float(auc),
            'average_precision': float(ap),
            'sample_size': sample_size
        }
        
        logger.info(f"    k={k}: pos_recall={pos_recall:.4f}, neg_recall={neg_recall:.4f}, auc={auc:.4f}, ap={ap:.4f}")
    
    # Overall status: PASS if AUC > 0.6 and k=10 pos_recall > 0.2
    k10_pos = results['k10']['positive_recall']
    k10_auc = results['k10']['auc']
    status = 'PASS' if (k10_auc > 0.6 and k10_pos > 0.2) else 'FAIL'
    
    return {
        'name': name,
        'k_values': results,
        'status': status,
        'note': f'Citation heritage: positive pairs should be closer than random. AUC>0.6 and recall@10>0.2 indicates citation structure preserved. Sample size: {sample_size}'
    }

def main():
    logger.info("=" * 70)
    logger.info("CITATION_HERITAGE BENCHMARK ON 174K TF-IDF EMBEDDINGS")
    logger.info("=" * 70)
    
    # Load metadata and citation pairs
    metadata, did_to_idx = load_metadata()
    positive_pairs, negative_pairs = load_citation_pairs(did_to_idx)
    
    if len(positive_pairs) < 100:
        logger.error(f"Too few positive pairs in corpus: {len(positive_pairs)}")
        return
    
    all_results = {}
    
    for name, fname in REPRESENTATIONS.items():
        logger.info(f"\nProcessing {name}...")
        try:
            emb_path = EMBEDDINGS_DIR / fname
            embeddings = np.load(emb_path, mmap_mode='r')
            logger.info(f"  Loaded {embeddings.shape}")
            
            result = evaluate_citation_heritage(embeddings, positive_pairs, negative_pairs, name)
            all_results[name] = result
            
        except Exception as e:
            logger.error(f"  Error evaluating {name}: {e}")
            import traceback
            traceback.print_exc()
            all_results[name] = {'name': name, 'error': str(e), 'status': 'ERROR'}
    
    # Save results
    from datetime import datetime
    output_file = OUTPUT_DIR / f"citation_heritage_174k_embeddings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Also save latest
    latest_file = OUTPUT_DIR / "citation_heritage_174k_embeddings_latest.json"
    with open(latest_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("CITATION_HERITAGE 174K EMBEDDINGS - SUMMARY")
    logger.info("=" * 70)
    for name, result in all_results.items():
        if 'error' in result:
            logger.info(f"  {name}: ERROR - {result['error']}")
        else:
            k10 = result['k_values']['k10']
            logger.info(f"  {name}: status={result['status']}, recall@10={k10['positive_recall']:.4f}, auc={k10['auc']:.4f}, ap={k10['average_precision']:.4f}")
    
    logger.info(f"\nResults saved to: {output_file}")
    logger.info("=" * 70)
    
    return all_results

if __name__ == "__main__":
    main()