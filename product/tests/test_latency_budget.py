"""Tests for the QUERY_MAP_MVP 9A latency budget recorder (direction v51 delta 2).

The v50 audit recorded the gap verbatim: *"Latency budgets from QUERY_MAP_MVP
§9A not yet measured on live retrieval path"*. These tests freeze the two
properties that make such a measurement usable rather than decorative:

* **separation** — upstream OpenCaseLaw time is measured and reported, but is
  never used to judge local code (and vice versa);
* **an auditable estimator** — p50/p95 are nearest-rank values of measurements
  that actually happened, never interpolated fiction, and the sample count
  travels with them.
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
    build_report,
    evaluate,
    measure,
    measure_detail_click_ms,
    quantile,
)


def sample(index: int, *, upstream: float, local: float, total: float, click: float, state: str = "warm") -> dict:
    return {
        "index": index,
        "cache_state": state,
        "mode": "fixture",
        "query": "Kündigung Mietvertrag Mietrecht",
        "n_decisions": 100,
        "n_clusters": 8,
        "upstream_retrieval_s": upstream,
        "local_map_s": local,
        "map_total_s": total,
        "detail_click_local_ms": click,
    }


def warm_run(n: int = 6, *, upstream: float = 0.3, local: float = 0.05, click: float = 0.4) -> list[dict]:
    return [sample(i, upstream=upstream, local=local, total=upstream + local, click=click) for i in range(n)]


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
    samples = [sample(0, upstream=4.0, local=0.05, total=4.05, click=0.3, state="cold")] + warm_run(6)
    report = build_report(samples)
    assert report["n_cold_samples"] == 1 and report["n_warm_samples"] == 6
    assert report["warm_samples"]["upstream_retrieval_s"]["p50"] == 0.3
    assert report["warm_samples"]["local_map_s"]["p50"] == 0.05
    assert "never attributed to local code" in report["separation_rule"]
    assert report["within_budget"] is True


def test_slow_upstream_never_fails_the_local_map_budget() -> None:
    """A slow public API must not be charged to local geometry."""
    samples = [
        sample(i, upstream=12.0, local=0.04, total=12.04, click=0.2, state="cold" if i == 0 else "warm")
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
    samples = measure("Kündigung Mietvertrag Mietrecht", mode="fixture", repeats=2, top_n=60)
    assert len(samples) == 2
    assert [s["cache_state"] for s in samples] == ["cold", "warm"]
    for s in samples:
        assert s["upstream_retrieval_s"] >= 0.0
        assert s["local_map_s"] >= 0.0
        assert s["map_total_s"] >= s["local_map_s"] - 1e-6
        assert s["n_decisions"] > 0
        assert s["detail_click_local_ms"] < 150.0


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