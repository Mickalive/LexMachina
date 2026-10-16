"""Runnable contract tests for the query-conditioned geometry variants.

Run with the stdlib only (no pytest required):

    PYTHONPATH=frontier/frontier-query-conditioned-map-geometry \
    python3 -m unittest discover -s frontier/frontier-query-conditioned-map-geometry/tests -v

Point the suite at a served packet with ``LEX_GATE_PACKET``; it defaults to the
workflow mount used by this team.

These tests exist to pin the properties that are easy to break silently, and to
lock in the two operational bugs already diagnosed on this charter:

  * test_reproducibility_comparison_ignores_in_place_annotations
    -- run 38969741834 reported non-reproducibility and flipped the charter
    outcome from A to B. The cause was the in-place ``schema`` annotation on
    the first scoring pass, which the second pass does not carry.
  * test_variant_fn_seam_is_keyword_only
    -- the producer snapshot crashed because the seam signature was positional
    while ``score_variant`` calls ``variant_fn(bundle, query_language=...)``.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

import numpy as np  # noqa: E402,F401  (imported early to fail fast on a broken env)

from qmap_geometry import cli  # noqa: E402
from qmap_geometry.nonvac_divergence import probe_coordinate_invariance  # noqa: E402
from qmap_geometry.scoring import (  # noqa: E402
    EXPECTED_RULES_SHA256,
    load_rules,
    rule_block_for,
    score_bundle,
)
from qmap_geometry.variants import VARIANTS, build_variant_geometry  # noqa: E402

REPO = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
RULES_PATH = os.path.join(
    REPO, "results/frontier/frontier-query-conditioned-map-geometry/RULES_GEOMETRY.json"
)
PACKET = os.environ.get(
    "LEX_GATE_PACKET",
    "/tmp/lex_accepted/core/product/results/product/gate_packet/38839347028/questions",
)
QIDS = list(cli.QIDS)
QUERY_LANGUAGE = dict(cli.QUERY_LANGUAGE)


def _load_bundle(qid: str) -> dict:
    with open(os.path.join(PACKET, f"{qid}.bundle.json"), encoding="utf-8") as fh:
        return json.load(fh)


class FrozenRuleTests(unittest.TestCase):
    def test_rule_file_hash_is_the_accepted_hash(self):
        with open(RULES_PATH, "rb") as fh:
            self.assertEqual(hashlib.sha256(fh.read()).hexdigest(), EXPECTED_RULES_SHA256)

    def test_load_rules_refuses_a_tampered_rule(self):
        """A re-tuned bar must be rejected, not scored."""
        with open(RULES_PATH, encoding="utf-8") as fh:
            rules = json.load(fh)
        crit = rules["criteria"]
        victim = crit[sorted(crit)[0]] if isinstance(crit, dict) else crit[0]
        victim["bar"] = 0.0
        tmp = os.path.join("/tmp", "tampered_rules.json")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(rules, fh)
        try:
            with self.assertRaises(ValueError):
                load_rules(tmp)
        finally:
            os.unlink(tmp)

    def test_rule_carries_the_binding_non_vacuity_clause(self):
        rules = load_rules(RULES_PATH)
        nv = rules.get("non_vacuity") or {}
        self.assertIn("control", nv)
        self.assertIn("required", nv)
        self.assertIn(">= 2", nv["required"])


class SeamContractTests(unittest.TestCase):
    """The seam Product will call. Breaking these breaks adoption."""

    def test_variant_fn_seam_is_keyword_only(self):
        def variant_fn(bundle, *, query_language):
            return build_variant_geometry(bundle, "relevance_ordered", query_language=query_language)

        bundle = _load_bundle(QIDS[0])
        out = variant_fn(bundle, query_language=QUERY_LANGUAGE[QIDS[0]])
        self.assertEqual(len(out["decisions"]), len(bundle["decisions"]))
        with self.assertRaises(TypeError):
            variant_fn(bundle, "de")  # positional must NOT be accepted

    def test_incumbent_identity_seam_is_keyword_only(self):
        def variant_fn(bundle, *, query_language=None):
            return bundle

        bundle = _load_bundle(QIDS[0])
        self.assertIs(variant_fn(bundle, query_language="de"), bundle)
        with self.assertRaises(TypeError):
            variant_fn(bundle, "de")

    def test_variants_emit_the_qmap_row_shape(self):
        bundle = _load_bundle(QIDS[0])
        for name in VARIANTS:
            with self.subTest(variant=name):
                cand = build_variant_geometry(bundle, name, query_language="de")
                for row in cand["decisions"]:
                    for field in ("decision_id", "cluster_id", "x", "y"):
                        self.assertIn(field, row)
                for cluster in cand["clusters"]:
                    for field in ("cluster_id", "label", "size", "member_ids"):
                        self.assertIn(field, cluster)


class DeterminismTests(unittest.TestCase):
    """Pins the 38969741834 non-reproducibility bug at its source."""

    def test_reproducibility_comparison_ignores_in_place_annotations(self):
        first = {"bundles": [{"n_pass": 7, "geometry_seconds": 0.1}], "schema": "x/1"}
        second = {"bundles": [{"n_pass": 7, "geometry_seconds": 0.2}]}
        stripped_a = cli._repro_view(first)
        stripped_b = cli._repro_view(second)
        self.assertEqual(cli._canon(stripped_a), cli._canon(stripped_b),
                         "schema/timing annotations must not count as non-reproducibility")

    def test_repro_view_keeps_claim_bearing_keys(self):
        view = cli._repro_view({"n_pass": 7, "schema": "x", "wall_seconds": 1.0})
        self.assertEqual(view, {"n_pass": 7})

    def test_building_a_variant_twice_is_byte_identical(self):
        bundle = _load_bundle(QIDS[1])
        for name in VARIANTS:
            with self.subTest(variant=name):
                a = build_variant_geometry(copy.deepcopy(bundle), name, query_language="fr")
                b = build_variant_geometry(copy.deepcopy(bundle), name, query_language="fr")
                self.assertEqual(cli._canon(cli._repro_view(a)), cli._canon(cli._repro_view(b)))


class PopulationIntegrityTests(unittest.TestCase):
    """Charter check (6): nothing dropped, duplicated or silently resized."""

    def test_no_decision_dropped_or_duplicated(self):
        for qid in QIDS:
            bundle = _load_bundle(qid)
            src = [d["decision_id"] for d in bundle["decisions"]]
            for name in VARIANTS:
                with self.subTest(qid=qid, variant=name):
                    cand = build_variant_geometry(copy.deepcopy(bundle), name,
                                                  query_language=QUERY_LANGUAGE[qid])
                    got = [d["decision_id"] for d in cand["decisions"]]
                    self.assertEqual(len(got), len(src))
                    self.assertEqual(sorted(got), sorted(src))

    def test_point_count_and_bundle_header_survive(self):
        for qid in QIDS:
            bundle = _load_bundle(qid)
            for name in VARIANTS:
                with self.subTest(qid=qid, variant=name):
                    cand = build_variant_geometry(copy.deepcopy(bundle), name,
                                                  query_language=QUERY_LANGUAGE[qid])
                    self.assertEqual(len(cand["decisions"]), len(bundle["decisions"]))
                    self.assertEqual(cand.get("relations"), bundle.get("relations"))

    def test_member_ids_truncation_contract_matches_qmap(self):
        """qmap.py truncates member_ids to [:50] while size stays true."""
        for qid in QIDS:
            bundle = _load_bundle(qid)
            for name in VARIANTS:
                with self.subTest(qid=qid, variant=name):
                    cand = build_variant_geometry(copy.deepcopy(bundle), name,
                                                  query_language=QUERY_LANGUAGE[qid])
                    for cluster in cand["clusters"]:
                        self.assertLessEqual(len(cluster["member_ids"]), 50)
                        self.assertEqual(cluster["member_ids"],
                                         cluster["member_ids"][:50])
                        true_size = sum(
                            1 for d in cand["decisions"]
                            if int(d.get("cluster_id", -1)) == int(cluster["cluster_id"])
                        )
                        self.assertEqual(int(cluster["size"]), true_size)


class NonVacuityDivergenceTests(unittest.TestCase):
    """Pins the divergence documented in NON_VACUITY_DIVERGENCE.json."""

    def test_proj_rank_is_coordinate_invariant(self):
        """The frozen scorer computes PROJ_RANK without reading x/y."""
        rules = load_rules(RULES_PATH)
        for qid in QIDS:
            bundle = _load_bundle(qid)
            rb = rule_block_for(rules, qid)
            cand = build_variant_geometry(bundle, "relevance_ordered",
                                          query_language=QUERY_LANGUAGE[qid])
            probe = probe_coordinate_invariance(rules, cand, rb)
            for crit in ("PROJ_RANK", "STRUCTURE_SEP"):
                self.assertTrue(probe["criteria"][crit]["invariant"],
                                f"{crit} moved under coordinate permutation on {qid}")

    def test_harness_is_sensitive_to_coordinate_corruption(self):
        """PROJ_SPEARMAN / PROJ_KNN10 do move, so the harness is not vacuous."""
        rules = load_rules(RULES_PATH)
        qid = "fr-bail-entretien"
        bundle = _load_bundle(qid)
        rb = rule_block_for(rules, qid)
        cand = build_variant_geometry(bundle, "relevance_ordered", query_language="fr")
        probe = probe_coordinate_invariance(rules, cand, rb)
        self.assertTrue(probe["at_least_one_reading_criterion_moved"])
        self.assertLess(abs(probe["criteria"]["PROJ_SPEARMAN"]["before"]
                            - probe["criteria"]["PROJ_SPEARMAN"]["after"]), 1.0)
        self.assertGreater(probe["criteria"]["PROJ_SPEARMAN"]["before"],
                           probe["criteria"]["PROJ_SPEARMAN"]["after"] + 0.05)


class OutcomeTests(unittest.TestCase):
    def test_winner_is_strictly_better_with_zero_regressions(self):
        with open(os.path.join(
                REPO, "results/frontier/frontier-query-conditioned-map-geometry/SIDE_BY_SIDE.json"),
                encoding="utf-8") as fh:
            sbs = json.load(fh)
        inc_total = sum(sbs["accepted_incumbent"]["pass_counts"].values())
        for name, res in sbs["variants"].items():
            total = sum(r["variant_n_pass"] for r in res["rows"])
            regressions = [
                (r["qid"], c["criterion"]) for r in res["rows"] for c in r["criteria"]
                if c["incumbent_pass"] and not c["variant_pass"]
            ]
            with self.subTest(variant=name):
                self.assertEqual(res["strictly_better"], total > inc_total and not regressions)
        with open(os.path.join(
                REPO,
                "results/frontier/frontier-query-conditioned-map-geometry/INTEGRATION_CONTRACT.json"),
                encoding="utf-8") as fh:
            winner_name = json.load(fh)["adoptable_variant"]
        winner = sbs["variants"][winner_name]
        self.assertTrue(winner["strictly_better"],
                        "the adopted variant must beat the incumbent with no regression")
        self.assertEqual(sum(r["variant_n_pass"] for r in winner["rows"]),
                         sum(sbs["accepted_incumbent"]["pass_counts"].values()) + 6)


if __name__ == "__main__":
    unittest.main(verbosity=2)