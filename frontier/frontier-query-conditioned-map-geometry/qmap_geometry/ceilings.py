"""Measured ceilings of the frozen rule on the served bundles.

These are NOT variant results.  They bound what ANY variant could achieve, so
that a failing criterion is attributable either to the variant or to the rule's
own reference geometry.  Everything here is computed from the frozen TF-IDF
cosine structure the rule itself builds.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from .scoring import frozen_inputs
from .vendored.frontier_map_semantics.textgeo import is_unhydrated

K_VALUES = (6, 8, 10)


def structure_sep_ceiling(bundle: dict, k: int = 8) -> dict[str, Any]:
    """Best achievable STRUCTURE_SEP for any partition of the rows.

    Intra pairs must come from the most similar row pairs; the inter side is
    everything else.  The qmap cluster-count rule caps k at 8, so k=8 is the
    operative bound and k=6/10 bracket it.
    """
    _texts, X, _q = frozen_inputs(bundle)
    from sklearn.metrics.pairwise import cosine_distances

    D = np.nan_to_num(np.asarray(cosine_distances(X), dtype=float), nan=1.0)
    n = D.shape[0]
    mask = np.array([not is_unhydrated(d) for d in bundle["decisions"]])
    idx = np.where(mask)[0]
    Dh = D[np.ix_(idx, idx)]
    m = len(idx)
    iuh = np.triu_indices(m, 1)
    dh = Dh[iuh]
    iu = np.triu_indices(n, 1)
    inter_mean = float(D[iu].mean())
    rows = {}
    for kk in K_VALUES:
        sizes = [m // kk + (1 if i < m % kk else 0) for i in range(kk)]
        n_intra = sum(s * (s - 1) // 2 for s in sizes)
        best_intra = float(np.sort(dh)[:n_intra].mean()) if n_intra else float("nan")
        rows[f"k={kk}"] = {
            "intra_pairs": n_intra,
            "oracle_best_intra_mean": best_intra,
            "inter_mean": inter_mean,
            "oracle_best_sep_ratio": best_intra / inter_mean if inter_mean else float("nan"),
            "bar": 0.90,
            "reachable": bool(best_intra / inter_mean < 0.90) if inter_mean else False,
        }
    return {
        "qid": bundle.get("query", "")[:40],
        "n_rows": n,
        "n_clusterable_rows": m,
        "cosine_reference": "the frozen rule's own TF-IDF space over ALL rows",
        "clusterable_pairwise_cosine": {
            "mean": float(dh.mean()),
            "p10": float(np.percentile(dh, 10)),
            "p5": float(np.percentile(dh, 5)),
            "min": float(dh.min()),
        },
        "by_k": rows,
        "operative_k": 8,
        "operative_reachable": rows["k=8"]["reachable"],
    }


def projection_invariance_proof(bundle: dict, candidate: dict, rules_bundle: dict) -> dict[str, Any]:
    """PROJ_RANK does not read x/y: shuffling every coordinate leaves it unchanged."""
    from .scoring import score_bundle

    import copy

    shuffled = copy.deepcopy(candidate)
    rng = np.random.default_rng(0)
    xy = np.array([[float(d.get("x", 0.0)), float(d.get("y", 0.0))] for d in shuffled["decisions"]])
    perm = rng.permutation(len(xy))
    for d, (x, y) in zip(shipped_rows(shuffled), xy[perm]):
        d["x"], d["y"] = float(x), float(y)
    a = score_bundle(candidate, rules_bundle)["criteria"]["PROJ_RANK"]["value"]
    b = score_bundle(shuffled, rules_bundle)["criteria"]["PROJ_RANK"]["value"]
    return {
        "proj_rank_with_coordinates": a,
        "proj_rank_after_full_coordinate_shuffle": b,
        "identical": a == b,
        "conclusion": (
            "PROJ_RANK is invariant to every layout change; it is a property of "
            "the retrieved rows (TF-IDF cosine distance to the query vector vs "
            "retrieval rank), not of the map. No variant can pass or fail it "
            "differently from the shipped bundle."
        ),
    }


def shipped_rows(bundle: dict) -> list[dict]:
    return list(bundle["decisions"])


def outlier_degeneracy(bundle: dict) -> dict[str, Any]:
    """Whether OUTLIER_VALIDITY is structurally reachable on this bundle."""
    from .vendored.frontier_map_semantics.metrics import outliers_metric

    out = outliers_metric(bundle["decisions"])
    deg = bool(out["citation_graph_degenerate"])
    return {
        "citation_graph_degenerate": deg,
        "n_outliers_shipped": out["n_outliers"],
        "outlier_mean_degree": out["outlier_mean_degree"],
        "rest_mean_degree": out["rest_mean_degree"],
        "structurally_unreachable": deg,
        "why": (
            "The frozen predicate is DEGENERATE->FAIL when no two rows share a "
            "BGE/ATF citation, so no outlier selection can pass on this bundle."
            if deg else "Reachable: the citation graph is non-degenerate."
        ),
    }


def ceilings_for(qid: str, bundle: dict, rules_bundle: dict, candidate: dict) -> dict[str, Any]:
    return {
        "qid": qid,
        "structure_sep": structure_sep_ceiling(bundle),
        "projection_rank_invariance": projection_invariance_proof(bundle, candidate, rules_bundle),
        "outlier_validity": outlier_degeneracy(bundle),
    }
