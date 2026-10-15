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

* ``upstream_retrieval_s``  — OpenCaseLaw **network** + adapter time. Recorded
  **only** for samples that were actually served by the network
  (``served_from == "network"``). A file-cache read, an offline replay or a
  fixture is not OpenCaseLaw latency, so those samples carry ``None`` here and
  keep the raw pipeline number in ``retrieval_s`` instead;
* ``retrieval_s``           — the raw ``provenance.timing.upstream_retrieval_s``
  of whatever the adapter returned, whatever served it (never called upstream);
* ``local_map_s``           — dedupe, query-conditioned TF-IDF/SVD/KMeans
  geometry and bundle assembly (the part we own);
* ``map_total_s``           — the user-visible time to first map;
* ``enrich_total_s``        — answer + counter-authority pass, reported but
  **not** budgeted, because 9A requires the first map not to wait for it.

Served-from provenance (repair of cycle 38649613677)
----------------------------------------------------
Cycle 38649613677 published an upstream p50/p95 of 0.275 s / 0.303 s that was
really a local file-cache read: every one of its five samples ran with zero
network calls, but ``cache_state`` was derived from the sample *index*
(``"cold" if index == 0``) and the field was named ``upstream_retrieval_s``.
That is a mislabelled claim, not a measurement, so this module now:

* derives ``cache_state``/``served_from`` from **observed** evidence in the
  bundle provenance (``fixture_mode``, ``request_summary.network_calls`` /
  ``cache_hits``, ``cache_stats``) instead of from the sample index;
* refuses to put a non-network time in ``upstream_retrieval_s``;
* aggregates upstream over network samples only and declares the value
  ``measured: false`` with an explicit warning when a run contains none, so
  "unmeasured" can never be printed as a small fast number;
* keeps ``cache_hits``/``network_calls``/``cache_stats`` on every sample so an
  auditor can recompute the classification from the artifact alone.

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
    python product/latency_budget.py --repeat 6 --mode offline \
        --refresh-first 3 --out results/product/latency_budget/run.json  # live: 3 network + 3 cache
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
    "retrieval_s",
    "local_map_s",
    "map_total_s",
    "enrich_total_s",
    "detail_click_local_ms",
)

#: Observed data sources a sample can have been served from. ``unknown`` is a
#: first-class value: a sample whose bundle carries no per-request evidence is
#: NOT allowed to masquerade as a network measurement.
SERVED_FROM_VALUES: tuple[str, ...] = ("network", "cache", "mixed", "fixture", "unknown")

#: Observed served_from -> budget cache_state.
CACHE_STATE_BY_SERVED_FROM: dict[str, str] = {
    "network": "cold",
    "mixed": "mixed",
    "cache": "warm",
    "fixture": "fixture",
    "unknown": "unknown",
}

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


def aggregate(samples: Iterable[dict], metric: str, predicate: Any = None) -> dict:
    """p50/p95/min/max/mean for one metric, with the sample count kept visible.

    ``predicate`` restricts the sample set before aggregating, which is how the
    upstream metric is kept admissible: only network-served samples are allowed
    to contribute an ``upstream_retrieval_s`` value, whatever a sample file says.
    """
    pool = list(samples)
    if predicate is not None:
        pool = [s for s in pool if predicate(s)]
    values = [float(s[metric]) for s in pool if s.get(metric) is not None]
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


#: Metrics that may only be aggregated over samples that were actually served by
#: the OpenCaseLaw network. Everything else (local geometry, wall clock, cache
#: read time) is product- or cache-owned and aggregates over every sample.
UPSTREAM_ONLY_METRICS = frozenset({"upstream_retrieval_s"})


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


def classify_served_from(bundle: dict) -> tuple[str, dict[str, Any]]:
    """Classify a bundle's data source from OBSERVED provenance evidence.

    Returns ``(served_from, evidence)`` with ``served_from`` in
    :data:`SERVED_FROM_VALUES`. The evidence dict is copied into every sample so
    an auditor can recompute the classification from the artifact alone.

    The classification is deliberately evidence-based and never index-based: the
    rejected cycle 38649613677 labelled sample 0 ``cold`` — and therefore
    "OpenCaseLaw" — while all five of its samples were local file-cache reads.

    ``unknown`` is a first-class value: a bundle without per-request evidence
    cannot support an upstream-latency claim, and saying so is the honest
    answer.
    """
    provenance = bundle.get("provenance") or {}
    timing = provenance.get("timing") or {}
    request_summary = provenance.get("request_summary") or {}
    cache_stats = provenance.get("cache_stats") or {}
    network_calls = int(request_summary.get("network_calls") or 0)
    cache_hits = int(request_summary.get("cache_hits") or 0)
    evidence: dict[str, Any] = {
        "request_summary": {
            "requests_logged": int(request_summary.get("requests_logged") or 0),
            "network_calls": network_calls,
            "cache_hits": cache_hits,
            "failures": request_summary.get("failures"),
        },
        "cache_stats": {
            "hits": cache_stats.get("hits"),
            "misses": cache_stats.get("misses"),
            "writes": cache_stats.get("writes"),
            "n_keys": cache_stats.get("n_keys"),
        },
        "fixture_mode": bool(provenance.get("fixture_mode") or timing.get("fixture_mode")),
        "retrieval_mode": timing.get("mode") or provenance.get("mode"),
    }
    if evidence["fixture_mode"]:
        evidence["basis"] = "provenance.fixture_mode"
        return "fixture", evidence
    if not request_summary:
        evidence["basis"] = "no_request_summary"
        return "unknown", evidence
    evidence["basis"] = "provenance.request_summary"
    if network_calls > 0 and cache_hits > 0:
        return "mixed", evidence
    if network_calls > 0:
        return "network", evidence
    if cache_hits > 0:
        return "cache", evidence
    evidence["basis"] = "request_summary_without_network_or_cache_activity"
    return "unknown", evidence


def derive_cache_state(bundle: dict) -> tuple[str, str, dict[str, Any]]:
    """``(served_from, cache_state, evidence)`` derived from observed provenance.

    ``cache_state`` is a consequence of what was observed, never of the
    position of the sample inside the run.
    """
    served_from, evidence = classify_served_from(bundle)
    return served_from, CACHE_STATE_BY_SERVED_FROM[served_from], evidence


def sample_served_from(sample: dict) -> str:
    """Served-from of a recorded sample, with a legacy ``cache_state`` fallback."""
    explicit = str(sample.get("served_from") or "")
    if explicit in SERVED_FROM_VALUES:
        return explicit
    legacy = {"cold": "network", "warm": "cache", "fixture": "fixture"}.get(
        str(sample.get("cache_state") or "")
    )
    return legacy or "unknown"


def upstream_admissible(sample: dict) -> bool:
    """True only for a sample genuinely served by the OpenCaseLaw network.

    Cache reads, offline replays, fixture replays and samples without observed
    evidence are all inadmissible as an upstream-latency measurement.
    """
    return sample_served_from(sample) == "network"


def measure(
    query: str = DEFAULT_QUERY,
    *,
    mode: str = "fixture",
    repeats: int = DEFAULT_REPEATS,
    top_n: int = 150,
    include_enrich: bool = False,
    fixture_generation: bool = False,
    refresh_first: int = 0,
) -> list[dict]:
    """Collect ``repeats`` samples, each separating upstream from local time.

    ``refresh_first`` leading samples are recorded with ``retrieval_mode
    "refresh"`` (network only, file-cache reads bypassed) so the artifact
    contains genuine OpenCaseLaw measurements; the remaining samples use
    ``mode``. Mixing both in one artifact is what allows the upstream network
    latency and the warm cached-map budget to be measured without either number
    being attributed to the wrong subsystem.

    ``cache_state``/``served_from`` are derived from observed provenance (see
    :func:`derive_cache_state`), so a run whose first sample is a cache hit
    reports ``warm`` and never publishes a file-cache read as upstream time.
    """
    from query.pipeline import enrich_query_bundle, run_query_initial  # local import: heavy deps

    repeats = max(1, int(repeats))
    refresh_first = max(0, min(int(refresh_first), repeats))
    samples: list[dict] = []
    for index in range(repeats):
        sample_mode = "refresh" if index < refresh_first else mode
        started = time.perf_counter()
        bundle = run_query_initial(query, top_n=top_n, retrieval_mode=sample_mode)
        wall = time.perf_counter() - started
        timing = dict(bundle.get("provenance", {}).get("timing") or {})
        retrieval_s = float(timing.get("upstream_retrieval_s") or 0.0)
        local_map = float(timing.get("local_map_s") or 0.0)
        served_from, cache_state, evidence = derive_cache_state(bundle)
        sample: dict[str, Any] = {
            "index": index,
            "cache_state": cache_state,
            "served_from": served_from,
            "served_from_basis": evidence.get("basis"),
            "mode": sample_mode,
            "query": bundle.get("query"),
            "n_decisions": timing.get("n_decisions") or len(bundle.get("decisions") or []),
            "n_clusters": timing.get("n_clusters") or len(bundle.get("clusters") or []),
            # Raw retrieval-phase time, whatever served the data.
            "retrieval_s": round(retrieval_s, 4),
            # Upstream OpenCaseLaw latency: only a network-served sample earns it.
            "upstream_retrieval_s": round(retrieval_s, 4) if served_from == "network" else None,
            "local_map_s": round(local_map, 4),
            "map_total_s": round(wall, 4),
            "detail_click_local_ms": measure_detail_click_ms(bundle),
            "request_summary": evidence["request_summary"],
            "cache_stats": evidence["cache_stats"],
        }
        if served_from == "fixture":
            sample["note"] = "fixture replay: not a network measurement"

        if include_enrich:
            t_enrich = time.perf_counter()
            enriched = enrich_query_bundle(
                bundle,
                retrieval_mode=sample_mode,
                fixture_generation=fixture_generation or sample_mode == "fixture",
            )
            enrich_timing = dict(enriched.get("provenance", {}).get("timing") or {})
            sample["enrich_total_s"] = round(time.perf_counter() - t_enrich, 4)
            sample["enrich_model_s"] = enrich_timing.get("enrich_model_s")
            sample["enrich_non_model_s"] = enrich_timing.get("enrich_non_model_s")
            sample["answer_method"] = (enriched.get("answer") or {}).get("method")
        samples.append(sample)
    return samples


def build_report(samples: Sequence[dict], *, run_id: str | None = None, note: str | None = None) -> dict:
    """Aggregate + budget verdict, keeping upstream/local separation honest.

    * ``network``-served samples are the only admissible source of
      ``upstream_retrieval_s`` statistics;
    * the budgeted local metrics (``cached_map_total_s``, ``local_map_s``,
      ``detail_click_local_ms``) are computed over non-network samples;
    * with no network-served sample, upstream is reported ``measured: false``
      with ``None`` percentiles plus a warning, so a cache or fixture read can
      never be published as OpenCaseLaw latency.
    """
    samples = list(samples)
    network = [s for s in samples if sample_served_from(s) == "network"]
    mixed = [s for s in samples if sample_served_from(s) == "mixed"]
    cache = [s for s in samples if sample_served_from(s) == "cache"]
    fixture = [s for s in samples if sample_served_from(s) == "fixture"]
    unknown = [s for s in samples if sample_served_from(s) == "unknown"]
    warm = cache or unknown or list(samples)
    warm_basis = "cache" if cache else ("unknown" if unknown else "all_samples_fallback")

    all_stats = {
        metric: aggregate(samples, metric, predicate=upstream_admissible if metric in UPSTREAM_ONLY_METRICS else None)
        for metric in METRICS
    }
    warm_stats = {
        metric: aggregate(warm, metric, predicate=upstream_admissible if metric in UPSTREAM_ONLY_METRICS else None)
        for metric in METRICS
    }
    upstream_stats = {
        metric: aggregate(network, metric, predicate=upstream_admissible if metric in UPSTREAM_ONLY_METRICS else None)
        for metric in METRICS
    }

    verdicts = {metric: evaluate(warm_stats, metric) for metric in METRICS}
    verdicts["cached_map_total_s"] = evaluate(
        {**warm_stats, "cached_map_total_s": warm_stats["map_total_s"]}, "cached_map_total_s"
    )
    upstream_verdict = evaluate(upstream_stats, "upstream_retrieval_s")
    upstream_measured = bool(upstream_stats["upstream_retrieval_s"].get("n"))
    upstream_verdict.update({
        "measured": upstream_measured,
        "sample_source": "network-served samples only (cache/mixed/fixture/unknown excluded)",
        "n_network_samples": len(network),
        "note": None if upstream_measured else (
            "UNMEASURED: no sample in this run was served by the OpenCaseLaw network, so upstream "
            "latency is not measured here. Cache/fixture read time is not OpenCaseLaw latency and "
            "is never reported as upstream_retrieval_s."
        ),
    })
    verdicts["upstream_retrieval_s"] = upstream_verdict

    budgeted = [v for v in verdicts.values() if v.get("budgeted")]
    warnings: list[str] = []
    if len(warm) < MIN_SAMPLES_FOR_P95:
        warnings.append(
            f"only {len(warm)} non-network sample(s): p95 from fewer than "
            f"{MIN_SAMPLES_FOR_P95} samples is coarse"
        )
    if warm_basis == "unknown":
        warnings.append(
            "cached-map budget computed from samples with NO observed cache/network evidence "
            "(served_from=unknown): these are unproven cache-served times"
        )
    if warm_basis == "all_samples_fallback":
        warnings.append(
            "no cache-served sample: the cached-map budget was computed over all samples, "
            "including any network-served ones"
        )
    if not upstream_measured:
        warnings.append(
            "no network-served sample: OpenCaseLaw upstream p50/p95 is UNMEASURED in this run "
            "(cache/fixture read time is not upstream latency)"
        )
    if not network:
        warnings.append(
            "no cold sample recorded: the upstream cost of a first-time query is unmeasured"
        )
    if mixed:
        warnings.append(
            f"{len(mixed)} mixed sample(s) (cache hits and network calls in one retrieval) are "
            "excluded from the pure-network upstream percentile"
        )
    return {
        "record_type": "lex_query_map_latency_budget",
        "generated_at": _utc_now(),
        "run_id": run_id,
        "note": note,
        "budget_source": "docs/product/QUERY_MAP_MVP.md 9A + product lane runtime performance mandate",
        "separation_rule": (
            "upstream_retrieval_s is recorded only for samples served by the OpenCaseLaw network "
            "(served_from=network) and is never attributed to local code; local_map_s is the "
            "product-owned remainder of the map phase. Cache reads, offline replays and fixtures "
            "keep their raw retrieval-phase time in retrieval_s and are NOT reported as upstream "
            "latency. cache_state/served_from are derived from observed bundle provenance "
            "(provenance.request_summary, provenance.cache_stats, provenance.fixture_mode), never "
            "from the sample index."
        ),
        "served_from_counts": {
            "network": len(network),
            "mixed": len(mixed),
            "cache": len(cache),
            "fixture": len(fixture),
            "unknown": len(unknown),
        },
        "queries": sorted({str(s.get("query")) for s in samples if s.get("query")}),
        "n_samples": len(samples),
        "n_warm_samples": len(warm),
        "n_warm_basis": warm_basis,
        "n_cold_samples": len(network),
        "n_network_samples": len(network),
        "n_mixed_samples": len(mixed),
        "n_fixture_samples": len(fixture),
        "n_unknown_samples": len(unknown),
        "all_samples": all_stats,
        "warm_samples": warm_stats,
        "upstream_samples": upstream_stats,
        "upstream_measured": upstream_measured,
        "verdicts": verdicts,
        "warnings": warnings,
        "within_budget": all(v["verdict"] == "PASS" for v in budgeted),
        "samples": samples,
    }


def annotate_legacy_report(
    report: dict,
    *,
    superseded_by: str | None = None,
    correction: str | None = None,
) -> dict:
    """Non-destructively relabel a recorded latency report recorded by an older recorder.

    Older artifacts (cycle 38649613677 and earlier) derived ``cache_state``
    from the sample index and stored every retrieval-phase time under
    ``upstream_retrieval_s``. Those artifacts are historical claim-bearing
    evidence, so nothing is deleted here:

    * the original per-sample values are preserved under
      ``as_recorded_*`` keys and the original report is kept verbatim under
      ``as_recorded_report``;
    * ``upstream_retrieval_s`` is nulled for every sample that is not provably
      network-served, and the raw value moves to ``retrieval_s``;
    * aggregates/verdicts are recomputed from the corrected samples, which can
      only *remove* upstream claims, never add budget headroom;
    * a ``correction`` block states plainly whether any sample in the artifact
      exercised the network.
    """
    samples_in = [dict(s) for s in (report.get("samples") or [])]
    samples_out: list[dict] = []
    exercised_network = False
    for raw in samples_in:
        sample = dict(raw)
        observed_summary = sample.get("request_summary") or {}
        if observed_summary:
            served_from = classify_served_from({
                "provenance": {
                    "request_summary": observed_summary,
                    "fixture_mode": sample.get("mode") == "fixture",
                }
            })[0]
        else:
            # No per-request evidence. The pre-repair ``cache_state`` was derived
            # from the sample index, so it cannot be trusted as a data source:
            # the only honest classification is "unknown", which costs the
            # artifact its upstream claim and keeps the budgeted numbers.
            served_from = "unknown"
        sample["served_from"] = served_from
        sample["cache_state"] = CACHE_STATE_BY_SERVED_FROM[served_from]
        sample["as_recorded_cache_state"] = raw.get("cache_state", sample["cache_state"])
        recorded_upstream = raw.get("upstream_retrieval_s")
        sample.setdefault("retrieval_s", recorded_upstream)
        if recorded_upstream is not None:
            sample["as_recorded_upstream_retrieval_s"] = recorded_upstream
        if served_from == "network":
            sample["upstream_retrieval_s"] = recorded_upstream
            exercised_network = True
        else:
            sample["upstream_retrieval_s"] = None
        samples_out.append(sample)

    rebuilt = build_report(samples_out, run_id=report.get("run_id"))
    corrected = dict(rebuilt)
    corrected["generated_at"] = report.get("generated_at", rebuilt["generated_at"])
    corrected["record_type"] = report.get("record_type", rebuilt["record_type"])
    corrected["note"] = report.get("note")
    # Re-annotating an already-corrected artifact must not nest history: the
    # ORIGINAL report stays the reference copy.
    prior_original = (report.get("correction") or {}).get("as_recorded_report")
    corrected["correction"] = {
        "applied_by": "product/latency_budget.py annotate_legacy_report",
        "reason": correction or (
            "per-sample cache_state was derived from the sample index and cache/fixture read time "
            "was published as upstream_retrieval_s"
        ),
        "network_sample_evidence": sorted({
            int((s.get("request_summary") or {}).get("network_calls") or 0)
            for s in samples_out if s.get("served_from") == "network"
        }),
        "any_sample_exercised_network": exercised_network,
        "original_upstream_retrieval_s_p50": (report.get("warm_samples") or {}).get(
            "upstream_retrieval_s", {}
        ).get("p50"),
        "original_upstream_retrieval_s_p95": (report.get("warm_samples") or {}).get(
            "upstream_retrieval_s", {}
        ).get("p95"),
        "as_recorded_report": prior_original if prior_original is not None else report,
    }
    if superseded_by:
        corrected["superseded_by"] = superseded_by
    return corrected


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--mode", choices=["fixture", "live", "offline", "refresh"], default="fixture")
    parser.add_argument("--repeat", type=int, default=DEFAULT_REPEATS)
    parser.add_argument("--top-n", type=int, default=150)
    parser.add_argument("--with-enrich", action="store_true", help="also time the answer/counter pass")
    parser.add_argument(
        "--refresh-first", type=int, default=0,
        help="record N leading samples with retrieval_mode=refresh (network only) so the "
             "artifact contains genuine OpenCaseLaw upstream measurements",
    )
    parser.add_argument("--from-samples", type=Path, default=None, help="re-aggregate recorded samples (offline)")
    parser.add_argument(
        "--annotate-legacy", type=Path, default=None,
        help="relabel a report recorded by the pre-repair recorder (non-destructive)",
    )
    parser.add_argument("--superseded-by", default=None, help="artifact path replacing an annotated legacy report")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.annotate_legacy:
        report = annotate_legacy_report(
            json.loads(args.annotate_legacy.read_text(encoding="utf-8")),
            superseded_by=args.superseded_by,
        )
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(
                json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
            )
            print(f"wrote {args.out}")
        correction = report["correction"]
        print(
            f"corrected {args.annotate_legacy}: upstream p50/p95 as recorded "
            f"{correction['original_upstream_retrieval_s_p50']}/"
            f"{correction['original_upstream_retrieval_s_p95']} -> "
            f"{report['verdicts']['upstream_retrieval_s']['p50']}/"
            f"{report['verdicts']['upstream_retrieval_s']['p95']} "
            f"(upstream_measured={report['upstream_measured']})"
        )
        return 0

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
            refresh_first=args.refresh_first,
        )

    report = build_report(samples, run_id=args.run_id)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {args.out}")

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        counts = report["served_from_counts"]
        print(
            f"samples: {report['n_samples']} "
            f"(network={counts['network']} cache={counts['cache']} mixed={counts['mixed']} "
            f"fixture={counts['fixture']} unknown={counts['unknown']}; "
            f"{report['n_warm_samples']} non-network used for the cached-map budget)"
        )
        for metric, verdict in sorted(report["verdicts"].items()):
            unit = "ms" if metric.endswith("_ms") else "s"
            if verdict.get("budgeted"):
                print(
                    f"  [{verdict['verdict']}] {metric}: p50={verdict['p50']}{unit} "
                    f"p95={verdict['p95']}{unit} budget={verdict['budget_s']}{unit} (n={verdict.get('n')})"
                )
            else:
                suffix = "" if verdict.get("measured", True) else " (UNMEASURED: no network-served sample)"
                print(
                    f"  [not budgeted] {metric}: p50={verdict.get('p50')}{unit} "
                    f"p95={verdict.get('p95')}{unit}{suffix}"
                )
        print("  upstream is reported separately and is not a local budget:")
        print(
            f"    upstream_retrieval_s (network-served only) "
            f"p50={report['upstream_samples']['upstream_retrieval_s'].get('p50')} "
            f"p95={report['upstream_samples']['upstream_retrieval_s'].get('p95')} "
            f"(n={report['upstream_samples']['upstream_retrieval_s'].get('n', 0)}) | "
            f"local_map_s p50={report['warm_samples']['local_map_s'].get('p50')} "
            f"p95={report['warm_samples']['local_map_s'].get('p95')}"
        )
        for warning in report["warnings"]:
            print(f"  ::warning::{warning}")
    return 0 if report["within_budget"] else 3


if __name__ == "__main__":  # pragma: no cover - CLI
    sys.exit(main())
