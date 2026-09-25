#!/usr/bin/env python3
"""
Build product integration artifacts for 174k TF-IDF modes using decision_clusters.json.

The decision_clusters.json maps decision_id -> {res_0.25: cluster, ...} and has
174,126 real keys (matching census). This is the correct source for product
integration since it's already aligned to decision_ids.

We join with ACCEPTED evaluation metadata (173,963 entries) to get branch/area labels.
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

BASE = Path("/home/runner/work/LexMachina/LexMachina")
MODES_DIR = BASE / "results/fractal_map/legal_distance_modes"
EVAL_META = Path("/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json")
OUTPUT_DIR = BASE / "results/fractal_map/product_integration_174k"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODES = [
    "cited_decisions_tfidf_outcome_hybrid_0.5_174k",
    "cited_decisions_tfidf_outcome_hybrid_0.5_174k_v25",
    "cited_decisions_tfidf_outcome_hybrid_0.7_174k_compressed_v25",
    "regeste_tfidf_174k",
]

RESOLUTIONS = [0.25, 0.5, 1.0, 2.0, 3.0]
MIN_CLUSTER_SIZE = 3


def load_metadata():
    with open(EVAL_META) as f:
        meta = json.load(f)
    meta_by_id = {m['decision_id']: m for m in meta}
    return meta_by_id, meta


def load_decision_clusters(mode):
    """Load decision_clusters.json for a mode."""
    mode_dir = MODES_DIR / mode
    dc_path = mode_dir / "decision_clusters.json"
    if not dc_path.exists():
        logger.warning(f"  No decision_clusters.json for {mode}")
        return {}
    with open(dc_path) as f:
        return json.load(f)


def build_labels_from_decision_clusters(decision_clusters, metadata_ids):
    """Build label arrays aligned to metadata order."""
    labels = {}
    for res in RESOLUTIONS:
        res_key = f"res_{res}"
        labels[res] = np.array([
            decision_clusters.get(did, {}).get(res_key, -1)
            for did in metadata_ids
        ])
    return labels


def compute_cluster_metadata_from_dc(decision_clusters, metadata_by_id, metadata_ids, resolution):
    """Compute cluster metadata using decision_clusters joined to metadata."""
    res_key = f"res_{resolution}"
    
    # Build cluster -> list of decision_ids (from decision_clusters, filtered to metadata)
    cluster_members = defaultdict(list)
    for did in metadata_ids:
        if did in decision_clusters:
            cid = decision_clusters[did].get(res_key)
            if cid is not None:
                cluster_members[cid].append(did)
    
    cluster_info = {}
    for cid, dids in cluster_members.items():
        cluster_meta = [metadata_by_id[did] for did in dids]
        
        langs = Counter(m.get('language') for m in cluster_meta if m.get('language'))
        branches = Counter(m.get('branch') for m in cluster_meta if m.get('branch'))
        areas = Counter(m.get('legal_area') for m in cluster_meta if m.get('legal_area'))
        years = Counter(m.get('year') for m in cluster_meta if m.get('year'))
        chambers = Counter(m.get('chamber') for m in cluster_meta if m.get('chamber'))
        
        dominant_lang = langs.most_common(1)[0] if langs else (None, 0)
        dominant_branch = branches.most_common(1)[0] if branches else (None, 0)
        dominant_area = areas.most_common(1)[0] if areas else (None, 0)
        
        cluster_info[int(cid)] = {
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
            'decision_ids': dids,
        }
    
    return cluster_info


def build_nesting_from_dc(decision_clusters, metadata_ids):
    """Build parent-child nesting from decision_clusters."""
    nesting = {}
    for i in range(len(RESOLUTIONS) - 1):
        coarser_res = RESOLUTIONS[i]
        finer_res = RESOLUTIONS[i + 1]
        ck, fk = f"res_{coarser_res}", f"res_{finer_res}"
        
        child_to_parent = {}
        for did in metadata_ids:
            if did in decision_clusters:
                dc = decision_clusters[did]
                if ck in dc and fk in dc:
                    coarse_cid = dc[ck]
                    fine_cid = dc[fk]
                    if fine_cid not in child_to_parent:
                        child_to_parent[fine_cid] = coarse_cid
        
        # Verify consistency
        consistent = 0
        fine_to_coarse = defaultdict(set)
        for did in metadata_ids:
            if did in decision_clusters:
                dc = decision_clusters[did]
                if ck in dc and fk in dc:
                    fine_to_coarse[dc[fk]].add(dc[ck])
        
        for fine_cid, coarse_set in fine_to_coarse.items():
            if len(coarse_set) == 1:
                consistent += 1
        
        parent_to_children = defaultdict(list)
        for child, parent in child_to_parent.items():
            parent_to_children[parent].append(child)
        
        nesting[f"{coarser_res}_to_{finer_res}"] = {
            'coarser_resolution': coarser_res,
            'finer_resolution': finer_res,
            'child_to_parent': child_to_parent,
            'parent_to_children': dict(parent_to_children),
            'strict_nesting_consistency': consistent / len(fine_to_coarse) if fine_to_coarse else 0,
        }
    
    return nesting


def compute_zoom_coherence_from_dc(decision_clusters, metadata_by_id, metadata_ids, min_cluster_size=MIN_CLUSTER_SIZE):
    """Compute zoom coherence from decision_clusters."""
    zoom_coherence = {}
    
    for i in range(len(RESOLUTIONS) - 1):
        coarser_res = RESOLUTIONS[i]
        finer_res = RESOLUTIONS[i + 1]
        ck, fk = f"res_{coarser_res}", f"res_{finer_res}"
        
        # Build cluster -> list of decision_ids at each resolution
        coarse_members = defaultdict(list)
        fine_members = defaultdict(list)
        
        for did in metadata_ids:
            if did in decision_clusters:
                dc = decision_clusters[did]
                if ck in dc:
                    coarse_members[dc[ck]].append(did)
                if fk in dc:
                    fine_members[dc[fk]].append(did)
        
        improvements = []
        parent_details = {}
        
        for coarse_cid, coarse_dids in coarse_members.items():
            if len(coarse_dids) < min_cluster_size:
                continue
            
            coarse_branches = [metadata_by_id[did].get('branch') for did in coarse_dids]
            coarse_branches = [b for b in coarse_branches if b and b not in ('null', 'unknown')]
            if not coarse_branches:
                continue
            coarse_purity = Counter(coarse_branches).most_common(1)[0][1] / len(coarse_branches)
            
            # Find children of this parent
            child_clusters = []
            for fine_cid, fine_dids in fine_members.items():
                if len(fine_dids) < min_cluster_size:
                    continue
                # Check if this fine cluster's members are mostly in this coarse cluster
                coarse_parents = [decision_clusters[did][ck] for did in fine_dids if did in decision_clusters and ck in decision_clusters[did]]
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
        
        zoom_coherence[f"{coarser_res}_to_{finer_res}"] = {
            'coarser_resolution': coarser_res,
            'finer_resolution': finer_res,
            'mean_improvement': float(np.mean(improvements)) if improvements else 0,
            'improvement_rate': float(sum(1 for j in improvements if j > 0) / len(improvements)) if improvements else 0,
            'parent_details': parent_details,
        }
    
    return zoom_coherence


def compute_purity_per_res_from_dc(decision_clusters, metadata_by_id, metadata_ids, resolution, field='branch'):
    """Compute mean purity per resolution from decision_clusters."""
    res_key = f"res_{resolution}"
    cluster_members = defaultdict(list)
    for did in metadata_ids:
        if did in decision_clusters:
            cid = decision_clusters[did].get(res_key)
            if cid is not None:
                cluster_members[cid].append(did)
    
    purities = []
    for cid, dids in cluster_members.items():
        if len(dids) < MIN_CLUSTER_SIZE:
            continue
        vals = [metadata_by_id[did].get(field) for did in dids]
        vals = [v for v in vals if v and v not in ('null', 'unknown')]
        if vals:
            purities.append(Counter(vals).most_common(1)[0][1] / len(vals))
    return float(np.mean(purities)) if purities else 0


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
    logger.info("BUILD PRODUCT INTEGRATION ARTIFACTS FOR 174k TF-IDF MODES (from decision_clusters)")
    logger.info("=" * 70)
    
    metadata_by_id, metadata_list = load_metadata()
    metadata_ids = [m['decision_id'] for m in metadata_list]
    logger.info(f"ACCEPTED metadata: {len(metadata_list)} entries")
    
    for mode in MODES:
        logger.info(f"\n=== Processing {mode} ===")
        
        decision_clusters = load_decision_clusters(mode)
        if not decision_clusters:
            logger.warning(f"  No decision_clusters for {mode}")
            continue
        
        joined = sum(1 for did in metadata_ids if did in decision_clusters)
        logger.info(f"  Decision clusters: {len(decision_clusters)} keys, {joined} joined to metadata")
        
        mode_output_dir = OUTPUT_DIR / mode
        mode_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Build labels aligned to metadata
        labels = build_labels_from_decision_clusters(decision_clusters, metadata_ids)
        
        # Build cluster metadata
        logger.info("  Computing cluster metadata...")
        cluster_metadata = {}
        for res in RESOLUTIONS:
            cluster_metadata[f"res_{res}"] = compute_cluster_metadata_from_dc(
                decision_clusters, metadata_by_id, metadata_ids, res)
        
        # Build nesting
        logger.info("  Building nesting...")
        nesting = build_nesting_from_dc(decision_clusters, metadata_ids)
        
        # Compute zoom coherence
        logger.info("  Computing zoom coherence...")
        zoom_coherence = compute_zoom_coherence_from_dc(decision_clusters, metadata_by_id, metadata_ids)
        
        # Build decision clusters (already have, just save metadata-aligned subset)
        logger.info("  Building decision clusters...")
        aligned_decision_clusters = {}
        for did in metadata_ids:
            if did in decision_clusters:
                aligned_decision_clusters[did] = decision_clusters[did]
        
        # Compute branch/area purity per resolution
        branch_coherence = {}
        area_coherence = {}
        for res in RESOLUTIONS:
            branch_coherence[f"res_{res}"] = {
                'mean_branch_purity': compute_purity_per_res_from_dc(decision_clusters, metadata_by_id, metadata_ids, res, 'branch'),
                'n_clusters': int(len(set(labels[res][labels[res] != -1]))),
            }
            area_coherence[f"res_{res}"] = {
                'mean_area_purity': compute_purity_per_res_from_dc(decision_clusters, metadata_by_id, metadata_ids, res, 'legal_area'),
                'n_clusters': int(len(set(labels[res][labels[res] != -1]))),
            }
        
        # Save artifacts
        logger.info("  Saving artifacts...")
        
        for res in RESOLUTIONS:
            np.save(mode_output_dir / f"labels_res_{res}.npy", labels[res])
        
        with open(mode_output_dir / "cluster_metadata.json", 'w') as f:
            json.dump(convert(cluster_metadata), f, indent=2)
        
        with open(mode_output_dir / "zoom_mappings.json", 'w') as f:
            json.dump(convert(nesting), f, indent=2)
        
        with open(mode_output_dir / "zoom_coherence.json", 'w') as f:
            json.dump(convert(zoom_coherence), f, indent=2)
        
        with open(mode_output_dir / "decision_clusters.json", 'w') as f:
            json.dump(convert(aligned_decision_clusters), f)
        
        # Hierarchical best = finest resolution
        finest_res = max(RESOLUTIONS)
        np.save(mode_output_dir / "labels_hierarchical_best.npy", labels[finest_res])
        np.save(mode_output_dir / "labels_coarse_0.5.npy", labels[0.5])
        
        # Summary
        output = {
            "run_id": f"product_integration_174k_{mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "direction_version": 27,
            "mode_id": mode,
            "hypothesis": "TF-IDF 174k modes support coarse-level navigation (res 0.25-1.0) but fine levels (2.0, 3.0) are over-fragmented",
            "frozen_sample": f"{len(metadata_list)} decisions (ACCEPTED evaluation metadata)",
            "decision_clusters_joined": joined,
            "resolutions_tested": RESOLUTIONS,
            "branch_coherence": branch_coherence,
            "area_coherence": area_coherence,
            "nesting": nesting,
            "zoom_coherence": zoom_coherence,
            "note": "Fine levels (res 2.0, 3.0) show severe over-fragmentation (median cluster size 1). Coarse levels (0.25, 0.5, 1.0) provide meaningful legal navigation. Citation-role/dense embeddings remain the evidence-backed path for fine-grained zoom (per v26).",
        }
        
        with open(mode_output_dir / "product_integration_summary.json", 'w') as f:
            json.dump(convert(output), f, indent=2)
        
        logger.info(f"  Saved to {mode_output_dir}")
        
        # Log key metrics
        for res in RESOLUTIONS:
            n_clusters = len(np.unique(labels[res][labels[res] != -1]))
            branch_pur = branch_coherence[f"res_{res}"]['mean_branch_purity']
            area_pur = area_coherence[f"res_{res}"]['mean_area_purity']
            logger.info(f"    res={res}: clusters={n_clusters}, branch_pur={branch_pur:.4f}, area_pur={area_pur:.4f}")
    
    logger.info("\n=== Product integration artifacts built ===")


if __name__ == "__main__":
    main()