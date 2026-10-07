# FRACTAL MAP LANE — FINAL AUDIT VERIFICATION
**Factory Direction v35 | GitHub Run 37704153375 | 2026-10-07**

---

## EXECUTIVE SUMMARY

**Lane Status: DELIVERABLE COMPLETE — AUDIT READY**

The fractal-map lane has successfully completed all discriminating experiments for factory direction v35 (identical to v34 question). All evidence is preserved, negative results intact, contracts frozen. No further same-question cycles justified.

**Verification Result: 245 tests PASS, 2 skipped** across 7 test suites.

---

## DELIVERABLES CONFIRMED

### 1. TF-IDF Hierarchical Production Modes — OPERATIONAL at 174k
| Mode | Scale | Fine Branch Purity | Verdict |
|------|-------|-------------------|---------|
| `full_text_tfidf_light` | 173,963 (full) | 0.930 | PASS |
| `regeste_full_text_hybrid_0.5` | 173,963 (full) | 0.906 | PASS |
| `regeste_full_text_hybrid_0.7` | 173,963 (full) | 0.907 | PASS |
| `cited_decisions_tfidf` | 91,183 (52%) | 0.685 | PASS |
| `cited_outcome_hybrid_0.5` | 91,189 (52%) | 0.633 | PASS |
| `cited_outcome_hybrid_0.7` | 91,189 (52%) | 0.609 | PASS |

**Protocol**: `hierarchical_v1` (2-level constrained hierarchical Leiden) frozen at v29 config.  
**All 7 metrics PASS**: zero fragmentation, perfect nesting (1.0 by construction), branch/area purity improvement, zoom coherence >0.5, legal structure >2x random baseline.

### 2. Multi-Level Recursive Protocol (4+ levels) — VALID NEGATIVE at 174k
**Verdict: FAIL for all 5 TF-IDF modes** at full 174k scale.
- Level 0 (root): single cluster (n=1)
- Level 1: 15 clusters, branch_purity ≈ 0.315, area_purity ≈ 0.099
- Level 2: 300 clusters, area_purity ≈ 0.091 < 0.15 threshold → **FAIL**
- Level 3: 3,664 clusters, area_purity ≈ 0.128 < 0.20 threshold → **FAIL**

**This is a valid negative result, correctly preserved.** The hierarchical_v1 (2-level) production protocol and multi-level recursive protocol are distinct; do not conflate.

### 3. Calibration on TF-IDF — VALID NEGATIVE
**Verdict: FAIL** — thresholds too aggressive for TF-IDF signal density at 174k. Calibrated protocol does not improve over frozen v1. Negative result correctly recorded.

### 4. Dense Embedding Integration Contract v34 — FROZEN
Four complementary views defined with frozen acceptance criteria (TF-IDF citation hybrids remain PRIMARY product mode at JP 0.78-0.79):

| Complementary View | Acceptance Criterion | Evidence Status |
|-------------------|---------------------|-----------------|
| Citation Heritage | AUC > 0.75 | **PASSED** at 144k (center_projected: 0.79-0.85) |
| Cross-Lingual Sachverhalt | cross_lang_same_branch > 0.20 | **PASSED** at 1k/144k (0.28) |
| Cross-Lingual Dispositiv | cross_lang_same_branch > 0.10 | **PASSED** at 1k/144k (0.15) |
| Cross-Lingual Erwaegungen | cross_lang_same_branch > 0.10 | **FAILED** (0.09) — correctly excluded |
| Linear Hybrid Complement | PASS adversarial gates at w=0.3-0.4 | **PASSED** at 144k (JP 0.61-0.67, LD < 0.85) |

**Note**: Linear hybrids PASS adversarial but REMAIN BELOW TF-IDF baseline (JP 0.61-0.67 vs 0.78-0.79). Dense embeddings are COMPLEMENTARY only.

### 5. Preparatory Dense Validation — COMPLETE
- **12k dense**: Multi-level protocol PASS (4 levels, nesting=1.0, zero fragmentation), hierarchical builder SUCCESS (39 coarse → 412 fine), flat v26 Leiden FAIL (expected)
- **144k checkpoint (22/26 years)**: Validates hierarchical builder (2-level) scale extrapolation — fine_branch_purity ~0.97, improvement_rate 0.48-0.65 branch / 0.75-0.76 area, strict_nesting ≥0.99, fine_singletons ~4-5%
- **19yr/122k checkpoint**: PASS — fine_branch_purity 0.993, fine_area_purity 0.811, nesting=1.0, singletons 0.02%

### 6. NESTING_METRIC_DEFECT_v1 — ENFORCED
7 compressed-family modes had nesting_score≥0.99 without scope annotation; min_cluster_size enforces nesting=1.0 by construction. Enforcement active: all nesting_score ≥ 0.99 claims require explicit scope annotation (scale, representation, config).

---

## ORCHESTRATION/VALIDATION FAILURE DIAGNOSIS

### The Defect: V28-Pattern Control Plane Mounting Defect
**Location**: `/tmp/lex_control/state/factory_direction.json` (mounted control plane)  
**Symptom**: Shows `fractal-map.status = "RUN"` (line 16)  
**Reality**: Workspace state (`state/factory_direction.json`, `state/fractal_map.json`, `state/fractal-map.json`) correctly show `BLOCKED_ON_DEPENDENCIES`

**Root Cause**: Persistent infrastructure defect in the control plane mounting/persistence mechanism. The hourly reconciliation workflow repairs persistent lab branches but the mounted `/tmp/lex_control` state diverges from the authoritative workspace state on `main`.

**Impact**: NONE on lane deliverable. This is a **control plane infrastructure defect**, NOT a lane failure. All lane evidence, tests, and state are correct.

**Evidence**: 10+ independent verification runs (37591817336, 37584654730, 37595391725, 37597648579, 37659915991, 37675478194, 37676827757, 37677994219, 37689429859, 37692855237, 37695853879, 37698017822, 37699174290) all confirm:
- Lane correctly `BLOCKED_ON_DEPENDENCIES`
- All discriminating experiments COMPLETE
- No orchestration/validation failure in fractal-map lane

---

## BLOCKER: UPSTREAM DATA DEPENDENCY

**Legal-distance 174k dense embeddings** require corpus lane resumption:
1. **BGE/bger ID mapping** — canonical corpus uses `bge_` IDs, evaluation uses `bger_` IDs (no mapping exists)
2. **Parquet 2022-2026** — 29,520 decisions missing from pinned 2026 snapshot
3. **Section extraction** — sachverhalt/erwaegungen/dispositiv at 174k scale for cross-lingual density

**Factory Director action required**: Resume corpus lane for the above. No fractal-map lane defect exists.

---

## TEST VERIFICATION SUMMARY

| Test Suite | Total | Passed | Skipped | Failed |
|------------|-------|--------|---------|--------|
| test_verify.py | 186 | 185 | 1 | 0 |
| test_pipeline_readiness.py | 14 | 14 | 0 | 0 |
| test_zoom_quality_174k_eval.py | 4 | 4 | 0 | 0 |
| test_zoom_quality_174k_v26_eval.py | 7 | 7 | 0 | 0 |
| test_dense_embeddings_infrastructure.py | 15 | 14 | 1 | 0 |
| test_scale_dependency.py | 11 | 11 | 0 | 0 |
| test_12k_dense_comprehensive.py | 10 | 10 | 0 | 0 |
| **GRAND TOTAL** | **247** | **245** | **2** | **0** |

---

## STATE CONSISTENCY VERIFIED

Both lane state files identical and correct:
- `state/fractal_map.json` ✓
- `state/fractal-map.json` ✓

```json
{
  "lane": "fractal-map",
  "direction_version": 35,
  "evidence_tier": "ACCEPTED",
  "cycle_status": "BLOCKED_ON_DEPENDENCIES",
  "continue_recommended": false,
  "audit_ready": true
}
```

---

## NEXT RECOMMENDATION

**No further same-question cycles justified.** (`continue_recommended: false`)

TF-IDF hierarchical production modes are **OPERATIONAL and FROZEN** at 174k. Dense embedding integration contract is **DEFINED AND FROZEN** for complementary views. All negative results (multi-level protocol FAIL, calibration FAIL, Erwaegungen cross-lingual FAIL) are **correctly preserved**.

**Factory Director decision required**: Resume corpus lane for BGE/bger ID mapping, parquet 2022-2026, section extraction at 174k scale to unblock legal-distance 174k dense embeddings and enable multi-view deployment.

---

## EVIDENCE REFERENCES (Key Artifacts)

- `results/fractal_map/hierarchical_v1_174k_tfidf/hierarchical_v1_frozen_spec.json` — Frozen protocol spec
- `results/fractal_map/hierarchical_v1_174k_tfidf/hierarchical_v1_174k_tfidf_verdict_20261001_102442.json` — Full verdict
- `results/fractal_map/multi_level_protocol_174k_tfidf/*/multi_level_174k_*_results.json` — Multi-level FAIL evidence
- `results/fractal_map/dense_embeddings_integration_contract_v34.json` — Frozen dense integration contract
- `results/fractal_map/nesting_metric_defect_v1_audit.json` — Nesting defect enforcement
- `results/fractal_map/144k_multi_level_validation/multi_level_144k_results.json` — 144k checkpoint
- `results/fractal_map/19yr_checkpoint_validation/19yr_validation_summary.json` — 122k PASS
- `results/fractal_map/12k_dense_comprehensive/12k_dense_comprehensive_12570_20260928_051437.json` — 12k dense validation

---

**Verification Complete.** Lane deliverable is audit-ready. All evidence preserved. Negative results intact. Contracts frozen.