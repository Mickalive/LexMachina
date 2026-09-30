# Fractal Map Lane — Audit-Ready Verification (Run 36790229930)

**Factory Direction Version:** 29
**GitHub Run:** 36790229930
**Timestamp:** 2026-09-30T23:20:00.000000+00:00
**Lane Status:** BLOCKED_ON_DEPENDENCIES
**Evidence Tier:** REPRODUCED
**Continue Recommended:** FALSE
**Audit Ready:** TRUE

---

## Executive Summary

This verification confirms the **fractal-map lane deliverable is COMPLETE for the current dependency state**. All discriminating experiments have been executed, evidence preserved, findings frozen. The lane is correctly BLOCKED awaiting upstream legal-distance 174k dense embeddings (only 3/26 years ACCEPTED).

**No same-question cycle is justified** without upstream ACCEPTED dense embeddings delivery.

---

## Orchestration/Validation Failure Diagnosis

### Root Cause (Resolved in v29)

**factory_direction.json v28 incorrectly claimed:** "ALL 4 TF-IDF MODES PASS the frozen v26 zoom-quality acceptance rule (per_mode_verdict: PASS)" for constrained hierarchical Leiden at 174k.

**Actual hierarchical_v1 protocol results:** 1/4 modes PASS (regeste_tfidf 83k sample, fine_branch_purity=0.566 > 0.5); 3/4 modes FAIL on legal_structure_branch (fine_branch_purity ~0.38-0.49 < 0.5 threshold).

### Legal-Distance Progress Gap

- **Progress.json checkpoints:** 15/26 years (2000-2014, ~100k decisions) — PENDING AUDIT
- **ACCEPTED dense embeddings:** 3/26 years (2000-2002, ~19,441 decisions, 11%) — ONLY these count as evidence
- **Not yet processed:** 11/26 years (2015-2026)

**Impact:** Fractal-map lane correctly BLOCKED_ON_DEPENDENCIES; no work can proceed without ACCEPTED 174k dense embeddings.

### Resolution Status

**RESOLVED in factory_direction.json v29** — discrepancy acknowledged and corrected; v29 question text accurately reflects 1/4 PASS on hierarchical_v1 protocol.

---

## Verification Results

### Test Suite
- **240 passed, 1 skipped** — full test suite verification
- All evidence artifacts verified
- Status reconfirmed: BLOCKED_ON_DEPENDENCIES
- Continue recommended: FALSE

### Evidence Preservation
- ✅ All positive results preserved
- ✅ All negative results preserved (critical for anti-noise principle)
- ✅ Provenance chains intact for every claim
- ✅ No claim-bearing outputs overwritten

### Key Accepted Claims (Frozen)

| Claim | Status | Evidence |
|-------|--------|----------|
| Flat Leiden 174k TF-IDF: 0/4 modes pass v26 zoom-quality rule | ACCEPTED | `v26_verdict.json` |
| Constrained hierarchical Leiden 174k TF-IDF (hierarchical_v1): 1/4 PASS | ACCEPTED | `hierarchical_verdict_20260928_193114.json` |
| Constrained hierarchical Leiden 174k TF-IDF structural: all 4 achieve singleton_fraction=0.0, nesting=1.0, improvement_rate 57-90% | ACCEPTED | 4 constrained hierarchical test artifacts |
| Constrained hierarchical Leiden 12k dense (ACCEPTED embeddings): PASS hierarchical_v1 | ACCEPTED | `12k_dense_hierarchical_test/hierarchical_leiden_results.json` |
| Flat v26 zoom quality at 12k dense: FAIL | ACCEPTED | `zoom_quality_174k_eval` artifacts |
| Scale dependency CONFIRMED: 1k severe fragmentation → 1.2k flat PASS → 12k flat FAIL/constrained 45.5% → 28k hier_impr=0.67 → 174k TF-IDF flat FAIL | ACCEPTED | Multiple scale validation artifacts |
| Evidence-backed zoom path: citation-role/dense at 1000-scale (ZQ=0.48-0.54) requires 174k dense to scale | ACCEPTED | `zoom_coherence_1000scale_citation_roles.json` |
| NESTING_METRIC_DEFECT_v1 enforced: 7 compressed modes PROHIBITED from nesting≥0.99 claims | ACCEPTED | `nesting_metric_defect_v1_audit.json` |
| Pipeline readiness for 174k dense: operational at simulation; best config coarse_0.5_fixed2.0_min20 | ACCEPTED | `pipeline_readiness_final/` artifacts |
| Scale extrapolation model VALIDATED: power law predicts hier_impr~0.67 at 174k (confirmed at 28k) | ACCEPTED | `scale_extrapolation/scale_extrapolation_model.json` |
| Alternative hierarchical methods on 174k TF-IDF: NEGATIVE (best fine_branch_purity=0.3989) | ACCEPTED | `alternative_hierarchical_tests/alt_hierarchical_174k_tfidf_20k_20260929.json` |
| Citation-role embeddings (768-dim, 1200 decisions): 0/15 PASS hierarchical_v1 or v26 | ACCEPTED | `citation_roles_comprehensive_20260930/`, `citation_roles_v26_768_20260930/` |

---

## Blocked Dependencies (Unchanged)

1. **legal-distance 174k dense embeddings**: Only 3/26 years ACCEPTED (2000-2002)
2. **citation-role embeddings**: Not available at 174k scale
3. **linear hybrid embeddings**: Not available at 174k scale
4. **v26 zoom-quality rule**: Cannot be satisfied by TF-IDF flat clustering at 174k
5. **section-specific cross-lingual evaluation**: Blocked pending dense embeddings

---

## Negative Results Preserved (First-Class Evidence)

- ✅ Flat Leiden at 174k: >99% singletons at fine resolutions
- ✅ 3/4 TF-IDF modes FAIL hierarchical_v1 legal_structure_branch at 174k
- ✅ 12k dense flat v26 zoom quality: FAIL
- ✅ 15-year dense evaluation: FAIL adversarial (language_dominance=0.988, jurist_preference=0.0315)
- ✅ Alternative hierarchical methods: ALL FAIL on 174k TF-IDF
- ✅ Citation-role embeddings (768-dim): 0/15 PASS with constrained Leiden
- ✅ v18 coarse hierarchy: NEGATIVE (max purity 0.65 < 0.7 threshold)

---

## Lane Deliverable Status

**COMPLETE for current dependency state**

All discriminating experiments executed:
- ✅ TF-IDF 174k flat Leiden evaluation (v26 rule)
- ✅ TF-IDF 174k constrained hierarchical Leiden (hierarchical_v1 protocol)
- ✅ TF-IDF 174k alternative hierarchical methods (HNSW, agglomerative, local UMAP)
- ✅ 12k dense embeddings constrained hierarchical (REPRODUCED with excellent results)
- ✅ 28k checkpoint dense embeddings validation (scale extrapolation confirmed)
- ✅ Citation-role embeddings evaluation (768-dim, 1200 decisions)
- ✅ Pipeline readiness validation for 174k dense embeddings
- ✅ Scale dependency analysis across 1k → 12k → 28k → 174k
- ✅ NESTING_METRIC_DEFECT_v1 audit enforcement

---

## Next Steps

**No action required for fractal-map lane** until legal-distance delivers ACCEPTED 174k dense embeddings.

When dense embeddings become ACCEPTED:
1. Run full 174k dense hierarchical Leiden pipeline (validated config: coarse_0.5_fixed2.0_min20)
2. Execute adversarial evaluation at 174k scale
3. Test citation-role and linear hybrid embeddings at 174k
4. Section-specific cross-lingual evaluation (sachverhalt/erwaegungen/dispositiv)
5. Re-evaluate production deployment vs CV tradeoff

---

## Audit Trail

- **State file:** `state/fractal-map.json` (updated with run 36790229930)
- **Evidence artifacts:** 41 references in `evidence_refs` (all verified present)
- **Reports:** 39+ audit-ready reports in `reports/fractal-map/`
- **Results:** 50+ result directories in `results/fractal_map/`
- **Previous verifications:** 23 audit gates PASS (including CYCLE_36790229930)

---

**VERIFICATION COMPLETE — SNAPSHOT AUDIT-READY**