#!/usr/bin/env python3
"""
Generate synthetic Jurivoc labels for the 1000-decision corpus slice.
Maps legal_area/branch to Jurivoc descriptors for benchmarking.
"""

import json
import sys
from pathlib import Path

# Load the Jurivoc taxonomy
with open('/home/runner/work/LexMachina/LexMachina/evaluation/jurivoc/jurivoc_taxonomy.json', 'r') as f:
    taxonomy = json.load(f)

mapping_rules = taxonomy['corpus_mapping']['mapping_rules']
top_level = taxonomy['jurivoc_framework']['top_level_categories']
second_level = taxonomy['jurivoc_framework']['second_level']

# Build full descriptor hierarchy
all_descriptors = {}
for k, v in top_level.items():
    all_descriptors[k] = v
for k, v in second_level.items():
    all_descriptors[k] = v

# Add trilingual labels
def get_descriptor_labels(desc_id):
    """Get trilingual labels for a descriptor."""
    if desc_id in top_level:
        return {
            'de': top_level[desc_id]['de'],
            'fr': top_level[desc_id]['fr'],
            'it': top_level[desc_id]['it']
        }
    elif desc_id in second_level:
        return {
            'de': second_level[desc_id]['de'],
            'fr': second_level[desc_id]['fr'],
            'it': second_level[desc_id]['it']
        }
    return {'de': '', 'fr': '', 'it': ''}

def get_hierarchy_path(desc_id):
    """Get full hierarchy path from root to descriptor."""
    if desc_id in top_level:
        return [desc_id]
    elif desc_id in second_level:
        parent = second_level[desc_id]['parent']
        return [parent, desc_id]
    return []

def map_decision_to_jurivoc(decision):
    """Map a decision to Jurivoc descriptors based on legal_area/branch."""
    legal_area = decision.get('legal_area', '')
    branch = decision.get('branch', '')
    regeste = decision.get('regeste', '') or ''
    
    descriptors = []
    
    # Direct mapping from legal_area
    if legal_area in mapping_rules:
        rule = mapping_rules[legal_area]
        primary = rule['primary']
        descriptors.append(primary)
        descriptors.extend(rule.get('secondary', []))
    else:
        # Fallback to branch-based mapping
        branch_to_primary = {
            'oeffentliches_recht': '1',
            'zivilrecht': '2',
            'strafrecht': '3',
            'sozialversicherungsrecht': '4'
        }
        if branch in branch_to_primary:
            descriptors.append(branch_to_primary[branch])
    
    # Deduplicate while preserving order
    seen = set()
    unique_descriptors = []
    for d in descriptors:
        if d not in seen:
            seen.add(d)
            unique_descriptors.append(d)
    
    # Limit to max 3 descriptors per decision
    return unique_descriptors[:3]

def main():
    corpus_path = Path('/tmp/lex_accepted/corpus/corpus/normalization/canonical/bger_2000plus_slice_1000.jsonl')
    output_path = Path('/home/runner/work/LexMachina/LexMachina/evaluation/jurivoc/jurivoc_labels.jsonl')
    
    results = []
    with open(corpus_path, 'r') as f:
        for line in f:
            decision = json.loads(line)
            descriptors = map_decision_to_jurivoc(decision)
            
            # Build full label info
            descriptor_info = []
            for desc_id in descriptors:
                labels = get_descriptor_labels(desc_id)
                hierarchy = get_hierarchy_path(desc_id)
                descriptor_info.append({
                    'descriptor_id': desc_id,
                    'labels': labels,
                    'hierarchy': hierarchy
                })
            
            result = {
                'decision_id': decision['decision_id'],
                'branch': decision.get('branch', ''),
                'legal_area': decision.get('legal_area', ''),
                'jurivoc_descriptors': descriptor_info,
                'descriptor_ids': [d['descriptor_id'] for d in descriptor_info]
            }
            results.append(result)
    
    with open(output_path, 'w') as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    
    print(f"Generated Jurivoc labels for {len(results)} decisions")
    print(f"Output: {output_path}")
    
    # Statistics
    desc_counts = {}
    for r in results:
        for d in r['descriptor_ids']:
            desc_counts[d] = desc_counts.get(d, 0) + 1
    
    print("\nDescriptor distribution:")
    for desc_id, count in sorted(desc_counts.items(), key=lambda x: -x[1])[:20]:
        labels = get_descriptor_labels(desc_id)
        print(f"  {desc_id}: {count} ({labels['de']})")

if __name__ == '__main__':
    main()