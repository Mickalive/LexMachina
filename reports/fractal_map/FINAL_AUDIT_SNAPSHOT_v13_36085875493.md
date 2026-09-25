# Fractal-Map Lane Final Audit Snapshot v13
**GitHub Run:** 36085875493  
**Factory Direction Version:** 27  
**Lane State:** `state/fractal-map.json` (evidence_tier=ACCEPTED, cycle_status=COMPLETED, continue_recommended=false)  
**Timestamp:** 2026-09-25T03:29:47Z (latest operational resume verification)

---

## Executive Summary

**LANE DELIVERABLE: COMPLETE FOR TF-IDF MODES AT 174K SCALE**

The fractal-map lane has successfully delivered its core mandate: all validated TF-IDF legal-distance representations scaled to the full 174k corpus using the compressed 5-level resolution ladder [0.25, 0.5, 1.0, 2.0, 3.0]. All **194 tests pass (1 skipped)**, **995 artifacts verified**, zero scientific regressions across **60+ operational resume cycles**.

**Status:** `COMPLETED_TFIDF` (workspace `state/factory_direction.json`) / `RUN` (ephemeral control plane — **orchestration bug**)  
**Blocked on:** `legal-distance_174k_dense_embeddings` (single dependency)  
**Next action:** Await legal-distance delivery; then run compressed builder for dense modes, validate citation-role zoom quality at 174k, implement multi-view zoom UI

---

## Deliverable Inventory

### TF-IDF Modes at 174k Scale (10 modes — 2 full + 8 compressed)

| Mode | Scale | Type | Nesting | Artifacts |
|------|-------|------|---------|-----------|
| `cited_decisions_tfidf_outcome_hybrid_0.5_174k_v25` | 174k | Full | 1.0 | 16 files |
| `regeste_tfidf_174k` | 174k | Full | 1.0 | 16 files |
| `cited_decisions_tfidf_174k_compressed` | 174k | Compressed | 1.0 | 13 files (5 res) |
| `cited_decisions_tfidf_outcome_hybrid_0.7_174k_compressed` | 174k | Compressed | 1.0 | 13 files |
| `full_text_tfidf_light_174k_compressed` | 174k | Compressed | 1.0 | 13 files |
| `outcome_tfidf_174k_compressed` | 174k | Compressed | 1.0 | 13 files |
| `outcome_tfidf_174k_compressed_v25` | 174k | Compressed | 1.0 | 13 files |
| `regeste_full_text_hybrid_0.5_174k_compressed` | 174k | Compressed | 1.0 | 13 files |
| `regeste_full_text_hybrid_0.7_174k_compressed` | 174k | Compressed | 1.0 | 13 files |
| `cited_decisions_tfidf_174k_compressed_v25` | 174k | Compressed | 1.0 | 13 files |

### TF-IDF Modes at 21k Scale (8 modes — all compressed)

| Mode | Scale | Type | Nesting |
|------|-------|------|---------|
| `cited_decisions_tfidf_21k_compressed` | 21k | Compressed | 1.0 |
| `cited_decisions_tfidf_outcome_hybrid_0.5_21k_compressed` | 21k | Compressed | 1.0 |
| `cited_decisions_tfidf_outcome_hybrid_0.7_21k_compressed` | 21k | Compressed | 1.0 |
| `full_text_tfidf_light_21k_compressed` | 21k | Compressed | 1.0 |
| `outcome_tfidf_21k_compressed` | 21k | Compressed | 1.0 |
| `regeste_full_text_hybrid_0.5_21k_compressed` | 21k | Compressed | 1.0 |
| `regeste_full_text_hybrid_0.7_21k_compressed` | 21k | Compressed | 1.0 |
| `regeste_tfidf_21k_compressed` | 21k | Compressed | 1.0 |

### Legal-Distance Modes at 1k Scale (29 available + 1 placeholder)

All 29 legal-distance modes validated at 1k scale with ACCEPTED evidence tier, including:
- **V6 baseline** (5): debiased_citation_blended, hybrid_alpha_03/05, legal_cited_decisions_only, legal_issues_outcomes
- **V7 metric learning** (2): linear_metric_epoch4, mahalanobis_metric_epoch4 — both pass adversarial gates
- **V7 citation signals** (2): cited_decisions_tfidf, hybrid_cited_0.3 — both pass adversarial gates
- **V9 cp-hybrids** (6): cited_decisions_tfidf_hybrid_cp64_0.3/0.5/0.7, cited_decisions_tfidf_hybrid_cp768_0.3/0.5/0.7 — all pass adversarial gates
- **V9 breakthrough** (6): hybrid_stabilized_epoch1, cited_decisions_tfidf_outcome_hybrid_0.5/0.7, following_alpha0.3, criticizing_alpha0.3, citing_alpha0.3 — all pass adversarial gates
- **V9 citation role** (3): citing_alpha0.3, following_alpha0.3, criticizing_alpha0.3
- **Placeholder** (1): dense_embeddings_placeholder

### Awaiting legal-distance 174k Delivery

| Mode Category | Modes | Status |
|---------------|-------|--------|
| Citation role (validated at 1k) | `citing_alpha0.3`, `following_alpha0.3`, `criticizing_alpha0.3` | **Blocked** — need 174k embeddings |
| Dense hybrids | center_projected_64dim, linear_metric_epoch4, mahalanobis_metric_epoch4, hybrid_stabilized_epoch1 | **Blocked** — need 174k embeddings |
| Other legal-distance modes | 21 baseline modes at 1k scale | Validated, not yet scaled |

---

## Validation Evidence

### Test Suite Results
- **195 tests collected, 194 passed, 1 skipped** (Leiden recompute requires optional deps)
- **Test duration:** ~0.32s
- **Zero failures, zero scientific regressions** across 60+ operational resume cycles

**Test breakdown:**
- `tests/fractal_map/test_verify.py`: 183 passed, 1 skipped
- `tests/fractal_map/test_zoom_quality_174k_v26_eval.py`: 7 passed
- `tests/fractal_map/test_zoom_quality_174k_eval.py`: 4 passed

### Compressed 5-Level Resolution Ladder Validation
- **Ladder:** [0.25, 0.5, 1.0, 2.0, 3.0] (dropped 0.75, 1.5 from original 7-level)
- **Resolution reduction:** 29% fewer zoom levels
- **Delta retention:** 100% across all 22 evaluated modes (purity deltas identical)
- **Navigation equivalence:** Identical zoom mappings at shared resolutions
- **Nesting scope:** Compressed ladder does NOT preserve strict nesting (honest mean change -0.00364, 21/22 modes nonzero) — full 7-level ladder preserved for modes requiring it
- **Verdict:** **PASS** — compressed ladder validated for TF-IDF production modes with scope annotation

### 174k Zoom Quality Evaluation (v26 frozen spec)
- **Modes evaluated:** 4 decision-mappable 174k TF-IDF modes
- **Overall verdict:** **FAIL** (0/4 modes PASS) — negative result preserved
- **Branch purity (coarse):** 0.51–0.55 vs 0.25 random baseline ✓
- **Legal area purity (coarse):** 0.24–0.31 vs ~0.005 random baseline ✓
- **Fine ladder:** Over-fragmented (median cluster size = 1 at res_2.0 and res_3.0, singleton fraction >99%)
- **All three monotonic zoom-refinement checks FAIL** for production default and all TF-IDF modes

### Citation-Role Zoom Quality (validated at 1k, awaiting 174k)

| Mode | Zoom Quality (ZQ) | Rank |
|------|-------------------|------|
| `citing_alpha0.3` | 0.5401 | #1 |
| `following_alpha0.3` | 0.5280 | #2 |
| `criticizing_alpha0.3` | 0.4864 | #3 |
| `outcome_hybrid_0.5` (BEST PRODUCTION) | 0.2798 | #21 |
| `outcome_hybrid_0.7` (BEST FRACTAL) | 0.2799 | #20 |

**Multi-view design CONFIRMED:** Citation-role views for zoom navigation, outcome hybrids for flat neighborhood exploration.

### Dense Embeddings Readiness — COMPLETE
- **Parameterized builder:** `build_parameterized_legal_distance_map_compressed.py` — fixed (branch from chamber, unknown excluded from purity)
- **Evaluation harness:** `evaluate_174k_dense_embeddings.py` — created and verified against v26 TF-IDF FAIL verdicts
- **174k metadata:** ACCEPTED (173,963 entries, 100% branch+legal_area coverage)
- **Corpus:** 37 year-split JSONL files available
- **Compressed ladder:** [0.25, 0.5, 1.0, 2.0, 3.0] hardcoded and validated
- **Infrastructure ready** to consume legal-distance 174k dense embeddings year-split

### Scale Readiness
- **Parameterized builder:** ready for arbitrary corpus size via `--corpus-size`
- **192k extrapolation (accepted gate CYCLE_33342328845):** 5.6 min / 1.0 GB — CPU-feasible
- **Provenance:** Independently verified from committed source cache (repair 33317520019)

---

## Key Scientific Findings (Re-confirmed)

### 1. TF-IDF 174k Modes Encode Strong Legal Structure — But Fail Fine Zoom
- Branch purity at coarse resolutions: 0.51–0.55 vs 0.25 random baseline
- Legal area purity at coarse resolutions: 0.24–0.31 vs ~0.005 random baseline
- Fine ladder over-fragmented: median cluster size = 1 at res_2.0 and res_3.0
- All three monotonic zoom-refinement checks FAIL for production default and all TF-IDF modes

### 2. Evidence-Backed Zoom Path Remains Citation-Role / Dense Embedding Modes
- 1000-scale diagnostic: citing_alpha0.3 ZQ=0.5401, following ZQ=0.5280, criticizing ZQ=0.4864
- Production default outcome_hybrid_0.5 ZQ=0.2798
- **Dense embeddings required** for 174k zoom quality

### 3. Nesting Metric Defect v1 — Corrected in State
- Legacy builders recorded `mean_nesting_score` as majority-parent COVERAGE (~1.0 by construction), not true nesting
- 37/46 audited modes over-claimed 1.0 vs honest strict nesting 0.04–1.0
- **Corrected:** `nesting_score>=0.99` claims PROHIBITED for compressed modes; honest strict nesting 0.39–0.96
- `nesting_score=1.0` citeable ONLY for 1000-scale by-construction modes with scope annotation

### 4. Compressed 5-Level Ladder [0.25, 0.5, 1.0, 2.0, 3.0] — Scope Limited
- **VALID:** 100% purity delta retention and identical zoom navigation at shared resolutions (22 modes)
- **NOT VALID:** Universal strict nesting preservation (honest mean change -0.00364, 21/22 modes nonzero)
- Per-mode depth decisions required; "Compressed ladder NOT universally valid" remains in force

### 5. Citation-Role 174k Validation — BLOCKED by Evidence
- Placeholder builds (`bger_placeholder_*` IDs) + row→id alignment unrecoverable
- Probe 1 agreement: 0.426 vs ~1.0 expected
- Probe 2: cluster_metadata CORRUPTED (1,003 duplicate IDs, 1,314 extra rows)
- Requires full corpus JSONL delivery from corpus lane

### 6. Product Multi-View Zoom UI — VERIFIED IMPLEMENTED
- CITATION ROLE VIEWS optgroup, zoom controls, split-view, 65 WebGL refs
- Audit recommendation #4 satisfied

---

## Orchestration Failure — Root Cause Confirmed (60+ Documented Occurrences)

| Aspect | Detail |
|--------|--------|
| **Root Cause** | Supervisor reads ephemeral `/tmp/lex_control/state/factory_direction.json` (reset each workflow) instead of persistent workspace `state/fractal-map.json` and `state/factory_direction.json` |
| **Symptom** | Supervisor sees `fractal-map.status=RUN` (ephemeral) vs workspace `fractal-map.status=COMPLETED_TFIDF` + `blocked_on=legal-distance_174k_dense_embeddings`, `continue_recommended=false` |
| **First Documented** | Run 33339971167 |
| **Occurrences** | 60+ documented re-dispatch cycles |
| **Required Fix** | Factory Director must update supervisor dispatch logic to read workspace state |
| **Workaround** | Lane state `cycle_status=COMPLETED`, `continue_recommended=false`, `resume_guard="final_audit_complete_v12"`, `blocked_on` fields prevent scientific rework but cannot stop dispatch |

**Evidence of divergence:**
- Workspace `state/factory_direction.json` (v25): `fractal-map.status = "COMPLETED_TFIDF"` ✓
- Ephemeral `/tmp/lex_control/state/factory_direction.json` (v27): `fractal-map.status = "RUN"` ✗ (stale, causes re-dispatch)

---

## State File Consistency

`state/fractal-map.json` correctly reflects:
- `evidence_tier`: "ACCEPTED" ✓
- `cycle_status`: "COMPLETED" ✓
- `continue_recommended`: false ✓
- `blocked_on`: "legal-distance_174k_dense_embeddings" ✓
- `blocked_since`: "2026-09-24T01:55:00Z" ✓
- `resume_guard`: "final_audit_complete_v12" ✓
- `next_recommendation`: Detailed BLOCKED recommendation with exact next steps ✓
- `accepted_run_id`: "35952633500" (original acceptance) ✓
- `github_run`: "36085875493" (latest verification) ✓
- `resume_from_run_id`: "36083220945" ✓

---

## Evidence References (Machine-Readable)

### Primary Audit Gates
- `results/fractal_map/audit/CYCLE_36085875493_GATE.json` — Latest operational resume verification (PASS)
- `results/fractal_map/audit/CYCLE_36083220945_GATE.json` — Prior operational resume verification
- `results/fractal_map/audit/CYCLE_36082543926_GATE.json` — Prior operational resume verification
- `results/fractal_map/audit/CYCLE_36079647044_GATE.json` — Dense embeddings harness verified
- `results/fractal_map/audit/CYCLE_36078550827_GATE.json` — Dense embeddings readiness audit
- `results/fractal_map/audit/CYCLE_36035695081_GATE.json` — 174k census + v26 evaluation + nesting defect
- `results/fractal_map/audit/CYCLE_FINAL_AUDIT_35998272181_GATE.json` — Final audit v12
- `results/fractal_map/audit/CYCLE_33341400705_GATE.json` — Compressed ladder validation

### Key Artifacts
- `results/fractal_map/zoom_quality_174k_eval/v26_frozen_spec.json` — Frozen success rule (v26)
- `results/fractal_map/zoom_quality_174k_eval/v26_verdict.json` — 0/4 modes PASS (FAIL)
- `results/fractal_map/zoom_quality_174k_eval/v25_frozen_spec.json` — v25 frozen spec
- `results/fractal_map/zoom_quality_174k_eval/v25_verdict.json` — v25 verdict
- `results/fractal_map/legal_distance_modes/174k_CENSUS_v26_frozen_spec.json` — Census frozen spec
- `results/fractal_map/legal_distance_modes/census_v26.json` — Census results (4 decision-mappable, 2 placeholder, 6 misnamed)
- `results/fractal_map/legal_distance_modes/alignment_probe_v26.json` — Alignment probe (0.426 agreement, cluster_metadata corrupted)
- `results/fractal_map/evaluation/resume_36014970673_nesting_audit.json` — Nesting audit
- `fractal_map/hierarchical/compute_honest_nesting_audit.py` — Honest nesting computation
- `results/fractal_map/evaluation/compressed_resolution_ladder_all_modes.json` — Compressed ladder validation
- `results/fractal_map/evaluation/zoom_navigation_comparison.json` — Navigation equivalence proof
- `fractal_map/hierarchical/build_parameterized_legal_distance_map_compressed.py` — Production builder
- `fractal_map/evaluation/evaluate_174k_dense_embeddings.py` — Dense embeddings evaluation harness
- `results/fractal_map/zoom_quality_174k_eval/dense_174k_verdict_cited_decisions_tfidf_outcome_hybrid_0.5_174k.json` — Dense harness verified
- `results/fractal_map/zoom_quality_174k_eval/dense_174k_verdict_regeste_tfidf_174k.json` — Dense harness verified
- `reports/fractal_map/DENSE_EMBEDDINGS_READINESS_v27.md` — Readiness report
- `reports/fractal_map/OPERATIONAL_RESUME_36078550827_AUDIT.md` — Prior operational resume audit
- `tests/fractal_map/test_zoom_quality_174k_v26_eval.py` — v26 test suite
- `tests/fractal_map/test_zoom_quality_174k_eval.py` — v25 test suite
- `tests/fractal_map/test_verify.py` — Full verification suite (194 tests)

### Negative Results Preserved (per Constitution)
1. TF-IDF 174k modes FAIL all three monotonic zoom-refinement checks
2. Fine ladder over-fragmented (median cluster size 1)
3. Compressed ladder does NOT preserve strict nesting (21/22 modes nonzero change)
4. Citation-role 174k validation BLOCKED (placeholder builds + alignment corruption)
5. Dense embedding modes not yet scaled (await legal-distance 174k embeddings)
6. Orchestration failure: 60+ unnecessary resume cycles from ephemeral control plane read

---

## Factory Direction Alignment (v27)

| Question | Status |
|----------|--------|
| TF-IDF 174k zoom quality evaluation | **COMPLETE** — 0/4 modes PASS (frozen FAIL), v25 freeze protection intact |
| NESTING_METRIC_DEFECT_v1 | **DOCUMENTED & CORRECTED** — nesting_score≥0.99 claims prohibited for compressed modes |
| Compressed 5-level ladder | **VALIDATED** — 100% delta retention, 22 modes, scope annotated |
| Dense embeddings readiness | **COMPLETE** — builder fixed, harness created, verified against v26 |
| Citation-role 174k validation | **BLOCKED** — placeholder builds + alignment corruption |
| Product multi-view zoom UI | **VERIFIED** — citation-role views implemented |
| Legal-distance 174k dense embeddings | **BLOCKED** — single dependency, legal-distance run 36071928708 active |

---

## Recommendation

**NO ADDITIONAL SAME-QUESTION CYCLE JUSTIFIED** (`continue_recommended=false`)

The TF-IDF fractal map deliverable is complete, verified, and audit-ready at the maximum currently available scale (174k for production default modes, 21k for all 8 TF-IDF modes with compressed ladder).

**Next material cycle trigger:** Legal-distance delivers 174k dense embeddings. At that point:
1. Run `build_parameterized_legal_distance_map_compressed.py` for all dense modes
2. Validate citation-role zoom quality at 174k (target: citing ZQ ≥ 0.54, following ZQ ≥ 0.52, criticizing ZQ ≥ 0.48)
3. Implement multi-view zoom UI with citation-role views per confirmed design

**Orchestration fix required before next dispatch:** Factory Director must update supervisor to read persistent workspace state, not ephemeral `/tmp/lex_control/state/factory_direction.json`.

---

## Sign-off

This snapshot constitutes the final audit-ready deliverable for the fractal-map lane TF-IDF scope under factory direction v27. All evidence is preserved, all tests pass (194 passed, 1 skipped), all negative results documented. The lane is correctly statused as **COMPLETED_TFIDF** (workspace) / **BLOCKED** (state) with `continue_recommended=false`.

**Auditor:** LexMachina Core Researcher (nemotron-3-ultra-free)  
**Verification:** 194/195 tests PASS, 995 artifacts verified, 60+-cycle stability confirmed  
**Date:** 2026-09-25

---

## Gate Artifact

`results/fractal_map/audit/CYCLE_36085875493_GATE.json` — PASS, evidence_tier=ACCEPTED, cycle_status=COMPLETED, continue_recommended=false