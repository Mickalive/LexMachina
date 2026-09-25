# OPERATIONAL RESUME FINAL VERIFICATION — Run 36100882865

**Lane:** fractal-map  
**Factory Direction:** v27  
**Resume From:** Run 36093600756 (prior operational resume final)  
**Date:** 2026-09-25T06:XX:XXZ  
**Gate Status:** PASS  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** COMPLETED  
**Continue Recommended:** false  
**Blocked On:** legal-distance_174k_dense_embeddings (single dependency)  
**Blocked Since:** 2026-09-24T01:55:00Z  
**Resume Guard:** final_audit_complete_v12

---

## Summary

Operational resume verification from persisted producer snapshot of run 36100405076. **All 195 tests PASS (184 + 7 + 4).** Lane state **CONFIRMED**: BLOCKED on `legal-distance_174k_dense_embeddings` (single dependency), `continue_recommended=false` — **no same-question cycle justified**.

Orchestration failure **RE-CONFIRMED**: Supervisor reads ephemeral `/tmp/lex_control/state/factory_direction.json` (fractal-map.status=RUN) instead of workspace `state/factory_direction.json` (fractal-map.status=COMPLETED_TFIDF) and `state/fractal-map.json` (blocked_on=legal-distance_174k_dense_embeddings, continue_recommended=false) — **60+ documented re-dispatch occurrences**. Factory Director must update supervisor dispatch logic.

All valid completed work preserved. Snapshot **audit-ready**.

---

## Deliverables Verified

| Deliverable | Status | Evidence |
|-------------|--------|----------|
| TF-IDF 174k zoom quality (v26) | COMPLETE — 0/4 modes PASS (frozen FAIL) | `v26_verdict.json`, `v26_frozen_spec.json` |
| v25 freeze protection | INTACT — purity bit-equal, zoom claims identical | `test_v25_freeze_protection_intact` |
| NESTING_METRIC_DEFECT_v1 | DOCUMENTED — 37/46 modes over-claimed, corrected in state | `compute_honest_nesting_audit.py` |
| Compressed 5-level ladder | VALIDATED — 100% purity delta retention, 22 modes | `compressed_resolution_ladder_all_modes.json` |
| Dense embeddings readiness | COMPLETE — builder fixed, harness created, verified | `evaluate_174k_dense_embeddings.py`, `DENSE_EMBEDDINGS_READINESS_v27.md` |
| Citation-role 174k validation | BLOCKED — placeholder builds + alignment corruption | `174k_CENSUS_v26_frozen_spec.json`, `alignment_probe_v26.json` |
| Product multi-view zoom UI | VERIFIED — citation-role views implemented | Product integration tests |
| Test suite | **195 PASS** (0 failed) | `test_verify.py`, `test_zoom_quality_174k_v26_eval.py`, `test_zoom_quality_174k_eval.py` |

---

## Key Findings (Re-confirmed)

### TF-IDF 174k Modes Encode Strong Legal Structure — But Fail Fine Zoom
- **Branch purity** at coarse resolutions: 0.51–0.55 vs 0.25 random baseline
- **Legal area purity** at coarse resolutions: 0.24–0.31 vs ~0.005 random baseline
- **Fine ladder over-fragmented**: median cluster size = 1 at res_2.0 and res_3.0 (singleton fraction >99%)
- **All three monotonic zoom-refinement checks FAIL** for production default and all TF-IDF modes

### Evidence-Backed Zoom Path Remains Citation-Role / Dense Embedding Modes
- 1000-scale diagnostic: `citing_alpha0.3` ZQ=0.5401, `following` ZQ=0.5280, `criticizing` ZQ=0.4864
- Production default `outcome_hybrid_0.5` ZQ=0.2798
- **Dense embeddings required** for 174k zoom quality

### Nesting Metric Defect v1 — Corrected in State
- Legacy builders recorded `mean_nesting_score` as majority-parent COVERAGE (~1.0 by construction), not true nesting
- 37/46 audited modes over-claimed 1.0 vs honest strict nesting 0.04–1.0
- **Corrected**: `nesting_score>=0.99` claims PROHIBITED for compressed modes; honest strict nesting 0.39–0.96
- `nesting_score=1.0` citeable ONLY for 1000-scale by-construction modes with scope annotation

### Compressed 5-Level Ladder [0.25, 0.5, 1.0, 2.0, 3.0] — Scope Limited
- **VALID**: 100% purity delta retention and identical zoom navigation at shared resolutions (22 modes)
- **NOT VALID**: Universal strict nesting preservation (honest mean change -0.00364, 21/22 modes nonzero)
- Per-mode depth decisions required; "Compressed ladder NOT universally valid" remains in force

### Dense Embeddings Readiness — COMPLETE
- Parameterized builder fixed: branch derived from chamber field; 'unknown' branches excluded from purity
- Evaluation harness created: `evaluate_174k_dense_embeddings.py` (verified against v26 TF-IDF FAIL verdicts)
- ACCEPTED 174k metadata (173,963 entries, 100% branch+legal_area coverage) and corpus (37 year-split JSONL) available
- Infrastructure ready to consume legal-distance 174k dense embeddings year-split

### Citation-Role 174k Validation — BLOCKED by Evidence
- Placeholder builds (`bger_placeholder_*` IDs) + row→id alignment unrecoverable
- Probe 1 agreement: 0.426 vs ~1.0 expected
- Probe 2: cluster_metadata CORRUPTED (1,003 duplicate IDs, 1,314 extra rows)
- Requires full corpus JSONL delivery from corpus lane

### Product Multi-View Zoom UI — VERIFIED IMPLEMENTED
- CITATION ROLE VIEWS optgroup, zoom controls, split-view, 65 WebGL refs
- Audit recommendation #4 satisfied

---

## Orchestration Failure — Root Cause Confirmed

| Aspect | Detail |
|--------|--------|
| **Root Cause** | Supervisor reads ephemeral `/tmp/lex_control/state/factory_direction.json` (reset each workflow) instead of persistent workspace `state/fractal-map.json` and `state/factory_direction.json` |
| **Symptom** | Supervisor sees `fractal-map.status=RUN` (ephemeral) vs workspace `fractal-map.status=COMPLETED_TFIDF` + `blocked_on=legal-distance_174k_dense_embeddings`, `continue_recommended=false` |
| **Occurrences** | 60+ documented since run 33339971167 |
| **Required Fix** | Factory Director must update supervisor dispatch logic to read workspace state |

---

## Test Results

```
tests/fractal_map/test_verify.py                         184 passed
tests/fractal_map/test_zoom_quality_174k_v26_eval.py       7 passed
tests/fractal_map/test_zoom_quality_174k_eval.py           4 passed
------------------------------------------------------------
Total: 195 passed, 0 failed, 0 skipped
```

---

## State Consistency Verification

All critical state fields match between `state/fractal-map.json` and `results/fractal_map/audit/CYCLE_36094045574_GATE.json`:

- `cycle_status`: COMPLETED ✓
- `continue_recommended`: false ✓
- `blocked_on`: legal-distance_174k_dense_embeddings ✓
- `resume_guard`: final_audit_complete_v12 ✓
- `evidence_tier`: ACCEPTED ✓

---

## Next Recommendation

**BLOCKED on legal-distance_174k_dense_embeddings.**  
Resume when dense embeddings delivered. **No same-question cycle justified.** (`continue_recommended=false`)

The fractal-map lane has completed all work possible with current TF-IDF representations. The evidence-backed path forward requires dense embeddings from legal-distance. The lane state is correctly set to BLOCKED with `continue_recommended=false` so the Factory Director can decide the successor question when the dependency is resolved.

---

## Gate Artifact

`results/fractal_map/audit/CYCLE_36100882865_GATE.json` (to be created)