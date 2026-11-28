"""Focused gate test for run 46122736362: FAST-MVP recall/counter-authority
falsification on the never-before-measured shipping product head 7be4480e.

This test locks only THIS run's claim-bearing artifacts. It does not edit,
re-derive or weaken any frozen bar, rubric, predicate, k, population or verdict
contract. It is intentionally written in the no-pytest-supported subset.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BASE = REPO / "results/evaluation/fast_mvp_retrieval_recall_benchmark"
RUN = "46122736362"
HEAD = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"


def _j(rel: str) -> dict:
    return json.loads(rel.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_freeze_precedes_and_pins_result() -> None:
    pre = _j(BASE / f"{RUN}_PRE_EXECUTION_PINS.json")
    post = _j(BASE / f"{RUN}_POST_EXECUTION_PINS.json")
    assert pre["direction_version"] == 68
    assert pre["verified_before_execution"] is True
    assert pre["result_file_absent_at_freeze"] is True
    assert pre["all_pins_hold"] is True
    assert pre["product_mount_head"] == HEAD
    assert post["all_hold"] is True
    hyp = REPO / "evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_46122736362_HYPOTHESIS_V1.json"
    frz = REPO / "evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_46122736362_FREEZE_V1.json"
    assert _sha(hyp) == pre["run_hypothesis_sha256"]
    assert _sha(frz) == pre["freeze_record_sha256"]
    assert _j(frz)["run_hypothesis_sha256_at_freeze"] == _sha(hyp)
    assert _j(frz)["run_id"] == RUN and _j(hyp)["run_id"] == RUN


def test_verdict_is_frozen_rule_output_not_a_new_bar() -> None:
    d = _j(BASE / f"{RUN}.json")
    assert d["run_id"] == RUN
    assert d["direction_version"] == 68
    assert d["product_mount_head"] == HEAD
    assert d["frozen_spec_sha256"] == "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72"
    assert d["frozen_hypothesis_sha256"] == "a9fe256cea627c0bbc9ecd8e316f68b00b1911ab4e99bf0c294576b60cafe4f7"
    assert d["no_new_thresholds"] is True
    assert d["no_universal_174k_benchmarks"] is True
    assert d["network_calls"] == 0
    assert d["rehash_before_execution"]["spec_matches_pin"] is True
    assert d["rehash_after_execution"]["spec_unchanged"] is True
    assert d["rehash_after_execution"]["hypothesis_unchanged"] is True
    # The verdict is whatever the frozen rule emitted; we lock it to what was
    # actually measured, we do not assert it "should" be PASS.
    assert d["verdict"] == "PRODUCT_FALSIFIED_RECALL_LOSS"
    assert d["exit_code"] == 1
    assert d["failed_controls"] == []
    assert d["n_controls"] == 10 and d["n_controls_passed"] == 9


def test_comparison_is_honest_confirmation() -> None:
    c = _j(BASE / f"{RUN}_COMPARISON_40261335674.json")
    assert c["new_head"] == HEAD
    assert c["claim_fields_byte_equal_40261335674"] is True
    assert c["per_cell_hits_retentions_differ_count_40261335674"] == 0
    assert c["per_cell_count_new"] == c["per_cell_count_prev"] == 24
    assert c["verdict_equal_all"] is True
    assert c["frozen_pins_equal"]["spec"] is True
    assert c["frozen_pins_equal"]["hypothesis"] is True
    assert "CONFIRMATION" in c["interpretation"]


def test_claim_ceiling_and_fail_closed() -> None:
    d = _j(BASE / f"{RUN}.json")
    assert d["human_gate_ready"] is False
    ceiling = d["claim_ceiling"]
    assert "relative" in ceiling.lower()
    shim = REPO / f"results/evaluation/orchestration/{RUN}_shim_multilingual.json"
    assert _j(shim)["verdict"] == "SHIM_PASS"
    assert _j(shim)["n_failed"] == 0
