#!/usr/bin/env python3
"""
Comprehensive fractal map evaluation on citation-role embeddings at 1200 scale.
Uses the validated pipeline configuration (coarse_0.5_fixed2.0_min20) that
worked at 12k and 28k scale. This characterizes the evidence-backed zoom path
(citation-role/dense-embedding modes) while awaiting 174k dense embeddings.
"""
import json
import numpy as np
import igraph as ig
import leidenalg as la
from pathlib import Path
from datetime import datetime
from sklearn.neighbors import NearestNeighbors
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

# Paths
CITATION_ROLES_DIR = Path("/tmp/lex_accepted/evaluation/evaluation/results/v3_citation_roles_frozen/")
METADATA_174K = Path("/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.jsonl")
OUTPUT_DIR = Path("results/fractal_map/citation_roles_comprehensive_20260930")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Validated pipeline config from 12k/28k validation
VALIDATED_CONFIG = {
    "coarse_res": 0.5,
    "fine_res": 2.0,
    "min_cluster_size": 20,
    "n_iterations": -1,
    "seed": 42
}

# Citation role embedding files
CITATION_ROLE_FILES = [
    "citing_alpha0.3.npy", "citing_alpha0.5.npy", "citing_alpha0.7.npy",
    "following_alpha0.3.npy", "following_alpha0.5.npy", "following_alpha0.7.npy",
    "criticizing_alpha0.3.npy", "criticizing_alpha0.5.npy", "criticizing_alpha0.7.npy",
    "distinguishing_alpha0.3.npy", "distinguishing_alpha0.5.npy", "distinguishing_alpha0.7.npy",
    "overruling_alpha0.3.npy", "overruling_alpha0.5.npy", "overruling_alpha0.7.npy",
    "center_projected_baseline.npy"
]

def load_metadata(n_decisions=1200):
    """Load metadata for the first n_decisions from 174k metadata."""
    metadata = []
    with open(METADATA_174K, 'r') as f:
        for i, line in enumerate(f):
            if i >= n_decisions:
                break
            metadata.append(json.loads(line.strip()))
    return metadata

def build_knn_graph(embeddings, k=15):
    """Build k-NN graph for Leiden clustering."""
    nbrs = NearestNeighbors(n_neighbors=k+1, metric='cosine', algorithm='brute').fit(embeddings)
    distances, indices = nbrs.kneighbors(embeddings)
    
    edges = []
    weights = []
    for i in range(len(embeddings)):
        for j_idx in range(1, k+1):  # skip self
            j = indices[i, j_idx]
            w = 1.0 - distances[i, j_idx]
            if w > 0:
                edges.append((i, j))
                weights.append(w)
    
    g = ig.Graph()
    g.add_vertices(len(embeddings))
    g.add_edges(edges)
    g.es['weight'] = weights
    return g

def run_leiden_at_resolution(graph, resolution, seed=42):
    """Run Leiden clustering at a specific resolution."""
    partition = la.find_partition(
        graph,
        la.RBConfigurationVertexPartition,
        resolution_parameter=resolution,
        weights='weight',
        seed=seed,
        n_iterations=-1
    )
    return np.array(partition.membership)

def compute_nesting(coarse_labels, fine_labels):
    """Compute nesting consistency: fraction of fine clusters that map to single coarse cluster."""
    consistent = 0
    total_fine = 0
    for fine_id in np.unique(fine_labels):
        fine_mask = (fine_labels == fine_id)
        coarse_in_fine = coarse_labels[fine_mask]
        unique_coarse = np.unique(coarse_in_fine)
        if len(unique_coarse) == 1:
            consistent += 1
        total_fine += 1
    return consistent / total_fine if total_fine > 0 else 0.0

def compute_purity(labels, metadata, field):
    """Compute purity of clusters w.r.t. a metadata field."""
    if field not in metadata[0]:
        return 0.0
    values = [m.get(field, '') for m in metadata]
    unique_labels = np.unique(labels)
    purities = []
    for label in unique_labels:
        mask = (labels == label)
        if np.sum(mask) == 0:
            continue
        cluster_values = [values[i] for i in np.where(mask)[0]]
        if len(cluster_values) == 0:
            continue
        dominant = max(set(cluster_values), key=cluster_values.count)
        purity = cluster_values.count(dominant) / len(cluster_values)
        purities.append(purity)
    return np.mean(purities) if purities else 0.0

def compute_improvement_rate(coarse_labels, fine_labels, metadata, field='branch'):
    """Compute zoom improvement rate: fraction of coarse clusters that improve purity at fine level."""
    improvements = 0
    total_coarse = 0
    for coarse_id in np.unique(coarse_labels):
        coarse_mask = (coarse_labels == coarse_id)
        coarse_size = np.sum(coarse_mask)
        if coarse_size < 2:
            continue
        coarse_purity = compute_purity(coarse_labels[coarse_mask], 
                                       [metadata[i] for i in np.where(coarse_mask)[0]], field)
        
        fine_in_coarse = fine_labels[coarse_mask]
        fine_purities = []
        for fine_id in np.unique(fine_in_coarse):
            fine_mask = (fine_labels == fine_id)
            if np.sum(fine_mask) < 2:
                continue
            fine_purity = compute_purity(fine_labels[fine_mask], 
                                        [metadata[i] for i in np.where(fine_mask)[0]], field)
            fine_purities.append(fine_purity)
        
        if fine_purities and np.mean(fine_purities) > coarse_purity:
            improvements += 1
        total_coarse += 1
    
    return improvements / total_coarse if total_coarse > 0 else 0.0

def evaluate_hierarchical_v1(embeddings, metadata, config, name):
    """Run hierarchical Leiden and evaluate against hierarchical_v1 protocol."""
    print(f"  Building k-NN graph...")
    graph = build_knn_graph(embeddings, k=15)
    
    print(f"  Running coarse Leiden (res={config['coarse_res']})...")
    coarse_labels = run_leiden_at_resolution(graph, config['coarse_res'], config['seed'])
    
    # Enforce min_cluster_size at coarse level
    coarse_labels = enforce_min_cluster_size(coarse_labels, config['min_cluster_size'], embeddings)
    
    print(f"  Running fine Leiden (res={config['fine_res']})...")
    fine_labels = run_leiden_at_resolution(graph, config['fine_res'], config['seed'])
    
    # Enforce min_cluster_size at fine level
    fine_labels = enforce_min_cluster_size(fine_labels, config['min_cluster_size'], embeddings)
    
    # Compute metrics
    n_coarse = len(np.unique(coarse_labels))
    n_fine = len(np.unique(fine_labels))
    
    nesting = compute_nesting(coarse_labels, fine_labels)
    
    coarse_branch_purity = compute_purity(coarse_labels, metadata, 'branch')
    fine_branch_purity = compute_purity(fine_labels, metadata, 'branch')
    coarse_area_purity = compute_purity(coarse_labels, metadata, 'legal_area')
    fine_area_purity = compute_purity(fine_labels, metadata, 'legal_area')
    
    branch_improvement = fine_branch_purity - coarse_branch_purity
    area_improvement = fine_area_purity - coarse_area_purity
    
    branch_improves = branch_improvement > 0
    area_improves = area_improvement > 0
    
    improvement_rate = compute_improvement_rate(coarse_labels, fine_labels, metadata, 'branch')
    
    # Singleton fraction
    fine_sizes = np.bincount(fine_labels)
    singleton_fraction = np.sum(fine_sizes == 1) / len(fine_sizes)
    
    # Legal structure checks
    legal_structure_branch = fine_branch_purity > 0.5
    legal_structure_area = fine_area_purity > 0.5
    
    # Zoom coherence (improvement_rate > 0.5)
    zoom_coherence_ok = improvement_rate > 0.5
    
    # Fragmentation check
    fragmentation_ok = singleton_fraction < 0.1
    
    # Nesting perfect
    nesting_perfect = nesting >= 0.99
    
    # Flat clustering baseline
    flat_labels = run_leiden_at_resolution(graph, config['fine_res'], config['seed'])
    flat_branch_purity = compute_purity(flat_labels, metadata, 'branch')
    hierarchical_advantage = fine_branch_purity - flat_branch_purity
    
    results = {
        "name": name,
        "config": config,
        "n_decisions": len(embeddings),
        "embedding_dim": embeddings.shape[1],
        "n_coarse": int(n_coarse),
        "n_fine": int(n_fine),
        "nesting_score": float(nesting),
        "coarse_branch_purity": float(coarse_branch_purity),
        "fine_branch_purity": float(fine_branch_purity),
        "coarse_area_purity": float(coarse_area_purity),
        "fine_area_purity": float(fine_area_purity),
        "branch_improvement": float(branch_improvement),
        "area_improvement": float(area_improvement),
        "branch_improves": bool(branch_improves),
        "area_improves": bool(area_improves),
        "improvement_rate": float(improvement_rate),
        "singleton_fraction": float(singleton_fraction),
        "fragmentation_ok": bool(fragmentation_ok),
        "nesting_perfect": bool(nesting_perfect),
        "zoom_coherence_ok": bool(zoom_coherence_ok),
        "legal_structure_branch": bool(legal_structure_branch),
        "legal_structure_area": bool(legal_structure_area),
        "flat_branch_purity": float(flat_branch_purity),
        "hierarchical_advantage": float(hierarchical_advantage),
        "hierarchical_v1_pass": bool(
            fragmentation_ok and nesting_perfect and 
            branch_improves and area_improves and 
            zoom_coherence_ok and legal_structure_branch and legal_structure_area
        ),
        "metadata_coverage": {
            "branch": len(set(m.get('branch', '') for m in metadata)),
            "legal_area": len(set(m.get('legal_area', '') for m in metadata))
        }
    }
    
    return results, coarse_labels, fine_labels

def enforce_min_cluster_size(labels, min_size, embeddings=None):
    """Merge clusters smaller than min_size into nearest larger cluster."""
    unique, counts = np.unique(labels, return_counts=True)
    small_clusters = unique[counts < min_size]
    
    if len(small_clusters) == 0:
        return labels
    
    new_labels = labels.copy()
    large_clusters = unique[counts >= min_size]
    
    if len(large_clusters) == 0:
        return new_labels
    
    # For each small cluster, assign to nearest large cluster by centroid distance
    if embeddings is not None:
        for small_id in small_clusters:
            small_mask = (labels == small_id)
            small_centroid = np.mean(embeddings[small_mask], axis=0)
            
            best_dist = float('inf')
            best_large = large_clusters[0]
            for large_id in large_clusters:
                large_mask = (labels == large_id)
                large_centroid = np.mean(embeddings[large_mask], axis=0)
                dist = np.linalg.norm(small_centroid - large_centroid)
                if dist < best_dist:
                    best_dist = dist
                    best_large = large_id
            
            new_labels[small_mask] = best_large
    else:
        # Fallback: merge into largest cluster
        largest = large_clusters[np.argmax(counts[counts >= min_size])]
        for small_id in small_clusters:
            new_labels[labels == small_id] = largest
    
    # Renumber to be contiguous
    unique_new = np.unique(new_labels)
    mapping = {old: new for new, old in enumerate(unique_new)}
    for old, new in mapping.items():
        new_labels[new_labels == old] = new
    
    return new_labels

def run_all_citation_roles():
    """Run comprehensive evaluation on all citation-role embeddings."""
    print("=" * 80)
    print("COMPREHENSIVE CITATION-ROLE FRACTAL MAP EVALUATION")
    print("=" * 80)
    print(f"Validated config: {VALIDATED_CONFIG}")
    print()
    
    # Load metadata once
    print("Loading metadata...")
    metadata = load_metadata(1200)
    print(f"Loaded {len(metadata)} decisions")
    print(f"Branches: {sorted(set(m['branch'] for m in metadata))}")
    print(f"Legal areas: {len(set(m['legal_area'] for m in metadata))}")
    print()
    
    all_results = {}
    
    for fname in CITATION_ROLE_FILES:
        name = fname.replace('.npy', '')
        print(f"\n{'='*80}")
        print(f"Evaluating: {name}")
        print(f"{'='*80}")
        
        emb_path = CITATION_ROLES_DIR / fname
        if not emb_path.exists():
            print(f"  WARNING: {emb_path} not found, skipping")
            continue
        
        embeddings = np.load(emb_path)
        print(f"  Loaded embeddings: {embeddings.shape}")
        
        try:
            results, coarse_labels, fine_labels = evaluate_hierarchical_v1(
                embeddings, metadata, VALIDATED_CONFIG, name
            )
            all_results[name] = results
            
            print(f"  Results:")
            print(f"    n_coarse: {results['n_coarse']}, n_fine: {results['n_fine']}")
            print(f"    nesting: {results['nesting_score']:.4f}")
            print(f"    coarse_branch_purity: {results['coarse_branch_purity']:.4f}")
            print(f"    fine_branch_purity: {results['fine_branch_purity']:.4f}")
            print(f"    branch_improvement: {results['branch_improvement']:.4f}")
            print(f"    improvement_rate: {results['improvement_rate']:.4f}")
            print(f"    singleton_fraction: {results['singleton_fraction']:.4f}")
            print(f"    hierarchical_v1_pass: {results['hierarchical_v1_pass']}")
            print(f"    legal_structure_branch: {results['legal_structure_branch']} (fine_branch_purity={results['fine_branch_purity']:.4f})")
            print(f"    legal_structure_area: {results['legal_structure_area']} (fine_area_purity={results['fine_area_purity']:.4f})")
            
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
            all_results[name] = {"error": str(e)}
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"citation_roles_hierarchical_v1_{timestamp}.json"
    with open(output_file, 'w') as f:
        json.dump({
            "run_id": f"citation_roles_hierarchical_v1_{timestamp}",
            "timestamp": datetime.now().isoformat(),
            "direction_version": 29,
            "hypothesis": "Citation-role embeddings at 1200 scale with validated pipeline config (coarse_0.5_fixed2.0_min20) achieve hierarchical_v1 protocol PASS, confirming evidence-backed zoom path",
            "frozen_config": VALIDATED_CONFIG,
            "frozen_sample": "1200 BGer decisions from 174k corpus (first 1200 by date order)",
            "validated_config_source": "12k/28k dense embedding validation (coarse_0.5_fixed2.0_min20)",
            "results": all_results
        }, f, indent=2)
    
    print(f"\n\nResults saved to: {output_file}")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    passes = [r for r in all_results.values() if r.get('hierarchical_v1_pass') == True]
    fails = [r for r in all_results.values() if r.get('hierarchical_v1_pass') == False]
    errors = [r for r in all_results.values() if 'error' in r]
    
    print(f"Total evaluated: {len(all_results)}")
    print(f"  PASS hierarchical_v1: {len(passes)}")
    print(f"  FAIL hierarchical_v1: {len(fails)}")
    print(f"  ERRORS: {len(errors)}")
    
    if passes:
        print(f"\nPASSING modes:")
        for r in passes:
            print(f"  {r['name']}: fine_branch_purity={r['fine_branch_purity']:.4f}, "
                  f"improvement_rate={r['improvement_rate']:.4f}, "
                  f"singleton_fraction={r['singleton_fraction']:.4f}")
    
    if fails:
        print(f"\nFAILING modes:")
        for r in fails:
            reason = []
            if not r.get('fragmentation_ok'): reason.append(f"fragmentation={r['singleton_fraction']:.4f}")
            if not r.get('nesting_perfect'): reason.append(f"nesting={r['nesting_score']:.4f}")
            if not r.get('branch_improves'): reason.append(f"branch_impr={r['branch_improvement']:.4f}")
            if not r.get('area_improves'): reason.append(f"area_impr={r['area_improvement']:.4f}")
            if not r.get('zoom_coherence_ok'): reason.append(f"impr_rate={r['improvement_rate']:.4f}")
            if not r.get('legal_structure_branch'): reason.append(f"branch_purity={r['fine_branch_purity']:.4f}")
            if not r.get('legal_structure_area'): reason.append(f"area_purity={r['fine_area_purity']:.4f}")
            print(f"  {r['name']}: {', '.join(reason)}")
    
    return all_results

if __name__ == "__main__":
    run_all_citation_roles()