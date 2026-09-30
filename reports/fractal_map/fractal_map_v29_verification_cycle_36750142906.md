# Fractal-Map Lane — v29 Verification Cycle (GitHub Run 36750142906)

**Run ID:** fractal_map_v29_verification_20260930_cycle_36750142906  
**Timestamp:** 2026-09-30T17:30:00.000000+00:00  
**Factory Direction Version:** 29  
**GitHub Run:** 36750142906  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  
**Continue Recommended:** false  

---

## Executive Summary

The fractal-map lane verification cycle **confirms the lane remains correctly BLOCKED_ON_DEPENDENCIES** awaiting legal-distance 174k dense embeddings. Only 3/26 years (2000-2002, ~19,441 decisions, 11%) are ACCEPTED post-audit. The 19/26 years (2000-2018) in checkpoints include 15/26 years (2000-2014, ~100k decisions) PENDING AUDIT. The 15-year evaluation (center_projected_768dim) FAILs adversarial benchmarks (language_dominance=0.988, jurist_preference=0.0315).

All 239 verification tests pass with 2 skipped. All evidence artifacts are intact and loadable. Negative results are preserved as first-class evidence. Snapshot is AUDIT-READY.

---

## Blocker Status Verification

| Blocker | Status | Detail |
|---------|--------|--------|
| legal-distance 174k dense embeddings | 🔴 BLOCKED | 3/26 years ACCEPTED (2000-2002, ~19,441 decisions, 11%) |
| Checkpoint progress | 🟡 PENDING AUDIT | 19/26 years (2000-2018) in checkpoints; 15/26 years (2000-2014, ~100k) PENDING AUDIT |
| 15-year evaluation (2000-2014) | ❌ FAIL | Adversarial: language_dominance=0.988, jurist_preference=0.0315 |
| Citation-role embeddings 174k | 🔴 BLOCKED | Not available at 174k scale |
| Linear hybrid embeddings 174k | 🔴 BLOCKED | Not available at 174k scale |
| TF-IDF flat v26 zoom-quality | ❌ FAIL | 0/4 modes PASS; severe over-fragmentation |
| Section-specific cross-lingual eval | 🔴 BLOCKED | Pending dense embeddings |

---

## Test Suite Results

- **Total tests:** 239 passed, 2 skipped
- **Duration:** 0.56s
- **All mandatory state fields verified:** lane, direction_version, evidence_tier, cycle_status, continue_recommended, accepted_run_id, evidence_refs, next_recommendation

---

## Evidence Preservation Confirmed

All 41 evidence references in state/fractal-map.json are intact and loadable:

### Key Evidence Categories Preserved:
1. **TF-IDF 174k flat v26 verdict** — 0/4 modes PASS, severe fragmentation
2. **Constrained hierarchical Leiden 174k TF-IDF** — 1/4 PASS (regeste_tfidf), 3/4 FAIL legal_structure_branch
3. **12k dense embeddings hierarchical validation** — PASS hierarchical_v1 protocol
4. **28k checkpoint validation** — hier_impr=0.67, validates scale extrapolation
5. **Citation-role evaluation (1200 decisions, 768-dim)** — 0/15 PASS hierarchical_v1 or v26
6. **Alternative hierarchical methods (174k TF-IDF)** — ALL FAIL legal_structure_branch (best 0.3989)
7. **Scale dependency confirmation** — flat FAILs sub-62k; hierarchical works at all scales
8. **NESTING_METRIC_DEFECT_v1 enforcement** — 7 compressed modes PROHIBITED from nesting≥0.99 claims
9. **Pipeline readiness** — coarse_0.5_fixed2.0_min20 validated at 12k and 28k

---

## Key Findings Reconfirmed

1. **Flat Leiden 174k TF-IDF**: 0/4 modes pass frozen v26 zoom-quality rule; severe over-fragmentation (singleton_fraction >0.99 at res 2.0/3.0); strong branch purity (0.51-0.55 vs 0.25 random) but NO monotonic zoom refinement.

2. **Constrained hierarchical Leiden 174k TF-IDF**: 1/4 modes PASS hierarchical_v1 protocol (regeste_tfidf, fine_branch_purity=0.566>0.5); 3/4 FAIL legal_structure_branch (fine_branch_purity ~0.38-0.49<0.5); ALL 4 achieve singleton_fraction=0.0, nesting=1.0, improvement_rate 57-90%.

3. **Constrained hierarchical Leiden 12k dense (ACCEPTED)**: PASS hierarchical_v1 protocol — improvement_rate=45.5% (adaptive), 75-80% (adaptive_min5), singleton_fraction=0.4%, nesting=1.0, branch_purity=0.988, legal_structure_branch PASS.

4. **Scale dependency CONFIRMED**: 1k severe fragmentation; 1.2k flat v26 PASS; 12k flat FAIL/constrained 45.5%; 28k constrained hier_impr=0.67; 174k TF-IDF flat FAIL/severe fragmentation.

5. **Citation-role embeddings**: 0/15 PASS hierarchical_v1 or v26 with constrained Leiden — ZQ=0.48-0.54 from 1000-scale was DEPRECATED adaptive method, not production pipeline.

6. **Pipeline readiness**: coarse_0.5_fixed2.0_min20 achieves 6/7 hierarchical_v1 checks PASS at 12k; requires ACCEPTED 174k dense embeddings for production.

7. **Scale extrapolation VALIDATED**: Power law predicts hier_impr ~0.67 at 174k for dense embeddings (HIGH confidence after 28k validation).

---

## Audit Trail

- **Audit Gates PASSED:** CYCLE_36495654105, CYCLE_36554241961, CYCLE_36580077418, CYCLE_36582579243, CYCLE_36638488102, CYCLE_36644449527, CYCLE_36655303636, CYCLE_36656873671, CYCLE_36658152353, CYCLE_36660556635, CYCLE_36662646344, CYCLE_36722696246, CYCLE_36728586176, CYCLE_36732295880, **CYCLE_36750142906**
- **Verification Complete:** true
- **All Evidence Preserved:** true
- **Negative Results Preserved:** true

---

## Next Recommendation

**BLOCKED on legal-distance 174k dense embeddings** — only 3/26 years (2000-2002, ~19,441 decisions, 11%) ACCEPTED; 15-year evaluation FAILs adversarial; 28k checkpoint validates scale extrapolation (hier_impr=0.67); pipeline readiness RE-VALIDATED on 12k ACCEPTED dense embeddings.

**continue_recommended: false** — no additional same-question cycle justified; Factory Director must decide successor question when upstream dependency resolves.

---

*This report certifies the fractal-map lane verification is complete for the current dependency state and the snapshot is audit-ready.*