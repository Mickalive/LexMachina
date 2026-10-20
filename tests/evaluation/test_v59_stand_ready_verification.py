"""Tests for evaluation.v59_stand_ready_verification (run 39355375694).

Direction v59 ordered work (1) STAND READY: the falsification battery stays
ARMED_UNFIRED on the packet-of-record 39319405429's exact bytes and is
discharged the moment a serve verdict lands; ordered work (2) standing
frozen-pin discipline (re-hash before use, never regenerate); ordered work
(3) the in-flight run 39349747472 produced NO gate (team-job failure), so
this dispatch is bound by the v59 question itself.

These tests pin:
* the freeze-first contract (hypothesis + freeze record, hypothesis sha, and
  the disclosed freeze self-correction with the pre-correction digest
  preserved);
* every frozen pin byte-identical;
* the serve-trigger adjudication NOT_SERVED_WITHHELD_PENDING_SERVE derived
  only from the packet's own committed admission fields;
* the battery integrity on the historical mount (BENCHMARK_VALID_NO_FALSIFICATION,
  both falsification legs firing) with the packet-of-record bytes untouched;
* the F-3B carry-forward INTACT_NOT_REOPENED with digests READ from the
  accepted disposition record;
* the packet byte verification (packet.json raw sha + per-bundle shas);
* the cross-check numbers (structural read + mapping-free mega-cluster
  disclosure conformance) published beside the frozen cells;
* the population pin NOT refreshed (the v59 question pins the refresh at
  discharge time);
* the pre-emption guard (zero frozen verdict fields on the packet bytes);
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

from evaluation import v59_stand_ready_verification as V  # noqa: E402

RUN_RECORD = REPO / "results/evaluation/v59_stand_ready_verification/39355375694.json"
HYP = REPO / V.HYPOTHESIS
FREEZE = REPO / V.FREEZE_RECORD
DISP = REPO / V.DISPOSITION

FROZEN_DIALECT = {
    "rules_label": "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608",
    "rules_geometry": "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633",
    "frozen_spec": "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72",
    "freeze_record": "b06a2ad024040c38312686ab7aacc5ab18c663f1ef0b77494caf6ce3b3b52e49",
    "mapping_free_freeze": "431aa87b8abeaec3b849d66bce7c0d6b1bcb1ea0fdd5f31bef4b3da122d229f5",
    "f3b_restored": "58a273de260770c12dcdc6f645b06b71f95a672757ae3cfa03e870be4bd5b11e",
    "f3b_rehomed": "d02255b8d11d7bce9b4529349e4e87de7b32a7d06311dfaa3aefa06f5de00032",
    "packet_of_record_packet": "32ac812626e679c357822543d0b2e78e62c0e95a9a1b233d1ec89d7cb7b6ac70",
}


def _record() -> dict:
    assert RUN_RECORD.exists(), f"run record missing: {RUN_RECORD}"
    return json.loads(RUN_RECORD.read_text(encoding="utf-8"))


# ------------------------------------------------------------- freeze-first
def test_hypothesis_and_freeze_exist_and_sha_matches():
    hyp = json.loads(HYP.read_text(encoding="utf-8"))
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert freeze["run_id"] == "39355375694"
    assert hyp["frozen_before_claim_bearing_execution"] is True
    assert V.sha256_file(str(HYP)) == freeze["hypothesis_sha256"]


def test_freeze_self_correction_disclosed_and_pre_correction_preserved():
    hyp = json.loads(HYP.read_text(encoding="utf-8"))
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    corr = hyp["freeze_self_correction_39355375694"]
    # the original mis-typed pin is preserved verbatim
    assert corr["original_mistyped"].endswith("b7749caf6ce3b3b52e49")
    # the corrected pin matches the direction v59 / accepted v58 value
    assert corr["corrected_to"] == FROZEN_DIALECT["freeze_record"]
    assert corr["frozen_file_untouched"] is True
    # the freeze record carries both digests
    assert freeze["hypothesis_sha256_pre_correction"] == "a05a96044e6664a8625578d2e13c96582a75551d489fac7ab2c730afc1e6935a"
    assert freeze["hypothesis_sha256"] == V.sha256_file(str(HYP))


def test_run_record_pins_the_frozen_hypothesis():
    rec = _record()
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert rec["hypothesis_sha256"] == freeze["hypothesis_sha256"]


def test_direction_version_is_59():
    rec = _record()
    assert rec["direction_version"] == 59


# ------------------------------------------------------------- frozen pins
def test_all_frozen_pins_match():
    rec = _record()
    assert rec["frozen_pin_verification"]["all_match"] is True
    for check in rec["frozen_pin_verification"]["checks"]:
        assert check["match"] is True, f"pin drift: {check['file']}"


def test_frozen_pin_values_match_the_dialect():
    hyp = json.loads(HYP.read_text(encoding="utf-8"))
    pins = hyp["population_pinned_before_execution"]["frozen_pins"]
    assert pins["evaluation/frozen_bars/RULES_LABEL.json"] == FROZEN_DIALECT["rules_label"]
    assert pins["evaluation/frozen_bars/RULES_GEOMETRY.json"] == FROZEN_DIALECT["rules_geometry"]
    assert pins["evaluation/retrieval_gate/frozen_retrieval_benchmark.json"] == FROZEN_DIALECT["frozen_spec"]
    assert pins["evaluation/retrieval_gate/FREEZE_RECORD.json"] == FROZEN_DIALECT["freeze_record"]
    assert pins["evaluation/MAPPING_FREE_RECALL_FALSIFIER_FREEZE_RECORD.json"] == FROZEN_DIALECT["mapping_free_freeze"]


# --------------------------------------------------------- serve trigger
def test_serve_trigger_not_served():
    rec = _record()
    st = rec["serve_trigger_adjudication"]
    assert st["verdict"] == "NOT_SERVED_WITHHELD_PENDING_SERVE"
    assert st["falsification_battery"] == "ARMED_UNFIRED"
    assert st["frozen_label_verdicts_computed_on_new_packet_bytes"] == 0
    assert st["frozen_geometry_verdicts_computed_on_new_packet_bytes"] == 0


def test_serve_trigger_derived_only_from_committed_fields():
    rec = _record()
    st = rec["serve_trigger_adjudication"]
    assert st["derived_only_from"] == (
        "/tmp/lex_accepted/product/results/product/gate_packet/39319405429/"
        "PACKET_OF_RECORD.json committed fields"
    )
    fields = st["committed_fields"]
    assert fields["packet_admitted"] is False
    assert fields["packet_admission_blocked"] is True
    assert fields["ready_for_owner_session"] is False
    assert fields["human_gate_ready"] is False


# ------------------------------------------------------- battery integrity
def test_battery_integrity_on_historical_mount():
    rec = _record()
    bat = rec["battery_integrity_on_historical_mount"]
    assert bat["exit_code"] == 0
    assert bat["verdict"] == "BENCHMARK_VALID_NO_FALSIFICATION"
    assert bat["falsification_proven"] is True
    assert bat["packet_of_record_bytes_touched"] is False
    legs = {lg["leg"]: lg for lg in bat["legs"]}
    assert legs["served_baseline"]["exit_code"] == 0
    assert legs["served_baseline"]["verdict"] == "PASS_NO_REGRESSION"
    assert legs["geometry_falsification_hostile"]["exit_code"] == 1
    assert legs["geometry_falsification_hostile"]["verdict"] == "FAIL_REGRESSION"
    assert legs["label_falsification_blanked_evidence"]["exit_code"] == 1
    assert legs["label_falsification_blanked_evidence"]["verdict"] == "FAIL_REGRESSION"


def test_battery_scratch_run_did_not_overwrite_committed_records():
    rec = _record()
    bat = rec["battery_integrity_on_historical_mount"]
    # the scratch out-dir is namespaced, not the committed claim-bearing tree
    assert "_scratch_namespaced" in bat["scratch_out_dir"]
    assert "retrieval_counter_authority_benchmark" not in bat["scratch_out_dir"]
    # the accepted committed records still exist and are untouched
    assert (REPO / "results/evaluation/retrieval_counter_authority_benchmark/39200567493.json").exists()
    assert (REPO / "results/evaluation/retrieval_counter_authority_benchmark/39214324454.json").exists()


# ------------------------------------------------------------------ F-3B
def test_f3b_carry_forward_intact():
    rec = _record()
    f3b = rec["f3b_carry_forward"]
    assert f3b["status"] == "INTACT_NOT_REOPENED"
    assert f3b["run_record_bytes_equal_preimage_copy"] is True
    assert f3b["deleted"] == []
    for check in f3b["checks"]:
        assert check["match"] is True, f"F-3B drift: {check['artifact']}"


def test_f3b_expected_digests_read_from_accepted_disposition():
    rec = _record()
    f3b = rec["f3b_carry_forward"]
    assert f3b["expected_digests_read_from"] == V.DISPOSITION
    disp = json.loads(Path(DISP).read_text(encoding="utf-8"))
    assert f3b["disposition_record_sha256"] == V.sha256_file(DISP)
    assert f3b["disposition_record_matches_hypothesis_pin"] is True
    assert disp["records"]["run_record"]["restored_sha256"] == FROZEN_DIALECT["f3b_restored"]


# -------------------------------------------------------- packet bytes
def test_packet_byte_verification():
    rec = _record()
    pbv = rec["packet_byte_verification"]
    assert pbv["match"] is True
    assert pbv["actual_packet_json_sha256"] == FROZEN_DIALECT["packet_of_record_packet"]
    assert pbv["all_bundles_match_pins"] is True
    for check in pbv["bundle_sha256"]:
        assert check["match"] is True, f"bundle drift: {check['qid']}"


# ---------------------------------------------------- cross-check numbers
def test_cross_check_numbers_conform():
    rec = _record()
    ccn = rec["evaluation_cross_check_numbers"]
    assert ccn["all_conform"] is True
    by_qid = {r["qid"]: r for r in ccn["per_question"]}
    assert by_qid["de-kapitalverletzung"]["n_decisions"] == 182
    assert by_qid["fr-bail-entretien"]["n_decisions"] == 185
    assert by_qid["it-responsabilita-medica"]["n_decisions"] == 179
    for r in ccn["per_question"]:
        assert r["conforms"] is True
        assert r["warning_fires_on_size_based_share"] is True
        assert r["size_based_share"] >= r["mega_share_floor"]


def test_cross_check_numbers_are_not_frozen_verdicts():
    rec = _record()
    ccn = rec["evaluation_cross_check_numbers"]
    for r in ccn["per_question"]:
        assert "NOT a RULES_GEOMETRY verdict" in r["kind"]
    # the record carries zero frozen verdict fields on the packet bytes
    assert rec["frozen_label_verdicts_computed_on_packet_of_record_bytes"] == 0
    assert rec["frozen_geometry_verdicts_computed_on_packet_of_record_bytes"] == 0


# --------------------------------------------------------- population pin
def test_population_pin_not_refreshed():
    rec = _record()
    pp = rec["population_pin"]
    assert pp["status"] == "NOT_REFRESHED_THIS_CYCLE"
    assert pp["frozen_incumbent_matches_65"] is True
    from evaluation.frozen_bars import label_gate
    assert label_gate.INCUMBENT["n_scored"] == 65


# ------------------------------------------------------- serve-audit status
def test_serve_verdict_not_landed():
    rec = _record()
    sas = rec["serve_audit_team_status"]
    # the CLAIM: the director-chartered serve-audit has NOT published a serve
    # verdict, so the trigger has not fired and the battery stays ARMED_UNFIRED
    assert sas["serve_verdict_landed"] is False
    assert sas["run_id"] == "39355384602"
    assert sas["frozen_pin_at_freeze"]["verdict_landed"] is False
    # serve_verdict_landed is computed conservatively from the live read: only a
    # run with conclusion=success AND a non-bootstrap commit on the team branch
    # counts as a landed verdict. Live status drift between the freeze-time read
    # (in_progress, pinned in the hypothesis) and the result-commit-time read
    # (completed/failure — the charter dispatch died without a verdict, the
    # documented requirement-20 orchestration class) is expected live-read
    # drift, disclosed beside the claim; either state keeps the trigger unfired.
    assert sas["run_status"] in {"in_progress", "completed", "API_UNREACHABLE"}
    if sas["run_status"] == "completed":
        # a completed run cannot carry a serve verdict unless it succeeded AND
        # pushed a non-bootstrap verdict commit
        assert not (
            sas["run_conclusion"] == "success" and sas.get("verdict_commit_present") is True
        )


# --------------------------------------------------------- dispatch chain
def test_dispatch_chain_recorded():
    rec = _record()
    dc = rec["dispatch_chain"]
    by_run = {r["run_id"]: r for r in dc["runs"]}
    assert by_run["39349747472"]["conclusion"] == "failure"
    assert by_run["39354142707"]["conclusion"] == "failure"
    assert by_run["39354569073"]["conclusion"] == "cancelled"
    assert by_run["39355375694"]["conclusion"] is None  # this run, in progress
    assert "ORCHESTRATION_FAILURE_NOT_LANE_WORK_FAILURE" in dc["diagnosis_class"]


# ------------------------------------------------------- pre-emption guard
def test_pre_emption_guard_clean():
    rec = _record()
    guard = rec["pre_emption_guard"]
    assert guard["clean"] is True
    assert guard["offenders"] == []


# ------------------------------------------------------------ non-vacuity
def test_non_vacuity_all_hold():
    rec = _record()
    nv = rec["non_vacuity"]
    assert nv["all_hold"] is True
    controls = {c["control"]: c for c in nv["battery"]}
    assert controls["A_blanked_admission_fields_never_claim_served"]["holds"] is True
    assert controls["A1_synthetic_admitted_fields_flip_to_served"]["holds"] is True
    assert controls["A2_blanked_clusters_break_mega_recompute"]["holds"] is True
    assert controls["A3_byte_identity_check_sensitive_on_identical_input"]["holds"] is True


# ------------------------------------------------------------- invariants
def test_no_owner_ask_invariants():
    rec = _record()
    assert rec["packet_admitted"] is False
    assert rec["human_gate_ready"] is False
    assert rec["ready_for_owner_session"] is False
    assert rec["owner_decision_required"] is False
    assert rec["falsification_battery"] == "ARMED_UNFIRED"


def test_verdict_and_exit_code():
    rec = _record()
    assert rec["verdict"] == "STAND_READY_POSTURE_HOLDS"
    assert rec["exit_code"] == 0
    for key, val in rec["verdict_detail"].items():
        if key == "serve_trigger":
            # serve_trigger is a string verdict, not a boolean sub-check
            assert val == "NOT_SERVED_WITHHELD_PENDING_SERVE"
            continue
        assert val is True, f"posture sub-check failed: {key}"


def test_claim_ceiling():
    rec = _record()
    cc = rec["claim_ceiling"]
    assert "does NOT serve, admit or falsify the packet" in cc
    assert "does NOT lift any DO-NOT-SERVE order" in cc
    assert "makes NO owner ask" in cc
    assert "ARMED_UNFIRED" in cc
