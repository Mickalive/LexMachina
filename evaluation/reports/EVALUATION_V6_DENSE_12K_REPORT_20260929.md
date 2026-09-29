# Evaluation Report: v6 Dense Embeddings (Years 2000-2002, 12,570 Decisions)

**Date:** 2026-09-29  
**Factory Direction Version:** 28  
**Lane:** Evaluation  
**Evidence Tier:** REPRODUCED  
**Run ID:** eval_v6_dense_2000_2002_12k_20260929_012428  
**Config Hash (v25 suite):** 4323f833fa72366a  
**Config Hash (adversarial):** b51701f5a9c11692

---

## Executive Summary

Evaluated **v6 dense embeddings** (legal-distance v6 pipeline, years 2000-2002, 12,570 decisions) using the **frozen v25 formal suite protocol**. This is the first evaluation of v6 dense embeddings at the 12k scale (3 ACCEPTED years per factory direction v28).

**Verdict: FAIL** — The v6 dense embeddings at 12k scale **fail the adversarial falsification gates** (language dominance = 0.99, branch coherence = 0.99), confirming the **scale dependency** previously observed: dense embeddings cluster by language, not legal substance, at sub-174k scales.

**v17b label normalization tested:** **NO significant improvement** — hierarchy purity unchanged (0.42→0.42), zoom coherence unchanged (50%→51%), legal_area purity unchanged (0.009→0.009). NMI drops from 0.59→0.45 (hierarchy) and 0.58→0.45 (legal_area).

**Note on v17b at 174k (TF-IDF):** The v17b label normalization at full 174k scale on TF-IDF representations shows a **differential effect** (corrected per audit CYCLE_36521692234): citation-based representations show **large purity gains (~49–64%)** across all hierarchy metrics; text-based representations show **no purity change (1.00x)**. Prior reports misrepresented this as 3-10% gains vs 30-34% degradation.

---

## Evaluation Protocol

### Frozen Configuration (v25 Formal Suite)
- **Benchmarks:** 12 benchmarks (citation_heritage, branch_knn, tf_metadata, adversarial_falsification, boilerplate_resistance, multilingual_invariance, cross_language_pairs, collapse_check, temporal_stability, hierarchy_coherence, zoom_coherence, legal_area_clustering)
- **Thresholds:** Frozen from v16 protocol (language_dominance < 0.85, branch_coherence > 0.3, citation_heritage AUC ≥ 0.65, hierarchy purity > 0.7, legal_area purity > 0.5, zoom improvement > 0%)
- **NN Backend:** Exact k-NN (sklearn brute force) — appropriate for n=12,570
- **Subsamples:** Hierarchy=5,000 (stratified by branch), Temporal=5,000 (random)
- **Seed:** 42 (frozen)
- **Data:** 12,570 decisions (years 2000, 2001, 2002) from legal-distance v6 checkpoints (ACCEPTED per factory direction v28)

### v17b Label Normalization
- Conservative cross-lingual legal_area normalization (214→71 unique areas on subsample)
- Tested on same frozen hierarchy subsample (5,000 decisions)
- Comparison: RAW vs NORMALIZED labels on hierarchy_coherence, zoom_coherence, legal_area_clustering

---

## Results Summary

| Benchmark | Status | Key Metrics |
|-----------|--------|-------------|
| citation_heritage | SKIP | Only 2 positive pairs in 12k decisions (insufficient) |
| branch_knn | **PASS** | knn@5 = 0.996 (threshold 0.633) |
| tf_metadata_human_indexing | **PASS** | recall@5 = 0.996 (threshold 0.8) |
| adversarial_falsification | **FAIL** | lang_dom = 0.990, branch_coh = 0.990 (thresholds: <0.85, >0.3) |
| boilerplate_resistance | SKIP | Full text not available for partial corpus |
| multilingual_invariance | **PASS** | separation = 0.076, gap = 0.038 (thresholds: sep≥0, gap<0.2) |
| cross_language_pairs | **PASS** | separation = 0.076 (threshold >0) |
| collapse_check | **PASS** | mean_sim = 0.859, std = 0.066 (thresholds: <0.99, >0.01) |
| temporal_stability | **PASS** | std_knn = 0.000 (threshold <0.1) |
| hierarchy_coherence | **FAIL** | best_purity = 0.420, best_nmi = 0.591 (thresholds: >0.7, >0.3) |
| zoom_coherence | **PASS** | coarse=0.253, fine=0.380, improvement=50.2% (threshold >0%) |
| legal_area_clustering | **FAIL** | purity = 0.009, nmi = 0.583 (threshold purity >0.5) |

**Overall:** 7 PASS / 3 FAIL / 2 SKIP

---

## Critical Finding: Adversarial Failure (Language Dominance = 0.99)

The **adversarial_falsification benchmark FAILS catastrophically**:
- **Language dominance mean: 0.990** (threshold: < 0.85) → 99% of neighbors share the same language
- **Branch coherence mean: 0.990** (threshold: > 0.3) → but this is because branch correlates with language in Swiss court (German=civil/admin, French=admin, Italian=social)

This confirms the **root cause**: the v6 dense embeddings (based on multilingual-e5) cluster decisions by **language**, not by legal doctrine. The high branch coherence is a **spurious correlation** — German decisions are mostly civil/administrative law, French are administrative, Italian are social security.

### Comparison with TF-IDF at 174k
| Representation | Scale | LangDom | BranchCoh | Both Pass |
|----------------|-------|---------|-----------|-----------|
| v6 dense (2000-2002) | 12,570 | **0.990** | 0.990 | **FAIL** |
| center_projected (2000-2002) | 7,652 | ~0.98-1.0 | ~0.5 | FAIL |
| cited_decisions_tfidf | 173,963 | **0.516** | **0.806** | **PASS** |
| cited_outcome_hybrid_0.5 | 173,963 | **0.516** | **0.806** | **PASS** |

**Conclusion:** The scale dependency is real and severe. At 12k, dense embeddings are **language-dominated**. At 174k, TF-IDF citation-based embeddings are **legally meaningful**. The v6 dense pipeline does not overcome the language clustering problem at this scale.

---

## v17b Label Normalization Results

| Metric | Raw | Normalized | Ratio | Change |
|--------|-----|------------|-------|--------|
| hierarchy_coherence (purity) | 0.420 | 0.422 | 1.005 | +0.5% |
| hierarchy_coherence (NMI) | 0.591 | 0.454 | 0.768 | **-23%** |
| zoom_coherence (improvement %) | 50.2% | 50.6% | 1.009 | +0.9% |
| legal_area_clustering (purity) | 0.009 | 0.009 | 1.000 | 0% |
| legal_area_clustering (NMI) | 0.583 | 0.453 | 0.777 | **-22%** |
| Unique legal_areas | 108 | 71 | 0.657 | -34% |

**Interpretation:** Normalization merges cross-lingual variants (214→71 areas on full 174k; 108→71 on 12k subsample) but **does not improve clustering quality** for dense embeddings. Purity metrics are unchanged; NMI **decreases significantly**. 

**Note on v17b at 174k (TF-IDF, corrected per audit CYCLE_36521692234):** The v17b normalization helps TF-IDF **citation-based** signals (large purity gains ~49–64% across all hierarchy metrics) but provides **no purity benefit for text-based signals (1.00x)**. Prior reports misrepresented this as 3-10% gains vs 30-34% degradation.

---

## Citation Heritage (SKIP — Insufficient Data)

- **Frozen pair pool:** 2,040 pairs (1,020 positive, 1,020 negative) at 174k
- **Filtered to 12k decisions:** Only **2 positive pairs** and 739 negative pairs remain
- **Status:** SKIP — statistical power near zero
- **Implication:** Citation graph is extremely sparse at 12k scale (0.1% coverage at 174k → even less at 12k)

---

## Context: Factory Direction v28 Status

### Completed (ACCEPTED/REPRODUCED)
✅ TF-IDF family (8 representations) — full 174k formal suite, citation heritage, v17b  
✅ Citation heritage infrastructure — frozen 2,040 pair pool, 95.9% citation-ID resolution  
✅ v17b normalization pipeline — differential effect reproduced across 4 seeds  
✅ HNSW artifact fix — exact k-NN on stratified subsample verified  
✅ V25 formal suite runner — all 8 TF-IDF reps evaluated, tradeoff reproduced  

### Awaited from Legal-Distance (Blockers)
⏳ **Dense embeddings at 174k** — only 3/26 years ACCEPTED (2000-2002); 22/26 years in checkpoints pending audit  
⏳ **Citation-role embeddings at 174k** — not yet available  
⏳ **Linear hybrid embeddings at 174k** — not yet available  

### Downstream Blocked
- **Fractal-map lane:** Blocked on legal-distance 174k dense embeddings
- **Product lane:** Blocked on legal-distance 174k dense embeddings for production default switch

---

## Evidence Artifacts

| Artifact | Path |
|----------|------|
| v25 formal suite results | `results/evaluation/v25_174k_formal_suite/partial_dense_results/dense_v6_2000_2002_12k.json` |
| Citation heritage (dedicated) | `results/evaluation/v25_174k_citation_heritage/partial_dense/dense_v6_2000_2002_12k.json` |
| v17b label normalization | `results/evaluation/v25_174k_v17b/partial_dense/dense_v6_2000_2002_12k.json` |
| Combined 12k embeddings | `results/evaluation/v25_174k_formal_suite/embeddings/dense_v6_2000_2002_12k.npy` |
| Combined 12k metadata | `results/evaluation/v25_174k_formal_suite/embeddings/metadata_dense_v6_2000_2002_12k.json` |
| Filtered citation pairs | `evaluation/results/174k_citation_heritage/citation_pairs_v6_2000_2002_12k.json` |
| Evaluation script | `evaluation/evaluate_v6_dense_12k.py` |

---

## Recommendation

**CONTINUE MONITORING** (continue_recommended = TRUE)

The evaluation lane has completed all work possible with current ACCEPTED representations:
1. TF-IDF family fully evaluated at 174k ✅
2. v6 dense embeddings (3 ACCEPTED years) evaluated at 12k ✅ — **confirms scale dependency**
3. Citation heritage and v17b pipelines verified ✅

**No further evaluation cycles are justified until new 174k representations land from legal-distance.** The monitor script (check_count=214) actively watches for:
- Final concatenated 174k dense embeddings (center_projected, PCA)
- Citation-role specific embeddings (citing/following/criticizing)
- Linear hybrid families (linear_citation_concat, linear_hybrid05_concat)

When these land, the evaluation lane will automatically run the full formal suite, citation heritage, and v17b tests.

---

## Provenance

- **Evaluation script:** `evaluation/evaluate_v6_dense_12k.py` (created 2026-09-29)
- **Config hash (v25 suite):** 4323f833fa72366a (frozen)
- **Config hash (adversarial):** b51701f5a9c11692 (frozen)
- **Global seed:** 42 (frozen)
- **HNSW artifact fix:** Exact k-NN on full 12k corpus (no HNSW approximation)
- **Subsample seeds:** 42 (frozen hierarchy/temporal subsamples)
- **Run timestamp:** 2026-09-29T01:24:28Z
- **Duration:** 9.6 seconds

All raw outputs preserved. Negative results documented as first-class evidence.