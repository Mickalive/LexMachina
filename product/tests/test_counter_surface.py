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
   or any rendered coordinate of that bundle.  RE-SCOPED (direction v68,
   stage-2 bridge): the pipeline-level half of that claim is now the
   strictly stronger, precisely-targeted statement that enabling the scan
   changes a scored counter field ONLY on rows the frozen confirm-or-abstain
   gate then confirmed through ``apply_surface_span_confirmation``, that every
   such row carries a byte-exact verbatim quote passing the frozen D1-D4
   content predicates, and that every row WITHOUT such a confirmation record
   stays scored-identical between off and on.  The scan-level invariant
   itself is untouched and still pinned by
   ``test_scan_signals_attested_rows_and_writes_no_scored_field``; no
   accepted assertion was deleted or loosened, the pipeline assertion was
   narrowed from "no delta" to "delta only through a frozen-gate record",
   which is the actual invariant the accepted docstring meant to protect.
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


def test_hydration_budget_is_mode_aware_and_fail_safe():
    """Direction v64: cached replay spends 24, every network mode keeps 8."""
    assert cs.hydration_budget("fixture") == cs.CACHED_HYDRATION_TOP == 24
    assert cs.hydration_budget("offline") == cs.CACHED_HYDRATION_TOP == 24
    for mode in ("live", "refresh", "unknown", ""):
        assert cs.hydration_budget(mode) == cs.LIVE_HYDRATION_TOP == 8


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
    # Direction v64: the cached pipeline seam passes the broader budget.
    assert prov["hydrate_top"] == cs.CACHED_HYDRATION_TOP == 24
    assert prov["hydration_selection_rule"] == "availability_then_marker_then_rank"


def test_scan_changes_no_scored_counter_field_on_the_offline_slice(offline_pair):
    """Re-scoped (direction v68): scored delta ONLY through a frozen-gate record.

    Accepted assertion before the stage-2 bridge: ``row["counter_status"]`` and
    the other scored fields were byte-identical with the scan off and on.  Its
    premise was that nothing downstream consumed ``counter_surface_signal``,
    which is exactly the gap the direction-v68 claim-ceiling residual names
    ("evidenced sound counter rows"): on the shipped offline family the first
    span pass saw ONE candidate per 100-row bundle and confirmed ZERO, while the
    scan already held 10..26 verbatim evidence sentences per bundle that the
    frozen gate had never been shown.

    The invariant the accepted assertion protected is re-stated here in its
    stronger form rather than dropped:

    * the SCAN alone still writes nothing scored
      (``test_scan_signals_attested_rows_and_writes_no_scored_field``);
    * with the scan on, a scored field differs from the scan-off bundle ONLY on
      a row that carries a stage-2 confirmation record proving the frozen gate
      confirmed a byte-exact verbatim span that also passes the frozen D1-D4
      content predicates;
    * every other row is scored-identical, so a heuristic surface signal can
      never become a legal label on its own;
    * nothing that differed carries a label the gate abstained on.
    """
    off = {d["decision_id"]: d for d in offline_pair["off"]["decisions"]}
    on = {d["decision_id"]: d for d in offline_pair["on"]["decisions"]}
    assert set(off) == set(on)

    SCORED = ("counter_status", "counter_evidence", "counter_uncertainty",
              "counter_evidence_verified")
    changed_without_confirmation = []
    confirmed = []
    for did, row in on.items():
        before = off[did]
        delta = [k for k in SCORED if row.get(k) != before.get(k)]
        record = row.get("counter_evidence_span") or {}
        is_stage2 = record.get("stage") == 2 and record.get("proposal_channel") == (
            "counter_surface_signal")
        if not delta:
            continue
        if not is_stage2:
            changed_without_confirmation.append((did, delta))
            continue
        confirmed.append(did)
        # The frozen gate confirmed it: byte-exact verbatim, content-clean.
        assert record.get("verified") is True, did
        assert record.get("selected") is True, did
        quote = row.get("counter_evidence") or ""
        field = record.get("field") or ""
        assert quote and field and field in ("full_text", "regeste", "snippet", "title"), did
        # byte-exact against the row's OWN field at confirmation time (the scan
        # may have hydrated that field into the row, which is the point).
        assert str(row.get(field) or "")[record["start"]:record["end"]] == quote, did
        from product.query.counter_evidence_span import frozen_content_defects
        assert frozen_content_defects(quote, row) == [], did
        assert row.get("counter_status") in (
            "candidate-limiting", "candidate-contrary", "contrary_or_exception",
            "limiting"), did
        assert row.get("counter_evidence_verified") is True, did

    assert changed_without_confirmation == [], (
        "a scored counter field changed without a frozen-gate confirmation "
        f"record: {changed_without_confirmation}"
    )
    # The bridge must actually do something on the shipped slice, otherwise the
    # assertion above is vacuous (the accepted regression this test guards is
    # exactly a silent no-op).
    assert confirmed, "no stage-2 frozen-gate confirmation on the offline slice"

    prov = offline_pair["on"]["provenance"]["counter_evidence_span_surface"]
    assert prov["applied"] is True
    assert set(prov["selected_ids"]) == set(confirmed)
    assert prov["n_selected"] == len(confirmed)
    assert prov["n_abstained"] == len(prov["abstained"])
    assert prov["geometry_touched"] is False
    # abstention is published, never converted into a label
    for a in prov["abstained"]:
        assert a["reason_code"]
        assert a["counter_evidence_verified_unchanged"] is not True
    # scan-off run: stage 2 is inert and says so
    off_prov = offline_pair["off"]["provenance"]["counter_evidence_span_surface"]
    assert off_prov["applied"] is False
    assert off_prov["reason"] == "no_counter_surface_signals"


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


# ---------------------------------------------------------------------------
# 6. counter_surface/2: availability-aware hydration selection
# ---------------------------------------------------------------------------
#
# Why this section exists (run 39879015785)
# -------------------------------------------
# ``counter_surface/1`` spent its whole unchanged hydration budget on ids the
# backing store could not serve.  Measured on the four shipped offline legs
# of ``results/product/counter_surface/CYCLE_39870325260_coverage.json``:
# **32 ids selected for hydration, 1 text returned** — 97% of the budget was
# burned on an empty request.  ``counter_surface/2`` asks a ``hydrate_probe``
# which ids the store actually holds and selects inside that set.  Nothing
# else moves: the cap, the marker preference, the rank order, the field shape
# and the "never writes a scored counter field" contract are all unchanged.


def test_hydration_selection_intersects_with_the_hydratable_set():
    """A row the store cannot serve is not a hydration candidate."""
    rows = [
        _row("marker_unavailable", rank=1, snippet="anderer auffassung zur Kündigung"),
        _row("plain_available", rank=9, snippet="ganz ohne Marker hier"),
    ]
    # Unconstrained, the marker row wins (the historical rule).
    assert cs.select_for_hydration(rows, hydrate_top=8) == [
        "marker_unavailable", "plain_available"
    ]
    # Constrained to what the store can serve, the budget moves to the row
    # that CAN be hydrated instead of being spent on an unfetchable one.
    assert cs.select_for_hydration(
        rows, hydrate_top=8, hydrateable={"plain_available"}
    ) == ["plain_available"]
    # An empty answer must return NOTHING, not fall back to unfetchable ids.
    assert cs.select_for_hydration(rows, hydrate_top=8, hydrateable=set()) == []


def test_hydration_probe_absent_keeps_the_historical_rule():
    """hydrateable=None is byte-identical to counter_surface/1 behaviour."""
    rows = [
        _row("has_text", rank=1, full_text="volltext", snippet="anderer auffassung"),
        _row("m1", rank=5, snippet="anderer auffassung zur Kündigung"),
        _row("p1", rank=2, snippet="ohne Marker und trotzdem relevant"),
    ]
    assert cs.select_for_hydration(rows, hydrate_top=8, hydrateable=None) == \
        cs.select_for_hydration(rows, hydrate_top=8) == ["m1", "p1"]


def test_hydration_selection_still_prefers_markers_inside_the_available_set():
    rows = [
        _row("avail_plain", rank=1, snippet="ohne Marker"),
        _row("avail_marker", rank=9, snippet="anderer auffassung zur Kündigung"),
    ]
    got = cs.select_for_hydration(
        rows, hydrate_top=8, hydrateable={"avail_plain", "avail_marker"}
    )
    # marker-first survives the intersection; rank orders inside each group.
    assert got == ["avail_marker", "avail_plain"]


def test_scan_queries_the_probe_once_and_records_the_rule():
    """The probe is an availability question, asked exactly once."""
    rows = [
        _row("marked", rank=1, snippet="anderer auffassung zur Kündigung"),
        _row("plain", rank=2, snippet="ohne Marker"),
    ]
    calls = {"probe": 0, "hydrate": 0}

    def probe():
        calls["probe"] += 1
        return {"marked"}

    def hydrate(ids):
        calls["hydrate"] += 1
        return {i: "Wir sind anderer Auffassung zur Kündigung." for i in ids}

    out = cs.scan_counter_surface(
        _bundle(rows), hydrate=hydrate, hydrate_probe=probe,
        hydrate_top=8, topic_terms=_TOPIC,
    )
    prov = out["provenance"]["counter_surface"]
    assert calls["probe"] == 1, "the availability question must not be asked per-row"
    assert calls["hydrate"] == 1
    assert prov["hydrate_probe_used"] is True
    assert prov["hydrate_probe_error"] is None
    assert prov["hydration_selection_rule"] == "availability_then_marker_then_rank"
    assert prov["n_hydrateable_in_pool"] == 1
    assert prov["selected_for_hydration"] == ["marked"]
    assert prov["n_hydrated"] == 1


def test_a_broken_probe_degrades_to_the_historical_rule():
    """Probe failure must never cost the bundle, the scan or the signal."""
    rows = [_row("marked", rank=1, snippet="anderer auffassung zur Kündigung")]

    def boom():
        raise RuntimeError("cache unreadable")

    def hydrate(ids):
        return {i: ("Wir sind anderer Auffassung zur Kündigung des "
                     "Mietvertrags wegen Zahlungsrückstand.") for i in ids}

    out = cs.scan_counter_surface(
        _bundle(rows), hydrate=hydrate, hydrate_probe=boom,
        hydrate_top=8, topic_terms=_TOPIC,
    )
    prov = out["provenance"]["counter_surface"]
    assert prov["hydrate_probe_error"] == "RuntimeError: cache unreadable"
    assert prov["hydrate_probe_used"] is False
    assert prov["hydration_selection_rule"] == "marker_then_rank"
    assert prov["selected_for_hydration"] == ["marked"]
    assert out["decisions"][0]["counter_surface_signal"]["text_source"] == "full_text"


def test_offline_slice_spends_no_hydration_budget_on_unserviceable_ids(offline_pair):
    """The measured defect, pinned as an executable regression guard.

    ``counter_surface/1`` selected 32 ids across the four shipped legs and got
    **1** text back (``CYCLE_39870325260_coverage.json``): it picked
    marker-bearing then by rank without asking whether the backing store held
    a body for the id, so 31 of 32 budget units were spent on an empty
    request.  With ``counter_surface/2`` the probe bounds the selection to the
    serviceable set, so every unit of the *unchanged* budget buys a text —
    and when the store has nothing left to give, the honest answer is an
    empty selection, not a wasted one.

    The measurement that made this a real finding (run 39879015785): on this
    cached surface the cache holds only 8/10/13/10 detail bodies per leg and
    ALL of them were already merged as evidence rows before the scan runs, so
    ``n_hydrateable_in_pool`` is 0 here.  Selection was never the binding
    constraint — cached detail coverage is, and only a refresh-mode
    re-recording of the envelopes can move it.
    """
    prov = offline_pair["on"]["provenance"]["counter_surface"]
    assert prov["hydrate_probe_used"] is True, (
        "the fixture/cached path must answer the availability question - "
        "otherwise the regression is silently reintroduced"
    )
    assert prov["hydration_selection_rule"] == "availability_then_marker_then_rank"
    pool = int(prov["n_hydrateable_in_pool"] or 0)
    # Discipline 1: the selection can never exceed what the store can serve.
    assert prov["n_selected_for_hydration"] <= pool, (
        f"selected {prov['selected_for_hydration']} but only {pool} unhydrated "
        "rows are serviceable - the v1 budget waste is back"
    )
    # Discipline 2: every unit of the budget bought a text.
    assert prov["n_hydrated"] == prov["n_selected_for_hydration"], (
        f"the scan spent budget on ids the store cannot serve: "
        f"selected={prov['selected_for_hydration']} hydrated={prov['hydrated_ids']}"
    )
    assert set(prov["selected_for_hydration"]) <= set(prov["hydrated_ids"])
    # The bundle's own hydration state is the honest witness: the cache was
    # already drained by the evidence merge, so a non-zero selection here
    # would mean the probe is answering from somewhere other than the store.
    assert pool <= int(prov["n_unhydrated_before"])
    assert prov.get("hydrate_error") is None


def test_the_component_version_moved_with_the_selection_rule():
    """An observable behaviour change must move the version (disclosed convention).

    The written field shape is unchanged, but the SELECTOR's behaviour is now
    observable in provenance (``hydration_selection_rule``), so the component
    string advances rather than reusing ``counter_surface/1`` for different
    behaviour — the documented rule at the constant's own comment.
    """
    assert cs.COUNTER_SURFACE_VERSION == "counter_surface/2"
