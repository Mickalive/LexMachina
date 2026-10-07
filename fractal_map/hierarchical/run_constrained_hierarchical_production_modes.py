#!/usr/bin/env python3
"""
Run constrained hierarchical Leiden on the 3 PRODUCTION TF-IDF modes at full 174k
and build product integration artifacts.

These 3 modes PASSED hierarchical_v1 at full 173,963 decisions:
- full_text_tfidf_light: fine_branch_purity=0.930
- regeste_full_text_hybrid_0.5: fine_branch_purity=0.906
- regeste_full_text_hybrid_0.7: fine_branch_purity=0.908

The constrained hierarchical method (v26 PASSING) was previously only run on:
- 3 citation-based modes (52% scale / ~91k decisions)
- regeste_tfidf (FAILED hierarchical_v1)

This script completes the finalization of TF-IDF hierarchical production modes at 174k.
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
import logging
import igraph as ig
import leidenalg
from sklearn.neighbors import kneighbors_graph

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
EMBEDDINGS_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings")
METADATA_PATH = Path("/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/product_integration_constrained_174k_production")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# The 3 PRODUCTION modes that PASSED hierarchical_v1 at FULL 174k
PRODUCTION_MODES = {
    "full_text_tfidf_light": {
        "coarse_res": 0.25,
        "base_sub_res": 3.0,
        "min_cluster_size": 10,
        "max_subclusters_per_parent": 20,
        "adaptive_sub_res": True,
    },
    "regeste_full_text_hybrid_0.5": {
        "coarse_res": 0.25,
        "base_sub_res": 3.0,
        "min_cluster_size": 10,
        "max_subclusters_per_parent": 20,
        "adaptive_sub_res": True,
    },
    "regeste_full_text_hybrid_0.7": {
        "coarse_res": 0.25,
        "base_sub_res": 3.0,
        "min_cluster_size": 10,
        "max_subclusters_per_parent": 20,
        "adaptive_sub_res": True,
    },
}

MIN_CLUSTER_SIZE = 3


def load_metadata():
    with open(METADATA_PATH) as f:
        meta = json.load(f)
    meta_by_id = {m['decision_id']: m for m in meta}
    meta_ids = [m['decision_id'] for m in meta]
    return meta_by_id, meta_ids


def load_embeddings(mode_name):
    """Load TF-IDF embeddings for a mode."""
    path = EMBEDDINGS_DIR / f"{mode_name}.npy"
    if not path.exists():
        logger.warning(f"Embeddings not found: {path}")
        return None
    embeddings = np.load(path)
    logger.info(f"Loaded {mode_name}: {embeddings.shape}")
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


def constrained_hierarchical_leiden(embeddings, metadata_ids, 
                                    coarse_res=0.25, 
                                    base_sub_res=3.0,
                                    min_cluster_size=10,
                                    max_subclusters_per_parent=20,
                                    adaptive_sub_res=True,
                                    k=15):
    """
    Run constrained hierarchical Leiden (same as test script).
    Returns: hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine
    """
    # Step 1: Global coarse clustering
    coarse_labels, coarse_mod = leiden_clustering(embeddings, resolution=coarse_res, k=k)
    unique_coarse = np.unique(coarse_labels[coarse_labels != -1])
    
    logger.info(f"  Coarse (res={coarse_res}): {len(unique_coarse)} clusters, modularity={coarse_mod:.4f}")
    
    # Step 2: Within each coarse cluster, run constrained Leiden
    hierarchical_labels = np.full(len(embeddings), -1, dtype=int)
    sub_cluster_id = 0
    cluster_info = {}
    coarse_to_fine = defaultdict(list)
    
    for coarse_id in unique_coarse:
        mask = coarse_labels == coarse_id
        indices = np.where(mask)[0]
        cluster_size = len(indices)
        
        if cluster_size < min_cluster_size * 2:
            hierarchical_labels[indices] = sub_cluster_id
            cluster_info[sub_cluster_id] = {
                'coarse_id': int(coarse_id), 'sub_id': 0,
                'size': cluster_size, 'too_small': True,
                'sub_res_used': None
            }
            coarse_to_fine[int(coarse_id)].append(sub_cluster_id)
            sub_cluster_id += 1
            continue
        
        subset_embeddings = embeddings[indices]
        
        # Determine adaptive sub-resolution based on cluster size
        if adaptive_sub_res:
            if cluster_size < 500:
                sub_res = 1.5
            elif cluster_size < 2000:
                sub_res = 2.0
            else:
                sub_res = base_sub_res
        else:
            sub_res = base_sub_res
        
        # Run Leiden within subset
        sub_labels, sub_mod = leiden_clustering(subset_embeddings, resolution=sub_res, k=k)
        unique_sub = np.unique(sub_labels[sub_labels != -1])
        
        logger.info(f"    Coarse {coarse_id} ({cluster_size} docs): "
                    f"{len(unique_sub)} sub-clusters at sub_res={sub_res:.2f}, modularity={sub_mod:.4f}")
        
        # Filter out sub-clusters that are too small
        valid_sub = []
        for sub_id in unique_sub:
            sub_mask = sub_labels == sub_id
            sub_size = sub_mask.sum()
            if sub_size >= min_cluster_size:
                valid_sub.append(sub_id)
        
        # If too many sub-clusters, keep largest
        if len(valid_sub) > max_subclusters_per_parent:
            sub_sizes = [(sid, (sub_labels == sid).sum()) for sid in valid_sub]
            sub_sizes.sort(key=lambda x: x[1], reverse=True)
            valid_sub = [sid for sid, _ in sub_sizes[:max_subclusters_per_parent]]
        
        # Assign global labels
        for sub_id in valid_sub:
            sub_mask = sub_labels == sub_id
            global_indices = indices[sub_mask]
            hierarchical_labels[global_indices] = sub_cluster_id
            
            cluster_info[sub_cluster_id] = {
                'coarse_id': int(coarse_id), 'sub_id': int(sub_id),
                'size': int(len(global_indices)), 'too_small': False,
                'sub_res_used': sub_res
            }
            coarse_to_fine[int(coarse_id)].append(sub_cluster_id)
            sub_cluster_id += 1
        
        # Handle documents in filtered-out tiny sub-clusters
        assigned_mask = np.isin(sub_labels, valid_sub)
        unassigned_indices = indices[~assigned_mask]
        if len(unassigned_indices) > 0:
            hierarchical_labels[unassigned_indices] = sub_cluster_id
            cluster_info[sub_cluster_id] = {
                'coarse_id': int(coarse_id), 'sub_id': -1,
                'size': int(len(unassigned_indices)), 'too_small': False,
                'sub_res_used': sub_res, 'is_remainder': True
            }
            coarse_to_fine[int(coarse_id)].append(sub_cluster_id)
            sub_cluster_id += 1
    
    return hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine


def build_decision_clusters_from_labels(hierarchical_labels, coarse_labels, metadata_ids):
    """Build decision_clusters.json format from label arrays."""
    decision_clusters = {}
    for i, did in enumerate(metadata_ids):
        decision_clusters[did] = {
            'res_0.25': int(coarse_labels[i]) if coarse_labels[i] != -1 else -1,
            'hierarchical': int(hierarchical_labels[i]) if hierarchical_labels[i] != -1 else -1,
        }
    return decision_clusters


def compute_cluster_metadata(embeddings, hierarchical_labels, coarse_labels, metadata_by_id, metadata_ids):
    """Compute cluster metadata for both coarse and hierarchical levels."""
    cluster_metadata = {}
    
    # Coarse (res_0.25)
    coarse_clusters = defaultdict(list)
    for i, did in enumerate(metadata_ids):
        cid = coarse_labels[i]
        if cid != -1:
            coarse_clusters[cid].append(did)
    
    cluster_metadata['res_0.25'] = {}
    for cid, dids in coarse_clusters.items():
        cluster_meta = [metadata_by_id[did] for did in dids]
        langs = Counter(m.get('language') for m in cluster_meta if m.get('language'))
        branches = Counter(m.get('branch') for m in cluster_meta if m.get('branch'))
        areas = Counter(m.get('legal_area') for m in cluster_meta if m.get('legal_area'))
        years = Counter(m.get('year') for m in cluster_meta if m.get('year'))
        chambers = Counter(m.get('chamber') for m in cluster_meta if m.get('chamber'))
        
        dominant_lang = langs.most_common(1)[0] if langs else (None, 0)
        dominant_branch = branches.most_common(1)[0] if branches else (None, 0)
        dominant_area = areas.most_common(1)[0] if areas else (None, 0)
        
        cluster_metadata['res_0.25'][int(cid)] = {
            'size': len(dids),
            'dominant_lang': dominant_lang[0],
            'lang_purity': dominant_lang[1] / len(dids) if dids else 0,
            'dominant_branch': dominant_branch[0],
            'branch_purity': dominant_branch[1] / len(dids) if dids else 0,
            'dominant_area': dominant_area[0],
            'area_count': len(areas),
            'top_areas': {str(k): int(v) for k, v in areas.most_common(5)},
            'top_branches': {str(k): int(v) for k, v in branches.most_common(5)},
            'year_dist': {str(k): int(v) for k, v in years.most_common()},
            'top_chambers': {str(k): int(v) for k, v in chambers.most_common(3)},
        }
    
    # Hierarchical (fine)
    fine_clusters = defaultdict(list)
    for i, did in enumerate(metadata_ids):
        cid = hierarchical_labels[i]
        if cid != -1:
            fine_clusters[cid].append(did)
    
    cluster_metadata['hierarchical'] = {}
    for cid, dids in fine_clusters.items():
        cluster_meta = [metadata_by_id[did] for did in dids]
        langs = Counter(m.get('language') for m in cluster_meta if m.get('language'))
        branches = Counter(m.get('branch') for m in cluster_meta if m.get('branch'))
        areas = Counter(m.get('legal_area') for m in cluster_meta if m.get('legal_area'))
        years = Counter(m.get('year') for m in cluster_meta if m.get('year'))
        chambers = Counter(m.get('chamber') for m in cluster_meta if m.get('chamber'))
        
        dominant_lang = langs.most_common(1)[0] if langs else (None, 0)
        dominant_branch = branches.most_common(1)[0] if branches else (None, 0)
        dominant_area = areas.most_common(1)[0] if areas else (None, 0)
        
        cluster_metadata['hierarchical'][int(cid)] = {
            'size': len(dids),
            'dominant_lang': dominant_lang[0],
            'lang_purity': dominant_lang[1] / len(dids) if dids else 0,
            'dominant_branch': dominant_branch[0],
            'branch_purity': dominant_branch[1] / len(dids) if dids else 0,
            'dominant_area': dominant_area[0],
            'area_count': len(areas),
            'top_areas': {str(k): int(v) for k, v in areas.most_common(5)},
            'top_branches': {str(k): int(v) for k, v in branches.most_common(5)},
            'year_dist': {str(k): int(v) for k, v in years.most_common()},
            'top_chambers': {str(k): int(v) for k, v in chambers.most_common(3)},
        }
    
    # Also add intermediate res_0.5
    labels_05, _ = leiden_clustering(embeddings, resolution=0.5, k=15)
    coarse_05_clusters = defaultdict(list)
    for i, did in enumerate(metadata_ids):
        cid = labels_05[i]
        if cid != -1:
            coarse_05_clusters[cid].append(did)
    
    cluster_metadata['res_0.5'] = {}
    for cid, dids in coarse_05_clusters.items():
        cluster_meta = [metadata_by_id[did] for did in dids]
        langs = Counter(m.get('language') for m in cluster_meta if m.get('language'))
        branches = Counter(m.get('branch') for m in cluster_meta if m.get('branch'))
        areas = Counter(m.get('legal_area') for m in cluster_meta if m.get('legal_area'))
        years = Counter(m.get('year') for m in cluster_meta if m.get('year'))
        chambers = Counter(m.get('chamber') for m in cluster_meta if m.get('chamber'))
        
        dominant_lang = langs.most_common(1)[0] if langs else (None, 0)
        dominant_branch = branches.most_common(1)[0] if branches else (None, 0)
        dominant_area = areas.most_common(1)[0] if areas else (None, 0)
        
        cluster_metadata['res_0.5'][int(cid)] = {
            'size': len(dids),
            'dominant_lang': dominant_lang[0],
            'lang_purity': dominant_lang[1] / len(dids) if dids else 0,
            'dominant_branch': dominant_branch[0],
            'branch_purity': dominant_branch[1] / len(dids) if dids else 0,
            'dominant_area': dominant_area[0],
            'area_count': len(areas),
            'top_areas': {str(k): int(v) for k, v in areas.most_common(5)},
            'top_branches': {str(k): int(v) for k, v in branches.most_common(5)},
            'year_dist': {str(k): int(v) for k, v in years.most_common()},
            'top_chambers': {str(k): int(v) for k, v in chambers.most_common(3)},
        }
    
    return cluster_metadata, labels_05


def build_nesting(coarse_labels, hierarchical_labels, metadata_ids):
    """Build parent-child nesting from coarse to hierarchical."""
    child_to_parent = {}
    fine_to_coarse = defaultdict(set)
    
    for i, did in enumerate(metadata_ids):
        coarse_cid = coarse_labels[i]
        fine_cid = hierarchical_labels[i]
        if coarse_cid != -1 and fine_cid != -1:
            fine_to_coarse[fine_cid].add(coarse_cid)
    
    for fine_cid, coarse_set in fine_to_coarse.items():
        if len(coarse_set) == 1:
            child_to_parent[int(fine_cid)] = int(list(coarse_set)[0])
    
    parent_to_children = defaultdict(list)
    for child, parent in child_to_parent.items():
        parent_to_children[parent].append(child)
    
    consistent = sum(1 for s in fine_to_coarse.values() if len(s) == 1)
    total = len(fine_to_coarse)
    
    return {
        'coarser_resolution': 0.25,
        'finer_resolution': 'hierarchical',
        'child_to_parent': child_to_parent,
        'parent_to_children': dict(parent_to_children),
        'strict_nesting_consistency': consistent / total if total > 0 else 0,
    }


def compute_zoom_coherence(coarse_labels, hierarchical_labels, metadata_by_id, metadata_ids):
    """Compute zoom coherence from coarse to hierarchical."""
    coarse_members = defaultdict(list)
    fine_members = defaultdict(list)
    
    for i, did in enumerate(metadata_ids):
        cc = coarse_labels[i]
        fc = hierarchical_labels[i]
        if cc != -1:
            coarse_members[cc].append(did)
        if fc != -1:
            fine_members[fc].append(did)
    
    improvements = []
    parent_details = {}
    
    for coarse_cid, coarse_dids in coarse_members.items():
        if len(coarse_dids) < MIN_CLUSTER_SIZE:
            continue
        
        coarse_branches = [metadata_by_id[did].get('branch') for did in coarse_dids]
        coarse_branches = [b for b in coarse_branches if b and b not in ('null', 'unknown')]
        if not coarse_branches:
            continue
        coarse_purity = Counter(coarse_branches).most_common(1)[0][1] / len(coarse_branches)
        
        # Find children of this parent
        child_clusters = []
        for fine_cid, fine_dids in fine_members.items():
            if len(fine_dids) < MIN_CLUSTER_SIZE:
                continue
            coarse_parents = [coarse_labels[metadata_ids.index(did)] for did in fine_dids if did in metadata_ids]
            if coarse_parents:
                majority_parent = Counter(coarse_parents).most_common(1)[0][0]
                if majority_parent == coarse_cid:
                    child_clusters.append(fine_cid)
        
        if not child_clusters:
            continue
        
        child_purities = []
        for fine_cid in child_clusters:
            fine_dids = fine_members[fine_cid]
            fine_branches = [metadata_by_id[did].get('branch') for did in fine_dids]
            fine_branches = [b for b in fine_branches if b and b not in ('null', 'unknown')]
            if fine_branches:
                child_purities.append(Counter(fine_branches).most_common(1)[0][1] / len(fine_branches))
        
        if child_purities:
            mean_child_purity = np.mean(child_purities)
            improvements.append(mean_child_purity - coarse_purity)
            parent_details[int(coarse_cid)] = {
                'coarse_purity': float(coarse_purity),
                'mean_child_purity': float(mean_child_purity),
                'improvement': float(mean_child_purity - coarse_purity),
                'n_children': len(child_clusters),
            }
    
    return {
        'coarser_resolution': 0.25,
        'finer_resolution': 'hierarchical',
        'mean_improvement': float(np.mean(improvements)) if improvements else 0,
        'improvement_rate': float(sum(1 for j in improvements if j > 0) / len(improvements)) if improvements else 0,
        'n_parents': len(parent_details),
        'parent_details': parent_details,
    }


def compute_purity_per_res(labels, metadata_by_id, metadata_ids):
    """Compute mean purity per resolution."""
    cluster_members = defaultdict(list)
    for i, did in enumerate(metadata_ids):
        cid = labels[i]
        if cid != -1:
            cluster_members[cid].append(did)
    
    branch_purities = []
    area_purities = []
    for cid, dids in cluster_members.items():
        if len(dids) < MIN_CLUSTER_SIZE:
            continue
        branch_vals = [metadata_by_id[did].get('branch') for did in dids]
        branch_vals = [v for v in branch_vals if v and v not in ('null', 'unknown')]
        if branch_vals:
            branch_purities.append(Counter(branch_vals).most_common(1)[0][1] / len(branch_vals))
        
        area_vals = [metadata_by_id[did].get('legal_area') for did in dids]
        area_vals = [v for v in area_vals if v and v not in ('null', 'unknown')]
        if area_vals:
            area_purities.append(Counter(area_vals).most_common(1)[0][1] / len(area_vals))
    
    return {
        'mean_branch_purity': float(np.mean(branch_purities)) if branch_purities else 0,
        'mean_area_purity': float(np.mean(area_purities)) if area_purities else 0,
        'n_clusters': int(len([c for c in cluster_members.values() if len(c) >= MIN_CLUSTER_SIZE])),
    }


def convert(obj):
    if isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert(v) for v in obj]
    return obj


def main():
    logger.info("=" * 70)
    logger.info("RUN CONSTRAINED HIERARCHICAL LEIDEN ON 3 PRODUCTION TF-IDF MODES")
    logger.info("=" * 70)
    
    metadata_by_id, metadata_ids = load_metadata()
    n_meta = len(metadata_ids)
    logger.info(f"ACCEPTED metadata: {n_meta} entries")
    
    for mode_name, config in PRODUCTION_MODES.items():
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {mode_name}")
        logger.info(f"Config: {config}")
        logger.info(f"{'='*60}")
        
        embeddings = load_embeddings(mode_name)
        if embeddings is None:
            logger.error(f"  FAILED: Embeddings not found for {mode_name}")
            continue
        
        if len(embeddings) > n_meta:
            embeddings = embeddings[:n_meta]
            logger.info(f"  Truncated embeddings to {n_meta}")
        elif len(embeddings) < n_meta:
            logger.error(f"  Embeddings ({len(embeddings)}) < metadata ({n_meta})")
            continue
        
        # Run constrained hierarchical Leiden
        logger.info("  Running constrained hierarchical Leiden...")
        hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine = constrained_hierarchical_leiden(
            embeddings, metadata_ids,
            coarse_res=config.get('coarse_res', 0.25),
            base_sub_res=config.get('base_sub_res', 3.0),
            min_cluster_size=config.get('min_cluster_size', 10),
            max_subclusters_per_parent=config.get('max_subclusters_per_parent', 20),
            adaptive_sub_res=config.get('adaptive_sub_res', True),
            k=15
        )
        
        # Build res_0.5 labels
        labels_05, _ = leiden_clustering(embeddings, resolution=0.5, k=15)
        
        # Build decision clusters
        logger.info("  Building decision clusters...")
        decision_clusters = build_decision_clusters_from_labels(hierarchical_labels, coarse_labels, metadata_ids)
        
        # Build cluster metadata
        logger.info("  Computing cluster metadata...")
        cluster_metadata, labels_05 = compute_cluster_metadata(embeddings, hierarchical_labels, coarse_labels, metadata_by_id, metadata_ids)
        
        # Build nesting
        logger.info("  Building nesting...")
        nesting = build_nesting(coarse_labels, hierarchical_labels, metadata_ids)
        
        # Compute zoom coherence
        logger.info("  Computing zoom coherence...")
        zoom_coherence = compute_zoom_coherence(coarse_labels, hierarchical_labels, metadata_by_id, metadata_ids)
        
        # Compute purity per resolution
        coarse_purity = compute_purity_per_res(coarse_labels, metadata_by_id, metadata_ids)
        hierarchical_purity = compute_purity_per_res(hierarchical_labels, metadata_by_id, metadata_ids)
        res05_purity = compute_purity_per_res(labels_05, metadata_by_id, metadata_ids)
        
        # Save artifacts
        mode_output_dir = OUTPUT_DIR / mode_name
        mode_output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("  Saving artifacts...")
        
        np.save(mode_output_dir / "labels_res_0.25.npy", coarse_labels)
        np.save(mode_output_dir / "labels_res_0.5.npy", labels_05)
        np.save(mode_output_dir / "labels_hierarchical_best.npy", hierarchical_labels)
        np.save(mode_output_dir / "labels_coarse_0.5.npy", labels_05)
        
        with open(mode_output_dir / "cluster_metadata.json", 'w') as f:
            json.dump(convert(cluster_metadata), f, indent=2)
        
        with open(mode_output_dir / "zoom_mappings.json", 'w') as f:
            json.dump(convert({'0.25_to_hierarchical': nesting}), f, indent=2)
        
        with open(mode_output_dir / "zoom_coherence.json", 'w') as f:
            json.dump(convert({'0.25_to_hierarchical': zoom_coherence}), f, indent=2)
        
        with open(mode_output_dir / "decision_clusters.json", 'w') as f:
            json.dump(convert(decision_clusters), f)
        
        # Summary
        logger.info(f"\n  === {mode_name} Summary ===")
        logger.info(f"  Coarse (0.25): {len(set(coarse_labels[coarse_labels!=-1]))} clusters, branch={coarse_purity['mean_branch_purity']:.4f}, area={coarse_purity['mean_area_purity']:.4f}")
        logger.info(f"  Intermediate (0.5): {len(set(labels_05[labels_05!=-1]))} clusters, branch={res05_purity['mean_branch_purity']:.4f}, area={res05_purity['mean_area_purity']:.4f}")
        logger.info(f"  Hierarchical: {len(set(hierarchical_labels[hierarchical_labels!=-1]))} clusters, branch={hierarchical_purity['mean_branch_purity']:.4f}, area={hierarchical_purity['mean_area_purity']:.4f}")
        logger.info(f"  Nesting consistency: {nesting['strict_nesting_consistency']:.4f}")
        logger.info(f"  Zoom coherence: improvement_rate={zoom_coherence['improvement_rate']:.4f}, mean_improvement={zoom_coherence['mean_improvement']:.4f}")
        
        # Save summary
        summary = {
            "run_id": f"product_integration_constrained_production_{mode_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "direction_version": 34,
            "mode_id": mode_name,
            "hypothesis": "Constrained hierarchical Leiden on 174k TF-IDF embeddings produces production-ready multi-resolution map with perfect nesting, zero fragmentation, and legal zoom refinement (v26 PASS)",
            "frozen_sample": f"{n_meta} BGer decisions (2000-2026)",
            "frozen_metric": "Branch/area purity, strict nesting, zoom coherence, fragmentation",
            "success_rule": "v26: branch/area improvement, improvement_rate > 0.5, singleton_fraction < 0.01, nesting = 1.0",
            "config": config,
            "results": {
                "coarse": coarse_purity,
                "intermediate": res05_purity,
                "hierarchical": hierarchical_purity,
                "nesting": nesting,
                "zoom_coherence": zoom_coherence,
            },
            "note": "This is the v26-PASSING constrained hierarchical method applied to the 3 production modes that PASSED hierarchical_v1 at full 174k. Coarse levels (0.25, 0.5) enable domain navigation; hierarchical level enables micro-cluster navigation. Perfect nesting guaranteed by construction.",
        }
        
        with open(mode_output_dir / "product_integration_summary.json", 'w') as f:
            json.dump(convert(summary), f, indent=2)
        
        logger.info(f"  Saved to {mode_output_dir}")
    
    logger.info("\n=== Product integration for 3 PRODUCTION TF-IDF constrained hierarchical modes complete ===")


if __name__ == "__main__":
    main()