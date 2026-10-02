# Evaluation Lane — v29 Cycle Final Report (2026-10-02)

## Executive Summary

All three factory direction v29 mandated deliverables are **DELIVERED and REPRODUCIBLE** for the TF-IDF family (8 representations at 174k scale). The evaluation infrastructure is **FULLY OPERATIONAL and AUDIT-READY**. The lane is **COMPLETE** for the current question — no further same-question cycle is justified. Lane should **PAUSE** until legal-distance delivers new 174k representations.

---

## Deliverables Status (v29 Factory Direction)

| Deliverable | Status | Details |
|-------------|--------|---------|
| **1. Full 12-benchmark formal suite at 174k** | ✅ COMPLETE | All 8 TF-IDF representations evaluated with frozen harness v3 (exact k-NN on stratified subsample n=2000, config hash `b51701f5a9c11692`). ALL 8 PASS both adversarial gates. |
| **2. Citation heritage benchmark at 174k** | ✅ COMPLETE | Validated on frozen 1,020-pair pool (95.9% corpus citation ID resolution). **4/8 PASS AUC-ROC ≥ 0.7** (citation-based signals), **4/8 FAIL** (text-based signals) — confirms two-mode tradeoff. |
| **3. v17b label normalization generalization** | ✅ COMPLETE | NEGATIVE result: does NOT generalize to 174k fine-grained labels. Hierarchy=1.0x for ALL reps (no improvement); zoom_fine DEGRADES for 4/8 reps (0.83-0.99x). Regeste_tfidf only representation with no-worsening on ALL hierarchy metrics. |

---

## Adversarial Gate Results (Frozen Harness v3, Config Hash: `b51701f5a9c11692`)

| Representation | Language Dominance | Jurist Preference | Both PASS |
|----------------|-------------------|-------------------|-----------|
| `cited_decisions_tfidf_outcome_hybrid_0.5` (production default) | **0.4895** ✅ | **0.7265** ✅ | ✅ |
| `cited_decisions_tfidf_outcome_hybrid_0.7` | 0.4908 ✅ | 0.7195 ✅ | ✅ |
| `cited_decisions_tfidf` | 0.4917 ✅ | 0.7075 ✅ | ✅ |
| `full_text_tfidf_light` | 0.4855 ✅ | 0.7080 ✅ | ✅ |
| `regeste_full_text_hybrid_0.5` | 0.4873 ✅ | 0.7140 ✅ | ✅ |
| `regeste_full_text_hybrid_0.7` | 0.4889 ✅ | 0.7120 ✅ | ✅ |
| `outcome_tfidf` | 0.5078 ✅ | 0.6660 ✅ | ✅ |
| `regeste_tfidf` | 0.5111 ✅ | 0.6145 ✅ | ✅ |

**Thresholds**: LangDom < 0.85, Jurist > 0.5 — **ALL 8 PASS**

*Values from authoritative frozen-harness formal suite (`evaluation_174k_formal_suite_latest.json`), not monitor check 273.*

---

## Critical Findings

### Two-Mode Tradeoff CONFIRMED at 174k
- **Citation-based signals** (cited_decisions_tfidf family): PASS citation_heritage (AUC 0.71-0.74), PASS adversarial, HIGH jurist preference (0.71-0.73)
- **Text-based signals** (regeste_tfidf, full_text_tfidf_light): FAIL citation_heritage (AUC ~0.50-0.63), PASS adversarial, MODERATE jurist preference (0.61-0.71)
- **Fundamental**: No single representation dominates all metrics

### v17b Label Normalization: REGIME SHIFT at 174k
- 1000-scale: 15-25% hierarchy purity gain REPRODUCED across 4 seeds
- 174k-scale: 213→111 labels (vs 104→54 at 1k); purity ratios 4-10x but **NMI decreases** on normalized labels
- **Conclusion**: Method reproduced but effect regime fundamentally different — requires separate validation

### v18 Coarse Hierarchy: NEGATIVE
- Even at 4-label branch level: best purity 0.65 (linear_citation_concat) < 0.7 threshold
- **Fundamental hierarchy limitation** for TF-IDF/citation representations at any scale

### Boilerplate Resistance: NEGATIVE (Proxy Issue)
- All representations resistance_score ≈ -0.84
- Measures language dominance/cross-lingual failure, NOT procedural boilerplate
- Consistent across TF-IDF and dense embeddings

---

## Legal-Distance 19-Year Checkpoint Status (Available but NOT at 174k)

| Representation | Scale | LangDom | Jurist Pref | Verdict |
|----------------|-------|---------|-------------|---------|
| raw 768dim | 122k | 0.983 | 0.047 | ❌ FAIL |
| center_projected 768/128/64dim | 122k | 0.86-0.87 | 0.34-0.37 | ❌ FAIL |
| linear_citation_concat | 122k | 0.767 | 0.545 | ✅ PASS |
| linear_hybrid05_concat | 122k | 0.778 | 0.540 | ✅ PASS |
| cited_decisions_tfidf | 122k | 0.472 | 0.724 | ✅ PASS |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 122k | 0.474 | 0.716 | ✅ PASS |

**Key insight**: Linear hybrids PASS adversarial at 19-year scale but **still below TF-IDF baseline** (Jurist=0.72-0.73 vs 0.7265). Two-mode tradeoff persists at scale.

---

## Blockers for 174k Dense Evaluation

1. **Dense embeddings**: 15/26 years (2000-2014) checkpointed; ONLY 3/26 years (2000-2002) ACCEPTED; concatenation to 174k NOT DONE
2. **BGE/bger ID mismatch**: Canonical corpus uses bge_ IDs, evaluation uses bger_ IDs — no mapping exists
3. **Missing years**: 2019, 2025, 2026 not processed (51,948 decisions)
4. **Citation role embeddings**: Available in legal-distance v6 but not at 174k scale
5. **Linear hybrids at 174k**: Evaluated at 19-year scale only

---

## Infrastructure Verification (2026-10-02)

| Component | Status | Verification |
|-----------|--------|--------------|
| Formal suite harness (run_174k_formal_suite.py) | ✅ OPERATIONAL | Re-verified 2026-09-30, config hash `b51701f5a9c11692` |
| Exact k-NN adversarial (n=2000 stratified) | ✅ VERIFIED | Production default reproduces: LangDom=0.4895 PASS, JuristPref=0.7265 PASS |
| HNSW artifact fix | ✅ CONFIRMED | Exact k-NN on valid subset avoids HNSW masking representation differences |
| Citation heritage pipeline | ✅ READY | Frozen 1,020-pair pool (95.9% corpus resolution) |
| v17b normalization pipeline | ✅ READY | Differential effect reproduced across all 8 TF-IDF reps |
| v25 formal suite | ✅ VERIFIED | Executed on all 8 TF-IDF reps + v6 dense 3-year |
| Metadata 174k | ✅ VERIFIED | 173,963 entries, branch+legal_area 100% coverage |
| Monitor script | ✅ ACTIVE | Check count: 275, last check 2026-10-02T00:00 |

---

## Recommendation

**PAUSE / PIVOT_WITHIN_MISSION** — Lane is COMPLETE for the v29 question; no further same-question cycle justified.

- **No same-question cycle justified for TF-IDF** — all deliverables complete and reproducible
- **Evaluation infrastructure is audit-ready** for immediate evaluation of new 174k representations
- **Awaiting from legal-distance** (priority order):
  1. 174k dense embeddings concatenation (blocked on BGE/bger ID mapping + missing years)
  2. Citation role embeddings at 174k
  3. Linear hybrids at 174k (legal_citation_concat, legal_hybrid05_concat)
  4. Section-specific embeddings at full density
  5. Metric learning embeddings (linear/Mahalanobis/hybrid objectives)

**Factory Director action needed**: legal-distance recommends FRONTIER_TEAM_REQUIRED for dense embedding data acquisition (parquet 2019-2026 or bge_↔bger_ ID mapping).

---

## Evidence Tier: REPRODUCED

All findings preserved including negative results (citation heritage split, v17b NEGATIVE, dense FAIL, v18 NEGATIVE, boilerplate resistance NEGATIVE). Config hash `b51701f5a9c11692` frozen for regression testing.

---

*Report generated: 2026-10-02T00:00:00Z | Monitor check: 275 | Factory direction: v29*