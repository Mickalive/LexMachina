"""Tests for evaluation.f3b_restore_disposition (run 39287274485, direction v58).

Factory-wide requirement 30 / direction v58 ordered work (1): restore the
as-first-written run-39164900837 record into the run-named file (proving the
restoration by re-hash against the pre-rewrite digest), re-home the 9b61dcf8
in-place rewrite under its own run-id filename with a provenance note, delete
nothing, and publish the restoration proof.

These tests pin the post-disposition live state and the proof artifact:

* the run-named file holds the as-first-written original (58a273de...) and the
  re-hash matches the pre-rewrite digest recorded in the accepted adjudication;
* the run-named file carries the pre-restore drift evidence (before_restore
  n_match=3, the 21-element drifted_query_keys list, m5_live_probe present);
* the 9b61dcf8 rewrite is re-homed under 39164900837_post-restore-9b61dcf8.json
  with a provenance note naming 9b61dcf8 as the authoring commit;
* the pre_restore sibling (47be772a...) and the pre-image copy (58a273de...)
  are preserved intact - nothing is deleted;
* the proof artifact publishes old/restored/re-homed digests and the 9b61dcf8
  commit id, and reports deleted == [];
* the frozen bars/rubrics/benchmark re-hash to their pinned digests;
* the instrument writes only its own namespace and deletes nothing.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from evaluation import f3b_restore_disposition as D  # noqa: E402

TARGET = REPO / D.TARGET_DIR / D.RUN_RECORD
PRE_RESTORE = REPO / D.TARGET_DIR / D.PRE_RESTORE
PREIMAGE = REPO / D.TARGET_DIR / D.PREIMAGE
REHOMED = REPO / D.TARGET_DIR / D.REHOMED
PROOF = REPO / "results/evaluation/f3b_restore_disposition/39287274485.json"

PREIMAGE_SHA = "58a273de260770c12dcdc6f645b06b71f95a672757ae3cfa03e870be4bd5b11e"
OVERWRITE_SHA = "af48f417a86215db00c65bc91df89814d88d0b389087bcbda6bcaee140b5f525"
PRE_RESTORE_SHA = "47be772a9d3d1fcf30185b7ed2bed45603df468c82cf4956e498151e296a17f0"


# --------------------------------------------------------------------------- #
# 1. the run-named file is restored to the as-first-written original
# --------------------------------------------------------------------------- #
def test_run_named_file_is_restored_to_as_first_written_original():
    assert D.sha256_file(TARGET) == PREIMAGE_SHA
    rec = json.loads(TARGET.read_text(encoding="utf-8"))
    assert rec["verdict"]["outcome"] == "ITEM_1_CLOSED"
    assert rec["m1_input_byte_identity_before_restore"]["n_match"] == 3
    assert rec["m1_input_byte_identity_after_restore"]["n_match"] == 24


def test_restored_file_carries_the_pre_restore_drift_evidence():
    rec = json.loads(TARGET.read_text(encoding="utf-8"))
    before = rec["m1_input_byte_identity_before_restore"]
    assert before["n_drift"] == 21
    assert len(before["drifted_query_keys"]) == 21
    assert "m5_live_probe" in rec


# --------------------------------------------------------------------------- #
# 2. the 9b61dcf8 rewrite is re-homed with a provenance note
# --------------------------------------------------------------------------- #
def test_9b61dcf8_rewrite_rehomed_with_provenance_note():
    assert REHOMED.is_file()
    rehomed = json.loads(REHOMED.read_text(encoding="utf-8"))
    note = rehomed["f3b_rehome_provenance"]
    assert note["authoring_commit"] == D.OVERWRITE_COMMIT_FULL
    assert note["original_sha256"] == OVERWRITE_SHA
    assert note["original_reading"] == "as_last_written"
    # the 9b61dcf8 reading: before_restore flipped to 24, m5_live_probe deleted
    assert rehomed["m1_input_byte_identity_before_restore"]["n_match"] == 24
    assert "m5_live_probe" not in rehomed
    # structural: minus the provenance key it deep-equals the 9b61dcf8 content
    stripped = {k: v for k, v in rehomed.items() if k != "f3b_rehome_provenance"}
    over = json.loads(D.git("show", f"{D.OVERWRITE_COMMIT}:{D.TARGET_DIR}/{D.RUN_RECORD}")[1])
    assert stripped == over


# --------------------------------------------------------------------------- #
# 3. nothing deleted
# --------------------------------------------------------------------------- #
def test_siblings_preserved_and_nothing_deleted():
    assert D.sha256_file(PRE_RESTORE) == PRE_RESTORE_SHA
    assert D.sha256_file(PREIMAGE) == PREIMAGE_SHA
    proof = json.loads(PROOF.read_text(encoding="utf-8"))
    assert proof["records"]["deleted"] == []
    assert proof["records"]["siblings_preserved_intact"] is True
    # the full original file inventory is still present
    for name in ("39164900837.json", "39164900837_pre_restore.json",
                 "39164900837_preimage_recovered.json", "39164900837_post-restore-9b61dcf8.json",
                 "39164900837_fresh_offline.json", "39207913953.json", "39207913953_fresh_offline.json",
                 "local_test.json", "local_test_fresh_offline.json"):
        assert (REPO / D.TARGET_DIR / name).is_file(), f"missing artifact: {name}"


# --------------------------------------------------------------------------- #
# 4. the proof artifact
# --------------------------------------------------------------------------- #
def test_proof_artifact_publishes_all_required_digests_and_commit_id():
    proof = json.loads(PROOF.read_text(encoding="utf-8"))
    assert proof["verdict"] == "F3B_DISPOSITION_COMPLETE"
    assert proof["exit_code"] == 0
    assert proof["overwrite_commit"] == D.OVERWRITE_COMMIT_FULL
    rr = proof["records"]["run_record"]
    assert rr["old_sha256"] == OVERWRITE_SHA
    assert rr["restored_sha256"] == PREIMAGE_SHA
    assert rr["pre_rewrite_sha256"] == PREIMAGE_SHA
    assert rr["restoration_matches_pre_rewrite_digest"] is True
    rh = proof["records"]["rehomed"]
    assert rh["rehomed_source_sha256"] == OVERWRITE_SHA
    assert rh["structural_match_to_9b61dcf8_content"] is True
    assert rh["authoring_commit"] == D.OVERWRITE_COMMIT_FULL


def test_git_blob_rederivation_matches_pre_rewrite_digest():
    proof = json.loads(PROOF.read_text(encoding="utf-8"))
    rederive = proof["records"]["run_record"]["git_blob_rederivation"]
    assert rederive["reproduces"] is True
    assert rederive["git_blob_sha256"] == PREIMAGE_SHA
    assert rederive["matches_pinned_pre_rewrite_digest"] is True


# --------------------------------------------------------------------------- #
# 5. frozen bars re-hash to pinned digests (standing requirement)
# --------------------------------------------------------------------------- #
def test_frozen_bars_rehash_match_pinned():
    proof = json.loads(PROOF.read_text(encoding="utf-8"))
    bars = proof["frozen_bars_rehash"]
    assert bars["all_match_pinned"] is True
    for name, info in bars.items():
        if name == "all_match_pinned":
            continue
        assert info["match"] is True, f"{name} no longer re-hashes to its pinned digest"


# --------------------------------------------------------------------------- #
# 6. write scope and claim ceiling
# --------------------------------------------------------------------------- #
def test_instrument_writes_only_authorized_paths():
    src = (REPO / "evaluation" / "f3b_restore_disposition.py").read_text(encoding="utf-8")
    body = src.split('"""', 2)[2]
    # authorized writes: the run-named file (restore), the re-homed file, the proof
    assert "run_record.write_bytes" in body
    assert "rehomed_path.write_bytes" in body
    assert "proof_path.write_text" in body
    # it never deletes
    assert ".unlink(" not in body and "os.remove" not in body and "shutil.rmtree" not in body


def test_claim_ceiling_denies_preemption_and_owner_ask():
    c = D.CLAIM_CEILING
    assert "does NOT pre-empt the next served packet" in c
    assert "does NOT re-open the item-1 technical closure" in c
    assert "makes NO owner ask" in c


def test_item_1_technical_closure_not_reopened():
    proof = json.loads(PROOF.read_text(encoding="utf-8"))
    assert proof["item_1_technical_closure"] == "NOT_REOPENED"
    # local_test.json (the ITEM_1_CLOSED technical closure) is untouched
    lt = json.loads((REPO / D.TARGET_DIR / "local_test.json").read_text(encoding="utf-8"))
    assert lt["verdict"]["outcome"] == "ITEM_1_CLOSED"
