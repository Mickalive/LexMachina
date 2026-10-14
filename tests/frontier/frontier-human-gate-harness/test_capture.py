"""Acceptance (4) + (6): the session capture record."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from _bootstrap import load_fixture

from frontier_human_gate_harness.bundle_io import bundle_sha256
from frontier_human_gate_harness.capture import (ANSWER_KEYS, QUESTION_IDS,
                                                 RECORD_KEYS, CaptureError,
                                                 MissingAnswerError, empty_capture,
                                                 finalize, merge_drafts,
                                                 personal_data_errors,
                                                 read_draft, record_bytes,
                                                 session_filename, validate_record,
                                                 write_session)

FROM = "2026-10-14T10:00:00Z"
TO = "2026-10-14T10:03:30Z"


def draft(*, session_id="s-1", answers=None, query="Kündigung Mietvertrag",
          n=3, started=FROM, ended=TO, source="switch", view_initial="map",
          view_final="list", actions=None, decisions=None, counters=None,
          bundle=None):
    """A minimal structurally valid draft, as the demo page exports it."""
    answers = answers if answers is not None else {}
    if bundle is not None:
        query = bundle.get("query")
        n = len(bundle.get("decisions") or [])
    missing = [qid for qid in QUESTION_IDS if qid not in answers]
    return {
        "schema_version": "1.0", "record_type": "lex_human_gate_session",
        "team_id": "frontier-human-gate-harness", "charter_version": 1,
        "session_id": session_id, "session_id_origin": "draft", "status": "draft",
        "source": source, "query": query,
        "bundle_ref": {"query": query, "n_decisions": n},
        "bundle_sha256": None, "bundle_hash_status": "not_verified",
        "started_at": started, "ended_at": ended,
        "wall_clock_seconds": 210.0,
        "view_mode_initial": view_initial, "view_mode_final": view_final,
        "actions": actions if actions is not None else
                   [{"at": FROM, "view_mode": "map", "event": "switch", "ref": None}],
        "decisions_opened": decisions if decisions is not None else [],
        "counter_authorities_opened": counters if counters is not None else [],
        "answers": answers, "missing_answers": missing,
        "latency": {"baseline_render_ms": None, "session_wall_clock_seconds": 210.0},
    }


def complete_answers(now=TO):
    return {
        qid: {"scale": 4, "text": f"texte {qid}", "answered_at": now}
        for qid in QUESTION_IDS
    }


class try_raise:
    """Minimal context manager asserting an exception type (no pytest needed)."""

    def __init__(self, exc_type):
        self.exc_type = exc_type
        self.value = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            raise AssertionError(f"expected {self.exc_type.__name__} was not raised")
        if not issubclass(exc_type, self.exc_type):
            return False
        self.value = exc
        return True


def test_record_schema_is_a_closed_key_set():
    d = draft()
    assert list(d.keys()) == RECORD_KEYS
    assert validate_record(d) == []
    d["extra_key"] = 1
    assert any("unknown key" in e for e in validate_record(d))
    assert personal_data_errors(d) == []


def test_rejects_missing_answer_instead_of_inventing_one():
    d = draft(answers={"q1": {"scale": 4, "text": "ok", "answered_at": FROM}})
    with try_raise(MissingAnswerError) as ctx:
        finalize([d], session_id="s-1", now=TO)
    assert ctx.value.missing == ["q2", "q3", "q4"]
    assert ctx.value.answered == ["q1"]
    # ...and the default record really is incomplete-by-choice, not complete
    with try_raise(MissingAnswerError):
        finalize([draft()], now=TO)


def test_allow_incomplete_is_explicitly_labelled_not_silent():
    record = finalize([draft(answers={"q1": complete_answers()["q1"]})],
                      session_id="s-1", allow_incomplete=True, now=TO)
    assert record["status"] == "incomplete"
    assert record["missing_answers"] == ["q2", "q3", "q4"]
    assert "q1" in record["answers"] and set(record["answers"]) == {"q1"}
    assert validate_record(record) == []



def test_complete_record_carries_the_four_required_elements():
    bundle = load_fixture()
    record = finalize([draft(answers=complete_answers(), bundle=bundle)],
                      bundle=bundle, now=TO)
    assert record["session_id"] == "s-1" and record["session_id_origin"] == "draft"
    assert record["status"] == "complete"
    assert record["missing_answers"] == []
    assert record["bundle_sha256"] == bundle_sha256(bundle)
    assert record["bundle_hash_status"] == "computed"
    assert record["bundle_ref"]["query"] == bundle["query"]
    assert record["bundle_ref"]["n_decisions"] == len(bundle["decisions"])
    assert record["wall_clock_seconds"] == 210.0
    assert record["latency"]["session_wall_clock_seconds"] == 210.0
    assert record["view_mode_initial"] == "map" and record["view_mode_final"] == "list"
    assert record["decisions_opened"] == [] and record["counter_authorities_opened"] == []
    assert record["actions"][0]["view_mode"] == "map"
    assert record["answers"]["q1"]["scale"] == 4
    assert record["answers"]["q1"]["answered_at"] == TO
    assert validate_record(record) == []


def test_silent_default_missing_answers_is_rejected():
    d = draft(answers=complete_answers())
    d["missing_answers"] = ["q2"]  # pretend q2 is unanswered while answers say otherwise
    assert any("silent defaults" in e or "missing_answers must be exactly" in e
               for e in validate_record(d))
    d2 = draft(answers=complete_answers())
    del d2["answers"]["q4"]
    d2["missing_answers"] = []   # claims everything answered while q4 is absent
    assert any("missing_answers must be exactly" in e for e in validate_record(d2))
    # empty answer text+scale counts as unanswered
    d3 = draft(answers=complete_answers())
    d3["answers"]["q4"] = {"scale": None, "text": "   ", "answered_at": TO}
    d3["missing_answers"] = ["q4"]
    assert any("empty" in e for e in validate_record(d3))
    # out-of-range scale is rejected
    d4 = draft(answers=complete_answers())
    d4["answers"]["q1"]["scale"] = 9
    assert any("1..5" in e for e in validate_record(d4))
    for bad in ("name", "email", "user"):
        d5 = draft(answers=complete_answers())
        d5[bad] = "x"
        assert any(bad in e for e in validate_record(d5))


def test_merge_conflicts_are_refused_not_guessed():
    a = draft(answers=complete_answers())
    b = draft(answers=complete_answers(), session_id="s-2")
    with try_raise(CaptureError):
        merge_drafts([a, b])
    c = draft(answers=complete_answers(), query="andere Anfrage")
    with try_raise(CaptureError):
        merge_drafts([a, c])
    conflicting = json.loads(json.dumps(complete_answers()))
    conflicting["q1"] = {"scale": 1, "text": "anders", "answered_at": TO}
    with try_raise(CaptureError):
        merge_drafts([draft(answers=complete_answers()),
                      draft(answers=conflicting)])
    with try_raise(CaptureError):
        merge_drafts([])
    # a session id cannot be invented for you
    with try_raise(CaptureError):
        merge_drafts([{**draft(answers=complete_answers(), session_id=None)}])


def test_merge_unions_actions_and_opened_lists_order_preserving():
    d1 = draft(answers=complete_answers(),
               actions=[{"at": FROM, "view_mode": "map", "event": "switch", "ref": None}],
               decisions=["d1", "d2"], counters=["c1"])
    d2 = draft(answers=complete_answers(), source="card",
               actions=[{"at": TO, "view_mode": "list", "event": "open_decision",
                         "ref": "d2"}],
               decisions=["d2", "d3"], counters=["c2"])
    record = merge_drafts([d1, d2])
    assert record["source"] == "switch+card"
    assert [a["event"] for a in record["actions"]] == ["switch", "open_decision"]
    assert record["decisions_opened"] == ["d1", "d2", "d3"]
    assert record["counter_authorities_opened"] == ["c1", "c2"]
    assert validate_record(record) == []


def test_empty_capture_is_deterministic_and_never_fabricated():
    bundle = load_fixture()
    a = empty_capture(bundle, now=FROM)
    b = empty_capture(bundle, now=FROM)
    assert record_bytes(a) == record_bytes(b)
    assert a["status"] == "empty"
    assert a["answers"] == {} and a["missing_answers"] == list(QUESTION_IDS)
    assert a["bundle_sha256"] == bundle_sha256(bundle)
    assert a["bundle_hash_status"] == "computed"
    assert a["session_id_origin"] == "derived_from_bundle_sha256"
    assert a["started_at"] is None and a["wall_clock_seconds"] is None
    assert validate_record(a) == []
    c = empty_capture(None, session_id="manual", now=FROM)
    assert c["session_id_origin"] == "cli_flag"
    assert c["bundle_hash_status"] == "not_verified" and c["bundle_sha256"] is None
    assert validate_record(c) == []


def test_write_session_names_and_roundtrip():
    bundle = load_fixture()
    record = finalize([draft(answers=complete_answers(), bundle=bundle)],
                      bundle=bundle, now=TO)
    name = session_filename(record)
    assert name.startswith("session_") and name.endswith(".json")
    assert "s-1" in name and "/" not in name and " " not in name
    with TemporaryDirectory() as tmp:
        path = write_session(record, tmp)
        assert path.name == name
        assert path.parent == Path(tmp)
        again = read_draft(path)
        assert record_bytes(again) == record_bytes(record)
        assert validate_record(again) == []


def test_answer_key_contract_never_widens():
    assert ANSWER_KEYS == {"scale", "text", "answered_at"}
    assert len(QUESTION_IDS) == 4

