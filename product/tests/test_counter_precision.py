"""Precision adjudication of the 42 -> 70 heuristic-signal trade (v65 item 3).

These tests pin the product-owned adjudication contract: the arm partition,
the pre-registered verdict rule, the unchanged budgets, and the fact that a
real single-leg measurement is network-free and discloses its frozen-profile
resolution.  They change no frozen bar and never assert legal correctness.
"""
from __future__ import annotations

import sys
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PRODUCT_ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from product.query import counter_precision as cp  # noqa: E402
from product.query import counter_surface as cs  # noqa: E402


def _signalled(decision_id: str, arm: str, evidenced_guarded: bool,
               evidenced_unguarded: bool | None = None) -> dict:
    return {
        "decision_id": decision_id,
        "arm": arm,
        "guarded": {
            "evidenced": evidenced_guarded,
            "reason_code": "supported_verbatim_span" if evidenced_guarded
            else "no_emitting_span",
        },
        "unguarded": {
            "evidenced": evidenced_unguarded if evidenced_unguarded is not None
            else evidenced_guarded,
            "reason_code": "supported_verbatim_span"
            if (evidenced_unguarded if evidenced_unguarded is not None
                else evidenced_guarded)
            else "no_emitting_span",
        },
    }


def test_budgets_are_the_accepted_ones_and_unchanged() -> None:
    assert cp.BASELINE_CAP == cs.LIVE_HYDRATION_TOP == 8
    assert cp.BROAD_CAP == cs.CACHED_HYDRATION_TOP == 24


def test_arm_summary_counts_and_yields() -> None:
    rows = [
        _signalled("a", "delta", True),
        _signalled("b", "delta", False),
        _signalled("c", "delta", False),
        _signalled("d", "baseline", True),
    ]
    delta = cp._arm_summary(rows, "delta")
    assert delta["n_signals"] == 3
    assert delta["n_evidenced_guarded"] == 1
    assert delta["evidence_yield_guarded"] == round(1 / 3, 6)
    baseline = cp._arm_summary(rows, "baseline")
    assert baseline["n_signals"] == 1
    assert baseline["n_evidenced_guarded"] == 1
    assert baseline["evidence_yield_guarded"] == 1.0
    assert delta["guarded_abstention_reasons"] == {
        "no_emitting_span": 2, "supported_verbatim_span": 1,
    }


def test_verdict_rule_is_pre_registered_and_trichotomous() -> None:
    base_ok = {"evidence_yield_guarded": 0.4}
    # proportional: delta >= 0.5 * base
    v = cp._verdict(base_ok, {"evidence_yield_guarded": 0.2})
    assert v["verdict"] == cp.VERDICT_PROPORTIONAL
    assert v["min_delta_rate_ratio"] == cp.MIN_DELTA_RATE_RATIO == 0.5
    # dominated: delta < 0.5 * base
    v = cp._verdict(base_ok, {"evidence_yield_guarded": 0.19})
    assert v["verdict"] == cp.VERDICT_DOMINATED
    # undiscriminating: baseline yield is 0 / None
    v = cp._verdict({"evidence_yield_guarded": 0}, {"evidence_yield_guarded": 1.0})
    assert v["verdict"] == cp.VERDICT_UNDISCRIMINATING
    v = cp._verdict({"evidence_yield_guarded": None}, {"evidence_yield_guarded": None})
    assert v["verdict"] == cp.VERDICT_UNDISCRIMINATING
    # the budget effect sentence is always published
    assert "live/refresh budget stays 8" in v["budget_effect"]


def test_adjudicate_row_abstains_honestly_without_a_profile() -> None:
    rec = cp._adjudicate_row(
        {"decision_id": "x", "counter_surface_signal": {"heuristic_status": "t"}},
        rules=None,
        profile=None,
        decide_label=None,
        guard=None,
    )
    assert rec["guarded"]["evidenced"] is False
    assert rec["guarded"]["reason_code"] == "no_frozen_anchor_profile"
    assert rec["unguarded"]["reason_code"] == "no_frozen_anchor_profile"


def test_signalled_rows_filter_is_strict() -> None:
    bundle = {
        "decisions": [
            {"decision_id": "a", "counter_surface_signal": {"heuristic_status": "t"}},
            {"decision_id": "b"},
            {"decision_id": "c", "counter_surface_signal": None},
        ],
    }
    assert set(cp._signalled_rows(bundle)) == {"a"}


def test_single_leg_measurement_is_network_free_and_discloses_profile() -> None:
    """One cached leg end-to-end: partition, profile disclosure, invariants."""
    out = cp.measure(legs=["rent-default"])
    assert out["schema"] == cp.SCHEMA
    assert out["version"] == cp.PRECISION_VERSION
    assert "network blocked" in out["mode"] and "no LLM" in out["mode"]
    assert out["invariants"]["network_calls_blocked"] is True
    assert out["invariants"]["signals_monotone_in_cap"] is True
    assert out["invariants"]["budgets_unchanged"] is True

    leg = out["legs"][0]
    assert leg["slug"] == "rent-default"
    # the French bail query resolves to the frozen fr-bail-entretien profile
    assert leg["resolved_profile_key"] == cp.PROFILE_KEY_RENT_DEFAULT
    assert leg["profile_applicable"] is True

    # arm partition is a true partition of the broad-cap signalled set
    broad = leg["n_signalled_broad_cap"]
    assert leg["arms"]["baseline"]["n_signals"] + leg["arms"]["delta"]["n_signals"] == broad
    assert leg["n_delta_only"] == leg["arms"]["delta"]["n_signals"]
    assert leg["n_signalled_baseline_cap"] == leg["arms"]["baseline"]["n_signals"]

    # every row is labelled with exactly one arm and carries both gate arms
    arms = {row["arm"] for row in leg["rows"]}
    assert arms <= {"baseline", "delta"}
    for row in leg["rows"]:
        assert row["arm"] in ("baseline", "delta")
        assert "evidenced" in row["guarded"] and "evidenced" in row["unguarded"]

    # the adjudication verdict is always present and named
    adj = out["aggregate"]["adjudication"]
    assert adj["verdict"] in (
        cp.VERDICT_PROPORTIONAL, cp.VERDICT_DOMINATED, cp.VERDICT_UNDISCRIMINATING,
    )
    assert "live/refresh budget stays 8" in adj["budget_effect"]

    # frozen-profile resolution is disclosed per leg, never hidden
    assert out["profile_resolution_disclosure"]["per_leg"]["rent-default"] == (
        cp.PROFILE_KEY_RENT_DEFAULT
    )


def test_reference_counts_match_the_accepted_coverage_artifact() -> None:
    import json

    path = (REPO_ROOT / "results" / "product" / "counter_surface_known"
            / "CYCLE_39956256289.json")
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc["aggregate"]["by_cap"]["8"]["n_signalled_total"] == 42
    assert doc["aggregate"]["by_cap"]["24"]["n_signalled_total"] == 70
    assert doc["aggregate"]["by_cap"]["8"]["known_signalled_n"] == 8
    assert doc["aggregate"]["by_cap"]["24"]["known_signalled_n"] == 11
    # the module's published reference counts must not drift from the artifact
    assert cp.BASELINE_CAP == 8 and cp.BROAD_CAP == 24
