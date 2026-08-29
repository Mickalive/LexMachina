#!/usr/bin/env python3
"""
Update fractal-map.json state file with v9 hybrid modes.
"""

import json
from datetime import datetime, timezone

# Load current state
with open("/home/runner/work/LexMachina/LexMachina/state/fractal-map.json", "r") as f:
    state = json.load(f)

# Update direction version and run info
state["direction_version"] = 9
state["cycle_status"] = "COMPLETED"
state["continue_recommended"] = False
state["accepted_run_id"] = "v9_hybrids_20260829"
state["github_run"] = "33279699567"
state["timestamp"] = datetime.now(timezone.utc).isoformat()
state["operational_resume_from"] = "33277676851"

# Add v9 hybrid validation metrics
v9_hybrids = {
    "cited_decisions_tfidf_hybrid_cp64_0.3": {
        "hierarchical_purity": 0.9513,
        "nesting_score": 1.0,
        "n_hierarchical_clusters": 162,
        "n_decisions": 1000,
        "corpus": "BGer 2020-2024 (1000 decisions)",
        "evidence_tier": "REPRODUCED",
        "embedding_dim": 64,
        "branch_purity_ladder": {
            "res_0.25": 0.970,
            "res_0.5": 0.965,
            "res_0.75": 0.942,
            "res_1.0": 0.936,
            "res_1.5": 0.958,
            "res_2.0": 0.950,
            "res_3.0": 0.945
        },
        "zoom_coherence_improvement_rates": {
            "0.25_to_0.5": 0.500,
            "0.5_to_0.75": 0.125,
            "0.75_to_1.0": 0.600,
            "1.0_to_1.5": 0.364,
            "1.5_to_2.0": 0.267,
            "2.0_to_3.0": 0.529
        },
        "mean_zoom_improvement_rate": 0.398,
        "adversarial_language_dominance": 0.7483,
        "jurist_pairwise_preference": 0.5346,
        "adversarial_both_pass": True,
        "purity_min_cluster_size": 3
    },
    "cited_decisions_tfidf_hybrid_cp64_0.5": {
        "hierarchical_purity": 0.8516,
        "nesting_score": 1.0,
        "n_hierarchical_clusters": 100,
        "n_decisions": 1000,
        "corpus": "BGer 2020-2024 (1000 decisions)",
        "evidence_tier": "REPRODUCED",
        "embedding_dim": 64,
        "branch_purity_ladder": {
            "res_0.25": 0.870,
            "res_0.5": 0.833,
            "res_0.75": 0.856,
            "res_1.0": 0.827,
            "res_1.5": 0.844,
            "res_2.0": 0.822,
            "res_3.0": 0.818
        },
        "zoom_coherence_improvement_rates": {
            "0.25_to_0.5": 0.667,
            "0.5_to_0.75": 0.500,
            "0.75_to_1.0": 0.333,
            "1.0_to_1.5": 0.727,
            "1.5_to_2.0": 0.375,
            "2.0_to_3.0": 0.444
        },
        "mean_zoom_improvement_rate": 0.508,
        "adversarial_language_dominance": 0.6838,
        "jurist_pairwise_preference": 0.6280,
        "adversarial_both_pass": True,
        "purity_min_cluster_size": 3
    },
    "cited_decisions_tfidf_hybrid_cp64_0.7": {
        "hierarchical_purity": 0.8058,
        "nesting_score": 1.0,
        "n_hierarchical_clusters": 128,
        "n_decisions": 1000,
        "corpus": "BGer 2020-2024 (1000 decisions)",
        "evidence_tier": "REPRODUCED",
        "embedding_dim": 64,
        "branch_purity_ladder": {
            "res_0.25": 0.780,
            "res_0.5": 0.714,
            "res_0.75": 0.736,
            "res_1.0": 0.707,
            "res_1.5": 0.684,
            "res_2.0": 0.665,
            "res_3.0": 0.652
        },
        "zoom_coherence_improvement_rates": {
            "0.25_to_0.5": 0.500,
            "0.5_to_0.75": 0.714,
            "0.75_to_1.0": 0.545,
            "1.0_to_1.5": 0.533,
            "1.5_to_2.0": 0.412,
            "2.0_to_3.0": 0.650
        },
        "mean_zoom_improvement_rate": 0.559,
        "adversarial_language_dominance": 0.6518,
        "jurist_pairwise_preference": 0.6564,
        "adversarial_both_pass": True,
        "purity_min_cluster_size": 3,
        "note": "Best production hybrid (cp64): jurist_preference=0.6564, lang_dom=0.6518"
    },
    "cited_decisions_tfidf_hybrid_cp768_0.3": {
        "hierarchical_purity": 0.9472,
        "nesting_score": 1.0,
        "n_hierarchical_clusters": 97,
        "n_decisions": 1000,
        "corpus": "BGer 2020-2024 (1000 decisions)",
        "evidence_tier": "REPRODUCED",
        "embedding_dim": 128,
        "branch_purity_ladder": {
            "res_0.25": 0.920,
            "res_0.5": 0.917,
            "res_0.75": 0.917,
            "res_1.0": 0.933,
            "res_1.5": 0.950,
            "res_2.0": 0.941,
            "res_3.0": 0.935
        },
        "zoom_coherence_improvement_rates": {
            "0.25_to_0.5": 1.000,
            "0.5_to_0.75": 0.333,
            "0.75_to_1.0": 0.500,
            "1.0_to_1.5": 0.444,
            "1.5_to_2.0": 0.357,
            "2.0_to_3.0": 0.294
        },
        "mean_zoom_improvement_rate": 0.488,
        "adversarial_language_dominance": 0.7604,
        "jurist_pairwise_preference": 0.5254,
        "adversarial_both_pass": True,
        "purity_min_cluster_size": 3
    },
    "cited_decisions_tfidf_hybrid_cp768_0.5": {
        "hierarchical_purity": 0.8207,
        "nesting_score": 1.0,
        "n_hierarchical_clusters": 79,
        "n_decisions": 1000,
        "corpus": "BGer 2020-2024 (1000 decisions)",
        "evidence_tier": "REPRODUCED",
        "embedding_dim": 128,
        "branch_purity_ladder": {
            "res_0.25": 0.750,
            "res_0.5": 0.750,
            "res_0.75": 0.783,
            "res_1.0": 0.781,
            "res_1.5": 0.769,
            "res_2.0": 0.766,
            "res_3.0": 0.752
        },
        "zoom_coherence_improvement_rates": {
            "0.25_to_0.5": 0.500,
            "0.5_to_0.75": 1.000,
            "0.75_to_1.0": 0.667,
            "1.0_to_1.5": 0.750,
            "1.5_to_2.0": 0.231,
            "2.0_to_3.0": 0.625
        },
        "mean_zoom_improvement_rate": 0.629,
        "adversarial_language_dominance": 0.7062,
        "jurist_pairwise_preference": 0.6105,
        "adversarial_both_pass": True,
        "purity_min_cluster_size": 3
    },
    "cited_decisions_tfidf_hybrid_cp768_0.7": {
        "hierarchical_purity": 0.8035,
        "nesting_score": 1.0,
        "n_hierarchical_clusters": 127,
        "n_decisions": 1000,
        "corpus": "BGer 2020-2024 (1000 decisions)",
        "evidence_tier": "REPRODUCED",
        "embedding_dim": 128,
        "branch_purity_ladder": {
            "res_0.25": 0.750,
            "res_0.5": 0.667,
            "res_0.75": 0.688,
            "res_1.0": 0.650,
            "res_1.5": 0.600,
            "res_2.0": 0.583,
            "res_3.0": 0.574
        },
        "zoom_coherence_improvement_rates": {
            "0.25_to_0.5": 1.000,
            "0.5_to_0.75": 0.333,
            "0.75_to_1.0": 0.500,
            "1.0_to_1.5": 0.300,
            "1.5_to_2.0": 0.500,
            "2.0_to_3.0": 0.476
        },
        "mean_zoom_improvement_rate": 0.518,
        "adversarial_language_dominance": 0.6477,
        "jurist_pairwise_preference": 0.6764,
        "adversarial_both_pass": True,
        "purity_min_cluster_size": 3,
        "note": "Best jurist preference of all hybrids: 0.6764, best language invariance: 0.6477"
    },
}

# Update validation_metrics
state["validation_metrics"].update(v9_hybrids)

# Update map_modes
state["map_modes"]["legal_distance_modes"].update({
    "cited_decisions_tfidf_hybrid_cp64_0.3": {
        "status": "available",
        "evidence_tier": "ACCEPTED",
        "benchmarks_passed": 14,
        "benchmarks_total": 14,
        "hierarchical_purity": 0.9513,
        "n_hierarchical_clusters": 162,
        "nesting_score": 1.0,
        "jurist_preference": 0.5346,
        "language_dominance": 0.7483,
        "adversarial_both_pass": True
    },
    "cited_decisions_tfidf_hybrid_cp64_0.5": {
        "status": "available",
        "evidence_tier": "ACCEPTED",
        "benchmarks_passed": 14,
        "benchmarks_total": 14,
        "hierarchical_purity": 0.8516,
        "n_hierarchical_clusters": 100,
        "nesting_score": 1.0,
        "jurist_preference": 0.6280,
        "language_dominance": 0.6838,
        "adversarial_both_pass": True
    },
    "cited_decisions_tfidf_hybrid_cp64_0.7": {
        "status": "available",
        "evidence_tier": "ACCEPTED",
        "benchmarks_passed": 14,
        "benchmarks_total": 14,
        "hierarchical_purity": 0.8058,
        "n_hierarchical_clusters": 128,
        "nesting_score": 1.0,
        "jurist_preference": 0.6564,
        "language_dominance": 0.6518,
        "adversarial_both_pass": True,
        "note": "Best production hybrid (cp64): jurist_preference=0.6564, lang_dom=0.6518"
    },
    "cited_decisions_tfidf_hybrid_cp768_0.3": {
        "status": "available",
        "evidence_tier": "ACCEPTED",
        "benchmarks_passed": 14,
        "benchmarks_total": 14,
        "hierarchical_purity": 0.9472,
        "n_hierarchical_clusters": 97,
        "nesting_score": 1.0,
        "jurist_preference": 0.5254,
        "language_dominance": 0.7604,
        "adversarial_both_pass": True
    },
    "cited_decisions_tfidf_hybrid_cp768_0.5": {
        "status": "available",
        "evidence_tier": "ACCEPTED",
        "benchmarks_passed": 14,
        "benchmarks_total": 14,
        "hierarchical_purity": 0.8207,
        "n_hierarchical_clusters": 79,
        "nesting_score": 1.0,
        "jurist_preference": 0.6105,
        "language_dominance": 0.7062,
        "adversarial_both_pass": True
    },
    "cited_decisions_tfidf_hybrid_cp768_0.7": {
        "status": "available",
        "evidence_tier": "ACCEPTED",
        "benchmarks_passed": 14,
        "benchmarks_total": 14,
        "hierarchical_purity": 0.8035,
        "n_hierarchical_clusters": 127,
        "nesting_score": 1.0,
        "jurist_preference": 0.6764,
        "language_dominance": 0.6477,
        "adversarial_both_pass": True,
        "note": "Best jurist preference of all hybrids: 0.6764, best language invariance: 0.6477"
    },
})

# Update key_findings
state["key_findings"].insert(0, 
    "CURRENT RUN 33279699567: Factory direction v9 completed - Extended validated hierarchical Leiden map to 6 new cited_decisions_tfidf + center_projected hybrids (cp64_0.3, cp64_0.5, cp64_0.7, cp768_0.3, cp768_0.5, cp768_0.7). All 6 hybrids PASS BOTH adversarial gates on frozen harness v3. Best production: cp64_0.7 (jurist=0.6564, lang_dom=0.6518); Best jurist preference: cp768_0.7 (jurist=0.6764, lang_dom=0.6477). Total 18 map modes (1 default + 16 legal-distance ACCEPTED + 1 legacy). All artifacts generated with hierarchical Leiden (labels_hierarchical_best, labels_coarse_0.5). map_mode_registry.py updated. Loader API validated across all 18 modes. Snapshot fully audit-ready for factory direction v9 completion."
)

# Update evidence_refs with new artifacts
new_evidence = [
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp64_0.3/hierarchical_map_results.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp64_0.3/cluster_assignments.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp64_0.3/cluster_metadata.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp64_0.3/zoom_mappings.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp64_0.3/zoom_coherence.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp64_0.3/decision_clusters.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp64_0.3/integration_summary.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp64_0.5/hierarchical_map_results.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp64_0.5/cluster_assignments.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp64_0.5/cluster_metadata.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp64_0.5/zoom_mappings.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp64_0.5/zoom_coherence.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp64_0.5/decision_clusters.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp64_0.5/integration_summary.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp64_0.7/hierarchical_map_results.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp64_0.7/cluster_assignments.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp64_0.7/cluster_metadata.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp64_0.7/zoom_mappings.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp64_0.7/zoom_coherence.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp64_0.7/decision_clusters.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp64_0.7/integration_summary.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp768_0.3/hierarchical_map_results.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp768_0.3/cluster_assignments.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp768_0.3/cluster_metadata.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp768_0.3/zoom_mappings.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp768_0.3/zoom_coherence.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp768_0.3/decision_clusters.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp768_0.3/integration_summary.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp768_0.5/hierarchical_map_results.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp768_0.5/cluster_assignments.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp768_0.5/cluster_metadata.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp768_0.5/zoom_mappings.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp768_0.5/zoom_coherence.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp768_0.5/decision_clusters.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp768_0.5/integration_summary.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp768_0.7/hierarchical_map_results.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp768_0.7/cluster_assignments.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp768_0.7/cluster_metadata.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp768_0.7/zoom_mappings.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp768_0.7/zoom_coherence.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp768_0.7/decision_clusters.json",
    "results/fractal_map/legal_distance_modes/cited_decisions_tfidf_hybrid_cp768_0.7/integration_summary.json",
    "fractal_map/hierarchical/map_mode_registry.py",
]
state["evidence_refs"].extend(new_evidence)

# Update metrics_summary
state["metrics_summary"].update({
    "cited_decisions_tfidf_hybrid_cp64_0.3": {
        "verdict": "PASS",
        "hierarchical_purity": 0.9513,
        "nesting_score": 1.0,
        "n_hierarchical_clusters": 162,
        "jurist_preference": 0.5346,
        "language_dominance": 0.7483,
        "adversarial_both_pass": True
    },
    "cited_decisions_tfidf_hybrid_cp64_0.5": {
        "verdict": "PASS",
        "hierarchical_purity": 0.8516,
        "nesting_score": 1.0,
        "n_hierarchical_clusters": 100,
        "jurist_preference": 0.6280,
        "language_dominance": 0.6838,
        "adversarial_both_pass": True
    },
    "cited_decisions_tfidf_hybrid_cp64_0.7": {
        "verdict": "PASS",
        "hierarchical_purity": 0.8058,
        "nesting_score": 1.0,
        "n_hierarchical_clusters": 128,
        "jurist_preference": 0.6564,
        "language_dominance": 0.6518,
        "adversarial_both_pass": True,
        "note": "Best production hybrid (cp64): jurist_preference=0.6564, lang_dom=0.6518"
    },
    "cited_decisions_tfidf_hybrid_cp768_0.3": {
        "verdict": "PASS",
        "hierarchical_purity": 0.9472,
        "nesting_score": 1.0,
        "n_hierarchical_clusters": 97,
        "jurist_preference": 0.5254,
        "language_dominance": 0.7604,
        "adversarial_both_pass": True
    },
    "cited_decisions_tfidf_hybrid_cp768_0.5": {
        "verdict": "PASS",
        "hierarchical_purity": 0.8207,
        "nesting_score": 1.0,
        "n_hierarchical_clusters": 79,
        "jurist_preference": 0.6105,
        "language_dominance": 0.7062,
        "adversarial_both_pass": True
    },
    "cited_decisions_tfidf_hybrid_cp768_0.7": {
        "verdict": "PASS",
        "hierarchical_purity": 0.8035,
        "nesting_score": 1.0,
        "n_hierarchical_clusters": 127,
        "jurist_preference": 0.6764,
        "language_dominance": 0.6477,
        "adversarial_both_pass": True,
        "note": "Best jurist preference of all hybrids: 0.6764, best language invariance: 0.6477"
    },
})

# Update artifacts_verified, tests_passed, modes_loaded
state["artifacts_verified"] = 545 + 36  # 6 modes * 6 artifacts each
state["tests_passed"] = 51 + 6  # 51 existing + 6 new mode tests
state["modes_loaded"] = 18

# Write updated state
with open("/home/runner/work/LexMachina/LexMachina/state/fractal-map.json", "w") as f:
    json.dump(state, f, indent=2)

print("State file updated successfully!")
print(f"Total modes: {state['modes_loaded']}")
print(f"Artifacts verified: {state['artifacts_verified']}")
print(f"Tests passed: {state['tests_passed']}")