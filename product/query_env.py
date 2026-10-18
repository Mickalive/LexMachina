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
  missing and the single command that fixes it.

It never installs anything and never imports the heavy stack at module import
time: importing this file must stay free (the fast-path import budget depends
on it).
"""
from __future__ import annotations

import importlib
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
           "DISTRIBUTION_NAMES", "probe", "installed_version", "requirement_name",
           "requirements_pins", "pip_freeze"]