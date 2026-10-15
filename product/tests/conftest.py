"""Test isolation for the product test suite.

Why this file exists
--------------------
Cycle 38726191935 committed five pytest byproducts into
``results/product/human_gate_sessions_simulated/``. The mechanism was a test
that ran ``human_gate_finalize.py`` without ``--out`` while the CLI's simulated
output directory resolved *inside the repository*; ``core-lane.yml`` then ran
``git add -A`` and the scratch became a lane result.

The output directories are now overridable through the environment
(``LEX_HUMAN_GATE_OUT_DIR`` / ``LEX_HUMAN_GATE_SIMULATED_OUT_DIR``). This module
points them at a temp directory **at import time** — pytest imports conftest
before it imports any test module, so ``human_gate_finalize`` reads the
override while it is being imported, before any test can reach the CLI without
``--out``. A unit run therefore cannot write into the repository's immutable
``results/`` tree even if a future test forgets ``--out`` or the override.

Tests that want the real repository directories import them explicitly
(``CANONICAL_DIR_DEFAULT`` / ``SIMULATED_DIR_DEFAULT``), and the evidence scanner
always reads the repository paths.
"""
from __future__ import annotations

import atexit
import os
import shutil
import tempfile

_TEST_OUT_ROOT = tempfile.mkdtemp(prefix="lex_human_gate_test_out_")
os.environ.setdefault("LEX_HUMAN_GATE_OUT_DIR", str(os.path.join(_TEST_OUT_ROOT, "canonical")))
os.environ.setdefault("LEX_HUMAN_GATE_SIMULATED_OUT_DIR", str(os.path.join(_TEST_OUT_ROOT, "simulated")))


@atexit.register
def _cleanup() -> None:  # pragma: no cover - process teardown
    shutil.rmtree(_TEST_OUT_ROOT, ignore_errors=True)