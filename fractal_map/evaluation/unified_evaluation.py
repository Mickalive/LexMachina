#!/usr/bin/env python3
"""
Unified evaluation of all fractal-map representations.

Produces a fair comparison across:
1. Baseline multilingual sentence embeddings (768-dim)
2. PCA language-debiased (2 components removed)
3. PCA language-debiased (3 components removed)
4. Language-center projected
5. Erwägungen-only TF-IDF (128-dim SVD)
6. Sachverhalt+Erwägungen TF-IDF (128-dim SVD)

All evaluated on the same 857 decisions that have extractable reasoning sections.
"""

import json
import re
import numpy as np
from pathlib import Path
from collections import Counter
import logging
from sklearn.decomposition import TruncatedSVD, PCA
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import normalized_mutual_info_score

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

BASELINE_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/baseline")
DEBIASING_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/language_debiasing")
CORPUS_DIR = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/unified_evaluation")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_all_representations():
    """Load all available representations and align to common decision set."""
    # Baseline metadata and embeddings
    with open(BASELINE_DIR / "metadata.json") as f:
        full_metadata = json.load(f)
    baseline_emb = np.load(BASELINE_DIR / "embeddings.npy")

    # Load debiased embeddings
    pca2_emb = np.load(DEBIASING_DIR / "embeddings_pca2.npy")
    pca3_emb = np.load(DEBIASING_DIR / "embeddings_pca3.npy")
    center_emb = np.load(DEBIASING_DIR / "embeddings_center_projected.npy")

    # Load reasoning TF-IDF results to get the valid indices
    with open(Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/"
                    "reasoning_tfidf/reasoning_tfidf_results.json")) as f:
        tfidf_results = json.load(f)

    return full_metadata, baseline_emb, pca2_emb, pca3_emb, center_emb


def extract_section(text, language, section='erwaegungen'):
    """Extract section from decision text."""
    if not text:
        return ""

    text_norm = text.replace('\r\n', '\n').replace('\r', '\n')

    if language == 'de':
        if section == 'erwaegungen':
            patterns = [r'(?:In\s+Erwägung\s*:)\s*\n', r'(?:Erwägungen\s*:)\s*\n',
                        r'(?:Erwägung\s*:)\s*\n']
        elif section == 'sachverhalt':
            patterns = [r'(?:Sachverhalt|Sachverhalt\s*:)\s*\n']
        else:
            return ""
    elif language == 'fr':
        if section == 'erwaegungen':
            patterns = [r'(?:Considérant\s+en\s+droit\s*:)\s*\n',
                        r'(?:Considérant\s*:)\s*\n']
        elif section == 'sachverhalt':
            patterns = [r'(?:Faits\s*:)\s*\n', r'(?:En\s+fait\s*:)\s*\n']
        else:
            return ""
    elif language == 'it':
        if section == 'erwaegungen':
            patterns = [r'(?:Considerando\s+in\s+diritto\s*:)\s*\n',
                        r'(?:Considerando\s*:)\s*\n']
        elif section == 'sachverhalt':
            patterns = [r'(?:Fatto\s*:)\s*\n', r'(?:In\s+fatto\s*:)\s*\n']
        else:
            return ""
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


def compute_tfidf_representations(metadata, decisions_map):
    """Compute TF-IDF representations for reasoning-only and full text."""
    results = {}

    for mode, section_fn in [
        ('erwaegungen', lambda text, lang: extract_section(text, lang, 'erwaegungen')),
        ('sachverhalt_erwaegungen', lambda text, lang: (
            extract_section(text, lang, 'sachverhalt') + " " +
            extract_section(text, lang, 'erwaegungen')
        ).strip()),
    ]:
        texts = []
        valid_indices = []

        for i, m in enumerate(metadata):
            did = m['decision_id']
            if did not in decisions_map:
                texts.append("")
                continue

            d = decisions_map[did]
            text = d.get('full_text', '')
            lang = m.get('language', 'de')
            extracted = section_fn(text, lang)
            texts.append(extracted)
            if extracted.strip():
                valid_indices.append(i)

        if len(valid_indices) < 100:
            logger.warning(f"Mode {mode}: only {len(valid_indices)} valid texts")
            continue

        filtered_texts = [texts[i] for i in valid_indices]

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

        results[mode] = {
            'embeddings': reduced,
            'indices': valid_indices,
            'n_valid': len(valid_indices),
        }
        logger.info(f"  {mode}: {len(valid_indices)} decisions, {n_comp} components")

    return results


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
        g,
        leidenalg.RBConfigurationVertexPartition,
        weights='weight',
        resolution_parameter=resolution,
        seed=42
    )
    return np.array(partition.membership), partition.modularity


def evaluate_representation(embeddings, metadata, name, resolutions):
    """Evaluate a representation at multiple resolutions."""
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
    logger.info("=== Unified Fractal-Map Evaluation ===")

    # Load all representations
    full_metadata, baseline_emb, pca2_emb, pca3_emb, center_emb = load_all_representations()

    # Load corpus for TF-IDF
    baseline_ids = set(m['decision_id'] for m in full_metadata)
    decisions_map = {}
    slice_path = CORPUS_DIR / "bger_2000plus_slice_1000.jsonl"
    if slice_path.exists():
        with open(slice_path) as f:
            for line in f:
                d = json.loads(line)
                if d['decision_id'] in baseline_ids:
                    decisions_map[d['decision_id']] = d

    logger.info(f"Corpus decisions loaded: {len(decisions_map)}")

    # Compute TF-IDF representations
    logger.info("\n--- Computing TF-IDF representations ---")
    tfidf_reps = compute_tfidf_representations(full_metadata, decisions_map)

    # Find common decision set (decisions present in ALL representations)
    # TF-IDF representations use different subsets, so we need to align
    common_indices = None
    for mode, rep in tfidf_reps.items():
        rep_set = set(rep['indices'])
        if common_indices is None:
            common_indices = rep_set
        else:
            common_indices = common_indices & rep_set

    if common_indices:
        common_indices = sorted(common_indices)
        logger.info(f"Common indices across TF-IDF modes: {len(common_indices)}")
    else:
        # If no overlap between TF-IDF modes, use each independently
        logger.info("No common TF-IDF indices, evaluating each independently")

    # Evaluations
    resolutions = [0.5, 1.0, 2.0, 3.0]
    all_results = {}

    # 1. Baseline (all 1000 decisions)
    logger.info("\n--- Baseline (multilingual sentence embeddings, 1000 decisions) ---")
    all_results['baseline_1000'] = evaluate_representation(
        baseline_emb, full_metadata, 'baseline_1000', resolutions
    )

    # 2. PCA2 debiased (all 1000)
    logger.info("\n--- PCA2 Language-Debiased (1000 decisions) ---")
    all_results['pca2_1000'] = evaluate_representation(
        pca2_emb, full_metadata, 'pca2_1000', resolutions
    )

    # 3. PCA3 debiased (all 1000)
    logger.info("\n--- PCA3 Language-Debiased (1000 decisions) ---")
    all_results['pca3_1000'] = evaluate_representation(
        pca3_emb, full_metadata, 'pca3_1000', resolutions
    )

    # 4. Center projected (all 1000)
    logger.info("\n--- Language-Center Projected (1000 decisions) ---")
    all_results['center_1000'] = evaluate_representation(
        center_emb, full_metadata, 'center_1000', resolutions
    )

    # 5-6. TF-IDF representations (subset with valid texts)
    for mode, rep in tfidf_reps.items():
        indices = rep['indices']
        subset_meta = [full_metadata[i] for i in indices]
        logger.info(f"\n--- TF-IDF {mode} ({len(indices)} decisions) ---")
        all_results[f'tfidf_{mode}'] = evaluate_representation(
            rep['embeddings'], subset_meta, f'tfidf_{mode}', resolutions
        )

    # Summary table
    logger.info("\n" + "=" * 80)
    logger.info("COMPARISON SUMMARY (resolution 1.0)")
    logger.info("=" * 80)
    logger.info(f"{'Representation':<35} {'Legal':>6} {'Lang':>6} {'Ratio':>6} {'Branch':>7} {'Clusters':>8}")
    logger.info("-" * 80)

    for name, res in all_results.items():
        r = res.get('resolution_1.0', {})
        if r:
            logger.info(f"{name:<35} {r.get('legal_area_purity',0):.3f}  "
                        f"{r.get('language_purity',0):.3f}  "
                        f"{r.get('ratio',0):.3f}  "
                        f"{r.get('branch_purity',0):.3f}  "
                        f"{r.get('n_clusters',0):>5}")

    # Save
    with open(OUTPUT_DIR / "unified_results.json", 'w') as f:
        json.dump(convert(all_results), f, indent=2)

    logger.info(f"\nResults saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
