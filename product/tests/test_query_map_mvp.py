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
from query import relevance as relevance_mod
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
    assert len(b["decisions"]) == 100
    assert b["provenance"]["product_selection"]["served_decisions"] == 100
    assert b["provenance"]["product_selection"]["requested_top_n"] == 100
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

    rent_variants = build_variants(
        "Sous quelles conditions un bailleur peut-il résilier un bail d'habitation pour retard dans le paiement du loyer ?",
        include_language_filters=False,
    )
    rent_texts = {v.text for v in rent_variants}
    assert "Art. 257d Abs. 2 OR Kündigungsfrist 30 Tage Ende eines Monats" in rent_texts


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


def test_reranker_remote_safeguard_lifts_index_top_judgment_when_local_is_silent():
    """Observed 2026-10-16 (petty-theft leg): the source index ranked the
    directly on-point Federal Supreme Court dismissal authority remote-#3, but
    cross-language TF-IDF similarity collapsed (~0.017: the shared dismissal
    terms saturate IDF across a dismissal-heavy pool) and the unhydrated
    snippet carries no article number, so the local blend buried it at rank
    50 — outside every evidence pack and the answer then ignored the
    controlling authority.  The safeguard defers to the index in a bounded way
    instead of vetoing it.  The flooded pool below reproduces the mechanism:
    German dismissal terms saturate IDF, so only the French-overlap row keeps
    discriminating local similarity."""
    french = (
        "Un vol de faible valeur commis par un employe justifie-t-il un "
        "licenciement immediat selon l'art. 337 CO ?"
    )
    german_core = "fristlose Kundigung Diebstahl Arbeitnehmer geringfugig Vertrauen "
    decisions = [
        {
            "decision_id": "DIRECT-TF",
            "court": "bger",
            "score": 49.0,
            "title": "Arbeitsrecht",
            "citation": "TF 4A_177/2017",
            "regeste": "",
            "snippet": (
                "Das Bezirksgericht wies die Klage ab: die " + german_core
                + "rechtfertigt die Kundigung. "
                "Bundesgericht Verweigerung sachverhalt erwogen."
            ),
        },
        {
            "decision_id": "REMOTE-TOP-FR",
            "court": "ge_gerichte",
            "score": 53.0,
            "title": "Contrat de travail",
            "citation": "GE CAPH",
            "regeste": "",
            "snippet": french + " employe voleur circonstance attenuante specificite",
        },
    ]
    for i in range(40):
        decisions.append({
            "decision_id": f"FILL-{i:02d}",
            "court": "ge_gerichte",
            "score": 30.0 - i * 0.1,
            "title": "t",
            "citation": "c",
            "regeste": "",
            "snippet": german_core + (
                f"entscheidung nummer {i} kanton das gericht stellt fest dass "
                "das arbeitsverhaltnis beendet wurde."
            ),
        })
    bundle = {
        "query": french,
        "query_variants": [
            "geringfugiger Diebstahl fristlose Kundigung",
            "Diebstahl Arbeitnehmer fristlose Kundigung",
        ],
        "decisions": decisions,
        "provenance": {},
    }
    reranked = rerank_product_bundle(bundle)
    order = [d["decision_id"] for d in reranked["decisions"]]
    by_id = {d["decision_id"]: d for d in reranked["decisions"]}
    # local similarity is genuinely silent on the direct authority ...
    assert by_id["DIRECT-TF"]["query_similarity"] < 0.05
    # ... so the index's top judgment stays usable: inside the evidence head
    assert order.index("DIRECT-TF") <= 1, order
    assert by_id["DIRECT-TF"]["remote_safeguard"] is True
    # the genuinely on-point French row still wins outright, without safeguard
    assert order[0] == "REMOTE-TOP-FR"
    assert by_id["REMOTE-TOP-FR"]["remote_safeguard"] is False
    # exactly one row lifted: the safeguard is narrow, not a blanket boost
    assert reranked["provenance"]["product_rerank"]["remote_safeguard"]["n_lifted"] == 1


def test_reranker_head_recall_places_remote_top_federal_row_in_evidence_head():
    """The safeguard alone left the observed authority at rank 16 — still out
    of the top-10 hydration/evidence packs.  Remote-head recall is the backstop
    for the product invariant: a federal row the source index ranked top-5
    must reach the generator.  Bounded: at most 3 rows move, head rows are
    never reordered among themselves, non-federal and remote-tail rows never
    move."""
    decisions = []
    for i in range(30):
        decisions.append({
            "decision_id": f"CANT-{i:02d}",
            "court": "ge_gerichte",
            "score": 60.0 - i,
            "title": "Contrat de travail licenciement",
            "citation": f"GE {i}",
            "regeste": "",
            "snippet": "contrat de travail licenciement employe circonstances " * 8,
        })
    decisions.append({
        "decision_id": "DIRECT-TF",
        "court": "bger",
        "score": 59.5,  # remote top-5, but lexically silent below
        "title": "Arbeitsrecht",
        "citation": "TF 4A_177/2017",
        "regeste": "",
        "snippet": "curia deliberanda est sine mora.",  # short, zero overlap: no local signal
    })
    bundle = {
        "query": "licenciement contrat de travail circonstances",
        "query_variants": [],
        "decisions": decisions,
        "provenance": {},
    }
    reranked = rerank_product_bundle(bundle)
    order = [d["decision_id"] for d in reranked["decisions"]]
    by_id = {d["decision_id"]: d for d in reranked["decisions"]}
    assert order.index("DIRECT-TF") < 10, order[:12]
    assert by_id["DIRECT-TF"]["remote_head_recall"] is True
    moved = reranked["provenance"]["product_rerank"]["remote_head_recall"]["moved"]
    assert len(moved) == 1 and moved[0]["decision_id"] == "DIRECT-TF"
    assert moved[0]["remote_rank"] <= 5 and moved[0]["from_rank"] > 10
    # ranks stay dense and unique after the splice
    assert sorted(d["rank"] for d in reranked["decisions"]) == list(range(1, 32))


def _silent_federal_pool(n_fill=30):
    """French-question pool where German federal rows are lexically silent.

    Mirrors the observed 2026-10-16 business-judgment-rule shape: the
    federal controlling authorities sit at mixed-channel raw-score remote
    ranks 6..15 (see REMOTE_HEAD_RECALL_REMOTE_TOP's measured-semantics
    note) but cross-language TF-IDF similarity collapses, so local scoring
    buries them below the evidence head.
    """
    french = (
        "Dans quelles conditions le juge suisse s'abstient-il de revoir une "
        "decision commerciale du conseil d'administration ?"
    )
    decisions = []
    for i in range(n_fill):
        decisions.append({
            "decision_id": f"CANT-{i:02d}",
            "court": "ge_gerichte",
            "score": 90.0 - i,
            "title": "Decision commerciale",
            "citation": f"GE {i}",
            "regeste": "",
            "snippet": "decision commerciale conseil administration juge abstient revoir " * 6,
        })
    return french, decisions


def test_reranker_variant_contract_string_list_reaches_query_document():
    """Public entry point: query_variants is the adapter contract's
    ``list[str]`` — variant text must reach the TF-IDF query document and
    provenance must record the measured shape.

    Measured truth (2026-10-16, auditor replay): the accepted adapter
    flattens its variant dicts to ``[v.get("text", "")]`` before the product
    sees them, so the dict form cannot reach the reranker and
    ``query_variant_kinds`` is always ['text'].  The old in-isolation helper
    test could not fail for the behaviour it documented (auditor mutation:
    call site reverted to str(), helper retained, file stayed green); this
    test asserts the real contract through ``rerank_product_bundle``:
    variant tokens demonstrably change the query document (a decision
    containing the token scores > 0) and provenance records
    query_variants_used/query_variant_kinds per the string-list contract.
    """
    distinctive = "zweckmabigkeitsprufung"  # not in the query, not stopwords
    decisions = [
        {"decision_id": "VARIANT-HIT", "court": "bger", "score": 50.0,
         "title": "Verwaltungsrat", "citation": "TF 1", "regeste": "",
         "snippet": f"der Verwaltungsrat handelte mit {distinctive} und Sorgfalt."},
        {"decision_id": "VARIANT-MISS", "court": "bger", "score": 49.0,
         "title": "Verwaltungsrat", "citation": "TF 2", "regeste": "",
         "snippet": "curia deliberanda est sine mora."},
    ]
    for variants in ([], [distinctive]):
        bundle = {"query": "conseil d'administration",
                  "query_variants": variants, "decisions": decisions,
                  "provenance": {}}
        reranked = rerank_product_bundle(bundle)
        by_id = {d["decision_id"]: d for d in reranked["decisions"]}
        prov = reranked["provenance"]["product_rerank"]
        if variants:
            assert by_id["VARIANT-HIT"]["query_similarity"] > 0
            assert by_id["VARIANT-MISS"]["query_similarity"] == 0
            assert prov["query_variants_used"] == 1
        else:
            assert by_id["VARIANT-HIT"]["query_similarity"] == 0
            assert prov["query_variants_used"] == 0
        # provenance shape per the string-list adapter contract (measured:
        # kinds are always ['text']; the dict form cannot reach here)
        assert prov["query_variant_kinds"] == (["text"] if variants else [])
        assert "variant_id" not in prov["query_variant_kinds"]


def test_reranker_recalls_federal_row_at_remote_rank_12_buried_by_language_gap(monkeypatch):
    """Observed 2026-10-16 (business-judgment-rule leg): the five frozen TF
    BJR authorities sat at remote ranks 12/13/14/17/31 with local similarity
    0.000-0.016, so the old top-5 window recalled only off-domain federal
    rows while every controlling authority stayed below the hydration head and
    the answer cited none of them.  "Remote rank" is the global mixed-channel
    raw-score ordering documented on REMOTE_HEAD_RECALL_REMOTE_TOP, not a
    source page position.  A federal row at remote rank 12 must now reach the
    evidence head; with the old window it must not (pins the window's role
    without touching production constants)."""
    french, decisions = _silent_federal_pool()
    decisions.append({
        "decision_id": "DIRECT-TF",
        "court": "bger",
        "score": 79.5,  # remote rank 12 in the mixed-channel raw-score sort, lexically silent below
        "title": "Verwaltungsrat",
        "citation": "TF 4A_219/2015",
        "regeste": "",
        "snippet": "curia deliberanda est sine mora.",
    })
    bundle = {"query": french, "query_variants": [], "decisions": decisions,
              "provenance": {}}
    reranked = rerank_product_bundle(bundle)
    order = [d["decision_id"] for d in reranked["decisions"]]
    by_id = {d["decision_id"]: d for d in reranked["decisions"]}
    assert order.index("DIRECT-TF") < 10, order[:12]
    assert by_id["DIRECT-TF"]["remote_head_recall"] is True
    moved = reranked["provenance"]["product_rerank"]["remote_head_recall"]["moved"]
    assert any(m["decision_id"] == "DIRECT-TF" and m["remote_rank"] == 12 for m in moved)
    assert len(moved) <= 3  # displacement stays bounded

    # negative control: the retired top-5 window leaves the same row buried
    monkeypatch.setattr(relevance_mod, "REMOTE_HEAD_RECALL_REMOTE_TOP", 5)
    buried = rerank_product_bundle(
        {"query": french, "query_variants": [], "decisions": decisions,
         "provenance": {}})
    by_id_old = {d["decision_id"]: d for d in buried["decisions"]}
    order_old = [d["decision_id"] for d in buried["decisions"]]
    assert order_old.index("DIRECT-TF") >= 10, order_old[:12]
    assert by_id_old["DIRECT-TF"]["remote_head_recall"] is False


# --------------------------------------------------------------------------- #
# one decision, one point: court + docket identity merge
# --------------------------------------------------------------------------- #
def _row(decision_id, docket, *, court="bvger", date="", status="pending", rank=10, text=""):
    return {
        "decision_id": decision_id,
        "court": court,
        "language": "de",
        "rank": rank,
        "score": 1.0,
        "provenance": "test",
        "snippet": text or f"{decision_id} snippet",
        "citation": docket,
        "docket_number": docket,
        "decision_date": date,
        "detail_status": status,
        "channels": ["citation.incoming"] if status == "pending" else ["search"],
        "counter_status": "none",
        "canonical_url": f"https://mcp.opencaselaw.ch/entscheid/{decision_id}",
        "title": None, "regeste": None, "full_text": text or None,
    }


def test_same_decision_arrives_twice_under_two_ids_is_one_row():
    """Live run 38812599575: A-2789/2024 sat on the map twice.

    Both rows were citation-channel shells, so the run-time admissibility check
    refused the question (``citation_duplicates``).  Court + docket identify one
    decision, so the product merges them and exports which ids went away.
    """
    from query.pipeline import merge_duplicate_identities

    rows = [
        _row("bvger_A-2789_2024", "A-2789/2024", date="2025-07-04", rank=148),
        _row("bvger_A-2789_2024_d20240318", "A-2789/2024", date="2024-03-18", rank=149),
        _row("bge_132_III_257", "132 III 257", court="bge", date="2006-02-08", rank=3),
    ]
    kept, merges = merge_duplicate_identities(rows)
    ids = [d["decision_id"] for d in kept]
    assert ids == ["bvger_A-2789_2024_d20240318", "bge_132_III_257"]
    assert merges[0]["merged_decision_ids"] == ["bvger_A-2789_2024"]
    assert merges[0]["identity"] == {"court": "bvger", "docket": "a27892024"}
    # the dropped row's retrieval channel survives on the kept row
    assert kept[0]["merged_duplicate_ids"] == ["bvger_A-2789_2024"]


def test_hydrated_row_wins_over_a_shell_of_the_same_decision_and_keeps_its_text():
    """Run 38799024807 shipped the milder form: a shell next to a search hit.

    The shell carried a different citation string for the same decision
    ("A-1979/2024" vs "BVGer A-1979/2024 vom 26. März 2024").  Evidence wins,
    so the hydrated row is kept and the shell is merged into it.
    """
    from query.pipeline import merge_duplicate_identities

    rows = [
        _row("bvger_A-1979_2024", "A-1979/2024", date="2025-03-28", status="pending", rank=101),
        _row("bvger_A-1979_2024_d20240326", "A-1979/2024", date="2024-03-26",
             status="search_hit", rank=16, text="Das Bundesgericht erwacht."),
        _row("bge_119_IA_134", "119 IA 134", court="bge", date="1993-06-08", rank=7),
    ]
    kept, merges = merge_duplicate_identities(rows)
    assert [d["decision_id"] for d in kept] == [
        "bvger_A-1979_2024_d20240326", "bge_119_IA_134",
    ]
    assert kept[0]["full_text"] == "Das Bundesgericht erwacht."
    assert merges[0]["kept_detail_status"] == "search_hit"
    assert merges[0]["merged_decision_ids"] == ["bvger_A-1979_2024"]


def test_identity_merge_is_a_no_op_when_no_two_rows_share_a_docket():
    from query.pipeline import merge_duplicate_identities

    rows = [
        _row("bge_132_III_257", "132 III 257", court="bge", rank=1),
        _row("bge_132_III_115", "132 III 115", court="bge", rank=2),
        _row("no_docket_row", "", rank=3),
    ]
    kept, merges = merge_duplicate_identities(rows)
    assert merges == []
    assert [d["decision_id"] for d in kept] == [
        "bge_132_III_257", "bge_132_III_115", "no_docket_row",
    ]


def test_merged_map_has_no_shared_citation_string_between_decisions():
    from query.pipeline import merge_duplicate_identities

    rows = [
        _row("bvger_A-2789_2024", "A-2789/2024", date="2025-07-04", rank=148),
        _row("bvger_A-2789_2024_d20240318", "A-2789/2024", date="2024-03-18", rank=149),
    ]
    kept, _ = merge_duplicate_identities(rows)
    citations = [d["citation"] for d in kept]
    assert len(citations) == len(set(citations)), "one decision, one citation string"
