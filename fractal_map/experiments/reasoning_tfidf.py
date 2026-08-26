#!/usr/bin/env python3
"""
Experiment: Reasoning-Only TF-IDF for Fractal Map

Hypothesis: TF-IDF on the full text is dominated by procedural boilerplate
and language-specific vocabulary. By restricting TF-IDF to only the
Erwägungen/Considérant (legal reasoning) section, we exclude procedural
boilerplate and focus on legally meaningful text.

Section markers (trilingual):
- DE: "Sachverhalt:" (facts), "Erwägungen:" or "In Erwägung:" (reasoning),
      "Dispositiv" or "Erkenntnis" (holding)
- FR: "Faits :" (facts), "Considérant en droit :" (reasoning),
      "Dispositif" (holding)
- IT: "Fatto:" (facts), "Considerando in diritto:" (reasoning),
      "Dispositivo" (holding)

Product decision: If Erwägungen-only TF-IDF improves language-agnosticism
while maintaining legal-area discrimination, it becomes a candidate.

Evidence tier: EXPLORATORY
"""

import json
import re
import numpy as np
from pathlib import Path
from collections import Counter
import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD, PCA

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

BASELINE_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/baseline")
CORPUS_DIR = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/reasoning_tfidf")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_baseline():
    with open(BASELINE_DIR / "metadata.json") as f:
        metadata = json.load(f)
    return metadata


def load_corpus_for_baseline(metadata):
    """Load decisions that match baseline metadata from canonical files."""
    baseline_ids = set(m['decision_id'] for m in metadata)
    decisions = {}

    # Load from the 2000plus slice (main baseline source)
    slice_path = CORPUS_DIR / "bger_2000plus_slice_1000.jsonl"
    if slice_path.exists():
        with open(slice_path) as f:
            for line in f:
                d = json.loads(line)
                if d['decision_id'] in baseline_ids:
                    decisions[d['decision_id']] = d

    # Also load from yearly files for any remaining
    for year in [2020, 2021, 2022, 2023, 2024]:
        path = CORPUS_DIR / f"bger_{year}.jsonl"
        if path.exists():
            with open(path) as f:
                for line in f:
                    d = json.loads(line)
                    if d['decision_id'] in baseline_ids and d['decision_id'] not in decisions:
                        decisions[d['decision_id']] = d

    logger.info(f"Loaded {len(decisions)} matching decisions from corpus")
    return decisions


def extract_section(text, language, section='erwaegungen'):
    """
    Extract a specific section from a BGer decision text.

    Sections:
    - 'sachverhalt' / 'faits' / 'fatto': Facts section
    - 'erwaegungen' / 'considerations' / 'considerando': Legal reasoning
    - 'dispositif' / 'dispositivo': Holding/outcome
    """
    if not text:
        return ""

    # Normalize text for matching
    text_norm = text.replace('\r\n', '\n').replace('\r', '\n')

    if language == 'de':
        if section == 'sachverhalt':
            patterns = [
                r'(?:Sachverhalt|Sachverhalt\s*:)\s*\n',
            ]
        elif section == 'erwaegungen':
            patterns = [
                r'(?:In\s+Erwägung\s*:)\s*\n',
                r'(?:Erwägungen\s*:)\s*\n',
                r'(?:Erwägung\s*:)\s*\n',
                r'(?:In\s+facto\s*:)\s*\n',  # rare Latin
            ]
        elif section == 'dispositif':
            patterns = [
                r'(?:Dispositiv\s*:)\s*\n',
                r'(?:Erkenntnis\s*:)\s*\n',
                r'(?:Ausgang\s*:)\s*\n',
            ]
        else:
            return ""
    elif language == 'fr':
        if section == 'sachverhalt':
            patterns = [
                r'(?:Faits\s*:)\s*\n',
                r'(?:En\s+fait\s*:)\s*\n',
            ]
        elif section == 'erwaegungen':
            patterns = [
                r'(?:Considérant\s+en\s+droit\s*:)\s*\n',
                r'(?:Considérant\s*:)\s*\n',
                r'(?:Sur\s+ce\s*:)\s*\n',
            ]
        elif section == 'dispositif':
            patterns = [
                r'(?:Dispositif\s*:)\s*\n',
                r'(?:Par\s+ces\s+motifs\s*:)\s*\n',
            ]
        else:
            return ""
    elif language == 'it':
        if section == 'sachverhalt':
            patterns = [
                r'(?:Fatto\s*:)\s*\n',
                r'(?:In\s+fatto\s*:)\s*\n',
            ]
        elif section == 'erwaegungen':
            patterns = [
                r'(?:Considerando\s+in\s+diritto\s*:)\s*\n',
                r'(?:Considerando\s*:)\s*\n',
            ]
        elif section == 'dispositif':
            patterns = [
                r'(?:Dispositivo\s*:)\s*\n',
                r'(?:Per\s+questi\s+motivi\s*:)\s*\n',
            ]
        else:
            return ""
    else:
        return ""

    # Find the section start
    start = -1
    for pattern in patterns:
        match = re.search(pattern, text_norm, re.IGNORECASE)
        if match:
            start = match.end()
            break

    if start == -1:
        return ""

    # Find the next major section or end of text
    # Common end markers
    end_patterns = [
        r'\n\s*(?:Dispositiv|Erkenntnis|Ausgang)\s*:',
        r'\n\s*(?:Dispositif|Par\s+ces\s+motifs)\s*:',
        r'\n\s*(?:Dispositivo|Per\s+questi\s+motivi)\s*:',
        r'\n\s*(?:Sachverhalt|Faits|Fatto)\s*:',
        r'\n\s*(?:In\s+Erwägung|Erwägungen|Considérant|Considerando)\s*:',
        r'\n\s*(?:Bundesgericht|Tribunal\s+fédéral|Tribunale\s+federale)\s*\n',
        r'\n\s*(?:Urteil\s+vom|Arrêt\s+du|Sentenza\s+del)\s',
    ]

    end = len(text_norm)
    for pattern in end_patterns:
        match = re.search(pattern, text_norm[start:], re.IGNORECASE)
        if match:
            candidate = start + match.start()
            if candidate < end:
                end = candidate

    section_text = text_norm[start:end].strip()

    # Clean up: remove numbered paragraph markers, excess whitespace
    section_text = re.sub(r'\n\s*\n+', '\n', section_text)
    section_text = re.sub(r'^\s*\d+\.\s*\n', '', section_text, flags=re.MULTILINE)

    return section_text


def prepare_texts(decisions, metadata, mode='erwaegungen'):
    """
    Prepare texts based on mode:
    - 'full': full text (baseline comparison)
    - 'erwaegungen': legal reasoning only
    - 'sachverhalt_erwaegungen': facts + reasoning (no procedural header)
    - 'dispositif': holding/outcome only
    """
    texts = []
    valid_indices = []

    for i, m in enumerate(metadata):
        did = m['decision_id']

        # First try the loaded decisions
        if did in decisions:
            d = decisions[did]
            text = d.get('full_text', '')
        else:
            # Try loading from yearly files directly
            text = ""
            for year in [2020, 2021, 2022, 2023, 2024]:
                path = CORPUS_DIR / f"bger_{year}.jsonl"
                if path.exists():
                    with open(path) as f:
                        for line in f:
                            d2 = json.loads(line)
                            if d2['decision_id'] == did:
                                text = d2.get('full_text', '')
                                break
                    if text:
                        break

        if not text:
            texts.append("")
            continue

        lang = m.get('language', 'de')

        if mode == 'full':
            extracted = text
        elif mode == 'erwaegungen':
            extracted = extract_section(text, lang, 'erwaegungen')
        elif mode == 'sachverhalt_erwaegungen':
            facts = extract_section(text, lang, 'sachverhalt')
            reasoning = extract_section(text, lang, 'erwaegungen')
            extracted = (facts + " " + reasoning).strip()
        elif mode == 'dispositif':
            extracted = extract_section(text, lang, 'dispositif')
        else:
            extracted = text

        texts.append(extracted)
        if extracted.strip():
            valid_indices.append(i)

    return texts, valid_indices


def compute_tfidf_embeddings(texts, metadata, valid_indices, max_features=10000):
    """Compute TF-IDF embeddings reduced to a common dimensionality."""
    # Filter to valid texts
    filtered_texts = [texts[i] for i in valid_indices]
    filtered_meta = [metadata[i] for i in valid_indices]

    # TF-IDF
    vectorizer = TfidfVectorizer(
        max_features=max_features,
        ngram_range=(1, 2),
        sublinear_tf=True,
        min_df=1,
        max_df=0.95,
        strip_accents='unicode',
    )

    tfidf_matrix = vectorizer.fit_transform(filtered_texts)
    logger.info(f"  TF-IDF: {tfidf_matrix.shape}")

    # Reduce to 128 dimensions
    n_comp = min(128, tfidf_matrix.shape[1] - 1, len(valid_indices) - 1)
    svd = TruncatedSVD(n_components=n_comp, random_state=42)
    reduced = svd.fit_transform(tfidf_matrix)

    # L2 normalize
    norms = np.linalg.norm(reduced, axis=1, keepdims=True)
    norms[norms == 0] = 1
    reduced = reduced / norms

    return reduced, filtered_meta


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


def evaluate_representation(embeddings, metadata, name,
                            resolutions=[0.5, 1.0, 2.0, 3.0]):
    logger.info(f"Evaluating {name} ({len(metadata)} decisions)")
    results = {}
    for res in resolutions:
        labels, modularity = leiden_clustering(embeddings, resolution=res)
        legal_purity = compute_purity(labels, metadata, 'legal_area')
        lang_purity = compute_purity(labels, metadata, 'language')
        branch_purity = compute_purity(labels, metadata, 'branch')
        n_clusters = len(set(labels[labels != -1]))

        results[f"resolution_{res}"] = {
            'n_clusters': n_clusters,
            'modularity': modularity,
            'legal_area_purity': legal_purity,
            'language_purity': lang_purity,
            'branch_purity': branch_purity,
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
    logger.info("=== Reasoning-Only TF-IDF Experiment ===")

    metadata = load_baseline()
    decisions = load_corpus_for_baseline(metadata)
    logger.info(f"Baseline: {len(metadata)} decisions, "
                f"{len(decisions)} matched in corpus")

    all_results = {}

    for mode in ['full', 'erwaegungen', 'sachverhalt_erwaegungen', 'dispositif']:
        logger.info(f"\n--- Mode: {mode} ---")
        texts, valid_indices = prepare_texts(decisions, metadata, mode=mode)

        n_valid = len(valid_indices)
        n_total = len(texts)
        logger.info(f"Valid texts: {n_valid}/{n_total}")

        if n_valid < 50:
            logger.warning(f"Too few valid texts ({n_valid}) for mode {mode}, skipping")
            continue

        embeddings, filtered_meta = compute_tfidf_embeddings(
            texts, metadata, valid_indices
        )

        results = evaluate_representation(embeddings, filtered_meta, mode)
        all_results[mode] = results

    # Summary
    logger.info("\n=== Summary at resolution 1.0 ===")
    for name, res in all_results.items():
        r = res.get('resolution_1.0', {})
        if r:
            logger.info(f"  {name}: legal={r.get('legal_area_purity', 0):.3f}, "
                        f"lang={r.get('language_purity', 0):.3f}, "
                        f"ratio={r.get('ratio', 0):.3f}")

    with open(OUTPUT_DIR / "reasoning_tfidf_results.json", 'w') as f:
        json.dump(convert(all_results), f, indent=2)

    logger.info(f"\nResults saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
