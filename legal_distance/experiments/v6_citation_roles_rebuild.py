#!/usr/bin/env python3
"""
Legal Distance Lane v6 - Rebuild Citation Role Embeddings with Court Decision Citations

Factory Direction v6 Objective 4: "Citation role modeling: integrate 2,988 role annotations 
once citation ID resolution pipeline ready"

FIX: The v5 extraction only matched BGE/ATF patterns. Court decision citations 
(e.g., "7B_189/2023") were in context but not extracted as targets.

This experiment:
1. Re-runs role extraction with BOTH BGE/ATF AND court decision patterns
2. Uses v6 citation_to_decision_id.json to resolve court decision targets
3. Builds role-specific embeddings with actual connectivity
4. Evaluates on adversarial benchmarks and fractal-map harness
"""

import json
import re
import numpy as np
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import Counter, defaultdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

SIGNALS_FILE = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/legal_signals_full.jsonl")
CITATION_ID_MAP = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v6/citation_id_resolution/citation_to_decision_id.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v6/citation_roles_rebuilt")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Trilingual citation role patterns (same as v5)
CITATION_ROLE_PATTERNS = {
    'de': {
        'following': ['bestätigt', 'folgt', 'wendet an', 'trifft zu', 'ist anwendbar',
            'stimmt zu', 'übernimmt', 'bejaht', 'bestätigend', 'zutreffend',
            'in Sinne von', 'gemäß', 'entsprechend', 'analog',],
        'distinguishing': ['unterscheidet', 'abgrenzt', 'nicht anwendbar', 'nicht zutreffend',
            'anders gelagert', 'anderer Fall', 'kann nicht herangezogen',
            'nicht vergleichbar', 'besondere Umstände', 'ausnahmsweise',
            'beschränkt auf', 'eingeschränkt',],
        'overruling': ['aufgegeben', 'überholt', 'nicht mehr haltbar', 'revidiert',
            'ändert Rechtsprechung', 'gibt auf', 'verlässt', 'korrigiert',
            'nicht mehr zutreffend', 'überwunden', 'abandonniert',],
        'criticizing': ['kritisiert', 'beanstandet', 'zweifelt an', 'fragwürdig',
            'bedenklich', 'problematisch', 'nicht überzeugend',],
    },
    'fr': {
        'following': ['confirme', 'suit', 'applique', 'est applicable', "est d'accord",
            'reprend', 'approuve', 'conforme', 'selon', 'selon la jurisprudence',
            'dans le sens de', 'conformément', 'analogiquement',],
        'distinguishing': ['distingue', 'différencie', 'non applicable', 'non pertinent',
            'espèce différente', 'autre cas', 'ne peut être invoqué',
            'non comparable', 'circonstances particulières', 'exceptionnellement',
            'limité à', 'restreint',],
        'overruling': ['abandonne', 'revient sur', 'non plus tenable', 'révise',
            'change la jurisprudence', 'renonce', 'quitte', 'corrige',
            'non plus pertinent', 'surmonté',],
        'criticizing': ['critique', 'conteste', 'met en doute', 'questionnable',
            'préoccupant', 'problématique', 'non convaincant',],
    },
    'it': {
        'following': ['conferma', 'segue', 'applica', 'è applicabile', "è d'accordo",
            'riprende', 'approva', 'conforme', 'secondo', 'secondo la giurisprudenza',
            "nell'ambito di", 'conformemente', 'analogicamente',],
        'distinguishing': ['distingue', 'differenzia', 'non applicabile', 'non pertinente',
            'fattispecie diversa', 'altro caso', 'non può essere invocato',
            'non comparabile', 'circostanze particolari', 'eccezionalmente',
            'limitato a', 'ristretto',],
        'overruling': ['abbandona', 'torna su', 'non più tenibile', 'rivisita',
            'cambia la giurisprudenza', 'rinuncia', 'lascia', 'corregge',
            'non più pertinente', 'superato',],
        'criticizing': ['critica', 'contesta', 'mette in dubbio', 'questionabile',
            'preoccupante', 'problematico', 'non convincente',],
    },
}

CONTEXT_WINDOW = 200

# Citation patterns: BGE/ATF + Court decisions
CITATION_PATTERNS = [
    # BGE/ATF
    r'(?:BGE|ATF)\s+\d+\s+[IVX]+\s+\d+(?:\s+consid\.\s*\d+)?(?:\s+E\.\s*\d+)?',
    r'(?:BGE|ATF)\s+\d+\s+[IVX]+\s+\d+',
    # Court decisions: 7B_189/2023, 1B_407/2022, 5A_129/2019, etc.
    r'\b([0-9][A-Z]_[0-9]{1,5}/[0-9]{4})\b',
    # With "arrêt" / "Urteil" / "sentenza" prefix
    r'(?:arr.t|Urteil|sentenza)\s+([0-9][A-Z]_[0-9]{1,5}/[0-9]{4})',
]

@dataclass
class CitationRole:
    target_decision: str
    target_normalized: str  # Normalized for matching (e.g., "7B_189/2023")
    role: str
    confidence: float
    context_snippet: str
    language: str
    paragraph_idx: int
    citation_type: str  # 'bge' or 'court'

@dataclass
class CitationRolesResult:
    decision_id: str
    roles: List[CitationRole]
    role_counts: Dict[str, int]

def load_signals() -> Dict[str, Any]:
    signals = {}
    with open(SIGNALS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            signals[data['decision_id']] = data
    logger.info(f"Loaded signals for {len(signals)} decisions")
    return signals

def load_citation_id_map() -> Dict[str, str]:
    """Load citation -> decision_id mapping."""
    with open(CITATION_ID_MAP, 'r') as f:
        data = json.load(f)
    # Flatten to citation_key -> target_decision_id
    mapping = {}
    for citation_key, info in data.items():
        mapping[citation_key] = info['target_decision_id']
    logger.info(f"Loaded citation ID map: {len(mapping)} resolved citations")
    return mapping

def extract_paragraphs(text: str, language: str) -> List[str]:
    """Extract paragraphs from Erwägungen section."""
    if not text:
        return []
    
    patterns = {
        'de': r'(?:In\s+Erwägung\s*:|Erwägungen\s*:|Erwägung\s*:)\s*\n',
        'fr': r'(?:Considérant\s+en\s+droit\s*:|Considérant\s*:|Sur\s+ce\s*:)\s*\n',
        'it': r'(?:Considerando\s+in\s+diritto\s*:|Considerando\s*:)\s*\n',
    }
    
    pattern = patterns.get(language, patterns['de'])
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return [p.strip() for p in text.split('\n\n') if p.strip()]
    
    start = match.end()
    erwaeg_text = text[start:]
    
    end_patterns = [
        r'\n\s*(?:Dispositiv|Erkenntnis|Ausgang|Dispositif|Dispositivo)\s*:',
        r'\n\s*(?:Bundesgericht|Tribunal\s+fédéral|Tribunale\s+federale)\s*\n',
    ]
    end = len(erwaeg_text)
    for ep in end_patterns:
        m = re.search(ep, erwaeg_text, re.IGNORECASE)
        if m:
            end = min(end, m.start())
    
    erwaeg_text = erwaeg_text[:end].strip()
    
    paragraphs = re.split(r'\n\s*\d+(?:\.\d+)*\.\s*', erwaeg_text)
    paragraphs = [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 20]
    return paragraphs

def find_citation_targets(paragraph: str) -> List[Tuple[str, int, str]]:
    """
    Find cited decision references in a paragraph. 
    Returns (target, position, citation_type) where type is 'bge' or 'court'.
    """
    targets = []
    
    for pattern in CITATION_PATTERNS:
        for match in re.finditer(pattern, paragraph, re.IGNORECASE):
            full_match = match.group().strip()
            # Determine citation type
            if match.group().startswith(('BGE', 'ATF')):
                citation_type = 'bge'
                target = full_match
            else:
                citation_type = 'court'
                # For court decisions, group 1 captures the citation if using prefix pattern
                # Otherwise the full match is the citation
                target = match.group(1) if match.lastindex and match.group(1) else full_match
            
            targets.append((target, match.start(), citation_type))
    
    return targets

def classify_citation_role(paragraph: str, target: str, pos: int, language: str) -> Tuple[str, float]:
    """Classify the role of a citation based on surrounding context."""
    start = max(0, pos - CONTEXT_WINDOW)
    end = min(len(paragraph), pos + len(target) + CONTEXT_WINDOW)
    context = paragraph[start:end].lower()
    
    patterns = CITATION_ROLE_PATTERNS.get(language, CITATION_ROLE_PATTERNS['de'])
    
    scores = defaultdict(float)
    
    for role, role_patterns in patterns.items():
        for rp in role_patterns:
            if re.search(re.escape(rp), context, re.IGNORECASE):
                scores[role] += 1.0
    
    if not scores:
        return 'citing', 0.5
    
    best_role = max(scores.items(), key=lambda x: x[1])
    confidence = min(best_role[1] / 3.0, 1.0)
    return best_role[0], confidence

def extract_citation_roles(decision_id: str, signals: Dict[str, Any], citation_id_map: Dict[str, str]) -> CitationRolesResult:
    """Extract citation roles for a single decision (BGE/ATF + court decisions)."""
    sig = signals.get(decision_id, {})
    full_text = sig.get('full_text', '')
    language = sig.get('language', 'de')
    
    paragraphs = extract_paragraphs(full_text, language)
    
    roles = []
    for para_idx, para in enumerate(paragraphs):
        targets = find_citation_targets(para)
        for target, pos, cit_type in targets:
            role, confidence = classify_citation_role(para, target, pos, language)
            target_clean = re.sub(r'\s+', ' ', target).strip()
            
            # Normalize target for matching
            if cit_type == 'court':
                target_normalized = target_clean
            else:
                # For BGE/ATF, normalize format
                target_normalized = target_clean
            
            roles.append(CitationRole(
                target_decision=target_clean,
                target_normalized=target_normalized,
                role=role,
                confidence=confidence,
                context_snippet=para[max(0, pos-100):pos+len(target)+100],
                language=language,
                paragraph_idx=para_idx,
                citation_type=cit_type,
            ))
    
    role_counts = Counter(r.role for r in roles)
    
    return CitationRolesResult(
        decision_id=decision_id,
        roles=roles,
        role_counts=dict(role_counts),
    )

def build_citation_role_matrix(
    signals: Dict[str, Any], 
    metadata: List[Dict],
    citation_id_map: Dict[str, str],
    role_filter: Optional[str] = None
) -> np.ndarray:
    """Build citation role-weighted adjacency matrix using resolved IDs."""
    n = len(metadata)
    id_to_idx = {m['decision_id']: i for i, m in enumerate(metadata)}
    
    role_weights = {
        'following': 1.5,
        'distinguishing': 1.0,
        'overruling': 2.0,
        'criticizing': 0.5,
        'citing': 0.8,
    }
    
    if role_filter:
        role_weights = {role_filter: 1.0}
    
    rows, cols, weights = [], [], []
    stats = {'total': 0, 'bge': 0, 'court': 0, 'resolved_bge': 0, 'resolved_court': 0, 'unresolved': 0}
    
    for i, m in enumerate(metadata):
        did = m['decision_id']
        result = extract_citation_roles(did, signals, citation_id_map)
        
        for role_obj in result.roles:
            if role_filter and role_obj.role != role_filter:
                continue
            
            stats['total'] += 1
            if role_obj.citation_type == 'bge':
                stats['bge'] += 1
            else:
                stats['court'] += 1
            
            # Try to resolve target
            target_resolved = None
            if role_obj.citation_type == 'court':
                # Direct lookup in citation_id_map
                if role_obj.target_normalized in citation_id_map:
                    target_resolved = citation_id_map[role_obj.target_normalized]
                    stats['resolved_court'] += 1
            else:
                # BGE/ATF - would need separate resolution (not available)
                stats['unresolved'] += 1
                continue
            
            if target_resolved and target_resolved in id_to_idx:
                j = id_to_idx[target_resolved]
                weight = role_weights.get(role_obj.role, 1.0) * role_obj.confidence
                rows.append(i)
                cols.append(j)
                weights.append(weight)
            else:
                stats['unresolved'] += 1
    
    logger.info(f"Role '{role_filter or 'all'}': {stats['total']} citations (BGE={stats['bge']}, Court={stats['court']}), "
                f"resolved court={stats['resolved_court']}, unresolved={stats['unresolved']}")
    
    if not rows:
        logger.warning(f"No resolved citation roles found for role_filter={role_filter}")
        return np.zeros((n, 64))
    
    from scipy.sparse import csr_matrix
    from sklearn.decomposition import TruncatedSVD
    
    citation_matrix = csr_matrix((weights, (rows, cols)), shape=(n, n))
    citation_sym = citation_matrix + citation_matrix.T
    
    row_sums = np.array(citation_sym.sum(axis=1)).flatten()
    row_sums[row_sums == 0] = 1
    citation_norm = citation_sym.multiply(1.0 / row_sums[:, np.newaxis])
    
    n_comp = min(64, citation_norm.shape[1] - 1, n - 1)
    svd = TruncatedSVD(n_components=n_comp, random_state=42)
    emb = svd.fit_transform(citation_norm)
    
    norms = np.linalg.norm(emb, axis=1, keepdims=True)
    norms[norms == 0] = 1
    emb = emb / norms
    
    logger.info(f"Citation role matrix ({role_filter or 'all'}): {n} decisions, {n_comp} dims, {len(rows)} edges")
    return emb

def main():
    logger.info("=" * 70)
    logger.info("Legal Distance v6 - Rebuild Citation Role Embeddings")
    logger.info("With court decision citation extraction + ID resolution")
    logger.info("=" * 70)
    
    sys.path.insert(0, '/tmp/lex_accepted/fractal-map/fractal_map/hierarchical')
    from hierarchical_leiden import load_metadata_with_branch
    
    # Load signals
    logger.info("\n1. Loading legal signals...")
    signals = load_signals()
    
    # Load citation ID map
    logger.info("\n2. Loading citation ID resolution map...")
    citation_id_map = load_citation_id_map()
    
    # Load metadata (full 1200 for scale, or 1000 for 1000-slice)
    logger.info("\n3. Loading metadata...")
    _, metadata = load_metadata_with_branch()
    logger.info(f"Metadata: {len(metadata)} decisions")
    
    # Extract roles for all decisions
    logger.info("\n4. Extracting citation roles (BGE + court decisions)...")
    all_roles = []
    role_distribution = Counter()
    citation_type_counts = Counter()
    
    for m in metadata:
        did = m['decision_id']
        result = extract_citation_roles(did, signals, citation_id_map)
        all_roles.extend(result.roles)
        role_distribution.update(result.role_counts)
        for r in result.roles:
            citation_type_counts[r.citation_type] += 1
    
    logger.info(f"Total citation roles extracted: {len(all_roles)}")
    logger.info(f"Role distribution: {dict(role_distribution)}")
    logger.info(f"Citation types: {dict(citation_type_counts)}")
    
    # Save role extraction results
    roles_output = [asdict(r) for r in all_roles]
    with open(OUTPUT_DIR / "citation_roles_rebuilt.json", 'w') as f:
        json.dump(roles_output, f, indent=2, default=str)
    
    # Build role-specific matrices
    logger.info("\n5. Building citation role matrices with resolved IDs...")
    role_types = ['following', 'distinguishing', 'overruling', 'criticizing', 'citing']
    
    role_embeddings = {}
    for role in role_types:
        emb = build_citation_role_matrix(signals, metadata, citation_id_map, role_filter=role)
        role_embeddings[role] = emb
        np.save(OUTPUT_DIR / f"citation_role_{role}_rebuilt.npy", emb)
    
    # Also build combined weighted matrix
    emb_all = build_citation_role_matrix(signals, metadata, citation_id_map, role_filter=None)
    role_embeddings['all_weighted'] = emb_all
    np.save(OUTPUT_DIR / "citation_role_all_weighted_rebuilt.npy", emb_all)
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("REBUILT CITATION ROLE MODELING SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Decisions analyzed: {len(metadata)}")
    logger.info(f"Total role annotations: {len(all_roles)}")
    logger.info(f"Role distribution: {dict(role_distribution)}")
    logger.info(f"Citation types: {dict(citation_type_counts)}")
    logger.info(f"Role-specific embeddings created: {list(role_embeddings.keys())}")
    
    summary = {
        'decisions_analyzed': len(metadata),
        'total_roles': len(all_roles),
        'role_distribution': dict(role_distribution),
        'citation_type_counts': dict(citation_type_counts),
        'embeddings_created': list(role_embeddings.keys()),
        'embedding_shapes': {k: list(v.shape) for k, v in role_embeddings.items()},
    }
    
    with open(OUTPUT_DIR / "citation_roles_rebuilt_summary.json", 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    
    logger.info("\n=== Citation Role Rebuild Complete ===")
    return summary, role_embeddings, metadata

if __name__ == "__main__":
    main()