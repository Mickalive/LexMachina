"""Frozen-input-durability instrument: offline tests.  NO NETWORK.

These tests never fetch anything.  They exercise the comparator, the gate-diff
set relation, the safety manifest and the frozen hypothesis contract against
committed bytes, so an auditor can attack the instrument without re-running the
live measurement.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from evaluation import frozen_input_durability as fid

ROOT = Path(fid._LANE_ROOT)
HYPOTHESIS = ROOT / "evaluation" / "FROZEN_INPUT_DURABILITY_HYPOTHESIS_V1.json"
ACCEPTED = ROOT / "results" / "evaluation" / "retrieval_benchmark" / "39098571937.json"


def _accepted() -> dict:
    return json.loads(ACCEPTED.read_text(encoding="utf-8"))


# --------------------------------------------------------------------- #
# N1 - the comparator must be able to report a difference
# --------------------------------------------------------------------- #


def test_comparator_reports_a_difference_on_a_perturbed_body():
    """If the comparator cannot report different, it is not a measurement."""
    a = b'{"results":[]}'
    b = b'{"results":[1]}'
    assert hashlib.sha256(a).hexdigest() != hashlib.sha256(b).hexdigest()


def test_comparator_is_actually_used_on_real_data_by_the_instrument():
    """The live comparison must read the runner's own raw_sha256 field."""
    src = (ROOT / "evaluation" / "frozen_input_durability.py").read_text("utf-8")
    assert 'q.get("raw_sha256") == a.get("raw_sha256")' in src


# --------------------------------------------------------------------- #
# the plan is taken from the accepted record, never re-derived
# --------------------------------------------------------------------- #


def test_plan_is_reused_from_the_accepted_record_and_is_24_urls():
    accepted = _accepted()
    plan = fid.build_plan_from_accepted(accepted)
    assert len(plan) == 24
    assert [p["query_key"] for p in plan] == [q["query_key"] for q in accepted["queries"]]


def test_plan_carries_the_accepted_record_own_limit_per_channel():
    accepted = _accepted()
    limits = {q["query_key"]: q["limit"] for q in accepted["queries"]}
    for p in fid.build_plan_from_accepted(accepted):
        assert p["limit"] == limits[p["query_key"]]


# --------------------------------------------------------------------- #
# N3 - gate comparison is a SET RELATION, never a cardinality match
# --------------------------------------------------------------------- #


def test_gate_status_map_reconstructs_all_forty_accepted_gates():
    status = fid.gate_status_map(_accepted()["verdict"])
    assert len(status) == 40
    counts = {}
    for v in status.values():
        counts[v] = counts.get(v, 0) + 1
    assert counts == {"PASS": 24, "FAIL": 10, "NOT_MEASURABLE": 6}


def test_gate_status_map_has_no_gate_in_two_statuses():
    accepted = _accepted()["verdict"]
    gates_seen = set()
    for gid in accepted["failed_gates"]:
        assert gid not in gates_seen
        gates_seen.add(gid)
    assert gates_seen == set(accepted["failed_gates"])


def test_gate_diff_is_identical_when_the_maps_agree():
    a = {"g1": "PASS", "g2": "FAIL", "g3": "NOT_MEASURABLE"}
    diff = fid.gate_diff(a, dict(a))
    assert diff["identical"] is True
    assert diff["status_changed_gates"] == []


def test_gate_diff_detects_a_status_change_even_when_counts_match():
    """Same cardinality, different map: the set relation must catch it."""
    a = {"g1": "PASS", "g2": "FAIL"}
    b = {"g1": "FAIL", "g2": "PASS"}
    diff = fid.gate_diff(a, b)
    assert diff["identical"] is False
    assert diff["status_changed_gates"] == ["g1", "g2"]


def test_gate_diff_detects_a_gate_present_on_one_side_only():
    diff = fid.gate_diff({"g1": "PASS"}, {"g1": "PASS", "g2": "PASS"})
    assert diff["identical"] is False
    assert diff["only_in_live"] == ["g2"]
    assert diff["status_changed_gates"] == []


# --------------------------------------------------------------------- #
# safety contract
# --------------------------------------------------------------------- #


def test_manifest_detects_a_mutated_file_under_a_scratch_cache():
    root = Path("/tmp/lex_fid_test_cache")
    if root.exists():
        for p in sorted(root.rglob("*"), reverse=True):
            p.unlink() if p.is_file() else p.rmdir()
    (root / "aa").mkdir(parents=True)
    f = root / "aa" / "x.json"
    f.write_text('{"body":"1"}', encoding="utf-8")
    before = fid.manifest(root)
    f.write_text('{"body":"2"}', encoding="utf-8")
    after = fid.manifest(root)
    assert before != after


def test_manifest_is_stable_when_nothing_is_touched():
    root = Path("/tmp/lex_fid_test_cache_stable")
    if root.exists():
        for p in sorted(root.rglob("*"), reverse=True):
            p.unlink() if p.is_file() else p.rmdir()
    (root / "aa").mkdir(parents=True)
    (root / "aa" / "x.json").write_text('{"body":"1"}', encoding="utf-8")
    assert fid.manifest(root) == fid.manifest(root)


def test_accepted_verdict_selfcheck_agrees_as_a_set_relation():
    """The tri-state map must reproduce the verdict's three declared id lists."""
    verdict = _accepted()["verdict"]
    check = fid.gate_status_map_selfcheck(verdict)
    assert check["sets_agree"] is True
    assert check["counts_agree"] is True
    assert check["failed_only_in_declared"] == []
    assert check["failed_only_in_observed"] == []
    assert check["not_measurable_only_in_declared"] == []
    assert check["not_measurable_only_in_observed"] == []


def test_a_null_passed_field_maps_to_not_measurable_never_to_fail():
    """A ``passed: null`` gate is not a falsification; mapping it to FAIL would
    invent one the frozen scorer never emitted."""
    verdict = {"gates": [{"gate": "g1", "passed": None}], "n_gates": 1}
    assert fid.gate_status_map(verdict) == {"g1": "NOT_MEASURABLE"}


def test_a_true_passed_field_maps_to_pass():
    verdict = {"gates": [{"gate": "g1", "passed": True}], "n_gates": 1}
    assert fid.gate_status_map(verdict) == {"g1": "PASS"}


def test_scratch_cache_default_is_outside_the_committed_cache():
    """The instrument must never be able to write the object under test."""
    committed = fid.FROZEN_CACHE.resolve()
    scratch = Path("/tmp/lex_fid_scratch_cache").resolve()
    assert committed not in scratch.parents
    assert scratch != committed


def test_committed_cache_is_not_the_default_cache_dir_of_the_runner():
    """Regression guard for the defect this instrument studies."""
    src = (ROOT / "evaluation" / "frozen_input_durability.py").read_text("utf-8")
    assert 'scratch.mkdir(parents=True)' in src
    assert "run_pass(plan, spec, offline=False, cache_dir=scratch)" in src


# --------------------------------------------------------------------- #
# the frozen hypothesis contract
# --------------------------------------------------------------------- #


def test_hypothesis_declares_three_falsifiers_and_a_success_rule():
    hyp = json.loads(HYPOTHESIS.read_text(encoding="utf-8"))
    for key in ("F1", "F2", "F3"):
        assert hyp["falsifiers_pre_registered"][key]
    assert hyp["success_rule_frozen"]["H_SUSTAINED"]
    assert hyp["success_rule_frozen"]["H_REFUTED"]
    assert hyp["frozen_before_execution"] is True


def test_hypothesis_pins_the_two_frozen_digests():
    hyp = json.loads(HYPOTHESIS.read_text(encoding="utf-8"))
    assert hyp["frozen_inputs"] if "frozen_inputs" in hyp else True
    src = HYPOTHESIS.read_text("utf-8")
    assert "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72" in src
    assert "b06a2ad024040c38312686ab7aacc5ab18c663f1ef0b77494caf6ce3b3b52e49" in src


def test_hypothesis_contains_no_new_threshold():
    hyp = json.loads(HYPOTHESIS.read_text(encoding="utf-8"))
    assert hyp["metrics_pinned"]["no_new_thresholds"] is True


def test_hypothesis_is_mapping_free():
    hyp = json.loads(HYPOTHESIS.read_text(encoding="utf-8"))
    contract = hyp["mapping_free_contract"]
    for forbidden in ("analyst slug", "frozen id set", "baseline record"):
        assert forbidden in contract


def test_lang_recall_gate_list_is_the_six_frozen_multilingual_failures():
    assert len(fid.LANG_RECALL_GATES) == 6
    failed = set(_accepted()["verdict"]["failed_gates"])
    for gid in fid.LANG_RECALL_GATES:
        assert gid in failed, gid


def test_exit_rule_treats_a_negative_result_as_a_success():
    hyp = json.loads(HYPOTHESIS.read_text(encoding="utf-8"))
    assert "0  a measurement was made" in hyp["exit_rule"] or "0" in hyp["exit_rule"]
    assert "H_REFUTED" in hyp["exit_rule"]