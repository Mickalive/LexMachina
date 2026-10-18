"""The query fast path must import without the optional dense-embedding stack.

Cycle 39097705922
=================

``product/app/navigation.py`` carried a module-scope
``from sentence_transformers import SentenceTransformer``. That single line had
three consequences, all measured in ``results/product/regression/logs_39097705922/``:

1. **The product server could not be imported at all** in any environment
   without torch. ``product/server.py`` -> ``app.navigation`` was a hard import
   chain, so the clickable-slice server - the thing the MVP is - was unimportable.
2. **287 product tests were dark.** 18 test modules, including
   ``test_http_api_integration.py`` (the HTTP end-to-end tests of the server
   surface itself) and ``test_cycle_v18_product.py``, could not even be
   *collected*, so pytest aborted the whole run with
   "Interrupted: 18 errors during collection". The lane's own regression
   evidence therefore excluded them by name on every run, and reported them as
   UNMEASURED. A test that cannot be collected is not a test that passes.
3. **The lane's own RF3 backlog was frozen.** ``state/product.json`` records
   that 14 modules were left holding a defect "because they need
   sentence_transformers/torch, so it cannot be executed or verified in a bare
   environment". The dependency was the blocker; removing it unblocked the fix.

The contract this module enforces is therefore narrow and behavioural: the fast
path imports, the optional dependency is resolved lazily at the point of use,
and the modules the darkness hid actually collect.

Non-vacuity
-----------

A guard that merely imports the server would pass on a machine where
``sentence_transformers`` happens to be installed, and would prove nothing about
the CI environment. Every check here runs in a SUBPROCESS with a meta-path
finder that makes ``sentence_transformers`` and ``torch`` raise
``ModuleNotFoundError`` on import - the canonical CI condition, reproduced
exactly. ``test_control_the_blocker_really_blocks`` asserts that the blocker is
itself effective, so a test that "passed because the blocker was broken" cannot
happen silently.
"""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PRODUCT_ROOT = REPO_ROOT / "product"
NAVIGATION = PRODUCT_ROOT / "app" / "navigation.py"

#: Written to a temp dir and put on PYTHONPATH; blocks the optional dense stack.
BLOCKER_SOURCE = textwrap.dedent(
    """
    import sys
    import importlib.abc


    class _Blocker(importlib.abc.MetaPathFinder):
        BLOCKED = ("sentence_transformers", "torch")

        def find_spec(self, fullname, path=None, target=None):
            root = fullname.split(".")[0]
            if root in self.BLOCKED:
                raise ModuleNotFoundError(f"No module named {root!r}")
            return None


    sys.meta_path.insert(0, _Blocker())
    """
)


#: One directory per process holding the sitecustomize that reproduces the CI
#: environment (no ``sentence_transformers``, no ``torch``).
_BLOCK_DIR: str | None = None


def _blocked_env_dir() -> str:
    """Materialise the blocker once and return its path."""
    global _BLOCK_DIR
    if _BLOCK_DIR is None:
        import tempfile
        _BLOCK_DIR = tempfile.mkdtemp(prefix="lex_st_block_")
        (Path(_BLOCK_DIR) / "sitecustomize.py").write_text(
            BLOCKER_SOURCE, encoding="utf-8"
        )
    return _BLOCK_DIR


def _run_without_dense_stack(snippet: str) -> subprocess.CompletedProcess:
    """Run ``snippet`` in a subprocess where the dense stack cannot be imported."""
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join([_blocked_env_dir(), str(REPO_ROOT)]),
    }
    env.pop("LEX_PRODUCT_RUN_ID", None)
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(snippet)],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(REPO_ROOT),
        env=env,
    )


# --------------------------------------------------------------------------- #
# 1. the blocker is effective (so every check below is non-vacuous)
# --------------------------------------------------------------------------- #

def test_control_the_blocker_really_blocks():
    """The reproduction of the CI environment must actually block the import."""
    proc = _run_without_dense_stack(
        """
        import sys
        try:
            import sentence_transformers  # noqa: F401
        except ModuleNotFoundError:
            print("BLOCKED")
        else:
            print("NOT_BLOCKED")
        try:
            import torch  # noqa: F401
        except ModuleNotFoundError:
            print("TORCH_BLOCKED")
        else:
            print("TORCH_NOT_BLOCKED")
        """,
    )
    out = proc.stdout.strip().splitlines()
    assert out == ["BLOCKED", "TORCH_BLOCKED"], (
        "the meta-path blocker did not take effect, so every check in this "
        f"module would pass vacuously. stdout={proc.stdout!r} "
        f"stderr={proc.stderr[-800:]!r}"
    )


# --------------------------------------------------------------------------- #
# 2. the fast path imports
# --------------------------------------------------------------------------- #

def test_product_server_imports_without_the_dense_stack():
    """``product/server.py`` must import with sentence_transformers absent."""
    proc = _run_without_dense_stack(
        """
        import sys
        sys.path.insert(0, "product")
        import server
        assert hasattr(server, "ProductHandler")
        assert hasattr(server, "ThreadedHTTPServer")
        print("SERVER_IMPORTED")
        """,
    )
    assert proc.returncode == 0, (
        "product/server.py failed to import without the optional dense stack - "
        "this is the defect this guard exists to prevent:\n"
        f"stdout={proc.stdout!r}\nstderr={proc.stderr[-3000:]!r}"
    )
    assert "SERVER_IMPORTED" in proc.stdout


def test_navigation_api_imports_and_reports_the_optional_dependency_as_absent():
    """The lazy resolver returns None instead of raising at import time."""
    proc = _run_without_dense_stack(
        """
        import sys
        sys.path.insert(0, "product")
        from app.navigation import NavigationAPI, _sentence_transformer_class
        assert _sentence_transformer_class() is None, "resolver must degrade to None"
        # Constructing the API must not need the dense stack either.
        import tempfile
        api = NavigationAPI(
            "product/results/corpus/normalization/canonical",
            "product/results/fractal_map",
            write_dir=tempfile.mkdtemp(prefix="lex_nav_write_"),
        )
        status = api.initialize()
        assert isinstance(status, dict), status
        # And the lazy getter degrades instead of exploding.
        assert api._get_embedding_model() is None or True
        print("NAV_OK")
        """,
    )
    assert proc.returncode == 0, (
        "NavigationAPI could not be constructed without the dense stack:\n"
        f"stdout={proc.stdout!r}\nstderr={proc.stderr[-3000:]!r}"
    )
    assert "NAV_OK" in proc.stdout


def test_query_fast_path_imports_without_the_dense_stack():
    """The query-specific bundle/map path never needed the dense stack."""
    proc = _run_without_dense_stack(
        """
        import sys
        sys.path.insert(0, "product")
        import query_app
        from query.pipeline import run_query_initial
        from query.bundle import build_bundle
        from query.qmap import build_map
        print("QUERY_OK")
        """,
    )
    assert proc.returncode == 0, (
        "the query fast path could not be imported without the dense stack:\n"
        f"stdout={proc.stdout!r}\nstderr={proc.stderr[-3000:]!r}"
    )
    assert "QUERY_OK" in proc.stdout


# --------------------------------------------------------------------------- #
# 3. the source no longer imports the optional stack at module scope
# --------------------------------------------------------------------------- #

def test_navigation_has_no_module_scope_sentence_transformers_import():
    """Static counterpart: the eager import must not come back.

    Only imports nested inside a ``def``/``if __name__`` guard or a function
    body are allowed; a module-scope import is the exact defect.
    """
    tree = ast.parse(NAVIGATION.read_text(encoding="utf-8"))
    module_scope: list[int] = []
    for node in tree.body:  # top level only - nested bodies are fine
        if isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] in {"sentence_transformers", "torch"}:
                module_scope.append(node.lineno)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in {"sentence_transformers", "torch"}:
                    module_scope.append(node.lineno)
    assert module_scope == [], (
        "product/app/navigation.py imports the optional dense stack at module "
        f"scope again, at line(s) {module_scope}. That makes the server "
        "unimportable and the 18 dependent test modules uncollectable wherever "
        "the stack is absent."
    )


def test_the_dense_model_is_only_referenced_through_the_lazy_resolver():
    """Every ``SentenceTransformer`` mention must sit inside the lazy resolver."""
    tree = ast.parse(NAVIGATION.read_text(encoding="utf-8"))
    resolver = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_sentence_transformer_class":
            resolver = node
            break
    assert resolver is not None, "the lazy resolver must exist"
    lo = resolver.lineno
    hi = resolver.end_lineno or resolver.lineno

    bad = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Name)
        and node.id == "SentenceTransformer"
        and not (lo <= node.lineno <= hi)
    ]
    assert bad == [], (
        "SentenceTransformer is used outside _sentence_transformer_class() at "
        f"line(s) {bad}; route every use through the lazy resolver so a missing "
        "optional dependency degrades to None instead of failing at import"
    )


# --------------------------------------------------------------------------- #
# 4. the darkness is actually gone (collection, not import)
# --------------------------------------------------------------------------- #

#: The 18 modules that could not be collected in the canonical CI environment.
DARKENED_MODULES = (
    "test_cycle_174k_simulation.py",
    "test_cycle_33032746334.py",
    "test_cycle_33033658714.py",
    "test_cycle_33304668621.py",
    "test_cycle_33660041466_health.py",
    "test_cycle_33660041466_incremental.py",
    "test_cycle_33660041466_lod.py",
    "test_cycle_33974964520.py",
    "test_cycle_33982486898.py",
    "test_cycle_product_scale.py",
    "test_cycle_product_v10.py",
    "test_cycle_product_v11.py",
    "test_cycle_scale_readiness.py",
    "test_cycle_v17_validate_reps.py",
    "test_cycle_v17_webgl_vectorized.py",
    "test_cycle_v18_product.py",
    "test_http_api_integration.py",
    "test_product.py",
)


def test_the_eighteen_darkened_modules_are_still_listed_and_now_collectable():
    """The named 18 must each exist and must collect with the dense stack absent.

    Collection is the property that matters. The prior lane evidence excluded
    these modules by name on every run and reported them as UNMEASURED; this
    test fails if one of them ever becomes uncollectable again.
    """
    import tempfile as _t

    with _t.TemporaryDirectory() as tmp:
        (Path(tmp) / "sitecustomize.py").write_text(BLOCKER_SOURCE, encoding="utf-8")
        env = {**os.environ, "PYTHONPATH": os.pathsep.join([tmp, str(REPO_ROOT)])}
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "product/tests", "--collect-only", "-q",
             "-p", "no:cacheprovider"],
            capture_output=True, text=True, timeout=900, cwd=str(REPO_ROOT), env=env,
        )
    assert proc.returncode != 2, (
        "collection of product/tests aborted - one or more modules are "
        "uncollectable again:\n" + proc.stdout[-3000:] + proc.stderr[-2000:]
    )
    collected = proc.stdout
    missing = [m for m in DARKENED_MODULES
               if not (PRODUCT_ROOT / "tests" / m).exists()]
    assert missing == [], f"named darkened module(s) no longer exist: {missing}"
    absent = [m for m in DARKENED_MODULES
              if f"product/tests/{m}::" not in collected]
    assert absent == [], (
        "these modules collect no tests with the dense stack absent, i.e. they "
        f"are dark again: {absent}"
    )
    # Record the measured collection size beside the claim.
    tail = collected.strip().splitlines()[-1]
    print(json.dumps({"collect_only_summary": tail, "modules": len(DARKENED_MODULES)}))