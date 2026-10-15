"""LEX v45 query-map integration tests.

All tests are deterministic/offline: they replay frozen real OpenCaseLaw
responses and use the generative-audit fixture provider.  Frontier component
suites test their own internals; this file tests the product seam.
"""
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "product"
sys.path.insert(0, str(PRODUCT))
sys.path.insert(0, str(ROOT))

from query import enrich_query_bundle, run_query_initial
from query.bundle import validate_bundle
from query.relevance import rerank_product_bundle
from ocl_adapter.expansion import build_variants

QUERY = "Kündigung Mietvertrag Mietrecht"


def initial(n=100):
    bundle = run_query_initial(QUERY, top_n=n, retrieval_mode="fixture")
    assert validate_bundle(bundle) == []
    return bundle


def test_initial_phase_is_real_map_not_fake_answer():
    b = initial()
    assert b["provenance"]["phase"] == "map_ready"
    assert b["provenance"]["fixture_mode"] is True
    assert len(b["decisions"]) >= 100
    assert len(b["clusters"]) >= 2
    assert b["answer"]["status"] == "pending"
    assert b["answer"]["cited_decision_ids"] == []


def test_verified_opencaselaw_urls_and_no_guessed_endpoint():
    b = initial()
    assert all(
        d["canonical_url"].startswith("https://mcp.opencaselaw.ch/")
        for d in b["decisions"][:20]
    )
    corpus_source = (PRODUCT / "query" / "corpus.py").read_text(encoding="utf-8")
    assert "opencaselaw.org/api/search" not in corpus_source
    assert "www.opencaselaw.org/api/search" not in corpus_source


def test_map_coordinates_finite_bounded_and_clustered():
    b = initial()
    cluster_ids = {c["cluster_id"] for c in b["clusters"]}
    for d in b["decisions"]:
        assert math.isfinite(d["x"]) and math.isfinite(d["y"])
        assert -1.0001 <= d["x"] <= 1.0001
        assert -1.0001 <= d["y"] <= 1.0001
        assert d["cluster_id"] in cluster_ids
    assert any(d.get("is_outlier") for d in b["decisions"])


def test_map_is_deterministic_in_one_numeric_stack():
    a = initial()
    b = initial()
    ga = {d["decision_id"]: (d["x"], d["y"], d["cluster_id"], d.get("is_outlier")) for d in a["decisions"]}
    gb = {d["decision_id"]: (d["x"], d["y"], d["cluster_id"], d.get("is_outlier")) for d in b["decisions"]}
    assert ga == gb


def test_fixture_replay_preserves_multilingual_retrieval():
    b = initial()
    langs = {d["language"] for d in b["decisions"]}
    assert {"de", "fr", "it"} <= langs


def test_enrichment_is_source_constrained_and_does_not_move_map():
    first = initial()
    geo = {d["decision_id"]: (d["x"], d["y"], d["cluster_id"], d.get("is_outlier")) for d in first["decisions"]}

    final = enrich_query_bundle(
        first,
        retrieval_mode="fixture",
        fixture_generation=True,
        evidence_count=12,
    )
    assert validate_bundle(final) == []
    assert final["provenance"]["phase"] == "complete"
    assert final["answer"]["status"] == "ready"
    assert final["answer"]["method"] == "generative_audit_llm_v2"

    ids = {d["decision_id"] for d in final["decisions"]}
    assert final["answer"]["cited_decision_ids"]
    assert set(final["answer"]["cited_decision_ids"]) <= ids

    after = {d["decision_id"]: (d["x"], d["y"], d["cluster_id"], d.get("is_outlier")) for d in final["decisions"]}
    assert after == geo


def test_independent_adversarial_result_patches_visible_counter_status():
    first = initial()
    final = enrich_query_bundle(
        first,
        retrieval_mode="fixture",
        fixture_generation=True,
        evidence_count=12,
    )
    ga = final["provenance"]["generative_audit"]
    assert ga["adversarial"]["method"] == "fixture_adversarial_v2"
    counters = [
        d for d in final["decisions"]
        if d.get("counter_status") in {"candidate-limiting", "candidate-contrary"}
    ]
    assert counters
    assert counters[0].get("counter_uncertainty") is not None


def test_fixture_mode_is_explicit_not_a_live_padding_source():
    b = initial()
    retrieval = b["provenance"]["retrieval"]
    assert b["provenance"]["fixture_mode"] is True
    assert retrieval["n_candidates"] == len(b["decisions"])
    pipeline_source = (PRODUCT / "query" / "pipeline.py").read_text(encoding="utf-8")
    assert 'if mode == "fixture"' in pipeline_source
    assert "load_fixture_decisions" not in pipeline_source


def test_one_command_server_contract_start_then_enrich():
    """One command -> map -> answer, now over the progressive job API.

    Contract change in run 38665681083: ``/api/query/enrich`` answers 202
    immediately and the client polls ``/api/query/status`` (a 136.79 s start
    plus a 150.70 s enrich made the blocking form unusable in a browser).
    ``wait_s`` keeps the blocking single-call form for scripts and CI, and is
    asserted at the end of this test.
    """
    import json
    import threading
    import urllib.parse
    import urllib.request
    from query_app import make_server

    srv = make_server("127.0.0.1", 0, fixture_mode=True, verbose=False)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        with urllib.request.urlopen(base + "/api/health", timeout=10) as resp:
            health = json.loads(resp.read())
        assert health["ok"] is True
        assert health["direction_version"] == 45

        url = base + "/api/query/start?" + urllib.parse.urlencode({"q": QUERY, "n": 100})
        with urllib.request.urlopen(url, timeout=60) as resp:
            first = json.loads(resp.read())
        assert first["bundle"]["provenance"]["phase"] == "map_ready"
        assert first["bundle"]["provenance"]["progressive"]["expanded"] is False
        run_id = first["run_id"]

        # Expansion is already running in the background; the request returned.
        assert first["expand_started"] is True
        deadline = time.time() + 120
        while time.time() < deadline:
            with urllib.request.urlopen(
                base + "/api/query/status?" + urllib.parse.urlencode({"run_id": run_id}), timeout=30
            ) as resp:
                status = json.loads(resp.read())
            if status["jobs"]["expand"]["status"] in {"done", "error"}:
                break
            time.sleep(0.2)
        assert status["jobs"]["expand"]["status"] == "done", status["jobs"]["expand"]

        with urllib.request.urlopen(
            base + "/api/query/enrich?" + urllib.parse.urlencode({"run_id": run_id}), timeout=30
        ) as resp:
            ack = json.loads(resp.read())
            assert resp.status == 202
        assert ack["status"] == "running"

        deadline = time.time() + 120
        while time.time() < deadline:
            with urllib.request.urlopen(
                base + "/api/query/status?" + urllib.parse.urlencode({"run_id": run_id}), timeout=30
            ) as resp:
                status = json.loads(resp.read())
            if status["jobs"]["enrich"]["status"] in {"done", "error"}:
                break
            time.sleep(0.2)
        assert status["jobs"]["enrich"]["status"] == "done", status["jobs"]["enrich"]

        with urllib.request.urlopen(
            base + "/api/query/bundle?" + urllib.parse.urlencode({"run_id": run_id}), timeout=30
        ) as resp:
            second = json.loads(resp.read())
        assert second["run_id"] == run_id
        assert second["bundle"]["provenance"]["phase"] == "complete"
        assert second["bundle"]["answer"]["status"] == "ready"

        # Backwards-compatible blocking form for scripts/CI.
        with urllib.request.urlopen(
            base + "/api/query/start?" + urllib.parse.urlencode({"q": QUERY, "n": 100}), timeout=60
        ) as resp:
            blocking_run = json.loads(resp.read())["run_id"]
        with urllib.request.urlopen(
            base + "/api/query/enrich?"
            + urllib.parse.urlencode({"run_id": blocking_run, "wait_s": 120}),
            timeout=180,
        ) as resp:
            blocking = json.loads(resp.read())
        assert blocking["bundle"]["provenance"]["phase"] == "complete"
    finally:
        srv.shutdown()
        srv.server_close()
        thread.join(timeout=5)


def test_legal_query_expansion_bridges_swiss_statute_languages_and_doctrine():
    variants = build_variants(
        "Dans quelles conditions la Business Judgment Rule protège-t-elle le conseil d'administration selon l'art. 754 CO ?",
        include_language_filters=False,
    )
    texts = {v.text for v in variants}
    assert "Art. 754 OR" in texts
    assert any("Geschäftsentscheid" in text and "Verwaltungsrat" in text for text in texts)
    assert any(v.kind == "legal_concept" for v in variants)

    theft_variants = build_variants(
        "Un vol de faible valeur commis par un employé justifie-t-il un licenciement immédiat selon l'art. 337 CO ?",
        include_language_filters=False,
    )
    theft_texts = {v.text for v in theft_variants}
    assert "Art. 337 OR" in theft_texts
    assert "Bagatelldiebstahl fristlose Kündigung" in theft_texts
    assert "geringfügiger Diebstahl fristlose Kündigung" in theft_texts


def test_product_reranker_prefers_direct_legal_issue_over_broad_remote_hit():
    bundle = {
        "query": "Business Judgment Rule conseil d'administration",
        "query_variants": [
            "Business Judgment Rule Verwaltungsrat",
            "Geschäftsentscheid Verwaltungsrat angemessene Informationsbasis Interessenkonflikt",
        ],
        "decisions": [
            {
                "decision_id": "TAX",
                "court": "bger",
                "score": 99.0,
                "title": "Impôt",
                "citation": "TF tax",
                "regeste": "Déduction fiscale relative à une activité commerciale.",
                "snippet": "",
            },
            {
                "decision_id": "BJR",
                "court": "bger",
                "score": 1.0,
                "title": "Verwaltungsrat",
                "citation": "TF BJR",
                "regeste": (
                    "Geschäftsentscheid des Verwaltungsrats auf angemessener "
                    "Informationsbasis und frei von Interessenkonflikten."
                ),
                "snippet": "",
            },
        ],
        "provenance": {},
    }
    reranked = rerank_product_bundle(bundle)
    assert reranked["decisions"][0]["decision_id"] == "BJR"
    assert reranked["decisions"][0]["score"] > reranked["decisions"][1]["score"]
