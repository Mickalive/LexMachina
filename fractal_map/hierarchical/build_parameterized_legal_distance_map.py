#!/usr/bin/env python3
"""
Parameterized Hierarchical Map Builder for LEGAL-DISTANCE modes.

Scales multi-resolution Leiden fractal maps for legal-distance representations
(including the two BEST outcome-hybrid modes) to arbitrary corpus sizes.

WHY THIS EXISTS (lanes the scalability gap flagged across many audit resumes):
  The prior `build_parameterized_map.py` supported ONLY center_projected. The
  two BEST production/fractal modes (cited_decisions_tfidf_outcome_hybrid_0.5
  and _0.7) had NO parameterized builder and NO reproducibility provenance.
  This closes both gaps.

PROVENANCE RULE (verified in run 33317287543, outcome_hybrid_provenance_repro):
  The accepted legal-distance embedding cache (e.g. 1200-decision *.npy) reproduces
  the validated 1000-decision map labels EXACTLY (purity=1.0 at every resolution,
  coarse_0.5, and hierarchical_best) IF AND ONLY IF the embedding is sliced to the
  map's decision subset BEFORE clustering. Clustering on the full superset then
  slicing the result gives only ~0.88 purity. Therefore this builder always
  operates on the slice that matches the metadata it is given.

  Also verified: for legal-distance modes, `labels_hierarchical_best` equals
  `labels_res_3.0` (single finest-resolution assignment, NOT the two-stage
  coarse_0.5->sub_3.0 subclustering used for center_projected).

Usage:
    python build_parameterized_legal_distance_map.py \
        --embedding-path <mode>.npy \
        --corpus-size 1000 \
        --output-dir results/fractal_map/legal_distance_modes/<mode> \
        --mode-id <mode>
"""

import json
import argparse
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone

# Default paths (mirror prior builder conventions)
DEFAULT_BASELINE_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/baseline")
DEFAULT_CORPUS_DIR = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")

RESOLUTIONS = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
MIN_CLUSTER_SIZE = 3


def load_metadata_with_branch(baseline_dir, corpus_dir, corpus_size=None,
                              metadata_path=None, has_branch=False):
    meta_file = Path(metadata_path) if metadata_path else baseline_dir / "metadata.json"
    with open(meta_file) as f:
        metadata = json.load(f)
    if corpus_size and len(metadata) > corpus_size:
        metadata = metadata[:corpus_size]
    if has_branch:
        return {m['decision_id']: i for i, m in enumerate(metadata)}, metadata
    id_to_idx = {m['decision_id']: i for i, m in enumerate(metadata)}
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
    return id_to_idx, metadata


def leiden_clustering(embeddings, resolution=1.0, k=15, seed=42):
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
        weights='weight', resolution_parameter=resolution, seed=seed)
    return np.array(partition.membership)


def build_nesting(hierarchy_labels):
    resolutions = sorted(hierarchy_labels.keys())
    nesting = {}
    for i in range(len(resolutions) - 1):
        coarser_res = resolutions[i]
        finer_res = resolutions[i + 1]
        coarser_labels = hierarchy_labels[coarser_res]
        finer_labels = hierarchy_labels[finer_res]
        child_to_parent = {}
        for fine_id in np.unique(finer_labels[finer_labels != -1]):
            fine_mask = finer_labels == fine_id
            parent_labels = coarser_labels[fine_mask]
            parent_labels_valid = parent_labels[parent_labels != -1]
            if len(parent_labels_valid) > 0:
                child_to_parent[int(fine_id)] = int(
                    Counter(parent_labels_valid.tolist()).most_common(1)[0][0])
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
            'nesting_consistency': (sum(1 for c, p in child_to_parent.items() if p != -1)
                                    / len(child_to_parent) if child_to_parent else 0),
        }
    return nesting


def compute_cluster_metadata(labels, metadata):
    cluster_info = {}
    for label in np.unique(labels[labels != -1]):
        mask = labels == label
        indices = np.where(mask)[0]
        cluster_meta = [metadata[i] for i in indices]
        langs = Counter(m.get('language') for m in cluster_meta if m.get('language'))
        branches = Counter(m.get('branch') for m in cluster_meta if m.get('branch'))
        areas = Counter(m.get('legal_area') for m in cluster_meta if m.get('legal_area'))
        years = Counter(m.get('year') for m in cluster_meta if m.get('year'))
        chambers = Counter(m.get('chamber') for m in cluster_meta if m.get('chamber'))
        dominant_lang = langs.most_common(1)[0] if langs else (None, 0)
        dominant_branch = branches.most_common(1)[0] if branches else (None, 0)
        dominant_area = areas.most_common(1)[0] if areas else (None, 0)
        cluster_info[int(label)] = {
            'size': int(mask.sum()),
            'dominant_lang': dominant_lang[0],
            'lang_purity': dominant_lang[1] / len(indices) if indices.size else 0,
            'dominant_branch': dominant_branch[0],
            'branch_purity': dominant_branch[1] / len(indices) if indices.size else 0,
            'dominant_area': dominant_area[0],
            'area_count': len(areas),
            'top_areas': {str(k): int(v) for k, v in areas.most_common(5)},
            'top_branches': {str(k): int(v) for k, v in branches.most_common(5)},
            'year_dist': {str(k): int(v) for k, v in years.most_common()},
            'top_chambers': {str(k): int(v) for k, v in chambers.most_common(3)},
            'decision_ids': [metadata[i]['decision_id'] for i in indices],
            'decision_indices': indices.tolist(),
        }
    return cluster_info


def compute_zoom_coherence(hierarchy_labels, metadata, min_cluster_size=3):
    resolutions = sorted(hierarchy_labels.keys())
    zoom_coherence = {}
    for i in range(len(resolutions) - 1):
        coarser_res = resolutions[i]
        finer_res = resolutions[i + 1]
        coarser_labels = hierarchy_labels[coarser_res]
        finer_labels = hierarchy_labels[finer_res]
        improvements = []
        parent_details = {}
        for coarse_id in np.unique(coarser_labels[coarser_labels != -1]):
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
            for fine_id in np.unique(finer_labels[finer_labels != -1]):
                fine_mask = finer_labels == fine_id
                parent_labels = coarser_labels[fine_mask]
                parent_labels_valid = parent_labels[parent_labels != -1]
                if len(parent_labels_valid) > 0 and \
                        Counter(parent_labels_valid.tolist()).most_common(1)[0][0] == coarse_id:
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
                    child_purities.append(Counter(child_branches).most_common(1)[0][1]
                                          / len(child_branches))
            if child_purities:
                mean_child_purity = np.mean(child_purities)
                improvements.append(mean_child_purity - coarse_purity)
                parent_details[int(coarse_id)] = {
                    'coarse_purity': float(coarse_purity),
                    'mean_child_purity': float(mean_child_purity),
                    'improvement': float(mean_child_purity - coarse_purity),
                    'n_children': len(child_clusters),
                }
        zoom_coherence[f"{coarser_res}_to_{finer_res}"] = {
            'coarser_resolution': coarser_res,
            'finer_resolution': finer_res,
            'mean_improvement': float(np.mean(improvements)) if improvements else 0,
            'improvement_rate': float(sum(1 for j in improvements if j > 0)
                                      / len(improvements)) if improvements else 0,
            'parent_details': parent_details,
        }
    return zoom_coherence


def build_decision_clusters(hierarchy_labels, metadata):
    decision_clusters = {}
    for idx, m in enumerate(metadata):
        did = m['decision_id']
        decision_clusters[did] = {f"res_{res}": int(hierarchy_labels[res][idx])
                                  for res in hierarchy_labels}
    return decision_clusters


def compute_branch_purity(labels, metadata, min_cluster_size=3):
    purities = []
    for label in np.unique(labels[labels != -1]):
        mask = labels == label
        indices = np.where(mask)[0]
        if len(indices) < min_cluster_size:
            continue
        branches = [metadata[i].get('branch') for i in indices]
        branches = [b for b in branches if b and b != 'null']
        if branches:
            purities.append(Counter(branches).most_common(1)[0][1] / len(branches))
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
    parser = argparse.ArgumentParser(description='Build parameterized legal-distance map')
    parser.add_argument('--embedding-path', type=Path, required=True,
                        help='Path to source embedding .npy (legal-distance cache)')
    parser.add_argument('--mode-id', type=str, default='legal_distance_mode',
                        help='Mode id for output naming')
    parser.add_argument('--corpus-size', type=int, default=None,
                        help='Number of decisions (slice taken from embedding start)')
    parser.add_argument('--baseline-dir', type=Path, default=DEFAULT_BASELINE_DIR)
    parser.add_argument('--corpus-dir', type=Path, default=DEFAULT_CORPUS_DIR)
    parser.add_argument('--metadata-path', type=Path, default=None,
                        help='Override metadata.json location (for scale runs)')
    parser.add_argument('--metadata-has-branch', action='store_true',
                        help='Metadata already carries branch field (skip corpus enrichment)')
    parser.add_argument('--output-dir', type=Path,
                        default=Path('results/fractal_map/legal_distance_modes_default'))
    parser.add_argument('--min-cluster-size', type=int, default=MIN_CLUSTER_SIZE)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load embeddings and slice to corpus-size (provenance rule: slice BEFORE clustering)
    embeddings = np.load(args.embedding_path)
    if args.corpus_size and embeddings.shape[0] > args.corpus_size:
        embeddings = embeddings[:args.corpus_size]

    # 2. Load metadata limited to corpus-size
    id_to_idx, metadata = load_metadata_with_branch(
        args.baseline_dir, args.corpus_dir, args.corpus_size,
        metadata_path=args.metadata_path, has_branch=args.metadata_has_branch)

    if embeddings.shape[0] != len(metadata):
        raise SystemExit(
            f"Embedding slice {embeddings.shape[0]} != metadata {len(metadata)}. "
            f"Aborting to avoid misalignment.")

    # 3. Multi-resolution Leiden
    hierarchy_labels = {}
    hierarchy_info = {}
    for res in RESOLUTIONS:
        labels = leiden_clustering(embeddings, resolution=res)
        hierarchy_labels[res] = labels
        hierarchy_info[f"res_{res}"] = {
            'resolution': res,
            'n_clusters': int(len(set(labels[labels != -1]))),
        }

    # 4. Nesting
    nesting = build_nesting(hierarchy_labels)

    # 5. Cluster metadata
    cluster_metadata_by_res = {}
    for res in RESOLUTIONS:
        cluster_metadata_by_res[f"res_{res}"] = compute_cluster_metadata(
            hierarchy_labels[res], metadata)

    # 6. Zoom coherence
    zoom_coherence = compute_zoom_coherence(hierarchy_labels, metadata,
                                            min_cluster_size=args.min_cluster_size)

    # 7. Decision clusters
    decision_clusters = build_decision_clusters(hierarchy_labels, metadata)

    # 8. hierarchical_best := finest resolution (verified rule for legal-distance modes)
    hierarchical_labels = hierarchy_labels[RESOLUTIONS[-1]]
    coarse_labels = hierarchy_labels[0.5]
    hier_purity = compute_branch_purity(hierarchical_labels, metadata,
                                        min_cluster_size=args.min_cluster_size)
    coarse_purity = compute_branch_purity(coarse_labels, metadata,
                                          min_cluster_size=args.min_cluster_size)

    branch_coherence = {}
    for res in RESOLUTIONS:
        branch_coherence[f"res_{res}"] = {
            'mean_branch_purity': compute_branch_purity(hierarchy_labels[res], metadata,
                                                        min_cluster_size=args.min_cluster_size),
            'n_clusters': int(len(np.unique(hierarchy_labels[res][hierarchy_labels[res] != -1]))),
        }

    # 9. Save artifacts (same layout as prior builders / product loader expectations)
    for res in RESOLUTIONS:
        np.save(args.output_dir / f"labels_res_{res}.npy", hierarchy_labels[res])
    np.save(args.output_dir / "labels_hierarchical_best.npy", hierarchical_labels)
    np.save(args.output_dir / "labels_coarse_0.5.npy", coarse_labels)

    output = {
        "run_id": f"parameterized_legal_distance_{args.mode_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction_version": 10,
        "mode_id": args.mode_id,
        "hypothesis": "Multi-resolution Leiden on legal-distance embeddings produces nested hierarchy",
        "frozen_sample": f"{len(metadata)} decisions ({args.mode_id})",
        "frozen_metric": "Nesting consistency, branch purity per level, zoom improvement rate, provenance purity",
        "embeddings_source": str(args.embedding_path),
        "corpus_size": len(metadata),
        "resolutions_tested": RESOLUTIONS,
        "hierarchy_info": hierarchy_info,
        "nesting": nesting,
        "mean_nesting_score": float(np.mean([n['nesting_consistency'] for n in nesting.values()])),
        "branch_coherence": branch_coherence,
        "zoom_coherence": zoom_coherence,
        "hierarchical": {
            "config": "fine_3.0 (legal-distance rule: hierarchical_best := finest resolution)",
            "n_clusters": int(len(set(hierarchical_labels[hierarchical_labels != -1]))),
            "branch_purity": hier_purity,
            "coarse_0.5_purity": coarse_purity,
        },
        "summary": {
            "n_decisions": len(metadata),
            "n_resolutions": len(RESOLUTIONS),
            "mean_branch_purity_all_levels": float(np.mean(
                [branch_coherence[f"res_{r}"]['mean_branch_purity'] for r in RESOLUTIONS])),
        },
    }
    with open(args.output_dir / "hierarchical_map_results.json", 'w') as f:
        json.dump(convert(output), f, indent=2)
    with open(args.output_dir / "zoom_mappings.json", 'w') as f:
        json.dump(convert(nesting), f, indent=2)
    with open(args.output_dir / "zoom_coherence.json", 'w') as f:
        json.dump(convert(zoom_coherence), f, indent=2)
    with open(args.output_dir / "decision_clusters.json", 'w') as f:
        json.dump(convert(decision_clusters), f)
    with open(args.output_dir / "cluster_metadata.json", 'w') as f:
        json.dump(convert(cluster_metadata_by_res), f, indent=2)

    print(json.dumps({
        "mode_id": args.mode_id,
        "corpus_size": len(metadata),
        "n_fine_clusters": int(len(set(hierarchical_labels[hierarchical_labels != -1]))),
        "mean_nesting_score": float(np.mean([n['nesting_consistency'] for n in nesting.values()])),
        "mean_branch_purity_all_levels": float(np.mean(
            [branch_coherence[f"res_{r}"]['mean_branch_purity'] for r in RESOLUTIONS])),
        "output_dir": str(args.output_dir),
    }, indent=2))


if __name__ == "__main__":
    main()
