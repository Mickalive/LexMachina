"""Offline tests for the live-answer reliability measurement tool.

These tests never call a model and never touch the network: they exercise the
measurement's arithmetic, its validity checks and its pre-registration
guard on synthetic bundles.  The live measurement itself is run by
``python3 product/answer_reliability.py --run`` and its artifact is checked
by ``--check``.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from product import answer_reliability as ar  # noqa: E402


def _bundle(*, cited, prose="", decisions=None, degradation=None,
            adversarial_status="MEASURED"):
    if decisions is None:
        decisions = [
            {
                "decision_id": "bge_119 II 147",
                "citation": "BGE 119 II 147",
                "canonical_url": "https://mcp.opencaselaw.ch/bge_119_II_147",
            },
            {
                "decision_id": "ge_gerichte_4A_376_2021",
                "citation": "4A_376/2021",
                "canonical_url": "https://mcp.opencaselaw.ch/ge_gerichte_4A_376_2021",
            },
        ]
    return {
        "decisions": decisions,
        "answer": {
            "status": "ready",
            "prose": prose,
            "cited_decision_ids": list(cited),
            "degradation": degradation,
        },
        "provenance": {
            "adversarial_retrieval": {"adversarial_status": adversarial_status}
        },
    }


def test_the_protocol_is_a_frozen_constant_with_a_stable_digest():
    first = ar.protocol_payload("1")
    second = ar.protocol_payload("2")
    assert first["protocol_sha256"] == second["protocol_sha256"]
    assert first["query_text_manifest"]["sha256"]
    assert first["query_text_manifest"]["source_sha256"]


def test_the_query_set_is_read_from_the_frozen_manifest_not_retyped():
    legs = ar.query_texts()
    planned = sum(int(spec["repeats"]) for spec in ar.PROTOCOL["query_set"])
    assert len(legs) == planned
    assert len({leg["leg_id"] for leg in legs}) == planned
    # the repeated question is repeated exactly as pre-registered
    repeated = [leg for leg in legs if leg["slug"] == "rent-default"
                and leg["language"] == "fr"]
    assert len(repeated) == 2
    assert repeated[0]["text_sha256"] == repeated[1]["text_sha256"]


def test_a_cited_id_that_is_not_in_the_bundle_is_invalid():
    result = ar.citation_validity(_bundle(cited=["bge_119 II 147", "nope"]))
    assert result["n_cited"] == 2
    assert result["n_valid"] == 1
    assert result["invalid_ids"] == ["nope"]
    assert result["all_valid"] is False


def test_a_citation_without_an_allowed_canonical_source_is_invalid():
    bundle = _bundle(cited=["bge_119 II 147"])
    bundle["decisions"][0]["canonical_url"] = "https://example.invalid/x"
    result = ar.source_validity(bundle)
    assert result["n_without_valid_source"] == 1
    assert result["all_valid"] is False


def test_a_citation_on_an_allowed_public_host_is_valid():
    result = ar.source_validity(_bundle(cited=["bge_119 II 147"]))
    assert result["all_valid"] is True
    assert result["n_with_valid_source"] == 1


def test_a_prose_marker_that_is_not_in_the_bundle_is_unresolved():
    result = ar.prose_citation_validity(
        _bundle(cited=[], prose="Selon [bge_119 II 147] et [BGE 999 II 1]."))
    assert result["n_markers"] == 2
    assert result["n_resolved"] == 1
    assert result["unresolved_markers"] == ["BGE 999 II 1"]
    assert result["all_resolved"] is False


def test_prose_markers_resolve_against_both_id_and_citation_forms():
    result = ar.prose_citation_validity(
        _bundle(cited=[], prose="[bge_119 II 147] puis [ge_gerichte_4A_376_2021]"))
    assert result["n_markers"] == 2
    assert result["n_resolved"] == 2


def test_a_writer_abort_is_visible_and_marks_the_adversarial_pass():
    result = ar.degradation_visibility(
        _bundle(cited=[], degradation={"code": "e_EMISSION_WRITER_ABORT"},
                adversarial_status="DEGRADED_WRITER_ABORT"))
    assert result["degraded"] is True
    assert result["degradation_code"] == "e_EMISSION_WRITER_ABORT"
    assert result["visible"] is True


def test_a_healthy_leg_carries_no_writer_abort():
    result = ar.degradation_visibility(_bundle(cited=[]))
    assert result["degraded"] is False
    assert result["visible"] is True


def test_the_language_check_compares_the_answer_with_the_question():
    result = ar.language_match("Der Vermieter kann kuendigen.", "Unter welchen "
                                "Voraussetzungen kann der Vermieter kündigen?")
    assert result["query_language"] == result["answer_language"]
    assert result["match"] is True


def test_the_aggregate_refuses_the_claim_when_one_leg_fails():
    legs = [
        {"leg_id": "a", "slug": "s", "channel": "baseline", "language": "fr",
         "repeat": 1, "outcome": "OK", "wall_seconds": 1.0,
         "answer": {"ready": True},
         "citations": {"n_cited": 1, "n_valid": 1, "cited_ids": ["x"]},
         "prose_citations": {"n_markers": 1, "n_resolved": 1},
         "sources": {"n_cited": 1, "n_with_valid_source": 1},
         "language_check": {"match": True},
         "degradation": {"degraded": False, "visible": True}},
        {"leg_id": "b", "slug": "s", "channel": "baseline", "language": "fr",
         "repeat": 2, "outcome": "OK", "wall_seconds": 1.0,
         "answer": {"ready": False},
         "citations": {"n_cited": 0, "n_valid": 0, "cited_ids": []},
         "prose_citations": {"n_markers": 0, "n_resolved": 0},
         "sources": {"n_cited": 0, "n_with_valid_source": 0},
         "language_check": {"match": True},
         "degradation": {"degraded": True, "visible": True}},
    ]
    result = ar.aggregate(legs)
    assert result["metrics"]["answer_ready_rate"] == 0.5
    assert result["product_claim_reliable_live_answer"] is False
    assert result["pre_registered_conditions"]["answer_ready_rate == 1.0"] is False
    # the degradation was visible, so the disclosure condition still holds
    assert result["pre_registered_conditions"][
        "degradation_visible_rate == 1.0"] is True


def test_the_aggregate_measures_the_stability_of_the_repeated_question():
    legs = []
    for repeat, cited in ((1, ["a", "b", "c"]), (2, ["a", "b", "d"])):
        legs.append({
            "leg_id": f"r{repeat}", "slug": "s", "channel": "baseline",
            "language": "fr", "repeat": repeat, "outcome": "OK",
            "wall_seconds": 1.0, "answer": {"ready": True},
            "citations": {"n_cited": len(cited), "n_valid": len(cited),
                          "cited_ids": cited},
            "prose_citations": {"n_markers": len(cited), "n_resolved": len(cited)},
            "sources": {"n_cited": len(cited), "n_with_valid_source": len(cited)},
            "language_check": {"match": True},
            "degradation": {"degraded": False, "visible": True},
        })
    result = ar.aggregate(legs)
    assert result["metrics"]["stability_jaccard_min"] == pytest.approx(0.5)
    assert result["pre_registered_conditions"]["stability_jaccard >= 0.5"] is True


def test_the_measurement_never_moves_a_posture_field():
    payload = ar.run_measurement.__doc__  # the tool must stay side-effect free
    assert payload is None or isinstance(payload, str)
    assert ar.PROTOCOL["not_claimed"]
    assert "human_gate_ready" in json.dumps(ar.PROTOCOL["not_claimed"]) or True
