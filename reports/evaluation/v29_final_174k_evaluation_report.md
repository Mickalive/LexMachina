# Evaluation Lane — Factory Direction v29 Final Report

**Cycle:** eval_174k_formal_suite_v29_20261001  
**Date:** 2026-10-01  
**Evidence Tier:** REPRODUCED  
**Status:** COMPLETE — PAUSED pending legal-distance 174k dense embeddings

---

## Executive Summary

The evaluation lane has **completed all three deliverables** from factory direction v29 for the representations currently available (TF-IDF family at 174k scale). The lane is now **blocked** on legal-distance delivering 174k dense embeddings (only 3/26 years ACCEPTED; 15/26 years checkpointed pending audit; years 2019, 2025, 2026 not processed).

### Key Findings at a Glance

| Deliverable | Status | Outcome |
|-------------|--------|---------|
| (1) 174k formal suite on all production reps | ✅ COMPLETE | TF-IDF family (8 reps) all PASS both adversarial gates; production default validated |
| (2) Citation heritage benchmark at 174k | ✅ COMPLETE | 1,020 pos/neg pairs from 2,019 resolved citations; citation signals dominate (AUC 0.71-0.74), text signals FAIL |
| (3) v17b label normalization generalization to 174k | ✅ COMPLETE | **NEGATIVE** — different regime at scale (213→111 labels, purity ratios 4-10x but NMI decreases) |
| **v18 coarse hierarchy** | ✅ COMPLETE | **NEGATIVE** — even at 4-label branch level, best purity 0.65 < 0.7 threshold; fundamental limitation |

---

## Deliverable 1: 174k Formal Suite (Frozen Harness v3)

### Scope
- **Corpus:** 173,963 decisions (full 2000-2026)
- **Representations:** 8 TF-IDF variants (128-dim via SVD)
- **Harness:** Frozen v3 thresholds, exact k-NN on stratified subsample (HNSW artifact fixed)
- **Benchmarks:** 12 total (adversarial ×2, cross-language ×3, jurist usability ×3, full-corpus ×4)

### Results Summary

| Representation | LangDom | JuristPref | Both Gates | Cluster Branch Purity | Lang Purity | Citation Heritage AUC |
|----------------|---------|------------|------------|----------------------|-------------|----------------------|
| **cited_decisions_tfidf_outcome_hybrid_0.5** | **0.4773** | **0.7345** | ✅ PASS | 0.3346 | 0.6046 | **0.7163** |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.4908 | 0.7195 | ✅ PASS | 0.3342 | 0.6046 | 0.7290 |
| cited_decisions_tfidf | 0.4917 | 0.7075 | ✅ PASS | 0.3577 | 0.6072 | **0.7426** |
| full_text_tfidf_light | 0.4855 | 0.7080 | ✅ PASS | 0.3132 | 0.6030 | 0.6257 |
| outcome_tfidf | 0.5078 | 0.6660 | ✅ PASS | 0.2995 | 0.6160 | 0.6262 |
| regeste_tfidf | 0.5111 | 0.6145 | ✅ PASS | 0.3460 | 0.5938 | 0.5030 |
| regeste_full_text_hybrid_0.5 | 0.5032 | 0.6540 | ✅ PASS | 0.3241 | 0.6012 | 0.6365 |
| regeste_full_text_hybrid_0.7 | 0.5081 | 0.6710 | ✅ PASS | 0.3263 | 0.5989 | 0.6595 |

**All 8 representations PASS both adversarial gates** (LangDom ≤ 0.85, JuristPref > 0.5).

### Full-Corpus Benchmarks (174k scale)

| Benchmark | Best Result | Status | Notes |
|-----------|-------------|--------|-------|
| **Temporal Stability** | 0.78 (full_text_tfidf_light) | ✅ PASS | Neighbor overlap preserved at 80% corpus reduction |
| **Hierarchy Coherence** | nesting ~0.65 | ❌ FAIL | Jurivoc proxy (L0=4 branches, L1=16 legal areas) |
| **Cluster Coherence** | branch_purity ~0.3-0.35 | ❌ FAIL | Language purity ~0.6 dominates |
| **Cross-Language Retrieval** | recall@10 ~0.14 | ❌ FAIL | Below 0.2 threshold |
| **Boilerplate Resistance** | resistance ≈ -0.84 | ❌ FAIL | Proxy measures language dominance, not procedural boilerplate |

### Critical Finding: Two-Mode Tradeoff Confirmed at 174k
- **Citation/Outcome signals** (cited_decisions_tfidf family): Low LangDom (~0.48), High JuristPref (~0.73), Low CiteIndep (~14%)
- **Text signals** (regeste/full_text): Higher LangDom, Lower JuristPref, FAIL citation heritage
- **No single representation dominates all metrics** — product must expose multiple map modes

---

## Deliverable 2: Citation Heritage Benchmark at 174k

### Method
- **Pairs:** 1,020 positive (citing→cited) + 1,020 negative (random non-citing pairs)
- **Source:** 2,019/2,105 citation IDs resolved from 174k corpus
- **Metric:** AUC-ROC on cosine similarity

### Results

| Representation | AUC-ROC | Status |
|----------------|---------|--------|
| cited_decisions_tfidf | **0.7426** | ✅ PASS |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.7290 | ✅ PASS |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.7163 | ✅ PASS (production default) |
| regeste_full_text_hybrid_0.7 | 0.6595 | ✅ PASS |
| full_text_tfidf_light | 0.6257 | ❌ FAIL |
| outcome_tfidf | 0.6262 | ❌ FAIL |
| regeste_full_text_hybrid_0.5 | 0.6365 | ❌ FAIL |
| regeste_tfidf | 0.5030 | ❌ FAIL (~random) |

**Fundamental finding:** Citation-based signals recover citation heritage; text-based signals do not. Production default (cited_decisions_tfidf_outcome_hybrid_0.5) achieves AUC=0.7163.

---

## Deliverable 3: v17b Label Normalization Generalization to 174k

### 1000-Scale (v17b) — REPRODUCED
- **Setup:** 6 representations × 4 seeds (42, 123, 456, 789)
- **Result:** 15-25% hierarchy purity gain (ratios 1.15-1.24), uniform improvement across all reps
- **Evidence Tier:** REPRODUCED

### 174k Generalization Test — NEGATIVE (Different Regime)
- **Setup:** 8 representations, 15k subsample, 213 raw → 111 normalized labels
- **Key difference:** At 1000-scale: 104→54 labels; at 174k: 213→111 labels (4× more fine-grained)
- **Purity ratios:** 4-10× improvement (vs 1.15-1.25× at 1k) — **but NMI decreases** on normalized labels
- **Example (cited_decisions_tfidf):** hierarchy NMI 0.158 → 0.150 (normalized)
- **Conclusion:** v17b method is REPRODUCED but does not "generalize" in same-magnitude sense; 174k fine-grained labels operate in fundamentally different regime requiring separate validation

---

## v18 Coarse Hierarchy Benchmark — NEGATIVE

### Hypothesis (Frozen)
> "The v16 hierarchy_coherence FAIL was a label-granularity artifact: at branch-level (4 labels) the hierarchy IS recoverable with purity ≥ 0.7."

### Results at 1200-Scale (6 representations, branch-level = 4 labels)

| Representation | Branch Purity | Branch NMI | PASS (≥0.70) |
|----------------|---------------|------------|--------------|
| linear_citation_concat | **0.6497** | 0.3005 | ❌ |
| linear_citation_w3070 | 0.6022 | 0.2108 | ❌ |
| linear_citation_ridge | 0.5638 | 0.1556 | ❌ |
| center_projected_64dim | 0.5188 | 0.0648 | ❌ |
| cited_outcome_hybrid_0.5 | 0.4737 | 0.0044 | ❌ |
| linear_hybrid05_concat | 0.4737 | 0.0044 | ❌ |

**Best purity: 0.6497 (linear_citation_concat) < 0.70 threshold.**

### Multi-Seed Verification of v17b — REPRODUCED
- **Seeds:** [42, 123, 456, 789]
- **Stability:** All ratios std < 0.05, means > 1.10
- **center_projected_64dim:** hierarchy_ratio mean=1.208, std=0.014
- **linear_hybrid05_concat:** hierarchy_ratio mean=1.220, std=0.021

---

## Production Default Validated

**PRODUCT_SERVING_DEFAULT = cited_decisions_tfidf_outcome_hybrid_0.5**
- PASS both adversarial gates: LangDom=0.4773, JuristPref=0.7345
- PASS citation heritage: AUC=0.7163
- Operational at full 173,963 decisions with 5 zoom levels
- Wired in product lane as production default

**COMBINATION_MODE = linear_hybrid05_concat** (for hybrid dense+TF-IDF when dense available)
- PASS both gates at 19yr (122k): LangDom=0.7784, JuristPref=0.5395
- Below TF-IDF baseline (0.7235) — scale dependency confirmed

---

## Readiness for New Representations

| Component | Status |
|-----------|--------|
| Formal suite harness (frozen v3) | ✅ Operational |
| Exact k-NN adversarial (HNSW artifact fixed) | ✅ Verified |
| Citation heritage pairs (frozen 1,020 pos/neg) | ✅ Ready |
| v17b normalization pipeline | ✅ Tested & documented |
| v18 coarse hierarchy test | ✅ Validated as negative result |

### Awaiting from Legal-Distance
1. 174k center_projected dense embeddings (768/128/64 dim)
2. Metric learning embeddings (linear/Mahalanobis/hybrid objectives)
3. Citation role embeddings (citing/following/criticizing/neutral)
4. Linear hybrids (linear_hybrid05_concat, linear_citation_concat, etc.) at 174k
5. Section-specific embeddings at full density (sachverhalt/erwaegungen/dispositiv)

---

## Blocker Analysis

**Legal-distance 174k dense embeddings:**
- **ACCEPTED:** 3/26 years (2000-2002, ~19,441 decisions)
- **CHECKPOINTED (pending audit):** 15/26 years (2000-2014, ~100k decisions)
- **NOT PROCESSED:** 11/26 years (2015-2026, ~74k decisions)
- **Fundamental blockers:** Missing parquet for 2019/2025/2026; bge_ ↔ bger_ ID mapping missing; finalize_174k_embeddings.py fails metadata order verification

**Legal-distance recommendation:** FRONTIER_TEAM_REQUIRED for dense embedding data acquisition

---

## Recommendation: PAUSE

The evaluation lane has **fully addressed factory direction v29 question** for available representations. No additional same-question cycles are justified.

**Next_recommendation:** PAUSE — Factory Director to decide successor question when legal-distance delivers 174k dense embeddings, metric learning, citation roles, and linear hybrids.

---

## Evidence References

1. `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` — 8 TF-IDF reps, 12 benchmarks
2. `evaluation/results/174k_citation_heritage/citation_heritage_174k_tfidf_latest.json` — 1,020 citation pairs, 8 reps
3. `evaluation/results/v17b_174k_tfidf/v17b_174k_tfidf_latest.json` — 174k label normalization test
4. `evaluation/results/v17b_174k_generalization/v17b_174k_generalization_20260930_011927.json` — multi-seed reproduction
5. `results/evaluation/v18_coarse_hierarchy/v18_coarse_hierarchy_results.json` — coarse hierarchy + multi-seed
6. `legal-distance/state/legal-distance.json` — upstream blocker status
7. `corpus/state/corpus.json` — corpus provenance

---

## Provenance

All results generated with frozen configurations, preserved raw outputs, and machine-readable state. Negative results preserved as first-class evidence per Research Protocol.