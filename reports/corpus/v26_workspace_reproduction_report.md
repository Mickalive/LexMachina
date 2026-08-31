# Corpus Lane v26 — Workspace Reproduction Verification

**Run ID**: 33451894801
**Factory Direction**: v14
**Date**: 2026-08-31
**Lane**: corpus
**Cycle Type**: Workspace reproduction (parquet + year files absent → regenerated from HuggingFace)

## Executive Summary

Successfully reproduced the full 174,113-decision corpus in a fresh workspace where parquet and year-split files were absent (gitignored). Downloaded 822.8 MB parquet from HuggingFace `voilaj/swiss-caselaw`, regenerated all 37 year-split files (1986-2026), verified all 75/75 tests PASS, confirmed citation resolver at 95.9% resolution, verified user import pipeline end-to-end. This is the 7th independent verification confirming identical results.

## Reproduction Procedure

1. **Initial state**: Workspace had no `corpus/acquisition/parquet/` directory and no `bger_*.jsonl` year-split files (both gitignored)
2. **Parquet download**: 822.8 MB from HuggingFace `voilaj/swiss-caselaw` (SHA-256: `74f3b2d683b6c298efc6e287cd88244cc19f38af38e060cc4d4e5cf5f938a62d`)
3. **Corpus regeneration**: `reproduce_full_corpus.py` → 174,113 normalized decisions, 0 errors, ~116s
4. **Post-regeneration**: 75-test suite → 75/75 PASS
5. **Citation resolver**: `build_index()` → 196,668 decisions indexed, 95.9% resolution rate
6. **User import**: End-to-end JSONL import verified (schema validation, artifacts created)
7. **Manifest integrity**: All 37 year files match SHA-256 and line counts from manifest

## Verification Results

### Test Suite: 75/75 PASS

| Suite | Tests | Pass | Fail |
|-------|-------|------|------|
| test_cycle_v14.py | 31 | 31 | 0 |
| test_cycle_v11.py | 21 | 21 | 0 |
| test_cycle3.py | 10 | 10 | 0 |
| test_pipeline.py | 7 | 7 | 0 |
| test_repair_cycle33032428186.py | 6 | 6 | 0 |
| **Total** | **75** | **75** | **0** |

### Corpus Statistics

| Metric | Value |
|--------|-------|
| Total decisions | 174,113 |
| Decisions 2000-2024 | 165,463 |
| Decisions 2000+ (incl. 2025-2026) | 173,963 |
| Year-split files | 37 (1986-2026) |
| German | 106,571 (61.2%) |
| French | 57,555 (33.1%) |
| Italian | 9,987 (5.7%) |
| Parquet source SHA-256 | `74f3b2d683b6c298efc6e287cd88244cc19f38af38e060cc4d4e5cf5f938a62d` |
| Reproduction time | ~116s |

### Field Coverage (Cross-year sample, n=1000, seed=42)

| Field | Coverage |
|-------|----------|
| full_text | 100.0% |
| cited_decisions | 99.3% |
| outcome | 100.0% |
| regeste | 47.4% |
| bge_reference | 0.0% |
| cited_laws | 0.0% |

### Citation Resolver (Full Corpus)

| Metric | Value |
|--------|-------|
| Decisions indexed | 196,668 |
| BGE references indexed | 17,618 |
| Docket numbers indexed | 195,757 |
| Total references | 2,105 |
| Resolved | 2,019 |
| Unresolved | 86 |
| Resolution rate | 95.91% |
| By method: exact_docket | 1,705 |
| By method: normalized_docket | 314 |
| Unresolved: cantonal_docket | 35 |
| Unresolved: admin_court_other | 35 |
| Unresolved: bge_volume_section_mismatch | 12 |
| Unresolved: bge_not_in_corpus | 4 |

### Manifest Integrity

| Check | Result |
|-------|--------|
| 37 year files present | ✓ |
| All line counts match manifest | ✓ |
| Parquet SHA-256 matches | ✓ |
| Total records: manifest vs counted | 174,113 == 174,113 ✓ |

### User Import Pipeline

| Feature | Status |
|---------|--------|
| Schema validation | ✓ |
| Cross-corpus dedup | ✓ |
| Artifact persistence | ✓ |
| Incremental import | ✓ |
| Multi-format support | ✓ |

## Lane Deliverable Status (v14 Objectives)

| v14 Objective | Status |
|---------------|--------|
| Full corpus acquired (174,113 decisions, 2000-2026) | ✅ COMPLETE |
| Citation ID resolution pipeline (95.9% rate) | ✅ COMPLETE |
| User corpus import with schema validation | ✅ COMPLETE |
| All 75 tests PASS | ✅ VERIFIED (7th independent verification) |
| Data artifacts consistent | ✅ VERIFIED |
| Manifest integrity verified | ✅ VERIFIED |

## Recommendation

**CORPUS_LANE_COMPLETE_UNBLOCK_DEPENDENTS** — No further corpus lane cycles needed.

This is the 7th independent verification confirming the same result. All v14 objectives are achieved. The corpus is reproducible from source parquet in ~2 minutes. No code or data changes in this cycle.

### Known Architecture Issue (Persistent)

The supervisor dispatches redundant corpus lane cycles because it reads `factory_direction.json` status (stale: `"RUN"`) instead of `state/corpus.json` cycle_status (correct: `"COMPLETED"`). This is the 7th cycle documenting this issue. The Factory Director must:
1. Update `factory_direction.json` corpus lane status from `"RUN"` to `"COMPLETE"`
2. Fix supervisor dispatch to read `state/<lane>.json` instead of `factory_direction.json` status

## Evidence References

- `corpus/acquisition/reproduce_full_corpus.py` — canonical reproduction script
- `corpus/acquisition/citation_resolver.py` — citation resolution pipeline
- `corpus/acquisition/user_import_hardened.py` — hardened user import
- `corpus/tests/test_cycle_v14.py` — 31 tests
- `corpus/tests/test_cycle_v11.py` — 21 tests
- `corpus/tests/test_cycle3.py` — 10 tests
- `corpus/tests/test_pipeline.py` — 7 tests
- `corpus/tests/test_repair_cycle33032428186.py` — 6 tests
- `corpus/normalization/canonical/manifest_v14_reproduction.json` — verifiable manifest
- `corpus/normalization/canonical/ingestion_metrics.json` — production metrics
- `corpus/normalization/canonical/resolved_full/citation_graph_resolved.json` — resolved citations