#!/usr/bin/env python3
"""
Legal Distance Lane v5 - Scale Test on Full Corpus

Validates the best modes from v4 signal ablation on the full corpus (1200 decisions):
- legal_cited_decisions_only
- hybrid_erwaegungen_07 (alpha=0.7)
- sachverhalt_tfidf
- norm_embeddings
- erwaegungen+citations
- legal_issues_outcomes
- debiased_citation_blended (baseline)

Uses the validated fractal-map harness (hierarchical Leiden + zoom coherence).
"""

import json
import numpy as np
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import Counter, defaultdict

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD, PCA
from sklearn.preprocessing import normalize
from scipy.sparse import csr_matrix

import sys
sys.path.insert(0, '/tmp/lex_accepted/fractal-map/fractal_map/hierarchical')
sys.path.insert(0, '/tmp/lex_accepted/evaluation/evaluation')

from hierarchical_leiden import (
    load_metadata_with_branch, load_representations, 
    load_corpus_decisions, leiden_clustering,
    compute_branch_purity,
)
from hierarchical_zoom_validation import hierarchical_leiden, compute_branch_purity_per_cluster

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
SIGNALS_FILE = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/legal_signals_full.jsonl")
FULL_CORPUS_FILE = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/bger_full_corpus.jsonl")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/scale_test")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Load multilingual sentence transformer for embeddings
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDING_MODEL = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
    logger.info("Loaded sentence transformer for embeddings")
except ImportError:
    EMBEDDING_MODEL = None
    logger.warning("sentence_transformers not available, will use TF-IDF only for norms")

@dataclass
class SignalConfig:
    use_sachverhalt: bool = False
    use_erwaegungen: bool = False
    use_norm_embeddings: bool = False
    use_citation_weights: bool = False
    use_cited_decisions_tfidf: bool = False
    use_doctrine_refs: bool = False
    use_outcome: bool = False
    use_legal_area: bool = False
    use_erwaegungen_headings: bool = False
    max_features: int = 5000
    min_df: int = 2
    max_df: float = 0.95
    ngram_range: Tuple[int, int] = (1, 2)

def load_signals() -> Dict[str, Any]:
    signals = {}
    with open(SIGNALS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            signals[data['decision_id']] = data
    logger.info(f"Loaded signals for {len(signals)} decisions")
    return signals

def load_full_corpus() -> List[Dict]:
    corpus = []
    with open(FULL_CORPUS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            corpus.append(json.loads(line))
    logger.info(f"Loaded {len(corpus)} decisions from full corpus")
    return corpus

def build_norm_embeddings(signals: Dict[str, Any], metadata: List[Dict]) -> Tuple[np.ndarray, List[int]]:
    if EMBEDDING_MODEL is None:
        logger.warning("No embedding model, returning zeros")
        return np.zeros((len(metadata), 384)), []
    
    meta_by_id = {m['decision_id']: i for i, m in enumerate(metadata)}
    valid_indices = []
    embeddings_list = []
    
    for i, m in enumerate(metadata):
        did = m['decision_id']
        sig = signals.get(did, {})
        
        statute_contexts = sig.get('statute_contexts', [])
        if not statute_contexts:
            continue
        
        context_embeddings = EMBEDDING_MODEL.encode(statute_contexts, show_progress_bar=False)
        avg_embedding = np.mean(context_embeddings, axis=0)
        embeddings_list.append(avg_embedding)
        valid_indices.append(i)
    
    if not embeddings_list:
        return np.zeros((len(metadata), 384)), []
    
    n_dim = embeddings_list[0].shape[0]
    full_emb = np.zeros((len(metadata), n_dim))
    for j, idx in enumerate(valid_indices):
        full_emb[idx] = embeddings_list[j]
    
    norms = np.linalg.norm(full_emb, axis=1, keepdims=True)
    norms[norms == 0] = 1
    full_emb = full_emb / norms
    
    logger.info(f"Norm embeddings: {len(valid_indices)} valid, {n_dim} dims")
    return full_emb, valid_indices

def build_citation_weight_matrix(signals: Dict[str, Any], metadata: List[Dict]) -> np.ndarray:
    n = len(metadata)
    id_to_idx = {m['decision_id']: i for i, m in enumerate(metadata)}
    
    rows, cols, weights = [], [], []
    
    for i, m in enumerate(metadata):
        did = m['decision_id']
        sig = signals.get(did, {})
        
        outgoing = sig.get('outgoing_citations', [])
        for cit in outgoing:
            target = cit.get('target', '')
            if target in id_to_idx:
                j = id_to_idx[target]
                mention_count = cit.get('mention_count', 1)
                confidence = cit.get('confidence', 1.0)
                weight = mention_count * confidence
                rows.append(i)
                cols.append(j)
                weights.append(weight)
        
        cited = sig.get('cited_decisions', [])
        for target in cited:
            if target in id_to_idx:
                j = id_to_idx[target]
                if not any(r == i and c == j for r, c in zip(rows, cols)):
                    rows.append(i)
                    cols.append(j)
                    weights.append(1.0)
    
    if not rows:
        return np.zeros((n, 64))
    
    citation_matrix = csr_matrix((weights, (rows, cols)), shape=(n, n))
    citation_sym = citation_matrix + citation_matrix.T
    
    row_sums = np.array(citation_sym.sum(axis=1)).flatten()
    row_sums[row_sums == 0] = 1
    citation_norm = citation_sym.multiply(1.0 / row_sums[:, np.newaxis])
    
    n_comp = min(64, citation_norm.shape[1] - 1, n - 1)
    svd = TruncatedSVD(n_components=n_comp, random_state=42)
    emb = svd.fit_transform(citation_norm)
    
    norms = np.linalg.norm(emb, axis=1, keepdims=True)
    norms[norms == 0] = 1
    emb = emb / norms
    
    logger.info(f"Citation weight embeddings: {n} decisions, {n_comp} dims")
    return emb

def build_tfidf_signals(signals: Dict[str, Any], metadata: List[Dict], config: SignalConfig) -> Tuple[np.ndarray, List[int]]:
    texts = []
    valid_indices = []
    
    for i, m in enumerate(metadata):
        did = m['decision_id']
        sig = signals.get(did, {})
        
        parts = []
        
        if config.use_sachverhalt and sig.get('sachverhalt_text'):
            parts.append(sig['sachverhalt_text'])
        
        if config.use_erwaegungen and sig.get('erwaegungen_text'):
            parts.append(sig['erwaegungen_text'])
        
        if config.use_cited_decisions_tfidf and sig.get('cited_decisions'):
            parts.append(" ".join(sig['cited_decisions']))
        
        if config.use_doctrine_refs and sig.get('doctrine_refs'):
            parts.append(" ".join(sig['doctrine_refs']))
        
        if config.use_outcome and sig.get('outcome'):
            parts.append(sig['outcome'])
        
        if config.use_legal_area and sig.get('legal_area'):
            parts.append(sig['legal_area'])
        
        if config.use_erwaegungen_headings and sig.get('erwaegungen_headings'):
            parts.append(" ".join(sig['erwaegungen_headings']))
        
        if parts:
            texts.append(" ".join(parts))
            valid_indices.append(i)
        else:
            texts.append("")
    
    if len(valid_indices) < 100:
        logger.warning(f"Only {len(valid_indices)} valid texts for TF-IDF")
        return np.zeros((len(metadata), 128)), valid_indices
    
    valid_texts = [texts[i] for i in valid_indices]
    
    vectorizer = TfidfVectorizer(
        max_features=config.max_features,
        min_df=config.min_df,
        max_df=config.max_df,
        ngram_range=config.ngram_range,
        sublinear_tf=True,
        lowercase=True,
        strip_accents='unicode',
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
    
    logger.info(f"TF-IDF signals: {len(valid_indices)} valid, {n_comp} dims")
    return full_emb, valid_indices

def build_baseline_embeddings():
    from run_cycle_14 import (
        load_representations, create_debiased_citation_blended,
        load_corpus_citations
    )
    
    _, metadata = load_metadata_with_branch()
    _, baseline_768 = load_representations()
    citations = load_corpus_citations()
    
    baseline_emb, baseline_info = create_debiased_citation_blended(
        baseline_768, metadata, citations,
        n_pca_components=1, alpha=0.7, dims=64
    )
    
    logger.info(f"Baseline created: {baseline_info}")
    return baseline_emb, metadata

def project_to_dim(emb: np.ndarray, target_dim: int) -> np.ndarray:
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

def create_hybrid_representation(
    legal_emb: np.ndarray,
    baseline_emb: np.ndarray,
    alpha: float = 0.5,
    target_dim: int = 64
) -> np.ndarray:
    legal_proj = project_to_dim(legal_emb, target_dim)
    baseline_proj = project_to_dim(baseline_emb, target_dim)
    
    legal_proj = normalize(legal_proj, norm='l2', axis=1)
    baseline_proj = normalize(baseline_proj, norm='l2', axis=1)
    
    hybrid = alpha * legal_proj + (1 - alpha) * baseline_proj
    hybrid = normalize(hybrid, norm='l2', axis=1)
    
    return hybrid

def average_embeddings(emb_list: List[np.ndarray], target_dim: int = 64) -> np.ndarray:
    projected = [project_to_dim(emb, target_dim) for emb in emb_list]
    projected = [normalize(emb, norm='l2', axis=1) for emb in projected]
    avg = np.mean(projected, axis=0)
    avg = normalize(avg, norm='l2', axis=1)
    return avg

def evaluate_with_fractal_harness(
    embeddings: np.ndarray,
    metadata: List[Dict],
    config_name: str,
    coarse_res: float = 0.5,
    sub_res: float = 3.0
) -> Dict[str, Any]:
    logger.info(f"\n=== Evaluating {config_name} with Fractal-Map Harness ===")
    
    hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine = hierarchical_leiden(
        embeddings, metadata, coarse_res=coarse_res, sub_res=sub_res
    )
    
    n_fine = len(set(hierarchical_labels[hierarchical_labels != -1]))
    n_coarse = len(set(coarse_labels[coarse_labels != -1]))
    
    coarse_purities = compute_branch_purity_per_cluster(coarse_labels, metadata)
    coarse_overall = compute_branch_purity(coarse_labels, metadata)
    
    fine_purities = compute_branch_purity_per_cluster(hierarchical_labels, metadata)
    fine_overall = compute_branch_purity(hierarchical_labels, metadata)
    
    total_improvements = 0
    total_deteriorations = 0
    total_no_change = 0
    zoom_results = {}
    
    for coarse_id in sorted(coarse_to_fine.keys()):
        fine_ids = coarse_to_fine[coarse_id]
        if not fine_ids:
            continue
        
        coarse_pur = coarse_purities.get(coarse_id, 0)
        fine_purs = [fine_purities.get(fid, 0) for fid in fine_ids]
        fine_mean = np.mean(fine_purs) if fine_purs else 0
        improvement = fine_mean - coarse_pur
        
        improvements = sum(1 for fp in fine_purs if fp > coarse_pur + 0.01)
        deteriorations = sum(1 for fp in fine_purs if fp < coarse_pur - 0.01)
        no_change = len(fine_purs) - improvements - deteriorations
        
        total_improvements += improvements
        total_deteriorations += deteriorations
        total_no_change += no_change
        
        coarse_mask = coarse_labels == coarse_id
        coarse_branches = [metadata[i].get('branch') for i in np.where(coarse_mask)[0]]
        coarse_branches = [b for b in coarse_branches if b and b != 'null']
        coarse_dom = Counter(coarse_branches).most_common(1)[0][0] if coarse_branches else "unknown"
        
        zoom_results[int(coarse_id)] = {
            'coarse_size': int(np.sum(coarse_mask)),
            'coarse_purity': float(coarse_pur),
            'coarse_dominant_branch': coarse_dom,
            'n_fine_clusters': len(fine_ids),
            'fine_purity_mean': float(fine_mean),
            'fine_purity_values': [float(p) for p in fine_purs],
            'improvement': float(improvement),
            'improvement_pct': float(improvement / coarse_pur * 100) if coarse_pur > 0 else 0,
            'improvements': improvements,
            'deteriorations': deteriorations,
            'no_change': no_change,
        }
    
    overall_improvement = fine_overall - coarse_overall
    total_fine = total_improvements + total_deteriorations + total_no_change
    improvement_rate = total_improvements / total_fine if total_fine > 0 else 0
    
    from sklearn.metrics import normalized_mutual_info_score
    unique_labels = np.unique(hierarchical_labels[hierarchical_labels != -1])
    legal_areas = [metadata[i].get('legal_area', '') for i in range(len(metadata))]
    legal_areas = [la if la else 'unknown' for la in legal_areas]
    nmi = normalized_mutual_info_score(legal_areas, hierarchical_labels)
    
    flat_labels, _ = leiden_clustering(embeddings, resolution=sub_res)
    flat_purity = compute_branch_purity(flat_labels, metadata)
    
    logger.info(f"  Coarse clusters: {n_coarse}, Fine clusters: {n_fine}")
    logger.info(f"  Coarse purity: {coarse_overall:.4f}, Fine purity: {fine_overall:.4f}")
    logger.info(f"  Overall improvement: {overall_improvement:+.4f} ({overall_improvement/coarse_overall*100:+.1f}%)")
    logger.info(f"  Improvement rate: {improvement_rate:.1%} ({total_improvements}/{total_fine})")
    logger.info(f"  Legal area NMI: {nmi:.4f}")
    logger.info(f"  Flat Leiden (res={sub_res}) purity: {flat_purity:.4f}, Hierarchical advantage: {fine_overall - flat_purity:+.4f}")
    
    verdict = "PASS" if improvement_rate > 0.5 and overall_improvement > 0 else "PARTIAL" if improvement_rate > 0.3 else "FAIL"
    logger.info(f"  VERDICT: {verdict}")
    
    return {
        'config_name': config_name,
        'n_coarse_clusters': n_coarse,
        'n_fine_clusters': n_fine,
        'coarse_purity': float(coarse_overall),
        'fine_purity': float(fine_overall),
        'overall_improvement': float(overall_improvement),
        'improvement_pct': float(overall_improvement / coarse_overall * 100) if coarse_overall > 0 else 0,
        'total_improvements': int(total_improvements),
        'total_deteriorations': int(total_deteriorations),
        'total_no_change': int(total_no_change),
        'improvement_rate': float(improvement_rate),
        'legal_area_nmi': float(nmi),
        'flat_purity': float(flat_purity),
        'hierarchical_advantage': float(fine_overall - flat_purity),
        'verdict': verdict,
        'zoom_results': zoom_results,
    }

def main():
    logger.info("=" * 70)
    logger.info("Legal Distance Lane v5 - Scale Test on Full Corpus (1200 decisions)")
    logger.info("=" * 70)
    
    # 1. Load data
    logger.info("\n1. Loading legal signals (full corpus)...")
    signals = load_signals()
    
    logger.info("\n2. Loading baseline embeddings and metadata...")
    baseline_emb, metadata = build_baseline_embeddings()
    
    # 3. Build signal components
    logger.info("\n3. Building signal components...")
    
    tfidf_sachverhalt, _ = build_tfidf_signals(signals, metadata, SignalConfig(use_sachverhalt=True))
    tfidf_erwaegungen, _ = build_tfidf_signals(signals, metadata, SignalConfig(use_erwaegungen=True))
    tfidf_cited_decisions, _ = build_tfidf_signals(signals, metadata, SignalConfig(use_cited_decisions_tfidf=True))
    tfidf_doctrine, _ = build_tfidf_signals(signals, metadata, SignalConfig(use_doctrine_refs=True))
    tfidf_outcome, _ = build_tfidf_signals(signals, metadata, SignalConfig(use_outcome=True))
    tfidf_legal_area, _ = build_tfidf_signals(signals, metadata, SignalConfig(use_legal_area=True))
    tfidf_headings, _ = build_tfidf_signals(signals, metadata, SignalConfig(use_erwaegungen_headings=True))
    
    norm_emb, _ = build_norm_embeddings(signals, metadata)
    citation_emb = build_citation_weight_matrix(signals, metadata)
    
    # 4. Define validated experiments from v4
    experiments = [
        # Baseline
        ("baseline_debiased_citation_blended", baseline_emb, "Validated baseline: debiased_citation_blended (n_pca=1, alpha=0.7)"),
        
        # Best single signals from v4
        ("sachverhalt_tfidf", tfidf_sachverhalt, "TF-IDF on Sachverhalt (facts) - v4 best balanced single signal"),
        ("norm_embeddings", norm_emb, "Norm/article embeddings (multilingual sentence transformer) - v4 strong balanced"),
        ("erwaegungen_tfidf", tfidf_erwaegungen, "TF-IDF on Erwägungen (reasoning)"),
        ("legal_area_tfidf", tfidf_legal_area, "TF-IDF on legal_area (Jurivoc) - v4 best NMI"),
        ("cited_decisions_tfidf", tfidf_cited_decisions, "TF-IDF on cited decisions"),
        
        # Best core combinations (no baseline)
        ("erwaegungen+citations", average_embeddings([tfidf_erwaegungen, citation_emb]), "Erwägungen + citation weights - v4 best core combo"),
        ("sachverhalt+erwaegungen", average_embeddings([tfidf_sachverhalt, tfidf_erwaegungen]), "Sachverhalt + Erwägungen (facts + reasoning)"),
        
        # Best hybrids with baseline
        ("hybrid_erwaegungen_07", create_hybrid_representation(tfidf_erwaegungen, baseline_emb, 0.7), "Hybrid: 70% erwaegungen + 30% baseline - v4 best trade-off"),
        ("hybrid_sachverhalt_07", create_hybrid_representation(tfidf_sachverhalt, baseline_emb, 0.7), "Hybrid: 70% sachverhalt + 30% baseline"),
        ("hybrid_norm_07", create_hybrid_representation(norm_emb, baseline_emb, 0.7), "Hybrid: 70% norm_embeddings + 30% baseline"),
        ("hybrid_erwaegungen_05", create_hybrid_representation(tfidf_erwaegungen, baseline_emb, 0.5), "Hybrid: 50% erwaegungen + 50% baseline"),
        ("hybrid_erwaegungen_03", create_hybrid_representation(tfidf_erwaegungen, baseline_emb, 0.3), "Hybrid: 30% erwaegungen + 70% baseline"),
        
        # Legal issues/outcomes mode
        ("legal_issues_outcomes", average_embeddings([tfidf_legal_area, tfidf_outcome, tfidf_headings]), "Legal area + outcome + headings (issue/outcome signals)"),
        
        # Core legal (erwaegungen + norms + citations)
        ("core_legal", average_embeddings([tfidf_erwaegungen, norm_emb, citation_emb]), "Core legal: erwaegungen + norms + citations"),
    ]
    
    # 5. Run evaluations
    logger.info(f"\n4. Running {len(experiments)} experiments with fractal-map harness...")
    all_results = {}
    
    for name, emb, desc in experiments:
        logger.info(f"\n{'='*60}")
        logger.info(f"EXPERIMENT: {name}")
        logger.info(f"  Description: {desc}")
        logger.info(f"  Embedding shape: {emb.shape}")
        
        results = evaluate_with_fractal_harness(emb, metadata, name)
        results['embedding_shape'] = list(emb.shape)
        all_results[name] = results
        
        # Save intermediate
        with open(OUTPUT_DIR / f"scale_{name}_results.json", 'w') as f:
            json.dump(results, f, indent=2, default=str)
    
    # 6. Save all results
    with open(OUTPUT_DIR / "scale_test_all_results.json", 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # 7. Summary comparison
    logger.info("\n" + "=" * 80)
    logger.info("V5 SCALE TEST SUMMARY")
    logger.info("=" * 80)
    logger.info(f"{'Experiment':<35} {'Coarse':>6} {'Fine':>6} {'Improv':>8} {'Rate':>7} {'NMI':>6} {'Verdict':>8}")
    logger.info("-" * 80)
    
    baseline_result = all_results.get("baseline_debiased_citation_blended", {})
    baseline_fine = baseline_result.get('fine_purity', 0)
    baseline_nmi = baseline_result.get('legal_area_nmi', 0)
    baseline_coarse = baseline_result.get('coarse_purity', 0)
    
    logger.info(f"{'baseline_debiased_citation_blended':<35} {baseline_coarse:.3f}  {baseline_fine:.3f}  {'0.000':>8}  {'-':>7}  {baseline_nmi:.3f}  {'BASELINE':>8}")
    
    for name, res in all_results.items():
        if name == "baseline_debiased_citation_blended":
            continue
        
        coarse = res.get('coarse_purity', 0)
        fine = res.get('fine_purity', 0)
        improv = res.get('overall_improvement', 0)
        rate = res.get('improvement_rate', 0)
        nmi = res.get('legal_area_nmi', 0)
        verdict = res.get('verdict', 'N/A')
        
        fine_delta = fine - baseline_fine
        nmi_delta = nmi - baseline_nmi
        coarse_delta = coarse - baseline_coarse
        
        logger.info(f"{name:<35} {coarse:.3f}  {fine:.3f}  {improv:+.3f}   {rate:.1%}  {nmi:.3f}  {verdict:>8}  (ΔF={fine_delta:+.3f}, ΔN={nmi_delta:+.3f}, ΔC={coarse_delta:+.3f})")
    
    # 8. Key findings
    logger.info("\n" + "=" * 80)
    logger.info("KEY FINDINGS - SCALE TEST")
    logger.info("=" * 80)
    
    # Compare with v4 results (from report)
    v4_baseline_fine = 0.850
    v4_baseline_nmi = 0.512
    v4_baseline_coarse = 0.714
    
    logger.info(f"\nBaseline comparison (v4 1000-slice vs v5 1200-full):")
    logger.info(f"  v4 baseline: coarse={v4_baseline_coarse:.3f}, fine={v4_baseline_fine:.3f}, NMI={v4_baseline_nmi:.3f}")
    logger.info(f"  v5 baseline: coarse={baseline_coarse:.3f}, fine={baseline_fine:.3f}, NMI={baseline_nmi:.3f}")
    logger.info(f"  Delta:       coarse={baseline_coarse-v4_baseline_coarse:+.3f}, fine={baseline_fine-v4_baseline_fine:+.3f}, NMI={baseline_nmi-v4_baseline_nmi:+.3f}")
    
    # Which signals improve over baseline at scale
    logger.info("\nSignals IMPROVING over baseline at scale (fine_purity):")
    for name, res in all_results.items():
        if name == "baseline_debiased_citation_blended":
            continue
        delta = res.get('fine_purity', 0) - baseline_fine
        if delta > 0.01:
            logger.info(f"  {name}: Δ={delta:+.4f} (fine={res.get('fine_purity', 0):.4f})")
    
    logger.info("\nSignals IMPROVING over baseline at scale (legal_area_NMI):")
    for name, res in all_results.items():
        if name == "baseline_debiased_citation_blended":
            continue
        delta = res.get('legal_area_nmi', 0) - baseline_nmi
        if delta > 0.01:
            logger.info(f"  {name}: Δ={delta:+.4f} (NMI={res.get('legal_area_nmi', 0):.4f})")
    
    logger.info("\nSignals PRESERVING coarse structure (coarse_purity close to baseline):")
    for name, res in all_results.items():
        if name == "baseline_debiased_citation_blended":
            continue
        delta = res.get('coarse_purity', 0) - baseline_coarse
        if delta > -0.1:  # Within 0.1 of baseline
            logger.info(f"  {name}: coarse={res.get('coarse_purity', 0):.4f} (Δ={delta:+.4f})")
    
    logger.info("\n=== V5 Scale Test Complete ===")
    return all_results

if __name__ == "__main__":
    main()
