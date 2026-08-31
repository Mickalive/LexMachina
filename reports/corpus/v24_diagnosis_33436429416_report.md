# Corpus Lane v24 — Orchestration Failure Diagnosis & Audit-Ready Verification

**Run ID**: 33436429416
**Factory Direction**: v14
**Date**: 2026-08-31
**Lane**: corpus
**Cycle Type**: Operational resume from snapshot 33435211349

## Executive Summary

Diagnosed the orchestration/validation failure causing redundant corpus lane dispatches. Verified all 65/65 offline tests PASS after data regeneration. Confirmed state file is audit-ready with all consistency checks passing. The corpus lane is COMPLETE — no further cycles needed.

## Orchestration Failure Diagnosis

### Root Cause

The supervisor dispatches redundant corpus lane cycles because it reads `factory_direction.json` status (stale: `"RUN"`) instead of `state/corpus.json` cycle_status (correct: `"COMPLETED"`).

**Evidence chain:**
1. `factory_direction.json` corpus lane: `"status": "RUN"` — never updated to `"COMPLETE"`
2. `state/corpus.json`: `"cycle_status": "COMPLETED"`, `"continue_recommended": false`
3. Result: supervisor sees "RUN" → dispatches new cycle → cycle finds nothing to do → produces zero-delta report → supervisor re-reads stale status → repeat

### Failure Mode History

| Cycle | Type | Outcome | Delta |
|-------|------|---------|-------|
| 33428790938 | v20 independent verification | PASS | Full corpus regeneration, 65/65 tests |
| 33431304963 | v21 independent verification | PASS | Identical results, 65/65 tests |
| 33433428793 | v22 5th verification | REVISE | 3 defects: trimmed evidence_refs, false outcome=1.0, self-referencing note |
| 33435211349 | v23 repair of 33433428793 | PASS | 3 defects fixed, 13/13 tests (pyarrow missing in env) |
| 33436429416 | v24 operational resume | **THIS CYCLE** | Full re-verification: 65/65 tests, all consistency checks |

**Pattern**: Cycles 33431304963, 33433428793, and 33436429416 all did identical work (regenerate corpus, run tests, confirm completeness). The only non-zero delta across all these cycles was the field_coverage correction in 33435211349 (outcome 1.0 → 0.505).

### Architectural Fix Required

The supervisor must read `state/<lane>.json` `cycle_status` field instead of `factory_direction.json` `lanes.<lane>.status`. The factory_direction.json status is a Director-level directive, not a real-time state indicator.

### Documented in Prior Reports

- v20 report: "Root Cause of Prior Orchestration Failures" section
- v21 report: "Action required by Factory Director: Update factory_direction.json to mark corpus lane status as DONE"
- v22 report: "Note: last cycle 33371028376 was AUDIT_BLOCKED for redundantly re-running accepted v16 with zero new science"
- factory_direction.json director_note: "Supervisor dispatch must be idempotent" + "fractal-map and evaluation lanes have documented 46+ and 6+ unnecessary resume cycles respectively due to supervisor reading ephemeral /tmp state instead of workspace state"

## Verification Results

### Test Suite: 65/65 PASS

| Suite | Tests | Pass | Fail |
|-------|-------|------|------|
| test_cycle_v14.py | 31 | 31 | 0 |
| test_cycle_v11.py | 21 | 21 | 0 |
| test_repair_cycle33032428186.py | 6 | 6 | 0 |
| test_pipeline.py | 7 | 7 | 0 |
| **Total** | **65** | **65** | **0** |

### Data Regeneration

- Source: HuggingFace `voilaj/swiss-caselaw` bger.parquet (822.8 MB)
- Parquet SHA-256: `74f3b2d683b6c298efc6e287cd88244cc19f38af38e060cc4d4e5cf5f938a62d`
- Rows processed: 174,114
- Normalized: 174,113 (1 duplicate skipped)
- Year-split files: 37 (bger_1986.jsonl through bger_2026.jsonl)
- Regeneration time: ~2 minutes

### State File Audit: ALL CHECKS PASS

| Check | Result |
|-------|--------|
| canonical triple-equal | 174,113 == 174,113 == 174,113 ✓ |
| language_distribution sum == total | 174,113 == 174,113 ✓ |
| year_coverage sum == total | 174,113 == 174,113 ✓ |
| schema_validation total == total | 174,113 == 174,113 ✓ |
| citation resolved + unresolved == total | 2,019 + 86 == 2,105 ✓ |
| outcome: state == ground_truth | 0.505 == 0.505 ✓ |
| regeste: state == ground_truth | 0.474 == 0.474 ✓ |
| cited_decisions: state == ground_truth | 0.526 == 0.526 ✓ |
| legal_area: state == ground_truth | 0.526 == 0.526 ✓ |
| manifest records == total | 174,113 == 174,113 ✓ |
| manifest year_files == 37 | 37 == 37 ✓ |
| resolved citation graph exists | ✓ |
| resolution_stats present | ✓ |
| outgoing present | ✓ |

### Ground Truth Alignment

Field coverage values now exactly match `validation_report_v14.json`:

| Field | State Value | Ground Truth | Match |
|-------|------------|-------------|-------|
| full_text | 1.0 | 1.0 | ✓ |
| regeste | 0.474 | 0.474 | ✓ |
| cited_decisions | 0.526 | 0.526 | ✓ |
| outcome | 0.505 | 0.505 | ✓ |
| legal_area | 0.526 | 0.526 | ✓ |
| bge_reference | 0.0 | 0.0 | ✓ |
| cited_laws | 0.0 | 0.0 | ✓ |

## Lane Deliverable Status

| v14 Objective | Status |
|---------------|--------|
| Full corpus acquired (174,113 decisions, 2000-2026) | ✅ COMPLETE |
| Citation ID resolution pipeline (95.9% rate) | ✅ COMPLETE |
| User corpus import with schema validation | ✅ COMPLETE |
| All 65 offline tests PASS | ✅ VERIFIED |
| Data artifacts consistent | ✅ VERIFIED |
| State file audit-ready | ✅ VERIFIED |

## Recommendation

**CORPUS_LANE_COMPLETE_UNBLOCK_DEPENDENTS** — No further corpus lane cycles needed.

The Factory Director must:
1. Update `factory_direction.json` corpus lane status from `"RUN"` to `"COMPLETE"`
2. Unblock dependent lanes (legal-distance, fractal-map, evaluation) with clarification that 174k IS the full BGer dataset
3. Fix supervisor dispatch to read `state/<lane>.json` instead of `factory_direction.json` status

## Evidence References

- `corpus/acquisition/reproduce_full_corpus.py` — canonical reproduction script
- `corpus/acquisition/citation_resolver.py` — citation resolution pipeline
- `corpus/acquisition/parquet_ingest_scaled.py` — scaled ingestion pipeline
- `corpus/acquisition/user_import_hardened.py` — hardened user import
- `corpus/tests/test_cycle_v14.py` — 31 tests
- `corpus/tests/test_cycle_v11.py` — 21 tests
- `corpus/tests/test_repair_cycle33032428186.py` — 6 tests
- `corpus/tests/test_pipeline.py` — 7 tests
- `corpus/normalization/canonical/ingestion_metrics.json` — production metrics
- `corpus/normalization/canonical/validation_report_v14.json` — ground truth
- `corpus/normalization/canonical/manifest_v14_reproduction.json` — verifiable manifest
- `corpus/normalization/canonical/resolved_full/citation_graph_resolved.json` — resolved citations
- `reports/corpus/v23_repair_33433428793_report.md` — prior repair report
- `reports/corpus/v21_cycle_33431304963_report.md` — prior verification report
- `reports/corpus/v20_cycle_33428790938_report.md` — prior verification report
