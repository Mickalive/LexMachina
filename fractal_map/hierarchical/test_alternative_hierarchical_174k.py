#!/usr/bin/env python3
"""
Test alternative hierarchical clustering methods on 174k TF-IDF embeddings.
Goal: Find methods that handle extreme cluster size skew better than Leiden.

Methods tested:
1. HDBSCAN (density-based, handles variable density)
2. Recursive balanced Leiden (size-constrained partitioning)
3. Local UMAP + Leiden (zoom-conditioned neighborhoods)
4. Agglomerative clustering with connectivity constraints

Evaluated against frozen v26 success rule:
- PASS iff: (a) branch purity res_3.0 > res_0.25 AND (b) area purity res_3.0 > res_0.25 AND (c) branch improvement_rate > 0.5 on ≥2 of 4 transitions.
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict
import logging
from datetime import datetime, timezone
import sys
import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

EMBEDDINGS_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings")
METADATA_PATH = Path("/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/alternative_hierarchical_174k")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODES = [
    "cited_decisions_tfidf_outcome_hybrid_0.5",
    "cited_decisions_tfidf_outcome_hybrid_0.7",
    "regeste_tfidf",
    "cited_decisions_tfidf",
    "full_text_tfidf_light",
    "outcome_tfidf",
    "regeste_full_text_hybrid_0.5",
    "regeste_full_text_hybrid_0.7",
]

RESOLUTIONS = [0.25, 0.5, 1.0, 2.0, 3.0]

# Frozen v26 baseline (from accepted evaluation)
BASELINE_BRANCH_RANDOM = 0.25
BASELINE_AREA_RANDOM = 1 / 213  # ~0.004695


def load_metadata():
    with open(METADATA_PATH) as f:
        metadata = json.load(f)
    logger.info(f"Loaded metadata: {len(metadata)} decisions")
    return metadata


def load_embeddings(mode):
    emb_path = EMBEDDINGS_DIR / f"{mode}.npy"
    embeddings = np.load(emb_path)
    logger.info(f"  Loaded {mode}: {embeddings.shape}")
    return embeddings


def compute_branch_purity(labels, metadata):
    unique_labels = np.unique(labels[labels != -1])
    purities = []
    for label in unique_labels:
        mask = labels == label
        cluster_branches = [metadata[i].get('branch') for i in np.where(mask)[0]]
        cluster_branches = [b for b in cluster_branches if b and b not in ('unknown', 'null')]
        if cluster_branches:
            most_common = Counter(cluster_branches).most_common(1)[0][1]
            purities.append(most_common / len(cluster_branches))
    return float(np.mean(purities)) if purities else 0


def compute_legal_area_purity(labels, metadata):
    unique_labels = np.unique(labels[labels != -1])
    purities = []
    for label in unique_labels:
        mask = labels == label
        cluster_areas = [metadata[i].get('legal_area') for i in np.where(mask)[0]]
        cluster_areas = [a for a in cluster_areas if a and a not in ('unknown', 'null')]
        if cluster_areas:
            most_common = Counter(cluster_areas).most_common(1)[0][1]
            purities.append(most_common / len(cluster_areas))
    return float(np.mean(purities)) if purities else 0


def compute_zoom_coherence_id_space(metadata, coarse_labels, fine_labels, field='branch'):
    id_pairs = {}
    for i, m in enumerate(metadata):
        did = m['decision_id']
        id_pairs[did] = (coarse_labels[i], fine_labels[i])

    coarse_vals = {}
    fine_vals = {}
    for i, m in enumerate(metadata):
        did = m['decision_id']
        val = m.get(field)
        if not val or val in ('unknown', 'null'):
            continue
        cc, fc = id_pairs[did]
        coarse_vals.setdefault(cc, []).append(val)
        fine_vals.setdefault(fc, []).append(val)

    coarse_members = {}
    fine_members = {}
    for did, (cc, fc) in id_pairs.items():
        coarse_members.setdefault(cc, []).append(did)
        fine_members.setdefault(fc, []).append(did)

    fine_coarse_counter = {}
    for did, (cc, fc) in id_pairs.items():
        fine_coarse_counter.setdefault(fc, Counter())[cc] += 1
    child_to_parent = {fc: cc.most_common(1)[0][0] for fc, cc in fine_coarse_counter.items() if cc}

    improvements = []
    n_parents = 0
    MIN_CLUSTER_SIZE = 3

    for pc, cmems in coarse_members.items():
        if len(cmems) < MIN_CLUSTER_SIZE:
            continue
        cvals = coarse_vals.get(pc, [])
        if not cvals:
            continue
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
        return {
            'mean_improvement': float(np.mean(improvements)),
            'improvement_rate': float(sum(1 for j in improvements if j > 0) / len(improvements)),
            'n_parents': n_parents,
        }
    return {'mean_improvement': None, 'improvement_rate': None, 'n_parents': 0}


def leiden_clustering(embeddings, resolution=1.0, k=15):
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


def balanced_leiden_partition(embeddings, target_n_clusters, k=15, max_iter=10):
    """
    Recursively partition using Leiden with resolution search to get approximately
    target_n_clusters, avoiding extreme size skew.
    """
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

    # Binary search for resolution that gives ~target_n_clusters
    low, high = 0.01, 10.0
    best_labels = None
    best_n = 0

    for _ in range(max_iter):
        mid = (low + high) / 2
        partition = leidenalg.find_partition(
            g, leidenalg.RBConfigurationVertexPartition,
            weights='weight', resolution_parameter=mid, seed=42
        )
        labels = np.array(partition.membership)
        n_clusters = len(set(labels[labels != -1]))

        if n_clusters == target_n_clusters:
            return labels, partition.modularity
        elif n_clusters < target_n_clusters:
            low = mid
        else:
            high = mid

        if abs(n_clusters - target_n_clusters) < abs(best_n - target_n_clusters):
            best_labels = labels
            best_n = n_clusters

    return best_labels, 0.0


def recursive_balanced_leiden(embeddings, level_sizes, k=15):
    """
    Recursively partition: at each level, split clusters to achieve target sizes.
    level_sizes: list of target cluster counts per level, e.g., [5, 10, 20, 40, 80]
    """
    n = len(embeddings)
    current_labels = np.zeros(n, dtype=int)  # All in one cluster initially
    level_labels = {}

    for level, target_n in enumerate(level_sizes):
        if level == 0:
            # First level: partition whole space
            labels, _ = balanced_leiden_partition(embeddings, target_n, k)
            level_labels[level] = labels
            current_labels = labels
        else:
            # Subdivide each cluster from previous level
            new_labels = np.full(n, -1, dtype=int)
            label_offset = 0
            unique_prev = np.unique(current_labels[current_labels != -1])

            for prev_label in unique_prev:
                mask = current_labels == prev_label
                indices = np.where(mask)[0]

                if len(indices) < 10:
                    # Too small, keep as is
                    new_labels[indices] = label_offset
                    label_offset += 1
                    continue

                # Target: subdivide this cluster proportionally
                cluster_target = max(1, int(target_n * len(indices) / n))
                subset_emb = embeddings[indices]

                sub_labels, _ = balanced_leiden_partition(subset_emb, cluster_target, k)

                # Remap to global labels
                for sub_label in np.unique(sub_labels[sub_labels != -1]):
                    sub_mask = sub_labels == sub_label
                    global_idx = indices[sub_mask]
                    new_labels[global_idx] = label_offset
                    label_offset += 1

            level_labels[level] = new_labels
            current_labels = new_labels

    return level_labels


def test_hdbscan(embeddings, metadata, mode_name):
    """Test HDBSCAN clustering at multiple min_cluster_size settings."""
    try:
        import hdbscan
    except ImportError:
        logger.warning("HDBSCAN not available, skipping")
        return {}

    logger.info(f"  Testing HDBSCAN on {mode_name}...")
    results = {}

    # Test multiple min_cluster_size values to get different granularities
    # Target similar cluster counts as Leiden resolutions
    min_cluster_sizes = [5000, 2000, 1000, 500, 200, 100, 50]

    for mcs in min_cluster_sizes:
        try:
            clusterer = hdbscan.HDBSCAN(
                min_cluster_size=mcs,
                min_samples=max(5, mcs // 10),
                metric='euclidean',
                cluster_selection_method='eom',
                core_dist_n_jobs=1
            )
            labels = clusterer.fit_predict(embeddings)

            n_clusters = len(set(labels[labels != -1]))
            noise_frac = np.mean(labels == -1)

            if n_clusters < 2:
                continue

            branch_purity = compute_branch_purity(labels, metadata)
            area_purity = compute_legal_area_purity(labels, metadata)

            results[f"mcs_{mcs}"] = {
                'method': 'HDBSCAN',
                'min_cluster_size': mcs,
                'n_clusters': int(n_clusters),
                'noise_fraction': float(noise_frac),
                'branch_purity': branch_purity,
                'area_purity': area_purity,
            }
            logger.info(f"    MCS={mcs}: {n_clusters} clusters, noise={noise_frac:.2%}, branch={branch_purity:.4f}, area={area_purity:.4f}")

        except Exception as e:
            logger.warning(f"    HDBSCAN MCS={mcs} failed: {e}")

    return results


def test_umap_leiden(embeddings, metadata, mode_name):
    """Test UMAP dimensionality reduction followed by Leiden at multiple resolutions."""
    try:
        import umap
    except ImportError:
        logger.warning("UMAP not available, skipping")
        return {}

    logger.info(f"  Testing UMAP+Leiden on {mode_name}...")

    # Reduce to 2D, 10D, 50D for local neighborhood preservation
    results = {}
    for n_components in [2, 10, 50]:
        if n_components >= embeddings.shape[1]:
            continue

        try:
            reducer = umap.UMAP(
                n_components=n_components,
                n_neighbors=15,
                min_dist=0.1,
                metric='cosine',
                random_state=42,
                n_jobs=1
            )
            reduced = reducer.fit_transform(embeddings)

            # Run Leiden at multiple resolutions on reduced space
            for res in RESOLUTIONS:
                labels, _ = leiden_clustering(reduced, resolution=res, k=15)
                n_clusters = len(set(labels[labels != -1]))

                if n_clusters < 2:
                    continue

                branch_purity = compute_branch_purity(labels, metadata)
                area_purity = compute_legal_area_purity(labels, metadata)

                key = f"umap{n_components}_res_{res}"
                results[key] = {
                    'method': f'UMAP_{n_components}D_Leiden',
                    'umap_dims': n_components,
                    'resolution': res,
                    'n_clusters': int(n_clusters),
                    'branch_purity': branch_purity,
                    'area_purity': area_purity,
                }
                logger.info(f"    UMAP{n_components} res={res}: {n_clusters} clusters, branch={branch_purity:.4f}, area={area_purity:.4f}")

        except Exception as e:
            logger.warning(f"    UMAP{n_components} failed: {e}")

    return results


def test_agglomerative(embeddings, metadata, mode_name):
    """Test Agglomerative clustering with connectivity constraints."""
    from sklearn.cluster import AgglomerativeClustering
    from sklearn.neighbors import kneighbors_graph

    logger.info(f"  Testing Agglomerative on {mode_name}...")

    # Build connectivity graph
    graph = kneighbors_graph(embeddings, n_neighbors=15, metric='cosine',
                             mode='connectivity', include_self=False)
    graph = graph.maximum(graph.T)

    results = {}
    # Target cluster counts similar to Leiden resolutions
    target_clusters = [5, 10, 20, 40, 80, 160, 320, 640]

    for n_clusters in target_clusters:
        if n_clusters >= len(embeddings):
            continue
        try:
            clustering = AgglomerativeClustering(
                n_clusters=n_clusters,
                metric='cosine',
                linkage='average',
                connectivity=graph
            )
            labels = clustering.fit_predict(embeddings)

            actual_n = len(set(labels[labels != -1]))
            branch_purity = compute_branch_purity(labels, metadata)
            area_purity = compute_legal_area_purity(labels, metadata)

            results[f"n_{n_clusters}"] = {
                'method': 'Agglomerative',
                'target_n_clusters': n_clusters,
                'actual_n_clusters': int(actual_n),
                'branch_purity': branch_purity,
                'area_purity': area_purity,
            }
            logger.info(f"    n={n_clusters}: {actual_n} clusters, branch={branch_purity:.4f}, area={area_purity:.4f}")

        except Exception as e:
            logger.warning(f"    Agglomerative n={n_clusters} failed: {e}")

    return results


def test_recursive_balanced_leiden(embeddings, metadata, mode_name):
    """Test recursive balanced Leiden partitioning."""
    logger.info(f"  Testing Recursive Balanced Leiden on {mode_name}...")

    # Target sizes matching resolution ladder: ~5, 10, 20, 40, 80 clusters
    level_sizes = [5, 10, 20, 40, 80]

    level_labels = recursive_balanced_leiden(embeddings, level_sizes, k=15)

    results = {}
    for level, labels in level_labels.items():
        n_clusters = len(set(labels[labels != -1]))
        branch_purity = compute_branch_purity(labels, metadata)
        area_purity = compute_legal_area_purity(labels, metadata)

        # Compute cluster size stats
        unique, counts = np.unique(labels[labels != -1], return_counts=True)
        median_size = float(np.median(counts)) if len(counts) > 0 else 0
        max_size = int(np.max(counts)) if len(counts) > 0 else 0
        min_size = int(np.min(counts)) if len(counts) > 0 else 0

        results[f"level_{level}"] = {
            'method': 'Recursive_Balanced_Leiden',
            'level': level,
            'target_n': level_sizes[level],
            'actual_n_clusters': int(n_clusters),
            'branch_purity': branch_purity,
            'area_purity': area_purity,
            'median_cluster_size': median_size,
            'max_cluster_size': max_size,
            'min_cluster_size': min_size,
        }
        logger.info(f"    Level {level} (target={level_sizes[level]}): {n_clusters} clusters, median_size={median_size:.1f}, max={max_size}, branch={branch_purity:.4f}, area={area_purity:.4f}")

    # Compute zoom coherence between consecutive levels
    zoom_results = {}
    level_keys = sorted(level_labels.keys())
    for i in range(len(level_keys) - 1):
        coarse = level_labels[level_keys[i]]
        fine = level_labels[level_keys[i + 1]]
        zoom_branch = compute_zoom_coherence_id_space(metadata, coarse, fine, 'branch')
        zoom_area = compute_zoom_coherence_id_space(metadata, coarse, fine, 'legal_area')
        zoom_results[f"level_{level_keys[i]}_to_{level_keys[i+1]}"] = {
            'branch': zoom_branch,
            'area': zoom_area,
        }
        logger.info(f"    Zoom {level_keys[i]}->{level_keys[i+1]}: branch_imp={zoom_branch['mean_improvement']:.4f}, rate={zoom_branch['improvement_rate']:.2%}")

    return {'levels': results, 'zoom': zoom_results}


def run_v26_style_evaluation(level_labels_dict, metadata):
    """
    Run v26-style evaluation on a method that produces labels at multiple levels.
    level_labels_dict: {level_name: labels_array} where level_name maps to resolution
    """
    # Map our levels to v26 resolutions (0.25, 0.5, 1.0, 2.0, 3.0)
    # We'll evaluate at the finest 5 levels available
    sorted_levels = sorted(level_labels_dict.keys())
    if len(sorted_levels) < 5:
        return None

    # Take 5 levels
    eval_levels = sorted_levels[:5]
    labels_at_levels = {res: level_labels_dict[level] for res, level in zip(RESOLUTIONS, eval_levels)}

    # Compute purities at each resolution
    branch_purities = {}
    area_purities = {}
    for res in RESOLUTIONS:
        labels = labels_at_levels[res]
        branch_purities[f"res_{res}"] = compute_branch_purity(labels, metadata)
        area_purities[f"res_{res}"] = compute_legal_area_purity(labels, metadata)

    # Zoom coherence between consecutive resolutions
    zoom_results = {}
    for i in range(len(RESOLUTIONS) - 1):
        coarse_res = RESOLUTIONS[i]
        fine_res = RESOLUTIONS[i + 1]
        zoom_branch = compute_zoom_coherence_id_space(
            metadata, labels_at_levels[coarse_res], labels_at_levels[fine_res], 'branch')
        zoom_area = compute_zoom_coherence_id_space(
            metadata, labels_at_levels[coarse_res], labels_at_levels[fine_res], 'legal_area')
        zoom_results[f"{coarse_res}_to_{fine_res}"] = {'branch': zoom_branch, 'area': zoom_area}

    # v26 success rule checks
    branch_mono = branch_purities["res_3.0"] > branch_purities["res_0.25"]
    area_mono = area_purities["res_3.0"] > area_purities["res_0.25"]

    # Improvement rate > 0.5 on >=2 of 4 transitions
    improvement_rates = [zoom_results[f"{RESOLUTIONS[i]}_to_{RESOLUTIONS[i+1]}"]['branch']['improvement_rate'] or 0
                         for i in range(4)]
    n_improving = sum(1 for r in improvement_rates if r > 0.5)
    rate_ok = n_improving >= 2

    passes = branch_mono and area_mono and rate_ok

    return {
        'branch_purity': branch_purities,
        'area_purity': area_purities,
        'zoom_coherence': zoom_results,
        'checks': {
            'branch_monotonic_res3_vs_res0.25': branch_mono,
            'area_monotonic_res3_vs_res0.25': area_mono,
            'improvement_rate_gt_0.5_on_2_of_4': rate_ok,
            'improvement_rates': improvement_rates,
        },
        'per_mode_verdict': 'PASS' if passes else 'FAIL'
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
    logger.info("=== Alternative Hierarchical Methods on 174k TF-IDF Embeddings ===")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")

    metadata = load_metadata()
    n_meta = len(metadata)

    all_results = {}

    for mode in MODES:
        logger.info(f"\n{'='*60}")
        logger.info(f"MODE: {mode}")
        logger.info(f"{'='*60}")

        embeddings = load_embeddings(mode)
        if len(embeddings) > n_meta:
            embeddings = embeddings[:n_meta]

        mode_results = {'mode': mode, 'embeddings_shape': list(embeddings.shape)}

        # 1. HDBSCAN
        logger.info("\n--- HDBSCAN ---")
        hdbscan_results = test_hdbscan(embeddings, metadata, mode)
        mode_results['hdbscan'] = hdbscan_results

        # 2. UMAP + Leiden
        logger.info("\n--- UMAP + Leiden ---")
        umap_results = test_umap_leiden(embeddings, metadata, mode)
        mode_results['umap_leiden'] = umap_results

        # 3. Agglomerative
        logger.info("\n--- Agglomerative ---")
        agg_results = test_agglomerative(embeddings, metadata, mode)
        mode_results['agglomerative'] = agg_results

        # 4. Recursive Balanced Leiden
        logger.info("\n--- Recursive Balanced Leiden ---")
        rbl_results = test_recursive_balanced_leiden(embeddings, metadata, mode)
        mode_results['recursive_balanced_leiden'] = rbl_results

        # 5. Run v26-style evaluation on Recursive Balanced Leiden (has proper hierarchy)
        if 'levels' in rbl_results:
            level_labels = {f"level_{k}": v for k, v in rbl_results['levels'].items()}
            # We need to extract labels from the level_labels - but rbl_results only has metrics
            # Re-run to get actual labels for evaluation
            rbl_labels = recursive_balanced_leiden(embeddings, [5, 10, 20, 40, 80])
            v26_eval = run_v26_style_evaluation(rbl_labels, metadata)
            mode_results['v26_evaluation'] = v26_eval
            if v26_eval:
                logger.info(f"    v26 verdict: {v26_eval['per_mode_verdict']}")
                logger.info(f"    Branch mono: {v26_eval['checks']['branch_monotonic_res3_vs_res0.25']}")
                logger.info(f"    Area mono: {v26_eval['checks']['area_monotonic_res3_vs_res0.25']}")
                logger.info(f"    Rate OK: {v26_eval['checks']['improvement_rate_gt_0.5_on_2_of_4']}")
                logger.info(f"    Imp rates: {v26_eval['checks']['improvement_rates']}")

        all_results[mode] = mode_results

    # Save
    output = {
        "run_id": f"alternative_hierarchical_174k_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction_version": 27,
        "hypothesis": "Alternative hierarchical methods (HDBSCAN, UMAP+Leiden, Agglomerative, Recursive Balanced Leiden) may handle extreme cluster size skew in TF-IDF 174k embeddings better than flat Leiden, enabling monotonic zoom refinement.",
        "frozen_sample": f"{n_meta} BGer decisions (metadata_174k.json)",
        "frozen_metric": "v26 success rule: branch monotonic, area monotonic, improvement_rate > 0.5 on >=2/4 transitions",
        "success_rule": "PASS iff (a) branch purity res_3.0 > res_0.25 AND (b) area purity res_3.0 > res_0.25 AND (c) branch improvement_rate > 0.5 on >=2 of 4 transitions",
        "baseline": {
            "branch_random": BASELINE_BRANCH_RANDOM,
            "area_random": BASELINE_AREA_RANDOM,
        },
        "modes_tested": MODES,
        "results": all_results,
    }

    output_path = OUTPUT_DIR / "alternative_hierarchical_174k_results.json"
    with open(output_path, 'w') as f:
        json.dump(convert(output), f, indent=2)

    logger.info(f"\n{'='*60}")
    logger.info(f"Results saved to {output_path}")
    logger.info("=== Alternative Hierarchical Methods Test Complete ===")


if __name__ == "__main__":
    main()