"""query_result_bundle **candidate** bundle: shape, validation, product bridge.

Two layers:

* :func:`build_candidate_bundle` - what this adapter produces. It carries the
  retrieval half of the canonical ``query_result_bundle`` described in
  ``docs/product/QUERY_MAP_MVP.md``: query + variants + provenance + a
  normalised candidate decision set. Answer / clusters / relations / counter
  status are explicitly *pending downstream* rather than fabricated.

* :func:`to_product_bundle` - a lossless bridge onto the ACCEPTED product
  contract ``product/query/bundle.py`` (``BUNDLE_VERSION``, ``REQUIRED_TOP``,
  ``REQUIRED_DECISION``). Product can call
  ``query.bundle.validate_bundle(to_product_bundle(b)) == []`` without any
  adapter-specific code.

Field constants below are mirrored from the accepted module so this package
stays importable without the accepted mount; :mod:`.contract` checks the
mirror against the live file when the mount is present.
"""
from __future__ import annotations

import time
from typing import Any, Dict, Iterable, List, Optional, Sequence

CANDIDATE_BUNDLE_VERSION = "1.0-candidate"
ADAPTER_NAME = "ocl_adapter"

# --- accepted product contract mirror (product/query/bundle.py) -------------
PRODUCT_BUNDLE_VERSION = "1.0"
PRODUCT_REQUIRED_TOP = [
    "bundle_version", "query", "query_variants", "answer",
    "decisions", "clusters", "relations", "provenance",
]
PRODUCT_REQUIRED_DECISION = [
    "decision_id", "court", "language", "rank", "score",
    "provenance", "snippet", "cluster_id", "x", "y",
    "counter_status", "canonical_url", "citation",
]
# -----------------------------------------------------------------------------

CANDIDATE_REQUIRED = [
    "schema_version",
    "decision_id",
    "canonical_decision_id",
    "canonical_url",
    "source_url",
    "court",
    "court_name",
    "language",
    "decision_date",
    "docket_number",
    "title",
    "regeste",
    "snippet",
    "citation",
    "rank",
    "score",
    "channels",
    "provenance",
    "provenance_events",
    "detail_status",
    "full_text_status",
    "structure_status",
]

PENDING_DOWNSTREAM_FIELDS = ["answer", "clusters", "relations", "cluster_id", "x", "y", "counter_status"]


def build_candidate_bundle(
    *,
    query: str,
    query_variants: Sequence[dict],
    candidates: Sequence[dict],
    dedupe_stats: dict,
    provenance: dict,
    lazy: Optional[dict] = None,
    generated_at: Optional[float] = None,
    config_snapshot: Optional[dict] = None,
) -> dict:
    """Assemble the adapter's output bundle (plain JSON-serialisable dict)."""
    ranked = rank_candidates(candidates)
    for i, c in enumerate(ranked, start=1):
        c["rank"] = i
    return {
        "bundle_version": CANDIDATE_BUNDLE_VERSION,
        "adapter": ADAPTER_NAME,
        "query": query,
        "query_variants": [dict(v) for v in query_variants],
        "candidates": ranked,
        "n_candidates": len(ranked),
        "dedupe": dict(dedupe_stats),
        "provenance": dict(provenance),
        "lazy": dict(lazy or {"full_text": "lazy", "structure": "lazy", "hydrated": []}),
        "pending_downstream": list(PENDING_DOWNSTREAM_FIELDS),
        "config": dict(config_snapshot or {}),
        "generated_at": generated_at if generated_at is not None else time.time(),
    }


def _has_relevance(rec: dict) -> bool:
    return rec.get("score") is not None and rec.get("score_kind") == "relevance"


def rank_candidates(candidates: Iterable[dict]) -> List[dict]:
    """Deterministic candidate ordering: relevance-ranked first, id tiebreak.

    Non-relevance channels (citation confidence, leading-case counts) sort
    after relevance hits so a downstream reranker starts from a sane prior.
    """
    recs = list(candidates)

    def key(rec: dict):
        has_rel = 0 if _has_relevance(rec) else 1
        score = rec.get("score")
        score = float("-inf") if score is None else -float(score)
        return (has_rel, score, str(rec.get("decision_id") or ""))

    recs.sort(key=key)
    return recs


def validate_candidate_bundle(bundle: dict) -> List[str]:
    """Return validation errors; empty list == valid."""
    errors: List[str] = []
    if not isinstance(bundle, dict):
        return ["bundle is not a dict"]
    if bundle.get("bundle_version") != CANDIDATE_BUNDLE_VERSION:
        errors.append(f"unexpected bundle_version: {bundle.get('bundle_version')!r}")
    for key in ("query", "query_variants", "candidates", "dedupe", "provenance"):
        if key not in bundle:
            errors.append(f"missing top-level key: {key}")
    if errors:
        return errors
    cands = bundle["candidates"]
    if not isinstance(cands, list):
        errors.append("candidates must be a list")
        return errors
    if not cands:
        errors.append("candidates must be non-empty")
        return errors
    seen = set()
    for i, c in enumerate(cands):
        for key in CANDIDATE_REQUIRED:
            if key not in c:
                errors.append(f"candidate[{i}] missing key: {key}")
        did = c.get("decision_id")
        if did in seen:
            errors.append(f"duplicate decision_id after dedupe: {did}")
        seen.add(did)
        if not c.get("provenance"):
            errors.append(f"candidate[{i}] has empty provenance")
        if not c.get("canonical_url"):
            errors.append(f"candidate[{i}] has empty canonical_url")
        if c.get("rank") != i + 1:
            errors.append(f"candidate[{i}] rank {c.get('rank')} != {i + 1}")
    return errors


def bundle_summary(bundle: dict) -> dict:
    cands = bundle.get("candidates", [])
    langs: Dict[str, int] = {}
    channels: Dict[str, int] = {}
    for c in cands:
        langs[c.get("language") or "?"] = langs.get(c.get("language") or "?", 0) + 1
        for ch in c.get("channels") or []:
            channels[ch] = channels.get(ch, 0) + 1
    return {
        "bundle_version": bundle.get("bundle_version"),
        "query": bundle.get("query"),
        "n_candidates": len(cands),
        "n_query_variants": len(bundle.get("query_variants", [])),
        "languages": dict(sorted(langs.items())),
        "channels": dict(sorted(channels.items())),
        "n_hydrated": sum(1 for c in cands if c.get("detail_status") == "hydrated"),
        "n_with_full_text": sum(1 for c in cands if c.get("full_text")),
        "n_with_structure": sum(1 for c in cands if c.get("structure")),
        "dedupe": bundle.get("dedupe", {}),
        "degraded": bool(bundle.get("provenance", {}).get("degraded")),
        "n_failures": len(bundle.get("provenance", {}).get("failures", [])),
        "request_summary": bundle.get("provenance", {}).get("request_summary", {}),
    }


def to_product_bundle(bundle: dict) -> dict:
    """Bridge to the accepted ``product/query/bundle.py`` contract.

    Decision rows carry every ``REQUIRED_DECISION`` key. Fields owned by
    downstream stages are emitted as explicit ``None`` / ``"unclassified"``
    placeholders (listed in ``pending_downstream``) instead of invented data.
    """
    decisions: List[dict] = []
    for c in bundle.get("candidates", []):
        decisions.append({
            "decision_id": c.get("decision_id"),
            "court": c.get("court"),
            "language": c.get("language"),
            "rank": c.get("rank"),
            "score": c.get("score"),
            "provenance": c.get("provenance"),
            "snippet": c.get("snippet") or "",
            "cluster_id": None,
            "x": None,
            "y": None,
            "counter_status": "unclassified",
            "canonical_url": c.get("canonical_url"),
            "citation": c.get("citation") or "",
            # extra, adapter-owned context (product may ignore)
            "decision_date": c.get("decision_date"),
            "docket_number": c.get("docket_number"),
            "title": c.get("title"),
            "regeste": c.get("regeste"),
            "source_url": c.get("source_url"),
            "channels": list(c.get("channels") or []),
            "detail_status": c.get("detail_status"),
        })
    return {
        "bundle_version": PRODUCT_BUNDLE_VERSION,
        "query": bundle.get("query", ""),
        "query_variants": [v.get("text", "") for v in bundle.get("query_variants", [])],
        "answer": {"text": "", "method": "pending_upstream", "cited_decision_ids": []},
        "decisions": decisions,
        "clusters": [],
        "relations": [],
        "provenance": {
            **bundle.get("provenance", {}),
            "source": "ocl_adapter_candidate_bundle",
            "candidate_bundle_version": bundle.get("bundle_version"),
        },
        "pending_downstream": list(PENDING_DOWNSTREAM_FIELDS),
    }


def validate_against_product(bundle: dict) -> List[str]:
    """Validate :func:`to_product_bundle` output against the mirrored accepted
    contract. Returns ``[]`` when the bridge is contract-compatible."""
    prod = to_product_bundle(bundle)
    errors: List[str] = []
    for key in PRODUCT_REQUIRED_TOP:
        if key not in prod:
            errors.append(f"missing top-level key: {key}")
    if errors:
        return errors
    decisions = prod["decisions"]
    if not isinstance(decisions, list) or not decisions:
        errors.append("decisions must be a non-empty list")
        return errors
    ids = set()
    for i, d in enumerate(decisions):
        for key in PRODUCT_REQUIRED_DECISION:
            if key not in d:
                errors.append(f"decision[{i}] missing key: {key}")
        did = d.get("decision_id")
        if did in ids:
            errors.append(f"duplicate decision_id: {did}")
        ids.add(did)
    cited = set(prod["answer"].get("cited_decision_ids", []))
    unknown = cited - ids
    if unknown:
        errors.append(f"answer cites unknown decision_ids: {sorted(unknown)}")
    for c in prod.get("clusters", []):
        if "cluster_id" not in c or "label" not in c:
            errors.append(f"cluster missing id/label: {c}")
    return errors
