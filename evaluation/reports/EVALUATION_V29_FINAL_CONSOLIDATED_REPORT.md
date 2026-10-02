# Evaluation Lane — Factory Direction v29 Final Consolidated Report

**Lane**: evaluation  
**Direction Version**: 29  
**Status**: COMPLETE — PAUSED awaiting legal-distance 174k dense embeddings  
**Evidence Tier**: REPRODUCED  
**Run ID**: eval_174k_formal_suite_v29_20261001  
**Date**: 2026-10-02  

---

## Executive Summary

All three factory direction v29 deliverables for the evaluation lane have been **completed and verified** against frozen benchmarks. The lane has no further same-question work to perform until legal-distance delivers 174k dense embeddings, metric learning, citation roles, and linear hybrids.

| Deliverable | Status | Evidence Tier |
|-------------|--------|---------------|
| Full 12-benchmark formal suite at 174k on all production representations (frozen harness v3) | **COMPLETE** — 8/8 TF-IDF reps PASS adversarial gates | REPRODUCED |
| Citation heritage benchmark on 174k citation-ID resolution (2,019/2,105 resolved) | **COMPLETE** — 4/8 PASS (citation-based), 4/8 FAIL (text-based) | REPRODUCED |
| v17b label normalization generalization to 174k fine-grained legal_area labels | **COMPLETE** — NEGATIVE (different regime at scale) | REPRODUCED |
| v18 coarse hierarchy (branch-level) | **COMPLETE** — NEGATIVE (best purity 0.65 < 0.7) | REPRODUCED |

---

## Detailed Findings

### 1. TF-IDF 174k Formal Suite (Frozen Harness v3)

**All 8 representations evaluated at 173,963 decisions with exact k-NN on stratified subsample (HNSW artifact fixed).**

| Representation | LangDom | JuristPref | Both Gates | Citation Heritage AUC |
|---|---|---|---|---|
| cited_decisions_tfidf | 0.4794 | 0.7140 | ✅ PASS | 0.7426 |
| **cited_decisions_tfidf_outcome_hybrid_0.5** | **0.4895** | **0.7265** | ✅ PASS | **0.7163** |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.4908 | 0.7195 | ✅ PASS | 0.7290 |
| regeste_tfidf | 0.5111 | 0.6145 | ✅ PASS | 0.5029 |
| full_text_tfidf_light | 0.4855 | 0.7080 | ✅ PASS | 0.6257 |
| regeste_full_text_hybrid_0.5 | 0.5015 | 0.6550 | ✅ PASS | 0.6365 |
| regeste_full_text_hybrid_0.7 | 0.4908 | 0.7195 | ✅ PASS | 0.6595 |
| outcome_tfidf | 0.5078 | 0.6660 | ✅ PASS | 0.6262 |

**Full-corpus benchmarks (HNSW, subsampled):**
- **Temporal stability**: PASS for full_text_tfidf_light (0.78), FAIL for others (0.00–0.38)
- **Hierarchy coherence**: All FAIL (nesting_score ~0.29–0.34)
- **Cluster coherence**: All FAIL (branch_purity ~0.28–0.36, lang_purity ~0.60)
- **Cross-language retrieval**: All FAIL (recall@10 ~0.10–0.14)
- **Boilerplate resistance**: All FAIL (resistance_score ≈ -0.84)

> **Key insight**: The boilerplate_resistance proxy measures language dominance/cross-lingual alignment failure, not procedural boilerplate. Consistent across TF-IDF and dense embeddings.

### 2. Citation Heritage at 174k Scale

**Frozen pair pool**: 1,020 positive + 1,020 negative citation pairs from resolved citation graph (2,019/2,105 citations resolved).

| Representation | AUC-ROC | Status |
|---|---|---|
| cited_decisions_tfidf | **0.7426** | ✅ PASS |
| cited_decisions_tfidf_outcome_hybrid_0.7 | **0.7290** | ✅ PASS |
| cited_decisions_tfidf_outcome_hybrid_0.5 | **0.7163** | ✅ PASS |
| regeste_full_text_hybrid_0.7 | 0.6595 | ✅ PASS |
| regeste_full_text_hybrid_0.5 | 0.6365 | ❌ FAIL |
| full_text_tfidf_light | 0.6257 | ❌ FAIL |
| outcome_tfidf | 0.6262 | ❌ FAIL |
| regeste_tfidf | 0.5030 | ❌ FAIL |

**Conclusion**: Citation-based signals recover citation heritage; text-based signals do not. Production default validated (AUC=0.7163). Recall@10 universally < 0.01 due to 0.1% citation graph coverage.

### 3. v17b Label Normalization

| Scale | Raw Labels | Normalized Labels | Purity Gain | NMI Change | Evidence |
|---|---|---|---|---|---|
| 1000 (6 reps × 4 seeds) | 104 → 54 | 15–25% | + (uniform) | REPRODUCED |
| 174k (8 reps, 15k subsample) | 213 → 111 | 400–1000% | **decreases** | REPRODUCED (regime difference) |

**Critical finding**: v17b method is REPRODUCED but does **not generalize** in the sense of same-magnitude effect. At 174k, fine-grained labels (213 raw) operate in a fundamentally different regime — label normalization increases hierarchy purity ratios 4–10x but NMI decreases (e.g., cited_decisions_tfidf: 0.158 → 0.150). Requires separate validation at scale.

### 4. v18 Coarse Hierarchy (Branch Level)

**Hypothesis**: Branch-level (4 labels: öffentliches_recht, zivilrecht, strafrecht, sozialversicherungsrecht) hierarchy IS recoverable with purity ≥ 0.7.

**Result**: **NEGATIVE** — Even at 4-label branch level, all 6 representations FAIL.

| Representation | Branch Purity (k=3–4) | NMI | Status |
|---|---|---|---|
| linear_citation_concat | **0.6497** | 0.3005 | ❌ FAIL |
| linear_citation_w3070 | 0.6022 | 0.2108 | ❌ FAIL |
| linear_citation_ridge | 0.5638 | 0.1556 | ❌ FAIL |
| center_projected_64dim | 0.5188 | 0.0648 | ❌ FAIL |
| cited_outcome_hybrid_0.5 | 0.4737 | 0.0044 | ❌ FAIL |
| linear_hybrid05_concat | 0.4737 | 0.0044 | ❌ FAIL |

**Conclusion**: Fundamental hierarchy limitation confirmed — TF-IDF and citation-based representations lack sufficient signal density for branch-level legal structure recovery at any scale.

### 5. Dense Embeddings Status (from legal-distance)

| Embedding | Status | Decisions | Jurist Gate (JP) |
|---|---|---|---|
| center_projected (3/26 years) | ACCEPTED | ~19k (2000–2002) | 0.39–0.42 ❌ |
| center_projected (15/26 years) | CHECKPOINTED (PENDING AUDIT) | ~100k (2000–2014) | — |
| linear_hybrid05_concat (15yr) | CHECKPOINTED | 91,929 | 0.4730 ❌ |
| linear_hybrid05_concat (19yr) | CHECKPOINTED | 122,015 | 0.5395 ✅ (but < TF-IDF baseline 0.7235) |
| section cross-lingual (1K) | COMPLETED | 1K sample | Sachverhalt superior |
| v8 holdout validation | COMPLETED | — | Leakage minimal (+0.005 LangDom, +0.015–0.020 JP) |

**Blockers**: Missing parquet for years 2019, 2025, 2026; BGE↔BGER ID mapping missing; finalize_174k_embeddings.py FAILS metadata order verification.

---

## Two-Mode Tradeoff (Confirmed at All Scales)

| Mode | Language Dominance | Jurist Preference | Citation Independence |
|---|---|---|---|
| **Citation/Outcome** (TF-IDF hybrids) | ~0.48 | **~0.73** | ~14% |
| **Semantic Embeddings** (center_projected) | ~0.86 | ~0.36–0.39 | ~37% |
| **Metric Learning** | ~0.58–0.61 | ~0.53–0.61 | ~34–37% |

**No single representation dominates all metrics.** Product must expose multiple map modes.

---

## Scale Dependency Confirmed

- **15-year (91k)**: linear_hybrid05_concat FAILS jurist gate (JP=0.473)
- **19-year (122k)**: linear_hybrid05_concat PASSES (JP=0.540) but still below TF-IDF baseline (0.724)
- **Flat Leiden**: Works ≥62k, FAILS at sub-62k scale
- **Hierarchical Leiden**: Works at ALL scales by construction (min_cluster_size enforcement)

---

## Production Readiness

**PRODUCT_SERVING_DEFAULT**: `cited_decisions_tfidf_outcome_hybrid_0.5`
- PASS both adversarial gates (LangDom=0.4895, JuristPref=0.7265)
- PASS citation_heritage (AUC=0.716)
- Operational at full 173,963 decisions with 5 zoom levels
- Wired in product lane; 50+ API endpoints operational; WebGL <3s at 174k

**TF-IDF production modes (3) operational at FULL 174k**:
- metadata_174k_full.json COMPLETE (16/16 scale simulation tests PASS)
- 95.7% section coverage

---

## Evaluation Harness Readiness (for incoming representations)

| Component | Status |
|---|---|
| Formal suite harness v3 | Operational (frozen thresholds) |
| Exact k-NN adversarial | Verified (HNSW artifact fixed) |
| Citation heritage pairs | Frozen (1,020 pos/neg from 174k resolved citations) |
| v17b normalization pipeline | Tested and documented |
| v18 coarse hierarchy test | Validated as negative result |
| Jurist study framework | Simulation complete; requires 5–10 Swiss jurists (no budget) |

**Awaiting from legal-distance**:
1. 174k center_projected dense embeddings (768/128/64 dim)
2. Metric learning embeddings (linear/Mahalanobis/hybrid objectives)
3. Citation role embeddings (citing/following/criticizing/neutral)
4. Linear hybrids (linear_hybrid05_concat, linear_citation_concat, etc.)
5. Section-specific embeddings at full density (sachverhalt/erwaegungen/dispositiv)

---

## Next Recommendation

**PAUSE** — Factory direction v29 question fully addressed for available representations.

No additional same-question cycles justified. Lane should remain PAUSED until legal-distance delivers ACCEPTED 174k dense embeddings and derived representations.

**Factory Director decision required**: Successor question for evaluation lane (legal-distance recommends FRONTIER_TEAM_REQUIRED for dense embedding data acquisition).

---

## Evidence References (Machine-Readable)

All claim-bearing outputs preserved at:
- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
- `evaluation/results/174k/dense_165k_formal_suite/evaluation_165k_dense_formal_suite_latest.json`
- `evaluation/results/174k_citation_heritage/citation_heritage_174k_tfidf_latest.json`
- `evaluation/results/174k_citation_heritage/citation_pairs_174k.json`
- `evaluation/results/v17b_174k_tfidf/v17b_174k_tfidf_latest.json`
- `evaluation/results/v17b_174k_generalization/v17b_174k_generalization_20260930_011927.json`
- `evaluation/results/v17b_174k_dense_partial/v17b_174k_dense_partial_latest.json`
- `evaluation/results/v18_coarse_hierarchy/v18_coarse_hierarchy_results.json`

Negative results preserved as first-class evidence per Research Protocol §5.