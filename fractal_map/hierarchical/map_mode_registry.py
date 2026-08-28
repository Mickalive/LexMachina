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


# ============================================================================
# MAP MODE REGISTRY
# ============================================================================

CENTER_PROJECTED_ARTIFACTS_BASE = "results/fractal_map/hierarchical_map_center_projected"
LEGAL_DISTANCE_ARTIFACTS_BASE = "results/fractal_map/legal_distance_modes"

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
    """Generate artifact paths for a legal-distance mode."""
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


MAP_MODES: Dict[str, MapModeSpec] = {
    "center_projected_hierarchical": MapModeSpec(
        mode_id="center_projected_hierarchical",
        name="Center Projected Hierarchical Leiden (Default)",
        description=(
            "NEW DEFAULT per factory direction v4: Multi-resolution hierarchical Leiden on "
            "pure center_projected embeddings (language-debiased, 768-dim). Achieves hierarchical "
            "purity 0.9638 (+0.0148 vs concat baseline), perfect nesting (1.0), 7-resolution "
            "ladder (5→7→9→11→14→16→19 clusters), 108 hierarchical clusters. "
            "Evaluation v2: ONLY representation passing BOTH adversarial language dominance "
            "(0.7593 < 0.85) AND jurist pairwise preference (0.5215 > 0.5). "
            "Zoom coherence validated, Jurivoc 4/5 PASS."
        ),
        mode_type=MapModeType.HIERARCHICAL_LEIDEN,
        status=MapModeStatus.AVAILABLE,
        is_default=True,
        resolution_ladder=[0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0],
        artifacts=_cp_artifacts(),
        metadata={
            "hierarchical_purity": 0.9638,
            "nesting_score": 1.0,
            "n_hierarchical_clusters": 108,
            "n_decisions": 1000,
            "corpus": "BGer 2020-2024 (1000 decisions)",
            "evidence_tier": "REPRODUCED",
            "validation_run": "33127766775",
            "embeddings": "center_projected (768 dim, pure, no TF-IDF)",
            "concat_baseline_purity": 0.9491,
            "purity_improvement": 0.0148,
            "adversarial_language_dominance": 0.7593,
            "jurist_pairwise_preference": 0.5215,
            "jurivoc_benchmarks_passed": 4,
            "jurivoc_benchmarks_total": 5,
        },
        benchmark_results={
            "hierarchy_coherence": {"status": "PASS", "purity": 0.9638, "nesting": 1.0},
            "zoom_coherence": {"status": "PASS", "improvement_rate": 0.592},
            "branch_purity_ladder": {
                "res_0.25": 0.840, "res_0.5": 0.912, "res_0.75": 0.972,
                "res_1.0": 0.965, "res_1.5": 0.964, "res_2.0": 0.955, "res_3.0": 0.929
            },
            "adversarial_language_dominance": {"status": "PASS", "value": 0.7593, "threshold": 0.85},
            "jurist_pairwise_preference": {"status": "PASS", "value": 0.5215, "threshold": 0.5},
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
            "cluster_metadata": "results/fractal_map/product_integration/cluster_metadata.json",
            "zoom_mappings": "results/fractal_map/product_integration/zoom_mappings.json",
            "zoom_coherence": "results/fractal_map/product_integration/zoom_coherence.json",
            "decision_clusters": "results/fractal_map/product_integration/decision_clusters.json",
            "integration_summary": "results/fractal_map/product_integration/integration_summary.json",
            "labels_res_0.25": "results/fractal_map/hierarchical_map/labels_res_0.25.npy",
            "labels_res_0.5": "results/fractal_map/hierarchical_map/labels_res_0.5.npy",
            "labels_res_0.75": "results/fractal_map/hierarchical_map/labels_res_0.75.npy",
            "labels_res_1.0": "results/fractal_map/hierarchical_map/labels_res_1.0.npy",
            "labels_res_1.5": "results/fractal_map/hierarchical_map/labels_res_1.5.npy",
            "labels_res_2.0": "results/fractal_map/hierarchical_map/labels_res_2.0.npy",
            "labels_res_3.0": "results/fractal_map/hierarchical_map/labels_res_3.0.npy",
            "labels_hierarchical_best": "results/fractal_map/hierarchical_map/labels_hierarchical_best.npy",
            "labels_coarse_0.5": "results/fractal_map/hierarchical_map/labels_coarse_0.5.npy",
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
        }
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
        }
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
        }
    ),

    # PLACEHOLDER: center_projected as legal-distance embedding (not hierarchical map mode)
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
