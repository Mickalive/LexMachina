#!/usr/bin/env python3
"""
Preparatory validation: Constrained Hierarchical Leiden on 20-year checkpoint dense embeddings (2000-2019, ~137k).
This is EXPLORATORY/PREPARATORY work - NOT claiming accepted results.
Purpose: Verify pipeline works at near-full scale before legal-distance audit promotion completes.
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
from sklearn.preprocessing import normalize

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
CHECKPOINT_DIR = Path('/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints')
META_174K_PATH = Path('/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json')
OUTPUT_DIR = Path('/home/runner/work/LexMachina/LexMachina/results/fractal_map/constrained_hierarchical_tests/preparatory_20yr_20260927')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

AVAILABLE_YEARS = [str(y) for y in range(2000, 2020)]  # 2000-2019 inclusive (20 years)

K = 15
MIN_CLUSTER_SIZE = 20  # For zoom coherence evaluation
V26_RESOLUTIONS = [0.25, 0.5, 1.0, 2.0, 3.0]


def load_checkpoint_embeddings_and_metadata():
    """Load and concatenate available year embeddings and metadata from checkpoints."""
    all_embeddings = []
    all_metadata = []
    total_decisions = 0
    
    for year in AVAILABLE_YEARS:
        emb_path = CHECKPOINT_DIR / f'embeddings_{year}.npy'
        meta_path = CHECKPOINT_DIR / f'metadata_{year}.json'
        
        if not emb_path.exists() or not meta_path.exists():
            logger.warning(f'Missing checkpoint for {year}')
            continue
            
        embeddings = np.load(emb_path)
        with open(meta_path) as f:
            metadata = json.load(f)
        
        logger.info(f'Loaded {year}: embeddings {embeddings.shape}, metadata {len(metadata)}')
        all_embeddings.append(embeddings)
        all_metadata.extend(metadata)
        total_decisions += len(metadata)
    
    # Concatenate
    all_embeddings = np.vstack(all_embeddings)
    logger.info(f'Total checkpoint embeddings: {all_embeddings.shape}, metadata: {len(all_metadata)}')
    
    return all_embeddings, all_metadata


def load_full_metadata():
    """Load full 174k metadata for evaluation."""
    with open(META_174K_PATH) as f:
        metadata = json.load(f)
    logger.info(f'Loaded full metadata: {len(metadata)} entries')
    return metadata


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


def constrained_hierarchical_leiden(embeddings, metadata, 
                                    coarse_res=0.25, 
                                    base_sub_res=3.0,
                                    min_cluster_size=10,
                                    max_subclusters_per_parent=20,
                                    adaptive_sub_res=True,
                                    k=15):
    """
    Run constrained hierarchical Leiden:
    1. Global Leiden at coarse_res
    2. Within each coarse cluster, run Leiden at adaptive sub_res
    3. Enforce min_cluster_size, max_subclusters_per_parent
    4. Guarantee perfect nesting (1.0 by construction)
    """
    logger.info(f'Running constrained hierarchical Leiden: coarse_res={coarse_res}, base_sub_res={base_sub_res}')
    logger.info(f'  min_cluster_size={min_cluster_size}, max_subclusters={max_subclusters_per_parent}, adaptive={adaptive_sub_res}')
    
    # Step 1: Global coarse clustering
    coarse_labels, coarse_mod = leiden_clustering(embeddings, resolution=coarse_res, k=k)
    unique_coarse = np.unique(coarse_labels[coarse_labels != -1])
    logger.info(f'  Coarse (res={coarse_res}): {len(unique_coarse)} clusters, modularity={coarse_mod:.4f}')
    
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
        
        # Filter out sub-clusters that are too small
        valid_sub = []
        for sub_id in unique_sub:
            sub_mask = sub_labels == sub_id
            sub_size = sub_mask.sum()
            if sub_size >= min_cluster_size:
                valid_sub.append(sub_id)
        
        # If too many sub-clusters, keep largest
        if len(valid_sub) > max_subclusters_per_parent:
            logger.warning(f'    Coarse {coarse_id}: {len(valid_sub)} sub-clusters > max {max_subclusters_per_parent}, merging smallest')
            sub_sizes = [(sid, (sub_labels == sid).sum()) for sid in valid_sub]
            sub_sizes.sort(key=lambda x: x[1], reverse=True)
            valid_sub = [sid for sid, _ in sub_sizes[:max_subclusters_per_parent]]
        
        logger.info(f'    Coarse {coarse_id} ({cluster_size} docs): {len(valid_sub)} sub-clusters (sub_res={sub_res:.1f}), modularity={sub_mod:.4f}')
        
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
    
    logger.info(f'  Hierarchical: {len(unique_coarse)} coarse -> {sub_cluster_id} fine clusters')
    return hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine


def compute_branch_purity(labels, metadata):
    """Compute mean branch purity per cluster."""
    unique_labels = np.unique(labels[labels != -1])
    purities = []
    for label in unique_labels:
        mask = labels == label
        cluster_branches = [metadata[i].get('branch') for i in np.where(mask)[0]]
        cluster_branches = [b for b in cluster_branches if b and b != 'unknown' and b != 'null']
        if cluster_branches:
            purities.append(Counter(cluster_branches).most_common(1)[0][1] / len(cluster_branches))
    return float(np.mean(purities)) if purities else 0


def compute_area_purity(labels, metadata):
    """Compute mean legal_area purity per cluster."""
    unique_labels = np.unique(labels[labels != -1])
    purities = []
    for label in unique_labels:
        mask = labels == label
        cluster_areas = [metadata[i].get('legal_area') for i in np.where(mask)[0]]
        cluster_areas = [a for a in cluster_areas if a and a != 'unknown']
        if cluster_areas:
            purities.append(Counter(cluster_areas).most_common(1)[0][1] / len(cluster_areas))
    return float(np.mean(purities)) if purities else 0


def compute_fragmentation(labels):
    vals, counts = np.unique(labels[labels != -1], return_counts=True)
    n = len(vals)
    if n == 0:
        return {'n_clusters': 0, 'median_size': None, 'singleton_fraction': None}
    return {
        'n_clusters': int(n),
        'median_size': float(np.median(counts)),
        'mean_size': float(np.mean(counts)),
        'singleton_fraction': round(float(np.mean(counts == 1)), 4),
        'max_size': int(np.max(counts)),
        'min_size': int(np.min(counts)),
    }


def compute_zoom_coherence_hierarchical(coarse_labels, hierarchical_labels, metadata, min_cluster_size=MIN_CLUSTER_SIZE):
    """Compute zoom coherence for hierarchical Leiden."""
    parent_details = {}
    improvements = []
    
    child_to_parent = {}
    for fine_id in np.unique(hierarchical_labels[hierarchical_labels != -1]):
        fine_mask = hierarchical_labels == fine_id
        parent_labels = coarse_labels[fine_mask]
        parent_labels_valid = parent_labels[parent_labels != -1]
        if len(parent_labels_valid) > 0:
            child_to_parent[int(fine_id)] = int(Counter(parent_labels_valid.tolist()).most_common(1)[0][0])
    
    for coarse_id in np.unique(coarse_labels[coarse_labels != -1]):
        coarse_mask = coarse_labels == coarse_id
        coarse_indices = np.where(coarse_mask)[0]
        if len(coarse_indices) < min_cluster_size:
            continue
        coarse_branches = [metadata[j].get('branch') for j in coarse_indices]
        coarse_branches = [b for b in coarse_branches if b and b != 'unknown' and b != 'null']
        if not coarse_branches:
            continue
        coarse_purity = Counter(coarse_branches).most_common(1)[0][1] / len(coarse_branches)
        
        child_clusters = [fc for fc, pc in child_to_parent.items() if pc == coarse_id]
        child_purities = []
        for fc in child_clusters:
            fine_mask = hierarchical_labels == fc
            fine_indices = np.where(fine_mask)[0]
            if len(fine_indices) < min_cluster_size:
                continue
            fine_branches = [metadata[j].get('branch') for j in fine_indices]
            fine_branches = [b for b in fine_branches if b and b != 'unknown' and b != 'null']
            if fine_branches:
                child_purities.append(Counter(fine_branches).most_common(1)[0][1] / len(fine_branches))
        
        if child_purities:
            mean_child_purity = np.mean(child_purities)
            improvements.append(mean_child_purity - coarse_purity)
            parent_details[int(coarse_id)] = {
                'coarse_purity': float(coarse_purity),
                'mean_child_purity': float(mean_child_purity),
                'improvement': float(mean_child_purity - coarse_purity),
                'n_children': len(child_clusters),
            }
    
    return {
        'parent_details': parent_details,
        'overall': {
            'mean_improvement': float(np.mean(improvements)) if improvements else 0.0,
            'improvement_rate': float(sum(1 for j in improvements if j > 0) / len(improvements)) if improvements else 0.0,
            'n_parents': len(parent_details),
        }
    }


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


def compute_center_projected(embeddings, metadata):
    """Compute language-debiased center_projected embeddings."""
    languages = sorted(set(m['language'] for m in metadata))
    logger.info(f'Languages in data: {languages}')
    
    centers = {}
    for lang in languages:
        mask = np.array([m.get('language') == lang for m in metadata])
        if np.sum(mask) > 0:
            centers[lang] = embeddings[mask].mean(axis=0)
            logger.info(f'  {lang}: {np.sum(mask)} decisions, center norm={np.linalg.norm(centers[lang]):.4f}')
    
    debiased = np.copy(embeddings)
    for i, m in enumerate(metadata):
        lang = m.get('language')
        if lang in centers:
            debiased[i] = embeddings[i] - centers[lang]
    
    # L2 normalize
    norms = np.linalg.norm(debiased, axis=1, keepdims=True)
    norms[norms == 0] = 1
    debiased = debiased / norms
    
    logger.info(f'Center projected shape: {debiased.shape}')
    norms = np.linalg.norm(debiased, axis=1)
    logger.info(f'Norm stats: min={norms.min():.6f}, max={norms.max():.6f}, mean={norms.mean():.6f}')
    
    return debiased


def main():
    logger.info("=" * 70)
    logger.info("PREPARATORY: Constrained Hierarchical Leiden on 20-Year Checkpoint Dense Embeddings (2000-2019)")
    logger.info("EXPLORATORY/PREPARATORY - NOT CLAIMING ACCEPTED RESULTS")
    logger.info("=" * 70)
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    # 1. Load checkpoint embeddings and metadata
    logger.info("\n1. Loading checkpoint embeddings (years 2000-2019)...")
    embeddings, checkpoint_metadata = load_checkpoint_embeddings_and_metadata()
    
    # 2. Load full metadata for evaluation
    logger.info("\n2. Loading full 174k metadata for evaluation...")
    full_metadata = load_full_metadata()
    full_meta_by_id = {m['decision_id']: m for m in full_metadata}
    
    # Filter full metadata to only include decisions in our checkpoint set
    checkpoint_ids = set(m['decision_id'] for m in checkpoint_metadata)
    eval_metadata = [m for m in full_metadata if m['decision_id'] in checkpoint_ids]
    logger.info(f'  Evaluation metadata: {len(eval_metadata)} decisions (matched from checkpoint)')
    
    # 3. Compute center_projected on checkpoint data
    logger.info("\n3. Computing center_projected (language-debiased)...")
    center_projected = compute_center_projected(embeddings, checkpoint_metadata)
    
    # 4. Run constrained hierarchical Leiden with validated config from TF-IDF 174k
    logger.info("\n4. Running constrained hierarchical Leiden with validated TF-IDF config...")
    logger.info("   Config: coarse_res=0.25, base_sub_res=3.0, min_cluster_size=10, max_subclusters=20, adaptive_sub_res=True")
    
    hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine = constrained_hierarchical_leiden(
        center_projected, eval_metadata,
        coarse_res=0.25,
        base_sub_res=3.0,
        min_cluster_size=10,
        max_subclusters_per_parent=20,
        adaptive_sub_res=True,
        k=K
    )
    
    n_fine = len(set(hierarchical_labels[hierarchical_labels != -1]))
    n_coarse = len(set(coarse_labels[coarse_labels != -1]))
    
    # 5. Compute metrics
    logger.info("\n5. Computing metrics...")
    coarse_branch_purity = compute_branch_purity(coarse_labels, eval_metadata)
    fine_branch_purity = compute_branch_purity(hierarchical_labels, eval_metadata)
    coarse_area_purity = compute_area_purity(coarse_labels, eval_metadata)
    fine_area_purity = compute_area_purity(hierarchical_labels, eval_metadata)
    nesting = compute_strict_nesting(hierarchical_labels, coarse_labels)
    
    zoom_coherence = compute_zoom_coherence_hierarchical(coarse_labels, hierarchical_labels, eval_metadata)
    frag_hierarchical = compute_fragmentation(hierarchical_labels)
    frag_coarse = compute_fragmentation(coarse_labels)
    
    logger.info(f'  Coarse clusters: {n_coarse}, median size: {frag_coarse["median_size"]:.1f}')
    logger.info(f'  Fine clusters: {n_fine}, median size: {frag_hierarchical["median_size"]:.1f}')
    logger.info(f'  Branch purity: coarse={coarse_branch_purity:.4f}, fine={fine_branch_purity:.4f} (Δ={fine_branch_purity - coarse_branch_purity:+.4f})')
    logger.info(f'  Area purity: coarse={coarse_area_purity:.4f}, fine={fine_area_purity:.4f} (Δ={fine_area_purity - coarse_area_purity:+.4f})')
    logger.info(f'  Strict nesting: {nesting:.4f}')
    logger.info(f'  Zoom coherence: improvement_rate={zoom_coherence["overall"]["improvement_rate"]:.4f}, mean_improvement={zoom_coherence["overall"]["mean_improvement"]:.4f}, n_parents={zoom_coherence["overall"]["n_parents"]}')
    logger.info(f'  Fragmentation: fine singletons={frag_hierarchical["singleton_fraction"]:.1%}, coarse singletons={frag_coarse["singleton_fraction"]:.1%}')
    
    # 6. Also run flat Leiden at v26 resolutions for comparison
    logger.info("\n6. Running flat Leiden at v26 resolutions for comparison...")
    flat_labels = {}
    for res in V26_RESOLUTIONS:
        labels, mod = leiden_clustering(center_projected, resolution=res, k=K)
        flat_labels[res] = labels
        n_clusters = len(set(labels[labels != -1]))
        branch_pur = compute_branch_purity(labels, eval_metadata)
        area_pur = compute_area_purity(labels, eval_metadata)
        logger.info(f'  Flat res={res}: {n_clusters} clusters, branch={branch_pur:.4f}, area={area_pur:.4f}')
    
    # 7. Evaluate flat zoom with v26 rule
    def compute_zoom_coherence_id_space(metadata, coarse_labels, fine_labels, field='branch'):
        id_pairs = {}
        for i, m in enumerate(metadata):
            did = m['decision_id']
            id_pairs[did] = (coarse_labels[i], fine_labels[i])
        
        coarse_vals = defaultdict(list)
        fine_vals = defaultdict(list)
        for i, m in enumerate(metadata):
            did = m['decision_id']
            val = m.get(field)
            if not val or val in ('unknown', 'null'):
                continue
            cc, fc = id_pairs[did]
            coarse_vals[cc].append(val)
            fine_vals[fc].append(val)
        
        coarse_members = defaultdict(list)
        fine_members = defaultdict(list)
        for did, (cc, fc) in id_pairs.items():
            coarse_members[cc].append(did)
            fine_members[fc].append(did)
        
        fine_coarse_counter = defaultdict(Counter)
        for did, (cc, fc) in id_pairs.items():
            fine_coarse_counter[fc][cc] += 1
        child_to_parent = {fc: cc.most_common(1)[0][0] for fc, cc in fine_coarse_counter.items() if cc}
        
        improvements = []
        n_parents = 0
        
        for pc, cmems in coarse_members.items():
            if len(cmems) < MIN_CLUSTER_SIZE:
                continue
            cvals = coarse_vals.get(pc, [])
            if not cvals:
                continue
            
            child_clusters = [fc for fc, p in child_to_parent.items() if p == pc and len(fine_vals.get(fc, [])) >= MIN_CLUSTER_SIZE]
            if not child_clusters:
                continue
            
            child_purities = []
            for fc in child_clusters:
                fvals = fine_vals[fc]
                child_purities.append(Counter(fvals).most_common(1)[0][1] / len(fvals))
            
            coarse_purity = Counter(cvals).most_common(1)[0][1] / len(cvals)
            mean_child = float(np.mean(child_purities))
            improvements.append(mean_child - coarse_purity)
            n_parents += 1
        
        if improvements:
            mean_improvement = float(np.mean(improvements))
            improvement_rate = float(sum(1 for j in improvements if j > 0) / len(improvements))
        else:
            mean_improvement = None
            improvement_rate = None
        
        return {
            'mean_improvement': mean_improvement,
            'improvement_rate': improvement_rate,
            'n_parents': n_parents,
        }
    
    def evaluate_v26_flat_zoom(labels_by_res, metadata):
        transitions = []
        for i in range(len(V26_RESOLUTIONS) - 1):
            coarse_res = V26_RESOLUTIONS[i]
            fine_res = V26_RESOLUTIONS[i + 1]
            
            zoom_branch = compute_zoom_coherence_id_space(metadata, labels_by_res[coarse_res], labels_by_res[fine_res], 'branch')
            zoom_area = compute_zoom_coherence_id_space(metadata, labels_by_res[coarse_res], labels_by_res[fine_res], 'legal_area')
            
            transitions.append({
                'from_res': coarse_res,
                'to_res': fine_res,
                'branch_improvement_rate': zoom_branch['improvement_rate'],
                'branch_mean_improvement': zoom_branch['mean_improvement'],
                'area_improvement_rate': zoom_area['improvement_rate'],
                'area_mean_improvement': zoom_area['mean_improvement'],
                'n_parents': zoom_branch['n_parents'],
            })
        
        branch_mono = (compute_branch_purity(labels_by_res[V26_RESOLUTIONS[-1]], metadata) > compute_branch_purity(labels_by_res[V26_RESOLUTIONS[0]], metadata))
        area_mono = (compute_area_purity(labels_by_res[V26_RESOLUTIONS[-1]], metadata) > compute_area_purity(labels_by_res[V26_RESOLUTIONS[0]], metadata))
        rate_gt_half = sum(1 for t in transitions if t['branch_improvement_rate'] and t['branch_improvement_rate'] > 0.5)
        
        passes = branch_mono and area_mono and (rate_gt_half >= 2)
        
        return {
            'transitions': transitions,
            'branch_monotonic': branch_mono,
            'area_monotonic': area_mono,
            'branch_improvement_rate_gt_0.5_count': rate_gt_half,
            'passes_v26': passes,
        }
    
    flat_zoom_eval = evaluate_v26_flat_zoom(flat_labels, eval_metadata)
    logger.info(f'  Flat v26: PASS={flat_zoom_eval["passes_v26"]}, branch_mono={flat_zoom_eval["branch_monotonic"]}, area_mono={flat_zoom_eval["area_monotonic"]}, rate>0.5={flat_zoom_eval["branch_improvement_rate_gt_0.5_count"]}/4')
    
    # 8. Save results
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
    
    output = {
        "run_id": f"preparatory_20yr_checkpoint_dense_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction_version": 28,
        "evidence_tier": "EXPLORATORY_PREPARATORY",
        "note": "PREPARATORY VALIDATION on checkpoint data (years 2000-2019, ~137k). Years 2003-2019 PENDING AUDIT per factory direction v28. Results NOT for acceptance - pipeline verification only.",
        "hypothesis": "Constrained hierarchical Leiden (validated TF-IDF 174k config) works on dense embeddings at near-full scale (~137k)",
        "frozen_sample": f"{len(eval_metadata)} BGer decisions from checkpoint years 2000-2019",
        "frozen_metric": "Strict nesting, branch/area purity, zoom coherence (v26 semantics), fragmentation",
        "success_rule": "Strict nesting >= 0.99 AND branch/area purity improvement AND zoom improvement_rate > 0.5 AND fine_singleton_fraction < 0.1",
        "v26_flat_zoom_rule": "Branch monotonic AND area monotonic AND branch improvement_rate > 0.5 on >=2/4 transitions",
        "config_tested": {
            "coarse_res": 0.25,
            "base_sub_res": 3.0,
            "min_cluster_size": 10,
            "max_subclusters_per_parent": 20,
            "adaptive_sub_res": True,
        },
        "results": {
            "n_decisions": int(len(eval_metadata)),
            "coarse_clusters": int(n_coarse),
            "fine_clusters": int(n_fine),
            "coarse_branch_purity": coarse_branch_purity,
            "fine_branch_purity": fine_branch_purity,
            "branch_improvement": fine_branch_purity - coarse_branch_purity,
            "coarse_area_purity": coarse_area_purity,
            "fine_area_purity": fine_area_purity,
            "area_improvement": fine_area_purity - coarse_area_purity,
            "strict_nesting": nesting,
            "zoom_coherence": zoom_coherence,
            "fragmentation": {
                "coarse": frag_coarse,
                "hierarchical": frag_hierarchical,
            },
        },
        "flat_v26_comparison": flat_zoom_eval,
        "scale_comparison": {
            "tfidf_174k_full": "ACCEPTED: improvement_rate 57-90%, zero fragmentation, nesting=1.0",
            "dense_99k_2000_2015": "EXPLORATORY: coarse_res=0.15/0.2 PASS v26, 0.25/0.3 FAIL",
            "dense_12k_2000_2002": "EXPLORATORY: improvement_rate=45.5%, zero fragmentation, nesting=1.0",
            "this_run_20yr_2000_2019": "PREPARATORY: await results",
        }
    }
    
    output_path = OUTPUT_DIR / "preparatory_20yr_checkpoint_dense_results.json"
    with open(output_path, 'w') as f:
        json.dump(convert(output), f, indent=2)
    
    logger.info(f"\nResults saved to {output_path}")
    logger.info("\n=== Preparatory 20-year checkpoint validation complete ===")
    logger.info("REMINDER: Results are EXPLORATORY/PREPARATORY - NOT for acceptance.")


if __name__ == "__main__":
    main()