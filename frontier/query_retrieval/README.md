# LexMachina Frontier Query Retrieval

Production-ready OpenCaseLaw retrieval adapter for Swiss legal research.

## Quick Start

```bash
# Install dependencies
pip install requests urllib3

# Run retrieval (live)
python -m frontier.query_retrieval.cli "Arbeitsvertrag Kündigung Bonus"

# Run with options
python -m frontier.query_retrieval.cli "Mietrecht Kündigungsschutz" --target 200 --output bundle.json

# Offline mode (for testing)
python -m frontier.query_retrieval.cli "Arbeitsvertrag" --offline

# Validate bundle
python -m frontier.query_retrieval.cli --validate bundle.json
```

## Python API

```python
from frontier.query_retrieval import create_retriever

retriever = create_retriever(
    target_count=150,
    max_count=300,
    enable_multilingual=True,
    enable_citations=True,
)

bundle = retriever.retrieve("Arbeitsvertrag Kündigung Bonus")
print(f"Found {len(bundle.decisions)} decisions")

# Lazy load full content for answer generation
retriever.load_full_text(bundle, [d.decision_id for d in bundle.decisions[:10]])
```

## Features

- **Multilingual query expansion** across DE/FR/IT legal terminology
- **Citation neighborhood expansion** (outgoing/incoming/appeal chain)
- **Deterministic deduplication** by decision_id
- **Provenance tracking** for every decision
- **Lazy loading** of full text, structure, citations
- **Rate limiting** (5 req/s, respects OpenCaseLaw limits)
- **Response caching** with TTL
- **Offline mode** with cached fixtures for deterministic testing
- **CLI** for ad-hoc queries and validation

## Testing

```bash
# Run all tests
python -m pytest frontier/query_retrieval/test_retriever.py -v

# Run specific test class
python -m pytest frontier/query_retrieval/test_retriever.py::TestOpenCaseLawRetriever -v
```

## Integration Contract

See [INTEGRATION_CONTRACT.md](INTEGRATION_CONTRACT.md) for complete API specification.

## Architecture

```
query_retrieval/
├── __init__.py           # Package exports
├── opencaselaw_client.py # HTTP client with rate limiting, caching, offline mode
├── query_expansion.py    # DE/FR/IT legal terminology mappings
├── bundle.py             # Normalized data structures (QueryResultBundle, DecisionBundleEntry)
├── retriever.py          # Main pipeline orchestrator
├── cli.py                # Command-line interface
├── test_retriever.py     # Comprehensive test suite (46 tests)
└── INTEGRATION_CONTRACT.md # Product integration documentation
```

## Acceptance Criteria

All charter requirements verified:

1. ✅ Runnable Python adapter/CLI with live and cached modes
2. ✅ Swiss-law query → normalized bundle with all required fields
3. ✅ Configurable target up to 300 results, respects rate limits
4. ✅ Deterministic deduplication by decision_id
5. ✅ Lazy full decision/structure/citation fetching
6. ✅ Citation-neighborhood expansion with provenance
7. ✅ FR/DE/IT query variants without fabricating translations
8. ✅ Cached fixtures for deterministic offline tests
9. ✅ Tests for pagination, cache, dedupe, provenance, failure degradation
10. ✅ Integration contract documented