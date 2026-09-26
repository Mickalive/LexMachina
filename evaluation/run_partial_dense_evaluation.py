#!/usr/bin/env python3
"""
Evaluation Lane - Partial Dense Embeddings Evaluation (Years 2000-2002)
Runs the formal benchmark suite on the year-split dense embeddings from legal-distance
as they land (currently 3/26 years = ~12,570 decisions).
"""

import json
import numpy as np
import logging
import time
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import Counter, defaultdict
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics import normalized_mutual_info_score, adjusted_rand_score
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# ============================================================
# FROZEN CONFIGURATION
# ============================================================
EVALUATION_VERSION = "v3_partial_dense"
GLOBAL_SEED = 42
FACTORY_DIRECTION_VERSION = 28

# Adversarial thresholds (FROZEN)
LANGUAGE_DOMINANCE_THRESHOLD = 0.85
JURIST_PAIRWISE_THRESHOLD = 0.5
CROSS_LANG_RECALL_THRESHOLD = 0.2
CLUSTER_COHERENCE_THRESHOLD = 0.7

# Benchmark parameters (FROZEN)
K_NEIGHBORS_LANG_DOM = 20
K_NEIGHBORS_JURIST = 10
K_NEIGHBORS_CROSS_LANG = 10
N_CLUSTERS_COHERENCE = 16

# Paths
DENSE_CHECKPOINTS_DIR = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/partial_dense_2000_2002")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Years available
AVAILABLE_YEARS = [2000, 2001, 2002]

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


def set_global_seed(seed: int = GLOBAL_SEED):
    np.random.seed(seed)


def load_year_data(year: int) -> Tuple[np.ndarray, List[Dict]]:
    """Load embeddings and metadata for a specific year."""
    emb_path = DENSE_CHECKPOINTS_DIR / f"embeddings_{year}.npy"
    meta_path = DENSE_CHECKPOINTS_DIR / f"metadata_{year}.json"
    
    embeddings = np.load(emb_path)
    with open(meta_path) as f:
        metadata = json.load(f)
    
    # Ensure branch is assigned
    for m in metadata:
        if 'branch' not in m or not m['branch'] or m['branch'] in ('null', None, ''):
            m['branch'] = assign_branch(m.get('chamber'))
        if 'language' not in m:
            m['language'] = m.get('language', 'de')
    
    return embeddings, metadata


def center_project(embeddings: np.ndarray, metadata: List[Dict]) -> np.ndarray:
    """Create center_projected embeddings by subtracting language centers."""
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


def project_to_dim(emb: np.ndarray, target_dim: int) -> np.ndarray:
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import normalize
    
    n_samples, n_features = emb.shape
    if n_features <= target_dim:
        if n_features < target_dim:
            padding = np.zeros((n_samples, target_dim - n_features))
            return np.concatenate([emb, padding], axis=1)
        return emb
    if n_samples < target_dim + 1:
        return emb[:, :target_dim]
    pca = PCA(n_components=target_dim, random_state=42)
    projected = pca.fit_transform(emb)
    return normalize(projected, norm='l2', axis=1)


def combine_years() -> Tuple[np.ndarray, List[Dict]]:
    """Combine embeddings and metadata from all available years."""
    all_embeddings = []
    all_metadata = []
    
    for year in AVAILABLE_YEARS:
        logger.info(f"Loading year {year}...")
        emb, meta = load_year_data(year)
        all_embeddings.append(emb)
        all_metadata.extend(meta)
        logger.info(f"  Year {year}: {emb.shape[0]} decisions, {emb.shape[1]} dims")
    
    combined_emb = np.vstack(all_embeddings)
    logger.info(f"Combined: {combined_emb.shape[0]} decisions, {combined_emb.shape[1]} dims")
    
    return combined_emb, all_metadata


def prepare_metadata(metadata: List[Dict]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[int], np.ndarray]:
    """Extract branch, language, chamber from metadata."""
    branches = []
    languages = []
    chambers = []
    valid_indices = []
    valid_mask = np.zeros(len(metadata), dtype=bool)
    
    for i, meta in enumerate(metadata):
        chamber = meta.get("chamber", "")
        branch = assign_branch(chamber)
        lang = meta.get("language", "unknown")
        
        if branch != "unknown":
            branches.append(branch)
            languages.append(lang)
            chambers.append(chamber)
            valid_indices.append(i)
            valid_mask[i] = True
    
    return np.array(branches), np.array(languages), np.array(chambers), valid_indices, valid_mask


# ============================================================
# ADVERSARIAL BENCHMARKS (EXACT k-NN)
# ============================================================

def adversarial_language_dominance(embeddings: np.ndarray, metadata: List[Dict], k: int = K_NEIGHBORS_LANG_DOM) -> Dict:
    nn = NearestNeighbors(n_neighbors=k+1, metric='cosine')
    nn.fit(embeddings)
    _, indices = nn.kneighbors(embeddings)
    neighbors = indices[:, 1:]
    
    dominance_rates = []
    for i, m in enumerate(metadata):
        lang = m.get('language', 'unknown')
        neighbor_langs = [metadata[n].get('language', 'unknown') for n in neighbors[i]]
        same_lang = sum(1 for l in neighbor_langs if l == lang)
        dominance_rates.append(same_lang / k)
    
    mean_dominance = np.mean(dominance_rates)
    
    return {
        'mean_language_dominance': float(mean_dominance),
        'std_language_dominance': float(np.std(dominance_rates)),
        'max_language_dominance': float(np.max(dominance_rates)),
        'k': k,
        'threshold': LANGUAGE_DOMINANCE_THRESHOLD,
        'status': 'PASS' if mean_dominance < LANGUAGE_DOMINANCE_THRESHOLD else 'FAIL',
        'note': 'Lower is better - language should not dominate neighbors'
    }


def simulate_pairwise_preference(
    embeddings: np.ndarray,
    branches: np.ndarray,
    languages: np.ndarray,
    k: int = K_NEIGHBORS_JURIST
) -> Dict:
    n = len(branches)
    
    nn = NearestNeighbors(n_neighbors=k+1, metric='cosine')
    nn.fit(embeddings)
    _, indices = nn.kneighbors(embeddings)
    neighbors = indices[:, 1:]
    
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
    
    jurist_correct = legal_relevant_count + both_count
    jurist_forced_wrong = language_artifact_count
    
    total = n
    legal_neighbor_rate = (legal_relevant_count + both_count) / total
    language_neighbor_rate = (language_artifact_count + both_count) / total
    
    return {
        "status": "PASS" if legal_neighbor_rate > JURIST_PAIRWISE_THRESHOLD else "FAIL",
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


def cross_language_neighbor_quality(embeddings: np.ndarray, metadata: List[Dict], k: int = 10) -> Dict:
    languages = [m.get('language', 'unknown') for m in metadata]
    branches = [m.get('branch', 'unknown') for m in metadata]
    
    nn = NearestNeighbors(n_neighbors=k+1, metric='cosine')
    nn.fit(embeddings)
    _, indices = nn.kneighbors(embeddings)
    neighbors = indices[:, 1:]
    
    cross_lang_same_branch = []
    same_lang_same_branch = []
    
    for i in range(len(embeddings)):
        lang_i = languages[i]
        branch_i = branches[i]
        
        cross_count = 0
        same_count = 0
        cross_total = 0
        same_total = 0
        
        for n_idx in neighbors[i]:
            lang_n = languages[n_idx]
            branch_n = branches[n_idx]
            
            if branch_n == branch_i:
                if lang_n != lang_i:
                    cross_total += 1
                    if lang_n != lang_i:
                        cross_count += 1
                else:
                    same_total += 1
                    if lang_n == lang_i:
                        same_count += 1
        
        if cross_total > 0:
            cross_lang_same_branch.append(cross_count / cross_total)
        if same_total > 0:
            same_lang_same_branch.append(same_count / same_total)
    
    return {
        'cross_lang_same_branch_mean': float(np.mean(cross_lang_same_branch)) if cross_lang_same_branch else 0.0,
        'same_lang_same_branch_mean': float(np.mean(same_lang_same_branch)) if same_lang_same_branch else 0.0,
        'invariance_gap': float(np.mean(same_lang_same_branch) - np.mean(cross_lang_same_branch)) if cross_lang_same_branch and same_lang_same_branch else 0.0,
        'status': 'PASS' if (cross_lang_same_branch and np.mean(cross_lang_same_branch) > 0.3) else 'FAIL',
    }


def zero_shot_cross_language_transfer(embeddings: np.ndarray, metadata: List[Dict], n_clusters: int = 16) -> Dict:
    languages = [m.get('language', 'unknown') for m in metadata]
    branches = [m.get('branch', 'unknown') for m in metadata]
    unique_langs = list(set(languages))
    
    if len(unique_langs) < 2:
        return {'status': 'SKIP', 'note': 'Need at least 2 languages'}
    
    nmi_scores = []
    
    for source_lang in unique_langs:
        for target_lang in unique_langs:
            if source_lang == target_lang:
                continue
            
            source_mask = np.array([l == source_lang for l in languages])
            target_mask = np.array([l == target_lang for l in languages])
            
            if np.sum(source_mask) < n_clusters or np.sum(target_mask) < n_clusters:
                continue
            
            source_emb = embeddings[source_mask]
            source_branches = np.array(branches)[source_mask]
            
            kmeans = KMeans(n_clusters=n_clusters, random_state=GLOBAL_SEED, n_init=10)
            source_labels = kmeans.fit_predict(source_emb)
            
            target_emb = embeddings[target_mask]
            target_branches = np.array(branches)[target_mask]
            
            target_labels = kmeans.predict(target_emb)
            
            source_nmi = normalized_mutual_info_score(source_branches, source_labels)
            target_nmi = normalized_mutual_info_score(target_branches, target_labels)
            
            nmi_scores.append({
                'source_lang': source_lang,
                'target_lang': target_lang,
                'source_nmi': source_nmi,
                'target_nmi': target_nmi,
                'transfer_gap': source_nmi - target_nmi
            })
    
    if not nmi_scores:
        return {'status': 'SKIP', 'note': 'Insufficient data per language'}
    
    zero_shot_mean = np.mean([s['target_nmi'] for s in nmi_scores])
    in_domain_mean = np.mean([s['source_nmi'] for s in nmi_scores])
    transfer_gap = in_domain_mean - zero_shot_mean
    
    return {
        'zero_shot_mean_nmi': float(zero_shot_mean),
        'in_domain_mean_nmi': float(in_domain_mean),
        'transfer_gap': float(transfer_gap),
        'status': 'PASS' if transfer_gap < 0.15 else 'FAIL',
        'details': nmi_scores
    }


def language_specific_representation_quality(embeddings: np.ndarray, metadata: List[Dict], n_clusters: int = 16) -> Dict:
    languages = [m.get('language', 'unknown') for m in metadata]
    branches = [m.get('branch', 'unknown') for m in metadata]
    unique_langs = list(set(languages))
    
    nmi_scores = []
    
    for lang in unique_langs:
        mask = np.array([l == lang for l in languages])
        if np.sum(mask) < n_clusters:
            continue
        
        lang_emb = embeddings[mask]
        lang_branches = np.array(branches)[mask]
        
        kmeans = KMeans(n_clusters=n_clusters, random_state=GLOBAL_SEED, n_init=10)
        labels = kmeans.fit_predict(lang_emb)
        
        nmi = normalized_mutual_info_score(lang_branches, labels)
        nmi_scores.append({'language': lang, 'nmi': float(nmi)})
    
    if not nmi_scores:
        return {'status': 'SKIP', 'note': 'Insufficient data per language'}
    
    mean_nmi = np.mean([s['nmi'] for s in nmi_scores])
    std_nmi = np.std([s['nmi'] for s in nmi_scores])
    
    return {
        'mean_nmi': float(mean_nmi),
        'std_nmi': float(std_nmi),
        'per_language': nmi_scores,
        'status': 'PASS' if mean_nmi > 0.4 else 'FAIL'
    }


def simulate_cluster_coherence_rating(
    embeddings: np.ndarray,
    branches: np.ndarray,
    languages: np.ndarray,
    n_clusters: int = N_CLUSTERS_COHERENCE
) -> Dict:
    kmeans = KMeans(n_clusters=n_clusters, random_state=GLOBAL_SEED, n_init=10)
    labels = kmeans.fit_predict(embeddings)
    
    branch_purities = []
    lang_purities = []
    
    for c in range(n_clusters):
        mask = labels == c
        if np.sum(mask) == 0:
            continue
        
        cluster_branches = branches[mask]
        cluster_langs = languages[mask]
        
        if len(cluster_branches) > 0:
            branch_counts = Counter(cluster_branches)
            branch_purity = max(branch_counts.values()) / len(cluster_branches)
            branch_purities.append(branch_purity)
        
        if len(cluster_langs) > 0:
            lang_counts = Counter(cluster_langs)
            lang_purity = max(lang_counts.values()) / len(cluster_langs)
            lang_purities.append(lang_purity)
    
    mean_purity = np.mean(branch_purities) if branch_purities else 0
    mean_lang_purity = np.mean(lang_purities) if lang_purities else 0
    
    nmi = normalized_mutual_info_score(branches, labels)
    
    return {
        "status": "PASS" if mean_purity > CLUSTER_COHERENCE_THRESHOLD else "FAIL",
        "n_clusters": n_clusters,
        "mean_branch_purity": round(float(mean_purity), 4),
        "branch_nmi": round(float(nmi), 4),
        "mean_language_purity": round(float(mean_lang_purity), 4),
        "cluster_purities": [round(p, 4) for p in branch_purities],
        "note": "Simulated jurist rates clusters by branch coherence. High branch purity = legally coherent clusters. High language purity = language-dominated clusters."
    }


def simulate_cross_language_retrieval(
    embeddings: np.ndarray,
    branches: np.ndarray,
    languages: np.ndarray,
    k: int = K_NEIGHBORS_CROSS_LANG
) -> Dict:
    unique_langs = list(set(languages))
    recalls = []
    
    nn = NearestNeighbors(n_neighbors=k+1, metric='cosine')
    nn.fit(embeddings)
    _, indices = nn.kneighbors(embeddings)
    neighbors = indices[:, 1:]
    
    for source_lang in unique_langs:
        source_mask = np.array([l == source_lang for l in languages])
        source_indices = np.where(source_mask)[0]
        
        if len(source_indices) == 0:
            continue
        
        for target_lang in unique_langs:
            if source_lang == target_lang:
                continue
            
            target_mask = np.array([l == target_lang for l in languages])
            target_indices = set(np.where(target_mask)[0])
            
            if len(target_indices) == 0:
                continue
            
            hits = 0
            for src_idx in source_indices:
                src_branch = branches[src_idx]
                neighbor_branches = branches[neighbors[src_idx]]
                neighbor_langs = languages[neighbors[src_idx]]
                
                for nb, nl in zip(neighbor_branches, neighbor_langs):
                    if nl == target_lang and nb == src_branch:
                        hits += 1
                        break
            
            recall = hits / len(source_indices) if len(source_indices) > 0 else 0
            recalls.append(recall)
    
    mean_recall = np.mean(recalls) if recalls else 0
    
    return {
        'mean_cross_language_recall_at_k': float(mean_recall),
        'status': 'PASS' if mean_recall > CROSS_LANG_RECALL_THRESHOLD else 'FAIL',
    }


def compute_jurivoc_alignment(embeddings: np.ndarray, metadata: List[Dict]) -> Dict:
    branches = [m.get('branch', 'unknown') for m in metadata]
    legal_areas = [m.get('legal_area', 'unknown') for m in metadata]
    legal_areas = [la if la and la != 'null' else 'unknown' for la in legal_areas]
    
    kmeans_l0 = KMeans(n_clusters=4, random_state=GLOBAL_SEED, n_init=10)
    labels_l0 = kmeans_l0.fit_predict(embeddings)
    nmi_l0 = normalized_mutual_info_score(branches, labels_l0)
    
    kmeans_l1 = KMeans(n_clusters=16, random_state=GLOBAL_SEED, n_init=10)
    labels_l1 = kmeans_l1.fit_predict(embeddings)
    nmi_l1 = normalized_mutual_info_score(legal_areas, labels_l1)
    
    nesting_score = 0.0
    for l0_cluster in range(4):
        mask = labels_l0 == l0_cluster
        if np.sum(mask) > 0:
            l1_subclusters = labels_l1[mask]
            subcluster_purities = []
            for sub in np.unique(l1_subclusters):
                sub_mask = (labels_l1 == sub)
                if np.sum(sub_mask) > 0:
                    branch_in_sub = [branches[i] for i in np.where(sub_mask)[0]]
                    majority = Counter(branch_in_sub).most_common(1)[0][1]
                    subcluster_purities.append(majority / len(branch_in_sub))
            if subcluster_purities:
                nesting_score += np.mean(subcluster_purities)
    nesting_score /= 4
    
    return {
        "level_0_nmi": float(nmi_l0),
        "level_1_nmi": float(nmi_l1),
        "nesting_score": float(nesting_score),
        "status": "PASS" if nmi_l0 > 0.3 and nmi_l1 > 0.2 else "FAIL",
        "note": "Jurivoc proxy: Level 0 = 4 branches, Level 1 = 16 legal areas. Higher NMI = better alignment with legal taxonomy."
    }


def compute_scale_stability(embeddings: np.ndarray, metadata: List[Dict]) -> Dict:
    n = embeddings.shape[0]
    if n < 100:
        return {"status": "SKIP", "note": "Insufficient decisions for scale stability test"}
    
    np.random.seed(GLOBAL_SEED)
    indices = np.arange(n)
    np.random.shuffle(indices)
    
    split_idx = int(0.8 * n)
    train_idx = indices[:split_idx]
    test_idx = indices[split_idx:]
    
    nn_full = NearestNeighbors(n_neighbors=11, metric='cosine')
    nn_full.fit(embeddings)
    _, full_neighbors = nn_full.kneighbors(embeddings)
    full_neighbors = full_neighbors[:, 1:]
    
    train_embeddings = embeddings[train_idx]
    train_to_full = {i: idx for i, idx in enumerate(train_idx)}
    
    nn_sub = NearestNeighbors(n_neighbors=11, metric='cosine')
    nn_sub.fit(train_embeddings)
    
    _, sub_neighbors = nn_sub.kneighbors(embeddings[test_idx])
    sub_neighbors = sub_neighbors[:, 1:]
    
    sub_neighbors_full = np.array([[train_to_full[n] for n in row] for row in sub_neighbors])
    
    overlaps = []
    for i, test_i in enumerate(test_idx):
        full_set = set(full_neighbors[test_i])
        sub_set = set(sub_neighbors_full[i])
        overlap = len(full_set & sub_set) / len(full_set)
        overlaps.append(overlap)
    
    mean_overlap = np.mean(overlaps)
    
    return {
        "mean_neighbor_overlap": float(mean_overlap),
        "std_neighbor_overlap": float(np.std(overlaps)),
        "n_test_points": len(test_idx),
        "status": "PASS" if mean_overlap > 0.5 else "FAIL",
        "note": "Scale stability: fraction of top-10 neighbors preserved when corpus reduced to 80%. Higher = more stable."
    }


def compute_boilerplate_resistance(embeddings: np.ndarray, metadata: List[Dict]) -> Dict:
    n = embeddings.shape[0]
    
    nn = NearestNeighbors(n_neighbors=11, metric='cosine')
    nn.fit(embeddings)
    _, indices = nn.kneighbors(embeddings)
    neighbors = indices[:, 1:]
    
    chambers = [m.get('chamber', 'unknown') for m in metadata]
    legal_areas = [m.get('legal_area', 'unknown') for m in metadata]
    legal_areas = [la if la and la != 'null' else 'unknown' for la in legal_areas]
    
    boilerplate_neighbors = 0
    legal_neighbors = 0
    total_comparisons = 0
    
    for i in range(n):
        chamber_i = chambers[i]
        legal_i = legal_areas[i]
        
        for j in neighbors[i]:
            chamber_j = chambers[j]
            legal_j = legal_areas[j]
            
            if chamber_i == chamber_j and legal_i != legal_j:
                boilerplate_neighbors += 1
                total_comparisons += 1
            elif chamber_i != chamber_j and legal_i == legal_j and legal_i != 'unknown':
                legal_neighbors += 1
                total_comparisons += 1
    
    boilerplate_rate = boilerplate_neighbors / total_comparisons if total_comparisons > 0 else 0
    legal_rate = legal_neighbors / total_comparisons if total_comparisons > 0 else 0
    
    resistance_score = legal_rate - boilerplate_rate
    
    return {
        "boilerplate_neighbor_rate": float(boilerplate_rate),
        "legal_neighbor_rate": float(legal_rate),
        "resistance_score": float(resistance_score),
        "total_comparisons": total_comparisons,
        "status": "PASS" if resistance_score > 0 else "FAIL",
        "note": "Boilerplate resistance: legal_neighbor_rate - boilerplate_neighbor_rate. Positive = legally relevant neighbors dominate over procedural neighbors."
    }


def run_fractal_quality(embeddings: np.ndarray, metadata: List[Dict]) -> Dict:
    branches_arr = np.array([m.get('branch', 'unknown') for m in metadata])
    languages_arr = np.array([m.get('language', 'unknown') for m in metadata])
    
    # Use sample for speed
    n_sample = min(10000, len(embeddings))
    if len(embeddings) > n_sample:
        np.random.seed(GLOBAL_SEED)
        sample_idx = np.random.choice(len(embeddings), n_sample, replace=False)
        emb_sample = embeddings[sample_idx]
        branches_sample = branches_arr[sample_idx]
        languages_sample = languages_arr[sample_idx]
    else:
        emb_sample = embeddings
        branches_sample = branches_arr
        languages_sample = languages_arr
    
    # Flat clustering
    n_clusters = N_CLUSTERS_COHERENCE
    kmeans = KMeans(n_clusters=n_clusters, random_state=GLOBAL_SEED, n_init=10)
    flat_labels = kmeans.fit_predict(emb_sample)
    
    flat_purity = 0
    for c in range(n_clusters):
        mask = flat_labels == c
        if mask.sum() == 0:
            continue
        gt = [branches_sample[i] for i in np.where(mask)[0]]
        gt = [b for b in gt if b != 'unknown']
        if gt:
            flat_purity += max(Counter(gt).values()) / len(gt)
    flat_purity /= n_clusters
    
    # Hierarchical (coarse=4, fine=16)
    kmeans_coarse = KMeans(n_clusters=4, random_state=GLOBAL_SEED, n_init=10)
    coarse_labels = kmeans_coarse.fit_predict(emb_sample)
    
    kmeans_fine = KMeans(n_clusters=16, random_state=GLOBAL_SEED, n_init=10)
    fine_labels = kmeans_fine.fit_predict(emb_sample)
    
    coarse_purity = 0
    for c in range(4):
        mask = coarse_labels == c
        if mask.sum() == 0:
            continue
        gt = [branches_sample[i] for i in np.where(mask)[0]]
        gt = [b for b in gt if b != 'unknown']
        if gt:
            coarse_purity += max(Counter(gt).values()) / len(gt)
    coarse_purity /= 4
    
    fine_purity = 0
    for c in range(16):
        mask = fine_labels == c
        if mask.sum() == 0:
            continue
        gt = [branches_sample[i] for i in np.where(mask)[0]]
        gt = [b for b in gt if b != 'unknown']
        if gt:
            fine_purity += max(Counter(gt).values()) / len(gt)
    fine_purity /= 16
    
    # Nesting
    nesting_violations = 0
    for c in range(16):
        mask = fine_labels == c
        if mask.sum() == 0:
            continue
        coarse_in_fine = coarse_labels[mask]
        if len(np.unique(coarse_in_fine)) > 1:
            nesting_violations += 1
    nesting_score = 1.0 - (nesting_violations / 16)
    
    # Legal area NMI
    legal_areas = [m.get('legal_area', 'unknown') for m in metadata]
    legal_areas = [la if la and la != 'null' else 'unknown' for la in legal_areas]
    if len(embeddings) > n_sample:
        legal_areas_sample = np.array(legal_areas)[sample_idx]
    else:
        legal_areas_sample = legal_areas
    legal_nmi = normalized_mutual_info_score(legal_areas_sample, fine_labels)
    
    # Cluster coherence
    coherence = simulate_cluster_coherence_rating(emb_sample, branches_sample, languages_sample)
    
    # Cross-language retrieval
    cross_lang = simulate_cross_language_retrieval(emb_sample, branches_sample, languages_sample)
    
    return {
        'n_coarse': 4,
        'n_fine': 16,
        'coarse_purity': float(coarse_purity),
        'fine_purity': float(fine_purity),
        'overall_improvement': float(fine_purity - coarse_purity),
        'improvement_rate': 0.0,  # Simplified for now
        'legal_area_nmi': float(legal_nmi),
        'flat_purity': float(flat_purity),
        'hierarchical_advantage': float(fine_purity - flat_purity),
        'cluster_coherence': coherence,
        'cross_language_retrieval': cross_lang,
    }


def evaluate_representation(name: str, embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Any]:
    logger.info(f"\n{'='*60}")
    logger.info(f"Evaluating: {name}")
    logger.info(f"Shape: {embeddings.shape}")
    logger.info(f"{'='*60}")
    
    start_time = time.time()
    
    branches, languages, chambers, valid_indices, valid_mask = prepare_metadata(metadata)
    rep_valid = embeddings[valid_indices]
    meta_valid = [metadata[i] for i in valid_indices]
    
    logger.info(f"Valid decisions (known branch): {len(rep_valid)} / {len(embeddings)}")
    
    # Adversarial benchmarks (EXACT k-NN on valid subset)
    logger.info("Running adversarial benchmarks (EXACT k-NN)...")
    lang_dom = adversarial_language_dominance(rep_valid, meta_valid)
    jurist_pref = simulate_pairwise_preference(rep_valid, branches, languages)
    adv_both_pass = lang_dom.get('status') == 'PASS' and jurist_pref.get('status') == 'PASS'
    
    # Cross-language benchmarks (EXACT k-NN on valid subset)
    logger.info("Running cross-language benchmarks (EXACT k-NN)...")
    cross_lang_nq = cross_language_neighbor_quality(rep_valid, meta_valid)
    zscl = zero_shot_cross_language_transfer(rep_valid, meta_valid)
    lsrq = language_specific_representation_quality(rep_valid, meta_valid)
    
    # Jurist usability (EXACT k-NN on valid subset)
    logger.info("Running jurist usability benchmarks (EXACT k-NN)...")
    cluster_coherence = simulate_cluster_coherence_rating(rep_valid, branches, languages)
    cross_lang_ret = simulate_cross_language_retrieval(rep_valid, branches, languages)
    zoom_task = {'status': 'SKIP', 'note': 'Requires hierarchical cluster assignments'}
    
    # Full-corpus scale benchmarks
    logger.info("Running full-corpus scale benchmarks...")
    jurivoc = compute_jurivoc_alignment(embeddings, metadata)
    scale_stab = compute_scale_stability(embeddings, metadata)
    boilerplate = compute_boilerplate_resistance(embeddings, metadata)
    
    # Fractal quality
    logger.info("Running fractal quality benchmarks...")
    fractal = run_fractal_quality(embeddings, metadata)
    
    duration = time.time() - start_time
    
    verdict = "PASS" if adv_both_pass else "FAIL"
    
    return {
        'name': name,
        'embedding_shape': list(embeddings.shape),
        'valid_decisions': len(rep_valid),
        'total_decisions': len(embeddings),
        'duration_seconds': duration,
        'adversarial': {
            'adversarial_language_dominance': lang_dom,
            'jurist_pairwise_preference': jurist_pref,
            'both_pass': adv_both_pass,
            'language_dominance_score': lang_dom.get('mean_language_dominance', 1.0),
            'jurist_preference_rate': jurist_pref.get('jurist_would_succeed_rate', 0.0),
        },
        'cross_language': {
            'cross_language_neighbor_quality': cross_lang_nq,
            'zero_shot_cross_language_transfer': zscl,
            'language_specific_representation_quality': lsrq,
        },
        'jurist_usability': {
            'cluster_coherence_rating': cluster_coherence,
            'zoom_task': zoom_task,
            'cross_language_retrieval': cross_lang_ret,
        },
        'full_corpus': {
            'jurivoc_alignment': jurivoc,
            'scale_stability': scale_stab,
            'boilerplate_resistance': boilerplate,
        },
        'fractal': fractal,
        'verdict': verdict,
        'both_adversarial_pass': adv_both_pass,
    }


def main():
    set_global_seed(GLOBAL_SEED)
    
    logger.info("=" * 70)
    logger.info(f"Evaluation Lane - Partial Dense Evaluation (Years {AVAILABLE_YEARS})")
    logger.info(f"Factory direction: v{FACTORY_DIRECTION_VERSION}")
    logger.info("=" * 70)
    
    # Combine years
    embeddings_raw, metadata = combine_years()
    
    # Create center_projected version
    logger.info("Creating center_projected version...")
    embeddings_cp = center_project(embeddings_raw, metadata)
    
    # Create 64-dim and 128-dim versions
    logger.info("Creating 64-dim version...")
    embeddings_cp_64 = project_to_dim(embeddings_cp, 64)
    
    logger.info("Creating 128-dim version...")
    embeddings_cp_128 = project_to_dim(embeddings_cp, 128)
    
    # Evaluate all versions
    representations = {
        'center_projected_768dim_partial': embeddings_cp,
        'center_projected_64dim_partial': embeddings_cp_64,
        'center_projected_128dim_partial': embeddings_cp_128,
    }
    
    all_results = {}
    
    for name, emb in representations.items():
        result = evaluate_representation(name, emb, metadata)
        all_results[name] = result
        
        # Log summary
        adv = result['adversarial']
        logger.info(f"  {name}: verdict={result['verdict']}, "
                   f"lang_dom={adv['language_dominance_score']:.4f} "
                   f"({'PASS' if adv['adversarial_language_dominance']['status']=='PASS' else 'FAIL'}), "
                   f"jurist_pref={adv['jurist_preference_rate']:.4f} "
                   f"({'PASS' if adv['jurist_pairwise_preference']['status']=='PASS' else 'FAIL'})")
    
    # Save results
    from datetime import datetime
    output_file = OUTPUT_DIR / f"evaluation_partial_dense_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Also save latest
    latest_file = OUTPUT_DIR / "evaluation_partial_dense_latest.json"
    with open(latest_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("PARTIAL DENSE EVALUATION SUMMARY (Years 2000-2002)")
    logger.info("=" * 80)
    
    for name, r in all_results.items():
        adv = r['adversarial']
        cross = r['cross_language']
        jurist = r['jurist_usability']
        full = r['full_corpus']
        fractal = r['fractal']
        
        logger.info(f"\n--- {name} ---")
        logger.info(f"Corpus: {r['valid_decisions']} valid / {r['total_decisions']} total decisions")
        logger.info(f"Duration: {r['duration_seconds']:.1f}s")
        logger.info(f"Verdict: {r['verdict']}")
        logger.info(f"Both adversarial pass: {r['both_adversarial_pass']}")
        
        logger.info(f"  Language Dominance: {adv['language_dominance_score']:.4f} ({adv['adversarial_language_dominance']['status']})")
        logger.info(f"  Jurist Pairwise: {adv['jurist_preference_rate']:.4f} ({adv['jurist_pairwise_preference']['status']})")
        logger.info(f"  Cross-Lang Neighbor Quality: gap={cross['cross_language_neighbor_quality'].get('invariance_gap', 'N/A'):.4f} ({cross['cross_language_neighbor_quality'].get('status', 'N/A')})")
        logger.info(f"  Zero-Shot Transfer: gap={cross['zero_shot_cross_language_transfer'].get('transfer_gap', 'N/A'):.4f} ({cross['zero_shot_cross_language_transfer'].get('status', 'N/A')})")
        logger.info(f"  Lang-Specific Quality: mean_nmi={cross['language_specific_representation_quality'].get('mean_nmi', 'N/A'):.4f} ({cross['language_specific_representation_quality'].get('status', 'N/A')})")
        logger.info(f"  Cluster Coherence: branch_purity={jurist['cluster_coherence_rating'].get('mean_branch_purity', 'N/A'):.4f} ({jurist['cluster_coherence_rating'].get('status', 'N/A')})")
        logger.info(f"  Cross-Lang Retrieval: recall={jurist['cross_language_retrieval'].get('mean_cross_language_recall_at_k', 'N/A'):.4f} ({jurist['cross_language_retrieval'].get('status', 'N/A')})")
        logger.info(f"  Jurivoc Level 0 NMI: {full['jurivoc_alignment']['level_0_nmi']:.4f}")
        logger.info(f"  Jurivoc Level 1 NMI: {full['jurivoc_alignment']['level_1_nmi']:.4f}")
        logger.info(f"  Nesting Score: {full['jurivoc_alignment']['nesting_score']:.4f}")
        logger.info(f"  Scale Stability: {full['scale_stability'].get('mean_neighbor_overlap', 'N/A'):.4f}")
        logger.info(f"  Boilerplate Resistance: {full['boilerplate_resistance']['resistance_score']:.4f}")
        logger.info(f"  Coarse Purity: {fractal.get('coarse_purity', 'N/A'):.4f}")
        logger.info(f"  Fine Purity: {fractal.get('fine_purity', 'N/A'):.4f}")
        logger.info(f"  Legal Area NMI: {fractal.get('legal_area_nmi', 'N/A'):.4f}")
        logger.info(f"  Hierarchical Advantage: {fractal.get('hierarchical_advantage', 'N/A'):.4f}")
    
    # Find best representation
    valid_results = {k: v for k, v in all_results.items() if 'error' not in v and v['both_adversarial_pass']}
    if valid_results:
        best = max(valid_results.items(), key=lambda x: (x[1]['adversarial']['jurist_preference_rate'],
                                                          -x[1]['adversarial']['language_dominance_score']))
        logger.info(f"\n🏆 BEST REPRESENTATION (passing both adversarial gates): {best[0]}")
    else:
        logger.info("\n⚠️  NO REPRESENTATION PASSES BOTH ADVERSARIAL GATES")
    
    logger.info(f"\nResults saved to: {output_file}")
    logger.info("=" * 80)
    
    return all_results


if __name__ == "__main__":
    main()