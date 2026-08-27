"""
Citation Graph Neighborhood Benchmark

Tests whether decisions connected in the citation graph (direct citation links)
are closer in embedding space than unconnected decisions. This is a stronger
signal than shared-citation heritage because it uses the full citation graph
from the corpus lane (2,105 edges across 250 decisions).

Hypothesis: A good legal representation should place directly-citing decisions
close together, reflecting doctrinal lineage.

Weak supervision source: citation_graph.json from corpus lane.

Frozen before observation:
- Sample: All 250 decisions in the citation graph
- Metric: AUC-ROC for cited-vs-uncited pair similarity
- Success rule: AUC > 0.7 (well above random 0.5)
"""

import json
import numpy as np
from typing import Callable, Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict
import logging
import time
import random

from ..benchmarks.core import BaseBenchmark, BenchmarkResult, BenchmarkStatus, EvidenceTier

logger = logging.getLogger(__name__)


@dataclass
class CitationGraphConfig:
    """Configuration for citation graph neighborhood benchmark."""
    max_pairs: int = 500
    random_seed: int = 42
    citation_graph_path: str = "corpus/normalization/canonical/citation_graph.json"
    # Also accept accepted corpus path
    citation_graph_path_accepted: str = "/tmp/lex_accepted/corpus/corpus/normalization/canonical/citation_graph.json"


class CitationGraphNeighborhoodBenchmark(BaseBenchmark):
    """
    Tests whether direct citation links predict embedding proximity.

    Method:
    1. Load the full citation graph (outgoing + incoming edges)
    2. Create positive pairs: decisions with direct citation links
    3. Create negative pairs: decisions with no citation link
    4. Compute embedding similarity for each pair
    5. Measure AUC-ROC: can we distinguish cited pairs from random?
    """

    def __init__(self, config: Optional[CitationGraphConfig] = None):
        super().__init__("citation_graph_neighborhood", config)
        self.config = config or CitationGraphConfig()

    def run(
        self,
        representation_fn: Callable,
        corpus: Any,
        **kwargs,
    ) -> BenchmarkResult:
        start_time = time.time()

        try:
            # Load citation graph
            citation_graph = self._load_citation_graph()
            if citation_graph is None:
                return self._create_result(
                    status=BenchmarkStatus.ERROR,
                    metrics={},
                    details={"error": "Could not load citation graph"},
                    duration=time.time() - start_time,
                    error_message="Citation graph not found",
                )

            # Build edge sets
            outgoing = citation_graph.get("outgoing", {})
            incoming = citation_graph.get("incoming", {})
            stats = citation_graph.get("stats", {})

            # Build bidirectional adjacency
            adjacency = defaultdict(set)
            for source, targets in outgoing.items():
                for target in targets:
                    adjacency[source].add(target)
                    adjacency[target].add(source)
            for target, sources in incoming.items():
                for source in sources:
                    adjacency[source].add(target)
                    adjacency[target].add(source)

            # Get all decision IDs that appear in the graph
            all_graph_ids = set(adjacency.keys())
            logger.info(f"Citation graph: {len(all_graph_ids)} decisions, {stats.get('total_edges', 0)} edges")

            # Create positive pairs (direct citation links)
            positive_pairs = []
            seen_pairs = set()
            for source, targets in adjacency.items():
                for target in targets:
                    pair = tuple(sorted([source, target]))
                    if pair not in seen_pairs:
                        seen_pairs.add(pair)
                        positive_pairs.append(pair)

            # Create negative pairs (no citation link)
            negative_pairs = []
            random.seed(self.config.random_seed)
            max_attempts = len(positive_pairs) * 20
            attempts = 0
            while len(negative_pairs) < len(positive_pairs) and attempts < max_attempts:
                d1, d2 = random.sample(list(all_graph_ids), 2)
                pair = tuple(sorted([d1, d2]))
                if pair not in seen_pairs:
                    negative_pairs.append(pair)
                    seen_pairs.add(pair)
                attempts += 1

            # Limit pairs
            if len(positive_pairs) > self.config.max_pairs:
                random.shuffle(positive_pairs)
                positive_pairs = positive_pairs[:self.config.max_pairs]
            if len(negative_pairs) > self.config.max_pairs:
                negative_pairs = negative_pairs[:self.config.max_pairs]

            if len(positive_pairs) < 10:
                return self._create_result(
                    status=BenchmarkStatus.FAILED,
                    metrics={},
                    details={"error": f"Insufficient positive pairs: {len(positive_pairs)}"},
                    duration=time.time() - start_time,
                    error_message="Insufficient citation pairs",
                )

            # Get embeddings for all decisions in pairs
            all_decision_ids = set()
            for d1, d2 in positive_pairs + negative_pairs:
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

            for d1, d2 in positive_pairs:
                if d1 in embeddings and d2 in embeddings:
                    sim = self._cosine_similarity(embeddings[d1], embeddings[d2])
                    positive_scores.append(sim)

            for d1, d2 in negative_pairs:
                if d1 in embeddings and d2 in embeddings:
                    sim = self._cosine_similarity(embeddings[d1], embeddings[d2])
                    negative_scores.append(sim)

            # Compute metrics
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
            metrics["graph_total_decisions"] = stats.get("total_decisions", 0)
            metrics["graph_total_edges"] = stats.get("total_edges", 0)

            # Pass if AUC > 0.7
            auc = metrics.get("auc_roc", 0.5)
            status = BenchmarkStatus.PASSED if auc > 0.7 else BenchmarkStatus.FAILED

            duration = time.time() - start_time

            return self._create_result(
                status=status,
                metrics=metrics,
                details={
                    "positive_pairs_sample": [list(p) for p in positive_pairs[:10]],
                    "negative_pairs_sample": [list(p) for p in negative_pairs[:10]],
                },
                duration=duration,
                evidence_tier=EvidenceTier.REPRODUCED,
                baseline_comparison={
                    "auc_roc_random": 0.5,
                    "note": "Random embeddings: AUC = 0.5. TF-IDF: expected ~0.6-0.7. Legal-BERT: expected >0.75.",
                },
            )

        except Exception as e:
            logger.error(f"Citation graph neighborhood benchmark failed: {e}")
            return self._create_result(
                status=BenchmarkStatus.ERROR,
                metrics={},
                details={"exception": str(e)},
                duration=time.time() - start_time,
                error_message=str(e),
            )

    def _load_citation_graph(self) -> Optional[Dict]:
        """Load citation graph from file."""
        import os
        for path in [self.config.citation_graph_path, self.config.citation_graph_path_accepted]:
            if os.path.exists(path):
                with open(path) as f:
                    return json.load(f)
        return None

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def get_baseline_metrics(self) -> Dict[str, float]:
        return {"auc_roc": 0.5, "note": "Random embeddings: AUC = 0.5 exactly."}
