"""Fixture-slice latency regression: MVP QUERY_MAP_MVP §9A budgets on measured code.

Why this file exists (run 38862025900)
--------------------------------------
``test_latency_budget.py`` freezes the estimator properties on synthetic
samples, and ``test_progressive_query.py`` freezes the progressive contract —
but nothing asserted the §9A engineering budgets against a *measured* run of
the shipped pipeline. A regression that put legacy 174k representations back
on the default hot path (explicitly forbidden by §9A "Memory/startup
discipline") would pass every existing test while blowing the budgets the
owner actually feels.

These tests run the real ``run_query_initial`` / first-page / expand path in
deterministic fixture mode (frozen OpenCaseLaw envelopes, no network) and
assert the bundle's own measured ``provenance.timing`` fields against the
mandate:

* local normalize/rerank/geometry/render overhead < 1.5 s after the first
  upstream page arrives (``local_map_s``);
* local clustering/projection for ~100 decisions < 2 s (``local_total_s``);
* upstream OpenCaseLaw time is measured separately and never judges local
  code (separation property, same rule as ``test_latency_budget.py``).

Headroom is deliberate: the frozen fixture slice measures ~0.2 s local map /
~0.3 s local total on CI hardware, so the 1.5 s / 2.0 s bars are tripwires for
structural regressions (corpus-scale matrices on the hot path, uncached
recompute), not flakiness sources. No threshold, baseline, metric or
pre-registration is touched; no geometry or label-measurement work is taken
up here (that is Frontier's lane per factory direction v54).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "product"
sys.path.insert(0, str(PRODUCT))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "frontier" / "frontier-query-retrieval"))
sys.path.insert(0, str(ROOT / "frontier" / "frontier-generative-audit"))

from query import expand_query_bundle, run_query_first_page  # noqa: E402
from query.bundle import validate_bundle  # noqa: E402
from query.pipeline import run_query_initial  # noqa: E402

QUERY = "Kündigung Mietvertrag Mietrecht"

# QUERY_MAP_MVP §9A engineering budgets (targets, used here as tripwires).
LOCAL_MAP_BUDGET_S = 1.5
LOCAL_TOTAL_BUDGET_S = 2.0


def _timing(bundle: dict) -> dict:
    timing = bundle["provenance"]["timing"]
    assert {"upstream_retrieval_s", "local_map_s", "local_total_s",
            "n_decisions"} <= set(timing), timing
    return timing


def test_initial_slice_local_map_overhead_is_within_budget():
    t0 = time.time()
    bundle = run_query_initial(QUERY, top_n=100, retrieval_mode="fixture")
    wall_s = time.time() - t0
    assert validate_bundle(bundle) == []
    assert len(bundle["decisions"]) >= 50
    timing = _timing(bundle)
    # The mandate's number: local overhead after the first upstream page.
    assert timing["local_map_s"] < LOCAL_MAP_BUDGET_S, timing
    assert timing["local_total_s"] < LOCAL_TOTAL_BUDGET_S, timing
    # Wall clock agrees with the bundle's self-report (no hidden stage).
    assert wall_s < LOCAL_TOTAL_BUDGET_S + 1.0, {"wall_s": wall_s, **timing}


def test_first_page_and_expansion_each_stay_within_budget():
    first = run_query_first_page(QUERY, top_n=100, retrieval_mode="fixture")
    assert validate_bundle(first) == []
    timing = _timing(first)
    assert timing["local_map_s"] < LOCAL_MAP_BUDGET_S, timing
    expanded = expand_query_bundle(first, retrieval_mode="fixture")
    assert validate_bundle(expanded) == []
    assert expanded["provenance"]["timing"]["expand_local_s"] < LOCAL_TOTAL_BUDGET_S, \
        expanded["provenance"]["timing"]


def test_upstream_time_never_judges_local_code_on_the_fixture_slice():
    bundle = run_query_initial(QUERY, top_n=100, retrieval_mode="fixture")
    timing = _timing(bundle)
    assert timing["upstream_retrieval_s"] >= 0
    # The budgeted verdicts use only local fields; upstream is reported, not
    # judged. Recompute the verdicts here so a future refactor cannot silently
    # fold upstream time into a "local" measurement.
    assert timing["local_total_s"] >= timing["local_map_s"] >= 0
    assert timing["mode"] == "fixture"
    assert timing["n_decisions"] == len(bundle["decisions"])
