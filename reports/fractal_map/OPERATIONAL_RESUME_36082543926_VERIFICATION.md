# OPERATIONAL RESUME VERIFICATION — Run 36082543926

**Factory Direction:** v27  
**Lane:** fractal-map  
**Resume From:** Run 36081650422 (persisted producer snapshot)  
**Timestamp:** 2026-09-25T01:55:00Z  
**Gate Artifact:** `results/fractal_map/audit/CYCLE_36082543926_GATE.json`

---

## Executive Summary

✅ **OPERATIONAL RESUME VERIFICATION COMPLETE** — All 195 tests PASS.  
✅ **LANE STATUS CONFIRMED:** BLOCKED on `legal-distance_174k_dense_embeddings` (single remaining dependency).  
✅ **NO SAME-QUESTION CYCLE JUSTIFIED:** `continue_recommended=false` — negative result frozen and complete.  
✅ **ALL VALID COMPLETED WORK PRESERVED:** Negative and positive results intact, audit trail complete.  
✅ **ORCHESTRATION FAILURE DIAGNOSED:** Root cause confirmed (supervisor reads ephemeral `/tmp/lex_control` instead of workspace state).  
✅ **SNAPSHOT AUDIT-READY:** All evidence references verified, state files consistent.

---

## Test Suite Verification

| Test File | Tests | Result |
|-----------|-------|--------|
| `tests/fractal_map/test_verify.py` | 184 | ✅ ALL PASS |
| `tests/fractal_map/test_zoom_quality_174k_v26_eval.py` | 7 | ✅ ALL PASS |
| `tests/fractal_map/test_zoom_quality_174k_eval.py` | 4 | ✅ ALL PASS |
| **TOTAL** | **195** | **✅ 195/195 PASS** |

All tests match the count recorded in `CYCLE_36079647044_GATE.json` (195 PASS, 0 FAIL, 0 ERROR).

---

## Lane State Verification

### Current Accepted State (`state/fractal-map.json` — Run 36079647044)

| Field | Value |
|-------|-------|
| `lane` | fractal-map |
| `direction_version` | 27 |
| `evidence_tier` | ACCEPTED |
| `cycle_status` | COMPLETED |
| `continue_recommended` | false |
| `accepted_run_id` | 35952633500 |
| `github_run` | 36079647044 |
| `resume_from_run_id` | 36078550827 |
| `blocked_on` | legal-distance_174k_dense_embeddings |
| `blocked_since` | 2026-09-24T01:55:00Z |
| `resume_guard` | final_audit_complete_v12 |
| `next_recommendation` | BLOCKED on legal-distance_174k_dense_embeddings. Resume when dense embeddings delivered. No same-question cycle justified. |

### Key Metrics (Frozen & Verified)

| Metric | Value | Status |
|--------|-------|--------|
| `center_projected_hierarchical` verdict | PASS | ✅ |
| `hierarchical_purity_global` | 0.957093 | ✅ |
| `best_config` | coarse_0.5_fine_3.0 | ✅ |
| `purity_improvement_vs_flat_pct` | 2.46% | ✅ |
| `nesting_score` (by construction) | 1.0 | ✅ |

---

## Orchestration Failure — Root Cause Confirmed

**Diagnosis (60+ documented occurrences since run 33339971167):**

The supervisor dispatch logic reads **ephemeral** `/tmp/lex_control/state/factory_direction.json` (reset each workflow run) instead of **persistent workspace** state:
- Workspace `state/factory_direction.json`: `fractal-map.status=COMPLETED_TFIDF`
- Workspace `state/fractal-map.json`: `blocked_on=legal-distance_174k_dense_embeddings`, `continue_recommended=false`
- Ephemeral `/tmp/lex_control/state/factory_direction.json`: `fractal-map.status=RUN` (stale v27 direction)

**Result:** Supervisor sees `status=RUN` and re-dispatches the lane despite the lane being correctly BLOCKED with `continue_recommended=false`.

**Required Fix:** Factory Director must update supervisor dispatch logic to read workspace state (`state/fractal-map.json` and `state/factory_direction.json`) instead of ephemeral `/tmp/lex_control/state/factory_direction.json`.

**This operational resume (36082543926) confirms the diagnosis persists.** No code fix was applied in this cycle — the fix is a Factory Director action outside lane scope.

---

## Evidence Summary — Frozen Negative Results (Preserved)

| Finding | Detail | Evidence Tier |
|---------|--------|---------------|
| **v25 FAIL** (primary mode) | FAIL on all 3 frozen success checks | ACCEPTED |
| **v26 FAIL** (all 4 decision-mappable TF-IDF 174k modes) | FAIL on all 3 frozen success checks — negative generalized to full mappable set | ACCEPTED |
| **Compressed ladder nesting defect** | 21/22 modes fail strict nesting preservation at 1000-scale (`NESTING_METRIC_DEFECT_v1`) | ACCEPTED |
| **TF-IDF 174k over-fragmentation** | Median cluster size 1 at fine resolutions (structural barrier to zoom refinement) | ACCEPTED |
| **Citation-bearing TF-IDF hybrids** | Do NOT outperform regeste-only at 174k zoom refinement (delta ~ -0.025 vs ~ -0.002) | ACCEPTED |

**Conclusion:** Zoom-quality at 174k **NOT established** for TF-IDF-only modes. Evidence-backed zoom path remains **citation-role/dense-embedding modes** (1000-scale: `citing_alpha0.3` ZQ=0.5401, `following_alpha0.3` ZQ=0.5280, `criticizing_alpha0.3` ZQ=0.4864, production default `outcome_hybrid_0.5` ZQ=0.2798).

---

## Evidence Summary — Preserved Positive Results

| Finding | Detail | Evidence Tier |
|---------|--------|---------------|
| **TF-IDF 174k legal structure** | Branch purity 0.51–0.55 vs 0.25 random; legal_area purity 0.24–0.31 vs ~0.005 random at ALL resolutions | ACCEPTED |
| **center_projected_hierarchical @ 1000-scale** | PASS (nesting=1.0, purity=0.957 > concat baseline 0.949) | ACCEPTED |
| **Hierarchical Leiden** | Guarantees perfect nesting by construction (zoom within clusters) | ACCEPTED |
| **Compressed 5-level ladder** | 100% purity delta retention for ALL 22 modes at 1000-scale; 29% fewer zoom levels | ACCEPTED |
| **Zoom navigation mappings** | Identical at shared resolutions between full and compressed ladders | ACCEPTED |
| **Multi-view zoom UI** | Citation-role views (citing, following, criticizing) implemented at product level (audit rec #4) | ACCEPTED |
| **1000-scale citation-role modes** | Strong zoom quality (`citing_alpha0.3` ZQ=0.5401) | ACCEPTED |

---

## Deliverables Verified (from CYCLE_36079647044_GATE.json)

| Deliverable | Status | Notes |
|-------------|--------|-------|
| TF-IDF 174k zoom-quality v26 | COMPLETE | 0/4 modes PASS (frozen FAIL) |
| v25 freeze protection | INTACT | Purity bit-equal, zoom claims identical |
| Nesting metric defect v1 | DOCUMENTED | 37/46 modes over-claimed, corrected in state |
| Compressed 5-level ladder | VALIDATED | 100% purity delta retention, 22 modes |
| Dense embeddings readiness | COMPLETE | Builder fixed, harness created, verified vs v26 TF-IDF |
| Citation-role 174k validation | BLOCKED | Placeholder builds + alignment corruption (needs full corpus JSONL) |
| Product multi-view zoom UI | VERIFIED | Citation-role views implemented |
| Test suite | 195 PASS | All tests passing |

---

## 174k Census & Alignment Probe (Frozen v26)

| Classification | Count | Details |
|----------------|-------|---------|
| True 174k decision-mappable | 4 | `cited_decisions_tfidf_outcome_hybrid_0.5_174k_v25`, `cited_decisions_tfidf_outcome_hybrid_0.7_174k_compressed_v25`, `cited_decisions_tfidf_outcome_hybrid_0.5_174k`, `regeste_tfidf_174k` |
| True 174k placeholder-only | 2 | Not decision-mappable |
| Misnamed 21k builds | 6 | Not 174k scale |

**Alignment Probe Verdict:** CORRUPTED  
- Row→ID agreement: 0.4264 (expected ~1.0) → **REJECTED**  
- Cluster metadata: 1003 duplicate IDs, 1314 extra rows → **CORRUPTED**  
- **Requires full corpus JSONL delivery from corpus lane**

---

## Dense Embeddings Readiness — COMPLETE (Run 36074331546)

| Component | Status |
|-----------|--------|
| Parameterized builder fix | ✅ Branch from chamber field; unknown branches excluded |
| Evaluation harness | ✅ `fractal_map/evaluation/evaluate_174k_dense_embeddings.py` created |
| Harness verification | ✅ Reproduces v26 FAIL verdicts for TF-IDF modes |
| 174k metadata | ✅ ACCEPTED: 173,963 entries, 100% branch+legal_area coverage |
| 174k corpus | ✅ 37 year-split JSONL available |
| Compressed 5-level ladder | ✅ Hardcoded `[0.25, 0.5, 1.0, 2.0, 3.0]` |

**Infrastructure ready to consume legal-distance 174k dense embeddings year-split.**

---

## Product Integration Status

| Component | Status |
|-----------|--------|
| Multi-view zoom UI | ✅ Implemented & verified (CITATION ROLE VIEWS optgroup, zoom controls, split-view, 65 WebGL refs) |
| API endpoints | ✅ 54 endpoints validated at 174k simulation (16/16 PASS: LOD<2s, culling<500ms, spatial index<5s, k-NN<500ms, inverted index<15s, WebGL ~6.6MB, full pipeline<3s) |
| Serving defaults | `PRODUCT_SERVING_DEFAULT=cited_outcome_hybrid_0.5`, `COMBINATION_MODE=linear_hybrid05_concat`, `DEFAULT_MAP_MODE=center_projected_64dim_hierarchical` |
| Blocked on | `legal-distance_174k_dense_embeddings` (citation-role and dense embedding modes at 174k scale) |

---

## Next Recommendation

**BLOCKED** — Resume **ONLY** when legal-distance delivers first 174k dense embeddings:
- Citation-role modes: `citing_alpha0.3`, `following_alpha0.3`, `criticizing_alpha0.3`
- Outcome hybrids at 174k scale

**DO NOT** run additional TF-IDF-only 174k cycles — negative result frozen and complete.

All valid completed work preserved. Snapshot audit-ready.

---

## Gate Artifact

See `results/fractal_map/audit/CYCLE_36082543926_GATE.json` for machine-readable gate record.