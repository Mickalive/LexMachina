#!/usr/bin/env python3
"""
Extract Dispositiv (holding/outcome) section from existing legal_signals_1000_v2.jsonl.

Adds dispositiv_text and dispositiv_paragraphs to each decision.
"""

import json
import re
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

SIGNALS_FILE = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/legal_signals_1000_v2.jsonl")
OUTPUT_FILE = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/legal_signals_1000_v3.jsonl")

# Trilingual section markers for Dispositiv
DISPOSITIV_PATTERNS = {
    'de': [
        r'(?:Demnach\s+erkennt\s+[^:]*:\s*)\n',
    ],
    'fr': [
        r'(?:Par\s+ces\s+motifs,\s+le\s+[^:]*\s+prononce\s*:\s*)\n',
    ],
    'it': [
        r'(?:Per\s+questi\s+motivi,\s+il\s+[^:]*\s+pronuncia\s*:\s*)\n',
    ],
}

# End patterns - sections that come after Dispositiv or end the document
END_PATTERNS = [
    r'\n\s*(?:Bundesgericht|Tribunal\s+fédéral|Tribunale\s+federale)\s*\n',
    r'\n\s*(?:Urteil\s+vom|Arrêt\s+du|Sentenza\s+del)\s',
    r'\n\s*(?:Richter|Juge|Giudice)\s*,',
    r'\n\s*(?:Greffier|Sekretär|Cancelliere)\s*:',
    r'\n\s*(?:Präsident|Président|Presidente)\s*,',
]

def extract_dispositiv(text: str, language: str) -> str:
    """Extract Dispositiv section from decision text."""
    if not text or language not in DISPOSITIV_PATTERNS:
        return ""
    
    text_norm = text.replace('\r\n', '\n').replace('\r', '\n')
    patterns = DISPOSITIV_PATTERNS[language]
    
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


def extract_dispositiv_paragraphs(text: str, language: str) -> list:
    """Extract individual paragraphs from Dispositiv section."""
    dispositiv_text = extract_dispositiv(text, language)
    if not dispositiv_text:
        return []
    
    # Split by paragraph markers (numbered items like "1.", "2.", etc.)
    paragraphs = re.split(r'\n\s*\d+\.\s*', dispositiv_text)
    # Filter out empty and very short paragraphs
    paragraphs = [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 10]
    return paragraphs


def main():
    logger.info("Extracting Dispositiv from legal_signals_1000_v2.jsonl...")
    
    signals = {}
    with open(SIGNALS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            signals[data['decision_id']] = data
    
    logger.info(f"Loaded {len(signals)} decisions")
    
    # Extract Dispositiv for each decision
    updated_count = 0
    for did, sig in signals.items():
        full_text = sig.get('full_text', '')
        language = sig.get('language', 'de')
        
        dispositiv_text = extract_dispositiv(full_text, language)
        dispositiv_paragraphs = extract_dispositiv_paragraphs(full_text, language)
        
        sig['dispositiv_text'] = dispositiv_text
        sig['dispositiv_paragraphs'] = dispositiv_paragraphs
        
        if dispositiv_text:
            updated_count += 1
    
    logger.info(f"Added Dispositiv to {updated_count} decisions")
    
    # Save updated signals
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for sig in signals.values():
            f.write(json.dumps(sig, ensure_ascii=False) + '\n')
    
    logger.info(f"Saved updated signals to {OUTPUT_FILE}")
    
    # Print coverage stats
    with_dispositiv = sum(1 for s in signals.values() if s.get('dispositiv_text'))
    total_chars = sum(len(s.get('dispositiv_text', '')) for s in signals.values())
    total_paragraphs = sum(len(s.get('dispositiv_paragraphs', [])) for s in signals.values())
    logger.info(f"Coverage: {with_dispositiv}/{len(signals)} ({with_dispositiv/len(signals)*100:.1f}%)")
    logger.info(f"Total Dispositiv chars: {total_chars}, mean: {total_chars/len(signals):.0f}")
    logger.info(f"Total paragraphs: {total_paragraphs}, mean: {total_paragraphs/len(signals):.1f}")

if __name__ == "__main__":
    main()