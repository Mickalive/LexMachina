#!/usr/bin/env python3
"""
Evaluation v10 - Cross-Lingual Alignment Deeper Investigation on Frozen Harness v3

Factory Direction v8 Evaluation Lane Question (Objective 5):
"Cross-lingual alignment deeper investigation — develop better cross-lingual alignment 
methods (beyond PCA), test if metric learning representations improve language invariance, 
evaluate section-specific embeddings (sachverhalt, erwaegungen, dispositiv) for 
cross-lingual coherence."

This script evaluates:
1. Section-specific TF-IDF embeddings (sachverhalt, erwaegungen, dispositiv, outcome)
2. Cross-lingual alignment methods on cited_decisions_tfidf base:
   - Mean Center (language-wise centering)
   - Joint PCA (concatenated language embeddings)
   - Procrustes (pairwise alignment)
   - Proc Pairs (Procrustes on language-paired decisions) - v8 winner
3. PCA-reduced versions and hybrids with "center_projected" equivalent
4. Hybrids of best cross-lingual aligned cited_decisions_tfidf with outcome signal

All evaluated against frozen evaluation harness v3 (seed=42, config_hash=4323f833fa72366a).
"""

import json
import numpy as np
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from collections import Counter, defaultdict
import sys
import time
import os
import hashlib
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics import normalized_mutual_info_score
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.linalg import orthogonal_procrustes

# Module-level logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# ============================================================
# FROZEN CONFIGURATION - MUST MATCH evaluation_v3_harness.py
# ============================================================
EVALUATION_VERSION = "v3"
GLOBAL_SEED = 42
FACTORY_DIRECTION_VERSION = 8

# Adversarial thresholds (frozen - DO NOT CHANGE)
LANGUAGE_DOMINANCE_THRESHOLD = 0.85
JURIST_PAIRWISE_THRESHOLD = 0.5
CROSS_LANG_RECALL_THRESHOLD = 0.2
CLUSTER_COHERENCE_THRESHOLD = 0.7

# Benchmark parameters (frozen)
K_NEIGHBORS_LANG_DOM = 20
K_NEIGHBORS_JURIST = 10
K_NEIGHBORS_CROSS_LANG = 10
N_CLUSTERS_COHERENCE = 16

REPO_ROOT = Path("/home/runner/work/LexMachina/LexMachina")

# Chamber to branch mapping (frozen)
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

def load_metadata_1200() -> List[Dict]:
    """Load the 1200-decision expanded slice metadata."""
    metadata_path = REPO_ROOT / "evaluation/data/bger_expanded_1200_metadata.jsonl"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata not found at {metadata_path}")
    
    metadata = []
    with open(metadata_path, 'r') as f:
        for line in f:
            if line.strip():
                metadata.append(json.loads(line))
    
    for meta in metadata:
        chamber = meta.get("chamber", "")
        meta['branch'] = assign_branch(chamber)
        if 'language' not in meta:
            meta['language'] = meta.get('language', 'de')
    
    return metadata

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

# ============================================================
# SECTION-SPECIFIC TF-IDF EMBEDDINGS
# ============================================================

def build_section_tfidf(metadata: List[Dict], section: str, max_features: int = 5000, 
                        min_df: int = 2, max_df: float = 0.95, ngram_range: Tuple[int, int] = (1, 2),
                        n_components: int = 128) -> np.ndarray:
    """Build TF-IDF + SVD embeddings for a specific section."""
    texts = []
    for meta in metadata:
        text = meta.get(section, "")
        if not text or text == "null":
            text = ""
        texts.append(text)
    
    # Filter out empty texts for vocabulary fitting
    non_empty_indices = [i for i, t in enumerate(texts) if t.strip()]
    non_empty_texts = [texts[i] for i in non_empty_indices]
    
    if len(non_empty_texts) < 10:
        logger.warning(f"Section {section}: too few non-empty texts ({len(non_empty_texts)})")
        return np.zeros((len(metadata), n_components), dtype=np.float32)
    
    vectorizer = TfidfVectorizer(
        max_features=max_features,
        min_df=min_df,
        max_df=max_df,
        ngram_range=ngram_range,
        sublinear_tf=True
    )
    
    tfidf_matrix = vectorizer.fit_transform(non_empty_texts)
    
    # SVD
    n_comp = min(n_components, tfidf_matrix.shape[1] - 1, tfidf_matrix.shape[0] - 1)
    if n_comp < 2:
        logger.warning(f"Section {section}: insufficient features for SVD (n_comp={n_comp})")
        return np.zeros((len(metadata), n_components), dtype=np.float32)
    
    from sklearn.decomposition import TruncatedSVD
    svd = TruncatedSVD(n_components=n_comp, random_state=GLOBAL_SEED)
    embeddings_reduced = svd.fit_transform(tfidf_matrix)
    embeddings_reduced = normalize(embeddings_reduced, norm='l2', axis=1)
    
    # Pad to full size
    full_embeddings = np.zeros((len(metadata), n_comp), dtype=np.float32)
    full_embeddings[non_empty_indices] = embeddings_reduced.astype(np.float32)
    
    # If n_comp < n_components, pad with zeros
    if n_comp < n_components:
        padded = np.zeros((len(metadata), n_components), dtype=np.float32)
        padded[:, :n_comp] = full_embeddings
        full_embeddings = padded
    
    logger.info(f"Section {section}: {len(non_empty_indices)}/{len(metadata)} non-empty, "
                f"vocab={len(vectorizer.vocabulary_)}, components={n_comp}, "
                f"explained_var={svd.explained_variance_ratio_.sum():.4f}")
    
    return full_embeddings

# ============================================================
# CROSS-LINGUAL ALIGNMENT METHODS
# ============================================================

def split_by_language(embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
    """Split embeddings by language, return (embeddings, indices) for each language."""
    lang_groups = defaultdict(list)
    for i, meta in enumerate(metadata):
        lang = meta.get('language', 'unknown')
        lang_groups[lang].append(i)
    
    result = {}
    for lang, indices in lang_groups.items():
        if len(indices) > 0:
            result[lang] = (embeddings[indices], np.array(indices))
    return result

def mean_center_alignment(embeddings: np.ndarray, metadata: List[Dict]) -> np.ndarray:
    """Mean center: subtract language-wise mean from each language's embeddings."""
    lang_groups = split_by_language(embeddings, metadata)
    aligned = embeddings.copy()
    
    for lang, (lang_emb, indices) in lang_groups.items():
        mean_vec = np.mean(lang_emb, axis=0, keepdims=True)
        aligned[indices] = lang_emb - mean_vec
    
    # Renormalize
    aligned = normalize(aligned, norm='l2', axis=1)
    return aligned.astype(np.float32)

def joint_pca_alignment(embeddings: np.ndarray, metadata: List[Dict], n_components: int = 128) -> np.ndarray:
    """Joint PCA: fit PCA on concatenated all-language embeddings."""
    # Simply fit PCA on all embeddings together
    pca = PCA(n_components=min(n_components, embeddings.shape[1]), random_state=GLOBAL_SEED)
    aligned = pca.fit_transform(embeddings)
    aligned = normalize(aligned, norm='l2', axis=1)
    logger.info(f"Joint PCA: {embeddings.shape[1]} -> {aligned.shape[1]} dims, "
                f"explained_var={pca.explained_variance_ratio_.sum():.4f}")
    return aligned.astype(np.float32)

def procrustes_alignment(embeddings: np.ndarray, metadata: List[Dict], 
                         reference_lang: str = 'de') -> np.ndarray:
    """Procrustes: align each language to reference language using all embeddings."""
    lang_groups = split_by_language(embeddings, metadata)
    
    if reference_lang not in lang_groups:
        logger.warning(f"Reference language {reference_lang} not found, using first available")
        reference_lang = list(lang_groups.keys())[0]
    
    ref_emb, ref_indices = lang_groups[reference_lang]
    aligned = embeddings.copy()
    aligned[ref_indices] = ref_emb  # Reference stays as-is
    
    for lang, (lang_emb, indices) in lang_groups.items():
        if lang == reference_lang:
            continue
        if len(lang_emb) < 2:
            continue
        # Procrustes alignment
        try:
            R, scale = orthogonal_procrustes(lang_emb, ref_emb[:len(lang_emb)])
            aligned_lang = lang_emb @ R
            aligned[indices] = aligned_lang
        except Exception as e:
            logger.warning(f"Procrustes failed for {lang}: {e}")
            aligned[indices] = lang_emb
    
    aligned = normalize(aligned, norm='l2', axis=1)
    return aligned.astype(np.float32)

def proc_pairs_alignment(embeddings: np.ndarray, metadata: List[Dict]) -> np.ndarray:
    """Proc Pairs: Procrustes on language-paired decisions (same branch, different language)."""
    lang_groups = split_by_language(embeddings, metadata)
    langs = list(lang_groups.keys())
    
    if len(langs) < 2:
        logger.warning("Need at least 2 languages for Proc Pairs")
        return embeddings
    
    # Build pairs: same branch, different language
    branches = [meta.get('branch', 'unknown') for meta in metadata]
    paired_indices = []
    
    for lang_a in langs:
        emb_a, idx_a = lang_groups[lang_a]
        branch_a = np.array([branches[i] for i in idx_a])
        
        for lang_b in langs:
            if lang_a >= lang_b:
                continue
            emb_b, idx_b = lang_groups[lang_b]
            branch_b = np.array([branches[i] for i in idx_b])
            
            # Find common branches
            common_branches = set(branch_a) & set(branch_b)
            for br in common_branches:
                idx_a_br = idx_a[branch_a == br]
                idx_b_br = idx_b[branch_b == br]
                n_pairs = min(len(idx_a_br), len(idx_b_br))
                if n_pairs > 0:
                    paired_indices.append((idx_a_br[:n_pairs], idx_b_br[:n_pairs]))
    
    if not paired_indices:
        logger.warning("No language pairs found for Proc Pairs")
        return embeddings
    
    # Concatenate all pairs
    all_a = np.concatenate([p[0] for p in paired_indices])
    all_b = np.concatenate([p[1] for p in paired_indices])
    
    if len(all_a) < 2:
        logger.warning("Too few pairs for Proc Pairs")
        return embeddings
    
    emb_a = embeddings[all_a]
    emb_b = embeddings[all_b]
    
    # Procrustes on paired decisions
    try:
        R, scale = orthogonal_procrustes(emb_a, emb_b)
        logger.info(f"Proc Pairs: {len(all_a)} pairs, Procrustes scale={scale:.4f}")
    except Exception as e:
        logger.warning(f"Proc Pairs Procrustes failed: {e}")
        return embeddings
    
    # Apply to all embeddings (use average rotation if multiple language pairs)
    aligned = embeddings.copy()
    aligned = aligned @ R
    aligned = normalize(aligned, norm='l2', axis=1)
    return aligned.astype(np.float32)

# ============================================================
# HYBRID CONSTRUCTION
# ============================================================

def create_hybrid(emb_a: np.ndarray, emb_b: np.ndarray, alpha: float) -> np.ndarray:
    """Create hybrid: alpha * emb_a + (1-alpha) * emb_b, then normalize."""
    # Ensure same dimensions
    if emb_a.shape[1] != emb_b.shape[1]:
        # Pad or truncate to match
        min_dim = min(emb_a.shape[1], emb_b.shape[1])
        emb_a = emb_a[:, :min_dim]
        emb_b = emb_b[:, :min_dim]
    
    hybrid = alpha * emb_a + (1 - alpha) * emb_b
    hybrid = normalize(hybrid, norm='l2', axis=1)
    return hybrid.astype(np.float32)

# ============================================================
# FROZEN BENCHMARKS (copied from evaluation_v3_harness.py)
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

def simulate_cluster_coherence_rating(
    embeddings: np.ndarray,
    branches: np.ndarray,
    languages: np.ndarray,
    n_clusters: int = N_CLUSTERS_COHERENCE
) -> Dict:
    kmeans = KMeans(n_clusters=n_clusters, random_state=GLOBAL_SEED, n_init=10)
    cluster_labels = kmeans.fit_predict(embeddings)
    
    cluster_purities = []
    cluster_sizes = []
    
    for c in range(n_clusters):
        mask = cluster_labels == c
        if np.sum(mask) == 0:
            continue
        cluster_branches = branches[mask]
        majority = Counter(cluster_branches).most_common(1)[0][0]
        purity = np.mean(cluster_branches == majority)
        cluster_purities.append(purity)
        cluster_sizes.append(int(np.sum(mask)))
    
    mean_purity = np.mean(cluster_purities)
    nmi = normalized_mutual_info_score(branches, cluster_labels)
    
    lang_purities = []
    for c in range(n_clusters):
        mask = cluster_labels == c
        if np.sum(mask) == 0:
            continue
        cluster_langs = languages[mask]
        majority = Counter(cluster_langs).most_common(1)[0][0]
        purity = np.mean(cluster_langs == majority)
        lang_purities.append(purity)
    
    mean_lang_purity = np.mean(lang_purities)
    
    return {
        "status": "PASS" if mean_purity > CLUSTER_COHERENCE_THRESHOLD else "FAIL",
        "n_clusters": n_clusters,
        "mean_branch_purity": round(float(mean_purity), 4),
        "branch_nmi": round(float(nmi), 4),
        "mean_language_purity": round(float(mean_lang_purity), 4),
        "cluster_purities": [round(p, 4) for p in cluster_purities],
        "cluster_sizes": cluster_sizes,
        "note": "Simulated jurist rates clusters by branch coherence. High branch purity = legally coherent clusters. High language purity = language-dominated clusters."
    }

def simulate_cross_language_retrieval(
    embeddings: np.ndarray,
    branches: np.ndarray,
    languages: np.ndarray,
    k: int = K_NEIGHBORS_CROSS_LANG
) -> Dict:
    branch_lang_groups = {}
    for i in range(len(branches)):
        key = (branches[i], languages[i])
        if key not in branch_lang_groups:
            branch_lang_groups[key] = []
        branch_lang_groups[key].append(i)
    
    nn = NearestNeighbors(n_neighbors=k+1, metric='cosine')
    nn.fit(embeddings)
    _, indices = nn.kneighbors(embeddings)
    neighbors = indices[:, 1:]
    
    cross_lang_recall_rates = []
    
    for i in range(len(branches)):
        branch = branches[i]
        lang = languages[i]
        
        cross_lang_gt = []
        for other_lang in ['de', 'fr', 'it']:
            if other_lang != lang:
                key = (branch, other_lang)
                if key in branch_lang_groups:
                    cross_lang_gt.extend(branch_lang_groups[key])
        
        if not cross_lang_gt:
            continue
        
        neighbor_set = set(neighbors[i])
        found = sum(1 for gt in cross_lang_gt if gt in neighbor_set)
        recall = found / min(len(cross_lang_gt), k)
        cross_lang_recall_rates.append(recall)
    
    mean_recall = np.mean(cross_lang_recall_rates) if cross_lang_recall_rates else 0
    
    return {
        "status": "PASS" if mean_recall > CROSS_LANG_RECALL_THRESHOLD else "FAIL",
        "mean_cross_language_recall_at_k": round(float(mean_recall), 4),
        "k": k,
        "n_queries": len(cross_lang_recall_rates),
        "note": "Simulated jurist searches for cross-language legal equivalents. Recall > 0.2 means at least 1 in 5 cross-language legal equivalents appears in top-10."
    }

# ============================================================
# JURIVOC HIERARCHY ALIGNMENT (frozen)
# ============================================================

def compute_jurivoc_alignment(embeddings: np.ndarray, metadata: List[Dict]) -> Dict:
    branches = [m.get('branch', 'unknown') for m in metadata]
    legal_areas = [m.get('legal_area', 'unknown') for m in metadata]
    legal_areas = [la if la and la != 'null' else 'unknown' for la in legal_areas]
    
    results = {}
    
    # Level 0 alignment (4 branches)
    kmeans_l0 = KMeans(n_clusters=4, random_state=GLOBAL_SEED, n_init=10)
    labels_l0 = kmeans_l0.fit_predict(embeddings)
    nmi_l0 = normalized_mutual_info_score(branches, labels_l0)
    
    # Level 1 alignment (legal areas - 16 clusters)
    kmeans_l1 = KMeans(n_clusters=16, random_state=GLOBAL_SEED, n_init=10)
    labels_l1 = kmeans_l1.fit_predict(embeddings)
    nmi_l1 = normalized_mutual_info_score(legal_areas, labels_l1)
    
    # Hierarchical consistency
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

# ============================================================
# SCALE STABILITY (frozen)
# ============================================================

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

# ============================================================
# BOILERPLATE RESISTANCE (frozen)
# ============================================================

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

# ============================================================
# FRACTAL QUALITY (hierarchical Leiden)
# ============================================================

FRACTAL_MAP_PATH = Path(os.environ.get(
    "LEX_FRACTAL_MAP_PATH", 
    str(REPO_ROOT / "fractal_map/hierarchical")
))
sys.path.insert(0, str(FRACTAL_MAP_PATH))
try:
    from hierarchical_leiden import hierarchical_leiden, compute_branch_purity
    HAS_HIERARCHICAL_LEIDEN = True
except ImportError:
    HAS_HIERARCHICAL_LEIDEN = False
    logger.warning(f"hierarchical_leiden module not found at {FRACTAL_MAP_PATH}. Fractal benchmarks will use fallback.")
    def hierarchical_leiden(*args, **kwargs):
        return None, None, {}
    def compute_branch_purity(labels, metadata):
        return 0.0

def run_fractal_quality_benchmarks(embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Any]:
    n_metadata = len(metadata)
    if embeddings.shape[0] != n_metadata:
        if embeddings.shape[0] > n_metadata:
            embeddings = embeddings[:n_metadata]
        else:
            return {
                'n_coarse': 0, 'n_fine': 0, 'coarse_purity': 0.0, 'fine_purity': 0.0,
                'overall_improvement': 0.0, 'improvement_rate': 0.0,
                'legal_area_nmi': 0.0, 'flat_purity': 0.0, 'hierarchical_advantage': 0.0,
                'cluster_coherence': {'status': 'SKIP', 'note': 'embedding/metadata length mismatch'},
                'cross_language_retrieval': {'status': 'SKIP', 'note': 'embedding/metadata length mismatch'},
            }
    
    if HAS_HIERARCHICAL_LEIDEN:
        result = hierarchical_leiden(embeddings, metadata, coarse_res=0.5, sub_res=3.0)
        hierarchical_labels, coarse_labels, cluster_info = result
        
        coarse_to_fine = defaultdict(list)
        for sub_id, info in cluster_info.items():
            if not info.get('too_small', False):
                coarse_id = info['coarse_id']
                coarse_to_fine[coarse_id].append(sub_id)
        
        n_fine = len(set(hierarchical_labels[hierarchical_labels != -1]))
        n_coarse = len(set(coarse_labels[coarse_labels != -1]))
        
        coarse_purities = {}
        for c in np.unique(coarse_labels[coarse_labels != -1]):
            mask = coarse_labels == c
            cluster_branches = [metadata[i].get('branch', 'unknown') for i in np.where(mask)[0]]
            cluster_branches = [b for b in cluster_branches if b != 'unknown']
            if cluster_branches:
                coarse_purities[int(c)] = Counter(cluster_branches).most_common(1)[0][1] / len(cluster_branches)
        
        fine_purities = {}
        for c in np.unique(hierarchical_labels[hierarchical_labels != -1]):
            mask = hierarchical_labels == c
            cluster_branches = [metadata[i].get('branch', 'unknown') for i in np.where(mask)[0]]
            cluster_branches = [b for b in cluster_branches if b != 'unknown']
            if cluster_branches:
                fine_purities[int(c)] = Counter(cluster_branches).most_common(1)[0][1] / len(cluster_branches)
        
        coarse_overall = np.mean(list(coarse_purities.values())) if coarse_purities else 0
        fine_overall = np.mean(list(fine_purities.values())) if fine_purities else 0
        
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
        cluster_coherence = simulate_cluster_coherence_rating(embeddings, branches_arr, languages_arr, n_clusters=16)
        
        # Cross-language retrieval
        cross_lang = simulate_cross_language_retrieval(embeddings, branches_arr, languages_arr)
        
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
    else:
        branches_arr = np.array([m.get('branch', 'unknown') for m in metadata])
        languages_arr = np.array([m.get('language', 'unknown') for m in metadata])
        cluster_coherence = simulate_cluster_coherence_rating(embeddings, branches_arr, languages_arr, n_clusters=16)
        cross_lang = simulate_cross_language_retrieval(embeddings, branches_arr, languages_arr)
        
        return {
            'n_coarse': 0, 'n_fine': 0, 'coarse_purity': 0.0, 'fine_purity': 0.0,
            'overall_improvement': 0.0, 'improvement_rate': 0.0,
            'legal_area_nmi': 0.0, 'flat_purity': 0.0, 'hierarchical_advantage': 0.0,
            'cluster_coherence': cluster_coherence,
            'cross_language_retrieval': cross_lang,
        }

# ============================================================
# MAIN EVALUATION
# ============================================================

def run_adversarial_benchmarks(embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Any]:
    branches, languages, chambers, valid_indices = prepare_metadata(metadata)
    rep_valid = embeddings[valid_indices]
    meta_valid = [metadata[i] for i in valid_indices]
    
    lang_dom = adversarial_language_dominance(rep_valid, meta_valid)
    jurist_pref = simulate_pairwise_preference(rep_valid, branches, languages)
    
    return {
        'adversarial_language_dominance': lang_dom,
        'jurist_pairwise_preference': jurist_pref,
        'both_pass': lang_dom.get('status') == 'PASS' and jurist_pref.get('status') == 'PASS',
        'language_dominance_score': lang_dom.get('mean_language_dominance', 1.0),
        'jurist_preference_rate': jurist_pref.get('jurist_would_succeed_rate', 0.0),
    }

def evaluate_representation(name: str, embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Any]:
    logger.info(f"\n{'='*60}")
    logger.info(f"Evaluating: {name}")
    logger.info(f"Shape: {embeddings.shape}")
    logger.info(f"{'='*60}")
    
    start_time = time.time()
    
    logger.info("Running adversarial benchmarks...")
    adv_results = run_adversarial_benchmarks(embeddings, metadata)
    
    logger.info("Running Jurivoc hierarchy alignment...")
    jurivoc_results = compute_jurivoc_alignment(embeddings, metadata)
    
    logger.info("Running scale stability...")
    scale_results = compute_scale_stability(embeddings, metadata)
    
    logger.info("Running boilerplate resistance...")
    boilerplate_results = compute_boilerplate_resistance(embeddings, metadata)
    
    logger.info("Running fractal quality benchmarks...")
    fractal_results = run_fractal_quality_benchmarks(embeddings, metadata)
    
    duration = time.time() - start_time
    
    both_adv_pass = adv_results['both_pass']
    verdict = "PASS" if both_adv_pass else "FAIL"
    
    return {
        'name': name,
        'embedding_shape': list(embeddings.shape),
        'duration_seconds': duration,
        'adversarial': adv_results,
        'jurivoc_alignment': jurivoc_results,
        'scale_stability': scale_results,
        'boilerplate_resistance': boilerplate_results,
        'fractal': fractal_results,
        'verdict': verdict,
        'both_adversarial_pass': both_adv_pass,
    }

def main():
    np.random.seed(GLOBAL_SEED)
    
    logger.info("=" * 70)
    logger.info(f"Evaluation v10 - Cross-Lingual Alignment Deeper Investigation")
    logger.info(f"Global seed: {GLOBAL_SEED}")
    logger.info(f"Factory direction: v{FACTORY_DIRECTION_VERSION}")
    logger.info("=" * 70)
    
    # Load metadata
    logger.info("\n1. Loading evaluation metadata...")
    metadata = load_metadata_1200()
    logger.info(f"Loaded metadata for {len(metadata)} decisions")
    
    # Load base cited_decisions_tfidf embeddings
    logger.info("\n2. Loading base cited_decisions_tfidf embeddings...")
    cdtf_path = REPO_ROOT / "evaluation/results/v3_cited_decisions/cited_decisions_tfidf_1200.npy"
    if not cdtf_path.exists():
        logger.error(f"Base embeddings not found at {cdtf_path}")
        return
    
    cited_decisions_tfidf = np.load(cdtf_path)
    if cited_decisions_tfidf.dtype == np.float64:
        cited_decisions_tfidf = cited_decisions_tfidf.astype(np.float32)
    logger.info(f"Loaded cited_decisions_tfidf: {cited_decisions_tfidf.shape} ({cited_decisions_tfidf.dtype})")
    
    # Build section-specific embeddings
    logger.info("\n3. Building section-specific TF-IDF embeddings...")
    sections = ['sachverhalt', 'erwaegungen', 'dispositiv', 'outcome']
    section_embeddings = {}
    for section in sections:
        emb = build_section_tfidf(metadata, section, n_components=128)
        section_embeddings[section] = emb
    
    # Create PCA-reduced versions of cited_decisions_tfidf (simulating center_projected equivalents)
    logger.info("\n4. Creating PCA-reduced versions...")
    pca_64 = PCA(n_components=64, random_state=GLOBAL_SEED)
    cdtf_64 = pca_64.fit_transform(cited_decisions_tfidf)
    cdtf_64 = normalize(cdtf_64, norm='l2', axis=1).astype(np.float32)
    logger.info(f"cited_decisions_tfidf_64: {cdtf_64.shape}, explained_var={pca_64.explained_variance_ratio_.sum():.4f}")
    
    pca_32 = PCA(n_components=32, random_state=GLOBAL_SEED)
    cdtf_32 = pca_32.fit_transform(cited_decisions_tfidf)
    cdtf_32 = normalize(cdtf_32, norm='l2', axis=1).astype(np.float32)
    logger.info(f"cited_decisions_tfidf_32: {cdtf_32.shape}, explained_var={pca_32.explained_variance_ratio_.sum():.4f}")
    
    # Cross-lingual alignment methods on cited_decisions_tfidf
    logger.info("\n5. Applying cross-lingual alignment methods...")
    
    # Mean Center
    cdtf_mean_center = mean_center_alignment(cited_decisions_tfidf, metadata)
    
    # Joint PCA
    cdtf_joint_pca = joint_pca_alignment(cited_decisions_tfidf, metadata)
    
    # Procrustes (single)
    cdtf_procrustes = procrustes_alignment(cited_decisions_tfidf, metadata)
    
    # Proc Pairs (v8 winner)
    cdtf_proc_pairs = proc_pairs_alignment(cited_decisions_tfidf, metadata)
    
    # Cross-lingual alignment on section embeddings
    logger.info("\n6. Applying cross-lingual alignment to section embeddings...")
    section_aligned = {}
    for section, emb in section_embeddings.items():
        if np.all(emb == 0):
            logger.warning(f"Skipping {section}: all zeros")
            continue
        section_aligned[f"{section}_mean_center"] = mean_center_alignment(emb, metadata)
        section_aligned[f"{section}_joint_pca"] = joint_pca_alignment(emb, metadata)
        section_aligned[f"{section}_procrustes"] = procrustes_alignment(emb, metadata)
        section_aligned[f"{section}_proc_pairs"] = proc_pairs_alignment(emb, metadata)
    
    # Hybrids: cited_decisions_tfidf (aligned) + PCA-reduced versions
    logger.info("\n7. Creating hybrids...")
    hybrids = {}
    
    # Base cited_decisions_tfidf + PCA-reduced (simulating cp64 hybrid)
    for alpha in [0.3, 0.5, 0.7]:
        hybrids[f"cited_decisions_tfidf_hybrid_cdtf64_{alpha}"] = create_hybrid(
            cited_decisions_tfidf, cdtf_64, alpha)
    
    # Cross-lingual aligned + PCA-reduced
    for method in ['mean_center', 'joint_pca', 'procrustes', 'proc_pairs']:
        aligned_emb = locals()[f'cdtf_{method}']
        for alpha in [0.3, 0.5, 0.7]:
            hybrids[f"cited_decisions_tfidf_{method}_hybrid_cdtf64_{alpha}"] = create_hybrid(
                aligned_emb, cdtf_64, alpha)
    
    # Outcome hybrid with cross-lingual aligned (2-dim outcome signal)
    outcome_emb = section_embeddings['outcome']
    if not np.all(outcome_emb == 0):
        for method in ['', 'mean_center_', 'joint_pca_', 'procrustes_', 'proc_pairs_']:
            if method == '':
                base_emb = cited_decisions_tfidf
            else:
                base_emb = section_aligned[f"cited_decisions_tfidf_{method.rstrip('_')}"] if f"cited_decisions_tfidf_{method.rstrip('_')}" in locals() else cited_decisions_tfidf
            
            # Reduce outcome to match base dim for proper hybrid, or use raw outcome
            # The v9 outcome hybrids were 2-dim, let's match that approach
            # First, reduce base to 2-dim for fair comparison
            pca_2 = PCA(n_components=2, random_state=GLOBAL_SEED)
            base_2d = pca_2.fit_transform(base_emb)
            base_2d = normalize(base_2d, norm='l2', axis=1).astype(np.float32)
            outcome_2d = pca_2.fit_transform(outcome_emb)  # Use same PCA for consistency? No, outcome has its own structure
            outcome_2d = normalize(outcome_2d, norm='l2', axis=1).astype(np.float32)
            
            for alpha in [0.3, 0.5, 0.7]:
                method_name = method.rstrip('_') if method else 'original'
                hybrids[f"cited_decisions_tfidf_{method_name}_outcome_hybrid_{alpha}"] = create_hybrid(
                    base_2d, outcome_2d, alpha)
    
    # Collect all representations to evaluate
    representations = {
        # Base
        'cited_decisions_tfidf': cited_decisions_tfidf,
        'cited_decisions_tfidf_64': cdtf_64,
        'cited_decisions_tfidf_32': cdtf_32,
        
        # Cross-lingual aligned
        'cited_decisions_tfidf_mean_center': cdtf_mean_center,
        'cited_decisions_tfidf_joint_pca': cdtf_joint_pca,
        'cited_decisions_tfidf_procrustes': cdtf_procrustes,
        'cited_decisions_tfidf_proc_pairs': cdtf_proc_pairs,
        
        # Section embeddings
        **{f"section_{k}": v for k, v in section_embeddings.items()},
        
        # Section cross-lingual aligned
        **{f"section_{k}": v for k, v in section_aligned.items()},
        
        # Hybrids
        **hybrids,
    }
    
    # Add reference baselines if available locally
    # We don't have center_projected_64dim locally, but we can use cdtf_64 as reference
    
    # Evaluate all
    logger.info("\n8. Running evaluations on all representations...")
    all_results = {}
    
    for name, emb in representations.items():
        if emb is None or emb.size == 0 or np.all(emb == 0):
            logger.warning(f"  Skipping {name}: empty or all zeros")
            continue
        
        try:
            result = evaluate_representation(name, emb, metadata)
            all_results[name] = result
            
            adv = result['adversarial']
            jurivoc = result['jurivoc_alignment']
            scale = result['scale_stability']
            boiler = result['boilerplate_resistance']
            frac = result['fractal']
            
            logger.info(f"  {name}: verdict={result['verdict']}, "
                       f"lang_dom={adv['language_dominance_score']:.4f} "
                       f"({'PASS' if adv['adversarial_language_dominance']['status']=='PASS' else 'FAIL'}), "
                       f"jurist_pref={adv['jurist_preference_rate']:.4f} "
                       f"({'PASS' if adv['jurist_pairwise_preference']['status']=='PASS' else 'FAIL'}), "
                       f"jurivoc_l0={jurivoc['level_0_nmi']:.4f}, "
                       f"scale_stability={scale.get('mean_neighbor_overlap', 'N/A'):.4f}, "
                       f"boilerplate_resist={boiler['resistance_score']:.4f}, "
                       f"improvement_rate={frac.get('improvement_rate', 0):.2%}")
            
        except Exception as e:
            logger.error(f"  {name}: ERROR - {e}")
            import traceback
            traceback.print_exc()
            all_results[name] = {'error': str(e), 'verdict': 'ERROR'}
    
    # Save all results
    output_dir = REPO_ROOT / "evaluation/results/v3_extended"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "evaluation_v10_cross_lingual_alignment_results.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Generate summary report
    logger.info("\n" + "=" * 90)
    logger.info("EVALUATION v10 - CROSS-LINGUAL ALIGNMENT ON FROZEN HARNESS v3 SUMMARY")
    logger.info("=" * 90)
    logger.info(f"Global seed: {GLOBAL_SEED} | Factory direction: v{FACTORY_DIRECTION_VERSION}")
    logger.info("-" * 90)
    logger.info(f"{'Representation':<50} {'Verdict':<7} {'LangDom':>7} {'LD-P':>5} {'Jurist':>7} {'JP-P':>5} {'Both':>5} {'Jurivoc0':>8} {'Scale':>6} {'Boiler':>7} {'ImpRate':>7}")
    logger.info("-" * 90)
    
    def sort_key(item):
        name, res = item
        if 'error' in res:
            return (0, 0, 1.0)
        both = res['both_adversarial_pass']
        jurist = res['adversarial']['jurist_preference_rate']
        lang_dom = res['adversarial']['language_dominance_score']
        return (both, jurist, -lang_dom)
    
    sorted_results = sorted(all_results.items(), key=sort_key, reverse=True)
    
    for name, res in sorted_results:
        if 'error' in res:
            logger.info(f"{name:<50} {'ERROR':<7} {'N/A':>7} {'N/A':>5} {'N/A':>7} {'N/A':>5} {'N/A':>5} {'N/A':>8} {'N/A':>6} {'N/A':>7} {'N/A':>7}")
            continue
        
        adv = res['adversarial']
        jurivoc = res['jurivoc_alignment']
        scale = res['scale_stability']
        boiler = res['boilerplate_resistance']
        frac = res['fractal']
        
        ld = adv['language_dominance_score']
        jp = adv['jurist_preference_rate']
        ld_pass = "✓" if adv['adversarial_language_dominance']['status'] == 'PASS' else "✗"
        jp_pass = "✓" if adv['jurist_pairwise_preference']['status'] == 'PASS' else "✗"
        both = "✓" if adv['both_pass'] else "✗"
        
        scale_score = scale.get('mean_neighbor_overlap', 0)
        boiler_score = boiler['resistance_score']
        imp_rate = frac.get('improvement_rate', 0)
        
        logger.info(f"{name:<50} {res['verdict']:<7} {ld:>7.4f} {ld_pass:>5} {jp:>7.4f} {jp_pass:>5} {both:>5} "
                   f"{jurivoc['level_0_nmi']:>8.4f} {scale_score:>6.4f} {boiler_score:>7.4f} {imp_rate:>6.1%}")
    
    # Find best representation (must pass both adversarial gates)
    valid_results = {k: v for k, v in all_results.items() if 'error' not in v and v['both_adversarial_pass']}
    if valid_results:
        best = max(valid_results.items(), key=lambda x: (x[1]['adversarial']['jurist_preference_rate'],
                                                         -x[1]['adversarial']['language_dominance_score']))
        logger.info(f"\n🏆 BEST REPRESENTATION (passing both adversarial gates): {best[0]}")
        logger.info(f"   Language dominance: {best[1]['adversarial']['language_dominance_score']:.4f}")
        logger.info(f"   Jurist preference: {best[1]['adversarial']['jurist_preference_rate']:.4f}")
        logger.info(f"   Jurivoc Level 0 NMI: {best[1]['jurivoc_alignment']['level_0_nmi']:.4f}")
        logger.info(f"   Scale stability: {best[1]['scale_stability'].get('mean_neighbor_overlap', 'N/A')}")
        logger.info(f"   Boilerplate resistance: {best[1]['boilerplate_resistance']['resistance_score']:.4f}")
    else:
        logger.info("\n⚠️  NO REPRESENTATION PASSES BOTH ADVERSARIAL GATES")
    
    logger.info(f"\nResults saved to: {output_file}")
    logger.info("=" * 90)
    
    return all_results

if __name__ == "__main__":
    main()