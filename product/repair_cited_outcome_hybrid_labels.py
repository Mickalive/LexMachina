#!/usr/bin/env python3
"""
Repair script for cited_outcome_hybrid_0.5_174k label size mismatch.

Issue: labels_res_0.25.npy, labels_res_0.5.npy, labels_res_0.75.npy, labels_res_1.5.npy
have 175,440 entries instead of 173,963 (matching decision_ids and embeddings).

Fix: Re-run flat Leiden clustering at affected resolutions on the correct 173,963 embeddings
and regenerate label files and cluster_metadata.json for those resolutions.
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

REP_DIR = Path("/home/runner/work/LexMachina/LexMachina/product/results/fractal_map/cited_outcome_hybrid_0.5_174k")

def load_embeddings_and_metadata():
    """Load embeddings and metadata from the representation directory."""
    embeddings = np.load(REP_DIR / "embeddings.npy")
    with open(REP_DIR / "metadata.json") as f:
        metadata = json.load(f)
    
    # Load decision_ids from metadata (should be 173,963)
    with open(REP_DIR / "metadata.json") as f:
        rep_metadata = json.load(f)
    decision_ids = rep_metadata.get("decision_ids", [])
    
    logger.info(f"Loaded embeddings: {embeddings.shape}")
    logger.info(f"Decision IDs: {len(decision_ids)}")
    
    # Load representation metadata for cluster info
    with open(REP_DIR / "metadata.json") as f:
        meta = json.load(f)
    # The metadata.json in rep dir has the decision_ids list
    # But we need the branch/language/area/outcome for each decision
    # Those are in the individual metadata entries
    
    return embeddings, meta, decision_ids

def leiden_clustering(embeddings, resolution=1.0, k=15):
    """Leiden clustering (copied from hierarchical_zoom_validation)."""
    import igraph as ig
    import leidenalg
    from sklearn.neighbors import kneighbors_graph

    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normalized = embeddings / norms

    k_actual = min(k, len(embeddings) - 1)
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
        weights='weight', resolution_parameter=resolution, seed=42
    )
    return np.array(partition.membership), partition.modularity

def compute_cluster_metadata(labels, metadata, n_decisions):
    """Compute cluster metadata for a given label array."""
    unique_labels = np.unique(labels[labels != -1])
    res_metadata = {}
    
    for cluster_id in unique_labels:
        mask = labels == cluster_id
        indices = np.where(mask)[0]
        
        # Get dominant branch
        cluster_branches = [metadata[i].get('branch') for i in indices]
        cluster_branches = [b for b in cluster_branches if b and b != 'null']
        branch_purity = 0
        dominant_branch = "unknown"
        if cluster_branches:
            branch_counts = Counter(cluster_branches)
            dominant_branch = branch_counts.most_common(1)[0][0]
            branch_purity = branch_counts.most_common(1)[0][1] / len(cluster_branches)
        
        # Get dominant language
        cluster_langs = [metadata[i].get('language', 'unknown') for i in indices]
        lang_counts = Counter(cluster_langs)
        dominant_lang = lang_counts.most_common(1)[0][0] if lang_counts else "unknown"
        lang_purity = lang_counts.most_common(1)[0][1] / len(cluster_langs) if cluster_langs else 0
        
        # Get dominant legal_area
        cluster_areas = [metadata[i].get('legal_area', 'unknown') for i in indices]
        area_counts = Counter(cluster_areas)
        dominant_area = area_counts.most_common(1)[0][0] if area_counts else "unknown"
        area_purity = area_counts.most_common(1)[0][1] / len(cluster_areas) if cluster_areas else 0
        
        # Get dominant outcome
        cluster_outcomes = [metadata[i].get('outcome', 'unknown') for i in indices]
        outcome_counts = Counter(cluster_outcomes)
        dominant_outcome = outcome_counts.most_common(1)[0][0] if outcome_counts else "unknown"
        outcome_purity = outcome_counts.most_common(1)[0][1] / len(cluster_outcomes) if cluster_outcomes else 0
        
        res_metadata[str(int(cluster_id))] = {
            "size": int(len(indices)),
            "decision_indices": indices.tolist(),
            "dominant_branch": dominant_branch,
            "branch_purity": float(branch_purity),
            "dominant_language": dominant_lang,
            "language_purity": float(lang_purity),
            "dominant_area": dominant_area,
            "area_purity": float(area_purity),
            "dominant_outcome": dominant_outcome,
            "outcome_purity": float(outcome_purity),
        }
    
    return res_metadata

def main():
    logger.info("=== Repairing cited_outcome_hybrid_0.5_174k label files ===")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    # Load embeddings and metadata
    embeddings, rep_metadata, decision_ids = load_embeddings_and_metadata()
    n_decisions = len(embeddings)
    logger.info(f"Embeddings shape: {embeddings.shape}, n_decisions: {n_decisions}")
    
    # Load the full metadata with branch/language/area/outcome for each decision
    # The metadata.json in the rep dir has the per-decision info
    # But we need to check if it has the full list or just summary
    with open(REP_DIR / "metadata.json") as f:
        meta = json.load(f)
    
    # The metadata.json has decision_ids list but not per-decision branch info
    # We need to load the per-decision metadata from the corpus or from the representation's metadata
    # Let's check if the representation metadata has a full decision list with branch info
    
    # Actually, the build script saves per-decision metadata in the decision_clusters.json
    # But we need the branch/language/area/outcome for computing cluster metadata
    # Let's load the hierarchical metadata which has this info
    
    # The simplest approach: load the metadata from the cited_decisions_tfidf_174k representation
    # which has the same decision order and has the full metadata
    cited_meta_path = Path("/home/runner/work/LexMachina/LexMachina/product/results/fractal_map/cited_decisions_tfidf_174k/metadata.json")
    with open(cited_meta_path) as f:
        cited_meta = json.load(f)
    
    # cited_meta is the full metadata.json with per-decision fields
    # But wait, cited_meta might be the summary metadata, not the per-decision list
    # Let me check
    logger.info(f"cited_meta keys: {cited_meta.keys()}")
    
    # The metadata.json in the rep dir is the summary metadata with n_decisions, etc.
    # The per-decision metadata is stored in the cluster_metadata.json with decision_indices
    # But we need the branch/language/area/outcome for each decision index
    
    # Let's load the per-decision metadata from the build_complete_metadata_174k.py output
    # or from the metadata_174k_full.json
    meta_174k_path = Path("/home/runner/work/LexMachina/LexMachina/product/results/fractal_map/hierarchical_map_174k/metadata_174k_full.json")
    with open(meta_174k_path) as f:
        full_metadata = json.load(f)
    
    logger.info(f"Full metadata: {len(full_metadata)} entries")
    # Verify the decision_ids match
    if len(full_metadata) == n_decisions:
        # Check if order matches by comparing first few decision_ids
        if decision_ids and full_metadata[0].get('decision_id') == decision_ids[0]:
            logger.info("Decision order matches metadata_174k_full.json")
            metadata = full_metadata
        else:
            # Build lookup and reorder
            meta_by_id = {m['decision_id']: m for m in full_metadata}
            metadata = [meta_by_id[did] for did in decision_ids]
            logger.info("Reordered metadata to match decision_ids")
    else:
        logger.warning(f"Size mismatch: full_metadata={len(full_metadata)}, n_decisions={n_decisions}")
        metadata = full_metadata[:n_decisions]
    
    # Verify metadata has required fields
    if metadata and 'branch' in metadata[0]:
        logger.info("Metadata has branch field")
    else:
        logger.warning("Metadata missing branch field")
    
    # Load existing cluster_metadata.json to preserve resolutions that are correct
    cluster_metadata_path = REP_DIR / "cluster_metadata.json"
    with open(cluster_metadata_path) as f:
        cluster_metadata = json.load(f)
    
    # Resolutions to fix (those with 175,440 labels)
    resolutions_to_fix = ["0.25", "0.5", "0.75", "1.5"]
    
    logger.info(f"\nRe-running flat Leiden at resolutions: {resolutions_to_fix}")
    
    for res_str in resolutions_to_fix:
        res = float(res_str)
        logger.info(f"\nProcessing resolution {res}...")
        
        # Run flat Leiden
        flat_labels, mod = leiden_clustering(embeddings, resolution=res, k=15)
        logger.info(f"  Labels shape: {flat_labels.shape}, Modularity: {mod:.4f}")
        
        # Verify size
        if len(flat_labels) != n_decisions:
            logger.error(f"  SIZE MISMATCH: labels={len(flat_labels)}, expected={n_decisions}")
            continue
        
        # Save label file
        label_file = REP_DIR / f"labels_res_{res_str}.npy"
        np.save(label_file, flat_labels.astype(np.int32))
        logger.info(f"  Saved: {label_file}")
        
        # Compute cluster metadata for this resolution
        res_metadata = compute_cluster_metadata(flat_labels, metadata, n_decisions)
        cluster_metadata[f"res_{res_str}"] = res_metadata
        logger.info(f"  Clusters: {len(res_metadata)}")
    
    # Save updated cluster_metadata.json
    with open(cluster_metadata_path, 'w') as f:
        json.dump(cluster_metadata, f, indent=2)
    logger.info(f"\nUpdated cluster_metadata.json")
    
    # Verify all label files now have correct size
    logger.info("\n=== Verification ===")
    resolution_keys = ["0.25", "0.5", "0.75", "1.0", "1.5", "2.0", "3.0"]
    for res_key in resolution_keys:
        label_file = REP_DIR / f"labels_res_{res_key}.npy"
        if label_file.exists():
            labels = np.load(label_file)
            status = "✅" if len(labels) == n_decisions else "❌"
            logger.info(f"  labels_res_{res_key}.npy: {len(labels)} entries {status}")
        else:
            logger.warning(f"  labels_res_{res_key}.npy: MISSING")
    
    # Also update the representation metadata.json if needed
    with open(REP_DIR / "metadata.json") as f:
        meta = json.load(f)
    
    # Ensure zoom_levels is correct (0-6 for 7 resolutions)
    meta["zoom_levels"] = [0, 1, 2, 3, 4, 5, 6]
    meta["n_decisions"] = n_decisions
    with open(REP_DIR / "metadata.json", 'w') as f:
        json.dump(meta, f, indent=2)
    logger.info("Updated metadata.json")
    
    logger.info("\n=== Repair complete ===")

if __name__ == "__main__":
    main()