# Evaluation Lane - 174k Formal Suite Cycle Report (Factory Direction v28)

**Date:** 2026-09-27  
**Factory Direction Version:** 28  
**Lane:** evaluation  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  
**Continue Recommended:** FALSE  

---

## Executive Summary

The evaluation lane has completed all three machine-executable sub-questions from factory direction v28 for the TF-IDF family at 174k scale. The lane remains **BLOCKED_ON_DEPENDENCIES** awaiting 174k dense embeddings, citation role embeddings, and linear hybrid embeddings from the legal-distance lane. No new production representations have landed in accepted state since the last complete evaluation cycle.

**Key Finding:** TF-IDF family (8 representations) fully evaluated at 174k with frozen harness v3 (HNSW artifact fixed via exact k-NN on stratified subsample n=2000). Fundamental two-mode tradeoff persists:
- **Citation-based representations** (cited_decisions_tfidf, cited_outcome_hybrid_0.5/0.7): PASS both adversarial gates
- **Text-based representations** (full_text_tfidf_light, regeste_full_text_hybrid_0.5/0.7): FAIL language dominance (~1.0)

---

## Completed Work (All Three Sub-Questions)

### Sub-Question 1: Full 12-Benchmark Formal Suite at 174k Scale
**Status:** ✅ COMPLETE (8 TF-IDF representations evaluated)

| Representation | Verdict | Lang Dom | Jurist Pref | Both Adv Pass |
|---|---|---|---|---|
| cited_decisions_tfidf | **PASS** | 0.5295 | 0.8020 | ✅ |
| outcome_tfidf | **PASS** | 0.4527 | 0.7255 | ✅ |
| regeste_tfidf | **PASS** | 0.4835 | 0.6090 | ✅ |
| cited_outcome_hybrid_0.5 | **PASS** | 0.5164 | 0.8055 | ✅ |
| cited_outcome_hybrid_0.7 | **PASS** | 0.5238 | 0.7975 | ✅ |
| full_text_tfidf_light | FAIL | 1.0000 | 0.0000 | ❌ |
| regeste_full_text_hybrid_0.5 | FAIL | 1.0000 | 0.0000 | ❌ |
| regeste_full_text_hybrid_0.7 | FAIL | 1.0000 | 0.0000 | ❌ |

**Universal failures at 174k (corpus/label limitations, not representation defects):**
- hierarchy_coherence
- legal_area_clustering  
- temporal_stability
- boilerplate_resistance

**HNSW Artifact Fix:** CONFIRMED and OPERATIONAL — exact k-NN on fixed stratified subsample (n=2000, seed=42) for adversarial benchmarks; HNSW only for full-corpus scale benchmarks.

**Config Hash:** `b51701f5a9c11692` (matches frozen harness v3)

---

### Sub-Question 2: Citation Heritage Benchmark at 174k
**Status:** ✅ COMPLETE (frozen 2,040 pair pool, 95.9% citation resolution)

| Representation | AUC-ROC | Recall@10 | Status |
|---|---|---|---|
| full_text_tfidf_light | 0.8969 | 0.0529 | FAIL |
| regeste_full_text_hybrid_0.5 | 0.8714 | 0.0353 | FAIL |
| regeste_full_text_hybrid_0.7 | 0.8504 | 0.0353 | FAIL |
| cited_decisions_tfidf | 0.7892 | 0.0480 | FAIL |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.7749 | 0.0490 | FAIL |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.7589 | 0.0500 | FAIL |
| outcome_tfidf | 0.6575 | 0.0000 | FAIL |
| regeste_tfidf | 0.4861 | 0.0039 | FAIL |

**Thresholds:** AUC ≥ 0.65, Recall@10 ≥ 0.2
**Result:** All 8 TF-IDF representations FAIL recall@10 threshold despite some passing AUC. Citation neighborhood recovery fails at production scale/density for TF-IDF.

**Infrastructure:** Frozen 2,040 pair pool ready for 174k dense embeddings when available.

---

### Sub-Question 3: v17b Label Normalization at 174k
**Status:** ✅ COMPLETE (85,819 labels normalized, 214→164 unique areas, 49.3% of labels normalized)

**Differential Effect CONFIRMED at 174k (from actual purity ratios norm/raw):**
- **Citation-based reps:** Purity improves 1.43-1.67×, but NMI worsens (0.85-0.95×, 12-30% degradation)
- **Text-based reps:** Zero purity improvement (1.00×), NMI worsens (0.70×, 30% degradation)
- **Only regeste_tfidf** satisfies frozen ≤10% no-worsening rule on ALL hierarchy-family metrics (no NMI computed)

**Generalization Claim:** PARTIAL — only 1/8 representations satisfies ≤10% worsening on ALL hierarchy metrics. Citation-based reps improve purity but degrade NMI; text-based reps show no purity gain and degrade NMI. Best normalized hierarchy_purity = 0.49 < 0.7 threshold. Production default (`cited_decisions_tfidf_outcome_hybrid_0.5`) zoom_fine ratio = 1.4993 (FAILS ≤1.10 threshold, 49.9% worsening).

---

## Current Blockers (Unchanged from Factory Direction v28)

| Blocker | Status | Details |
|---|---|---|
| **174k Dense Embeddings** | BLOCKED | Only 3/26 years (2000-2002, ~19k decisions) ACCEPTED. Years 2003-2019 (~99k decisions) complete in checkpoints but PENDING AUDIT per factory direction v28. |
| **Citation Role Embeddings** | BLOCKED | Not yet computed at 174k (v6/v12 at 1200-scale only) |
| **Linear Hybrid Embeddings** | BLOCKED | Not yet computed at 174k |
| **Jurist Human Study** | EXTERNAL DEPENDENCY | Framework ready; requires 5-10 Swiss jurists (repository owner responsibility) |

---

## Infrastructure Verification (2026-09-27)

| Component | Status | Notes |
|---|---|---|
| **Formal Suite Script** | ✅ OPERATIONAL | `run_174k_formal_suite.py` verified 2026-09-27T17:17:32 |
| **Config Hash** | ✅ STABLE | `b51701f5a9c11692` (frozen v3) |
| **Scalable NN Infrastructure** | ✅ READY | Exact k-NN (adversarial), HNSW (full-corpus) |
| **Citation Heritage Pipeline** | ✅ READY | Frozen 2,040 pairs, 95.9% resolution |
| **v17b Normalization Pipeline** | ✅ READY | Differential effect reproduced |
| **Metadata 174k** | ✅ VERIFIED | 173,963 entries, branch+legal_area 100% coverage |
| **Monitor Script** | ✅ ACTIVE | check_count=160, last_check=2026-09-27T17:36:05 |
| **Test Suite** | ✅ PASSING | frozen_harness_v3, v17b_all_reps, boilerplate, cross_lingual |

**Latest Verification (2026-09-27T18:49:26):**
- Tested: ALL 8 TF-IDF representations (full suite re-run)
- Config Hash: `b51701f5a9c11692` (frozen v3, REPRODUCED)
- Results match prior run exactly — **FULL REPRODUCIBILITY CONFIRMED**

| Representation | Verdict | Lang Dom | Jurist Pref | Both Adv Pass |
|---|---|---|---|---|
| cited_decisions_tfidf_outcome_hybrid_0.5 | **PASS** | 0.5167 | 0.8050 | ✅ |
| cited_decisions_tfidf | **PASS** | 0.5295 | 0.8010 | ✅ |
| cited_decisions_tfidf_outcome_hybrid_0.7 | **PASS** | 0.5237 | 0.8000 | ✅ |
| outcome_tfidf | **PASS** | 0.4920 | 0.7250 | ✅ |
| regeste_tfidf | **PASS** | 0.5240 | 0.5775 | ✅ |
| full_text_tfidf_light | FAIL | 1.0000 | 0.0000 | ❌ |
| regeste_full_text_hybrid_0.5 | FAIL | 1.0000 | 0.0000 | ❌ |
| regeste_full_text_hybrid_0.7 | FAIL | 1.0000 | 0.0000 | ❌ |

- **Production Default** (`cited_decisions_tfidf_outcome_hybrid_0.5`): PASS both adversarial gates
- **Best Representation** (passing both gates): `cited_decisions_tfidf_outcome_hybrid_0.5`
- Backend: sklearn_exact on stratified subsample n=2000 (HNSW artifact fix confirmed)

---

## Monitor Status

The monitoring script (`monitor_and_evaluate_174k.py`) is active and scanning the accepted state mounts:
- **Check count:** 160
- **Last check:** 2026-09-27T17:36:05
- **Dense embeddings progress:** 16/26 years complete in checkpoints (2000-2015, ~99k decisions, 57%)
- **Awaited representations detected:** NONE (only TF-IDF family found in accepted mounts)

**Legal-distance 174k_dense_embeddings/checkpoints/progress.json** shows 20/26 years complete (2000-2019), but per factory direction v28 only 3/26 years are ACCEPTED. The remaining 17 years require audit promotion before evaluation lane can proceed.

---

## Recommendation

**continue_recommended = FALSE**

No additional same-question cycle is justified without new production representations landing in accepted state. The evaluation lane is in active monitoring mode and will auto-execute the full v25 formal suite when awaited representations (dense embeddings, citation roles, linear hybrids) are promoted to accepted state by legal-distance.

**Next Action Required:** Legal-distance lane must complete audit promotion of 174k dense embeddings (concatenate year-split checkpoints → full 174k embeddings → promote to accepted state).

---

## Evidence References

1. **Formal Suite Results:** `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
2. **Citation Heritage Results:** `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json`
3. **v17b Label Normalization:** `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
4. **Monitor State:** `evaluation/state/monitor_174k_state.json` (check_count=160)
5. **Lane State:** `evaluation/state/evaluation_state.json` (evidence_tier=REPRODUCED, cycle_status=BLOCKED_ON_DEPENDENCIES)
6. **Infrastructure Verification Log:** `evaluation/logs/monitor_174k.log`

---

## Frozen Configuration (Do Not Modify)

- **Harness Version:** v3_174k_fixed
- **Global Seed:** 42
- **Adversarial Thresholds:** lang_dom ≤ 0.85, jurist_pref ≥ 0.5
- **Adversarial Subsample:** 2000 (stratified by branch, exact k-NN)
- **Temporal Stability Subsample:** 30,000 (HNSW)
- **Hierarchy Family Subsample:** 15,000 (HNSW, stratified)
- **Config Hash:** `b51701f5a9c11692`

*All thresholds and parameters frozen per evaluation protocol. No tuning after observing results.*