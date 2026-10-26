"""The query fast path's third-party runtime, declared in one place.

Why this module exists
----------------------
``product/query/qmap.py`` and ``product/query/relevance.py`` import ``numpy``,
and ``qmap.py`` uses ``sklearn`` for TF-IDF/SVD/KMeans.  Those imports are the
vertical slice: without them ``product/offline_slice.py``,
``product/cycle_verify.py`` (checks ``slice``/``counter``/``relation``/
``relation_direction``/``tracked``) and the shipped server cannot run at all.

None of that used to be written down anywhere, and **no step of
``.github/workflows/core-lane.yml`` installs them** (only
``query-map-ci.yml`` and ``product-reality-check.yml`` run
``pip install -r product/requirements-query.txt``).  So on a fresh runner the
lane's own instrument dies with ``ModuleNotFoundError: No module named 'numpy'``
and the resulting artifact is indistinguishable from a product defect - the
measured instance is recorded in
``results/product/orchestration/CYCLE_39128456801_dep_class.json``.

This module makes the runtime explicit and checkable:

* ``REQUIRED`` - the modules the fast path imports, derived from the shipped
  code (``product/query/**`` + ``product/query_app.py`` +
  ``product/offline_slice.py``), not from what happens to be installed;
* ``PINNED`` - the exact versions this lane measured, recorded beside the
  hashes of every reproducibility claim per the standing numeric rule;
* ``probe()`` - a stdlib-only import check that returns what is present, what is
  missing and the single command that fixes it.  ``probe()`` never installs.
* ``ensure()`` - the explicit, opt-in self-heal: probe, and if a *required*
  module is missing run the one-command bootstrap **once per process**, then
  re-probe.  ``product/tests/conftest.py`` calls it so the lane's own suite
  can no longer die on a fresh runner before any product claim is testable -
  the observed instance is ``results/product/orchestration/
  CYCLE_40263666190_lane_cycle_log_evidence.json`` (run 40262401687 burned its
  whole quantum on ``ModuleNotFoundError``).  ``ensure()`` is skippable with
  ``LEX_QUERY_ENV_NO_AUTOBOOTSTRAP=1`` for callers that must observe an
  uninstalled environment.

Importing this file never installs anything and never imports the heavy stack
at module import time: importing this file must stay free (the fast-path import
budget depends on it).  Installation only happens inside an explicit
``ensure()`` call.
"""
from __future__ import annotations

import importlib
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = REPO_ROOT / "product" / "requirements-query.txt"
BOOTSTRAP = REPO_ROOT / "product" / "bootstrap_query_env.sh"

#: Modules the query fast path imports, with the module that needs them.
REQUIRED: dict[str, str] = {
    "numpy": "product/query/qmap.py, product/query/relevance.py",
    "sklearn": "product/query/qmap.py (TfidfVectorizer/TruncatedSVD/KMeans)",
}

#: import name -> distribution name, for the few pairs that differ.
DISTRIBUTION_NAMES = {"sklearn": "scikit-learn"}

#: Versions this lane measured on a real run of the vertical slice. Pins, not
#: floors: the recorded numeric environment travels with every sha.
PINNED: dict[str, str] = {
    "numpy": "2.5.4",
    "scipy": "1.18.1",          # scikit-learn's own dependency, recorded not required
    "sklearn": "1.9.1",
    "pytest": "9.1.1",          # the lane suite, not the fast path
}

REMEDY = "bash product/bootstrap_query_env.sh"


def installed_version(module: str) -> str | None:
    try:
        mod = importlib.import_module(module)
    except Exception:
        return None
    return str(getattr(mod, "__version__", "unknown"))


def probe() -> dict:
    """Import every required module and report the environment honestly."""
    present: dict[str, str | None] = {}
    missing: list[str] = []
    for module in sorted(REQUIRED):
        version = installed_version(module)
        present[module] = version
        if version is None:
            missing.append(module)
    return {
        "python": sys.version.split()[0],
        "required": dict(REQUIRED),
        "pinned": dict(PINNED),
        "installed": present,
        "installed_matches_pin": {
            m: (present.get(m) == v) for m, v in PINNED.items() if m in present
        },
        "missing": missing,
        "ok": not missing,
        "remedy": REMEDY,
        "requirements_file": "product/requirements-query.txt",
        "workflow_gap": (
            "no step of .github/workflows/core-lane.yml installs "
            "product/requirements-query.txt, so a fresh runner has none of these; "
            "recorded as a control-plane item, never edited from this lane"
        ),
    }


def requirement_name(module: str) -> str:
    """Import name -> distribution name (``sklearn`` ships as ``scikit-learn``)."""
    return DISTRIBUTION_NAMES.get(module, module)


#: One attempt per process: a failed install must not be retried per test.
_ENSURE_ATTEMPTED = False

#: Why ``ensure()`` exists, published so callers and reports cite the same fact.
ENSURE_REASON = (
    "the core-lane team job installs nothing, so a fresh runner reaches the "
    "vertical slice with no numpy/scikit-learn; observed on run 40262401687, "
    "whose producer burned its whole quantum on ModuleNotFoundError and exited "
    "LEX_ZERO_DELTA_REPAIR (evidence: results/product/orchestration/"
    "CYCLE_40263666190_lane_cycle_log_evidence.json)"
)


def ensure(*, install: bool = True, timeout_s: int = 900) -> dict:
    """Probe the pinned runtime and self-heal a *missing* required module.

    Returns the post-``probe()`` dict, extended with an ``ensured`` block:

    * ``attempted`` - whether the bootstrap ran in this process;
    * ``installed_by_ensure`` - the install actually happened and the runtime
      now probes ok;
    * ``skipped`` - ``install=False`` or ``LEX_QUERY_ENV_NO_AUTOBOOTSTRAP=1``
      (callers that must observe an uninstalled environment, e.g. the
      fresh-runner ``-S`` probes, set the flag);
    * ``error`` - the bootstrap failed (offline runner, ...).  ``ensure()``
      never raises: an environment that cannot install itself is reported, so
      the caller fails with the remedy command instead of a bare
      ``ModuleNotFoundError``.

    Version *mismatches* are not repaired here - a present-but-different pin is
    a disclosure (``installed_matches_pin``), not a crash, and silently
    re-pinning a working environment would change measured numbers behind the
    caller's back.
    """
    global _ENSURE_ATTEMPTED
    result = probe()
    block: dict[str, object] = {"attempted": False, "installed_by_ensure": False,
                                "skipped": None, "error": None,
                                "reason": ENSURE_REASON}
    result["ensured"] = block
    if result["ok"]:
        block["skipped"] = "already_present"
        return result
    if not install:
        block["skipped"] = "install_disabled"
        return result
    if os.environ.get("LEX_QUERY_ENV_NO_AUTOBOOTSTRAP"):
        block["skipped"] = "LEX_QUERY_ENV_NO_AUTOBOOTSTRAP"
        return result
    if _ENSURE_ATTEMPTED:
        block["skipped"] = "already_attempted"
        return result
    _ENSURE_ATTEMPTED = True
    block["attempted"] = True
    try:
        proc = subprocess.run(  # noqa: S603
            ["bash", str(BOOTSTRAP)], cwd=str(REPO_ROOT), timeout=timeout_s,
            capture_output=True, text=True, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        block["error"] = f"{type(exc).__name__}: {exc}"
        return result
    if proc.returncode != 0:
        tail = (proc.stdout + proc.stderr).strip().splitlines()[-3:]
        block["error"] = f"exit {proc.returncode}: {tail}"
        return result
    after = probe()
    block["installed_by_ensure"] = bool(after["ok"])
    after["ensured"] = block
    return after


def requirements_pins() -> dict[str, str]:
    """Parse ``numpy>=1.24.0`` style floors out of the requirements file."""
    if not REQUIREMENTS.is_file():
        return {}
    pins: dict[str, str] = {}
    for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        for sep in (">=", "==", "===", "~="):
            if sep in line:
                name, _, version = line.partition(sep)
                pins[name.strip().lower()] = version.strip()
                break
        else:
            pins[line.lower()] = "*"
    return pins


def pip_freeze() -> dict[str, str]:
    """Best-effort version map for disclosure; never raises."""
    try:
        out = subprocess.run(  # noqa: S603
            [sys.executable, "-m", "pip", "freeze"], capture_output=True,
            text=True, timeout=120, check=False,
        )
    except Exception:
        return {}
    frozen: dict[str, str] = {}
    for line in (out.stdout or "").splitlines():
        if "==" in line:
            name, _, version = line.partition("==")
            frozen[name.strip().lower()] = version.strip()
    return frozen


__all__ = ["REQUIRED", "PINNED", "REMEDY", "REQUIREMENTS", "BOOTSTRAP",
           "DISTRIBUTION_NAMES", "probe", "ensure", "ENSURE_REASON",
           "installed_version", "requirement_name",
           "requirements_pins", "pip_freeze"]