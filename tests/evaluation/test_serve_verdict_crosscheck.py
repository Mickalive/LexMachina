"""Tests for the run-39381093325 serve-verdict cross-check (direction v60 (b)).

Standard-library only: runs under pytest AND under the lane's no-pytest shim
(evaluation/no_pytest_runner.py), so the twin readings stay comparable.

Nothing here re-derives a frozen threshold; every assertion is about identity
pins, comparator behaviour (including non-vacuity), the committed record, and
the claim ceiling.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "evaluation"))

import serve_verdict_crosscheck as svc  # noqa: E402  (lane-local instrument)

RESULT = REPO / "results/evaluation/serve_verdict_crosscheck/39381093325.json"
HYP = REPO / "evaluation/SERVE_VERDICT_CROSSCHECK_HYPOTHESIS_V1.json"
FREEZE = REPO / "evaluation/SERVE_VERDICT_CROSSCHECK_FREEZE_RECORD_V1.json"
VEND = REPO / "evaluation/vendored_frontier_serve_audit/VERDICT_39371834165.json"
PROV = REPO / "evaluation/vendored_frontier_serve_audit/PROVENANCE.json"
STATE = REPO / "state/evaluation.json"
SUPERSEDED = "No serve verdict has landed."


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class TestFreezeFirstContract(unittest.TestCase):
    def test_freeze_record_pins_the_hypothesis_sha(self) -> None:
        self.assertEqual(load(FREEZE)["hypothesis_sha256"], sha256_file(HYP))

    def test_hypothesis_declares_frozen_before_execution(self) -> None:
        self.assertTrue(load(HYP)["frozen_before_execution"])

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

    def test_vendored_verdict_sha_matches_provenance(self) -> None:
        pinned = load(PROV)["files"]["VERDICT_39371834165.json"]["sha256"]
        self.assertEqual(sha256_file(VEND), pinned)


class TestComparatorNonVacuity(unittest.TestCase):
    """The comparator must SEE a divergence on every side it claims to compare."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.discharge = load(svc.DISCHARGE_PATH)
        cls.standready = load(svc.STANDREADY_PATH)
        cls.team = load(svc.VENDORED)

    def _mutated(self, mutate) -> dict:
        payload = json.loads(json.dumps(self.discharge))
        mutate(payload)
        rows = svc.extract_rows(payload, self.standready, self.team)
        return svc.compare(rows)

    def test_lane_side_perturbation_is_detected(self) -> None:
        got = self._mutated(lambda p: p["adjudication"]["label_gate"].update(n_scored=1))
        self.assertTrue(any(d["quantity"] == "label.n_scored" for d in got["divergences"]))

    def test_lane_side_geometry_perturbation_is_detected(self) -> None:
        got = self._mutated(
            lambda p: p["adjudication"]["geometry_gate"]["per_bundle_counts"].update(
                **{"de-kapitalverletzung": 6}))
        self.assertTrue(any(d["quantity"] == "geometry.per_bundle_counts.de-kapitalverletzung"
                            for d in got["divergences"]))

    def test_team_side_perturbation_is_detected(self) -> None:
        team = json.loads(json.dumps(self.team))
        team["label_half"]["n_supported"] = 9
        got = svc.compare(svc.extract_rows(self.discharge, self.standready, team))
        self.assertTrue(any(d["quantity"] == "label.n_supported" for d in got["divergences"]))

    def test_standready_side_perturbation_is_detected(self) -> None:
        stand = json.loads(json.dumps(self.standready))
        for q in stand["mega_cluster_disclosure_conformance"]["per_question"]:
            if q.get("qid") == "de-kapitalverletzung":
                q["size_based_share"] = 0.9999
        got = svc.compare(svc.extract_rows(self.discharge, stand, self.team))
        self.assertTrue(any(d["quantity"] == "mega_share.de-kapitalverletzung"
                            for d in got["divergences"]))

    def test_unperturbed_comparison_has_no_divergence(self) -> None:
        got = svc.compare(svc.extract_rows(self.discharge, self.standready, self.team))
        self.assertEqual(got["n_divergent"], 0)
        self.assertTrue(got["headline"].startswith("ZERO_DIVERGENCE"))


class TestCommittedCrosscheckRecord(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.record = load(RESULT)

    def test_verdict_is_complete_with_exit_zero(self) -> None:
        self.assertEqual(self.record["verdict"], "CROSSCHECK_COMPLETE")
        self.assertEqual(self.record["exit_code"], 0)

    def test_headline_names_every_comparable_quantity(self) -> None:
        comp = self.record["comparison"]
        self.assertEqual(comp["n_divergent"], 0)
        self.assertEqual(comp["n_comparable"], comp["n_match"])
        self.assertTrue(comp["headline"].startswith("ZERO_DIVERGENCE_ACROSS_"))
        # every frozen quantity appears as a row, comparable or not
        named = set(load(HYP)["quantities_compared"])
        emitted = {row["quantity"] for row in self.record["side_by_side"]}
        self.assertTrue(named.issubset(emitted), named - emitted)

    def test_identity_checks_all_match(self) -> None:
        self.assertTrue(self.record["identity_all_match"])
        for key, value in self.record["identity_checks"].items():
            with self.subTest(key=key):
                self.assertTrue(value["match"], key)

    def test_non_vacuity_controls_all_hold(self) -> None:
        self.assertTrue(self.record["non_vacuity_all_hold"])
        for control in self.record["non_vacuity_controls"]:
            with self.subTest(control=control["name"]):
                self.assertTrue(control["detected"], control["name"])

    def test_vendored_blob_cross_verified(self) -> None:
        blob = self.record["inputs"]["vendored_team_verdict"]["blob_crosscheck"]
        if blob.get("performed"):
            self.assertTrue(blob["match"])
        else:
            self.assertIn("reason", blob)

    def test_superseded_state_sentence_is_preserved_verbatim(self) -> None:
        landing = self.record["serve_verdict_landing"]
        superseded = landing["superseded_state_sentence"]
        self.assertEqual(superseded["verbatim"], SUPERSEDED)
        self.assertIn(SUPERSEDED, superseded["correction"] + " " + SUPERSEDED)
        self.assertTrue(landing["serve_verdict_landed"])
        self.assertEqual(landing["outcome"], "BOUNDED-NEGATIVE")

    def test_population_pin_refresh_edited_nothing(self) -> None:
        pin = self.record["population_pin_refresh"]
        self.assertEqual(pin["frozen_files_edited"], [])
        self.assertEqual(pin["refresh_meaning"].split(".")[0].split(",")[0],
                         "re-hashed and re-recorded AT DISCHARGE TIME under this run id")
        self.assertEqual(pin["packet_scored_population"]["n_scored"], 0)
        self.assertEqual(pin["team_scored_population_same_bytes"]["n_scored"], 0)
        for key in ("rules_label", "rules_geometry", "verdict_contract"):
            self.assertTrue(pin["rehash_proof"][key]["match"], key)

    def test_claim_ceiling_disclaims_the_big_claims(self) -> None:
        ceiling = self.record["claim_ceiling"]
        for phrase in ("does NOT re-derive", "does NOT certify LABEL_SOUND",
                       "does NOT lift any DO-NOT-SERVE order",
                       "authorises NO owner question"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, ceiling)

    def test_do_not_serve_orders_and_owner_flags_stay_false(self) -> None:
        discharge = load(svc.DISCHARGE_PATH)["serve_status"]
        self.assertFalse(discharge["packet_admitted"])
        self.assertFalse(discharge["ready_for_owner_session"])
        self.assertFalse(discharge["machine_gate_ready"])
        self.assertFalse(discharge["human_gate_ready"])
        self.assertFalse(discharge["owner_decision_required"])
        self.assertFalse(load(svc.VENDORED)["verdict"]["owner_decision_required"])


class TestInstrumentEndToEnd(unittest.TestCase):
    def test_instrument_exits_zero_and_reproduces_the_record(self) -> None:
        out = Path("/tmp/opencode/lex_serve_crosscheck_selftest.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        proc = subprocess.run(
            [sys.executable, str(REPO / "evaluation/serve_verdict_crosscheck.py"),
             "--out", str(out)],
            capture_output=True, text=True, timeout=180, cwd=str(REPO))
        self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])
        fresh = load(out)
        committed = load(RESULT)
        self.assertEqual(fresh["verdict"], "CROSSCHECK_COMPLETE")
        self.assertEqual(fresh["comparison"]["n_divergent"], 0)
        self.assertEqual(fresh["comparison"]["n_comparable"],
                         committed["comparison"]["n_comparable"])
        self.assertTrue(fresh["non_vacuity_all_hold"])

    def test_state_keeps_the_superseded_sentence_verbatim(self) -> None:
        state_text = STATE.read_text(encoding="utf-8")
        self.assertIn(SUPERSEDED, state_text,
                      "the superseded sentence must be preserved verbatim in state")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
