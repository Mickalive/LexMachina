#!/usr/bin/env python3
"""Determinism probe for the OpenCaseLaw retrieval adapter (charter v2).

Answers one question with a discriminating test rather than a narrative:

    Given byte-identical HTTP responses, does the adapter produce a
    byte-identical candidate set (ids, ordering, provenance strings)?

Two independent probes:

1. ``warm_cache`` - run the primary live scenario twice against the SAME
   cache directory (first run may hit the network, second run is a pure
   warm-cache replay). Identical candidate content across the two runs proves
   the pipeline is deterministic given identical responses. This is the exact
   regression that stale /tmp caches can otherwise hide: an old cache replayed
   under a new run id looks like "live" evidence but carries different API
   responses from a different day.
2. ``fixture_subprocess`` - two separate ``python -m ocl_adapter --preset
   fixtures`` processes (different interpreter instances => different
   ``PYTHONHASHSEED``) must produce identical candidate content. This proves
   cross-process determinism, i.e. no set-iteration or hash-order dependence.

Scope safety: writes only to ``results/frontier/frontier-query-retrieval/
verification/<stamp>/`` (or an explicit ``--out``); never writes at the
repository root; never touches claim-bearing LIVE_*.json or fixtures/.

Usage (run from the repository root)::

    python3 frontier/frontier-query-retrieval/verify_determinism.py \\
        --out results/frontier/frontier-query-retrieval/verification/<run>/determinism.json

``--out`` is resolved relative to the *current working directory*, not to this
script, so pass a path relative to wherever you are running from (or an
absolute path). In-team only: the target must stay under
``results/frontier/frontier-query-retrieval/``.

Exit codes: 0 deterministic, 1 non-deterministic, 2 usage/config error.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ocl_adapter.cache import FileCache  # noqa: E402
from ocl_adapter.config import AdapterConfig  # noqa: E402
from ocl_adapter.pipeline import build_candidate_bundle  # noqa: E402

PRIMARY_QUERY = "Kündigung Mietvertrag Mietrecht"
PRIMARY_OVERRIDES = dict(
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
)


def content_signature(bundle: dict) -> dict:
    """Candidate content only: excludes run metadata (generated_at, latency)."""
    return {
        "decision_ids": [c["decision_id"] for c in bundle["candidates"]],
        "provenance_strings": [c["provenance"] for c in bundle["candidates"]],
        "scores": [c.get("score") for c in bundle["candidates"]],
        "ranks": [c.get("rank") for c in bundle["candidates"]],
        "channels": sorted({ch for c in bundle["candidates"] for ch in c.get("channels", [])}),
        "n_candidates": bundle["n_candidates"],
        "dedupe": bundle["dedupe"],
        "query_variants": bundle["query_variants"],
        "n_failures": bundle["provenance"].get("request_summary", {}).get("failures"),
    }


def _run_primary(cache_dir: Path, mode: str) -> dict:
    cfg = AdapterConfig(mode=mode, cache_dir=str(cache_dir), max_rps=4.0,
                        language_filters=("de", "fr", "it"), **PRIMARY_OVERRIDES)
    t0 = time.time()
    bundle = build_candidate_bundle(PRIMARY_QUERY, config=cfg, cache=FileCache(cache_dir),
                                    hydrate_top=0, include_structure=True)
    return {
        "bundle": bundle,
        "elapsed_seconds": round(time.time() - t0, 3),
        "request_summary": bundle["provenance"].get("request_summary", {}),
    }


def probe_warm_cache(cache_dir: Path) -> dict:
    """Two identical live-mode runs against the same cache directory."""
    runs = []
    for i in (1, 2):
        res = _run_primary(cache_dir, "live")
        rs = res["request_summary"]
        runs.append({
            "pass": i,
            "elapsed_seconds": res["elapsed_seconds"],
            "network_calls": rs.get("network_calls"),
            "cache_hits": rs.get("cache_hits"),
            "signature": content_signature(res["bundle"]),
        })
    a, b = runs[0]["signature"], runs[1]["signature"]
    identical = a == b
    diffs = {}
    if not identical:
        for key in a:
            if a[key] != b[key]:
                av, bv = a[key], b[key]
                if isinstance(av, list) and isinstance(bv, list):
                    diffs[key] = {
                        "len": [len(av), len(bv)],
                        "first_divergence": next(
                            (i for i, (x, y) in enumerate(zip(av, bv)) if x != y), None),
                        "sample_a": av[:3], "sample_b": bv[:3],
                    }
                else:
                    diffs[key] = {"a": av, "b": bv}
    return {
        "probe": "warm_cache_same_responses",
        "cache_dir": str(cache_dir),
        "run1_network_calls": runs[0]["network_calls"],
        "run2_network_calls": runs[1]["network_calls"],
        "run2_is_pure_cache_replay": runs[1]["network_calls"] == 0 and runs[1]["cache_hits"] > 0,
        "identical_candidate_content": identical,
        "differences": diffs,
        "n_candidates": [a["n_candidates"], b["n_candidates"]],
        "runs": runs,
    }


def probe_fixture_subprocess(out_dir: Path) -> dict:
    """Two separate interpreter processes replaying the committed fixtures."""
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    rcs, sigs = [], []
    for i in (1, 2):
        # Resolve to an absolute path: the subprocess runs with a different
        # cwd (this package dir), so a relative --out would be written
        # somewhere unexpected and the probe would see no file (false
        # non-determinism verdict; found in run 38200364291).
        out = (out_dir / f"fixture_replay_{i}.json").resolve()
        p = subprocess.run(
            [sys.executable, "-B", "-m", "ocl_adapter", PRIMARY_QUERY,
             "--preset", "fixtures", "--out", str(out), "--validate", "--quiet"],
            capture_output=True, text=True, env=env, timeout=300,
            cwd=str(Path(__file__).resolve().parent),
        )
        rcs.append(p.returncode)
        if out.exists():
            sigs.append(content_signature(json.loads(out.read_text(encoding="utf-8"))))
    identical = len(sigs) == 2 and sigs[0] == sigs[1]
    return {
        "probe": "fixture_subprocess_cross_process",
        "returncodes": rcs,
        "identical_candidate_content": identical,
        "n_candidates": [s["n_candidates"] for s in sigs] if sigs else None,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cache-dir", default="/tmp/opencode/lex_ocl_live_cache",
                   help="cache directory shared by both warm-cache passes "
                        "(must already be populated for a pure-replay second pass)")
    p.add_argument("--out", default=None, help="write the JSON report here")
    p.add_argument("--skip-warm-cache", action="store_true",
                   help="only run the offline fixture subprocess probe")
    p.add_argument("--skip-fixtures", action="store_true",
                   help="only run the warm-cache probe")
    args = p.parse_args(argv)

    report = {
        "schema": "ocl_adapter_determinism_probe_v1",
        "team_id": "frontier-query-retrieval",
        "charter_version": 2,
        "run_id": os.environ.get("LEX_FRONTIER_RUN_ID", "unattributed"),
        "generated_at": time.time(),
        "probes": {},
    }

    if not args.skip_fixtures:
        if args.out:
            fixture_out_dir = Path(args.out).parent
        else:
            # Never write into the checkout or the repository root: fall back
            # to the system temp dir (scope-safe from any working directory).
            import tempfile

            fixture_out_dir = Path(tempfile.mkdtemp(prefix="ocl_determinism_"))
        report["probes"]["fixture_subprocess"] = probe_fixture_subprocess(fixture_out_dir)
    if not args.skip_warm_cache:
        cache_dir = Path(args.cache_dir)
        if not cache_dir.is_dir():
            print(f"error: cache dir {cache_dir} does not exist; run live evidence first "
                  f"or pass --skip-warm-cache", file=sys.stderr)
            return 2
        report["probes"]["warm_cache"] = probe_warm_cache(cache_dir)

    deterministic = all(p.get("identical_candidate_content") for p in report["probes"].values())
    report["deterministic"] = deterministic

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print(json.dumps({"out": str(out), "deterministic": deterministic,
                          "probes": {k: v.get("identical_candidate_content")
                                     for k, v in report["probes"].items()}}, indent=2))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0 if deterministic else 1


if __name__ == "__main__":
    raise SystemExit(main())
