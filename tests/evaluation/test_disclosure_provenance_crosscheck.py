"""Tests for the run-39516448683 disclosure-provenance cross-check.

Standard-library only: runs under pytest AND under the lane's no-pytest shim
(evaluation/no_pytest_runner.py), so the twin readings stay comparable.

Nothing here re-derives a frozen threshold; every assertion is about identity
pins, comparator behaviour (including non-vacuity), the committed record, the
strengthening disclosure and the claim ceiling.  Mount-dependent tests SKIP
with an explicit reason when the accepted product mount is absent - a skip is
NEVER a pass.
"""
from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "evaluation"))

import disclosure_provenance_crosscheck as dpc  # noqa: E402  (lane instrument)

RESULT = REPO / "results/evaluation/disclosure_provenance_crosscheck/39516448683.json"
INITIAL = (REPO / "results/evaluation/disclosure_provenance_crosscheck/"
                  "39516448683_initial_instrument_execution_preserved.json")
HYP = REPO / "evaluation/DISCLOSURE_PROVENANCE_CROSSCHECK_HYPOTHESIS_V1.json"
FREEZE = REPO / "evaluation/DISCLOSURE_PROVENANCE_CROSSCHECK_FREEZE_RECORD_V1.json"
SWEEP = REPO / "results/evaluation/cross_run_stability_sweep/39322925971.json"
STATE = REPO / "state/evaluation.json"

MOUNT = Path("/tmp/lex_accepted/product")
MOUNT_OK = (MOUNT / dpc.DISCLOSURE_REL).is_file() and (
    MOUNT / dpc.PACKET_REL / "packet.json").is_file()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class TestFreezeFirstContract(unittest.TestCase):
    def test_freeze_record_pins_the_hypothesis_sha(self) -> None:
        self.assertEqual(load(FREEZE)["hypothesis_sha256"], sha256_file(HYP))

    def test_hypothesis_sha_matches_the_instruments_hardcoded_pin(self) -> None:
        self.assertEqual(sha256_file(HYP), dpc.HYP_SHA256)

    def test_hypothesis_declares_frozen_before_execution(self) -> None:
        self.assertTrue(load(HYP)["frozen_before_execution"])

    def test_freeze_commit_recorded(self) -> None:
        freeze = load(FREEZE)
        self.assertIn("freeze_commit", freeze)
        self.assertEqual(len(freeze["freeze_commit"]), 40)
        self.assertTrue(freeze["frozen_before_execution"])

    def test_every_evaluation_owned_pin_in_the_freeze_record_holds(self) -> None:
        freeze = load(FREEZE)
        pins = freeze["evaluation_owned_pins_rehashed_at_freeze"]
        self.assertEqual(sha256_file(SWEEP), pins[
            "results/evaluation/cross_run_stability_sweep/39322925971.json"])
        self.assertEqual(sha256_file(
            REPO / "evaluation/frozen_bars/RULES_LABEL.json"),
            dpc.FROZEN_BAR_SHAS["RULES_LABEL.json"])
        self.assertEqual(sha256_file(
            REPO / "evaluation/frozen_bars/RULES_GEOMETRY.json"),
            dpc.FROZEN_BAR_SHAS["RULES_GEOMETRY.json"])
        self.assertEqual(sha256_file(
            REPO / "evaluation/frozen_bars/VERDICT_CONTRACT.json"),
            dpc.FROZEN_BAR_SHAS["VERDICT_CONTRACT.json"])


class TestItemTextShaConvention(unittest.TestCase):
    def test_jq_dash_r_convention_adds_trailing_newline(self) -> None:
        # sha256("abc\n") is the jq -r byte convention for value "abc"
        self.assertEqual(dpc.item_text_sha("abc"),
                         hashlib.sha256(b"abc\n").hexdigest())

    def test_existing_trailing_newline_not_doubled(self) -> None:
        self.assertEqual(dpc.item_text_sha("abc\n"),
                         hashlib.sha256(b"abc\n").hexdigest())

    def test_lane_state_open_items_match_the_freeze_pins(self) -> None:
        items = load(STATE)["open_items"]
        self.assertEqual(dpc.item_text_sha(items[dpc.ITEM5]),
                         dpc.FROZEN_TEXT_SHAS[dpc.ITEM5])
        self.assertEqual(dpc.item_text_sha(items[dpc.ITEM6]),
                         dpc.FROZEN_TEXT_SHAS[dpc.ITEM6])


def _product_extraction() -> dict:
    """A synthetic-but-faithful extraction built from the real evidence."""
    lane_items = load(STATE)["open_items"]
    return {
        "verbatim_open_items": {dpc.ITEM5: lane_items[dpc.ITEM5],
                                dpc.ITEM6: lane_items[dpc.ITEM6]},
        "vendored_open_items": {dpc.ITEM5: lane_items[dpc.ITEM5],
                                dpc.ITEM6: lane_items[dpc.ITEM6]},
        "file_sha256_at_pin": dpc.PIN_STATE_SHA256,
        "git_blob_oid_at_pin": dpc.PIN_STATE_BLOB,
        "pin_commit": dpc.PIN_COMMIT,
        "p1": {
            "gate": "sr::counter_authority_surface",
            "group": "FR 102-CP same-query group",
            "status": "DIVERGENT",
            "passing_run": "CYCLE_39128456801_live",
            "failing_run": "CYCLE_39139648336_F1F2_VERIFY",
            "failing_run_n_issued": 0,
            "other_applicable_verdicts": "STABLE on both same-query groups",
        },
        "p1ext": {
            "reported_only": True,
            "retrieved_set_jaccard": {"de": 0.904762, "fr": 0.892216},
            "common_ids_changing_rank": {"de": 26, "fr": 126},
            "cluster_reassignment": {
                "de": {"reassigned": 71, "common_ids": 95, "share": 0.747},
                "fr": {"reassigned": 113, "common_ids": 149, "share": 0.758},
            },
            "fr_counter_evidence_lost": ["bge_146 IV 68",
                                         "bstger_TPF_2012_62"],
            "fr_counter_evidence_gained": ["bger_6B_750_2020"],
        },
        "de_applies": {
            "counter_stage_evidence": (
                "UNTESTED for this language - the DE same-query group is "
                "STABLE on all applicable gates and DE counter stability "
                "stays UNTESTED (stage NOT_APPLICABLE in both DE runs), not "
                "proven")},
        "it_applies": {
            "counter_stage_evidence": (
                "NOT MEASURED - no IT same-query group exists in the "
                "accepted 2-group population, so no IT run-to-run verdict "
                "was published")},
        "per_qids": sorted(dpc.QIDS),
        "packet": {"packet_json_raw_sha256": dpc.V3_PACKET_SHA},
        "per_question_blocks": {qid: {} for qid in dpc.QIDS},
    }


def _synthetic_inputs():
    sweep_re = dpc.recompute_sweep(load(SWEEP))
    lane_items = load(STATE)["open_items"]
    pins = {"pin_resolution": "already_present",
            "pin_state_sha256": dpc.PIN_STATE_SHA256,
            "pin_state_blob": dpc.PIN_STATE_BLOB,
            "current_state_sha256": "synthetic",
            "current_state_blob": "synthetic"}
    placement = {"packet_json_sha256": dpc.V3_PACKET_SHA,
                 **{f"{q}.bundle.sha256": dpc.V3_BUNDLE_SHAS[q]
                    for q in dpc.QIDS},
                 "placement": {
                     layer: {"exists": True, "per_question": {
                         qid: {"counter_block_present": True,
                               "disclosure_code":
                                   "run_to_run_counter_instability",
                               "coverage_block_present": True}
                         for qid in dpc.QIDS}}
                     for layer in ("disclosures.json", "handoff.json")}}
    return lane_items, lane_items, pins, sweep_re, placement


class TestComparatorMountless(unittest.TestCase):
    """Exercises the REAL row comparator on synthetic inputs, no mount."""

    def _rows(self, product):
        lane_items, main_items, pins, sweep_re, placement = _synthetic_inputs()
        return dpc.build_rows(product, lane_items, main_items, pins, sweep_re,
                              placement)

    def test_faithful_extraction_yields_no_divergence(self) -> None:
        rows = self._rows(_product_extraction())
        diverging = [r["id"] for r in rows
                     if r["id"] != "P4" and not r["match"]]
        self.assertEqual(diverging, [])

    def test_planted_jaccard_divergence_is_detected(self) -> None:
        prod = _product_extraction()
        prod["p1ext"]["retrieved_set_jaccard"]["fr"] = 0.5
        rows = {r["id"]: r for r in self._rows(prod)}
        self.assertFalse(rows["Q2_jaccard_fr"]["match"])

    def test_planted_verbatim_divergence_is_detected(self) -> None:
        prod = _product_extraction()
        prod["verbatim_open_items"][dpc.ITEM5] = prod[
            "verbatim_open_items"][dpc.ITEM5].replace(" DIVERGENT", "", 1)
        rows = {r["id"]: r for r in self._rows(prod)}
        self.assertFalse(rows["V1"]["match"])

    def test_planted_pin_divergence_is_detected(self) -> None:
        prod = _product_extraction()
        prod["file_sha256_at_pin"] = "0" * 64
        rows = {r["id"]: r for r in self._rows(prod)}
        self.assertFalse(rows["P1"]["match"])

    def test_planted_lost_id_divergence_is_detected(self) -> None:
        prod = _product_extraction()
        prod["p1ext"]["fr_counter_evidence_lost"] = ["bge_146 IV 68"]
        rows = {r["id"]: r for r in self._rows(prod)}
        self.assertFalse(rows["Q7_fr_evidence_lost"]["match"])

    def test_planted_cluster_share_divergence_is_detected(self) -> None:
        prod = _product_extraction()
        prod["p1ext"]["cluster_reassignment"]["fr"]["share"] = 0.9
        rows = {r["id"]: r for r in self._rows(prod)}
        self.assertFalse(rows["Q6_cluster_fr"]["match"])

    def test_planted_de_attribution_divergence_is_detected(self) -> None:
        prod = _product_extraction()
        prod["de_applies"]["counter_stage_evidence"] = "proven stable"
        rows = {r["id"]: r for r in self._rows(prod)}
        self.assertFalse(rows["Q10_de_untested"]["match"])

    def test_row_count_is_frozen_at_twenty(self) -> None:
        rows = self._rows(_product_extraction())
        self.assertEqual(len(rows), 20)
        self.assertEqual(len([r for r in rows if r["id"] != "P4"]), 19)


class TestCommittedRecord(unittest.TestCase):
    def setUp(self) -> None:
        if not RESULT.is_file():
            self.skipTest("committed record for 39516448683 absent - skip is "
                          "NEVER a pass")

    def test_verdict_vocabulary_and_zero_divergence(self) -> None:
        rec = load(RESULT)
        self.assertEqual(
            rec["verdict"],
            "VERDICT_DISCLOSURE_PROVENANCE_VERIFIED_ZERO_DIVERGENCE")
        self.assertEqual(rec["exit_code"], 0)
        self.assertEqual(rec["n_divergent"], 0)
        self.assertEqual(rec["diverging_rows"], [])
        self.assertEqual(rec["n_comparable"], 19)
        self.assertEqual(rec["n_match"], 19)
        self.assertTrue(rec["non_vacuity_all_hold"])
        self.assertEqual(len(rec["non_vacuity_controls"]), 4)
        self.assertTrue(all(c["hold"] for c in rec["non_vacuity_controls"]))

    def test_record_pins_the_frozen_hypothesis_and_instrument(self) -> None:
        rec = load(RESULT)
        self.assertEqual(rec["hypothesis_sha256"], sha256_file(HYP))
        self.assertEqual(rec["hypothesis_sha256"], dpc.HYP_SHA256)
        self.assertEqual(rec["instrument_sha256"], sha256_file(
            REPO / "evaluation/disclosure_provenance_crosscheck.py"))

    def test_claim_ceiling_stays_narrow_and_flags_fail_closed(self) -> None:
        rec = load(RESULT)
        for phrase in ("PROVENANCE FIDELITY", "no bar", "DO-NOT-SERVE",
                       "authorises no owner question"):
            self.assertIn(phrase, rec["claim_ceiling"])
        flags = rec["state_flags"]
        self.assertFalse(flags["human_gate_ready"])
        self.assertFalse(flags["machine_gate_ready"])
        self.assertFalse(flags["packet_admitted"])
        self.assertFalse(flags["ready_for_owner_session"])
        self.assertFalse(flags["owner_decision_required"])
        self.assertTrue(flags["both_do_not_serve_orders_stand"])
        self.assertTrue(flags["no_174k_benchmark_rerun"])
        self.assertTrue(flags["no_new_thresholds"])

    def test_safety_pins_unchanged_before_and_after(self) -> None:
        rec = load(RESULT)
        self.assertTrue(rec["safety"]["pins_unchanged"])
        self.assertTrue(rec["safety"]["hypothesis_unchanged"])

    def test_initial_execution_preserved_and_disclosed(self) -> None:
        rec = load(RESULT)
        self.assertTrue(INITIAL.is_file())
        self.assertIn("initial_instrument_execution_preserved",
                      rec["instrument_strengthening_disclosure"])
        self.assertIn("No check was weakened",
                      rec["instrument_strengthening_disclosure"])
        initial = load(INITIAL)
        self.assertEqual(initial["verdict"], rec["verdict"])
        self.assertEqual(initial["exit_code"], 0)

    def test_every_comparable_row_carries_both_sides(self) -> None:
        rec = load(RESULT)
        for row in rec["comparison_rows"]:
            self.assertIn("product_published", row)
            self.assertIn("lane_recomputed", row)
            self.assertIn("match", row)
            self.assertIn("comparability", row)


class TestMountEndToEnd(unittest.TestCase):
    def test_full_run_reproduces_the_committed_record(self) -> None:
        if not MOUNT_OK:
            self.skipTest("accepted product mount absent - skip is NEVER a "
                          "pass")
        rec = dpc.run(MOUNT, out_path=REPO / "results/evaluation/"
                                             "disclosure_provenance_crosscheck"
                                             "/test_local_reexec.json")
        committed = load(RESULT)
        self.assertEqual(rec["verdict"], committed["verdict"])
        self.assertEqual(rec["exit_code"], committed["exit_code"])
        self.assertEqual(rec["n_divergent"], committed["n_divergent"])
        self.assertEqual(
            [(r["id"], r["match"]) for r in rec["comparison_rows"]],
            [(r["id"], r["match"]) for r in committed["comparison_rows"]])
        self.assertTrue(rec["non_vacuity_all_hold"])

    def test_mount_absence_never_produces_a_pass(self) -> None:
        # fail-closed contract: a missing mount must raise the environment
        # error path (exit 2), never a zero-divergence verdict
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            empty = Path(td) / "absent_mount"
            empty.mkdir()
            with self.assertRaises(dpc.EnvironmentError_):
                dpc.run(empty, out_path=Path(td) / "out.json")


if __name__ == "__main__":
    unittest.main()
