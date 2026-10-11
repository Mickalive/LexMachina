"""Command-line entry point for the OpenCaseLaw retrieval adapter.

Examples::

    # live retrieval, 150 candidates, all stages, write bundle + summary
    python3 -m ocl_adapter "Kündigung Mietvertrag Mietrecht" \\
        --target 150 --out results.json

    # fully offline replay of the recorded fixtures (deterministic)
    python3 -m ocl_adapter "Kündigung Mietvertrag Mietrecht" \\
        --mode offline --cache-dir results/frontier/frontier-query-retrieval/fixtures/cache \\
        --out offline.json --validate
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional, Sequence

from .bundle import (
    bundle_summary,
    to_product_bundle,
    validate_against_product,
    validate_candidate_bundle,
)
from .cache import FileCache
from .config import AdapterConfig, DEFAULT_FIXTURE_CACHE_DIR, LANGUAGES, MODES, STAGES
from .pipeline import build_candidate_bundle, make_transport


def _csv(value: Optional[str]) -> Optional[List[str]]:
    if value is None:
        return None
    return [p.strip() for p in value.split(",") if p.strip()]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ocl_adapter",
        description="OpenCaseLaw retrieval/cache adapter -> query_result_bundle candidates",
    )
    p.add_argument("query", nargs="?", help="Swiss legal question / search query")
    p.add_argument("--query", dest="query_opt", default=None, help="same as positional query")
    p.add_argument("--mode", choices=MODES, default="live",
                   help="live=network+cache, offline=cache only, refresh=network only")
    p.add_argument("--cache-dir", default=None, help="cache/fixture directory")
    p.add_argument("--base-url", default=None, help="OpenCaseLaw API base URL")
    p.add_argument("--target", type=int, default=150, help="soft candidate target (100-300)")
    p.add_argument("--max-candidates", type=int, default=300, help="hard cap on candidates")
    p.add_argument("--page-size", type=int, default=100, help="page size for /decisions")
    p.add_argument("--max-pages", type=int, default=3, help="max pages per query variant")
    p.add_argument("--max-requests", type=int, default=40, help="hard request budget")
    p.add_argument("--max-rps", type=float, default=4.0, help="max requests/second (<=5)")
    p.add_argument("--stages", default=",".join(STAGES),
                   help=f"comma list of stages from {STAGES}")
    p.add_argument("--no-stop-at-target", action="store_true",
                   help="run every requested stage even after the target is met")
    p.add_argument("--languages", default=",".join(LANGUAGES),
                   help="language filters for the 'lang' stage")
    p.add_argument("--no-citations", action="store_true", help="skip citation-neighbourhood expansion")
    p.add_argument("--no-leading", action="store_true", help="skip /leading-cases stage")
    p.add_argument("--hydrate", default="", help="comma list of decision ids to fully fetch")
    p.add_argument("--hydrate-top", type=int, default=0, help="fully fetch the first N candidates")
    p.add_argument("--no-structure", action="store_true", help="skip /structure during hydration")
    p.add_argument("--out", default=None, help="write the candidate bundle JSON here")
    p.add_argument("--product-bundle", default=None,
                   help="also write the accepted product query_result_bundle JSON here")
    p.add_argument("--quiet", action="store_true", help="do not print the summary")
    p.add_argument("--validate", action="store_true",
                   help="validate the produced bundle and exit 4 on failure")
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    query = (args.query_opt or args.query or "").strip()
    if not query:
        print("error: a query is required (positional or --query)", file=sys.stderr)
        return 2

    stages = tuple(_csv(args.stages) or [])
    unknown = [s for s in stages if s not in STAGES]
    if unknown:
        print(f"error: unknown stages {unknown}; valid: {STAGES}", file=sys.stderr)
        return 2

    cfg_kwargs = dict(
        mode=args.mode,
        target=args.target,
        max_candidates=args.max_candidates,
        page_size=args.page_size,
        max_pages_per_variant=args.max_pages,
        max_requests=args.max_requests,
        max_rps=args.max_rps,
        stages=stages,
        stop_when_target_met=not args.no_stop_at_target,
        citation_expansion=not args.no_citations,
        leading_cases=not args.no_leading,
        language_filters=tuple(_csv(args.languages) or LANGUAGES),
    )
    if args.cache_dir:
        cfg_kwargs["cache_dir"] = args.cache_dir
    if args.base_url:
        cfg_kwargs["base_url"] = args.base_url
    try:
        cfg = AdapterConfig(**cfg_kwargs)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    bundle = build_candidate_bundle(
        query,
        config=cfg,
        cache=FileCache(Path(cfg.cache_dir)),
        hydrate_ids=_csv(args.hydrate) or None,
        hydrate_top=args.hydrate_top,
        include_structure=not args.no_structure,
    )

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.product_bundle:
        out = Path(args.product_bundle)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(to_product_bundle(bundle), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    exit_code = 0
    summary = bundle_summary(bundle)
    errors = []
    if args.validate:
        errors = validate_candidate_bundle(bundle)
        errors += [f"product_bridge: {e}" for e in validate_against_product(bundle)]
        summary["validation_errors"] = errors
        if errors:
            exit_code = 4
    if not bundle.get("candidates"):
        summary["error"] = "no candidates retrieved"
        exit_code = exit_code or 3

    if not args.quiet:
        print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
        if errors:
            for e in errors:
                print(f"validation: {e}", file=sys.stderr)
    return exit_code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
