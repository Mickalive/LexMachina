# Fractal Map Lane — Final Verification Run 38002296609
## Fresh Independent Re-verification of v35 Deliverables

**Date:** 2026-10-09  
**Factory Direction:** v35  
**GitHub Run:** 38002296609  
**Lane Status:** BLOCKED_ON_DEPENDENCIES (deliverable COMPLETE for v34/v35 question)  
**Evidence Tier:** ACCEPTED  

---

## Verification Summary

**All 7 fractal-map test suites PASS** in fresh environment with clean dependency install:

| Test Suite | Passed | Skipped | Failed | Total |
|------------|--------|---------|--------|-------|
| test_verify.py | 186 | 0 | 0 | 186 |
| test_pipeline_readiness.py | 14 | 0 | 0 | 14 |
| test_zoom_quality_174k_eval.py | 4 | 0 | 0 | 4 |
| test_zoom_quality_174k_v26_eval.py | 7 | 0 | 0 | 7 |
| test_12k_dense_comprehensive.py | 10 | 0 | 0 | 10 |
| test_dense_embeddings_infrastructure.py | 14 | 1 | 0 | 15 |
| test_scale_dependency.py | 11 | 0 | 0 | 11 |
| **TOTAL** | **246** | **1** | **0** | **247** |

---

## Diagnosis Reconfirmed

**No orchestration/validation failure in fractal-map lane.** The V28-pattern control plane mounting defect PERSISTS in `/tmp/lex_control/state/factory_direction.json` (shows `status: "RUN"` at line 16) while workspace `state/factory_direction.json` and lane `state/fractal-map.json` correctly show `BLOCKED_ON_DEPENDENCIES`. This is a **PERSISTENT INFRASTRUCTURE DEFECT** in the control plane mounting/persistence mechanism, **NOT a lane failure**.

---

## Deliverable Status — All Complete for v34/v35 Question

### ✅ TF-IDF Hierarchical Production Modes FINALIZED and OPERATIONAL at 174k
- **3 production modes** at full 173,963 decisions: `cited_decisions_tfidf`, `cited_decisions_tfidf_outcome_hybrid_0.5`, `cited_decisions_tfidf_outcome_hybrid_0.7`
- **Fine branch purity:** 0.906–0.930 (text-based, full scale) / 0.609–0.685 (citation-based, 52% scale)
- **16/16 scale tests PASS** — product integration ready
- **WebGL pipeline:** <3s at 174k

### ❌ Multi-level Recursive Protocol — FAILS at 174k (VALID NEGATIVE)
- Structurally validated: perfect nesting ≥0.95, zero fragmentation, monotonic refinement
- **Calibration FAILS:** thresholds too aggressive for TF-IDF sparse signal density at 174k
- Level 2 area_purity ~0.134 < 0.15 threshold
- Hierarchical_v1 (2-level) PASSES — negative result preserved

### ❌ Calibration Protocol — FAILS on TF-IDF (VALID NEGATIVE)
- Thresholds too aggressive for signal density
- Negative result frozen and preserved

### 🧊 Dense Embedding Integration Contract v34 — FROZEN
**4 Complementary Views defined with acceptance criteria:**

| View | Criterion | Evidence (144k/22-yr) | Status |
|------|-----------|----------------------|--------|
| Citation Heritage | AUC > 0.75 | cp64: 0.792, cp768: 0.795 | ✅ PASSED |
| Cross-Lingual (Sachverhalt) | same_branch > 0.20 | cp64: 0.282 | ✅ PASSED |
| Cross-Lingual (Dispositiv) | same_branch > 0.10 | cp64: 0.150 | ✅ PASSED |
| Cross-Lingual (Erwaegungen) | same_branch > 0.10 | cp64: 0.094 | ❌ FAILED — EXCLUDED |
| Linear Hybrid Complement | PASS adversarial at w=0.3–0.4 | JP 0.61–0.67 | ✅ PASSED (below TF-IDF baseline) |

**Required dense modes:** `center_projected_64dim`, `center_projected_128dim`, `center_projected_768dim`

### ✅ Scale Extrapolation — VALIDATED at 144k Checkpoint
- Fine branch purity ~0.97
- Improvement rate: 0.48–0.65 (branch) / 0.75–0.76 (area)
- Strict nesting ≥0.99
- Fine singletons ~4–5%

### 🔒 NESTING_METRIC_DEFECT_v1 — ENFORCED
- Strict parent-child label matching enforced
- All nesting ≥0.99 claims require explicit scope annotation (scale, representation, config)

---

## Blockers — Unchanged (Upstream Dependencies)

| Blocker | Owner | Required For |
|---------|-------|--------------|
| BGE/bger ID mapping production | Corpus lane | Legal-distance 174k dense embeddings |
| Parquet generation 2022–2026 (29,520 decisions) | Corpus lane | Legal-distance 174k dense embeddings |
| Section extraction at 174k scale (Sachverhalt/Erwaegungen/Dispositiv) | Corpus lane | Cross-lingual evaluation density |
| 174k dense embeddings computation | Legal-distance lane | Dense integration per frozen contract |

---

## Recommendation

**`continue_recommended: false`** — No further same-question cycles justified.

All discriminating experiments for factory direction v34/v35 question **COMPLETE**:
1. TF-IDF hierarchical production modes → FINALIZED ✅
2. Dense embedding integration contract → FROZEN ✅
3. Multi-level recursive protocol → NEGATIVE (valid) ✅
4. Calibration → NEGATIVE (valid) ✅
5. Scale extrapolation → VALIDATED ✅
6. Nesting metric defect → ENFORCED ✅

**Next action:** Factory Director to resume corpus lane for data blockers. Fractal-map lane will resume only when legal-distance delivers 174k dense embeddings meeting all 4 complementary view acceptance criteria.

---

## Evidence Preservation

All negative results preserved per Research Protocol §5 and Constitution §5, §6:
- Calibration FAILS on TF-IDF
- Erwaegungen cross-lingual FAILS (0.094 < 0.10)
- v18 coarse hierarchy NEGATIVE (max purity 0.65 < 0.7)
- True OOS JuristPref ceiling ~0.53 < 0.7 factory target
- Dense embeddings FAIL jurist gate at ALL scales (JP 0.05–0.43)
- Linear hybrids PASS adversarial but BELOW TF-IDF baseline (JP 0.61–0.67 vs 0.78–0.79)

---

*Fresh independent re-verification completed by fractal-map lane researcher per Research Protocol and Factory Direction v35. GitHub Run: 38002296609*