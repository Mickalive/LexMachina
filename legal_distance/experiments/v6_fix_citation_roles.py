#!/usr/bin/env python3
"""
Legal Distance Lane v6 - FIX Citation Role Embeddings

Addresses the citation format mismatch that produced zero matrices:
- v5 role extraction only captured BGE/ATF format citations
- v6 citation ID resolution only resolves court decision format citations
- This script extracts BOTH formats and uses resolved mappings to build valid embeddings

Strategy:
1. Re-extract citation roles including court decision format (e.g., "7B_189/2023", "1B_407/2022")
2. Use v6 resolved citation_to_decision_id.json to map targets to internal decision_ids
3. Filter role annotations to only those with resolved targets
4. Rebuild role matrices with actual graph connectivity
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
from scipy.sparse import csr_matrix
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
SIGNALS_FILE = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/legal_signals_full.jsonl")
RESOLVED_MAPPING_FILE = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v6/citation_id_resolution/citation_to_decision_id.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v6/citation_roles_fixed")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Trilingual citation role patterns (from v5)
CITATION_ROLE_PATTERNS = {
    'de': {
        'following': [
            'bestätigt', 'folgt', 'wendet an', 'trifft zu', 'ist anwendbar',
            'stimmt zu', 'übernimmt', 'bejaht', 'bestätigend', 'zutreffend',
            'in sinne von', 'gemäß', 'entsprechend', 'analog',
        ],
        'distinguishing': [
            'unterscheidet', 'abgrenzt', 'nicht anwendbar', 'nicht zutreffend',
            'anders gelagert', 'anderer fall', 'kann nicht herangezogen',
            'nicht vergleichbar', 'besondere umstände', 'ausnahmsweise',
            'beschränkt auf', 'eingeschränkt',
        ],
        'overruling': [
            'aufgegeben', 'überholt', 'nicht mehr haltbar', 'revidiert',
            'ändert rechtsprechung', 'gibt auf', 'verlässt', 'korrigiert',
            'nicht mehr zutreffend', 'überwunden', 'abandonniert',
        ],
        'criticizing': [
            'kritisiert', 'beanstandet', 'zweifelt an', 'fragwürdig',
            'bedenklich', 'problematisch', 'nicht überzeugend',
        ],
    },
    'fr': {
        'following': [
            'confirme', 'suit', 'applique', 'est applicable', "est d'accord",
            'reprend', 'approuve', 'conforme', 'selon', 'selon la jurisprudence',
            'dans le sens de', 'conformément', 'analogiquement',
        ],
        'distinguishing': [
            'distingue', 'différencie', 'non applicable', 'non pertinent',
            'espèce différente', 'autre cas', 'ne peut être invoqué',
            'non comparable', 'circonstances particulières', 'exceptionnellement',
            'limité à', 'restreint',
        ],
        'overruling': [
            'abandonne', 'revient sur', 'non plus tenable', 'révise',
            'change la jurisprudence', 'renonce', 'quitte', 'corrige',
            'non plus pertinent', 'surmonté',
        ],
        'criticizing': [
            'critique', 'conteste', 'met en doute', 'questionnable',
            'préoccupant', 'problématique', 'non convaincant',
        ],
    },
    'it': {
        'following': [
            'conferma', 'segue', 'applica', 'è applicabile', "è d'accordo",
            'riprende', 'approva', 'conforme', 'secondo', 'secondo la giurisprudenza',
            "nell'ambito di", 'conformemente', 'analogicamente',
        ],
        'distinguishing': [
            'distingue', 'differenzia', 'non applicabile', 'non pertinente',
            'fattispecie diversa', 'altro caso', 'non può essere invocato',
            'non comparabile', 'circostanze particolari', 'eccezionalmente',
            'limitato a', 'ristretto',
        ],
        'overruling': [
            'abbandona', 'torna su', 'non più tenibile', 'rivisita',
            'cambia la giurisprudenza', 'rinuncia', 'lascia', 'corregge',
            'non più pertinente', 'superato',
        ],
        'criticizing': [
            'critica', 'contesta', 'mette in dubbio', 'questionabile',
            'preoccupante', 'problematico', 'non convincente',
        ],
    },
}

CONTEXT_WINDOW = 200

@dataclass
class CitationRole:
    target_decision: str
    role: str
    confidence: float
    context_snippet: str
    language: str
    paragraph_idx: int
    citation_format: str  # 'bge_atf' or 'court_decision'

def load_signals() -> Dict[str, Any]:
    signals = {}
    with open(SIGNALS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            signals[data['decision_id']] = data
    logger.info(f"Loaded signals for {len(signals)} decisions")
    return signals

def load_resolved_mapping() -> Dict[str, str]:
    """Load citation -> decision_id mapping from v6 resolution pipeline."""
    with open(RESOLVED_MAPPING_FILE, 'r') as f:
        data = json.load(f)
    # Extract just the target decision_id mapping
    mapping = {}
    for cit, info in data.items():
        mapping[cit] = info['target_decision_id']
    logger.info(f"Loaded {len(mapping)} resolved citation mappings")
    return mapping

# Citation parsing patterns
# Court decision format: "7B_189/2023", "1B_407/2022", "5A_129/2019", "2A.478/2005"
COURT_DECISION_PATTERNS = [
    re.compile(r'\b([0-9]+[A-Z][A-Z]?)_(\d+)/(\d{4})\b'),  # 7B_189/2023
    re.compile(r'\b([0-9]+[A-Z])\.(\d+)/(\d{4})\b'),         # 2A.478/2005
    re.compile(r'\b([A-Z]{1,2})\-(\d+)/(\d{4})\b'),          # A-3375/2023
    re.compile(r'arr[eê]t\s+([0-9]+[A-Z][A-Z]?)_(\d+)/(\d{4})', re.IGNORECASE),  # arrêt 7B_189/2023
    re.compile(r'urteil\s+([0-9]+[A-Z][A-Z]?)_(\d+)/(\d{4})', re.IGNORECASE),    # Urteil 7B_189/2023
    re.compile(r'entscheid\s+([0-9]+[A-Z][A-Z]?)_(\d+)/(\d{4})', re.IGNORECASE),  # Entscheid 7B_189/2023
]

# BGE/ATF format: "BGE 149 IV 9", "ATF 147 IV 73 consid. 2"
BGE_ATF_PATTERNS = [
    re.compile(r'\b(?:BGE|ATF)\s+\d+\s+[IVX]+\s+\d+(?:\s+consid\.\s*\d+)?(?:\s+E\.\s*\d+)?', re.IGNORECASE),
    re.compile(r'\b(?:BGE|ATF)\s+\d+\s+[IVX]+\s+\d+', re.IGNORECASE),
]

def normalize_court_citation(match, pattern_idx: int) -> str:
    """Normalize court decision citation to standard format: chamber_number/year"""
    groups = match.groups()
    if pattern_idx == 0:  # 7B_189/2023
        chamber, number, year = groups
        return f"{chamber}_{number}/{year}"
    elif pattern_idx == 1:  # 2A.478/2005
        chamber, number, year = groups
        return f"{chamber}_{number}/{year}"
    elif pattern_idx == 2:  # A-3375/2023
        chamber, number, year = groups
        return f"{chamber}_{number}/{year}"
    elif pattern_idx in [3, 4, 5]:  # arrêt/Urteil/Entscheid 7B_189/2023
        chamber, number, year = groups
        return f"{chamber}_{number}/{year}"
    return match.group()

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

def find_all_citation_targets(paragraph: str) -> List[Tuple[str, int, str]]:
    """Find ALL cited decision references in a paragraph. Returns (target, position, format)."""
    targets = []
    
    # Court decision format
    for pattern_idx, pattern in enumerate(COURT_DECISION_PATTERNS):
        for match in pattern.finditer(paragraph):
            normalized = normalize_court_citation(match, pattern_idx)
            targets.append((normalized, match.start(), 'court_decision'))
    
    # BGE/ATF format
    for pattern in BGE_ATF_PATTERNS:
        for match in pattern.finditer(paragraph):
            targets.append((match.group().strip(), match.start(), 'bge_atf'))
    
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

def extract_citation_roles_full(decision_id: str, signals: Dict[str, Any], resolved_mapping: Dict[str, str]) -> List[CitationRole]:
    """Extract citation roles for a single decision, including court decision format."""
    sig = signals.get(decision_id, {})
    full_text = sig.get('full_text', '')
    language = sig.get('language', 'de')
    
    paragraphs = extract_paragraphs(full_text, language)
    
    roles = []
    for para_idx, para in enumerate(paragraphs):
        targets = find_all_citation_targets(para)
        for target, pos, cit_format in targets:
            role, confidence = classify_citation_role(para, target, pos, language)
            target_clean = re.sub(r'\s+', ' ', target).strip()
            
            roles.append(CitationRole(
                target_decision=target_clean,
                role=role,
                confidence=confidence,
                context_snippet=para[max(0, pos-100):pos+len(target)+100],
                language=language,
                paragraph_idx=para_idx,
                citation_format=cit_format,
            ))
    
    return roles

def build_citation_role_matrix_fixed(
    metadata: List[Dict],
    all_roles_by_did: Dict[str, List[CitationRole]],
    resolved_mapping: Dict[str, str],
    role_filter: Optional[str] = None
) -> np.ndarray:
    """Build citation role-weighted adjacency matrix using resolved citation IDs."""
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
    resolved_count = 0
    total_count = 0
    
    for i, m in enumerate(metadata):
        did = m['decision_id']
        roles = all_roles_by_did.get(did, [])
        
        for role_obj in roles:
            total_count += 1
            if role_filter and role_obj.role != role_filter:
                continue
            
            target = role_obj.target_decision
            # Try to resolve the citation
            target_did = None
            
            if target in resolved_mapping:
                target_did = resolved_mapping[target]
            # Also try case-insensitive match
            elif target.lower() in {k.lower(): v for k, v in resolved_mapping.items()}:
                target_did = {k.lower(): v for k, v in resolved_mapping.items()}[target.lower()]
            
            if target_did and target_did in id_to_idx:
                j = id_to_idx[target_did]
                weight = role_weights.get(role_obj.role, 1.0) * role_obj.confidence
                rows.append(i)
                cols.append(j)
                weights.append(weight)
                resolved_count += 1
    
    logger.info(f"Role matrix ({role_filter or 'all'}): {resolved_count}/{total_count} edges resolved")
    
    if not rows:
        logger.warning(f"No resolved citation roles found for role_filter={role_filter}")
        return np.zeros((n, 64))
    
    citation_matrix = csr_matrix((weights, (rows, cols)), shape=(n, n))
    citation_sym = citation_matrix + citation_matrix.T
    
    row_sums = np.array(citation_sym.sum(axis=1)).flatten()
    row_sums[row_sums == 0] = 1
    citation_norm = citation_sym.multiply(1.0 / row_sums[:, np.newaxis])
    
    n_comp = min(64, citation_norm.shape[1] - 1, n - 1)
    svd = TruncatedSVD(n_components=n_comp, random_state=42)
    emb = svd.fit_transform(citation_norm)
    
    emb = normalize(emb, norm='l2', axis=1)
    
    logger.info(f"Citation role matrix ({role_filter or 'all'}): {n} decisions, {n_comp} dims, {len(rows)} edges")
    return emb

def main():
    logger.info("=" * 70)
    logger.info("Legal Distance Lane v6 - FIX Citation Role Embeddings")
    logger.info("Extracting court decision format citations + using resolved IDs")
    logger.info("=" * 70)
    
    sys.path.insert(0, '/tmp/lex_accepted/fractal-map/fractal_map/hierarchical')
    from hierarchical_leiden import load_metadata_with_branch
    
    # 1. Load signals
    logger.info("\n1. Loading legal signals...")
    signals = load_signals()
    
    # 2. Load resolved citation mapping
    logger.info("\n2. Loading v6 resolved citation mappings...")
    resolved_mapping = load_resolved_mapping()
    
    # 3. Load metadata
    logger.info("\n3. Loading metadata...")
    _, metadata = load_metadata_with_branch()
    logger.info(f"Metadata: {len(metadata)} decisions")
    
    # 4. Extract citation roles for ALL decisions (not just 200 sample)
    logger.info("\n4. Extracting citation roles (ALL decisions, both formats)...")
    all_roles_by_did = {}
    role_distribution = Counter()
    format_distribution = Counter()
    total_roles = 0
    
    for m in metadata:
        did = m['decision_id']
        roles = extract_citation_roles_full(did, signals, resolved_mapping)
        all_roles_by_did[did] = roles
        for r in roles:
            role_distribution[r.role] += 1
            format_distribution[r.citation_format] += 1
        total_roles += len(roles)
    
    logger.info(f"Total citation roles extracted: {total_roles}")
    logger.info(f"Role distribution: {dict(role_distribution)}")
    logger.info(f"Format distribution: {dict(format_distribution)}")
    
    # Save role extraction results
    roles_output = []
    for did, roles in all_roles_by_did.items():
        for r in roles:
            d = asdict(r)
            d['source_decision'] = did
            roles_output.append(d)
    
    with open(OUTPUT_DIR / "citation_roles_fixed_sample.json", 'w') as f:
        json.dump(roles_output, f, indent=2, default=str)
    
    # 5. Build role-specific matrices
    logger.info("\n5. Building FIXED citation role matrices...")
    role_types = ['following', 'distinguishing', 'overruling', 'criticizing', 'citing']
    
    role_embeddings = {}
    for role in role_types:
        emb = build_citation_role_matrix_fixed(metadata, all_roles_by_did, resolved_mapping, role_filter=role)
        role_embeddings[role] = emb
        np.save(OUTPUT_DIR / f"citation_role_{role}_fixed.npy", emb)
    
    # Also build combined weighted matrix
    emb_all = build_citation_role_matrix_fixed(metadata, all_roles_by_did, resolved_mapping, role_filter=None)
    role_embeddings['all_weighted'] = emb_all
    np.save(OUTPUT_DIR / "citation_role_all_weighted_fixed.npy", emb_all)
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("FIXED CITATION ROLE MODELING SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Decisions analyzed: {len(metadata)}")
    logger.info(f"Total role annotations: {total_roles}")
    logger.info(f"Role distribution: {dict(role_distribution)}")
    logger.info(f"Format distribution: {dict(format_distribution)}")
    logger.info(f"Role-specific embeddings created: {list(role_embeddings.keys())}")
    logger.info(f"Embedding shapes: {{k: v.shape for k, v in role_embeddings.items()}}")
    
    # Check for non-zero embeddings
    for role, emb in role_embeddings.items():
        non_zero = np.count_nonzero(emb)
        total = emb.size
        logger.info(f"  {role}: {non_zero}/{total} non-zero ({non_zero/total*100:.1f}%)")
    
    summary = {
        'decisions_analyzed': len(metadata),
        'total_roles': total_roles,
        'role_distribution': dict(role_distribution),
        'format_distribution': dict(format_distribution),
        'embeddings_created': list(role_embeddings.keys()),
        'embedding_shapes': {k: list(v.shape) for k, v in role_embeddings.items()},
        'non_zero_stats': {k: f"{np.count_nonzero(v)}/{v.size} ({np.count_nonzero(v)/v.size*100:.1f}%)" for k, v in role_embeddings.items()},
    }
    
    with open(OUTPUT_DIR / "citation_roles_fixed_summary.json", 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    
    logger.info("\n=== Fixed Citation Role Modeling Complete ===")
    return summary, role_embeddings

if __name__ == "__main__":
    main()