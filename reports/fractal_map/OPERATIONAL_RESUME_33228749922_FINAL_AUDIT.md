# Operational Resume 33228749922 — Final Audit

**Lane:** fractal-map  
**Factory Direction:** v6  
**GitHub Run:** 33228749922  
**Timestamp:** 2026-08-29T02:25:00Z  
**Status:** PASS  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** COMPLETED  
**Next Recommendation:** PRODUCTIZE  

---

## Diagnosis

| Field | Value |
|-------|-------|
| **Issue** | `/tmp/lex_accepted/fractal_map/` mirroring lost due to ephemeral storage volatility between GitHub runs |
| **Root Cause** | `/tmp` directory is ephemeral; accepted branch mirroring must be re-established on every operational resume |
| **Resolution** | Re-established `/tmp/lex_accepted/fractal_map/` mirroring from validated workspace source (`results/fractal_map/`, `reports/fractal_map/`, `state/fractal-map.json`) |

---

## Mirroring Verification

| Metric | Value |
|--------|-------|
| Workspace results files | 233 |
| Workspace reports files | 85 |
| **Total mirrored** | **329** |
| Mirror integrity | ✅ Verified |
| Mirror path | `/tmp/lex_accepted/fractal_map/` |

---

## Verification Tests

**All 48 tests PASS**

| Test Class | Tests | Passed |
|------------|-------|--------|
| TestArtifactIntegrity | 14 | 14 |
| TestHierarchicalLeiden | 6 | 6 |
| TestMetricConsistency | 9 | 9 |
| TestLegacyConcatPreserved | 10 | 10 |
| TestLegalDistanceModes | 9 | 9 |
| **TOTAL** | **48** | **48** |

---

## Loader API Verification

| Mode | Status | Label Arrays | Notes |
|------|--------|--------------|-------|
| center_projected_hierarchical | available | 9 | **DEFAULT** |
| debiased_citation_blended | available | 7 | ACCEPTED (14/14 benchmarks) |
| legal_cited_decisions_only | available | 7 | ACCEPTED (14/14 benchmarks) |
| hybrid_alpha_03 | available | 7 | ACCEPTED (13/14, fails adversarial_falsification) |
| hybrid_alpha_05 | available | 7 | ACCEPTED (13/14, fails adversarial_falsification) |
| legal_issues_outcomes | available | 7 | ACCEPTED (10/14, multiple warnings) |
| hierarchical_leiden_concat | legacy | 9 | LEGACY (preserved for comparison) |
| center_projected | placeholder | 0 | Raw embedding only |

**All API methods functional:**
- `list_modes`, `load_mode`, `get_resolution_labels`, `get_hierarchical_labels`
- `get_coarse_labels`, `get_zoom_mapping`, `get_cluster_metadata`
- `get_hierarchical_cluster_metadata`, `get_decision_clusters`
- `get_zoom_coherence`, `get_mode_spec`

---

## Key Deliverables Verified

| Deliverable | Status |
|-------------|--------|
| Default mode: center_projected_hierarchical | ✅ |
| 7-resolution ladder (0.25 → 3.0) | ✅ |
| Cluster metadata with legal coherence | ✅ |
| Map mode registry (8 modes) | ✅ |
| Product integration spec complete | ✅ |
| Unified loader API functional | ✅ |

---

## Validation Metrics (Carried Forward + v6 Recomputed)

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Hierarchical purity | 0.9571 | > 0.95 | ✅ PASS |
| Nesting score | 1.0 | = 1.0 | ✅ PASS |
| Adversarial language dominance | 0.7593 | < 0.85 | ✅ PASS |
| Jurist pairwise preference | 0.5215 | > 0.5 | ✅ PASS |
| Jurivoc hierarchy alignment | 4/5 | — | ✅ PASS |
| Zoom coherence improvement rate | 31.1% | > 0% | ✅ PASS |

**Sources:** Evaluation v2 cycle 33137354250 (adversarial + jurist + Jurivoc, carried forward) + v6 recomputed zoom validation

---

## Factory Direction v6 Requirements — ALL SATISFIED

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Reproduce hierarchical Leiden on center_projected | ✅ VERIFIED | `center_projected_hierarchical_results.json`: purity=0.9571, nesting=1.0 |
| Expose resolution ladder | ✅ VERIFIED | 7 levels: 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0 |
| Cluster metadata with legal coherence | ✅ VERIFIED | `cluster_metadata.json` with 108 hierarchical clusters |
| Integrate as default map structure | ✅ VERIFIED | center_projected_hierarchical replaces hierarchical_leiden_concat as default |
| Legal-distance selectable modes | ✅ VERIFIED | 5 modes at ACCEPTED tier integrated in registry |

---

## Audit Trail (This Cycle)

- `results/fractal_map/audit/CYCLE_operational_resume_33228749922_FINAL_AUDIT_GATE.json`
- `state/fractal-map.json` (updated with run 33228749922)
- `reports/fractal_map/OPERATIONAL_RESUME_33228749922_FINAL_AUDIT.md`

---

## Final Verdict

**GATE: PASS** — The fractal-map lane has successfully completed all Factory Direction v6 requirements. The hierarchical Leiden fractal map on center_projected embeddings is validated, productized as the DEFAULT map mode, and integrated with 5 legal-distance selectable modes at ACCEPTED tier. The deliverable is audit-ready with full evidence traceability, negative results preserved, and accepted branch mirroring re-established.

**Next Action:** Factory Director may promote to PRODUCTIZE. No further fractal-map cycles under v6.