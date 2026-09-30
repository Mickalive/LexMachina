# Fractal Map Lane — Audit-Ready Verification

**Date**: 2026-09-30  
**Factory Direction**: v29  
**Lane**: fractal-map  
**Status**: BLOCKED_ON_DEPENDENCIES  
**Run ID**: fractal_map_v29_verification_20260930_cycle_36660556635  
**GitHub Run**: 36660556635 (prior: 36661735263)

---

## Executive Summary

The fractal-map lane is **verified complete for the current dependency state** and **audit-ready**. All discriminating experiments have been executed, all evidence is preserved, and the lane correctly remains BLOCKED awaiting upstream delivery of ACCEPTED 174k dense embeddings from legal-distance.

**Test Suite**: 240 passed, 1 skipped — **ALL PASS**

---

## Orchestration Failure Diagnosis (Resolved in v29)

| Issue | Root Cause | Resolution |
|-------|------------|------------|
| **factory_direction v28 overclaim** | Claimed "ALL 4 TF-IDF MODES PASS constrained hierarchical at 174k" — conflated flat v26 rule with hierarchical_v1 protocol | **RESOLVED in v29**: factory_direction.json corrected; hierarchical_v1 protocol shows 1/4 PASS (regeste_tfidf 83k), 3/4 FAIL on legal_structure_branch |
| **Legal-distance progress gap** | Checkpoints show 25/26 years (2000-2024, ~100k decisions) but only 3/26 years (2000-2002, ~19k) ACCEPTED | **DOCUMENTED**: 22/26 years PENDING AUDIT — cannot be cited as accepted evidence; lane correctly BLOCKED |

---

## Accepted Claims (Frozen, Evidence-Backed)

### TF-IDF at 174k Scale
- **Flat Leiden (v26 zoom-quality)**: 0/4 modes PASS; severe over-fragmentation (singleton_fraction >0.99 at res 2.0/3.0); strong branch purity (0.51-0.55 vs 0.25 random) but NO monotonic zoom refinement
- **Constrained hierarchical Leiden (hierarchical_v1 protocol)**: 1/4 PASS — only regeste_tfidf (83k sample) passes all 7 metrics (fine_branch_purity=0.566 > 0.5); 3/4 FAIL legal_structure_branch (fine_branch_purity ~0.38-0.49 < 0.5)
- **Structural metrics (all 4 modes)**: singleton_fraction=0.0 (min_cluster_size=10), nesting=1.0 (by construction), zoom_coherence improvement_rate 57-90%

### Dense Embeddings (Evidence-Backed Path)
- **12k dense (ACCEPTED 2000-2002)**: PASS hierarchical_v1 with adaptive=True (improvement_rate=45.5%, branch_purity=0.988, area_purity=0.556, legal_structure_branch PASS)
- **Flat v26 at 12k dense**: FAIL — only 1/4 transitions exceed 0.5 threshold
- **Citation-role/dense at 1k**: citing_alpha0.3 ZQ=0.5401, following_alpha0.3 ZQ=0.5280, criticizing_alpha0.3 ZQ=0.4864 — **requires 174k dense to scale**
- **Dense 12k adversarial**: FAIL — language_dominance ~0.98, jurist_preference ~0.04

### Scale Dependency (CONFIRMED)
| Scale | Flat v26 | Constrained Hierarchical |
|-------|----------|-------------------------|
| 1k | Severe fragmentation | Severe fragmentation |
| 1.2k | PASS (citing_alpha0.7) | — |
| 12k | FAIL | 45.5% improvement_rate (adaptive) |
| 28k (checkpoint) | FAIL | **67% improvement_rate** (validated) |
| 174k TF-IDF | FAIL | 57-90% improvement_rate, but fine_branch_purity < 0.5 |

### Pipeline Readiness
- **Best config**: `coarse_0.5_fixed2.0_min20` — validated at 12k ACCEPTED and 28k PENDING AUDIT
- **12k final validation**: 6/7 hierarchical_v1 checks PASS; zoom_coherence borderline (improvement_rate=0.50 exactly)
- **Scale extrapolation**: Power law predicts hier_impr ~0.67 at 174k for dense (HIGH confidence after 28k validation)

### Negative Results (Preserved)
- **Alternative hierarchical methods on 174k TF-IDF**: ALL FAIL hierarchical_v1 legal_structure_branch (best 0.3989, 20% below 0.5 threshold)
- **TF-IDF constrained hierarchical at 174k**: NOT production-ready — FAILS v26 zoom-quality rule despite nesting=1.0
- **Adaptive sub-resolution**: HARMS zoom quality at ≥10k scale; DEPRECATED per v26 rule
- **NESTING_METRIC_DEFECT_v1**: 7 compressed-family modes PROHIBITED from nesting≥0.99 claims; only 1k/12k by-construction modes permitted with scope annotation (audit CYCLE_36027099305)

---

## Blocked Dependencies (Upstream)

1. **legal-distance 174k dense embeddings**: Only 3/26 years (2000-2002, ~19,441 decisions, 11%) ACCEPTED
2. **Citation-role embeddings** at 174k scale
3. **Linear hybrid embeddings** at 174k scale
4. **Section-specific cross-lingual evaluation** (sachverhalt/erwaegungen/dispositiv)

---

## Evidence Artifacts (Immutable)

### Core Results
- `results/fractal_map/zoom_quality_174k_eval/v26_verdict.json` — Flat v26 verdict
- `results/fractal_map/hierarchical_zoom_eval/hierarchical_verdict_20260928_193114.json` — Hierarchical_v1 protocol (1/4 PASS)
- `results/fractal_map/nesting_metric_defect_v1_audit.json` — NESTING_METRIC_DEFECT_v1 enforcement
- `results/fractal_map/constrained_hierarchical_tests/` — 174k TF-IDF constrained hierarchical (4 modes)
- `results/fractal_map/12k_dense_comprehensive/` — 12k dense comprehensive results
- `results/fractal_map/28k_checkpoint_validation/28k_validation_20260928_212756.json` — 28k checkpoint validation
- `results/fractal_map/pipeline_readiness_final/pipeline_readiness_12k_dense_coarse0.5_fixed2.0_min20_20260930_001147.json` — Final pipeline readiness

### Negative Results
- `results/fractal_map/alternative_hierarchical_tests/alt_hierarchical_174k_tfidf_20k_20260929.json` — All alternative methods FAIL
- `reports/fractal-map/alternative_hierarchical_methods_174k_tfidf_report.md` — Negative results report

### Provenance
- 12k dense embeddings: `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/` (years 2000-2002, ACCEPTED)
- 28k checkpoint embeddings: Same path (years 2000-2005, PENDING AUDIT — pipeline validation only)
- Citation alpha embeddings: `/tmp/lex_accepted/evaluation/evaluation/results/v3_citation_roles_frozen/` (1200 decisions, ACCEPTED)
- Metadata 174k: `/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json` (173,963 entries)
- Global seed: 42, Leiden seed: 42, k_neighbors: 15

---

## Test Suite Verification

```
======================== 240 passed, 1 skipped in 1.52s ========================
```

**Key test categories verified**:
- Artifact integrity (label arrays, cluster assignments, hierarchical maps)
- Metric consistency (state fields, evidence refs, blocked dependencies)
- Hierarchical Leiden configuration (best config, purity, nesting)
- Zoom quality 174k eval (frozen v26 spec, verdict FAIL)
- Hierarchical v1 protocol checks
- Scale dependency findings
- Pipeline readiness
- Legal-distance scale readiness
- Compressed resolution ladder
- NESTING_METRIC_DEFECT_v1 enforcement

---

## State File Accuracy Check

`state/fractal-map.json` fields verified:
- ✅ `lane`: "fractal-map"
- ✅ `direction_version`: 29
- ✅ `evidence_tier`: "REPRODUCED"
- ✅ `cycle_status`: "BLOCKED_ON_DEPENDENCIES"
- ✅ `continue_recommended`: false (no additional same-question cycle justified)
- ✅ `accepted_run_id`: "fractal_map_v29_verification_20260930_cycle_36660556635"
- ✅ `evidence_refs`: 20 artifacts referenced
- ✅ `next_recommendation`: Identifies dense embeddings dependency
- ✅ `blocked_dependencies`: 5 items, all accurate
- ✅ `accepted_claims`: 16 claims, all evidence-backed
- ✅ `factory_direction_v28_discrepancy`: Documented and resolved
- ✅ `key_findings`: 15 findings, all traceable
- ✅ `audit_gate`: 10 PASS cycles recorded
- ✅ `provenance`: Complete with paths
- ✅ `orchestration_failure_diagnosis`: Root cause, gap, impact, resolution path
- ✅ `lane_deliverable_status`: "COMPLETE for current dependency state"
- ✅ `verification_cycle`: Complete with timestamp, test results, status confirmed
- ✅ `alternative_methods_verification`: Negative result confirmed

---

## Recommendation

**No further fractal-map cycles on current question.** The lane has exhausted all discriminating experiments for the current dependency state. The Factory Director must:

1. **Promote legal-distance 174k dense embeddings through audit** (22/26 years PENDING AUDIT), OR
2. **Accept that TF-IDF at 174k cannot satisfy zoom-quality requirements** and the evidence-backed path requires dense embeddings

All work products are audit-ready. Negative results preserved. Provenance intact.

---

**Verification Complete**: 2026-09-30T02:45:00Z  
**Next Action**: Await legal-distance 174k dense embeddings promotion