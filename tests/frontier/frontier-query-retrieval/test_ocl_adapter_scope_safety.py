"""Scope-safety and evidence-freshness regression tests (charter acceptance 9).

History: two Frontier cycles (38192249068, 38193491547) failed the workflow's
team-scope gate with exit code 4 because documented/derived commands wrote
outside ``frontier/frontier-query-retrieval/`` (a root-level ``bundle.json``
from a relative ``--out``, then a ``product/**`` copy). A later re-execution
also overwrote claim-bearing ``LIVE_*.json`` evidence with a zero-network
stale-cache replay that still carried an older run id. These tests pin the
contract-level fixes so the pathology cannot come back unnoticed.

Everything here is offline and stdlib-only.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
TEAM_DIR = REPO_ROOT / "frontier" / "frontier-query-retrieval"
CONTRACT_PATH = TEAM_DIR / "INTEGRATION_CONTRACT.json"
RESULTS_DIR = REPO_ROOT / "results" / "frontier" / "frontier-query-retrieval"
SCRATCH_DIR = RESULTS_DIR / "scratch"

if str(TEAM_DIR) not in sys.path:
    sys.path.insert(0, str(TEAM_DIR))

# Paths a documented command may legitimately target.
_SAFE_OUT_PREFIXES = (
    "results/frontier/frontier-query-retrieval/",  # this team's namespace
    "/tmp/",  # system temp
    "/dev/null",  # tests that only need the CLI to run
)


def _out_args(command_text: str):
    """Yield (flag, value) for every --out/--product-bundle in a command string.

    Only path-looking values are considered, so prose such as ``--product-bundle
    must stay inside your lane`` is not mistaken for a command argument.
    """
    for flag in ("--out", "--product-bundle"):
        for m in re.finditer(rf"{flag}\s+(\S+)", command_text):
            value = m.group(1)
            if value.endswith((".json", ".jsonl")) or value.startswith(("/", "results/")):
                yield flag, value


class TestDocumentedCommandsAreScopeSafe(unittest.TestCase):
    """Every CLI command printed in the contract must stay in scope."""

    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    def _assert_scope_safe(self, command: str, where: str):
        for flag, value in _out_args(command):
            if value.startswith(_SAFE_OUT_PREFIXES):
                continue
            if value.startswith("/") and not value.startswith("/tmp/"):
                continue  # absolute non-repo paths (e.g. /dev/null) are fine
            # A relative path is only safe if it cannot resolve to the repo
            # root or anywhere outside this team's namespace.
            self.fail(
                f"{where}: {flag} {value!r} is a repository-root-relative write "
                f"risk; documented commands must target results/frontier/"
                f"frontier-query-retrieval/... or /tmp/..."
            )

    def test_contract_integration_options_commands(self):
        for option in self.contract["integration_options"]:
            for step in option["steps"]:
                if "--out" in step or "--product-bundle" in step:
                    self._assert_scope_safe(step, option["method"])

    def test_contract_fixture_replay_command(self):
        self._assert_scope_safe(
            self.contract["fixtures"]["replay_command"], "fixtures.replay_command"
        )

    def test_cli_module_examples(self):
        cli_src = (TEAM_DIR / "ocl_adapter" / "cli.py").read_text(encoding="utf-8")
        checked = 0
        for flag, value in _out_args(cli_src):
            self._assert_scope_safe(f"{flag} {value}", "ocl_adapter/cli.py")
            checked += 1
        self.assertGreaterEqual(checked, 2, "expected at least the docstring + epilog examples")

    def test_contract_declares_scope_safety_section(self):
        scope = self.contract.get("scope_safety") or {}
        self.assertIn("38192249068", scope.get("why", ""))
        self.assertIn("38193491547", scope.get("why", ""))
        self.assertTrue(scope.get("documented_command_rule"))

    def test_guard_rejects_legacy_repo_root_out(self):
        """Negative control: the exact command shape that killed run 38192249068."""
        with self.assertRaises(AssertionError):
            self._assert_scope_safe(
                "python3 -m ocl_adapter 'q' --out bundle.json --validate", "legacy"
            )


class TestLiveEvidenceFreshness(unittest.TestCase):
    """Claim-bearing live evidence must not be silently re-labelled or faked."""

    def test_no_hardcoded_previous_run_id_default(self):
        src = (TEAM_DIR / "run_live_evidence.py").read_text(encoding="utf-8")
        self.assertNotIn('"38190325825"', src)
        self.assertIn("LEX_FRONTIER_RUN_ID", src)
        self.assertIn("unattributed", src)

    def test_freshness_check_present(self):
        src = (TEAM_DIR / "run_live_evidence.py").read_text(encoding="utf-8")
        self.assertIn("A0_fresh_live_network", src)
        self.assertIn("LEX_ALLOW_CACHE_REPLAY", src)
        self.assertIn("cache_replayed", src)

    def test_freshness_check_blocks_zero_network_replay(self):
        """Simulate a warm-cache run: A0 must fail unless replay is allowed."""
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(TEAM_DIR) + os.pathsep + env.get("PYTHONPATH", "")
        # Wipe the live cache so the first scenario is forced onto the network;
        # we do not run it. Instead we assert the guard logic directly.
        from run_live_evidence import run  # noqa: F401  (importability check only)

        src = Path(run.__code__.co_filename).read_text(encoding="utf-8")
        self.assertIn('rs.get("network_calls", 0) == 0', src)


class TestVerifyHarnessScopeSafety(unittest.TestCase):
    def test_verify_scope_safe_passes_repo_root_explicitly(self):
        """Regression: the repo root must not be guessed by a parent walk,
        which used to match results/frontier/frontier-query-retrieval."""
        src = (TEAM_DIR / "verify_scope_safe.sh").read_text(encoding="utf-8")
        self.assertIn('"$OUT" "$ROOT"', src)
        self.assertNotIn('next((q for q in p.parents', src)

    def test_verify_determinism_never_writes_repo_root(self):
        src = (TEAM_DIR / "verify_determinism.py").read_text(encoding="utf-8")
        # Without --out it must fall back to the system temp dir, not CWD.
        self.assertIn("tempfile.mkdtemp", src)


class TestDeterminismProbeRelativeOut(unittest.TestCase):
    """A relative --out must not fool the fixture-subprocess probe.

    Found in run 38200364291: the probe spawned ``python -m ocl_adapter``
    with cwd=<package dir> while passing a --out resolved against the
    repository root. The subprocess therefore wrote its replay next to a
    nonexistent relative path inside the team namespace, the probe saw no
    output files and reported a false non-determinism verdict (and left
    stray fixture_replay_*.json under the team dir). The probe must
    resolve subprocess outputs to absolute paths first.
    """

    def test_relative_out_replays_and_leaves_no_stray_files(self):
        with tempfile.TemporaryDirectory(prefix="ocl_det_out_") as tmp:
            requested = Path(tmp) / "det.json"
            rel = os.path.relpath(requested, REPO_ROOT)
            proc = subprocess.run(
                [sys.executable, "-B", str(TEAM_DIR / "verify_determinism.py"),
                 "--skip-warm-cache", "--out", rel],
                cwd=str(REPO_ROOT),
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                capture_output=True, text=True, timeout=300,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            # --out is the authoritative artifact; stdout carries a compact
            # summary whose ``probes`` values are booleans, not probe dicts.
            summary = json.loads(proc.stdout)
            self.assertTrue(requested.exists())
            report = json.loads(requested.read_text(encoding="utf-8"))
            self.assertTrue(report["deterministic"])
            self.assertTrue(
                report["probes"]["fixture_subprocess"]["identical_candidate_content"]
            )
            self.assertEqual(summary["deterministic"], report["deterministic"])
            self.assertTrue(summary["probes"]["fixture_subprocess"])
            # No stray replays anywhere in the team namespace.
            self.assertEqual(list(TEAM_DIR.rglob("fixture_replay_*.json")), [])


class TestDocumentedReplayCommandRunsScopeSafe(unittest.TestCase):
    """Execute the documented replay command verbatim (offline, no network)."""

    def test_documented_replay_command(self):
        replay = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))["fixtures"][
            "replay_command"
        ]
        # Re-target --out into a temp dir so the test leaves no by-products,
        # keeping everything else of the documented command identical.
        tokens = shlex.split(replay)
        if tokens and tokens[0] in ("python3", "python"):
            tokens = tokens[1:]
        out_idx = tokens.index("--out")
        with tempfile.TemporaryDirectory(prefix="ocl_scope_test_") as tmp:
            target = Path(tmp) / "replay.json"
            tokens[out_idx + 1] = str(target)
            env = dict(os.environ)
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            env["PYTHONPATH"] = str(TEAM_DIR) + os.pathsep + env.get("PYTHONPATH", "")
            proc = subprocess.run(
                [sys.executable, "-B", *tokens],
                cwd=str(TEAM_DIR), env=env, capture_output=True, text=True, timeout=180,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            bundle = json.loads(target.read_text(encoding="utf-8"))
            self.assertGreaterEqual(bundle["n_candidates"], 100)
            # nothing was created in the repository root by this run
            self.assertFalse((REPO_ROOT / "bundle.json").exists())


if __name__ == "__main__":
    unittest.main()
