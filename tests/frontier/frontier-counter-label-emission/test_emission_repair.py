"""Emission-repair tests (acceptance tests 3, 5)."""

from __future__ import annotations

import copy

from conftest import PACKET, requires_accepted
from frontier_counter_label_emission import (
    REPAIR_ID,
    SCORED_STATUSES,
    promote_heuristic_proposals,
)
import json


def _row(did, status="none", heur=None, ev="", ft="text", **kw):
    d = {
        "decision_id": did,
        "counter_status": status,
        "counter_evidence": "",
        "full_text": ft,
        "x": 1.0, "y": 2.0, "cluster_id": 0, "is_outlier": False, "rank": 1,
    }
    if heur is not None:
        d["adversarial_retrieval_signal"] = {
            "heuristic_status": heur, "evidence": ev, "markers": [],
        }
    d.update(kw)
    return d


def test_promotes_rows_with_heuristic_signal():
    b = {"query": "q", "decisions": [
        _row("a", heur="candidate-limiting", ev="X" * 60),
    ], "provenance": {}}
    out = promote_heuristic_proposals(b, scored_statuses=SCORED_STATUSES)
    row = out["decisions"][0]
    assert row["counter_status"] == "candidate-limiting"
    assert len(row["counter_evidence"]) >= 40
    assert row["counter_proposal_source"] == REPAIR_ID
    assert out["provenance"]["counter_label_emission_repair"]["n_promoted"] == 1


def test_never_overwrites_existing_scored_status():
    b = {"query": "q", "decisions": [
        _row("a", status="candidate-contrary", heur="candidate-limiting", ev="Y" * 60),
    ], "provenance": {}}
    out = promote_heuristic_proposals(b, scored_statuses=SCORED_STATUSES)
    assert out["decisions"][0]["counter_status"] == "candidate-contrary"
    assert out["provenance"]["counter_label_emission_repair"]["n_promoted"] == 0


def test_never_touches_geometry():
    b = {"query": "q", "decisions": [
        _row("a", heur="candidate-limiting", ev="Z" * 60, x=9.5, y=-3.2, cluster_id=7, is_outlier=True),
    ], "provenance": {}}
    out = promote_heuristic_proposals(b, scored_statuses=SCORED_STATUSES)
    row = out["decisions"][0]
    assert row["x"] == 9.5 and row["y"] == -3.2
    assert row["cluster_id"] == 7 and row["is_outlier"] is True


def test_skips_short_evidence():
    b = {"query": "q", "decisions": [
        _row("a", heur="candidate-limiting", ev="short"),
    ], "provenance": {}}
    out = promote_heuristic_proposals(b, scored_statuses=SCORED_STATUSES)
    assert out["decisions"][0]["counter_status"] == "none"
    assert out["provenance"]["counter_label_emission_repair"]["n_promoted"] == 0


def test_pure_no_side_effect_on_input():
    b = {"query": "q", "decisions": [_row("a", heur="candidate-limiting", ev="W" * 60)], "provenance": {}}
    snapshot = copy.deepcopy(b)
    promote_heuristic_proposals(b, scored_statuses=SCORED_STATUSES)
    assert b == snapshot


@requires_accepted
def test_real_packet_repair_promotes_n_scored_gt_zero():
    for qid in ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica"):
        bundle = json.loads(
            (PACKET / "questions" / f"{qid}.bundle.json").read_text(encoding="utf-8")
        )
        out = promote_heuristic_proposals(bundle, scored_statuses=SCORED_STATUSES)
        n_scored = sum(
            1 for d in out["decisions"]
            if str(d.get("counter_status") or "") in SCORED_STATUSES
        )
        assert n_scored > 0, f"{qid}: repair produced no scored proposals"
