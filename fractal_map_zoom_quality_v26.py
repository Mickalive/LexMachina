#!/usr/bin/env python3
"""
Reproduce v26 Zoom Quality (ZQ) evaluation on citation-role embeddings at 1200 scale.
This matches the methodology from zoom_coherence_1000scale_citation_roles.json.
ZQ = improvement_rate * fine_purity * hierarchical_advantage
"""
import json
import numpy as np
import igraph as ig
import leidenalg as la
from pathlib import Path
from datetime import datetime
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

# Paths
CITATION_ROLES_DIR = Path("/tmp/lex_accepted/evaluation/evaluation/results/v3_citation_roles_frozen/")
METADATA_174K = Path("/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.jsonl")
OUTPUT_DIR = Path("results/fractal_map/citation_roles_zoom_quality_20260930")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Citation role embedding files
CITATION_ROLE_FILES = [
    "citing_alpha0.3.npy", "citing_alpha0.5.npy", "citing_alpha0.7.npy",
    "following_alpha0.3.npy", "following_alpha0.5.npy", "following_alpha0.7.npy",
    "criticizing_alpha0.3.npy", "criticizing_alpha0.5.npy", "criticizing_alpha0.7.npy",
    "distinguishing_alpha0.3.npy", "distinguishing_alpha0.5.npy", "distinguishing_alpha0.7.npy",
    "overruling_alpha0.3.npy", "overruling_alpha0.5.npy", "overruling_alpha0.7.npy",
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

def compute_zoom_quality(embeddings, metadata, coarse_res=0.25, fine_res=1.5, seed=42):
    """
    Compute Zoom Quality (ZQ) per v26 methodology.
    ZQ = improvement_rate * fine_purity * hierarchical_advantage
    """
    graph = build_knn_graph(embeddings, k=15)
    
    # Coarse clustering
    coarse_labels = run_leiden_at_resolution(graph, coarse_res, seed)
    n_coarse = len(np.unique(coarse_labels))
    
    # Fine clustering
    fine_labels = run_leiden_at_resolution(graph, fine_res, seed)
    n_fine = len(np.unique(fine_labels))
    
    # Coarse purity (branch)
    coarse_purity = compute_purity(coarse_labels, metadata, 'branch')
    
    # Fine purity (branch)
    fine_purity = compute_purity(fine_labels, metadata, 'branch')
    
    # Improvement rate: fraction of coarse clusters that improve at fine level
    improvements = 0
    total_coarse = 0
    for coarse_id in np.unique(coarse_labels):
        coarse_mask = (coarse_labels == coarse_id)
        coarse_size = np.sum(coarse_mask)
        if coarse_size < 2:
            continue
        
        coarse_cluster_purity = compute_purity(coarse_labels[coarse_mask], 
                                               [metadata[i] for i in np.where(coarse_mask)[0]], 'branch')
        
        fine_in_coarse = fine_labels[coarse_mask]
        fine_purities = []
        for fine_id in np.unique(fine_in_coarse):
            fine_mask = (fine_labels == fine_id)
            if np.sum(fine_mask) < 2:
                continue
            fp = compute_purity(fine_labels[fine_mask], 
                               [metadata[i] for i in np.where(fine_mask)[0]], 'branch')
            fine_purities.append(fp)
        
        if fine_purities and np.mean(fine_purities) > coarse_cluster_purity:
            improvements += 1
        total_coarse += 1
    
    improvement_rate = improvements / total_coarse if total_coarse > 0 else 0.0
    
    # Flat clustering at fine resolution for hierarchical advantage
    flat_labels = run_leiden_at_resolution(graph, fine_res, seed)
    flat_purity = compute_purity(flat_labels, metadata, 'branch')
    
    hierarchical_advantage = fine_purity - flat_purity
    
    # Zoom Quality
    zq = improvement_rate * fine_purity * hierarchical_advantage
    
    return {
        "zoom_quality_score": float(zq),
        "improvement_rate": float(improvement_rate),
        "fine_purity": float(fine_purity),
        "coarse_purity": float(coarse_purity),
        "flat_purity": float(flat_purity),
        "hierarchical_advantage": float(hierarchical_advantage),
        "n_coarse": int(n_coarse),
        "n_fine": int(n_fine),
        "n_decisions": len(embeddings)
    }

def run_zoom_quality_all():
    """Run ZQ evaluation on all citation-role embeddings."""
    print("=" * 80)
    print("ZOOM QUALITY (v26) EVALUATION ON CITATION-ROLE EMBEDDINGS")
    print("=" * 80)
    print("ZQ = improvement_rate * fine_purity * hierarchical_advantage")
    print("Success rule: ZQ > 0.25 indicates evidence-backed zoom path; ZQ > 0.50 is strong")
    print()
    
    # Load metadata
    print("Loading metadata...")
    metadata = load_metadata(1200)
    print(f"Loaded {len(metadata)} decisions")
    print()
    
    all_results = {}
    
    for fname in CITATION_ROLE_FILES:
        name = fname.replace('.npy', '')
        print(f"Evaluating: {name}")
        
        emb_path = CITATION_ROLES_DIR / fname
        if not emb_path.exists():
            print(f"  WARNING: {emb_path} not found, skipping")
            continue
        
        embeddings = np.load(emb_path)
        print(f"  Shape: {embeddings.shape}")
        
        try:
            results = compute_zoom_quality(embeddings, metadata)
            all_results[name] = results
            
            print(f"    ZQ: {results['zoom_quality_score']:.4f}")
            print(f"    improvement_rate: {results['improvement_rate']:.4f}")
            print(f"    fine_purity: {results['fine_purity']:.4f}")
            print(f"    coarse_purity: {results['coarse_purity']:.4f}")
            print(f"    hierarchical_advantage: {results['hierarchical_advantage']:.4f}")
            print(f"    n_coarse: {results['n_coarse']}, n_fine: {results['n_fine']}")
            
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
            all_results[name] = {"error": str(e)}
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"zoom_quality_v26_citation_roles_{timestamp}.json"
    with open(output_file, 'w') as f:
        json.dump({
            "run_id": f"zoom_quality_v26_citation_roles_{timestamp}",
            "timestamp": datetime.now().isoformat(),
            "direction_version": 29,
            "hypothesis": "Citation-role embeddings at 1200 scale reproduce v26 zoom-quality scores from 1000-scale evaluation",
            "frozen_sample": "1200 BGer decisions from 174k corpus (first 1200 by date order)",
            "frozen_metric": "Zoom Quality (ZQ) = improvement_rate * fine_purity * hierarchical_advantage",
            "success_rule": "ZQ > 0.25 indicates evidence-backed zoom path; ZQ > 0.50 is strong",
            "methodology": "v26 zoom-quality evaluation: coarse_res=0.25, fine_res=1.5, k=15, seed=42",
            "results": all_results
        }, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")
    
    # Summary
    print("\n" + "=" * 80)
    print("ZOOM QUALITY SUMMARY")
    print("=" * 80)
    
    valid_results = {k: v for k, v in all_results.items() if 'error' not in v}
    sorted_results = sorted(valid_results.items(), key=lambda x: x[1]['zoom_quality_score'], reverse=True)
    
    print(f"{'Mode':<30} {'ZQ':<8} {'Impr_Rate':<10} {'Fine_Pur':<10} {'Coarse_Pur':<10} {'Hier_Adv':<10} {'Verdict'}")
    print("-" * 90)
    
    for name, r in sorted_results:
        zq = r['zoom_quality_score']
        if zq > 0.50:
            verdict = "STRONG"
        elif zq > 0.25:
            verdict = "EVIDENCE"
        else:
            verdict = "WEAK"
        print(f"{name:<30} {zq:<8.4f} {r['improvement_rate']:<10.4f} {r['fine_purity']:<10.4f} {r['coarse_purity']:<10.4f} {r['hierarchical_advantage']:<10.4f} {verdict}")
    
    return all_results

if __name__ == "__main__":
    run_zoom_quality_all()