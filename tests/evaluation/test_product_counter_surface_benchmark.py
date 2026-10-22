"""Focused tests for the product counter-signal benchmark.

These are read-only: they exercise the frozen sample and the shipped product
module, but never write results or touch the network.
"""
from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest

import evaluation.product_counter_surface_benchmark as bench


def test_frozen_inputs_and_product_pins_are_unchanged():
    freeze = json.loads(bench.FREEZE_PATH.read_text(encoding="utf-8"))
    assert bench.sha256(bench.HYPOTHESIS_PATH) == freeze["hypothesis_sha256"]
    assert bench.sha256(bench.SPEC_PATH) == freeze["sample_pins"]["frozen_spec_sha256"]
    assert (
        bench.sha256(bench.ACCEPTED_RECORD_PATH)
        == freeze["sample_pins"]["accepted_cached_bundle_record_sha256"]
    )
    assert (
        bench.sha256(bench.BUNDLE_PRODUCER_PATH)
        == freeze["sample_pins"]["bundle_producer_sha256"]
    )
    product_root = Path(freeze["product_root"])
    for rel, expected in freeze["product_files"].items():
        assert bench.sha256(product_root / rel) == expected


def test_product_module_identity_and_classifier_guards():
    freeze = json.loads(bench.FREEZE_PATH.read_text(encoding="utf-8"))
    modules = bench.load_product(Path(freeze["product_root"]))
    ar = modules["adversarial_retrieval"]
    assert ar.ADVERSARIAL_RETRIEVAL_VERSION == "adversarial_retrieval/3"
    planted = (
        "Dies ist eine Ausnahme von der Regel. Der Mieter kann den Mietvertrag "
        "wegen Zahlungsverzugs kündigen. Der Vermieter muss die Kündigung "
        "schriftlich begründen."
    )
    topic = ["mieter", "mietvertrag", "kündigung"]
    status, evidence, markers = ar.classify_against_intent(
        planted, "exception", topic_terms=topic
    )
    assert status == "candidate-limiting"
    assert evidence
    assert "ausnahme" in markers
    assert ar.classify_against_intent(planted, "exception", topic_terms=[])[0] is None
    assert ar.classify_against_intent(
        "Das Gericht weist die Beschwerde ab. Der Mieter schuldet die Miete.",
        "exception", topic_terms=topic,
    )[0] is None


def test_network_guard_fails_closed():
    guard = bench.NetworkGuard()
    with guard:
        with pytest.raises(RuntimeError):
            socket.socket().connect(("example.invalid", 443))
    assert guard.calls


def test_cached_sample_pool_parity_and_known_counter_reach():
    freeze = json.loads(bench.FREEZE_PATH.read_text(encoding="utf-8"))
    spec = json.loads(bench.SPEC_PATH.read_text(encoding="utf-8"))
    measurement = bench.build_measurement(
        spec=spec, product_root=Path(freeze["product_root"]), freeze=freeze
    )
    assert measurement["cache"]["n_envelopes"] == 24
    assert measurement["aggregate"]["known_expected_n"] == 28
    assert measurement["aggregate"]["known_reached_n"] == 14
    assert measurement["aggregate"]["pool_n"] == 867
    assert [q["pool_n"] for q in measurement["questions"]] == [223, 218, 221, 205]
    assert all(q["duplicate_free"] for q in measurement["questions"])
    # The accepted marker rule labels one reached known row; the offline
    # product surface must at least not silently drop that fact.
    assert measurement["aggregate"]["known_marker_labelled_n"] == 1


def test_hydration_index_prefers_nonempty_full_text():
    freeze = json.loads(bench.FREEZE_PATH.read_text(encoding="utf-8"))
    docs = bench.index_product_docs(Path(freeze["product_root"]))
    assert docs["n_files"] == 609
    assert docs["n_full_text_docs"] >= 145
    assert len(docs["by_core"]["146iv68"]["full_text"]) > 10000
    assert len(docs["by_core"]["124iii25"]["full_text"]) > 10000


def test_frozen_gate_contract_is_complete_and_nonvacuous():
    freeze = json.loads(bench.FREEZE_PATH.read_text(encoding="utf-8"))
    spec = json.loads(bench.SPEC_PATH.read_text(encoding="utf-8"))
    measurement = bench.build_measurement(
        spec=spec, product_root=Path(freeze["product_root"]), freeze=freeze
    )
    gates = measurement["gates"]
    assert list(gates) == [
        "G1_offline_product_signal_on_every_question",
        "G2_offline_product_signal_reaches_known_counter_authority",
        "G3_hydrated_product_signal_reaches_known_counter_authority",
        "G4_hydration_surface_available_for_g3",
        "G5_same_surface_product_signal_not_worse_than_marker_rule_on_known",
        "G6_every_signal_has_verbatim_evidence",
        "G7_pool_provenance_and_duplicate_free",
    ]
    # Structural validity only; the product verdict is written by run().
    assert gates["G6_every_signal_has_verbatim_evidence"]["passed"]
    assert gates["G7_pool_provenance_and_duplicate_free"]["passed"]
    assert measurement["aggregate"]["known_hydrated_n"] > 0
