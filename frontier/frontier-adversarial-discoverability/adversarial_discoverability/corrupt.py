"""Deterministic input corruptions that must each flip one frozen metric.

RULES.json ``non_vacuity``.  A metric that can never report PASS is not
evidence.  Each corruption is a pure function of the input document; no
randomness source is consulted (the frozen constant is carried for provenance
only and is recorded in the report).
"""

from __future__ import annotations

import copy
import math
from typing import Any, Dict, List, Tuple

from . import CORRUPTION_SEED
from . import populations as pop

#: Channel name injected by N1.  By construction absent from the initial
#: broad retrieval's channel inventory.
ADVERSARIAL_CHANNEL = "adversarial.negation_search.v1"

#: Cluster id injected by N3.  Absent from every real bundle's cluster set.
ORPHAN_CLUSTER_ID = 9999


def _rows(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    return doc.get("decisions") or []


def _counter_rows(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    return pop.c_strict(_rows(doc))


def n1_inject_adversarial_channel(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Give every counter row a retrieval channel the initial pass never used."""
    out = copy.deepcopy(doc)
    touched = []
    for d in _counter_rows(out):
        ch = list(pop.channels_of(d))
        if ADVERSARIAL_CHANNEL not in ch:
            ch.append(ADVERSARIAL_CHANNEL)
        d["channels"] = ch
        touched.append(d.get("decision_id"))
    return {"doc": out, "touched": touched,
            "description": f"added channel {ADVERSARIAL_CHANNEL!r} to {len(touched)} counter rows"}


def n2_deep_permute_ranks(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Swap ranks so the counter rows take the N deepest ranks in the bundle.

    The rank multiset is preserved exactly: the counter rows vacate their own
    ranks and those ranks are handed to the non-counter rows that occupied the
    depths the counter rows move into.  Deterministic — deep ranks and vacated
    ranks are both sorted, and rows are matched by sorted ``decision_id``.

    (v1 of this corruption assigned the vacated ranks to the alphabetically
    first displaced rows, which silently destroyed one rank from the multiset.
    The multiset invariant is now asserted by the test suite.)
    """
    out = copy.deepcopy(doc)
    rows = _rows(out)
    by_id = {str(d.get("decision_id")): d for d in rows}
    ranks = {str(d.get("decision_id")): pop._rank_of(d, i)
             for i, d in enumerate(rows, start=1)}
    counter_ids = sorted({str(d.get("decision_id")) for d in _counter_rows(out)})
    if not counter_ids:
        return {"doc": out, "touched": [],
                "description": "no counter rows to permute"}

    vacated = sorted(ranks[i] for i in counter_ids)
    non_counter = sorted((i for i in ranks if i not in set(counter_ids)),
                         key=lambda i: (ranks[i], i))
    deep = sorted(ranks[i] for i in non_counter[-len(counter_ids):])
    for did, r in zip(counter_ids, deep):
        by_id[did]["rank"] = r
    for did, r in zip(non_counter[-len(counter_ids):], vacated):
        by_id[did]["rank"] = r
    return {"doc": out, "touched": counter_ids,
            "description": (f"counter rows {counter_ids} moved to the {len(counter_ids)} "
                            f"deepest ranks {deep}; ranks {vacated} handed to the rows "
                            f"that previously held {deep}")}


def n3_separate_placement(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Make every counter row an outlier in its own cluster."""
    out = copy.deepcopy(doc)
    touched = []
    for d in _counter_rows(out):
        d["is_outlier"] = True
        d["cluster_id"] = ORPHAN_CLUSTER_ID
        touched.append(d.get("decision_id"))
    return {"doc": out, "touched": touched,
            "description": f"counter rows moved to isolated cluster {ORPHAN_CLUSTER_ID} and flagged is_outlier"}


def n4_evidence_backing(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Back every counter label with verified, non-placeholder evidence."""
    out = copy.deepcopy(doc)
    touched = []
    for d in _counter_rows(out):
        d["counter_evidence_verified"] = True
        d["counter_reason"] = "contradictory"
        d["counter_evidence"] = "verbatim excerpt injected by non-vacuity corruption N4"
        touched.append(d.get("decision_id"))
    return {"doc": out, "touched": touched,
            "description": f"counter_evidence_verified=True + substantive reason/evidence on {len(touched)} counter rows"}


def n5_yield_boost(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Relabel enough ``none`` rows to clear the frozen 2% yield floor."""
    out = copy.deepcopy(doc)
    rows = _rows(out)
    target = int(math.ceil(0.02 * len(rows)))
    none_rows = sorted((d for d in rows if pop.counter_status(d) == "none"),
                       key=lambda d: (pop._rank_of(d, 10 ** 9), str(d.get("decision_id"))))
    touched = []
    for d in none_rows[:target]:
        d["counter_status"] = "candidate-contrary"
        touched.append(d.get("decision_id"))
    return {"doc": out, "touched": touched,
            "description": f"relabelled {len(touched)} lowest-ranked 'none' rows as candidate-contrary"}


#: RULES.json ``non_vacuity.corruptions``, in frozen order.
CORRUPTIONS: Tuple[Tuple[str, Any, str], ...] = (
    ("N1_inject_adversarial_channel", n1_inject_adversarial_channel,
     "b_marginal_retrieval_contribution"),
    ("N2_deep_permute_ranks", n2_deep_permute_ranks, "c_rank_placement"),
    ("N3_separate_placement", n3_separate_placement, "d_placement_visibility"),
    ("N4_evidence_backing", n4_evidence_backing, "e_evidence_quality"),
    ("N5_yield_boost", n5_yield_boost, "a_counter_yield"),
)


def apply(doc: Dict[str, Any], corruption_id: str) -> Dict[str, Any]:
    for cid, fn, _metric in CORRUPTIONS:
        if cid == corruption_id:
            return fn(doc)
    raise KeyError(f"unknown corruption {corruption_id!r}")


SEED = CORRUPTION_SEED
