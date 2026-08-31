#!/usr/bin/env python3
"""Runner script for corpus lane cycle v14 test suite.

Adds project root to sys.path so imports resolve, then invokes the
v14 comprehensive test suite.

Usage:
    python tests/corpus/run_v14_tests.py
"""
import os
import sys

# Add project root (two levels up from this script) to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Change working directory to project root so relative paths resolve
os.chdir(PROJECT_ROOT)

from corpus.tests.test_cycle_v14 import main

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
