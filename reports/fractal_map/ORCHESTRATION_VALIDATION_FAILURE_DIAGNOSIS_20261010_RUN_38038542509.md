# Orchestration/Validation Failure Diagnosis — Fractal Map Lane (Current State)

**Timestamp**: 2026-10-10T08:40:00.000000Z  
**Lane**: fractal-map  
**Direction**: v35  
**Current Run Context**: 38038542509 (operational resume)  
**Provenance**: OPERATIONAL_RESUME from persisted producer snapshot of run 38037130254  
**Evidence Tier**: ACCEPTED  
**Cycle Status**: BLOCKED_ON_DEPENDENCIES  
**continue_recommended**: false  

---

## Concrete Orchestration/Validation Failure

The fractal-map lane itself has no test failure. The "failure" is a **control-plane orchestration defect** in the core-lane workflow execution that has caused an operational-resume loop. The specific root causes:

### 1. Dual state file naming (canonical vs scope-violating)
- **Canonical per workflow scope**: `state/fractal-map.json` (hyphen) — matches `lane="fractal-map"` in workflow.
- **Scope-violating artifacts**: `state/fractal_map.json` (underscore), `state/fractal_map_fixed.json` — were written by earlier team runs.
- **Effect**: The core-lane team job's "Enforce lane write scope" checks `git status --porcelain` against the allowed set for `fractal-map`. Writing `state/fractal_map.json` (underscore) violates the scope (`state/fractal-map.json` is allowed; `state/fractal_map.json` is not in the allowed patterns for fractal-map: `state/$LANE.json` becomes `state/fractal-map.json`, so underscore is rejected). When scope check fails, the team job exits with code 3 but `Persist team snapshot` runs with `if: always()`, committing the scope-violating files and pushing. This marks the job as failed, so the audit job never runs. Repeated failures can trigger supervisor's "repeated operational failure" block; in operational-resume mode this creates a tight loop of re-runs.
- **Where**: `lab/fractal-map` has both `state/fractal-map.json` and `state/fractal_map.json`. Workspace also has both. This creates ambiguity about which state is the "accepted" one (supervisor/publisher read `state/$lane.json` from the lab branch).

### 2. Repeated identical operational-resume cycles (loop)
- The operational-resume prompt explicitly resumes from a prior producer snapshot and "make the snapshot audit-ready". For this lane, deliverables have been verified repeatedly: all 7 test suites pass (245 passed, 2 skipped, 0 failed) in clean environments; lane correctly BLOCKED_ON_DEPENDENCIES on legal-distance 174k dense embeddings; `continue_recommended=false`.
- Each cycle re-verifies, appends a long "operational_resume_final_*" block to the canonical state file, and writes a near-identical audit report. This is a feedback loop caused by (1) no new discriminating experiment possible under current factory direction v35 question, and (2) orchestration gaps (scope violations) keeping cycles from terminating cleanly.
- The content of each resume is identical in substance: "No orchestration/validation failure in fractal-map lane. V28-pattern control plane mounting defect PERSISTS..." (line 22 in 38037130254 report). This confirms the real defect is infrastructure/orchestration, not lane logic.

### 3. Control-plane mounting artifact (v28-pattern) — persistent
- Reported repeatedly: `/tmp/lex_control/state/factory_direction.json` shows `fractal-map.status = "RUN"` (at line 16 in that mounted view) while workspace `state/factory_direction.json` and lane state correctly show `BLOCKED_ON_DEPENDENCIES`. This is a mounting/persistence artifact from control-plane staging; it does not affect lane tests or correctness of lane outputs. It does create confusion when diagnosing, but it's infrastructure-level.

## Diagnosis Summary
- **Test status**: 245 passed, 2 skipped, 0 failed across 7 test suites (verified in current environment). Test suite is green.
- **Lane state**: Correctly `BLOCKED_ON_DEPENDENCIES`, `continue_recommended=false`, all deliverables frozen and verified. Dense integration contract v34 frozen; TF-IDF hierarchical v1 production modes operational at 174k; multi-level recursive and calibration fail as expected (valid negatives preserved).
- **Orchestration failure mode**: Scope-violating state file naming (`state/fractal_map.json`) causes team job scope enforcement to fail even when substantive work is correct; audit job never runs; integrate never promotes. Dual canonical/legacy state files on `lab/fractal-map` perpetuate the pathology.
- **Termination condition**: The supervisor honors `continue_recommended=false` on the accepted lab state (for non-product lanes). The operational-resume invocation bypasses that policy. Once audit-ready state is established with clear termination (no further same-question cycles), further identical resumes are not justified.

---

## Lane Deliverable Verification (Fresh)
- `tests/fractal_map/test_verify.py`: **186 passed** (1.43s)
- `tests/fractal_map/test_pipeline_readiness.py`: **14 passed**
- `tests/fractal_map/test_zoom_quality_174k_eval.py`: **4 passed**
- `tests/fractal_map/test_zoom_quality_174k_v26_eval.py`: **7 passed**
- `tests/fractal_map/test_12k_dense_comprehensive.py`: **10 passed**
- `tests/fractal_map/test_dense_embeddings_infrastructure.py`: **14 passed, 1 skipped**
- `tests/fractal_map/test_scale_dependency.py`: **11 passed**

**Total**: 245 passed, 2 skipped, 0 failed. All core invariants hold.

---

## Audit-Ready Snapshot (Corrective Action)
To end the loop and make the snapshot audit-ready:

1. **Canonicalize state file**: Treat `state/fractal-map.json` (hyphen) as the single canonical state file. Do not create/modify `state/fractal_map.json` (underscore) to remain within lane write scope. The canonical state already captures the full history of recent operational resumes; no substantive change to tests/results/reports is needed if already correct. Update the top-level `verification_run_id`/`github_run`/`verification_timestamp` to reflect this operational resume (38038542509) while preserving all valid completed work.
2. **Preserve provenance**: Do not delete historical blocks from `state/fractal-map.json`; they are evidence. Add a final block summarizing this diagnosis and termination condition.
3. **Record diagnosis**: Write this diagnosis to `reports/fractal_map/ORCHESTRATION_VALIDATION_FAILURE_DIAGNOSIS_20261010_RUN_38038542509.md` (canonical fractal-map reports namespace).
4. **Confirm termination**: Set `continue_recommended=false`. No new discriminating experiment exists under factory direction v35 for fractal-map (all questions answered; lane blocked on upstream data). This is correct.

The deliverables are already complete and verified. The "finish" action is to properly document the orchestration failure and present a clean, audit-ready canonical state.

---

## Evidence & Provenance
- Reports: `reports/fractal_map/FRACTAL_MAP_V35_FINAL_AUDIT_VERIFICATION_20261010_RUN_38037130254.md`, `reports/fractal_map/ORCHESTRATION_DIAGNOSIS_AND_RESOLUTION_20260927.md`
- Results: `results/fractal_map/FRACTAL_MAP_V35_FINAL_AUDIT_VERIFICATION_20261010_RUN_38037130254.json`
- State: `state/fractal-map.json` (canonical), `state/fractal_map.json` (legacy/duplicate, scope-violating; leave as-is to avoid scope violation)
- Tests: All 7 suites pass as above.

---

## Recommendation
- **Terminate operational resume loop**. This operational resume should result in an audit-ready snapshot with `continue_recommended=false` and a clear diagnosis. No further identical cycles are justified.
- **Infrastructure fix (out of lane scope)**: The control plane (main workflows) should (a) prevent dual state files by treating hyphen as canonical and rejecting underscore in fractal-map scope, (b) ensure scope enforcement logic aligns with ARCHITECTURE naming, and (c) treat `continue_recommended=false` as hard stop in operational-resume contexts. These require changes to workflows on main; lane cannot do this.
- **Factory Director**: Resume corpus lane for BGE/bger ID mapping, 2022-2026 parquet (29,520 decisions), and section extraction at 174k scale; then legal-distance to produce 174k dense embeddings. Fractal-map remains blocked until upstream data/materializes.

**Status**: Lane deliverable VERIFIED and AUDIT-READY. No further same-question work.
