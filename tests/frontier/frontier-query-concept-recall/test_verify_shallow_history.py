#!/usr/bin/env python3
"""Regression tests for defect K (cycle 39184014244): R2 must never fabricate.

Defect K
--------
``frontier/frontier-query-concept-recall/verify.py`` check
``R2_freeze_ordering_from_real_commit_times`` decided PASS/FAIL from a
commit-time comparison.  The Frontier workflow fetches the team branch with
``--depth=1`` (see ``.github/workflows/frontier-team.yml``), so
``git log -- <path>`` collapses to the single checked-out commit:
``last_rules`` and ``first_canonical`` become the SAME commit, their timestamps
are equal, ``ordering_holds`` is structurally False, and R2 reported a hard
FAIL whose narrative asserted commit shas and times it had never read -- in a
shallow checkout those objects do not resolve at all.

Two independent verifiers of this team therefore disagreed about the same fact:
``closure.py:240-254`` returned ``ENUM_SHALLOW_HISTORY`` (correct) while
``verify.py`` (later, and the file whose docstring claims it "adds the checks
closure.py does not make") emitted a fabricated FAIL.  Cycle 39184014244
ported the ``closure.py`` guard into ``verify.py`` and pinned it here.

These tests are about the VERIFIER's reporting contract, not about the
charter's measurement.  They change no number and make no measurement claim.
They run fully offline.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
VERIFY_PY = REPO / "frontier" / "frontier-query-concept-recall" / "verify.py"
CLOSURE_PY = REPO / "frontier" / "frontier-query-concept-recall" / "closure.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader, path
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


verify = _load(VERIFY_PY, "fqc_verify_under_test")


def _r2_record() -> dict:
    for c in verify.run(Path("/tmp/opencode/verify_scratch/r2_probe"))["checks"]:
        if c["check"] == "R2_freeze_ordering_from_real_commit_times":
            return c
    raise AssertionError("R2 check missing from the verification record")


class ShallowHistoryGuard(unittest.TestCase):
    def test_repo_state_is_measurable_either_way(self):
        # The guard must key on the repository's ACTUAL shallow state, so this
        # test is valid in both a shallow and a full checkout.
        self.assertIn(verify.history_is_shallow(), (True, False))

    def test_r2_is_never_a_fabricated_fail_in_a_shallow_checkout(self):
        shallow = verify.history_is_shallow()
        n_rules = len(verify.commits_touching(
            "results/frontier/frontier-query-concept-recall/RULES.json"))
        rec = _r2_record()
        if shallow and n_rules < 3:
            self.assertEqual(
                rec["status"], "ENUM_SHALLOW_HISTORY",
                "a shallow checkout must not yield a hard FAIL: the commit-time "
                "comparison is vacuous, so a FAIL would be fabricated")
            self.assertTrue(rec["not_measured_note"])
            self.assertIsNone(
                rec["ordering_rule_last_edit_before_first_canonical_measurement"],
                "a vacuous comparison must be reported as None, never as a "
                "measured False")
        else:
            self.assertEqual(rec["status"], "PASS")

    def test_r2_reports_history_state_explicitly(self):
        rec = _r2_record()
        self.assertIn("history_is_shallow", rec)
        self.assertIn("n_rules_commits_visible", rec)
        self.assertIn("ordering_measurable", rec)

    def test_byte_identity_half_is_reported_even_when_unmeasurable(self):
        # The freeze INTEGRITY claim survives a shallow checkout even though the
        # ordering claim cannot be recomputed; it must never be silently dropped.
        rec = _r2_record()
        self.assertIn("rules_blob_unchanged_since_that_commit", rec)
        self.assertIn("head_blob", rec)
        self.assertTrue(rec["head_blob"], "HEAD blob of RULES.json must resolve")

    def test_enum_is_not_counted_as_a_failure_and_not_counted_as_a_pass(self):
        record = verify.run(Path("/tmp/opencode/verify_scratch/r2_probe2"))
        enums = record["enum_checks"]
        statuses = {c["check"]: c["status"] for c in record["checks"]}
        for check in enums:
            self.assertTrue(statuses[check].startswith("ENUM"))
            self.assertNotIn(check, record["failed_checks"])
            self.assertNotIn(check, record["repair_checks"])

    def test_verify_and_closure_agree_on_shallow_history(self):
        # The two verifiers of this team must not disagree about the same fact.
        self.assertIn("is-shallow-repository",
                      CLOSURE_PY.read_text(encoding="utf-8"),
                      "closure.py must keep its shallow-history guard")
        self.assertIn("is-shallow-repository",
                      VERIFY_PY.read_text(encoding="utf-8"),
                      "verify.py must keep the ported guard")


class RepairExitPolicy(unittest.TestCase):
    def test_no_dead_repair_variable_left_in_run(self):
        # Defect K's sibling: an unused `repairs` local and a loose `and`/`or`
        # binding drove the exit code from a SEPARATE computation the reader
        # could not see. The record now names the checks it scores.
        src = VERIFY_PY.read_text(encoding="utf-8")
        body = src.split("def run(out_dir: Path) -> dict:", 1)[1].split("\ndef ", 1)[0]
        self.assertNotIn("repairs = [", body)
        self.assertIn('"repair_checks": repair_checks', body)

    def test_exit_code_tracks_the_named_repair_checks(self):
        record = verify.run(Path("/tmp/opencode/verify_scratch/r2_probe3"))
        scored = {c["check"] for c in record["checks"]
                  if c["check"] in record["repair_checks"]}
        self.assertTrue(scored, "at least one in-scope repair check must be scored")
        self.assertIn("exit_code_policy", record)


class OfflineContract(unittest.TestCase):
    def test_record_declares_zero_network_calls(self):
        record = verify.run(Path("/tmp/opencode/verify_scratch/r2_probe4"))
        self.assertEqual(record["network_calls"], 0)

    def test_this_cycle_makes_no_measurement_claim(self):
        record = verify.run(Path("/tmp/opencode/verify_scratch/r2_probe5"))
        self.assertTrue(record["this_run_adds_no_measurement_claim"])
        self.assertEqual(record["charter_outcome_unchanged"],
                         "OUTCOME_B_BOUNDED_NEGATIVE")

    def test_claim_ceiling_is_carried_verbatim(self):
        ceiling = verify.run(Path("/tmp/opencode/verify_scratch/r2_probe6"))["claim_ceiling"]
        for forbidden in ("helps a jurist", "absent from the corpus",
                          "fit to serve", "fail-closed"):
            self.assertIn(forbidden, ceiling)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        unittest.main(verbosity=2)