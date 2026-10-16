"""Map-CONTRACT gates for the shipped query_result_bundle (evaluation lane, v49).

Every bar is read from the frozen spec; no threshold literal lives in this
module.  All five gates read ONLY the shipped bundle fields (``cluster_id``,
``clusters[].member_ids``, ``clusters[].size``, ``x``/``y``, ``is_outlier``,
``relations``, ``counter_status``, ``provenance.query``) -- no clustering, no
projection, no re-computation of the geometry, no numpy, no sklearn, no Product
import and no network call.

A gate result is always a dict with ``gate``, ``passed`` (bool), ``detail``
(blank on a pass, per the lane's record convention) and, when applicable,
``not_measurable`` with an explicit ``reason``.
"""
from __future__ import annotations

import statistics
from collections import Counter, defaultdict

from . import frozen

_COUNTER_DEFAULT = frozenset()


def _blank(gate: str, **measured) -> dict:
    return {"gate": gate, "passed": True, "detail": "", **measured}


def _fail(gate: str, detail: str, **measured) -> dict:
    return {"gate": gate, "passed": False, "detail": detail, **measured}


def _nm(gate: str, reason: str, **measured) -> dict:
    return {"gate": gate, "passed": False, "not_measurable": True,
            "reason": reason, **measured}


# --------------------------------------------------------------------------- #
# 1. cluster membership enumerability
# --------------------------------------------------------------------------- #


def evaluate_cluster_membership_enumerable(bundle: dict, spec: dict) -> dict:
    gate = "MAP::cluster_membership_enumerable"
    decisions = bundle.get("decisions") or []
    clusters = bundle.get("clusters") or []
    if not decisions or not clusters:
        return _nm(gate, "bundle carries no decisions or no clusters")

    ids = {str(d.get("decision_id") or "") for d in decisions}
    assigned: dict[int, list[str]] = defaultdict(list)
    for d in decisions:
        cid = d.get("cluster_id")
        if cid is not None:
            assigned[int(cid)].append(str(d.get("decision_id") or ""))

    enumerated: set[str] = set()
    size_mismatches: list[dict] = []
    for cluster in clusters:
        members = [str(m) for m in (cluster.get("member_ids") or [])]
        enumerated.update(members)
        declared = cluster.get("size")
        if declared is not None and int(declared) != len(members):
            size_mismatches.append({
                "cluster_id": cluster.get("cluster_id"),
                "declared_size": int(declared),
                "enumerated_members": len(members),
                "unrecoverable": int(declared) - len(members),
            })

    unreachable = sorted({i for members in assigned.values() for i in members
                         if i not in enumerated})
    unknown_members = sorted(enumerated - ids)
    measured = {
        "n_decisions": len(decisions),
        "n_assigned": sum(len(v) for v in assigned.values()),
        "n_enumerated": len(enumerated & ids),
        "unreachable_count": len(unreachable),
        "size_mismatch_count": len(size_mismatches),
        "size_mismatches": size_mismatches,
        "member_ids_not_in_decisions": unknown_members[:20],
    }
    if unknown_members:
        return _fail(gate,
                     f"{len(unknown_members)} member_ids name decisions that are "
                     f"not in the bundle (e.g. {unknown_members[:3]})", **measured)
    if unreachable:
        return _fail(gate,
                     f"{len(unreachable)} of {measured['n_assigned']} "
                     f"cluster-assigned decisions cannot be enumerated through "
                     f"clusters[].member_ids (e.g. {unreachable[:3]})", **measured)
    if size_mismatches:
        return _fail(gate,
                     f"{len(size_mismatches)} clusters declare a size their "
                     f"member_ids do not match: {size_mismatches[:3]}", **measured)
    return _blank(gate, **measured)


# --------------------------------------------------------------------------- #
# 2. point distinguishability
# --------------------------------------------------------------------------- #


def evaluate_points_distinguishable(bundle: dict, spec: dict) -> dict:
    gate = "MAP::points_distinguishable"
    decisions = bundle.get("decisions") or []
    if not decisions:
        return _nm(gate, "bundle carries no decisions")
    precision = int(spec["parameters"]["coordinate_precision"])
    bar = float(spec["parameters"]["max_coincident_cell_share"])

    cells: Counter = Counter()
    for d in decisions:
        try:
            x = round(float(d["x"]), precision)
            y = round(float(d["y"]), precision)
        except (TypeError, ValueError):
            return _nm(gate, "a decision row has a non-numeric coordinate")
        cells[(x, y)] += 1

    total = len(decisions)
    worst, worst_n = cells.most_common(1)[0]
    share = worst_n / total
    collided_rows = sum(n for n in cells.values() if n > 1)
    distinct = len(cells)
    measured = {
        "n_decisions": total,
        "n_distinct_cells": distinct,
        "n_rows_in_collided_cells": collided_rows,
        "collided_row_share": round(collided_rows / total, 6),
        "max_cell": {"x": worst[0], "y": worst[1], "n": worst_n},
        "max_cell_share": round(share, 6),
        "bar": bar,
    }
    if share > bar:
        return _fail(gate,
                     f"coordinate cell ({worst[0]}, {worst[1]}) holds "
                     f"{worst_n}/{total} decisions = {share:.4f} > bar {bar}; "
                     f"{collided_rows} rows share a cell with another row, so "
                     f"{collided_rows} points cannot be picked apart", **measured)
    return _blank(gate, **measured)


# --------------------------------------------------------------------------- #
# 3. outlier flag vs the shipped relations graph
# --------------------------------------------------------------------------- #


def relation_degrees(bundle: dict) -> Counter:
    degrees: Counter = Counter()
    for rel in bundle.get("relations") or []:
        src, dst = rel.get("source"), rel.get("target")
        if src is not None:
            degrees[str(src)] += 1
        if dst is not None:
            degrees[str(dst)] += 1
    return degrees


def evaluate_outlier_degree_consistent(bundle: dict, spec: dict) -> dict:
    gate = "MAP::outlier_degree_consistent"
    decisions = bundle.get("decisions") or []
    relations = bundle.get("relations") or []
    if not decisions:
        return _nm(gate, "bundle carries no decisions")
    degrees = relation_degrees(bundle)
    if not relations:
        return _fail(gate,
                     "DEGENERATE: the bundle ships no relations, so the "
                     "is_outlier flag cannot be consistent with any relation "
                     "graph and the 'weakly connected outlier' claim is "
                     "unfalsifiable on this artifact",
                     degenerate=True, n_decisions=len(decisions),
                     n_relations=0, n_outliers=0)
    outlier_deg = [degrees.get(str(d.get("decision_id") or ""), 0)
                   for d in decisions if d.get("is_outlier")]
    other_deg = [degrees.get(str(d.get("decision_id") or ""), 0)
                 for d in decisions if not d.get("is_outlier")]
    measured = {
        "n_relations": len(relations),
        "n_outliers": len(outlier_deg),
        "n_other": len(other_deg),
        "mean_outlier_degree": round(statistics.fmean(outlier_deg), 6) if outlier_deg else 0.0,
        "mean_other_degree": round(statistics.fmean(other_deg), 6) if other_deg else 0.0,
        "median_outlier_degree": statistics.median(outlier_deg) if outlier_deg else 0.0,
        "median_other_degree": statistics.median(other_deg) if other_deg else 0.0,
    }
    if not outlier_deg:
        return _nm(gate, "bundle flags no outlier, so the flag cannot be checked")
    if not other_deg:
        return _nm(gate, "every row is flagged outlier; no comparison group")
    if measured["mean_outlier_degree"] >= measured["mean_other_degree"]:
        return _fail(gate,
                     f"mean relation degree of flagged outliers "
                     f"({measured['mean_outlier_degree']:.4f}) is not below the "
                     f"mean of the rest ({measured['mean_other_degree']:.4f})",
                     **measured)
    return _blank(gate, **measured)


# --------------------------------------------------------------------------- #
# 4. cluster label language vs query language
# --------------------------------------------------------------------------- #


def label_language(label: object, query_language: str, spec: dict) -> dict:
    """Attribute a cluster label to a language, conservatively.

    ``off_language`` is True only when every lexicon-attributed token belongs
    to exactly one language and that language is not the query language.  Tokens
    attributed to several languages and tokens absent from the lexicon (all
    content words) are ignored, so the gate is a lower bound on mismatch.
    """
    attr = frozen.attribution(spec)
    exclusive: dict[str, list[str]] = defaultdict(list)
    unattributed: list[str] = []
    for token in frozen.tokenize(label):
        langs = attr.get(token)
        if not langs:
            unattributed.append(token)
        elif len(langs) == 1:
            exclusive[next(iter(langs))].append(token)
    languages = sorted(exclusive)
    verdict = "unknown"
    if len(languages) == 1:
        verdict = languages[0]
    off = verdict != "unknown" and verdict != query_language
    return {
        "label_tokens_attributed": {k: sorted(v) for k, v in sorted(exclusive.items())},
        "n_unattributed_tokens": len(unattributed),
        "attributed_language": verdict,
        "off_language": bool(off),
    }


def evaluate_label_language_matches_query(bundle: dict, spec: dict,
                                          *, query_language: str | None = None,
                                          language_votes: dict | None = None) -> dict:
    gate = "MAP::label_language_matches_query"
    clusters = bundle.get("clusters") or []
    if not clusters:
        return _nm(gate, "bundle carries no clusters to label")
    if query_language is None or query_language == "unknown":
        return _nm(gate,
                   "query language could not be inferred unambiguously from the "
                   f"frozen lexicon rule (votes={language_votes})",
                   query_language=query_language, language_votes=language_votes)
    bar = float(spec["parameters"]["label_language_min_share"])

    per_label = []
    for cluster in clusters:
        info = label_language(cluster.get("label"), query_language, spec)
        info["cluster_id"] = cluster.get("cluster_id")
        per_label.append(info)
    n = len(per_label)
    bad = [i for i in per_label if i["off_language"]]
    share_ok = (n - len(bad)) / n
    measured = {
        "query_language": query_language,
        "language_votes": language_votes,
        "n_clusters": n,
        "n_off_language": len(bad),
        "share_ok": round(share_ok, 6),
        "bar": bar,
        "off_language_clusters": bad,
    }
    if share_ok < bar:
        return _fail(gate,
                     f"{len(bad)}/{n} cluster labels are unambiguously in a "
                     f"language other than the query language ({query_language}): "
                     f"{[(b['cluster_id'], b['attributed_language']) for b in bad][:6]}",
                     **measured)
    return _blank(gate, **measured)


# --------------------------------------------------------------------------- #
# 5. counter-authority selectability and reachability
# --------------------------------------------------------------------------- #


def counter_statuses(spec: dict) -> frozenset[str]:
    return frozenset(spec.get("counter_statuses") or _COUNTER_DEFAULT)


def evaluate_counter_authority_selectable(bundle: dict, spec: dict) -> dict:
    gate = "MAP::counter_authority_selectable"
    statuses = counter_statuses(spec)
    decisions = bundle.get("decisions") or []
    clusters = bundle.get("clusters") or []
    if not decisions or not clusters:
        return _nm(gate, "bundle carries no decisions or no clusters")

    precision = int(spec["parameters"]["coordinate_precision"])
    bar = float(spec["parameters"]["max_coincident_cell_share"])
    cells: Counter = Counter()
    for d in decisions:
        try:
            cells[(round(float(d["x"]), precision), round(float(d["y"]), precision))] += 1
        except (TypeError, ValueError):
            return _nm(gate, "a decision row has a non-numeric coordinate")

    enumerated: set[str] = set()
    for cluster in clusters:
        enumerated.update(str(m) for m in (cluster.get("member_ids") or []))

    counters = [d for d in decisions
                if str(d.get("counter_status") or "") in statuses]
    measured = {
        "counter_statuses": sorted(statuses),
        "n_counter": len(counters),
        "n_decisions": len(decisions),
        "bar": bar,
    }
    if not counters:
        return _nm(gate, "bundle carries no decision with a counter-authority "
                         "status, so counter-authority map reachability cannot "
                         "be measured on this artifact", **measured)

    unselectable, unreachable = [], []
    for d in counters:
        did = str(d.get("decision_id") or "")
        try:
            cell = (round(float(d["x"]), precision), round(float(d["y"]), precision))
        except (TypeError, ValueError):
            return _nm(gate, "a counter row has a non-numeric coordinate")
        if cells[cell] / len(decisions) > bar:
            unselectable.append({"decision_id": did, "cell": list(cell),
                                 "cell_n": cells[cell]})
        if d.get("cluster_id") is not None and did not in enumerated:
            unreachable.append(did)
    measured["n_unselectable"] = len(unselectable)
    measured["n_unreachable"] = len(unreachable)
    measured["unselectable"] = unselectable[:20]
    measured["unreachable"] = unreachable[:20]
    if unselectable:
        return _fail(gate,
                     f"{len(unselectable)}/{len(counters)} counter-authority "
                     f"decisions sit in a coordinate cell holding more than the "
                     f"bar's share of the map, so they cannot be picked out as "
                     f"their own point", **measured)
    if unreachable:
        return _fail(gate,
                     f"{len(unreachable)}/{len(counters)} counter-authority "
                     f"decisions are cluster-assigned but cannot be enumerated "
                     f"through their cluster's member_ids", **measured)
    return _blank(gate, **measured)


# --------------------------------------------------------------------------- #
# bundle driver
# --------------------------------------------------------------------------- #


def evaluate_bundle(bundle: dict, spec: dict, *, bundle_path: str) -> dict:
    """Run every frozen gate on one shipped bundle."""
    qlang, votes = frozen.infer_query_language(
        (bundle.get("provenance") or {}).get("query") or bundle.get("query"), spec)

    results = [
        evaluate_cluster_membership_enumerable(bundle, spec),
        evaluate_points_distinguishable(bundle, spec),
        evaluate_outlier_degree_consistent(bundle, spec),
        evaluate_label_language_matches_query(
            bundle, spec, query_language=qlang, language_votes=votes),
        evaluate_counter_authority_selectable(bundle, spec),
    ]
    by_gate = {r["gate"]: r for r in results}
    measurable = [r for r in results if not r.get("not_measurable")]
    passed = [r for r in measurable if r["passed"]]
    failed = [r for r in measurable if not r["passed"]]
    return {
        "bundle_path": bundle_path,
        "n_decisions": len(bundle.get("decisions") or []),
        "n_clusters": len(bundle.get("clusters") or []),
        "query_language": qlang,
        "query_language_votes": votes,
        "passed": not failed,
        "gates": by_gate,
        "n_gates_measurable": len(measurable),
        "n_gates_passed": len(passed),
        "n_gates_failed": len(failed),
        "n_gates_not_measurable": len(results) - len(measurable),
        "failed_gates": [r["gate"] for r in failed],
        "not_measurable_gates": [
            {"gate": r["gate"], "reason": r["reason"]} for r in results
            if r.get("not_measurable")
        ],
    }


def summarize(results: list[dict]) -> dict:
    """Bundle-level roll-up. not_measurable never counts as a pass."""
    gates = sorted({g for r in results for g in r["gates"]})
    per_gate = {}
    for gate in gates:
        measurable = [r for r in results if gate in r["gates"]
                      and not r["gates"][gate].get("not_measurable")]
        nm = [r for r in results if gate in r["gates"]
              and r["gates"][gate].get("not_measurable")]
        failed = [r for r in measurable if not r["gates"][gate]["passed"]]
        per_gate[gate] = {
            "n_bundles": len(results),
            "n_measurable": len(measurable),
            "n_passed": len(measurable) - len(failed),
            "n_failed": len(failed),
            "n_not_measurable": len(nm),
            "failing_bundles": [r["bundle_path"] for r in failed],
        }
    n_failed_bundles = sum(1 for r in results if not r["passed"])
    return {
        "schema": "lex-map-contract-summary/1",
        "n_bundles": len(results),
        "n_bundles_passed": len(results) - n_failed_bundles,
        "n_bundles_failed": n_failed_bundles,
        "overall_pass": n_failed_bundles == 0,
        "per_gate": per_gate,
        "failed_bundle_paths": [r["bundle_path"] for r in results if not r["passed"]],
    }
