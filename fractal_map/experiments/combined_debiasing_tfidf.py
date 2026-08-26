#!/usr/bin/env python3
"""
Experiment: Combined Language Debiasing + Reasoning TF-IDF

Hypothesis: Two independent methods improve the legal/language purity ratio:
1. Language-center projection (ratio +20%, but reduces legal purity)
2. Erwaegungen-only TF-IDF (legal purity +10%, but ratio only +9%)

Are these improvements additive? Can we combine the strengths of both?

Methods tested:
1. TF-IDF Erwaegungen + SVD + center-projection (debiased TF-IDF)
2. TF-IDF Erwaegungen with language-specific terms removed
3. Concatenation of center-projected embeddings + TF-IDF Erwaegungen
4. SVD-reduced TF-IDF Erwaegungen with language regularization

Product decision: If combined method achieves ratio >0.5 (legal purity > language purity),
it becomes the default representation for the fractal map.

Evidence tier: EXPLORATORY

Frozen hypothesis, sample, metric, and success rule:
- Hypothesis: Combined debiasing + TF-IDF achieves ratio > 0.5
- Sample: 1000 BGer decisions from bger_2000plus_slice_1000.jsonl
- Metric: legal_area_purity / language_purity at Leiden resolution 1.0
- Success rule: ratio > 0.5 OR legal_purity > 0.40 with ratio > 0.40
"""

import json
import re
import numpy as np
from pathlib import Path
from collections import Counter
import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.neighbors import kneighbors_graph

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

CORPUS_DIR = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
BASELINE_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/baseline")
CENTER_PROJECTED_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/language_debiasing")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/combined_debiasing_tfidf")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_baseline():
    embeddings = np.load(BASELINE_DIR / "embeddings.npy")
    with open(BASELINE_DIR / "metadata.json") as f:
        metadata = json.load(f)
    return embeddings, metadata


def load_center_projected():
    return np.load(CENTER_PROJECTED_DIR / "embeddings_center_projected.npy")


def load_corpus_for_baseline(metadata):
    baseline_ids = set(m['decision_id'] for m in metadata)
    decisions = {}
    slice_path = CORPUS_DIR / "bger_2000plus_slice_1000.jsonl"
    if slice_path.exists():
        with open(slice_path) as f:
            for line in f:
                d = json.loads(line)
                if d['decision_id'] in baseline_ids:
                    decisions[d['decision_id']] = d
    logger.info(f"Loaded {len(decisions)} matching decisions from corpus")
    return decisions


def extract_erwaegungen(text, language):
    if not text:
        return ""
    text_norm = text.replace('\r\n', '\n').replace('\r', '\n')

    if language == 'de':
        patterns = [
            r'(?:In\s+Erwägung\s*:)\s*\n',
            r'(?:Erwägungen\s*:)\s*\n',
            r'(?:Erwägung\s*:)\s*\n',
        ]
    elif language == 'fr':
        patterns = [
            r'(?:Considérant\s+en\s+droit\s*:)\s*\n',
            r'(?:Considérant\s*:)\s*\n',
        ]
    elif language == 'it':
        patterns = [
            r'(?:Considerando\s+in\s+diritto\s*:)\s*\n',
            r'(?:Considerando\s*:)\s*\n',
        ]
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
        r'\n\s*(?:Dispositiv|Erkenntnis|Ausgang)\s*:',
        r'\n\s*(?:Dispositif|Par\s+ces\s+motifs)\s*:',
        r'\n\s*(?:Dispositivo|Per\s+questi\s+motivi)\s*:',
        r'\n\s*(?:Bundesgericht|Tribunal\s+fédéral|Tribunale\s+federale)\s*\n',
    ]
    end = len(text_norm)
    for pattern in end_patterns:
        match = re.search(pattern, text_norm[start:], re.IGNORECASE)
        if match:
            candidate = start + match.start()
            if candidate < end:
                end = candidate

    section_text = text_norm[start:end].strip()
    section_text = re.sub(r'\n\s*\n+', '\n', section_text)
    return section_text


def compute_tfidf_erwaegungen(decisions, metadata):
    """Compute TF-IDF on Erwaegungen sections, return embeddings and aligned metadata."""
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
        min_df=1, max_df=0.95, strip_accents='unicode',
    )
    tfidf_matrix = vectorizer.fit_transform(filtered_texts)
    n_comp = min(128, tfidf_matrix.shape[1] - 1, len(valid_indices) - 1)
    svd = TruncatedSVD(n_components=n_comp, random_state=42)
    reduced = svd.fit_transform(tfidf_matrix)

    norms = np.linalg.norm(reduced, axis=1, keepdims=True)
    norms[norms == 0] = 1
    reduced = reduced / norms

    logger.info(f"TF-IDF Erwaegungen: {len(valid_indices)} decisions, {n_comp} dimensions")
    return reduced, filtered_meta, valid_indices


def center_project_in_tfidf_space(embeddings, metadata):
    """Apply language-center projection in TF-IDF space."""
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
    debiased = debiased / norms

    return debiased


def pca_language_removal_in_tfidf(embeddings, metadata, n_components=2):
    """Remove top-n language-correlated directions from TF-IDF embeddings."""
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
    debiased = debiased / norms
    return debiased


def concatenate_representations(rep1, rep2):
    """Concatenate two representations and L2-normalize."""
    combined = np.concatenate([rep1, rep2], axis=1)
    norms = np.linalg.norm(combined, axis=1, keepdims=True)
    norms[norms == 0] = 1
    combined = combined / norms
    return combined


def bilinear_debiasing_tfidf(embeddings, metadata):
    """
    Language-regularized TF-IDF: downweight features that are highly
    correlated with language identity.
    """
    languages = sorted(set(m['language'] for m in metadata))
    lang_labels = np.array([languages.index(m.get('language', 'de')) for m in metadata])

    # For each feature dimension, compute correlation with language
    n_features = embeddings.shape[1]
    lang_correlation = np.zeros(n_features)
    for dim in range(n_features):
        # ANOVA-like: compute between-class vs total variance
        feature_vals = embeddings[:, dim]
        overall_mean = feature_vals.mean()
        total_var = np.var(feature_vals)

        between_var = 0
        for lang_idx in range(len(languages)):
            mask = lang_labels == lang_idx
            if np.sum(mask) > 0:
                class_mean = feature_vals[mask].mean()
                between_var += np.sum(mask) * (class_mean - overall_mean) ** 2
        between_var /= len(feature_vals)

        if total_var > 0:
            lang_correlation[dim] = between_var / total_var

    # Downweight features highly correlated with language
    # weight = 1 - correlation^2 (soft debiasing)
    weights = 1.0 - lang_correlation ** 2
    weights = np.clip(weights, 0.1, 1.0)  # Don't zero out completely

    debiased = embeddings * weights
    norms = np.linalg.norm(debiased, axis=1, keepdims=True)
    norms[norms == 0] = 1
    debiased = debiased / norms
    return debiased, weights


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


def evaluate_representation(embeddings, metadata, name, resolutions=[0.5, 1.0, 2.0, 3.0]):
    logger.info(f"Evaluating {name} ({len(metadata)} decisions)")
    results = {}
    for res in resolutions:
        labels, modularity = leiden_clustering(embeddings, resolution=res)
        legal_purity = compute_purity(labels, metadata, 'legal_area')
        lang_purity = compute_purity(labels, metadata, 'language')
        n_clusters = len(set(labels[labels != -1]))

        results[f"resolution_{res}"] = {
            'n_clusters': n_clusters,
            'modularity': modularity,
            'legal_area_purity': legal_purity,
            'language_purity': lang_purity,
            'ratio': legal_purity / lang_purity if lang_purity > 0 else 0,
        }
        logger.info(f"  res={res}: {n_clusters} clusters, "
                    f"legal={legal_purity:.3f}, lang={lang_purity:.3f}, "
                    f"ratio={legal_purity/lang_purity:.3f}")
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
    logger.info("=== Combined Debiasing + TF-IDF Experiment ===")

    # Load data
    baseline_embeddings, metadata = load_baseline()
    center_projected = load_center_projected()
    decisions = load_corpus_for_baseline(metadata)
    logger.info(f"Baseline: {baseline_embeddings.shape[0]} decisions, "
                f"{len(decisions)} matched in corpus")

    # Compute TF-IDF Erwaegungen
    tfidf_erw, tfidf_meta, tfidf_valid_idx = compute_tfidf_erwaegungen(decisions, metadata)

    # Align center-projected embeddings to TF-IDF valid indices
    center_projected_aligned = center_projected[tfidf_valid_idx]
    baseline_aligned = baseline_embeddings[tfidf_valid_idx]

    all_results = {}

    # ─── Method 0: Baseline (already computed, load from existing) ───
    logger.info("\n--- Method 0: Baseline (sentence-transformer, full text) ---")
    # Use the aligned baseline for fair comparison
    all_results['baseline_aligned'] = evaluate_representation(baseline_aligned, tfidf_meta, "baseline_aligned")

    # ─── Method 1: Center-projected (already computed, load) ───
    logger.info("\n--- Method 1: Center-projected (sentence-transformer) ---")
    all_results['center_projected'] = evaluate_representation(center_projected_aligned, tfidf_meta, "center_projected")

    # ─── Method 2: TF-IDF Erwaegungen (already computed) ───
    logger.info("\n--- Method 2: TF-IDF Erwaegungen ---")
    all_results['tfidf_erwaegungen'] = evaluate_representation(tfidf_erw, tfidf_meta, "tfidf_erwaegungen")

    # ─── Method 3: TF-IDF Erwaegungen + center-projection in TF-IDF space ───
    logger.info("\n--- Method 3: TF-IDF Erwaegungen + center-projection ---")
    tfidf_center = center_project_in_tfidf_space(tfidf_erw, tfidf_meta)
    all_results['tfidf_center_projected'] = evaluate_representation(tfidf_center, tfidf_meta, "tfidf_center_projected")

    # ─── Method 4: TF-IDF Erwaegungen + PCA language removal ───
    logger.info("\n--- Method 4: TF-IDF Erwaegungen + PCA language removal ---")
    tfidf_pca = pca_language_removal_in_tfidf(tfidf_erw, tfidf_meta, n_components=2)
    all_results['tfidf_pca2'] = evaluate_representation(tfidf_pca, tfidf_meta, "tfidf_pca2")

    # ─── Method 5: Concatenation (center-projected + TF-IDF Erwaegungen) ───
    logger.info("\n--- Method 5: Concatenation (center-projected + TF-IDF Erwaegungen) ---")
    concat = concatenate_representations(center_projected_aligned, tfidf_erw)
    all_results['concat_center_tfidf'] = evaluate_representation(concat, tfidf_meta, "concat_center_tfidf")

    # ─── Method 6: Bilinear debiasing of TF-IDF ───
    logger.info("\n--- Method 6: Bilinear debiasing of TF-IDF Erwaegungen ---")
    tfidf_bilinear, bilinear_weights = bilinear_debiasing_tfidf(tfidf_erw, tfidf_meta)
    all_results['tfidf_bilinear_debiased'] = evaluate_representation(tfidf_bilinear, tfidf_meta, "tfidf_bilinear_debiased")

    # Save bilinear weights for analysis
    np.save(OUTPUT_DIR / "bilinear_weights.npy", bilinear_weights)

    # ─── Method 7: Concatenation (PCA-debiased + TF-IDF Erwaegungen) ───
    logger.info("\n--- Method 7: Concatenation (PCA-debiased + TF-IDF Erwaegungen) ---")
    pca2_embeddings = np.load(CENTER_PROJECTED_DIR / "embeddings_pca2.npy")
    pca2_aligned = pca2_embeddings[tfidf_valid_idx]
    concat_pca = concatenate_representations(pca2_aligned, tfidf_erw)
    all_results['concat_pca_tfidf'] = evaluate_representation(concat_pca, tfidf_meta, "concat_pca_tfidf")

    # ─── Summary ───
    logger.info("\n=== Summary at resolution 1.0 ===")
    for name, res in all_results.items():
        r = res.get('resolution_1.0', {})
        if r:
            logger.info(f"  {name}: legal={r.get('legal_area_purity', 0):.3f}, "
                        f"lang={r.get('language_purity', 0):.3f}, "
                        f"ratio={r.get('ratio', 0):.3f}")

    # Best methods comparison
    logger.info("\n=== Key Comparison ===")
    baseline_ratio = all_results.get('baseline_aligned', {}).get('resolution_1.0', {}).get('ratio', 0)
    for name, res in all_results.items():
        r = res.get('resolution_1.0', {})
        if r:
            ratio = r.get('ratio', 0)
            improvement = (ratio - baseline_ratio) / baseline_ratio * 100 if baseline_ratio > 0 else 0
            logger.info(f"  {name}: ratio={ratio:.3f} ({improvement:+.1f}% vs baseline)")

    with open(OUTPUT_DIR / "combined_results.json", 'w') as f:
        json.dump(convert(all_results), f, indent=2)

    logger.info(f"\nResults saved to {OUTPUT_DIR}")
    return all_results


if __name__ == "__main__":
    main()
