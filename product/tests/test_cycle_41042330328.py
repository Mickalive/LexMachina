#!/usr/bin/env python3
"""Pins the operational resume of the 41032950199 snapshot by 41042330328.

Run 41032950199's TEAM job was fully green (state validation and write scope
passed; snapshot persisted at 37fdb227) and its AUDIT 'Independent audit' step
was then stopped by the workflow's own 2700 s work quantum (2705.0 s, exit 78,
LEX_WORK_QUANTUM_EXPIRED pid=2496) before writing a gate; gate/persist were
skipped and the run is UNADJUDICATED.

This cycle captures/classifies the failure, preserves the inherited
absent-vs-defective incumbent repair and four flagship slices, re-verifies the
served path, progressive smoke and the content family on the snapshot's own
bytes, and re-keys the audit surface to 41042330328.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state" / "product.json"
ORCH = ROOT / "results" / "product" / "orchestration"
AR = ROOT / "results" / "product" / "audit_readiness"
REPORT = ROOT / "reports" / "product" / "CYCLE_41042330328.md"
RAW = ORCH / "CYCLE_41032950199_run_jobs_raw.json"
FLAT = ORCH / "CYCLE_41032950199_audit_step_diagnosis.json"
DIAG = ORCH / "CYCLE_41032950199_resume_diagnosis.json"
DELTA = ORCH / "CYCLE_41032950199_delta_substance.json"
CONTENT_FAMILY = (ROOT / "results" / "product" / "counter_content_family"
                  / "CYCLE_41042330328.json")
SMOKE = (ROOT / "results" / "product" / "progressive_smoke"
         / "CYCLE_41042330328_progressive_smoke.json")
SLICE_ROOT = ROOT / "results" / "product" / "offline_slice"
SLICE_STAMP = "20261030T093031Z"
SERVER = ROOT / "results" / "product" / "server_slice" / "41042330328"
DOSSIER = AR / "CYCLE_41042330328_audit_readiness.json"
ROUTE = AR / "CYCLE_41042330328_AUDIT_ROUTE.json"
INTAKE = AR / "CYCLE_41042330328_AUDIT_INTAKE.md"
RUN = "41042330328"
RESUME = "41032950199"
PRED_RUN = "41023710274"
SNAPSHOT = "37fdb22783a7102332d90028fc58983441858950"
PREVSNAP = "4796618e1bda6e321832549daf4deec70ccef3a9"
ACCEPTED = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
GATE = ROOT / "results" / "audit" / "product" / f"CYCLE_{RUN}_GATE.json"
AUDIT_REPORT = ROOT / "reports" / "audit" / "product" / f"CYCLE_{RUN}.md"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_state_pointer_posture_and_cycle_block():
    state = _json(STATE)
    assert state["accepted_run_id"] == "CYCLE_40284658455"
    assert state["accepted_commit"] == ACCEPTED
    for key in ("current_cycle_run_id", "current_run", "current_run_id"):
        assert state[key] == RUN, key
    assert state["direction_version"] == 68
    assert state["cycle_status"] == "COMPLETE"
    assert state["continue_recommended"] is True
    assert state["human_gate_ready"] is False
    assert state["machine_gate_ready"] is False
    assert state["ready_for_owner_session"] is False
    assert state["packet_admitted"] is False
    assert state["owner_decision_required"] is False

    block = state[f"cycle_{RUN}_operational_resume"]
    assert block["run_id"] == RUN
    assert block["resumed_run_id"] == RESUME
    assert block["predecessor_run_id"] == PRED_RUN
    assert block["resumed_snapshot_head"] == SNAPSHOT
    assert block["predecessor_snapshot_head"] == PREVSNAP
    assert block["adjudication"] == "UNADJUDICATED"
    assert block["diagnosis_of_resumed"] == \
        f"results/product/orchestration/CYCLE_{RESUME}_resume_diagnosis.json"

    rf = block["resumed_failure"]
    assert rf["classification"] == \
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    assert "SUCCESS" in rf["team_job"] and "37fdb227" in rf["team_job"]
    assert "2705.0 s" in rf["audit_job"]
    assert "exit 78" in rf["audit_job"]
    assert "OBSERVED_QUANTUM_EXPIRED" in rf["mechanism"]
    assert "pid=2496" in rf["mechanism"]
    assert "not a product defect" in rf["mechanism"]
    assert rf["gate_file_written"] is False
    assert rf["adjudication"] == "UNADJUDICATED"
    assert "26 changed files" in rf["durable_delta"]

    rep = block["inherited_repair"]
    assert rep["artifact"] == "product/query/counter_evidence_span.py"
    assert set(rep["states"]) == {"absent", "fails", "sound"}
    assert rep["targeted_suite"] == "16 passed (test_counter_incumbent_rejection_v68.py + test_cycle_41032950199.py)"
    assert block["snapshot_audit_readiness"]["state_advanced"] is True
    assert block["posture"]["continue_recommended"] is True
    assert block["posture"]["human_gate_ready"] is False
    assert block["posture"]["do_not_serve_orders"] == "IN_FORCE"
    assert state["audit_route"]["artifact"] == \
        f"results/product/audit_readiness/CYCLE_{RUN}_AUDIT_ROUTE.json"
    assert state["cycle_41032950199_operational_resume"]
    assert (ROOT / "reports" / "product" / "CYCLE_41032950199.md").is_file()


def test_run_history_chain_is_append_only():
    hist = {str(e.get("run_id")): e for e in _json(STATE)["run_history"]}
    for run_id in (PRED_RUN, RESUME, RUN):
        assert run_id in hist, run_id
    resumed = hist[RESUME]
    assert resumed["audit_gate"] == "NONE_YET"
    assert "37fdb227" not in resumed["summary"]  # that entry predates this snapshot
    cur = hist[RUN]
    assert cur["resumed_run"] == RESUME
    assert cur["accepted"] is False
    assert cur["accepted_commit"] == ACCEPTED
    assert cur["report_of_record"] == f"reports/product/CYCLE_{RUN}.md"
    assert cur["cycle_test"] == f"product/tests/test_cycle_{RUN}.py"
    assert cur["audit_gate"] == "NONE_YET"
    assert "37fdb227" in cur["summary"]
    assert "2705.0 s" in cur["summary"]
    assert "pid=2496" in cur["audit_job"]


def test_resumed_orchestration_is_observed_audit_quantum_expiry():
    for path in (RAW, FLAT, DIAG, DELTA):
        assert path.is_file(), path
    raw = _json(RAW)
    assert raw["run"]["id"] == int(RESUME)
    assert raw["run"]["conclusion"] == "failure"
    jobs = {j["name"]: j for j in raw["jobs"]}
    assert jobs["team"]["conclusion"] == "success"
    assert jobs["audit"]["conclusion"] == "failure"
    assert jobs["integrate"]["conclusion"] == "skipped"
    flat = _json(FLAT)
    assert flat["run_id"] == RESUME
    assert flat["classification"] == \
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    assert flat["team"]["conclusion"] == "success"
    assert flat["team"]["producer_state_validation_step_conclusion"] == "success"
    assert flat["team"]["write_scope_step_conclusion"] == "success"
    assert flat["audit"]["failed_step"] == "Independent audit"
    assert flat["audit"]["independent_audit_step_seconds"] == 2705.0
    assert flat["audit"]["gate_step"] == "skipped"
    assert flat["audit"]["persist_step"] == "skipped"
    assert flat["audit"]["gate_file_written"] is False
    mech = flat["mechanism"]
    assert mech["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert mech["quantum_seconds"] == 2700
    assert mech["exit_code"] == 78
    assert "pid=2496" in mech["claim"]
    assert flat["adjudication"]["product_defect"] is False
    assert flat["adjudication"]["verdict_written"] is False
    diag = _json(DIAG)
    assert diag["run_id"] == RESUME
    assert diag["predecessor_run_id"] == PRED_RUN
    assert diag["durable_delta"]["classification"] == "COMMITTED_DELTA"
    assert diag["durable_delta"]["changed_files"] == 26
    assert diag["durable_delta"]["snapshot_head"] == SNAPSHOT
    assert diag["durable_delta"]["predecessor_head"] == PREVSNAP
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    delta = _json(DELTA)
    assert delta["changed_files"] == 26
    assert delta["delta_substance"] == "SUBSTANTIVE"
    assert delta["product_work"] is True
    assert delta["counts"] == {
        "code": 4,
        "report": 1,
        "results_artifact": 20,
        "state": 1,
    }
    assert any("20261030T093031Z" in p for p in delta["substantive_files"])


def test_inherited_absent_incumbent_repair_is_preserved():
    from product.query import counter_evidence_span as ces
    assert ces._incumbent_content_failure({"counter_evidence": ""}) == (
        False, [], None)
    assert ces._incumbent_content_state({"counter_evidence": "  "})[0] == "absent"
    bundle = _json(SLICE_ROOT / f"{SLICE_STAMP}-rent-default"
                   / "rent-default.bundle.json")
    stale = [d for d in bundle["decisions"]
             if d.get("counter_evidence_verified") is not True
             and d.get("counter_evidence_unevidenced") is True
             and not str(d.get("counter_evidence") or "").strip()]
    assert stale == []
    prov = bundle["provenance"]["counter_evidence_span_surface"]
    assert prov["n_downgraded"] == 0
    assert prov["n_incumbent_downgraded"] == 0
    assert all(a["incumbent_downgraded"] is False for a in prov["abstained"])
    assert all(a["incumbent_state"] in {"absent", "sound"}
               for a in prov["abstained"])


def test_four_inherited_flagship_slices_are_verified():
    expected = {
        "rent-default": (4, 4, 70),
        "petty-theft-dismissal": (3, 1, 70),
        "corporate-criminal-liability": (2, 6, 69),
        "business-judgment-rule": (3, 1, 71),
    }
    for slug, (cited, counters, assertions) in expected.items():
        summary = _json(SLICE_ROOT / f"{SLICE_STAMP}-{slug}" / "summary.json")
        assert summary["verified"] is True, slug
        assert summary["mode"] == "full_loop", slug
        assert summary["degraded"] is False, slug
        assert summary["page_contract"] is True, slug
        assert summary["page_contract_detail"] == \
            f"PASS {assertions} assertions", slug
        stats = summary["stats"]
        assert stats["n_decisions"] == 100, slug
        assert stats["n_clusters"] == 8, slug
        assert stats["answer_status"] == "ready", slug
        assert stats["cited_decision_ids"] == cited, slug
        assert stats["counter_rows"] == counters, slug
        assert stats["rows_with_xy"] == 100, slug
        assert stats["rows_with_canonical_url"] == 100, slug
        assert stats["geometry_preserved_by_enrich"] is True, slug
        assert stats["fixture_replay"]["network"] == "none", slug
        assert stats["fixture_replay_cache_misses"] == 0, slug


def test_served_path_and_progressive_smoke_are_green():
    served = _json(SERVER / "summary.json")
    assert served["verdict"] == "PASS"
    assert served["failures"] == []
    assert served["counts"]["n_first_page"] == 100
    assert served["counts"]["n_final"] == 100
    assert served["counts"]["n_clusters_final"] == 8
    assert served["counts"]["n_cited"] == 2
    assert served["counts"]["counter_authorities"] == 1
    assert served["counts"]["rows_with_source_url"] == 100
    assert served["counts"]["page_contract_assertions"] == 71
    assert served["timing_s"]["total_s"] < 5.0
    smoke = _json(SMOKE)
    assert smoke["run_id"] == RUN
    assert smoke["verdict"] == "PASS"
    assert smoke["checks_passed"] == smoke["checks_total"] == 23
    assert smoke["timings_s"]["server_boot_s"] < 3.0
    assert smoke["timings_s"]["start_s"] < 1.0


def test_content_family_reverification_is_zero_defect():
    fam = _json(CONTENT_FAMILY)
    assert fam["run_id"] == RUN
    totals = fam["fixed_path_family"]["totals"]
    assert totals["n_bundles"] == 81
    assert totals["n_decisions"] == 8100
    assert totals["n_verified"] == 127
    assert totals["n_verified_defective"] == 0
    assert totals["defect_histogram"] == {
        "D1_empty_evidence": 0,
        "D2_letterhead_zone": 0,
        "D3_markup_residue": 0,
        "D4_language_marker_mismatch": 0,
    }
    assert fam["false_reject_count"] == 0
    assert fam["confirmed_set"]["still_verified"] is True
    assert fam["ordered_work_2_success_rule"]["met"] is True
    assert fam["ordered_work_2_full_success_rule"]["met"] is True
    historical = fam["all_committed"]["totals"]
    assert historical["n_bundles"] == 184
    assert historical["defect_histogram"]["D2_letterhead_zone"] == 44
    assert historical["defect_histogram"]["D3_markup_residue"] == 31
    assert historical["defect_histogram"]["D4_language_marker_mismatch"] == 7


def test_audit_surface_exists_and_no_gate_was_minted():
    assert REPORT.is_file()
    assert not GATE.exists()
    assert not AUDIT_REPORT.exists()


def test_dossier_generated_if_present():
    # Conditional on presence: audit_readiness.py runs this cycle test while
    # generating the dossier, so the dossier cannot exist on first generation.
    if not DOSSIER.exists():
        return
    dossier = _json(DOSSIER)
    assert dossier["run_id"] == RUN
    assert dossier["direction_version"] == 68
    assert dossier["overall_status"] in {"PASS", "PARTIAL"}
    assert dossier["resumed_run"]["classification"] == \
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    assert dossier["resumed_run"]["adjudication"] == "UNADJUDICATED"
    check = next(c for c in dossier["checks"]
                 if c["id"] == "resumed_diagnosis")
    assert check["detail"]["mechanism_kind"] == "observed"
    assert check["detail"]["delta_kind"] == "committed"
    assert check["detail"]["changed_files"] == 26


def test_audit_route_and_intake_if_present():
    if ROUTE.exists():
        route = _json(ROUTE)
        assert route["schema"] == "product-audit-route/1"
        assert route["run_id"] == RUN
        assert route["quantum_budget_s"] == 2700
        assert route["audit_target"]["audit_target_ref"] == \
            f"origin/cycle/core/product/{RUN}/team"
        assert route["snapshot_self_label"]["status"] in (
            "ALIGNED", "ALIGNED_AFTER_WRITE")
        ids = [s["id"] for s in route["steps"]]
        for step in ("snapshot_self_label", "state_contract"):
            assert step in ids
        assert "never a verdict" in route["contract"]
    if INTAKE.exists():
        text = INTAKE.read_text(encoding="utf-8")
        assert f"AUDIT INTAKE — product run {RUN}" in text
        assert f"origin/cycle/core/product/{RUN}/team" in text
        assert "UPPERCASE" in text or "_GATE.json" in text


def test_report_matches_the_committed_artifacts():
    body = REPORT.read_text(encoding="utf-8")
    assert "37fdb227" in body
    assert "2705.0 s" in body
    assert "pid=2496" in body
    assert "81 bundles / 8100 decisions / 127 verified rows" in body
    assert "0 verified+defective" in body
    assert "UNADJUDICATED" in body
    assert "AUDIT_READY_UNADJUDICATED" in body
    assert "Claim ceiling" in body
