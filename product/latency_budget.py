"""Record p50/p95 query-map latency against the QUERY_MAP_MVP 9A budgets.

Why this exists
---------------
Direction v51 names this as the second owner-independent delta: *"record p50/p95
latency against QUERY_MAP_MVP 9A budgets with upstream and local time
separated"*. It had been listed as a known limitation by the v50 audit
("Latency budgets from QUERY_MAP_MVP 9A not yet measured on live retrieval
path").

The separation is the whole point. A latency number that mixes public
OpenCaseLaw response time with local geometry time is un-actionable: it either
blames local code for infrastructure time or hides a real regression behind a
slow upstream. Every sample therefore carries, separately:

* ``upstream_retrieval_s``  — OpenCaseLaw network + adapter (never local work),
* ``local_map_s``           — dedupe, query-conditioned TF-IDF/SVD/KMeans
  geometry and bundle assembly (the part we own),
* ``map_total_s``           — the user-visible time to first map,
* ``enrich_total_s``        — answer + counter-authority pass, reported but
  **not** budgeted, because 9A requires the first map not to wait for it.

Estimator
---------
p50/p95 use the nearest-rank method on the sorted sample
(``ceil(q*n)``-th value, 1-indexed): no interpolation, so every reported
percentile is a measurement that actually happened. With small samples the
percentile is coarse by construction, so ``n`` is reported next to every
percentile and a warning is emitted below ``MIN_SAMPLES_FOR_P95``.

Usage
-----
    python product/latency_budget.py --repeat 5 --mode fixture        # offline, deterministic
    python product/latency_budget.py --repeat 3 --mode live \
        --query "Kündigung Mietvertrag Mietrecht"                     # live OpenCaseLaw
    python product/latency_budget.py --from-samples samples.json --out report.json

Exit codes: 0 all budgeted metrics within budget, 3 at least one budget missed,
4 invalid input.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Sequence

PRODUCT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PRODUCT_ROOT.parent
if str(PRODUCT_ROOT) not in sys.path:
    sys.path.insert(0, str(PRODUCT_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_OUT_DIR = REPO_ROOT / "results" / "product" / "latency_budget"
DEFAULT_QUERY = "Kündigung Mietvertrag Mietrecht"

#: Engineering budgets from QUERY_MAP_MVP 9A and the product lane runtime
#: performance mandate. ``None`` = measured and reported, but not budgeted,
#: with the reason recorded next to it.
BUDGETS: dict[str, dict[str, Any]] = {
    "cached_map_total_s": {
        "limit": 1.0,
        "source": "QUERY_MAP_MVP 9A / lane runtime mandate: 'cached map <1s'",
    },
    "local_map_s": {
        "limit": 1.5,
        "source": "lane runtime mandate: after the first upstream search page arrives, "
        "local map overhead <1.5s",
    },
    "upstream_retrieval_s": {
        "limit": None,
        "source": "QUERY_MAP_MVP 9A / lane runtime mandate: 'Measure upstream OpenCaseLaw "
        "latency separately rather than blaming local code'. Public infrastructure; explicitly "
        "NOT a local performance budget",
    },
    "enrich_total_s": {
        "limit": None,
        "source": "QUERY_MAP_MVP 9A: the initial map MUST NOT wait for generation or the "
        "adversarial pass; reported for cost accounting only, never budgeted",
    },
    "detail_click_local_ms": {
        "limit": 150.0,
        "source": "lane runtime mandate: detail click <150ms where data is local",
    },
}

METRICS: tuple[str, ...] = (
    "upstream_retrieval_s",
    "local_map_s",
    "map_total_s",
    "enrich_total_s",
    "detail_click_local_ms",
)

MIN_SAMPLES_FOR_P95 = 5
DEFAULT_REPEATS = 5


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def quantile(values: Sequence[float], q: float) -> float | None:
    """Nearest-rank percentile: the ceil(q*n)-th smallest value, no interpolation."""
    data = sorted(float(v) for v in values if v is not None)
    if not data:
        return None
    if q <= 0:
        return data[0]
    rank = max(1, min(len(data), math.ceil(q * len(data))))
    return data[rank - 1]


def aggregate(samples: Iterable[dict], metric: str) -> dict:
    """p50/p95/min/max/mean for one metric, with the sample count kept visible."""
    values = [float(s[metric]) for s in samples if s.get(metric) is not None]
    if not values:
        return {"n": 0}
    return {
        "n": len(values),
        "p50": round(quantile(values, 0.50), 4),
        "p95": round(quantile(values, 0.95), 4),
        "min": round(min(values), 4),
        "max": round(max(values), 4),
        "mean": round(sum(values) / len(values), 4),
        "estimator": "nearest-rank (ceil(q*n)), no interpolation",
    }


def evaluate(agg: dict, metric: str) -> dict:
    """Verdict for one metric against its 9A budget (or an explicit non-budget)."""
    budget = BUDGETS.get(metric, {"limit": None, "source": "unknown metric"})
    limit = budget["limit"]
    stats = agg.get(metric, {})
    if limit is None:
        return {
            "metric": metric,
            "budget_s": None,
            "budgeted": False,
            "source": budget["source"],
            "p50": stats.get("p50"),
            "p95": stats.get("p95"),
            "verdict": "not_budgeted",
        }
    p95 = stats.get("p95")
    p50 = stats.get("p50")
    verdict = "PASS" if p95 is not None and p95 <= limit else "MISS"
    return {
        "metric": metric,
        "budget_s": limit,
        "budgeted": True,
        "source": budget["source"],
        "p50": p50,
        "p95": p95,
        "n": stats.get("n"),
        "verdict": verdict,
        "headroom_p95_s": round(limit - p95, 4) if p95 is not None else None,
    }


def measure_detail_click_ms(bundle: dict, repeats: int = 5) -> float | None:
    """Median wall-clock of a detail click against an already-loaded bundle.

    "Where data is local" in the 9A/lane budget means exactly this: the decision
    record already travels with the bundle, so the click is a lookup plus a
    render payload, not a network round trip.
    """
    decisions = bundle.get("decisions") or []
    if not decisions:
        return None
    index = {str(d.get("decision_id")): d for d in decisions if isinstance(d, dict)}
    ids = [str(d.get("decision_id")) for d in decisions[: min(20, len(decisions))] if d.get("decision_id")]
    samples: list[float] = []
    for decision_id in ids:
        best = None
        for _ in range(max(1, repeats)):
            start = time.perf_counter()
            record = index.get(decision_id)
            payload = dict(record) if record else None
            best = (time.perf_counter() - start) * 1000.0 if best is None else min(best, (time.perf_counter() - start) * 1000.0)
        samples.append(best or 0.0)
    return round(quantile(samples, 0.50), 4) if samples else None


def measure(
    query: str = DEFAULT_QUERY,
    *,
    mode: str = "fixture",
    repeats: int = DEFAULT_REPEATS,
    top_n: int = 150,
    include_enrich: bool = False,
    fixture_generation: bool = False,
) -> list[dict]:
    """Collect ``repeats`` samples, each separating upstream from local time.

    The first sample is reported separately as ``cold``: it pays the OpenCaseLaw
    network cost, later samples reuse the product's persistent query cache and
    therefore measure the *cached map* budget.
    """
    from query.pipeline import enrich_query_bundle, run_query_initial  # local import: heavy deps

    samples: list[dict] = []
    for index in range(max(1, int(repeats))):
        started = time.perf_counter()
        bundle = run_query_initial(query, top_n=top_n, retrieval_mode=mode)
        wall = time.perf_counter() - started
        timing = dict(bundle.get("provenance", {}).get("timing") or {})
        upstream = float(timing.get("upstream_retrieval_s") or 0.0)
        local_map = float(timing.get("local_map_s") or 0.0)
        sample: dict[str, Any] = {
            "index": index,
            "cache_state": "cold" if index == 0 else "warm",
            "mode": mode,
            "query": bundle.get("query"),
            "n_decisions": timing.get("n_decisions") or len(bundle.get("decisions") or []),
            "n_clusters": timing.get("n_clusters") or len(bundle.get("clusters") or []),
            "upstream_retrieval_s": round(upstream, 4),
            "local_map_s": round(local_map, 4),
            "map_total_s": round(wall, 4),
            "detail_click_local_ms": measure_detail_click_ms(bundle),
        }
        if include_enrich:
            t_enrich = time.perf_counter()
            enriched = enrich_query_bundle(
                bundle,
                retrieval_mode=mode,
                fixture_generation=fixture_generation or mode == "fixture",
            )
            enrich_timing = dict(enriched.get("provenance", {}).get("timing") or {})
            sample["enrich_total_s"] = round(time.perf_counter() - t_enrich, 4)
            sample["enrich_model_s"] = enrich_timing.get("enrich_model_s")
            sample["enrich_non_model_s"] = enrich_timing.get("enrich_non_model_s")
            sample["answer_method"] = (enriched.get("answer") or {}).get("method")
        samples.append(sample)
    return samples


def build_report(samples: Sequence[dict], *, run_id: str | None = None, note: str | None = None) -> dict:
    """Aggregate + budget verdict. ``cached_map_total_s`` uses warm samples only."""
    warm = [s for s in samples if s.get("cache_state") == "warm"] or list(samples)
    cold = [s for s in samples if s.get("cache_state") == "cold"]
    all_stats = {metric: aggregate(samples, metric) for metric in METRICS}
    warm_stats = {metric: aggregate(warm, metric) for metric in METRICS}
    verdicts = {metric: evaluate(warm_stats, metric) for metric in METRICS}
    verdicts["cached_map_total_s"] = evaluate({**warm_stats, "cached_map_total_s": warm_stats["map_total_s"]}, "cached_map_total_s")
    budgeted = [v for v in verdicts.values() if v.get("budgeted")]
    warnings: list[str] = []
    if len(warm) < MIN_SAMPLES_FOR_P95:
        warnings.append(
            f"only {len(warm)} warm sample(s): p95 from fewer than {MIN_SAMPLES_FOR_P95} samples is coarse"
        )
    if not cold:
        warnings.append("no cold sample recorded: the upstream cost of a first-time query is unmeasured")
    return {
        "record_type": "lex_query_map_latency_budget",
        "generated_at": _utc_now(),
        "run_id": run_id,
        "note": note,
        "budget_source": "docs/product/QUERY_MAP_MVP.md 9A + product lane runtime performance mandate",
        "separation_rule": "upstream_retrieval_s is OpenCaseLaw network+adapter time and is never "
        "attributed to local code; local_map_s is the product-owned remainder of the map phase",
        "queries": sorted({str(s.get("query")) for s in samples if s.get("query")}),
        "n_samples": len(samples),
        "n_warm_samples": len(warm),
        "n_cold_samples": len(cold),
        "all_samples": all_stats,
        "warm_samples": warm_stats,
        "verdicts": verdicts,
        "warnings": warnings,
        "within_budget": all(v["verdict"] == "PASS" for v in budgeted),
        "samples": list(samples),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--mode", choices=["fixture", "live", "offline", "refresh"], default="fixture")
    parser.add_argument("--repeat", type=int, default=DEFAULT_REPEATS)
    parser.add_argument("--top-n", type=int, default=150)
    parser.add_argument("--with-enrich", action="store_true", help="also time the answer/counter pass")
    parser.add_argument("--from-samples", type=Path, default=None, help="re-aggregate recorded samples (offline)")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.from_samples:
        payload = json.loads(args.from_samples.read_text(encoding="utf-8"))
        samples = payload.get("samples", payload) if isinstance(payload, dict) else payload
        if not isinstance(samples, list):
            print("::error::--from-samples must contain a list of samples", file=sys.stderr)
            return 4
    else:
        if args.repeat < 1:
            print("::error::--repeat must be >= 1", file=sys.stderr)
            return 4
        samples = measure(
            args.query,
            mode=args.mode,
            repeats=args.repeat,
            top_n=args.top_n,
            include_enrich=args.with_enrich,
        )

    report = build_report(samples, run_id=args.run_id)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {args.out}")

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print(f"samples: {report['n_samples']} ({report['n_warm_samples']} warm / {report['n_cold_samples']} cold)")
        for metric, verdict in sorted(report["verdicts"].items()):
            if verdict.get("budgeted"):
                unit = "ms" if metric.endswith("_ms") else "s"
                print(
                    f"  [{verdict['verdict']}] {metric}: p50={verdict['p50']}{unit} "
                    f"p95={verdict['p95']}{unit} budget={verdict['budget_s']}{unit} (n={verdict.get('n')})"
                )
            else:
                unit = "ms" if metric.endswith("_ms") else "s"
                print(
                    f"  [not budgeted] {metric}: p50={verdict.get('p50')}{unit} "
                    f"p95={verdict.get('p95')}{unit}"
                )
        print("  upstream is reported separately and is not a local budget:")
        print(
            f"    upstream_retrieval_s p50={report['warm_samples']['upstream_retrieval_s'].get('p50')} "
            f"p95={report['warm_samples']['upstream_retrieval_s'].get('p95')} | "
            f"local_map_s p50={report['warm_samples']['local_map_s'].get('p50')} "
            f"p95={report['warm_samples']['local_map_s'].get('p95')}"
        )
        for warning in report["warnings"]:
            print(f"  ::warning::{warning}")
    return 0 if report["within_budget"] else 3


if __name__ == "__main__":  # pragma: no cover - CLI
    sys.exit(main())