#!/usr/bin/env python3
"""Pins the operational resume of run 40858206250 by 40858799166.

Run 40850096631's TEAM job was green and committed one file at 50591be7
(product/query/counter_evidence_span.py) adding an UNCONDITIONAL
``counter_evidence_verified = False`` on every stage-2 surface abstention.
Its AUDIT "Independent audit" step then died at the 2700 s work quantum
(2705.0 s, exit 78) before writing a gate.  Run 40858206250 was a producer
re-dispatch that found nothing to add: HEAD stayed at 50591be7, the tree was
empty, and the workflow's rc-67 LEX_ZERO_DELTA_REPAIR guard fired.

This cycle scopes that rejection/incumbent leg to DEFECTIVE incumbent
evidence, leaves a content-sound confirmed incumbent verified, adds a final
gate-free sweep and the regression suite, re-verifies the inherited snapshot,
and re-keys state/report/test/profile/dossier/route/intake to 40858799166.
Neither failed run is accepted; no gate exists.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state" / "product.json"
ORCH = ROOT / "results" / "product" / "orchestration"
AR = ROOT / "results" / "product" / "audit_readiness"
REPORT = ROOT / "reports" / "product" / "CYCLE_40858799166.md"
DIAG = ORCH / "CYCLE_40858206250_resume_diagnosis.json"
RAW = ORCH / "CYCLE_40858206250_run_jobs_raw.json"
FLAT = ORCH / "CYCLE_40858206250_audit_step_diagnosis.json"
DELTA = ORCH / "CYCLE_40858206250_delta_substance.json"
PRED_RAW = ORCH / "CYCLE_40850096631_run_jobs_raw.json"
PRED_FLAT = ORCH / "CYCLE_40850096631_audit_step_diagnosis.json"
PRED_DELTA = ORCH / "CYCLE_40850096631_delta_substance.json"
CONTENT_FAMILY = (ROOT / "results" / "product" / "counter_content_family"
                  / "CYCLE_40858799166.json")
SLICE_ROOT = ROOT / "results" / "product" / "offline_slice"
SLICE_STAMP = "20261029T1046Z"
SMOKE = (ROOT / "results" / "product" / "progressive_smoke"
         / "CYCLE_40858799166_progressive_smoke.json")
DOSSIER = AR / "CYCLE_40858799166_audit_readiness.json"
ROUTE = AR / "CYCLE_40858799166_AUDIT_ROUTE.json"
INTAKE = AR / "CYCLE_40858799166_AUDIT_INTAKE.md"
STAGE2_BUNDLE = (ROOT / "results" / "product" / "offline_slice"
                 / "20261025T045400Z" / "rent-default.bundle.json")
ACCEPTED = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
SNAPSHOT = "50591be777c47f64e73488b91e335b941e531cd3"
PREVSNAP = "a5feff0ab491fa378858a760fb9132e4a4969810"
RUN = "40858799166"
RESUME = "40858206250"
PRED_RUN = "40850096631"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_state_pointer_and_posture_non_rotting():
    state = _json(STATE)
    assert state["accepted_run_id"] == "CYCLE_40284658455"
    assert state["accepted_commit"] == ACCEPTED
    assert state["current_cycle_run_id"] == RUN
    assert state["current_run"] == RUN
    assert state["current_run_id"] == RUN
    assert state["direction_version"] == 68
    assert state["cycle_status"] == "COMPLETE"
    assert state["continue_recommended"] is True
    assert state["human_gate_ready"] is False
    assert state["machine_gate_ready"] is False
    assert state["ready_for_owner_session"] is False
    assert state["packet_admitted"] is False
    assert state["owner_decision_required"] is False
    block = state["cycle_40858799166_operational_resume"]
    assert block["run_id"] == RUN
    assert block["resumed_run_id"] == RESUME
    assert block["predecessor_run_id"] == PRED_RUN
    assert block["resumed_snapshot_head"] == SNAPSHOT
    assert block["diagnosis_of_resumed"] == \
        "results/product/orchestration/CYCLE_40858206250_resume_diagnosis.json"
    rf = block["resumed_failure"]
    assert rf["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert "137.0 s" in rf["team_job"]
    assert "exit 67" in rf["team_job"]
    assert "LEX_ZERO_DELTA_REPAIR" in rf["team_job"]
    assert "OBSERVED_ZERO_DELTA_REPAIR_GUARD_EXIT_67" in rf["mechanism"]
    assert "requirement 10" in rf["mechanism"]
    assert "NOT a product defect" in rf["mechanism"]
    assert rf["gate_file_written"] is False
    assert rf["adjudication"] == "UNADJUDICATED"
    assert "ZERO_DURABLE_DELTA" in rf["durable_delta"]
    assert "0 changed files" in rf["durable_delta"]
    pf = block["predecessor_failure"]
    assert pf["classification"] == \
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    assert "2705.0 s" in pf["audit_job"]
    assert "OBSERVED_QUANTUM_EXPIRED" in pf["audit_job"]
    assert "COMMITTED_DELTA" in pf["durable_delta"]
    assert "1 changed file" in pf["durable_delta"]
    assert "product/query/counter_evidence_span.py" in pf["durable_delta"]
    assert pf["adjudication"] == "UNADJUDICATED"
    assert block["regression_repair"]["file"] == \
        "product/query/counter_evidence_span.py"
    assert "UNCONDITIONAL" in block["regression_repair"]["removed"]
    assert "retained_content_sound" in block["regression_repair"]["scoped_rule"]
    assert block["snapshot_audit_readiness"]["state_advanced"] is True
    assert block["posture"]["continue_recommended"] is True
    assert block["posture"]["human_gate_ready"] is False
    assert state["audit_route"]["artifact"] == \
        "results/product/audit_readiness/CYCLE_40858799166_AUDIT_ROUTE.json"
    # Append-only predecessors must survive.
    assert state["cycle_40840720468_operational_resume"]
    assert state["cycle_40823586491_operational_resume"]
    assert state["cycle_40820909501_operational_resume"]


def test_run_history_entries_and_append_only_predecessors():
    state = _json(STATE)
    hist = {str(e["run_id"]): e for e in state["run_history"]}
    for run_id in (PRED_RUN, RESUME, RUN):
        assert run_id in hist, run_id
    pred = hist[PRED_RUN]
    assert pred["accepted"] is False
    assert "TEAM_GREEN" in pred["status"]
    assert "SUCCESS" in pred["team_job"]
    assert "2705.0 s" in pred["audit_job"]
    assert "OBSERVED_QUANTUM_EXPIRED" in pred["audit_job"]
    assert pred["audit_gate"] == "NONE_YET"
    res = hist[RESUME]
    assert res["accepted"] is False
    assert "ZERO_DELTA_REPAIR" in res["status"]
    assert "137.0 s" in res["team_job"]
    assert "LEX_ZERO_DELTA_REPAIR" in res["team_job"]
    assert res["audit_job"] == "skipped (team job did not succeed)"
    cur = hist[RUN]
    assert cur["status"] == \
        "ZERO_DELTA_GUARD_RESUME_STAGE2_INCUMBENT_SCOPED_SNAPSHOT_" \
        "REVERIFIED_AUDIT_READY_UNADJUDICATED"
    assert cur["resumed_run"] == RESUME
    assert cur["accepted"] is False
    assert cur["accepted_commit"] == ACCEPTED
    assert cur["report_of_record"] == "reports/product/CYCLE_40858799166.md"
    assert cur["cycle_test"] == "product/tests/test_cycle_40858799166.py"
    assert cur["audit_gate"] == "NONE_YET"
    # Earlier history must stay append-only.
    assert "40840720468" in hist and "40832905362" in hist


def test_resumed_run_is_zero_delta_guard_observed():
    diag = _json(DIAG)
    assert diag["run_id"] == RESUME
    assert diag["predecessor_run_id"] == PRED_RUN
    orch = diag["orchestration"]
    assert orch["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    mech = orch["mechanism"]
    assert mech["status"] == "OBSERVED_ZERO_DELTA_REPAIR_GUARD_EXIT_67"
    assert mech["quantum_expired"] is False
    assert mech["exit_code"] == 67
    team = orch["team"]
    assert team["failed_step"] == "Run lane cycle"
    assert team["failed_step_seconds"] == 137.0
    assert team["team_snapshot_persisted_after_failed_team_job"] is True
    audit = orch["audit"]
    assert audit["conclusion"] == "skipped"
    assert audit["gate_file_written"] is False
    delta = diag["durable_delta"]
    assert delta["classification"] == "ZERO_DURABLE_DELTA"
    assert delta["changed_files"] == 0
    assert delta["snapshot_head"] == SNAPSHOT
    assert delta["predecessor_head"] == SNAPSHOT
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    # The raw snapshot carries the rc-67 sentinel the classification rests on.
    raw = _json(RAW)
    raw_team = next(j for j in raw["jobs"] if j["name"] == "team")
    steps = {s["name"]: s["conclusion"] for s in raw_team["steps"]}
    assert steps["Run lane cycle"] == "failure"
    assert steps["Validate active MVP producer state"] == "skipped"
    assert steps["Enforce lane write scope"] == "skipped"
    assert steps["Persist team snapshot"] == "success"
    messages = " ".join(str(a.get("message") or "")
                        for a in (raw.get("annotations") or {}).get(
                            str(raw_team["id"])) or [])
    assert "LEX_ZERO_DELTA_REPAIR" in messages
    assert "exit code 67" in messages.lower()


def test_predecessor_audit_quantum_death_and_substantive_delta():
    assert PRED_RAW.is_file() and PRED_FLAT.is_file() and PRED_DELTA.is_file()
    flat = _json(PRED_FLAT)
    assert flat["run_id"] == PRED_RUN
    assert flat["classification"] == \
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    assert flat["mechanism"]["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert flat["mechanism"]["quantum_seconds"] == 2700
    assert flat["mechanism"]["exit_code"] == 78
    assert flat["team"]["conclusion"] == "success"
    assert flat["team"]["producer_state_validation_step_conclusion"] == "success"
    assert flat["team"]["write_scope_step_conclusion"] == "success"
    assert flat["audit"]["failed_step"] == "Independent audit"
    assert flat["audit"]["independent_audit_step_seconds"] == 2705.0
    assert flat["audit"]["gate_step"] == "skipped"
    assert flat["audit"]["persist_step"] == "skipped"
    assert flat["audit"]["gate_file_written"] is False
    ds = _json(PRED_DELTA)
    assert ds["run_id"] == PRED_RUN
    assert ds["delta_substance"] == "SUBSTANTIVE"
    assert ds["product_work"] is True
    assert ds["changed_files"] == 1
    assert ds["base"]["sha"].startswith(PREVSNAP[:8])
    assert ds["head"]["sha"].startswith(SNAPSHOT[:8])
    assert ds["substantive_files"] == [
        "product/query/counter_evidence_span.py"]
    dz = _json(DELTA)
    assert dz["run_id"] == RESUME
    assert dz["delta_substance"] == "EMPTY"
    assert dz["product_work"] is False
    assert dz["changed_files"] == 0


def test_stage2_rejection_leg_is_scoped_and_helpers_are_present():
    text = (ROOT / "product" / "query" / "counter_evidence_span.py").read_text(
        encoding="utf-8")
    # The repair is visible as helpers and provenance, not as a blanket write.
    for needle in ("_incumbent_content_failure", "_downgrade_incumbent",
                   "_content_rejection_sweep", "retained_content_sound",
                   "n_retained_content_sound"):
        assert needle in text, needle
    # The legacy unconditional write directly inside the abstention branch is
    # gone; the only stage-2 writes now go through the scoped helper.
    assert "incumbent_fails" in text
    assert "d[\"counter_evidence_verified\"] = False\n            continue" \
        not in text

    # Behaviour pin on an append-only committed bundle with a stage-2
    # abstention population: a content-sound incumbent is retained; the same
    # row with an offset-0 header is downgraded.
    sys.path.insert(0, str(ROOT))
    from product.query import counter_evidence_span as ces
    doc = _json(STAGE2_BUNDLE)
    prov = (doc.get("provenance") or {}).get(
        "counter_evidence_span_surface") or {}
    entry = prov["abstained"][0]
    did = entry["decision_id"]
    row = next(d for d in doc["decisions"] if d["decision_id"] == did)
    sound = None
    for match in re.finditer(r"[^.!?]{60,400}[.!?]", str(row.get("full_text") or "")):
        candidate = match.group(0).strip()
        if ces.passes_content_filter(candidate, row,
                                     str(row["full_text"]).find(candidate))[0]:
            sound = candidate
            break
    assert sound, "no content-sound sentence in the committed bundle"
    row["counter_evidence"] = sound
    row["counter_evidence_verified"] = True
    out = ces.apply_surface_span_confirmation(doc)
    after = next(d for d in out["decisions"] if d["decision_id"] == did)
    assert after["counter_evidence_verified"] is True
    retained = (out["provenance"]["counter_evidence_span_surface"]
                ["retained_content_sound"])
    assert did in {r["decision_id"] for r in retained}

    doc2 = _json(STAGE2_BUNDLE)
    row2 = next(d for d in doc2["decisions"] if d["decision_id"] == did)
    row2["counter_evidence"] = str(row2.get("full_text") or "")[:80]
    row2["counter_evidence_verified"] = True
    assert ces.frozen_content_defects(row2["counter_evidence"], row2) == [
        "D2_letterhead_zone"]
    out2 = ces.apply_surface_span_confirmation(doc2)
    after2 = next(d for d in out2["decisions"] if d["decision_id"] == did)
    assert after2["counter_evidence_verified"] is False
    assert after2["counter_evidence_unevidenced_reason"] == entry["reason_code"]
    record = next(r for r in out2["provenance"]["counter_evidence_span_surface"]
                  ["downgrades"] if r["decision_id"] == did)
    assert record["leg"] == "surface_abstention"
    assert "D2_letterhead_zone" in record["defects"]


def test_profile_registered_and_cross_validated():
    sys.path.insert(0, str(ROOT))
    from product.audit_readiness import PROFILES, select_profile
    assert RUN in PROFILES
    prof = select_profile(RUN)
    assert prof["resumed_run_id"] == RESUME
    assert prof["predecessor_run_id"] == PRED_RUN
    assert prof["failed_job"] == "team"
    assert prof["mechanism_kind"] == "observed_zero_delta_guard"
    assert prof["delta_kind"] == "zero"
    assert prof["changed_files"] == 0
    assert prof["exit_code"] == 67
    assert prof["quantum_seconds"] is None
    assert prof["state_block"] == "cycle_40858799166_operational_resume"
    assert prof["current_report"] == REPORT
    assert prof["content_family_expected"] == {
        "n_bundles": 67,
        "n_decisions": 6700,
        "n_verified": 91,
        "n_verified_defective": 0,
        "false_reject_count": 0,
    }
    extras = {str(Path(x)) for x in prof["extra_claim_artifacts"]}
    for path in (RAW, FLAT, DELTA, PRED_RAW, PRED_FLAT, PRED_DELTA):
        assert str(path) in extras


def test_content_family_matches_committed_artifact():
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
    assert doc["ordered_work_2_full_success_rule"]["met"] is True
    full = doc["ordered_work_2_full_success_rule"]
    assert full["packet_v3_bytes_unchanged"] is True
    assert full["guarded_arm_yield_not_decreased"] is True
    assert full["accepted_four_before_after_complete"] is True
    hist = doc["all_committed"]["totals"]["defect_histogram"]
    assert hist["D2_letterhead_zone"] == 44
    assert hist["D3_markup_residue"] == 31
    assert hist["D4_language_marker_mismatch"] == 7


def test_four_flagship_slices_are_committed_bytes():
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
        if slug != "petty-theft-dismissal":
            assert prov["applied"] is True, slug
        assert prov["n_selected"] == 0, slug
        if slug == "corporate-criminal-liability":
            # No stage-1 downgrade on this leg; one content-sound abstention
            # is retained instead (the success-rule direction of the repair).
            assert prov["n_downgraded"] == 0, slug
            assert prov["n_incumbent_downgraded"] == 0, slug
            assert prov["n_retained_content_sound"] >= 1, slug
        else:
            assert prov["n_downgraded"] >= 1, slug


def test_progressive_smoke_is_committed_and_passing():
    assert SMOKE.is_file()
    doc = _json(SMOKE)
    assert doc["run_id"] == RUN
    assert doc["verdict"] == "PASS"
    assert doc["checks_passed"] == doc["checks_total"] == 23
    assert doc["timings_s"]["server_boot_s"] < 3.0
    assert doc["timings_s"]["start_s"] < 1.0


def test_report_and_claims_match_the_committed_artifacts():
    assert REPORT.is_file()
    text = " ".join(REPORT.read_text(encoding="utf-8").split())
    for needle in (RUN, RESUME, PRED_RUN, SNAPSHOT[:8], PREVSNAP[:8],
                   ACCEPTED[:8], "137.0 s", "exit 67",
                   "LEX_ZERO_DELTA_REPAIR", "2705.0 s", "exit 78",
                   "OBSERVED_QUANTUM_EXPIRED",
                   "UNCONDITIONAL", "retained_content_sound",
                   "UNADJUDICATED", "PASS", "70 assertions",
                   "67 bundles / 6700 decisions / 91 verified",
                   "0 verified+defective", "false rejects",
                   "DO-NOT-SERVE"):
        assert needle in text, needle


def test_audit_route_artifact_if_present():
    if ROUTE.exists():
        route = _json(ROUTE)
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
    if ROUTE.exists():
        assert INTAKE.is_file()


def test_dossier_generated_if_present():
    if DOSSIER.exists():
        dossier = _json(DOSSIER)
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
            "observed_zero_delta_guard"
        assert check["detail"]["delta_kind"] == "zero"
        assert check["detail"]["changed_files"] == 0
        hashes = next(c for c in dossier["checks"]
                      if c["id"] == "claim_artifacts")["detail"]["sha256"]
        for path in (RAW, FLAT, DELTA, DIAG, PRED_RAW, PRED_FLAT, PRED_DELTA,
                     CONTENT_FAMILY, REPORT, STATE):
            assert str(path.relative_to(ROOT)) in hashes, path
