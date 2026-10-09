# Fractal Map Lane - Operational Resume Final Audit-Ready Snapshot

**Factory Direction**: v35  
**Lane**: fractal-map  
**GitHub Run**: 38004888068  
**Timestamp**: 2026-10-09T23:45:00.000000Z  
**Resume From**: Persisted producer snapshot of run 38003948885  

---

## Executive Summary

**STATUS: VERIFIED AND AUDIT-READY** ✅

This operational resume from the persisted producer snapshot of run 38003948885 confirms that the fractal-map lane deliverable for factory direction v35 is **complete, verified, and audit-ready**. All discriminating experiments for the v34/v35 question are complete.

### Fresh Verification Results (Clean Environment)

| Test Suite | Tests Passed | Tests Skipped | Tests Failed |
|------------|--------------|---------------|--------------|
| test_verify.py (artifact integrity, metric consistency, legacy concat, legal distance modes, compressed ladder, scale readiness) | 185 | 1 | 0 |
| test_pipeline_readiness.py (hierarchical Leiden pipeline, zoom coherence, LOD, WebGL, dense embeddings requirements) | 14 | 0 | 0 |
| test_zoom_quality_174k_eval.py (frozen spec, verdict FAIL recorded) | 4 | 0 | 0 |
| test_zoom_quality_174k_v26_eval.py (v26 verdict FAIL, baseline pinned, census, alignment) | 7 | 0 | 0 |
| test_12k_dense_comprehensive.py (constrained hierarchical, zero fragmentation, perfect nesting, zoom coherence) | 10 | 0 | 0 |
| test_dense_embeddings_infrastructure.py (evaluation script, success rules, metadata, builder, workflow) | 14 | 1 | 0 |
| test_scale_dependency.py (improvement rates, flat zoom collapse, citation role ZQ, nesting defect) | 11 | 0 | 0 |
| **GRAND TOTAL** | **245** | **2** | **0** |

---

## Confirmed Accepted Evidence (v34/v35)

### 1. TF-IDF Hierarchical Production Modes — OPERATIONAL at 174k
- **3 text-based modes at full 173,963 decisions**: `cited_decisions_tfidf`, `cited_decisions_tfidf_outcome_hybrid_0.5`, `cited_decisions_tfidf_outcome_hybrid_0.7`
- **fine_branch_purity**: 0.906–0.930 (all PASS hierarchical_v1 protocol threshold > 0.5)
- **16/16 scale simulation tests PASS** (product integration)
- **WebGL pipeline**: <3s render at full scale

### 2. Multi-Level Recursive Protocol — STRUCTURALLY VALIDATED, Calibration FAILS
- **4-level recursive protocol**: Perfect nesting (≥0.95), zero fragmentation, monotonic refinement
- **Calibration FAILS** on TF-IDF (thresholds too aggressive for signal density) — **valid negative result preserved**

### 3. Dense Embedding Integration Contract v34 — FROZEN
Four complementary views with frozen acceptance criteria:
| View | Acceptance Criterion |
|------|---------------------|
| Citation Heritage | AUC > 0.75 |
| Cross-Lingual Sachverhalt | Same-branch > 0.20 |
| Cross-Lingual Dispositiv | Same-branch > 0.10 |
| Linear Hybrid Complement | PASS adversarial gates |

### 4. Scale Extrapolation — VALIDATED at 144k Checkpoint
- **22/26 years (2000-2021)**: fine_branch_purity ~0.97
- **Improvement rate**: 0.48–0.65 branch / 0.75–0.76 area
- **Strict nesting**: ≥0.99
- **Fine singletons**: ~4-5%

### 5. NESTING_METRIC_DEFECT_v1 — ENFORCED
Strict definition: fine label's parent must match coarse label for that decision. Previous lenient "any parent has child" inflated scores.

---

## Orchestration/Validation Failure Diagnosis

### The Defect
**V28-pattern control plane mounting defect PERSISTS** in `/tmp/lex_control/state/factory_direction.json`:
- Line 16: `"status": "RUN"` for fractal-map lane
- Workspace `state/factory_direction.json` and lane state correctly show: `"cycle_status": "BLOCKED_ON_DEPENDENCIES"`

### Root Cause Analysis
This is a **PERSISTENT INFRASTRUCTURE DEFECT** in the control plane mounting/persistence mechanism, NOT a fractal-map lane failure. The defect has persisted since factory direction v28 and appears in every subsequent version (v29-v35).

The `/tmp/lex_control/` directory is the workflow-mounted control plane from `main`, but it appears to be mounting a stale or incorrectly synchronized version where the fractal-map status was never updated from "RUN" to "BLOCKED_ON_DEPENDENCIES" despite:
1. The lane state (`state/fractal_map.json`) correctly showing `BLOCKED_ON_DEPENDENCIES` since v28
2. The workspace factory_direction.json correctly showing `BLOCKED_ON_DEPENDENCIES`
3. Multiple audit confirmations documenting this exact mismatch

### Impact
- External observers / downstream lanes see fractal-map as runnable when it is correctly blocked
- Could trigger premature product integration attempts on un-audited dense embeddings
- Masks the true critical path: **legal-distance 174k dense embeddings audit promotion** (which requires corpus lane resumption)

### Resolution Required (Control Plane)
Update `factory_direction.json` on `main` branch:
```json
"fractal-map": {
  "status": "BLOCKED_ON_DEPENDENCIES",
  ...
}
```
No version increment needed — v35 question fully answered.

---

## Blocker: Upstream Dependencies (Corpus Lane Resumption Required)

The fractal-map lane is **correctly BLOCKED** on legal-distance 174k dense embeddings, which requires corpus lane resumption for:

1. **BGE/bger ID mapping production** (canonical corpus uses `bge_` IDs, evaluation uses `bger_` IDs — no mapping exists)
2. **Parquet generation for years 2022-2026** (29,520 decisions missing)
3. **Section extraction** (sachverhalt/erwaegungen/dispositiv) at 174k scale for cross-lingual evaluation

---

## State File Confirmation

The lane state (`state/fractal_map.json`) correctly reflects:
- `evidence_tier`: "ACCEPTED"
- `cycle_status`: "BLOCKED_ON_DEPENDENCIES"
- `continue_recommended`: false
- `audit_ready`: true
- All evidence_refs preserved
- `next_recommendation` identifies dense embeddings dependency and confirms TF-IDF operational

---

## Recommendation

**No further same-question cycles justified.** `continue_recommended = false`.

**Factory Director action required**: Resume corpus lane for BGE/bger ID mapping, 2022-2026 parquet (29,520 decisions), and section extraction at 174k scale.

---

## Artifacts Preserved

All evidence, negative results, and contracts preserved per LexMachina invariants:
- TF-IDF hierarchical production modes: FROZEN and OPERATIONAL
- Multi-level recursive protocol: NEGATIVE result preserved (calibration FAILS)
- Dense embedding integration contract v34: FROZEN with 4 complementary views
- Scale extrapolation: VALIDATED at 144k
- NESTING_METRIC_DEFECT_v1: ENFORCED
- All raw outputs and failures preserved

**Lane deliverable VERIFIED AND AUDIT-READY** for GitHub run 38004888068.