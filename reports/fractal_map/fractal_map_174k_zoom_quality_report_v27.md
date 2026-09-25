# Fractal Map Lane — 174k Zoom Quality Evaluation Report

**Factory Direction Version:** 27  
**Lane Status:** BLOCKED_ON_DEPENDENCIES  
**Evidence Tier:** REPRODUCED  
**Run ID:** fractal_map_174k_zoom_quality_v26_36035695081  
**Date:** 2026-09-25

---

## Executive Summary

The fractal-map lane remains **BLOCKED** on `legal-distance_174k_dense_embeddings` (single remaining dependency). Corpus metadata (173,963 entries, branch+legal_area 100% coverage) is CLEARED via accepted evaluation state.

**Core finding:** All 4 decision-mappable TF-IDF 174k modes **FAIL** the frozen v26 zoom-quality success rule. TF-IDF modes encode strong legal structure but cannot support monotonic zoom refinement at 174k scale with the current independent-Leiden multi-resolution approach.

---

## Frozen Evaluation Specification (v26)

**Hypothesis:** Among the decision-mappable true-174k TF-IDF builds, at least one representation supports monotonic zoom refinement: branch purity and area purity increase coarse→fine across the compressed 5-level ladder [0.25, 0.5, 1.0, 2.0, 3.0], with zoom improvement_rate > 0.5 on ≥ 2 of 4 transitions.

**Success Rule (per mode):** PASS iff (a) branch purity res_3.0 > res_0.25 AND (b) area purity res_3.0 > res_0.25 AND (c) branch improvement_rate > 0.5 on ≥ 2 of 4 transitions.

**Overall Verdict Rule:** PASS iff ANY mode passes all three per-mode checks.

---

## Results Summary

| Mode | Branch Mono (0.25→3.0) | Area Mono | Rate>0.5 Transitions | Verdict |
|------|------------------------|-----------|----------------------|---------|
| cited_decisions_tfidf_outcome_hybrid_0.5_174k_v25 | ❌ (0.5525→0.5273) | ❌ | 1/4 | FAIL |
| cited_decisions_tfidf_outcome_hybrid_0.7_174k_compressed_v25 | ❌ (0.5491→0.5204) | ❌ | 1/4 | FAIL |
| cited_decisions_tfidf_outcome_hybrid_0.5_174k | ❌ (0.5525→0.5273) | ❌ | 1/4 | FAIL |
| regeste_tfidf_174k | ❌ (0.3452→0.3434) | ✅ | 1/4 | FAIL |

**OVERALL VERDICT: FAIL (0/4 modes PASS)**

---

## Detailed Findings

### 1. Legal Structure is Present but Zoom Refinement Fails

**Branch purity (vs random baseline 0.25):**
- Citation-bearing hybrids: ~0.55 at coarse → ~0.53 at fine (NO monotonic improvement)
- Regeste-only: ~0.34 flat across all resolutions

**Legal area purity (vs random baseline 0.0047):**
- Citation-bearing hybrids: ~0.31 at coarse → ~0.26 at fine (NO monotonic improvement)
- Regeste-only: ~0.08 flat

**Zoom improvement rates (need >0.5 on ≥2 transitions):**
- Best mode (hybrid_0.5): rates = [0.31, 0.48, 0.56, 0.42] → only 1/4 transitions > 0.5
- All modes fail the ≥2 threshold

### 2. Severe Over-Fragmentation at Fine Resolutions

| Mode | res_0.25 | res_0.5 | res_1.0 | res_2.0 | res_3.0 |
|------|----------|---------|---------|---------|---------|
| hybrid_0.5 | 22 clusters (med 663) | 31 (med 508) | 45 (med 401) | **12,902 (med 1.0)** | **64,131 (med 1.0)** |
| hybrid_0.7 | 29 (med 121) | 34 (med 275) | 48 (med 350) | **11,633 (med 1.0)** | **63,281 (med 1.0)** |
| regeste | 142 (med 264) | 166 (med 271) | 202 (med 237) | **21,909 (med 1.0)** | **76,186 (med 1.0)** |

**Singleton fractions:** >99% at res_2.0 and res_3.0 for all modes. The fine ladder is not navigable — users would see ~64k clusters of size 1 at the finest level.

### 3. Honest Nesting Scores (NESTING_METRIC_DEFECT_v1)

Independent Leiden partitions do NOT guarantee hierarchical nesting:

| Mode | 0.25→0.5 | 0.5→1.0 | 1.0→2.0 | 2.0→3.0 |
|------|----------|---------|---------|---------|
| hybrid_0.5 | **0.61** | **0.44** | 0.997 | 0.999 |
| hybrid_0.7 | **0.50** | **0.46** | 0.996 | 0.999 |
| regeste | **0.90** | **0.88** | 0.999 | 1.000 |

**Critical insight:** The legacy `mean_nesting_score=1.0` recorded by compressed builders measured "majority coverage" (fraction of fine clusters with ANY valid parent), not strict nesting. Honest strict nesting at coarse resolutions is **0.44-0.90**, not 1.0.

### 4. Hierarchical Leiden (Zoom Within Clusters) Test

Tested hierarchical Leiden on 174k TF-IDF embeddings (coarse_res=0.5, sub_res=3.0):

- **Cited_decisions_tfidf**: 28 coarse → 89,245 fine clusters (median size 1.0)
- **Strict nesting: 1.0** (by construction)
- **Branch purity: 0.34 → 0.99** (but driven by over-fragmentation)
- **Area purity: 0.09 → 0.99** (but driven by over-fragmentation)
- **Zoom improvement_rate: 100%** (but median cluster size = 1)

**Conclusion:** Hierarchical Leiden guarantees nesting but the sub_res=3.0 is too aggressive for large coarse clusters, producing singleton clusters. The approach needs constrained sub-clustering (min cluster size, adaptive resolution).

### 5. Evidence-Backed Zoom Path: Citation-Role Modes (1000-Scale)

At 1000-scale (accepted evidence from legal-distance v7 fractal validation):

| Mode | Zoom Quality Score | Key Metrics |
|------|-------------------|-------------|
| citing_alpha0.3 | **0.5401** | Best overall |
| following_alpha0.3 | 0.5280 | Strong |
| criticizing_alpha0.3 | 0.4864 | Good |
| outcome_hybrid_0.5 (production default) | 0.2798 | Baseline |

**However:** These citation-role modes also show over-fragmentation at fine resolutions (928 clusters for 1000 decisions at res_3.0). The 174k dense embeddings for citation roles are **not yet available** — blocked on legal-distance lane.

### 6. Citation Signal Probe at 174k

Cited_decisions-bearing hybrids vs regeste-only at 174k:

| Metric | Hybrid_0.5 | Hybrid_0.7 | Regeste |
|--------|-----------|-----------|---------|
| Branch purity (coarse) | 0.5525 | 0.5491 | 0.3452 |
| Branch purity (fine) | 0.5273 | 0.5204 | 0.3434 |
| Δ (fine - coarse) | **-0.025** | **-0.029** | -0.002 |

**Finding:** Citation-bearing modes have higher absolute purity but STILL fail monotonic zoom refinement. The citation signal helps cluster quality but doesn't fix the fundamental over-fragmentation problem at 174k with independent Leiden.

---

## Root Cause Analysis

The current fractal-map architecture uses **independent Leiden clustering at each resolution**. This has three fatal flaws at 174k scale:

1. **No hierarchy guarantee**: Fine clusters can split across multiple coarse parents (strict nesting 0.44-0.61 at coarse transitions)
2. **Resolution ladder mismatch**: Fixed resolution values [0.25, 0.5, 1.0, 2.0, 3.0] don't adapt to data density — coarse resolutions under-cluster, fine resolutions over-cluster
3. **Scale collapse**: At 174k, the fine resolutions (2.0, 3.0) shatter into ~64k singleton clusters because the k-NN graph connectivity doesn't support meaningful substructure at that granularity

---

## Recommendations

### Immediate (Unblocking)
- **WAIT** for legal-distance lane to deliver 174k dense embeddings:
  - `center_projected_768dim`, `center_projected_64dim`
  - `citation_role_citing_alpha0.3`, `citation_role_following_alpha0.3`, `citation_role_criticizing_alpha0.3`
  - `linear_hybrid05_concat`, `linear_metric_epoch4`, `mahalanobis_metric_epoch4`

### When Dense Embeddings Arrive
1. **Test citation-role modes at 174k** with the same frozen v26 success rule
2. **Evaluate hierarchical clustering on dense embeddings** — dense vectors may support better substructure than sparse TF-IDF
3. **Implement constrained hierarchical Leiden**: min_cluster_size parameter, adaptive sub_resolution per coarse cluster
4. **Test multilevel graph methods** (e.g., Leiden with hierarchy, Louvain with recursive partitioning) that build hierarchy by construction

### Architectural (For Next Cycle)
1. **Replace independent Leiden ladder** with hierarchy-by-construction methods (hierarchical Leiden, multilevel graph coarsening, HDBSCAN hierarchy)
2. **Adaptive resolution selection**: choose resolutions per mode based on cluster stability, not fixed ladder
3. **Minimum cluster size enforcement**: prevent singleton clusters in navigation layer
4. **Multi-view zoom**: expose citation-role, legal-issue, reasoning, and outcome views separately (per Master Prompt multi-view requirement)

---

## Accepted Claim Ceiling (Per Audit CYCLE_36027099305)

- ❌ `nesting_score >= 0.99` claims for 7 compressed-family modes **PROHIBITED**
- ✅ `nesting_score = 1.0` citeable ONLY for 1000-scale by-construction modes with scope annotation
- ✅ `outcome_tfidf_174k_compressed nesting=1.0` is genuine (by construction)
- ❌ Compressed 5-level ladder [0.25,0.5,1.0,2.0,3.0] does **NOT** preserve strict nesting universally
- ⚠️ "Compressed ladder NOT universally valid — some modes require the full 7-level ladder" remains in force

---

## Next Steps

**No further same-question cycle justified** — `continue_recommended = false`.

The lane will resume when legal-distance delivers 174k dense embeddings. At that point, the next cycle should:
1. Run frozen v26 success rule on ALL new 174k dense modes
2. Test hierarchical clustering on dense embeddings with constrained sub-clustering
3. Evaluate citation-role zoom quality at 174k (primary product hypothesis)

---

## Evidence References

- `results/fractal_map/zoom_quality_174k_eval/v26_verdict.json` — Complete per-mode results
- `results/fractal_map/zoom_quality_174k_eval/v26_frozen_spec.json` — Frozen-before-compute specification
- `results/fractal_map/evaluation/resume_36014970673_nesting_audit.json` — NESTING_METRIC_DEFECT_v1 audit
- `results/fractal_map/hierarchical_leiden_174k/hierarchical_leiden_174k_results.json` — Hierarchical Leiden experiment
- `results/fractal_map/legal_distance_modes/*/hierarchical_map_results.json` — Per-mode hierarchical results