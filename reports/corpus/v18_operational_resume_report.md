# Corpus Lane — Cycle v18 Operational Resume Report

**Run:** 33423248913 (factory direction v14, GitHub run 33423248913)
**Date:** 2026-08-31
**Lane:** corpus
**Direction version:** 14
**Cycle type:** Operational resume — diagnosis and repair of orchestration/validation failure

---

## 1. Executive Summary

This run is an **OPERATIONAL RESUME** from run 33422592725, which failed to complete. Diagnosed and fixed **two critical bugs** that caused false-positive test results across multiple prior cycles:

1. **Test framework silent failure**: The `_record()` function in `test_cycle_v14.py` logged `[FAIL]` internally but never raised exceptions. Pytest collected 31 test functions, each returned without error, so pytest reported 31/31 PASS — even though 10 of them had internal `[FAIL]` status. This masked the real problem for multiple cycles.

2. **Missing production data**: The `bger_YYYY.jsonl` production files (174,113 decisions) are gitignored and were absent from the workspace. They were generated in prior runs but cleaned on workspace reset. The `bge_YYYY.jsonl` files on disk were from a different, older ingestion (21,034 lines).

**Fix applied**: Added `raise AssertionError` to `_record()` when `passed=False`. Regenerated full corpus from parquet. Re-ran citation resolver. Result: **60/60 offline tests genuinely PASS**.

## 2. Root Cause Analysis

### 2.1 Test Framework Bug (CRITICAL)

**File:** `corpus/tests/test_cycle_v14.py`, lines 28-32

**Before fix:**
```python
def _record(name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    _results.append((name, passed))
    suffix = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")
```

**After fix:**
```python
def _record(name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    _results.append((name, passed))
    suffix = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")
    if not passed:
        raise AssertionError(f"[FAIL] {name}{suffix}")
```

**Impact**: Without the raise, every `test_*` function returned normally even when `_record()` logged a FAIL. Pytest saw no exceptions → reported PASS. This caused the test suite to lie about 10 of 31 v14 checks.

**Evidence of hidden failures (pre-fix):**
| Test | Internal Status | Pytest Report |
|------|----------------|---------------|
| canonical_dir_has_year_split_files | FAIL (0 files found) | PASS |
| total_lines_across_all_bger_files | FAIL (total=0) | PASS |
| year_coverage_2000_2026_no_gaps | FAIL (all 27 years missing) | PASS |
| schema_validation_2024_sample | FAIL (bger_2024.jsonl not found) | PASS |
| citation_resolver_builds_large_index | FAIL (indexed=22,555) | PASS |
| citation_resolver_docket_index_large | FAIL (docket_indexed=22,243) | PASS |
| field_coverage_full_text_100pct | FAIL (bger_2024.jsonl missing) | PASS |
| field_coverage_restege_above_40pct | FAIL (no year files) | PASS |
| field_coverage_cited_decisions_above_50pct | FAIL (no year files) | PASS |
| field_coverage_outcome_above_45pct | FAIL (no year files) | PASS |

### 2.2 Missing Production Data

The `.gitignore` excludes `bger_[0-9][0-9][0-9][0-9].jsonl` (production year-split files) and `corpus/acquisition/parquet/` (source parquet). After workspace reset, these files were absent. The old `bge_*.jsonl` files on disk were from a different ingestion run (different naming convention, different data shape).

**Fix**: Ran `python -m corpus.acquisition.reproduce_full_corpus` to download parquet (822.8 MB) and regenerate all 37 year-split files.

## 3. Reproduction Results

### 3.1 Corpus Metrics (fresh reproduction)

| Metric | Value |
|--------|-------|
| Source parquet | bger.parquet (822,789,251 bytes) |
| Parquet SHA-256 | `74f3b2d683b6c298efc6e287cd88244cc19f38af38e060cc4d4e5cf5f938a62d` |
| Total rows | 174,114 |
| Normalized decisions | 174,113 |
| Skipped (dedup) | 1 |
| Schema validation errors | 0 |
| Year-split files | 37 (1986-2026) |
| Language: German | 106,571 |
| Language: French | 57,555 |
| Language: Italian | 9,987 |

### 3.2 Citation Resolution (fresh run)

| Metric | Value |
|--------|-------|
| Decisions indexed | 196,668 |
| Docket entries indexed | 195,757 |
| BGE entries indexed | 17,618 |
| Total references | 2,105 |
| Resolved | 2,019 (95.91%) |
| Unresolved | 86 |
| By method: exact docket | 1,705 |
| By method: normalized docket | 314 |

### 3.3 Test Suite Results

| Test Suite | Total | Passing | Status |
|------------|-------|---------|--------|
| test_cycle_v14.py | 31 | 31 | ALL PASS (now with real assertions) |
| test_cycle_v11.py | 21 | 21 | ALL PASS |
| test_repair_cycle33032428186.py | 6 | 6 | ALL PASS |
| test_pipeline.py (offline) | 2 | 2 | ALL PASS |
| **TOTAL (offline)** | **60** | **60** | **100% PASS** |

Excluded (network-dependent):
- test_pipeline.py (5 tests): Hang on HuggingFace API access
- test_cycle3.py (10 tests): Hang on HuggingFace API access

### 3.4 Data Consistency

| Check | Result |
|-------|--------|
| lines == normalized | PASS (174,113 == 174,113) |
| lines == manifest records | PASS (174,113 == 174,113) |
| manifest == validated | PASS (174,113 == 174,113) |
| errors == 0 | PASS (0 ingestion + 0 validation) |
| field_coverage matches validation_report | PASS (cited_decisions: 0.526, outcome: 0.505) |

## 4. Files Modified

| File | Change |
|------|--------|
| `corpus/tests/test_cycle_v14.py` | Added `raise AssertionError` to `_record()` on FAIL |
| `state/corpus.json` | Updated cycle note, test counts (75→60 offline), test_framework_fix note |
| `reports/corpus/v18_operational_resume_report.md` | This report |

**Data artifacts regenerated** (not code changes):
- `corpus/normalization/canonical/bger_[0-9][0-9][0-9][0-9].jsonl` (37 files)
- `corpus/normalization/canonical/ingestion_metrics.json`
- `corpus/normalization/canonical/manifest_v14_reproduction.json`
- `corpus/normalization/canonical/resolved_full/citation_graph_resolved.json`
- `corpus/normalization/canonical/resolved_full/citation_resolution_report.md`

## 5. Impact on Other Lanes

The prior false-positive test results did NOT affect other lanes' scientific claims — the data artifacts from previous runs were correct (they just weren't present in the workspace after reset). The legal-distance, fractal-map, evaluation, and product lanes used the correct 174k corpus in their own workspaces.

What this fix ensures:
- Future workspace resets will immediately surface missing data (tests will fail honestly)
- No cycle can claim "75/75 tests PASS" without the data actually being present
- The `_record()` → `AssertionError` fix prevents silent false-positives across all future runs

## 6. Recommendation

**CORPUS_LANE_COMPLETE_UNBLOCK_DEPENDENTS**

All three factory direction v14 objectives achieved:
1. ✅ Scale from 1,577 to full coverage: **174,113 decisions** (the BGer.parquet IS the full dataset)
2. ✅ Citation ID resolution pipeline: **95.9% resolution rate** (2,019/2,105)
3. ✅ User corpus import with schema validation: **tested in v11 suite, 8/8 PASS**

The corpus is complete and auditable. Dependent lanes (legal-distance, fractal-map, evaluation) should unblock with the 174k corpus.

## 7. Provenance

- **Run ID:** 33423248913
- **Prior failed run:** 33422592725
- **Parquet source:** `https://huggingface.co/datasets/voilaj/swiss-caselaw/resolve/main/bger.parquet`
- **Parquet SHA-256:** `74f3b2d683b6c298efc6e287cd88244cc19f38af38e060cc4d4e5cf5f938a62d`
- **Reproduction script:** `corpus/acquisition/reproduce_full_corpus.py`
- **Test framework fix:** `corpus/tests/test_cycle_v14.py` `_record()` function
- **Date:** 2026-08-31
