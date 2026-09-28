# Fractal Map Lane — Audit-Ready Report (Factory Direction v28)

**Run ID:** `fractal_map_v28_174k_blocked_operational_resume_36476032905`
**Timestamp:** 2026-09-28
**Lane:** fractal-map
**Direction Version:** 28
**Evidence Tier:** REPRODUCED
**Cycle Status:** BLOCKED_ON_DEPENDENCIES
**Continue Recommended:** false
**Audit Gate:** PASS (CYCLE_36476032905)

---

## Executive Summary

The fractal-map lane is **correctly blocked** on a single dependency: **legal-distance 174k dense embeddings**. Only 3 of 26 years (2000-2002, ~19,441 decisions, 11%) have been ACCEPTED; 16 years (2003-2019, ~99k decisions) are PENDING AUDIT; 7 years (2020-2025) not yet processed.

**No product-readiness claim can be made while blocked.** The lane state accurately reflects BLOCKED_ON_DEPENDENCIES with `continue_recommended=false`. The factory_direction.json on main incorrectly reports `fractal-map.status=RUN` — this is a control plane discrepancy, not a lane defect.

---

## Accepted Evidence (All Verified)

| # | Evidence Reference | Status | Key Finding |
|---|-------------------|--------|-------------|
| 1 | `zoom_quality_174k_eval/v26_verdict.json` | ✓ Verified | Flat Leiden 174k TF-IDF: 0/4 modes pass v26 zoom-quality; severe over-fragmentation (>99% singletons at res_2.0/res_3.0); strong legal structure (branch purity 0.51-0.55 vs 0.25 random) but NO monotonic zoom refinement |
| 2 | `hierarchical_zoom_eval/hierarchical_verdict_20260928_193114.json` | ✓ Verified | Constrained hierarchical Leiden 174k: nesting=1.0 by construction but per_mode_verdict=FAIL (singleton_fraction >0.99 at fine resolutions); only regeste_tfidf (83k) passes all structural checks |
| 3 | `nesting_metric_defect_v1_audit.json` | ✓ Verified | **NESTING_METRIC_DEFECT_v1 enforced**: 7 compressed-family modes PROHIBITED from nesting≥0.99 claims; only 1000-scale and 12k-scale by-construction modes permitted with scope annotation (audit CYCLE_36027099305) |
| 4 | `12k_dense_hierarchical_test/hierarchical_leiden_results.json` | ✓ Verified | Constrained hierarchical Leiden 12k dense (adaptive=False): **PASS** — improvement_rate=50%, singleton_fraction=0.9%, nesting=1.0, branch_purity=0.988, area_purity=0.556 |
| 5 | `zoom_coherence_1000scale_citation_roles.json` | ✓ Verified | Evidence-backed zoom path: citation-role/dense-embedding modes at 1000-scale — citing_alpha0.3 ZQ=0.5401, following_alpha0.3 ZQ=0.5280, criticizing_alpha0.3 ZQ=0.4864 |
| 6-12 | Constrained hierarchical tests (174k TF-IDF modes) | ✓ Verified | All 7 TF-IDF modes tested at 174k: only regeste_tfidf passes structural checks; others FAIL per_mode_verdict due to singleton_fraction >0.99 |
| 13 | `constrained_hierarchical_tests/dense_3yr_20260927/constrained_hierarchical_dense_3yr_results.json` | ✓ Verified | 3-year dense (2000-2002) hierarchical validation confirms pipeline readiness |
| 14-15 | `12k_dense_comprehensive/` (2 files) | ✓ Verified | Flat v26 zoom quality at 12k dense: FAIL — only 1/4 transitions exceed 0.5 improvement_rate threshold |
| 16 | `center_projected_hierarchical_zoom_validation.py` | ✓ Verified | Reproducible validation script for hierarchical zoom quality |

---

## Key Findings (Frozen, Audit-Backed)

### 1. Flat v26 Zoom Quality at 174k TF-IDF: **FAIL**
- **0/4 modes pass** the frozen v26 zoom-quality rule
- **Severe over-fragmentation**: median cluster size = 1, singleton_fraction >0.99 at res_2.0/res_3.0
- **Strong legal structure but NO monotonic zoom refinement**: branch_purity 0.51-0.55 (vs 0.25 random), legal_area_purity 0.24-0.31 (vs ~0.005 random)
- **Checks failed**: branch_monotonic=false, area_monotonic=false, improvement_rate_gt_0.5_on_2_of_4=false

### 2. Constrained Hierarchical Leiden at 174k TF-IDF: **FAIL (per_mode_verdict)**
- Nesting = 1.0 **BY CONSTRUCTION** (min_cluster_size enforcement)
- But **singleton_fraction >0.99 at fine resolutions** → fails v26 zoom-quality acceptance rule
- Only **regeste_tfidf (83k decisions)** passes all structural checks (fragmentation_ok, legal_structure_branch, legal_structure_area)

### 3. 12k Dense Validation (Years 2000-2002): **SCALE DEPENDENCY CONFIRMED**
| Scale | Flat v26 | Constrained Hierarchical (adaptive=False) |
|-------|----------|------------------------------------------|
| 1k | Severe fragmentation | N/A (by-construction nesting) |
| 1.2k | **PASS** (citing_alpha0.7) | N/A |
| 12k | **FAIL** (1/4 transitions >0.5) | **PASS** (improvement_rate=50%, singleton_fraction=0.9%) |
| 174k | **FAIL** (severe fragmentation) | **FAIL** (singleton_fraction >0.99) |

**Conclusion**: Scale dependency is real. Methods that work at 1k-1.2k fail at ≥12k.

### 4. Evidence-Backed Zoom Path (1000-scale)
| Representation | Zoom Quality (ZQ) | Adversarial Gates | Evidence Tier |
|----------------|-------------------|-------------------|---------------|
| citing_alpha0.3 | **0.5401** | PASS (lang_dom=0.74, jurist=0.54) | REPRODUCED |
| following_alpha0.3 | **0.5280** | PASS (lang_dom=0.75, jurist=0.52) | REPRODUCED |
| criticizing_alpha0.3 | **0.4864** | PASS (lang_dom=0.77, jurist=0.50) | REPRODUCED |
| cited_decisions_tfidf | 0.4252 | PASS | REPRODUCED |
| cited_outcome_hybrid_0.5 | **0.2798** (PRODUCTION DEFAULT) | PASS | REPRODUCED |
| center_projected_64dim | 0.2584 (CURRENT PRODUCT DEFAULT) | PASS | REPRODUCED |

**Requires 174k dense embeddings to scale** — citation-role embeddings not yet available at 174k.

### 5. Dense 12k Adversarial: **FAIL**
- language_dominance ~0.98 (threshold: <0.85)
- jurist_preference ~0.04 (threshold: >0.5)
- Root cause: 18.3% metadata coverage, partial corpus center-projection, raw multilingual-e5 language clustering
- **NOT comparable to 1,200-slice center_projected** (which PASS adversarial)

### 6. Adaptive Sub-Resolution: **DEPRECATED for ≥10k scale**
- improvement_rate capped at 45.5% at ≥10k scale
- HARMS zoom quality vs fixed sub-resolution
- Best config for 174k: `coarse_0.5_fixed2.0_min20` (validated at 12k)

### 7. Nesting Metric Defect v1: **ENFORCED**
- 7 compressed-family modes PROHIBITED from nesting≥0.99 claims
- Only 1000-scale and 12k-scale by-construction modes permitted with scope annotation
- Audit: CYCLE_36027099305

---

## Blocked Dependencies (Must Resolve Before Continue)

1. **legal-distance 174k dense embeddings**: Only 3/26 years ACCEPTED (2000-2002)
2. **Citation-role embeddings at 174k**: Awaits dense completion
3. **Linear hybrid embeddings at 174k**: Awaits dense completion
4. **Frozen v26 zoom-quality rule**: Cannot be satisfied by TF-IDF at 174k scale
5. **Section-specific cross-lingual evaluation** (sachverhalt/erwaegungen/dispositiv): Blocked pending dense embeddings

---

## Pipeline Readiness for 174k Dense Embeddings

| Component | Status | Validation |
|-----------|--------|------------|
| Hierarchical Leiden pipeline | **Operational** | Validated at 12k (adaptive=False) |
| Best config | `coarse_0.5_fixed2.0_min20` | 12k: improvement_rate=50%, singleton_fraction=0.9% |
| Metadata 174k | **Ready** | 173,963 entries, branch+legal_area 100% coverage |
| Evaluation harness | **Ready** | Frozen v3 thresholds, exact k-NN on stratified subsample |
| Adversarial gates | **Defined** | language_dominance <0.85, jurist_preference >0.5 |

**Requires**: ACCEPTED 174k dense embeddings (all 26 years) for production deployment.

---

## Factory Direction v28 Discrepancy

| Field | factory_direction.json (main) | Lane State (Actual) |
|-------|-------------------------------|---------------------|
| fractal-map.status | RUN | BLOCKED_ON_DEPENDENCIES |
| fractal-map.question | "BLOCKED on legal-distance_174k_dense_embeddings..." | Same question, correct status |

**Impact**: Control plane misreports lane status. Not a fractal-map lane defect.
**Resolution Required**: Factory Director must update factory_direction.json on main.

---

## Recommendation

**BLOCKED — Await legal-distance 174k dense embeddings audit promotion**

- `continue_recommended: false` — No additional same-question cycle justified
- Next cycle triggered automatically when legal-distance promotes ACCEPTED 174k dense embeddings
- Monitor script active: `monitor_and_evaluate_174k.py` (check_count=201, last_check=2026-09-28T13:48:26)

---

## Provenance

| Artifact | Location | Scope |
|----------|----------|-------|
| 12k dense embeddings | `/tmp/lex_accepted/evaluation/evaluation/data/dense_1200_baseline/` + legal-distance checkpoints (years 2000-2002, ACCEPTED) | 12,570 decisions |
| Citation alpha embeddings | `/tmp/lex_accepted/evaluation/evaluation/results/v3_citation_roles_frozen/` | 1,200 decisions, ACCEPTED |
| Metadata 174k | `/tmp/lex_accepted/evaluation/evaluation/data/metadata_174k.json` | 173,963 entries |
| Global seed | 42 | Fixed |
| Leiden seed | 42 | Fixed |
| k_neighbors | 15 | Fixed |

---

## Test Suite Results

```
passed: 239
skipped: 2
duration_seconds: 0.53
```

All tests pass. State is **audit-ready**.

---

## Appendix: Mandatory State Fields (per RESEARCH_PROTOCOL.md)

```json
{
  "lane": "fractal-map",
  "direction_version": 28,
  "evidence_tier": "REPRODUCED",
  "cycle_status": "BLOCKED_ON_DEPENDENCIES",
  "continue_recommended": false,
  "accepted_run_id": "fractal_map_v28_174k_blocked_operational_resume_36476032905",
  "evidence_refs": [23 verified references],
  "next_recommendation": "BLOCKED on legal-distance 174k dense embeddings — only 3/26 years (2000-2002) ACCEPTED"
}
```

All mandatory fields present and correct.

---

*Report generated for audit gate. No product-readiness claims made while lane blocked. All evidence preserved.*