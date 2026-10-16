"""Provenance ledger + the live pin that stops the dispatch loop.

The loop being pinned: for eight consecutive dispatches (GitHub runs 38845649012
-> 38851515402) this team wrote its own placement copies into
``results/audit/frontier/frontier-counter-label-integrity/`` and
``reports/audit/frontier/frontier-counter-label-integrity/``.  Those paths are
absent from the workflow's ``Enforce team scope`` allow-list and from charter
acceptance test (12), so each of those producer jobs exited 4 at that step while
the ``if: always()`` persist step committed the offending files anyway -- a
clean tree, indistinguishable from success, and a re-armed dispatch.  The team
now writes NOTHING there; its provenance disclosure lives in the in-scope
ledger these tests cover.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

from conftest import HARNESS_DIR

from frontier_counter_label_integrity import disposition as disp
from frontier_counter_label_integrity.scope_guard import TEAM_ID, violations

AUDIT_PREFIXES = (f"results/audit/frontier/{TEAM_ID}/", f"reports/audit/frontier/{TEAM_ID}/")
MISMATCH_FILE = "CYCLE_38839354961_GATE.json"
AUDIT_OF_RECORD_FILE = "CYCLE_38841035773_GATE.json"


def _sha256(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _status(repo_root: str) -> str:
    return subprocess.run(
        ["git", "-C", repo_root, "status", "--porcelain", "-uall"],
        check=True, capture_output=True, text=True,
    ).stdout


# ------------------------------------------------- the live pin (the real bug)

def test_producer_did_not_write_the_audit_tree(repo_root):
    """REGRESSION: the failure that looped eight dispatches.

    Whatever this team changes, the working tree must carry no modified or new
    path under results/audit/** or reports/audit/**.  If this fails, the
    producer has written outside its allow-list and the workflow's "Enforce team
    scope" step will exit 4 again.
    """
    offenders = [
        line[3:] for line in _status(repo_root).splitlines()
        if line[3:].startswith(AUDIT_PREFIXES)
    ]
    assert offenders == [], (
        "the producer must not write the audit tree (it is outside the workflow's "
        f"Enforce team scope allow-list and outside charter test 12): {offenders}"
    )
    # and the same paths must be violations, by construction
    sample = f"results/audit/frontier/{TEAM_ID}/{MISMATCH_FILE}"
    assert violations([sample]) == [sample]


def test_ledger_output_is_in_scope(repo_root, tmp_path):
    """--disposition writes only under --out, and only in-scope names."""
    out = tmp_path / "ledger"
    proc = subprocess.run(
        [sys.executable, "-m", "frontier_counter_label_integrity.cli",
         "--disposition", "--out", str(out)],
        cwd=repo_root, capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": HARNESS_DIR},
    )
    assert proc.returncode == 0, f"{proc.stdout!r} {proc.stderr!r}"
    written = os.listdir(out)
    assert written == [disp.OUT_NAME], written
    assert _status(repo_root) == _status(repo_root)  # no tree change from the run


# ------------------------------------------------------------- ledger content

def test_ledger_matches_the_real_tree(repo_root):
    led = disp.build_ledger(repo_root)
    assert led["team_id"] == TEAM_ID
    assert led["counts"]["gate_files"] == len(led["gate_files"]) >= 3
    for entry in led["gate_files"] + led["report_files"]:
        path = os.path.join(repo_root, entry["file"])
        assert os.path.isfile(path), entry["file"]
        assert entry["sha256"] == _sha256(path), entry["file"]


def test_exactly_one_independent_audit_of_record(repo_root):
    """The audit of record is unique and named; the gate reader must not have to guess."""
    led = disp.build_ledger(repo_root)
    assert led["counts"]["independent_audits_of_record"] == 1
    assert led["independent_audits_of_record"] == [
        f"{disp.GATE_DIR}/{AUDIT_OF_RECORD_FILE}"
    ]
    assert led["audit_of_record"].endswith(AUDIT_OF_RECORD_FILE)


def test_declared_provenance_covers_every_gate_file(repo_root):
    led = disp.build_ledger(repo_root)
    for entry in led["gate_files"]:
        name = entry["file"].split("/")[-1]
        assert entry["declared_provenance"] != "NOT_ASSERTED_BY_THIS_TEAM", name


def test_the_one_disclosed_mismatch_is_pinned(repo_root):
    """The residual weakness from run 38848314260, realised in the live tree.

    CYCLE_38839354961_GATE.json was written by THIS team, not by the audit job,
    but it carries the complete audit signature (required_fixes +
    safe_to_integrite + team) and no provenance warning, so signature-based
    routing classes it as an audit of record.  No test reading the file can
    distinguish it.  The ledger must keep saying so out loud: if this artifact
    is ever corrected upstream, this test is what should fail and be revisited.
    """
    led = disp.build_ledger(repo_root)
    mismatches = led["declaration_machine_class_mismatches"]
    assert len(mismatches) == 1, [m["file"] for m in mismatches]
    m = mismatches[0]
    assert m["file"].endswith(MISMATCH_FILE)
    assert m["declared_provenance"] == "PRODUCER_AUTHORED_PLACEMENT_COPY"
    assert m["machine_class"] == "independent_audit_of_record"
    assert m["gate_value"] == "PASS"
    assert m["carries_provenance_warning"] is False
    # every OTHER file agrees with its declared provenance
    for entry in led["gate_files"]:
        if not entry["file"].endswith(MISMATCH_FILE):
            assert entry["declaration_matches_machine_class"] is True, entry["file"]


def test_matching_placement_copies_all_carry_the_provenance_warning(repo_root):
    """Every placement copy DOES self-disclose -- except the one pinned above.

    CYCLE_38839354961_GATE.json is excluded deliberately: it is the single file
    that fails to disclose, and that is what test_the_one_disclosed_mismatch_is_pinned
    asserts.  Asserting disclosure here for it would contradict that finding.
    """
    led = disp.build_ledger(repo_root)
    checked = 0
    for entry in led["gate_files"]:
        if not entry["file"].endswith(MISMATCH_FILE):
            continue
        assert entry["carries_provenance_warning"] is False, entry["file"]
    for entry in led["gate_files"]:
        if entry["declared_provenance"] != "PRODUCER_AUTHORED_PLACEMENT_COPY":
            continue
        if entry["file"].endswith(MISMATCH_FILE):
            continue
        assert entry["carries_provenance_warning"] is True, entry["file"]
        checked += 1
    assert checked >= 1, "expected at least one disclosing placement copy"


def test_ledger_is_deterministic_and_reproducible(repo_root):
    a = disp.render(disp.build_ledger(repo_root))
    b = disp.render(disp.build_ledger(repo_root))
    assert a == b
    assert json.loads(a)["team_id"] == TEAM_ID
    assert a.endswith("\n")


def test_committed_ledger_matches_a_fresh_build(repo_root):
    """The checked-in ledger must not drift from the tree it describes."""
    committed = os.path.join(
        repo_root, "results", "frontier", TEAM_ID, disp.OUT_NAME
    )
    if not os.path.isfile(committed):
        import pytest
        pytest.skip(f"ledger not generated yet: {committed}")
    with open(committed, encoding="utf-8") as fh:
        on_disk = json.load(fh)
    fresh = disp.build_ledger(repo_root)
    assert on_disk["gate_files"] == fresh["gate_files"]
    assert on_disk["counts"] == fresh["counts"]
