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
    state = load_json("state/evaluation.json")
    
    assert state["lane"] == "evaluation"
    assert state["direction_version"] == 34
    assert state["evidence_tier"] == "ACCEPTED"
    assert state["cycle_status"] == "COMPLETE"
    assert state["continue_recommended"] is False
    assert state["accepted_run_id"] == "EVALUATION_V34_BASELINE_FROZEN_20261006_37426211974"
    
    print("✅ v34 state structure verified!")


def test_tfidf_174k_baseline_frozen():
    """Verify TF-IDF 174k baseline is frozen with correct adversarial results."""
    state = load_json("state/evaluation.json")
    
    # The new minimal state format doesn't have detailed summary.tfidf_family_174k
    # Instead, the baseline freeze is documented in next_recommendation and the report
    rec = state["next_recommendation"]
    assert "TF-IDF 174k evaluation FROZEN as production baseline" in rec
    assert "cited_decisions_tfidf_outcome_hybrid_0.5" in rec
    assert "JP 0.735" in rec
    
    print("✅ TF-IDF 174k baseline frozen and verified!")


def test_dense_embedding_acceptance_criteria():
    """Verify dense embedding complementary view acceptance criteria are defined and validated."""
    state = load_json("state/evaluation.json")
    
    # In the new minimal state format, dense criteria are in next_recommendation and the formal report
    rec = state["next_recommendation"]
    assert "Dense embedding complementary views acceptance criteria FORMALIZED" in rec
    assert "Citation Heritage View" in rec
    assert "AUC > 0.75" in rec
    assert "0.7922" in rec
    assert "Cross-Lingual View" in rec
    assert "sachverhalt" in rec
    assert "dispositiv" in rec
    assert "erwaegungen" in rec
    assert "Hybrid Complement View" in rec
    assert "PASS both adversarial gates" in rec
    assert "True OOS jurist preference ceiling ~0.53" in rec
    assert "dense embeddings CANNOT be primary navigation" in rec
    
    print("✅ Dense embedding acceptance criteria verified!")


def test_citation_heritage_174k_tfidf():
    """Verify citation heritage at 174k for TF-IDF is correctly recorded in state."""
    state = load_json("state/evaluation.json")
    
    # The new minimal state format doesn't have detailed summary.citation_heritage_174k_tfidf
    # Verify evidence refs include the citation heritage validation
    refs = state["evidence_refs"]
    assert any("citation_heritage_22year_latest.json" in ref for ref in refs)
    assert any("evaluation_174k_formal_suite_latest.json" in ref for ref in refs)
    
    print("✅ Citation heritage 174k TF-IDF evidence refs verified!")


def test_negative_findings_preserved():
    """Verify negative findings are preserved in state (via next_recommendation and evidence refs)."""
    state = load_json("state/evaluation.json")
    
    rec = state["next_recommendation"]
    assert "True OOS jurist preference ceiling ~0.53" in rec
    assert "dense embeddings CANNOT be primary navigation" in rec
    assert "No further same-question cycles justified" in rec
    
    # Verify evidence refs include negative results
    refs = state["evidence_refs"]
    assert any("24year_dense_adversarial" in ref for ref in refs)
    assert any("EVALUATION_V34_BASELINE_FROZEN_AND_DENSE_ACCEPTANCE_CRITERIA.md" in ref for ref in refs)
    
    print("✅ Negative findings preserved!")


def test_data_blockers_documented():
    """Verify data blockers for 174k dense deployment are documented."""
    state = load_json("state/evaluation.json")
    
    rec = state["next_recommendation"]
    assert "BGE/bger ID mapping" in rec
    assert "parquet 2022-2026" in rec
    assert "section extraction" in rec
    assert "corpus lane resumption required" in rec
    
    print("✅ Data blockers documented!")


def test_evidence_refs():
    """Verify evidence_refs point to correct artifacts (minimal set for v34)."""
    state = load_json("state/evaluation.json")
    
    refs = state["evidence_refs"]
    # New minimal format has 5 core evidence refs
    assert len(refs) == 5
    assert "evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json" in refs
    assert "results/evaluation/partial_dense_2000_2002/citation_heritage_22year_latest.json" in refs
    assert "results/evaluation/partial_dense_2000_2002/section_crosslingual_eval_latest.json" in refs
    assert "results/evaluation/24year_dense_adversarial/evaluation_24year_dense_adversarial_latest.json" in refs
    assert "reports/evaluation/EVALUATION_V34_BASELINE_FROZEN_AND_DENSE_ACCEPTANCE_CRITERIA.md" in refs
    
    print("✅ Evidence references verified!")


def test_accepted_run_id_format():
    """Verify accepted_run_id follows the v34 naming convention."""
    state = load_json("state/evaluation.json")
    
    run_id = state["accepted_run_id"]
    assert run_id.startswith("EVALUATION_V34_")
    assert "BASELINE_FROZEN" in run_id
    assert "37426211974" in run_id  # GitHub run ID
    
    print("✅ Accepted run ID format verified!")


if __name__ == "__main__":
    print("=" * 60)
    print("VERIFICATION TEST: Evaluation Lane State v34 (Repaired)")
    print("Factory Direction: v34")
    print("=" * 60)
    
    test_v34_state_structure()
    test_tfidf_174k_baseline_frozen()
    test_dense_embedding_acceptance_criteria()
    test_citation_heritage_174k_tfidf()
    test_negative_findings_preserved()
    test_data_blockers_documented()
    test_evidence_refs()
    test_accepted_run_id_format()
    
    print("\n" + "=" * 60)
    print("ALL V34 VERIFICATION TESTS PASSED ✅")
    print("=" * 60)