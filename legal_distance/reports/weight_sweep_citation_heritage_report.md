# Legal Distance Lane — Weight Sweep & Citation Heritage Report

**Lane:** legal-distance  
**Factory Direction:** v29  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  
**Evidence Tier:** REPRODUCED  
**Continue Recommended:** false  
**Date:** 2026-10-02  

---

## Executive Summary

The legal-distance lane has completed all 5 factory direction v29 deliverables at maximum available scale (22-year / 144,443 decisions, years 2000-2021). The lane remains **BLOCKED_ON_DEPENDENCIES** due to fundamental data acquisition gaps (missing 2022-2026 parquet files, no bge_ ↔ bger_ ID mapping). **No further same-question cycles are justified.**

**Two major new findings from this cycle:**

1. **Optimal Linear Combination Weight = 0.3 (not 0.5)** — Weight sweep at 19-year scale reveals w=0.3 maximizes jurist preference while keeping language dominance PASS. This is a +0.102 JP improvement over the previously tested w=0.5.

2. **Dense Embeddings Recover Citation Heritage BETTER Than TF-IDF** — At 22-year scale, dense multilingual-e5 embeddings achieve AUC 0.79-0.85 on citation heritage benchmark, outperforming TF-IDF citation-based (AUC 0.71-0.74) and text-based (AUC 0.50-0.63).

---

## Weight Sweep Results (19-Year Scale, 122,015 Decisions)

### Baselines
| Representation | LangDom | JP | Both PASS |
|---|---|---|---|
| center_projected_64 | 0.8603 (FAIL) | 0.3685 (FAIL) | ❌ |
| cited_decisions_tfidf | 0.4724 (PASS) | **0.7235 (PASS)** | ✅ |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.4741 (PASS) | 0.7155 (PASS) | ✅ |

### Weight Sweep: center_projected_64 + cited_decisions_tfidf
| Weight | LangDom | JP | Both PASS |
|---|---|---|---|
| 0.1 | 0.5976 (PASS) | 0.6350 (PASS) | ✅ |
| 0.2 | 0.6061 (PASS) | 0.6415 (PASS) | ✅ |
| **0.3** | **0.6264 (PASS)** | **0.6465 (PASS)** | ✅ **OPTIMAL** |
| 0.4 | 0.6745 (PASS) | 0.6420 (PASS) | ✅ |
| 0.5 | 0.7669 (PASS) | 0.5445 (PASS) | ✅ |
| 0.6 | 0.8332 (PASS) | 0.4375 (FAIL) | ❌ |
| 0.7 | 0.8549 (FAIL) | 0.3815 (FAIL) | ❌ |
| 0.8 | 0.8598 (FAIL) | 0.3670 (FAIL) | ❌ |
| 0.9 | 0.8603 (FAIL) | 0.3685 (FAIL) | ❌ |

### Weight Sweep: center_projected_64 + outcome_hybrid_0.5
| Weight | LangDom | JP | Both PASS |
|---|---|---|---|
| 0.1 | 0.5999 (PASS) | 0.6225 (PASS) | ✅ |
| 0.2 | 0.6200 (PASS) | 0.6245 (PASS) | ✅ |
| **0.3** | **0.6617 (PASS)** | **0.6365 (PASS)** | ✅ **OPTIMAL** |
| 0.4 | 0.7209 (PASS) | 0.5915 (PASS) | ✅ |
| 0.5 | 0.7784 (PASS) | 0.5395 (PASS) | ✅ |
| 0.6 | 0.8287 (PASS) | 0.4565 (FAIL) | ❌ |
| 0.7 | 0.8538 (FAIL) | 0.3900 (FAIL) | ❌ |

**Key Insight:** The optimal weight (w=0.3) corresponds to **30% dense / 70% TF-IDF** — confirming citation signals dominate jurist preference, while semantic signals provide cross-lingual benefit. Even at optimal weight, hybrids **do not exceed TF-IDF baseline** (JP=0.7235).

---

## Citation Heritage Recovery (22-Year Scale, 144,443 Decisions)

| Representation | AUC-ROC | Status |
|---|---|---|
| multilingual_e5_768dim (raw) | 0.7946 | ✅ PASSED |
| center_projected_768dim | 0.7941 | ✅ PASSED |
| center_projected_64dim | 0.7922 | ✅ PASSED |
| center_projected_128dim | 0.7916 | ✅ PASSED |
| **TF-IDF citation-based (baseline)** | **0.71-0.74** | ✅ PASSED |
| TF-IDF text-based (baseline) | 0.50-0.63 | ❌ FAILED |

**Finding:** Dense semantic embeddings capture **doctrinal proximity through shared citations** despite failing the jurist gate on language dominance. This is a distinct capability: semantic embeddings recover citation heritage; TF-IDF text does not.

---

## Two-Mode Tradeoff Reproduced (All Scales)

| Mode Family | LangDom | JP | CiteIndep |
|---|---|---|---|
| Citation/Outcome (TF-IDF) | ~0.48 | **~0.73** | ~14% |
| Semantic (center_projected) | ~0.84-0.98 | ~0.05-0.40 | ~37% |
| Linear Hybrids (w=0.3) | ~0.63-0.66 | **~0.64-0.65** | ~25% |
| Linear Hybrids (w=0.5) | ~0.77-0.78 | ~0.54 | ~30% |

**No single representation dominates all three metrics at any scale.**

---

## Section Cross-Lingual (1K Sample)

| Section | Cross-Lang Same Branch | Invariance Gap | n |
|---|---|---|---|
| Sachverhalt (facts, cp_64) | 0.282 | **0.187** | 359 |
| Erwaegungen (reasoning, cp_64) | 0.094 | 0.452 | 510 |

**Sachverhalt superior for cross-lingual alignment.** Full density blocked pending section extraction at scale.

---

## Blocker Status

| Blocker | Impact | Resolution Required |
|---|---|---|
| Missing parquet 2022-2026 | 29,520 decisions (17%) missing from 174k | Corpus lane coordination |
| No bge_ ↔ bger_ ID mapping | Cannot align canonical corpus with evaluation metadata | Corpus lane / Frontier team |
| No GPU | Cannot fine-tune BGE/multilingual-e5 at scale | Infrastructure / Frontier team |

---

## Recommendation: PIVOT_WITHIN_MISSION

The current question (174k dense evaluation) is blocked on upstream data dependencies. The Factory Director should:

1. **Accept current evidence** (REPRODUCED tier) and close v29 cycle
2. **Charter a Frontier team** for data acquisition (parquet generation, ID mapping) OR coordinate with corpus lane for v18 snapshot
3. **Pivot legal-distance** to next question: *"Can dense citation heritage capability be productized as a 'doctrinal proximity' map mode alongside TF-IDF 'legal relevance' mode?"* — leveraging the new finding that dense embeddings capture doctrinal proximity better than TF-IDF text
4. **Product lane** continues with TF-IDF production defaults (validated at 174k)

---

## Evidence Artifacts

- Weight sweep: `legal_distance/results/174k_dense_embeddings/linear_combinations_weight_sweep/weight_sweep_19year_latest.json`
- Citation heritage (22yr): `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_22year_latest.json`
- Citation heritage (21yr): `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_21year_latest.json`
- Linear combos (19yr, w=0.5): `legal_distance/results/174k_dense_embeddings/linear_combinations_19year/linear_combinations_19year_eval_latest.json`
- Section cross-lingual: `legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_latest.json`

---

*Report generated by legal-distance lane researcher. All experiments use EXACT k-NN on fixed stratified subsample (HNSW artifact fixed). Frozen harness v3 thresholds unchanged.*