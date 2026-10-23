"""Known-authority coverage fixture, matcher and measurement contract (v64).

These tests pin the product-owned part of the direction-v64 item 7(a)
measurement: the adopted ids, the frozen alnum-core rule, the mode-aware
hydration budget, and the fact that the measurement is network-free and
monotone.  They do NOT re-freeze or edit the evaluation benchmark.
"""
from __future__ import annotations

import sys
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PRODUCT_ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from product.query import counter_surface as cs  # noqa: E402
from product.query import counter_surface_known as csk  # noqa: E402
from product.query import known_authorities as ka  # noqa: E402

SOURCE_SHA = "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72"
SLUGS = {
    "rent-default": 9,
    "corporate-criminal-liability": 6,
    "business-judgment-rule": 4,
    "petty-theft-dismissal": 9,
}


def test_fixture_is_the_adopted_spec_subset() -> None:
    fixture = ka.load_fixture()
    assert fixture["schema"] == ka.SCHEMA
    assert fixture["source"]["sha256"] == SOURCE_SHA
    assert set(fixture["questions"]) == set(SLUGS)
    ids = [
        known_id
        for slug in SLUGS
        for known_id in ka.known_ids(fixture, slug)
    ]
    assert len(ids) == 28 and len(set(ids)) == 28
    for slug, expected_n in SLUGS.items():
        assert len(ka.known_ids(fixture, slug)) == expected_n
    assert fixture["_fixture_sha256"]


def test_frozen_alnum_core_rule_matches_legacy_and_atf_ids() -> None:
    assert ka.alnum_core("bger_4A_219_2015") == "4a2192015"
    assert ka.alnum_core("bge_4A 219/2015") == "4a2192015"
    assert ka.matches("bger_4A_219_2015", {"decision_id": "bge_4A 219/2015"})
    assert ka.matches(
        "bge_BGE_142_IV_333",
        {"decision_id": "oclaw_142_IV_333", "citation_string_de": "BGE 142 IV 333"},
    )
    # Repeated leading court tokens are stripped, not one at a time.
    assert ka.alnum_core("bge_BGE_117_II_415") == "117ii415"
    assert ka.alnum_core("BGer_BGE_117_II_415") == "117ii415"
    # A core shorter than the frozen minimum never matches.
    assert not ka.matches("bger_1A", {"decision_id": "1A"})
    assert not ka.matches("", {"decision_id": ""})


def test_measurement_is_network_free_and_monotone() -> None:
    """One cached leg, both budgets, no network: the documented delta holds."""
    out = csk.measure(legs=["rent-default"], caps=[8, 24])
    assert out["schema"] == csk.SCHEMA
    assert "fixture replay" in out["mode"] and "network blocked" in out["mode"]
    assert out["invariants"]["network_calls_blocked"] is True
    assert out["invariants"]["known_signals_monotone_in_cap"] is True
    leg = out["legs"][0]
    assert leg["slug"] == "rent-default"
    assert leg["known_n"] == 9
    assert leg["scans"]["8"]["summary"]["known_signalled_n"] == 2
    assert leg["scans"]["24"]["summary"]["known_signalled_n"] == 2
    assert (leg["scans"]["24"]["summary"]["known_hydrated_n"]
            >= leg["scans"]["8"]["summary"]["known_hydrated_n"])
    assert out["aggregate"]["by_cap"]["24"]["n_signalled_total"] >= \
        out["aggregate"]["by_cap"]["8"]["n_signalled_total"]
    # The external 0/14 reference is context, never this measurement's denominator.
    assert out["external_reference"]["known_n"] == 14
    assert out["aggregate"]["known_n"] == 9


def test_the_mode_aware_budget_keeps_live_at_the_accepted_cap() -> None:
    assert cs.hydration_budget("fixture") == 24
    assert cs.hydration_budget("offline") == 24
    assert cs.hydration_budget("live") == 8
    assert cs.hydration_budget("refresh") == 8
    assert cs.hydration_budget("something-else") == 8
