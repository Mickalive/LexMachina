"""Audit-artifact placement, state hygiene and write-scope guard rails.

The charter's operational revision requires the audit gate to be written at
``results/audit/frontier/frontier-counter-label-integrity/CYCLE_<run_id>_GATE.json`` and
``reports/audit/frontier/frontier-counter-label-integrity/CYCLE_<run_id>.md`` inside the audit
job checkout — never into /tmp, where the gate reader cannot see them and the lane re-dispatches
forever.
"""

from __future__ import annotations

import glob
import json
import os

import pytest

from conftest import REPO_ROOT
from frontier_counter_label_integrity.audit_contract import (
    AUDIT_GATE_VALUES,
    INDEPENDENT,
    PLACEMENT,
    check_gate_files,
    classify_gate_files,
    classify_gate_payload,
)

AUDIT_DIR = os.path.join("results/audit/frontier/frontier-counter-label-integrity")


def _gate_files():
    return sorted(glob.glob(os.path.join(REPO_ROOT, "results/audit/frontier/frontier-counter-label-integrity/CYCLE_*_GATE.json")))


def _audit_md_files():
    return sorted(glob.glob(os.path.join(REPO_ROOT, "reports/audit/frontier/frontier-counter-label-integrity/CYCLE_*.md")))


def test_audit_gate_is_written_at_the_required_relative_path():
    gates = _gate_files()
    assert gates, "no audit GATE.json under results/audit/frontier/frontier-counter-label-integrity/"

    # Anti-vacuity: routing the two artifact classes apart must never make the
    # independent-audit requirement satisfiable by a producer placement copy.
    classes = classify_gate_files(REPO_ROOT)
    assert classes[INDEPENDENT], (
        "no independent audit of record in the audit tree; the audit-artifact "
        "placement requirement must never substitute a producer placement copy "
        "for an independent audit"
    )

    for path in gates:
        payload = json.loads(open(path, encoding="utf-8").read())
        assert path.startswith(os.path.join(REPO_ROOT, "results", "audit")) or "results/audit" in path
        if classify_gate_payload(payload) == PLACEMENT:
            # Producer-authored placement copy: its own contract, enforced below.
            continue
        assert payload["gate"] in AUDIT_GATE_VALUES
        assert isinstance(payload["required_fixes"], list)
        assert payload.get("claim_ceiling")
        assert payload.get("safe_to_integrate") is True or payload["gate"] == "REVISE"


def test_audit_md_is_written_at_the_required_relative_path():
    mds = _audit_md_files()
    assert mds, "no audit markdown under reports/audit/frontier/frontier-counter-label-integrity/"
    for path in mds:
        assert "VERDICT" in open(path, encoding="utf-8").read().upper() or "verdict" in open(path, encoding="utf-8").read()


def test_gate_run_id_matches_the_md_run_id():
    gates = [os.path.basename(p) for p in _gate_files()]
    mds = [os.path.basename(p) for p in _audit_md_files()]
    gate_runs = {g.replace("CYCLE_", "").replace("_GATE.json", "") for g in gates}
    md_runs = {m.replace("CYCLE_", "").replace(".md", "") for m in mds}
    assert gate_runs == md_runs, (gate_runs, md_runs)


def test_each_independent_audit_of_record_has_its_own_markdown():
    """A placement copy's markdown may not stand in for an independent audit's."""
    mds = {os.path.basename(p) for p in _audit_md_files()}
    classes = classify_gate_files(REPO_ROOT)
    for path in classes[INDEPENDENT]:
        run = os.path.basename(path).replace("CYCLE_", "").replace("_GATE.json", "")
        assert f"CYCLE_{run}.md" in mds, run
    assert len(classes[INDEPENDENT]) >= 1


def test_gate_claim_ceiling_preserves_the_claim_limits():
    for path in _gate_files():
        payload = json.loads(open(path, encoding="utf-8").read())
        ceiling = payload["claim_ceiling"]
        if classify_gate_payload(payload) == PLACEMENT:
            continue
        assert "NEVER asserts that any specific decision IS" in ceiling
        assert "BASELINE ONLY" in ceiling
        assert "38828034436" in ceiling


def test_every_gate_artifact_conforms_to_its_own_class_contract():
    """Class-aware sweep: the whole audit tree passes, no file excepted."""
    result = check_gate_files(REPO_ROOT)
    broken = [f for f in result["findings"] if not f["ok"]]
    assert not broken, json.dumps(broken, indent=2, ensure_ascii=False)
    assert result["independent_audit_present"]
    assert result["n_files"] >= 1


def test_producer_placement_copies_may_not_impersonate_an_audit():
    """A placement copy wearing an audit verdict or audit-only keys is rejected.

    This is the check that a naive 'skip the placement copies' fix would have
    dropped: it is what stops a producer from writing gate=PASS into the audit
    tree and having it read as an independent gate.
    """
    classes = classify_gate_files(REPO_ROOT)
    if not classes[PLACEMENT]:
        pytest.skip("no producer placement copy on disk")
    for path in classes[PLACEMENT]:
        payload = json.loads(open(path, encoding="utf-8").read())
        assert "artifact_provenance_warning" in payload
        assert "safe_to_integrate" not in payload
        assert payload.get("gate") not in AUDIT_GATE_VALUES
        assert payload.get("cycle_status") == payload.get("gate")


def test_a_silent_audit_impersonator_is_rejected(tmp_path):
    """Regression: the contract must catch a fabricated audit gate file."""
    from frontier_counter_label_integrity.audit_contract import check_producer_placement_copy

    silent = {
        "run_id": "99999999999",
        "gate": "PASS",  # impersonates an audit verdict
        "safe_to_integrate": True,  # audit-only key
        "claim_ceiling": "looks official",
    }
    problems = check_producer_placement_copy(silent, ["38841035773"])
    assert any("artifact_provenance_warning" in p for p in problems), problems
    assert any("safe_to_integrate" in p for p in problems), problems
    assert any("audit verdict" in p for p in problems), problems
    assert any("claim_ceiling" in p for p in problems), problems


def test_a_placement_copy_must_still_carry_the_substantive_claim_limits():
    """Placement copies are a different contract, not an unchecked escape hatch."""
    from frontier_counter_label_integrity.audit_contract import check_producer_placement_copy

    warned_but_bare = {
        "run_id": "99999999999",
        "gate": "TERMINATE",
        "cycle_status": "TERMINATE",
        "artifact_provenance_warning": (
            "PRODUCER-AUTHORED, NOT INDEPENDENT AUDIT OUTPUT. Do not read this file's "
            "gate as an independent gate. The independent audit of record remains "
            "results/audit/frontier/frontier-counter-label-integrity/CYCLE_38841035773_GATE.json."
        ),
    }
    problems = check_producer_placement_copy(warned_but_bare, ["38841035773"])
    assert any("claim_ceiling" in p for p in problems), problems


def test_a_placement_copy_must_name_a_real_audit_of_record():
    from frontier_counter_label_integrity.audit_contract import check_producer_placement_copy

    misdirected = {
        "run_id": "99999999999",
        "gate": "TERMINATE",
        "cycle_status": "TERMINATE",
        "claim_ceiling": (
            "never asserts any specific decision IS supporting/contrary/limiting; "
            "pre-repair baseline only; run 38828034436 is mechanism evidence only."
        ),
        "artifact_provenance_warning": (
            "PRODUCER-AUTHORED, NOT INDEPENDENT AUDIT OUTPUT. Do not read this file's "
            "gate as an independent gate. The audit of record is CYCLE_11111111111_GATE.json."
        ),
    }
    problems = check_producer_placement_copy(misdirected, ["38841035773"])
    assert any("not an independent audit of record" in p for p in problems), problems


def test_state_retains_charter_version_and_continue_recommendation():
    path = os.path.join(REPO_ROOT, "state/frontier/frontier-counter-label-integrity.json")
    state = json.loads(open(path, encoding="utf-8").read())
    assert state["team_id"] == "frontier-counter-label-integrity"
    assert state["charter_version"] == 1
    assert isinstance(state["continue_recommended"], bool)
    assert state["continue_recommended"] is False
    assert state["continue_recommended_reason"]
    assert state["verdict"] == "LABEL_UNSOUND"
    assert state["charter_run_history"][0]["run_id"] == 38839354961


def test_state_does_not_touch_product_or_human_gate():
    state = json.loads(
        open(os.path.join(REPO_ROOT, "state/frontier/frontier-counter-label-integrity.json"), encoding="utf-8").read()
    )
    blob = json.dumps(state, ensure_ascii=False)
    assert "human_gate_ready" not in blob
    assert "results/product/human_gate_sessions" not in blob


def test_report_md_states_the_verdict_and_the_claim_ceiling():
    path = os.path.join(REPO_ROOT, "reports/frontier/frontier-counter-label-integrity/CYCLE_1.md")
    text = open(path, encoding="utf-8").read()
    assert "LABEL_UNSOUND" in text
    assert "0 / 7" in text and "0 / 39" in text
    assert "not endorsed" in text
    assert "did not test the fix" in text.lower()


def test_no_human_gate_session_artifacts_written():
    for rel in ("results/product/human_gate_sessions", "results/product/human_gate_sessions_simulated"):
        assert not os.path.exists(os.path.join(REPO_ROOT, rel)), rel


def test_team_artifacts_are_all_inside_the_frozen_write_scope(rules):
    allowed = tuple(p.replace("**", "") for p in rules.data["write_scope"])
    tracked = [
        os.path.relpath(os.path.join(root, name), REPO_ROOT)
        for root, _dirs, files in os.walk(os.path.join(REPO_ROOT, "frontier", "frontier-counter-label-integrity"))
        for name in files
        if not name.endswith(".pyc")
    ] + [
        os.path.relpath(os.path.join(root, name), REPO_ROOT)
        for base in ("tests/frontier/frontier-counter-label-integrity",
                     "results/frontier/frontier-counter-label-integrity",
                     "reports/frontier/frontier-counter-label-integrity",
                     "results/audit/frontier/frontier-counter-label-integrity",
                     "reports/audit/frontier/frontier-counter-label-integrity")
        for root, _dirs, files in os.walk(os.path.join(REPO_ROOT, base))
        for name in files
    ]
    for rel in tracked:
        assert any(rel.startswith(prefix) for prefix in allowed), rel