"""Progressive query execution: first-page map, background expansion, job server.

Offline and deterministic (frozen OpenCaseLaw envelopes + fixture generation).

The defect these tests pin (measured live, run 38665681083): ``/api/query/start``
blocked **136.79 s** before the first point was drawn and ``/api/query/enrich`` a
further **150.70 s**, so the human-gate session began with ~2.3 minutes of empty
page.  The contract now is:

* one bounded upstream page -> a complete, valid map (seconds);
* the wider multi-channel retrieval runs as a background job and patches that
  map without moving a single point that was already rendered;
* generation + counter-authority run as a second job the browser polls;
* a double-click cannot start two model runs, and the server answers while they
  run.
"""
import json
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "product"
sys.path.insert(0, str(PRODUCT))
sys.path.insert(0, str(ROOT))

from query import expand_query_bundle, run_query_first_page
from query.bundle import validate_bundle
from query.qmap import build_map, fit_map_model, project_into_model

QUERY = "Kündigung Mietvertrag Mietrecht"


def _geo(bundle):
    return {
        d["decision_id"]: (d["x"], d["y"], d["cluster_id"], bool(d.get("is_outlier")))
        for d in bundle["decisions"]
    }


def _first(n=150):
    bundle = run_query_first_page(QUERY, top_n=n, retrieval_mode="fixture")
    assert validate_bundle(bundle) == []
    return bundle


# --------------------------------------------------------------------------
# stage 0: first page
# --------------------------------------------------------------------------

def test_first_page_is_a_complete_valid_map_not_a_placeholder():
    b = _first()
    assert b["provenance"]["phase"] == "map_ready"
    assert len(b["decisions"]) >= 50
    assert len(b["clusters"]) >= 2
    assert b["answer"]["status"] == "pending"
    assert b["answer"]["cited_decision_ids"] == []
    for d in b["decisions"]:
        assert -1.0001 <= d["x"] <= 1.0001 and -1.0001 <= d["y"] <= 1.0001
        assert d["canonical_url"].startswith("https://mcp.opencaselaw.ch/")


def test_first_page_declares_itself_partial_and_timed():
    prog = _first()["provenance"]["progressive"]
    assert prog["stage"] == "first_page"
    assert prog["expanded"] is False
    assert prog["target"] >= 100
    assert prog["first_page_total_s"] > 0
    timing = _first()["provenance"]["timing"]
    assert {"upstream_retrieval_s", "local_map_s", "n_decisions"} <= set(timing)


def test_first_page_does_not_ship_answer_or_counter_claims():
    b = _first()
    assert b["answer"]["status"] == "pending"
    assert all(d["counter_status"] == "none" for d in b["decisions"])


# --------------------------------------------------------------------------
# stage 1: background expansion
# --------------------------------------------------------------------------

def test_expansion_adds_candidates_and_keeps_the_rendered_map_fixed():
    first = _first()
    expanded = expand_query_bundle(first, retrieval_mode="fixture")
    assert validate_bundle(expanded) == []
    assert expanded["provenance"]["phase"] == "map_expanded"
    prog = expanded["provenance"]["progressive"]
    assert prog["expanded"] is True
    assert prog["points_moved"] == 0
    assert prog["n_after"] >= prog["n_before"] == len(first["decisions"])
    before, after = _geo(first), _geo(expanded)
    for did, geo in before.items():
        assert after[did] == geo, did


def test_expansion_keeps_cluster_ids_and_improves_cluster_labels():
    """Ids stay stable so no colour/label the researcher read changes meaning;
    labels are recomputed from the merged membership (more evidence, no move)."""
    first = _first()
    expanded = expand_query_bundle(first, retrieval_mode="fixture")
    ids_first = [c["cluster_id"] for c in first["clusters"]]
    ids_after = [c["cluster_id"] for c in expanded["clusters"]]
    assert ids_after == [cid for cid in ids_first if cid in set(ids_after)]
    for d in expanded["decisions"]:
        assert d["cluster_id"] in set(ids_after)
    assert all(c.get("label") for c in expanded["clusters"])
    assert len(expanded["clusters"]) == len(first["clusters"])


def test_first_page_uses_the_cluster_granularity_of_the_finished_map():
    from query.progressive import target_clusters

    first = _first(150)
    assert len(first["clusters"]) == target_clusters(150)
    assert first["provenance"]["progressive"]["target_clusters"] == target_clusters(150)


def test_expansion_keeps_counter_status_of_an_already_enriched_bundle():
    from query import enrich_query_bundle

    enriched = enrich_query_bundle(_first(), retrieval_mode="fixture", fixture_generation=True)
    counters = {d["decision_id"]: d["counter_status"] for d in enriched["decisions"]
                if d["counter_status"] not in ("none", None, "")}
    assert counters, "fixture generation must expose at least one counter authority"
    again = expand_query_bundle(enriched, retrieval_mode="fixture")
    after = {d["decision_id"]: d["counter_status"] for d in again["decisions"]
             if d["counter_status"] not in ("none", None, "")}
    assert after == counters
    assert again["answer"]["status"] == enriched["answer"]["status"]


def test_expansion_never_moves_the_answer_into_a_pending_state():
    first = _first()
    expanded = expand_query_bundle(first, retrieval_mode="fixture")
    assert expanded["answer"]["status"] == "pending"
    assert expanded["answer"]["cited_decision_ids"] == []


def test_expansion_records_upstream_and_local_time_separately():
    expanded = expand_query_bundle(_first(), retrieval_mode="fixture")
    timing = expanded["provenance"]["timing"]
    assert timing["expand_upstream_s"] >= 0
    assert timing["expand_local_s"] >= 0
    assert timing["n_decisions"] == len(expanded["decisions"])


def test_expansion_rejects_an_invalid_bundle_instead_of_silently_mapping_it():
    broken = _first()
    broken["decisions"] = []
    try:
        expand_query_bundle(broken, retrieval_mode="fixture")
    except ValueError as exc:
        assert "invalid bundle" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expansion accepted an invalid bundle")


# --------------------------------------------------------------------------
# map model: the mechanism behind "already rendered points never move"
# --------------------------------------------------------------------------

def test_map_model_projects_new_decisions_into_the_existing_space():
    words = ["kündigung", "mietrecht", "frist", "arbeitsvertrag", "sozialversicherung",
             "immobilien", "steuer", "family", "straf", "bankrecht"]
    ranked = [
        {"decision_id": f"d{i}",
         "regeste": " ".join([words[i % 10], words[(i // 3) % 10], words[(i // 7) % 10], f"w{i}"])}
        for i in range(20)
    ]
    base_decisions, base_clusters, _ = build_map(ranked)
    model = fit_map_model(ranked)
    fresh = [{"decision_id": "n1", "regeste": " ".join([words[0], words[1], "w3"])},
             {"decision_id": "n2", "regeste": " ".join([words[9], words[4], "w5"])}]
    projected = project_into_model(model, fresh)
    assert [p["decision_id"] for p in projected] == ["n1", "n2"]
    for p in projected:
        assert -1.0 <= p["x"] <= 1.0 and -1.0 <= p["y"] <= 1.0
        assert p["cluster_id"] in {c["cluster_id"] for c in base_clusters}
    merged, clusters, _ = build_map(ranked + fresh, model=model)
    frozen = {d["decision_id"]: (d["x"], d["y"], d["cluster_id"]) for d in base_decisions}
    assert all((d["x"], d["y"], d["cluster_id"]) == frozen[d["decision_id"]]
               for d in merged if d["decision_id"] in frozen)
    assert len(clusters) == len(base_clusters)


def test_expansion_never_touches_is_outlier_of_an_already_rendered_point():
    """Regression (live, run 38665681083): the merged refit re-flagged 15 outliers.

    Outlier status is a claim the researcher already read on screen ("weakly
    connected result worth inspecting"), so it must survive expansion exactly
    like coordinates and cluster membership.
    """
    from query.progressive import map_model_from_bundle

    words = ["kündigung", "mietrecht", "frist", "arbeitsvertrag", "sozialversicherung",
             "immobilien", "steuer", "family", "straf", "bankrecht"]
    ranked = [{"decision_id": f"d{i}",
               "regeste": " ".join([words[i % 10], words[(i // 3) % 10], f"wort{i}"])}
              for i in range(20)]
    base, clusters, _ = build_map(ranked)
    assert any(d.get("is_outlier") for d in base)
    model = map_model_from_bundle({"decisions": base, "clusters": clusters})
    flooded = ranked + [
        {"decision_id": f"clone{i}", "regeste": "kündigung mietrecht " + "wort0 " * 6}
        for i in range(40)
    ]
    merged, _clusters, _rel = build_map(flooded, model=model)
    base_flags = {d["decision_id"]: bool(d.get("is_outlier")) for d in base}
    assert len(base_flags) == 20
    for d in merged:
        if d["decision_id"] in base_flags:
            assert bool(d.get("is_outlier")) == base_flags[d["decision_id"]], d["decision_id"]


def test_map_model_is_deterministic_for_the_same_input():
    words = ["kündigung", "mietrecht", "frist", "arbeitsvertrag", "sozialversicherung",
             "immobilien", "steuer", "family", "straf", "bankrecht"]
    ranked = [{"decision_id": f"d{i}",
               "regeste": " ".join([words[i % 10], words[(i // 3) % 10], f"wort{i}"])}
              for i in range(15)]
    a = fit_map_model(ranked)
    b = fit_map_model(ranked)
    fresh = [{"decision_id": "x", "regeste": "mietrecht frist artikel 2"}]
    assert [p["x"] for p in project_into_model(a, fresh)] == [p["x"] for p in project_into_model(b, fresh)]


# --------------------------------------------------------------------------
# server: job contract
# --------------------------------------------------------------------------

class _Server:
    def __enter__(self):
        from query_app import make_server

        self.srv = make_server("127.0.0.1", 0, fixture_mode=True, verbose=False)
        self.thread = threading.Thread(target=self.srv.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.srv.server_address[1]}"
        return self

    def __exit__(self, *exc):
        self.srv.shutdown()
        self.srv.server_close()
        self.thread.join(timeout=5)
        return False

    def get(self, path, timeout=180):
        url = self.base + path
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read() or b"{}")


def _start(server, n=100):
    code, payload = server.get("/api/query/start?" + urllib.parse.urlencode({"q": QUERY, "n": n}))
    assert code == 200
    return payload


def _await_job(server, run_id, name, limit=120.0):
    deadline = time.time() + limit
    while time.time() < deadline:
        _code, st = server.get("/api/query/status?run_id=" + run_id)
        job = (st.get("jobs") or {}).get(name) or {}
        if job.get("status") in {"done", "error"}:
            return st, job
        time.sleep(0.1)
    raise AssertionError(f"job {name} did not finish within {limit}s")


def test_server_start_returns_a_map_and_runs_expansion_as_a_job():
    with _Server() as srv:
        payload = _start(srv)
        assert payload["bundle"]["provenance"]["progressive"]["stage"] == "first_page"
        assert payload["expand_started"] is True
        run_id = payload["run_id"]
        st, job = _await_job(srv, run_id, "expand")
        assert job["status"] == "done", job
        _code, data = srv.get("/api/query/bundle?run_id=" + run_id)
        assert data["bundle"]["provenance"]["progressive"]["expanded"] is True
        assert data["status"]["counts"]["decisions"] >= st["counts"]["decisions"]


def test_enrich_is_accepted_asynchronously_and_the_server_stays_responsive():
    with _Server() as srv:
        run_id = _start(srv)["run_id"]
        _st, _job = _await_job(srv, run_id, "expand")
        t0 = time.time()
        code, ack = srv.get("/api/query/enrich?run_id=" + run_id)
        assert code == 202, code
        assert ack["status"] == "running"
        assert time.time() - t0 < 5.0, "enrich must not block the request thread"
        # health answers while the model job runs
        code, health = srv.get("/api/health", timeout=5)
        assert code == 200 and health["ok"] is True
        st, job = _await_job(srv, run_id, "enrich")
        assert job["status"] == "done", job
        _code, data = srv.get("/api/query/bundle?run_id=" + run_id)
        bundle = data["bundle"]
        assert bundle["provenance"]["phase"] == "complete"
        assert bundle["answer"]["status"] == "ready"
        assert bundle["answer"]["cited_decision_ids"]
        # RF1: the server no longer publishes a bare `counts.counter`. That key
        # counted rows with any non-empty counter_status - including every decision
        # the answer cited - and labelled them "counter authorities". Both definitions
        # are published under honest names, and the broad key is gone so nothing can
        # keep reading it as a finding count.
        assert "counter" not in st["counts"], (
            "the mislabelled broad counter key must not return: it counted cited, "
            "supporting-candidate, context and unclassified rows as counter authorities"
        )
        assert st["counts"]["counter_status_bearing_rows"] >= 0
        assert st["counts"]["counter_authorities"] <= st["counts"]["counter_status_bearing_rows"]


def test_double_click_does_not_start_two_model_runs():
    import query_app

    with _Server() as srv:
        run_id = _start(srv)["run_id"]
        _st, _job = _await_job(srv, run_id, "expand")
        original = query_app._enrich_task
        calls = []
        slow_started = threading.Event()

        def slow(run_id_arg):
            calls.append(run_id_arg)
            slow_started.set()
            time.sleep(1.5)
            original(run_id_arg)

        query_app._enrich_task = slow
        try:
            code1, ack1 = srv.get("/api/query/enrich?run_id=" + run_id)
            slow_started.wait(5)
            code2, ack2 = srv.get("/api/query/enrich?run_id=" + run_id)
            assert code1 == 202 and code2 == 202
            assert ack2.get("deduplicated") is True
            _st, job = _await_job(srv, run_id, "enrich")
            assert job["status"] == "done"
        finally:
            query_app._enrich_task = original
        assert len(calls) == 1, f"the second click started another run: {calls}"


def test_failed_job_reports_an_error_instead_of_killing_the_server():
    import query_app

    with _Server() as srv:
        run_id = _start(srv)["run_id"]
        _st, _job = _await_job(srv, run_id, "expand")
        original = query_app._enrich_task

        def boom(run_id_arg):
            raise RuntimeError("synthetic job failure")

        query_app._enrich_task = boom
        try:
            code, _ack = srv.get("/api/query/enrich?run_id=" + run_id)
            assert code == 202
            _st, job = _await_job(srv, run_id, "enrich")
            assert job["status"] == "error"
            assert "synthetic job failure" in job["error"]
        finally:
            query_app._enrich_task = original
        code, health = srv.get("/api/health", timeout=5)
        assert code == 200 and health["ok"] is True


def test_unknown_run_and_empty_query_are_explicit_errors():
    with _Server() as srv:
        code, payload = srv.get("/api/query/status?run_id=nope")
        assert code == 404 and "unknown" in payload["error"]
        code, payload = srv.get("/api/query/bundle?run_id=nope")
        assert code == 404
        code, payload = srv.get("/api/query/start?q=")
        assert code == 400 and "empty query" in payload["error"]


def test_blocking_wait_s_contract_still_exists_for_scripts_and_ci():
    with _Server() as srv:
        run_id = _start(srv)["run_id"]
        _st, _job = _await_job(srv, run_id, "expand")
        code, payload = srv.get("/api/query/enrich?run_id=" + run_id + "&wait_s=120")
        assert code == 200
        assert payload["bundle"]["provenance"]["phase"] == "complete"
        assert payload["bundle"]["answer"]["status"] == "ready"


def test_enrich_started_during_expansion_answers_over_the_expanded_set():
    """Regression: enrich must not answer from the partial first-page set.

    Observed in run 38665681083: an enrich job that overlapped the background
    expansion finished first and the expansion then replaced the bundle, so the
    session ended with a map but no answer.
    """
    import query_app

    original_expand = query_app._expand_task

    with _Server() as srv:
        run_id = _start(srv)["run_id"]
        code, _ack = srv.get("/api/query/enrich?run_id=" + run_id)  # overlaps expansion
        assert code == 202
        st, exp = _await_job(srv, run_id, "expand")
        assert exp["status"] == "done", exp
        st, job = _await_job(srv, run_id, "enrich")
        assert job["status"] == "done", job
        _code, data = srv.get("/api/query/bundle?run_id=" + run_id)
        bundle = data["bundle"]
        assert bundle["answer"]["status"] == "ready"
        assert bundle["provenance"]["phase"] == "complete"
        assert len(bundle["decisions"]) >= st["counts"]["decisions"]


def test_expansion_after_the_answer_keeps_the_answer_and_its_citations():
    from query import enrich_query_bundle

    enriched = enrich_query_bundle(_first(), retrieval_mode="fixture", fixture_generation=True)
    again = expand_query_bundle(enriched, retrieval_mode="fixture")
    assert again["answer"]["status"] == "ready"
    assert again["answer"]["cited_decision_ids"] == enriched["answer"]["cited_decision_ids"]
    assert again["provenance"]["phase"] == "complete"
    assert again["provenance"]["progressive"]["expanded_after_answer"] is True


def test_reload_resume_returns_the_same_run_without_new_retrieval():
    with _Server() as srv:
        run_id = _start(srv)["run_id"]
        _st, _job = _await_job(srv, run_id, "expand")
        _code, first = srv.get("/api/query/bundle?run_id=" + run_id)
        _code, second = srv.get("/api/query/bundle?run_id=" + run_id)
        assert first["bundle"] == second["bundle"]
        assert first["status"]["jobs"]["expand"]["status"] == "done"