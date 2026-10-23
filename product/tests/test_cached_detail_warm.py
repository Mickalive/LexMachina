"""Tests for the cached detail warm pass (direction v63 item 7(a)).

No sockets: every test injects a client, and the replay-budget regression test
monkeypatches ``replay_fixtures`` so it never touches the real adapter cache.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from product.cached_detail_warm import (  # noqa: E402
    detail_cache_index,
    select_warm_targets,
    warm_leg,
    warm_targets,
)


def _write_envelope(root: Path, name: str, path: str, body: dict) -> None:
    target = root / name[:2] / f"{name}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({
        "key": name,
        "path": path,
        "params": {},
        "status": 200,
        "body": json.dumps(body, ensure_ascii=False),
        "fetched_at": 1,
    }), encoding="utf-8")


def test_detail_cache_index_only_counts_decision_bodies(tmp_path):
    _write_envelope(tmp_path, "a" * 64, "/decisions/dec_a", {
        "decision_id": "dec_a", "full_text": "some text"})
    _write_envelope(tmp_path, "b" * 64, "/decisions/dec_b", {
        "decision_id": "dec_b", "full_text": ""})
    _write_envelope(tmp_path, "c" * 64, "/search", {
        "results": [{"decision_id": "not_a_detail"}]})
    (tmp_path / "dd").mkdir()
    (tmp_path / "dd" / ("d" * 64 + ".json")).write_text("{not json", encoding="utf-8")

    index = detail_cache_index(tmp_path)
    assert set(index) == {"dec_a", "dec_b"}
    assert index["dec_a"]["full_text_chars"] > 0
    assert index["dec_b"]["full_text_chars"] == 0


def test_select_warm_targets_is_marker_first_then_rank_and_bounded():
    rows = [
        {"decision_id": "plain-1", "rank": 1, "snippet": "ordinary text"},
        {"decision_id": "marker-1", "rank": 2, "snippet": "die Vorinstanz ist anderer Auffassung"},
        {"decision_id": "has-text", "rank": 3, "full_text": "already here",
         "snippet": "nicht zu teilen"},
        {"decision_id": "cached", "rank": 4, "snippet": "sauf exception"},
        {"decision_id": "marker-2", "rank": 5, "snippet": "cependant, la cour"},
        {"decision_id": "plain-2", "rank": 6, "snippet": "another row"},
    ]
    targets = select_warm_targets(rows, existing_ids={"cached"}, limit=3)
    # marker-bearing rows first, by rank; full-text and cached rows excluded
    assert targets == ["marker-1", "marker-2", "plain-1"]


def test_select_warm_targets_zero_limit_and_empty_rows():
    assert select_warm_targets([{"decision_id": "a", "snippet": "x"}],
                               existing_ids=set(), limit=0) == []
    assert select_warm_targets([], existing_ids=set(), limit=5) == []


class _FakeClient:
    def __init__(self, bodies, fail=()):
        self.bodies = bodies
        self.fail = set(fail)
        self.calls = []

    def get_decision(self, decision_id, *, full_text=True):
        self.calls.append((decision_id, full_text))
        if decision_id in self.fail:
            raise RuntimeError("injected outage")
        return {"decision_id": decision_id,
                "full_text": self.bodies.get(decision_id, "")}


def test_warm_targets_counts_fetched_empty_and_failed_without_raising():
    client = _FakeClient({"a": "text"}, fail={"c"})
    counters = warm_targets(["a", "b", "c"], client=client)
    assert client.calls == [("a", True), ("b", True), ("c", True)]
    assert counters["requested"] == 3
    assert counters["fetched"] == 1
    assert counters["empty"] == 1
    assert counters["failed"] == 1


def test_warm_leg_appends_only_missing_bodies_and_reports_targets(tmp_path, monkeypatch):
    _write_envelope(tmp_path, "e" * 64, "/decisions/already", {
        "decision_id": "already", "full_text": "cached body"})
    rows = [
        {"decision_id": "already", "rank": 1, "snippet": "sauf"},
        {"decision_id": "new-marker", "rank": 2, "snippet": "nicht zu teilen"},
        {"decision_id": "new-plain", "rank": 3, "snippet": "plain"},
    ]

    import product.query.pipeline as pipeline

    monkeypatch.setattr(pipeline, "run_query_initial",
                        lambda q, top_n=150, retrieval_mode="fixture": {
                            "decisions": rows})

    written = []

    def fake_factory(cache_dir):
        client = _FakeClient({"new-marker": "m" * 10, "new-plain": ""})

        original = client.get_decision

        def get_decision(decision_id, *, full_text=True):
            body = original(decision_id, full_text=full_text)
            if body["full_text"]:
                _write_envelope(cache_dir, decision_id.replace("-", "x") * 4,
                                f"/decisions/{decision_id}", body)
                written.append(decision_id)
            return body

        client.get_decision = get_decision  # type: ignore[assignment]
        return client

    record = warm_leg("leg", "q", top_n=10, limit=5, cache_dir=tmp_path,
                      client_factory=fake_factory)

    assert record["targets"] == ["new-marker", "new-plain"]
    assert record["n_selected_marker_bearing"] == 1
    assert record["counters"]["fetched"] == 1
    assert record["counters"]["empty"] == 1
    assert record["append_only_ok"] is True
    assert written == ["new-marker"]  # an empty body is never cached as evidence
    # the pre-existing envelope was not rewritten
    assert "already" not in written


def test_replay_fixture_query_raises_hydration_budget_only_for_product_cache(monkeypatch):
    import product.query.pipeline as pipeline

    seen = []

    def fake_replay(query, *, config, hydrate_top):
        seen.append((config.max_requests, config.cache_dir))
        if len(seen) == 1:
            return {"candidates": []}  # legacy scenario missed
        return {"candidates": [{"decision_id": "x"}]}

    monkeypatch.setattr(pipeline, "replay_fixtures", fake_replay)
    out = pipeline.replay_fixture_query("q", top_n=100, hydrate_top=100)

    assert out["candidates"]
    assert len(seen) == 2
    legacy_budget, legacy_cache = seen[0]
    product_budget, product_cache = seen[1]
    # legacy replay is untouched; the product-cache replay must be able to
    # hydrate the ids the caller asked for instead of starving at 40 total.
    assert legacy_budget == 30
    assert product_budget >= 100 * 2 + 16
    assert legacy_cache != product_cache


def test_replay_fixture_query_hydrate_top_zero_keeps_budget(monkeypatch):
    import product.query.pipeline as pipeline

    seen = []

    def fake_replay(query, *, config, hydrate_top):
        seen.append(config.max_requests)
        if len(seen) == 1:
            return {"candidates": []}
        return {"candidates": [{"decision_id": "x"}]}

    monkeypatch.setattr(pipeline, "replay_fixtures", fake_replay)
    pipeline.replay_fixture_query("q", top_n=100, hydrate_top=0)
    assert seen[1] == 40


def test_warm_leg_dry_run_makes_no_client(tmp_path, monkeypatch):
    import product.query.pipeline as pipeline

    monkeypatch.setattr(pipeline, "run_query_initial",
                        lambda q, top_n=150, retrieval_mode="fixture": {
                            "decisions": [{"decision_id": "a", "snippet": "sauf"}]})
    called = []
    record = warm_leg("leg", "q", top_n=10, limit=5, cache_dir=tmp_path,
                      dry_run=True,
                      client_factory=lambda _c: called.append(True))
    assert called == []
    assert record["targets"] == ["a"]
    assert record["counters"]["requested"] == 0
