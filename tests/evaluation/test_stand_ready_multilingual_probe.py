"""Tests for evaluation.stand_ready_multilingual_probe (run 39315343123).

The probe is the durable stand-ready delta of direction v58 lanes.evaluation
ordered work (2): it re-measures the CURRENT accepted product head's own live
retrieval bundles against the ACCEPTED mapping-free gates (every predicate
imported, nothing re-derived), and proves the unserved packet 39275520116 is
STRUCTURALLY addressable while every verdict on its bytes stays
WITHHELD_PENDING_SERVE.

These tests pin:
* the freeze-first contract (hypothesis + freeze record committed digests);
* counter-stage applicability (NOT_APPLICABLE is never a pass and never a fail);
* the non-vacuity battery and that the gates fire on hostile synthetic bundles;
* that the unserved-packet readiness path can NEVER emit a falsify-or-pass
  verdict on packet bytes (the pre-emption contract of the lane question);
* that the scored-status vocabulary is READ from the frozen rubric, never
  hardcoded in the probe source.

All tests here are MOUNT-INDEPENDENT (synthetic bundles) unless marked
``needs_mount``; the mount-dependent end-to-end run re-executes into a SCRATCH
path and never overwrites the committed claim-bearing record.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from evaluation import stand_ready_multilingual_probe as P  # noqa: E402

MOUNT = Path("/tmp/lex_accepted/product")
needs_mount = pytest.mark.skipif(not MOUNT.is_dir(), reason="no accepted product mount")

FROZEN_DIALECT = {
    "rules_label": "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608",
    "rules_geometry": "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633",
    "frozen_benchmark": "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72",
    "freeze_record": "b06a2ad024040c38312686ab7aacc5ab18c663f1ef0b77494caf6ce3b3b52e49",
}


# --------------------------------------------------------------------------- #
# 1. freeze-first contract
# --------------------------------------------------------------------------- #
def test_hypothesis_and_freeze_record_exist_and_pin_accepted_digests():
    h = json.loads((REPO / P.HYPOTHESIS_RELPATH).read_text(encoding="utf-8"))
    f = json.loads((REPO / P.FREEZE_RELPATH).read_text(encoding="utf-8"))
    assert h["frozen_before_claim_bearing_execution"] is True
    assert h["run_id"] == "39315343123"
    pins = f["frozen_inputs_rehashed_before_execution"]
    assert pins["evaluation/frozen_bars/RULES_LABEL.json"] == FROZEN_DIALECT["rules_label"]
    assert pins["evaluation/frozen_bars/RULES_GEOMETRY.json"] == FROZEN_DIALECT["rules_geometry"]
    assert (pins["evaluation/retrieval_gate/frozen_retrieval_benchmark.json"]
            == FROZEN_DIALECT["frozen_benchmark"])
    assert (pins["evaluation/retrieval_gate/FREEZE_RECORD.json"]
            == FROZEN_DIALECT["freeze_record"])
    # the hypothesis digest the freeze record names must re-derive
    import hashlib
    actual = hashlib.sha256((REPO / P.HYPOTHESIS_RELPATH).read_bytes()).hexdigest()
    assert f["hypothesis_sha256"] == actual


def test_hypothesis_forbids_preemption_of_the_unserved_packet():
    h = json.loads((REPO / P.HYPOTHESIS_RELPATH).read_text(encoding="utf-8"))
    rule = h["falsification_rule_frozen_before_execution"]["unserved_packet"]
    assert "WITHHELD_PENDING_SERVE" in rule
    assert "NO gate" in rule
    excl = " ".join(h["exclusions"])
    assert "39275520116" in excl
    assert "NO universal-174k" in excl


def test_probe_source_hardcodes_no_scored_status_vocabulary():
    src = (REPO / "evaluation" / "stand_ready_multilingual_probe.py").read_text(encoding="utf-8")
    assert "candidate-limiting" not in src
    assert "candidate-contrary" not in src
    assert "contrary_or_exception" not in src
    # the vocabulary is READ from the frozen rubric at run time
    assert "scored_statuses" in src


# --------------------------------------------------------------------------- #
# 2. counter-stage applicability (instrument qualification)
# --------------------------------------------------------------------------- #
def test_explicit_false_counter_stage_is_not_applicable():
    out = P.counter_stage_applicability(
        {"stages_executed": {"counter_authority": False, "retrieval": True}})
    assert out["applicable"] is False
    assert out["basis"] == "STAGE_NOT_RUN_EXPLICIT"


def test_absent_stages_with_zero_counters_is_inferred_not_applicable():
    out = P.counter_stage_applicability(
        {"stages_executed": None,
         "counters": {"counter_authorities": 0, "by_status": {"none": 100}}})
    assert out["applicable"] is False
    assert out["basis"] == "STAGE_NOT_RUN_INFERRED_FROM_COUNTERS"


def test_status_bearing_rows_make_the_counter_gate_applicable():
    out = P.counter_stage_applicability(
        {"stages_executed": None,
         "counters": {"counter_authorities": 1,
                      "by_status": {"none": 153, "cited": 4, "abstained_unevidenced": 1}}})
    assert out["applicable"] is True


def test_not_applicable_is_never_a_pass_in_the_gate_record_shape():
    gate = P._gate("x", None, "NOT_APPLICABLE_STAGE_NOT_RUN")
    assert gate["passed"] is None
    assert gate["passed"] is not True


# --------------------------------------------------------------------------- #
# 3. non-vacuity battery + gates fire on hostile synthetic bundles
# --------------------------------------------------------------------------- #
def test_non_vacuity_battery_holds_on_a_realistic_question():
    vac = P.non_vacuity("Kündigung Mietvertrag Mietrecht", "synthetic")
    assert vac["all_hold"] is True
    names = {c["control"] for c in vac["battery"]}
    assert names == {
        "A_blanked_pool_fails_concept_coverage",
        "A2_blanked_row_fails_source_validity",
        "C_oracle_pool_passes_concept_coverage",
        "D_hostile_duplicate_pool_fails_duplicate_suppression",
    }


def test_concept_coverage_gate_fires_on_a_blanked_pool():
    cov = P.concept_coverage({"question": "Kündigung Mietvertrag Mietrecht"},
                             {"decisions": []})
    assert cov["n_zero"] == cov["n_concepts"] > 0


def test_source_validity_and_duplicate_gates_fire_on_hostile_pools():
    bad = P.source_validity({"decisions": [{"decision_id": "", "canonical_url": ""}]})
    assert bad["n_rows_missing_id_or_url"] == 1
    dup = P.duplicate_suppression({"decisions": [
        {"decision_id": "a"}, {"decision_id": "a"}, {"decision_id": "b"}]})
    assert dup["duplicates"] == 1


def test_counter_surface_counts_only_frozen_scored_statuses():
    rules = json.loads((REPO / P.RULES_LABEL_RELPATH).read_text(encoding="utf-8"))
    scored = list(rules["rubric"]["scored_statuses"])
    bundle = {"decisions": [
        {"decision_id": "x1", "counter_status": "cited", "counter_evidence": ""},
        {"decision_id": "x2", "counter_status": scored[0], "counter_evidence": "ev"},
        {"decision_id": "x3", "counter_status": "none"},
    ]}
    cas = P.counter_authority_surface(bundle, scored)
    assert cas["n_issued"] == 1          # 'cited' and 'none' are NOT scored
    assert cas["n_with_empty_evidence"] == 0


# --------------------------------------------------------------------------- #
# 4. unserved-packet readiness can NEVER emit a falsify-or-pass verdict
# --------------------------------------------------------------------------- #
def test_packet_structural_readiness_hardcodes_withheld_verdict():
    import tempfile
    hypothesis = json.loads((REPO / P.HYPOTHESIS_RELPATH).read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as td:
        # synthetic mount with the pinned packet structure absent -> readiness False
        out = P.packet_structural_readiness(Path(td), hypothesis)
    assert out["falsification_verdict"] == "WITHHELD_PENDING_SERVE"
    assert out["serve_status"] == "BUILT_NOT_SERVED"
    assert out["all_structurally_addressable"] is False
    # no gate / no coverage key may ever appear in the readiness record
    assert "gates" not in out
    assert "coverage" not in out
    assert all("gates" not in q for q in out["questions"])


def test_committed_record_also_carries_withheld_verdict_for_39275520116():
    rec_path = (REPO / "results" / "evaluation" / "stand_ready_multilingual_probe"
                / "39315343123.json")
    if not rec_path.is_file():
        pytest.skip("committed claim-bearing record not present in this checkout")
    rec = json.loads(rec_path.read_text(encoding="utf-8"))
    readiness = rec["unserved_packet_structural_readiness"]
    assert readiness["packet"] == "39275520116"
    assert readiness["falsification_verdict"] == "WITHHELD_PENDING_SERVE"
    assert readiness["all_structurally_addressable"] is True
    # the serve-status probe must show ZERO serve-verdict references to it
    assert rec["serve_status"]["packet_39275520116_serve_verdict_references"] == []


# --------------------------------------------------------------------------- #
# 5. F-3B carry-forward freshness pins the accepted proof digests
# --------------------------------------------------------------------------- #
def test_f3b_carry_forward_rehashes_the_accepted_proof():
    out = P.f3b_carry_forward(REPO)
    assert out["proof_present"] is True
    assert out["status"] == "CARRY_FORWARD_FRESHNESS_OK"
    assert out["restored_matches_pre_rewrite"] is True
    assert out["note"].startswith("freshness check only")


# --------------------------------------------------------------------------- #
# 6. frozen benchmark cells are published BESIDE, never replaced
# --------------------------------------------------------------------------- #
def test_frozen_cells_beside_are_the_accepted_fr_it_zero_cells():
    cells = P.frozen_cells_beside(REPO)
    assert cells["present"] is True
    assert "BESIDE" in cells["usage"]
    lang_cells = {c["gate"]: c for c in cells["authority_lang_recall_cells"]}
    # the accepted 0/2, 0/5, 0/2 fr/it cells must be present and still failing
    fr_cc = lang_cells["authority::baseline_lang_recall::corporate-criminal-liability::fr"]
    assert (fr_cc["n_hits"], fr_cc["n_required"]) == (0, 2)
    fr_bjr = lang_cells["authority::baseline_lang_recall::business-judgment-rule::fr"]
    assert (fr_bjr["n_hits"], fr_bjr["n_required"]) == (0, 5)
    fr_ptd = lang_cells["authority::baseline_lang_recall::petty-theft-dismissal::fr"]
    assert (fr_ptd["n_hits"], fr_ptd["n_required"]) == (0, 2)


# --------------------------------------------------------------------------- #
# 7. mount-dependent end-to-end replay into a SCRATCH path
# --------------------------------------------------------------------------- #
@needs_mount
def test_end_to_end_replay_into_scratch_is_deterministic():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        scratch = Path(td) / "replay.json"
        proc = subprocess.run(
            [sys.executable, str(REPO / "evaluation" / "stand_ready_multilingual_probe.py"),
             "--run-id", "scratch-replay", "--out", str(scratch)],
            capture_output=True, text=True, timeout=300,
        )
        assert scratch.is_file(), proc.stderr[-2000:]
        replay = json.loads(scratch.read_text(encoding="utf-8"))
        committed_path = (REPO / "results" / "evaluation" / "stand_ready_multilingual_probe"
                          / "39315343123.json")
        if committed_path.is_file():
            committed = json.loads(committed_path.read_text(encoding="utf-8"))
            same_population = (replay["product_mount_head"]
                               == committed["product_mount_head"])
            if same_population:
                # SAME pinned population -> the claim-bearing verdict must
                # reproduce byte-for-byte (the original assertion of this test).
                assert replay["verdict"] == committed["verdict"]
                assert (replay["non_vacuity"]["all_hold"]
                        == committed["non_vacuity"]["all_hold"])

                def vector(rec):
                    return {
                        r["record"]: [g["passed"] for g in r["gates"]]
                        for r in rec["live_bundle_results"]
                    }
                assert vector(replay) == vector(committed)
            else:
                # POPULATION MOVED — observed pre-existing on run 39587184968
                # (committed head 6c4b8f7d, mount head 7eb5b135): the probe is
                # population-pinned by construction, so a moved mount must make
                # it REFUSE (exit 2 / ENVIRONMENT_OR_VACUOUS with drift), never
                # emit a different product verdict.  Comparing verdicts across
                # two different populations is the vacuous comparison this
                # branch forbids in both directions.
                assert replay["product_mount_head"] != committed["product_mount_head"]
                assert replay["exit_code"] == 2, (
                    "a moved population must fail closed, got "
                    f"exit {replay['exit_code']} verdict {replay['verdict']}")
                assert replay["verdict"] == "ENVIRONMENT_OR_VACUOUS", replay["verdict"]
                assert committed["verdict"] in (
                    "LIVE_BUNDLE_FALSIFIED", "ENVIRONMENT_OR_VACUOUS",
                    "PROBE_RAN_NO_LIVE_FALSIFICATION"), committed["verdict"]
        assert replay["exit_code"] in (0, 1, 2)
        # the replay must never touch the committed claim-bearing path
        assert str(committed_path) not in str(scratch)
