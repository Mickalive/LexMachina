"""Offline replay must survive page-size drift in the committed OpenCaseLaw cache.

The adapter cache key includes the search ``limit``.  The product cache holds
real answers for the four frozen reality questions at several recorded page
sizes (10/12/25/30/...), while the query pipeline derives 25 or 37 from
``top_n``.  Before ``query.cache_replay.QuestionMatchTransport`` this made
``retrieval_mode="fixture"`` raise ``OpenCaseLaw retrieval returned no
decisions`` for questions whose answer was already on disk.

These tests pin the narrow contract:

* exact request keys still win;
* a search miss may reuse a recorded page for the SAME query text, language
  and all other request params, ignoring only ``limit``;
* a different query, language, offset or sort/fields selection never matches;
* the four frozen questions are renderable offline at the server's default
  ``n=150`` without network access.
"""
from __future__ import annotations

import json
import socket
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "product"
for _p in (str(PRODUCT), str(ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from query import pipeline as pl  # noqa: E402  (also puts ocl_adapter on sys.path)
from query import run_query_first_page, run_query_initial  # noqa: E402
from query.bundle import validate_bundle  # noqa: E402
from query.cache_replay import QuestionMatchTransport  # noqa: E402
from reality_check import LEGS  # noqa: E402

from ocl_adapter.cache import FileCache  # noqa: E402


def _no_network(*_a, **_k):  # pragma: no cover - executed by every replay test
    raise AssertionError("fixture replay attempted network access")


def _search_body(*ids: str) -> str:
    return json.dumps({
        "results": [
            {
                "decision_id": decision_id,
                "court": "bge",
                "language": "de",
                "docket_number": decision_id,
                "decision_date": "2024-01-01",
                "regeste": "synthetic test record",
            }
            for decision_id in ids
        ],
        "total": len(ids),
        "returned": len(ids),
        "has_more": False,
    })


def _put(cache_dir: Path, *, query: str, limit: int, language: str | None = None,
         offset: int = 0, sort: str = "relevance", fields: str = "full",
         ids=("bge_1",)) -> str:
    params = {
        "query": query,
        "limit": limit,
        "offset": offset,
        "sort": sort,
        "fields": fields,
        "include_pinpoint": "false",
    }
    if language:
        params["language"] = language
    cache = FileCache(cache_dir)
    return cache.put_response(
        "/decisions", params, status=200, body=_search_body(*ids),
        url=f"https://example.invalid/decisions?query={query}&limit={limit}",
        fetched_at=1_700_000_000.0,
    )


def _request_params(*, query: str, limit: int, language: str | None = None,
                    offset: int = 0, sort: str = "relevance",
                    fields: str = "full") -> dict:
    params = {
        "query": query,
        "limit": limit,
        "offset": offset,
        "sort": sort,
        "fields": fields,
        "include_pinpoint": "false",
    }
    if language:
        params["language"] = language
    return params


def test_exact_key_still_wins(tmp_path):
    cache_dir = tmp_path / "cache"
    exact_key = _put(cache_dir, query="Q", limit=25, ids=("bge_exact",))
    _put(cache_dir, query="Q", limit=12, ids=("bge_larger_page",))

    transport = QuestionMatchTransport(cache_dir)
    response = transport.get("/decisions", _request_params(query="Q", limit=25))

    assert response.ok
    assert response.from_cache is True
    assert "bge_exact" in response.body
    assert transport.exact_hits == 1
    assert transport.question_matches == 0
    # the exact response really is the one stored under the requested key
    assert response.body == FileCache(cache_dir).get(exact_key)["body"]


def test_page_size_drift_matches_the_same_question_and_largest_page(tmp_path):
    cache_dir = tmp_path / "cache"
    _put(cache_dir, query="Q", limit=10, ids=("bge_small",))
    _put(cache_dir, query="Q", limit=12, ids=("bge_large",))

    transport = QuestionMatchTransport(cache_dir)
    response = transport.get("/decisions", _request_params(query="Q", limit=25))

    assert response.ok and response.from_cache is True
    assert "bge_large" in response.body, "largest recorded page should be preferred"
    assert transport.question_matches == 1


@pytest.mark.parametrize("variant", [
    {"query": "OTHER", "limit": 25},
    {"query": "Q", "limit": 25, "language": "fr"},
    {"query": "Q", "limit": 25, "offset": 12},
    {"query": "Q", "limit": 25, "sort": "date_desc"},
    {"query": "Q", "limit": 25, "fields": "snippet"},
])
def test_question_match_never_crosses_a_semantic_parameter(tmp_path, variant):
    cache_dir = tmp_path / "cache"
    _put(cache_dir, query="Q", limit=25, language="de", ids=("bge_de",))

    transport = QuestionMatchTransport(cache_dir)
    response = transport.get("/decisions", _request_params(**variant))

    assert response.ok is False
    assert response.error == "cache_miss"
    assert transport.question_matches == 0
    assert transport.misses == 1


def test_extra_cached_filter_does_not_match_a_request_without_it(tmp_path):
    """A cached entry carrying an unrequested filter is a different request."""
    cache_dir = tmp_path / "cache"
    cache = FileCache(cache_dir)
    params = _request_params(query="Q", limit=12)
    params["channel"] = "statute"
    cache.put_response("/decisions", params, status=200, body=_search_body("bge_1"),
                       url="https://example.invalid/decisions", fetched_at=1_700_000_000.0)

    transport = QuestionMatchTransport(cache_dir)
    response = transport.get("/decisions", _request_params(query="Q", limit=25))

    assert response.ok is False
    assert transport.question_matches == 0


def test_non_search_paths_are_not_question_matched(tmp_path):
    cache_dir = tmp_path / "cache"
    _put(cache_dir, query="Q", limit=25, ids=("bge_1",))
    transport = QuestionMatchTransport(cache_dir)

    response = transport.get("/leading-cases", {"query": "Q", "limit": 10})

    assert response.ok is False
    assert transport.question_matches == 0


def test_question_match_ignores_limit_but_honours_language(tmp_path):
    cache_dir = tmp_path / "cache"
    _put(cache_dir, query="Q", limit=10, language="fr", ids=("bge_fr",))
    transport = QuestionMatchTransport(cache_dir)

    hit = transport.get("/decisions", _request_params(query="Q", limit=25, language="fr"))
    miss = transport.get("/decisions", _request_params(query="Q", limit=25, language="de"))

    assert hit.ok and "bge_fr" in hit.body
    assert miss.ok is False


@pytest.mark.parametrize("slug", ["rent-default", "petty-theft-dismissal",
                                  "corporate-criminal-liability",
                                  "business-judgment-rule"])
def test_all_frozen_questions_render_offline_at_server_default_n(monkeypatch, slug):
    """The server's default ``n=150`` must render every frozen question offline."""
    monkeypatch.setattr(socket.socket, "connect", _no_network)

    bundle = run_query_first_page(LEGS[slug], top_n=150, retrieval_mode="fixture")

    assert validate_bundle(bundle) == []
    assert bundle["decisions"], f"{slug}: no decisions replayed"
    assert bundle["provenance"]["product_fixture_replay"]["network"] == "none"
    for decision in bundle["decisions"]:
        assert isinstance(decision.get("x"), (int, float))
        assert isinstance(decision.get("y"), (int, float))
        assert decision.get("cluster_id") is not None
        assert decision.get("canonical_url")


GERMAN_RENT_QUESTION = (
    "Unter welchen Voraussetzungen kann der Vermieter einen Wohnmietvertrag "
    "wegen Zahlungsverzug kündigen, und welche Ausnahmen oder Grenzen der "
    "Rechtsprechung bestehen nach Schweizer Recht?"
)


def test_german_rent_question_replays_where_exact_config_replay_used_to_fail(monkeypatch):
    """This question is recorded at limit=10/12; the full pipeline asks 25.

    Concrete regression: the answer was on disk but the exact-key replay
    raised 'no decisions'.  It must now replay through the question-match
    transport with provenance naming the fallback.
    """
    monkeypatch.setattr(socket.socket, "connect", _no_network)

    bundle = run_query_initial(GERMAN_RENT_QUESTION, top_n=100,
                               retrieval_mode="fixture")

    replay = bundle["provenance"]["product_fixture_replay"]
    assert replay["source"] == "product_query_cache_question_match_replay"
    assert replay["question_match"]["question_matches"] >= 1
    assert replay["n_candidates"] >= len(bundle.get("decisions") or [])
    assert bundle["decisions"]
    assert validate_bundle(bundle) == []


def test_frozen_rent_question_at_n150_names_the_fallback(monkeypatch):
    """The server default (n=150 -> page 37) is not the recorded 41-page key."""
    monkeypatch.setattr(socket.socket, "connect", _no_network)

    bundle = run_query_first_page(LEGS["rent-default"], top_n=150,
                                  retrieval_mode="fixture")

    replay = bundle["provenance"]["product_fixture_replay"]
    assert replay["source"] == "product_query_cache_question_match_replay"
    assert replay["question_match"]["question_matches"] >= 1
    assert bundle["decisions"]


def test_unknown_question_still_fails_closed(monkeypatch):
    """Nothing is invented: a question absent from the cache still raises."""
    monkeypatch.setattr(socket.socket, "connect", _no_network)
    with pytest.raises(RuntimeError, match="returned no decisions"):
        pl.run_query_initial("Question that was never cached anywhere 4f7c1a",
                             top_n=100, retrieval_mode="fixture")


@pytest.mark.parametrize("slug", ["rent-default", "petty-theft-dismissal",
                                  "corporate-criminal-liability",
                                  "business-judgment-rule"])
def test_shipped_server_first_page_works_for_every_frozen_question(monkeypatch, slug):
    """The shipped fixture server's default request must return a renderable map.

    This is the developer-facing path from ``product/query_app.py --fixture``:
    one command, submit a real Swiss-law question, see a map.  Before the
    page-size-tolerant replay, the default ``n=150`` raised 500 for three of
    the four frozen questions.
    """
    import json
    import threading
    import urllib.parse
    import urllib.request
    from concurrent.futures import ThreadPoolExecutor

    import query_app

    # Isolate the module-global job pool so this test cannot starve or shut
    # down the pool used by any later server test in the same process.
    pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="test-fixture-replay")
    monkeypatch.setattr(query_app, "POOL", pool)
    real_connect = socket.socket.connect

    def _loopback_only(self, address):
        host = address[0] if isinstance(address, tuple) else address
        if host not in {"127.0.0.1", "::1", "localhost"}:
            raise AssertionError(f"fixture server attempted remote network access: {address!r}")
        return real_connect(self, address)

    monkeypatch.setattr(socket.socket, "connect", _loopback_only)
    server = query_app.make_server("127.0.0.1", 0, fixture_mode=True, verbose=False)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        query = urllib.parse.quote(LEGS[slug])
        url = f"http://127.0.0.1:{server.server_address[1]}/api/query/start?q={query}"
        with urllib.request.urlopen(url, timeout=120) as response:
            payload = json.load(response)
    finally:
        server.shutdown()
        server.server_close()
        pool.shutdown(wait=False, cancel_futures=True)

    assert "error" not in payload, payload.get("error")
    bundle = payload["bundle"]
    assert validate_bundle(bundle) == []
    assert bundle["decisions"], f"{slug}: /api/query/start returned an empty map"
    replay = bundle["provenance"]["product_fixture_replay"]
    assert replay["network"] == "none"
    assert replay["source"] in {
        "canonical_frontier_fixture_scenario",
        "product_query_cache_live_config_replay",
        "product_query_cache_question_match_replay",
    }
