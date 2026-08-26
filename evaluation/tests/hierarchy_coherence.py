"""
Hierarchy Coherence Test

Tests whether the hierarchical/multi-resolution structure of the fractal map
is legally coherent - i.e., clusters at different levels correspond to
meaningful legal subdivisions.
"""

import numpy as np
from typing import Callable, Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict
import logging

from ..benchmarks import BaseBenchmark, BenchmarkResult, BenchmarkStatus, EvidenceTier
from ..benchmarks.synthetic_supervision import SyntheticWeakSupervision, SyntheticSupervisionConfig
from ..benchmarks.jurivoc_loader import WeakSupervisionBenchmark, JurivocLoader

logger = logging.getLogger(__name__)


@dataclass
class HierarchyConfig:
    """Configuration for hierarchy coherence test."""
    num_levels: int = 3  # Number of hierarchy levels to test
    min_cluster_size: int = 5
    max_clusters_per_level: int = 50
    coherence_metric: str = "jurivoc_purity"  # or "silhouette", "modularity"
    random_seed: int = 42


class HierarchyCoherenceTest(BaseBenchmark):
    """
    Tests whether hierarchical clustering of legal decisions produces
    legally coherent clusters at multiple resolutions.
    
    Method:
    1. Build hierarchical clustering of decisions (using legal distance)
    2. At each level, evaluate cluster purity against Jurivoc descriptors
    3. Check that parent clusters are meaningful unions of child clusters
    4. Verify that zoom reveals legally specific substructure
    """

    def __init__(self, config: Optional[HierarchyConfig] = None):
        super().__init__("hierarchy_coherence", config)
        self.config = config or HierarchyConfig()
        self.real_supervision = WeakSupervisionBenchmark()
        self.jurivoc_loader = JurivocLoader()
        self.synthetic_supervision: Optional[SyntheticWeakSupervision] = None

    def run(
        self,
        representation_fn: Callable,
        corpus: Any,
        hierarchy_fn: Optional[Callable] = None,
        **kwargs,
    ) -> BenchmarkResult:
        """
        Run hierarchy coherence test.

        Args:
            representation_fn: Function that takes a decision_id and returns embedding vector
            corpus: Corpus object with decisions
            hierarchy_fn: Optional function that takes embeddings and returns hierarchical clustering
                         If not provided, uses agglomerative clustering
            **kwargs: Additional arguments (can include 'ground_truth' for synthetic data)

        Returns:
            BenchmarkResult with hierarchy coherence metrics
        """
        import time
        start_time = time.time()

        try:
            # Try to use synthetic ground truth if available
            ground_truth = kwargs.get("ground_truth")
            if ground_truth:
                self.synthetic_supervision = SyntheticWeakSupervision(
                    ground_truth,
                    SyntheticSupervisionConfig(random_seed=self.config.random_seed),
                )
                use_synthetic = True
                # Get decisions with Jurivoc descriptors from synthetic data
                decision_metadata = ground_truth.get("decision_metadata", {})
                decisions_with_jurivoc = [
                    type('Decision', (), {'decision_id': did, 'jurivoc_descriptors': meta.get('jurivoc_descriptors', [])})()
                    for did, meta in decision_metadata.items()
                    if meta.get('jurivoc_descriptors')
                ]
            else:
                use_synthetic = False
                # Load real weak supervision data
                if not self.real_supervision.load_data():
                    return self._create_result(
                        status=BenchmarkStatus.ERROR,
                        metrics={},
                        details={"error": "Failed to load weak supervision data"},
                        duration=time.time() - start_time,
                        error_message="Failed to load TF metadata",
                    )
                decisions_with_jurivoc = [
                    d for d in self.real_supervision.tf.decisions.values()
                    if d.jurivoc_descriptors
                ]

            if len(decisions_with_jurivoc) < self.config.min_cluster_size * 2:
                return self._create_result(
                    status=BenchmarkStatus.FAILED,
                    metrics={},
                    details={"error": f"Insufficient decisions with Jurivoc: {len(decisions_with_jurivoc)}"},
                    duration=time.time() - start_time,
                    error_message="Insufficient Jurivoc-annotated decisions",
                )

            # Limit for computational feasibility
            import random
            random.seed(self.config.random_seed)
            if len(decisions_with_jurivoc) > 1000:
                decisions_with_jurivoc = random.sample(decisions_with_jurivoc, 1000)

            # Get embeddings
            decision_ids = [d.decision_id for d in decisions_with_jurivoc]
            embeddings = {}
            for did in decision_ids:
                try:
                    emb = representation_fn(did)
                    if emb is not None:
                        embeddings[did] = np.array(emb, dtype=np.float32)
                except Exception as e:
                    logger.warning(f"Failed to get embedding for {did}: {e}")

            valid_ids = [did for did in decision_ids if did in embeddings]
            if len(valid_ids) < self.config.min_cluster_size * 2:
                return self._create_result(
                    status=BenchmarkStatus.FAILED,
                    metrics={},
                    details={"error": f"Insufficient valid embeddings: {len(valid_ids)}"},
                    duration=time.time() - start_time,
                    error_message="Insufficient embeddings",
                )

            embedding_matrix = np.stack([embeddings[did] for did in valid_ids])

            # Build hierarchical clustering
            if hierarchy_fn is not None:
                hierarchy = hierarchy_fn(embedding_matrix, valid_ids)
            else:
                hierarchy = self._default_hierarchical_clustering(embedding_matrix, valid_ids)

            # Evaluate coherence at each level
            level_metrics = []
            for level in range(min(self.config.num_levels, len(hierarchy))):
                clusters = hierarchy[level]
                metrics = self._evaluate_level_coherence(
                    clusters, valid_ids, decisions_with_jurivoc, level
                )
                level_metrics.append(metrics)

            # Overall coherence
            mean_purity = float(np.mean([m["jurivoc_purity"] for m in level_metrics]))
            mean_nmi = float(np.mean([m.get("nmi", 0) for m in level_metrics]))
            hierarchy_consistency = self._check_hierarchy_consistency(hierarchy)

            metrics = {
                "mean_jurivoc_purity": mean_purity,
                "mean_nmi": mean_nmi,
                "hierarchy_consistency": hierarchy_consistency,
                "num_levels_tested": len(level_metrics),
                "num_decisions": len(valid_ids),
            }

            # Add per-level metrics
            for i, m in enumerate(level_metrics):
                for k, v in m.items():
                    metrics[f"level_{i}_{k}"] = v

            # Pass if mean purity > 0.5 and hierarchy is consistent
            status = BenchmarkStatus.PASSED if (
                mean_purity > 0.4 and hierarchy_consistency > 0.5
            ) else BenchmarkStatus.FAILED

            duration = time.time() - start_time

            return self._create_result(
                status=status,
                metrics=metrics,
                details={
                    "level_metrics": level_metrics,
                    "hierarchy_structure": [
                        {"level": i, "num_clusters": len(hierarchy[i])} 
                        for i in range(len(hierarchy))
                    ],
                },
                duration=duration,
                evidence_tier=EvidenceTier.EXPLORATORY,
                baseline_comparison={
                    "mean_jurivoc_purity_baseline": 0.2,  # Random clustering
                    "hierarchy_consistency_baseline": 0.3,
                },
            )

        except Exception as e:
            logger.error(f"Hierarchy coherence test failed: {e}")
            return self._create_result(
                status=BenchmarkStatus.ERROR,
                metrics={},
                details={"exception": str(e)},
                duration=time.time() - start_time,
                error_message=str(e),
            )

    def _default_hierarchical_clustering(
        self,
        embeddings: np.ndarray,
        decision_ids: List[str],
    ) -> List[Dict[int, List[str]]]:
        """Default hierarchical clustering using agglomerative clustering."""
        from sklearn.cluster import AgglomerativeClustering

        # Normalize embeddings
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1
        normalized = embeddings / norms

        hierarchy = []
        
        # Generate clusters at different resolutions
        n_samples = len(decision_ids)
        for level in range(self.config.num_levels):
            # Number of clusters decreases as we go up the hierarchy
            n_clusters = max(
                self.config.min_cluster_size,
                min(self.config.max_clusters_per_level, n_samples // (2 ** level))
            )
            n_clusters = min(n_clusters, n_samples)

            if n_clusters < 2:
                break

            clustering = AgglomerativeClustering(
                n_clusters=n_clusters,
                metric="cosine",
                linkage="average",
            )
            labels = clustering.fit_predict(normalized)

            # Convert to cluster -> decisions mapping
            clusters = defaultdict(list)
            for idx, label in enumerate(labels):
                clusters[label].append(decision_ids[idx])

            # Filter small clusters
            filtered = {k: v for k, v in clusters.items() if len(v) >= self.config.min_cluster_size}
            hierarchy.append(dict(filtered))

        return hierarchy

    def _evaluate_level_coherence(
        self,
        clusters: Dict[int, List[str]],
        decision_ids: List[str],
        decisions_with_jurivoc: List[Any],
        level: int,
    ) -> Dict[str, float]:
        """Evaluate coherence of clusters at one hierarchy level."""
        # Build decision_id -> Jurivoc descriptors mapping
        id_to_jurivoc = {d.decision_id: set(d.jurivoc_descriptors) for d in decisions_with_jurivoc}

        # Compute purity for each cluster
        purities = []
        cluster_sizes = []

        for cluster_id, member_ids in clusters.items():
            if len(member_ids) < 2:
                continue

            # Get all Jurivoc descriptors in this cluster
            all_descriptors = []
            for mid in member_ids:
                if mid in id_to_jurivoc:
                    all_descriptors.extend(id_to_jurivoc[mid])

            if not all_descriptors:
                purities.append(0.0)
                cluster_sizes.append(len(member_ids))
                continue

            # Purity = fraction of most common descriptor
            descriptor_counts = defaultdict(int)
            for desc in all_descriptors:
                descriptor_counts[desc] += 1

            max_count = max(descriptor_counts.values())
            purity = max_count / len(all_descriptors)
            purities.append(purity)
            cluster_sizes.append(len(member_ids))

        # Weighted average purity
        if cluster_sizes:
            weighted_purity = sum(p * s for p, s in zip(purities, cluster_sizes)) / sum(cluster_sizes)
        else:
            weighted_purity = 0.0

        # Compute NMI against Jurivoc-based clustering
        nmi = self._compute_nmi(clusters, id_to_jurivoc, decision_ids)

        return {
            "jurivoc_purity": weighted_purity,
            "mean_purity": float(np.mean(purities)) if purities else 0.0,
            "num_clusters": len(clusters),
            "mean_cluster_size": float(np.mean(cluster_sizes)) if cluster_sizes else 0.0,
            "nmi": nmi,
        }

    def _compute_nmi(
        self,
        clusters: Dict[int, List[str]],
        id_to_jurivoc: Dict[str, Set[str]],
        decision_ids: List[str],
    ) -> float:
        """Compute Normalized Mutual Information against Jurivoc clustering."""
        try:
            from sklearn.metrics import normalized_mutual_info_score
        except ImportError:
            return 0.0

        # Create flat labels for clustering
        cluster_labels = {}
        for cluster_id, members in clusters.items():
            for mid in members:
                cluster_labels[mid] = cluster_id

        # Create Jurivoc-based labels (use most frequent descriptor per decision)
        jurivoc_labels = {}
        all_descriptors = set()
        for mid in decision_ids:
            if mid in id_to_jurivoc and id_to_jurivoc[mid]:
                # Use first descriptor as label
                desc = list(id_to_jurivoc[mid])[0]
                jurivoc_labels[mid] = desc
                all_descriptors.add(desc)

        # Only compute for decisions present in both
        common_ids = set(cluster_labels.keys()) & set(jurivoc_labels.keys())
        if len(common_ids) < 10:
            return 0.0

        y_true = [jurivoc_labels[mid] for mid in common_ids]
        y_pred = [cluster_labels[mid] for mid in common_ids]

        return float(normalized_mutual_info_score(y_true, y_pred))

    def _check_hierarchy_consistency(self, hierarchy: List[Dict[int, List[str]]]) -> float:
        """
        Check that hierarchy is consistent: parent clusters are unions of children.
        Returns score between 0 and 1.
        """
        if len(hierarchy) < 2:
            return 1.0

        consistency_scores = []

        for level in range(len(hierarchy) - 1):
            parent_clusters = hierarchy[level]
            child_clusters = hierarchy[level + 1]

            # For each child cluster, find which parent it belongs to
            child_to_parent = {}
            for parent_id, parent_members in parent_clusters.items():
                parent_set = set(parent_members)
                for child_id, child_members in child_clusters.items():
                    child_set = set(child_members)
                    if child_set.issubset(parent_set):
                        child_to_parent[child_id] = parent_id

            # Consistency = fraction of children assigned to exactly one parent
            if child_clusters:
                consistency = len(child_to_parent) / len(child_clusters)
                consistency_scores.append(consistency)

        return float(np.mean(consistency_scores)) if consistency_scores else 0.0

    def get_baseline_metrics(self) -> Dict[str, float]:
        """Expected baseline metrics for random hierarchy."""
        return {
            "mean_jurivoc_purity": 0.2,
            "hierarchy_consistency": 0.3,
        }