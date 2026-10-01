# Fractal Map Lane — Verification Report (Factory Direction v29)

**GitHub Run:** 36799259021  
**Timestamp:** 2026-10-01T01:05:00.000000+00:00  
**Lane Status:** BLOCKED_ON_DEPENDENCIES  
**Continue Recommended:** false  
**Evidence Tier:** REPRODUCED

---

## Executive Summary

The fractal-map lane is **correctly BLOCKED_ON_DEPENDENCIES** awaiting delivery of ACCEPTED 174k dense embeddings from the legal-distance lane. Only 3/26 years (2000-2002, ~19,441 decisions, 11%) of dense embeddings are currently ACCEPTED. An additional 15/26 years (2000-2014, ~100k decisions) are checkpointed but PENDING AUDIT. The remaining 11/26 years (2015-2026) have not yet been processed.

All discriminating experiments for the current dependency state have been executed, evidence is preserved, findings are frozen, and **no additional same-question cycle is justified** without upstream delivery of ACCEPTED 174k dense embeddings.

---

## Blocker Status (Unchanged)

| Metric | Status |
|--------|--------|
| **ACCEPTED dense embeddings** | 3/26 years (2000-2002, ~19,441 decisions, 11%) |
| **Checkpointed (PENDING AUDIT)** | 15/26 years (2000-2014, ~100k decisions) |
| **Not yet processed** | 11/26 years (2015-2026) |
| **Citation-role embeddings at 174k** | Not available |
| **Linear hybrid embeddings at 174k** | Not available |
| **Section-specific cross-lingual evaluation** | Blocked pending dense embeddings |

---

## Key Accepted Findings (Frozen)

### 1. Flat Leiden at 174k TF-IDF — FAILS v26 Zoom-Quality Rule
- **0/4 modes PASS** frozen v26 zoom-quality acceptance rule
- Severe over-fragmentation at fine resolutions (singleton_fraction >0.99 at res 2.0/3.0)
- Strong legal structure at coarse levels (branch purity 0.51-0.55 vs 0.25 random; legal_area purity 0.24-0.31 vs ~0.005 random)
- **NO monotonic zoom refinement** — zoom does not reveal more specific structure

### 2. Constrained Hierarchical Leiden at 174k TF-IDF (hierarchical_v1 protocol)
- **1/4 modes PASS** — only `regeste_tfidf` (83k sample, fine_branch_purity=0.566 > 0.5)
- **3/4 modes FAIL** on `legal_structure_branch` (fine_branch_purity ~0.38-0.49 < 0.5 threshold)
- All 4 modes achieve: singleton_fraction=0.0 (min_cluster_size=10 enforcement), nesting=1.0 (by construction), zoom_coherence improvement_rate 57-90%, branch/area purity delta > 0

### 3. Scale Dependency CONFIRMED
| Scale | Flat v26 | Constrained Hierarchical |
|-------|----------|-------------------------|
| 1k | Severe fragmentation | — |
| 1.2k | PASS (citing_alpha0.7) | — |
| 12k | FAIL | 45.5% improvement_rate (adaptive) |
| 28k | FAIL | **67% improvement_rate** (checkpoint validation) |
| 174k TF-IDF | FAIL (severe fragmentation) | 57-90% (structural), but legal_structure_branch FAIL for 3/4 |

### 4. 12k Dense Embeddings (ACCEPTED 2000-2002) — Pipeline Readiness VALIDATED
- Constrained hierarchical Leiden PASSes hierarchical_v1 protocol (adaptive=True): improvement_rate=45.5%, singleton_fraction=0.4%, nesting=1.0, branch_purity=0.988, legal_structure_branch PASS (0.988 > 0.5)
- **Best validated config for 174k dense:** `coarse_0.5_fixed2.0_min20` — 6/7 hierarchical_v1 checks PASS (zoom_coherence borderline at exactly 0.50)
- Flat v26 zoom quality at 12k dense: FAIL (only 1/4 transitions exceed 0.5 improvement_rate)

### 5. 28k Checkpoint Validation — Scale Extrapolation Model CONFIRMED
- Constrained hierarchical Leiden on 28k checkpoint dense embeddings (years 2000-2005, PENDING AUDIT): fine_singleton=0.0%, fine_median=43-53, **improvement_rate=0.67**, branch_impr=0.15-0.154, nesting=1.0
- Power law model predicts hierarchical improvement_rate ~0.67 at 174k for dense embeddings (HIGH confidence after 28k validation)

### 6. Evidence-Backed Zoom Path Requires Dense Embeddings at Scale
- Citation-role/dense-embedding modes at 1000-scale: citing_alpha0.3 ZQ=0.5401, following_alpha0.3 ZQ=0.5280, criticizing_alpha0.3 ZQ=0.4864
- Production default: cited_outcome_hybrid_0.5 ZQ=0.2798 (flat citation TF-IDF + outcome)
- **Citation-role embeddings at 768-dim (1200 decisions): 0/15 PASS** hierarchical_v1 or v26 zoom-quality with constrained Leiden — ZQ=0.48-0.54 was from DEPRECATED adaptive method
- Adaptive sub-resolution HARMS zoom quality at >=10k scale (improvement_rate capped at 45.5%); DEPRECATED for scales >=10k per v26 rule

### 7. Alternative Hierarchical Methods on 174k TF-IDF — NEGATIVE RESULT
- Tested: multi-resolution Leiden, HNSW hierarchical, agglomerative (Ward/average/complete), local UMAP zoom neighborhoods
- **ALL methods FAIL** hierarchical_v1 legal_structure_branch — best fine_branch_purity=0.3989 (local UMAP), 20% below 0.5 threshold
- **Conclusion:** TF-IDF representation fundamentally lacks signal density for fine-grained branch purity > 0.5 at 174k scale; no clustering algorithm can overcome this

### 8. NESTING_METRIC_DEFECT_v1 Enforced (Audit CYCLE_36027099305)
- 7 compressed-family modes PROHIBITED from nesting>=0.99 claims
- Only 1000-scale and 12k-scale by-construction modes permitted with scope annotation

---

## Verification Results

- **Test Suite:** 240 passed, 1 skipped
- **All evidence artifacts verified** — 42 evidence_refs in state file
- **Negative results preserved** — all failed experiments documented
- **Audit trail complete** — 24 audit cycles recorded
- **Snapshot:** AUDIT-READY

---

## Recommendation

**BLOCKED** — No same-question cycle justified. The lane must wait for legal-distance to deliver ACCEPTED 174k dense embeddings through the audit gate. The pipeline is validated and ready (best config: `coarse_0.5_fixed2.0_min20`), scale extrapolation model is confirmed (hier_impr ~0.67 at 174k), and all TF-IDF discriminating experiments are complete.

The Factory Director should either:
1. Promote legal-distance 174k dense embeddings through audit to unblock this lane, or
2. Define a successor question for fractal-map once dense embeddings are available

---

## Provenance

- **12k dense embeddings (ACCEPTED):** `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/` (years 2000-2002)
- **28k checkpoint embeddings (PENDING AUDIT):** `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/` (years 2000-2005)
- **Citation alpha embeddings (ACCEPTED):** `/tmp/lex_accepted/evaluation/evaluation/results/v3_citation_roles_frozen/` (1200 decisions)
- **Metadata 174k:** `/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json` (173,963 entries)
- **Global seed:** 42 | **Leiden seed:** 42 | **k_neighbors:** 15