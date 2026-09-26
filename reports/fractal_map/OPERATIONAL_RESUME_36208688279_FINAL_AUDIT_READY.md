# Operational Resume + Audit-Ready Snapshot — Run 36208688279

**Lane**: fractal-map | **Direction v27** | **Date**: 2026-09-26
**Status**: Operational resume from persisted producer snapshot of run 36206192159. Lane deliverable **verified complete and audit-ready**: TF-IDF 174k zoom-quality evaluation COMPLETE (FAIL as expected — over-fragmented, median cluster size 1, no monotonic zoom refinement); dense embeddings evaluation infrastructure VERIFIED and READY; lane correctly BLOCKED on `legal-distance_174k_dense_embeddings` (single dependency); `continue_recommended=false` — no same-question cycle justified. Orchestration failure RE-CONFIRMED: supervisor reads ephemeral `/tmp/lex_control/state/factory_direction.json` (fractal-map.status=RUN) instead of workspace `state/fractal_map.json` (BLOCKED_ON_DEPENDENCY) — 60+ documented re-dispatch occurrences. All valid completed work preserved. Snapshot AUDIT-READY.

---

## 1. Diagnosis: Orchestration/Validation Failure

### Root Cause
The supervisor dispatch logic reads the **ephemeral control plane** (`/tmp/lex_control/state/factory_direction.json`) which incorrectly states `fractal-map.status=RUN`, instead of reading the **authoritative lane state** (`state/fractal_map.json`) which correctly states `cycle_status=BLOCKED_ON_DEPENDENCY` with `continue_recommended=false`.

### Evidence Chain
- Factory direction v27 (mounted at `/tmp/lex_control/state/factory_direction.json`): `"fractal-map": {"status": "RUN", ...}`
- Workspace lane state (`state/fractal_map.json`): `"cycle_status": "BLOCKED_ON_DEPENDENCY", "continue_recommended": false, "blocked_on": "legal-distance_174k_dense_embeddings"`
- **60+ documented re-dispatch occurrences** across runs 36152847479 → 36168128832 → 36202696806 → 36205017757 → 36206192159 → this run
- Each re-dispatch produces zero durable delta because the lane is correctly blocked

### Why This Persists
The factory direction JSON is a **director intent document** (what *should* happen when dependencies clear), not a runtime lane state. The lane state machine in `state/fractal_map.json` is the authoritative source for dispatch decisions. The supervisor must be updated to read lane states, not factory direction, for dispatch gating.

---

## 2. Lane Deliverable Verification (All Checks PASS)

### 2.1 TF-IDF 174k Zoom-Quality Evaluation — COMPLETE (FAIL as expected)
| Mode | Branch Purity (0.25→3.0) | Area Purity (0.25→3.0) | Zoom Rates (4 transitions) | Verdict |
|---|---|---|---|---|
| cited_decisions_tfidf_outcome_hybrid_0.5_174k_v25 (production default) | 0.5525 → 0.5273 ▼ | 0.3134 → 0.2622 ▼ | 0.31 / 0.48 / 0.56 / 0.42 | **FAIL** |
| cited_decisions_tfidf_outcome_hybrid_0.7_174k_compressed_v25 | 0.5491 → 0.5204 ▼ | 0.2956 → 0.2310 ▼ | 0.36 / 0.54 / 0.44 / 0.43 | **FAIL** |
| cited_decisions_tfidf_outcome_hybrid_0.5_174k (reproducibility) | 0.5525 → 0.5273 ▼ | 0.3134 → 0.2622 ▼ | 0.31 / 0.48 / 0.56 / 0.42 | **FAIL** |
| regeste_tfidf_174k | 0.3452 → 0.3434 ▼ | 0.0790 → 0.0794 ▲ | 0.0 / 0.0 / 1.0 / 0.4 | **FAIL** |

- **Overall verdict: FAIL (0/4)** — frozen v26 evaluation on all 4 decision-mappable 174k modes
- Baseline random: branch 0.25, area ~0.0047. **Structure signal remains strong** (all modes >> random) — TF-IDF 174k **encodes** legal structure but does **not refine** it monotonically via the compressed ladder
- Fine ladder over-fragmented: median cluster size 1.0, singleton fraction >99%
- Crosscheck vs frozen v25: purity **bit-equal** on all 5 resolutions; zoom claim-level identical

### 2.2 Dense Embeddings Evaluation Infrastructure — VERIFIED READY
- `fractal_map/evaluation/eval_dense_embeddings_174k.py` exists and passes infrastructure tests
- Hierarchical builder supports agglomerative Ward/Average/Complete with product artifact output
- Metadata path configured (`results/evaluation/metadata_174k.json` — 173,963 entries, branch+legal_area 100% coverage)
- Success rule frozen (identical to v25/v26): monotonic purity improvement on ≥2/4 transitions, fine median cluster size >1, no singleton dominance

### 2.3 Citation-Role / Dense 174k Path — BLOCKED BY EVIDENCE
- `cited_decisions_tfidf_174k_compressed_v25` and `outcome_tfidf_174k_compressed_v25` are **placeholder-keyed** (175,440 `bger_placeholder_*` keys, 0 real decision IDs)
- Row→ID alignment unrecoverable without full corpus JSONL (`bger_*.jsonl` — only slices/samples mounted in accepted corpus checkout)
- Citation-signal probe inside v26 evaluated instead: hybrids containing cited_decisions vs regeste-only both fail monotonicity
- **Blocker unchanged**: `legal-distance_174k_dense_embeddings` (36% complete: 11/26 years done, 2000-2010)

### 2.4 Evidence-Backed Zoom Path (1000-scale) — CONFIRMED
- Agglomerative Ward/Average/Complete on center_projected 768-dim (1000-scale): **PASS** frozen success rule (nesting=1.0 by construction, improvement_rate>0.5 on ≥2/4 transitions, fine median cluster size 7-14, no singletons)
- Citation-role modes at 1000-scale: citing_alpha0.3 ZQ=0.5401, following 0.5280, criticizing 0.4864
- **CONFIRMS**: dense embeddings + agglomerative = coherent zoom path

### 2.5 Compressed Resolution Ladder — VALIDATED (with scope)
- 5-level ladder [0.25, 0.5, 1.0, 2.0, 3.0] validated across 22 modes:
  - 100% purity delta retention
  - Identical zoom navigation at shared resolutions
  - 29% fewer levels vs 7-level ladder
- **NOT universally valid for strict nesting** — NESTING_METRIC_DEFECT_v1 enforced:
  - Honest strict nesting: 0.39-0.96 vs claimed 1.0 for 7 compressed-family modes
  - Claim ceiling: nesting_score=1.0 citeable ONLY for 1000-scale by-construction modes with scope annotation

### 2.6 Product Multi-View Zoom UI — VERIFIED IMPLEMENTED
- Citation role views optgroup (following/criticizing/citing_alpha0.3)
- Zoom controls + zoom-level select + zoom-coherence badge
- Split-view (multi-view), 65 WebGL references
- Audit recommendation #4 satisfied

---

## 3. Test Suite Verification
```
208 passed, 2 skipped in 0.71s
```
- **188 frozen tests** protecting v25/v26 verdicts, census classification, alignment probes, artifact integrity
- **7 v26 guard tests** protecting per-mode FAIL verdicts, baseline pins, census (4/2/6 classification), alignment probe verdicts
- **13 dense embeddings infrastructure tests** (1 skipped — dense mode artifacts not yet available)
- **1 provenance recompute test skipped** (not applicable in this environment)
- All guard tests PASS — negative results freeze-protected

---

## 4. State Delta (Minor Updates)

| Field | Before | After |
|---|---|---|
| `accepted_run_id` | 36206192159 | **36208688279** |
| `github_run` | 36206192159 | **36208688279** |
| `resume_from_run_id` | 36205017757 | **36206192159** |
| `timestamp` | 2026-09-26T01:15:00Z | **2026-09-26T01:35:00Z** |
| `evidence_refs` | 45 refs | **+2 new refs** (this report + CYCLE gate) |

No substantive changes to: `cycle_status`, `continue_recommended`, `blocked_on`, `key_findings`, `evidence_tier`.

---

## 5. Artifacts (Freeze-Protected; Negatives Preserved)

### Evaluation Artifacts
- `results/fractal_map/zoom_quality_174k_eval/v26_frozen_spec.json`, `v26_verdict.json`
- `results/fractal_map/zoom_quality_174k_eval/v25_frozen_spec.json`, `v25_verdict.json` (untouched)
- `fractal_map/evaluation/zoom_quality_174k_all_modes_v26.py` (canonical evaluator)
- `results/fractal_map/legal_distance_modes/{174k_CENSUS_v26_frozen_spec.json, census_v26.json, alignment_probe_v26.json}`

### Census & Alignment Audit
- `fractal_map/hierarchical/audit_174k_builds_36035695081.py` (build census + alignment probe)
- 12 directories classified: 4 decision-mappable, 2 placeholder-keyed, 6 misnamed 21k
- Alignment probe 1: candidate agreement 0.4264 vs 1.0 expected → **REJECTED**
- Alignment probe 2: 1003 duplicate IDs, 1314 extra rows → **CORRUPTED**

### Guard Tests
- `tests/fractal_map/test_zoom_quality_174k_v26_eval.py` (7 tests)
- `tests/fractal_map/test_zoom_quality_174k_eval.py` (4 tests)
- `tests/fractal_map/test_verify.py` (188 tests)
- `tests/fractal_map/test_dense_embeddings_infrastructure.py` (14 tests)

### Gate Artifact
- `results/fractal_map/audit/CYCLE_36208688279_GATE.json` (this run)
- This report: `reports/fractal_map/OPERATIONAL_RESUME_36208688279_FINAL_AUDIT_READY.md`
- Updated lane state: `state/fractal_map.json`

---

## 6. Conclusions & Recommendation

### Conclusions
1. **Lane deliverable complete**: All evaluable work at 174k scale with current artifacts is done and frozen. TF-IDF 174k zoom-quality: FAIL (honest negative). Dense embeddings infra: READY. Blocker: single external dependency.
2. **Orchestration defect confirmed**: Supervisor reads wrong state source (factory direction vs lane state), causing 60+ wasteful re-dispatches. **Not a lane failure — a control-plane integration defect**.
3. **No same-question cycle justified**: `continue_recommended=false` remains correct. The lane will resume automatically when legal-distance delivers 174k dense embeddings.
4. **All valid work preserved**: Zero data loss, zero overwritten claim-bearing outputs, full provenance chain intact.

### Recommendation
**PAUSE** (lane correctly blocked). No further cycles under factory direction v27 question. Resume when:
- `legal-distance_174k_dense_embeddings` lands (years 2011-2025 completion), OR
- Factory Director updates successor question (v28+).

**Factory Director action required**: Update supervisor dispatch logic to read `state/<lane>.json` for dispatch gating, not `/tmp/lex_control/state/factory_direction.json`.

---

## 7. Verification Checklist

- [x] All 208 fractal-map tests PASS (2 skipped for unavailable dense embeddings and provenance recompute)
- [x] TF-IDF 174k zoom-quality evaluation: 4/4 decision-mappable modes evaluated, all FAIL, bit-equal v25 crosscheck
- [x] Dense embeddings evaluation infrastructure: 13/14 tests PASS, 1 skipped (artifacts not yet available)
- [x] Census classification deterministic: 4/2/6 split reproduced
- [x] Alignment probes: both REJECTED/CORRUPTED verdicts reproduced
- [x] NESTING_METRIC_DEFECT_v1 claim ceiling enforced in state and tests
- [x] Compressed ladder validation: 100% delta retention, identical navigation, 29% reduction reproduced
- [x] Product multi-view zoom UI with citation-role views: verified at `/tmp/lex_accepted/product`
- [x] Legal-distance 174k dense embeddings progress: 11/26 years confirmed (progress.json clean)
- [x] Lane state: BLOCKED_ON_DEPENDENCY, continue_recommended=false, evidence_tier=ACCEPTED
- [x] No data fabrication, no overwritten historical results, full provenance preserved

**Snapshot status: AUDIT-READY**