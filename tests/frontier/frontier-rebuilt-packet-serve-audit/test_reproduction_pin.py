"""Reproduction / published-sha-pin acceptance tests (audit CYCLE_39056749213
required_fix FIX-1).

The prior cycle shipped an AUDIT_RECORD.json whose published sha256 the
delivered harness could not reproduce: the record was generated before the last
code edit of the same commit, so the record and the code disagreed on exactly
one disclosure field and every pin that referenced the record was false as
shipped. These tests make that defect class impossible to ship again silently:

  * two FRESH harness runs (the shipped entrypoint, subprocess, offline) must be
    byte-identical to each other AND to the committed AUDIT_RECORD.json;
  * their sha256 must equal the sha256 pinned in INTEGRATION_CONTRACT.json and
    the run1/run2/published pins in REPRODUCTION.json;
  * the superseded prior published sha must be disclosed (never silently
    dropped) and the extended process rule must be published in the record.

Deterministic and offline. Needs the real packet mount (the record embeds the
resolved packet_dir), so it carries the same explicit skip markers as every
other real-byte test; it never degrades to a synthetic stand-in.
"""
from __future__ import annotations

import json
import subprocess
import sys

import pytest

from conftest import (
    OLD_PACKET_DIR,
    REAL_PACKET_DIR,
    REPO_ROOT,
    TEAM_ID,
    needs_old_packet,
    needs_real_packet,
    sha256_file,
)

TEAM_ROOT = REPO_ROOT / "frontier" / TEAM_ID
TEAM_RESULTS = REPO_ROOT / "results" / "frontier" / TEAM_ID
CONTRACT_PATH = TEAM_RESULTS / "INTEGRATION_CONTRACT.json"
REPRODUCTION_PATH = TEAM_RESULTS / "REPRODUCTION.json"
PUBLISHED_RECORD_PATH = TEAM_RESULTS / "AUDIT_RECORD.json"

# The sha superseded by this repair's regeneration (audit CYCLE_39056749213
# FIX-1 step 2: a measured artifact hash is recorded, never silently dropped).
SUPERSEDED_RECORD_SHA256 = "11eb58efd286f01f24462e74d3e2a9b5eb034c6fc03eae4d31a803a74f60b497"


def _contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _pinned_record_sha() -> str:
    """The AUDIT_RECORD.json sha256 the integration contract publishes."""
    for entry in _contract()["publishes"]:
        if entry.get("path", "").endswith("AUDIT_RECORD.json"):
            return entry["sha256"]
    raise AssertionError("INTEGRATION_CONTRACT.json publishes no AUDIT_RECORD.json sha256")


def _run_shipped_harness(out_path) -> str:
    """One fresh run of the SHIPPED entrypoint, via the contract's recipe."""
    cmd = [
        sys.executable, "-m", "frontier_rebuilt_packet_serve_audit.cli",
        "--packet", str(REAL_PACKET_DIR),
        "--old-packet", str(OLD_PACKET_DIR),
        "--frozen-rules",
        "--evaluation-rescore", "vendored_cross_check_input/39049030442_adjudication.json",
        "--out", str(out_path),
        "--quiet",
    ]
    proc = subprocess.run(
        cmd, cwd=str(TEAM_ROOT), capture_output=True, text=True, timeout=600, check=False
    )
    assert proc.returncode == 0, f"harness failed rc={proc.returncode}: {proc.stderr}"
    return sha256_file(out_path)


@needs_real_packet
@needs_old_packet
def test_two_fresh_runs_reproduce_the_pinned_record_sha(tmp_path):
    """FIX-1: run the harness twice; both shas equal the contract's pin.

    This is the exact regression test the audit ordered: the published record
    sha must be reproducible by the delivered harness, run twice, byte-identical
    to each other AND to the committed record, and equal to every published pin.
    """
    pinned = _pinned_record_sha()

    run1 = _run_shipped_harness(tmp_path / "run1.json")
    run2 = _run_shipped_harness(tmp_path / "run2.json")

    assert run1 == run2, "two consecutive harness runs must be byte-identical"
    assert run1 == pinned, (
        f"shipped harness emitted {run1}, INTEGRATION_CONTRACT.json pins {pinned}"
    )
    assert pinned == sha256_file(PUBLISHED_RECORD_PATH), (
        "the committed AUDIT_RECORD.json must be the artifact the pin names"
    )

    # Every published pin agrees with the freshly emitted sha.
    reproduction = json.loads(REPRODUCTION_PATH.read_text(encoding="utf-8"))
    assert reproduction["published_record_sha256"] == pinned
    assert reproduction["determinism"]["run1_record_sha256"] == pinned
    assert reproduction["determinism"]["run2_record_sha256"] == pinned
    assert reproduction["determinism"]["byte_identical"] is True
    determinism_sentence = _contract()["consumers"]["reproduction"]["determinism"]
    assert pinned in determinism_sentence, (
        "the contract's reproduction.determinism sentence must name the reproducible sha"
    )


@needs_real_packet
@needs_old_packet
def test_emitted_record_carries_the_extended_process_rule(tmp_path):
    """FIX-1 step 5: the record publishes the reproduction/sha-pin process rule.

    The round-1 FIX-4 rule (absence claims re-verified at the final attempt) is
    retained beside the extended rule; both are constant strings so the record
    stays deterministic.
    """
    out_path = tmp_path / "record.json"
    assert _run_shipped_harness(out_path) == _pinned_record_sha()
    record = json.loads(out_path.read_text(encoding="utf-8"))

    rules = record["process_rules"]
    assert "BLOCKED" in rules["absence_and_negativity_claims"]
    extended = rules["reproduction_and_sha_pin_claims"]
    assert "FINAL attempt" in extended
    assert "after the last code edit" in extended.lower() or "AFTER the last code edit" in extended
    assert "BLOCKED" in extended
    assert "CYCLE_39056749213" in extended
    # The cross-check search basis keeps the round-1 absence rule verbatim.
    assert (
        record["cross_check"]["evaluation_search_basis"]["process_rule"]
        == rules["absence_and_negativity_claims"]
    )


def test_superseded_record_sha_is_disclosed_never_silently_dropped():
    """FIX-1 step 2: the prior published sha survives as a superseded disclosure."""
    reproduction = json.loads(REPRODUCTION_PATH.read_text(encoding="utf-8"))
    superseded = reproduction.get("superseded_publications") or []
    entries = {e.get("record_sha256"): e for e in superseded}
    assert SUPERSEDED_RECORD_SHA256 in entries, (
        "the prior published AUDIT_RECORD sha must be preserved as superseded"
    )
    entry = entries[SUPERSEDED_RECORD_SHA256]
    assert entry["preserved_at_commit"]
    assert "regenerat" in entry["superseded_by"].lower()
    assert "code edit" in entry["cause"].lower()
    assert "2942c3c2" in json.dumps(reproduction)  # measured bytes unchanged


def test_process_rule_is_the_one_the_audit_ordered():
    """The extended rule names the blocking escalation the audit attached."""
    from frontier_rebuilt_packet_serve_audit import report

    extended = report.PROCESS_RULES["reproduction_and_sha_pin_claims"]
    assert "shipped harness" in extended
    assert "reproduction.command" in extended
    assert "gates BLOCKED" in extended
    assert report.PROCESS_RULES["absence_and_negativity_claims"].startswith(
        "Any absence"
    )
    # Deterministic: no clock or environment text in the constants.
    for text in report.PROCESS_RULES.values():
        assert "\n" not in text
        assert "TODO" not in text


def test_every_published_team_json_artifact_parses():
    """Packaging guard: a claim-bearing JSON artifact must be parseable JSON.

    Found while executing audit CYCLE_39056749213 FIX-1: the shipped
    INTEGRATION_CONTRACT.json was INVALID JSON (the consumers object was never
    closed, so write_scope / write_scope_prohibitions / non_goals /
    supersession were nested inside consumers and the root brace was missing).
    A contract Product and Evaluation cannot parse is not a contract, so every
    published team JSON artifact must load, and the scope keys must sit at the
    root where the charter's write-scope prohibitions are read from.
    """
    for path in (
        CONTRACT_PATH,
        REPRODUCTION_PATH,
        PUBLISHED_RECORD_PATH,
        TEAM_RESULTS / "RULES.json",
    ):
        assert path.is_file(), path
        json.loads(path.read_text(encoding="utf-8")), path  # raises if malformed

    contract = _contract()
    assert "reproduction" in contract["consumers"]
    for key in (
        "write_scope",
        "write_scope_prohibitions",
        "non_goals",
        "supersession",
        "publishes",
        "consumers",
    ):
        assert key in contract, key
    for key in ("write_scope", "write_scope_prohibitions", "non_goals", "supersession"):
        assert key not in contract["consumers"], f"{key} must not be nested in consumers"
    assert contract["consumers"]["reproduction"]["command"].startswith(
        "cd frontier/frontier-rebuilt-packet-serve-audit"
    )
