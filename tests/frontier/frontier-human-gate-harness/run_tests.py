#!/usr/bin/env python3
"""Offline test runner for frontier-human-gate-harness (no third-party deps).

    python tests/frontier/frontier-human-gate-harness/run_tests.py
    python tests/frontier/frontier-human-gate-harness/run_tests.py -k capture

Exit code 0 = every test passed (skips are allowed and reported), 1 = failures.

The same test modules also run under pytest when pytest is installed:
    python -m pytest tests/frontier/frontier-human-gate-harness
"""
from __future__ import annotations

import argparse
import importlib
import sys
import traceback
from pathlib import Path
from unittest import SkipTest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import _bootstrap  # noqa: E402,F401  (puts the harness package on sys.path)

MODULES = ["test_fixture_provenance", "test_owner_card", "test_baseline_view",
           "test_switch", "test_capture", "test_cli"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-k", "--filter", default="", help="substring filter on test names")
    parser.add_argument("-q", "--quiet", action="store_true")
    args = parser.parse_args(argv)

    passed: list[str] = []
    failed: list[tuple[str, str]] = []
    skipped: list[tuple[str, str]] = []

    for module_name in MODULES:
        try:
            module = importlib.import_module(module_name)
        except Exception:
            failed.append((module_name, traceback.format_exc()))
            continue
        names = [n for n in sorted(dir(module)) if n.startswith("test_")]
        for name in names:
            full = f"{module_name}.{name}"
            if args.filter and args.filter not in full:
                continue
            func = getattr(module, name)
            if not callable(func):
                continue
            try:
                func()
            except SkipTest as exc:
                skipped.append((full, str(exc)))
                if not args.quiet:
                    print(f"SKIP {full}: {exc}")
            except Exception:
                failed.append((full, traceback.format_exc()))
                print(f"FAIL {full}")
            else:
                passed.append(full)
                if not args.quiet:
                    print(f"ok   {full}")

    print()
    print(f"passed={len(passed)} failed={len(failed)} skipped={len(skipped)} "
          f"total={len(passed) + len(failed) + len(skipped)}")
    for name, tb in failed:
        print(f"\n--- {name} ---\n{tb}")
    for name, reason in skipped:
        print(f"skip {name}: {reason}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
