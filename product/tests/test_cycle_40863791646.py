#!/usr/bin/env python3
"""Pins the operational resume of the 40858799166 snapshot by 40863791646.

Run 40858799166 wrote a 27-file SUBSTANTIVE delta at 0023cfa9 and then its
lane-cycle agent process exited 1 after 2164.0 s.  The public check-run
annotations record the workflow wrapper's own provider/network sentinels
(LEX_NETWORK_STALL, LEX_MODEL_AUTH_FAILURE on big-pickle, rotation to
beam-free).  The always-run persist step committed the already-written tree
while state validation and write scope were skipped; the audit job never ran,
so no gate exists and the run is UNADJUDICATED.

This cycle preserves that snapshot, proves the failure and the durable delta
from committed evidence, re-verifies the inherited v68 deliverable, and
re-keys state/report/test/profile/dossier/route/intake to 40863791646.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state" / "product.json"
ORCH = ROOT / "results" / "product" / "orchestration"
AR = ROOT / "results" / "product" / "audit_readiness"
REPORT = ROOT / "reports" / "product" / "CYCLE_40863791646.md"
PREV_REPORT = ROOT / "reports" / "product" / "CYCLE_40858799166.md"
RAW = ORCH / "CYCLE_40858799166_run_jobs_raw.json"
FLAT = ORCH / "CYCLE_40858799166_audit_step_diagnosis.json"
DIAG = ORCH / "CYCLE_40858799166_resume_diagnosis.json"
DELTA = ORCH / "CYCLE_40858799166_delta_substance.json"
CONTENT_FAMILY = (ROOT / "results" / "product" / "counter_content_family"
                  / "CYCLE_40863791646.json")
PREV_CONTENT_FAMILY = (ROOT / "results" / "product" / "counter_content_family"
                       / "CYCLE_40858799166.json")
SMOKE = (ROOT / "results" / "product" / "progressive_smoke"
         / "CYCLE_40863791646_progressive_smoke.json")
SLICE_ROOT = ROOT / "results" / "product" / "offline_slice"
SLICE_STAMP = "20261029T1046Z"
DOSSIER = AR / "CYCLE_40863791646_audit_readiness.json"
ROUTE = AR / "CYCLE_40863791646_AUDIT_ROUTE.json"
INTAKE = AR / "CYCLE_40863791646_AUDIT_INTAKE.md"
RUN = "40863791646"
RESUME = "40858799166"
PRED_RUN = "40858206250"
SNAPSHOT = "0023cfa9fe5c3fa45049edb48c8dae28a30c3b3b"
PREVSNAP = "50591be777c47f64e73488b91e335b941e531cd3"
ACCEPTED = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_state_pointer_posture_and_append_only_blocks():
    state = _json(STATE)
    assert state["accepted_run_id"] == "CYCLE_40284658455"
    assert state["accepted_commit"] == ACCEPTED
    # DISCLOSED MAINTENANCE REPAIR (cycle 40990419541): the top-level run
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
    block = state["cycle_40863791646_operational_resume"]
    assert block["run_id"] == RUN
    assert block["resumed_run_id"] == RESUME
    assert block["predecessor_run_id"] == PRED_RUN
    assert block["resumed_snapshot_head"] == SNAPSHOT
    assert block["diagnosis_of_resumed"] == \
        "results/product/orchestration/CYCLE_40858799166_resume_diagnosis.json"
    rf = block["resumed_failure"]
    assert rf["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert "2164.0 s" in rf["team_job"]
    assert "exit 1" in rf["team_job"]
    assert "OBSERVED_PROVIDER_NETWORK_ANNOTATIONS" in rf["mechanism"]
    assert "LEX_NETWORK_STALL" in rf["mechanism"]
    assert "LEX_MODEL_AUTH_FAILURE" in rf["mechanism"]
    assert "LEX_MODEL_ROTATE" in rf["mechanism"]
    assert "NOT a product defect" in rf["mechanism"] or \
        "Not a product defect" in rf["mechanism"]
    assert rf["gate_file_written"] is False
    assert rf["adjudication"] == "UNADJUDICATED"
    assert "COMMITTED_DELTA" in rf["durable_delta"]
    assert "27 changed files" in rf["durable_delta"]
    assert block["snapshot_audit_readiness"]["state_advanced"] is True
    assert block["posture"]["continue_recommended"] is True
    assert block["posture"]["human_gate_ready"] is False
    # DISCLOSED MAINTENANCE REPAIR (cycle 40990419541): the audit_route
    # pointer rotates with the executing run.  The original is preserved:
    #   assert state["audit_route"]["artifact"] == \
    #       "results/product/audit_readiness/" \
    #       "CYCLE_40863791646_AUDIT_ROUTE.json"
    assert state["audit_route"]["artifact"]  # pointer exists and is truthy
    # Append-only predecessors must survive.
    assert state["cycle_40858799166_operational_resume"]
    assert state["cycle_40840720468_operational_resume"]
    assert state["cycle_40823586491_operational_resume"]


def test_run_history_correction_and_new_entry():
    state = _json(STATE)
    hist = {str(e.get("run_id")): e for e in state["run_history"]}
    assert RUN in hist
    cur = hist[RUN]
    assert cur["accepted"] is False
    assert cur["accepted_commit"] == ACCEPTED
    assert cur["report_of_record"] == "reports/product/CYCLE_40863791646.md"
    assert cur["cycle_test"] == "product/tests/test_cycle_40863791646.py"
    assert cur["audit_gate"] == "NONE_YET"
    assert "PROVIDER_NETWORK" in cur["status"]

    prev = hist[RESUME]
    # The predecessor cycle test pins this status literal; a resumed cycle
    # corrects the omitted team-job outcome with an explicit correction block
    # instead of rewriting accepted history.
    assert prev["status"] == (
        "ZERO_DELTA_GUARD_RESUME_STAGE2_INCUMBENT_SCOPED_SNAPSHOT_"
        "REVERIFIED_AUDIT_READY_UNADJUDICATED")
    assert prev["orchestration_classification"] == \
        "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert "2164.0 s" in prev["team_job"]
    assert "LEX_NETWORK_STALL" in prev["team_job"]
    correction = prev["correction"]
    assert correction["corrected_by_run"] == RUN
    assert correction["field"] == "team_job"
    assert correction["from"] == "this dispatch (producer cycle)"
    assert correction["to"] == prev["team_job"]
    # Earlier history stays append-only.
    assert PRED_RUN in hist and "40850096631" in hist


def test_orchestration_failure_is_observed_provider_network():
    assert RAW.is_file() and FLAT.is_file() and DELTA.is_file() and DIAG.is_file()
    flat = _json(FLAT)
    assert flat["run_id"] == RESUME
    assert flat["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    mech = flat["mechanism"]
    assert mech["status"] == "OBSERVED_PROVIDER_NETWORK_ANNOTATIONS"
    assert mech["exit_code"] == 1
    assert mech["quantum_expired"] is False
    assert mech["annotations_available"] is True
    assert mech["logs_available"] is False
    joined = " ".join(mech["provider_network_annotations"])
    for sentinel in ("LEX_NETWORK_STALL", "LEX_MODEL_AUTH_FAILURE",
                     "LEX_MODEL_ROTATE"):
        assert sentinel in joined, sentinel
    team = flat["team"]
    assert team["failed_step"] == "Run lane cycle"
    assert team["failed_step_seconds"] == 2164.0
    assert team["team_snapshot_persisted"] is True
    assert team["team_snapshot_persisted_after_failed_team_job"] is True
    assert team["producer_state_validation_step_conclusion"] == "skipped"
    assert team["write_scope_step_conclusion"] == "skipped"
    assert flat["audit"]["conclusion"] == "skipped"
    assert flat["audit"]["gate_file_written"] is False
    assert flat["adjudication"]["product_defect"] is False

    raw = _json(RAW)
    raw_team = next(j for j in raw["jobs"] if j["name"] == "team")
    steps = {s["name"]: s["conclusion"] for s in raw_team["steps"]}
    assert steps["Run lane cycle"] == "failure"
    assert steps["Persist team snapshot"] == "success"
    assert steps["Enforce lane write scope"] == "skipped"
    anns = (raw.get("annotations") or {}).get(str(raw_team["id"])) or []
    messages = " ".join(str(a.get("message") or "") for a in anns)
    for sentinel in ("LEX_NETWORK_STALL", "LEX_MODEL_AUTH_FAILURE",
                     "LEX_MODEL_ROTATE", "exit code 1"):
        assert sentinel.lower() in messages.lower(), sentinel

    delta = _json(DELTA)
    assert delta["run_id"] == RESUME
    assert delta["delta_substance"] == "SUBSTANTIVE"
    assert delta["product_work"] is True
    assert delta["changed_files"] == 27
    assert delta["base"]["sha"] == PREVSNAP
    assert delta["head"]["sha"] == SNAPSHOT
    for path in ("product/query/counter_evidence_span.py",
                 "product/tests/test_counter_incumbent_rejection_v68.py",
                 "reports/product/CYCLE_40858799166.md"):
        assert path in delta["substantive_files"], path


def test_resume_diagnosis_proves_committed_delta_and_absent_gate():
    diag = _json(DIAG)
    assert diag["run_id"] == RESUME
    assert diag["predecessor_run_id"] == PRED_RUN
    assert diag["orchestration"]["classification"] == \
        "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert diag["orchestration"]["mechanism"]["status"] == \
        "OBSERVED_PROVIDER_NETWORK_ANNOTATIONS"
    dl = diag["durable_delta"]
    assert dl["classification"] == "COMMITTED_DELTA"
    assert dl["changed_files"] == 27
    assert dl["snapshot_head"] == SNAPSHOT
    assert dl["predecessor_head"] == PREVSNAP
    adj = diag["adjudication"]
    assert adj["status"] == "UNADJUDICATED"
    assert adj["accepted"] is False
    assert adj["audit"]["audit_ref_present"] is False
    assert adj["audit"]["gate_file_present"] is False
    assert adj["accept"]["accept_commit"] is None


def test_content_family_reproduces_on_the_committed_family():
    assert CONTENT_FAMILY.is_file()
    doc = _json(CONTENT_FAMILY)
    assert doc["run_id"] == RUN
    assert doc["direction_version"] == 68
    fixed = doc["fixed_path_family"]["totals"]
    assert fixed["n_bundles"] == 67
    assert fixed["n_decisions"] == 6700
    assert fixed["n_verified"] == 91
    assert fixed["n_verified_defective"] == 0
    assert fixed["defect_histogram"] == {
        "D1_empty_evidence": 0,
        "D2_letterhead_zone": 0,
        "D3_markup_residue": 0,
        "D4_language_marker_mismatch": 0,
    }
    assert doc["false_reject_count"] == 0
    assert doc["confirmed_set"]["still_verified"] is True
    assert doc["confirmed_set"]["decision_id"] == "bstger_SK.2023.49"
    assert doc["ordered_work_2_success_rule"]["met"] is True
    full = doc["ordered_work_2_full_success_rule"]
    assert full["met"] is True
    assert full["packet_v3_bytes_unchanged"] is True
    assert full["guarded_arm_yield_not_decreased"] is True
    assert full["accepted_four_before_after_complete"] is True
    hist = doc["all_committed"]["totals"]["defect_histogram"]
    assert hist["D2_letterhead_zone"] == 44
    assert hist["D3_markup_residue"] == 31
    assert hist["D4_language_marker_mismatch"] == 7
    # The inherited artifact is preserved, not overwritten.
    assert PREV_CONTENT_FAMILY.is_file()
    assert _json(PREV_CONTENT_FAMILY)["run_id"] == RESUME


def test_four_flagship_slices_and_smoke_are_committed():
    expected = {
        "rent-default": (70, 4, 3, 100),
        "business-judgment-rule": (71, 1, 0, 92),
        "petty-theft-dismissal": (70, 1, 0, 100),
        "corporate-criminal-liability": (69, 6, 6, 100),
    }
    for slug, (assertions, rows, verified, source_urls) in expected.items():
        summary = _json(SLICE_ROOT / f"{SLICE_STAMP}-{slug}" / "summary.json")
        assert summary["verified"] is True, slug
        assert summary["mode"] == "full_loop", slug
        assert summary["page_contract"] is True, slug
        assert summary["page_contract_detail"] == \
            f"PASS {assertions} assertions", slug
        stats = summary["stats"]
        assert stats["n_decisions"] == 100, slug
        assert stats["n_clusters"] == 8, slug
        assert stats["answer_status"] == "ready", slug
        assert stats["counter_rows"] == rows, slug
        assert stats["rows_with_source_url"] == source_urls, slug
        assert stats["geometry_preserved_by_enrich"] is True, slug
        assert stats["fixture_replay"]["network"] == "none", slug
        bundle = _json(SLICE_ROOT / f"{SLICE_STAMP}-{slug}"
                       / f"{slug}.bundle.json")
        got = sum(1 for d in bundle["decisions"]
                  if d.get("counter_evidence_verified") is True)
        assert got == verified, slug
        prov = bundle["provenance"]["counter_evidence_span"]
        # petty-theft-dismissal has no frozen anchor profile: the content-
        # rejection leg still runs, but only in content-only mode.
        if slug == "petty-theft-dismissal":
            assert prov["applied"] is False, slug
            assert prov["content_filter_applied"] is True, slug
            assert prov["content_filter_leg"] == \
                "content_only_no_anchor_profile", slug
            assert prov["reason"] == "no_frozen_anchor_profile_for_query", slug
        else:
            assert prov["applied"] is True, slug
        assert prov["n_selected"] == 0, slug

    assert SMOKE.is_file()
    smoke = _json(SMOKE)
    assert smoke["run_id"] == RUN
    assert smoke["verdict"] == "PASS"
    assert smoke["checks_passed"] == smoke["checks_total"] == 23
    assert smoke["timings_s"]["server_boot_s"] < 3.0
    assert smoke["timings_s"]["start_s"] < 1.0


def test_inherited_v68_repair_and_cycle_surface_are_preserved():
    text = (ROOT / "product" / "query" / "counter_evidence_span.py").read_text(
        encoding="utf-8")
    for needle in ("_incumbent_content_failure", "_downgrade_incumbent",
                   "_content_rejection_sweep", "retained_content_sound"):
        assert needle in text, needle
    assert PREV_REPORT.is_file()
    assert (ROOT / "product" / "tests"
            / "test_cycle_40858799166.py").is_file()
    assert (ROOT / "product" / "tests"
            / "test_counter_incumbent_rejection_v68.py").is_file()


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
    assert prof["changed_files"] == 27
    assert prof["exit_code"] == 1
    assert prof["quantum_seconds"] is None
    assert prof["state_block"] == "cycle_40863791646_operational_resume"
    assert prof["current_report"] == REPORT
    assert prof["content_family_expected"] == {
        "n_bundles": 67,
        "n_decisions": 6700,
        "n_verified": 91,
        "n_verified_defective": 0,
        "false_reject_count": 0,
    }
    extras = {str(Path(x)) for x in prof["extra_claim_artifacts"]}
    for path in (RAW, FLAT, DELTA, DIAG):
        assert str(path) in extras


def test_report_claims_match_committed_artifacts():
    assert REPORT.is_file()
    text = " ".join(REPORT.read_text(encoding="utf-8").split())
    for needle in (RUN, RESUME, PRED_RUN, SNAPSHOT[:8], PREVSNAP[:8],
                   ACCEPTED[:8], "2164.0 s", "exit 1", "LEX_NETWORK_STALL",
                   "LEX_MODEL_AUTH_FAILURE", "LEX_MODEL_ROTATE",
                   "OBSERVED_PROVIDER_NETWORK_ANNOTATIONS",
                   "committed", "27", "UNADJUDICATED",
                   "67 bundles", "6700", "91", "0 verified+defective",
                   "23/23", "DO-NOT-SERVE"):
        assert needle in text, needle


def test_no_producer_minted_gate_for_this_run():
    assert not (ROOT / "results" / "audit" / "product"
                / f"CYCLE_{RUN}_GATE.json").exists()
    assert not (ROOT / "reports" / "audit" / "product"
                / f"CYCLE_{RUN}.md").exists()


def test_dossier_generated_if_present():
    if not DOSSIER.exists():
        return
    dossier = _json(DOSSIER)
    assert dossier["run_id"] == RUN
    assert dossier["resumed_run_id"] == RESUME
    assert dossier["predecessor_run_id"] == PRED_RUN
    assert dossier["direction_version"] == 68
    assert dossier["overall_status"] == "PASS"
    assert dossier["failed_checks"] == []
    assert dossier["skipped_checks"] == []
    check = next(c for c in dossier["checks"]
                 if c["id"] == "resumed_diagnosis")
    assert check["status"] == "PASS"
    assert check["detail"]["mechanism_kind"] == "observed_provider_network"
    assert check["detail"]["delta_kind"] == "committed"
    assert check["detail"]["changed_files"] == 27
    hashes = next(c for c in dossier["checks"]
                  if c["id"] == "claim_artifacts")["detail"]["sha256"]
    for path in (RAW, FLAT, DELTA, DIAG, CONTENT_FAMILY, REPORT, STATE,
                 PREV_REPORT):
        assert str(path.relative_to(ROOT)) in hashes, path


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
    # First generation is a fixpoint break: the route cannot be strict-PASS
    # until the artifact it is writing exists.  The non-bootstrap rerun
    # verifies this artifact through this test.
    if route.get("mode") != "bootstrap":
        assert route["overall_status"] == "PASS"
        assert route["failed_steps"] == []
        assert route["total_seconds"] < route["quantum_budget_s"]
    assert INTAKE.is_file()


def test_disclosed_non_rotting_repair_of_prior_cycle_test():
    """The predecessor test pinned the moving current pointer and the
    rotating audit_route pointer; this cycle discloses and applies the same
    non-rotting repair prior cycles used, preserving the originals inline."""
    text = (ROOT / "product" / "tests"
            / "test_cycle_40858799166.py").read_text(encoding="utf-8")
    assert "DISCLOSED MAINTENANCE REPAIR (cycle 40863791646)" in text
    for needle in ('assert state["current_cycle_run_id"] == RUN',
                   'assert state["current_run"] == RUN',
                   'assert state["current_run_id"] == RUN',
                   'CYCLE_40858799166_AUDIT_ROUTE.json'):
        assert needle in text, needle
    for line in text.splitlines():
        stripped = line.strip()
        if stripped in ('assert state["current_cycle_run_id"] == RUN',
                        'assert state["current_run"] == RUN',
                        'assert state["current_run_id"] == RUN'):
            raise AssertionError(
                "the rotating pointer equality is live again; keep it "
                "preserved only as an inline comment")
        if stripped.startswith('assert state["audit_route"]["artifact"] =='):
            raise AssertionError(
                "the rotating audit_route equality is live again; keep it "
                "preserved only as an inline comment")
