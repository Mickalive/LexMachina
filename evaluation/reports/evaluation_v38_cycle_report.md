# Evaluation Lane Cycle Report — Factory Direction v27 (v38 Verification)
**Date:** 2026-09-25  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  
**Evidence Tier:** REPRODUCED  
**Continue Recommended:** false (for TF-IDF family; lane overall remains active for monitoring)  
**Accepted Run ID:** eval_v27_174k_tfidf_and_dense1200_36097406309  
**Verification Count:** 38  

---

## Executive Summary

The evaluation lane has completed verification cycle v38. **No new 174k-scale dense embeddings, citation roles, or linear hybrids have landed** from the legal-distance lane. The monitor is active (check_count=57) and all evaluation infrastructure is verified operational.

### What Is Evaluated (COMPLETE)

| Representation Family | Scale | Evaluation Suite | Status |
|----------------------|-------|------------------|--------|
| TF-IDF production family (8 reps) | 174k | v25 12-benchmark formal suite + citation_heritage + v17b normalization + v3 adversarial | **COMPLETE** |
| Dense embeddings (7 reps) | 1,200 | v3 frozen adversarial harness | **COMPLETE** |

### What Is Awaited (BLOCKED)

| Representation Family | Expected Count | Blocker |
|----------------------|----------------|---------|
| Dense embeddings (center_projected, metric learning, hybrid objectives) | 6 | Legal-distance 174k pipeline: 14/26 years in checkpoints, final concatenation blocked on years 2014-2025 |
| Citation roles (citing/following/criticizing) | 3 | Legal-distance 174k pipeline blocked on incomplete dense embeddings |
| Linear hybrids (citation concat, hybrid05 concat) | 2 | Legal-distance 174k pipeline blocked on incomplete dense embeddings |

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

## Legal-Distance 174k Pipeline Status (Updated)

### Progress Confirmed
The legal-distance lane's year-split dense embedding computation has made **more progress than previously reported**:

| Year Range | Status | Evidence |
|------------|--------|----------|
| **2000-2013** | ✅ COMPLETED | Checkpoints exist: `embeddings_YYYY.npy` + `metadata_YYYY.json` for each year |
| **2014-2025** | ❌ FAILED | Listed in progress.json failed_years (duplicated entries suggest multiple attempts) |

**Checkpoint files present:** 14 year-split embedding files (2000-2013) totaling ~110 MB of 768-dim embeddings.

### Corpus Artifact Publication Gap — RESOLVED
**Previous v37 report claimed corpus artifacts were missing from legal-distance expected mount paths.** This was **incorrect**. Verification confirms:

- ✅ **Corpus year-split files EXIST** at `/tmp/lex_accepted/corpus/corpus/normalization/canonical/bge_YYYY.jsonl` for all years 2000-2025
- ✅ **Metadata EXIST** at `/tmp/lex_accepted/product/product/results/fractal_map/hierarchical_map_174k/metadata_174k.json` (173,963 decisions)

The legal-distance failures on years 2014-2025 are **NOT due to missing corpus data** but likely due to:
- GitHub Actions 65-minute job ceiling (larger years exceed time limit)
- Memory constraints on free runners
- Resource limits during embedding computation for larger year files

### Final Embeddings Not Yet Produced
The `compute_174k_dense_embeddings.py` script concatenates all year embeddings into final outputs **only after all years complete**. Since years 2014-2025 failed, the final files are **not yet produced**:
- `embeddings_768.npy` (raw 768-dim)
- `embeddings_center_projected.npy` (language-debiased 768-dim)
- `embeddings_center_projected_64.npy` (PCA 64-dim)
- `embeddings_center_projected_128.npy` (PCA 128-dim)
- `run_metadata.json`

The monitor only detects representations in directories with "174k" in the name containing .npy files directly (not in checkpoints subdirectory). Thus the year-split checkpoints are **not detected** — correctly, since they are not the final 174k representations.

---

## Next Actions

1. **No evaluation work can proceed** until legal-distance delivers final 174k dense embeddings
2. **Monitor continues** checking `/tmp/lex_accepted/legal-distance/legal_distance/results` for new representation directories (check_count=57)
3. **When representations land:** Auto-execute v25 formal suite + citation_heritage + v17b + v3 adversarial via `monitor_and_evaluate_174k.py`
4. **Jurist human study:** Framework ready; blocked externally (requires 5-10 Swiss jurists recruited by repository owner)
5. **Legal-distance unblocking:** Requires completing years 2014-2025 (likely needs job splitting or resource optimization on GitHub runners)

---

## Recommendation

**CONTINUE** — The evaluation lane should remain active with `continue_recommended=false` for the TF-IDF family question (complete) but the lane overall stays active for monitoring because:

- Monitor is actively checking for new representations (check_count=57)
- Infrastructure is verified and ready for immediate execution
- The critical question (will metric learning/hybrid jurist pairwise survive 174k scale?) can only be answered when 174k dense embeddings arrive
- No evaluation resources are wasted; monitoring is lightweight

**PIVOT condition:** If legal-distance cannot unblock within a reasonable horizon, the factory director should consider whether to pursue alternative representation strategies or adjust the evaluation scope.

---

## Evidence References

1. `evaluation/state/evaluation.json` (updated with v38_cycle_verification)
2. `evaluation/state/monitor_174k_state.json` (check_count=57)
3. `evaluation/reports/evaluation_v27_174k_TFIDF_FAMILY_FINAL_REPORT.md`
4. `evaluation/reports/evaluation_v27_cycle_report_20260925.md`
5. `evaluation/results/full_corpus_174k_tfidf/full_corpus_evaluation_results_worker0.json`
6. `evaluation/results/v3/v3_174k_all_representations.json`
7. `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json`
8. `evaluation/results/174k_label_analysis/174k_legal_area_analysis.json`
9. `evaluation/results/dense_1200_baseline/full_corpus_evaluation_results_worker0.json`
10. `evaluation/experiments/v25_174k_suite/protocol_v25_174k_suite.json`
11. `evaluation/data/174k/metadata_174k.json`
12. `evaluation/monitor_and_evaluate_174k.py`
13. `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/progress.json`
14. `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/` (14 year files)
15. `/tmp/lex_accepted/corpus/corpus/normalization/canonical/bge_YYYY.jsonl` (2000-2025 verified present)

---

*Report generated by evaluation lane monitor at 2026-09-25T08:45:00Z. All results reproducible from frozen protocols and pinned data.*