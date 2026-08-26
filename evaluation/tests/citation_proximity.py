"""
Citation Proximity Benchmark

Tests whether decisions sharing common cited precedents are closer in
embedding space than decisions with no shared citations. This is a stronger
signal than simple citation lineage because it measures topical proximity
through shared intellectual heritage, not just direct citation chains.

Hypothesis: A good legal representation should place decisions that cite
the same precedents close together, even if they don't cite each other.

Weak supervision source: Citation graph from corpus lane + cited_decisions
fields in canonical decisions.

Frozen before observation:
- Sample: All 212 canonical decisions with cited_decisions metadata
- Metric: AUC-ROC for shared-citation vs. non-shared-citation pair similarity
- Success rule: AUC > 0.7 (well above random 0.5)
"""

import json
import numpy as np
from typing import Callable, Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict
import logging
import time

from ..benchmarks.core import BaseBenchmark, BenchmarkResult, BenchmarkStatus, EvidenceTier

logger = logging.getLogger(__name__)


@dataclass
class CitationProximityConfig:
    """Configuration for citation proximity benchmark."""
    min_shared_citations: int = 1  # Minimum shared citations to count as positive pair
    max_pairs_per_query: int = 200
    sample_size: int = 200  # Max decisions to include
    random_seed: int = 42


class CitationProximityBenchmark(BaseBenchmark):
    """
    Tests whether shared citation heritage predicts embedding proximity.

    Method:
    1. For each pair of decisions, count shared cited precedents
    2. Create positive pairs (>= min_shared_citations shared) and negative pairs (0 shared)
    3. Compute embedding similarity for each pair
    4. Measure AUC-ROC: can we distinguish shared-citation pairs from random?
    """

    def __init__(self, config: Optional[CitationProximityConfig] = None):
        super().__init__("citation_proximity", config)
        self.config = config or CitationProximityConfig()

    def run(
        self,
        representation_fn: Callable,
        corpus: Any,
        **kwargs,
    ) -> BenchmarkResult:
        import time as time_mod
        start_time = time_mod.time()

        try:
            # Load decisions from corpus
            decisions = self._load_decisions(corpus)
            if len(decisions) < 20:
                return self._create_result(
                    status=BenchmarkStatus.ERROR,
                    metrics={},
                    details={"error": f"Insufficient decisions: {len(decisions)}"},
                    duration=time_mod.time() - start_time,
                    error_message="Insufficient decisions",
                )

            # Build citation index: decision_id -> set of cited references
            citation_index = {}
            for d in decisions:
                did = d.get("decision_id", "")
                cites = d.get("cited_decisions", [])
                if did and cites:
                    citation_index[did] = set(cites)

            # Find all pairs of decisions that share at least min_shared_citations
            decision_ids = list(citation_index.keys())
            positive_pairs = []
            negative_pairs = []

            # Build shared-citation matrix (sparse approach for efficiency)
            # Group decisions by each cited reference
            ref_to_decisions = defaultdict(set)
            for did, refs in citation_index.items():
                for ref in refs:
                    ref_to_decisions[ref].add(did)

            # Positive pairs: decisions sharing >= min_shared_citations references
            pair_shared_count = defaultdict(int)
            for ref, dids in ref_to_decisions.items():
                dids_list = list(dids)
                for i in range(len(dids_list)):
                    for j in range(i + 1, len(dids_list)):
                        pair_key = tuple(sorted([dids_list[i], dids_list[j]]))
                        pair_shared_count[pair_key] += 1

            for pair, count in pair_shared_count.items():
                if count >= self.config.min_shared_citations:
                    positive_pairs.append((pair[0], pair[1], count))

            # Negative pairs: decisions with zero shared citations
            import random
            random.seed(self.config.random_seed)
            
            # Build set of all positive pairs for fast lookup
            positive_set = set((p[0], p[1]) for p in positive_pairs)
            
            attempts = 0
            max_attempts = len(positive_pairs) * 20
            while len(negative_pairs) < len(positive_pairs) and attempts < max_attempts:
                d1, d2 = random.sample(decision_ids, 2)
                pair_key = tuple(sorted([d1, d2]))
                if pair_key not in positive_set:
                    negative_pairs.append((d1, d2))
                attempts += 1

            if len(positive_pairs) < 10:
                return self._create_result(
                    status=BenchmarkStatus.FAILED,
                    metrics={},
                    details={
                        "error": f"Insufficient positive pairs: {len(positive_pairs)}",
                        "total_decisions": len(decision_ids),
                        "decisions_with_citations": len(citation_index),
                    },
                    duration=time_mod.time() - start_time,
                    error_message="Insufficient citation pairs",
                )

            # Limit pairs
            if len(positive_pairs) > self.config.max_pairs_per_query:
                random.shuffle(positive_pairs)
                positive_pairs = positive_pairs[:self.config.max_pairs_per_query]
            if len(negative_pairs) > self.config.max_pairs_per_query:
                negative_pairs = negative_pairs[:self.config.max_pairs_per_query]

            # Get embeddings for all decisions in pairs
            all_decision_ids = set()
            for d1, d2, _ in positive_pairs:
                all_decision_ids.add(d1)
                all_decision_ids.add(d2)
            for d1, d2 in negative_pairs:
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

            # Compute similarities
            positive_scores = []
            negative_scores = []

            for d1, d2, shared_count in positive_pairs:
                if d1 in embeddings and d2 in embeddings:
                    sim = self._cosine_similarity(embeddings[d1], embeddings[d2])
                    positive_scores.append(sim)

            for d1, d2 in negative_pairs:
                if d1 in embeddings and d2 in embeddings:
                    sim = self._cosine_similarity(embeddings[d1], embeddings[d2])
                    negative_scores.append(sim)

            # Compute AUC-ROC
            metrics = {}
            if positive_scores and negative_scores:
                from sklearn.metrics import roc_auc_score
                y_true = [1] * len(positive_scores) + [0] * len(negative_scores)
                y_scores = positive_scores + negative_scores
                metrics["auc_roc"] = float(roc_auc_score(y_true, y_scores))
                metrics["positive_mean_sim"] = float(np.mean(positive_scores))
                metrics["negative_mean_sim"] = float(np.mean(negative_scores))
                metrics["mean_similarity_gap"] = float(np.mean(positive_scores) - np.mean(negative_scores))
            else:
                metrics["auc_roc"] = 0.5

            metrics["num_positive_pairs"] = len(positive_pairs)
            metrics["num_negative_pairs"] = len(negative_pairs)
            metrics["num_unique_decisions"] = len(all_decision_ids)
            metrics["num_embedded_decisions"] = len(embeddings)

            # Distribution of shared citation counts
            shared_counts = [p[2] for p in positive_pairs]
            metrics["mean_shared_citations"] = float(np.mean(shared_counts))
            metrics["max_shared_citations"] = int(np.max(shared_counts))

            # Pass if AUC > 0.7
            auc = metrics.get("auc_roc", 0.5)
            status = BenchmarkStatus.PASSED if auc > 0.7 else BenchmarkStatus.FAILED

            duration = time_mod.time() - start_time

            return self._create_result(
                status=status,
                metrics=metrics,
                details={
                    "positive_pairs_sample": [(d1, d2, c) for d1, d2, c in positive_pairs[:10]],
                    "negative_pairs_sample": negative_pairs[:10],
                },
                duration=duration,
                evidence_tier=EvidenceTier.REPRODUCED,
                baseline_comparison={
                    "auc_roc_random": 0.5,
                    "note": "Random embeddings: AUC = 0.5. TF-IDF on full text: expected ~0.7-0.85 (shared vocabulary from same legal domain). Legal-BERT: expected >0.85.",
                },
            )

        except Exception as e:
            logger.error(f"Citation proximity benchmark failed: {e}")
            return self._create_result(
                status=BenchmarkStatus.ERROR,
                metrics={},
                details={"exception": str(e)},
                duration=time_mod.time() - start_time,
                error_message=str(e),
            )

    def _load_decisions(self, corpus: Any) -> List[Dict[str, Any]]:
        """Load decisions from corpus."""
        if hasattr(corpus, "get_decisions"):
            return corpus.get_decisions()
        elif hasattr(corpus, "decisions"):
            decisions = list(corpus.decisions.values())
            return [d if isinstance(d, dict) else vars(d) for d in decisions]
        elif isinstance(corpus, list):
            return corpus
        return []

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def get_baseline_metrics(self) -> Dict[str, float]:
        return {
            "auc_roc": 0.5,
            "note": "Random embeddings: AUC = 0.5 exactly.",
        }
