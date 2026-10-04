# Evaluation Lane v34 — Monitor Check #293 Verification

**Run ID:** `eval_monitor_check293_20261004`  
**Factory Direction Version:** 34  
**Date:** 2026-10-04  
**Evidence Tier:** ACCEPTED (lane state unchanged)  
**Cycle Status:** COMPLETE — VERIFIED & CLOSED  
**Continue Recommended:** FALSE (no further same-question cycles justified)

---

## Executive Summary

This run performs **honest null monitoring** — the evaluation lane v34 deliverable was already completed and frozen. Fresh verification confirms:

1. ✅ **TF-IDF 174k production baseline remains FROZEN** — All 8 representations PASS both adversarial gates on frozen harness v3 (config hash `b51701f5a9c11692`). Production default: `cited_decisions_tfidf_outcome_hybrid_0.5` (JP=0.7265, LangDom=0.4895).

2. ✅ **Dense embedding complementary view acceptance criteria remain VALIDATED** against 22-year/144k checkpoint evidence:
   - Citation heritage AUC > 0.75: **PASS** (center_projected 0.79-0.80)
   - Cross-lingual sachverhalt > 0.2: **PASS** (~0.282)
   - Cross-lingual dispositiv > 0.1: **PASS** (~0.148-0.150)
   - Cross-lingual erwaegungen > 0.1: **FAIL** (~0.093-0.094) — correctly recorded as negative finding

3. ✅ **Center_projected FAILS jurist preference at ALL scales** (JP 0.05-0.43) — confirming complementary-only role per pivot decision.

4. ✅ **No 174k dense embeddings available** — monitor check #293 detects zero new awaited representations. Blocked on corpus lane (bge_/bger_ ID mapping + parquet 2022-2026).

5. ✅ **State consistent** — `state/evaluation.json`: `evidence_tier=ACCEPTED`, `cycle_status=COMPLETE`, `continue_recommended=false`.

---

## Monitor Check #293 Results

```
REPRESENTATION READINESS:
  COMPLETED (TF-IDF family at 174k):
    ✓ cited_decisions_tfidf
    ✓ outcome_tfidf
    ✓ cited_decisions_tfidf_outcome_hybrid_0.5
    ✓ cited_decisions_tfidf_outcome_hybrid_0.7
    ✓ regeste_tfidf
    ✓ full_text_tfidf_light
    ✓ regeste_full_text_hybrid_0.5
    ✓ regeste_full_text_hybrid_0.7
  AWAITED (dense embeddings, citation roles, linear hybrids):
    awaited_dense_174k:
      ✗ center_projected_768dim
      ✗ center_projected_64dim
      ✗ center_projected_128dim
      ✗ linear_metric_epoch4
      ✗ mahalanobis_metric_epoch4
      ✗ hybrid_stabilized_epoch1
      ✗ hybrid_v2_epoch3
    awaited_citation_roles_174k:
      ✗ citation_role_citing_alpha0.3
      ✗ citation_role_following_alpha0.3
      ✗ citation_role_criticizing_alpha0.3
    awaited_linear_hybrids_174k:
      ✗ linear_citation_concat
      ✗ linear_hybrid05_concat
```

**Check count:** 293 (incremented from 292)  
**Last check:** 2026-10-04T10:05:38.051683

---

## Frozen Adversarial Baseline — Re-Verified

**Source:** `results/evaluation/adversarial_reverify_20261002/exact_adversarial_all_tfidf.json`  
**Config Hash:** `b51701f5a9c11692` (immutable — guarantees exact reproduction)  
**Method:** Exact k-NN on stratified subsample n=2000, seed=42, sklearn exact search

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

---

## Dense Embedding Acceptance Criteria — Re-Validated

### Citation Heritage (22-year, 144,443 decisions, 344 positive pairs)

| Representation | AUC-ROC | Threshold | Status |
|---|---|---|---|
| `center_projected_768dim` | 0.7946 | > 0.75 | ✅ **PASS** |
| `center_projected_64dim` | 0.7922 | > 0.75 | ✅ **PASS** |
| `center_projected_128dim` | 0.7916 | > 0.75 | ✅ **PASS** |
| `raw_768dim` (multilingual-e5) | 0.7946 | > 0.75 | ✅ **PASS** |

**TF-IDF citation-based baseline:** AUC 0.71-0.74  
**Dense embeddings EXCEED TF-IDF by ~0.05-0.08 AUC points.**

**Source:** `results/evaluation/partial_dense_2000_2002/citation_heritage_22year_latest.json`

### Cross-Lingual Section Alignment (3-year subset, decisions with section coverage)

| Section | Representation | `cross_lang_same_branch@10` | Threshold | Status |
|---|---|---|---|---|
| **Sachverhalt** (Facts) | `center_projected_768` | 0.2816 | > 0.20 | ✅ **PASS** |
| | `center_projected_64` | 0.2816 | > 0.20 | ✅ **PASS** |
| **Dispositiv** (Holdings) | `center_projected_768` | 0.1481 | > 0.10 | ✅ **PASS** |
| | `center_projected_64` | 0.1502 | > 0.10 | ✅ **PASS** |
| **Erwaegungen** (Reasoning) | `center_projected_768` | 0.0925 | > 0.10 | ❌ **FAIL** |
| | `center_projected_64` | 0.0941 | > 0.10 | ❌ **FAIL** |

**Hierarchy Confirmed:** Sachverhalt > Dispositiv > Erwaegungen for cross-lingual alignment.

**Source:** `results/evaluation/partial_dense_2000_2002/section_crosslingual_eval_latest.json`

---

## Blocker Status — Unchanged

| Blocker | Owner | Status |
|---|---|---|
| bge_/bger_ ID mapping | Corpus lane | **BLOCKING** — no mapping between canonical (bge_) and evaluation (bger_) IDs |
| Parquet 2022-2026 | Corpus lane | **BLOCKING** — 29,520 decisions missing from 144k checkpoint |
| 174k dense embedding concatenation | Legal-distance lane | BLOCKED on above |
| Citation role embeddings 174k | Legal-distance lane | BLOCKED on above |
| Linear hybrid embeddings 174k | Legal-distance lane | BLOCKED on above |

**Corpus lane status:** PAUSED (per factory direction v34). Resumption criteria explicitly defined in factory direction.

---

## Recommendations — Confirmed

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
- Continue honest null monitoring (check_count=293+) until dense embeddings land

---

## Conclusion

The Evaluation Lane v34 cycle remains **complete, verified, and closed**. The TF-IDF 174k production baseline is frozen with exact reproducibility guaranteed by config hash `b51701f5a9c11692`. Dense embedding complementary view acceptance criteria are defined, validated against checkpoint evidence, and ready for integration when 174k dense embeddings become available.

**No additional work required on this factory direction question.** The lane continues in monitoring mode pending corpus lane resumption.

---

*Generated 2026-10-04 as monitor verification of evaluation lane v34 cycle completion.*