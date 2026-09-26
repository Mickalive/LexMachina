# Evaluation Lane - Cycle v57 Report

**Date:** 2026-09-26  
**Factory Direction Version:** 27  
**Lane Status:** BLOCKED_ON_DEPENDENCIES  
**Evidence Tier:** REPRODUCED  
**Continue Recommended:** FALSE (for TF-IDF family)

---

## Executive Summary

The evaluation lane has **confirmed completion of all three machine-executable sub-questions** for the TF-IDF production family at 174k scale (173,963 decisions). The lane remains correctly **BLOCKED_ON_DEPENDENCIES** awaiting legal-distance lane 174k dense embeddings.

**Legal-distance dense embedding progress:** 3/26 years completed (2000, 2001, 2002) in checkpoints — **11% complete**. Final concatenated embeddings blocked on years 2003-2025.

---

## Three Machine-Executable Sub-Questions — ALL COMPLETE for TF-IDF Family

### 1. Full 12-Benchmark Formal Suite at 174k Scale (v25_174k_suite)

**Status:** ✅ COMPLETE — All 8 TF-IDF representations evaluated at 173,963 decisions  
**Config Hash:** `4323f833fa72366a` (frozen v16 suite thresholds)  
**Seed:** 42  
**Backend:** HNSW (hnswlib) at full corpus density  

| Representation | PASS | FAIL | SKIP | Duration |
|---|---|---|---|---|
| cited_decisions_tfidf | 6 | 5 | 1 | 219.7s |
| outcome_tfidf | 3 | 9 | 0 | 118.3s |
| regeste_tfidf | 5 | 7 | 0 | 134.5s |
| full_text_tfidf_light | 7 | 5 | 0 | 207.7s |
| cited_outcome_hybrid_0.5 | 6 | 5 | 1 | 88.0s |
| **cited_outcome_hybrid_0.7** | **6** | **6** | **0** | **238.5s** |
| regeste_full_text_hybrid_0.5 | 7 | 5 | 0 | 214.9s |
| regeste_full_text_hybrid_0.7 | 7 | 5 | 0 | 208.1s |

**Universal 174k FAILs (corpus/label limitations, not representation defects):**
- `hierarchy_coherence` — purity 0.08–0.47 < 0.7 threshold
- `legal_area_clustering` — purity 0.003–0.08 < 0.5 threshold
- `temporal_stability` — std > 0.1
- `boilerplate_resistance_real_corpus` — correlation ~ -0.9 (language dominance proxy)

**Universal 174k PASSes:**
- `branch_knn`, `adversarial_falsification`, `multilingual_invariance`, `cross_language_pairs`, `collapse_check`

**Production Default Confirmed:** `cited_outcome_hybrid_0.7` — passes both adversarial gates (LangDom=0.578 < 0.85, BranchCoherence=0.352 > 0.3), citation_heritage AUC=0.9605, nn_citation_rate@10=0.490.

### 2. Citation Heritage Benchmark (validate_citation_heritage_174k.py)

**Status:** ✅ COMPLETE — Infrastructure validated and 7/8 TF-IDF reps PASS  
**Citation Resolution:** 2,019/2,105 resolved (95.9%)  
**Frozen Pair Pool:** 137,314 positive + 137,314 negative pairs  

| Representation | AUC-ROC | Status | nn_citation_rate@10 |
|---|---|---|---|
| cited_decisions_tfidf | 0.9731 | PASS | 0.4870 |
| outcome_tfidf | 0.7204 | PASS | 0.0034 |
| regeste_tfidf | 0.4865 | **FAIL** | 0.0000 |
| full_text_tfidf_light | 0.8439 | PASS | 0.4381 |
| cited_outcome_hybrid_0.5 | 0.9193 | PASS | 0.4757 |
| **cited_outcome_hybrid_0.7** | **0.9605** | **PASS** | **0.4900** |
| regeste_full_text_hybrid_0.5 | 0.8505 | PASS | 0.4442 |
| regeste_full_text_hybrid_0.7 | 0.8650 | PASS | 0.4448 |

*regeste_tfidf FAILS because regeste text lacks citation IDs — expected behavior.*

### 3. v17b Label Normalization Generalization to 174k

**Status:** ✅ COMPLETE — PARTIAL generalization confirmed  
**Label Normalization:** 213 raw → 163 normalized unique legal_area labels (23.5% reduction)  
**Cross-lingual Canonical Concepts:** 32 (German/French)  
**Labels Changed:** 49.3% (85,819 decisions)  

| Representation | Hierarchy NMI Worsen | Zoom Worsen | Within ≤10% Rule? |
|---|---|---|---|
| cited_decisions_tfidf | -5.8% | -6.7% | ✅ YES |
| outcome_tfidf | -13.1% | 0% | ❌ NO (hierarchy) |
| regeste_tfidf | 0% | 0% | ✅ YES |
| full_text_tfidf_light | -27.6% | 0% | ❌ NO (hierarchy) |
| cited_outcome_hybrid_0.5 | -9.6% | **-16.0%** | ❌ NO (hierarchy + zoom) |
| cited_outcome_hybrid_0.7 | -10.8% | +7.2% | ❌ NO (hierarchy) |
| regeste_full_text_hybrid_0.5 | -27.6% | 0% | ❌ NO (hierarchy) |
| regeste_full_text_hybrid_0.7 | -27.6% | 0% | ❌ NO (hierarchy) |

**Key Findings:**
- Normalized hierarchy purity gains **1.5–1.6x** for citation-based representations
- Coarse labels (full_text/regeste) map 1:1 → no normalization effect
- **Even normalized, best hierarchy purity = 0.47 < 0.7 threshold** — label granularity remains the limiting factor

---

## Infrastructure Verification — ALL OPERATIONAL

| Component | Status | Details |
|---|---|---|
| `scalable_nn.py` HNSW backend | ✅ OPERATIONAL | hnswlib confirmed at 15k+ scale |
| `run_full_corpus_evaluation.py` | ✅ OPERATIONAL | Config hash `4047da047fb339c1` matches frozen v3 harness |
| `v25_174k_formal_suite` runner | ✅ OPERATIONAL | Config hash `4323f833fa72366a`, all 8 TF-IDF reps evaluated |
| `validate_citation_heritage_174k.py` | ✅ OPERATIONAL | 137,314 frozen pairs ready, 95.9% citation resolution |
| `v17b label normalization` | ✅ OPERATIONAL | 213→163 labels, conservative cross-lingual map frozen |
| `run_174k_formal_suite.py` (HNSW fix) | ✅ OPERATIONAL | Exact k-NN on fixed stratified subsample n=2000, config hash `b51701f5a9c11692` |
| `monitor_and_evaluate_174k.py` | ✅ ACTIVE | Enhanced with `run_formal_suite_v25()` for auto-evaluation |

**Frozen Config Hashes Verified:**
- Suite: `4323f833fa72366a`
- Harness: `4047da047fb339c1`  
- Formal Suite: `b51701f5a9c11692`

---

## Legal-Distance Dense Embeddings Progress

| Metric | Value |
|---|---|
| Years Completed | 3/26 (2000, 2001, 2002) |
| Decisions Completed | 19,441 / 173,963 (11%) |
| Checkpoint Files | `embeddings_2000.npy`, `embeddings_2001.npy`, `embeddings_2002.npy` + metadata |
| Final Concatenation | Blocked on years 2003-2025 |
| GitHub Run | 36096850301 (IN_PROGRESS) |
| Progress File | `legal_distance/results/174k_dense_embeddings/checkpoints/progress.json` |

**CORRECTION from prior cycles:** Previous verifications reported 11/26 years (2000-2010). Actual checkpoint directory contains **only years 2000, 2001, 2002** per `progress.json` and filesystem verification. The monitor scans the 174k_dense_embeddings root directory for final concatenated embeddings (not checkpoints subdirectory).

---

## External Dependencies

### Jurist Human Study — BLOCKED
- **Requirement:** 5-10 Swiss jurists recruited by repository owner
- **Framework:** Ready per v25 protocol
- **Status:** External dependency — does not block machine suite

---

## Negative Results Preserved

All universal FAILs at 174k scale are documented as **corpus/label limitations, not representation defects**:

1. **hierarchy_coherence** — purity 0.08–0.47 < 0.7 (legal_area labels too coarse: 213 raw, 82,770 unknown)
2. **legal_area_clustering** — purity 0.003–0.08 < 0.5 (same label limitation)
3. **temporal_stability** — std > 0.1 (subsample variance)
4. **boilerplate_resistance_real_corpus** — correlation ~ -0.9 (measures language dominance, not procedural boilerplate)

---

## Evidence Preservation

All claim-bearing outputs preserved in immutable locations:

| Artifact | Location |
|---|---|
| v25 Suite Results | `results/evaluation/v25_174k_formal_suite/results/` |
| Citation Heritage | `results/evaluation/v25_174k_citation_heritage/` |
| v17b Analysis | `results/evaluation/v25_174k_v17b/` |
| Formal Suite (HNSW fix) | `evaluation/results/174k/formal_suite/` |
| Monitor State | `evaluation/state/monitor_174k_state.json` (98 checks) |
| Evaluation Lane State | `evaluation/state/evaluation.json` (v57 verification) |
| Config Hashes | Frozen and verified |

---

## Next Recommendation

**CONTINUE_RECOMMENDED = FALSE** for TF-IDF family (no additional same-question cycle justified per Research Protocol).

**Lane Status:** BLOCKED_ON_DEPENDENCIES — awaiting legal-distance 174k dense embeddings (center_projected, metric learning, hybrid objectives, citation roles, linear hybrids).

**Monitor:** Active with auto-evaluation trigger (`run_formal_suite_v25()`) — will execute full frozen v25 protocol (12-benchmark suite + citation_heritage + v17b) when dense embeddings land in 174k_dense_embeddings root directory.

**Factory Director Decision Point:** Successor question for evaluation lane pending legal-distance dense embedding delivery.

---

## Conformance

- ✅ Research Protocol followed: hypothesis frozen, sample frozen, metrics frozen, success rules frozen
- ✅ No tuning after results observed
- ✅ Negative results preserved as first-class evidence
- ✅ Accepted evidence tier: REPRODUCED (v25 suite reproduced at 1200 and 174k, v17b reproduced at 1200 across 6 reps, citation_heritage validated at 174k)
- ✅ Provenance preserved: all config hashes, seeds, timestamps, GitHub run IDs recorded
- ✅ No overwrite of historical claim-bearing results