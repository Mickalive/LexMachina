#!/usr/bin/env python3
"""
Citation heritage verification for TF-IDF 174k representations.
Uses the frozen 1,020-pair pool with 174k citation-ID resolution.
"""

import json
import numpy as np
import logging
import sys
import time
from pathlib import Path
from typing import List, Dict, Tuple, Any
from sklearn.metrics import roc_auc_score

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

LEX_ACCEPTED_ROOT = Path("/tmp/lex_accepted")
METADATA_174K_PATH = LEX_ACCEPTED_ROOT / "legal-distance/evaluation/data/174k/metadata_174k.json"
CITATION_PAIRS_PATH = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k_citation_heritage/citation_pairs_174k.json")

TFIDF_EMBEDDINGS_DIR = LEX_ACCEPTED_ROOT / "fractal-map/results/fractal_map/hierarchical_map_174k/tfidf_embeddings"
LEGAL_TFIDF_EMBEDDINGS_DIR = LEX_ACCEPTED_ROOT / "fractal-map/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings"

TFIDF_REPRESENTATIONS = {
    'regeste_tfidf': TFIDF_EMBEDDINGS_DIR / "regeste_tfidf.npy",
    'full_text_tfidf_light': TFIDF_EMBEDDINGS_DIR / "full_text_tfidf_light.npy",
    'regeste_full_text_hybrid_0.5': TFIDF_EMBEDDINGS_DIR / "regeste_full_text_hybrid_0.5.npy",
    'regeste_full_text_hybrid_0.7': TFIDF_EMBEDDINGS_DIR / "regeste_full_text_hybrid_0.7.npy",
    'cited_decisions_tfidf': LEGAL_TFIDF_EMBEDDINGS_DIR / "cited_decisions_tfidf.npy",
    'cited_decisions_tfidf_outcome_hybrid_0.5': LEGAL_TFIDF_EMBEDDINGS_DIR / "cited_decisions_tfidf_outcome_hybrid_0.5.npy",
    'cited_decisions_tfidf_outcome_hybrid_0.7': LEGAL_TFIDF_EMBEDDINGS_DIR / "cited_decisions_tfidf_outcome_hybrid_0.7.npy",
    'outcome_tfidf': LEGAL_TFIDF_EMBEDDINGS_DIR / "outcome_tfidf.npy",
}

def load_citation_pairs(metadata: List[Dict]) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
    with open(CITATION_PAIRS_PATH) as f:
        pairs_data = json.load(f)
    
    decision_id_to_idx = {m['decision_id']: i for i, m in enumerate(metadata)}
    
    positive_pairs = []
    for src_id, tgt_id in pairs_data['positive_pairs']:
        if src_id in decision_id_to_idx and tgt_id in decision_id_to_idx:
            positive_pairs.append((decision_id_to_idx[src_id], decision_id_to_idx[tgt_id]))
    
    negative_pairs = []
    for src_id, tgt_id in pairs_data['negative_pairs']:
        if src_id in decision_id_to_idx and tgt_id in decision_id_to_idx:
            negative_pairs.append((decision_id_to_idx[src_id], decision_id_to_idx[tgt_id]))
    
    logger.info(f"Citation heritage: {len(positive_pairs)} positive pairs, {len(negative_pairs)} negative pairs")
    return positive_pairs, negative_pairs

def run_citation_heritage(embeddings: np.ndarray, positive_pairs: List[Tuple[int, int]], 
                          negative_pairs: List[Tuple[int, int]]) -> Dict[str, Any]:
    pos_similarities = []
    for i, j in positive_pairs:
        if i < len(embeddings) and j < len(embeddings):
            norm_i = np.linalg.norm(embeddings[i])
            norm_j = np.linalg.norm(embeddings[j])
            if norm_i > 0 and norm_j > 0:
                sim = np.dot(embeddings[i], embeddings[j]) / (norm_i * norm_j)
                pos_similarities.append(sim)
    
    neg_similarities = []
    for i, j in negative_pairs:
        if i < len(embeddings) and j < len(embeddings):
            norm_i = np.linalg.norm(embeddings[i])
            norm_j = np.linalg.norm(embeddings[j])
            if norm_i > 0 and norm_j > 0:
                sim = np.dot(embeddings[i], embeddings[j]) / (norm_i * norm_j)
                neg_similarities.append(sim)
    
    y_true = [1] * len(pos_similarities) + [0] * len(neg_similarities)
    y_score = pos_similarities + neg_similarities
    
    if len(set(y_true)) < 2:
        return {'auc_roc': None, 'status': 'ERROR', 'note': 'Insufficient class diversity'}
    
    auc_roc = roc_auc_score(y_true, y_score)
    status = 'PASS' if auc_roc >= 0.65 else 'FAIL'
    
    return {
        'auc_roc': float(auc_roc),
        'positive_mean_sim': float(np.mean(pos_similarities)) if pos_similarities else 0,
        'negative_mean_sim': float(np.mean(neg_similarities)) if neg_similarities else 0,
        'mean_similarity_gap': float(np.mean(pos_similarities) - np.mean(neg_similarities)) if pos_similarities and neg_similarities else 0,
        'num_positive_pairs': len(pos_similarities),
        'num_negative_pairs': len(neg_similarities),
        'status': status
    }

def main():
    logger.info("Loading metadata...")
    with open(METADATA_174K_PATH) as f:
        metadata = json.load(f)
    logger.info(f"Loaded metadata for {len(metadata)} decisions")
    
    logger.info("Loading citation pairs...")
    pos_pairs, neg_pairs = load_citation_pairs(metadata)
    
    logger.info("\nRunning citation heritage validation on all 8 representations...")
    all_results = {}
    
    for name, path in TFIDF_REPRESENTATIONS.items():
        logger.info(f"  Loading {name}...")
        embeddings = np.load(path)
        
        if len(embeddings) > len(metadata):
            embeddings = embeddings[:len(metadata)]
        
        result = run_citation_heritage(embeddings, pos_pairs, neg_pairs)
        all_results[name] = result
        
        auc = result.get('auc_roc')
        auc_str = f"{auc:.4f}" if auc is not None else "N/A"
        logger.info(f"  {name}: AUC={auc_str} ({result['status']})")
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("CITATION HERITAGE VALIDATION - 174k (Threshold: AUC >= 0.65)")
    logger.info("=" * 80)
    logger.info(f"{'Representation':<45} {'AUC':>7} {'Status':>7}")
    logger.info("-" * 80)
    
    for name, res in sorted(all_results.items(), key=lambda x: x[1].get('auc_roc', 0) or 0, reverse=True):
        auc = res.get('auc_roc')
        auc_str = f"{auc:.4f}" if auc is not None else "N/A"
        logger.info(f"{name:<45} {auc_str:>7} {res['status']:>7}")
    
    logger.info("=" * 80)
    
    # Save
    OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k_tfidf_formal_suite")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    output_file = OUTPUT_DIR / f"citation_heritage_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    latest_file = OUTPUT_DIR / "citation_heritage_latest.json"
    with open(latest_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    logger.info(f"\nResults saved to: {output_file}")

if __name__ == "__main__":
    main()
