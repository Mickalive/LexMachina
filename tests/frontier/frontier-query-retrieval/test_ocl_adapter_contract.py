"""Integration-contract validity tests (charter acceptance 9).

The machine-readable contract must stay in sync with the adapter package:
documented paths exist, public API symbols import, and the documented CLI /
fixture replay commands actually run.
"""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
TEAM_DIR = REPO_ROOT / "frontier" / "frontier-query-retrieval"
CONTRACT_PATH = TEAM_DIR / "INTEGRATION_CONTRACT.json"
ADAPTER_DIR = TEAM_DIR / "ocl_adapter"

if str(TEAM_DIR) not in sys.path:
    sys.path.insert(0, str(TEAM_DIR))

import ocl_adapter  # noqa: E402
from ocl_adapter import (  # noqa: E402
    AdapterConfig,
    build_candidate_bundle,
    to_product_bundle,
    validate_candidate_bundle,
)


class TestContractFile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    def test_contract_metadata(self):
        self.assertEqual(self.contract["team_id"], "frontier-query-retrieval")
        self.assertEqual(self.contract["charter_version"], 2)
        self.assertIn("handoff", self.contract)
        self.assertIn("candidate_bundle", self.contract)
        self.assertIn("product_bundle", self.contract)

    def test_package_dir_exists(self):
        pkg = self.contract["adapter"]["package_dir"]
        self.assertTrue((REPO_ROOT / pkg).is_dir(), pkg)
        self.assertTrue((REPO_ROOT / pkg / "__init__.py").is_file())

    def test_public_api_symbols_exist(self):
        for entry in self.contract["public_api"]:
            name = entry["symbol"]
            kind = entry.get("kind", "")
            # Some entries describe groups of symbols (classes, exceptions).
            if " " in name or "/" in name or kind in ("classes", "hierarchy"):
                continue
            self.assertTrue(hasattr(ocl_adapter, name), f"missing public symbol {name}")

    def test_documented_test_files_exist(self):
        for rel in self.contract["tests"]["files"]:
            self.assertTrue((REPO_ROOT / rel).is_file(), f"missing test file {rel}")

    def test_handoff_artifacts_exist(self):
        for rel in self.contract["handoff"]["artifacts"]:
            path = REPO_ROOT / rel
            self.assertTrue(path.exists(), f"missing handoff artifact {rel}")

    def test_fixture_paths_in_contract(self):
        fixtures = self.contract["fixtures"]
        self.assertTrue((REPO_ROOT / fixtures["cache_dir"]).is_dir())
        self.assertTrue((REPO_ROOT / fixtures["meta"]).is_file())

    def test_adapter_version_matches(self):
        self.assertEqual(self.contract["adapter"]["version"], ocl_adapter.__version__)

    def test_candidate_fields_match_bundle_module(self):
        from ocl_adapter.bundle import CANDIDATE_REQUIRED

        documented = self.contract["candidate_bundle"]["required_candidate_fields"]
        self.assertEqual(sorted(documented), sorted(CANDIDATE_REQUIRED))

    def test_product_required_fields_match_bridge(self):
        from ocl_adapter.bundle import PRODUCT_REQUIRED_DECISION, PRODUCT_REQUIRED_TOP

        self.assertEqual(
            sorted(self.contract["product_bundle"]["required_top_keys"]),
            sorted(PRODUCT_REQUIRED_TOP),
        )
        self.assertEqual(
            sorted(self.contract["product_bundle"]["required_decision_keys"]),
            sorted(PRODUCT_REQUIRED_DECISION),
        )

    def test_rate_limit_defaults_respect_charter(self):
        rl = self.contract["rate_limits"]
        self.assertLessEqual(rl["charter_max_rps"], 5.0)
        self.assertLessEqual(rl["default_max_rps"], rl["charter_max_rps"])
        self.assertFalse(rl["api_key_required"])

    def test_stdlib_only_claim(self):
        self.assertEqual(self.contract["adapter"]["third_party_dependencies"], [])
        self.assertEqual(ocl_adapter.AdapterConfig().mode, "live")


class TestSysPathImportOption(unittest.TestCase):
    def test_documented_import_snippet(self):
        # Contract option 1: sys.path.insert + from ocl_adapter import ...
        self.assertTrue(callable(build_candidate_bundle))
        self.assertTrue(callable(to_product_bundle))
        self.assertTrue(callable(validate_candidate_bundle))
        cfg = AdapterConfig()
        self.assertEqual(cfg.base_url, "https://mcp.opencaselaw.ch/api")


class TestContractCliCommandRuns(unittest.TestCase):
    def test_fixture_replay_command(self):
        fixtures = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))["fixtures"]
        cmd = [
            sys.executable,
            "-m",
            "ocl_adapter",
            fixtures["query"],
            "--preset",
            "fixtures",
            "--out",
            "/dev/null",
            "--validate",
            "--quiet",
        ]
        import os

        env = dict(os.environ)
        env["PYTHONPATH"] = str(TEAM_DIR) + os.pathsep + env.get("PYTHONPATH", "")
        proc = subprocess.run(
            cmd, cwd=str(TEAM_DIR), env=env, capture_output=True, text=True, timeout=120
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main()
