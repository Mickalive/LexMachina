#!/usr/bin/env python3
"""Pins the accepted-ref fetch fallback of resume_snapshot_diagnosis.

Why this exists: core-lane repair rounds fetch only the team/audit refs
(`.github/workflows/core-lane.yml` "Validate lane and initialize accepted
base") and the accepted-peer mount skips the lane's own `lab/<lane>` branch,
so every repair-round diagnosis recorded ACCEPTED_REF_ABSENT even when
`lab/product` exists on the remote — measured on the committed 40692326715
diagnosis (accepted_head null) against real remote head 7be4480e. The
`--ensure-accepted-ref` opt-in performs a read-only remote-tracking fetch and
records its outcome; the default offline contract (never fetch) is unchanged.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from product import resume_snapshot_diagnosis as rsd  # noqa: E402


class _Proc:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_ensure_ref_skips_fetch_when_ref_present(monkeypatch):
    calls: list[tuple[str, ...]] = []

    def fake_git(*args):
        calls.append(args)
        return _Proc()

    monkeypatch.setattr(rsd, "_git", fake_git)
    monkeypatch.setattr(rsd, "_rev", lambda ref: "abc123" if ref == "origin/lab/product" else None)
    rec = rsd.ensure_accepted_ref()
    assert rec == {"attempted": False, "reason": "ref_already_present",
                   "accepted_head": "abc123"}
    assert calls == []  # never touches the network when the ref is local


def test_ensure_ref_fetches_remote_tracking_only(monkeypatch):
    calls: list[tuple[str, ...]] = []
    state = {"fetched": False}

    def fake_git(*args):
        calls.append(args)
        state["fetched"] = True
        return _Proc(returncode=0)

    def fake_rev(ref):
        if ref != "origin/lab/product":
            return None
        return "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83" if state["fetched"] else None

    monkeypatch.setattr(rsd, "_git", fake_git)
    monkeypatch.setattr(rsd, "_rev", fake_rev)
    rec = rsd.ensure_accepted_ref()
    assert rec["attempted"] is True
    assert rec["ok"] is True
    assert rec["method"] == "git-fetch-remote-tracking-only"
    assert rec["accepted_head"] == "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
    # the ONLY network command is the remote-tracking fetch; no branch switch,
    # no push, no local-branch write
    assert calls == [("fetch", "origin",
                      "lab/product:refs/remotes/origin/lab/product")]


def test_ensure_ref_records_failed_fetch_without_inventing_head(monkeypatch):
    def fake_git(*args):
        return _Proc(returncode=128, stderr="fatal: could not read from remote")

    monkeypatch.setattr(rsd, "_git", fake_git)
    monkeypatch.setattr(rsd, "_rev", lambda ref: None)
    rec = rsd.ensure_accepted_ref()
    assert rec["attempted"] is True
    assert rec["ok"] is False
    assert rec["fetch_returncode"] == 128
    assert rec["accepted_head"] is None
    assert rec["fetch_stderr_tail"] == ["fatal: could not read from remote"]


def test_accepted_head_relation_attaches_fetch_record_only_when_given():
    delta = {"snapshot_head": "876d1a82f70548a8b789b1ff23c5900029951b6f"}
    plain = rsd._accepted_head_relation(delta)
    assert "accepted_ref_fetch" not in plain  # historical byte shape preserved
    fetch = {"attempted": True, "ok": True,
             "accepted_head": "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"}
    with_fetch = rsd._accepted_head_relation(delta, fetch)
    assert with_fetch["accepted_ref_fetch"] == fetch


def test_run_default_does_not_attempt_fetch(monkeypatch):
    monkeypatch.setattr(rsd, "ensure_accepted_ref",
                        lambda: pytest.fail("run() must not fetch by default"))
    # the heavy instruments are stubbed: this test pins only the fetch contract
    monkeypatch.setattr(rsd, "_delta", lambda *a: {"snapshot_head": "x"})
    monkeypatch.setattr(rsd, "_accept_commit", lambda rid: {"accepted_ref_present": False,
                                                           "accept_commit": None})
    monkeypatch.setattr(rsd, "_audit_half", lambda rid: {"audit_ref_present": False,
                                                        "gate_verdict": None})
    monkeypatch.setattr(rsd, "_audit_namespace", lambda: {})
    monkeypatch.setattr(rsd, "_validation_findings", lambda a, b: {})
    monkeypatch.setattr(rsd, "_orchestration_without_raw", lambda p: {})
    rec = rsd.run("40000000000")
    assert "accepted_ref_fetch" not in rec["accepted_head_relation"]
