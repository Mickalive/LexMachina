"""Coverage remediation tests (direction v62 ordered item 2).

Evaluation run 39631600439 measured 4/24 frozen texts executed and all 18
comparator-only ids coming from never-executed texts.  These tests pin the
product-owned planning/merge/execution seam that closes that gap without
network access and without touching any frozen gate.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from product.query import pipeline
from product.query import query_texts as qt


def _question(i: int = 0) -> dict:
    return qt.load_manifest()["questions"][i]


def _cand(did: str, docket: str, *, channels=("search",)) -> dict:
    return {
        "decision_id": did,
        "canonical_decision_id": did,
        "court": "bger",
        "docket_number": docket,
        "language": "de",
        "rank": 1,
        "score": 0.5,
        "snippet": "Mietvertrag Kündigung",
        "channels": list(channels),
        "canonical_url": f"https://mcp.opencaselaw.org/decisions/{did}",
        "citation": docket,
    }


# --------------------------------------------------------------------------
# 1. planning
# --------------------------------------------------------------------------

def test_manifest_pins_the_accepted_frozen_benchmark_bytes():
    data = qt.load_manifest()
    assert data["source_sha256"] == (
        "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72"
    )
    assert len(data["questions"]) == 4


def test_every_frozen_question_plans_exactly_its_six_texts():
    for question in qt.load_manifest()["questions"]:
        plan = qt.frozen_text_plan(question["queries"]["baseline"]["fr"])
        assert len(plan) == 6
        assert {(p["channel"], p["language"]) for p in plan} == {
            (c, l) for c in ("baseline", "counter") for l in ("fr", "de", "it")
        }
        assert {p["slug"] for p in plan} == {question["slug"]}


def test_identity_match_works_from_any_of_the_six_texts():
    question = _question(0)
    for channel in ("baseline", "counter"):
        for lang in ("fr", "de", "it"):
            plan = qt.frozen_text_plan(question["queries"][channel][lang])
            assert len(plan) == 6


def test_unknown_query_gets_three_counter_texts_not_fabricated_translations():
    plan = qt.counter_intent_plan("Art. 337 CO licenciement immédiat vol de faible valeur")
    assert len(plan) == 3
    assert {p["language"] for p in plan} == {"fr", "de", "it"}
    assert all(p["source"] == "product_counter_intent_planner" for p in plan)
    assert all("Art. 337 CO" in p["text"] for p in plan)
    # each language carries its own limitation vocabulary
    assert "Ausnahme" in plan[1]["text"]
    assert "eccezione" in plan[2]["text"]


def test_topic_free_query_plans_nothing_rather_than_a_noise_probe():
    assert qt.counter_intent_plan("???") == []


def test_missing_plan_filters_the_primary_text_unless_explicitly_retried():
    question = _question(0)
    primary = question["queries"]["baseline"]["fr"]
    assert len(qt.plan_missing_texts(primary)) == 5
    assert len(qt.plan_missing_texts(primary, include_primary=True)) == 6


# --------------------------------------------------------------------------
# 2. merge (pure)
# --------------------------------------------------------------------------

def test_merge_adds_new_rows_and_never_duplicates_identity():
    base = [_cand("a", "1A_1/2020")]
    extra = [
        _cand("a", "1A_1/2020", channels=("search", "adversarial.contrary")),
        _cand("b", "1A_2/2020"),
        _cand("b_alias", "1A_2/2020"),  # same court+docket, different upstream id
    ]
    merged, stats = qt.merge_coverage_candidates(base, extra)
    assert len(merged) == 2
    assert stats["n_added"] == 1
    assert "adversarial.contrary" in merged[0]["channels"]
    assert stats["added_decision_ids"] == ["b"]


# --------------------------------------------------------------------------
# 3. pipeline execution seam
# --------------------------------------------------------------------------

def _fake_builder(row_for):
    calls: list[str] = []

    def _build(query, config=None, hydrate_top=0, hydrate_ids=None,
               include_structure=True):
        calls.append(query)
        rows = row_for(query, len(calls))
        return {
            "bundle_version": "1.0-candidate",
            "query": query,
            "query_variants": [{"text": query}],
            "candidates": rows,
            "n_candidates": len(rows),
            "provenance": {
                "query_variants": [{"text": query}],
                "request_summary": {"network_calls": 0, "cache_hits": 1},
                "degraded": False,
                "failures": [],
            },
        }
    return _build, calls


def test_pipeline_executes_the_remaining_frozen_texts_additively(monkeypatch):
    question = _question(0)
    primary = question["queries"]["baseline"]["fr"]
    rows_by_text = {
        question["queries"]["baseline"]["de"]: [_cand("de_1", "1A_10/2020")],
        question["queries"]["counter"]["de"]: [_cand("de_2", "1A_11/2020")],
        question["queries"]["counter"]["it"]: [_cand("it_1", "1A_12/2020")],
        question["queries"]["counter"]["fr"]: [_cand("fr_1", "1A_13/2020")],
    }

    def row_for(query, _call):
        if query == primary:
            return [_cand("base_1", "1A_9/2020")]
        return rows_by_text.get(query, [])

    build, calls = _fake_builder(row_for)
    monkeypatch.setattr(pipeline, "build_candidate_bundle", build)
    out = pipeline._retrieve(primary, 120, mode="offline")

    assert len(calls) == 6, "primary + the five missing frozen texts"
    ids = {c["decision_id"] for c in out["candidates"]}
    assert {"base_1", "de_1", "de_2", "it_1", "fr_1"} <= ids
    cov = out["provenance"]["coverage_expansion"]
    assert cov["n_planned"] == 6
    assert cov["n_to_execute"] == 5
    assert cov["n_added"] == 4
    assert {p["language"] for p in cov["per_text"]} == {"de", "fr", "it"}


def test_a_failing_coverage_text_never_costs_the_primary_bundle(monkeypatch):
    question = _question(0)
    primary = question["queries"]["baseline"]["fr"]

    def row_for(query, _call):
        if query == primary:
            return [_cand("base_1", "1A_9/2020")]
        raise RuntimeError("upstream unavailable")

    build, _ = _fake_builder(row_for)
    monkeypatch.setattr(pipeline, "build_candidate_bundle", build)
    out = pipeline._retrieve(primary, 120, mode="offline")
    assert [c["decision_id"] for c in out["candidates"]] == ["base_1"]
    cov = out["provenance"]["coverage_expansion"]
    assert cov["n_added"] == 0
    assert any("upstream unavailable" in (r.get("error") or "") for r in cov["per_text"])


def test_offline_primary_miss_retries_the_same_text_from_coverage(monkeypatch):
    question = _question(0)
    primary = question["queries"]["baseline"]["fr"]
    state = {"primary_calls": 0}

    def row_for(query, _call):
        if query == primary:
            state["primary_calls"] += 1
            # the primary request key misses; the coverage config hits
            return [] if state["primary_calls"] == 1 else [_cand("base_1", "1A_9/2020")]
        return []

    build, calls = _fake_builder(row_for)
    monkeypatch.setattr(pipeline, "build_candidate_bundle", build)
    out = pipeline._retrieve(primary, 120, mode="offline")
    assert [c["decision_id"] for c in out["candidates"]] == ["base_1"]
    assert state["primary_calls"] == 2
    assert len(calls) == 7  # failed primary + six coverage texts
    assert out["provenance"]["coverage_expansion"]["n_to_execute"] == 6


def test_generic_query_only_adds_counter_intent_texts(monkeypatch):
    query = "Art. 337 CO licenciement immédiat"
    build, calls = _fake_builder(lambda q, n: [_cand("base", "1A_1/2020")])
    monkeypatch.setattr(pipeline, "build_candidate_bundle", build)
    out = pipeline._retrieve(query, 120, mode="offline")
    cov = out["provenance"]["coverage_expansion"]
    assert cov["n_planned"] == 3
    assert cov["n_to_execute"] == 3
    assert len(calls) == 4
    assert all(p["channel"] == "counter" for p in cov["planned_texts"])
