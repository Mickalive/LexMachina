"""Frontier ``frontier-adversarial-discoverability`` — frozen-measurement tests.

Run offline, deterministic, no network::

    cd frontier/frontier-adversarial-discoverability
    python3 -m unittest discover -s ../../tests/frontier/frontier-adversarial-discoverability -t ../../.. -v

These tests do two jobs:
  1. prove the harness itself is correct and non-vacuous (synthetic inputs with
     hand-computed answers, corruption determinism, integrity abort);
  2. lock the accepted-artifact findings so a later change cannot quietly move a
     number that this cycle published.

No network. No writes outside this team's namespace.
"""
from __future__ import annotations

import copy
import json
import re
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
TEAM_DIR = REPO_ROOT / "frontier" / "frontier-adversarial-discoverability"
RESULTS_DIR = REPO_ROOT / "results" / "frontier" / "frontier-adversarial-discoverability"
MOUNT = Path(os.environ.get("LEX_PRODUCT_MOUNT", "/tmp/lex_accepted/core/product"))
RULES_PATH = RESULTS_DIR / "RULES.json"

if str(TEAM_DIR) not in sys.path:
    sys.path.insert(0, str(TEAM_DIR))

from adversarial_discoverability import (  # noqa: E402
    COUNTER_VALUES, PLACEHOLDER_EVIDENCE, corrupt, metrics as M, populations as pop,
)
from adversarial_discoverability import harness as H  # noqa: E402


# ---------------------------------------------------------------------------
# synthetic fixtures with hand-computed answers
# ---------------------------------------------------------------------------

def _dec(did, rank, status="none", **kw):
    row = {
        "decision_id": did, "rank": rank, "counter_status": status,
        "language": "de", "decision_date": "2015-01-01", "cluster_id": 0,
        "is_outlier": False, "channels": ["search"], "counter_evidence": "",
        "counter_reason": "", "counter_evidence_verified": False,
    }
    row.update(kw)
    return row


def _bundle(rows, channels=None, clusters=None):
    return {
        "bundle_version": "1.0",
        "query": "synthetic",
        "decisions": rows,
        "clusters": clusters or [{"cluster_id": 0, "label": "consensus", "size": len(rows),
                                  "member_ids": [r["decision_id"] for r in rows]}],
        "answer": {"prose": "prose", "cited_decision_ids": []},
        "provenance": {
            "retrieval": {"candidate_channels": channels or {"search": len(rows),
                                                            "search.language_filter": 0},
                          "dedupe": {"candidates_by_channel": channels or {"search": len(rows)}}},
            "retrieval_first_page": {"candidate_channels": channels or {"search": len(rows)}},
            "generative_audit": {},
        },
    }


class TestPopulations(unittest.TestCase):
    def test_counter_vs_challenged_populations(self):
        rows = [_dec("a", 1, "candidate-contrary"), _dec("b", 2, "cited"), _dec("c", 3, "none")]
        self.assertEqual([d["decision_id"] for d in pop.c_strict(rows)], ["a"])
        self.assertEqual([d["decision_id"] for d in pop.c_challenged(rows)], ["a", "b"])

    def test_counter_values_are_the_charter_literal_four(self):
        self.assertEqual(set(COUNTER_VALUES),
                         {"candidate-limiting", "candidate-contrary",
                          "contrary_or_exception", "limiting"})

    def test_consensus_cluster_is_rank_one(self):
        doc = _bundle([_dec("a", 40, cluster_id=3), _dec("b", 1, cluster_id=0)])
        self.assertEqual(pop.consensus_cluster(doc), 0)

    def test_bundle_total_uses_decision_count_for_legs(self):
        rows = [_dec("a", 1, "candidate-limiting"), _dec("b", 2)]
        self.assertEqual(pop.bundle_total({"decisions": rows}, rows, "decisions"), 2)
        leg = {"cited_decisions": rows, "decision_count": 165}
        self.assertEqual(pop.bundle_total(leg, rows, "cited_decisions"), 165)

    def test_placeholder_detection(self):
        self.assertTrue(pop.placeholder_evidence({"counter_evidence": PLACEHOLDER_EVIDENCE}))
        self.assertFalse(pop.placeholder_evidence({"counter_evidence": "a real quote"}))


class TestMetricsOnSynthetic(unittest.TestCase):
    def test_counter_yield_threshold(self):
        rows = [_dec("x%d" % i, i, "candidate-contrary" if i <= 1 else "none") for i in range(1, 101)]
        m = M.metric_a_counter_yield(_bundle(rows), rows, 100)
        self.assertEqual(m["value"], 0.01)
        self.assertEqual(m["verdict"], "FAIL")  # below frozen MIN_COUNTER_YIELD 0.02
        rows2 = [_dec("x%d" % i, i, "candidate-contrary" if i <= 2 else "none") for i in range(1, 101)]
        m2 = M.metric_a_counter_yield(_bundle(rows2), rows2, 100)
        self.assertEqual(m2["value"], 0.02)
        self.assertEqual(m2["verdict"], "PASS")

    def test_rank_placement_metric(self):
        rows = ([_dec("top", 1, "candidate-contrary")]
                + [_dec("f%d" % i, i, "none") for i in range(2, 31)]
                + [_dec("deep", 60, "candidate-contrary")])
        m = M.metric_c_rank_placement(_bundle(rows), rows)
        self.assertEqual(m["counter_ranks"], [1, 60])
        self.assertEqual(m["beyond_top20_share"], 0.5)
        self.assertEqual(m["verdict"], "PASS")

    def test_placement_visibility_metric(self):
        rows = [_dec("c1", 1, "candidate-contrary", cluster_id=0),
                _dec("c2", 5, "candidate-contrary", cluster_id=7, is_outlier=True),
                _dec("n", 9)]
        m = M.metric_d_placement(_bundle(rows), rows)
        self.assertEqual(m["discoverable_placement_share"], 0.5)
        self.assertEqual(m["verdict"], "PASS")

    def test_evidence_quality_metric(self):
        rows = [_dec("c1", 1, "candidate-limiting", counter_evidence_verified=True,
                     counter_reason="limiting", counter_evidence="verbatim quote"),
                _dec("c2", 2, "candidate-limiting", counter_evidence=PLACEHOLDER_EVIDENCE)]
        m = M.metric_e_evidence(_bundle(rows), rows)
        self.assertEqual(m["verified_with_reason_share"], 0.5)
        self.assertEqual(m["placeholder_evidence_share"], 0.5)
        self.assertEqual(m["verdict"], "PASS")

    def test_minority_reach_metric(self):
        rows = [_dec("c1", 1, "candidate-contrary", language="fr", decision_date="1990-01-01"),
                _dec("n1", 2, "none", decision_date="2015-01-01")]
        m = M.metric_g_minority_reach(_bundle(rows), rows)
        self.assertEqual(m["minority_reach_share"], 1.0)
        self.assertEqual(m["verdict"], "PASS")

    def test_answer_linkage_is_never_gated(self):
        rows = [_dec("c1", 1, "candidate-contrary")]
        doc = _bundle(rows)
        doc["answer"] = {"prose": "see c1 for the rule", "cited_decision_ids": []}
        m = M.metric_f_answer_linkage(doc, rows)
        self.assertEqual(m["verdict"], "OBSERVED")
        self.assertEqual(m["answer_mentions_counter_share"], 1.0)

    def test_b_metric_flags_only_genuinely_new_channels(self):
        rows = [_dec("c1", 1, "candidate-contrary", channels=["search"]),
                _dec("c2", 2, "candidate-contrary", channels=["adversarial.negation_search.v1"]),
                _dec("n", 3)]
        doc = _bundle(rows, channels={"search": 2})
        m = M.metric_b_marginal_retrieval(doc, rows, shortlist={"c1", "c2"})
        self.assertEqual(m["b1_adversarial_channel_rows"], 1)
        self.assertEqual(m["b2_new_channels"], ["adversarial.negation_search.v1"])
        self.assertEqual(m["verdict"], "PASS")

    def test_b_metric_is_not_applicable_without_retrieval_provenance(self):
        rows = [_dec("c1", 1, "candidate-contrary")]
        doc = {"decisions": rows, "clusters": [], "answer": {}}
        m = M.metric_b_marginal_retrieval(doc, rows)
        self.assertEqual(m["verdict"], "NOT_APPLICABLE")

    def test_missing_schema_is_not_applicable_not_zero(self):
        """A leg artifact that does not export a field must not score 0 on it."""
        rows = [{"decision_id": "a", "rank": 1, "counter_status": "candidate-contrary"}]
        self.assertEqual(M.metric_e_evidence({"decisions": rows}, rows)["verdict"],
                         "NOT_APPLICABLE")
        g = M.metric_g_minority_reach({"decisions": rows, "clusters": []}, rows)
        self.assertEqual(g["verdict"], "NOT_APPLICABLE")


class TestVerdictRule(unittest.TestCase):
    def test_retrieval_independence_verdict_flows_from_b(self):
        rows = [_dec("c1", 1, "candidate-contrary", channels=["adversarial.x.v1"]),
                _dec("n", 2)]
        doc = _bundle(rows, channels={"search": 1})
        ms = M.all_metrics(doc, rows, n_bundle_total=2)
        self.assertEqual(M.verdicts(ms)["retrieval_independence"], "PASS")

    def test_classification_only_when_all_bundles_fail(self):
        per_input = [
            {"kind": "bundle", "verdicts": {"retrieval_independence": "FAIL"}},
            {"kind": "bundle", "verdicts": {"retrieval_independence": "FAIL"}},
            {"kind": "leg", "verdicts": {"retrieval_independence": "NOT_APPLICABLE"}},
        ]
        verdict, why = H.named_verdict(per_input)
        self.assertEqual(verdict, "CLASSIFICATION_ONLY")
        self.assertIn("2 bundles", why)

    def test_mixed_and_all_pass(self):
        mixed = [{"kind": "bundle", "verdicts": {"retrieval_independence": "PASS"}},
                 {"kind": "bundle", "verdicts": {"retrieval_independence": "FAIL"}}]
        self.assertEqual(H.named_verdict(mixed)[0], "MIXED")
        allp = [{"kind": "bundle", "verdicts": {"retrieval_independence": "PASS"}}]
        self.assertEqual(H.named_verdict(allp)[0], "RETRIEVAL_INDEPENDENT_AND_DISCOVERABLE")


class TestCorruptions(unittest.TestCase):
    def test_every_corruption_is_deterministic(self):
        doc = _bundle([_dec("c1", 1, "candidate-contrary"),
                       _dec("n1", 2), _dec("n2", 3)])
        for cid, _fn, _metric in corrupt.CORRUPTIONS:
            a = corrupt.apply(doc, cid)
            b = corrupt.apply(doc, cid)
            self.assertEqual(H.canonical(a["doc"]), H.canonical(b["doc"]),
                             f"{cid} is not deterministic")

    def test_n2_deep_permute_actually_moves_counter_rows_deep(self):
        rows = [_dec("c1", 1, "candidate-contrary")] + [_dec("n%d" % i, i + 2) for i in range(40)]
        out = corrupt.apply(_bundle(rows), "N2_deep_permute_ranks")["doc"]
        got = {d["decision_id"]: d["rank"] for d in out["decisions"]}
        self.assertEqual(got["c1"], 41)
        ranks = sorted(d["rank"] for d in out["decisions"])
        self.assertEqual(ranks, list(range(1, 42)))  # multiset preserved exactly

    def test_every_corruption_preserves_the_rank_multiset(self):
        """A rank corruption must not create or destroy a rank."""
        rows = ([_dec("c1", 1, "candidate-contrary"), _dec("c2", 7, "candidate-limiting")]
                + [_dec("n%d" % i, i + 2) for i in range(40)])
        original = sorted(d["rank"] for d in rows)
        out = corrupt.apply(_bundle(rows), "N2_deep_permute_ranks")["doc"]
        self.assertEqual(sorted(d["rank"] for d in out["decisions"]), original)
        moved = {d["decision_id"]: d["rank"] for d in out["decisions"]
                 if d["decision_id"] in ("c1", "c2")}
        self.assertEqual(sorted(moved.values()), [40, 41])

    def test_n3_and_n4_touch_only_counter_rows(self):
        rows = [_dec("c1", 1, "candidate-contrary"), _dec("n1", 2)]
        for cid in ("N3_separate_placement", "N4_evidence_backing"):
            out = corrupt.apply(_bundle(rows), cid)["doc"]
            non_counter = [d for d in out["decisions"] if d["decision_id"] == "n1"][0]
            self.assertEqual(non_counter, _dec("n1", 2), f"{cid} leaked onto a non-counter row")


class TestIntegrityAndReproducibility(unittest.TestCase):
    def test_tampered_input_aborts(self):
        spec = {"path": "nope.json", "sha256": "0" * 64, "bytes": 1}
        with self.assertRaises(H.IntegrityAbort):
            H.verify_input(spec, str(MOUNT))

    def test_measure_is_byte_identical_across_calls(self):
        doc = _bundle([_dec("c1", 1, "candidate-contrary", channels=["adversarial.x.v1"]),
                       _dec("n1", 2)])
        one = H.measure(copy.deepcopy(doc), with_shortlist=False)
        two = H.measure(copy.deepcopy(doc), with_shortlist=False)
        self.assertEqual(H.canonical(one), H.canonical(two))


@unittest.skipUnless((MOUNT / "results" / "product").is_dir(), "accepted product mount absent")
class TestAcceptedArtifacts(unittest.TestCase):
    """Locks the published numbers against the frozen accepted inputs."""

    @classmethod
    def setUpClass(cls):
        cls.rules = json.loads(RULES_PATH.read_text(encoding="utf-8"))
        cls.results = []
        for spec in cls.rules["inputs"]["bundles"]:
            cls.results.append(H.measure_input(spec, str(MOUNT), "bundle", non_vacuity=True))
        for spec in cls.rules["inputs"]["frozen_legs"]:
            cls.results.append(H.measure_input(spec, str(MOUNT), "leg"))

    def by_id(self, ident):
        for r in self.results:
            if r["id"] == ident:
                return r
        self.fail(f"no result {ident}")

    def test_all_frozen_inputs_verify_by_sha256(self):
        for spec in self.rules["inputs"]["bundles"] + self.rules["inputs"]["frozen_legs"]:
            self.assertEqual(H.verify_input(spec, str(MOUNT)), os.path.join(str(MOUNT), spec["path"]))

    def test_thresholds_match_the_frozen_rules_file(self):
        self.assertEqual(M.THRESHOLDS, {
            "MIN_COUNTER_YIELD": 0.02,
            "MIN_BEYOND_TOP20_SHARE": 0.30,
            "MIN_DISCOVERABLE_PLACEMENT_SHARE": 0.50,
            "MIN_VERIFIED_EVIDENCE_SHARE": 0.50,
            "MAX_PLACEHOLDER_EVIDENCE_SHARE": 0.50,
            "MIN_MINORITY_REACH_SHARE": 0.20,
        })

    def test_published_verdict_is_classification_only(self):
        verdict, _why = H.named_verdict(self.results)
        self.assertEqual(verdict, "CLASSIFICATION_ONLY")

    def test_no_counter_row_uses_an_adversarial_channel(self):
        for ident in ("B1_gate_rehearsal_live_227",
                      "B2_clickable_slice_live_enriched_287",
                      "B3_kundigung_fixture_100"):
            b = self.by_id(ident)["metrics"]["b_marginal_retrieval_contribution"]
            self.assertEqual(b["b1_adversarial_channel_rows"], 0, ident)
            self.assertEqual(b["b2_new_channels"], [], ident)
            self.assertEqual(b["verdict"], "FAIL", ident)

    def test_shortlist_replay_reproduces_the_product_recorded_24(self):
        for ident in ("B1_gate_rehearsal_live_227", "B2_clickable_slice_live_enriched_287"):
            r = self.by_id(ident)
            prov = r["shortlist"]["provenance"]
            self.assertEqual(prov["status"], "OK", ident)
            self.assertEqual(prov["max_prompt_sources"], 24, ident)
            self.assertEqual(len(r["shortlist"]["ids"]), 24, ident)
            self.assertEqual(r["product_recorded_counters"]["adversarial"]["prompt_decisions"], 24,
                             ident)
            b = r["metrics"]["b_marginal_retrieval_contribution"]
            self.assertEqual(b["shortlist_ids"], r["shortlist"]["ids"], ident)

    def test_adversarial_pass_never_saw_the_majority_of_the_pool(self):
        for ident in ("B1_gate_rehearsal_live_227", "B2_clickable_slice_live_enriched_287"):
            b = self.by_id(ident)["metrics"]["b_marginal_retrieval_contribution"]
            self.assertGreater(b["b6_pool_never_seen_rate"], 0.5, ident)

    def test_counter_rows_sit_inside_the_conventional_top20(self):
        self.assertEqual(self.by_id("B1_gate_rehearsal_live_227")["metrics"]
                         ["c_rank_placement"]["counter_ranks"], [1, 3, 13])
        self.assertEqual(self.by_id("B2_clickable_slice_live_enriched_287")["metrics"]
                         ["c_rank_placement"]["counter_ranks"], [5, 6, 14, 27])
        self.assertEqual(self.by_id("B3_kundigung_fixture_100")["metrics"]
                         ["c_rank_placement"]["counter_ranks"], [3])

    def test_non_vacuity_passes_on_every_real_bundle(self):
        for ident in ("B1_gate_rehearsal_live_227",
                      "B2_clickable_slice_live_enriched_287",
                      "B3_kundigung_fixture_100"):
            self.assertEqual(self.by_id(ident)["non_vacuity"]["gate"], "PASS", ident)

    def test_all_four_frozen_legs_measured_with_bundle_denominator(self):
        for ident in ("L1_rent-default", "L2_petty-theft-dismissal",
                      "L3_corporate-criminal-liability", "L4_business-judgment-rule"):
            r = self.by_id(ident)
            self.assertEqual(r["row_source"], "cited_decisions", ident)
            a = r["metrics"]["a_counter_yield"]
            self.assertTrue(a["denominator_is_bundle_total"], ident)
            self.assertEqual(a["n_bundle_total"],
                             r["product_recorded_counters"]["leg_context"]["decision_count"], ident)
            self.assertEqual(a["value"],
                             round(a["n_counter_strict"] / a["n_bundle_total"], 6), ident)

    def test_leg_evidence_is_not_applicable_not_zero(self):
        for ident in ("L1_rent-default", "L2_petty-theft-dismissal",
                      "L3_corporate-criminal-liability", "L4_business-judgment-rule"):
            self.assertEqual(self.by_id(ident)["metrics"]["e_evidence_quality"]["verdict"],
                             "NOT_APPLICABLE", ident)


class TestCliAndScope(unittest.TestCase):
    def test_cli_matrix_is_reproducible_and_stays_in_scope(self):
        with tempfile.TemporaryDirectory() as td:
            outs = []
            for _ in range(2):
                r = subprocess.run(
                    [sys.executable, "-m", "adversarial_discoverability.harness",
                     "--matrix", "--no-non-vacuity", "--out", td],
                    cwd=str(TEAM_DIR), capture_output=True, text=True, timeout=900)
                self.assertEqual(r.returncode, 0, r.stderr[-2000:])
                summary = json.loads(r.stdout)
                self.assertEqual(summary["named_verdict"], "CLASSIFICATION_ONLY")
                self.assertEqual(summary["non_vacuity_gate"], "NOT_RUN")  # --no-non-vacuity
                self.assertEqual(summary["report_sha256"],
                                 H.sha256_file(summary["report"]))
                outs.append(Path(summary["report"]))
            self.assertEqual(outs[0].read_bytes(), outs[1].read_bytes(),
                             "two CLI runs must be byte-identical")

    def test_report_body_has_no_timestamp(self):
        report = RESULTS_DIR / "CYCLE_38792663259_REPORT.json"
        if not report.is_file():
            self.skipTest("report not generated yet")
        body = report.read_text(encoding="utf-8")
        self.assertNotIn('"generated_at"', body, "report body must not embed generated_at")
        # No ISO-8601 date or datetime may appear anywhere in the report body.
        self.assertIsNone(re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", body),
                          "report body must not embed a wall-clock timestamp")
        self.assertIsNone(re.search(r'"(generated_at|run_at|timestamp|created_at)"', body),
                          "report body must not carry a time key")

    def test_default_output_path_is_inside_the_team_namespace(self):
        default_out = os.path.join(REPO_ROOT, "results", "frontier",
                                   "frontier-adversarial-discoverability")
        self.assertTrue(default_out.startswith(str(REPO_ROOT)))
        self.assertIn("frontier-adversarial-discoverability", default_out)
        self.assertNotIn(os.path.join(str(REPO_ROOT), "product"), default_out)
        self.assertNotIn("results/audit", default_out)


# ---------------------------------------------------------------------------
# D5/D6 — the claim-bearing report must survive a later run (IO revision 2)
# ---------------------------------------------------------------------------

FROZEN_REPORT = RESULTS_DIR / "CYCLE_38792663259_REPORT.json"
#: sha256 of the published run-38792663259 report, also recorded in RULES-derived
#: state and in CYCLE_38792663259_REPRODUCIBILITY.json.  If this changes, a
#: published claim-bearing artifact was rewritten.
FROZEN_REPORT_SHA256 = "b15ea198c2df9a1bedeaff6a33d12d96153a84e331f8ce91e601c124292006bd"


class TestHistoricalArtifactProtection(unittest.TestCase):
    def test_published_frozen_report_still_hashes_to_its_recorded_sha256(self):
        if not FROZEN_REPORT.is_file():
            self.skipTest("frozen report not present")
        self.assertEqual(H.sha256_file(str(FROZEN_REPORT)), FROZEN_REPORT_SHA256)

    def test_report_path_is_derived_from_run_id_not_hardcoded(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertTrue(H.report_path(td, "111").endswith("CYCLE_111_REPORT.json"))
            self.assertTrue(H.envelope_path(td, "222").endswith("CYCLE_222_ENVELOPE.json"))
            self.assertNotEqual(H.report_path(td, "111"), H.report_path(td, "222"))

    def test_identical_bytes_rewrite_is_a_noop_not_a_modification(self):
        body = {"x": 1}
        with tempfile.TemporaryDirectory() as td:
            first = H.write_report(body, td, run_id="1")
            second = H.write_report(body, td, run_id="1")
            self.assertTrue(first["written"])
            self.assertFalse(second["written"])
            self.assertTrue(second["identical_to_existing"])
            self.assertEqual(first["report_sha256"], second["report_sha256"])

    def test_overwriting_a_claim_bearing_report_with_different_bytes_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            H.write_report({"x": 1}, td, run_id="1")
            with self.assertRaises(H.ReportOverwriteRefused):
                H.write_report({"x": 2}, td, run_id="1")
            # the historical bytes survived the refused write
            self.assertEqual(H.canonical({"x": 1}), Path(H.report_path(td, "1")).read_bytes())
            # explicit override is possible and is recorded
            forced = H.write_report({"x": 2}, td, run_id="1", overwrite=True)
            self.assertTrue(forced["overwrote_existing"])

    def test_cli_refuses_to_overwrite_and_exits_4(self):
        with tempfile.TemporaryDirectory() as td:
            first = subprocess.run(
                [sys.executable, "-m", "adversarial_discoverability.harness",
                 "--matrix", "--no-non-vacuity", "--out", td, "--run-id", "42"],
                cwd=str(TEAM_DIR), capture_output=True, text=True, timeout=900)
            self.assertEqual(first.returncode, 0, first.stderr[-2000:])
            # Re-publishing the same run id with identical bytes stays a success.
            again = subprocess.run(
                [sys.executable, "-m", "adversarial_discoverability.harness",
                 "--matrix", "--no-non-vacuity", "--out", td, "--run-id", "42"],
                cwd=str(TEAM_DIR), capture_output=True, text=True, timeout=900)
            self.assertEqual(again.returncode, 0, again.stderr[-2000:])
            # Destroy the report, then force a different body onto the same path.
            Path(H.report_path(td, "42")).write_bytes(b'{"tampered": true}\n')
            clash = subprocess.run(
                [sys.executable, "-m", "adversarial_discoverability.harness",
                 "--matrix", "--no-non-vacuity", "--out", td, "--run-id", "42"],
                cwd=str(TEAM_DIR), capture_output=True, text=True, timeout=900)
            self.assertEqual(clash.returncode, 4, clash.stdout[-2000:])
            self.assertIn("already holds different bytes", clash.stderr)
            self.assertEqual(Path(H.report_path(td, "42")).read_bytes(),
                             b'{"tampered": true}\n')

    def test_envelope_records_observed_input_hashes(self):
        rules = json.loads(RULES_PATH.read_text(encoding="utf-8"))
        spec = rules["inputs"]["bundles"][0]
        path, obs = H.verify_input_observed(spec, str(MOUNT))
        self.assertTrue(obs["verified"])
        self.assertEqual(obs["sha256_observed"], obs["sha256_frozen"])
        self.assertEqual(obs["bytes_observed"], obs["bytes_frozen"])
        self.assertEqual(obs["path"], spec["path"])
        self.assertTrue(os.path.isfile(path))

    def test_envelope_has_a_clock_but_the_report_body_never_does(self):
        with tempfile.TemporaryDirectory() as td:
            w = H.write_report({"body": True}, td, run_id="7")
            body = H.run_matrix(str(MOUNT), non_vacuity=False)
            env = H.build_envelope(body, [], "7", td, ["harness"], w)
            H.write_envelope(env, td, run_id="7")
            env_path = Path(H.envelope_path(td, "7"))
            self.assertTrue(env_path.is_file())
            self.assertRegex(env["generated_at_utc"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
            self.assertNotIn("generated_at_utc", H.canonical(body).decode("utf-8"))

    def test_envelope_says_whether_it_reproduces_the_frozen_report(self):
        with tempfile.TemporaryDirectory() as td:
            # non_vacuity=True: the frozen report was produced with the full gate.
            body = H.run_matrix(str(MOUNT), non_vacuity=True)
            w = H.write_report(body, td, run_id="7")
            # copy the frozen report in, so the comparison target exists
            if FROZEN_REPORT.is_file():
                Path(H.report_path(td, H.FROZEN_RUN_ID)).write_bytes(FROZEN_REPORT.read_bytes())
            env = H.build_envelope(body, [], "7", td, ["harness"], w)
            if FROZEN_REPORT.is_file():
                self.assertTrue(env["reproduces_frozen_report"]["byte_identical_to_frozen_report"])
                self.assertEqual(env["reproduces_frozen_report"]["frozen_report_sha256"],
                                 FROZEN_REPORT_SHA256)
            # A body computed WITHOUT the non-vacuity gate must not claim to
            # reproduce the frozen (gate-carrying) report.
            body_nv = H.run_matrix(str(MOUNT), non_vacuity=False)
            w_nv = H.write_report(body_nv, td, run_id="8")
            env_nv = H.build_envelope(body_nv, [], "8", td, ["harness"], w_nv)
            self.assertFalse(env_nv["reproduces_frozen_report"]["byte_identical_to_frozen_report"])


@unittest.skipUnless((MOUNT / "results" / "product").is_dir(), "accepted product mount absent")
class TestNarrativeNumbersAreMachineChecked(unittest.TestCase):
    """The prose report states these numbers; they are recomputed from the
    published report JSON so a wording drift cannot survive a rerun."""

    @classmethod
    def setUpClass(cls):
        if not FROZEN_REPORT.is_file():
            raise unittest.SkipTest("frozen report not present")
        cls.body = json.loads(FROZEN_REPORT.read_text(encoding="utf-8"))

    def bundles(self):
        return [i for i in self.body["inputs"] if i["kind"] == "bundle"]

    def test_counter_row_totals_in_the_prose(self):
        n = sum(i["metrics"]["a_counter_yield"]["n_counter_strict"] for i in self.bundles())
        self.assertEqual(n, 8)  # "0 of 8", "7 of 8", "8 counter rows"

    def test_counter_rows_outside_the_consensus_cluster_is_three_not_two(self):
        """CYCLE_38792663259.md said "only 2 of 8 sit outside the consensus
        mega-cluster"; the report's own metric (d) gives 1/3 + 1/4 + 1/1 = 3."""
        distinct = 0
        for i in self.bundles():
            m = i["metrics"]["d_placement_visibility"]
            distinct += round(m["distinct_cluster_share"] * m["n_counter"])
        self.assertEqual(distinct, 3)

    def test_no_counter_row_is_an_outlier(self):
        for i in self.bundles():
            m = i["metrics"]["d_placement_visibility"]
            self.assertEqual(m["is_outlier_share"], 0.0, i["id"])

    def test_seven_of_eight_counter_rows_sit_inside_the_top20(self):
        n = tot = 0
        for i in self.bundles():
            c = i["metrics"]["c_rank_placement"]
            tot += c["n_counter"]
            n += round(c["top20_share"] * c["n_counter"])
        self.assertEqual((n, tot), (7, 8))

    def test_every_counter_row_channel_is_search_or_language_filter(self):
        for i in self.bundles():
            h = i["metrics"]["b_marginal_retrieval_contribution"]["b3_counter_channel_histogram"]
            self.assertTrue(set(h) <= {"search", "search.language_filter"}, i["id"])


@unittest.skipUnless((MOUNT / "results" / "product").is_dir(), "accepted product mount absent")
class TestIndependentCrossCheckAgrees(unittest.TestCase):
    """A second, independent implementation must reproduce the same numbers.

    ``frontier/frontier-adversarial-discoverability/independent_crosscheck.py`` imports
    nothing from the harness and re-expresses the populations, metrics and thresholds
    from RULES.json.  If the two implementations ever diverge, this test fails rather
    than letting one of them quietly back the published claim.
    """

    @classmethod
    def setUpClass(cls):
        script = TEAM_DIR / "independent_crosscheck.py"
        if not script.is_file():
            raise unittest.SkipTest("cross-check tool absent")
        r = subprocess.run([sys.executable, str(script), "--json"],
                           capture_output=True, text=True, timeout=900)
        if r.returncode not in (0, 1):
            raise unittest.SkipTest(f"cross-check could not run: {r.stderr[-500:]}")
        cls.x = json.loads(r.stdout)

    def test_crosscheck_verifies_every_frozen_input(self):
        self.assertTrue(self.x["all_inputs_verified"])

    def test_crosscheck_confirms_every_prose_claim(self):
        checks = self.x["prose_claims"]["checks"]
        for name, ok in checks.items():
            self.assertTrue(ok, f"prose claim failed cross-check: {name}")

    def test_crosscheck_numbers_match_the_harness_report(self):
        if not FROZEN_REPORT.is_file():
            self.skipTest("frozen report not present")
        body = json.loads(FROZEN_REPORT.read_text(encoding="utf-8"))
        by_id = {i["id"]: i for i in body["inputs"]}
        for x in self.x["bundles"]:
            m = by_id[x["id"]]["metrics"]
            self.assertEqual(x["counter_rows"],
                             m["a_counter_yield"]["n_counter_strict"], x["id"])
            self.assertEqual(x["counter_ranks"], m["c_rank_placement"]["counter_ranks"], x["id"])
            self.assertEqual(x["counter_rows_with_a_channel_absent_from_initial_retrieval"],
                             m["b_marginal_retrieval_contribution"]["b1_adversarial_channel_rows"],
                             x["id"])
            self.assertEqual(x["counter_rows_flagged_outlier"],
                             round(m["d_placement_visibility"]["is_outlier_share"]
                                   * m["d_placement_visibility"]["n_counter"]), x["id"])
            self.assertEqual(x["counter_rows_verified_with_substantive_reason"],
                             m["e_evidence_quality"]["n_verified_with_reason"], x["id"])
            self.assertEqual(x["counter_rows_with_placeholder_evidence"],
                             m["e_evidence_quality"]["n_placeholder_evidence"], x["id"])
            self.assertEqual(x["counter_rows_linked_into_the_answer"],
                             m["f_answer_linkage"]["n_linked"], x["id"])
            self.assertEqual(x["consensus_cluster_id"],
                             m["d_placement_visibility"]["consensus_cluster_id"], x["id"])
        for l in self.x["legs"]:
            a = by_id[l["id"]]["metrics"]["a_counter_yield"]
            self.assertEqual(l["counter_rows"], a["n_counter_strict"], l["id"])
            self.assertEqual(l["decision_count"], a["n_bundle_total"], l["id"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
