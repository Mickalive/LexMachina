#!/usr/bin/env python3
"""
Generate Product Integration Artifacts for 174k Constrained Hierarchical Leiden Modes.

This script takes the constrained hierarchical Leiden results and generates
the full set of product integration artifacts required by ProductMapLoader.

Modes to process:
1. cited_decisions_tfidf_outcome_hybrid_0.5
2. cited_decisions_tfidf_outcome_hybrid_0.7
3. cited_decisions_tfidf
4. regeste_tfidf (subset: ~83k decisions with regeste)

Output structure per mode:
  results/fractal_map/constrained_hierarchical_174k/<mode_id>/
    ├── cluster_metadata.json      # Legal context per cluster
    ├── zoom_mappings.json         # Parent-child navigation
    ├── zoom_coherence.json        # Per-cluster zoom improvement
    ├── decision_clusters.json     # Decision-to-cluster index
    ├── labels_res_0.25.npy        # Resolution ladder labels
    ├── labels_res_0.5.npy
    ├── labels_res_0.75.npy
    ├── labels_res_1.0.npy
    ├── labels_res_1.5.npy
    ├── labels_res_2.0.npy
    ├── labels_res_3.0.npy
    ├── labels_hierarchical_best.npy
    └── labels_coarse_0.5.npy
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict
import logging
from datetime import datetime, timezone
import igraph as ig
import leidenalg
from sklearn.neighbors import kneighbors_graph
from sklearn.feature_extraction.text import TfidfVectorizer
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
EMBEDDINGS_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings")
METADATA_PATH = Path("/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json")
OUTPUT_BASE = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/constrained_hierarchical_174k")
OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

# Modes to process
MODES = [
    {
        "mode_id": "cited_decisions_tfidf_outcome_hybrid_0.5_174k_constrained",
        "embedding_file": "cited_decisions_tfidf_outcome_hybrid_0.5.npy",
        "name": "Cited Decisions TF-IDF + Outcome Hybrid 0.5 (174k Constrained Hierarchical)",
        "description": "Constrained hierarchical Leiden (min_cluster_size=20, adaptive sub_res) on 174k cited_decisions_tfidf_outcome_hybrid_0.5 embeddings. Nesting=1.0, zero fragmentation, branch purity improvement +0.06, area purity improvement +0.09.",
        "coarse_res": 0.5,
        "min_cluster_size": 20,
        "sub_res_base": 3.0,
        "adaptive_sub_res": True,
    },
    {
        "mode_id": "cited_decisions_tfidf_outcome_hybrid_0.7_174k_constrained",
        "embedding_file": "cited_decisions_tfidf_outcome_hybrid_0.7.npy",
        "name": "Cited Decisions TF-IDF + Outcome Hybrid 0.7 (174k Constrained Hierarchical)",
        "description": "Constrained hierarchical Leiden (min_cluster_size=20, adaptive sub_res) on 174k cited_decisions_tfidf_outcome_hybrid_0.7 embeddings. Nesting=1.0, zero fragmentation, branch purity improvement +0.05, area purity improvement +0.07.",
        "coarse_res": 0.5,
        "min_cluster_size": 20,
        "sub_res_base": 3.0,
        "adaptive_sub_res": True,
    },
    {
        "mode_id": "cited_decisions_tfidf_174k_constrained",
        "embedding_file": "cited_decisions_tfidf.npy",
        "name": "Cited Decisions TF-IDF (174k Constrained Hierarchical)",
        "description": "Constrained hierarchical Leiden (min_cluster_size=20, adaptive sub_res) on 174k cited_decisions_tfidf embeddings. Nesting=1.0, zero fragmentation.",
        "coarse_res": 0.5,
        "min_cluster_size": 20,
        "sub_res_base": 3.0,
        "adaptive_sub_res": True,
    },
    {
        "mode_id": "regeste_tfidf_83k_constrained",
        "embedding_file": "regeste_tfidf.npy",
        "name": "Regeste TF-IDF (83k Constrained Hierarchical)",
        "description": "Constrained hierarchical Leiden (min_cluster_size=10, adaptive sub_res) on 83k regeste_tfidf embeddings (decisions with regeste text). Nesting=1.0, zero fragmentation, branch purity improvement +0.09, area purity improvement +0.14.",
        "coarse_res": 0.25,
        "min_cluster_size": 10,
        "sub_res_base": 3.0,
        "adaptive_sub_res": True,
    },
]

K = 15
RESOLUTION_LADDER = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]


def load_metadata():
    """Load evaluation metadata with branch and legal_area."""
    with open(METADATA_PATH) as f:
        metadata = json.load(f)
    logger.info(f"Loaded metadata: {len(metadata)} entries")
    return metadata


def load_embeddings(embedding_file):
    """Load embeddings for a mode."""
    emb_path = EMBEDDINGS_DIR / embedding_file
    if not emb_path.exists():
        logger.warning(f"Embeddings not found: {emb_path}")
        return None
    embeddings = np.load(emb_path)
    logger.info(f"Loaded {embedding_file}: {embeddings.shape}")
    return embeddings


def leiden_clustering(embeddings, resolution=1.0, k=15, seed=42):
    """Leiden clustering on k-NN graph."""
    k_actual = min(k, len(embeddings) - 1)
    graph = kneighbors_graph(embeddings, n_neighbors=k_actual, metric='euclidean',
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
    return np.array(partition.membership), partition.modularity


def hierarchical_leiden_constrained(embeddings, metadata, coarse_res=0.5, 
                                     min_cluster_size=20, 
                                     sub_res_base=3.0,
                                     adaptive_sub_res=True,
                                     k=15):
    """
    Run constrained hierarchical Leiden:
    1. Global Leiden at coarse_res to get coarse clusters
    2. For each coarse cluster, run Leiden at adaptive sub_res within the subset
    3. Enforce min_cluster_size - merge tiny clusters
    4. Assign global labels with guaranteed nesting
    """
    # Step 1: Global coarse clustering
    coarse_labels, coarse_mod = leiden_clustering(embeddings, resolution=coarse_res, k=k)
    unique_coarse = np.unique(coarse_labels[coarse_labels != -1])
    
    logger.info(f"  Coarse (res={coarse_res}): {len(unique_coarse)} clusters, modularity={coarse_mod:.4f}")
    
    # Step 2: Within each coarse cluster, run Leiden at adaptive sub_res
    hierarchical_labels = np.full(len(embeddings), -1, dtype=int)
    sub_cluster_id = 0
    cluster_info = {}
    coarse_to_fine = defaultdict(list)
    sub_labels_dict = {}  # Store sub_labels for each coarse cluster
    
    for coarse_id in unique_coarse:
        mask = coarse_labels == coarse_id
        indices = np.where(mask)[0]
        cluster_size = len(indices)
        
        if cluster_size < min_cluster_size:
            # Too small to sub-cluster
            hierarchical_labels[indices] = sub_cluster_id
            cluster_info[sub_cluster_id] = {
                'coarse_id': int(coarse_id),
                'sub_id': 0,
                'size': int(cluster_size),
                'too_small': True,
            }
            coarse_to_fine[int(coarse_id)].append(sub_cluster_id)
            sub_cluster_id += 1
            continue
        
        subset_embeddings = embeddings[indices]
        
        # Adaptive sub-resolution: lower resolution for larger clusters
        if adaptive_sub_res:
            target_subclusters = max(5, min(50, cluster_size // 100))
            sub_res = sub_res_base * (20 / target_subclusters) ** 0.5
            sub_res = max(1.0, min(5.0, sub_res))
        else:
            sub_res = sub_res_base
        
        # Run Leiden within subset
        sub_labels, sub_mod = leiden_clustering(subset_embeddings, resolution=sub_res, k=k)
        unique_sub = np.unique(sub_labels[sub_labels != -1])
        
        logger.info(f"    Coarse {coarse_id} ({cluster_size} docs): "
                    f"{len(unique_sub)} sub-clusters at sub_res={sub_res:.2f}, modularity={sub_mod:.4f}")
        
        # Store sub_labels for this coarse cluster
        sub_labels_dict[coarse_id] = (sub_labels, indices)
        
        # Post-process: merge sub-clusters smaller than min_cluster_size
        sub_label_to_indices = {sid: indices[sub_labels == sid] for sid in unique_sub}
        
        valid_sub_labels = [sid for sid, idxs in sub_label_to_indices.items() if len(idxs) >= min_cluster_size]
        tiny_sub_labels = [sid for sid, idxs in sub_label_to_indices.items() if len(idxs) < min_cluster_size]
        
        # Merge tiny clusters into nearest valid cluster (by centroid distance)
        if tiny_sub_labels and valid_sub_labels:
            valid_centroids = {sid: np.mean(subset_embeddings[sub_labels == sid], axis=0) 
                              for sid in valid_sub_labels}
            for tiny_sid in tiny_sub_labels:
                tiny_centroid = np.mean(subset_embeddings[sub_labels == tiny_sid], axis=0)
                best_sid = min(valid_sub_labels, 
                               key=lambda sid: np.linalg.norm(tiny_centroid - valid_centroids[sid]))
                sub_labels[sub_labels == tiny_sid] = best_sid
            unique_sub = valid_sub_labels
        
        # Assign global labels
        for sub_id in unique_sub:
            sub_mask = sub_labels == sub_id
            global_indices = indices[sub_mask]
            hierarchical_labels[global_indices] = sub_cluster_id
            
            cluster_info[sub_cluster_id] = {
                'coarse_id': int(coarse_id),
                'sub_id': int(sub_id),
                'size': int(len(global_indices)),
                'too_small': False,
            }
            coarse_to_fine[int(coarse_id)].append(sub_cluster_id)
            sub_cluster_id += 1
    
    return hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine, sub_labels_dict


def compute_strict_nesting(hierarchical_labels, coarse_labels):
    """Compute strict nesting score: fraction of fine clusters whose members share ONE coarse parent."""
    unique_fine = np.unique(hierarchical_labels[hierarchical_labels != -1])
    consistent = 0
    
    for fine_id in unique_fine:
        fine_mask = hierarchical_labels == fine_id
        parent_labels = coarse_labels[fine_mask]
        parent_valid = parent_labels[parent_labels != -1]
        if len(parent_valid) > 0:
            if len(set(parent_valid.tolist())) == 1:
                consistent += 1
    
    score = consistent / len(unique_fine) if len(unique_fine) > 0 else 0
    return float(score)


def compute_branch_purity(labels, metadata):
    """Compute mean branch purity per cluster."""
    unique_labels = np.unique(labels[labels != -1])
    purities = []
    
    for label in unique_labels:
        mask = labels == label
        cluster_branches = [metadata[i].get('branch') for i in np.where(mask)[0]]
        cluster_branches = [b for b in cluster_branches if b and b != 'unknown' and b != 'null']
        
        if cluster_branches:
            most_common = Counter(cluster_branches).most_common(1)[0][1]
            purities.append(most_common / len(cluster_branches))
    
    return float(np.mean(purities)) if purities else 0


def compute_legal_area_purity(labels, metadata):
    """Compute mean legal_area purity per cluster."""
    unique_labels = np.unique(labels[labels != -1])
    purities = []
    
    for label in unique_labels:
        mask = labels == label
        cluster_areas = [metadata[i].get('legal_area') for i in np.where(mask)[0]]
        cluster_areas = [a for a in cluster_areas if a and a != 'unknown' and a != 'null']
        
        if cluster_areas:
            most_common = Counter(cluster_areas).most_common(1)[0][1]
            purities.append(most_common / len(cluster_areas))
    
    return float(np.mean(purities)) if purities else 0


def compute_cluster_metadata(hierarchical_labels, coarse_labels, metadata, cluster_info):
    """Compute detailed cluster metadata with legal context."""
    unique_fine = np.unique(hierarchical_labels[hierarchical_labels != -1])
    metadata_out = {"hierarchical": {}, "coarse": {}}
    
    # Fine (hierarchical) clusters
    for fine_id in unique_fine:
        mask = hierarchical_labels == fine_id
        indices = np.where(mask)[0]
        info = cluster_info.get(fine_id, {})
        
        # Get legal metadata
        branches = [metadata[i].get('branch') for i in indices]
        branches = [b for b in branches if b and b != 'unknown' and b != 'null']
        areas = [metadata[i].get('legal_area') for i in indices]
        areas = [a for a in areas if a and a != 'unknown' and a != 'null']
        chambers = [metadata[i].get('chamber') for i in indices]
        chambers = [c for c in chambers if c and c != 'unknown' and c != 'null']
        languages = [metadata[i].get('language') for i in indices]
        languages = [l for l in languages if l and l != 'unknown' and l != 'null']
        
        branch_purity = Counter(branches).most_common(1)[0][1] / len(branches) if branches else 0
        area_purity = Counter(areas).most_common(1)[0][1] / len(areas) if areas else 0
        
        metadata_out["hierarchical"][str(fine_id)] = {
            "size": int(len(indices)),
            "coarse_parent": info.get('coarse_id', -1),
            "branch_purity": branch_purity,
            "area_purity": area_purity,
            "dominant_branch": Counter(branches).most_common(1)[0][0] if branches else None,
            "dominant_area": Counter(areas).most_common(1)[0][0] if areas else None,
            "dominant_chamber": Counter(chambers).most_common(1)[0][0] if chambers else None,
            "dominant_language": Counter(languages).most_common(1)[0][0] if languages else None,
            "branch_distribution": dict(Counter(branches)),
            "area_distribution": dict(Counter(areas)),
            "chamber_distribution": dict(Counter(chambers)),
            "language_distribution": dict(Counter(languages)),
        }
    
    # Coarse clusters
    unique_coarse = np.unique(coarse_labels[coarse_labels != -1])
    for coarse_id in unique_coarse:
        mask = coarse_labels == coarse_id
        indices = np.where(mask)[0]
        
        branches = [metadata[i].get('branch') for i in indices]
        branches = [b for b in branches if b and b != 'unknown' and b != 'null']
        areas = [metadata[i].get('legal_area') for i in indices]
        areas = [a for a in areas if a and a != 'unknown' and a != 'null']
        chambers = [metadata[i].get('chamber') for i in indices]
        chambers = [c for c in chambers if c and c != 'unknown' and c != 'null']
        languages = [metadata[i].get('language') for i in indices]
        languages = [l for l in languages if l and l != 'unknown' and l != 'null']
        
        branch_purity = Counter(branches).most_common(1)[0][1] / len(branches) if branches else 0
        area_purity = Counter(areas).most_common(1)[0][1] / len(areas) if areas else 0
        
        metadata_out["coarse"][str(int(coarse_id))] = {
            "size": int(len(indices)),
            "children": coarse_to_fine.get(int(coarse_id), []),
            "branch_purity": branch_purity,
            "area_purity": area_purity,
            "dominant_branch": Counter(branches).most_common(1)[0][0] if branches else None,
            "dominant_area": Counter(areas).most_common(1)[0][0] if areas else None,
            "dominant_chamber": Counter(chambers).most_common(1)[0][0] if chambers else None,
            "dominant_language": Counter(languages).most_common(1)[0][0] if languages else None,
            "branch_distribution": dict(Counter(branches)),
            "area_distribution": dict(Counter(areas)),
            "chamber_distribution": dict(Counter(chambers)),
            "language_distribution": dict(Counter(languages)),
        }
    
    return metadata_out


def compute_zoom_mappings(hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine):
    """Compute parent-child zoom mappings."""
    zoom_mappings = {}
    
    # Coarse -> Fine mapping
    parent_to_children = {}
    for coarse_id, children in coarse_to_fine.items():
        parent_to_children[str(coarse_id)] = [str(c) for c in children]
    
    # Fine -> Coarse mapping
    child_to_parent = {}
    for fine_id, info in cluster_info.items():
        coarse_id = info.get('coarse_id', -1)
        if coarse_id >= 0:
            child_to_parent[str(fine_id)] = str(coarse_id)
    
    zoom_mappings["0.5_to_hierarchical"] = {
        "parent_to_children": parent_to_children,
        "child_to_parent": child_to_parent,
    }
    
    # Also add resolution ladder mappings for flat resolutions
    # (For hierarchical mode, the main navigation is coarse <-> hierarchical)
    zoom_mappings["hierarchical_to_0.5"] = {
        "parent_to_children": {v: k for k, vals in parent_to_children.items() for v in vals},
        "child_to_parent": {v: k for k, v in child_to_parent.items()},
    }
    
    return zoom_mappings


def compute_zoom_coherence(metadata, coarse_labels, hierarchical_labels, cluster_info, coarse_to_fine, min_cluster_size=3):
    """Compute zoom coherence metrics in decision-ID space."""
    # Map decision_id to (coarse, fine) labels
    id_pairs = {}
    for i, m in enumerate(metadata):
        did = m['decision_id']
        id_pairs[did] = (coarse_labels[i], hierarchical_labels[i])
    
    # Labeled values per cluster
    coarse_vals_branch = defaultdict(list)
    fine_vals_branch = defaultdict(list)
    coarse_vals_area = defaultdict(list)
    fine_vals_area = defaultdict(list)
    
    for i, m in enumerate(metadata):
        did = m['decision_id']
        cc, fc = id_pairs[did]
        val_branch = m.get('branch')
        val_area = m.get('legal_area')
        if val_branch and val_branch not in ('unknown', 'null'):
            coarse_vals_branch[cc].append(val_branch)
            fine_vals_branch[fc].append(val_branch)
        if val_area and val_area not in ('unknown', 'null'):
            coarse_vals_area[cc].append(val_area)
            fine_vals_area[fc].append(val_area)
    
    # Membership counts (all ids)
    coarse_members = defaultdict(list)
    fine_members = defaultdict(list)
    for did, (cc, fc) in id_pairs.items():
        coarse_members[cc].append(did)
        fine_members[fc].append(did)
    
    # child -> parent: majority coarse cluster among ALL member ids
    fine_coarse_counter = defaultdict(Counter)
    for did, (cc, fc) in id_pairs.items():
        fine_coarse_counter[fc][cc] += 1
    child_to_parent = {fc: cc.most_common(1)[0][0]
                       for fc, cc in fine_coarse_counter.items() if cc}
    
    zoom_coherence = {}
    
    for field_name, coarse_vals, fine_vals in [
        ('branch', coarse_vals_branch, fine_vals_branch),
        ('legal_area', coarse_vals_area, fine_vals_area),
    ]:
        improvements = []
        parent_details = {}
        n_parents = 0
        
        for pc, cmems in coarse_members.items():
            if len(cmems) < min_cluster_size:
                continue
            cvals = coarse_vals.get(pc, [])
            if not cvals:
                continue
            
            # children of this parent with >= MIN_CLUSTER_SIZE labeled decisions
            child_clusters = [fc for fc, p in child_to_parent.items()
                              if p == pc and len(fine_vals.get(fc, [])) >= min_cluster_size]
            if not child_clusters:
                continue
            
            child_purities = []
            for fc in child_clusters:
                fvals = fine_vals[fc]
                child_purities.append(Counter(fvals).most_common(1)[0][1] / len(fvals))
            
            coarse_purity = Counter(cvals).most_common(1)[0][1] / len(cvals)
            mean_child = float(np.mean(child_purities))
            improvement = mean_child - coarse_purity
            improvements.append(improvement)
            
            parent_details[str(pc)] = {
                "coarse_purity": coarse_purity,
                "mean_child_purity": mean_child,
                "improvement": improvement,
                "n_children": len(child_clusters),
            }
            n_parents += 1
        
        if improvements:
            mean_improvement = float(np.mean(improvements))
            improvement_rate = float(sum(1 for j in improvements if j > 0) / len(improvements))
        else:
            mean_improvement = None
            improvement_rate = None
        
        zoom_coherence[field_name] = {
            "mean_improvement": mean_improvement,
            "improvement_rate": improvement_rate,
            "n_parents": n_parents,
            "parent_details": parent_details,
        }
    
    return zoom_coherence


def build_decision_clusters(metadata, hierarchical_labels, coarse_labels, resolution_labels):
    """Build decision-to-cluster index for all resolutions."""
    decision_clusters = {}
    
    for i, m in enumerate(metadata):
        did = m['decision_id']
        decision_clusters[did] = {
            "hierarchical": int(hierarchical_labels[i]) if hierarchical_labels[i] >= 0 else None,
            "coarse_0.5": int(coarse_labels[i]) if coarse_labels[i] >= 0 else None,
        }
        # Add flat resolution labels
        for res, labels in resolution_labels.items():
            decision_clusters[did][f"res_{res}"] = int(labels[i]) if labels[i] >= 0 else None
    
    return decision_clusters


def process_mode(mode_config, metadata):
    """Process a single mode and generate all artifacts."""
    mode_id = mode_config["mode_id"]
    logger.info(f"\n{'='*70}")
    logger.info(f"Processing mode: {mode_id}")
    logger.info(f"{'='*70}")
    
    # Load embeddings
    embeddings = load_embeddings(mode_config["embedding_file"])
    if embeddings is None:
        return None
    
    n_meta = len(metadata)
    if len(embeddings) > n_meta:
        embeddings = embeddings[:n_meta]
        logger.info(f"  Truncated embeddings to {n_meta}")
    elif len(embeddings) < n_meta:
        logger.warning(f"  Embeddings ({len(embeddings)}) < metadata ({n_meta}), skipping")
        return None
    
    # Run constrained hierarchical Leiden
    logger.info("Running constrained hierarchical Leiden...")
    hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine, sub_labels_dict = hierarchical_leiden_constrained(
        embeddings, metadata,
        coarse_res=mode_config["coarse_res"],
        min_cluster_size=mode_config["min_cluster_size"],
        sub_res_base=mode_config["sub_res_base"],
        adaptive_sub_res=mode_config["adaptive_sub_res"],
        k=K
    )
    
    # Also run flat Leiden at each resolution in the ladder
    logger.info("Running flat Leiden at resolution ladder...")
    resolution_labels = {}
    for res in RESOLUTION_LADDER:
        labels, mod = leiden_clustering(embeddings, resolution=res, k=K)
        resolution_labels[res] = labels
        n_clusters = len(set(labels[labels != -1]))
        logger.info(f"  Flat res={res}: {n_clusters} clusters, modularity={mod:.4f}")
    
    # Compute metrics
    coarse_branch_purity = compute_branch_purity(coarse_labels, metadata)
    fine_branch_purity = compute_branch_purity(hierarchical_labels, metadata)
    coarse_area_purity = compute_legal_area_purity(coarse_labels, metadata)
    fine_area_purity = compute_legal_area_purity(hierarchical_labels, metadata)
    nesting = compute_strict_nesting(hierarchical_labels, coarse_labels)
    
    logger.info(f"Branch purity: coarse={coarse_branch_purity:.4f}, fine={fine_branch_purity:.4f} (Δ={fine_branch_purity-coarse_branch_purity:+.4f})")
    logger.info(f"Area purity: coarse={coarse_area_purity:.4f}, fine={fine_area_purity:.4f} (Δ={fine_area_purity-coarse_area_purity:+.4f})")
    logger.info(f"Strict nesting: {nesting:.4f}")
    
    # Generate artifacts
    logger.info("Generating cluster metadata...")
    cluster_metadata = compute_cluster_metadata(hierarchical_labels, coarse_labels, metadata, cluster_info)
    
    logger.info("Generating zoom mappings...")
    zoom_mappings = compute_zoom_mappings(hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine)
    
    logger.info("Generating zoom coherence...")
    zoom_coherence = compute_zoom_coherence(metadata, coarse_labels, hierarchical_labels, cluster_info, coarse_to_fine)
    
    logger.info("Building decision clusters...")
    decision_clusters = build_decision_clusters(metadata, hierarchical_labels, coarse_labels, resolution_labels)
    
    # Create output directory
    mode_output_dir = OUTPUT_BASE / mode_id
    mode_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save JSON artifacts
    logger.info("Saving JSON artifacts...")
    with open(mode_output_dir / "cluster_metadata.json", 'w') as f:
        json.dump(cluster_metadata, f, indent=2)
    
    with open(mode_output_dir / "zoom_mappings.json", 'w') as f:
        json.dump(zoom_mappings, f, indent=2)
    
    with open(mode_output_dir / "zoom_coherence.json", 'w') as f:
        json.dump(zoom_coherence, f, indent=2)
    
    with open(mode_output_dir / "decision_clusters.json", 'w') as f:
        json.dump(decision_clusters, f, indent=2)
    
    # Save label arrays (.npy)
    logger.info("Saving label arrays...")
    np.save(mode_output_dir / "labels_hierarchical_best.npy", hierarchical_labels)
    np.save(mode_output_dir / "labels_coarse_0.5.npy", coarse_labels)
    
    for res, labels in resolution_labels.items():
        np.save(mode_output_dir / f"labels_res_{res}.npy", labels)
    
    # Create integration summary
    integration_summary = {
        "mode_id": mode_id,
        "name": mode_config["name"],
        "description": mode_config["description"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "n_decisions": n_meta,
        "hierarchical_clusters": int(len(np.unique(hierarchical_labels[hierarchical_labels != -1]))),
        "coarse_clusters": int(len(np.unique(coarse_labels[coarse_labels != -1]))),
        "nesting_score": nesting,
        "coarse_branch_purity": coarse_branch_purity,
        "fine_branch_purity": fine_branch_purity,
        "branch_purity_improvement": fine_branch_purity - coarse_branch_purity,
        "coarse_area_purity": coarse_area_purity,
        "fine_area_purity": fine_area_purity,
        "area_purity_improvement": fine_area_purity - coarse_area_purity,
        "resolution_ladder": RESOLUTION_LADDER,
        "flat_resolution_cluster_counts": {str(res): int(len(np.unique(labels[labels != -1]))) for res, labels in resolution_labels.items()},
        "evidence_tier": "ACCEPTED",
        "validation_note": "Constrained hierarchical Leiden with min_cluster_size + adaptive sub_resolution at 174k scale",
    }
    
    with open(mode_output_dir / "integration_summary.json", 'w') as f:
        json.dump(integration_summary, f, indent=2)
    
    logger.info(f"Completed mode: {mode_id}")
    logger.info(f"  Hierarchical clusters: {integration_summary['hierarchical_clusters']}")
    logger.info(f"  Coarse clusters: {integration_summary['coarse_clusters']}")
    logger.info(f"  Nesting: {nesting:.4f}")
    logger.info(f"  Branch purity improvement: {fine_branch_purity - coarse_branch_purity:+.4f}")
    logger.info(f"  Area purity improvement: {fine_area_purity - coarse_area_purity:+.4f}")
    
    return integration_summary


def main():
    logger.info("=== Generating 174k Constrained Hierarchical Product Integration Artifacts ===")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    # Load metadata once
    metadata = load_metadata()
    
    # Process each mode
    all_summaries = {}
    for mode_config in MODES:
        try:
            summary = process_mode(mode_config, metadata)
            if summary:
                all_summaries[mode_config["mode_id"]] = summary
        except Exception as e:
            logger.error(f"Failed to process {mode_config['mode_id']}: {e}", exc_info=True)
    
    # Save overall summary
    overall_summary = {
        "run_id": f"174k_constrained_hierarchical_product_integration_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction_version": 30,
        "modes_processed": list(all_summaries.keys()),
        "summaries": all_summaries,
    }
    
    with open(OUTPUT_BASE / "product_integration_summary.json", 'w') as f:
        json.dump(overall_summary, f, indent=2)
    
    logger.info(f"\n=== Complete ===")
    logger.info(f"Processed {len(all_summaries)} modes")
    logger.info(f"Artifacts saved to: {OUTPUT_BASE}")
    
    for mode_id, summary in all_summaries.items():
        logger.info(f"  {mode_id}: {summary['hierarchical_clusters']} hierarchical clusters, nesting={summary['nesting_score']:.4f}")


if __name__ == "__main__":
    main()