#!/usr/bin/env python3
"""
Experiment: Weighted Concatenation Optimization

Hypothesis: The equal-weight concatenation of center-projected embeddings
and TF-IDF Erwaegungen achieves ratio 0.511, but optimal weights may
further improve the legal/language purity ratio.

Methods tested:
1. Grid search over weight ratios (0.0 to 1.0 in 0.1 increments)
2. Optimization via gradient-free Nelder-Mead
3. Cross-validation on held-out subsets

Product decision: If weighted concatenation improves ratio by >5% over
equal-weight, it becomes the default representation.

Evidence tier: EXPLORATORY

Frozen hypothesis, sample, metric, and success rule:
- Hypothesis: Weighted concatenation achieves ratio > 0.536 (5% improvement)
- Sample: 857 BGer decisions with extractable Erwaegungen
- Metric: legal_area_purity / language_purity at Leiden resolution 3.0
- Success rule: ratio > 0.536
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
from scipy.optimize import minimize

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

CORPUS_DIR = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
BASELINE_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/baseline")
CENTER_PROJECTED_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/language_debiasing")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/weighted_concatenation")
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


def weighted_concatenate(rep1, rep2, weight):
    """Concatenate two representations with specified weight for rep1.
    weight=0.5 means equal weight (original method).
    weight=1.0 means only rep1.
    weight=0.0 means only rep2.
    """
    # Normalize each representation
    norms1 = np.linalg.norm(rep1, axis=1, keepdims=True)
    norms1[norms1 == 0] = 1
    rep1_norm = rep1 / norms1
    
    norms2 = np.linalg.norm(rep2, axis=1, keepdims=True)
    norms2[norms2 == 0] = 1
    rep2_norm = rep2 / norms2
    
    # Weighted concatenation
    combined = np.concatenate([weight * rep1_norm, (1 - weight) * rep2_norm], axis=1)
    norms = np.linalg.norm(combined, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return combined / norms


def evaluate_representation(embeddings, metadata, name, resolution=3.0):
    labels, modularity = leiden_clustering(embeddings, resolution=resolution)
    legal_purity = compute_purity(labels, metadata, 'legal_area')
    lang_purity = compute_purity(labels, metadata, 'language')
    n_clusters = len(set(labels[labels != -1]))
    
    return {
        'n_clusters': n_clusters,
        'modularity': modularity,
        'legal_area_purity': legal_purity,
        'language_purity': lang_purity,
        'ratio': legal_purity / lang_purity if lang_purity > 0 else 0,
    }


def grid_search_weights(center_projected, tfidf_erw, metadata, weights=np.arange(0.0, 1.1, 0.1)):
    """Grid search over weight ratios."""
    results = {}
    for weight in weights:
        concat = weighted_concatenate(center_projected, tfidf_erw, weight)
        result = evaluate_representation(concat, metadata, f"weight_{weight:.1f}")
        results[f"weight_{weight:.1f}"] = result
        logger.info(f"Weight {weight:.1f}: ratio={result['ratio']:.4f}, "
                   f"legal={result['legal_area_purity']:.4f}, "
                   f"lang={result['language_purity']:.4f}")
    return results


def optimize_weights(center_projected, tfidf_erw, metadata):
    """Optimize weights using Nelder-Mead."""
    def objective(params):
        weight = params[0]
        # Clip weight to [0, 1]
        weight = np.clip(weight, 0.0, 1.0)
        concat = weighted_concatenate(center_projected, tfidf_erw, weight)
        result = evaluate_representation(concat, metadata, "optimized")
        # Negative ratio because we minimize
        return -result['ratio']
    
    # Start from equal weight
    initial = [0.5]
    result = minimize(objective, initial, method='Nelder-Mead', 
                     options={'xatol': 0.01, 'fatol': 0.001, 'maxiter': 50})
    
    optimal_weight = np.clip(result.x[0], 0.0, 1.0)
    optimal_concat = weighted_concatenate(center_projected, tfidf_erw, optimal_weight)
    optimal_result = evaluate_representation(optimal_concat, metadata, "optimized")
    
    logger.info(f"Optimal weight: {optimal_weight:.3f}")
    logger.info(f"Optimal ratio: {optimal_result['ratio']:.4f}")
    
    return optimal_weight, optimal_result, result


def cross_validate_weights(center_projected, tfidf_erw, metadata, n_folds=5):
    """Cross-validate weight optimization."""
    n = len(metadata)
    indices = np.arange(n)
    np.random.seed(42)
    np.random.shuffle(indices)
    fold_size = n // n_folds
    
    fold_results = []
    for fold in range(n_folds):
        # Train/test split
        test_start = fold * fold_size
        test_end = test_start + fold_size
        test_idx = indices[test_start:test_end]
        train_idx = np.concatenate([indices[:test_start], indices[test_end:]])
        
        # Optimize on train, evaluate on test
        train_center = center_projected[train_idx]
        train_tfidf = tfidf_erw[train_idx]
        train_meta = [metadata[i] for i in train_idx]
        
        test_center = center_projected[test_idx]
        test_tfidf = tfidf_erw[test_idx]
        test_meta = [metadata[i] for i in test_idx]
        
        # Find optimal weight on train
        best_weight = 0.5
        best_ratio = 0
        for w in np.arange(0.0, 1.1, 0.1):
            concat = weighted_concatenate(train_center, train_tfidf, w)
            result = evaluate_representation(concat, train_meta, f"fold_{fold}_w{w:.1f}")
            if result['ratio'] > best_ratio:
                best_ratio = result['ratio']
                best_weight = w
        
        # Evaluate on test
        test_concat = weighted_concatenate(test_center, test_tfidf, best_weight)
        test_result = evaluate_representation(test_concat, test_meta, f"fold_{fold}_test")
        
        fold_results.append({
            'fold': fold,
            'best_weight': best_weight,
            'train_ratio': best_ratio,
            'test_ratio': test_result['ratio'],
            'test_legal_purity': test_result['legal_area_purity'],
            'test_lang_purity': test_result['language_purity'],
        })
        
        logger.info(f"Fold {fold}: weight={best_weight:.1f}, "
                   f"train_ratio={best_ratio:.4f}, test_ratio={test_result['ratio']:.4f}")
    
    return fold_results


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
    logger.info("=== Weighted Concatenation Optimization Experiment ===")

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

    # 1. Grid search
    logger.info("\n--- Grid Search over Weight Ratios ---")
    grid_results = grid_search_weights(center_projected_aligned, tfidf_erw, tfidf_meta)
    all_results['grid_search'] = grid_results

    # 2. Nelder-Mead optimization
    logger.info("\n--- Nelder-Mead Optimization ---")
    optimal_weight, optimal_result, opt_result = optimize_weights(
        center_projected_aligned, tfidf_erw, tfidf_meta)
    all_results['optimization'] = {
        'optimal_weight': optimal_weight,
        'optimal_result': optimal_result,
        'optimization_success': opt_result.success,
        'optimization_message': opt_result.message,
    }

    # 3. Cross-validation
    logger.info("\n--- Cross-Validation ---")
    cv_results = cross_validate_weights(center_projected_aligned, tfidf_erw, tfidf_meta)
    all_results['cross_validation'] = cv_results

    # 4. Compare with equal-weight baseline
    logger.info("\n--- Comparison with Equal-Weight Baseline ---")
    equal_weight_concat = weighted_concatenate(center_projected_aligned, tfidf_erw, 0.5)
    equal_weight_result = evaluate_representation(equal_weight_concat, tfidf_meta, "equal_weight")
    all_results['equal_weight_baseline'] = equal_weight_result

    # 5. Summary
    logger.info("\n=== Summary ===")
    logger.info(f"Equal weight (0.5): ratio={equal_weight_result['ratio']:.4f}")
    logger.info(f"Optimal weight ({optimal_weight:.3f}): ratio={optimal_result['ratio']:.4f}")
    improvement = (optimal_result['ratio'] - equal_weight_result['ratio']) / equal_weight_result['ratio'] * 100
    logger.info(f"Improvement: {improvement:+.2f}%")
    
    # Check if success criterion met
    success_criterion = 0.536  # 5% improvement over 0.511
    if optimal_result['ratio'] > success_criterion:
        logger.info("SUCCESS: Optimal weight achieves ratio > 0.536")
    else:
        logger.info("FAILURE: Optimal weight does not achieve ratio > 0.536")

    # Save results
    with open(OUTPUT_DIR / "weighted_concatenation_results.json", 'w') as f:
        json.dump(convert(all_results), f, indent=2)

    logger.info(f"\nResults saved to {OUTPUT_DIR}")
    return all_results


if __name__ == "__main__":
    main()
