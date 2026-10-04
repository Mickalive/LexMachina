# Evaluation Lane v34 — Regression Verification (Run 37231337758)

**Run ID:** `eval_v34_regression_verification_20261004`  
**Factory Direction Version:** 34  
**Date:** 2026-10-04  
**Evidence Tier:** ACCEPTED (regression verification)  
**Cycle Status:** MONITORING — No new cycle, baseline re-verified  

---

## Executive Summary

This report documents a **fresh regression verification** of the frozen TF-IDF 174k production baseline (Factory Direction v34). The evaluation lane completed its v34 cycle with `continue_recommended: false` and entered monitoring mode pending corpus lane resumption for 174k dense embeddings. This verification confirms:

1. ✅ **Frozen adversarial baseline STILL HOLDS** — All 8 TF-IDF representations PASS both adversarial gates on fresh stratified subsample (n=2000, seed=42, exact k-NN).
2. ✅ **No new 174k dense embeddings detected** — Monitor check #295 confirms all 12 awaited representations remain unavailable.
3. ✅ **Data blockers unchanged** — bge_/bger_ ID mapping + parquet 2022-2026 still block 174k dense embedding completion.
4. ✅ **Lane state consistent** — `evidence_tier=ACCEPTED`, `cycle_status=COMPLETE`, `continue_recommended=false`.

---

## 1. Fresh Adversarial Verification — All 8 TF-IDF Representations

**Method:** Exact k-NN on stratified subsample n=2000, seed=42, sklearn exact search (cosine)  
**Config:** Frozen harness v3 thresholds (LangDom < 0.85, Jurist > 0.5)  
**Date:** 2026-10-04

| Representation | Language Dominance | Jurist Preference | Both Gates PASS |
|---|---|---|---|
| `cited_decisions_tfidf` | 0.3953 | 0.7891 | ✅ |
| `cited_decisions_tfidf_outcome_hybrid_0.5` | **0.3976** | **0.7929** | ✅ **PRODUCTION DEFAULT** |
| `cited_decisions_tfidf_outcome_hybrid_0.7` | 0.3927 | 0.7948 | ✅ |
| `outcome_tfidf` | 0.3099 | 0.8207 | ✅ |
| `regeste_tfidf` | 0.2777 | 0.8945 | ✅ |
| `full_text_tfidf_light` | 0.4871 | 0.7517 | ✅ |
| `regeste_full_text_hybrid_0.5` | 0.4868 | 0.7469 | ✅ |
| `regeste_full_text_hybrid_0.7` | 0.4865 | 0.7450 | ✅ |

**All 8 PASS both gates:** Language Dominance range [0.278, 0.487] < 0.85 threshold; Jurist Preference range [0.745, 0.895] > 0.5 threshold.

**Production Baseline Reconfirmed:**
- `PRODUCT_SERVING_DEFAULT` = `cited_decisions_tfidf_outcome_hybrid_0.5`
- `COMBINATION_MODE` = `linear_hybrid05_concat`
- `DEFAULT_MAP_MODE` = `center_projected_64dim_hierarchical`
- Audit Gate CYCLE_37073590337: `safe_to_integrate=true`

> **Note:** Values differ slightly from the frozen baseline (exact_adversarial_all_tfidf.json: LangDom 0.4895, JP 0.7265) because the frozen baseline used the full `valid_indices` filtering from `prepare_metadata()` and exact k=20/k=10 parameters on the full valid set. This verification uses a stratified subsample of 2000 decisions with k=20/k=10. Gate outcomes are **identical** (all PASS).

---

## 2. Monitor Check #295 — No New 174k Dense Embeddings

**Monitor State:** `evaluation/state/monitor_174k_state.json`  
**Check Count:** 295  
**Last Check:** 2026-10-04T20:26:XX

### Representation Readiness Status

| Category | Representation | Status |
|---|---|---|
| **TF-IDF (COMPLETED)** | 8/8 representations | ✅ All evaluated, frozen |
| **Dense (AWAITED)** | `center_projected_768dim` | ❌ Not available |
|  | `center_projected_64dim` | ❌ Not available |
|  | `center_projected_128dim` | ❌ Not available |
|  | `linear_metric_epoch4` | ❌ Not available |
|  | `mahalanobis_metric_epoch4` | ❌ Not available |
|  | `hybrid_stabilized_epoch1` | ❌ Not available |
|  | `hybrid_v2_epoch3` | ❌ Not available |
| **Citation Roles (AWAITED)** | `citation_role_citing_alpha0.3` | ❌ Not available |
|  | `citation_role_following_alpha0.3` | ❌ Not available |
|  | `citation_role_criticizing_alpha0.3` | ❌ Not available |
| **Linear Hybrids (AWAITED)** | `linear_citation_concat` | ❌ Not available |
|  | `linear_hybrid05_concat` | ❌ Not available |

### Data Blockers (Unchanged)

| Blocker | Owner | Impact |
|---|---|---|
| bge_/bger_ ID mapping | Corpus lane | No mapping between canonical (bge_) and evaluation (bger_) IDs |
| Parquet 2022-2026 | Corpus lane | 29,520 decisions missing from 144k checkpoint |
| Section extraction 174k | Corpus lane | Sachverhalt/Erwaegungen/Dispositiv not extracted at 174k scale |
| GPU unavailable | Legal-distance | No BGE/multilingual-e5 finetuning at scale |

**Legal-distance progress:** 22/26 years (2000-2021) checkpointed (144,443 decisions), only 3/26 years (2000-2002) ACCEPTED. Center-projected concatenation of 22 years not performed. Years 2022-2026 not yet processed.

---

## 3. Dense Embedding Acceptance Criteria — Still Validated Against 22-Year Evidence

The acceptance criteria defined in Factory Direction v34 remain validated against the 22-year/144k checkpoint evidence (no new evidence available):

| Capability | Metric | Threshold | 22-Year Evidence | Status |
|---|---|---|---|---|
| **Citation Heritage** | AUC-ROC | > 0.75 | center_projected: 0.7916-0.7946 | ✅ PASS |
| **Cross-Lingual (Sachverhalt)** | cross_lang_same_branch@10 | > 0.20 | center_projected: 0.2816 | ✅ PASS |
| **Cross-Lingual (Dispositiv)** | cross_lang_same_branch@10 | > 0.10 | center_projected: 0.148-0.150 | ✅ PASS |
| **Cross-Lingual (Erwaegungen)** | cross_lang_same_branch@10 | > 0.10 | center_projected: 0.093-0.094 | ❌ FAIL |
| **Jurist Preference (Primary)** | JP score | > 0.50 | center_projected: 0.39-0.43 | ❌ FAIL |

**Interpretation unchanged:** Dense embeddings are **COMPLEMENTARY VIEWS ONLY** — they exceed TF-IDF on citation heritage and cross-lingual sachverhalt/dispositiv, but FAIL jurist preference gate at ALL scales. True OOS JP ceiling ~0.53 < 0.7 factory target.

---

## 4. State Consistency

**Lane State:** `state/evaluation.json` (unchanged)
```json
{
  "lane": "evaluation",
  "direction_version": 34,
  "evidence_tier": "ACCEPTED",
  "cycle_status": "COMPLETE",
  "continue_recommended": false,
  "accepted_run_id": "eval_174k_v34_baseline_and_dense_criteria_20261003",
  "last_verified_run": 37227561960,
  "last_verified_timestamp": "2026-10-04T19:23:21.000000Z"
}
```

**Monitor State:** Updated with check #295
```json
{
  "check_count": 295,
  "last_verification": "monitor_check295_20261004T2026_frozen_baseline_verified_all_8_tfidf_pass_no_new_174k_dense_reps_bge_bger_mapping_blocked_continue_recommended_false"
}
```

**All evidence references remain valid and accessible.**

---

## 5. Recommendations — No Change

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
- Continue honest null monitoring until dense embeddings land

---

## 6. Conclusion

The TF-IDF 174k production baseline remains **frozen and verified**. The evaluation lane v34 cycle is **complete and closed**. This regression verification (Run 37231337758) confirms no drift in the frozen baseline and no new dense embeddings available. The lane remains in monitoring mode pending corpus lane resumption.

**No additional work required on this factory direction question.**

---

*Generated 2026-10-04 as regression verification for GitHub run 37231337758.*
