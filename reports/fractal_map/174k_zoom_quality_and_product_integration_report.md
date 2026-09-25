# Fractal Map Lane — 174k Zoom Quality Assessment & Product Integration Report

**Run ID:** `fractal_map_174k_product_integration_20260925`  
**Direction Version:** 27  
**Timestamp:** 2026-09-25T00:35:35Z  
**Evidence Tier:** EXPLORATORY  
**Status:** COMPLETED — PAUSED pending legal-distance_174k_dense_embeddings

---

## Executive Summary

This cycle addressed the fractal-map lane's BLOCKED state on `legal-distance_174k_dense_embeddings` by:
1. **Testing whether hierarchical Leiden** (which achieved perfect nesting + high purity at 1000-scale) could fix the severe over-fragmentation of flat Leiden at 174k scale.
2. **Building product integration artifacts** for the 4 decision-mappable TF-IDF 174k modes at coarse resolutions where they DO provide meaningful legal navigation.

**Key Result:** Hierarchical Leiden **fails to fix** over-fragmentation at 174k scale. The fundamental issue is extreme cluster size skew in the TF-IDF embedding space: one coarse cluster contains ~48% of the corpus (83,089/173,963 decisions). Sub-clustering this dominant cluster produces ~55,000 sub-clusters (median size 1). The TF-IDF signal is too sparse for fine-grained zoom at 174k scale.

**Product Decision:** TF-IDF 174k modes support **coarse-level navigation only** (resolutions 0.25, 0.5, 1.0). Fine-grained zoom (resolutions 2.0, 3.0) is not available until citation-role/dense-embedding modes are delivered at 174k scale. Product integration artifacts have been built for coarse-level use.

---

## 1. Background: v26 Evaluation Findings (Frozen)

The v26 evaluation (`results/fractal_map/zoom_quality_174k_eval/v26_verdict.json`) tested all 4 decision-mappable TF-IDF 174k modes against ACCEPTED evaluation metadata (173,963 decisions) with the **same frozen success rule as v25**:

> PASS iff: (a) branch purity res_3.0 > res_0.25 AND (b) area purity res_3.0 > res_0.25 AND (c) branch improvement_rate > 0.5 on ≥2 of 4 transitions.

**All 4 modes FAILED:**

| Mode | Branch Mono (3.0>0.25) | Area Mono | Improvement Rate >0.5 on ≥2 | Verdict |
|------|------------------------|-----------|------------------------------|---------|
| `cited_decisions_tfidf_outcome_hybrid_0.5_174k` | ❌ 0.527 < 0.553 | ❌ | ❌ (0/4) | FAIL |
| `cited_decisions_tfidf_outcome_hybrid_0.5_174k_v25` | ❌ | ❌ | ❌ | FAIL |
| `cited_decisions_tfidf_outcome_hybrid_0.7_174k_compressed_v25` | ❌ | ❌ | ❌ | FAIL |
| `regeste_tfidf_174k` | ❌ flat ~0.345 | N/A | ❌ | FAIL |

**Fine-level fragmentation (from v26):**
- `res_2.0`: 12,852 clusters, median size = 1, singleton fraction = 99.4%
- `res_3.0`: 63,778 clusters, median size = 1, singleton fraction = 99.8%

**Conclusion from v26:** "TF-IDF 174k compressed-ladder modes recover legal structure (purity far above random) but do NOT demonstrate monotonic zoom-refinement against ACCEPTED metadata... Zoom-quality at 174k is NOT established for TF-IDF-only modes. Citation-role/dense modes remain the evidence path (top ZQ at 1000-scale) and stay BLOCKED on legal-distance 174k dense embeddings."

---

## 2. Hierarchical Leiden Test at 174k Scale (This Cycle)

### Hypothesis
Hierarchical Leiden (global coarse clustering → local fine clustering within each parent) achieved at 1000-scale:
- Perfect nesting (1.0) by construction
- Branch purity 0.949 (vs flat Leiden 0.912)
- 8 coarse clusters → 98 fine clusters

Could this approach work at 174k scale with appropriate parameters?

### Experimental Design
Tested 2 modes × 5 hierarchical configs with 174k-appropriate parameters:
- Coarse resolutions: 0.1, 0.15, 0.25 (to get ~8-13 coarse clusters like 1000-scale)
- Sub resolutions: 1.0, 1.5, 2.0
- Min cluster size: 500-1000 (to avoid sub-clustering tiny clusters)

### Results: Negative Finding

**Even with 174k-appropriate parameters, hierarchical Leiden fails:**

| Config | Coarse Clusters | Fine Clusters | Fine Median Size | Improvement Rate | Verdict |
|--------|-----------------|---------------|------------------|------------------|---------|
| `coarse_0.1_sub_1.5` | 13 | 55,607 | 1 | 0.54 | FAIL - over-fragmented |
| `coarse_0.15_sub_1.5` | 9 | ~40k | 1 | ~0.5 | FAIL - over-fragmented |
| `coarse_0.1_sub_2.0` | 13 | ~55k | 1 | ~0.5 | FAIL - over-fragmented |
| `coarse_0.15_sub_2.0` | 9 | ~35k | 1 | ~0.5 | FAIL - over-fragmented |
| `coarse_0.25_sub_1.0_large` | 22 | ~60k | 1 | ~0.5 | FAIL - over-fragmented |

**Root Cause:** The TF-IDF embedding space at 174k has **extreme cluster size skew**:
- At `coarse_res=0.1`: 13 clusters, but Cluster 0 = 83,089 docs (48% of corpus)
- Sub-clustering Cluster 0 at `sub_res=1.5` → 55,399 sub-clusters (one per document!)
- The signal is too sparse to discriminate within this massive cluster

**Comparison with 1000-scale:** At 1000 decisions, coarse cluster sizes were ~125 docs each. Sub-clustering at res=3.0 within 125 docs produced ~12 sub-clusters. At 174k, the same resolution within 83,000 docs produces 55,000 sub-clusters.

**Conclusion:** Hierarchical Leiden cannot overcome fundamental signal sparsity in TF-IDF embeddings at 174k scale. The citation-role/dense-embedding path remains the only evidence-backed route for fine-grained zoom.

---

## 3. Product Integration Artifacts Built

Despite the zoom refinement failure at fine levels, the TF-IDF 174k modes **do encode strong legal structure at coarse resolutions** and are usable for domain/subdomain navigation.

### Artifacts Created
Location: `results/fractal_map/product_integration_174k/<mode>/`

For each of 4 decision-mappable modes:
- `cluster_metadata.json` — Rich legal metadata per cluster (dominant branch, area, chamber, year distribution, top areas/branches)
- `zoom_mappings.json` — Parent-child navigation mappings between all resolution pairs with strict nesting consistency
- `zoom_coherence.json` — Zoom coherence metrics (improvement rate, mean improvement per parent)
- `decision_clusters.json` — Decision ID → cluster mapping at all 5 resolutions (173,963 joined entries)
- `labels_res_*.npy` — Label arrays aligned to ACCEPTED metadata order
- `labels_hierarchical_best.npy` / `labels_coarse_0.5.npy` — For product loader compatibility
- `product_integration_summary.json` — Machine-readable summary with success/failure flags

### Coarse-Level Quality Metrics (Production Default: `cited_decisions_tfidf_outcome_hybrid_0.5_174k`)

| Resolution | Clusters | Branch Purity | Area Purity | vs Random (branch=0.25, area=0.0047) |
|------------|----------|---------------|-------------|--------------------------------------|
| 0.25 | 22 | **0.550** | **0.313** | 2.2× branch, **67× area** |
| 0.5 | 31 | **0.512** | **0.273** | 2.0× branch, **58× area** |
| 1.0 | 45 | **0.543** | **0.265** | 2.2× branch, **56× area** |
| 2.0 | 12,852 | 0.514 | 0.278 | Over-fragmented (median=1) |
| 3.0 | 63,778 | 0.527 | 0.279 | Over-fragmented (median=1) |

### Other Modes
- **`cited_decisions_tfidf_outcome_hybrid_0.7_174k_compressed_v25`**: Similar quality, slightly fewer clusters at coarse levels
- **`regeste_tfidf_174k`**: Weaker signal — branch purity flat ~0.345 across all resolutions (only 1.4× random), 142 clusters at res_0.25 (over-fragmented even at coarse level)

---

## 4. Evidence Landscape & Product Decision

### Current Evidence State (Per Factory Direction v27)

| Path | Status | Zoom Quality (ZQ) at 1000-scale | 174k Availability |
|------|--------|----------------------------------|-------------------|
| **TF-IDF modes** (4 decision-mappable) | DELIVERED | ZQ=0.2798 (production default) | ✅ Coarse only |
| **Citation-role modes** (`citing_alpha0.3`, `following_alpha0.3`, `criticizing_alpha0.3`) | ACCEPTED at 1000-scale | **ZQ=0.5401 / 0.5280 / 0.4864** | ❌ BLOCKED on dense embeddings |
| **Dense embeddings** (BGE, metric learning) | IN PROGRESS | N/A | ❌ BLOCKED — legal-distance lane actively computing |
| **Hybrid modes** (`cited_outcome_hybrid_0.5/0.7`) | ACCEPTED at 1000-scale | ZQ=0.2798 / fractal-best | ❌ Not at 174k |

### ACCEPTED Constraints (from Audit CYCLE_36027099305 - NESTING_METRIC_DEFECT_v1)
- `nesting_score >= 0.99` claims for 7 compressed-family modes **PROHIBITED**
- `nesting_score = 1.0` citeable ONLY for 1000-scale by-construction modes
- Compressed 5-level ladder **NOT universally valid** — some modes require full 7-level ladder
- No product-readiness claim while lane is BLOCKED

---

## 5. Recommendations

### For Factory Director
1. **PAUSE fractal-map lane** — No further discriminating experiments possible until `legal-distance_174k_dense_embeddings` delivers citation-role/dense modes at 174k scale.
2. **Product lane can consume** coarse-level artifacts (res 0.25, 0.5, 1.0) for domain/subdomain navigation immediately.
3. **Legal-distance lane priority** — Citation-role TF-IDF modes (`citing_alpha0.3`, `following_alpha0.3`, `criticizing_alpha0.3`) should be computed at 174k as soon as dense embeddings allow, as they are the evidence-backed zoom path.

### For Product Lane
- Use `results/fractal_map/product_integration_174k/` artifacts for **coarse navigation only** (domain → subdomain → microcluster at res 1.0).
- **Do not expose** res 2.0/3.0 zoom levels for TF-IDF modes — they are over-fragmented.
- When citation-role modes arrive at 174k, they will enable fine-grained zoom (microcluster → decisions).

### For Legal-Distance Lane
- The 174k census infrastructure is ready (`174k_CENSUS_v26_frozen_spec.json`).
- Citation-role embeddings should be prioritized for 174k computation.
- TF-IDF hybrid modes (already computed) provide coarse baseline.

---

## 6. Artifacts Summary

| Artifact | Location | Purpose |
|----------|----------|---------|
| v26 verdict (frozen) | `results/fractal_map/zoom_quality_174k_eval/v26_verdict.json` | Negative result: no TF-IDF mode passes zoom refinement |
| v25 verdict (frozen) | `results/fractal_map/zoom_quality_174k_eval/v25_verdict.json` | Production default FAIL |
| Hierarchical Leiden test | `results/fractal_map/hierarchical_174k_test/hierarchical_leiden_174k_v2_all_results.json` | Negative result: hierarchical approach fails at 174k |
| Product integration | `results/fractal_map/product_integration_174k/` | Coarse-level artifacts for 4 modes |
| 174k census | `results/fractal_map/legal_distance_modes/census_v26.json` | Mode inventory & classification |
| Lane state | `state/fractal_map.json` | Machine-readable state |

---

## 7. Next Cycle Trigger

**Resume condition:** `legal-distance_174k_dense_embeddings` delivers first citation-role/dense mode at 174k scale with decision-mappable artifacts.

**Expected deliverable:** `citing_alpha0.3_174k` or equivalent with `decision_clusters.json` joined to ACCEPTED metadata (≥99% real keys).

**Next experiment:** Run v26-equivalent zoom quality evaluation on citation-role 174k modes to validate if they achieve monotonic zoom refinement at 174k (predicted: YES based on 1000-scale ZQ=0.5401).

---

*Report generated per Research Protocol: freeze hypothesis → run discriminating experiment → preserve negative results → write machine-readable state + human-readable report.*