"""Population extraction for the frozen adversarial-discoverability metrics.

Every function here is a pure function of a loaded bundle / leg dict.
Populations are named exactly as in RULES.json ``populations``.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from . import COUNTER_VALUES, PLACEHOLDER_EVIDENCE


def decisions_of(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """All decisions, in the artifact's own order (never re-sorted)."""
    out = [d for d in (doc.get("decisions") or []) if isinstance(d, dict)]
    return out


def counter_status(d: Dict[str, Any]) -> str:
    return str(d.get("counter_status") or "none")


def c_strict(decisions: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """PRIMARY population: charter-literal counter-authority rows."""
    return [d for d in decisions if counter_status(d) in COUNTER_VALUES]


def c_challenged(decisions: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """SECONDARY, read-only population: every non-``none`` row (the 6/14-row series)."""
    return [d for d in decisions if counter_status(d) != "none"]


def _rank_of(d: Dict[str, Any], fallback: int) -> int:
    rank = d.get("rank")
    if isinstance(rank, bool):
        return fallback
    if isinstance(rank, int) and rank > 0:
        return rank
    try:
        r = int(rank)
    except (TypeError, ValueError):
        return fallback
    return r if r > 0 else fallback


def ranked_pairs(decisions: Iterable[Dict[str, Any]]) -> List[tuple]:
    """``[(decision, rank)]`` in the artifact's own order with a concrete rank."""
    return [(d, _rank_of(d, i)) for i, d in enumerate(decisions, start=1)]


def consensus_decision(doc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The decision at rank 1 — the head of the conventional ranked list."""
    best = None
    best_rank = None
    for d in decisions_of(doc):
        r = _rank_of(d, 10 ** 9)
        if best_rank is None or r < best_rank:
            best, best_rank = d, r
    return best


def consensus_cluster(doc: Dict[str, Any]) -> Optional[int]:
    """RULES.json ``populations.consensus_cluster``.

    ``cluster_id`` of the rank-1 decision; absent rank 1 -> largest cluster,
    ties broken by lowest ``cluster_id``.
    """
    head = consensus_decision(doc)
    if head is not None and head.get("cluster_id") is not None:
        return head.get("cluster_id")
    clusters = [c for c in (doc.get("clusters") or []) if isinstance(c, dict)]
    if not clusters:
        return None
    best = sorted(clusters, key=lambda c: (-int(c.get("size") or 0), c.get("cluster_id")))[0]
    return best.get("cluster_id")


def channels_of(d: Dict[str, Any]) -> List[str]:
    ch = d.get("channels")
    if isinstance(ch, str):
        return [ch]
    if not isinstance(ch, list):
        return []
    return [str(c) for c in ch]


def initial_channel_set(doc: Dict[str, Any]) -> set:
    """RULES.json ``metrics.b_marginal_retrieval_contribution.definition``.

    Union of every channel inventory the INITIAL broad retrieval declares.
    Empty when the artifact carries no retrieval provenance (reality-check legs),
    which makes metric (b) NOT_APPLICABLE rather than PASS.
    """
    prov = doc.get("provenance")
    out = set()
    if not isinstance(prov, dict):
        return out
    blocks = [
        ((prov.get("retrieval") or {}).get("dedupe") or {}).get("candidates_by_channel"),
        (prov.get("retrieval") or {}).get("candidate_channels"),
        (prov.get("retrieval_first_page") or {}).get("candidate_channels"),
    ]
    for block in blocks:
        if isinstance(block, dict):
            for k in block:
                out.add(str(k))
    return out


def has_retrieval_provenance(doc: Dict[str, Any]) -> bool:
    return bool(initial_channel_set(doc))


def placeholder_evidence(d: Dict[str, Any]) -> bool:
    return str(d.get("counter_evidence") or "").strip() == PLACEHOLDER_EVIDENCE


def substantive_reason(d: Dict[str, Any]) -> bool:
    """Non-empty ``counter_reason`` that is not the placeholder string."""
    r = str(d.get("counter_reason") or "").strip()
    return bool(r) and r != PLACEHOLDER_EVIDENCE


def verified_flag(d: Dict[str, Any]) -> bool:
    return d.get("counter_evidence_verified") is True


def year_of(d: Dict[str, Any]) -> Optional[int]:
    raw = str(d.get("decision_date") or "")[:4].strip()
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def median_year(doc: Dict[str, Any]) -> Optional[float]:
    years = sorted(y for y in (year_of(d) for d in decisions_of(doc)) if y is not None)
    if not years:
        return None
    n = len(years)
    mid = n // 2
    return float(years[mid]) if n % 2 else (years[mid - 1] + years[mid]) / 2.0


def modal_language(doc: Dict[str, Any], cluster_id: Optional[int]) -> Optional[str]:
    """Modal ``language`` over the consensus cluster; ties -> alphabetically first.

    ``?`` / empty language markers are excluded: they record a missing value, not a
    language, and letting them win would fabricate a consensus band.  Returns
    ``None`` when no real language is present, so callers can report the metric as
    NOT_APPLICABLE instead of scoring a placeholder.
    """
    hist: Dict[str, int] = {}
    for d in decisions_of(doc):
        if cluster_id is None or d.get("cluster_id") == cluster_id:
            lang = str(d.get("language") or "").strip().lower()
            if not lang or lang == "?":
                continue
            hist[lang] = hist.get(lang, 0) + 1
    if not hist:
        return None
    return sorted(hist.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def answer_prose(doc: Dict[str, Any]) -> str:
    ans = doc.get("answer")
    if isinstance(ans, dict):
        return str(ans.get("prose") or "")
    if isinstance(ans, str):
        return ans
    # slimmed reality-check leg reports flatten the answer to ``answer_prose``
    return str(doc.get("answer_prose") or "")


def answer_cited_ids(doc: Dict[str, Any]) -> List[str]:
    ans = doc.get("answer")
    if isinstance(ans, dict) and isinstance(ans.get("cited_decision_ids"), list):
        return [str(x) for x in ans["cited_decision_ids"]]
    if isinstance(doc.get("cited_decision_ids"), list):
        return [str(x) for x in doc["cited_decision_ids"]]
    return []


def leg_cited_decisions(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Reality-check legs expose ``cited_decisions`` instead of ``decisions``.

    Each entry carries ``decision_id``/``rank``/``counter_status`` but not
    ``channels``/``cluster_id``/``is_outlier``/``counter_evidence``; metrics
    that need those are reported NOT_APPLICABLE for legs rather than silently
    scored as zero.

    ``cited_decisions`` is a SUBSET (the answer-cited rows), never the leg's
    decision population.  RULES.json ``metrics.a_counter_yield`` is defined as
    "a share of the bundle", so the denominator for a leg is its own
    ``decision_count``, never ``len(cited_decisions)``.
    """
    rows = [d for d in (doc.get("cited_decisions") or []) if isinstance(d, dict)]
    return rows


def bundle_total(doc: Dict[str, Any], rows: List[Dict[str, Any]], source: str) -> int:
    """``|B_all|`` for the artifact — the denominator of metric (a).

    A query_result_bundle exposes its full population as ``decisions``.  A slimmed
    reality-check leg does not, but it does report the true population size as
    ``decision_count``; using ``len(cited_decisions)`` there would inflate the
    yield by an order of magnitude.
    """
    if source == "decisions":
        return len(rows)
    raw = doc.get("decision_count")
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return len(rows)
    return n if n > 0 else len(rows)


def rows_carry(doc: Dict[str, Any], rows: List[Dict[str, Any]], keys: Iterable[str]) -> bool:
    """True when the artifact's row schema actually exports any of ``keys``.

    Used to distinguish "the product produced a zero" from "this artifact does
    not export the field at all", which RULES.json forbids conflating.
    """
    wanted = set(keys)
    for d in rows:
        if wanted & set(d.keys()):
            return True
    return False
