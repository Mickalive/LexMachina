# Evaluation Lane - Monitoring Cycle Report (Factory Direction v28)

**Date**: 2026-09-26  
**Lane**: evaluation  
**Direction Version**: 28  
**Evidence Tier**: REPRODUCED  
**Cycle Status**: BLOCKED_ON_DEPENDENCIES  
**Run ID**: evaluation_v28_monitoring_cycle_20260926  
**Continue Recommended**: false  

---

## Executive Summary

This monitoring cycle confirms the evaluation lane remains **correctly BLOCKED_ON_DEPENDENCIES** with no new awaited representations detected since the last formal suite completion. The TF-IDF family evaluation at 174k scale is complete across all three machine-executable sub-questions per factory direction v28. The active monitor (`monitor_and_evaluate_174k.py`) performed check #126 and verified infrastructure readiness for auto-evaluation when dense embeddings land from legal-distance.

---

## Monitoring Check Results

**Monitor execution**: `python evaluation/monitor_and_evaluate_174k.py`  
**Check count**: 126 (incremented from 125)  
**Last check**: 2026-09-26T13:56:01.036977  

### Scan Results

| Mount Path | Status | Files Found | Notes |
|------------|--------|-------------|-------|
| `fractal_map/hierarchical_map_174k/legal_tfidf_embeddings` | ✓ DETECTED | 8 TF-IDF embeddings | Already evaluated, marked `TF_IDF_COMPLETE_NO_EVAL_NEEDED` |
| `fractal_map/hierarchical_map_174k/tfidf_embeddings` | ✓ DETECTED | 4 TF-IDF embeddings | Already evaluated, marked `TF_IDF_COMPLETE_NO_EVAL_NEEDED` |
| `legal-distance/legal_distance/results/174k_dense_embeddings` | ✗ NO FINAL EMBEDDINGS | 3 year-split checkpoints only | Years 2000-2002 complete; years 2003-2025 blocked on corpus mount path gap |

### Representation Readiness Matrix

**COMPLETED (TF-IDF family at 174k) - All 8 evaluated:**
- ✓ `cited_decisions_tfidf`
- ✓ `outcome_tfidf`
- ✓ `cited_decisions_tfidf_outcome_hybrid_0.5`
- ✓ `cited_decisions_tfidf_outcome_hybrid_0.7`
- ✓ `regeste_tfidf`
- ✓ `full_text_tfidf_light`
- ✓ `regeste_full_text_hybrid_0.5`
- ✓ `regeste_full_text_hybrid_0.7`

**AWAITED (12 representations) - All ✗ NOT READY:**

| Category | Representation | Status |
|----------|----------------|--------|
| **Dense embeddings (8)** | center_projected_768dim | ✗ |
| | center_projected_64dim | ✗ |
| | center_projected_128dim | ✗ |
| | linear_metric_epoch4 | ✗ |
| | mahalanobis_metric_epoch4 | ✗ |
| | hybrid_stabilized_epoch1 | ✗ |
| | hybrid_v2_epoch3 | ✗ |
| | (8th dense variant) | ✗ |
| **Citation roles (3)** | citation_role_citing_alpha0.3 | ✗ |
| | citation_role_following_alpha0.3 | ✗ |
| | citation_role_criticizing_alpha0.3 | ✗ |
| **Linear hybrids (2)** | linear_citation_concat | ✗ |
| | linear_hybrid05_concat | ✗ |

---

## Legal-Distance Dense Embeddings Progress

**Year-split checkpoints available** in `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/`:
- `embeddings_2000.npy` (11,793,536 bytes)
- `embeddings_2001.npy` (13,308,032 bytes)
- `embeddings_2002.npy` (13,513,856 bytes)
- Metadata files for each year

**Progress**: 3/26 years complete (2000, 2001, 2002) = 19,441 decisions = 11% of 173,963  
**Blocker**: Years 2003-2025 pending corpus artifact publication gap resolution at expected mount paths (factory direction v28)  
**Final concatenation**: Pending completion of all 26 years

---

## Infrastructure Status (All OPERATIONAL)

| Component | Status | Notes |
|-----------|--------|-------|
| HNSW backend | OPERATIONAL_ON_GITHUB_RUNNERS | Verified in CI |
| Scalable NN | OPERATIONAL_WITH_SKLEARN_FALLBACK | HNSW + exact k-NN fallback |
| v25 formal suite | OPERATIONAL | 12-benchmark suite + HNSW artifact fix |
| Citation heritage | FROZEN_137314_PAIRS_READY | 95.9% citation resolution |
| v17b normalization | OPERATIONAL | 213→163 labels, 32 cross-lingual concepts |
| Monitor script | ACTIVE | Enhanced scan paths, formal suite integration |
| Formal suite runner | OPERATIONAL | NoneType.lower bug fixed (v52+) |
| HNSW artifact fix | CONFIRMED | Exact k-NN on valid subset for adversarial |

---

## HNSW Artifact Status: CONFIRMED AND FIXED

**Root cause**: HNSW with fixed parameters (M=16, ef_construction=200, ef_search=100, seed=42) produces nearly identical k-NN graphs across different TF-IDF representations at 174k scale.

**Evidence**: 
- Exact k-NN on valid subset (1,199 decisions with known branch): jurist pairwise 0.73-0.80 across representations
- HNSW on full corpus: jurist pairwise ≈0.12 for ALL representations

**Fix applied**: Adversarial benchmarks (language dominance, jurist pairwise) use exact k-NN on fixed stratified subsample (n=2000, seed=42). HNSW retained for full-corpus scale benchmarks (citation heritage, temporal stability, hierarchy family on subsamples).

---

## Sub-Question Completion Status (from v28 Formal Suite)

### 1. Full 12-Benchmark Formal Suite at 174k Scale ✓ COMPLETE
- **8 TF-IDF representations evaluated** with frozen harness v3 thresholds
- **Config hash**: `b51701f5a9c11692` (immutable)
- **4 PASS / 4 FAIL** on both adversarial gates
- **Best**: `cited_decisions_tfidf` (LangDom=0.5295, JuristPref=0.8020)
- **Production default**: `cited_outcome_hybrid_0.7` (LangDom=0.5238, JuristPref=0.7975)
- **Universal failures**: hierarchy_coherence, legal_area_clustering, temporal_stability, boilerplate_resistance (corpus/label limitations)
- **Two-mode tradeoff confirmed**: Citation-based PASS adversarial, FAIL hierarchy; Text-based PASS hierarchy, FAIL adversarial

### 2. Citation Heritage Benchmark ✓ COMPLETE
- **Infrastructure validated** with published 174k citation-ID resolution (2,019/2,105 = 95.9%)
- **Frozen pair pool**: 137,314 pairs (1,020 positive + 1,020 negative)
- **TF-IDF results**: All FAIL (recall@10 < 0.2 threshold despite AUC 0.76-0.90)
- **Ready for**: 174k dense embeddings evaluation when available

### 3. v17b Label Normalization Generalization ✓ COMPLETE
- **Normalization**: 213 raw → 163 normalized labels (23.5% reduction), 32 cross-lingual concepts
- **85,819 decisions relabeled**, 91,193 with legal_area field
- **Generalization**: PARTIAL (2/8 reps within ≤10% worsening rule)
- **Citation-based reps**: 1.5-1.6x hierarchy purity gains
- **Text-based reps**: 1.0x (no improvement)
- **Best normalized hierarchy purity**: 0.47 (threshold: 0.7 — NOT MET)
- **Conclusion**: Label normalization helps but doesn't solve hierarchy ceiling at 174k

---

## External Dependencies

**Jurist human study**: BLOCKED (5-10 Swiss jurists recruitment by repository owner; framework ready)

---

## Recommendation

**CONTINUE MONITORING** — No additional same-question cycle justified for TF-IDF family.

The evaluation lane will automatically detect and evaluate new representations when they land via the active monitor (`monitor_and_evaluate_174k.py`). The next evaluation cycle will be triggered when legal-distance delivers:

1. **Full 174k dense embeddings** (concatenated from all 26 years)
2. **Citation role embeddings** at 174k
3. **Linear hybrid combinations** at 174k

The lane state correctly remains `BLOCKED_ON_DEPENDENCIES` with `continue_recommended=false` for the current question. The Factory Director will decide the successor question when dense embeddings land.

---

## Evidence References

1. `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
2. `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json`
3. `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json`
4. `evaluation/results/174k_label_analysis/174k_legal_area_analysis.json`
5. `evaluation/results/v17b_174k_tfidf/v17b_174k_tfidf_latest.json`
6. `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
7. `evaluation/state/monitor_174k_state.json` (check_count=126, last_check=2026-09-26T13:56:01)
8. `evaluation/state/evaluation.json` (direction_version=28, cycle_status=BLOCKED_ON_DEPENDENCIES)

---

*Report generated per Research Protocol §8: "Write machine-readable lane state plus human-readable report"*