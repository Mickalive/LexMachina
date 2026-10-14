"""pytest bootstrap: put the harness package on sys.path before collection."""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_HARNESS_ROOT = _HERE.parents[2] / "frontier" / "frontier-human-gate-harness"
if str(_HARNESS_ROOT) not in sys.path:
    sys.path.insert(0, str(_HARNESS_ROOT))
