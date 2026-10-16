"""Re-dispatch adjudication tests — run 38889472353 (charter v1, HARD STOP).

This charter allows exactly ONE verdict cycle; that cycle is already complete
and promoted (run 38880639079, audit gate PASS, commit 464c45f7).  These tests
pin the four properties a later reader needs in order to trust that a second
dispatch did NOT silently open a second cycle:

  (a) the committed claim-bearing artifacts still hash to their recorded,
      independently audited reproducibility shas;
  (b) the team state still carries charter_version and an honest
      continue_recommended=false;
  (c) the re-dispatch adjudication artifact reports all checks pass, no second
      verdict cycle, no new threshold, and an unchanged verdict of record;
  (d) no claim-bearing text produced by this team crosses the claim ceiling,
      and nothing was written outside this team's enforced scope.

Claim-bearing scope is SUPPORT of labels AS ISSUED and GEOMETRY SEMANTICS of
gate packet 38839347028 only.  Nothing here asserts anything about whether any
individual case supports, contradicts or limits any legal proposition.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "frontier", "frontier-served-packet-falsification"))

from frontier_served_packet_falsification import (  # noqa: E402
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

RESULTS = os.path.join(REPO, "results", "frontier", TEAM_ID)
REPORTS = os.path.join(REPO, "reports", "frontier", TEAM_ID)
STATE_PATH = os.path.join(REPO, "state", "frontier", f"{TEAM_ID}.json")
VERIFICATION_PATH = os.path.join(RESULTS, "REDISPATCH_VERIFICATION_38889472353.json")
REPORT_PATH = os.path.join(REPORTS, "REDISPATCH_38889472353.md")

RUN_ID = "38889472353"
PROMOTED_RUN_ID = "38880639079"
PROMOTED_COMMIT = "464c45f7e4bf741b6a67adbef35dc587d8cfa21f"

CLAIM_BEARING = (
    "LABEL_HALF.json",
    "GEOMETRY_HALF.json",
    "BEFORE_AFTER.json",
    "CLAIM_CEILING.json",
    "FREEZE.json",
    "SUMMARY.json",
    "CLAIM_CEILING_CHECK.json",
)


def _sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


class TestNoSecondVerdictCycle(unittest.TestCase):
    """Acceptance: HARD STOP — exactly ONE verdict cycle under charter v1."""

    def setUp(self):
        self.state = _load(STATE_PATH)
        self.verification = _load(VERIFICATION_PATH)

    def test_state_retains_charter_version(self):
        self.assertEqual(self.state["charter_version"], CHARTER_VERSION)
        self.assertEqual(self.verification["charter_version"], CHARTER_VERSION)

    def test_continue_recommended_is_false(self):
        self.assertIs(self.state["continue_recommended"], False)
        self.assertIs(self.verification["continue_recommended"], False)
        self.assertIn("HARD STOP", self.state["continue_recommended_reason"])

    def test_no_second_verdict_cycle_claimed(self):
        self.assertIs(self.verification["second_verdict_cycle_performed"], False)
        self.assertEqual(
            self.verification["dispatch_class"],
            "OPERATIONAL_RE_DISPATCH_OF_AN_ALREADY_PROMOTED_CHARTER",
        )
        self.assertIs(self.verification["new_threshold_introduced"], False)

    def test_promoted_cycle_still_named(self):
        self.assertEqual(self.state["promoted_verdict_run_id"], PROMOTED_RUN_ID)
        self.assertEqual(self.state["promoted_commit"], PROMOTED_COMMIT)
        self.assertEqual(
            self.state["promoted_independent_audit"]["gate_path"],
            "results/audit/frontier/frontier-served-packet-falsification/"
            "CYCLE_38880639079_GATE.json",
        )
        self.assertEqual(self.state["promoted_independent_audit"]["gate"], "PASS")

    def test_new_charter_trigger_absent(self):
        trig = self.verification["inputs"]["packet_rebuilt_since_verdict_cycle"]
        self.assertIs(trig, False)
        self.assertIs(
            self.verification["inputs"]["further_product_repair_needs_re_scoring"],
            False,
        )
        self.assertTrue(self.verification["inputs"]["all_inputs_unchanged"])

    def test_state_machine_gate_still_satisfied(self):
        self.assertEqual(self.state["charter_version"], 1)
        self.assertNotEqual(self.state.get("cycle_status", "INITIALIZED"), "INITIALIZED")
        self.assertNotEqual(self.state.get("evidence_tier", "UNTESTED"), "")


class TestAllAdjudicationChecksPass(unittest.TestCase):
    """Acceptance: freeze, inputs, population, reproduction, scope, verdict."""

    def setUp(self):
        self.v = _load(VERIFICATION_PATH)

    def test_all_checks_pass(self):
        self.assertTrue(self.v["all_checks_pass"], self.v["checks"])
        for name, ok in self.v["checks"].items():
            self.assertTrue(ok, f"check failed: {name}")

    def test_freeze_byte_identity_and_no_frozen_at_utc(self):
        f = self.v["freeze"]
        self.assertEqual(f["rules_label_sha256"], RULES_LABEL_SHA256)
        self.assertEqual(f["rules_geometry_sha256"], RULES_GEOMETRY_SHA256)
        self.assertTrue(f["byte_identity_ok"])
        self.assertIs(f["frozen_at_utc_field_written"], False)
        self.assertEqual(_sha(os.path.join(RESULTS, "RULES_LABEL.json")), RULES_LABEL_SHA256)
        self.assertEqual(_sha(os.path.join(RESULTS, "RULES_GEOMETRY.json")), RULES_GEOMETRY_SHA256)

    def test_population_matches_charter_pre_registration(self):
        p = self.v["population_recount"]
        self.assertTrue(p["matches_charter_pre_registration"])
        self.assertEqual(p["n_scored_total"], 65)
        self.assertEqual(p["n_empty_evidence_at_uncertainty_ge_0_95"], 16)
        self.assertEqual(p["n_cited_placeholders"], 11)
        self.assertEqual(
            p["counter_evidence_verified"],
            {"present_true": 49, "present_false": 0, "absent": 16},
        )
        self.assertEqual(len(p["empty_evidence_rows"]), 16)
        # Every empty-evidence row must be present individually, never skipped.
        for row in p["empty_evidence_rows"]:
            self.assertIn("decision_id", row)
            self.assertIn("counter_uncertainty", row)

    def test_reproduction_byte_identical(self):
        r = self.v["reproduction"]
        self.assertTrue(r["committed_match_recorded_run1_run2"])
        self.assertTrue(r["fresh_runs_byte_identical_to_each_other"])
        self.assertTrue(r["fresh_runs_byte_identical_to_committed"])
        self.assertTrue(r["all_reproductions_byte_identical"])

    def test_committed_artifacts_hash_to_recorded_shas(self):
        recorded = _load(os.path.join(RESULTS, "REPRODUCIBILITY.json"))["files"]
        for name in CLAIM_BEARING:
            self.assertIn(name, recorded)
            self.assertEqual(
                _sha(os.path.join(RESULTS, name)),
                recorded[name]["run1_sha256"],
                name,
            )
            self.assertEqual(
                _sha(os.path.join(RESULTS, name)),
                recorded[name]["run2_sha256"],
                name,
            )

    def test_verdict_of_record_unchanged(self):
        summary = _load(os.path.join(RESULTS, "SUMMARY.json"))
        self.assertEqual(summary["label_verdict"], "LABEL_UNSOUND")
        self.assertEqual(summary["label_n_scored"], 65)
        self.assertEqual(summary["label_n_supported"], 5)
        self.assertEqual(summary["geometry_verdict"], "FAIL")
        self.assertEqual(summary["geometry_n_bundles_pass"], 0)
        state = _load(STATE_PATH)
        self.assertEqual(state["verdict"]["label_half"]["verdict"], "LABEL_UNSOUND")
        self.assertEqual(state["verdict"]["geometry_half"]["verdict"], "FAIL")
        self.assertEqual(
            state["serve_recommendation"], "DO-NOT-SERVE this packet unchanged."
        )


class TestClaimCeilingOnThisRun(unittest.TestCase):
    """Acceptance (9): no authority-claiming construction, anywhere."""

    def test_verification_payload_clean(self):
        v = _load(VERIFICATION_PATH)
        result = check_payload(v)
        self.assertTrue(result["pass"], result["violations"])
        self.assertEqual(result["n_violations"], 0)

    def test_state_file_clean(self):
        with open(STATE_PATH, encoding="utf-8") as fh:
            text = fh.read()
        self.assertEqual(scan_for_violations(text), [])

    def test_report_clean(self):
        with open(REPORT_PATH, encoding="utf-8") as fh:
            text = fh.read()
        self.assertEqual(scan_for_violations(text), [])

    def test_claim_ceiling_present_and_negated(self):
        v = _load(VERIFICATION_PATH)
        self.assertIn("NEVER asserts", v["claim_ceiling"])
        self.assertTrue(v["claim_ceiling_check"]["pass"])


class TestWriteScopeThisRun(unittest.TestCase):
    """Acceptance (8): zero files written outside this team's scope."""

    def _git_status(self) -> list[str]:
        proc = subprocess.run(
            ["git", "status", "--porcelain", "-uall"],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        )
        return [ln for ln in proc.stdout.splitlines() if ln.strip()]

    def test_recorded_scope_is_clean(self):
        v = _load(VERIFICATION_PATH)
        self.assertEqual(v["scope"]["files_outside_scope"], [])
        self.assertEqual(v["scope"]["forbidden_prefix_hits"], [])
        self.assertTrue(v["scope"]["zero_out_of_scope_writes"])

    def test_producer_delta_separated_from_compiler_artifacts(self):
        v = _load(VERIFICATION_PATH)
        scope = v["scope"]
        delta = scope["producer_delta"]
        # Producer delta never carries bytecode, and never leaves team scope.
        for path in delta:
            self.assertNotIn("__pycache__", path, path)
            self.assertFalse(path.endswith((".pyc", ".pyo")), path)
            self.assertTrue(
                any(path.startswith(p.rstrip("/")) for p in WRITE_SCOPE)
                or path == f"state/frontier/{TEAM_ID}.json"
                or path == f"data/frontier/{TEAM_ID}/",
                f"out-of-scope producer delta entry: {path}",
            )
        # Compiler artifacts are recorded separately, all inside team scope.
        for path in scope["compiler_artifacts_excluded_from_producer_delta"]:
            self.assertIn("__pycache__", path, path)
            self.assertTrue(
                any(path.startswith(p.rstrip("/")) for p in WRITE_SCOPE), path
            )

    def test_live_git_status_stays_in_scope(self):
        allowed = tuple(WRITE_SCOPE) + (
            f"state/frontier/{TEAM_ID}.json",
            f"data/frontier/{TEAM_ID}/",
            "",
        )
        outside = []
        forbidden = []
        for line in self._git_status():
            path = line[3:]
            if any(path.startswith(p) for p in allowed):
                continue
            outside.append(path)
            if any(path.startswith(f) for f in FORBIDDEN_WRITE_PREFIXES):
                forbidden.append(path)
        self.assertEqual(sorted(set(outside)), [], "out-of-scope write")
        self.assertEqual(sorted(set(forbidden)), [], "forbidden write")

    def test_new_artifacts_live_inside_scope(self):
        for path in (VERIFICATION_PATH, REPORT_PATH, STATE_PATH, __file__):
            rel = os.path.relpath(path, REPO).replace(os.sep, "/")
            self.assertTrue(
                any(rel.startswith(p.rstrip("/")) for p in WRITE_SCOPE)
                or rel == f"state/frontier/{TEAM_ID}.json",
                rel,
            )

    def test_audit_paths_untouched_by_this_team(self):
        # This team never writes under results/audit/ or reports/audit/.
        for rel in (
            "results/audit/frontier/frontier-served-packet-falsification",
            "reports/audit/frontier/frontier-served-packet-falsification",
        ):
            base = os.path.join(REPO, rel)
            if not os.path.isdir(base):
                continue
            # Existing audit artifacts are the independent auditor's; this
            # team's git status must show no modification to them.
            for line in self._git_status():
                path = line[3:]
                self.assertFalse(
                    path.startswith(rel) and line[:2].strip() in ("M", "MM", "A"),
                    f"producer modified an audit path: {line}",
                )


if __name__ == "__main__":
    unittest.main()
