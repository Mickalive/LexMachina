"""Shared fixtures.

The harness lives in frontier/frontier-counter-label-integrity/ (hyphens are not
importable, so the path is prepended here).  The accepted product mount is read
read-only; nothing in this suite writes to it.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
HARNESS_DIR = os.path.join(REPO_ROOT, "frontier", "frontier-counter-label-integrity")
if HARNESS_DIR not in sys.path:
    sys.path.insert(0, HARNESS_DIR)

RULES_PATH = os.path.join(
    REPO_ROOT, "results", "frontier", "frontier-counter-label-integrity", "RULES.json"
)
RESULTS_DIR = os.path.join(REPO_ROOT, "results", "frontier", "frontier-counter-label-integrity")
REPORT_PATH = os.path.join(RESULTS_DIR, "REPORT.json")
NONVAC_PATH = os.path.join(RESULTS_DIR, "NON_VACUITY.json")

PRODUCT_MOUNT = os.environ.get("LEX_PRODUCT_MOUNT", "/tmp/lex_accepted/core/product")


def _require(path: str) -> str:
    if not os.path.exists(path):
        pytest.skip(f"missing required artifact: {path}")
    return path


@pytest.fixture(scope="session")
def repo_root() -> str:
    return REPO_ROOT


@pytest.fixture(scope="session")
def rules_path() -> str:
    return _require(RULES_PATH)


@pytest.fixture(scope="session")
def rules(rules_path):
    from frontier_counter_label_integrity.rules import load_rules

    return load_rules(rules_path)


@pytest.fixture(scope="session")
def report():
    with open(_require(REPORT_PATH), "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


@pytest.fixture(scope="session")
def non_vacuity():
    with open(_require(NONVAC_PATH), "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))["result"]


@pytest.fixture(scope="session")
def product_mount() -> str:
    if not os.path.isdir(PRODUCT_MOUNT):
        pytest.skip(f"accepted product mount not available: {PRODUCT_MOUNT}")
    return PRODUCT_MOUNT


def git(repo_root: str, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", repo_root, *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def freeze_commit_time(repo_root: str) -> str:
    out = git(
        repo_root,
        "log",
        "--format=%cI",
        "--",
        "results/frontier/frontier-counter-label-integrity/RULES.json",
    )
    return out.splitlines()[-1]