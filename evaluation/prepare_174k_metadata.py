#!/usr/bin/env python3
"""
Prepare 174k metadata for evaluation lane.
Combines all year-split bger_*.jsonl files into a single metadata file
or creates an index for efficient loading.
"""
import json
import os
from pathlib import Path
from collections import Counter
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

CANONICAL_DIR = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/data/174k")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Year files for 2000-2026 (excluding eval/test files)
YEAR_FILES = [f"bger_{year}.jsonl" for year in range(2000, 2027)]

CHAMBER_TO_BRANCH = {
    "I. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
    "II. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
    "III. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
    "IV. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
    "I. Zivilrechtliche Abteilung": "zivilrecht",
    "II. Zivilrechtliche Abteilung": "zivilrecht",
    "I. Strafrechtliche Abteilung": "strafrecht",
    "II. Strafrechtliche Abteilung": "strafrecht",
    "II. sozialrechtliche Abteilung": "sozialversicherungsrecht",
    "IIe Cour de droit social": "sozialversicherungsrecht",
    "Ire Cour de droit public": "oeffentliches_recht",
    "IIe Cour de droit public": "oeffentliches_recht",
    "Ire Cour de droit civil": "zivilrecht",
    "IIe Cour de droit civil": "zivilrecht",
    "Ire Cour de droit pénal": "strafrecht",
    "IIe Cour de droit pénal": "strafrecht",
}

def assign_branch(chamber: str) -> str:
    if not chamber:
        return "unknown"
    if chamber in CHAMBER_TO_BRANCH:
        return CHAMBER_TO_BRANCH[chamber]
    chamber_lower = chamber.lower()
    if "öffentlich" in chamber_lower or "public" in chamber_lower:
        return "oeffentliches_recht"
    if "zivil" in chamber_lower or "civil" in chamber_lower:
        return "zivilrecht"
    if "straf" in chamber_lower or "pénal" in chamber_lower or "penal" in chamber_lower:
        return "strafrecht"
    if "sozial" in chamber_lower or "social" in chamber_lower:
        return "sozialversicherungsrecht"
    return "unknown"

def process_year_file(fpath: Path, stats: dict) -> list:
    """Process a single year file, return metadata records."""
    records = []
    with open(fpath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON decode error in {fpath}: {e}")
                continue
            
            decision_id = d.get('decision_id', '')
            if not decision_id:
                continue
                
            chamber = d.get('chamber', '')
            branch = assign_branch(chamber)
            language = d.get('language', 'de')
            legal_area = d.get('legal_area', '')
            year = d.get('decision_date', '')[:4] if d.get('decision_date') else 'unknown'
            
            record = {
                'decision_id': decision_id,
                'language': language,
                'branch': branch,
                'chamber': chamber,
                'legal_area': legal_area if legal_area and legal_area != 'null' else 'unknown',
                'year': year,
            }
            records.append(record)
            
            stats['languages'][language] += 1
            stats['branches'][branch] += 1
            stats['legal_areas'][legal_area if legal_area and legal_area != 'null' else 'unknown'] += 1
            stats['years'][year] += 1
    
    return records

def main():
    logger.info("=" * 70)
    logger.info("PREPARE 174K METADATA FOR EVALUATION")
    logger.info("=" * 70)
    
    stats = {
        'languages': Counter(),
        'branches': Counter(),
        'legal_areas': Counter(),
        'years': Counter(),
    }
    
    all_records = []
    total_decisions = 0
    
    for fname in YEAR_FILES:
        fpath = CANONICAL_DIR / fname
        if not fpath.exists():
            logger.warning(f"File not found: {fpath}")
            continue
        
        logger.info(f"Processing {fname}...")
        records = process_year_file(fpath, stats)
        all_records.extend(records)
        total_decisions += len(records)
        logger.info(f"  Added {len(records)} decisions (total: {total_decisions})")
    
    logger.info(f"\nTotal decisions processed: {total_decisions}")
    logger.info(f"Language distribution: {dict(stats['languages'])}")
    logger.info(f"Branch distribution: {dict(stats['branches'])}")
    logger.info(f"Unique legal areas: {len(stats['legal_areas'])}")
    logger.info(f"Year range: {min(stats['years'].keys())} - {max(stats['years'].keys())}")
    
    # Save as JSONL for streaming
    output_jsonl = OUTPUT_DIR / "metadata_174k.jsonl"
    with open(output_jsonl, 'w', encoding='utf-8') as f:
        for record in all_records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    logger.info(f"Saved metadata JSONL to {output_jsonl}")
    
    # Also save as JSON array for tools that need it
    output_json = OUTPUT_DIR / "metadata_174k.json"
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved metadata JSON to {output_json}")
    
    # Save statistics
    stats_output = OUTPUT_DIR / "metadata_stats.json"
    with open(stats_output, 'w', encoding='utf-8') as f:
        json.dump({
            'total_decisions': total_decisions,
            'languages': dict(stats['languages']),
            'branches': dict(stats['branches']),
            'legal_areas': dict(stats['legal_areas']),
            'years': dict(stats['years']),
            'unique_legal_areas': len(stats['legal_areas']),
        }, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved statistics to {stats_output}")
    
    logger.info("=" * 70)
    logger.info("METADATA PREPARATION COMPLETE")
    logger.info("=" * 70)

if __name__ == "__main__":
    main()
