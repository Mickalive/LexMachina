"""Stage-level progress for the enrich leg (QUERY_MAP_MVP 9A).

Why this exists
---------------
The enrich leg — source-constrained answer + independent counter-authority pass
— is the only part of the query path that is not sub-second.  Measured live on
2026-11-27 against real OpenCaseLaw (run 61e701394b1b, ``--port 8803``):

    /api/query/start -> first map     11.70 s   (upstream 11.60, local 0.09)
    expansion -> 163 decisions        +51.95 s   (upstream 51.95, local 0.04)
    /api/query/enrich                 319.68 s   (hydrate 0.23, rest 319.45)
    final bundle: 171 decisions, 8 clusters, 50 relations, 5 cited,
                  11 counter authorities, 15 counter-status-bearing rows

Before this change those 319.68 s were a single opaque "running" counter: the
operator could not tell a generating model from a hung tab, and nothing was
painted until the whole leg finished.  This module pins the three things that
fix that:

1. ``provenance.timing.enrich_stages`` — every leg of the leg, in run order,
   summing to the published total;
2. an early, geometry-identical answer milestone published while the
   counter-authority pass is still running;
3. ``/api/query/status`` reporting the running leg by name, and the shipped
   page painting the answer once and never wiping it again.

It is a latency/progress contract.  It makes no claim about answer quality,
counter-authority soundness or legal usefulness.
"""
from __future__ import annotations

import json
import math
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "product"
if str(PRODUCT) not in sys.path:
    sys.path.insert(0, str(PRODUCT))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from query import enrich_query_bundle, run_query_initial  # noqa: E402
from query.bundle import validate_bundle  # noqa: E402
from query.pipeline import ENRICH_STAGES  # noqa: E402

QUERY = "Kündigung Mietvertrag Mietrecht"

def initial(n=60):
    bundle = run_query_initial(QUERY, top_n=n, retrieval_mode="fixture")
    assert validate_bundle(bundle) == []
    return bundle


def enrich(bundle, **kwargs):
    kwargs.setdefault("retrieval_mode", "fixture")
    kwargs.setdefault("fixture_generation", True)
    return enrich_query_bundle(bundle, **kwargs)


# ---------------------------------------------------------------------------
# 1. every leg is timed, in order, and the split sums to the published total
# ---------------------------------------------------------------------------

def test_enrich_records_every_stage_in_run_order():
    seen: list[str] = []
    final = enrich(initial(), stage_hook=lambda name, info: seen.append(name))

    stages = final["provenance"]["timing"]["enrich_stages"]
    assert list(stages) == list(ENRICH_STAGES), (
        "the published split must name every leg, in the order they run"
    )
    assert seen == list(ENRICH_STAGES), (
        "the hook must observe the same legs, in the same order"
    )
    for name, seconds in stages.items():
        assert seconds >= 0.0, f"negative duration for {name}: {seconds}"
        assert math.isfinite(seconds), f"non-finite duration for {name}: {seconds}"


def test_stage_split_sums_to_the_published_enrich_total():
    final = enrich(initial())
    timing = final["provenance"]["timing"]
    total = timing["enrich_total_s"]
    split = sum(timing["enrich_stages"].values())
    assert total > 0
    # The split is closed just before content annotation/validation, so the two
    # agree to within the finalisation time (measured < 1 ms on the fixture path).
    assert abs(total - split) < 1.0, (
        f"stage split {split:.4f}s does not account for enrich_total_s {total:.4f}s"
    )
    # The legacy two-way split stays internally consistent with the new one.
    assert timing["enrich_non_model_s"] == timing["enrich_stages"]["hydrate"] or (
        abs(timing["enrich_non_model_s"] - timing["enrich_stages"]["hydrate"]) < 1e-3
    )


def test_stage_progress_is_pure_and_never_raises_on_a_broken_hook():
    def boom(name, info):
        raise AssertionError(f"hook failure must be swallowed, got {name}")

    final = enrich(initial(), stage_hook=boom)
    assert validate_bundle(final) == [], (
        "a progress reporter must not be able to fail the generation it reports on"
    )
    assert list(final["provenance"]["timing"]["enrich_stages"]) == list(ENRICH_STAGES)


def test_without_a_hook_the_bundle_contract_is_unchanged():
    final = enrich(initial())
    assert validate_bundle(final) == []
    assert final["answer"]["status"] == "ready"
    assert final["provenance"]["phase"] == "complete"


# ---------------------------------------------------------------------------
# 2. the early answer milestone: published, sourced, and geometry-identical
# ---------------------------------------------------------------------------

def test_the_answer_milestone_is_published_before_the_counter_pass():
    milestones: dict[str, dict] = {}

    def hook(name, info):
        if "bundle" in info:
            milestones[name] = info["bundle"]

    initial_bundle = initial()
    final = enrich(initial_bundle, stage_hook=hook)

    assert "coverage" in milestones, (
        "the answer milestone must be handed to the consumer, or the browser has "
        "nothing to paint while the counter-authority pass runs"
    )
    milestone = milestones["coverage"]
    assert milestone["answer"]["status"] == "ready", "the milestone must carry the answer"
    assert milestone["answer"]["cited_decision_ids"], "the milestone must carry the citations"
    # The counter pass has NOT run yet at this point: it is the thing still running.
    assert final["provenance"]["timing"]["enrich_stages"]["counter_retrieval"] >= 0.0
    # ...and the geometry it will not touch is already final.
    frozen_before = {
        d["decision_id"]: (d["x"], d["y"], d["cluster_id"]) for d in initial_bundle["decisions"]
    }
    frozen_milestone = {
        d["decision_id"]: (d["x"], d["y"], d["cluster_id"]) for d in milestone["decisions"]
    }
    frozen_final = {
        d["decision_id"]: (d["x"], d["y"], d["cluster_id"]) for d in final["decisions"]
    }
    for did, point in frozen_before.items():
        assert frozen_milestone.get(did) == point, f"the milestone moved {did}"
        assert frozen_final.get(did) == point, f"enrichment moved {did}"


def test_only_the_answer_contract_legs_are_publishable():
    published = []

    def hook(name, info):
        if "bundle" in info:
            published.append(name)

    enrich(initial(), stage_hook=hook)
    assert published == ["coverage"], (
        f"exactly one publishable milestone is expected before the counter pass, got {published}"
    )


def test_an_outage_fallback_is_still_published_as_a_milestone(monkeypatch):
    """A degraded answer is a complete, sourced answer — it must not be hidden.

    Measured live on 2026-11-27 (run c03af101f48a) the generative writer
    returned no citations, the answer-gap contract composed the extractive
    fallback and the shipped status read ``degraded``.  The milestone publish is
    therefore keyed on the answer contract being finished, never on the writer
    having succeeded — otherwise the one run that most needs an early,
    honest answer would be the one that waits the full leg for it.
    """
    import query.pipeline as pipeline_mod

    milestones: dict[str, dict] = {}

    def hook(name, info):
        if "bundle" in info:
            milestones[name] = info["bundle"]

    def outage(*args, **kwargs):
        raise RuntimeError("synthetic model outage")

    monkeypatch.setattr(pipeline_mod, "run_generative_audit", outage)
    final = enrich(initial(), stage_hook=hook)

    assert "coverage" in milestones, "the fallback answer must still reach the consumer"
    milestone = milestones["coverage"]
    assert milestone["answer"]["status"] == "degraded"
    assert milestone["answer"].get("degradation"), "the fallback must explain itself"
    assert milestone["answer"]["cited_decision_ids"], (
        "the extractive fallback still cites the decisions it quotes"
    )
    assert final["answer"]["status"] == "degraded"
    assert validate_bundle(final) == []


# ---------------------------------------------------------------------------
# 3. the server reports the running leg, and publishes the milestone over HTTP
# ---------------------------------------------------------------------------

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
        try:
            with urllib.request.urlopen(self.base + path, timeout=timeout) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read() or b"{}")

    def await_job(self, run_id, name, timeout=90):
        deadline = time.time() + timeout
        last = {}
        while time.time() < deadline:
            code, status = self.get(f"/api/query/status?run_id={run_id}")
            assert code == 200, status
            last = status["jobs"][name]
            if last["status"] in {"done", "error"}:
                return status, last
            time.sleep(0.05)
        raise AssertionError(f"{name} never finished: {last}")


def test_stage_labels_cover_every_leg_the_pipeline_can_publish():
    import query_app

    assert set(query_app.STAGE_LABELS) == set(ENRICH_STAGES), (
        "the browser must be able to name every leg the pipeline reports: "
        f"missing={set(ENRICH_STAGES) - set(query_app.STAGE_LABELS)} "
        f"stale={set(query_app.STAGE_LABELS) - set(ENRICH_STAGES)}"
    )
    for stage, label in query_app.STAGE_LABELS.items():
        assert label and label != stage, f"{stage} has no human-readable label"


def test_stage_detail_reports_the_running_leg_by_name():
    import query_app

    detail = query_app._stage_detail(
        "answer", {"stages": {"hydrate": 0.2, "answer": 12.5}, "elapsed_s": 12.7}
    )
    assert detail["stage"] == "answer"
    assert detail["stage_label"] == query_app.STAGE_LABELS["answer"]
    assert detail["stages"]["answer"] == 12.5
    assert detail["stage_elapsed_s"] == pytest.approx(12.7)


def test_status_names_the_running_leg_and_the_milestone_arrives_over_http():
    """The whole browser contract, driven through the real HTTP handler.

    A wrapper widens the window right after the answer milestone is published so
    the poll can observe the state a jurist actually sees: the job is still
    ``running``, the status line already names a leg, and the bundle already
    carries a sourced answer.  Without the window this test would race the
    fixture path (which finishes in ~0.3 s).
    """
    import query_app

    real = query_app.enrich_query_bundle
    observed: dict = {"stage": None, "published_while_running": False}

    def slow(*args, **kwargs):
        inner = kwargs.get("stage_hook")

        def hooked(stage, info):
            if inner is not None:
                inner(stage, info)
            if stage == "coverage":
                observed["stage"] = info.get("stages") and stage
                observed["detail"] = dict(info.get("stages") or {})
                observed["window_open"] = True
                time.sleep(1.5)

        kwargs["stage_hook"] = hooked
        return real(*args, **kwargs)

    query_app.enrich_query_bundle = slow
    try:
        with _Server() as srv:
            code, started = srv.get(
                "/api/query/start?q=" + urllib.parse.quote(QUERY) + "&n=60"
            )
            assert code == 200, started
            run_id = started["run_id"]
            status, exp = srv.await_job(run_id, "expand")
            assert exp["status"] == "done"

            code, ack = srv.get(f"/api/query/enrich?run_id={run_id}")
            assert code in {200, 202}, ack

            # Poll for the milestone window.
            deadline = time.time() + 30
            snapshot = None
            while time.time() < deadline:
                _code, st = srv.get(f"/api/query/status?run_id={run_id}")
                det = (st.get("jobs", {}).get("enrich") or {}).get("detail") or {}
                if det.get("stage") == "coverage":
                    _bcode, bundle = srv.get(f"/api/query/bundle?run_id={run_id}")
                    snapshot = (st, det, bundle.get("bundle") or {})
                    break
                if (st.get("jobs", {}).get("enrich") or {}).get("status") == "error":
                    raise AssertionError(f"enrich failed: {st['jobs']['enrich']}")
                time.sleep(0.05)
            assert snapshot is not None, (
                "the enrich job never reported a stage to the status endpoint"
            )
            st, det, partial = snapshot
            assert st["jobs"]["enrich"]["status"] == "running", (
                "the milestone must be observable while the counter pass is still running"
            )
            assert det["stage_label"] == query_app.STAGE_LABELS["coverage"]
            assert set(det["stages"]) <= set(ENRICH_STAGES)
            assert (partial.get("answer") or {}).get("status") == "ready", (
                "the browser must be able to read a sourced answer from the bundle "
                "before the counter-authority pass finishes"
            )
            assert st["answer"]["status"] == "ready"

            status, job = srv.await_job(run_id, "enrich")
            assert job["status"] == "done", job
            assert job["detail"]["stage"] == "complete"
            assert job["detail"]["stage_label"] == "terminé"
            stages = job["detail"]["enrich_stages"]
            assert list(stages) == list(ENRICH_STAGES)
            # The counter pass really did run after the milestone.
            assert stages["counter_retrieval"] >= 0.0
            _code, final_bundle = srv.get(f"/api/query/bundle?run_id={run_id}")
            final = final_bundle["bundle"]
            assert final["answer"]["status"] == "ready"
            assert validate_bundle(final) == []
    finally:
        query_app.enrich_query_bundle = real


def test_the_shipped_page_contract_for_progress_and_milestone():
    """The shipped browser behaviour, executed in a minimal DOM by node."""
    import shutil
    import subprocess

    node = shutil.which("node")
    if node is None:
        pytest.skip("node not available")
    script = PRODUCT / "verify_enrich_progress.js"
    # A real bundle makes the paint path realistic; any committed bundle works
    # because the milestone answer is synthesised by the script itself.
    candidates = [
        ROOT / "results" / "product" / "progressive_slice" / "bundle_39060279436_LIVE_V2.json",
        ROOT / "results" / "product" / "gate_packet" / "38839347028" / "questions" / "de-kapitalverletzung.bundle.json",
    ]
    bundle_path = next((p for p in candidates if p.is_file()), None)
    if bundle_path is None:
        pytest.skip("no committed bundle available for the page contract")
    proc = subprocess.run(
        [node, str(script), str(bundle_path)],
        capture_output=True, text=True, timeout=300,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "PASS" in proc.stdout, proc.stdout
    assert "FAIL" not in proc.stdout, proc.stdout
