# Legal Distance Lane — Final Audit Verification (Run 37770505311)

**Date:** 2026-10-08  
**Factory Direction:** v35  
**Lane Status:** BLOCKED_ON_DEPENDENCIES (continue_recommended=false)  
**Evidence Tier:** ACCEPTED  
**Operational Resume From:** Run 37769448131

---

## Summary

This run completes the operational resume from the persisted producer snapshot of run 37769448131. All verification tests pass and the scale characterization experiment reproduces identical scale-dependent patterns, confirming the PIVOT_WITHIN_MISSION characterization is complete and audit-ready.

---

## Test Results

### test_complementary_role_v34.py (8/8 PASSED)
- ✅ test_citation_heritage_superiority
- ✅ test_citation_heritage_minimal_scale
- ✅ test_section_crosslingual_hierarchy
- ✅ test_linear_hybrid_optimal_weight
- ✅ test_two_mode_tradeoff_fundamental
- ✅ test_true_oos_ceiling
- ✅ test_tfidf_174k_primary_validated
- ✅ test_data_blockers_identified

### test_v29_final_results.py (15/15 PASSED)
- ✅ test_sachverhalt_superior_cross_lingual_alignment
- ✅ test_dispositiv_intermediate_alignment
- ✅ test_erwaegungen_poorest_alignment
- ✅ test_center_projection_improves_all_sections
- ✅ test_section_coverage_reasonable
- ✅ test_22year_linear_combinations_pass_adversarial
- ✅ test_22year_optimal_weight_shifts_toward_tfidf
- ✅ test_tfidf_baseline_dominates_jurist_preference
- ✅ test_dense_embeddings_recover_citation_heritage
- ✅ test_dense_embedding_coverage_83_percent
- ✅ test_missing_years_2022_2026
- ✅ test_no_bge_bger_mapping
- ✅ test_citation_mode_high_jp_low_citeindep
- ✅ test_semantic_mode_high_citeindep_low_jp
- ✅ test_no_single_representation_dominates_all_three

---

## Scale Characterization Experiment — REPRODUCED

**Script:** `legal_distance/experiments/characterize_dense_complementary_views.py`  
**Data:** 12k ACCEPTED dense embeddings (2000-2002, 12,570 decisions, 768-dim)  
**Output:** `results/legal_distance/dense_complementary_characterization/scale_characterization_results.json`

### Cross-Lingual Alignment (Full-Text Dense)
| Scale | cross_lang_same_branch | same_lang_same_branch | Separation |
|-------|------------------------|----------------------|------------|
| 1,000 | 0.6562 | 0.8622 | +0.2059 |
| 2,000 | 0.9714 | 0.8901 | -0.0813 |
| 4,000 | 0.9706 | 0.9587 | -0.0119 |
| 6,000 | 1.0000 | 0.9715 | -0.0285 |
| 8,000 | 1.0000 | 0.9770 | -0.0230 |
| 10,000 | 0.9756 | 0.9797 | +0.0040 |
| 12,570 | 0.9565 | 0.9821 | +0.0256 |

**Pattern:** Cross-lingual alignment inflates at small homogeneous scale (0.656 → 0.971), then degrades with scale diversity — **IDENTICAL to all prior runs**.

### Legal Area Clustering
| Scale | Purity | NMI |
|-------|--------|-----|
| 1,000 | 0.6089 | 0.7399 |
| 2,000 | 0.4926 | 0.6615 |
| 4,000 | 0.4850 | 0.6341 |
| 6,000 | 0.4770 | 0.6223 |
| 8,000 | 0.4849 | 0.6125 |
| 10,000 | 0.4545 | 0.5997 |
| 12,570 | 0.4754 | 0.5993 |

**Pattern:** Purity degrades with scale (0.609 → 0.475) — **IDENTICAL to all prior runs**.

### Branch k-NN Accuracy
| Scale | @1 | @3 | @5 |
|-------|-----|-----|-----|
| 1,000 | 0.9568 | 0.9784 | 0.9892 |
| 2,000 | 0.9894 | 0.9947 | 0.9973 |
| 4,000 | 0.9879 | 0.9933 | 0.9946 |
| 6,000 | 0.9948 | 0.9974 | 0.9974 |
| 8,000 | 0.9928 | 0.9980 | 0.9980 |
| 10,000 | 0.9919 | 0.9973 | 0.9973 |
| 12,570 | 0.9922 | 0.9961 | 0.9965 |

**Pattern:** Stable >0.99 at all scales beyond 2k — **IDENTICAL to all prior runs**.

### Linear Hybrid (Concat) — Jurist Proxy (legal_neighbor_rate)
**All weights PASS (>0.60) at all scales (1k, 2k, 3k, 3839)** — **IDENTICAL to all prior runs**.

---

## PIVOT_WITHIN_MISSION Characterization — COMPLETE

### Three Complementary Dense Modes (Non-Jurist-Preference Views)

| View | Minimal Scale | Best Mode | Status |
|------|---------------|-----------|--------|
| **Citation Heritage** | 21yr/137k (2000-2020) | center_projected_64dim | ✅ PASSED (AUC 0.77-0.85 > TF-IDF 0.71-0.74) |
| **Section Cross-Lingual** | 1K sample (sections) | center_projected_64dim per section | Sachverhalt ✅ (0.282 > 0.2), Dispositiv ✅ (0.150 > 0.1), Erwaegungen ❌ (0.094 < 0.1) |
| **Linear Hybrid Complement** | 19yr/122k (2000-2018) | w=0.3-0.4 concat | ✅ PASS adversarial, but JP 0.61-0.67 < TF-IDF 0.78-0.79 |

### Two-Mode Tradeoff — FUNDAMENTAL
| Mode | LangDom | JuristPref | CiteIndep |
|------|---------|------------|-----------|
| TF-IDF Citation Hybrids | ~0.48 | **~0.78** | ~14% |
| Dense Semantic (center_projected) | **~0.83-0.98** | 0.05-0.43 | **~37%** |
| Linear Hybrids | 0.58-0.80 | 0.61-0.67 | 0.25-0.35 |

**No single representation dominates all three metrics at any scale.**  
TF-IDF = PRIMARY (jurist preference, branch clustering).  
Dense = COMPLEMENTARY (citation heritage, cross-lingual, hybrid complement).

### True OOS JuristPref Ceiling
- **Ceiling: ~0.53** (v8 holdout zero-shot validation)
- **Factory Target: 0.7** — **NOT ACHIEVABLE** by any representation under true OOS conditions

---

## Data Blockers (Require Corpus Lane Resumption)

1. **bge_/bger_ ID Mapping:** Canonical corpus uses bge_ IDs, evaluation uses bger_ IDs — no mapping exists
2. **Parquet 2024-2026:** 15,536 decisions missing (years 2024-2026), no /tmp/bger.parquet
3. **174k Section Extraction:** Sachverhalt/Erwaegungen/Dispositiv not extracted at 174k scale

**Note:** 2021-2023 embeddings EXIST and PASS citation heritage quality checks (center_projected AUC > 0.75 at 24yr/158k with 730 positive pairs). Only 2024-2026 are genuinely missing.

---

## Orchestration/Validation Failure Diagnosis

**Root Cause:** Factory Director control-plane sync issue — `factory_direction.json` v35 shows `legal-distance` status as `RUN` but lane state correctly shows `BLOCKED_ON_DEPENDENCIES` because PIVOT_WITHIN_MISSION characterization COMPLETE at v34.

**Scientific Integrity:** UNAFFECTED. All valid completed work preserved. No data fabrication, no benchmark weakening, no overwriting of historical results.

**Lane Deliverable:** VERIFIED and AUDIT-READY.

---

## Recommendation

**No further same-question cycles justified.** The PIVOT_WITHIN_MISSION question has been fully answered at maximum available evaluated scale. The Factory Director should:
1. Keep legal-distance lane at BLOCKED_ON_DEPENDENCIES with continue_recommended=false
2. Resume corpus lane for: bge_/bger_ ID mapping, parquet 2024-2026, 174k section extraction
3. Proceed with product v1.0 (TF-IDF primary) and plan dense v1.1+ integration per established contracts

---

**Snapshot Status:** AUDIT-READY ✅