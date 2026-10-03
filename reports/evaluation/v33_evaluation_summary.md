# Evaluation Lane — Factory Direction v33 Summary

**Status**: BLOCKED_ON_DEPENDENCIES  
**Evidence Tier**: REPRODUCED  
**Continue Recommended**: false  
**Date**: 2026-10-03

---

## Executive Summary

The evaluation lane has completed all three deliverables from the factory direction question for **TF-IDF representations** at 174k scale. **Dense embeddings remain blocked** awaiting legal-distance promotion (only 3/26 years ACCEPTED).

| Deliverable | Status | Key Result |
|-------------|--------|------------|
| 174k formal suite (8 TF-IDF reps) | ✅ COMPLETE | All PASS adversarial gates; two-mode tradeoff persists |
| Citation heritage @ 174k | ✅ VALIDATED | Citation-based PASS (AUC 0.70-0.74); text-based FAIL (AUC 0.50-0.65) |
| v17b label normalization @ 174k | ✅ TESTED | 5-10x purity gains but NMI ↓ (regime shift from 1K) |
| v18 coarse hierarchy | ✅ NEGATIVE | 4-label branch max purity 0.65 < 0.7 threshold |
| Dense embeddings formal suite | ⏳ BLOCKED | 3/26 yr ACCEPTED (JP FAIL); 22/26 yr checkpointed pending audit |

---

## TF-IDF 174k Formal Suite Results (Frozen Harness v3)

**All 8 representations PASS both adversarial gates** (language dominance < 0.85, jurist pairwise > 0.5):

| Representation | LangDom | JuristPref | Verdict | Mode |
|----------------|---------|------------|---------|------|
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.477 | **0.735** | PASS | Citation/Outcome hybrid |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.478 | 0.728 | PASS | Citation/Outcome hybrid |
| cited_decisions_tfidf | 0.479 | 0.714 | PASS | Citation-based |
| full_text_tfidf_light | 0.485 | 0.708 | PASS | Text-based |
| outcome_tfidf | 0.502 | 0.655 | PASS | Outcome-based |
| regeste_tfidf | 0.485 | 0.632 | PASS | Text-based |
| regeste_full_text_hybrid_0.5 | 0.487 | 0.638 | PASS | Text-based |
| regeste_full_text_hybrid_0.7 | 0.489 | 0.634 | PASS | Text-based |

**Two-mode tradeoff confirmed at 174k:**
- **Citation/Outcome mode**: Low language dominance (~0.48), high jurist preference (~0.73), cite-independent ~14%
- **Text mode**: Higher language dominance (~0.49-0.99 on full text), lower jurist preference (~0.63-0.71)

**Full-corpus benchmarks (HNSW on subsamples):**
- Temporal stability: FAIL citation-based (0.36-0.38), PASS full_text (0.78)
- Hierarchy coherence: FAIL all (NMI < 0.03)
- Cluster coherence: FAIL all (branch purity ~0.3, language purity ~0.6)
- Cross-language retrieval: FAIL all (recall@10 ~0.14)
- Boilerplate resistance: FAIL all (score ~-0.8)

---

## Citation Heritage @ 174k (Frozen Pair Pool: 1,020 pos/neg)

| Representation | AUC-ROC | Status |
|----------------|---------|--------|
| cited_decisions_tfidf | 0.743 | ✅ PASS |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.729 | ✅ PASS |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.716 | ✅ PASS |
| regeste_full_text_hybrid_0.7 | 0.659 | ❌ FAIL |
| full_text_tfidf_light | 0.626 | ❌ FAIL |
| outcome_tfidf | 0.626 | ❌ FAIL |
| regeste_full_text_hybrid_0.5 | 0.636 | ❌ FAIL |
| regeste_tfidf | 0.503 | ❌ FAIL |

**Conclusion**: Citation signals recover citation heritage; text signals do not.

---

## v17b Label Normalization @ 174k

**Tested on 15k subsample (213 → 111 legal_area labels)**

| Representation | Hierarchy Purity Ratio | Zoom Fine Ratio | Legal Area Ratio | NMI Change |
|----------------|------------------------|-----------------|------------------|------------|
| cited_decisions_tfidf | 5.18x | 6.47x | 6.47x | -0.037 |
| outcome_tfidf | 10.07x | 10.07x | 10.07x | -0.013 |
| regeste_tfidf | 6.64x | 7.84x | 7.84x | -0.018 |
| full_text_tfidf_light | 4.70x | 5.89x | 5.89x | -0.035 |
| cited_outcome_hybrid_0.5 | 5.20x | 6.68x | 6.68x | -0.035 |
| cited_outcome_hybrid_0.7 | 5.20x | 6.60x | 6.60x | -0.038 |
| regeste_full_text_hybrid_0.5 | 5.09x | 6.31x | 6.31x | -0.027 |
| regeste_full_text_hybrid_0.7 | 5.53x | 7.27x | 7.27x | -0.012 |

**Key finding**: Purity gains 5-10x (vs 1.15-1.25x at 1K scale) but **NMI decreases** on normalized labels. Normalization merges labels that embeddings were separating. **Different regime at scale** — does not generalize in same-magnitude sense.

---

## v18 Coarse Hierarchy (Branch-Level: 4 Labels)

| Representation | Branch Purity | Branch NMI | Pass (≥0.7)? |
|----------------|---------------|------------|--------------|
| linear_citation_concat | **0.650** | 0.301 | ❌ |
| linear_citation_w3070 | 0.602 | 0.211 | ❌ |
| linear_citation_ridge | 0.564 | 0.156 | ❌ |
| center_projected_64dim | 0.519 | 0.065 | ❌ |
| cited_outcome_hybrid_0.5 | 0.474 | 0.004 | ❌ |
| linear_hybrid05_concat | 0.474 | 0.004 | ❌ |

**Conclusion**: Even at coarsest branch granularity (4 labels), hierarchy NOT recoverable. Fundamental limitation for TF-IDF/citation representations.

---

## Dense Embeddings Status

### ACCEPTED (3/26 years: 2000-2002, ~19,441 decisions)
- center_projected FAILS jurist gate at ALL scales (JP 0.04-0.43, LangDom 0.83-0.98)
- Cross-language: PASS (zero-shot NMI 0.23-0.32, language-specific NMI 0.30-0.34)
- Citation heritage: NOT TESTED at this scale (insufficient citation pairs in early years)

### CHECKPOINTED - PENDING AUDIT (22/26 years: 2000-2021, 144,443 decisions)
Legal-distance ran 165k formal suite:
- center_projected_64/768/128dim: **FAIL adversarial** (JP 0.39-0.43, LangDom 0.83-0.85)
- Citation heritage: **PASS** (AUC 0.79-0.85) — **BETTER than TF-IDF** (0.71-0.74)
- Linear hybrids (w=0.3-0.4): PASS adversarial at 22yr but **BELOW TF-IDF baseline** (JP 0.66-0.67 vs 0.78-0.79)
- Section cross-lingual: Sachverhalt superior (gap 0.187 vs 0.452 Erwaegungen)

### UNPROCESSED (4/26 years: 2022-2026, ~29,520 decisions)
**Blocker**: bge_ ↔ bger_ ID mapping missing + parquet files for 2022-2026 not available.

---

## Key Metrics vs Factory Targets

| Metric | Factory Target | Best Achieved | Status |
|--------|----------------|---------------|--------|
| Jurist Preference (OOS) | > 0.70 | ~0.53 (true OOS ceiling) | ❌ NOT MET |
| Language Dominance | < 0.85 | 0.48 (TF-IDF) / 0.83 (dense) | TF-IDF ✅ |
| Citation Heritage AUC | > 0.65 | 0.74 (TF-IDF) / 0.85 (dense) | ✅ MET |
| Branch Purity (4-label) | > 0.70 | 0.65 (linear_citation_concat) | ❌ NOT MET |
| Cross-lang Recall@10 | > 0.20 | 0.14 (all reps) | ❌ NOT MET |

---

## Recommendation

**No further evaluation cycles justified** until legal-distance promotes the 22-year (144k) dense embeddings to ACCEPTED. The evaluation harness is frozen at v3 and ready to run on any new representations that land.

**Next factory decision**: PIVOT_WITHIN_MISSION — either (a) resolve data blockers for 174k dense embeddings, or (b) accept TF-IDF citation/outcome hybrid as production default and advance fractal-map/product with current evidence.

---

## Evidence References

1. `results/evaluation/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
2. `results/evaluation/174k_citation_heritage/citation_heritage_174k_tfidf_latest.json`
3. `results/evaluation/v17b_174k_generalization/v17b_174k_generalization_latest.json`
4. `results/evaluation/v18_coarse_hierarchy/v18_coarse_hierarchy_latest.json`
5. `results/evaluation/partial_dense_2000_2002/evaluation_partial_dense_latest.json`
6. `legal_distance/results/174k/dense_165k_formal_suite/evaluation_165k_dense_formal_suite_latest.json`
7. `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_22year_latest.json`