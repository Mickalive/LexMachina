"""Shared fixtures for the frontier-rebuilt-packet-serve-audit acceptance tests.

These tests cover the 12 categories of charter acceptance test 7 (26 test
functions across four test_*.py modules). Everything here is deterministic and
offline: no network, no sleeps, no unseeded randomness, no clock dependence.
Synthetic bundles are built inline from fixed literals; the only subprocess is a
read-only ``git log`` guarded by its own skipif.

The real rebuilt packet (``/tmp/lex_work/results/product/gate_packet/
rebuilt-39027045675``) may be absent in other environments, so every test that
needs real bytes carries an explicit ``needs_real_packet`` /
``needs_old_packet`` skipif marker and never silently degrades to a synthetic
stand-in.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
TEAM_ROOT = REPO_ROOT / "frontier" / "frontier-rebuilt-packet-serve-audit"
if str(TEAM_ROOT) not in sys.path:
    sys.path.insert(0, str(TEAM_ROOT))

from frontier_rebuilt_packet_serve_audit import paths as harness_paths  # noqa: E402

TEAM_ID = "frontier-rebuilt-packet-serve-audit"
QIDS = tuple(harness_paths.QIDS)
RULES_PATH = REPO_ROOT / "results" / "frontier" / TEAM_ID / "RULES.json"
TEAM_RESULTS_DIR = REPO_ROOT / "results" / "frontier" / TEAM_ID
VENDORED_BARS = TEAM_ROOT / "vendored_accepted" / "evaluation" / "frozen_bars"

# RULES.json write_scope_prohibitions: the five namespaces this team may never
# write, relative to the repository root.
FORBIDDEN_WRITE_PREFIXES = (
    "product/",
    "evaluation/",
    "results/product/",
    "state/product.json",
    ".github/",
)

# Claim-bearing and byte-identical inputs a measurement run must also leave
# alone: the frozen rules and the vendored ACCEPTED instruments. (Artefacts the
# team itself owns -- AUDIT_RECORD.json, its report and its state file -- are
# deliberately NOT in this tuple: another writer may legitimately refresh them,
# and a snapshot across a run would be a race, not evidence.)
GUARDED_REPO_PATHS = FORBIDDEN_WRITE_PREFIXES + (
    f"results/frontier/{TEAM_ID}/RULES.json",
    "frontier/frontier-rebuilt-packet-serve-audit/vendored_accepted",
)

# Directories never snapshotted (VCS internals and interpreter caches).
SNAPSHOT_IGNORED_DIRS = frozenset({".git", "__pycache__", ".pytest_cache"})


def _first_packet(candidates) -> Path | None:
    for candidate in candidates:
        p = Path(candidate)
        if (p / "packet.json").is_file():
            return p
    return None


REAL_PACKET_DIR = _first_packet(harness_paths.DEFAULT_PACKET_CANDIDATES)
OLD_PACKET_DIR = _first_packet(harness_paths.DEFAULT_OLD_PACKET_CANDIDATES)

needs_real_packet = pytest.mark.skipif(
    REAL_PACKET_DIR is None,
    reason=(
        "real rebuilt packet rebuilt-39027045675 (packet.json sha256 2942c3c2...) is "
        f"not mounted; searched {[str(c) for c in harness_paths.DEFAULT_PACKET_CANDIDATES]}"
    ),
)
needs_old_packet = pytest.mark.skipif(
    OLD_PACKET_DIR is None,
    reason=(
        "old (before/after) packet 38839347028 is not mounted; searched "
        f"{[str(c) for c in harness_paths.DEFAULT_OLD_PACKET_CANDIDATES]}"
    ),
)


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot_tree(root: str | Path) -> dict:
    """{relpath: (mtime_ns, sha256)} for every regular file under ``root``."""
    root = Path(root)
    out: dict = {}
    if not root.exists():
        return out
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SNAPSHOT_IGNORED_DIRS)
        for name in sorted(filenames):
            p = Path(dirpath) / name
            try:
                out[str(p.relative_to(root))] = (p.stat().st_mtime_ns, sha256_file(p))
            except OSError:  # pragma: no cover - vanished mid-walk
                out[str(p.relative_to(root))] = ("unreadable", None)
    return out


def snapshot_repo_paths(rel_paths) -> dict:
    """Snapshot repository-relative paths; absent paths are recorded as None.

    Recording absence matters: a run that CREATES ``product/`` or
    ``state/product.json`` is as much a write-scope violation as one that edits
    an existing file.
    """
    out: dict = {}
    for rel in rel_paths:
        p = REPO_ROOT / rel
        if p.is_dir():
            out[rel] = snapshot_tree(p)
        elif p.is_file():
            out[rel] = {rel: (p.stat().st_mtime_ns, sha256_file(p))}
        else:
            out[rel] = None
    return out


def load_rules() -> dict:
    return json.loads(RULES_PATH.read_bytes().decode("utf-8"))


@pytest.fixture
def write_bundle():
    """Write ``<qid>.bundle.json`` (synthetic, fixed literals only) and return it."""
    def _write(questions_dir, qid: str, decisions, **extra) -> Path:
        directory = Path(questions_dir)
        directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "qid": qid,
            "bundle_version": "synthetic-acceptance-test",
            "decisions": decisions,
        }
        payload.update(extra)
        path = directory / f"{qid}.bundle.json"
        path.write_text(
            json.dumps(payload, sort_keys=True, ensure_ascii=False), encoding="utf-8"
        )
        return path
    return _write