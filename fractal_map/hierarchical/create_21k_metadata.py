#!/usr/bin/env python3
"""
Create 21k metadata from ALL corpus JSONL files (bge_1900-2026 + bge_.jsonl).
"""

import json
from pathlib import Path
from collections import Counter
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

CORPUS_DIR = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/hierarchical_map_21k")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    logger.info("=== Creating 21k Metadata (All Available Corpus) ===")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    metadata = []
    year_counts = Counter()
    lang_counts = Counter()
    branch_counts = Counter()
    area_counts = Counter()
    chamber_counts = Counter()
    
    # Process ALL bge_*.jsonl files
    year_files = sorted(CORPUS_DIR.glob("bge_*.jsonl"))
    logger.info(f"Found {len(year_files)} year files")
    
    for year_file in year_files:
        logger.info(f"Processing {year_file.name}...")
        
        with open(year_file) as f:
            for line in f:
                try:
                    d = json.loads(line)
                    
                    # Extract year from decision_date
                    year = None
                    if d.get('decision_date'):
                        try:
                            year = int(d['decision_date'][:4])
                        except:
                            pass
                    
                    # Fallback: extract from filename
                    if year is None:
                        fname = year_file.stem.replace("bge_", "")
                        try:
                            year = int(fname)
                        except:
                            year = 0
                    
                    year_counts[year] += 1
                    lang_counts[d.get('language', 'unknown')] += 1
                    branch_counts[d.get('branch', 'unknown')] += 1
                    area_counts[d.get('legal_area', 'unknown')] += 1
                    chamber_counts[d.get('chamber', 'unknown')] += 1
                    
                    # Create metadata entry
                    meta = {
                        'decision_id': d.get('decision_id', ''),
                        'docket_number': d.get('docket_number', ''),
                        'decision_date': d.get('decision_date', ''),
                        'language': d.get('language', 'unknown'),
                        'legal_area': d.get('legal_area'),
                        'chamber': d.get('chamber'),
                        'branch': d.get('branch'),
                        'year': year,
                        'proceeding_type': d.get('proceeding_type'),
                        'court': d.get('court', 'bge'),
                    }
                    metadata.append(meta)
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON decode error in {year_file.name}: {e}")
                    continue
    
    logger.info(f"Total decisions: {len(metadata)}")
    logger.info(f"Years: {dict(sorted(year_counts.items()))}")
    logger.info(f"Languages: {dict(lang_counts)}")
    logger.info(f"Branches: {dict(branch_counts)}")
    logger.info(f"Areas (top 10): {dict(area_counts.most_common(10))}")
    logger.info(f"Chambers (top 10): {dict(chamber_counts.most_common(10))}")
    
    # Save metadata
    output_path = OUTPUT_DIR / "metadata_21k.json"
    with open(output_path, 'w') as f:
        json.dump(metadata, f)
    
    logger.info(f"Metadata saved to {output_path}")
    
    # Also save summary
    summary = {
        "run_id": f"metadata_21k_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "n_decisions": len(metadata),
        "year_distribution": dict(sorted(year_counts.items())),
        "language_distribution": dict(lang_counts),
        "branch_distribution": dict(branch_counts),
        "area_distribution_top20": dict(area_counts.most_common(20)),
        "chamber_distribution_top20": dict(chamber_counts.most_common(20)),
        "corpus_source": "All bge_*.jsonl from /tmp/lex_accepted/corpus/corpus/normalization/canonical",
        "direction_version": 25,
        "note": "Subset of full 174k corpus (local JSONL files only); full 174k on HuggingFace parquet",
    }
    
    summary_path = OUTPUT_DIR / "metadata_21k_summary.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"Summary saved to {summary_path}")
    logger.info("=== 21k metadata creation complete ===")
    
    return metadata

if __name__ == "__main__":
    main()
