#!/usr/bin/env python3
"""
Parameter sweep for constrained hierarchical Leiden on 174k hybrid embeddings.
Goal: Find configuration achieving fine_branch_purity > 0.5 for hybrid0.5 and hybrid0.7
"""
import json
import numpy as np
from pathlib import Path
from collections import Counter
import logging
from datetime import datetime, timezone
import igraph as ig
import leidenalg
from sklearn.neighbors import kneighbors_graph
import itertools

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

EMBEDDINGS_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings")
METADATA_DIR = Path("/tmp/lex_accepted/evaluation/corpus")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/parameter_sweep_174k_hybrid")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_metadata_with_branch():
    """Load metadata and enrich with branch from corpus files."""
    # Try to load from accepted evaluation corpus
    metadata_files = list(METADATA_DIR.glob("metadata_174k*.json"))
    if metadata_files:
        with open(metadata_files[0]) as f:
            metadata = json.load(f)
        logger.info(f"Loaded metadata from {metadata_files[0]}: {len(metadata)} entries")
    else:
        # Fallback to the standard location
        with open(EMBEDDINGS_DIR.parent.parent / "baseline" / "metadata.json") as f:
            metadata = json.load(f)
        logger.info(f"Loaded metadata from baseline: {len(metadata)} entries")

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

    # Count how many have branch
    with_branch = sum(1 for m in metadata if m.get('branch'))
    logger.info(f"Branch coverage: {with_branch}/{len(metadata)} = {with_branch/len(metadata):.3f}")

    return id_to_idx, metadata


def load_embeddings(embedding_name):
    """Load specified embedding."""
    path = EMBEDDINGS_DIR / f"{embedding_name}.npy"
    embeddings = np.load(path)
    logger.info(f"Loaded {embedding_name}: {embeddings.shape}")
    return embeddings


def leiden_clustering(embeddings, resolution=1.0, k=15):
    """Leiden clustering."""
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


def constrained_hierarchical_leiden(embeddings, metadata,
                                    coarse_res=0.25, base_sub_res=3.0,
                                    min_cluster_size=10, max_subclusters_per_parent=20,
                                    adaptive_sub_res=True, k=15):
    """
    Run constrained hierarchical Leiden with adaptive sub-resolution.
    """
    # Step 1: Global coarse clustering
    coarse_labels, coarse_mod = leiden_clustering(embeddings, resolution=coarse_res, k=k)
    unique_coarse = np.unique(coarse_labels[coarse_labels != -1])

    logger.info(f"  Coarse (res={coarse_res}): {len(unique_coarse)} clusters, modularity={coarse_mod:.4f}")

    # Step 2: Within each coarse cluster, run Leiden at adaptive sub_res
    hierarchical_labels = np.full(len(embeddings), -1, dtype=int)
    sub_cluster_id = 0
    cluster_info = {}

    for coarse_id in unique_coarse:
        mask = coarse_labels == coarse_id
        indices = np.where(mask)[0]

        if len(indices) < min_cluster_size * 2:
            # Too small to split meaningfully
            hierarchical_labels[indices] = sub_cluster_id
            cluster_info[sub_cluster_id] = {
                'coarse_id': int(coarse_id),
                'sub_id': 0,
                'size': int(len(indices)),
                'too_small': True,
                'sub_res_used': None,
            }
            sub_cluster_id += 1
            continue

        subset_embeddings = embeddings[indices]

        # Adaptive sub-resolution based on cluster size
        if adaptive_sub_res:
            if len(indices) > 5000:
                sub_res = base_sub_res * 0.5
            elif len(indices) > 2000:
                sub_res = base_sub_res * 0.75
            elif len(indices) > 500:
                sub_res = base_sub_res
            else:
                sub_res = base_sub_res * 1.5
        else:
            sub_res = base_sub_res

        # Run Leiden within subset
        sub_labels, sub_mod = leiden_clustering(subset_embeddings, resolution=sub_res, k=k)
        unique_sub = np.unique(sub_labels[sub_labels != -1])

        # Limit number of subclusters per parent
        if len(unique_sub) > max_subclusters_per_parent:
            # Merge smallest clusters
            sub_sizes = [(s, np.sum(sub_labels == s)) for s in unique_sub]
            sub_sizes.sort(key=lambda x: x[1])
            to_merge = sub_sizes[:len(unique_sub) - max_subclusters_per_parent]
            merge_map = {s: sub_sizes[-1][0] for s, _ in to_merge}
            for i in range(len(sub_labels)):
                if sub_labels[i] in merge_map:
                    sub_labels[i] = merge_map[sub_labels[i]]
            unique_sub = np.unique(sub_labels[sub_labels != -1])

        logger.info(f"    Coarse {coarse_id} ({len(indices)} docs): "
                    f"{len(unique_sub)} sub-clusters, sub_res={sub_res:.2f}, modularity={sub_mod:.4f}")

        # Assign global labels
        for sub_id in unique_sub:
            sub_mask = sub_labels == sub_id
            global_indices = indices[sub_mask]

            if len(global_indices) < min_cluster_size:
                # Merge into a remainder cluster for this parent
                continue

            hierarchical_labels[global_indices] = sub_cluster_id
            cluster_info[sub_cluster_id] = {
                'coarse_id': int(coarse_id),
                'sub_id': int(sub_id),
                'size': int(len(global_indices)),
                'too_small': False,
                'sub_res_used': float(sub_res),
            }
            sub_cluster_id += 1

    return hierarchical_labels, coarse_labels, cluster_info


def compute_branch_purity(labels, metadata):
    """Compute branch purity."""
    unique_labels = np.unique(labels[labels != -1])
    purities = []

    for label in unique_labels:
        mask = labels == label
        cluster_branches = [metadata[i].get('branch') for i in np.where(mask)[0]]
        cluster_branches = [b for b in cluster_branches if b and b != 'null']

        if cluster_branches:
            most_common = Counter(cluster_branches).most_common(1)[0][1]
            purities.append(most_common / len(cluster_branches))

    return float(np.mean(purities)) if purities else 0


def compute_area_purity(labels, metadata):
    """Compute legal_area purity."""
    unique_labels = np.unique(labels[labels != -1])
    purities = []

    for label in unique_labels:
        mask = labels == label
        cluster_areas = [metadata[i].get('legal_area') for i in np.where(mask)[0]]
        cluster_areas = [a for a in cluster_areas if a and a != 'null']

        if cluster_areas:
            most_common = Counter(cluster_areas).most_common(1)[0][1]
            purities.append(most_common / len(cluster_areas))

    return float(np.mean(purities)) if purities else 0


def compute_fragmentation(labels):
    """Compute fragmentation metrics."""
    unique_labels = np.unique(labels[labels != -1])
    sizes = [np.sum(labels == l) for l in unique_labels]

    from collections import Counter
    size_dist = Counter(sizes)

    return {
        'n_clusters': int(len(unique_labels)),
        'median_size': float(np.median(sizes)),
        'mean_size': float(np.mean(sizes)),
        'singleton_fraction': float(np.sum(np.array(sizes) == 1) / len(sizes)),
        'size_distribution': {str(k): int(v) for k, v in sorted(size_dist.items())},
        'max_size': int(np.max(sizes)),
        'min_size': int(np.min(sizes)),
    }


def compute_zoom_coherence(hierarchical_labels, coarse_labels, metadata):
    """Compute zoom coherence (improvement from coarse to fine)."""
    unique_coarse = np.unique(coarse_labels[coarse_labels != -1])
    parent_details = {}
    improvements = []

    for coarse_id in unique_coarse:
        coarse_mask = coarse_labels == coarse_id
        coarse_indices = np.where(coarse_mask)[0]

        if len(coarse_indices) < 2:
            continue

        # Get fine labels within this coarse cluster
        fine_labels = hierarchical_labels[coarse_indices]
        unique_fine = np.unique(fine_labels[fine_labels != -1])

        if len(unique_fine) <= 1:
            continue

        # Compute coarse purity
        coarse_branches = [metadata[i].get('branch') for i in coarse_indices]
        coarse_branches = [b for b in coarse_branches if b and b != 'null']
        if not coarse_branches:
            continue
        coarse_purity = Counter(coarse_branches).most_common(1)[0][1] / len(coarse_branches)

        # Compute mean child purity
        child_purities = []
        for fine_id in unique_fine:
            fine_mask = fine_labels == fine_id
            fine_indices = coarse_indices[fine_mask]
            fine_branches = [metadata[i].get('branch') for i in fine_indices]
            fine_branches = [b for b in fine_branches if b and b != 'null']
            if fine_branches:
                child_purity = Counter(fine_branches).most_common(1)[0][1] / len(fine_branches)
                child_purities.append(child_purity)

        if not child_purities:
            continue

        mean_child_purity = np.mean(child_purities)
        improvement = mean_child_purity - coarse_purity

        parent_details[str(int(coarse_id))] = {
            'coarse_purity': float(coarse_purity),
            'mean_child_purity': float(mean_child_purity),
            'improvement': float(improvement),
            'n_children': int(len(unique_fine)),
        }
        improvements.append(improvement)

    if improvements:
        return {
            'mean_improvement': float(np.mean(improvements)),
            'improvement_rate': float(np.sum(np.array(improvements) > 0) / len(improvements)),
            'n_parents': len(improvements),
            'parent_details': parent_details,
        }
    else:
        return {
            'mean_improvement': 0.0,
            'improvement_rate': 0.0,
            'n_parents': 0,
            'parent_details': {},
        }


def run_config(embedding_name, embeddings, metadata, config):
    """Run a single configuration."""
    logger.info(f"Running config: {config}")

    hierarchical_labels, coarse_labels, cluster_info = constrained_hierarchical_leiden(
        embeddings, metadata,
        coarse_res=config['coarse_res'],
        base_sub_res=config['base_sub_res'],
        min_cluster_size=config['min_cluster_size'],
        max_subclusters_per_parent=config['max_subclusters_per_parent'],
        adaptive_sub_res=config['adaptive_sub_res'],
    )

    # Compute metrics
    coarse_purity = compute_branch_purity(coarse_labels, metadata)
    coarse_area_purity = compute_area_purity(coarse_labels, metadata)
    hier_purity = compute_branch_purity(hierarchical_labels, metadata)
    hier_area_purity = compute_area_purity(hierarchical_labels, metadata)
    fragmentation = compute_fragmentation(hierarchical_labels)
    zoom_coherence = compute_zoom_coherence(hierarchical_labels, coarse_labels, metadata)

    # Nesting is guaranteed by construction
    nesting = 1.0

    result = {
        'embedding': embedding_name,
        'config': config,
        'coarse': {
            'n_clusters': int(len(np.unique(coarse_labels[coarse_labels != -1]))),
            'branch_purity': coarse_purity,
            'area_purity': coarse_area_purity,
            'fragmentation': compute_fragmentation(coarse_labels),
        },
        'hierarchical': {
            'n_clusters': int(len(np.unique(hierarchical_labels[hierarchical_labels != -1]))),
            'branch_purity': hier_purity,
            'area_purity': hier_area_purity,
            'fragmentation': fragmentation,
            'nesting': nesting,
        },
        'zoom_coherence': zoom_coherence,
        'cluster_info': {str(k): v for k, v in cluster_info.items()},
    }

    logger.info(f"  coarse_branch_purity: {coarse_purity:.4f}")
    logger.info(f"  hierarchical_branch_purity: {hier_purity:.4f}")
    logger.info(f"  zoom improvement_rate: {zoom_coherence['improvement_rate']:.3f}")

    return result


def main():
    logger.info("=== 174k Hybrid Parameter Sweep ===")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")

    # Load metadata
    id_to_idx, metadata = load_metadata_with_branch()

    # Embeddings to test
    embedding_names = [
        'cited_decisions_tfidf_outcome_hybrid_0.5',
        'cited_decisions_tfidf_outcome_hybrid_0.7',
        'full_text_tfidf_light',
        'regeste_tfidf',  # Already known to pass at 83k, test at 174k
    ]

    # Parameter configurations to test
    # The current config: coarse_res=0.25, base_sub_res=3.0, min_cluster_size=10, max_subclusters=20, adaptive=True
    configs = [
        # Vary coarse_res
        {'coarse_res': 0.15, 'base_sub_res': 3.0, 'min_cluster_size': 10, 'max_subclusters_per_parent': 20, 'adaptive_sub_res': True},
        {'coarse_res': 0.25, 'base_sub_res': 3.0, 'min_cluster_size': 10, 'max_subclusters_per_parent': 20, 'adaptive_sub_res': True},
        {'coarse_res': 0.5, 'base_sub_res': 3.0, 'min_cluster_size': 10, 'max_subclusters_per_parent': 20, 'adaptive_sub_res': True},
        {'coarse_res': 0.75, 'base_sub_res': 3.0, 'min_cluster_size': 10, 'max_subclusters_per_parent': 20, 'adaptive_sub_res': True},

        # Vary base_sub_res
        {'coarse_res': 0.25, 'base_sub_res': 1.5, 'min_cluster_size': 10, 'max_subclusters_per_parent': 20, 'adaptive_sub_res': True},
        {'coarse_res': 0.25, 'base_sub_res': 2.0, 'min_cluster_size': 10, 'max_subclusters_per_parent': 20, 'adaptive_sub_res': True},
        {'coarse_res': 0.25, 'base_sub_res': 4.0, 'min_cluster_size': 10, 'max_subclusters_per_parent': 20, 'adaptive_sub_res': True},
        {'coarse_res': 0.25, 'base_sub_res': 5.0, 'min_cluster_size': 10, 'max_subclusters_per_parent': 20, 'adaptive_sub_res': True},

        # Vary min_cluster_size
        {'coarse_res': 0.25, 'base_sub_res': 3.0, 'min_cluster_size': 5, 'max_subclusters_per_parent': 20, 'adaptive_sub_res': True},
        {'coarse_res': 0.25, 'base_sub_res': 3.0, 'min_cluster_size': 20, 'max_subclusters_per_parent': 20, 'adaptive_sub_res': True},
        {'coarse_res': 0.25, 'base_sub_res': 3.0, 'min_cluster_size': 50, 'max_subclusters_per_parent': 20, 'adaptive_sub_res': True},

        # Vary max_subclusters_per_parent
        {'coarse_res': 0.25, 'base_sub_res': 3.0, 'min_cluster_size': 10, 'max_subclusters_per_parent': 10, 'adaptive_sub_res': True},
        {'coarse_res': 0.25, 'base_sub_res': 3.0, 'min_cluster_size': 10, 'max_subclusters_per_parent': 30, 'adaptive_sub_res': True},
        {'coarse_res': 0.25, 'base_sub_res': 3.0, 'min_cluster_size': 10, 'max_subclusters_per_parent': 50, 'adaptive_sub_res': True},

        # Fixed sub_res (no adaptive)
        {'coarse_res': 0.25, 'base_sub_res': 3.0, 'min_cluster_size': 10, 'max_subclusters_per_parent': 20, 'adaptive_sub_res': False},
        {'coarse_res': 0.25, 'base_sub_res': 2.0, 'min_cluster_size': 10, 'max_subclusters_per_parent': 20, 'adaptive_sub_res': False},

        # Promising combos from 12k results
        {'coarse_res': 0.5, 'base_sub_res': 2.0, 'min_cluster_size': 20, 'max_subclusters_per_parent': 20, 'adaptive_sub_res': False},
        {'coarse_res': 0.25, 'base_sub_res': 3.0, 'min_cluster_size': 20, 'max_subclusters_per_parent': 20, 'adaptive_sub_res': False},
    ]

    all_results = {}

    for embedding_name in embedding_names:
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing embedding: {embedding_name}")
        logger.info(f"{'='*60}")

        embeddings = load_embeddings(embedding_name)

        # Subsample if too large for rapid testing (use first 50k for sweep)
        # Actually, let's run on full 174k for accuracy
        embedding_results = {}

        for i, config in enumerate(configs):
            logger.info(f"\nConfig {i+1}/{len(configs)}: {config}")

            try:
                result = run_config(embedding_name, embeddings, metadata, config)
                config_key = f"coarse_{config['coarse_res']}_sub_{config['base_sub_res']}_min_{config['min_cluster_size']}_max_{config['max_subclusters_per_parent']}_adaptive_{config['adaptive_sub_res']}"
                embedding_results[config_key] = result

                # Save intermediate
                output_path = OUTPUT_DIR / f"{embedding_name}_{config_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(output_path, 'w') as f:
                    json.dump(result, f, indent=2, default=str)
                logger.info(f"  Saved to {output_path}")

            except Exception as e:
                logger.error(f"  Config failed: {e}")
                import traceback
                traceback.print_exc()

        all_results[embedding_name] = embedding_results

    # Save summary
    summary = {
        'run_id': f"parameter_sweep_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'direction_version': 28,
        'embeddings_tested': embedding_names,
        'configs_tested': len(configs),
        'results': all_results,
    }

    summary_path = OUTPUT_DIR / f"sweep_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    logger.info(f"\nSummary saved to {summary_path}")

    # Print best configs per embedding
    logger.info("\n" + "="*60)
    logger.info("BEST CONFIGS PER EMBEDDING (by hierarchical_branch_purity)")
    logger.info("="*60)

    for emb_name, emb_results in all_results.items():
        if not emb_results:
            continue
        best = max(emb_results.items(), key=lambda x: x[1]['hierarchical']['branch_purity'])
        logger.info(f"\n{emb_name}:")
        logger.info(f"  Best config: {best[0]}")
        logger.info(f"  Hierarchical branch purity: {best[1]['hierarchical']['branch_purity']:.4f}")
        logger.info(f"  Coarse branch purity: {best[1]['coarse']['branch_purity']:.4f}")
        logger.info(f"  Zoom improvement_rate: {best[1]['zoom_coherence']['improvement_rate']:.3f}")
        logger.info(f"  Fine clusters: {best[1]['hierarchical']['n_clusters']}")

    logger.info("\n=== Parameter sweep complete ===")


if __name__ == "__main__":
    main()