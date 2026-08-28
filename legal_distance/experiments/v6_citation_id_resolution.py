#!/usr/bin/env python3
"""
Legal Distance Lane v6 - Citation ID Resolution Pipeline

Maps BGE/ATF citation references to decision_ids for graph connectivity.
This enables the 2,988 role annotations to be used in citation graphs.

Citation formats in corpus:
1. Court decisions: "7B_189/2023", "1B_163/2022", "5A_766/2024" -> decision_id: "bger_7B_189_2023"
2. BGE/ATF: "BGE 147 IV 73", "BGE 136 III 605" -> published volumes (may not be in 2000+ corpus)
3. Other: "IV.2022.00405", "ST.2019.30", "VB.2024.00510" -> various formats

Strategy:
- Build exact mapping for court decision citations (chamber_number/year -> bger_chamber_number_year)
- For BGE citations, attempt to match via volume/page if those decisions are in corpus
- For other formats, best-effort matching
- Output: citation_to_decision_id.json mapping + statistics
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict, Counter
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
CORPUS_FILE = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/bger_full_corpus.jsonl")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v6/citation_id_resolution")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Citation parsing patterns
# Court decision pattern: e.g., "7B_189/2023", "1B_163/2022", "5A_766/2024"
COURT_DECISION_PATTERN = re.compile(r'^([0-9]+[A-Z][A-Z]?)_(\d+)/(\d{4})$')

# BGE pattern: "BGE {volume} {book} {page}"
BGE_PATTERN = re.compile(r'^BGE\s+(\d+)\s+([IVX]+)\s+(\d+)$')

# Other patterns
OTHER_PATTERNS = [
    re.compile(r'^([IVX]+)\.(\d{4})\.(\d{5,})$'),  # IV.2022.00405
    re.compile(r'^([A-Z]{2})\.(\d{4})\.(\d+)$'),    # ST.2019.30, VB.2024.00510
    re.compile(r'^([A-Z]{2})\.(\d{4})\.(\d+)$'),    # CR.2024.0049
    re.compile(r'^([A-Z]{1,2})\-(\d+)/(\d{4})$'),   # A-3375/2023
    re.compile(r'^([0-9]+[A-Z])\.(\d+)/(\d{4})$'),  # 2A.478/2005
]

def load_corpus() -> Tuple[Dict[str, Dict], Dict[str, str]]:
    """Load corpus and build decision_id lookup."""
    corpus = {}
    decision_id_set = set()
    
    with open(CORPUS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            d = json.loads(line)
            decision_id = d['decision_id']
            corpus[decision_id] = d
            decision_id_set.add(decision_id)
    
    logger.info(f"Loaded {len(corpus)} decisions from corpus")
    return corpus, decision_id_set


def build_court_decision_mapping(decision_ids: Set[str]) -> Dict[str, str]:
    """
    Build mapping from citation format to decision_id for court decisions.
    
    Citation: "7B_189/2023" -> decision_id: "bger_7B_189_2023"
    """
    mapping = {}
    
    for did in decision_ids:
        # decision_id format: bger_{chamber}_{number}_{year}
        # e.g., bger_7B_832_2024
        match = re.match(r'^bger_([0-9]+[A-Z][A-Z]?)_(\d+)_(\d{4})$', did)
        if match:
            chamber, number, year = match.groups()
            citation = f"{chamber}_{number}/{year}"
            mapping[citation] = did
    
    logger.info(f"Built court decision mapping: {len(mapping)} entries")
    return mapping


def parse_citation(citation: str) -> Optional[Tuple[str, Dict]]:
    """
    Parse a citation string and return (type, parsed_components).
    Returns None if unparseable.
    """
    citation = citation.strip()
    
    # Court decision: 7B_189/2023
    m = COURT_DECISION_PATTERN.match(citation)
    if m:
        chamber, number, year = m.groups()
        return ('court_decision', {'chamber': chamber, 'number': number, 'year': year})
    
    # BGE: BGE 147 IV 73
    m = BGE_PATTERN.match(citation)
    if m:
        volume, book, page = m.groups()
        return ('bge', {'volume': int(volume), 'book': book, 'page': int(page)})
    
    # Other patterns
    for pattern in OTHER_PATTERNS:
        m = pattern.match(citation)
        if m:
            return ('other', {'raw': citation, 'groups': m.groups()})
    
    # Unknown format
    return ('unknown', {'raw': citation})


def build_bge_mapping(corpus: Dict[str, Dict]) -> Dict[str, str]:
    """
    Build mapping for BGE citations.
    Since BGE citations refer to published volumes (often pre-2000),
    we can only map them if the same decision appears in our corpus.
    We'd need the BGE reference in the decision metadata, which we don't have.
    For now, return empty mapping - BGE resolution requires external data.
    """
    # The corpus doesn't contain BGE references in a structured way
    # We would need to parse the full_text for "BGE {vol} {book} {page}" patterns
    # and match to decisions. This is complex and low-yield for 2000+ corpus.
    logger.info("BGE mapping: Not implemented (requires full-text parsing + external BGE index)")
    return {}


def resolve_all_citations(corpus: Dict[str, Dict], decision_ids: Set[str]) -> Dict:
    """
    Resolve all citations in the corpus to decision_ids.
    """
    court_mapping = build_court_decision_mapping(decision_ids)
    bge_mapping = build_bge_mapping(corpus)
    
    # Statistics
    stats = {
        'total_citations': 0,
        'resolved_court': 0,
        'resolved_bge': 0,
        'unresolved': 0,
        'by_type': Counter(),
        'unresolved_examples': [],
    }
    
    # Collect all unique citations
    all_citations = set()
    citation_sources = defaultdict(list)  # citation -> list of (source_decision_id, role_info)
    
    for did, decision in corpus.items():
        for cit in decision.get('cited_decisions', []):
            all_citations.add(cit)
            citation_sources[cit].append({'source': did})
    
    logger.info(f"Total unique citations in corpus: {len(all_citations)}")
    
    # Resolve each citation
    resolved_mapping = {}
    unresolved = []
    
    for cit in all_citations:
        stats['total_citations'] += 1
        parsed = parse_citation(cit)
        
        if not parsed:
            stats['unresolved'] += 1
            stats['by_type']['unparseable'] += 1
            unresolved.append(cit)
            continue
        
        cit_type, components = parsed
        stats['by_type'][cit_type] += 1
        
        if cit_type == 'court_decision':
            if cit in court_mapping:
                resolved_mapping[cit] = court_mapping[cit]
                stats['resolved_court'] += 1
            else:
                stats['unresolved'] += 1
                unresolved.append(cit)
        
        elif cit_type == 'bge':
            if cit in bge_mapping:
                resolved_mapping[cit] = bge_mapping[cit]
                stats['resolved_bge'] += 1
            else:
                stats['unresolved'] += 1
                unresolved.append(cit)
        
        else:
            stats['unresolved'] += 1
            unresolved.append(cit)
    
    logger.info(f"Resolution stats: {stats['resolved_court']} court, {stats['resolved_bge']} BGE, {stats['unresolved']} unresolved")
    
    # Add source information to mapping
    enriched_mapping = {}
    for cit, target_did in resolved_mapping.items():
        enriched_mapping[cit] = {
            'target_decision_id': target_did,
            'sources': citation_sources[cit],
            'citation_type': 'court_decision'
        }
    
    return {
        'resolved_mapping': enriched_mapping,
        'unresolved_citations': unresolved[:100],  # Sample
        'stats': stats,
        'court_mapping_raw': court_mapping,
    }


def create_role_graph_edges(citation_roles_file: Path, resolved_mapping: Dict) -> Dict:
    """
    Use the resolved citation mapping to create role-weighted graph edges
    from the citation role annotations.
    """
    if not citation_roles_file.exists():
        logger.warning(f"Citation roles file not found: {citation_roles_file}")
        return {}
    
    with open(citation_roles_file, 'r') as f:
        roles_data = json.load(f)
    
    # The roles data contains role annotations for 200 decisions
    # We need to map the cited references to decision_ids
    logger.info("Processing citation roles for graph edge creation...")
    
    # This would be expanded based on the actual roles data structure
    # For now, return the structure for future use
    return {
        'note': 'Citation role graph edges require the roles data structure to be parsed',
        'resolved_citations_available': len(resolved_mapping)
    }


def main():
    logger.info("=" * 70)
    logger.info("Legal Distance Lane v6 - Citation ID Resolution Pipeline")
    logger.info("=" * 70)
    
    # 1. Load corpus
    logger.info("\n1. Loading corpus...")
    corpus, decision_ids = load_corpus()
    
    # 2. Resolve all citations
    logger.info("\n2. Resolving citations...")
    results = resolve_all_citations(corpus, decision_ids)
    
    # 3. Save results
    logger.info("\n3. Saving results...")
    
    # Main mapping file
    with open(OUTPUT_DIR / "citation_to_decision_id.json", 'w') as f:
        json.dump(results['resolved_mapping'], f, indent=2, ensure_ascii=False)
    
    # Statistics
    with open(OUTPUT_DIR / "resolution_stats.json", 'w') as f:
        json.dump(results['stats'], f, indent=2)
    
    # Unresolved sample
    with open(OUTPUT_DIR / "unresolved_citations.json", 'w') as f:
        json.dump(results['unresolved_citations'], f, indent=2)
    
    # Raw court mapping for reference
    with open(OUTPUT_DIR / "court_citation_mapping.json", 'w') as f:
        json.dump(results['court_mapping_raw'], f, indent=2)
    
    # 4. Process citation roles if available
    roles_file = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/citation_roles/citation_roles_sample.json")
    role_graph = create_role_graph_edges(roles_file, results['resolved_mapping'])
    
    with open(OUTPUT_DIR / "role_graph_edges.json", 'w') as f:
        json.dump(role_graph, f, indent=2)
    
    # 5. Summary
    logger.info("\n" + "=" * 70)
    logger.info("CITATION ID RESOLUTION SUMMARY")
    logger.info("=" * 70)
    stats = results['stats']
    logger.info(f"Total unique citations: {stats['total_citations']}")
    logger.info(f"Resolved (court decisions): {stats['resolved_court']}")
    logger.info(f"Resolved (BGE): {stats['resolved_bge']}")
    logger.info(f"Unresolved: {stats['unresolved']}")
    logger.info(f"Resolution rate: {stats['resolved_court'] / stats['total_citations'] * 100:.1f}%")
    logger.info(f"\nBy type:")
    for cit_type, count in stats['by_type'].most_common():
        logger.info(f"  {cit_type}: {count}")
    
    logger.info(f"\nOutput files in {OUTPUT_DIR}:")
    logger.info(f"  - citation_to_decision_id.json (resolved mappings with sources)")
    logger.info(f"  - resolution_stats.json")
    logger.info(f"  - unresolved_citations.json")
    logger.info(f"  - court_citation_mapping.json")
    logger.info(f"  - role_graph_edges.json")
    
    return results


if __name__ == "__main__":
    main()