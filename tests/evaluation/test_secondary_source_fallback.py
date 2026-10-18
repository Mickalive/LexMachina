"""Tests for the secondary-source fallback verifier (repair F4 of audit CYCLE_39120832665).

Run 39123055362 repairs the four required fixes of the independent audit of
rejected cycle 39120832665 (gate=REVISE). These tests are IN-REPO and
MOUNT-INDEPENDENT by design - that is the point of F4: the fallback verifier
must be re-runnable from committed bytes alone, in an auditor or CI checkout
where the ephemeral dispatch mount /tmp/lex_accepted/product does not exist.

They pin:
- the frozen primary instrument was NOT edited by the repair (F1/F4 discipline);
- the fallback re-hashes all 14 declared pins from committed bytes and matches;
- the F1 gap-closure check #14 (primary instrument self-hash) is present;
- the claim-bearing record's pin count is 13, so the false "14/14" claim of
  034f2043 cannot recur as an unchallenged number (F1 regression guard);
- a missing secondary source yields NOT_MEASURED exit 2, never a silent pass;
- the corrected 13/13 text stands in the report and state (F1/F3 text guards).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from evaluation.secondary_source_fallback import (
    EXIT_MISMATCH,
    EXIT_NOT_MEASURED,
    EXIT_OK,
    FROZEN_QIDS,
    PRIMARY_INSTRUMENT_RELPATH,
    SECONDARY_DEFAULT,
    rehash_all_pins,
    run,
)

ROOT = Path(__file__).resolve().parents[2]
HYP = ROOT / "evaluation" / "QUESTION_NATIVE_TRANSFER_HYPOTHESIS.json"
PRIMARY_RECORD = (ROOT / "results" / "evaluation" / "question_native_transfer"
                  / "39120832665.json")
SECONDARY = ROOT / SECONDARY_DEFAULT
REPORT = ROOT / "reports" / "evaluation" / "CYCLE_39120832665.md"
STATE = ROOT / "state" / "evaluation.json"
PRIMARY_SHA_PIN = ("ffb2c70fe202ecd495dc0bf969a68bdf4ea891769be2b812ea4f36379a258a29")


def _load(p: Path) -> dict:
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------- #
# F1/F4 discipline: the frozen primary instrument is untouched
# --------------------------------------------------------------------------- #
def test_frozen_primary_instrument_was_not_edited_by_the_repair():
    import hashlib
    actual = hashlib.sha256((ROOT / PRIMARY_INSTRUMENT_RELPATH).read_bytes()).hexdigest()
    assert actual == PRIMARY_SHA_PIN, \
        "the frozen primary instrument was edited - this destroys run 39120832665 provenance"
    hyp = _load(HYP)
    assert hyp["frozen_inputs"]["instrument_sha256"] == PRIMARY_SHA_PIN


# --------------------------------------------------------------------------- #
# the fallback instrument itself
# --------------------------------------------------------------------------- #
def test_fallback_runs_in_repo_without_mount_and_matches_all_pins():
    record, exit_code = run("test-inline", HYP, SECONDARY, ROOT)
    assert exit_code == EXIT_OK
    assert record["verdict"] == "SECONDARY_SOURCE_MATCHES_HYPOTHESIS_PINS"
    assert record["primary_mount_used"] is False
    assert record["network_requests"] == 0
    assert record["n_pin_checks"] == 14
    assert record["pins_all_match"] is True
    assert all(c.get("match") for c in record["pins"]["checks"].values())


def test_f1_gap_closure_check_is_present_and_named():
    record, _ = run("test-inline", HYP, SECONDARY, ROOT)
    checks = record["pins"]["checks"]
    assert "primary_instrument_self_hash" in checks
    c = checks["primary_instrument_self_hash"]
    assert c["expected"] == PRIMARY_SHA_PIN
    assert c["actual"] == PRIMARY_SHA_PIN
    assert c["match"] is True


def test_all_three_frozen_qids_are_covered_by_the_ten_packet_pins():
    record, _ = run("test-inline", HYP, SECONDARY, ROOT)
    names = set(record["pins"]["checks"])
    for qid in FROZEN_QIDS:
        assert f"rebuilt_bundle::{qid}" in names
        assert f"rebuilt_question::{qid}" in names
        assert f"rebuilt_admissibility::{qid}" in names
    assert "rebuilt_packet_json" in names


def test_missing_secondary_source_is_NOT_MEASURED_never_a_silent_pass():
    with tempfile.TemporaryDirectory() as td:
        absent = Path(td) / "no_such_secondary"
        record, exit_code = run("test-absent", HYP, absent, ROOT)
    assert exit_code == EXIT_NOT_MEASURED
    assert record["verdict"] == "NOT_MEASURED"
    assert record["pins_all_match"] is False


def test_tampered_secondary_pin_is_PIN_MISMATCH():
    with tempfile.TemporaryDirectory() as td:
        bad = Path(td) / "tampered_packet"
        shutil.copytree(SECONDARY, bad)
        target = bad / "packet.json"
        target.write_bytes(target.read_bytes() + b"\n# tamper\n")
        record, exit_code = run("test-tampered", HYP, bad, ROOT)
    assert exit_code == EXIT_MISMATCH
    assert record["verdict"] == "PIN_MISMATCH"
    c = record["pins"]["checks"]["rebuilt_packet_json"]
    assert c["match"] is False
    assert c["expected"] != c["actual"]


def test_cli_entry_point_is_executable_and_writes_a_record():
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "fallback.json"
        proc = subprocess.run(
            [sys.executable, "-m", "evaluation.secondary_source_fallback",
             "--run-id", "test-cli", "--out", str(out)],
            cwd=str(ROOT), capture_output=True, text=True, timeout=120)
        assert proc.returncode == EXIT_OK, proc.stderr
        record = json.loads(out.read_text())
    assert record["verdict"] == "SECONDARY_SOURCE_MATCHES_HYPOTHESIS_PINS"


# --------------------------------------------------------------------------- #
# F1 regression guards: the false 14/14 claim cannot recur unchallenged
# --------------------------------------------------------------------------- #
def test_primary_record_pin_count_is_13_not_14():
    record = _load(PRIMARY_RECORD)
    assert len(record["pins"]["checks"]) == 13, \
        "the claim-bearing record carries exactly 13 pin checks; the false 14/14 claim of 034f2043 must not be laundered"


def test_report_carries_the_corrected_13_of_13_pin_line():
    text = REPORT.read_text(encoding="utf-8")
    assert "**Pins: 13/13 re-hashed match**" in text
    # the ORIGINAL false standalone claim must be gone (the repair-disclosure
    # prose may still QUOTE it; that is disclosure, not the claim)
    assert "- **Pins: 14/14 re-hashed match**" not in text


def test_state_pin_claims_are_corrected():
    state = _load(STATE)
    reason = state["continue_recommended_reason"]
    assert "all 13 pins re-hashed match" in reason
    assert "all 14 pins re-hashed match" not in reason
    delta = state["durable_delta_39120832665"]
    entry = next(e for e in delta if "question_native_transfer/39120832665.json" in e)
    assert "13/13 pins match" in entry
    assert "14/14 pins match" not in entry


def test_state_claim_ceiling_carries_the_f2_f3_corrections():
    state = _load(STATE)
    ceiling = state["claim_ceiling"]
    assert "24 of 214" in ceiling or "24/214" in ceiling
    assert "bge_97 IV 10" in ceiling
    assert "arbeitgebers" in ceiling


# --------------------------------------------------------------------------- #
# the secondary source is a committed, byte-identical fallback
# --------------------------------------------------------------------------- #
def test_secondary_source_files_are_committed_to_the_repository():
    proc = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(SECONDARY / "packet.json")],
        cwd=str(ROOT), capture_output=True, text=True)
    assert proc.returncode == 0, \
        "the secondary source must be committed, not an untracked mount artefact"


def test_rehash_all_pins_resolves_every_input_from_committed_bytes():
    hyp = _load(HYP)
    result = rehash_all_pins(hyp, ROOT, SECONDARY)
    assert result["n_checks"] == 14
    assert result["any_input_missing"] is False
    assert result["all_match"] is True
    # no check may resolve from the ephemeral mount
    for name, c in result["checks"].items():
        assert "/tmp/lex_accepted" not in c.get("resolved_from", ""), name
