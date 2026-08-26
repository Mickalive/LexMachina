#!/usr/bin/env python3
"""
Experiment: Language-Debiased Fractal Map

Hypothesis: The primary geometric signal in multilingual embeddings is language
(DE/FR/IT), not legal content. By projecting out the language-correlated
subspace, we can reveal the underlying legal signal.

Methods tested:
1. PCA language removal: find top embedding-space directions correlated with
   language, project them out
2. Language-center projection: compute language cluster centers in embedding
   space, project out the subspace they span

Product decision: If debiasing improves legal-area purity by >10% while
maintaining hierarchy consistency, it becomes a candidate preprocessing step.

Evidence tier: EXPLORATORY
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

CORPUS_DIR = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
BASELINE_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/baseline")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/language_debiasing")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_baseline():
    embeddings = np.load(BASELINE_DIR / "embeddings.npy")
    with open(BASELINE_DIR / "metadata.json") as f:
        metadata = json.load(f)
    return embeddings, metadata


def pca_language_removal(embeddings, metadata, n_components=2):
    """
    Find the top-n embedding-space directions most correlated with language,
    then project them out.

    Algorithm:
    1. One-hot encode language for each decision
    2. Regress embeddings onto language indicators to get residual directions
    3. SVD of the language-difference matrix gives principal language directions
    4. Project out those directions
    """
    # One-hot language indicators (use 2 of 3 to avoid rank deficiency)
    languages = sorted(set(m['language'] for m in metadata))
    lang_map = {l: i for i, l in enumerate(languages)}

    L = np.zeros((len(metadata), len(languages)))
    for i, m in enumerate(metadata):
        lang = m.get('language')
        if lang in lang_map:
            L[i, lang_map[lang]] = 1.0

    # Use first 2 languages (DE, FR) — IT is linearly dependent
    L2 = L[:, :2]

    # Language cluster centers in embedding space
    centers = []
    for j in range(L2.shape[1]):
        mask = L2[:, j] == 1
        if np.sum(mask) > 0:
            centers.append(embeddings[mask].mean(axis=0))
    centers = np.stack(centers)
    center_mean = centers.mean(axis=0)

    # Directions from center mean to each language center
    diffs = centers - center_mean  # (n_langs, 768)

    # SVD to find orthogonal language directions
    U, S, Vt = np.linalg.svd(diffs, full_matrices=False)
    rank = min(n_components, np.sum(S > S[0] * 1e-10))
    logger.info(f"  Language singular values: {S.tolist()[:4]}, rank={rank}")

    # Top rank directions in embedding space
    lang_dirs = Vt[:rank, :]  # (rank, 768)

    # Projection matrix: P = lang_dirs^T @ lang_dirs
    P = lang_dirs.T @ lang_dirs

    debiased = embeddings - embeddings @ P
    return debiased


def language_center_projection(embeddings, metadata):
    """
    Project each embedding to remove the component toward its language center.
    This is equivalent to centering each language cluster in embedding space.
    """
    languages = sorted(set(m['language'] for m in metadata))
    lang_map = {l: i for i, l in enumerate(languages)}

    # Compute language centers
    centers = {}
    for lang in languages:
        mask = np.array([m.get('language') == lang for m in metadata])
        if np.sum(mask) > 0:
            centers[lang] = embeddings[mask].mean(axis=0)

    # For each embedding, subtract its language center
    debiased = np.copy(embeddings)
    for i, m in enumerate(metadata):
        lang = m.get('language')
        if lang in centers:
            debiased[i] = embeddings[i] - centers[lang]

    return debiased


def compute_purity(labels, metadata, target_field):
    labels = np.array(labels)
    unique_labels = np.unique(labels[labels != -1])
    total_purity = 0
    total_size = 0
    for label in unique_labels:
        mask = labels == label
        cluster_meta = [metadata[i] for i in np.where(mask)[0]]
        values = [m.get(target_field) for m in cluster_meta if m.get(target_field)]
        if not values:
            continue
        counter = Counter(values)
        max_count = max(counter.values())
        total_purity += max_count
        total_size += len(values)
    return total_purity / total_size if total_size > 0 else 0


def leiden_clustering(embeddings, resolution=1.0, k=15):
    from sklearn.neighbors import kneighbors_graph
    import igraph as ig
    import leidenalg

    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normalized = embeddings / norms

    graph = kneighbors_graph(normalized, n_neighbors=k, metric='euclidean',
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
        g,
        leidenalg.RBConfigurationVertexPartition,
        weights='weight',
        resolution_parameter=resolution,
        seed=42
    )
    return np.array(partition.membership), partition.modularity


def evaluate_representation(embeddings, metadata, name,
                            resolutions=[0.5, 1.0, 2.0, 3.0]):
    logger.info(f"Evaluating {name}")
    results = {}
    for res in resolutions:
        labels, modularity = leiden_clustering(embeddings, resolution=res)
        legal_purity = compute_purity(labels, metadata, 'legal_area')
        lang_purity = compute_purity(labels, metadata, 'language')
        chamber_purity = compute_purity(labels, metadata, 'chamber')
        branch_purity = compute_purity(labels, metadata, 'branch')
        n_clusters = len(set(labels[labels != -1]))

        results[f"resolution_{res}"] = {
            'n_clusters': n_clusters,
            'modularity': modularity,
            'legal_area_purity': legal_purity,
            'language_purity': lang_purity,
            'chamber_purity': chamber_purity,
            'branch_purity': branch_purity,
            'ratio': legal_purity / lang_purity if lang_purity > 0 else 0,
        }
        logger.info(f"  res={res}: {n_clusters} clusters, "
                    f"legal={legal_purity:.3f}, lang={lang_purity:.3f}, "
                    f"ratio={legal_purity/lang_purity:.3f}, mod={modularity:.3f}")
    return results


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
    logger.info("=== Language-Debiased Fractal Map Experiment ===")

    baseline_embeddings, metadata = load_baseline()
    logger.info(f"Baseline: {baseline_embeddings.shape[0]} decisions, "
                f"{baseline_embeddings.shape[1]}-dim embeddings")
    logger.info(f"Language distribution: "
                f"{dict(Counter(m['language'] for m in metadata))}")

    # ─── Method 1: PCA language removal (top 2) ───
    logger.info("\n--- Method 1: PCA Language Removal (2 components) ---")
    debiased_pca2 = pca_language_removal(baseline_embeddings, metadata, n_components=2)
    np.save(OUTPUT_DIR / "embeddings_pca2.npy", debiased_pca2)
    results_pca2 = evaluate_representation(debiased_pca2, metadata, "pca2")

    # ─── Method 2: PCA language removal (top 3) ───
    logger.info("\n--- Method 2: PCA Language Removal (3 components) ---")
    debiased_pca3 = pca_language_removal(baseline_embeddings, metadata, n_components=3)
    np.save(OUTPUT_DIR / "embeddings_pca3.npy", debiased_pca3)
    results_pca3 = evaluate_representation(debiased_pca3, metadata, "pca3")

    # ─── Method 3: Language-center projection ───
    logger.info("\n--- Method 3: Language-Center Projection ---")
    debiased_center = language_center_projection(baseline_embeddings, metadata)
    np.save(OUTPUT_DIR / "embeddings_center_projected.npy", debiased_center)
    results_center = evaluate_representation(debiased_center, metadata, "center_projected")

    # ─── Baseline ───
    logger.info("\n--- Baseline (no debiasing) ---")
    results_baseline = evaluate_representation(baseline_embeddings, metadata, "baseline")

    # ─── Summary ───
    all_results = {
        'baseline': results_baseline,
        'pca2': results_pca2,
        'pca3': results_pca3,
        'center_projected': results_center,
    }

    logger.info("\n=== Summary at resolution 1.0 ===")
    for name, res in all_results.items():
        r = res.get('resolution_1.0', {})
        if r:
            logger.info(f"  {name}: legal={r.get('legal_area_purity', 0):.3f}, "
                        f"lang={r.get('language_purity', 0):.3f}, "
                        f"ratio={r.get('ratio', 0):.3f}")

    with open(OUTPUT_DIR / "debiasing_results.json", 'w') as f:
        json.dump(convert(all_results), f, indent=2)

    logger.info(f"\nResults saved to {OUTPUT_DIR}")
    return all_results


if __name__ == "__main__":
    main()
