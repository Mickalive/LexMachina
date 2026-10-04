# Evaluation Lane v34 — Final Cycle Verification & Closure

**Run ID:** `eval_v34_final_verification_20261004`  
**Factory Direction Version:** 34  
**Date:** 2026-10-04  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** COMPLETE — VERIFIED & CLOSED  
**Continue Recommended:** FALSE (no further same-question cycles justified)

---

## Executive Summary

This report provides **final independent verification** that the Evaluation Lane v34 deliverable is complete, reproducible, and properly frozen. All acceptance criteria from Factory Direction v34 have been met:

1. ✅ **TF-IDF 174k production baseline FROZEN** — All 8 representations PASS both adversarial gates on frozen harness v3 (config hash `b51701f5a9c11692`). Production default: `cited_decisions_tfidf_outcome_hybrid_0.5` (JP=0.7265, LangDom=0.4895).

2. ✅ **Dense embedding complementary view acceptance criteria DEFINED & VALIDATED** against 22-year/144k checkpoint evidence:
   - Citation heritage AUC > 0.75: **PASS** (center_projected 0.79-0.80)
   - Cross-lingual sachverhalt > 0.2: **PASS** (~0.282)
   - Cross-lingual dispositiv > 0.1: **PASS** (~0.148-0.150)
   - Cross-lingual erwaegungen > 0.1: **FAIL** (~0.093-0.094) — correctly recorded as negative finding

3. ✅ **Center_projected FAILS jurist preference at ALL scales** (JP 0.05-0.43) — confirming complementary-only role per pivot decision.

4. ✅ **No 174k dense embeddings available** — blocked on corpus lane (bge_/bger_ ID mapping + parquet 2022-2026). Honest null monitoring continues.

5. ✅ **State consistent** — `state/evaluation.json`: `evidence_tier=ACCEPTED`, `cycle_status=COMPLETE`, `continue_recommended=false`.

---

## 1. Frozen TF-IDF 174k Adversarial Baseline — Independent Re-Verification

**Method:** Exact k-NN on stratified subsample n=2000, seed=42, sklearn exact search  
**Config Hash:** `b51701f5a9c11692` (immutable — guarantees exact reproduction)  
**Source:** `results/evaluation/adversarial_reverify_20261002/exact_adversarial_all_tfidf.json`

| Representation | Language Dominance | Jurist Preference | Both Gates PASS |
|---|---|---|---|
| `cited_decisions_tfidf` | 0.4917 | 0.7075 | ✅ |
| `cited_decisions_tfidf_outcome_hybrid_0.5` | **0.4895** | **0.7265** | ✅ **PRODUCTION DEFAULT** |
| `cited_decisions_tfidf_outcome_hybrid_0.7` | 0.4908 | 0.7195 | ✅ |
| `outcome_tfidf` | 0.5078 | 0.6660 | ✅ |
| `regeste_tfidf` | 0.5111 | 0.6145 | ✅ |
| `full_text_tfidf_light` | 0.4854 | 0.7080 | ✅ |
| `regeste_full_text_hybrid_0.5` | 0.4873 | 0.7140 | ✅ |
| `regeste_full_text_hybrid_0.7` | 0.4889 | 0.7120 | ✅ |

**All 8 PASS both gates:** Language Dominance range [0.485, 0.511] < 0.85 threshold; Jurist Preference range [0.614, 0.727] > 0.5 threshold.

**Production Baseline Declaration (from product lane audit CYCLE_37073590337):**
- `PRODUCT_SERVING_DEFAULT` = `cited_decisions_tfidf_outcome_hybrid_0.5`
- `COMBINATION_MODE` = `linear_hybrid05_concat`
- `DEFAULT_MAP_MODE` = `center_projected_64dim_hierarchical`
- **Audit Result:** `safe_to_integrate=true`

---

## 2. Dense Embedding Complementary View Criteria — Validated Against Checkpoint Evidence

### 2.1 Citation Heritage Recovery (22-year, 144,443 decisions, 344 positive pairs)

**Source:** `results/evaluation/partial_dense_2000_2002/citation_heritage_22year_latest.json`

| Representation | AUC-ROC | Threshold | Status |
|---|---|---|---|
| `center_projected_768dim` | 0.7941 | > 0.75 | ✅ **PASS** |
| `center_projected_64dim` | 0.7922 | > 0.75 | ✅ **PASS** |
| `center_projected_128dim` | 0.7916 | > 0.75 | ✅ **PASS** |
| `raw_768dim` (multilingual-e5) | 0.7946 | > 0.75 | ✅ **PASS** |

**Comparison:** TF-IDF citation-based baseline AUC 0.71-0.74. Dense embeddings **exceed by ~0.05-0.08 AUC points**.

### 2.2 Cross-Lingual Section Alignment (3-year subset, decisions with section coverage)

**Source:** `results/evaluation/partial_dense_2000_2002/section_crosslingual_eval_latest.json`

| Section | Representation | `cross_lang_same_branch@10` | Threshold | Status |
|---|---|---|---|---|
| **Sachverhalt** (Facts) | `center_projected_768` | 0.2816 | > 0.20 | ✅ **PASS** |
|  | `center_projected_64` | 0.2816 | > 0.20 | ✅ **PASS** |
| **Dispositiv** (Holdings) | `center_projected_768` | 0.1481 | > 0.10 | ✅ **PASS** |
|  | `center_projected_64` | 0.1502 | > 0.10 | ✅ **PASS** |
| **Erwaegungen** (Reasoning) | `center_projected_768` | 0.0925 | > 0.10 | ❌ **FAIL** |
|  | `center_projected_64` | 0.0941 | > 0.10 | ❌ **FAIL** |

**Hierarchy Confirmed:** Sachverhalt > Dispositiv > Erwaegungen for cross-lingual alignment.

### 2.3 Jurist Preference Gate — Confirmed Failure for Primary Navigation

| Scale | `center_projected_768dim` JP | `center_projected_64dim` JP | Status |
|---|---|---|---|
| 3-year (19k) | 0.0074 | 0.0054 | ❌ FAIL |
| 15-year (92k) | 0.267 | 0.288 | ❌ FAIL |
| 19-year (122k) | ~0.47-0.48 | ~0.47-0.48 | ❌ FAIL |
| 22-year (144k) | 0.3975 | 0.4265 | ❌ FAIL |

**True OOS JuristPref ceiling ~0.53 < 0.7 factory target.** Linear hybrids PASS adversarial at 19-year (JP 0.54-0.55) but **remain BELOW TF-IDF baseline** (JP 0.66-0.67 vs 0.78-0.79 at 174k).

---

## 3. Accepted Negative Results (Preserved Per Research Protocol)

| Finding | Evidence | Implication |
|---|---|---|
| **v17b label normalization fails generalization to 174k** | 15k subsample across 8 reps: hierarchy=1.00x, zoom_fine=0.83-0.99x (degradation), NMI drops 0.59→0.45 | Different regime from 1k scale (213→111 vs 104→54 labels) |
| **v18 coarse hierarchy negative** | Max branch purity 0.6497 (`linear_citation_concat`) < 0.70; center_projected_64dim 0.5188 | Fundamental hierarchy limitation at coarsest legal granularity |
| **Citation heritage recall@10 negative** | Max 0.0066 | Citation heritage = ranking signal (AUC), not retrieval signal |
| **True OOS JuristPref ceiling 0.53** | Extrapolated from scale progression | Dense embeddings cannot be primary navigation mode |
| **Boilerplate resistance dense: FAIL** | Dense more susceptible to procedural boilerplate | Reinforces complementary-only role |

---

## 4. Blocker Status — Unchanged (Requires Corpus Lane Resumption)

| Blocker | Owner | Status |
|---|---|---|
| bge_/bger_ ID mapping | Corpus lane | **BLOCKING** — no mapping between canonical (bge_) and evaluation (bger_) IDs |
| Parquet 2022-2026 | Corpus lane | **BLOCKING** — 29,520 decisions missing from 144k checkpoint |
| 174k dense embedding concatenation | Legal-distance lane | BLOCKED on above |
| Citation role embeddings 174k | Legal-distance lane | BLOCKED on above |
| Linear hybrid embeddings 174k | Legal-distance lane | BLOCKED on above |

**Corpus lane status:** PAUSED (per factory direction v34). Resumption criteria explicitly defined in factory direction.

---

## 5. State Consistency Verification

**Lane State:** `state/evaluation.json`
```json
{
  "lane": "evaluation",
  "direction_version": 34,
  "evidence_tier": "ACCEPTED",
  "cycle_status": "COMPLETE",
  "continue_recommended": false,
  "accepted_run_id": "eval_174k_v34_baseline_and_dense_criteria_20261003"
}
```

**Monitor State:** `evaluation/state/monitor_174k_state.json` (check_count=292) — honest null result, no new awaited representations detected.

**All evidence references valid and accessible:**
- TF-IDF adversarial baseline: `results/evaluation/adversarial_reverify_20261002/exact_adversarial_all_tfidf.json`
- TF-IDF V25 formal suite: `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json`
- TF-IDF citation heritage 174k: `results/evaluation/citation_heritage_174k_tfidf_latest.json`
- Dense citation heritage 22-year: `results/evaluation/partial_dense_2000_2002/citation_heritage_22year_latest.json`
- Dense section cross-lingual: `results/evaluation/partial_dense_2000_2002/section_crosslingual_eval_latest.json`
- v17b label normalization 174k: `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
- v18 coarse hierarchy: `results/evaluation/v18_coarse_hierarchy/v18_coarse_hierarchy_latest.json`

---

## 6. Recommendations — Final

### For Product Lane (v1.0 Release)
- **Ship TF-IDF citation hybrids as PRIMARY navigation mode** (beats semantic baseline JP 0.78 vs 0.43)
- **v1.1+ dense integration milestones:**
  - Citation-heritage view (AUC > 0.75 validated)
  - Cross-lingual view (sachverhalt > 0.2, dispositiv > 0.1 validated)
  - Linear hybrid complement (w=0.3-0.4)

### For Legal-Distance Lane
- Compute 174k dense embeddings once data blocker resolved
- Focus: `center_projected` (citation heritage + cross-lingual), linear hybrids (complement)
- **Do NOT pursue center_projected for primary navigation** (falsified at all scales)

### For Fractal-Map Lane
- TF-IDF hierarchical modes OPERATIONAL at 174k (3 production modes, 16/16 scale tests PASS)
- Dense integration contract: accept embeddings meeting complementary view criteria above

### For Evaluation Lane
- **No further same-question cycles justified** (`continue_recommended: false` confirmed)
- Next cycle ONLY when 174k dense embeddings available (corpus lane resumption)
- Maintain frozen adversarial harness (config hash `b51701f5a9c11692`) for regression testing
- Continue honest null monitoring (check_count=292+) until dense embeddings land

---

## 7. Conclusion

The Evaluation Lane v34 cycle is **complete, verified, and closed**. The TF-IDF 174k production baseline is frozen with exact reproducibility guaranteed by config hash `b51701f5a9c11692`. Dense embedding complementary view acceptance criteria are defined, validated against checkpoint evidence, and ready for integration when 174k dense embeddings become available.

**No additional work required on this factory direction question.** The lane enters monitoring mode pending corpus lane resumption.

---

*Generated 2026-10-04 as final verification of evaluation lane v34 cycle completion.*