#!/usr/bin/env python3
"""Measure which manifest-covered cache rewrites the recorded live runs own.

Why this exists
---------------
Cycle 39674781875 changed ``product/live_slice.py``'s default cache root to a
throwaway directory, because a ``refresh`` run rewrites the tracked cache IN
PLACE and the tracked cache is covered by a frozen claim-cache manifest
(``results/product/CYCLE_38759730609_cache_manifest.json``).  The reason for
that change is written down in the module docstring and in the comment above
the default - and the independent audit of the cycle found that the written
down number was wrong (audit CYCLE_39674781875, D2):

    claimed:  "cycle 39667945530's two live runs turned 9 more [manifest-covered
               entries]"
    measured: the commit rewrote 9 manifest-covered entries, but the two
              recorded runs' OWN independent probes account for only 7.  Two
              files (``11/11c69a8b...json`` and ``88/88a3a731...json``) were
              rewritten in the same commit with NO probe attribution.

A published attribution that does not reproduce from the committed tree is the
binding defect class of this factory, so the number is now MEASURED by this
tool instead of asserted in prose, and the prose is pinned to this measurement
by ``product/tests/test_cache_rewrite_attribution.py``.

What it measures (and what it does not)
---------------------------------------
* which manifest-covered cache files differ between two named git revisions;
* which of them each named live-slice record's own ``files_modified`` probe
  lists, i.e. which rewrites that record can be said to have caused;
* which rewrites NO named record accounts for (``unattributed``) - they are
  published, never silently folded into a run's count;
* whether the current working tree still matches the frozen manifest.

It asserts nothing about retrieval quality, answer usefulness, any frozen bar,
any Frontier verdict or any human-gate input, it changes no cache byte, no
threshold and no posture field, and it never edits a historical record.

Commands
--------
    python3 product/cache_rewrite_attribution.py --run-id <run> --write
    python3 product/cache_rewrite_attribution.py --check

Exit codes: 0 ok, 1 artifact mismatch (fail-closed), 6 git/manifest problem.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

PRODUCT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PRODUCT_ROOT.parent
for _p in (str(PRODUCT_ROOT), str(REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

SCHEMA = "product-cache-rewrite-attribution/1"

#: The frozen claim-cache manifest that defines "manifest-covered".
MANIFEST_PATH = REPO_ROOT / "results" / "product" / "CYCLE_38759730609_cache_manifest.json"

#: The revision range whose manifest-covered rewrites are attributed.  The base
#: is the accepted tip before the carried cycle; the head is the commit that
#: carried cycle 39667945530's live runs.  Both are named in the artifact with
#: their subjects so a reader can re-derive them.
DEFAULT_BASE = "5cf9098"
DEFAULT_HEAD = "3f94e0e"

#: The live-slice records whose own probes may be credited with a rewrite.
#: Selected by run_id (never by file order) so a renamed file cannot silently
#: change the attribution.
DEFAULT_RECORDS = (
    "results/product/live_slice/CYCLE_39667945530.json",
    "results/product/live_slice/CYCLE_39667945530_FIX1.json",
)

#: Where the run-named artifact of record is written.
OUT_DIR = REPO_ROOT / "results" / "product" / "cache_attribution"
ARTIFACT = OUT_DIR / "CYCLE_39674781875_manifest_rewrite_attribution.json"

CACHE_PREFIX = "results/product/query_cache/"


class MeasurementError(RuntimeError):
    """A measurement that could not be taken - never a silent zero."""


def _git(*args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=str(REPO_ROOT),
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise MeasurementError(
            f"git {' '.join(args)} failed ({proc.returncode}): "
            f"{(proc.stderr or '').strip()[:400]}")
    return proc.stdout


def manifest_entries() -> dict[str, str]:
    """``{repo-relative path: frozen sha256}`` for the frozen claim cache."""
    if not MANIFEST_PATH.is_file():
        raise MeasurementError(f"missing frozen cache manifest: {MANIFEST_PATH}")
    raw = MANIFEST_PATH.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    entries = payload.get("entries")
    if not isinstance(entries, list) or not entries:
        raise MeasurementError("the frozen cache manifest carries no entries")
    out: dict[str, str] = {}
    for entry in entries:
        try:
            out[str(entry["path"])] = str(entry["sha256"])
        except (KeyError, TypeError) as exc:
            raise MeasurementError(f"malformed manifest entry: {entry!r}") from exc
    return out


def blob_sha(rev: str, path: str) -> str | None:
    """The sha256 of ``path`` at ``rev``, or ``None`` when the path is absent."""
    proc = subprocess.run(["git", "show", f"{rev}:{path}"], cwd=str(REPO_ROOT),
                          capture_output=True)
    if proc.returncode != 0:
        return None
    return hashlib.sha256(proc.stdout).hexdigest()


def manifest_covered_rewritten(base: str, head: str,
                               entries: dict[str, str]) -> list[str]:
    """Manifest-covered files whose bytes differ between ``base`` and ``head``."""
    rewritten: list[str] = []
    for path, frozen in sorted(entries.items()):
        before = blob_sha(base, path)
        after = blob_sha(head, path)
        if before is None or after is None:
            raise MeasurementError(
                f"cannot read {path} at {base}/{head}; the attribution needs the "
                "full history, not a shallow clone")
        if before != after:
            rewritten.append(path)
    return rewritten


def record_probes(record_paths: list[str]) -> dict[str, list[str]]:
    """``{run_id: [manifest-covered paths the record's own probe lists]}``.

    Only a file the record's own ``freshness.independent_cache_probe`` names is
    credited to that record.  A rewrite nobody's probe lists stays
    ``unattributed`` - it is never folded into the nearest run's count.
    """
    out: dict[str, list[str]] = {}
    for rel in record_paths:
        path = REPO_ROOT / rel
        if not path.is_file():
            raise MeasurementError(f"missing live-slice record: {rel}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        run_id = str(payload.get("run_id") or rel)
        probe = ((payload.get("freshness") or {})
                 .get("independent_cache_probe") or {})
        modified = probe.get("files_modified") or []
        if not isinstance(modified, list):
            raise MeasurementError(f"{rel}: files_modified is not a list")
        out[run_id] = sorted({f"{CACHE_PREFIX}{m}" for m in modified})
    return out


def attribute(rewritten: list[str],
              probes: dict[str, list[str]]) -> dict[str, Any]:
    """Split the rewrites into attributed / unattributed.

    ``distinct_attributed`` is the union over the records; a file listed by two
    records is still ONE file, which is why the union is computed over sets and
    not by adding per-record counts.
    """
    rewritten_set = set(rewritten)
    per_record = {
        run_id: sorted(set(paths) & rewritten_set)
        for run_id, paths in sorted(probes.items())
    }
    union: set[str] = set()
    for paths in per_record.values():
        union |= set(paths)
    unattributed = sorted(rewritten_set - union)
    return {
        "per_record": per_record,
        "distinct_attributed": sorted(union),
        "unattributed": unattributed,
        "counts": {
            "manifest_covered_rewritten": len(rewritten_set),
            "distinct_attributed": len(union),
            "unattributed": len(unattributed),
        },
    }


def current_tree_integrity(entries: dict[str, str]) -> dict[str, Any]:
    """How many frozen manifest entries the working tree still matches."""
    mismatches: list[str] = []
    missing: list[str] = []
    for path, frozen in sorted(entries.items()):
        abs_path = REPO_ROOT / path
        if not abs_path.is_file():
            missing.append(path)
            continue
        digest = hashlib.sha256(abs_path.read_bytes()).hexdigest()
        if digest != frozen:
            mismatches.append(path)
    return {
        "n_entries": len(entries),
        "n_missing": len(missing),
        "n_mismatch": len(mismatches),
        "missing": missing,
        "mismatched": mismatches,
        "intact": not missing and not mismatches,
    }


#: Length of the abbreviated commit sha this module publishes.
#:
#: ``git log --format=%h`` is NOT a fixed width: git auto-scales the
#: abbreviation to the repository's size, so the same commit renders as
#: ``3f94e0e`` on one git build and ``3f94e0e8c`` on another.  That made the
#: committed attribution artifact of run 39674781875 FAIL to reproduce from the
#: committed tree on a git build with a different auto-abbreviation length -
#: the binding defect class of this factory ("a published claim does not
#: reproduce from the committed tree").  The abbreviation is therefore pinned
#: to a fixed width.  The published artifact shape is deliberately UNCHANGED:
#: the committed artifact must reproduce byte-for-byte, so the rule is stated
#: here and in product/tests/test_cache_rewrite_attribution.py, not added to
#: the artifact.
SHORT_SHA_LENGTH = 7


def short_sha(rev: str) -> str:
    """A FIXED-WIDTH abbreviated sha. Never ``%h``: that width is git's choice."""
    out = _git("rev-parse", "--short=%d" % SHORT_SHA_LENGTH, rev).strip()
    return out or rev


def commit_subject(rev: str) -> str:
    """``<short-sha> <subject>``, with the short sha pinned to a fixed width."""
    try:
        subject = _git("log", "-1", "--format=%s", rev).strip()
        return f"{short_sha(rev)} {subject}".strip()
    except MeasurementError:
        return rev


def measure(base: str = DEFAULT_BASE, head: str = DEFAULT_HEAD,
            records: list[str] | None = None) -> dict[str, Any]:
    """The full measurement, as a JSON-ready dict."""
    records = list(records or DEFAULT_RECORDS)
    entries = manifest_entries()
    rewritten = manifest_covered_rewritten(base, head, entries)
    probes = record_probes(records)
    attr = attribute(rewritten, probes)
    union = set(attr["distinct_attributed"])
    unattributed = set(attr["unattributed"])
    if union & unattributed:
        raise MeasurementError(
            "attribution overlap: a file is both attributed and unattributed")
    if union | unattributed != set(rewritten):
        raise MeasurementError(
            "attribution does not partition the rewritten set")
    manifest_raw = MANIFEST_PATH.read_bytes()
    return {
        "schema": SCHEMA,
        "claim_ceiling": (
            "MEASURED ATTRIBUTION OF FROZEN-CACHE REWRITES ONLY. It says which "
            "manifest-covered cache files differ between two named git "
            "revisions and which recorded live-slice probe lists each of them. "
            "It is not a bar score, not an audit verdict, not a legal claim and "
            "not a human-gate input; it changes no cache byte and no posture "
            "field."),
        "manifest": {
            "path": "results/product/CYCLE_38759730609_cache_manifest.json",
            "sha256": hashlib.sha256(manifest_raw).hexdigest(),
            "n_entries": len(entries),
        },
        "range": {
            "base": base,
            "base_subject": commit_subject(base),
            "head": head,
            "head_subject": commit_subject(head),
        },
        "records": records,
        "manifest_covered_rewritten": rewritten,
        "attribution": attr,
        "current_tree": current_tree_integrity(entries),
    }


def artifact_payload(run_id: str) -> dict[str, Any]:
    payload = measure()
    # The run id is an integer where it can be one, like every other run-named
    # product artifact (a reader must not have to know whether a field is a
    # string or a number).
    payload["run_id"] = int(run_id) if str(run_id).isdigit() else run_id
    payload["tool"] = "product/cache_rewrite_attribution.py"
    payload["re_derive"] = (
        "python3 product/cache_rewrite_attribution.py --check "
        f"(recomputes from git revs {DEFAULT_BASE}..{DEFAULT_HEAD} and the "
        "frozen manifest; no cached value is read)")
    return payload


def _canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run-id", default="39674781875")
    ap.add_argument("--write", action="store_true",
                    help="write the run-named artifact of record")
    ap.add_argument("--check", action="store_true",
                    help="re-derive and compare against the committed artifact")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    try:
        payload = artifact_payload(args.run_id)
    except MeasurementError as exc:
        print(f"[FAIL] the attribution could not be measured: {exc}",
              file=sys.stderr)
        return 6

    if args.write:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        target = OUT_DIR / f"CYCLE_{args.run_id}_manifest_rewrite_attribution.json"
        target.write_text(_canonical(payload), encoding="utf-8")
        print(f"[ok] wrote {target.relative_to(REPO_ROOT)}")

    if args.check:
        if not ARTIFACT.is_file():
            print(f"[FAIL] missing committed artifact: {ARTIFACT}", file=sys.stderr)
            return 1
        committed = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        fresh = json.loads(_canonical(payload))
        if committed != fresh:
            print("[FAIL] the committed attribution artifact does not match a "
                  "fresh measurement - re-run with --write and record why",
                  file=sys.stderr)
            if args.json:
                print(json.dumps({"committed": committed, "fresh": fresh},
                                 indent=2, sort_keys=True))
            return 1
        print(f"[ok] committed artifact matches a fresh measurement: "
              f"{ARTIFACT.relative_to(REPO_ROOT)}")

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        counts = payload["attribution"]["counts"]
        print(f"manifest-covered rewritten : {counts['manifest_covered_rewritten']}")
        print(f"attributed to the probes   : {counts['distinct_attributed']}")
        print(f"unattributed               : {counts['unattributed']}")
        for path in payload["attribution"]["unattributed"]:
            print(f"  unattributed: {path}")
        tree = payload["current_tree"]
        print(f"frozen manifest intact     : {tree['intact']} "
              f"({tree['n_entries'] - tree['n_mismatch'] - tree['n_missing']}"
              f"/{tree['n_entries']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
