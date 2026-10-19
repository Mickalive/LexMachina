"""Corrected OFFLINE entry point for the accepted concept-recall harness.

Why this file exists
--------------------
Charter acceptance test (3) names the invocation::

    python -m frontier_query_concept_recall.cli --bundle <path> --out <dir>

With a **fresh** ``<dir>`` and ``--offline`` that invocation is wrong.  The A1
channel's cached OpenCaseLaw envelopes live under this team's committed results
directory, but the accepted harness roots its cache only at ``<dir>/cache``.
The replay therefore finds no cached envelope for any A1 query, treats each as
an errored search, and emits a **fabricated** ``transport::all_queries_ok``
regression on a run that is otherwise perfect::

    --out <fresh>  --offline  ->  regressed_gates: ["transport::all_queries_ok"]
    --out <committed> --offline -> regressed_gates: []

This entry point performs the missing read-only fallback without modifying the
accepted package, so a fresh ``--out`` replays correctly and a genuinely empty
cache fails loudly instead of silently degrading.

Usage
-----
::

    PYTHONPATH=frontier python frontier/frontier-query-concept-recall/run_harness.py \
        --bundle <path> --out <dir> [--offline] [--print-verdict]

Identical to the accepted harness in every respect except where the A1 cache is
read from.  ``network_calls`` stays 0 for any replay served from the committed
cache.

Scope note
----------
This file lives under ``frontier/frontier-query-concept-recall/`` -- inside the
Frontier team's enforced write scope.  The accepted package at
``frontier/frontier_query_concept_recall/`` is deliberately left byte-untouched:
a Python package cannot be named with the hyphens in the team id, so that path
is outside the workflow's scope guard, and the package is already accepted and
independently audited (cycle 39178441123).  The remedy lives here instead of in
the audited code.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent.parent
_PACKAGE_PARENT = _REPO / "frontier"
if str(_PACKAGE_PARENT) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_PARENT))

from frontier_query_concept_recall import cli as harness_cli  # noqa: E402

#: Read-only locations of this team's committed A1-channel cache.
COMMITTED_CACHE_DIRS = (
    _REPO / "results/frontier/frontier-query-concept-recall/cache",
)

ABORT_MESSAGE = """\
offline replay found no cached A1-channel envelopes.

  --out cache dir            -> {out_cache}
  committed fallbacks        -> {fallbacks}

Nothing was measured, because a replay with no cache cannot measure anything.
Either point --out at this team's results directory, seed the cache with

    cp -r results/frontier/frontier-query-concept-recall/cache <dir>/

or drop --offline to issue the calls live (network; frozen per-search budget
applies).
"""


def committed_cache_roots() -> tuple[Path, ...]:
    roots = []
    for path in COMMITTED_CACHE_DIRS:
        resolved = path.resolve()
        if resolved.is_dir() and resolved not in roots:
            roots.append(resolved)
    return tuple(roots)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="frontier/frontier-query-concept-recall/run_harness.py",
        description="Offline-safe entry point for the accepted concept-recall harness")
    parser.add_argument("--bundle", action="append", dest="bundles")
    parser.add_argument("--out", default="results/frontier/frontier-query-concept-recall")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--print-verdict", action="store_true")
    args = parser.parse_args(argv)

    out_dir = Path(args.out)
    out_cache = out_dir / "cache"
    fallbacks = committed_cache_roots()

    if args.offline:
        visible = sum(1 for root in (out_cache, *fallbacks) if root.is_dir()
                      for _ in root.glob("*/*.json"))
        if visible == 0:
            print(ABORT_MESSAGE.format(out_cache=out_cache,
                                       fallbacks=[str(p) for p in fallbacks] or "none found"),
                  file=sys.stderr)
            return 2
        # The accepted harness reads its cache only from <out>/cache, so an
        # offline replay against a fresh <out> is served by seeding a scratch
        # copy.  Read-only with respect to the committed cache.
        if not out_cache.is_dir() or not any(out_cache.glob("*/*.json")):
            with tempfile.TemporaryDirectory() as tmp:
                scratch = Path(tmp) / "cache"
                for root in fallbacks:
                    shutil.copytree(root, scratch, dirs_exist_ok=True)
                bundles = harness_cli.load_bundles(args.bundles)
                record = harness_cli.run(bundles, Path(tmp), offline=True)
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "harness_results.json").write_text(
                json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        else:
            bundles = harness_cli.load_bundles(args.bundles)
            record = harness_cli.run(bundles, out_dir, offline=True)
    else:
        bundles = harness_cli.load_bundles(args.bundles)
        record = harness_cli.run(bundles, out_dir, offline=False)

    verdict = record["verdict"]
    print(json.dumps({k: verdict[k] for k in (
        "outcome", "accepted_baseline_reproduced", "improved_fr_it_cells",
        "reduced_under_covered_questions", "any_vacuous", "regressed_gates")},
        indent=1))
    if args.print_verdict:
        print(json.dumps({"network_calls": record["latency_budget"].get(
            "n_network_calls_this_run"), "cache_hits": record["latency_budget"].get(
            "n_cache_hits_this_run")}, indent=1))
    return 0 if verdict["accepted_baseline_reproduced"] else 1


if __name__ == "__main__":
    raise SystemExit(main())