"""Alternative-geometry evaluation under the identical frozen rule + §9A budget."""
from __future__ import annotations

import numpy as np

from . import alternatives as ALT
from .metrics import tfidf_of, verdicts
from .textgeo import body, is_unhydrated


def _alt_bundle(bundle, g, ids):
    hyd = [d for d in bundle["decisions"] if d.get("decision_id") in set(ids)]
    id2i = {cid: i for i, cid in enumerate(ids)}
    coords = np.asarray(g["coords"], dtype=float)
    cids = [int(x) for x in g["cluster_ids"]]
    flags = [bool(x) for x in g["is_outlier"]]
    labels = {int(c["cluster_id"]): str(c.get("label") or "") for c in g["clusters"]}
    decs = []
    for d in hyd:
        i = id2i[d["decision_id"]]
        decs.append({**d, "x": round(float(coords[i, 0]), 4),
                     "y": round(float(coords[i, 1]), 4),
                     "cluster_id": cids[i], "is_outlier": flags[i]})
    clusters = []
    for c in g["clusters"]:
        cid = int(c["cluster_id"])
        members = [d["decision_id"] for d in decs if int(d["cluster_id"]) == cid]
        clusters.append({"cluster_id": cid, "label": labels[cid],
                         "size": len(members), "member_ids": members[:50]})
    keep = {d["decision_id"] for d in decs}
    rels = [r for r in (bundle.get("relations", []) or [])
            if r.get("source") in keep and r.get("target") in keep]
    return {"decisions": decs, "clusters": clusters, "relations": rels,
            "query": bundle.get("query", "")}


def evaluate(bundle, rules_bundle):
    from .cli import CRITERIA_ORDER, overall

    decisions = bundle["decisions"]
    hyd = [d for d in decisions if not is_unhydrated(d)]
    texts = [body(d)[:6000] for d in hyd]
    ids = [d.get("decision_id") for d in hyd]
    if not any(t.strip() for t in texts):
        texts = [str(i) for i in ids]
    langs = [d.get("language") for d in hyd]
    vec, X = tfidf_of(texts)
    qvec = vec.transform([str(bundle.get("query", ""))])
    out = {}
    builders = {"A1_drop_unhydrated": lambda: ALT.alt_A1(texts, ids),
                "A2_language_aware_tfidf": lambda: ALT.alt_A2(texts, ids, langs),
                "A3_mds_cosine": lambda: ALT.alt_A3(texts, ids)}
    for name, build in builders.items():
        try:
            g = build()
            ab = _alt_bundle(bundle, g, ids)
            V, _detail = verdicts(ab, rules_bundle, X, qvec)
            out[name] = {"elapsed_s": g["elapsed"], "within_budget": bool(g["elapsed"] < 2.0),
                         "criteria": {c: bool(V[c]["pass"]) for c in CRITERIA_ORDER},
                         "overall": "PASS" if overall(V) else "FAIL",
                         "values": {c: (V[c]["value"] if not isinstance(V[c]["value"], list) else V[c]["value"]) for c in CRITERIA_ORDER},
                         "error": None}
        except Exception as e:  # never let an alternative kill the harness
            out[name] = {"elapsed_s": None, "within_budget": False, "criteria": {},
                         "overall": "ERROR", "values": {}, "error": f"{type(e).__name__}: {e}"}
    passing = [n for n, r in out.items() if r["overall"] == "PASS" and r["within_budget"]]
    out["best"] = passing[0] if passing else None
    return out
