# LexMachina Frontier Query Retrieval — Integration Contract

## Overview

This document specifies the integration contract for the OpenCaseLaw Retrieval Adapter, a production-ready component that transforms Swiss legal questions into normalized `QueryResultBundle` objects for downstream answer generation and mapping.

**Component**: `frontier.query_retrieval`  
**Version**: 1.0.0  
**Status**: ACCEPTED (all tests pass)

---

## Public API

### Main Entry Point

```python
from frontier.query_retrieval import create_retriever

retriever = create_retriever(
    target_count=150,           # Target candidate count (default: 150)
    max_count=300,              # Maximum candidate count (default: 300)
    enable_multilingual=True,   # Enable DE/FR/IT query expansion (default: True)
    enable_citations=True,      # Enable citation neighborhood expansion (default: True)
    offline=False,              # Offline mode for testing (default: False)
    cache_ttl=3600,             # Cache TTL in seconds (default: 3600)
)

bundle = retriever.retrieve("Arbeitsvertrag Kündigung Bonus")
```

### Configuration Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `target_count` | int | 150 | Target number of candidates to retrieve |
| `max_count` | int | 300 | Hard maximum candidates (including citation expansion) |
| `enable_multilingual` | bool | True | Expand queries across DE/FR/IT legal terminology |
| `enable_citations` | bool | True | Expand via outgoing/incoming citations and appeal chains |
| `offline` | bool | False | Run in offline mode using cached fixtures |
| `cache_ttl` | int | 3600 | Response cache time-to-live in seconds |

### Advanced Configuration

For fine-grained control, use `RetrievalConfig` directly:

```python
from frontier.query_retrieval import OpenCaseLawRetriever, RetrievalConfig

config = RetrievalConfig(
    target_candidate_count=150,
    max_candidate_count=300,
    min_candidate_count=50,
    enable_multilingual=True,
    languages=["de", "fr", "it"],
    max_variants_per_language=3,
    enable_citation_expansion=True,
    max_citation_depth=1,
    max_outgoing_citations=20,
    max_incoming_citations=20,
    max_appeal_chain_decisions=10,
    deduplicate_by_decision_id=True,
    lazy_load_full_text=True,
    lazy_load_structure=True,
    lazy_load_citations=True,
    legal_area_filter=None,
    court_filter=None,
    date_from=None,
    date_to=None,
    use_cache=True,
    offline_mode=False,
)

retriever = OpenCaseLawRetriever(config=config)
bundle = retriever.retrieve("query")
```

---

## Output Contract: QueryResultBundle

The retriever returns a `QueryResultBundle` with the following structure:

```python
@dataclass
class QueryResultBundle:
    query: str                              # Original user query
    expanded_queries: Dict[str, List[str]]  # Language -> query variants
    decisions: List[DecisionBundleEntry]    # Retrieved decisions
    retrieval_metadata: Dict[str, Any]      # Pipeline metadata
    generated_at: str                       # ISO timestamp
    config_hash: str                        # Config fingerprint (16-char hex)
    total_candidates_found: int             # Before deduplication
    total_after_dedupe: int                 # After deduplication
    citation_expanded: bool                 # Whether citation expansion ran
    multilingual_expanded: bool             # Whether multilingual expansion ran
```

### DecisionBundleEntry

Each decision in the bundle contains:

```python
@dataclass
class DecisionBundleEntry:
    # Core identifiers (REQUIRED)
    decision_id: str                        # OpenCaseLaw decision ID
    canonical_url: str                      # https://mcp.opencaselaw.ch/entscheid/{id}
    citation_string_de: str                 # German citation (e.g., "BGE 142 III 381")
    citation_string_fr: str                 # French citation (e.g., "ATF 142 III 381")
    citation_string_it: str                 # Italian citation (e.g., "DTF 142 III 381")
    
    # Court metadata
    court: str                              # Court code (bge, bger, bvger, zh_obergericht, etc.)
    court_level: Optional[str]              # federal_supreme, federal_admin, cantonal, etc.
    canton: Optional[str]                   # Swiss canton code
    chamber: Optional[str]                  # Court chamber
    docket_number: Optional[str]            # Original docket number
    decision_date: Optional[str]            # YYYY-MM-DD
    language: str                           # de, fr, it
    legal_area: Optional[str]               # civil, criminal, administrative, etc.
    
    # Content (from search results)
    title: Optional[str]
    regeste: Optional[str]                  # Official court summary
    snippet: Optional[str]                  # Search result snippet
    
    # Provenance (REQUIRED - at least one entry)
    provenance: List[RetrievalProvenance]
    
    # Lazy-loaded content (populated on demand)
    full_text: Optional[str] = None
    structure: Optional[Dict] = None
    citations_outgoing: Optional[List] = None
    citations_incoming: Optional[List] = None
    appeal_chain: Optional[Dict] = None
    
    # Scoring
    retrieval_score: float = 0.0
    rerank_score: Optional[float] = None
    
    # Counter-authority classification
    counter_authority_status: CounterAuthorityStatus = UNCLASSIFIED
    counter_authority_evidence: Optional[str] = None
    
    # Map positioning (for visualization)
    cluster_id: Optional[int] = None
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
```

### RetrievalProvenance

Every decision carries full provenance:

```python
@dataclass
class RetrievalProvenance:
    source: RetrievalSource                 # OPENCASELAW_SEARCH, CITATION_OUTGOING, etc.
    query_variant: Optional[str]            # Query variant that found this decision
    language: Optional[str]                 # Language of the query variant
    relevance_score: Optional[float]        # OpenCaseLaw relevance score
    page: Optional[int]                     # Search page number
    offset: Optional[int]                   # Search offset
    retrieved_at: str                       # ISO timestamp
    citation_depth: int                     # 0 = direct search, 1 = citation expansion
    parent_decision_id: Optional[str]       # Parent decision for citation expansion
    expansion_type: Optional[str]           # "multilingual", "citation_outgoing", etc.
```

### RetrievalSource Enum

```python
class RetrievalSource(Enum):
    OPENCASELAW_SEARCH = "opencaselaw_search"
    OPENCASELAW_CITATION_OUTGOING = "opencaselaw_citation_outgoing"
    OPENCASELAW_CITATION_INCOMING = "opencaselaw_citation_incoming"
    OPENCASELAW_LEADING_CASE = "opencaselaw_leading_case"
    OPENCASELAW_APPEAL_CHAIN = "opencaselaw_appeal_chain"
    CACHE = "cache"
    FIXTURE = "fixture"
```

### CounterAuthorityStatus Enum

```python
class CounterAuthorityStatus(Enum):
    UNCLASSIFIED = "unclassified"
    SUPPORTING = "supporting"
    LIMITING = "limiting"
    CONTRARY = "contrary"
    DISTINGUISHING = "distinguishing"
    EXCEPTION = "exception"
    MINORITY_LINE = "minority_line"
    UNCERTAIN = "uncertain"
```

---

## Bundle Methods

```python
# Serialization
bundle.to_dict(include_full_content=False) -> Dict
bundle.to_json(include_full_content=False) -> str

# Deserialization
QueryResultBundle.from_dict(data) -> QueryResultBundle

# Querying
bundle.get_decision(decision_id) -> Optional[DecisionBundleEntry]
bundle.get_decisions_by_language(lang) -> List[DecisionBundleEntry]
bundle.get_counter_authorities() -> List[DecisionBundleEntry]
bundle.get_supporting_authorities() -> List[DecisionBundleEntry]
bundle.get_unclassified() -> List[DecisionBundleEntry]
bundle.decision_ids() -> Set[str]
bundle.languages() -> Set[str]
bundle.courts() -> Set[str]

# Validation
validate_bundle(bundle) -> List[str]  # Empty list = valid
```

---

## Lazy Loading API

After retrieval, enrich decisions on demand:

```python
# Load full text for specific decisions
retriever.load_full_text(bundle, ["bge_BGE_142_III_381"])

# Load structure (regeste, sachverhalt, erwaegungen)
retriever.load_structure(bundle, ["bge_BGE_142_III_381"])

# Load citation graph
retriever.load_citations(bundle, ["bge_BGE_142_III_381"])

# Load appeal chain
retriever.load_appeal_chain(bundle, ["bge_BGE_142_III_381"])
```

---

## Offline Testing

For deterministic CI/CD testing:

```python
retriever = create_retriever(
    target_count=100,
    offline=True,  # Uses fixtures from /tmp/lexmachina_fixtures
)

# Or with custom fixture directory
retriever = create_retriever(offline=True)
retriever.client.fixture_dir = Path("/path/to/fixtures")
```

Fixtures are JSON files named by cache key (SHA256 of request). The test suite includes fixtures for:
- Search queries (DE/FR/IT variants)
- Decision details
- Decision structure
- Citations (outgoing/incoming)
- Appeal chains

---

## Error Handling

The retriever handles failures gracefully:

- **Network errors**: Automatic retry with exponential backoff (3 retries)
- **Rate limits**: Token bucket limiter (5 req/s, burst 10)
- **Missing fixtures (offline)**: Raises `RuntimeError` with fixture key
- **Invalid bundles**: `validate_bundle()` returns list of errors

```python
try:
    bundle = retriever.retrieve("query")
except Exception as e:
    logger.error(f"Retrieval failed: {e}")
    # Handle or return empty bundle

errors = validate_bundle(bundle)
if errors:
    logger.warning(f"Bundle validation: {errors}")
```

---

## Statistics & Monitoring

```python
stats = retriever.get_stats()
# {
#     "queries_executed": 12,
#     "total_results_fetched": 150,
#     "citations_expanded": 23,
#     "deduplicates_removed": 5,
#     "client_stats": {
#         "request_count": 12,
#         "error_count": 0,
#         "cache": {"hits": 8, "misses": 4, "hit_rate": 0.67, "entries": 12},
#         "rate_limiter_tokens": 8.5
#     }
# }
```

---

## CLI Interface

```bash
# Live retrieval
python -m frontier.query_retrieval.cli "Arbeitsvertrag Kündigung Bonus"

# With options
python -m frontier.query_retrieval.cli "Mietrecht Kündigung" \
    --target 200 \
    --max 300 \
    --output bundle.json

# Offline mode
python -m frontier.query_retrieval.cli "Arbeitsvertrag" \
    --offline \
    --fixtures ./fixtures

# Validate bundle
python -m frontier.query_retrieval.cli --validate bundle.json

# Lazy load content
python -m frontier.query_retrieval.cli "Query" \
    --load-full-text bge_BGE_142_III_381 \
    --load-structure bge_BGE_142_III_381
```

---

## Integration Requirements for Product Layer

The product layer must:

1. **Call `retriever.retrieve(query)`** to get a `QueryResultBundle`
2. **Validate the bundle** using `validate_bundle(bundle)` before processing
3. **Use `bundle.get_counter_authorities()`** for adversarial pass
4. **Lazy-load full text/structure** only for decisions needed by answer generation
5. **Respect `config_hash`** for cache invalidation when retrieval config changes
6. **Preserve provenance** when passing decisions to downstream components

---

## Versioning & Compatibility

- **Config hash** (16-char hex) identifies retrieval configuration
- Bundle format changes require version bump in `config_hash` computation
- Breaking changes to `DecisionBundleEntry` fields require major version bump
- Backward-compatible additions (new optional fields) are minor versions

---

## Performance Targets

| Metric | Target |
|--------|--------|
| Live query → first results | < 5s (typical network) |
| Cached query → bundle | < 1s |
| Offline test suite | < 1s |
| 100-300 decisions with citations | < 10s live |
| Memory usage (offline) | < 50MB |

---

## Acceptance Criteria (from Charter)

All criteria verified by test suite:

1. ✅ Runnable Python adapter/CLI with live and cached modes
2. ✅ Real Swiss-law query → normalized bundle with decision_id, canonical_url, citation strings, language, date/court, title/regeste/snippet, provenance
3. ✅ Configurable target up to 300 results without violating rate limits
4. ✅ Deterministic deduplication by decision_id
5. ✅ Lazy full decision/structure fetching works
6. ✅ Citation-neighborhood expansion (incoming/outgoing/appeal chain) with provenance and bounded limits
7. ✅ FR/DE/IT query variants without fabricating translations
8. ✅ Cached fixtures make tests deterministic/offline
9. ✅ Tests exercise pagination, cache, dedupe, provenance, remote-failure degradation
10. ✅ This integration contract documents how product imports/copies the adapter

---

## Example Usage in Product

```python
# product/services/retrieval_service.py
from frontier.query_retrieval import create_retriever, validate_bundle

class RetrievalService:
    def __init__(self):
        self.retriever = create_retriever(
            target_count=150,
            max_count=300,
            enable_multilingual=True,
            enable_citations=True,
        )
    
    def retrieve_for_question(self, question: str) -> QueryResultBundle:
        bundle = self.retriever.retrieve(question)
        
        errors = validate_bundle(bundle)
        if errors:
            raise ValueError(f"Invalid bundle: {errors}")
        
        # Optionally enrich top decisions for answer generation
        top_decisions = sorted(
            bundle.decisions, 
            key=lambda d: d.retrieval_score, 
            reverse=True
        )[:20]
        decision_ids = [d.decision_id for d in top_decisions]
        
        self.retriever.load_full_text(bundle, decision_ids)
        self.retriever.load_structure(bundle, decision_ids)
        
        return bundle
```