#!/usr/bin/env python3
"""
Validate citation_heritage benchmark at 174k scale using the resolved citation graph.
This prepares the benchmark infrastructure for when 174k embeddings become available.
"""
import json
import sys
from pathlib import Path
from collections import defaultdict
import logging
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
CITATION_TO_DECISION_ID = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical/resolved_full/citation_to_decision_id.json")
CITATION_GRAPH_RESOLVED = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical/resolved_full/citation_graph_resolved.json")
METADATA_174K = Path("/home/runner/work/LexMachina/LexMachina/evaluation/data/174k/metadata_174k.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k_citation_heritage")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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

def load_metadata():
    """Load 174k metadata."""
    logger.info(f"Loading metadata from {METADATA_174K}")
    with open(METADATA_174K) as f:
        metadata = json.load(f)
    
    # Create decision_id -> index mapping
    did_to_idx = {m['decision_id']: i for i, m in enumerate(metadata)}
    logger.info(f"Loaded {len(metadata)} decisions, {len(did_to_idx)} unique decision_ids")
    
    return metadata, did_to_idx

def build_citation_pairs(graph, did_to_idx):
    """Build positive and negative citation pairs for citation_heritage benchmark."""
    logger.info("Building citation pairs...")
    
    outgoing = graph.get('outgoing', {})
    
    # Positive pairs: decisions that cite each other (directly or indirectly)
    positive_pairs = set()
    decision_citations = defaultdict(set)  # decision_id -> set of cited decision_ids
    
    for source_did, citations in outgoing.items():
        for c in citations:
            target_did = c.get('target_decision_id')
            if target_did and target_did in did_to_idx and source_did in did_to_idx:
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
    all_dids = list(did_to_idx.keys())
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

def validate_citation_coverage(metadata, did_to_idx, graph):
    """Validate how many decisions in the 174k corpus have citation data."""
    outgoing = graph.get('outgoing', {})
    
    # Count decisions in 174k that appear in citation graph
    in_graph = 0
    with_outgoing = 0
    for m in metadata:
        did = m['decision_id']
        if did in outgoing:
            in_graph += 1
            if outgoing[did]:
                with_outgoing += 1
    
    logger.info(f"Decisions in 174k corpus: {len(metadata)}")
    logger.info(f"Decisions appearing in citation graph: {in_graph} ({100*in_graph/len(metadata):.1f}%)")
    logger.info(f"Decisions with outgoing citations: {with_outgoing} ({100*with_outgoing/len(metadata):.1f}%)")
    
    # Check how many of the 2,019 resolved citations map to decisions in our 174k corpus
    citation_to_did = {}
    with open(CITATION_TO_DECISION_ID) as f:
        citation_to_did = json.load(f)
    
    resolved_in_corpus = sum(1 for v in citation_to_did.values() 
                            if v.get('target_decision_id') in did_to_idx)
    
    logger.info(f"Resolved citations mapping to 174k corpus: {resolved_in_corpus}/{len(citation_to_did)}")
    
    return {
        'total_corpus': len(metadata),
        'in_citation_graph': in_graph,
        'with_outgoing_citations': with_outgoing,
        'resolved_citations_in_corpus': resolved_in_corpus,
    }

def main():
    logger.info("=" * 70)
    logger.info("VALIDATE CITATION_HERITAGE BENCHMARK AT 174K SCALE")
    logger.info("=" * 70)
    
    # Load data
    graph = load_citation_graph()
    metadata, did_to_idx = load_metadata()
    
    # Validate coverage
    coverage = validate_citation_coverage(metadata, did_to_idx, graph)
    
    # Build citation pairs
    positive_pairs, negative_pairs, decision_citations = build_citation_pairs(graph, did_to_idx)
    
    # Save citation pairs for later benchmark runs
    pairs_data = {
        'positive_pairs': [list(p) for p in positive_pairs],
        'negative_pairs': [list(p) for p in negative_pairs],
        'coverage': coverage,
        'citation_graph_stats': {
            'total_outgoing': len(graph.get('outgoing', {})),
            'total_citations': sum(len(c) for c in graph.get('outgoing', {}).values()),
        }
    }
    
    with open(OUTPUT_DIR / "citation_pairs_174k.json", "w") as f:
        json.dump(pairs_data, f, indent=2)
    
    logger.info(f"Saved citation pairs to {OUTPUT_DIR / 'citation_pairs_174k.json'}")
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("CITATION_HERITAGE 174K VALIDATION SUMMARY")
    logger.info("=" * 70)
    logger.info(f"174k corpus decisions: {coverage['total_corpus']}")
    logger.info(f"Decisions in citation graph: {coverage['in_citation_graph']} ({100*coverage['in_citation_graph']/coverage['total_corpus']:.1f}%)")
    logger.info(f"Decisions with outgoing citations: {coverage['with_outgoing_citations']} ({100*coverage['with_outgoing_citations']/coverage['total_corpus']:.1f}%)")
    logger.info(f"Resolved citations mapping to corpus: {coverage['resolved_citations_in_corpus']}")
    logger.info(f"Positive pairs (direct + shared citations): {len(positive_pairs)}")
    logger.info(f"Negative pairs (no citation relation): {len(negative_pairs)}")
    logger.info(f"Benchmark ready for 174k embeddings when available")
    logger.info("=" * 70)

if __name__ == "__main__":
    main()
