#!/usr/bin/env python3
"""
Resolution-Dependent Representation Selector Evaluation

Tests whether a zoom-dependent representation switching strategy outperforms
using a single representation at all zoom levels.

Strategy 1 (Baseline): Use sentence-transformer at all zoom levels
Strategy 2 (Concat): Use concat_center_tfidf at all zoom levels
Strategy 3 (Resolution-Dependent):
  - Zoom 0 (domain): Baseline for cross-language navigation
  - Zoom 1 (subdomain): Center-projected for language-agnostic legal navigation
  - Zoom 2+ (microcluster): Concat for intra-language deep legal navigation

Hypothesis: Resolution-dependent strategy achieves higher average legal purity
across zoom levels while maintaining cross-language capability at domain level.

Product decision: If resolution-dependent outperforms single-representation,
justify the multi-representation architecture for the fractal map product.

Frozen before observation:
- Corpus: 857 BGer decisions (2020-2024) with extractable reasoning sections
- Baseline: sentence-transformer-mpnet-base-v2 (768-dim)
- Center-projected: Language-debiased embeddings
- Concat: center-projected + TF-IDF Erwaegungen (896-dim)
- Clustering: Leiden at resolutions [0.5, 1.0, 2.0, 3.0]
- Success: Resolution-dependent achieves higher average legal purity across zoom levels

Evidence tier: EXPLORATORY
"""

import json
import re
import numpy as np
from pathlib import Path
from collections import Counter
import logging
from datetime import datetime, timezone
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

BASELINE_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/baseline")
DEBIASING_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/language_debiasing")
CORPUS_DIR = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/evaluation")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_metadata_with_branch():
    """Load baseline metadata and enrich with branch from corpus files."""
    with open(BASELINE_DIR / "metadata.json") as f:
        metadata = json.load(f)
    
    id_to_idx = {m['decision_id']: i for i, m in enumerate(metadata)}
    
    # Load branch info from corpus files
    branch_map = {}
    for year_file in sorted(CORPUS_DIR.glob("bger_20*.jsonl")):
        with open(year_file) as f:
            for line in f:
                d = json.loads(line)
                did = d.get('decision_id', '')
                if did in id_to_idx:
                    branch_map[did] = d.get('branch')
    
    # Enrich metadata
    for m in metadata:
        m['branch'] = branch_map.get(m['decision_id'])
    
    return id_to_idx, metadata


def load_representations():
    """Load pre-computed embeddings."""
    baseline_emb = np.load(BASELINE_DIR / "embeddings.npy")
    center_emb = np.load(DEBIASING_DIR / "embeddings_center_projected.npy")
    return baseline_emb, center_emb


def extract_erwaegungen(text, language):
    """Extract Erwaegungen section."""
    if not text:
        return ""
    text_norm = text.replace('\r\n', '\n').replace('\r', '\n')
    
    if language == 'de':
        patterns = [r'(?:In\s+Erwägung\s*:)\s*\n', r'(?:Erwägungen\s*:)\s*\n']
    elif language == 'fr':
        patterns = [r'(?:Considérant\s+en\s+droit\s*:)\s*\n', r'(?:Considérant\s*:)\s*\n']
    elif language == 'it':
        patterns = [r'(?:Considerando\s+in\s+diritto\s*:)\s*\n', r'(?:Considerando\s*:)\s*\n']
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
    ]
    end = len(text_norm)
    for pattern in end_patterns:
        match = re.search(pattern, text_norm[start:], re.IGNORECASE)
        if match:
            candidate = start + match.start()
            if candidate < end:
                end = candidate
    return text_norm[start:end].strip()


def load_corpus_decisions(metadata):
    """Load corpus decisions."""
    baseline_ids = set(m['decision_id'] for m in metadata)
    decisions = {}
    
    for year_file in sorted(CORPUS_DIR.glob("bger_20*.jsonl")):
        with open(year_file) as f:
            for line in f:
                d = json.loads(line)
                if d['decision_id'] in baseline_ids:
                    decisions[d['decision_id']] = d
    
    return decisions


def compute_tfidf_erwaegungen(metadata, decisions):
    """Compute TF-IDF on Erwaegungen."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import TruncatedSVD
    
    texts = []
    valid_indices = []
    
    for i, m in enumerate(metadata):
        did = m['decision_id']
        if did in decisions:
            d = decisions[did]
            text = d.get('full_text', '')
            lang = m.get('language', 'de')
            erwaegungen = extract_erwaegungen(text, lang)
            if erwaegungen.strip():
                texts.append((i, erwaegungen))
    
    if not texts:
        return np.zeros((len(metadata), 128)), []
    
    indices = [t[0] for t in texts]
    only_texts = [t[1] for t in texts]
    
    vectorizer = TfidfVectorizer(
        max_features=10000, ngram_range=(1, 2), sublinear_tf=True,
        min_df=2, max_df=0.95, strip_accents='unicode'
    )
    tfidf_matrix = vectorizer.fit_transform(only_texts)
    n_comp = min(128, tfidf_matrix.shape[1] - 1, len(only_texts) - 1)
    svd = TruncatedSVD(n_components=n_comp, random_state=42)
    reduced = svd.fit_transform(tfidf_matrix)
    norms = np.linalg.norm(reduced, axis=1, keepdims=True)
    norms[norms == 0] = 1
    reduced = reduced / norms
    
    tfidf_full = np.zeros((len(metadata), n_comp))
    for j, i in enumerate(indices):
        tfidf_full[i] = reduced[j]
    
    return tfidf_full, indices


def build_concat(baseline_emb, center_emb, tfidf_full):
    """Build concatenated representation."""
    concat = np.concatenate([center_emb, tfidf_full], axis=1)
    norms = np.linalg.norm(concat, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return concat / norms


def leiden_clustering(embeddings, resolution=1.0, k=15):
    """Leiden clustering."""
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


def compute_purity(labels, metadata, target_field):
    """Compute clustering purity for a specific field."""
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


def compute_cross_language_similarity(embeddings, metadata, n_pairs=200):
    """Compute cross-language similarity for multilingual invariance test."""
    random.seed(42)
    
    # Group by (language, branch)
    groups = {}
    for i, m in enumerate(metadata):
        lang = m.get('language')
        branch = m.get('branch')
        if lang and branch and branch != 'null':
            key = (lang, branch)
            if key not in groups:
                groups[key] = []
            groups[key].append(i)
    
    # Find cross-language same-branch pairs
    cross_lang_pairs = []
    branches = set(b for _, b in groups.keys())
    for branch in branches:
        lang_groups = {l: groups[(l, branch)] for l in ['de', 'fr', 'it'] if (l, branch) in groups}
        if len(lang_groups) >= 2:
            langs = list(lang_groups.keys())
            for i in range(len(langs)):
                for j in range(i+1, len(langs)):
                    n_pairs_per = min(50, len(lang_groups[langs[i]]), len(lang_groups[langs[j]]))
                    for _ in range(n_pairs_per):
                        idx1 = random.choice(lang_groups[langs[i]])
                        idx2 = random.choice(lang_groups[langs[j]])
                        cross_lang_pairs.append((idx1, idx2))
    
    if len(cross_lang_pairs) < 10:
        return 0.0
    
    cross_sims = []
    for idx1, idx2 in cross_lang_pairs[:n_pairs]:
        emb1 = embeddings[idx1]
        emb2 = embeddings[idx2]
        norm1, norm2 = np.linalg.norm(emb1), np.linalg.norm(emb2)
        if norm1 > 0 and norm2 > 0:
            cross_sims.append(float(np.dot(emb1, emb2) / (norm1 * norm2)))
    
    return float(np.mean(cross_sims)) if cross_sims else 0.0


class ResolutionDependentSelector:
    """Resolution-dependent representation selector."""
    
    def __init__(self, baseline_emb, center_emb, concat_emb, metadata):
        self.representations = {
            0: baseline_emb,      # Domain level: baseline for cross-language
            1: center_emb,        # Subdomain level: center-projected for legal navigation
            2: concat_emb,        # Microcluster level: concat for fine-grained legal
        }
        self.metadata = metadata
        
    def get_representation(self, zoom_level):
        """Get representation for a specific zoom level."""
        if zoom_level in self.representations:
            return self.representations[zoom_level]
        # For zoom levels > 2, use concat
        return self.representations[2]


def evaluate_single_representation(embeddings, metadata, name, resolutions):
    """Evaluate a single representation at multiple resolutions."""
    results = {}
    for res in resolutions:
        labels, modularity = leiden_clustering(embeddings, resolution=res)
        legal_purity = compute_purity(labels, metadata, 'legal_area')
        lang_purity = compute_purity(labels, metadata, 'language')
        cross_lang_sim = compute_cross_language_similarity(embeddings, metadata)
        n_clusters = len(set(labels[labels != -1]))
        
        results[f"resolution_{res}"] = {
            'n_clusters': n_clusters,
            'modularity': modularity,
            'legal_area_purity': legal_purity,
            'language_purity': lang_purity,
            'cross_language_similarity': cross_lang_sim,
            'ratio': legal_purity / lang_purity if lang_purity > 0 else 0,
        }
    return results


def evaluate_resolution_dependent(selector, metadata, resolutions):
    """Evaluate resolution-dependent strategy."""
    results = {}
    
    for zoom_level in [0, 1, 2]:
        embeddings = selector.get_representation(zoom_level)
        zoom_results = {}
        
        for res in resolutions:
            labels, modularity = leiden_clustering(embeddings, resolution=res)
            legal_purity = compute_purity(labels, metadata, 'legal_area')
            lang_purity = compute_purity(labels, metadata, 'language')
            cross_lang_sim = compute_cross_language_similarity(embeddings, metadata)
            n_clusters = len(set(labels[labels != -1]))
            
            zoom_results[f"resolution_{res}"] = {
                'n_clusters': n_clusters,
                'modularity': modularity,
                'legal_area_purity': legal_purity,
                'language_purity': lang_purity,
                'cross_language_similarity': cross_lang_sim,
                'ratio': legal_purity / lang_purity if lang_purity > 0 else 0,
            }
        
        results[f"zoom_{zoom_level}"] = zoom_results
    
    return results


def compute_strategy_summary(results, strategy_name):
    """Compute summary statistics for a strategy."""
    # Average legal purity across all resolutions
    legal_purities = []
    lang_purities = []
    ratios = []
    
    for zoom_key, zoom_results in results.items():
        for res_key, res_data in zoom_results.items():
            legal_purities.append(res_data['legal_area_purity'])
            lang_purities.append(res_data['language_purity'])
            ratios.append(res_data['ratio'])
    
    return {
        'strategy': strategy_name,
        'avg_legal_purity': float(np.mean(legal_purities)),
        'avg_language_purity': float(np.mean(lang_purities)),
        'avg_ratio': float(np.mean(ratios)),
        'min_legal_purity': float(np.min(legal_purities)),
        'max_legal_purity': float(np.max(legal_purities)),
    }


def main():
    logger.info("=== Resolution-Dependent Representation Selector Evaluation ===")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    # 1. Load data
    logger.info("\n1. Loading metadata with branch info...")
    id_to_idx, metadata = load_metadata_with_branch()
    baseline_emb, center_emb = load_representations()
    logger.info(f"   Metadata: {len(metadata)} decisions")
    
    # Branch distribution
    branches = Counter(m.get('branch') for m in metadata if m.get('branch'))
    logger.info(f"   Branches: {dict(branches)}")
    
    # 2. Load corpus
    logger.info("\n2. Loading corpus decisions...")
    decisions = load_corpus_decisions(metadata)
    logger.info(f"   Loaded {len(decisions)} decisions")
    
    # 3. Compute TF-IDF
    logger.info("\n3. Computing TF-IDF Erwaegungen...")
    tfidf_full, valid_indices = compute_tfidf_erwaegungen(metadata, decisions)
    logger.info(f"   TF-IDF: {tfidf_full.shape}, {len(valid_indices)} valid")
    
    # 4. Build concat
    logger.info("\n4. Building concatenated representation...")
    concat_emb = build_concat(baseline_emb, center_emb, tfidf_full)
    logger.info(f"   Concat: {concat_emb.shape}")
    
    # 5. Create selector
    logger.info("\n5. Creating resolution-dependent selector...")
    selector = ResolutionDependentSelector(baseline_emb, center_emb, concat_emb, metadata)
    
    # 6. Evaluate strategies
    resolutions = [0.5, 1.0, 2.0, 3.0]
    all_results = {}
    
    logger.info("\n6. Evaluating strategies...")
    
    # Strategy 1: Baseline at all zoom levels
    logger.info("\n   6a. Strategy 1: Baseline (single representation)")
    all_results['baseline'] = evaluate_single_representation(
        baseline_emb, metadata, 'baseline', resolutions
    )
    
    # Strategy 2: Concat at all zoom levels
    logger.info("\n   6b. Strategy 2: Concat (single representation)")
    all_results['concat'] = evaluate_single_representation(
        concat_emb, metadata, 'concat', resolutions
    )
    
    # Strategy 3: Resolution-dependent
    logger.info("\n   6c. Strategy 3: Resolution-dependent selector")
    all_results['resolution_dependent'] = evaluate_resolution_dependent(
        selector, metadata, resolutions
    )
    
    # 7. Compute summaries
    logger.info("\n7. Computing strategy summaries...")
    summaries = {}
    
    # Baseline summary
    summaries['baseline'] = compute_strategy_summary(
        {'all': all_results['baseline']}, 'baseline'
    )
    
    # Concat summary
    summaries['concat'] = compute_strategy_summary(
        {'all': all_results['concat']}, 'concat'
    )
    
    # Resolution-dependent summary (average across zoom levels)
    rd_legal = []
    rd_lang = []
    rd_ratio = []
    for zoom_key in ['zoom_0', 'zoom_1', 'zoom_2']:
        zoom_results = all_results['resolution_dependent'][zoom_key]
        for res_key, res_data in zoom_results.items():
            rd_legal.append(res_data['legal_area_purity'])
            rd_lang.append(res_data['language_purity'])
            rd_ratio.append(res_data['ratio'])
    
    summaries['resolution_dependent'] = {
        'strategy': 'resolution_dependent',
        'avg_legal_purity': float(np.mean(rd_legal)),
        'avg_language_purity': float(np.mean(rd_lang)),
        'avg_ratio': float(np.mean(rd_ratio)),
        'min_legal_purity': float(np.min(rd_legal)),
        'max_legal_purity': float(np.max(rd_legal)),
    }
    
    # 8. Print comparison
    logger.info("\n" + "=" * 80)
    logger.info("STRATEGY COMPARISON SUMMARY")
    logger.info("=" * 80)
    
    logger.info(f"\n{'Strategy':<25} {'Avg Legal':>10} {'Avg Lang':>10} {'Avg Ratio':>10} {'Min Legal':>10} {'Max Legal':>10}")
    logger.info("-" * 80)
    for name, summary in summaries.items():
        logger.info(f"{name:<25} {summary['avg_legal_purity']:>10.3f} {summary['avg_language_purity']:>10.3f} "
                    f"{summary['avg_ratio']:>10.3f} {summary['min_legal_purity']:>10.3f} {summary['max_legal_purity']:>10.3f}")
    
    # 9. Determine winner
    logger.info("\n" + "=" * 80)
    logger.info("WINNER DETERMINATION")
    logger.info("=" * 80)
    
    # Compare average legal purity
    strategies = list(summaries.keys())
    best_legal = max(strategies, key=lambda s: summaries[s]['avg_legal_purity'])
    best_ratio = max(strategies, key=lambda s: summaries[s]['avg_ratio'])
    
    logger.info(f"\nBest average legal purity: {best_legal} ({summaries[best_legal]['avg_legal_purity']:.3f})")
    logger.info(f"Best average ratio: {best_ratio} ({summaries[best_ratio]['avg_ratio']:.3f})")
    
    # Check if resolution-dependent wins
    rd_wins = (best_legal == 'resolution_dependent' or best_ratio == 'resolution_dependent')
    logger.info(f"\nResolution-dependent wins: {rd_wins}")
    
    # 10. Save results
    logger.info("\n8. Saving results...")
    
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
    
    output = {
        "run_id": f"resolution_dependent_selector_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction_version": 1,
        "hypothesis": "Resolution-dependent strategy outperforms single-representation strategies",
        "frozen_sample": f"{len(metadata)} BGer decisions (2020-2024)",
        "frozen_metric": "Legal purity, language purity, ratio across zoom levels",
        "success_rule": "Resolution-dependent achieves higher average legal purity or ratio",
        "strategies_tested": ["baseline", "concat", "resolution_dependent"],
        "detailed_results": all_results,
        "summaries": summaries,
        "winner": {
            "best_legal_purity": best_legal,
            "best_ratio": best_ratio,
            "resolution_dependent_wins": rd_wins,
        },
    }
    
    output_path = OUTPUT_DIR / "resolution_dependent_results.json"
    with open(output_path, 'w') as f:
        json.dump(convert(output), f, indent=2)
    
    logger.info(f"\nResults saved to {output_path}")
    logger.info("\n=== Resolution-dependent selector evaluation complete ===")
    
    return output


if __name__ == "__main__":
    main()
