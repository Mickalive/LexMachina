"""Query-map MVP acceptance tests (product lane, factory direction v44).

Covers the vertical slice: question -> bundle -> answer -> counter -> map.
Deterministic (vendored fixture); live OpenCaseLaw is optional enhancement.
"""
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from query import run_query
from query.bundle import bundle_summary, validate_bundle

QUERIES = ["Kündigung Mietvertrag Mietrecht", "licenciement assurance invalidité"]


def _bundle(q="Kündigung Mietvertrag Mietrecht", n=60):
    b = run_query(q, top_n=n)
    assert validate_bundle(b) == [], f"bundle invalid: {validate_bundle(b)}"
    return b


def test_bundle_contract():
    b = _bundle()
    for key in ["bundle_version", "query", "query_variants", "answer",
                "decisions", "clusters", "relations", "provenance"]:
        assert key in b, f"missing {key}"
    assert len(b["query_variants"]) >= 1
    assert b["provenance"]["corpus"]["n_total"] >= 60


def test_map_coordinates_finite_and_bounded():
    b = _bundle()
    cids = {c["cluster_id"] for c in b["clusters"]}
    assert len(cids) >= 2
    for d in b["decisions"]:
        assert math.isfinite(d["x"]) and math.isfinite(d["y"])
        assert -1.0 - 1e-6 <= d["x"] <= 1.0 + 1e-6
        assert -1.0 - 1e-6 <= d["y"] <= 1.0 + 1e-6
        assert d["cluster_id"] in cids


def test_clusters_labeled_and_outliers_marked():
    b = _bundle()
    for c in b["clusters"]:
        assert c["label"] and len(c["label"]) >= 3, f"empty label: {c}"
        assert c["size"] >= 1
    assert any("is_outlier" in d for d in b["decisions"])


def test_answer_citations_valid():
    b = _bundle()
    ids = {d["decision_id"] for d in b["decisions"]}
    assert len(b["answer"]["cited_decision_ids"]) >= 1
    assert set(b["answer"]["cited_decision_ids"]) <= ids
    assert len(b["answer"]["statements"]) >= 1
    for s in b["answer"]["statements"]:
        assert s["decision_id"] in ids and len(s["text"]) > 40


def test_counter_authority_pass_independent():
    b = _bundle()
    counters = [d for d in b["decisions"]
                if d["counter_status"] not in ("none", "cited")]
    assert len(counters) >= 1, "adversarial pass found no candidates"
    assert any(d["counter_evidence"] or d["counter_markers"] for d in counters)
    assert b["provenance"]["counter"]["method"].startswith("independent_")


def test_multilingual_recall():
    b = _bundle(n=100)
    langs = {d["language"] for d in b["decisions"]}
    assert {"de", "fr", "it"} <= langs, f"missing languages: {langs}"


def test_french_query_end_to_end():
    b = _bundle(QUERIES[1])
    s = bundle_summary(b)
    assert s["n_decisions"] == 60 and s["answer_citations"] >= 1


def test_deterministic_projection():
    b1 = _bundle()
    b2 = _bundle()
    m1 = {d["decision_id"]: (d["x"], d["y"], d["cluster_id"]) for d in b1["decisions"]}
    m2 = {d["decision_id"]: (d["x"], d["y"], d["cluster_id"]) for d in b2["decisions"]}
    assert m1.keys() == m2.keys()
    for k in m1:
        assert m1[k] == m2[k], f"nondeterministic map for {k}"


def test_latency_bounded():
    b = _bundle()
    assert b["provenance"]["latency_seconds"] < 60


def test_source_links_present():
    b = _bundle()
    for d in b["decisions"][:10]:
        assert d["canonical_url"].startswith("http")
        assert d["snippet"]
