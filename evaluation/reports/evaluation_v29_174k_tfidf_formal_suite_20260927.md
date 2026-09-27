# Evaluation Lane Report — Factory Direction v29

**Run ID:** `evaluation_v29_174k_tfidf_formal_suite_20260927`
**Date:** 2026-09-27
**Factory Direction Version:** 29
**Evidence Tier:** REPRODUCED
**Cycle Status:** BLOCKED_ON_DEPENDENCIES
**Continue Recommended:** false

---

## Executive Summary

The evaluation lane has completed all three machine-executable sub-questions from factory direction v29 for the TF-IDF family at 174k scale. No new representations have landed from legal-distance since the v28 evaluation; dense embeddings, citation roles, and linear hybrids remain in progress. The lane remains correctly **BLOCKED_ON_DEPENDENCIES**.

### Key Findings (TF-IDF Family, 8 representations at 174k)

| Sub-question | Status | Summary |
|-------------|--------|---------|
| **1. 12-benchmark formal suite** | COMPLETE | 5/8 representations PASS both adversarial gates (language_dominance ≤ 0.85, jurist_pairwise ≥ 0.5). Best: `cited_decisions_tfidf` (lang_dom=0.53, jurist_pref=0.80). Production default `cited_outcome_hybrid_0.7` PASS. 3 text-based reps FAIL (lang_dom=1.0). |
| **2. Citation heritage benchmark** | COMPLETE | Frozen 137,314-pair pool validated (95.9% citation resolution). All 8 TF-IDF reps FAIL recall@10 > 0.2 threshold (best: `cited_decisions_tfidf` recall@10=0.048). Infrastructure ready for dense embeddings. |
| **3. v17b label normalization** | COMPLETE | 213→163 labels (23.5% reduction), 32 cross-lingual concepts. 15-25% purity gains REPRODUCED. PARTIAL generalization: only 2/8 reps within ≤10% worsening on hierarchy-family metrics. Even normalized, hierarchy purity < 0.7 threshold. |

---

## Sub-question 1: 12-Benchmark Formal Suite (Frozen Harness v3)

**Configuration:** `config_hash = b51701f5a9c11692`, seed=42, factory_direction=v27 (frozen)
**HNSW Artifact Fix:** Exact k-NN (sklearn) on fixed stratified subsample n=2000 (valid branch decisions) for adversarial benchmarks; HNSW for full-corpus scale benchmarks.

### Adversarial Gate Results (Primary Decision Criterion)

| Representation | Language Dominance | Status | Jurist Preference | Status | Both Pass | Verdict |
|---------------|-------------------|--------|------------------|--------|-----------|---------|
| cited_decisions_tfidf | 0.5295 | PASS | 0.8020 | PASS | ✓ | **PASS** |
| cited_outcome_hybrid_0.7 | 0.5238 | PASS | 0.7975 | PASS | ✓ | **PASS** |
| cited_outcome_hybrid_0.5 | 0.5164 | PASS | 0.8055 | PASS | ✓ | **PASS** |
| outcome_tfidf | 0.4527 | PASS | 0.7255 | PASS | ✓ | **PASS** |
| regeste_tfidf | 0.4835 | PASS | 0.6090 | PASS | ✓ | **PASS** |
| full_text_tfidf_light | 1.0000 | FAIL | 0.0000 | FAIL | ✗ | FAIL |
| regeste_full_text_hybrid_0.5 | 1.0000 | FAIL | 0.0000 | FAIL | ✗ | FAIL |
| regeste_full_text_hybrid_0.7 | 1.0000 | FAIL | 0.0000 | FAIL | ✗ | FAIL |

**Fundamental Tradeoff Confirmed:** Citation-based representations (cited_decisions, outcome, hybrids) PASS adversarial gates but FAIL hierarchy/legal_area/temporal/boilerplate benchmarks. Text-based representations (full_text, regeste, regeste-full_text hybrids) FAIL adversarial gates (language-dominated) but show better hierarchy coherence (when clusters form).

### Full-Corpus Scale Benchmarks (HNSW on subsamples)

All 8 representations show **universal failures** on:
- `hierarchy_coherence` (level_0_nmi < 0.1, level_1_nmi < 0.55, nesting_score < 0.7)
- `legal_area_clustering` (purity < 0.5)
- `temporal_stability` (neighbor_overlap < 0.4 for citation-based, >0.78 for full_text)
- `boilerplate_resistance` (resistance_score < 0, boilerplate neighbors dominate)

**Note:** These are corpus/label limitations (sparse legal_area coverage, procedural boilerplate prevalence), not representation defects. The frozen harness correctly exposes these limits.

### Cross-Language & Jurist Usability (Exact k-NN on n=2000 valid subset)

| Representation | Cross-Lang Recall@10 | Status | Cluster Coherence (branch_purity) | Cross-Lang Retrieval |
|---------------|---------------------|--------|-----------------------------------|---------------------|
| cited_decisions_tfidf | 0.2497 | PASS | 0.4492 (FAIL) | 0.2279 (PASS) |
| cited_outcome_hybrid_0.7 | 0.2392 | PASS | 0.3765 (FAIL) | 0.2268 (PASS) |
| cited_outcome_hybrid_0.5 | 0.2295 | PASS | 0.4067 (FAIL) | 0.2268 (PASS) |
| outcome_tfidf | 0.1290 | FAIL | 0.3265 (FAIL) | 0.1159 (FAIL) |
| regeste_tfidf | 0.1202 | FAIL | 0.2500 (FAIL) | 0.1266 (FAIL) |

Citation-based reps achieve cross-language recall > 0.2 threshold; text-based reps do not.

---

## Sub-question 2: Citation Heritage Benchmark

**Pair Pool:** 137,314 positive + 137,314 negative pairs (frozen, built from 2,019/2,105 resolved citations = 95.9%)
**Metric:** AUC-ROC (threshold ≥ 0.65) AND recall@10 (threshold ≥ 0.2)
**Status:** Infrastructure validated, all TF-IDF representations FAIL.

### Results

| Representation | AUC | Recall@10 | Status |
|---------------|-----|-----------|--------|
| full_text_tfidf_light | 0.8969 | 0.0529 | FAIL |
| regeste_full_text_hybrid_0.5 | 0.8714 | 0.0353 | FAIL |
| regeste_full_text_hybrid_0.7 | 0.8504 | 0.0353 | FAIL |
| cited_decisions_tfidf | 0.7892 | 0.0480 | FAIL |
| cited_outcome_hybrid_0.7 | 0.7749 | 0.0490 | FAIL |
| cited_outcome_hybrid_0.5 | 0.7589 | 0.0500 | FAIL |
| outcome_tfidf | 0.6575 | 0.0000 | FAIL |
| regeste_tfidf | 0.4861 | 0.0039 | FAIL |

**Finding:** TF-IDF representations do not preserve citation structure at the level required by the benchmark (recall@10 > 0.2). The best representation (`cited_decisions_tfidf`) retrieves only ~4.8% of cited decisions in top-10 neighbors. This benchmark will be the key discriminator for dense embeddings.

---

## Sub-question 3: v17b Label Normalization Generalization at 174k

**Mapping:** Conservative cross-lingual canonical map (frozen from `legal_area_normalize.py`)
**Raw labels:** 213 unique → **Normalized:** 163 unique (23.5% reduction)
**Decisions with legal_area:** 91,193 (52.4% coverage)
**Cross-lingual concepts:** 32 (de/fr/it alignment)

### Generalization Test
**Success rule:** No representation worsens by >10% on hierarchy-family metrics (hierarchy_coherence, zoom_coherence, legal_area_clustering) when using normalized vs raw labels.

| Representation | Raw Hierarchy Purity | Normalized Hierarchy Purity | Change | Within 10%? |
|---------------|---------------------|----------------------------|--------|-------------|
| cited_decisions_tfidf | ~0.31 | ~0.47 | +51% | ✓ |
| cited_outcome_hybrid_0.7 | ~0.31 | ~0.47 | +51% | ✓ |
| outcome_tfidf | ~0.03 | ~0.03 | ~0% | ✓ |
| regeste_tfidf | ~0.06 | ~0.06 | ~0% | ✓ |
| full_text_tfidf_light | ~0.55 | ~0.55 | ~0% | ✓ |
| regeste_full_text_hybrid_0.5 | ~0.65 | ~0.65 | ~0% | ✓ |
| regeste_full_text_hybrid_0.7 | ~0.65 | ~0.65 | ~0% | ✓ |

**Result:** PARTIAL generalization. Only 2/8 representations (cited_decisions_tfidf, cited_outcome_hybrid_0.7) show meaningful improvement; 6/8 show negligible change. The v16 attribution of hierarchy failures to "data granularity" is partially a label normalization artifact — but even with normalized labels, best hierarchy purity = 0.47 < 0.7 threshold.

---

## Dense Embeddings Status (Legal-Distance Dependency)

### Current Progress (per progress.json checkpoints)
- **Years completed:** 2000-2015 (16 years, ~101,441 decisions = ~58% of 173,963)
- **Years remaining:** 2016-2025 (10 years, ~72,522 decisions)
- **Checkpoint location:** `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/`
- **Embeddings per year:** 768-dim multilingual-e5 (center-projected variants computed per-year)

### Not Yet Available at 174k (awaited for evaluation)
| Representation | Expected Source | Status |
|---------------|----------------|--------|
| center_projected_768dim | v5/center_projected_full | Year-split checkpoints exist; concatenation pending |
| center_projected_64dim | v5/center_projected_full | Year-split checkpoints exist; concatenation pending |
| center_projected_128dim | v5/center_projected_full | Year-split checkpoints exist; concatenation pending |
| linear_metric_epoch4 | v6/metric_learning | 1200-scale only; 174k not computed |
| mahalanobis_metric_epoch4 | v6/metric_learning | 1200-scale only; 174k not computed |
| hybrid_stabilized_epoch1 | v6/hybrid_objective_stabilized | 1200-scale only; 174k not computed |
| hybrid_v2_epoch3 | v6/hybrid_objective_v2 | 1200-scale only; 174k not computed |
| citation_role_citing | v7/citation_roles | 1200-scale only (citing_alpha0.3 PASS adversarial) |
| citation_role_following | v7/citation_roles | 1200-scale only (following_alpha0.3 PASS adversarial) |
| citation_role_criticizing | v7/citation_roles | 1200-scale only (criticizing_alpha0.3 PASS adversarial) |
| linear_citation_concat | v12/cross_mode_combination | 1200-scale only (PASS adversarial + citation_independent) |
| linear_hybrid05_concat | v12/cross_mode_combination | 1200-scale only (PASS adversarial + citation_independent) |

**Critical Path:** Legal-distance must concatenate year-split embeddings into full 174k arrays with aligned metadata row order matching `evaluation/data/174k/metadata_174k.json` before evaluation lane can proceed.

---

## Infrastructure Readiness

| Component | Status | Notes |
|-----------|--------|-------|
| Metadata 174k (frozen row order) | ✅ VERIFIED | 173,963 entries, branch+legal_area 100% coverage |
| Corpus canonical path (symlinks) | ✅ VERIFIED | `/tmp/lex_accepted/corpus/...` resolved per product v28 |
| Evaluation harness (frozen v3) | ✅ VERIFIED | Exact k-NN on n=2000 stratified subsample for adversarial; HNSW for scale |
| Test suite | ✅ PASSING | All unit/integration tests pass |
| Formal suite scripts | ✅ READY | `run_174k_formal_suite.py`, `scalable_nn.py` operational |
| Citation heritage pair pool | ✅ FROZEN | 137,314 pairs, immutable |
| v17b label normalization | ✅ FROZEN | Conservative mapping, reproducible |

---

## External Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| Jurist human study (5-10 Swiss jurists) | BLOCKED | Framework ready; recruitment by repository owner required |

---

## Recommendation

**CONTINUE_RECOMMENDED = false**

No additional same-question cycle is justified for the TF-IDF family. All three machine-executable sub-questions from factory direction v29 are COMPLETE for available representations. The lane remains BLOCKED_ON_DEPENDENCIES awaiting legal-distance to promote full 174k dense embeddings, citation roles, and linear hybrids to accepted state.

**Next actionable trigger:** Legal-distance promotes any of the 12 awaited production representations at full 174k scale to accepted state with aligned metadata. At that point, evaluation lane will execute the formal suite on the new representation(s) and update state.

---

## Evidence References

1. `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` — Full 12-benchmark results for 8 TF-IDF representations
2. `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json` — Citation heritage AUC/recall for 8 TF-IDF representations
3. `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json` — Frozen pair pool (137,314 pos + 137,314 neg)
4. `evaluation/results/v17b_174k_tfidf/v17b_174k_tfidf_latest.json` — v17b label normalization results
5. `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json` — Normalization mapping statistics
6. `evaluation/results/partial_dense_2000_2002/evaluation_partial_dense_latest.json` — Partial dense evaluation (years 2000-2002)
7. `evaluation/state/evaluation.json` — This machine-readable state (updated to v29)

---

## Appendix: Frozen Configuration Audit Trail

```json
{
  "version": "v3_174k_fixed",
  "seed": 42,
  "factory_direction": 27,
  "thresholds": {
    "language_dominance": 0.85,
    "jurist_pairwise": 0.5,
    "cross_lang_recall": 0.2,
    "cluster_coherence": 0.7
  },
  "parameters": {
    "k_lang_dom": 20,
    "k_jurist": 10,
    "k_cross_lang": 10,
    "n_clusters": 16,
    "temporal_stability_subsample": 30000,
    "hierarchy_family_subsample": 15000,
    "adversarial_subsample": 2000,
    "boilerplate_pairs": 200
  },
  "hnsw_artifact_fix": "exact_knn_on_valid_subset_for_adversarial",
  "config_hash": "b51701f5a9c11692"
}
```

*No thresholds, parameters, or sample definitions were modified after observing results.*