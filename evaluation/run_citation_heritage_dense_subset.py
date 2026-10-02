#!/usr/bin/env python3
"""
Run citation_heritage benchmark on dense embeddings subset (15-year, 19-year) 
by building citation pairs directly from the resolved citation graph for each subset.
"""
import json
import numpy as np
import logging
import sys
from pathlib import Path
from collections import defaultdict
from sklearn.metrics import roc_auc_score
from datetime import datetime

# Add paths
sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina')

from evaluation.run_15year_dense_formal_suite import (
    load_dense_embeddings_subset,
    apply_center_projection,
    apply_pca,
    load_citation_tfidf_for_subset,
    load_outcome_hybrid_for_subset,
    create_concat,
    COMPLETED_YEARS,
    DENSE_CHECKPOINTS_DIR,
    TFIDF_EMBEDDINGS_DIR,
    FULL_METADATA_PATH,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
CITATION_GRAPH_RESOLVED = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical/resolved_full/citation_graph_resolved.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k_citation_heritage")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Years for 19-year evaluation
COMPLETED_YEARS_19 = list(range(2000, 2019))  # 2000-2018 inclusive (19 years)


def load_full_metadata():
    """Load full 174k metadata."""
    logger.info(f"Loading full 174k metadata from {FULL_METADATA_PATH}")
    with open(FULL_METADATA_PATH) as f:
        metadata = json.load(f)
    did_to_idx = {m['decision_id']: i for i, m in enumerate(metadata)}
    logger.info(f"Loaded {len(metadata)} decisions, {len(did_to_idx)} unique decision_ids")
    return metadata, did_to_idx


def load_citation_graph():
    """Load the resolved citation graph."""
    logger.info(f"Loading citation graph from {CITATION_GRAPH_RESOLVED}")
    with open(CITATION_GRAPH_RESOLVED) as f:
        graph = json.load(f)
    
    # Count stats
    outgoing = graph.get('outgoing', {})
    total_decisions_with_citations = len(outgoing)
    total_citations = sum(len(citations) for citations in outgoing.values())
    resolved_citations = sum(1 for citations in outgoing.values() 
                            for c in citations if c.get('target_decision_id') is not None)
    unresolved_citations = total_citations - resolved_citations
    
    logger.info(f"Decisions with outgoing citations: {total_decisions_with_citations}")
    logger.info(f"Total citations: {total_citations}")
    logger.info(f"Resolved citations: {resolved_citations} ({100*resolved_citations/total_citations:.1f}%)")
    logger.info(f"Unresolved citations: {unresolved_citations} ({100*unresolved_citations/total_citations:.1f}%)")
    
    return graph


def build_citation_pairs_for_subset(graph, subset_did_to_idx):
    """Build positive and negative citation pairs for a subset of decisions."""
    logger.info("Building citation pairs for subset...")
    
    outgoing = graph.get('outgoing', {})
    
    # Positive pairs: decisions that cite each other (directly or indirectly)
    positive_pairs = set()
    decision_citations = defaultdict(set)  # decision_id -> set of cited decision_ids
    
    for source_did, citations in outgoing.items():
        if source_did not in subset_did_to_idx:
            continue
        for c in citations:
            target_did = c.get('target_decision_id')
            if target_did and target_did in subset_did_to_idx and source_did in subset_did_to_idx:
                # Direct citation pair
                positive_pairs.add((source_did, target_did))
                decision_citations[source_did].add(target_did)
    
    # Also add shared-citation pairs (decisions that cite the same decision)
    cited_by = defaultdict(set)  # target_did -> set of source_dids
    for source_did, targets in decision_citations.items():
        for target_did in targets:
            cited_by[target_did].add(source_did)
    
    for target_did, sources in cited_by.items():
        sources_list = list(sources)
        for i, s1 in enumerate(sources_list):
            for s2 in sources_list[i+1:]:
                positive_pairs.add((s1, s2))
                positive_pairs.add((s2, s1))
    
    logger.info(f"Positive citation pairs (direct + shared): {len(positive_pairs)}")
    
    # Sample negative pairs: random decision pairs with no citation relationship
    # We'll sample the same number as positive pairs for balanced evaluation
    all_dids = list(subset_did_to_idx.keys())
    np.random.seed(42)
    
    negative_pairs = set()
    max_attempts = len(positive_pairs) * 10
    attempts = 0
    
    while len(negative_pairs) < len(positive_pairs) and attempts < max_attempts:
        i, j = np.random.choice(len(all_dids), 2, replace=False)
        did1, did2 = all_dids[i], all_dids[j]
        
        # Check if they have any citation relationship
        has_relation = False
        if did1 in decision_citations and did2 in decision_citations[did1]:
            has_relation = True
        if did2 in decision_citations and did1 in decision_citations[did2]:
            has_relation = True
        # Check shared citations
        if did1 in decision_citations and did2 in decision_citations:
            if decision_citations[did1] & decision_citations[did2]:
                has_relation = True
        
        if not has_relation:
            negative_pairs.add((did1, did2))
        
        attempts += 1
    
    logger.info(f"Negative pairs sampled: {len(negative_pairs)} (attempts: {attempts})")
    
    return positive_pairs, negative_pairs, decision_citations


def cosine_similarity(a, b):
    """Compute cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def run_citation_heritage_on_embeddings(name, embeddings, subset_did_to_idx, valid_positive, valid_negative):
    """Run citation heritage benchmark on given embeddings."""
    logger.info(f"Running citation_heritage on {name}...")
    
    if len(valid_positive) < 10 or len(valid_negative) < 10:
        logger.warning(f"  Insufficient valid pairs: positive={len(valid_positive)}, negative={len(valid_negative)}")
        return {'status': 'FAILED', 'error': 'Insufficient valid pairs'}
    
    # Compute similarities
    positive_scores = []
    for d1, d2 in valid_positive:
        sim = cosine_similarity(embeddings[subset_did_to_idx[d1]], embeddings[subset_did_to_idx[d2]])
        positive_scores.append(sim)
    
    negative_scores = []
    for d1, d2 in valid_negative:
        sim = cosine_similarity(embeddings[subset_did_to_idx[d1]], embeddings[subset_did_to_idx[d2]])
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
        'status': 'PASS' if auc_roc >= 0.7 else 'FAIL'
    }
    
    logger.info(f"  {name}: AUC={auc_roc:.4f} (pos={len(valid_positive)}, neg={len(valid_negative)}) [{metrics['status']}]")
    return metrics


def load_dense_subset(years, label):
    """Load dense embeddings for specified years."""
    logger.info(f"\n=== Loading {label} dense embeddings ({years[0]}-{years[-1]}) ===")
    
    full_metadata, _ = load_full_metadata()
    dense_768, subset_metadata = load_dense_embeddings_subset(full_metadata, years)
    
    # Apply center projection
    logger.info("Applying language center projection...")
    dense_cp_768 = apply_center_projection(dense_768, subset_metadata)
    
    # Create PCA versions
    logger.info("Creating PCA-reduced versions...")
    dense_cp_128 = apply_pca(dense_cp_768, 128)
    dense_cp_64 = apply_pca(dense_cp_768, 64)
    
    # Load citation embeddings for subset
    logger.info("Loading citation embeddings for subset...")
    citation_tfidf = load_citation_tfidf_for_subset(subset_metadata, full_metadata)
    hybrid_05 = load_outcome_hybrid_for_subset(subset_metadata, full_metadata, 0.5)
    hybrid_07 = load_outcome_hybrid_for_subset(subset_metadata, full_metadata, 0.7)
    
    # Create linear combinations
    logger.info("Creating linear combinations...")
    linear_citation_concat = create_concat(dense_cp_64, citation_tfidf, f"linear_citation_concat_{label}")
    linear_hybrid05_concat = create_concat(dense_cp_64, hybrid_05, f"linear_hybrid05_concat_{label}")
    linear_hybrid07_concat = create_concat(dense_cp_64, hybrid_07, f"linear_hybrid07_concat_{label}")
    
    # Build decision_id -> index mapping for subset
    subset_did_to_idx = {m['decision_id']: i for i, m in enumerate(subset_metadata)}
    
    representations = {
        f'center_projected_768dim_{label}': dense_cp_768,
        f'center_projected_128dim_{label}': dense_cp_128,
        f'center_projected_64dim_{label}': dense_cp_64,
        f'linear_citation_concat_{label}': linear_citation_concat,
        f'linear_hybrid05_concat_{label}': linear_hybrid05_concat,
        f'linear_hybrid07_concat_{label}': linear_hybrid07_concat,
        f'cited_decisions_tfidf_{label}': citation_tfidf,
        f'cited_decisions_tfidf_outcome_hybrid_0.5_{label}': hybrid_05,
        f'cited_decisions_tfidf_outcome_hybrid_0.7_{label}': hybrid_07,
    }
    
    return representations, subset_metadata, subset_did_to_idx


def main():
    logger.info("=" * 70)
    logger.info("CITATION_HERITAGE BENCHMARK ON DENSE SUBSETS")
    logger.info("=" * 70)
    
    # Load citation graph
    graph = load_citation_graph()
    
    all_results = {}
    
    # Evaluate 15-year dense embeddings
    logger.info("\n" + "=" * 70)
    logger.info("EVALUATING 15-YEAR DENSE EMBEDDINGS (2000-2014)")
    logger.info("=" * 70)
    
    reps_15year, meta_15year, did_to_idx_15year = load_dense_subset(COMPLETED_YEARS, "15year")
    pos_15, neg_15, _ = build_citation_pairs_for_subset(graph, did_to_idx_15year)
    
    for name, embeddings in reps_15year.items():
        try:
            result = run_citation_heritage_on_embeddings(name, embeddings, did_to_idx_15year, pos_15, neg_15)
            all_results[name] = result
        except Exception as e:
            logger.error(f"  {name}: ERROR - {e}")
            import traceback
            traceback.print_exc()
            all_results[name] = {'error': str(e), 'status': 'ERROR'}
    
    # Evaluate 19-year dense embeddings
    logger.info("\n" + "=" * 70)
    logger.info("EVALUATING 19-YEAR DENSE EMBEDDINGS (2000-2018)")
    logger.info("=" * 70)
    
    reps_19year, meta_19year, did_to_idx_19year = load_dense_subset(COMPLETED_YEARS_19, "19year")
    pos_19, neg_19, _ = build_citation_pairs_for_subset(graph, did_to_idx_19year)
    
    for name, embeddings in reps_19year.items():
        try:
            result = run_citation_heritage_on_embeddings(name, embeddings, did_to_idx_19year, pos_19, neg_19)
            all_results[name] = result
        except Exception as e:
            logger.error(f"  {name}: ERROR - {e}")
            import traceback
            traceback.print_exc()
            all_results[name] = {'error': str(e), 'status': 'ERROR'}
    
    # Save results
    output_file = OUTPUT_DIR / f"citation_heritage_dense_subsets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    latest_file = OUTPUT_DIR / "citation_heritage_dense_subsets_latest.json"
    with open(latest_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("CITATION_HERITAGE DENSE SUBSETS SUMMARY")
    logger.info("=" * 70)
    
    for label in ["15year", "19year"]:
        logger.info(f"\n--- {label} ---")
        label_results = {k: v for k, v in all_results.items() if label in k}
        for name, res in sorted(label_results.items(), key=lambda x: x[1].get('auc_roc', 0) if 'error' not in x[1] else -1, reverse=True):
            if 'error' in res:
                logger.info(f"  {name:<55} ERROR")
            else:
                logger.info(f"  {name:<55} AUC={res['auc_roc']:.4f} [{res['status']}]")
    
    logger.info(f"\nResults saved to: {output_file}")
    logger.info("=" * 70)
    
    return all_results


if __name__ == "__main__":
    main()