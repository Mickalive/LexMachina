"""Packet admission: the accepted frozen bars as a machine gate (v50 obligation 1).

Why this module exists
----------------------
Factory direction v50, product obligation (1): the two accepted bar verdicts
(counter-label support against the frozen absolute bar, map geometry against the
frozen all-11 bar) must be a machine-readable input of packet admission, so no
packet, owner card, disclosure or state field can carry
``ready_for_owner_session=true`` or ``human_gate_ready=true`` while either bar
is unmet.

The binding accepted measurement (``frontier-served-packet-falsification``,
team run 38880639079) is 5/65 = 0.0769 label support and 0/3 bundles passing all
11 geometry criteria.  These tests pin that admission DENIES, that the reason
names those exact numbers, and — as a positive control — that admission OPENS
when both bars are satisfied, so the gate is not a constant ``False``.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from product.query import packet_admission as pa  # noqa: E402


def _falsification_snapshot(label_supported: int = 5, label_scored: int = 65,
                            geometry_pass: int = 0, geometry_bundles: int = 3) -> dict:
    return {
        "team_run_id": "38880639079",
        "measured_packet": "gate_packet/38839347028 (the packet that will be served)",
        "label_half": {
            "verdict": "LABEL_SOUND" if label_supported == label_scored else "LABEL_UNSOUND",
            "n_scored": label_scored,
            "n_supported": label_supported,
            "support_rate": label_supported / label_scored,
        },
        "geometry_half": {
            "verdict": "PASS" if geometry_pass == geometry_bundles else "FAIL",
            "n_bundles_pass": geometry_pass,
            "n_bundles": geometry_bundles,
            "pass_counts": {"de": 6, "fr": 5, "it": 5},
        },
    }


def test_current_accepted_verdicts_deny_admission():
    adm = pa.assess()
    assert adm["packet_admitted"] is False
    assert adm["ready_for_owner_session_allowed"] is False
    assert "5/65" in adm["blocking_reason"]
    assert "0/3" in adm["blocking_reason"]
    assert adm["bars"]["counter_label"]["satisfied"] is False
    assert adm["bars"]["map_geometry"]["satisfied"] is False


def test_binding_measurement_is_the_served_packet_not_the_older_pre_fix_one():
    adm = pa.assess()
    label = adm["bars"]["counter_label"]["binding_measurement"]
    assert label["n_scored"] == 65 and label["n_supported"] == 5
    assert label["measured_packet"].startswith("gate_packet/")
    geometry = adm["bars"]["map_geometry"]["binding_measurement"]
    assert geometry["n_bundles_pass"] == 0 and geometry["n_bundles"] == 3


def test_denied_admission_blocks_owner_readiness_and_keeps_the_base_auditable():
    summary = {"ready_for_owner_session": True}
    adm = pa.enforce(summary, admission=pa.assess())
    assert adm["packet_admitted"] is False
    assert summary["ready_for_owner_session"] is False
    assert summary["ready_for_owner_session_base"] is True  # the hold-back is visible
    assert summary["packet_admission_blocked"] is True
    assert summary["packet_admission_reason"]


def test_admission_opens_when_both_frozen_bars_are_met():
    """Positive control: the gate is not a constant False."""
    snap = _falsification_snapshot(label_supported=65, label_scored=65,
                                   geometry_pass=3, geometry_bundles=3)
    adm = pa.assess(snapshots=[("synthetic", snap)])
    assert adm["packet_admitted"] is True
    assert adm["ready_for_owner_session_allowed"] is True
    assert adm["blocking_reason"] is None


def test_any_single_unsupported_label_denies_even_at_high_support():
    """The label bar is ABSOLUTE: 64/65 is still a denial."""
    snap = _falsification_snapshot(label_supported=64, label_scored=65,
                                   geometry_pass=3, geometry_bundles=3)
    adm = pa.assess(snapshots=[("synthetic", snap)])
    assert adm["packet_admitted"] is False
    assert adm["bars"]["counter_label"]["satisfied"] is False


def test_two_of_three_geometry_bundles_denies():
    snap = _falsification_snapshot(label_supported=65, label_scored=65,
                                   geometry_pass=2, geometry_bundles=3)
    adm = pa.assess(snapshots=[("synthetic", snap)])
    assert adm["packet_admitted"] is False
    assert adm["bars"]["map_geometry"]["satisfied"] is False


def test_missing_evidence_fails_closed():
    adm = pa.assess(snapshots=[])
    assert adm["packet_admitted"] is False
    assert adm["blocking_reason"] == "no_accepted_bar_verdict"


def test_enforce_preserves_an_already_false_flag():
    summary = {"ready_for_owner_session": False}
    pa.enforce(summary, admission=pa.assess())
    assert summary["ready_for_owner_session"] is False
    assert summary["ready_for_owner_session_base"] is False
    assert summary["packet_admission_blocked"] is True


def test_offending_owner_claims_reports_fields_while_denied():
    adm = pa.assess()
    # precondition: current admission is denied
    assert adm["ready_for_owner_session_allowed"] is False
    found = pa.offending_owner_claims(
        {"ready_for_owner_session": True, "human_gate_ready": True,
         "packet_admitted": False}, admission=adm)
    assert set(found) == {"ready_for_owner_session", "human_gate_ready"}


def test_offending_owner_claims_is_clean_on_a_non_claiming_record():
    adm = pa.assess()
    assert pa.offending_owner_claims(
        {"ready_for_owner_session": False, "human_gate_ready": False}, admission=adm
    ) == []


def test_offending_owner_claims_is_empty_when_admitted():
    snap = _falsification_snapshot(65, 65, 3, 3)
    adm = pa.assess(snapshots=[("synthetic", snap)])
    assert pa.offending_owner_claims(
        {"ready_for_owner_session": True, "human_gate_ready": True}, admission=adm
    ) == []


def test_frozen_bars_are_not_tunable_in_this_module():
    assert pa.FROZEN_LABEL_BAR == 1.0
    assert pa.FROZEN_GEOMETRY_CRITERIA == 11
    assert pa.FROZEN_LABEL_RULES_SHA256.startswith("4457e971")
    assert pa.FROZEN_GEOMETRY_RULES_SHA256.startswith("a7452748")
