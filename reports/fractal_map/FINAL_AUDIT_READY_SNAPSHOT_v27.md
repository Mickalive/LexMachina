# FRACTAL-MAP LANE — FINAL AUDIT-READY SNAPSHOT (Factory Direction v27)

**Lane:** fractal-map  
**Factory Direction:** v27  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** COMPLETED  
**Continue Recommended:** false  
**Blocked On:** legal-distance_174k_dense_embeddings (single dependency)  
**Blocked Since:** 2026-09-24T01:55:00Z  
**Resume Guard:** final_audit_complete_v12  
**Accepted Run ID:** 35952633500  
**Latest Verification Run:** 36107024770  
**Date:** 2026-09-25  

---

## EXECUTIVE SUMMARY

The fractal-map lane has **completed all deliverable work** possible with the current TF-IDF representations from legal-distance. The lane is correctly **BLOCKED** on a single external dependency: `legal-distance_174k_dense_embeddings`. No further same-question cycle is justified (`continue_recommended=false`).

**All 195 tests PASS.** The test suite covers:
- 184 artifact integrity, hierarchical Leiden, metric consistency, legal-distance mode integration, compressed ladder, and scale-readiness tests
- 7 v26 174k zoom-quality freeze-protection tests  
- 4 v25 174k zoom-quality freeze-protection tests

All valid completed work is preserved. Negative results are frozen. The snapshot is **audit-ready**.

---

## DELIVERABLES — COMPLETE AND VERIFIED

| # | Deliverable | Status | Key Evidence |
|---|-------------|--------|--------------|
| 1 | **TF-IDF 174k Zoom Quality (v26)** | **COMPLETE** — 0/4 modes PASS (frozen FAIL) | `v26_verdict.json`, `v26_frozen_spec.json` |
| 2 | **v25 Freeze Protection** | **INTACT** — purity bit-equal, zoom claims identical | `test_v25_freeze_protection_intact` |
| 3 | **NESTING_METRIC_DEFECT_v1** | **DOCUMENTED & CORRECTED** — 37/46 modes over-claimed 1.0, honest strict nesting 0.39–0.96 | `compute_honest_nesting_audit.py`, state corrected |
| 4 | **Compressed 5-Level Ladder** | **VALIDATED** — 100% purity delta retention, 22 modes | `compressed_resolution_ladder_all_modes.json` |
| 5 | **Dense Embeddings Readiness** | **COMPLETE** — builder fixed, harness created, verified vs v26 | `evaluate_174k_dense_embeddings.py`, `DENSE_EMBEDDINGS_READINESS_v27.md` |
| 6 | **Citation-Role 174k Validation** | **BLOCKED** — placeholder builds + alignment corruption (0.426 agreement, 1003 duplicate IDs) | `174k_CENSUS_v26_frozen_spec.json`, `alignment_probe_v26.json` |
| 7 | **Product Multi-View Zoom UI** | **VERIFIED** — citation-role views implemented (optgroup, zoom controls, split-view, 65 WebGL refs) | Product integration tests |
| 8 | **Test Suite** | **195 PASS / 0 FAIL** | `test_verify.py`, `test_zoom_quality_174k_v26_eval.py`, `test_zoom_quality_174k_eval.py` |

---

## KEY FINDINGS — FROZEN AND EVIDENCE-BACKED

### 1. TF-IDF 174k Modes: Strong Coarse Structure, Failed Fine Zoom
- **Branch purity** (coarse): 0.51–0.55 vs 0.25 random baseline — **2-2.2× signal**
- **Legal area purity** (coarse): 0.24–0.31 vs ~0.005 random baseline — **48-62× signal**
- **Fine ladder**: severely over-fragmented — median cluster size = 1 at res_2.0 and res_3.0 (singleton fraction >99%)
- **All three monotonic zoom-refinement checks FAIL** for production default and all 4 TF-IDF modes
- **Conclusion**: TF-IDF-only modes support coarse navigation but **do not establish monotonic zoom refinement at 174k**

### 2. Evidence-Backed Zoom Path: Citation-Role / Dense Embeddings
- 1000-scale diagnostic (ground truth):
  - `citing_alpha0.3`: ZQ=0.5401
  - `following_alpha0.3`: ZQ=0.5280
  - `criticizing_alpha0.3`: ZQ=0.4864
  - Production default `outcome_hybrid_0.5`: ZQ=0.2798
- **Dense embeddings required** for 174k zoom quality — infrastructure ready

### 3. NESTING_METRIC_DEFECT_v1 — Corrected in State
- **Defect**: Legacy builders recorded `mean_nesting_score` as majority-parent COVERAGE (~1.0 by construction), not true strict nesting
- **Impact**: 37/46 audited modes over-claimed 1.0 vs honest strict nesting 0.04–1.0
- **Correction applied**:
  - `nesting_score>=0.99` claims **PROHIBITED** for compressed modes
  - Honest strict nesting range: 0.39–0.96
  - `nesting_score=1.0` citeable **ONLY** for 1000-scale by-construction modes with scope annotation
  - `outcome_tfidf_174k_compressed` nesting=1.0 is genuine (verified)

### 4. Compressed 5-Level Ladder [0.25, 0.5, 1.0, 2.0, 3.0] — Scope Limited
- **VALID**: 100% purity delta retention and identical zoom navigation at shared resolutions (22 modes tested)
- **NOT VALID**: Universal strict nesting preservation (honest mean change -0.00364, range [-0.0556, +0.1150], 21/22 modes nonzero)
- **Per-mode depth decisions required** — "Compressed ladder NOT universally valid" remains in force

### 5. Dense Embeddings Readiness — COMPLETE
- Parameterized builder fixed:
  - Branch derived from `chamber` field (corpus `branch` field was null)
  - 'unknown' branches excluded from purity computation
- Evaluation harness created: `fractal_map/evaluation/evaluate_174k_dense_embeddings.py`
- Verified against v26 TF-IDF results (reproduces FAIL verdicts for `cited_decisions_tfidf_outcome_hybrid_0.5_174k_v25` and `regeste_tfidf_174k`)
- ACCEPTED 174k metadata (173,963 entries, 100% branch+legal_area coverage) and corpus (37 year-split JSONL) available
- Infrastructure ready to consume legal-distance 174k dense embeddings year-split

### 6. Citation-Role 174k Validation — BLOCKED by Evidence
- **4 of 6** true-174k directories are decision-mappable (2 are placeholder-only)
- **6 directories** are misnamed 21k builds
- Row→id alignment unrecoverable without full corpus JSONL:
  - Probe 1 agreement: 0.426 vs ~1.0 expected → **REJECTED**
  - Probe 2: `cluster_metadata` CORRUPTED (1,003 duplicate IDs, 1,314 extra rows)
- Requires full corpus JSONL delivery from corpus lane

### 7. Product Multi-View Zoom UI — VERIFIED
- CITATION ROLE VIEWS optgroup implemented
- Zoom controls and split-view operational
- 65 WebGL references confirmed
- Audit recommendation #4 satisfied

---

## ORCHESTRATION FAILURE — ROOT CAUSE DIAGNOSED AND DOCUMENTED

| Aspect | Detail |
|--------|--------|
| **Root Cause** | Supervisor reads ephemeral `/tmp/lex_control/state/factory_direction.json` (reset each workflow) instead of persistent workspace `state/fractal-map.json` and `state/factory_direction.json` |
| **Symptom** | Supervisor sees `fractal-map.status=RUN` (ephemeral) vs workspace `fractal-map.status=COMPLETED_TFIDF` + `blocked_on=legal-distance_174k_dense_embeddings`, `continue_recommended=false` |
| **Occurrences** | **60+ documented** since run 33339971167 |
| **Required Fix** | Factory Director must update supervisor dispatch logic to read workspace state |
| **Mitigation Active** | `resume_guard: final_audit_complete_v12` in lane state prevents dishonest re-dispatch loops |

### Evidence Chain (60+ occurrences)
- Run 36078550827: First operational resume — orchestration failure diagnosed
- Run 36079647044: Verification — failure re-confirmed
- Run 36082543926: Operational resume — failure re-confirmed
- Run 36083220945: Operational resume — failure re-confirmed
- Run 36085875493: Operational resume — failure re-confirmed
- Run 36094045574: Operational resume — failure re-confirmed
- Run 36100882865: Final verification — failure re-confirmed
- Run 36107024770: Final audit-ready — failure re-confirmed

**This is a supervisor/workflow bug, not a lane failure.** The lane correctly completed its work and entered BLOCKED state. The supervisor incorrectly re-dispatches because it reads stale ephemeral state.

---

## STATE CONSISTENCY — VERIFIED

All critical state fields match between `state/fractal-map.json` and gate artifact `CYCLE_36107024770_GATE.json`:

| Field | State Value | Gate Value | Match |
|-------|-------------|------------|-------|
| `cycle_status` | COMPLETED | COMPLETED | ✓ |
| `continue_recommended` | false | false | ✓ |
| `blocked_on` | legal-distance_174k_dense_embeddings | legal-distance_174k_dense_embeddings | ✓ |
| `resume_guard` | final_audit_complete_v12 | final_audit_complete_v12 | ✓ |
| `evidence_tier` | ACCEPTED | ACCEPTED | ✓ |
| `direction_version` | 27 | 27 | ✓ |

---

## EVIDENCE REFERENCES — MACHINE-READABLE

### Core State & Gates
- `state/fractal-map.json` — Lane state (ACCEPTED, COMPLETED, continue_recommended=false)
- `results/fractal_map/audit/CYCLE_36107024770_GATE.json` — Final verification gate (PASS)
- `results/fractal_map/audit/CYCLE_36100882865_GATE.json` — Prior verification gate (PASS)

### 174k Zoom Quality Evaluation (Frozen)
- `results/fractal_map/zoom_quality_174k_eval/v26_frozen_spec.json` — Frozen experiment spec
- `results/fractal_map/zoom_quality_174k_eval/v26_verdict.json` — Frozen verdict (FAIL, all modes)
- `results/fractal_map/zoom_quality_174k_eval/v25_frozen_spec.json` — v25 frozen spec
- `results/fractal_map/zoom_quality_174k_eval/v25_verdict.json` — v25 frozen verdict (FAIL)

### 174k Census & Alignment
- `results/fractal_map/legal_distance_modes/174k_CENSUS_v26_frozen_spec.json` — Census classification rules
- `results/fractal_map/legal_distance_modes/census_v26.json` — 4 decision-mappable, 2 placeholder, 6 misnamed
- `results/fractal_map/legal_distance_modes/alignment_probe_v26.json` — Alignment CORRUPTED

### Hierarchical Map (Center Projected — Default)
- `results/fractal_map/hierarchical_map_center_projected/center_projected_hierarchical_results.json` — Purity 0.9571, best config coarse_0.5_fine_3.0
- `results/fractal_map/hierarchical_map_center_projected/hierarchical_map_results.json` — Nesting 1.0 (by construction)

### Compressed Resolution Ladder
- `results/fractal_map/evaluation/compressed_resolution_ladder_all_modes.json` — 22 modes, 100% delta retention
- `results/fractal_map/evaluation/zoom_navigation_comparison.json` — PASS, identical navigation at shared resolutions

### Dense Embeddings Readiness
- `fractal_map/evaluation/evaluate_174k_dense_embeddings.py` — Evaluation harness
- `reports/fractal_map/DENSE_EMBEDDINGS_READINESS_v27.md` — Readiness report
- `results/fractal_map/zoom_quality_174k_eval/dense_174k_verdict_cited_decisions_tfidf_outcome_hybrid_0.5_174k.json` — Verified against v26 FAIL
- `results/fractal_map/zoom_quality_174k_eval/dense_174k_verdict_regeste_tfidf_174k.json` — Verified against v26 FAIL

### Scale Readiness (Repaired)
- `results/fractal_map/evaluation/legal_distance_scale_readiness_33317287543.json` — Honest verdict: consistency extension, NOT scale-ready
- `results/fractal_map/scalability/legal_distance/source_cache/` — Committed source cache for independent recompute

### Nesting Audit
- `fractal_map/hierarchical/compute_honest_nesting_audit.py` — Honest nesting computation
- `results/fractal_map/evaluation/resume_36014970673_nesting_audit.json` — 37/46 modes over-claimed

### Tests (All Passing)
- `tests/fractal_map/test_verify.py` — 184 tests
- `tests/fractal_map/test_zoom_quality_174k_v26_eval.py` — 7 tests
- `tests/fractal_map/test_zoom_quality_174k_eval.py` — 4 tests

---

## NEXT RECOMMENDATION

**BLOCKED on legal-distance_174k_dense_embeddings.**

Resume when dense embeddings delivered. **No same-question cycle justified.** (`continue_recommended=false`)

The fractal-map lane has completed all work possible with current TF-IDF representations. The evidence-backed path forward requires dense embeddings from legal-distance. The lane state is correctly set to BLOCKED with `continue_recommended=false` so the Factory Director can decide the successor question when the dependency is resolved.

---

## AUDIT TRAIL

This report, the gate artifact `CYCLE_36107024770_GATE.json`, and the lane state `state/fractal-map.json` constitute the **final audit-ready snapshot** for the fractal-map lane at factory direction v27.

**No further work is required** until the `legal-distance_174k_dense_embeddings` dependency is resolved. All evidence is preserved, negative results are frozen, and the orchestration failure is documented for Factory Director action.

---

**Snapshot Status: AUDIT-READY ✓**

*Generated: 2026-09-25 | Factory Direction v27 | Lane: fractal-map*