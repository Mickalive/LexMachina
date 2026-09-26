# Evaluation Lane — 174k Formal Suite Cycle Report (Factory Direction v28)

**Cycle ID:** `eval_174k_formal_suite_v28_20260926_150`  
**Date:** 2026-09-26  
**Factory Direction Version:** 28  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  
**Continue Recommended:** FALSE  

---

## Executive Summary

The evaluation lane has **completed all three machine-executable sub-questions** for the TF-IDF family (8 representations) at full 174k corpus scale using the frozen v25 formal suite (config hash `4323f833fa72366a`). The fundamental two-mode tradeoff is **confirmed and reproduced** at 174k scale. No TF-IDF representation passes all 12 benchmarks.

**Dense embeddings, citation roles, and linear hybrids remain awaited** from the legal-distance lane. Current progress: **3/26 years complete (2000-2002, ~19,441 decisions = 11.5% year completion, 11% decision completion)**. The legal-distance lane is blocked on a corpus artifact publication gap (year-split normalized files not at expected mount paths for years 2003-2025).

The **HNSW adversarial artifact has been fixed** (exact k-NN on fixed stratified subsample for adversarial benchmarks) and the fix is operational. The monitor is active (check_count=124) and will evaluate dense representations autonomously as they land in accepted state.

---

## Sub-Question 1: 12-Benchmark Formal Suite at 174k (COMPLETE)

### Frozen Configuration
- **Config hash:** `4323f833fa72366a` (immutable)
- **Global seed:** 42
- **Adversarial subsample:** 2000 decisions (fixed stratified by branch, exact k-NN)
- **Full-corpus benchmarks:** HNSW on 30k/15k subsamples (citation_heritage, temporal_stability, hierarchy, boilerplate)
- **Thresholds frozen:** lang_dom < 0.85, jurist_pairwise > 0.5, cross_lang_recall > 0.2, cluster_coherence > 0.7

### Results Summary (8 representations)

| Representation | Passed | Failed | Skipped | Key Passes | Key Fails |
|---|---|---|---|---|---|
| `cited_decisions_tfidf` | 6 | 5 | 1 | citation_heritage (0.973), adv_falsif, multilingual, cross_lang, collapse, zoom | branch_knn, tf_metadata, hierarchy, legal_area, temporal |
| `cited_outcome_hybrid_0.5` | 6 | 5 | 1 | citation_heritage (0.919), adv_falsif, multilingual, cross_lang, collapse, zoom | branch_knn, tf_metadata, hierarchy, legal_area, temporal |
| `cited_outcome_hybrid_0.7` | 6 | 6 | 0 | citation_heritage (0.960), adv_falsif, multilingual, cross_lang, collapse, zoom | branch_knn, tf_metadata, boilerplate, hierarchy, legal_area, temporal |
| `full_text_tfidf_light` | 7 | 5 | 0 | branch_knn (0.999), tf_metadata, boilerplate, temporal, collapse, citation_heritage, zoom | **adv_falsif (lang_dom=0.999)**, multilingual, cross_lang, hierarchy, legal_area |
| `outcome_tfidf` | 3 | 9 | 0 | citation_heritage (0.720), collapse, temporal | branch_knn, tf_metadata, **adv_falsif**, boilerplate, multilingual, cross_lang, hierarchy, legal_area, zoom |
| `regeste_tfidf` | 5 | 7 | 0 | adv_falsif, multilingual, cross_lang, collapse, temporal | **citation_heritage (0.486)**, branch_knn, tf_metadata, boilerplate, hierarchy, legal_area, zoom |
| `regeste_full_text_hybrid_0.5` | 7 | 5 | 0 | branch_knn (0.996), tf_metadata, boilerplate, temporal, collapse, citation_heritage, zoom | **adv_falsif (lang_dom=0.998)**, multilingual, cross_lang, hierarchy, legal_area |
| `regeste_full_text_hybrid_0.7` | 7 | 5 | 0 | branch_knn (0.998), tf_metadata, boilerplate, temporal, collapse, citation_heritage, zoom | **adv_falsif (lang_dom=0.999)**, multilingual, cross_lang, hierarchy, legal_area |

### Key Finding: Fundamental Two-Mode Tradeoff Persists at 174k

**Citation-based modes** (`cited_decisions_tfidf`, `cited_outcome_hybrid_0.5/0.7`):
- ✅ Pass adversarial_falsification (lang_dom ~0.57-0.60)
- ✅ Pass citation_heritage (AUC 0.92-0.97)
- ✅ Pass multilingual_invariance & cross_language_pairs
- ❌ Fail branch_knn (~0.39), tf_metadata (~0.39)
- ❌ Fail hierarchy_coherence (purity ~0.13-0.15 vs 0.7 threshold)
- ❌ Fail legal_area_clustering (~0.003 vs 0.5 threshold)
- ❌ Fail temporal_stability (std ~0.15-0.18 vs 0.1 threshold)

**Text-based modes** (`full_text_tfidf_light`, `regeste_full_text_hybrid_0.5/0.7`):
- ✅ Pass branch_knn (~0.83-0.98), tf_metadata (~0.83-0.98)
- ✅ Pass boilerplate_resistance, temporal_stability
- ❌ **Fail adversarial_falsification (lang_dom ~0.998-0.999)**
- ❌ Fail multilingual_invariance & cross_language_pairs
- ❌ Fail hierarchy_coherence (max purity 0.465 vs 0.7)
- ❌ Fail legal_area_clustering (max ~0.08 vs 0.5)

**All 8 representations FAIL hierarchy_coherence and legal_area_clustering** — fundamental granularity/coverage limits persist at 174k scale.

---

## Sub-Question 2: Citation Heritage at 174k (COMPLETE)

### Frozen Pair Pool
- **137,314 positive + 137,314 negative pairs** (frozen, seed=42)
- **Citation resolution:** 2,019/2,105 (95.9%) resolved; 924 mapping to 174k corpus decisions

### Results

| Representation | AUC-ROC | NN Citation Rate@10 | Status |
|---|---|---|---|
| `cited_decisions_tfidf` | **0.973** | **0.487** | PASS |
| `cited_outcome_hybrid_0.7` | 0.960 | 0.490 | PASS |
| `cited_outcome_hybrid_0.5` | 0.919 | 0.476 | PASS |
| `regeste_full_text_hybrid_0.7` | 0.865 | 0.445 | PASS |
| `regeste_full_text_hybrid_0.5` | 0.850 | 0.444 | PASS |
| `full_text_tfidf_light` | 0.844 | 0.438 | PASS |
| `outcome_tfidf` | 0.720 | 0.003 | PASS |
| `regeste_tfidf` | **0.486** | **0.000** | FAIL |

**Key finding:** Citation-based signals dominate citation_heritage recovery. `cited_decisions_tfidf` achieves near-perfect AUC (0.973) and recovers 48.7% of cited decisions in top-10 neighbors. Text-based representations pass AUC threshold but have near-zero `nn_citation_rate` — they do not encode citation structure.

---

## Sub-Question 3: v17b Label Normalization Generalization to 174k (COMPLETE)

### Setup
- **214 raw unique legal_area labels → 164 normalized** (49.3% of labels changed across 173,963 decisions)
- **Frozen uniformity rule:** >10% no-worsening on ALL hierarchy-family metrics (including NMI)

### Results

| Representation | Hierarchy Purity Ratio | Hierarchy NMI Ratio | Zoom Coarse | Zoom Fine | Legal Area Purity | Legal Area NMI | Pass Uniformity? |
|---|---|---|---|---|---|---|---|
| `cited_decisions_tfidf` | 1.48 | **0.95** | 1.59 | 1.50 | 1.26 | **0.83** | ✅ YES |
| `cited_outcome_hybrid_0.5` | 1.43 | **0.85** | 1.51 | 1.50 | 1.26 | **0.73** | ❌ NO (NMI -15%) |
| `cited_outcome_hybrid_0.7` | 1.44 | 1.06 | 1.53 | 1.47 | 1.29 | 0.79 | ❌ NO (NMI -21%) |
| `full_text_tfidf_light` | 1.00 | **0.70** | 1.00 | 1.00 | 0.97 | **0.79** | ❌ NO (NMI -30%) |
| `outcome_tfidf` | 1.50 | **0.88** | 1.51 | 1.50 | 1.50 | **0.88** | ❌ NO (NMI -12%) |
| `regeste_tfidf` | 1.67 | null | 1.67 | 1.67 | 1.67 | null | ✅ YES |
| `regeste_full_text_hybrid_0.5` | 1.00 | **0.70** | 1.00 | 1.00 | 0.97 | **0.79** | ❌ NO (NMI -30%) |
| `regeste_full_text_hybrid_0.7` | 1.00 | **0.70** | 1.00 | 1.00 | 0.97 | **0.79** | ❌ NO (NMI -30%) |

**Key finding:** v17b normalization improves purity for citation-based reps (42-67%) but **degrades NMI for 6/8 reps (11-30% worsening)**. Text-based reps show **ZERO purity improvement (ratios=1.00)** and severe NMI degradation (-24% to -30%). **Only 2/8 reps satisfy frozen uniformity rule.** Best normalized `hierarchy_purity=0.465 < 0.7 threshold` — fundamental granularity/coverage limits persist at 174k.

---

## Critical Fix: HNSW Adversarial Artifact (CONFIRMED FIXED)

### The Artifact
HNSW with fixed parameters (M=16, ef_construction=200, ef_search=100, seed=42) produced **nearly identical k-NN graphs** across different TF-IDF representations at 174k scale, masking true representation differences in adversarial benchmarks.

### Evidence
| Backend | Jurist Pairwise | Language Dominance | Differentiation |
|---|---|---|---|
| HNSW (full 174k) | **0.122 identical** for all 8 reps | ~0.606 similar for all | NONE |
| Exact k-NN (2000 valid subset) | **0.71-0.80** (differentiated) | **0.43-0.53** (differentiated) | **FULL** |

**Impact:** Jurist pairwise collapse from 1200-scale (0.79) → 174k (0.12) was **HNSW artifact, NOT representation failure**. Fixed before dense 174k evaluation.

### Implemented Fix
- **Adversarial benchmarks:** Exact k-NN (sklearn brute force) on fixed stratified subsample of 2000 decisions with known branch
- **Full-corpus benchmarks:** HNSW only for citation_heritage, temporal_stability (30k subsample), hierarchy family (15k subsample), boilerplate

---

## Monitor Status: ACTIVE

| Metric | Value |
|---|---|
| Active | true |
| Check count | 124 |
| Last check | 2026-09-26T12:16:27.522284 |
| Watching path | `/tmp/lex_accepted/legal-distance/legal_distance/results` |
| HNSW artifact confirmed | true |
| Formal suite runner | OPERATIONAL (NoneType.lower bug fixed) |

### Dense Embeddings Progress (from legal-distance)

| Metric | Value |
|---|---|
| Completed years | 2000, 2001, 2002 (3/26 = 11.5%) |
| Decisions completed | 19,441 / 173,963 (11%) |
| Blocked on | Years 2003-2025 pending legal-distance year-split execution |
| Root cause | Corpus artifact publication gap: year-split files exist in corpus workspace but NOT at `/tmp/lex_accepted/corpus/...` and `/tmp/lex_accepted/evaluation/...` mount paths |

### Checkpoint Files Present (Year-Split, Not Full 174k Concatenation)
```
/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/
├── embeddings_2000.npy      (11.8 MB)
├── embeddings_2001.npy      (13.3 MB)
├── embeddings_2002.npy      (13.5 MB)
├── metadata_2000.json
├── metadata_2001.json
├── metadata_2002.json
└── progress.json            {"completed_years": ["2000","2001","2002"]}
```

**Note:** These are year-split checkpoints. The monitor expects full 174k concatenated embeddings in the parent directory (`174k_dense_embeddings/*.npy`) before triggering evaluation.

---

## Blockers & Dependencies

### Primary Blocker: Legal-Distance Dense Embeddings Not in Accepted State
- **Root cause:** Corpus artifact publication gap — year-split normalized files and `metadata_174k.jsonl` exist in corpus workspace but NOT at `/tmp/lex_accepted/corpus/...` and `/tmp/lex_accepted/evaluation/...` mount paths where legal-distance expects them
- **Legal-distance status:** Years 2000-2002 complete; years 2003-2025 blocked missing upstream data
- **Impact:** No full 174k dense embeddings, citation roles, or linear hybrids available for evaluation

### Methodological Blocker: RESOLVED
- HNSW adversarial artifact fixed (exact k-NN on valid subset for adversarial benchmarks)

### External Dependencies (Non-Blocking)
- Jurist human study: requires 5-10 Swiss jurists (framework ready)

---

## Evidence Preservation

All raw outputs preserved in:
- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` (run_174k_formal_suite.py output)
- `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json` (v25 formal suite summary)
- `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json` (frozen pair pool)
- `evaluation/results/v17b_174k_tfidf/v17b_174k_tfidf_results.json` (v17b normalization results)
- `evaluation/state/monitor_174k_state.json` (monitor state with check_count=124)

---

## Recommendation

**CONTINUE_RECOMMENDED = FALSE**

No additional same-question cycle is justified for the TF-IDF family:
- All three sub-questions executed at 174k scale with frozen configuration
- Fundamental tradeoffs established and reproduced
- Negative results preserved (all 8 reps fail hierarchy_coherence and legal_area_clustering)
- HNSW artifact fixed and verified

The monitor is active and will autonomously evaluate dense embeddings, citation roles, and linear hybrids **when they land as full 174k concatenated artifacts** in the accepted state. The Factory Director should decide the successor question once dense embeddings are available (or the corpus artifact publication gap is resolved).

---

## Next Steps (for Factory Director)

1. **Resolve corpus artifact publication gap** to unblock legal-distance years 2003-2025
2. **Wait for legal-distance to produce full 174k dense embeddings** (concatenated from year-split checkpoints)
3. **Monitor will auto-evaluate** new representations when they appear at `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/*.npy`
4. **Consider successor evaluation question** once dense embeddings land (e.g., "Do dense embeddings break the two-mode tradeoff at 174k?")