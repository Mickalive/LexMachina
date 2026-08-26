"""
Corpus Scale Stability Test

Tests whether the legal distance representation is stable as the corpus grows.
A good representation should not dramatically change the relative positions
of existing decisions when new decisions are added.
"""

import numpy as np
from typing import Callable, Dict, List, Any, Optional
from dataclasses import dataclass
import logging
import random

from ..benchmarks.core import BaseBenchmark, BenchmarkResult, BenchmarkStatus, EvidenceTier

logger = logging.getLogger(__name__)


@dataclass
class StabilityConfig:
    """Configuration for corpus stability test."""
    initial_corpus_size: int = 100
    growth_steps: List[int] = None  # Sizes to grow to
    num_anchor_decisions: int = 20  # Decisions to track across growth
    num_trials: int = 3  # Number of random seeds to average over
    random_seed: int = 42

    def __post_init__(self):
        if self.growth_steps is None:
            self.growth_steps = [200, 500, 1000, 2000]


class CorpusStabilityTest(BaseBenchmark):
    """
    Tests corpus-scale stability of legal distance representations.
    
    Method:
    1. Start with a small corpus subset
    2. Compute embeddings for anchor decisions
    3. Grow corpus incrementally
    4. Recompute embeddings (or use incremental update if supported)
    5. Measure how much anchor decision positions change
    6. Good representations should be stable (low position drift)
    """

    def __init__(self, config: Optional[StabilityConfig] = None):
        super().__init__("corpus_stability", config.__dict__ if config else {})
        self.config = config or StabilityConfig()

    def run(
        self,
        representation_fn: Callable,
        corpus: Any,
        **kwargs,
    ) -> BenchmarkResult:
        """
        Run corpus stability test.

        Args:
            representation_fn: Function that takes a decision_id and returns embedding vector.
                              Should optionally accept a `corpus_subset` parameter for 
                              incremental computation.
            corpus: Corpus object with decisions
            **kwargs: Additional arguments

        Returns:
            BenchmarkResult with stability metrics
        """
        import time
        start_time = time.time()

        try:
            # Get all available decisions
            all_decisions = self._get_all_decisions(corpus)
            if len(all_decisions) < max(self.config.growth_steps):
                # Adjust growth steps to available data
                max_size = len(all_decisions)
                self.config.growth_steps = [s for s in self.config.growth_steps if s <= max_size]
                if not self.config.growth_steps:
                    self.config.growth_steps = [max_size]

            if len(all_decisions) < self.config.initial_corpus_size + self.config.num_anchor_decisions:
                return self._create_result(
                    status=BenchmarkStatus.FAILED,
                    metrics={},
                    details={"error": f"Insufficient decisions: {len(all_decisions)}"},
                    duration=time.time() - start_time,
                    error_message="Insufficient corpus size",
                )

            all_trial_metrics = []

            for trial in range(self.config.num_trials):
                random.seed(self.config.random_seed + trial)
                
                # Select anchor decisions (fixed across trials)
                anchor_decisions = random.sample(all_decisions, self.config.num_anchor_decisions)
                anchor_ids = [d["decision_id"] for d in anchor_decisions]

                # Remaining decisions for corpus growth
                remaining = [d for d in all_decisions if d["decision_id"] not in anchor_ids]

                trial_metrics = self._run_single_trial(
                    representation_fn, anchor_ids, remaining, trial
                )
                all_trial_metrics.append(trial_metrics)

            # Aggregate across trials
            aggregated = self._aggregate_trial_metrics(all_trial_metrics)

            # Determine pass/fail
            mean_drift = aggregated.get("mean_position_drift", 1.0)
            status = BenchmarkStatus.PASSED if mean_drift < 0.3 else BenchmarkStatus.FAILED

            duration = time.time() - start_time

            return self._create_result(
                status=status,
                metrics=aggregated,
                details={
                    "trial_metrics": all_trial_metrics,
                    "config": self.config.__dict__,
                },
                duration=duration,
                evidence_tier=EvidenceTier.EXPLORATORY,
                baseline_comparison={"mean_position_drift_baseline": 0.5},
            )

        except Exception as e:
            logger.error(f"Corpus stability test failed: {e}")
            return self._create_result(
                status=BenchmarkStatus.ERROR,
                metrics={},
                details={"exception": str(e)},
                duration=time.time() - start_time,
                error_message=str(e),
            )

    def _get_all_decisions(self, corpus: Any) -> List[Dict[str, Any]]:
        """Get all decisions from corpus."""
        if hasattr(corpus, "get_decisions"):
            return corpus.get_decisions()
        elif hasattr(corpus, "decisions"):
            decisions = list(corpus.decisions.values())
            return [d if isinstance(d, dict) else d.__dict__ for d in decisions]
        elif isinstance(corpus, list):
            return corpus
        return []

    def _run_single_trial(
        self,
        representation_fn: Callable,
        anchor_ids: List[str],
        remaining_decisions: List[Dict[str, Any]],
        trial: int,
    ) -> Dict[str, Any]:
        """Run a single stability trial."""
        random.seed(self.config.random_seed + trial)
        random.shuffle(remaining_decisions)

        # Build corpus incrementally
        corpus_sizes = [self.config.initial_corpus_size] + self.config.growth_steps
        corpus_sizes = [s for s in corpus_sizes if s <= len(remaining_decisions) + self.config.initial_corpus_size]

        anchor_embeddings_history = {aid: [] for aid in anchor_ids}

        for size in corpus_sizes:
            # Build corpus subset
            current_corpus = remaining_decisions[:size - self.config.initial_corpus_size]
            current_corpus_ids = [d["decision_id"] for d in current_corpus]
            
            # Get embeddings for anchor decisions with current corpus
            # Note: This assumes representation_fn can work with a corpus subset
            # In practice, this might require retraining or incremental update
            for anchor_id in anchor_ids:
                try:
                    # Try to pass corpus context if supported
                    emb = representation_fn(anchor_id, corpus_subset=current_corpus_ids)
                    if emb is None:
                        emb = representation_fn(anchor_id)  # Fallback
                    if emb is not None:
                        anchor_embeddings_history[anchor_id].append(np.array(emb, dtype=np.float32))
                except TypeError:
                    # representation_fn doesn't accept corpus_subset
                    emb = representation_fn(anchor_id)
                    if emb is not None:
                        anchor_embeddings_history[anchor_id].append(np.array(emb, dtype=np.float32))
                except Exception as e:
                    logger.warning(f"Failed to get embedding for {anchor_id} at size {size}: {e}")

        # Compute position drift for each anchor
        drifts = []
        for anchor_id, embeddings in anchor_embeddings_history.items():
            if len(embeddings) >= 2:
                # Compute pairwise cosine distances between consecutive embeddings
                for i in range(1, len(embeddings)):
                    sim = self._cosine_similarity(embeddings[i-1], embeddings[i])
                    drift = 1.0 - sim  # Distance = 1 - similarity
                    drifts.append(drift)

        return {
            "trial": trial,
            "corpus_sizes": corpus_sizes,
            "mean_drift": float(np.mean(drifts)) if drifts else 1.0,
            "max_drift": float(np.max(drifts)) if drifts else 1.0,
            "std_drift": float(np.std(drifts)) if drifts else 0.0,
            "num_anchor_tracked": len([e for e in anchor_embeddings_history.values() if len(e) >= 2]),
        }

    def _aggregate_trial_metrics(self, trial_metrics: List[Dict[str, Any]]) -> Dict[str, float]:
        """Aggregate metrics across trials."""
        mean_drifts = [t["mean_drift"] for t in trial_metrics]
        max_drifts = [t["max_drift"] for t in trial_metrics]

        return {
            "mean_position_drift": float(np.mean(mean_drifts)),
            "std_position_drift": float(np.std(mean_drifts)),
            "max_position_drift": float(np.max(max_drifts)),
            "mean_max_drift": float(np.mean(max_drifts)),
            "num_trials": len(trial_metrics),
        }

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def get_baseline_metrics(self) -> Dict[str, float]:
        """Expected baseline metrics for unstable representations."""
        return {
            "mean_position_drift": 0.5,
            "max_position_drift": 0.8,
        }