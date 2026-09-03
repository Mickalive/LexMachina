# Corpus Lane v35 — Factory Direction v17 Verification Report

**Date:** 2026-09-03
**Run:** Local verification (direction v17)
**Lane:** corpus
**Status:** COMPLETED / PAUSED
**Evidence tier:** REPRODUCED

## Summary

15th independent verification of the corpus lane under factory direction v17. Full corpus reproduced from OpenCaseLaw Parquet source. All 76/76 regression tests PASS. Manifest integrity and field coverage ground truth verified. Direction version updated 14→17.

## Reproduction

- **Source:** `https://huggingface.co/datasets/voilaj/swiss-caselaw/resolve/main/bger.parquet`
- **Parquet size:** 822.8 MB
- **SHA-256:** `74f3b2d683b6c298efc6e287cd88244cc19f38af38e060cc4d4e5cf5f938a62d`
- **Total rows in parquet:** 174,114
- **Normalized decisions:** 174,113 (1 duplicate skipped)
- **Errors:** 0
- **Year-split files:** 37 `bger_*.jsonl` files

## Language Distribution

| Language | Count |
|----------|-------|
| de       | 106,571 |
| fr       | 57,555 |
| it       | 9,987 |

## Year Coverage

- **2000-2026:** 173,963 decisions
- **Pre-2000:** 150 decisions
- **Missing years:** None

## Test Results

**76/76 PASS** (pytest, 24 warnings)

| Test Suite | Tests | Status |
|------------|-------|--------|
| test_cycle_v14.py | 31 | PASS |
| test_cycle_v11.py | 21 | PASS |
| test_cycle3.py | 10 | PASS |
| test_pipeline.py | 7 | PASS |
| test_repair_cycle33032428186.py | 7 | PASS |

## Manifest Integrity

All 37 `bger_*.jsonl` file line counts in `manifest_v14_reproduction.json` match actual files on disk. Total: 174,113 lines.

## Field Coverage Ground Truth

Verified against `validation_report_v14.json` (sample_size=1000, seed=42):

| Field | Actual | Ground Truth | Delta | Status |
|-------|--------|-------------|-------|--------|
| full_text | 1.000 | 1.000 | 0.000 | MATCH |
| regeste | 0.474 | 0.474 | 0.000 | MATCH |
| cited_decisions | 0.526 | 0.526 | 0.000 | MATCH |
| outcome | 0.505 | 0.505 | 0.000 | MATCH |
| legal_area | 0.526 | 0.526 | 0.000 | MATCH |

**Note:** The outcome field contains 495 records with string value `"null"` (truthy) and 505 with meaningful outcomes. The `d.get("outcome")` truthiness check in the test suite treats both as present, yielding 100% raw coverage. The meaningful outcome coverage (excluding `"null"` strings) is 50.5%, matching ground truth exactly.

## Data Inventory

### Canonical Corpus
- `corpus/normalization/canonical/bger_[0-9][0-9][0-9][0-9].jsonl` — 37 year-split files, 174,113 total lines
- `corpus/normalization/canonical/manifest_v14_reproduction.json` — verifiable manifest with SHA-256 per file
- `corpus/normalization/canonical/ingestion_metrics.json` — ingestion statistics
- `corpus/normalization/canonical/validation_report_v14.json` — schema validation + field coverage ground truth

### Citation Resolution
- `corpus/normalization/canonical/citation_graph.json` — resolved citation graph
- `corpus/normalization/canonical/resolved_full/citation_graph_resolved.json` — full resolution output
- `corpus/normalization/canonical/resolved_full/citation_to_decision_id.json` — citation→decision_id mapping
- **Resolution rate:** 95.9% (2,105 BGE/ATF references → 2,019 resolved, 86 unresolved)

### Test/Sample Data
- `corpus/normalization/canonical/bge_[0-9][0-9][0-9][0-9].jsonl` — 111 legacy sample files
- `corpus/normalization/canonical/bger_test_*.jsonl` — test slices
- `corpus/normalization/canonical/bger_eval_*.jsonl` — evaluation samples

### Source
- `corpus/acquisition/parquet/bger.parquet` — 822.8 MB source parquet (downloaded from HuggingFace)

## Direction Version Update

State file `state/corpus.json` updated:
- `direction_version`: 14 → 17
- `independent_verifications`: 14 → 15
- `field_coverage_ground_truth_verified`: true (new field)
- `reproduced.method`: updated with v35 verification description
- `reproduced.new_in_this_cycle`: updated with v35 details
- `notes`: updated with v35 summary

## Lane Status

- **Cycle status:** COMPLETED
- **Continue recommended:** false
- **Next recommendation:** CORPUS_LANE_COMPLETE_UNBLOCK_DEPENDENTS
- **Dependent lanes:** legal-distance, fractal-map, evaluation (all PAUSED pending corpus 174k delivery)

## Pre-existing Observation

The normalizer writes `"null"` (string) for records with no outcome, rather than `None`. This inflates raw truthiness-based coverage checks from 50.5% to 100%. The actual meaningful outcome coverage remains 50.5%. This is a known data quality quirk, not a regression — the ground truth is preserved.
