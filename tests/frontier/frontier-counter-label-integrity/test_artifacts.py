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

from conftest import REPO_ROOT


def _gate_files():
    return sorted(glob.glob(os.path.join(REPO_ROOT, "results/audit/frontier/frontier-counter-label-integrity/CYCLE_*_GATE.json")))


def _audit_md_files():
    return sorted(glob.glob(os.path.join(REPO_ROOT, "reports/audit/frontier/frontier-counter-label-integrity/CYCLE_*.md")))


def test_audit_gate_is_written_at_the_required_relative_path():
    gates = _gate_files()
    assert gates, "no audit GATE.json under results/audit/frontier/frontier-counter-label-integrity/"
    for path in gates:
        payload = json.loads(open(path, encoding="utf-8").read())
        assert payload["gate"] in ("PASS", "REVISE")
        assert isinstance(payload["required_fixes"], list)
        assert payload.get("claim_ceiling")
        assert payload.get("safe_to_integrate") is True or payload["gate"] == "REVISE"
        assert path.startswith(os.path.join(REPO_ROOT, "results", "audit")) or "results/audit" in path


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


def test_gate_claim_ceiling_preserves_the_claim_limits():
    for path in _gate_files():
        ceiling = json.loads(open(path, encoding="utf-8").read())["claim_ceiling"]
        assert "NEVER asserts that any specific decision IS" in ceiling
        assert "BASELINE ONLY" in ceiling
        assert "38828034436" in ceiling


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