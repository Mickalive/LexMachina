#!/usr/bin/env python3
"""
Evaluation Lane v3 - Frozen Evaluation Harness

Factory Direction v6 requirement:
"Define and execute v3: Validate legal-distance unsupervised signal ablation 
results (on center_projected baseline) and frontier_metric_learning_jurivoc 
supervised metric learning results on expanded slice (1,200 decisions) using 
adversarial benchmarks (language dominance, jurist pairwise, Jurivoc hierarchy 
alignment, scale stability, boilerplate resistance). center_projected is the 
default reference representation to beat. Freeze evaluation harness with global seed."

This script freezes the evaluation harness with global seed=42 and runs:
1. Adversarial language dominance (threshold: < 0.85)
2. Jurist pairwise preference (threshold: > 0.5)
3. Jurivoc hierarchy alignment
4. Scale stability
5. Boilerplate resistance

Representations tested:
- center_projected (768-dim, reference baseline)
- center_projected_64dim (frozen PCA, current production default)
- linear_metric_epoch4 (best linear projection, JP=0.685)
- mahalanobis_metric_epoch4 (best Mahalanobis, JP=0.678)
- hybrid_stabilized_epoch1 (best stabilized hybrid, JP=0.666)
- hybrid_v2_epoch3 (best hybrid v2, JP=0.599)
"""

import json
import numpy as np
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from collections import Counter, defaultdict
import sys
import time
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics import normalized_mutual_info_score
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize
import hashlib

# Module-level logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# ============================================================
# FROZEN CONFIGURATION - DO NOT MODIFY AFTER FREEZE
# ============================================================
EVALUATION_VERSION = "v3"
GLOBAL_SEED = 42
FACTORY_DIRECTION_VERSION = 6

# Adversarial thresholds (frozen)
LANGUAGE_DOMINANCE_THRESHOLD = 0.85
JURIST_PAIRWISE_THRESHOLD = 0.5
CROSS_LANG_RECALL_THRESHOLD = 0.2
CLUSTER_COHERENCE_THRESHOLD = 0.7

# Benchmark parameters (frozen)
K_NEIGHBORS_LANG_DOM = 20
K_NEIGHBORS_JURIST = 10
K_NEIGHBORS_CROSS_LANG = 10
N_CLUSTERS_COHERENCE = 16

# Paths (frozen)
METADATA_PATH = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/v5/center_projected_full/metadata.json")
CP_768_PATH = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/v5/center_projected_full/embeddings_center_projected.npy")
CP_64_PATH = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/v5/center_projected_full/embeddings_center_projected_64.npy")
LINEAR_METRIC_PATH = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/v6/metric_learning/best_linear_embeddings.npy")
MAHALANOBIS_METRIC_PATH = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/v6/metric_learning/best_mahalanobis_embeddings.npy")
HYBRID_STABILIZED_PATH = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/v6/hybrid_objective_stabilized/best_embeddings.npy")
HYBRID_V2_PATH = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/v6/hybrid_objective_v2/best_embeddings.npy")

OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/v3")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# UTILITY FUNCTIONS (frozen implementations)
# ============================================================

def set_global_seed(seed: int = GLOBAL_SEED):
    """Set global random seed for reproducibility."""
    np.random.seed(seed)

def get_config_hash() -> str:
    """Generate hash of frozen configuration for audit trail."""
    config = {
        "version": EVALUATION_VERSION,
        "seed": GLOBAL_SEED,
        "factory_direction": FACTORY_DIRECTION_VERSION,
        "thresholds": {
            "language_dominance": LANGUAGE_DOMINANCE_THRESHOLD,
            "jurist_pairwise": JURIST_PAIRWISE_THRESHOLD,
            "cross_lang_recall": CROSS_LANG_RECALL_THRESHOLD,
            "cluster_coherence": CLUSTER_COHERENCE_THRESHOLD
        },
        "parameters": {
            "k_lang_dom": K_NEIGHBORS_LANG_DOM,
            "k_jurist": K_NEIGHBORS_JURIST,
            "k_cross_lang": K_NEIGHBORS_CROSS_LANG,
            "n_clusters": N_CLUSTERS_COHERENCE
        }
    }
    config_str = json.dumps(config, sort_keys=True)
    return hashlib.sha256(config_str.encode()).hexdigest()[:16]

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

def load_evaluation_metadata() -> List[Dict]:
    """Load metadata from fractal-map baseline (1200 decisions)."""
    with open(METADATA_PATH, 'r') as f:
        metadata = json.load(f)
    
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
# ADVERSARIAL BENCHMARKS (frozen implementations)
# ============================================================

def adversarial_language_dominance(embeddings: np.ndarray, metadata: List[Dict], k: int = K_NEIGHBORS_LANG_DOM) -> Dict:
    """
    Adversarial test: measure language dominance in nearest neighbors.
    Language dominance = fraction of k-NN that share the same language.
    Should be LOW (not dominated by language).
    """
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
    nn = NearestNeighbors(n_neighbors=k+1, metric='cosine')
    nn.fit(embeddings)
    _, indices = nn.kneighbors(embeddings)
    neighbors = indices[:, 1:]  # Exclude self
    
    # For each decision, count same-branch-diff-lang vs same-lang-diff-branch in top-k
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
    # If both available, jurist picks legal-relevant (correct)
    # If only language artifact available, jurist is forced to pick it (wrong)
    jurist_correct = legal_relevant_count + both_count
    jurist_forced_wrong = language_artifact_count
    jurist_no_choice = neither_count
    
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
    """
    Simulate jurist cluster coherence rating.
    
    A jurist is shown the top-5 decisions from each cluster and asked:
    "Do these decisions share a coherent legal theme?"
    
    We proxy this by measuring branch purity and Jurivoc alignment of clusters.
    """
    kmeans = KMeans(n_clusters=n_clusters, random_state=GLOBAL_SEED, n_init=10)
    cluster_labels = kmeans.fit_predict(embeddings)
    
    # Compute branch purity per cluster
    cluster_purities = []
    cluster_sizes = []
    cluster_branch_dist = {}
    
    for c in range(n_clusters):
        mask = cluster_labels == c
        if np.sum(mask) == 0:
            continue
        cluster_branches = branches[mask]
        majority = Counter(cluster_branches).most_common(1)[0][0]
        purity = np.mean(cluster_branches == majority)
        cluster_purities.append(purity)
        cluster_sizes.append(int(np.sum(mask)))
        cluster_branch_dist[c] = dict(Counter(cluster_branches))
    
    mean_purity = np.mean(cluster_purities)
    
    # NMI with branch labels
    nmi = normalized_mutual_info_score(branches, cluster_labels)
    
    # Language purity (should be high if language dominates)
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
    """
    Simulate jurist cross-language retrieval task.
    
    A jurist has a German decision and wants to find related French decisions.
    We measure the cross-language same-branch recall in top-k.
    """
    from collections import Counter
    
    # Group by branch and language
    branch_lang_groups = {}
    for i in range(len(branches)):
        key = (branches[i], languages[i])
        if key not in branch_lang_groups:
            branch_lang_groups[key] = []
        branch_lang_groups[key].append(i)
    
    # Build NN graph
    nn = NearestNeighbors(n_neighbors=k+1, metric='cosine')
    nn.fit(embeddings)
    _, indices = nn.kneighbors(embeddings)
    neighbors = indices[:, 1:]
    
    # For each decision, measure cross-language same-branch recall
    cross_lang_recall_rates = []
    
    for i in range(len(branches)):
        branch = branches[i]
        lang = languages[i]
        
        # Find all same-branch different-language decisions (ground truth)
        cross_lang_gt = []
        for other_lang in ['de', 'fr', 'it']:
            if other_lang != lang:
                key = (branch, other_lang)
                if key in branch_lang_groups:
                    cross_lang_gt.extend(branch_lang_groups[key])
        
        if not cross_lang_gt:
            continue
        
        # Check how many appear in top-k
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

def load_jurivoc_hierarchy() -> Dict:
    """Load Jurivoc hierarchy data if available, otherwise return synthetic."""
    # Try to load from accepted corpus
    jurivoc_paths = [
        Path("/tmp/lex_accepted/corpus/results/jurivoc/hierarchy.json"),
        Path("/tmp/lex_accepted/corpus/jurivoc_hierarchy.json"),
        Path("/home/runner/work/LexMachina/LexMachina/corpus/results/jurivoc/hierarchy.json"),
    ]
    
    for path in jurivoc_paths:
        if path.exists():
            with open(path) as f:
                return json.load(f)
    
    # Synthetic Jurivoc structure based on Swiss Federal Supreme Court domains
    return {
        "levels": {
            "0": ["Public Law", "Civil Law", "Criminal Law", "Social Security Law"],
            "1": {
                "Public Law": ["Constitutional Law", "Administrative Law", "Tax Law", "Social Insurance Law"],
                "Civil Law": ["Contract Law", "Family Law", "Property Law", "Inheritance Law", "Debt Enforcement"],
                "Criminal Law": ["Criminal Procedure", "Substantive Criminal Law", "Execution of Sentences"],
                "Social Security Law": ["Old Age/Disability", "Accident Insurance", "Health Insurance", "Unemployment"]
            }
        },
        "decision_mapping": {}  # Would map decision_id to Jurivoc codes
    }

def compute_jurivoc_alignment(embeddings: np.ndarray, metadata: List[Dict]) -> Dict:
    """
    Compute alignment with Jurivoc hierarchy.
    
    Since we don't have full Jurivoc annotations for all 1200 decisions,
    we use branch + legal_area as proxy for Jurivoc levels.
    """
    # Use branch as Level 0 (coarse), legal_area as Level 1 (fine)
    branches = [m.get('branch', 'unknown') for m in metadata]
    legal_areas = [m.get('legal_area', 'unknown') for m in metadata]
    legal_areas = [la if la and la != 'null' else 'unknown' for la in legal_areas]
    
    # Cluster at different resolutions to match Jurivoc levels
    # Level 0: 4 clusters (4 main branches)
    # Level 1: ~12-16 clusters (legal areas)
    
    results = {}
    
    # Level 0 alignment (4 branches)
    kmeans_l0 = KMeans(n_clusters=4, random_state=GLOBAL_SEED, n_init=10)
    labels_l0 = kmeans_l0.fit_predict(embeddings)
    nmi_l0 = normalized_mutual_info_score(branches, labels_l0)
    
    # Level 1 alignment (legal areas - use 16 clusters to match legal areas)
    kmeans_l1 = KMeans(n_clusters=16, random_state=GLOBAL_SEED, n_init=10)
    labels_l1 = kmeans_l1.fit_predict(embeddings)
    nmi_l1 = normalized_mutual_info_score(legal_areas, labels_l1)
    
    # Hierarchical consistency: Level 1 clusters should nest within Level 0
    # Compute nesting score
    nesting_score = 0.0
    for l0_cluster in range(4):
        mask = labels_l0 == l0_cluster
        if np.sum(mask) > 0:
            l1_subclusters = labels_l1[mask]
            # Check if subclusters are pure w.r.t L0
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
    """
    Test stability of neighbor structure under corpus subsampling.
    
    Split decisions by year/metadata, compute neighbors on subset,
    measure overlap with full-corpus neighbors.
    """
    n = embeddings.shape[0]
    if n < 100:
        return {"status": "SKIP", "note": "Insufficient decisions for scale stability test"}
    
    # Use random splits (seeded)
    np.random.seed(GLOBAL_SEED)
    indices = np.arange(n)
    np.random.shuffle(indices)
    
    # Split: 80% train, 20% test
    split_idx = int(0.8 * n)
    train_idx = indices[:split_idx]
    test_idx = indices[split_idx:]
    
    # Full corpus neighbors
    nn_full = NearestNeighbors(n_neighbors=11, metric='cosine')
    nn_full.fit(embeddings)
    _, full_neighbors = nn_full.kneighbors(embeddings)
    full_neighbors = full_neighbors[:, 1:]  # Exclude self
    
    # Subset neighbors (train only)
    train_embeddings = embeddings[train_idx]
    train_to_full = {i: idx for i, idx in enumerate(train_idx)}
    
    nn_sub = NearestNeighbors(n_neighbors=11, metric='cosine')
    nn_sub.fit(train_embeddings)
    
    # For test points, find neighbors in train set
    _, sub_neighbors = nn_sub.kneighbors(embeddings[test_idx])
    sub_neighbors = sub_neighbors[:, 1:]  # Exclude self (but self not in train)
    
    # Map back to full indices
    sub_neighbors_full = np.array([[train_to_full[n] for n in row] for row in sub_neighbors])
    
    # Compute neighbor overlap for test points
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
    """
    Test resistance to procedural boilerplate.
    
    Decisions with similar procedural posture but different legal issues
    should NOT be nearest neighbors.
    
    Proxy: Check if decisions from same chamber but different legal areas
    are clustered together (bad) vs decisions from different chambers
    but same legal area (good).
    """
    n = embeddings.shape[0]
    
    # Build NN graph
    nn = NearestNeighbors(n_neighbors=11, metric='cosine')
    nn.fit(embeddings)
    _, indices = nn.kneighbors(embeddings)
    neighbors = indices[:, 1:]
    
    chambers = [m.get('chamber', 'unknown') for m in metadata]
    legal_areas = [m.get('legal_area', 'unknown') for m in metadata]
    legal_areas = [la if la and la != 'null' else 'unknown' for la in legal_areas]
    
    # Count: same chamber/diff legal_area vs diff chamber/same legal_area in top-10
    boilerplate_neighbors = 0  # Same chamber, different legal area (bad)
    legal_neighbors = 0        # Different chamber, same legal area (good)
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
    
    # Good resistance = low boilerplate_rate, high legal_rate
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
# FRACTAL QUALITY (frozen - hierarchical Leiden)
# ============================================================

sys.path.insert(0, '/tmp/lex_accepted/fractal-map/fractal_map/hierarchical')
try:
    from hierarchical_leiden import hierarchical_leiden, compute_branch_purity
    HAS_HIERARCHICAL_LEIDEN = True
except ImportError:
    HAS_HIERARCHICAL_LEIDEN = False
    def hierarchical_leiden(*args, **kwargs):
        return None, None, {}
    def compute_branch_purity(labels, metadata):
        return 0.0

def run_fractal_quality_benchmarks(embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Any]:
    """Run fractal-map quality benchmarks (hierarchical Leiden, zoom coherence)."""
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
        # Fallback if hierarchical Leiden not available
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
    """Run the two critical adversarial benchmarks."""
    branches, languages, chambers, valid_indices = prepare_metadata(metadata)
    rep_valid = embeddings[valid_indices]
    meta_valid = [metadata[i] for i in valid_indices]
    
    # 1. Adversarial language dominance
    lang_dom = adversarial_language_dominance(rep_valid, meta_valid)
    
    # 2. Jurist pairwise preference
    jurist_pref = simulate_pairwise_preference(rep_valid, branches, languages)
    
    return {
        'adversarial_language_dominance': lang_dom,
        'jurist_pairwise_preference': jurist_pref,
        'both_pass': lang_dom.get('status') == 'PASS' and jurist_pref.get('status') == 'PASS',
        'language_dominance_score': lang_dom.get('mean_language_dominance', 1.0),
        'jurist_preference_rate': jurist_pref.get('jurist_would_succeed_rate', 0.0),
    }

def evaluate_representation(name: str, embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Any]:
    """Evaluate a single representation against all frozen benchmarks."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Evaluating: {name}")
    logger.info(f"Shape: {embeddings.shape}")
    logger.info(f"{'='*60}")
    
    start_time = time.time()
    
    # Adversarial benchmarks
    logger.info("Running adversarial benchmarks...")
    adv_results = run_adversarial_benchmarks(embeddings, metadata)
    
    # Jurivoc hierarchy alignment
    logger.info("Running Jurivoc hierarchy alignment...")
    jurivoc_results = compute_jurivoc_alignment(embeddings, metadata)
    
    # Scale stability
    logger.info("Running scale stability...")
    scale_results = compute_scale_stability(embeddings, metadata)
    
    # Boilerplate resistance
    logger.info("Running boilerplate resistance...")
    boilerplate_results = compute_boilerplate_resistance(embeddings, metadata)
    
    # Fractal quality benchmarks
    logger.info("Running fractal quality benchmarks...")
    fractal_results = run_fractal_quality_benchmarks(embeddings, metadata)
    
    duration = time.time() - start_time
    
    # Overall verdict: MUST pass BOTH adversarial gates
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
    set_global_seed(GLOBAL_SEED)
    
    config_hash = get_config_hash()
    
    logger.info("=" * 70)
    logger.info(f"Evaluation Lane v3 - Frozen Evaluation Harness")
    logger.info(f"Config hash: {config_hash}")
    logger.info(f"Global seed: {GLOBAL_SEED}")
    logger.info(f"Factory direction: v{FACTORY_DIRECTION_VERSION}")
    logger.info("=" * 70)
    
    # Load metadata
    logger.info("\n1. Loading evaluation metadata...")
    metadata = load_evaluation_metadata()
    logger.info(f"Loaded metadata for {len(metadata)} decisions")
    
    # Define representations to test (frozen list)
    representations = {
        'center_projected_768': CP_768_PATH,
        'center_projected_64dim': CP_64_PATH,
        'linear_metric_epoch4': LINEAR_METRIC_PATH,
        'mahalanobis_metric_epoch4': MAHALANOBIS_METRIC_PATH,
        'hybrid_stabilized_epoch1': HYBRID_STABILIZED_PATH,
        'hybrid_v2_epoch3': HYBRID_V2_PATH,
    }
    
    # Load and evaluate each
    logger.info("\n2. Loading representations and running evaluations...")
    all_results = {}
    
    for name, path in representations.items():
        if not path.exists():
            logger.warning(f"  {name}: NOT FOUND at {path}")
            all_results[name] = {'error': f'File not found: {path}', 'verdict': 'ERROR'}
            continue
        
        try:
            embeddings = np.load(path)
            logger.info(f"  Loaded {name}: {embeddings.shape}")
            
            result = evaluate_representation(name, embeddings, metadata)
            all_results[name] = result
            
            # Log summary
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
            all_results[name] = {
                'name': name,
                'error': str(e),
                'verdict': 'ERROR'
            }
    
    # Save all results
    output_file = OUTPUT_DIR / "evaluation_v3_results.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Generate summary report
    logger.info("\n" + "=" * 90)
    logger.info("EVALUATION v3 - FROZEN HARNESS SUMMARY")
    logger.info("=" * 90)
    logger.info(f"Config hash: {config_hash} | Global seed: {GLOBAL_SEED} | Factory direction: v{FACTORY_DIRECTION_VERSION}")
    logger.info("-" * 90)
    logger.info(f"{'Representation':<30} {'Verdict':<7} {'LangDom':>7} {'LD-P':>5} {'Jurist':>7} {'JP-P':>5} {'Both':>5} {'Jurivoc0':>8} {'Scale':>6} {'Boiler':>7} {'ImpRate':>7}")
    logger.info("-" * 90)
    
    # Sort by adversarial pass, then jurist preference, then language dominance
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
            logger.info(f"{name:<30} {'ERROR':<7} {'N/A':>7} {'N/A':>5} {'N/A':>7} {'N/A':>5} {'N/A':>5} {'N/A':>8} {'N/A':>6} {'N/A':>7} {'N/A':>7}")
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
        
        logger.info(f"{name:<30} {res['verdict']:<7} {ld:>7.4f} {ld_pass:>5} {jp:>7.4f} {jp_pass:>5} {both:>5} "
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
    
    # Reference baseline (center_projected_64dim - production default)
    if 'center_projected_64dim' in all_results and 'error' not in all_results['center_projected_64dim']:
        ref = all_results['center_projected_64dim']
        logger.info(f"\n📏 REFERENCE BASELINE (center_projected_64dim - production default):")
        logger.info(f"   Language dominance: {ref['adversarial']['language_dominance_score']:.4f} ({ref['adversarial']['adversarial_language_dominance']['status']})")
        logger.info(f"   Jurist preference: {ref['adversarial']['jurist_preference_rate']:.4f} ({ref['adversarial']['jurist_pairwise_preference']['status']})")
        logger.info(f"   Both adversarial pass: {ref['both_adversarial_pass']}")
    
    logger.info(f"\nResults saved to: {output_file}")
    logger.info("=" * 90)
    
    return all_results, config_hash

if __name__ == "__main__":
    main()