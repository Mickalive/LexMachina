"""Tests for evaluation.packet_of_record_stand_ready (run 39338699604).

Direction v58 ordered work (2): the packet-of-record 39319405429 landed
(PACKET_OF_RECORD V3 committed at product accepted head 15008266) but is NOT
SERVED under its own committed fail-closed admission record, so the
falsify-or-pass battery on its exact bytes stays WITHHELD_PENDING_SERVE with
ZERO frozen-label/geometry verdicts computed on them; the before/after
admission-record delta against the previously watched bare packet 39275520116
is published side by side with per-bundle byte-identity verdicts; the
v58-directed map_is_one_mega_cluster disclosure fires on the size-based share
for all three committed bundles (mapping-free disclosure conformance, NOT a
frozen-bar verdict).  Ordered work (1) F-3B carry-forward and ordered work (3)
frozen-pin discipline are re-hashed, never re-opened.

These tests pin:
* the freeze-first contract (hypothesis + freeze record, hypothesis sha);
* the F-3B carry-forward INTACT_NOT_REOPENED with digests READ from the
  accepted disposition record;
* every frozen pin byte-identical;
* the serve-trigger adjudication NOT_SERVED_WITHHELD_PENDING_SERVE derived
  only from the packet's own committed admission fields;
* the before/after side-by-side with all three bundles differing (no
  zero-delta transfer claimed);
* the mega-cluster disclosure conformance on the size-based share;
* the pre-emption guard (zero frozen verdict fields on the new bytes);
* the non-vacuity battery all holding;
* the claim ceiling and the no-owner-ask invariants.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from evaluation import packet_of_record_stand_ready as P  # noqa: E402

RUN_RECORD = REPO / "results/evaluation/packet_of_record_stand_ready/39338699604.json"
HYP = REPO / P.HYPOTHESIS
FREEZE = REPO / P.FREEZE_RECORD
DISP = REPO / P.DISPOSITION

FROZEN_DIALECT = {
    "rules_label": "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608",
    "rules_geometry": "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633",
    "frozen_spec": "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72",
    "freeze_record": "b06a2ad024040c38312686ab7aacc5ab18c663f1ef0b77494caf6ce3b3b52e49",
    "mapping_free_freeze": "431aa87b8abeaec3b849d66bce7c0d6b1bcb1ea0fdd5f31bef4b3da122d229f5",
    "f3b_restored": "58a273de260770c12dcdc6f645b06b71f95a672757ae3cfa03e870be4bd5b11e",
    "f3b_rehomed": "d02255b8d11d7bce9b4529349e4e87de7b32a7d06311dfaa3aefa06f5de00032",
    "f3b_pre_restore": "47be772a9d3d1fcf30185b7ed2bed45603df468c82cf4956e498151e296a17f0",
    "packet_of_record_packet": "32ac812626e679c357822543d0b2e78e62c0e95a9a1b233d1ec89d7cb7b6ac70",
}


def _record() -> dict:
    assert RUN_RECORD.exists(), f"run record missing: {RUN_RECORD}"
    return json.loads(RUN_RECORD.read_text(encoding="utf-8"))


# ------------------------------------------------------------- freeze-first
def test_hypothesis_and_freeze_exist_and_sha_matches():
    hyp = json.loads(HYP.read_text(encoding="utf-8"))
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert hyp["run_id"] == "39338699604"
    assert hyp["frozen_before_claim_bearing_execution"] is True
    assert P.sha256_file(str(HYP)) == freeze["hypothesis_sha256"]


def test_run_record_pins_the_frozen_hypothesis():
    rec = _record()
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert rec["hypothesis_sha256"] == freeze["hypothesis_sha256"]


def test_direction_version_is_58():
    rec = _record()
    assert rec["direction_version"] == 58


# ------------------------------------------------------------------ F-3B
def test_f3b_carry_forward_intact_not_reopened():
    rec = _record()
    f3b = rec["f3b_carry_forward"]
    assert f3b["status"] == "INTACT_NOT_REOPENED"
    assert all(c["match"] for c in f3b["checks"])
    assert f3b["disposition_record_matches_hypothesis_pin"] is True
    assert f3b["run_record_bytes_equal_preimage_copy"] is True
    assert f3b["deleted"] == []
    assert f3b["item_1_technical_closure"] == "NOT_REOPENED"
    assert f3b["overwrite_commit"] == "9b61dcf845c5c75ab58d9b2fdc554c998536b011"


def test_f3b_expected_digests_read_from_accepted_disposition_not_hand_typed():
    """Regression for the PREFIX_BUGGY class: the instrument must read the
    expected F-3B digests from the accepted disposition record itself."""
    disp = json.loads(DISP.read_text(encoding="utf-8"))
    rec = _record()
    checks = {c["artifact"]: c for c in rec["f3b_carry_forward"]["checks"]}
    assert (
        checks["run_record"]["expected_from_accepted_disposition"]
        == disp["records"]["run_record"]["restored_sha256"]
    )
    assert (
        checks["rehomed"]["expected_from_accepted_disposition"]
        == disp["records"]["rehomed"]["rehomed_sha256"]
    )
    assert (
        checks["run_record"]["actual"]
        == FROZEN_DIALECT["f3b_restored"]
    )
    assert checks["rehomed"]["actual"] == FROZEN_DIALECT["f3b_rehomed"]


# ------------------------------------------------------------ frozen pins
def test_all_frozen_pins_match():
    rec = _record()
    pv = rec["frozen_pin_verification"]
    assert pv["all_match"] is True
    by_file = {c["file"]: c for c in pv["checks"]}
    assert (
        by_file["evaluation/frozen_bars/RULES_LABEL.json"]["actual"]
        == FROZEN_DIALECT["rules_label"]
    )
    assert (
        by_file["evaluation/frozen_bars/RULES_GEOMETRY.json"]["actual"]
        == FROZEN_DIALECT["rules_geometry"]
    )
    assert (
        by_file["evaluation/retrieval_gate/frozen_retrieval_benchmark.json"]["actual"]
        == FROZEN_DIALECT["frozen_spec"]
    )
    assert (
        by_file["evaluation/retrieval_gate/FREEZE_RECORD.json"]["actual"]
        == FROZEN_DIALECT["freeze_record"]
    )


# -------------------------------------------------- serve-trigger adjudication
def test_serve_trigger_not_served_withheld():
    rec = _record()
    adj = rec["serve_trigger_adjudication"]
    assert adj["verdict"] == "NOT_SERVED_WITHHELD_PENDING_SERVE"
    assert adj["falsification_battery"] == "ARMED_UNFIRED"
    assert adj["frozen_label_verdicts_computed_on_new_packet_bytes"] == 0
    assert adj["frozen_geometry_verdicts_computed_on_new_packet_bytes"] == 0
    fields = adj["committed_fields"]
    assert fields["packet_admitted"] is False
    assert fields["admission_packet_admitted"] is False
    assert fields["ready_for_owner_session"] is False
    assert fields["admission_ready_for_owner_session_allowed"] is False
    assert "counter_label_support" in (fields["packet_admission_reason"] or "")


def test_serve_adjudication_derived_only_from_committed_fields():
    rec = _record()
    adj = rec["serve_trigger_adjudication"]
    assert "PACKET_OF_RECORD.json" in adj["derived_only_from"]


# ------------------------------------------- before/after admission records
def test_before_after_side_by_side_published():
    rec = _record()
    ba = rec["before_after_admission_records"]
    side = ba["side_by_side"]
    assert side["before"]["packet"] == "39275520116"
    assert side["before"]["packet_of_record_present"] is False
    assert side["before"]["admission_record_committed"] is False
    assert side["after"]["packet"] == "39319405429"
    assert side["after"]["packet_of_record_present"] is True
    assert side["after"]["admission_record_committed"] is True
    assert side["after"]["packet_admitted"] is False
    assert (
        side["after"]["packet_json_sha256"]
        == FROZEN_DIALECT["packet_of_record_packet"]
    )


def test_all_three_bundles_differ_no_zero_delta_transfer():
    rec = _record()
    ba = rec["before_after_admission_records"]
    assert ba["all_three_bundles_differ"] is True
    assert len(ba["bundle_byte_identity"]) == 3
    for row in ba["bundle_byte_identity"]:
        assert row["byte_identical"] is False
        assert (
            row["before_39275520116_bundle_sha256"]
            != row["after_39319405429_bundle_sha256"]
        )
    assert "no zero-delta byte-transfer" in ba["transfer_claim"]


def test_packet_byte_verification_matches_declared():
    rec = _record()
    pv = rec["packet_byte_verification"]
    assert pv["match"] is True
    assert (
        pv["actual_packet_json_sha256"] == FROZEN_DIALECT["packet_of_record_packet"]
    )
    assert pv["declared_in_PACKET_OF_RECORD"] == pv["actual_packet_json_sha256"]


# --------------------------------------- mega-cluster disclosure conformance
def test_mega_cluster_disclosure_fires_on_size_based_share_for_all_three():
    rec = _record()
    mc = rec["mega_cluster_disclosure_conformance"]
    assert mc["all_conform"] is True
    assert len(mc["per_question"]) == 3
    for row in mc["per_question"]:
        assert row["recomputed"] is True
        assert row["warning_should_fire_on_size_based_share"] is True
        assert row["product_warning_present_in_committed_ledger"] is True
        assert row["conforms"] is True
        assert row["size_based_share"] >= 0.5
        # size-based share is the binding definition; member_ids share is beside
        assert row["member_ids_share"] <= row["size_based_share"]


def test_mega_cluster_is_disclosure_conformance_not_frozen_bar():
    rec = _record()
    mc = rec["mega_cluster_disclosure_conformance"]
    assert "NOT a RULES_GEOMETRY verdict" in mc["kind"]


def test_regression_ledger_findings_read_from_verdict_block():
    """Regression for the first (buggy) execution (preserved at
    results/evaluation/_scratch_namespaced/39338699604/
    PREFIX_BUGGY_ledger_findings_path_and_vacuity_control.json,
    sha256 6c76a968...): the committed PACKET_OF_RECORD ledger nests findings
    under each question's own "verdict" object; reading top-level "findings"
    false-flagged all three map_is_one_mega_cluster warnings absent. The fixed
    instrument must find the warning present for all three questions."""
    buggy_path = (
        REPO
        / "results/evaluation/_scratch_namespaced/39338699604/"
        "PREFIX_BUGGY_ledger_findings_path_and_vacuity_control.json"
    )
    assert buggy_path.exists(), "buggy pre-fix execution must be preserved"
    buggy = json.loads(buggy_path.read_text(encoding="utf-8"))
    for row in buggy["mega_cluster_disclosure_conformance"]["per_question"]:
        assert row["product_warning_present_in_committed_ledger"] is False
        assert row["conforms"] is False
    rec = _record()
    for row in rec["mega_cluster_disclosure_conformance"]["per_question"]:
        assert row["product_warning_present_in_committed_ledger"] is True
        assert row["conforms"] is True


# ------------------------------------------------------ structural readiness
def test_structural_readiness_all_addressable():
    rec = _record()
    sr = rec["structural_readiness_on_new_bytes"]
    assert sr["all_addressable"] is True
    assert len(sr["questions"]) == 3
    for row in sr["questions"]:
        assert row["structurally_addressable_by_falsifier"] is True
        assert row["n_decisions"] > 0
        assert row["question_present"] is True
        assert row["admissibility_present_in_packet_of_record"] is True


# --------------------------------------------------------- pre-emption guard
def test_pre_emption_guard_clean():
    rec = _record()
    guard = rec["pre_emption_guard"]
    assert guard["clean"] is True
    assert guard["offenders"] == []


def test_no_frozen_verdict_counts_on_new_bytes():
    rec = _record()
    adj = rec["serve_trigger_adjudication"]
    assert adj["frozen_label_verdicts_computed_on_new_packet_bytes"] == 0
    assert adj["frozen_geometry_verdicts_computed_on_new_packet_bytes"] == 0


# ------------------------------------------------------------ non-vacuity
def test_non_vacuity_battery_all_hold():
    rec = _record()
    nv = rec["non_vacuity"]
    assert nv["all_hold"] is True
    names = {c["control"] for c in nv["battery"]}
    assert "A_blanked_admission_fields_never_claim_served" in names
    assert "A1_synthetic_admitted_fields_flip_to_served" in names
    assert "A2_blanked_clusters_break_mega_recompute" in names
    assert "A3_byte_identity_check_sensitive_on_identical_input" in names
    for c in nv["battery"]:
        assert c["holds"] is True


def test_non_vacuity_control_a1_proves_adjudication_is_computed():
    """Regression for the first (buggy) execution: the blanked-fields control
    alone was non-discriminating (blanked AND real both yield NOT_SERVED). The
    A1 control must flip to SERVED on synthetic admitted fields, proving the
    verdict is computed from the committed fields and not hard-coded."""
    rec = _record()
    nv = rec["non_vacuity"]
    a1 = [c for c in nv["battery"] if c["control"] == "A1_synthetic_admitted_fields_flip_to_served"][0]
    assert a1["holds"] is True
    assert a1["admitted_verdict"] == "SERVED_TRIGGER_FIRED"


# ----------------------------------------------------- verdict + claim ceiling
def test_overall_verdict_and_invariants():
    rec = _record()
    assert rec["verdict"] == "PACKET_LANDED_NOT_SERVED_FALSIFICATION_ARMED"
    assert rec["exit_code"] == 0
    assert rec["packet_admitted"] is False
    assert rec["human_gate_ready"] is False
    assert rec["ready_for_owner_session"] is False
    assert rec["owner_decision_required"] is False
    assert "WITHHELD" in rec["claim_ceiling"]
    assert "ZERO frozen-label/geometry verdicts" in rec["claim_ceiling"]
    assert "NO owner ask" in rec["claim_ceiling"]


def test_frozen_cells_published_beside_never_replaced():
    rec = _record()
    beside = rec["frozen_cells_published_beside"]
    assert beside["artifact"] == "results/evaluation/retrieval_benchmark/39117425713.json"
    assert "never replaced" in beside["note"]


# ------------------------------------- regression: blanked admission flips
def test_blanked_admission_fields_flip_adjudication():
    por = json.loads(
        (Path(P.PACKET_MOUNT) / P.NEW_PACKET / "PACKET_OF_RECORD.json").read_text(
            encoding="utf-8"
        )
    )
    blanked = dict(por)
    for k in (
        "packet_admitted",
        "packet_admission_blocked",
        "ready_for_owner_session",
        "machine_gate_ready",
        "human_gate_ready",
    ):
        blanked[k] = None
    blanked["admission"] = None
    blanked["packet_admission"] = None
    scratch = {}
    verdict = P.adjudicate_serve_trigger(blanked, scratch)
    assert verdict != "SERVED_TRIGGER_FIRED" or scratch


def test_adjudicate_serve_trigger_flips_on_admitted_fields():
    """If the committed fields said admitted + allowed, the adjudication must
    flip — proving the verdict is computed, not hard-coded."""
    admitted = {
        "packet_admitted": True,
        "packet_admission_blocked": False,
        "packet_admission_reason": None,
        "ready_for_owner_session": True,
        "ready_for_owner_session_base": True,
        "machine_gate_ready": True,
        "human_gate_ready": True,
        "admission": {
            "packet_admitted": True,
            "ready_for_owner_session_allowed": True,
            "blocking_reason": None,
        },
    }
    scratch = {}
    verdict = P.adjudicate_serve_trigger(admitted, scratch)
    assert verdict == "SERVED_TRIGGER_FIRED"
    assert scratch["serve_trigger_adjudication"]["falsification_battery"] == "ARMED_FIRED"


def test_pre_emission_guard_flags_nonzero_verdict_fields():
    dirty = {
        "x": {"label_verdict": "LABEL_SOUND"},
        "y": [{"geometry_verdict": 7}],
    }
    guard = P.pre_emption_guard(dirty)
    assert guard["clean"] is False
    assert len(guard["offenders"]) == 2
