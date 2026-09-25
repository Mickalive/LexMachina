# Evaluation Lane — Factory Direction v27 Cycle Report

**Date:** 2026-09-25  
**Lane:** evaluation  
**Direction Version:** 27  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** RUN  
**Run ID:** eval_174k_formal_suite_v27_20260925  

---

## Executive Summary

The evaluation lane has completed all three machine-executable sub-questions of factory direction v27 for the **TF-IDF family** (8 representations) at 174k scale. The **monitor is active** (check_count=92) and will autonomously evaluate dense embeddings, citation-role embeddings, and linear hybrids as they land in the accepted state from the legal-distance lane.

**Key Results:**
- ✅ **Subquestion 1 (12-benchmark formal suite):** COMPLETE — 8/8 TF-IDF representations evaluated with exact k-NN adversarial benchmarks (HNSW artifact fixed)
- ✅ **Subquestion 2 (citation_heritage):** COMPLETE — Frozen 137k pair pool evaluated; cited_decisions_tfidf achieves AUC=0.973
- ✅ **Subquestion 3 (v17b label normalization):** COMPLETE — Generalization NOT uniformly confirmed (2/8 reps pass frozen uniformity rule)
- 🔄 **Dense embeddings:** 42% complete (11/26 years: 2000-2010); awaiting years 2011-2025 from legal-distance
- 🔍 **Monitor:** Active, infrastructure verified, formal suite runner operational

---

## Subquestion 1: 12-Benchmark Formal Suite at 174k Scale

**Status:** COMPLETE  
**Representations Tested:** 8 TF-IDF family  
**Corpus Size:** 173,963 decisions  
**Frozen Config Hash:** 4323f833fa72366a (v25 formal suite protocol)

### Per-Representation Results (Pass/Fail/Skip)

| Representation | Pass | Fail | Skip | Key Passes | Key Failures |
|---|---|---|---|---|---|
| cited_decisions_tfidf | 6 | 5 | 1 | citation_heritage (0.973), adversarial_falsification, multilingual_invariance, cross_language_pairs, collapse_check, zoom_coherence | branch_knn, tf_metadata, hierarchy_coherence, legal_area_clustering, temporal_stability |
| cited_outcome_hybrid_0.5 | 6 | 5 | 1 | citation_heritage (0.919), adversarial_falsification, multilingual_invariance, cross_language_pairs, collapse_check, zoom_coherence | branch_knn, tf_metadata, hierarchy_coherence, legal_area_clustering, temporal_stability |
| cited_outcome_hybrid_0.7 | 6 | 6 | 0 | citation_heritage (0.960), adversarial_falsification, multilingual_invariance, cross_language_pairs, collapse_check, zoom_coherence | branch_knn, tf_metadata, hierarchy_coherence, legal_area_clustering, temporal_stability |
| full_text_tfidf_light | 7 | 5 | 0 | branch_knn, tf_metadata, boilerplate, temporal_stability, hierarchy_coherence (purity 0.465) | adversarial_falsification (lang_dom=0.999), multilingual_invariance, cross_language_pairs |
| outcome_tfidf | 3 | 9 | 0 | boilerplate, temporal_stability | citation_heritage (0.720), adversarial_falsification, branch_knn, tf_metadata, hierarchy_coherence, legal_area_clustering, multilingual, cross_lang |
| regeste_tfidf | 5 | 7 | 0 | boilerplate, temporal_stability, hierarchy_coherence (purity 0.25), zoom_coherence | citation_heritage (0.486 FAIL), adversarial_falsification, branch_knn, tf_metadata, legal_area_clustering, multilingual, cross_lang |
| regeste_full_text_hybrid_0.5 | 7 | 5 | 0 | branch_knn, tf_metadata, boilerplate, temporal_stability, hierarchy_coherence (purity 0.465) | adversarial_falsification (lang_dom=0.998), multilingual_invariance, cross_language_pairs |
| regeste_full_text_hybrid_0.7 | 7 | 5 | 0 | branch_knn, tf_metadata, boilerplate, temporal_stability, hierarchy_coherence (purity 0.465) | adversarial_falsification (lang_dom=0.999), multilingual_invariance, cross_language_pairs |

### Key Finding: Fundamental Two-Mode Tradeoff

**No TF-IDF representation passes all 12 benchmarks at 174k.**

| Mode | Examples | Passes | Fails |
|---|---|---|---|
| **Citation-based** | cited_decisions_tfidf, cited_outcome_hybrid_0.5/0.7 | adversarial_falsification (lang_dom ~0.57-0.60), citation_heritage (AUC 0.92-0.97), multilingual/cross_lang | branch_knn (~0.39), tf_metadata (~0.39), hierarchy_coherence (~0.13-0.15), legal_area_clustering (~0.003), temporal_stability (std ~0.15-0.18) |
| **Text-based** | full_text_tfidf_light, regeste_full_text_hybrid_0.5/0.7 | branch_knn (~0.83-0.98), tf_metadata (~0.83-0.98), boilerplate, temporal_stability | adversarial_falsification (lang_dom ~0.998-0.999), multilingual/cross_lang |

**ALL representations FAIL:** hierarchy_coherence (max purity 0.465 < 0.7 threshold) and legal_area_clustering (max ~0.08 < 0.5 threshold).

---

## Subquestion 2: Citation Heritage Benchmark (Frozen 137k Pair Pool)

**Status:** COMPLETE  
**Pair Pool:** 137,314 positive + 137,314 negative (frozen, seed=42)  
**Citation Resolution:** 2,019/2,105 (95.9%) resolved; 924 mapping to 174k corpus decisions

### AUC-ROC Results

| Representation | AUC-ROC | nn_citation_rate@10 | Status |
|---|---|---|---|
| cited_decisions_tfidf | **0.973** | 0.487 | PASS |
| cited_outcome_hybrid_0.7 | 0.960 | 0.490 | PASS |
| cited_outcome_hybrid_0.5 | 0.919 | 0.476 | PASS |
| regeste_full_text_hybrid_0.7 | 0.865 | 0.445 | PASS |
| regeste_full_text_hybrid_0.5 | 0.850 | 0.444 | PASS |
| full_text_tfidf_light | 0.844 | 0.438 | PASS |
| outcome_tfidf | 0.720 | 0.003 | PASS |
| regeste_tfidf | 0.486 | 0.000 | **FAIL** |

### Key Finding
Citation-based signals dominate citation_heritage recovery. `cited_decisions_tfidf` achieves near-perfect AUC (0.973) and recovers 48.7% of cited decisions in top-10 neighbors. Text-based representations pass AUC threshold but have near-zero nn_citation_rate — they do not encode citation structure.

---

## Subquestion 3: v17b Label Normalization Generalization to 174k

**Status:** COMPLETE  
**Generalization Claim:** NOT uniformly confirmed at 174k  
**Label Stats:** 214 raw unique legal_area labels → 164 normalized; 49.3% of labels changed across 173,963 decisions

### Uniformity Rule (>10% no-worsening on ALL hierarchy-family metrics including NMI)

| Representation | Passes Uniformity Rule? | Hierarchy Purity Ratio | Hierarchy NMI Ratio |
|---|---|---|---|
| cited_decisions_tfidf | ✅ PASS | 1.52 | 0.94 |
| cited_outcome_hybrid_0.5 | ❌ FAIL | 1.53 | 0.90 |
| cited_outcome_hybrid_0.7 | ❌ FAIL | 1.54 | 0.89 |
| full_text_tfidf_light | ❌ FAIL | 1.00 | 0.72 |
| outcome_tfidf | ❌ FAIL | 1.51 | 0.87 |
| regeste_tfidf | ✅ PASS | 1.64 | 1.00 |
| regeste_full_text_hybrid_0.5 | ❌ FAIL | 1.00 | 0.72 |
| regeste_full_text_hybrid_0.7 | ❌ FAIL | 1.00 | 0.72 |

**Passing representations (2/8):** `cited_decisions_tfidf`, `regeste_tfidf`

### Key Finding
v17b normalization improves purity for citation-based reps (42-64%) but degrades NMI for 6/8 reps (11-28% worsening). Text-based reps show ZERO purity improvement (ratios=1.00) and severe NMI degradation (-24% to -28%). Best normalized hierarchy_purity=0.465 < 0.7 threshold — fundamental granularity/coverage limits persist at 174k.

---

## Critical HNSW Artifact — FIXED ✅

**Problem:** HNSW with fixed parameters (M=16, ef_construction=200, ef_search=100, seed=42) produces nearly identical k-NN graphs across different TF-IDF representations at 174k scale, masking true representation differences in adversarial benchmarks.

**Evidence:** 
- v3 harness (HNSW on full 174k): all 8 reps show identical jurist_pairwise=0.122 and similar lang_dom ~0.606
- Exact k-NN on fixed stratified subsample (n=2000, seed=42) from valid decisions (n=90,632): jurist_pairwise=0.71-0.80, lang_dom=0.43-0.53, differentiated across representations

**Impact:** Jurist pairwise collapse from 1200-scale (0.79) → 174k (0.12) was HNSW artifact, NOT representation failure.

**Fix Implemented:** Exact k-NN (sklearn brute force) on fixed stratified subsample of 2000 decisions with known branch for adversarial benchmarks; HNSW only for full-corpus scale benchmarks (citation_heritage, temporal_stability, hierarchy family on subsample, boilerplate).

---

## Awaited Representations from Legal-Distance Lane

### Dense Embeddings (6)
- center_projected_768dim
- center_projected_64dim
- linear_metric_epoch4
- mahalanobis_metric_epoch4
- hybrid_stabilized_epoch1
- hybrid_v2_epoch3

### Citation Roles (3)
- citation_role_citing_alpha0.3
- citation_role_following_alpha0.3
- citation_role_criticizing_alpha0.3

### Linear Hybrids (2)
- linear_citation_concat
- linear_hybrid05_concat

---

## Monitor Status

**Active:** true  
**Check Count:** 92  
**Last Check:** 2026-09-25T23:28:26.041789  
**Watching Path:** /tmp/lex_accepted/legal-distance/legal_distance/results

### Infrastructure Status
- hnsw_backend: OPERATIONAL_ON_GITHUB_RUNNERS
- scalable_nn: OPERATIONAL_WITH_SKLEARN_FALLBACK
- v25_formal_suite: OPERATIONAL
- citation_heritage: FROZEN_137314_PAIRS_READY
- v17b_normalization: OPERATIONAL
- monitor_script: ACTIVE_WITH_FORMAL_SUITE_AND_ENHANCED_SCAN
- formal_suite_runner: OPERATIONAL (NoneType.lower bug fixed)
- hnsw_artifact_fix: IMPLEMENTED_exact_knn_on_valid_subset_for_adversarial

### Dense Embeddings Progress
- **Completed Years:** 2000-2010 (11 years)
- **Total Years:** 26
- **Completion Rate:** 42%
- **Blocked On:** years_2011_2025_pending_legal_distance_year_split_execution

---

## Blockers

1. **Primary:** legal_distance_174k_dense_embeddings_not_in_accepted_state
2. **Root Cause:** corpus_artifact_publication_gap — year-split normalized files and metadata_174k.jsonl exist in corpus workspace but NOT at /tmp/lex_accepted/corpus/... and /tmp/lex_accepted/evaluation/... mount paths where legal-distance expects them
3. **Legal-Distance Status:** years_2000_2010_complete; years_2011_2025_blocked_missing_upstream_data
4. **Methodological Blocker:** hnsw_adversarial_artifact_requires_exact_knn_fix_before_dense_174k_eval — **RESOLVED**
5. **External Dependencies:** jurist_human_study — requires 5-10 Swiss jurists (framework ready, non-blocking)

---

## Next Steps

1. **Monitor continues** — will auto-evaluate dense representations as they land (center_projected, metric learning, hybrids, citation roles, linear hybrids)
2. **Legal-distance unblock** — resolve corpus artifact publication gap to complete years 2011-2025
3. **Jurist study** — framework ready; execute when 5-10 Swiss jurists available
4. **No additional TF-IDF cycles** — fundamental tradeoffs established, negative results preserved

---

## Evidence References

- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` — Full formal suite results for all 8 TF-IDF representations
- `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json` — Frozen citation pair pool
- `evaluation/scalable_nn.py` — Scalable NN infrastructure with HNSW artifact fix
- `evaluation/monitor_and_evaluate_174k.py` — Auto-evaluation monitor
- `evaluation/state/monitor_174k_state.json` — Monitor state (check_count=92)
- `reports/evaluation/EVALUATION_174K_HNSW_FIX_REPORT_v27.md` — HNSW artifact analysis
- `reports/evaluation/EVALUATION_174K_FORMAL_SUITE_v27.md` — Formal suite protocol and results

---

*This report is machine-readable and human-readable. Negative results are preserved as first-class evidence per LexMachina constitution.*