"""Explicit degraded fallback for the v45 query product.

The normal path is generative-audit contract 2.2: source-constrained generation
followed by a separate adversarial model pass. This module is used only when
no generative provider succeeds, so the UI remains useful without pretending
that the fallback is the target product behavior.

Fallback answer: extracts source sentences and cites only retrieved IDs.
Fallback counter pass: lexical DE/FR/IT exception/limitation retrieval; these
are candidate signals rather than model-verified legal classifications.
"""
from __future__ import annotations

import re

from .retrieval import tfidf_scores, tokenize

SENT_SPLIT = re.compile(r"(?<=[.!?;])\s+(?=[A-ZÄÖÜÉÈÊA-Z0-9«\"'])")

ADVERSARIAL_TERMS = [
    # DE
    "ausnahme", "einschränkung", "entgegen", "abweichend", "minderheit",
    "vorbehalt", "jedoch", "dennoch", "abgelehnt", "abgewiesen", "nicht",
    "unbegründet", "unzulässig", "ausschluss", "eng auszulegen",
    # FR
    "exception", "contraire", "limitatif", "rejeté", "irrecevable",
    "minorité", "toutefois", "néanmoins", "écarté", "réservé",
    # IT
    "eccezione", "contrario", "respinto", "irricevibile", "minoranza",
    "tuttavia", "riserva",
]


def split_sentences(text: str, max_len: int = 600) -> list[str]:
    parts = SENT_SPLIT.split((text or "").replace("\n", " "))
    return [p.strip()[:max_len] for p in parts if len(p.strip()) > 40][:400]


def build_answer(query: str, ranked: list[dict], max_cites: int = 8) -> dict:
    qtoks = set(tokenize(query))
    cands: list[tuple[float, str, str]] = []  # (cover, sentence, decision_id)
    for d in ranked[:40]:
        for s in split_sentences(d.get("full_text") or d.get("regeste") or d.get("snippet") or ""):
            stoks = set(tokenize(s))
            overlap = len(qtoks & stoks)
            if overlap == 0:
                continue
            # coverage density + mild preference for higher-ranked decisions
            score = overlap / (1 + len(stoks) / 60.0) + 0.05 * max(0.0, 1.0 - d.get("rank", 50) / 40.0)
            cands.append((score, s, d["decision_id"]))
    cands.sort(key=lambda t: -t[0])
    picked: list[dict] = []
    used: set[str] = set()
    for score, sent, did in cands:
        if did in used and len(used) >= 3:
            continue
        # skip near-duplicate sentences
        if any(_jaccard(sent, p["text"]) > 0.7 for p in picked):
            continue
        picked.append({"text": sent, "decision_id": did, "relevance": round(score, 4)})
        used.add(did)
        if len(picked) >= max_cites:
            break
    cited = sorted({p["decision_id"] for p in picked})
    if picked:
        prose = ("Zur Anfrage finden sich in den abgerufenen Entscheiden u.a. folgende "
                 "relevante Stellen (Extrakt, keine Rechtsberatung):\n" +
                 "\n".join(f"[{i+1}] ({p['decision_id']}) {p['text']}" for i, p in enumerate(picked)))
    else:
        prose = ("Zu dieser Anfrage fand die breite Abfrage keine direkt zitierfähige "
                 "Stelle im abgerufenen Bestand. Bitte Anfrage präzisieren oder Bestand erweitern.")
    return {
        "prose": prose,
        "statements": picked,
        "cited_decision_ids": cited,
        "method": "extractive_tfidf_v1",
        "model": "none-local-extractive",
    }


def _jaccard(a: str, b: str) -> float:
    sa, sb = set(tokenize(a)), set(tokenize(b))
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def counter_authority_pass(query: str, ranked: list[dict], corpus_texts: dict[str, str],
                            top_k: int = 12) -> tuple[list[dict], dict]:
    """Independent adversarial retrieval. Returns (counter_hits, info).

    corpus_texts: decision_id -> full_text for the whole query corpus.
    Counter candidates are decisions whose text matches adversarial vocabulary
    AND the query topic, preferring ones NOT top-ranked by the initial search
    (minority/low-ranked lines stay visible).
    """
    adv_q = query + " " + " ".join(ADVERSARIAL_TERMS)
    ids = list(corpus_texts.keys())
    docs = [(corpus_texts[i] or "")[:8000] for i in ids]
    order, scores = tfidf_scores(adv_q, docs)
    initial_rank = {d["decision_id"]: d.get("rank", 10**9) for d in ranked}
    hits = []
    for idx in order:
        did = ids[idx]
        if scores[idx] <= 0:
            break
        text = corpus_texts[did]
        # evidence: which adversarial markers actually occur
        low = text.lower()
        markers = sorted({t for t in ADVERSARIAL_TERMS if t in low})
        if not markers:
            continue
        sents = [s for s in split_sentences(text)
                 if any(m in s.lower() for m in markers[:8])]
        hits.append({
            "decision_id": did,
            "adversarial_score": round(scores[idx], 6),
            "initial_rank": initial_rank.get(did),
            "was_low_ranked": initial_rank.get(did, 10**9) > 20,
            "markers": markers[:6],
            "evidence_sentence": sents[0][:400] if sents else "",
            "counter_status": "candidate-limiting",
        })
        if len(hits) >= top_k:
            break
    info = {
        "method": "independent_adversarial_tfidf_v1",
        "n_candidates": len(hits),
        "n_low_ranked_rescued": sum(1 for h in hits if h["was_low_ranked"]),
    }
    return hits, info
