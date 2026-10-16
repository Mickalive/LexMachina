"""Offline harness: recompute map metrics from a bundle's own texts.

Usage:
  PYTHONPATH=frontier/frontier-map-semantics python -m frontier_map_semantics.cli \
      --bundle <path> --out <dir> --rules <RULES.json> [--run-id 38839351403]
  python -m frontier_map_semantics.cli --frozen-rules --rules <RULES.json>

Network calls: zero. Deterministic: identical inputs yield byte-identical
report.json (no timestamps; floats from fixed-seed pipelines).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

CRITERIA_ORDER = ["COHERENCE_QUERY_LANG", "COHERENCE_QUERY_TERM", "PROJ_RANK",
                  "PROJ_SPEARMAN", "PROJ_KNN10", "STRUCTURE_LARGEST",
                  "STRUCTURE_SEP", "LABEL_CONTENT_FRACTION", "LABEL_JACCARD",
                  "OUTLIER_VALIDITY", "RELATIONS"]


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def overall(V):
    return all(V[c]["pass"] for c in CRITERIA_ORDER)


def run_bundle(bundle_path, rules_bundle, out_dir, run_id):
    from .metrics import ablate, tfidf_of, verdicts
    from .textgeo import body

    bundle = json.load(open(bundle_path))
    decisions = bundle["decisions"]
    texts = [body(d)[:6000] for d in decisions]
    if not any(t.strip() for t in texts):
        texts = [str(d.get("decision_id") or i) for i, d in enumerate(decisions)]
    vec, X = tfidf_of(texts)
    qtext = str(bundle.get("query", ""))
    qvec = vec.transform([qtext])
    V, detail = verdicts(bundle, rules_bundle, X, qvec)
    side, g_all, g_hyd = ablate(bundle, rules_bundle, X=X, qvec=qvec)
    ctrl = nonvacuity(bundle, rules_bundle, X, qvec)
    report = {
        "run_id": run_id,
        "bundle_path": bundle_path,
        "bundle_file_sha256": sha256_file(bundle_path),
        "n_decisions": len(decisions),
        "n_clusters": len(bundle.get("clusters", []) or []),
        "n_relations": len(bundle.get("relations", []) or []),
        "query": bundle.get("query", ""),
        "query_language": rules_bundle["query_language"],
        "criteria": {c: V[c] for c in CRITERIA_ORDER},
        "overall": "PASS" if overall(V) else "FAIL",
        "detail": detail,
        "ablation": side,
        "nonvacuity": ctrl,
    }
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "report.json", "w") as f:
        json.dump(report, f, ensure_ascii=False, sort_keys=True, indent=1)
    return report


def corrupt(bundle, mode, seed=0):
    """Deliberately corrupted geometry. C-charter: permute cluster ids across
    rows (sizes preserved) + permute label texts across cluster ids.
    C-full: C-charter + permute coordinates across rows."""
    import copy

    rng = np.random.RandomState(seed)
    b = copy.deepcopy(bundle)
    decs = b["decisions"]
    ids = [int(d.get("cluster_id")) for d in decs]
    perm = rng.permutation(len(decs))
    shuffled_ids = [ids[i] for i in perm]
    for d, c in zip(decs, shuffled_ids):
        d["cluster_id"] = int(c)
    clusters = b.get("clusters", []) or []
    labels = [str(c.get("label") or "") for c in clusters]
    plabels = [labels[i] for i in rng.permutation(len(labels))] if labels else []
    for c, lb in zip(clusters, plabels):
        c["label"] = lb
    # rebuild member_ids + sizes from shuffled assignment
    for c in clusters:
        cid = int(c["cluster_id"])
        c["member_ids"] = [d.get("decision_id") for d in decs if int(d.get("cluster_id")) == cid][:50]
        c["size"] = sum(1 for d in decs if int(d.get("cluster_id")) == cid)
    if mode == "full":
        xs = [d.get("x") for d in decs]
        ys = [d.get("y") for d in decs]
        px = [xs[i] for i in rng.permutation(len(decs))]
        py = [ys[i] for i in rng.permutation(len(decs))]
        for d, x, y in zip(decs, px, py):
            d["x"], d["y"] = x, y
    return b


def nonvacuity(bundle, rules_bundle, X, qvec):
    from .metrics import verdicts

    decisions = bundle["decisions"]
    V0, _ = verdicts(bundle, rules_bundle, X, qvec)
    out = {}
    for mode in ("charter", "full"):
        b = corrupt(bundle, mode)
        # X rows correspond to original row order; corruption only reorders
        # labels/coords, texts unchanged, so X and qvec are still valid.
        Vc, _ = verdicts(b, rules_bundle, X, qvec)
        flips = [c for c in CRITERIA_ORDER if bool(V0[c]["pass"]) != bool(Vc[c]["pass"])]
        out[mode] = {"flips": flips, "n_flips": len(flips),
                     "corrupted_overall": "PASS" if overall(Vc) else "FAIL",
                     "corrupted_criteria": {c: bool(Vc[c]["pass"]) for c in CRITERIA_ORDER},
                     "corrupted_values": {c: Vc[c]["value"] for c in CRITERIA_ORDER},
                     "original_criteria": {c: bool(V0[c]["pass"]) for c in CRITERIA_ORDER}}
    best = max(out[m]["n_flips"] for m in out)
    out["passed"] = bool(best >= 2 and any(out[m]["corrupted_overall"] == "FAIL" for m in out))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--rules", default=None)
    ap.add_argument("--run-id", default="38839351403")
    ap.add_argument("--frozen-rules", action="store_true")
    ap.add_argument("--bundle-key", default=None,
                    help="key into RULES inputs/additional_bundle selecting lexicon/language")
    ap.add_argument("--alternatives", action="store_true",
                    help="also evaluate A1/A2/A3 under the identical frozen rule "
                         "(§9A < 2 s) and write <out>/alternatives.json")
    args = ap.parse_args(argv)
    if args.frozen_rules:
        rules = json.load(open(args.rules))
        print(json.dumps({"criteria": rules["criteria"],
                          "query_term_lexicons": rules["query_term_lexicons"],
                          "non_vacuity": rules["non_vacuity"],
                          "decisive_ablation": rules["decisive_ablation"]},
                         ensure_ascii=False, sort_keys=True, indent=1))
        return 0
    rules = json.load(open(args.rules))
    if args.bundle_key == "additional":
        rb = {"query_language": rules["additional_bundle"]["query_language"],
              "query_term_lexicon": rules["additional_bundle"]["query_term_lexicon"]}
    else:
        match = [i for i in rules["inputs"] if i["bundle"] == args.bundle_key]
        if not match:
            print(f"unknown --bundle-key {args.bundle_key}", file=sys.stderr)
            return 2
        m = match[0]
        lex = rules["query_term_lexicons"].get(args.bundle_key, [])
        rb = {"query_language": m["query_language"], "query_term_lexicon": lex}
    rep = run_bundle(args.bundle, rb, args.out, args.run_id)
    alt_best = None
    if args.alternatives:
        from .alt_eval import evaluate

        bundle = json.load(open(args.bundle))
        alts = evaluate(bundle, rb)
        alt_best = alts.get("best")
        with open(Path(args.out) / "alternatives.json", "w") as f:
            json.dump(alts, f, ensure_ascii=False, sort_keys=True, indent=1)
    print(json.dumps({"overall": rep["overall"],
                      "criteria": {c: rep["criteria"][c]["pass"] for c in CRITERIA_ORDER},
                      "ARTIFACT": rep["ablation"]["ARTIFACT"],
                      "nonvacuity_passed": rep["nonvacuity"]["passed"],
                      "alternatives_best": alt_best},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
