#!/usr/bin/env python3
"""
Evaluate 19k dense embeddings (years 2000-2002, ~19,441 decisions) using the formal suite.
This is the ACCEPTED subset from legal-distance lane (3/26 years, 11% of corpus).

Uses the frozen harness v3 thresholds with exact k-NN on stratified subsample (HNSW artifact fix).
"""

import json
import numpy as np
import logging
import time
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import Counter, defaultdict
from datetime import datetime
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics import normalized_mutual_info_score, adjusted_rand_score
from sklearn.cluster import KMeans

# Add paths for local modules
sys.path.insert(0, '/tmp/lex_accepted/legal-distance/evaluation')
from scalable_nn import (
    build_scalable_nn,
    batched_adversarial_language_dominance,
    batched_jurist_pairwise_preference,
    batched_cross_language_retrieval,
    batched_scale_stability,
    batched_boilerplate_resistance,
    batched_jurivoc_alignment,
    batched_cluster_coherence,
    K_NEIGHBORS_LANG_DOM,
    K_NEIGHBORS_JURIST,
    K_NEIGHBORS_CROSS_LANG,
)

# Import hierarchical Leiden from fractal-map
sys.path.insert(0, '/tmp/lex_accepted/fractal-map/fractal_map/hierarchical')
from hierarchical_leiden import hierarchical_leiden, compute_branch_purity

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
DENSE_CHECKPOINTS_DIR = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints")
FULL_METADATA_PATH = Path("/tmp/lex_accepted/legal-distance/evaluation/data/174k/metadata_174k.json")
CITATION_PAIRS_PATH = Path("/tmp/lex_accepted/legal-distance/evaluation/results/174k_citation_heritage/citation_pairs_174k.json")
OUTPUT_DIR = Path("/tmp/lex_accepted/legal-distance/evaluation/results/174k/dense_19k_formal_suite")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ACCEPTED years (3 years: 2000-2002)
ACCEPTED_YEARS = list(range(2000, 2003))

# CHAMBER_TO_BRANCH mapping
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
    if not chamber:
        return "unknown"
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


def load_full_metadata() -> List[Dict]:
    """Load full 174k metadata."""
    logger.info("Loading full 174k metadata...")
    with open(FULL_METADATA_PATH) as f:
        metadata = json.load(f)
    logger.info(f"Full metadata: {len(metadata)} decisions")
    return metadata


def load_dense_embeddings_subset(full_metadata: List[Dict], years: List[int]) -> Tuple[np.ndarray, List[Dict]]:
    """Load dense embeddings for specified years and assemble in full metadata order."""
    logger.info(f"Loading dense embeddings for years {years[0]}-{years[-1]}...")
    
    # Build decision_id -> index mapping for full metadata
    full_id_to_idx = {m['decision_id']: i for i, m in enumerate(full_metadata)}
    
    # Collect all decision_ids for the target years
    target_ids = set()
    year_meta = {}
    year_emb = {}
    
    for year in years:
        meta_path = DENSE_CHECKPOINTS_DIR / f"metadata_{year}.json"
        emb_path = DENSE_CHECKPOINTS_DIR / f"embeddings_{year}.npy"
        
        with open(meta_path) as f:
            meta = json.load(f)
        emb = np.load(emb_path)
        
        year_meta[year] = meta
        year_emb[year] = emb
        
        for m in meta:
            target_ids.add(m['decision_id'])
    
    logger.info(f"Total target decisions from checkpoints: {len(target_ids)}")
    
    # Filter full metadata to only target decisions, preserving order
    subset_metadata = []
    
    for m in full_metadata:
        if m['decision_id'] in target_ids:
            subset_metadata.append(m)
    
    logger.info(f"Subset metadata count (in full metadata order): {len(subset_metadata)}")
    
    # Build a lookup: decision_id -> (year, local_index)
    id_to_year_local = {}
    for year in years:
        meta = year_meta[year]
        for local_idx, m in enumerate(meta):
            id_to_year_local[m['decision_id']] = (year, local_idx)
    
    # Assemble embeddings
    dim = year_emb[years[0]].shape[1]
    embeddings_subset = np.zeros((len(subset_metadata), dim), dtype=np.float32)
    
    missing = 0
    for i, m in enumerate(subset_metadata):
        did = m['decision_id']
        if did in id_to_year_local:
            year, local_idx = id_to_year_local[did]
            embeddings_subset[i] = year_emb[year][local_idx]
        else:
            missing += 1
            logger.warning(f"Decision {did} not found in year embeddings")
    
    if missing > 0:
        logger.warning(f"Missing embeddings for {missing} decisions")
    
    logger.info(f"Assembled embeddings shape: {embeddings_subset.shape}")
    return embeddings_subset, subset_metadata


def language_center_projection(embeddings: np.ndarray, metadata: List[Dict]) -> np.ndarray:
    """Project each embedding to remove the component toward its language center."""
    languages = sorted(set(m.get('language', 'unknown') for m in metadata))
    
    # Compute language centers
    centers = {}
    for lang in languages:
        mask = np.array([m.get('language') == lang for m in metadata])
        if np.sum(mask) > 0:
            centers[lang] = embeddings[mask].mean(axis=0)
            logger.info(f"  {lang}: {np.sum(mask)} decisions, center norm={np.linalg.norm(centers[lang]):.4f}")
    
    # For each embedding, subtract its language center
    debiased = np.copy(embeddings)
    for i, m in enumerate(metadata):
        lang = m.get('language')
        if lang in centers:
            debiased[i] = embeddings[i] - centers[lang]
    
    # L2 normalize
    norms = np.linalg.norm(debiased, axis=1, keepdims=True)
    norms[norms == 0] = 1
    debiased = debiased / norms
    
    logger.info(f"Center projected shape: {debiased.shape}")
    logger.info(f"Norm stats: min={np.linalg.norm(debiased, axis=1).min():.6f}, max={np.linalg.norm(debiased, axis=1).max():.6f}, mean={np.linalg.norm(debiased, axis=1).mean():.6f}")
    
    return debiased


def apply_frozen_pca(embeddings: np.ndarray, n_components: int = 64, random_state: int = 42) -> Tuple[np.ndarray, PCA]:
    """Apply PCA fitted on the given embeddings (frozen for this dataset)."""
    logger.info(f"Fitting PCA: {embeddings.shape[1]} -> {n_components} dimensions...")
    pca = PCA(n_components=n_components, random_state=random_state)
    reduced = pca.fit_transform(embeddings)
    reduced = normalize(reduced, norm='l2', axis=1)
    
    explained_var = pca.explained_variance_ratio_.sum()
    logger.info(f"Explained variance ratio (top {n_components}): {explained_var:.4f}")
    
    return reduced, pca


def compute_branch_purity_per_cluster(labels, metadata):
    """Compute branch purity per cluster."""
    unique_labels = np.unique(labels[labels != -1])
    purities = {}
    
    for label in unique_labels:
        mask = labels == label
        cluster_branches = [metadata[i].get('branch') for i in np.where(mask)[0]]
        cluster_branches = [b for b in cluster_branches if b and b != 'null']
        
        if cluster_branches:
            most_common = Counter(cluster_branches).most_common(1)[0][1]
            purities[int(label)] = most_common / len(cluster_branches)
    
    return purities


def prepare_metadata(metadata: List[Dict]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[int]]:
    """Extract branch, language, chamber from metadata."""
    branches = []
    languages = []
    chambers = []
    valid_indices = []
    
    for i, meta in enumerate(metadata):
        chamber = meta.get("chamber", "")
        branch = assign_branch(chamber)
        lang = meta.get("language", "unknown")
        
        if branch != "unknown":
            branches.append(branch)
            languages.append(lang)
            chambers.append(chamber)
            valid_indices.append(i)
    
    return np.array(branches), np.array(languages), np.array(chambers), valid_indices


def run_fractal_quality_benchmarks(embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Any]:
    """Run fractal-map quality benchmarks (hierarchical Leiden, zoom coherence)."""
    n_metadata = len(metadata)
    if embeddings.shape[0] != n_metadata:
        if embeddings.shape[0] > n_metadata:
            embeddings = embeddings[:n_metadata]
        else:
            logger.warning(f"Embeddings ({embeddings.shape[0]}) < metadata ({n_metadata}), skipping fractal benchmarks")
            return {
                'n_coarse': 0, 'n_fine': 0, 'coarse_purity': 0.0, 'fine_purity': 0.0,
                'overall_improvement': 0.0, 'improvement_rate': 0.0,
                'legal_area_nmi': 0.0, 'flat_purity': 0.0, 'hierarchical_advantage': 0.0,
                'cluster_coherence': {'status': 'SKIP', 'note': 'embedding/metadata length mismatch'},
                'cross_language_retrieval': {'status': 'SKIP', 'note': 'embedding/metadata length mismatch'},
            }
    
    # Run hierarchical Leiden
    logger.info("Running hierarchical Leiden...")
    result = hierarchical_leiden(embeddings, metadata, coarse_res=0.5, sub_res=3.0)
    hierarchical_labels, coarse_labels, cluster_info = result
    
    # Build coarse_to_fine mapping from cluster_info
    coarse_to_fine = defaultdict(list)
    for sub_id, info in cluster_info.items():
        if not info.get('too_small', False):
            coarse_id = info['coarse_id']
            coarse_to_fine[coarse_id].append(sub_id)
    
    n_fine = len(set(hierarchical_labels[hierarchical_labels != -1]))
    n_coarse = len(set(coarse_labels[coarse_labels != -1]))
    
    coarse_purities = compute_branch_purity_per_cluster(coarse_labels, metadata)
    coarse_overall = compute_branch_purity(coarse_labels, metadata)
    
    fine_purities = compute_branch_purity_per_cluster(hierarchical_labels, metadata)
    fine_overall = compute_branch_purity(hierarchical_labels, metadata)
    
    total_improvements = 0
    total_deteriorations = 0
    total_no_change = 0
    
    for coarse_id in sorted(coarse_to_fine.keys()):
        fine_ids = coarse_to_fine[coarse_id]
        if not fine_ids:
            continue
        coarse_pur = coarse_purities.get(coarse_id, 0)
        fine_purs = [fine_purities.get(fid, 0) for fid in fine_ids]
        improvements = sum(1 for fp in fine_purs if fp > coarse_pur + 0.01)
        deteriorations = sum(1 for fp in fine_purs if fp < coarse_pur - 0.01)
        no_change = len(fine_purs) - improvements - deteriorations
        total_improvements += improvements
        total_deteriorations += deteriorations
        total_no_change += no_change
    
    overall_improvement = fine_overall - coarse_overall
    total_fine = total_improvements + total_deteriorations + total_no_change
    improvement_rate = total_improvements / total_fine if total_fine > 0 else 0
    
    # Legal area NMI
    legal_areas = [metadata[i].get('legal_area', '') for i in range(len(metadata))]
    legal_areas = [la if la else 'unknown' for la in legal_areas]
    nmi = normalized_mutual_info_score(legal_areas, hierarchical_labels)
    
    # Flat Leiden comparison
    flat_result = hierarchical_leiden(embeddings, metadata, coarse_res=3.0, sub_res=0.5)
    flat_labels = flat_result[0]
    flat_purity = compute_branch_purity(flat_labels, metadata)
    hierarchical_advantage = fine_overall - flat_purity
    
    # Jurist cluster coherence
    branches_arr = np.array([m.get('branch', 'unknown') for m in metadata])
    languages_arr = np.array([m.get('language', 'unknown') for m in metadata])
    cluster_coherence = batched_cluster_coherence(embeddings, branches_arr, languages_arr, n_clusters=16)
    
    # Cross-language retrieval
    cross_lang = batched_cross_language_retrieval(
        build_scalable_nn(embeddings, n_neighbors=max(K_NEIGHBORS_LANG_DOM, K_NEIGHBORS_JURIST, K_NEIGHBORS_CROSS_LANG), force_exact=True),
        metadata, branches_arr, languages_arr
    )
    
    return {
        'n_coarse': n_coarse,
        'n_fine': n_fine,
        'coarse_purity': float(coarse_overall),
        'fine_purity': float(fine_overall),
        'overall_improvement': float(overall_improvement),
        'improvement_rate': float(improvement_rate),
        'legal_area_nmi': float(nmi),
        'flat_purity': float(flat_purity),
        'hierarchical_advantage': float(hierarchical_advantage),
        'cluster_coherence': cluster_coherence,
        'cross_language_retrieval': cross_lang,
    }


def run_full_corpus_benchmarks(embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Any]:
    """Run full-corpus benchmarks using scalable NN."""
    logger.info("Running full-corpus benchmarks...")
    
    # Build scalable NN index (force exact for consistency with 174k formal suite)
    nn_index = build_scalable_nn(embeddings, n_neighbors=max(K_NEIGHBORS_LANG_DOM, K_NEIGHBORS_JURIST, K_NEIGHBORS_CROSS_LANG), force_exact=True)
    
    # Citation heritage (run separately)
    citation_heritage = {
        'status': 'RUN_SEPARATELY',
        'note': 'Run via validate_citation_heritage_174k.py on frozen 137k pair pool'
    }
    
    # Temporal stability
    logger.info("Running temporal stability...")
    scale_results = batched_scale_stability(embeddings, metadata)
    
    # Hierarchy coherence (Jurivoc alignment)
    logger.info("Running hierarchy coherence...")
    hierarchy_results = batched_jurivoc_alignment(embeddings, metadata)
    
    # Cluster coherence
    logger.info("Running cluster coherence...")
    branches = np.array([m.get('branch', 'unknown') for m in metadata])
    languages = np.array([m.get('language', 'unknown') for m in metadata])
    cluster_coherence = batched_cluster_coherence(embeddings, branches, languages, n_clusters=16)
    
    # Cross-language retrieval full
    logger.info("Running cross-language retrieval full...")
    cross_lang_full = batched_cross_language_retrieval(nn_index, metadata, branches, languages)
    
    # Boilerplate resistance
    logger.info("Running boilerplate resistance...")
    boilerplate_results = batched_boilerplate_resistance(nn_index, metadata)
    
    return {
        'citation_heritage': citation_heritage,
        'temporal_stability': scale_results,
        'hierarchy_coherence': hierarchy_results,
        'cluster_coherence': cluster_coherence,
        'cross_language_retrieval_full': cross_lang_full,
        'boilerplate_resistance': boilerplate_results,
    }


def run_cross_language_benchmarks(embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Any]:
    """Run cross-language benchmarks."""
    logger.info("Running cross-language benchmarks...")
    
    # Use exact k-NN for consistency
    nn_index = build_scalable_nn(embeddings, n_neighbors=max(K_NEIGHBORS_LANG_DOM, K_NEIGHBORS_JURIST, K_NEIGHBORS_CROSS_LANG), force_exact=True)
    
    branches, languages, _, valid_indices = prepare_metadata(metadata)
    rep_valid = embeddings[valid_indices]
    meta_valid = [metadata[i] for i in valid_indices]
    
    # Cross-language neighbor quality
    # Compute similarities between cross-language same-branch pairs
    from collections import defaultdict
    
    branch_lang_groups = defaultdict(list)
    for i, (b, l) in enumerate(zip(branches, languages)):
        branch_lang_groups[(b, l)].append(i)
    
    cross_lang_same_branch = []
    same_lang_same_branch = []
    cross_branch = []
    
    for i in range(len(meta_valid)):
        branch_i = branches[i]
        lang_i = languages[i]
        
        # Find same-branch different-language decisions
        for other_lang in ['de', 'fr', 'it']:
            if other_lang != lang_i:
                key = (branch_i, other_lang)
                if key in branch_lang_groups:
                    for j in branch_lang_groups[key]:
                        if j <= i:
                            continue
                        sim = np.dot(rep_valid[i], rep_valid[j])
                        cross_lang_same_branch.append(sim)
        
        # Find same-branch same-language decisions
        key = (branch_i, lang_i)
        if key in branch_lang_groups:
            for j in branch_lang_groups[key]:
                if j <= i:
                    continue
                sim = np.dot(rep_valid[i], rep_valid[j])
                same_lang_same_branch.append(sim)
        
        # Find cross-branch decisions (sample)
        for other_branch in ['oeffentliches_recht', 'zivilrecht', 'strafrecht', 'sozialversicherungsrecht']:
            if other_branch != branch_i:
                for other_lang in ['de', 'fr', 'it']:
                    key = (other_branch, other_lang)
                    if key in branch_lang_groups:
                        for j in branch_lang_groups[key][:5]:  # Sample 5 per branch-lang
                            sim = np.dot(rep_valid[i], rep_valid[j])
                            cross_branch.append(sim)
                            break
                        break
    
    cross_lang_same_branch_mean = float(np.mean(cross_lang_same_branch)) if cross_lang_same_branch else 0.0
    same_lang_same_branch_mean = float(np.mean(same_lang_same_branch)) if same_lang_same_branch else 0.0
    cross_branch_mean = float(np.mean(cross_branch)) if cross_branch else 0.0
    invariance_gap = cross_lang_same_branch_mean - same_lang_same_branch_mean
    separation = cross_lang_same_branch_mean - cross_branch_mean
    
    # Zero-shot cross-language transfer
    # Train KMeans on one language, test on another
    zero_shot_results = {}
    for train_lang in ['fr', 'de', 'it']:
        for test_lang in ['fr', 'de', 'it']:
            train_mask = languages == train_lang
            test_mask = languages == test_lang
            
            if np.sum(train_mask) < 50 or np.sum(test_mask) < 50:
                continue
            
            kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
            kmeans.fit(rep_valid[train_mask])
            test_labels = kmeans.predict(rep_valid[test_mask])
            true_branches_test = branches[test_mask]
            
            nmi = normalized_mutual_info_score(true_branches_test, test_labels)
            ari = adjusted_rand_score(true_branches_test, test_labels)
            
            zero_shot_results[f"{train_lang}->{test_lang}"] = {
                'train_lang': train_lang,
                'test_lang': test_lang,
                'zero_shot': train_lang != test_lang,
                'nmi': float(nmi),
                'ari': float(ari),
                'test_size': int(np.sum(test_mask))
            }
    
    zero_shot_nmi = [r['nmi'] for r in zero_shot_results.values() if r['zero_shot']]
    in_domain_nmi = [r['nmi'] for r in zero_shot_results.values() if not r['zero_shot']]
    zero_shot_mean_nmi = float(np.mean(zero_shot_nmi)) if zero_shot_nmi else 0.0
    in_domain_mean_nmi = float(np.mean(in_domain_nmi)) if in_domain_nmi else 0.0
    transfer_gap = zero_shot_mean_nmi - in_domain_mean_nmi
    
    # Language-specific representation quality
    lang_quality = {}
    for lang in ['fr', 'de', 'it']:
        lang_mask = languages == lang
        if np.sum(lang_mask) < 10:
            continue
        lang_embeddings = rep_valid[lang_mask]
        lang_branches = branches[lang_mask]
        kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
        labels = kmeans.fit_predict(lang_embeddings)
        nmi = normalized_mutual_info_score(lang_branches, labels)
        ari = adjusted_rand_score(lang_branches, labels)
        lang_quality[lang] = {
            'n_decisions': int(np.sum(lang_mask)),
            'branch_nmi': float(nmi),
            'branch_ari': float(ari),
            'n_branches': 4
        }
    
    mean_nmi = float(np.mean([v['branch_nmi'] for v in lang_quality.values()])) if lang_quality else 0.0
    std_nmi = float(np.std([v['branch_nmi'] for v in lang_quality.values()])) if lang_quality else 0.0
    min_nmi = float(np.min([v['branch_nmi'] for v in lang_quality.values()])) if lang_quality else 0.0
    max_nmi = float(np.max([v['branch_nmi'] for v in lang_quality.values()])) if lang_quality else 0.0
    
    return {
        'cross_language_neighbor_quality': {
            'cross_lang_same_branch_mean': cross_lang_same_branch_mean,
            'same_lang_same_branch_mean': same_lang_same_branch_mean,
            'cross_branch_mean': cross_branch_mean,
            'invariance_gap': invariance_gap,
            'separation': separation,
            'k': K_NEIGHBORS_CROSS_LANG
        },
        'zero_shot_cross_language_transfer': {
            'pairwise_results': zero_shot_results,
            'zero_shot_mean_nmi': zero_shot_mean_nmi,
            'in_domain_mean_nmi': in_domain_mean_nmi,
            'transfer_gap': transfer_gap,
            'status': 'PASS' if zero_shot_mean_nmi > 0.1 else 'FAIL'
        },
        'language_specific_representation_quality': {
            'per_language': lang_quality,
            'mean_nmi': mean_nmi,
            'std_nmi': std_nmi,
            'min_nmi': min_nmi,
            'max_nmi': max_nmi,
            'status': 'PASS' if mean_nmi > 0.1 else 'FAIL'
        }
    }


def run_adversarial_benchmarks(embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Any]:
    """Run the two critical adversarial benchmarks using exact k-NN on stratified subsample."""
    logger.info("Running adversarial benchmarks (exact k-NN on stratified subsample)...")
    
    # Prepare metadata
    branches, languages, chambers, valid_indices = prepare_metadata(metadata)
    rep_valid = embeddings[valid_indices]
    meta_valid = [metadata[i] for i in valid_indices]
    
    # Use exact k-NN on full valid set (for 19k scale, exact is feasible)
    # The 174k formal suite uses exact on 2000 subsample; for 19k we can use exact on all
    nn_index = build_scalable_nn(rep_valid, n_neighbors=max(K_NEIGHBORS_LANG_DOM, K_NEIGHBORS_JURIST, K_NEIGHBORS_CROSS_LANG), force_exact=True)
    
    # 1. Adversarial language dominance
    lang_dom = batched_adversarial_language_dominance(nn_index, meta_valid)
    
    # 2. Jurist pairwise preference
    jurist_pref = batched_jurist_pairwise_preference(nn_index, meta_valid, branches, languages)
    
    return {
        'adversarial_language_dominance': lang_dom,
        'jurist_pairwise_preference': jurist_pref,
        'both_pass': lang_dom.get('status') == 'PASS' and jurist_pref.get('status') == 'PASS',
        'language_dominance_score': lang_dom.get('mean_language_dominance', 1.0),
        'jurist_preference_rate': jurist_pref.get('jurist_would_succeed_rate', 0.0),
        'backend': 'sklearn_exact',
        'subset_size': len(meta_valid),
        'note': 'EXACT k-NN on full valid subset (19k scale permits exact computation)'
    }


def run_jurist_usability_benchmarks(embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Any]:
    """Run jurist usability benchmarks."""
    logger.info("Running jurist usability benchmarks...")
    
    branches = np.array([m.get('branch', 'unknown') for m in metadata])
    languages = np.array([m.get('language', 'unknown') for m in metadata])
    
    # Cluster coherence rating
    cluster_coherence = batched_cluster_coherence(embeddings, branches, languages, n_clusters=16)
    
    # Cross-language retrieval
    nn_index = build_scalable_nn(embeddings, n_neighbors=max(K_NEIGHBORS_LANG_DOM, K_NEIGHBORS_JURIST, K_NEIGHBORS_CROSS_LANG), force_exact=True)
    cross_lang = batched_cross_language_retrieval(nn_index, metadata, branches, languages)
    
    return {
        'cluster_coherence_rating': cluster_coherence,
        'zoom_task': {
            'status': 'SKIP',
            'note': 'Requires hierarchical cluster assignments'
        },
        'cross_language_retrieval': cross_lang
    }


def evaluate_representation(name: str, embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Any]:
    """Evaluate a single representation against all benchmarks (formal suite)."""
    logger.info(f"\n{'='*70}")
    logger.info(f"Evaluating: {name}")
    logger.info(f"Shape: {embeddings.shape}")
    logger.info(f"{'='*70}")
    
    start_time = time.time()
    
    # 1. Adversarial benchmarks
    adv_results = run_adversarial_benchmarks(embeddings, metadata)
    
    # 2. Cross-language benchmarks
    cross_lang_results = run_cross_language_benchmarks(embeddings, metadata)
    
    # 3. Jurist usability benchmarks
    jurist_results = run_jurist_usability_benchmarks(embeddings, metadata)
    
    # 4. Fractal quality benchmarks
    fractal_results = run_fractal_quality_benchmarks(embeddings, metadata)
    
    # 5. Full-corpus benchmarks
    full_corpus_results = run_full_corpus_benchmarks(embeddings, metadata)
    
    duration = time.time() - start_time
    
    # Overall verdict
    both_pass = adv_results['both_pass']
    verdict = "PASS" if both_pass else "FAIL"
    
    return {
        'name': name,
        'embedding_shape': list(embeddings.shape),
        'duration_seconds': duration,
        'adversarial': adv_results,
        'cross_language': cross_lang_results,
        'jurist_usability': jurist_results,
        'fractal': fractal_results,
        'full_corpus': full_corpus_results,
        'verdict': verdict,
        'both_adversarial_pass': both_pass,
    }


def save_pca_model(pca: PCA, output_path: Path, name: str):
    """Save PCA model info for reproducibility."""
    pca_info = {
        'name': name,
        'n_components': pca.n_components_,
        'original_dim': pca.n_features_in_,
        'explained_variance_ratio': pca.explained_variance_ratio_.tolist(),
        'explained_variance_ratio_sum': float(pca.explained_variance_ratio_.sum()),
        'random_state': 42,
        'mean': pca.mean_.tolist(),
        'components_shape': pca.components_.shape,
    }
    with open(output_path, 'w') as f:
        json.dump(pca_info, f, indent=2)
    logger.info(f"Saved PCA model to {output_path}")


def main():
    logger.info("=" * 70)
    logger.info(f"Evaluating 19k Dense Embeddings (ACCEPTED years: 2000-2002)")
    logger.info(f"Using formal suite with exact k-NN (HNSW artifact fix)")
    logger.info("=" * 70)
    
    # Load full metadata
    logger.info("Loading full 174k metadata...")
    full_metadata = load_full_metadata()
    
    # Load and assemble dense embeddings for ACCEPTED years
    embeddings_768, subset_metadata = load_dense_embeddings_subset(full_metadata, ACCEPTED_YEARS)
    
    # Step 1: Apply language-center projection
    logger.info("\n=== Step 1: Language-Center Projection ===")
    embeddings_center_projected = language_center_projection(embeddings_768, subset_metadata)
    
    # Step 2: Apply frozen PCA to get 64-dim version
    logger.info("\n=== Step 2: Frozen PCA (768 -> 64 dim) ===")
    embeddings_64, pca_64 = apply_frozen_pca(embeddings_center_projected, n_components=64, random_state=42)
    save_pca_model(pca_64, OUTPUT_DIR / "pca_model_19k_64.json", "center_projected_64dim_19k")
    
    # Step 3: Apply frozen PCA to get 128-dim version
    logger.info("\n=== Step 3: Frozen PCA (768 -> 128 dim) ===")
    embeddings_128, pca_128 = apply_frozen_pca(embeddings_center_projected, n_components=128, random_state=42)
    save_pca_model(pca_128, OUTPUT_DIR / "pca_model_19k_128.json", "center_projected_128dim_19k")
    
    # Step 4: Evaluate all versions
    results = {}
    
    # Evaluate raw 768-dim for comparison
    logger.info("\n=== Evaluating raw 768-dim (baseline) ===")
    results['raw_768dim'] = evaluate_representation("multilingual_e5_768dim_19k", embeddings_768, subset_metadata)
    
    # Evaluate center_projected 768-dim
    logger.info("\n=== Evaluating center_projected 768-dim ===")
    results['center_projected_768dim'] = evaluate_representation("center_projected_768dim_19k", embeddings_center_projected, subset_metadata)
    
    # Evaluate center_projected 64-dim
    logger.info("\n=== Evaluating center_projected 64-dim ===")
    results['center_projected_64dim'] = evaluate_representation("center_projected_64dim_19k", embeddings_64, subset_metadata)
    
    # Evaluate center_projected 128-dim
    logger.info("\n=== Evaluating center_projected 128-dim ===")
    results['center_projected_128dim'] = evaluate_representation("center_projected_128dim_19k", embeddings_128, subset_metadata)
    
    # Save all results
    output_file = OUTPUT_DIR / f"evaluation_19k_dense_formal_suite_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Also save latest
    latest_file = OUTPUT_DIR / "evaluation_19k_dense_formal_suite_latest.json"
    with open(latest_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Generate summary report
    logger.info("\n" + "=" * 100)
    logger.info("EVALUATION 19k DENSE FORMAL SUITE - SUMMARY (HNSW ARTIFACT FIXED)")
    logger.info("=" * 100)
    
    logger.info(f"\n{'Representation':<35} {'Verdict':<7} {'LangDom':>7} {'LD-P':>4} {'Jurist':>7} {'JP-P':>4} {'Both':>4} {'Backend':>10}")
    logger.info("-" * 85)
    
    def sort_key(item):
        name, res = item
        if 'error' in res:
            return (0, 0, 1.0)
        both = res['both_adversarial_pass']
        jurist = res['adversarial']['jurist_preference_rate']
        lang_dom = res['adversarial']['language_dominance_score']
        return (both, jurist, -lang_dom)
    
    sorted_results = sorted(results.items(), key=sort_key, reverse=True)
    
    for name, res in sorted_results:
        if 'error' in res:
            logger.info(f"{name:<35} {'ERROR':<7} {'N/A':>7} {'N/A':>4} {'N/A':>7} {'N/A':>4} {'N/A':>4} {'N/A':>10}")
            continue
        
        adv = res['adversarial']
        ld = adv['language_dominance_score']
        jp = adv['jurist_preference_rate']
        ld_pass = "✓" if adv['adversarial_language_dominance']['status'] == 'PASS' else "✗"
        jp_pass = "✓" if adv['jurist_pairwise_preference']['status'] == 'PASS' else "✗"
        both = "✓" if adv['both_pass'] else "✗"
        backend = adv.get('backend', 'N/A')
        
        logger.info(f"{name:<35} {res['verdict']:<7} {ld:>7.4f} {ld_pass:>4} {jp:>7.4f} {jp_pass:>4} {both:>4} {backend:>10}")
    
    # Find best representation (must pass both adversarial gates)
    valid_results = {k: v for k, v in results.items() if 'error' not in v and v['both_adversarial_pass']}
    if valid_results:
        best = max(valid_results.items(), key=lambda x: (x[1]['adversarial']['jurist_preference_rate'],
                                                         -x[1]['adversarial']['language_dominance_score']))
        logger.info(f"\n🏆 BEST REPRESENTATION (passing both adversarial gates): {best[0]}")
        logger.info(f"   Language dominance: {best[1]['adversarial']['language_dominance_score']:.4f}")
        logger.info(f"   Jurist preference: {best[1]['adversarial']['jurist_preference_rate']:.4f}")
        logger.info(f"   Backend: {best[1]['adversarial'].get('backend', 'N/A')}")
        logger.info(f"   Valid subset size: {best[1]['adversarial'].get('subset_size', 'N/A')}")
    else:
        logger.info("\n⚠️  NO REPRESENTATION PASSES BOTH ADVERSARIAL GATES")
    
    logger.info(f"\nResults saved to: {output_file}")
    logger.info("=" * 100)
    
    return results


if __name__ == "__main__":
    main()