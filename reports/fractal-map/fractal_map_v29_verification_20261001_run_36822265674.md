# Fractal Map Lane — Verification Run 36822265674 (Factory Direction v29)

## Executive Summary

**Status**: `BLOCKED_ON_DEPENDENCIES` — correctly blocked awaiting legal-distance 174k dense embeddings  
**Evidence Tier**: `REPRODUCED`  
**Continue Recommended**: `false` — no same-question cycle justified without upstream ACCEPTED dense embeddings  
**Test Suite**: 240 passed, 1 skipped (1.76s)  
**Audit Ready**: Yes

---

## Blocker Status Confirmed

The fractal-map lane remains blocked on a **single remaining dependency**: legal-distance 174k dense embeddings.

| Metric | Value |
|--------|-------|
| Years ACCEPTED (2000-2002) | 3/26 (~19,441 decisions, 11%) |
| Years CHECKPOINTED PENDING AUDIT (2000-2018, 2020-2024) | 22/26 |
| Years NOT YET PROCESSED (2019, 2025) | 2/26 |

**Impact**: All discriminating experiments for the current dependency state are complete. No work can proceed without ACCEPTED 174k dense embeddings.

---

## Key Evidence Verified (All Preserved)

### 1. TF-IDF 174k Flat Leiden — FROZEN NEGATIVE (v26 rule)
- **0/4 modes pass** frozen v26 zoom-quality acceptance rule
- Severe over-fragmentation at fine resolutions (median cluster size 1, >99% singletons)
- Strong legal structure at coarse levels (branch purity 0.51-0.55 vs 0.25 random; legal_area purity 0.24-0.31 vs ~0.005 random) but **NO monotonic zoom refinement**

### 2. Constrained Hierarchical Leiden 174k TF-IDF (hierarchical_v1 protocol)
- **1/4 modes PASS**: `regeste_tfidf` (83k sample, fine_branch_purity=0.566 > 0.5)
- **3/4 modes FAIL**: fine_branch_purity ~0.38-0.49 < 0.5 threshold
- All 4 achieve: singleton_fraction=0.0 (min_cluster_size enforcement), nesting=1.0 (by construction), zoom_coherence improvement_rate 57-90%

### 3. Dense 12k ACCEPTED Embeddings (2000-2002) — REPRODUCED EXCELLENT RESULTS
- Constrained hierarchical Leiden: **nesting=1.0, zero fragmentation, branch_purity > 0.97, improvement_rate 0.75-0.80**
- Flat v26 zoom quality: **FAIL** — only 1/4 transitions exceed 0.5 improvement_rate
- **Scale dependency CONFIRMED**: flat works ≥62k, fails below; hierarchical works at ALL scales

### 4. Scale Extrapolation Validated
- **28k checkpoint** (2000-2005, PENDING AUDIT): hier_impr = 0.67
- **19yr checkpoint** (2000-2018, 122k decisions, 70% of 174k, PENDING AUDIT): **ALL 7 hierarchical_v1 checks PASS** (fine_branch_purity=0.993, fine_area_purity=0.811, improvement_rate=1.0)
- Power law model predicts hierarchical improvement_rate ~0.67 at 174k for dense embeddings

### 5. Alternative Hierarchical Methods on 174k TF-IDF — NEGATIVE
- Tested: multi-resolution Leiden, HNSW hierarchical, agglomerative (Ward/average/complete), local UMAP zoom
- **ALL FAIL** hierarchical_v1 legal_structure_branch — best fine_branch_purity=0.3989 (local UMAP), 20% below 0.5 threshold
- **Conclusion**: TF-IDF representation fundamentally lacks signal density for fine-grained branch purity > 0.5 at 174k scale

### 6. Citation-Role Embeddings (768-dim, 1200 decisions) — NEGATIVE
- **0/15 PASS** hierarchical_v1 protocol — all FAIL nesting (0.42-0.70), legal_structure_area (fine_area_purity 0.32-0.36)
- **0/15 PASS** v26 zoom-quality rule — improvement_rate=0.000 at all transitions (min_cluster_size enforcement merges fine clusters)
- ZQ=0.48-0.54 from 1000-scale was achieved with **DEPRECATED adaptive hierarchical Leiden**, not production pipeline
- **Conclusion**: Citation-role embeddings do NOT provide a viable zoom path under current production pipeline; evidence-backed zoom path requires dense embeddings at scale

### 7. NESTING_METRIC_DEFECT_v1 — ENFORCED
- 7 compressed-family modes **PROHIBITED** from nesting≥0.99 claims
- nesting_score=1.0 citeable ONLY for 1000-scale and 12k-scale by-construction modes with scope annotation
- Compressed 5-level ladder NOT universally valid

---

## Pipeline Readiness for 174k Dense Embeddings

| Config | Validation Status |
|--------|-------------------|
| `coarse_0.5_fixed2.0_min20` | Validated at 12k ACCEPTED (6/7 hierarchical_v1 PASS), 28k PENDING AUDIT (hier_impr=0.67), 19yr PENDING AUDIT (7/7 PASS) |
| Production default mode | `center_projected_64dim_hierarchical` (zero-shot TF-IDF hybrid, no GPU required) |

**Operational at simulation level** — requires ACCEPTED 174k dense embeddings for production deployment.

---

## Factory Direction v28 Discrepancy — RESOLVED in v29

| v28 Claim | v29 Correction |
|-----------|----------------|
| "ALL 4 TF-IDF MODES PASS the frozen v26 zoom-quality acceptance rule for constrained hierarchical" | Conflated v26 flat rule with hierarchical_v1 protocol. Actual: 1/4 PASS (regeste_tfidf 83k), 3/4 FAIL on legal_structure_branch |
| "15/26 years (2000-2014, ~100k decisions) checkpointed" | **22/26 years** (2000-2018, 2020-2024) in checkpoints per progress.json, but only 3/26 ACCEPTED; 19/26 PENDING AUDIT |

---

## Test Suite Verification

All 241 tests collected, 240 passed, 1 skipped:
- `test_12k_dense_comprehensive.py`: 9 tests — dense 12k results verified
- `test_dense_embeddings_infrastructure.py`: 12 tests — infrastructure readiness verified
- `test_pipeline_readiness.py`: 15 tests — pipeline operational at simulation level
- `test_scale_dependency.py`: 12 tests — scale dependency finding validated
- `test_verify.py`: 183 tests — all evidence artifacts verified, metric consistency confirmed
- `test_zoom_quality_174k_eval.py`: 5 tests — v25 freeze protection intact
- `test_zoom_quality_174k_v26_eval.py`: 7 tests — v26 frozen negative generalized to full mappable set

---

## Next Recommendation

**No same-question cycle justified.** The lane has:
1. Completed all discriminating experiments for the current dependency state
2. Preserved all evidence (positive and negative)
3. Frozen all claim-bearing results
4. Correctly identified the single blocker (legal-distance 174k dense embeddings)

**Resume condition**: Legal-distance lane delivers ACCEPTED 174k dense embeddings (26/26 years, not just 3/26).

---

## Provenance

| Artifact | Location |
|----------|----------|
| 12k dense embeddings (ACCEPTED) | `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/` (years 2000-2002) |
| 28k/19yr checkpoint embeddings (PENDING AUDIT) | Same path (years 2000-2005, 2000-2018) |
| Citation-alpha embeddings | `/tmp/lex_accepted/evaluation/evaluation/results/v3_citation_roles_frozen/` |
| Metadata 174k | `/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json` (173,963 entries) |
| Global seed | 42 |
| Leiden seed | 42 |
| k-neighbors | 15 |

---

*Verification run: fractal_map_v29_verification_20261001_run_36822265674*  
*Timestamp: 2026-10-01T05:30:00.000000+00:00*  
*Factory direction version: 29*