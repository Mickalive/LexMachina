"""An empty relation panel must be a stated measurement, not a silent omission.

Two independent things are guarded here:

* the classifier itself (pure, stdlib-only, no network, no numpy) — including
  that the four states are actually reachable, which a naive implementation that
  always answers EMPTY_… would not pass;
* the two seams that publish it — the map-build provenance and the
  post-hydration refresh — including the invariant that the refresh never removes
  an edge it did not create and never moves a point.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from product.query import relation_channel as rc
from product.query.qmap import shared_citation_relations

ROOT = Path(__file__).resolve().parents[2]


def _dec(**kw):
    base = {"decision_id": kw.pop("decision_id", "d"), "regeste": kw.pop("regeste", ""),
            "snippet": kw.pop("snippet", ""), "title": kw.pop("title", "")}
    base.update(kw)
    return base


def _detect(decision):
    """Detector with the module's contract: it receives the ROW, not the text.

    Production injects ``lambda d: find_citations(_body(d)[:20000])``; keeping the
    extraction on the caller is what lets this module stay a numpy-free leaf.
    """
    text = " ".join(str(decision.get(k) or "") for k in
                    ("full_text", "regeste", "snippet", "title", "citation"))
    return set(re.findall(r"BGE\s+\d+\s+[IVX]+\s+\d+", text))


# --------------------------------------------------------------------------
# the classifier
# --------------------------------------------------------------------------

def test_no_decisions_is_its_own_state():
    out = rc.classify(rc.coverage([], _detect), n_relations=0)
    assert out["state"] == "EMPTY_NO_DECISIONS"
    assert "nothing to relate" in out["note"]


def test_no_detected_citation_is_distinct_from_no_shared_authority():
    """The distinction is the whole point: one is a detection gap, one is a fact
    about the retrieved set, and they demand different next actions."""
    blind = rc.classify(rc.coverage([_dec(regeste="keine Zitate")], _detect), 0)
    assert blind["state"] == "EMPTY_NO_CITATIONS_DETECTED"
    assert blind["disclosure_required"] is True

    alone = rc.classify(
        rc.coverage(
            [_dec(decision_id="a", regeste="BGE 117 II 415"),
             _dec(decision_id="b", regeste="BGE 119 II 147")],
            _detect,
        ),
        0,
    )
    assert alone["state"] == "EMPTY_NO_SHARED_AUTHORITY"
    assert alone["measured"]["n_rows_with_citation"] == 2
    assert "no two cite the same one" in alone["note"]


def test_a_single_shared_authority_populates_the_channel():
    rows = [
        _dec(decision_id="a", regeste="BGE 117 II 415"),
        _dec(decision_id="b", regeste="verweist auf BGE 117 II 415"),
        _dec(decision_id="c", regeste="BGE 119 II 147"),
    ]
    meas = rc.coverage(rows, _detect)
    assert meas["n_rows_with_citation"] == 3
    assert meas["n_pairs_sharing_citation"] == 1
    assert meas["n_rows_in_a_shared_pair"] == 2
    out = rc.classify(meas, n_relations=1)
    assert out["state"] == "POPULATED"
    assert out["disclosure_required"] is False


def test_state_vocabulary_is_published_not_hard_coded():
    flags = rc.state_flags()
    assert flags["populated"] in flags["states"]
    assert len(flags["states"]) == len(rc.CHANNEL_STATES) == 4


def test_a_broken_detector_never_breaks_a_bundle():
    def boom(_d):
        raise RuntimeError("detector exploded")

    meas = rc.coverage([_dec(regeste="BGE 117 II 415")], boom)
    assert meas["n_rows_with_citation"] == 0
    assert rc.classify(meas, 0)["state"] == "EMPTY_NO_CITATIONS_DETECTED"


def test_coverage_is_quadratic_free_in_shape_not_in_cost():
    """300 rows is the MVP ceiling; the inverted index must not degrade to a scan."""
    rows = [_dec(decision_id=f"d{i}", regeste=f"BGE {i} II 1") for i in range(300)]
    meas = rc.coverage(rows, _detect)
    assert meas["n_decisions"] == 300
    assert meas["n_pairs_sharing_citation"] == 0


def test_channel_state_reads_back_from_a_bundle_provenance():
    prov = {"relations_provenance": {"channel_state": "POPULATED"}}
    assert rc.channel_state(prov) == "POPULATED"
    assert rc.channel_state({}) == ""
    assert rc.channel_state(None) == ""


def test_describe_never_claims_an_edge_when_there_is_none():
    out = rc.classify(rc.coverage([_dec()], _detect), n_relations=0)
    assert "arête" not in out["note"]  # English note, no fabricated edges
    assert out["claim_ceiling"]


# --------------------------------------------------------------------------
# the qmap extraction (one rule, two call sites)
# --------------------------------------------------------------------------

def test_shared_citation_relations_is_the_single_rule():
    rows = [
        _dec(decision_id="a", regeste="BGE 117 II 415"),
        _dec(decision_id="b", regeste="BGE 117 II 415 und BGE 119 II 147"),
    ]
    rels = shared_citation_relations(rows)
    assert rels == [{"source": "a", "target": "b", "kind": "shared_citation",
                     "shared": ["BGE 117 II 415"]}]


def test_shared_citation_relations_respects_its_cap():
    rows = [_dec(decision_id=f"d{i}", regeste="BGE 117 II 415") for i in range(6)]
    assert len(shared_citation_relations(rows, limit=3)) == 3


def test_shared_citation_relations_on_an_empty_set():
    assert shared_citation_relations([]) == []


# --------------------------------------------------------------------------
# the post-hydration refresh seam
# --------------------------------------------------------------------------

def _refresh():
    from product.query.pipeline import _refresh_relation_channel

    return _refresh_relation_channel


def test_refresh_adds_edges_and_keeps_the_pre_existing_ones():
    bundle = {
        "decisions": [
            _dec(decision_id="a", regeste="BGE 117 II 415"),
            _dec(decision_id="b", regeste="BGE 117 II 415"),
        ],
        "relations": [{"source": "a", "target": "z", "kind": "citation", "confidence": 0.9}],
        "provenance": {"relations_provenance": {
            "channel_state": "EMPTY_NO_SHARED_AUTHORITY",
            "channel": rc.classify(rc.coverage([], _detect), 0)}},
    }
    out = _refresh()(bundle)
    assert out["added"] == 1
    kinds = {(r["source"], r["target"]) for r in bundle["relations"]}
    assert ("a", "z") in kinds, "an edge the refresh did not create must survive"
    assert ("a", "b") in kinds
    prov = bundle["provenance"]["relations_provenance"]
    assert prov["channel_state"] == "POPULATED"
    assert prov["relations_added_by_hydration"] == 1


def test_refresh_never_moves_a_point():
    """MVP 9A: enrichment must not recompute geometry."""
    import product.query.pipeline as pipeline

    coords = {"a": (0.1, 0.2, 3, True), "b": (-0.4, 0.9, 1, False)}
    bundle = {
        "decisions": [
            dict(_dec(decision_id=k, regeste="BGE 117 II 415"), x=v[0], y=v[1],
                 cluster_id=v[2], is_outlier=v[3])
            for k, v in coords.items()
        ],
        "relations": [],
        "provenance": {},
    }
    _refresh()(bundle)
    for d in bundle["decisions"]:
        assert (d["x"], d["y"], d["cluster_id"], d["is_outlier"]) == coords[d["decision_id"]]
    assert pipeline is not None


def test_refresh_reports_an_honest_zero_when_nothing_new_appears():
    bundle = {
        "decisions": [_dec(decision_id="a", regeste="BGE 117 II 415"),
                      _dec(decision_id="b", regeste="BGE 119 II 147")],
        "relations": [],
        "provenance": {},
    }
    out = _refresh()(bundle)
    assert out["added"] == 0
    prov = bundle["provenance"]["relations_provenance"]
    assert prov["channel_state"] == "EMPTY_NO_SHARED_AUTHORITY"
    assert prov["channel_after_hydration"]["measured"]["phase"] == "after_hydration"


def test_refresh_keeps_both_measurements_side_by_side():
    """The map-build number is the historical baseline; overwriting it would make
    'the edges were thin because the evidence was not fetched yet' unverifiable."""
    bundle = {
        "decisions": [_dec(decision_id="a", regeste="BGE 117 II 415"),
                      _dec(decision_id="b", regeste="BGE 117 II 415")],
        "relations": [],
        "provenance": {"relations_provenance": {
            "channel": {"state": "EMPTY_NO_CITATIONS_DETECTED", "measured": {"n_decisions": 0}}}},
    }
    _refresh()(bundle)
    prov = bundle["provenance"]["relations_provenance"]
    assert prov["channel"]["state"] == "EMPTY_NO_CITATIONS_DETECTED"
    assert prov["channel_after_hydration"]["state"] == "POPULATED"


def test_refresh_is_idempotent():
    bundle = {
        "decisions": [_dec(decision_id="a", regeste="BGE 117 II 415"),
                      _dec(decision_id="b", regeste="BGE 117 II 415")],
        "relations": [],
        "provenance": {},
    }
    _refresh()(bundle)
    first = len(bundle["relations"])
    _refresh()(bundle)
    assert len(bundle["relations"]) == first == 1


# --------------------------------------------------------------------------
# leaf-module discipline (mirrors counter_status.py's contract)
# --------------------------------------------------------------------------

def test_relation_channel_is_stdlib_only():
    """human_gate_finalize is a browser-export CLI; a heavy import here would be
    a regression for every consumer that only needs the classification."""
    source = (ROOT / "product" / "query" / "relation_channel.py").read_text(encoding="utf-8")
    for banned in ("import numpy", "import scipy", "import sklearn", "from sklearn",
                   "import torch", "import igraph"):
        assert banned not in source


def test_bundle_from_the_offline_slice_publishes_the_channel():
    slices = sorted((ROOT / "results" / "product" / "offline_slice").glob("*/rent-default.bundle.json"))
    if not slices:
        pytest.skip("no offline slice committed")
    bundle = json.loads(slices[-1].read_text(encoding="utf-8"))
    prov = bundle["provenance"]["relations_provenance"]
    assert prov["channel_state"] in rc.CHANNEL_STATES
    assert prov["channel"]["measured"]["n_decisions"] == len(bundle["decisions"])
    if prov["channel_state"] != "POPULATED":
        assert prov["channel_after_hydration"]["measured"]["phase"] == "after_hydration"
