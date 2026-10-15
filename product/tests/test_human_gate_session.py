"""Tests for the one-command human-gate runner (product/human_gate_session.py).

The runner exists to make the last product milestone a single owner action:
start the product, use map <-> list, press export. These tests freeze the part
that is mechanical — the draft watcher, the automatic bundle binding, the write
and the admissibility verdict — and they keep the honesty properties: the runner
never sets the human gate, never answers a question, and never records a session
it cannot bind to a real bundle.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PRODUCT_ROOT.parent
if str(PRODUCT_ROOT) not in sys.path:
    sys.path.insert(0, str(PRODUCT_ROOT))

import human_gate_finalize as hgf  # noqa: E402
import human_gate_session as runner  # noqa: E402

QUERY = "Kündigung Mietvertrag Mietrecht"
COUNTER_ID = "SR 123/2020"
PLAIN_ID = "SR 999/2020"


def make_bundle(n: int = 120) -> dict:
    decisions = [
        {"decision_id": COUNTER_ID, "counter_status": "candidate-limiting", "citation": COUNTER_ID},
        {"decision_id": PLAIN_ID, "counter_status": "none", "citation": PLAIN_ID},
    ]
    decisions += [
        {"decision_id": f"SR {500 + i}/2022", "counter_status": "none", "canonical_url": f"https://x/{i}"}
        for i in range(n - 2)
    ]
    return {"query": QUERY, "decisions": decisions, "clusters": [], "relations": [], "provenance": {"mode": "fixture"}}


def make_draft(session_id: str | None = "owner-session-2026-10-20T120000Z", answers: bool = True) -> dict:
    started, ended = "2026-10-20T12:00:00.000Z", "2026-10-20T12:11:30.000Z"
    draft = {
        "schema_version": "1.0",
        "record_type": "lex_human_gate_session",
        "team_id": "frontier-human-gate-harness",
        "session_id": session_id,
        "status": "draft",
        "source": "switch",
        "query": QUERY,
        "bundle_ref": {"query": QUERY, "n_decisions": 120},
        "bundle_sha256": None,
        "bundle_hash_status": "not_verified",
        "started_at": started,
        "ended_at": ended,
        "view_mode_initial": "map",
        "view_mode_final": "list",
        "actions": [
            {"at": started, "view_mode": "map", "event": "switch_view", "ref": None},
            {"at": "2026-10-20T12:03:00.000Z", "view_mode": "list", "event": "open_decision", "ref": PLAIN_ID},
            {"at": "2026-10-20T12:06:00.000Z", "view_mode": "list", "event": "open_counter", "ref": COUNTER_ID},
        ],
        "decisions_opened": [PLAIN_ID],
        "counter_authorities_opened": [COUNTER_ID],
        "answers": {q: {"rating": "yes", "note": "the exception branch was visible only on the map"} for q in ("q1", "q2", "q3", "q4")} if answers else {},
        "missing_answers": [] if answers else ["q1", "q2", "q3", "q4"],
        "latency": {"baseline_render_ms": 412, "session_wall_clock_seconds": None},
    }
    return draft


def _has_gate_key(node) -> bool:
    if isinstance(node, dict):
        return "human_gate_ready" in node or any(_has_gate_key(v) for v in node.values())
    if isinstance(node, list):
        return any(_has_gate_key(item) for item in node)
    return False


def write_draft(directory: Path, draft: dict, name: str = "owner-session-2026-10-20T120000Z.json") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(json.dumps(draft, indent=2), encoding="utf-8")
    return path


# --------------------------------------------------------------------------
# the owner card
# --------------------------------------------------------------------------


def test_owner_card_contains_every_gate_question_and_the_url() -> None:
    card = runner.owner_card("http://127.0.0.1:8791")
    for question in hgf.GATE_QUESTIONS.values():
        assert question in card
    assert "http://127.0.0.1:8791" in card
    assert "human_gate_ready is set by the director" in card
    assert "A \"no\" on any question is a valid" in card, "the negative-result case must be visible to the owner"


# --------------------------------------------------------------------------
# draft watching
# --------------------------------------------------------------------------


def test_find_draft_picks_the_newest_export_and_ignores_older_files(tmp_path: Path) -> None:
    old = write_draft(tmp_path, make_draft(), name="lex_session_draft.json")
    new = write_draft(tmp_path, make_draft(session_id="owner-session-2"), name="owner-session-2.json")
    cutoff = time.time()
    time.sleep(0.01)

    assert runner.find_draft(tmp_path, since=cutoff) is None, "pre-existing files must not be picked up"

    fresh = write_draft(tmp_path, make_draft(session_id="owner-session-3"), name="owner-session-3.json")
    assert runner.find_draft(tmp_path, since=cutoff) == fresh
    assert old != new and new != fresh


def test_find_draft_returns_none_in_an_empty_directory(tmp_path: Path) -> None:
    assert runner.find_draft(tmp_path, since=time.time()) is None


# --------------------------------------------------------------------------
# bundle binding
# --------------------------------------------------------------------------


def test_bundle_is_bound_automatically_from_the_served_run(monkeypatch) -> None:
    import query_app

    bundle = make_bundle()
    other = make_bundle(60) | {"query": "Eine ganz andere Frage"}
    monkeypatch.setattr(
        query_app,
        "RUNS",
        {
            "run-old": {"query": QUERY, "bundle": other, "created_at": "2026-10-20T11:00:00"},
            "run-new": {"query": QUERY, "bundle": bundle, "created_at": "2026-10-20T12:00:00"},
            "run-other": {"query": "etwas anderes", "bundle": other, "created_at": "2026-10-20T12:30:00"},
        },
        raising=False,
    )
    monkeypatch.setattr(query_app, "RUNS_LOCK", __import__("threading").Lock(), raising=False)

    resolved, source = runner.resolve_live_bundle(make_draft())
    assert source == "server_run"
    assert resolved is not None and resolved["query"] == QUERY
    assert len(resolved["decisions"]) == 120


def test_bundle_binding_reports_no_match_instead_of_guessing(monkeypatch) -> None:
    import query_app

    monkeypatch.setattr(query_app, "RUNS", {}, raising=False)
    monkeypatch.setattr(query_app, "RUNS_LOCK", __import__("threading").Lock(), raising=False)
    resolved, source = runner.resolve_live_bundle(make_draft())
    assert resolved is None and source == "no_matching_run"


# --------------------------------------------------------------------------
# finalize + verdict
# --------------------------------------------------------------------------


def test_finish_finalizes_into_the_canonical_directory_and_reports_admissible(tmp_path: Path, capsys) -> None:
    draft_path = write_draft(tmp_path, make_draft())
    out = tmp_path / "sessions"
    code = runner.finish(draft_path, run_id="38732097101", operator="owner", bundle=make_bundle(), out_dir=out)
    assert code == 0, capsys.readouterr().out
    written = list(out.glob("session_*.json"))
    assert len(written) == 1
    record = json.loads(written[0].read_text(encoding="utf-8"))
    assert record["status"] == "finalized"
    assert record["simulated"] is False
    assert record["run_id"] == "38732097101"
    assert record["finalized_by"] == "owner"
    assert record["bundle_hash_status"] == "verified"
    assert not _has_gate_key(record), "the record must never carry a human_gate_ready field"
    printed = capsys.readouterr().out
    assert "human_gate_ready is NOT set" in printed
    assert "ADMISSIBLE" in printed


def test_finish_records_an_incomplete_session_without_pretending(tmp_path: Path, capsys) -> None:
    draft_path = write_draft(tmp_path, make_draft(answers=False))
    out = tmp_path / "sessions"
    code = runner.finish(draft_path, run_id="38732097101", operator="owner", bundle=make_bundle(), out_dir=out)
    assert code == 3
    record = json.loads(next(out.glob("session_*.json")).read_text(encoding="utf-8"))
    assert record["status"] == "incomplete"
    assert record["missing_answers"] == ["q1", "q2", "q3", "q4"]
    assert "answers still required" in capsys.readouterr().out


def test_finish_refuses_a_session_it_cannot_bind_to_a_bundle(tmp_path: Path, capsys) -> None:
    """An unbindable session stays draft evidence instead of entering the tree."""
    draft_path = write_draft(tmp_path, make_draft())
    out = tmp_path / "sessions"
    code = runner.finish(draft_path, run_id="38732097101", operator="owner", bundle=None, out_dir=out)
    assert code == 7
    assert not out.exists() or not list(out.glob("*.json"))
    assert "bundle" in capsys.readouterr().err


def test_finish_refuses_a_session_bound_to_a_fixture_sized_bundle(tmp_path: Path) -> None:
    draft_path = write_draft(tmp_path, make_draft())
    out = tmp_path / "sessions"
    assert runner.finish(draft_path, run_id="38732097101", operator="owner", bundle=make_bundle(3), out_dir=out) == 7


def test_runner_never_writes_a_simulated_record(tmp_path: Path) -> None:
    draft_path = write_draft(tmp_path, make_draft())
    out = tmp_path / "sessions"
    runner.finish(draft_path, run_id="38732097101", operator="owner", bundle=make_bundle(), out_dir=out)
    written = json.loads(next(out.glob("session_*.json")).read_text(encoding="utf-8"))
    assert written["simulated"] is False
    assert written["claim_ceiling"] == hgf.CLAIM_CEILING_REAL


# --------------------------------------------------------------------------
# CLI surface
# --------------------------------------------------------------------------


def test_cli_check_subcommand_reports_the_repository_state() -> None:
    result = subprocess.run(
        [sys.executable, str(PRODUCT_ROOT / "human_gate_session.py"), "check"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=120, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ADMISSIBLE" in result.stdout


def test_cli_finalize_subcommand_runs_without_starting_a_server(tmp_path: Path) -> None:
    draft_path = write_draft(tmp_path, make_draft())
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(make_bundle()), encoding="utf-8")
    out = tmp_path / "sessions"
    result = subprocess.run(
        [
            sys.executable, str(PRODUCT_ROOT / "human_gate_session.py"), "finalize", str(draft_path),
            "--bundle", str(bundle_path), "--run-id", "38732097101", "--operator", "owner", "--out", str(out),
        ],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=120, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(next(out.glob("session_*.json")).read_text(encoding="utf-8"))["status"] == "finalized"


def test_cli_finalize_without_a_bundle_is_refused_with_exit_7(tmp_path: Path) -> None:
    draft_path = write_draft(tmp_path, make_draft())
    out = tmp_path / "sessions"
    result = subprocess.run(
        [
            sys.executable, str(PRODUCT_ROOT / "human_gate_session.py"), "finalize", str(draft_path),
            "--run-id", "38732097101", "--operator", "owner", "--out", str(out),
        ],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=120, check=False,
    )
    assert result.returncode == 7, result.stdout + result.stderr
    assert not out.exists() or not list(out.glob("*.json"))


def test_serve_returns_9_when_no_session_is_exported(tmp_path: Path) -> None:
    """A missed session is reported, not silently recorded as evidence."""
    assert runner.serve(host="127.0.0.1", port=0, fixture=True, watch_dir=tmp_path, wait_s=0.01, verbose=False) == 9


def test_serve_does_not_shut_down_the_process_global_job_pool(tmp_path: Path) -> None:
    """``serve()`` may only tear down what it created.

    Regression guard for audit CYCLE_38732097101 (repair round 3, required fix 1).
    ``serve()`` used to call ``POOL.shutdown()`` on the module-level
    ``query_app.POOL`` executor. Because that pool is process-global, one
    in-process ``serve()`` call permanently disabled background jobs: every later
    ``POOL.submit`` raised ``RuntimeError: cannot schedule new futures after
    shutdown`` and ``/api/query/start`` answered HTTP 500 in eight pre-existing
    server tests that happen to be collected after this module.

    Both halves are asserted here — the mechanism (the executor still accepts
    work) and the user-visible symptom (a fresh server still starts a query) —
    so re-introducing the shutdown line fails this test in isolation, not only
    through default-order cross-module pollution.
    """
    import json
    import threading
    import urllib.parse
    import urllib.request

    import query_app

    assert runner.serve(host="127.0.0.1", port=0, fixture=True, watch_dir=tmp_path, wait_s=0.01, verbose=False) == 9

    # mechanism: the shared executor must still accept submissions
    assert query_app.POOL.submit(lambda: "alive").result(timeout=15) == "alive"

    # symptom: a server started afterwards must still be able to run a query job
    srv = query_app.make_server("127.0.0.1", 0, fixture_mode=True, verbose=False)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        url = base + "/api/query/start?" + urllib.parse.urlencode({"q": QUERY, "n": 100})
        with urllib.request.urlopen(url, timeout=60) as resp:
            started = json.loads(resp.read())
        assert started["bundle"]["provenance"]["phase"] == "map_ready"
        assert len(started["bundle"]["decisions"]) > 0
    finally:
        srv.shutdown()
        srv.server_close()