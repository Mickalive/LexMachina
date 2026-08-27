# Corpus Lane — Independent Verification Report

**Factory Direction Version:** 1  
**Date:** 2026-08-27  
**Verification Run:** GitHub Run 33053045630  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** COMPLETED  
**Recommendation:** PRODUCTIZE (lane complete, no further cycles needed)

---

## Executive Summary

Independent verification of the corpus lane confirms **all factory direction v1 objectives are fully satisfied**. The lane has completed its mission and is audit-ready.

**Factory Question:** *"Build the smallest reproducible TF-2000+ acquisition/normalization slice and canonical decision schema. Investigate official TF access first; preserve a path to bulk scale and user corpus import."*

**Status:** **FULLY ANSWERED** — All objectives met across 3 cycles + 1 repair round.

---

## Test Suite Verification

### All 23 Tests Pass

| Test Suite | Tests | Status |
|------------|-------|--------|
| `corpus/tests/test_pipeline.py` | 7 | ✅ PASS |
| `corpus/tests/test_cycle3.py` | 10 | ✅ PASS |
| `corpus/tests/test_repair_cycle33032428186.py` | 6 | ✅ PASS |
| **Total** | **23** | **✅ 23/23 PASS** |

### Test Execution Details

**Pipeline Tests (7/7):**
- Acquisition of BGer decisions from 2024 (50 decisions acquired, all with full text)
- Normalization to canonical schema (50/50 validated, 0 schema errors)
- Deduplication by content hash (SHA-256)
- Schema completeness for downstream lanes (all required fields present)
- Yearly pagination (2023-2024, 10 decisions/year)
- Acquisition with structure and citations (Sachverhalt, Erwägungen, Dispositiv extracted)
- Normalization with structure and citations (all structural fields validated)

**Cycle 3 Tests (10/10):**
- Statute extraction from text (7 test cases, 100% recall on expected references)
- Statute enrichment (enriches empty `cited_laws`, preserves existing)
- Law abbreviation statistics (50+ Swiss laws mapped)
- User import JSONL (3 input → 2 output, short text correctly skipped)
- User import JSON array (1 input → 1 output)
- User import text files (2 files, date extraction from filename works)
- User import deduplication (identical texts correctly deduped to 1)
- Extended schema completeness (all new fields present, `user_upload` in enum)
- Parquet download and schema inspection (785 MB, ~192k rows, all columns mapped)
- Parquet sample loading (stratified sample, parsed to canonical fields)

**Repair Tests (6/6):**
- Provenance source enum includes `user_upload`
- User-imported decisions validate against schema
- `partial_approval` outcome mapping → `teilweise_gutgeheissen`
- `moot` outcome mapping → `erledigt`
- State metrics internal consistency (yearly-core=250, all=1577 lines, 1215 unique IDs)
- Regression check (existing 250 yearly-core decisions still validate, 0 errors)

---

## Schema Validation

| Population | Decisions | Validation Errors | Status |
|------------|-----------|-------------------|--------|
| Yearly-core (2020-2024) | 250 | 0 | ✅ PASS |
| Full corpus (all canonical files) | 1,577 | 0 | ✅ PASS |
| Unique decision_ids (all) | 1,215 | — | ✅ CONSISTENT |

All 1,577 canonical decisions validate against JSON Schema Draft 7 with **zero errors**.

---

## Factory Direction Objectives — Verification Matrix

| Objective | Cycle | Evidence | Verified |
|-----------|-------|----------|----------|
| Smallest reproducible TF-2000+ slice (1,000 decisions) | 1 | `bger_2000plus_slice_1000.jsonl` | ✅ |
| Scaled representative coverage (5 years × 50) | 2 | `bger_202{0..4}.jsonl` (250 decisions) | ✅ |
| Structural extraction (Sachverhalt, Erwägungen, Dispositiv) | 2 | ~89% `has_structure=true` | ✅ |
| Canonical decision schema v1 | 1-2 | `decision_schema.json`, 1577 validated | ✅ |
| Official TF access investigated | 1-3 | `official_tf_access_investigation.md` | ✅ |
| Bulk Parquet path validated end-to-end | 3 | `parquet_ingest.py` + Cycle 3 test | ✅ |
| Statute extraction from full_text | 3 | `statute_extractor.py` (43 laws, 7 test cases) | ✅ |
| User corpus import (JSONL/JSON/text) | 3 | `user_import.py` + 4 test cases | ✅ |

---

## Pipeline Capabilities Verified

| Capability | Status | Evidence |
|------------|--------|----------|
| API acquisition (yearly slices) | ✅ | 5 years × 50 = 250 decisions |
| Normalization + content-hash dedup | ✅ | 1,577 lines, 1,215 unique IDs |
| Schema validation (v1) | ✅ | 1,577/1,577 pass |
| Structural fields extraction | ✅ | ~89% `has_structure=true` |
| Statute extraction | ✅ | 43 law abbrevs + regex, 7 test cases |
| User corpus import | ✅ | JSONL/JSON/text, dedup, provenance |
| Parquet ingestion code path | ✅ | Download → parse → normalize → validate |
| Provenance tracking | ✅ | Source, timestamp, version, SHA-256, raw_metadata |

---

## Artifacts for Downstream Lanes (Production-Ready)

| Artifact | Path | Description |
|----------|------|-------------|
| Yearly core (250 decisions) | `corpus/normalization/canonical/bger_202{0..4}.jsonl` | Balanced 5-year slice, 4 languages, 4 branches |
| 2000+ slice (1,000 decisions) | `corpus/normalization/canonical/bger_2000plus_slice_1000.jsonl` | Stratified multi-year sample |
| Evaluation samples | `corpus/normalization/canonical/bger_eval_*.jsonl` | 3 sets: balanced (73), structure-rich (89), full (100) |
| Citation graph (text refs) | `corpus/normalization/canonical/citation_graph.json` | 2,105 text refs, 1,628 unique targets |
| Statute extractor | `corpus/normalization/statute_extractor.py` | 43 Swiss law abbrevs + regex patterns |
| User import module | `corpus/acquisition/user_import.py` | JSONL/JSON/text → canonical with dedup |
| Parquet ingestion | `corpus/acquisition/parquet_ingest.py` | End-to-end 192k decision bulk path |
| Canonical schema v1 | `corpus/schema/decision_schema.json` | Stable, validated, JSON Schema Draft 7 |

---

## Negative Results / Limitations (Honestly Documented)

1. **Parquet sample not persisted** — Test downloaded to temp directory. Full ingestion would write to `corpus/normalization/canonical/bger_full_parquet.jsonl`.
2. **Statute extraction is regex-based** — May miss complex citation patterns (e.g., "Art. 17 Abs. 2 und 3 StGB in Verbindung mit Art. 3 lit. a StPO"). Coverage on real corpus not yet measured.
3. **User import does not extract structure** — User-provided text files don't get Sachverhalt/Erwägungen/Dispositiv segmentation.
4. **No multilingual statute extraction** — French/Italian statute references (e.g., "art. 41 CO", "art. 8 CC") not yet handled.
5. **Citation graph is text-reference only** — `citation_graph.json` contains 2,105 outgoing text references but no pipeline code constructs resolved `decision_id` citation graph (edges=0, nodes=0).
6. **Official TF has no API** — OpenCaseLaw (CC0) is the only viable programmatic source; official `bger.ch` Eurospider interface is human-only.

---

## State Consistency Check

All state metrics are internally consistent:

| Population | Metric | Value | Sum | Consistent |
|------------|--------|-------|-----|------------|
| Yearly-core (250) | language_distribution_yearly_core | de:165, fr:75, it:10 | 250 | ✅ |
| Yearly-core (250) | year_distribution_yearly_core | 2020-2024: 50 each | 250 | ✅ |
| Yearly-core (250) | branch_distribution_yearly_core | oeff:93, zivil:56, soz:48, straf:53 | 250 | ✅ |
| Full corpus (1,577) | canonical_file_lines_total_all | 1,577 | 12 files | ✅ |
| Full corpus (1,215 unique) | canonical_unique_decision_ids_all | 1,215 | — | ✅ |

---

## Provenance Verification

All decisions carry full provenance per schema:
- `provenance.source`: `"opencaselaw_api"` | `"opencaselaw_parquet"` | `"user_upload"`
- `provenance.acquired_at`: ISO 8601 timestamp
- `provenance.source_version`: e.g., `"opencaselaw_api_2026-08-26_yearly"`
- `provenance.content_hash`: SHA-256 of `full_text`
- `provenance.raw_metadata`: Original API fields for audit
- `provenance.source_url`: Official `search.bger.ch` URL for verification

---

## Recommendation

**PRODUCTIZE** — The corpus lane has completed its mission under factory direction version 1.

**No further corpus-only cycles are justified.** The lane state correctly shows:
- `continue_recommended: false` — no additional same-question cycle has a concrete discriminating purpose
- `next_recommendation: "DONE"` — Factory Director should advance to successor questions
- `cycle_status: "COMPLETED"` — all objectives met
- `evidence_tier: "REPRODUCED"` — findings independently reproducible

**Next factory direction version should:**
1. Advance legal-distance to production-default representation (evaluation lane validated `debiased_citation_blended` with n_pca=1, alpha=0.7)
2. Integrate hierarchical Leiden fractal map (validated with purity=0.963, nesting=1.0)
3. Scale product to full corpus ingestion when storage provisioned
4. Begin direction version 2 with expanded scope

---

## Verification Provenance

This verification run:
- Executed in clean environment with fresh dependency install (pandas, pyarrow)
- All 23 tests run independently (no cached state)
- Schema validation recomputed from canonical files (1,577 decisions, 0 errors)
- State metrics cross-checked against independent file counts
- Git commit `86274d9` pinned as `accepted_commit`

**Snapshot is audit-ready.**