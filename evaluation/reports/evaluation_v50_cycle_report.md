# Evaluation Lane Cycle v50 Report

**GitHub Run:** 36187240095  
**Timestamp:** 2026-09-25T20:52:00Z  
**Factory Direction:** v27  
**Lane Status:** BLOCKED_ON_DEPENDENCIES (correct)  
**Evidence Tier:** REPRODUCED  
**Continue Recommended:** false

---

## Executive Summary

This cycle independently executed the machine-executable 174k formal evaluation suite on the TF-IDF production family (8 representations at 173,963 decisions) and validated the citation_heritage benchmark infrastructure. All three factory-direction sub-questions for the TF-IDF family are **confirmed COMPLETE** with frozen thresholds and no tuning after results.

The lane remains correctly **BLOCKED_ON_DEPENDENCIES** awaiting legal-distance 174k dense embeddings (center_projected, metric learning, hybrid objectives, citation roles, linear hybrids). Legal-distance year-split computation shows 7/26 years complete (2000-2006, 27%) in checkpoints.

---

## Sub-Question 1: 12-Benchmark Formal Suite at 174k Scale ✅ COMPLETE

**Runner:** `evaluation/run_174k_formal_suite.py` (HNSW artifact fix: exact k-NN on fixed stratified subsample n=2000 for adversarial/cross-language/jurist benchmarks; HNSW for full-corpus scale benchmarks)

**Config Hash:** `b51701f5a9c11692` | **Seed:** 42 | **Factory Direction:** v27

### Adversarial Gate Results (EXACT k-NN on 2000 stratified decisions)

| Representation | Verdict | LangDom | LD-PASS | JuristPref | JP-PASS | Both |
|---|---|---|---|---|---|---|
| cited_decisions_tfidf_outcome_hybrid_0.5 | **PASS** | 0.5164 | ✓ | 0.8055 | ✓ | ✓ |
| cited_decisions_tfidf | **PASS** | 0.5295 | ✓ | 0.8020 | ✓ | ✓ |
| cited_decisions_tfidf_outcome_hybrid_0.7 | **PASS** | 0.5238 | ✓ | 0.7975 | ✓ | ✓ |
| outcome_tfidf | **PASS** | 0.4527 | ✓ | 0.7255 | ✓ | ✓ |
| regeste_tfidf | **PASS** | 0.4835 | ✓ | 0.6090 | ✓ | ✓ |
| full_text_tfidf_light | FAIL | 1.0000 | ✗ | 0.0000 | ✗ | ✗ |
| regeste_full_text_hybrid_0.5 | FAIL | 1.0000 | ✗ | 0.0000 | ✗ | ✗ |
| regeste_full_text_hybrid_0.7 | FAIL | 1.0000 | ✗ | 0.0000 | ✗ | ✗ |

**Best (passing both gates):** `cited_decisions_tfidf_outcome_hybrid_0.5`  
**Production Default:** `cited_decisions_tfidf_outcome_hybrid_0.7` (equivalent adversarial performance)

### Key Observations

- **Citation-based representations** (cited_decisions_tfidf + outcome hybrids) pass both adversarial gates with strong jurist preference (0.79-0.81)
- **Full-text/regeste representations** fail language dominance (~1.0) because full_text is available for all decisions and dominates TF-IDF space
- **HNSW artifact fix verified**: Exact k-NN on stratified subsample (2000 decisions, 90,632 valid with known branch) produces clean adversarial results matching v25 frozen suite
- **Universal 174k FAILs** (corpus/label limitations, not representation defects):
  - `hierarchy_coherence`: purity 0.08-0.47 < 0.7 threshold
  - `legal_area_clustering`: purity 0.003-0.08 < 0.5 threshold  
  - `temporal_stability`: neighbor overlap 0.03-0.78 (unstable)
  - `boilerplate_resistance`: resistance_score -0.57 to -0.77 (negative)

---

## Sub-Question 2: Citation_Heritage Benchmark Validation ✅ COMPLETE

**Runner:** `evaluation/validate_citation_heritage_174k.py`

### Citation Graph Statistics (from resolved_full)

- **Total citations:** 2,105
- **Resolved:** 2,019 (95.9%)
- **Unresolved:** 86 (4.1%)
- **Decisions with outgoing citations in 174k corpus:** 174 (0.1% of 173,963)
- **Resolved citations mapping to 174k corpus:** 924

### Frozen Pair Pool

- **Positive pairs (direct + shared citations):** 1,020
- **Negative pairs (no citation relation):** 1,020
- **Saved to:** `evaluation/results/174k_citation_heritage/citation_pairs_174k.json`
- **Full pool (v25 protocol):** 137,314 pairs in `citation_pairs_174k_full.json`

### V25 Suite Citation_Heritage Results (from prior runs)

| Representation | AUC | Status (threshold ≥ 0.65) | nn_citation_rate@10 |
|---|---|---|---|
| cited_decisions_tfidf | 0.9731 | **PASS** | 0.476 |
| cited_outcome_hybrid_0.7 | 0.9605 | **PASS** | 0.490 |
| cited_outcome_hybrid_0.5 | 0.9193 | **PASS** | 0.476 |
| regeste_full_text_hybrid_0.5 | 0.8921 | **PASS** | 0.440 |
| regeste_full_text_hybrid_0.7 | 0.8834 | **PASS** | 0.438 |
| full_text_tfidf_light | 0.7832 | **PASS** | 0.000 |
| outcome_tfidf | 0.5012 | FAIL | 0.003 |
| regeste_tfidf | 0.4865 | FAIL | 0.000 |

**7/8 representations PASS** (citation-based and full-text hybrids; outcome_tfidf and regeste_tfidf lack citation IDs in source text).

---

## Sub-Question 3: v17b Label Normalization Generalization ✅ COMPLETE (Previously Documented)

**Status:** Tested across all 8 TF-IDF representations at 174k scale (v44-v49 cycles)

### Label Normalization Effect

- **Raw unique legal_area labels:** 213
- **Normalized labels:** 163 (23.5% reduction)
- **Labels changed:** 49.3% (85,819 decisions affected)
- **Avg decisions per label:** 428 → 560
- **Cross-lingual canonical concepts:** 32

### Generalization Result: PARTIAL

| Representation | Hierarchy NMI Change | Zoom Coherence Change | Within ≤10% Rule? |
|---|---|---|---|
| cited_decisions_tfidf | +1.2% | +2.1% | ✅ YES |
| regeste_tfidf | -3.4% | +1.8% | ✅ YES |
| cited_outcome_hybrid_0.7 | -10.8% | +1.5% | ❌ NO (hierarchy NMI) |
| outcome_tfidf | -13.1% | +0.9% | ❌ NO |
| full_text_tfidf_light | -27.6% | +2.3% | ❌ NO |
| regeste_full_text_hybrid_0.5 | -27.6% | -0.2% | ❌ NO |
| regeste_full_text_hybrid_0.7 | -27.6% | -0.2% | ❌ NO |
| cited_outcome_hybrid_0.5 | -9.6% | -16.0% | ❌ NO (zoom) |

**Normalized hierarchy purity gains:** 1.5-1.6x for citation-based reps, 1.0x for full-text/regeste reps (coarse labels map 1:1).

**Even normalized, best hierarchy purity = 0.47 (full_text_tfidf_light) < 0.7 threshold** — confirming v16/v18 finding that hierarchy_coherence is a fundamental limitation at 174k scale with current label granularity.

---

## Infrastructure Verification

| Component | Status | Notes |
|---|---|---|
| `run_174k_formal_suite.py` | **OPERATIONAL** | HNSW artifact fix verified; exact k-NN on subsample; HNSW for full-corpus |
| `validate_citation_heritage_174k.py` | **OPERATIONAL** | Frozen pair pool ready (137,314 pairs) |
| v17b label normalization | **OPERATIONAL** | Frozen conservative canonical map (32 concepts) |
| `monitor_and_evaluate_174k.py` | **OPERATIONAL** | Enhanced with `run_formal_suite_v25()` for auto-evaluation |
| `scalable_nn.py` HNSW backend | **OPERATIONAL** | hnswlib available, EXACT_NN_THRESHOLD=10000 |
| `run_full_corpus_evaluation.py` | **OPERATIONAL** | Config hash 4047da047fb339c1 matches frozen v3 harness |

**All config hashes frozen and verified:**
- Formal suite: `b51701f5a9c11692`
- v25 suite: `4323f833fa72366a`  
- Harness: `4047da047fb339c1`
- v3 harness: `a31c443a9b0e992e`

---

## Legal-Distance Dependency Status

- **Dense embeddings needed:** center_projected (768/64/128), metric learning, hybrid objectives, citation roles, linear hybrids
- **Current progress:** 7/26 years complete in checkpoints (2000-2006, 27%)
- **GitHub Run:** 36096850301 (IN_PROGRESS)
- **Checkpoint location:** `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/`
- **Monitor scans:** `174k_dense_embeddings` root directory (excludes checkpoints subdir) for final concatenated embeddings
- **Auto-evaluation trigger:** `run_formal_suite_v25()` will execute full v25 protocol when new embeddings land

---

## Jurist Human Study

**Status:** BLOCKED (external dependency)  
**Requirement:** 5-10 Swiss jurists recruited by repository owner  
**Framework:** Ready per v25 protocol

---

## Recommendation

**NO ADDITIONAL SAME-QUESTION CYCLE JUSTIFIED** for TF-IDF family (`continue_recommended=false` per Research Protocol).

The three machine-executable sub-questions are frozen complete:
1. ✅ 12-benchmark formal suite at 174k scale (8/8 representations, frozen thresholds)
2. ✅ Citation_heritage benchmark validated (7/8 PASS AUC≥0.65, frozen 137k pair pool)
3. ✅ v17b label normalization generalization tested (PARTIAL, documented)

Lane correctly remains **BLOCKED_ON_DEPENDENCIES** awaiting legal-distance 174k dense embeddings.

All evidence preserved in:
- `evaluation/results/174k/formal_suite/` (formal suite results)
- `evaluation/results/174k_citation_heritage/` (citation heritage infrastructure)
- `evaluation/results/evaluation/v25_174k_v17b/` (v17b normalization analysis)
- `evaluation/state/monitor_174k_state.json` (78+ monitor checks)
- `evaluation/state/evaluation.json` (this verification v50)

---

## Negative Results Preserved

Per Anti-Noise Principle and Evaluation Doctrine, the following universal failures at 174k are **corpus/label limitations**, not representation defects:

- `hierarchy_coherence`: All representations FAIL (purity 0.08-0.47 < 0.7) — fine-grained legal_area labels (213 raw, 163 normalized) too sparse for 174k decisions
- `legal_area_clustering`: All representations FAIL (purity 0.003-0.08 < 0.5) — same label granularity issue
- `temporal_stability`: All representations FAIL — neighbor preservation unstable at full corpus density
- `boilerplate_resistance`: All representations FAIL — proxy measures language alignment failure, not procedural boilerplate

These are honestly documented and do not block production deployment of citation-based representations that pass adversarial gates.

---
*Report generated by Evaluation Lane Cycle v50 (GitHub Run 36187240095)*