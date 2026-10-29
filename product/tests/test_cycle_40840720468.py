#!/usr/bin/env python3
"""Pins the operational resume of run 40832905362 by run 40840720468.

Run 40828117614's TEAM job consumed the 2700 s work quantum in
"Run lane cycle" (2705.0 s, exit 78) AFTER writing the durable P0 fix, and the
always-run persist step committed that tree at 7393042a.  Run 40832905362's
TEAM job was fully green, but its AUDIT "Independent audit" step then died at
the same 2700 s quantum (2705.0 s, exit 78) before writing a gate; its one-file
delta (product/query/counter_evidence_span.py) added an over-broad
``_LEADHEAD_INDICATORS`` content supplement to ``frozen_content_defects``.

This cycle removes that supplement, adds the anti-regression test, re-verifies
the inherited 7393042a P0 fix in place, and re-keys state/report/test/dossier/
route/intake to 40840720468.  Neither failed run is accepted; no gate exists.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state" / "product.json"
ORCH = ROOT / "results" / "product" / "orchestration"
AR = ROOT / "results" / "product" / "audit_readiness"
REPORT = ROOT / "reports" / "product" / "CYCLE_40840720468.md"
DIAG = ORCH / "CYCLE_40832905362_resume_diagnosis.json"
RAW = ORCH / "CYCLE_40832905362_run_jobs_raw.json"
FLAT = ORCH / "CYCLE_40832905362_audit_step_diagnosis.json"
DELTA = ORCH / "CYCLE_40832905362_delta_substance.json"
PRED_RAW = ORCH / "CYCLE_40828117614_run_jobs_raw.json"
PRED_FLAT = ORCH / "CYCLE_40828117614_audit_step_diagnosis.json"
PRED_DELTA = ORCH / "CYCLE_40828117614_delta_substance.json"
CONTENT_FAMILY = (ROOT / "results" / "product" / "counter_content_family"
                  / "CYCLE_40840720468.json")
SLICE_SUMMARY = (ROOT / "results" / "product" / "offline_slice"
                 / "20261029T082259Z" / "summary.json")
SMOKE = (ROOT / "results" / "product" / "progressive_smoke"
         / "CYCLE_40840720468_progressive_smoke.json")
DOSSIER = AR / "CYCLE_40840720468_audit_readiness.json"
ROUTE = AR / "CYCLE_40840720468_AUDIT_ROUTE.json"
INTAKE = AR / "CYCLE_40840720468_AUDIT_INTAKE.md"
ACCEPTED = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
SNAPSHOT = "e2a5b5995abb47b5685bcd2ec08e6bbb3ec7469c"
PREVSNAP = "7393042a9193afa611c0d5ddd630870eb85ce1e4"
RUN = "40840720468"
RESUME = "40832905362"
PRED_RUN = "40828117614"


def test_state_pointer_and_posture_non_rotting():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    assert state["accepted_run_id"] == "CYCLE_40284658455"
    assert state["accepted_commit"] == ACCEPTED
    # DISCLOSED MAINTENANCE REPAIR (cycle 40858799166): the top-level run
    # pointers rotate by design.  The originals are preserved here as history
    # and replaced with the non-rotting form used by prior cycles:
    #   assert state["current_cycle_run_id"] == RUN
    #   assert state["current_run"] == RUN
    #   assert state["current_run_id"] == RUN
    ptr = state["current_cycle_run_id"]
    assert ptr and str(ptr).isdigit()
    assert state["current_run"] == ptr
    assert state["current_run_id"] == ptr
    assert f"cycle_{ptr}_operational_resume" in state
    assert state["direction_version"] == 68
    assert state["cycle_status"] == "COMPLETE"
    assert state["continue_recommended"] is True
    assert state["human_gate_ready"] is False
    assert state["machine_gate_ready"] is False
    assert state["ready_for_owner_session"] is False
    assert state["packet_admitted"] is False
    assert state["owner_decision_required"] is False
    block = state["cycle_40840720468_operational_resume"]
    assert block["run_id"] == RUN
    assert block["resumed_run_id"] == RESUME
    assert block["predecessor_run_id"] == PRED_RUN
    assert block["resumed_snapshot_head"] == SNAPSHOT
    assert block["diagnosis_of_resumed"] == \
        "results/product/orchestration/CYCLE_40832905362_resume_diagnosis.json"
    rf = block["resumed_failure"]
    assert rf["classification"] == "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    assert "2705.0 s" in rf["audit_job"]
    assert "OBSERVED_QUANTUM_EXPIRED" in rf["mechanism"]
    assert rf["gate_file_written"] is False
    assert rf["adjudication"] == "UNADJUDICATED"
    assert "COMMITTED_DELTA" in rf["durable_delta"]
    assert "1 " in rf["durable_delta"]
    pf = block["predecessor_failure"]
    assert pf["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert "2705.0 s" in pf["team_job"]
    assert "OBSERVED_QUANTUM_EXPIRED" in pf["team_job"]
    assert "SUBSTANTIVE" in pf["durable_delta"]
    assert "39" in pf["durable_delta"]
    assert block["regression_repair"]["file"] == \
        "product/query/counter_evidence_span.py"
    assert "_LEADHEAD_INDICATORS" in block["regression_repair"]["removed"]
    assert block["snapshot_audit_readiness"]["state_advanced"] is True
    assert block["posture"]["continue_recommended"] is True
    assert block["posture"]["human_gate_ready"] is False
    # DISCLOSED MAINTENANCE REPAIR (cycle 40858799166): the audit_route
    # pointer rotates with the executing run.  The original is preserved:
    #   assert state["audit_route"]["artifact"] == \
    #       "results/product/audit_readiness/" \
    #       "CYCLE_40840720468_AUDIT_ROUTE.json"
    assert state["audit_route"]["artifact"]  # pointer exists and is truthy
    # Append-only predecessors must survive.
    assert state["cycle_40823586491_operational_resume"]
    assert state["cycle_40820909501_operational_resume"]
    assert state["cycle_40808627073_operational_resume"]


def test_run_history_entries_and_append_only_predecessor():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    hist = {str(e["run_id"]): e for e in state["run_history"]}
    assert PRED_RUN in hist and RESUME in hist and RUN in hist
    pred = hist[PRED_RUN]
    assert pred["accepted"] is False
    assert "QUANTUM" in pred["status"]
    assert "2705.0 s" in pred["team_job"]
    assert "OBSERVED_QUANTUM_EXPIRED" in pred["team_job"]
    assert pred["audit_job"] == "skipped (team job did not succeed)"
    res = hist[RESUME]
    assert res["accepted"] is False
    assert "AUDIT_QUANTUM" in res["status"]
    assert "SUCCESS" in res["team_job"]
    assert "2705.0 s" in res["audit_job"]
    assert "OBSERVED_QUANTUM_EXPIRED" in res["audit_job"]
    cur = hist[RUN]
    assert cur["status"] == \
        "AUDIT_JOB_QUANTUM_DEATH_P0_SUPPLEMENT_REMOVED_SNAPSHOT_REVERIFIED_" \
        "AUDIT_READY_UNADJUDICATED"
    assert cur["resumed_run"] == RESUME
    assert cur["accepted"] is False
    assert cur["accepted_commit"] == ACCEPTED
    assert cur["report_of_record"] == "reports/product/CYCLE_40840720468.md"
    assert cur["cycle_test"] == "product/tests/test_cycle_40840720468.py"
    assert cur["audit_gate"] == "NONE_YET"


def test_resumed_run_is_audit_quantum_death_not_team_failure():
    diag = json.loads(DIAG.read_text(encoding="utf-8"))
    assert diag["run_id"] == RESUME
    assert diag["predecessor_run_id"] == PRED_RUN
    orch = diag["orchestration"]
    assert orch["classification"] == \
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    mech = orch["mechanism"]
    assert mech["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert mech["quantum_expired"] is True
    assert mech["quantum_seconds"] == 2700
    assert mech["exit_code"] == 78
    team = orch["team"]
    assert team["conclusion"] == "success"
    assert team["producer_state_validation_step_conclusion"] == "success"
    assert team["write_scope_step_conclusion"] == "success"
    audit = orch["audit"]
    assert audit["conclusion"] == "failure"
    assert audit["failed_step"] == "Independent audit"
    assert audit["independent_audit_step_seconds"] == 2705.0
    assert audit["gate_step"] == "skipped"
    assert audit["persist_step"] == "skipped"
    assert audit["gate_file_written"] is False
    delta = diag["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["changed_files"] == 1
    assert delta["snapshot_head"] == SNAPSHOT
    assert delta["predecessor_head"] == PREVSNAP
    assert "product/query/counter_evidence_span.py" in \
        delta["changed_paths_sample"]
    assert diag["adjudication"]["status"] == "UNADJUDICATED"


def test_flat_diagnosis_and_delta_are_substantive():
    flat = json.loads(FLAT.read_text(encoding="utf-8"))
    assert flat["run_id"] == RESUME
    assert flat["classification"] == \
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    assert flat["mechanism"]["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert flat["audit"]["independent_audit_step_seconds"] == 2705.0
    ds = json.loads(DELTA.read_text(encoding="utf-8"))
    assert ds["run_id"] == RESUME
    assert ds["delta_substance"] == "SUBSTANTIVE"
    assert ds["product_work"] is True
    assert ds["changed_files"] == 1
    assert "product/query/counter_evidence_span.py" in ds["substantive_files"]


def test_predecessor_quantum_death_preserved():
    assert PRED_RAW.is_file() and PRED_FLAT.is_file() and PRED_DELTA.is_file()
    flat = json.loads(PRED_FLAT.read_text(encoding="utf-8"))
    assert flat["run_id"] == PRED_RUN
    assert flat["classification"] == \
        "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert flat["mechanism"]["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert flat["team"]["failed_step_seconds"] == 2705.0
    assert flat["team"]["team_snapshot_persisted_after_failed_team_job"] is True
    assert flat["audit"]["conclusion"] == "skipped"
    ds = json.loads(PRED_DELTA.read_text(encoding="utf-8"))
    assert ds["run_id"] == PRED_RUN
    assert ds["delta_substance"] == "SUBSTANTIVE"
    assert ds["product_work"] is True
    assert ds["changed_files"] == 39
    assert len(ds["substantive_files"]) == 3


def test_overbroad_supplement_is_gone_and_predicate_set_is_closed():
    text = (ROOT / "product" / "query" / "counter_evidence_span.py").read_text(
        encoding="utf-8")
    assert "_LEADHEAD_INDICATORS" not in text
    assert "closed" in text.lower()
    assert "removed in cycle 40840720468" in text
    # Behaviour pin: substantive court words at offset >= the frozen letterhead
    # zone are sound, and the same quote at offset 0 yields exactly one D2.
    import sys
    sys.path.insert(0, str(ROOT))
    from product.query import counter_evidence_span as ces
    quote = ("Das Gericht hat erwogen, dass die Kundigung des Mietvertrags "
             "nach Art. 271 OR unwirksam ist.")
    row = {
        "decision_id": "SYN_SUBSTANTIVE_COURT_WORD",
        "language": "de",
        "snippet": "",
        "regeste": "",
        "full_text": ("Pad. " * 200) + quote + " Fortsetzung.",
    }
    assert ces.ground_evidence(quote, row)[1] >= ces.LETTERHEAD_ZONE_OFFSET_MAX
    assert ces.frozen_content_defects(quote, row) == []
    assert ces.passes_content_filter(quote, row) == (True, "")
    head_row = dict(row, full_text=quote + " " + ("Pad. " * 200))
    assert ces.frozen_content_defects(quote, head_row) == [
        "D2_letterhead_zone"]


def test_profile_registered_and_cross_validated():
    import sys
    sys.path.insert(0, str(ROOT))
    from product.audit_readiness import PROFILES, select_profile
    assert RUN in PROFILES
    prof = select_profile(RUN)
    assert prof["resumed_run_id"] == RESUME
    assert prof["predecessor_run_id"] == PRED_RUN
    assert prof["failed_job"] == "audit"
    assert prof["mechanism_kind"] == "observed"
    assert prof["delta_kind"] == "committed"
    assert prof["changed_files"] == 1
    assert prof["exit_code"] == 78
    assert prof["quantum_seconds"] == 2700
    assert prof["state_block"] == "cycle_40840720468_operational_resume"
    assert prof["content_family_expected"] == {
        "n_bundles": 63,
        "n_decisions": 6300,
        "n_verified": 82,
        "n_verified_defective": 0,
        "false_reject_count": 0,
    }
    extras = {str(Path(x)) for x in prof["extra_claim_artifacts"]}
    for path in (RAW, FLAT, DELTA, PRED_RAW, PRED_FLAT, PRED_DELTA):
        assert str(path) in extras


def test_vf_non_rotting_repair_of_prior_cycle_test():
    """The prior cycle test pinned the rotating audit_route pointer; this
    cycle disclosed and applied the same non-rotting repair."""
    path = ROOT / "product" / "tests" / "test_cycle_40823586491.py"
    text = path.read_text(encoding="utf-8")
    assert "DISCLOSED MAINTENANCE REPAIR (cycle 40840720468)" in text
    assert 'CYCLE_40823586491_AUDIT_ROUTE.json' in text
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('assert state["audit_route"]["artifact"] =='):
            raise AssertionError(
                "the rotating equality is live again; keep it preserved "
                "only as an inline comment"
            )


def test_report_and_claims_match_the_committed_artifacts():
    assert REPORT.is_file()
    text = " ".join(REPORT.read_text(encoding="utf-8").split())
    for needle in (RUN, RESUME, PRED_RUN, SNAPSHOT[:8], PREVSNAP[:8],
                   ACCEPTED[:8], "2705.0 s", "exit 78",
                   "OBSERVED_QUANTUM_EXPIRED", "_LEADHEAD_INDICATORS",
                   "UNADJUDICATED", "PASS", "70 assertions",
                   "63 bundles / 6300 decisions / 82 verified",
                   "0 verified+defective", "false rejects",
                   "DO-NOT-SERVE"):
        assert needle in text, needle


def test_content_family_matches_committed_artifact():
    assert CONTENT_FAMILY.is_file()
    doc = json.loads(CONTENT_FAMILY.read_text(encoding="utf-8"))
    assert doc["run_id"] == RUN
    assert doc["direction_version"] == 68
    fixed = doc["fixed_path_family"]["totals"]
    assert fixed["n_bundles"] == 63
    assert fixed["n_decisions"] == 6300
    assert fixed["n_verified"] == 82
    assert fixed["n_verified_defective"] == 0
    assert fixed["defect_histogram"] == {
        "D1_empty_evidence": 0,
        "D2_letterhead_zone": 0,
        "D3_markup_residue": 0,
        "D4_language_marker_mismatch": 0,
    }
    assert doc["false_reject_count"] == 0
    assert doc["confirmed_set"]["still_verified"] is True
    assert doc["ordered_work_2_success_rule"]["met"] is True
    assert doc["ordered_work_2_full_success_rule"]["met"] is True
    hist = doc["all_committed"]["totals"]["defect_histogram"]
    assert hist["D2_letterhead_zone"] == 44
    assert hist["D3_markup_residue"] == 31
    assert hist["D4_language_marker_mismatch"] == 7


def test_fresh_offline_slice_is_the_committed_bytes():
    assert SLICE_SUMMARY.is_file()
    summary = json.loads(SLICE_SUMMARY.read_text(encoding="utf-8"))
    assert summary["verified"] is True
    assert summary["mode"] == "full_loop"
    assert summary["page_contract"] is True
    assert summary["page_contract_detail"] == "PASS 70 assertions"
    stats = summary["stats"]
    assert stats["n_decisions"] == 100
    assert stats["n_clusters"] == 8
    assert stats["answer_status"] == "ready"
    assert stats["counter_rows"] == 4
    assert stats["geometry_preserved_by_enrich"] is True
    assert stats["fixture_replay"]["network"] == "none"
    assert stats["rows_with_source_url"] == 100


def test_progressive_smoke_is_committed_and_passing():
    assert SMOKE.is_file()
    doc = json.loads(SMOKE.read_text(encoding="utf-8"))
    assert doc["run_id"] == RUN
    assert doc["verdict"] == "PASS"
    assert doc["checks_passed"] == doc["checks_total"] == 23
    assert doc["timings_s"]["server_boot_s"] < 3.0
    assert doc["timings_s"]["start_s"] < 1.0


def test_audit_route_artifact_if_present():
    if ROUTE.exists():
        route = json.loads(ROUTE.read_text(encoding="utf-8"))
        assert route["schema"] == "product-audit-route/1"
        assert route["run_id"] == RUN
        assert route["quantum_budget_s"] == 2700
        assert route["audit_target"]["audit_target_ref"] == \
            f"origin/cycle/core/product/{RUN}/team"
        label = route["snapshot_self_label"]["status"]
        assert label in ("ALIGNED", "ALIGNED_AFTER_WRITE")
        ids = [s["id"] for s in route["steps"]]
        assert "snapshot_self_label" in ids
        assert "state_contract" in ids
        assert "chain_cycle_tests" in ids
        assert "never a verdict" in route["contract"]
        if route.get("mode") != "bootstrap":
            assert route["overall_status"] == "PASS"
            assert route["failed_steps"] == []
            assert route["total_seconds"] < route["quantum_budget_s"]


def test_dossier_generated_if_present():
    if DOSSIER.exists():
        dossier = json.loads(DOSSIER.read_text(encoding="utf-8"))
        assert dossier["run_id"] == RUN
        assert dossier["resumed_run_id"] == RESUME
        assert dossier["predecessor_run_id"] == PRED_RUN
        assert dossier["overall_status"] == "PASS"
        assert dossier["failed_checks"] == []
        assert dossier["skipped_checks"] == []
        check = next(c for c in dossier["checks"]
                     if c["id"] == "resumed_diagnosis")
        assert check["status"] == "PASS"
        assert check["detail"]["mechanism_kind"] == "observed"
        hashes = next(c for c in dossier["checks"]
                      if c["id"] == "claim_artifacts")["detail"]["sha256"]
        for path in (RAW, FLAT, DELTA, DIAG, PRED_RAW, PRED_FLAT, PRED_DELTA):
            assert str(path.relative_to(ROOT)) in hashes
