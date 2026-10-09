#!/usr/bin/env python3
"""
Verification test for evaluation lane state v35 (Factory Direction v35).
Validates that the v35 evaluation state correctly documents:
- TF-IDF 174k baseline mutation (degraded from original freeze)
- Dense embedding complementary view acceptance criteria (defined but BLOCKED at 174k)
- All data blockers requiring corpus lane resumption
"""
import json
from pathlib import Path


def load_json(path):
    with open(path) as f:
        return json.load(f)


def test_v35_state_structure():
    """Verify evaluation.json has correct v35 structure (final completion)."""
    state = load_json("state/evaluation.json")
    
    assert state["lane"] == "evaluation"
    assert state["direction_version"] == 35
    assert state["evidence_tier"] == "TF-IDF_REPRODUCED_DENSE_COMPLEMENTARY_VALIDATED_AT_144K"
    assert state["cycle_status"] == "COMPLETE"
    assert state["continue_recommended"] is False
    assert state["accepted_run_id"] == "evaluation_v35_dense_complementary_validation_20261009_0104"
    
    print("✅ v35 state structure verified!")


def test_tfidf_174k_baseline_mutation_documented():
    """Verify TF-IDF 174k baseline mutation is accurately documented (final state)."""
    state = load_json("state/evaluation.json")
    
    rec = state["next_recommendation"]
    assert "EVALUATION LANE V35 COMPLETE" in rec
    assert "original freeze JP=0.735, 8/8 PASS on 2026-10-01" in rec
    assert "non-deterministic results: 6/8 PASS at JP=0.5565 ↔ 7/8 PASS at JP=0.702" in rec
    assert "Dense complementary view acceptance criteria FROZEN and VALIDATED" in rec
    assert "Citation Heritage AUC 0.792-0.795 > 0.75" in rec
    assert "Cross-Lingual Sachverhalt 0.282 > 0.20" in rec
    assert "Cross-Lingual Dispositiv 0.150 > 0.10" in rec
    assert "Cross-Lingual Erwaegungen 0.094 < 0.10" in rec
    assert "ORIGINAL FREEZE EMBEDDINGS LOST" in state["frozen_baseline"]["known_limitations"][-1]
    
    # Verify frozen_baseline section documents both mutations
    fb = state["frozen_baseline"]
    assert fb["mutation_1_fractal_map_rebuild"]["effect"] == "Degraded production baseline JP from 0.735 to ~0.702 (per pre-refresh verification with OLD metadata)"
    assert fb["mutation_2_accepted_mount_refresh"]["effect"] == "Further degraded production baseline JP from ~0.702 to 0.5565; 6/8 PASS"
    
    # Verify current mount metrics (NEW metadata: 6/8 PASS at JP=0.5565)
    assert fb["adversarial_gates"]["current_mount_reps_pass_both"] == 6
    assert fb["adversarial_gates"]["current_mount_reps_tested"] == 8
    
    print("✅ TF-IDF 174k baseline mutation accurately documented!")


def test_dense_embedding_acceptance_criteria():
    """Verify dense embedding complementary view acceptance criteria are defined."""
    state = load_json("state/evaluation.json")
    
    criteria = state["dense_complementary_acceptance_criteria"]
    
    # Citation Heritage View
    ch = criteria["citation_heritage_view"]
    assert ch["acceptance_criterion"] == "AUC > 0.75"
    assert ch["best_dense_mode"] == "center_projected_64dim"
    assert ch["evidence_at_144k_22yr_cohort"]["center_projected_64dim_auc"] == 0.7922
    assert ch["evidence_at_full_174k"]["status"] == "FAIL at full 174k — VALIDATION BLOCKED per prior audit CYCLE_37591874490"
    assert ch["blocker"] == "Corpus lane: BGE/bger ID mapping + parquet 2022-2026"
    
    # Cross-Lingual Sachverhalt View
    cls = criteria["cross_lingual_sachverhalt_view"]
    assert cls["acceptance_criterion"] == "cross_lang_same_branch > 0.20"
    assert cls["evidence_at_144k_22yr"]["cross_lang_same_branch"] == 0.2816
    assert cls["full_corpus_status"] == "BLOCKED pending section extraction at 174k"
    
    # Cross-Lingual Dispositiv View
    cld = criteria["cross_lingual_dispositiv_view"]
    assert cld["acceptance_criterion"] == "cross_lang_same_branch > 0.10"
    assert cld["evidence_at_144k_22yr"]["cross_lang_same_branch"] == 0.1502
    
    # Cross-Lingual Erwaegungen View - REJECTED
    cle = criteria["cross_lingual_erwaegungen_view"]
    assert cle["evidence_at_144k_22yr"]["status"] == "FAILED at 144k partial cohort (22yr, 2000-2021)"
    assert cle["product_integration"] == "NOT INCLUDED — does not meet acceptance criterion"
    
    # Linear Hybrid Complement View
    lhc = criteria["linear_hybrid_complement_view"]
    assert "PASS both adversarial gates AND cross_lang_same_branch > TF-IDF baseline" in lhc["acceptance_criterion"]
    assert "PASS adversarial gates on obsolete v6-v10 era embeddings" in lhc["evidence_at_22yr_144k"]["status"]
    assert "target 174k legal-distance dense embeddings do not exist" in lhc["evidence_at_22yr_144k"]["status"]
    assert "validation BLOCKED" in lhc["evidence_at_22yr_144k"]["status"]
    
    print("✅ Dense embedding acceptance criteria verified!")


def test_fundamental_tradeoff():
    """Verify fundamental tradeoff is documented."""
    state = load_json("state/evaluation.json")
    
    ft = state["fundamental_tradeoff"]
    assert ft["reproduced_at_all_scales"] is True
    assert "3yr" in ft["scales_tested"]
    assert "22yr" in ft["scales_tested"]
    assert ft["conclusion"] == "NO single representation dominates all three metrics at any scale"
    
    # Verify TF-IDF = PRIMARY, Dense = COMPLEMENTARY
    assert ft["metrics"]["tfidf_citation_hybrids"]["jurist_preference"] == 0.78
    assert ft["metrics"]["dense_semantic"]["jurist_preference"] == "0.05-0.43"
    
    print("✅ Fundamental tradeoff verified!")


def test_true_oos_ceiling():
    """Verify true OOS jurist preference ceiling is documented."""
    state = load_json("state/evaluation.json")
    
    oos = state["true_oos_ceiling"]
    assert oos["jurist_pref_ceiling"] == 0.53
    assert oos["factory_target"] == 0.7
    assert oos["achievable"] is False
    assert oos["source"] == "v8 holdout zero-shot validation"
    
    print("✅ True OOS ceiling verified!")


def test_data_blockers_documented():
    """Verify data blockers for 174k dense deployment are documented."""
    state = load_json("state/evaluation.json")
    
    blockers = state["data_blockers"]
    assert blockers["bge_bger_id_mapping"] == "Canonical corpus uses bge_ IDs, evaluation uses bger_ IDs — no mapping exists"
    assert "29,520 decisions missing" in blockers["parquet_2022_2026"]
    assert "Sachverhalt/Erwaegungen/Dispositiv not extracted at 174k scale" in blockers["section_extraction_174k"]
    assert "No BGE/multilingual-e5 finetuning at scale" in blockers["gpu_unavailable"]
    
    print("✅ Data blockers documented!")


def test_external_dependencies():
    """Verify external dependencies are documented."""
    state = load_json("state/evaluation.json")
    
    deps = state["external_dependencies"]
    assert deps["jurist_human_study"]["status"] == "FRAMEWORK_READY"
    assert "5-10 Swiss jurists" in deps["jurist_human_study"]["description"]
    
    print("✅ External dependencies documented!")


def test_audit_corrections_applied():
    """Verify audit corrections from CYCLE_37696016446 are applied (with subsequent verification correction)."""
    state = load_json("state/evaluation.json")
    
    corrections = state["audit_corrections_applied"]
    assert corrections["cycle_revised"] == "CYCLE_37696016446"
    fixes = corrections["fixes_applied"]
    assert len(fixes) == 5
    assert "Citation Heritage: Distinguished 144k partial cohort" in fixes[0]
    assert "Cross-Lingual Sachverhalt/Dispositiv/Erwaegungen" in fixes[1]
    assert "Linear Hybrid: Replaced" in fixes[2]
    assert "Product Audit Gate: Removed broken reference" in fixes[3]
    assert "Evaluation Framework: Clarified" in fixes[4]
    
    # Verify stability confirmation (CORRECTED by 2026-10-08T23:44 verification showing non-determinism)
    sc = corrections["stability_confirmation_20261008_CORRECTED"]
    assert sc["result"] == "6/8 TF-IDF representations PASS both adversarial gates on accepted mount with NEW metadata"
    assert "CRITICAL CORRECTION" in sc["note"]
    assert "Metadata file was updated at 2026-10-08T23:40" in sc["note"]
    assert "Results are NOT deterministic across metadata orderings" in sc["note"]
    assert "Original freeze (2026-10-01, JP=0.735, 8/8 PASS) is LOST" in sc["note"]
    
    # Verify latest verification confirms non-determinism
    lv = corrections["latest_verification_20261009_0354"]
    assert lv["reps_pass_both"] == 7
    assert lv["reps_tested"] == 8
    assert "CONFIRMS NON-DETERMINISM" in lv["note"]
    
    print("✅ Audit corrections verified!")


def test_evidence_refs():
    """Verify evidence_refs point to correct artifacts."""
    state = load_json("state/evaluation.json")
    
    refs = state["evidence_refs"]
    assert len(refs) == 6
    assert "legal-distance/evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json" in refs
    assert "legal-distance/results/legal_distance/complementary_role_characterization_v34.json" in refs
    assert "legal-distance/results/legal_distance/dense_complementary_characterization/scale_characterization_results.json" in refs
    assert "legal-distance/legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_22year_latest.json" in refs
    assert "fractal-map/results/fractal_map/dense_embeddings_integration_contract_v34.json" in refs
    assert "fractal-map/results/fractal_map/144k_checkpoint_validation/144k_validation_144443decisions.json" in refs
    
    print("✅ Evidence references verified!")


def test_accepted_run_id_format():
    """Verify accepted_run_id follows the v35 naming convention (final completion)."""
    state = load_json("state/evaluation.json")
    
    run_id = state["accepted_run_id"]
    assert run_id.startswith("evaluation_v35_")
    assert "dense_complementary_validation" in run_id
    assert "20261009" in run_id
    
    print("✅ Accepted run ID format verified!")


if __name__ == "__main__":
    print("=" * 60)
    print("VERIFICATION TEST: Evaluation Lane State v35")
    print("Factory Direction: v35")
    print("=" * 60)
    
    test_v35_state_structure()
    test_tfidf_174k_baseline_mutation_documented()
    test_dense_embedding_acceptance_criteria()
    test_fundamental_tradeoff()
    test_true_oos_ceiling()
    test_data_blockers_documented()
    test_external_dependencies()
    test_audit_corrections_applied()
    test_evidence_refs()
    test_accepted_run_id_format()
    
    print("\n" + "=" * 60)
    print("ALL V35 VERIFICATION TESTS PASSED ✅")
    print("=" * 60)