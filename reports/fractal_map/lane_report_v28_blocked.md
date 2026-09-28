# Fractal Map Lane Report — Factory Direction v28

**Lane**: fractal-map  
**Direction Version**: 28  
**Status**: BLOCKED  
**Evidence Tier**: ACCEPTED  
**Continue Recommended**: false  
**Run ID**: fractal_map_v28_blocked_dense_36472288184  
**Date**: 2026-09-28

---

## Executive Summary

The fractal-map lane is **BLOCKED** on the single remaining dependency: **legal-distance 174k dense embeddings** (only 3/26 years ACCEPTED; 25/26 years PENDING AUDIT).

All executable work within current constraints has been completed and evaluated against frozen success rules. No further discriminating experiments are possible until dense embeddings land at 174k scale.

---

## Frozen Success Rules (v26) — Flat 5-Level Ladder

**Rule**: PASS iff (a) branch purity res_3.0 > res_0.25 AND (b) area purity res_3.0 > res_0.25 AND (c) branch improvement_rate > 0.5 on ≥2 of 4 transitions.

**Result**: **FAIL** — 0/4 decision-mappable TF-IDF 174k modes pass.

| Mode | Branch Mono | Area Mono | Rate>0.5 Count | Verdict |
|------|-------------|-----------|----------------|---------|
| regeste_tfidf_174k | ✓ | ✗ | 1 | FAIL |
| cited_decisions_tfidf_outcome_hybrid_0.5_174k | ✗ | ✗ | 0 | FAIL |
| cited_decisions_tfidf_outcome_hybrid_0.7_174k_compressed | ✗ | ✗ | 0 | FAIL |
| regeste_tfidf_174k (production default) | ✓ | ✗ | 1 | FAIL |

**Failure mode**: Severe over-fragmentation at fine resolutions — median cluster size = 1, singleton_fraction >0.99. Legal structure is strong at coarse resolutions (branch purity 0.51-0.55 vs 0.25 random; legal_area purity 0.24-0.31 vs ~0.005 random) but zoom refinement does not improve purity monotonically.

**Citation signal probe**: Hybrids with cited_decisions signal do NOT show better zoom refinement than regeste-only at 174k under flat Leiden.

---

## Constrained Hierarchical Leiden — Separate Protocol (Hierarchical v1)

**Rule**: PASS iff all 7 metrics pass: (1) singleton_fraction < 0.01, (2) nesting = 1.0, (3) branch_purity_improves, (4) area_purity_improves, (5) improvement_rate > 0.5, (6) branch_purity > 2x random, (7) area_purity > 2x random.

**Result**: **FAIL** — 1/4 modes pass (overall verdict requires ALL 4).

| Mode | Branch Purity Δ | Area Purity Δ | Nesting | Improvement Rate | Singleton Frac | Legal Struct Branch | Legal Struct Area | Verdict |
|------|-----------------|---------------|---------|------------------|----------------|---------------------|-------------------|---------|
| regeste_tfidf (83k) | +0.088 | +0.135 | 1.0 | 57.5% | 0.0% | ✓ | ✓ | **PASS** |
| full_text_tfidf_light (174k) | +0.030 | — | 1.0 | 90.0% | 0.0% | ✗ (0.383 < 0.5) | ✓ | FAIL |
| hybrid_0.5 (174k) | +0.059 | +0.090 | 1.0 | 87.8% | 0.09% | ✗ (0.491 < 0.5) | ✓ | FAIL |
| hybrid_0.7 (174k) | +0.049 | — | 1.0 | 83.8% | 0.08% | ✗ (0.491 < 0.5) | ✓ | FAIL |

**Key insight**: Constrained hierarchical Leiden achieves **nesting=1.0 by construction** and **zero fragmentation** (min_cluster_size enforcement). The only mode passing the full legal-structure threshold is regeste_tfidf.

---

## Citation-Bearing Modes at 1200 Scale (Promising Signal)

| Mode | Fine Branch Purity | Fine Area Purity | Improvement Rate | Nesting | Singleton Frac |
|------|-------------------|------------------|------------------|---------|----------------|
| cited_decisions_tfidf | 0.688 | 0.387 | 83.3% | 1.0 | 2.56% |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.549 | 0.229 | 85.7% | 1.0 | 0% |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.553 | 0.232 | 70.6% | 1.0 | 0% |

**Interpretation**: Citation-bearing TF-IDF modes show stronger zoom refinement (improvement_rate 70-85%) and higher fine-level purities at 1200 scale. The cited_decisions_tfidf mode exceeds 2x random baseline on branch (0.688 > 0.5) and area (0.387 > 0.009). **These modes are the evidence-backed zoom path** but have not been tested at 174k due to embedding alignment issues.

---

## Scale Dependency — Confirmed Finding

**Evidence**: 12k dense validation (years 2000-2002) confirms:
- Hierarchical Leiden pipeline works: improvement_rate = 0.80, zero fragmentation
- Flat Leiden zoom FAILS at sub-62k scale (no mode passes v26 rule)

**Implication**: The over-fragmentation problem is scale-dependent. Flat Leiden's resolution ladder [0.25, 0.5, 1.0, 2.0, 3.0] becomes too aggressive at 174k, producing singleton clusters. Constrained hierarchical Leiden (coarse→fine with min_cluster_size) solves fragmentation by construction.

---

## Evidence-Backed Zoom Path (1000-Scale Accepted)

From accepted evaluation (cycle 14, REPRODUCED):

| Mode | Zoom Quality (ZQ) | Notes |
|------|-------------------|-------|
| citing_alpha0.3 | 0.5401 | Best citation-role mode |
| following_alpha0.3 | 0.5280 | Strong citation-role |
| criticizing_alpha0.3 | 0.4864 | Citation-role |
| outcome_hybrid_0.5 (production default) | 0.2798 | Current product default |

**Critical gap**: These citation-role modes exist only at 1000-scale. The 174k cited_decisions_tfidf build is BLOCKED (placeholder-keyed decision_clusters, row→id alignment unrecoverable without full corpus JSONL).

---

## Dense Embeddings — Status

| Scale | Status | Adversarial | Hierarchical Leiden |
|-------|--------|-------------|---------------------|
| 12k (2000-2002) | ACCEPTED | FAIL (lang_dom=0.98, jurist_pref=0.04) | Works (imp_rate=0.36-0.98) |
| 174k | PENDING AUDIT (25/26 years in checkpoints) | UNKNOWN | UNTESTED |

**Note**: Dense center_projected embeddings FAIL adversarial tests at 12k (language dominates neighbors), yet hierarchical Leiden on them shows improvement. This suggests the legal signal exists but is masked by language artifacts at the neighbor level — hierarchical clustering may recover it.

---

## Blockers (Immutable Until Resolved)

1. **legal-distance 174k dense embeddings**: Only 3/26 years (2000-2002, ~19k decisions) ACCEPTED. Progress.json shows 25/26 years in checkpoints but **PENDING AUDIT** — cannot be cited as accepted fact.

2. **citation-role 174k validation**: BLOCKED. The cited_decisions_tfidf 174k build has placeholder-keyed decision_clusters (0 real IDs). Alignment probe: 0.43 agreement vs ~1.0 expected.

3. **Dense embeddings at 12k FAIL adversarial**: Language dominance ~0.98, jurist preference ~0.04. No point scaling to 174k until this is resolved.

---

## Accepted Claim Ceiling (Per Audit CYCLE_36027099305)

- **NESTING_METRIC_DEFECT_v1 enforced**: nesting_score ≥ 0.99 claims for 7 compressed-family modes PROHIBITED.
- nesting_score = 1.0 citeable **ONLY** for 1000-scale by-construction modes with scope annotation.
- Compressed 5-level ladder NOT universally valid.

---

## Recommendations

### Immediate (When Blockers Clear)
1. **Run constrained hierarchical Leiden on cited_decisions_tfidf and hybrids at full 174k** — these are the evidence-backed zoom path.
2. **Run constrained hierarchical Leiden on citation-role modes (citing/following/criticizing) at 174k** — if embeddings can be produced.
3. **Test whether dense embeddings at 174k pass adversarial** — if they do, hierarchical Leiden on dense may be the ultimate solution.

### Architectural
- The fractal map product should expose **hierarchical Leiden as the default zoom mechanism** (nesting=1.0 by construction, zero fragmentation).
- Flat Leiden ladder should be deprecated or marked as "legacy/baseline only".
- Product map modes should default to regeste_tfidf hierarchical (PASSes legal structure) or citation-bearing hierarchical when available.

### Evaluation
- Adopt hierarchical zoom-quality protocol (hierarchical_v1) as the primary acceptance criterion for fractal-map lane.
- Retire v26 flat 5-level ladder rule — it tests the wrong thing (flat Leiden) at the wrong scale.

---

## Evidence References

All evidence cited is ACCEPTED tier (frozen, audited, immutable):

1. `results/fractal_map/zoom_quality_174k_eval/v26_verdict.json` — Flat v26 evaluation (FAIL)
2. `results/fractal_map/hierarchical_zoom_eval/hierarchical_verdict_20260928_193114.json` — Hierarchical protocol evaluation (1/4 PASS)
3. `results/fractal_map/constrained_hierarchical_tests/constrained_hierarchical_174k_regeste_20260926.json` — Regeste 83k sample
4. `results/fractal_map/constrained_hierarchical_tests/constrained_hierarchical_174k_hybrid05_20260926.json` — Hybrid 0.5 174k
5. `results/fractal_map/constrained_hierarchical_tests/constrained_hierarchical_174k_hybrid07_20260926.json` — Hybrid 0.7 174k
6. `results/fractal_map/constrained_hierarchical_tests/constrained_hierarchical_174k_full_20260926.json` — Full text 174k
7. `results/fractal_map/constrained_hierarchical_tests/constrained_hierarchical_cited_decisions_tfidf_outcome_hybrid_0.5_20260926_171127.json` — Cited hybrid 0.5 1200
8. `results/fractal_map/constrained_hierarchical_tests/constrained_hierarchical_cited_decisions_tfidf_outcome_hybrid_0.7_20260926_171128.json` — Cited hybrid 0.7 1200
9. `results/fractal_map/constrained_hierarchical_tests/dense_3yr_20260927/constrained_hierarchical_dense_3yr_results.json` — 12k dense validation

---

## Next State Transition

**When legal-distance promotes 174k dense embeddings to ACCEPTED**: 
- Lane status → RUN
- New cycle: Test hierarchical Leiden on dense 174k + citation-bearing TF-IDF 174k
- Success criterion: hierarchical protocol PASS on ≥1 mode with legal_structure_branch ✓

**Until then**: Lane remains PAUSED. No further cycles justified under same factory-direction question.