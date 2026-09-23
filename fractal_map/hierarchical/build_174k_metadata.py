#!/usr/bin/env python3
"""
Build full metadata for 174k-scale (or local 21k) corpus with all fields:
branch, legal_area, chamber, proceeding_type, etc.
Uses local JSONL files from /tmp/lex_accepted/corpus/corpus/normalization/canonical/
"""

import json
from pathlib import Path
from collections import Counter
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

CORPUS_DIR = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/hierarchical_map_174k")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

METADATA_OUTPUT = OUTPUT_DIR / "metadata_174k_full.json"
SUMMARY_OUTPUT = OUTPUT_DIR / "metadata_174k_full_summary.json"


def build_full_metadata():
    """Build complete metadata from all bge_*.jsonl files."""
    metadata = []
    
    year_files = sorted(CORPUS_DIR.glob("bge_*.jsonl"))
    logger.info(f"Found {len(year_files)} year files")
    
    for year_file in year_files:
        with open(year_file) as f:
            for line in f:
                d = json.loads(line)
                # Ensure all required fields exist
                meta = {
                    'decision_id': d.get('decision_id', ''),
                    'docket_number': d.get('docket_number', ''),
                    'decision_date': d.get('decision_date', ''),
                    'language': d.get('language', ''),
                    'legal_area': d.get('legal_area'),
                    'chamber': d.get('chamber'),
                    'branch': d.get('branch'),
                    'year': d.get('year'),
                    'proceeding_type': d.get('proceeding_type'),
                    'court': d.get('court', 'bge'),
                }
                metadata.append(meta)
    
    logger.info(f"Loaded {len(metadata)} decisions")
    return metadata


def save_metadata(metadata):
    """Save full metadata and summary."""
    logger.info(f"Saving metadata to {METADATA_OUTPUT}")
    with open(METADATA_OUTPUT, 'w') as f:
        json.dump(metadata, f)
    
    # Build summary
    year_dist = Counter(m.get('year') for m in metadata if m.get('year'))
    lang_dist = Counter(m.get('language') for m in metadata if m.get('language'))
    branch_dist = Counter(m.get('branch') for m in metadata if m.get('branch'))
    area_dist = Counter(m.get('legal_area') for m in metadata if m.get('legal_area'))
    chamber_dist = Counter(m.get('chamber') for m in metadata if m.get('chamber'))
    proc_dist = Counter(m.get('proceeding_type') for m in metadata if m.get('proceeding_type'))
    
    summary = {
        "run_id": f"metadata_174k_full_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "n_decisions": len(metadata),
        "year_distribution": {str(k): int(v) for k, v in year_dist.most_common()},
        "language_distribution": {str(k): int(v) for k, v in lang_dist.most_common()},
        "branch_distribution": {str(k): int(v) for k, v in branch_dist.most_common(20)},
        "area_distribution_top20": {str(k): int(v) for k, v in area_dist.most_common(20)},
        "chamber_distribution_top20": {str(k): int(v) for k, v in chamber_dist.most_common(20)},
        "proceeding_type_distribution": {str(k): int(v) for k, v in proc_dist.most_common(10)},
        "corpus_source": "All bge_*.jsonl from /tmp/lex_accepted/corpus/corpus/normalization/canonical",
        "direction_version": 25,
        "note": "Full metadata with all fields extracted from corpus JSONL. Local subset (21k); full 174k on HuggingFace parquet.",
    }
    
    logger.info(f"Saving summary to {SUMMARY_OUTPUT}")
    with open(SUMMARY_OUTPUT, 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"Total decisions: {len(metadata)}")
    logger.info(f"Languages: {dict(lang_dist)}")
    logger.info(f"Branch coverage: {sum(1 for m in metadata if m.get('branch') and m['branch'] != 'null')}/{len(metadata)}")
    logger.info(f"Legal area coverage: {sum(1 for m in metadata if m.get('legal_area') and m['legal_area'] != 'null')}/{len(metadata)}")
    logger.info(f"Chamber coverage: {sum(1 for m in metadata if m.get('chamber') and m['chamber'] != 'null')}/{len(metadata)}")
    
    return summary


def main():
    logger.info("=== Building Full Metadata for 174k-scale Corpus ===")
    metadata = build_full_metadata()
    summary = save_metadata(metadata)
    logger.info("=== Metadata build complete ===")
    return summary


if __name__ == "__main__":
    main()