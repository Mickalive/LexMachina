# Dense Embeddings Handoff Readiness — Fractal Map Lane (v27)

**Status**: BLOCKED on `legal-distance_174k_dense_embeddings` (single dependency)
**Lane State**: COMPLETED_TFIDF / BLOCKED_ON_DEPENDENCIES
**Continue Recommended**: false (no same-question cycle justified)
**Last Verified**: 2026-09-25T08:09:00Z

---

## Summary

The fractal-map lane has completed all TF-IDF work at 174k scale and is correctly blocked awaiting dense embeddings from the legal-distance lane. All infrastructure for consuming and evaluating dense embeddings is ready and verified.

---

## 1. TF-IDF Work COMPLETED (Evidence Tier: ACCEPTED)

### 174k TF-IDF Modes Built and Evaluated
- **4 decision-mappable 174k TF-IDF modes** evaluated against frozen v26 spec
- **Verdict**: ALL FAIL (0/4) on monotonic zoom refinement — negative result preserved
- **Branch purity**: 0.51–0.55 vs 0.25 random (strong legal structure)
- **Legal area purity**: 0.24–0.31 vs 0.005 random (strong signal)
- **Fine ladder**: Over-fragmented (median cluster size 1 at res_2.0/3.0)
- **Conclusion**: TF-IDF-only modes do NOT establish zoom refinement at 174k

### Evidence-Backed Zoom Path (Requires Dense Embeddings)
| Mode | Zoom Quality (1000-scale) | Evidence Tier |
|------|---------------------------|---------------|
| citing_alpha0.3 | ZQ=0.5401 | ACCEPTED |
| following_alpha0.3 | ZQ=0.5280 | ACCEPTED |
| criticizing_alpha0.3 | ZQ=0.4864 | ACCEPTED |
| production default (outcome_hybrid_0.5) | ZQ=0.2798 | ACCEPTED |

### NESTING_METRIC_DEFECT_v1 — CORRECTED
- `nesting_score >= 0.99` claims **PROHIBITED** for 7 compressed-family modes
- Honest strict nesting: 0.3911–0.9632
- `nesting_score = 1.0` citeable **ONLY** for 1000-scale by-construction modes
- Compressed 5-level ladder [0.25, 0.5, 1.0, 2.0, 3.0]: 100% purity delta retention + identical zoom navigation at shared resolutions; NOT universal strict nesting (mean change -0.00364, 21/22 modes nonzero)

---

## 2. Dense Embeddings Evaluation Infrastructure READY

### Evaluation Harness: `fractal_map/evaluation/evaluate_174k_dense_embeddings.py`
- **Status**: Created and verified against v26 TF-IDF results (reproduces FAIL verdicts)
- **Success Rule** (frozen v25/v26):
  - (a) Branch purity res_3.0 > res_0.25
  - (b) Area purity res_3.0 > res_0.25  
  - (c) Branch improvement_rate > 0.5 on ≥2 of 4 transitions
- **Resolutions**: Compressed 5-level ladder [0.25, 0.5, 1.0, 2.0, 3.0]
- **Outputs**: Per-mode verdict JSON + strict nesting recomputation + fragmentation metrics

### Metadata: ACCEPTED and Complete
- **Path**: `/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json` (173,963 entries)
- **Branch coverage**: 100% (90,632 labeled, 83,331 unknown — expected for procedural decisions)
- **Legal area coverage**: 100% (91,193 labeled, 82,770 unknown)
- **Languages**: de=106,501, fr=57,489, it=9,973
- **Years**: 2000–2026 complete

### Builder: `fractal_map/hierarchical/build_parameterized_legal_distance_map.py`
- **Supports**: Arbitrary legal-distance embeddings (TF-IDF, dense, hybrids) at any corpus size
- **Resolutions**: 7-level [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0] (compressed ladder is subset)
- **Provenance Rule**: Slice embedding to metadata subset BEFORE clustering (verified purity=1.0)
- **Outputs**: Hierarchical labels, zoom mappings, decision clusters, cluster metadata, zoom coherence
- **Legal-distance Rule**: `hierarchical_best := finest resolution` (not coarse_0.5→sub_3.0)

### Compressed Ladder Validation: COMPLETE
- 22 modes tested at 174k
- 100% purity delta retention at shared resolutions
- Identical zoom navigation at shared resolutions
- 29% fewer zoom levels with zero quality loss
- **Limitation**: Does NOT preserve strict nesting universally (21/22 modes nonzero change)

---

## 3. Legal-Distance Dense Embeddings Computation (IN PROGRESS)

### Script: `legal_distance/experiments/compute_174k_dense_embeddings.py`
- **Model**: `paraphrase-multilingual-mpnet-base-v2` (768-dim)
- **Strategy**: Year-split chunked processing with resumable checkpoints
- **Target**: CPU execution within 65-min job ceilings on free public runners
- **Outputs** (to `legal_distance/results/174k_dense_embeddings/`):
  - `embeddings_768.npy` — raw 768-dim
  - `embeddings_center_projected.npy` — language-center-subtracted 768-dim
  - `embeddings_center_projected_64.npy` — PCA 64-dim
  - `embeddings_center_projected_128.npy` — PCA 128-dim
  - `metadata.json` — aligned with canonical order
  - `run_metadata.json` — provenance

### Expected Modes for Fractal Map Evaluation
1. `center_projected_768` — raw debiased 768-dim
2. `center_projected_64` — PCA 64-dim (product serving default candidate)
3. `center_projected_128` — PCA 128-dim
4. Metric learning variants (linear_metric_epoch4, mahalanobis_metric_epoch4)
5. Hybrid stabilized variants (hybrid_stabilized_epoch1)
6. Citation role embeddings (citing, following, criticizing)

---

## 4. Integration Points Ready

### Fractal Map Builder Consumption
```bash
python fractal_map/hierarchical/build_parameterized_legal_distance_map.py \
    --embedding-path legal_distance/results/174k_dense_embeddings/embeddings_center_projected_64.npy \
    --mode-id center_projected_64_174k \
    --corpus-size 173963 \
    --metadata-path /tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json \
    --metadata-has-branch \
    --output-dir results/fractal_map/legal_distance_modes/center_projected_64_174k
```

### Evaluation Consumption
```bash
python fractal_map/evaluation/evaluate_174k_dense_embeddings.py \
    --mode center_projected_64_174k \
    --output results/fractal_map/zoom_quality_174k_eval/dense_174k_verdict_center_projected_64_174k.json
```

### Product Integration
- `map_mode_registry.py` supports dynamic mode loading
- `zoom_neighborhood_api.py` provides navigation endpoints
- Product default: `center_projected_64dim_hierarchical` (TF-IDF hybrid) → will switch to dense when available

---

## 5. Orchestration Failure (Documented, Mitigated)

**Root Cause**: Supervisor reads ephemeral `/tmp/lex_control/state/factory_direction.json` (reset each workflow) instead of persistent workspace `state/fractal-map.json` and `state/factory_direction.json`.

**Impact**: 60+ documented re-dispatch occurrences since run 33339971167.

**Mitigations Active**:
- `resume_guard=final_audit_complete_v12` on fractal-map state
- Explicit resume trigger documented in factory direction
- Workspace `state/fractal-map.json` has `cycle_status: "COMPLETED"` / `blocked_on: "legal-distance_174k_dense_embeddings"`
- Workspace `state/factory_direction.json` correctly shows `fractal-map.status: "COMPLETED_TFIDF"`

**Required Fix**: Factory Director must update supervisor dispatch logic to read workspace state.

---

## 6. Accepted State References

- `state/fractal-map.json` — lane state (ACCEPTED, COMPLETED, continue_recommended=false)
- `state/factory_direction.json` — workspace factory direction v27 (COMPLETED_TFIDF)
- `results/fractal_map/audit/CYCLE_36107024770_GATE.json` — final audit PASS
- `reports/fractal_map/OPERATIONAL_RESUME_36107024770_FINAL_AUDIT_READY.md` — audit-ready snapshot
- `fractal_map/evaluation/evaluate_174k_dense_embeddings.py` — evaluation harness
- `results/fractal_map/zoom_quality_174k_eval/v26_frozen_spec.json` — frozen success rule

---

## 7. Next Actions (When Dense Embeddings Land)

1. **Legal-distance** delivers 174k dense embeddings to `legal_distance/results/174k_dense_embeddings/`
2. **Fractal-map** runs parameterized builder for each dense mode (7 resolutions)
3. **Fractal-map** runs `evaluate_174k_dense_embeddings.py` on each mode against frozen v26 spec
4. **Evaluation** runs full 12-benchmark formal suite on dense modes
5. **Product** wires dense modes as map mode options (TF-IDF hybrid remains default until jurist study)

---

## 8. Conclusion

**The fractal-map lane is correctly BLOCKED with all handoff infrastructure ready.** No same-question cycle is justified (`continue_recommended: false`). The lane will automatically resume when legal-distance delivers 174k dense embeddings, per the explicit resume trigger documented in factory direction v27.

All negative results (TF-IDF zoom refinement FAIL) are preserved. All positive infrastructure (evaluation harness, builder, compressed ladder, metadata) is verified and frozen.

**Lane Status**: BLOCKED (correct) | **Handoff Readiness**: COMPLETE