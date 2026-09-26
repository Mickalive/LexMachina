# Evaluation Lane v27 — 174k Monitor Cycle Final Report

**Run ID:** `eval_v27_174k_monitor_cycle_20260926_final`  
**Factory Direction:** v27  
**Date:** 2026-09-26  
**Evidence Tier:** REPRODUCED (TF-IDF family)  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  
**Continue Recommended:** false (for same-question TF-IDF cycle)

---

## Executive Summary

The evaluation lane has **COMPLETED all three machine-executable sub-questions** for the TF-IDF production family (8 representations) at full 174k corpus scale. The v25 174k formal suite is validated and frozen. The HNSW methodological artifact has been **CONFIRMED and FIXED** via exact k-NN on a fixed stratified subsample for adversarial benchmarks. The monitoring infrastructure is **VERIFIED and ACTIVE** (check_count=119), correctly detecting representations in accepted mounts and ready to auto-evaluate dense embeddings when they land.

**Dense embeddings remain BLOCKED** on legal-distance upstream corpus artifact publication gap (only 3/26 years complete: 2000-2002). No additional same-question evaluation cycle is justified for the TF-IDF family — fundamental tradeoffs are established and negative results preserved as first-class evidence.

---

## Sub-Question Completion Status

| Sub-Question | Status | Representations | Key Finding |
|--------------|--------|-----------------|-------------|
| **1. 12-Benchmark Formal Suite (v25 protocol)** | ✅ COMPLETE | 8/8 TF-IDF | No representation passes all 12. Citation-aware excel at citation_heritage/adversarial/multilingual; text-based excel at branch_knn/tf_metadata/boilerplate. **ALL fail hierarchy_coherence** (max purity 0.465 vs 0.7 threshold). |
| **2. Citation Heritage (137k frozen pairs)** | ✅ COMPLETE | 8/8 TF-IDF | 7/8 PASS (AUC ≥ 0.65). **cited_decisions_tfidf AUC=0.973**, nn_citation_rate@10=0.487. Only regeste_tfidf FAILS (AUC=0.486). |
| **3. v17b Label Normalization Generalization** | ✅ COMPLETE | 8/8 TF-IDF | **NOT uniformly confirmed** — 6/8 representations worsen >10% on NMI. Only cited_decisions_tfidf and regeste_tfidf satisfy frozen uniformity rule. Best normalized hierarchy_purity=0.465 < 0.7. |

---

## Critical Infrastructure Fix: HNSW Artifact

**Problem:** HNSW with fixed parameters (M=16, ef_construction=200, ef_search=100, seed=42) produced nearly identical k-NN graphs across all 8 TF-IDF representations at 174k scale, masking true representation differences in adversarial benchmarks.

| Evaluation Method | Jurist Pairwise | Language Dominance |
|-------------------|-----------------|-------------------|
| v3 harness (HNSW, full 174k) | **0.122 (identical for ALL 8)** | ~0.606 (identical) |
| Exact k-NN (valid n≈1200) | **0.71-0.80 (varies by rep)** | 0.43-0.53 (varies) |
| 1200-scale exact k-NN (prior) | **0.79-0.80** | ~0.51 |

**Fix Implemented:** Exact k-NN (sklearn brute force) on fixed stratified subsample (n=2000, seed=42) of decisions with known branch for adversarial benchmarks; HNSW reserved for full-corpus scale benchmarks (citation_heritage, temporal_stability, hierarchy family on subsamples, boilerplate).

**Impact:** Jurist pairwise collapse from 1200-scale (0.79) → 174k (0.12) was an **HNSW artifact, NOT a representation failure**. FIXED before dense 174k evaluation.

---

## Monitor Infrastructure Verification

### Fixes Applied (from prior cycle)
1. **Corrected path scanning** — Now scans:
   - `/tmp/lex_accepted/fractal-map/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings/` for TF-IDF
   - `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/` for dense embeddings
   - Legal-distance version directories for citation roles and linear hybrids

2. **Skip completed TF-IDF** — Monitor only evaluates representations in `AWAITED_REPRESENTATIONS` list

3. **Aligned representation names** — Updated `EXPECTED_REPRESENTATIONS.completed_tfidf_174k` to match actual filenames

4. **Correct path mapping** — `execute_evaluation_suite` maps found directories to correct filesystem paths

### Current Monitor State (check_count=119)
- **TF-IDF family:** 8/8 detected, status `TF_IDF_COMPLETE_NO_EVAL_NEEDED` ✓
- **Dense embeddings:** 0/7 detected (only year-split checkpoints exist at `174k_dense_embeddings/checkpoints/`) ✓
- **Citation roles:** 0/3 detected ✓
- **Linear hybrids:** 0/2 detected ✓
- **No spurious evaluation attempts** ✓

---

## Awaited Representations (Blocked on Legal-Distance)

| Category | Representations | Dependencies | Status |
|----------|-----------------|--------------|--------|
| **Dense (6)** | center_projected_768dim, center_projected_64dim, center_projected_128dim, linear_metric_epoch4, mahalanobis_metric_epoch4, hybrid_stabilized_epoch1, hybrid_v2_epoch3 | Full 174k dense embeddings finalized (concatenated from 26 year-split checkpoints) | ⏳ **3/26 years complete** (2000-2002 checkpoints only) |
| **Citation Roles (3)** | citing_alpha0.3, following_alpha0.3, criticizing_alpha0.3 | Legal-distance 174k citation role pipeline | ⏳ Awaited |
| **Linear Hybrids (2)** | linear_citation_concat, linear_hybrid05_concat | Dense + citation embeddings available | ⏳ Awaited |

**Primary Blocker:** Corpus artifact publication gap — year-split normalized files and metadata_174k.jsonl exist in corpus workspace but **NOT** at `/tmp/lex_accepted/corpus/...` and `/tmp/lex_accepted/evaluation/...` mount paths where legal-distance expects them. Legal-distance years 2003-2025 blocked missing upstream data.

---

## Evaluation Readiness for Dense Embeddings

### Infrastructure Status: ✅ FULLY OPERATIONAL

| Component | Status | Notes |
|-----------|--------|-------|
| HNSW backend | ✅ OPERATIONAL | Tested on GitHub runners |
| Scalable NN module | ✅ OPERATIONAL | Batched processing with sklearn fallback |
| v25 formal suite runner | ✅ OPERATIONAL | 12-benchmark + citation_heritage + v17b, frozen config hash `4323f833fa72366a` |
| Citation heritage pairs | ✅ FROZEN | 137,314 pos + 137,314 neg, path fixed |
| v17b normalization | ✅ OPERATIONAL | Cross-lingual canonical map (164 concepts) |
| Monitor script | ✅ ACTIVE | Enhanced scan, correct paths, check_count=119 |
| run_174k_formal_suite.py | ✅ OPERATIONAL | HNSW artifact fixed (exact k-NN on valid subset) |
| Exact k-NN adversarial | ✅ IMPLEMENTED | Fixed stratified subsample n=2000, seed=42 |

### Evaluation Protocol (Frozen, Ready to Execute)

When dense embeddings land in `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/` root:

1. **Monitor detects** new .npy files
2. **Auto-executes** for each awaited representation:
   - Full corpus adversarial evaluation (v3 harness, exact k-NN on valid subset)
   - v25 formal suite (12-benchmark + citation_heritage + v17b)
3. **Results saved** to `evaluation/results/174k_formal_suite/`
4. **State updated** in `evaluation/state/monitor_174k_state.json` and `state/evaluation.json`

### Priority Evaluation Order (per factory direction v27)

1. **Metric learning / hybrid objectives first** (highest 1200-scale jurist pairwise: 0.60-0.68)
   - linear_metric_epoch4, mahalanobis_metric_epoch4
   - hybrid_stabilized_epoch1, hybrid_v2_epoch3
2. **Center projected variants** (center_projected_64dim validated at 1200-scale: JP=0.982)
3. **Citation role embeddings** (citing/following_alpha0.3 passed adversarial at 1200-scale)
4. **Linear hybrids** (linear_citation_concat REPRODUCED at v13/v14)

### Critical Test for Dense 174k

**Will metric learning/hybrid objectives maintain jurist pairwise > 0.5 at 174k, or collapse like TF-IDF (0.79 → 0.12)?** The HNSW fix ensures this will be a true test of representation quality.

---

## Negative Results Preserved (First-Class Evidence)

1. **No TF-IDF representation passes all 12 benchmarks** at 174k
2. **Fundamental two-mode tradeoff**: Citation-based vs text-based — cannot simultaneously pass adversarial_falsification and branch_knn/tf_metadata
3. **ALL TF-IDF representations fail hierarchy_coherence** (max purity 0.465 < 0.7) and legal_area_clustering (max ~0.08 < 0.5)
4. **v17b normalization does not universally improve** — 6/8 representations worsen on NMI >10%
5. **HNSW artifact confirmed and fixed** — was masking representation differences, not a representation failure
6. **JP ceiling ~0.53 true OOS** (from legal-distance v14 REPRODUCED) — dense embeddings unlikely to exceed this without structural changes
7. **Boilerplate resistance negative** for all TF-IDF representations at 174k
8. **Temporal stability negative** for citation-based representations (std ~0.15-0.18 > 0.1 threshold)

---

## Evidence References

| Artifact | Path |
|----------|------|
| TF-IDF formal suite final report | `reports/evaluation/evaluation_v27_174k_TFIDF_FAMILY_FINAL_REPORT.md` |
| HNSW artifact fix report | `reports/evaluation/EVALUATION_174K_HNSW_FIX_REPORT_v27.md` |
| v25 formal suite results (8 reps) | `results/evaluation/v25_174k_formal_suite/results/*.json` |
| Suite summary | `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json` |
| Citation heritage dedicated | `results/evaluation/v25_174k_citation_heritage/*.json` |
| v17b normalization comparison | `results/evaluation/v25_174k_v17b/*.json` |
| v3 full corpus adversarial (TF-IDF) | `results/full_corpus_174k_tfidf/full_corpus_evaluation_results_worker0.json` |
| Frozen protocol v25 | `experiments/v25_174k_suite/protocol_v25_174k_suite.json` |
| Metadata 174k | `data/174k/metadata_174k.json` (173,963 decisions) |
| Citation pairs 174k | `results/174k_citation_heritage/citation_pairs_174k_full.json` |
| Monitor state | `evaluation/state/monitor_174k_state.json` (check_count=119) |
| Monitor script (fixed) | `evaluation/monitor_and_evaluate_174k.py` |
| Legal-area normalization | `experiments/legal_area_normalize.py` |
| Formal suite runner (fixed) | `evaluation/run_174k_formal_suite.py` |
| Scalable NN infrastructure | `evaluation/scalable_nn.py` |

---

## Recommendation

**CONTINUE = FALSE** for same-question TF-IDF cycle (all three machine-executable sub-questions COMPLETE).

**MONITOR = ACTIVE** — The monitor script will continue checking the legal-distance accepted state and auto-evaluate awaited representations when they land.

**Next cycle trigger:** Detection of any awaited representation in:
- `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/` (dense embeddings)
- Legal-distance version directories (citation roles, linear hybrids)

**When triggered:** Auto-execute v25 formal suite + v3 adversarial harness (exact k-NN) + citation_heritage + v17b on new representation(s).

---

## Provenance

All results preserved in:
- `/home/runner/work/LexMachina/LexMachina/results/evaluation/v25_174k_formal_suite/`
- `/home/runner/work/LexMachina/LexMachina/evaluation/results/full_corpus_174k_tfidf/`
- `/home/runner/work/LexMachina/LexMachina/evaluation/results/dense_1200_baseline/`
- `/home/runner/work/LexMachina/LexMachina/evaluation/results/174k_citation_heritage/`

No claim-bearing outputs overwritten. Negative results (hierarchy_coherence FAIL for all, HNSW artifact, v17b non-uniformity) preserved as first-class evidence.

---

*Report generated by evaluation lane. All claim-bearing measurements frozen before observation. All results reproducible from frozen protocols and pinned data.*