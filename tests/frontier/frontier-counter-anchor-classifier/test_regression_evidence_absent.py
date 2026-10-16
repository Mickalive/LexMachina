"""Regression: the 16 evidence_absent rows must all come out ABSTAIN.

Charter acceptance test 6: the 16 rows the accepted measurement
(LABEL_HALF.json) records as evidence_absent at counter_uncertainty 0.95-1.0
must all come out ABSTAIN or supported-with-cited-evidence, NEVER an
unevidenced confident label.

The fixture pins the 16 decision_ids, their bundles, their empty cited
evidence and their accepted uncertainty, so the contract is regression-tested
against the accepted record rather than against a re-derived population.
"""

from __future__ import annotations

import json
import os

import pytest

from frontier_counter_anchor_classifier.counter_anchor_classifier import (
    LABEL_ABSTAIN,
    decide_label,
)
from frontier_counter_anchor_classifier.vendored.rules import load_rules

from conftest import RULES_PATH

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "evidence_absent_rows.json")


@pytest.fixture(scope="module")
def rules():
    return load_rules(RULES_PATH)


@pytest.fixture(scope="module")
def evidence_absent_rows():
    with open(FIXTURE, "r", encoding="utf-8") as fh:
        return json.load(fh)["evidence_absent_rows"]


def test_fixture_pins_exactly_the_accepted_16(evidence_absent_rows):
    assert len(evidence_absent_rows) == 16
    for r in evidence_absent_rows:
        assert r["reason_code"] == "evidence_absent"
        assert not r["cited_evidence"], r["decision_id"]
        assert float(r["counter_uncertainty"]) >= 0.95


def _full_row(r):
    """The candidate requires the row's own title and regeste: the frozen
    criterion (v) checks the PIVOT anchor in the cited evidence, the title OR
    the regeste, so a drop-in adapter must pass all three text fields."""
    return {
        "decision_id": r["decision_id"],
        "counter_status": r["counter_status"],
        "counter_evidence": r["cited_evidence"],
        "language": r["language"],
        "rank": r["rank"],
        "title": r.get("title") or "",
        "regeste": r.get("regeste") or "",
    }


def test_all_16_evidence_absent_rows_abstain(rules, evidence_absent_rows):
    for r in evidence_absent_rows:
        profile = rules.anchor_profile(r["bundle"])
        d = decide_label(_full_row(r), rules, profile)
        assert d.label == LABEL_ABSTAIN, r["decision_id"]
        assert d.abstained
        assert d.reason_code == "evidence_absent", r["decision_id"]
        # never an unevidenced confident label
        assert d.uncertainty >= 0.95


def test_the_5_accepted_supported_rows_all_emit(rules):
    """The positive contract: the accepted SUPPORTED rows must emit, not abstain."""
    with open(FIXTURE, "r", encoding="utf-8") as fh:
        supported = json.load(fh)["supported_rows"]
    assert len(supported) == 5
    for r in supported:
        profile = rules.anchor_profile(r["bundle"])
        d = decide_label(_full_row(r), rules, profile)
        assert not d.abstained, r["decision_id"]
        assert d.reason_code == "supported", r["decision_id"]
