#!/usr/bin/env python3
"""Build a product-shaped ``query_result_bundle`` from live OpenCaseLaw.

Purpose (charter acceptance 5 + 6): exercise the source-validation path
against **real** OpenCaseLaw decision IDs, so live attestation can actually
verify something (the synthetic ``CH-…`` fixture ids legitimately cannot be
verified against the corpus).

Usage::

    python3 frontier/frontier-generative-audit/build_ocl_fixture.py \
        --query "Konkurrenzklausel Kündigung Karenzentschädigung" \
        --limit 6 \
        --out tests/frontier/frontier-generative-audit/fixtures/real_ocl_bundle.json

The resulting bundle is a cached artifact (frozen at build time) and is
consumed by ``run_e2e.py --real --bundle … --attestation`` exactly like any
retrieval-lane bundle.  Coordinates are deterministic rank placeholders, not
a similarity map — mapping belongs to the product/map lane.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

DEFAULT_BASE = "https://mcp.opencaselaw.ch/api"
LANG_BY_COURT = {"bger": "de", "bge": "de"}


def _get(url: str, timeout: float) -> Any:
    req = urllib.request.Request(
        url, headers={"User-Agent": "LexMachina-GenAudit-fixture", "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def search(base: str, query: str, limit: int, timeout: float) -> List[Dict[str, Any]]:
    url = (
        f"{base}/decisions?query={urllib.parse.quote(query)}"
        f"&limit={limit}&full_text=false"
    )
    body = _get(url, timeout)
    return list(body.get("results") or [])[:limit]


def fetch_decision(base: str, decision_id: str, timeout: float) -> Dict[str, Any]:
    return _get(
        f"{base}/decisions/{urllib.parse.quote(decision_id)}?full_text=true", timeout
    )


def _snippet(decision: Dict[str, Any], max_chars: int = 1200) -> str:
    for key in ("full_text", "regeste", "abstract_de", "abstract_fr", "abstract_it"):
        value = decision.get(key)
        if isinstance(value, str) and value.strip():
            return " ".join(value.split())[:max_chars]
    return " ".join(str(decision.get("title") or "").split())[:max_chars]


def _citation(decision: Dict[str, Any]) -> str:
    for key in ("citation_string_de", "citation_string_fr", "citation_string_it"):
        if decision.get(key):
            return str(decision[key])
    return str(decision.get("docket_number") or decision.get("decision_id") or "")


def _canonical_url(decision: Dict[str, Any], base: str) -> str:
    if decision.get("canonical_url"):
        return str(decision["canonical_url"])
    host = base.split("/api")[0]
    return f"{host}/entscheid/{decision.get('decision_id')}"


def build_bundle(base: str, query: str, limit: int, timeout: float) -> Dict[str, Any]:
    hits = search(base, query, limit, timeout)
    decisions: List[Dict[str, Any]] = []
    for rank, hit in enumerate(hits, start=1):
        did = hit.get("decision_id")
        if not did:
            continue
        full = fetch_decision(base, did, timeout)
        decisions.append(
            {
                "decision_id": did,
                "court": full.get("court") or hit.get("court") or "bger",
                "language": full.get("language") or hit.get("language") or "de",
                "rank": rank,
                "score": round(1.0 - (rank - 1) * 0.05, 4),
                "provenance": {
                    "source": "opencaselaw-public-api",
                    "endpoint": f"{base}/decisions/{did}",
                    "decision_date": full.get("decision_date"),
                    "docket_number": full.get("docket_number"),
                    "content_hash": full.get("content_hash"),
                    "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                },
                "snippet": _snippet(full),
                "cluster_id": "ocl-1",
                # Deterministic placeholder coordinates (map lane owns layout).
                "x": round(0.1 * rank, 4),
                "y": round((rank % 3) * 0.25, 4),
                "counter_status": "none",
                "canonical_url": _canonical_url(full, base),
                "citation": _citation(full),
                "citations": list(full.get("cited_decisions") or [])[:10],
            }
        )

    return {
        "bundle_version": "1.0",
        "query": query,
        "query_variants": [query],
        "answer": {
            "prose": "",
            "statements": [],
            "cited_decision_ids": [],
            "method": "pending_generative_audit",
            "model": "none",
        },
        "decisions": decisions,
        "clusters": [
            {"cluster_id": "ocl-1", "label": f"OpenCaseLaw results: {query}",
             "decision_ids": [d["decision_id"] for d in decisions]}
        ],
        "relations": [],
        "provenance": {
            "corpus": {"source": "opencaselaw-public-api", "base": base, "n": len(decisions)},
            "query": query,
            "answer_method": "pending_generative_audit",
            "counter": {"method": "pending_generative_audit"},
            "bundle": "query_result_bundle v1.0",
            "coordinates": "deterministic rank placeholders — not a similarity map",
            "built_by": "frontier/frontier-generative-audit/build_ocl_fixture.py",
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--query", required=True)
    ap.add_argument("--limit", type=int, default=6)
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--timeout", type=float, default=45.0)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)

    bundle = build_bundle(args.base, args.query, args.limit, args.timeout)
    if not bundle["decisions"]:
        raise SystemExit("no decisions retrieved")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(bundle, fh, indent=2, ensure_ascii=False)
    print(f"wrote {args.out} ({len(bundle['decisions'])} decisions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
