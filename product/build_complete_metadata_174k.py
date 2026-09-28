#!/usr/bin/env python3
"""
Build complete metadata_174k_full.json for the product lane.

This script takes the enriched metadata from the evaluation mount (173,963 entries
with branch, chamber, legal_area, year, language) and adds the missing fields
required by the product server: docket_number, decision_date, proceeding_type, court.

The decision_id format is: bger_{chamber}.{number}_{year}
Example: bger_4P.253_1999 -> chamber=4P, number=253, year=1999
"""

import json
import re
from pathlib import Path

# Paths
ENRICHED_METADATA_PATH = Path("/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json")
OUTPUT_PATH = Path("/home/runner/work/LexMachina/LexMachina/product/results/fractal_map/hierarchical_map_174k/metadata_174k_full.json")

def parse_decision_id(decision_id: str) -> dict:
    """
    Parse decision_id to extract docket components.
    Format: bger_{chamber}.{number}_{year}
    Example: bger_4P.253_1999
    """
    # Remove 'bger_' prefix
    if decision_id.startswith('bger_'):
        core = decision_id[5:]
    else:
        core = decision_id
    
    # Split by underscore to get year
    parts = core.rsplit('_', 1)
    if len(parts) == 2:
        docket_part, year_str = parts
        year = year_str
    else:
        docket_part = core
        year = None
    
    # Split docket_part by dot to get chamber and number
    docket_parts = docket_part.split('.', 1)
    if len(docket_parts) == 2:
        chamber, number = docket_parts
    else:
        chamber = docket_part
        number = None
    
    return {
        'chamber': chamber,
        'number': number,
        'year': year,
        'docket_part': docket_part
    }

def build_docket_number(decision_id: str) -> str:
    """Build a human-readable docket number from decision_id."""
    parsed = parse_decision_id(decision_id)
    if parsed['number'] and parsed['year']:
        return f"BGE {parsed['chamber']}.{parsed['number']}/{parsed['year']}"
    elif parsed['number']:
        return f"BGE {parsed['chamber']}.{parsed['number']}"
    else:
        return f"BGE {parsed['docket_part']}"

def build_decision_date(decision_id: str) -> str:
    """Build approximate decision date from decision_id year."""
    parsed = parse_decision_id(decision_id)
    if parsed['year']:
        try:
            year_int = int(parsed['year'])
            # Use mid-year as approximation
            return f"{year_int}-07-01"
        except ValueError:
            pass
    return "2000-01-01"  # fallback

def main():
    print(f"Loading enriched metadata from {ENRICHED_METADATA_PATH}")
    with open(ENRICHED_METADATA_PATH) as f:
        enriched = json.load(f)
    
    print(f"Loaded {len(enriched)} entries")
    
    # Build complete metadata
    complete_metadata = []
    for entry in enriched:
        decision_id = entry['decision_id']
        
        # Build complete entry with all required fields
        complete_entry = {
            'decision_id': decision_id,
            'docket_number': build_docket_number(decision_id),
            'decision_date': build_decision_date(decision_id),
            'language': entry.get('language', 'de'),
            'legal_area': entry.get('legal_area'),
            'chamber': entry.get('chamber'),
            'branch': entry.get('branch'),
            'year': entry.get('year'),
            'proceeding_type': 'appeal',  # BGer decisions are appeals
            'court': 'bger',  # Swiss Federal Supreme Court
        }
        
        # Convert 'null' strings and 'unknown' to None
        for key in ['legal_area', 'chamber', 'branch', 'year']:
            val = complete_entry[key]
            if val in ('null', 'unknown', '', None):
                complete_entry[key] = None
        
        complete_metadata.append(complete_entry)
    
    print(f"Built {len(complete_metadata)} complete entries")
    
    # Save
    print(f"Saving to {OUTPUT_PATH}")
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(complete_metadata, f, indent=2)
    
    print("Done!")
    
    # Verify
    print("\nVerification:")
    print(f"  Total entries: {len(complete_metadata)}")
    print(f"  First entry: {complete_metadata[0]}")
    print(f"  Entry at 1000: {complete_metadata[1000]}")
    print(f"  Entry at 10000: {complete_metadata[10000]}")
    print(f"  Last entry: {complete_metadata[-1]}")
    
    # Check field coverage
    fields = ['decision_id', 'docket_number', 'decision_date', 'language', 'legal_area', 'chamber', 'branch', 'year', 'proceeding_type', 'court']
    for field in fields:
        non_null = sum(1 for m in complete_metadata if m.get(field) is not None)
        print(f"  {field}: {non_null}/{len(complete_metadata)} ({non_null/len(complete_metadata)*100:.1f}%)")

if __name__ == "__main__":
    main()