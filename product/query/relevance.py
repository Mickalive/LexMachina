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
#: Bounded remote-index safeguard (same observed failure): when local lexical
#: evidence is silent (cross-language similarity below threshold) the blend
#: defers to the source index instead of vetoing it, but only for rows with
#: genuine remote support (upper half of remote scores), real text, and
#: federal-court standing — and the ceiling sits below the range where
#: discriminating local evidence lives.  Never demotes.
REMOTE_SAFEGUARD_SIM_THRESHOLD = 0.05
REMOTE_SAFEGUARD_WEIGHT = 0.22
REMOTE_SAFEGUARD_MIN_TEXT = 120
REMOTE_SAFEGUARD_MIN_REMOTE = 0.5
#: Remote-head recall (product reality leg 2026-10-16 petty-theft): the
#: bounded safeguard alone left bger_4A_177_2017 at rank 16 — still outside
#: the top-10 hydration/evidence packs, so the leg still failed.  The product
#: invariant is stronger than any score blend: a Federal Supreme Court row the
#: source index itself ranked top-5 must reach the generator.  After local
#: scoring, up to this many such rows sitting below the evidence head are
#: spliced into its tail (positions HEAD_RECALL_AT..10), preserving their
#: relative local order and pushing other rows down without reordering them.
#: Bounded by construction: at most 3 rows move, only federal courts qualify,
#: only when the index ranked them top-5, and rows already in the head are
#: never touched.  Rows the generator still ignores remain subject to the
#: citation-validation and adversarial passes downstream.
#:
#: Window widened 5 -> 15 (2026-10-16, business-judgment-rule leg): the five
#: frozen TF BJR authorities sit at remote ranks 12/13/14/17/31 with local
#: TF-IDF similarity 0.000-0.016 (French question vs German texts, no
#: statute anchor in the thin snippets), so the top-5 window recalled only
#: off-domain federal rows (remote 4/5) while every controlling authority
#: stayed below the hydration head and the answer cited none of them.  The
#: window stays inside the source index's first result page (page_size 25 at
#: top_n=100); every other bound (federal-only, max 3 moved, insert at 8..10,
#: head order preserved) is unchanged.
REMOTE_HEAD_RECALL_REMOTE_TOP = 15
REMOTE_HEAD_RECALL_LOCAL_HEAD = 10
REMOTE_HEAD_RECALL_MAX_MOVED = 3
REMOTE_HEAD_RECALL_INSERT_AT = 8
REMOTE_FEDERAL_COURTS = frozenset({"bger", "bge", "bstger"})
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

STOPWORDS = frozenset("""der die das und des den dem ein eine einer eines einem einen auch als bei nach noch nur oder vom von
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


def _variant_texts(raw_variants) -> tuple[list[str], list[str]]:
    """Extract search text from product-bundle query variants.

    Production bundles carry the accepted adapter's variant *dicts*
    (``{"variant_id": ..., "text": ..., "kind": ...}``); older fixtures and
    unit tests carry plain strings.  ``str()``-ing a dict injects Python-repr
    boilerplate (``variant_id``, ``kind``, hex digests, ``None`` ...) into the
    TF-IDF query document and dilutes the curated cross-language concept
    vocabulary — observed 2026-10-16 on the business-judgment-rule leg, where
    the German ``legal_concept`` variants were present but buried ~10x under
    repr noise while French lexical rows kept the evidence head.  Returns
    (texts, kinds) so provenance can record which variant kinds contributed.
    """
    texts: list[str] = []
    kinds: list[str] = []
    for v in raw_variants or []:
        if isinstance(v, dict):
            text = str(v.get("text") or "").strip()
            kind = str(v.get("kind") or "?")
        else:
            text = str(v or "").strip()
            kind = "text"
        if text:
            texts.append(text)
            kinds.append(kind)
    return texts, kinds


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


def _remote_head_recall(scored: list[dict]) -> list[dict]:
    """Federal rows the source index ranked inside the recall window but local
    scoring left below the evidence head.  Returned in current relative order
    (best local first), capped so displacement stays bounded."""
    raws = [
        (float(d.get("retrieval_score_raw"))
         if isinstance(d.get("retrieval_score_raw"), (int, float)) else 0.0)
        for d in scored
    ]
    order = sorted(range(len(scored)), key=lambda i: (-raws[i], i))
    remote_rank = {i: r + 1 for r, i in enumerate(order)}
    out = []
    for pos, dec in enumerate(scored):
        if pos < REMOTE_HEAD_RECALL_LOCAL_HEAD:
            continue
        if str(dec.get("court") or "").lower() not in REMOTE_FEDERAL_COURTS:
            continue
        if remote_rank[pos] > REMOTE_HEAD_RECALL_REMOTE_TOP:
            continue
        out.append({
            "pos": pos,
            "decision_id": dec.get("decision_id"),
            "from_rank": pos + 1,
            "remote_rank": remote_rank[pos],
        })
        if len(out) >= REMOTE_HEAD_RECALL_MAX_MOVED:
            break
    return out


def _apply_head_recall(scored: list[dict], recalls: list[dict]) -> list[dict]:
    """Splice recalled rows into the head tail, preserving relative order of
    every row.  No row is reordered except by the insertion shift."""
    moving = {r["pos"] for r in recalls}
    staying = [d for i, d in enumerate(scored) if i not in moving]
    insert_at = min(REMOTE_HEAD_RECALL_INSERT_AT - 1, len(staying))
    head, tail = staying[:insert_at], staying[insert_at:]
    moved_rows = [scored[r["pos"]] for r in recalls]
    for k, rec in enumerate(recalls):
        rec["to_rank"] = insert_at + k + 1
    out = head + moved_rows + tail
    for rank, dec in enumerate(out, start=1):
        dec["rank"] = rank
        dec["remote_head_recall"] = any(
            r["decision_id"] == dec.get("decision_id") for r in recalls
        )
    return out


def rerank_product_bundle(product_bundle: dict) -> dict:
    """Reorder decisions by query-conditioned local legal relevance.

    The adapter's remote score is retained as retrieval_score_raw. The
    product-facing score becomes a 0..1 relevance score used consistently
    for hydration, source packing and adversarial shortlisting.
    """
    decisions = list(product_bundle.get("decisions") or [])
    if not decisions:
        return product_bundle

    variants, variant_kinds = _variant_texts(product_bundle.get("query_variants"))
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
            0.82 * float(sims[idx])
            + 0.04 * float(raw_norm[idx])
            + 0.12 * anchor
            + 0.02 * federal
        )
        safeguard = (
            float(sims[idx]) < REMOTE_SAFEGUARD_SIM_THRESHOLD
            and float(raw_norm[idx]) >= REMOTE_SAFEGUARD_MIN_REMOTE
            and len(text) >= REMOTE_SAFEGUARD_MIN_TEXT
            and federal > 0.0
        )
        lifted = False
        if safeguard:
            floor = REMOTE_SAFEGUARD_WEIGHT * float(raw_norm[idx])
            if floor > value:
                value = floor
                lifted = True
        value = max(0.0, min(1.0, value))
        row = dict(dec)
        row["retrieval_score_raw"] = dec.get("score")
        row["query_similarity"] = round(float(sims[idx]), 6)
        row["legal_anchor_score"] = round(anchor, 6)
        row["remote_safeguard"] = bool(lifted)
        row["remote_head_recall"] = False
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

    recalls = _remote_head_recall(scored)
    if recalls:
        scored = _apply_head_recall(scored, recalls)

    product_bundle["decisions"] = scored
    prov = product_bundle.setdefault("provenance", {})
    prov["product_rerank"] = {
        "method": "local_legal_tfidf_v3_remote_head_recall",
        "query_variants_used": len(variants),
        "query_variant_kinds": sorted(set(variant_kinds)),
        "statute_anchors": [{"article": n, "code": c} for n, c in anchors],
        "remote_safeguard": {
            "sim_threshold": REMOTE_SAFEGUARD_SIM_THRESHOLD,
            "weight": REMOTE_SAFEGUARD_WEIGHT,
            "min_text": REMOTE_SAFEGUARD_MIN_TEXT,
            "min_remote": REMOTE_SAFEGUARD_MIN_REMOTE,
            "requires_federal_court": True,
            "n_lifted": sum(1 for d in scored if d.get("remote_safeguard")),
            "lifted_ids": [d.get("decision_id") for d in scored if d.get("remote_safeguard")],
        },
        "remote_head_recall": {
            "remote_top": REMOTE_HEAD_RECALL_REMOTE_TOP,
            "local_head": REMOTE_HEAD_RECALL_LOCAL_HEAD,
            "max_moved": REMOTE_HEAD_RECALL_MAX_MOVED,
            "insert_at": REMOTE_HEAD_RECALL_INSERT_AT,
            "moved": [
                {
                    "decision_id": m["decision_id"],
                    "from_rank": m["from_rank"],
                    "to_rank": m["to_rank"],
                    "remote_rank": m["remote_rank"],
                }
                for m in recalls
            ],
        },
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
