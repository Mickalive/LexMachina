"""Direction v63 ordered item 7(a): pool counter-surface coverage.

Why this module exists
----------------------
The accepted cached counter-surface falsification (anchor run 39838415410)
measured 0/14 known authorities signalled and 5/14 hydrated: the shipped
counter surface only ever examined rows that reached the map through the
adversarial probes, so an authority the initial pass already retrieved was
never looked at.  ``product/query/counter_surface.py`` closes that gap with a
bounded, disclosure-only scan of the rendered pool (broader hydration +
lexicon alignment + two precision guards).  These tests pin the contract that
makes the scan safe to ship:

1. the aligned lexicon is ADDITIVE and disjoint from the frozen planner
   markers (the planner sha 9764a37e... must never drift);
2. the scan writes ``counter_surface_signal`` — never ``counter_status``,
   geometry, ranks or clusters;
3. short markers are word-boundary-checked (the FR ``sauf`` / DE
   ``Zahlungsaufforderung`` compound collision measured on the rent-default
   slice) and a dismissal narration licenses no signal for any intent;
4. hydration selection is marker-preferring, rank-ordered and hard-capped;
5. the env kill-switch is fail-open-to-honesty: ``off`` records a skip and
   changes nothing;
6. the full offline vertical slice (fixture enrich) still passes with the
   scan on, and the scan provably does not change any scored counter field
   or any rendered coordinate of that bundle.
"""
from __future__ import annotations

import copy
import json
import socket
import sys
from pathlib import Path

import pytest

PRODUCT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PRODUCT_ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from product.query import counter_surface as cs  # noqa: E402
from product.query.adversarial_retrieval import (  # noqa: E402
    ADVERSARIAL_RETRIEVAL_VERSION,
    EVIDENCE_MARKERS,
)

_TOPIC = ["mietvertrag", "kuendigung", "mietzins"]

#: The planner version pinned by evaluation's V2 re-freeze condition
#: (direction v63 item 7b): the planner sha must not drift in this cycle.
PLANNER_VERSION_PIN = "adversarial_retrieval/3"


def _row(did: str, **kw) -> dict:
    row = {
        "decision_id": did,
        "rank": kw.pop("rank", 1),
        "counter_status": kw.pop("counter_status", "none"),
        "x": kw.pop("x", 0.1),
        "y": kw.pop("y", -0.2),
        "cluster_id": kw.pop("cluster_id", 3),
    }
    row.update(kw)
    return row


def _bundle(rows: list[dict], *, query: str = "Kündigung Mietvertrag Mietrecht") -> dict:
    return {
        "query": query,
        "decisions": copy.deepcopy(rows),
        "answer": {"prose": "Kündigung des Mietvertrags wegen Zahlungsrückstand."},
        "provenance": {},
    }


# ---------------------------------------------------------------------------
# 1. lexicon alignment contract
# ---------------------------------------------------------------------------

def test_planner_version_is_unchanged():
    assert ADVERSARIAL_RETRIEVAL_VERSION == PLANNER_VERSION_PIN


def test_aligned_markers_are_additive_and_disjoint():
    for intent, markers in cs.ALIGNED_MARKERS.items():
        frozen = set(EVIDENCE_MARKERS.get(intent, ()))
        for marker in markers:
            assert marker not in frozen, (intent, marker)
            assert marker in cs.combined_markers(intent)


def test_aligned_markers_fire_on_attested_sentences():
    cases = [
        ("contrary", "Der Vorinstanz ist nicht beizutreten; wir sind anderer "
                     "Auffassung, was die Kündigung anbelangt.", ["anderer auffassung"]),
        ("contrary", "Diese Auffassung kann nicht gefolgt werden, denn der "
                     "Mietvertrag sieht eine andere Regelung vor.",
         ["kann nicht gefolgt werden"]),
        ("older_line", "Bis anhin galt eine andere Rechtsprechung zur "
                       "Zahlungsaufforderung.", ["bis anhin"]),
        ("exception", "Behaltlich des nachgewiesenen Zahlungsrückstandes kann "
                      "die Kündigung ausgesprochen werden.", ["behaltlich"]),
    ]
    for intent, text, want in cases:
        got = cs.attested_markers(text, cs.ALIGNED_MARKERS[intent])
        assert got == want, (intent, text, got)


def test_scan_classify_uses_aligned_markers():
    text = ("Der Vorinstanz ist nicht beizutreten; wir sind anderer Auffassung "
            "zur Kündigung des Mietvertrags.")
    status, evidence, markers, matched = cs.scan_classify(
        text, "contrary", topic_terms=_TOPIC)
    assert status == "candidate-contrary"
    assert matched == "contrary"
    assert "anderer auffassung" in markers
    assert evidence


def test_short_marker_compound_collision_is_rejected():
    """FR 'sauf' inside the DE compound Zahlungsaufforderung is NOT attested."""
    text = ("Eine Zahlungsaufforderung mit Kündigungsandrohung verlängert die "
            "Zahlungsfrist für frühere Mietzinse nicht.")
    assert "sauf" in text  # the raw substring is present...
    assert cs.attested_markers(text, ["sauf"]) == []  # ...but not as a word
    # while a genuine French occurrence is kept
    fr = "La résiliation est admise, sauf si le locataire régularise."
    assert cs.attested_markers(fr, ["sauf"]) == ["sauf"]


def test_disposal_narration_guard_applies_to_every_intent():
    sentence = ("Der Recours des Mieters wurde abgewiesen, soweit die "
                "Kündigung wegen Zahlungsrückstand betreffend den Mietvertrag.")
    assert cs._disposal_narration(sentence)


# ---------------------------------------------------------------------------
# 2. hydration selection contract
# ---------------------------------------------------------------------------

def test_hydration_prefers_marker_bearing_rows_then_rank():
    rows = [
        _row("plain_high", rank=1, snippet="Mietvertrag Zahlungsrückstand"),
        _row("marker_mid", rank=5, snippet="anderer auffassung zur Kündigung"),
        _row("marker_low", rank=9, snippet="bis anhin galt andere Rechtsprechung"),
    ]
    got = cs.select_for_hydration(rows, hydrate_top=2)
    assert got == ["marker_mid", "marker_low"]


def test_hydration_cap_is_hard():
    rows = [_row(f"m{i}", rank=i, snippet="andeutungsweise vorbehalt") for i in range(1, 6)]
    assert len(cs.select_for_hydration(rows, hydrate_top=3)) == 3
    assert cs.select_for_hydration(rows, hydrate_top=0) == []


def test_hydration_skips_already_hydrated_rows():
    rows = [
        _row("has_text", rank=1, full_text="volltext", snippet="anderer auffassung"),
        _row("needs_text", rank=2, snippet="anderer auffassung zur Kündigung"),
    ]
    assert cs.select_for_hydration(rows, hydrate_top=8) == ["needs_text"]


# ---------------------------------------------------------------------------
# 3. scan contract
# ---------------------------------------------------------------------------

def test_scan_signals_attested_rows_and_writes_no_scored_field():
    rows = [
        _row("contrary_row", rank=1, full_text=(
            "Der Vorinstanz kann nicht beigetreten werden; wir sind anderer "
            "Auffassung, was die Kündigung des Mietvertrags anbelangt.")),
        _row("quiet_row", rank=2, full_text="Der Mietvertrag wurde aufgelöst."),
    ]
    bundle = _bundle(rows)
    out = cs.scan_counter_surface(bundle, topic_terms=_TOPIC)
    by_id = {d["decision_id"]: d for d in out["decisions"]}
    sig = by_id["contrary_row"].get("counter_surface_signal")
    assert sig and sig["heuristic_status"] == "candidate-contrary"
    assert "anderer auffassung" in sig["markers"]
    assert sig["evidence"]
    assert "counter_surface_signal" not in by_id["quiet_row"]
    # the input bundle is untouched and no scored field is written anywhere
    assert "counter_surface_signal" not in bundle["decisions"][0]
    for d in out["decisions"]:
        assert d["counter_status"] == "none"
        assert "counter_evidence" not in d or d["counter_evidence"] == ""
    prov = out["provenance"]["counter_surface"]
    assert prov["n_signalled"] == 1
    assert prov["writes_scored_counter_fields"] is False
    assert prov["signalled_ids"] == ["contrary_row"]


def test_scan_never_moves_geometry_or_rank():
    rows = [_row("a", rank=4, x=0.31, y=-0.77, cluster_id=2, full_text=(
        "Die Rechtsprechung zur Kündigung wurde bestätigt; wir sind anderer "
        "Auffassung zur Zahlungsfrist des Mietvertrags."))]
    out = cs.scan_counter_surface(_bundle(rows), topic_terms=_TOPIC)
    d = out["decisions"][0]
    assert (d["x"], d["y"], d["cluster_id"], d["rank"]) == (0.31, -0.77, 2, 4)


def test_scan_signals_from_regeste_when_no_full_text():
    rows = [_row("reg_row", rank=3, regeste=(
        "Exceptions à ce principe en matière de résiliation du bail à loyer."))]
    out = cs.scan_counter_surface(
        _bundle(rows), topic_terms=["résiliation", "bail", "loyer"])
    sig = out["decisions"][0].get("counter_surface_signal")
    assert sig and sig["text_source"] == "regeste"
    assert sig["intent"] == "exception"


def test_scan_uses_hydration_callback_and_records_it():
    rows = [_row("needs", rank=1, snippet="anderer auffassung zur Kündigung "
                                          "des Mietvertrags")]
    seen: dict[str, list[str]] = {}

    def hydrate(ids):
        seen["ids"] = list(ids)
        return {"needs": "Wir sind anderer Auffassung zur Kündigung des "
                         "Mietvertrags wegen Zahlungsrückstand."}

    out = cs.scan_counter_surface(_bundle(rows), hydrate=hydrate, hydrate_top=5,
                                  topic_terms=_TOPIC)
    assert seen["ids"] == ["needs"]
    prov = out["provenance"]["counter_surface"]
    assert prov["n_hydrated"] == 1 and prov["hydrated_ids"] == ["needs"]
    assert out["decisions"][0]["counter_surface_signal"]["text_source"] == "full_text"


def test_scan_survives_a_broken_hydrator():
    rows = [_row("needs", rank=1, snippet="anderer auffassung")]
    out = cs.scan_counter_surface(
        _bundle(rows), hydrate=lambda ids: (_ for _ in ()).throw(RuntimeError("boom")),
        topic_terms=_TOPIC)
    prov = out["provenance"]["counter_surface"]
    assert prov["hydrate_error"].startswith("RuntimeError")
    assert prov["n_hydrated"] == 0


def test_disposal_narration_never_signals_for_any_intent():
    rows = [_row("disp", rank=1, full_text=(
        "Der Recours des Mieters wurde abgewiesen, soweit die Kündigung wegen "
        "Zahlungsrückstand betreffend den Mietvertrag; andere Auffassung "
        "vertritt diesbezüglich die Lehre."))]
    out = cs.scan_counter_surface(_bundle(rows), topic_terms=_TOPIC)
    assert "counter_surface_signal" not in out["decisions"][0]


# ---------------------------------------------------------------------------
# 4. pipeline seam + kill-switch
# ---------------------------------------------------------------------------

def test_kill_switch_records_a_skip_and_changes_nothing(monkeypatch):
    monkeypatch.setenv(cs.ENABLE_ENV, "off")
    bundle = _bundle([_row("a", rank=1, full_text="anderer auffassung zur Kündigung")])
    out = cs.apply_counter_surface(bundle)
    prov = out["provenance"]["counter_surface"]
    assert prov["skipped"] and cs.ENABLE_ENV in prov["skip_reason"]
    assert "counter_surface_signal" not in out["decisions"][0]


def test_apply_default_is_on(monkeypatch):
    monkeypatch.delenv(cs.ENABLE_ENV, raising=False)
    bundle = _bundle([_row("a", rank=1, snippet="text")])
    out = cs.apply_counter_surface(bundle, retrieval_mode="fixture")
    assert out["provenance"]["counter_surface"].get("skipped") is not True


# ---------------------------------------------------------------------------
# 5. end-to-end offline slice: scan on vs off changes no scored field
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def offline_pair():
    """Enrich the canonical fixture twice: scan disabled, then enabled."""
    from product.reality_check import LEGS
    from product.query.pipeline import enrich_query_bundle, run_query_initial

    results = {}
    real_connect = socket.socket.connect

    def _no_network(*_a, **_k):
        raise AssertionError("offline test attempted network access")

    socket.socket.connect = _no_network
    try:
        for mode in ("off", "on"):
            if mode == "off":
                import os
                os.environ[cs.ENABLE_ENV] = "off"
            else:
                import os
                os.environ.pop(cs.ENABLE_ENV, None)
            initial = run_query_initial(LEGS["rent-default"], top_n=100,
                                        retrieval_mode="fixture")
            results[mode] = enrich_query_bundle(
                initial, retrieval_mode="fixture", fixture_generation=True)
    finally:
        socket.socket.connect = real_connect
        import os
        os.environ.pop(cs.ENABLE_ENV, None)
    return results


def test_offline_enrich_has_counter_surface_provenance(offline_pair):
    prov = offline_pair["on"]["provenance"]["counter_surface"]
    assert prov["component"] == cs.COUNTER_SURFACE_VERSION
    assert prov["n_rows"] == len(offline_pair["on"]["decisions"])
    assert prov.get("skipped") is not True


def test_scan_changes_no_scored_counter_field_on_the_offline_slice(offline_pair):
    off = {d["decision_id"]: d for d in offline_pair["off"]["decisions"]}
    on = {d["decision_id"]: d for d in offline_pair["on"]["decisions"]}
    assert set(off) == set(on)
    for did, row in on.items():
        assert row["counter_status"] == off[did]["counter_status"], did
        assert row.get("counter_evidence") == off[did].get("counter_evidence"), did
        assert row.get("counter_uncertainty") == off[did].get("counter_uncertainty"), did
        assert row.get("counter_evidence_verified") == off[did].get(
            "counter_evidence_verified"), did


def test_scan_changes_no_rendered_coordinate_on_the_offline_slice(offline_pair):
    off = {d["decision_id"]: d for d in offline_pair["off"]["decisions"]}
    for d in offline_pair["on"]["decisions"]:
        o = off[d["decision_id"]]
        assert (d["x"], d["y"], d["cluster_id"], d["rank"]) == (
            o["x"], o["y"], o["cluster_id"], o["rank"]), d["decision_id"]


def test_offline_slice_signals_are_attested(offline_pair):
    prov = offline_pair["on"]["provenance"]["counter_surface"]
    for d in offline_pair["on"]["decisions"]:
        sig = d.get("counter_surface_signal")
        if not sig:
            continue
        assert sig["markers"], d["decision_id"]
        assert sig["evidence"], d["decision_id"]
        assert d["decision_id"] in prov["signalled_ids"]
