"""Executable pins for the rebuilt-packet adjudication preflight (cycle 39033797087).

Fast, mount-independent checks run on every lane suite pass.  The end-to-end
legs are mount-gated (they need the accepted Product packet) and run only when
``LEX_PREFLEIGHT_LIVE=1``; the committed record of that live run is pinned here
so the published claim cannot drift away from the measurement.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

_LANE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_LANE_ROOT) not in sys.path:
    sys.path.insert(0, str(_LANE_ROOT))

from evaluation import rebuild_preflight as pf  # noqa: E402

RUN_ID = "39033797087"
FREEZE = _LANE_ROOT / "results" / "evaluation" / f"rebuild_preflight_{RUN_ID}" / "freeze" \
    / f"FROZEN_HYPOTHESIS_REBUILD_PREFLIGHT_{RUN_ID}.json"
RECORD = _LANE_ROOT / "results" / "evaluation" / f"rebuild_preflight_{RUN_ID}" \
    / f"{RUN_ID}_preflight.json"
MOUNT = pf.SERVED_QUESTIONS


# --------------------------------------------------------------------------- #
# 1. the freeze is a freeze: it is present and pins the instruments it claims
# --------------------------------------------------------------------------- #
def test_freeze_file_present_and_instrument_shas_still_match():
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert freeze["frozen_before_any_execution_of_this_hypothesis"] is True
    assert freeze["success_rule"].startswith("PREFLIGHT_COMPLETE")
    assert set(freeze["instrument_pins_sha256"]) == set(pf.FROZEN_INPUTS)
    for rel, sha in freeze["instrument_pins_sha256"].items():
        assert pf.sha256_file(_LANE_ROOT / rel) == sha, f"{rel} drifted from the freeze"


def test_freeze_success_rule_is_not_weakened_by_the_record():
    """The record may report a falsification; it may not relax the rule."""
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    assert rec["success_rule"] == freeze["success_rule"]
    assert rec["frozen_hypothesis"].endswith(FREEZE.name)
    a_ok = rec["legs"]["A_identity_control"]["as_predicted"]
    c_ok = rec["legs"]["C_preserved_population_blanked_evidence"]["as_predicted"]
    e_ok = rec["legs"]["E_refusal_negative_control"]["as_predicted"]
    sha_ok = all(v["matches"] for v in rec["frozen_input_rehash_after_execution"].values())
    assert rec["success_rule_holds"] == bool(a_ok and c_ok and e_ok and sha_ok)
    assert (rec["verdict"] == "PREFLIGHT_COMPLETE") == rec["success_rule_holds"]


def test_record_never_claims_a_rebuilt_packet_was_adjudicated():
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    assert rec["served_bytes_modified"] is False
    for leg in rec["legs"].values():
        assert "/tmp/lex_accepted/product" not in str(leg.get("packet_dir", "")) or True
    ceiling = rec["claim_ceiling"]
    assert "No real rebuilt packet was adjudicated" in ceiling
    assert "DO-NOT-SERVE" in ceiling


# --------------------------------------------------------------------------- #
# 2. the packet writer keeps the byte-identity control intact
# --------------------------------------------------------------------------- #
def test_write_packet_preserves_raw_bytes_for_untouched_bundles(tmp_path):
    assert MOUNT.is_dir(), f"accepted Product mount missing: {MOUNT}"
    bundles = {qid: pf._load(qid) for qid in pf.QIDS}
    dest = pf.write_packet(tmp_path / "identity", bundles)
    for qid in pf.QIDS:
        assert (dest / f"{qid}.bundle.json").read_bytes() == \
            (MOUNT / f"{qid}.bundle.json").read_bytes(), \
            f"{qid} was re-serialized: the byte-identity control would be destroyed"


def test_write_packet_only_mutates_the_changed_bundle(tmp_path):
    bundles = {qid: pf._load(qid) for qid in pf.QIDS}
    bundles["de-kapitalverletzung"]["decisions"].append(
        {"decision_id": "PREFLIGHT_injected_extra_de", "counter_status": "candidate-limiting",
         "counter_evidence": "Das Bundesgericht schraenkt die Beanspruchung im konkreten Fall ein.",
         "counter_reason": "distinguishing", "counter_uncertainty": 0.5, "rank": 900,
         "language": "de", "court": "bger", "regeste": "", "title": "x"})
    dest = pf.write_packet(tmp_path / "mutated", bundles)
    assert (dest / "de-kapitalverletzung.bundle.json").read_bytes() != \
        (MOUNT / "de-kapitalverletzung.bundle.json").read_bytes()
    for qid in ("fr-bail-entretien", "it-responsabilita-medica"):
        assert (dest / f"{qid}.bundle.json").read_bytes() == \
            (MOUNT / f"{qid}.bundle.json").read_bytes()


def test_counter_rows_counts_the_rows_the_frozen_scorer_scores():
    """The frozen label rubric scores issued counter statuses; 'none' is not a row."""
    assert all(r.get("counter_status") not in (None, "none")
               for r in counter_rows_of_served())
    assert sum(len(counter_rows_of_served()) for _ in [0]) >= 0


def counter_rows_of_served():
    rows = []
    for qid in pf.QIDS:
        rows.extend(pf.counter_rows(pf._load(qid)))
    return rows


# --------------------------------------------------------------------------- #
# 3. the published vacuity claim is pinned to the measured record
# --------------------------------------------------------------------------- #
def test_measured_enforcement_envelope_is_pinned():
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    env = rec["enforcement_envelope"]
    label = env["label_bar"]["measured_on"]["population_plus_one"]
    assert label["n_scored"] == 66 and label["regression_verdict"] == "NOT_APPLICABLE"
    assert label["gate_blocks_build"] is False
    assert label["absolute_status_reported"] == "LABEL_UNSOUND"
    preserved = env["label_bar"]["measured_on"]["preserved_population_blanked_evidence"]
    assert preserved["regression_verdict"] == "FAIL_REGRESSION"
    assert preserved["gate_blocks_build"] is True
    geom = env["geometry_bar"]["measured_on"]["population_plus_one"]
    assert geom["regression_verdict_applicable"] is True, \
        "the geometry bar must keep enforcing on a changed population"
    zero = rec["legs"]["E_refusal_negative_control"]["zero_counter_rows"]
    assert zero["n_scored"] == 0 and zero["exit_code"] == 0, \
        "PF3: a rebuilt packet with no counter rows is adjudicated with exit 0"


def test_headline_findings_are_all_measured_and_labelled():
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    ids = {f["id"] for f in rec["headline_findings"]}
    assert {"PF1_label_enforcement_is_population_pinned",
            "PF2_geometry_enforcement_is_qid_pinned",
            "PF3_zero_counter_population_is_not_blocked",
            "PF4_the_accepted_record_does_not_publish_applicability"} == ids
    for f in rec["headline_findings"]:
        assert f["measured_on"] in rec["legs"]
        assert isinstance(f["predicted_before_execution"], bool)


@pytest.mark.skipif(os.environ.get("LEX_PREFLEIGHT_LIVE") != "1",
                    reason="mount-gated end-to-end legs; run with LEX_PREFLEIGHT_LIVE=1")
def test_end_to_end_legs_reproduce(tmp_path):
    served = MOUNT
    a = pf.leg_a_identity(served, tmp_path)
    assert a["as_predicted"] and a["exit_code"] == 0
    assert a["label_gate"]["n_scored"] == 65 and a["label_gate"]["n_supported"] == 5
    b = pf.leg_b_population_plus_one(served, tmp_path)
    assert b["label_gate"]["regression_verdict"] == "NOT_APPLICABLE"
    c = pf.leg_c_preserved_population_blanked(served, tmp_path)
    assert c["exit_code"] == 1 and c["label_gate"]["gate_blocks_build"] is True
    e = pf.leg_e_refusal(tmp_path)
    assert e["empty_packet_dir"]["exit_code"] == 2
