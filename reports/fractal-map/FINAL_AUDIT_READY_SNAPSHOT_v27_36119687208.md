# FRACTAL-MAP LANE — FINAL AUDIT-READY SNAPSHOT v27
**Cycle:** 36119687208 | **Direction Version:** 27 | **Evidence Tier:** ACCEPTED | **Status:** BLOCKED_ON_DEPENDENCY

---

## Executive Summary

The fractal-map lane has **completed all TF-IDF work at 174k scale** and is **correctly blocked** on the single remaining dependency: `legal-distance_174k_dense_embeddings`. No same-question cycle is justified (`continue_recommended=false`).

All 194 verification tests pass (1 skipped for optional Leiden dependencies). The lane state is frozen, audit-ready, and consistent with the independent gate audit from cycle 36112941372 (PASS).

---

## Deliverables Status

| Deliverable | Status | Evidence |
|-------------|--------|----------|
| **TF-IDF 174k Zoom Quality (v26)** | ✅ COMPLETE | 0/4 modes PASS (frozen FAIL); v25 negative GENERALIZED; v25 freeze protection INTACT (purity bit-equal) |
| **Nesting Metric Defect v1** | ✅ DOCUMENTED & CORRECTED | 37/46 audited modes over-claimed nesting=1.0; honest strict nesting 0.39-0.96; corrected in both parameterized builders |
| **Compressed 5-Level Ladder** | ✅ VALIDATED | 100% purity delta retention across 22 modes; identical zoom navigation at shared resolutions; 29% resolution reduction; NOT universally valid for strict nesting |
| **Hierarchical Leiden 174k Test** | ✅ COMPLETE | `coarse_0.25_sub_2.0`: 22→83,844 clusters, branch purity 0.337→0.392, zoom_improvement_rate=0.947, **BUT** fine median=1, singleton_fraction=0.996 → **OVER_FRAGMENTED** |
| **Zoom Quality Diagnostic (1000-scale)** | ✅ COMPLETE | Citation-role modes confirmed: `citing_alpha0.3` ZQ=0.5401, `following_alpha0.3` ZQ=0.5280, `criticizing_alpha0.3` ZQ=0.4864 vs prod default `outcome_hybrid_0.5` ZQ=0.2798 |
| **Dense Embeddings Readiness** | ✅ COMPLETE | Parameterized builder fixed (branch from chamber, unknown exclusion); evaluation harness created & verified against v26 TF-IDF FAIL verdicts |
| **Citation-Role 174k Validation** | 🚫 BLOCKED | Placeholder builds (`bger_placeholder_*` IDs) + row→id alignment unrecoverable (probe1 agreement 0.426 vs ~1.0; probe2 cluster_metadata CORRUPTED: 1003 duplicate IDs) |
| **Product Multi-View Zoom UI** | ✅ VERIFIED | Citation-role views implemented (CITATION ROLE VIEWS optgroup, zoom controls, split-view, 65 WebGL refs) |
| **Center Projected Hierarchical** | ✅ PASS | `hierarchical_purity_global=0.9571`, `nesting=1.0`, `purity_improvement_vs_flat=2.46%`, beats concat baseline (0.9491) |
| **Legal-Distance Modes Integration** | ✅ COMPLETE | 29 available ACCEPTED modes + 1 `dense_embeddings_placeholder` |

---

## Key Findings (Frozen — Do Not Modify)

### 1. TF-IDF 174k: Strong Coarse Structure, Failed Fine Zoom
- **Coarse navigation WORKS**: Branch purity 0.51-0.55 vs 0.25 random; Legal-area purity 0.24-0.31 vs ~0.005 random
- **Fine zoom FAILS**: Resolution 2.0 median cluster size = 1; Resolution 3.0 median = 1; No monotonic refinement across 3 transitions
- **Root cause**: One massive coarse cluster (83,089 docs = 48% of corpus) fragments into 83,089 singletons. TF-IDF embedding space is structurally skewed — no clustering fix without better representations.

### 2. Evidence-Backed Zoom Path = Citation-Role / Dense-Embedding Modes
- 1000-scale diagnostic confirms: `citing_alpha0.3` ZQ=0.5401, `following_alpha0.3` ZQ=0.5280, `criticizing_alpha0.3` ZQ=0.4864
- Production default `outcome_hybrid_0.5` ZQ=0.2798 (significantly worse)
- Dense embeddings are the only path to viable 174k zoom refinement

### 3. Nesting Metric Defect v1 — Claims Ceiling Enforced
- **PROHIBITED**: `nesting_score >= 0.99` claims for the 7 compressed-family modes
- **Honest strict nesting**: 0.3911-0.9632 (mean 0.8722/0.8644 for 1000-scale by-construction modes)
- **Compressed 5-level ladder [0.25, 0.5, 1.0, 2.0, 3.0]**: Does NOT preserve strict nesting (mean change -0.00364, range [-0.0556, +0.1150], 21/22 modes nonzero)
- **Valid claims LIMITED TO**: 100% purity-delta retention + identical zoom navigation at shared resolutions

### 4. Compressed Ladder Scope
- **VALID**: 100% purity delta retention across all 22 modes; identical zoom navigation at shared resolutions; 29% fewer zoom levels with zero quality loss
- **INVALID**: Universal strict nesting preservation — `honest mean change -0.00364`, 21/22 modes show nonzero deviation
- **Per-mode depth decisions required**: Some modes require the full 7-level ladder

### 5. Orchestration Failure — Root Cause Documented
- **Failure**: Supervisor reads ephemeral `/tmp/lex_control/state/factory_direction.json` (reset each workflow, shows `fractal-map.status=RUN`) instead of persistent workspace state:
  - `state/fractal-map.json`: `cycle_status=BLOCKED_ON_DEPENDENCY`, `continue_recommended=false`
  - `state/factory_direction.json`: `fractal-map.status=COMPLETED_TFIDF`
- **Impact**: 60+ documented re-dispatch occurrences since run 33339971167
- **Required Fix**: Factory Director must update supervisor dispatch logic to read **persistent workspace state**, not ephemeral control plane

---

## Test Suite Verification

```
tests/fractal_map/test_verify.py                 183 passed, 1 skipped
tests/fractal_map/test_zoom_quality_174k_v26_eval.py  7 passed
tests/fractal_map/test_zoom_quality_174k_eval.py     4 passed
─────────────────────────────────────────────────────
TOTAL: 194 passed, 1 skipped (Leiden deps not installed)
```

All tests verify:
- Artifact integrity for 30 legal-distance modes (29 available + 1 placeholder)
- Hierarchical Leiden metrics (purity > 0.95, nesting = 1.0, valid parent hierarchy)
- State file consistency (evidence_tier=ACCEPTED, cycle_status=BLOCKED_ON_DEPENDENCY, continue_recommended=false)
- Compressed ladder 100% delta retention & identical zoom navigation
- Scale-readiness provenance reproduction (N=1200 consistency extension)
- Frozen v26/v25 evaluation specs and verdicts

---

## Gate Artifacts (This Cycle)

| Artifact | Path |
|----------|------|
| Gate JSON | `results/fractal_map/audit/CYCLE_36119687208_GATE.json` |
| State File | `state/fractal-map.json` |
| Test Results | `tests/fractal_map/` (194 passed) |

---

## Prior Gate Artifacts (Audit Trail)

| Cycle | Type | Status |
|-------|------|--------|
| 36112941372 | FINAL_AUDIT_READY_CONFIRMATION | PASS |
| 36107024770 | OPERATIONAL_RESUME_FINAL_AUDIT_READY | PASS |
| 36100882865 | OPERATIONAL_RESUME_FINAL_VERIFICATION | PASS |
| 36094045574 | OPERATIONAL_RESUME_VERIFICATION | PASS |
| 36085875493 | OPERATIONAL_RESUME | PASS |
| 36083220945 | OPERATIONAL_RESUME | PASS |
| 36082543926 | OPERATIONAL_RESUME | PASS |
| 36079647044 | OPERATIONAL_RESUME | PASS |
| 36078550827 | OPERATIONAL_RESUME | PASS |
| 36074331546 | DENSE_EMBEDDINGS_READINESS | COMPLETE |
| 36035695081 | OPERATIONAL_RESUME | COMPLETE |
| 36029852715 | FIRST_174k_ZOOM_QUALITY | FAIL (TF-IDF) |

---

## Recommendation

**NO ADDITIONAL SAME-QUESTION CYCLE JUSTIFIED.**

The fractal-map lane has:
1. ✅ Completed all TF-IDF work at 174k scale (ACCEPTED evidence tier)
2. ✅ Validated all deliverables with independent gate audits (3 consecutive PASS)
3. ✅ Corrected all metric defects (nesting, compressed ladder scope)
4. ✅ Built dense-embeddings-ready infrastructure (builder, harness, metadata)
5. ✅ Identified evidence-backed zoom path (citation-role/dense-embedding modes)
6. 🚫 **BLOCKED** on single dependency: `legal-distance_174k_dense_embeddings`

**Resume condition**: When legal-distance lane delivers 174k dense embeddings (year-split, resumable computation), the fractal-map lane will consume them via the validated `evaluate_174k_dense_embeddings.py` harness and the parameterized builder.

---

## Constitution Compliance

- ✅ **Preserve provenance**: All historical artifacts preserved untouched (NESTING_METRIC_DEFECT_v1 documented, not deleted)
- ✅ **Never fabricate**: All claims backed by evidence refs; negative results (TF-IDF FAIL, OVER_FRAGMENTED) preserved
- ✅ **Never weaken benchmark**: Frozen v26/v25 specs and verdicts unchanged; compressed ladder scope honestly limited
- ✅ **Accepted evidence beats narrative**: Citation-role ZQ scores > production default ZQ accepted as evidence-backed path
- ✅ **Stay on mission**: No work on unrelated legal-AI ideas; all tasks map to fractal case-law map product capability

---

*Signed: Fractal-Map Lane — Cycle 36119687208 — Audit-Ready*