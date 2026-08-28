#!/usr/bin/env python3
"""
Create combined full corpus from all canonical files (deduplicated by decision_id).
"""

import json
from pathlib import Path
from collections import OrderedDict
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

CANONICAL_DIR = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
OUTPUT_FILE = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/bger_full_corpus.jsonl")

# Files to combine (prioritize slice_1000 as it has 2000+ coverage, then yearly for 2020-2024)
CORPUS_FILES = [
    "bger_2000plus_slice_1000.jsonl",      # 1000 decisions from 2000+
    "bger_2020.jsonl",                      # 50 decisions
    "bger_2021.jsonl",                      # 50 decisions
    "bger_2022.jsonl",                      # 50 decisions
    "bger_2023.jsonl",                      # 50 decisions
    "bger_2024.jsonl",                      # 50 decisions
    # Skip eval/test files to avoid contamination
]

def main():
    logger.info("=" * 60)
    logger.info("Creating combined full corpus (deduplicated)")
    logger.info("=" * 60)
    
    all_decisions = OrderedDict()  # Preserves insertion order, deduplicates by key
    
    for fname in CORPUS_FILES:
        fpath = CANONICAL_DIR / fname
        if not fpath.exists():
            logger.warning(f"File not found: {fpath}")
            continue
            
        count = 0
        with open(fpath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                decision = json.loads(line)
                did = decision.get('decision_id', '')
                if did and did not in all_decisions:
                    all_decisions[did] = decision
                    count += 1
        logger.info(f"  {fname}: added {count} new decisions (total: {len(all_decisions)})")
    
    # Save combined corpus
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for decision in all_decisions.values():
            f.write(json.dumps(decision, ensure_ascii=False) + '\n')
    
    logger.info(f"\nCombined corpus saved to {OUTPUT_FILE}")
    logger.info(f"Total unique decisions: {len(all_decisions)}")
    
    # Statistics
    languages = {}
    years = {}
    branches = {}
    for d in all_decisions.values():
        lang = d.get('language', 'unknown')
        languages[lang] = languages.get(lang, 0) + 1
        
        year = d.get('year', 'unknown')
        years[year] = years.get(year, 0) + 1
        
        branch = d.get('branch', 'unknown')
        branches[branch] = branches.get(branch, 0) + 1
    
    logger.info(f"Language distribution: {languages}")
    logger.info(f"Year distribution: {dict(sorted(years.items()))}")
    logger.info(f"Branch distribution: {branches}")
    
    return all_decisions

if __name__ == "__main__":
    main()
