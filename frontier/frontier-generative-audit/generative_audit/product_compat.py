"""Product ``query_result_bundle`` compatibility check (accepted core reconciled).

Audit observation on cycle 38180132239: the suite *mirrored*
``product/query/bundle.py::validate_bundle`` instead of calling it, because
the accepted core mount was absent in the audit environment.  This module
resolves that:

1. prefer the **real accepted validator** — loaded by file path from the
   workflow core mount (``/tmp/lex_accepted/core/product``), from
   ``LEX_ACCEPTED_CORE`` if set, or from an in-repo ``product/`` tree;
2. otherwise fall back to an offline mirror that is byte-for-byte faithful
   to the accepted rules (same required keys, same messages, same
   cluster / non-empty / unknown-citation checks).

The source actually used is always returned, so tests and provenance can
show which validator signed off.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

#: Accepted contract constants (product/query/bundle.py, BUNDLE_VERSION 1.0).
REQUIRED_TOP = ["bundle_version", "query", "query_variants", "answer",
                "decisions", "clusters", "relations", "provenance"]
REQUIRED_DECISION = ["decision_id", "court", "language", "rank", "score",
                     "provenance", "snippet", "cluster_id", "x", "y",
                     "counter_status", "canonical_url", "citation"]


def _candidate_validator_paths() -> List[Path]:
    env = os.environ.get("LEX_ACCEPTED_CORE")
    out: List[Path] = []
    if env:
        out.append(Path(env))
    out.append(Path("/tmp/lex_accepted/core/product"))
    here = Path(__file__).resolve()
    for base in [here.parent, *here.parents]:
        out.append(base)                      # repo root (…/frontier/frontier-generative-audit)
        out.append(base.parent)
    seen, uniq = set(), []
    for p in out:
        rp = p if p.is_absolute() else p.resolve()
        if rp not in seen:
            seen.add(rp)
            uniq.append(rp)
    return uniq


def _load_module(path: Path):
    name = f"lex_accepted_query_bundle_{abs(hash(str(path)))}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_accepted_validator() -> Tuple[Optional[Any], str]:
    """Return ``(validate_bundle_callable_or_None, source_label)``."""
    for root in _candidate_validator_paths():
        for rel in ("product/query/bundle.py", "query/bundle.py"):
            path = root / rel
            if not path.is_file():
                continue
            try:
                module = _load_module(path)
            except Exception:
                continue
            fn = getattr(module, "validate_bundle", None)
            if callable(fn):
                return fn, f"accepted-core:{path}"
    return None, "mirror:product/query/bundle.py::validate_bundle (offline fallback)"


def _mirror_validate_bundle(bundle: dict) -> List[str]:
    """Offline mirror of the accepted ``validate_bundle`` (same rules/messages)."""
    errors: List[str] = []
    for key in REQUIRED_TOP:
        if key not in bundle:
            errors.append(f"missing top-level key: {key}")
    if errors:
        return errors
    if not isinstance(bundle["decisions"], list) or not bundle["decisions"]:
        errors.append("decisions must be a non-empty list")
        return errors
    ids = set()
    for i, d in enumerate(bundle["decisions"]):
        for key in REQUIRED_DECISION:
            if key not in d:
                errors.append(f"decision[{i}] missing key: {key}")
        did = d.get("decision_id")
        if did in ids:
            errors.append(f"duplicate decision_id: {did}")
        ids.add(did)
    cited = set(bundle.get("answer", {}).get("cited_decision_ids", []))
    unknown = cited - ids
    if unknown:
        errors.append(f"answer cites unknown decision_ids: {sorted(unknown)}")
    for c in bundle.get("clusters", []):
        if "cluster_id" not in c or "label" not in c:
            errors.append(f"cluster missing id/label: {c}")
    return errors


def validate_product_bundle(bundle: Dict[str, Any]) -> Tuple[List[str], str]:
    """Validate an audited bundle with the accepted product rules.

    Returns ``(errors, source)`` where ``source`` names the validator that
    actually ran.
    """
    fn, source = load_accepted_validator()
    if fn is None:
        return _mirror_validate_bundle(bundle), source
    try:
        return list(fn(bundle)), source
    except Exception as exc:  # pragma: no cover - defensive
        return [f"accepted validator raised: {exc}"], source


#: Product-required key lists, re-exported for tests/provenance.
PRODUCT_REQUIRED_TOP = list(REQUIRED_TOP)
PRODUCT_REQUIRED_DECISION = list(REQUIRED_DECISION)

__all__ = [
    "PRODUCT_REQUIRED_DECISION",
    "PRODUCT_REQUIRED_TOP",
    "REQUIRED_DECISION",
    "REQUIRED_TOP",
    "load_accepted_validator",
    "validate_product_bundle",
]
