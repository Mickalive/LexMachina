"""
Legal-Area Clustering Benchmark

Tests whether embedding-space clustering recovers the 4 legal branches
(zivilrecht, strafrecht, oeffentliches_recht, sozialversicherungsrecht) of
the Swiss Federal Supreme Court.

This benchmark is INDEPENDENT of Jurivoc and uses only the branch metadata
from the corpus lane. It measures the fundamental question: does the geometry
organize decisions by legal domain?

Hypothesis: A good legal representation should produce clusters that
substantially align with legal branches, achieving NMI > 0.3 and purity > 0.7.

Frozen before observation:
- Sample: All canonical decisions with branch metadata (4 branches, ~100 each)
- Metric: NMI and purity of agglomerative clustering vs. branch labels
- Success rule: NMI > 0.3 AND purity > 0.7
"""

import json
import numpy as np
from typing import Callable, Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from collections import Counter, defaultdict
import logging
import time

from ..benchmarks.core import BaseBenchmark, BenchmarkResult, BenchmarkStatus, EvidenceTier

logger = logging.getLogger(__name__)


@dataclass
class LegalAreaClusteringConfig:
    """Configuration for legal-area clustering benchmark."""
    n_clusters_list: List[int] = None  # Number of clusters to test
    min_decisions_per_branch: int = 10
    sample_size: int = 500
    random_seed: int = 42

    def __post_init__(self):
        if self.n_clusters_list is None:
            self.n_clusters_list = [4, 6, 8, 12]


class LegalAreaClusteringBenchmark(BaseBenchmark):
    """
    Tests whether clustering in embedding space recovers legal branch structure.

    Method:
    1. Load decisions with branch metadata
    2. Compute embeddings
    3. Run agglomerative clustering at multiple resolutions
    4. Measure NMI and purity against branch labels
    """

    def __init__(self, config: Optional[LegalAreaClusteringConfig] = None):
        super().__init__("legal_area_clustering", config)
        self.config = config or LegalAreaClusteringConfig()

    def run(
        self,
        representation_fn: Callable,
        corpus: Any,
        **kwargs,
    ) -> BenchmarkResult:
        import time as time_mod
        start_time = time_mod.time()

        try:
            # Load decisions with branch metadata
            decisions = self._load_decisions(corpus)
            branch_decisions = {}
            for d in decisions:
                branch = d.get("branch")
                did = d.get("decision_id", "")
                if branch and did and branch != "null":
                    branch_decisions.setdefault(branch, []).append(did)

            # Filter branches with enough decisions
            valid_branches = {
                b: ids for b, ids in branch_decisions.items()
                if len(ids) >= self.config.min_decisions_per_branch
            }

            if len(valid_branches) < 2:
                return self._create_result(
                    status=BenchmarkStatus.ERROR,
                    metrics={},
                    details={
                        "error": f"Insufficient branches: {len(valid_branches)}",
                        "branch_counts": {b: len(ids) for b, ids in branch_decisions.items()},
                    },
                    duration=time_mod.time() - start_time,
                    error_message="Insufficient branch labels",
                )

            # Sample decisions (balanced across branches)
            import random
            random.seed(self.config.random_seed)
            
            sampled_ids = []
            sampled_labels = {}
            per_branch = self.config.sample_size // len(valid_branches)
            
            for branch, ids in valid_branches.items():
                n = min(per_branch, len(ids))
                selected = random.sample(ids, n)
                sampled_ids.extend(selected)
                for did in selected:
                    sampled_labels[did] = branch

            if len(sampled_ids) < 20:
                return self._create_result(
                    status=BenchmarkStatus.FAILED,
                    metrics={},
                    details={"error": f"Insufficient sampled decisions: {len(sampled_ids)}"},
                    duration=time_mod.time() - start_time,
                    error_message="Insufficient decisions",
                )

            # Get embeddings
            embeddings = {}
            for did in sampled_ids:
                try:
                    emb = representation_fn(did)
                    if emb is not None:
                        embeddings[did] = np.array(emb, dtype=np.float32)
                except Exception as e:
                    logger.warning(f"Failed to get embedding for {did}: {e}")

            valid_ids = [did for did in sampled_ids if did in embeddings]
            if len(valid_ids) < 20:
                return self._create_result(
                    status=BenchmarkStatus.FAILED,
                    metrics={},
                    details={"error": f"Insufficient embeddings: {len(valid_ids)}"},
                    duration=time_mod.time() - start_time,
                    error_message="Insufficient embeddings",
                )

            embedding_matrix = np.stack([embeddings[did] for did in valid_ids])
            true_labels = [sampled_labels[did] for did in valid_ids]

            # Normalize
            norms = np.linalg.norm(embedding_matrix, axis=1, keepdims=True)
            norms[norms == 0] = 1
            normalized = embedding_matrix / norms

            # Run clustering at multiple resolutions
            from sklearn.cluster import AgglomerativeClustering
            from sklearn.metrics import normalized_mutual_info_score

            all_level_metrics = []
            best_nmi = 0.0
            best_purity = 0.0

            for n_clusters in self.config.n_clusters_list:
                if n_clusters > len(valid_ids) or n_clusters < 2:
                    continue

                clustering = AgglomerativeClustering(
                    n_clusters=n_clusters,
                    metric="cosine",
                    linkage="average",
                )
                pred_labels = clustering.fit_predict(normalized)

                # Compute NMI
                nmi = float(normalized_mutual_info_score(true_labels, pred_labels))

                # Compute purity
                purity = self._compute_purity(true_labels, pred_labels)

                # Compute language dominance (how much clustering separates by language)
                all_level_metrics.append({
                    "n_clusters": n_clusters,
                    "nmi": nmi,
                    "purity": purity,
                    "num_valid_decisions": len(valid_ids),
                })

                best_nmi = max(best_nmi, nmi)
                best_purity = max(best_purity, purity)

            # Also test cluster quality at n_clusters = num_branches (ideal case)
            n_true_branches = len(valid_branches)
            if n_true_branches >= 2 and n_true_branches <= len(valid_ids):
                clustering = AgglomerativeClustering(
                    n_clusters=n_true_branches,
                    metric="cosine",
                    linkage="average",
                )
                pred_labels = clustering.fit_predict(normalized)
                nmi_at_true = float(normalized_mutual_info_score(true_labels, pred_labels))
                purity_at_true = self._compute_purity(true_labels, pred_labels)
            else:
                nmi_at_true = best_nmi
                purity_at_true = best_purity

            # Compute branch distribution in each cluster
            cluster_branch_dist = self._cluster_branch_distribution(true_labels, pred_labels) if n_true_branches >= 2 else {}

            metrics = {
                "best_nmi": best_nmi,
                "best_purity": best_purity,
                "nmi_at_true_k": nmi_at_true,
                "purity_at_true_k": purity_at_true,
                "num_decisions": len(valid_ids),
                "num_branches": n_true_branches,
                "branch_distribution": {b: len(ids) for b, ids in valid_branches.items()},
            }

            # Add per-level metrics
            for i, m in enumerate(all_level_metrics):
                for k, v in m.items():
                    metrics[f"level_{i}_{k}"] = v

            # Pass if NMI > 0.3 AND purity > 0.7
            status = BenchmarkStatus.PASSED if (
                best_nmi > 0.3 and best_purity > 0.7
            ) else BenchmarkStatus.FAILED

            duration = time_mod.time() - start_time

            return self._create_result(
                status=status,
                metrics=metrics,
                details={
                    "level_metrics": all_level_metrics,
                    "cluster_branch_distribution": cluster_branch_dist,
                },
                duration=duration,
                evidence_tier=EvidenceTier.REPRODUCED,
                baseline_comparison={
                    "random_nmi": 0.0,
                    "random_purity": 1.0 / n_true_branches if n_true_branches > 0 else 0.25,
                    "note": "Random clustering: NMI ~ 0, purity ~ 1/k. TF-IDF expected: NMI ~ 0.01-0.05 (language-dominated). Legal embeddings: NMI > 0.3.",
                },
            )

        except Exception as e:
            logger.error(f"Legal-area clustering benchmark failed: {e}")
            return self._create_result(
                status=BenchmarkStatus.ERROR,
                metrics={},
                details={"exception": str(e)},
                duration=time_mod.time() - start_time,
                error_message=str(e),
            )

    def _compute_purity(self, true_labels: List[str], pred_labels: np.ndarray) -> float:
        """Compute clustering purity."""
        purity_scores = []
        unique_clusters = set(pred_labels)
        
        for cluster_id in unique_clusters:
            mask = pred_labels == cluster_id
            cluster_true = [true_labels[i] for i in range(len(true_labels)) if mask[i]]
            if cluster_true:
                most_common = Counter(cluster_true).most_common(1)[0][1]
                purity_scores.append(most_common / len(cluster_true))
        
        return float(np.mean(purity_scores)) if purity_scores else 0.0

    def _cluster_branch_distribution(
        self, true_labels: List[str], pred_labels: np.ndarray
    ) -> Dict[int, Dict[str, int]]:
        """Get branch distribution per cluster."""
        dist = defaultdict(lambda: Counter())
        for i, label in enumerate(pred_labels):
            dist[int(label)][true_labels[i]] += 1
        return {k: dict(v) for k, v in dist.items()}

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

    def get_baseline_metrics(self) -> Dict[str, float]:
        return {
            "random_nmi": 0.0,
            "random_purity": 0.25,
            "note": "Random clustering with 4 branches: NMI ~ 0, purity ~ 0.25.",
        }
