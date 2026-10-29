#!/usr/bin/env python3
"""Classify a cycle's committed delta as SUBSTANTIVE or CACHE_ONLY.

Why this exists
---------------
Run 40783679367's TEAM job was fully green and persisted a **25-file**
committed delta over its predecessor — and every one of those 25 files is a
query-cache envelope whose ONLY change is the ``fetched_at`` timestamp.  The
workflow's rc-67 ``LEX_ZERO_DELTA_REPAIR`` guard (and the lane's own
"a cycle that produces only plans/reports/specs is REVISE" rule) both look at
*changed files*, so a live cache warm-up is indistinguishable from real
product work: 25 touched files pass every count-based guard while the product
code, tests, reports and state are byte-identical to the predecessor.

This instrument makes the distinction mechanical and reproducible instead of
prose.  It is deliberately read-only: it never writes the tree, never rewrites
a cache byte, never scores a frozen bar, and asserts nothing about retrieval
quality, a serve verdict or the human gate.

Commands
--------
    python3 product/delta_substance.py --base REV --head REV \
        --out results/product/orchestration/CYCLE_<run>_delta_substance.json
    python3 product/delta_substance.py --run-id <run> \
        --predecessor-ref refs/remotes/origin/cycle/core/product/<prev>/team
    python3 product/delta_substance.py --base REV --head REV --require-substantive

``--require-substantive`` exits 2 unless the delta is SUBSTANTIVE, i.e. it
touches at least one non-cache product path (code, tests, report, state or a
results artifact), so a cycle test or an audit can treat "live cache refresh
only" as zero product work without weakening any count-based guard.

Categories
----------
``cache_timestamp_only``
    ``results/product/query_cache/**/*.json`` whose parsed content is equal
    after removing ``fetched_at`` (and ``fetched_at_iso``) recursively.  These
    are the exact bytes a warm cache rewrites on every re-fetch of an
    unchanged OpenCaseLaw response.
``cache_content``
    A query-cache envelope whose RESPONSE BODY (or any non-timestamp field)
    changed, e.g. an upstream ``citation_count`` drift observed by a live
    re-fetch.  It is published, never hidden, but it is still CACHE-class
    work: it advances no product code, test, report, state or artifact.
``code`` / ``tests`` / ``report`` / ``state`` / ``results_artifact`` / ``other``
    Everything else, by repo-relative path.  Only these count as product work.

``delta_substance``
    ``EMPTY`` (no files), ``CACHE_ONLY`` (timestamp-only cache rewrites),
    ``CACHE_REFRESH`` (cache rewrites with at least one body change) or
    ``SUBSTANTIVE`` (at least one non-cache path).  ``product_work`` is True
    only for SUBSTANTIVE.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

PRODUCT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PRODUCT_ROOT.parent

SCHEMA = "product-delta-substance/1"

#: The frozen claim-cache manifest.  A rewrite of one of these keys is
#: published separately because the manifest exists to make such a rewrite
#: visible, even if the body is unchanged.
MANIFEST_PATH = REPO_ROOT / "results" / "product" / "CYCLE_38759730609_cache_manifest.json"

#: Keys that a cache refresh is allowed to move without changing what the
#: response *says*.  Kept tiny and explicit on purpose.
TIMESTAMP_KEYS = ("fetched_at", "fetched_at_iso")

CACHE_PREFIX = "results/product/query_cache/"


class GitError(RuntimeError):
    """A git invocation failed; the caller should surface it, not guess."""


def _git(*args: str, repo: Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise GitError(
            f"git {' '.join(args)} failed ({proc.returncode}): "
            f"{proc.stderr.strip()[:400]}"
        )
    return proc


def _rev(ref: str, repo: Path = REPO_ROOT) -> str:
    return _git("rev-parse", "--verify", ref, repo=repo).stdout.strip()


def _changed_paths(base: str, head: str,
                   repo: Path = REPO_ROOT) -> list[str]:
    out = _git("diff", "--name-only", base, head, repo=repo).stdout.splitlines()
    return [p for p in out if p]


def _blob(rev: str, path: str, repo: Path = REPO_ROOT) -> bytes | None:
    proc = subprocess.run(
        ["git", "show", f"{rev}:{path}"],
        cwd=repo,
        capture_output=True,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout


def _strip_timestamps(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: _strip_timestamps(v)
            for k, v in value.items()
            if k not in TIMESTAMP_KEYS
        }
    if isinstance(value, list):
        return [_strip_timestamps(v) for v in value]
    return value


def _cache_verdict(base: str, head: str, path: str,
                   repo: Path = REPO_ROOT) -> str:
    """Return ``cache_timestamp_only`` or ``cache_content`` for a cache file."""
    old = _blob(base, path, repo)
    new = _blob(head, path, repo)
    if old is None or new is None:
        # Added/removed cache entry: the response set changed -> content.
        return "cache_content"
    try:
        old_doc = json.loads(old.decode("utf-8"))
        new_doc = json.loads(new.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return "cache_content"
    if _strip_timestamps(old_doc) == _strip_timestamps(new_doc):
        return "cache_timestamp_only"
    return "cache_content"


def _category(base: str, head: str, path: str,
              repo: Path = REPO_ROOT) -> str:
    if path.startswith(CACHE_PREFIX) and path.endswith(".json"):
        return _cache_verdict(base, head, path, repo)
    if path.startswith("product/"):
        return "code"
    if path.startswith("tests/product/") or path.startswith("product/tests/"):
        return "tests"
    if path.startswith("reports/product/"):
        return "report"
    if path == "state/product.json":
        return "state"
    if path.startswith("results/product/"):
        return "results_artifact"
    return "other"


def _manifest_covered(manifest_path: Path = MANIFEST_PATH) -> set[str]:
    if not manifest_path.is_file():
        return set()
    try:
        doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()
    keys = set()
    for entry in doc.get("entries") or []:
        if isinstance(entry, dict):
            keys.add(str(entry.get("path") or ""))
        elif isinstance(entry, str):
            keys.add(entry)
    return {k for k in keys if k}


SUBSTANTIVE_CATEGORIES = (
    "code",
    "tests",
    "report",
    "state",
    "results_artifact",
    "other",
)

CACHE_CATEGORIES = ("cache_timestamp_only", "cache_content")


def classify(base: str, head: str, *, repo_root: Path | None = None,
             manifest_path: Path | None = None) -> dict[str, Any]:
    """Classify every path changed between ``base`` and ``head``.

    ``repo_root``/``manifest_path`` are injectable so the classification
    logic can be exercised on a throwaway git repo without touching the
    product tree.
    """
    repo = Path(repo_root) if repo_root is not None else REPO_ROOT
    manifest = Path(manifest_path) if manifest_path is not None else MANIFEST_PATH
    base_sha = _rev(base, repo)
    head_sha = _rev(head, repo)
    paths = _changed_paths(base_sha, head_sha, repo)
    covered = _manifest_covered(manifest)

    by_category: dict[str, list[str]] = {}
    for path in paths:
        by_category.setdefault(
            _category(base_sha, head_sha, path, repo), []
        ).append(path)

    timestamp_only = sorted(by_category.get("cache_timestamp_only", []))
    cache_content = sorted(by_category.get("cache_content", []))
    substantive = sorted(
        p for cat in SUBSTANTIVE_CATEGORIES for p in by_category.get(cat, [])
    )
    cache_files = len(timestamp_only) + len(cache_content)
    if not paths:
        substance = "EMPTY"
    elif substantive:
        substance = "SUBSTANTIVE"
    elif cache_content:
        substance = "CACHE_REFRESH"
    elif cache_files:
        substance = "CACHE_ONLY"
    else:
        substance = "CACHE_ONLY"

    return {
        "schema": SCHEMA,
        "base": {"ref": base, "sha": base_sha},
        "head": {"ref": head, "sha": head_sha},
        "changed_files": len(paths),
        "counts": {cat: len(v) for cat, v in sorted(by_category.items())},
        "delta_substance": substance,
        "product_work": substance == "SUBSTANTIVE",
        "substantive_files": substantive,
        "cache_timestamp_only": timestamp_only,
        "cache_timestamp_only_count": len(timestamp_only),
        "cache_content": cache_content,
        "cache_content_count": len(cache_content),
        "cache_manifest_covered_rewrites": sorted(
            p for p in paths if p in covered
        ),
        "claim_ceiling": (
            "Read-only classification of a git delta by path and by whether a "
            "query-cache envelope's response body changed. It asserts no "
            "retrieval quality, no frozen-bar result, no serve verdict and no "
            "product usefulness; it does not write the tree."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--base", default=None, help="base git revision")
    ap.add_argument("--head", default=None, help="head git revision")
    ap.add_argument("--run-id", default=None,
                    help="run id; defaults --head to its persisted team ref")
    ap.add_argument("--predecessor-ref", default="",
                    help="predecessor team ref; defaults --base to accepted head")
    ap.add_argument("--predecessor-run-id", default=None,
                    help="convenience: build the predecessor team ref")
    ap.add_argument("--out", default=None, help="optional JSON output path")
    ap.add_argument("--require-substantive", action="store_true",
                    help="exit 2 unless the delta is product work (SUBSTANTIVE)")
    args = ap.parse_args(argv)

    base = args.base
    head = args.head
    if args.run_id and not head:
        head = f"refs/remotes/origin/cycle/core/product/{args.run_id}/team"
    if args.predecessor_run_id and not base:
        base = (
            "refs/remotes/origin/cycle/core/product/"
            f"{args.predecessor_run_id}/team"
        )
    if args.predecessor_ref and not base:
        base = args.predecessor_ref
    if not base:
        base = "refs/remotes/origin/lab/product"
    if not head:
        head = "HEAD"

    try:
        record = classify(base, head)
    except GitError as exc:
        print(f"delta_substance: {exc}", file=sys.stderr)
        return 6

    if args.run_id:
        record["run_id"] = args.run_id
    if args.predecessor_run_id:
        record["predecessor_run_id"] = args.predecessor_run_id
    text = json.dumps(record, indent=2, sort_keys=True)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
        print(f"delta substance -> {args.out}")
    else:
        print(text)
    print(
        "  delta_substance: {substance}  product_work={pw}  changed={n}  "
        "cache_timestamp_only={c}  cache_content={cc}  substantive={s}  "
        "manifest_covered={m}".format(
            substance=record["delta_substance"],
            pw=record["product_work"],
            n=record["changed_files"],
            c=record["cache_timestamp_only_count"],
            cc=record["cache_content_count"],
            s=len(record["substantive_files"]),
            m=len(record["cache_manifest_covered_rewrites"]),
        )
    )
    if args.require_substantive and not record["product_work"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
