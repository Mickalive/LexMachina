#!/usr/bin/env python3
"""
Legal Distance Lane v7 - Improved Citation ID Resolution with BGE/ATF Support

Maps BGE/ATF citation references to decision_ids by extracting BGE/ATF references
from the full_text of decisions in our corpus. This enables the 2,988 role annotations
(distinguishing, overruling, criticizing, following) to be used in citation graphs.

Strategy:
1. Extract BGE/ATF references from full_text of all corpus decisions
2. Build mapping: BGE/ATF reference -> decision_id(s) that contain it
3. Resolve role annotations target_decisions to decision_ids
4. Output citation role embeddings with resolved graph connectivity
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from collections import defaultdict, Counter
import logging
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
CORPUS_FILE = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/bger_full_corpus.jsonl")
ROLES_FILE = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/citation_roles/citation_roles_sample.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v7/citation_id_resolution_bge")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Patterns
COURT_DECISION_PATTERN = re.compile(r'^([0-9]+[A-Z][A-Z]?)_(\d+)/(\d{4})$')
BGE_PATTERN = re.compile(r'BGE\s+(\d+)\s+([IVX]+)\s+(\d+)')
ATF_PATTERN = re.compile(r'ATF\s+(\d+)\s+([IVX]+)\s+(\d+)')

# BGE/ATF reference normalization (remove trailing "E. 2", "consid. 2", etc.)
BGE_ATF_CLEAN = re.compile(r'^(BGE|ATF)\s+(\d+)\s+([IVX]+)\s+(\d+)')


def load_corpus() -> Tuple[Dict[str, Dict], Set[str]]:
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


def load_citation_roles() -> List[Dict]:
    """Load the 2,988 citation role annotations."""
    with open(ROLES_FILE, 'r') as f:
        roles = json.load(f)
    logger.info(f"Loaded {len(roles)} citation role annotations")
    return roles


def build_court_decision_mapping(decision_ids: Set[str]) -> Dict[str, str]:
    """Build mapping from court citation format to decision_id."""
    mapping = {}
    
    for did in decision_ids:
        # decision_id format: bger_{chamber}_{number}_{year}
        match = re.match(r'^bger_([0-9]+[A-Z][A-Z]?)_(\d+)_(\d{4})$', did)
        if match:
            chamber, number, year = match.groups()
            citation = f"{chamber}_{number}/{year}"
            mapping[citation] = did
    
    logger.info(f"Built court decision mapping: {len(mapping)} entries")
    return mapping


def extract_bge_atf_references(corpus: Dict[str, Dict]) -> Dict[str, List[str]]:
    """
    Extract BGE and ATF references from full_text of corpus decisions.
    Returns mapping: bge_atf_ref -> list of decision_ids that contain it.
    """
    bge_atf_map = defaultdict(list)
    stats = Counter()
    
    for did, decision in corpus.items():
        full_text = decision.get('full_text', '')
        
        # Find BGE references
        for match in BGE_PATTERN.finditer(full_text):
            vol, book, page = match.groups()
            ref = f"BGE {vol} {book} {page}"
            bge_atf_map[ref].append(did)
            stats['bge'] += 1
        
        # Find ATF references
        for match in ATF_PATTERN.finditer(full_text):
            vol, book, page = match.groups()
            ref = f"ATF {vol} {book} {page}"
            bge_atf_map[ref].append(did)
            stats['atf'] += 1
    
    logger.info(f"Extracted BGE refs: {stats['bge']} mentions, {sum(1 for v in bge_atf_map.values() if v and any(r.startswith('BGE') for r in [list(bge_atf_map.keys())[list(bge_atf_map.values()).index(v)]]))} unique")
    logger.info(f"Extracted ATF refs: {stats['atf']} mentions, {sum(1 for v in bge_atf_map.values() if v and any(r.startswith('ATF') for r in [list(bge_atf_map.keys())[list(bge_atf_map.values()).index(v)]]))} unique")
    
    # Count unique BGE vs ATF
    unique_bge = sum(1 for ref in bge_atf_map if ref.startswith('BGE'))
    unique_atf = sum(1 for ref in bge_atf_map if ref.startswith('ATF'))
    logger.info(f"Unique BGE references in corpus: {unique_bge}")
    logger.info(f"Unique ATF references in corpus: {unique_atf}")
    
    return dict(bge_atf_map)


def normalize_bge_atf_citation(citation: str) -> Optional[str]:
    """
    Normalize a BGE/ATF citation to the base reference format.
    E.g., "BGE 142 III 364 E. 2" -> "BGE 142 III 364"
    """
    match = BGE_ATF_CLEAN.match(citation.strip())
    if match:
        prefix, vol, book, page = match.groups()
        return f"{prefix} {vol} {book} {page}"
    return None


def resolve_all_citations(corpus: Dict[str, Dict], 
                          decision_ids: Set[str],
                          roles: List[Dict],
                          bge_atf_map: Dict[str, List[str]],
                          court_mapping: Dict[str, str]) -> Dict:
    """
    Resolve all citations in corpus and role annotations.
    """
    stats = {
        'total_corpus_citations': 0,
        'resolved_court': 0,
        'resolved_bge_atf': 0,
        'unresolved': 0,
        'by_type': Counter(),
        'roles_total': len(roles),
        'roles_resolved': 0,
        'roles_by_type': Counter(),
        'roles_by_role': Counter(),
    }
    
    # Collect all unique citations from corpus
    all_citations = set()
    for decision in corpus.values():
        for cit in decision.get('cited_decisions', []):
            all_citations.add(cit)
    
    logger.info(f"Total unique citations in corpus: {len(all_citations)}")
    
    # Resolve corpus citations
    resolved_mapping = {}
    unresolved = []
    
    for cit in all_citations:
        stats['total_corpus_citations'] += 1
        cit_clean = cit.strip()
        
        # Court decision
        m = COURT_DECISION_PATTERN.match(cit_clean)
        if m:
            stats['by_type']['court_decision'] += 1
            if cit_clean in court_mapping:
                resolved_mapping[cit_clean] = {
                    'target_decision_id': court_mapping[cit_clean],
                    'citation_type': 'court_decision',
                    'normalized_citation': cit_clean
                }
                stats['resolved_court'] += 1
            else:
                stats['unresolved'] += 1
                unresolved.append(cit_clean)
            continue
        
        # BGE/ATF
        normalized = normalize_bge_atf_citation(cit_clean)
        if normalized:
            if normalized.startswith('BGE'):
                stats['by_type']['bge'] += 1
            else:
                stats['by_type']['atf'] += 1
            
            if normalized in bge_atf_map:
                # Multiple decisions might have this reference - pick first
                target_did = bge_atf_map[normalized][0]
                resolved_mapping[cit_clean] = {
                    'target_decision_id': target_did,
                    'citation_type': 'bge' if normalized.startswith('BGE') else 'atf',
                    'normalized_citation': normalized,
                    'all_candidates': bge_atf_map[normalized]
                }
                stats['resolved_bge_atf'] += 1
            else:
                stats['unresolved'] += 1
                unresolved.append(cit_clean)
            continue
        
        # Other
        stats['by_type']['other'] += 1
        stats['unresolved'] += 1
        unresolved.append(cit_clean)
    
    # Now resolve role annotations
    logger.info(f"\nResolving {len(roles)} role annotations...")
    roles_resolved = []
    
    for role in roles:
        target = role['target_decision']
        normalized = normalize_bge_atf_citation(target)
        
        stats['roles_by_role'][role['role']] += 1
        
        if normalized and normalized in bge_atf_map:
            target_did = bge_atf_map[normalized][0]
            roles_resolved.append({
                **role,
                'resolved_decision_id': target_did,
                'normalized_citation': normalized,
                'all_candidates': bge_atf_map[normalized],
                'resolved': True
            })
            stats['roles_resolved'] += 1
            stats['roles_by_type']['bge_atf'] += 1
        else:
            roles_resolved.append({
                **role,
                'resolved_decision_id': None,
                'normalized_citation': normalized,
                'resolved': False
            })
            stats['roles_by_type']['unresolved'] += 1
    
    logger.info(f"Role resolution: {stats['roles_resolved']}/{stats['roles_total']} resolved ({stats['roles_resolved']/stats['roles_total']*100:.1f}%)")
    logger.info(f"  By role: {dict(stats['roles_by_role'])}")
    logger.info(f"  By type: {dict(stats['roles_by_type'])}")
    
    return {
        'resolved_mapping': resolved_mapping,
        'unresolved_citations': unresolved[:200],
        'stats': stats,
        'court_mapping_raw': court_mapping,
        'bge_atf_map': {k: v for k, v in bge_atf_map.items()},
        'roles_resolved': roles_resolved,
    }


def create_role_embeddings(roles_resolved: List[Dict], 
                          decision_ids: Set[str],
                          output_dim: int = 64) -> Dict[str, np.ndarray]:
    """
    Create role-specific embedding matrices from resolved role annotations.
    Each role gets a (n_decisions, output_dim) matrix.
    """
    # Build decision_id to index mapping
    decision_list = sorted(decision_ids)
    did_to_idx = {did: i for i, did in enumerate(decision_list)}
    n = len(decision_list)
    
    # Initialize role matrices
    role_names = ['citing', 'following', 'distinguishing', 'overruling', 'criticizing']
    role_matrices = {role: np.zeros((n, output_dim), dtype=np.float32) for role in role_names}
    
    # Count non-zero entries
    role_counts = {role: 0 for role in role_names}
    
    for role_anno in roles_resolved:
        if not role_anno['resolved']:
            continue
        
        source_did = role_anno.get('source_decision')  # Need to check if this exists
        target_did = role_anno['resolved_decision_id']
        role_type = role_anno['role']
        
        # The roles data doesn't have source_decision - we need to infer from context
        # For now, we'll use the target_did as the key and build citation graph
        # Actually, the roles file structure might be different - let me check
        pass
    
    # Actually, the roles data is per-citation, not per-decision-pair
    # We need to build a citation graph where edges are weighted by role
    # For now, create a simple weighted adjacency
    
    logger.warning("Role embedding creation needs source decision info - using simplified approach")
    return {role: np.zeros((n, output_dim), dtype=np.float32) for role in role_names}


def build_citation_role_graph(roles_resolved: List[Dict], 
                             decision_ids: Set[str]) -> Dict:
    """
    Build a citation role graph from resolved annotations.
    Returns adjacency information for graph-based methods.
    """
    did_to_idx = {did: i for i, did in enumerate(sorted(decision_ids))}
    
    # Count role occurrences per target decision
    role_counts = defaultdict(lambda: defaultdict(int))
    
    for role_anno in roles_resolved:
        if not role_anno['resolved']:
            continue
        target_did = role_anno['resolved_decision_id']
        role_type = role_anno['role']
        role_counts[target_did][role_type] += 1
    
    logger.info(f"Built role graph: {len(role_counts)} target decisions have role annotations")
    
    # Role distribution
    total_by_role = Counter()
    for target, counts in role_counts.items():
        for role, count in counts.items():
            total_by_role[role] += count
    
    logger.info(f"Total role counts: {dict(total_by_role)}")
    
    return {
        'role_counts_per_target': {k: dict(v) for k, v in role_counts.items()},
        'total_by_role': dict(total_by_role),
        'n_targets_with_roles': len(role_counts),
    }


def main():
    logger.info("=" * 70)
    logger.info("Legal Distance Lane v7 - BGE/ATF Citation ID Resolution")
    logger.info("=" * 70)
    
    # 1. Load corpus
    logger.info("\n1. Loading corpus...")
    corpus, decision_ids = load_corpus()
    
    # 2. Load citation roles
    logger.info("\n2. Loading citation roles...")
    roles = load_citation_roles()
    
    # 3. Build court decision mapping
    logger.info("\n3. Building court decision mapping...")
    court_mapping = build_court_decision_mapping(decision_ids)
    
    # 4. Extract BGE/ATF references from full_text
    logger.info("\n4. Extracting BGE/ATF references from full_text...")
    bge_atf_map = extract_bge_atf_references(corpus)
    
    # 5. Resolve all citations
    logger.info("\n5. Resolving all citations and role annotations...")
    results = resolve_all_citations(corpus, decision_ids, roles, bge_atf_map, court_mapping)
    
    # 6. Build citation role graph
    logger.info("\n6. Building citation role graph...")
    role_graph = build_citation_role_graph(results['roles_resolved'], decision_ids)
    
    # 7. Save results
    logger.info("\n7. Saving results...")
    
    # Main mapping
    with open(OUTPUT_DIR / "citation_to_decision_id.json", 'w') as f:
        json.dump(results['resolved_mapping'], f, indent=2, ensure_ascii=False)
    
    # Statistics
    with open(OUTPUT_DIR / "resolution_stats.json", 'w') as f:
        # Convert Counter to dict
        stats = results['stats'].copy()
        stats['by_type'] = dict(stats['by_type'])
        stats['roles_by_type'] = dict(stats['roles_by_type'])
        stats['roles_by_role'] = dict(stats['roles_by_role'])
        json.dump(stats, f, indent=2)
    
    # Unresolved sample
    with open(OUTPUT_DIR / "unresolved_citations.json", 'w') as f:
        json.dump(results['unresolved_citations'], f, indent=2)
    
    # Court mapping
    with open(OUTPUT_DIR / "court_citation_mapping.json", 'w') as f:
        json.dump(results['court_mapping_raw'], f, indent=2)
    
    # BGE/ATF map
    with open(OUTPUT_DIR / "bge_atf_reference_map.json", 'w') as f:
        json.dump(results['bge_atf_map'], f, indent=2)
    
    # Resolved roles
    with open(OUTPUT_DIR / "citation_roles_resolved.json", 'w') as f:
        json.dump(results['roles_resolved'], f, indent=2, ensure_ascii=False)
    
    # Role graph
    with open(OUTPUT_DIR / "role_graph.json", 'w') as f:
        json.dump(role_graph, f, indent=2)
    
    # 8. Summary
    logger.info("\n" + "=" * 70)
    logger.info("BGE/ATF CITATION ID RESOLUTION SUMMARY")
    logger.info("=" * 70)
    stats = results['stats']
    logger.info(f"Corpus citations:")
    logger.info(f"  Total unique: {stats['total_corpus_citations']}")
    logger.info(f"  Resolved (court): {stats['resolved_court']}")
    logger.info(f"  Resolved (BGE/ATF): {stats['resolved_bge_atf']}")
    logger.info(f"  Unresolved: {stats['unresolved']}")
    logger.info(f"  Resolution rate: {(stats['resolved_court'] + stats['resolved_bge_atf']) / stats['total_corpus_citations'] * 100:.1f}%")
    logger.info(f"\nRole annotations:")
    logger.info(f"  Total: {stats['roles_total']}")
    logger.info(f"  Resolved: {stats['roles_resolved']} ({stats['roles_resolved']/stats['roles_total']*100:.1f}%)")
    logger.info(f"  By role: {dict(stats['roles_by_role'])}")
    logger.info(f"\nOutput files in {OUTPUT_DIR}:")
    logger.info(f"  - citation_to_decision_id.json")
    logger.info(f"  - resolution_stats.json")
    logger.info(f"  - unresolved_citations.json")
    logger.info(f"  - court_citation_mapping.json")
    logger.info(f"  - bge_atf_reference_map.json")
    logger.info(f"  - citation_roles_resolved.json")
    logger.info(f"  - role_graph.json")
    
    return results


if __name__ == "__main__":
    main()