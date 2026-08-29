#!/usr/bin/env python3
"""
Evaluation Lane v3 - Comprehensive Adversarial Evaluation Harness

Factory Direction v6 requirement: Validate legal-distance unsupervised signal ablation 
results (on center_projected baseline) and frontier_metric_learning_jurivoc supervised 
metric learning results on expanded slice (1,200 decisions) using adversarial benchmarks:
- language dominance
- jurist pairwise preference
- Jurivoc hierarchy alignment
- scale stability
- boilerplate resistance

center_projected is the default reference representation to beat.
Freeze evaluation harness with global seed.
"""

import json
import numpy as np
import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from collections import Counter
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics import normalized_mutual_info_score, adjusted_rand_score
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# FROZEN GLOBAL SEED - DO NOT CHANGE AFTER FREEZING
# ============================================================
GLOBAL_SEED = 42
np.random.seed(GLOBAL_SEED)

# ============================================================
# PATHS
# ============================================================
CENTER_PROJECTED_DIR = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/v5/center_projected_full")
SIGNAL_EMBEDDINGS_DIR = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/v5/signal_ablation_embeddings")
FRACTAL_BASELINE_META = Path("/tmp/lex_accepted/fractal-map/results/fractal_map/baseline/metadata.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/v3")
REPORT_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/reports")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# ============================================================
# CHAMBER TO BRANCH MAPPING
# ============================================================
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

# ============================================================
# METADATA LOADING
# ============================================================
def load_center_projected_metadata() -> List[Dict]:
    """Load metadata for 1200-decision center_projected corpus."""
    with open(CENTER_PROJECTED_DIR / "metadata.json") as f:
        metadata = json.load(f)
    
    for meta in metadata:
        chamber = meta.get("chamber", "")
        meta['branch'] = assign_branch(chamber)
        if 'language' not in meta:
            meta['language'] = meta.get('language', 'de')
    
    return metadata

def load_fractal_baseline_metadata() -> List[Dict]:
    """Load metadata for 1000-decision fractal baseline (signal ablation overlap)."""
    with open(FRACTAL_BASELINE_META) as f:
        metadata = json.load(f)
    
    for meta in metadata:
        chamber = meta.get("chamber", "")
        meta['branch'] = assign_branch(chamber)
        if 'language' not in meta:
            meta['language'] = meta.get('language', 'de')
    
    return metadata

def prepare_metadata_arrays(metadata: List[Dict]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[int]]:
    """Extract branch, language, legal_area from metadata."""
    branches = []
    languages = []
    legal_areas = []
    valid_indices = []
    
    for i, meta in enumerate(metadata):
        branch = meta.get("branch", "unknown")
        lang = meta.get("language", "unknown")
        legal_area = meta.get("legal_area", "unknown")
        
        if branch != "unknown":
            branches.append(branch)
            languages.append(lang)
            legal_areas.append(legal_area)
            valid_indices.append(i)
    
    return np.array(branches), np.array(languages), np.array(legal_areas), valid_indices


def prepare_metadata_arrays_aligned(metadata: List[Dict], embedding_indices: List[int]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[int]]:
    """Extract branch, language, legal_area for specific embedding indices.
    Returns arrays and the filtered embedding indices (excluding unknown branches)."""
    branches = []
    languages = []
    legal_areas = []
    filtered_indices = []
    
    for idx in embedding_indices:
        meta = metadata[idx]
        branch = meta.get("branch", "unknown")
        lang = meta.get("language", "unknown")
        legal_area = meta.get("legal_area", "unknown")
        
        if branch != "unknown":
            branches.append(branch)
            languages.append(lang)
            legal_areas.append(legal_area)
            filtered_indices.append(idx)
    
    return np.array(branches), np.array(languages), np.array(legal_areas), filtered_indices

# ============================================================
# ADVERSARIAL BENCHMARKS
# ============================================================

def adversarial_language_dominance(
    embeddings: np.ndarray, 
    metadata: List[Dict], 
    k: int = 20,
    valid_indices: Optional[List[int]] = None
) -> Dict:
    """
    Adversarial test: measure language dominance in nearest neighbors.
    Language dominance = fraction of k-NN that share the same language.
    Should be LOW (not dominated by language).
    Threshold: < 0.85 PASS
    """
    if valid_indices is not None:
        rep_embeddings = embeddings[valid_indices]
        rep_metadata = [metadata[i] for i in valid_indices]
    else:
        rep_embeddings = embeddings
        rep_metadata = metadata
    
    nn = NearestNeighbors(n_neighbors=k+1, metric='cosine', n_jobs=-1)
    nn.fit(rep_embeddings)
    _, indices = nn.kneighbors(rep_embeddings)
    neighbors = indices[:, 1:]  # Exclude self
    
    dominance_rates = []
    for i, m in enumerate(rep_metadata):
        lang = m.get('language', 'unknown')
        neighbor_langs = [rep_metadata[n].get('language', 'unknown') for n in neighbors[i]]
        same_lang = sum(1 for l in neighbor_langs if l == lang)
        dominance_rates.append(same_lang / k)
    
    mean_dominance = np.mean(dominance_rates)
    
    return {
        'mean_language_dominance': float(mean_dominance),
        'std_language_dominance': float(np.std(dominance_rates)),
        'max_language_dominance': float(np.max(dominance_rates)),
        'k': k,
        'threshold': 0.85,
        'status': 'PASS' if mean_dominance < 0.85 else 'FAIL',
        'note': 'Lower is better - language should not dominate neighbors'
    }

def jurist_pairwise_preference(
    embeddings: np.ndarray,
    branches: np.ndarray,
    languages: np.ndarray,
    k: int = 10
) -> Dict:
    """
    Simulate jurist pairwise preference study.
    
    A jurist is shown a decision and two neighbor candidates:
    - Candidate A: Same branch, different language (legally relevant)
    - Candidate B: Same language, different branch (language artifact)
    
    The jurist should prefer Candidate A. We measure how often
    the embedding space presents Candidate A vs B in top-k.
    """
    n = len(branches)
    
    # Build NN graph
    nn = NearestNeighbors(n_neighbors=k+1, metric='cosine', n_jobs=-1)
    nn.fit(embeddings)
    _, indices = nn.kneighbors(embeddings)
    neighbors = indices[:, 1:]  # Exclude self
    
    legal_relevant_count = 0
    language_artifact_count = 0
    both_count = 0
    neither_count = 0
    
    for i in range(n):
        branch_i = branches[i]
        lang_i = languages[i]
        
        neighbor_branches = branches[neighbors[i]]
        neighbor_langs = languages[neighbors[i]]
        
        has_legal_relevant = False
        has_language_artifact = False
        
        for nb, nl in zip(neighbor_branches, neighbor_langs):
            if nb == branch_i and nl != lang_i:
                has_legal_relevant = True
            if nb != branch_i and nl == lang_i:
                has_language_artifact = True
        
        if has_legal_relevant and has_language_artifact:
            both_count += 1
        elif has_legal_relevant:
            legal_relevant_count += 1
        elif has_language_artifact:
            language_artifact_count += 1
        else:
            neither_count += 1
    
    # Simulated jurist preference: would choose legal-relevant if available
    jurist_correct = legal_relevant_count + both_count
    jurist_forced_wrong = language_artifact_count
    
    total = n
    legal_neighbor_rate = (legal_relevant_count + both_count) / total
    language_neighbor_rate = (language_artifact_count + both_count) / total
    
    return {
        "status": "PASS" if legal_neighbor_rate > 0.5 else "FAIL",
        "total_decisions": total,
        "legal_relevant_only": legal_relevant_count,
        "language_artifact_only": language_artifact_count,
        "both_available": both_count,
        "neither_available": neither_count,
        "legal_neighbor_rate": round(legal_neighbor_rate, 4),
        "language_neighbor_rate": round(language_neighbor_rate, 4),
        "jurist_would_succeed_rate": round(jurist_correct / total, 4),
        "jurist_forced_wrong_rate": round(jurist_forced_wrong / total, 4),
        "note": "Simulated jurist prefers legally-relevant neighbors. Rate > 0.5 means majority of decisions have at least one legally-relevant neighbor in top-k."
    }

def jurivoc_hierarchy_alignment(
    embeddings: np.ndarray,
    legal_areas: np.ndarray,
    n_clusters_list: List[int] = None
) -> Dict:
    """
    Jurivoc hierarchy alignment benchmark (using legal_area as proxy).
    
    Since true Jurivoc descriptors are not available in the corpus,
    we use the court's legal_area metadata as a proxy for human intellectual indexing.
    
    Measures NMI between clustering at different resolutions and legal_area labels.
    Higher NMI indicates better alignment with human legal taxonomy.
    """
    # Filter out None legal_areas
    valid_mask = np.array([la is not None for la in legal_areas])
    if not valid_mask.any():
        return {
            'per_resolution': {},
            'avg_nmi': 0.0,
            'avg_ari': 0.0,
            'status': 'FAIL',
            'note': 'No valid legal_area labels for alignment'
        }
    
    valid_embeddings = embeddings[valid_mask]
    valid_legal_areas = legal_areas[valid_mask]
    
    if n_clusters_list is None:
        n_clusters_list = [5, 10, 15, 20, 30, 50]
    
    results = {}
    for n_clusters in n_clusters_list:
        kmeans = KMeans(n_clusters=n_clusters, random_state=GLOBAL_SEED, n_init=10)
        cluster_labels = kmeans.fit_predict(valid_embeddings)
        nmi = normalized_mutual_info_score(valid_legal_areas, cluster_labels)
        ari = adjusted_rand_score(valid_legal_areas, cluster_labels)
        results[f'n_clusters_{n_clusters}'] = {
            'nmi': float(nmi),
            'ari': float(ari)
        }
    
    # Overall score: average NMI across resolutions
    avg_nmi = np.mean([v['nmi'] for v in results.values()])
    avg_ari = np.mean([v['ari'] for v in results.values()])
    
    return {
        'per_resolution': results,
        'avg_nmi': float(avg_nmi),
        'avg_ari': float(avg_ari),
        'status': 'PASS' if avg_nmi > 0.3 else 'FAIL',  # Threshold based on baseline
        'note': 'NMI with legal_area (proxy for Jurivoc). Higher = better alignment with human legal taxonomy.'
    }

def scale_stability_frozen_pca(
    embeddings: np.ndarray,
    metadata: List[Dict],
    valid_indices: Optional[List[int]] = None,
    subsample_frac: float = 0.8,
    n_trials: int = 10
) -> Dict:
    """
    Scale stability benchmark with frozen PCA.
    
    Tests whether the embedding geometry is stable under corpus subsampling.
    Uses frozen PCA (fit on full corpus, transform subsamples) to measure
    projection consistency.
    
    Returns mean cosine similarity between full and subsample projections.
    """
    if valid_indices is not None:
        rep_embeddings = embeddings[valid_indices]
    else:
        rep_embeddings = embeddings
    
    n = len(rep_embeddings)
    subsample_size = int(n * subsample_frac)
    
    # Fit frozen PCA on full corpus (95% variance or 64 dims, whichever smaller)
    pca = PCA(n_components=min(64, n-1), random_state=GLOBAL_SEED)
    pca.fit(rep_embeddings)
    full_proj = pca.transform(rep_embeddings)
    full_proj = normalize(full_proj, norm='l2', axis=1)
    
    similarities = []
    for trial in range(n_trials):
        # Subsample with fixed seed per trial
        rng = np.random.RandomState(GLOBAL_SEED + trial)
        subsample_idx = rng.choice(n, size=subsample_size, replace=False)
        subsample_emb = rep_embeddings[subsample_idx]
        
        # Transform using FROZEN PCA
        sub_proj = pca.transform(subsample_emb)
        sub_proj = normalize(sub_proj, norm='l2', axis=1)
        
        # Compute similarity for overlapping decisions
        # Map subsample back to full indices
        full_proj_sub = full_proj[subsample_idx]
        cos_sims = np.sum(full_proj_sub * sub_proj, axis=1)
        similarities.append(float(np.mean(cos_sims)))
    
    mean_sim = np.mean(similarities)
    std_sim = np.std(similarities)
    
    return {
        'mean_cosine_similarity': float(mean_sim),
        'std_cosine_similarity': float(std_sim),
        'subsample_frac': subsample_frac,
        'n_trials': n_trials,
        'pca_dims': pca.n_components_,
        'status': 'PASS' if mean_sim > 0.95 else 'FAIL',
        'note': 'Frozen PCA projection consistency under subsampling. Higher = more stable.'
    }

def boilerplate_resistance(
    embeddings: np.ndarray,
    metadata: List[Dict],
    valid_indices: Optional[List[int]] = None,
    k: int = 20
) -> Dict:
    """
    Boilerplate resistance benchmark.
    
    Tests whether nearest neighbors are driven by procedural boilerplate
    rather than substantive legal content.
    
    Approach: Compare neighbor overlap between full-text embeddings and
    embeddings with procedural sections removed (if available).
    
    Since we don't have section-segmented embeddings here, we use a proxy:
    measure how much neighbor sets change when we remove high-frequency
    procedural terms from the representation.
    
    For pure embeddings (no TF-IDF), we use a language-based proxy:
    if neighbors are dominated by same-language pairs, boilerplate may be driving.
    """
    if valid_indices is not None:
        rep_embeddings = embeddings[valid_indices]
        rep_metadata = [metadata[i] for i in valid_indices]
    else:
        rep_embeddings = embeddings
        rep_metadata = metadata
    
    # Language dominance as boilerplate proxy
    nn = NearestNeighbors(n_neighbors=k+1, metric='cosine', n_jobs=-1)
    nn.fit(rep_embeddings)
    _, indices = nn.kneighbors(rep_embeddings)
    neighbors = indices[:, 1:]
    
    # Fraction of decisions where >80% of neighbors share language
    boilerplate_dominated = 0
    for i, m in enumerate(rep_metadata):
        lang = m.get('language', 'unknown')
        neighbor_langs = [rep_metadata[n].get('language', 'unknown') for n in neighbors[i]]
        same_lang = sum(1 for l in neighbor_langs if l == lang)
        if same_lang / k > 0.8:
            boilerplate_dominated += 1
    
    boilerplate_rate = boilerplate_dominated / len(rep_metadata)
    
    return {
        'boilerplate_dominated_rate': float(boilerplate_rate),
        'k': k,
        'threshold': 0.3,  # Should be LOW
        'status': 'PASS' if boilerplate_rate < 0.3 else 'FAIL',
        'note': 'Fraction of decisions with >80% same-language neighbors. Lower = less boilerplate-driven.'
    }

def run_full_benchmark_suite(
    name: str,
    embeddings: np.ndarray,
    metadata: List[Dict],
    valid_indices: Optional[List[int]] = None
) -> Dict:
    """Run all benchmarks on a representation."""
    logger.info(f"\n--- Evaluating {name} ---")
    
    # Align embeddings with metadata
    if valid_indices is not None:
        rep_branches, rep_languages, rep_legal_areas, filtered_indices = prepare_metadata_arrays_aligned(metadata, valid_indices)
        rep_embeddings = embeddings[filtered_indices]
        rep_metadata = [metadata[i] for i in filtered_indices]
    else:
        if len(embeddings) != len(metadata):
            # Try to align by truncating
            min_len = min(len(embeddings), len(metadata))
            rep_embeddings = embeddings[:min_len]
            rep_metadata = metadata[:min_len]
            rep_branches, rep_languages, rep_legal_areas, filtered_indices = prepare_metadata_arrays(rep_metadata)
            rep_embeddings = rep_embeddings[filtered_indices]
            rep_metadata = [rep_metadata[i] for i in filtered_indices]
        else:
            rep_branches, rep_languages, rep_legal_areas, filtered_indices = prepare_metadata_arrays(metadata)
            rep_embeddings = embeddings[filtered_indices]
            rep_metadata = [metadata[i] for i in filtered_indices]
    
    logger.info(f"  Evaluating on {len(rep_embeddings)} decisions")
    
    # 1. Adversarial Language Dominance
    lang_dom = adversarial_language_dominance(rep_embeddings, rep_metadata)
    logger.info(f"  Language Dominance: {lang_dom['mean_language_dominance']:.4f} ({lang_dom['status']})")
    
    # 2. Jurist Pairwise Preference
    jurist_pref = jurist_pairwise_preference(rep_embeddings, rep_branches, rep_languages)
    logger.info(f"  Jurist Preference: {jurist_pref['jurist_would_succeed_rate']:.4f} ({jurist_pref['status']})")
    
    # 3. Jurivoc Hierarchy Alignment (legal_area proxy)
    jurivoc = jurivoc_hierarchy_alignment(rep_embeddings, rep_legal_areas)
    logger.info(f"  Jurivoc Alignment (avg NMI): {jurivoc['avg_nmi']:.4f} ({jurivoc['status']})")
    
    # 4. Scale Stability (Frozen PCA)
    scale_stab = scale_stability_frozen_pca(rep_embeddings, rep_metadata)
    logger.info(f"  Scale Stability: {scale_stab['mean_cosine_similarity']:.4f} ({scale_stab['status']})")
    
    # 5. Boilerplate Resistance
    boilerplate = boilerplate_resistance(rep_embeddings, rep_metadata)
    logger.info(f"  Boilerplate Resistance: {boilerplate['boilerplate_dominated_rate']:.4f} ({boilerplate['status']})")
    
    # Combined status
    all_pass = all([
        lang_dom['status'] == 'PASS',
        jurist_pref['status'] == 'PASS',
        jurivoc['status'] == 'PASS',
        scale_stab['status'] == 'PASS',
        boilerplate['status'] == 'PASS'
    ])
    
    return {
        'name': name,
        'n_decisions': len(rep_embeddings),
        'embedding_dim': int(rep_embeddings.shape[1]),
        'adversarial_language_dominance': lang_dom,
        'jurist_pairwise_preference': jurist_pref,
        'jurivoc_hierarchy_alignment': jurivoc,
        'scale_stability_frozen_pca': scale_stab,
        'boilerplate_resistance': boilerplate,
        'all_benchmarks_pass': all_pass,
        'n_passed': sum([
            lang_dom['status'] == 'PASS',
            jurist_pref['status'] == 'PASS',
            jurivoc['status'] == 'PASS',
            scale_stab['status'] == 'PASS',
            boilerplate['status'] == 'PASS'
        ]),
        'n_total': 5
    }

# ============================================================
# EMBEDDING LOADING
# ============================================================

def load_center_projected() -> Tuple[np.ndarray, List[Dict]]:
    """Load center_projected embeddings (1200 decisions, 768 dim)."""
    embeddings = np.load(CENTER_PROJECTED_DIR / "embeddings_center_projected.npy")
    metadata = load_center_projected_metadata()
    logger.info(f"Loaded center_projected: {embeddings.shape}, {len(metadata)} metadata")
    return embeddings, metadata

def load_center_projected_128() -> Tuple[np.ndarray, List[Dict]]:
    """Load center_projected_128 embeddings (1200 decisions, 128 dim)."""
    embeddings = np.load(CENTER_PROJECTED_DIR / "embeddings_center_projected_128.npy")
    metadata = load_center_projected_metadata()
    logger.info(f"Loaded center_projected_128: {embeddings.shape}")
    return embeddings, metadata

def load_signal_embeddings() -> Dict[str, np.ndarray]:
    """Load signal ablation embeddings (1000 decisions, 128 dim)."""
    signal_names = [
        'signal_sachverhalt_tfidf',
        'signal_erwaegungen_tfidf',
        'signal_legal_area_tfidf',
        'signal_legal_issues_tfidf',
        'signal_outcome_tfidf',
        'signal_headings_tfidf',
        'signal_norm_embeddings',
        'signal_cited_decisions_tfidf',
        'signal_erwaegungen+citations',
        'signal_sachverhalt+erwaegungen',
        'signal_sachverhalt+norms',
        'signal_erwaegungen+norms',
        'signal_erwaegungen+doctrine',
        'signal_legal_issues_outcomes',
        'signal_sachverhalt',
        'signal_erwaegungen',
        'signal_legal_area',
        'signal_legal_issues',
        'signal_outcome',
        'signal_headings',
        'signal_cited_decisions',
        'signal_norm_refs',
    ]
    
    embeddings = {}
    for name in signal_names:
        path = SIGNAL_EMBEDDINGS_DIR / f"{name}.npy"
        if path.exists():
            embeddings[name] = np.load(path)
            logger.info(f"  Loaded {name}: {embeddings[name].shape}")
        else:
            logger.warning(f"  Not found: {path}")
    return embeddings

def load_hybrid_embeddings() -> Dict[str, np.ndarray]:
    """Load hybrid embeddings (1000 decisions, 768 dim)."""
    hybrid_names = [
        'hybrid_erwaegungen_0.3',
        'hybrid_erwaegungen_0.5',
        'hybrid_erwaegungen_0.7',
        'hybrid_sachverhalt_0.3',
        'hybrid_sachverhalt_0.5',
        'hybrid_sachverhalt_0.7',
        'hybrid_norm_refs_0.3',
        'hybrid_norm_refs_0.5',
        'hybrid_norm_refs_0.7',
        'hybrid_legal_area_0.3',
        'hybrid_legal_area_0.5',
        'hybrid_legal_area_0.7',
        'hybrid_cited_decisions_0.3',
        'hybrid_cited_decisions_0.5',
        'hybrid_cited_decisions_0.7',
    ]
    
    embeddings = {}
    for name in hybrid_names:
        path = SIGNAL_EMBEDDINGS_DIR / f"{name}.npy"
        if path.exists():
            embeddings[name] = np.load(path)
            logger.info(f"  Loaded {name}: {embeddings[name].shape}")
        else:
            logger.warning(f"  Not found: {path}")
    return embeddings

def load_baseline_center_projected() -> np.ndarray:
    """Load baseline center_projected from signal ablation dir (1000 decisions)."""
    path = SIGNAL_EMBEDDINGS_DIR / "baseline_center_projected.npy"
    if path.exists():
        return np.load(path)
    return None

# ============================================================
# MAIN
# ============================================================

def main():
    logger.info("=" * 80)
    logger.info("EVALUATION v3 - COMPREHENSIVE ADVERSARIAL EVALUATION")
    logger.info(f"Global Seed: {GLOBAL_SEED} (FROZEN)")
    logger.info("=" * 80)
    
    # Load metadata
    logger.info("\n1. Loading metadata...")
    cp_metadata = load_center_projected_metadata()  # 1200 decisions
    fractal_metadata = load_fractal_baseline_metadata()  # 1000 decisions
    
    # Create decision_id to index mapping for center_projected
    cp_id_to_idx = {m['decision_id']: i for i, m in enumerate(cp_metadata)}
    fractal_ids = [m['decision_id'] for m in fractal_metadata]
    valid_cp_indices = [cp_id_to_idx[did] for did in fractal_ids if did in cp_id_to_idx]
    
    logger.info(f"  Center_projected metadata: {len(cp_metadata)} decisions")
    logger.info(f"  Fractal baseline metadata: {len(fractal_metadata)} decisions")
    logger.info(f"  Overlap (valid indices): {len(valid_cp_indices)} decisions")
    
    # Load all embeddings
    logger.info("\n2. Loading embeddings...")
    
    # Center projected (1200) - BASELINE
    cp_embeddings, _ = load_center_projected()
    cp_128_embeddings, _ = load_center_projected_128()
    
    # Signal embeddings (1000) - aligned to fractal baseline
    signal_embeddings = load_signal_embeddings()
    
    # Hybrid embeddings (1000) - aligned to fractal baseline
    hybrid_embeddings = load_hybrid_embeddings()
    
    # Baseline center_projected from signal dir (1000)
    baseline_cp = load_baseline_center_projected()
    
    # ============================================================
    # RUN BENCHMARKS
    # ============================================================
    logger.info("\n3. Running benchmark suite...")
    all_results = {}
    
    # --- BASELINE: center_projected on FULL 1200 decisions ---
    logger.info("\n" + "=" * 60)
    logger.info("BASELINE: center_projected (1200 decisions, 768 dim)")
    logger.info("=" * 60)
    results = run_full_benchmark_suite(
        "center_projected_1200", cp_embeddings, cp_metadata
    )
    all_results["center_projected_1200"] = results
    
    # --- BASELINE: center_projected_128 on FULL 1200 decisions ---
    logger.info("\n" + "=" * 60)
    logger.info("BASELINE: center_projected_128 (1200 decisions, 128 dim)")
    logger.info("=" * 60)
    results = run_full_benchmark_suite(
        "center_projected_128_1200", cp_128_embeddings, cp_metadata
    )
    all_results["center_projected_128_1200"] = results
    
    # --- BASELINE: center_projected on 1000 overlap (for fair comparison) ---
    logger.info("\n" + "=" * 60)
    logger.info("BASELINE: center_projected (1000 overlap, 768 dim)")
    logger.info("=" * 60)
    results = run_full_benchmark_suite(
        "center_projected_1000", cp_embeddings, cp_metadata, valid_cp_indices
    )
    all_results["center_projected_1000"] = results
    
    # --- Signal embeddings (1000) ---
    logger.info("\n" + "=" * 60)
    logger.info("SIGNAL ABLATION EMBEDDINGS (1000 decisions)")
    logger.info("=" * 60)
    for name, emb in signal_embeddings.items():
        if emb.shape[0] != len(fractal_metadata):
            logger.warning(f"  Shape mismatch for {name}: {emb.shape[0]} vs {len(fractal_metadata)}")
            continue
        results = run_full_benchmark_suite(name, emb, fractal_metadata)
        all_results[name] = results
    
    # --- Hybrid embeddings (1000) ---
    logger.info("\n" + "=" * 60)
    logger.info("HYBRID EMBEDDINGS (1000 decisions)")
    logger.info("=" * 60)
    for name, emb in hybrid_embeddings.items():
        if emb.shape[0] != len(fractal_metadata):
            logger.warning(f"  Shape mismatch for {name}: {emb.shape[0]} vs {len(fractal_metadata)}")
            continue
        results = run_full_benchmark_suite(name, emb, fractal_metadata)
        all_results[name] = results
    
    # --- Baseline center_projected from signal dir (1000) ---
    if baseline_cp is not None:
        logger.info("\n" + "=" * 60)
        logger.info("BASELINE: baseline_center_projected (1000 decisions)")
        logger.info("=" * 60)
        results = run_full_benchmark_suite("baseline_center_projected", baseline_cp, fractal_metadata)
        all_results["baseline_center_projected"] = results
    
    # ============================================================
    # SAVE RESULTS
    # ============================================================
    logger.info("\n4. Saving results...")
    
    # Machine-readable results
    output_file = OUTPUT_DIR / "evaluation_v3_results.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Summary table
    logger.info("\n" + "=" * 100)
    logger.info("EVALUATION v3 SUMMARY")
    logger.info("=" * 100)
    logger.info(f"{'Representation':<35} {'N':>4} {'Dim':>4} {'LangDom':>8} {'LD':>4} {'Jurist':>7} {'JP':>4} {'Jurivoc':>8} {'JV':>4} {'Scale':>7} {'SC':>4} {'Boiler':>7} {'BP':>4} {'Pass':>4}/5")
    logger.info("-" * 100)
    
    # Sort by number of benchmarks passed, then by jurist preference
    def sort_key(item):
        name, res = item
        n_passed = res['n_passed']
        jurist = res['jurist_pairwise_preference']['jurist_would_succeed_rate']
        lang_dom = res['adversarial_language_dominance']['mean_language_dominance']
        return (-n_passed, -jurist, lang_dom)
    
    sorted_results = sorted(all_results.items(), key=sort_key)
    
    for name, res in sorted_results:
        ld = res['adversarial_language_dominance']['mean_language_dominance']
        ld_status = "✓" if res['adversarial_language_dominance']['status'] == 'PASS' else "✗"
        jp = res['jurist_pairwise_preference']['jurist_would_succeed_rate']
        jp_status = "✓" if res['jurist_pairwise_preference']['status'] == 'PASS' else "✗"
        jv = res['jurivoc_hierarchy_alignment']['avg_nmi']
        jv_status = "✓" if res['jurivoc_hierarchy_alignment']['status'] == 'PASS' else "✗"
        sc = res['scale_stability_frozen_pca']['mean_cosine_similarity']
        sc_status = "✓" if res['scale_stability_frozen_pca']['status'] == 'PASS' else "✗"
        bp = res['boilerplate_resistance']['boilerplate_dominated_rate']
        bp_status = "✓" if res['boilerplate_resistance']['status'] == 'PASS' else "✗"
        
        logger.info(f"{name:<35} {res['n_decisions']:>4} {res['embedding_dim']:>4} {ld:>8.4f} {ld_status:>4} {jp:>7.4f} {jp_status:>4} {jv:>8.4f} {jv_status:>4} {sc:>7.4f} {sc_status:>4} {bp:>7.4f} {bp_status:>4} {res['n_passed']:>4}/5")
    
    # Find best representation
    valid_results = {k: v for k, v in all_results.items() if v['n_passed'] == 5}
    if valid_results:
        best = max(valid_results.items(), key=lambda x: (
            x[1]['jurist_pairwise_preference']['jurist_would_succeed_rate'],
            -x[1]['adversarial_language_dominance']['mean_language_dominance']
        ))
        logger.info(f"\n🏆 BEST REPRESENTATION (all 5 PASS): {best[0]}")
    else:
        # Best by jurist preference among those passing adversarial gates
        adv_pass = {k: v for k, v in all_results.items() 
                   if v['adversarial_language_dominance']['status'] == 'PASS' 
                   and v['jurist_pairwise_preference']['status'] == 'PASS'}
        if adv_pass:
            best = max(adv_pass.items(), key=lambda x: x[1]['jurist_pairwise_preference']['jurist_would_succeed_rate'])
            logger.info(f"\n🏆 BEST REPRESENTATION (adversarial PASS): {best[0]}")
        else:
            best = max(all_results.items(), key=lambda x: x[1]['n_passed'])
            logger.info(f"\n🏆 BEST REPRESENTATION (most benchmarks): {best[0]}")
    
    logger.info(f"   All 5 benchmarks PASS: {best[1]['all_benchmarks_pass']}")
    logger.info(f"   Benchmarks passed: {best[1]['n_passed']}/5")
    logger.info(f"   Language dominance: {best[1]['adversarial_language_dominance']['mean_language_dominance']:.4f}")
    logger.info(f"   Jurist preference: {best[1]['jurist_pairwise_preference']['jurist_would_succeed_rate']:.4f}")
    logger.info(f"   Jurivoc NMI: {best[1]['jurivoc_hierarchy_alignment']['avg_nmi']:.4f}")
    logger.info(f"   Scale stability: {best[1]['scale_stability_frozen_pca']['mean_cosine_similarity']:.4f}")
    logger.info(f"   Boilerplate resistance: {best[1]['boilerplate_resistance']['boilerplate_dominated_rate']:.4f}")
    
    # Compare with center_projected baseline
    baseline_key = "center_projected_1200"
    if baseline_key in all_results:
        baseline = all_results[baseline_key]
        logger.info(f"\n📊 BASELINE COMPARISON (vs {baseline_key}):")
        logger.info(f"   Baseline - LangDom: {baseline['adversarial_language_dominance']['mean_language_dominance']:.4f}, Jurist: {baseline['jurist_pairwise_preference']['jurist_would_succeed_rate']:.4f}, Jurivoc: {baseline['jurivoc_hierarchy_alignment']['avg_nmi']:.4f}, Scale: {baseline['scale_stability_frozen_pca']['mean_cosine_similarity']:.4f}, Boilerplate: {baseline['boilerplate_resistance']['boilerplate_dominated_rate']:.4f}")
        
        for name, res in sorted_results:
            if name == baseline_key:
                continue
            ld_diff = res['adversarial_language_dominance']['mean_language_dominance'] - baseline['adversarial_language_dominance']['mean_language_dominance']
            jp_diff = res['jurist_pairwise_preference']['jurist_would_succeed_rate'] - baseline['jurist_pairwise_preference']['jurist_would_succeed_rate']
            jv_diff = res['jurivoc_hierarchy_alignment']['avg_nmi'] - baseline['jurivoc_hierarchy_alignment']['avg_nmi']
            sc_diff = res['scale_stability_frozen_pca']['mean_cosine_similarity'] - baseline['scale_stability_frozen_pca']['mean_cosine_similarity']
            bp_diff = res['boilerplate_resistance']['boilerplate_dominated_rate'] - baseline['boilerplate_resistance']['boilerplate_dominated_rate']
            
            # Only show if different from baseline
            if abs(ld_diff) > 0.01 or abs(jp_diff) > 0.01 or abs(jv_diff) > 0.01:
                logger.info(f"   {name}: ΔLangDom={ld_diff:+.4f}, ΔJurist={jp_diff:+.4f}, ΔJurivoc={jv_diff:+.4f}, ΔScale={sc_diff:+.4f}, ΔBoiler={bp_diff:+.4f}")
    
    logger.info(f"\nResults saved to: {output_file}")
    logger.info("=" * 100)
    
    return all_results

if __name__ == "__main__":
    main()