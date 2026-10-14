"""Acceptance (5) + (6): the one-command offline path and its exit codes."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from _bootstrap import HARNESS_ROOT, PACKAGE_ROOT, FIXTURE_PATH

from frontier_human_gate_harness.capture import QUESTION_IDS
from frontier_human_gate_harness.cli import EXIT_BUNDLE_FIELD, EXIT_CAPTURE, EXIT_OK, EXIT_USAGE, main


def run_cli(*args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(HARNESS_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run([sys.executable, "-m", "frontier_human_gate_harness.cli", *args],
                          capture_output=True, text=True, cwd=str(HARNESS_ROOT),
                          env=env, timeout=180)


def test_one_command_offline_path_writes_everything():
    with TemporaryDirectory() as tmp:
        out = Path(tmp) / "out"
        proc = run_cli("--fixture", str(FIXTURE_PATH), "--out", str(out),
                       "--now", "2026-10-14T00:00:00Z")
        assert proc.returncode == EXIT_OK, proc.stdout + proc.stderr
        payload = json.loads(proc.stdout)
        assert payload["ok"] is True and payload["mode"] == "fixture"
        expected = ["baseline_view.html", "owner_card_fr.html", "owner_card_de.html",
                    "owner_card.json", "harness_demo.html", "summary.json"]
        for name in expected:
            assert (out / name).is_file(), f"missing output: {name}"
        sessions = list(out.glob("session_*.json"))
        assert len(sessions) == 1, sessions
        assert sessions[0].name.startswith("session_") and sessions[0].name.endswith(".json")

        summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
        assert summary["offline"] is True
        assert summary["n_decisions"] >= 100
        assert len(summary["bundle_sha256"]) == 64
        assert summary["capture"]["missing_answers"] == list(QUESTION_IDS)

        session = json.loads(sessions[0].read_text(encoding="utf-8"))
        assert session["status"] == "empty"
        assert session["answers"] == {}
        assert session["missing_answers"] == list(QUESTION_IDS)
        assert session["bundle_hash_status"] == "computed"

        baseline = (out / "baseline_view.html").read_text(encoding="utf-8")
        assert "baseline" in baseline.lower()
        assert "cluster" not in baseline.lower()

        card_fr = (out / "owner_card_fr.html").read_text(encoding="utf-8")
        card_de = (out / "owner_card_de.html").read_text(encoding="utf-8")
        assert len(card_fr) > 1000 and len(card_de) > 1000


def test_missing_conventional_field_is_reported_not_invented():
    bundle = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    bundle["decisions"] = [dict(bundle["decisions"][0])]
    bundle["decisions"][0].pop("citation", None)
    with TemporaryDirectory() as tmp:
        fixture = Path(tmp) / "broken.json"
        fixture.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
        out = Path(tmp) / "out"
        proc = run_cli("--fixture", str(fixture), "--out", str(out))
        assert proc.returncode == EXIT_BUNDLE_FIELD, proc.stdout + proc.stderr
        assert "citation" in proc.stderr, "the missing field must be named in the message"
        assert not (out / "baseline_view.html").exists(), \
            "TERMINATE rule: no output may be written once the contract is broken"


def test_finalize_rejects_missing_answer_then_accepts_labelled_incomplete():
    draft = {
        "schema_version": "1.0", "record_type": "lex_human_gate_session",
        "team_id": "frontier-human-gate-harness", "charter_version": 1,
        "session_id": "owner-7", "session_id_origin": "draft", "status": "draft",
        "source": "demo", "query": "Kündigung Mietvertrag Mietrecht",
        "bundle_ref": {"query": "Kündigung Mietvertrag Mietrecht", "n_decisions": 100},
        "bundle_sha256": None, "bundle_hash_status": "not_verified",
        "started_at": "2026-10-14T10:00:00Z", "ended_at": "2026-10-14T10:05:00Z",
        "wall_clock_seconds": 300.0,
        "view_mode_initial": "map", "view_mode_final": "list",
        "actions": [{"at": "2026-10-14T10:00:00Z", "view_mode": "map",
                     "event": "switch", "ref": None}],
        "decisions_opened": ["d1"], "counter_authorities_opened": [],
        "answers": {"q1": {"scale": 3, "text": "partielle", "answered_at": "2026-10-14T10:04:00Z"}},
        "missing_answers": ["q2", "q3", "q4"],
        "latency": {"baseline_render_ms": None, "session_wall_clock_seconds": 300.0},
    }
    with TemporaryDirectory() as tmp:
        draft_path = Path(tmp) / "draft.json"
        draft_path.write_text(json.dumps(draft, ensure_ascii=False), encoding="utf-8")

        # 1. a missing answer is REJECTED (exit 2) and nothing is written
        out = Path(tmp) / "sessions"
        proc = run_cli("--finalize", str(draft_path), "--out", str(out))
        assert proc.returncode == EXIT_CAPTURE, proc.stdout + proc.stderr
        assert "q2" in proc.stderr and "q3" in proc.stderr and "q4" in proc.stderr
        assert not out.exists() or not list(out.glob("session_*.json")), \
            "a rejected capture must not leave a file behind"

        # 2. ...unless the owner explicitly asks for an incomplete record
        proc = run_cli("--finalize", str(draft_path), "--out", str(out),
                       "--allow-incomplete", "--fixture", str(FIXTURE_PATH),
                       "--now", "2026-10-14T10:06:00Z")
        assert proc.returncode == EXIT_OK, proc.stdout + proc.stderr
        # fixture mode also writes its own empty capture into the same --out
        target = out / "session_owner-7.json"
        assert target.is_file(), sorted(x.name for x in out.glob("session_*.json"))
        record = json.loads(target.read_text(encoding="utf-8"))
        assert record["status"] == "incomplete"
        assert record["missing_answers"] == ["q2", "q3", "q4"]
        assert sorted(record["answers"]) == ["q1"]
        assert record["bundle_hash_status"] == "computed"
        assert len(record["bundle_sha256"]) == 64
        empty_siblings = [x.name for x in out.glob("session_*.json")
                          if x.name != "session_owner-7.json"]
        assert empty_siblings and all(n.startswith("session_empty_") for n in empty_siblings), \
            "fixture mode should also have written its explicitly empty capture"

        # 3. all four answers -> complete record
        full = dict(draft)
        full["answers"] = {qid: {"scale": 4, "text": "ok",
                                 "answered_at": "2026-10-14T10:04:00Z"}
                           for qid in QUESTION_IDS}
        full["missing_answers"] = []
        full_path = Path(tmp) / "full.json"
        full_path.write_text(json.dumps(full, ensure_ascii=False), encoding="utf-8")
        out2 = Path(tmp) / "sessions2"
        proc = run_cli("--finalize", str(full_path), "--out", str(out2),
                       "--fixture", str(FIXTURE_PATH), "--now", "2026-10-14T10:06:00Z")
        assert proc.returncode == EXIT_OK, proc.stdout + proc.stderr
        record2 = json.loads((out2 / "session_owner-7.json").read_text(encoding="utf-8"))
        assert record2["status"] == "complete"
        assert record2["missing_answers"] == []
        assert record2["wall_clock_seconds"] == 300.0
        assert record2["decisions_opened"] == ["d1"]


def test_usage_errors_return_exit_4():
    with TemporaryDirectory() as tmp:
        assert run_cli("--out", tmp).returncode == EXIT_USAGE
        assert run_cli("--fixture", str(FIXTURE_PATH)).returncode == EXIT_USAGE
        assert run_cli().returncode == EXIT_USAGE


def test_package_contains_no_network_capability():
    allowed_socket = {"cli.py"}  # cli imports socket only to BLOCK connections
    for path in sorted(PACKAGE_ROOT.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for token in ("import urllib", "from urllib", "import requests", "import httpx",
                      "import aiohttp", "from http.client", "import ftplib", "import smtplib",
                      "urlopen("):
            assert token not in text, f"{path.name} contains {token!r}"
        if "import socket" in text and path.name not in allowed_socket:
            raise AssertionError(f"{path.name} imports socket outside the offline guard")
    js = (PACKAGE_ROOT.parent / "static" / "lex_gate_switch.js").read_text(encoding="utf-8")
    assert "socket" not in js and "XMLHttpRequest" not in js


def test_offline_guard_blocks_real_connections_and_restores_state():
    import socket

    from frontier_human_gate_harness.cli import NetworkDisabled, offline_only

    original_getaddrinfo = socket.getaddrinfo
    original_create_connection = socket.create_connection

    guard = offline_only()
    guard.__enter__()
    try:
        assert socket.getaddrinfo is not original_getaddrinfo, "guard not installed"
        try:
            socket.create_connection(("127.0.0.1", 9), timeout=1)
            raise AssertionError("the offline guard allowed a connection attempt")
        except NetworkDisabled:
            pass
    finally:
        guard.__exit__(None, None, None)

    assert socket.getaddrinfo is original_getaddrinfo, "guard left socket state modified"
    assert socket.create_connection is original_create_connection


def test_cli_main_runs_in_process_without_network():
    with TemporaryDirectory() as tmp:
        code = main(["--fixture", str(FIXTURE_PATH), "--out", str(Path(tmp) / "o"),
                     "--quiet", "--no-demo", "--now", "2026-10-14T00:00:00Z"])
        assert code == EXIT_OK
        assert (Path(tmp) / "o" / "summary.json").is_file()


def test_no_output_directory_without_hash_leak():
    """A draft with no bundle hash must not claim one (no fabricated hash)."""
    with TemporaryDirectory() as tmp:
        out = Path(tmp) / "o"
        code = main(["--fixture", str(FIXTURE_PATH), "--out", str(out),
                     "--quiet", "--no-demo", "--now", "2026-10-14T00:00:00Z"])
        assert code == EXIT_OK
        record = json.loads(next(out.glob("session_*.json")).read_text(encoding="utf-8"))
        assert re.fullmatch(r"[0-9a-f]{64}", record["bundle_sha256"])
        from frontier_human_gate_harness.bundle_io import bundle_sha256

        expected = bundle_sha256(json.loads(FIXTURE_PATH.read_text(encoding="utf-8")))
        assert record["bundle_sha256"] == expected, \
            "the recorded hash must be the real bundle hash, not a placeholder"
        assert record["bundle_hash_status"] == "computed"
        assert record["missing_answers"] == list(QUESTION_IDS)
