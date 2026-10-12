#!/usr/bin/env python3
"""
Generate test fixtures for offline testing.

Run this script to create cached fixtures from live OpenCaseLaw API calls.
The fixtures can then be used for deterministic offline testing.

Usage:
    python generate_fixtures.py --query "miete" --output fixtures/miete_fixture.json
    python generate_fixtures.py --queries-file test_queries.txt --output-dir fixtures/
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import List, Dict, Any

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from ocl_adapter.client import OpenCaseLawClient, create_client, Decision
from ocl_adapter.expansion import get_search_variants
from ocl_adapter.retrieval import RetrievalOrchestrator, RetrievalConfig
from ocl_adapter.bundle import QueryResultBundle, build_bundle_from_retrieval


# Standard test queries covering different legal areas and languages
DEFAULT_TEST_QUERIES = [
    "miete kündigung erstreckung",           # German: tenancy law
    "bail congé prolongation",               # French: tenancy law
    "lavoro licenziamento",                  # Italian: employment law
    "arbeitsrecht kündigung",                # German: employment law
    "divorce pension alimentaire",           # French: family law
    "scheidung nachehelicher unterhalt",     # German: family law
    "erbrecht pflichtteil",                  # German: inheritance
    "succession reserve hereditaire",        # French: inheritance
    "strafrecht vorsatz fahrlässigkeit",     # German: criminal law
    "droit pénal intention négligence",      # French: criminal law
    "datenschutz einwilligung",              # German: data protection
    "protection données consentement",       # French: data protection
    "haftung schadenersatz",                 # German: liability
    "responsabilité dommages-intérêts",      # French: liability
    "asyl flüchtling",                       # German: asylum
    "asile réfugié",                         # French: asylum
]


def generate_fixture_for_query(
    query: str,
    client: OpenCaseLawClient,
    config: RetrievalConfig,
) -> Dict[str, Any]:
    """Generate a fixture for a single query."""
    print(f"Generating fixture for: {query}")
    
    orchestrator = RetrievalOrchestrator(client=client, config=config)
    decisions, stats = orchestrator.retrieve(query)
    
    bundle = build_bundle_from_retrieval(
        query=query,
        query_variants=stats.query_variants_used,
        decisions=decisions,
        retrieval_stats=stats,
        max_decisions=config.target_count,
    )
    
    return bundle.to_dict()


def save_fixture(bundle_dict: Dict[str, Any], output_path: Path) -> None:
    """Save fixture to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(bundle_dict, f, ensure_ascii=False, indent=2)
    print(f"Saved fixture to {output_path}")


def generate_all_fixtures(
    queries: List[str],
    output_dir: Path,
    config: RetrievalConfig,
    client: Optional[OpenCaseLawClient] = None,
) -> None:
    """Generate fixtures for multiple queries."""
    client = client or create_client(use_cache=True)
    
    for query in queries:
        try:
            bundle_dict = generate_fixture_for_query(query, client, config)
            
            # Create safe filename
            safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in query)
            safe_name = safe_name[:50]
            output_path = output_dir / f"{safe_name}.json"
            
            save_fixture(bundle_dict, output_path)
            
            # Be nice to the API
            time.sleep(1)
            
        except Exception as e:
            print(f"ERROR generating fixture for '{query}': {e}")


def create_minimal_fixture() -> Dict[str, Any]:
    """Create a minimal fixture for testing without API access."""
    return {
        "bundle_version": "1.0",
        "schema_version": 1,
        "query": "test query",
        "query_variants": ["test query"],
        "decisions": [
            {
                "decision_id": "bge_BGE_117_II_410",
                "canonical_decision_id": "bge_BGE_117_II_410",
                "canonical_url": "https://mcp.opencaselaw.ch/entscheid/bge_BGE_117_II_410",
                "citation_string_de": "BGE 117 II 410",
                "citation_string_fr": "ATF 117 II 410",
                "citation_string_it": "DTF 117 II 410",
                "court": "bge",
                "court_name": "Bundesgericht (BGE)",
                "canton": "CH",
                "chamber": "II",
                "docket_number": "BGE 117 II 410",
                "decision_date": "1990-07-01",
                "publication_date": "1991-01-01",
                "language": "de",
                "legal_area": "civil",
                "regeste": "Mieterstreckung; materielle Rechtskraft (Art. 273 OR; Art. 5 Abs. 2 der Schlussbestimmungen zum neuen Mietrecht).",
                "rule_statement": "Regeste: Mieterstreckung; materielle Rechtskraft...",
                "full_text": "Bundesgericht (BGE) Band II 1991 BGE 117 II 410...",
                "snippet": "Mieterstreckung; materielle Rechtskraft (Art. 273 OR; Art. 5 Abs. 2 der Schlussbestimmungen zum neuen Mietrecht).",
                "rank": 1,
                "score": 28.7941,
                "provenance": "fixture",
                "retrieval_method": "search",
                "query_variant": "test query",
                "statutes": ["Art. 273 OR", "Art. 5 Abs. 2 Schlußbestimmungen"],
                "citation_count": 23,
                "cited_by_count": 1,
                "cluster_id": None,
                "x": None,
                "y": None,
                "is_outlier": False,
                "counter_status": "none",
                "counter_evidence": "",
                "counter_markers": [],
                "content_hash": "aa7a9650cf2213d6",
            },
            {
                "decision_id": "bge_BGE_140_III_86",
                "canonical_decision_id": "bge_BGE_140_III_86",
                "canonical_url": "https://mcp.opencaselaw.ch/entscheid/bge_BGE_140_III_86",
                "citation_string_de": "BGE 140 III 86",
                "citation_string_fr": "ATF 140 III 86",
                "citation_string_it": "DTF 140 III 86",
                "court": "bge",
                "court_name": "Bundesgericht (BGE)",
                "canton": "CH",
                "chamber": "III",
                "docket_number": "BGE 140 III 86",
                "decision_date": "2014-03-18",
                "publication_date": None,
                "language": "de",
                "legal_area": "civil",
                "regeste": "Mietrecht; Formvorschriften; Kündigung; Erstreckung.",
                "rule_statement": "Regeste: Mietrecht; Formvorschriften; Kündigung; Erstreckung.",
                "full_text": "BGE 140 III 86...",
                "snippet": "Mietrecht; Formvorschriften; Kündigung; Erstreckung.",
                "rank": 2,
                "score": 25.3,
                "provenance": "fixture",
                "retrieval_method": "search",
                "query_variant": "test query",
                "statutes": ["Art. 266l OR", "Art. 271 OR"],
                "citation_count": 15,
                "cited_by_count": 3,
                "cluster_id": None,
                "x": None,
                "y": None,
                "is_outlier": False,
                "counter_status": "none",
                "counter_evidence": "",
                "counter_markers": [],
                "content_hash": "bb8b9650cf2213d7",
            },
        ],
        "clusters": [],
        "relations": [],
        "answer": None,
        "provenance": {
            "bundle_version": "1.0",
            "schema_version": 1,
            "query": "test query",
            "query_variants": ["test query"],
            "retrieval": {
                "total_api_calls": 0,
                "cache_hits": 0,
                "decisions_fetched": 2,
                "decisions_after_dedupe": 2,
                "citation_expansions": 0,
                "leading_cases_added": 0,
                "full_text_fetched": 0,
                "errors": [],
                "duration_seconds": 0.0,
                "provenance_breakdown": {"fixture": 2},
                "query_variants_used": ["test query"],
            },
            "answer": {},
            "counter_authority": {},
            "map": {},
            "timestamp": "2026-01-01T00:00:00Z",
            "bundle_id": "test1234",
            "adapter_version": "1.0.0",
            "charter_version": 2,
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description="Generate test fixtures for OpenCaseLaw retrieval adapter"
    )
    parser.add_argument(
        "--query",
        help="Single query to generate fixture for",
    )
    parser.add_argument(
        "--queries-file",
        type=Path,
        help="File with queries (one per line)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file for single query",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./fixtures"),
        help="Output directory for multiple queries",
    )
    parser.add_argument(
        "--target-count",
        type=int,
        default=50,
        help="Target number of decisions per query",
    )
    parser.add_argument(
        "--max-variants",
        type=int,
        default=3,
        help="Max query variants",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=2,
        help="Max pages per variant",
    )
    parser.add_argument(
        "--minimal",
        action="store_true",
        help="Create minimal fixture without API calls",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable cache for fresh API calls",
    )
    
    args = parser.parse_args()
    
    if args.minimal:
        fixture = create_minimal_fixture()
        output = args.output or Path("minimal_fixture.json")
        save_fixture(fixture, output)
        return
    
    if not args.query and not args.queries_file:
        parser.error("Must provide --query or --queries-file (or use --minimal)")
    
    config = RetrievalConfig(
        target_count=args.target_count,
        max_query_variants=args.max_variants,
        max_pages_per_query=args.max_pages,
    )
    
    if args.query:
        client = create_client(use_cache=not args.no_cache)
        bundle_dict = generate_fixture_for_query(args.query, client, config)
        output = args.output or Path(f"fixture_{int(time.time())}.json")
        save_fixture(bundle_dict, output)
    else:
        queries = []
        with open(args.queries_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    queries.append(line)
        
        if not queries:
            queries = DEFAULT_TEST_QUERIES
        
        generate_all_fixtures(queries, args.output_dir, config)


if __name__ == "__main__":
    main()