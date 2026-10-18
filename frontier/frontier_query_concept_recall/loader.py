"""Load the accepted product / evaluation modules BY FILE PATH.

Why not a normal import
-----------------------
``from product.query.concept_coverage import coverage_report`` triggers
``product/query/__init__.py``, which imports ``pipeline`` -> ``qmap`` ->
``numpy``.  numpy is not part of the free harness environment, so the normal
import path fails before a single number is produced.  The predecessor run
(39160486882) hit exactly this: its ``cli.py`` could never have imported, and
its committed ``harness_results.json`` does not match the schema its own code
emits.

``frozen.py`` and ``gates.py`` are pure stdlib, and so is
``concept_coverage.py``; loading them by path gives the accepted semantics
byte-for-byte with zero third-party dependencies.

Nothing here copies or re-implements accepted logic.  The functions are
imported from the mounted bytes and called directly.
"""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

ACCEPTED_PRODUCT_ROOT = Path("/tmp/lex_accepted/core/product")
ACCEPTED_EVALUATION_ROOT = Path("/tmp/lex_accepted/core/evaluation")


def _load(name: str, path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise ImportError(f"cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _register_namespace(name: str, path: Path) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__path__ = [str(path)]  # type: ignore[attr-defined]
    sys.modules[name] = module
    return module


_CACHED: dict[str, types.ModuleType] = {}


def concept_coverage() -> types.ModuleType:
    """product.query.concept_coverage (accepted bytes)."""
    if "concept_coverage" not in _CACHED:
        _CACHED["concept_coverage"] = _load(
            "lex_accepted_concept_coverage",
            ACCEPTED_PRODUCT_ROOT / "product" / "query" / "concept_coverage.py",
        )
    return _CACHED["concept_coverage"]


def product_retrieval() -> types.ModuleType:
    """product.query.retrieval -- carries the accepted EXPANSION lexicon."""
    if "product_retrieval" not in _CACHED:
        _CACHED["product_retrieval"] = _load(
            "lex_accepted_product_retrieval",
            ACCEPTED_PRODUCT_ROOT / "product" / "query" / "retrieval.py",
        )
    return _CACHED["product_retrieval"]


def frozen() -> types.ModuleType:
    if "frozen" not in _CACHED:
        _register_namespace("evaluation", ACCEPTED_EVALUATION_ROOT / "evaluation")
        _register_namespace(
            "evaluation.retrieval_gate",
            ACCEPTED_EVALUATION_ROOT / "evaluation" / "retrieval_gate",
        )
        _CACHED["frozen"] = _load(
            "evaluation.retrieval_gate.frozen",
            ACCEPTED_EVALUATION_ROOT / "evaluation" / "retrieval_gate" / "frozen.py",
        )
        _CACHED["gates"] = _load(
            "evaluation.retrieval_gate.gates",
            ACCEPTED_EVALUATION_ROOT / "evaluation" / "retrieval_gate" / "gates.py",
        )
    return _CACHED["frozen"]


def gates() -> types.ModuleType:
    frozen()
    return _CACHED["gates"]


__all__ = [
    "ACCEPTED_PRODUCT_ROOT",
    "ACCEPTED_EVALUATION_ROOT",
    "concept_coverage",
    "product_retrieval",
    "frozen",
    "gates",
]
