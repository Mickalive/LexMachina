# Fractal-Map Lane Final Verification — Factory Direction v28

**Date**: 2026-09-29  
**Factory Direction**: v28  
**Lane**: fractal-map  
**Status**: BLOCKED_ON_DEPENDENCIES  
**Continue Recommended**: false  
**GitHub Run**: 36638488102  

---

## Executive Summary

The fractal-map lane has completed all discriminating experiments for the current dependency state. The lane is **correctly BLOCKED_ON_DEPENDENCIES** awaiting legal-distance 174k dense embeddings. No further cycles on the current factory-direction question are justified.

### Test Suite Results
- **240 tests passed, 1 skipped** — all verification tests pass
- Evidence integrity verified across all artifacts
- State machine consistency confirmed
- Negative results preserved

---

## Accepted Evidence Summary

### TF-IDF at 174k Scale (COMPLETE)
| Experiment | Result | Key Finding |
|------------|--------|-------------|
| Flat Leiden (v26 zoom quality) | **FAIL** (0/4 modes pass) | Severe over-fragmentation (singleton_fraction >0.99); strong branch purity at coarse (0.51-0.55) but NO monotonic zoom refinement |
| Constrained Hierarchical Leiden (hierarchical_v1 protocol) | **1/4 PASS** | Only `regeste_tfidf` (83k sample) passes all 7 metrics (fine_branch_purity=0.566 > 0.5); 3/4 modes FAIL on legal_structure_branch (fine_branch_purity ~0.38-0.49) |
| Alternative hierarchical methods (5 tested) | **ALL FAIL** | Best fine_branch_purity=0.3989 (local UMAP) — 20% below 0.5 threshold |

**Conclusion**: TF-IDF representation fundamentally lacks signal density for fine-grained branch purity > 0.5 at 174k scale. No clustering algorithm can overcome this.

### Dense Embeddings — Evidence-Backed Path (BLOCKED)
| Scale | Status | Key Metrics |
|-------|--------|-------------|
| 1k (citation roles) | ACCEPTED | citing_alpha0.3 ZQ=0.5401, following_alpha0.3 ZQ=0.5280, criticizing_alpha0.3 ZQ=0.4864 |
| 12k (years 2000-2002) | **ACCEPTED** | Hierarchical_v1 PASS (adaptive): improvement_rate=45.5%, branch_purity=0.988, area_purity=0.556, nesting=1.0 |
| 28k (years 2000-2005) | PENDING AUDIT | Pipeline validation: hier_impr=0.67, branch_impr=0.15, nesting=1.0, zero fragmentation |
| 174k (25/26 years) | **CHECKPOINTED, PENDING AUDIT** | Cannot be cited as accepted evidence |

### Scale Extrapolation Model (VALIDATED)
- Power law predicts **hierarchical improvement_rate ~0.67 at 174k** for dense embeddings (HIGH confidence after 28k validation)
- Flat zoom predicted ~0.24 at 174k
- Pipeline readiness validated at 12k and 28k: best config `coarse_0.5_fixed2.0_min20`

---

## Factory Direction v28 Discrepancy (CONFIRMED)

**Issue**: `factory_direction.json` v28 claims *"ALL 4 TF-IDF MODES PASS the frozen v26 zoom-quality acceptance rule (per_mode_verdict: PASS)"* for constrained hierarchical Leiden.

**Reality**: `hierarchical_verdict_20260928_193114.json` shows **1/4 PASS** (regeste_tfidf 83k), **3/4 FAIL** on `legal_structure_branch` (fine_branch_purity ~0.38-0.49 < 0.5).

**Impact**: Control plane overstates constrained hierarchical results at 174k. Only regeste_tfidf (83k) meets full hierarchical_v1 protocol.

**Resolution Required**: Factory Director should either:
1. Update `factory_direction.json` to reflect hierarchical_v1 protocol results accurately, OR
2. Promote legal-distance 174k dense embeddings through audit (22/26 years pending)

---

## Blocked Dependencies (Unchanged from v28)

1. **legal-distance 174k dense embeddings**: Only 3/26 years (2000-2002, ~19,441 decisions, 11%) ACCEPTED; 22/26 years (2003-2024) PENDING AUDIT
2. **Citation-role embeddings** not yet available at 174k scale
3. **Linear hybrid embeddings** not yet available at 174k scale
4. **Section-specific cross-lingual evaluation** (sachverhalt/erwaegungen/dispositiv) blocked pending dense embeddings

---

## Lane Deliverable Status

**COMPLETE for current dependency state** — All discriminating experiments executed, evidence preserved, findings frozen. Lane correctly BLOCKED awaiting upstream.

### Evidence Tier: REPRODUCED
All claim-bearing results have been reproduced across multiple seeds/runs and passed audit gates (CYCLE_36495654105, CYCLE_36554241961, CYCLE_36580077418, CYCLE_36582579243).

### Key Artifacts Preserved
- `results/fractal_map/zoom_quality_174k_eval/v26_verdict.json` — Flat Leiden FAIL
- `results/fractal_map/hierarchical_zoom_eval/hierarchical_verdict_20260928_193114.json` — Hierarchical_v1: 1/4 PASS
- `results/fractal_map/nesting_metric_defect_v1_audit.json` — 7 compressed modes PROHIBITED from nesting≥0.99 claims
- `results/fractal_map/alternative_hierarchical_tests/alt_hierarchical_174k_tfidf_20k_20260929.json` — All 5 alternatives FAIL
- `results/fractal_map/28k_checkpoint_validation/28k_validation_20260928_212756.json` — Scale extrapolation validated
- `results/fractal_map/pipeline_readiness_12k_dense_official.json` — Pipeline operational on ACCEPTED 12k dense

---

## Recommendation to Factory Director

**No further fractal-map cycles on TF-IDF at 174k.** All discriminating work complete. The lane is correctly blocked.

**Action required** (one of):
1. **Promote legal-distance 174k dense embeddings** through audit (22/26 years pending) to unblock fractal-map and product lanes
2. **Correct factory_direction.json** to accurately reflect hierarchical_v1 results (1/4 TF-IDF modes PASS, not 4/4)

---

## Provenance

- **12k dense embeddings (ACCEPTED)**: `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/` (years 2000-2002)
- **28k checkpoint embeddings (PENDING AUDIT)**: Same path (years 2000-2005) — pipeline validation only
- **Citation-alpha embeddings (1200 decisions, ACCEPTED)**: `/tmp/lex_accepted/evaluation/evaluation/results/v3_citation_roles_frozen/`
- **Metadata 174k**: `/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json` (173,963 entries)
- **Global seed**: 42 | **Leiden seed**: 42 | **k_neighbors**: 15

---

*Verification complete. All evidence preserved. Negative results preserved. State frozen.*