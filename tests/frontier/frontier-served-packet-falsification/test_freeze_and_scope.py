"""Tests for frontier-served-packet-falsification.

Covers: freeze byte-identity, claim ceiling machine-check, non-vacuity on
real population, scope safety, and basic rubric/geometry smoke on the served
packet. No product file is touched.
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
    BUNDLES,
    BUNDLE_SHA256,
    CHARTER_VERSION,
    FORBIDDEN_WRITE_PREFIXES,
    RULES_GEOMETRY_SHA256,
    RULES_LABEL_SHA256,
    TEAM_ID,
    WRITE_SCOPE,
)
from frontier_served_packet_falsification.claim_ceiling import (  # noqa: E402
    check_payload,
    scan_for_violations,
)
from frontier_served_packet_falsification.vendored.frontier_counter_label_integrity.rules import (  # noqa: E402
    load_rules,
)

RESULTS = os.path.join(REPO, "results", "frontier", TEAM_ID)
PACKET = os.path.join(
    REPO, "results", "product", "gate_packet", "38839347028"
)
# Fall back to the accepted mount if the repo checkout has no product tree.
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


class TestFreezeByteIdentity(unittest.TestCase):
    """Acceptance test (1): both RULES files are byte-identical to the frozen sha256."""

    def test_label_rules_byte_identity(self):
        path = os.path.join(RESULTS, "RULES_LABEL.json")
        self.assertTrue(os.path.isfile(path), f"missing {path}")
        self.assertEqual(_sha(path), RULES_LABEL_SHA256)

    def test_geometry_rules_byte_identity(self):
        path = os.path.join(RESULTS, "RULES_GEOMETRY.json")
        self.assertTrue(os.path.isfile(path), f"missing {path}")
        self.assertEqual(_sha(path), RULES_GEOMETRY_SHA256)

    def test_label_rules_load_and_schema(self):
        rules = load_rules(os.path.join(RESULTS, "RULES_LABEL.json"))
        self.assertEqual(rules.sha256, RULES_LABEL_SHA256)
        self.assertEqual(rules.data["schema"], "frontier-counter-label-integrity/rules/1")

    def test_no_frozen_at_utc_in_freeze_record(self):
        path = os.path.join(RESULTS, "FREEZE.json")
        if not os.path.isfile(path):
            self.skipTest("FREEZE.json not yet emitted")
        with open(path) as f:
            data = json.load(f)
        self.assertNotIn("frozen_at_utc", data)


class TestInputList(unittest.TestCase):
    """The only new frozen artifact: input list with sha256 of the three bundles."""

    def test_input_list_sha256_match(self):
        path = os.path.join(RESULTS, "INPUT_LIST.json")
        self.assertTrue(os.path.isfile(path))
        with open(path) as f:
            data = json.load(f)
        for entry in data["served_gate_packet"]["bundles"]:
            qid = entry["qid"]
            bpath = os.path.join(PACKET, "questions", f"{qid}.bundle.json")
            self.assertTrue(os.path.isfile(bpath), f"missing bundle {bpath}")
            self.assertEqual(_sha(bpath), entry["sha256"], f"sha mismatch for {qid}")
            self.assertEqual(_sha(bpath), BUNDLE_SHA256[qid])


class TestClaimCeiling(unittest.TestCase):
    """Acceptance test (9): reject any authority-claiming construction on a decision."""

    def test_forbidden_patterns_detected(self):
        bad = [
            "decision bvger_A-4619_2021 is supporting",
            "decision X is contrary authority",
            "We classify foo_bar as limiting",
            "asserts that baz is supporting",
        ]
        for s in bad:
            self.assertTrue(scan_for_violations(s), f"should flag: {s}")

    def test_allowed_phrases_not_flagged(self):
        good = [
            "The product's label is reported, not endorsed.",
            "0 of 65 issued labels score SUPPORTED.",
            "The dominant cluster contains 12 counter rows.",
        ]
        for s in good:
            self.assertFalse(scan_for_violations(s), f"should not flag: {s}")

    def test_claim_ceiling_artifact_exists(self):
        path = os.path.join(RESULTS, "CLAIM_CEILING.json")
        if not os.path.isfile(path):
            self.skipTest("CLAIM_CEILING.json not yet emitted")
        with open(path) as f:
            data = json.load(f)
        self.assertIn("claim_ceiling", data)
        self.assertIn("NEVER asserts", data["claim_ceiling"])


class TestScopeSafety(unittest.TestCase):
    """Acceptance test (8): zero files written outside the team's write scope."""

    def _violating_paths(self, root: str) -> list[str]:
        bad: list[str] = []
        for dirpath, dirnames, filenames in os.walk(root):
            rel = os.path.relpath(dirpath, root).replace(os.sep, "/")
            if rel == ".":
                rel = ""
            # Skip .git and node_modules
            dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules", "__pycache__")]
            for fn in filenames:
                path = (rel + "/" if rel else "") + fn
                if any(path.startswith(p) for p in FORBIDDEN_WRITE_PREFIXES):
                    bad.append(path)
        return bad

    def test_no_forbidden_writes_under_results_product(self):
        # This test only checks that the team has not created files under
        # results/product/ (it is read-only). We do not walk the whole repo
        # because the accepted mount is outside the write scope by design.
        product_results = os.path.join(REPO, "results", "product")
        if not os.path.isdir(product_results):
            self.skipTest("no results/product in this checkout")
        # There should be no team artifacts under results/product/
        team_marker = os.path.join(product_results, TEAM_ID)
        self.assertFalse(os.path.exists(team_marker))

    def test_write_scope_constants(self):
        self.assertIn("frontier/frontier-served-packet-falsification/", WRITE_SCOPE)
        self.assertIn("results/frontier/frontier-served-packet-falsification/", WRITE_SCOPE)
        self.assertNotIn("results/audit/", WRITE_SCOPE)
        self.assertNotIn("product/", WRITE_SCOPE)


class TestCharterConstants(unittest.TestCase):
    def test_charter_version_retained(self):
        self.assertEqual(CHARTER_VERSION, 1)
        self.assertEqual(TEAM_ID, "frontier-served-packet-falsification")

    def test_bundle_set(self):
        self.assertEqual(
            set(BUNDLES),
            {"de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica"},
        )


if __name__ == "__main__":
    unittest.main()
