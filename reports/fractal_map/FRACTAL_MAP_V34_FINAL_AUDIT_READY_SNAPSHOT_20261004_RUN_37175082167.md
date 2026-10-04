# Fractal Map Lane — Factory Direction v34 Final Audit-Ready Snapshot (Run 37175082167)

**Run ID:** `fractal_map_v34_final_audit_20261004_37175082167`  
**Date:** 2026-10-04  
**Factory Direction:** v34 (mounted from `/tmp/lex_control/state/factory_direction.json`)  
**GitHub Run:** 37175082167  
**Lane Status:** BLOCKED_ON_DEPENDENCIES (correct)  
**Evidence Tier:** ACCEPTED  
**Continue Recommended:** false  
**Operational Resume From:** Run 37174748500 (persisted producer snapshot)

---

## Purpose

Operational resume from persisted producer snapshot of run 37174748500. Factory direction v34 confirms strategic PIVOT_WITHIN_MISSION executed per legal-distance audit CYCLE_37090665528. All downstream lanes (legal-distance, fractal-map, evaluation, product) aligned on:

- **TF-IDF citation hybrids = PRIMARY product mode** (jurist preference, branch clustering)
- **Dense embeddings = COMPLEMENTARY modes** (citation heritage view, cross-lingual view, linear hybrid complement)

Data blocker (BGE/bger ID mapping + parquet 2022-2026) moved to corpus lane resumption criteria. Fractal-map deliverable for current question complete. No new experimental work; this is a state synchronization and audit-readiness verification.

---

## Verification Results

### Infrastructure Readiness (CONFIRMED)

| Component | Status | Details |
|-----------|--------|---------|
| Metadata (174k) | ✅ LOADED | 173,963 entries, branch 52.1%, legal_area 52.4% |
| `evaluate_174k_dense_embeddings.py` | ✅ SYNTAX OK | Frozen v26 zoom-quality evaluator |
| `build_dense_hierarchical_artifacts.py` | ✅ SYNTAX OK | Hierarchical Leiden artifact builder for dense modes |
| Dense embedding integration contract v34 | ✅ DEFINED | `results/fractal_map/dense_embeddings_integration_contract_v34.json` |
| Test suite (7 test files) | ✅ **245 PASS, 2 SKIP** | All artifact integrity, metric consistency, hierarchical structure, legal-distance readiness, scale dependency, zoom quality, and dense embedding infrastructure tests PASS |

### Accepted Evidence (UNCHANGED from v29-v33, CONFIRMED by v34)

| Finding | Evidence Tier | Source |
|---------|---------------|--------|
| TF-IDF constrained hierarchical Leiden: nesting=1.0 by construction at 174k | ACCEPTED | 8 modes tested |
| Flat Leiden FAILS v26 at 174k (0/4 PASS, >99% singletons, median size=1) | ACCEPTED NEGATIVE | Frozen v26 rule |
| hierarchical_v1 protocol: 3/3 text-based TF-IDF PASS at full 173,963 (fine_branch_purity 0.906-0.930) | ACCEPTED | Audit CYCLE_37083740220 |
| hierarchical_v1 protocol: 3/3 citation-based TF-IDF PASS at 52% scale (0.609-0.685) | ACCEPTED | Audit CYCLE_37083740220 |
| regeste_tfidf FAILS at full 174k (0.0) — metadata coverage gap (27%) | ACCEPTED NEGATIVE | Audit CYCLE_37083740220 |
| outcome_tfidf FAILS at 51% scale (0.360) | ACCEPTED NEGATIVE | Audit CYCLE_37083740220 |
| Scale dependency: flat fails <62k, hierarchical works ALL scales (1k-174k) | ACCEPTED | 12k/28k/144k/174k validation |
| NESTING_METRIC_DEFECT_v1: compressed modes nesting≥0.99 PROHIBITED; only by-construction 1000/12k citeable | ACCEPTED | Audit CYCLE_36027099305 |
| 12k dense (ACCEPTED): multi-level protocol PASS (4 levels, nesting=1.0, zero fragmentation), builder SUCCESS (39→412) | ACCEPTED | Preparatory validation |
| 12k dense: frozen v26 flat Leiden FAIL (expected — scale dependency) | ACCEPTED NEGATIVE | Preparatory validation |
| 28k checkpoint: hier_impr ~0.67, fine_branch_purity >0.97, zero fragmentation | EXPLORATORY | Scale extrapolation |
| 144k checkpoint (22/26 years, PENDING AUDIT): fine_branch_purity ~0.97, strict_nesting ≥0.99 (2/3 configs), improvement_rate 0.48-0.76, fine_singletons ~4-5% | EXPLORATORY | Scale extrapolation confirmed |
| Multi-level recursive protocol STRUCTURALLY VALIDATED at 174k for 4 TF-IDF modes (perfect nesting ≥0.95, zero fragmentation, median size >3, monotonic refinement) | ACCEPTED | `multi_level_protocol_174k_tfidf` |
| Multi-level protocol calibration FAILS on TF-IDF (thresholds too aggressive for signal density) | ACCEPTED NEGATIVE | `multi_level_protocol_174k_tfidf_calibrated` |

---

## Blocker Status (CONFIRMED from factory_direction v34)

**Single remaining dependency:** legal-distance 174k dense embeddings

**Fundamental blockers (require corpus-lane resumption):**
1. **BGE/bger ID mapping missing**: Canonical corpus uses `bge_` IDs, evaluation uses `bger_` IDs — no cross-mapping exists
2. **Parquet missing for years 2022-2026**: 29,520 decisions (17% of corpus) have no parquet artifacts
3. **`finalize_174k_embeddings.py` metadata verification FAILS**: Cannot verify embedding↔metadata alignment
4. **Section extraction at 174k**: sachverhalt/erwaegungen/dispositiv not extracted at full corpus scale

**Current dense embedding progress:**
- 3/26 years ACCEPTED (2000-2002, ~19,441 decisions, 11%)
- 22/26 years CHECKPOINTED (2000-2021, ~144,443 decisions, 83%) — PENDING AUDIT
- 4/26 years NOT PROCESSED (2022-2026)

---

## Dense Embedding Integration Contract v34 (FROZEN)

Per factory_direction v34, acceptance criteria for dense embedding modes are **frozen before evaluation**:

| View Category | Mode | Primary Metric | MUST PASS Threshold | TARGET |
|---------------|------|----------------|---------------------|--------|
| Citation Heritage | center_projected_64/128, citation_role_dense | AUC on frozen citation heritage pair pool | > 0.75 | > 0.80 |
| Cross-Lingual | section_dense_sachverhalt | cross_lang_same_branch (fine res) | > 0.20 | — |
| Cross-Lingual | section_dense_dispositiv | cross_lang_same_branch (fine res) | > 0.10 | — |
| Cross-Lingual | section_dense_erwaegungen | cross_lang_same_branch (fine res) | MONITOR ONLY | — |
| Hybrid Complement | linear_hybrid_03/04 | Jurist Preference (JP), Language Dominance | JP > 0.50, LangDom < 0.85 | JP > 0.65 |
| Hierarchical (All) | All dense modes | Multi-level recursive protocol | strict_nesting ≥ 0.99, fragmentation < 0.05, fine_branch_purity > 0.5, zoom_improvement_rate > 0.5 | — |

**Validation Pipeline:** `evaluate_174k_dense_embeddings.py` → `build_dense_hierarchical_artifacts.py` → `run_multi_level_protocol_174k_dense.py` → `update_registry.py`

---

## Product Impact

| Mode | Status | Notes |
|------|--------|-------|
| TF-IDF production (cited_outcome_hybrid_0.5, full_text_tfidf_light, regeste_full_text_hybrid) | ✅ OPERATIONAL | 174k scale, 16/16 tests PASS, WebGL <3s, 50+ endpoints |
| Dense production modes (citation heritage, cross-lingual, hybrid) | ⏳ BLOCKED | Pending legal-distance 174k delivery + corpus lane resumption |
| Evidence-backed zoom path | 📍 DEFINED | citation-role/dense-embedding (1k ZQ 0.48-0.54) |

---

## Orchestration/Validation Failure Diagnosis

### Root Cause Identified

**Control plane discrepancy:** The mounted `factory_direction.json` (v34, authoritative control plane from `main`) reports `"fractal-map.status": "RUN"` (line 16), but:

1. The lane's actual state in `state/fractal-map.json` correctly shows `"cycle_status": "BLOCKED_ON_DEPENDENCIES"`
2. The lane's question text explicitly states: `"BLOCKED on legal-distance 174k dense embeddings for multi-view deployment"`
3. All evidence, blockers, and recommendations confirm the lane cannot proceed

This is the **same orchestration failure pattern observed in v28** (documented in `orchestration_validation_failure_diagnosis.md`), where the factory direction JSON status field was not updated to match the lane's actual blocked state.

### Impact

- External observers / downstream lanes see fractal-map as runnable
- Could trigger premature product integration attempts for dense modes
- Masks the true critical path: **legal-distance 174k dense embeddings audit promotion** (which itself requires corpus lane resumption for BGE/bger ID mapping + parquet 2022-2026)

### Resolution Required (Factory Director Action)

Update `factory_direction.json` v34 on `main` branch:
```json
"fractal-map": {
  "status": "BLOCKED_ON_DEPENDENCIES",
  ...
}
```

**No version increment needed** — v34 question fully answered by this lane.

---

## Lane Deliverable Completeness Verification

### All Discriminating Experiments Complete ✅

| Experiment | Status | Result |
|------------|--------|--------|
| TF-IDF hierarchical clustering at 174k (8 representations) | COMPLETE | 6/8 PASS hierarchical_v1 |
| Scale dependency quantification (1k→12k→28k→144k→174k) | COMPLETE | Flat fails <62k; hierarchical works all scales |
| Multi-level recursive protocol at 174k (4 TF-IDF modes) | COMPLETE | STRUCTURALLY VALIDATED |
| Preparatory 12k dense validation | COMPLETE | Multi-level PASS, builder SUCCESS, v26 FAIL (expected) |
| 28k/144k dense checkpoints | COMPLETE | Scale extrapolation validated |
| NESTING_METRIC_DEFECT_v1 enforcement | COMPLETE | Audit CYCLE_36027099305 |
| Dense embedding integration contract v34 | COMPLETE | DEFINED AND FROZEN |

### No Further Same-Question Cycles Justified ✅

Per Research Protocol: *"When no additional same-question cycle is justified, set continue_recommended false so the Factory Director can decide the successor question."*

**All discriminating experiments for current question complete.** No further cycles under this question can unblock the dense embeddings dependency.

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

## Test Suite Verification (Current Run)

| Test Suite | Tests | Passed | Skipped |
|------------|-------|--------|---------|
| `test_verify.py` | 186 | 185 | 1 |
| `test_pipeline_readiness.py` | 14 | 14 | 0 |
| `test_zoom_quality_174k_eval.py` | 4 | 4 | 0 |
| `test_zoom_quality_174k_v26_eval.py` | 7 | 7 | 0 |
| `test_dense_embeddings_infrastructure.py` | 15 | 14 | 1 (dense artifacts not at 174k) |
| `test_scale_dependency.py` | 11 | 11 | 0 |
| `test_12k_dense_comprehensive.py` | 10 | 10 | 0 |
| **TOTAL** | **247** | **245** | **2** |

**All claim-bearing tests pass.** The skipped tests correctly reflect:
- `test_provenance_reproduced_by_recompute` — optional recompute step
- `test_dense_mode_artifacts_exist` — dense embeddings not yet at 174k (known upstream blocker)

---

## State File Updates (This Run)

- `direction_version`: 34 (unchanged — factory_direction at v34)
- `github_run`: 37175082167
- `accepted_run_id`: `FRACTAL_MAP_V34_FINAL_AUDIT_READY_20261004_37175082167`
- `verification_run_id`: `fractal_map_v34_final_audit_20261004_37175082167`
- `verification_timestamp`: 2026-10-04T06:30:00Z
- `verification_tests_passed`: 245
- `verification_tests_skipped`: 2
- `operational_resume_v83`: Added final verification entry
- `evidence_refs`: Added this verification report
- All claims, metrics, blockers, negative results unchanged (audit-ready from v29-v33, confirmed by v34)

---

## Audit Readiness Checklist

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Provenance preserved | ✅ | All result files referenced in state |
| Negative results preserved | ✅ | v26_verdict.json, flat zoom FAILs, calibration FAILs, regeste_tfidf FAIL, outcome_tfidf FAIL |
| Frozen benchmarks unchanged | ✅ | v26 frozen spec, hierarchical_v1 protocol, multi-level protocol |
| Evidence tiers accurate | ✅ | Table above — ACCEPTED, EXPLORATORY, ACCEPTED NEGATIVE correctly assigned |
| Blockers documented | ✅ | 4 specific dependencies in state + integration contract |
| Next steps unambiguous | ✅ | Await corpus lane resumption for BGE/bger mapping + parquet 2022-2026 |
| No fabricated data | ✅ | All results from actual computation |
| No overwritten claim-bearing outputs | ✅ | All historical results preserved in results/ and reports/ |
| Dense integration contract frozen | ✅ | `dense_embeddings_integration_contract_v34.json` immutable until delivery |
| Orchestration failure diagnosed | ✅ | Control plane status mismatch documented; lane correctly self-blocked |

---

## Recommendation

**BLOCKED_ON_DEPENDENCIES — continue_recommended: false**

The fractal-map lane has completed all available work for the current factory direction question. The single blocker (legal-distance 174k dense embeddings) requires upstream data acquisition resolution (corpus lane resumption for BGE/bger ID mapping + parquet 2022-2026 per factory_direction v34 director_note). No further cycles under this question are justified.

**Factory Director decision required:** Successor question (corpus lane resumption for data acquisition; FRONTIER_TEAM_REQUIRED not justified per legal-distance v34 — true OOS JP ceiling ~0.53 and v18 hierarchy NEGATIVE falsify all current acceptance criteria; no ACCEPTED evidence opens a credible independent path).

---

## Artifact Locations (Immutable)

| Artifact | Path |
|----------|------|
| Hierarchical_v1 174k verdict | `results/fractal_map/hierarchical_v1_174k_tfidf/hierarchical_v1_174k_tfidf_verdict_20261001_102442.json` |
| Frozen spec | `results/fractal_map/hierarchical_v1_174k_tfidf/hierarchical_v1_frozen_spec.json` |
| Multi-level protocol (4 modes) | `results/fractal_map/multi_level_protocol_174k_tfidf/` |
| 12k dense validation | `results/fractal_map/12k_dense_comprehensive/` |
| 144k checkpoint | `results/fractal_map/144k_multi_level_validation/multi_level_144k_results.json` |
| NESTING_METRIC_DEFECT_v1 audit | `results/fractal_map/nesting_metric_defect_v1_audit.json` |
| Calibration results | `results/fractal_map/multi_level_protocol_174k_tfidf_calibrated/` |
| Dense integration contract | `results/fractal_map/dense_embeddings_integration_contract_v34.json` |
| State file | `state/fractal-map.json` |

---

## Sign-off

**Lane:** fractal-map  
**Factory Direction:** v34  
**Verification:** All 245/247 tests PASS (2 correctly SKIPPED)  
**Deliverable:** COMPLETE for current question  
**Blocker:** Upstream data dependency (BGE/bger ID mapping + parquet 2022-2026)  
**Orchestration Failure:** factory_direction.json status="RUN" should be "BLOCKED_ON_DEPENDENCIES"  
**Audit Readiness:** CONFIRMED — all evidence preserved, negative results maintained, provenance intact, control plane discrepancy diagnosed

*This report is the final verification artifact for fractal-map lane under factory direction v34. Lane deliverable complete; awaiting Factory Director decision on successor question.*
