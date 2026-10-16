"""Label-half and geometry-half smoke tests on the served packet.

These tests score real served-packet rows under the frozen rubrics and check
the named populations (65 issued labels, 16 empty-evidence rows, the three
bundle geometries). They are claim-bearing only about SUPPORT and GEOMETRY
SEMANTICS, never about whether any specific decision is supporting/contrary/
limiting.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "frontier", "frontier-served-packet-falsification"))

from frontier_served_packet_falsification import (  # noqa: E402
    BUNDLE_SHA256,
    RULES_GEOMETRY_SHA256,
    RULES_LABEL_SHA256,
    TEAM_ID,
)
from frontier_served_packet_falsification.label_half import run_label_half  # noqa: E402
from frontier_served_packet_falsification.geometry_half import run_geometry_half  # noqa: E402

RESULTS = os.path.join(REPO, "results", "frontier", TEAM_ID)
PACKET = os.path.join(REPO, "results", "product", "gate_packet", "38839347028")
if not os.path.isdir(PACKET):
    PACKET = os.path.join(
        "/tmp/lex_accepted/core/product", "results", "product", "gate_packet", "38839347028"
    )


def _sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class TestLabelHalf(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.label = run_label_half(
            os.path.join(RESULTS, "RULES_LABEL.json"),
            PACKET,
            BUNDLE_SHA256,
            expected_rules_sha256=RULES_LABEL_SHA256,
        )

    def test_rules_byte_identity(self):
        self.assertTrue(self.label["rules_byte_identity_ok"])
        self.assertEqual(self.label["rules_sha256"], RULES_LABEL_SHA256)

    def test_population_is_65(self):
        self.assertEqual(self.label["n_scored"], 65)

    def test_verdict_is_label_unsound_or_sound(self):
        self.assertIn(self.label["verdict"], ("LABEL_SOUND", "LABEL_UNSOUND"))
        # With 5 supported of 65, verdict must be LABEL_UNSOUND (absolute bar).
        self.assertEqual(self.label["verdict"], "LABEL_UNSOUND")

    def test_support_rate_matches_counts(self):
        o = self.label["overall"]
        self.assertEqual(o["n_scored"], 65)
        self.assertEqual(o["n_supported"], 5)
        self.assertAlmostEqual(o["support_rate"], 5 / 65)

    def test_defect_classes_cover_all_rows(self):
        o = self.label["overall"]
        total = sum(v["count"] for v in o["defect_classes"].values())
        self.assertEqual(total, 65)

    def test_sixteen_empty_evidence_rows_each_unbacked(self):
        o = self.label["overall"]
        self.assertEqual(o["n_empty_evidence_at_uncertainty_ge_0_95"], 16)
        for row in o["empty_evidence_at_uncertainty_ge_0_95_rows"]:
            self.assertEqual(row["primary_defect_class"], "UNBACKED")
            self.assertEqual(row["reason_code"], "evidence_absent")
            self.assertFalse(row["supported"])

    def test_counter_evidence_verified_never_false(self):
        dist = self.label["overall"]["counter_evidence_verified_distribution"]
        self.assertEqual(dist["present_false"], 0)
        self.assertEqual(dist["absent"], 16)
        self.assertEqual(dist["present_true"], 49)

    def test_non_vacuity_injection_passed(self):
        self.assertTrue(self.label["non_vacuity"]["passed"])

    def test_population_nonvacuity_reports_real_supported(self):
        pn = self.label["population_nonvacuity"]
        self.assertTrue(pn["at_least_one_real_row_supported"])
        self.assertEqual(pn["n_real_rows_scored_supported"], 5)

    def test_per_bundle_counts(self):
        by_qid = {b["qid"]: b for b in self.label["bundles"]}
        self.assertEqual(by_qid["de-kapitalverletzung"]["n_scored"], 25)
        self.assertEqual(by_qid["fr-bail-entretien"]["n_scored"], 15)
        self.assertEqual(by_qid["it-responsabilita-medica"]["n_scored"], 25)

    def test_no_threshold_of_our_own(self):
        # The verdict threshold is the frozen 1.0, not a new bar.
        self.assertEqual(self.label["threshold_support_rate_sound"], 1.0)


class TestGeometryHalf(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.geo = run_geometry_half(
            os.path.join(RESULTS, "RULES_GEOMETRY.json"),
            PACKET,
            BUNDLE_SHA256,
            expected_rules_sha256=RULES_GEOMETRY_SHA256,
        )

    def test_rules_byte_identity(self):
        self.assertTrue(self.geo["rules_byte_identity_ok"])
        self.assertEqual(self.geo["rules_sha256"], RULES_GEOMETRY_SHA256)

    def test_verdict_is_fail(self):
        self.assertEqual(self.geo["verdict"], "FAIL")
        self.assertEqual(self.geo["n_bundles_pass"], 0)

    def test_all_eleven_criteria_present(self):
        for b in self.geo["bundles"]:
            self.assertEqual(len(b["criteria"]), 11)
            self.assertEqual(b["n_criteria"], 11)

    def test_french_largest_share_fails_bar(self):
        fr = next(b for b in self.geo["bundles"] if b["qid"] == "fr-bail-entretien")
        self.assertFalse(fr["criteria"]["STRUCTURE_LARGEST"]["pass"])
        self.assertAlmostEqual(
            fr["largest_share_both_definitions"]["largest_share_size_field"],
            0.7696,
            places=3,
        )
        self.assertFalse(fr["criteria"]["STRUCTURE_LARGEST"]["pass"])

    def test_both_largest_share_definitions_reported(self):
        for b in self.geo["bundles"]:
            both = b["largest_share_both_definitions"]
            self.assertIn("largest_share_size_field", both)
            self.assertIn("largest_share_member_ids", both)
            self.assertIn("member_ids_capped_at_50", both)
            # member_ids is capped: must undercount on any cluster > 50
            if both["member_ids_capped_at_50"]:
                self.assertLessEqual(
                    both["largest_share_member_ids"],
                    both["largest_share_size_field"] + 1e-9,
                )

    def test_ablation_present_side_by_side(self):
        for b in self.geo["bundles"]:
            ab = b["ablation"]
            self.assertIn("ARTIFACT", ab)
            self.assertIn("shipped_largest_share", ab)
            self.assertIn("hydrated_largest_share", ab)
            self.assertIn("side_by_side", ab)

    def test_per_bundle_pass_counts_in_expected_range(self):
        counts = {b["qid"]: b["n_pass"] for b in self.geo["bundles"]}
        # de improved 5->6, it improved 4->5, fr stayed 5
        self.assertEqual(counts["de-kapitalverletzung"], 6)
        self.assertEqual(counts["fr-bail-entretien"], 5)
        self.assertEqual(counts["it-responsabilita-medica"], 5)


class TestBeforeAfter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from frontier_served_packet_falsification.before_after import build_before_after

        label = run_label_half(
            os.path.join(RESULTS, "RULES_LABEL.json"),
            PACKET,
            BUNDLE_SHA256,
            expected_rules_sha256=RULES_LABEL_SHA256,
        )
        geo = run_geometry_half(
            os.path.join(RESULTS, "RULES_GEOMETRY.json"),
            PACKET,
            BUNDLE_SHA256,
            expected_rules_sha256=RULES_GEOMETRY_SHA256,
        )
        cls.ba = build_before_after(label, geo)

    def test_baselines_marked_pre_repair(self):
        self.assertTrue(self.ba["label_half"]["before"]["pre_repair"])
        self.assertTrue(self.ba["geometry_half"]["before"]["pre_repair"])
        self.assertTrue(self.ba["mark_every_baseline_pre_repair"])

    def test_label_direction_improved(self):
        self.assertEqual(self.ba["label_half"]["direction_support_rate"], "IMPROVED")
        self.assertAlmostEqual(self.ba["label_half"]["delta_support_rate"], 5 / 65)

    def test_geometry_french_share_regressed(self):
        fr = next(
            p for p in self.ba["geometry_half"]["after"]["per_bundle"]
            if p["qid"] == "fr-bail-entretien"
        )
        self.assertEqual(fr["largest_share_direction"], "REGRESSED")
        self.assertEqual(fr["n_pass_direction"], "SAME")

    def test_geometry_de_it_improved_pass_counts(self):
        de = next(
            p for p in self.ba["geometry_half"]["after"]["per_bundle"]
            if p["qid"] == "de-kapitalverletzung"
        )
        it = next(
            p for p in self.ba["geometry_half"]["after"]["per_bundle"]
            if p["qid"] == "it-responsabilita-medica"
        )
        self.assertEqual(de["n_pass_direction"], "IMPROVED")
        self.assertEqual(it["n_pass_direction"], "IMPROVED")


if __name__ == "__main__":
    unittest.main()
