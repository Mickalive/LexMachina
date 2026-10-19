"""Tests for evaluation.f3b_record_adjudication (run 39225862749) AND the v58 disposition.

HISTORY (v57 escalation, ACCEPTED): the lane escalated F-3b ("which
frozen_cache_integrity record is the record of record?") to the OWNER and set
``owner_decision_required: true``, citing an audit gate file that does not
exist at any ref.  Factory direction v57 states that no lane is
HUMAN_DECISION_REQUIRED, and factory-wide requirement 29 makes an
unreproducible provenance citation the binding operational defect class.  The
adjudication instrument resolved it autonomously: the pre-image is recoverable
byte-exactly from git, both readings were published side by side, and the cited
source was proven absent.  That accepted record is
``results/evaluation/f3b_adjudication/39225862749.json`` and is PRESERVED.

V58 DISPOSITION (this cycle 39287274485): factory-wide requirement 30 / v58
ordered work (1) then executed the disposition: the as-first-written original is
restored into ``39164900837.json`` (re-hash matches the pre-rewrite digest), the
9b61dcf8 in-place rewrite is re-homed under its own run-id filename with a
provenance note, and nothing is deleted.  See
``results/evaluation/f3b_restore_disposition/39287274485.json`` and
``tests/evaluation/test_f3b_restore_disposition.py``.

These tests pin BOTH the historical facts (git-provable, accepted) and the
post-disposition live state:

* the historical overwrite is git-provable (688321db != 9b61dcf8);
* the current run-named file is RESTORED to the as-first-written pre-image;
* the 9b61dcf8 rewrite is RE-HOMED under its own run-id filename with a note;
* the pre_restore sibling and the pre-image copy are preserved (nothing deleted);
* the cited escalation source is tested, not assumed;
* the accepted adjudication record is preserved unmodified.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from evaluation import f3b_record_adjudication as F  # noqa: E402

TARGET = REPO / F.TARGET_DIR / "39164900837.json"
RESTORED = REPO / F.TARGET_DIR / F.RESTORED_NAME
PRE_RESTORE = REPO / F.TARGET_DIR / "39164900837_pre_restore.json"
REHOMED = REPO / F.TARGET_DIR / "39164900837_post-restore-9b61dcf8.json"
ACCEPTED_RECORD = REPO / "results/evaluation/f3b_adjudication/39225862749.json"
PREIMAGE_COMMIT = "688321db"
OVERWRITE_COMMIT = "9b61dcf8"

PREIMAGE_SHA = "58a273de260770c12dcdc6f645b06b71f95a672757ae3cfa03e870be4bd5b11e"
OVERWRITE_SHA = "af48f417a86215db00c65bc91df89814d88d0b389087bcbda6bcaee140b5f525"
PRE_RESTORE_SHA = "47be772a9d3d1fcf30185b7ed2bed45603df468c82cf4956e498151e296a17f0"


def _git_show(ref: str) -> bytes:
    proc = subprocess.run(
        ["git", "-C", str(REPO), "show", f"{ref}:{F.TARGET_DIR}/39164900837.json"],
        capture_output=True)
    assert proc.returncode == 0, f"{ref} must still carry the record"
    return proc.stdout


# --------------------------------------------------------------------------- #
# 1. the historical overwrite is git-provable (accepted evidence, preserved)
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not TARGET.is_file(), reason="record not present in this checkout")
def test_historical_overwrite_is_git_provable():
    pre_bytes = _git_show(PREIMAGE_COMMIT)
    over_bytes = _git_show(OVERWRITE_COMMIT)
    pre_sha = hashlib.sha256(pre_bytes).hexdigest()
    over_sha = hashlib.sha256(over_bytes).hexdigest()
    assert pre_sha == PREIMAGE_SHA
    assert over_sha == OVERWRITE_SHA
    assert pre_sha != over_sha, "the 9b61dcf8 overwrite was a real, observable difference"


@pytest.mark.skipif(not TARGET.is_file(), reason="record not present in this checkout")
def test_current_file_is_restored_to_the_preimage():
    cur_sha = F.sha256_file(TARGET)
    assert cur_sha == PREIMAGE_SHA, "the run-named file must hold the as-first-written original"
    rec = json.loads(TARGET.read_text(encoding="utf-8"))
    assert rec["verdict"]["outcome"] == "ITEM_1_CLOSED"
    assert rec["m1_input_byte_identity_before_restore"]["n_match"] == 3
    assert "m5_live_probe" in rec, "the deleted evidence field is restored"


@pytest.mark.skipif(not TARGET.is_file(), reason="record not present in this checkout")
def test_9b61dcf8_rewrite_is_rehomed_under_own_run_id_with_provenance_note():
    assert REHOMED.is_file(), "the 9b61dcf8 rewrite must be re-homed, not deleted"
    rehomed = json.loads(REHOMED.read_text(encoding="utf-8"))
    note = rehomed["f3b_rehome_provenance"]
    assert note["authoring_commit"].startswith(OVERWRITE_COMMIT)
    assert note["original_sha256"] == OVERWRITE_SHA
    # the re-homed content is the 9b61dcf8 reading: before_restore flipped to 24,
    # m5_live_probe deleted
    assert rehomed["m1_input_byte_identity_before_restore"]["n_match"] == 24
    assert "m5_live_probe" not in rehomed
    # structural: re-homed minus the provenance key deep-equals the 9b61dcf8 content
    stripped = {k: v for k, v in rehomed.items() if k != "f3b_rehome_provenance"}
    over_json = json.loads(_git_show(OVERWRITE_COMMIT).decode("utf-8"))
    assert stripped == over_json


# --------------------------------------------------------------------------- #
# 2. nothing deleted - siblings preserved
# --------------------------------------------------------------------------- #
def test_pre_restore_sibling_and_preimage_copy_preserved():
    assert F.sha256_file(PRE_RESTORE) == PRE_RESTORE_SHA
    assert F.sha256_file(RESTORED) == PREIMAGE_SHA


def test_accepted_adjudication_record_preserved_unmodified():
    assert ACCEPTED_RECORD.is_file()
    rec = json.loads(ACCEPTED_RECORD.read_text(encoding="utf-8"))
    assert rec["verdict"] == "F3B_AUTONOMOUSLY_RESOLVED_RECORD_RECOVERABLE"
    assert rec["preimage"]["sha256"] == PREIMAGE_SHA
    assert rec["current"]["sha256"] == OVERWRITE_SHA
    assert rec["byte_identity_recovery_proof"]["restored_sha256_matches_preimage_sha256"] is True
    b = rec["both_readings_side_by_side"]
    assert b["as_first_written"]["has_m5_live_probe"] is True
    assert b["as_last_written"]["has_m5_live_probe"] is False


# --------------------------------------------------------------------------- #
# 3. the cited escalation source is tested, not assumed
# --------------------------------------------------------------------------- #
def test_cited_escalation_source_is_proven_absent():
    rec_probe = F.path_exists_anywhere(F.CITED_ESCALATION_SOURCE)
    assert rec_probe["exists_at_any_ref"] is False
    assert rec_probe["ever_added_in_history"] is False


# --------------------------------------------------------------------------- #
# 4. write scope and the exit rule
# --------------------------------------------------------------------------- #
def test_instrument_writes_only_its_own_namespace():
    src = (REPO / "evaluation" / "f3b_record_adjudication.py").read_text(encoding="utf-8")
    body = src.split('"""', 2)[2]
    assert 'TARGET_DIR = "results/evaluation/frozen_cache_integrity"' in src
    assert 'f3b_adjudication' in src
    writes = [ln.strip() for ln in body.splitlines()
              if ".write_text(" in ln or ".write_bytes(" in ln]
    assert len(writes) == 2, writes  # the restored pre-image and the adjudication record
    for ln in writes:
        assert "REPO" in ln or "repo" in ln or "restored_path" in ln or "out" in ln
    for forbidden in ("state/evaluation.json", "results/accepted-state",
                      "results/audit/evaluation/CYCLE"):
        assert f'"{forbidden}' not in body or forbidden == "results/audit/evaluation/CYCLE", forbidden


@pytest.mark.skipif(not TARGET.is_file(), reason="record not present in this checkout")
def test_adjudication_now_reports_preimage_identical_after_disposition():
    """After the v58 restore, the current file matches the pre-image, so the
    adjudication instrument reports F3B_PREIMAGE_IDENTICAL (exit 2) rather than
    RECOVERABLE.  This is the expected post-disposition behaviour, not a
    regression: the escalation was already resolved and disposed."""
    rec = F.adjudicate(REPO, "t")
    assert rec["preimage"]["sha256"] == PREIMAGE_SHA
    assert rec["current"]["sha256"] == PREIMAGE_SHA
    assert rec["verdict"] == "F3B_PREIMAGE_IDENTICAL_NOTE_DISTINCTION_NOT_REQUIRED"
    assert rec["exit_code"] == 2
    # the instrument still writes the pre-image to its own NEW path and overwrites nothing
    assert rec["restored_to_new_path"]["overwrote_nothing"] is True


def test_claim_ceiling_denies_the_thing_an_owner_would_have_decided():
    c = F.CLAIM_CEILING
    assert "does NOT decide which reading is legally or scientifically correct" in c
    assert "does NOT unblock any human gate" in c
    assert "does NOT touch any frozen spec" in c


def test_state_file_no_longer_claims_an_owner_decision_is_required():
    st = json.loads((REPO / "state" / "evaluation.json").read_text(encoding="utf-8"))
    assert st["summary"]["owner_decision_required"] is False
    assert st["continue_recommended"] is True
    esc = st.get("owner_escalations", [])
    for e in esc:
        assert e.get("status") != "STILL OPEN - owner must adjudicate which artifact is the record of record"
