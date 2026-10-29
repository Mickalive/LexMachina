#!/usr/bin/env python3
"""Pins the operational resume of run 40820909501 by run 40823586491.

Run 40820909501's TEAM job failed in "Run lane cycle" after 1534.0 s with
exit code 1.  Unlike the earlier UNOBSERVED chain links, its public check-run
annotations record the workflow wrapper's own provider/network sentinels
(LEX_MODEL_AUTH_FAILURE quarantining big-pickle, LEX_MODEL_ROTATE to
beam-free, LEX_NETWORK_STALL), so the mechanism is classified
OBSERVED_PROVIDER_NETWORK_ANNOTATIONS: the agent died AFTER writing the
durable v68 deliverable into the tree, and the always-run persist step then
committed that tree at 42e58db2 (SUBSTANTIVE, 19 files, product_work=true)
while state validation and write scope were skipped and the audit job never
ran.

This cycle re-verifies the inherited deliverable in place, extends the
diagnosis classifier with the observed provider/network mechanism class,
applies the disclosed non-rotting audit_route repair to
test_cycle_40820909501.py, and re-keys state/report/test/dossier/route/
intake to 40823586491.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state" / "product.json"
ORCH = ROOT / "results" / "product" / "orchestration"
AR = ROOT / "results" / "product" / "audit_readiness"
REPORT = ROOT / "reports" / "product" / "CYCLE_40823586491.md"
DIAG = ORCH / "CYCLE_40820909501_resume_diagnosis.json"
FLAT_DIAG = ORCH / "CYCLE_40820909501_audit_step_diagnosis.json"
RAW = ORCH / "CYCLE_40820909501_run_jobs_raw.json"
DELTA = ORCH / "CYCLE_40820909501_delta_substance.json"
DOSSIER = AR / "CYCLE_40823586491_audit_readiness.json"
ROUTE = AR / "CYCLE_40823586491_AUDIT_ROUTE.json"
INTAKE = AR / "CYCLE_40823586491_AUDIT_INTAKE.md"
CONTENT_FAMILY = (ROOT / "results" / "product" / "counter_content_family"
                  / "CYCLE_40823586491.json")
SLICE_SUMMARY = (ROOT / "results" / "product" / "offline_slice"
                 / "20261029T053917Z" / "summary.json")
SMOKE = (ROOT / "results" / "product" / "progressive_smoke"
         / "CYCLE_40823586491_progressive_smoke.json")
ACCEPTED = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
SNAPSHOT = "42e58db2f651f6f8fbb263c6946da33fa2300399"
PREDSNAP = "bed9a21827b1f2d9ffb14d98cc5d19fe382590cb"
RUN = "40823586491"
RESUME = "40820909501"
PRED_RUN = "40820694435"
SENTINELS = ("LEX_MODEL_AUTH_FAILURE", "LEX_MODEL_ROTATE", "LEX_NETWORK_STALL")


def test_state_pointer_and_posture_non_rotting():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    assert state["accepted_run_id"] == "CYCLE_40284658455"
    assert state["accepted_commit"] == ACCEPTED
    # The pointer rotates by design; this cycle's own block carries the pin.
    assert state["current_cycle_run_id"]
    assert state["current_run"]
    assert state["current_run_id"]
    assert state["continue_recommended"] is True
    assert state["human_gate_ready"] is False
    assert state["machine_gate_ready"] is False
    assert state["ready_for_owner_session"] is False
    assert state["packet_admitted"] is False
    assert state["owner_decision_required"] is False
    assert state["direction_version"] == 68
    block = state["cycle_40823586491_operational_resume"]
    assert block["run_id"] == RUN
    assert block["resumed_run_id"] == RESUME
    assert block["predecessor_run_id"] == PRED_RUN
    assert block["resumed_snapshot_head"] == SNAPSHOT
    assert block["diagnosis_of_resumed"] == \
        "results/product/orchestration/CYCLE_40820909501_resume_diagnosis.json"
    rf = block["resumed_failure"]
    assert rf["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert "1534.0 s" in rf["team_job"]
    assert "OBSERVED_PROVIDER_NETWORK_ANNOTATIONS" in rf["mechanism"]
    assert rf["gate_file_written"] is False
    assert rf["adjudication"] == "UNADJUDICATED"
    assert "SUBSTANTIVE" in rf["durable_delta"]
    assert "19" in rf["durable_delta"]
    ext = block["classifier_extension"]
    assert "OBSERVED_PROVIDER_NETWORK_ANNOTATIONS" in ext["audit_step_diagnosis"]
    assert "observed_provider_network" in ext["audit_readiness"]
    assert "DISCLOSED" in ext["non_rotting_repair"]
    assert block["snapshot_audit_readiness"]["state_advanced"] is True
    assert block["posture"]["continue_recommended"] is True
    assert block["posture"]["human_gate_ready"] is False
    assert state["audit_route"]["artifact"] == \
        "results/product/audit_readiness/CYCLE_40823586491_AUDIT_ROUTE.json"
    # Append-only predecessors must survive.
    assert state["cycle_40820909501_operational_resume"]
    assert state["cycle_40808627073_operational_resume"]
    assert state["cycle_40803969886_operational_resume"]


def test_run_history_entry_and_append_only_predecessor():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    hist = {str(e["run_id"]): e for e in state["run_history"]}
    cur = hist[RUN]
    assert cur["status"] == \
        "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE_OBSERVED_PROVIDER_NETWORK_" \
        "DELTA_SUBSTANTIVE_SNAPSHOT_REVERIFIED_AUDIT_READY_UNADJUDICATED"
    assert cur["resumed_run"] == RESUME
    assert cur["accepted"] is False
    assert cur["accepted_commit"] == ACCEPTED
    assert cur["report_of_record"] == "reports/product/CYCLE_40823586491.md"
    assert cur["cycle_test"] == "product/tests/test_cycle_40823586491.py"
    assert cur["team_job"].startswith("FAILURE")
    assert "1534.0 s" in cur["team_job"]
    assert "OBSERVED_PROVIDER_NETWORK_ANNOTATIONS" in cur["team_job"]
    assert cur["audit_job"] == "skipped (team job did not succeed)"
    assert RUN in hist
    assert RESUME in hist
    assert hist[RESUME]["accepted"] is False


def test_resumed_death_is_observed_provider_network_not_unobserved():
    diag = json.loads(DIAG.read_text(encoding="utf-8"))
    assert diag["run_id"] == RESUME
    assert diag["predecessor_run_id"] == PRED_RUN
    orch = diag["orchestration"]
    assert orch["classification"] == \
        "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    mech = orch["mechanism"]
    assert mech["status"] == "OBSERVED_PROVIDER_NETWORK_ANNOTATIONS"
    assert mech["quantum_expired"] is False
    assert mech["exit_code"] == 1
    pn = mech["provider_network_annotations"]
    for sentinel in SENTINELS:
        assert any(sentinel in m for m in pn), sentinel
    team = orch["team"]
    assert team["conclusion"] == "failure"
    assert team["failed_step"] == "Run lane cycle"
    assert team["failed_step_seconds"] == 1534.0
    assert team["team_snapshot_persisted"] is True
    assert team["team_snapshot_persisted_after_failed_team_job"] is True
    assert team["producer_state_validation_step_conclusion"] == "skipped"
    assert team["write_scope_step_conclusion"] == "skipped"
    assert orch["audit"]["conclusion"] == "skipped"
    assert orch["audit"]["gate_file_written"] is False
    delta = diag["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["changed_files"] == 19
    assert delta["snapshot_head"] == SNAPSHOT
    assert delta["predecessor_head"] == PREDSNAP
    assert diag["adjudication"]["status"] == "UNADJUDICATED"


def test_flat_diagnosis_and_classifier_reclassification():
    flat = json.loads(FLAT_DIAG.read_text(encoding="utf-8"))
    assert flat["run_id"] == RESUME
    assert flat["classification"] == \
        "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert flat["mechanism"]["status"] == \
        "OBSERVED_PROVIDER_NETWORK_ANNOTATIONS"
    assert flat["team"]["failed_step_seconds"] == 1534.0
    # The committed diagnosis must be exactly what the instrument re-derives
    # from the committed raw snapshot (fresh-context reproducibility).
    sys.path.insert(0, str(ROOT))
    from product import audit_step_diagnosis as asd
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    fresh = asd.classify(raw)
    assert fresh["mechanism"]["status"] == \
        "OBSERVED_PROVIDER_NETWORK_ANNOTATIONS"
    assert fresh["mechanism"]["exit_code"] == \
        flat["mechanism"]["exit_code"]
    assert fresh["classification"] == flat["classification"]
    # The classifier must NOT claim a quantum for this death.
    assert fresh["mechanism"]["quantum_expired"] is False
    # And the raw annotations must actually carry the sentinels.
    msgs = [a["message"] for v in (raw.get("annotations") or {}).values()
            for a in v]
    for sentinel in SENTINELS:
        assert any(sentinel in m for m in msgs), sentinel
    assert any("exit code 1" in m for m in msgs)
    assert not any("LEX_WORK_QUANTUM_EXPIRED" in m for m in msgs)


def test_delta_substance_is_substantive_product_work():
    ds = json.loads(DELTA.read_text(encoding="utf-8"))
    assert ds["run_id"] == RESUME
    assert ds["delta_substance"] == "SUBSTANTIVE"
    assert ds["product_work"] is True
    assert ds["changed_files"] == 19
    assert ds["cache_content_count"] == 0
    assert ds["cache_timestamp_only_count"] == 0
    assert "reports/product/CYCLE_40820909501.md" in ds["substantive_files"]
    assert ds["counts"]["state"] == 1


def test_profile_registered_and_cross_validated():
    sys.path.insert(0, str(ROOT))
    from product.audit_readiness import PROFILES, select_profile
    assert RUN in PROFILES
    prof = select_profile(RUN)
    assert prof["resumed_run_id"] == RESUME
    assert prof["predecessor_run_id"] == PRED_RUN
    assert prof["failed_job"] == "team"
    assert prof["mechanism_kind"] == "observed_provider_network"
    assert prof["delta_kind"] == "committed"
    assert prof["changed_files"] == 19
    assert prof["exit_code"] == 1
    assert prof["quantum_seconds"] is None
    assert prof["state_block"] == "cycle_40823586491_operational_resume"
    assert prof["content_family_expected"] == {
        "n_bundles": 61,
        "n_decisions": 6100,
        "n_verified": 76,
        "n_verified_defective": 0,
        "false_reject_count": 0,
    }
    extras = {str(Path(x)) for x in prof["extra_claim_artifacts"]}
    assert str(RAW) in extras
    assert str(FLAT_DIAG) in extras
    assert str(DELTA) in extras


def test_vf4_non_rotting_repair_of_prior_cycle_test():
    """The prior cycle test pinned the rotating audit_route pointer; this
    cycle disclosed and applied the same non-rotting repair the prior
    cycles used for current_cycle_run_id."""
    path = ROOT / "product" / "tests" / "test_cycle_40820909501.py"
    text = path.read_text(encoding="utf-8")
    assert "DISCLOSED MAINTENANCE REPAIR (cycle 40823586491)" in text
    # Originals preserved inline, not silently deleted.
    assert 'CYCLE_40820909501_AUDIT_ROUTE.json' in text
    # Non-rotting form in force: the equality line is gone as live code.
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
    for needle in (RUN, RESUME, PRED_RUN, SNAPSHOT[:8], PREDSNAP[:8],
                   ACCEPTED[:8], "1534.0 s", "exit code 1",
                   "OBSERVED_PROVIDER_NETWORK_ANNOTATIONS",
                   "LEX_MODEL_AUTH_FAILURE", "LEX_MODEL_ROTATE",
                   "LEX_NETWORK_STALL", "SUBSTANTIVE", "product_work=true",
                   "UNADJUDICATED", "PASS", "70 assertions",
                   "61 bundles / 6100 decisions / 76 verified",
                   "0 verified+defective", "false rejects",
                   "DO-NOT-SERVE"):
        assert needle in text, needle


def test_content_family_matches_committed_artifact():
    assert CONTENT_FAMILY.is_file()
    doc = json.loads(CONTENT_FAMILY.read_text(encoding="utf-8"))
    assert doc["run_id"] == RUN
    assert doc["direction_version"] == 68
    fixed = doc["fixed_path_family"]["totals"]
    assert fixed["n_bundles"] == 61
    assert fixed["n_decisions"] == 6100
    assert fixed["n_verified"] == 76
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
        if label == "ALIGNED_AFTER_WRITE":
            assert route["snapshot_self_label"]["missing_artifacts"] == \
                ["route"]
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
        assert check["detail"]["mechanism_kind"] == \
            "observed_provider_network"
        hashes = next(c for c in dossier["checks"]
                      if c["id"] == "claim_artifacts")["detail"]["sha256"]
        for path in (RAW, FLAT_DIAG, DELTA, DIAG):
            assert str(path.relative_to(ROOT)) in hashes


def test_audit_brief_never_mints_a_gate():
    proc = subprocess.run(
        [sys.executable, "product/audit_route.py", "--for-auditor",
         "--run-id", RUN],
        cwd=str(ROOT), capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0
    assert "AUDIT TARGET" in proc.stdout
    assert "PRESENT" in proc.stdout
    assert not (ROOT / "results" / "audit" / "product"
                / f"CYCLE_{RUN}_GATE.json").exists()
    assert INTAKE.is_file()
