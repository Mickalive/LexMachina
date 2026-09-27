# Evaluation Lane Cycle Report — Factory Direction v30

**Date:** 2026-09-27  
**Lane:** evaluation  
**Direction Version:** 30  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  
**Evidence Tier:** REPRODUCED  
**Continue Recommended:** false (no additional same-question cycle justified)

---

## Executive Summary

The evaluation lane executed its monitoring and autonomous evaluation protocol per factory direction v30. **No new awaited representations were detected** in the accepted state mounts. The lane remains blocked on legal-distance lane delivery of 174k-scale **transformed dense embeddings** (center_projected, metric-learned, hybrid), citation role embeddings, and linear hybrid embeddings.

**Key status:**
- ✅ TF-IDF family (8 representations): **COMPLETE** at 174k, fully evaluated with v25 formal suite
- ⚠️ Raw multilingual-e5 768-dim embeddings: **16/26 years complete** (2000-2015, ~99k decisions) as year-split checkpoints; partial evaluations show adversarial FAIL (language dominance ~0.98)
- ❌ Transformed dense embeddings at 174k: **NOT YET AVAILABLE** (center_projected_64/128/768dim, linear_metric_epoch4, mahalanobis_metric_epoch4, hybrid_stabilized_epoch1, hybrid_v2_epoch3)
- ❌ Citation role embeddings at 174k: **NOT YET AVAILABLE**
- ❌ Linear hybrid embeddings at 174k: **NOT YET AVAILABLE**

---

## Monitor Execution (Check #138)

**Command:** `python evaluation/monitor_and_evaluate_174k.py`

**Scan Results:**
| Source | Status | Files Found |
|--------|--------|-------------|
| `/tmp/lex_accepted/fractal-map/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings` | TF-IDF complete (already evaluated) | 8 `.npy` files |
| `/tmp/lex_accepted/fractal-map/results/fractal_map/hierarchical_map_174k/tfidf_embeddings` | TF-IDF complete (already evaluated) | 4 `.npy` files |
| `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/` | Year-split checkpoints only (2000-2015) | 16 year files in `checkpoints/` |
| `/tmp/lex_accepted/legal-distance/legal_distance/results/v5/v6/v7/v12` | Sub-174k scale (1,200 decisions) | Multiple `.npy` but NOT 174k |

**No awaited 174k representations detected.** The monitor correctly identifies only the already-evaluated TF-IDF family.

---

## Current Evaluation State (Frozen)

### TF-IDF Family — COMPLETE (8/8 representations)

All 8 production TF-IDF representations evaluated with the **frozen v25 174k formal suite** (12 benchmarks + citation_heritage + v17b label normalization) at full 174k corpus density (173,963 decisions).

| Representation | Suite Pass/Fail/Skip | Citation Heritage AUC | v17b Uniformity |
|----------------|---------------------|----------------------|-----------------|
| `cited_decisions_tfidf` | 4 / 7 / 1 | 0.7892 PASS | PASS |
| `cited_outcome_hybrid_0.5` | 4 / 7 / 1 | 0.7589 PASS | FAIL (NMI -15%) |
| `cited_outcome_hybrid_0.7` | 4 / 7 / 1 | 0.7749 PASS | FAIL (NMI -15%) |
| `full_text_tfidf_light` | 5 / 6 / 1 | 0.8969 PASS | FAIL (NMI -30%) |
| `outcome_tfidf` | 2 / 9 / 1 | 0.6575 PASS (barely) | FAIL (NMI -12%) |
| `regeste_tfidf` | 2 / 9 / 1 | 0.4861 FAIL | PASS |
| `regeste_full_text_hybrid_0.5` | 5 / 6 / 1 | 0.8714 PASS | FAIL (NMI -30%) |
| `regeste_full_text_hybrid_0.7` | 5 / 6 / 1 | 0.8504 PASS | FAIL (NMI -30%) |

**Key Finding (REPRODUCED):** Fundamental two-mode tradeoff persists at 174k:
- **Citation-based** (cited_decisions_tfidf, hybrids): Pass adversarial_falsification (lang_dom ~0.45-0.53, jurist_pref ~0.72-0.80 via EXACT k-NN), pass cross_language_retrieval_full, but fail zero_shot_cross_language_transfer, hierarchy_coherence, cluster_coherence, temporal_stability, boilerplate_resistance
- **Text-based** (full_text_tfidf_light, regeste hybrids): Pass zero_shot_cross_language_transfer, language_specific_representation_quality, cluster_coherence, temporal_stability but FAIL adversarial_falsification (lang_dom=1.0, jurist_pref=0.0) and cross_language_retrieval (recall@10=0.0)

**NO TF-IDF representation passes all benchmarks.** This is a REPRODUCED negative finding.

---

### Raw Multilingual-E5 768-dim — PARTIAL EVALUATION COMPLETE

**Representation:** `multilingual_e5_768dim_partial_2000_2015` (99,325 decisions, years 2000-2015)

| Benchmark Family | Status | Key Metrics |
|------------------|--------|-------------|
| Adversarial (exact k-NN) | **FAIL** | lang_dom=0.9855, jurist_pref=0.0275 |
| Cross-language transfer (zero-shot) | PASS | NMI=0.293 (transfer gap 0.007) |
| Per-language branch quality | PASS | de: 0.386, fr: 0.485, it: 0.461 (mean 0.444) |
| Temporal stability | PASS | mean_overlap=0.785 |
| Hierarchy coherence | FAIL | level_1_nmi=0.454, nesting=0.600 |
| Cluster coherence | FAIL | branch_purity=0.618, language_purity=0.978 |
| Cross-language retrieval (full) | FAIL | recall@10=0.002 |
| Boilerplate resistance | FAIL | boilerplate_rate=0.962, resistance=-0.925 |
| Citation heritage | INSUFFICIENT_PAIRS | Citation graph sources 2020-2024, outside 2000-2015 subset |

**Verdict:** Raw multilingual-e5 embeddings capture legal structure WITHIN each language (cross-language transfer PASS, per-language NMI=0.44) but language artifacts dominate neighbors (language purity 0.98), making cross-language legal navigation impossible. **Requires legal-distance transformations** (center projection, metric learning, citation hybridization) to suppress language artifacts.

---

### Partial Dense Evaluations — HISTORICAL CONTEXT

| Evaluation | Corpus | Result | Note |
|------------|--------|--------|------|
| `center_projected_768dim_partial_2000_2002` (7,652) | 2000-2002 | 8 PASS / 2 FAIL | Promising but small slice |
| `center_projected_768dim_partial_2000_2002` (12,570) | 2000-2002 expanded | **ADVERSARIAL FAIL** | lang_dom=0.98, jurist_pref=0.04; 18.3% metadata coverage, partial center-projection artifacts |

**Critical Finding:** The initially promising 7,652-decision result **does not hold at larger scale** (12,570 decisions). Partial corpus center-projection introduces language artifacts that dominate at scale. This confirms the need for **full-corpus transformed embeddings** from legal-distance.

---

## HNSW Artifact — CONFIRMED AND FIXED FOR ADVERSARIAL

**Issue:** HNSW (M=16, ef_construction=200, ef_search=100, seed=42) produces nearly identical k-NN graphs across different TF-IDF representations at 174k scale, masking true representation differences.

**Evidence:** 
- v3 harness (HNSW on full 174k): all 8 reps show identical jurist_pairwise=0.122, lang_dom ~0.606
- Exact k-NN on fixed stratified subsample (n=2000, seed=42): jurist_pairwise=0.71-0.80, lang_dom=0.43-0.53, differentiated

**Fix Applied:** Adversarial benchmarks (adversarial_language_dominance, jurist_pairwise_preference) now use **exact k-NN on fixed stratified subsample**; HNSW retained for citation_heritage, temporal_stability, hierarchy family, cross_language_retrieval_full, boilerplate (by design for full-corpus scale).

---

## Legal-Distance Dependency Status

**From factory direction v30 (corrected from v29):**
- Dense embedding progress: **16/26 years complete** (2000-2015, ~99,325 decisions, ~57% decision completion)
- Years 2016-2025 remaining
- Transformed representations (center_projected, metric learning, hybrids) at 174k: **PENDING**
- Citation role embeddings at 174k: **PENDING**
- Linear hybrid embeddings at 174k: **PENDING**

**Root Cause:** Legal-distance executes year-split computation on CPU runners with 65-min job ceilings. Transformed representations require full-corpus raw embeddings as input, so they can only be computed after all 26 years of raw embeddings are complete.

---

## Recommendation

**CONTINUE_RECOMMENDED = false**

No additional same-question cycle is justified. The evaluation infrastructure is fully operational (v25 formal suite, citation heritage, v17b normalization, HNSW fix, monitor with enhanced scan paths). The lane is correctly **BLOCKED_ON_DEPENDENCIES** awaiting legal-distance 174k transformed dense embeddings.

**Next Action:** Factory Director should monitor legal-distance progress. When 174k transformed dense embeddings land in accepted state, the evaluation monitor will automatically detect and evaluate them with the frozen v25 formal suite.

---

## Evidence References

1. `evaluation/state/monitor_174k_state.json` — Monitor state (check #138)
2. `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` — TF-IDF suite results
3. `evaluation/results/174k/dense_partial_2000_2015/dense_partial_2000_2015_eval_latest.json` — Raw multilingual-e5 evaluation
4. `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json` — Frozen citation pair pool (137,314 pos/neg)
5. `evaluation/experiments/v25_174k_suite/protocol_v25_174k_suite.json` — Frozen protocol (config hash 4323f833fa72366a)
6. `evaluation/scalable_nn.py` — HNSW/exact k-NN backend (config hash 4047da047fb339c1)
7. `reports/evaluation/EVALUATION_174K_V27_CYCLE_REPORT_20260926_CORRECTED.md` — Audit-corrected prior report

---

## Provenance

- Monitor check: 138 (incremented from 137)
- Last verification: `v57_cycle_report_20260926`
- Frozen config hash (v25 suite): `4323f833fa72366a`
- Frozen config hash (v3 adversarial): `4047da047fb339c1`
- Factory direction version: 30