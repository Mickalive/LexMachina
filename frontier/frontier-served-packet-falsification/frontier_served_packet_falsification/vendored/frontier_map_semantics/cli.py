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


def _same_value(a, b):
    """NaN-aware structural equality for criterion values.

    A plain `!=` reports an UNCHANGED degenerate criterion (value NaN on both
    sides) as moved, because NaN != NaN. That would silently inflate the
    movability audit exactly on the degenerate bundles the charter cares about
    (charter-1 RF2). Found by test_movability_is_measured_not_asserted.
    """
    import math

    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_same_value(x, y) for x, y in zip(a, b))
    if isinstance(a, float) or isinstance(b, float):
        try:
            fa, fb = float(a), float(b)
        except (TypeError, ValueError):
            return a == b
        if math.isnan(fa) and math.isnan(fb):
            return True
        return fa == fb
    return a == b


def heal(bundle, rules_bundle):
    """POSITIVE CONTROL (added and declared in cycle 38846038296; additive).

    A deliberately GOOD geometry, used only to prove that the criteria which FAIL
    on the shipped geometry are REACHABLE, i.e. that the observed FAILs are a
    property of the shipped geometry and not of an unreachable bar.

    Same rows, same x/y, same cluster labels, same relations, same outlier flags;
    ONLY the cluster_id assignment changes: rows are sorted by
    (query-language match DESC, query-term hit DESC, decision_id ASC) and the
    sorted order is cut into the SHIPPED cluster size profile, largest shipped
    cluster first. Deterministic: no RNG and therefore no seed to re-draw.

    This is NOT a corruption, NOT a candidate geometry and NOT an alternative; it
    never feeds `overall`, never feeds the promoted decision and is reported under
    its own key so the frozen control's own `passed` flag stays untouched.
    """
    import copy

    from .textgeo import body

    b = copy.deepcopy(bundle)
    decs = b["decisions"]
    qlang = rules_bundle["query_language"]
    lex = [str(x).casefold() for x in (rules_bundle.get("query_term_lexicon") or [])]

    def _key(d):
        lang_match = d.get("language") == qlang
        term_hit = any(q in body(d).casefold() for q in lex)
        return (not lang_match, not term_hit, str(d.get("decision_id")))

    order = sorted(decs, key=_key)
    clusters = b.get("clusters", []) or []
    by_size = sorted(clusters, key=lambda c: (-int(c.get("size", 0)), int(c["cluster_id"])))
    i = 0
    for c in by_size:
        cid = int(c["cluster_id"])
        for d in order[i:i + int(c.get("size", 0))]:
            d["cluster_id"] = cid
        i += int(c.get("size", 0))
    tail = int(by_size[-1]["cluster_id"]) if by_size else 0
    for d in order[i:]:
        d["cluster_id"] = tail
    for c in clusters:
        cid = int(c["cluster_id"])
        c["member_ids"] = [d.get("decision_id") for d in decs if int(d["cluster_id"]) == cid][:50]
        c["size"] = sum(1 for d in decs if int(d["cluster_id"]) == cid)
    return b


def nonvacuity(bundle, rules_bundle, X, qvec):
    from .metrics import verdicts

    V0, _ = verdicts(bundle, rules_bundle, X, qvec)
    out = {}
    for mode in ("charter", "full"):
        b = corrupt(bundle, mode)
        # X rows correspond to original row order; corruption only reorders
        # labels/coords, texts unchanged, so X and qvec are still valid.
        Vc, _ = verdicts(b, rules_bundle, X, qvec)
        flips = [c for c in CRITERIA_ORDER if bool(V0[c]["pass"]) != bool(Vc[c]["pass"])]
        # Which criteria the control can even MOVE (value actually changes), as
        # opposed to which verdicts flipped. Measured, not asserted (RF4): a
        # criterion whose value is identical before and after is invariant under
        # this control and cannot contribute a flip. NaN-aware (see _same_value).
        value_changed = [c for c in CRITERIA_ORDER
                         if not _same_value(Vc[c]["value"], V0[c]["value"])]
        out[mode] = {"flips": flips, "n_flips": len(flips),
                     "corrupted_overall": "PASS" if overall(Vc) else "FAIL",
                     "corrupted_criteria": {c: bool(Vc[c]["pass"]) for c in CRITERIA_ORDER},
                     "corrupted_values": {c: Vc[c]["value"] for c in CRITERIA_ORDER},
                     "original_criteria": {c: bool(V0[c]["pass"]) for c in CRITERIA_ORDER},
                     "original_values": {c: V0[c]["value"] for c in CRITERIA_ORDER},
                     "movable_criteria": value_changed,
                     "n_movable_criteria": len(value_changed),
                     "n_invariant_criteria": len(CRITERIA_ORDER) - len(value_changed)}
    best = max(out[m]["n_flips"] for m in ("charter", "full"))
    out["passed"] = bool(best >= 2 and any(out[m]["corrupted_overall"] == "FAIL" for m in ("charter", "full")))
    out["movability_note"] = (
        "MEASURED per control, not asserted: a criterion appears in `movable_criteria` "
        "iff its emitted value differs between the shipped geometry and the corrupted one. "
        "Under the frozen C-charter control (cluster ids permuted across rows + labels "
        "permuted across cluster ids) only COHERENCE_QUERY_LANG, COHERENCE_QUERY_TERM and "
        "STRUCTURE_SEP can move; the other 8 read only x/y, the pooled label multiset, the "
        "cluster-size multiset, the relation list or the outlier flags, all of which that "
        "permutation provably preserves. The frozen >=2-flip assertion is therefore capped "
        "at 3 achievable flips and cannot be met by any permutation control on a geometry "
        "that already fails those axes."
    )
    try:
        Vh, _ = verdicts(heal(bundle, rules_bundle), rules_bundle, X, qvec)
        hflips = [c for c in CRITERIA_ORDER if bool(V0[c]["pass"]) != bool(Vh[c]["pass"])]
        # The positive control is an UPPER BOUND construction: it puts every
        # query-language (resp. query-term-hit) row inside the largest shipped
        # cluster, so its share is the maximum attainable under ANY partition of
        # these rows into a cluster of that size. Recording the bound explicitly
        # makes "reachable" vs "provably unreachable" machine-checkable instead
        # of asserted.
        from .textgeo import body

        decs = bundle["decisions"]
        qlang = rules_bundle["query_language"]
        lex = [str(x).casefold() for x in (rules_bundle.get("query_term_lexicon") or [])]
        dom_size = max((int(c.get("size", 0)) for c in (bundle.get("clusters") or [])), default=1)
        dom_size = max(1, dom_size)
        n_lang = sum(1 for d in decs if d.get("language") == qlang)
        n_term = sum(1 for d in decs
                     if any(q in body(d).casefold() for q in lex))
        max_lang = min(1.0, n_lang / dom_size)
        max_term = min(1.0, n_term / dom_size)
        out["positive_control"] = {
            "note": ("DECLARED ADDITION, cycle 38846038296. Positive control (see heal()): "
                     "cluster ids re-assigned by query-language/query-term relevance into the "
                     "shipped size profile; no RNG. It is not a corruption, not a candidate "
                     "geometry and not an alternative. It exists to show the criteria that FAIL "
                     "on the shipped geometry can PASS, i.e. the FAILs are about the shipped "
                     "geometry rather than about unreachable bars. It feeds no verdict: `overall`, "
                     "`passed`, the criterion table, the ablation, the alternatives and "
                     "DECISION.txt are all computed without it."),
            "control_kind": "positive_control_not_corruption",
            "flips": hflips, "n_flips": len(hflips),
            "overall": "PASS" if overall(Vh) else "FAIL",
            "criteria": {c: bool(Vh[c]["pass"]) for c in CRITERIA_ORDER},
            "values": {c: Vh[c]["value"] for c in CRITERIA_ORDER},
            "max_reachable_query_lang_share": max_lang,
            "max_reachable_query_term_share": max_term,
            "coherence_lang_reachable": bool(max_lang >= V0["COHERENCE_QUERY_LANG"]["bar"]),
            "coherence_term_reachable": bool(max_term >= V0["COHERENCE_QUERY_TERM"]["bar"]),
            "n_rows_query_language": n_lang,
            "n_rows_query_term_hit": n_term,
            "dominant_cluster_size": dom_size,
            "n_decisions": len(decs),
            "passed": bool(len(hflips) >= 2),
        }
    except Exception as e:  # a positive control must never kill the harness
        out["positive_control"] = {"error": f"{type(e).__name__}: {e}", "n_flips": 0,
                                   "passed": False}
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
                      "nonvacuity_movable": {m: rep["nonvacuity"][m]["n_movable_criteria"]
                                             for m in ("charter", "full")},
                      "nonvacuity_positive_control_flips":
                          rep["nonvacuity"]["positive_control"]["n_flips"],
                      "nonvacuity_positive_control_passed":
                          rep["nonvacuity"]["positive_control"]["passed"],
                      "alternatives_best": alt_best},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
