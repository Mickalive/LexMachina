#!/usr/bin/env python3
"""Record live OpenCaseLaw responses into the committed fixture cache.

Usage::

    python3 record_fixtures.py           # idempotent: fills missing entries
    python3 record_fixtures.py --force   # wipes and re-records

Writes ``results/frontier/frontier-query-retrieval/fixtures/FIXTURE_META.json``
plus one cache envelope per request under ``fixtures/cache/``.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ocl_adapter.fixtures import FIXTURE_QUERY, record_fixtures  # noqa: E402


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--query", default=FIXTURE_QUERY)
    p.add_argument("--force", action="store_true", help="wipe the fixture cache first")
    p.add_argument("--hydrate-top", type=int, default=2)
    args = p.parse_args(argv)
    meta = record_fixtures(args.query, force=args.force, hydrate_top=args.hydrate_top)
    print(json.dumps({k: meta[k] for k in ("query", "n_entries", "degraded", "summary")}, indent=2))
    return 0 if not meta["validation_errors"] and meta["n_entries"] > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
