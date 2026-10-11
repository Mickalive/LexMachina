"""End-to-end query pipeline: question -> bundle (retrieval, answer, counter, map)."""
from __future__ import annotations

import re
import time

from .answer import build_answer, counter_authority_pass
from .bundle import build_bundle
from .corpus import get_query_corpus
from .qmap import build_map, find_citations
from .retrieval import retrieve


def opencaselaw_url(decision_id: str, docket: str = "") -> str:
    q = docket or decision_id
    return f"https://opencaselaw.org/search?q={q}"


def run_query(query: str, top_n: int = 150, max_cites: int = 8) -> dict:
    t0 = time.time()
    query = (query or "").strip()
    if not query:
        raise ValueError("empty query")
    top_n = max(10, min(300, top_n))

    corpus, corpus_info = get_query_corpus(query, limit=50)
    ranked, variants = retrieve(query, corpus, top_n=top_n)

    answer = build_answer(query, ranked, max_cites=max_cites)

    texts = {d["decision_id"]: d.get("full_text", "") for d in corpus}
    counter_hits, counter_info = counter_authority_pass(query, ranked, texts)
    counter_by_id = {h["decision_id"]: h for h in counter_hits}

    mapped, clusters, relations = build_map(ranked)

    cited = set(answer["cited_decision_ids"])
    decisions = []
    for d in mapped:
        did = d["decision_id"]
        ch = counter_by_id.get(did)
        text = d.get("full_text", "") or ""
        snippet = re.sub(r"\s+", " ", text[:600]).strip()
        role = "supporting-candidate" if did in cited else "context"
        if ch:
            role = ch["counter_status"]
        decisions.append({
            "decision_id": did,
            "court": d.get("court", "?"),
            "language": d.get("language", "?"),
            "decision_date": d.get("decision_date", ""),
            "docket_number": d.get("docket_number", ""),
            "rank": d.get("rank"),
            "score": d.get("score"),
            "provenance": d.get("provenance", "?"),
            "snippet": snippet,
            "cluster_id": d.get("cluster_id"),
            "x": d.get("x"),
            "y": d.get("y"),
            "is_outlier": d.get("is_outlier", False),
            "counter_status": ch["counter_status"] if ch else ("cited" if did in cited else "none"),
            "counter_evidence": ch["evidence_sentence"] if ch else "",
            "counter_markers": ch["markers"] if ch else [],
            "canonical_url": d.get("canonical_url") or opencaselaw_url(did, d.get("docket_number", "")),
            "citation": (find_citations(text)[:3]),
        })

    bundle = build_bundle(
        query=query,
        query_variants=variants,
        answer=answer,
        decisions=decisions,
        clusters=clusters,
        relations=relations,
        provenance={
            "corpus": corpus_info,
            "answer_method": answer["method"],
            "counter": counter_info,
            "latency_seconds": round(time.time() - t0, 3),
            "bundle": "query_result_bundle v1.0",
        },
    )
    return bundle


__all__ = ["run_query"]
