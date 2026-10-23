"""Tests for ``evaluation/fast_mvp_acceptance.py`` (FAST-MVP acceptance battery).

Every assertion here is either (a) a property of the committed freeze-first
hypothesis/freeze record, (b) a pure-function property of this instrument
(classification, drift detection, adjudication conditions), or (c) a
non-vacuity control: a planted divergence MUST be detected and a planted
permits-serve recommendation MUST flip ordered item (5).

No frozen rubric, bar or gate threshold is read or re-derived here. Mount-
dependent tests skip with an explicit reason when the accepted product mount
is absent (a skip is NEVER a pass).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from evaluation import fast_mvp_acceptance as F  # noqa: E402

HYP_PATH = REPO / F.HYPOTHESIS_RELPATH
FREEZE_PATH = REPO / F.FREEZE_RELPATH
MOUNT = Path(F.DEFAULT_MOUNT)
needs_mount = pytest.mark.skipif(not MOUNT.is_dir(), reason="no accepted product mount")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_hypothesis_sha_matches_freeze_record():
    hyp = json.loads(HYP_PATH.read_text(encoding="utf-8"))
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    assert freeze["hypothesis_sha256_at_freeze"] == _sha(HYP_PATH)
    assert hyp["frozen_before_execution"] is True
    assert hyp["run_id"] == "39884405570"
    assert hyp["direction_version"] == 63


def test_freeze_inputs_pinned_equals_hypothesis_evaluation_digests():
    hyp = json.loads(HYP_PATH.read_text(encoding="utf-8"))
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    hyp_digests = {k: v for k, v in hyp["inputs_pinned"].items()
                   if k.startswith("evaluation/")}
    assert hyp_digests == freeze["expected_repo_pins_before_execution"]


def test_all_standing_repo_pins_exist_and_rehash():
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    for rel, expected in freeze["expected_repo_pins_before_execution"].items():
        p = REPO / rel
        assert p.is_file(), f"missing pinned input {rel}"
        assert _sha(p) == expected, f"pin mismatch for {rel}"


def test_frozen_bars_match_accepted_digests():
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    pins = freeze["expected_repo_pins_before_execution"]
    assert pins["evaluation/frozen_bars/RULES_LABEL.json"].startswith("4457e971")
    assert pins["evaluation/frozen_bars/RULES_GEOMETRY.json"].startswith("a7452748")
    assert pins["evaluation/frozen_bars/VERDICT_CONTRACT.json"].startswith("b9cdb894")
    assert pins["evaluation/retrieval_gate/frozen_retrieval_benchmark.json"].startswith("187b0e54")


def test_exit_codes_match_hypothesis_contract():
    hyp = json.loads(HYP_PATH.read_text(encoding="utf-8"))
    assert set(hyp["exit_codes"]) == {"0", "1", "2"}
    assert F.EXIT_OK == 0 and F.EXIT_INCOMPLETE == 1 and F.EXIT_DRIFT == 2
    assert hyp["exit_codes"]["0"].startswith("BATTERY_EXECUTED_PINS_HELD")
    assert hyp["exit_codes"]["1"].startswith("BATTERY_INCOMPLETE")
    assert hyp["exit_codes"]["2"].startswith("PINS_DRIFTED_VACUOUS")


def test_battery_list_files_all_exist():
    hyp = json.loads(HYP_PATH.read_text(encoding="utf-8"))
    assert len(hyp["battery_test_files"]) == 7
    for tf in hyp["battery_test_files"]:
        assert (REPO / tf).is_file(), f"battery suite missing: {tf}"
    # the reuse-first multilingual/provenance suites are named by the lane directive
    joined = " ".join(hyp["battery_test_files"])
    assert "stand_ready_multilingual_probe" in joined
    assert "mount_provenance_gate" in joined
    assert "disclosure_provenance_crosscheck" in joined


def test_classify_serve_recommendation_non_vacuity():
    assert F.classify_serve_recommendation("DO-NOT-SERVE this packet unchanged") == "DO_NOT_SERVE"
    assert F.classify_serve_recommendation("DO-NOT-SERVE-UNCHANGED") == "DO_NOT_SERVE"
    assert F.classify_serve_recommendation("BOUNDED-NEGATIVE: both bars unmet") == "DO_NOT_SERVE"
    # planted permits-serve must be detected - the classifier is not vacuous
    assert F.classify_serve_recommendation("SERVE this packet as-is") == "PERMITS_SERVE"


def test_pin_drift_detects_planted_divergence():
    before = {"repo": {"a.json": {"expected": "x", "actual": "x", "match": True}},
              "mount": {}}
    same = {"repo": {"a.json": {"expected": "x", "actual": "x", "match": True}},
            "mount": {}}
    changed = {"repo": {"a.json": {"expected": "x", "actual": "y", "match": True}},
               "mount": {}}
    broken = {"repo": {"a.json": {"expected": "x", "actual": "z", "match": False}},
              "mount": {}}
    assert F.pin_drift(before, same) == []
    assert any("before_after_mismatch" in d for d in F.pin_drift(before, changed))
    assert any("expected_never_matched" in d for d in F.pin_drift(before, broken))


def _fake_hypothesis() -> dict:
    return {
        "accepted_failed_gate_set": ["mf::concept_coverage::39319405429::de-kapitalverletzung"],
        "inputs_pinned": {
            "mount:/tmp/lex_accepted/product/product/query/adversarial_retrieval.py": "P" * 64,
            "accepted_product_mount_head": "H" * 40,
        },
    }


def test_benchmark_findings_match_and_mismatch():
    hyp = _fake_hypothesis()
    accepted = {"verdict": "PRODUCT_FALSIFIED", "exit_code": 1, "run_valid": True,
                "input_drift": [], "n_gates": 18, "n_passed": 11, "n_failed": 1,
                "n_reported": 0, "falsification_proven": True,
                "failed_gates": [{"gate": "mf::concept_coverage::39319405429::de-kapitalverletzung"}],
                "non_vacuity": {"all_hold": True, "battery": [{"control": "c", "holds": True}]},
                "product_mount_head": "H" * 40, "direction_version": 61}
    ok = F.benchmark_findings({"record": accepted}, hyp)
    assert ok["falsification_reproduced"] is True
    assert ok["failed_gate_set_matches_accepted"] is True
    other = dict(accepted, failed_gates=[{"gate": "mf::counter_authority_surface::other"}])
    bad = F.benchmark_findings({"record": other}, hyp)
    assert bad["failed_gate_set_matches_accepted"] is False


@needs_mount
def test_adjudication_non_vacuity_and_current_condition():
    hyp = json.loads(HYP_PATH.read_text(encoding="utf-8"))
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    pins_before = F.rehash_pins(freeze, MOUNT)
    items = F.adjudicate_ordered_items(MOUNT, pins_before, hyp)
    # current condition: unchanged accepted pins => (1)(2)(5) NOT_TRIGGERED, (3)(4) STANDING_OK
    if _sha(MOUNT / "product/query/adversarial_retrieval.py") == \
            hyp["inputs_pinned"]["mount:/tmp/lex_accepted/product/product/query/adversarial_retrieval.py"]:
        assert items["(1)_remedy_a_re_freeze"]["verdict"] == "NOT_TRIGGERED"
    # (5): with no permits-serve recommendation committed today -> NOT_TRIGGERED
    if items["(5)_falsify_new_served_packet"]["permits_serve_count"] == 0:
        assert items["(5)_falsify_new_served_packet"]["verdict"] == "NOT_TRIGGERED"
    # non-vacuity: every verdict carries its condition, none empty
    for key, it in items.items():
        assert it.get("condition"), f"{key} lacks a machine condition"


@needs_mount
def test_adjudication_trigger_flip_on_planted_planner_drill():
    """Planted planner drift MUST flip (1) to TRIGGERED (adjudication non-vacuous)."""
    hyp = json.loads(HYP_PATH.read_text(encoding="utf-8"))
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    pins_before = F.rehash_pins(freeze, MOUNT)
    hyp_planted = json.loads(json.dumps(hyp))
    hyp_planted["inputs_pinned"][
        "mount:/tmp/lex_accepted/product/product/query/adversarial_retrieval.py"] = "0" * 64
    items = F.adjudicate_ordered_items(MOUNT, pins_before, hyp_planted)
    assert items["(1)_remedy_a_re_freeze"]["verdict"] == "TRIGGERED"


def test_skip_execute_writes_scratch_only_and_exits_incomplete():
    if not MOUNT.is_dir():
        pytest.skip("no accepted product mount (adjudication re-hashes the planner)")
    with tempfile.TemporaryDirectory() as td:
        proc = subprocess.run(
            [sys.executable, "-m", "evaluation.fast_mvp_acceptance",
             "--run-id", "scratch_test", "--skip-execute",
             "--out-dir", td, "--report-dir", td],
            cwd=str(REPO), capture_output=True, text=True, timeout=300)
        assert proc.returncode == F.EXIT_INCOMPLETE, proc.stdout + proc.stderr
        rec = json.loads((Path(td) / "scratch_test.json").read_text(encoding="utf-8"))
        assert rec["verdict"] == "ASSEMBLE_ONLY_NOT_CLAIM_BEARING"
        assert rec["no_new_thresholds"] is True
        assert rec["frozen_rubrics_read_for_enforcement"] is False
        assert (Path(td) / "FAST_MVP_ACCEPTANCE_scratch_test.md").is_file()
        # nothing claim-bearing was written into the committed tree
        assert not (REPO / "results/evaluation/fast_mvp_acceptance/scratch_test.json").exists()
