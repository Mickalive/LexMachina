#!/usr/bin/env python3
"""Measure a query-cache pre-warm: what a commit range added, and (optionally)
re-verify those envelopes against the live OpenCaseLaw API.

Why this exists
---------------
Run 39389625385 (repair 0) pre-warmed 35 content-addressed OpenCaseLaw envelopes
for the German rent question into ``results/product/query_cache``. The run wrote
no report of record and no machine-readable measurement, so the independent audit
had to re-derive the before/after counts and re-fetch the live API from the commit
message alone (audit D2). This instrument makes the run's own coverage claim
reproducible from the committed bytes: it enumerates the envelopes a commit range
added, partitions them by upstream API path, and - when ``--verify-live`` is given
- re-fetches each envelope's ``url`` and compares the response body byte-for-byte.

It is deliberately stdlib-only so it is runnable in the bare lane environment
without the dense stack.

Usage::

    python3 product/query_cache_prewarm.py --base fc908bd --head 5fa0105 \
        --run-id 39389625385 \
        --out results/product/regression/CYCLE_39389625385_query_cache_prewarm.json

    python3 product/query_cache_prewarm.py --base fc908bd --head 5fa0105 \
        --run-id 39389625385 --verify-live \
        --out results/product/regression/CYCLE_39389625385_query_cache_prewarm.json

The artifact is a coverage measurement, not an audit verdict: it scores no frozen
bar and makes no legal-usefulness claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE_REL = "results/product/query_cache"
CACHE_DIR = ROOT / CACHE_REL

SCHEMA = "product-query-cache-prewarm/1"


def _git(*args: str) -> str:
    out = subprocess.run(  # noqa: S603 - fixed argv, no shell
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True,
    )
    return out.stdout


def _added_files(base: str, head: str) -> list[str]:
    """Paths added under the product cache root between ``base`` and ``head``."""
    out = _git("diff", "--name-only", "--diff-filter=A", base, head, "--", CACHE_REL)
    return [line.strip() for line in out.splitlines() if line.strip()]


def _total_at(commit: str) -> int:
    out = _git("ls-tree", "-r", "--name-only", commit, "--", CACHE_REL)
    return sum(1 for line in out.splitlines() if line.strip())


def _category(path: str) -> str:
    if path.startswith("/structure/"):
        return "structure"
    if path.startswith("/citations/"):
        return "citations"
    if path.startswith("/leading-cases"):
        return "leading_cases"
    if path.startswith("/decisions/"):
        return "decision_full_text"
    if path == "/decisions":
        return "decisions_search"
    return "other"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_envelope(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _fetch(url: str, timeout: float) -> tuple[int, str | None, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "lexmachina-prewarm/1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - product-owned source
            return resp.status, resp.read().decode("utf-8", "replace"), ""
    except urllib.error.HTTPError as exc:
        return exc.code, None, f"HTTPError {exc.code}"
    except Exception as exc:  # noqa: BLE001 - recorded, never silently skipped
        return 0, None, f"{type(exc).__name__}: {exc}"


def measure(base: str, head: str, *, verify_live: bool = False,
            timeout: float = 20.0) -> dict:
    added = _added_files(base, head)
    n_before = _total_at(base)
    n_after = _total_at(head)
    partition: dict[str, int] = {}
    entries: list[dict] = []
    for rel in added:
        env = _read_envelope(rel)
        path = str(env.get("path") or "")
        category = _category(path)
        partition[category] = partition.get(category, 0) + 1
        row = {
            "file": rel,
            "sha256": _sha256(ROOT / rel),
            "api_path": path,
            "category": category,
            "status": env.get("status"),
            "cache_version": env.get("cache_version"),
            "key_consistent": env.get("key") == rel.rsplit("/", 1)[-1][:-5],
        }
        if verify_live:
            status, body, err = _fetch(str(env.get("url") or ""), timeout)
            row["live_http_status"] = status
            row["live_error"] = err or None
            cached_body = env.get("body")
            row["live_byte_identical"] = (
                body is not None and cached_body is not None and body == cached_body
            )
        entries.append(row)

    identical = sum(1 for e in entries if e.get("live_byte_identical") is True)
    return {
        "schema": SCHEMA,
        "base_commit": base,
        "head_commit": head,
        "cache_root": CACHE_REL,
        "n_cache_before": n_before,
        "n_cache_after": n_after,
        "n_added": len(added),
        "partition_by_api_path": dict(sorted(partition.items())),
        "live_verification": {
            "requested": verify_live,
            "n_byte_identical": identical if verify_live else None,
            "n_drifted": (len(entries) - identical) if verify_live else None,
            "n_unreachable": (
                sum(1 for e in entries if e.get("live_http_status") == 0) if verify_live else None
            ),
            "note": (
                "live GETs to the envelope's own url; a drifted response is "
                "recorded as drift, never overwritten. A /decisions search page "
                "naturally drifts in ranking/order over time while covering ~the "
                "same decision-ID set."
            ),
        },
        "entries": entries,
        "claim_ceiling": (
            "A coverage measurement of the product's own committed query cache and, "
            "when --verify-live is given, a live re-fetch of the recorded envelopes. "
            "It is not an audit verdict, scores no frozen bar, reads no Frontier "
            "verdict, and asserts nothing about legal usefulness or answer quality."
        ),
        "environment": {
            "python": sys.version.split()[0],
            "measured_at_unix": time.time(),
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", required=True)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--verify-live", action="store_true")
    ap.add_argument("--timeout", type=float, default=20.0)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    payload = measure(args.base, args.head, verify_live=args.verify_live,
                      timeout=args.timeout)
    if args.run_id:
        payload["run_id"] = int(args.run_id)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    live = payload["live_verification"]
    print(f"added={payload['n_added']} before={payload['n_cache_before']} "
          f"after={payload['n_cache_after']} partition={payload['partition_by_api_path']}")
    if args.verify_live:
        print(f"live: byte_identical={live['n_byte_identical']} "
              f"drifted={live['n_drifted']} unreachable={live['n_unreachable']}")
    print(f"wrote {out} sha256 {hashlib.sha256(out.read_bytes()).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
