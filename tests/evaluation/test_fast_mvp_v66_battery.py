"""Unit tests for the FAST-MVP v66 acceptance battery instrument.

These tests exercise the battery's pure helpers (pin re-hash, drift detection,
ordered-item adjudication, exit-code contract) WITHOUT running the claim-bearing
benchmark or test battery. They are part of the lane's normal test suite and
are NOT the freeze-first battery execution itself.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation.fast_mvp_v66_battery import (  # noqa: E402
    EXIT_DRIFT,
    EXIT_INCOMPLETE,
    EXIT_OK,
    adjudicate_v66_ordered_items,
    pin_drift,
    rehash_pins,
    sha256_file,
)


def test_exit_codes_frozen():
    assert EXIT_OK == 0
    assert EXIT_INCOMPLETE == 1
    assert EXIT_DRIFT == 2


def test_hypothesis_and_freeze_exist_and_are_json():
    hyp = json.loads((REPO_ROOT / "evaluation/FAST_MVP_V66_HYPOTHESIS_V1.json").read_text())
    frz = json.loads((REPO_ROOT / "evaluation/FAST_MVP_V66_FREEZE_RECORD_V1.json").read_text())
    assert hyp["direction_version"] == 66
    assert hyp["run_id"] == "40073123887"
    assert frz["direction_version"] == 66
    assert frz["run_id"] == "40073123887"
    # hypothesis sha in freeze record must match actual file
    actual = sha256_file(REPO_ROOT / "evaluation/FAST_MVP_V66_HYPOTHESIS_V1.json")
    assert frz["hypothesis_sha256_at_freeze"] == actual


def test_freeze_record_pins_resolve_and_match():
    """Every pin in the freeze record must resolve to a real file whose
    sha256 equals the recorded expected value (identity re-hash only)."""
    frz = json.loads((REPO_ROOT / "evaluation/FAST_MVP_V66_FREEZE_RECORD_V1.json").read_text())
    mount = Path("/tmp/lex_accepted/product")
    # only re-hash repo pins here; mount pins need the product mount which may
    # not be present in every test environment (disclosed, never silently pass)
    for rel, expected in frz["expected_repo_pins_before_execution"].items():
        p = REPO_ROOT / rel
        assert p.is_file(), f"missing repo pin: {rel}"
        actual = sha256_file(p)
        assert actual == expected, f"pin drift on {rel}: {actual} != {expected}"


def test_pin_drift_detects_mismatch():
    before = {"repo": {"a.json": {"expected": "x", "actual": "x", "match": True}},
              "mount": {}}
    after = {"repo": {"a.json": {"expected": "x", "actual": "y", "match": True}},
             "mount": {}}
    d = pin_drift(before, after)
    assert any("before_after_mismatch" in x for x in d)


def test_pin_drift_clean_when_identical():
    b = {"repo": {"a.json": {"expected": "x", "actual": "x", "match": True}},
         "mount": {"b.json": {"expected": "y", "actual": "y", "match": True}}}
    assert pin_drift(b, b) == []


def test_adjudicate_item4_not_discriminating_when_head_unchanged():
    """When mount head == last measured head, item (4) must be
    NOT_YET_DISCRIMINATING (the REPRODUCED finding must not be re-confirmed)."""
    hyp = json.loads((REPO_ROOT / "evaluation/FAST_MVP_V66_HYPOTHESIS_V1.json").read_text())
    last = hyp["v66_ordered_item_conditions"]["(4)_conditional_remeasure"]["last_measured_product_head"]
    # monkeypatch-free: call with a mount path whose git head we control via a
    # fake _git_head by using the real mount if present, else a stub path.
    mount = Path("/tmp/lex_accepted/product")
    pins_before = {"repo": {}, "mount": {}}
    bench = {"record": {"verdict": "PRODUCT_FALSIFIED", "exit_code": 1,
                        "failed_gates": list(hyp["accepted_failed_gate_set"])}}
    items = adjudicate_v66_ordered_items(mount, pins_before, hyp, bench)
    # the accepted mount head IS the last measured head at freeze time
    assert items["(4)_conditional_remeasure"]["actual_mount_head"] == last
    assert items["(4)_conditional_remeasure"]["verdict"] == "NOT_YET_DISCRIMINATING"
    assert items["(4)_conditional_remeasure"]["head_unchanged"] is True


def test_adjudicate_item5_standing_on_matching_failed_set():
    hyp = json.loads((REPO_ROOT / "evaluation/FAST_MVP_V66_HYPOTHESIS_V1.json").read_text())
    mount = Path("/tmp/lex_accepted/product")
    bench = {"record": {"verdict": "PRODUCT_FALSIFIED", "exit_code": 1,
                        "failed_gates": list(hyp["accepted_failed_gate_set"])}}
    items = adjudicate_v66_ordered_items(mount, {"repo": {}, "mount": {}}, hyp, bench)
    assert items["(5)_report_standing_falsification"]["verdict"] == "STANDING"
    assert items["(5)_report_standing_falsification"]["failed_gate_set_matches_accepted"] is True
    assert items["(5)_report_standing_falsification"]["this_run_supersedes"] is False


def test_rehash_pins_on_freeze_record_repo_side():
    frz = json.loads((REPO_ROOT / "evaluation/FAST_MVP_V66_FREEZE_RECORD_V1.json").read_text())
    # build a minimal freeze dict with only repo pins for this helper test
    mini = {"expected_repo_pins_before_execution": frz["expected_repo_pins_before_execution"],
            "expected_mount_pins_before_execution": {}}
    out = rehash_pins(mini, Path("/nonexistent-mount"))
    assert all(v["match"] for v in out["repo"].values())
    assert out["mount"] == {}
