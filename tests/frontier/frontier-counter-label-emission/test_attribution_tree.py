"""Attribution-tree resolution tests (acceptance test 2)."""

from __future__ import annotations

import copy

from conftest import PACKET, requires_accepted
from frontier_counter_label_emission import (
    ALL_CAUSES,
    CAUSE_A,
    CAUSE_B,
    CAUSE_C,
    CAUSE_D,
    CAUSE_E,
    SCORED_STATUSES,
    attribute_bundle,
    attribute_packet,
)


def test_cause_b_no_probes(base_bundle):
    b = copy.deepcopy(base_bundle)
    b["provenance"]["adversarial_retrieval"] = {
        "attempted": False, "n_candidates": 0, "probes": [], "channels": [],
    }
    rec = attribute_bundle(b, SCORED_STATUSES)
    assert rec["primary_cause"] == CAUSE_B
    assert rec["secondary_causes"] == []


def test_cause_a_exception_fallback_no_signal(base_bundle):
    b = copy.deepcopy(base_bundle)
    for d in b["decisions"]:
        d["provenance"] = "ocl:adversarial.exception variant=adversarial:exception page=0"
        d["adversarial_retrieval_signal"] = {"heuristic_status": None, "evidence": "", "markers": []}
    rec = attribute_bundle(b, SCORED_STATUSES)
    assert rec["primary_cause"] == CAUSE_A
    assert rec["evidence"]["n_heuristic_positive"] == 0


def test_cause_c_all_lazy_no_signal(base_bundle):
    b = copy.deepcopy(base_bundle)
    for d in b["decisions"]:
        d["provenance"] = "ocl:adversarial.minority variant=adversarial:minority page=0"
        d["adversarial_retrieval_signal"] = {"heuristic_status": None, "evidence": "", "markers": []}
        d["full_text_status"] = "lazy"
        d["full_text"] = ""
    rec = attribute_bundle(b, SCORED_STATUSES)
    assert rec["primary_cause"] == CAUSE_C


def test_cause_d_gate_suppressed(base_bundle):
    # Row has full text that WOULD pass the gate but carries no heuristic signal.
    b = copy.deepcopy(base_bundle)
    for d in b["decisions"]:
        d["adversarial_retrieval_signal"] = {"heuristic_status": None, "evidence": "", "markers": []}
        d["full_text_status"] = "fetched"
        d["full_text"] = (
            "Vorbehaltlich der ausdrücklichen Ausnahme begrenzt die Fürsorgepflicht "
            "des Arbeitgebers die Überwachungspflicht bei Kapitalverletzung."
        )
    rec = attribute_bundle(b, SCORED_STATUSES)
    assert rec["primary_cause"] == CAUSE_D
    assert rec["evidence"]["n_gate_suppressed"] >= 1


def test_cause_e_emission_writer_abort(base_bundle):
    rec = attribute_bundle(base_bundle, SCORED_STATUSES)
    assert rec["primary_cause"] == CAUSE_E
    assert rec["evidence"]["n_heuristic_positive"] >= 1
    assert rec["evidence"]["n_scored_before"] == 0
    assert rec["evidence"]["llm_reviewer_n_findings"] == 0


def test_exactly_one_primary_and_evidence_fields(base_bundle):
    rec = attribute_bundle(base_bundle, SCORED_STATUSES)
    assert rec["primary_cause"] in ALL_CAUSES
    assert isinstance(rec["secondary_causes"], list)
    assert "row_evidence" in rec
    assert "llm_reviewer" in rec
    for row in rec["row_evidence"]:
        assert "decision_id" in row
        assert "heuristic_status" in row
        assert "counter_status" in row


@requires_accepted
def test_real_packet_attribution_is_deterministic():
    a1 = attribute_packet(PACKET, SCORED_STATUSES)
    a2 = attribute_packet(PACKET, SCORED_STATUSES)
    assert a1 == a2
    for qid, rec in a1.items():
        assert rec["primary_cause"] in ALL_CAUSES
        assert len(rec["primary_cause"]) > 0


@requires_accepted
def test_real_packet_all_three_resolved():
    a = attribute_packet(PACKET, SCORED_STATUSES)
    assert set(a) == {"de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica"}
