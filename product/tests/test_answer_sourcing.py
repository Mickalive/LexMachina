"""Finish the persisted snapshot of run 44694975109 (direction v68).

Run 44694975109 committed ``product/query/answer_sourcing.py`` and its
``pipeline.py`` wiring but produced NO test, result, report or state delta
before its validation/orchestration step ended.  This module is the missing
executable acceptance contract for that work:

* ``build_fixture_answer``: the offline path ships a *sourced* answer - every
  quoted passage is verbatim from a decision already cited by the bundle, the
  provenance header is preserved, citation markers all resolve, degradation is
  explicit and the fragment guard rejects header/locator cut-offs;
* ``apply_counter_authority_note``: the answer mentions the independent pass's
  counter-authorities without laundering unverified evidence, is idempotent,
  and writes ONLY ``answer.prose`` + its own provenance block (never a scored
  counter field, geometry, rank, cluster or relation);
* the shipped offline slice actually exhibits both writers through
  ``enrich_query_bundle(fixture_generation=True)``.

No frozen gate, rubric, threshold or bar is imported, edited or re-derived.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "product"
for _p in (str(ROOT), str(PRODUCT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from product.answer_reliability import prose_citation_validity  # noqa: E402
from product.query.answer_sourcing import (  # noqa: E402
    COUNTER_NOTE_VERSION,
    FIXTURE_SOURCE_VERSION,
    MAX_COUNTER_ROWS,
    MAX_FIXTURE_QUOTES,
    _complete,
    apply_counter_authority_note,
    build_fixture_answer,
)
from product.query.bundle import validate_bundle  # noqa: E402

GOOD_DE = (
    "Der Vermieter kann das Mietverhältnis bei Zahlungsverzug des Mieters "
    "fristgerecht kündigen und muss die gesetzliche Frist dabei beachten."
)


def _decision(did: str, **kw) -> dict:
    row = {
        "decision_id": did,
        "citation": f"TF {did}",
        "canonical_url": f"https://open caselaw.example/{did}".replace(" ", ""),
        "score": 0.5,
        "provenance": {},
        "title": "",
        "court": "",
        "date": "",
        "language": "de",
        "full_text": "",
        "regeste": "",
        "snippet": "",
        "counter_status": "none",
        "counter_evidence": "",
        "counter_evidence_verified": False,
        "counter_uncertainty": 1.0,
        "x": 1.0,
        "y": 2.0,
        "cluster_id": 3,
        "is_outlier": False,
        "rank": 4,
    }
    row.update(kw)
    return row


def _bundle(decisions: list[dict], *, query="Mietvertrag Kündigung",
            prose="Base answer.", status="ready") -> dict:
    return {
        "bundle_version": "1",
        "query": query,
        "query_variants": [],
        "decisions": decisions,
        "clusters": [],
        "relations": [],
        "answer": {
            "prose": prose,
            "status": status,
            "cited_decision_ids": [d["decision_id"] for d in decisions],
        },
        "provenance": {},
    }


# --------------------------------------------------------------------------- #
# 1. fragment guard (the reason a quote can be trusted as 'verbatim')
# --------------------------------------------------------------------------- #

def test_complete_sentence_guard_accepts_a_real_sentence():
    assert _complete(GOOD_DE) is True


def test_complete_sentence_guard_rejects_locator_date_lowercase_and_broken_brackets():
    assert _complete("Kurzer Satz.") is False                       # too short
    assert _complete(GOOD_DE + " (lit.") is False                   # splitter artifact
    assert _complete("vom 4. April 2015 war der Mietvertrag bereits beendet.") is False
    assert _complete(GOOD_DE[0].lower() + GOOD_DE[1:]) is False       # mid-sentence start
    assert _complete(GOOD_DE + " (vgl") is False                     # unbalanced bracket


# --------------------------------------------------------------------------- #
# 2. build_fixture_answer
# --------------------------------------------------------------------------- #

def test_fixture_answer_quotes_verbatim_from_cited_rows_and_preserves_header():
    row = _decision("bger_A", full_text="Einleitung.\n" + GOOD_DE)
    bundle = _bundle([row])
    header = "Fixture grounded answer [bger_A]"
    prose, record = build_fixture_answer(bundle, ["bger_A"], header)

    assert prose.startswith(header)
    assert GOOD_DE in prose
    assert record["version"] == FIXTURE_SOURCE_VERSION
    assert record["applied"] is True
    assert record["quoted_ids"] == ["bger_A"]
    assert record["n_quotes"] == 1
    assert record["header_preserved"] == header
    assert record["quotes"][0]["selected_by"] == "query_concept"
    assert record["quotes"][0]["query_concept_overlap"] >= 1


def test_fixture_answer_prefix_match_reaches_morphological_variant():
    # the query says Mietvertrag, the decision says Mietverhältnis
    row = _decision("bger_A", full_text=GOOD_DE)
    _, record = build_fixture_answer(_bundle([row]), ["bger_A"], "H")
    assert record["quotes"][0]["selected_by"] == "query_concept"


def test_fixture_answer_every_prose_marker_resolves_in_bundle():
    rows = [_decision(f"bger_d{i}", full_text=GOOD_DE.replace("Mietverhältnis", f"Mietverhältnis {i}"))
            for i in range(3)]
    bundle = _bundle(rows)
    prose, _ = build_fixture_answer(bundle, [r["decision_id"] for r in rows], "H")
    validity = prose_citation_validity({**bundle, "answer": {**bundle["answer"], "prose": prose}})
    assert validity["all_resolved"] is True
    assert validity["n_markers"] >= 1


def test_fixture_answer_degradation_is_explicit_not_paraphrased():
    bundle = _bundle([_decision("d0", full_text="nur ein Titel")])
    prose, record = build_fixture_answer(bundle, ["missing_id", "d0"], "HEADER")
    assert prose == "HEADER"
    assert record["applied"] is False
    assert record["reason"] == "no_complete_sentence_in_cited_rows"
    assert "missing_id" in record["skipped_ids"]
    assert "d0" in record["skipped_ids"]


def test_fixture_answer_deduplicates_and_caps_quote_count():
    rows = [_decision(f"d{i}", full_text=GOOD_DE) for i in range(8)]
    _, record = build_fixture_answer(_bundle(rows), [r["decision_id"] for r in rows], "H")
    # identical verbatim passages are emitted once, not stacked
    assert record["n_quotes"] == 1
    assert MAX_FIXTURE_QUOTES >= 1
    distinct = [_decision(f"d{i}", full_text=GOOD_DE.replace("Vermieter", f"Vermieter {i}"))
                for i in range(8)]
    _, record2 = build_fixture_answer(
        _bundle(distinct), [r["decision_id"] for r in distinct], "H")
    assert record2["n_quotes"] == MAX_FIXTURE_QUOTES


# --------------------------------------------------------------------------- #
# 3. apply_counter_authority_note
# --------------------------------------------------------------------------- #

def test_counter_note_reports_only_counter_rows_and_known_counts():
    rows = [
        _decision("cited", counter_status="cited", counter_evidence="x",
                  counter_evidence_verified=True),
        _decision("lim", counter_status="limiting",
                  counter_evidence="Dies ist ein wörtlicher Beleg.",
                  counter_evidence_verified=True),
    ]
    bundle = _bundle(rows)
    before = copy.deepcopy(bundle["decisions"])
    record = apply_counter_authority_note(bundle)
    assert record["version"] == COUNTER_NOTE_VERSION
    assert record["applied"] is True
    assert record["n_counter_rows"] == 1
    assert record["listed"][0]["decision_id"] == "lim"
    assert "Dies ist ein wörtlicher Beleg." in bundle["answer"]["prose"]
    # the scored/geometry fields are byte-unchanged
    assert bundle["decisions"] == before


def test_counter_note_never_reproduces_unverified_evidence():
    rows = [_decision("lim", counter_status="candidate-limiting",
                      counter_evidence="UNVERIFIED-SECRET-PASSAGE",
                      counter_evidence_verified=False)]
    bundle = _bundle(rows)
    apply_counter_authority_note(bundle)
    prose = bundle["answer"]["prose"]
    assert "UNVERIFIED-SECRET-PASSAGE" not in prose
    assert "unevidenced" in prose or "NON confirmé" in prose or "NICHT" in prose


def test_counter_note_is_idempotent():
    rows = [_decision("lim", counter_status="limiting",
                      counter_evidence="Beleg", counter_evidence_verified=True)]
    bundle = _bundle(rows)
    first = apply_counter_authority_note(bundle)
    prose_once = bundle["answer"]["prose"]
    second = apply_counter_authority_note(bundle)
    assert second == first
    assert bundle["answer"]["prose"] == prose_once


def test_counter_note_respects_answer_status_and_empty_population():
    rows = [_decision("lim", counter_status="limiting", counter_evidence="Beleg",
                      counter_evidence_verified=True)]
    pending = _bundle(rows, prose="pending", status="pending")
    r1 = apply_counter_authority_note(pending)
    assert r1["applied"] is False and r1["reason"] == "answer_not_ready"
    assert pending["answer"]["prose"] == "pending"

    empty = _bundle([_decision("plain")])
    r2 = apply_counter_authority_note(empty)
    assert r2["applied"] is False and r2["reason"] == "no_counter_authority_rows"


def test_counter_note_truncates_bounded_list():
    rows = [_decision(f"lim{i}", counter_status="limiting") for i in range(MAX_COUNTER_ROWS + 3)]
    bundle = _bundle(rows)
    record = apply_counter_authority_note(bundle)
    assert record["n_counter_rows"] == MAX_COUNTER_ROWS + 3
    assert record["n_listed"] == MAX_COUNTER_ROWS
    assert record["n_truncated"] == 3


def test_counter_note_markers_resolve_and_bundle_stays_valid():
    rows = [_decision(f"lim{i}", counter_status="limiting",
                      counter_evidence=f"Beleg {i}", counter_evidence_verified=True)
            for i in range(3)]
    bundle = _bundle(rows)
    apply_counter_authority_note(bundle)
    assert validate_bundle(bundle) == []
    validity = prose_citation_validity(bundle)
    assert validity["all_resolved"] is True


# --------------------------------------------------------------------------- #
# 4. shipped offline path exhibits both writers
# --------------------------------------------------------------------------- #

def test_shipped_offline_slice_emits_sourced_answer_and_counter_note():
    from offline_slice import build_bundle

    bundle = build_bundle("rent-default", top_n=100)
    prov = bundle.get("provenance") or {}
    src = prov.get("answer_fixture_source") or {}
    note = prov.get("answer_counter_note") or {}
    prose = str((bundle.get("answer") or {}).get("prose") or "")

    assert src.get("applied") is True, "offline answer must carry verbatim sourced passages"
    assert src.get("n_quotes", 0) >= 1
    assert note.get("applied") is True, "offline answer must mention counter-authorities"
    assert note.get("n_counter_rows", 0) >= 1
    assert len(prose) > len(str(src.get("header_preserved") or "")), \
        "answer must be more than two bare bracketed identifiers"
    cited = set(src.get("quoted_ids") or [])
    assert cited <= {d["decision_id"] for d in bundle["decisions"]}
    assert prose_citation_validity(bundle)["all_resolved"] is True
    assert validate_bundle(bundle) == []


def test_offline_sourced_quotes_are_verbatim_in_the_cited_row():
    import re

    from offline_slice import build_bundle
    from product.query.answer_contract import _clean, norm

    bundle = build_bundle("rent-default", top_n=60)
    by_id = {d["decision_id"]: d for d in bundle["decisions"]}
    prose = str((bundle.get("answer") or {}).get("prose") or "")
    quoted = ((bundle.get("provenance") or {}).get("answer_fixture_source") or {}).get("quoted_ids") or []
    assert quoted, "the offline answer must actually quote cited decisions"
    for did in quoted:
        row = by_id[did]
        match = re.search(r"^«\s+(.*?)\s+»\s+\[" + re.escape(did) + r"\]",
                          prose, flags=re.MULTILINE)
        assert match, f"no attributed verbatim passage for {did}"
        needle = norm(_clean(match.group(1)))[:60]
        assert needle
        assert any(needle in norm(_clean(row.get(field))) for field in
                   ("full_text", "regeste", "snippet", "title")), \
            f"quote attributed to {did} is not verbatim in that decision"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
