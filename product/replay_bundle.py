#!/usr/bin/env python3
"""Deterministic offline replay of a recorded query into a query_result_bundle.

Product-lane tool introduced by run 38766812030 (operational resume of
38763217418) to make `results/product/CYCLE_<run>_bundle.json` artifacts
reproducible by one command and to refuse synthetic fixture content on the
claim path (see reports/product/CYCLE_38759730609.md incident section).

Usage:
    python product/replay_bundle.py --query "<recorded query>" \
        --top-n 120 --out results/product/CYCLE_<run>_bundle.json

Exit codes:
    0  replay written/verified, bundle is genuine OpenCaseLaw-sourced data
    2  bad arguments
    3  bundle failed validate_bundle
    4  synthetic/fabricated content detected (ids or cluster labels)
    5  required claim fields missing (decision_id, citation, canonical_url,
       source_url, x, y, cluster_id, is_outlier)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import urllib.parse
from collections import Counter
from pathlib import Path

from product.query.bundle import validate_bundle
from product.query.pipeline import run_query_initial

REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_DECISION_FIELDS = (
    "decision_id",
    "citation",
    "canonical_url",
    "x",
    "y",
    "cluster_id",
)

# Field must exist on every decision (value may be null: OpenCaseLaw does not
# return a source_url for every citation-channel record, but the key is part of
# the query_result_bundle contract demanded by the cycle-38759730609 audit).
REQUIRED_DECISION_KEYS = (
    "is_outlier",
    "source_url",
)


def _looks_synthetic(decision_id: str) -> bool:
    """Detect the bge_BGE_test_0000_2024-style ids found in the retired bundle."""
    did = str(decision_id or "").lower()
    return "test_" in did and any(ch.isdigit() for ch in did)


def inspect_bundle(bundle: dict) -> dict:
    """Return the machine-readable inspection used by the CLI and the tests."""
    decisions = bundle.get("decisions") or []
    clusters = bundle.get("clusters") or []
    prov = bundle.get("provenance") or {}
    retrieval = prov.get("retrieval") or {}
    remote = retrieval.get("remote") or {}
    request_summary = remote.get("request_summary") or prov.get("request_summary") or {}
    dedupe = retrieval.get("dedupe") or {}
    timing = prov.get("timing") or {}

    synthetic_ids = [d.get("decision_id") for d in decisions if _looks_synthetic(d.get("decision_id"))]
    synthetic_labels = [
        c.get("label") for c in clusters if "test decision group" in str(c.get("label") or "").lower()
    ]
    missing_fields = []
    for i, d in enumerate(decisions):
        for f in REQUIRED_DECISION_FIELDS:
            if f not in d or d.get(f) is None or d.get(f) == "":
                missing_fields.append(f"decisions[{i}].{f}")
        for f in REQUIRED_DECISION_KEYS:
            if f not in d:
                missing_fields.append(f"decisions[{i}].{f} (key absent)")
        for f in ("x", "y"):
            if isinstance(d.get(f), float) and not math.isfinite(d[f]):
                missing_fields.append(f"decisions[{i}].{f} (non-finite)")
    decision_ids = {d.get("decision_id") for d in decisions}
    orphan_members = [
        c.get("cluster_id")
        for c in clusters
        for m in (c.get("member_ids") or [])
        if m not in decision_ids
    ]
    hosts = Counter(urllib.parse.urlparse(str(d.get("canonical_url") or "")).netloc for d in decisions)
    languages = Counter(str(d.get("language")) for d in decisions)

    return {
        "n_decisions": len(decisions),
        "n_clusters": len(clusters),
        "n_relations": len(bundle.get("relations") or []),
        "n_outliers": sum(1 for d in decisions if d.get("is_outlier") is True),
        "languages": dict(sorted(languages.items())),
        "hosts": dict(sorted(hosts.items())),
        "synthetic_decision_ids": synthetic_ids,
        "synthetic_cluster_labels": synthetic_labels,
        "missing_required_fields": missing_fields,
        "orphan_cluster_member_ids": orphan_members,
        "validate_bundle_errors": validate_bundle(bundle),
        "n_candidates": retrieval.get("n_candidates"),
        "dedupe": dedupe,
        "degraded": bool(prov.get("degraded")) if "degraded" in prov else None,
        "request_summary": request_summary,
        "targets": prov.get("targets"),
        "stages": prov.get("stages"),
        "base_url": prov.get("base_url") or remote.get("base_url"),
        "query_variants": [
            (
                {
                    "variant_id": v.get("variant_id"),
                    "kind": v.get("kind"),
                    "language_filter": v.get("language_filter"),
                    "text": v.get("text"),
                }
                if isinstance(v, dict)
                else {"text": str(v)}
            )
            for v in (prov.get("query_variants") or bundle.get("query_variants") or [])
        ],
        "searches": [
            {
                "stage": s.get("stage"),
                "variant_id": s.get("variant_id"),
                "language_filter": s.get("language_filter"),
                "page": s.get("page"),
                "limit": s.get("limit"),
                "offset": s.get("offset"),
                "returned": s.get("returned"),
                "total": s.get("total"),
            }
            for s in (prov.get("searches") or [])
        ],
        "stage_notes": prov.get("stage_notes"),
        "timing": timing,
        "latency_seconds": prov.get("latency_seconds"),
        "answer_status": (bundle.get("answer") or {}).get("status"),
        "answer_method": (bundle.get("answer") or {}).get("method"),
        "cache_root": (prov.get("cache_stats") or {}).get("root"),
        "cache_keys": (prov.get("cache_stats") or {}).get("n_keys"),
    }


def genuine(insp: dict) -> bool:
    return not (
        insp["synthetic_decision_ids"]
        or insp["synthetic_cluster_labels"]
        or insp["missing_required_fields"]
        or insp["orphan_cluster_member_ids"]
        or insp["validate_bundle_errors"]
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--query", required=True, help="recorded research query")
    ap.add_argument("--top-n", type=int, default=120)
    ap.add_argument("--out", default=None, help="write the replayed bundle here")
    ap.add_argument("--retrieval-mode", default="offline", choices=["offline", "live"])
    args = ap.parse_args(argv)

    bundle = run_query_initial(args.query, top_n=args.top_n, retrieval_mode=args.retrieval_mode)
    insp = inspect_bundle(bundle)

    if insp["validate_bundle_errors"]:
        print(json.dumps({"error": "validate_bundle_failed", "errors": insp["validate_bundle_errors"]}, indent=2))
        return 3
    if insp["synthetic_decision_ids"] or insp["synthetic_cluster_labels"]:
        print(json.dumps({"error": "synthetic_content_refused", "inspection": insp}, indent=2))
        return 4
    if insp["missing_required_fields"]:
        print(json.dumps({"error": "missing_claim_fields", "missing": insp["missing_required_fields"][:20]}, indent=2))
        return 5

    out_path = Path(args.out) if args.out else None
    if out_path is not None:
        if not out_path.is_absolute():
            out_path = REPO_ROOT / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(bundle, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
        out_path.write_text(payload, encoding="utf-8")
        insp["out"] = str(out_path.relative_to(REPO_ROOT))
        insp["out_sha256"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        insp["out_bytes"] = len(payload.encode("utf-8"))
    insp["genuine"] = genuine(insp)
    print(json.dumps(insp, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
