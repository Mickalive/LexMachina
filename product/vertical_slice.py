#!/usr/bin/env python3
"""
LexMachina Query-Map Vertical Slice

End-to-end demo: legal question -> OpenCaseLaw retrieval -> query_result_bundle
-> query-specific clickable map -> sourced generative answer -> counter-authority pass.

This is the canonical MVP vertical slice per QUERY_MAP_MVP.md.
Uses only free OpenCaseLaw public infrastructure and existing repository code.
No paid APIs, no universal 174k embeddings, no custom model training.
"""

import sys
import json
from collections import Counter
from pathlib import Path

# Ensure product package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "frontier" / "frontier-query-retrieval"))

from pathlib import Path
from query.pipeline import run_query
from query.bundle import validate_bundle, bundle_summary, annotate_content_state
from query.qmap import build_map
from query.counter_evidence_span import apply_verified_span_selection


def vertical_slice(query: str, top_n: int = 120, retrieval_mode: str = "offline",
                   fixture_generation: bool = True) -> dict:
    """
    Run the complete query-map MVP pipeline for one query.

    Returns a dict with:
    - bundle: the full query_result_bundle
    - summary: bundle summary statistics
    - counter_status_dist: Counter of counter_status values
    - content_coverage: local inspectability coverage
    """
    # Phase 1: Retrieval + reranking + answer + counter-authority (fixture mode)
    print(f"=== Query: {query} ===")
    print(f"Mode: {retrieval_mode}, fixture_generation={fixture_generation}")
    bundle = run_query(
        query, top_n=top_n, retrieval_mode=retrieval_mode,
        fixture_generation=fixture_generation,
    )

    # Phase 2: Validation
    errors = validate_bundle(bundle)
    if errors:
        raise RuntimeError(f"Invalid bundle: {errors}")

    # Phase 3: Content state annotation (local inspectability)
    bundle = annotate_content_state(bundle)

    # Phase 4: Build query-specific map (projection + clustering)
    mapped, clusters, relations = build_map(bundle["decisions"], n_clusters=8)

    # Phase 5: Counter-evidence span selection (direction v65/v68)
    # This selects verbatim verbatim spans from each decision's own text
    # and lets the frozen decide_label gate confirm or abstain.
    bundle = apply_verified_span_selection(bundle, qid=None)

    # Phase 6: Summary statistics
    summary = bundle_summary(bundle)
    counter_status_dist = Counter(d.get("counter_status") for d in bundle["decisions"])

    return {
        "bundle": bundle,
        "summary": summary,
        "counter_status_dist": dict(counter_status_dist),
        "content_coverage": bundle["provenance"]["content_coverage"],
        "mapped_decisions": len(mapped),
        "n_clusters": len(clusters),
        "n_relations": len(relations),
        "phase": bundle["provenance"]["phase"],
        "latency_seconds": bundle["provenance"]["latency_seconds"],
    }


def main():
    """CLI entry point for the vertical slice."""
    import argparse
    parser = argparse.ArgumentParser(description="LexMachina Query-Map Vertical Slice")
    parser.add_argument("query", nargs="?", default="Kündigung Mietvertrag Mietrecht",
                        help="Swiss law research question")
    parser.add_argument("--top-n", type=int, default=120,
                        help="Target number of decisions (100-300 per QUERY_MAP_MVP)")
    parser.add_argument("--mode", choices=["live", "offline", "fixture"], default="offline",
                        help="Retrieval mode: live=network, offline=cache, fixture=frozen envelopes")
    parser.add_argument("--no-fixture-generation", action="store_true",
                        help="Skip generative answer (use extractive fallback only)")
    parser.add_argument("--output", type=str, default=None,
                        help="Write bundle JSON to file")
    args = parser.parse_args()

    # Run the vertical slice
    result = vertical_slice(
        query=args.query,
        top_n=args.top_n,
        retrieval_mode=args.mode,
        fixture_generation=not args.no_fixture_generation,
    )

    # Output results
    print("\n=== VERTICAL SLICE RESULTS ===")
    print(json.dumps({
        "query": args.query,
        "phase": result["phase"],
        "latency_seconds": result["latency_seconds"],
        "n_decisions": result["mapped_decisions"],
        "n_clusters": result["n_clusters"],
        "n_relations": result["n_relations"],
        "counter_status_dist": result["counter_status_dist"],
        "content_coverage": result["content_coverage"],
        "summary": {
            "n_decisions": result["summary"]["n_decisions"],
            "n_clusters": result["summary"]["n_clusters"],
            "n_relations": result["summary"]["n_relations"],
            "n_counter_authorities": result["summary"]["n_counter_authorities"],
            "languages": result["summary"]["languages"],
        },
    }, indent=2, ensure_ascii=False))

    # Optionally write the full bundle to file
    if args.output:
        bundle_path = Path(args.output)
        bundle_path.parent.mkdir(parents=True, exist_ok=True)
        with open(bundle_path, "w", encoding="utf-8") as f:
            json.dump(result["bundle"], f, indent=2, ensure_ascii=False)
        print(f"\nBundle written to: {bundle_path}")


if __name__ == "__main__":
    main()