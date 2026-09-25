# Evaluation Lane Cycle Report — Factory Direction v27

**Lane**: evaluation
**Direction Version**: 27
**Cycle Status**: BLOCKED_ON_DEPENDENCIES
**Evidence Tier**: REPRODUCED
**Date**: 2026-09-25
**Run ID**: eval_v27_174k_tfidf_and_dense1200_36097406309

---

## Executive Summary

The evaluation lane has **completed all machine-executable sub-questions** for the TF-IDF family at 174k scale and established dense 1200-scale baselines. The lane is now **blocked on legal-distance delivering 174k dense embeddings, citation roles, and linear hybrids**.

| Sub-question | Status | Representations Tested |
|--------------|--------|------------------------|
| 1. 12-benchmark formal suite at 174k | ✅ COMPLETE | 8 TF-IDF |
| 2. Citation heritage validation (174k pairs) | ✅ COMPLETE | 8 TF-IDF |
| 3. v17b label normalization generalization | ✅ COMPLETE | 8 TF-IDF |
| 4. v3 adversarial harness at 1200-scale | ✅ COMPLETE | 7 dense |
| 5. Jurist human study | ⏳ BLOCKED (external) | 5-10 Swiss jurists needed |

**Next milestone**: Legal-distance delivers first 174k dense embeddings (year-split computation in progress).

---

## Sub-question 1: 12-Benchmark Formal Suite at 174k Scale

**Protocol**: Frozen v25 174k suite (config hash `4323f833fa72366a`), HNSW k-NN at full corpus density (173,963 decisions), seed 42.

### Results Summary

| Representation | Passed/12 | Key Strengths | Key Failures |
|----------------|-----------|---------------|--------------|
| `cited_decisions_tfidf` | 6 | citation_heritage (AUC 0.973), adversarial, multilingual, collapse_check, zoom_coherence | branch_knn (0.39), tf_metadata (0.39), boilerplate, temporal_stability (std 0.18), hierarchy_coherence (purity 0.15), legal_area (0.004) |
| `cited_outcome_hybrid_0.5` | 6 | citation_heritage (AUC 0.919), adversarial, multilingual, collapse_check, zoom_coherence | branch_knn, tf_metadata, boilerplate, temporal_stability, hierarchy_coherence, legal_area |
| `cited_outcome_hybrid_0.7` | 6 | citation_heritage (AUC 0.960), adversarial, multilingual, collapse_check, zoom_coherence | branch_knn, tf_metadata, boilerplate, temporal_stability, hierarchy_coherence, legal_area |
| `full_text_tfidf_light` | 7 | branch_knn (0.83), tf_metadata (0.83), boilerplate, temporal_stability, collapse_check, zoom_coherence | citation_heritage (AUC 0.84), adversarial (lang_dom 0.999), multilingual, hierarchy_coherence (purity 0.465), legal_area |
| `regeste_full_text_hybrid_0.5` | 7 | branch_knn (0.97), tf_metadata (0.97), boilerplate, temporal_stability, collapse_check, zoom_coherence | citation_heritage (AUC 0.85), adversarial (lang_dom 0.998), multilingual, hierarchy_coherence (0.465), legal_area |
| `regeste_full_text_hybrid_0.7` | 7 | branch_knn (0.98), tf_metadata (0.98), boilerplate, temporal_stability, collapse_check, zoom_coherence | citation_heritage (AUC 0.87), adversarial (lang_dom 0.999), multilingual, hierarchy_coherence (0.465), legal_area |
| `outcome_tfidf` | 3 | citation_heritage (AUC 0.72), collapse_check, temporal_stability | branch_knn, tf_metadata, adversarial, boilerplate, multilingual, cross_language, hierarchy_coherence, zoom_coherence, legal_area |
| `regeste_tfidf` | 5 | adversarial, multilingual, cross_language, collapse_check, temporal_stability | citation_heritage (AUC 0.49 FAIL), branch_knn, tf_metadata, boilerplate, hierarchy_coherence, zoom_coherence, legal_area |

### Critical Findings

1. **No representation passes all 12 benchmarks** at 174k scale
2. **Fundamental trade-off**: Citation-aware representations recover citation structure but fail branch/legal metadata alignment; full-text hybrids recover branch/metadata but are language-dominated
3. **Hierarchy coherence universally fails** (max purity 0.465 vs 0.7 threshold) — fine-grained legal_area labels (167 areas) too sparse at 174k
4. **Temporal stability fails for citation-aware** (std 0.15-0.18 > 0.1 threshold) — citation neighborhoods unstable across temporal splits
5. **Boilerplate resistance fails for citation-aware** (correlation ~0.0 to -0.08) — citation signals don't correlate with textual similarity

---

## Sub-question 2: Citation Heritage Benchmark at 174k

**Protocol**: Frozen pair pool (137,314 positive + 137,314 negative pairs), citation-ID resolution 2,019/2,105 (95.9%), AUC-ROC threshold 0.65.

### Results

| Representation | AUC-ROC | nn_citation_rate@10 | Status |
|----------------|---------|---------------------|--------|
| `cited_decisions_tfidf` | **0.973** | **0.487** | ✅ PASS |
| `cited_outcome_hybrid_0.7` | 0.960 | 0.490 | ✅ PASS |
| `cited_outcome_hybrid_0.5` | 0.919 | 0.476 | ✅ PASS |
| `full_text_tfidf_light` | 0.844 | 0.438 | ✅ PASS |
| `regeste_full_text_hybrid_0.5` | 0.850 | 0.444 | ✅ PASS |
| `regeste_full_text_hybrid_0.7` | 0.865 | 0.445 | ✅ PASS |
| `outcome_tfidf` | 0.720 | 0.003 | ✅ PASS |
| `regeste_tfidf` | **0.487** | 0.000 | ❌ FAIL |

**Finding**: Citation structure strongly recovered by citation-aware representations (AUC > 0.91). Only `regeste_tfidf` fails (no citation signal). The 174k pair pool validates the benchmark at production scale.

---

## Sub-question 3: v17b Label Normalization Generalization

**Protocol**: Conservative cross-lingual legal_area normalization (v17b), frozen hierarchy subsample (15,000 decisions, seed 42), compare raw vs normalized on hierarchy-family benchmarks.

### Results

| Representation | Raw Hierarchy Purity | Normalized Purity | Gain | Status |
|----------------|---------------------|-------------------|------|--------|
| `cited_decisions_tfidf` | 0.152 | 0.232 | **+52%** | Partial |
| `cited_outcome_hybrid_0.5` | 0.130 | 0.201 | **+55%** | Partial |
| `cited_outcome_hybrid_0.7` | 0.128 | 0.197 | **+54%** | Partial |
| `full_text_tfidf_light` | 0.465 | 0.465 | 0% | Already normalized |
| `regeste_full_text_hybrid_0.5` | 0.465 | 0.465 | 0% | Already normalized |
| `regeste_full_text_hybrid_0.7` | 0.465 | 0.465 | 0% | Already normalized |
| `outcome_tfidf` | 0.090 | 0.131 | **+46%** | Partial |
| `regeste_tfidf` | 0.081 | 0.132 | **+64%** | Partial |

**Finding**: **PARTIAL GENERALIZATION** — 5/8 representations show 46-64% purity gains across hierarchy-family metrics; 3/8 show no change (labels already normalized by full-text dominance); 0 worsen. However, **even normalized, best hierarchy purity = 0.47 < 0.7 threshold** — fundamental granularity/coverage limits persist at 174k scale.

---

## Sub-question 4: v3 Adversarial Harness at 1200-Scale (Dense Baselines)

**Protocol**: Frozen harness v3 thresholds (LangDom < 0.85, Jurist > 0.5), 1200 decisions, exact k-NN, seed 42, config hash `4047da047fb339c1`.

### Results

| Representation | Dim | LangDom | Jurist Pref | Both Gates | Jurivoc L0 NMI | Cross-lang Recall | Boilerplate Resist |
|----------------|-----|---------|-------------|------------|----------------|-------------------|-------------------|
| `linear_metric_epoch4` | 128 | **0.681** | **0.685** | ✅ **PASS** | 0.688 | 0.211 | -0.888 |
| `mahalanobis_metric_epoch4` | 128 | 0.684 | 0.678 | ✅ **PASS** | **0.705** | 0.208 | -0.895 |
| `hybrid_stabilized_epoch1` | 128 | **0.670** | 0.666 | ✅ **PASS** | 0.633 | **0.236** | -0.919 |
| `hybrid_v2_epoch3` | 128 | 0.711 | 0.599 | ✅ **PASS** | 0.743 | 0.227 | -0.914 |
| `center_projected_64` | 64 | 0.766 | 0.512 | ✅ **PASS** (marginal) | 0.065 | 0.156 | -0.901 |
| `center_projected_768` | 768 | 0.774 | 0.491 | ❌ FAIL (jurist) | 0.086 | 0.146 | -0.896 |
| `center_projected_128` | 128 | 0.772 | 0.495 | ❌ FAIL (jurist) | 0.083 | 0.149 | -0.897 |

### Critical Findings

1. **5/7 dense representations pass BOTH adversarial gates** at 1200 scale
2. **Metric learning/hybrid objectives dominate**: `linear_metric_epoch4` (jurist=0.685), `mahalanobis_metric_epoch4` (jurist=0.678), `hybrid_stabilized_epoch1` (jurist=0.666)
3. **Center-projected variants FAIL jurist pairwise** at 768/128 dim (jurist ~0.49); 64-dim marginal pass (0.51)
4. **ALL pass scale stability** (~0.76-0.80 neighbor overlap)
5. **ALL FAIL boilerplate resistance** (~-0.89 to -0.92) — procedural boilerplate dominates neighbors
6. **Metric learning/hybrid PASS Jurivoc L0** (NMI 0.63-0.74) and cross-language retrieval (>0.2); center_projected FAIL both

---

## Critical Scale Extrapolation Risk

**TF-IDF jurist pairwise COLLAPSED from 0.79 (1200-scale, cycle 14) → 0.12 (174k-scale, v3 harness)**

This is the **single most critical risk** for the product. The dense 1200-scale baselines show promising jurist pairwise (0.51-0.68), but **will they hold at 174k density?**

- If metric learning/hybrid objectives maintain >0.5 jurist pairwise at 174k → **PRODUCTIZE path viable**
- If they collapse like TF-IDF (0.79→0.12) → **fundamental architecture reconsideration needed**

The v3 adversarial harness is frozen and operational for 174k evaluation. The monitor is active (check_count=42, last_check=2026-09-25T05:16:28).

---

## Awaited Representations from Legal-Distance

| Category | Representations | Status |
|----------|-----------------|--------|
| **Dense embeddings (6)** | `center_projected_768dim`, `center_projected_64dim`, `linear_metric_epoch4`, `mahalanobis_metric_epoch4`, `hybrid_stabilized_epoch1`, `hybrid_v2_epoch3` | ⏳ Year-split computation in progress (year 2000 only: 3,839/174k decisions) |
| **Citation roles (3)** | `citation_role_citing_alpha0.3`, `citation_role_following_alpha0.3`, `citation_role_criticizing_alpha0.3` | ⏳ Not started |
| **Linear hybrids (2)** | `linear_citation_concat`, `linear_hybrid05_concat` | ⏳ Not started |

**Legal-distance status**: Year-split TF-IDF computation running (gh run 36096850301). Dense embeddings blocked on corpus delivery for years 2001-2025 (only year 2000 normalized corpus available).

---

## Evidence References

| Artifact | Path |
|----------|------|
| v25 174k formal suite results | `results/evaluation/v25_174k_formal_suite/results/` |
| Citation heritage 174k | `results/evaluation/v25_174k_citation_heritage/` |
| v17b label normalization | `results/evaluation/v25_174k_v17b/` |
| v3 dense 1200 baseline | `evaluation/results/dense_1200_baseline/full_corpus_evaluation_results_worker0.json` |
| 174k metadata | `evaluation/data/174k/metadata_174k.json` (173,963 entries) |
| Citation pairs 174k | `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json` |
| Monitor state | `evaluation/state/monitor_174k_state.json` |
| Frozen protocol | `evaluation/experiments/v25_174k_suite/protocol_v25_174k_suite.json` |

---

## Recommendation

**BLOCKED_ON_DEPENDENCIES — continue_recommended = true**

The evaluation lane has completed all autonomous machine-executable work for currently available representations. The lane should:
1. **Continue monitoring** for 174k dense embeddings, citation roles, and linear hybrids from legal-distance
2. **Auto-evaluate** any new representations as they land using frozen v25 suite + v3 adversarial harness
3. **Report scale extrapolation risk** when first dense 174k results arrive (will jurist pairwise hold?)
4. **Jurist human study** remains blocked on external recruitment (5-10 Swiss jurists)

No pivot within mission needed — the evaluation infrastructure is operational and validated. The blocker is upstream compute (legal-distance year-split dense embedding production).

---

## Next Actions

| Action | Owner | Trigger |
|--------|-------|---------|
| Monitor legal-distance 174k dense embeddings | evaluation (auto) | Continuous (monitor active) |
| Run v25 formal suite on new 174k dense reps | evaluation (auto) | On detection |
| Run v3 adversarial harness on new 174k dense reps | evaluation (auto) | On detection |
| Test jurist pairwise at 174k for metric learning | evaluation (auto) | When dense 174k lands |
| Recruit jurists for human study | repository owner | External dependency |
| Deliver 174k normalized corpus years 2001-2025 | corpus lane | Unblocks legal-distance dense |

---

*Report generated per Research Protocol §12-13. Machine-readable state at `state/evaluation.json`.*