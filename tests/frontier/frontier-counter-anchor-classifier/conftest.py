"""Shared pytest configuration for the frontier-counter-anchor-classifier tests."""

from __future__ import annotations

import os
import sys

# Make the team package importable without installation.
# conftest.py lives at <repo>/tests/frontier/frontier-counter-anchor-classifier/.
_HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
TEAM_PACKAGE_PARENT = os.path.join(REPO_ROOT, "frontier", "frontier-counter-anchor-classifier")
for _p in (TEAM_PACKAGE_PARENT, REPO_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

#: The accepted product mount (read-only).  The full head-to-head integration
#: test skips gracefully when it is not present.
ACCEPTED_PRODUCT_MOUNT = "/tmp/lex_accepted/core/product"
SERVED_BUNDLES_DIR = os.path.join(
    ACCEPTED_PRODUCT_MOUNT,
    "results/product/gate_packet/38839347028/questions",
)
ACCEPTED_LABEL_HALF = "/tmp/LABEL_HALF.json"
RULES_PATH = os.path.join(
    REPO_ROOT, "results/frontier/frontier-counter-anchor-classifier/RULES_LABEL.json"
)
