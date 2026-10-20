"""Non-vacuity: seeded controls proving the harness can move and both verdicts
are reachable.

Charter acceptance test (4): prove at least two criteria/verdicts can move
under a seeded control, and prove the harness can output BOTH a serve and a
do-not-serve outcome (negative control).

Controls:
  * geometry permutation (seed 0): permute cluster_id across rows + permute
    label texts across cluster ids; recompute all 11 criteria; corrupted
    geometry must flip >= 2 criteria verdicts.
  * label injection battery (frozen, from RULES_LABEL.non_vacuity): every
    injected row must be assigned its frozen expected_class, exercising >= 2
    distinct defect criteria; injected rows are excluded from the population
    support rate and the verdict.
  * verdict reachability: a seeded SERVE control (a synthetic packet that
    passes both bars) and a seeded DO-NOT-SERVE control (the real v3 bytes)
    must both be reachable by the same decide() call path.
"""
from __future__ import annotations

import copy
import random
from typing import Any

from .geometry_gate import CRITERIA_ORDER, bundle_pass_count, score_bundle
from .verdict import decide


def _corrupt(bundle: dict, mode: str) -> dict:
    """Deliberately corrupted geometry (seed 0).

    C-charter: permute cluster ids across rows + permute label texts across
    cluster ids. C-full: C-charter + permute x/y coordinates across rows.
    PRNG: CPython random.Random(0) shuffles (seed 0 per frozen rule).
    """
    rng = random.Random(0)
    b = copy.deepcopy(bundle)
    decs = b.get("decisions") or []
    ids = [d.get("cluster_id") for d in decs]
    order = list(range(len(decs)))
    rng.shuffle(order)
    for d, i in zip(decs, order):
        d["cluster_id"] = ids[i]
    clusters = b.get("clusters", []) or []
    labels = [c.get("label") for c in clusters]
    lorder = list(range(len(labels)))
    rng.shuffle(lorder)
    for c, i in zip(clusters, lorder):
        c["label"] = labels[i]
    for c in clusters:
        cid = int(c["cluster_id"])
        c["member_ids"] = [d.get("decision_id") for d in decs if int(d.get("cluster_id")) == cid][:50]
        c["size"] = sum(1 for d in decs if int(d.get("cluster_id")) == cid)
    if mode == "full":
        xs = [d.get("x") for d in decs]
        ys = [d.get("y") for d in decs]
        xorder = list(range(len(decs)))
        rng.shuffle(xorder)
        yorder = list(range(len(decs)))
        rng.shuffle(yorder)
        for d, i, j in zip(decs, xorder, yorder):
            d["x"], d["y"] = xs[i], ys[j]
    return b


def _overall(V: dict) -> bool:
    return all(bool(V[c]["pass"]) for c in CRITERIA_ORDER)


def geometry_non_vacuity_control(bundle: dict, query_language: str, lexicon: list[str]) -> dict:
    v0, _ = score_bundle(bundle, query_language, lexicon)
    out: dict = {}
    for mode in ("charter", "full"):
        corrupted = _corrupt(bundle, mode)
        vc, _ = score_bundle(corrupted, query_language, lexicon)
        flips = [c for c in CRITERIA_ORDER if bool(v0[c]["pass"]) != bool(vc[c]["pass"])]
        out[mode] = {"flips": flips, "n_flips": len(flips),
                     "corrupted_overall": "PASS" if _overall(vc) else "FAIL"}
    best = max(out[m]["n_flips"] for m in ("charter", "full"))
    proven = bool(best >= 2 and any(out[m]["corrupted_overall"] == "FAIL" for m in ("charter", "full")))
    out["required_min_flips"] = 2
    out["best_n_flips"] = best
    out["proven_non_vacuous"] = proven
    out["prng"] = "CPython random.Random(0).shuffle streams (seed 0 per frozen rule)"
    return out


def label_injection_control(rules) -> dict:
    """The frozen injection battery from RULES_LABEL.non_vacuity."""
    from .vendor_label.injection import run_non_vacuity
    result = run_non_vacuity(rules)
    cases = result.get("cases", [])
    n_pass = sum(1 for c in cases if c.get("pass"))
    return {
        "control": "frozen injection battery from RULES_LABEL.non_vacuity",
        "n_cases": len(cases),
        "n_cases_pass": n_pass,
        "exercised_classes": result.get("defect_criteria_exercised", []),
        "min_criteria_flagged_required": result.get("min_criteria_flagged"),
        "proven_non_vacuous": bool(result.get("passed", False)),
    }


def verdict_reachability_control() -> dict:
    """Prove the harness can output BOTH a SERVE and a DO-NOT-SERVE outcome.

    SERVE control: a synthetic label/geometry/marginal measurement that passes
    both bars. DO-NOT-SERVE control: the real v3 measurement shape (both bars
    unmet, no marginal discovery). Both go through the same decide() path.
    """
    serve_label = {"absolute_status": "LABEL_SOUND"}
    serve_geom = {"absolute_status": "GEOMETRY_SOUND",
                  "per_bundle": {qid: {"mega_cluster": {"disclosure_fires": True}}
                                 for qid in ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica")}}
    serve_marginal = {"map_adds_marginal_discovery_on_packet": False}
    serve = decide(serve_label, serve_geom, serve_marginal)

    dns_label = {"absolute_status": "LABEL_UNSOUND"}
    dns_geom = {"absolute_status": "GEOMETRY_UNSOUND",
                "per_bundle": {qid: {"mega_cluster": {"disclosure_fires": True}}
                               for qid in ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica")}}
    dns_marginal = {"map_adds_marginal_discovery_on_packet": False}
    dns = decide(dns_label, dns_geom, dns_marginal)

    dns_reachable = dns["outcome"] in ("BOUNDED-NEGATIVE", "DO-NOT-SERVE-UNCHANGED")
    return {
        "serve_control": {"outcome": serve["outcome"], "reachable": serve["outcome"] == "SERVE"},
        "do_not_serve_control": {"outcome": dns["outcome"], "reachable": dns_reachable},
        "both_outcomes_reachable": bool(serve["outcome"] == "SERVE" and dns_reachable),
    }
