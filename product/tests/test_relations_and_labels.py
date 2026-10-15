"""Round-3 repair tests for cycle 38779139471: map relations and map labels.

Two product gaps recorded by the independent audit of run 38779139471
(results/audit/product/CYCLE_38779139471_GATE.json, gate=REVISE) are closed
here.  Both are product-side: they need no frontier change and no network.

F2 — ``advisory_cluster_label_environment_sensitive``.
    ``build_map`` ranked label terms with ``terms[np.argsort(-mean)[:5]]`` over
    the *whole* fitted vocabulary.  For a cluster of 1-5 decisions only a few
    terms have a non-zero mean, so the 4th/5th label slots were filled from
    thousands of exactly tied zero-mean terms — i.e. from ``argsort`` internals
    rather than from the data.  The committed bundle's sha256 was therefore not
    reproducible outside the machine that generated it, and the labels a jurist
    read could name terms that do not occur anywhere in their cluster.
    ``label_terms`` is now shared by the initial fit and the recompute-on-merge
    path, admits only present terms, and breaks ties on the term string.

F3 — ``advisory_citation_view_empty_no_followup``.
    The map's "reveal relations on selection" affordance (QUERY_MAP_MVP 7) was
    always empty for an unhydrated map: relations were produced only by
    ``find_citations`` string matching over decision bodies, which are empty for
    30 of 154 rows.  The OpenCaseLaw ``/citations`` channel already returns
    *typed* edges, and the adapter records each one on the candidate row's
    ``provenance_events``; the product now recovers them.

Everything here is offline and deterministic: the unit tests build their own
candidates, and the end-to-end test replays the recorded claim query out of the
committed OpenCaseLaw cache (network_calls == 0).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product"))
sys.path.insert(0, str(ROOT))

from query.pipeline import (  # noqa: E402
    _merge_relations, run_query_initial, typed_citation_relations,
)
from query.qmap import MapModel, _body, _cluster_label, label_terms  # noqa: E402

RECORDED_QUERY = "Responsabilite penale de l'entreprise selon l'art. 102 CP"


# --------------------------------------------------------------------------
# F2 — cluster labels
# --------------------------------------------------------------------------

def _label_model(documents: list[str]):
    """A MapModel carrying only the vectorizer ``_cluster_label`` needs."""
    from sklearn.feature_extraction.text import TfidfVectorizer

    vectorizer = TfidfVectorizer(token_pattern=r"(?u)\b[^\W\d_]{2,}\b", lowercase=True)
    vectorizer.fit(documents)
    return MapModel(vectorizer, None, 1.0, None, None, None, None, 0, [], {})


def test_label_terms_never_names_a_term_absent_from_the_cluster():
    """A label must explain the group: only terms the cluster contains."""
    model = _label_model(["rechtsprechung zivilrecht entscheid", "zivilrecht rechtsprechung"])
    label = _cluster_label(model, [{"full_text": "rechtsprechung zivilrecht entscheid"}])

    assert label, "a cluster with text must get a label"
    present = {"rechtsprechung", "zivilrecht", "entscheid"}
    for term in label.split(", "):
        assert term in present, f"label names a term that does not occur in the cluster: {term!r}"


def test_label_terms_breaks_exact_ties_on_the_term_string():
    """Equal means must resolve the same way on every machine."""
    mean = np.array([0.5, 0.5, 0.25, 0.25, 0.25, 0.0, 0.0])
    terms = ["zeta", "alpha", "omega", "beta", "gamma", "absent1", "absent2"]

    first = label_terms(mean, terms)
    assert first == ["alpha", "zeta", "beta", "gamma", "omega"], first
    # Same multiset, different input order -> same label.
    shuffled = label_terms(mean[::-1], terms[::-1])
    assert set(shuffled) == set(first)


def test_cluster_label_is_stable_under_last_bit_float_noise():
    """The property audit F2 asks for: an off-environment build must not relabel.

    Reproduced here by perturbing every cluster mean at the last-bit level a
    different BLAS/scipy build can produce (1e-16 relative), which is how two
    foreign environments produced two different label sets for the *same* 154
    decision rows.
    """
    documents = [
        "rechtsprechung zivilrecht entscheid bundesgericht",
        "rechtsprechung zivilrecht kantonsgericht",
        "strafrecht bundesgericht entscheid haftung",
    ]
    model = _label_model(documents)
    members = [{"full_text": t} for t in documents]
    baseline = _cluster_label(model, members).split(", ")
    assert baseline, "the fixture must produce a label"

    rng = np.random.default_rng(20261015)
    for _ in range(25):
        mean = np.asarray(
            model.vectorizer.transform([_body(d) for d in members]).mean(axis=0)
        ).ravel()
        perturbed = mean * (1.0 + rng.normal(0.0, 1e-16, size=mean.shape))
        assert label_terms(perturbed, model.vectorizer.get_feature_names_out()) == baseline, (
            "last-bit noise changed a cluster label: the artifact is not reproducible off-environment"
        )


def test_all_absent_terms_yields_empty_label_and_cluster_fallback():
    """No present term -> no label, so build_map falls back to 'Cluster N'."""
    model = _label_model(["alpha beta gamma"])
    terms = model.vectorizer.get_feature_names_out()
    assert label_terms(np.zeros(len(terms)), terms) == []


# --------------------------------------------------------------------------
# F3 — typed citation relations
# --------------------------------------------------------------------------

def _citation_row(decision_id: str, seed: str, direction: str, **extra) -> dict:
    channel = f"citation.{direction}"
    row = {
        "decision_id": decision_id,
        "channels": [channel],
        "record_kind": "citation_neighbour",
        "detail_status": "pending",
        "provenance": f"ocl:{channel} seed={seed}",
        "provenance_events": [{
            "channel": channel,
            "endpoint": "/citations",
            "seed_decision_id": seed,
            "direction": direction,
            "confidence": 0.9,
            "mention_count": 2.0,
        }],
    }
    row.update(extra)
    return row


def test_incoming_edge_is_emitted_as_citing_decision_points_at_the_seed():
    """/citations incoming = "these decisions cite the seed"."""
    on_map = [{"decision_id": "citer"}, {"decision_id": "seed"}]
    rows = [_citation_row("citer", "seed", "incoming")]

    assert typed_citation_relations(rows, on_map) == [{
        "source": "citer",
        "target": "seed",
        "kind": "citation",
        "evidence": "OpenCaseLaw /citations incoming (seed seed, confidence 0.9)",
        "seed_decision_id": "seed",
        "direction": "incoming",
        "confidence": 0.9,
        "mention_count": 2.0,
    }]


def test_outgoing_edge_is_emitted_as_the_seed_citing_the_other_decision():
    """/citations outgoing = "the seed cites these decisions"."""
    rows = [_citation_row("cited", "seed", "outgoing")]
    rels = typed_citation_relations(rows, [{"decision_id": "cited"}, {"decision_id": "seed"}])

    assert [(r["source"], r["target"], r["kind"]) for r in rels] == [("seed", "cited", "citation")]


def test_edges_whose_other_endpoint_is_not_on_the_map_are_dropped():
    """The UI cannot open a decision that is not on the map."""
    rows = [
        _citation_row("cited", "seed_never_retrieved", "outgoing"),
        _citation_row("citer", "seed", "incoming"),
    ]
    rels = typed_citation_relations(rows, [{"decision_id": "citer"}, {"decision_id": "seed"}])

    assert [(r["source"], r["target"]) for r in rels] == [("citer", "seed")]


def test_relations_are_deduplicated_and_ordered_deterministically():
    rows = [
        _citation_row("b_citer", "seed", "incoming"),
        _citation_row("b_citer", "seed", "incoming"),   # same edge from two channels
        _citation_row("a_cited", "seed", "outgoing"),
    ]
    on_map = [{"decision_id": i} for i in ("a_cited", "b_citer", "seed")]
    rels = typed_citation_relations(rows, on_map)

    assert [(r["source"], r["target"]) for r in rels] == [
        ("b_citer", "seed"), ("seed", "a_cited"),
    ], "the repeated edge is emitted once and the order is stable across inputs"


def test_non_citation_channels_contribute_no_relation():
    """A search hit that merely *mentions* a reference is not a citation edge."""
    rows = [{
        "decision_id": "search_hit",
        "channels": ["search"],
        "record_kind": "search_hit",
        "detail_status": "search_hit",
        "provenance_events": [{"channel": "search", "endpoint": "/search", "variant_id": "v1"}],
    }]
    assert typed_citation_relations(rows, [{"decision_id": "search_hit"}, {"decision_id": "seed"}]) == []


def test_merge_prefers_typed_edges_and_caps_the_relation_list():
    typed = [{"source": "a", "target": "b", "kind": "citation"}]
    shared = [
        {"source": "a", "target": "b", "kind": "shared_citation", "shared": ["BGE 142 IV 333"]},
        {"source": "b", "target": "c", "kind": "shared_citation"},
    ]
    merged = _merge_relations(typed, shared)

    assert [(r["source"], r["target"], r["kind"]) for r in merged] == [
        ("a", "b", "citation"), ("b", "c", "shared_citation"),
    ], "an edge present as both kinds must appear once, as the typed one"
    assert len(_merge_relations(typed, shared, limit=1)) == 1


# --------------------------------------------------------------------------
# End-to-end on the recorded claim query (offline, from committed cache)
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def claim_bundle() -> dict:
    return run_query_initial(RECORDED_QUERY, top_n=120, retrieval_mode="offline")


def test_claim_map_now_carries_typed_citation_relations(claim_bundle):
    rels = claim_bundle["relations"]
    prov = claim_bundle["provenance"]["relations_provenance"]

    assert prov["typed_citation_relations"] == len(rels) > 0, (
        "audit F3 recorded 0 relations for this query while retrieval had found 30 "
        "typed citation neighbours"
    )
    assert prov["citation_channel_rows"] >= prov["typed_citation_relations"] > 0


def test_every_relation_endpoint_is_on_the_map(claim_bundle):
    """Invariants a renderer relies on: relations only ever name mapped points."""
    on_map = {d["decision_id"] for d in claim_bundle["decisions"]}
    for rel in claim_bundle["relations"]:
        assert rel["source"] in on_map, rel
        assert rel["target"] in on_map, rel
        assert rel["source"] != rel["target"]


def test_claim_replay_stayed_offline_and_unvalidated(claim_bundle):
    from query.bundle import validate_bundle

    assert validate_bundle(claim_bundle) == []
    assert claim_bundle["provenance"]["retrieval"]["remote"]["request_summary"]["network_calls"] == 0
    assert claim_bundle["answer"]["status"] == "pending", (
        "the map phase must not start generating; the answer stays a separate job"
    )