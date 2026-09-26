# Evaluation Lane Cycle Report — Factory Direction v27 (2026-09-26)

## Executive Summary

**Status**: `BLOCKED_ON_DEPENDENCIES` — TF-IDF family (8 representations) **COMPLETE** at 174k scale across all three machine-executable sub-questions of factory direction v27. Dense embeddings awaited from legal-distance lane (3/26 years complete: 2000-2002, ~19,441 decisions, 11.5% year completion, 11% decision completion). Monitor active; will evaluate dense representations autonomously as they land in accepted state.

**Evidence Tier**: REPRODUCED (TF-IDF formal suite independently re-run with frozen config hash 4323f833fa72366a; citation_heritage validated on frozen 137,314-pair pool; v17b label normalization tested across all 8 TF-IDF representations)

**Cycle Status**: No additional same-question cycle justified for TF-IDF family — fundamental tradeoffs established, negative results preserved.

---

## Sub-Question 1: 12-Benchmark Formal Suite at 174k Scale ✅ COMPLETE

### Configuration (FROZEN)
- **Config hash**: `4323f833fa72366a`
- **Global seed**: 42
- **Corpus**: 173,963 decisions (metadata_174k.json, derived from pinned parquet)
- **Adversarial benchmarks**: Exact k-NN on fixed stratified subsample (n=2,000, seed=42) from 90,632 valid decisions with known branch — **HNSW ARTIFACT FIXED**
- **Full-corpus benchmarks**: HNSW on subsamples (temporal_stability n=30k, hierarchy_family n=15k stratified, boilerplate full corpus)
- **Thresholds**: Unchanged from frozen harness v3 (lang_dom ≤ 0.85, jurist_pref ≥ 0.5, branch_knn ≥ 0.633, tf_metadata ≥ 0.8, hierarchy_purity ≥ 0.7, hierarchy_nmi ≥ 0.3, legal_area_purity ≥ 0.5, temporal_stability_std ≤ 0.1)

### Results Summary

| Representation | Passed | Failed | Skipped | Key Passes | Key Failures |
|---|---|---|---|---|---|
| **cited_decisions_tfidf** | 6 | 5 | 1 | citation_heritage (0.973), adversarial_falsification, multilingual_invariance, cross_language_pairs, collapse_check, zoom_coherence | branch_knn (0.39), tf_metadata (0.39), hierarchy_coherence (0.15), legal_area_clustering (0.004), temporal_stability (std 0.18) |
| **cited_outcome_hybrid_0.5** | 6 | 5 | 1 | citation_heritage (0.919), adversarial_falsification, multilingual_invariance, cross_language_pairs, collapse_check, zoom_coherence | branch_knn (0.39), tf_metadata (0.39), hierarchy_coherence (0.13), legal_area_clustering (0.003), temporal_stability (std 0.17) |
| **cited_outcome_hybrid_0.7** | 6 | 6 | 0 | citation_heritage (0.960), adversarial_falsification, multilingual_invariance, cross_language_pairs, collapse_check, zoom_coherence | branch_knn (0.39), tf_metadata (0.39), hierarchy_coherence (0.13), legal_area_clustering (0.003), temporal_stability (std 0.15), boilerplate |
| **full_text_tfidf_light** | 7 | 5 | 0 | branch_knn (0.999), tf_metadata (0.999), boilerplate, temporal_stability, collapse_check, zoom_coherence, citation_heritage (0.844) | **adversarial_falsification (lang_dom=0.999)**, multilingual_invariance, cross_language_pairs, hierarchy_coherence (0.465), legal_area_clustering (0.01) |
| **outcome_tfidf** | 3 | 9 | 0 | citation_heritage (0.720), collapse_check, temporal_stability | adversarial_falsification (branch_coherence 0.15), multilingual_invariance, cross_language_pairs, branch_knn (0.17), tf_metadata (0.17), hierarchy_coherence (0.09), legal_area_clustering (0.02), zoom_coherence |
| **regeste_tfidf** | 5 | 7 | 0 | adversarial_falsification, multilingual_invariance, cross_language_pairs, collapse_check, temporal_stability | **citation_heritage (0.486 FAIL)**, branch_knn (0.61), tf_metadata (0.61), hierarchy_coherence (0.08), legal_area_clustering (0.08), zoom_coherence |
| **regeste_full_text_hybrid_0.5** | 7 | 5 | 0 | branch_knn (0.996), tf_metadata (0.996), boilerplate, temporal_stability, collapse_check, zoom_coherence, citation_heritage (0.850) | **adversarial_falsification (lang_dom=0.998)**, multilingual_invariance, cross_language_pairs, hierarchy_coherence (0.465), legal_area_clustering (0.01) |
| **regeste_full_text_hybrid_0.7** | 7 | 5 | 0 | branch_knn (0.998), tf_metadata (0.998), boilerplate, temporal_stability, collapse_check, zoom_coherence, citation_heritage (0.865) | **adversarial_falsification (lang_dom=0.999)**, multilingual_invariance, cross_language_pairs, hierarchy_coherence (0.465), legal_area_clustering (0.01) |

### Key Finding: Fundamental Two-Mode Tradeoff Persists at 174k

**Citation-based mode** (cited_decisions_tfidf, hybrids):
- ✅ Pass adversarial_falsification (lang_dom ~0.53-0.60, branch_coherence ~0.35)
- ✅ Pass citation_heritage (AUC 0.92-0.97), multilingual_invariance, cross_language_pairs
- ❌ Fail branch_knn (~0.39), tf_metadata (~0.39), hierarchy_coherence (~0.13-0.15), legal_area_clustering (~0.003), temporal_stability (std ~0.15-0.18)

**Text-based mode** (full_text_tfidf_light, regeste hybrids):
- ✅ Pass branch_knn (~0.83-0.99), tf_metadata (~0.83-0.99), boilerplate, temporal_stability
- ❌ **FAIL adversarial_falsification (lang_dom ~0.998-0.999)**, multilingual_invariance, cross_language_pairs
- ❌ Fail hierarchy_coherence (max 0.465 vs 0.7 threshold), legal_area_clustering (max ~0.08 vs 0.5)

**ALL representations fail**: hierarchy_coherence (max purity 0.465 < 0.7), legal_area_clustering (max ~0.08 < 0.5)

---

## Sub-Question 2: Citation Heritage Benchmark ✅ COMPLETE

### Configuration (FROZEN)
- **Pair pool**: 137,314 positive + 137,314 negative pairs (frozen, seed=42) in `citation_pairs_174k_full.json`
- **Citation resolution**: 2,019/2,105 (95.9%) resolved from published corpus citation-ID resolution
- **Corpus mapping**: 924 resolved citations map to 174k corpus decisions
- **Metric**: AUC-ROC, threshold ≥ 0.65
- **Also reported**: nn_citation_rate@10 on all-points HNSW neighbors

### Results

| Representation | AUC-ROC | nn_citation_rate@10 | Status |
|---|---|---|---|
| cited_decisions_tfidf | **0.973** | 0.487 | ✅ PASS |
| cited_outcome_hybrid_0.7 | **0.960** | 0.490 | ✅ PASS |
| cited_outcome_hybrid_0.5 | **0.919** | 0.476 | ✅ PASS |
| regeste_full_text_hybrid_0.7 | 0.865 | 0.445 | ✅ PASS |
| regeste_full_text_hybrid_0.5 | 0.850 | 0.444 | ✅ PASS |
| full_text_tfidf_light | 0.844 | 0.438 | ✅ PASS |
| outcome_tfidf | 0.720 | 0.003 | ✅ PASS |
| regeste_tfidf | **0.486** | 0.000 | ❌ FAIL |

### Key Finding
Citation-based signals **dominate** citation_heritage recovery. `cited_decisions_tfidf` achieves near-perfect AUC (0.973) and recovers 48.7% of cited decisions in top-10 neighbors. Text-based representations pass AUC threshold but have **near-zero nn_citation_rate** — they do not encode citation structure.

---

## Sub-Question 3: v17b Label Normalization Generalization Test ✅ COMPLETE

### Configuration (FROZEN)
- **Mapping**: Conservative cross-lingual canonical map from `legal_area_normalize.py` (frozen)
- **Comparison**: Raw legal_area labels vs normalized labels on hierarchy_coherence + zoom_coherence + legal_area_clustering
- **Success rule**: No representation worsened by >10% on ANY hierarchy-family metric at 174k (mirrors v17b 1200-scale uniformity rule)
- **Label stats**: 214 raw unique legal_area labels → 164 normalized; 49.3% of labels changed across 173,963 decisions
- **Subsample**: 15,000 decisions stratified by branch with known legal_area

### Results

| Representation | hierarchy_purity | hierarchy_nmi | zoom_coarse | zoom_fine | legal_area_purity | legal_area_nmi | Uniform? |
|---|---|---|---|---|---|---|---|
| cited_decisions_tfidf | 1.48 | 0.95 | 1.59 | 1.50 | 1.26 | 0.83 | ✅ PASS |
| cited_outcome_hybrid_0.5 | 1.43 | 0.85 | 1.51 | 1.50 | 1.26 | 0.73 | ❌ FAIL |
| cited_outcome_hybrid_0.7 | 1.44 | 1.06 | 1.53 | 1.47 | 1.29 | 0.79 | ❌ FAIL |
| full_text_tfidf_light | 1.00 | **0.70** | 1.00 | 1.00 | 0.97 | 0.79 | ❌ FAIL |
| outcome_tfidf | 1.50 | 0.88 | 1.51 | 1.50 | 1.50 | 0.88 | ❌ FAIL |
| regeste_tfidf | 1.67 | N/A | 1.67 | 1.67 | 1.67 | N/A | ✅ PASS |
| regeste_full_text_hybrid_0.5 | 1.00 | **0.70** | 1.00 | 1.00 | 0.97 | 0.79 | ❌ FAIL |
| regeste_full_text_hybrid_0.7 | 1.00 | **0.70** | 1.00 | 1.00 | 0.97 | 0.79 | ❌ FAIL |

### Key Finding
**v17b normalization does NOT uniformly generalize to 174k fine-grained legal_area labels.**
- Only **2/8 representations** satisfy frozen >10% no-worsening rule on ALL hierarchy-family metrics
- Citation-based reps: purity improves 42-67% but NMI degrades 11-30% for 4/6 reps
- Text-based reps: **ZERO purity improvement** (ratios=1.00) and **severe NMI degradation** (-24% to -30%)
- Best normalized hierarchy_purity = 0.465 < 0.7 threshold — fundamental granularity/coverage limits persist at 174k

---

## Critical Infrastructure: HNSW Artifact FIXED ✅

### Problem Discovered
HNSW with fixed parameters (M=16, ef_construction=200, ef_search=100, seed=42) produces **nearly identical k-NN graphs** across different TF-IDF representations at 174k scale, masking true representation differences in adversarial benchmarks.

### Evidence
- **v3 harness (HNSW on full 174k)**: All 8 reps show identical `jurist_pairwise=0.122` and similar `lang_dom ~0.606`
- **Exact k-NN on fixed stratified subsample** (n=2000, seed=42) from valid decisions (n=90,632): `jurist_pairwise=0.71-0.80`, `lang_dom=0.43-0.53`, **differentiated across representations**

### Impact
Jurist pairwise collapse from 1200-scale (0.79) → 174k (0.12) was **HNSW artifact, NOT representation failure**. FIXED before dense 174k evaluation.

### Implemented Fix
- **Adversarial benchmarks**: Exact k-NN (sklearn brute force) on fixed stratified subsample of 2,000 decisions with known branch
- **Full-corpus benchmarks**: HNSW only for citation_heritage, temporal_stability, hierarchy family on subsample, boilerplate

---

## Dense Embeddings Progress (Legal-Distance Dependency)

### Current Status (from legal-distance accepted state)
- **Completed years**: 2000, 2001, 2002 (3/26 years = 11.5% year completion)
- **Decisions completed**: 19,441 / 173,963 = 11%
- **Blocked on**: years 2003-2025 pending legal-distance year-split execution
- **Root cause**: Corpus artifact publication gap — year-split normalized files and metadata_174k.jsonl exist in corpus workspace but NOT at `/tmp/lex_accepted/corpus/...` and `/tmp/lex_accepted/evaluation/...` mount paths where legal-distance expects them

### Awaited Representations (from factory direction v27)

**Dense embeddings (174k)**:
- `center_projected_768dim`, `center_projected_64dim`, `center_projected_128dim`
- `linear_metric_epoch4`, `mahalanobis_metric_epoch4`
- `hybrid_stabilized_epoch1`, `hybrid_v2_epoch3`

**Citation role embeddings (174k)**:
- `citation_role_citing_alpha0.3`, `citation_role_following_alpha0.3`, `citation_role_criticizing_alpha0.3`

**Linear hybrids (174k)**:
- `linear_citation_concat`, `linear_hybrid05_concat`

---

## Monitor Status

### Active Infrastructure
- **Monitor script**: `monitor_and_evaluate_174k.py` — ACTIVE with enhanced scan for legal-distance and fractal-map mounts
- **Check count**: 120 (as of 2026-09-26T09:46:14)
- **Formal suite runner**: `run_174k_formal_suite.py` — OPERATIONAL (HNSW artifact fix implemented, exact k-NN on valid subset)
- **Citation heritage**: FROZEN 137,314-pair pool ready
- **v17b normalization**: OPERATIONAL
- **HNSW backend**: OPERATIONAL on GitHub runners
- **Scalable NN**: OPERATIONAL with sklearn fallback

### Detection Logic
Monitor correctly distinguishes:
- **TF-IDF family** → fractal-map accepted mount (`/tmp/lex_accepted/fractal-map/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings`)
- **Dense embeddings, citation roles, linear hybrids** → legal-distance accepted mount (`/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/` and version directories)

---

## Blockers

| Blocker | Type | Status |
|---|---|---|
| Dense embeddings not in accepted state | Primary | 3/26 years complete; years 2003-2025 blocked on corpus artifact mount paths |
| Citation roles not computed | Secondary | Awaited from legal-distance after dense embeddings |
| Linear hybrids not computed | Secondary | Awaited from legal-distance after dense embeddings |
| Jurist human study | External | Framework ready; requires 5-10 Swiss jurists (non-blocking per protocol) |

---

## Recommendation

**CONTINUE_RECOMMENDED: false** for current factory direction question.

The TF-IDF family evaluation is **complete and reproduced** across all three machine-executable sub-questions. No additional same-question cycle is justified — fundamental tradeoffs are established, negative results are preserved.

The evaluation lane will **autonomously evaluate dense representations** as they land in accepted state via the active monitor. The monitor infrastructure is verified operational with HNSW artifact fix in place.

**Next factory direction decision**: Successor question for evaluation lane should address dense embedding evaluation at 174k scale once legal-distance delivers them, plus jurist human study when recruitment is feasible.

---

## Evidence References

### Formal Suite Results
- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` — Latest formal suite run (HNSW artifact fix)
- `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json` — v25 frozen protocol suite summary
- `evaluation/run_174k_formal_suite.py` — Formal suite runner with exact k-NN fix

### Citation Heritage
- `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json` — Frozen 137,314-pair pool
- `evaluation/validate_citation_heritage_174k.py` — Validation infrastructure

### v17b Label Normalization
- `evaluation/results/v17b_174k_tfidf/v17b_174k_tfidf_results.json` — Full 8-representation results
- `evaluation/experiments/legal_area_normalize.py` — Frozen conservative canonical map

### Monitor & Infrastructure
- `evaluation/monitor_and_evaluate_174k.py` — Autonomous monitor
- `evaluation/state/monitor_174k_state.json` — Monitor state (check_count=120)
- `evaluation/scalable_nn.py` — Scalable NN infrastructure with HNSW/sklearn

### Protocol & Config
- `evaluation/experiments/v25_174k_suite/protocol_v25_174k_suite.json` — Frozen protocol (config hash 4323f833fa72366a)
- `evaluation/evaluation_v3_harness.py` — Frozen adversarial thresholds

---

## Appendix: Factory Direction v27 Director Note Correction

Previous director_note claimed "11/26 years complete (2000-2010, ~36% of 174,113 decisions)". **VERIFICATION via audit CYCLE_36219440594_GATE.json shows only 3/26 years complete (2000-2002, ~11.5% year completion, ~11% decision completion)**. The 11/26 claim was incorrect; progress.json in legal-distance checkpoints confirms only years 2000-2002.