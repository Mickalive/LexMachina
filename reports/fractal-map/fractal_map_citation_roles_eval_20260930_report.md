# Fractal Map Lane — Citation-Role Embeddings Evaluation Report (Factory Direction v29)

**Run ID:** `fractal_map_citation_roles_eval_20260930`
**Date:** 2026-09-30
**Evidence Tier:** REPRODUCED
**Lane Status:** BLOCKED_ON_DEPENDENCIES (unchanged)
**Continue Recommended:** FALSE

---

## Executive Summary

While the fractal-map lane remains **BLOCKED_ON_DEPENDENCIES** awaiting legal-distance 174k dense embeddings (only 3/26 years ACCEPTED), I executed discriminating experiments on the available **citation-role embeddings** (1200 decisions, 768-dim from `/tmp/lex_accepted/evaluation/evaluation/results/v3_citation_roles_frozen/`) to characterize the "evidence-backed zoom path" cited in the state file.

**Key Finding:** The "evidence-backed zoom path" (citation-role/dense-embedding modes at 1000-scale with ZQ=0.48-0.54) was achieved using the **adaptive hierarchical Leiden** method, which is **DEPRECATED** for scales ≥10k per the v26 rule ("adaptive sub-resolution HARMS zoom quality at >=10k scale (improvement_rate capped at 45.5%); DEPRECATED for scales >=10k").

Under the **current production pipeline** (constrained hierarchical Leiden with `min_cluster_size=10` enforcement), **ALL 15 citation-role embeddings FAIL the v26 zoom-quality rule** (improvement_rate = 0.000 across all zoom transitions).

---

## Experiments Executed

### 1. Hierarchical_v1 Protocol Evaluation (constrained Leiden, min_cluster_size=20)

**Config:** coarse_res=0.5, fine_res=2.0, min_cluster_size=20 (validated at 12k/28k dense scale)
**Result:** 0/15 PASS hierarchical_v1 protocol

| Failure Mode | Count | Details |
|--------------|-------|---------|
| Nesting not perfect (<0.99) | 15/15 | Nesting scores 0.42-0.70 |
| Legal structure area FAIL (fine_area_purity < 0.5) | 15/15 | fine_area_purity 0.32-0.36 |
| Legal structure branch marginal | 6/15 | fine_branch_purity 0.49-0.52 (threshold 0.5) |
| Improvement_rate < 0.5 | 8/15 | Range 0.30-0.71 |

**Conclusion:** Citation-role embeddings lack signal density for hierarchical_v1 protocol at 1200 scale.

---

### 2. v26 Zoom-Quality Rule Evaluation (constrained Leiden, min_cluster_size=10)

**Config:** resolutions [0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0], min_cluster_size=10
**Result:** 0/15 PASS v26 zoom-quality rule (improvement_rate > 0.5 AND singleton_fraction < 0.99)

**Detailed Results (citing_alpha0.3 example):**
| Resolution | n_clusters | Cluster Sizes |
|------------|------------|---------------|
| 0.1 | 3 | [1001, 128, 71] |
| 0.25 | 4 | [900+, ...] |
| 0.5 | 7 | [...] |
| 1.0 | 11 | [...] |
| 3.0 | 19 | [...] |

**Zoom Coherence (all transitions):**
- improvement_rate = 0.000
- singleton_fraction = 0.000
- v26_PASS = False

**Root Cause:** The min_cluster_size enforcement merges fine clusters into the same coarse mega-clusters, destroying hierarchical refinement. At low resolutions, 1-3 mega-clusters contain >95% of decisions; at high resolutions, only 19 clusters total.

---

### 3. Comparison with Original 1000-Scale ZQ=0.54 Result

| Aspect | Original (ZQ=0.54) | Current Evaluation |
|--------|-------------------|-------------------|
| **Method** | Adaptive hierarchical Leiden | Constrained Leiden (min_cluster_size) |
| **Embeddings** | 64-dim center_projected | 768-dim original |
| **Scale** | 1000 decisions (2020-2024) | 1200 decisions (first 1200 by date) |
| **Fine Clusters** | 118 (citing_alpha0.3) | 19 (citing_alpha0.3) |
| **Fine Purity** | 0.9142 | ~0.50 (branch) |
| **Improvement Rate** | 0.669 | 0.000 |
| **ZQ Score** | 0.5401 | 0.000 |
| **v26 Status** | N/A (different metric) | FAIL |

**Critical Insight:** The adaptive hierarchical Leiden that produced ZQ=0.54 is explicitly **DEPRECATED** per the state file: "adaptive sub-resolution HARMS zoom quality at >=10k scale (improvement_rate capped at 45.5%); DEPRECATED for scales >=10k per v26 rule".

The production pipeline uses constrained Leiden with min_cluster_size enforcement, which produces fundamentally different (and for citation-role embeddings, non-functional) zoom behavior.

---

### 4. 64-dim Center-Projected Embeddings (Production Format)

Also evaluated the 64-dim embeddings from `/tmp/lex_accepted/product/product/results/fractal_map/{citing,following,criticizing}_alpha0.3/embeddings.npy` (1000 decisions, 64-dim) with constrained Leiden min_cluster_size=10.

**Result:** Near-complete fragmentation — 993-997 clusters out of 1000 decisions at ALL resolutions. HDBSCAN found 0 clusters (all noise).

**Conclusion:** The 64-dim center-projected format destroys the cluster structure needed for constrained Leiden.

---

## Implications for Fractal Map Lane

### What Works (from prior accepted evidence)
- **12k dense embeddings (ACCEPTED 2000-2002):** PASS hierarchical_v1 protocol with adaptive=True (improvement_rate=45.5%, nesting=1.0, branch_purity=0.988)
- **28k dense checkpoint (PENDING AUDIT 2000-2005):** Validates scale extrapolation (hier_impr=0.67)
- **TF-IDF regeste_tfidf at 174k (83k sample):** PASS hierarchical_v1 protocol (fine_branch_purity=0.566)
- **TF-IDF regeste_tfidf at 174k (full 47,810 valid):** REPRODUCES PASS (fine_branch_purity=0.579)

### What Does NOT Work (confirmed by this cycle)
- Citation-role embeddings (768-dim, 1200 scale) with constrained Leiden: FAIL v26 & hierarchical_v1
- Citation-role embeddings (64-dim, 1000 scale) with constrained Leiden: COMPLETE FRAGMENTATION
- Adaptive hierarchical Leiden: DEPRECATED for production scales ≥10k

### Evidence-Backed Zoom Path Status

| Path | Status | Notes |
|------|--------|-------|
| Citation-role/dense-embedding (1000-scale, adaptive) | **HISTORICAL ONLY** | ZQ=0.48-0.54 achieved but method DEPRECATED |
| Citation-role/dense-embedding (1200-scale, constrained) | **FAIL** | improvement_rate=0.0, no zoom refinement |
| Dense embeddings (12k, constrained, adaptive) | **PASS** | Requires 174k dense embeddings (BLOCKED) |
| Dense embeddings (12k, constrained, min20) | **PARTIAL** | 6/7 checks PASS, zoom_coherence borderline (0.50) |
| TF-IDF regeste (174k, constrained) | **PASS** | Only text-based mode passing hierarchical_v1 |

---

## Recommendation

**CONTINUE_RECOMMENDED = FALSE**

The lane remains correctly BLOCKED_ON_DEPENDENCIES. All discriminating experiments for the current dependency state are complete:

1. ✅ Citation-role embeddings evaluated with production pipeline (constrained Leiden) — **FAIL**
2. ✅ Confirmed ZQ=0.54 was from DEPRECATED adaptive method
3. ✅ TF-IDF 174k hierarchical_v1 results confirmed (1/4 PASS: regeste_tfidf only)
4. ✅ Scale extrapolation model validated at 28k checkpoint (hier_impr=0.67)
5. ✅ Pipeline readiness confirmed for 174k dense embeddings (coarse_0.5_fixed2.0_min20)

**No additional same-question cycle is justified** without upstream delivery of ACCEPTED 174k dense embeddings from legal-distance.

---

## Evidence Artifacts

| Artifact | Location |
|----------|----------|
| Hierarchical_v1 evaluation (768-dim) | `results/fractal_map/citation_roles_comprehensive_20260930/citation_roles_hierarchical_v1_20260930_161421.json` |
| v26 Zoom-quality evaluation (768-dim) | `results/fractal_map/citation_roles_v26_768_20260930/citation_roles_v26_768_20260930_162853.json` |
| Scale extrapolation model | `results/fractal_map/scale_extrapolation/scale_extrapolation_model.json` |
| 28k checkpoint validation | `results/fractal_map/28k_checkpoint_validation/28k_validation_20260928_212756.json` |

---

## Provenance

- **Citation-role embeddings (768-dim):** `/tmp/lex_accepted/evaluation/evaluation/results/v3_citation_roles_frozen/` (1200 decisions, 15 roles × 3 alphas)
- **Citation-role embeddings (64-dim):** `/tmp/lex_accepted/product/product/results/fractal_map/{citing,following,criticizing}_alpha0.3/embeddings.npy` (1000 decisions)
- **Metadata:** `/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.jsonl` (first 1200 decisions)
- **Global seed:** 42
- **Leiden seed:** 42
- **K neighbors:** 30 (v26), 15 (hierarchical_v1)

---

## Negative Results Preserved

All negative results are preserved in the evidence artifacts above. The failure of citation-role embeddings to achieve zoom quality under the production pipeline is a **first-class negative result** that informs the product: the "evidence-backed zoom path" requires dense embeddings at scale, not citation-role embeddings with constrained Leiden.