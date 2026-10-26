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

Query runtime self-heal
-----------------------
The second job in this file is the pinned *query* runtime.  ``core-lane.yml``
never runs ``product/bootstrap_query_env.sh``, so on a fresh runner the suite
reaches ``product/query/**`` (numpy/sklearn) with nothing installed and dies
with ``ModuleNotFoundError`` before a single product claim is tested - measured
on run 40262401687, whose agent hit that import failure and exited 0 with an
unchanged tree after ~526 s, so the wrapper's delta guard rejected it
(``LEX_ZERO_DELTA_REPAIR``, exit 67; ``quantum_expired=false``; no work-quantum
expiry occurred; evidence:
``results/product/orchestration/CYCLE_40263666190_lane_cycle_log_evidence.json``).
``audit_readiness.py`` already bootstraps for the *dossier* invocation, but the
lane wrapper invokes pytest directly, so the harness - not each test - owns the
fix: pytest imports this conftest before any test module, and
``query_env.ensure()`` runs the documented one-command bootstrap at most once
per process and never raises.  Set ``LEX_QUERY_ENV_NO_AUTOBOOTSTRAP=1`` to
observe an uninstalled environment (the fresh-runner ``-S`` probes do).
"""
from __future__ import annotations

import atexit
import os
import shutil
import sys
import tempfile
import warnings
from pathlib import Path

_TEST_OUT_ROOT = tempfile.mkdtemp(prefix="lex_human_gate_test_out_")
os.environ.setdefault("LEX_HUMAN_GATE_OUT_DIR", str(os.path.join(_TEST_OUT_ROOT, "canonical")))
os.environ.setdefault("LEX_HUMAN_GATE_SIMULATED_OUT_DIR", str(os.path.join(_TEST_OUT_ROOT, "simulated")))

# The product modules (query_env, server, ...) live one directory up; the test
# modules insert that path themselves at *their* import time, which is after
# this file runs, so the bootstrap needs it earlier.
_PRODUCT_DIR = str(Path(__file__).resolve().parents[1])
if _PRODUCT_DIR not in sys.path:
    sys.path.insert(0, _PRODUCT_DIR)

try:
    import query_env  # noqa: E402
except ImportError:  # pragma: no cover - product tree relocated
    query_env = None  # type: ignore[assignment]

if query_env is not None:
    _runtime = query_env.ensure()
    if not _runtime["ok"]:
        warnings.warn(
            "query fast-path runtime incomplete after ensure(): "
            f"missing={_runtime['missing']} remedy={_runtime['remedy']} "
            f"ensure={_runtime['ensured']}",
            RuntimeWarning,
            stacklevel=1,
        )


@atexit.register
def _cleanup() -> None:  # pragma: no cover - process teardown
    shutil.rmtree(_TEST_OUT_ROOT, ignore_errors=True)