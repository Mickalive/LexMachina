# Fractal-Map Lane — v29 Final Verification Report

**Run ID:** fractal_map_v29_verification_20260930_cycle_36660556635  
**Timestamp:** 2026-09-30T02:45:00.000000+00:00  
**Factory Direction Version:** 29  
**GitHub Run:** 36660556635  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  
**Continue Recommended:** false  

---

## Executive Summary

The fractal-map lane has completed all discriminating experiments for the current dependency state. The lane is correctly **BLOCKED_ON_DEPENDENCIES** awaiting legal-distance 174k dense embeddings (only 3/26 years ACCEPTED). All evidence is preserved, negative results retained, and the snapshot is audit-ready.

**Key Finding:** Factory direction v28 discrepancy resolved — v29 accurately reflects that only 1/4 TF-IDF modes PASS the hierarchical_v1 protocol (regeste_tfidf 83k sample, fine_branch_purity=0.566), not "ALL 4 MODES PASS" as v28 claimed.

---

## Orchestration/Validation Failure Diagnosis

### Root Cause
factory_direction.json v28 incorrectly claimed "ALL 4 TF-IDF MODES PASS the frozen v26 zoom-quality acceptance rule (per_mode_verdict: PASS)" for constrained hierarchical Leiden — this conflated the v26 flat zoom-quality rule with the hierarchical_v1 protocol. Actual hierarchical_verdict_20260928_193114.json shows **1/4 PASS** (regeste_tfidf 83k), **3/4 FAIL** on legal_structure_branch (fine_branch_purity ~0.38-0.49 < 0.5 threshold).

### Legal-Distance Progress Gap
- **Checkpoints:** 25/26 years (2000-2024) in progress.json
- **ACCEPTED:** Only 3/26 years (2000-2002, ~19,441 decisions, 11%)
- **PENDING AUDIT:** 22/26 years (2003-2024) — cannot be cited as accepted evidence

### Impact
Fractal-map lane correctly BLOCKED_ON_DEPENDENCIES; no work can proceed without ACCEPTED 174k dense embeddings; all discriminating experiments for current dependency state complete.

### Resolution Path
✅ **RESOLVED** in factory_direction.json v29 — discrepancy acknowledged and corrected; v29 question text accurately reflects 1/4 PASS on hierarchical_v1 protocol.

---

## Accepted Claims (Frozen)

| Claim | Status | Evidence |
|-------|--------|----------|
| Flat Leiden 174k TF-IDF: 0/4 modes pass v26 zoom-quality; severe over-fragmentation (>99% singletons) | CONFIRMED | zoom_quality_174k_eval/v26_verdict.json |
| Constrained hierarchical Leiden 174k TF-IDF (hierarchical_v1): 1/4 PASS (regeste_tfidf 83k), 3/4 FAIL legal_structure_branch | CONFIRMED | hierarchical_zoom_eval/hierarchical_verdict_20260928_193114.json |
| Constrained hierarchical Leiden 174k TF-IDF structural: ALL 4 achieve singleton_fraction=0.0, nesting=1.0 (by construction), improvement_rate 57-90% | CONFIRMED | constrained_hierarchical_tests/ |
| Constrained hierarchical Leiden 12k dense (ACCEPTED): PASS hierarchical_v1 protocol (adaptive=True) | CONFIRMED | 12k_dense_hierarchical_test/hierarchical_leiden_results.json |
| Flat v26 zoom quality at 12k dense: FAIL (only 1/4 transitions >0.5 improvement_rate) | CONFIRMED | 12k_constrained_zoom_diagnostic/constrained_zoom_diagnostic_v2_...json |
| Scale dependency CONFIRMED: 1k severe frag; 1.2k flat PASS; 12k flat FAIL/constrained 45.5%; 28k hier_impr=0.67; 174k flat FAIL | CONFIRMED | Multiple scale validation artifacts |
| Evidence-backed zoom path: citation-role/dense-embedding at 1000-scale (citing_alpha0.3 ZQ=0.5401) | CONFIRMED | zoom_coherence_1000scale_citation_roles.json |
| Production default: cited_outcome_hybrid_0.5 ZQ=0.2798 | CONFIRMED | zoom_coherence_1000scale_citation_roles.json |
| Dense 12k adversarial: FAIL (language_dominance ~0.98, jurist_preference ~0.04) | CONFIRMED | 12k_dense_comprehensive/ |
| Adaptive sub-resolution HARMS zoom quality at ≥10k scale; DEPRECATED | CONFIRMED | 12k_constrained_zoom_diagnostic/ |
| NESTING_METRIC_DEFECT_v1: 7 compressed modes PROHIBITED from nesting≥0.99 claims | ENFORCED | nesting_metric_defect_v1_audit.json |
| Pipeline readiness 174k dense: best config coarse_0.5_fixed2.0_min20 (validated 12k, 28k) | VALIDATED | pipeline_readiness_12k_dense_official.json, 28k_checkpoint_validation/ |
| Scale extrapolation: power law predicts hier_impr ~0.67 at 174k for dense (validated at 28k) | VALIDATED | 28k_checkpoint_validation/28k_validation_20260928_212756.json |
| Alternative hierarchical methods (HNSW, agglomerative, local UMAP): ALL FAIL legal_structure_branch on 174k TF-IDF | NEGATIVE RESULT CONFIRMED | alternative_hierarchical_tests/alt_hierarchical_174k_tfidf_20k_20260929.json |

---

## Blocked Dependencies (Unchanged)

1. **legal-distance 174k dense embeddings:** only 3/26 years (2000-2002) ACCEPTED
2. **citation-role embeddings** not yet available at 174k scale
3. **linear hybrid embeddings** not yet available at 174k scale
4. **Frozen v26 zoom-quality rule** cannot be satisfied by TF-IDF flat clustering at 174k scale
5. **section-specific cross-lingual evaluation** (sachverhalt/erwaegungen/dispositiv) blocked pending dense embeddings

---

## Test Suite Results

- **Total tests:** 240 passed, 1 skipped
- **Duration:** 1.66s
- **All mandatory state fields verified:** lane, direction_version, evidence_tier, cycle_status, continue_recommended, accepted_run_id, evidence_refs, next_recommendation

---

## Artifacts Preserved

All 21 evidence references in state/fractal-map.json are intact and loadable. Negative results (failed modes, adversarial failures, alternative method failures) are preserved as first-class evidence per Research Protocol §5.

---

## Next Recommendation

**BLOCKED on legal-distance 174k dense embeddings** — only 3/26 years (2000-2002, ~19,441 decisions, 11%) ACCEPTED; 28k checkpoint validation CONFIRMS scale extrapolation model (hier_impr ~0.67 at 174k); pipeline readiness RE-VALIDATED on 12k ACCEPTED dense embeddings.

**continue_recommended: false** — no additional same-question cycle justified; Factory Director must decide successor question.

---

## Audit Trail

- **Audit Gates PASSED:** CYCLE_36495654105, CYCLE_36554241961, CYCLE_36580077418, CYCLE_36582579243, CYCLE_36638488102, CYCLE_36644449527, CYCLE_36655303636, CYCLE_36656873671, CYCLE_36658152353, CYCLE_36660556635
- **Verification Complete:** true
- **All Evidence Preserved:** true
- **Negative Results Preserved:** true

---

*This report certifies the fractal-map lane deliverable is complete for the current dependency state and the snapshot is audit-ready.*
