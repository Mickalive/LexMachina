# Corpus Lane — Cycle v17 Reproduction Verification Report

**Run:** 33420652112 (factory direction v14, GitHub run 33420652112)  
**Date:** 2026-08-31  
**Lane:** corpus  
**Direction version:** 14  
**Cycle type:** Fresh reproduction verification (deterministic re-derivation from parquet source)

## Executive Summary

Performed a fresh deterministic reproduction of the full 174,113-decision corpus from the HuggingFace parquet source, re-ran citation resolution, and executed the complete 75-test suite. All objectives achieved: **75/75 tests PASS**, 174,113 decisions normalized, 95.9% citation resolution rate confirmed. This is a fresh-context independent verification of the previous cycle's results, confirming reproducibility.

## What Was Done

1. **Installed dependencies:** pyarrow 25.0.1, pandas 3.0.5, jsonschema
2. **Downloaded parquet source:** bger.parquet (822,789,251 bytes) from HuggingFace
3. **Ran `reproduce_full_corpus.py`:** Deterministic clean-output ingestion of all 174,114 rows, producing 174,113 unique normalized decisions across 37 year-split files (bger_1986–bger_2026.jsonl)
4. **Ran citation resolution:** Built index from 196,668 decisions (174k BGer + 22k BGE canonical), resolved 2,019/2,105 references (95.9%)
5. **Executed all 5 test suites:** v14 (31 tests), v11 (21 tests), pipeline (7 tests), cycle3 (10 tests), repair (6 tests)

## Verification Results

### Test Suite Results

| Test Suite | Total | Passing | Status |
|------------|-------|---------|--------|
| test_cycle_v14.py | 31 | 31 | ALL PASS |
| test_cycle_v11.py | 21 | 21 | ALL PASS |
| test_pipeline.py | 7 | 7 | ALL PASS |
| test_cycle3.py | 10 | 10 | ALL PASS |
| test_repair_cycle33032428186.py | 6 | 6 | ALL PASS |
| **TOTAL** | **75** | **75** | **100% PASS** |

### Corpus Metrics (fresh reproduction)

| Metric | Value |
|--------|-------|
| Canonical decisions | 174,113 |
| Source parquet | bger.parquet (822,789,251 bytes) |
| Parquet SHA-256 | `74f3b2d683b6c298efc6e287cd88244cc19f38af38e060cc4d4e5cf5f938a62d` |
| Year range | 1986–2026 (173,963 from 2000–2026, 150 pre-2000) |
| Language distribution | DE: 106,571 / FR: 57,555 / IT: 9,987 |
| Schema validation | 0 errors |
| Row processing errors | 0 |
| Ingestion rate | ~1,427 decisions/second |

### Citation Resolution (fresh run)

| Metric | Value |
|--------|-------|
| Decisions indexed | 196,668 |
| Docket entries indexed | 195,757 |
| BGE entries indexed | 17,618 |
| Total references | 2,105 |
| Resolved | 2,019 (95.9%) |
| Unresolved | 86 |
| By method: exact docket | 1,705 |
| By method: normalized docket | 314 |
| By type: BGE | 1,053 |
| By type: docket | 1,017 |
| By type: other | 35 |

### Key Observations

1. **Deterministic reproducibility confirmed:** The same parquet source, same normalization pipeline, same output counts (174,113 decisions, 0 errors). Manifest SHA-256 of year files will differ from prior runs because timestamps in provenance are non-deterministic, but data content is identical.

2. **Full BGer dataset:** The 174,113 count represents the complete Swiss Federal Supreme Court (BGer) dataset available in OpenCaseLaw's HuggingFace parquet. The original 192k target was an over-estimate; the actual dataset has 174k decisions.

3. **Field coverage at scale:** Full text: 100%, regeste: 47.4%, cited_decisions: 52.6%, outcome: 50.5% (sampled from validation_report_v14.json, 1000-record cross-year sample).

4. **All pipeline objectives from factory direction v14 achieved:**
   - Scale from 1,577 to full coverage ✓ (174,113 decisions)
   - Citation ID resolution pipeline ✓ (95.9% resolution rate)
   - User corpus import with schema validation and artifact persistence ✓ (tested in v11 suite)

## Recommendation

**CORPUS_LANE_COMPLETE_UNBLOCK_DEPENDENTS** — same as previous cycles. The corpus is fully normalized at 174,113 decisions with 75/75 tests passing, confirmed by fresh reproduction. Dependent lanes (legal-distance, fractal-map, evaluation) should be unblocked for evaluation at 174k scale.

## Files Modified

- `reports/corpus/v17_reproduction_verification_report.md` — this report
- `state/corpus.json` — updated with fresh run metrics and cycle note
