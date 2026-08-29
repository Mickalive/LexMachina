#!/usr/bin/env python3
"""
Legal Distance Lane v6 - 16-Benchmark Suite Validation

Runs the refined 16-benchmark suite on the best representations:
- center_projected (baseline)
- hybrid_cited_0.3 (best hybrid)
- cited_decisions_tfidf (new candidate)

Benchmarks include:
1. adversarial_language_dominance (adversarial gate)
2. jurist_pairwise_preference (adversarial gate)
3. cross_language_neighbor_quality
4. zero_shot_cross_language_transfer
5. language_specific_representation_quality
6. simulate_cluster_coherence_rating
7. simulate_zoom_task
8. simulate_cross_language_retrieval
9. boilerplate_resistance
10. citation_graph_neighborhood
11. citation_proximity
12. hierarchy_coherence
12. jurivoc_benchmarks
13. legal_area_clustering
14. multilingual_invariance
15. neighbor_relevance
16. scale_benchmarks
"""

import json
import numpy as np
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
from collections import Counter
import sys

# Add evaluation modules
sys.path.insert(0, '/tmp/lex_accepted/evaluation/evaluation')
sys.path.insert(0, '/tmp/lex_accepted/evaluation/evaluation/tests')
sys.path.insert(0, '/tmp/lex_accepted/evaluation/evaluation/data')

from cross_language_benchmarks import (
    cross_language_neighbor_quality,
    zero_shot_cross_language_transfer,
    language_specific_representation_quality,
    adversarial_language_dominance,
)
from jurist_usability import (
    simulate_pairwise_preference,
    simulate_cluster_coherence_rating,
    simulate_zoom_task,
    simulate_cross_language_retrieval,
    prepare_metadata,
)
from boilerplate_resistance import boilerplate_resistance_test
from citation_graph_neighborhood import citation_graph_neighborhood_test
from citation_proximity import citation_proximity_test
from hierarchy_coherence import hierarchy_coherence_test
from jurivoc_benchmarks import jurivoc_benchmarks_test
from legal_area_clustering import legal_area_clustering_test
from multilingual_invariance import multilingual_invariance_test
from neighbor_relevance import neighbor_relevance_test
from scale_benchmarks import scale_benchmarks_test
from stability import stability_test
from zoom_coherence import zoom_coherence_test

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v6/benchmark_suite_validation")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

COMPREHENSIVE_RESULTS_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v6/comprehensive_validation")

# Chamber to branch mapping
CHAMBER_TO_BRANCH = {
    "I. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
    "II. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
    "III. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
    "IV. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
    "I. Zivilrechtliche Abteilung": "zivilrecht",
    "II. Zivilrechtliche Abteilung": "zivilrecht",
    "I. Strafrechtliche Abteilung": "strafrecht",
    "II. Strafrechtliche Abteilung": "strafrecht",
    "II. sozialrechtliche Abteilung": "sozialversicherungsrecht",
    "IIe Cour de droit social": "sozialversicherungsrecht",
    "Ire Cour de droit public": "oeffentliches_recht",
    "IIe Cour de droit public": "oeffentliches_recht",
    "Ire Cour de droit civil": "zivilrecht",
    "IIe Cour de droit civil": "zivilrecht",
    "Ire Cour de droit pénal": "strafrecht",
    "IIe Cour de droit pénal": "strafrecht",
}

def assign_branch(chamber: str) -> str:
    if chamber in CHAMBER_TO_BRANCH:
        return CHAMBER_TO_BRANCH[chamber]
    chamber_lower = chamber.lower()
    if "öffentlich" in chamber_lower or "public" in chamber_lower:
        return "oeffentliches_recht"
    if "zivil" in chamber_lower or "civil" in chamber_lower:
        return "zivilrecht"
    if "straf" in chamber_lower or "pénal" in chamber_lower or "penal" in chamber_lower:
        return "strafrecht"
    if "sozial" in chamber_lower or "social" in chamber_lower:
        return "sozialversicherungsrecht"
    return "unknown"


def load_embeddings_and_metadata(name: str) -> Tuple[np.ndarray, List[Dict]]:
    """Load embeddings and metadata from comprehensive validation results."""
    result_file = COMPREHENSIVE_RESULTS_DIR / f"comprehensive_{name}_results.json"
    with open(result_file, 'r') as f:
        results = json.load(f)
    
    # We need to reconstruct embeddings - for now load from the saved embeddings
    # Actually, the embeddings aren't saved in the results. We need to recompute or load from source.
    # For now, let's load the center_projected embeddings from the fractal-map baseline
    # and the cited_decisions_tfidf from the v6_test_hybrids_adversarial
    
    # Better approach: recompute from the canonical data sources
    pass


def load_canonical_corpus() -> Tuple[np.ndarray, List[Dict]]:
    """Load the 1200-decision expanded corpus with sentence transformer embeddings."""
    from sentence_transformers import SentenceTransformer
    
    # Load corpus
    corpus = []
    with open("/tmp/lex_accepted/evaluation/evaluation/data/bger_expanded_1200.jsonl", 'r', encoding='utf-8') as f:
        for line in f:
            corpus.append(json.loads(line))
    
    metadata = []
    with open("/tmp/lex_accepted/evaluation/evaluation/data/bger_expanded_1200_metadata.jsonl", 'r', encoding='utf-8') as f:
        for line in f:
            metadata.append(json.loads(line))
    
    # Add branch
    for m in metadata:
        if 'branch' not in m:
            m['branch'] = assign_branch(m.get('chamber', ''))
    
    # Compute embeddings
    model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
    texts = [d.get('erwaegungen_text', '')[:2000] for d in corpus]
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)
    
    return embeddings, metadata


def create_center_projected(embeddings: np.ndarray, metadata: List[Dict]) -> np.ndarray:
    """Create center_projected by subtracting language centers."""
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


def load_signals_v2() -> Dict[str, Any]:
    """Load v2 legal signals."""
    signals = {}
    with open("/home/runner/work/LexMachina/LexMachina/legal_distance/results/legal_signals_1000_v2.jsonl", 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            signals[data['decision_id']] = data
    return signals


def build_cited_decisions_tfidf(signals: Dict[str, Any], metadata: List[Dict], max_features: int = 5000) -> np.ndarray:
    """Build TF-IDF on cited decisions."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import TruncatedSVD
    from sklearn.preprocessing import normalize
    
    texts = []
    valid_indices = []
    
    for i, m in enumerate(metadata):
        did = m['decision_id']
        sig = signals.get(did, {})
        cited = sig.get('cited_decisions', [])
        if cited:
            texts.append(" ".join(cited))
            valid_indices.append(i)
        else:
            texts.append("")
    
    if len(valid_indices) < 100:
        return np.zeros((len(metadata), 128))
    
    valid_texts = [texts[i] for i in valid_indices]
    
    vectorizer = TfidfVectorizer(
        max_features=max_features, min_df=2, max_df=0.95,
        ngram_range=(1, 2), sublinear_tf=True, lowercase=True, strip_accents='unicode'
    )
    
    tfidf_matrix = vectorizer.fit_transform(valid_texts)
    n_comp = min(128, tfidf_matrix.shape[1] - 1, len(valid_texts) - 1)
    svd = TruncatedSVD(n_components=n_comp, random_state=42)
    reduced = svd.fit_transform(tfidf_matrix)
    
    norms = np.linalg.norm(reduced, axis=1, keepdims=True)
    norms[norms == 0] = 1
    reduced = reduced / norms
    
    full_emb = np.zeros((len(metadata), n_comp))
    for j, idx in enumerate(valid_indices):
        full_emb[idx] = reduced[j]
    
    return full_emb


def project_to_dim(emb: np.ndarray, target_dim: int) -> np.ndarray:
    from sklearn.decomposition import TruncatedSVD
    from sklearn.preprocessing import normalize
    
    n_samples, n_features = emb.shape
    if n_features <= target_dim:
        if n_features < target_dim:
            padding = np.zeros((n_samples, target_dim - n_features))
            return np.concatenate([emb, padding], axis=1)
        return emb
    if n_samples < target_dim + 1:
        return emb[:, :target_dim]
    svd = TruncatedSVD(n_components=target_dim, random_state=42)
    return svd.fit_transform(emb)


def create_hybrid_representation(legal_emb: np.ndarray, baseline_emb: np.ndarray, alpha: float = 0.5, target_dim: int = 64) -> np.ndarray:
    from sklearn.preprocessing import normalize
    legal_proj = project_to_dim(legal_emb, target_dim)
    baseline_proj = project_to_dim(baseline_emb, target_dim)
    legal_proj = normalize(legal_proj, norm='l2', axis=1)
    baseline_proj = normalize(baseline_proj, norm='l2', axis=1)
    hybrid = alpha * legal_proj + (1 - alpha) * baseline_proj
    return normalize(hybrid, norm='l2', axis=1)


def run_all_benchmarks(embeddings: np.ndarray, metadata: List[Dict], name: str) -> Dict[str, Any]:
    """Run all 16 benchmarks on a representation."""
    logger.info(f"\n{'='*70}")
    logger.info(f"Running 16-benchmark suite for {name}")
    logger.info(f"{'='*70}")
    
    # Prepare metadata for jurist usability
    branches, languages, chambers, valid_indices = prepare_metadata(metadata)
    emb_valid = embeddings[valid_indices]
    meta_valid = [metadata[i] for i in valid_indices]
    
    results = {}
    
    # 1. Adversarial language dominance
    logger.info("1. Adversarial language dominance...")
    results['adversarial_language_dominance'] = adversarial_language_dominance(emb_valid, meta_valid)
    logger.info(f"   mean_dominance: {results['adversarial_language_dominance']['mean_language_dominance']:.4f}, status: {results['adversarial_language_dominance']['status']}")
    
    # 2. Jurist pairwise preference
    logger.info("2. Jurist pairwise preference...")
    results['jurist_pairwise_preference'] = simulate_pairwise_preference(emb_valid, branches, languages)
    logger.info(f"   jurist_would_succeed_rate: {results['jurist_pairwise_preference']['jurist_would_succeed_rate']:.4f}, status: {results['jurist_pairwise_preference']['status']}")
    
    # 3. Cross-language neighbor quality
    logger.info("3. Cross-language neighbor quality...")
    results['cross_language_neighbor_quality'] = cross_language_neighbor_quality(emb_valid, meta_valid)
    logger.info(f"   invariance_gap: {results['cross_language_neighbor_quality'].get('invariance_gap', 'N/A')}")
    
    # 4. Zero-shot cross-language transfer
    logger.info("4. Zero-shot cross-language transfer...")
    results['zero_shot_cross_language_transfer'] = zero_shot_cross_language_transfer(emb_valid, meta_valid)
    logger.info(f"   transfer_gap: {results['zero_shot_cross_language_transfer'].get('transfer_gap', 'N/A')}, status: {results['zero_shot_cross_language_transfer'].get('status', 'N/A')}")
    
    # 5. Language-specific representation quality
    logger.info("5. Language-specific representation quality...")
    results['language_specific_representation_quality'] = language_specific_representation_quality(emb_valid, meta_valid)
    logger.info(f"   mean_nmi: {results['language_specific_representation_quality'].get('mean_nmi', 'N/A')}, status: {results['language_specific_representation_quality'].get('status', 'N/A')}")
    
    # 6. Cluster coherence rating
    logger.info("6. Cluster coherence rating...")
    results['cluster_coherence_rating'] = simulate_cluster_coherence_rating(emb_valid, branches, languages)
    logger.info(f"   mean_branch_purity: {results['cluster_coherence_rating'].get('mean_branch_purity', 'N/A')}, status: {results['cluster_coherence_rating'].get('status', 'N/A')}")
    
    # 7. Zoom task
    logger.info("7. Zoom task...")
    zoom_path = Path("/tmp/lex_accepted/fractal-map/results/fractal_map/hierarchical_map/cluster_assignments.json")
    results['zoom_task'] = simulate_zoom_task(emb_valid, branches, languages, valid_indices, zoom_path)
    logger.info(f"   coarse_purity: {results['zoom_task'].get('coarse_purity', 'N/A')}, status: {results['zoom_task'].get('status', 'N/A')}")
    
    # 8. Cross-language retrieval
    logger.info("8. Cross-language retrieval...")
    results['cross_language_retrieval'] = simulate_cross_language_retrieval(emb_valid, branches, languages)
    logger.info(f"   mean_cross_language_recall_at_k: {results['cross_language_retrieval'].get('mean_cross_language_recall_at_k', 'N/A')}, status: {results['cross_language_retrieval'].get('status', 'N/A')}")
    
    # 9. Boilerplate resistance
    logger.info("9. Boilerplate resistance...")
    try:
        results['boilerplate_resistance'] = boilerplate_resistance_test(embeddings, metadata)
        logger.info(f"   status: {results['boilerplate_resistance'].get('status', 'N/A')}")
    except Exception as e:
        logger.warning(f"   Failed: {e}")
        results['boilerplate_resistance'] = {'error': str(e)}
    
    # 10. Citation graph neighborhood
    logger.info("10. Citation graph neighborhood...")
    try:
        results['citation_graph_neighborhood'] = citation_graph_neighborhood_test(embeddings, metadata)
        logger.info(f"   status: {results['citation_graph_neighborhood'].get('status', 'N/A')}")
    except Exception as e:
        logger.warning(f"   Failed: {e}")
        results['citation_graph_neighborhood'] = {'error': str(e)}
    
    # 11. Citation proximity
    logger.info("11. Citation proximity...")
    try:
        results['citation_proximity'] = citation_proximity_test(embeddings, metadata)
        logger.info(f"   status: {results['citation_proximity'].get('status', 'N/A')}")
    except Exception as e:
        logger.warning(f"   Failed: {e}")
        results['citation_proximity'] = {'error': str(e)}
    
    # 12. Hierarchy coherence
    logger.info("12. Hierarchy coherence...")
    try:
        results['hierarchy_coherence'] = hierarchy_coherence_test(embeddings, metadata)
        logger.info(f"   status: {results['hierarchy_coherence'].get('status', 'N/A')}")
    except Exception as e:
        logger.warning(f"   Failed: {e}")
        results['hierarchy_coherence'] = {'error': str(e)}
    
    # 13. Jurivoc benchmarks
    logger.info("13. Jurivoc benchmarks...")
    try:
        results['jurivoc_benchmarks'] = jurivoc_benchmarks_test(embeddings, metadata)
        logger.info(f"   status: {results['jurivoc_benchmarks'].get('status', 'N/A')}")
    except Exception as e:
        logger.warning(f"   Failed: {e}")
        results['jurivoc_benchmarks'] = {'error': str(e)}
    
    # 14. Legal area clustering
    logger.info("14. Legal area clustering...")
    try:
        results['legal_area_clustering'] = legal_area_clustering_test(embeddings, metadata)
        logger.info(f"   status: {results['legal_area_clustering'].get('status', 'N/A')}")
    except Exception as e:
        logger.warning(f"   Failed: {e}")
        results['legal_area_clustering'] = {'error': str(e)}
    
    # 15. Multilingual invariance
    logger.info("15. Multilingual invariance...")
    try:
        results['multilingual_invariance'] = multilingual_invariance_test(embeddings, metadata)
        logger.info(f"   status: {results['multilingual_invariance'].get('status', 'N/A')}")
    except Exception as e:
        logger.warning(f"   Failed: {e}")
        results['multilingual_invariance'] = {'error': str(e)}
    
    # 16. Neighbor relevance
    logger.info("16. Neighbor relevance...")
    try:
        results['neighbor_relevance'] = neighbor_relevance_test(embeddings, metadata)
        logger.info(f"   status: {results['neighbor_relevance'].get('status', 'N/A')}")
    except Exception as e:
        logger.warning(f"   Failed: {e}")
        results['neighbor_relevance'] = {'error': str(e)}
    
    # Summary
    passed = sum(1 for v in results.values() if isinstance(v, dict) and v.get('status') == 'PASS')
    failed = sum(1 for v in results.values() if isinstance(v, dict) and v.get('status') == 'FAIL')
    errors = sum(1 for v in results.values() if isinstance(v, dict) and 'error' in v)
    total = len(results)
    
    results['summary'] = {
        'total': total,
        'passed': passed,
        'failed': failed,
        'errors': errors,
        'pass_rate': passed / (total - errors) if total > errors else 0,
    }
    
    logger.info(f"\nSummary for {name}: {passed}/{total-errors} passed, {failed} failed, {errors} errors")
    
    return results


def main():
    logger.info("=" * 70)
    logger.info("Legal Distance Lane v6 - 16-Benchmark Suite Validation")
    logger.info("=" * 70)
    
    # 1. Load canonical corpus and create representations
    logger.info("\n1. Loading canonical corpus and creating representations...")
    st_embeddings, metadata = load_canonical_corpus()
    
    logger.info("Creating center_projected...")
    center_projected = create_center_projected(st_embeddings, metadata)
    
    logger.info("Loading signals and building cited_decisions_tfidf...")
    signals = load_signals_v2()
    cited_decisions_tfidf = build_cited_decisions_tfidf(signals, metadata)
    
    logger.info("Creating hybrid_cited_0.3...")
    hybrid_cited_03 = create_hybrid_representation(cited_decisions_tfidf, center_projected, 0.3)
    
    # 2. Run benchmarks on each representation
    representations = {
        'center_projected': center_projected,
        'hybrid_cited_0.3': hybrid_cited_03,
        'cited_decisions_tfidf': cited_decisions_tfidf,
    }
    
    all_results = {}
    
    for name, emb in representations.items():
        results = run_all_benchmarks(emb, metadata, name)
        all_results[name] = results
        
        # Save intermediate
        with open(OUTPUT_DIR / f"benchmark_suite_{name}_results.json", 'w') as f:
            json.dump(results, f, indent=2, default=str)
    
    # 3. Save all results
    with open(OUTPUT_DIR / "benchmark_suite_all_results.json", 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # 4. Summary comparison
    logger.info("\n" + "=" * 100)
    logger.info("16-BENCHMARK SUITE SUMMARY")
    logger.info("=" * 100)
    
    benchmark_names = [
        'adversarial_language_dominance',
        'jurist_pairwise_preference',
        'cross_language_neighbor_quality',
        'zero_shot_cross_language_transfer',
        'language_specific_representation_quality',
        'cluster_coherence_rating',
        'zoom_task',
        'cross_language_retrieval',
        'boilerplate_resistance',
        'citation_graph_neighborhood',
        'citation_proximity',
        'hierarchy_coherence',
        'jurivoc_benchmarks',
        'legal_area_clustering',
        'multilingual_invariance',
        'neighbor_relevance',
    ]
    
    logger.info(f"\n{'Benchmark':<40} {'center_projected':<20} {'hybrid_cited_0.3':<20} {'cited_decisions_tfidf':<20}")
    logger.info("-" * 100)
    
    for bm_name in benchmark_names:
        row = f"{bm_name:<40}"
        for name in ['center_projected', 'hybrid_cited_0.3', 'cited_decisions_tfidf']:
            res = all_results[name].get(bm_name, {})
            if 'error' in res:
                row += f" {'ERROR':<20}"
            elif 'status' in res:
                status = res['status']
                row += f" {status:<20}"
            else:
                row += f" {'N/A':<20}"
        logger.info(row)
    
    # Overall summary
    logger.info("\n" + "=" * 80)
    logger.info("OVERALL PASS RATES")
    logger.info("=" * 80)
    for name in ['center_projected', 'hybrid_cited_0.3', 'cited_decisions_tfidf']:
        summary = all_results[name].get('summary', {})
        logger.info(f"{name}: {summary.get('passed', 0)}/{summary.get('total', 0) - summary.get('errors', 0)} passed ({summary.get('pass_rate', 0):.1%})")
    
    logger.info("\n=== 16-Benchmark Suite Validation Complete ===")
    return all_results


if __name__ == "__main__":
    main()