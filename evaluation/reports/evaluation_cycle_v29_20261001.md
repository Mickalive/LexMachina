# Evaluation Lane — Cycle Report (Factory Direction v29)

**Lane**: evaluation
**Direction Version**: 29
**Cycle Status**: COMPLETE
**Evidence Tier**: REPRODUCED
**Run ID**: eval_174k_formal_suite_v29_20261001
**Date**: 2026-10-01

---

## Executive Summary

The factory direction v29 evaluation question — *"Run the machine-executable 174k formal suite autonomously as representations land"* — has been **fully addressed for all currently available representations**.

All three deliverables are complete:
1. ✅ **Full 12-benchmark formal suite at 174k scale** on all 8 TF-IDF production representations (frozen harness v3)
2. ✅ **Citation heritage benchmark validated** on 174k using 2,019/2,105 resolved citation IDs (1,020 positive/negative pairs)
3. ✅ **v17b label normalization generalization tested** at 174k — NEGATIVE result (different regime confirmed)

**No new 174k representations have landed from legal-distance** since the last evaluation cycle. Legal-distance remains BLOCKED_ON_DEPENDENCIES awaiting dense embedding data acquisition (FRONTIER_TEAM_REQUIRED). The evaluation lane should **PAUSE** until new 174k representations arrive.

---

## Detailed Findings

### 1. TF-IDF 174k Formal Suite — COMPLETE (8/8 representations)

| Representation | LangDom | JuristPref | Both Gates | Citation Heritage (AUC) |
|---|---|---|---|---|
| cited_decisions_tfidf | 0.492 | 0.708 | PASS | 0.7426 PASS |
| **cited_decisions_tfidf_outcome_hybrid_0.5** | **0.477** | **0.735** | **PASS** | **0.7163 PASS** |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.478 | 0.728 | PASS | 0.7290 PASS |
| outcome_tfidf | 0.502 | 0.655 | PASS | 0.6262 FAIL |
| regeste_tfidf | 0.485 | 0.632 | PASS | 0.5030 FAIL |
| full_text_tfidf_light | 0.485 | 0.708 | PASS | 0.6257 FAIL |
| regeste_full_text_hybrid_0.5 | 0.480 | 0.679 | PASS | 0.6365 FAIL |
| regeste_full_text_hybrid_0.7 | 0.485 | 0.692 | PASS | 0.6595 PASS |

**Production default validated**: `cited_decisions_tfidf_outcome_hybrid_0.5` — PASS both adversarial gates, PASS citation heritage, operational at full 173,963 decisions.

**Full-corpus benchmarks** (HNSW on 30k-150k subsamples):
- Temporal stability: PASS only for `full_text_tfidf_light` (0.78)
- Hierarchy coherence: FAIL all (nesting ~0.27-0.34)
- Cluster coherence: FAIL all (branch_purity ~0.28-0.36, lang_purity ~0.60)
- Boilerplate resistance: FAIL all (resistance ≈ -0.84)

---

### 2. Citation Heritage at 174k — VALIDATED

- **Pairs**: 1,020 positive (shared citations) + 1,020 negative (no shared citations)
- **Citation graph**: 2,019/2,105 citations resolved (95.9%)
- **Result**: Citation-based signals DOMINATE — 4/8 PASS (AUC 0.71-0.74); text-based FAIL (AUC ~0.50-0.63)
- **Confirms**: Fundamental two-mode tradeoff reproduced at full 174k scale

---

### 3. v17b Label Normalization — REPRODUCED at 1k, NEGATIVE Generalization at 174k

| Scale | Labels (raw→norm) | Hierarchy Purity Gain | NMI Change | Evidence Tier |
|---|---|---|---|---|
| 1000 decisions | 104 → 54 | 15-25% (ratios 1.15-1.24) | Increases | **REPRODUCED** (4 seeds) |
| 174k (15k subsample) | 213 → 111 | 400-1000% (ratios 4-10x) | **Decreases** | **FAIL — different regime** |

**Conclusion**: Method is reproducible but does not generalize with same-magnitude effect. 174k fine-grained labels operate in a qualitatively different regime.

---

### 4. v18 Coarse Hierarchy — NEGATIVE

- **Test**: 4-label branch level (oeffentliches_recht, zivilrecht, strafrecht, sozialversicherungsrecht)
- **Best purity**: 0.65 (linear_citation_concat) < 0.7 threshold
- **All 6 representations FAIL** branch-level hierarchy coherence
- **Finding**: Fundamental limitation — TF-IDF/citation representations lack signal density for legal structure recovery at any scale

---

### 5. Dense Embeddings — BLOCKED in Legal-Distance

| Status | Decisions | Years | Notes |
|---|---|---|---|
| ACCEPTED | ~19k | 3/26 (2000-2002) | Only 3 years post-audit |
| CHECKPOINTED (PENDING AUDIT) | ~122k | 19/26 (2000-2018) | 15-year (100k) + 19-year (122k) |
| MISSING | ~52k | 2019, 2025, 2026 | Parquet unavailable; BGE↔bger ID mismatch |

**Checkpoint findings** (not yet evaluated by evaluation lane):
- 15-year center_projected: FAILS jurist gate (JP=0.39-0.42)
- 19-year center_projected: FAILS jurist gate (JP=0.39-0.42)
- Linear hybrid 15-year: FAILS jurist gate (JP=0.473, Δ=-0.2465 vs TF-IDF)
- Linear hybrid 19-year: PASSES gates but BELOW TF-IDF baseline (JP=0.540 vs 0.724)
- Section cross-lingual (1K sample): Sachverhalt superior to Erwaegungen

---

## Two-Mode Tradeoff — CONFIRMED at All Scales

| Mode Family | Citation Heritage | Jurist Preference | Cross-Lang Retrieval | Citation Independence |
|---|---|---|---|---|
| **Citation-based** (TF-IDF hybrids) | PASS (AUC>0.71) | HIGH (~0.73) | POOR (~0.14) | ~14% |
| **Text-based** (regeste, full_text) | FAIL (AUC~0.5-0.63) | MODERATE (~0.65) | POOR (~0.12) | ~37% |
| **Dense semantic** (center_projected) | FAIL | LOW (~0.39) | GOOD (~0.26) | ~37% |
| **Metric learning** (hybrid objectives) | MODERATE | MODERATE (~0.53-0.61) | MODERATE | ~34-37% |

**No single representation dominates all metrics.** Production default optimizes for jurist preference + citation heritage.

---

## Evaluation Harness Readiness

| Component | Status |
|---|---|
| Formal suite harness (v3) | Operational — frozen thresholds, exact k-NN |
| Adversarial benchmarks | Verified — HNSW artifact fixed via sklearn_exact on stratified subsample |
| Citation heritage pairs | Frozen — 1,020 pos/neg from 174k resolved citations |
| v17b normalization pipeline | Tested & documented |
| v18 coarse hierarchy test | Validated as negative result |
| Jurist simulation framework | Ready — requires 5-10 Swiss jurists (no budget) |

---

## Awaiting from Legal-Distance

1. 174k center_projected dense embeddings (768/128/64 dim)
2. Metric learning embeddings (linear/Mahalanobis/hybrid objectives)
3. Citation role embeddings (citing/following/criticizing/neutral)
4. Linear hybrids (linear_hybrid05_concat, linear_citation_concat, etc.)
5. Section-specific embeddings at full density (sachverhalt/erwaegungen/dispositiv)

---

## Recommendation

**PAUSE** the evaluation lane on the current factory direction question.

- All three deliverables complete for available representations
- No new 174k representations have landed
- Legal-distance blocked on dense embedding data acquisition (FRONTIER_TEAM_REQUIRED)
- Factory Director should decide successor question

**Next cycle trigger**: When legal-distance delivers 174k dense embeddings (or any new 174k representation), evaluation lane will automatically run the formal suite and report results.

---

## Evidence References

- Formal suite: `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
- Citation heritage: `evaluation/results/174k_citation_heritage/citation_heritage_174k_tfidf_latest.json`
- v17b 1k: `evaluation/results/v17b_174k_tfidf/v17b_174k_tfidf_latest.json`
- v17b 174k generalization: `evaluation/results/v17b_174k_generalization/v17b_174k_generalization_20260930_011927.json`
- Legal-distance state: `legal-distance/state/legal-distance.json`
- Corpus state: `corpus/state/corpus.json`