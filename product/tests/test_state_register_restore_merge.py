"""The state register is MERGED back, never replaced - the recurrence guard.

Why this exists
---------------
The register deletion happened TWICE:

* accepted cycle 39543057762 (``bdfcc9813``) replaced ``state/product.json``
  wholesale and deleted the top-level ``verification`` register;
* accepted cycle 39660515863 (``03b4bc6``) replaced it again - the live 20-key
  register became a 13-key block carrying NONE of the 12 records accepted at
  ``bcb1217``.

The second deletion could happen because the first version of
``product/state_register_restore.py`` RESTORED by replacing the whole
``verification`` block with the preserved bytes, while its own docstring
claimed "the live state keeps its own value for every key it already carried".
It did not: the restore itself dropped the live register's own records, so the
tool enforced shrinkage and the next wholesale replacement went unnoticed.

These tests pin the merge semantics and the preserved bytes, so a third
deletion cannot be papered over by a restore that replaces.

The contract
------------
1. The live register is the MERGE of the two preserved registers: every key of
   each is present, and where both carry a key the LIVE value wins.
2. The 12 records accepted at ``bcb1217`` are present with unedited values
   (``product/state_register.py`` owns that byte-exact check; this module
   asserts the merge does not fight it).
3. Every preserved artifact exists with a provenance whose sha256 matches the
   artifact's bytes, and the historical restoration disclosure is byte-exact
   against the state that wrote it.
4. The restore is idempotent: re-running it on a conformant tree changes
   nothing.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from product import state_register  # noqa: E402
from product import state_register_restore as srr  # noqa: E402

STATE_PATH = ROOT / "state" / "product.json"


def _live() -> dict:
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def _git_state(commit: str) -> dict:
    proc = subprocess.run(  # noqa: S603
        ["git", "show", f"{commit}:state/product.json"],
        cwd=str(ROOT), capture_output=True, check=True)
    return json.loads(proc.stdout.decode("utf-8"))


def test_the_live_register_is_the_merge_of_both_preserved_registers() -> None:
    """Neither cycle's own register records may be lost by the restore."""
    live = _live()["verification"]
    first = _git_state("fe30b0d")["verification"]          # run 39651573572
    second = json.loads(                                  # run 39660515863
        (ROOT / "results" / "product" / "state_register"
         / "CYCLE_39660515863_state_product.json").read_text(encoding="utf-8")
    )["verification"]

    missing_first = sorted(set(first) - set(live))
    missing_second = sorted(set(second) - set(live))
    assert not missing_first, f"the restore dropped the 39651573572 records: {missing_first}"
    assert not missing_second, f"the restore dropped the 39660515863 records: {missing_second}"

    # Where both registers carry a key, the LIVE value wins (the merge is
    # additive, never a silent revert of a later cycle's own record).
    shared = sorted(set(first) & set(second))
    for key in shared:
        if key in srr.CLAIM_BEARING_REGISTER_KEYS:
            assert live[key] == second[key], (
                f"the claim-bearing record {key!r} was reverted to the "
                "39651573572 value; a claim-bearing record is never edited")
        else:
            # A per-cycle pointer (a timestamp, a run id, an artifact path) may
            # legitimately have moved on - but it may never be silently reverted
            # to the OLDER register's value.
            assert live[key] != first[key] or first[key] == second[key], (
                f"the register key {key!r} was reverted to the 39651573572 value; "
                "the live value must win for every key the live state already "
                "carries")


def test_the_baseline_records_are_present_and_unedited() -> None:
    """The 12 records accepted at bcb1217 survive, byte-exact."""
    diff = state_register.missing_or_changed(_live())
    assert not diff["missing"], f"the register lost: {diff['missing']}"
    assert not diff["changed"], f"the register edited: {sorted(diff['changed'])}"
    assert not diff["baseline_error"]


def test_the_restore_tool_merges_instead_of_replacing() -> None:
    """The tool's own merge keeps a live-only key and a live-only value."""
    live = {"a": 1, "live_only": "keep me"}
    preserved = {"a": 99, "preserved_only": "add me"}
    changed = srr._merge_into_live(live, preserved, ("verification",))
    assert changed == [], "a merge with nothing to do must change nothing"

    live = {"verification": {"a": 1, "live_only": "keep me"}}
    preserved = {"verification": {"a": 99, "preserved_only": "add me"}}
    srr._merge_into_live(live, preserved, ("verification",))
    merged = live["verification"]
    assert merged["a"] == 1, "the live value must win for a key both carry"
    assert merged["live_only"] == "keep me", "a live-only key must not be dropped"
    assert merged["preserved_only"] == "add me", "a preserved-only key must be added"

    # Negative control: the OLD semantics (replace) would have dropped both
    # live-only keys. The merge must not be that.
    replaced = dict(preserved["verification"])
    assert "live_only" not in replaced
    assert "live_only" in merged


def test_every_preserved_artifact_and_its_provenance_are_intact() -> None:
    """The deleted bytes are still on disk, and their provenance still matches."""
    for entry in srr.PRESERVED_ONLY:
        artifact = ROOT / "results" / "product" / "state_register" / entry["artifact"]
        assert artifact.exists(), f"the preserved artifact {artifact.name} is missing"
        provenance = artifact.with_name(artifact.name.replace(
            ".json", ".PROVENANCE.json"))
        assert provenance.exists(), f"{provenance.name} is missing"
        recorded = json.loads(provenance.read_text(encoding="utf-8"))
        digest = srr.sha256_file(artifact)
        assert recorded.get("sha256") == digest, (
            f"{provenance.name} records sha256 {recorded.get('sha256')!r}, "
            f"the artifact hashes to {digest}")

    for restoration in srr.RESTORATIONS:
        artifact = (ROOT / "results" / "product" / "state_register"
                    / restoration["artifact"])
        assert artifact.exists(), f"the preserved artifact {artifact.name} is missing"
        provenance = artifact.with_name(artifact.name.replace(
            ".json", ".PROVENANCE.json"))
        assert provenance.exists(), f"{provenance.name} is missing"
        recorded = json.loads(provenance.read_text(encoding="utf-8"))
        assert recorded.get("sha256") == srr.sha256_file(artifact)


def test_the_historical_restoration_disclosure_is_byte_exact() -> None:
    """The 39651573572 disclosure is HISTORY: it is restored, never re-worded."""
    live = _live()
    historical = _git_state("fe30b0d")
    assert live["state_register_restoration_39651573572"] == \
        historical["state_register_restoration_39651573572"], (
        "the first restoration disclosure was re-worded; a historical record is "
        "restored byte-exact, never edited in place")
    assert live["supersedes_claims"]["state_register_deleted_by_39543057762"] == \
        historical["supersedes_claims"]["state_register_deleted_by_39543057762"]


def test_this_cycles_restoration_is_disclosed_with_its_preserved_bytes() -> None:
    """The second deletion is disclosed the same way the first one was."""
    live = _live()
    record = live.get("state_register_restoration_39674781875")
    assert record is not None, "the second register deletion is not disclosed"
    assert record["deleting_run"] == "39660515863"
    artifact = ROOT / "results" / "product" / "state_register" / \
        "CYCLE_39651573572_state_product.json"
    assert record["preserved_bytes"]["sha256"] == srr.sha256_file(artifact)
    assert live["supersedes_claims"]["state_register_deleted_by_39660515863"]


def test_the_check_passes_on_the_live_tree_and_the_restore_is_idempotent() -> None:
    """The guard is green here, and re-running the restore changes nothing."""
    assert srr.check() == [], f"the register guard is red: {srr.check()}"
    before = STATE_PATH.read_bytes()
    assert srr.apply_restore() is False, "the restore changed a conformant tree"
    assert STATE_PATH.read_bytes() == before, "the restore rewrote a conformant tree"


def test_a_shrunken_register_is_detected() -> None:
    """Negative control: a register that lost a baseline record is a FAIL."""
    live = _live()
    shrunk = json.loads(json.dumps(live))
    shrunk["verification"].pop("latest_reality_check", None)
    diff = state_register.missing_or_changed(shrunk)
    assert diff["missing"] == ["latest_reality_check"], (
        "a register that lost a claim-bearing record must be reported missing")
