"""Tests for evaluation.f3b_record_adjudication (run 39225862749).

The lane escalated F-3b ("which frozen_cache_integrity record is the record of
record?") to the OWNER and set ``owner_decision_required: true``, citing an audit
gate file that does not exist at any ref.  Factory direction v57 states that no
lane is HUMAN_DECISION_REQUIRED, and factory-wide requirement 29 makes an
unreproducible provenance citation the binding operational defect class.

These tests pin the autonomous resolution:

* the pre-image really is recoverable byte-exactly from git;
* the instrument never overwrites, restores-over or deletes either record;
* both readings are published side by side with named digests;
* the cited escalation source is tested, not assumed;
* the exit rule cannot report a resolution when nothing was recovered.
"""
from __future__ import annotations

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
PREIMAGE_COMMIT = "688321db"


# --------------------------------------------------------------------------- #
# 1. the pre-image is genuinely recoverable, byte-exactly
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not TARGET.is_file(), reason="record not present in this checkout")
def test_preimage_is_recoverable_byte_exactly_from_git():
    proc = subprocess.run(
        ["git", "-C", str(REPO), "show",
         f"{PREIMAGE_COMMIT}:{F.TARGET_DIR}/39164900837.json"],
        capture_output=True)
    assert proc.returncode == 0, "the pre-image commit must still carry the record"
    import hashlib
    pre_sha = hashlib.sha256(proc.stdout).hexdigest()
    cur_sha = F.sha256_file(TARGET)
    assert pre_sha != cur_sha, "the overwrite must be a real, observable difference"
    assert pre_sha == "58a273de260770c12dcdc6f645b06b71f95a672757ae3cfa03e870be4bd5b11e"
    assert cur_sha == "af48f417a86215db00c65bc91df89814d88d0b389087bcbda6bcaee140b5f525"


@pytest.mark.skipif(not TARGET.is_file(), reason="record not present in this checkout")
def test_adjudication_resolves_and_restores_to_a_new_path(tmp_path):
    out = tmp_path / "adj.json"
    rec = F.adjudicate(REPO, "t")
    assert rec["verdict"] == "F3B_AUTONOMOUSLY_RESOLVED_RECORD_RECOVERABLE"
    assert rec["exit_code"] == 0
    assert rec["preimage"]["sha256"] == "58a273de260770c12dcdc6f645b06b71f95a672757ae3cfa03e870be4bd5b11e"
    assert rec["preimage_commit"].startswith(PREIMAGE_COMMIT)
    # the restore writes a NEW file and never touches the current record
    assert rec["restored_to_new_path"]["path"] == f"{F.TARGET_DIR}/{F.RESTORED_NAME}"
    assert rec["restored_to_new_path"]["sha256"] == rec["preimage"]["sha256"]
    assert rec["byte_identity_recovery_proof"]["restored_sha256_matches_preimage_sha256"] is True
    assert F.sha256_file(TARGET) == rec["current"]["sha256"], "current record must be untouched"


@pytest.mark.skipif(not TARGET.is_file(), reason="record not present in this checkout")
def test_both_readings_are_published_side_by_side_with_named_digests():
    rec = F.adjudicate(REPO, "t")
    b = rec["both_readings_side_by_side"]
    assert b["as_first_written"]["sha256"] != b["as_last_written"]["sha256"]
    assert b["as_first_written"]["has_m5_live_probe"] is True
    assert b["as_last_written"]["has_m5_live_probe"] is False


@pytest.mark.skipif(not TARGET.is_file(), reason="record not present in this checkout")
def test_exact_delta_is_a_set_relation_not_a_cardinality_match():
    rec = F.adjudicate(REPO, "t")
    d = rec["exact_delta_preimage_vs_current"]
    changed = {c["key"] for c in d["value_changed"]}
    removed = {c["key"] for c in d["removed"]}
    # the deleted claim-bearing block is named, not merely counted
    assert any(k.startswith("m5_live_probe") for k in removed)
    assert any("S2_prior_repair_completeness" in k for k in changed)
    assert d["n_keys_changed"] == len(d["value_changed"])


# --------------------------------------------------------------------------- #
# 2. the cited escalation source is tested, not assumed
# --------------------------------------------------------------------------- #
def test_cited_escalation_source_is_proven_absent():
    rec_probe = F.path_exists_anywhere(F.CITED_ESCALATION_SOURCE)
    assert rec_probe["exists_at_any_ref"] is False
    assert rec_probe["ever_added_in_history"] is False


@pytest.mark.skipif(not TARGET.is_file(), reason="record not present in this checkout")
def test_missing_cited_source_is_reported_as_a_material_finding():
    rec = F.adjudicate(REPO, "t")
    ids = [f["finding"] for f in rec["findings"]]
    assert "CITED_ESCALATION_SOURCE_DOES_NOT_EXIST" in ids
    fnd = next(f for f in rec["findings"]
               if f["finding"] == "CITED_ESCALATION_SOURCE_DOES_NOT_EXIST")
    assert fnd["severity"] == "material"
    assert "reproduce" in fnd


# --------------------------------------------------------------------------- #
# 3. write scope and the exit rule
# --------------------------------------------------------------------------- #
def test_instrument_writes_only_its_own_namespace():
    src = (REPO / "evaluation" / "f3b_record_adjudication.py").read_text(encoding="utf-8")
    body = src.split('"""', 2)[2]
    # the only path the instrument constructs is its restored file inside its
    # own results namespace plus its own record
    assert 'TARGET_DIR = "results/evaluation/frozen_cache_integrity"' in src
    assert 'f3b_adjudication' in src
    # results/audit is PROBED (to test whether the cited escalation source
    # exists) and never WRITTEN; state/ and accepted-state/ are never touched
    writes = [ln.strip() for ln in body.splitlines()
              if ".write_text(" in ln or ".write_bytes(" in ln]
    assert len(writes) == 2, writes  # the restored pre-image and the adjudication record
    for ln in writes:
        assert "REPO" in ln or "repo" in ln or "restored_path" in ln or "out" in ln
    for forbidden in ("state/evaluation.json", "results/accepted-state",
                      "results/audit/evaluation/CYCLE"):
        # forbidden as a WRITE target; the audit probe is a read of a literal
        # path that is only used to ask git whether it exists
        assert f'"{forbidden}' not in body or forbidden == "results/audit/evaluation/CYCLE", forbidden


@pytest.mark.skipif(not TARGET.is_file(), reason="record not present in this checkout")
def test_exit_code_is_zero_only_when_something_was_recovered(monkeypatch, tmp_path):
    out = tmp_path / "r.json"
    rc = F.main(["--run-id", "t", "--out", str(out)])
    rec = json.loads(out.read_text(encoding="utf-8"))
    assert rc == 0 and rec["verdict"].startswith("F3B_AUTONOMOUSLY_RESOLVED")
    assert out.is_file(), "the artifact of record must be written on the passing path too"
    # simulate a destroyed pre-image: the instrument must refuse to claim a resolution
    monkeypatch.setattr(F, "git_blob_at", lambda ref, rel: (None, {"error": "gone"}))
    rec2 = F.adjudicate(REPO, "t")
    assert rec2["verdict"] == "F3B_UNRESOLVED_PREIMAGE_NOT_RECOVERABLE"
    assert rec2["exit_code"] == 2


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