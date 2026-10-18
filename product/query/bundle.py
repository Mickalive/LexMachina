"""query_result_bundle: central integration contract (ARCHITECTURE.md).

Minimum fields: query + variants/provenance, answer + cited IDs, decisions
(stable id, URL/citation, court/date/language, text/snippets), retrieval scores
+ provenance, counter-authority status, cluster id/label, x/y coords, relations.
"""
from __future__ import annotations

from typing import Any

from product.query.counter_status import (
    counter_authority_count,
    counter_status_bearing_count,
    counter_status_histogram,
)

BUNDLE_VERSION = "1.0"

REQUIRED_TOP = ["bundle_version", "query", "query_variants", "answer",
                "decisions", "clusters", "relations", "provenance"]
REQUIRED_DECISION = ["decision_id", "court", "language", "rank", "score",
                     "provenance", "snippet", "cluster_id", "x", "y",
                     "counter_status", "canonical_url", "citation"]


def build_bundle(query: str, query_variants: list[str], answer: dict,
                 decisions: list[dict], clusters: list[dict],
                 relations: list[dict], provenance: dict) -> dict:
    return {
        "bundle_version": BUNDLE_VERSION,
        "query": query,
        "query_variants": query_variants,
        "answer": answer,
        "decisions": decisions,
        "clusters": clusters,
        "relations": relations,
        "provenance": provenance,
    }


def validate_bundle(bundle: dict) -> list[str]:
    """Return list of validation errors (empty = valid)."""
    errors = []
    for key in REQUIRED_TOP:
        if key not in bundle:
            errors.append(f"missing top-level key: {key}")
    if errors:
        return errors
    if not isinstance(bundle["decisions"], list) or not bundle["decisions"]:
        errors.append("decisions must be a non-empty list")
        return errors
    ids = set()
    for i, d in enumerate(bundle["decisions"]):
        for key in REQUIRED_DECISION:
            if key not in d:
                errors.append(f"decision[{i}] missing key: {key}")
        did = d.get("decision_id")
        if did in ids:
            errors.append(f"duplicate decision_id: {did}")
        ids.add(did)
    cited = set(bundle.get("answer", {}).get("cited_decision_ids", []))
    unknown = cited - ids
    if unknown:
        errors.append(f"answer cites unknown decision_ids: {sorted(unknown)}")
    for c in bundle.get("clusters", []):
        if "cluster_id" not in c or "label" not in c:
            errors.append(f"cluster missing id/label: {c}")
    return errors


def bundle_summary(bundle: dict) -> dict[str, Any]:
    decs = bundle.get("decisions", [])
    langs: dict[str, int] = {}
    for d in decs:
        langs[d.get("language", "?")] = langs.get(d.get("language", "?"), 0) + 1
    return {
        "n_decisions": len(decs),
        "n_clusters": len(bundle.get("clusters", [])),
        "n_relations": len(bundle.get("relations", [])),
        # RF1: `n_counter` used `counter_status != "none"`, which counted every
        # decision the sourced answer cited. Both definitions are now published
        # under their honest names (audit CYCLE_39065274887 F3 convention).
        "n_counter_authorities": counter_authority_count(decs),
        "n_rows_with_counter_status": counter_status_bearing_count(decs),
        "counter_status_histogram": counter_status_histogram(decs),
        "languages": langs,
        "answer_citations": len(bundle.get("answer", {}).get("cited_decision_ids", [])),
    }
