#!/usr/bin/env python3
"""
Optimized generation of citation pairs for 174k benchmark.
Uses efficient sampling instead of random trial-and-error.
"""
import json
import sys
import numpy as np
from pathlib import Path
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

GRAPH_PATH = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k_citation_heritage/citation_graph_174k.json")
INCOMING_PATH = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k_citation_heritage/citation_graph_174k_incoming.json")
METADATA_PATH = Path("/home/runner/work/LexMachina/LexMachina/evaluation/data/174k/metadata_174k.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k_citation_heritage")
PAIRS_OUTPUT = OUTPUT_DIR / "citation_pairs_174k_full.json"

def main():
    logger.info("Loading citation graph...")
    with open(GRAPH_PATH) as f:
        citation_graph = json.load(f)
    
    with open(INCOMING_PATH) as f:
        incoming_graph = json.load(f)
    
    logger.info("Loading metadata...")
    with open(METADATA_PATH) as f:
        metadata = json.load(f)
    did_to_idx = {m['decision_id']: i for i, m in enumerate(metadata)}
    
    # Build decision_citations (only for decisions in our corpus)
    decision_citations = {}
    for source_did, targets in citation_graph.items():
        if source_did in did_to_idx:
            valid_targets = [t for t in targets if t in did_to_idx]
            if valid_targets:
                decision_citations[source_did] = set(valid_targets)
    
    logger.info(f"Decisions with outgoing citations in corpus: {len(decision_citations)}")
    
    # Build positive pairs efficiently
    logger.info("Building positive pairs...")
    positive_pairs = set()
    
    # Direct citations
    for source_did, targets in decision_citations.items():
        for target_did in targets:
            positive_pairs.add((source_did, target_did))
    
    # Shared citations: decisions citing the same target
    cited_by = defaultdict(set)
    for source_did, targets in decision_citations.items():
        for target_did in targets:
            cited_by[target_did].add(source_did)
    
    for target_did, sources in cited_by.items():
        sources_list = list(sources)
        # Limit to avoid O(n^2) explosion for highly-cited decisions
        if len(sources_list) > 100:
            # Sample pairs instead of all combinations
            np.random.seed(42)
            for _ in range(min(5000, len(sources_list) * 10)):
                i, j = np.random.choice(len(sources_list), 2, replace=False)
                s1, s2 = sources_list[i], sources_list[j]
                positive_pairs.add((s1, s2))
                positive_pairs.add((s2, s1))
        else:
            for i, s1 in enumerate(sources_list):
                for s2 in sources_list[i+1:]:
                    positive_pairs.add((s1, s2))
                    positive_pairs.add((s2, s1))
    
    logger.info(f"Positive pairs: {len(positive_pairs)}")
    
    # Build negative pairs efficiently
    logger.info("Building negative pairs...")
    all_dids = list(did_to_idx.keys())
    n_all = len(all_dids)
    
    # Create a set of all pairs that have ANY citation relationship for fast lookup
    # This is memory-efficient for the positive pairs we have
    has_relation = set(positive_pairs)
    
    # Also add reverse of positive pairs
    for p in list(positive_pairs):
        has_relation.add((p[1], p[0]))
    
    np.random.seed(42)
    negative_pairs = set()
    target_count = len(positive_pairs)
    
    # Strategy: sample random pairs and check against has_relation
    # Since has_relation is relatively small, most random pairs will be negative
    batch_size = 100000
    while len(negative_pairs) < target_count:
        # Generate batch of random pairs
        i_indices = np.random.randint(0, n_all, batch_size)
        j_indices = np.random.randint(0, n_all, batch_size)
        # Ensure i != j
        mask = i_indices != j_indices
        i_indices = i_indices[mask]
        j_indices = j_indices[mask]
        
        for i_idx, j_idx in zip(i_indices, j_indices):
            if len(negative_pairs) >= target_count:
                break
            did1 = all_dids[i_idx]
            did2 = all_dids[j_idx]
            if (did1, did2) not in has_relation:
                negative_pairs.add((did1, did2))
    
    logger.info(f"Negative pairs: {len(negative_pairs)}")
    
    # Load stats from previous run
    with open(OUTPUT_DIR / "citation_pairs_174k.json") as f:
        old_pairs = json.load(f)
    stats = old_pairs.get('stats', {})
    
    pairs_data = {
        'positive_pairs': [list(p) for p in positive_pairs],
        'negative_pairs': [list(p) for p in negative_pairs],
        'stats': stats,
        'num_decisions_in_graph': len(decision_citations),
        'num_decisions_with_incoming': len(incoming_graph),
    }
    
    with open(PAIRS_OUTPUT, 'w') as f:
        json.dump(pairs_data, f, indent=2)
    logger.info(f"Saved full citation pairs to {PAIRS_OUTPUT}")
    
    logger.info("\n" + "=" * 70)
    logger.info("CITATION PAIRS GENERATED")
    logger.info("=" * 70)
    logger.info(f"Positive pairs: {len(positive_pairs)}")
    logger.info(f"Negative pairs: {len(negative_pairs)}")
    logger.info("=" * 70)

if __name__ == "__main__":
    main()
