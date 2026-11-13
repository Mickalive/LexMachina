"""Cycle 43357207555: break the zero-delta chain with a shipped product fix.

Run 43356960891 resumed snapshot ``696cd4b7`` and, like its predecessors
43356503308 and 43349050225, persisted a team ref byte-identical to that same
commit.  The workflow therefore had no audit half again.  This resuming cycle
does not re-diagnose the already-accepted v68 P0 leg; it adds a *durable
product delta* discovered by exercising the shipped progressive server:

    a late ``expand`` job could overwrite an ``enrich`` result

so ``/api/query/status`` said ``answer.status=ready`` while
``/api/query/bundle`` returned ``answer.status=pending``.  The fix is a
monotonic stage guard in ``product/query_app.py`` (``first_page`` /
``map_ready`` < ``map_expanded`` < ``complete``); a lower stage may never
replace a higher one.

Pinned here:

* the resumed snapshot really is a zero-delta, unobserved, unadjudicated
  orchestration outcome (no invented cause);
* the stage guard refuses the exact losing write and the real regression file
  ``product/tests/test_query_app_stage_guard.py`` exists;
* the v68 fixed-path family still re-measures cleanly on current bytes;
* the end-to-end offline slice still answers from the cached fixture;
* the accepted pointer still satisfies both halves of requirement 4;
* posture stays fail-closed and the producer minted no auditor artifact.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "product"
for _p in (str(ROOT), str(PRODUCT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

EXECUTING_RUN_ID = "43357207555"
RESUMED_RUN_ID = "43356960891"
PREDECESSOR_RUN_ID = "43356503308"
SNAPSHOT_HEAD = "696cd4b794133db3a0be94c81c6b3a27208e7b67"
ACCEPTED_RUN_ID = "CYCLE_40284658455"
ACCEPTED_COMMIT = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"

STATE = ROOT / "state" / "product.json"
ORCH = ROOT / "results" / "product" / "orchestration"
DIAG = ORCH / f"CYCLE_{RESUMED_RUN_ID}_resume_diagnosis.json"
FAMILY = (ROOT / "results" / "product" / "counter_content_family"
          / f"CYCLE_{EXECUTING_RUN_ID}.json")
REPORT = ROOT / "reports" / "product" / f"CYCLE_{EXECUTING_RUN_ID}.md"
STAGE_GUARD_TEST = PRODUCT / "tests" / "test_query_app_stage_guard.py"
ACCEPT_GATE = (ROOT / "results" / "audit" / "product"
               / "CYCLE_40284658455_GATE.json")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_resumed_snapshot_continues_a_zero_delta_unobserved_chain():
    diag = _load(DIAG)
    assert diag["run_id"] == RESUMED_RUN_ID
    assert diag["predecessor_run_id"] == PREDECESSOR_RUN_ID
    orch = diag["orchestration"]
    assert orch["classification"] == "RAW_SNAPSHOT_UNAVAILABLE"
    assert orch["mechanism_unobserved"] is True
    assert "mechanism" not in orch
    delta = diag["durable_delta"]
    assert delta["classification"] == "ZERO_DURABLE_DELTA"
    assert delta["changed_files"] == 0
    assert delta["snapshot_head"] == SNAPSHOT_HEAD
    assert delta["predecessor_head"] == SNAPSHOT_HEAD
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["accepted"] is False


def test_late_expansion_cannot_erase_an_enriched_bundle():
    import query_app

    first = {"provenance": {"phase": "map_ready"}, "decisions": [], "clusters": []}
    complete = {
        "provenance": {"phase": "complete"},
        "decisions": [],
        "clusters": [],
        "answer": {"status": "ready", "cited_decision_ids": ["x"]},
    }
    late = {"provenance": {"phase": "map_expanded"}, "decisions": [], "clusters": []}

    run_id = query_app._remember("guard fixture", 100, first, "fixture")
    query_app._set_bundle(run_id, complete)
    query_app._set_bundle(run_id, late)  # the exact losing write
    current = query_app._get(run_id)["bundle"]
    assert current is complete
    assert current["answer"]["status"] == "ready"

    # The real-bundle regression lives beside this cycle test.
    assert STAGE_GUARD_TEST.is_file()


def test_stage_guard_regression_tests_pass():
    proc = subprocess.run(
        [sys.executable, "-m", "pytest",
         str(STAGE_GUARD_TEST.relative_to(ROOT)), "-q"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=600, check=False)
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-1000:]


def test_p0_full_family_rule_still_holds_on_current_committed_bytes():
    cf = _load(FAMILY)
    totals = cf["fixed_path_family"]["totals"]
    assert totals["n_bundles"] == 49
    assert totals["n_decisions"] == 4900
    assert totals["n_verified"] == 55
    assert totals["n_verified_defective"] == 0
    assert totals["defect_histogram"] == {
        "D1_empty_evidence": 0,
        "D2_letterhead_zone": 0,
        "D3_markup_residue": 0,
        "D4_language_marker_mismatch": 0,
    }
    assert cf["false_reject_count"] == 0
    assert cf["confirmed_set"]["decision_id"] == "bstger_SK.2023.49"
    assert cf["confirmed_set"]["still_verified"] is True
    assert cf["ordered_work_2_success_rule"]["met"] is True
    assert cf["ordered_work_2_full_success_rule"]["met"] is True


def test_offline_slice_still_delivers_sourced_clickable_map():
    from offline_slice import build_bundle

    bundle = build_bundle("rent-default", 100, enrich=True)
    rows = bundle["decisions"]
    assert len(rows) == 100
    assert all(r.get("x") is not None and r.get("y") is not None for r in rows)
    assert all(r.get("cluster_id") is not None for r in rows)
    assert all(r.get("canonical_url") for r in rows)
    assert len({r.get("cluster_id") for r in rows}) >= 2
    answer = bundle.get("answer") or {}
    assert answer.get("status") == "ready"
    assert answer.get("cited_decision_ids")
    assert bundle["provenance"]["offline_slice"]["geometry_preserved"] is True
    assert bundle["provenance"]["offline_slice"]["network"] == "none"


def test_accepted_pointer_satisfies_both_halves():
    st = _load(STATE)
    assert st["accepted_run_id"] == ACCEPTED_RUN_ID
    assert st["accepted_commit"] == ACCEPTED_COMMIT
    gate = _load(ACCEPT_GATE)
    assert gate["gate"] == "PASS"
    assert gate["safe_to_integrate"] is True
    assert gate["required_fixes"] == []
    from product.state_contract import accepted_pointer_evidence
    evidence = accepted_pointer_evidence(st, ROOT)
    assert evidence["problems"] == []
    assert evidence["gate_ok"] is True
    assert evidence["accept_commit_present"] is True


def test_posture_fail_closed_and_no_auditor_namespace_writes():
    st = _load(STATE)
    assert st["direction_version"] == 68
    assert st["continue_recommended"] is True
    for flag in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                 "ready_for_owner_session"):
        assert st[flag] is False, f"{flag} must stay fail-closed"
    assert st["current_cycle_run_id"] == int(EXECUTING_RUN_ID)
    assert REPORT.is_file()
    assert not (ROOT / "results" / "audit" / "product"
                / f"CYCLE_{EXECUTING_RUN_ID}_GATE.json").exists()
    assert not (ROOT / "reports" / "audit" / "product"
                / f"CYCLE_{EXECUTING_RUN_ID}.md").exists()
