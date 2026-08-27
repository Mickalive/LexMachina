#!/usr/bin/env python3
"""
Legal Signal Representation Builder for Legal Distance Lane

Builds representations from legally structured signals extracted from BGer decisions:
1. Norms/articles at issue (statutes)
2. Reasoning sections (Erwägungen paragraphs)
3. Citation roles (outgoing/incoming, cited decisions)
4. Legal issues (legal_area, Erwägungen headings)
5. Outcomes (outcome, decision_type)
6. Doctrine citations (preparatory_materials, doctrine_refs)
7. Procedural boilerplate suppression (boilerplate_density weighting)

Tests against the validated debiased_citation_blended baseline (n_pca=1, alpha=0.7).
"""

import json
import numpy as np
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import Counter
import time

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import PCA, TruncatedSVD
from sklearn.preprocessing import normalize
from scipy.sparse import csr_matrix, hstack, vstack

import sys
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

SIGNALS_FILE = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/legal_signals_1000.jsonl")
CORPUS_FILE = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical/bger_2000plus_slice_1000.jsonl")
BASELINE_META = Path("/tmp/lex_accepted/fractal-map/results/fractal_map/baseline/metadata.json")
BASELINE_EMB = Path("/tmp/lex_accepted/fractal-map/results/fractal_map/baseline/embeddings.npy")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results")
REPORT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/reports")


@dataclass
class LegalSignalConfig:
    """Configuration for which legal signals to include in representation."""
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


def load_signals() -> Dict[str, Any]:
    """Load extracted legal signals."""
    signals = {}
    with open(SIGNALS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            signals[data['decision_id']] = data
    logger.info(f"Loaded signals for {len(signals)} decisions")
    return signals


def load_corpus_metadata() -> List[Dict]:
    """Load corpus metadata for alignment."""
    corpus = []
    with open(CORPUS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            corpus.append(json.loads(line))
    return corpus


def build_legal_texts(signals: Dict[str, Any], corpus_meta: List[Dict], config: LegalSignalConfig) -> Tuple[List[str], List[str]]:
    """
    Build text representations from legal signals for TF-IDF vectorization.
    Returns (texts, decision_ids) aligned with corpus order.
    """
    # Create lookup for corpus order
    meta_by_id = {m['decision_id']: m for m in corpus_meta}
    
    texts = []
    decision_ids = []
    
    for meta in corpus_meta:
        did = meta['decision_id']
        sig = signals.get(did, {})
        
        parts = []
        
        # 1. Statutes/norms at issue - with context
        if config.use_statutes and sig.get('statutes'):
            statute_texts = []
            for i, statute in enumerate(sig['statutes']):
                ctx = sig.get('statute_contexts', [])[i] if i < len(sig.get('statute_contexts', [])) else ""
                statute_texts.append(f"{statute} {ctx}")
            parts.append(" ".join(statute_texts))
        
        # 2. Erwägungen (reasoning) paragraphs
        if config.use_erwaegungen and sig.get('erwaegungen_paragraphs'):
            parts.append(" ".join(sig['erwaegungen_paragraphs']))
        
        # 3. Cited decisions
        if config.use_cited_decisions and sig.get('cited_decisions'):
            parts.append(" ".join(sig['cited_decisions']))
        
        # 4. Legal area
        if config.use_legal_area and sig.get('legal_area'):
            parts.append(sig['legal_area'])
        
        # 5. Outcome
        if config.use_outcome and sig.get('outcome'):
            parts.append(sig['outcome'])
        
        # 6. Doctrine references
        if config.use_doctrine_refs and sig.get('doctrine_refs'):
            parts.append(" ".join(sig['doctrine_refs']))
        
        # 7. Erwägungen headings (structural signal)
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
    """Build TF-IDF representation from legal texts with optional boilerplate suppression."""
    
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
    
    # Apply boilerplate suppression weighting
    if config.boilerplate_suppression and boilerplate_weights is not None:
        # Weight rows by (1 - boilerplate_density) to suppress boilerplate-heavy decisions
        weights = 1.0 - boilerplate_weights
        weights = np.clip(weights, 0.1, 1.0)  # Don't zero out completely
        tfidf_matrix = tfidf_matrix.multiply(weights[:, np.newaxis])
    
    # Normalize rows
    tfidf_matrix = normalize(tfidf_matrix, norm='l2', axis=1)
    
    return tfidf_matrix.toarray(), vectorizer


def create_hybrid_representation(
    legal_emb: np.ndarray,
    baseline_emb: np.ndarray,
    alpha: float = 0.5,
    legal_dim: int = 64,
    baseline_dim: int = 64
) -> np.ndarray:
    """
    Create hybrid representation blending legal signals with baseline.
    
    Args:
        legal_emb: Legal signal embeddings (n_samples, legal_dim)
        baseline_emb: Baseline embeddings (n_samples, 768)
        alpha: Weight for legal signals (1-alpha for baseline)
        legal_dim: Target dimension for legal signals
        baseline_dim: Target dimension for baseline (after PCA)
    """
    # Project legal signals to target dimension
    if legal_emb.shape[1] > legal_dim:
        svd = TruncatedSVD(n_components=legal_dim, random_state=42)
        legal_proj = svd.fit_transform(legal_emb)
    else:
        legal_proj = legal_emb
    
    # Project baseline to target dimension
    if baseline_emb.shape[1] > baseline_dim:
        pca = PCA(n_components=baseline_dim, random_state=42)
        baseline_proj = pca.fit_transform(baseline_emb)
    else:
        baseline_proj = baseline_emb
    
    # Normalize both
    legal_proj = normalize(legal_proj, norm='l2', axis=1)
    baseline_proj = normalize(baseline_proj, norm='l2', axis=1)
    
    # Blend
    hybrid = alpha * legal_proj + (1 - alpha) * baseline_proj
    hybrid = normalize(hybrid, norm='l2', axis=1)
    
    return hybrid


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
    """Run full benchmark suite on a representation."""
    
    # Filter embeddings to valid indices (decisions with known branch)
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
    if b["status"] == "FAIL":
        all_passed = False
    
    # 2. Adversarial Falsification
    logger.info("\n[2/14] Adversarial Falsification...")
    b = bench_adversarial(sim_matrix, branches, languages)
    benchmarks["adversarial_falsification"] = b
    logger.info(f"  Result: {b['status']} (lang_dom={b.get('language_dominance_mean', 'N/A')})")
    if b["status"] == "FAIL":
        all_passed = False
    
    # 3. Branch k-NN
    logger.info("\n[3/14] Branch k-NN Classification...")
    b = bench_branch_knn(sim_matrix, branches)
    benchmarks["branch_knn"] = b
    logger.info(f"  Result: {b['status']} (kNN@5={b.get('knn_accuracy@5', 'N/A')})")
    if b["status"] == "FAIL":
        all_passed = False
    
    # 4. Collapse Check
    logger.info("\n[4/14] Collapse Check...")
    b = bench_collapse(sim_matrix)
    benchmarks["collapse_check"] = b
    logger.info(f"  Result: {b['status']} (mean_sim={b.get('mean_similarity', 'N/A')})")
    if b["status"] == "FAIL":
        all_passed = False
    
    # 5. Multilingual Invariance
    logger.info("\n[5/14] Multilingual Invariance...")
    b = bench_multilingual(sim_matrix, branches, languages, metadata, valid_indices)
    benchmarks["multilingual_invariance"] = b
    logger.info(f"  Result: {b['status']} (separation={b.get('separation', 'N/A')})")
    if b["status"] == "FAIL":
        all_passed = False
    
    # 6. Hierarchy Coherence
    logger.info("\n[6/14] Hierarchy Coherence...")
    b = bench_hierarchy_coherence(branches, valid_indices, metadata)
    benchmarks["hierarchy_coherence"] = b
    logger.info(f"  Result: {b['status']} (purity={b.get('best_purity', 'N/A')})")
    if b["status"] == "FAIL":
        all_passed = False
    
    # 7. Citation Proximity
    logger.info("\n[7/14] Citation Proximity...")
    b = bench_citation_proximity(sim_matrix, metadata, valid_indices, citation_pairs)
    benchmarks["citation_proximity"] = b
    logger.info(f"  Result: {b['status']} (AUC={b.get('auc_roc', 'N/A')})")
    if b["status"] == "FAIL":
        all_passed = False
    
    # 8. Citation Graph Neighborhood
    logger.info("\n[8/14] Citation Graph Neighborhood...")
    b = bench_citation_graph_neighborhood(sim_matrix, metadata, valid_indices, citation_pairs_strong)
    benchmarks["citation_graph_neighborhood"] = b
    logger.info(f"  Result: {b['status']} (AUC={b.get('auc_roc', 'N/A')})")
    if b["status"] == "FAIL":
        all_passed = False
    
    # 9. Legal Area Clustering
    logger.info("\n[9/14] Legal Area Clustering...")
    b = bench_legal_area_clustering(branches, legal_areas, sim_matrix)
    benchmarks["legal_area_clustering"] = b
    logger.info(f"  Result: {b['status']} (purity={b.get('overall_purity', 'N/A')})")
    if b["status"] == "FAIL":
        all_passed = False
    
    # 10. Zoom Coherence
    logger.info("\n[10/14] Zoom Coherence...")
    b = bench_zoom_coherence(branches, valid_indices, metadata)
    benchmarks["zoom_coherence"] = b
    logger.info(f"  Result: {b['status']} (improvement={b.get('improvement_pct', 'N/A')}%)")
    if b["status"] == "FAIL":
        all_passed = False
    
    # 11. Temporal Stability
    logger.info("\n[11/14] Temporal Stability...")
    b = bench_temporal_stability(sim_matrix, branches, metadata, valid_indices)
    benchmarks["temporal_stability"] = b
    logger.info(f"  Result: {b['status']} (std={b.get('std_knn_score', 'N/A')})")
    if b["status"] == "FAIL":
        all_passed = False
    
    # 12. Cross-Language Pairs
    logger.info("\n[12/14] Cross-Language Pairs...")
    b = bench_cross_language_pairs(sim_matrix, branches, languages)
    benchmarks["cross_language_pairs"] = b
    logger.info(f"  Result: {b['status']} (separation={b.get('separation', 'N/A')})")
    if b["status"] == "FAIL":
        all_passed = False
    
    # 13. Boilerplate Resistance (Real Corpus)
    logger.info("\n[13/14] Boilerplate Resistance (Real Corpus)...")
    b = bench_boilerplate_real(sim_matrix, corpus, valid_indices, metadata)
    benchmarks["boilerplate_resistance_real_corpus"] = b
    logger.info(f"  Result: {b['status']} (corr={b.get('text_emb_correlation', 'N/A')})")
    if b["status"] == "FAIL":
        all_passed = False
    
    # 14. TF Metadata Human Indexing
    logger.info("\n[14/14] TF Metadata Human Indexing...")
    b = bench_tf_metadata_human_indexing(sim_matrix, branches, valid_indices, metadata)
    benchmarks["tf_metadata_human_indexing"] = b
    logger.info(f"  Result: {b['status']} (recall@5={b.get('recall@5', 'N/A')})")
    if b["status"] == "FAIL":
        all_passed = False
    
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
    logger.info("Legal Distance Lane - Legal Signal Representation Experiments")
    logger.info("=" * 60)
    
    # Load data
    logger.info("Loading legal signals...")
    signals = load_signals()
    
    logger.info("Loading corpus metadata...")
    corpus_meta = load_corpus_metadata()
    
    logger.info("Loading corpus for text benchmarks...")
    corpus = load_corpus()
    
    logger.info("Loading citations...")
    citations = load_corpus_citations()
    
    logger.info("Loading baseline representations...")
    metadata, baseline_768 = load_representations()
    
    # Create baseline representation (validated debiased_citation_blended)
    logger.info("Creating baseline debiased_citation_blended (n_pca=1, alpha=0.7)...")
    baseline_emb, baseline_info = create_debiased_citation_blended(
        baseline_768, metadata, citations,
        n_pca_components=1, alpha=0.7, dims=64
    )
    logger.info(f"Baseline created: {baseline_info}")
    
    # Prepare valid data
    _, branches, languages, _, legal_areas, valid_idx = prepare_valid_data(metadata, baseline_emb)
    
    # Get boilerplate densities for suppression
    boilerplate_densities = []
    for meta in corpus_meta:
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
            "description": "TF-IDF on all legal signals (statutes, erwaegungen, citations, legal_area, outcome, doctrine, headings)",
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
            "name": "hybrid_legal03_baseline07",
            "description": "Hybrid: 30% legal_full_signals + 70% baseline",
            "type": "hybrid",
            "config": LegalSignalConfig(use_statutes=True, use_erwaegungen=True, use_cited_decisions=True,
                                        use_legal_area=True, use_outcome=True, use_doctrine_refs=True,
                                        use_erwaegungen_headings=True),
            "alpha": 0.3,
        },
        {
            "name": "hybrid_legal05_baseline05",
            "description": "Hybrid: 50% legal_full_signals + 50% baseline",
            "type": "hybrid",
            "config": LegalSignalConfig(use_statutes=True, use_erwaegungen=True, use_cited_decisions=True,
                                        use_legal_area=True, use_outcome=True, use_doctrine_refs=True,
                                        use_erwaegungen_headings=True),
            "alpha": 0.5,
        },
        {
            "name": "hybrid_legal07_baseline03",
            "description": "Hybrid: 70% legal_full_signals + 30% baseline",
            "type": "hybrid",
            "config": LegalSignalConfig(use_statutes=True, use_erwaegungen=True, use_cited_decisions=True,
                                        use_legal_area=True, use_outcome=True, use_doctrine_refs=True,
                                        use_erwaegungen_headings=True),
            "alpha": 0.7,
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
        
        run_id = f"legal_dist_{exp['name']}_{int(time.time())}"
        
        if exp["type"] == "baseline":
            emb = baseline_emb
            
        elif exp["type"] == "legal_tfidf":
            config = exp["config"]
            
            # Build texts
            texts, _ = build_legal_texts(signals, corpus_meta, config)
            
            # Get boilerplate weights
            bp_weights = boilerplate_densities if config.boilerplate_suppression else None
            
            # Build TF-IDF
            logger.info(f"Building TF-IDF with config: {config}")
            legal_emb, vectorizer = build_tfidf_representation(texts, config, bp_weights)
            logger.info(f"Legal TF-IDF shape: {legal_emb.shape}")
            
            emb = legal_emb
            
        elif exp["type"] == "hybrid":
            config = exp["config"]
            alpha = exp["alpha"]
            
            # Build legal texts
            texts, _ = build_legal_texts(signals, corpus_meta, config)
            bp_weights = boilerplate_densities if config.boilerplate_suppression else None
            
            # Build TF-IDF
            legal_emb, _ = build_tfidf_representation(texts, config, bp_weights)
            logger.info(f"Legal TF-IDF shape: {legal_emb.shape}")
            
            # Create hybrid
            emb = create_hybrid_representation(
                legal_emb, baseline_768, alpha=alpha, legal_dim=64, baseline_dim=64
            )
            logger.info(f"Hybrid shape: {emb.shape} (alpha={alpha})")
        
        # Run benchmarks
        results = run_full_benchmarks(
            emb, metadata, corpus, citations, valid_idx,
            branches, languages, legal_areas, run_id
        )
        
        all_results[exp["name"]] = {
            "description": exp["description"],
            "type": exp["type"],
            "config": exp.get("config", {}).__dict__ if hasattr(exp.get("config", {}), '__dict__') else exp.get("config", {}),
            "alpha": exp.get("alpha"),
            "results": results
        }
        
        # Save intermediate results
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
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