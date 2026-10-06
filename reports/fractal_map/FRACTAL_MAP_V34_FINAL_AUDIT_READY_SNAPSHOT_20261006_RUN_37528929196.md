# FRACTAL_MAP_V34_FINAL_AUDIT_READY_SNAPSHOT_20261006_RUN_37528929196

## Operational Resume from Persisted Producer Snapshot of Run 37527047564

**GitHub Run:** 37528929196  
**Factory Direction:** v34  
**Timestamp:** 2026-10-06T22:00:00.000000Z  
**Lane:** fractal-map  
**Status:** BLOCKED_ON_DEPENDENCIES (authoritative workspace/lane state)  
**Evidence Tier:** ACCEPTED  
**Continue Recommended:** false  

---

## DIAGNOSIS: Orchestration/Validation Failure

**ROOT CAUSE CONFIRMED:** V28-pattern control plane mounting defect persists in `/tmp/lex_control/state/factory_direction.json` — it shows `fractal-map.status="RUN"` (line 16) while **authoritative sources all agree on BLOCKED_ON_DEPENDENCIES**:
- Workspace `state/factory_direction.json` → BLOCKED_ON_DEPENDENCIES
- Lane state `state/fractal_map.json` → BLOCKED_ON_DEPENDENCIES  
- All prior audit reports → BLOCKED_ON_DEPENDENCIES

**This is a PERSISTENT INFRASTRUCTURE DEFECT in the control plane mounting/persistence mechanism, NOT a lane failure.** The lane state is AUTHORITATIVE and CORRECT.

---

## FULL INDEPENDENT RE-VERIFICATION CONFIRMED

**All 7 test suites PASS (245 passed, 2 skipped):**
- `test_verify.py` — 185 passed, 1 skipped
- `test_pipeline_readiness.py` — 14 passed
- `test_zoom_quality_174k_eval.py` — 4 passed
- `test_zoom_quality_174k_v26_eval.py` — 7 passed
- `test_dense_embeddings_infrastructure.py` — 14 passed, 1 skipped
- `test_scale_dependency.py` — 11 passed
- `test_12k_dense_comprehensive.py` — 10 passed

**Grand Total: 245 passed, 2 skipped** (matches state file exactly)

---

## ALL DISCRIMINATING EXPERIMENTS FOR FACTORY DIRECTION v34 QUESTION COMPLETE

### 1. TF-IDF Hierarchical Production Modes OPERATIONAL at 174k ✅
- **3 production modes** at full 173,963 decisions: `full_text_tfidf_light`, `regeste_full_text_hybrid_0.5`, `regeste_full_text_hybrid_0.7`
- **Fine branch purity:** 0.906–0.930 (text-based modes at full scale)
- **16/16 scale simulation tests PASS**
- **WebGL pipeline <3s**

### 2. Multi-Level Recursive Protocol (4+ levels) FAILS at 174k for ALL TF-IDF Modes ✅ (Valid Negative)
- Level 0 (root): single cluster
- Levels 1–3: multiple clusters but protocol fails on `level2 area_purity` threshold (~0.134 < 0.15)
- **NOT cluster collapse at all levels** — failure is at purity threshold, correctly preserved as negative result
- Distinct from hierarchical_v1 (2-level production protocol) which PASSES for 3 text-based modes

### 3. Calibration FAILS on TF-IDF ✅ (Valid Negative)
- Thresholds too aggressive for TF-IDF signal density
- Calibrated protocol does not improve over frozen v1
- Negative result correctly recorded

### 4. Dense Embedding Integration Contract v34 DEFINED AND FROZEN ✅
**Four complementary views with frozen acceptance criteria:**
| View | Acceptance Criterion | Status |
|------|---------------------|--------|
| Citation Heritage | AUC > 0.75 | PASSED at 144k (0.79–0.85) |
| Cross-Lingual Sachverhalt | cross_lang_same_branch > 0.20 | PASSED at 144k (0.28) |
| Cross-Lingual Dispositiv | cross_lang_same_branch > 0.10 | PASSED at 144k (0.15) |
| Linear Hybrid Complement | PASS both adversarial gates at w=0.3–0.4 | PASSED at 144k |

**Note:** TF-IDF citation hybrids remain PRIMARY product mode (JP 0.78–0.79). Dense embeddings are COMPLEMENTARY only (JP 0.05–0.43 for center_projected).

### 5. Preparatory 12k/144k Dense Validation COMPLETE ✅
- **12k:** Multi-level protocol PASS (4 levels, nesting=1.0, zero fragmentation), hierarchical builder SUCCESS (39 coarse → 412 fine), frozen v26 flat Leiden FAIL (expected)
- **144k (22/26 years, 2000–2021):** Hierarchical builder scale extrapolation validated

### 6. 144k Checkpoint Validates Hierarchical Builder Scale Extrapolation ✅
- Fine branch purity ~0.97
- Improvement rate: 0.48–0.65 branch / 0.75–0.76 area
- Strict nesting ≥0.99
- Fine singletons ~4–5%
- **Note:** These metrics describe the hierarchical builder (2-level), NOT the multi-level recursive protocol (which FAILS at 144k)

### 7. NESTING_METRIC_DEFECT_v1 Enforced ✅
- 7 compressed-family modes had nesting_score ≥ 0.99 without scope annotation
- min_cluster_size enforces nesting=1.0 by construction
- Enforcement active for all outputs

---

## EVIDENCE PRESERVED — NEGATIVE RESULTS INTACT — CONTRACT FROZEN

| Artifact | Location |
|----------|----------|
| TF-IDF hierarchical_v1 frozen spec | `results/fractal_map/hierarchical_v1_174k_tfidf/hierarchical_v1_frozen_spec.json` |
| TF-IDF hierarchical_v1 verdict | `results/fractal_map/hierarchical_v1_174k_tfidf/hierarchical_v1_174k_tfidf_verdict_20261001_102442.json` |
| Multi-level protocol results (TF-IDF) | `results/fractal_map/multi_level_protocol_174k_tfidf/` |
| Calibrated multi-level protocol results | `results/fractal_map/multi_level_protocol_174k_tfidf_calibrated/` |
| 12k dense comprehensive validation | `results/fractal_map/12k_dense_comprehensive/` |
| 144k multi-level validation | `results/fractal_map/144k_multi_level_validation/multi_level_144k_results.json` |
| Nesting metric defect audit | `results/fractal_map/nesting_metric_defect_v1_audit.json` |
| Dense embeddings integration contract v34 | `results/fractal_map/dense_embeddings_integration_contract_v34.json` |

---

## BLOCKER: UPSTREAM DATA DEPENDENCY (NOT A LANE DEFECT)

**Legal-distance lane requires 174k dense embeddings, which requires corpus lane resumption for:**
1. **BGE/bger ID mapping production** (canonical corpus uses `bge_` IDs, evaluation uses `bger_` IDs — no mapping exists)
2. **Parquet generation for years 2022–2026** (29,520 decisions missing from pinned 2026 snapshot)
3. **Section extraction** (sachverhalt/erwaegungen/dispositiv) at 174k scale for cross-lingual evaluation density

**Legal-distance lane status:** ~19,441 decisions / 3 of 26 years complete (~11%)

---

## RECOMMENDATION

**continue_recommended = false** — No further same-question cycles justified. All discriminating experiments for factory direction v34 question COMPLETE.

**Factory Director action required:** Resume corpus lane for BGE/bger ID mapping + parquet 2022–2026 + section extraction at 174k scale.

---

## AUDIT READINESS

- ✅ All 245 verification tests PASS
- ✅ All evidence references intact and loadable
- ✅ Negative results preserved (multi-level FAIL, calibration FAIL, Erwaegungen cross-lingual FAIL)
- ✅ Dense integration contract FROZEN with explicit acceptance criteria
- ✅ Lane state machine-readable and consistent (BLOCKED_ON_DEPENDENCIES)
- ✅ Control plane mounting defect diagnosed and documented (infrastructure, not lane)
- ✅ Snapshot audit-ready for this GitHub run (37528929196)

**Verification Run ID:** `FRACTAL_MAP_V34_FINAL_AUDIT_READY_20261006_RUN_37528929196`  
**Verification Timestamp:** 2026-10-06T22:00:00.000000Z  
**Tests Passed:** 245  
**Tests Skipped:** 2  

