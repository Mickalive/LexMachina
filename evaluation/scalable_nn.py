#!/usr/bin/env python3
"""
Scalable Nearest Neighbor Infrastructure for LexMachina Evaluation

Uses HNSW (Hierarchical Navigable Small World) via hnswlib for 
approximate nearest neighbor search at 192k+ scale with exact 
fallback for small corpuses (<10k).

Maintains frozen harness v3 compatibility: same metrics, thresholds, seed.
"""

import numpy as np
import logging
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
import json
import time

try:
    import hnswlib
    HNSWLIB_AVAILABLE = True
except ImportError:
    HNSWLIB_AVAILABLE = False
    hnswlib = None

try:
    from sklearn.neighbors import NearestNeighbors
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

logger = logging.getLogger(__name__)

# Frozen configuration (must match evaluation_v3_harness.py)
GLOBAL_SEED = 42
K_NEIGHBORS_LANG_DOM = 20
K_NEIGHBORS_JURIST = 10
K_NEIGHBORS_CROSS_LANG = 10

# HNSW parameters (tuned for legal corpus)
HNSW_M = 16          # Number of bi-directional links per element
HNSW_EF_CONSTRUCTION = 200  # Size of dynamic candidate list during construction
HNSW_EF_SEARCH = 100        # Size of dynamic candidate list during search (accuracy/speed tradeoff)

# Scale thresholds
EXACT_NN_THRESHOLD = 10000  # Use exact NN below this size
BATCH_SIZE = 5000           # Batch size for memory-efficient processing


class ScalableNearestNeighbors:
    """
    Scalable nearest neighbor search with automatic backend selection.
    
    For small corpuses (<10k): uses sklearn exact NearestNeighbors (cosine)
    For large corpuses (>=10k): uses HNSW approximate NN (cosine via inner product on normalized vectors)
    
    Both backends produce comparable results for evaluation purposes.
    """
    
    def __init__(
        self, 
        n_neighbors: int = 20,
        metric: str = 'cosine',
        force_exact: bool = False,
        seed: int = GLOBAL_SEED
    ):
        self.n_neighbors = n_neighbors
        self.metric = metric
        self.force_exact = force_exact
        self.seed = seed
        self.index = None
        self.backend = None
        self.embeddings = None
        self.dim = None
        self._normalized = None
        
    def fit(self, embeddings: np.ndarray) -> 'ScalableNearestNeighbors':
        """Build the nearest neighbor index."""
        np.random.seed(self.seed)
        
        self.embeddings = embeddings
        self.dim = embeddings.shape[1]
        n_samples = embeddings.shape[0]
        
        # Normalize embeddings for cosine similarity (HNSW uses inner product)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self._normalized = embeddings / norms
        
        # Choose backend
        use_exact = self.force_exact or n_samples < EXACT_NN_THRESHOLD or not HNSWLIB_AVAILABLE
        
        if use_exact and SKLEARN_AVAILABLE:
            logger.info(f"Building exact NN index (sklearn) for {n_samples} samples...")
            self.index = NearestNeighbors(
                n_neighbors=min(self.n_neighbors + 1, n_samples),
                metric='cosine',
                algorithm='brute',  # Brute force is exact for cosine
                n_jobs=-1
            )
            self.index.fit(self._normalized)
            self.backend = 'sklearn_exact'
            logger.info("Exact NN index built successfully")
            
        elif HNSWLIB_AVAILABLE:
            logger.info(f"Building HNSW index for {n_samples} samples (M={HNSW_M}, ef_construction={HNSW_EF_CONSTRUCTION})...")
            start = time.time()
            
            # HNSW with inner product space (cosine on normalized vectors)
            self.index = hnswlib.Index(space='ip', dim=self.dim)
            self.index.init_index(
                max_elements=n_samples,
                ef_construction=HNSW_EF_CONSTRUCTION,
                M=HNSW_M,
                random_seed=self.seed
            )
            
            # Add items in batches for memory efficiency
            batch_size = min(BATCH_SIZE, n_samples)
            for i in range(0, n_samples, batch_size):
                end = min(i + batch_size, n_samples)
                self.index.add_items(self._normalized[i:end], np.arange(i, end))
            
            # Set search ef parameter
            self.index.set_ef(HNSW_EF_SEARCH)
            
            self.backend = 'hnsw'
            logger.info(f"HNSW index built in {time.time() - start:.2f}s")
            
        else:
            raise RuntimeError("No NN backend available. Install sklearn or hnswlib.")
            
        return self
    
    def kneighbors(
        self, 
        query_embeddings: Optional[np.ndarray] = None,
        n_neighbors: Optional[int] = None,
        return_distance: bool = True
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Find k-nearest neighbors.
        
        Args:
            query_embeddings: Query vectors (default: use fitted embeddings)
            n_neighbors: Number of neighbors (default: self.n_neighbors)
            return_distance: Whether to return distances
            
        Returns:
            (distances, indices) arrays
        """
        if self.index is None:
            raise RuntimeError("Index not fitted. Call fit() first.")
            
        k = n_neighbors or self.n_neighbors
        
        if query_embeddings is None:
            query_embeddings = self._normalized
        else:
            # Normalize query embeddings
            norms = np.linalg.norm(query_embeddings, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            query_embeddings = query_embeddings / norms
        
        n_queries = query_embeddings.shape[0]
        
        if self.backend == 'sklearn_exact':
            # sklearn returns (n_queries, k+1) including self
            distances, indices = self.index.kneighbors(
                query_embeddings, 
                n_neighbors=min(k + 1, self.embeddings.shape[0]),
                return_distance=return_distance
            )
            # Exclude self (first neighbor)
            if query_embeddings is self._normalized:
                distances = distances[:, 1:]
                indices = indices[:, 1:]
                
        elif self.backend == 'hnsw':
            # HNSW knn_query returns (labels, distances) - no self-exclusion
            # For self-query, we need to exclude the query point itself
            labels, distances = self.index.knn_query(query_embeddings, k=k + (1 if query_embeddings is self._normalized else 0))
            
            if query_embeddings is self._normalized:
                # Exclude self (first result for each query)
                distances = distances[:, 1:]
                labels = labels[:, 1:]
            else:
                distances = distances[:, :k]
                labels = labels[:, :k]
            indices = labels
            
        else:
            raise RuntimeError(f"Unknown backend: {self.backend}")
        
        if not return_distance:
            return indices
        
        # Convert inner product distances to cosine distances for consistency
        # cosine_distance = 1 - cosine_similarity = 1 - inner_product (for normalized)
        if self.backend == 'hnsw':
            distances = 1.0 - distances
            
        return distances, indices
    
    def kneighbors_graph(self, n_neighbors: Optional[int] = None) -> np.ndarray:
        """Return neighbor indices for all points (excluding self)."""
        _, indices = self.kneighbors(n_neighbors=n_neighbors)
        return indices


def build_scalable_nn(
    embeddings: np.ndarray,
    n_neighbors: int = 20,
    force_exact: bool = False,
    seed: int = GLOBAL_SEED
) -> ScalableNearestNeighbors:
    """Factory function to build scalable NN index."""
    return ScalableNearestNeighbors(
        n_neighbors=n_neighbors,
        force_exact=force_exact,
        seed=seed
    ).fit(embeddings)


# ============================================================
# BATCHED EVALUATION UTILITIES
# ============================================================

def batched_adversarial_language_dominance(
    nn_index: ScalableNearestNeighbors,
    metadata: List[Dict],
    k: int = K_NEIGHBORS_LANG_DOM,
    batch_size: int = BATCH_SIZE
) -> Dict[str, Any]:
    """
    Compute adversarial language dominance in batches for memory efficiency.
    
    Language dominance = fraction of k-NN that share the same language.
    """
    n = len(metadata)
    languages = [m.get('language', 'unknown') for m in metadata]
    
    all_dominance_rates = []
    
    for start in range(0, n, batch_size):
        end = min(start + batch_size, n)
        batch_indices = nn_index.kneighbors(n_neighbors=k)[1][start:end]
        
        for i, neighbor_indices in enumerate(batch_indices):
            lang = languages[start + i]
            neighbor_langs = [languages[n_idx] for n_idx in neighbor_indices]
            same_lang = sum(1 for l in neighbor_langs if l == lang)
            all_dominance_rates.append(same_lang / k)
    
    dominance_rates = np.array(all_dominance_rates)
    mean_dominance = float(np.mean(dominance_rates))
    
    return {
        'mean_language_dominance': mean_dominance,
        'std_language_dominance': float(np.std(dominance_rates)),
        'max_language_dominance': float(np.max(dominance_rates)),
        'k': k,
        'threshold': 0.85,  # Frozen threshold
        'status': 'PASS' if mean_dominance < 0.85 else 'FAIL',
        'note': 'Lower is better - language should not dominate neighbors',
        'backend': nn_index.backend
    }


def batched_jurist_pairwise_preference(
    nn_index: ScalableNearestNeighbors,
    metadata: List[Dict],
    branches: np.ndarray,
    languages: np.ndarray,
    k: int = K_NEIGHBORS_JURIST,
    batch_size: int = BATCH_SIZE
) -> Dict[str, Any]:
    """
    Simulate jurist pairwise preference in batches.
    
    Jurist prefers: same branch, different language (legally relevant)
    over: same language, different branch (language artifact)
    """
    n = len(metadata)
    all_neighbors = nn_index.kneighbors(n_neighbors=k)[1]
    
    legal_relevant_count = 0
    language_artifact_count = 0
    both_count = 0
    neither_count = 0
    
    for i in range(n):
        branch_i = branches[i]
        lang_i = languages[i]
        neighbor_indices = all_neighbors[i]
        
        has_legal_relevant = False
        has_language_artifact = False
        
        for n_idx in neighbor_indices:
            if branches[n_idx] == branch_i and languages[n_idx] != lang_i:
                has_legal_relevant = True
            if branches[n_idx] != branch_i and languages[n_idx] == lang_i:
                has_language_artifact = True
        
        if has_legal_relevant and has_language_artifact:
            both_count += 1
        elif has_legal_relevant:
            legal_relevant_count += 1
        elif has_language_artifact:
            language_artifact_count += 1
        else:
            neither_count += 1
    
    total = n
    legal_neighbor_rate = (legal_relevant_count + both_count) / total
    language_neighbor_rate = (language_artifact_count + both_count) / total
    jurist_correct = legal_relevant_count + both_count
    jurist_forced_wrong = language_artifact_count
    
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
        "note": "Simulated jurist prefers legally-relevant neighbors. Rate > 0.5 means majority of decisions have at least one legally-relevant neighbor in top-k.",
        'backend': nn_index.backend
    }


def batched_cross_language_retrieval(
    nn_index: ScalableNearestNeighbors,
    metadata: List[Dict],
    branches: np.ndarray,
    languages: np.ndarray,
    k: int = K_NEIGHBORS_CROSS_LANG,
    batch_size: int = BATCH_SIZE
) -> Dict[str, Any]:
    """
    Simulate jurist cross-language retrieval task in batches.
    
    Jurist has a German decision and wants to find related French decisions.
    """
    from collections import defaultdict, Counter
    
    n = len(metadata)
    
    # Group by branch and language
    branch_lang_groups = defaultdict(list)
    for i in range(n):
        key = (branches[i], languages[i])
        branch_lang_groups[key].append(i)
    
    all_neighbors = nn_index.kneighbors(n_neighbors=k)[1]
    
    cross_lang_recall_rates = []
    
    for i in range(n):
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
        neighbor_set = set(all_neighbors[i])
        found = sum(1 for gt in cross_lang_gt if gt in neighbor_set)
        recall = found / min(len(cross_lang_gt), k)
        cross_lang_recall_rates.append(recall)
    
    mean_recall = float(np.mean(cross_lang_recall_rates)) if cross_lang_recall_rates else 0.0
    
    return {
        "status": "PASS" if mean_recall > 0.2 else "FAIL",
        "mean_cross_language_recall_at_k": round(mean_recall, 4),
        "k": k,
        "n_queries": len(cross_lang_recall_rates),
        "note": "Simulated jurist searches for cross-language legal equivalents. Recall > 0.2 means at least 1 in 5 cross-language legal equivalents appears in top-10.",
        'backend': nn_index.backend
    }


def batched_scale_stability(
    embeddings: np.ndarray,
    metadata: List[Dict],
    train_fraction: float = 0.8,
    k: int = 10,
    seed: int = GLOBAL_SEED
) -> Dict[str, Any]:
    """
    Test stability of neighbor structure under corpus subsampling.
    
    Uses scalable NN for both full and subset.
    """
    n = embeddings.shape[0]
    if n < 100:
        return {"status": "SKIP", "note": "Insufficient decisions for scale stability test"}
    
    np.random.seed(seed)
    indices = np.arange(n)
    np.random.shuffle(indices)
    
    split_idx = int(train_fraction * n)
    train_idx = indices[:split_idx]
    test_idx = indices[split_idx:]
    
    # Full corpus neighbors (using scalable NN)
    nn_full = build_scalable_nn(embeddings, n_neighbors=k+1)
    _, full_neighbors = nn_full.kneighbors(n_neighbors=k+1)
    full_neighbors = full_neighbors[:, 1:]  # Exclude self
    
    # Subset neighbors
    train_embeddings = embeddings[train_idx]
    nn_sub = build_scalable_nn(train_embeddings, n_neighbors=k+1)
    
    # For test points, find neighbors in train set
    _, sub_neighbors = nn_sub.kneighbors(embeddings[test_idx], n_neighbors=k+1)
    sub_neighbors = sub_neighbors[:, 1:]  # Exclude self (not in train)
    
    # Map back to full indices
    train_to_full = {i: idx for i, idx in enumerate(train_idx)}
    sub_neighbors_full = np.array([[train_to_full[n] for n in row] for row in sub_neighbors])
    
    # Compute neighbor overlap for test points
    overlaps = []
    for i, test_i in enumerate(test_idx):
        full_set = set(full_neighbors[test_i])
        sub_set = set(sub_neighbors_full[i])
        overlap = len(full_set & sub_set) / len(full_set) if len(full_set) > 0 else 0
        overlaps.append(overlap)
    
    mean_overlap = float(np.mean(overlaps))
    
    return {
        "mean_neighbor_overlap": mean_overlap,
        "std_neighbor_overlap": float(np.std(overlaps)),
        "n_test_points": len(test_idx),
        "status": "PASS" if mean_overlap > 0.5 else "FAIL",
        "note": "Scale stability: fraction of top-10 neighbors preserved when corpus reduced to 80%. Higher = more stable.",
        'backend': nn_full.backend
    }


def batched_boilerplate_resistance(
    nn_index: ScalableNearestNeighbors,
    metadata: List[Dict],
    k: int = 10,
    batch_size: int = BATCH_SIZE
) -> Dict[str, Any]:
    """
    Test resistance to procedural boilerplate in batches.
    
    Same chamber, different legal_area = boilerplate neighbor (bad)
    Different chamber, same legal_area = legal neighbor (good)
    """
    n = len(metadata)
    chambers = [m.get('chamber', 'unknown') for m in metadata]
    legal_areas = [m.get('legal_area', 'unknown') for m in metadata]
    legal_areas = [la if la and la != 'null' else 'unknown' for la in legal_areas]
    
    all_neighbors = nn_index.kneighbors(n_neighbors=k)[1]
    
    boilerplate_neighbors = 0
    legal_neighbors = 0
    total_comparisons = 0
    
    for i in range(n):
        chamber_i = chambers[i]
        legal_i = legal_areas[i]
        
        for n_idx in all_neighbors[i]:
            chamber_j = chambers[n_idx]
            legal_j = legal_areas[n_idx]
            
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
        "note": "Boilerplate resistance: legal_neighbor_rate - boilerplate_neighbor_rate. Positive = legally relevant neighbors dominate over procedural neighbors.",
        'backend': nn_index.backend
    }


def batched_jurivoc_alignment(
    embeddings: np.ndarray,
    metadata: List[Dict],
    seed: int = GLOBAL_SEED
) -> Dict[str, Any]:
    """
    Compute alignment with Jurivoc hierarchy (batched KMeans).
    
    Uses branch as Level 0 (4 clusters), legal_area as Level 1 (~16 clusters).
    """
    from sklearn.cluster import KMeans
    from sklearn.metrics import normalized_mutual_info_score
    from collections import Counter
    
    branches = [m.get('branch', 'unknown') for m in metadata]
    legal_areas = [m.get('legal_area', 'unknown') for m in metadata]
    legal_areas = [la if la and la != 'null' else 'unknown' for la in legal_areas]
    
    # Level 0: 4 clusters (branches)
    kmeans_l0 = KMeans(n_clusters=4, random_state=seed, n_init=10)
    labels_l0 = kmeans_l0.fit_predict(embeddings)
    nmi_l0 = float(normalized_mutual_info_score(branches, labels_l0))
    
    # Level 1: 16 clusters (legal areas)
    kmeans_l1 = KMeans(n_clusters=16, random_state=seed, n_init=10)
    labels_l1 = kmeans_l1.fit_predict(embeddings)
    nmi_l1 = float(normalized_mutual_info_score(legal_areas, labels_l1))
    
    # Hierarchical consistency (nesting score)
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
                    if branch_in_sub:
                        majority = Counter(branch_in_sub).most_common(1)[0][1]
                        subcluster_purities.append(majority / len(branch_in_sub))
            if subcluster_purities:
                nesting_score += np.mean(subcluster_purities)
    nesting_score /= 4
    
    return {
        "level_0_nmi": nmi_l0,
        "level_1_nmi": nmi_l1,
        "nesting_score": float(nesting_score),
        "status": "PASS" if nmi_l0 > 0.3 and nmi_l1 > 0.2 else "FAIL",
        "note": "Jurivoc proxy: Level 0 = 4 branches, Level 1 = 16 legal areas. Higher NMI = better alignment with legal taxonomy."
    }


def batched_cluster_coherence(
    embeddings: np.ndarray,
    branches: np.ndarray,
    languages: np.ndarray,
    n_clusters: int = 16,
    seed: int = GLOBAL_SEED
) -> Dict[str, Any]:
    """Simulate jurist cluster coherence rating (batched KMeans)."""
    from sklearn.cluster import KMeans
    from sklearn.metrics import normalized_mutual_info_score
    from collections import Counter
    
    kmeans = KMeans(n_clusters=n_clusters, random_state=seed, n_init=10)
    cluster_labels = kmeans.fit_predict(embeddings)
    
    # Compute branch purity per cluster
    cluster_purities = []
    cluster_sizes = []
    
    for c in range(n_clusters):
        mask = cluster_labels == c
        if np.sum(mask) == 0:
            continue
        cluster_branches = branches[mask]
        majority = Counter(cluster_branches).most_common(1)[0][0]
        purity = np.mean(cluster_branches == majority)
        cluster_purities.append(float(purity))
        cluster_sizes.append(int(np.sum(mask)))
    
    mean_purity = float(np.mean(cluster_purities)) if cluster_purities else 0.0
    nmi = float(normalized_mutual_info_score(branches, cluster_labels))
    
    # Language purity
    lang_purities = []
    for c in range(n_clusters):
        mask = cluster_labels == c
        if np.sum(mask) == 0:
            continue
        cluster_langs = languages[mask]
        majority = Counter(cluster_langs).most_common(1)[0][0]
        purity = np.mean(cluster_langs == majority)
        lang_purities.append(float(purity))
    
    mean_lang_purity = float(np.mean(lang_purities)) if lang_purities else 0.0
    
    return {
        "status": "PASS" if mean_purity > 0.7 else "FAIL",
        "n_clusters": n_clusters,
        "mean_branch_purity": round(mean_purity, 4),
        "branch_nmi": round(nmi, 4),
        "mean_language_purity": round(mean_lang_purity, 4),
        "cluster_purities": [round(p, 4) for p in cluster_purities],
        "cluster_sizes": cluster_sizes,
        "note": "Simulated jurist rates clusters by branch coherence. High branch purity = legally coherent clusters. High language purity = language-dominated clusters."
    }


# ============================================================
# DISTRIBUTED EVALUATION SUPPORT
# ============================================================

class DistributedEvaluator:
    """
    Supports distributed evaluation across multiple workers.
    
    Each worker evaluates a subset of representations on the full corpus,
    or evaluates all representations on a shard of the corpus.
    """
    
    def __init__(
        self,
        worker_id: int,
        n_workers: int,
        output_dir: Path,
        seed: int = GLOBAL_SEED
    ):
        self.worker_id = worker_id
        self.n_workers = n_workers
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.seed = seed
        
    def shard_indices(self, n_total: int) -> np.ndarray:
        """Get indices assigned to this worker (corpus sharding)."""
        np.random.seed(self.seed)
        indices = np.arange(n_total)
        np.random.shuffle(indices)
        
        # Split evenly
        shard_size = n_total // self.n_workers
        start = self.worker_id * shard_size
        end = start + shard_size if self.worker_id < self.n_workers - 1 else n_total
        return indices[start:end]
    
    def shard_representations(self, representations: List[str]) -> List[str]:
        """Get representations assigned to this worker (model sharding)."""
        per_worker = len(representations) // self.n_workers
        start = self.worker_id * per_worker
        end = start + per_worker if self.worker_id < self.n_workers - 1 else len(representations)
        return representations[start:end]
    
    def save_partial_results(self, results: Dict, suffix: str = ""):
        """Save partial results for this worker."""
        fname = f"partial_results_worker{self.worker_id}{suffix}.json"
        with open(self.output_dir / fname, 'w') as f:
            json.dump(results, f, indent=2, default=str)
    
    @staticmethod
    def merge_results(result_dirs: List[Path], output_file: Path):
        """Merge partial results from all workers."""
        all_results = {}
        for result_dir in result_dirs:
            for json_file in result_dir.glob("partial_results_worker*.json"):
                with open(json_file) as f:
                    partial = json.load(f)
                    all_results.update(partial)
        
        with open(output_file, 'w') as f:
            json.dump(all_results, f, indent=2, default=str)
        
        logger.info(f"Merged results from {len(result_dirs)} workers to {output_file}")
        return all_results


# ============================================================
# COMPATIBILITY LAYER FOR FROZEN HARNESS v3
# ============================================================

def run_scalable_adversarial_benchmarks(
    embeddings: np.ndarray,
    metadata: List[Dict],
    force_exact: bool = False
) -> Dict[str, Any]:
    """
    Drop-in replacement for run_adversarial_benchmarks in frozen harness.
    
    Uses scalable NN backend but returns identical output format.
    """
    from evaluation.evaluation_v3_harness import prepare_metadata
    
    branches, languages, chambers, valid_indices = prepare_metadata(metadata)
    rep_valid = embeddings[valid_indices]
    meta_valid = [metadata[i] for i in valid_indices]
    
    # Build scalable NN index
    nn_index = build_scalable_nn(rep_valid, n_neighbors=max(K_NEIGHBORS_LANG_DOM, K_NEIGHBORS_JURIST), force_exact=force_exact)
    
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
    }


def run_scalable_full_evaluation(
    embeddings: np.ndarray,
    metadata: List[Dict],
    force_exact: bool = False
) -> Dict[str, Any]:
    """
    Run all frozen benchmarks using scalable infrastructure.
    
    Returns same format as evaluate_representation in frozen harness.
    """
    from evaluation.evaluation_v3_harness import prepare_metadata, compute_jurivoc_alignment
    
    branches, languages, chambers, valid_indices = prepare_metadata(metadata)
    rep_valid = embeddings[valid_indices]
    meta_valid = [metadata[i] for i in valid_indices]
    
    # Build scalable NN index
    nn_index = build_scalable_nn(rep_valid, n_neighbors=max(K_NEIGHBORS_LANG_DOM, K_NEIGHBORS_JURIST, K_NEIGHBORS_CROSS_LANG), force_exact=force_exact)
    
    # Adversarial benchmarks
    adv_results = run_scalable_adversarial_benchmarks(rep_valid, meta_valid, force_exact=force_exact)
    
    # Jurivoc hierarchy alignment
    jurivoc_results = batched_jurivoc_alignment(rep_valid, meta_valid)
    
    # Scale stability (uses its own NN internally)
    scale_results = batched_scale_stability(rep_valid, meta_valid)
    
    # Boilerplate resistance
    boilerplate_results = batched_boilerplate_resistance(nn_index, meta_valid)
    
    # Cluster coherence
    cluster_coherence = batched_cluster_coherence(rep_valid, branches, languages)
    
    # Cross-language retrieval
    cross_lang = batched_cross_language_retrieval(nn_index, meta_valid, branches, languages)
    
    # Fractal quality (simplified for scale - no hierarchical Leiden)
    fractal_results = {
        'n_coarse': 0, 'n_fine': 0, 'coarse_purity': 0.0, 'fine_purity': 0.0,
        'overall_improvement': 0.0, 'improvement_rate': 0.0,
        'legal_area_nmi': 0.0, 'flat_purity': 0.0, 'hierarchical_advantage': 0.0,
        'cluster_coherence': cluster_coherence,
        'cross_language_retrieval': cross_lang,
    }
    
    both_adv_pass = adv_results['both_pass']
    verdict = "PASS" if both_adv_pass else "FAIL"
    
    return {
        'embedding_shape': list(embeddings.shape),
        'adversarial': adv_results,
        'jurivoc_alignment': jurivoc_results,
        'scale_stability': scale_results,
        'boilerplate_resistance': boilerplate_results,
        'fractal': fractal_results,
        'verdict': verdict,
        'both_adversarial_pass': both_adv_pass,
        'backend': nn_index.backend
    }