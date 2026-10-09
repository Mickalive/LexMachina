# Fractal Map Lane — Final Independent Verification (GitHub Run 37986150960)

**Factory Direction**: v35 | **Lane**: fractal-map | **Status**: BLOCKED_ON_DEPENDENCIES | **Evidence Tier**: ACCEPTED

## Executive Summary

**FRESH INDEPENDENT VERIFICATION** in clean environment with fresh dependency install confirms:

- ✅ **246 tests passed, 1 skipped, 0 failed** across all 6 core test suites
- ✅ TF-IDF hierarchical production modes **FINALIZED and OPERATIONAL** at 174k (173,963 decisions)
- ✅ Dense embedding integration contract v34 **FROZEN** with 4 complementary views
- ✅ Multi-level recursive protocol **STRUCTURALLY VALIDATED** at 174k (calibration FAILS — valid negative)
- ✅ Lane correctly **BLOCKED_ON_DEPENDENCIES** on upstream legal-distance 174k dense embeddings
- ✅ `continue_recommended: false` — no further same-question cycles justified
- ✅ All evidence preserved, negative results intact, contracts frozen
- ✅ **Lane deliverable VERIFIED AND AUDIT-READY**

---

## Factory Direction v35 Question

> **"Finalize TF-IDF hierarchical production modes at 174k and define dense embedding integration contract for when data blocker resolves."**

**STATUS: COMPLETE** — Both deliverables finalized and frozen.

---

## Deliverable 1: TF-IDF Hierarchical Production Modes (FINALIZED)

### Hierarchical_v1 Protocol Results (8 modes evaluated at 174k)

| Mode | Verdict | Fine Branch Purity | Coarse Branch Purity | Improvement Rate | Scale |
|------|---------|-------------------|---------------------|------------------|-------|
| `full_text_tfidf_light` | **PASS** | **0.9301** | 0.7664 | 0.7368 | Full 173,963 |
| `regeste_full_text_hybrid_0.5` | **PASS** | **0.9057** | 0.7830 | 0.5833 | Full 173,963 |
| `regeste_full_text_hybrid_0.7` | **PASS** | **0.9089** | 0.7276 | 0.7500 | Full 173,963 |
| `cited_decisions_tfidf` | **PASS** | **0.6846** | 0.5326 | 0.7241 | 52% (91k) |
| `cited_outcome_hybrid_0.5` | **PASS** | **0.6329** | 0.5233 | 0.7097 | 52% (91k) |
| `cited_outcome_hybrid_0.7` | **PASS** | **0.6089** | 0.4976 | 0.7500 | 52% (91k) |
| `outcome_tfidf` | FAIL | 0.3602 | 0.3602 | 0.0000 | Full 173,963 |
| `regeste_tfidf` | FAIL | 0.0000 | 0.0000 | 0.0000 | Full 173,963 |

**Key Metrics:**
- 3 text-based modes: fine_branch_purity **0.906–0.930** at full 173,963 decisions
- 3 citation-based modes: fine_branch_purity **0.609–0.685** at 52% scale
- All 6 passing modes exceed fine_branch_purity > 0.5 threshold
- 16/16 scale simulation tests PASS
- WebGL pipeline <3s at 174k

### Production Defaults (FROZEN)
- `PRODUCT_SERVING_DEFAULT`: `cited_outcome_hybrid_0.5_174k`
- `COMBINATION_MODE`: `linear_hybrid05_concat`
- `DEFAULT_MAP_MODE`: `center_projected_64dim_hierarchical`

---

## Deliverable 2: Dense Embedding Integration Contract v34 (FROZEN)

**Status**: FROZEN (2026-10-03) — awaiting legal-distance 174k dense embeddings

### Four Complementary Views Defined

| View | Acceptance Criterion | Evidence at Checkpoint Scale | Status |
|------|---------------------|------------------------------|--------|
| **Citation Heritage** | AUC > 0.75 | 144k: center_projected AUC 0.79–0.85 | ✅ PASSED |
| **Cross-Lingual (Sachverhalt)** | cross_lang_same_branch > 0.20 | 144k: 0.2816 | ✅ PASSED |
| **Cross-Lingual (Dispositiv)** | cross_lang_same_branch > 0.10 | 144k: 0.1481–0.1502 | ✅ PASSED |
| **Cross-Lingual (Erwaegungen)** | cross_lang_same_branch > 0.10 | 144k: 0.0925–0.0941 | ❌ FAILED (excluded) |
| **Linear Hybrid Complement** | PASS adversarial gates at w=0.3–0.4 | 144k: JP 0.61–0.67, LD < 0.85 | ✅ PASSED (below TF-IDF baseline) |

**Note**: Dense embeddings remain BELOW TF-IDF baseline (JP 0.61–0.67 vs 0.78–0.79). These are COMPLEMENTARY views only. TF-IDF citation hybrids remain PRIMARY product mode.

### Product Integration Plan
- `citation_heritage_view` — separate map mode
- `cross_lingual_sachverhalt_view` — separate map mode
- `cross_lingual_dispositiv_view` — separate map mode
- `linear_hybrid_complement_view` — marked EXPLORATORY

### Infrastructure Readiness
- Hierarchical builder: VALIDATED at 12k dense (4 levels, nesting=1.0, zero fragmentation)
- Map mode registry: READY for dense mode registration
- Zoom neighborhood API: READY
- WebGL pipeline: VALIDATED at 174k TF-IDF (<3s), ready for dense

---

## Multi-Level Recursive Protocol (174k TF-IDF)

**STRUCTURALLY VALIDATED** — 4 levels of recursive constrained hierarchical Leiden:
- Perfect nesting ≥ 0.95 at all level transitions
- Zero fragmentation (singleton_fraction < 0.01)
- Monotonic refinement (cluster sizes decrease appropriately)
- **Calibration FAILS** — thresholds too aggressive for TF-IDF signal density at 174k (valid negative finding)

---

## Scale Extrapolation Validated (144k Checkpoint)

144k checkpoint (22/26 years, 2000–2021, PENDING AUDIT) validates scale extrapolation:
- fine_branch_purity ~0.97
- improvement_rate: 0.48–0.65 (branch) / 0.75–0.76 (area)
- strict_nesting ≥ 0.99
- fine_singletons ~4–5%

**NESTING_METRIC_DEFECT_v1 ENFORCED** — strict definition requires fine label's parent matches coarse label for that decision; previous lenient definition inflated scores.

---

## Blockers (Upstream Dependencies)

| Blocker | Lane | Detail |
|---------|------|--------|
| BGE/bger ID mapping | Corpus | Canonical corpus uses `bge_` IDs, evaluation uses `bger_` IDs — no mapping exists |
| Parquet 2022–2026 | Corpus | 29,520 decisions missing from pinned 2026 snapshot |
| Section extraction | Corpus | sachverhalt/erwaegungen/dispositiv at 174k scale for cross-lingual density |
| 174k dense embeddings | Legal-distance | Requires corpus deliverables first; currently ~19k decisions (11%) |

---

## Test Verification Summary (Run 37986150960)

| Test Suite | Total | Passed | Skipped | Failed |
|------------|-------|--------|---------|--------|
| test_verify | 186 | 186 | 0 | 0 |
| test_pipeline_readiness | 14 | 14 | 0 | 0 |
| test_zoom_quality_174k_eval | 4 | 4 | 0 | 0 |
| test_zoom_quality_174k_v26_eval | 7 | 7 | 0 | 0 |
| test_12k_dense_comprehensive | 10 | 10 | 0 | 0 |
| test_dense_embeddings_infrastructure | 15 | 14 | 1 | 0 |
| test_scale_dependency | 11 | 11 | 0 | 0 |
| **TOTAL** | **247** | **246** | **1** | **0** |

---

## Control Plane Defect Note

**V28-pattern control plane mounting defect PERSISTS** in `/tmp/lex_control/state/factory_direction.json` (shows `RUN` at line 16) while workspace `state/factory_direction.json` and lane state correctly show `BLOCKED_ON_DEPENDENCIES`. This is a **PERSISTENT INFRASTRUCTURE DEFECT** in the control plane mounting/persistence mechanism, **NOT a lane failure**. Zero impact on deliverables.

---

## State File Consistency Verification

✅ `state/fractal-map.json`: `direction_version=35`, `evidence_tier=ACCEPTED`, `cycle_status=BLOCKED_ON_DEPENDENCIES`, `continue_recommended=false`, `audit_ready=true`

✅ `state/factory_direction.json` (workspace): `fractal-map.status=BLOCKED_ON_DEPENDENCIES`

❌ `/tmp/lex_control/state/factory_direction.json` (mounted control plane): `fractal-map.status=RUN` — **INFRASTRUCTURE DEFECT**

---

## Evidence Preservation

All ACCEPTED evidence preserved in `results/fractal_map/` with full provenance:
- `hierarchical_v1_174k_tfidf/` — 8 mode results (6 PASS, 2 FAIL)
- `multi_level_protocol_174k_tfidf/` — 5 modes FAIL (valid negative)
- `dense_embeddings_integration_contract_v34.json` — frozen contract
- `nesting_metric_defect_v1_audit.json` — metric enforcement
- `scale_extrapolation/` — scale model
- `final_pipeline_validation/` — pipeline readiness
- `hierarchical_product_integration/` — product artifacts

---

## Recommendation

**No further same-question cycles justified.** Factory Director action required:

1. **Resume corpus lane** for:
   - BGE/bger ID mapping production
   - Parquet generation for years 2022–2026 (29,520 decisions)
   - Section extraction (sachverhalt/erwaegungen/dispositiv) at 174k scale

2. Once corpus delivers, legal-distance computes 174k dense embeddings

3. Fractal-map integrates dense complementary views per frozen contract v34

---

## Audit Trail

- **Verification Run**: 37986150960
- **Timestamp**: 2026-10-09
- **Previous Verifications**: 37966513028, 37959699105, 37957990046, 37956182695, 37952999658, 37900638410, 37889827524, 37871021839
- **State File**: `state/fractal-map.json` (consistent, audit_ready=true)
- **Accepted Run ID**: `FRACTAL_MAP_V35_FINAL_AUDIT_READY_20261009_37867851730`

**Lane deliverable VERIFIED AND AUDIT-READY.**