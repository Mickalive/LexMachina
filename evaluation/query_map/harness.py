"""Independent executable checks for the LEX v45 query-map product.

This evaluator deliberately consumes JSON bundles rather than importing Product.
It checks contract/integrity properties that can be falsified automatically;
it does not pretend to prove that the map is useful to a jurist.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Iterable
from urllib.parse import urlparse

COUNTER_STATUSES = {"limiting", "contrary_or_exception", "candidate-limiting", "candidate-contrary"}


def _ids(bundle: dict) -> list[str]:
    return [str(d.get("decision_id") or "") for d in bundle.get("decisions", [])]


def geometry_signature(bundle: dict, precision: int = 4) -> str:
    """Stable semantic geometry signature, insensitive to decision array order."""
    rows = []
    for d in bundle.get("decisions", []):
        rows.append((
            str(d.get("decision_id") or ""),
            round(float(d.get("x") or 0.0), precision),
            round(float(d.get("y") or 0.0), precision),
            int(d.get("cluster_id") if d.get("cluster_id") is not None else -1),
            bool(d.get("is_outlier", False)),
        ))
    payload = json.dumps(sorted(rows), separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _known_recall(found: set[str], expected: Iterable[str] | None) -> dict:
    expected_set = {str(x) for x in (expected or []) if str(x)}
    if not expected_set:
        return {"expected": 0, "found": 0, "recall": None, "missing": []}
    hit = found & expected_set
    return {
        "expected": len(expected_set),
        "found": len(hit),
        "recall": round(len(hit) / len(expected_set), 4),
        "missing": sorted(expected_set - found),
    }


def evaluate_query_map_bundle(
    initial: dict,
    final: dict,
    *,
    known_relevant_ids: Iterable[str] | None = None,
    known_counter_ids: Iterable[str] | None = None,
) -> dict:
    initial_ids = _ids(initial)
    final_ids = _ids(final)
    final_set = set(final_ids)
    cited = {str(x) for x in final.get("answer", {}).get("cited_decision_ids", [])}
    counters = {
        str(d.get("decision_id"))
        for d in final.get("decisions", [])
        if d.get("counter_status") in COUNTER_STATUSES
    }

    duplicates = len(final_ids) - len(final_set)
    source_bad = []
    for d in final.get("decisions", []):
        u = str(d.get("canonical_url") or "")
        p = urlparse(u)
        if p.scheme != "https" or p.hostname != "mcp.opencaselaw.ch":
            source_bad.append(str(d.get("decision_id") or ""))

    unsupported_counter = []
    for d in final.get("decisions", []):
        if d.get("counter_status") not in COUNTER_STATUSES:
            continue
        evidence = str(d.get("counter_evidence") or "").strip()
        uncertainty = d.get("counter_uncertainty")
        if not evidence or uncertainty is None:
            unsupported_counter.append(str(d.get("decision_id") or ""))

    initial_geo = geometry_signature(initial)
    final_geo = geometry_signature(final)
    languages = Counter(str(d.get("language") or "?") for d in final.get("decisions", []))
    prov = final.get("provenance", {}) or {}
    retrieval = prov.get("retrieval", {}) or {}
    remote = retrieval.get("remote", {}) or {}

    checks = {
        "bundle_nonempty": bool(final_ids),
        "duplicate_free": duplicates == 0,
        "source_urls_valid": not source_bad,
        "answer_citations_constrained": cited <= final_set,
        "counter_classifications_supported": not unsupported_counter,
        "geometry_preserved_after_enrichment": initial_geo == final_geo,
        "progressive_phases": (
            initial.get("provenance", {}).get("phase") == "map_ready"
            and final.get("provenance", {}).get("phase") == "complete"
        ),
        "no_fixture_in_live_claim": not (
            prov.get("fixture_mode") is False
            and "fixture" in json.dumps(remote, sort_keys=True).lower()
        ),
    }

    result = {
        "schema": "lex-query-map-eval/1.0",
        "checks": checks,
        "pass": all(checks.values()),
        "counts": {
            "initial_decisions": len(initial_ids),
            "final_decisions": len(final_ids),
            "duplicates": duplicates,
            "cited_decisions": len(cited),
            "counter_decisions": len(counters),
            "clusters": len(final.get("clusters", [])),
        },
        "languages": dict(sorted(languages.items())),
        "bad_source_ids": source_bad,
        "invalid_cited_ids": sorted(cited - final_set),
        "unsupported_counter_ids": unsupported_counter,
        "geometry": {
            "initial_signature": initial_geo,
            "final_signature": final_geo,
            "preserved": initial_geo == final_geo,
        },
        "known_relevant": _known_recall(final_set, known_relevant_ids),
        "known_counter": _known_recall(counters, known_counter_ids),
        "latency": {
            "initial_seconds": initial.get("provenance", {}).get("latency_seconds"),
            "enrichment_seconds": prov.get("enrichment_latency_seconds"),
            "total_seconds": prov.get("latency_seconds_total"),
            "remote_seconds": remote.get("latency_seconds"),
        },
        "retrieval": {
            "languages": retrieval.get("candidate_languages", {}),
            "channels": retrieval.get("candidate_channels", {}),
            "network_calls": remote.get("request_summary", {}).get("network_calls"),
            "cache_hits": remote.get("request_summary", {}).get("cache_hits"),
            "degraded": remote.get("degraded"),
        },
    }
    return result
