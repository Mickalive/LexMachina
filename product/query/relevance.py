"""Deterministic legal relevance reranking for the product hot path.

OpenCaseLaw supplies broad lexical recall. This layer reorders that candidate
set for the user's concrete question before mapping, hydration and generation.
It stays cheap, local and auditable: TF-IDF similarity over retrieved text plus
small boosts for exact Swiss statute anchors and federal authority.
"""
from __future__ import annotations

import html
import re
from typing import Iterable

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

TAG_RE = re.compile(r"<[^>]+>")
ARTICLE_RE = re.compile(
    r"(?i)\bart(?:\.|icle)?\s*(\d+[a-z]?)"
    r"(?:\s*(?:al\.|alin[ée]a|abs\.|cpv\.)\s*(\d+))?"
    r"\s*(CP|CO|CC|CPC|CPP|LTF|StGB|OR|ZGB|ZPO|StPO|BGG)?\b"
)

CODE_FAMILY = {
    "CP": {"CP", "STGB"},
    "STGB": {"CP", "STGB"},
    "CO": {"CO", "OR"},
    "OR": {"CO", "OR"},
    "CC": {"CC", "ZGB"},
    "ZGB": {"CC", "ZGB"},
    "CPC": {"CPC", "ZPO"},
    "ZPO": {"CPC", "ZPO"},
    "CPP": {"CPP", "STPO"},
    "STPO": {"CPP", "STPO"},
    "LTF": {"LTF", "BGG"},
    "BGG": {"LTF", "BGG"},
}

STOPWORDS = frozenset("""
der die das und des den dem ein eine einer eines einem einen auch als bei nach noch nur oder vom von
vor zum zur über fuer für mit sich sie sind ist war wird werden wurde wurden haben hat hatte aus auf an am
im ins aber doch denn le la les de des du un une est sont et en dans que qui pour pas sur plus par
au aux il ils elle elles nous vous leur son sa ses ce cette ces dont comme avec di del della dello
che non uno dei degli delle dal allo alla al ai agli sul sulla per con come più sono era stato stata
hanno aveva perché nel cui alle quale quali questo questa questi queste anche tra fra può possono
deve devono essere ogni dove quando senza sopra sotto dopo prima mentre the and for are with from
that this have has had were was will bundesgericht tribunal tribunale federale recours beschwerde
ricorso arrêt urteil sentenza entscheid entscheidung considérant erwägung considerando ordonnance
verordnung ordinanza code droit recht diritto mark regeste regesto consid bger bge atf dtf
""".split())


def clean_text(value: object) -> str:
    text = html.unescape(str(value or ""))
    text = TAG_RE.sub(" ", text)
    return " ".join(text.split())


def decision_text(decision: dict) -> str:
    parts = [
        decision.get("title"),
        decision.get("citation"),
        decision.get("regeste"),
        decision.get("snippet"),
        decision.get("full_text"),
    ]
    return clean_text(" ".join(str(x or "") for x in parts))[:12000]


def _anchors(query_text: str) -> list[tuple[str, str | None]]:
    out: list[tuple[str, str | None]] = []
    for match in ARTICLE_RE.finditer(query_text or ""):
        number = match.group(1).lower()
        code = (match.group(3) or "").upper() or None
        item = (number, code)
        if item not in out:
            out.append(item)
    return out


def _anchor_score(text: str, anchors: Iterable[tuple[str, str | None]]) -> float:
    low = text.casefold()
    score = 0.0
    for number, code in anchors:
        if not re.search(rf"(?i)\bart(?:\.|icle)?\s*{re.escape(number)}\b", low):
            continue
        if not code:
            score += 0.6
            continue
        family = CODE_FAMILY.get(code, {code})
        if any(re.search(rf"(?i)\b{re.escape(alias)}\b", text) for alias in family):
            score += 1.0
        else:
            score += 0.35
    return min(1.0, score)


def rerank_product_bundle(product_bundle: dict) -> dict:
    """Reorder decisions by query-conditioned local legal relevance.

    The adapter's remote score is retained as retrieval_score_raw. The
    product-facing score becomes a 0..1 relevance score used consistently
    for hydration, source packing and adversarial shortlisting.
    """
    decisions = list(product_bundle.get("decisions") or [])
    if not decisions:
        return product_bundle

    variants = [str(v) for v in product_bundle.get("query_variants") or [] if str(v).strip()]
    query = str(product_bundle.get("query") or "")
    query_doc = clean_text(" ".join([query, *variants]))
    docs = [decision_text(d) for d in decisions]

    vectorizer = TfidfVectorizer(
        lowercase=True,
        strip_accents="unicode",
        sublinear_tf=True,
        ngram_range=(1, 2),
        max_features=12000,
        stop_words=list(STOPWORDS),
        token_pattern=r"(?u)\b[\wÀ-ÿ][\wÀ-ÿ.-]{1,}\b",
    )
    matrix = vectorizer.fit_transform([query_doc, *docs])
    query_vec = matrix[0]
    sims = (matrix[1:] @ query_vec.T).toarray().ravel()

    raw = np.array([
        float(d.get("score")) if isinstance(d.get("score"), (int, float)) else 0.0
        for d in decisions
    ], dtype=float)
    if len(raw) and float(raw.max()) > float(raw.min()):
        raw_norm = (raw - raw.min()) / (raw.max() - raw.min())
    elif len(raw):
        raw_norm = np.zeros_like(raw)
    else:
        raw_norm = raw

    anchors = _anchors(query_doc)
    scored = []
    for idx, dec in enumerate(decisions):
        text = docs[idx]
        anchor = _anchor_score(text, anchors)
        court = str(dec.get("court") or "").lower()
        federal = 1.0 if court in {"bger", "bge", "bstger"} else 0.0
        value = (
            0.72 * float(sims[idx])
            + 0.16 * float(raw_norm[idx])
            + 0.10 * anchor
            + 0.02 * federal
        )
        value = max(0.0, min(1.0, value))
        row = dict(dec)
        row["retrieval_score_raw"] = dec.get("score")
        row["query_similarity"] = round(float(sims[idx]), 6)
        row["legal_anchor_score"] = round(anchor, 6)
        row["score"] = round(value, 6)
        scored.append(row)

    scored.sort(
        key=lambda d: (
            -float(d.get("score") or 0.0),
            -float(d.get("legal_anchor_score") or 0.0),
            str(d.get("decision_id") or ""),
        )
    )
    for rank, dec in enumerate(scored, start=1):
        dec["rank"] = rank

    product_bundle["decisions"] = scored
    prov = product_bundle.setdefault("provenance", {})
    prov["product_rerank"] = {
        "method": "local_legal_tfidf_v1",
        "query_variants_used": len(variants),
        "statute_anchors": [{"article": n, "code": c} for n, c in anchors],
        "top": [
            {
                "decision_id": d.get("decision_id"),
                "score": d.get("score"),
                "query_similarity": d.get("query_similarity"),
                "legal_anchor_score": d.get("legal_anchor_score"),
            }
            for d in scored[:10]
        ],
    }
    return product_bundle


__all__ = ["rerank_product_bundle", "clean_text", "decision_text"]
