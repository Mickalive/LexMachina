"""Apply the FROZEN geometry rule to a candidate geometry bundle.

The rule itself is not reimplemented here: ``vendored.frontier_map_semantics``
is a byte-identical copy of the scorer that produced the accepted incumbent
verdict (frontier-served-packet-falsification, run 38880639079, accept commit
464c45f / frontier-map-semantics accept commit 15362f6).  Bars, baselines and
criterion order are unchanged; this module only feeds it a different set of
shipped fields (x/y/cluster_id/is_outlier/clusters), which is exactly what the
gate renders.
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from .vendored.frontier_map_semantics.metrics import tfidf_of, verdicts
from .vendored.frontier_map_semantics.textgeo import body, is_unhydrated

EXPECTED_RULES_SHA256 = (
    "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633"
)

CRITERIA_ORDER = [
    "COHERENCE_QUERY_LANG",
    "COHERENCE_QUERY_TERM",
    "PROJ_RANK",
    "PROJ_SPEARMAN",
    "PROJ_KNN10",
    "STRUCTURE_LARGEST",
    "STRUCTURE_SEP",
    "LABEL_CONTENT_FRACTION",
    "LABEL_JACCARD",
    "OUTLIER_VALIDITY",
    "RELATIONS",
]


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_rules(rules_path: str, *, expected_sha256: str = EXPECTED_RULES_SHA256) -> dict:
    with open(rules_path, "rb") as f:
        raw = f.read()
    observed = hashlib.sha256(raw).hexdigest()
    if observed != expected_sha256:
        raise ValueError(
            f"frozen geometry rule sha256 mismatch: expected {expected_sha256}, observed {observed}"
        )
    return json.loads(raw.decode("utf-8"))


def rule_block_for(rules_geom: dict, qid: str) -> dict:
    for e in rules_geom.get("inputs", []) or []:
        if e.get("bundle") == qid:
            lex = e.get("query_term_lexicon") or rules_geom.get("query_term_lexicons", {}).get(qid, [])
            return {"query_language": e.get("query_language") or qid[:2],
                    "query_term_lexicon": list(lex)}
    return {
        "query_language": "de" if qid.startswith("de-") else "fr" if qid.startswith("fr-") else "it",
        "query_term_lexicon": list(rules_geom.get("query_term_lexicons", {}).get(qid, [])),
    }


def frozen_inputs(bundle: dict) -> tuple[list[str], Any, Any]:
    """The rule's own reference vector space: built from ALL decision rows.

    Identical to geometry_half.run_geometry_half, so the X/qvec a variant is
    scored against is bit-for-bit the X/qvec the incumbent was scored against.
    """
    decisions = bundle["decisions"]
    texts = [body(d)[:6000] for d in decisions]
    if not any(t.strip() for t in texts):
        texts = [str(d.get("decision_id") or i) for i, d in enumerate(decisions)]
    vec, X = tfidf_of(texts)
    qvec = vec.transform([str(bundle.get("query", ""))])
    return texts, X, qvec


def score_bundle(candidate: dict, rules_bundle: dict) -> dict:
    """Frozen 11-criteria verdict on one candidate geometry bundle."""
    _texts, X, qvec = frozen_inputs(candidate)
    V, detail = verdicts(candidate, rules_bundle, X, qvec)
    n_pass = sum(1 for c in CRITERIA_ORDER if V[c]["pass"])
    return {
        "criteria": {c: _jsonable(V[c]) for c in CRITERIA_ORDER},
        "n_pass": n_pass,
        "n_criteria": len(CRITERIA_ORDER),
        "overall": "PASS" if n_pass == len(CRITERIA_ORDER) else "FAIL",
        "detail": _jsonable(detail),
    }


def largest_share_both_definitions(candidate: dict) -> dict[str, Any]:
    """Largest-cluster share from BOTH the size field and len(member_ids).

    Vendored logic of geometry_half._largest_share_both_definitions (accepted
    run 38880639079); kept so the 50-cap truncation contract stays visible.
    """
    decisions = candidate.get("decisions") or []
    clusters = candidate.get("clusters") or []
    n = max(1, len(decisions))
    if not clusters:
        return {"largest_share_size_field": 0.0, "largest_share_member_ids": 0.0,
                "member_ids_capped_at_50": False, "max_member_ids_len": 0,
                "n_decisions": len(decisions)}
    by_size = max(clusters, key=lambda c: int(c.get("size") or 0))
    by_members = max(clusters, key=lambda c: len(c.get("member_ids") or []))
    max_members = max(len(c.get("member_ids") or []) for c in clusters)
    return {
        "largest_share_size_field": int(by_size.get("size") or 0) / n,
        "largest_share_member_ids": len(by_members.get("member_ids") or []) / n,
        "largest_size_field": int(by_size.get("size") or 0),
        "largest_member_ids_len": len(by_members.get("member_ids") or []),
        "largest_cluster_id_size_field": int(by_size.get("cluster_id") or -1),
        "member_ids_capped_at_50": bool(max_members >= 50),
        "max_member_ids_len": int(max_members),
        "n_decisions": len(decisions),
    }


def dominant_cluster_context(candidate: dict, query_language: str) -> dict[str, Any]:
    """Read-only context for the dominant (largest) cluster."""
    decisions = candidate.get("decisions") or []
    clusters = candidate.get("clusters") or []
    if not clusters:
        return {}
    dom = max(clusters, key=lambda c: int(c.get("size") or 0))
    dom_cid = int(dom.get("cluster_id") or -1)
    members = [d for d in decisions if int(d.get("cluster_id") or -1) == dom_cid]
    n_m = max(1, len(members))
    lang_counts: dict[str, int] = {}
    for d in members:
        lang = str(d.get("language") or "null")
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
    counter_statuses = ("candidate-limiting", "candidate-contrary", "contrary_or_exception", "limiting")
    return {
        "cluster_id": dom_cid,
        "size_field": int(dom.get("size") or 0),
        "member_ids_len": len(dom.get("member_ids") or []),
        "label": str(dom.get("label") or ""),
        "language_mix": dict(sorted(lang_counts.items())),
        "n_query_language": lang_counts.get(query_language, 0),
        "share_query_language": lang_counts.get(query_language, 0) / n_m,
        "n_counter_rows_contained": sum(
            1 for d in members if d.get("counter_status") in counter_statuses
        ),
        "n_unclustered_shells_in_dominant": sum(
            1 for d in members if bool(d.get("unclustered"))
        ),
    }


def _jsonable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, float):
        if obj != obj:  # NaN
            return None
        return obj
    if hasattr(obj, "item"):
        try:
            return _jsonable(obj.item())
        except Exception:
            return str(obj)
    return obj


def score_variant(
    rules_path: str,
    packet_questions_dir: str,
    qids: list[str],
    expected_shas: dict[str, str],
    variant_fn,
    *,
    query_language_of: dict[str, str],
) -> dict[str, Any]:
    """Score one variant across all served bundles."""
    rules_geom = load_rules(rules_path)
    out: dict[str, Any] = {"bundles": []}
    for qid in sorted(qids):
        path = os.path.join(packet_questions_dir, f"{qid}.bundle.json")
        digest = sha256_file(path)
        expected = expected_shas[qid]
        if digest != expected:
            raise ValueError(f"input sha256 drift for {path}: expected {expected}, observed {digest}")
        with open(path, "rb") as f:
            bundle = json.loads(f.read().decode("utf-8"))
        candidate = variant_fn(bundle, query_language=query_language_of[qid])
        rules_bundle = rule_block_for(rules_geom, qid)
        scored = score_bundle(candidate, rules_bundle)
        out["bundles"].append({
            "qid": qid,
            "sha256": digest,
            "n_decisions": len(bundle["decisions"]),
            "n_clusters": len(candidate.get("clusters") or []),
            "n_relations": len(candidate.get("relations") or []),
            "query": bundle.get("query", ""),
            "query_language": rules_bundle["query_language"],
            "criteria": scored["criteria"],
            "n_pass": scored["n_pass"],
            "n_criteria": scored["n_criteria"],
            "overall": scored["overall"],
            "largest_share_both_definitions": largest_share_both_definitions(candidate),
            "dominant_cluster_context": dominant_cluster_context(
                candidate, rules_bundle["query_language"]
            ),
            "geometry_seconds": (candidate.get("geometry_variant") or {}).get("geometry_seconds"),
            "variant_meta": candidate.get("geometry_variant"),
        })
    out["n_bundles_pass"] = sum(1 for b in out["bundles"] if b["overall"] == "PASS")
    out["total_criteria_passed"] = sum(b["n_pass"] for b in out["bundles"])
    return out
