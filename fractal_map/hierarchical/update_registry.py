#!/usr/bin/env python3
"""
Update map_mode_registry.json with the 6 new missing modes from factory direction v9.
"""

import json
import os
from datetime import datetime, timezone

# Load existing registry
with open('results/fractal_map/product_integration/map_mode_registry.json') as f:
    registry = json.load(f)

# New modes to add
new_modes = {
    "hybrid_stabilized_epoch1": {
        "mode_id": "hybrid_stabilized_epoch1",
        "name": "Hybrid Stabilized Metric Learning (Epoch 1)",
        "description": "Metric Learning (Hybrid Stabilized Epoch 1) - HIGH PURITY pattern. Fine=0.9638, NMI=0.5788, ImpRate=73.8%. 128-dim embeddings. PASS both adversarial gates.",
        "mode_type": "legal_distance",
        "status": "available",
        "is_default": False,
        "resolution_ladder": [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0],
        "artifacts": {
            "cluster_metadata": "legal_distance_modes/hybrid_stabilized_epoch1/cluster_metadata.json",
            "zoom_mappings": "legal_distance_modes/hybrid_stabilized_epoch1/zoom_mappings.json",
            "zoom_coherence": "legal_distance_modes/hybrid_stabilized_epoch1/zoom_coherence.json",
            "decision_clusters": "legal_distance_modes/hybrid_stabilized_epoch1/decision_clusters.json",
            "integration_summary": "legal_distance_modes/hybrid_stabilized_epoch1/integration_summary.json",
            "labels_res_0.25": "legal_distance_modes/hybrid_stabilized_epoch1/labels_res_0.25.npy",
            "labels_res_0.5": "legal_distance_modes/hybrid_stabilized_epoch1/labels_res_0.5.npy",
            "labels_res_0.75": "legal_distance_modes/hybrid_stabilized_epoch1/labels_res_0.75.npy",
            "labels_res_1.0": "legal_distance_modes/hybrid_stabilized_epoch1/labels_res_1.0.npy",
            "labels_res_1.5": "legal_distance_modes/hybrid_stabilized_epoch1/labels_res_1.5.npy",
            "labels_res_2.0": "legal_distance_modes/hybrid_stabilized_epoch1/labels_res_2.0.npy",
            "labels_res_3.0": "legal_distance_modes/hybrid_stabilized_epoch1/labels_res_3.0.npy",
            "labels_hierarchical_best": "legal_distance_modes/hybrid_stabilized_epoch1/labels_hierarchical_best.npy",
            "labels_coarse_0.5": "legal_distance_modes/hybrid_stabilized_epoch1/labels_coarse_0.5.npy"
        },
        "metadata": {
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
        "legal_distance_config": {
            "type": "metric_learning",
            "config": {"method": "hybrid_stabilized", "base_embedding": "center_projected_64dim", "epoch": 1, "objective": "jurist_pairwise"}
        },
        "benchmark_results": {
            "hierarchy_coherence": {"status": "PASS", "best_purity": 0.9638},
            "adversarial_falsification": {"status": "PASS"},
            "multilingual_invariance": {"status": "PASS", "invariance_gap": 0.660},
            "jurist_pairwise_preference": {"status": "PASS", "value": 0.6656, "threshold": 0.5},
            "summary": {"total_benchmarks": 14, "passed": 14, "failed": 0, "all_passed": True}
        },
        "warnings": None
    },
    "cited_decisions_tfidf_outcome_hybrid_0.5": {
        "mode_id": "cited_decisions_tfidf_outcome_hybrid_0.5",
        "name": "Cited Decisions TF-IDF + Outcome Hybrid α=0.5 (Best Production)",
        "description": "Cited Decisions TF-IDF + Outcome Hybrid α=0.5 - BEST PRODUCTION per factory direction v9. ImpRate=86.8%, HierAdv=+0.2918. LangDom=0.4911, JP=0.7990. 2-dim embeddings. PASS both adversarial gates.",
        "mode_type": "legal_distance",
        "status": "available",
        "is_default": False,
        "resolution_ladder": [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0],
        "artifacts": {
            "cluster_metadata": "legal_distance_modes/cited_decisions_tfidf_outcome_hybrid_0.5/cluster_metadata.json",
            "zoom_mappings": "legal_distance_modes/cited_decisions_tfidf_outcome_hybrid_0.5/zoom_mappings.json",
            "zoom_coherence": "legal_distance_modes/cited_decisions_tfidf_outcome_hybrid_0.5/zoom_coherence.json",
            "decision_clusters": "legal_distance_modes/cited_decisions_tfidf_outcome_hybrid_0.5/decision_clusters.json",
            "integration_summary": "legal_distance_modes/cited_decisions_tfidf_outcome_hybrid_0.5/integration_summary.json",
            "labels_res_0.25": "legal_distance_modes/cited_decisions_tfidf_outcome_hybrid_0.5/labels_res_0.25.npy",
            "labels_res_0.5": "legal_distance_modes/cited_decisions_tfidf_outcome_hybrid_0.5/labels_res_0.5.npy",
            "labels_res_0.75": "legal_distance_modes/cited_decisions_tfidf_outcome_hybrid_0.5/labels_res_0.75.npy",
            "labels_res_1.0": "legal_distance_modes/cited_decisions_tfidf_outcome_hybrid_0.5/labels_res_1.0.npy",
            "labels_res_1.5": "legal_distance_modes/cited_decisions_tfidf_outcome_hybrid_0.5/labels_res_1.5.npy",
            "labels_res_2.0": "legal_distance_modes/cited_decisions_tfidf_outcome_hybrid_0.5/labels_res_2.0.npy",
            "labels_res_3.0": "legal_distance_modes/cited_decisions_tfidf_outcome_hybrid_0.5/labels_res_3.0.npy",
            "labels_hierarchical_best": "legal_distance_modes/cited_decisions_tfidf_outcome_hybrid_0.5/labels_hierarchical_best.npy",
            "labels_coarse_0.5": "legal_distance_modes/cited_decisions_tfidf_outcome_hybrid_0.5/labels_coarse_0.5.npy"
        },
        "metadata": {
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
        "legal_distance_config": {
            "type": "hybrid",
            "config": {"alpha": 0.5, "cited_decisions_weight": 0.5, "outcome_weight": 0.5, "boilerplate_suppression": True}
        },
        "benchmark_results": {
            "hierarchy_coherence": {"status": "PASS", "best_purity": 0.868},
            "adversarial_falsification": {"status": "PASS"},
            "multilingual_invariance": {"status": "PASS", "invariance_gap": 0.4911},
            "jurist_pairwise_preference": {"status": "PASS", "value": 0.7990, "threshold": 0.5},
            "summary": {"total_benchmarks": 14, "passed": 14, "failed": 0, "all_passed": True}
        },
        "warnings": None
    },
    "cited_decisions_tfidf_outcome_hybrid_0.7": {
        "mode_id": "cited_decisions_tfidf_outcome_hybrid_0.7",
        "name": "Cited Decisions TF-IDF + Outcome Hybrid α=0.7 (Best Fractal)",
        "description": "Cited Decisions TF-IDF + Outcome Hybrid α=0.7 - BEST FRACTAL per factory direction v9. ImpRate=90.3%, HierAdv=+0.3703. LangDom=0.4907, JP=0.7907. 2-dim embeddings. PASS both adversarial gates.",
        "mode_type": "legal_distance",
        "status": "available",
        "is_default": False,
        "resolution_ladder": [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0],
        "artifacts": {
            "cluster_metadata": "legal_distance_modes/cited_decisions_tfidf_outcome_hybrid_0.7/cluster_metadata.json",
            "zoom_mappings": "legal_distance_modes/cited_decisions_tfidf_outcome_hybrid_0.7/zoom_mappings.json",
            "zoom_coherence": "legal_distance_modes/cited_decisions_tfidf_outcome_hybrid_0.7/zoom_coherence.json",
            "decision_clusters": "legal_distance_modes/cited_decisions_tfidf_outcome_hybrid_0.7/decision_clusters.json",
            "integration_summary": "legal_distance_modes/cited_decisions_tfidf_outcome_hybrid_0.7/integration_summary.json",
            "labels_res_0.25": "legal_distance_modes/cited_decisions_tfidf_outcome_hybrid_0.7/labels_res_0.25.npy",
            "labels_res_0.5": "legal_distance_modes/cited_decisions_tfidf_outcome_hybrid_0.7/labels_res_0.5.npy",
            "labels_res_0.75": "legal_distance_modes/cited_decisions_tfidf_outcome_hybrid_0.7/labels_res_0.75.npy",
            "labels_res_1.0": "legal_distance_modes/cited_decisions_tfidf_outcome_hybrid_0.7/labels_res_1.0.npy",
            "labels_res_1.5": "legal_distance_modes/cited_decisions_tfidf_outcome_hybrid_0.7/labels_res_1.5.npy",
            "labels_res_2.0": "legal_distance_modes/cited_decisions_tfidf_outcome_hybrid_0.7/labels_res_2.0.npy",
            "labels_res_3.0": "legal_distance_modes/cited_decisions_tfidf_outcome_hybrid_0.7/labels_res_3.0.npy",
            "labels_hierarchical_best": "legal_distance_modes/cited_decisions_tfidf_outcome_hybrid_0.7/labels_hierarchical_best.npy",
            "labels_coarse_0.5": "legal_distance_modes/cited_decisions_tfidf_outcome_hybrid_0.7/labels_coarse_0.5.npy"
        },
        "metadata": {
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
        "legal_distance_config": {
            "type": "hybrid",
            "config": {"alpha": 0.7, "cited_decisions_weight": 0.7, "outcome_weight": 0.3, "boilerplate_suppression": True}
        },
        "benchmark_results": {
            "hierarchy_coherence": {"status": "PASS", "best_purity": 0.903},
            "adversarial_falsification": {"status": "PASS"},
            "multilingual_invariance": {"status": "PASS", "invariance_gap": 0.4907},
            "jurist_pairwise_preference": {"status": "PASS", "value": 0.7907, "threshold": 0.5},
            "summary": {"total_benchmarks": 14, "passed": 14, "failed": 0, "all_passed": True}
        },
        "warnings": None
    },
    "following_alpha0.3": {
        "mode_id": "following_alpha0.3",
        "name": "Citation Role: Following (α=0.3)",
        "description": "Citation Role: Following (α=0.3) - HIGH ADVANTAGE pattern. ImpRate=82.2%, Fine=0.9501. 64-dim embeddings. PASS both adversarial gates. Note: Clustering shows overclustering at high resolutions.",
        "mode_type": "legal_distance",
        "status": "available",
        "is_default": False,
        "resolution_ladder": [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0],
        "artifacts": {
            "cluster_metadata": "legal_distance_modes/following_alpha0.3/cluster_metadata.json",
            "zoom_mappings": "legal_distance_modes/following_alpha0.3/zoom_mappings.json",
            "zoom_coherence": "legal_distance_modes/following_alpha0.3/zoom_coherence.json",
            "decision_clusters": "legal_distance_modes/following_alpha0.3/decision_clusters.json",
            "integration_summary": "legal_distance_modes/following_alpha0.3/integration_summary.json",
            "labels_res_0.25": "legal_distance_modes/following_alpha0.3/labels_res_0.25.npy",
            "labels_res_0.5": "legal_distance_modes/following_alpha0.3/labels_res_0.5.npy",
            "labels_res_0.75": "legal_distance_modes/following_alpha0.3/labels_res_0.75.npy",
            "labels_res_1.0": "legal_distance_modes/following_alpha0.3/labels_res_1.0.npy",
            "labels_res_1.5": "legal_distance_modes/following_alpha0.3/labels_res_1.5.npy",
            "labels_res_2.0": "legal_distance_modes/following_alpha0.3/labels_res_2.0.npy",
            "labels_res_3.0": "legal_distance_modes/following_alpha0.3/labels_res_3.0.npy",
            "labels_hierarchical_best": "legal_distance_modes/following_alpha0.3/labels_hierarchical_best.npy",
            "labels_coarse_0.5": "legal_distance_modes/following_alpha0.3/labels_coarse_0.5.npy"
        },
        "metadata": {
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
        "legal_distance_config": {
            "type": "citation_role",
            "config": {"role": "following", "alpha": 0.3}
        },
        "benchmark_results": {
            "hierarchy_coherence": {"status": "PASS", "best_purity": 0.9501},
            "adversarial_falsification": {"status": "PASS"},
            "multilingual_invariance": {"status": "PASS", "invariance_gap": 0.753},
            "jurist_pairwise_preference": {"status": "PASS", "value": 0.5188, "threshold": 0.5},
            "summary": {"total_benchmarks": 14, "passed": 14, "failed": 0, "all_passed": True}
        },
        "warnings": ["Overclustering at high resolutions (res>=1.5 produces ~986 clusters for 1000 decisions)"]
    },
    "criticizing_alpha0.3": {
        "mode_id": "criticizing_alpha0.3",
        "name": "Citation Role: Criticizing (α=0.3)",
        "description": "Citation Role: Criticizing (α=0.3) - HIGH ADVANTAGE pattern. Fine=0.9619, HierAdv=+0.0815. 64-dim embeddings. PASS both adversarial gates. Note: Clustering shows overclustering at high resolutions.",
        "mode_type": "legal_distance",
        "status": "available",
        "is_default": False,
        "resolution_ladder": [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0],
        "artifacts": {
            "cluster_metadata": "legal_distance_modes/criticizing_alpha0.3/cluster_metadata.json",
            "zoom_mappings": "legal_distance_modes/criticizing_alpha0.3/zoom_mappings.json",
            "zoom_coherence": "legal_distance_modes/criticizing_alpha0.3/zoom_coherence.json",
            "decision_clusters": "legal_distance_modes/criticizing_alpha0.3/decision_clusters.json",
            "integration_summary": "legal_distance_modes/criticizing_alpha0.3/integration_summary.json",
            "labels_res_0.25": "legal_distance_modes/criticizing_alpha0.3/labels_res_0.25.npy",
            "labels_res_0.5": "legal_distance_modes/criticizing_alpha0.3/labels_res_0.5.npy",
            "labels_res_0.75": "legal_distance_modes/criticizing_alpha0.3/labels_res_0.75.npy",
            "labels_res_1.0": "legal_distance_modes/criticizing_alpha0.3/labels_res_1.0.npy",
            "labels_res_1.5": "legal_distance_modes/criticizing_alpha0.3/labels_res_1.5.npy",
            "labels_res_2.0": "legal_distance_modes/criticizing_alpha0.3/labels_res_2.0.npy",
            "labels_res_3.0": "legal_distance_modes/criticizing_alpha0.3/labels_res_3.0.npy",
            "labels_hierarchical_best": "legal_distance_modes/criticizing_alpha0.3/labels_hierarchical_best.npy",
            "labels_coarse_0.5": "legal_distance_modes/criticizing_alpha0.3/labels_coarse_0.5.npy"
        },
        "metadata": {
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
        "legal_distance_config": {
            "type": "citation_role",
            "config": {"role": "criticizing", "alpha": 0.3}
        },
        "benchmark_results": {
            "hierarchy_coherence": {"status": "PASS", "best_purity": 0.9619},
            "adversarial_falsification": {"status": "PASS"},
            "multilingual_invariance": {"status": "PASS", "invariance_gap": 0.7676},
            "jurist_pairwise_preference": {"status": "PASS", "value": 0.5004, "threshold": 0.5},
            "summary": {"total_benchmarks": 14, "passed": 14, "failed": 0, "all_passed": True}
        },
        "warnings": ["Overclustering at high resolutions (res>=1.5 produces ~997 clusters for 1000 decisions)"]
    },
    "citing_alpha0.3": {
        "mode_id": "citing_alpha0.3",
        "name": "Citation Role: Citing (α=0.3)",
        "description": "Citation Role: Citing (α=0.3) - ImpRate=66.9%. 64-dim embeddings. PASS both adversarial gates. Note: Clustering shows overclustering at high resolutions.",
        "mode_type": "legal_distance",
        "status": "available",
        "is_default": False,
        "resolution_ladder": [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0],
        "artifacts": {
            "cluster_metadata": "legal_distance_modes/citing_alpha0.3/cluster_metadata.json",
            "zoom_mappings": "legal_distance_modes/citing_alpha0.3/zoom_mappings.json",
            "zoom_coherence": "legal_distance_modes/citing_alpha0.3/zoom_coherence.json",
            "decision_clusters": "legal_distance_modes/citing_alpha0.3/decision_clusters.json",
            "integration_summary": "legal_distance_modes/citing_alpha0.3/integration_summary.json",
            "labels_res_0.25": "legal_distance_modes/citing_alpha0.3/labels_res_0.25.npy",
            "labels_res_0.5": "legal_distance_modes/citing_alpha0.3/labels_res_0.5.npy",
            "labels_res_0.75": "legal_distance_modes/citing_alpha0.3/labels_res_0.75.npy",
            "labels_res_1.0": "legal_distance_modes/citing_alpha0.3/labels_res_1.0.npy",
            "labels_res_1.5": "legal_distance_modes/citing_alpha0.3/labels_res_1.5.npy",
            "labels_res_2.0": "legal_distance_modes/citing_alpha0.3/labels_res_2.0.npy",
            "labels_res_3.0": "legal_distance_modes/citing_alpha0.3/labels_res_3.0.npy",
            "labels_hierarchical_best": "legal_distance_modes/citing_alpha0.3/labels_hierarchical_best.npy",
            "labels_coarse_0.5": "legal_distance_modes/citing_alpha0.3/labels_coarse_0.5.npy"
        },
        "metadata": {
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
        "legal_distance_config": {
            "type": "citation_role",
            "config": {"role": "citing", "alpha": 0.3}
        },
        "benchmark_results": {
            "hierarchy_coherence": {"status": "PASS", "best_purity": 0.9203},
            "adversarial_falsification": {"status": "PASS"},
            "multilingual_invariance": {"status": "PASS", "invariance_gap": 0.7414},
            "jurist_pairwise_preference": {"status": "PASS", "value": 0.5363, "threshold": 0.5},
            "summary": {"total_benchmarks": 14, "passed": 14, "failed": 0, "all_passed": True}
        },
        "warnings": ["Overclustering at high resolutions (res>=1.5 produces ~928 clusters for 1000 decisions)"]
    },
}

# Add new modes to registry
for mode_id, mode_data in new_modes.items():
    registry["modes"][mode_id] = mode_data

# Update default_mode remains the same
registry["default_mode"] = "center_projected_hierarchical"

# Save updated registry
with open('results/fractal_map/product_integration/map_mode_registry.json', 'w') as f:
    json.dump(registry, f, indent=2)

print(f"Updated registry with {len(new_modes)} new modes")
print(f"Total modes now: {len(registry['modes'])}")
for k in registry['modes'].keys():
    print(f"  {k}")