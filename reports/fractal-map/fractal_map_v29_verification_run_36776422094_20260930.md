# Fractal-Map Lane Verification — Factory Direction v29, GitHub Run 36776422094

**Date:** 2026-09-30T21:15:00Z  
**Run ID:** fractal_map_v29_verification_20260930_run_36776422094  
**Status:** BLOCKED_ON_DEPENDENCIES  
**Evidence Tier:** REPRODUCED  
**Continue Recommended:** false  

---

## Executive Summary

The fractal-map lane remains **correctly BLOCKED_ON_DEPENDENCIES** awaiting legal-distance 174k dense embeddings. Only 3/26 years (2000-2002, ~19,441 decisions, 11%) are ACCEPTED; 15/26 years (2000-2014, ~100k decisions) are CHECKPOINTED but PENDING AUDIT; 11/26 years (2015-2026) are not yet processed.

**All 240 verification tests pass (1 skipped).** The complete test suite validates:
- All evidence artifacts exist and are intact
- State file metrics match accepted TF-IDF constrained hierarchical results
- Hierarchical Leiden achieves perfect nesting (1.0) and high purity (0.956) on center_projected 1000-scale baseline
- TF-IDF constrained hierarchical Leiden at 174k: 1/4 modes PASS hierarchical_v1 protocol (regeste_tfidf), 3/4 FAIL on legal_structure_branch
- 12k dense (ACCEPTED 2000-2002): constrained hierarchical Leiden PASSes with adaptive=True (improvement_rate=45.5%, singleton_fraction=0.4%, branch_purity=0.988)
- 28k checkpoint validates scale extrapolation (hier_impr=0.67)
- Alternative hierarchical methods on 174k TF-IDF: ALL FAIL (best fine_branch_purity=0.3989)
- Citation-role embeddings at 1200-scale: 0/15 PASS hierarchical_v1 or v26 zoom-quality with constrained Leiden
- NESTING_METRIC_DEFECT_v1 enforced: 7 compressed-family modes PROHIBITED from nesting≥0.99 claims

**No same-question cycle is justified without upstream ACCEPTED dense embeddings delivery.**

---

## Key Findings (Frozen)

| Finding | Status | Detail |
|---------|--------|--------|
| Flat v26 zoom quality (174k TF-IDF) | **FAIL** | 0/4 modes pass; singleton_fraction >0.99 at res 2.0/3.0; strong branch purity (0.51-0.55 vs 0.25 random) but NO monotonic zoom refinement |
| Constrained hierarchical Leiden 174k TF-IDF (hierarchical_v1) | **1/4 PASS** | Only regeste_tfidf (83k sample) passes all 7 metrics including legal_structure_branch (fine_branch_purity=0.566 > 0.5); 3/4 FAIL on legal_structure_branch (fine_branch_purity ~0.38-0.49 < 0.5) |
| Constrained hierarchical Leiden 174k structural metrics | **ALL 4 modes** | Achieve singleton_fraction=0.0 (min_cluster_size=10), nesting=1.0 (by construction), improvement_rate 57-90%, branch/area purity delta > 0 |
| Constrained hierarchical Leiden 12k dense (ACCEPTED) | **PASS** | Adaptive=True: improvement_rate=45.5%, singleton_fraction=0.4%, nesting=1.0, branch_purity=0.988, area_purity=0.556, legal_structure_branch PASS (0.988 > 0.5) |
| Flat v26 zoom quality at 12k dense | **FAIL** | Only 1/4 transitions exceed 0.5 improvement_rate threshold |
| Scale dependency | **CONFIRMED** | 1k: severe fragmentation; 1.2k: flat v26 PASS (citing_alpha0.7); 12k: flat FAIL/constrained 45.5%; 28k: constrained 67%; 174k TF-IDF: flat FAIL/severe fragmentation |
| Evidence-backed zoom path | **BLOCKED** | citation-role/dense-embedding modes at 1000-scale: citing_alpha0.3 ZQ=0.5401, following_alpha0.3 ZQ=0.5280, criticizing_alpha0.3 ZQ=0.4864; requires 174k dense embeddings to scale |
| Production default | **OPERATIONAL** | cited_outcome_hybrid_0.5 ZQ=0.2798 (flat citation TF-IDF + outcome) |
| Dense 12k adversarial | **FAIL** | language_dominance ~0.98, jurist_preference ~0.04 |
| Adaptive sub-resolution | **DEPRECATED** | HARMS zoom quality at ≥10k scale (improvement_rate capped at 45.5%); DEPRECATED for scales ≥10k per v26 rule |
| NESTING_METRIC_DEFECT_v1 | **ENFORCED** | 7 compressed-family modes PROHIBITED from nesting≥0.99 claims; only 1000-scale and 12k-scale by-construction modes permitted with scope annotation |
| Pipeline readiness 174k dense | **SIMULATION ONLY** | Best validated config: coarse_0.5_fixed2.0_min20 (validated at 12k and 28k); requires ACCEPTED 174k dense embeddings for production |
| Scale extrapolation 174k dense | **HIGH CONFIDENCE** | Power law predicts hierarchical improvement_rate ~0.67 at 174k for dense embeddings; flat zoom predicted ~0.24; 28k validation confirms hier_impr=0.67 |
| 28k checkpoint validation | **PIPELINE VALIDATED** | Constrained hierarchical Leiden on 28k checkpoint dense embeddings (years 2000-2005): fine_singleton=0.0%, fine_median=43-53, improvement_rate=0.67, branch_impr=0.15-0.154, nesting=1.0 |
| Alternative hierarchical methods (174k TF-IDF) | **NEGATIVE** | ALL 7 methods FAIL hierarchical_v1 legal_structure_branch — best fine_branch_purity=0.3989 (local UMAP), 20% below 0.5 threshold |
| Citation-role embeddings (1200, 768-dim) | **NEGATIVE** | 0/15 PASS hierarchical_v1 or v26 zoom-quality with constrained Leiden; ZQ=0.48-0.54 was from DEPRECATED adaptive method |

---

## Blocked Dependencies (Unchanged)

1. **legal-distance 174k dense embeddings**: Only 3/26 years (2000-2002, ~19,441 decisions, 11%) ACCEPTED
2. **citation-role embeddings**: Not available at 174k scale
3. **linear hybrid embeddings**: Not available at 174k scale
4. **Frozen v26 zoom-quality rule**: Cannot be satisfied by TF-IDF flat clustering at 174k scale
5. **section-specific cross-lingual evaluation** (sachverhalt/erwaegungen/dispositiv): Blocked pending dense embeddings

---

## Factory Direction v28 Discrepancy — RESOLVED in v29

**Issue:** factory_direction.json v28 incorrectly claimed "ALL 4 TF-IDF modes PASS the frozen v26 zoom-quality acceptance rule (per_mode_verdict: PASS)" for constrained hierarchical Leiden — this conflated v26 flat rule with hierarchical_v1 protocol.

**Actual Result:** hierarchical_verdict_20260928_193114.json shows 1/4 PASS (regeste_tfidf 83k), 3/4 FAIL on legal_structure_branch.

**Resolution:** Factory direction v29 question text accurately reflects hierarchical_v1 protocol results. Discrepancy recorded in state file with full detail.

---

## Evidence Artifacts Verified

All 42 evidence references in state file confirmed present and loadable:
- Constrained hierarchical Leiden results at 174k (4 TF-IDF modes)
- 12k dense hierarchical Leiden results (ACCEPTED years 2000-2002)
- 28k checkpoint validation results
- Alternative hierarchical methods test results
- Citation-role embeddings evaluation results (15 modes)
- Scale extrapolation model
- Compressed resolution ladder analysis
- Zoom navigation comparison
- Pipeline readiness validations

---

## Test Suite Results

```
240 passed, 1 skipped in 1.66s
```

**Test Classes Verified:**
- `TestArtifactIntegrity` (117 tests): All label arrays, hierarchical results, integration summaries exist and have correct sizes
- `TestHierarchicalLeiden` (5 tests): Best config exists, hierarchical_purity > 0.95, nesting = 1.0, cluster counts valid, parent assignments valid
- `TestMetricConsistency` (9 tests): Evidence tier REPRODUCED, cycle_status BLOCKED_ON_DEPENDENCIES, continue_recommended=false, next_recommendation identifies dense embeddings dependency, TF-IDF not production-ready, blocked dependencies recorded, key findings descriptive, factory direction discrepancy recorded, evidence refs present
- `TestLegacyConcatPreserved` (7 tests): Legacy concat artifacts preserved
- `TestLegalDistanceModes` (6 tests): Citation-role/outcome-hybrid modes in blocked dependencies, evidence-backed zoom path in key findings, 1k results exist, TF-IDF 174k results exist, blocked dependencies match evidence
- `TestCompressedResolutionLadder` (7 tests): Analysis exists, verdict recorded, 100% delta retention, 5-res ladder correct, 28.57% resolution reduction, ≥21 modes evaluated, zoom navigation comparison PASS, identical at shared resolutions
- `TestLegalDistanceScaleReadiness` (6 tests): Parameterized builder exists, honest verdict (REPRODUCIBLE/CONSISTENCY_EXTENSION_NOT_SCALE_READY), source cache committed, provenance reproduced by recompute (purity=1.0), honest zoom comparison recompute (both modes IMPROVED), scale artifacts present and loadable, nesting=1.0 at N=1200
- `test_zoom_quality_174k_eval.py` (4 tests): Frozen spec present, raw purity join coverage full, raw zoom transitions present, verdict FAIL recorded
- `test_zoom_quality_174k_v26_eval.py` (6 tests): v26 frozen spec present, v26 verdict FAIL all modes, baseline pinned, primary reproduces v25 purity, v25 freeze protection intact, census spec and classification, alignment probe corrupted

---

## Recommendation

**BLOCKED** — No additional same-question cycle is justified. The lane has completed all discriminating experiments for the current dependency state. All evidence is preserved, negative results are first-class results, and the state is AUDIT-READY.

**Unblock Condition:** Factory Director must promote legal-distance 174k dense embeddings through audit (at minimum 15/26 years ACCEPTED for 2000-2014) to enable fractal-map pipeline validation at production scale.

---

## Provenance

- **12k dense embeddings (ACCEPTED):** `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/` (years 2000-2002)
- **28k checkpoint embeddings (PENDING AUDIT):** `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/` (years 2000-2005)
- **Citation-alpha embeddings (1200, ACCEPTED):** `/tmp/lex_accepted/evaluation/evaluation/results/v3_citation_roles_frozen/`
- **Metadata 174k:** `/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json` (173,963 entries)
- **Global seed:** 42
- **Leiden seed:** 42
- **k_neighbors:** 15

---

*Generated by fractal-map lane verification cycle for factory direction v29, GitHub run 36776422094.*