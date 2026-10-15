"""Recompute, offline and exactly, which decisions the ACCEPTED adversarial
pass was able to see.

REUSE-FIRST: instead of trusting the free-text ``independence`` provenance
string, the harness imports the accepted
``frontier/frontier-generative-audit/generative_audit/adversarial.py`` from the
read-only lab/product mount, instantiates :class:`AdversarialPass` in
``fixture_mode`` (which resolves no provider and therefore opens no socket),
and calls its deterministic ``_prompt_decisions()``.

That turns "the adversarial pass saw N of M decisions" from a claim into a
reproduced measurement, and it is the only way to test whether counter rows
outside the shortlist could ever have been found.
"""

from __future__ import annotations

import copy
import importlib
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

#: The accepted generative-audit package tree on the read-only lab/product mount.
_ACCEPTED_TREE = "frontier/frontier-generative-audit"


def _mount_root() -> Optional[str]:
    for cand in (os.environ.get("LEX_PRODUCT_MOUNT"),
                 "/tmp/lex_accepted/core/product"):
        if cand and os.path.isdir(os.path.join(cand, _ACCEPTED_TREE, "generative_audit")):
            return os.path.abspath(cand)
    return None


def accepted_tree_available() -> bool:
    return _mount_root() is not None


def _import_adversarial():
    root = _mount_root()
    if root is None:
        return None, None
    pkg_parent = os.path.join(root, _ACCEPTED_TREE)
    if pkg_parent not in sys.path:
        sys.path.insert(0, pkg_parent)
    mod = importlib.import_module("generative_audit.adversarial")
    return mod, root


def recompute_shortlist(doc: Dict[str, Any], answer_prose: str = "") -> Tuple[Optional[List[str]], Dict[str, Any]]:
    """Return ``(sorted shortlist ids, provenance dict)``.

    ``(None, {...})`` when the accepted tree or the bundle cannot be packed;
    the caller then reports metric (b5)/(b6) as NOT_APPLICABLE rather than
    inventing a number.
    """
    mod, root = _import_adversarial()
    if mod is None:
        return None, {"status": "ACCEPTED_TREE_UNAVAILABLE", "searched": _ACCEPTED_TREE}
    pack = importlib.import_module("generative_audit.source_packing")
    decisions = [d for d in (doc.get("decisions") or []) if isinstance(d, dict)]
    if not decisions:
        return None, {"status": "NO_DECISIONS"}
    try:
        bundle = pack.from_product_bundle(copy.deepcopy(doc))
    except Exception as exc:  # noqa: BLE001
        return None, {"status": "PACK_FAILED", "error": f"{type(exc).__name__}: {exc}"}

    prose = answer_prose or str((doc.get("answer") or {}).get("prose") or "")
    # fixture_mode=True -> no runner is resolved, no provider call can be made.
    # model is pinned only so the object is fully deterministic; _prompt_decisions
    # does not read it.
    try:
        ap = mod.AdversarialPass(bundle=bundle, answer=prose, model="fixture://fad-offline",
                                 fixture_mode=True, runner=None)
        selected = ap._prompt_decisions()
    except Exception as exc:  # noqa: BLE001
        return None, {"status": "SHORTLIST_FAILED", "error": f"{type(exc).__name__}: {exc}"}

    ids = sorted(str(d.decision_id) for d in selected)
    return ids, {
        "status": "OK",
        "source": f"{root}/{_ACCEPTED_TREE}/generative_audit/adversarial.py",
        "class": "AdversarialPass",
        "max_prompt_sources": int(getattr(mod, "MAX_PROMPT_SOURCES", -1)),
        "challenge_marker_count": len(getattr(mod, "CHALLENGE_MARKERS", ())),
        "n_bundle_decisions": len(bundle.decisions),
        "n_shortlist": len(ids),
        "shortlist_fraction": round(len(ids) / max(1, len(bundle.decisions)), 6),
        "offline": True,
        "network_calls": 0,
        "note": "imported from the ACCEPTED tree, called in fixture_mode; the "
                "accepted module was read, never modified",
    }
