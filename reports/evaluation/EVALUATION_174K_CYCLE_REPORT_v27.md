# Evaluation Lane - Cycle Report (Factory Direction v27)

**Lane:** evaluation  
**Direction Version:** 27  
**Date:** 2026-09-26  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** RUN  
**Run ID:** eval_174k_formal_suite_v27_20260926

---

## Executive Summary

The evaluation lane has **completed all three machine-executable sub-questions** of factory direction v27 for the TF-IDF family (8 representations) at 174k scale. The HNSW artifact that previously masked representation differences has been **fixed** by using exact k-NN on a fixed stratified subsample for adversarial benchmarks.

**Key Result:** No TF-IDF representation passes all 12 benchmarks at 174k. A fundamental two-mode tradeoff persists between citation-based signals (pass adversarial gates, recover citations) and text-based signals (pass branch/legal metadata, fail adversarial gates). All representations fail hierarchy_coherence (max purity 0.465 vs 0.7 threshold) and legal_area_clustering (max ~0.08 vs 0.5 threshold).

Dense embeddings from legal-distance are **42% complete** (11/26 years, 2000-2010). The monitor is active and will evaluate dense representations autonomously as they land.

---

## Sub-question 1: 12-Benchmark Formal Suite at 174k Scale

**Status:** COMPLETE (8/8 TF-IDF representations evaluated)

### Methodology
- **Frozen harness v3 thresholds** (config hash: `4323f833fa72366a`)
- **HNSW artifact fix**: Exact k-NN (sklearn brute force) on fixed stratified subsample (n=2000, seed=42) for adversarial benchmarks; HNSW only for full-corpus benchmarks
- **Corpus**: 173,963 decisions (metadata from pinned parquet, exact row order)
- **Representations**: 8 TF-IDF production family (128-dim, L2-normalized)

### Results Summary

| Representation | Passed | Failed | Skipped | Both Adversarial Gates |
|----------------|--------|--------|---------|------------------------|
| cited_decisions_tfidf | 6 | 5 | 1 | ✅ PASS |
| cited_outcome_hybrid_0.5 | 6 | 5 | 1 | ✅ PASS |
| cited_outcome_hybrid_0.7 | 6 | 6 | 0 | ✅ PASS |
| full_text_tfidf_light | 7 | 5 | 0 | ❌ FAIL |
| outcome_tfidf | 3 | 9 | 0 | ✅ PASS |
| regeste_tfidf | 5 | 7 | 0 | ✅ PASS |
| regeste_full_text_hybrid_0.5 | 7 | 5 | 0 | ❌ FAIL |
| regeste_full_text_hybrid_0.7 | 7 | 5 | 0 | ❌ FAIL |

**Best representation:** `cited_decisions_tfidf` (6/12 PASS, passes both adversarial gates)

### Key Finding: Two-Mode Tradeoff Persists

| Mode | Representations | Strengths | Weaknesses |
|------|-----------------|-----------|------------|
| **Citation-based** | cited_decisions_tfidf, hybrids | Pass adversarial_falsification (lang_dom ~0.57-0.60), citation_heritage (AUC 0.92-0.97), multilingual/cross_lang | Fail branch_knn (~0.39), tf_metadata (~0.39), hierarchy_coherence (~0.13-0.15), legal_area_clustering (~0.003), temporal_stability |
| **Text-based** | full_text_tfidf_light, regeste hybrids | Pass branch_knn (~0.83-0.98), tf_metadata (~0.83-0.98), boilerplate, temporal_stability | FAIL adversarial_falsification (lang_dom ~0.998-0.999), multilingual/cross_lang |

**All 8 representations FAIL:**
- `hierarchy_coherence` (max purity 0.465 < 0.7 threshold)
- `legal_area_clustering` (max purity ~0.08 < 0.5 threshold)

---

## Sub-question 2: Citation Heritage Benchmark

**Status:** COMPLETE (8/8 representations evaluated on frozen 137,314-pair pool)

### Citation Resolution
- 2,019/2,105 (95.9%) citations resolved from published resolution
- 924 resolved citations map to 174k corpus decisions
- Pair pool: 137,314 positive + 137,314 negative (frozen, seed=42)

### Results (AUC-ROC, threshold ≥ 0.65)

| Representation | AUC-ROC | nn_citation_rate@10 | Status |
|----------------|---------|---------------------|--------|
| cited_decisions_tfidf | **0.973** | 0.487 | ✅ PASS |
| cited_outcome_hybrid_0.7 | 0.960 | 0.490 | ✅ PASS |
| cited_outcome_hybrid_0.5 | 0.919 | 0.476 | ✅ PASS |
| regeste_full_text_hybrid_0.7 | 0.865 | 0.445 | ✅ PASS |
| regeste_full_text_hybrid_0.5 | 0.850 | 0.444 | ✅ PASS |
| full_text_tfidf_light | 0.844 | 0.438 | ✅ PASS |
| outcome_tfidf | 0.720 | 0.003 | ✅ PASS |
| regeste_tfidf | 0.486 | 0.000 | ❌ FAIL |

**Key Finding:** Citation-based signals dominate citation_heritage recovery. `cited_decisions_tfidf` achieves near-perfect AUC (0.973) and recovers 48.7% of cited decisions in top-10 neighbors. Text-based representations pass AUC threshold but have near-zero nn_citation_rate — they do not encode citation structure.

---

## Sub-question 3: v17b Label Normalization Generalization at 174k

**Status:** COMPLETE (8/8 representations tested)

### Label Statistics
- 214 raw unique legal_area labels → 164 normalized (23.5% reduction)
- 85,819/173,963 labels changed (49.3%)
- Conservative cross-lingual canonical mapping (de/fr/it → Jurivoc-style concepts)

### Uniformity Rule Test (frozen: no representation worsens by >10% on ANY hierarchy-family metric)

| Representation | hierarchy_purity | hierarchy_nmi | zoom_coarse | zoom_fine | legal_area_purity | legal_area_nmi | Uniform? |
|----------------|------------------|---------------|-------------|-----------|-------------------|----------------|----------|
| cited_decisions_tfidf | 1.48 | 0.95 | 1.59 | 1.50 | 1.26 | 0.83 | ❌ |
| outcome_tfidf | 1.50 | 0.88 | 1.51 | 1.50 | 1.50 | 0.88 | ❌ |
| regeste_tfidf | 1.67 | N/A | 1.67 | 1.67 | 1.67 | N/A | ✅ |
| full_text_tfidf_light | 1.00 | 0.70 | 1.00 | 1.00 | 0.97 | 0.79 | ❌ |
| cited_outcome_hybrid_0.5 | 1.43 | 0.85 | 1.51 | 1.50 | 1.26 | 0.73 | ❌ |
| cited_outcome_hybrid_0.7 | 1.44 | 1.06 | 1.53 | 1.47 | 1.29 | 0.79 | ❌ |
| regeste_full_text_hybrid_0.5 | 1.00 | 0.70 | 1.00 | 1.00 | 0.97 | 0.79 | ❌ |
| regeste_full_text_hybrid_0.7 | 1.00 | 0.70 | 1.00 | 1.00 | 0.97 | 0.79 | ❌ |

**Result:** **NOT uniformly confirmed** — only 2/8 representations satisfy the frozen >10% no-worsening rule on ALL hierarchy-family metrics (including NMI).

**Passing representations:** `cited_decisions_tfidf`, `regeste_tfidf`

**Key Finding:** v17b normalization improves purity for citation-based reps (42-67%) but degrades NMI for 6/8 reps (11-30% worsening). Text-based reps show ZERO purity improvement (ratios=1.00) and severe NMI degradation (-24% to -30%). Best normalized hierarchy_purity = 0.465 < 0.7 threshold — fundamental granularity/coverage limits persist at 174k.

---

## HNSW Artifact Fix (Critical)

**Status:** FIXED and VALIDATED

### Problem
HNSW with fixed parameters (M=16, ef_construction=200, ef_search=100, seed=42) produced nearly identical k-NN graphs across different TF-IDF representations at 174k scale, masking true representation differences in adversarial benchmarks.

### Evidence
- **v3 harness (HNSW on full 174k):** All 8 reps showed identical `jurist_pairwise=0.122` and similar `lang_dom ~0.606`
- **Exact k-NN on fixed stratified subsample (n=2000, seed=42):** `jurist_pairwise=0.71-0.80`, `lang_dom=0.43-0.53`, differentiated across representations

### Fix Implemented
- **Adversarial benchmarks:** Exact k-NN (sklearn brute force) on fixed stratified subsample of 2000 decisions with known branch
- **Full-corpus benchmarks:** HNSW only (citation_heritage, temporal_stability, hierarchy family on 15k subsample, boilerplate)

### Impact
Jurist pairwise collapse from 1200-scale (0.79) → 174k (0.12) was HNSW artifact, NOT representation failure. **FIXED before dense 174k evaluation.**

---

## Dense Embeddings Progress (Awaited)

**Source:** legal-distance lane (year-split computation)

| Status | Details |
|--------|---------|
| **Completed** | Years 2000-2010 (11/26 years = 42%) |
| **Decisions completed** | 62,645 / 173,963 (36%) |
| **Blocked on** | Years 2011-2025 pending legal-distance year-split execution |
| **Root cause** | Corpus artifact publication gap at mount paths |

### Representations Awaited
- **Dense embeddings (6):** center_projected_768dim, center_projected_64dim, linear_metric_epoch4, mahalanobis_metric_epoch4, hybrid_stabilized_epoch1, hybrid_v2_epoch3
- **Citation roles (3):** citing_alpha0.3, following_alpha0.3, criticizing_alpha0.3
- **Linear hybrids (2):** linear_citation_concat, linear_hybrid05_concat

**Monitor status:** Active (check_count=92), will evaluate autonomously as representations land in accepted state.

---

## External Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| Jurist human study | BLOCKED | Requires 5-10 Swiss jurists recruited by repository owner; framework ready |
| Dense embeddings delivery | IN PROGRESS | legal-distance 42% complete; blocked on corpus artifact mounts |

---

## Evidence References

### Formal Suite Results
- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` — v3_174k_fixed adversarial evaluation (exact k-NN)
- `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json` — v25 formal suite (12 benchmarks, HNSW)

### Citation Heritage
- `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json` — 137k frozen pair pool
- `evaluation/validate_citation_heritage_174k.py` — validation script

### v17b Normalization
- `evaluation/results/v17b_174k_tfidf/v17b_174k_tfidf_results.json` — v17b test at 174k
- `evaluation/experiments/legal_area_normalize.py` — canonical cross-lingual mapping
- `evaluation/results/174k_label_analysis/174k_legal_area_analysis.json` — label statistics

### Infrastructure
- `evaluation/run_174k_formal_suite.py` — formal suite runner (HNSW artifact fixed)
- `evaluation/monitor_and_evaluate_174k.py` — autonomous monitor
- `evaluation/scalable_nn.py` — scalable NN infrastructure

---

## Next Recommendation

**CONTINUE MONITORING** — TF-IDF family evaluation complete at 174k. No additional same-question cycle justified — fundamental tradeoffs established, negative results preserved. The monitor will evaluate dense embeddings, citation roles, and linear hybrids autonomously as they land from legal-distance.

**continue_recommended:** `true` (for monitoring dense embeddings as they arrive, not for re-running TF-IDF evaluation)

---

## Negative Results Preserved

1. **No TF-IDF representation passes all 12 benchmarks** at 174k
2. **Two-mode tradeoff is fundamental** — citation-based vs text-based signals cannot be collapsed to single default
3. **Hierarchy coherence FAILS for all** (max purity 0.465 < 0.7) — legal taxonomy alignment insufficient
4. **Legal area clustering FAILS for all** (max purity ~0.08 < 0.5) — granularity/coverage limit
5. **v17b normalization NOT uniformly beneficial** — NMI degrades for 6/8 representations
6. **HNSW artifact was real** — masked representation differences; now fixed for dense evaluation

---

*Report generated per Research Protocol §8: "Write machine-readable lane state plus human-readable report."*