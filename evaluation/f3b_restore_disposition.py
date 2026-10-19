#!/usr/bin/env python3
"""F-3B record-integrity disposition (factory-wide requirement 30 / direction v58).

THE DEFECT (append-only evidence violation, AGENTS.md items 5/6)
----------------------------------------------------------------
Commit 9b61dcf8 (evaluation cycle 39198745348 repair 0) rewrote
``results/evaluation/frozen_cache_integrity/39164900837.json`` IN PLACE.  The
as-first-written record (git blob 6a5ed68 at commit 688321db, sha256
58a273de...) was the run-39164900837 measurement ``ITEM_1_CLOSED`` with the
pre-restore drift evidence intact (``m1_input_byte_identity_before_restore``
n_match=3, the 21-element ``drifted_query_keys`` list, and the ``m5_live_probe``
field).  The 9b61dcf8 rewrite flipped the before-restore reading 3 -> 24 and
deleted ``m5_live_probe`` and the 21-element list, erasing the evidence that the
pre-restore tree had drifted.

THE DISPOSITION ORDERED (factory-wide requirement 30, carried into v58)
----------------------------------------------------------------------
1. Restore the original run-39164900837 bytes into
   ``results/evaluation/frozen_cache_integrity/39164900837.json`` and PROVE the
   restoration by re-hash against the pre-rewrite digest.
2. RE-HOME the 9b61dcf8 rewritten content under its OWN run-id filename with a
   provenance note naming 9b61dcf8 as the authoring commit.
3. DELETE NOTHING - neither the pre_restore sibling nor any other artifact is
   removed.  A file named for run X holds run X's measurement; a later
   re-measurement is a NEW artifact under a NEW run id.

RESTORE SOURCE - WHY THE PRE-IMAGE AND NOT THE PRE_RESTORE SIBLING
-------------------------------------------------------------------
The order names "the preserved sibling 39164900837_pre_restore.json".  Forensic
recomputation (this instrument, and the accepted f3b_adjudication record
39225862749.json) establishes that the pre_restore sibling is a DISTINCT record:
it is the pre-restore NEGATIVE STATE (n_match=3/24, S1_closure_complete=false,
outcome INPUT_BYTES_MOVED_WITH_AGGREGATE_STABLE, restore.performed=false), not the
as-first-written 39164900837.json.  The as-first-written original is preserved
byte-exactly at 39164900837_preimage_recovered.json (git blob 6a5ed68 at 688321db,
sha256 58a273de...).  The pre-rewrite digest recorded in the accepted
f3b_adjudication is 58a273de..., and the objective proof criterion ("re-hash
against the pre-rewrite digest") is satisfied ONLY by the pre-image.  The
pre-image also contains the same pre-restore evidence the sibling records
(before_restore n_match=3 and the 21-element drifted_query_keys list), so
restoring it preserves the negative result too.  The pre_restore sibling is
preserved untouched.

This instrument WRITES only:
  * the restored 39164900837.json   (the authorized in-place restore),
  * the re-homed 9b61dcf8 file      (a NEW artifact under a NEW run id),
  * the proof artifact              (a NEW record).
It does NOT delete, move or rewrite any other artifact, frozen spec, rubric,
bar, gate, test or state file.  It introduces NO threshold and NO bar.

Exit codes
----------
0  F3B_DISPOSITION_COMPLETE
2  F3B_DISPOSITION_FAILED
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "lex-evaluation-f3b-restore-disposition/1"
TARGET_DIR = "results/evaluation/frozen_cache_integrity"
RUN_RECORD = "39164900837.json"
PREIMAGE = "39164900837_preimage_recovered.json"
PRE_RESTORE = "39164900837_pre_restore.json"
REHOMED = "39164900837_post-restore-9b61dcf8.json"
PROOF_DIR = "results/evaluation/f3b_restore_disposition"

OVERWRITE_COMMIT = "9b61dcf8"
OVERWRITE_COMMIT_FULL = "9b61dcf845c5c75ab58d9b2fdc554c998536b011"
PREIMAGE_BLOB = "6a5ed68ff1cb0b51927b0360a4cc7a0962fc7649"
PREIMAGE_COMMIT = "688321dbb6262491bd3f5a495b56558a1d707172"

# Digests established by the accepted f3b_adjudication (39225862749.json) and
# re-verified here.  Pinned so the proof is a re-derivation, not a retype.
EXPECTED_OLD_SHA256 = "af48f417a86215db00c65bc91df89814d88d0b389087bcbda6bcaee140b5f525"
EXPECTED_PREIMAGE_SHA256 = "58a273de260770c12dcdc6f645b06b71f95a672757ae3cfa03e870be4bd5b11e"
EXPECTED_PRE_RESTORE_SHA256 = "47be772a9d3d1fcf30185b7ed2bed45603df468c82cf4956e498151e296a17f0"

FROZEN_BARS = {
    "RULES_LABEL.json": (
        "evaluation/frozen_bars/RULES_LABEL.json",
        "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608",
    ),
    "RULES_GEOMETRY.json": (
        "evaluation/frozen_bars/RULES_GEOMETRY.json",
        "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633",
    ),
    "frozen_retrieval_benchmark.json": (
        "evaluation/retrieval_gate/frozen_retrieval_benchmark.json",
        "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72",
    ),
    "FREEZE_RECORD.json": (
        "evaluation/retrieval_gate/FREEZE_RECORD.json",
        "b06a2ad024040c38312686ab7aacc5ab18c663f1ef0b77494caf6ce3b3b52e49",
    ),
}

CLAIM_CEILING = (
    "This instrument executes the F-3B record-integrity disposition ordered by factory-wide "
    "requirement 30 and direction v58: it restores the as-first-written run-39164900837 record "
    "into the run-named file, re-homes the 9b61dcf8 in-place rewrite under its own run-id "
    "filename with a provenance note, deletes nothing, and publishes the restoration proof. It "
    "does NOT re-open the item-1 technical closure (local_test.json ITEM_1_CLOSED stands on its "
    "own fresh instruments), does NOT re-run the frozen cache integrity instrument, does NOT "
    "change any frozen spec/threshold/bar/rubric, does NOT unblock the human gate, makes NO "
    "owner ask, and does NOT pre-empt the next served packet."
)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git(*args: str) -> tuple[int, str]:
    proc = subprocess.run(["git", "-C", str(REPO_ROOT), *args],
                          capture_output=True, text=True)
    return proc.returncode, proc.stdout


def verify_git_blob() -> dict:
    """Re-derive the pre-rewrite digest from git and compare to the pinned value."""
    rc, out = git("cat-file", "blob", PREIMAGE_BLOB)
    if rc != 0:
        return {"reproduces": False, "error": "git cat-file blob failed"}
    digest = sha256_bytes(out.encode("utf-8", errors="surrogateescape"))
    return {
        "reproduces": True,
        "git_blob": PREIMAGE_BLOB,
        "git_blob_commit": PREIMAGE_COMMIT,
        "git_blob_sha256": digest,
        "matches_pinned_pre_rewrite_digest": digest == EXPECTED_PREIMAGE_SHA256,
    }


def rehash_frozen_bars() -> dict:
    out: dict[str, Any] = {}
    all_match = True
    for name, (rel, pinned) in FROZEN_BARS.items():
        p = REPO_ROOT / rel
        actual = sha256_file(p) if p.is_file() else None
        match = actual == pinned
        all_match = all_match and match
        out[name] = {"path": rel, "pinned_sha256": pinned, "actual_sha256": actual,
                     "match": match}
    out["all_match_pinned"] = all_match
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None, help="proof artifact path (default: auto-named by run id)")
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args()

    run_id = args.run_id or "local"
    proof_rel = args.out or f"{PROOF_DIR}/{run_id}.json"
    proof_path = REPO_ROOT / proof_rel

    run_record = REPO_ROOT / TARGET_DIR / RUN_RECORD
    preimage_path = REPO_ROOT / TARGET_DIR / PREIMAGE
    pre_restore_path = REPO_ROOT / TARGET_DIR / PRE_RESTORE
    rehomed_path = REPO_ROOT / TARGET_DIR / REHOMED

    findings: list[dict] = []

    # ---- pre-condition verification -------------------------------------
    if not run_record.is_file():
        return _fail(proof_path, run_id, f"{RUN_RECORD} absent from the tree")
    if not preimage_path.is_file():
        return _fail(proof_path, run_id, f"{PREIMAGE} absent from the tree")
    if not pre_restore_path.is_file():
        return _fail(proof_path, run_id, f"{PRE_RESTORE} absent from the tree")

    old_bytes = run_record.read_bytes()
    old_sha = sha256_bytes(old_bytes)
    preimage_bytes = preimage_path.read_bytes()
    preimage_sha = sha256_bytes(preimage_bytes)
    pre_restore_sha = sha256_file(pre_restore_path)

    if old_sha != EXPECTED_OLD_SHA256:
        findings.append({"finding": "OLD_RECORD_UNEXPECTED", "severity": "material",
                         "detail": f"current {RUN_RECORD} sha256 {old_sha} != expected 9b61dcf8 rewrite {EXPECTED_OLD_SHA256}"})
    if preimage_sha != EXPECTED_PREIMAGE_SHA256:
        findings.append({"finding": "PREIMAGE_UNEXPECTED", "severity": "material",
                         "detail": f"{PREIMAGE} sha256 {preimage_sha} != expected as-first-written {EXPECTED_PREIMAGE_SHA256}"})
    if pre_restore_sha != EXPECTED_PRE_RESTORE_SHA256:
        findings.append({"finding": "PRE_RESTORE_SIBLING_UNEXPECTED", "severity": "material",
                         "detail": f"{PRE_RESTORE} sha256 {pre_restore_sha} != expected {EXPECTED_PRE_RESTORE_SHA256}"})

    git_blob = verify_git_blob()
    if not git_blob.get("reproduces") or not git_blob.get("matches_pinned_pre_rewrite_digest"):
        findings.append({"finding": "PREWRITE_DIGEST_NOT_REPRODUCIBLE", "severity": "material",
                         "detail": str(git_blob)})

    bars = rehash_frozen_bars()
    if not bars.get("all_match_pinned"):
        findings.append({"finding": "FROZEN_BAR_DRIFT", "severity": "material",
                         "detail": "a frozen bar/rubric/benchmark no longer re-hashes to its pinned digest"})

    if findings:
        return _fail(proof_path, run_id, "pre-condition verification failed", findings)

    # ---- re-home the 9b61dcf8 rewrite (NEW artifact, NEW run id) --------
    old_json = json.loads(old_bytes.decode("utf-8"))
    rehomed_json = dict(old_json)
    rehomed_json["f3b_rehome_provenance"] = {
        "authoring_commit": OVERWRITE_COMMIT_FULL,
        "authoring_commit_short": OVERWRITE_COMMIT,
        "rehomed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rehomed_by_run": run_id,
        "original_reading": "as_last_written",
        "original_sha256": old_sha,
        "reason": (
            "Re-homed per factory-wide requirement 30 / direction v58 F-3B disposition. This file "
            "is the 9b61dcf8 in-place rewrite of run 39164900837's record (the 'as last written' "
            "reading). The as-first-written original is restored to 39164900837.json. This "
            "re-homed copy preserves the 9b61dcf8 content apart from this provenance key."
        ),
    }
    rehomed_bytes = (json.dumps(rehomed_json, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    rehomed_path.write_bytes(rehomed_bytes)
    rehomed_sha = sha256_bytes(rehomed_bytes)

    # structural verification: re-homed minus the provenance key == 9b61dcf8 content
    rehomed_minus = dict(rehomed_json)
    rehomed_minus.pop("f3b_rehome_provenance", None)
    structural_match = rehomed_minus == old_json

    # ---- restore the as-first-written original into the run-named file --
    run_record.write_bytes(preimage_bytes)
    restored_sha = sha256_file(run_record)
    restoration_matches = restored_sha == EXPECTED_PREIMAGE_SHA256

    # ---- verify nothing deleted / siblings preserved --------------------
    post_pre_restore_sha = sha256_file(pre_restore_path)
    post_preimage_sha = sha256_file(preimage_path)
    preserved_intact = (post_pre_restore_sha == EXPECTED_PRE_RESTORE_SHA256
                        and post_preimage_sha == EXPECTED_PREIMAGE_SHA256)

    deleted: list[str] = []  # nothing is deleted by this instrument

    proof = {
        "schema": SCHEMA,
        "run_id": run_id,
        "direction_version": 58,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "disposition": "F3B_RESTORE_AND_REHOME",
        "ruling": "factory-wide requirement 30 / direction v58 ordered work (1)",
        "claim_ceiling": CLAIM_CEILING,
        "overwrite_commit": OVERWRITE_COMMIT_FULL,
        "records": {
            "run_record": {
                "path": f"{TARGET_DIR}/{RUN_RECORD}",
                "old_sha256": old_sha,
                "restored_sha256": restored_sha,
                "pre_rewrite_sha256": EXPECTED_PREIMAGE_SHA256,
                "restoration_matches_pre_rewrite_digest": restoration_matches,
                "restore_source": f"{TARGET_DIR}/{PREIMAGE}",
                "restore_source_sha256": preimage_sha,
                "git_blob": PREIMAGE_BLOB,
                "git_blob_commit": PREIMAGE_COMMIT,
                "git_blob_rederivation": git_blob,
            },
            "rehomed": {
                "path": f"{TARGET_DIR}/{REHOMED}",
                "rehomed_sha256": rehomed_sha,
                "rehomed_source_sha256": old_sha,
                "structural_match_to_9b61dcf8_content": structural_match,
                "authoring_commit": OVERWRITE_COMMIT_FULL,
                "provenance_note_embedded": True,
            },
            "preserved": [
                {"path": f"{TARGET_DIR}/{PRE_RESTORE}", "sha256": post_pre_restore_sha,
                 "role": "pre-restore negative state (distinct record, untouched)"},
                {"path": f"{TARGET_DIR}/{PREIMAGE}", "sha256": post_preimage_sha,
                 "role": "as-first-written original (copy, untouched)"},
                {"path": f"{TARGET_DIR}/local_test.json",
                 "role": "ITEM_1_CLOSED technical closure - NOT re-opened by this repair"},
            ],
            "deleted": deleted,
            "siblings_preserved_intact": preserved_intact,
        },
        "restore_source_rationale": (
            "The order names the pre_restore sibling; forensic recomputation (and the accepted "
            "f3b_adjudication 39225862749.json) establishes the pre_restore sibling is the pre-restore "
            "negative state, not the as-first-written 39164900837.json. The as-first-written original "
            "(preimage, 58a273de...) is the version that matches the pre-rewrite digest and is run "
            "39164900837's actual measurement (ITEM_1_CLOSED); it also contains the same pre-restore "
            "evidence (before_restore n_match=3, 21-element drifted_query_keys list). The pre_restore "
            "sibling is preserved untouched."
        ),
        "frozen_bars_rehash": bars,
        "item_1_technical_closure": "NOT_REOPENED",
        "owner_decision_required": False,
        "pre_empts_next_packet": False,
    }

    ok = (restoration_matches and structural_match and preserved_intact
          and not deleted and bars.get("all_match_pinned"))
    proof["verdict"] = "F3B_DISPOSITION_COMPLETE" if ok else "F3B_DISPOSITION_FAILED"
    proof["exit_code"] = 0 if ok else 2

    proof_path.parent.mkdir(parents=True, exist_ok=True)
    proof_path.write_text(json.dumps(proof, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps({"verdict": proof["verdict"], "proof": proof_rel,
                      "restored_sha256": restored_sha,
                      "rehomed_sha256": rehomed_sha,
                      "restoration_matches_pre_rewrite_digest": restoration_matches,
                      "structural_match_to_9b61dcf8_content": structural_match,
                      "siblings_preserved_intact": preserved_intact}, indent=2))
    return 0 if ok else 2


def _fail(proof_path: Path, run_id: str, detail: str,
          findings: list[dict] | None = None) -> int:
    proof = {
        "schema": SCHEMA,
        "run_id": run_id,
        "direction_version": 58,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "disposition": "F3B_RESTORE_AND_REHOME",
        "verdict": "F3B_DISPOSITION_FAILED",
        "exit_code": 2,
        "detail": detail,
        "findings": findings or [],
    }
    try:
        proof_path.parent.mkdir(parents=True, exist_ok=True)
        proof_path.write_text(json.dumps(proof, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except Exception:
        pass
    print(json.dumps(proof, indent=2))
    return 2


if __name__ == "__main__":
    sys.exit(main())
