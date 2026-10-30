#!/usr/bin/env python3
"""Pins the operational resume of the 41006386119 snapshot by 41015062553.

Run 41006386119's TEAM job was fully green (state validation and write scope
passed; snapshot persisted at 1148dbdb) and its AUDIT 'Independent audit'
step was then stopped by the workflow's own 2700 s work quantum (2704.0 s,
exit 78, LEX_WORK_QUANTUM_EXPIRED pid=2495) before writing a gate; the
gate/persist steps were skipped and the run is UNADJUDICATED.

Its predecessor, producer run 41004755021, crossed producer write scope: its
lane-cycle step succeeded, then 'Enforce lane write scope' failed (exit 3,
'lane crossed protected scope:') because it had minted an auditor-namespace
PASS gate and report for 40997039714 plus a state block citing that PASS. The
always-run persist step published the tree anyway.

This cycle classifies both failures, repairs the producer write-scope branch
of product/audit_step_diagnosis.py, disowns the minted artifacts in place,
retracts the false state block (preserving its claims verbatim), re-verifies
the inherited v68 deliverable, and re-keys state/report/test/profile/dossier/
route/intake to 41015062553.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state" / "product.json"
ORCH = ROOT / "results" / "product" / "orchestration"
AR = ROOT / "results" / "product" / "audit_readiness"
REPORT = ROOT / "reports" / "product" / "CYCLE_41015062553.md"
RAW = ORCH / "CYCLE_41006386119_run_jobs_raw.json"
FLAT = ORCH / "CYCLE_41006386119_audit_step_diagnosis.json"
DIAG = ORCH / "CYCLE_41006386119_resume_diagnosis.json"
DELTA = ORCH / "CYCLE_41006386119_delta_substance.json"
PRED_RAW = ORCH / "CYCLE_41004755021_run_jobs_raw.json"
PRED_FLAT = ORCH / "CYCLE_41004755021_audit_step_diagnosis.json"
PRED_DIAG = ORCH / "CYCLE_41004755021_resume_diagnosis.json"
PRED_DELTA = ORCH / "CYCLE_41004755021_delta_substance.json"
CONTENT_FAMILY = (ROOT / "results" / "product" / "counter_content_family"
                  / "CYCLE_41015062553.json")
SMOKE = (ROOT / "results" / "product" / "progressive_smoke"
         / "CYCLE_41015062553_progressive_smoke.json")
SLICE = ROOT / "results" / "product" / "offline_slice" / "20261030T061500Z"
LIVE = ROOT / "results" / "product" / "live_slice"
LIVE_BUNDLE = ROOT / "results" / "product" / "query_result_bundle_live.json"
INCIDENT = (ROOT / "reports" / "product" / "incidents"
            / "self_minted_gate_40997039714.DISOWNED.json")
MINTED_GATE = ROOT / "results" / "audit" / "product" / "CYCLE_40997039714_GATE.json"
MINTED_REPORT = ROOT / "reports" / "audit" / "product" / "CYCLE_40997039714.md"
DOSSIER = AR / "CYCLE_41015062553_audit_readiness.json"
ROUTE = AR / "CYCLE_41015062553_AUDIT_ROUTE.json"
INTAKE = AR / "CYCLE_41015062553_AUDIT_INTAKE.md"
RUN = "41015062553"
RESUME = "41006386119"
PRED_RUN = "41004755021"
SNAPSHOT = "1148dbdb6e3dd67300e5702e1a76a31eb6a870bb"
PREVSNAP = "f78d43d20e5c546fc335b4d1f8fcee740e8fbc05"
ACCEPTED = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    assert "SUCCESS" in rf["team_job"] and "1148dbdb" in rf["team_job"]
    assert "2704.0 s" in rf["audit_job"]
    assert "exit 78" in rf["audit_job"]
    assert "OBSERVED_QUANTUM_EXPIRED" in rf["mechanism"]
    assert "pid=2495" in rf["mechanism"]
    assert "not a product defect" in rf["mechanism"]
    assert rf["gate_file_written"] is False
    assert rf["adjudication"] == "UNADJUDICATED"
    assert "22 changed files" in rf["durable_delta"]

    pf = block["predecessor_failure"]
    assert pf["classification"] == "TEAM_JOB_SCOPE_ENFORCEMENT_FAILED_NO_GATE"
    assert pf["failed_step"] == "Enforce lane write scope"
    assert pf["exit_code"] == 3
    assert "lane crossed protected scope" in pf["annotation"]
    assert pf["lane_cycle_step"] == "success"
    assert pf["audit_gate_for_this_run"] is False
    assert pf["self_minted_audit_artifacts"] is True
    assert pf["adjudication"] == "UNADJUDICATED"

    dis = block["self_minted_gate_disowned"]
    assert dis["authored_by"].startswith(PREVSNAP)
    assert dis["disposition"] == "DISOWNED_IN_PLACE_UNRETIRED"
    assert dis["false_state_block"] == \
        "cycle_40997039714_vertical_slice_delivery (retracted)"
    assert dis["incident_record"] == str(INCIDENT.relative_to(ROOT))

    assert block["snapshot_audit_readiness"]["state_advanced"] is True
    assert block["posture"]["continue_recommended"] is True
    assert block["posture"]["human_gate_ready"] is False
    assert block["posture"]["do_not_serve_orders"] == "IN_FORCE"
    assert state["audit_route"]["artifact"] == \
        f"results/product/audit_readiness/CYCLE_{RUN}_AUDIT_ROUTE.json"
    # Append-only predecessors and their reports must survive.
    assert state["cycle_40997039714_operational_resume"]
    assert state["cycle_40990419541_operational_resume"]
    assert (ROOT / "reports" / "product" / "CYCLE_40997039714.md").is_file()


def test_false_delivery_block_is_retracted_with_claims_preserved():
    state = _json(STATE)
    block = state["cycle_40997039714_vertical_slice_delivery"]
    assert block["retracted"] is True
    assert block["retracted_by_run_id"] == RUN
    assert block["source_of_false_claim"]["commit"] == PREVSNAP
    assert "audit gate" in " ".join(block["do_not_cite"]).lower()
    # The retraction does not delete the historical claim: it is preserved.
    old = block["original_claims_preserved"]
    assert old["delivered"] is True
    assert any("audit gate: PASS" in c
               for c in old["delivered_components"])
    # The minted files are still identified by their exact committed bytes.
    gates = {a["path"]: a for a in block["self_minted_artifacts"]}
    assert gates["results/audit/product/CYCLE_40997039714_GATE.json"]["sha256"] \
        == _sha256(MINTED_GATE)
    assert gates["reports/audit/product/CYCLE_40997039714.md"]["sha256"] \
        == _sha256(MINTED_REPORT)
    # What is actually measured contradicts the minted report's 8 cited / 5
    # counter rows.
    actual = block["what_is_actually_measured"]
    assert actual["live_bundle"]["cited_decision_ids"] == [
        "bge_133 III 61", "bge_144 III 346"]
    assert actual["live_bundle"]["counter_authority"] is None
    assert actual["live_map_only"]["stages_executed"]["answer"] is False
    assert actual["live_map_only"]["stages_executed"]["counter_authority"] is False
    assert actual["offline_full_loop"]["verdict"] == "PASS"


def test_run_history_chain_is_append_only():
    hist = {str(e.get("run_id")): e for e in _json(STATE)["run_history"]}
    for run_id in ("40997039714", PRED_RUN, RESUME, RUN):
        assert run_id in hist, run_id
    pred = hist[PRED_RUN]
    assert pred["status"] == (
        "TEAM_WRITE_SCOPE_ENFORCEMENT_FAILED_SELF_MINTED_AUDIT_BYTES_"
        "PUBLISHED_UNADJUDICATED")
    assert pred["orchestration_classification"] == \
        "TEAM_JOB_SCOPE_ENFORCEMENT_FAILED_NO_GATE"
    assert "exit 3" in pred["team_job"]
    assert "41 changed files" in pred["durable_delta"]
    resumed = hist[RESUME]
    assert resumed["status"] == \
        "TEAM_GREEN_AUDIT_QUANTUM_DEATH_NO_GATE_UNADJUDICATED"
    assert "pid=2495" in resumed["audit_job"]
    assert "22 changed files" in resumed["durable_delta"]
    cur = hist[RUN]
    assert cur["resumed_run"] == RESUME
    assert cur["accepted"] is False
    assert cur["accepted_commit"] == ACCEPTED
    assert cur["report_of_record"] == f"reports/product/CYCLE_{RUN}.md"
    assert cur["cycle_test"] == f"product/tests/test_cycle_{RUN}.py"
    assert cur["audit_gate"] == "NONE_YET"
    assert "1148dbdb" in cur["summary"]
    assert "2704.0 s" in cur["summary"]


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
    assert flat["audit"]["independent_audit_step_seconds"] == 2704.0
    assert flat["audit"]["gate_step"] == "skipped"
    assert flat["audit"]["persist_step"] == "skipped"
    assert flat["audit"]["gate_file_written"] is False
    mech = flat["mechanism"]
    assert mech["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert mech["quantum_seconds"] == 2700
    assert mech["exit_code"] == 78
    assert "pid=2495" in mech["claim"]
    assert flat["adjudication"]["product_defect"] is False
    assert flat["adjudication"]["verdict_written"] is False
    diag = _json(DIAG)
    assert diag["run_id"] == RESUME
    assert diag["predecessor_run_id"] == PRED_RUN
    assert diag["durable_delta"]["classification"] == "COMMITTED_DELTA"
    assert diag["durable_delta"]["changed_files"] == 22
    assert diag["durable_delta"]["snapshot_head"] == SNAPSHOT
    assert diag["durable_delta"]["predecessor_head"] == PREVSNAP
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    delta = _json(DELTA)
    assert delta["changed_files"] == 22
    assert delta["delta_substance"] == "SUBSTANTIVE"
    assert delta["product_work"] is True
    assert delta["counts"]["code"] == 1
    assert any("query_map_diagnosis.py" in p
               for p in delta["substantive_files"])
    assert any("20261030T051448Z_bundle.json" in p
               for p in delta["substantive_files"])


def test_predecessor_scope_failure_is_first_class_and_re_derivable():
    for path in (PRED_RAW, PRED_FLAT, PRED_DIAG, PRED_DELTA):
        assert path.is_file(), path
    flat = _json(PRED_FLAT)
    assert flat["run_id"] == PRED_RUN
    assert flat["classification"] == \
        "TEAM_JOB_SCOPE_ENFORCEMENT_FAILED_NO_GATE"
    assert flat["team"]["conclusion"] == "failure"
    assert flat["team"]["failed_step"] == "Enforce lane write scope"
    assert flat["team"]["write_scope_step_conclusion"] == "failure"
    assert flat["team"]["team_snapshot_persisted"] is True
    assert flat["audit"]["conclusion"] == "skipped"
    mech = flat["mechanism"]
    assert mech["status"] == "OBSERVED_TEAM_SCOPE_ENFORCEMENT_FAILED"
    assert mech["quantum_expired"] is False
    assert mech["exit_code"] == 3
    assert "lane crossed protected scope" in mech["claim"]
    assert "WRITE-SCOPE failure" in mech["claim"]
    # The old UNOBSERVED sentence ("the lane-cycle agent process exited
    # non-zero") is false for this class and must not come back.
    assert "lane-cycle agent process exited non-zero" not in mech["claim"]

    # Re-derive from the committed raw snapshot so the repair is pinned by the
    # code path, not only by the committed artifact.
    from product.audit_step_diagnosis import classify
    again = classify(_json(PRED_RAW))
    assert again["classification"] == \
        "TEAM_JOB_SCOPE_ENFORCEMENT_FAILED_NO_GATE"
    assert again["mechanism"]["status"] == \
        "OBSERVED_TEAM_SCOPE_ENFORCEMENT_FAILED"
    assert again["mechanism"]["exit_code"] == 3

    diag = _json(PRED_DIAG)
    assert diag["orchestration"]["classification"] == \
        "TEAM_JOB_SCOPE_ENFORCEMENT_FAILED_NO_GATE"
    assert diag["durable_delta"]["changed_files"] == 41
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    delta = _json(PRED_DELTA)
    assert delta["changed_files"] == 41
    assert delta["delta_substance"] == "SUBSTANTIVE"
    assert any("CYCLE_40997039714_GATE.json" in p
               for p in delta["substantive_files"])


def test_incident_record_disowns_the_minted_gate():
    inc = _json(INCIDENT)
    assert inc["class"] == "CP-AUDIT-SCOPE-4"
    assert inc["authoring_commit"]["sha"] == PREVSNAP
    arts = {a["path"]: a for a in inc["artifacts"]}
    assert set(arts) == {
        "results/audit/product/CYCLE_40997039714_GATE.json",
        "reports/audit/product/CYCLE_40997039714.md",
    }
    assert arts["results/audit/product/CYCLE_40997039714_GATE.json"]["sha256"] \
        == _sha256(MINTED_GATE)
    assert arts["reports/audit/product/CYCLE_40997039714.md"]["sha256"] \
        == _sha256(MINTED_REPORT)
    body = arts["results/audit/product/CYCLE_40997039714_GATE.json"][
        "producer_gate_body"]
    assert body["gate"] == "PASS" and body["safe_to_integrate"] is True
    assert inc["disposition"]["status"] == "DISOWNED_IN_PLACE_UNRETIRED"
    assert inc["disposition"]["files_retired"] is False
    assert "git status --porcelain -uall" in \
        inc["disposition"]["why_not_retired"]
    assert "never cite" in inc["disposition"]["citation_policy"].lower()


def test_fresh_reverification_artifacts():
    summary = _json(SLICE / "summary.json")
    bundle = _json(SLICE / "rent-default.bundle.json")
    assert summary["mode"] == "full_loop"
    assert summary["verified"] is True
    assert summary["degraded"] is False
    assert summary["page_contract"] is True
    assert summary["page_contract_detail"] == "PASS 70 assertions"
    stats = summary["stats"]
    assert stats["fixture_replay"]["network"] == "none"
    assert stats["fixture_replay_cache_misses"] == 0
    assert stats["n_decisions"] == 100
    assert stats["n_clusters"] == 8
    assert stats["rows_with_canonical_url"] == 100
    assert stats["rows_with_xy"] == 100
    assert stats["answer_status"] == "ready"
    assert stats["counter_rows"] == 4
    assert len(bundle["decisions"]) == 100

    fam = _json(CONTENT_FAMILY)
    assert fam["run_id"] == RUN
    totals = fam["fixed_path_family"]["totals"]
    assert totals["n_bundles"] == 71
    assert totals["n_decisions"] == 7100
    assert totals["n_verified"] == 103
    assert totals["n_verified_defective"] == 0
    assert totals["defect_histogram"] == {
        "D1_empty_evidence": 0,
        "D2_letterhead_zone": 0,
        "D3_markup_residue": 0,
        "D4_language_marker_mismatch": 0,
    }
    assert fam["false_reject_count"] == 0
    assert fam["ordered_work_2_success_rule"]["met"] is True
    assert fam["ordered_work_2_full_success_rule"]["met"] is True

    smoke = _json(SMOKE)
    assert smoke["run_id"] == RUN
    assert smoke["checks_passed"] == smoke["checks_total"] == 23
    assert all(c["ok"] for c in smoke["checks"])


def test_live_map_only_slices_and_bundle_bytes():
    from product.query.bundle import validate_bundle
    for stamp, largest in (("20261030T051448Z", 27), ("20261030T052106Z", 23)):
        rec = _json(LIVE / f"{stamp}.json")
        assert rec["run_id"]
        assert rec["mode"] == "map_only"
        assert rec["verdict"] == "PASS_MAP_ONLY"
        assert rec["stages_executed"]["retrieval"] is True
        assert rec["stages_executed"]["map"] is True
        assert rec["stages_executed"]["answer"] is False
        assert rec["stages_executed"]["counter_authority"] is False
        assert rec["n_failed_checks"] == ["canonical_chain_ran"]
        assert rec["map"]["n_decisions"] == 100
        assert rec["map"]["n_clusters"] == 8
        assert rec["map"]["largest_cluster"] == largest
        assert rec["map"]["rows_with_xy"] == 100
        assert rec["map"]["rows_with_source_url"] == 100
        assert rec["page_contract"]["ok"] is True
        bundle = _json(LIVE / f"{stamp}_bundle.json")
        assert validate_bundle(bundle) == []
        assert len(bundle["decisions"]) == 100

    lb = _json(LIVE_BUNDLE)
    assert validate_bundle(lb) == []
    assert len(lb["decisions"]) == 100
    assert lb["answer"]["method"] == "generative_audit_llm_v2"
    cites = {s["decision_id"] for s in lb["answer"]["statements"]}
    assert cites == {"bge_133 III 61", "bge_144 III 346"}
    assert lb.get("counter_authority") is None


def test_report_and_cycle_test_are_addressable():
    assert REPORT.is_file()
    text = REPORT.read_text(encoding="utf-8")
    assert "CYCLE_40284658455" in text
    assert "DO-NOT-SERVE" in text
    assert "UNADJUDICATED" in text
    assert "2704.0 s" in text
    assert "pid=2495" in text
    assert "22 changed files" in text or "22-file" in text
    assert "lane crossed protected scope" in text
    assert "DISOWNED_IN_PLACE_UNRETIRED" in text or "disowned in place" in text
    assert "retracted" in text
    assert "not a product defect" in text
    assert Path(__file__).is_file()


def test_no_producer_minted_gate_for_this_run():
    assert not (ROOT / "results" / "audit" / "product"
                / f"CYCLE_{RUN}_GATE.json").exists()
    assert not (ROOT / "reports" / "audit" / "product"
                / f"CYCLE_{RUN}.md").exists()


def test_dossier_generated_if_present():
    # Conditional on presence: this is the first-generation fixpoint break.
    # audit_readiness.py runs this cycle test while generating the dossier, so
    # the dossier cannot exist when the test first executes.
    if not DOSSIER.exists():
        return
    dossier = _json(DOSSIER)
    assert dossier["run_id"] == RUN
    assert dossier["direction_version"] == 68
    check = next(c for c in dossier["checks"]
                 if c["id"] == "resumed_diagnosis")
    # Pin the dossier's static claims, not the pass/fail status of the
    # previous file: this test runs INSIDE dossier generation, so asserting
    # the old file's status would deadlock the first generation.  The
    # status is enforced by the dossier itself and by --verify.
    assert check["detail"]["mechanism_kind"] == "observed"
    assert check["detail"]["delta_kind"] == "committed"
    assert check["detail"]["changed_files"] == 22


def test_audit_route_artifact_if_present():
    if not ROUTE.exists():
        return
    route = _json(ROUTE)
    assert route["schema"] == "product-audit-route/1"
    assert route["run_id"] == RUN
    assert route["quantum_budget_s"] == 2700
    assert route["audit_target"]["audit_target_ref"] == \
        f"origin/cycle/core/product/{RUN}/team"
    assert route["snapshot_self_label"]["status"] in (
        "ALIGNED", "ALIGNED_AFTER_WRITE")
    ids = [s["id"] for s in route["steps"]]
    for step in ("snapshot_self_label", "state_contract",
                 "chain_cycle_tests"):
        assert step in ids
    assert "never a verdict" in route["contract"]


def test_intake_artifact_if_present():
    if not INTAKE.exists():
        return
    text = INTAKE.read_text(encoding="utf-8")
    assert f"AUDIT INTAKE — product run {RUN}" in text
    assert f"origin/cycle/core/product/{RUN}/team" in text
    assert "UPPERCASE" in text or "_GATE.json" in text
