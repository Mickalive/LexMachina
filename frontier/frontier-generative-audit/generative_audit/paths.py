"""Repository path + model-health resolution (no hardcoded absolute paths).

The v2 snapshot hard-coded /home/runner/work/... which only worked on one
CI layout.  v2.1 resolves the repository root dynamically so the package is
portable between CI runners, local clones and product copies.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional

#: Ordered preference list of free OpenCode models (no owner-provisioned cost).
DEFAULT_FREE_MODELS = [
    "opencode/nemotron-3.5-lightning-free",
    "opencode/nemotron-3-ultra-free",
    "opencode/mimo-v2.6-flash-free",
    "opencode/ling-3.1-flash-free",
]


def repo_root() -> Path:
    """Locate the LexMachina repository root.

    Resolution order:
      1. ``LEX_REPO_ROOT`` environment variable (explicit override).
      2. Walk upwards from this file until a directory contains
         ``state/model_health.json`` or ``.git``.
      3. Parent of this file's package root (``frontier/frontier-generative-audit``).
    """
    env = os.environ.get("LEX_REPO_ROOT")
    if env:
        p = Path(env).expanduser().resolve()
        if p.is_dir():
            return p

    here = Path(__file__).resolve()
    for candidate in [here.parent, *here.parents]:
        if (candidate / "state" / "model_health.json").exists() or (candidate / ".git").exists():
            return candidate
    # package lives at frontier/frontier-generative-audit/generative_audit
    return here.parent.parent.parent


def model_health_path() -> Path:
    return repo_root() / "state" / "model_health.json"


def model_health() -> dict:
    """Return the parsed model-health document, or {} when unavailable."""
    path = model_health_path()
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def healthy_models() -> List[str]:
    """Healthy free models from state, falling back to the static list."""
    health = model_health()
    models = health.get("healthy_models") or []
    cleaned = [m for m in models if isinstance(m, str) and m]
    if cleaned:
        return cleaned
    return list(DEFAULT_FREE_MODELS)


def preferred_model(fallback: Optional[str] = None) -> str:
    """First healthy free model, or ``fallback``, or the static default."""
    models = healthy_models()
    if models:
        return models[0]
    return fallback or DEFAULT_FREE_MODELS[0]
