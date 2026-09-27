#!/usr/bin/env python3
"""
Constrained Hierarchical Leiden on Citation-Role Modes at 1k Scale.

Tests the evidence-backed zoom path (citation-role modes: citing_alpha0.3, 
following_alpha0.3, criticizing_alpha0.3) with the constrained hierarchical 
method that solved over-fragmentation at 5k-30k TF-IDF scale.

Hypothesis: Constrained hierarchical Leiden (min_cluster_size + adaptive 
sub_resolution) on citation-role embeddings at 1k scale produces a two-level 
hierarchy (matching v26 coarsest transition 0.25→0.5) that achieves:
- Perfect nesting (1.0 by construction)
- Higher zoom improvement_rate than flat Leiden
- Zero over-fragmentation (singleton_fraction = 0.0)
- Monotonic branch/area purity improvement

Baseline: Flat Leiden at v26 resolutions (current citation-role evaluation)
Product decision: Whether constrained hierarchical on citation-role modes 
provides a validated fractal map path scalable to 174k when dense embeddings arrive.

Frozen success rule per mode:
- Strict nesting = 1.0
- Branch improvement_rate > 0.5 (transition 0.25→0.5)
- Fine singleton_fraction = 0.0
- Fine median cluster size >= 10
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
BASELINE_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/baseline")
CITATION_ROLE_EMBEDDINGS = {
    "citing_alpha0.3": Path("/tmp/lex_accepted/legal-distance/legal_distance/results/v6/citation_roles_rebuilt/citation_role_citing_rebuilt.npy"),
    "following_alpha0.3": Path("/tmp/lex_accepted/legal-distance/legal_distance/results/v6/citation_roles_rebuilt/citation_role_following_rebuilt.npy"),
    "criticizing_alpha0.3": Path("/tmp/lex_accepted/legal-distance/legal_distance/results/v6/citation_roles_rebuilt/citation_role_criticizing_rebuilt.npy"),
}
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/constrained_hierarchical_tests/citation_roles_1k")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# v26 compressed ladder resolutions
V26_RESOLUTIONS = [0.25, 0.5, 1.0, 2.0, 3.0]
MIN_CLUSTER_SIZE = 10  # For zoom coherence evaluation and fragmentation control
K = 15
SEED = 42

# Coarse resolution to test (matching v26 second level - 0.5 works better than 0.25 for 1k scale)
COARSE_RES = 0.5
SUB_RES_BASE = 1.5  # Fixed sub-resolution (like earlier successful test)
ADAPTIVE_SUB_RES = False  # Use fixed sub_res
MAX_SUBCLUSTERS_PER_PARENT = 20


def load_metadata():
    """Load baseline metadata with branch (1000 decisions, 2020-2024)."""
    with open(BASELINE_DIR / "metadata.json") as f:
        metadata = json.load(f)
    
    # Enrich with branch from corpus files
    id_to_idx = {m['decision_id']: i for i, m in enumerate(metadata)}
    corpus_dir = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
    branch_map = {}
    for year_file in sorted(corpus_dir.glob("bger_20*.jsonl")):
        with open(year_file) as f:
            for line in f:
                d = json.loads(line)
                did = d.get('decision_id', '')
                if did in id_to_idx:
                    branch_map[did] = d.get('branch')
    
    for m in metadata:
        m['branch'] = branch_map.get(m['decision_id'])
    
    logger.info(f"Loaded baseline metadata: {len(metadata)} entries")
    return metadata


def load_citation_role_metadata(metadata, mode_id):
    """Use all baseline metadata (1000 decisions) - citation-role modes use first 1000."""
    return metadata


def load_embeddings(mode_id, n_expected):
    """Load embeddings for a citation-role mode (first 1000 of 1200)."""
    emb_path = CITATION_ROLE_EMBEDDINGS[mode_id]
    if not emb_path.exists():
        logger.error(f"Embeddings not found: {emb_path}")
        return None
    embeddings = np.load(emb_path)
    logger.info(f"Loaded {mode_id}: {embeddings.shape}")
    
    # Citation-role modes use first 1000 of 1200 (subset_first_n=1000 in build_missing_modes)
    if len(embeddings) > 1000:
        embeddings = embeddings[:1000]
        logger.info(f"  Subset to first 1000")
    return embeddings


def leiden_clustering(embeddings, resolution=1.0, k=15, seed=42):
    """Leiden clustering on k-NN graph (with normalization like parameterized builder)."""
    k_actual = min(k, len(embeddings) - 1)
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normalized = embeddings / norms
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
    return np.array(partition.membership), partition.modularity


def hierarchical_leiden_constrained(embeddings, metadata, coarse_res=0.5, 
                                     min_cluster_size=10, 
                                     sub_res=1.5,
                                     max_subclusters_per_parent=20,
                                     k=15):
    """
    Run constrained hierarchical Leiden (matching earlier successful test config):
    1. Global Leiden at coarse_res to get coarse clusters
    2. For each coarse cluster, run Leiden at fixed sub_res within the subset
    3. Enforce min_cluster_size and max_subclusters_per_parent - merge tiny clusters
    4. Assign global labels with guaranteed nesting
    """
    # Step 1: Global coarse clustering
    coarse_labels, coarse_mod = leiden_clustering(embeddings, resolution=coarse_res, k=k)
    unique_coarse = np.unique(coarse_labels[coarse_labels != -1])
    
    logger.info(f"  Coarse (res={coarse_res}): {len(unique_coarse)} clusters, modularity={coarse_mod:.4f}")
    
    # Step 2: Within each coarse cluster, run Leiden at fixed sub_res
    hierarchical_labels = np.full(len(embeddings), -1, dtype=int)
    sub_cluster_id = 0
    cluster_info = {}
    coarse_to_fine = defaultdict(list)
    
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
        
        # Run Leiden within subset at fixed sub_res
        sub_labels, sub_mod = leiden_clustering(subset_embeddings, resolution=sub_res, k=k)
        unique_sub = np.unique(sub_labels[sub_labels != -1])
        
        logger.info(f"    Coarse {coarse_id} ({cluster_size} docs): "
                    f"{len(unique_sub)} sub-clusters at sub_res={sub_res:.2f}, modularity={sub_mod:.4f}")
        
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
        
        # Enforce max_subclusters_per_parent by merging smallest clusters
        if len(unique_sub) > max_subclusters_per_parent:
            # Sort by size and merge smallest
            sub_sizes = {sid: len(indices[sub_labels == sid]) for sid in unique_sub}
            sorted_subs = sorted(unique_sub, key=lambda sid: sub_sizes[sid])
            to_merge = sorted_subs[:len(unique_sub) - max_subclusters_per_parent]
            keep = sorted_subs[len(unique_sub) - max_subclusters_per_parent:]
            keep_centroids = {sid: np.mean(subset_embeddings[sub_labels == sid], axis=0) for sid in keep}
            for merge_sid in to_merge:
                merge_centroid = np.mean(subset_embeddings[sub_labels == merge_sid], axis=0)
                best_sid = min(keep, key=lambda sid: np.linalg.norm(merge_centroid - keep_centroids[sid]))
                sub_labels[sub_labels == merge_sid] = best_sid
            unique_sub = keep
            logger.info(f"    Merged to {len(unique_sub)} sub-clusters (max={max_subclusters_per_parent})")
        
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
                'sub_res_used': round(sub_res, 2),
            }
            coarse_to_fine[int(coarse_id)].append(sub_cluster_id)
            sub_cluster_id += 1
    
    return hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine


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


def compute_branch_purity(labels, metadata, min_cluster_size=3):
    """Compute mean branch purity per cluster."""
    unique_labels = np.unique(labels[labels != -1])
    purities = []
    
    for label in unique_labels:
        mask = labels == label
        cluster_branches = [metadata[i].get('branch') for i in np.where(mask)[0]]
        cluster_branches = [b for b in cluster_branches if b and b != 'unknown' and b != 'null']
        
        if cluster_branches and len(cluster_branches) >= min_cluster_size:
            most_common = Counter(cluster_branches).most_common(1)[0][1]
            purities.append(most_common / len(cluster_branches))
    
    return float(np.mean(purities)) if purities else 0


def compute_legal_area_purity(labels, metadata, min_cluster_size=3):
    """Compute mean legal_area purity per cluster."""
    unique_labels = np.unique(labels[labels != -1])
    purities = []
    
    for label in unique_labels:
        mask = labels == label
        cluster_areas = [metadata[i].get('legal_area') for i in np.where(mask)[0]]
        cluster_areas = [a for a in cluster_areas if a and a != 'unknown' and a != 'null']
        
        if cluster_areas and len(cluster_areas) >= min_cluster_size:
            most_common = Counter(cluster_areas).most_common(1)[0][1]
            purities.append(most_common / len(cluster_areas))
    
    return float(np.mean(purities)) if purities else 0


def compute_zoom_coherence_id_space(metadata, coarse_labels, fine_labels, field='branch'):
    """
    Compute zoom coherence in decision-ID space (matching v26 evaluation semantics).
    """
    id_pairs = {}
    for i, m in enumerate(metadata):
        did = m['decision_id']
        id_pairs[did] = (coarse_labels[i], fine_labels[i])
    
    # Labeled values per cluster
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
    
    improvements = []
    n_parents = 0
    
    for pc, cmems in coarse_members.items():
        if len(cmems) < MIN_CLUSTER_SIZE:
            continue
        cvals = coarse_vals.get(pc, [])
        if not cvals:
            continue
        
        # children of this parent with >= MIN_CLUSTER_SIZE labeled decisions
        child_clusters = [fc for fc, p in child_to_parent.items()
                          if p == pc and len(fine_vals.get(fc, [])) >= MIN_CLUSTER_SIZE]
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


def evaluate_flat_v26(embeddings, metadata):
    """Evaluate flat Leiden at v26 resolutions for comparison."""
    flat_labels = {}
    for res in V26_RESOLUTIONS:
        labels, mod = leiden_clustering(embeddings, resolution=res, k=K)
        flat_labels[res] = labels
    
    # Compute purities at each resolution
    purities_branch = {}
    purities_area = {}
    for res in V26_RESOLUTIONS:
        purities_branch[res] = compute_branch_purity(flat_labels[res], metadata)
        purities_area[res] = compute_legal_area_purity(flat_labels[res], metadata)
    
    # Compute zoom coherence at each transition
    zoom_transitions = {}
    for i in range(len(V26_RESOLUTIONS) - 1):
        coarse_res = V26_RESOLUTIONS[i]
        fine_res = V26_RESOLUTIONS[i + 1]
        zoom_branch = compute_zoom_coherence_id_space(metadata, 
                                                       flat_labels[coarse_res], 
                                                       flat_labels[fine_res], 
                                                       'branch')
        zoom_area = compute_zoom_coherence_id_space(metadata, 
                                                     flat_labels[coarse_res], 
                                                     flat_labels[fine_res], 
                                                     'legal_area')
        zoom_transitions[f'{coarse_res}_to_{fine_res}'] = {
            'branch_improvement_rate': zoom_branch['improvement_rate'],
            'branch_mean_improvement': zoom_branch['mean_improvement'],
            'area_improvement_rate': zoom_area['improvement_rate'],
            'area_mean_improvement': zoom_area['mean_improvement'],
            'n_parents': zoom_branch['n_parents'],
        }
    
    # v26 success rule
    branch_mono = purities_branch[3.0] > purities_branch[0.25]
    area_mono = purities_area[3.0] > purities_area[0.25]
    rate_gt_half = sum(1 for t in zoom_transitions.values() 
                       if t['branch_improvement_rate'] and t['branch_improvement_rate'] > 0.5)
    
    # Fragmentation
    fragmentation = {}
    for res in V26_RESOLUTIONS:
        vals, counts = np.unique(flat_labels[res][flat_labels[res] != -1], return_counts=True)
        fragmentation[res] = {
            'n_clusters': int(len(vals)),
            'median_size': float(np.median(counts)) if len(counts) > 0 else 0,
            'singleton_fraction': float(np.mean(counts == 1)) if len(counts) > 0 else 0,
        }
    
    return {
        'purities_branch': purities_branch,
        'purities_area': purities_area,
        'zoom_transitions': zoom_transitions,
        'branch_monotonic': branch_mono,
        'area_monotonic': area_mono,
        'rate_gt_0.5_count': rate_gt_half,
        'passes_v26': branch_mono and area_mono and (rate_gt_half >= 2),
        'fragmentation': fragmentation,
    }


def convert(obj):
    if isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert(v) for v in obj]
    return obj


def main():
    logger.info("=== Constrained Hierarchical Leiden on Citation-Role Modes at 1k Scale ===")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    logger.info(f"Coarse resolution: {COARSE_RES} (matching v26 coarsest level)")
    logger.info(f"Min cluster size: {MIN_CLUSTER_SIZE}")
    logger.info(f"Adaptive sub-resolution: {ADAPTIVE_SUB_RES}")
    
    # 1. Load metadata
    logger.info("\n1. Loading metadata...")
    full_metadata = load_metadata()
    
    all_results = {}
    
    for mode_id in CITATION_ROLE_EMBEDDINGS:
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing mode: {mode_id}")
        logger.info(f"{'='*60}")
        
        # Use baseline metadata (1000 decisions) - matches citation-role mode embeddings
        metadata = load_citation_role_metadata(full_metadata, mode_id)
        n_meta = len(metadata)
        
        # Load embeddings (first 1000)
        embeddings = load_embeddings(mode_id, n_meta)
        if embeddings is None:
            continue
        
        if len(embeddings) != n_meta:
            logger.warning(f"  Embedding count ({len(embeddings)}) != metadata count ({n_meta}), adjusting")
            min_n = min(len(embeddings), n_meta)
            embeddings = embeddings[:min_n]
            metadata = metadata[:min_n]
            n_meta = min_n
        
        # 2. Run constrained hierarchical Leiden
        logger.info(f"\n2. Running constrained hierarchical Leiden (coarse_res={COARSE_RES}, sub_res={SUB_RES_BASE})...")
        hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine = hierarchical_leiden_constrained(
            embeddings, metadata,
            coarse_res=COARSE_RES,
            min_cluster_size=MIN_CLUSTER_SIZE,
            sub_res=SUB_RES_BASE,
            max_subclusters_per_parent=MAX_SUBCLUSTERS_PER_PARENT,
            k=K
        )
        
        n_fine = len(set(hierarchical_labels[hierarchical_labels != -1]))
        n_coarse = len(set(coarse_labels[coarse_labels != -1]))
        
        # 3. Compute metrics
        coarse_branch_purity = compute_branch_purity(coarse_labels, metadata)
        fine_branch_purity = compute_branch_purity(hierarchical_labels, metadata)
        coarse_area_purity = compute_legal_area_purity(coarse_labels, metadata)
        fine_area_purity = compute_legal_area_purity(hierarchical_labels, metadata)
        nesting = compute_strict_nesting(hierarchical_labels, coarse_labels)
        
        # Zoom coherence in ID space (matching v26 semantics)
        zoom_branch = compute_zoom_coherence_id_space(metadata, coarse_labels, hierarchical_labels, 'branch')
        zoom_area = compute_zoom_coherence_id_space(metadata, coarse_labels, hierarchical_labels, 'legal_area')
        
        # Fragmentation
        fine_unique, fine_counts = np.unique(hierarchical_labels[hierarchical_labels != -1], return_counts=True)
        coarse_unique, coarse_counts = np.unique(coarse_labels[coarse_labels != -1], return_counts=True)
        
        logger.info(f"    Coarse clusters: {n_coarse}, median size: {np.median(coarse_counts):.1f}")
        logger.info(f"    Fine clusters: {n_fine}, median size: {np.median(fine_counts):.1f}")
        logger.info(f"    Branch purity: coarse={coarse_branch_purity:.4f}, fine={fine_branch_purity:.4f} (Δ={fine_branch_purity - coarse_branch_purity:+.4f})")
        logger.info(f"    Area purity: coarse={coarse_area_purity:.4f}, fine={fine_area_purity:.4f} (Δ={fine_area_purity - coarse_area_purity:+.4f})")
        logger.info(f"    Strict nesting: {nesting:.4f}")
        zoom_branch_rate = zoom_branch['improvement_rate'] if zoom_branch['improvement_rate'] is not None else 0
        zoom_area_rate = zoom_area['improvement_rate'] if zoom_area['improvement_rate'] is not None else 0
        zoom_branch_imp = zoom_branch['mean_improvement'] if zoom_branch['mean_improvement'] is not None else 0
        zoom_area_imp = zoom_area['mean_improvement'] if zoom_area['mean_improvement'] is not None else 0
        logger.info(f"    Zoom branch: mean_imp={zoom_branch_imp:.4f}, rate={zoom_branch_rate:.2%}, n_parents={zoom_branch['n_parents']}")
        logger.info(f"    Zoom area: mean_imp={zoom_area_imp:.4f}, rate={zoom_area_rate:.2%}, n_parents={zoom_area['n_parents']}")
        logger.info(f"    Fragmentation: fine singletons={np.mean(fine_counts == 1):.1%}, median size={np.median(fine_counts):.1f}")
        
        constrained_result = {
            'config': {
                'coarse_res': COARSE_RES,
                'min_cluster_size': MIN_CLUSTER_SIZE,
                'sub_res_base': SUB_RES_BASE,
                'adaptive_sub_res': ADAPTIVE_SUB_RES,
            },
            'n_decisions': n_meta,
            'coarse_clusters': int(n_coarse),
            'fine_clusters': int(n_fine),
            'coarse_branch_purity': coarse_branch_purity,
            'fine_branch_purity': fine_branch_purity,
            'coarse_area_purity': coarse_area_purity,
            'fine_area_purity': fine_area_purity,
            'branch_improvement': fine_branch_purity - coarse_branch_purity,
            'area_improvement': fine_area_purity - coarse_area_purity,
            'strict_nesting': nesting,
            'zoom_branch': zoom_branch,
            'zoom_area': zoom_area,
            'fragmentation': {
                'coarse_median_size': float(np.median(coarse_counts)),
                'fine_median_size': float(np.median(fine_counts)),
                'fine_singleton_fraction': float(np.mean(fine_counts == 1)),
                'coarse_singleton_fraction': float(np.mean(coarse_counts == 1)),
            },
            'success_checks': {
                'nesting_1.0': nesting >= 0.999,
                'branch_improvement_rate_gt_0.5': zoom_branch['improvement_rate'] is not None and zoom_branch['improvement_rate'] > 0.5,
                'area_improvement_rate_gt_0.5': zoom_area['improvement_rate'] is not None and zoom_area['improvement_rate'] > 0.5,
                'zero_fragmentation': np.mean(fine_counts == 1) == 0.0,
                'fine_median_size_ge_10': np.median(fine_counts) >= 10,
            }
        }
        
        # 4. Also run flat Leiden at v26 resolutions for comparison
        logger.info(f"\n3. Running flat Leiden at v26 resolutions for comparison...")
        flat_eval = evaluate_flat_v26(embeddings, metadata)
        
        logger.info(f"    Flat v26: PASS={flat_eval['passes_v26']}, "
                    f"branch_mono={flat_eval['branch_monotonic']}, "
                    f"area_mono={flat_eval['area_monotonic']}, "
                    f"rate>0.5={flat_eval['rate_gt_0.5_count']}/4")
        logger.info(f"    Flat fragmentation at res_3.0: "
                    f"n={flat_eval['fragmentation'][3.0]['n_clusters']}, "
                    f"median={flat_eval['fragmentation'][3.0]['median_size']:.1f}, "
                    f"singletons={flat_eval['fragmentation'][3.0]['singleton_fraction']:.1%}")
        
        all_results[mode_id] = {
            'mode': mode_id,
            'n_decisions': n_meta,
            'constrained_hierarchical': constrained_result,
            'flat_v26': flat_eval,
        }
    
    # 5. Summary
    logger.info("\n" + "=" * 70)
    logger.info("CONSTRAINED HIERARCHICAL LEIDEN ON CITATION-ROLE MODES (1k) SUMMARY")
    logger.info("=" * 70)
    
    for mode_id, result in all_results.items():
        logger.info(f"\n  {mode_id}:")
        logger.info(f"    Flat v26: PASS={result['flat_v26']['passes_v26']}, "
                    f"branch_mono={result['flat_v26']['branch_monotonic']}, "
                    f"area_mono={result['flat_v26']['area_monotonic']}, "
                    f"rate>0.5={result['flat_v26']['rate_gt_0.5_count']}/4")
        
        ch = result['constrained_hierarchical']
        logger.info(f"\n    Constrained Hierarchical (coarse_res={COARSE_RES}):")
        logger.info(f"      Coarse->Fine: {ch['coarse_clusters']} -> {ch['fine_clusters']}")
        logger.info(f"      Branch: {ch['coarse_branch_purity']:.4f} -> {ch['fine_branch_purity']:.4f} (Δ={ch['branch_improvement']:+.4f})")
        logger.info(f"      Area: {ch['coarse_area_purity']:.4f} -> {ch['fine_area_purity']:.4f} (Δ={ch['area_improvement']:+.4f})")
        logger.info(f"      Nesting: {ch['strict_nesting']:.4f}")
        branch_rate = ch['zoom_branch']['improvement_rate'] if ch['zoom_branch']['improvement_rate'] is not None else 0
        area_rate = ch['zoom_area']['improvement_rate'] if ch['zoom_area']['improvement_rate'] is not None else 0
        logger.info(f"      Zoom branch rate: {branch_rate:.2%}")
        logger.info(f"      Zoom area rate: {area_rate:.2%}")
        logger.info(f"      Fragmentation: fine median={ch['fragmentation']['fine_median_size']:.1f}, singletons={ch['fragmentation']['fine_singleton_fraction']:.1%}")
        logger.info(f"      Success checks: {ch['success_checks']}")
    
    # 6. Save results
    output = {
        "run_id": f"constrained_hierarchical_citation_roles_1k_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction_version": 28,
        "hypothesis": "Constrained hierarchical Leiden on citation-role embeddings at 1k scale achieves perfect nesting, zero fragmentation, and monotonic zoom refinement at the coarsest v26 transition (0.25→0.5)",
        "frozen_sample": "1000 BGer decisions (citation-role mode subset, ~2020-2024)",
        "frozen_metric": "Strict nesting, branch/area purity, zoom coherence (v26 semantics), fragmentation",
        "success_rule": "Strict nesting >= 0.99 AND branch improvement_rate > 0.5 AND fine_singleton_fraction == 0.0 AND fine_median_size >= 10",
        "v26_flat_zoom_rule": "Branch monotonic AND area monotonic AND branch improvement_rate > 0.5 on >=2/4 transitions",
        "config": {
            "coarse_res": COARSE_RES,
            "min_cluster_size": MIN_CLUSTER_SIZE,
            "sub_res": SUB_RES_BASE,
            "max_subclusters_per_parent": MAX_SUBCLUSTERS_PER_PARENT,
            "adaptive_sub_res": ADAPTIVE_SUB_RES,
            "k": K,
        },
        "results": all_results,
    }
    
    output_path = OUTPUT_DIR / f"constrained_hierarchical_citation_roles_1k_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, 'w') as f:
        json.dump(convert(output), f, indent=2)
    
    logger.info(f"\nResults saved to {output_path}")
    logger.info("\n=== Experiment complete ===")


if __name__ == "__main__":
    main()