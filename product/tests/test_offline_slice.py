"""One-command offline clickable slice (product cycle 39011220761 -> resume 39014141628).

`python product/offline_slice.py` is the developer entry point for the FAST-MVP
vertical slice: frozen question -> query_result_bundle -> source-linked clickable
map, with no network and no owner time. These tests pin that contract and prove
the PASS verdict is not vacuous.
"""
from __future__ import annotations

import json
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "product"
for _p in (str(PRODUCT), str(ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import offline_slice as ofs  # noqa: E402


def _no_network(*_a, **_k):  # pragma: no cover
    raise AssertionError("offline slice attempted network access")


def test_one_command_slice_is_offline_clickable_and_verified(monkeypatch, tmp_path, capsys):
    """The whole slice runs with `socket.connect` booby-trapped: any network
    attempt raises, so rc==0 proves the path is cache-only."""
    monkeypatch.setattr(socket.socket, "connect", _no_network)
    rc = ofs.main(["--slug", "rent-default", "--out", str(tmp_path), "--verify"])
    out = capsys.readouterr().out
    assert rc == 0, out
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    stats = summary["stats"]
    assert summary["verified"] is True
    assert stats["n_decisions"] >= 40
    assert stats["rows_with_xy"] == stats["n_decisions"], "every row needs map coordinates"
    assert stats["rows_with_cluster_id"] == stats["n_decisions"], "every row needs a cluster_id"
    assert stats["rows_with_source_url"] == stats["n_decisions"], "every row needs a source link"
    assert stats["n_clusters"] >= 2, "a map with one cluster is a list"
    assert "OFFLINE WIRING EVIDENCE ONLY" in summary["claim_ceiling"]
    bundle = json.loads((tmp_path / "rent-default.bundle.json").read_text(encoding="utf-8"))
    assert bundle["provenance"]["product_fixture_replay"]["network"] == "none"
    # the page contract actually executed (node present in this environment)
    assert summary["page_contract"] is True
    # Full loop, still offline: sourced answer + counter pass, geometry untouched.
    assert stats["enriched"] is True, "the one-command slice runs the answer/counter pass"
    assert stats["answer_status"] == "ready"
    assert stats["cited_decision_ids"] >= 1, "a sourced answer must cite a retrieved decision"
    assert stats["geometry_preserved_by_enrich"] is True, \
        "enrichment must not move or drop a rendered point"
    # Non-vacuity on the DOM side: the page contract must really have executed
    # the answer-panel section (45 assertions as of this cycle; the pre-answer
    # floor was 36), not just booted the page.
    detail = summary.get("page_contract_detail") or ""
    assert detail.startswith("PASS"), detail
    assert int(detail.split()[-2]) >= 40, detail


def test_map_only_mode_makes_no_answer_claim(monkeypatch, tmp_path, capsys):
    """`--no-enrich` is a map-only slice: it must NOT be recorded as if the
    answer half of the product had run."""
    monkeypatch.setattr(socket.socket, "connect", _no_network)
    rc = ofs.main(["--slug", "rent-default", "--out", str(tmp_path), "--no-enrich", "--verify"])
    assert rc == 0, capsys.readouterr().out
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    stats = summary["stats"]
    assert stats["enriched"] is False
    assert stats["answer_status"] == "pending"
    assert stats["cited_decision_ids"] == 0
    assert stats["geometry_preserved_by_enrich"] is None


def test_verdict_fails_when_enrichment_moves_a_rendered_point(monkeypatch, tmp_path, capsys):
    """Non-vacuity: the geometry-preservation claim is checked, not assumed."""
    def _moved(*_a, **_k):
        rows = [{"decision_id": f"bge_{n}", "x": float(n), "y": float(n),
                 "cluster_id": n % 3, "counter_status": "none",
                 "canonical_url": "https://mcp.opencaselaw.ch/d/x"}
                for n in range(45)]
        return {
            "decisions": rows,
            "answer": {"status": "ready", "cited_decision_ids": ["bge_0"],
                       "prose": "x", "method": "synthetic", "model": "none"},
            "provenance": {"offline_slice": {"enriched": True,
                                             "geometry_preserved": False,
                                             "network": "none"}},
        }
    monkeypatch.setattr(ofs, "build_bundle", _moved)
    rc = ofs.main(["--slug", "rent-default", "--out", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 1, out
    assert "enrichment moved or dropped a rendered point" in out
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["verified"] is False


def test_verdict_fails_when_the_map_is_degenerate(monkeypatch, tmp_path, capsys):
    """Non-vacuity: a too-small bundle must FAIL the verdict, not pass it."""
    def _tiny(*_a, **_k):
        return {"decisions": [{"decision_id": "bge_1", "x": 0.0, "y": 0.0,
                               "cluster_id": 0, "counter_status": "none"}],
                "answer": {"status": "pending"}, "provenance": {}}
    monkeypatch.setattr(ofs, "build_bundle", _tiny)
    rc = ofs.main(["--slug", "rent-default", "--out", str(tmp_path), "--quiet"])
    assert rc == 1
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["verified"] is False


def test_verdict_fails_when_a_row_has_no_cluster_id(monkeypatch, tmp_path, capsys):
    """Non-vacuity (audit D3): rows with x/y but cluster_id=None must FAIL the
    verdict — the tool claims 'cluster_id on every row', so it checks it.
    A single None-keyed bucket must not satisfy the n_clusters >= 2 check."""
    def _unclustered(*_a, **_k):
        return {"decisions": [
                    {"decision_id": f"bge_{n}", "x": float(n), "y": float(n),
                     "cluster_id": None, "counter_status": "none",
                     "canonical_url": "https://mcp.opencaselaw.ch/d/x"}
                    for n in range(45)],
                "answer": {"status": "pending"}, "provenance": {}}
    monkeypatch.setattr(ofs, "build_bundle", _unclustered)
    rc = ofs.main(["--slug", "rent-default", "--out", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 1, out
    assert "rows missing cluster_id" in out
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["stats"]["rows_with_cluster_id"] == 0
    assert summary["stats"]["n_clusters"] == 0  # None keys are not clusters


def test_unknown_slug_is_refused(tmp_path):
    try:
        ofs.main(["--slug", "no-such-leg", "--out", str(tmp_path), "--quiet"])
    except SystemExit as exc:                       # argparse-style refusal
        assert "unknown slug" in str(exc)
        return
    raise AssertionError("unknown slug must be refused")


def test_no_network_attempt_leaves_the_real_socket_intact(monkeypatch):
    """The offline trap must be restored after the call (no leak into later code)."""
    monkeypatch.setattr(socket.socket, "connect", _no_network)
    real = socket.socket.connect
    bundle = ofs.build_bundle("business-judgment-rule", top_n=100)
    assert bundle["decisions"], "fixture replay returned nothing"
    assert socket.socket.connect is real, "build_bundle leaked its own network trap"
