"""CLI for the independent v45 query-map evaluator."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .harness import evaluate_query_map_bundle


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--initial", required=True)
    ap.add_argument("--final", required=True)
    ap.add_argument("--expectations", help="JSON with known_relevant_ids / known_counter_ids")
    ap.add_argument("--out")
    args = ap.parse_args(argv)

    exp = _load(args.expectations) if args.expectations else {}
    report = evaluate_query_map_bundle(
        _load(args.initial),
        _load(args.final),
        known_relevant_ids=exp.get("known_relevant_ids"),
        known_counter_ids=exp.get("known_counter_ids"),
    )
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
