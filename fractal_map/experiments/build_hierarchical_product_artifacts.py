#!/usr/bin/env python3
"""
Build Product Integration Artifacts for Constrained Hierarchical Leiden
======================================================================
Generates the artifact structure needed for product integration:
- cluster_metadata.json: Legal context per cluster (branch, area, chamber, language)
- zoom_mappings.json: Bidirectional parent-child navigation
- decision_clusters.json: Decision-to-cluster index (decision_id -> {coarse, fine})
- labels_coarse.npy, labels_fine.npy: Cluster assignments for rendering
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
import argparse

BASE = Path('/home/runner/work/LexMachina/LexMachina')
RESULTS_DIR = BASE / 'results/fractal_map/constrained_hierarchical_tests'
OUTPUT_BASE = BASE / 'results/fractal_map/hierarchical_product_integration'
METADATA_PATH = Path('/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json')

MODE_FILES = {
    "full_text_tfidf_light": "constrained_hierarchical_174k_full_20260926.json",
    "regeste_tfidf": "constrained_hierarchical_174k_regeste_20260926.json",
    "regeste_full_text_hybrid_0.5": "constrained_hierarchical_174k_hybrid05_20260926.json",
    "regeste_full_text_hybrid_0.7": "constrained_hierarchical_174k_hybrid07_20260926.json",
}

# Mode IDs for product registry
MODE_IDS = {
    "full_text_tfidf_light": "hierarchical_full_text_tfidf",
    "regeste_tfidf": "hierarchical_regeste_tfidf",
    "regeste_full_text_hybrid_0.5": "hierarchical_regeste_full_text_hybrid_0.5",
    "regeste_full_text_hybrid_0.7": "hierarchical_regeste_full_text_hybrid_0.7",
}


def load_metadata():
    with open(METADATA_PATH) as f:
        return json.load(f)


def build_coarse_labels(n_docs, cluster_info):
    """Build coarse label array from cluster_info."""
    labels = np.full(n_docs, -1, dtype=int)
    # We need to reconstruct the assignment from cluster_info
    # The cluster_info has size and coarse_id but not the actual doc indices
    # We need to run the clustering again OR store the labels during clustering
    # For now, this is a limitation - we need the actual label arrays
    return labels


def build_fine_labels(n_docs, cluster_info):
    labels = np.full(n_docs, -1, dtype=int)
    return labels


def compute_cluster_metadata(labels, metadata, cluster_ids, level_name):
    """Compute legal context metadata for each cluster."""
    cluster_meta = {}
    for cid in cluster_ids:
        mask = labels == cid
        indices = np.where(mask)[0]
        if len(indices) == 0:
            continue
        
        # Collect metadata
        branches = [metadata[i].get('branch') for i in indices]
        areas = [metadata[i].get('legal_area') for i in indices]
        chambers = [metadata[i].get('chamber') for i in indices]
        languages = [metadata[i].get('language') for i in indices]
        decision_ids = [metadata[i].get('decision_id') for i in indices]
        years = [metadata[i].get('year') for i in indices]
        
        # Filter valid
        branches = [b for b in branches if b and b != 'unknown' and b != 'null']
        areas = [a for a in areas if a and a != 'unknown' and a != 'null']
        chambers = [c for c in chambers if c and c != 'unknown' and c != 'null']
        languages = [l for l in languages if l and l != 'unknown' and l != 'null']
        years = [y for y in years if y is not None]
        
        cluster_meta[str(cid)] = {
            'cluster_id': int(cid),
            'level': level_name,
            'size': int(len(indices)),
            'dominant_branch': Counter(branches).most_common(1)[0][0] if branches else None,
            'branch_purity': round(Counter(branches).most_common(1)[0][1] / len(branches), 4) if branches else None,
            'branch_distribution': dict(Counter(branches)),
            'dominant_area': Counter(areas).most_common(1)[0][0] if areas else None,
            'area_purity': round(Counter(areas).most_common(1)[0][1] / len(areas), 4) if areas else None,
            'area_distribution': dict(Counter(areas)),
            'dominant_chamber': Counter(chambers).most_common(1)[0][0] if chambers else None,
            'chamber_distribution': dict(Counter(chambers)),
            'dominant_language': Counter(languages).most_common(1)[0][0] if languages else None,
            'language_distribution': dict(Counter(languages)),
            'year_range': [min(years), max(years)] if years else None,
            'decision_ids': decision_ids[:100],  # Sample for inspection
        }
    return cluster_meta


def build_zoom_mappings(coarse_labels, fine_labels):
    """Build bidirectional parent-child zoom mappings."""
    child_to_parent = {}
    parent_to_children = defaultdict(list)
    
    for fid in np.unique(fine_labels[fine_labels != -1]):
        mask = fine_labels == fid
        parent_vals = coarse_labels[mask]
        parent_vals = parent_vals[parent_vals != -1]
        if len(parent_vals) > 0:
            parent = int(Counter(parent_vals.tolist()).most_common(1)[0][0])
            child_to_parent[str(fid)] = parent
            parent_to_children[str(parent)].append(int(fid))
    
    return {
        'child_to_parent': child_to_parent,
        'parent_to_children': {k: v for k, v in parent_to_children.items()},
    }


def build_decision_clusters(metadata, coarse_labels, fine_labels):
    """Build decision_id -> {coarse, fine} mapping."""
    decision_clusters = {}
    for i, m in enumerate(metadata):
        did = m.get('decision_id')
        if did:
            decision_clusters[did] = {
                'coarse': int(coarse_labels[i]) if coarse_labels[i] != -1 else None,
                'fine': int(fine_labels[i]) if fine_labels[i] != -1 else None,
            }
    return decision_clusters


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', required=True, choices=list(MODE_FILES.keys()))
    args = parser.parse_args()
    
    mode_name = args.mode
    result_file = MODE_FILES[mode_name]
    mode_id = MODE_IDS[mode_name]
    
    print(f"Building product artifacts for {mode_name} -> {mode_id}")
    
    # Load constrained hierarchical result
    with open(RESULTS_DIR / result_file) as f:
        hier_data = json.load(f)
    
    # Load metadata
    meta = load_metadata()
    n_docs = hier_data['sample_size']
    
    # We need the actual label arrays. The hierarchical result has cluster_info with sizes
    # but not the actual doc->cluster mapping. We need to regenerate by running the algorithm
    # OR we need to have saved the labels during the original run.
    # Let's check if labels are saved elsewhere...
    
    # Actually, the original constrained_hierarchical_leiden.py doesn't save labels.
    # We need to re-run the clustering to get the labels.
    # But that's expensive. Let me check if there's a cached version.
    
    # For now, let's note this limitation and create a structure that shows what's needed
    output_dir = OUTPUT_BASE / mode_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a summary of what would be needed
    summary = {
        'mode_id': mode_id,
        'source_mode': mode_name,
        'source_result': result_file,
        'sample_size': n_docs,
        'config': hier_data['config'],
        'coarse': hier_data['coarse'],
        'hierarchical_fine': hier_data['hierarchical'],
        'zoom_coherence': hier_data['zoom_coherence'],
        'note': 'Label arrays not stored in original run. Need to re-run constrained hierarchical Leiden with label persistence to generate product artifacts.',
        'required_artifacts': [
            'labels_coarse.npy',
            'labels_fine.npy',
            'cluster_metadata.json',
            'zoom_mappings.json',
            'decision_clusters.json',
        ],
    }
    
    summary_path = output_dir / 'build_summary.json'
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    
    print(f"  Build summary written to {summary_path}")
    print(f"  Note: Label arrays need to be generated by re-running constrained hierarchical Leiden with persistence")


if __name__ == '__main__':
    main()