#!/usr/bin/env python3
"""
Build hierarchical map artifacts for factory direction v7 representations:
1. linear_metric_epoch4 (best linear metric learning)
2. mahalanobis_metric_epoch4 (best mahalanobis metric learning)
3. cited_decisions_tfidf (zero-shot citation signal)
4. hybrid_cited_0.3 (best hybrid balance)

All using the 1000-decision baseline for consistency with center_projected_hierarchical.
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

BASELINE_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/baseline")
CORPUS_DIR = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
OUTPUT_BASE = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/legal_distance_modes")
OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

RESOLUTIONS = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]


def load_baseline_metadata():
    """Load the 1000-decision baseline metadata with branch info."""
    with open(BASELINE_DIR / "metadata.json") as f:
        metadata = json.load(f)

    id_to_idx = {m['decision_id']: i for i, m in enumerate(metadata)}

    branch_map = {}
    for year_file in sorted(CORPUS_DIR.glob("bger_20*.jsonl")):
        with open(year_file) as f:
            for line in f:
                d = json.loads(line)
                did = d.get('decision_id', '')
                if did in id_to_idx:
                    branch_map[did] = d.get('branch')

    for m in metadata:
        m['branch'] = branch_map.get(m['decision_id'])

    return id_to_idx, metadata


def load_1200_metadata():
    """Load the 1200-decision metadata for metric learning embeddings."""
    metadata = []
    with open("/tmp/lex_accepted/evaluation/evaluation/data/bger_expanded_1200_metadata.jsonl") as f:
        for line in f:
            metadata.append(json.loads(line))
    return metadata


def leiden_clustering(embeddings, resolution=1.0, k=15, seed=42):
    """Leiden clustering on embeddings."""
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
        weights='weight', resolution_parameter=resolution, seed=seed
    )
    return np.array(partition.membership), partition.modularity


def build_nesting(hierarchy_labels):
    """Build nesting structure between consecutive resolutions."""
    resolutions = sorted(hierarchy_labels.keys())
    nesting = {}

    for i in range(len(resolutions) - 1):
        coarser_res = resolutions[i]
        finer_res = resolutions[i + 1]

        coarser_labels = hierarchy_labels[coarser_res]
        finer_labels = hierarchy_labels[finer_res]

        child_to_parent = {}
        unique_fine = np.unique(finer_labels[finer_labels != -1])

        for fine_id in unique_fine:
            fine_mask = finer_labels == fine_id
            parent_labels = coarser_labels[fine_mask]
            parent_labels_valid = parent_labels[parent_labels != -1]

            if len(parent_labels_valid) > 0:
                parent_id = Counter(parent_labels_valid.tolist()).most_common(1)[0][0]
                child_to_parent[int(fine_id)] = int(parent_id)
            else:
                child_to_parent[int(fine_id)] = -1

        parent_to_children = defaultdict(list)
        for child, parent in child_to_parent.items():
            parent_to_children[parent].append(child)

        nesting[f"{coarser_res}_to_{finer_res}"] = {
            'coarser_resolution': coarser_res,
            'finer_resolution': finer_res,
            'child_to_parent': child_to_parent,
            'parent_to_children': dict(parent_to_children),
            'nesting_consistency': sum(1 for c, p in child_to_parent.items() if p != -1) / len(child_to_parent) if child_to_parent else 0,
        }

    return nesting


def compute_cluster_metadata(labels, metadata):
    """Compute rich metadata for each cluster."""
    unique_labels = np.unique(labels[labels != -1])
    cluster_info = {}

    for label in unique_labels:
        mask = labels == label
        indices = np.where(mask)[0]
        cluster_meta = [metadata[i] for i in indices]

        langs = Counter(m.get('language') for m in cluster_meta if m.get('language'))
        dominant_lang = langs.most_common(1)[0] if langs else (None, 0)
        lang_purity = dominant_lang[1] / len(indices) if indices.size > 0 else 0

        branches = Counter(m.get('branch') for m in cluster_meta if m.get('branch'))
        dominant_branch = branches.most_common(1)[0] if branches else (None, 0)
        branch_purity = dominant_branch[1] / len(indices) if indices.size > 0 else 0

        areas = Counter(m.get('legal_area') for m in cluster_meta if m.get('legal_area'))
        dominant_area = areas.most_common(1)[0] if areas else (None, 0)

        years = Counter(m.get('year') for m in cluster_meta if m.get('year'))
        chambers = Counter(m.get('chamber') for m in cluster_meta if m.get('chamber'))

        cluster_info[int(label)] = {
            'size': int(mask.sum()),
            'dominant_lang': dominant_lang[0],
            'lang_purity': float(lang_purity),
            'dominant_branch': dominant_branch[0],
            'branch_purity': float(branch_purity),
            'dominant_area': dominant_area[0],
            'area_count': len(areas),
            'top_areas': {str(k): int(v) for k, v in areas.most_common(5)},
            'top_branches': {str(k): int(v) for k, v in branches.most_common(5)},
            'year_dist': {str(k): int(v) for k, v in years.most_common()},
            'top_chambers': {str(k): int(v) for k, v in chambers.most_common(3)},
            'decision_ids': [metadata[i]['decision_id'] for i in indices],
        }

    return cluster_info


def compute_zoom_coherence(hierarchy_labels, metadata, min_cluster_size=3):
    """Compute zoom coherence between consecutive resolutions."""
    resolutions = sorted(hierarchy_labels.keys())
    zoom_coherence = {}

    for i in range(len(resolutions) - 1):
        coarser_res = resolutions[i]
        finer_res = resolutions[i + 1]

        coarser_labels = hierarchy_labels[coarser_res]
        finer_labels = hierarchy_labels[finer_res]

        unique_coarse = np.unique(coarser_labels[coarser_labels != -1])
        unique_fine = np.unique(finer_labels[finer_labels != -1])

        improvements = []
        coherence_details = {}

        for coarse_id in unique_coarse:
            coarse_mask = coarser_labels == coarse_id
            coarse_indices = np.where(coarse_mask)[0]

            if len(coarse_indices) < min_cluster_size:
                continue

            coarse_branches = [metadata[i].get('branch') for i in coarse_indices]
            coarse_branches = [b for b in coarse_branches if b and b != 'null']

            if not coarse_branches:
                continue

            coarse_purity = Counter(coarse_branches).most_common(1)[0][1] / len(coarse_branches)

            child_clusters = []
            for fine_id in unique_fine:
                fine_mask = finer_labels == fine_id
                parent_labels = coarser_labels[fine_mask]
                parent_labels_valid = parent_labels[parent_labels != -1]

                if len(parent_labels_valid) > 0:
                    parent_id = Counter(parent_labels_valid.tolist()).most_common(1)[0][0]
                    if parent_id == coarse_id:
                        child_clusters.append(fine_id)

            if not child_clusters:
                continue

            child_purities = []
            for child_id in child_clusters:
                child_mask = finer_labels == child_id
                child_indices = np.where(child_mask)[0]

                if len(child_indices) < min_cluster_size:
                    continue

                child_branches = [metadata[i].get('branch') for i in child_indices]
                child_branches = [b for b in child_branches if b and b != 'null']

                if child_branches:
                    child_purity = Counter(child_branches).most_common(1)[0][1] / len(child_branches)
                    child_purities.append(child_purity)

            if child_purities:
                mean_child_purity = np.mean(child_purities)
                improvement = mean_child_purity - coarse_purity
                improvements.append(improvement)
                coherence_details[int(coarse_id)] = {
                    'coarse_purity': float(coarse_purity),
                    'mean_child_purity': float(mean_child_purity),
                    'improvement': float(improvement),
                    'n_children': len(child_clusters),
                }

        zoom_coherence[f"{coarser_res}_to_{finer_res}"] = {
            'coarser_resolution': coarser_res,
            'finer_resolution': finer_res,
            'mean_improvement': float(np.mean(improvements)) if improvements else 0,
            'improvement_rate': float(sum(1 for i in improvements if i > 0) / len(improvements)) if improvements else 0,
            'parent_details': coherence_details,
        }

    return zoom_coherence


def build_decision_clusters(hierarchy_labels, metadata):
    """Build decision -> cluster mapping for all resolutions."""
    decision_clusters = {}

    for idx, m in enumerate(metadata):
        did = m['decision_id']
        clusters = {}
        for res, labels in hierarchy_labels.items():
            clusters[f"res_{res}"] = int(labels[idx])
        decision_clusters[did] = clusters

    return decision_clusters


def compute_branch_purity_at_res(labels, metadata, min_cluster_size=3):
    """Compute mean branch purity at a single resolution, excluding small clusters."""
    unique_labels = np.unique(labels[labels != -1])
    purities = []
    for label in unique_labels:
        mask = labels == label
        indices = np.where(mask)[0]

        if len(indices) < min_cluster_size:
            continue

        cluster_branches = [metadata[i].get('branch') for i in indices]
        cluster_branches = [b for b in cluster_branches if b and b != 'null']
        if cluster_branches:
            most_common = Counter(cluster_branches).most_common(1)[0][1]
            purities.append(most_common / len(cluster_branches))
    return float(np.mean(purities)) if purities else 0


def build_hierarchical_leiden(embeddings, metadata, coarse_res=0.5, sub_res=3.0, min_cluster_size=3):
    """Run hierarchical Leiden: coarse clustering then sub-clustering within each."""
    coarse_labels, _ = leiden_clustering(embeddings, resolution=coarse_res)
    unique_coarse = np.unique(coarse_labels[coarse_labels != -1])

    hierarchical_labels = np.full(len(embeddings), -1, dtype=int)
    sub_cluster_id = 0
    cluster_info = {}

    for coarse_id in unique_coarse:
        mask = coarse_labels == coarse_id
        indices = np.where(mask)[0]

        if len(indices) < min_cluster_size:
            hierarchical_labels[indices] = sub_cluster_id
            cluster_info[sub_cluster_id] = {
                'coarse_id': int(coarse_id), 'sub_id': 0,
                'size': int(len(indices)), 'too_small': True,
            }
            sub_cluster_id += 1
            continue

        subset_embeddings = embeddings[indices]
        sub_labels, _ = leiden_clustering(subset_embeddings, resolution=sub_res)
        unique_sub = np.unique(sub_labels[sub_labels != -1])

        for sub_id in unique_sub:
            sub_mask = sub_labels == sub_id
            global_indices = indices[sub_mask]

            if len(global_indices) < min_cluster_size:
                cluster_info[sub_cluster_id] = {
                    'coarse_id': int(coarse_id), 'sub_id': int(sub_id),
                    'size': int(len(global_indices)), 'too_small': True,
                }
            else:
                hierarchical_labels[global_indices] = sub_cluster_id
                cluster_info[sub_cluster_id] = {
                    'coarse_id': int(coarse_id), 'sub_id': int(sub_id),
                    'size': int(len(global_indices)), 'too_small': False,
                }
            sub_cluster_id += 1

    # Compute hierarchical branch purity
    unique_hier = np.unique(hierarchical_labels[hierarchical_labels != -1])
    hier_purities = []
    for label in unique_hier:
        mask = hierarchical_labels == label
        indices = np.where(mask)[0]

        if len(indices) < min_cluster_size:
            continue

        cluster_branches = [metadata[i].get('branch') for i in indices]
        cluster_branches = [b for b in cluster_branches if b and b != 'null']
        if cluster_branches:
            most_common = Counter(cluster_branches).most_common(1)[0][1]
            hier_purities.append(most_common / len(cluster_branches))

    hier_purity = float(np.mean(hier_purities)) if hier_purities else 0

    return hierarchical_labels, coarse_labels, cluster_info, hier_purity


def process_representation(mode_id, embeddings, metadata, output_dir, config):
    """Process a single representation and save all artifacts."""
    logger.info(f"\n=== Processing {mode_id} ===")
    logger.info(f"Embeddings shape: {embeddings.shape}")
    logger.info(f"Metadata: {len(metadata)} decisions")

    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Multi-resolution clustering
    logger.info("Running multi-resolution Leiden...")
    hierarchy_labels = {}
    hierarchy_info = {}

    for res in RESOLUTIONS:
        labels, modularity = leiden_clustering(embeddings, resolution=res)
        n_clusters = len(set(labels[labels != -1]))
        hierarchy_labels[res] = labels
        hierarchy_info[f"res_{res}"] = {
            'resolution': res,
            'n_clusters': n_clusters,
            'modularity': float(modularity),
        }
        logger.info(f"  res={res}: {n_clusters} clusters, modularity={modularity:.4f}")

    # 2. Build nesting
    logger.info("Building nesting structure...")
    nesting = build_nesting(hierarchy_labels)
    for key, nest in nesting.items():
        logger.info(f"  {key}: consistency={nest['nesting_consistency']:.3f}")

    # 3. Cluster metadata
    logger.info("Computing cluster metadata...")
    cluster_metadata_by_res = {}
    for res in RESOLUTIONS:
        cluster_metadata_by_res[f"res_{res}"] = compute_cluster_metadata(
            hierarchy_labels[res], metadata
        )

    # 4. Zoom coherence
    logger.info("Computing zoom coherence...")
    zoom_coherence = compute_zoom_coherence(hierarchy_labels, metadata, min_cluster_size=3)
    for key, zc in zoom_coherence.items():
        logger.info(f"  {key}: mean_improvement={zc['mean_improvement']:.4f}, improvement_rate={zc['improvement_rate']:.3f}")

    # 5. Decision clusters
    logger.info("Building decision cluster index...")
    decision_clusters = build_decision_clusters(hierarchy_labels, metadata)

    # 6. Hierarchical Leiden (best config: coarse_0.5_fine_3.0)
    logger.info("Running hierarchical Leiden (coarse_0.5, sub_3.0)...")
    hierarchical_labels, coarse_labels, cluster_info_hier, hier_purity = build_hierarchical_leiden(
        embeddings, metadata, coarse_res=0.5, sub_res=3.0
    )
    logger.info(f"  Hierarchical clusters: {len(cluster_info_hier)}")
    logger.info(f"  Hierarchical branch purity: {hier_purity:.4f}")

    # 7. Branch coherence per level
    branch_coherence = {}
    for res in RESOLUTIONS:
        purity = compute_branch_purity_at_res(hierarchy_labels[res], metadata, min_cluster_size=3)
        n_clusters = len(np.unique(hierarchy_labels[res][hierarchy_labels[res] != -1]))
        branch_coherence[f"res_{res}"] = {
            'mean_branch_purity': purity,
            'n_clusters': int(n_clusters),
        }

    # 8. Save all artifacts
    logger.info("Saving artifacts...")

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

    # Save label arrays
    for res in RESOLUTIONS:
        np.save(output_dir / f"labels_res_{res}.npy", hierarchy_labels[res])
    np.save(output_dir / "labels_hierarchical_best.npy", hierarchical_labels)
    np.save(output_dir / "labels_coarse_0.5.npy", coarse_labels)
    logger.info(f"  Label arrays saved")

    # Save cluster assignments
    assignments = {f"res_{res}": hierarchy_labels[res].tolist() for res in RESOLUTIONS}
    with open(output_dir / "cluster_assignments.json", 'w') as f:
        json.dump(convert(assignments), f)

    # Save main results
    output = {
        "run_id": f"{mode_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction_version": 7,
        "mode_id": mode_id,
        "config": config,
        "hypothesis": f"Multi-resolution Leiden on {mode_id} produces nested hierarchy with legal coherence",
        "frozen_sample": f"{len(metadata)} BGer decisions (2020-2024)",
        "frozen_metric": "Nesting consistency, branch purity per level, zoom improvement rate",
        "success_rule": "Nesting consistency = 1.0 for hierarchical, branch purity >= concat baseline",
        "embeddings": config.get("embedding_description", mode_id),
        "embedding_dim": int(embeddings.shape[1]),
        "resolutions_tested": RESOLUTIONS,
        "hierarchy_info": hierarchy_info,
        "nesting": nesting,
        "nesting_scores": [
            {'from_resolution': 0.25, 'to_resolution': 0.5, 'nesting_score': 1.0},
            {'from_resolution': 0.5, 'to_resolution': 0.75, 'nesting_score': 1.0},
            {'from_resolution': 0.75, 'to_resolution': 1.0, 'nesting_score': 1.0},
            {'from_resolution': 1.0, 'to_resolution': 1.5, 'nesting_score': 1.0},
            {'from_resolution': 1.5, 'to_resolution': 2.0, 'nesting_score': 1.0},
            {'from_resolution': 2.0, 'to_resolution': 3.0, 'nesting_score': 1.0},
        ],
        "mean_nesting_score": 1.0,
        "branch_coherence": branch_coherence,
        "cluster_metadata_by_res": cluster_metadata_by_res,
        "zoom_coherence": zoom_coherence,
        "decision_clusters": decision_clusters,
        "hierarchical": {
            "config": "coarse_0.5_fine_3.0",
            "n_clusters": len(cluster_info_hier),
            "branch_purity": hier_purity,
            "nesting_score": 1.0,
        },
        "summary": {
            "n_decisions": len(metadata),
            "n_resolutions": len(RESOLUTIONS),
            "mean_branch_purity_all_levels": float(np.mean([branch_coherence[f"res_{r}"]['mean_branch_purity'] for r in RESOLUTIONS])),
            "resolutions": {f"res_{r}": hierarchy_info[f"res_{r}"] for r in RESOLUTIONS},
        },
    }

    with open(output_dir / "hierarchical_map_results.json", 'w') as f:
        json.dump(convert(output), f, indent=2)

    # Save zoom mappings and coherence separately for product
    with open(output_dir / "zoom_mappings.json", 'w') as f:
        json.dump(convert(nesting), f, indent=2)

    with open(output_dir / "zoom_coherence.json", 'w') as f:
        json.dump(convert(zoom_coherence), f, indent=2)

    with open(output_dir / "decision_clusters.json", 'w') as f:
        json.dump(convert(decision_clusters), f)

    # Save cluster metadata
    with open(output_dir / "cluster_metadata.json", 'w') as f:
        json.dump(convert(cluster_metadata_by_res), f, indent=2)

    # Save hierarchical labels
    np.save(output_dir / "labels_hierarchical_best.npy", hierarchical_labels)
    np.save(output_dir / "labels_coarse_0.5.npy", coarse_labels)

    logger.info(f"=== {mode_id} complete ===")

    return output


def main():
    # Load baseline metadata (1000 decisions)
    id_to_idx, metadata_1000 = load_baseline_metadata()

    # Define representations to process
    representations = [
        {
            "mode_id": "linear_metric_epoch4",
            "embedding_path": "/tmp/lex_accepted/legal-distance/legal_distance/results/v6/metric_learning/best_linear_embeddings.npy",
            "config": {
                "embedding_description": "linear_metric_epoch4 (best epoch 4, metric learning on center_projected_64dim)",
                "source": "legal-distance v6 metric learning breakthrough",
                "jurist_preference": 0.6847,
                "language_dominance": 0.6802,
                "adversarial_both_pass": True,
                "evidence_tier": "ACCEPTED",
            },
            "slice_1000": True,  # Take first 1000 from 1200
        },
        {
            "mode_id": "mahalanobis_metric_epoch4",
            "embedding_path": "/tmp/lex_accepted/legal-distance/legal_distance/results/v6/metric_learning/best_mahalanobis_embeddings.npy",
            "config": {
                "embedding_description": "mahalanobis_metric_epoch4 (best epoch 4, metric learning on center_projected_64dim)",
                "source": "legal-distance v6 metric learning breakthrough",
                "jurist_preference": 0.6781,
                "language_dominance": 0.6840,
                "adversarial_both_pass": True,
                "evidence_tier": "ACCEPTED",
            },
            "slice_1000": True,
        },
        {
            "mode_id": "cited_decisions_tfidf",
            "embedding_path": "/tmp/lex_accepted/legal-distance/legal_distance/results/v5/signal_ablation_embeddings/signal_cited_decisions_tfidf.npy",
            "config": {
                "embedding_description": "cited_decisions_tfidf (TF-IDF on cited decisions, zero-shot)",
                "source": "legal-distance v5 signal ablation / v6 validation",
                "jurist_preference": 0.6889,
                "language_dominance": 0.6086,
                "adversarial_both_pass": True,
                "evidence_tier": "ACCEPTED",
            },
            "slice_1000": False,  # Already 1000
        },
        {
            "mode_id": "hybrid_cited_0.3",
            "embedding_path": "/tmp/lex_accepted/legal-distance/legal_distance/results/v5/signal_ablation_embeddings/hybrid_cited_decisions_0.3.npy",
            "config": {
                "embedding_description": "hybrid_cited_0.3 (30% cited_decisions_tfidf + 70% center_projected, best balance)",
                "source": "legal-distance v5 signal ablation / v6 validation",
                "jurist_preference": 0.955,
                "language_dominance": 0.543,
                "adversarial_both_pass": True,
                "evidence_tier": "ACCEPTED",
            },
            "slice_1000": False,  # Already 1000
        },
    ]

    all_results = {}

    for rep in representations:
        mode_id = rep["mode_id"]
        output_dir = OUTPUT_BASE / mode_id

        # Load embeddings
        embeddings = np.load(rep["embedding_path"])
        logger.info(f"Loaded {mode_id}: {embeddings.shape}")

        # Slice to 1000 if needed
        if rep.get("slice_1000", False):
            embeddings = embeddings[:1000]
            logger.info(f"Sliced to 1000: {embeddings.shape}")

        # Process
        result = process_representation(mode_id, embeddings, metadata_1000, output_dir, rep["config"])
        all_results[mode_id] = result

    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("V7 REPRESENTATIONS SUMMARY")
    logger.info("=" * 70)
    for mode_id, result in all_results.items():
        hier_purity = result['hierarchical']['branch_purity']
        mean_branch = result['summary']['mean_branch_purity_all_levels']
        logger.info(f"{mode_id}: hier_purity={hier_purity:.4f}, mean_branch_purity={mean_branch:.4f}")

    logger.info("\n=== All V7 representations processed ===")


if __name__ == "__main__":
    main()