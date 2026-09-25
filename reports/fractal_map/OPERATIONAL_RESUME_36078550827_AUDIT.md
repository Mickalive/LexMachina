# Fractal-Map Lane: Operational Resume & Audit-Ready Snapshot (Run 36078550827)

**Date**: 2026-09-25  
**Lane**: fractal-map  
**Factory Direction**: v27 (ephemeral) / v25 (workspace canonical)  
**Evidence Tier**: ACCEPTED (v26 TF-IDF evaluation complete)  
**Cycle Status**: COMPLETED (TF-IDF work)  
**Continue Recommended**: **false** — no additional same-question cycle justified  
**Blocker**: `legal-distance_174k_dense_embeddings` (single remaining dependency)  
**Resume Guard**: `final_audit_complete_v12`  

---

## Executive Summary

The fractal-map lane has **completed all TF-IDF 174k work** and is **audit-ready**. The lane is correctly **BLOCKED** on the single remaining dependency: `legal-distance_174k_dense_embeddings`. All infrastructure for consuming dense embeddings is built and verified.

**Orchestration Failure Diagnosed**: The supervisor has re-dispatched this lane 60+ times because it reads the ephemeral `/tmp/lex_control/state/factory_direction.json` (v27, `fractal-map.status=RUN`) instead of the workspace `state/factory_direction.json` (v25, `fractal-map.status=COMPLETED_TFIDF`) and the lane state `state/fractal-map.json` (`blocked_on="legal-distance_174k_dense_embeddings"`, `continue_recommended=false`).

---

## Verified Deliverables (ACCEPTED Tier)

### 1. TF-IDF 174k Zoom-Quality Evaluation (v26) — COMPLETE

| Metric | Result | Evidence |
|--------|--------|----------|
| **Decision-mappable modes evaluated** | 4 / 4 | `v26_verdict.json` |
| **Modes PASSING v25 success rule** | 0 / 4 | **OVERALL FAIL** |
| **Branch purity (res_0.25 → res_3.0)** | 0.55 → 0.53 (non-monotonic) | All 4 modes |
| **Area purity (res_0.25 → res_3.0)** | 0.31 → 0.26 (non-monotonic) | All 4 modes |
| **Zoom improvement_rate > 0.5 on ≥2/4 transitions** | 0 / 4 modes | Max 1/4 transitions |
| **Fine ladder fragmentation** | Median cluster size = 1 | res_2.0: 12,852 clusters; res_3.0: 63,778 |
| **Legal structure signal** | **STRONG** | Branch purity 0.51-0.55 vs 0.25 random; Area purity 0.24-0.31 vs 0.005 random |

**Frozen Spec**: `results/fractal_map/zoom_quality_174k_eval/v26_frozen_spec.json`  
**Frozen Verdict**: `results/fractal_map/zoom_quality_174k_eval/v26_verdict.json`  
**Census**: `results/fractal_map/legal_distance_modes/174k_CENSUS_v26_frozen_spec.json` (12 "174k"-named dirs classified: 4 TRUE decision-mappable, 2 placeholder-keyed, 6 misnamed 21k)

### 2. v25 Freeze Protection — INTACT

Cross-check vs v25 (run 36029852715):
- **Purity**: Bit-equal on all 5 resolutions (0.5525/0.5128/0.5324/0.514/0.5273)
- **Zoom claims**: Identical (rate>0.5 count = 1, branch_monotonic = False)
- **Micro-deviations**: ≤2 parents, ΔMI ≤ 0.006

### 3. NESTING_METRIC_DEFECT_v1 — DOCUMENTED & CORRECTED

| Claim | Reality | Scope |
|-------|---------|-------|
| `nesting_score ≥ 0.99` for 7 compressed-family modes | **PROHIBITED** | Honest strict nesting: 0.3911–0.9632 |
| `nesting_score = 1.0` citeable | **ONLY** 1000-scale by-construction modes | With scope annotation + honest ladder mean (0.8722/0.8644) |
| `outcome_tfidf_174k_compressed nesting=1.0` | **GENUINE** | Verified |
| Compressed 5-level ladder `[0.25,0.5,1.0,2.0,3.0]` preserves strict nesting | **FALSE** | Mean change -0.00364, range [-0.0556, +0.1150], 21/22 modes nonzero |

**Audit Artifact**: `results/fractal_map/evaluation/resume_36014970673_nesting_audit.json`  
**Audit Script**: `fractal_map/hierarchical/compute_honest_nesting_audit.py` (bit-exact reproduction in run 36025207612)

### 4. Compressed 5-Level Ladder — VALIDATED (ACCEPTED)

| Property | Result |
|----------|--------|
| **Purity delta retention** | 100% across all 22 modes |
| **Zoom navigation at shared resolutions** | Identical by construction |
| **Strict nesting change** | Non-zero but benign (does not affect product zoom behavior) |
| **Resolution reduction** | 29% (7 → 5 levels) |

**Evidence**: `results/fractal_map/audit/CYCLE_33341400705_GATE.json`, `compressed_resolution_ladder_full_validation`

### 5. Dense Embeddings Readiness — COMPLETE (v27)

| Component | Status | Validation |
|-----------|--------|------------|
| **Parameterized builder** | ✅ Fixed | Branch from chamber; excludes "unknown"; tested center_projected 768-dim at 1000-scale (mean_branch_purity=0.934) |
| **Evaluation harness** | ✅ Created | `evaluate_174k_dense_embeddings.py` verified against v26 TF-IDF results (reproduces FAIL) |
| **ACCEPTED 174k metadata** | ✅ Available | `/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json` (173,963 entries, 100% branch+legal_area) |
| **Corpus directory** | ✅ Available | `/tmp/lex_accepted/corpus/corpus/normalization/canonical/` (37 year-split JSONL) |
| **Compressed ladder** | ✅ Hardcoded | `[0.25, 0.5, 1.0, 2.0, 3.0]` validated |

**Files Created v27**:
- `fractal_map/hierarchical/build_parameterized_legal_distance_map_compressed.py` (fixed)
- `fractal_map/evaluation/evaluate_174k_dense_embeddings.py` (new)
- `results/fractal_map/legal_distance_modes/center_projected_768_1000_test/` (test artifacts)
- `results/fractal_map/zoom_quality_174k_eval/dense_174k_verdict_*.json` (verification outputs)

### 6. Citation-Role 174k Validation — BLOCKED (Evidence-Backed)

| Issue | Status |
|-------|--------|
| Placeholder builds (`bger_placeholder_*` IDs) | **CONFIRMED** |
| Row→ID alignment (probe 1) | Agreement 0.426 vs ~1.0 expected → **REJECTED** |
| Cluster metadata (probe 2) | 1,003 duplicate IDs, 1,314 extra rows → **CORRUPTED** |
| **Conclusion** | Citation-role 174k validation **BLOCKED by evidence**, not skipped |

### 7. Product Multi-View Zoom UI — VERIFIED IMPLEMENTED

- CITATION ROLE VIEWS optgroup ✅
- Zoom controls ✅
- Split-view ✅
- 65 WebGL references ✅
- Audit recommendation #4 satisfied

---

## Test Suite Verification

```
tests/fractal_map/                    194 passed, 1 skipped
├── test_verify.py                    107 passed
├── test_zoom_quality_174k_eval.py    7 passed (v25 freeze)
├── test_zoom_quality_174k_v26_eval.py 7 passed (v26 frozen)
└── test_zoom_quality_174k_all_modes_v26.py 73 passed (new v26 guard tests)
```

**All 194 tests PASS** (1 skipped: provenance recompute — expected).

---

## Evidence References (Canonical)

### Primary Evaluation Artifacts
- `results/fractal_map/zoom_quality_174k_eval/v26_frozen_spec.json`
- `results/fractal_map/zoom_quality_174k_eval/v26_verdict.json`
- `results/fractal_map/zoom_quality_174k_eval/v25_frozen_spec.json`
- `results/fractal_map/zoom_quality_174k_eval/v25_verdict.json`

### Census & Alignment
- `results/fractal_map/legal_distance_modes/174k_CENSUS_v26_frozen_spec.json`
- `results/fractal_map/legal_distance_modes/census_v26.json`
- `results/fractal_map/legal_distance_modes/alignment_probe_v26.json`

### Nesting Audit
- `results/fractal_map/evaluation/resume_36014970673_nesting_audit.json`
- `fractal_map/hierarchical/compute_honest_nesting_audit.py`
- `fractal_map/hierarchical/verify_state_nesting_fix.py`

### Compressed Ladder
- `results/fractal_map/evaluation/compressed_resolution_ladder_all_modes.json`
- `results/fractal_map/audit/CYCLE_33341400705_GATE.json`
- `fractal_map/evaluation/compressed_resolution_ladder_all_modes.py`

### Dense Embeddings Readiness
- `fractal_map/hierarchical/build_parameterized_legal_distance_map_compressed.py`
- `fractal_map/evaluation/evaluate_174k_dense_embeddings.py`
- `results/fractal_map/zoom_quality_174k_eval/dense_174k_verdict_cited_decisions_tfidf_outcome_hybrid_0.5_174k.json`
- `results/fractal_map/zoom_quality_174k_eval/dense_174k_verdict_regeste_tfidf_174k.json`
- `reports/fractal_map/DENSE_EMBEDDINGS_READINESS_v27.md`

### Operational Resume Chain
- `results/fractal_map/audit/CYCLE_36035695081_GATE.json`
- `reports/fractal_map/OPERATIONAL_RESUME_36035695081.md`
- `results/fractal_map/audit/CYCLE_36025207612_GATE.json`
- `reports/fractal_map/OPERATIONAL_RESUME_36025207612_VERIFICATION.md`

---

## Orchestration Failure Diagnosis

### Root Cause
The supervisor dispatch logic reads `/tmp/lex_control/state/factory_direction.json` (ephemeral, reset on each workflow run) which has:
```json
"fractal-map": { "status": "RUN", "priority": 1, ... }
```

While the **workspace canonical** files correctly show:

**`state/factory_direction.json` (v25, persistent)**:
```json
"fractal-map": { "status": "COMPLETED_TFIDF", ... }
```

**`state/fractal-map.json` (canonical lane state)**:
```json
{
  "cycle_status": "COMPLETED",
  "continue_recommended": false,
  "blocked_on": "legal-distance_174k_dense_embeddings",
  "blocked_since": "2026-09-24T01:55:00Z",
  "resume_guard": "final_audit_complete_v12"
}
```

### Failure Chain
1. Supervisor reads ephemeral control plane → sees `RUN` → dispatches fractal-map
2. Lane executes operational resume → verifies state → writes `BLOCKED` to workspace state
3. Next workflow run → ephemeral control plane reset to v27 with `RUN` → re-dispatch
4. **60+ documented occurrences** (first at run 33339971167, this is 60th+)

### Required Fix (Factory Director Authority)
Update supervisor dispatch logic to read **workspace state** (`state/factory_direction.json` and `state/fractal-map.json`) instead of ephemeral `/tmp/lex_control/state/factory_direction.json`.

---

## Lane State (Machine-Readable)

```json
{
  "lane": "fractal-map",
  "direction_version": 27,
  "evidence_tier": "ACCEPTED",
  "cycle_status": "COMPLETED",
  "continue_recommended": false,
  "accepted_run_id": "35952633500",
  "github_run": "36035695081",
  "resume_from_run_id": "36034386649",
  "timestamp": "2026-09-24T18:10:00.000000+00:00",
  "blocked_on": "legal-distance_174k_dense_embeddings",
  "blocked_since": "2026-09-24T01:55:00Z",
  "resume_guard": "final_audit_complete_v12",
  "next_recommendation": "BLOCKED (narrowed, v26 completion): v25's single-mode negative GENERALIZED to the full decision-mappable set. 0/4 TF-IDF 174k modes PASS zoom refinement. Dense embeddings readiness COMPLETE. Citation-role 174k validation BLOCKED by evidence (placeholder builds + alignment corruption). Infrastructure ready for legal-distance 174k dense embeddings year-split delivery."
}
```

---

## Next Actions (When Blocker Resolves)

### For Factory Director / Legal-Distance Lane
1. **MONITOR** legal-distance 174k dense embedding delivery (gh run 36071928708 actively executing)
2. **EXECUTE** for each delivered dense embedding mode:
   ```bash
   # Build hierarchical map
   python3 fractal_map/hierarchical/build_parameterized_legal_distance_map_compressed.py \
       --embedding-path /path/to/dense_embedding.npy \
       --mode-id <mode_id> \
       --corpus-size 174113 \
       --metadata-path /tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json \
       --output-dir results/fractal_map/legal_distance_modes/<mode_id> \
       --corpus-dir /tmp/lex_accepted/corpus/corpus/normalization/canonical \
       --metadata-has-branch
   
   # Evaluate zoom quality
   python3 fractal_map/evaluation/evaluate_174k_dense_embeddings.py \
       --mode <mode_id>
   ```
3. **COMPARE** against TF-IDF baselines and 1000-scale citation-role ZQ benchmarks
4. **INTEGRATE** passing modes into product map mode registry

### Expected Dense Modes (per legal-distance v14 REPRODUCED)
| Priority | Modes | Target ZQ Benchmark |
|----------|-------|---------------------|
| HIGH | `center_projected_64dim`, `linear_metric_epoch4`, `mahalanobis_metric_epoch4` | citing_alpha0.3 ZQ=0.5401 |
| HIGH | `citing_alpha0.3`, `following_alpha0.3`, `criticizing_alpha0.3` | 1000-scale: 0.5401 / 0.5280 / 0.4864 |
| MEDIUM | `hybrid_stabilized_epoch1`, `cited_decisions_tfidf`, `hybrid_cp64_0.7`, `hybrid_cp768_0.7` | |
| LOW | `ft_multilingual_e5_small_pretrained` (overclusters) | |

---

## Recommendation

**`continue_recommended: false`** — No additional same-question cycle justified.

The fractal-map lane has:
1. ✅ **Completed** all TF-IDF 174k work with frozen, claim-bearing evaluation (v25/v26)
2. ✅ **Documented** honest negative results (TF-IDF fails zoom refinement at 174k)
3. ✅ **Corrected** all metric over-claims (NESTING_METRIC_DEFECT_v1)
4. ✅ **Built & verified** dense embeddings consumption infrastructure
5. ✅ **Passed** all 194 frozen tests
6. ✅ **Verified** product multi-view zoom UI with citation-role views

The lane is **correctly BLOCKED** on `legal-distance_174k_dense_embeddings`. Factory Director should resume this lane **only when** dense embeddings are delivered by legal-distance.

---

## Audit Readiness Checklist

- [x] Frozen claim-bearing spec (v26) committed before computation
- [x] Raw outputs preserved (v26_verdict.json, dense_174k_verdict_*.json)
- [x] Negative results preserved (0/4 modes PASS)
- [x] Baseline pinned (branch_random=0.25, area_random=0.0047)
- [x] Success rule frozen (3 checks, unchanged from v25)
- [x] Cross-check vs prior cycle (v25 purity bit-equal, zoom claims identical)
- [x] Metric defects documented and annotated in state (NESTING_METRIC_DEFECT_v1)
- [x] All 194 tests PASS
- [x] Evidence references complete and traceable
- [x] Machine-readable state written (`state/fractal-map.json`)
- [x] Human-readable report written (this document)
- [x] Orchestration failure diagnosed and documented
- [x] Resume guard set (`final_audit_complete_v12`)

---

**Signed**: Fractal-Map Lane Operational Resume 36078550827  
**Status**: AUDIT-READY — Awaiting `legal-distance_174k_dense_embeddings` delivery