# Operational Resume Verification — Run 36079647044

## Summary
**Lane**: fractal-map  
**Factory Direction**: v27  
**GitHub Run**: 36079647044  
**Resume From**: 36078550827  
**Timestamp**: 2026-09-25T00:55:00Z  
**Gate Status**: PASS  
**Evidence Tier**: ACCEPTED  
**Cycle Status**: COMPLETED  
**Continue Recommended**: false  

## Verification Results
- **Test Suite**: 194 passed, 1 skipped (LEIDEN recompute deps not installed)
- **Artifacts Verified**: 995+
- **State File**: `state/fractal-map.json` updated with all required fields per RESEARCH_PROTOCOL.md

## Key Deliverables Verified

### 1. TF-IDF 174k Zoom Quality Evaluation (v26)
- **Status**: COMPLETE — frozen FAIL verdict confirmed
- **Modes Evaluated**: 4 decision-mappable 174k TF-IDF modes
- **Verdict**: FAIL on all three frozen success checks
  - Branch monotonic res_3.0 vs res_0.25: **FAIL** (0.5525 → 0.5273)
  - Area monotonic res_3.0 vs res_0.25: **FAIL** (0.3134 → 0.2622)
  - Improvement rate > 0.5 on ≥2/4 transitions: **FAIL** (only 1/4)
- **Structure Signal**: Strong (branch purity 0.51-0.55 vs 0.25 random; area purity 0.24-0.31 vs ~0.005 random)
- **Fine Ladder**: Over-fragmented (median cluster size = 1 at res_2.0/res_3.0)
- **Conclusion**: TF-IDF-only 174k modes NOT established for zoom refinement

### 2. v25 Freeze Protection
- **Status**: INTACT
- **Verification**: Purity bit-equal, zoom claims identical with micro-deviations ≤2 parents
- **Crosscheck**: v25 raw data matches v26 re-evaluation exactly

### 3. Nesting Metric Defect (v1) — Documented & Corrected
- **Finding**: 37/46 audited modes over-claimed nesting_score ≥ 0.99 (honest strict nesting: 0.04–1.0)
- **Root Cause**: Parameterized builders recorded majority-parent coverage (~1.0 by construction), not strict nesting
- **Remediation**: Both parameterized builders corrected; historical artifacts preserved untouched
- **Compressed Ladder**: [0.25, 0.5, 1.0, 2.0, 3.0] does NOT preserve strict nesting (honest mean change -0.00364, 21/22 modes nonzero)
- **Valid Claim Scope**: 100% purity delta retention + identical zoom navigation at shared resolutions ONLY

### 4. Compressed 5-Level Resolution Ladder
- **Status**: VALIDATED across 22 modes
- **Ladder**: [0.25, 0.5, 1.0, 2.0, 3.0] (dropped 0.75, 1.5)
- **Delta Retention**: 100% purity delta retention
- **Zoom Navigation**: Identical at shared resolutions
- **Resolution Reduction**: 28.57% (29% fewer zoom levels, zero quality loss)
- **Limitation**: NOT universally valid for strict nesting preservation

### 5. Dense Embeddings Readiness
- **Status**: COMPLETE
- **Parameterized Builder Fixes**:
  1. Branch derived from chamber field (corpus branch=null)
  2. 'unknown' branches excluded from purity computation
- **Validation**: center_projected 768-dim at 1000-scale (mean_branch_purity=0.934, zoom coherence operational)
- **Evaluation Harness**: `fractal_map/evaluation/evaluate_174k_dense_embeddings.py` created and verified against v26 TF-IDF results (reproduces FAIL verdicts)
- **Infrastructure**: ACCEPTED 174k metadata (173,963 entries, 100% branch+legal_area) and corpus (37 year-split JSONL) available

### 6. Citation-Role 174k Validation
- **Status**: BLOCKED by evidence
- **Blockers**:
  - Placeholder builds (bger_placeholder_* IDs)
  - Row→ID alignment unrecoverable (probe 1 agreement 0.426 vs ~1.0 expected)
  - Cluster metadata CORRUPTED (1003 duplicate IDs, 1314 extra rows)
- **Resolution Required**: Full corpus JSONL delivery from corpus lane

### 7. Product Multi-View Zoom UI
- **Status**: VERIFIED IMPLEMENTED
- **Features**: CITATION ROLE VIEWS optgroup, zoom controls, split-view, 65 WebGL refs
- **Audit Recommendation #4**: SATISFIED

## Orchestration Failure — Root Cause Confirmed
**Supervisor reads ephemeral `/tmp/lex_control/state/factory_direction.json`** (reset each workflow) instead of persistent workspace `state/factory_direction.json` and `state/fractal-map.json`.

- **Manifestation**: fractal-map.status=RUN in ephemeral vs COMPLETED_TFIDF in workspace; blocked_on=legal-distance_174k_dense_embeddings, continue_recommended=false in workspace
- **Occurrences**: 60+ documented since run 33339971167
- **Required Fix**: Factory Director must update supervisor dispatch logic to read workspace state
- **Gate Artifact**: `results/fractal_map/audit/CYCLE_36079647044_GATE.json`

## Evidence References
All evidence references preserved in `state/fractal-map.json` (94 entries). Key new references:
- `results/fractal_map/zoom_quality_174k_eval/v26_frozen_spec.json`
- `results/fractal_map/zoom_quality_174k_eval/v26_verdict.json`
- `results/fractal_map/zoom_quality_174k_eval/dense_174k_verdict_cited_decisions_tfidf_outcome_hybrid_0.5_174k.json`
- `results/fractal_map/zoom_quality_174k_eval/dense_174k_verdict_regeste_tfidf_174k.json`
- `fractal_map/evaluation/evaluate_174k_dense_embeddings.py`
- `reports/fractal_map/DENSE_EMBEDDINGS_READINESS_v27.md`

## Next Recommendation
**BLOCKED on legal-distance_174k_dense_embeddings**. Resume when dense embeddings delivered. No same-question cycle justified (continue_recommended=false).

---
*Generated by fractal-map lane operational resume verification*
