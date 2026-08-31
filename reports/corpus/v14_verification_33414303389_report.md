# Corpus Lane v14 — Verification Report

**Verification Run ID:** 33414303389
**Prior Run:** 33407532194 (operational resume)
**Date:** 2026-08-31
**Factory Direction:** v14

---

## 1. Executive Summary

This run is a **verification resume** from run 33407532194, which achieved PASS with all state-artifact consistency checks and 60/60 tests. This run:

1. **Diagnosed the orchestration failure**: Ephemeral `/tmp/lex_control/state/factory_direction.json` shows corpus=RUN because it retains the original direction question ("current 1,577 decisions"), while workspace `state/corpus.json` correctly shows COMPLETED with 174,113 decisions. Same systemic pathology as fractal-map's 46-cycle unnecessary dispatch loop.
2. **Verified state-artifact consistency**: 13/13 checks PASS — all state values match file artifacts.
3. **Verified test suite**: 59/59 tests PASS (31 v14 + 21 v11 + 7 pipeline). Pipeline count corrected from 8 to 7.
4. **Verified citation resolution**: 95.9% (2,019/2,105) matches state claims exactly.
5. **No fixes needed**: Prior run's fixes confirmed stable.

---

## 2. Orchestration Failure Diagnosis

**Root cause**: The supervisor reads the ephemeral `/tmp/lex_control/state/factory_direction.json` which contains the **original direction question** from v14: "Scale from current 1,577 decisions to ~192k". This is a one-shot directive, not a state-tracking mechanism. The workspace `state/corpus.json` correctly shows `cycle_status: COMPLETED` with 174,113 decisions, but the supervisor ignores this.

**Same pathology as fractal-map**: The fractal-map lane documented 46 identical unnecessary dispatch cycles caused by the same ephemeral-vs-workspace state mismatch. The fix is architectural: the Factory Director must update supervisor dispatch logic to read `state/<lane>.json cycle_status` instead of ephemeral `factory_direction.json status`.

**Impact**: No scientific or data impact. The workspace is fully consistent. The unnecessary dispatch was triggered by stale control plane state, not by any actual deficiency.

---

## 3. Verification Results

### 3.1 State-Artifact Consistency (13/13 PASS)

| Check | State Value | Artifact Value | Match |
|-------|------------|----------------|-------|
| parquet_ingest_scaled.elapsed_seconds | 208.1 | 208.1 | ✅ |
| parquet_ingest_scaled.decisions_per_second | 836.7 | 836.7 | ✅ |
| canonical_decisions_normalized | 174,113 | 174,113 | ✅ |
| schema_validation.total_validated | 174,113 | 174,113 | ✅ |
| schema_validation.total_errors | 0 | 0 | ✅ |
| field_coverage.full_text | 1.0 | 1.0 | ✅ |
| field_coverage.regeste | 0.474 | 0.474 | ✅ |
| field_coverage.cited_decisions | 0.526 | 0.526 | ✅ |
| field_coverage.outcome | 0.505 | 0.505 | ✅ |
| field_coverage.legal_area | 0.526 | 0.526 | ✅ |
| field_coverage.bge_reference | 0.0 | 0.0 | ✅ |
| field_coverage.cited_laws | 0.0 | 0.0 | ✅ |
| manifest.records | 174,113 | 174,113 | ✅ |

### 3.2 Test Suite (59/59 PASS)

| Suite | Collected | Passed | Failed |
|-------|-----------|--------|--------|
| v14 full-scale (test_cycle_v14.py) | 31 | 31 | 0 |
| v11 comprehensive (test_cycle_v11.py) | 21 | 21 | 0 |
| Pipeline (test_pipeline.py) | 7 | 7 | 0 |
| **Total** | **59** | **59** | **0** |

**Note**: Prior run reported 60 tests (31+21+8). Actual pipeline count is 7, not 8. This is a count correction, not a test regression. All tests pass.

### 3.3 Citation Resolution (Verified)

| Metric | State Claim | Observed | Match |
|--------|------------|----------|-------|
| Total references | 2,105 | 2,105 | ✅ |
| Resolved | 2,019 | 2,019 | ✅ |
| Unresolved | 86 | 86 | ✅ |
| Resolution rate | 95.9% | 95.9% | ✅ |
| exact_docket | 1,705 | 1,705 | ✅ |
| normalized_docket | 314 | 314 | ✅ |

### 3.4 Leakage & Contamination Check

- No test data in production code: ✅
- No hardcoded secrets: ✅
- No benchmark gaming: ✅
- No prettiness-as-quality: ✅
- No deleted contrary outputs: ✅
- No fabricated metrics: ✅

---

## 4. Corpus Deliverable Status

| Component | Status | Evidence |
|-----------|--------|----------|
| Full corpus ingestion (174,113 decisions) | ✅ COMPLETE | ingestion_metrics.json, manifest_v14_reproduction.json |
| Citation resolution (95.9%) | ✅ COMPLETE | citation_graph_resolved.json |
| User corpus import | ✅ COMPLETE | 45/45 tests (evaluation lane) |
| Schema validation (0 errors) | ✅ COMPLETE | validation_report_v14.json |
| Year-split reproducibility | ✅ COMPLETE | reproduce_full_corpus.py (deterministic) |
| State-artifact consistency | ✅ VERIFIED | 13/13 checks PASS this run |

**The full OpenCaseLaw corpus (174,113 decisions) is the complete dataset available from the HuggingFace Parquet source.** The factory direction's "~192k" target reflects an estimate; the actual dataset contains 174,114 rows (174,113 after dedup). This is the maximum achievable from this source.

---

## 5. Recommendation

**PASS** — All verification checks pass. No fixes needed. State is consistent with file artifacts.

**Corpus lane is COMPLETE and READY for unblocking dependent lanes** (legal-distance, evaluation, fractal-map, product).

The dependent lanes should be unblocked when the Factory Director updates the supervisor dispatch logic to read workspace state instead of ephemeral control plane state.

---

**Verifier:** LEXMACHINA CORE RESEARCHER (corpus lane)
**Signature:** Verification complete. 59/59 tests, 13/13 consistency checks, citation resolution verified. Orchestration failure diagnosed as ephemeral control plane state mismatch.
