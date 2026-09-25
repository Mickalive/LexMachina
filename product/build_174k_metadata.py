#!/usr/bin/env python3
"""
Build correct metadata_174k_full.json from bger corpus files in glob order.
This matches the embedding order used in build_174k_legal_tfidf_embeddings.py
"""
import json
import glob
from pathlib import Path

CORPUS_DIR = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
OUTPUT_PATH = Path("/tmp/lex_accepted/fractal-map/results/fractal_map/hierarchical_map_174k/metadata_174k_full_correct.json")

# Get files in the same order as build script: sorted(CORPUS_DIR.glob('bger_*.jsonl'))
files = sorted(glob.glob(str(CORPUS_DIR / "bger_*.jsonl")))

metadata = []
total = 0

for fpath in files:
    fname = Path(fpath).name
    with open(fpath) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                # Extract metadata fields matching the schema
                entry = {
                    "decision_id": d.get("decision_id", ""),
                    "docket_number": d.get("docket_number", ""),
                    "decision_date": d.get("decision_date", ""),
                    "language": d.get("language", "de"),
                    "legal_area": d.get("legal_area"),
                    "chamber": d.get("chamber"),
                    "branch": d.get("branch"),
                    "year": d.get("year"),
                    "proceeding_type": d.get("proceeding_type"),
                    "court": d.get("court", "bger"),
                }
                metadata.append(entry)
                total += 1
            except json.JSONDecodeError:
                continue

print(f"Total entries: {total}")
print(f"First: {metadata[0]}")
print(f"Last: {metadata[-1]}")

# Save
with open(OUTPUT_PATH, 'w') as f:
    json.dump(metadata, f, ensure_ascii=False)

print(f"Saved to {OUTPUT_PATH}")
