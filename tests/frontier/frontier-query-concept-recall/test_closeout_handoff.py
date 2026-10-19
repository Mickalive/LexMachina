#!/usr/bin/env python3
"""Tests for closeout_handoff.py: the ONE control-plane write we cannot make.

The module's whole value is that the command it hands the director is correct.
Two ways it was wrong, both caught in cycle 39184014244 by EXECUTING the emitted
command against a portfolio COPY (never the real file):

* ``(.teams[] | select(...)) | (.status = "PAUSE")`` replaces the entire
  document with the single matched team object. jq streams the selection, so
  ``.version`` and ``.teams`` are destroyed and the director's own validation
  gate fails.
* ``\\"`` inside a shell single-quoted jq program reaches jq literally, so the
  closure note must not carry double quotes.

These tests execute the emitted command for real, against a copy, and assert the
result passes the director's own two validation gates, ends the dispatch
selector and leaves every other team byte-identical.

They are read-only with respect to the repository. Fully offline.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
MODULE = REPO / "frontier/frontier-query-concept-recall/closeout_handoff.py"
SCRATCH = Path("/tmp/opencode/verify_scratch/handoff_tests")


def _load():
    spec = importlib.util.spec_from_file_location("fqc_closeout_under_test", MODULE)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


handoff = _load()


def run_jq(program: str, path: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["jq", program, str(path), *args],
                          capture_output=True, text=True)


class EmittedPatchIsExecutable(unittest.TestCase):
    """The handoff is worthless if its command does not run."""

    @classmethod
    def setUpClass(cls):
        SCRATCH.mkdir(parents=True, exist_ok=True)
        # The director's flow: emit the handoff (and its history file) into the
        # results dir first, then run the command that references them, from the
        # repository root.
        handoff.main(["--out", str(handoff.RESULTS_DIR)])
        cls.record = handoff.build()
        cls.cmd = cls.record["proposed_control_plane_write"]["jq_command"]
        cls.portfolio = SCRATCH / "portfolio.json"
        cls.raw = SCRATCH / "raw.json"
        shutil.copyfile(handoff.PORTFOLIO, cls.portfolio)
        # The emitted command is `jq ... <portfolio> > /tmp/p.json && mv
        # /tmp/p.json <portfolio>`: redirecting the portfolio argument to a COPY
        # is therefore sufficient to execute it end to end without touching the
        # real file, and the copy ends up holding the patched result.
        proc = subprocess.run(
            ["bash", "-c", cls.cmd.replace("state/frontier_portfolio.json",
                                           str(cls.portfolio))
             .replace("/tmp/p.json", str(cls.raw))],
            capture_output=True, text=True, cwd=str(handoff.REPO))
        cls.proc = proc
        cls.patched = cls.portfolio

    def test_command_exits_zero(self):
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr)

    def test_director_structure_gate_passes(self):
        # Verbatim from factory-director.yml:98
        proc = run_jq('.version and (.teams|type=="array") and '
                      'all(.teams[]; (.team_id and .charter_version and .status))',
                      self.patched)
        self.assertEqual(proc.stdout.strip(), "true", proc.stderr)

    def test_director_run_entry_completeness_gate_passes(self):
        # Verbatim from factory-director.yml:99
        proc = run_jq('all(.teams[] | select(.status=="RUN"); '
                      '(.product_capability and .question and .hypothesis and '
                      '.why_now and .non_duplication and .dependencies and '
                      '.acceptance_test and .stop_promote_rule))', self.patched)
        self.assertEqual(proc.stdout.strip(), "true", proc.stderr)

    def test_root_document_survives(self):
        original = json.loads(handoff.PORTFOLIO.read_text(encoding="utf-8"))
        patched = json.loads(self.patched.read_text(encoding="utf-8"))
        self.assertEqual(len(patched["teams"]), len(original["teams"]),
                         "the root document was replaced by the selection")
        self.assertIsInstance(patched.get("version"), int)

    def test_dispatch_selector_no_longer_matches(self):
        # The exact predicate from frontier-team.yml:58
        proc = run_jq('[.teams[] | select(.team_id=="%s" and .charter_version==%d '
                      'and .status=="RUN")] | length'
                      % (handoff.TEAM_ID, handoff.CHARTER_VERSION), self.patched)
        self.assertEqual(proc.stdout.strip(), "0",
                         "the loop would still re-dispatch after the patch")
        before = run_jq('[.teams[] | select(.team_id=="%s" and '
                        '.charter_version==%d and .status=="RUN")] | length'
                        % (handoff.TEAM_ID, handoff.CHARTER_VERSION),
                        handoff.PORTFOLIO)
        self.assertEqual(before.stdout.strip(), "1",
                         "precondition: the entry is RUN today")

    def test_other_team_entries_are_byte_identical(self):
        original = json.loads(handoff.PORTFOLIO.read_text(encoding="utf-8"))
        patched = json.loads(self.patched.read_text(encoding="utf-8"))
        others_before = [t for t in original["teams"]
                         if t["team_id"] != handoff.TEAM_ID]
        others_after = [t for t in patched["teams"]
                        if t["team_id"] != handoff.TEAM_ID]
        self.assertEqual(others_before, others_after)

    def test_patch_records_the_completed_cycles(self):
        patched = json.loads(self.patched.read_text(encoding="utf-8"))
        entry = next(t for t in patched["teams"]
                     if t["team_id"] == handoff.TEAM_ID)
        state = json.loads(handoff.STATE_FILE.read_text(encoding="utf-8"))
        self.assertEqual(len(entry["run_history"]), len(state["run_history"]))
        self.assertIs(entry["continue_recommended"], False)
        self.assertEqual(entry["status"], handoff.build()[
            "proposed_control_plane_write"]["recommended_status"])

    def test_patch_is_idempotent_in_shape_not_content(self):
        # Applying it twice must not drop teams or duplicate the entry; the
        # director may re-run it if a previous attempt failed.
        again = SCRATCH / "patched2.json"
        raw2 = SCRATCH / "raw2.json"
        shutil.copyfile(self.patched, again)
        subprocess.run(["bash", "-c",
                        self.cmd.replace("state/frontier_portfolio.json", str(again))
                        .replace("/tmp/p.json", str(raw2))],
                       capture_output=True, text=True, check=True,
                       cwd=str(handoff.REPO))
        twice = json.loads(again.read_text(encoding="utf-8"))
        self.assertEqual(len(twice["teams"]),
                         len(json.loads(handoff.PORTFOLIO.read_text(
                             encoding="utf-8"))["teams"]))


class HistoryIsNeverShellQuoted(unittest.TestCase):
    """Defect C7: an apostrophe in a disposition broke the emitted command."""

    def test_history_ships_as_a_file_not_an_inline_literal(self):
        cmd = handoff.build()["proposed_control_plane_write"]["jq_command"]
        self.assertIn("--slurpfile hist", cmd)
        self.assertNotIn("--argjson hist", cmd,
                         "inlining JSON into single quotes is what broke")

    def test_emitted_command_survives_apostrophes_in_the_history(self):
        """The real failure: the team state's disposition text contains one."""
        state = json.loads(handoff.STATE_FILE.read_text(encoding="utf-8"))
        if not any("'" in (r.get("disposition") or "") for r in state["run_history"]):
            self.skipTest("no apostrophe in the current run history")
        S = SCRATCH / "apos"; S.mkdir(parents=True, exist_ok=True)
        portfolio = S / "portfolio.json"
        shutil.copyfile(handoff.PORTFOLIO, portfolio)
        # Emit with the real (apostrophe-bearing) history into the results dir
        # the command references, then execute it from the repo root.
        handoff.main(["--out", str(handoff.RESULTS_DIR)])
        proc = subprocess.run(
            ["bash", "-c", handoff.build()["proposed_control_plane_write"]["jq_command"]
             .replace("state/frontier_portfolio.json", str(portfolio))
             .replace("/tmp/p.json", str(S / "raw.json"))],
            capture_output=True, text=True, cwd=str(handoff.REPO))
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_history_file_matches_the_record(self):
        out = SCRATCH / "hist"
        handoff.main(["--out", str(out)])
        written = json.loads((out / Path(handoff.HISTORY_NAME).name)
                             .read_text(encoding="utf-8"))
        expected = handoff.build()["proposed_control_plane_write"][
            "proposed_run_history_entries"]
        self.assertEqual(written, expected)

    def test_jq_program_is_shell_safe(self):
        program = handoff.build()["proposed_control_plane_write"]["jq_program"]
        self.assertNotIn("'", program,
                         "the program is wrapped in shell single quotes")
        self.assertNotIn("\\\"", program,
                         "escaped quotes reach jq literally and fail to compile")


class HandoffHonesty(unittest.TestCase):
    def test_it_never_writes_the_portfolio(self):
        src = MODULE.read_text(encoding="utf-8")
        for forbidden in ('open(PORTFOLIO, "w")', "write_text(json.dumps(portfolio)",
                          "PORTFOLIO.write_text"):
            self.assertNotIn(forbidden, src,
                             "this team must not perform the control-plane write")

    def test_it_states_the_charter_is_terminal_and_adds_no_claim(self):
        rec = handoff.build()
        self.assertEqual(rec["charter_outcome_unchanged"],
                         "OUTCOME_B_BOUNDED_NEGATIVE")
        self.assertTrue(rec["this_cycle_adds_no_measurement_claim"])
        self.assertEqual(rec["network_calls"], 0)

    def test_it_diagnoses_the_gap_from_state_not_from_assertion(self):
        gap = handoff.reflect_gap()
        self.assertEqual(gap["portfolio_entry_status"], "RUN")
        self.assertEqual(gap["portfolio_entry_run_history_len"], 0)
        self.assertIs(gap["team_state_continue_recommended"], False)
        self.assertGreater(gap["team_state_n_run_history"], 0)

    def test_it_proves_only_status_gates_dispatch(self):
        # cycle_status IS present in the workflow (validation step), so the
        # claim must be scoped to the dispatch selector, not to the file.
        ev = handoff.workflow_evidence()
        gates = ev["team_state_fields_in_the_dispatch_selector"]
        self.assertTrue(gates["status"])
        for field in ("cycle_status", "continue_recommended", "run_history"):
            self.assertFalse(gates[field],
                             f"{field} gates dispatch; the diagnosis must be "
                             "re-derived")
        outside = ev["team_state_fields_read_outside_dispatch"]
        self.assertTrue(any("cycle_status" in ln for ln in outside["cycle_status"]),
                        "cycle_status validation is disclosed, not hidden")
        self.assertEqual(outside["run_history"], [],
                         "run_history must not appear anywhere in the workflow")

    def test_evidence_index_rehashes_every_accepted_record(self):
        index = handoff.build()["evidence_index"]
        for key, meta in index.items():
            self.assertTrue(meta["present"], f"{key} missing: {meta['path']}")
            self.assertRegex(meta["sha256"], r"^[0-9a-f]{64}$")

    def test_check_mode_reports_valid_while_unapplied(self):
        out = SCRATCH / "emitted"
        handoff.main(["--out", str(out)])
        code, verdict = handoff.check(out)
        self.assertEqual(verdict["stale"], False)
        self.assertIn("VALID", verdict["verdict"])
        self.assertEqual(code, 0 if not verdict["already_applied"] else 3)

    def test_check_mode_detects_a_moved_digest(self):
        out = SCRATCH / "tampered"
        out.mkdir(parents=True, exist_ok=True)
        rec = handoff.build()
        rec["evidence_index"]["frozen_rules"]["sha256"] = "0" * 64
        (out / handoff.HANDOFF_NAME).write_text(json.dumps(rec), encoding="utf-8")
        code, verdict = handoff.check(out)
        self.assertIn("frozen_rules", verdict["stale_evidence_keys"])
        self.assertEqual(code, 3)

    def test_claim_ceiling_is_carried(self):
        rec = handoff.build()
        for phrase in ("helps a jurist", "absent from the corpus", "fit to serve",
                       "fail-closed"):
            self.assertIn(phrase, rec["claim_ceiling"])

    def test_it_names_the_actors_and_flags_the_blocking_one(self):
        actions = handoff.build()["residual_actions_outside_this_teams_scope"]
        blocking = [a for a in actions if a["blocking"]]
        self.assertEqual(len(blocking), 1)
        self.assertEqual(blocking[0]["actor"], "factory director")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        unittest.main(verbosity=2)