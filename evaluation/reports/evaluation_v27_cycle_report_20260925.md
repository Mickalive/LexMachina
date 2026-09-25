# Evaluation Lane Cycle Report — Factory Direction v27
**Date:** 2026-09-25  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  
**Evidence Tier:** REPRODUCED  
**Continue Recommended:** true  
**Accepted Run ID:** eval_v27_174k_tfidf_and_dense1200_36097406309  

---

## Executive Summary

The evaluation lane has completed all machine-executable evaluation tasks for representations currently available in accepted state. No new 174k-scale dense embeddings, citation roles, or linear hybrids have landed from the legal-distance lane. The monitor is active (check_count=52) and infrastructure is verified ready.

### What Is Evaluated (COMPLETE)

| Representation Family | Scale | Evaluation Suite | Status |
|----------------------|-------|------------------|--------|
| TF-IDF production family (8 reps) | 174k | v25 12-benchmark formal suite + citation_heritage + v17b normalization + v3 adversarial | **COMPLETE** |
| Dense embeddings (7 reps) | 1,200 | v3 frozen adversarial harness | **COMPLETE** |

### What Is Awaited (BLOCKED)

| Representation Family | Expected Count | Blocker |
|----------------------|----------------|---------|
| Dense embeddings (center_projected, metric learning, hybrid objectives) | 6 | Legal-distance 174k pipeline only at year 2000 checkpoint |
| Citation roles (citing/following/criticizing) | 3 | Legal-distance 174k pipeline blocked on corpus artifacts |
| Linear hybrids (citation concat, hybrid05 concat) | 2 | Legal-distance 174k pipeline blocked on corpus artifacts |

---

## Key Findings (Frozen — No New Data)

### TF-IDF Family at 174k Scale (8 representations)

**12-Benchmark Formal Suite (v25 protocol, frozen thresholds):**
- **No representation passes all 12 benchmarks**
- Citation-aware representations (cited_decisions_tfidf, cited_outcome_hybrid_*) excel at:
  - citation_heritage (AUC > 0.91) ✓
  - adversarial/multilingual ✓
  - But FAIL: branch_knn, tf_metadata, boilerplate, temporal_stability, hierarchy_coherence
- Full-text/regeste hybrids pass:
  - branch_knn, tf_metadata, boilerplate, temporal ✓
  - But FAIL: adversarial (language dominance > 0.99), multilingual, hierarchy_coherence
- **ALL FAIL:** hierarchy_coherence (max purity 0.465 vs 0.7 threshold), legal_area_clustering

**Citation Heritage (frozen 137,314-pair pool):**
- 7/8 representations PASS (AUC-ROC ≥ 0.65)
- Top: cited_decisions_tfidf AUC=0.973, nn_citation_rate@10=0.487
- Only regeste_tfidf FAILS (AUC=0.487)

**v17b Label Normalization (174k fine-grained legal_area):**
- 5/8 representations show 46-64% purity gains across hierarchy-family metrics
- 3/8 show no change (labels already normalized)
- 0 representations worsen
- **But:** Even normalized, best hierarchy purity = 0.47 < 0.7 threshold — fundamental granularity/coverage limits persist

**v3 Adversarial Harness at 174k:**
- **NO representation passes BOTH adversarial gates** (lang_dom < 0.85 AND jurist_pairwise > 0.5)
- All pass language dominance (~0.61) but **ALL FAIL jurist pairwise** (legal_neighbor_rate ~0.12 vs 0.5 threshold)
- 6/8 representations show identical HNSW k-NN graphs (methodological artifact)
- Cross-language recall ~0.01 for ALL representations

### Dense Embeddings at 1,200 Scale (7 representations, v3 frozen harness)

| Representation | Lang Dom | Jurist Pref | Both Gates | Jurivoc L0 NMI | Scale Stability | Boilerplate |
|---------------|----------|-------------|------------|----------------|-----------------|-------------|
| **linear_metric_epoch4** | 0.6805 | **0.6847** | ✓ PASS | 0.63-0.74 | ~0.76-0.80 | ~-0.89 |
| mahalanobis_metric_epoch4 | 0.6830 | 0.6781 | ✓ PASS | 0.63-0.74 | ~0.76-0.80 | ~-0.89 |
| hybrid_stabilized_epoch1 | 0.6701 | 0.6656 | ✓ PASS | 0.63-0.74 | ~0.76-0.80 | ~-0.89 |
| hybrid_v2_epoch3 | 0.7765 | 0.5988 | ✓ PASS | 0.63-0.74 | ~0.76-0.80 | ~-0.89 |
| center_projected_64dim | 0.7733 | 0.5121 | ✓ PASS | FAIL | ~0.76-0.80 | ~-0.89 |
| center_projected_768dim | 0.7733 | 0.4912 | ✗ FAIL | FAIL | ~0.76-0.80 | ~-0.89 |
| hybrid_projection_final | 0.7774 | 0.4529 | ✗ FAIL | FAIL | ~0.76-0.80 | ~-0.89 |

**Critical Scale Extrapolation Risk:** TF-IDF jurist pairwise **COLLAPSED from 0.79→0.12** (1200→174k). Will metric learning/hybrid objectives maintain >0.5 at 174k?

---

## Infrastructure Status (Verified)

| Component | Status |
|-----------|--------|
| HNSW backend (hnswlib) | OPERATIONAL_ON_GITHUB_RUNNERS |
| Scalable NN (sklearn fallback) | OPERATIONAL_WITH_SKLEARN_FALLBACK |
| v25 formal suite (174k) | OPERATIONAL |
| Citation heritage (137,314 pairs) | FROZEN_READY |
| v17b label normalization | OPERATIONAL |
| Monitor script | ACTIVE_WITH_FORMAL_SUITE |

---

## Blocker Detail: Legal-Distance 174k Pipeline

The legal-distance lane's 174k dense embedding computation is **blocked on corpus artifact publication**:

- **Year 2000 checkpoint exists:** `embeddings_2000.npy` (11.8 MB), `metadata_2000.json`
- **Years 2001-2025:** FAILED — missing upstream data at expected mount paths
- **Root cause:** Year-split normalized parquet files and `metadata_174k.jsonl` exist in corpus workspace but NOT at `/tmp/lex_accepted/corpus/...` and `/tmp/lex_accepted/evaluation/...` mount paths where legal-distance expects them
- **Director note (v27):** "CRITICAL PATH: Publish corpus lane year-split artifacts to legal-distance expected mount paths to unblock 174k dense embeddings"

---

## Next Actions

1. **No evaluation work can proceed** until legal-distance delivers 174k dense embeddings
2. **Monitor continues** checking `/tmp/lex_accepted/legal-distance/legal_distance/results` for new representation directories
3. **When representations land:** Auto-execute v25 formal suite + citation_heritage + v17b + v3 adversarial via `monitor_and_evaluate_174k.py`
4. **Jurist human study:** Framework ready; blocked externally (requires 5-10 Swiss jurists recruited by repository owner)

---

## Recommendation

**CONTINUE** — The evaluation lane should remain active with `continue_recommended=true` because:
- Monitor is actively checking for new representations (check_count=52)
- Infrastructure is verified and ready for immediate execution
- The critical question (will metric learning/hybrid jurist pairwise survive 174k scale?) can only be answered when 174k dense embeddings arrive
- No evaluation resources are wasted; monitoring is lightweight

**PIVOT condition:** If legal-distance cannot unblock within a reasonable horizon, the factory director should consider whether to pursue alternative representation strategies or adjust the evaluation scope.

---

## Evidence References

1. `evaluation/reports/evaluation_v26_174k_VERIFICATION_REPORT.md`
2. `evaluation/reports/evaluation_v26_174k_formal_suite_COMPLETION_REPORT.md`
3. `evaluation/reports/evaluation_v26_174k_adversarial_synthesis_report.md`
4. `evaluation/reports/evaluation_v27_cycle_report.md`
5. `evaluation/reports/dense_1200_baseline_report.md`
6. `evaluation/results/full_corpus_174k_tfidf/full_corpus_evaluation_results_worker0.json`
7. `evaluation/results/v3/v3_174k_all_representations.json`
8. `evaluation/results/v3/cited_decisions_tfidf_174k_full.json`
9. `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json`
10. `evaluation/results/174k_label_analysis/174k_legal_area_analysis.json`
10. `evaluation/results/dense_1200_baseline/full_corpus_evaluation_results_worker0.json`
11. `evaluation/experiments/v25_174k_suite/protocol_v25_174k_suite.json`
12. `evaluation/data/174k/metadata_174k.json`
13. `evaluation/monitor_and_evaluate_174k.py`
14. `evaluation/state/monitor_174k_state.json`

---

*Report generated by evaluation lane monitor at 2026-09-25T07:46:11*