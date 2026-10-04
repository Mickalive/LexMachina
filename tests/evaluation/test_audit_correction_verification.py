#!/usr/bin/env python3
"""
Verification test for evaluation lane state v34 (Factory Direction v34).
Validates that the v34 evaluation state correctly freezes TF-IDF 174k as production baseline
and defines dense embedding complementary view acceptance criteria.
"""
import json
from pathlib import Path


def load_json(path):
    with open(path) as f:
        return json.load(f)


def test_v34_state_structure():
    """Verify evaluation.json has correct v34 structure."""
    state = load_json("evaluation/state/evaluation.json")
    
    assert state["lane"] == "evaluation"
    assert state["direction_version"] == 34
    assert state["evidence_tier"] == "ACCEPTED"
    assert state["cycle_status"] == "COMPLETE"
    assert state["continue_recommended"] is False
    assert state["accepted_run_id"] == "eval_174k_v34_baseline_and_dense_criteria_20261003"
    
    print("✅ v34 state structure verified!")


def test_tfidf_174k_baseline_frozen():
    """Verify TF-IDF 174k baseline is frozen with correct adversarial results."""
    state = load_json("evaluation/state/evaluation.json")
    
    tfidf = state["summary"]["tfidf_family_174k"]
    assert tfidf["status"] == "COMPLETE"
    assert tfidf["representations_evaluated"] == 8
    
    # All 8 should PASS adversarial
    for rep, results in tfidf["adversarial_results"].items():
        assert results["verdict"] == "PASS", f"{rep} should PASS adversarial"
        assert results["language_dominance"] < 0.85, f"{rep} LangDom {results['language_dominance']} >= 0.85"
        assert results["jurist_preference"] > 0.5, f"{rep} JP {results['jurist_preference']} <= 0.5"
    
    # Production default
    prod = tfidf["adversarial_results"]["cited_decisions_tfidf_outcome_hybrid_0.5"]
    assert prod["language_dominance"] == 0.4895
    assert prod["jurist_preference"] == 0.7265
    
    print("✅ TF-IDF 174k baseline frozen and verified!")


def test_dense_embedding_acceptance_criteria():
    """Verify dense embedding complementary view acceptance criteria are defined and validated."""
    state = load_json("evaluation/state/evaluation.json")
    
    criteria = state["dense_embedding_acceptance_criteria"]
    
    # Citation heritage AUC > 0.75
    ch = criteria["citation_heritage_auc"]
    assert ch["threshold"] == 0.75
    assert ch["status"] == "PASS"
    assert ch["evidence_22year"]["center_projected_768dim"] >= 0.75
    assert ch["evidence_22year"]["center_projected_64dim"] >= 0.75
    assert ch["evidence_22year"]["center_projected_128dim"] >= 0.75
    
    # Cross-lingual sachverhalt > 0.2
    cls = criteria["cross_lang_same_branch_sachverhalt"]
    assert cls["threshold"] == 0.2
    assert cls["status"] == "PASS"
    assert cls["evidence_22year"]["center_projected_768dim"] >= 0.2
    assert cls["evidence_22year"]["center_projected_64dim"] >= 0.2
    
    # Cross-lingual dispositiv > 0.1
    cld = criteria["cross_lang_same_branch_dispositiv"]
    assert cld["threshold"] == 0.1
    assert cld["status"] == "PASS"
    assert cld["evidence_22year"]["center_projected_768dim"] >= 0.1
    assert cld["evidence_22year"]["center_projected_64dim"] >= 0.1
    
    # Cross-lingual erwaegungen > 0.1 (should FAIL)
    cle = criteria["cross_lang_same_branch_erwaegungen"]
    assert cle["threshold"] == 0.1
    assert cle["status"] == "FAIL"
    assert cle["evidence_22year"]["center_projected_768dim"] < 0.1
    assert cle["evidence_22year"]["center_projected_64dim"] < 0.1
    
    # Jurist preference (should FAIL for center_projected)
    jp = criteria["jurist_pairwise_preference"]
    assert jp["threshold"] == 0.5
    assert jp["status"] == "FAIL"
    assert all(v < 0.5 for v in jp["evidence_165k"].values())
    
    print("✅ Dense embedding acceptance criteria verified!")


def test_citation_heritage_174k_tfidf():
    """Verify citation heritage at 174k for TF-IDF is correctly recorded in state."""
    state = load_json("evaluation/state/evaluation.json")
    
    ch = state["summary"]["citation_heritage_174k_tfidf"]
    assert ch["status"] == "COMPLETE"
    # State records 4 passing at threshold 0.65 (per accepted run)
    assert ch["passing_representations"] == 4
    assert ch["failing_representations"] == 4
    assert ch["threshold_auc"] == 0.65
    assert ch["best"] == "cited_decisions_tfidf (AUC=0.743)"
    
    # Verify state internal consistency: passing + failing = 8
    assert ch["passing_representations"] + ch["failing_representations"] == 8
    
    print("✅ Citation heritage 174k TF-IDF state verified!")


def test_v17b_label_normalization_174k():
    """Verify v17b label normalization at 174k shows regime difference (no false generalization)."""
    state = load_json("evaluation/state/evaluation.json")
    
    v17b = state["summary"]["v17b_label_normalization_174k_tfidf"]
    assert v17b["status"] == "COMPLETE"
    assert v17b["uniform_improvement_or_matching"] is False
    assert v17b["worsened_gt10pct"] == 4
    assert "does NOT uniformly improve" in v17b["conclusion"]
    assert "different regime from 1K scale" in v17b["conclusion"]
    assert "213->111 vs 104->54" in v17b["conclusion"]
    
    # Verify mapping coverage info
    mapping = state["summary"]["v17b_normalization_mapping_coverage"]
    assert mapping["raw_labels_in_corpus"] == 214
    assert mapping["canonical_concepts_after_normalization"] == 164
    assert mapping["cross_lingual_map_entries"] == 91
    assert mapping["coverage_fraction"] == "91/214 = 42.5% of raw labels explicitly mapped"
    
    print("✅ v17b label normalization regime difference verified!")


def test_v18_coarse_hierarchy_negative():
    """Verify v18 coarse hierarchy result is negative (fundamental limitation)."""
    state = load_json("evaluation/state/evaluation.json")
    
    v18 = state["summary"]["v18_coarse_hierarchy"]
    assert v18["status"] == "COMPLETE"
    assert v18["result"] == "FAIL"
    assert v18["best_branch_purity"] == 0.6497
    assert v18["best_representation"] == "linear_citation_concat"
    assert v18["center_projected_64dim_purity"] == 0.5188
    assert v18["best_branch_purity"] < 0.7
    assert "Fundamental hierarchy limitation confirmed" in v18["conclusion"]
    
    print("✅ v18 coarse hierarchy negative result verified!")


def test_critical_findings():
    """Verify critical_findings section captures key conclusions."""
    state = load_json("evaluation/state/evaluation.json")
    
    cf = state["critical_findings"]
    
    # TF-IDF baseline frozen
    assert "tfidf_174k_production_baseline_frozen" in cf
    assert "All 8 TF-IDF representations evaluated" in cf["tfidf_174k_production_baseline_frozen"]
    assert "cited_decisions_tfidf_outcome_hybrid_0.5" in cf["tfidf_174k_production_baseline_frozen"]
    
    # Dense embedding criteria validation
    assert "dense_embedding_acceptance_criteria_validation" in cf
    assert "PASS > 0.75 threshold" in cf["dense_embedding_acceptance_criteria_validation"]
    assert "Sachverhalt > Dispositiv > Erwaegungen hierarchy" in cf["dense_embedding_acceptance_criteria_validation"]
    assert "COMPLEMENTARY VIEWS ONLY" in cf["dense_embedding_acceptance_criteria_validation"]
    
    # v17b regime difference (case insensitive check)
    assert "v17b_label_normalization_174k" in cf
    v17b_text = cf["v17b_label_normalization_174k"]
    assert "does NOT generalize" in v17b_text or "Does NOT generalize" in v17b_text
    
    # v18 negative
    assert "v18_coarse_hierarchy_negative" in cf
    assert "best purity 0.65" in cf["v18_coarse_hierarchy_negative"]
    assert "< 0.7 threshold" in cf["v18_coarse_hierarchy_negative"]
    
    print("✅ Critical findings verified!")


def test_next_recommendation():
    """Verify next_recommendation reflects v34 completion."""
    state = load_json("evaluation/state/evaluation.json")
    
    rec = state["next_recommendation"]
    assert "TF-IDF 174k evaluation FROZEN as production baseline" in rec
    assert "Dense embedding complementary view acceptance criteria DEFINED and VALIDATED" in rec
    assert "blocked on bge_/bger_ ID mapping" in rec
    assert "No additional same-question cycle justified" in rec
    assert "eval_174k_v34_baseline_and_dense_criteria_report.md" in rec
    
    print("✅ Next recommendation verified!")


def test_evidence_refs():
    """Verify evidence_refs point to correct artifacts."""
    state = load_json("evaluation/state/evaluation.json")
    
    refs = state["evidence_refs"]
    assert len(refs) == 9
    assert "results/evaluation/v25_174k_formal_suite/results/_suite_summary.json" in refs
    assert "results/evaluation/citation_heritage_174k_tfidf_latest.json" in refs
    assert "evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json" in refs
    assert "results/evaluation/v18_coarse_hierarchy/v18_coarse_hierarchy_latest.json" in refs
    assert "results/evaluation/partial_dense_2000_2002/citation_heritage_22year_latest.json" in refs
    assert "results/evaluation/partial_dense_2000_2002/section_crosslingual_eval_latest.json" in refs
    assert "results/evaluation/adversarial_reverify_20261002/exact_adversarial_all_tfidf.json" in refs
    assert "reports/evaluation/eval_174k_v34_baseline_and_dense_criteria_report.md" in refs
    assert "reports/evaluation/evaluation_v34_final_cycle_verification_20261004.md" in refs
    
    print("✅ Evidence references verified!")


if __name__ == "__main__":
    print("=" * 60)
    print("VERIFICATION TEST: Evaluation Lane State v34")
    print("Factory Direction: v34")
    print("=" * 60)
    
    test_v34_state_structure()
    test_tfidf_174k_baseline_frozen()
    test_dense_embedding_acceptance_criteria()
    test_citation_heritage_174k_tfidf()
    test_v17b_label_normalization_174k()
    test_v18_coarse_hierarchy_negative()
    test_critical_findings()
    test_next_recommendation()
    test_evidence_refs()
    
    print("\n" + "=" * 60)
    print("ALL V34 VERIFICATION TESTS PASSED ✅")
    print("=" * 60)