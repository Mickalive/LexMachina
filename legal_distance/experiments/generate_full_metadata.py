#!/usr/bin/env python3
"""
Generate full metadata_174k.json from yearly canonical JSONL files.
"""
import json
from pathlib import Path

CANONICAL_DIR = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
OUTPUT_PATH = Path("/tmp/lex_accepted/product/product/results/fractal_map/hierarchical_map_174k/metadata_174k_full.json")

# Year files to process (2000 onward per product scope)
YEAR_FILES = sorted(CANONICAL_DIR.glob("bger_20[0-9][0-9].jsonl"))

all_metadata = []

for year_file in YEAR_FILES:
    year = int(year_file.stem.split('_')[1])
    print(f"Processing {year_file.name}...")
    with open(year_file, 'r') as f:
        for line in f:
            d = json.loads(line)
            # Extract metadata fields needed by compute script
            meta = {
                "decision_id": d.get("decision_id"),
                "docket_number": d.get("docket_number"),
                "decision_date": d.get("decision_date"),
                "language": d.get("language"),
                "legal_area": d.get("legal_area"),
                "chamber": d.get("chamber"),
                "branch": d.get("branch"),
                "year": year,
                "proceeding_type": d.get("proceeding_type"),
                "court": d.get("court"),
            }
            all_metadata.append(meta)

print(f"Total decisions: {len(all_metadata)}")

# Save
with open(OUTPUT_PATH, 'w') as f:
    json.dump(all_metadata, f, ensure_ascii=False)

print(f"Saved to {OUTPUT_PATH}")
