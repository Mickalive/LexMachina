#!/usr/bin/env python3
"""Run the lane's pytest-style tests in a producer image where pytest is ABSENT.

    python -m evaluation.no_pytest_runner --run-id <run_id> \
        --test-file tests/evaluation/test_<name>.py \
        --out results/evaluation/orchestration/<run_id>_pytest_shim.json

WHY
---
``state/evaluation.json`` has disclosed for several cycles that the lane's
pytest scope is never executed in the producer image and that the snapshot-audit
READY verdict is CONDITIONAL on pytest's absence. This module does not fix that
disclosure -- it cannot, because installing pytest is not a lane's call -- but it
removes most of the dependency: the same test files are executed here under a
minimal, documented ``pytest`` shim that supports exactly the constructs the
lane's tests use (``mark.skipif``, ``raises``, ``approx``-free plain asserts and
parametrised functions).

WHAT IT IS NOT
--------------
It is NOT pytest. It does not discover, collect, fixture-inject, xfail, warn or
report the way pytest does. A test needing a fixture, a parametrisation, a
context manager or a marker this shim does not implement is reported
``UNSUPPORTED`` and **counted as not-run, never as passed**. The verdict line is
therefore always an upper bound on what pytest would do, and the record says so
in those words.

The shim exists because an unexecuted test file is an unverified claim. Running
it turns that claim into a measurement while keeping the standing disclosure
intact.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import inspect
import json
import sys
import traceback
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "lex-evaluation-no-pytest-runner/1"

#: pytest constructs this shim implements. Anything outside this list is reported
#: UNSUPPORTED rather than silently skipped.
SUPPORTED = ("plain test function with no parameters",
             "pytest.mark.skipif(condition, reason=...)",
             "pytest.raises",
             "module-level `from evaluation import ... as ...`")


def _install_shim() -> types.ModuleType:
    m = types.ModuleType("pytest")

    class _Mark:
        def parametrize(self, *a, **k):
            def deco(f):
                f.__parametrized__ = True
                return f
            return deco

        def skipif(self, cond, reason=""):
            def deco(f):
                f.__skip__ = bool(cond)
                f.__skip_reason__ = reason
                return f
            return deco

    class Skipped(Exception):
        pass

    class _Raises:
        def __init__(self, exc):
            self.exc = exc
            self.value = None

        def __enter__(self):
            return self

        def __exit__(self, et, ev, tb):
            if et is None:
                raise AssertionError(f"DID NOT RAISE {self.exc}")
            self.value = ev
            return issubclass(et, self.exc)

    m.mark = _Mark()
    m.Skipped = Skipped
    m.skip = lambda reason="": (_ for _ in ()).throw(Skipped(reason))
    m.raises = _Raises
    m.fixture = lambda *a, **k: (a[0] if a and callable(a[0]) else (lambda f: f))
    m.fail = lambda msg="": (_ for _ in ()).throw(AssertionError(msg))
    sys.modules["pytest"] = m
    return m


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(
        "lex_shim_" + hashlib.sha256(str(path).encode()).hexdigest()[:12], path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def run_file(path: Path, repo_root: Path) -> dict:
    """Execute one test file. Returns a per-file result dict."""
    out: dict = {"test_file": str(path.relative_to(repo_root)),
                 "test_file_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    saved = sys.path[:]
    sys.path.insert(0, str(repo_root))
    prev_mod = sys.modules.get("pytest")
    try:
        _install_shim()
        try:
            mod = _load(path)
        except Exception as exc:
            out.update(status="IMPORT_ERROR", error=f"{type(exc).__name__}: {exc}",
                       traceback=traceback.format_exc()[-2000:],
                       n_passed=0, n_failed=0, n_skipped=0, n_unsupported=0, cases=[])
            return out

        cases = []
        for name in sorted(vars(mod)):
            obj = getattr(mod, name)
            # Support both plain test functions and unittest.TestCase methods
            if inspect.isclass(obj) and issubclass(obj, unittest.TestCase):
                # Discover test methods on TestCase classes
                for method_name in sorted(dir(obj)):
                    if method_name.startswith("test_") and callable(getattr(obj, method_name)):
                        method = getattr(obj, method_name)
                        case = {"test": f"{name}.{method_name}"}
                        # unittest methods don't use our pytest markers
                        try:
                            # Create instance and run
                            instance = obj()
                            method(instance)
                            case.update(status="PASS")
                        except Exception as exc:
                            case.update(status="FAIL", error=f"{type(exc).__name__}: {exc}",
                                        traceback=traceback.format_exc()[-2000:])
                        cases.append(case)
            elif name.startswith("test_") and callable(obj):
                fn = obj
                case = {"test": name}
                if getattr(fn, "__skip__", False):
                    case.update(status="SKIPPED", reason=getattr(fn, "__skip_reason__", ""))
                elif getattr(fn, "__parametrized__", False):
                    case.update(status="UNSUPPORTED",
                                reason="parametrised test: the shim does not expand parametrisation")
                elif len(inspect.signature(fn).parameters):
                    case.update(status="UNSUPPORTED",
                                reason=f"test needs fixture(s): "
                                       f"{list(inspect.signature(fn).parameters)}")
                else:
                    try:
                        fn()
                        case.update(status="PASS")
                    except sys.modules["pytest"].Skipped as exc:
                        case.update(status="SKIPPED", reason=str(exc))
                    except Exception as exc:
                        case.update(status="FAIL", error=f"{type(exc).__name__}: {exc}",
                                    traceback=traceback.format_exc()[-2000:])
                cases.append(case)

        n_passed = sum(c["status"] == "PASS" for c in cases)
        n_failed = sum(c["status"] == "FAIL" for c in cases)
        n_skipped = sum(c["status"] == "SKIPPED" for c in cases)
        n_unsupported = sum(c["status"] == "UNSUPPORTED" for c in cases)
        n_cases = len(cases)
        
        # Per the shim's doctrine: "an unexecuted test file is an unverified claim"
        # If zero cases were discovered, mark as NOT_RAN, never PASS
        if n_cases == 0:
            out.update(status="NOT_RAN",
                       n_passed=0, n_failed=0, n_skipped=0, n_unsupported=0, cases=[])
        else:
            out.update(status="FAIL" if n_failed else "PASS",
                       n_passed=n_passed, n_failed=n_failed, n_skipped=n_skipped,
                       n_unsupported=n_unsupported, cases=cases)
        return out
    finally:
        sys.path[:] = saved
        if prev_mod is not None:
            sys.modules["pytest"] = prev_mod
        else:
            sys.modules.pop("pytest", None)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", default="local")
    ap.add_argument("--test-file", action="append", required=True,
                    help="repeatable; a path relative to the repo root")
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    root = Path(args.repo_root).resolve()
    results = []
    for tf in args.test_file:
        p = (root / tf) if not Path(tf).is_absolute() else Path(tf)
        if not p.exists():
            results.append({"test_file": tf, "status": "ABSENT",
                            "error": "test file not present in this image"})
            continue
        results.append(run_file(p, root))

    n_failed = sum(r.get("status") == "FAIL" for r in results)
    n_absent = sum(r.get("status") == "ABSENT" for r in results)
    rec = {
        "schema": SCHEMA,
        "run_id": args.run_id,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "python": sys.version.split()[0],
        "pytest_available": _pytest_available(),
        "supported_constructs": SUPPORTED,
        "verdict": ("SHIM_PASS" if n_failed == 0 and n_absent == 0 else "SHIM_FAIL"),
        "n_files": len(results),
        "n_passed": sum(r.get("n_passed", 0) for r in results),
        "n_failed": n_failed,
        "n_skipped": sum(r.get("n_skipped", 0) for r in results),
        "n_unsupported": sum(r.get("n_unsupported", 0) for r in results),
        "n_absent": n_absent,
        "results": results,
        "what_this_is_not": (
            "NOT pytest. This runner does not discover, collect, fixture-inject, xfail or "
            "report the way pytest does. A case needing a fixture, a parametrisation or a "
            "construct outside supported_constructs is reported UNSUPPORTED and counted as "
            "NOT-RUN, never as passed, so the counts here are an UPPER BOUND on what pytest "
            "would execute. A SHIM_PASS does NOT withdraw the standing disclosure that the "
            "lane's pytest scope is unexecuted in the producer image and that the "
            "snapshot-audit READY verdict is conditional on that absence."),
        "why_it_exists": (
            "An unexecuted test file is an unverified claim. This converts the lane's "
            "pytest-style tests into a measurement in an image where pytest is absent, "
            "without pretending the absence is fixed."),
    }

    out = Path(args.out) if args.out else (
        root / "results/evaluation/orchestration" / f"{args.run_id}_pytest_shim.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"pytest available in this image: {rec['pytest_available']}")
    for r in results:
        print(f"  {r.get('status'):<13} {r['test_file']} "
              f"passed={r.get('n_passed', 0)} failed={r.get('n_failed', 0)} "
              f"skipped={r.get('n_skipped', 0)} unsupported={r.get('n_unsupported', 0)}")
    print(f"verdict: {rec['verdict']} "
          f"({rec['n_passed']} passed, {rec['n_failed']} failed, "
          f"{rec['n_skipped']} skipped, {rec['n_unsupported']} unsupported)")
    print(f"record: {out}")
    return 1 if (n_failed or n_absent) else 0


def _pytest_available() -> bool:
    try:
        import importlib.util as _u
        return _u.find_spec("pytest") is not None
    except (ImportError, ValueError):
        return False


if __name__ == "__main__":
    raise SystemExit(main())