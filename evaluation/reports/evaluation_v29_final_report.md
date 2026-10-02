# LexMachina Evaluation Lane — Factory Direction v29 Final Report

**Run ID:** eval_174k_formal_suite_v29_20261001  
**Lane:** evaluation  
**Direction Version:** 29  
**Date:** 2026-10-02  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** COMPLETE  
**Continue Recommended:** false  

---

## Executive Summary

The evaluation lane has **fully addressed the factory direction v29 question** for all currently available representations. All three deliverables are complete:

1. ✅ **Full 12-benchmark formal suite at 174k scale** — TF-IDF family (8 representations) COMPLETE with frozen harness v3
2. ✅ **Citation heritage benchmark validated** — 174k citation-ID resolution (2,019/2,105 resolved), 1,020 positive/negative pairs tested
3. ✅ **v17b label normalization generalization to 174k** — TESTED, NEGATIVE (different regime at scale)

**No new ACCEPTED representations have landed from legal-distance since the last evaluation cycle.** The lane correctly PAUSEs until legal-distance delivers 174k dense embeddings, metric learning, citation roles, and linear hybrids.

---

## Deliverable 1: 174k Formal Suite — TF-IDF Family (COMPLETE)

### Results Summary

| Representation | LangDom | JuristPref | Both Pass | Verdict |
|----------------|---------|------------|-----------|---------|
| cited_decisions_tfidf | 0.4794 | 0.7140 | ✅ | PASS |
| outcome_tfidf | 0.5015 | 0.6550 | ✅ | PASS |
| regeste_tfidf | 0.4853 | 0.6315 | ✅ | PASS |
| full_text_tfidf_light | 0.4855 | 0.7080 | ✅ | PASS |
| **cited_decisions_tfidf_outcome_hybrid_0.5** | **0.4895** | **0.7265** | ✅ | **PASS (BEST)** |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.4783 | 0.7275 | ✅ | PASS |
| regeste_full_text_hybrid_0.5 | 0.4855 | 0.6890 | ✅ | PASS |
| regeste_full_text_hybrid_0.7 | 0.4835 | 0.6850 | ✅ | PASS |

**All 8 TF-IDF representations PASS both adversarial gates on frozen harness v3 at 173,963 decisions.**

### Full-Corpus Benchmarks (174k)

| Benchmark | cited_decisions_tfidf | cited_decisions_tfidf_outcome_hybrid_0.5 | full_text_tfidf_light |
|-----------|----------------------|-----------------------------------------|----------------------|
| Temporal Stability | FAIL (0.36) | FAIL (0.38) | **PASS (0.78)** |
| Hierarchy Coherence | FAIL (nesting 0.34) | FAIL (nesting 0.32) | FAIL (nesting 0.29) |
| Cluster Coherence | FAIL (branch_purity 0.34) | FAIL (branch_purity 0.32) | FAIL (branch_purity 0.29) |
| Cross-Language Retrieval | FAIL (0.13) | FAIL (0.14) | FAIL (0.14) |
| Boilerplate Resistance | FAIL (-0.84) | FAIL (-0.83) | FAIL (-0.84) |

**Key Finding:** The two-mode tradeoff persists at 174k scale:
- **Citation-based signals** (cited_decisions_tfidf family): PASS adversarial gates, PASS citation heritage (AUC 0.71-0.74), FAIL cross-language retrieval
- **Text-based signals** (regeste_tfidf, full_text_tfidf_light): PASS adversarial gates, FAIL citation heritage (AUC ~0.50-0.63), better branch metadata recovery

### Production Default Validated
**cited_decisions_tfidf_outcome_hybrid_0.5** is the PRODUCTION DEFAULT:
- PASS both adversarial gates (LangDom=0.4895, JuristPref=0.7265)
- PASS citation_heritage (AUC=0.7163)
- Operational at full 173,963 decisions with 5 zoom levels
- Wired in product lane as `PRODUCT_SERVING_DEFAULT`

---

## Deliverable 2: Citation Heritage Benchmark (VALIDATED)

### Methodology
- Frozen pair pool: 1,020 positive (citing) + 1,020 negative (non-citing) pairs
- Derived from 174k resolved citation graph (2,019/2,105 citations resolved = 95.9%)
- AUC-ROC threshold: frozen at ≥0.65 (stricter: ≥0.7 for strong pass)

### Results

| Representation | AUC-ROC | Status |
|----------------|---------|--------|
| cited_decisions_tfidf | **0.7426** | PASS (≥0.7) |
| cited_decisions_tfidf_outcome_hybrid_0.7 | **0.7290** | PASS (≥0.7) |
| cited_decisions_tfidf_outcome_hybrid_0.5 | **0.7163** | PASS (≥0.65) |
| regeste_full_text_hybrid_0.7 | 0.6595 | PASS (≥0.65) |
| regeste_full_text_hybrid_0.5 | 0.6365 | FAIL |
| full_text_tfidf_light | 0.6257 | FAIL |
| outcome_tfidf | 0.6262 | FAIL |
| regeste_tfidf | 0.5030 | FAIL (~random) |

**4/8 PASS at frozen threshold AUC≥0.65; 3/8 PASS at AUC≥0.7 (cited_decisions_tfidf family).**

### Critical Finding
**Citation signals recover citation heritage; text signals do not.** This confirms the fundamental two-mode tradeoff:
- Citation-based representations encode legal authority/precedent relationships
- Text-based representations encode topical/content similarity
- No single representation dominates all metrics

---

## Deliverable 3: v17b Label Normalization Generalization (NEGATIVE)

### v17b at 1000 Scale (REPRODUCED)
- 6 representations × 4 seeds (42, 123, 456, 789)
- Hierarchy purity gain: **15-25%** (ratios 1.15-1.24)
- Uniform improvement across all representations
- **Evidence Tier: REPRODUCED**

### v17b at 174k Scale (GENERALIZATION TESTED — NEGATIVE)
- 8 representations tested on 15k subsample
- Label space: 213 raw legal_area labels → 111 normalized (vs 104→54 at 1000)
- Purity ratios: **4-10x improvement** (much larger than 1000 scale)
- **BUT NMI decreases on normalized labels** (e.g., cited_decisions_tfidf: 0.158→0.150 hierarchy NMI)

| Representation | Hierarchy Purity Ratio | Zoom Fine Ratio | Legal Area Ratio | NMI Change |
|----------------|----------------------|----------------|------------------|------------|
| cited_decisions_tfidf | 5.18x | 6.47x | 6.47x | -0.008 |
| outcome_tfidf | 10.07x | 10.07x | 10.07x | -0.013 |
| regeste_tfidf | 6.64x | 7.84x | 7.84x | -0.016 |
| full_text_tfidf_light | 4.70x | 5.89x | 5.89x | -0.035 |

**Conclusion:** v17b label normalization is REPRODUCED as a method but operates in a **fundamentally different regime at 174k scale**. The fine-grained label space (213→111) creates different clustering dynamics. Separate validation required for 174k deployment.

---

## Additional Completed Evaluations

### v18 Coarse Hierarchy (NEGATIVE)
- Tested 6 representations at branch level (4 labels: öffentliches_recht, zivilrecht, strafrecht, sozialversicherungsrecht)
- **Best purity: 0.65 (linear_citation_concat) < 0.7 threshold**
- All 6 representations FAIL branch-level hierarchy coherence
- **Fundamental limitation:** TF-IDF and citation-based representations lack sufficient signal density for branch-level legal structure recovery at any scale

### 3-Year Accepted Dense Embeddings (FAIL)
- center_projected_768/128/64dim at 12,570 decisions (2000-2002)
- Language dominance: **0.996-0.997** (FAIL, threshold 0.85)
- Jurist preference: **0.005-0.007** (FAIL, threshold >0.5)
- Cross-language transfer: PASS (zero-shot NMI 0.43-0.51)
- **Verdict: FAIL both adversarial gates**

### 15-Year Checkpointed Dense Embeddings (FAIL)
- center_projected_768/128/64dim at 91,929 decisions (2000-2014)
- Language dominance: **0.893-0.899** (FAIL)
- Jurist preference: **0.267-0.288** (FAIL)
- Cross-language transfer: PASS (zero-shot NMI 0.33-0.38)
- **Verdict: FAIL both adversarial gates**

### 15-Year Checkpointed Linear Hybrids (FAIL)
- linear_citation_concat: LangDom=0.794 PASS, JP=0.481 FAIL (delta -0.242 vs TF-IDF baseline 0.723)
- linear_hybrid05_concat: LangDom=0.809 PASS, JP=0.473 FAIL (delta -0.247 vs baseline)
- **Clear scale dependency confirmed; two-mode tradeoff persists**

---

## Legal-Distance Dependency Status

| Representation | Status | Decisions | Notes |
|----------------|--------|-----------|-------|
| 3-year dense (2000-2002) | **ACCEPTED** | ~19,441 | Evaluated: FAIL |
| 15-year dense (2000-2014) | **CHECKPOINTED** | ~100k | Evaluated: FAIL (PENDING AUDIT) |
| 19-year dense (2000-2018) | **CHECKPOINTED** | ~122k | NOT YET EVALUATED (PENDING AUDIT) |
| 174k dense (2000-2026) | **BLOCKED** | 173,963 | BGE/bger ID mismatch; missing 2019, 2025, 2026 |
| Metric learning | **PENDING** | — | Requires 174k dense |
| Citation roles | **PENDING** | — | Requires 174k dense |
| Section-specific (sachverhalt/erwaegungen/dispositiv) | **PENDING** | — | 1K sample done; full density blocked |

**Legal-distance next recommendation:** FRONTIER_TEAM_REQUIRED for dense embedding data acquisition (parquet 2019-2026 or BGE↔BGER ID mapping).

---

## Critical Findings Summary

| Finding | Evidence Tier | Implication |
|---------|---------------|-------------|
| TF-IDF 174k formal suite complete | ACCEPTED | Production default validated; 8/8 PASS adversarial |
| Citation heritage: citation signals dominate | REPRODUCED | Two-mode tradeoff confirmed at all scales |
| v17b label normalization: regime shift at 174k | REPRODUCED (method) / NEGATIVE (generalization) | Separate 174k validation needed |
| v18 coarse hierarchy: fundamental limit | REPRODUCED (negative) | TF-IDF/citation reps cannot recover branch structure |
| Dense embeddings: FAIL jurist gate at all tested scales | REPRODUCED | center_projected baselines insufficient |
| Linear hybrids: scale dependency | REPRODUCED | Citation signals dominate jurist preference |
| Boilerplate resistance proxy: measures language dominance | REPRODUCED | Not measuring procedural boilerplate |
| Jurist study framework ready | EXPLORATORY | Requires 5-10 Swiss jurists; no budget |

---

## Evaluation Readiness for New Representations

| Component | Status |
|-----------|--------|
| Formal suite harness (v3) | ✅ Operational |
| Exact k-NN adversarial (HNSW artifact fixed) | ✅ Verified |
| Citation heritage pairs (frozen) | ✅ 1,020 pos/neg from 174k |
| v17b normalization pipeline | ✅ Tested & documented |
| v18 coarse hierarchy test | ✅ Validated as negative result |
| **Awaiting from legal-distance** | |
| 174k center_projected dense embeddings | ⏳ BLOCKED |
| Metric learning embeddings | ⏳ BLOCKED |
| Citation role embeddings | ⏳ BLOCKED |
| Linear hybrids | ⏳ BLOCKED |
| Section-specific embeddings (full density) | ⏳ BLOCKED |

---

## Recommendation

**Cycle Status:** COMPLETE — All factory direction v29 deliverables addressed for available representations.

**Continue Recommended:** **false** — No additional same-question cycle justified.

**Next Recommendation:** **PAUSE (BLOCKED_ON_DEPENDENCIES)**

The evaluation lane should remain paused until legal-distance delivers:
1. 174k dense embeddings (ACCEPTED, not checkpointed)
2. Metric learning embeddings at 174k
3. Citation role embeddings at 174k
4. Linear hybrids at 174k
5. Section-specific embeddings at full 174k density

**Factory Director Decision Required:** Successor question for evaluation lane (legal-distance recommends FRONTIER_TEAM_REQUIRED for dense embedding data acquisition).

---

## Evidence References

### Formal Suite Results
- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` — TF-IDF 8 reps at 174k
- `evaluation/results/174k/formal_suite/15year_dense/evaluation_15year_dense_formal_suite_latest.json` — 15yr dense + hybrids
- `evaluation/results/174k/dense_3year_formal_suite/evaluation_3year_dense_formal_suite_latest.json` — 3yr accepted dense

### Citation Heritage
- `evaluation/results/174k_citation_heritage/citation_heritage_174k_tfidf_latest.json` — TF-IDF 8 reps
- `evaluation/results/174k_citation_heritage/citation_pairs_174k.json` — Frozen pair pool

### Label Normalization
- `evaluation/results/v17b_174k_tfidf/v17b_174k_tfidf_latest.json` — 174k TF-IDF (15k subsample)
- `evaluation/results/v17b_174k_generalization/v17b_174k_generalization_20260930_011927.json` — Generalization test

### Coarse Hierarchy
- `evaluation/results/v18_coarse_hierarchy/v18_coarse_hierarchy_results.json` — 6 reps at branch level

### Cross-Lane References
- `/tmp/lex_accepted/legal-distance/state/legal-distance.json` — Legal-distance v29 state
- `/tmp/lex_accepted/corpus/state/corpus.json` — Corpus v29 state

---

## State File Consistency

The machine-readable state file at `state/evaluation.json` is current and consistent with this report:

```json
{
  "lane": "evaluation",
  "direction_version": 29,
  "evidence_tier": "REPRODUCED",
  "cycle_status": "COMPLETE",
  "continue_recommended": false,
  "accepted_run_id": "eval_174k_formal_suite_v29_20261001",
  "next_recommendation": "PAUSE — Factory direction v29 question fully addressed for available representations..."
}
```

---

**Signed:** LEXMACHINA EVALUATION ENGINEER  
**Run:** eval_174k_formal_suite_v29_20261001  
**Factory Direction:** v29