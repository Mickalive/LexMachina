"""
Neighbor Relevance Test

Tests whether nearest neighbors in the legal distance space are legally relevant.
Uses Jurivoc descriptors, citation lineage, and legal area as weak supervision.
"""

import numpy as np
from typing import Callable, Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging

from ..benchmarks import BaseBenchmark, BenchmarkResult, BenchmarkStatus, EvidenceTier
from ..benchmarks.synthetic_supervision import SyntheticWeakSupervision, SyntheticSupervisionConfig
from ..benchmarks.jurivoc_loader import WeakSupervisionBenchmark

logger = logging.getLogger(__name__)


@dataclass
class NeighborRelevanceConfig:
    """Configuration for neighbor relevance test."""
    k_values: List[int] = None  # k values for k-NN evaluation
    min_positive_pairs: int = 50
    max_pairs_per_query: int = 100
    use_jurivoc: bool = True
    use_citation_lineage: bool = True
    use_legal_area: bool = True
    random_seed: int = 42

    def __post_init__(self):
        if self.k_values is None:
            self.k_values = [1, 3, 5, 10, 20, 50]


class NeighborRelevanceTest(BaseBenchmark):
    """
    Tests whether nearest neighbors in the embedding space correspond to
    legally relevant decisions (sharing Jurivoc descriptors, citation lineage, or legal area).
    """

    def __init__(self, config: Optional[NeighborRelevanceConfig] = None):
        super().__init__("neighbor_relevance", config)
        self.config = config or NeighborRelevanceConfig()
        self.real_supervision = WeakSupervisionBenchmark()
        self.synthetic_supervision: Optional[SyntheticWeakSupervision] = None

    def run(
        self,
        representation_fn: Callable,
        corpus: Any,
        **kwargs,
    ) -> BenchmarkResult:
        """
        Run neighbor relevance test.

        Args:
            representation_fn: Function that takes a decision_id and returns embedding vector
            corpus: Corpus object with decision metadata
            **kwargs: Additional arguments (can include 'ground_truth' for synthetic data)

        Returns:
            BenchmarkResult with precision@k, recall@k, and AUC metrics
        """
        import time
        start_time = time.time()

        try:
            # Try to use synthetic ground truth if available
            ground_truth = kwargs.get("ground_truth")
            if ground_truth:
                self.synthetic_supervision = SyntheticWeakSupervision(
                    ground_truth,
                    SyntheticSupervisionConfig(
                        min_positive_pairs=self.config.min_positive_pairs,
                        max_pairs_per_query=self.config.max_pairs_per_query,
                        random_seed=self.config.random_seed,
                    ),
                )
                use_synthetic = True
            else:
                use_synthetic = False
                # Load real weak supervision data
                if not self.real_supervision.load_data():
                    return self._create_result(
                        status=BenchmarkStatus.ERROR,
                        metrics={},
                        details={"error": "Failed to load weak supervision data"},
                        duration=time.time() - start_time,
                        error_message="Failed to load Jurivoc/TF metadata",
                    )

            # Get test pairs from weak supervision
            all_positive_pairs = []
            all_negative_pairs = []

            if self.config.use_jurivoc:
                if use_synthetic:
                    jurivoc_bench = self.synthetic_supervision.create_jurivoc_similarity_benchmark()
                else:
                    jurivoc_bench = self.real_supervision.create_jurivoc_similarity_benchmark()
                all_positive_pairs.extend([(a, b) for a, b, _ in jurivoc_bench["positive_pairs"]])
                all_negative_pairs.extend(jurivoc_bench["negative_pairs"])
                logger.info(f"Jurivoc: {len(jurivoc_bench['positive_pairs'])} positive, {len(jurivoc_bench['negative_pairs'])} negative pairs")

            if self.config.use_citation_lineage:
                if use_synthetic:
                    citation_bench = self.synthetic_supervision.create_citation_lineage_benchmark()
                else:
                    citation_bench = self.real_supervision.create_citation_lineage_benchmark()
                all_positive_pairs.extend(citation_bench["lineage_pairs"])
                all_negative_pairs.extend(citation_bench["non_lineage_pairs"])
                logger.info(f"Citation: {len(citation_bench['lineage_pairs'])} positive, {len(citation_bench['non_lineage_pairs'])} negative pairs")

            if self.config.use_legal_area:
                if use_synthetic:
                    area_bench = self.synthetic_supervision.create_legal_area_benchmark()
                else:
                    area_bench = self.real_supervision.create_legal_area_benchmark()
                all_positive_pairs.extend([(a, b) for a, b, _ in area_bench["positive_pairs"]])
                all_negative_pairs.extend(area_bench["negative_pairs"])
                logger.info(f"Legal area: {len(area_bench['positive_pairs'])} positive, {len(area_bench['negative_pairs'])} negative pairs")

            # Limit pairs
            import random
            random.seed(self.config.random_seed)
            if len(all_positive_pairs) > self.config.max_pairs_per_query:
                all_positive_pairs = random.sample(all_positive_pairs, self.config.max_pairs_per_query)
            if len(all_negative_pairs) > self.config.max_pairs_per_query:
                all_negative_pairs = random.sample(all_negative_pairs, self.config.max_pairs_per_query)

            if len(all_positive_pairs) < self.config.min_positive_pairs:
                return self._create_result(
                    status=BenchmarkStatus.FAILED,
                    metrics={},
                    details={"error": f"Insufficient positive pairs: {len(all_positive_pairs)} < {self.config.min_positive_pairs}"},
                    duration=time.time() - start_time,
                    error_message="Insufficient weak supervision pairs",
                )

            # Compute embeddings for all unique decisions in pairs
            all_decision_ids = set()
            for a, b in all_positive_pairs + all_negative_pairs:
                all_decision_ids.add(a)
                all_decision_ids.add(b)

            embeddings = {}
            for decision_id in all_decision_ids:
                try:
                    emb = representation_fn(decision_id)
                    if emb is not None:
                        embeddings[decision_id] = np.array(emb, dtype=np.float32)
                except Exception as e:
                    logger.warning(f"Failed to get embedding for {decision_id}: {e}")

            # Compute similarities for all pairs
            positive_scores = []
            negative_scores = []

            for d1, d2 in all_positive_pairs:
                if d1 in embeddings and d2 in embeddings:
                    sim = self._cosine_similarity(embeddings[d1], embeddings[d2])
                    positive_scores.append(sim)

            for d1, d2 in all_negative_pairs:
                if d1 in embeddings and d2 in embeddings:
                    sim = self._cosine_similarity(embeddings[d1], embeddings[d2])
                    negative_scores.append(sim)

            # Compute metrics at different k values
            metrics = self._compute_ranking_metrics(
                embeddings, all_positive_pairs, all_negative_pairs
            )

            # AUC-ROC
            if positive_scores and negative_scores:
                from sklearn.metrics import roc_auc_score
                y_true = [1] * len(positive_scores) + [0] * len(negative_scores)
                y_scores = positive_scores + negative_scores
                metrics["auc_roc"] = float(roc_auc_score(y_true, y_scores))
            else:
                metrics["auc_roc"] = 0.5

            # Mean similarity gap
            if positive_scores and negative_scores:
                metrics["mean_similarity_gap"] = float(np.mean(positive_scores) - np.mean(negative_scores))
                metrics["positive_mean_sim"] = float(np.mean(positive_scores))
                metrics["negative_mean_sim"] = float(np.mean(negative_scores))

            duration = time.time() - start_time

            details = {
                "num_positive_pairs": len(all_positive_pairs),
                "num_negative_pairs": len(all_negative_pairs),
                "num_unique_decisions": len(all_decision_ids),
                "num_embedded_decisions": len(embeddings),
                "positive_scores_stats": {
                    "mean": float(np.mean(positive_scores)) if positive_scores else 0,
                    "std": float(np.std(positive_scores)) if positive_scores else 0,
                },
                "negative_scores_stats": {
                    "mean": float(np.mean(negative_scores)) if negative_scores else 0,
                    "std": float(np.std(negative_scores)) if negative_scores else 0,
                },
            }

            # Determine pass/fail based on AUC > baseline (0.5 random)
            baseline_auc = 0.5
            auc = metrics.get("auc_roc", 0.5)
            status = BenchmarkStatus.PASSED if auc > baseline_auc + 0.05 else BenchmarkStatus.FAILED

            return self._create_result(
                status=status,
                metrics=metrics,
                details=details,
                duration=duration,
                evidence_tier=EvidenceTier.EXPLORATORY,
                baseline_comparison={"auc_roc_baseline": baseline_auc},
            )

        except Exception as e:
            logger.error(f"Neighbor relevance test failed: {e}")
            return self._create_result(
                status=BenchmarkStatus.ERROR,
                metrics={},
                details={"exception": str(e)},
                duration=time.time() - start_time,
                error_message=str(e),
            )

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def _compute_ranking_metrics(
        self,
        embeddings: Dict[str, np.ndarray],
        positive_pairs: List[Tuple[str, str]],
        negative_pairs: List[Tuple[str, str]],
    ) -> Dict[str, float]:
        """Compute precision@k, recall@k, MRR for each query decision."""
        # Build adjacency from positive pairs
        positive_neighbors = {}
        for d1, d2 in positive_pairs:
            positive_neighbors.setdefault(d1, set()).add(d2)
            positive_neighbors.setdefault(d2, set()).add(d1)

        # For each query decision that has positive neighbors
        query_decisions = list(positive_neighbors.keys())
        if not query_decisions:
            return {f"p@{k}": 0.0 for k in self.config.k_values}

        all_decision_ids = list(embeddings.keys())
        decision_to_idx = {d: i for i, d in enumerate(all_decision_ids)}
        embedding_matrix = np.stack([embeddings[d] for d in all_decision_ids])

        # Normalize embeddings for cosine similarity
        norms = np.linalg.norm(embedding_matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1
        normalized = embedding_matrix / norms

        metrics = {}
        precisions = {k: [] for k in self.config.k_values}
        recalls = {k: [] for k in self.config.k_values}
        reciprocal_ranks = []

        for query_id in query_decisions:
            if query_id not in embeddings:
                continue

            query_emb = normalized[decision_to_idx[query_id]]
            # Compute similarities to all other decisions
            similarities = normalized @ query_emb
            # Exclude self
            similarities[decision_to_idx[query_id]] = -1

            # Get top-k indices
            ranked_indices = np.argsort(similarities)[::-1]
            ranked_ids = [all_decision_ids[i] for i in ranked_indices]

            true_neighbors = positive_neighbors[query_id]
            if not true_neighbors:
                continue

            # Compute metrics at each k
            for k in self.config.k_values:
                top_k = set(ranked_ids[:k])
                tp = len(top_k & true_neighbors)
                precisions[k].append(tp / k if k > 0 else 0)
                recalls[k].append(tp / len(true_neighbors) if true_neighbors else 0)

            # MRR
            for rank, doc_id in enumerate(ranked_ids, 1):
                if doc_id in true_neighbors:
                    reciprocal_ranks.append(1.0 / rank)
                    break

        # Average metrics
        for k in self.config.k_values:
            metrics[f"precision@{k}"] = float(np.mean(precisions[k])) if precisions[k] else 0.0
            metrics[f"recall@{k}"] = float(np.mean(recalls[k])) if recalls[k] else 0.0

        metrics["mrr"] = float(np.mean(reciprocal_ranks)) if reciprocal_ranks else 0.0

        return metrics

    def get_baseline_metrics(self) -> Dict[str, float]:
        """Expected baseline metrics for random embeddings."""
        baselines = {"auc_roc": 0.5, "mrr": 0.0}
        for k in self.config.k_values:
            baselines[f"precision@{k}"] = 0.01  # Very low for random
            baselines[f"recall@{k}"] = 0.01
        return baselines