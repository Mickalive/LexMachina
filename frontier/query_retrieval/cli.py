#!/usr/bin/env python3
"""
CLI for OpenCaseLaw Retrieval Adapter
"""
import argparse
import json
import sys
from pathlib import Path

from .retriever import create_retriever, OpenCaseLawRetriever
from .bundle import validate_bundle, QueryResultBundle


def main():
    parser = argparse.ArgumentParser(
        description="LexMachina OpenCaseLaw Retrieval Adapter CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Live retrieval (default)
  python -m frontier.query_retrieval.cli "Arbeitsvertrag Kündigung Bonus"
  
  # With custom target count
  python -m frontier.query_retrieval.cli "Arbeitsvertrag Kündigung" --target 200
  
  # Offline mode with fixtures
  python -m frontier.query_retrieval.cli "Arbeitsvertrag" --offline --fixtures ./fixtures
  
  # Save output as JSON
  python -m frontier.query_retrieval.cli "Mietrecht Kündigungsschutz" --output bundle.json
  
  # Validate existing bundle
  python -m frontier.query_retrieval.cli --validate bundle.json
        """
    )
    
    parser.add_argument("query", nargs="?", help="Legal research query")
    parser.add_argument("--target", type=int, default=150, help="Target candidate count (default: 150)")
    parser.add_argument("--max", type=int, default=300, help="Maximum candidate count (default: 300)")
    parser.add_argument("--no-multilingual", action="store_true", help="Disable multilingual expansion")
    parser.add_argument("--no-citations", action="store_true", help="Disable citation expansion")
    parser.add_argument("--offline", action="store_true", help="Run in offline mode (requires fixtures)")
    parser.add_argument("--fixtures", type=Path, default=Path("/tmp/lexmachina_fixtures"), help="Fixture directory")
    parser.add_argument("--cache-ttl", type=int, default=3600, help="Cache TTL in seconds")
    parser.add_argument("--output", type=Path, help="Output file for bundle JSON")
    parser.add_argument("--validate", type=Path, help="Validate existing bundle file")
    parser.add_argument("--load-full-text", nargs="+", help="Decision IDs to load full text for")
    parser.add_argument("--load-structure", nargs="+", help="Decision IDs to load structure for")
    parser.add_argument("--load-citations", nargs="+", help="Decision IDs to load citations for")
    parser.add_argument("--pretty", action="store_true", help="Pretty print JSON output")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output")
    
    args = parser.parse_args()
    
    if args.validate:
        return validate_bundle_file(args.validate)
    
    if not args.query:
        parser.error("Query is required unless --validate is used")
    
    # Create retriever
    retriever = create_retriever(
        target_count=args.target,
        max_count=args.max,
        enable_multilingual=not args.no_multilingual,
        enable_citations=not args.no_citations,
        offline=args.offline,
        cache_ttl=args.cache_ttl,
    )
    
    if args.offline:
        retriever.client.fixture_dir = args.fixtures
        retriever.client.offline_mode = True
    
    # Execute retrieval
    bundle = retriever.retrieve(args.query)
    
    # Lazy load additional content if requested
    if args.load_full_text:
        retriever.load_full_text(bundle, args.load_full_text)
    if args.load_structure:
        retriever.load_structure(bundle, args.load_structure)
    if args.load_citations:
        retriever.load_citations(bundle, args.load_citations)
    
    # Output
    output_json = bundle.to_json(include_full_content=bool(args.load_full_text or args.load_structure or args.load_citations))
    
    if args.output:
        args.output.write_text(output_json)
        if not args.quiet:
            print(f"Bundle saved to {args.output}", file=sys.stderr)
    else:
        print(output_json if args.pretty else bundle.to_json())
    
    if not args.quiet:
        print_stats(bundle, retriever)
    
    return 0


def validate_bundle_file(path: Path) -> int:
    """Validate a bundle file."""
    try:
        data = json.loads(path.read_text())
        bundle = QueryResultBundle.from_dict(data)
        errors = validate_bundle(bundle)
        
        if errors:
            print(f"VALIDATION FAILED ({len(errors)} errors):")
            for err in errors:
                print(f"  - {err}")
            return 1
        else:
            print(f"VALIDATION PASSED: {len(bundle.decisions)} decisions")
            print(f"  Languages: {', '.join(sorted(bundle.languages()))}")
            print(f"  Courts: {', '.join(sorted(bundle.courts()))}")
            print(f"  Counter-authorities: {len(bundle.get_counter_authorities())}")
            print(f"  Supporting: {len(bundle.get_supporting_authorities())}")
            print(f"  Unclassified: {len(bundle.get_unclassified())}")
            return 0
    except Exception as e:
        print(f"ERROR: {e}")
        return 1


def print_stats(bundle: QueryResultBundle, retriever: OpenCaseLawRetriever) -> None:
    """Print retrieval statistics."""
    print(f"\n=== Retrieval Stats ===", file=sys.stderr)
    print(f"Query: {bundle.query}", file=sys.stderr)
    print(f"Decisions in bundle: {len(bundle.decisions)}", file=sys.stderr)
    print(f"Languages: {', '.join(sorted(bundle.languages()))}", file=sys.stderr)
    print(f"Courts: {', '.join(sorted(bundle.courts()))}", file=sys.stderr)
    print(f"Counter-authorities: {len(bundle.get_counter_authorities())}", file=sys.stderr)
    print(f"Supporting: {len(bundle.get_supporting_authorities())}", file=sys.stderr)
    print(f"Unclassified: {len(bundle.get_unclassified())}", file=sys.stderr)
    
    stats = retriever.get_stats()
    print(f"\nClient stats:", file=sys.stderr)
    print(f"  Queries executed: {stats['queries_executed']}", file=sys.stderr)
    print(f"  Results fetched: {stats['total_results_fetched']}", file=sys.stderr)
    print(f"  Citations expanded: {stats['citations_expanded']}", file=sys.stderr)
    print(f"  Duplicates removed: {stats['deduplicates_removed']}", file=sys.stderr)
    print(f"  Cache: {stats['client_stats']['cache']}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())