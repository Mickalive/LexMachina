"""Tests for the QUERY_MAP_MVP 9A latency budget recorder (direction v51 delta 2).

The v50 audit recorded the gap verbatim: *"Latency budgets from QUERY_MAP_MVP
§9A not yet measured on live retrieval path"*. These tests freeze the two
properties that make such a measurement usable rather than decorative:

* **separation** — upstream OpenCaseLaw time is measured and reported, but is
  never used to judge local code (and vice versa);
* **an auditable estimator** — p50/p95 are nearest-rank values of measurements
  that actually happened, never interpolated fiction, and the sample count
  travels with them.

Repair of cycle 38649613677 (audit REVISE, round 1)
--------------------------------------------------
The rejected cycle published ``upstream_retrieval_s`` p50 0.275 s / p95 0.303 s
while every one of its five samples ran with zero network calls: the value was a
local file-cache read, ``cache_state`` came from the sample index, and nothing
in the artifact said the network had never been touched. The properties frozen
below are therefore *stronger* than the originals:

* only a sample with observed ``network_calls`` may carry upstream latency;
* ``cache_state``/``served_from`` are derived from observed provenance, never
  from the position of the sample in the run;
* a run with no network-served sample reports upstream as UNMEASURED instead of
  publishing a small, fast, wrong number;
* the three budgeted verdicts keep their original 9A limits (cached map <1s,
  local map <1.5s, detail click <150ms) and are still computed by nearest rank.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

PRODUCT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PRODUCT_ROOT.parent
if str(PRODUCT_ROOT) not in sys.path:
    sys.path.insert(0, str(PRODUCT_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from latency_budget import (  # noqa: E402
    BUDGETS,
    MIN_SAMPLES_FOR_P95,
    aggregate,
    annotate_legacy_report,
    build_report,
    classify_served_from,
    derive_cache_state,
    evaluate,
    measure,
    measure_detail_click_ms,
    quantile,
    sample_served_from,
    upstream_admissible,
)


def sample(
    index: int,
    *,
    upstream: float,
    local: float,
    total: float,
    click: float,
    state: str = "warm",
    served_from: str | None = None,
) -> dict:
    out = {
        "index": index,
        "cache_state": state,
        "mode": "fixture",
        "query": "Kündigung Mietvertrag Mietrecht",
        "n_decisions": 100,
        "n_clusters": 8,
        "retrieval_s": upstream,
        "upstream_retrieval_s": upstream,
        "local_map_s": local,
        "map_total_s": total,
        "detail_click_local_ms": click,
    }
    if served_from is not None:
        out["served_from"] = served_from
    return out


def warm_run(n: int = 6, *, upstream: float = 0.3, local: float = 0.05, click: float = 0.4) -> list[dict]:
    """Cache-served samples: the default shape of a warm/cached run."""
    return [
        sample(i, upstream=upstream, local=local, total=upstream + local, click=click, served_from="cache")
        for i in range(n)
    ]


# --------------------------------------------------------------------------
# estimator
# --------------------------------------------------------------------------


def test_quantile_uses_nearest_rank_not_interpolation() -> None:
    values = [1.0, 2.0, 3.0, 4.0]
    assert quantile(values, 0.5) == 2.0  # ceil(0.5*4)=2 -> 2nd value
    assert quantile(values, 0.95) == 4.0  # ceil(0.95*4)=4 -> 4th value
    assert quantile(values, 0.0) == 1.0


def test_quantile_handles_empty_and_none() -> None:
    assert quantile([], 0.5) is None
    assert quantile([None, 2.0], 0.5) == 2.0


def test_aggregate_reports_count_and_estimator() -> None:
    stats = aggregate(warm_run(6), "local_map_s")
    assert stats["n"] == 6
    assert stats["p50"] == 0.05 and stats["p95"] == 0.05
    assert stats["min"] == stats["max"] == 0.05
    assert "nearest-rank" in stats["estimator"]


# --------------------------------------------------------------------------
# budgets and separation
# --------------------------------------------------------------------------


def test_budgets_come_from_the_9a_lane_mandate() -> None:
    assert BUDGETS["cached_map_total_s"]["limit"] == 1.0
    assert BUDGETS["local_map_s"]["limit"] == 1.5
    assert BUDGETS["detail_click_local_ms"]["limit"] == 150.0
    for spec in BUDGETS.values():
        assert "QUERY_MAP_MVP" in spec["source"] or "lane runtime" in spec["source"]


def test_upstream_is_never_a_local_budget() -> None:
    verdict = evaluate({"upstream_retrieval_s": {"p50": 9.0, "p95": 30.0, "n": 6}}, "upstream_retrieval_s")
    assert verdict["budgeted"] is False
    assert verdict["verdict"] == "not_budgeted"
    assert verdict["p95"] == 30.0  # reported, not suppressed


def test_enrich_is_reported_but_never_budgeted() -> None:
    verdict = evaluate({"enrich_total_s": {"p50": 90.0, "p95": 200.0, "n": 6}}, "enrich_total_s")
    assert verdict["verdict"] == "not_budgeted"


def test_local_budget_miss_is_reported_as_MISS() -> None:
    verdict = evaluate({"local_map_s": {"p50": 0.9, "p95": 1.4, "n": 6}}, "local_map_s")
    assert verdict["verdict"] == "PASS"
    miss = evaluate({"local_map_s": {"p50": 1.2, "p95": 1.9, "n": 6}}, "local_map_s")
    assert miss["verdict"] == "MISS"
    assert miss["headroom_p95_s"] == pytest.approx(-0.4)


def test_report_separates_upstream_from_local_end_to_end() -> None:
    """One network sample + six cache samples: upstream comes from the network sample."""
    samples = [
        sample(0, upstream=4.0, local=0.05, total=4.05, click=0.3, state="cold", served_from="network")
    ] + warm_run(6)
    report = build_report(samples)
    assert report["n_cold_samples"] == 1 and report["n_warm_samples"] == 6
    # Upstream statistics come from network-served samples only ...
    assert report["upstream_samples"]["upstream_retrieval_s"]["p50"] == 4.0
    assert report["upstream_measured"] is True
    assert report["verdicts"]["upstream_retrieval_s"]["p50"] == 4.0
    # ... and a cache read is never charged to the OpenCaseLaw network.
    assert report["warm_samples"]["upstream_retrieval_s"]["n"] == 0
    assert report["warm_samples"]["local_map_s"]["p50"] == 0.05
    assert "never attributed to local code" in report["separation_rule"]
    assert report["within_budget"] is True


def test_slow_upstream_never_fails_the_local_map_budget() -> None:
    """A slow public API must not be charged to local geometry."""
    samples = [
        sample(
            i,
            upstream=12.0,
            local=0.04,
            total=12.04,
            click=0.2,
            state="cold" if i == 0 else "warm",
            served_from="network" if i == 0 else "cache",
        )
        for i in range(6)
    ]
    report = build_report(samples)
    assert report["verdicts"]["local_map_s"]["verdict"] == "PASS"
    assert report["verdicts"]["local_map_s"]["p95"] == 0.04
    assert report["verdicts"]["upstream_retrieval_s"]["budgeted"] is False
    # The cached-MAP budget is a user-visible total and therefore still fails
    # honestly when every warm query costs 12s upstream: slow public
    # infrastructure is not hidden from the product's own budget either.
    assert report["verdicts"]["cached_map_total_s"]["verdict"] == "MISS"
    assert report["within_budget"] is False


def test_realistic_warm_sample_set_is_within_budget() -> None:
    assert build_report(warm_run(6))["within_budget"] is True


def test_small_sample_warning_is_emitted() -> None:
    report = build_report(warm_run(2))
    assert any("coarse" in warning for warning in report["warnings"])
    report_ok = build_report(warm_run(MIN_SAMPLES_FOR_P95))
    assert not any("coarse" in warning for warning in report_ok["warnings"])


def test_missing_cold_sample_is_warned_about() -> None:
    report = build_report(warm_run(6))
    assert any("no cold sample" in warning for warning in report["warnings"])


# --------------------------------------------------------------------------
# measurement helpers
# --------------------------------------------------------------------------


def test_detail_click_is_a_local_bundle_lookup() -> None:
    bundle = {"decisions": [{"decision_id": "a"}, {"decision_id": "b"}]}
    ms = measure_detail_click_ms(bundle)
    assert ms is not None and 0.0 <= ms < 150.0
    assert measure_detail_click_ms({"decisions": []}) is None


def test_measure_fixture_mode_produces_upstream_local_split() -> None:
    """Fixture replay: local timings are measured, upstream is NOT claimed."""
    samples = measure("Kündigung Mietvertrag Mietrecht", mode="fixture", repeats=2, top_n=60)
    assert len(samples) == 2
    # Fixture replay is neither a network measurement nor a cache measurement.
    assert [s["cache_state"] for s in samples] == ["fixture", "fixture"]
    assert [s["served_from"] for s in samples] == ["fixture", "fixture"]
    for s in samples:
        assert s["upstream_retrieval_s"] is None
        assert s["retrieval_s"] >= 0.0
        assert s["local_map_s"] >= 0.0
        assert s["map_total_s"] >= s["local_map_s"] - 1e-6
        assert s["n_decisions"] > 0
        assert s["detail_click_local_ms"] < 150.0
    report = build_report(samples)
    assert report["upstream_measured"] is False
    assert any("UNMEASURED" in warning for warning in report["warnings"])


# --------------------------------------------------------------------------
# repair of the mislabelled upstream latency (cycle 38649613677)
# --------------------------------------------------------------------------


def bundle_with(*, network_calls: int = 0, cache_hits: int = 0, fixture_mode: bool = False,
                retrieval_mode: str = "live", upstream_s: float = 0.3) -> dict:
    return {
        "query": "Kündigung Mietvertrag Mietrecht",
        "decisions": [{"decision_id": "a"}],
        "provenance": {
            "fixture_mode": fixture_mode,
            "mode": retrieval_mode,
            "request_summary": {
                "requests_logged": network_calls + cache_hits,
                "network_calls": network_calls,
                "cache_hits": cache_hits,
            },
            "cache_stats": {"hits": cache_hits, "misses": network_calls, "writes": network_calls},
            "timing": {"upstream_retrieval_s": upstream_s, "local_map_s": 0.05, "mode": retrieval_mode},
        },
    }


def test_served_from_is_derived_from_observed_network_calls_not_the_index() -> None:
    """A first sample that was served from cache must not be labelled cold."""
    assert classify_served_from(bundle_with(network_calls=12, cache_hits=0))[0] == "network"
    assert classify_served_from(bundle_with(network_calls=0, cache_hits=12))[0] == "cache"
    assert classify_served_from(bundle_with(network_calls=6, cache_hits=6))[0] == "mixed"
    assert classify_served_from(bundle_with(fixture_mode=True, retrieval_mode="fixture"))[0] == "fixture"
    assert classify_served_from({"provenance": {}})[0] == "unknown"


def test_cache_state_is_a_consequence_of_the_observation() -> None:
    _, network_state, _ = derive_cache_state(bundle_with(network_calls=12))
    _, cache_state, _ = derive_cache_state(bundle_with(cache_hits=12))
    assert network_state == "cold"
    assert cache_state == "warm"


def test_cache_read_time_is_never_published_as_upstream_latency() -> None:
    """The exact defect of cycle 38649613677, frozen as a regression guard."""
    samples = [sample(i, upstream=0.2774, local=0.05, total=0.33, click=0.0004, served_from="cache")
               for i in range(5)]
    report = build_report(samples)
    assert report["upstream_measured"] is False
    assert report["verdicts"]["upstream_retrieval_s"]["p50"] is None
    assert report["verdicts"]["upstream_retrieval_s"]["p95"] is None
    assert report["upstream_samples"]["upstream_retrieval_s"]["n"] == 0
    assert "UNMEASURED" in report["verdicts"]["upstream_retrieval_s"]["note"]
    assert any("UNMEASURED" in warning for warning in report["warnings"])
    # The local budgets are still judged, and still pass.
    assert report["within_budget"] is True
    assert report["verdicts"]["cached_map_total_s"]["verdict"] == "PASS"


def test_only_network_samples_are_upstream_admissible() -> None:
    assert upstream_admissible({"served_from": "network"}) is True
    for served_from in ("cache", "mixed", "fixture", "unknown"):
        assert upstream_admissible({"served_from": served_from}) is False
    assert sample_served_from({"cache_state": "warm"}) == "cache"  # legacy fallback


def test_mixed_samples_are_excluded_from_the_pure_network_percentile() -> None:
    samples = [
        sample(0, upstream=10.0, local=0.05, total=10.05, click=0.2, served_from="network"),
        sample(1, upstream=6.0, local=0.05, total=6.05, click=0.2, served_from="mixed"),
    ] + warm_run(5)
    report = build_report(samples)
    assert report["upstream_samples"]["upstream_retrieval_s"]["n"] == 1
    assert report["upstream_samples"]["upstream_retrieval_s"]["p50"] == 10.0
    assert report["n_mixed_samples"] == 1
    assert any("mixed" in warning for warning in report["warnings"])


def test_mixed_network_and_cache_run_measures_both_halves() -> None:
    """One artifact, two data sources: network upstream + warm cached-map budget."""
    samples = [sample(i, upstream=11.0 + i, local=0.06, total=11.1 + i, click=0.0004, served_from="network")
               for i in range(3)] + warm_run(6)
    report = build_report(samples)
    assert report["served_from_counts"] == {"network": 3, "mixed": 0, "cache": 6, "fixture": 0, "unknown": 0}
    assert report["upstream_measured"] is True
    assert report["upstream_samples"]["upstream_retrieval_s"]["p50"] == 12.0  # median of 11,12,13
    assert report["warm_samples"]["local_map_s"]["p95"] == 0.05
    assert report["verdicts"]["cached_map_total_s"]["verdict"] == "PASS"
    assert report["within_budget"] is True


def test_unknown_samples_are_flagged_as_unproven_cache_times() -> None:
    samples = [
        sample(i, upstream=0.3, local=0.05, total=0.35, click=0.4, state="unknown", served_from="unknown")
        for i in range(6)
    ]
    report = build_report(samples)
    assert report["n_unknown_samples"] == 6
    assert report["n_warm_basis"] == "unknown"
    assert any("NO observed cache/network evidence" in warning for warning in report["warnings"])
    assert report["upstream_measured"] is False


def test_measure_records_per_sample_cache_and_network_provenance() -> None:
    samples = measure("Kündigung Mietvertrag Mietrecht", mode="fixture", repeats=1, top_n=40)
    assert samples[0]["served_from_basis"] == "provenance.fixture_mode"
    assert set(samples[0]["request_summary"]) == {"requests_logged", "network_calls", "cache_hits", "failures"}
    assert set(samples[0]["cache_stats"]) == {"hits", "misses", "writes", "n_keys"}


def test_annotate_legacy_report_retracts_the_unproven_upstream_claim() -> None:
    """Repair of the rejected artifact: nothing deleted, false claim retracted."""
    legacy = {
        "generated_at": "2026-10-14T22:49:58Z",
        "run_id": "38649613677",
        "samples": [
            sample(0, upstream=0.2774, local=0.212, total=0.4898, click=0.0002, state="cold"),
            *[sample(i, upstream=0.30, local=0.05, total=0.34, click=0.0004, state="warm") for i in range(1, 5)],
        ],
        "warm_samples": {"upstream_retrieval_s": {"p50": 0.275, "p95": 0.3034}},
    }
    corrected = annotate_legacy_report(legacy, superseded_by="results/product/latency_budget/NEW.json")
    assert corrected["superseded_by"] == "results/product/latency_budget/NEW.json"
    assert corrected["upstream_measured"] is False
    assert corrected["verdicts"]["upstream_retrieval_s"]["p50"] is None
    assert corrected["correction"]["any_sample_exercised_network"] is False
    assert corrected["correction"]["original_upstream_retrieval_s_p95"] == 0.3034
    # The original claim survives verbatim inside the correction block.
    assert corrected["correction"]["as_recorded_report"] == legacy
    # Raw values are preserved per sample, only relabelled.
    first = corrected["samples"][0]
    assert first["retrieval_s"] == 0.2774
    assert first["as_recorded_upstream_retrieval_s"] == 0.2774
    assert first["as_recorded_cache_state"] == "cold"
    assert first["upstream_retrieval_s"] is None
    assert first["cache_state"] == "unknown"


def test_annotate_legacy_report_keeps_a_genuinely_network_served_sample() -> None:
    samples = [sample(0, upstream=107.6075, local=0.1864, total=107.7939, click=0.0004,
                      state="cold", served_from="network")]
    samples[0]["mode"] = "live"
    samples[0]["request_summary"] = {"requests_logged": 12, "network_calls": 12, "cache_hits": 0}
    corrected = annotate_legacy_report({"samples": samples, "warm_samples": {}})
    assert corrected["upstream_measured"] is True
    assert corrected["verdicts"]["upstream_retrieval_s"]["p50"] == 107.6075
    assert corrected["correction"]["any_sample_exercised_network"] is True


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def test_cli_reaggregates_recorded_samples_offline(tmp_path: Path) -> None:
    samples_path = tmp_path / "samples.json"
    samples_path.write_text(json.dumps({"samples": warm_run(6)}), encoding="utf-8")
    out_path = tmp_path / "report.json"
    result = subprocess.run(
        [
            sys.executable, str(PRODUCT_ROOT / "latency_budget.py"),
            "--from-samples", str(samples_path), "--out", str(out_path),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(out_path.read_text(encoding="utf-8"))
    assert report["within_budget"] is True
    assert "upstream is reported separately" in result.stdout


def test_cli_exits_3_when_a_budget_is_missed(tmp_path: Path) -> None:
    samples_path = tmp_path / "slow.json"
    samples_path.write_text(
        json.dumps({"samples": [sample(i, upstream=0.2, local=2.5, total=2.7, click=0.4) for i in range(6)]}),
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(PRODUCT_ROOT / "latency_budget.py"), "--from-samples", str(samples_path)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 3
    assert "[MISS] local_map_s" in result.stdout

def test_annotate_legacy_report_is_idempotent_about_history() -> None:
    """Re-annotating must not nest the correction block inside itself."""
    legacy = {
        "samples": [sample(0, upstream=0.2774, local=0.05, total=0.33, click=0.2, state="cold")],
        "warm_samples": {"upstream_retrieval_s": {"p50": 0.275, "p95": 0.3034}},
    }
    once = annotate_legacy_report(legacy)
    twice = annotate_legacy_report(once)
    assert twice["correction"]["as_recorded_report"] == legacy
    assert "correction" not in twice["correction"]["as_recorded_report"]
    assert twice["verdicts"]["upstream_retrieval_s"]["p95"] is None
    assert once["correction"]["as_recorded_report"] == legacy
