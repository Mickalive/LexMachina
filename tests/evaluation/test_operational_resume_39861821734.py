"""Shim tests for the operational-resume instrument of run 39861821734.

Runs under evaluation.no_pytest_runner (stdlib only). Each test exercises one
frozen gate or one planted-drift control of
evaluation/operational_resume_39861821734.py; a broken control is a failure.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.getcwd())

from evaluation import operational_resume_39861821734 as inst  # noqa: E402


def test_t1_wrong_run_id_is_exit_2():
    res = inst.run(run_id="00000000000")
    assert res["exit_code"] == 2, res
    assert res["verdict"] == "ENVIRONMENT_OR_VACUOUS", res


def test_t2_freeze_pins_hold():
    r = inst.r3_frozen_and_accepted_pins_hold(os.getcwd())
    assert r["pass"], r["details"]


def test_t3_c1_planted_pin_drift_detected():
    c = inst.c1_planted_pin_drift_detected(os.getcwd())
    assert c["holds"], c


def test_t4_c2_planted_mount_head_flips_r4():
    c = inst.c2_planted_mount_head_flips_r4(os.getcwd())
    assert c["holds"], c


def test_t5_c4_diagnosis_structure_violation_detected():
    c = inst.c4_diagnosis_structure_violation_detected(os.getcwd())
    assert c["holds"], c


def test_t6_c5_planted_state_ref_break_detected():
    c = inst.c5_planted_state_ref_break_detected(os.getcwd())
    assert c["holds"], c


def test_t7_r2_diagnosis_parses_with_recorded_annotations():
    r = inst.r2_orchestration_diagnosis_structured(os.getcwd())
    assert r["pass"], r["details"]


def test_t8_r5_prior_cycle_three_numbers_intact():
    r = inst.r5_prior_cycle_result_integrity(os.getcwd())
    assert r["pass"], r["details"]


def test_t9_r4_all_five_items_adjudicated():
    r = inst.r4_ordered_item_adjudication(os.getcwd())
    verdicts = {k: v["verdict"] for k, v in r["items"].items()}
    assert verdicts["(1)_remedy_a_re_freeze"] == "NOT_TRIGGERED", verdicts
    assert verdicts["(2)_cross_check_next_product_measurement"] == "NOT_TRIGGERED", verdicts
    assert verdicts["(3)_frozen_bars_standing"] == "STANDING_OK", verdicts
    assert verdicts["(4)_p1_fr_divergence_standing"] == "STANDING_OK", verdicts
    assert verdicts["(5)_falsify_new_served_packet"] == "NOT_TRIGGERED", verdicts


def test_t10_r6_state_reconciled():
    r = inst.r6_state_reconciled(os.getcwd())
    assert r["pass"], r["details"]
