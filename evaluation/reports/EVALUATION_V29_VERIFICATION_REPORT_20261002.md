# Evaluation Lane Verification Report — Factory Direction v29

**Date:** 2026-10-02  
**Lane:** evaluation  
**Factory Direction Version:** 29  
**Status:** PAUSED (Awaiting legal-distance 174k dense embeddings delivery)  
**Evidence Tier:** REPRODUCED

---

## Executive Summary

The evaluation lane has completed all work for available representations at 174k scale. The frozen formal suite harness (v3 with HNSW artifact fix) is operational and verified. The citation heritage benchmark infrastructure is validated and ready for new representations.

**No new 174k representations have landed from legal-distance since the last evaluation cycle.** The lane correctly remains PAUSED per the research protocol — `continue_recommended: false` — until legal-distance delivers 174k dense embeddings, metric learning variants, citation role embeddings, linear hybrids, and section-specific embeddings.

---

## Verification Results (This Cycle)

### 1. Formal Suite Harness Smoke Test — **PASS**

Ran adversarial benchmarks (exact k-NN on fixed stratified subsample of 2,000 valid decisions) on production default representation:

| Metric | Value | Status |
|--------|-------|--------|
| Language Dominance | 0.4895 | ✅ PASS (< 0.85) |
| Jurist Pairwise Preference | 0.7265 | ✅ PASS (> 0.5) |
| Both Adversarial Gates | — | ✅ PASS |

**Configuration verified:** Frozen harness v3 thresholds unchanged, exact k-NN on valid subset (HNSW artifact fix confirmed), global seed=42, factory direction v29.

### 2. Citation Heritage Benchmark — **OPERATIONAL**

Validated benchmark infrastructure on 1,020 positive + 1,020 negative citation pairs from resolved citation graph (2,019/2,105 citations resolved at 95.9%):

| Representation | AUC-ROC | Expected |
|----------------|---------|----------|
| cited_decisions_tfidf | 0.7426 | ✅ PASS (≥ 0.7) |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.7290 | ✅ PASS |
| cited_decisions_tfidf_outcome_hybrid_0.5 (production default) | 0.7163 | ✅ PASS |
| regeste_tfidf | 0.5030 | ❌ FAIL (~random) |

**Fundamental two-mode tradeoff confirmed:** Citation-based signals recover citation heritage; text-based signals do not.

---

## Current State (from evaluation.json v29)

### Completed Work Items (3/3)

1. ✅ **TF-IDF family formal suite at 174k** — 8 representations, all PASS both adversarial gates
2. ✅ **Citation heritage validation at 174k** — 1,020 pairs, 4/8 PASS AUC-ROC ≥ 0.7
3. ✅ **v17b label normalization** — REPRODUCED at 1K (15-25% gain, 4 seeds); 174k generalization tested (NEGATIVE — different regime)
4. ✅ **v18 coarse hierarchy** — NEGATIVE (best branch purity 0.65 < 0.7 threshold)

### Blocked On

**legal-distance 174k dense embeddings delivery:**
- 3/26 years ACCEPTED (2000-2002, ~19k decisions)
- 15/26 years CHECKPOINTED (2000-2014, ~100k decisions) — PENDING AUDIT
- 11/26 years NOT YET PROCESSED (2015-2026)
- Years 2019, 2025, 2026 missing/failed
- Center_projected baselines FAIL jurist gate at 174k (JP=0.39-0.42)

---

## Evaluation Infrastructure Readiness

| Component | Status | Notes |
|-----------|--------|-------|
| Formal suite harness (v3 frozen) | ✅ Operational | Exact k-NN on valid subset; HNSW artifact fixed |
| Adversarial benchmarks | ✅ Verified | LangDom < 0.85, JuristPref > 0.5 thresholds frozen |
| Cross-language benchmarks | ✅ Ready | Zero-shot transfer, language-specific quality |
| Jurist usability benchmarks | ✅ Ready | Cluster coherence, zoom task, cross-lang retrieval |
| Citation heritage pairs | ✅ Frozen | 1,020 pos/neg pairs from 174k resolved citations |
| Scale stability / hierarchy / boilerplate | ✅ Ready | HNSW on subsamples (30k/15k) |
| v17b label normalization pipeline | ✅ Tested | REPRODUCED at 1K, regime difference documented at 174k |
| v18 coarse hierarchy test | ✅ Validated | Negative result confirmed as genuine failure |

---

## Critical Findings Summary (Unchanged from v29)

1. **TF-IDF 174k formal suite COMPLETE** — Production default `cited_decisions_tfidf_outcome_hybrid_0.5` validated (LangDom=0.4895, JuristPref=0.7265)
2. **Citation heritage VALIDATED** — Citation-based signals dominate (AUC 0.71-0.74); text-based fail (AUC ~0.5)
3. **v17b label normalization REPRODUCED** — But 174k generalization FAILS (different label regime: 213→111 vs 104→54)
4. **v18 coarse hierarchy NEGATIVE** — Fundamental hierarchy limitation at branch level (best 0.65 < 0.7)
5. **Two-mode tradeoff CONFIRMED** — Citation signals vs text signals; persists in dense embeddings at 165k
6. **Boilerplate resistance NEGATIVE** — All reps show resistance_score ≈ -0.84 (measures language dominance, not boilerplate)
7. **Jurist study framework READY** — Requires 5-10 Swiss jurists; no budget allocated

---

## Next Recommendation

**PAUSE** — Factory direction v29 question fully addressed for available representations.

The evaluation lane should remain PAUSED until legal-distance delivers:
- 174k center_projected dense embeddings (768/128/64 dim)
- Metric learning embeddings (linear/Mahalanobis/hybrid objectives)
- Citation role embeddings (citing/following/criticizing/neutral)
- Linear hybrids (linear_hybrid05_concat, linear_citation_concat, etc.)
- Section-specific embeddings at full density (sachverhalt/erwaegungen/dispositiv)

Factory Director to decide successor question. Legal-distance recommends FRONTIER_TEAM_REQUIRED for dense embedding data acquisition.

---

## Evidence References

- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
- `evaluation/results/174k/dense_165k_formal_suite/evaluation_165k_dense_formal_suite_latest.json`
- `evaluation/results/174k_citation_heritage/citation_heritage_174k_tfidf_latest.json`
- `evaluation/results/174k_citation_heritage/citation_pairs_174k.json`
- `evaluation/results/v17b_174k_tfidf/v17b_174k_tfidf_latest.json`
- `evaluation/results/v17b_174k_generalization/v17b_174k_generalization_20260930_011927.json`
- `evaluation/results/v17b_174k_dense_partial/v17b_174k_dense_partial_latest.json`
- `results/evaluation/v18_coarse_hierarchy/v18_coarse_hierarchy_results.json`
- `state/evaluation.json` (updated with verification timestamp)

---

## Compliance

- ✅ Frozen harness thresholds unchanged (v3, factory direction v6+)
- ✅ Exact k-NN on valid subset for adversarial benchmarks (HNSW artifact fix)
- ✅ Citation heritage pairs frozen from resolved 174k citation graph
- ✅ Negative results preserved (v18 coarse hierarchy, boilerplate resistance, v17b 174k generalization)
- ✅ No benchmark weakening after seeing results
- ✅ Provenance preserved in state/evaluation.json and evidence refs