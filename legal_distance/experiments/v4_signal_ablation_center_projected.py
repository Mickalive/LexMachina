#!/usr/bin/env python3
"""
Legal Distance Lane v4 - Systematic Unsupervised Signal Ablation (center_projected baseline)

Using the REPRODUCED center_projected baseline (language-center-subtracted 768-dim embeddings)
and validated fractal-map harness, run systematic UNSUPERVISED signal ablation:
combine/weight legal-specific signals (sachverhalt TF-IDF, erwaegungen TF-IDF, 
norm/article embeddings, citation role weights, doctrine citations, outcome/holding) 
against the center_projected baseline to identify which legally structured signals improve 
nearest-neighbor legal relevance while suppressing procedural boilerplate.

Leverages Jurivoc/TF metadata as evaluation proxies, not training labels.
"""

import json
import numpy as np
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import Counter, defaultdict
from datetime import datetime, timezone

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
    build_concat, extract_erwaegungen, compute_tfidf_erwaegungen
)
from hierarchical_zoom_validation import hierarchical_leiden, compute_branch_purity_per_cluster

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
SIGNALS_FILE = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/legal_signals_full.jsonl")
CENTER_PROJECTED_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/signal_ablation_center_projected")
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
    """Configuration for which legal signals to include."""
    use_sachverhalt: bool = False
    use_erwaegungen: bool = False
    use_norm_embeddings: bool = False
    use_citation_weights: bool = False
    use_doctrine_refs: bool = False
    use_outcome: bool = False
    use_legal_area: bool = False
    use_erwaegungen_headings: bool = False
    max_features: int = 5000
    min_df: int = 2
    max_df: float = 0.95
    ngram_range: Tuple[int, int] = (1, 2)


def load_signals() -> Dict[str, Any]:
    """Load extracted legal signals (full corpus)."""
    signals = {}
    with open(SIGNALS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            signals[data['decision_id']] = data
    logger.info(f"Loaded signals for {len(signals)} decisions")
    return signals


def load_center_projected_baseline() -> Tuple[np.ndarray, List[Dict]]:
    """Load the REPRODUCED center_projected baseline (768-dim) and metadata."""
    embeddings_path = CENTER_PROJECTED_DIR / 'embeddings_center_projected.npy'
    metadata_path = CENTER_PROJECTED_DIR / 'metadata.json'
    
    embeddings = np.load(embeddings_path)
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    logger.info(f"Loaded center_projected baseline: {embeddings.shape}")
    return embeddings, metadata


def build_norm_embeddings(signals: Dict[str, Any], metadata: List[Dict]) -> Tuple[np.ndarray, List[int]]:
    """
    Build norm/article embeddings using statute contexts + sentence transformer.
    For each decision, embed the statute contexts and average them.
    """
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
        
        # Embed each statute context
        context_embeddings = EMBEDDING_MODEL.encode(statute_contexts, show_progress_bar=False)
        
        # Average the embeddings for this decision
        avg_embedding = np.mean(context_embeddings, axis=0)
        embeddings_list.append(avg_embedding)
        valid_indices.append(i)
    
    if not embeddings_list:
        return np.zeros((len(metadata), 384)), []
    
    # Create full matrix
    n_dim = embeddings_list[0].shape[0]
    full_emb = np.zeros((len(metadata), n_dim))
    for j, idx in enumerate(valid_indices):
        full_emb[idx] = embeddings_list[j]
    
    # Normalize
    norms = np.linalg.norm(full_emb, axis=1, keepdims=True)
    norms[norms == 0] = 1
    full_emb = full_emb / norms
    
    logger.info(f"Norm embeddings: {len(valid_indices)} valid, {n_dim} dims")
    return full_emb, valid_indices


def build_citation_weight_matrix(signals: Dict[str, Any], metadata: List[Dict]) -> np.ndarray:
    """
    Build citation role weight matrix.
    Uses outgoing citations with mention_count and confidence as weights.
    Creates a decision x decision weighted adjacency matrix, then embeds via SVD.
    """
    n = len(metadata)
    id_to_idx = {m['decision_id']: i for i, m in enumerate(metadata)}
    
    # Build weighted citation matrix
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
        
        # Also use cited_decisions as fallback (binary)
        cited = sig.get('cited_decisions', [])
        for target in cited:
            if target in id_to_idx:
                j = id_to_idx[target]
                # Check if already added from outgoing
                if not any(r == i and c == j for r, c in zip(rows, cols)):
                    rows.append(i)
                    cols.append(j)
                    weights.append(1.0)
    
    if not rows:
        return np.zeros((n, 64))
    
    # Create sparse matrix and compute SVD
    from scipy.sparse import csr_matrix
    citation_matrix = csr_matrix((weights, (rows, cols)), shape=(n, n))
    
    # Make symmetric (undirected for embedding)
    citation_sym = citation_matrix + citation_matrix.T
    
    # Row-normalize
    row_sums = np.array(citation_sym.sum(axis=1)).flatten()
    row_sums[row_sums == 0] = 1
    citation_norm = citation_sym.multiply(1.0 / row_sums[:, np.newaxis])
    
    # SVD for embedding
    n_comp = min(64, citation_norm.shape[1] - 1, n - 1)
    svd = TruncatedSVD(n_components=n_comp, random_state=42)
    emb = svd.fit_transform(citation_norm)
    
    # Normalize
    norms = np.linalg.norm(emb, axis=1, keepdims=True)
    norms[norms == 0] = 1
    emb = emb / norms
    
    logger.info(f"Citation weight embeddings: {n} decisions, {n_comp} dims")
    return emb


def build_tfidf_signals(signals: Dict[str, Any], metadata: List[Dict], config: SignalConfig) -> Tuple[np.ndarray, List[int]]:
    """Build TF-IDF representation from selected legal signals."""
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
    
    # Filter to valid only
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
    
    # Create full matrix
    full_emb = np.zeros((len(metadata), n_comp))
    for j, idx in enumerate(valid_indices):
        full_emb[idx] = reduced[j]
    
    logger.info(f"TF-IDF signals: {len(valid_indices)} valid, {n_comp} dims")
    return full_emb, valid_indices


def project_to_dim(emb: np.ndarray, target_dim: int) -> np.ndarray:
    """Project embeddings to target dimension."""
    n_samples, n_features = emb.shape
    
    if n_features <= target_dim:
        # Pad with zeros if needed
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
    """Create hybrid representation blending legal signals with center_projected baseline."""
    # Project both to same dimension
    legal_proj = project_to_dim(legal_emb, target_dim)
    baseline_proj = project_to_dim(baseline_emb, target_dim)
    
    # Normalize both
    legal_proj = normalize(legal_proj, norm='l2', axis=1)
    baseline_proj = normalize(baseline_proj, norm='l2', axis=1)
    
    # Blend: alpha = weight for legal signals, (1-alpha) = weight for center_projected
    hybrid = alpha * legal_proj + (1 - alpha) * baseline_proj
    hybrid = normalize(hybrid, norm='l2', axis=1)
    
    return hybrid


def average_embeddings(emb_list: List[np.ndarray], target_dim: int = 64) -> np.ndarray:
    """Average multiple embeddings after projecting to same dimension."""
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
    """
    Evaluate embeddings using the validated fractal-map harness:
    Hierarchical Leiden + zoom coherence validation.
    """
    logger.info(f"\n=== Evaluating {config_name} with Fractal-Map Harness ===")
    
    # Run hierarchical Leiden
    hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine = hierarchical_leiden(
        embeddings, metadata, coarse_res=coarse_res, sub_res=sub_res
    )
    
    n_fine = len(set(hierarchical_labels[hierarchical_labels != -1]))
    n_coarse = len(set(coarse_labels[coarse_labels != -1]))
    
    # Compute branch purity at coarse level
    coarse_purities = compute_branch_purity_per_cluster(coarse_labels, metadata)
    coarse_overall = compute_branch_purity(coarse_labels, metadata)
    
    # Compute branch purity at fine level
    fine_purities = compute_branch_purity_per_cluster(hierarchical_labels, metadata)
    fine_overall = compute_branch_purity(hierarchical_labels, metadata)
    
    # Zoom coherence analysis
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
    
    # Legal area NMI (as proxy for Jurivoc/TF metadata alignment)
    from sklearn.metrics import normalized_mutual_info_score
    unique_labels = np.unique(hierarchical_labels[hierarchical_labels != -1])
    legal_areas = [metadata[i].get('legal_area', '') for i in range(len(metadata))]
    legal_areas = [la if la else 'unknown' for la in legal_areas]
    nmi = normalized_mutual_info_score(legal_areas, hierarchical_labels)
    
    # Compare with flat Leiden at equivalent resolution
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
    logger.info("Legal Distance Lane v4 - Systematic Unsupervised Signal Ablation")
    logger.info("BASELINE: center_projected (reproduced, language-center-subtracted)")
    logger.info("=" * 70)
    
    # 1. Load data
    logger.info("\n1. Loading legal signals (full corpus)...")
    signals = load_signals()
    
    logger.info("\n2. Loading center_projected baseline embeddings and metadata...")
    baseline_emb, metadata = load_center_projected_baseline()
    
    # 3. Build individual signal components
    logger.info("\n3. Building individual signal components...")
    
    # TF-IDF signals
    tfidf_sachverhalt, _ = build_tfidf_signals(signals, metadata, SignalConfig(use_sachverhalt=True))
    tfidf_erwaegungen, _ = build_tfidf_signals(signals, metadata, SignalConfig(use_erwaegungen=True))
    tfidf_doctrine, _ = build_tfidf_signals(signals, metadata, SignalConfig(use_doctrine_refs=True))
    tfidf_outcome, _ = build_tfidf_signals(signals, metadata, SignalConfig(use_outcome=True))
    tfidf_legal_area, _ = build_tfidf_signals(signals, metadata, SignalConfig(use_legal_area=True))
    tfidf_headings, _ = build_tfidf_signals(signals, metadata, SignalConfig(use_erwaegungen_headings=True))
    
    # Norm embeddings
    norm_emb, _ = build_norm_embeddings(signals, metadata)
    
    # Citation weight embeddings
    citation_emb = build_citation_weight_matrix(signals, metadata)
    
    # 4. Define experiment configurations for systematic ablation
    # Using center_projected as baseline (alpha = legal weight, 1-alpha = center_projected weight)
    experiments = [
        # Single signals
        ("sachverhalt_tfidf", tfidf_sachverhalt, 1.0),
        ("erwaegungen_tfidf", tfidf_erwaegungen, 1.0),
        ("norm_embeddings", norm_emb, 1.0),
        ("citation_weights", citation_emb, 1.0),
        ("doctrine_tfidf", tfidf_doctrine, 1.0),
        ("outcome_tfidf", tfidf_outcome, 1.0),
        ("legal_area_tfidf", tfidf_legal_area, 1.0),
        ("headings_tfidf", tfidf_headings, 1.0),
        
        # Core combinations (no baseline) - average after projection
        ("sachverhalt+erwaegungen", average_embeddings([tfidf_sachverhalt, tfidf_erwaegungen]), 1.0),
        ("erwaegungen+norms", average_embeddings([tfidf_erwaegungen, norm_emb]), 1.0),
        ("erwaegungen+citations", average_embeddings([tfidf_erwaegungen, citation_emb]), 1.0),
        ("erwaegungen+doctrine", average_embeddings([tfidf_erwaegungen, tfidf_doctrine]), 1.0),
        ("sachverhalt+norms", average_embeddings([tfidf_sachverhalt, norm_emb]), 1.0),
        ("core_legal", average_embeddings([tfidf_erwaegungen, norm_emb, citation_emb]), 1.0),
        ("all_tfidf", average_embeddings([tfidf_sachverhalt, tfidf_erwaegungen, tfidf_doctrine, tfidf_outcome, tfidf_legal_area, tfidf_headings]), 1.0),
        
        # Hybrids with center_projected baseline (alpha = legal weight)
        ("hybrid_erwaegungen_03", create_hybrid_representation(tfidf_erwaegungen, baseline_emb, 0.3), 0.3),
        ("hybrid_erwaegungen_05", create_hybrid_representation(tfidf_erwaegungen, baseline_emb, 0.5), 0.5),
        ("hybrid_erwaegungen_07", create_hybrid_representation(tfidf_erwaegungen, baseline_emb, 0.7), 0.7),
        ("hybrid_core_03", create_hybrid_representation(average_embeddings([tfidf_erwaegungen, norm_emb, citation_emb]), baseline_emb, 0.3), 0.3),
        ("hybrid_core_05", create_hybrid_representation(average_embeddings([tfidf_erwaegungen, norm_emb, citation_emb]), baseline_emb, 0.5), 0.5),
        ("hybrid_core_07", create_hybrid_representation(average_embeddings([tfidf_erwaegungen, norm_emb, citation_emb]), baseline_emb, 0.7), 0.7),
        ("hybrid_alltfidf_03", create_hybrid_representation(average_embeddings([tfidf_sachverhalt, tfidf_erwaegungen, tfidf_doctrine, tfidf_outcome, tfidf_legal_area, tfidf_headings]), baseline_emb, 0.3), 0.3),
        ("hybrid_alltfidf_05", create_hybrid_representation(average_embeddings([tfidf_sachverhalt, tfidf_erwaegungen, tfidf_doctrine, tfidf_outcome, tfidf_legal_area, tfidf_headings]), baseline_emb, 0.5), 0.5),
        ("hybrid_alltfidf_07", create_hybrid_representation(average_embeddings([tfidf_sachverhalt, tfidf_erwaegungen, tfidf_doctrine, tfidf_outcome, tfidf_legal_area, tfidf_headings]), baseline_emb, 0.7), 0.7),
        
        # Baseline only (center_projected)
        ("baseline_center_projected", baseline_emb, 0.0),
    ]
    
    # 5. Run evaluations
    logger.info(f"\n4. Running {len(experiments)} experiments with fractal-map harness...")
    all_results = {}
    
    for name, emb, alpha in experiments:
        logger.info(f"\n{'='*60}")
        logger.info(f"EXPERIMENT: {name} (alpha={alpha})")
        logger.info(f"  Embedding shape: {emb.shape}")
        
        results = evaluate_with_fractal_harness(emb, metadata, name)
        results['alpha'] = alpha
        results['embedding_shape'] = list(emb.shape)
        all_results[name] = results
        
        # Save intermediate
        with open(OUTPUT_DIR / f"v4_{name}_results.json", 'w') as f:
            json.dump(results, f, indent=2, default=str)
    
    # 6. Save all results
    with open(OUTPUT_DIR / "v4_signal_ablation_center_projected_all_results.json", 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # 7. Summary comparison
    logger.info("\n" + "=" * 80)
    logger.info("V4 SIGNAL ABLATION SUMMARY (center_projected baseline)")
    logger.info("=" * 80)
    logger.info(f"{'Experiment':<30} {'Coarse':>6} {'Fine':>6} {'Improv':>8} {'Rate':>7} {'NMI':>6} {'Verdict':>8}")
    logger.info("-" * 80)
    
    baseline_result = all_results.get("baseline_center_projected", {})
    baseline_fine = baseline_result.get('fine_purity', 0)
    baseline_nmi = baseline_result.get('legal_area_nmi', 0)
    
    for name, res in all_results.items():
        if name == "baseline_center_projected":
            continue
        
        coarse = res.get('coarse_purity', 0)
        fine = res.get('fine_purity', 0)
        improv = res.get('overall_improvement', 0)
        rate = res.get('improvement_rate', 0)
        nmi = res.get('legal_area_nmi', 0)
        verdict = res.get('verdict', 'N/A')
        
        # Delta from baseline
        fine_delta = fine - baseline_fine
        nmi_delta = nmi - baseline_nmi
        
        logger.info(f"{name:<30} {coarse:.3f}  {fine:.3f}  {improv:+.3f}   {rate:.1%}  {nmi:.3f}  {verdict:>8}  (Δfine={fine_delta:+.3f}, ΔNMI={nmi_delta:+.3f})")
    
    # 8. Key findings
    logger.info("\n" + "=" * 80)
    logger.info("KEY FINDINGS (center_projected baseline)")
    logger.info("=" * 80)
    
    # Best single signal
    single_signals = {k: v for k, v in all_results.items() if '+' not in k and 'hybrid' not in k and k != 'baseline_center_projected'}
    if single_signals:
        best_single = max(single_signals.items(), key=lambda x: x[1].get('fine_purity', 0))
        logger.info(f"Best single signal: {best_single[0]} (fine_purity={best_single[1]['fine_purity']:.4f}, NMI={best_single[1]['legal_area_nmi']:.4f})")
    
    # Best combination (no baseline)
    combos = {k: v for k, v in all_results.items() if '+' in k and 'hybrid' not in k}
    if combos:
        best_combo = max(combos.items(), key=lambda x: x[1].get('fine_purity', 0))
        logger.info(f"Best core combination: {best_combo[0]} (fine_purity={best_combo[1]['fine_purity']:.4f}, NMI={best_combo[1]['legal_area_nmi']:.4f})")
    
    # Best hybrid
    hybrids = {k: v for k, v in all_results.items() if 'hybrid' in k}
    if hybrids:
        best_hybrid = max(hybrids.items(), key=lambda x: x[1].get('fine_purity', 0))
        logger.info(f"Best hybrid: {best_hybrid[0]} (fine_purity={best_hybrid[1]['fine_purity']:.4f}, NMI={best_hybrid[1]['legal_area_nmi']:.4f})")
    
    # Which signals improve over baseline
    logger.info("\nSignals IMPROVING over center_projected baseline (fine_purity):")
    for name, res in all_results.items():
        if name == "baseline_center_projected":
            continue
        delta = res.get('fine_purity', 0) - baseline_fine
        if delta > 0.01:
            logger.info(f"  {name}: Δ={delta:+.4f}")
    
    logger.info("\nSignals IMPROVING over center_projected baseline (legal_area_NMI):")
    for name, res in all_results.items():
        if name == "baseline_center_projected":
            continue
        delta = res.get('legal_area_nmi', 0) - baseline_nmi
        if delta > 0.01:
            logger.info(f"  {name}: Δ={delta:+.4f}")
    
    logger.info("\n=== V4 Signal Ablation (center_projected) Complete ===")
    return all_results


if __name__ == "__main__":
    main()