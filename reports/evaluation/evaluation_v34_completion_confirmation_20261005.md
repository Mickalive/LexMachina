# Evaluation Lane v34 — Completion Confirmation

**Date:** 2026-10-05  
**Direction Version:** 34  
**Run ID:** `eval_174k_v34_baseline_and_dense_criteria_20261003`  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** COMPLETE  
**Continue Recommended:** false  

---

## Confirmation

The evaluation lane has **completed all work** for factory direction v34. The lane question has been fully answered:

> **Question:** Freeze TF-IDF 174k evaluation as production baseline; define acceptance criteria for dense embedding complementary views (citation heritage AUC > 0.75, cross_lang_same_branch > 0.2 for sachverhalt, cross_lang_same_branch > 0.1 for dispositiv).

---

## Accepted Findings

### 1. TF-IDF 174k Production Baseline — FROZEN

| Representation | Language Dominance | Jurist Preference | Both Gates |
|----------------|-------------------|-------------------|------------|
| cited_decisions_tfidf | 0.479 PASS | 0.714 PASS | ✅ |
| outcome_tfidf | 0.502 PASS | 0.655 PASS | ✅ |
| regeste_tfidf | 0.485 PASS | 0.632 PASS | ✅ |
| full_text_tfidf_light | 0.485 PASS | 0.708 PASS | ✅ |
| **cited_decisions_tfidf_outcome_hybrid_0.5** | **0.477 PASS** | **0.7345 PASS** | ✅ **BEST** |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.478 PASS | 0.7275 PASS | ✅ |
| regeste_full_text_hybrid_0.5 | 0.480 PASS | 0.720 PASS | ✅ |
| regeste_full_text_hybrid_0.7 | 0.482 PASS | 0.715 PASS | ✅ |

**Thresholds:** Language dominance < 0.85; Jurist preference > 0.5  
**Production Default:** `cited_decisions_tfidf_outcome_hybrid_0.5_174k` (JP=0.7345, LangDom=0.4773)

### 2. Dense Embedding Acceptance Criteria — DEFINED & VALIDATED

| Criterion | Threshold | 22yr/144k Evidence | Status |
|-----------|-----------|-------------------|--------|
| Citation heritage AUC | > 0.75 | 0.79–0.80 (center_projected 64/128/768dim) | ✅ PASS |
| Cross-lang sachverhalt | > 0.2 | 0.282 | ✅ PASS |
| Cross-lang dispositiv | > 0.1 | 0.148 | ✅ PASS |
| Cross-lang erwaegungen | > 0.1 | 0.093 | ❌ FAIL |
| Jurist preference (primary) | > 0.5 | 0.39–0.43 (all scales) | ❌ FAIL |

**Conclusion:** Dense embeddings are **COMPLEMENTARY VIEWS ONLY** (citation heritage, cross-lingual alignment). They cannot serve as primary navigation (true OOS JP ceiling ~0.53 < 0.7 factory target).

### 3. Negative Results (Accepted)

| Finding | Evidence |
|---------|----------|
| v18 coarse hierarchy | Max branch purity 0.65 < 0.7 (even at 4-label level) |
| v17b label normalization 174k | Does NOT generalize (hierarchy=1.00x, zoom_fine=0.83–0.99x degradation) |
| Dense center_projected | FAILS jurist gate at ALL scales tested (3yr→22yr) |
| Linear hybrids | PASS adversarial but BELOW TF-IDF baseline (JP 0.66–0.67 vs 0.78–0.79) |

---

## State File

`state/evaluation.json` — Updated with:
- `evidence_tier`: "ACCEPTED"
- `cycle_status`: "COMPLETE"  
- `continue_recommended`: false
- `last_verified_run`: 37270030183 (2026-10-05T06:15:00Z)
- `verification_note`: "All 6 core regression tests PASSED. Dense acceptance criteria stand."

---

## Next Steps

**No further evaluation cycles on this question.** The lane is **BLOCKED** waiting for:

| Blocker | Owner | Impact |
|---------|-------|--------|
| BGE/bger ID mapping | Corpus lane | Cannot link 174k embeddings to evaluation metadata |
| Parquet 2022–2026 | Corpus lane | 29,520 decisions missing from 174k dense compute |
| Section extraction 174k | Corpus lane | Required for cross-lingual section-level criteria |

**When corpus lane delivers:** Legal-distance computes 174k dense embeddings → Evaluation runs formal suite against frozen criteria → If criteria met, dense views integrated as v1.1+ complementary modes.

---

## Evidence References

1. TF-IDF 174k formal suite: `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json`
2. Citation heritage 22yr: `results/evaluation/partial_dense_2000_2002/citation_heritage_22year_latest.json`
3. Section cross-lingual 22yr: `results/evaluation/partial_dense_2000_2002/section_crosslingual_eval_latest.json`
4. Dense 165k formal suite: `/tmp/lex_accepted/legal-distance/evaluation/results/174k/dense_165k_formal_suite/evaluation_165k_dense_formal_suite_latest.json`
5. TF-IDF 174k formal suite: `/tmp/lex_accepted/legal-distance/evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
6. Report: `reports/evaluation/v34_tfidf_baseline_and_dense_criteria_report.md`

---

**This evaluation cycle is COMPLETE.** The TF-IDF baseline is frozen; dense criteria are defined; blockers are explicitly assigned to corpus lane.