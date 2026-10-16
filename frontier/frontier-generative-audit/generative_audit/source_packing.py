"""Source packing + citation-ID constraint enforcement.

Responsibilities:
  * canonical ``DecisionBundle`` input format for generation;
  * strict citation validation — every surfaced citation must be a decision
    ID that was actually retrieved into the bundle;
  * redaction of hallucinated citation markers from answer prose so the
    product never displays an unconstrained citation;
  * adapter from the product lane's ``query_result_bundle`` (v1.0) dict.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

#: Unicode hyphens that models frequently substitute inside decision IDs.
_HYPHEN_TRANSLATION = str.maketrans({c: "-" for c in "\u2010\u2011\u2012\u2013\u2014\u2015\u2212\u2043"})

#: Bracketed OR parenthetical citation markers.  Live free models emit both
#: ``[CH-001]`` and ``(CH-001)`` — observed during run 38176699303.
CITATION_PATTERN = re.compile(r"\[([^\[\]\n]{1,80})\]|\(([^()\n]{1,80})\)")

#: A token only counts as a *decision-ID citation* if it looks like one:
#: letters/digits joined by hyphen/underscore, containing a digit.  This
#: keeps prose parentheses ``(2020)`` and numbered citations ``[1]`` intact.
ID_LIKE_PATTERN = re.compile(
    r"^[A-Za-z][A-Za-z0-9]*[-_][A-Za-z0-9][A-Za-z0-9._/-]*$"
)

REDACTION_PLACEHOLDER = "[citation removed: not in retrieved set]"


def normalize_id(value: Any) -> str:
    """Strip and fold unicode hyphens so model output matches bundle IDs."""
    if value is None:
        return ""
    return str(value).strip().translate(_HYPHEN_TRANSLATION)


def is_id_like(token: str) -> bool:
    """True when a bracketed/parenthetical token could be a decision ID."""
    token = normalize_id(token)
    if not token or len(token) > 80 or " " in token:
        return False
    if not ID_LIKE_PATTERN.match(token):
        return False
    return any(ch.isdigit() for ch in token)


@dataclass
class Decision:
    """A single retrieved decision with its metadata."""

    decision_id: str
    title: str = ""
    text: str = ""
    citations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionBundle:
    """Canonical input for generation (the charter's query_result_bundle view).

    All decision IDs surfaced in a generated answer or an adversarial finding
    must be a subset of ``decision_ids``.
    """

    query: str
    decision_ids: List[str]
    decisions: List[Decision] = field(default_factory=list)
    retrieval_scores: Dict[str, float] = field(default_factory=dict)

    def by_id(self) -> Dict[str, Decision]:
        return {d.decision_id: d for d in self.decisions}


class CitationValidator:
    """Validate and filter citations against a bundle's decision IDs."""

    @staticmethod
    def filter_valid_citations(cited_ids: List[str], valid_ids: List[str]) -> List[str]:
        """Keep only IDs present in ``valid_ids``; order-preserving, de-duplicated.

        Comparison is unicode-hyphen-normalized; the bundle's original
        spelling is returned.
        """
        valid_map = {normalize_id(v): v for v in valid_ids if normalize_id(v)}
        seen = set()
        out: List[str] = []
        for cid in cited_ids:
            key = normalize_id(cid)
            if key and key in valid_map and key not in seen:
                seen.add(key)
                out.append(valid_map[key])
        return out

    @staticmethod
    def hallucinated_ids(cited_ids: List[str], valid_ids: List[str]) -> List[str]:
        """IDs that were cited but are absent from the bundle (programmatic rejection)."""
        valid_set = {normalize_id(v) for v in valid_ids if normalize_id(v)}
        out: List[str] = []
        seen = set()
        for cid in cited_ids:
            key = normalize_id(cid)
            if key and key not in valid_set and key not in seen:
                seen.add(key)
                out.append(key)
        return out

    @staticmethod
    def validate_bundle_integrity(bundle: DecisionBundle) -> bool:
        if not bundle.query or not bundle.query.strip():
            return False
        if not bundle.decision_ids:
            return False
        for dec in bundle.decisions:
            if not dec.decision_id or not dec.decision_id.strip():
                return False
        return True

    @staticmethod
    def from_decisions(query: str, decisions: List[Dict[str, Any]]) -> DecisionBundle:
        """Build a bundle from plain decision dicts.

        Accepts ``decision_id`` or ``id``; ``text``/``full_text``/``snippet``
        for the decision body; ``citation``/``title`` for the display label.
        """
        objs: List[Decision] = []
        ids: List[str] = []
        seen = set()
        for d in decisions:
            did = str(d.get("decision_id") or d.get("id") or "").strip()
            if not did or did in seen:
                continue
            seen.add(did)
            text = d.get("full_text") or d.get("text") or d.get("snippet") or ""
            title = d.get("title") or d.get("citation") or d.get("docket_number") or did
            metadata = {
                k: d.get(k)
                for k in (
                    "court", "language", "rank", "score", "decision_date",
                    "docket_number", "cluster_id", "canonical_url",
                    "provenance", "counter_status", "query_similarity",
                    "legal_anchor_score", "retrieval_score_raw", "snippet",
                )
                if d.get(k) is not None
            }
            metadata["evidence_hydrated"] = bool(d.get("full_text"))
            objs.append(
                Decision(
                    decision_id=did,
                    title=str(title),
                    text=str(text),
                    citations=list(d.get("citations") or []),
                    metadata=metadata,
                )
            )
            ids.append(did)
        scores = {}
        for d in decisions:
            did = str(d.get("decision_id") or d.get("id") or "").strip()
            if did and isinstance(d.get("score"), (int, float)):
                scores[did] = float(d["score"])
        return DecisionBundle(query=query, decision_ids=ids, decisions=objs, retrieval_scores=scores)


def from_product_bundle(product_bundle: Dict[str, Any]) -> DecisionBundle:
    """Adapt a product ``query_result_bundle`` (v1.0 dict) to a DecisionBundle.

    The product bundle is the accepted schema in docs/product/QUERY_MAP_MVP.md
    and product/query/bundle.py.  Decisions are ordered by ``rank`` when
    present so prompt ordering matches retrieval quality.
    """
    if not isinstance(product_bundle, dict):
        raise TypeError("product_bundle must be a dict")
    query = str(product_bundle.get("query") or "")
    decisions = list(product_bundle.get("decisions") or [])

    def _rank(d: Dict[str, Any]) -> Tuple[int, Any]:
        r = d.get("rank")
        return (0, r) if isinstance(r, int) else (1, 0)

    ordered = sorted(decisions, key=_rank)
    return CitationValidator.from_decisions(query, ordered)


def extract_citation_ids(text: str) -> List[str]:
    """Decision-ID citation candidates in ``text``, in order.

    Accepts ``[ID]`` and ``(ID)`` markers (both observed from live free
    models), normalizes unicode hyphens, and ignores non-ID-like tokens
    such as numbered citations ``[1]`` or plain parentheses.
    """
    if not text:
        return []
    out: List[str] = []
    for match in CITATION_PATTERN.finditer(text):
        token = match.group(1) if match.group(1) is not None else match.group(2)
        # Models emit nested styles like "([CH-001])"; peel outer brackets.
        token = normalize_id(token).strip("[]{}<>\"' ")
        if is_id_like(token) and token not in out:
            out.append(token)
    return out


def redact_unknown_citations(text: str, valid_ids: List[str]) -> Tuple[str, List[str]]:
    """Replace ID-like citation markers that are not bundle IDs with a placeholder.

    Returns ``(clean_text, removed_ids)``.  This guarantees the *surfaced*
    answer never contains a citation the retrieval set cannot support, while
    leaving ordinary parentheses and numbered citations untouched.
    """
    valid_set = {normalize_id(v) for v in valid_ids if normalize_id(v)}
    removed: List[str] = []

    def _sub(match: "re.Match[str]") -> str:
        raw_token = match.group(1) if match.group(1) is not None else match.group(2)
        token = normalize_id(raw_token).strip("[]{}<>\"' ")
        if not is_id_like(token) or token in valid_set:
            return match.group(0)
        removed.append(token)
        return REDACTION_PLACEHOLDER

    clean = CITATION_PATTERN.sub(_sub, text or "")
    return clean, removed
