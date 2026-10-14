"""Tests for the human-gate session finalizer (direction v51 delta 1).

The accepted ``frontier-human-gate-harness`` switch exports a ``status: "draft"``
session whose bundle hashes are ``null`` and whose ``integrity`` is asserted by
nobody. These tests freeze what the finalizer must guarantee before a session is
allowed to become lane evidence:

* it never fabricates a gate answer (missing answers -> incomplete + exit 3);
* it never marks a session usable when the bundle it was run on is a different
  bundle, or when the session claims to have opened decisions that do not exist;
* it binds the record to the bundle digest, so a hand-edited draft is detectable;
* a negative session (the jurist answered "no") survives as valid evidence.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

PRODUCT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PRODUCT_ROOT.parent
if str(PRODUCT_ROOT) not in sys.path:
    sys.path.insert(0, str(PRODUCT_ROOT))

from human_gate_finalize import (  # noqa: E402
    GATE_QUESTIONS,
    IncompleteSession,
    FinalizeError,
    bundle_evidence,
    canonical_sha256,
    finalize,
    session_metrics,
    validate_draft,
    write_record,
)

COUNTER_ID = "SR 123/2020"
PLAIN_ID = "SR 999/2020"


def make_bundle(query: str = "Kündigung Mietvertrag Mietrecht") -> dict:
    return {
        "bundle_version": "query_result_bundle v1.0",
        "query": query,
        "decisions": [
            {"decision_id": COUNTER_ID, "counter_status": "candidate-limiting", "citation": "SR 123/2020"},
            {"decision_id": PLAIN_ID, "counter_status": "none", "citation": "SR 999/2020"},
        ],
        "clusters": [],
        "relations": [],
        "provenance": {},
    }


def make_draft(**overrides) -> dict:
    draft = {
        "schema_version": "1.0",
        "record_type": "lex_human_gate_session",
        "team_id": "frontier-human-gate-harness",
        "charter_version": 1,
        "session_id": None,
        "status": "draft",
        "source": "switch",
        "query": "Kündigung Mietvertrag Mietrecht",
        "bundle_ref": {"query": "Kündigung Mietvertrag Mietrecht", "n_decisions": 2},
        "bundle_sha256": None,
        "query_sha256": None,
        "bundle_hash_status": "not_verified",
        "started_at": "2026-10-14T20:00:00.000Z",
        "ended_at": "2026-10-14T20:07:30.000Z",
        "view_mode_initial": "map",
        "view_mode_final": "list",
        "actions": [
            {"at": "2026-10-14T20:00:01.000Z", "view_mode": "map", "event": "switch_view", "ref": None},
            {"at": "2026-10-14T20:01:00.000Z", "view_mode": "list", "event": "open_decision", "ref": PLAIN_ID},
            {"at": "2026-10-14T20:02:00.000Z", "view_mode": "list", "event": "open_counter", "ref": COUNTER_ID},
        ],
        "decisions_opened": [PLAIN_ID],
        "counter_authorities_opened": [COUNTER_ID],
        "answers": {},
        "missing_answers": list(GATE_QUESTIONS),
        "latency": {"baseline_render_ms": None, "session_wall_clock_seconds": None},
    }
    draft.update(overrides)
    return draft


def all_yes() -> dict:
    return {qid: {"rating": "yes", "note": ""} for qid in GATE_QUESTIONS}


# --------------------------------------------------------------------------
# draft validation
# --------------------------------------------------------------------------


def test_valid_draft_has_no_problems() -> None:
    assert validate_draft(make_draft()) == []


@pytest.mark.parametrize(
    "mutation, expected",
    [
        ({"record_type": "something_else"}, "record_type"),
        ({"team_id": "other-team"}, "team_id"),
        ({"actions": []}, "actions is empty"),
        ({"ended_at": "2026-10-14T19:00:00.000Z"}, "ended_at precedes started_at"),
        ({"started_at": None}, "started_at"),
        ({"decisions_opened": "SR-1"}, "decisions_opened must be a list"),
    ],
)
def test_invalid_drafts_are_rejected_with_a_reason(mutation, expected) -> None:
    problems = validate_draft(make_draft(**mutation))
    assert any(expected in problem for problem in problems), problems


def test_finalize_rejects_invalid_draft_with_exit_4() -> None:
    with pytest.raises(FinalizeError) as excinfo:
        finalize(make_draft(record_type="nope"), all_yes(), make_bundle())
    assert excinfo.value.exit_code == 4


# --------------------------------------------------------------------------
# the gate answers are never fabricated
# --------------------------------------------------------------------------


def test_missing_answers_yield_incomplete_evidence_and_exit_3() -> None:
    with pytest.raises(IncompleteSession) as excinfo:
        finalize(make_draft(), {"q1": "yes", "q2": "yes"}, make_bundle())
    assert excinfo.value.exit_code == 3
    assert excinfo.value.missing == ["q3", "q4"]
    record = excinfo.value.record
    assert record["status"] == "incomplete"
    assert set(record["answers"]) == {"q1", "q2"}


def test_no_answers_at_all_is_rejected() -> None:
    with pytest.raises(IncompleteSession) as excinfo:
        finalize(make_draft(), None, make_bundle())
    assert excinfo.value.missing == list(GATE_QUESTIONS)


def test_finalized_record_binds_to_the_bundle_digest() -> None:
    record = finalize(make_draft(), all_yes(), make_bundle())
    assert record["status"] == "finalized"
    assert record["bundle_hash_status"] == "verified"
    assert record["bundle_sha256"] == canonical_sha256(make_bundle())
    assert record["query_sha256"] == canonical_sha256("Kündigung Mietvertrag Mietrecht")
    assert record["missing_answers"] == []


def test_negative_session_is_valid_evidence() -> None:
    """The Master Prompt's 'if not, stop the standalone product' case must survive."""
    record = finalize(
        make_draft(),
        {qid: {"rating": "no", "note": "the map hid nothing I could not see in the list"} for qid in GATE_QUESTIONS},
        make_bundle(),
    )
    assert record["status"] == "finalized"
    assert all(record["answers"][q]["rating"] == "no" for q in GATE_QUESTIONS)


def test_free_text_answers_are_kept_verbatim() -> None:
    note = "FR 4A exception invisible in the ranked list"
    record = finalize(make_draft(), {**{q: "yes" for q in ("q1", "q2", "q4")}, "q3": note}, make_bundle())
    assert record["answers"]["q3"]["note"] == note
    assert record["answers"]["q3"]["rating"] == ""
    assert record["answers"]["q1"]["rating"] == "yes"


def test_answers_can_be_taken_from_the_draft_itself() -> None:
    draft = make_draft(answers={"q1": {"rating": "yes"}, "q2": "partly", "q3": "no", "q4": "mixed"})
    record = finalize(draft, None, make_bundle())
    assert record["status"] == "finalized"
    assert record["answers"]["q3"]["rating"] == "no"


def test_tool_never_claims_human_gate_ready() -> None:
    """No field may assert the gate is passed; the director decides from records."""
    record = finalize(make_draft(), all_yes(), make_bundle())
    assert "human_gate_ready" not in record
    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                assert key != "human_gate_ready"
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)
    walk(record)


# --------------------------------------------------------------------------
# integrity against the bundle
# --------------------------------------------------------------------------


def test_bundle_mismatch_on_query_is_refused_with_exit_5() -> None:
    with pytest.raises(FinalizeError) as excinfo:
        finalize(make_draft(), all_yes(), make_bundle("Eine ganz andere Frage"))
    assert excinfo.value.exit_code == 5
    assert "does not match" in str(excinfo.value)


def test_opened_decision_absent_from_the_bundle_is_refused() -> None:
    draft = make_draft(decisions_opened=[PLAIN_ID, "SR 000/1900"])
    with pytest.raises(FinalizeError) as excinfo:
        finalize(draft, all_yes(), make_bundle())
    assert excinfo.value.exit_code == 5
    assert "absent from the bundle" in str(excinfo.value)


def test_counter_opened_without_counter_status_is_refused() -> None:
    draft = make_draft(counter_authorities_opened=[PLAIN_ID])
    with pytest.raises(FinalizeError) as excinfo:
        finalize(draft, all_yes(), make_bundle())
    assert excinfo.value.exit_code == 5
    assert "without a counter status" in str(excinfo.value)


def test_draft_without_bundle_stays_unverified_evidence() -> None:
    record = finalize(make_draft(), all_yes(), None)
    assert record["bundle_hash_status"] == "not_verified"
    assert record["bundle_evidence"]["bundle_supplied"] is False


def test_bundle_evidence_counts_real_counter_openings() -> None:
    evidence = bundle_evidence(make_draft(), make_bundle())
    assert evidence["opened_in_bundle"] == 1
    assert evidence["counters_in_bundle"] == 1
    assert evidence["bundle_counter_count"] == 1
    assert evidence["integrity_problems"] == []


# --------------------------------------------------------------------------
# derived session metrics
# --------------------------------------------------------------------------


def test_session_metrics_count_baseline_use_and_wall_clock() -> None:
    metrics = session_metrics(make_draft())
    assert metrics["n_decisions_opened"] == 1
    assert metrics["n_counter_authorities_opened"] == 1
    assert metrics["used_conventional_baseline"] is True
    assert metrics["view_mode_initial"] == "map" and metrics["view_mode_final"] == "list"
    assert metrics["wall_clock_seconds"] == 450.0
    assert metrics["events"]["open_counter"] == 1


def test_session_metrics_tolerate_missing_timestamps() -> None:
    metrics = session_metrics(make_draft(started_at=None, ended_at=None))
    assert metrics["wall_clock_seconds"] is None


# --------------------------------------------------------------------------
# persistence + CLI
# --------------------------------------------------------------------------


def test_write_record_lands_in_results_product(tmp_path: Path) -> None:
    record = finalize(make_draft(), all_yes(), make_bundle(), run_id="38649613677")
    path = write_record(record, tmp_path)
    assert path.is_file()
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["run_id"] == "38649613677"
    assert stored["status"] == "finalized"


def test_cli_end_to_end(tmp_path: Path) -> None:
    draft_path = tmp_path / "draft.json"
    bundle_path = tmp_path / "bundle.json"
    answers_path = tmp_path / "answers.json"
    draft_path.write_text(json.dumps(make_draft()), encoding="utf-8")
    bundle_path.write_text(json.dumps(make_bundle()), encoding="utf-8")
    answers_path.write_text(json.dumps(all_yes()), encoding="utf-8")

    out_dir = tmp_path / "sessions"
    result = subprocess.run(
        [
            sys.executable, str(PRODUCT_ROOT / "human_gate_finalize.py"),
            "--draft", str(draft_path), "--bundle", str(bundle_path),
            "--answers", str(answers_path), "--out", str(out_dir), "--run-id", "38649613677",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "human_gate_ready is NOT set" in result.stdout
    written = list(out_dir.glob("session_*.json"))
    assert len(written) == 1
    assert json.loads(written[0].read_text(encoding="utf-8"))["status"] == "finalized"


def test_cli_exits_3_on_incomplete_session_but_still_records_it(tmp_path: Path) -> None:
    draft_path = tmp_path / "draft.json"
    bundle_path = tmp_path / "bundle.json"
    draft_path.write_text(json.dumps(make_draft()), encoding="utf-8")
    bundle_path.write_text(json.dumps(make_bundle()), encoding="utf-8")
    out_dir = tmp_path / "sessions"
    result = subprocess.run(
        [
            sys.executable, str(PRODUCT_ROOT / "human_gate_finalize.py"),
            "--draft", str(draft_path), "--bundle", str(bundle_path), "--out", str(out_dir),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 3, result.stdout + result.stderr
    written = list(out_dir.glob("session_*.json"))
    assert len(written) == 1
    assert json.loads(written[0].read_text(encoding="utf-8"))["status"] == "incomplete"