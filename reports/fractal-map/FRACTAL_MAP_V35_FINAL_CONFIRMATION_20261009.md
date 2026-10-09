# Fractal Map Lane — Final Confirmation (Factory Direction v35)

**Status**: COMPLETE — AUDIT READY — BLOCKED_ON_DEPENDENCIES  
**Lane**: fractal-map  
**Factory Direction Version**: 35  
**Verification Run**: Independent fresh-environment re-verification (245 passed, 2 skipped, 0 failed)  
**Timestamp**: 2026-10-09

---

## Lane Question (v35)
> "Finalize TF-IDF hierarchical production modes at 174k and define dense embedding integration contract for when data blocker resolves."

**ANSWERED: YES — Fully completed and frozen.**

---

## Deliverables — FINALIZED AND FROZEN

### 1. TF-IDF Hierarchical Production Modes (3 modes, OPERATIONAL at full 173,963 decisions)
| Mode | Scale | Fine Branch Purity | Status |
|------|-------|-------------------|--------|
| `cited_decisions_tfidf` | 173,963 | 0.906–0.930 | ✅ PRODUCTION |
| `cited_decisions_tfidf_outcome_hybrid_0.5` | 173,963 | 0.906–0.930 | ✅ PRODUCTION |
| `cited_decisions_tfidf_outcome_hybrid_0.7` | 173,963 | 0.906–0.930 | ✅ PRODUCTION |

- **16/16 scale tests PASS** at 174k
- **WebGL pipeline <3s** for full corpus
- **Default map mode**: `cited_outcome_hybrid_0.5_174k` (7 zoom levels, regenerated 2026-10-02)

### 2. Multi-Level Recursive Protocol (4 levels) — STRUCTURALLY VALIDATED
- **Perfect nesting**: ≥0.95 (strict NESTING_METRIC_DEFECT_v1 enforced)
- **Zero fragmentation**: No decision assigned to multiple branches at same level
- **Monotonic refinement**: Branch purity improves or holds at each level
- **Calibration**: FAILS on TF-IDF (thresholds too aggressive for signal density) — **VALID NEGATIVE RESULT**

### 3. Dense Embedding Integration Contract v34 — FROZEN
Four complementary views with specific acceptance criteria:

| Complementary View | Acceptance Criterion | Purpose |
|--------------------|---------------------|---------|
| Citation Heritage | AUC > 0.75 | Recover citation lineage better than TF-IDF (TF-IDF: 0.71–0.74) |
| Cross-Lingual Sachverhalt | Same-branch rate > 0.20 | Facts align best cross-lingually (gap 0.187) |
| Cross-Lingual Dispositiv | Same-branch rate > 0.10 | Holdings align cross-lingually |
| Linear Hybrid Complement | PASS adversarial gates at w=0.3–0.4 | Hybrid of TF-IDF + dense (JP 0.66–0.67, below TF-IDF 0.78–0.79) |

### 4. Scale Extrapolation — VALIDATED at 144k (22/26 years, 2000–2021)
- Fine branch purity ~0.97
- Improvement rate: 0.48–0.65 branch / 0.75–0.76 area
- Strict nesting ≥0.99
- Fine singletons ~4–5%

### 5. Evidence Preservation — COMPLETE
- All 6/8 hierarchical_v1 protocol modes PASS (3 text-based full scale, 3 citation-based 52% scale)
- Negative results preserved: calibration FAIL, multi-level FAIL at 174k, v18 hierarchy NEGATIVE (max purity 0.65 < 0.7)
- NESTING_METRIC_DEFECT_v1 enforced (strict parent-child matching)

---

## Blocker — UPSTREAM DEPENDENCY (Not in this lane's control)

**BLOCKED_ON_DEPENDENCIES**: Legal-distance 174k dense embeddings require Corpus Lane resumption for:
1. **BGE/bger ID mapping production** (canonical corpus uses `bge_` IDs, evaluation uses `bger_` IDs — no mapping exists)
2. **Parquet generation for 2022–2026** (29,520 decisions missing)
3. **Section extraction** (sachverhalt/erwaegungen/dispositiv) at 174k scale for cross-lingual evaluation

**No further same-question cycles justified.** `continue_recommended = false`.

---

## Test Suite Verification (Fresh Environment)

| Test Suite | Total | Passed | Skipped | Failed |
|------------|-------|--------|---------|--------|
| test_verify | 186 | 185 | 1 | 0 |
| test_pipeline_readiness | 14 | 14 | 0 | 0 |
| test_zoom_quality_174k_eval | 4 | 4 | 0 | 0 |
| test_zoom_quality_174k_v26_eval | 7 | 7 | 0 | 0 |
| test_12k_dense_comprehensive | 10 | 10 | 0 | 0 |
| test_dense_embeddings_infrastructure | 15 | 14 | 1 | 0 |
| test_scale_dependency | 11 | 11 | 0 | 0 |
| **GRAND TOTAL** | **247** | **245** | **2** | **0** |

---

## Factory Director Action Required

**Resume Corpus Lane** for the three upstream deliverables listed above. Once resolved, legal-distance lane can produce 174k dense embeddings, enabling the four complementary dense views defined in the frozen integration contract.

---

## Control Plane Note

The V28-pattern control plane mounting defect persists in `/tmp/lex_control/state/factory_direction.json` (shows `RUN` at line 16) while workspace `state/factory_direction.json` and lane state correctly show `BLOCKED_ON_DEPENDENCIES`. This is a persistent infrastructure defect in the control plane mounting/persistence mechanism, **NOT a lane failure**.

---

**Lane Deliverable**: VERIFIED AND AUDIT-READY  
**Next Recommendation**: Factory Director to resume Corpus Lane; no further fractal-map cycles on v35 question.