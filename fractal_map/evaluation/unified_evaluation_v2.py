#!/usr/bin/env python3
"""
Unified evaluation of ALL fractal-map representations including combined methods.

Produces a fair comparison across all tested representations on the same
857 decisions that have extractable reasoning sections.

New in this cycle:
- Concatenation of center-projected + TF-IDF Erwaegungen
- Concatenation of PCA-debiased + TF-IDF Erwaegungen
- TF-IDF center-projected (debiasing in TF-IDF space)
- TF-IDF PCA-debiased (PCA language removal in TF-IDF space)
- TF-IDF bilinear-debiased (feature-weight debiasing)
"""

import json
import re
import numpy as np
from pathlib import Path
from collections import Counter
import logging
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import normalized_mutual_info_score
from sklearn.neighbors import kneighbors_graph

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

BASELINE_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/baseline")
DEBIASING_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/language_debiasing")
COMBINED_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/combined_debiasing_tfidf")
CORPUS_DIR = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/unified_evaluation")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_all_representations():
    with open(BASELINE_DIR / "metadata.json") as f:
        full_metadata = json.load(f)
    baseline_emb = np.load(BASELINE_DIR / "embeddings.npy")
    pca2_emb = np.load(DEBIASING_DIR / "embeddings_pca2.npy")
    center_emb = np.load(DEBIASING_DIR / "embeddings_center_projected.npy")
    return full_metadata, baseline_emb, pca2_emb, center_emb


def extract_erwaegungen(text, language):
    if not text:
        return ""
    text_norm = text.replace('\r\n', '\n').replace('\r', '\n')

    if language == 'de':
        patterns = [r'(?:In\s+Erwägung\s*:)\s*\n', r'(?:Erwägungen\s*:)\s*\n',
                    r'(?:Erwägung\s*:)\s*\n']
    elif language == 'fr':
        patterns = [r'(?:Considérant\s+en\s+droit\s*:)\s*\n',
                    r'(?:Considérant\s*:)\s*\n']
    elif language == 'it':
        patterns = [r'(?:Considerando\s+in\s+diritto\s*:)\s*\n',
                    r'(?:Considerando\s*:)\s*\n']
    else:
        return ""

    start = -1
    for pattern in patterns:
        match = re.search(pattern, text_norm, re.IGNORECASE)
        if match:
            start = match.end()
            break
    if start == -1:
        return ""

    end_patterns = [
        r'\n\s*(?:Dispositiv|Erkenntnis|Ausgang|Dispositif|Dispositivo)\s*:',
        r'\n\s*(?:Sachverhalt|Faits|Fatto)\s*:',
        r'\n\s*(?:In\s+Erwägung|Erwägungen|Considérant|Considerando)\s*:',
    ]
    end = len(text_norm)
    for pattern in end_patterns:
        match = re.search(pattern, text_norm[start:], re.IGNORECASE)
        if match:
            candidate = start + match.start()
            if candidate < end:
                end = candidate
    return text_norm[start:end].strip()


def load_corpus(metadata):
    baseline_ids = set(m['decision_id'] for m in metadata)
    decisions = {}
    slice_path = CORPUS_DIR / "bger_2000plus_slice_1000.jsonl"
    if slice_path.exists():
        with open(slice_path) as f:
            for line in f:
                d = json.loads(line)
                if d['decision_id'] in baseline_ids:
                    decisions[d['decision_id']] = d
    return decisions


def compute_tfidf_erwaegungen(metadata, decisions):
    texts = []
    valid_indices = []
    for i, m in enumerate(metadata):
        did = m['decision_id']
        if did in decisions:
            d = decisions[did]
            text = d.get('full_text', '')
            lang = m.get('language', 'de')
            erwaegungen = extract_erwaegungen(text, lang)
            texts.append(erwaegungen)
            if erwaegungen.strip():
                valid_indices.append(i)
        else:
            texts.append("")

    filtered_texts = [texts[i] for i in valid_indices]
    filtered_meta = [metadata[i] for i in valid_indices]

    vectorizer = TfidfVectorizer(
        max_features=10000, ngram_range=(1, 2), sublinear_tf=True,
        min_df=2, max_df=0.95, strip_accents='unicode'
    )
    tfidf_matrix = vectorizer.fit_transform(filtered_texts)
    n_comp = min(128, tfidf_matrix.shape[1] - 1, len(valid_indices) - 1)
    svd = TruncatedSVD(n_components=n_comp, random_state=42)
    reduced = svd.fit_transform(tfidf_matrix)
    norms = np.linalg.norm(reduced, axis=1, keepdims=True)
    norms[norms == 0] = 1
    reduced = reduced / norms
    return reduced, filtered_meta, valid_indices


def center_project_in_space(embeddings, metadata):
    languages = sorted(set(m['language'] for m in metadata))
    centers = {}
    for lang in languages:
        mask = np.array([m.get('language') == lang for m in metadata])
        if np.sum(mask) > 0:
            centers[lang] = embeddings[mask].mean(axis=0)
    debiased = np.copy(embeddings)
    for i, m in enumerate(metadata):
        lang = m.get('language')
        if lang in centers:
            debiased[i] = embeddings[i] - centers[lang]
    norms = np.linalg.norm(debiased, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return debiased / norms


def pca_language_removal(embeddings, metadata, n_components=2):
    languages = sorted(set(m['language'] for m in metadata))
    lang_map = {l: i for i, l in enumerate(languages)}
    L = np.zeros((len(metadata), len(languages)))
    for i, m in enumerate(metadata):
        lang = m.get('language')
        if lang in lang_map:
            L[i, lang_map[lang]] = 1.0
    L2 = L[:, :2]
    centers = []
    for j in range(L2.shape[1]):
        mask = L2[:, j] == 1
        if np.sum(mask) > 0:
            centers.append(embeddings[mask].mean(axis=0))
    centers = np.stack(centers)
    center_mean = centers.mean(axis=0)
    diffs = centers - center_mean
    U, S, Vt = np.linalg.svd(diffs, full_matrices=False)
    rank = min(n_components, np.sum(S > S[0] * 1e-10))
    lang_dirs = Vt[:rank, :]
    P = lang_dirs.T @ lang_dirs
    debiased = embeddings - embeddings @ P
    norms = np.linalg.norm(debiased, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return debiased / norms


def concatenate(rep1, rep2):
    combined = np.concatenate([rep1, rep2], axis=1)
    norms = np.linalg.norm(combined, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return combined / norms


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
        total_purity += max(counter.values())
        total_size += len(values)
    return total_purity / total_size if total_size > 0 else 0


def leiden_clustering(embeddings, resolution=1.0, k=15):
    import igraph as ig
    import leidenalg

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


def evaluate_representation(embeddings, metadata, name, resolutions):
    results = {}
    for res in resolutions:
        labels, modularity = leiden_clustering(embeddings, resolution=res)
        legal_purity = compute_purity(labels, metadata, 'legal_area')
        lang_purity = compute_purity(labels, metadata, 'language')
        branch_purity = compute_purity(labels, metadata, 'branch')
        chamber_purity = compute_purity(labels, metadata, 'chamber')
        n_clusters = len(set(labels[labels != -1]))

        results[f"resolution_{res}"] = {
            'n_clusters': n_clusters,
            'modularity': modularity,
            'legal_area_purity': legal_purity,
            'language_purity': lang_purity,
            'branch_purity': branch_purity,
            'chamber_purity': chamber_purity,
            'ratio': legal_purity / lang_purity if lang_purity > 0 else 0,
        }
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
    logger.info("=== Unified Fractal-Map Evaluation (Cycle 6) ===")

    full_metadata, baseline_emb, pca2_emb, center_emb = load_all_representations()
    decisions = load_corpus(full_metadata)
    logger.info(f"Corpus: {len(decisions)} decisions loaded")

    # Compute TF-IDF Erwaegungen
    tfidf_erw, tfidf_meta, tfidf_valid_idx = compute_tfidf_erwaegungen(full_metadata, decisions)

    # Align other embeddings to TF-IDF valid indices
    baseline_aligned = baseline_emb[tfidf_valid_idx]
    pca2_aligned = pca2_emb[tfidf_valid_idx]
    center_aligned = center_emb[tfidf_valid_idx]

    resolutions = [0.5, 1.0, 2.0, 3.0]
    all_results = {}

    # 1. Baseline (1000 decisions)
    logger.info("\n--- Baseline (1000 decisions) ---")
    all_results['baseline_1000'] = evaluate_representation(
        baseline_emb, full_metadata, 'baseline_1000', resolutions)

    # 2. Center-projected (1000 decisions)
    logger.info("\n--- Center-projected (1000 decisions) ---")
    all_results['center_projected_1000'] = evaluate_representation(
        center_emb, full_metadata, 'center_projected_1000', resolutions)

    # 3. PCA2 (1000 decisions)
    logger.info("\n--- PCA2-debiased (1000 decisions) ---")
    all_results['pca2_1000'] = evaluate_representation(
        pca2_emb, full_metadata, 'pca2_1000', resolutions)

    # 4. Baseline aligned (857 decisions)
    logger.info("\n--- Baseline aligned (857 decisions) ---")
    all_results['baseline_aligned'] = evaluate_representation(
        baseline_aligned, tfidf_meta, 'baseline_aligned', resolutions)

    # 5. Center-projected aligned (857 decisions)
    logger.info("\n--- Center-projected aligned (857 decisions) ---")
    all_results['center_projected_aligned'] = evaluate_representation(
        center_aligned, tfidf_meta, 'center_projected_aligned', resolutions)

    # 6. TF-IDF Erwaegungen (857 decisions)
    logger.info("\n--- TF-IDF Erwaegungen (857 decisions) ---")
    all_results['tfidf_erwaegungen'] = evaluate_representation(
        tfidf_erw, tfidf_meta, 'tfidf_erwaegungen', resolutions)

    # 7. TF-IDF + center-projection (857 decisions)
    logger.info("\n--- TF-IDF + center-projection (857 decisions) ---")
    tfidf_center = center_project_in_space(tfidf_erw, tfidf_meta)
    all_results['tfidf_center_projected'] = evaluate_representation(
        tfidf_center, tfidf_meta, 'tfidf_center_projected', resolutions)

    # 8. TF-IDF + PCA (857 decisions)
    logger.info("\n--- TF-IDF + PCA language removal (857 decisions) ---")
    tfidf_pca = pca_language_removal(tfidf_erw, tfidf_meta, n_components=2)
    all_results['tfidf_pca2'] = evaluate_representation(
        tfidf_pca, tfidf_meta, 'tfidf_pca2', resolutions)

    # 9. Concat center + TF-IDF (857 decisions)
    logger.info("\n--- Concat center-projected + TF-IDF Erwaegungen (857 decisions) ---")
    concat_center = concatenate(center_aligned, tfidf_erw)
    all_results['concat_center_tfidf'] = evaluate_representation(
        concat_center, tfidf_meta, 'concat_center_tfidf', resolutions)

    # 10. Concat PCA + TF-IDF (857 decisions)
    logger.info("\n--- Concat PCA-debiased + TF-IDF Erwaegungen (857 decisions) ---")
    concat_pca = concatenate(pca2_aligned, tfidf_erw)
    all_results['concat_pca_tfidf'] = evaluate_representation(
        concat_pca, tfidf_meta, 'concat_pca_tfidf', resolutions)

    # Summary
    logger.info("\n" + "=" * 90)
    logger.info("COMPARISON SUMMARY")
    logger.info("=" * 90)

    for target_res in [1.0, 3.0]:
        logger.info(f"\n--- Resolution {target_res} ---")
        logger.info(f"{'Representation':<40} {'Legal':>6} {'Lang':>6} {'Ratio':>6} {'Clust':>6}")
        logger.info("-" * 70)
        for name, res in all_results.items():
            r = res.get(f'resolution_{target_res}', {})
            if r:
                logger.info(f"{name:<40} {r.get('legal_area_purity',0):.3f}  "
                            f"{r.get('language_purity',0):.3f}  "
                            f"{r.get('ratio',0):.3f}  "
                            f"{r.get('n_clusters',0):>4}")

    with open(OUTPUT_DIR / "unified_results.json", 'w') as f:
        json.dump(convert(all_results), f, indent=2)

    logger.info(f"\nResults saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
