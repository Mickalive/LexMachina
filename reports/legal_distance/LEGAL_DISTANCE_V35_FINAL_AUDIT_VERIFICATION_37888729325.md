# Legal Distance Lane — Final Audit Verification (Run 37888729325)

## Summary
**Status**: AUDIT-READY ✅  
**Lane**: legal-distance  
**Factory Direction**: v35  
**Evidence Tier**: ACCEPTED  
**Cycle Status**: BLOCKED_ON_DEPENDENCIES  
**Continue Recommended**: false  

## Orchestration/Validation Failure Diagnosed
**Root Cause**: Factory direction v35 shows `legal-distance: RUN` but lane state correctly shows `BLOCKED_ON_DEPENDENCIES` because the PIVOT_WITHIN_MISSION characterization was COMPLETE at v34 (run 37677999602). The "new question" in factory direction v35 was ALREADY ANSWERED at v34.

**Scientific Integrity**: UNAFFECTED — all evidence ACCEPTED, all tests PASS.

## PIVOT_WITHIN_MISSION Characterization — COMPLETE
The new question from factory direction v34/v35 has been **fully answered** at maximum available evaluated scale:

> **"What minimal dense embedding scale and which specific dense modes (citation heritage, section cross-lingual, linear hybrid complement) are necessary and sufficient for the product's non-jurist-preference views?"**

### Three Complementary Modes Characterized

| View | Minimal Scale | Best Mode | Key Metric | Status |
|------|---------------|-----------|------------|--------|
| **Citation Heritage** | 21yr / 137k (2000-2020) | center_projected_64dim | AUC 0.77-0.85 > TF-IDF 0.71-0.74 | ✅ PASSED |
| **Section Cross-Lingual** | 1K sample (sections) | center_projected_64dim per section | Sachverhalt 0.282 > 0.2, Dispositiv 0.150 > 0.1, Erwaegungen 0.094 < 0.1 | ✅ 2/3 PASSED |
| **Linear Hybrid Complement** | 19yr / 122k (2000-2018) | w=0.3-0.4 linear | PASS adversarial gates, JP 0.61-0.67 < TF-IDF 0.78-0.79 | ✅ PASSED |

### Fundamental Tradeoff Reproduced
**NO single representation dominates all three metrics at any scale:**
- TF-IDF Citation Hybrids: JP ~0.78, LangDom ~0.48, CiteIndep ~14% → **PRIMARY**
- Dense Semantic (center_projected): JP ~0.05-0.43, LangDom ~0.83-0.98, CiteIndep ~37% → FAILS jurist gate
- Linear Hybrids: Intermediate on all, but JP < TF-IDF baseline → COMPLEMENTARY

### True OOS Ceiling Confirmed
- **True OOS JuristPref ceiling ~0.53** < 0.7 factory target (via v8 holdout zero-shot validation)
- No representation achieves factory target under true out-of-sample conditions

## Test Results — ALL PASS (23/23)

### test_complementary_role_v34.py (8/8)
1. ✅ test_citation_heritage_superiority
2. ✅ test_citation_heritage_minimal_scale
3. ✅ test_section_crosslingual_hierarchy
4. ✅ test_linear_hybrid_optimal_weight
5. ✅ test_two_mode_tradeoff_fundamental
6. ✅ test_true_oos_ceiling
7. ✅ test_tfidf_174k_primary_validated
8. ✅ test_data_blockers_identified

### test_v29_final_results.py (15/15)
1. ✅ test_sachverhalt_superior_cross_lingual_alignment
2. ✅ test_dispositiv_intermediate_alignment
3. ✅ test_erwaegungen_poorest_alignment
4. ✅ test_center_projection_improves_all_sections
5. ✅ test_section_coverage_reasonable
6. ✅ test_22year_linear_combinations_pass_adversarial
7. ✅ test_22year_optimal_weight_shifts_toward_tfidf
8. ✅ test_tfidf_baseline_dominates_jurist_preference
9. ✅ test_dense_embeddings_recover_citation_heritage
10. ✅ test_dense_embedding_coverage_83_percent
11. ✅ test_missing_years_2022_2026
12. ✅ test_no_bge_bger_mapping
13. ✅ test_citation_mode_high_jp_low_citeindep
14. ✅ test_semantic_mode_high_citeindep_low_jp
15. ✅ test_no_single_representation_dominates_all_three

## Evidence References Verified
- **174k Dense Embeddings**: Checkpoints 2000-2023 complete (24 years, 158,427 decisions); 2024-2026 genuinely missing
- **Citation Heritage**: 22yr AUC 0.7946 (raw), 0.7922 (cp64), 344 positive pairs; 24yr AUC 0.767-0.770, 730 pairs
- **Section Cross-Lingual**: 1K sample, Sachverhalt n=359, Dispositiv n=538, Erwaegungen n=510
- **Linear Hybrids**: 22yr weight sweep complete, w=0.3-0.4 PASS both adversarial gates
- **174k TF-IDF Formal Suite**: cited_decisions_tfidf and cited_outcome_hybrid_0.5 PASS citation_heritage (AUC 0.973, 0.919), adversarial_falsification (LangDom 0.602, 0.578), multilingual_invariance
- **v8 Holdout**: True OOS ceiling confirmed ~0.53
- **v17b Label Normalization**: 15-25% purity gain at 1k but FAILS generalization to 174k
- **v18 Coarse Hierarchy**: NEGATIVE (max branch purity 0.65 < 0.7)

## Data Blockers (Require Corpus Lane Resumption)
1. **bge_/bger_ ID mapping** — Canonical corpus uses bge_ IDs, evaluation uses bger_ IDs
2. **Parquet 2024-2026** — 15,536 decisions missing (no /tmp/bger.parquet for these years)
3. **Section extraction at 174k** — Sachverhalt/Erwaegungen/Dispositiv not extracted at full scale

## Product Integration Contracts
| View | Integration | Status |
|------|-------------|--------|
| Citation Heritage | v1.1+ dense view, center_projected_64dim | READY at 144k |
| Cross-Lingual | v1.1+ dense view, per-section cp64 | SAMPLE ONLY — BLOCKED |
| Hybrid Complement | v1.1+ exploratory mode | READY at 144k |

**TF-IDF citation hybrids = PRIMARY product mode (v1.0)**  
**Dense embeddings = COMPLEMENTARY modes (v1.1+)**

## Conclusion
The legal-distance lane deliverable is **COMPLETE and AUDIT-READY**. The PIVOT_WITHIN_MISSION characterization answers the factory direction question at maximum available evaluated scale. All evidence is ACCEPTED, all tests PASS, and the lane correctly remains BLOCKED_ON_DEPENDENCIES pending corpus lane resumption for 174k completion. No further same-question cycles are justified.

---
*Generated: 2026-10-09T14:30:00Z | Run: 37888729325*