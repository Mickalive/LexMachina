"""Dedicated fail-closed tests for the scored-claim-movement adjudication.

Every test is load-bearing. The NON-VACUITY tests (N1, N2) prove the
adjudication can fail: the planted control must flip the frozen composite,
and the byte-identity guard must refuse a one-byte drift between the deeper
mount and the accepted mount. A wrapper that cannot fail is not an
adjudication.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

LANE = Path(__file__).resolve().parents[2]
if str(LANE) not in sys.path:
    sys.path.insert(0, str(LANE))

from evaluation import scored_claim_movement_adjudication as scma  # noqa: E402

HYP = LANE / scma.HYPOTHESIS_PATH


# --------------------------------------------------------------------------- #
# P1 frozen pins must match the committed files (a drift here is exit 2)
# --------------------------------------------------------------------------- #
def test_hypothesis_sha_matches_pinned_constant():
    got = hashlib.sha256(HYP.read_bytes()).hexdigest()
    assert got == scma.HYPOTHESIS_SHA256, (got, scma.HYPOTHESIS_SHA256)


def test_frozen_pin_files_match_pinned_constants():
    for rel, want in scma.FROZEN_PINS.items():
        p = LANE / rel
        assert p.is_file(), rel
        got = hashlib.sha256(p.read_bytes()).hexdigest()
        assert got == want, (rel, got, want)


def test_composite_literals_match_the_frozen_instrument_source():
    """If the frozen instrument's composite strings ever change, fail here."""
    src = (LANE / "evaluation/trigger_reconciliation.py").read_text(encoding="utf-8")
    for literal in (scma.COMPOSITE_MOVED, scma.COMPOSITE_NO_OP,
                    scma.COMPOSITE_NOT_MEASURED):
        assert literal in src, literal


# --------------------------------------------------------------------------- #
# U1 claim-population manifest covers gate_packet/** AND state/product.json
# --------------------------------------------------------------------------- #
def test_claim_population_manifest_covers_gate_packet_and_state(tmp_path):
    mount = tmp_path / "m"
    gp = mount / "results/product/gate_packet/1/questions"
    gp.mkdir(parents=True)
    (gp / "x.bundle.json").write_text('{"b":2}', encoding="utf-8")
    (mount / "results/product/gate_packet/1/packet.json").write_text(
        '{"a":1}', encoding="utf-8")
    (mount / "state").mkdir(parents=True)
    (mount / "state/product.json").write_text('{"c":3}', encoding="utf-8")
    # a file OUTSIDE the claim population must NOT appear
    (mount / "other.txt").write_text("zz", encoding="utf-8")

    man = scma.claim_population_manifest(mount)
    assert set(man) == {
        "results/product/gate_packet/1/packet.json",
        "results/product/gate_packet/1/questions/x.bundle.json",
        "state/product.json",
    }


# --------------------------------------------------------------------------- #
# N1 NON-VACUITY: mount identity must refuse a one-byte drift
# --------------------------------------------------------------------------- #
def _tiny_mount(tmp_path: Path, name: str, state_text: str = '{"c":3}') -> Path:
    mount = tmp_path / name
    gp = mount / "results/product/gate_packet/1"
    gp.mkdir(parents=True)
    (gp / "packet.json").write_text('{"a":1}', encoding="utf-8")
    (mount / "state").mkdir(parents=True)
    (mount / "state/product.json").write_text(state_text, encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(mount)], check=True)
    subprocess.run(["git", "-C", str(mount), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(mount), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-qm", "init"], check=True)
    return mount


def test_mount_identity_refuses_one_byte_drift(tmp_path):
    a = _tiny_mount(tmp_path, "accepted")
    d = _tiny_mount(tmp_path, "deeper")
    ident = scma.mount_identity(a, d)
    assert ident["identity_proven"] is True

    # one byte in the deeper mount's claim population -> NOT proven
    (d / "results/product/gate_packet/1/packet.json").write_text(
        '{"a":2}', encoding="utf-8")
    ident = scma.mount_identity(a, d)
    assert ident["identity_proven"] is False
    assert ident["differing_files"] == [
        "results/product/gate_packet/1/packet.json"]
    assert ident["n_differing"] == 1


def test_mount_identity_refuses_head_mismatch(tmp_path):
    a = _tiny_mount(tmp_path, "accepted")
    d = _tiny_mount(tmp_path, "deeper")
    # move the deeper head forward by one commit
    (d / "extra.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "-C", str(d), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(d), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-qm", "second"], check=True)
    with pytest.raises(scma.EnvironmentError_, match="HEAD mismatch"):
        scma.mount_identity(a, d)


# --------------------------------------------------------------------------- #
# N2 NON-VACUITY: planted control flips the frozen composite
# --------------------------------------------------------------------------- #
def test_build_planted_control_adds_marked_synthetic_row(tmp_path):
    deep = _tiny_mount(tmp_path, "deep")
    control = scma.build_planted_control(deep, tmp_path / "control_mount")
    state = json.loads(
        (tmp_path / "control_mount/state/product.json").read_text(encoding="utf-8"))
    rows = state["synthetic_control_rows"]
    assert rows[0]["decision_id"] == scma.PLANTED_ROW_ID
    assert rows[0]["synthetic"] is True
    assert control["planted_row_id"] == scma.PLANTED_ROW_ID


def test_frozen_instrument_detects_the_planted_row(tmp_path):
    """The frozen _scored_row_ids + state leg must see the planted row."""
    from evaluation import trigger_reconciliation as tr

    deep = _tiny_mount(tmp_path, "deep")
    scma.build_planted_control(deep, tmp_path / "control_mount")
    old = json.loads(
        (deep / "state/product.json").read_text(encoding="utf-8"))
    new = json.loads(
        (tmp_path / "control_mount/state/product.json").read_text(encoding="utf-8"))
    old_rows = tr._scored_row_ids(old)
    new_rows = tr._scored_row_ids(new)
    assert f"decision_id={scma.PLANTED_ROW_ID}" in (new_rows - old_rows)


# --------------------------------------------------------------------------- #
# C1 CLI fail-closed: a mount without state/ exits 2, never a measurement
# --------------------------------------------------------------------------- #
def test_cli_missing_state_dir_exits_2(tmp_path):
    bare = tmp_path / "bare"
    bare.mkdir()
    rc = scma.main([
        "--run-id", "testcli",
        "--accepted-mount", str(bare),
        "--deep-mount", str(bare),
        "--repo-root", str(LANE),
        "--out-dir", str(tmp_path / "out"),
    ])
    assert rc == 2


# --------------------------------------------------------------------------- #
# C2 hypothesis tamper -> exit 2 before anything else runs
# --------------------------------------------------------------------------- #
def test_verify_pins_refuses_tampered_hypothesis(tmp_path):
    fake = tmp_path / "fake_repo"
    (fake / "evaluation").mkdir(parents=True)
    shutil.copyfile(HYP, fake / "evaluation/hypothesis.json")
    # tamper
    p = fake / scma.HYPOTHESIS_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(HYP, p)
    p.write_text(p.read_text(encoding="utf-8") + " ", encoding="utf-8")
    for rel in scma.FROZEN_PINS:
        dst = fake / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(LANE / rel, dst)
    with pytest.raises(scma.EnvironmentError_, match="hypothesis hash mismatch"):
        scma.verify_frozen_pins(fake)


# --------------------------------------------------------------------------- #
# R1 PROSE-DRIFT GUARD (repair round 1 of rejected cycle 39529073155)
#
# The round-0 report/state claimed "53 keys added" and "all bookkeeping ...
# zero scored rows"; both were false (audit CYCLE_39529073155_GATE.json
# required_fixes D1/D2). The committed machine records say 55/13 and are the
# source of truth. These tests pin the prose to the records so it cannot
# drift back.
# --------------------------------------------------------------------------- #
ADJ_RECORD = LANE / ("results/evaluation/trigger_reconciliation/39529073155/"
                     "39529073155_adjudication.json")
REC_RECORD = LANE / ("results/evaluation/trigger_reconciliation/39529073155/"
                     "39529073155_reconciliation.json")
REPORT = LANE / "reports/evaluation/RETRIEVAL_CA_BENCHMARK_39529073155.md"
STATE = LANE / "state/evaluation.json"


def test_committed_records_key_diff_counts_are_55_and_13():
    adj = json.loads(ADJ_RECORD.read_text(encoding="utf-8"))
    leg = adj["scored_claim_movement_leg"]
    assert len(leg["keys_added"]) == 55, len(leg["keys_added"])
    assert len(leg["keys_changed"]) == 13, len(leg["keys_changed"])
    assert leg["keys_removed"] == []
    rec = json.loads(REC_RECORD.read_text(encoding="utf-8"))
    sp = rec["state_product_json"]
    assert len(sp["keys_added"]) == 55, len(sp["keys_added"])
    assert len(sp["keys_changed"]) == 13, len(sp["keys_changed"])
    assert sp["keys_removed"] == []


def _operative_bullet(report: str) -> str:
    """Return the Results bullet that states the key-diff count (not the
    verbatim-quoted round-0 false claim inside the correction-of-record
    section)."""
    for line in report.splitlines():
        if line.startswith("- `state/product.json` did move as a file"):
            return line
    raise AssertionError("operative state/product.json results bullet not found")


def test_report_and_state_prose_carry_55_not_53():
    report = REPORT.read_text(encoding="utf-8")
    bullet = _operative_bullet(report)
    assert "55 keys added and 13 keys changed" in bullet
    assert "53 keys added" not in bullet
    # the correction-of-record section must preserve the false claim verbatim
    assert "## Correction of record (repair round 1 of rejected cycle 39529073155)" in report

    state = json.loads(STATE.read_text(encoding="utf-8"))
    headline = state["summary"]["headline"]
    assert "55 added / 13 changed" in headline
    assert "53 added / 13 changed" not in headline
    assert "are cycle-ledger and posture bookkeeping, no scored rows" not in headline
    leg = state["scored_claim_movement_adjudication_39529073155"]["movement_leg"]
    assert "55 keys added / 13 changed" in leg
    assert "53 keys added / 13 changed" not in leg
    assert "are cycle-ledger/posture bookkeeping" not in leg
