#!/usr/bin/env python3
"""Execute/replay the frozen multilingual + counter-intent query texts.

Why this exists
---------------
Core Evaluation run ``39631600439`` measured that the product's cached
retrieval executed only 4 of 24 frozen query texts (``baseline/fr`` per frozen
reality question) and that all 18 comparator-only decision ids came from texts
the product never executed.  Factory direction v62, product ordered item 2,
requires the product to execute (live) or replay (cache-first) the remaining
texts so multilingual and counter-intent recall is no longer bounded by
coverage.

This runner is the product-owned executor for that remediation.  It is NOT a
gate and NOT a benchmark re-derivation:

* it reads the product-owned frozen-text snapshot
  (``product/data/frozen_retrieval_texts.json``), whose ``source_sha256`` pins
  the accepted evaluation benchmark bytes;
* it runs each planned text through the SAME accepted OpenCaseLaw adapter the
  product uses (``build_candidate_bundle``), with the bounded coverage config
  from ``product/query/pipeline.py``;
* ``--mode live`` writes the fetched envelopes into the product cache
  (append-only: existing files are fingerprinted before and after, and any
  modification is reported, never hidden);
* ``--mode offline`` replays from the cache only and reports cache hits/misses;
* for each text it reports which frozen authority/counter ids the returned rows
  contain.  Those counts are REPORTED-ONLY context for Evaluation's next
  independent measurement; no gate is scored here.

Usage::

    python product/coverage_replay.py --mode both --run-id CYCLE_XXXX
    python product/coverage_replay.py --mode offline --run-id CYCLE_XXXX

Writes ``results/product/coverage_replay/<run_id>.json``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PRODUCT_ROOT.parent
for _p in (str(REPO_ROOT), str(PRODUCT_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from product.query.cache_path import product_cache_dir  # noqa: E402
from product.query.pipeline import MIN_LIVE_RESULTS, _coverage_text_config  # noqa: E402
from product.query.query_texts import (  # noqa: E402
    MANIFEST_PATH,
    load_manifest,
    normalize_text,
    plan_query_texts,
)

OUT_DIR = REPO_ROOT / "results" / "product" / "coverage_replay"
SCHEMA = "product-coverage-replay/1"
#: Frozen question texts are the four reality-check questions; the snapshot is
#: the identity anchor, so this list is derived from the manifest, not retyped.
DEFAULT_TOP_N = 120


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _cache_fingerprint(cache_dir: Path) -> dict[str, str]:
    return {
        str(p.relative_to(cache_dir)): _sha256(p)
        for p in sorted(cache_dir.glob("*/*.json"))
    }


def _row_ids(candidates: list[dict]) -> set[str]:
    out: set[str] = set()
    for row in candidates:
        did = str(row.get("decision_id") or "").strip()
        if did:
            out.add(did)
        canon = str(row.get("canonical_decision_id") or "").strip()
        if canon:
            out.add(canon)
    return out


def _reached(frozen_ids: list[str], ids: set[str]) -> list[str]:
    # Identity is exact id membership; no fuzzy match is invented here.
    return sorted(did for did in frozen_ids if did in ids)


def _run_one(mode: str, question: dict, entry: dict, *, top_n: int) -> dict:
    from ocl_adapter import build_candidate_bundle

    cfg = _coverage_text_config(top_n, mode)
    t0 = time.time()
    record: dict = {
        "slug": question.get("slug"),
        "channel": entry.get("channel"),
        "language": entry.get("language"),
        "text": entry.get("text"),
        "mode": mode,
    }
    try:
        bundle = build_candidate_bundle(
            str(entry.get("text") or ""),
            config=cfg,
            hydrate_top=0,
            hydrate_ids=[],
            include_structure=False,
        )
        rows = list(bundle.get("candidates") or [])
        prov = bundle.get("provenance") or {}
        summary = prov.get("request_summary") or {}
        ids = _row_ids(rows)
        record.update({
            "n_candidates": len(rows),
            "network_calls": summary.get("network_calls"),
            "cache_hits": summary.get("cache_hits"),
            "degraded": bool(prov.get("degraded")),
            "failures": prov.get("failures") or [],
            "authority_ids_reached": _reached(question.get("authority_ids") or [], ids),
            "counter_ids_reached": _reached(question.get("known_counter_ids") or [], ids),
            "seconds": round(time.time() - t0, 3),
        })
        record["all_frozen_ids_reached"] = sorted(
            set(record["authority_ids_reached"]) | set(record["counter_ids_reached"])
        )
    except Exception as exc:  # a miss is recorded, never fabricated
        record.update({
            "n_candidates": 0,
            "error": f"{type(exc).__name__}: {exc}",
            "seconds": round(time.time() - t0, 3),
        })
    return record


def run(mode: str, *, top_n: int = DEFAULT_TOP_N) -> dict:
    manifest = load_manifest()
    cache_dir = product_cache_dir()
    before = _cache_fingerprint(cache_dir) if cache_dir.exists() else {}
    results: list[dict] = []
    for question in manifest.get("questions") or []:
        plan = plan_query_texts(
            (question.get("queries") or {}).get("baseline", {}).get("fr", ""),
            manifest=manifest,
        )
        primary_norm = normalize_text(
            (question.get("queries") or {}).get("baseline", {}).get("fr", "")
        )
        for entry in plan:
            record = _run_one(mode, question, entry, top_n=top_n)
            # The primary question text is retained on purpose: Evaluation
            # identity-matches envelopes by text, but the product's OWN cache-
            # first replay is keyed by config shape.  Fetching/replaying the
            # primary text under the coverage config is what lets an offline
            # run of a frozen question rebuild its bundle from the cache.
            record["executed_by_primary_query"] = (
                normalize_text(entry.get("text")) == primary_norm
            )
            results.append(record)
    after = _cache_fingerprint(cache_dir) if cache_dir.exists() else {}
    modified = sorted(
        rel for rel, sha in before.items() if after.get(rel) not in (None, sha)
    )
    added = sorted(rel for rel in after if rel not in before)
    executable = list(results)
    return {
        "schema": SCHEMA,
        "record_type": "PRODUCT_COVERAGE_EXECUTION",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mode": mode,
        "manifest": {
            "path": str(MANIFEST_PATH.relative_to(REPO_ROOT)),
            "sha256": _sha256(MANIFEST_PATH),
            "source_sha256": manifest.get("source_sha256"),
            "source_path": manifest.get("source_path"),
        },
        "cache_dir": str(cache_dir.relative_to(REPO_ROOT)) if cache_dir.is_relative_to(REPO_ROOT) else str(cache_dir),
        "top_n": top_n,
        "n_texts_planned": len(results),
        "n_texts_executed": sum(1 for r in executable if "error" not in r),
        "n_texts_with_rows": sum(1 for r in executable if (r.get("n_candidates") or 0) > 0),
        "n_texts_cache_miss": sum(
            1 for r in executable
            if (r.get("n_candidates") or 0) == 0 and (r.get("cache_hits") or 0) == 0
        ),
        "n_network_calls": sum(int(r.get("network_calls") or 0) for r in executable),
        "n_cache_hits": sum(int(r.get("cache_hits") or 0) for r in executable),
        "n_frozen_ids_reached": len({
            did for r in executable for did in (r.get("all_frozen_ids_reached") or [])
        }),
        "cache": {
            "n_before": len(before),
            "n_after": len(after),
            "n_added": len(added),
            "added": added,
            "n_modified_existing": len(modified),
            "modified_existing": modified,
        },
        "per_text": results,
        "claim_ceiling": (
            "executes/replays the frozen multilingual and counter-intent query "
            "texts through the accepted adapter and reports raw row/id counts; "
            "it scores no frozen gate, re-derives no threshold, classifies no "
            "decision and asserts no serve or human-gate readiness"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", choices=("live", "offline"), default="offline")
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--top-n", type=int, default=DEFAULT_TOP_N)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    run_id = args.run_id or time.strftime("LOCAL_%Y%m%dT%H%M%SZ", time.gmtime())
    record = run(args.mode, top_n=max(MIN_LIVE_RESULTS, args.top_n))
    record["run_id"] = run_id
    out = Path(args.out) if args.out else OUT_DIR / f"{run_id}_{args.mode}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: record[k] for k in (
        "mode", "n_texts_planned", "n_texts_executed", "n_texts_with_rows",
        "n_texts_cache_miss", "n_network_calls", "n_cache_hits",
        "n_frozen_ids_reached", "cache",
    )}, indent=1)[:2000])
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
