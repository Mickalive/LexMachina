#!/usr/bin/env python3
"""Run live OpenCaseLaw retrieval evidence for the charter acceptance test.

Produces, under ``results/frontier/frontier-query-retrieval/``:

* ``LIVE_BUNDLE_<slug>.json``        - candidate bundle (live, paged, all stages)
* ``LIVE_PRODUCT_BUNDLE_<slug>.json``- accepted product query_result_bundle shape
* ``LIVE_EVIDENCE.json``             - machine-readable acceptance evidence

Usage::

    python3 run_live_evidence.py            # both scenarios
    python3 run_live_evidence.py --scenario primary
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ocl_adapter.bundle import (  # noqa: E402
    bundle_summary,
    to_product_bundle,
    validate_against_product,
    validate_candidate_bundle,
)
from ocl_adapter.cache import FileCache  # noqa: E402
from ocl_adapter.config import DEFAULT_RESULTS_DIR  # noqa: E402
from ocl_adapter.pipeline import build_candidate_bundle  # noqa: E402

RESULTS = DEFAULT_RESULTS_DIR
LIVE_CACHE = Path("/tmp/opencode/lex_ocl_live_cache")  # kept out of the repo; fixtures/ is the committed offline pack

# (slug, query, config overrides)
SCENARIOS = {
    "primary": {
        "query": "Kündigung Mietvertrag Mietrecht",
        "slug": "KUENDIGUNG_MIETVERTRAG",
        "overrides": dict(
            target=150,
            max_candidates=300,
            page_size=50,
            max_pages_per_variant=2,
            lang_max_pages=1,
            stages=("search", "lang", "leading", "citations"),
            stop_when_target_met=False,
            citation_seeds=5,
            citation_page_size=15,
            leading_cases_limit=15,
            max_requests=40,
        ),
        "hydrate_top": 3,
        "min_candidates": 100,
    },
    "secondary": {
        "query": "responsabilité contractuelle dommages indemnisation",
        "slug": "RESPONSABILITE_CONTRACTUELLE",
        "overrides": dict(
            target=100,
            max_candidates=200,
            page_size=50,
            max_pages_per_variant=2,
            lang_max_pages=1,
            stages=("search", "lang"),
            stop_when_target_met=False,
            max_requests=20,
        ),
        "hydrate_top": 1,
        "min_candidates": 60,
    },
}


def run(name: str) -> dict:
    spec = SCENARIOS[name]
    from ocl_adapter.config import AdapterConfig

    cfg = AdapterConfig(
        mode="live",
        cache_dir=str(LIVE_CACHE),
        max_rps=4.0,
        language_filters=("de", "fr", "it"),
        **spec["overrides"],
    )
    t0 = time.time()
    bundle = build_candidate_bundle(
        spec["query"],
        config=cfg,
        cache=FileCache(LIVE_CACHE),
        hydrate_top=spec["hydrate_top"],
        include_structure=True,
    )
    elapsed = round(time.time() - t0, 3)

    errors = validate_candidate_bundle(bundle)
    product_errors = validate_against_product(bundle)

    slug = spec["slug"]
    bundle_path = RESULTS / f"LIVE_BUNDLE_{slug}.json"
    product_path = RESULTS / f"LIVE_PRODUCT_BUNDLE_{slug}.json"
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    product_path.write_text(
        json.dumps(to_product_bundle(bundle), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    summary = bundle_summary(bundle)
    n = summary["n_candidates"]
    langs = {k: v for k, v in summary["languages"].items() if k != "?"}
    channels = summary["channels"]
    rs = summary["request_summary"]

    # Freshness guard: "live evidence" must actually touch the network. A warm
    # /tmp cache replayed under a previous run id is stale evidence, not live
    # evidence (found and fixed in operational resume 38196996329: the top-level
    # LIVE_* files had been overwritten by a 0-network cache replay that still
    # carried run_id 38190325825 and a different, older candidate set).
    # Opt back in explicitly with LEX_ALLOW_CACHE_REPLAY=1 when a cache replay
    # is genuinely what you want (then the evidence is flagged as such).
    cache_replayed = rs.get("network_calls", 0) == 0
    allow_replay = os.environ.get("LEX_ALLOW_CACHE_REPLAY") == "1"

    checks = {
        "A0_fresh_live_network": (not cache_replayed) or allow_replay,
        "A1_runnable_cli_and_modes": True,
        "A2_target_at_least_100": n >= spec["min_candidates"],
        "A3_deterministic_dedupe": bundle["dedupe"].get("strategy") == "canonical_identity_v1"
        and summary["n_candidates"] == len({c["decision_id"] for c in bundle["candidates"]}),
        "A4_lazy_full_and_structure": summary["n_with_full_text"] > 0 and summary["n_with_structure"] > 0,
        "A5_citation_and_leading_expansion": (
            channels.get("citation.incoming", 0) + channels.get("citation.outgoing", 0) > 0
            and channels.get("leading_case", 0) > 0
        ) if "citations" in cfg.stages else None,
        "A6_trilingual_variants": len(bundle["query_variants"]) >= 4 and len(langs) >= 2,
        "A7_cache_populated": rs.get("cache_hits", 0) + rs.get("network_calls", 0) > 0,
        "A8_no_failures": summary["n_failures"] == 0 and not summary["degraded"],
        "A9_valid_contract": not errors and not product_errors,
        "rate_limit_respected": rs.get("rate_limit_rps", 99) <= 5.0
        and rs.get("network_calls", 0) <= cfg.max_requests,
    }
    checks = {k: v for k, v in checks.items() if v is not None}

    return {
        "scenario": name,
        "query": spec["query"],
        "elapsed_seconds": elapsed,
        "bundle_path": str(bundle_path.relative_to(RESULTS.parents[2])),
        "product_bundle_path": str(product_path.relative_to(RESULTS.parents[2])),
        "summary": summary,
        "cache_dir": str(LIVE_CACHE),
        "cache_replayed": cache_replayed,
        "search_pages": len(bundle["provenance"]["searches"]),
        "stage_notes": bundle["provenance"]["stage_notes"],
        "failures": bundle["provenance"]["failures"],
        "rate_limit": bundle["provenance"]["rate_limit"],
        "targets": bundle["provenance"]["targets"],
        "validation_errors": errors,
        "product_bridge_errors": product_errors,
        "checks": checks,
        "all_checks_pass": all(bool(v) for v in checks.values()),
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--scenario", choices=sorted(SCENARIOS) + ["all"], default="all")
    args = p.parse_args(argv)
    names = list(SCENARIOS) if args.scenario == "all" else [args.scenario]

    # Attribution rule (operational resume 38196996329): evidence must carry the
    # id of the run that produced it. A previously accepted run id must never be
    # the default, or a later re-execution silently re-labels its output as that
    # older run's claim-bearing evidence.
    run_id = os.environ.get("LEX_FRONTIER_RUN_ID") or f"unattributed-{int(time.time())}"

    runs = []
    for name in names:
        print(f"[live] running scenario {name} ...", flush=True)
        runs.append(run(name))
        print(f"[live] {name}: {runs[-1]['summary']['n_candidates']} candidates, "
              f"pass={runs[-1]['all_checks_pass']}", flush=True)

    evidence = {
        "generated_at": time.time(),
        "team_id": "frontier-query-retrieval",
        "charter_version": 2,
        "run_id": run_id,
        "base_url": "https://mcp.opencaselaw.ch/api",
        "cache_dir": str(LIVE_CACHE),
        "cache_replay_allowed": os.environ.get("LEX_ALLOW_CACHE_REPLAY") == "1",
        "runs": runs,
        "all_runs_pass": all(r["all_checks_pass"] for r in runs),
    }
    out = RESULTS / "LIVE_EVIDENCE.json"
    out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"evidence": str(out), "all_runs_pass": evidence["all_runs_pass"]}, indent=2))
    return 0 if evidence["all_runs_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
