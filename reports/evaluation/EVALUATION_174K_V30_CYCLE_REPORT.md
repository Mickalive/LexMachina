# Evaluation Lane Cycle Report — Factory Direction v30

**Date:** 2026-09-27  
**Run ID:** `eval_174k_formal_suite_v30_20260927_01`  
**Cycle Status:** `BLOCKED_ON_DEPENDENCIES`  
**Evidence Tier:** `REPRODUCED`  
**Continue Recommended:** `false`

---

## Executive Summary

The evaluation lane has completed all available work at 174k scale and is blocked awaiting transformed dense representations from the legal-distance lane. No new representations have landed since the last evaluation cycle.

**Key Status:**
- ✅ **TF-IDF family (8 representations):** COMPLETE and EVALUATED at full 174k scale
- ✅ **Raw multilingual-e5 768dim (2000-2015, ~99k decisions):** EVALUATED — FAILS adversarial benchmarks (language dominance 0.9855)
- ⏳ **Transformed dense embeddings (center_projected, metric-learned, hybrids):** AWAITED — legal-distance has 16/26 years of raw embeddings complete (2000-2015), but transformed representations not yet available at 174k scale
- ⏳ **Citation roles (174k):** AWAITED
- ⏳ **Linear hybrids (174k):** AWAITED
- ✅ **Citation heritage benchmark:** COMPLETE for all 8 TF-IDF representations on frozen 137k pair pool
- ✅ **v17b label normalization test:** COMPLETE at 174k scale — only 2/8 representations satisfy frozen uniformity rule
- ✅ **HNSW artifact fix:** CONFIRMED and DEPLOYED — exact k-NN on stratified subsample for adversarial benchmarks
- ✅ **Monitor infrastructure:** OPERATIONAL — actively scanning for new representations

---

## Completed Work This Cycle

### 1. Monitor Scan Verification
Ran `monitor_and_evaluate_174k.py` to scan accepted state mounts for new 174k representations.

**Results:**
- **Found:** 8 TF-IDF embeddings in fractal-map mount (already evaluated)
- **Not found:** Any new transformed dense embeddings, citation roles, or linear hybrids at 174k scale in legal-distance mount
- **Confirmed:** Legal-distance has 16/26 years (2000-2015) of raw multilingual-e5 embeddings complete per progress.json

### 2. State File Updates
Updated both evaluation state files to reflect factory direction v30:
- `state/evaluation.json` — main lane state with `direction_version: 30`
- `evaluation/state/monitor_174k_state.json` — monitor state with corrected dense embeddings progress (61.5% year completion, 57% decision completion)

---

## Evidence Summary (Frozen, Reproduced)

### Subquestion 1: 12-Benchmark Formal Suite at 174k Scale
**Status:** COMPLETE for TF-IDF family (8 representations)

| Representation | Verdict | Lang Dom | Jurist Pref | Both Adv Pass |
|----------------|---------|----------|-------------|---------------|
| cited_decisions_tfidf | PASS | 0.5295 | 0.8020 | ✅ |
| cited_outcome_hybrid_0.5 | PASS | 0.5164 | 0.8055 | ✅ |
| cited_outcome_hybrid_0.7 | PASS | 0.5238 | 0.7975 | ✅ |
| full_text_tfidf_light | FAIL | 1.0000 | 0.0000 | ❌ |
| outcome_tfidf | FAIL | 0.4527 | 0.7255 | ❌* |
| regeste_tfidf | FAIL | 0.4835 | 0.6090 | ❌* |
| regeste_full_text_hybrid_0.5 | FAIL | 1.0000 | 0.0000 | ❌ |
| regeste_full_text_hybrid_0.7 | FAIL | 1.0000 | 0.0000 | ❌ |

*\*Passes adversarial gates but fails multiple full-corpus benchmarks*

**Fundamental Tradeoff Confirmed:**
- **Citation-based modes** (cited_decisions_tfidf, hybrids): Pass adversarial, fail cross-language transfer, hierarchy, temporal stability, boilerplate resistance
- **Text-based modes** (full_text_tfidf_light, regeste hybrids): Pass cross-language, hierarchy, temporal stability; FAIL adversarial (language dominates completely)

**No TF-IDF representation passes all benchmarks at 174k scale.**

### Subquestion 2: Citation Heritage at 174k Scale
**Status:** COMPLETE for all 8 TF-IDF representations

| Representation | AUC-ROC | Positive Recall@10 | Status |
|----------------|---------|-------------------|--------|
| full_text_tfidf_light | 0.8969 | 0.0529 | PASS |
| regeste_full_text_hybrid_0.5 | 0.8714 | 0.0353 | PASS |
| regeste_full_text_hybrid_0.7 | 0.8504 | 0.0353 | PASS |
| cited_decisions_tfidf | 0.7892 | 0.0480 | PASS |
| cited_outcome_hybrid_0.7 | 0.7749 | 0.0490 | PASS |
| cited_outcome_hybrid_0.5 | 0.7589 | 0.0500 | PASS |
| outcome_tfidf | 0.6575 | 0.0000 | PASS (barely) |
| regeste_tfidf | 0.4861 | 0.0039 | **FAIL** |

**Key Finding (Corrected per Audit CYCLE_36242734524):** 
- AUC ranges 0.66-0.90 (NOT 0.72-0.97 as previously fabricated)
- Positive recall@10 ranges 0.00-0.053 (NOT 0.44-0.49 as previously fabricated)
- nn_citation_rate@10 ~0.03-0.05 for ALL representations — citation structure NOT strongly encoded in nearest neighbors

### Subquestion 3: v17b Label Normalization at 174k Scale
**Status:** COMPLETE

- **Label normalization:** 214 raw → 164 normalized legal_area labels; 49.3% of labels changed
- **Uniformity rule (>10% no-worsening on ALL hierarchy metrics):** PASSES for 2/8 representations only
- **Passing:** cited_decisions_tfidf, regeste_tfidf
- **Failing (NMI degradation 11-30%):** cited_outcome_hybrid_0.5, cited_outcome_hybrid_0.7, full_text_tfidf_light, outcome_tfidf, regeste_full_text_hybrid_0.5, regeste_full_text_hybrid_0.7
- **Best normalized hierarchy_purity:** 0.465 < 0.7 threshold — fundamental granularity/coverage limits persist

### Raw Multilingual-e5 768dim Partial (2000-2015, ~99k decisions)
**Status:** EVALUATED — **FAIL**

| Benchmark | Result | Key Metric |
|-----------|--------|------------|
| Adversarial Language Dominance | **FAIL** | lang_dom = 0.9855 |
| Jurist Pairwise Preference | **FAIL** | jurist_pref = 0.0275 |
| Zero-shot Cross-language Transfer | PASS | NMI = 0.293 |
| Per-language Branch NMI | PASS | de=0.386, fr=0.485, it=0.461 |
| Temporal Stability | PASS | overlap = 0.786 |
| Hierarchy Coherence (level_1) | FAIL | NMI = 0.454 |
| Cross-language Retrieval | FAIL | recall@10 = 0.0024 |
| Boilerplate Resistance | FAIL | score = -0.925 |

**Critical Finding:** Raw embeddings capture legal structure WITHIN each language (cross-language transfer passes) but language artifacts dominate neighbors (98% same-language), making cross-language legal navigation impossible. Transformations (center projection, metric learning, citation hybridization) are REQUIRED before dense embeddings are usable.

---

## Blockers

| Blocker | Status | Details |
|---------|--------|---------|
| Transformed dense embeddings at 174k | **ACTIVE** | legal-distance: 16/26 years raw complete (2000-2015); transformed representations (center_projected, metric-learned, hybrids) not yet produced |
| Citation roles at 174k | **ACTIVE** | Not yet produced by legal-distance |
| Linear hybrids at 174k | **ACTIVE** | Not yet produced by legal-distance |
| Years 2016-2025 raw embeddings | **ACTIVE** | 10 years pending from legal-distance year-split execution |
| Jurist human study | **NON-BLOCKING** | Framework ready; requires 5-10 Swiss jurists |

---

## Infrastructure Status

| Component | Status |
|-----------|--------|
| HNSW backend | OPERATIONAL on GitHub runners |
| Scalable NN (HNSW + sklearn fallback) | OPERATIONAL |
| v25 Formal Suite (12 benchmarks) | OPERATIONAL |
| Citation Heritage (137k frozen pairs) | READY |
| v17b Label Normalization | OPERATIONAL |
| Monitor Script | ACTIVE (enhanced scan, formal suite integration) |
| Formal Suite Runner | OPERATIONAL (NoneType.lower bug fixed) |

---

## HNSW Artifact — CONFIRMED AND FIXED

**Problem:** HNSW with fixed parameters produces nearly identical k-NN graphs across different TF-IDF representations at 174k scale, masking true differences in adversarial benchmarks.

**Evidence:**
- HNSW on full 174k: all 8 reps show jurist_pairwise ≈ 0.122, lang_dom ≈ 0.606
- Exact k-NN on stratified subsample (n=2000, valid decisions n≈90k): jurist_pairwise 0.71-0.80, lang_dom 0.43-0.53, differentiated

**Fix Deployed:** Exact k-NN (sklearn brute force) on fixed stratified subsample of 2000 decisions with known branch for **adversarial benchmarks only**. HNSW still used for full-corpus scale benchmarks (citation_heritage, temporal_stability, hierarchy family, cross_language_retrieval_full, boilerplate) by design.

---

## Next Steps

**No additional same-question cycle justified.** The evaluation lane has completed all available evaluations. The lane remains `BLOCKED_ON_DEPENDENCIES` with `continue_recommended: false`.

The monitor will continue scanning for new representations from legal-distance. When transformed dense embeddings, citation roles, or linear hybrids land at 174k scale, the monitor will automatically:
1. Detect the new representation
2. Run the full v25 formal suite (12 benchmarks + citation_heritage + v17b)
3. Record results and update state

**Factory Director Decision Required:** Successor question for evaluation lane once legal-distance delivers 174k transformed representations.

---

## Evidence References (Machine-Readable)

All evidence preserved in:
- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` — formal suite results
- `evaluation/results/174k_citation_heritage/` — citation heritage results
- `evaluation/results/v17b_174k_tfidf/v17b_174k_tfidf_results.json` — v17b normalization results
- `evaluation/results/174k/dense_partial_2000_2015/dense_partial_2000_2015_eval_latest.json` — raw multilingual-e5 evaluation
- `evaluation/state/monitor_174k_state.json` — monitor state with scan history
- `state/evaluation.json` — this lane state (updated to v30)

---

## Compliance with Research Protocol

1. ✅ Read Master Prompt, factory direction v30, lane directive
2. ✅ Inspected ACCEPTED evidence from corpus, legal-distance, fractal-map, product
3. ✅ Stated hypothesis/baseline/product decision (no new hypothesis — blocked on dependencies)
4. ✅ Frozen sample/metric/success rule (v25 formal suite config hash: `4323f833fa72366a`)
5. ✅ Implemented smallest discriminating experiment (monitor scan — no new reps found)
6. ✅ Ran experiment; preserved outputs
7. ✅ Compared with baseline (TF-IDF results unchanged)
8. ✅ Written machine-readable lane state + human-readable report
9. ✅ Recommendation: `BLOCKED_ON_DEPENDENCIES` (continue_recommended=false)

---

*End of Cycle Report*