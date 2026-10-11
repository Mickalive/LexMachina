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
        epilog=(
            "Offline fixture replay (deterministic, no network): "
            "python3 -m ocl_adapter 'Kündigung Mietvertrag Mietrecht' "
            "--preset fixtures --out bundle.json --validate"
        ),
    )
    p.add_argument("query", nargs="?", help="Swiss legal question / search query")
    p.add_argument("--query", dest="query_opt", default=None, help="same as positional query")
    p.add_argument("--preset", choices=("standard", "fixtures"), default="standard",
                   help="standard=today's CLI defaults; fixtures=exact recorded fixture "
                        "scenario (results/frontier/frontier-query-retrieval/fixtures/cache), "
                        "which also defaults --mode to offline")
    p.add_argument("--mode", choices=MODES, default=None,
                   help="live=network+cache, offline=cache only, refresh=network only "
                        "(default: live; offline with --preset fixtures)")
    p.add_argument("--cache-dir", default=None, help="cache/fixture directory")
    p.add_argument("--base-url", default=None, help="OpenCaseLaw API base URL")
    p.add_argument("--target", type=int, default=None,
                   help="soft candidate target (100-300); default 150")
    p.add_argument("--max-candidates", type=int, default=None, help="hard cap on candidates; default 300")
    p.add_argument("--page-size", type=int, default=None, help="page size for /decisions; default 100")
    p.add_argument("--max-pages", type=int, default=None,
                   help="max pages per query variant; default 3")
    p.add_argument("--max-requests", type=int, default=None, help="hard request budget; default 40")
    p.add_argument("--max-rps", type=float, default=None, help="max requests/second (<=5); default 4.0")
    p.add_argument("--lang-pages", type=int, default=None,
                   help="max pages per language-filter variant; default 1")
    p.add_argument("--citation-seeds", type=int, default=None,
                   help="citation-neighbourhood seeds; default 5")
    p.add_argument("--citation-page-size", type=int, default=None,
                   help="citations fetched per seed; default 20")
    p.add_argument("--leading-limit", type=int, default=None,
                   help="/leading-cases limit; default 20")
    p.add_argument("--stages", default=None,
                   help=f"comma list of stages from {STAGES}; default {','.join(STAGES)}")
    p.add_argument("--stop-at-target", action="store_true",
                   help="stop stages once the candidate target is met")
    p.add_argument("--no-stop-at-target", action="store_true",
                   help="run every requested stage even after the target is met")
    p.add_argument("--languages", default=None,
                   help=f"language filters for the 'lang' stage; default {','.join(LANGUAGES)}")
    p.add_argument("--no-citations", action="store_true", help="skip citation-neighbourhood expansion")
    p.add_argument("--no-leading", action="store_true", help="skip /leading-cases stage")
    p.add_argument("--hydrate", default="", help="comma list of decision ids to fully fetch")
    p.add_argument("--hydrate-top", type=int, default=None,
                   help="fully fetch the first N candidates; default 0 (2 with --preset fixtures)")
    p.add_argument("--hydrate-needs-detail", type=int, default=None,
                   help="also fully fetch the first N candidates flagged needs_detail; default 0")
    p.add_argument("--no-structure", action="store_true", help="skip /structure during hydration")
    p.add_argument("--out", default=None, help="write the candidate bundle JSON here")
    p.add_argument("--product-bundle", default=None,
                   help="also write the accepted product query_result_bundle JSON here")
    p.add_argument("--quiet", action="store_true", help="do not print the summary")
    p.add_argument("--validate", action="store_true",
                   help="validate the produced bundle and exit 4 on failure")
    return p


def _preset_dict(args: argparse.Namespace):
    """AdapterConfig snapshot for ``--preset fixtures``, else None."""
    if args.preset != "fixtures":
        return None
    from .fixtures import fixture_config  # local import keeps import graph light

    return fixture_config().to_dict()


def resolve_config_kwargs(args: argparse.Namespace) -> dict:
    """Precedence: explicit CLI flag > --preset fixture value > built-in default."""
    preset = _preset_dict(args)
    base = AdapterConfig().to_dict()

    def pick(arg_name: str, cfg_key: str):
        val = getattr(args, arg_name)
        if val is not None:
            return val
        if preset is not None and cfg_key in preset:
            return preset[cfg_key]
        return base[cfg_key]

    if args.mode is not None:
        mode = args.mode
    else:
        mode = "offline" if preset is not None else "live"

    if args.stop_at_target:
        stop = True
    elif args.no_stop_at_target:
        stop = False
    else:
        stop = bool(preset["stop_when_target_met"]) if preset is not None else base["stop_when_target_met"]

    def toggle(arg_name: str, cfg_key: str) -> bool:
        if getattr(args, arg_name):
            return False
        if preset is not None:
            return bool(preset[cfg_key])
        return bool(base[cfg_key])

    if args.stages is not None:
        stages = tuple(_csv(args.stages) or [])
    elif preset is not None:
        stages = tuple(preset["stages"])
    else:
        stages = tuple(base["stages"])

    if args.languages is not None:
        language_filters = tuple(_csv(args.languages) or LANGUAGES)
    elif preset is not None:
        language_filters = tuple(preset["language_filters"])
    else:
        language_filters = tuple(base["language_filters"])

    kwargs = dict(
        mode=mode,
        target=pick("target", "target"),
        max_candidates=pick("max_candidates", "max_candidates"),
        page_size=pick("page_size", "page_size"),
        max_pages_per_variant=pick("max_pages", "max_pages_per_variant"),
        max_requests=pick("max_requests", "max_requests"),
        max_rps=pick("max_rps", "max_rps"),
        lang_max_pages=pick("lang_pages", "lang_max_pages"),
        citation_seeds=pick("citation_seeds", "citation_seeds"),
        citation_page_size=pick("citation_page_size", "citation_page_size"),
        leading_cases_limit=pick("leading_limit", "leading_cases_limit"),
        hydrate_needs_detail=pick("hydrate_needs_detail", "hydrate_needs_detail"),
        stages=stages,
        stop_when_target_met=stop,
        citation_expansion=toggle("no_citations", "citation_expansion"),
        leading_cases=toggle("no_leading", "leading_cases"),
        language_filters=language_filters,
    )
    if preset is not None:
        kwargs.setdefault("cache_dir", preset["cache_dir"])
    return kwargs


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    query = (args.query_opt or args.query or "").strip()
    if not query:
        print("error: a query is required (positional or --query)", file=sys.stderr)
        return 2

    cfg_kwargs = resolve_config_kwargs(args)
    unknown = [s for s in cfg_kwargs["stages"] if s not in STAGES]
    if unknown:
        print(f"error: unknown stages {unknown}; valid: {STAGES}", file=sys.stderr)
        return 2

    if args.preset == "fixtures" and cfg_kwargs["mode"] == "offline":
        from .fixtures import FIXTURE_QUERY

        if query != FIXTURE_QUERY:
            print(
                "note: --preset fixtures records only the "
                f"'{FIXTURE_QUERY}' scenario; other queries replay as cache misses",
                file=sys.stderr,
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

    hydrate_top = args.hydrate_top
    if hydrate_top is None:
        hydrate_top = 2 if args.preset == "fixtures" else 0

    bundle = build_candidate_bundle(
        query,
        config=cfg,
        cache=FileCache(Path(cfg.cache_dir)),
        hydrate_ids=_csv(args.hydrate) or None,
        hydrate_top=hydrate_top,
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
