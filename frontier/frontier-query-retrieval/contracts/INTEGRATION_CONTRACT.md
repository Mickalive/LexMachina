# OpenCaseLaw Retrieval Adapter — Integration Contract

**Team**: frontier-query-retrieval  
**Charter Version**: 2  
**Adapter Version**: 1.0.0  
**Bundle Schema Version**: 1  
**Date**: 2026-10-12  

---

## Purpose

This document defines the machine-readable integration contract for the OpenCaseLaw Retrieval Adapter. The adapter produces a `QueryResultBundle` that serves as the canonical interface between the frontier retrieval layer and the product layer (answer generation, counter-authority search, map building, UI).

---

## 1. Adapter Interface

### 1.1 Main Entry Point

```python
from ocl_adapter import retrieve_for_query
from ocl_adapter.retrieval import RetrievalConfig
from ocl_adapter.client import create_client

# Quick usage
decisions, stats = retrieve_for_query("miete kündigung")

# With custom config
config = RetrievalConfig(
    target_count=150,
    max_query_variants=4,
    enable_citation_expansion=True,
    enable_leading_cases=True,
)
client = create_client(cache_dir=Path("./.ocl_cache"))
decisions, stats = retrieve_for_query("miete kündigung", config=config, client=client)

# Build bundle
from ocl_adapter.bundle import build_bundle_from_retrieval
bundle = build_bundle_from_retrieval(
    query="miete kündigung",
    query_variants=stats.query_variants_used,
    decisions=decisions,
    retrieval_stats=stats,
)
```

### 1.2 CLI Interface

```bash
# Live mode (default, uses cache)
ocl-retrieve "miete kündigung" --target-count 150 --output bundle.json

# Cached only mode
ocl-retrieve "miete kündigung" --cached --target-count 150

# Offline mode (fixture only)
ocl-retrieve "miete kündigung" --offline --target-count 150

# Query expansion only
ocl-retrieve "miete kündigung" --expand-only

# Validate bundle
ocl-retrieve "miete kündigung" --validate-only
```

---

## 2. QueryResultBundle Contract

### 2.1 Top-Level Structure

```json
{
  "bundle_version": "1.0",
  "schema_version": 1,
  "query": "string",
  "query_variants": ["string"],
  "decisions": [BundleDecision],
  "clusters": [BundleCluster],
  "relations": [BundleRelation],
  "answer": BundleAnswer | null,
  "provenance": BundleProvenance
}
```

### 2.2 BundleDecision (Required Fields)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `decision_id` | string | Yes | OpenCaseLaw decision ID (e.g., `bge_BGE_117_II_410`) |
| `canonical_decision_id` | string | Yes | Canonical ID for deduplication |
| `canonical_url` | string | Yes | `https://mcp.opencaselaw.ch/entscheid/...` |
| `citation_string_de` | string | No | German citation (e.g., `BGE 117 II 410`) |
| `citation_string_fr` | string | No | French citation (e.g., `ATF 117 II 410`) |
| `citation_string_it` | string | No | Italian citation (e.g., `DTF 117 II 410`) |
| `court` | string | Yes | Court code (e.g., `bge`, `zh_obergericht`) |
| `court_name` | string | No | Human-readable court name |
| `canton` | string | No | Swiss canton code |
| `chamber` | string | No | Court chamber/division |
| `docket_number` | string | Yes | Official docket number |
| `decision_date` | string | Yes | ISO date `YYYY-MM-DD` |
| `publication_date` | string | No | Publication date if different |
| `language` | string | Yes | `de`, `fr`, `it`, or `rm` |
| `legal_area` | string | No | Legal area classification |
| `regeste` | string | No | Regeste/summary text |
| `rule_statement` | string | No | Extracted rule statement |
| `full_text` | string | No | Full decision text (lazy-loaded) |
| `snippet` | string | Yes | ≤600 char display snippet |
| `rank` | integer | Yes | Retrieval rank (1-based) |
| `score` | float | No | Relevance score from OCL |
| `provenance` | string | Yes | `live`, `cache`, or `fixture` |
| `retrieval_method` | string | Yes | `search`, `citation_expansion`, `leading_cases` |
| `query_variant` | string | No | Which query variant found this |
| `statutes` | string[] | No | Cited statutes/articles |
| `citation_count` | integer | No | Outgoing citations count |
| `cited_by_count` | integer | No | Incoming citations count |
| `cluster_id` | integer | No | Map cluster assignment |
| `x` | float | No | Map X coordinate |
| `y` | float | No | Map Y coordinate |
| `is_outlier` | boolean | No | Isolated decision flag |
| `counter_status` | string | No | `none`, `cited`, `candidate-limiting`, `candidate-contrary` |
| `counter_evidence` | string | No | Evidence sentence for counter status |
| `counter_markers` | string[] | No | Adversarial terms found |
| `content_hash` | string | No | SHA256 of full_text for change detection |

### 2.3 BundleCluster

```json
{
  "cluster_id": "integer",
  "label": "string",
  "size": "integer",
  "centroid_x": "float|null",
  "centroid_y": "float|null",
  "member_decision_ids": ["string"],
  "sample_decisions": [{"decision_id": "...", "title": "..."}],
  "dominant_language": "string|null",
  "dominant_legal_area": "string|null"
}
```

### 2.4 BundleRelation

```json
{
  "source_id": "string",
  "target_id": "string",
  "relation_type": "citation|co_citation|shared_statute|similarity",
  "weight": "float",
  "metadata": {}
}
```

### 2.5 BundleAnswer

```json
{
  "prose": "string",
  "statements": [{"text": "...", "decision_id": "...", "relevance": 0.0}],
  "cited_decision_ids": ["string"],
  "method": "extractive_tfidf_v1",
  "model": "none-local-extractive",
  "confidence": "float|null",
  "uncertainties": ["string"],
  "counter_authorities_mentioned": ["string"]
}
```

### 2.6 BundleProvenance

```json
{
  "bundle_version": "1.0",
  "schema_version": 1,
  "query": "string",
  "query_variants": ["string"],
  "retrieval": {
    "total_api_calls": "integer",
    "cache_hits": "integer",
    "decisions_fetched": "integer",
    "decisions_after_dedupe": "integer",
    "citation_expansions": "integer",
    "leading_cases_added": "integer",
    "full_text_fetched": "integer",
    "errors": ["string"],
    "duration_seconds": "float",
    "provenance_breakdown": {"live": 0, "cache": 0, "fixture": 0},
    "query_variants_used": ["string"]
  },
  "answer": {},
  "counter_authority": {},
  "map": {},
  "timestamp": "ISO8601 UTC",
  "bundle_id": "string (8 chars)",
  "adapter_version": "1.0.0",
  "charter_version": 2
}
```

---

## 3. RetrievalConfig Contract

```python
@dataclass
class RetrievalConfig:
    target_count: int = 150              # Target decisions (100-300)
    max_pages_per_query: int = 5         # Pagination depth
    max_query_variants: int = 4          # Expansion variants
    enable_citation_expansion: bool = True
    citation_expansion_limit: int = 20   # Per seed decision
    citation_seed_count: int = 10        # Top N to expand
    enable_leading_cases: bool = True
    leading_cases_limit: int = 10
    prefer_provenance: Tuple[str] = ("live", "cache", "fixture")
    language_filter: Optional[str] = None  # de/fr/it/rm
    court_filter: Optional[str] = None
    date_from: Optional[str] = None       # YYYY-MM-DD
    date_to: Optional[str] = None
    sort: str = "relevance"               # relevance|date_desc|date_asc
    full_text_for_top: int = 20           # Lazy fetch for top N
    timeout: int = 30                     # Request timeout
```

---

## 4. Client Configuration

```python
from ocl_adapter.client import create_client, OpenCaseLawClient

# Standard client with caching
client = create_client(
    cache_dir=Path("./.ocl_cache"),
    use_cache=True,
    rate_limit=5,          # req/sec (OCL soft limit)
    cache_ttl=86400        # 24 hours
)

# Offline client (no network)
client = create_client(cache_dir=None, use_cache=False)
```

---

## 5. Query Expansion Contract

### 5.1 Expansion Result

```python
from ocl_adapter.expansion import expand_query, get_search_variants

result = expand_query("miete kündigung")
# Returns ExpansionResult:
{
  "original_query": "miete kündigung",
  "expanded_terms": {
    "de": ["mietrecht", "mietvertrag", "mietzins", "erstreckung", ...],
    "fr": ["loyer", "bail", "prolongation", "congés", ...],
    "it": ["affitto", "locazione", "proroga", "disdetta", ...]
  },
  "combined_query": "miete kündigung mietrecht mietvertrag loyer bail ...",
  "language_detected": "de",
  "variants": [
    "miete kündigung",
    "miete kündigung mietrecht mietvertrag loyer bail ...",
    "miete kündigung mietrecht mietvertrag erstreckung",
    "miete kündigung loyer bail prolongation congés"
  ]
}

# Search-optimized variants
variants = get_search_variants("miete kündigung", max_variants=4)
# Returns: ["miete kündigung", "miete kündigung mietrecht...", ...]
```

---

## 6. Deduplication Contract

```python
from ocl_adapter.deduplication import deduplicate_decisions, DecisionDeduplicator

# One-shot deduplication
unique_decisions, report = deduplicate_decisions(
    decisions,
    prefer_provenance=["live", "cache", "fixture"]
)

# Report structure
{
  "input_count": 150,
  "output_count": 142,
  "duplicates_removed": 8,
  "duplicate_groups": 5,
  "provenance_distribution": {"live": 100, "cache": 40, "fixture": 10},
  "unique_identities": 142
}

# Stateful deduplicator for streaming
deduplicator = DecisionDeduplicator(prefer_provenance=["live", "cache"])
deduplicator.add(decision)  # Returns True if new
deduplicator.add_batch(decisions)  # Returns (new_decisions, duplicate_count)
deduplicator.get_unique()  # All unique in insertion order
```

---

## 7. Error Handling & Degradation

### 7.1 Network Failure Behavior

- **Live mode**: Exceptions caught, logged, recorded in `provenance.retrieval.errors`
- **Cached mode**: Returns cached results if available, otherwise empty
- **Offline mode**: Returns fixture data only

### 7.2 Partial Failure

- Failed query variants don't stop other variants
- Failed citation/leading-case expansion logged but doesn't stop pipeline
- Failed full-text fetch logged, decision kept with snippet only

### 7.3 Rate Limiting

- Automatic token-bucket rate limiting at 5 req/sec (configurable)
- Blocks until slot available
- Respects OpenCaseLaw documented soft limit

---

## 8. Caching Contract

### 8.1 Cache Key Format

```
sha256("ocl|<endpoint>|<sorted_params>")[:32].json
```

### 8.2 Cache Entry Structure

```json
{
  "_cached_at": 1700000000.0,
  "data": { ... API response ... }
}
```

### 8.3 Cache TTL

- Default: 86400 seconds (24 hours)
- Configurable via `CacheManager(ttl_seconds=...)`

### 8.4 Cache Invalidation

```python
cache_manager.invalidate()           # Clear all
cache_manager.invalidate("pattern")  # Clear matching keys
```

---

## 9. Validation Rules

### 9.1 Bundle Validation

```python
from ocl_adapter.bundle import validate_bundle, validate_bundle_object

errors = validate_bundle(bundle_dict)
# Or
errors = validate_bundle_object(bundle_obj)

# Returns [] if valid, list of error strings if invalid
```

### 9.2 Required Field Checks

- All `REQUIRED_TOP_KEYS` present
- All decisions have `REQUIRED_DECISION_KEYS`
- No duplicate `decision_id` or `canonical_decision_id`
- Answer cited IDs exist in decisions
- Clusters have `cluster_id` and `label`

---

## 10. Integration Examples

### 10.1 Product Layer Consumption

```python
# In product layer
from ocl_adapter import retrieve_for_query
from ocl_adapter.bundle import build_bundle_from_retrieval
from product.query.answer import build_answer
from product.query.pipeline import counter_authority_pass

decisions, stats = retrieve_for_query(user_query)
bundle = build_bundle_from_retrieval(user_query, stats.query_variants_used, decisions, stats)

# Enrich with answer
answer = build_answer(user_query, [d.to_dict() for d in bundle.decisions])
bundle = enrich_bundle_with_answer(bundle, answer)

# Enrich with counter-authority
counter_hits, counter_info = counter_authority_pass(
    user_query, 
    [d.to_dict() for d in bundle.decisions],
    {d.decision_id: d.full_text for d in bundle.decisions}
)
bundle = enrich_bundle_with_counter_authority(bundle, counter_hits, counter_info)

# Enrich with map (clustering/projection)
clusters, relations = build_map(bundle.decisions)
bundle = enrich_bundle_with_map(bundle, clusters, relations, map_info)

# Return to UI
return bundle.to_dict()
```

### 10.2 Testing with Fixtures

```python
import json
from pathlib import Path
from ocl_adapter.bundle import QueryResultBundle, validate_bundle

# Load fixture
fixture = json.loads(Path("fixtures/minimal_fixture.json").read_text())

# Validate
errors = validate_bundle(fixture)
assert errors == []

# Deserialize
bundle = QueryResultBundle.from_dict(fixture)
assert bundle.query == "test query"
assert len(bundle.decisions) == 2
```

---

## 11. Versioning & Compatibility

| Version | Bundle Version | Schema Version | Notes |
|---------|---------------|----------------|-------|
| 1.0.0   | 1.0           | 1              | Initial release per charter v2 |

- **Bundle version**: Semantic version for bundle format changes
- **Schema version**: Integer for structural changes
- **Adapter version**: Semantic version for code changes

Breaking changes require charter revision and major version bump.

---

## 12. Performance Targets

| Metric | Target |
|--------|--------|
| Live query → bundle (≤150 decisions) | < 5s p95 |
| Cached query → bundle | < 1s |
| Cold start (first query) | < 3s (excluding model download) |
| Memory footprint | < 500MB |
| Cache hit rate (repeated queries) | > 90% |

---

## 13. Compliance with Charter Acceptance Tests

| Acceptance Criterion | Implementation |
|---------------------|----------------|
| (1) Runnable Python adapter/CLI | `ocl_adapter/cli.py`, `main()` |
| (2) Real Swiss-law query → bundle | `retrieve_for_query()`, `build_bundle_from_retrieval()` |
| (3) Deterministic deduplication | `deduplicate_decisions()`, `DecisionIdentity` |
| (4) Lazy full decision fetching | `fetch_decision_lazy()`, `full_text_for_top` config |
| (5) Citation-neighborhood expansion | `enable_citation_expansion`, `get_decision_citations()` |
| (6) FR/DE/IT query variants | `QueryExpander`, `get_search_variants()` |
| (7) Cached fixtures for tests | `fixtures/minimal_fixture.json`, `generate_fixtures.py` |
| (8) Tests for pagination, cache, dedupe, provenance, degradation | `tests/test_adapter.py` (41 tests) |
| (9) Machine-readable contract | This document (`contracts/INTEGRATION_CONTRACT.md`) |

---

## 14. Files & Artifacts

```
frontier/frontier-query-retrieval/
├── ocl_adapter/
│   ├── __init__.py           # Public API exports
│   ├── client.py             # OpenCaseLawClient, RateLimiter, CacheManager
│   ├── expansion.py          # QueryExpander, multilingual synonyms
│   ├── deduplication.py      # DecisionIdentity, deduplicate_decisions
│   ├── retrieval.py          # RetrievalOrchestrator, config
│   ├── bundle.py             # QueryResultBundle, validation, builders
│   └── cli.py                # CLI entry point
├── fixtures/
│   ├── minimal_fixture.json  # Offline test fixture
│   └── generate_fixtures.py  # Fixture generator
├── tests/
│   └── test_adapter.py       # 41 unit/integration tests
└── contracts/
    └── INTEGRATION_CONTRACT.md  # This document
```

---

## 15. Dependencies

### Runtime
- Python 3.10+
- `requests` or `urllib` (stdlib only, no external deps)
- `sklearn` (for TF-IDF in product layer, not in adapter)

### Development
- `pytest` (testing)
- `pytest-mock` (mocking)

---

## 16. Support & Escalation

- **Technical issues**: Autonomous retry/recovery built-in
- **Schema changes**: Require charter revision
- **Performance regression**: Automated benchmarks in test suite
- **API changes**: Monitor OpenCaseLaw `/api/docs` for breaking changes

---

*Generated per Charter v2, Team frontier-query-retrieval*