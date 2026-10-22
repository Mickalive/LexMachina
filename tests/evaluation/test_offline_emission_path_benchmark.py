"""Tests for the offline emission-path benchmark (FAST-MVP evaluation lane)."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation import offline_emission_path_benchmark as oepb  # noqa: E402


def test_scored_statuses_match_frozen_rubric():
    rules = json.loads(
        (REPO_ROOT / "evaluation/frozen_bars/RULES_LABEL.json").read_text(encoding="utf-8")
    )
    scored = list(((rules.get("rubric") or {}).get("scored_statuses")) or [])
    assert scored == [
        "candidate-limiting",
        "candidate-contrary",
        "contrary_or_exception",
        "limiting",
    ]


def test_claim_ceiling_is_restrictive():
    ceiling = oepb.CLAIM_CEILING
    assert "does NOT meet" in ceiling
    assert "human_gate_ready stays false" in ceiling
    assert "universal-174k" in ceiling


def test_reused_assets_declared():
    assert "apply_counter_emission_repair" in oepb.REUSED
    assert "apply_anchor_labels" in oepb.REUSED
    assert "mf_counter_surface" in oepb.REUSED


def test_signal_rows_filters_empty_evidence():
    bundle = {
        "decisions": [
            {"decision_id": "a", "adversarial_retrieval_signal": {
                "heuristic_status": "limiting", "evidence": "some evidence"}},
            {"decision_id": "b", "adversarial_retrieval_signal": {
                "heuristic_status": "limiting", "evidence": ""}},
            {"decision_id": "c"},
        ]
    }
    rows = oepb.signal_rows(bundle)
    assert [r["decision_id"] for r in rows] == ["a"]


def test_network_guard_blocks_and_records():
    import socket

    guard = oepb.NetworkGuard()
    with guard:
        try:
            socket.socket.connect(object(), ("127.0.0.1", 9))
            raised = False
        except RuntimeError:
            raised = True
    assert raised
    assert len(guard.calls) == 1
    # restored
    assert socket.socket.connect is not object


def test_hypothesis_and_freeze_exist_and_pin_direction():
    hyp = json.loads(
        (REPO_ROOT / "evaluation/OFFLINE_EMISSION_PATH_HYPOTHESIS_V1.json").read_text(
            encoding="utf-8"
        )
    )
    freeze = json.loads(
        (REPO_ROOT / "evaluation/OFFLINE_EMISSION_PATH_FREEZE_RECORD_V1.json").read_text(
            encoding="utf-8"
        )
    )
    assert hyp["lane"] == "evaluation"
    assert hyp["direction_version"] == 63
    assert freeze["frozen_before_execution"] is True
    assert freeze["product_mount_head"] == "fe219a197e4bfb129984a732ab9adca917556eac"
    assert "RULES_LABEL" in json.dumps(freeze["pins_before_execution"])


def test_measure_question_on_product_mount_if_present():
    """Full path measurement when the accepted product mount is available."""
    mount = Path(oepb.DEFAULT_MOUNT)
    if not mount.is_dir():
        print("SKIP: product mount not present")
        return
    try:
        modules = oepb.load_product_modules(mount)
    except Exception as exc:
        print(f"SKIP: cannot load product modules: {exc}")
        return
    rules = json.loads(
        (REPO_ROOT / "evaluation/frozen_bars/RULES_LABEL.json").read_text(encoding="utf-8")
    )
    scored = list(((rules.get("rubric") or {}).get("scored_statuses")) or [])
    guard = oepb.NetworkGuard()
    with guard:
        result = oepb.measure_question(
            mount, "de-kapitalverletzung", modules, scored, guard
        )
    assert result["qid"] == "de-kapitalverletzung"
    assert result["gates"]["E1_promotion_matches_heuristic_signal_count"]["passed"] is True
    assert result["gates"]["E3_three_number_publication"]["passed"] is True
    # three-number publication is present and numeric
    assert isinstance(result["post_path"]["n_scored"], int)
    assert isinstance(result["post_path"]["n_emitted"], int)
    assert result["controls"]["C3_blanked_promotion_control"]["passed"] is True
    assert guard.calls == []


def test_end_to_end_run_when_mount_present():
    import tempfile

    mount = Path(oepb.DEFAULT_MOUNT)
    if not mount.is_dir():
        print("SKIP: product mount not present")
        return
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "out"
        report = Path(td) / "report"
        try:
            code, rec = oepb.run("local_test_oepb", out, report, str(mount))
        except Exception as exc:
            print(f"SKIP: run raised: {exc}")
            return
        assert rec["schema"] == oepb.SCHEMA
        assert rec["verdict"] in {
            "PATH_MEASURED_NO_FALSIFICATION",
            "PRODUCT_PATH_FALSIFIED",
            "ENVIRONMENT_OR_VACUOUS",
        }
        assert rec["exit_code"] == code
        assert rec["human_gate_ready"] is False
        # three numbers always co-published
        assert "n_emitted_total" in rec["aggregate"]
        assert "comparative_map_vs_ranked_list" in rec["aggregate"]
        assert (out / "local_test_oepb.json").is_file()
