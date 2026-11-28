"""Shim-compatible tests for the pure decision helpers of the v68 discrimination gate.

No pytest fixtures, no parametrisation, stdlib only: the accepted
``evaluation.no_pytest_runner`` shim can execute every case here.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from evaluation.v68_discrimination_gate import (  # noqa: E402
    role_key_of,
    verdict_from_conditions,
)


def test_verdict_not_discriminating_when_neither_condition_holds():
    assert verdict_from_conditions(False, False) == "NOT_YET_DISCRIMINATING"


def test_verdict_discriminating_when_code_changed():
    assert verdict_from_conditions(True, False) == "DISCRIMINATING_WORK_AVAILABLE"


def test_verdict_discriminating_when_family_complete():
    assert verdict_from_conditions(False, True) == "DISCRIMINATING_WORK_AVAILABLE"


def test_verdict_discriminating_when_both_hold():
    assert verdict_from_conditions(True, True) == "DISCRIMINATING_WORK_AVAILABLE"


def test_role_key_offline_rent_default():
    p = "results/product/offline_slice/20261023T190402Z/rent-default.bundle.json"
    assert role_key_of(p) == ("offline", "rent-default")


def test_role_key_server_served():
    p = "results/product/server_slice/20261023T223109Z/served.bundle.json"
    assert role_key_of(p) == ("server", "served")
