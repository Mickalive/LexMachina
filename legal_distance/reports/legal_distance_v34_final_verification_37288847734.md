# Legal Distance Lane — Final Verification (GitHub Run 37288847734)

**Factory Direction v34 | Legal-Distance Lane | 2026-10-05**

---

## Verification Summary

✅ **ALL TESTS PASS** — `tests/legal_distance/test_complementary_role_v34.py` (8/8 tests)

✅ **STATE CONSISTENT** — `state/legal-distance.json` matches factory direction v34

✅ **AUDIT GATE PASS** — Latest audit `CYCLE_37286324799_GATE.json`: `gate=PASS`, `safe_to_integrate=true`

✅ **EVIDENCE TIER: ACCEPTED** — Characterization complete at maximum available evaluated scale

✅ **CONTINUE_RECOMMENDED: false** — No further same-question cycles justified

---

## PIVOT_WITHIN_MISSION Characterization Complete

The original hypothesis that dense embeddings would beat TF-IDF on jurist preference at scale is **falsified**. Dense embeddings (multilingual-e5 center_projected) **FAIL jurist gate at ALL scales** (JP 0.05–0.43).

However, dense embeddings are **NECESSARY and SUFFICIENT** for three complementary views:

| Complementary View | Minimal Sufficient Scale | Acceptance Status |
|--------------------|-------------------------|-------------------|
| **Citation Heritage Recovery** | 21yr / 137k (2000–2020) | ✅ PASSED (AUC 0.77–0.85 > 0.75) |
| **Section Cross-Lingual (Sachverhalt)** | 1K sample (359 decisions) | ✅ PASSED (cross_lang 0.282 > 0.2) |
| **Section Cross-Lingual (Dispositiv)** | 1K sample (538 decisions) | ✅ PASSED (cross_lang 0.150 > 0.1) |
| **Section Cross-Lingual (Erwaegungen)** | 1K sample (510 decisions) | ❌ FAILED (cross_lang 0.094 < 0.1) |
| **Linear Hybrid Complement** | 19yr / 122k (2000–2018) | ✅ PASSED adversarial (w=0.3–0.4) but JP < TF-IDF |

### Two-Mode Tradeoff (Fundamental)

| Representation | LangDom | JP | CiteIndep | Role |
|----------------|---------|-----|-----------|------|
| TF-IDF Citation Hybrids | ~0.48 | **~0.78** | ~14% | **PRIMARY** |
| Dense (center_projected) | ~0.83–0.98 | 0.05–0.43 | ~37% | **COMPLEMENTARY** |
| Linear Hybrids (w=0.3–0.4) | ~0.58–0.80 | 0.61–0.67 | Intermediate | **COMPLEMENTARY** |

**No single representation dominates all three metrics at any scale.** Multi-view architecture is required.

---

## Data Blockers (Corpus Lane Resumption Required)

| Blocker | Impact | Resolution Owner |
|---------|--------|------------------|
| **bge_ ↔ bger_ ID mapping** | Cannot align 174k evaluation corpus with canonical corpus | Corpus lane |
| **Parquet 2024–2026** | 15,536 decisions missing from 174k target | Corpus lane |
| **Section extraction at 174k** | Cross-lingual section evaluation blocked at full corpus density | Corpus lane |

**Note:** 2022–2023 embeddings **EXIST and PASS** citation heritage quality check (center_projected AUC > 0.75 at 24yr/158k with 730 pairs). Only 2024–2026 are genuinely missing.

---

## Product Integration Contract

### Primary Mode (v1.0 — Operational Now)
- **Method:** `cited_outcome_hybrid_0.5_174k` (TF-IDF citation + outcome hybrid)
- **Jurist Preference:** 0.735 (PASS adversarial)
- **Map Mode:** `center_projected_64dim_hierarchical` (TF-IDF hierarchical)
- **Status:** ✅ **OPERATIONAL at full 173,963 decisions**

### Complementary Modes (v1.1+ — Blocked on Corpus)
| View | Method | Acceptance Criteria | Status |
|------|--------|---------------------|--------|
| Citation Heritage | Dense center_projected_64 | AUC > 0.75 | ✅ Validated at 21–24yr; ⏳ Blocked at 174k |
| Cross-Lingual (Sachverhalt) | Dense section cp_64 | cross_lang_same_branch > 0.2 | ✅ Validated at sample; ⏳ Blocked at 174k |
| Cross-Lingual (Dispositiv) | Dense section cp_64 | cross_lang_same_branch > 0.1 | ✅ Validated at sample; ⏳ Blocked at 174k |
| Linear Hybrid Complement | Dense + TF-IDF concat w=0.3–0.4 | PASS adversarial + cross_lang improvement | ✅ Validated at 19–22yr; ⏳ Blocked at 174k |

---

## Evidence References (20 verified)

1. `legal_distance/results/174k_dense_embeddings/checkpoints/progress.json`
2. `legal_distance/results/174k_dense_embeddings/evaluation_22year_center_projected/`
3. `legal_distance/results/174k_dense_embeddings/linear_combinations_weight_sweep_22year/weight_sweep_22year_latest.json`
4. `legal_distance/results/174k_dense_embeddings/linear_combinations_22year/linear_citation_concat_22year_eval_latest.json`
4. `legal_distance/results/174k_dense_embeddings/linear_combinations_22year/linear_hybrid05_concat_22year_eval_latest.json`
5. `legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_latest.json`
6. `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_22year_latest.json`
7. `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_21year_latest.json`
8. `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_24year_latest.json`
9. `legal_distance/results/174k_dense_embeddings/legal_tfidf_bge/all_experiments_results.json`
10. `/tmp/lex_accepted/evaluation/results/evaluation/v25_174k_formal_suite/results/_suite_summary.json`
11. `/tmp/lex_accepted/evaluation/results/evaluation/v17b_label_normalization_all_reps/v17b_label_normalization_all_reps_latest.json`
12. `/tmp/lex_accepted/evaluation/results/evaluation/v18_coarse_hierarchy/v18_coarse_hierarchy_results.json`
13. `legal_distance/reports/legal_distance_v34_complementary_role.md`
14. `legal_distance/reports/legal_distance_v34_24year_scale_extension.md`
15. `legal_distance/results/dense_complementary_characterization/scale_characterization_results.json`
16. `/tmp/lex_accepted/evaluation/results/evaluation/partial_dense_2000_2002/section_crosslingual_eval_latest.json`
17. `legal_distance/reports/legal_distance_v34_complementary_characterization_complete.md`
18. `legal_distance/results/v6/comprehensive_validation/comprehensive_validation_all_results.json`
19. `legal_distance/results/v6/citation_role_integration/citation_role_integration_all_results.json`
20. `tests/legal_distance/test_complementary_role_v34.py` (ALL PASS)

---

## Audit Repairs Applied (Cycle 37239653489)

1. **comprehensive_validation JP anomaly fixed** — v5 baseline center_projected JP=0.4892 (consistent), ST variant labeled separately
2. **citation_role_integration fractal collapse fixed** — Degenerate base roles detected via overclustering, marked FAIL_DEGENERATE
3. **Overclustering gate implemented** — Fractal verdict requires `valid_representation=true` across all evaluation scripts

---

## Conclusion

**CHARACTERIZATION COMPLETE.** The legal-distance lane has fulfilled its PIVOT_WITHIN_MISSION mandate at factory direction v34. Dense embeddings are characterized as complementary to TF-IDF citation hybrids for the product's multi-view map.

**Lane Status:** `BLOCKED_ON_DEPENDENCIES` with `continue_recommended=false`

**Next Action:** Factory Director decision on successor question; corpus lane resumption for 174k completion.

---

*Verification run: GitHub 37288847734 | Evidence tier: ACCEPTED | All tests passing*