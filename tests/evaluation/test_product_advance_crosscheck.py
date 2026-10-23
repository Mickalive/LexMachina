"""Read-only contract tests for the v63 product-advance cross-check.

These tests do NOT execute any claim-bearing leg. They assert that the
freeze-first artifacts exist, that the new re-freezes name the new run id and
the new accepted product bytes, that the accepted inputs are still byte-equal,
and that the wrapper's own non-vacuity controls detect planted drift.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from evaluation import product_advance_crosscheck as pac  # noqa: E402

MOUNT = Path("/tmp/lex_accepted/product")
RUN = "39916358347"
HEAD = "ae854b6a9ff4df4429d36725e364e721cb73096b"


def sha256(path: str) -> str:
    return hashlib.sha256((REPO / path).read_bytes()).hexdigest()


def load(path: str) -> dict:
    return json.loads((REPO / path).read_text(encoding="utf-8"))


def test_hypothesis_and_freeze_agree_on_run_direction_and_head():
    hyp = load(pac.HYPOTHESIS_RELPATH)
    freeze = load(pac.FREEZE_RELPATH)
    assert hyp["run_id_of_record"] == RUN == freeze["run_id_of_record"]
    assert hyp["direction_version"] == 63 == freeze["direction_version"]
    assert hyp["frozen_before_claim_bearing_execution"] is True
    assert freeze["frozen_before_claim_bearing_execution"] is True
    assert freeze["product_mount_head_expected"] == HEAD
    assert freeze["no_thresholds_or_bars_touched"] is True
    assert freeze["no_universal_174k_benchmark"] is True


def test_every_frozen_repo_input_still_rehashes():
    freeze = load(pac.FREEZE_RELPATH)
    rehash = pac.pin_map(REPO, freeze["pins"])
    drifted = [c for c in rehash["checks"] if c["status"] != "ok"]
    assert rehash["all_hold"], drifted


def test_every_new_product_pin_matches_the_accepted_mount():
    freeze = load(pac.FREEZE_RELPATH)
    rehash = pac.pin_map(MOUNT, freeze["product_pins"])
    drifted = [c for c in rehash["checks"] if c["status"] != "ok"]
    assert rehash["all_hold"], drifted


def test_new_product_pins_are_the_expected_advanced_bytes():
    pins = load(pac.FREEZE_RELPATH)["product_pins"]
    assert pins["product/query/pipeline.py"] == (
        "e105bfedc9bf54cb9835369f380e963ccf151d9a75533c734d8419cd94ec631f")
    assert pins["product/query/answer.py"] == (
        "474448ed77a5934a71a71754b55000119c59845f2906c0fa6f08e84e6b3f2316")
    assert pins["product/query/adversarial_retrieval.py"] == (
        "9764a37e8bc7c8c31a329ba15db89657e8ee47dde8ada924fa55d5e755fd06a9")


def test_planner_refreeze_v2_names_new_run_and_new_head():
    freeze = load(pac.PLANNER_V2_FREEZE_RELPATH)
    hyp = load(pac.PLANNER_V2_HYP_RELPATH)
    assert freeze["run_id_of_record"] == RUN == hyp["run_id_of_record"]
    assert freeze["product_mount_head_expected"] == HEAD
    assert freeze["direction_version"] == 63
    assert freeze["pins"][pac.PLANNER_V2_HYP_RELPATH] == sha256(pac.PLANNER_V2_HYP_RELPATH)
    # the V1 accepted result is preserved and pinned, not overwritten
    assert freeze["v1_result_preserved"]["path"] == (
        "results/evaluation/shipped_planner_remedy_verification/39813664201.json")
    assert freeze["v1_result_preserved"]["sha256"] == sha256(
        freeze["v1_result_preserved"]["path"])
    for rel, expected in freeze["pins"].items():
        assert (REPO / rel).is_file(), rel
        assert sha256(rel) == expected, rel
    for rel, expected in freeze["product_pins"].items():
        assert (MOUNT / rel).is_file(), rel
        assert hashlib.sha256((MOUNT / rel).read_bytes()).hexdigest() == expected, rel


def test_degradation_refreeze_v3_names_new_run_new_pins_and_preserves_v1_v2():
    freeze = load(pac.DDC_V3_FREEZE_RELPATH)
    hyp = load(pac.DDC_V3_HYP_RELPATH)
    assert freeze["run_id_of_record"] == RUN == hyp["run_id_of_record"]
    assert freeze["product_mount_head_expected"] == HEAD
    assert freeze["direction_version"] == 63
    assert freeze["product_pins"]["product/query/pipeline.py"] == (
        "e105bfedc9bf54cb9835369f380e963ccf151d9a75533c734d8419cd94ec631f")
    assert freeze["product_pins"]["product/query/answer.py"] == (
        "474448ed77a5934a71a71754b55000119c59845f2906c0fa6f08e84e6b3f2316")
    assert freeze["v1_result_preserved"]["sha256"] == sha256(
        freeze["v1_result_preserved"]["path"])
    assert freeze["v2_result_preserved"]["sha256"] == sha256(
        freeze["v2_result_preserved"]["path"])
    for rel, expected in freeze["pins"].items():
        assert (REPO / rel).is_file(), rel
        assert sha256(rel) == expected, rel


def test_accepted_leg_records_are_byte_pinned_by_the_crosscheck_freeze():
    freeze = load(pac.FREEZE_RELPATH)
    for rel, expected in freeze["pins"].items():
        if rel.startswith("results/evaluation/"):
            assert sha256(rel) == expected, rel


def test_wrong_run_id_is_exit_2_and_writes_nothing(tmp_path):
    out = tmp_path / "out"
    report = tmp_path / "report"
    code, rec = pac.run("39999999999", MOUNT, out, report)
    assert code == 2
    assert rec["verdict"] == "ENVIRONMENT_OR_VACUOUS"
    assert rec["exit_code"] == 2
    assert not out.exists()
    assert not report.exists()


def test_leg_records_do_not_collide_and_live_in_accepted_namespaces():
    a = pac.leg_a_engine_path(RUN)
    b = pac.leg_b_record_path(RUN)
    c = pac.leg_c_record_path(RUN)
    assert a != b != c != a
    assert a.parent.name == "mapping_free_recall_falsifier"
    assert b.parent.name == "shipped_planner_remedy_verification"
    assert c.parent.name == "degradation_disclosure_crosscheck"
    assert a.name == f"{RUN}_engine_mapping_free_recall_falsifier.json"
    assert b.name == f"{RUN}.json" and c.name == f"{RUN}.json"


def test_planted_product_pin_drift_is_detected():
    freeze = load(pac.FREEZE_RELPATH)
    ctrl = pac.control_pin_drift_detected(MOUNT, freeze["product_pins"])
    assert ctrl["holds"] is True and ctrl["detected"] is True


def test_planted_bundle_hash_mismatch_is_detected():
    accepted = load(pac.ACCEPTED_A_RELPATH)
    hashes = pac.bundle_hashes(accepted)
    assert hashes
    ctrl = pac.control_bundle_mismatch_detected(hashes)
    assert ctrl["holds"] is True and ctrl["detected"] is True


def test_bundle_hash_comparison_is_exact():
    accepted = load(pac.ACCEPTED_A_RELPATH)
    hashes = pac.bundle_hashes(accepted)
    same = pac.compare_bundle_hashes(hashes, hashes)
    assert same["identical"] is True
    mutated = dict(hashes)
    key = sorted(mutated)[0]
    mutated[key] = "0" * 64
    diff = pac.compare_bundle_hashes(hashes, mutated)
    assert diff["identical"] is False
    assert any(row["qid"] == key and not row["identical"] for row in diff["questions"])


def test_orchestration_diagnosis_is_zero_delta_and_bounded():
    freeze = load(pac.FREEZE_RELPATH)
    diag = pac.orchestration_diagnosis(freeze)
    assert diag["conclusion"] == "ZERO_DELTA_ORCHESTRATION_FAILURE"
    facts = diag["facts"]
    assert facts["snapshot_team_ref_local"] == (
        "81b4f13151bcf95043360e01b4f073664a0eef2b")
    assert facts["snapshot_equals_prior_run_snapshot"] is True
    assert facts["snapshot_equals_accepted_tip"] is False
    assert facts["audit_ref_present"] is False
    assert "NOT a validation verdict" in diag["assessment"]


def test_freezes_carry_no_serve_or_admission_claim():
    freeze = load(pac.FREEZE_RELPATH)
    ceiling = freeze["claim_ceiling"].lower()
    assert "not a serve recommendation" in ceiling
    assert "admission stays fail-closed" in ceiling
    assert "reported-only and unmet" in ceiling
    assert freeze["no_universal_174k_benchmark"] is True


def test_seq3_claim_bearing_record_is_complete_and_conservative():
    path = REPO / "results/evaluation/product_advance_crosscheck/39916358347.json"
    rec = json.loads(path.read_text(encoding="utf-8"))
    assert rec["verdict"] == "PRODUCT_STILL_FALSIFIED_WITH_DELIVERABLE_DRIFT"
    assert rec["exit_code"] == 1
    assert rec["product_mount_head_before"] == rec["product_mount_head_after"] == HEAD
    assert rec["product_head_matches_expected"] is True
    a = rec["legs"]["A_mapping_free_falsification"]
    assert a["exit_code"] == 1 and a["verdict"] == "PRODUCT_FALSIFIED"
    assert a["failed_gates_equal_accepted_set"] is True
    assert set(a["failed_gates"]) == pac.ACCEPTED_A_FAILED_GATES
    assert a["non_vacuity_all_hold"] is True
    assert a["input_drift"] == []
    assert a["bundle_byte_identity"]["identical"] is True
    accepted = pac.bundle_hashes(load(pac.ACCEPTED_A_RELPATH))
    for row in a["bundle_byte_identity"]["questions"]:
        assert row["new"] == accepted[row["qid"]]
    assert rec["legs"]["B_shipped_planner_remedy"]["exit_code"] == 0
    assert rec["legs"]["C_degradation_disclosure"]["exit_code"] == 0
    assert rec["legs"]["D_coverage_remediation_pins"]["exit_code"] == 0
    e = rec["legs"]["E_answer_reliability_currency"]
    assert e["exit_code"] == 1
    assert e["verdict"] == "RELIABILITY_MEASUREMENT_STALE_ON_PRODUCT_ADVANCE"
    assert e["measurement_artifact_pins_ok"] is True
    assert set(e["drifting_product_sources"]) == {
        "product/query/answer.py", "product/query/pipeline.py"}
    assert all(c["holds"] for c in rec["controls"].values())
    assert rec["control_failures"] == []
    assert rec["pins_before"]["all_hold"] and rec["pins_after"]["all_hold"]
    assert rec["human_gate_ready"] is False
    assert rec["machine_gate_ready"] is False
    assert rec["packet_admitted"] is False
    assert rec["ready_for_owner_session"] is False
    assert rec["no_174k_benchmark_rerun"] is True


def test_seq3_record_pins_the_freeze_that_was_committed_before_execution():
    rec = load("results/evaluation/product_advance_crosscheck/39916358347.json")
    assert rec["freeze_record"]["sha256"] == sha256(pac.FREEZE_RELPATH)
    assert rec["hypothesis"]["sha256"] == sha256(pac.HYPOTHESIS_RELPATH)
    assert rec["instrument"]["sha256"] == sha256("evaluation/product_advance_crosscheck.py")


def test_attempt_records_are_preserved_and_disclaim_a_product_verdict():
    for rel, verdict in (
        ("results/evaluation/product_advance_crosscheck/39916358347_attempt1_output_path_and_env_bug.json",
         "ENVIRONMENT_OR_VACUOUS"),
        ("results/evaluation/product_advance_crosscheck/39916358347_attempt2_wrapper_control_path_bug.json",
         "ENVIRONMENT_OR_VACUOUS"),
    ):
        rec = load(rel)
        assert rec["verdict"] == verdict
        assert rec["exit_code"] == 2
        freeze = load(pac.FREEZE_RELPATH)
        assert rel in freeze["pins"]
        assert freeze["pins"][rel] == sha256(rel)


def test_standalone_orchestration_diagnosis_matches_the_record():
    rec = load("results/evaluation/product_advance_crosscheck/39916358347.json")
    diag = load("results/evaluation/orchestration/39915124469_diagnosis.json")
    assert diag["conclusion"] == rec["orchestration_diagnosis"]["conclusion"]
    assert diag["facts"] == rec["orchestration_diagnosis"]["facts"]
    assert diag["diagnosed_run"] == "39915124469"
    assert diag["facts"]["snapshot_equals_prior_run_snapshot"] is True
    assert diag["facts"]["audit_ref_present"] is False
