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
# 3. the cited escalation source is tested, not assumed — DUAL-PIN (run 39297074815)
#
# HISTORY: the accepted adjudication (run 39225862749) probed the cited source
# in the core-lane CI checkout, which fetches ONLY the current run's team/audit
# refs plus lab/* branches (.github/workflows/core-lane.yml team job lines
# 42-64, audit job lines 171-182).  The probe therefore recorded absence FROM
# ITS REF SET (finding CITED_ESCALATION_SOURCE_DOES_NOT_EXIST).  A full-fetch
# environment finds the gate at refs/remotes/origin/cycle/core/evaluation/
# 39199651952/audit (commit 97894bba, 2026-10-19T04:39:18Z — 4h25m BEFORE the
# adjudication freeze commit c9d97b50), content gate=REVISE with F-3b escalate.
# The citation was VALID; the universal-negative phrasing was a ref-coverage
# artifact.  The accepted record is NOT edited (AGENTS.md items 5/6); the
# correction is published as a NEW run-namespaced artifact:
# results/evaluation/f3b_escalation_source_correction/39297074815.json.
# Both readings are pinned here — historical (from the accepted record) and
# live (environment-honest: content pin when the audit ref is present, an
# explicit skip naming the missing ref otherwise — never a silent pass).
# --------------------------------------------------------------------------- #
ACCEPTED_ADJ_SHA = "5271024e6fa73b5e3fbbe38e75658a8f88031c16b6086126060ae4ddee494a90"
AUDIT_REF = "refs/remotes/origin/cycle/core/evaluation/39199651952/audit"
AUDIT_REF_COMMIT = "97894bbace99575eccccca158b21df777322f345"
GATE_SHA256 = "206a9376e2ef71252590dc2e8ae1d4e4d3c926928cf6d1b248fd8c15c77ccb2f"
CORRECTION_ARTIFACT = (REPO / "results/evaluation/f3b_escalation_source_correction"
                       / "39297074815.json")


def test_accepted_adjudication_record_still_pins_the_historical_absence_finding():
    """The accepted adjudication record is preserved BYTE-EXACT and still
    carries the historical finding; this cycle corrects it by publication,
    never by editing the record."""
    assert ACCEPTED_RECORD.is_file()
    assert hashlib.sha256(ACCEPTED_RECORD.read_bytes()).hexdigest() == ACCEPTED_ADJ_SHA
    rec = json.loads(ACCEPTED_RECORD.read_text(encoding="utf-8"))
    findings = [f["finding"] for f in rec.get("findings", [])]
    assert "CITED_ESCALATION_SOURCE_DOES_NOT_EXIST" in findings


def test_cited_escalation_source_live_probe_dual_pin():
    """Live probe with environment-honest semantics (see header)."""
    rec_probe = F.path_exists_anywhere(F.CITED_ESCALATION_SOURCE)
    ref_present = AUDIT_REF in rec_probe.get("refs_containing_it", [])
    if not ref_present:
        # A partial-fetch (CI-style) environment: the content pin cannot be
        # evaluated.  SKIP with an explicit reason — never a silent pass, and
        # never a false failure for an environment contract the probe cannot
        # control.  The historical reading is pinned by the previous test.
        pytest.skip(
            f"{AUDIT_REF} is not fetched in this environment (core-lane CI "
            f"checkout fetches only the current run's team/audit refs + lab "
            f"branches); live content pin not evaluable here. Historical "
            f"reading pinned in the accepted adjudication record.")
    # Full-fetch environment: the gate must exist AND carry what the
    # escalation cited — gate=REVISE, F-3b severity=escalate.
    assert rec_probe["exists_at_any_ref"] is True
    assert rec_probe["ever_added_in_history"] is True
    rc, out = F.git("show", f"{AUDIT_REF}:{F.CITED_ESCALATION_SOURCE}")
    assert rc == 0, "the cited gate must be readable at the audit ref"
    gate_bytes = out.encode("utf-8") if isinstance(out, str) else out
    # git show returns text; re-hash via the raw blob to avoid newline munging
    rc2, blob = F.git("rev-parse", f"{AUDIT_REF}:{F.CITED_ESCALATION_SOURCE}")
    assert rc2 == 0
    rc3, raw = F.git("cat-file", "blob", blob.strip())
    assert rc3 == 0
    raw_bytes = raw.encode("utf-8") if isinstance(raw, str) else raw
    assert hashlib.sha256(raw_bytes).hexdigest() == GATE_SHA256
    gate = json.loads(raw)
    assert gate["gate"] == "REVISE"
    assert gate["safe_to_integrate"] is False
    f3b = [f for f in gate.get("required_fixes", []) if f.get("id") == "F-3b"]
    assert len(f3b) == 1
    assert f3b[0]["severity"] == "escalate"


def test_correction_artifact_publishes_both_readings():
    """The NEW correction artifact exists, matches this run, and publishes
    both readings beside each other with the CI fetch contract as mechanism."""
    assert CORRECTION_ARTIFACT.is_file(), (
        "the dual-pin correction artifact of run 39297074815 must be committed")
    art = json.loads(CORRECTION_ARTIFACT.read_text(encoding="utf-8"))
    assert art["run_id"] == "39297074815"
    assert art["cited_escalation_source"] == F.CITED_ESCALATION_SOURCE
    h = art["reading_1_historical_adjudication_env"]
    assert h["finding_recorded"] == "CITED_ESCALATION_SOURCE_DOES_NOT_EXIST"
    assert h["artifact_sha256_pinned"] == ACCEPTED_ADJ_SHA
    v = art["reading_2_live_full_fetch_env"]
    assert v["exists_at_any_ref"] is True
    assert v["gate"] == "REVISE"
    assert v["f3b_fix_entry"]["severity"] == "escalate"
    assert v["audit_ref_commit"] == AUDIT_REF_COMMIT
    assert "core-lane.yml" in art["timeline_proof"]["conclusion"] or (
        "ref-coverage" in art["timeline_proof"]["conclusion"])


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
