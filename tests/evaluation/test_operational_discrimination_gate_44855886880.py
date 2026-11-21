"""Tests for the operational-discrimination gate (evaluation run 44855886880, v68).

These tests verify the instrument's own invariants and that it re-computes the
v68 ordered-work status from committed bytes without re-running any falsifier.
"""
import hashlib
import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MOD_PATH = REPO / "evaluation/operational_discrimination_gate_44855886880.py"
HYP = REPO / "evaluation/OPERATIONAL_DISCRIMINATION_GATE_44855886880_HYPOTHESIS_V1.json"
FRZ = REPO / "evaluation/OPERATIONAL_DISCRIMINATION_GATE_44855886880_FREEZE_V1.json"
RESULT = REPO / "results/evaluation/operational_discrimination_gate/44855886880.json"


def _load_mod():
    spec = importlib.util.spec_from_file_location("odg_44855886880", MOD_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_frozen_artifacts_present_and_digests_match():
    mod = _load_mod()
    hyp = mod.load_json(HYP)
    frz = mod.load_json(FRZ)
    assert _sha(HYP) == frz["hypothesis_sha256_at_freeze"]
    assert hyp["frozen_before_execution"] is True
    assert hyp["run_id"] == frz["run_id"] == "44855886880"
    assert hyp["direction_version"] == frz["direction_version"] == 68


def test_frozen_inputs_and_bars_rehash_identical():
    mod = _load_mod()
    hyp = mod.load_json(HYP)
    pins = dict(hyp["expected_pins_frozen_before_execution"]["frozen_instruments_sha256"])
    pins.update(hyp["expected_pins_frozen_before_execution"]["frozen_bars_sha256"])
    for rel, expected in pins.items():
        assert _sha(REPO / rel) == expected, rel


def test_no_falsifier_import_or_call_in_code():
    mod = _load_mod()
    found = mod.forbidden_references(MOD_PATH.read_text(encoding="utf-8"))
    assert found == [], found


def test_run_verdict_is_operational_no_delta_and_all_claims_hold():
    mod = _load_mod()
    result = mod.run()
    assert result["verdict"] == "OPERATIONAL_NO_DELTA", result["failed_claims"]
    assert result["exit_code"] == 0
    assert result["n_claims"] == 8 and result["n_claims_ok"] == 8
    assert result["n_controls"] == 4 and result["n_controls_holding"] == 4
    assert result["failed_claims"] == [] and result["failed_controls"] == []


def test_item2_precondition_is_14_of_15_not_discriminating():
    mod = _load_mod()
    result = mod.run()
    c5 = next(c for c in result["claim_checks"] if c["id"] == "C5_item2_full_family_still_incomplete")
    assert c5["ok"] is True
    assert c5["observed"]["n_post_repair_server_served"] == 3
    assert c5["observed"]["matched_members"] == 14
    assert c5["observed"]["full_family_precondition"] is False
    assert result["ordered_work_status"]["item_2_protocol"].startswith("NOT EXECUTED")


def test_requirement4_both_halves_and_posture():
    mod = _load_mod()
    result = mod.run()
    c6 = next(c for c in result["claim_checks"] if c["id"] == "C6_requirement4_both_halves")
    assert c6["ok"] is True
    for flag in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                 "ready_for_owner_session", "owner_decision_required", "falsifier_reexecuted"):
        assert result["flags"][flag] is False
    assert result["continuation"]["continue_recommended"] is False


def test_side_by_side_read_from_committed_records():
    mod = _load_mod()
    result = mod.run()
    c7 = next(c for c in result["claim_checks"] if c["id"] == "C7_side_by_side_from_committed_records")
    assert c7["ok"] is True
    assert c7["observed"]["baseline_40105794124"]["n_defective"] == 4
    assert c7["observed"]["post_repair_40258497460"]["n_defective"] == 0
    assert c7["observed"]["post_repair_40258497460"]["n_enriched"] == 49


def test_result_artifact_exists_and_matches_run():
    mod = _load_mod()
    assert RESULT.is_file()
    saved = mod.load_json(RESULT)
    fresh = mod.run()
    assert saved["verdict"] == fresh["verdict"] == "OPERATIONAL_NO_DELTA"
    assert saved["run_id"] == fresh["run_id"] == "44855886880"
    assert saved["claim_checks"] == fresh["claim_checks"]
