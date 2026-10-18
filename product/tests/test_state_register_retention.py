"""The state register may grow; it may never shrink silently.

Audit F2 of rejected cycle 39169296466
---------------------------------------
``state/product.json``'s top-level ``verification`` register was replaced
wholesale by that cycle. The 12 keys accepted at ``bcb1217`` existed nowhere in
the shipped tree - not as ``latest_reality_check`` (the lane's own admitted
failures: "Generation quality can still be legally misweighted even with the
correct decision present", "Full live runs observed roughly 316-469 seconds on
free models; this is not an acceptable product latency"), not as
``pre_existing_collection_errors``, not as ``resume_39014141628`` (which carries
the standing instruction "never weaken content_sha256 or the seam's exclusion to
make them pass"), not as the measured ``latency_budget_9a`` and not as
``live_clickable_slice_this_cycle``. There was no ``supersedes_claims`` entry.
AGENTS.md rule 6 forbids deleting contrary outputs and overwriting historical
claim-bearing results.

Audit note N4 named the reason it escaped: **no committed test read that
register**. The 44-claim ledger could not see it, so nothing failed until a
human auditor diffed the file.

These tests are that reader, and they are written to fail closed: every negative
control below asserts that a deletion, an in-place edit, a missing register and
a missing baseline are each DETECTED, so the guard cannot pass by having nothing
to compare against.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from product import state_register as sr

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state" / "product.json"


def _state() -> dict:
    return json.loads(STATE.read_text(encoding="utf-8"))


def test_state_register_retains_every_record_accepted_at_the_base():
    """The live assertion: nothing accepted at bcb1217 was dropped."""
    state = _state()
    base = sr.baseline()
    assert len(base) == 12, (
        f"the baseline register carries {len(base)} keys, not the 12 extracted "
        f"from `git show {sr.BASELINE_COMMIT}:{sr.BASELINE_SOURCE_PATH}`; "
        "re-derive it rather than restate it")
    diff = sr.missing_or_changed(state, base)
    assert diff["missing"] == [], (
        f"records accepted at {sr.BASELINE_COMMIT} are gone from the state "
        f"register: {diff['missing']} - restore them from "
        "product/data/state_register_baseline/verification_bcb1217.json, or "
        "retire them under a top-level supersedes_claims entry naming the run")
    assert diff["changed"] == {}, (
        "a record accepted at the base was edited in place; editing a claim-"
        "bearing record is the same overwrite as deleting it: "
        f"{sorted(diff['changed'])}")


def test_the_guard_is_non_vacuous_on_this_tree():
    """The register it protects really does hold the base's keys plus new ones."""
    register = _state()["verification"]
    assert set(sr.EXPECTED_BASELINE_KEYS) <= set(register), (
        "the live register does not even contain every base key, so the guard "
        "above cannot be passing for the reason it claims")
    added = sorted(set(register) - set(sr.EXPECTED_BASELINE_KEYS))
    assert added, (
        "the register is exactly the baseline, so this cycle's own entries are "
        "missing - growth is the normal way a cycle records work")


def test_deleting_a_base_record_is_detected():
    """Negative control: the exact F2 shape - a wholesale replacement."""
    state = _state()
    state["verification"] = {k: v for k, v in state["verification"].items()
                             if k not in set(sr.EXPECTED_BASELINE_KEYS)}
    diff = sr.missing_or_changed(state)
    assert set(diff["missing"]) == set(sr.EXPECTED_BASELINE_KEYS), (
        f"replacing the register with this cycle's keys only must report all 12 "
        f"base keys missing, got {sorted(diff['missing'])}")


def test_editing_a_base_record_in_place_is_detected():
    """Negative control: softening an admitted failure is also an overwrite."""
    state = _state()
    findings = state["verification"]["latest_reality_check"]["findings"]
    before = len(findings)
    state["verification"]["latest_reality_check"]["findings"] = [
        f for f in findings if "misweighted" not in f]
    diff = sr.missing_or_changed(state)
    assert before - len(state["verification"]["latest_reality_check"]["findings"]) == 1
    assert "latest_reality_check" in diff["changed"], (
        "an edited admitted finding must be reported as changed; a guard that "
        "only checks key presence would pass this")


def test_a_missing_baseline_is_fail_closed_not_an_empty_pass():
    """A guard with nothing to compare against must FAIL, never pass."""
    state = _state()
    real = sr.BASELINE_PATH
    try:
        sr.BASELINE_PATH = ROOT / "product" / "data" / "does-not-exist.json"
        diff = sr.missing_or_changed(state)
    finally:
        sr.BASELINE_PATH = real
    assert diff["baseline_error"] is True
    assert set(diff["missing"]) == set(sr.EXPECTED_BASELINE_KEYS), (
        "an unreadable baseline must be reported as every key missing; an empty "
        "expectation set would make this guard vacuously green")


def test_a_state_file_without_a_register_is_fail_closed():
    """No ``verification`` register at all is the worst case, not an empty pass."""
    state = {"verification": None}
    diff = sr.missing_or_changed(state)
    assert set(diff["missing"]) == set(sr.EXPECTED_BASELINE_KEYS)
    assert diff["changed"] == {}


def test_the_baseline_is_pinned_to_the_accepted_base_commit():
    """Provenance is part of the guard: an unpinned baseline is editable."""
    raw = sr.BASELINE_PATH.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == sr.BASELINE_SHA256, (
        "the committed baseline no longer hashes to its pinned sha256; re-extract "
        "it from `git show bcb1217:state/product.json` and record the reason")
    assert sr.BASELINE_COMMIT == "bcb1217", (
        "the baseline provenance moved off the accepted base commit")
    assert tuple(sorted(sr.baseline())) == sr.EXPECTED_BASELINE_KEYS, (
        "the EXPECTED_BASELINE_KEYS constant and the baseline file disagree; one "
        "of them was edited without the other")


def test_the_cycle_records_the_audit_F2_repair_in_state_itself():
    """The disclosure lives where a reader of the state will see it."""
    state = _state()
    record = state.get("repair_39169296466_round1")
    assert isinstance(record, dict), (
        "state/product.json does not carry the repair record for the F2 register "
        "deletion; the deletion and its restoration must be disclosed in the "
        "canonical lane state, not only in a report")
    assert record["run_id"] == 39172315384
    assert "restored" in json.dumps(record["f2_state_register_restored"]).lower()
