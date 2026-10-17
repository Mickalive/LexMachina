"""Executable pins for the rebuilt-packet adjudication preflight (cycle 39033797087).

Repair round 1 (audit CYCLE_39033797087 required fix M4) rebuilt this file:

* the mount-dependent tests now use ``pytest.mark.skipif`` per the lane
  convention (tests/evaluation/test_label_lineage_gate.py:35), instead of
  hard-failing on a missing ``/tmp/lex_accepted``;
* the two vacuous assertions (``... or True`` and ``sum(...) >= 0``) are
  deleted;
* ``test_measured_enforcement_envelope_is_pinned``, which pinned the defective
  ONE-instrument envelope as settled truth, is replaced by
  ``test_two_bar_envelope_is_instrument_qualified_and_measured``, which pins
  the corrected TWO-BAR envelope and asserts that the unqualified M1 sentence
  is absent from the record;
* the file is now IN the lane-suite pytest scope (evaluation/lane_suite.py),
  so snapshot-audit check 4 actually covers it.

Every test here is mount-independent unless it is marked ``needs_mount``; the
committed repaired record is pinned so the published claim cannot drift away
from the measurement.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_LANE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_LANE_ROOT) not in sys.path:
    sys.path.insert(0, str(_LANE_ROOT))

from evaluation import rebuild_preflight as pf  # noqa: E402

RUN_ID = "39033797087"
FREEZE_DIR = _LANE_ROOT / "results" / "evaluation" / f"rebuild_preflight_{RUN_ID}" / "freeze"
FREEZE = FREEZE_DIR / f"FROZEN_HYPOTHESIS_REBUILD_PREFLIGHT_{RUN_ID}.json"
ERRATUM = FREEZE_DIR / f"FREEZE_ERRATA_{RUN_ID}_REPAIR_R1.json"
#: The rejected cycle's committed record. Claim-bearing history: never overwritten.
RECORD_ORIGINAL = _LANE_ROOT / "results" / "evaluation" / f"rebuild_preflight_{RUN_ID}" \
    / f"{RUN_ID}_preflight.json"
#: The repair round 1 record, produced by the repaired module.
RECORD = _LANE_ROOT / "results" / "evaluation" / f"rebuild_preflight_{RUN_ID}" \
    / f"{RUN_ID}_repair_r1_preflight.json"
SWEEP = _LANE_ROOT / "results" / "evaluation" / "label_lineage_gate" / "39020603510_sweep.json"
MOUNT = pf.SERVED_QUESTIONS
needs_mount = pytest.mark.skipif(not MOUNT.is_dir(),
                                 reason="accepted product mount absent")


def _rec() -> dict:
    return json.loads(RECORD.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# 1. the freeze is a freeze: present, byte-unchanged, pins still match, and the
#    repair's additive pins are declared by the erratum (M1)
# --------------------------------------------------------------------------- #
def test_freeze_file_present_and_instrument_shas_still_match():
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert freeze["frozen_before_any_execution_of_this_hypothesis"] is True
    assert freeze["success_rule"].startswith("PREFLIGHT_COMPLETE")
    # FROZEN_INPUTS is EXACTLY the freeze's pin set: the freeze file is
    # preserved byte-unchanged and no original pin was removed or replaced.
    assert set(freeze["instrument_pins_sha256"]) == set(pf.FROZEN_INPUTS)
    for rel, sha in freeze["instrument_pins_sha256"].items():
        assert pf.sha256_file(_LANE_ROOT / rel) == sha, f"{rel} drifted from the freeze"


def test_erratum_declares_the_additive_lineage_pins_and_no_freeze_edit():
    """M1: the sibling instruments are named in the freeze pins via the erratum."""
    erratum = json.loads(ERRATUM.read_text(encoding="utf-8"))
    freeze_sha = pf.sha256_file(FREEZE)
    assert erratum["original_freeze_sha256"] == freeze_sha, \
        "the erratum must pin the byte-identity of the freeze it corrects"
    declared = erratum["errata"][0]["additive_instrument_pins_declared_here"]
    assert declared == pf.LINEAGE_INSTRUMENT_PINS
    for rel, sha in pf.LINEAGE_INSTRUMENT_PINS.items():
        assert pf.sha256_file(_LANE_ROOT / rel) == sha, f"{rel} drifted from the additive pins"
    # No original pin may be removed or replaced by the additive set.
    assert set(pf.FROZEN_INPUTS).isdisjoint(set(pf.LINEAGE_INSTRUMENT_PINS))


def test_record_rehashes_both_pin_blocks_and_all_match():
    rec = _rec()
    rehash = rec["frozen_input_rehash_after_execution"]
    assert set(rehash) == {"freeze_pinned_instruments", "additive_lineage_instruments"}
    assert set(rehash["freeze_pinned_instruments"]) == set(pf.FROZEN_INPUTS)
    assert set(rehash["additive_lineage_instruments"]) == set(pf.LINEAGE_INSTRUMENT_PINS)
    assert pf.all_pins_match(rehash) is True


def test_freeze_success_rule_is_not_weakened_by_the_record():
    """The record may report a falsification; it may not relax the rule."""
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    rec = _rec()
    assert rec["success_rule"] == freeze["success_rule"]
    assert rec["frozen_hypothesis"].endswith(FREEZE.name)
    assert rec["freeze_erratum"].endswith(ERRATUM.name)
    assert rec["freeze_file_byte_unchanged"] is True
    a_ok = rec["legs"]["A_identity_control"]["as_predicted"]
    c_ok = rec["legs"]["C_preserved_population_blanked_evidence"]["as_predicted"]
    e_ok = rec["legs"]["E_refusal_negative_control"]["as_predicted"]
    sha_ok = pf.all_pins_match(rec["frozen_input_rehash_after_execution"])
    assert rec["success_rule_holds"] == bool(a_ok and c_ok and e_ok and sha_ok)
    assert (rec["verdict"] == "PREFLIGHT_COMPLETE") == rec["success_rule_holds"]
    # M2: the instrument's own incomplete verdict is carried in the record.
    assert rec["verdict"] == "PREFLIGHT_INCOMPLETE"
    assert rec["success_rule_holds"] is False
    assert rec["success_rule_falsified_legs"] == ["E_refusal_negative_control"]


def test_frozen_leg_e_prediction_is_quoted_verbatim_not_reworded():
    """M3: the record quotes the freeze's leg-E prediction byte-for-byte."""
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    frozen_pred = next(l["prediction"] for l in freeze["legs_frozen"]
                       if l["leg"] == "E_refusal_negative_control")
    rec = _rec()
    leg_e = rec["legs"]["E_refusal_negative_control"]
    assert leg_e["prediction"] == frozen_pred, \
        "the frozen prediction must be quoted verbatim, never restated post hoc"
    assert "run_bar_gates" in leg_e["prediction_scope"]
    # The falsification itself is preserved, not edited away.
    assert leg_e["as_predicted"] is False
    assert leg_e["exit_codes"] == [2, 0]


def test_original_rejected_cycle_record_is_preserved_not_overwritten():
    """History: the rejected cycle's committed record still carries its own verdict."""
    orig = json.loads(RECORD_ORIGINAL.read_text(encoding="utf-8"))
    assert orig["run_id"] == RUN_ID
    assert orig["verdict"] == "PREFLIGHT_INCOMPLETE"
    assert orig["success_rule_holds"] is False
    assert orig["success_rule_falsified_legs"] == ["E_refusal_negative_control"]
    # The repair never edited it: its envelope still carries the ONE-instrument
    # (defective) statement, which the repaired record must NOT carry.
    old_stmts = [s if isinstance(s, str) else s.get("statement", "")
                 for s in orig["enforcement_envelope"]["what_a_rebuilt_packet_cannot_be_blocked_on"]]
    assert any("any label regression once its scored counter-row count differs from 65" == s
               for s in old_stmts)


def test_preflight_refuses_to_overwrite_a_claim_bearing_record(tmp_path):
    """A re-execution must name a fresh record file; overwrite is an environment error.

    Mount-independent by construction: the guard fires before any leg runs, so an
    empty directory suffices as --served-questions.
    """
    proc = subprocess.run(
        [sys.executable, "-m", "evaluation.rebuild_preflight", "--run-id", RUN_ID,
         "--record-name", RECORD_ORIGINAL.name, "--served-questions", str(tmp_path)],
        cwd=str(_LANE_ROOT), capture_output=True, text=True, timeout=120)
    assert proc.returncode == 2
    assert "refusing to overwrite claim-bearing record" in proc.stderr


# --------------------------------------------------------------------------- #
# 2. the packet writer keeps the byte-identity control intact (mount-gated)
# --------------------------------------------------------------------------- #
@needs_mount
def test_write_packet_preserves_raw_bytes_for_untouched_bundles(tmp_path):
    bundles = {qid: pf._load(qid) for qid in pf.QIDS}
    dest = pf.write_packet(tmp_path / "identity", bundles)
    for qid in pf.QIDS:
        assert (dest / f"{qid}.bundle.json").read_bytes() == \
            (MOUNT / f"{qid}.bundle.json").read_bytes(), \
            f"{qid} was re-serialized: the byte-identity control would be destroyed"


@needs_mount
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


@needs_mount
def test_counter_rows_counts_issued_rows_and_never_conflates_them_with_scored():
    """The harness predicate is a SUPERSET; the accepted gate's n_scored is authoritative.

    Disclosed precision (repair r1): counter_rows() returns decisions with ANY
    issued counter status (76 on the served packet), while the frozen label
    scorer scores only SCORED_STATUSES (65).  The 11-row delta is the ``cited``
    status: issued but never scored.  No n_scored may ever be computed here.
    """
    from evaluation.frozen_bars.label_lineage_gate import SCORED_STATUSES
    issued = []
    for qid in pf.QIDS:
        issued.extend(pf.counter_rows(pf._load(qid)))
    assert issued, "the served packet must carry issued counter rows"
    assert all(r.get("counter_status") not in (None, "none") for r in issued)
    # The disclosed superset relationship, measured on the served packet.
    scored_rows = [r for r in issued if r["counter_status"] in SCORED_STATUSES]
    non_scored = [r for r in issued if r["counter_status"] not in SCORED_STATUSES]
    assert len(scored_rows) == 65, "the frozen incumbent population is 65 scored counter rows"
    assert len(issued) == 76
    assert {r["counter_status"] for r in non_scored} == {"cited"}
    # The authoritative n_scored in every record is read from the ACCEPTED
    # entry point, never computed from counter_rows().
    assert _rec()["legs"]["A_identity_control"]["label_gate"]["n_scored"] == 65


# --------------------------------------------------------------------------- #
# 3. the published TWO-BAR envelope is pinned to the measured record (M1)
# --------------------------------------------------------------------------- #
def test_two_bar_envelope_is_instrument_qualified_and_measured():
    """The M1 repair: both accepted label-side instruments, side by side, qualified."""
    rec = _rec()
    env = rec["enforcement_envelope"]

    # Both instruments are named in the envelope.
    assert "run_bar_gates" in env["instruments_measured"]["run_bar_gates_label_half"]
    assert "run_label_lineage_gate" in env["instruments_measured"]["label_lineage_gate"]

    # run_bar_gates LABEL half: population-pinned vacuity, exactly as before.
    bar = env["label_bar_run_bar_gates_population_pinned"]["measured_on"]
    assert bar["population_plus_one"]["n_scored"] == 66
    assert bar["population_plus_one"]["regression_verdict"] == "NOT_APPLICABLE"
    assert bar["population_plus_one"]["gate_blocks_build"] is False
    assert bar["population_plus_one"]["absolute_status_reported"] == "LABEL_UNSOUND"
    assert bar["preserved_population_blanked_evidence"]["regression_verdict"] == "FAIL_REGRESSION"
    assert bar["preserved_population_blanked_evidence"]["gate_blocks_build"] is True

    # label_lineage_gate: population-free, and it BLOCKS the same 66-row packet.
    lin = env["label_bar_label_lineage_gate_population_free"]["measured_on"]
    plus_one = lin["population_plus_one"]
    assert plus_one["n_scored"] == 66 and plus_one["n_supported"] == 5
    assert plus_one["regression_verdict"] == "FAIL_REGRESSION"
    assert plus_one["gate_blocks_build"] is True
    assert plus_one["admission_blocks_build"] is True
    assert "strictly below incumbent 5/65" in " ".join(plus_one["admission_block_reasons"])
    blanked = lin["preserved_population_blanked_evidence"]
    assert blanked["regression_verdict"] == "FAIL_REGRESSION"
    assert blanked["gate_blocks_build"] is True

    # The live divergence on the exact population the rejected cycle called
    # unblockable is measured and published.
    div = env["two_bar_label_divergence_measured_this_cycle"]["population_plus_one"]
    assert div == {"run_bar_gates_label_half_blocks": False,
                   "label_lineage_gate_blocks": True, "readings_disagree": True}

    # The geometry bar still enforces on the changed population.
    geom = env["geometry_bar"]["measured_on"]["population_plus_one"]
    assert geom["regression_verdict_applicable"] is True

    # ZERO-counter packet: neither label instrument blocks; neither certifies.
    e = rec["legs"]["E_refusal_negative_control"]
    assert e["zero_counter_rows"]["exit_code"] == 0
    assert e["zero_counter_rows"]["regression_verdict"] == "NOT_APPLICABLE"
    assert e["zero_counter_rows_lineage_instrument"]["label_lineage_regression_verdict"] \
        == "NOT_MEASURED"
    assert e["zero_counter_rows_lineage_instrument"]["label_lineage_gate_blocks_build"] is False
    assert e["zero_counter_rows_lineage_instrument"]["exit_code"] == 0

    # EVERY can/cannot-block statement is qualified by instrument (M1).
    for item in env["what_a_rebuilt_packet_cannot_be_blocked_on"]:
        assert item.get("qualified_by_instrument"), item
    for item in env["what_a_rebuilt_packet_can_be_blocked_on"]:
        assert item.get("qualified_by_instrument"), item

    # The defective UNQUALIFIED M1 sentence is absent from the repaired record.
    unqualified = [s if isinstance(s, str) else s.get("statement", "")
                   for s in env["what_a_rebuilt_packet_cannot_be_blocked_on"]]
    assert "any label regression once its scored counter-row count differs from 65" \
        not in unqualified, "the unqualified M1 admission claim must not survive the repair"


def test_accepted_two_bar_evidence_is_cited_and_matches_the_accepted_sweep():
    """M1: the divergence is CITED from the accepted sweep, not re-derived as new."""
    rec = _rec()
    cited = rec["accepted_evidence_cited_not_rederived"]
    assert cited["source"].endswith("39020603510_sweep.json")
    assert cited["accepted_run_id"] == "39020603510"
    assert cited["cited_not_rederived"]
    sweep = json.loads(SWEEP.read_text(encoding="utf-8"))
    row = next(r for r in sweep["blocking_matrix"] if r["packet_id"] == "38799024807")
    assert row["lineage_gate"]["n_scored"] == cited["n_scored"] == 7
    assert row["lineage_gate"]["n_supported"] == cited["n_supported"] == 0
    assert row["lineage_gate"]["regression_verdict"] \
        == cited["lineage_gate"]["regression_verdict"] == "FAIL_REGRESSION"
    assert row["lineage_gate"]["gate_blocks_build"] \
        == cited["lineage_gate"]["gate_blocks_build"] is True
    assert row["accepted_label_gate"]["regression_verdict"] \
        == cited["accepted_label_gate_run_bar_gates"]["regression_verdict"] == "NOT_APPLICABLE"
    assert row["accepted_label_gate"]["gate_blocks_build"] \
        == cited["accepted_label_gate_run_bar_gates"]["gate_blocks_build"] is False
    assert row["parity"]["readings_disagree_on_this_packet"] \
        == cited["parity"]["readings_disagree_on_this_packet"] is True
    # The envelope must carry the same citation.
    env_cited = rec["enforcement_envelope"]["accepted_evidence_cited_not_rederived"]
    assert env_cited["packet_id"] == "38799024807"


def test_headline_findings_are_all_measured_and_labelled():
    rec = _rec()
    ids = {f["id"] for f in rec["headline_findings"]}
    assert {
        "PF1_run_bar_gates_label_enforcement_is_population_pinned",
        "PF2_geometry_enforcement_is_qid_pinned",
        "PF3_zero_counter_population_is_not_blocked",
        "PF4_the_accepted_record_does_not_publish_applicability",
        "PF5_the_two_bar_label_envelope_is_wider_than_the_population_pinned_half",
    } == ids
    for f in rec["headline_findings"]:
        assert f["measured_on"] in rec["legs"] or f["measured_on"].startswith("accepted")
        assert isinstance(f["predicted_before_execution"], bool)
        assert f.get("instrument"), f"headline {f['id']} must name its instrument (M1)"
    pf5 = next(f for f in rec["headline_findings"]
               if f["id"].startswith("PF5_"))
    assert pf5["predicted_before_execution"] is False
    assert "38799024807" in pf5["statement"]


def test_record_never_claims_a_rebuilt_packet_was_adjudicated():
    rec = _rec()
    assert rec["served_bytes_modified"] is False
    # No leg may be adjudicated inside the accepted Product mount: the legs are
    # synthetic /tmp packets. (Replaces the vacuous `or True` assertion the
    # audit found; audit required fix M4.)
    for name, leg in rec["legs"].items():
        pdir = leg.get("packet_dir")
        if pdir is not None:
            assert not str(pdir).startswith(str(MOUNT)), \
                f"leg {name} was adjudicated inside the Product mount: {pdir}"
    ceiling = rec["claim_ceiling"]
    assert "No real rebuilt packet was adjudicated" in ceiling
    assert "DO-NOT-SERVE" in ceiling
    assert "human_gate_ready stays false" in ceiling
    # M1: the ceiling names the two-bar envelope, not a single instrument.
    assert "label_lineage_gate" in ceiling
    assert "5/65" in ceiling


@needs_mount
def test_end_to_end_legs_reproduce_under_both_instruments(tmp_path):
    """Mount-gated live re-execution: both accepted instruments, both readings."""
    served = MOUNT
    a = pf.leg_a_identity(served, tmp_path)
    assert a["as_predicted"] and a["exit_code"] == 0
    assert a["label_gate"]["n_scored"] == 65 and a["label_gate"]["n_supported"] == 5
    assert a["lineage_instrument"]["label_lineage_gate"]["regression_verdict"] \
        == "PASS_NO_REGRESSION"
    b = pf.leg_b_population_plus_one(served, tmp_path)
    assert b["label_gate"]["regression_verdict"] == "NOT_APPLICABLE"
    assert b["label_gate"]["gate_blocks_build"] is False
    # THE M1 delta, measured live: the population the rejected cycle declared
    # unblockable IS blocked by the accepted population-free lineage gate.
    assert b["lineage_instrument"]["label_lineage_gate"]["regression_verdict"] \
        == "FAIL_REGRESSION"
    assert b["lineage_instrument"]["label_lineage_gate"]["gate_blocks_build"] is True
    assert b["lineage_instrument"]["admission_input"]["blocks_build"] is True
    c = pf.leg_c_preserved_population_blanked(served, tmp_path)
    assert c["exit_code"] == 1 and c["label_gate"]["gate_blocks_build"] is True
    assert c["lineage_instrument"]["label_lineage_gate"]["gate_blocks_build"] is True
    e = pf.leg_e_refusal(tmp_path)
    assert e["empty_packet_dir"]["exit_code"] == 2
    assert e["exit_codes"] == [2, 0]
    assert e["as_predicted"] is False
    assert e["zero_counter_rows_lineage_instrument"]["label_lineage_regression_verdict"] \
        == "NOT_MEASURED"
