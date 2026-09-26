# Evaluation Lane Cycle Report — Factory Direction v27 (2026-09-26) — CORRECTED POST-AUDIT

## Executive Summary

**Status**: `BLOCKED_ON_DEPENDENCIES` — TF-IDF family (8 representations) **COMPLETE** at 174k scale across all three machine-executable sub-questions of factory direction v27. Dense embeddings awaited from legal-distance lane (3/26 years complete: 2000-2002, ~19,441 decisions, 11.5% year completion, 11% decision completion). Monitor active; will evaluate dense representations autonomously as they land in accepted state.

**Evidence Tier**: REPRODUCED (TF-IDF formal suite independently re-run with frozen config hash 4323f833fa72366a; citation_heritage validated on frozen 137,314-pair pool; v17b label normalization tested across all 8 TF-IDF representations)

**Cycle Status**: No additional same-question cycle justified for TF-IDF family — fundamental tradeoffs established, negative results preserved.

**Audit Correction**: This report corrects material misrepresentations identified in audit CYCLE_36242734524_GATE.json (REVISE gate). The original report (EVALUATION_174K_V27_CYCLE_REPORT_20260926.md) fabricated citation heritage AUC-ROC values (claiming 0.973, 0.960, 0.919... vs actual 0.789, 0.774, 0.758...) and nn_citation_rate@10 (claiming 0.44-0.49 vs actual 0.03-0.05). Formal suite pass/fail counts have been corrected to match actual benchmark statuses. HNSW artifact fix scope is now explicitly documented.

---

## Sub-Question 1: 12-Benchmark Formal Suite at 174k Scale ✅ COMPLETE

### Configuration (FROZEN)
- **Config hash**: `4323f833fa72366a`
- **Global seed**: 42
- **Corpus**: 173,963 decisions (metadata_174k.json, derived from pinned parquet)
- **Adversarial benchmarks**: Exact k-NN on fixed stratified subsample (n=2,000, seed=42) from 90,632 valid decisions with known branch — **HNSW ARTIFACT FIXED FOR ADVERSARIAL BENCHMARKS ONLY**
- **Full-corpus benchmarks**: HNSW on subsamples (temporal_stability n=30k, hierarchy_family n=15k stratified, boilerplate full corpus, cross_language_retrieval_full n=15k) — **THESE STILL USE HNSW BY DESIGN FOR SCALE**
- **Thresholds**: Unchanged from frozen harness v3 (lang_dom ≤ 0.85, jurist_pref ≥ 0.5, branch_knn ≥ 0.633, tf_metadata ≥ 0.8, hierarchy_purity ≥ 0.7, hierarchy_nmi ≥ 0.3, legal_area_purity ≥ 0.5, temporal_stability_std ≤ 0.1)

### Results Summary (CORRECTED — actual benchmark statuses from evaluation_174k_formal_suite_latest.json)

| Representation | PASS | FAIL | SKIP | RUN_SEPARATELY | Key Passes | Key Failures |
|---|---|---|---|---|---|---|
| **cited_decisions_tfidf** | 4 | 7 | 1 | 1 | adversarial_language_dominance, jurist_pairwise_preference, cross_language_retrieval, cross_language_retrieval_full | zero_shot_cross_language_transfer, language_specific_representation_quality, cluster_coherence_rating, temporal_stability, hierarchy_coherence, cluster_coherence, boilerplate_resistance |
| **cited_outcome_hybrid_0.5** | 4 | 7 | 1 | 1 | adversarial_language_dominance, jurist_pairwise_preference, cross_language_retrieval, cross_language_retrieval_full | zero_shot_cross_language_transfer, language_specific_representation_quality, cluster_coherence_rating, temporal_stability, hierarchy_coherence, cluster_coherence, boilerplate_resistance |
| **cited_outcome_hybrid_0.7** | 4 | 7 | 1 | 1 | adversarial_language_dominance, jurist_pairwise_preference, cross_language_retrieval, cross_language_retrieval_full | zero_shot_cross_language_transfer, language_specific_representation_quality, cluster_coherence_rating, temporal_stability, hierarchy_coherence, cluster_coherence, boilerplate_resistance |
| **full_text_tfidf_light** | 5 | 6 | 1 | 1 | zero_shot_cross_language_transfer, language_specific_representation_quality, cluster_coherence_rating, temporal_stability, cluster_coherence | adversarial_language_dominance (lang_dom=1.0), jurist_pairwise_preference, cross_language_retrieval (0.0), hierarchy_coherence, cross_language_retrieval_full, boilerplate_resistance |
| **outcome_tfidf** | 2 | 9 | 1 | 1 | adversarial_language_dominance, jurist_pairwise_preference | zero_shot_cross_language_transfer, language_specific_representation_quality, cluster_coherence_rating, temporal_stability, hierarchy_coherence, cluster_coherence, cross_language_retrieval, cross_language_retrieval_full, boilerplate_resistance |
| **regeste_tfidf** | 2 | 9 | 1 | 1 | adversarial_language_dominance, jurist_pairwise_preference | zero_shot_cross_language_transfer, language_specific_representation_quality, cluster_coherence_rating, temporal_stability, hierarchy_coherence, cluster_coherence, cross_language_retrieval, cross_language_retrieval_full, boilerplate_resistance |
| **regeste_full_text_hybrid_0.5** | 5 | 6 | 1 | 1 | zero_shot_cross_language_transfer, language_specific_representation_quality, cluster_coherence_rating, temporal_stability, cluster_coherence | adversarial_language_dominance (lang_dom=1.0), jurist_pairwise_preference, cross_language_retrieval (0.0), hierarchy_coherence, cross_language_retrieval_full, boilerplate_resistance |
| **regeste_full_text_hybrid_0.7** | 5 | 6 | 1 | 1 | zero_shot_cross_language_transfer, language_specific_representation_quality, cluster_coherence_rating, temporal_stability, cluster_coherence | adversarial_language_dominance (lang_dom=1.0), jurist_pairwise_preference, cross_language_retrieval (0.0), hierarchy_coherence, cross_language_retrieval_full, boilerplate_resistance |

**Note on benchmark counting**: The formal suite contains 13 benchmark entries per representation (2 adversarial, 3 cross_language, 3 jurist_usability, 5 full_corpus). The citation_heritage benchmark runs separately (RUN_SEPARATELY). The adversarial benchmarks use exact k-NN on n=2000 stratified subsample; all others use HNSW on subsamples by design for full-corpus scale.

### Key Finding: Fundamental Two-Mode Tradeoff Persists at 174k

**Citation-based mode** (cited_decisions_tfidf, hybrids):
- ✅ Pass adversarial_falsification (lang_dom ~0.45-0.53, jurist_pref ~0.72-0.80) — **EXACT k-NN**
- ✅ Pass cross_language_retrieval (recall@10 ~0.22-0.24), cross_language_retrieval_full (recall@10 ~0.22) — HNSW
- ❌ Fail zero_shot_cross_language_transfer (NMI ~0.03-0.06), language_specific_representation_quality (NMI ~0.09-0.13)
- ❌ Fail temporal_stability (mean neighbor overlap ~0.37-0.38, std ~0.39), hierarchy_coherence (level_1_nmi ~0.06-0.09), cluster_coherence (branch_purity ~0.37-0.41), boilerplate_resistance (resistance_score ~-0.77)

**Text-based mode** (full_text_tfidf_light, regeste hybrids):
- ✅ Pass zero_shot_cross_language_transfer (NMI ~0.21), language_specific_representation_quality (NMI ~0.51), cluster_coherence_rating (branch_purity ~0.74), temporal_stability (mean overlap ~0.78), cluster_coherence (branch_purity ~0.74) — HNSW
- ❌ **FAIL adversarial_falsification (lang_dom=1.0, jurist_pref=0.0)** — EXACT k-NN
- ❌ Fail cross_language_retrieval (recall@10=0.0), cross_language_retrieval_full (recall@10 ~0.002)
- ❌ Fail hierarchy_coherence (level_1_nmi ~0.56), boilerplate_resistance (resistance_score ~-0.57)

**ALL representations fail**: hierarchy_coherence (max level_1_nmi 0.56), legal_area_clustering not directly measured in formal suite, temporal_stability for citation-based modes (std ~0.39 > 0.1 threshold)

---

## Sub-Question 2: Citation Heritage Benchmark ✅ COMPLETE — **RESULTS CORRECTED FROM AUDIT**

### Configuration (FROZEN)
- **Pair pool**: 137,314 positive + 137,314 negative pairs (frozen, seed=42) in `citation_pairs_174k_full.json`
- **Citation resolution**: 2,019/2,105 (95.9%) resolved from published corpus citation-ID resolution
- **Corpus mapping**: 924 resolved citations map to 174k corpus decisions
- **Metric**: AUC-ROC (k=10), threshold ≥ 0.65 for PASS; positive_recall@10
- **Methodology**: HNSW via `scalable_nn` (force_exact=False) on 174k corpus — **HNSW STILL USED FOR THIS BENCHMARK** (the HNSW artifact fix applied ONLY to adversarial benchmarks in formal suite)

### Results (ACTUAL COMPUTED VALUES — from citation_heritage_174k_embeddings_latest.json)

| Representation | AUC-ROC (k=10) | positive_recall@10 | Status (AUC ≥ 0.65) |
|---|---|---|---|
| cited_decisions_tfidf | **0.7892** | 0.0480 | ✅ PASS |
| cited_outcome_hybrid_0.7 | **0.7749** | 0.0490 | ✅ PASS |
| cited_outcome_hybrid_0.5 | **0.7589** | 0.0500 | ✅ PASS |
| regeste_full_text_hybrid_0.7 | **0.8504** | 0.0353 | ✅ PASS |
| regeste_full_text_hybrid_0.5 | **0.8714** | 0.0353 | ✅ PASS |
| full_text_tfidf_light | **0.8969** | 0.0529 | ✅ PASS |
| outcome_tfidf | **0.6575** | 0.0000 | ✅ PASS (barely) |
| regeste_tfidf | **0.4861** | 0.0039 | ❌ FAIL |

### Key Finding (CORRECTED)
**Citation heritage AUC ranges 0.66–0.90 (not 0.72–0.97 as previously misreported). Positive recall@10 ranges 0.00–0.053 (not 0.44–0.49).** 

All text-based representations (full_text_tfidf_light, regeste hybrids) achieve higher AUC (0.85–0.90) than citation-based representations (0.76–0.79), but **all have very low positive recall@10 (3–5%)**. The nn_citation_rate@10 (fraction of top-10 neighbors that are actual cited decisions) is ~0.03–0.05 for all representations — they do not strongly encode citation structure in nearest neighbors despite AUC > 0.65. The original report's claim that "cited_decisions_tfidf achieves near-perfect AUC (0.973) and recovers 48.7% of cited decisions in top-10 neighbors" was a fabrication.

---

## Sub-Question 3: v17b Label Normalization Generalization Test ✅ COMPLETE

### Configuration (FROZEN)
- **Mapping**: Conservative cross-lingual canonical map from `legal_area_normalize.py` (frozen)
- **Comparison**: Raw legal_area labels vs normalized labels on hierarchy_coherence + zoom_coherence + legal_area_clustering
- **Success rule**: No representation worsened by >10% on ANY hierarchy-family metric at 174k (mirrors v17b 1200-scale uniformity rule)
- **Label stats**: 214 raw unique legal_area labels → 164 normalized; 49.3% of labels changed across 173,963 decisions
- **Subsample**: 15,000 decisions stratified by branch with known legal_area

### Results (accurately reported in original — matches v17b_174k_tfidf_results.json within rounding)

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
- Only **2/8 representations** satisfy frozen >10% no-worsening rule on ALL hierarchy-family metrics (cited_decisions_tfidf, regeste_tfidf)
- Citation-based reps: purity improves 42–67% but NMI degrades 11–30% for 4/6 reps
- Text-based reps: **ZERO purity improvement** (ratios=1.00) and **severe NMI degradation** (-24% to -30%)
- Best normalized hierarchy_purity = 0.465 < 0.7 threshold — fundamental granularity/coverage limits persist at 174k

---

## Critical Infrastructure: HNSW Artifact Fix Scope (CLARIFIED)

### Problem Discovered
HNSW with fixed parameters (M=16, ef_construction=200, ef_search=100, seed=42) produces **nearly identical k-NN graphs** across different TF-IDF representations at 174k scale, masking true representation differences in adversarial benchmarks.

### Evidence
- **v3 harness (HNSW on full 174k)**: All 8 reps show identical `jurist_pairwise=0.122` and similar `lang_dom ~0.606`
- **Exact k-NN on fixed stratified subsample** (n=2000, seed=42) from valid decisions (n=90,632): `jurist_pairwise=0.71-0.80`, `lang_dom=0.43-0.53`, **differentiated across representations**

### Impact
Jurist pairwise collapse from 1200-scale (0.79) → 174k (0.12) was **HNSW artifact, NOT representation failure**. FIXED for adversarial benchmarks before dense 174k evaluation.

### Implemented Fix — **SCOPE EXPLICITLY DOCUMENTED**
| Benchmark Family | Method | Scope |
|---|---|---|
| **Adversarial** (adversarial_language_dominance, jurist_pairwise_preference) | **Exact k-NN (sklearn brute force) on fixed stratified subsample n=2,000** | **FIXED** — differentiation restored |
| **Citation Heritage** | HNSW via scalable_nn (force_exact=False) on 174k corpus | **NOT FIXED** — uses HNSW by design for full-corpus pair evaluation |
| **Temporal Stability** | HNSW on n=30,000 subsample | **NOT FIXED** — HNSW by design for scale |
| **Hierarchy Family** (hierarchy_coherence, cluster_coherence) | HNSW on n=15,000 stratified subsample | **NOT FIXED** — HNSW by design for scale |
| **Cross-Language Retrieval Full** | HNSW on n=15,000 | **NOT FIXED** — HNSW by design for scale |
| **Boilerplate Resistance** | HNSW on full corpus | **NOT FIXED** — HNSW by design for scale |

**Assessment**: The fix is real and effective for its intended scope (adversarial benchmarks). The original report overstated by implying the artifact is fully resolved across all benchmarks. Citation heritage, temporal_stability, hierarchy family, and boilerplate benchmarks still use HNSW — this is by design for full-corpus scale and does not invalidate their results, but the scope must be explicit.

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
- **Check count**: 124 (as of 2026-09-26T12:16:27)
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

The evaluation lane will **autonomously evaluate dense representations** as they land in accepted state via the active monitor. The monitor infrastructure is verified operational with HNSW artifact fix in place for adversarial benchmarks.

**Next factory direction decision**: Successor question for evaluation lane should address dense embedding evaluation at 174k scale once legal-distance delivers them, plus jurist human study when recruitment is feasible.

---

## Evidence References

### Formal Suite Results
- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` — Latest formal suite run (HNSW artifact fix for adversarial benchmarks)
- `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json` — v25 frozen protocol suite summary
- `evaluation/run_174k_formal_suite.py` — Formal suite runner with exact k-NN fix (`get_adversarial_subsample()`)

### Citation Heritage (ACTUAL RESULTS)
- `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json` — **Actual computed AUC/recall values (CORRECTED)**
- `evaluation/validate_citation_heritage_174k.py` — Validation infrastructure
- `evaluation/run_citation_heritage_174k_embeddings.py` — Benchmark runner (uses HNSW via scalable_nn)

### v17b Label Normalization
- `evaluation/results/v17b_174k_tfidf/v17b_174k_tfidf_results.json` — Full 8-representation results
- `evaluation/experiments/legal_area_normalize.py` — Frozen conservative canonical map

### Monitor & Infrastructure
- `evaluation/monitor_and_evaluate_174k.py` — Autonomous monitor
- `evaluation/state/monitor_174k_state.json` — Monitor state (check_count=124)
- `evaluation/scalable_nn.py` — Scalable NN infrastructure with HNSW/sklearn

### Protocol & Config
- `evaluation/experiments/v25_174k_suite/protocol_v25_174k_suite.json` — Frozen protocol (config hash 4323f833fa72366a)
- `evaluation/evaluation_v3_harness.py` — Frozen adversarial thresholds

---

## Appendix: Audit Correction Summary

**Audit CYCLE_36242734524 (REVISE gate) required fixes applied:**

1. ✅ **CORRECTED Citation Heritage AUC-ROC values**: 0.789, 0.774, 0.758, 0.871, 0.850, 0.896, 0.657, 0.486 (NOT 0.973, 0.960, 0.919, 0.865, 0.850, 0.844, 0.720, 0.486)
2. ✅ **CORRECTED nn_citation_rate@10 (positive_recall@10)**: ~0.03–0.05 (NOT ~0.44–0.49)
3. ✅ **CORRECTED formal suite pass/fail counts**: Per-representation counts now match actual benchmark statuses in evaluation_174k_formal_suite_latest.json
4. ✅ **CLARIFIED HNSW fix scope**: Explicitly stated that citation heritage, temporal_stability, hierarchy family, and boilerplate benchmarks still use HNSW (by design for full-corpus scale); only adversarial benchmarks use exact k-NN fix
5. ✅ **PRESERVED negative results**: Two-mode tradeoff, v17b non-uniformity, hierarchy_coherence failures all honestly reported as negative evidence

**Claim Ceiling (per audit):**
> "TF-IDF family (8 representations) evaluated at 174k scale across three sub-questions with frozen config (hash 4323f833fa72366a). HNSW adversarial artifact fixed for adversarial benchmarks only (exact k-NN on n=2000 stratified subsample). Citation heritage AUC ranges 0.66-0.90, nn_citation_rate@10 3-5%. No representation passes all 12 benchmarks. Two-mode tradeoff confirmed. v17b normalization not uniformly confirmed (2/8 reps satisfy frozen rule). Dense embeddings awaited (3/26 years complete, blocked on corpus artifact publication gap). Monitor active (check_count=124)."

---

**This corrected report supersedes EVALUATION_174K_V27_CYCLE_REPORT_20260926.md for all claim-bearing purposes.**