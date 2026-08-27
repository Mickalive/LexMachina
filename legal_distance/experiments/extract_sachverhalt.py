#!/usr/bin/env python3
"""
Extract Sachverhalt (facts) section from existing legal_signals_1000.jsonl.

Adds sachverhalt_text and sachverhalt_paragraphs to each decision.
"""

import json
import re
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

SIGNALS_FILE = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/legal_signals_1000.jsonl")
OUTPUT_FILE = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/legal_signals_1000_v2.jsonl")

# Trilingual section markers for Sachverhalt
SACHVERHALT_PATTERNS = {
    'de': [
        r'(?:Sachverhalt\s*:)\s*\n',
        r'(?:A\.\s*Sachverhalt\s*:)\s*\n',
    ],
    'fr': [
        r'(?:Faits\s*:)\s*\n',
        r'(?:En\s+fait\s*:)\s*\n',
    ],
    'it': [
        r'(?:Fatto\s*:)\s*\n',
        r'(?:In\s+fatto\s*:)\s*\n',
    ],
}

END_PATTERNS = [
    r'\n\s*(?:Erwägungen|In\s+Erwägung|Considérant|Considerando)\s*:',
    r'\n\s*(?:Dispositiv|Erkenntnis|Ausgang|Dispositif|Dispositivo)\s*:',
    r'\n\s*(?:Bundesgericht|Tribunal\s+fédéral|Tribunale\s+federale)\s*\n',
    r'\n\s*(?:Urteil\s+vom|Arrêt\s+du|Sentenza\s+del)\s',
]

def extract_sachverhalt(text: str, language: str) -> str:
    """Extract Sachverhalt section from decision text."""
    if not text or language not in SACHVERHALT_PATTERNS:
        return ""
    
    text_norm = text.replace('\r\n', '\n').replace('\r', '\n')
    patterns = SACHVERHALT_PATTERNS[language]
    
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
    """Extract individual paragraphs from Sachverhalt section."""
    sachverhalt_text = extract_sachverhalt(text, language)
    if not sachverhalt_text:
        return []
    
    # Split by paragraph markers (numbered paragraphs or lettered)
    # Swiss BGer uses patterns like "1.", "1.1.", "A.", "B.", etc.
    paragraphs = re.split(r'\n\s*(?:\d+(?:\.\d+)*\.|[A-Z]\.)\s*', sachverhalt_text)
    # Filter out empty and very short paragraphs
    paragraphs = [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 20]
    return paragraphs

def main():
    logger.info("Extracting Sachverhalt from legal_signals_1000.jsonl...")
    
    signals = {}
    with open(SIGNALS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            signals[data['decision_id']] = data
    
    logger.info(f"Loaded {len(signals)} decisions")
    
    # Extract Sachverhalt for each decision
    updated_count = 0
    for did, sig in signals.items():
        full_text = sig.get('full_text', '')
        language = sig.get('language', 'de')
        
        sachverhalt_text = extract_sachverhalt(full_text, language)
        sachverhalt_paragraphs = extract_sachverhalt_paragraphs(full_text, language)
        
        sig['sachverhalt_text'] = sachverhalt_text
        sig['sachverhalt_paragraphs'] = sachverhalt_paragraphs
        
        if sachverhalt_text:
            updated_count += 1
    
    logger.info(f"Added Sachverhalt to {updated_count} decisions")
    
    # Save updated signals
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for sig in signals.values():
            f.write(json.dumps(sig, ensure_ascii=False) + '\n')
    
    logger.info(f"Saved updated signals to {OUTPUT_FILE}")
    
    # Print coverage stats
    with_sachverhalt = sum(1 for s in signals.values() if s.get('sachverhalt_text'))
    total_chars = sum(len(s.get('sachverhalt_text', '')) for s in signals.values())
    total_paragraphs = sum(len(s.get('sachverhalt_paragraphs', [])) for s in signals.values())
    logger.info(f"Coverage: {with_sachverhalt}/{len(signals)} ({with_sachverhalt/len(signals)*100:.1f}%)")
    logger.info(f"Total Sachverhalt chars: {total_chars}, mean: {total_chars/len(signals):.0f}")
    logger.info(f"Total paragraphs: {total_paragraphs}, mean: {total_paragraphs/len(signals):.1f}")

if __name__ == "__main__":
    main()