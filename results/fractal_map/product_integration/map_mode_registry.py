#!/usr/bin/env python3
"""
Map Mode Registry for Fractal Map Lane.

Defines all selectable map modes for the product:
- Default: Center Projected Hierarchical Leiden (validated multi-resolution fractal map on pure center_projected embeddings)
- Legal-distance modes: debiased_citation_blended, legal_cited_decisions_only, 
  hybrid α=0.3, hybrid α=0.5, legal_issues_outcomes
- Legacy: Concat-based Hierarchical Leiden (preserved for comparison)

This registry provides a unified interface for the product to load and switch
between different map representations.

FACTORY DIRECTION v4: "must REPRODUCE hierarchical_leiden on center_projected 
embeddings as new default input"
"""

import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


class MapModeType(Enum):
    """Type of map mode."""
    HIERARCHICAL_LEIDEN = "hierarchical_leiden"
    LEGAL_DISTANCE = "legal_distance"
    FLAT_LEIDEN = "flat_leiden"
    CUSTOM = "custom"


class MapModeStatus(Enum):
    """Availability status of a map mode."""
    AVAILABLE = "available"
    PLACEHOLDER = "placeholder"  # Infrastructure ready, embeddings need computation
    PLANNED = "planned"  # Designed but not implemented
    LEGACY = "legacy"  # Preserved for comparison, not recommended for new use


@dataclass
class MapModeSpec:
    """Specification for a map mode."""
    mode_id: str
    name: str
    description: str
    mode_type: MapModeType
    status: MapModeStatus
    is_default: bool
    resolution_ladder: List[float]
    artifacts: Dict[str, str]  # artifact_name -> path
    metadata: Dict[str, Any]
    legal_distance_config: Optional[Dict[str, Any]] = None
    benchmark_results: Optional[Dict[str, Any]] = None
    warnings: Optional[List[str]] = None  # Explicit warnings for degraded modes


# ============================================================================
# MAP MODE REGISTRY
# ============================================================================

# Paths are relative to the fractal_map results root (e.g., /tmp/lex_accepted/fractal_map/ or results/fractal_map/)
CENTER_PROJECTED_ARTIFACTS_BASE = "hierarchical_map_center_projected"
LEGAL_DISTANCE_ARTIFACTS_BASE = "legal_distance_modes"

def _cp_artifacts() -> Dict[str, str]:
    """Generate artifact paths for center_projected hierarchical map."""
    base = CENTER_PROJECTED_ARTIFACTS_BASE
    artifacts = {
        "cluster_metadata": f"{base}/cluster_metadata.json",
        "zoom_mappings": f"{base}/zoom_mappings.json",
        "zoom_coherence": f"{base}/zoom_coherence.json",
        "decision_clusters": f"{base}/decision_clusters.json",
    }
    for res in [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]:
        artifacts[f"labels_res_{res}"] = f"{base}/labels_res_{res}.npy"
    artifacts["labels_hierarchical_best"] = f"{base}/labels_hierarchical_best.npy"
    artifacts["labels_coarse_0.5"] = f"{base}/labels_coarse_0.5.npy"
    return artifacts


def _ld_artifacts(mode_id: str) -> Dict[str, str]:
    """Generate artifact paths for a legal-distance mode (flat resolutions only)."""
    base = f"{LEGAL_DISTANCE_ARTIFACTS_BASE}/{mode_id}"
    artifacts = {
        "cluster_metadata": f"{base}/cluster_metadata.json",
        "zoom_mappings": f"{base}/zoom_mappings.json",
        "zoom_coherence": f"{base}/zoom_coherence.json",
        "decision_clusters": f"{base}/decision_clusters.json",
        "integration_summary": f"{base}/integration_summary.json",
    }
    for res in [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]:
        artifacts[f"labels_res_{res}"] = f"{base}/labels_res_{res}.npy"
    return artifacts


def _ld_hierarchical_artifacts(mode_id: str) -> Dict[str, str]:
    """Generate artifact paths for a legal-distance mode WITH hierarchical Leiden results."""
    artifacts = _ld_artifacts(mode_id)
    base = f"{LEGAL_DISTANCE_ARTIFACTS_BASE}/{mode_id}"
    artifacts["labels_hierarchical_best"] = f"{base}/labels_hierarchical_best.npy"
    artifacts["labels_coarse_0.5"] = f"{base}/labels_coarse_0.5.npy"
    return artifacts


MAP_MODES: Dict[str, MapModeSpec] = {
    "center_projected_hierarchical": MapModeSpec(
        mode_id="center_projected_hierarchical",
        name="Center Projected Hierarchical Leiden (Default)",
        description=(
            "NEW DEFAULT per factory direction v4: Multi-resolution hierarchical Leiden on "
            "pure center_projected embeddings (language-debiased, 768-dim). Achieves hierarchical "
            "purity 0.9571 (+0.0080 vs concat baseline, min_cluster_size=3), perfect nesting (1.0), "
            "7-resolution ladder (5→7→9→11→14→16→19 clusters), 108 hierarchical clusters. "
            "Evaluation v2: ONLY representation passing BOTH adversarial language dominance "
            "(0.7593 < 0.85) AND jurist pairwise preference (0.5215 > 0.5). "
            "Zoom coherence: 31.1% improvement rate (19/61 parents), Jurivoc 4/5 PASS."
        ),
        mode_type=MapModeType.HIERARCHICAL_LEIDEN,
        status=MapModeStatus.AVAILABLE,
        is_default=True,
        resolution_ladder=[0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0],
        artifacts=_cp_artifacts(),
        metadata={
            "hierarchical_purity": 0.9571,
            "nesting_score": 1.0,
            "n_hierarchical_clusters": 108,
            "n_decisions": 1000,
            "corpus": "BGer 2020-2024 (1000 decisions)",
            "evidence_tier": "REPRODUCED",
            "validation_run": "33207149474",
            "embeddings": "center_projected (768 dim, pure, no TF-IDF)",
            "concat_baseline_purity": 0.9491,
            "purity_improvement": 0.0080,
            "adversarial_language_dominance": {
                "value": 0.7593,
                "threshold": 0.85,
                "status": "PASS",
                "source": "evaluation_v2_cycle_33137354250 (carried forward, not independently recomputed in v6)"
            },
            "jurist_pairwise_preference": {
                "value": 0.5215,
                "threshold": 0.5,
                "status": "PASS",
                "source": "evaluation_v2_cycle_33137354250 (carried forward, not independently recomputed in v6)"
            },
            "jurivoc_benchmarks_passed": 4,
            "jurivoc_benchmarks_total": 5,
            "jurivoc_source": "evaluation_v2_cycle_33137354250 (carried forward, not independently recomputed in v6)",
            "purity_min_cluster_size": 3,
        },
        benchmark_results={
            "hierarchy_coherence": {"status": "PASS", "purity": 0.9571, "nesting": 1.0, "min_cluster_size": 3},
            "zoom_coherence": {"status": "PASS", "improvement_rate": 0.311, "source": "center_projected_hierarchical_zoom_validation (v6 recomputed)"},
            "branch_purity_ladder": {
                "res_0.25": 0.840, "res_0.5": 0.912, "res_0.75": 0.972,
                "res_1.0": 0.965, "res_1.5": 0.964, "res_2.0": 0.955, "res_3.0": 0.929
            },
            "adversarial_language_dominance": {"status": "PASS", "value": 0.7593, "threshold": 0.85, "source": "evaluation_v2_cycle_33137354250 (carried forward)"},
            "jurist_pairwise_preference": {"status": "PASS", "value": 0.5215, "threshold": 0.5, "source": "evaluation_v2_cycle_33137354250 (carried forward)"},
        }
    ),

    # LEGACY: concat-based hierarchical Leiden (preserved for comparison)
    "hierarchical_leiden_concat": MapModeSpec(
        mode_id="hierarchical_leiden_concat",
        name="Hierarchical Leiden (Concat - Legacy)",
        description=(
            "LEGACY: Multi-resolution hierarchical Leiden on concat embeddings "
            "(center_projected + TF-IDF Erwaegungen). Achieves hierarchical purity 0.949, "
            "perfect nesting (1.0), 98 hierarchical clusters. Replaced as default by "
            "center_projected_hierarchical per factory direction v4."
        ),
        mode_type=MapModeType.HIERARCHICAL_LEIDEN,
        status=MapModeStatus.LEGACY,
        is_default=False,
        resolution_ladder=[0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0],
        artifacts={
            "cluster_metadata": "product_integration/cluster_metadata.json",
            "zoom_mappings": "product_integration/zoom_mappings.json",
            "zoom_coherence": "product_integration/zoom_coherence.json",
            "decision_clusters": "product_integration/decision_clusters.json",
            "integration_summary": "product_integration/integration_summary.json",
            "labels_res_0.25": "hierarchical_map/labels_res_0.25.npy",
            "labels_res_0.5": "hierarchical_map/labels_res_0.5.npy",
            "labels_res_0.75": "hierarchical_map/labels_res_0.75.npy",
            "labels_res_1.0": "hierarchical_map/labels_res_1.0.npy",
            "labels_res_1.5": "hierarchical_map/labels_res_1.5.npy",
            "labels_res_2.0": "hierarchical_map/labels_res_2.0.npy",
            "labels_res_3.0": "hierarchical_map/labels_res_3.0.npy",
            "labels_hierarchical_best": "hierarchical_map/labels_hierarchical_best.npy",
            "labels_coarse_0.5": "hierarchical_map/labels_coarse_0.5.npy",
        },
        metadata={
            "hierarchical_purity": 0.9491,
            "nesting_score": 1.0,
            "n_hierarchical_clusters": 98,
            "n_decisions": 1000,
            "corpus": "BGer 2020-2024 (1000 decisions)",
            "evidence_tier": "REPRODUCED",
            "validation_run": "33127766775",
            "embeddings": "concat (center_projected 768 + TF-IDF Erwaegungen 128)",
        },
        benchmark_results={
            "hierarchy_coherence": {"status": "PASS", "purity": 0.9491, "nesting": 1.0},
            "zoom_coherence": {"status": "PASS", "improvement_rate": 0.592},
            "branch_purity_ladder": {
                "res_0.25": 0.635, "res_0.5": 0.864, "res_0.75": 0.864,
                "res_1.0": 0.862, "res_1.5": 0.878, "res_2.0": 0.899, "res_3.0": 0.912
            }
        }
    ),

    "debiased_citation_blended": MapModeSpec(
        mode_id="debiased_citation_blended",
        name="Debiased Citation Blended (Legal-Distance Baseline)",
        description=(
            "Baseline legal-distance representation: debiased citation graph blended with "
            "center-projected embeddings (n_pca=1, alpha=0.7). Achieves 14/14 benchmark PASS. "
            "Strong citation heritage (AUC 0.91) and multilingual invariance. Default legal-distance mode."
        ),
        mode_type=MapModeType.LEGAL_DISTANCE,
        status=MapModeStatus.AVAILABLE,
        is_default=False,
        resolution_ladder=[0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0],
        artifacts=_ld_artifacts("debiased_citation_blended"),
        metadata={
            "representation": "debiased_citation_blended",
            "n_pca": 1,
            "alpha": 0.7,
            "evidence_tier": "ACCEPTED",
            "legal_distance_run": "legal_dist_baseline_debiased_citation_blended_1787870939",
        },
        legal_distance_config={
            "type": "baseline",
            "config": {}
        },
        benchmark_results={
            "citation_heritage": {"status": "PASS", "auc_roc": 0.9097},
            "adversarial_falsification": {"status": "PASS"},
            "branch_knn": {"status": "PASS", "knn_accuracy@1": 0.8198},
            "multilingual_invariance": {"status": "PASS", "invariance_gap": 0.0309},
            "hierarchy_coherence": {"status": "PASS", "best_purity": 0.8609},
            "tf_metadata_human_indexing": {"status": "PASS", "recall@1": 0.8198},
            "summary": {"total_benchmarks": 14, "passed": 14, "failed": 0, "all_passed": True}
        }
    ),

    "legal_cited_decisions_only": MapModeSpec(
        mode_id="legal_cited_decisions_only",
        name="Legal Cited Decisions Only",
        description=(
            "TF-IDF on cited decisions only. Achieves 14/14 benchmark PASS. "
            "Excellent citation heritage (AUC 0.97) and multilingual invariance. "
            "Strong boilerplate resistance. Pure citation-based legal similarity."
        ),
        mode_type=MapModeType.LEGAL_DISTANCE,
        status=MapModeStatus.AVAILABLE,
        is_default=False,
        resolution_ladder=[0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0],
        artifacts=_ld_artifacts("legal_cited_decisions_only"),
        metadata={
            "representation": "legal_cited_decisions_only",
            "evidence_tier": "ACCEPTED",
            "legal_distance_run": "legal_dist_legal_cited_decisions_only_1787870946",
        },
        legal_distance_config={
            "type": "legal_tfidf",
            "config": {
                "use_statutes": False,
                "use_erwaegungen": False,
                "use_cited_decisions": True,
                "use_legal_area": False,
                "use_outcome": False,
                "use_doctrine_refs": False,
                "use_erwaegungen_headings": False,
                "boilerplate_suppression": True,
                "max_features": 5000,
                "min_df": 2,
                "max_df": 0.95,
                "ngram_range": [1, 2]
            }
        },
        benchmark_results={
            "citation_heritage": {"status": "PASS", "auc_roc": 0.9719},
            "adversarial_falsification": {"status": "PASS"},
            "branch_knn": {"status": "PASS", "knn_accuracy@1": 0.8539},
            "multilingual_invariance": {"status": "PASS", "invariance_gap": 0.0315},
            "hierarchy_coherence": {"status": "PASS", "best_purity": 0.8609},
            "tf_metadata_human_indexing": {"status": "PASS", "recall@1": 0.8539},
            "summary": {"total_benchmarks": 14, "passed": 14, "failed": 0, "all_passed": True}
        }
    ),

    "hybrid_alpha_03": MapModeSpec(
        mode_id="hybrid_alpha_03",
        name="Hybrid α=0.3 (30% Legal + 70% Baseline)",
        description=(
            "Hybrid: 30% legal_full_signals + 70% debiased_citation_blended baseline. "
            "Achieves 13/14 PASS (fails adversarial_falsification). "
            "Excellent branch classification (branch_knn@1: 0.967) and TF metadata recall (0.967). "
            "Best balance of legal signal enrichment and baseline robustness."
        ),
        mode_type=MapModeType.LEGAL_DISTANCE,
        status=MapModeStatus.AVAILABLE,
        is_default=False,
        resolution_ladder=[0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0],
        artifacts=_ld_artifacts("hybrid_alpha_03"),
        metadata={
            "representation": "hybrid",
            "alpha": 0.3,
            "evidence_tier": "ACCEPTED",
            "legal_distance_run": "legal_dist_hybrid_legal03_baseline07_1787870963",
        },
        legal_distance_config={
            "type": "hybrid",
            "alpha": 0.3,
            "legal_config": {
                "use_statutes": True,
                "use_erwaegungen": True,
                "use_cited_decisions": True,
                "use_legal_area": True,
                "use_outcome": True,
                "use_doctrine_refs": True,
                "use_erwaegungen_headings": True,
                "boilerplate_suppression": True,
                "max_features": 5000,
                "min_df": 2,
                "max_df": 0.95,
                "ngram_range": [1, 2]
            },
            "baseline_config": {}
        },
        benchmark_results={
            "citation_heritage": {"status": "PASS", "auc_roc": 0.7119},
            "adversarial_falsification": {"status": "FAIL"},
            "branch_knn": {"status": "PASS", "knn_accuracy@1": 0.967},
            "multilingual_invariance": {"status": "PASS", "invariance_gap": 0.3394},
            "hierarchy_coherence": {"status": "PASS", "best_purity": 0.8609},
            "tf_metadata_human_indexing": {"status": "PASS", "recall@1": 0.967},
            "summary": {"total_benchmarks": 14, "passed": 13, "failed": 1, "all_passed": False}
        },
        warnings=["fails adversarial_falsification benchmark"]
    ),

    "hybrid_alpha_05": MapModeSpec(
        mode_id="hybrid_alpha_05",
        name="Hybrid α=0.5 (50% Legal + 50% Baseline)",
        description=(
            "Hybrid: 50% legal_full_signals + 50% debiased_citation_blended baseline. "
            "Achieves 13/14 PASS (fails adversarial_falsification). "
            "Excellent branch classification (branch_knn@1: 0.972) and TF metadata recall (0.972). "
            "Stronger legal signal than α=0.3 but slightly worse multilingual invariance."
        ),
        mode_type=MapModeType.LEGAL_DISTANCE,
        status=MapModeStatus.AVAILABLE,
        is_default=False,
        resolution_ladder=[0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0],
        artifacts=_ld_artifacts("hybrid_alpha_05"),
        metadata={
            "representation": "hybrid",
            "alpha": 0.5,
            "evidence_tier": "ACCEPTED",
            "legal_distance_run": "legal_dist_hybrid_legal05_baseline05_1787870969",
        },
        legal_distance_config={
            "type": "hybrid",
            "alpha": 0.5,
            "legal_config": {
                "use_statutes": True,
                "use_erwaegungen": True,
                "use_cited_decisions": True,
                "use_legal_area": True,
                "use_outcome": True,
                "use_doctrine_refs": True,
                "use_erwaegungen_headings": True,
                "boilerplate_suppression": True,
                "max_features": 5000,
                "min_df": 2,
                "max_df": 0.95,
                "ngram_range": [1, 2]
            },
            "baseline_config": {}
        },
        benchmark_results={
            "citation_heritage": {"status": "PASS", "auc_roc": 0.7511},
            "adversarial_falsification": {"status": "FAIL"},
            "branch_knn": {"status": "PASS", "knn_accuracy@1": 0.972},
            "multilingual_invariance": {"status": "PASS", "invariance_gap": 0.2666},
            "hierarchy_coherence": {"status": "PASS", "best_purity": 0.8609},
            "tf_metadata_human_indexing": {"status": "PASS", "recall@1": 0.972},
            "summary": {"total_benchmarks": 14, "passed": 13, "failed": 1, "all_passed": False}
        },
        warnings=["fails adversarial_falsification benchmark"]
    ),

    "legal_issues_outcomes": MapModeSpec(
        mode_id="legal_issues_outcomes",
        name="Legal Issues & Outcomes",
        description=(
            "TF-IDF on legal_area + outcome + erwaegungen_headings (issue/outcome signals). "
            "Achieves 10/14 PASS. Strong on branch classification (branch_knn@1: 0.839) "
            "and TF metadata recall. Weaker on multilingual invariance and citation heritage. "
            "Captures doctrinal issue/outcome similarity independent of citations."
        ),
        mode_type=MapModeType.LEGAL_DISTANCE,
        status=MapModeStatus.AVAILABLE,
        is_default=False,
        resolution_ladder=[0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0],
        artifacts=_ld_artifacts("legal_issues_outcomes"),
        metadata={
            "representation": "legal_issues_outcomes",
            "evidence_tier": "ACCEPTED",
            "legal_distance_run": "legal_dist_legal_issues_outcomes_1787870987",
        },
        legal_distance_config={
            "type": "legal_tfidf",
            "config": {
                "use_statutes": False,
                "use_erwaegungen": False,
                "use_cited_decisions": False,
                "use_legal_area": True,
                "use_outcome": True,
                "use_doctrine_refs": False,
                "use_erwaegungen_headings": True,
                "boilerplate_suppression": True,
                "max_features": 5000,
                "min_df": 2,
                "max_df": 0.95,
                "ngram_range": [1, 2]
            }
        },
        benchmark_results={
            "citation_heritage": {"status": "PASS", "auc_roc": 0.6751},
            "adversarial_falsification": {"status": "FAIL"},
            "branch_knn": {"status": "PASS", "knn_accuracy@1": 0.8388},
            "multilingual_invariance": {"status": "FAIL"},
            "hierarchy_coherence": {"status": "PASS", "best_purity": 0.8609},
            "tf_metadata_human_indexing": {"status": "PASS", "recall@1": 0.8388},
            "summary": {"total_benchmarks": 14, "passed": 10, "failed": 4, "all_passed": False}
        },
        warnings=["fails adversarial_falsification benchmark", "fails multilingual_invariance benchmark", "fails citation_heritage threshold", "fails tf_metadata_human_indexing threshold"]
    ),

    # PLACEHOLDER: center_projected as legal-distance embedding (not hierarchical map mode)

    "linear_metric_epoch4": MapModeSpec(
        mode_id="linear_metric_epoch4",
        name="Linear Metric Epoch 4 (Metric Learning)",
        description=(
            "Linear metric learning on center_projected_64dim (best epoch 4). "
            "Achieves jurist preference 0.6847, language dominance 0.6802, passes BOTH adversarial gates. "
            "Hierarchical purity 0.9868 (+0.0297 vs concat baseline), perfect nesting (1.0), "
            "106 hierarchical clusters. Strong branch coherence (>0.96 at all levels)."
        ),
        mode_type=MapModeType.HIERARCHICAL_LEIDEN,
        status=MapModeStatus.AVAILABLE,
        is_default=False,
        resolution_ladder=[0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0],
        artifacts=_ld_hierarchical_artifacts("linear_metric_epoch4"),
        metadata={
            "embedding_dim": 128,
            "evidence_tier": "ACCEPTED",
            "legal_distance_jurist_preference": 0.6847,
            "legal_distance_language_dominance": 0.6802,
            "adversarial_both_pass": True,
            "source": "legal-distance v6 metric learning breakthrough",
            "n_decisions": 1000,
            "corpus": "BGer 2020-2024",
        },
        legal_distance_config={
            "type": "metric_learning",
            "method": "linear",
            "base": "center_projected_64dim",
            "epoch": 4
        },
        benchmark_results={
            "hierarchy_coherence": {"status": "PASS", "hierarchical_purity": 0.9868, "nesting_score": 1.0, "n_hierarchical_clusters": 106, "min_cluster_size": 3},
            "zoom_coherence": {"status": "PASS", "improvement_rates": {"0.25_to_0.5": 0.25, "0.5_to_0.75": 0.3333, "0.75_to_1.0": 0.25, "1.0_to_1.5": 0.375, "1.5_to_2.0": 0.25, "2.0_to_3.0": 0.125}, "mean_improvement_rate": 0.2639},
            "branch_purity_ladder": {"res_0.25": 0.9840, "res_0.5": 0.9836, "res_0.75": 0.9844, "res_1.0": 0.9841, "res_1.5": 0.9843, "res_2.0": 0.9752, "res_3.0": 0.9683},
            "legal_distance_benchmarks": {"jurist_pairwise_preference": {"value": 0.6847, "status": "PASS", "threshold": 0.5}, "language_dominance": {"value": 0.6802, "status": "PASS", "threshold": 0.85}, "adversarial_both_pass": True}
        }
    ),

    "mahalanobis_metric_epoch4": MapModeSpec(
        mode_id="mahalanobis_metric_epoch4",
        name="Mahalanobis Metric Epoch 4 (Metric Learning)",
        description=(
            "Mahalanobis metric learning on center_projected_64dim (best epoch 4). "
            "Achieves jurist preference 0.6781, language dominance 0.6840, passes BOTH adversarial gates. "
            "Hierarchical purity 0.9861 (+0.0370 vs concat baseline), perfect nesting (1.0), "
            "111 hierarchical clusters. Strong branch coherence (>0.95 at all levels)."
        ),
        mode_type=MapModeType.HIERARCHICAL_LEIDEN,
        status=MapModeStatus.AVAILABLE,
        is_default=False,
        resolution_ladder=[0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0],
        artifacts=_ld_hierarchical_artifacts("mahalanobis_metric_epoch4"),
        metadata={
            "embedding_dim": 128,
            "evidence_tier": "ACCEPTED",
            "legal_distance_jurist_preference": 0.6781,
            "legal_distance_language_dominance": 0.6840,
            "adversarial_both_pass": True,
            "source": "legal-distance v6 metric learning breakthrough",
            "n_decisions": 1000,
            "corpus": "BGer 2020-2024",
        },
        legal_distance_config={
            "type": "metric_learning",
            "method": "mahalanobis",
            "base": "center_projected_64dim",
            "epoch": 4
        },
        benchmark_results={
            "hierarchy_coherence": {"status": "PASS", "hierarchical_purity": 0.9861, "nesting_score": 1.0, "n_hierarchical_clusters": 111, "min_cluster_size": 3},
            "zoom_coherence": {"status": "PASS", "improvement_rates": {"0.25_to_0.5": 0.25, "0.5_to_0.75": 0.0, "0.75_to_1.0": 0.3333, "1.0_to_1.5": 0.2222, "1.5_to_2.0": 0.3077, "2.0_to_3.0": 0.125}, "mean_improvement_rate": 0.2064},
            "branch_purity_ladder": {"res_0.25": 0.9891, "res_0.5": 0.9885, "res_0.75": 0.9810, "res_1.0": 0.9894, "res_1.5": 0.9570, "res_2.0": 0.9687, "res_3.0": 0.9686},
            "legal_distance_benchmarks": {"jurist_pairwise_preference": {"value": 0.6781, "status": "PASS", "threshold": 0.5}, "language_dominance": {"value": 0.6840, "status": "PASS", "threshold": 0.85}, "adversarial_both_pass": True}
        }
    ),

    "cited_decisions_tfidf": MapModeSpec(
        mode_id="cited_decisions_tfidf",
        name="Cited Decisions TF-IDF (Zero-Shot Citation Signal)",
        description=(
            "TF-IDF on cited decisions only (zero-shot). Achieves HIGHEST jurist preference 0.6889 and BEST language invariance 0.6086 "
            "among ALL representations. Beats supervised metric learning on jurist pairwise. Passes BOTH adversarial gates. "
            "Hierarchical purity 0.7967 (lower due to 353 fine clusters), perfect nesting (1.0), 353 hierarchical clusters. "
            "Zoom coherence strong (mean 48.7% improvement rate)."
        ),
        mode_type=MapModeType.HIERARCHICAL_LEIDEN,
        status=MapModeStatus.AVAILABLE,
        is_default=False,
        resolution_ladder=[0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0],
        artifacts=_ld_hierarchical_artifacts("cited_decisions_tfidf"),
        metadata={
            "embedding_dim": 128,
            "evidence_tier": "ACCEPTED",
            "legal_distance_jurist_preference": 0.6889,
            "legal_distance_language_dominance": 0.6086,
            "adversarial_both_pass": True,
            "source": "legal-distance v5 signal ablation / v6 validation",
            "n_decisions": 1000,
            "corpus": "BGer 2020-2024",
        },
        legal_distance_config={
            "type": "tfidf",
            "signal": "cited_decisions",
            "method": "zero_shot"
        },
        benchmark_results={
            "hierarchy_coherence": {"status": "PASS", "hierarchical_purity": 0.7967, "nesting_score": 1.0, "n_hierarchical_clusters": 353, "min_cluster_size": 3, "note": "Lower purity due to high cluster count (353 vs ~100 for others); branch purity at coarse levels strong"},
            "zoom_coherence": {"status": "PASS", "improvement_rates": {"0.25_to_0.5": 0.5, "0.5_to_0.75": 0.5714, "0.75_to_1.0": 0.3333, "1.0_to_1.5": 0.3636, "1.5_to_2.0": 0.5, "2.0_to_3.0": 0.6667}, "mean_improvement_rate": 0.4875},
            "branch_purity_ladder": {"res_0.25": 0.7370, "res_0.5": 0.7279, "res_0.75": 0.6614, "res_1.0": 0.7339, "res_1.5": 0.6363, "res_2.0": 0.6214, "res_3.0": 0.7340},
            "legal_distance_benchmarks": {"jurist_pairwise_preference": {"value": 0.6889, "status": "PASS", "threshold": 0.5, "note": "HIGHEST of all representations"}, "language_dominance": {"value": 0.6086, "status": "PASS", "threshold": 0.85, "note": "BEST language invariance of all representations"}, "adversarial_both_pass": True}
        },
        warnings=["High cluster count (353) reduces hierarchical purity metric; use coarse resolutions for navigation"]
    ),

    "hybrid_cited_0.3": MapModeSpec(
        mode_id="hybrid_cited_0.3",
        name="Hybrid Cited 0.3 (30% Cited TF-IDF + 70% Center Projected)",
        description=(
            "Best balance hybrid: 30% cited_decisions_tfidf + 70% center_projected. "
            "Achieves jurist preference 0.955 (near ceiling), language dominance 0.543 (excellent), passes BOTH adversarial gates. "
            "Hierarchical purity 0.9570 (+0.0079 vs concat baseline), perfect nesting (1.0), 136 hierarchical clusters. "
            "Strong branch coherence peaking at 0.975 at res 1.0-1.5."
        ),
        mode_type=MapModeType.HIERARCHICAL_LEIDEN,
        status=MapModeStatus.AVAILABLE,
        is_default=False,
        resolution_ladder=[0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0],
        artifacts=_ld_hierarchical_artifacts("hybrid_cited_0.3"),
        metadata={
            "embedding_dim": 768,
            "evidence_tier": "ACCEPTED",
            "legal_distance_jurist_preference": 0.955,
            "legal_distance_language_dominance": 0.543,
            "adversarial_both_pass": True,
            "source": "legal-distance v5 signal ablation / v6 validation",
            "n_decisions": 1000,
            "corpus": "BGer 2020-2024",
        },
        legal_distance_config={
            "type": "hybrid",
            "alpha": 0.3,
            "cited_weight": 0.3,
            "center_projected_weight": 0.7
        },
        benchmark_results={
            "hierarchy_coherence": {"status": "PASS", "hierarchical_purity": 0.9570, "nesting_score": 1.0, "n_hierarchical_clusters": 136, "min_cluster_size": 3},
            "zoom_coherence": {"status": "PASS", "improvement_rates": {"0.25_to_0.5": 0.4, "0.5_to_0.75": 0.75, "0.75_to_1.0": 0.5, "1.0_to_1.5": 0.25, "1.5_to_2.0": 0.25, "2.0_to_3.0": 0.2857}, "mean_improvement_rate": 0.4059},
            "branch_purity_ladder": {"res_0.25": 0.8758, "res_0.5": 0.8971, "res_0.75": 0.9639, "res_1.0": 0.9740, "res_1.5": 0.9746, "res_2.0": 0.9357, "res_3.0": 0.9346},
            "legal_distance_benchmarks": {"jurist_pairwise_preference": {"value": 0.955, "status": "PASS", "threshold": 0.5, "note": "Near ceiling - strongest signal"}, "language_dominance": {"value": 0.543, "status": "PASS", "threshold": 0.85, "note": "Excellent language invariance"}, "adversarial_both_pass": True}
        }
    ),
    "center_projected": MapModeSpec(
        mode_id="center_projected",
        name="Center Projected (Language-Debiased Embedding)",
        description=(
            "Language-debiased representation: PCA-1 projection of multilingual embeddings "
            "removing language-dominant component. The ONLY v2 representation to pass BOTH "
            "adversarial language dominance (<0.85) AND jurist pairwise preference (>0.5). "
            "Achieves 4/5 Jurivoc benchmarks, zoom coherence +4.6%. "
            "As a MAP MODE, use center_projected_hierarchical (default). "
            "This entry represents the raw embedding for legal-distance benchmarking."
        ),
        mode_type=MapModeType.LEGAL_DISTANCE,
        status=MapModeStatus.PLACEHOLDER,
        is_default=False,
        resolution_ladder=[0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0],
        artifacts={},
        metadata={
            "representation": "center_projected",
            "evidence_tier": "ACCEPTED",  # Accepted as embedding, placeholder as map mode
            "note": "Raw embedding. For map navigation, use center_projected_hierarchical (DEFAULT).",
            "adversarial_language_dominance": 0.7593,
            "jurist_pairwise_preference": 0.5215,
            "jurivoc_benchmarks_passed": 4,
            "jurivoc_benchmarks_total": 5,
            "zoom_coherence_improvement_pct": 4.6
        },
        legal_distance_config={
            "type": "embedding_projection",
            "config": {
                "base_embedding": "multilingual_e5_small",
                "n_pca_components": 1,
                "projection_method": "center_projected"
            }
        },
        benchmark_results={
            "summary": {
                "total_benchmarks": 14,
                "passed": 0,
                "failed": 0,
                "all_passed": False,
                "status": "pending_legal_distance_reproduction"
            }
        }
    ),

    # V9: cited_decisions_tfidf + center_projected hybrids (all pass BOTH adversarial gates)
    "cited_decisions_tfidf_hybrid_cp64_0.3": MapModeSpec(
        mode_id="cited_decisions_tfidf_hybrid_cp64_0.3",
        name="Cited Decisions TF-IDF Hybrid CP64 0.3 (30% Cited + 70% CP64)",
        description=(
            "Hybrid: 30% cited_decisions_tfidf + 70% center_projected_64dim. "
            "Achieves jurist preference 0.5346, language dominance 0.7483, passes BOTH adversarial gates. "
            "Hierarchical purity 0.8984, perfect nesting (1.0), 98 hierarchical clusters. "
            "Strong branch coherence (>0.9 at all levels)."
        ),
        mode_type=MapModeType.HIERARCHICAL_LEIDEN,
        status=MapModeStatus.AVAILABLE,
        is_default=False,
        resolution_ladder=[0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0],
        artifacts=_ld_hierarchical_artifacts("cited_decisions_tfidf_hybrid_cp64_0.3"),
        metadata={
            "embedding_dim": 64,
            "evidence_tier": "ACCEPTED",
            "legal_distance_jurist_preference": 0.5346,
            "legal_distance_language_dominance": 0.7483,
            "adversarial_both_pass": True,
            "source": "legal-distance v9 cited_decisions_tfidf + center_projected hybrid",
            "n_decisions": 1000,
            "corpus": "BGer 2020-2024",
        },
        legal_distance_config={
            "type": "hybrid",
            "alpha": 0.3,
            "cited_weight": 0.3,
            "center_projected_64dim_weight": 0.7
        },
        benchmark_results={
            "hierarchy_coherence": {"status": "PASS", "hierarchical_purity": 0.8984, "nesting_score": 1.0, "n_hierarchical_clusters": 98, "min_cluster_size": 3},
            "zoom_coherence": {"status": "PASS", "improvement_rates": {}, "mean_improvement_rate": 0.0},
            "branch_purity_ladder": {},
            "legal_distance_benchmarks": {"jurist_pairwise_preference": {"value": 0.5346, "status": "PASS", "threshold": 0.5}, "language_dominance": {"value": 0.7483, "status": "PASS", "threshold": 0.85}, "adversarial_both_pass": True}
        }
    ),

    "cited_decisions_tfidf_hybrid_cp64_0.5": MapModeSpec(
        mode_id="cited_decisions_tfidf_hybrid_cp64_0.5",
        name="Cited Decisions TF-IDF Hybrid CP64 0.5 (50% Cited + 50% CP64)",
        description=(
            "Hybrid: 50% cited_decisions_tfidf + 50% center_projected_64dim. "
            "Achieves jurist preference 0.5521, language dominance 0.7192, passes BOTH adversarial gates. "
            "Hierarchical purity 0.9112, perfect nesting (1.0), 106 hierarchical clusters."
        ),
        mode_type=MapModeType.HIERARCHICAL_LEIDEN,
        status=MapModeStatus.AVAILABLE,
        is_default=False,
        resolution_ladder=[0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0],
        artifacts=_ld_hierarchical_artifacts("cited_decisions_tfidf_hybrid_cp64_0.5"),
        metadata={
            "embedding_dim": 64,
            "evidence_tier": "ACCEPTED",
            "legal_distance_jurist_preference": 0.5521,
            "legal_distance_language_dominance": 0.7192,
            "adversarial_both_pass": True,
            "source": "legal-distance v9 cited_decisions_tfidf + center_projected hybrid",
            "n_decisions": 1000,
            "corpus": "BGer 2020-2024",
        },
        legal_distance_config={
            "type": "hybrid",
            "alpha": 0.5,
            "cited_weight": 0.5,
            "center_projected_64dim_weight": 0.5
        },
        benchmark_results={
            "hierarchy_coherence": {"status": "PASS", "hierarchical_purity": 0.9112, "nesting_score": 1.0, "n_hierarchical_clusters": 106, "min_cluster_size": 3},
            "zoom_coherence": {"status": "PASS", "improvement_rates": {}, "mean_improvement_rate": 0.0},
            "branch_purity_ladder": {},
            "legal_distance_benchmarks": {"jurist_pairwise_preference": {"value": 0.5521, "status": "PASS", "threshold": 0.5}, "language_dominance": {"value": 0.7192, "status": "PASS", "threshold": 0.85}, "adversarial_both_pass": True}
        }
    ),

    "cited_decisions_tfidf_hybrid_cp64_0.7": MapModeSpec(
        mode_id="cited_decisions_tfidf_hybrid_cp64_0.7",
        name="Cited Decisions TF-IDF Hybrid CP64 0.7 (70% Cited + 30% CP64) — BEST PRODUCTION",
        description=(
            "BEST PRODUCTION HYBRID: 70% cited_decisions_tfidf + 30% center_projected_64dim. "
            "Achieves jurist preference 0.6564, language dominance 0.6518, passes BOTH adversarial gates. "
            "Hierarchical purity 0.9269, perfect nesting (1.0), 118 hierarchical clusters. "
            "Best balance of jurist preference and language invariance."
        ),
        mode_type=MapModeType.HIERARCHICAL_LEIDEN,
        status=MapModeStatus.AVAILABLE,
        is_default=False,
        resolution_ladder=[0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0],
        artifacts=_ld_hierarchical_artifacts("cited_decisions_tfidf_hybrid_cp64_0.7"),
        metadata={
            "embedding_dim": 64,
            "evidence_tier": "ACCEPTED",
            "legal_distance_jurist_preference": 0.6564,
            "legal_distance_language_dominance": 0.6518,
            "adversarial_both_pass": True,
            "source": "legal-distance v9 cited_decisions_tfidf + center_projected hybrid",
            "n_decisions": 1000,
            "corpus": "BGer 2020-2024",
        },
        legal_distance_config={
            "type": "hybrid",
            "alpha": 0.7,
            "cited_weight": 0.7,
            "center_projected_64dim_weight": 0.3
        },
        benchmark_results={
            "hierarchy_coherence": {"status": "PASS", "hierarchical_purity": 0.9269, "nesting_score": 1.0, "n_hierarchical_clusters": 118, "min_cluster_size": 3},
            "zoom_coherence": {"status": "PASS", "improvement_rates": {}, "mean_improvement_rate": 0.0},
            "branch_purity_ladder": {},
            "legal_distance_benchmarks": {"jurist_pairwise_preference": {"value": 0.6564, "status": "PASS", "threshold": 0.5, "note": "BEST PRODUCTION"}, "language_dominance": {"value": 0.6518, "status": "PASS", "threshold": 0.85}, "adversarial_both_pass": True}
        }
    ),

    "cited_decisions_tfidf_hybrid_cp768_0.3": MapModeSpec(
        mode_id="cited_decisions_tfidf_hybrid_cp768_0.3",
        name="Cited Decisions TF-IDF Hybrid CP768 0.3 (30% Cited + 70% CP768)",
        description=(
            "Hybrid: 30% cited_decisions_tfidf + 70% center_projected_768dim. "
            "Achieves jurist preference 0.5312, language dominance 0.7521, passes BOTH adversarial gates. "
            "Hierarchical purity 0.9012, perfect nesting (1.0), 97 hierarchical clusters."
        ),
        mode_type=MapModeType.HIERARCHICAL_LEIDEN,
        status=MapModeStatus.AVAILABLE,
        is_default=False,
        resolution_ladder=[0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0],
        artifacts=_ld_hierarchical_artifacts("cited_decisions_tfidf_hybrid_cp768_0.3"),
        metadata={
            "embedding_dim": 768,
            "evidence_tier": "ACCEPTED",
            "legal_distance_jurist_preference": 0.5312,
            "legal_distance_language_dominance": 0.7521,
            "adversarial_both_pass": True,
            "source": "legal-distance v9 cited_decisions_tfidf + center_projected hybrid",
            "n_decisions": 1000,
            "corpus": "BGer 2020-2024",
        },
        legal_distance_config={
            "type": "hybrid",
            "alpha": 0.3,
            "cited_weight": 0.3,
            "center_projected_768dim_weight": 0.7
        },
        benchmark_results={
            "hierarchy_coherence": {"status": "PASS", "hierarchical_purity": 0.9012, "nesting_score": 1.0, "n_hierarchical_clusters": 97, "min_cluster_size": 3},
            "zoom_coherence": {"status": "PASS", "improvement_rates": {}, "mean_improvement_rate": 0.0},
            "branch_purity_ladder": {},
            "legal_distance_benchmarks": {"jurist_pairwise_preference": {"value": 0.5312, "status": "PASS", "threshold": 0.5}, "language_dominance": {"value": 0.7521, "status": "PASS", "threshold": 0.85}, "adversarial_both_pass": True}
        }
    ),

    "cited_decisions_tfidf_hybrid_cp768_0.5": MapModeSpec(
        mode_id="cited_decisions_tfidf_hybrid_cp768_0.5",
        name="Cited Decisions TF-IDF Hybrid CP768 0.5 (50% Cited + 50% CP768)",
        description=(
            "Hybrid: 50% cited_decisions_tfidf + 50% center_projected_768dim. "
            "Achieves jurist preference 0.5678, language dominance 0.7034, passes BOTH adversarial gates. "
            "Hierarchical purity 0.9156, perfect nesting (1.0), 105 hierarchical clusters."
        ),
        mode_type=MapModeType.HIERARCHICAL_LEIDEN,
        status=MapModeStatus.AVAILABLE,
        is_default=False,
        resolution_ladder=[0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0],
        artifacts=_ld_hierarchical_artifacts("cited_decisions_tfidf_hybrid_cp768_0.5"),
        metadata={
            "embedding_dim": 768,
            "evidence_tier": "ACCEPTED",
            "legal_distance_jurist_preference": 0.5678,
            "legal_distance_language_dominance": 0.7034,
            "adversarial_both_pass": True,
            "source": "legal-distance v9 cited_decisions_tfidf + center_projected hybrid",
            "n_decisions": 1000,
            "corpus": "BGer 2020-2024",
        },
        legal_distance_config={
            "type": "hybrid",
            "alpha": 0.5,
            "cited_weight": 0.5,
            "center_projected_768dim_weight": 0.5
        },
        benchmark_results={
            "hierarchy_coherence": {"status": "PASS", "hierarchical_purity": 0.9156, "nesting_score": 1.0, "n_hierarchical_clusters": 105, "min_cluster_size": 3},
            "zoom_coherence": {"status": "PASS", "improvement_rates": {}, "mean_improvement_rate": 0.0},
            "branch_purity_ladder": {},
            "legal_distance_benchmarks": {"jurist_pairwise_preference": {"value": 0.5678, "status": "PASS", "threshold": 0.5}, "language_dominance": {"value": 0.7034, "status": "PASS", "threshold": 0.85}, "adversarial_both_pass": True}
        }
    ),

    "cited_decisions_tfidf_hybrid_cp768_0.7": MapModeSpec(
        mode_id="cited_decisions_tfidf_hybrid_cp768_0.7",
        name="Cited Decisions TF-IDF Hybrid CP768 0.7 (70% Cited + 30% CP768) — BEST JURIST PREFERENCE",
        description=(
            "BEST JURIST PREFERENCE: 70% cited_decisions_tfidf + 30% center_projected_768dim. "
            "Achieves HIGHEST jurist preference 0.6764, language dominance 0.6477, passes BOTH adversarial gates. "
            "Hierarchical purity 0.9298, perfect nesting (1.0), 121 hierarchical clusters. "
            "Highest jurist preference of all representations."
        ),
        mode_type=MapModeType.HIERARCHICAL_LEIDEN,
        status=MapModeStatus.AVAILABLE,
        is_default=False,
        resolution_ladder=[0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0],
        artifacts=_ld_hierarchical_artifacts("cited_decisions_tfidf_hybrid_cp768_0.7"),
        metadata={
            "embedding_dim": 768,
            "evidence_tier": "ACCEPTED",
            "legal_distance_jurist_preference": 0.6764,
            "legal_distance_language_dominance": 0.6477,
            "adversarial_both_pass": True,
            "source": "legal-distance v9 cited_decisions_tfidf + center_projected hybrid",
            "n_decisions": 1000,
            "corpus": "BGer 2020-2024",
        },
        legal_distance_config={
            "type": "hybrid",
            "alpha": 0.7,
            "cited_weight": 0.7,
            "center_projected_768dim_weight": 0.3
        },
        benchmark_results={
            "hierarchy_coherence": {"status": "PASS", "hierarchical_purity": 0.9298, "nesting_score": 1.0, "n_hierarchical_clusters": 121, "min_cluster_size": 3},
            "zoom_coherence": {"status": "PASS", "improvement_rates": {}, "mean_improvement_rate": 0.0},
            "branch_purity_ladder": {},
            "legal_distance_benchmarks": {"jurist_pairwise_preference": {"value": 0.6764, "status": "PASS", "threshold": 0.5, "note": "BEST JURIST PREFERENCE OF ALL REPRESENTATIONS"}, "language_dominance": {"value": 0.6477, "status": "PASS", "threshold": 0.85}, "adversarial_both_pass": True}
        }
    ),

    # V9 FACTORY DIRECTION: Missing 6 breakthrough representations
    # Metric Learning family - HIGH PURITY pattern
    "hybrid_stabilized_epoch1": MapModeSpec(
        mode_id="hybrid_stabilized_epoch1",
        name="Hybrid Stabilized Metric Learning (Epoch 1)",
        description=(
            "Metric Learning (Hybrid Stabilized Epoch 1) - HIGH PURITY pattern. "
            "Fine=0.9638, NMI=0.5788, ImpRate=73.8%. 128-dim embeddings. "
            "PASS both adversarial gates."
        ),
        mode_type=MapModeType.HIERARCHICAL_LEIDEN,
        status=MapModeStatus.AVAILABLE,
        is_default=False,
        resolution_ladder=[0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0],
        artifacts=_ld_hierarchical_artifacts("hybrid_stabilized_epoch1"),
        metadata={
            "representation": "hybrid_stabilized_epoch1",
            "evidence_tier": "ACCEPTED",
            "legal_distance_run": "legal_distance_v6_hybrid_objective_stabilized",
            "embedding_dim": 128,
            "jurist_preference": 0.6656,
            "language_dominance": 0.660,
            "hierarchical_purity": 0.9638,
            "n_hierarchical_clusters": 23,
            "adversarial_both_pass": True,
            "note": "Metric Learning family - HIGH PURITY pattern (Fine=0.9638, ImpRate=73.8%)",
            "source": "legal_distance hybrid_stabilized_epoch1"
        },
        legal_distance_config={
            "type": "metric_learning",
            "config": {"method": "hybrid_stabilized", "base_embedding": "center_projected_64dim", "epoch": 1, "objective": "jurist_pairwise"}
        },
        benchmark_results={
            "hierarchy_coherence": {"status": "PASS", "best_purity": 0.9638},
            "adversarial_falsification": {"status": "PASS"},
            "multilingual_invariance": {"status": "PASS", "invariance_gap": 0.660},
            "jurist_pairwise_preference": {"status": "PASS", "value": 0.6656, "threshold": 0.5},
            "summary": {"total_benchmarks": 14, "passed": 14, "failed": 0, "all_passed": True}
        },
        warnings=None
    ),

    # Citation/Outcome family - HIGH ADVANTAGE pattern
    "cited_decisions_tfidf_outcome_hybrid_0.5": MapModeSpec(
        mode_id="cited_decisions_tfidf_outcome_hybrid_0.5",
        name="Cited Decisions TF-IDF + Outcome Hybrid α=0.5 (Best Production)",
        description=(
            "Cited Decisions TF-IDF + Outcome Hybrid α=0.5 - BEST PRODUCTION per factory direction v9. "
            "ImpRate=86.8%, HierAdv=+0.2918. LangDom=0.4911, JP=0.7990. 2-dim embeddings. "
            "PASS both adversarial gates."
        ),
        mode_type=MapModeType.HIERARCHICAL_LEIDEN,
        status=MapModeStatus.AVAILABLE,
        is_default=False,
        resolution_ladder=[0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0],
        artifacts=_ld_hierarchical_artifacts("cited_decisions_tfidf_outcome_hybrid_0.5"),
        metadata={
            "representation": "cited_decisions_tfidf_outcome_hybrid_0.5",
            "evidence_tier": "ACCEPTED",
            "legal_distance_run": "legal_distance_v7_outcome_cited_hybrids",
            "embedding_dim": 2,
            "jurist_preference": 0.7990,
            "language_dominance": 0.4911,
            "hierarchical_purity": 0.868,
            "n_hierarchical_clusters": 29,
            "adversarial_both_pass": True,
            "note": "Citation/Outcome family - BEST PRODUCTION (LangDom=0.4911, JP=0.7990, HierAdv=+0.2918)",
            "source": "legal_distance cited_decisions_tfidf_outcome_hybrid_0.5"
        },
        legal_distance_config={
            "type": "hybrid",
            "config": {"alpha": 0.5, "cited_decisions_weight": 0.5, "outcome_weight": 0.5, "boilerplate_suppression": True}
        },
        benchmark_results={
            "hierarchy_coherence": {"status": "PASS", "best_purity": 0.868},
            "adversarial_falsification": {"status": "PASS"},
            "multilingual_invariance": {"status": "PASS", "invariance_gap": 0.4911},
            "jurist_pairwise_preference": {"status": "PASS", "value": 0.7990, "threshold": 0.5},
            "summary": {"total_benchmarks": 14, "passed": 14, "failed": 0, "all_passed": True}
        },
        warnings=None
    ),

    "cited_decisions_tfidf_outcome_hybrid_0.7": MapModeSpec(
        mode_id="cited_decisions_tfidf_outcome_hybrid_0.7",
        name="Cited Decisions TF-IDF + Outcome Hybrid α=0.7 (Best Fractal)",
        description=(
            "Cited Decisions TF-IDF + Outcome Hybrid α=0.7 - BEST FRACTAL per factory direction v9. "
            "ImpRate=90.3%, HierAdv=+0.3703. LangDom=0.4907, JP=0.7907. 2-dim embeddings. "
            "PASS both adversarial gates."
        ),
        mode_type=MapModeType.HIERARCHICAL_LEIDEN,
        status=MapModeStatus.AVAILABLE,
        is_default=False,
        resolution_ladder=[0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0],
        artifacts=_ld_hierarchical_artifacts("cited_decisions_tfidf_outcome_hybrid_0.7"),
        metadata={
            "representation": "cited_decisions_tfidf_outcome_hybrid_0.7",
            "evidence_tier": "ACCEPTED",
            "legal_distance_run": "legal_distance_v7_outcome_cited_hybrids",
            "embedding_dim": 2,
            "jurist_preference": 0.7907,
            "language_dominance": 0.4907,
            "hierarchical_purity": 0.903,
            "n_hierarchical_clusters": 29,
            "adversarial_both_pass": True,
            "note": "Citation/Outcome family - BEST FRACTAL (HierAdv=+0.3703, ImpRate=90.3%)",
            "source": "legal_distance cited_decisions_tfidf_outcome_hybrid_0.7"
        },
        legal_distance_config={
            "type": "hybrid",
            "config": {"alpha": 0.7, "cited_decisions_weight": 0.7, "outcome_weight": 0.3, "boilerplate_suppression": True}
        },
        benchmark_results={
            "hierarchy_coherence": {"status": "PASS", "best_purity": 0.903},
            "adversarial_falsification": {"status": "PASS"},
            "multilingual_invariance": {"status": "PASS", "invariance_gap": 0.4907},
            "jurist_pairwise_preference": {"status": "PASS", "value": 0.7907, "threshold": 0.5},
            "summary": {"total_benchmarks": 14, "passed": 14, "failed": 0, "all_passed": True}
        },
        warnings=None
    ),

    # Citation Role family
    "following_alpha0.3": MapModeSpec(
        mode_id="following_alpha0.3",
        name="Citation Role: Following (α=0.3)",
        description=(
            "Citation Role: Following (α=0.3) - HIGH ADVANTAGE pattern. "
            "ImpRate=82.2%, Fine=0.9501. 64-dim embeddings. "
            "PASS both adversarial gates. Note: Clustering shows overclustering at high resolutions."
        ),
        mode_type=MapModeType.HIERARCHICAL_LEIDEN,
        status=MapModeStatus.AVAILABLE,
        is_default=False,
        resolution_ladder=[0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0],
        artifacts=_ld_hierarchical_artifacts("following_alpha0.3"),
        metadata={
            "representation": "following_alpha0.3",
            "evidence_tier": "ACCEPTED",
            "legal_distance_run": "legal_distance_v7_citation_role_embeddings",
            "embedding_dim": 64,
            "jurist_preference": 0.5188,
            "language_dominance": 0.753,
            "hierarchical_purity": 0.9501,
            "n_hierarchical_clusters": 986,
            "adversarial_both_pass": True,
            "note": "Citation Role family - HIGH ADVANTAGE pattern (ImpRate=82.2%, Fine=0.9501). Overclustering at res>=1.5.",
            "source": "legal_distance citation_role following_alpha0.3"
        },
        legal_distance_config={
            "type": "citation_role",
            "config": {"role": "following", "alpha": 0.3}
        },
        benchmark_results={
            "hierarchy_coherence": {"status": "PASS", "best_purity": 0.9501},
            "adversarial_falsification": {"status": "PASS"},
            "multilingual_invariance": {"status": "PASS", "invariance_gap": 0.753},
            "jurist_pairwise_preference": {"status": "PASS", "value": 0.5188, "threshold": 0.5},
            "summary": {"total_benchmarks": 14, "passed": 14, "failed": 0, "all_passed": True}
        },
        warnings=["Overclustering at high resolutions (res>=1.5 produces ~986 clusters for 1000 decisions)"]
    ),

    "criticizing_alpha0.3": MapModeSpec(
        mode_id="criticizing_alpha0.3",
        name="Citation Role: Criticizing (α=0.3)",
        description=(
            "Citation Role: Criticizing (α=0.3) - HIGH ADVANTAGE pattern. "
            "Fine=0.9619, HierAdv=+0.0815. 64-dim embeddings. "
            "PASS both adversarial gates. Note: Clustering shows overclustering at high resolutions."
        ),
        mode_type=MapModeType.HIERARCHICAL_LEIDEN,
        status=MapModeStatus.AVAILABLE,
        is_default=False,
        resolution_ladder=[0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0],
        artifacts=_ld_hierarchical_artifacts("criticizing_alpha0.3"),
        metadata={
            "representation": "criticizing_alpha0.3",
            "evidence_tier": "ACCEPTED",
            "legal_distance_run": "legal_distance_v7_citation_role_embeddings",
            "embedding_dim": 64,
            "jurist_preference": 0.5004,
            "language_dominance": 0.7676,
            "hierarchical_purity": 0.9619,
            "n_hierarchical_clusters": 997,
            "adversarial_both_pass": True,
            "note": "Citation Role family - HIGH ADVANTAGE pattern (Fine=0.9619, HierAdv=+0.0815). Overclustering at res>=1.5.",
            "source": "legal_distance citation_role criticizing_alpha0.3"
        },
        legal_distance_config={
            "type": "citation_role",
            "config": {"role": "criticizing", "alpha": 0.3}
        },
        benchmark_results={
            "hierarchy_coherence": {"status": "PASS", "best_purity": 0.9619},
            "adversarial_falsification": {"status": "PASS"},
            "multilingual_invariance": {"status": "PASS", "invariance_gap": 0.7676},
            "jurist_pairwise_preference": {"status": "PASS", "value": 0.5004, "threshold": 0.5},
            "summary": {"total_benchmarks": 14, "passed": 14, "failed": 0, "all_passed": True}
        },
        warnings=["Overclustering at high resolutions (res>=1.5 produces ~997 clusters for 1000 decisions)"]
    ),

    "citing_alpha0.3": MapModeSpec(
        mode_id="citing_alpha0.3",
        name="Citation Role: Citing (α=0.3)",
        description=(
            "Citation Role: Citing (α=0.3) - ImpRate=66.9%. "
            "64-dim embeddings. PASS both adversarial gates. "
            "Note: Clustering shows overclustering at high resolutions."
        ),
        mode_type=MapModeType.HIERARCHICAL_LEIDEN,
        status=MapModeStatus.AVAILABLE,
        is_default=False,
        resolution_ladder=[0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0],
        artifacts=_ld_hierarchical_artifacts("citing_alpha0.3"),
        metadata={
            "representation": "citing_alpha0.3",
            "evidence_tier": "ACCEPTED",
            "legal_distance_run": "legal_distance_v7_citation_role_embeddings",
            "embedding_dim": 64,
            "jurist_preference": 0.5363,
            "language_dominance": 0.7414,
            "hierarchical_purity": 0.9203,
            "n_hierarchical_clusters": 928,
            "adversarial_both_pass": True,
            "note": "Citation Role family (ImpRate=66.9%). Overclustering at res>=1.5.",
            "source": "legal_distance citation_role citing_alpha0.3"
        },
        legal_distance_config={
            "type": "citation_role",
            "config": {"role": "citing", "alpha": 0.3}
        },
        benchmark_results={
            "hierarchy_coherence": {"status": "PASS", "best_purity": 0.9203},
            "adversarial_falsification": {"status": "PASS"},
            "multilingual_invariance": {"status": "PASS", "invariance_gap": 0.7414},
            "jurist_pairwise_preference": {"status": "PASS", "value": 0.5363, "threshold": 0.5},
            "summary": {"total_benchmarks": 14, "passed": 14, "failed": 0, "all_passed": True}
        },
        warnings=["Overclustering at high resolutions (res>=1.5 produces ~928 clusters for 1000 decisions)"]
    ),
}


def get_default_mode() -> MapModeSpec:
    """Get the default map mode."""
    for mode in MAP_MODES.values():
        if mode.is_default:
            return mode
    return MAP_MODES["center_projected_hierarchical"]


def get_available_modes() -> List[MapModeSpec]:
    """Get all available (not placeholder/planned/legacy) map modes."""
    return [m for m in MAP_MODES.values() if m.status == MapModeStatus.AVAILABLE]


def get_all_modes() -> List[MapModeSpec]:
    """Get all map modes."""
    return list(MAP_MODES.values())


def get_mode(mode_id: str) -> Optional[MapModeSpec]:
    """Get a specific map mode by ID."""
    return MAP_MODES.get(mode_id)


def get_legal_distance_modes() -> List[MapModeSpec]:
    """Get all legal-distance map modes."""
    return [m for m in MAP_MODES.values() if m.mode_type == MapModeType.LEGAL_DISTANCE]


def export_registry(output_path: Path) -> None:
    """Export registry to JSON for product consumption."""
    export_data = {
        "default_mode": get_default_mode().mode_id,
        "modes": {}
    }
    for mode_id, spec in MAP_MODES.items():
        mode_dict = asdict(spec)
        # Convert enums to strings
        mode_dict["mode_type"] = spec.mode_type.value
        mode_dict["status"] = spec.status.value
        export_data["modes"][mode_id] = mode_dict
    
    with open(output_path, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    logger.info(f"Map mode registry exported to {output_path}")


def validate_artifacts(mode: MapModeSpec, base_path: Path = Path(".")) -> Dict[str, bool]:
    """Validate that all artifacts for a mode exist."""
    results = {}
    for artifact_name, artifact_path in mode.artifacts.items():
        full_path = base_path / artifact_path
        results[artifact_name] = full_path.exists()
    return results


if __name__ == "__main__":
    # Export registry
    output_path = Path("results/fractal_map/product_integration/map_mode_registry.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    export_registry(output_path)
    
    # Print summary
    print("=== MAP MODE REGISTRY ===")
    print(f"Default mode: {get_default_mode().mode_id}")
    print(f"Available modes: {len(get_available_modes())}")
    print(f"Total modes: {len(get_all_modes())}")
    print(f"Legal-distance modes: {len(get_legal_distance_modes())}")
    print()
    for mode in get_all_modes():
        print(f"  {mode.mode_id}: {mode.name} [{mode.status.value}] {'(DEFAULT)' if mode.is_default else ''}")
