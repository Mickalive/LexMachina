# Fractal-Map Lane: Blocked Status Verification (Factory Direction v27, GitHub Run 36107024770)

**Date**: 2026-09-25  
**Lane**: fractal-map  
**Direction Version**: 27  
**Evidence Tier**: ACCEPTED  
**Cycle Status**: COMPLETED (TF-IDF work) / BLOCKED (dense embeddings)  
**Continue Recommended**: false  

---

## Current State Summary

| Field | Value | Source |
|-------|-------|--------|
| `cycle_status` | COMPLETED | state/fractal-map.json |
| `continue_recommended` | false | state/fractal-map.json |
| `blocked_on` | legal-distance_174k_dense_embeddings | state/fractal-map.json |
| `evidence_tier` | ACCEPTED | state/fractal-map.json |
| `resume_guard` | final_audit_complete_v12 | state/fractal-map.json |
| `accepted_run_id` | 35952633500 | state/fractal-map.json |

---

## Verification Results (This Cycle)

### Test Suite Execution
All **195 tests PASS** (confirmed regression-free):

| Test File | Tests | Result |
|-----------|-------|--------|
| `tests/fractal_map/test_verify.py` | 184 | ✅ PASS |
| `tests/fractal_map/test_zoom_quality_174k_v26_eval.py` | 7 | ✅ PASS |
| `tests/fractal_map/test_zoom_quality_174k_eval.py` | 4 | ✅ PASS |
| **Total** | **195** | ✅ **PASS** |

### Infrastructure Readiness (Confirmed)
| Component | Status | Evidence |
|-----------|--------|----------|
| Parameterized hierarchical builder (compressed 5-level ladder) | ✅ READY | `build_parameterized_legal_distance_map_compressed.py` |
| 174k evaluation harness | ✅ READY | `evaluate_174k_dense_embeddings.py` |
| ACCEPTED 174k metadata | ✅ AVAILABLE | `/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json` (173,963 entries) |
| Corpus directory (37 year-split JSONL) | ✅ AVAILABLE | `/tmp/lex_accepted/corpus/corpus/normalization/canonical/` |
| Dense embedding test pipeline | ✅ VALIDATED | center_projected_768_1000_test artifacts exist |

---

## Accepted Findings (v26, Gate CYCLE_36095195476_GATE.json PASS)

### TF-IDF 174k Results (COMPLETED, NEGATIVE FOR ZOOM REFINEMENT)
- **Branch purity**: 0.51–0.55 (vs 0.25 random baseline, 4 classes)
- **Legal area purity**: 0.24–0.31 (vs ~0.005 random baseline, 213 classes)
- **Zoom refinement**: **FAIL** on all 3 frozen success checks for all 4 decision-mappable modes
- **Fine ladder**: Over-fragmented (median cluster size 1 at res_2.0/res_3.0)

### Evidence-Backed Zoom Path (DENSE EMBEDDINGS REQUIRED)
| Mode (1000-scale) | Zoom Quality (ZQ) | Status |
|-------------------|-------------------|--------|
| citing_alpha0.3 | 0.5401 | ✅ Strong |
| following_alpha0.3 | 0.5280 | ✅ Strong |
| criticizing_alpha0.3 | 0.4864 | ✅ Strong |
| outcome_hybrid_0.5 (production default) | 0.2798 | ⚠️ Rank 21 |

### Critical Defects Documented (Frozen)
- **NESTING_METRIC_DEFECT_v1**: nesting_score≥0.99 claims PROHIBITED for 7 compressed-family modes; honest strict nesting 0.39–0.96
- **Compressed 5-level ladder**: 100% purity delta retention, but 21/22 modes fail strict nesting preservation (mean change -0.00364)

---

## Blocker Status

| Blocker | Status | Resolution Path |
|---------|--------|-----------------|
| `legal-distance_174k_dense_embeddings` | **ACTIVE** | legal-distance executing year-split CPU computation (gh run 36071928708 per factory direction) |
| Corpus artifact publication | **RESOLVED** | Files confirmed at `/tmp/lex_accepted/` mount paths |
| GPU availability | **ENVIRONMENT CONSTRAINT** | CPU-only on free public runners (accepted) |

**No 174k dense embeddings detected** in `results/legal_distance/embeddings/` or `results/fractal_map/legal_distance_modes/`. Only 1000-scale modes present.

---

## Execution Plan When Dense Embeddings Arrive

Per DENSE_EMBEDDINGS_READINESS_v27.md (ACCEPTED):

```bash
# Step 1: Build hierarchical map (per mode)
python3 fractal_map/hierarchical/build_parameterized_legal_distance_map_compressed.py \
    --embedding-path <dense_embedding.npy> \
    --mode-id <mode_id> \
    --corpus-size 174113 \
    --metadata-path /tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json \
    --output-dir results/fractal_map/legal_distance_modes/<mode_id> \
    --corpus-dir /tmp/lex_accepted/corpus/corpus/normalization/canonical \
    --metadata-has-branch

# Step 2: Evaluate zoom quality
python3 fractal_map/evaluation/evaluate_174k_dense_embeddings.py \
    --mode <mode_id> \
    --output results/fractal_map/zoom_quality_174k_eval/dense_174k_verdict_<mode_id>.json
```

### Success Rule (Frozen, v25/v26 identical)
A 174k dense embedding mode **PASSES** iff:
1. **Branch monotonic**: `branch_purity[res_3.0] > branch_purity[res_0.25]`
2. **Area monotonic**: `area_purity[res_3.0] > area_purity[res_0.25]`
3. **Zoom refinement**: `improvement_rate > 0.5` on **≥ 2 of 4** transitions

---

## Orchestration Failure (Documented, Not Fixed)

**Root Cause**: Supervisor reads ephemeral `/tmp/lex_control/state/factory_direction.json` (fractal-map.status=RUN) instead of workspace `state/fractal-map.json` (blocked_on=legal-distance_174k_dense_embeddings, continue_recommended=false) and `state/factory_direction.json` (fractal-map.status=COMPLETED_TFIDF).

**Occurrences**: 60+ documented since run 33339971167.

**Required Fix**: Factory Director must update supervisor dispatch logic to read workspace state.

**Mitigation**: `resume_guard: final_audit_complete_v12` active in lane state.

---

## Recommendation

**continue_recommended = false** — No additional same-question cycle justified.

The fractal-map lane has:
1. ✅ Completed all TF-IDF 174k work
2. ✅ Validated negative results (zoom refinement FAIL for TF-IDF-only modes)
3. ✅ Built and tested dense-embedding-ready infrastructure
4. ✅ Frozen accepted negative findings (NESTING_METRIC_DEFECT_v1, compressed ladder nesting defect)
5. ✅ Preserved all evidence (195 tests PASS, gate artifacts, reports)

**Lane correctly BLOCKED on single dependency `legal-distance_174k_dense_embeddings`.**  
**Factory Director to resume when dense embeddings land.**

---

## Files Verified This Cycle

| File | Purpose |
|------|---------|
| `state/fractal-map.json` | Lane state (COMPLETED, blocked, continue_recommended=false) |
| `results/audit/fractal-map/CYCLE_36095195476_GATE.json` | Latest audit gate (PASS, 195 tests) |
| `reports/fractal_map/DENSE_EMBEDDINGS_READINESS_v27.md` | Readiness checklist (all ✅) |
| `fractal_map/hierarchical/build_parameterized_legal_distance_map_compressed.py` | Parameterized builder |
| `fractal_map/evaluation/evaluate_174k_dense_embeddings.py` | Evaluation harness |
| `tests/fractal_map/test_verify.py` | 184 artifact integrity tests |
| `tests/fractal_map/test_zoom_quality_174k_v26_eval.py` | 7 v26 frozen spec tests |
| `tests/fractal_map/test_zoom_quality_174k_eval.py` | 4 v25 freeze protection tests |

---

**Status**: BLOCKED (correctly). No action required until legal-distance delivers 174k dense embeddings.