# Fractal Map Lane — Final Audit-Ready Snapshot (v28)

**Run ID**: `fractal_map_v28_blocked_dense_36472288184`
**Date**: 2026-09-28
**Factory Direction**: v28
**Lane Status**: BLOCKED
**Evidence Tier**: ACCEPTED
**Continue Recommended**: false
**Next Recommendation**: PAUSE

---

## Executive Summary

The fractal-map lane has completed all executable TF-IDF validation work at 174k scale. The lane is **BLOCKED** on the single remaining dependency: **legal-distance 174k dense embeddings** (only 3/26 years ACCEPTED, 23/26 PENDING AUDIT).

**No same-question cycle is justified for TF-IDF**. All frozen evaluation rules have been tested; all TF-IDF modes fail the v26 zoom-quality rule. The evidence-backed zoom path remains citation-role/dense-embedding modes at 1000-scale.

---

## Key Findings

### 1. TF-IDF 174k Flat Zoom (v26 Frozen Rule) — **FAIL** (0/4 modes pass)

| Mode | Branch Purity (res_3.0) | Area Purity (res_3.0) | Singleton Fraction (res_3.0) | Verdict |
|------|------------------------|----------------------|------------------------------|---------|
| `cited_decisions_tfidf_outcome_hybrid_0.5_174k_v25` | 0.5273 | 0.2622 | 0.9985 | FAIL |
| `cited_decisions_tfidf_outcome_hybrid_0.7_174k_compressed_v25` | 0.5204 | 0.2310 | 0.9985 | FAIL |
| `cited_decisions_tfidf_outcome_hybrid_0.5_174k` | — | — | — | FAIL |
| `regeste_tfidf_174k` | — | — | — | FAIL |

**Failure mode**: Severe over-fragmentation at fine resolutions (median cluster size = 1, singleton_fraction > 0.99 at res 2.0 and 3.0). Strong legal structure at coarse resolutions (branch purity 0.51–0.55 vs 0.25 random; area purity 0.24–0.31 vs ~0.005 random) but **NO monotonic zoom refinement** (0/4 modes pass improvement_rate > 0.5 on ≥ 2 of 4 transitions).

**Evidence**: `results/fractal_map/zoom_quality_174k_eval/v26_verdict.json`

---

### 2. Constrained Hierarchical Leiden at 174k (hierarchical_v1 Protocol) — **1/4 modes PASS**

| Mode | Sample | Branch Purity Δ | Area Purity Δ | Improvement Rate | Singleton Fraction | Verdict |
|------|--------|-----------------|---------------|------------------|-------------------|---------|
| `full_text_tfidf_light` | 173,963 | +0.030 | +0.031 | 0.90 | 0.0 | FAIL (branch < 2× random) |
| `regeste_tfidf` | 83,072 | +0.088 | +0.135 | 0.575 | 0.0 | **PASS** |
| `regeste_full_text_hybrid_0.5` | 173,963 | +0.059 | +0.090 | 0.878 | 0.0009 | FAIL (branch < 2× random) |
| `regeste_full_text_hybrid_0.7` | 173,963 | +0.049 | +0.070 | 0.838 | 0.0008 | FAIL (branch < 2× random) |

**All modes achieve nesting = 1.0 BY CONSTRUCTION** (min_cluster_size enforcement), but this is a **construction artifact**, not evidence of meaningful hierarchy.

**Evidence**: `results/fractal_map/hierarchical_zoom_eval/hierarchical_verdict_20260928_193114.json`

---

### 3. Nesting Metric Defect v1 — **Audit Enforcement** (CYCLE_36027099305)

**Finding**: 7 compressed-family modes reported `nesting_score ≥ 0.99` without scope limitation. The `min_cluster_size` parameter enforces `nesting_score = 1.0` regardless of actual hierarchical structure quality.

**Enforcement**:
- `nesting_score ≥ 0.99` claims for compressed-family modes: **PROHIBITED**
- `nesting_score = 1.0` citeable **ONLY** for 1000-scale and 12k-scale by-construction modes with explicit scope annotation
- All nesting claims must include `scope_annotation` field (scale, representation, config)

**Evidence**: `results/fractal_map/nesting_metric_defect_v1_audit.json`

---

### 4. Scale Dependency — **CONFIRMED**

| Scale | Hierarchical Leiden | Flat Zoom (v26) |
|-------|---------------------|-----------------|
| 12k (years 2000–2002) | **WORKS** (improvement_rate=0.80, zero fragmentation, branch_purity 0.979–0.988, singleton_fraction=0.003, nesting=1.0) | **FAILS** |
| 174k | Nesting=1.0 by construction, but FAILS v26 rule (singleton_fraction >0.99) | **FAILS** (0/4 modes pass) |

**Conclusion**: The compressed 5-level ladder is **NOT universally valid**. Hierarchical structure quality degrades with scale for TF-IDF representations.

**Evidence**: 
- `results/fractal_map/12k_dense_hierarchical_test/hierarchical_leiden_results.json`
- `results/fractal_map/constrained_hierarchical_tests/dense_3yr_20260927/constrained_hierarchical_dense_3yr_results.json`

---

### 5. Evidence-Backed Zoom Path — **Citation-Role / Dense Embedding Modes (1000-scale)**

| Mode | Zoom Quality (ZQ) | Improvement Rate | Fine Purity | Hierarchical Advantage | Adversarial Gates |
|------|-------------------|------------------|-------------|------------------------|-------------------|
| `citing_alpha0.3` | **0.5401** | 0.669 | 0.9142 | 0.0110 | LangDom=0.7414, JP=0.5363 ✓ |
| `following_alpha0.3` | **0.5280** | 0.822 | 0.9501 | 0.0700 | LangDom=0.7530, JP=0.5188 ✓ |
| `criticizing_alpha0.3` | **0.4864** | 0.797 | 0.9619 | 0.0815 | LangDom=0.7676, JP=0.5004 ✓ |
| `outcome_hybrid_0.5` (production default) | **0.2798** | 0.868 | 0.8149 | 0.2918 | LangDom=0.4911, JP=0.7990 ✓ |

All 12 representations tested at 1000-scale pass fractal validation. Two design patterns emerge:
- **High-Purity**: metric-learning modes (linear_metric, mahalanobis, hybrid_stabilized)
- **High-Advantage**: citation-bearing modes (cited_decisions_tfidf, cited_outcome hybrids, citation-role modes)

**Evidence**: `results/fractal_map/zoom_coherence_1000scale_citation_roles.json`

---

### 6. Dense Embeddings at 12k — **FAIL Adversarial Tests**

- Hierarchical Leiden pipeline **works** on 12k dense embeddings (improvement_rate=0.36–0.98, singleton_fraction=0.003, nesting=1.0)
- But **flat zoom FAILS** at sub-62k scale
- Adversarial evaluation: `language_dominance ~0.98`, `jurist_preference ~0.04` — **FAIL**

**Evidence**: `results/fractal_map/12k_dense_comprehensive/` (8 result files)

---

### 7. Citation-Role 174k Validation — **BLOCKED**

- `decision_clusters` placeholder-keyed (0 real IDs)
- Row→ID alignment unrecoverable without full corpus JSONL
- Alignment probe: 0.43 agreement vs ~1.0 expected

**Evidence**: Recorded in v26 frozen spec honesty notes

---

## Blocker Summary

| Blocker | Status | Impact |
|---------|--------|--------|
| legal-distance 174k dense embeddings | 3/26 years ACCEPTED (2000–2002), 23/26 PENDING AUDIT | **Primary blocker** — cannot evaluate dense embedding zoom quality at 174k |
| citation-role 174k validation | Placeholder-keyed, alignment unrecoverable | Cannot validate citation-role zoom path at 174k |
| dense embeddings 12k adversarial | LangDom ~0.98, JP ~0.04 — FAIL | Dense embeddings not production-ready even at partial scale |

---

## Orchestration / Validation Failure Diagnosis

### Root Cause Analysis

1. **TF-IDF representations fundamentally cannot support monotonic zoom refinement at 174k scale** — the v26 frozen rule (branch/area monotonic + improvement_rate > 0.5 on ≥2 transitions) correctly captures this. The compressed 5-level ladder is not universally valid.

2. **Constrained hierarchical Leiden achieves nesting=1.0 by construction** (min_cluster_size parameter forces no singletons), but this is a **metric artifact**, not evidence of meaningful hierarchy. The hierarchical_v1 protocol correctly requires `branch_purity > 2× random` which only regeste_tfidf (on 83k subset) satisfies.

3. **Scale dependency is real and confirmed**: The same hierarchical Leiden pipeline that works at 12k (dense embeddings) fails at 174k (TF-IDF). The method is scale-sensitive.

4. **The evidence-backed path requires dense embeddings + citation roles at full scale** — which depends on legal-distance delivering 174k dense embeddings.

### Validation Integrity

- **No frozen rules were weakened**: v26 rule unchanged from v25; hierarchical_v1 protocol frozen before evaluation
- **No results were overwritten**: All negative results preserved as ACCEPTED evidence
- **Provenance maintained**: Every result references frozen specs, census, and metadata
- **Nesting metric defect caught and enforced**: Audit CYCLE_36027099305 prevents misleading nesting claims

---

## Accepted Evidence References

### Primary Validation Results
1. `results/fractal_map/zoom_quality_174k_eval/v26_verdict.json` — v26 flat zoom verdict (0/4 PASS)
2. `results/fractal_map/hierarchical_zoom_eval/hierarchical_verdict_20260928_193114.json` — hierarchical_v1 verdict (1/4 PASS)
3. `results/fractal_map/nesting_metric_defect_v1_audit.json` — nesting metric defect enforcement

### Constrained Hierarchical Tests (174k)
4. `results/fractal_map/constrained_hierarchical_tests/constrained_hierarchical_174k_regeste_20260926.json`
5. `results/fractal_map/constrained_hierarchical_tests/constrained_hierarchical_174k_hybrid05_20260926.json`
6. `results/fractal_map/constrained_hierarchical_tests/constrained_hierarchical_174k_hybrid07_20260926.json`
7. `results/fractal_map/constrained_hierarchical_tests/constrained_hierarchical_174k_full_20260926.json`
8. `results/fractal_map/constrained_hierarchical_tests/constrained_hierarchical_cited_decisions_tfidf_outcome_hybrid_0.5_20260926_171127.json`
9. `results/fractal_map/constrained_hierarchical_tests/constrained_hierarchical_cited_decisions_tfidf_outcome_hybrid_0.7_20260926_171128.json`

### Scale Dependency Evidence
10. `results/fractal_map/12k_dense_hierarchical_test/hierarchical_leiden_results.json`
11. `results/fractal_map/constrained_hierarchical_tests/dense_3yr_20260927/constrained_hierarchical_dense_3yr_results.json`

### Evidence-Backed Zoom Path (1000-scale)
12. `results/fractal_map/zoom_coherence_1000scale_citation_roles.json`

### Dense Embeddings Comprehensive (12k)
13. `results/fractal_map/12k_dense_comprehensive/12k_dense_comprehensive_12570_20260927_221342.json`
14. `results/fractal_map/12k_dense_comprehensive/12k_dense_comprehensive_12570_20260927_221413.json`
15. `results/fractal_map/12k_dense_comprehensive/12k_dense_comprehensive_12570_20260927_221442.json`
16. `results/fractal_map/12k_dense_comprehensive/12k_dense_comprehensive_12570_20260927_221514.json`
17. `results/fractal_map/12k_dense_comprehensive/12k_dense_comprehensive_12570_20260927_221545.json`
18. `results/fractal_map/12k_dense_comprehensive/12k_dense_comprehensive_12570_20260927_231441.json`
19. `results/fractal_map/12k_dense_comprehensive/12k_dense_comprehensive_12570_20260927_231516.json`
20. `results/fractal_map/12k_dense_comprehensive/12k_dense_comprehensive_12570_20260928_051437.json`
21. `results/fractal_map/12k_dense_comprehensive/12k_dense_comprehensive_12570_20260928_051528.json`

### Evaluation Harness
22. `fractal_map/evaluation/center_projected_hierarchical_zoom_validation.py`

---

## Final State

```json
{
  "lane": "fractal-map",
  "direction_version": 28,
  "evidence_tier": "ACCEPTED",
  "cycle_status": "BLOCKED",
  "continue_recommended": false,
  "accepted_run_id": "fractal_map_v28_blocked_dense_36472288184",
  "blockers": [
    "legal-distance 174k dense embeddings (only 3/26 years ACCEPTED, 23/26 PENDING AUDIT)",
    "citation-role 174k validation BLOCKED (decision_clusters placeholder-keyed, row->id alignment unrecoverable)",
    "dense embeddings at 12k FAIL adversarial tests (language_dominance ~0.98, jurist_preference ~0.04)"
  ],
  "next_recommendation": "PAUSE",
  "key_findings": {
    "flat_leiden_174k_v26": { "modes_tested": 4, "modes_passed": 0, "failure_mode": "severe over-fragmentation (singleton_fraction >0.99)", "legal_structure": "strong (branch purity 0.51-0.55 vs 0.25 random)", "zoom_refinement": "NO monotonic zoom refinement (0/4 modes pass)" },
    "constrained_hierarchical_leiden_174k": { "modes_tested": 4, "modes_passed_hierarchical_protocol": 1, "passing_mode": "regeste_tfidf (83k sample)", "failing_modes": ["full_text_tfidf_light", "regeste_full_text_hybrid_0.5", "regeste_full_text_hybrid_0.7"], "failure_reason": "branch_purity < 2x random baseline (0.5)" },
    "scale_dependency": { "finding": "hierarchical Leiden works at 12k (improvement_rate=0.80, zero fragmentation) but flat zoom FAILS at sub-62k scale", "confirmed": true },
    "evidence_backed_zoom_path": { "citation_role_modes_1000": { "citing_alpha0.3": 0.5401, "following_alpha0.3": 0.5280, "criticizing_alpha0.3": 0.4864 }, "production_default": { "outcome_hybrid_0.5": 0.2798 } },
    "nesting_metric_defect_v1": { "enforcement": "nesting_score>=0.99 claims PROHIBITED for 7 compressed-family modes; citeable ONLY for 1000-scale and 12k-scale by-construction modes with scope annotation" }
  }
}
```

---

## Product Implications

1. **TF-IDF modes are NOT suitable for fractal zoom at 174k** — they fail both flat (v26) and hierarchical (hierarchical_v1) zoom-quality rules.

2. **Production default remains `outcome_hybrid_0.5`** (ZQ=0.2798 at 1000-scale) but with caveat: zoom quality unvalidated at 174k.

3. **High-priority path**: Citation-role modes (`citing_alpha0.3`, `following_alpha0.3`, `criticizing_alpha0.3`) show strongest zoom quality (ZQ 0.48–0.54) at 1000-scale and pass adversarial gates. These require 174k dense embeddings + citation role resolution.

4. **No product-readiness claim** while lane is blocked. The fractal map product must either:
   - Wait for legal-distance 174k dense embeddings (audit promotion)
   - Ship with TF-IDF modes at reduced zoom capability (coarse-level only)
   - Expose citation-role modes at 1000-scale as "preview" with scale limitation documented

---

## Audit Verification Checklist

- [x] All frozen specs referenced and unchanged
- [x] All raw outputs preserved (no overwrites)
- [x] Negative results preserved as first-class evidence
- [x] Nesting metric defect audited and enforced
- [x] Scale dependency confirmed with independent evidence
- [x] Evidence-backed zoom path documented with provenance
- [x] Blockers explicitly recorded with evidence
- [x] State file machine-readable with all mandatory fields
- [x] `continue_recommended = false` (no same-question cycle justified)
- [x] `next_recommendation = PAUSE` (factory director decision gate)

---

**Snapshot Status**: AUDIT-READY  
**Prepared by**: Fractal Map Lane (fractal-map researcher)  
**Factory Direction**: v28  
**GitHub Run**: 36474134149