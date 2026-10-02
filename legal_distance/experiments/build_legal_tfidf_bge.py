#!/usr/bin/env python3
"""
Build legal TF-IDF representations from bge_ corpus signals (published decisions, ~6k scale).
Tests segmented/multi-view legal features against adversarial benchmarks.
"""

import json
import numpy as np
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import Counter
import time
import sys

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD, PCA
from sklearn.preprocessing import normalize
from scipy.sparse import csr_matrix

# Add evaluation harness
sys.path.insert(0, '/tmp/lex_accepted/evaluation/evaluation')
from run_cycle_14 import (
    load_corpus, load_corpus_citations, build_shared_citation_pairs,
    load_representations, prepare_valid_data, normalize_embeddings,
    compute_similarity, create_debiased_citation_blended,
    bench_citation_heritage, bench_adversarial, bench_branch_knn,
    bench_collapse, bench_multilingual, bench_hierarchy_coherence,
    bench_citation_proximity, bench_citation_graph_neighborhood,
    bench_legal_area_clustering, bench_zoom_coherence,
    bench_temporal_stability, bench_cross_language_pairs,
    bench_boilerplate_real, bench_tf_metadata_human_indexing
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

SIGNALS_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/174k_dense_embeddings/legal_signals_144k")
CORPUS_DIR = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/174k_dense_embeddings/legal_tfidf_bge")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

@dataclass
class LegalSignalConfig:
    use_statutes: bool = True
    use_erwaegungen: bool = True
    use_cited_decisions: bool = True
    use_legal_area: bool = True
    use_outcome: bool = True
    use_doctrine_refs: bool = True
    use_erwaegungen_headings: bool = True
    boilerplate_suppression: bool = True
    max_features: int = 5000
    min_df: int = 2
    max_df: float = 0.95
    ngram_range: Tuple[int, int] = (1, 2)

def load_bge_signals() -> Dict[str, Any]:
    """Load legal signals from all bge_ year files."""
    signals = {}
    for year_file in sorted(SIGNALS_DIR.glob("legal_signals_2*.jsonl")):
        with open(year_file, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line)
                signals[data['decision_id']] = data
    logger.info(f"Loaded signals for {len(signals)} decisions from bge_ corpus")
    return signals

def load_bge_corpus() -> List[Dict]:
    """Load bge_ corpus decisions for metadata alignment."""
    corpus = []
    for year_file in sorted(CORPUS_DIR.glob("bge_2*.jsonl")):
        with open(year_file, 'r', encoding='utf-8') as f:
            for line in f:
                corpus.append(json.loads(line))
    logger.info(f"Loaded {len(corpus)} decisions from bge_ corpus")
    return corpus

def build_legal_texts(signals: Dict[str, Any], corpus_meta: List[Dict], config: LegalSignalConfig) -> Tuple[List[str], List[str]]:
    """Build text representations from legal signals for TF-IDF vectorization."""
    texts = []
    decision_ids = []
    
    for meta in corpus_meta:
        did = meta['decision_id']
        sig = signals.get(did, {})
        
        parts = []
        
        if config.use_statutes and sig.get('statutes'):
            statute_texts = []
            for i, statute in enumerate(sig['statutes']):
                ctx = sig.get('statute_contexts', [])[i] if i < len(sig.get('statute_contexts', [])) else ""
                statute_texts.append(f"{statute} {ctx}")
            parts.append(" ".join(statute_texts))
        
        if config.use_erwaegungen and sig.get('erwaegungen_paragraphs'):
            parts.append(" ".join(sig['erwaegungen_paragraphs']))
        
        if config.use_cited_decisions and sig.get('cited_decisions'):
            parts.append(" ".join(sig['cited_decisions']))
        
        if config.use_legal_area and sig.get('legal_area'):
            parts.append(sig['legal_area'])
        
        if config.use_outcome and sig.get('outcome'):
            parts.append(sig['outcome'])
        
        if config.use_doctrine_refs and sig.get('doctrine_refs'):
            parts.append(" ".join(sig['doctrine_refs']))
        
        if config.use_erwaegungen_headings and sig.get('erwaegungen_headings'):
            parts.append(" ".join(sig['erwaegungen_headings']))
        
        combined = " ".join(parts)
        texts.append(combined)
        decision_ids.append(did)
    
    return texts, decision_ids

def build_tfidf_representation(
    texts: List[str],
    config: LegalSignalConfig,
    boilerplate_weights: Optional[np.ndarray] = None
) -> Tuple[np.ndarray, TfidfVectorizer]:
    vectorizer = TfidfVectorizer(
        max_features=config.max_features,
        min_df=config.min_df,
        max_df=config.max_df,
        ngram_range=config.ngram_range,
        sublinear_tf=True,
        lowercase=True,
        strip_accents='unicode',
    )
    
    tfidf_matrix = vectorizer.fit_transform(texts)
    
    if config.boilerplate_suppression and boilerplate_weights is not None:
        weights = 1.0 - boilerplate_weights
        weights = np.clip(weights, 0.1, 1.0)
        tfidf_matrix = tfidf_matrix.multiply(weights[:, np.newaxis])
    
    tfidf_matrix = normalize(tfidf_matrix, norm='l2', axis=1)
    return tfidf_matrix.toarray(), vectorizer

def run_full_benchmarks(
    emb: np.ndarray,
    metadata: List[Dict],
    corpus: List[Dict],
    citations: Dict[str, List[str]],
    valid_indices: List[int],
    branches: np.ndarray,
    languages: np.ndarray,
    legal_areas: np.ndarray,
    run_id: str
) -> Dict[str, Any]:
    emb_valid = emb[valid_indices]
    emb_norm = normalize_embeddings(emb_valid)
    sim_matrix = compute_similarity(emb_norm)
    
    citation_pairs = build_shared_citation_pairs(citations, min_shared=1)
    citation_pairs_strong = build_shared_citation_pairs(citations, min_shared=2)
    
    benchmarks = {}
    all_passed = True
    
    logger.info(f"\n{'='*70}")
    logger.info(f"RUNNING FULL BENCHMARK SUITE: {run_id}")
    logger.info(f"{'='*70}")
    
    # 1. Citation Heritage
    logger.info("\n[1/14] Citation Heritage...")
    b = bench_citation_heritage(sim_matrix, metadata, valid_indices, citation_pairs)
    benchmarks["citation_heritage"] = b
    logger.info(f"  Result: {b['status']} (AUC={b.get('auc_roc', 'N/A')})")
    if b["status"] == "FAIL": all_passed = False
    
    # 2. Adversarial Falsification
    logger.info("\n[2/14] Adversarial Falsification...")
    b = bench_adversarial(sim_matrix, branches, languages)
    benchmarks["adversarial_falsification"] = b
    logger.info(f"  Result: {b['status']} (lang_dom={b.get('language_dominance_mean', 'N/A')})")
    if b["status"] == "FAIL": all_passed = False
    
    # 3. Branch k-NN
    logger.info("\n[3/14] Branch k-NN Classification...")
    b = bench_branch_knn(sim_matrix, branches)
    benchmarks["branch_knn"] = b
    logger.info(f"  Result: {b['status']} (kNN@5={b.get('knn_accuracy@5', 'N/A')})")
    if b["status"] == "FAIL": all_passed = False
    
    # 4. Collapse Check
    logger.info("\n[4/14] Collapse Check...")
    b = bench_collapse(sim_matrix)
    benchmarks["collapse_check"] = b
    logger.info(f"  Result: {b['status']} (mean_sim={b.get('mean_similarity', 'N/A')})")
    if b["status"] == "FAIL": all_passed = False
    
    # 5. Multilingual Invariance
    logger.info("\n[5/14] Multilingual Invariance...")
    b = bench_multilingual(sim_matrix, branches, languages, metadata, valid_indices)
    benchmarks["multilingual_invariance"] = b
    logger.info(f"  Result: {b['status']} (separation={b.get('separation', 'N/A')})")
    if b["status"] == "FAIL": all_passed = False
    
    # 6. Hierarchy Coherence
    logger.info("\n[6/14] Hierarchy Coherence...")
    b = bench_hierarchy_coherence(branches, valid_indices, metadata)
    benchmarks["hierarchy_coherence"] = b
    logger.info(f"  Result: {b['status']} (purity={b.get('best_purity', 'N/A')})")
    if b["status"] == "FAIL": all_passed = False
    
    # 7. Citation Proximity
    logger.info("\n[7/14] Citation Proximity...")
    b = bench_citation_proximity(sim_matrix, metadata, valid_indices, citation_pairs)
    benchmarks["citation_proximity"] = b
    logger.info(f"  Result: {b['status']} (AUC={b.get('auc_roc', 'N/A')})")
    if b["status"] == "FAIL": all_passed = False
    
    # 8. Citation Graph Neighborhood
    logger.info("\n[8/14] Citation Graph Neighborhood...")
    b = bench_citation_graph_neighborhood(sim_matrix, metadata, valid_indices, citation_pairs_strong)
    benchmarks["citation_graph_neighborhood"] = b
    logger.info(f"  Result: {b['status']} (AUC={b.get('auc_roc', 'N/A')})")
    if b["status"] == "FAIL": all_passed = False
    
    # 9. Legal Area Clustering
    logger.info("\n[9/14] Legal Area Clustering...")
    b = bench_legal_area_clustering(branches, legal_areas, sim_matrix)
    benchmarks["legal_area_clustering"] = b
    logger.info(f"  Result: {b['status']} (purity={b.get('overall_purity', 'N/A')})")
    if b["status"] == "FAIL": all_passed = False
    
    # 10. Zoom Coherence
    logger.info("\n[10/14] Zoom Coherence...")
    b = bench_zoom_coherence(branches, valid_indices, metadata)
    benchmarks["zoom_coherence"] = b
    logger.info(f"  Result: {b['status']} (improvement={b.get('improvement_pct', 'N/A')}%)")
    if b["status"] == "FAIL": all_passed = False
    
    # 11. Temporal Stability
    logger.info("\n[11/14] Temporal Stability...")
    b = bench_temporal_stability(sim_matrix, branches, metadata, valid_indices)
    benchmarks["temporal_stability"] = b
    logger.info(f"  Result: {b['status']} (std={b.get('std_knn_score', 'N/A')})")
    if b["status"] == "FAIL": all_passed = False
    
    # 12. Cross-Language Pairs
    logger.info("\n[12/14] Cross-Language Pairs...")
    b = bench_cross_language_pairs(sim_matrix, branches, languages)
    benchmarks["cross_language_pairs"] = b
    logger.info(f"  Result: {b['status']} (separation={b.get('separation', 'N/A')})")
    if b["status"] == "FAIL": all_passed = False
    
    # 13. Boilerplate Resistance (Real Corpus)
    logger.info("\n[13/14] Boilerplate Resistance (Real Corpus)...")
    b = bench_boilerplate_real(sim_matrix, corpus, valid_indices, metadata)
    benchmarks["boilerplate_resistance_real_corpus"] = b
    logger.info(f"  Result: {b['status']} (corr={b.get('text_emb_correlation', 'N/A')})")
    if b["status"] == "FAIL": all_passed = False
    
    # 14. TF Metadata Human Indexing
    logger.info("\n[14/14] TF Metadata Human Indexing...")
    b = bench_tf_metadata_human_indexing(sim_matrix, branches, valid_indices, metadata)
    benchmarks["tf_metadata_human_indexing"] = b
    logger.info(f"  Result: {b['status']} (recall@5={b.get('recall@5', 'N/A')})")
    if b["status"] == "FAIL": all_passed = False
    
    passed_count = sum(1 for b in benchmarks.values() if b.get('status') == 'PASS')
    total_count = len(benchmarks)
    
    logger.info(f"\n{'='*70}")
    logger.info(f"SUMMARY: {passed_count}/{total_count} benchmarks PASSED")
    logger.info(f"{'='*70}")
    
    return {
        "run_id": run_id,
        "benchmarks": benchmarks,
        "summary": {
            "total_benchmarks": total_count,
            "passed": passed_count,
            "failed": total_count - passed_count,
            "all_passed": all_passed
        }
    }

def main():
    logger.info("=" * 60)
    logger.info("Legal TF-IDF from bge_ Corpus - Legal Distance Lane")
    logger.info("=" * 60)
    
    # Load data
    logger.info("Loading legal signals from bge_ corpus...")
    signals = load_bge_signals()
    
    logger.info("Loading bge_ corpus metadata...")
    corpus_meta = load_bge_corpus()
    
    logger.info("Loading corpus for text benchmarks...")
    corpus = load_corpus()
    
    logger.info("Loading citations...")
    citations = load_corpus_citations()
    
    logger.info("Loading baseline representations...")
    metadata, baseline_768 = load_representations()
    
    # Create baseline representation
    logger.info("Creating baseline debiased_citation_blended (n_pca=1, alpha=0.7)...")
    baseline_emb, baseline_info = create_debiased_citation_blended(
        baseline_768, metadata, citations,
        n_pca_components=1, alpha=0.7, dims=64
    )
    logger.info(f"Baseline created: {baseline_info}")
    
    # Prepare valid data
    _, branches, languages, _, legal_areas, valid_idx = prepare_valid_data(metadata, baseline_emb)
    
    # Filter corpus_meta to only decisions with signals
    corpus_meta_filtered = [m for m in corpus_meta if m['decision_id'] in signals]
    logger.info(f"Decisions with signals: {len(corpus_meta_filtered)}")
    
    # Get boilerplate densities for suppression
    boilerplate_densities = []
    for meta in corpus_meta_filtered:
        did = meta['decision_id']
        sig = signals.get(did, {})
        boilerplate_densities.append(sig.get('boilerplate_density', 0.0))
    boilerplate_densities = np.array(boilerplate_densities)
    
    # Define experiment configurations
    experiments = [
        {
            "name": "baseline_debiased_citation_blended",
            "description": "Validated baseline: debiased_citation_blended (n_pca=1, alpha=0.7)",
            "type": "baseline",
        },
        {
            "name": "legal_statutes_only",
            "description": "TF-IDF on statutes/norms at issue only",
            "type": "legal_tfidf",
            "config": LegalSignalConfig(use_statutes=True, use_erwaegungen=False, use_cited_decisions=False,
                                        use_legal_area=False, use_outcome=False, use_doctrine_refs=False,
                                        use_erwaegungen_headings=False),
        },
        {
            "name": "legal_erwaegungen_only",
            "description": "TF-IDF on Erwägungen (reasoning) paragraphs only",
            "type": "legal_tfidf",
            "config": LegalSignalConfig(use_statutes=False, use_erwaegungen=True, use_cited_decisions=False,
                                        use_legal_area=False, use_outcome=False, use_doctrine_refs=False,
                                        use_erwaegungen_headings=False),
        },
        {
            "name": "legal_cited_decisions_only",
            "description": "TF-IDF on cited decisions only",
            "type": "legal_tfidf",
            "config": LegalSignalConfig(use_statutes=False, use_erwaegungen=False, use_cited_decisions=True,
                                        use_legal_area=False, use_outcome=False, use_doctrine_refs=False,
                                        use_erwaegungen_headings=False),
        },
        {
            "name": "legal_erwaegungen_statutes",
            "description": "TF-IDF on Erwägungen + statutes",
            "type": "legal_tfidf",
            "config": LegalSignalConfig(use_statutes=True, use_erwaegungen=True, use_cited_decisions=False,
                                        use_legal_area=False, use_outcome=False, use_doctrine_refs=False,
                                        use_erwaegungen_headings=False),
        },
        {
            "name": "legal_full_signals",
            "description": "TF-IDF on all legal signals",
            "type": "legal_tfidf",
            "config": LegalSignalConfig(use_statutes=True, use_erwaegungen=True, use_cited_decisions=True,
                                        use_legal_area=True, use_outcome=True, use_doctrine_refs=True,
                                        use_erwaegungen_headings=True),
        },
        {
            "name": "legal_full_signals_noboilerplate",
            "description": "TF-IDF on all legal signals WITHOUT boilerplate suppression",
            "type": "legal_tfidf",
            "config": LegalSignalConfig(use_statutes=True, use_erwaegungen=True, use_cited_decisions=True,
                                        use_legal_area=True, use_outcome=True, use_doctrine_refs=True,
                                        use_erwaegungen_headings=True, boilerplate_suppression=False),
        },
        {
            "name": "legal_statutes_erwaegungen_citations",
            "description": "TF-IDF on statutes + erwaegungen + cited_decisions (core legal signals)",
            "type": "legal_tfidf",
            "config": LegalSignalConfig(use_statutes=True, use_erwaegungen=True, use_cited_decisions=True,
                                        use_legal_area=False, use_outcome=False, use_doctrine_refs=False,
                                        use_erwaegungen_headings=False),
        },
        {
            "name": "legal_issues_outcomes",
            "description": "TF-IDF on legal_area + outcome + erwaegungen_headings (issue/outcome signals)",
            "type": "legal_tfidf",
            "config": LegalSignalConfig(use_statutes=False, use_erwaegungen=False, use_cited_decisions=False,
                                        use_legal_area=True, use_outcome=True, use_doctrine_refs=False,
                                        use_erwaegungen_headings=True),
        },
    ]
    
    all_results = {}
    
    for exp in experiments:
        logger.info(f"\n{'='*60}")
        logger.info(f"EXPERIMENT: {exp['name']}")
        logger.info(f"DESCRIPTION: {exp['description']}")
        logger.info(f"{'='*60}")
        
        run_id = f"legal_tfidf_bge_{exp['name']}_{int(time.time())}"
        
        if exp["type"] == "baseline":
            emb = baseline_emb
            
        elif exp["type"] == "legal_tfidf":
            config = exp["config"]
            
            # Build texts
            texts, _ = build_legal_texts(signals, corpus_meta_filtered, config)
            
            # Get boilerplate weights
            bp_weights = boilerplate_densities if config.boilerplate_suppression else None
            
            # Build TF-IDF
            logger.info(f"Building TF-IDF with config: {config}")
            legal_emb, vectorizer = build_tfidf_representation(texts, config, bp_weights)
            logger.info(f"Legal TF-IDF shape: {legal_emb.shape}")
            
            emb = legal_emb
        
        # Run benchmarks
        results = run_full_benchmarks(
            emb, metadata, corpus, citations, valid_idx,
            branches, languages, legal_areas, run_id
        )
        
        all_results[exp["name"]] = {
            "description": exp["description"],
            "type": exp["type"],
            "config": exp.get("config", {}).__dict__ if hasattr(exp.get("config", {}), '__dict__') else exp.get("config", {}),
            "results": results
        }
        
        # Save intermediate results
        with open(OUTPUT_DIR / f"experiment_{exp['name']}_results.json", 'w') as f:
            json.dump(all_results[exp["name"]], f, indent=2, default=str)
    
    # Save all results
    with open(OUTPUT_DIR / "all_experiments_results.json", 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Print summary comparison
    logger.info("\n" + "=" * 80)
    logger.info("EXPERIMENT SUMMARY COMPARISON")
    logger.info("=" * 80)
    
    baseline_results = all_results["baseline_debiased_citation_blended"]["results"]
    
    for exp_name, exp_data in all_results.items():
        if exp_name == "baseline_debiased_citation_blended":
            continue
        
        res = exp_data["results"]
        passed = res["summary"]["passed"]
        total = res["summary"]["total_benchmarks"]
        all_pass = res["summary"]["all_passed"]
        
        # Compare key metrics with baseline
        baseline_auc = baseline_results["benchmarks"]["citation_heritage"].get("auc_roc", 0)
        exp_auc = res["benchmarks"]["citation_heritage"].get("auc_roc", 0)
        auc_diff = exp_auc - baseline_auc
        
        baseline_lang = baseline_results["benchmarks"]["adversarial_falsification"].get("language_dominance_mean", 0)
        exp_lang = res["benchmarks"]["adversarial_falsification"].get("language_dominance_mean", 0)
        lang_diff = exp_lang - baseline_lang
        
        baseline_branch = baseline_results["benchmarks"]["branch_knn"].get("knn_accuracy@5", 0)
        exp_branch = res["benchmarks"]["branch_knn"].get("knn_accuracy@5", 0)
        branch_diff = exp_branch - baseline_branch
        
        logger.info(f"{exp_name}: {passed}/{total} PASS {'✓' if all_pass else '✗'} | "
                    f"Citation AUC: {exp_auc:.4f} ({auc_diff:+.4f}) | "
                    f"Lang dom: {exp_lang:.4f} ({lang_diff:+.4f}) | "
                    f"Branch kNN@5: {exp_branch:.4f} ({branch_diff:+.4f})")
    
    logger.info("\nAll experiments complete!")
    return all_results

if __name__ == "__main__":
    main()
