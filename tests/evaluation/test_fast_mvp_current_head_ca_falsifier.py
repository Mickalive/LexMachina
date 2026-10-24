"""Tests for the v67 FAST-MVP current-head counter-authority falsifier.

These tests pin the freeze-first contract and the claim ceiling of
evaluation/fast_mvp_current_head_ca_falsifier.py. They read the committed
record; they do NOT re-run the claim-bearing measurement into the committed
tree and they do NOT touch any frozen rubric, threshold or verdict contract.

Plain zero-argument test functions so the stdlib shim
evaluation/no_pytest_runner.py can execute them where pytest is absent.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation import fast_mvp_current_head_ca_falsifier as F  # noqa: E402

RUN_ID = "40105794124"
RECORD = (_REPO_ROOT / "results/evaluation/fast_mvp_current_head_ca_falsifier"
          / f"{RUN_ID}.json")


def _rec() -> dict:
    return json.loads(RECORD.read_text(encoding="utf-8"))


def test_hypothesis_and_freeze_are_committed_and_digest_bound():
    assert F.HYPOTHESIS_RELPATH.endswith("HYPOTHESIS_V1.json")
    assert F.FREEZE_RELPATH.endswith("FREEZE_V1.json")
    hyp = json.loads((_REPO_ROOT / F.HYPOTHESIS_RELPATH).read_text(encoding="utf-8"))
    freeze = json.loads((_REPO_ROOT / F.FREEZE_RELPATH).read_text(encoding="utf-8"))
    rec = _rec()
    assert hyp["frozen_before_execution"] is True
    assert hyp["run_id"] == RUN_ID
    assert rec["consistency"]["hypothesis_sha_matches_freeze_record"] is True
    assert rec["hypothesis"]["sha256"] == freeze["hypothesis_sha256_at_freeze"]


def test_instrument_reuses_frozen_predicates_and_defines_no_threshold():
    src = Path(F.__file__).read_text(encoding="utf-8")
    assert "from evaluation import counter_evidence_quality_benchmark as CQ" in src
    assert "from evaluation import mapping_free_recall_falsifier as MF" in src
    assert "CQ.classify_verified_row" in src
    assert "MF.counter_authority_surface" in src
    # no re-implementation of the frozen predicates
    assert "def classify_verified_row" not in src
    assert "def counter_authority_surface" not in src


def test_population_is_pinned_and_pins_hold_before_and_after():
    rec = _rec()
    assert rec["pins_before_execution"]["all_match"] is True
    assert rec["pins_after_execution"]["all_match"] is True
    assert rec["product_mount_head"] == "8b5b08dddeda482961ecfd432a5b5b40675b92ab"
    assert rec["aggregate"]["n_bundles"] == len(rec["bundles"]) == 6


def test_controls_all_hold():
    rec = _rec()
    assert rec["controls"]["all_hold"] is True
    assert len(rec["controls"]["battery"]) == 4


def test_record_is_not_a_frozen_bar_result_and_keeps_posture_fail_closed():
    rec = _rec()
    assert rec["no_new_thresholds"] is True
    assert rec["no_174k_benchmark_rerun"] is True
    assert rec["benchmark_of_record_untouched"] is True
    assert rec["packet_admitted"] is False
    assert rec["machine_gate_ready"] is False
    assert rec["human_gate_ready"] is False
    assert rec["ready_for_owner_session"] is False
    assert rec["owner_decision_required"] is False
    assert "benchmark of record" in rec["claim_ceiling"]
    assert "NO serve verdict" in rec["claim_ceiling"]
    assert "universal-174k" in rec["claim_ceiling"]


def test_surface_gate_is_content_blind_on_the_new_bytes():
    """The probe must show the gap it was built to expose, without overclaiming.

    At least one enriched bundle's frozen counter_authority_surface gate would
    PASS while its only verified scored row carries a frozen D1-D4 content
    defect. If this ever stops being true, the record is stale and the instrument
    must be re-run under a NEW frozen spec - never silently edited.
    """
    rec = _rec()
    gap = [b for b in rec["bundles"]
           if b["enriched"]
           and b["frozen_surface_gate"]["would_pass"]
           and b["n_defective_verified_scored_rows"] >= 1]
    assert gap, "expected at least one content-blind surface pass on the frozen population"
    assert rec["aggregate"]["n_defective_verified_scored_rows_total"] >= 1


def test_verdict_matches_the_frozen_rule():
    rec = _rec()
    agg = rec["aggregate"]
    if rec["verdict"] == "CAPABILITY_FALSIFIED_CONTENT_DEFECTIVE":
        assert rec["exit_code"] == 1
        assert agg["n_enriched_with_sound_counter_row"] == 0
    elif rec["verdict"] == "SOUND_COUNTER_ROW_PRESENT":
        assert rec["exit_code"] == 0
        assert agg["n_enriched_with_sound_counter_row"] >= 1
    elif rec["verdict"] == "NOT_MEASURED_VACUOUS":
        assert rec["exit_code"] == 2
    else:
        assert rec["verdict"] == "PARTIAL_OR_UNEXPECTED"
        assert rec["exit_code"] == 0


def test_item_2_is_not_claimed_discharged():
    rec = _rec()
    assert rec["v67_item_2_status"].startswith("NOT_YET_DISCRIMINATING")
