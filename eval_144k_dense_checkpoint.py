#!/usr/bin/env python3
"""
Evaluate constrained hierarchical Leiden on 144k dense embeddings checkpoints (years 2000-2021).
This tests the hierarchical pipeline at the largest available dense embedding scale.
Results are for PIPELINE VALIDATION only (years 2003-2021 are PENDING AUDIT).
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict
import igraph as ig
import leidenalg
from sklearn.neighbors import kneighbors_graph

# ============================================================
# FROZEN CONFIGURATION (same as 28k/15yr validation)
# ============================================================
CHECKPOINT_DIR = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints")
METADATA_PATH = Path("/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json")

# Years available as checkpoints (2000-2021 = 22 years, 144,443 decisions)
AVAILABLE_YEARS = [str(y) for y in range(2000, 2022)]

# Constrained hierarchical Leiden config (validated at 28k, tested at 100k)
CONFIGS = [
    {
        "name": "coarse_0.5_fixed2.0_min20",
        "coarse_res": 0.5,
        "base_sub_res": 2.0,
        "min_cluster_size": 20,
        "max_subclusters_per_parent": 20,
        "adaptive_sub_res": False
    },
    {
        "name": "coarse_0.5_fixed3.0_min20",
        "coarse_res": 0.5,
        "base_sub_res": 3.0,
        "min_cluster_size": 20,
        "max_subclusters_per_parent": 20,
        "adaptive_sub_res": False
    },
    {
        "name": "coarse_0.25_fixed2.0_min20",
        "coarse_res": 0.25,
        "base_sub_res": 2.0,
        "min_cluster_size": 20,
        "max_subclusters_per_parent": 20,
        "adaptive_sub_res": False
    }
]

K = 15
SEED = 42

OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/144k_checkpoint_validation")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_checkpoints():
    """Load and concatenate embeddings and metadata from year checkpoints."""
    print("Loading checkpoint embeddings and metadata...")
    
    all_embeddings = []
    all_metadata = []
    year_offsets = {}
    
    for year in AVAILABLE_YEARS:
        emb_path = CHECKPOINT_DIR / f"embeddings_{year}.npy"
        meta_path = CHECKPOINT_DIR / f"metadata_{year}.json"
        
        if not emb_path.exists() or not meta_path.exists():
            print(f"  WARNING: Missing files for {year}")
            continue
            
        embeddings = np.load(emb_path)
        with open(meta_path) as f:
            metadata = json.load(f)
        
        year_offsets[year] = {
            "start": len(all_metadata),
            "count": len(metadata),
            "embedding_shape": embeddings.shape
        }
        
        all_embeddings.append(embeddings)
        all_metadata.extend(metadata)
        print(f"  {year}: {len(metadata)} decisions, embeddings shape {embeddings.shape}")
    
    combined_embeddings = np.vstack(all_embeddings)
    print(f"\nTotal: {len(all_metadata)} decisions, combined embeddings shape {combined_embeddings.shape}")
    return combined_embeddings, all_metadata, year_offsets


def load_full_metadata():
    """Load full 174k metadata and filter to available years."""
    print("Loading full metadata...")
    with open(METADATA_PATH) as f:
        full_metadata = json.load(f)
    
    # Filter to years 2000-2021
    filtered = [m for m in full_metadata if str(m.get('year')) in AVAILABLE_YEARS]
    print(f"Filtered metadata: {len(filtered)} decisions (years 2000-2021)")
    
    # Check branch/area coverage
    branch_known = sum(1 for m in filtered if m.get('branch') and m['branch'] not in ('unknown', 'null'))
    area_known = sum(1 for m in filtered if m.get('legal_area') and m['legal_area'] not in ('unknown', 'null'))
    print(f"  Branch known: {branch_known}/{len(filtered)} ({branch_known/len(filtered)*100:.1f}%)")
    print(f"  Area known: {area_known}/{len(filtered)} ({area_known/len(filtered)*100:.1f}%)")
    
    return filtered


def leiden_clustering(embeddings, resolution=1.0, k=K, seed=SEED):
    """Run Leiden clustering on embeddings."""
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normalized = embeddings / norms
    n = len(embeddings)
    k_actual = min(k, n - 1)
    graph = kneighbors_graph(normalized, n_neighbors=k_actual, metric='euclidean',
                             mode='connectivity', include_self=False)
    graph = graph.maximum(graph.T)
    sources, targets = graph.nonzero()
    weights = graph.data
    edges = list(zip(sources.tolist(), targets.tolist()))
    g = ig.Graph()
    g.add_vertices(graph.shape[0])
    g.add_edges(edges)
    g.es['weight'] = weights.tolist()
    partition = leidenalg.find_partition(
        g, leidenalg.RBConfigurationVertexPartition,
        weights='weight', resolution_parameter=resolution, seed=seed)
    return np.array(partition.membership)


def constrained_hierarchical_leiden(embeddings, metadata, config):
    """Run constrained hierarchical Leiden with given config."""
    coarse_res = config['coarse_res']
    base_sub_res = config['base_sub_res']
    min_cluster_size = config['min_cluster_size']
    max_subclusters = config['max_subclusters_per_parent']
    
    print(f"\n  Running constrained hierarchical Leiden:")
    print(f"    coarse_res={coarse_res}, base_sub_res={base_sub_res}, min_cluster_size={min_cluster_size}")
    
    # Coarse clustering
    coarse_labels = leiden_clustering(embeddings, resolution=coarse_res)
    unique_coarse = np.unique(coarse_labels[coarse_labels != -1])
    print(f"    Coarse clusters: {len(unique_coarse)}")
    
    # Fine clustering per coarse cluster
    fine_labels = np.full(len(embeddings), -1, dtype=int)
    fine_cluster_id = 0
    coarse_to_fine = defaultdict(list)
    
    for coarse_id in unique_coarse:
        mask = coarse_labels == coarse_id
        indices = np.where(mask)[0]
        
        if len(indices) < min_cluster_size:
            fine_labels[indices] = fine_cluster_id
            coarse_to_fine[int(coarse_id)].append(fine_cluster_id)
            fine_cluster_id += 1
            continue
        
        subset_embeddings = embeddings[indices]
        sub_labels = leiden_clustering(subset_embeddings, resolution=base_sub_res)
        unique_sub = np.unique(sub_labels[sub_labels != -1])
        
        # Cap subclusters per parent
        if len(unique_sub) > max_subclusters:
            sub_unique, sub_counts = np.unique(sub_labels, return_counts=True)
            sorted_idx = np.argsort(sub_counts)[::-1]
            keep = sub_unique[sorted_idx[:max_subclusters]]
            for old_label in sub_unique:
                if old_label not in keep:
                    sub_labels[sub_labels == old_label] = keep[0]
            unique_sub = keep
        
        if len(unique_sub) == 1:
            fine_labels[indices] = fine_cluster_id
            coarse_to_fine[int(coarse_id)].append(fine_cluster_id)
            fine_cluster_id += 1
        else:
            for j, idx in enumerate(indices):
                fine_labels[idx] = fine_cluster_id + sub_labels[j]
            child_labels = list(range(fine_cluster_id, fine_cluster_id + len(unique_sub)))
            coarse_to_fine[int(coarse_id)].extend(child_labels)
            fine_cluster_id += len(unique_sub)
    
    print(f"    Fine clusters: {fine_cluster_id}")
    return coarse_labels, fine_labels, coarse_to_fine


def compute_legal_purity(labels, metadata, field, min_size=3):
    """Compute weighted legal purity for clusters."""
    purities = []
    weights = []
    per_cluster = {}
    
    for label in np.unique(labels[labels != -1]):
        mask = labels == label
        indices = np.where(mask)[0]
        if len(indices) < min_size:
            continue
        values = [metadata[i].get(field) for i in indices]
        values = [v for v in values if v and v not in ('unknown', 'null')]
        if not values:
            continue
        counts = Counter(values)
        dominant = counts.most_common(1)[0]
        purity = dominant[1] / len(values)
        purities.append(purity)
        weights.append(len(indices))
        per_cluster[int(label)] = {
            'purity': purity,
            'size': len(indices),
            'dominant': dominant[0],
            'distribution': dict(counts)
        }
    
    weighted_purity = np.average(purities, weights=weights) if purities else 0.0
    return weighted_purity, per_cluster


def compute_zoom_metrics(coarse_labels, fine_labels, metadata, field='branch', min_size=3):
    """Compute zoom improvement metrics."""
    improvements = []
    n_parents = 0
    parent_details = {}
    
    child_to_parent = {}
    for fine_id in np.unique(fine_labels[fine_labels != -1]):
        fine_mask = fine_labels == fine_id
        parent_labels = coarse_labels[fine_mask]
        parent_labels_valid = parent_labels[parent_labels != -1]
        if len(parent_labels_valid) > 0:
            child_to_parent[int(fine_id)] = int(Counter(parent_labels_valid.tolist()).most_common(1)[0][0])
    
    for coarse_id in np.unique(coarse_labels[coarse_labels != -1]):
        coarse_mask = coarse_labels == coarse_id
        coarse_indices = np.where(coarse_mask)[0]
        if len(coarse_indices) < min_size:
            continue
        coarse_values = [metadata[i].get(field) for i in coarse_indices]
        coarse_values = [v for v in coarse_values if v and v not in ('unknown', 'null')]
        if not coarse_values:
            continue
        coarse_purity = Counter(coarse_values).most_common(1)[0][1] / len(coarse_values)
        
        child_clusters = [fc for fc, pc in child_to_parent.items() if pc == coarse_id]
        child_purities = []
        for fc in child_clusters:
            fine_mask = fine_labels == fc
            fine_indices = np.where(fine_mask)[0]
            if len(fine_indices) < min_size:
                continue
            fine_values = [metadata[i].get(field) for i in fine_indices]
            fine_values = [v for v in fine_values if v and v not in ('unknown', 'null')]
            if fine_values:
                child_purities.append(Counter(fine_values).most_common(1)[0][1] / len(fine_values))
        
        if child_purities:
            mean_child_purity = np.mean(child_purities)
            improvements.append(mean_child_purity - coarse_purity)
            parent_details[int(coarse_id)] = {
                'coarse_purity': float(coarse_purity),
                'mean_child_purity': float(mean_child_purity),
                'improvement': float(mean_child_purity - coarse_purity),
                'n_children': len(child_purities),
            }
            n_parents += 1
    
    rate = sum(1 for imp in improvements if imp > 0) / len(improvements) if improvements else 0.0
    mean_improvement = np.mean(improvements) if improvements else 0.0
    
    return {
        'mean_improvement': float(mean_improvement),
        'improvement_rate': float(rate),
        'n_parents': n_parents,
        'parent_details': parent_details,
        'improvements': improvements
    }


def compute_nesting(coarse_labels, fine_labels):
    """Compute strict nesting score."""
    n_strict = 0
    n_valid = 0
    for fid in np.unique(fine_labels[fine_labels != -1]):
        members = coarse_labels[fine_labels == fid]
        members = members[members != -1]
        if len(members) == 0:
            continue
        n_valid += 1
        if len(set(members.tolist())) == 1:
            n_strict += 1
    return n_strict / n_valid if n_valid else 0.0


def compute_fragmentation(labels):
    """Compute fragmentation metrics."""
    unique, counts = np.unique(labels[labels != -1], return_counts=True)
    if len(unique) == 0:
        return {'n_clusters': 0, 'median_size': 0, 'singleton_fraction': 0}
    return {
        'n_clusters': int(len(unique)),
        'median_size': float(np.median(counts)),
        'singleton_fraction': float(np.mean(counts == 1))
    }


def evaluate_config(embeddings, metadata, config):
    """Evaluate a single constrained hierarchical config."""
    print(f"\n{'='*60}")
    print(f"Config: {config['name']}")
    print(f"{'='*60}")
    
    coarse_labels, fine_labels, coarse_to_fine = constrained_hierarchical_leiden(
        embeddings, metadata, config)
    
    # Legal purities
    coarse_branch_purity, _ = compute_legal_purity(coarse_labels, metadata, 'branch')
    fine_branch_purity, _ = compute_legal_purity(fine_labels, metadata, 'branch')
    coarse_area_purity, _ = compute_legal_purity(coarse_labels, metadata, 'legal_area')
    fine_area_purity, _ = compute_legal_purity(fine_labels, metadata, 'legal_area')
    
    # Zoom metrics
    zoom_branch = compute_zoom_metrics(coarse_labels, fine_labels, metadata, 'branch')
    zoom_area = compute_zoom_metrics(coarse_labels, fine_labels, metadata, 'legal_area')
    
    # Nesting
    nesting = compute_nesting(coarse_labels, fine_labels)
    
    # Fragmentation
    coarse_frag = compute_fragmentation(coarse_labels)
    fine_frag = compute_fragmentation(fine_labels)
    
    print(f"  Coarse clusters: {coarse_frag['n_clusters']}, median size: {coarse_frag['median_size']:.1f}")
    print(f"  Fine clusters: {fine_frag['n_clusters']}, median size: {fine_frag['median_size']:.1f}")
    print(f"  Fine singleton fraction: {fine_frag['singleton_fraction']:.4f}")
    print(f"  Coarse branch purity: {coarse_branch_purity:.4f}")
    print(f"  Fine branch purity: {fine_branch_purity:.4f}")
    print(f"  Branch improvement: {fine_branch_purity - coarse_branch_purity:.4f}")
    print(f"  Coarse area purity: {coarse_area_purity:.4f}")
    print(f"  Fine area purity: {fine_area_purity:.4f}")
    print(f"  Area improvement: {fine_area_purity - coarse_area_purity:.4f}")
    print(f"  Strict nesting: {nesting:.4f}")
    print(f"  Zoom branch - improvement_rate: {zoom_branch['improvement_rate']:.4f}, mean_improvement: {zoom_branch['mean_improvement']:.4f}, n_parents: {zoom_branch['n_parents']}")
    print(f"  Zoom area - improvement_rate: {zoom_area['improvement_rate']:.4f}, mean_improvement: {zoom_area['mean_improvement']:.4f}, n_parents: {zoom_area['n_parents']}")
    
    return {
        "config": config,
        "n_decisions": len(embeddings),
        "coarse_clusters": coarse_frag['n_clusters'],
        "fine_clusters": fine_frag['n_clusters'],
        "coarse_branch_purity": float(coarse_branch_purity),
        "fine_branch_purity": float(fine_branch_purity),
        "coarse_area_purity": float(coarse_area_purity),
        "fine_area_purity": float(fine_area_purity),
        "branch_improvement": float(fine_branch_purity - coarse_branch_purity),
        "area_improvement": float(fine_area_purity - coarse_area_purity),
        "strict_nesting": float(nesting),
        "zoom_branch": zoom_branch,
        "zoom_area": zoom_area,
        "fragmentation": {
            "coarse_median_size": coarse_frag['median_size'],
            "fine_median_size": fine_frag['median_size'],
            "fine_singleton_fraction": fine_frag['singleton_fraction'],
            "coarse_singleton_fraction": coarse_frag['singleton_fraction']
        }
    }


def main():
    print("="*70)
    print("144k DENSE CHECKPOINT VALIDATION (Years 2000-2021)")
    print("="*70)
    print(f"Available years: {AVAILABLE_YEARS}")
    print(f"Checkpoint dir: {CHECKPOINT_DIR}")
    print(f"Configs to test: {[c['name'] for c in CONFIGS]}")
    
    # Load embeddings from checkpoints
    embeddings, checkpoint_metadata, year_offsets = load_checkpoints()
    
    # Load full metadata filtered to available years
    full_metadata = load_full_metadata()
    
    # Verify alignment
    if len(embeddings) != len(full_metadata):
        print(f"WARNING: Embedding count ({len(embeddings)}) != metadata count ({len(full_metadata)})")
        # Use the smaller count
        min_len = min(len(embeddings), len(full_metadata))
        embeddings = embeddings[:min_len]
        full_metadata = full_metadata[:min_len]
        print(f"  Truncated to {min_len}")
    
    # Evaluate all configs
    results = {
        "run_id": "144k_checkpoint_validation_20261002",
        "timestamp": "2026-10-02",
        "direction_version": 29,
        "sample": f"{len(embeddings)} dense embeddings from checkpoints (years 2000-2021, PENDING AUDIT for 2003-2021)",
        "embedding_dim": 768,
        "year_offsets": year_offsets,
        "constrained_hierarchical_results": {},
        "scale_context": {
            "28k_checkpoint": "hier_impr ~0.67 (improvement_rate=0.667)",
            "100k_15yr_checkpoint": "hier_impr ~0.35 (improvement_rate=0.348)",
            "144k_this_run": "TBD",
            "extrapolated_174k": "Power law from 28k: ~0.67, but 100k shows non-monotonic dependency"
        }
    }
    
    for config in CONFIGS:
        result = evaluate_config(embeddings, full_metadata, config)
        results["constrained_hierarchical_results"][config['name']] = result
    
    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    for name, result in results["constrained_hierarchical_results"].items():
        print(f"  {name}:")
        print(f"    n={result['n_decisions']}, coarse={result['coarse_clusters']}, fine={result['fine_clusters']}")
        print(f"    coarse_branch={result['coarse_branch_purity']:.4f}, fine_branch={result['fine_branch_purity']:.4f}")
        print(f"    branch_improvement={result['branch_improvement']:.4f}")
        print(f"    zoom_branch_rate={result['zoom_branch']['improvement_rate']:.4f}")
        print(f"    nesting={result['strict_nesting']:.4f}")
        print(f"    fine_singletons={result['fragmentation']['fine_singleton_fraction']:.4f}")
    
    # Save results
    output_path = OUTPUT_DIR / f"144k_validation_{len(embeddings)}decisions.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, default=float)
    print(f"\nResults saved to: {output_path}")
    
    return results


if __name__ == "__main__":
    main()
