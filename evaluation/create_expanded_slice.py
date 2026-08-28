#!/usr/bin/env python3
"""
Create expanded 1200-decision slice for evaluation v3.
Union of 1000 slice + 250 yearly core (2020-2024) = 1200 unique decisions (50 overlap).
"""

import json
from pathlib import Path

CORPUS_DIR = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_decisions(filepath):
    decisions = {}
    with open(filepath) as f:
        for line in f:
            d = json.loads(line)
            decisions[d['decision_id']] = d
    return decisions

def main():
    # Load 1000 slice
    slice_1000 = load_decisions(CORPUS_DIR / "bger_2000plus_slice_1000.jsonl")
    print(f"1000 slice: {len(slice_1000)} decisions")

    # Load yearly core (2020-2024)
    yearly = {}
    for year in ['2020', '2021', '2022', '2023', '2024']:
        yearly.update(load_decisions(CORPUS_DIR / f"bger_{year}.jsonl"))
    print(f"Yearly core: {len(yearly)} decisions")

    # Union = expanded slice
    expanded = {**slice_1000, **yearly}
    print(f"Expanded slice (union): {len(expanded)} decisions")

    # Save expanded slice
    expanded_path = OUTPUT_DIR / "bger_expanded_1200.jsonl"
    with open(expanded_path, 'w') as f:
        for d in expanded.values():
            f.write(json.dumps(d, ensure_ascii=False) + '\n')
    print(f"Saved to {expanded_path}")

    # Also save metadata only
    meta_path = OUTPUT_DIR / "bger_expanded_1200_metadata.jsonl"
    with open(meta_path, 'w') as f:
        for d in expanded.values():
            meta = {k: v for k, v in d.items() if k != 'full_text'}
            f.write(json.dumps(meta, ensure_ascii=False) + '\n')
    print(f"Saved metadata to {meta_path}")

    # Statistics
    languages = {}
    branches = {}
    years = {}
    for d in expanded.values():
        languages[d.get('language', 'unknown')] = languages.get(d.get('language', 'unknown'), 0) + 1
        branches[d.get('chamber', 'unknown')] = branches.get(d.get('chamber', 'unknown'), 0) + 1
        years[d.get('decision_date', 'unknown')[:4]] = years.get(d.get('decision_date', 'unknown')[:4], 0) + 1

    print(f"\nLanguage distribution: {languages}")
    print(f"Branch distribution: {branches}")
    print(f"Year distribution: {years}")

    # Save stats
    stats = {
        "total_decisions": len(expanded),
        "languages": languages,
        "branches": branches,
        "years": years,
        "overlap_1000_yearly": len(set(slice_1000.keys()) & set(yearly.keys()))
    }
    with open(OUTPUT_DIR / "expanded_slice_stats.json", 'w') as f:
        json.dump(stats, f, indent=2)

if __name__ == "__main__":
    main()