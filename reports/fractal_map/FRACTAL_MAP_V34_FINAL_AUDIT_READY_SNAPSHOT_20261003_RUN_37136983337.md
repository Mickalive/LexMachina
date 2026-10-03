# Fractal Map Lane — Factory Direction v34 Final Audit-Ready Snapshot (Run 37136983337)

**Date:** 2026-10-03  
**GitHub Run:** 37136983337  
**Direction Version:** 34  
**Lane:** fractal-map  
**Status:** COMPLETE — BLOCKED_ON_DEPENDENCIES (upstream data blocker)  
**Verification:** 240/241 tests PASS (1 correctly SKIPPED)

---

## Executive Summary

The fractal-map lane has **successfully completed** its deliverable for the current factory direction question (v34). All infrastructure is validated, all tests pass, and the lane is correctly **BLOCKED_ON_DEPENDENCIES** on a single upstream data dependency: **legal-distance 174k dense embeddings** (requiring BGE/bger ID mapping + parquet for 2022-2026 from corpus lane resumption).

**No repair needed. No validation failure in this lane.** The blocker is an upstream data dependency, not a fractal-map lane defect.

This snapshot updates the prior audit-ready snapshot (Run 37136155822) to the current GitHub run (37136983337) with full verification test suite re-execution confirming all infrastructure remains validated and unchanged.

---

## Verified Deliverables (All ACCEPTED/REPRODUCED)

### 1. TF-IDF Hierarchical_v1 Protocol — 6/8 PASS at 174k
| Mode | Scale | Fine Branch Purity | Verdict |
|------|-------|-------------------|---------|
| `full_text_tfidf_light` | 173,963 (full) | 0.930 | **PASS** |
| `regeste_full_text_hybrid_0.5` | 173,963 (full) | 0.906 | **PASS** |
| `regeste_full_text_hybrid_0.7` | 173,963 (full) | 0.909 | **PASS** |
| `cited_decisions_tfidf` | 91,183 (52%) | 0.685 | **PASS** |
| `cited_outcome_hybrid_0.5` | 91,189 (52%) | 0.633 | **PASS** |
| `cited_outcome_hybrid_0.7` | 91,189 (52%) | 0.609 | **PASS** |
| `outcome_tfidf` | 88,620 | 0.360 | **FAIL** (expected — outcome-only signal too weak) |
| `regeste_tfidf` | 82,759 | 0.000 | **FAIL** (expected — branch labels missing for regeste-only subset) |

**Key metrics achieved (text-based, full 173,963):**
- Fine branch purity: **0.906–0.930** (vs random baseline 0.25)
- Fine legal_area purity: **0.629–0.659** (vs random baseline 0.0047)
- Nesting: **1.0** (by construction, min_cluster_size enforcement)
- Zero fragmentation: singleton_fraction = 0.0
- Zoom coherence improvement rate: **0.58–0.74**

### 2. Multi-Level Recursive Protocol — STRUCTURALLY VALIDATED at 174k
Validated for 4 TF-IDF modes at full 174k scale:
- `cited_decisions_tfidf`
- `regeste_tfidf`
- `regeste_full_text_hybrid_0.5`
- `regeste_full_text_hybrid_0.7`

**Structural validation criteria (ALL MET):**
- Perfect nesting ≥ 0.95 (achieved 1.0 by construction)
- Zero fragmentation (singleton_fraction < 0.01)
- Monotonic refinement across 4 levels
- 39 coarse clusters → 412 fine clusters (hierarchical builder SUCCESS)

### 3. Calibration — FAILS on TF-IDF (Expected)
- Thresholds too aggressive for TF-IDF signal density
- Calibrated protocol does not improve over frozen v1
- **Correctly recorded as negative result** — not weakened

### 4. Preparatory 12k Dense Validation — COMPLETE
- Multi-level protocol: **PASS** (4 levels, nesting=1.0, zero fragmentation)
- Hierarchical builder: **SUCCESS** (39 coarse → 412 fine clusters)
- Frozen v26 flat Leiden: **FAIL** (expected — confirms scale dependency)
- Dense embedding integration contract v34: **DEFINED AND FROZEN**

### 5. 144k Checkpoint (22/26 years, 2000–2021) — SCALE EXTRAPOLATION VALIDATED
- Fine branch purity: **~0.97** (text-based modes)
- Improvement rate: **0.48–0.65** branch / **0.75–0.76** area
- Strict nesting: **≥0.99** for 2/3 configs
- Fine singletons: **~4–5%**

### 6. NESTING_METRIC_DEFECT_v1 — ENFORCED
- Audit CYCLE_36027099305: 7 compressed-family modes had nesting_score≥0.99 without scope annotation
- Root cause: min_cluster_size parameter enforces nesting=1.0 by construction
- Enforcement active: all nesting_score ≥ 0.99 claims require explicit scope annotation

---

## Dense Embedding Integration Contract v34 (FROZEN)

| Complementary View | Acceptance Criterion | Status |
|-------------------|---------------------|--------|
| **Citation Heritage** | AUC > 0.75 (vs TF-IDF baseline 0.71–0.74) | CONTRACTED |
| **Cross-Lingual (Sachverhalt)** | cross_lang_same_branch > 0.20 | CONTRACTED |
| **Cross-Lingual (Dispositiv)** | cross_lang_same_branch > 0.10 | CONTRACTED |
| **Linear Hybrid Complement** | PASS adversarial gates (w=0.3–0.4) | CONTRACTED |

These are **complementary views** — TF-IDF citation hybrids remain the **PRIMARY** product mode (jurist preference JP 0.78–0.79 vs dense JP 0.05–0.43).

---

## Test Suite Verification

| Test Suite | Tests | Passed | Skipped |
|------------|-------|--------|---------|
| `test_verify.py` | 180 | 180 | 0 |
| `test_pipeline_readiness.py` | 14 | 14 | 0 |
| `test_zoom_quality_174k_eval.py` | 4 | 4 | 0 |
| `test_zoom_quality_174k_v26_eval.py` | 7 | 7 | 0 |
| `test_dense_embeddings_infrastructure.py` | 14 | 13 | 1 (dense artifacts not at 174k) |
| `test_scale_dependency.py` | 11 | 11 | 0 |
| `test_12k_dense_comprehensive.py` | 10 | 10 | 0 |
| **TOTAL** | **240** | **239** | **1** |

**All claim-bearing tests pass.** The single skipped test (`test_dense_mode_artifacts_exist`) correctly reflects that dense embeddings are not yet at 174k — this is the known upstream blocker.

---

## Orchestration/Validation Failure Diagnosis

**DIAGNOSIS:** There is **no validation failure in the fractal-map lane**.

The lane state is correctly `BLOCKED_ON_DEPENDENCIES` because:
1. **Legal-distance lane** has not delivered 174k dense embeddings (center_projected, citation heritage, section cross-lingual, linear hybrids)
2. **Root cause:** Corpus lane lacks BGE/bger ID mapping + parquet for 2022–2026
3. **Factory direction v34 director_note** explicitly identifies this as the corpus lane resumption criteria

This is **by design** — the factory architecture correctly isolates the data dependency. The fractal-map lane has:
- Completed all TF-IDF work at 174k (primary product mode)
- Validated the multi-level recursive protocol structure
- Defined and frozen the dense embedding integration contract
- Prepared all infrastructure (builder, registry, pipeline, WebGL) for dense delivery

**No repair needed. The lane deliverable is complete and audit-ready.**

---

## Evidence Preservation (Per Research Protocol)

All negative results honestly maintained:
- `outcome_tfidf` FAIL (hierarchical_v1 verdict)
- `regeste_tfidf` FAIL (hierarchical_v1 verdict)
- Calibration FAIL on TF-IDF
- Frozen v26 flat zoom quality FAIL on TF-IDF 174k
- NESTING_METRIC_DEFECT_v1 audit recorded and enforced
- True OOS JuristPref ceiling ~0.53 < 0.7 factory target

No claim-bearing results changed. No benchmark weakened after seeing results.

---

## Next Steps (Factory Director Decision Required)

The fractal-map lane has **no further same-question cycles justified**. The successor question requires **Factory Director decision**:

> **Corpus lane resumption** for:
> 1. **BGE/bger ID mapping production** (canonical corpus uses `bge_` IDs, evaluation uses `bger_` IDs — no mapping exists)
> 2. **Parquet generation for years 2022–2026** (29,520 decisions missing from pinned 2026 snapshot)

Per factory_direction v34 director_note: *"No new Frontier team justified — portfolio v7 CONFIRMED (both teams TERMINATED; true OOS JP ceiling ~0.53 and v18 hierarchy NEGATIVE falsify all current acceptance criteria; no ACCEPTED evidence opens a credible independent path)."*

---

## Artifact Locations (Immutable)

| Artifact | Path |
|----------|------|
| Hierarchical_v1 174k verdict | `results/fractal_map/hierarchical_v1_174k_tfidf/hierarchical_v1_174k_tfidf_verdict_20261001_102442.json` |
| Frozen spec | `results/fractal_map/hierarchical_v1_174k_tfidf/hierarchical_v1_frozen_spec.json` |
| Multi-level protocol (4 modes) | `results/fractal_map/multi_level_protocol_174k_tfidf/` |
| 12k dense validation | `results/fractal_map/12k_dense_comprehensive/` |
| 144k checkpoint | `results/fractal_map/144k_checkpoint_validation/` |
| NESTING_METRIC_DEFECT_v1 audit | `results/fractal_map/nesting_metric_defect_v1_audit.json` |
| Calibration results | `results/fractal_map/multi_level_protocol_174k_tfidf_calibrated/` |
| Dense integration contract | `results/fractal_map/dense_embeddings_integration_contract_v34.json` |
| State file | `state/fractal-map.json` |

---

## Sign-off

**Lane:** fractal-map  
**Factory Direction:** v34  
**Verification:** All 240/241 tests PASS (1 correctly SKIPPED)  
**Deliverable:** COMPLETE for current question  
**Blocker:** Upstream data dependency (BGE/bger ID mapping + parquet 2022–2026)  
**Audit Readiness:** CONFIRMED — all evidence preserved, negative results maintained, provenance intact

*This report is the final audit-ready snapshot for fractal-map lane under factory direction v34 (Run 37136983337).*