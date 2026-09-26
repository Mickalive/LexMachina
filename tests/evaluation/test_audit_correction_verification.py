#!/usr/bin/env python3
"""
Verification test for evaluation lane state correction post-audit CYCLE_36242734524.
Validates that corrected state.json matches actual computed benchmark results.
"""
import json
from pathlib import Path


def load_json(path):
    with open(path) as f:
        return json.load(f)


def test_citation_heritage_actual_values():
    """Verify citation heritage results match actual computed values from audit."""
    actual = load_json("evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json")
    
    expected_auc = {
        "cited_decisions_tfidf": 0.78921,
        "cited_decisions_tfidf_outcome_hybrid_0.7": 0.774922,
        "cited_decisions_tfidf_outcome_hybrid_0.5": 0.758928,
        "regeste_full_text_hybrid_0.7": 0.850363,
        "regeste_full_text_hybrid_0.5": 0.871414,
        "full_text_tfidf_light": 0.896936,
        "outcome_tfidf": 0.6575000000000001,
        "regeste_tfidf": 0.486074,
    }
    
    expected_recall = {
        "cited_decisions_tfidf": 0.04803921568627451,
        "cited_decisions_tfidf_outcome_hybrid_0.7": 0.049019607843137254,
        "cited_decisions_tfidf_outcome_hybrid_0.5": 0.05,
        "regeste_full_text_hybrid_0.7": 0.03529411764705882,
        "regeste_full_text_hybrid_0.5": 0.03529411764705882,
        "full_text_tfidf_light": 0.052941176470588235,
        "outcome_tfidf": 0.0,
        "regeste_tfidf": 0.00392156862745098,
    }
    
    for rep, data in actual.items():
        auc = data["k_values"]["k10"]["auc"]
        recall = data["k_values"]["k10"]["positive_recall"]
        assert abs(auc - expected_auc[rep]) < 0.001, f"{rep}: AUC {auc} != {expected_auc[rep]}"
        assert abs(recall - expected_recall[rep]) < 0.001, f"{rep}: recall {recall} != {expected_recall[rep]}"
        print(f"✅ {rep}: AUC={auc:.4f}, recall@10={recall:.4f}")


def test_formal_suite_benchmark_counts():
    """Verify formal suite pass/fail counts match actual benchmark statuses."""
    formal = load_json("evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json")
    
    for rep_name, data in formal.items():
        pass_count = 0
        fail_count = 0
        skip_count = 0
        run_separately_count = 0
        
        # adversarial benchmarks
        for bm_name, bm_data in data["adversarial"].items():
            if bm_name == "both_pass":
                continue
            if isinstance(bm_data, dict) and "status" in bm_data:
                if bm_data["status"] == "PASS":
                    pass_count += 1
                elif bm_data["status"] == "FAIL":
                    fail_count += 1
        
        # cross_language benchmarks
        for bm_name, bm_data in data["cross_language"].items():
            if isinstance(bm_data, dict) and "status" in bm_data:
                if bm_data["status"] == "PASS":
                    pass_count += 1
                elif bm_data["status"] == "FAIL":
                    fail_count += 1
        
        # jurist_usability benchmarks
        for bm_name, bm_data in data["jurist_usability"].items():
            if isinstance(bm_data, dict) and "status" in bm_data:
                if bm_data["status"] == "PASS":
                    pass_count += 1
                elif bm_data["status"] == "FAIL":
                    fail_count += 1
                elif bm_data["status"] == "SKIP":
                    skip_count += 1
        
        # full_corpus benchmarks
        for bm_name, bm_data in data["full_corpus"].items():
            if isinstance(bm_data, dict) and "status" in bm_data:
                if bm_data["status"] == "PASS":
                    pass_count += 1
                elif bm_data["status"] == "FAIL":
                    fail_count += 1
                elif bm_data["status"] == "RUN_SEPARATELY":
                    run_separately_count += 1
        
        print(f"\n{rep_name}: PASS={pass_count}, FAIL={fail_count}, SKIP={skip_count}, RUN_SEPARATELY={run_separately_count}")
        
        # Verify against expected corrected counts
        if rep_name == "cited_decisions_tfidf":
            assert pass_count == 4, f"Expected 4 PASS, got {pass_count}"
            assert fail_count == 7, f"Expected 7 FAIL, got {fail_count}"
            assert skip_count == 1, f"Expected 1 SKIP, got {skip_count}"
            assert run_separately_count == 1, f"Expected 1 RUN_SEPARATELY, got {run_separately_count}"
        elif rep_name == "full_text_tfidf_light":
            assert pass_count == 5, f"Expected 5 PASS, got {pass_count}"
            assert fail_count == 6, f"Expected 6 FAIL, got {fail_count}"
            assert skip_count == 1, f"Expected 1 SKIP, got {skip_count}"
            assert run_separately_count == 1, f"Expected 1 RUN_SEPARATELY, got {run_separately_count}"
        elif rep_name == "regeste_full_text_hybrid_0.5":
            assert pass_count == 5, f"Expected 5 PASS, got {pass_count}"
            assert fail_count == 6, f"Expected 6 FAIL, got {fail_count}"
            assert skip_count == 1, f"Expected 1 SKIP, got {skip_count}"
            assert run_separately_count == 1, f"Expected 1 RUN_SEPARATELY, got {run_separately_count}"
    
    print("\n✅ All formal suite benchmark counts verified!")


def test_state_file_has_corrected_citation_heritage():
    """Verify state.json contains corrected citation heritage values."""
    state = load_json("state/evaluation.json")
    
    results = state["summary"]["subquestion_2_citation_heritage"]["results"]
    
    # Check corrected AUC values (not fabricated ones)
    assert abs(results["cited_decisions_tfidf"]["auc_roc"] - 0.7892) < 0.001
    assert abs(results["cited_outcome_hybrid_0.7"]["auc_roc"] - 0.7749) < 0.001
    assert abs(results["cited_outcome_hybrid_0.5"]["auc_roc"] - 0.7589) < 0.001
    assert abs(results["regeste_full_text_hybrid_0.7"]["auc_roc"] - 0.8504) < 0.001
    assert abs(results["regeste_full_text_hybrid_0.5"]["auc_roc"] - 0.8714) < 0.001
    assert abs(results["full_text_tfidf_light"]["auc_roc"] - 0.8969) < 0.001
    assert abs(results["outcome_tfidf"]["auc_roc"] - 0.6575) < 0.001
    assert abs(results["regeste_tfidf"]["auc_roc"] - 0.4861) < 0.001
    
    # Check corrected recall values
    assert abs(results["cited_decisions_tfidf"]["positive_recall@10"] - 0.0480) < 0.001
    assert abs(results["full_text_tfidf_light"]["positive_recall@10"] - 0.0529) < 0.001
    
    # Verify fabricated values are NOT present
    assert results["cited_decisions_tfidf"]["auc_roc"] != 0.973
    assert results["cited_outcome_hybrid_0.7"]["auc_roc"] != 0.960
    assert results["cited_decisions_tfidf"]["positive_recall@10"] != 0.487
    
    print("✅ State file citation heritage values verified as corrected!")


def test_state_file_has_corrected_formal_suite_counts():
    """Verify state.json contains corrected formal suite pass/fail counts."""
    state = load_json("state/evaluation.json")
    
    summary = state["summary"]["subquestion_1_12_benchmark_suite"]["per_representation_summary"]
    
    # Check cited_decisions_tfidf corrected counts
    cd = summary["cited_decisions_tfidf"]
    assert cd["passed"] == 4, f"cited_decisions_tfidf passed={cd['passed']} != 4"
    assert cd["failed"] == 7, f"cited_decisions_tfidf failed={cd['failed']} != 7"
    assert cd["skipped"] == 1, f"cited_decisions_tfidf skipped={cd['skipped']} != 1"
    assert cd["run_separately"] == 1, f"cited_decisions_tfidf run_separately={cd['run_separately']} != 1"
    
    # Check full_text_tfidf_light corrected counts
    ft = summary["full_text_tfidf_light"]
    assert ft["passed"] == 5, f"full_text_tfidf_light passed={ft['passed']} != 5"
    assert ft["failed"] == 6, f"full_text_tfidf_light failed={ft['failed']} != 6"
    assert ft["skipped"] == 1, f"full_text_tfidf_light skipped={ft['skipped']} != 1"
    assert ft["run_separately"] == 1, f"full_text_tfidf_light run_separately={ft['run_separately']} != 1"
    
    # Check regeste_full_text_hybrid_0.5 corrected counts
    rft = summary["regeste_full_text_hybrid_0.5"]
    assert rft["passed"] == 5, f"regeste_full_text_hybrid_0.5 passed={rft['passed']} != 5"
    assert rft["failed"] == 6, f"regeste_full_text_hybrid_0.5 failed={rft['failed']} != 6"
    assert rft["skipped"] == 1, f"regeste_full_text_hybrid_0.5 skipped={rft['skipped']} != 1"
    assert rft["run_separately"] == 1, f"regeste_full_text_hybrid_0.5 run_separately={rft['run_separately']} != 1"
    
    # Verify fabricated counts are NOT present
    assert cd["passed"] != 6  # original fabricated value
    assert cd["failed"] != 5  # original fabricated value
    
    print("✅ State file formal suite counts verified as corrected!")


def test_state_file_hnsw_scope_clarified():
    """Verify state.json clarifies HNSW fix scope."""
    state = load_json("state/evaluation.json")
    
    hnsw = state["summary"]["critical_hnsw_artifact"]
    assert hnsw["status"] == "FIXED_FOR_ADVERSARIAL_ONLY"
    assert "ADVERSARIAL BENCHMARKS ONLY" in hnsw["implemented_fix"]
    assert "citation_heritage" in hnsw["implemented_fix"]
    assert "temporal_stability" in hnsw["implemented_fix"]
    assert "hierarchy family" in hnsw["implemented_fix"]
    assert "boilerplate" in hnsw["implemented_fix"]
    
    print("✅ State file HNSW fix scope verified as clarified!")


def test_state_file_has_audit_correction_record():
    """Verify state.json records the audit correction."""
    state = load_json("state/evaluation.json")
    
    assert "audit_correction_applied" in state["summary"]
    audit = state["summary"]["audit_correction_applied"]
    assert audit["audit_id"] == "CYCLE_36242734524"
    assert audit["gate"] == "REVISE"
    assert len(audit["fixes_applied"]) == 4
    assert "Corrected citation heritage AUC-ROC values" in audit["fixes_applied"][0]
    assert "Corrected positive_recall@10" in audit["fixes_applied"][1]
    assert "Corrected formal suite pass/fail" in audit["fixes_applied"][2]
    assert "Clarified HNSW artifact fix scope" in audit["fixes_applied"][3]
    assert audit["corrected_report"] == "reports/evaluation/EVALUATION_174K_V27_CYCLE_REPORT_20260926_CORRECTED.md"
    
    print("✅ State file audit correction record verified!")


def test_next_recommendation_mentions_corrections():
    """Verify next_recommendation mentions audit corrections."""
    state = load_json("state/evaluation.json")
    
    rec = state["next_recommendation"]
    assert "CORRECTED from audit CYCLE_36242734524" in rec
    assert "AUDIT CORRECTION APPLIED" in rec
    assert "0.66-0.90" in rec  # corrected AUC range
    assert "3-5%" in rec  # corrected recall range
    
    print("✅ State file next_recommendation mentions corrections!")


if __name__ == "__main__":
    print("=" * 60)
    print("VERIFICATION TEST: Evaluation Lane State Correction")
    print("Audit: CYCLE_36242734524 (REVISE gate)")
    print("=" * 60)
    
    test_citation_heritage_actual_values()
    test_formal_suite_benchmark_counts()
    test_state_file_has_corrected_citation_heritage()
    test_state_file_has_corrected_formal_suite_counts()
    test_state_file_hnsw_scope_clarified()
    test_state_file_has_audit_correction_record()
    test_next_recommendation_mentions_corrections()
    
    print("\n" + "=" * 60)
    print("ALL VERIFICATION TESTS PASSED ✅")
    print("=" * 60)