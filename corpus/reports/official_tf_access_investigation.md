# Corpus Lane — Official TF Access Investigation

**Factory Direction Version:** 1  
**Date:** 2026-08-27  
**Status:** COMPLETED — Investigation confirms OpenCaseLaw is the best practical programmatic access

---

## Factory Direction Question

> *"Build the smallest reproducible TF-2000+ acquisition/normalization slice and canonical decision schema. Investigate official TF access first; preserve a path to bulk scale and user corpus import."*

---

## Official TF (Swiss Federal Supreme Court / Tribunal Fédéral / Bundesgericht) Access Options

### 1. Official Website: `https://www.bger.ch/`

The official court website provides:

| Access Method | URL | Capabilities | Limitations |
|---------------|-----|--------------|-------------|
| **Web Search (Eurospider)** | `https://search.bger.ch/ext/eurospider/live/de/php/aza/http/index.php?lang=de` | Full-text search, date filters, legal area filters, docket number lookup | Human-oriented web UI; no API; no bulk download; rate-limited by design |
| **Leitentscheide (BGE)** | `https://search.bger.ch/ext/eurospider/live/de/php/clir/http/index.php?lang=de` | Published leading decisions only (~3,000 total) | Subset of all decisions; no API |
| **Liste der Neuheiten** | `https://search.bger.ch/ext/eurospider/live/de/php/aza/http/index_aza.php?lang=de&mode=index&search=false` | Daily list of newly added decisions (by ingestion date, not decision date) | No full text; only references; no API |
| **RSS Feed** | `https://www.bger.ch/home/juridiction/feed-rss.html` | Announced on website | Not accessible / returns transport error |
| **Expert Search (Subscribers)** | `https://search.bger.ch/ext/eurospider/live/de/php/login/http/main.php?lang=de` | Advanced search for paid subscribers | Requires paid subscription; no public API |
| **Urteilsbestellung (Order Decisions)** | Manual order form | Individual decision PDFs | Manual, paid, not programmatic |

### 2. Key Findings

| Finding | Detail |
|---------|--------|
| **No official API** | The official source is a legacy Eurospider web interface (circa 2008). No REST/GraphQL API exists. |
| **No bulk download** | No official Parquet, CSV, JSONL, or XML bulk export. |
| **No machine-readable access** | All access is via HTML web forms designed for human browsing. |
| **Rate limiting** | Web interface enforces human-scale rate limits; scraping at scale would violate ToS. |
| **Coverage** | "Alle Urteile ab 2007, grösstenteils ab 2000" — all decisions from 2007, mostly from 2000. |

### 3. OpenCaseLaw (`https://opencaselaw.ch/`) — Third-Party Mirror

| Attribute | Detail |
|-----------|--------|
| **Source** | Scrapes official BGer Eurospider interface daily (plus all other Swiss courts) |
| **License** | CC0 (public domain) for data; MIT for code |
| **API** | REST API at `https://mcp.opencaselaw.ch` (OpenAPI spec available) |
| **MCP Server** | `mcp.opencaselaw.ch` for LLM integration |
| **Bulk Download** | HuggingFace Parquet: `huggingface.co/datasets/voilaj/swiss-caselaw` (bger.parquet = 785 MB, ~192k BGer decisions 2000+) |
| **Update Frequency** | Nightly rebuild |
| **Citation Graph** | 9.8M resolved citations across all courts |
| **Laws** | 5,525 federal laws (Fedlex) + 15,600 cantonal acts |

### 4. Comparison: Official vs OpenCaseLaw

| Criterion | Official BGer | OpenCaseLaw |
|-----------|---------------|-------------|
| Programmatic API | ❌ No | ✅ REST + MCP |
| Bulk download | ❌ No | ✅ Parquet (HuggingFace) |
| License | © Swiss Federal Court (restrictive) | ✅ CC0 |
| Citation graph | ❌ No | ✅ 9.8M resolved |
| Structured data (Sachverhalt/Erwägungen/Dispositiv) | ⚠️ Partial (HTML only) | ✅ Parsed JSON |
| Multi-language | ✅ DE/FR/IT | ✅ DE/FR/IT |
| Update frequency | Daily (web) | Nightly (rebuild) |
| Historical coverage (2000+) | ✅ Mostly | ✅ Full |
| Sustainability | Official (permanent) | Community project (bus factor) |

---

## Recommendation

**Use OpenCaseLaw as the primary first-party source** for the following reasons:

1. **Only practical programmatic access** — Official source has no API or bulk download
2. **Open license (CC0)** — Official source retains copyright; OpenCaseLaw releases as CC0
3. **Richer data** — Citation graph, structured sections, laws integration
4. **Validated pipeline** — Our corpus pipeline already works end-to-end with OpenCaseLaw (API + Parquet)
5. **Provenance tracking** — Our schema records `provenance.source = "opencaselaw_api"` or `"opencaselaw_parquet"` for full auditability

**Preserve official source as provenance reference** — Each decision retains `provenance.source_url` pointing to the official `search.bger.ch` URL for verification.

**Risk mitigation** — OpenCaseLaw is a single-maintainer project. Mitigation:
- Parquet snapshot (785 MB) can be archived locally
- Pipeline supports multiple source versions (`source_version` field)
- User corpus import allows fallback to other sources

---

## Lane Completion Status

All factory direction objectives **FULLY ANSWERED**:

| Objective | Status | Evidence |
|-----------|--------|----------|
| Smallest reproducible TF-2000+ slice | ✅ COMPLETE | `bger_2000plus_slice_1000.jsonl` (1,000 decisions via API) |
| Scaled representative coverage | ✅ COMPLETE | Yearly slices 2020-2024 (250 decisions) + 1,000 slice = 1,215 unique |
| Canonical decision schema v1 | ✅ COMPLETE | `decision_schema.json` — 1577 decisions validated, 0 errors |
| Official TF access investigated | ✅ COMPLETE | This report — no official API/bulk; OpenCaseLaw is best practical |
| Bulk Parquet path validated | ✅ COMPLETE | `parquet_ingest.py` — 785 MB downloaded, sampled, normalized, validated |
| User corpus import | ✅ COMPLETE | `user_import.py` — JSONL/JSON/text → canonical schema, dedup, provenance |
| Statute extraction (fills API gap) | ✅ COMPLETE | `statute_extractor.py` — 50+ Swiss law abbreviations, regex-based |

**Evidence Tier:** REPRODUCED  
**Cycle Status:** COMPLETED  
**Continue Recommended:** FALSE  
**Next Recommendation:** PRODUCTIZE (hand off to Product lane)

---

## Artifacts for Downstream Lanes

| Artifact | Path | Description |
|----------|------|-------------|
| Canonical decisions (1,000 slice) | `corpus/normalization/canonical/bger_2000plus_slice_1000.jsonl` | Multi-year representative sample |
| Canonical decisions (yearly 2020-2024) | `corpus/normalization/canonical/bger_202{0,1,2,3,4}.jsonl` | 50 decisions/year, balanced |
| Evaluation samples | `corpus/normalization/canonical/bger_eval_*.jsonl` | Balanced, structure-rich, full eval sets |
| Citation graph (empty template) | `corpus/normalization/canonical/citation_graph.json` | Schema for citation edges/nodes |
| Schema v1 | `corpus/schema/decision_schema.json` | JSON Schema Draft 7 |
| Acquisition client | `corpus/acquisition/opencaselaw_client.py` | REST API client with rate limiting |
| Parquet ingestion | `corpus/acquisition/parquet_ingest.py` | End-to-end bulk pipeline |
| Statute extractor | `corpus/normalization/statute_extractor.py` | 50+ law abbreviations |
| User import | `corpus/acquisition/user_import.py` | JSONL/JSON/text → canonical |
| Test suite | `corpus/tests/` | 23 tests, all passing |

---

## Provenance

All decisions carry full provenance per schema:
- `provenance.source`: `"opencaselaw_api"` | `"opencaselaw_parquet"` | `"user_upload"`
- `provenance.acquired_at`: ISO 8601 timestamp
- `provenance.source_version`: e.g., `"opencaselaw_api_2026-08-26_yearly"`
- `provenance.content_hash`: SHA-256 of `full_text`
- `provenance.raw_metadata`: Original API fields for audit
- `provenance.source_url`: Official `search.bger.ch` URL for verification

---

## Conclusion

The corpus lane has **completed all factory direction v1 objectives**. The official TF source was investigated and found to lack programmatic access. OpenCaseLaw provides the only viable programmatic path with open licensing, bulk download, and rich structured data. The pipeline is production-ready for the Product lane to integrate.

No further corpus-only cycles are justified unless a downstream lane identifies a specific missing field or format requirement.