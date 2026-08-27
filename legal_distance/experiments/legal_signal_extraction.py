#!/usr/bin/env python3
"""
Legal Signal Extraction for Legal Distance Lane

Extracts legally structured signals from Swiss Federal Supreme Court decisions:
1. Norms/articles at issue (via statute extractor)
2. Reasoning sections (Erwägungen/Considérant/Considerando extraction from full_text)
3. Citation roles (outgoing/incoming, mention counts, confidence)
4. Legal issues (from legal_area and extracted from Erwägungen headings)
5. Outcomes (from outcome field)
6. Doctrine citations (from preparatory_materials and extracted from text)
7. Procedural boilerplate markers (for suppression)

These signals will be tested against the debiased_citation_blended baseline
using the full evaluation benchmark suite.
"""

import json
import re
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import Counter
import logging

# Import statute extractor
import sys
sys.path.insert(0, '/tmp/lex_accepted/corpus/corpus/normalization')
from statute_extractor import extract_statutes_from_text, StatuteReference

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

CORPUS_DIR = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
BASELINE_DIR = Path("/tmp/lex_accepted/fractal-map/results/fractal_map/baseline")
EVAL_DIR = Path("/tmp/lex_accepted/evaluation/evaluation")


@dataclass
class LegalSignals:
    """Container for extracted legal signals from a decision."""
    decision_id: str
    # 1. Norms/articles at issue
    statutes: List[str]  # e.g., ["Art. 41 OR", "Art. 8 ZGB"]
    statute_contexts: List[str]  # surrounding text for each statute
    # 2. Reasoning section text
    erwaegungen_text: str  # full reasoning text
    erwaegungen_paragraphs: List[str]  # individual paragraphs
    # 3. Citation roles
    outgoing_citations: List[Dict]  # target, mention_count, confidence
    incoming_citations: List[Dict]  # source, mention_count, confidence
    cited_decisions: List[str]  # simple list
    # 4. Legal issues
    legal_area: str  # from metadata
    erwaegungen_headings: List[str]  # extracted heading numbers
    # 5. Outcome
    outcome: str  # gutgeheissen, abgewiesen, etc.
    decision_type: str  # Leitentscheid, Endentscheid, etc.
    # 6. Doctrine citations
    preparatory_materials: List[Dict]  # law, article, sr_number
    doctrine_refs: List[str]  # e.g., "ATF 149 IV 9", "BGE 133 II 249"
    # 7. Procedural boilerplate markers
    boilerplate_density: float  # fraction of text matching boilerplate patterns
    # Raw text for reference
    full_text: str
    language: str


# Trilingual section markers
SECTION_PATTERNS = {
    'de': {
        'sachverhalt': [
            r'(?:Sachverhalt\s*:)\s*\n',
            r'(?:A\.\s*Sachverhalt\s*:)\s*\n',
        ],
        'erwaegungen': [
            r'(?:In\s+Erwägung\s*:)\s*\n',
            r'(?:Erwägungen\s*:)\s*\n',
            r'(?:Erwägung\s*:)\s*\n',
        ],
        'dispositif': [
            r'(?:Dispositiv\s*:)\s*\n',
            r'(?:Erkenntnis\s*:)\s*\n',
            r'(?:Ausgang\s*:)\s*\n',
        ],
    },
    'fr': {
        'sachverhalt': [
            r'(?:Faits\s*:)\s*\n',
            r'(?:En\s+fait\s*:)\s*\n',
        ],
        'erwaegungen': [
            r'(?:Considérant\s+en\s+droit\s*:)\s*\n',
            r'(?:Considérant\s*:)\s*\n',
            r'(?:Sur\s+ce\s*:)\s*\n',
        ],
        'dispositif': [
            r'(?:Dispositif\s*:)\s*\n',
            r'(?:Par\s+ces\s+motifs\s*:)\s*\n',
        ],
    },
    'it': {
        'sachverhalt': [
            r'(?:Fatto\s*:)\s*\n',
            r'(?:In\s+fatto\s*:)\s*\n',
        ],
        'erwaegungen': [
            r'(?:Considerando\s+in\s+diritto\s*:)\s*\n',
            r'(?:Considerando\s*:)\s*\n',
        ],
        'dispositif': [
            r'(?:Dispositivo\s*:)\s*\n',
            r'(?:Per\s+questi\s+motivi\s*:)\s*\n',
        ],
    },
}

END_PATTERNS = [
    r'\n\s*(?:Dispositiv|Erkenntnis|Ausgang)\s*:',
    r'\n\s*(?:Dispositif|Par\s+ces\s+motifs)\s*:',
    r'\n\s*(?:Dispositivo|Per\s+questi\s+motivi)\s*:',
    r'\n\s*(?:Sachverhalt|Faits|Fatto)\s*:',
    r'\n\s*(?:In\s+Erwägung|Erwägungen|Considérant|Considerando)\s*:',
    r'\n\s*(?:Bundesgericht|Tribunal\s+fédéral|Tribunale\s+federale)\s*\n',
    r'\n\s*(?:Urteil\s+vom|Arrêt\s+du|Sentenza\s+del)\s',
]

# Boilerplate patterns (common procedural text)
BOILERPLATE_PATTERNS = [
    r'Bundesgericht\s*\n\s*Tribunal\s+fédéral\s*\n\s*Tribunale\s+federale',
    r'Composition\s*\n',
    r'Participants?\s+à\s+la\s+procédure',
    r'Verfahrensbeteiligte',
    r'Objet\s*\n',
    r'Gegenstand\s*\n',
    r'recourse\s+contre',
    r'Beschwerde\s+gegen',
    r'invité\s+à\s+se\s+déterminer',
    r'zur\s+Stellungnahme\s+aufgefordert',
    r'a\s+répliqué',
    r'hat\s+repliziert',
    r'Greffier\s*:',
    r'Sekretär\s*:',
    r'Président\s*,',
    r'Präsident\s*,',
]


def load_corpus(file_path: Path) -> List[Dict]:
    """Load decisions from JSONL file."""
    decisions = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                decisions.append(json.loads(line))
    logger.info(f"Loaded {len(decisions)} decisions from {file_path}")
    return decisions


def extract_section(text: str, language: str, section: str) -> str:
    """Extract a specific section from decision text."""
    if not text or language not in SECTION_PATTERNS:
        return ""
    
    text_norm = text.replace('\r\n', '\n').replace('\r', '\n')
    patterns = SECTION_PATTERNS[language].get(section, [])
    
    start = -1
    for pattern in patterns:
        match = re.search(pattern, text_norm, re.IGNORECASE)
        if match:
            start = match.end()
            break
    
    if start == -1:
        return ""
    
    end = len(text_norm)
    for pattern in END_PATTERNS:
        match = re.search(pattern, text_norm[start:], re.IGNORECASE)
        if match:
            candidate = start + match.start()
            if candidate < end:
                end = candidate
    
    section_text = text_norm[start:end].strip()
    section_text = re.sub(r'\n\s*\n+', '\n', section_text)
    return section_text


def extract_erwaegungen_paragraphs(text: str, language: str) -> List[str]:
    """Extract individual paragraphs from Erwägungen section."""
    erwaeg_text = extract_section(text, language, 'erwaegungen')
    if not erwaeg_text:
        return []
    
    # Split by paragraph markers (numbered paragraphs)
    # Swiss BGer uses patterns like "1.", "1.1.", "2.", etc.
    paragraphs = re.split(r'\n\s*\d+(?:\.\d+)*\.\s*', erwaeg_text)
    # Filter out empty and very short paragraphs
    paragraphs = [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 20]
    return paragraphs


def extract_erwaegungen_headings(text: str, language: str) -> List[str]:
    """Extract heading numbers from Erwägungen (e.g., '1.', '2.1.', '3.')."""
    erwaeg_text = extract_section(text, language, 'erwaegungen')
    if not erwaeg_text:
        return []
    
    headings = re.findall(r'^\s*(\d+(?:\.\d+)*)\.\s', erwaeg_text, re.MULTILINE)
    return headings


def extract_doctrine_refs(text: str) -> List[str]:
    """Extract doctrine citations (ATF, BGE, JAR, etc.) from text."""
    # Swiss legal citation patterns
    patterns = [
        r'(?:ATF|BGE)\s+\d+\s+[IVX]+\s+\d+',  # ATF 149 IV 9, BGE 133 II 249
        r'(?:ATF|BGE)\s+\d+\s+[IVX]+\s+\d+\s+consid\.\s*\d+',  # with consid.
        r'(?:ATF|BGE)\s+\d+\s+[IVX]+\s+\d+\s+E\.\s*\d+',  # with E.
    ]
    
    refs = []
    for pattern in patterns:
        refs.extend(re.findall(pattern, text, re.IGNORECASE))
    
    # Deduplicate
    seen = set()
    unique = []
    for r in refs:
        if r not in seen:
            seen.add(r)
            unique.append(r)
    return unique


def compute_boilerplate_density(text: str) -> float:
    """Compute fraction of text matching boilerplate patterns."""
    if not text:
        return 0.0
    
    total_chars = len(text)
    boilerplate_chars = 0
    
    for pattern in BOILERPLATE_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            boilerplate_chars += match.end() - match.start()
    
    return boilerplate_chars / total_chars if total_chars > 0 else 0.0


def extract_legal_signals(decision: Dict) -> LegalSignals:
    """Extract all legal signals from a canonical decision."""
    decision_id = decision.get('decision_id', '')
    full_text = decision.get('full_text', '')
    language = decision.get('language', 'de')
    
    # 1. Norms/articles at issue
    statute_refs = extract_statutes_from_text(full_text, max_results=200, include_context=True)
    statutes = [f"{r.article} {r.law_abbrev}" for r in statute_refs]
    statute_contexts = [r.context or "" for r in statute_refs]
    
    # 2. Reasoning section
    erwaegungen_text = extract_section(full_text, language, 'erwaegungen')
    erwaegungen_paragraphs = extract_erwaegungen_paragraphs(full_text, language)
    
    # 3. Citation roles
    outgoing_citations = decision.get('outgoing_citations', []) or []
    incoming_citations = decision.get('incoming_citations', []) or []
    cited_decisions = decision.get('cited_decisions', []) or []
    
    # 4. Legal issues
    legal_area = decision.get('legal_area', '')
    erwaegungen_headings = extract_erwaegungen_headings(full_text, language)
    
    # 5. Outcome
    outcome = decision.get('outcome', '')
    decision_type = decision.get('decision_type', '')
    
    # 6. Doctrine citations
    preparatory_materials = decision.get('preparatory_materials', []) or []
    doctrine_refs = extract_doctrine_refs(full_text)
    
    # 7. Boilerplate density
    boilerplate_density = compute_boilerplate_density(full_text)
    
    return LegalSignals(
        decision_id=decision_id,
        statutes=statutes,
        statute_contexts=statute_contexts,
        erwaegungen_text=erwaegungen_text,
        erwaegungen_paragraphs=erwaegungen_paragraphs,
        outgoing_citations=outgoing_citations,
        incoming_citations=incoming_citations,
        cited_decisions=cited_decisions,
        legal_area=legal_area,
        erwaegungen_headings=erwaegungen_headings,
        outcome=outcome,
        decision_type=decision_type,
        preparatory_materials=preparatory_materials,
        doctrine_refs=doctrine_refs,
        boilerplate_density=boilerplate_density,
        full_text=full_text,
        language=language,
    )


def extract_signals_batch(decisions: List[Dict]) -> Dict[str, LegalSignals]:
    """Extract legal signals for a batch of decisions."""
    signals = {}
    for d in decisions:
        sig = extract_legal_signals(d)
        signals[sig.decision_id] = sig
    return signals


def save_signals(signals: Dict[str, LegalSignals], output_path: Path):
    """Save extracted signals to JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        for sig in signals.values():
            f.write(json.dumps(asdict(sig), ensure_ascii=False) + '\n')
    logger.info(f"Saved signals for {len(signals)} decisions to {output_path}")


def load_signals(file_path: Path) -> Dict[str, LegalSignals]:
    """Load signals from JSONL."""
    signals = {}
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            signals[data['decision_id']] = LegalSignals(**data)
    return signals


def analyze_signal_coverage(signals: Dict[str, LegalSignals]) -> Dict[str, Any]:
    """Analyze coverage and statistics of extracted signals."""
    total = len(signals)
    stats = {
        'total_decisions': total,
        'statutes': {
            'decisions_with': sum(1 for s in signals.values() if s.statutes),
            'mean_per_decision': np.mean([len(s.statutes) for s in signals.values()]),
        },
        'erwaegungen': {
            'decisions_with': sum(1 for s in signals.values() if s.erwaegungen_text),
            'mean_chars': np.mean([len(s.erwaegungen_text) for s in signals.values()]),
            'mean_paragraphs': np.mean([len(s.erwaegungen_paragraphs) for s in signals.values()]),
        },
        'citations': {
            'decisions_with_outgoing': sum(1 for s in signals.values() if s.outgoing_citations),
            'decisions_with_cited': sum(1 for s in signals.values() if s.cited_decisions),
            'mean_cited': np.mean([len(s.cited_decisions) for s in signals.values()]),
        },
        'outcomes': {
            'distribution': dict(Counter(s.outcome for s in signals.values())),
        },
        'decision_types': {
            'distribution': dict(Counter(s.decision_type for s in signals.values())),
        },
        'doctrine_refs': {
            'decisions_with': sum(1 for s in signals.values() if s.doctrine_refs),
            'mean_per_decision': np.mean([len(s.doctrine_refs) for s in signals.values()]),
        },
        'boilerplate': {
            'mean_density': np.mean([s.boilerplate_density for s in signals.values()]),
        },
    }
    return stats


def main():
    """Main function to extract signals from the 1000-decision slice."""
    logger.info("=" * 60)
    logger.info("Legal Signal Extraction - Legal Distance Lane")
    logger.info("=" * 60)
    
    # Load 1000-decision slice
    corpus = load_corpus(CORPUS_DIR / "bger_2000plus_slice_1000.jsonl")
    
    # Extract signals
    logger.info("Extracting legal signals...")
    signals = extract_signals_batch(corpus)
    
    # Analyze coverage
    stats = analyze_signal_coverage(signals)
    logger.info(f"Coverage stats: {json.dumps(stats, indent=2, default=str)}")
    
    # Save signals
    output_dir = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results")
    output_dir.mkdir(parents=True, exist_ok=True)
    save_signals(signals, output_dir / "legal_signals_1000.jsonl")
    
    # Save stats
    with open(output_dir / "signal_coverage_stats.json", 'w') as f:
        json.dump(stats, f, indent=2, default=str)
    
    logger.info("Legal signal extraction complete!")
    return signals, stats


if __name__ == "__main__":
    main()