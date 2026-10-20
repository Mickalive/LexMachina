"""Hash re-verification tests (acceptance test 6)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import PACKET, requires_accepted
from frontier_counter_label_emission import verify_input_hashes
from frontier_counter_label_emission.classifier_bridge import (
    CLASSIFIER_FILE_PINS,
    FROZEN_LABEL_RULES_SHA256,
    verify_classifier_and_rubric,
)

GOOD_PACKET_PINS = {
    "packet.json": "32ac812626e679c357822543d0b2e78e62c0e95a9a1b233d1ec89d7cb7b6ac70",
    "questions/de-kapitalverletzung.bundle.json":
        "9b856e2b1b3e4675f8d4d135cd5d1ad23f0baa63fcb2e4cc7bc45182c012881b",
}


@requires_accepted
def test_correct_hashes_pass():
    rec = verify_input_hashes(PACKET, GOOD_PACKET_PINS)
    assert rec["ok"] is True
    assert rec["n_checked"] == 2
    assert rec["mismatches"] == []


@requires_accepted
def test_mutated_byte_fails(tmp_path: Path):
    # Copy one pinned file, flip a byte, expect a mismatch.
    src = PACKET / "packet.json"
    dst = tmp_path / "packet.json"
    data = bytearray(src.read_bytes())
    data[-2] = (data[-2] + 1) % 256
    dst.write_bytes(bytes(data))
    rec = verify_input_hashes(tmp_path, {"packet.json": GOOD_PACKET_PINS["packet.json"]})
    assert rec["ok"] is False
    assert rec["mismatches"][0]["status"] == "mismatch"


@requires_accepted
def test_missing_file_fails(tmp_path: Path):
    rec = verify_input_hashes(tmp_path, {"packet.json": GOOD_PACKET_PINS["packet.json"]})
    assert rec["ok"] is False
    assert rec["mismatches"][0]["status"] == "missing"


@requires_accepted
def test_classifier_and_rubric_verify():
    rec = verify_classifier_and_rubric()
    assert rec["ok"] is True
    assert rec["frozen_rules_ok"] is True
    assert rec["frozen_rules_sha256_actual"] == FROZEN_LABEL_RULES_SHA256
    assert len(rec["classifier_files"]) == len(CLASSIFIER_FILE_PINS)


@requires_accepted
def test_classifier_verify_raises_on_mutated_rules(tmp_path: Path):
    bad = tmp_path / "RULES_LABEL.json"
    payload = Path(rec_rules_path()).read_bytes() + b"\n"
    bad.write_bytes(payload)
    with pytest.raises(ValueError, match="mismatch"):
        verify_classifier_and_rubric(rules_path=bad)


def rec_rules_path() -> Path:
    from conftest import RULES_PATH
    return RULES_PATH
