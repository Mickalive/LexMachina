"""Shared path bootstrap for the frontier-human-gate-harness offline tests.

Kept importable under both runners:
  * ``python tests/frontier/frontier-human-gate-harness/run_tests.py`` (stdlib)
  * ``python -m pytest tests/frontier/frontier-human-gate-harness`` (if pytest exists)
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from unittest import SkipTest

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
HARNESS_ROOT = REPO_ROOT / "frontier" / "frontier-human-gate-harness"
PACKAGE_ROOT = HARNESS_ROOT / "frontier_human_gate_harness"
STATIC_DIR = HARNESS_ROOT / "static"
TOOLS_DIR = HARNESS_ROOT / "tools"
VERIFY_JS = HERE / "js" / "verify_switch.js"
SWITCH_JS = STATIC_DIR / "lex_gate_switch.js"
FIXTURE_DIR = REPO_ROOT / "results" / "frontier" / "frontier-human-gate-harness" / "fixtures"
FIXTURE_PATH = FIXTURE_DIR / "query_result_bundle_kuendigung_101.json"
PROVENANCE_PATH = FIXTURE_DIR / "FIXTURE_PROVENANCE.json"
MASTER_PROMPT = REPO_ROOT / "LEXMACHINA_MASTER_PROMPT.md"
REALITY_CHECK = Path("/tmp/lex_accepted/core/product/product/reality_check.py")

if str(HARNESS_ROOT) not in sys.path:
    sys.path.insert(0, str(HARNESS_ROOT))

NODE = shutil.which("node")


def require_node() -> str:
    if not NODE:
        raise SkipTest("node is not installed on this machine")
    return NODE


def run_node(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([NODE, *args], capture_output=True, text=True,
                          cwd=str(cwd or REPO_ROOT), timeout=120)


def load_fixture() -> dict:
    import json

    if not FIXTURE_PATH.is_file():
        raise SkipTest(f"frozen fixture missing: {FIXTURE_PATH}")
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
