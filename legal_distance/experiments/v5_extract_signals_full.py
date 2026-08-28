#!/usr/bin/env python3
"""
Extract legal signals for the full corpus (1200 decisions).
"""

import json
import re
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import Counter
import logging
import sys

sys.path.insert(0, '/tmp/lex_accepted/corpus/corpus/normalization')
from statute_extractor import extract_statutes_from_text, StatuteReference

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

CORPUS_FILE = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/bger_full_corpus.jsonl")
OUTPUT_FILE = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/legal_signals_full.jsonl")
STATS_FILE = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/signal_coverage_stats_full.json")

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

@dataclass
class LegalSignals:
    decision_id: str
    statutes: List[str]
    statute_contexts: List[str]
    erwaegungen_text: str
    erwaegungen_paragraphs: List[str]
    outgoing_citations: List[Dict]
    incoming_citations: List[Dict]
    cited_decisions: List[str]
    legal_area: str
    erwaegungen_headings: List[str]
    outcome: str
    decision_type: str
    preparatory_materials: List[Dict]
    doctrine_refs: List[str]
    boilerplate_density: float
    full_text: str
    language: str
    # New: Sachverhalt
    sachverhalt_text: str = ""
    sachverhalt_paragraphs: List[str] = None

    def __post_init__(self):
        if self.sachverhalt_paragraphs is None:
            self.sachverhalt_paragraphs = []

def load_corpus(file_path: Path) -> List[Dict]:
    decisions = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                decisions.append(json.loads(line))
    logger.info(f"Loaded {len(decisions)} decisions from {file_path}")
    return decisions

def extract_section(text: str, language: str, section: str) -> str:
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
    erwaeg_text = extract_section(text, language, 'erwaegungen')
    if not erwaeg_text:
        return []
    
    paragraphs = re.split(r'\n\s*\d+(?:\.\d+)*\.\s*', erwaeg_text)
    paragraphs = [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 20]
    return paragraphs

def extract_erwaegungen_headings(text: str, language: str) -> List[str]:
    erwaeg_text = extract_section(text, language, 'erwaegungen')
    if not erwaeg_text:
        return []
    
    headings = re.findall(r'^\s*(\d+(?:\.\d+)*)\.\s', erwaeg_text, re.MULTILINE)
    return headings

def extract_sachverhalt(text: str, language: str) -> str:
    if not text or language not in SECTION_PATTERNS:
        return ""
    
    text_norm = text.replace('\r\n', '\n').replace('\r', '\n')
    patterns = SECTION_PATTERNS[language].get('sachverhalt', [])
    
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

def extract_sachverhalt_paragraphs(text: str, language: str) -> list:
    sachverhalt_text = extract_sachverhalt(text, language)
    if not sachverhalt_text:
        return []
    
    paragraphs = re.split(r'\n\s*(?:\d+(?:\.\d+)*\.|[A-Z]\.)\s*', sachverhalt_text)
    paragraphs = [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 20]
    return paragraphs

def extract_doctrine_refs(text: str) -> List[str]:
    patterns = [
        r'(?:ATF|BGE)\s+\d+\s+[IVX]+\s+\d+',
        r'(?:ATF|BGE)\s+\d+\s+[IVX]+\s+\d+\s+consid\.\s*\d+',
        r'(?:ATF|BGE)\s+\d+\s+[IVX]+\s+\d+\s+E\.\s*\d+',
    ]
    
    refs = []
    for pattern in patterns:
        refs.extend(re.findall(pattern, text, re.IGNORECASE))
    
    seen = set()
    unique = []
    for r in refs:
        if r not in seen:
            seen.add(r)
            unique.append(r)
    return unique

def compute_boilerplate_density(text: str) -> float:
    if not text:
        return 0.0
    
    total_chars = len(text)
    boilerplate_chars = 0
    
    for pattern in BOILERPLATE_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            boilerplate_chars += match.end() - match.start()
    
    return boilerplate_chars / total_chars if total_chars > 0 else 0.0

def extract_legal_signals(decision: Dict) -> LegalSignals:
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
    
    # 3. Sachverhalt (facts)
    sachverhalt_text = extract_sachverhalt(full_text, language)
    sachverhalt_paragraphs = extract_sachverhalt_paragraphs(full_text, language)
    
    # 4. Citation roles
    outgoing_citations = decision.get('outgoing_citations', []) or []
    incoming_citations = decision.get('incoming_citations', []) or []
    cited_decisions = decision.get('cited_decisions', []) or []
    
    # 5. Legal issues
    legal_area = decision.get('legal_area', '')
    erwaegungen_headings = extract_erwaegungen_headings(full_text, language)
    
    # 6. Outcome
    outcome = decision.get('outcome', '')
    decision_type = decision.get('decision_type', '')
    
    # 7. Doctrine citations
    preparatory_materials = decision.get('preparatory_materials', []) or []
    doctrine_refs = extract_doctrine_refs(full_text)
    
    # 8. Boilerplate density
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
        sachverhalt_text=sachverhalt_text,
        sachverhalt_paragraphs=sachverhalt_paragraphs,
    )

def extract_signals_batch(decisions: List[Dict]) -> Dict[str, LegalSignals]:
    signals = {}
    for i, d in enumerate(decisions):
        if i % 100 == 0:
            logger.info(f"  Processing {i}/{len(decisions)}...")
        sig = extract_legal_signals(d)
        signals[sig.decision_id] = sig
    return signals

def save_signals(signals: Dict[str, LegalSignals], output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        for sig in signals.values():
            f.write(json.dumps(asdict(sig), ensure_ascii=False) + '\n')
    logger.info(f"Saved signals for {len(signals)} decisions to {output_path}")

def analyze_signal_coverage(signals: Dict[str, LegalSignals]) -> Dict[str, Any]:
    total = len(signals)
    stats = {
        'total_decisions': total,
        'statutes': {
            'decisions_with': sum(1 for s in signals.values() if s.statutes),
            'mean_per_decision': float(np.mean([len(s.statutes) for s in signals.values()])),
        },
        'erwaegungen': {
            'decisions_with': sum(1 for s in signals.values() if s.erwaegungen_text),
            'mean_chars': float(np.mean([len(s.erwaegungen_text) for s in signals.values()])),
            'mean_paragraphs': float(np.mean([len(s.erwaegungen_paragraphs) for s in signals.values()])),
        },
        'sachverhalt': {
            'decisions_with': sum(1 for s in signals.values() if s.sachverhalt_text),
            'mean_chars': float(np.mean([len(s.sachverhalt_text) for s in signals.values()])),
            'mean_paragraphs': float(np.mean([len(s.sachverhalt_paragraphs) for s in signals.values()])),
        },
        'citations': {
            'decisions_with_outgoing': sum(1 for s in signals.values() if s.outgoing_citations),
            'decisions_with_cited': sum(1 for s in signals.values() if s.cited_decisions),
            'mean_cited': float(np.mean([len(s.cited_decisions) for s in signals.values()])),
        },
        'outcomes': {
            'distribution': dict(Counter(s.outcome for s in signals.values())),
        },
        'decision_types': {
            'distribution': dict(Counter(s.decision_type for s in signals.values())),
        },
        'doctrine_refs': {
            'decisions_with': sum(1 for s in signals.values() if s.doctrine_refs),
            'mean_per_decision': float(np.mean([len(s.doctrine_refs) for s in signals.values()])),
        },
        'boilerplate': {
            'mean_density': float(np.mean([s.boilerplate_density for s in signals.values()])),
        },
    }
    return stats

def main():
    logger.info("=" * 60)
    logger.info("Legal Signal Extraction - Full Corpus (v5)")
    logger.info("=" * 60)
    
    # Load full corpus
    corpus = load_corpus(CORPUS_FILE)
    
    # Extract signals
    logger.info("Extracting legal signals...")
    signals = extract_signals_batch(corpus)
    
    # Analyze coverage
    stats = analyze_signal_coverage(signals)
    logger.info(f"Coverage stats: {json.dumps(stats, indent=2, default=str)}")
    
    # Save signals
    save_signals(signals, OUTPUT_FILE)
    
    # Save stats
    with open(STATS_FILE, 'w') as f:
        json.dump(stats, f, indent=2, default=str)
    
    logger.info("Legal signal extraction complete!")
    return signals, stats

if __name__ == "__main__":
    main()
