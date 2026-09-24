#!/usr/bin/env python3
"""
Build full 174k citation graph from cited_decisions field in corpus,
using the resolved citation-to-decision_id mapping.
This enables citation_heritage benchmark at full 174k scale.
"""
import json
import sys
from pathlib import Path
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
CITATION_MAP = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical/resolved_full/citation_to_decision_id.json")
CANONICAL_DIR = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
YEAR_FILES = [f"bger_{year}.jsonl" for year in range(2000, 2027)]
METADATA_174K = Path("/home/runner/work/LexMachina/LexMachina/evaluation/data/174k/metadata_174k.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k_citation_heritage")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_citation_map():
    """Load citation string -> decision_id mapping."""
    logger.info(f"Loading citation map from {CITATION_MAP}")
    with open(CITATION_MAP) as f:
        citation_map = json.load(f)
    logger.info(f"Loaded {len(citation_map)} resolved citation strings")
    return citation_map

def load_metadata_index():
    """Load 174k metadata decision_id -> index mapping."""
    logger.info(f"Loading metadata index from {METADATA_174K}")
    with open(METADATA_174K) as f:
        metadata = json.load(f)
    did_to_idx = {m['decision_id']: i for i, m in enumerate(metadata)}
    logger.info(f"Loaded {len(did_to_idx)} decision indices")
    return did_to_idx

def build_full_citation_graph():
    """Build citation graph from all year files using cited_decisions field."""
    citation_map = load_citation_map()
    did_to_idx = load_metadata_index()
    
    # Track statistics
    stats = {
        'total_decisions_processed': 0,
        'decisions_with_cited_field': 0,
        'total_citation_strings': 0,
        'resolved_citations': 0,
        'unresolved_citations': 0,
        'citations_to_corpus_decisions': 0,
        'citations_to_external': 0,
    }
    
    # Build graph: source_did -> list of target_dids
    citation_graph = defaultdict(list)
    
    for fname in YEAR_FILES:
        fpath = CANONICAL_DIR / fname
        if not fpath.exists():
            logger.warning(f"File not found: {fpath}")
            continue
        
        logger.info(f"Processing {fname}...")
        year_decisions = 0
        year_with_cited = 0
        
        with open(fpath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                
                source_did = d.get('decision_id', '')
                if not source_did:
                    continue
                
                year_decisions += 1
                stats['total_decisions_processed'] += 1
                
                cited_decisions = d.get('cited_decisions', [])
                if cited_decisions:
                    year_with_cited += 1
                    stats['decisions_with_cited_field'] += 1
                
                for cite_str in cited_decisions:
                    stats['total_citation_strings'] += 1
                    if cite_str in citation_map:
                        target_info = citation_map[cite_str]
                        target_did = target_info.get('target_decision_id')
                        if target_did:
                            stats['resolved_citations'] += 1
                            if target_did in did_to_idx:
                                stats['citations_to_corpus_decisions'] += 1
                                citation_graph[source_did].append(target_did)
                            else:
                                stats['citations_to_external'] += 1
                        else:
                            stats['unresolved_citations'] += 1
                    else:
                        stats['unresolved_citations'] += 1
        
        logger.info(f"  {fname}: {year_decisions} decisions, {year_with_cited} with cited_decisions")
    
    logger.info("\nCitation graph build complete:")
    for k, v in stats.items():
        if 'rate' not in k and 'pct' not in k:
            logger.info(f"  {k}: {v}")
    
    # Compute rates
    if stats['total_citation_strings'] > 0:
        resolution_rate = stats['resolved_citations'] / stats['total_citation_strings']
        corpus_rate = stats['citations_to_corpus_decisions'] / stats['total_citation_strings']
        logger.info(f"  resolution_rate: {resolution_rate:.3f}")
        logger.info(f"  citations_to_corpus_rate: {corpus_rate:.3f}")
    
    # Convert defaultdict to dict for JSON serialization
    citation_graph = dict(citation_graph)
    
    # Save citation graph
    graph_output = OUTPUT_DIR / "citation_graph_174k.json"
    with open(graph_output, 'w') as f:
        json.dump(citation_graph, f, indent=2)
    logger.info(f"Saved citation graph to {graph_output}")
    
    # Build reverse graph (incoming citations)
    incoming_graph = defaultdict(list)
    for source_did, targets in citation_graph.items():
        for target_did in targets:
            incoming_graph[target_did].append(source_did)
    
    incoming_output = OUTPUT_DIR / "citation_graph_174k_incoming.json"
    with open(incoming_output, 'w') as f:
        json.dump(dict(incoming_graph), f, indent=2)
    logger.info(f"Saved incoming citation graph to {incoming_output}")
    
    # Build citation pairs for benchmark
    logger.info("Building citation pairs for benchmark...")
    
    # Positive pairs: direct citations + shared citations
    positive_pairs = set()
    decision_citations = defaultdict(set)
    
    for source_did, targets in citation_graph.items():
        for target_did in targets:
            if source_did in did_to_idx and target_did in did_to_idx:
                positive_pairs.add((source_did, target_did))
                decision_citations[source_did].add(target_did)
    
    # Shared citations: decisions citing the same target
    cited_by = defaultdict(set)
    for source_did, targets in decision_citations.items():
        for target_did in targets:
            cited_by[target_did].add(source_did)
    
    for target_did, sources in cited_by.items():
        sources_list = list(sources)
        for i, s1 in enumerate(sources_list):
            for s2 in sources_list[i+1:]:
                positive_pairs.add((s1, s2))
                positive_pairs.add((s2, s1))
    
    logger.info(f"Positive pairs (direct + shared): {len(positive_pairs)}")
    
    # Negative pairs: random pairs with no citation relationship
    all_dids = list(did_to_idx.keys())
    import numpy as np
    np.random.seed(42)
    
    negative_pairs = set()
    max_attempts = len(positive_pairs) * 20
    attempts = 0
    
    while len(negative_pairs) < len(positive_pairs) and attempts < max_attempts:
        i, j = np.random.choice(len(all_dids), 2, replace=False)
        did1, did2 = all_dids[i], all_dids[j]
        
        # Check citation relationship
        has_relation = False
        if did1 in decision_citations and did2 in decision_citations[did1]:
            has_relation = True
        if did2 in decision_citations and did1 in decision_citations[did2]:
            has_relation = True
        if did1 in decision_citations and did2 in decision_citations:
            if decision_citations[did1] & decision_citations[did2]:
                has_relation = True
        
        if not has_relation:
            negative_pairs.add((did1, did2))
        
        attempts += 1
    
    logger.info(f"Negative pairs: {len(negative_pairs)} (attempts: {attempts})")
    
    # Save pairs
    pairs_data = {
        'positive_pairs': [list(p) for p in positive_pairs],
        'negative_pairs': [list(p) for p in negative_pairs],
        'stats': stats,
        'num_decisions_in_graph': len(citation_graph),
        'num_decisions_with_incoming': len(incoming_graph),
    }
    
    pairs_output = OUTPUT_DIR / "citation_pairs_174k_full.json"
    with open(pairs_output, 'w') as f:
        json.dump(pairs_data, f, indent=2)
    logger.info(f"Saved full citation pairs to {pairs_output}")
    
    return citation_graph, pairs_data, stats

def main():
    logger.info("=" * 70)
    logger.info("BUILD FULL 174K CITATION GRAPH FOR CITATION_HERITAGE BENCHMARK")
    logger.info("=" * 70)
    
    graph, pairs, stats = build_full_citation_graph()
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("174K CITATION GRAPH SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Decisions processed: {stats['total_decisions_processed']}")
    logger.info(f"Decisions with cited_decisions field: {stats['decisions_with_cited_field']} ({100*stats['decisions_with_cited_field']/stats['total_decisions_processed']:.1f}%)")
    logger.info(f"Total citation strings: {stats['total_citation_strings']}")
    logger.info(f"Resolved citations: {stats['resolved_citations']} ({100*stats['resolved_citations']/stats['total_citation_strings']:.1f}%)")
    logger.info(f"Citations to corpus decisions: {stats['citations_to_corpus_decisions']} ({100*stats['citations_to_corpus_decisions']/stats['total_citation_strings']:.1f}%)")
    logger.info(f"Decisions with outgoing citations in graph: {len(graph)}")
    logger.info(f"Decisions with incoming citations: {pairs['num_decisions_with_incoming']}")
    logger.info(f"Positive pairs for benchmark: {len(pairs['positive_pairs'])}")
    logger.info(f"Negative pairs for benchmark: {len(pairs['negative_pairs'])}")
    logger.info("=" * 70)

if __name__ == "__main__":
    main()
