"""Tests for the run-39457963802 counter-emission cross-check (direction v61 (2)).

Standard-library only: runs under pytest AND under the lane's no-pytest shim
(evaluation/no_pytest_runner.py), so the twin readings stay comparable.

Nothing here re-derives a frozen threshold; every assertion is about identity
pins, comparator behaviour (including non-vacuity), the committed record, the
requirement-25/26 triple publication and the claim ceiling.
"""
from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "evaluation"))

import counter_emission_crosscheck as cec  # noqa: E402  (lane instrument)

RESULT = REPO / "results/evaluation/counter_emission_crosscheck/39457963802.json"
HYP = REPO / "evaluation/COUNTER_EMISSION_CROSSCHECK_HYPOTHESIS_V1.json"
FREEZE = REPO / "evaluation/COUNTER_EMISSION_CROSSCHECK_FREEZE_RECORD_V1.json"
VEND = REPO / "evaluation/vendored_frontier_counter_emission"
PROV = VEND / "PROVENANCE.json"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class TestFreezeFirstContract(unittest.TestCase):
    def test_freeze_record_pins_the_hypothesis_sha(self) -> None:
        self.assertEqual(load(FREEZE)["hypothesis_sha256"], sha256_file(HYP))

    def test_hypothesis_declares_frozen_before_execution(self) -> None:
        self.assertTrue(load(HYP)["frozen_before_execution"])

    def test_freeze_commit_recorded_and_precedes_instrument(self) -> None:
        freeze = load(FREEZE)
        self.assertIn("freeze_commit", freeze)
        self.assertTrue(freeze["committed_before_any_claim_bearing_execution"])

    def test_every_frozen_input_pin_still_holds(self) -> None:
        pins = load(HYP)["frozen_inputs_rehashed_not_rewritten"]
        for rel, pinned in pins.items():
            with self.subTest(rel=rel):
                self.assertEqual(sha256_file(REPO / rel), pinned, rel)

    def test_every_packet_identity_pin_still_holds(self) -> None:
        pins = load(HYP)["packet_identity_pins"]
        packet_dir = Path(pins["packet_dir"])
        for name, pinned in pins.items():
            if name == "packet_dir":
                continue
            path = packet_dir / name
            if not path.is_file():
                path = packet_dir / "questions" / name
            with self.subTest(name=name):
                self.assertEqual(sha256_file(path), pinned, name)

    def test_vendored_files_match_provenance_shas(self) -> None:
        prov = load(PROV)
        for name, meta in prov["files"].items():
            with self.subTest(name=name):
                self.assertEqual(sha256_file(VEND / name), meta["sha256"], name)


class TestLaneRecomputation(unittest.TestCase):
    """The lane's own recomputation over the packet bytes and team artifacts."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.packet_dir = Path(load(HYP)["packet_identity_pins"]["packet_dir"])
        cls.facts = cec.recompute_bundle_facts(cls.packet_dir)
        cls.emission = load(VEND / "EMISSION.json")["emission"]
        cls.determinism = load(VEND / "DETERMINISM.json")["determinism"]
        cls.attribution = load(VEND / "ATTRIBUTION.json")["attribution"]
        cls.cons = cec.recompute_consistency(cls.emission, cls.determinism,
                                             cls.attribution)

    def test_bundle_row_totals_match_frozen_expectation(self) -> None:
        expected = load(HYP)["expected_lane_recomputed_before_state"]
        for qid in cec.QIDS:
            with self.subTest(qid=qid):
                self.assertEqual(
                    self.facts[qid]["n_total_rows"],
                    expected[qid]["n_total_rows"], qid)

    def test_eight_adversarial_rows_all_unevidenced_per_bundle(self) -> None:
        expected = load(HYP)["expected_lane_recomputed_before_state"]
        for qid in cec.QIDS:
            with self.subTest(qid=qid):
                self.assertEqual(self.facts[qid]["n_adversarial_rows"],
                                 expected[qid]["n_adversarial_rows"])
                self.assertEqual(self.facts[qid]["n_adversarial_ce_empty"],
                                 expected[qid]["n_adversarial_ce_empty"])
                self.assertEqual(self.facts[qid]["n_adversarial_cs_none"],
                                 expected[qid]["n_adversarial_cs_none"])

    def test_before_state_is_zero_scored_everywhere(self) -> None:
        for qid in cec.QIDS:
            with self.subTest(qid=qid):
                before = self.emission[qid]["before"]
                self.assertEqual(before["n_scored"], 0)
                self.assertEqual(before["n_abstained"], 0)
                self.assertEqual(before["n_emitted"], 0)

    def test_after_state_is_fully_abstained_zero_emitted(self) -> None:
        for qid in cec.QIDS:
            with self.subTest(qid=qid):
                after = self.emission[qid]["after"]
                self.assertEqual(after["n_emitted"], 0)
                self.assertEqual(after["n_abstained"], after["n_scored"])
                self.assertEqual(after["support_rate_among_issued"], 0.0)
                self.assertEqual(after["yield_over_population"], 0.0)
                self.assertFalse(after["absolute_bar_status"]["satisfied"])

    def test_internal_consistency_all_true(self) -> None:
        for qid in cec.QIDS:
            with self.subTest(qid=qid):
                self.assertTrue(
                    self.cons[qid]["n_scored_eq_abstained_plus_emitted"])
                self.assertTrue(self.cons[qid]["abstention_reasons_sum"])
                self.assertTrue(self.cons[qid]["determinism_signature_len"])
                self.assertTrue(self.cons[qid]["repair_promoted_eq_proposed"])
                self.assertTrue(self.cons[qid]["before_n_scored_is_zero"])

    def test_primary_cause_is_writer_abort_on_all_bundles(self) -> None:
        gate = load(VEND / "CYCLE_39426324296_GATE.json")["evidence_summary"]
        self.assertEqual(gate["primary_cause_all_bundles"],
                         "e_EMISSION_WRITER_ABORT")
        summary = load(VEND / "MEASUREMENT_SUMMARY.json")
        for qid in cec.QIDS:
            with self.subTest(qid=qid):
                self.assertEqual(summary["attribution"][qid]["primary_cause"],
                                 "e_EMISSION_WRITER_ABORT")
                self.assertEqual(self.attribution[qid]["primary_cause"],
                                 "e_EMISSION_WRITER_ABORT")


class TestComparatorNonVacuity(unittest.TestCase):
    """The comparator must SEE a divergence on every side it compares."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.summary = load(VEND / "MEASUREMENT_SUMMARY.json")
        cls.team = {
            "summary": cls.summary,
            "emission": load(VEND / "EMISSION.json")["emission"],
            "attribution": load(VEND / "ATTRIBUTION.json")["attribution"],
            "determinism": load(VEND / "DETERMINISM.json")["determinism"],
            "non_vacuity": load(VEND / "NON_VACUITY.json")["non_vacuity"],
            "gate": load(VEND / "CYCLE_39426324296_GATE.json")[
                "evidence_summary"],
        }
        packet_dir = Path(load(HYP)["packet_identity_pins"]["packet_dir"])
        cls.lane = {
            "bundle_facts": cec.recompute_bundle_facts(packet_dir),
            "identities": cec.recompute_identities(packet_dir),
            "consistency": cec.recompute_consistency(
                cls.team["emission"], cls.team["determinism"],
                cls.team["attribution"]),
            "artifact_digest_pin_ok": cec.recompute_artifact_digest_pin(
                load(VEND / "ARTIFACT_DIGESTS.json")),
            "rules_label_sha256": sha256_file(
                REPO / "evaluation/frozen_bars/RULES_LABEL.json"),
            "rules_label_pin": load(HYP)[
                "frozen_inputs_rehashed_not_rewritten"][
                    "evaluation/frozen_bars/RULES_LABEL.json"],
        }

    def test_team_side_perturbation_detected(self) -> None:
        team = json.loads(json.dumps(self.team))
        team["emission"]["de-kapitalverletzung"]["after"]["n_scored"] = 9
        got = cec.compare(cec.extract_rows(team, self.lane))
        self.assertTrue(any(
            d["quantity"] == "after.n_scored.de-kapitalverletzung"
            for d in got["divergences"]))

    def test_lane_side_perturbation_detected(self) -> None:
        lane = json.loads(json.dumps(self.lane))
        lane["bundle_facts"]["de-kapitalverletzung"]["n_total_rows"] = 181
        got = cec.compare(cec.extract_rows(self.team, lane))
        self.assertTrue(any(
            d["quantity"] == "bundle.n_total_rows.de-kapitalverletzung"
            for d in got["divergences"]))

    def test_lane_identity_perturbation_detected(self) -> None:
        lane = json.loads(json.dumps(self.lane))
        lane["identities"]["packet.json"] = "0" * 64
        got = cec.compare(cec.extract_rows(self.team, lane))
        self.assertTrue(any(
            d["quantity"] == "identity.packet_json_sha256"
            for d in got["divergences"]))

    def test_team_bar_status_perturbation_detected(self) -> None:
        team = json.loads(json.dumps(self.team))
        team["emission"]["fr-bail-entretien"]["after"][
            "absolute_bar_status"]["status"] = "LABEL_SOUND"
        got = cec.compare(cec.extract_rows(team, self.lane))
        self.assertTrue(any(
            d["quantity"] == "after.absolute_status.fr-bail-entretien"
            for d in got["divergences"]))


class TestCommittedRecord(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.record = load(RESULT)

    def test_record_verdict_and_exit(self) -> None:
        self.assertEqual(self.record["verdict"], "CROSSCHECK_COMPLETE")
        self.assertEqual(self.record["exit_code"], 0)

    def test_headline_names_every_divergence_or_zero(self) -> None:
        comp = self.record["comparison"]
        self.assertEqual(comp["n_divergent"], 0)
        self.assertTrue(comp["headline"].startswith("ZERO_DIVERGENCE_ACROSS_"))
        self.assertIn(str(comp["n_match"]), comp["headline"])

    def test_every_frozen_quantity_emitted(self) -> None:
        emitted = {r["quantity"] for r in self.record["side_by_side"]}
        for q in load(HYP)["quantities_compared"]:
            with self.subTest(q=q):
                self.assertIn(q, emitted)
        self.assertEqual(self.record["extra_rows_beyond_frozen_list"], [])

    def test_not_comparable_rows_are_published_not_dropped(self) -> None:
        nc = [r for r in self.record["side_by_side"]
              if r.get("comparable") is False]
        self.assertEqual(len(nc), 6)
        for row in nc:
            self.assertIn("lane recomputation stands alone"
                          if "ce_empty" in row["quantity"]
                          else "lane-recomputed",
                          row.get("note") or "")

    def test_non_vacuity_all_hold_and_four_controls(self) -> None:
        self.assertTrue(self.record["non_vacuity_all_hold"])
        controls = self.record["non_vacuity_controls"]
        self.assertEqual(len(controls), 4)
        for c in controls:
            with self.subTest(name=c["name"]):
                self.assertTrue(c["detected"], c["name"])

    def test_identity_and_blob_checks_pass(self) -> None:
        self.assertTrue(self.record["identity_all_match"])
        blobs = self.record["blob_checks"]
        if blobs["performed"]:
            for name, meta in blobs["files"].items():
                with self.subTest(name=name):
                    self.assertTrue(meta["match"], name)

    def test_requirement_25_26_triples_published_together(self) -> None:
        triples = self.record["requirement_25_26_triples"]
        self.assertEqual(set(triples), set(cec.QIDS))
        for qid, t in triples.items():
            with self.subTest(qid=qid):
                self.assertEqual(t["support_rate_among_issued"], 0.0)
                self.assertEqual(t["n_emitted"], 0)
                self.assertGreater(t["abstention_count"], 0)
                self.assertEqual(t["yield_over_population"], 0.0)
                self.assertTrue(t["not_applicable_or_not_measured_is_never_a_pass"])

    def test_state_flags_all_false_and_orders_stand(self) -> None:
        flags = self.record["state_flags"]
        for key in ("human_gate_ready", "machine_gate_ready",
                    "packet_admitted", "ready_for_owner_session",
                    "owner_decision_required"):
            with self.subTest(key=key):
                self.assertFalse(flags[key], key)
        self.assertTrue(flags["do_not_serve_orders_stand"])

    def test_claim_ceiling_forbids_the_forbidden_claims(self) -> None:
        ceiling = self.record["claim_ceiling"]
        for phrase in ("does NOT certify LABEL_SOUND",
                       "authorises NO owner question",
                       "re-runs no closed charter",
                       "never asserts that any decision IS supporting"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, ceiling)

    def test_team_charter_closure_recorded(self) -> None:
        closure = self.record["team_charter_closure"]
        self.assertEqual(closure["team_run_id"], "39426324296")
        self.assertEqual(closure["outcome"], "A_EMISSION_RECOVERED")
        self.assertTrue(closure["this_lane_never_reruns_the_closed_charter"])


class TestInstrumentIsDeterministic(unittest.TestCase):
    def test_extraction_is_stable_across_two_calls(self) -> None:
        summary = load(VEND / "MEASUREMENT_SUMMARY.json")
        team = {
            "summary": summary,
            "emission": load(VEND / "EMISSION.json")["emission"],
            "attribution": load(VEND / "ATTRIBUTION.json")["attribution"],
            "determinism": load(VEND / "DETERMINISM.json")["determinism"],
            "non_vacuity": load(VEND / "NON_VACUITY.json")["non_vacuity"],
            "gate": load(VEND / "CYCLE_39426324296_GATE.json")[
                "evidence_summary"],
        }
        packet_dir = Path(load(HYP)["packet_identity_pins"]["packet_dir"])
        lane = {
            "bundle_facts": cec.recompute_bundle_facts(packet_dir),
            "identities": cec.recompute_identities(packet_dir),
            "consistency": cec.recompute_consistency(
                team["emission"], team["determinism"], team["attribution"]),
            "artifact_digest_pin_ok": cec.recompute_artifact_digest_pin(
                load(VEND / "ARTIFACT_DIGESTS.json")),
            "rules_label_sha256": sha256_file(
                REPO / "evaluation/frozen_bars/RULES_LABEL.json"),
            "rules_label_pin": load(HYP)[
                "frozen_inputs_rehashed_not_rewritten"][
                    "evaluation/frozen_bars/RULES_LABEL.json"],
        }
        first = json.dumps(cec.extract_rows(team, lane), sort_keys=True)
        second = json.dumps(cec.extract_rows(team, lane), sort_keys=True)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
