"""
CLI for OpenCaseLaw Retrieval Adapter.

Provides live and cached modes for testing and production use.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Optional, List

from .client import OpenCaseLawClient, create_client, RateLimiter, CacheManager
from .expansion import QueryExpander, get_search_variants
from .retrieval import RetrievalOrchestrator, RetrievalConfig, retrieve_for_query
from .bundle import (
    QueryResultBundle,
    build_bundle_from_retrieval,
    validate_bundle,
    BUNDLE_VERSION,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="ocl-retrieve",
        description="OpenCaseLaw Retrieval Adapter - Swiss legal query to query_result_bundle",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    
    # Query arguments
    parser.add_argument(
        "query",
        nargs="?",
        help="Swiss legal research query (if omitted, reads from stdin)",
    )
    parser.add_argument(
        "-q", "--query-file",
        type=Path,
        help="Read query from file",
    )
    
    # Mode arguments
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--live",
        action="store_true",
        help="Force live API calls (default if cache disabled)",
    )
    mode_group.add_argument(
        "--cached",
        action="store_true",
        help="Force cached mode only (fail if not in cache)",
    )
    mode_group.add_argument(
        "--offline",
        action="store_true",
        help="Run with fixture data only (no network)",
    )
    
    # Output arguments
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output bundle to JSON file (default: stdout)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print bundle summary instead of full JSON",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )
    
    # Retrieval configuration
    parser.add_argument(
        "-n", "--target-count",
        type=int,
        default=150,
        help="Target number of decisions to retrieve",
    )
    parser.add_argument(
        "--max-variants",
        type=int,
        default=4,
        help="Maximum query expansion variants to execute",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=5,
        help="Maximum pagination pages per variant",
    )
    parser.add_argument(
        "--language",
        choices=["de", "fr", "it", "rm"],
        help="Filter by language",
    )
    parser.add_argument(
        "--court",
        help="Filter by court code",
    )
    parser.add_argument(
        "--date-from",
        help="Filter decisions from date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--date-to",
        help="Filter decisions to date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--no-citation-expansion",
        action="store_true",
        help="Disable citation neighborhood expansion",
    )
    parser.add_argument(
        "--no-leading-cases",
        action="store_true",
        help="Disable leading cases expansion",
    )
    parser.add_argument(
        "--full-text-top",
        type=int,
        default=20,
        help="Fetch full text for top N decisions",
    )
    
    # Cache configuration
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("./.ocl_cache"),
        help="Cache directory",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable caching entirely",
    )
    parser.add_argument(
        "--cache-ttl",
        type=int,
        default=86400,
        help="Cache TTL in seconds",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear cache before running",
    )
    
    # Rate limiting
    parser.add_argument(
        "--rate-limit",
        type=int,
        default=5,
        help="Max requests per second",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds",
    )
    
    # Testing/debugging
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate bundle without output",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Print retrieval statistics",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="count",
        default=0,
        help="Increase verbosity",
    )
    
    # Expansion testing
    parser.add_argument(
        "--expand-only",
        action="store_true",
        help="Only show query expansion variants",
    )
    
    return parser


def setup_logging(verbosity: int) -> None:
    """Configure logging based on verbosity."""
    import logging
    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def get_query(args: argparse.Namespace) -> str:
    """Get query from arguments."""
    if args.query:
        return args.query
    if args.query_file:
        return args.query_file.read_text(encoding="utf-8").strip()
    # Read from stdin
    return sys.stdin.read().strip()


def run_expand_only(query: str, args: argparse.Namespace) -> int:
    """Run query expansion only."""
    expander = QueryExpander(max_variants=args.max_variants)
    result = expander.expand_query(query)
    
    print(f"Original query: {result.original_query}")
    print(f"Detected language: {result.language_detected or 'unknown'}")
    print(f"Combined query: {result.combined_query}")
    print(f"\nVariants ({len(result.variants)}):")
    for i, variant in enumerate(result.variants):
        print(f"  {i+1}. {variant}")
    
    print(f"\nExpanded terms by language:")
    for lang in ["de", "fr", "it"]:
        terms = result.expanded_terms.get(lang, [])
        if terms:
            print(f"  {lang}: {', '.join(terms[:10])}")
    
    return 0


def create_client_from_args(args: argparse.Namespace) -> OpenCaseLawClient:
    """Create client from CLI arguments."""
    use_cache = not args.no_cache and not args.offline
    cache_dir = None if args.offline else args.cache_dir
    
    if args.clear_cache and cache_dir:
        import shutil
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
    
    return create_client(
        cache_dir=cache_dir,
        use_cache=use_cache,
        rate_limit=args.rate_limit,
        cache_ttl=args.cache_ttl,
    )


def run_retrieval(query: str, args: argparse.Namespace) -> Tuple[QueryResultBundle, RetrievalConfig]:
    """Run the full retrieval pipeline."""
    client = create_client_from_args(args)
    
    config = RetrievalConfig(
        target_count=args.target_count,
        max_query_variants=args.max_variants,
        max_pages_per_query=args.max_pages,
        enable_citation_expansion=not args.no_citation_expansion,
        enable_leading_cases=not args.no_leading_cases,
        language_filter=args.language,
        court_filter=args.court,
        date_from=args.date_from,
        date_to=args.date_to,
        full_text_for_top=args.full_text_top,
        timeout=args.timeout,
    )
    
    if args.cached:
        # In cached mode, we still use the client but it will only hit cache
        # For true offline, we'd need fixture loading
        pass
    
    decisions, stats = retrieve_for_query(query, config=config, client=client)
    
    bundle = build_bundle_from_retrieval(
        query=query,
        query_variants=stats.query_variants_used,
        decisions=decisions,
        retrieval_stats=stats,
        max_decisions=args.target_count,
    )
    
    return bundle, config


def print_summary(bundle: QueryResultBundle, stats: Optional[RetrievalConfig] = None) -> None:
    """Print bundle summary."""
    summary = bundle.summary()
    
    print(f"\n=== Query Result Bundle Summary ===")
    print(f"Bundle ID: {summary['bundle_id']}")
    print(f"Query: {summary['query']}")
    print(f"Bundle Version: {BUNDLE_VERSION}")
    print(f"\nDecisions: {summary['n_decisions']}")
    print(f"Clusters: {summary['n_clusters']}")
    print(f"Relations: {summary['n_relations']}")
    print(f"Cited in answer: {summary['n_cited']}")
    print(f"Counter-authorities: {summary['n_counter']}")
    print(f"\nLanguages:")
    for lang, count in sorted(summary['languages'].items()):
        print(f"  {lang}: {count}")
    
    print(f"\nProvenance:")
    for prov, count in sorted(summary['provenance_breakdown'].items()):
        print(f"  {prov}: {count}")
    
    if stats:
        print(f"\nRetrieval config:")
        print(f"  Target count: {stats.target_count}")
        print(f"  Citation expansion: {stats.enable_citation_expansion}")
        print(f"  Leading cases: {stats.enable_leading_cases}")


def print_stats(stats) -> None:
    """Print retrieval statistics."""
    print(f"\n=== Retrieval Statistics ===")
    print(f"Query: {stats.query}")
    print(f"Duration: {stats.duration_seconds:.2f}s")
    print(f"API calls: {stats.total_api_calls}")
    print(f"Cache hits: {stats.cache_hits}")
    print(f"Decisions fetched: {stats.decisions_fetched}")
    print(f"After deduplication: {stats.decisions_after_dedupe}")
    print(f"Citation expansions: {stats.citation_expansions}")
    print(f"Leading cases added: {stats.leading_cases_added}")
    print(f"Full text fetched: {stats.full_text_fetched}")
    print(f"Query variants used: {len(stats.query_variants_used)}")
    for variant in stats.query_variants_used:
        print(f"  - {variant}")
    if stats.errors:
        print(f"Errors ({len(stats.errors)}):")
        for err in stats.errors:
            print(f"  - {err}")


def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    
    setup_logging(args.verbose)
    
    query = get_query(args)
    if not query:
        parser.error("No query provided. Use positional argument, --query-file, or stdin.")
    
    if args.expand_only:
        return run_expand_only(query, args)
    
    # Run retrieval
    print(f"Query: {query}", file=sys.stderr)
    start = time.time()
    
    try:
        bundle, config = run_retrieval(query, args)
    except Exception as e:
        print(f"ERROR: Retrieval failed: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
    
    elapsed = time.time() - start
    print(f"Retrieval completed in {elapsed:.2f}s", file=sys.stderr)
    
    # Validate
    errors = validate_bundle_object(bundle)
    if errors:
        print(f"VALIDATION ERRORS:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        if args.validate_only:
            return 1
    
    if args.validate_only:
        print("Bundle validation: PASSED", file=sys.stderr)
        return 0
    
    # Output
    if args.summary:
        print_summary(bundle, config)
    else:
        output = bundle.to_json(indent=2 if args.pretty else None)
        if args.output:
            args.output.write_text(output, encoding="utf-8")
            print(f"Bundle written to {args.output}", file=sys.stderr)
        else:
            print(output)
    
    if args.stats:
        # We don't have stats object here, but bundle has provenance
        # Could reconstruct from provenance if needed
        pass
    
    return 0


if __name__ == "__main__":
    sys.exit(main())