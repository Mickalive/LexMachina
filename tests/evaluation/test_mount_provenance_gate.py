"""Tests for evaluation/mount_provenance_gate.py.

Pins the two-verdict separation (measurements vs provenance) so a future edit
cannot collapse them into one convenient "it reproduces" claim.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from evaluation import mount_provenance_gate as mpg  # noqa: E402
from evaluation.mount_provenance_gate import (  # noqa: E402
    CLAIM_CEILING, PROVENANCE_SOURCES, check_pins, check_provenance,
    commit_facts, generations_behind, run,
)

RECORD = REPO_ROOT / "results" / "evaluation" / "mount_provenance_gate" / "39231573047.json"
FREEZE = REPO_ROOT / "evaluation" / "MAPPING_FREE_RECALL_FALSIFIER_FREEZE_RECORD.json"


def test_provenance_sources_are_all_reachable_or_absent_not_silent():
    """Coverage must be explicit: every source is either read or reported ABSENT."""
    for rel, pointer in PROVENANCE_SOURCES:
        assert rel.startswith(("evaluation/", "results/", "state/", "reports/")), rel
        assert pointer


def test_commit_facts_rejects_non_sha():
    assert commit_facts("nope")["resolvable"] is False
    assert commit_facts("")["resolvable"] is False


def test_generations_behind_identical_is_zero():
    head = mpg.live_mount_head(Path("/tmp/lex_accepted/product"))
    if head:
        assert generations_behind(head, head) == 0


def test_check_pins_counts_drift_and_missing(tmp_path):
    (tmp_path / "a.txt").write_text("hello")
    (tmp_path / "b.txt").write_text("world")
    import hashlib
    pins = {
        "mount": "/somewhere", "mount_head_at_freeze": "x" * 40,
        "a.txt": hashlib.sha256(b"hello").hexdigest(),
        "b.txt": "0" * 64,
        "c.txt": "0" * 64,
    }
    out = check_pins(tmp_path, pins)
    assert out["n_pins"] == 3
    assert out["n_match"] == 1
    assert out["n_drift"] == 1
    assert out["n_missing"] == 1
    assert out["verdict"] == "PIN_VERDICT_BROKEN"


def test_check_pins_all_match_is_verified(tmp_path):
    import hashlib
    (tmp_path / "a.txt").write_text("hello")
    out = check_pins(tmp_path, {"a.txt": hashlib.sha256(b"hello").hexdigest()})
    assert out["verdict"] == "PIN_VERDICT_VERIFIED"
    assert out["n_drift"] == 0


def test_check_provenance_flags_mismatch():
    """A recorded head that is not the live head must NOT re-derive."""
    rows = check_provenance(Path("/tmp/lex_accepted/product"), "0" * 40)
    assert rows["verdict"] == "PROVENANCE_UNREPRODUCIBLE"
    assert rows["n_do_not_re_derive"] >= 1


def test_check_provenance_all_match_is_verified(tmp_path, monkeypatch):
    """All recorded heads equal to the live head => VERIFIED.

    Uses a temporary source file recording the LIVE head, so this asserts the
    verdict LOGIC and is not entangled with which heads the committed tree
    happens to carry today.
    """
    live = mpg.live_mount_head(Path("/tmp/lex_accepted/product"))
    if not live:
        pytest.skip("accepted product mount absent in this environment")
    rel = "results/evaluation/_tmp_mpg_fixture.json"
    target = REPO_ROOT / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"product_mount_head": live}))
    try:
        monkeypatch.setattr(mpg, "PROVENANCE_SOURCES", ((rel, "product_mount_head"),))
        rows = check_provenance(Path("/tmp/lex_accepted/product"), live)
        assert rows["n_do_not_re_derive"] == 0
        assert rows["verdict"] == "PROVENANCE_VERIFIED"
    finally:
        target.unlink(missing_ok=True)


def test_check_provenance_on_the_committed_tree_does_not_re_derive():
    """The committed tree's recorded head differs from the live mount head.

    This is the finding of record for run 39231573047, asserted rather than
    described, so a later edit that silently 'fixes' the record is visible.
    """
    rows = check_provenance(Path("/tmp/lex_accepted/product"),
                            mpg.live_mount_head(Path("/tmp/lex_accepted/product")))
    assert rows["verdict"] == "PROVENANCE_UNREPRODUCIBLE"
    assert rows["n_do_not_re_derive"] == len(PROVENANCE_SOURCES)


@pytest.mark.skipif(not RECORD.exists(), reason="record of record not committed")
def test_committed_record_separates_the_two_verdicts():
    rec = json.loads(RECORD.read_text())
    assert rec["pin_verdict"]["n_match"] == rec["pin_verdict"]["n_pins"]
    assert rec["measurements_reproduce"] is True
    assert rec["provenance_reproduces"] is False
    assert rec["verdict"] == "PROVENANCE_UNREPRODUCIBLE"
    assert rec["exit_code"] == 1


@pytest.mark.skipif(not RECORD.exists(), reason="record of record not committed")
def test_committed_record_states_the_human_gate_is_closed():
    rec = json.loads(RECORD.read_text())
    for k in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
              "ready_for_owner_session", "owner_decision_required"):
        assert rec[k] is False, k


@pytest.mark.skipif(not RECORD.exists(), reason="record of record not committed")
def test_committed_record_is_read_only_over_frozen_inputs():
    rec = json.loads(RECORD.read_text())
    assert rec["read_only"] is True
    assert rec["freeze_record"]["path"] == "evaluation/MAPPING_FREE_RECALL_FALSIFIER_FREEZE_RECORD.json"
    assert rec["claim_ceiling"] == CLAIM_CEILING


def test_refusal_path_still_writes_a_record(tmp_path):
    """A refusal with no artifact is not re-derivable from the committed tree."""
    out = tmp_path / "absent.json"
    code, rec = run("t-absent", out, Path("/tmp/definitely-not-a-mount"))
    assert code == 2
    assert rec["verdict"] == "NOT_MEASURED"
    assert out.exists(), "refusal must still emit its record"
    assert json.loads(out.read_text())["verdict"] == "NOT_MEASURED"


def test_module_is_importable_without_the_mount():
    assert mpg.DEFAULT_MOUNT
    assert "does NOT" in CLAIM_CEILING