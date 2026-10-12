from evaluation.query_map import evaluate_query_map_bundle, geometry_signature


def decision(i, *, lang="fr", status="none", evidence="", uncertainty=None):
    return {
        "decision_id": f"d{i}",
        "canonical_url": f"https://mcp.opencaselaw.ch/entscheid/d{i}",
        "language": lang,
        "cluster_id": i % 2,
        "x": i / 10,
        "y": -i / 10,
        "is_outlier": i == 3,
        "counter_status": status,
        "counter_evidence": evidence,
        "counter_uncertainty": uncertainty,
    }


def bundles():
    ds = [
        decision(1, lang="de"),
        decision(2, lang="fr"),
        decision(3, lang="it", status="limiting", evidence="exception", uncertainty=0.2),
    ]
    initial = {
        "answer": {"cited_decision_ids": []},
        "decisions": [dict(x) for x in ds],
        "clusters": [{"cluster_id": 0}, {"cluster_id": 1}],
        "provenance": {"phase": "map_ready", "latency_seconds": 0.4, "fixture_mode": True},
    }
    final = {
        "answer": {"cited_decision_ids": ["d1", "d2"]},
        "decisions": [dict(x) for x in ds],
        "clusters": [{"cluster_id": 0}, {"cluster_id": 1}],
        "provenance": {
            "phase": "complete",
            "fixture_mode": True,
            "enrichment_latency_seconds": 0.8,
            "latency_seconds_total": 1.2,
            "retrieval": {"candidate_languages": {"de": 1, "fr": 1, "it": 1}},
        },
    }
    return initial, final


def test_happy_path_and_recall():
    initial, final = bundles()
    r = evaluate_query_map_bundle(
        initial,
        final,
        known_relevant_ids=["d1", "d3"],
        known_counter_ids=["d3"],
    )
    assert r["pass"] is True
    assert r["known_relevant"]["recall"] == 1.0
    assert r["known_counter"]["recall"] == 1.0
    assert r["languages"] == {"de": 1, "fr": 1, "it": 1}


def test_invented_citation_fails():
    initial, final = bundles()
    final["answer"]["cited_decision_ids"].append("invented")
    r = evaluate_query_map_bundle(initial, final)
    assert r["pass"] is False
    assert r["checks"]["answer_citations_constrained"] is False
    assert r["invalid_cited_ids"] == ["invented"]


def test_counter_without_evidence_or_uncertainty_fails():
    initial, final = bundles()
    final["decisions"][0]["counter_status"] = "contrary_or_exception"
    r = evaluate_query_map_bundle(initial, final)
    assert r["checks"]["counter_classifications_supported"] is False
    assert r["unsupported_counter_ids"] == ["d1"]


def test_geometry_change_fails():
    initial, final = bundles()
    final["decisions"][0]["x"] += 0.2
    r = evaluate_query_map_bundle(initial, final)
    assert r["checks"]["geometry_preserved_after_enrichment"] is False


def test_bad_source_and_duplicate_fail():
    initial, final = bundles()
    final["decisions"][0]["canonical_url"] = "https://example.com/d1"
    final["decisions"].append(dict(final["decisions"][1]))
    r = evaluate_query_map_bundle(initial, final)
    assert r["checks"]["source_urls_valid"] is False
    assert r["checks"]["duplicate_free"] is False


def test_geometry_signature_order_independent():
    initial, _ = bundles()
    reverse = dict(initial)
    reverse["decisions"] = list(reversed(initial["decisions"]))
    assert geometry_signature(initial) == geometry_signature(reverse)
