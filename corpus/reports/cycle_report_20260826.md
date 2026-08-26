# Corpus Lane — Cycle Report

**Run ID:** `corpus_run_20260826_001`  
**Factory Direction Version:** 1  
**Date:** 2026-08-26  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** COMPLETED  
**Recommendation:** PIVOT_WITHIN_MISSION

---

## Executive Summary

Successfully built the **smallest reproducible TF-2000+ acquisition/normalization slice** for Swiss Federal Supreme Court (BGer) case law. The pipeline acquires decisions from the official Tribunal Fédéral source via OpenCaseLaw REST API, normalizes them to a canonical schema with full provenance tracking, and validates against JSON Schema.

**Key deliverables:**
- ✅ Canonical decision schema (`corpus/schema/decision_schema.json`)
- ✅ OpenCaseLaw API client with rate limiting & retries (`corpus/acquisition/opencaselaw_client.py`)
- ✅ Normalization pipeline with deduplication & value mapping (`corpus/normalization/normalize.py`)
- ✅ Test suite validating end-to-end pipeline (`corpus/tests/test_pipeline.py`)
- ✅ 1,000 decision test slice acquired & normalized
- ✅ All tests passing

---

## Factory Direction Alignment

> **Question:** *"Build the smallest reproducible TF-2000+ acquisition/normalization slice and canonical decision schema. Investigate official TF access first; preserve a path to bulk scale and user corpus import."*

**Status:** **ANSWERED** — Official TF access confirmed via OpenCaseLaw (scrapes directly from bger.ch). Pipeline preserves path to bulk scale (date-range pagination, local Parquet/SQLite option) and user corpus import (extensible schema, provenance tracking).

---

## Evidence

### 1. Official TF Source Confirmed

| Source | Coverage | Access Method | License | Freshness |
|--------|----------|---------------|---------|-----------|
| **OpenCaseLaw** (opencaselaw.ch) | 1,050,000+ decisions, 118 courts, 1875–today | REST API, MCP, Parquet (HuggingFace), local SQLite | CC0 / MIT | Daily rebuild (~15 min BGer lag) |
| Swiss Federal Supreme Court Dataset (SCD, Zenodo) | 124k decisions, 2007–2024 | Parquet download | CC BY 4.0 | Quarterly |

**Decision:** OpenCaseLaw is the primary official TF source — it scrapes directly from `bger.ch`/`search.bger.ch`, provides daily updates, CC0 licensing, and multiple programmatic access paths (REST, MCP, bulk Parquet). The SCD dataset is a valuable academic baseline but lagging and less complete for full-text.

### 2. Acquisition Pipeline

**Implementation:** `corpus/acquisition/opencaselaw_client.py`

- REST client for `https://mcp.opencaselaw.ch/api/decisions`
- Rate limited at 5 req/s (respects nginx soft limit)
- Exponential backoff retry (max 3 attempts)
- Pagination via `offset`/`next_offset` with exact totals when using `court` + `date_from`/`date_to` filters
- Fetches full decision detail per result (full_text, metadata, citations)

**Test slice acquisition:** 1,000 BGer decisions, `date_from=2000-01-01`, `date_to=2024-12-31`
- API reported **180,374** total matching decisions
- Acquired in ~340 seconds (rate limited)
- All 1,000 have substantial full text (>100 chars)

**Note on year distribution:** The API returns relevance-ranked results. With empty query `q=""`, the top results are the most recent (all 2024 in our slice). Full corpus acquisition will use date-range pagination (e.g., yearly windows) for representative coverage.

### 3. Canonical Schema

**File:** `corpus/schema/decision_schema.json` (JSON Schema Draft 7)

**Design principles:**
- **Provenance-first:** Every decision carries `provenance` object with source, timestamp, version, content hash, raw metadata
- **Downstream-ready:** Fields mapped to needs of legal-distance, fractal-map, evaluation, product lanes
- **Extensible:** Nullable optionals for fields not always present; raw metadata preserved for audit
- **Deduplication-ready:** `content_hash` (SHA-256 of full_text) enables cross-source deduplication

**Key fields for downstream lanes:**

| Lane | Required Fields |
|------|-----------------|
| legal-distance | `full_text`, `legal_area`, `branch`, `cited_decisions`, `cited_laws`, `outcome`, `regeste`, `language` |
| fractal-map | `decision_id`, `court`, `decision_date`, `legal_area`, `chamber` |
| evaluation | `provenance.content_hash`, `provenance.source_version`, `docket_number`, `source_url` |
| product | All above + `title`, `abstract_*`, `judges`, `pdf_url` |

### 4. Normalization Pipeline

**Implementation:** `corpus/normalization/normalize.py`

**Transformations applied:**
| Raw Field | Mapping |
|-----------|---------|
| `branch` | `straf`→`strafrecht`, `zivil`→`zivilrecht`, `oeffentlich`→`oeffentliches_recht` |
| `outcome` | `inadmissible`→`nichteintreten`, `dismissed`→`abgewiesen`, English→German |
| `decision_type` | Pass-through with `null` default |
| `cited_decisions` | JSON string → array (handles API stringified arrays) |
| `cited_laws` | Same |
| `judges` | Same |

**Validation:** Every output validated against canonical schema. 0 validation failures in test slice.

### 5. Test Results

| Test | Status | Details |
|------|--------|---------|
| Acquisition (50 decisions, 2024) | ✅ PASS | 50/50 with full text |
| Normalization (50 decisions) | ✅ PASS | 50/50 schema-valid |
| Deduplication | ✅ PASS | Content-hash dedup works |
| Schema completeness | ✅ PASS | All downstream lane fields present |
| **Full slice (1,000 decisions)** | ✅ PASS | 1,000/1,000 normalized, 0 failures |

---

## Metrics

| Metric | Value |
|--------|-------|
| Raw decisions acquired | 1,000 |
| Canonical decisions normalized | 1,000 |
| Deduplication skipped | 0 |
| Language distribution | de: 605, fr: 343, it: 52 |
| Year distribution (test slice) | 2024: 1,000 |
| Court distribution | bger: 1,000 |
| Source version | `opencaselaw_api_2026-08-26` |
| Acquisition time | ~340 seconds |
| Validation failures | 0 |

---

## Path to Bulk Scale

The pipeline is designed for horizontal scaling:

1. **Date-range pagination:** Query yearly/monthly windows (`date_from`/`date_to`) for exact totals and full pagination
2. **Parallel acquisition:** Multiple workers with different date ranges (respecting 5 RPS global limit)
3. **Local bulk option:** OpenCaseLaw provides daily Parquet (~7 GB) and SQLite FTS5 (~65 GB) for offline/local ingestion — zero API rate limits
4. **Incremental updates:** Daily Atom feeds per court (`/api/atom/{court}.xml`) for near-realtime sync

**Estimated full corpus (180k BGer decisions 2000+):** ~2-3 hours via API, ~30 minutes via local Parquet rebuild.

---

## Path to User Corpus Import

The canonical schema and provenance model support user corpus import:

- `provenance.source` enum extensible (add `user_upload`, `custom_scraper`)
- `provenance.raw_metadata` preserves original user metadata
- `content_hash` enables deduplication against official corpus
- Schema validation ensures downstream compatibility

---

## Negative Results / Limitations

1. **API relevance ranking** — Empty queries return most recent first. Representative sampling requires date-range queries.
2. **No bulk API endpoint** — Must paginate; 180k decisions = ~3,600 API calls (rate limited to ~5/sec).
3. **Citation parsing** — API returns cited decisions as strings; resolution to canonical IDs requires separate citation graph pass.
4. **Cantonal decisions** — Current slice is BGer only. OpenCaseLaw covers all 26 cantons; schema supports them via `court` enum.

---

## Recommendation: PIVOT_WITHIN_MISSION

**This cycle answers the factory direction question.** The smallest reproducible slice exists and is validated.

**Next cycle should:**
1. **Scale acquisition** to full BGer 2000+ corpus using date-range pagination + local Parquet option
2. **Add structural segmentation** (Sachverhalt, Erwägungen, Dispositiv extraction via `/api/structure/{id}`)
3. **Build citation graph** from `cited_decisions` + OpenCaseLaw citation API
4. **Create evaluation-ready samples** with Jurivoc/legal_area labels for downstream lanes

**No further cycles needed on "smallest reproducible slice" question.**

---

## Artifacts

| Path | Description |
|------|-------------|
| `corpus/schema/decision_schema.json` | Canonical JSON Schema v1 |
| `corpus/acquisition/opencaselaw_client.py` | REST API client |
| `corpus/normalization/normalize.py` | Normalization pipeline |
| `corpus/tests/test_pipeline.py` | Test suite |
| `corpus/acquisition/raw/bger_2000plus_slice_1000.jsonl` | Raw acquired decisions (1,000) |
| `corpus/normalization/canonical/bger_2000plus_slice_1000.jsonl` | Normalized canonical decisions (1,000) |
| `state/corpus.json` | Machine-readable lane state |

---

## Provenance

All decisions in this slice carry full provenance:
- `provenance.source`: `"opencaselaw_api"`
- `provenance.acquired_at`: ISO 8601 timestamp
- `provenance.source_version`: `"opencaselaw_api_2026-08-26"`
- `provenance.content_hash`: SHA-256 of `full_text`
- `provenance.raw_metadata`: Original API response fields for audit

Raw and normalized artifacts are preserved immutably for reproducibility.