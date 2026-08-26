"""
Multilingual Invariance Test

Tests whether the legal distance representation is invariant across languages
(German, French, Italian) for the same legal content.
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
class MultilingualConfig:
    """Configuration for multilingual invariance test."""
    min_pairs: int = 20
    max_pairs: int = 200
    similarity_threshold: float = 0.7  # Expected minimum similarity for same case
    languages: List[str] = None

    def __post_init__(self):
        if self.languages is None:
            self.languages = ["de", "fr", "it"]


class MultilingualInvarianceTest(BaseBenchmark):
    """
    Tests cross-language invariance of legal distance representations.
    
    For Swiss Federal Supreme Court decisions, the same case may be published
    in multiple languages (German, French, Italian). A good legal representation
    should place these parallel versions close together in the embedding space,
    regardless of language.
    """

    def __init__(self, config: Optional[MultilingualConfig] = None):
        super().__init__("multilingual_invariance", config)
        self.config = config or MultilingualConfig()
        self.real_supervision = WeakSupervisionBenchmark()
        self.synthetic_supervision: Optional[SyntheticWeakSupervision] = None

    def run(
        self,
        representation_fn: Callable,
        corpus: Any,
        **kwargs,
    ) -> BenchmarkResult:
        """
        Run multilingual invariance test.

        Args:
            representation_fn: Function that takes a decision_id and returns embedding vector
            corpus: Corpus object with decision metadata
            **kwargs: Additional arguments (can include 'ground_truth' for synthetic data)

        Returns:
            BenchmarkResult with cross-language similarity metrics
        """
        import time
        start_time = time.time()

        try:
            # Try to use synthetic ground truth if available
            ground_truth = kwargs.get("ground_truth")
            if ground_truth:
                self.synthetic_supervision = SyntheticWeakSupervision(
                    ground_truth,
                    SyntheticSupervisionConfig(random_seed=42),
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
                        error_message="Failed to load TF metadata",
                    )

            # Get cross-language pairs
            if use_synthetic:
                multilingual_bench = self.synthetic_supervision.create_multilingual_benchmark()
            else:
                multilingual_bench = self.real_supervision.create_multilingual_benchmark()
            
            cross_lang_pairs = multilingual_bench["cross_language_pairs"]

            if len(cross_lang_pairs) < self.config.min_pairs:
                return self._create_result(
                    status=BenchmarkStatus.FAILED,
                    metrics={},
                    details={
                        "error": f"Insufficient cross-language pairs: {len(cross_lang_pairs)} < {self.config.min_pairs}",
                        "num_pairs_found": len(cross_lang_pairs),
                    },
                    duration=time.time() - start_time,
                    error_message="Insufficient multilingual data",
                )

            # Limit pairs
            cross_lang_pairs = cross_lang_pairs[:self.config.max_pairs]

            # Get embeddings for all decisions in pairs
            all_decision_ids = set()
            for d1, d2, _ in cross_lang_pairs:
                all_decision_ids.add(d1)
                all_decision_ids.add(d2)

            embeddings = {}
            for decision_id in all_decision_ids:
                try:
                    emb = representation_fn(decision_id)
                    if emb is not None:
                        embeddings[decision_id] = np.array(emb, dtype=np.float32)
                except Exception as e:
                    logger.warning(f"Failed to get embedding for {decision_id}: {e}")

            # Compute cross-language similarities
            cross_lang_similarities = []
            same_lang_similarities = []  # Control: same-language different cases

            for d1, d2, docket in cross_lang_pairs:
                if d1 in embeddings and d2 in embeddings:
                    sim = self._cosine_similarity(embeddings[d1], embeddings[d2])
                    cross_lang_similarities.append(sim)

            # Also compute same-language different-case similarities as control
            # Group decisions by language
            decisions_by_lang = {}
            if ground_truth:
                decision_metadata = ground_truth.get("decision_metadata", {})
                for decision_id in embeddings:
                    if decision_id in decision_metadata:
                        lang = decision_metadata[decision_id].get("language", "unknown")
                        decisions_by_lang.setdefault(lang, []).append(decision_id)
            else:
                # Fallback: use single group
                decisions_by_lang["unknown"] = list(embeddings.keys())

            import random
            random.seed(42)
            for lang, ids in decisions_by_lang.items():
                if len(ids) >= 2:
                    for _ in range(min(50, len(cross_lang_pairs))):
                        d1, d2 = random.sample(ids, 2)
                        sim = self._cosine_similarity(embeddings[d1], embeddings[d2])
                        same_lang_similarities.append(sim)

            if not cross_lang_similarities:
                return self._create_result(
                    status=BenchmarkStatus.FAILED,
                    metrics={},
                    details={"error": "No valid cross-language pairs with embeddings"},
                    duration=time.time() - start_time,
                    error_message="No valid embeddings for cross-language pairs",
                )

            # Compute metrics
            cross_lang_mean = float(np.mean(cross_lang_similarities))
            cross_lang_std = float(np.std(cross_lang_similarities))
            cross_lang_min = float(np.min(cross_lang_similarities))
            cross_lang_max = float(np.max(cross_lang_similarities))

            same_lang_mean = float(np.mean(same_lang_similarities)) if same_lang_similarities else 0.0
            same_lang_std = float(np.std(same_lang_similarities)) if same_lang_similarities else 0.0

            # Invariance score: how close cross-lang similarity is to 1.0
            # and how well it separates from same-lang different-case
            invariance_score = cross_lang_mean
            separation = cross_lang_mean - same_lang_mean if same_lang_similarities else cross_lang_mean

            # Fraction above threshold
            frac_above_threshold = sum(1 for s in cross_lang_similarities if s >= self.config.similarity_threshold) / len(cross_lang_similarities)

            metrics = {
                "cross_lang_mean_similarity": cross_lang_mean,
                "cross_lang_std_similarity": cross_lang_std,
                "cross_lang_min_similarity": cross_lang_min,
                "cross_lang_max_similarity": cross_lang_max,
                "same_lang_mean_similarity": same_lang_mean,
                "same_lang_std_similarity": same_lang_std,
                "invariance_score": invariance_score,
                "separation_from_same_lang": separation,
                "fraction_above_threshold": frac_above_threshold,
                "num_cross_lang_pairs": len(cross_lang_similarities),
                "num_same_lang_pairs": len(same_lang_similarities),
            }

            # Pass if invariance score is high and separation is positive
            status = BenchmarkStatus.PASSED if (
                invariance_score >= self.config.similarity_threshold and
                separation > 0.1
            ) else BenchmarkStatus.FAILED

            duration = time.time() - start_time

            return self._create_result(
                status=status,
                metrics=metrics,
                details={
                    "cross_lang_similarities": cross_lang_similarities[:20],
                    "same_lang_similarities": same_lang_similarities[:20],
                    "num_multilingual_dockets": multilingual_bench["num_multilingual_dockets"],
                },
                duration=duration,
                evidence_tier=EvidenceTier.EXPLORATORY,
                baseline_comparison={
                    "invariance_score_baseline": 0.3,  # Naive multilingual embeddings
                    "separation_baseline": 0.0,
                },
            )

        except Exception as e:
            logger.error(f"Multilingual invariance test failed: {e}")
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

    def get_baseline_metrics(self) -> Dict[str, float]:
        """Expected baseline metrics for naive embeddings."""
        return {
            "invariance_score": 0.3,
            "cross_lang_mean_similarity": 0.3,
            "separation_from_same_lang": 0.0,
            "fraction_above_threshold": 0.0,
        }