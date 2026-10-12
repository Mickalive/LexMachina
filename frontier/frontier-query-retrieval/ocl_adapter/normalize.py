"""Normalisation of raw OpenCaseLaw payloads into candidate records.

One record shape is used for every acquisition channel (search page, language
filtered search, leading cases, citation neighbourhood, direct decision
lookup) so downstream ranking/dedup/mapping only has to know one schema.

Field semantics are frozen in ``INTEGRATION_CONTRACT.json``.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "candidate-1.0"

# Channels, in acquisition-priority order (lower wins on merge).
CHANNEL_SEARCH = "search"
CHANNEL_LANG = "search.language_filter"
CHANNEL_LEADING = "leading_case"
CHANNEL_CITE_IN = "citation.incoming"
CHANNEL_CITE_OUT = "citation.outgoing"
CHANNEL_LOOKUP = "decision_lookup"

CHANNEL_PRIORITY = {
    CHANNEL_SEARCH: 0,
    CHANNEL_LANG: 1,
    CHANNEL_LEADING: 2,
    CHANNEL_CITE_IN: 3,
    CHANNEL_CITE_OUT: 4,
    CHANNEL_LOOKUP: 5,
}

_WS_RE = re.compile(r"\s+")


def squash(text: Optional[str], limit: int = 0) -> str:
    s = _WS_RE.sub(" ", (text or "")).strip()
    if limit and len(s) > limit:
        return s[: limit - 1].rstrip() + "…"
    return s


def _s(v: Any) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return str(v)


def _num(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def canonical_url_for(decision_id: str) -> str:
    """OpenCaseLaw canonical decision URL (stable, always derivable)."""
    from urllib.parse import quote

    return f"https://mcp.opencaselaw.ch/entscheid/{quote(decision_id, safe='')}"


def pick_citation(raw: dict, language: Optional[str] = None) -> str:
    """Language-appropriate citation string; never invents one."""
    lang = (language or "de").lower()
    direct = f"citation_string_{lang}"
    if _s(raw.get(direct)):
        return str(raw[direct]).strip()
    for key in ("citation_string_de", "citation_string_fr", "citation_string_it"):
        if _s(raw.get(key)):
            return str(raw[key]).strip()
    if _s(raw.get("citation")):
        return str(raw["citation"]).strip()
    # Falling back to the docket number is a faithful, non-fabricated citation.
    if _s(raw.get("docket_number")):
        court = _s(raw.get("court")) or ""
        return f"{court} {raw['docket_number']}".strip()
    return ""


def empty_candidate(decision_id: str, *, channel: str) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "decision_id": decision_id,
        "canonical_decision_id": decision_id,
        "canonical_url": canonical_url_for(decision_id),
        "source_url": None,
        "pdf_url": None,
        "court": None,
        "court_name": None,
        "court_level": None,
        "canton": None,
        "docket_number": None,
        "language": None,
        "decision_date": None,
        "title": None,
        "regeste": None,
        "snippet": "",
        "citation": "",
        "citation_string_de": None,
        "citation_string_fr": None,
        "citation_string_it": None,
        "legal_area": None,
        "statutes": [],
        "citation_count": None,
        "rank": None,
        "score": None,
        "score_kind": None,
        "channel": channel,
        "channels": [channel],
        "variant_id": None,
        "query": None,
        "page": None,
        "provenance": "",
        "provenance_events": [],
        "record_kind": None,
        "is_canonical": True,
        "detail_status": "search_hit",     # search_hit | hydrated | not_found | pending
        "full_text": None,
        "full_text_status": "lazy",        # lazy | fetched | unavailable
        "structure": None,
        "structure_status": "lazy",        # lazy | fetched | unavailable
        "expansion_depth": 0,
        "needs_detail": False,
    }


def _base_provenance(channel: str, *, variant_id: str = "", page=None) -> str:
    parts = [f"ocl:{channel}"]
    if variant_id:
        parts.append(f"variant={variant_id}")
    if page is not None:
        parts.append(f"page={page}")
    return " ".join(parts)


def normalize_search_hit(
    raw: dict,
    *,
    channel: str = CHANNEL_SEARCH,
    query: str = "",
    variant_id: str = "",
    page: int = 0,
    offset: int = 0,
    language_filter: Optional[str] = None,
) -> Optional[dict]:
    """Normalise one ``/decisions`` search result. Returns None if unusable."""
    if not isinstance(raw, dict):
        return None
    decision_id = _s(raw.get("decision_id")) or _s(raw.get("canonical_decision_id"))
    if not decision_id:
        return None
    lang = _s(raw.get("language")) or _s(language_filter)
    rec = empty_candidate(decision_id, channel=channel)
    rec.update(
        {
            "canonical_decision_id": _s(raw.get("canonical_decision_id")) or decision_id,
            "canonical_url": _s(raw.get("canonical_url")) or canonical_url_for(
                _s(raw.get("canonical_decision_id")) or decision_id
            ),
            "source_url": _s(raw.get("source_url")),
            "pdf_url": _s(raw.get("pdf_url")),
            "court": _s(raw.get("court")),
            "court_name": _s(raw.get("court_name")),
            "court_level": _s(raw.get("court_level")),
            "canton": _s(raw.get("canton")),
            "docket_number": _s(raw.get("docket_number")),
            "language": lang,
            "decision_date": _s(raw.get("decision_date")),
            "title": _s(raw.get("title")),
            "regeste": squash(raw.get("regeste"), 4000),
            "snippet": squash(raw.get("snippet") or raw.get("regeste") or raw.get("title"), 1200),
            "citation": pick_citation(raw, lang),
            "citation_string_de": _s(raw.get("citation_string_de")),
            "citation_string_fr": _s(raw.get("citation_string_fr")),
            "citation_string_it": _s(raw.get("citation_string_it")),
            "legal_area": _s(raw.get("legal_area")),
            "statutes": [str(s) for s in (raw.get("statutes") or []) if s],
            "citation_count": int(raw["citation_count"]) if isinstance(raw.get("citation_count"), (int, float)) else None,
            "score": _num(raw.get("relevance_score")),
            "score_kind": "relevance" if _num(raw.get("relevance_score")) is not None else None,
            "channel": channel,
            "channels": [channel],
            "variant_id": variant_id,
            "query": query,
            "page": page,
            "is_canonical": bool(raw.get("is_canonical", True)),
            "record_kind": "search_hit",
            "provenance": _base_provenance(channel, variant_id=variant_id, page=page),
        }
    )
    rec["provenance_events"] = [
        {
            "channel": channel,
            "endpoint": "/decisions",
            "variant_id": variant_id,
            "language_filter": language_filter,
            "page": page,
            "offset": offset,
            "relevance_score": rec["score"],
        }
    ]
    return rec


def normalize_leading_case(raw: dict, *, query: str = "", variant_id: str = "") -> Optional[dict]:
    if not isinstance(raw, dict):
        return None
    decision_id = _s(raw.get("decision_id"))
    if not decision_id:
        return None
    rec = normalize_search_hit(
        raw,
        channel=CHANNEL_LEADING,
        query=query,
        variant_id=variant_id,
        page=0,
        offset=0,
    )
    if rec is None:
        return None
    count = _num(raw.get("citation_count"))
    rec["record_kind"] = "leading_case"
    rec["citation_count"] = int(count) if count is not None else None
    if rec["score"] is None and count is not None:
        rec["score"] = count
        rec["score_kind"] = "citation_count"
    rec["snippet"] = rec["snippet"] or squash(raw.get("regeste"), 1200)
    rec["provenance"] = _base_provenance(CHANNEL_LEADING, variant_id=variant_id)
    rec["provenance_events"] = [
        {
            "channel": CHANNEL_LEADING,
            "endpoint": "/leading-cases",
            "variant_id": variant_id,
            "citation_count": rec["citation_count"],
        }
    ]
    return rec


def normalize_citation(
    raw: dict,
    *,
    direction: str,
    seed_id: str,
    query: str = "",
) -> Optional[dict]:
    """Normalise one incoming/outgoing citation edge into a candidate shell."""
    if not isinstance(raw, dict):
        return None
    if direction == "incoming":
        decision_id = _s(raw.get("source_decision_id"))
        channel = CHANNEL_CITE_IN
    else:
        decision_id = _s(raw.get("target_decision_id"))
        channel = CHANNEL_CITE_OUT
    if not decision_id:
        return None
    rec = empty_candidate(decision_id, channel=channel)
    conf = _num(raw.get("confidence_score"))
    rec.update(
        {
            "court": _s(raw.get("court")),
            "docket_number": _s(raw.get("docket_number")),
            "decision_date": _s(raw.get("decision_date")),
            "citation": _s(raw.get("target_ref")) or "",
            "score": conf,
            "score_kind": "citation_confidence",
            "channel": channel,
            "channels": [channel],
            "query": query,
            "record_kind": "citation_neighbour",
            "detail_status": "pending",
            "needs_detail": True,
            "provenance": f"ocl:{channel} seed={seed_id}",
            "expansion_depth": 1,
        }
    )
    rec["provenance_events"] = [
        {
            "channel": channel,
            "endpoint": "/citations",
            "seed_decision_id": seed_id,
            "direction": direction,
            "confidence": conf,
            "mention_count": _num(raw.get("mention_count")),
        }
    ]
    return rec


def normalize_decision_detail(raw: dict, *, channel: str = CHANNEL_LOOKUP) -> Optional[dict]:
    """Normalise ``/decisions/{id}`` (full decision, includes text)."""
    if not isinstance(raw, dict):
        return None
    decision_id = _s(raw.get("decision_id"))
    if not decision_id:
        return None
    rec = normalize_search_hit(raw, channel=channel, page=0)
    text = raw.get("full_text") or raw.get("text") or ""
    rec["full_text"] = str(text) if text else None
    rec["full_text_status"] = "fetched" if text else "unavailable"
    rec["detail_status"] = "hydrated"
    rec["record_kind"] = "decision_full"
    return rec


def structure_summary(raw: dict) -> dict:
    """Compact, stable summary of ``/structure/{id}`` for the bundle."""
    if not isinstance(raw, dict):
        return {}
    erwaegungen = raw.get("erwaegungen_paragraphs") or []
    heads: List[dict] = []
    if isinstance(erwaegungen, list):
        for item in erwaegungen[:50]:
            if isinstance(item, dict):
                heads.append(
                    {
                        "e_number": item.get("e_number") or item.get("number"),
                        "heading": squash(item.get("heading") or item.get("title"), 300),
                        "chars": item.get("chars") or item.get("length"),
                    }
                )
            else:
                heads.append({"e_number": None, "heading": squash(str(item), 300), "chars": None})
    return {
        "decision_id": _s(raw.get("decision_id")),
        "canonical_url": _s(raw.get("canonical_url")),
        "court": _s(raw.get("court")),
        "language": _s(raw.get("language")),
        "decision_date": _s(raw.get("decision_date")),
        "regeste": squash(raw.get("regeste"), 2000),
        "dispositiv": squash(raw.get("dispositiv"), 2000),
        "dispositiv_orders": [
            squash(o, 500) for o in (raw.get("dispositiv_orders") or [])[:20]
        ],
        "sachverhalt_excerpt": squash(raw.get("sachverhalt_excerpt"), 2000),
        "erwaegungen": heads,
        "erwaegungen_paragraph_count": raw.get("erwaegungen_paragraph_count"),
        "extraction_methods": raw.get("extraction_methods") or [],
    }
