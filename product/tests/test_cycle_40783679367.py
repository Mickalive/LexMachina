#!/usr/bin/env python3
"""Pins the operational resume of run 40783679367 (audit quantum death #6).

Run 40783679367 was a fresh producer re-dispatch of the completed producer
snapshot after the fifth audit quantum death.  Its TEAM job was fully green
and persisted a 25-file committed delta ``c73d9d84`` over predecessor team
head ``d1f2356a``, but the delta is **CACHE_REFRESH only** — 22 query-cache
envelopes whose only change is ``fetched_at`` and 3 whose upstream
``citation_count`` moved, with 0 product code/test/report/state/artifact and
0 manifest-covered rewrites.  Its AUDIT "Independent audit" step then died at
the 2700 s work quantum (2705.0 s, exit 78, ``OBSERVED_QUANTUM_EXPIRED`` via
public check-run annotations) before writing any gate.  That is the SIXTH
audit-side quantum death on this lineage.

This cycle's binding product delta is ``product/delta_substance.py`` plus its
tests: a read-only classifier that makes cache churn mechanically
distinguishable from product work, so a count-based guard cannot again let a
cache refresh pass for a work cycle.

This module pins: the machine diagnosis of 40783679367; the cache-refresh
classification; the run-history/state truth repair; the profile entry; the
fresh offline slice and content-family verifications; the fail-closed
posture; and (conditionally) the committed dossier and route artifacts.
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
REPORT = ROOT / "reports" / "product" / "CYCLE_40783679367.md"
PREV_REPORT = ROOT / "reports" / "product" / "CYCLE_40772551540.md"
DOSSIER = AR / "CYCLE_40783679367_audit_readiness.json"
ROUTE = AR / "CYCLE_40783679367_AUDIT_ROUTE.json"
INTAKE = AR / "CYCLE_40783679367_AUDIT_INTAKE.md"
BUNDLE = (ROOT / "results" / "product" / "offline_slice"
          / "20261029T001038Z" / "rent-default.bundle.json")
BUNDLE_SUMMARY = BUNDLE.with_name("summary.json")
BUNDLE_2 = (ROOT / "results" / "product" / "offline_slice"
            / "20261029T002005Z" / "business-judgment-rule.bundle.json")
CONTENT_FAMILY = (ROOT / "results" / "product" / "counter_content_family"
                  / "CYCLE_40783679367.json")
DELTA_ARTIFACT = (ORCH / "CYCLE_40783679367_delta_substance.json")
ACCEPTED = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
SNAPSHOT = "c73d9d848018e56d2d2ec3a5d53f9791688ae376"
PREDECESSOR = "d1f2356a335cfde44e11cc79bcada8d54b394f97"


def test_state_pointer_and_posture_non_rotting():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    assert state["accepted_run_id"] == "CYCLE_40284658455"
    assert state["accepted_commit"] == ACCEPTED
    # current_run is the MOVING latest-resume pointer; assert this cycle's
    # own durable record below rather than a value a later resume may move.
    assert state["current_run"]
    assert "cycle_40783679367_operational_resume" in state
    assert state["continue_recommended"] is True
    assert state["human_gate_ready"] is False
    assert state["machine_gate_ready"] is False
    assert state["ready_for_owner_session"] is False
    assert state["packet_admitted"] is False
    assert state["owner_decision_required"] is False
    assert state["direction_version"] == 68
    block = state["cycle_40783679367_operational_resume"]
    assert block["resumed_run_id"] == "40772551540"
    assert block["predecessor_team_head"] == PREDECESSOR
    assert block["resumed_failure"]["classification"] == \
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    assert block["resumed_failure"]["gate_file_written"] is False
    assert "SIXTH audit-side quantum death" in \
        block["resumed_failure"]["audit_death_ordinal"]
    assert block["resumed_failure"]["adjudication"] == "UNADJUDICATED"
    assert block["delta_substance_finding"]["delta_substance"] == \
        "CACHE_REFRESH"
    assert block["delta_substance_finding"]["product_work"] is False
    assert block["delta_substance_finding"]["changed_files"] == 25
    assert block["snapshot_audit_readiness"]["state_advanced"] is True
    assert block["posture"]["human_gate_ready"] is False
    assert block["posture"]["continue_recommended"] is True
    assert block["posture"]["owner_decision_required"] is False


def test_run_history_fates():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    hist = {str(e["run_id"]): e for e in state["run_history"]}
    prev = hist["40772551540"]
    assert prev["status"] == \
        "OPERATIONAL_RESUME_WORKSPACE_CONTRACT_AND_AUDIT_DEATH_5"
    assert prev["resumed_run"] == "40763434744"
    assert prev["accepted"] is False
    cur = hist["40783679367"]
    assert cur["status"] == \
        "AUDIT_JOB_QUANTUM_DEATH_CACHE_REFRESH_DELTA_UNADJUDICATED"
    assert cur["resumed_run"] == "40772551540"
    assert cur["accepted"] is False
    assert cur["accepted_commit"] == ACCEPTED
    assert cur["report_of_record"] == "reports/product/CYCLE_40783679367.md"
    assert cur["cycle_test"] == "product/tests/test_cycle_40783679367.py"
    assert cur["team_job"].startswith("SUCCESS")
    assert "25-file committed delta c73d9d84" in cur["team_job"]
    assert "CACHE_REFRESH" in cur["team_job"]
    assert "2705.0 s" in cur["audit_job"]
    assert "OBSERVED_QUANTUM_EXPIRED" in cur["audit_job"]
    # The predecessor entry must survive append-only.
    assert "40763434744" in hist


def test_diagnosed_audit_quantum_death_of_40783679367():
    diag = json.loads((ORCH / "CYCLE_40783679367_resume_diagnosis.json")
                      .read_text(encoding="utf-8"))
    assert diag["run_id"] == "40783679367"
    assert diag["predecessor_run_id"] == "40772551540"
    orch = diag["orchestration"]
    assert orch["classification"] == \
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    mech = orch["mechanism"]
    assert mech["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert mech["quantum_expired"] is True
    assert mech["quantum_seconds"] == 2700
    assert mech["exit_code"] == 78
    assert mech["logs_available"] is False
    assert mech["logs_endpoint_status"] == 403
    assert orch["team"]["conclusion"] == "success"
    assert orch["team"]["producer_state_validation_step_conclusion"] == \
        "success"
    assert orch["team"]["write_scope_step_conclusion"] == "success"
    assert orch["audit"]["conclusion"] == "failure"
    assert orch["audit"]["failed_step"] == "Independent audit"
    assert orch["audit"]["independent_audit_step_seconds"] == 2705.0
    assert orch["audit"]["gate_file_written"] is False
    assert orch["integrate"]["conclusion"] == "skipped"
    delta = diag["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["changed_files"] == 25
    assert delta["snapshot_head"] == SNAPSHOT
    assert delta["predecessor_head"] == PREDECESSOR
    assert all(p.startswith("results/product/query_cache/")
               for p in delta["changed_paths_sample"])
    assert diag["adjudication"]["status"] == "UNADJUDICATED"


def test_raw_snapshot_is_the_committed_public_record():
    raw = json.loads((ORCH / "CYCLE_40783679367_run_jobs_raw.json")
                     .read_text(encoding="utf-8"))
    assert raw["run"]["id"] == 40783679367
    team = next(j for j in raw["jobs"] if j["name"] == "team")
    assert team["conclusion"] == "success"
    audit = next(j for j in raw["jobs"] if j["name"] == "audit")
    assert audit["conclusion"] == "failure"
    steps = {s["name"]: s["conclusion"] for s in audit["steps"]}
    assert steps["Independent audit"] == "failure"
    assert steps["Enforce audit scope and read gate"] == "skipped"
    msgs = [a["message"] for v in (raw.get("annotations") or {}).values()
            for a in v]
    assert any("LEX_WORK_QUANTUM_EXPIRED seconds=2700" in m for m in msgs)
    assert any("exit code 78" in m for m in msgs)


def test_delta_is_cache_refresh_not_product_work():
    doc = json.loads(DELTA_ARTIFACT.read_text(encoding="utf-8"))
    assert doc["run_id"] == "40783679367"
    assert doc["head"]["sha"] == SNAPSHOT
    assert doc["base"]["sha"] == PREDECESSOR
    assert doc["changed_files"] == 25
    assert doc["delta_substance"] == "CACHE_REFRESH"
    assert doc["product_work"] is False
    assert doc["cache_timestamp_only_count"] == 22
    assert doc["cache_content_count"] == 3
    assert doc["substantive_files"] == []
    assert doc["cache_manifest_covered_rewrites"] == []
    for p in doc["cache_timestamp_only"] + doc["cache_content"]:
        assert p.startswith("results/product/query_cache/")
        assert p.endswith(".json")


def test_delta_classifier_instrument_and_guard():
    sys.path.insert(0, str(ROOT))
    from product import delta_substance as ds
    base_ref = ("refs/remotes/origin/cycle/core/product/"
                "40772551540/team")
    head_ref = ("refs/remotes/origin/cycle/core/product/"
                "40783679367/team")
    for ref in (base_ref, head_ref):
        try:
            ds._rev(ref)
        except ds.GitError:
            return  # bare checkout: refs not mounted
    rec = ds.classify(base_ref, head_ref)
    assert rec["delta_substance"] == "CACHE_REFRESH"
    assert rec["product_work"] is False
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = ds.main(["--base", base_ref, "--head", head_ref,
                      "--require-substantive"])
    assert rc == 2
    assert "product_work=False" in buf.getvalue()


def test_profile_registered_and_cross_validated():
    sys.path.insert(0, str(ROOT))
    from product import audit_readiness
    from product.audit_readiness import PROFILES, select_profile
    assert "40783679367" in PROFILES
    prof = select_profile("40783679367")
    assert prof["resumed_run_id"] == "40783679367"
    assert prof["predecessor_run_id"] == "40772551540"
    assert prof["failed_job"] == "audit"
    assert prof["mechanism_kind"] == "observed"
    assert prof["delta_kind"] == "committed"
    assert prof["changed_files"] == 25
    assert prof["exit_code"] == 78
    assert prof["quantum_seconds"] == 2700
    assert prof["changed_paths_include"] == ("results/product/query_cache/",)
    assert prof["cycle_test"] == "product/tests/test_cycle_40783679367.py"
    saved = dict(audit_readiness.PROFILE)
    try:
        audit_readiness.PROFILE.update(prof)
        check = audit_readiness.check_resumed_diagnosis()
        assert check["status"] == "PASS", check
    finally:
        audit_readiness.PROFILE.clear()
        audit_readiness.PROFILE.update(saved)


def test_offline_vertical_slice_claims_match_the_committed_bundle():
    assert BUNDLE.is_file()
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    rows = bundle["decisions"]
    assert len(rows) == 100
    assert bundle["query"]
    assert len(bundle.get("clusters") or []) == 8
    assert all(r.get("x") is not None and r.get("y") is not None
               for r in rows)
    assert all(r.get("cluster_id") is not None for r in rows)
    assert all(r.get("canonical_url") for r in rows)
    assert bundle["answer"]["status"] == "ready"
    assert len(bundle["answer"]["cited_decision_ids"]) == 4
    assert bundle["provenance"]["offline_slice"]["network"] == "none"
    assert bundle["provenance"]["offline_slice"]["geometry_preserved"] is True
    summary = json.loads(BUNDLE_SUMMARY.read_text(encoding="utf-8"))
    assert summary["page_contract"] is True
    assert summary["page_contract_detail"] == "PASS 70 assertions"
    assert summary["verified"] is True
    assert summary["degraded"] is False


def test_second_query_builds_a_distinct_query_specific_bundle():
    # A second frozen question must build its own bundle from the same adapter:
    # this is the query-specific seam, not a single hard-coded demo.
    assert BUNDLE_2.is_file()
    bundle = json.loads(BUNDLE_2.read_text(encoding="utf-8"))
    assert "commerciale" in bundle["query"]
    rows = bundle["decisions"]
    assert len(rows) == 100
    assert len(bundle.get("clusters") or []) == 8
    assert bundle["answer"]["status"] == "ready"
    assert len(bundle["answer"]["cited_decision_ids"]) == 3
    assert bundle["provenance"]["offline_slice"]["network"] == "none"
    assert bundle["provenance"]["offline_slice"]["geometry_preserved"] is True
    rent = json.loads(BUNDLE.read_text(encoding="utf-8"))
    assert bundle["query"] != rent["query"]
    assert ({r["decision_id"] for r in rows}
            != {r["decision_id"] for r in rent["decisions"]})


def test_content_family_probe_matches_the_committed_artifact():
    assert CONTENT_FAMILY.is_file()
    doc = json.loads(CONTENT_FAMILY.read_text(encoding="utf-8"))
    assert doc["run_id"] == "40783679367"
    assert doc["direction_version"] == 68
    fixed = doc["fixed_path_family"]["totals"]
    assert fixed["n_bundles"] == 55
    assert fixed["n_decisions"] == 5500
    assert fixed["n_verified"] == 64
    assert fixed["n_verified_defective"] == 0
    assert fixed["defect_histogram"] == {
        "D1_empty_evidence": 0,
        "D2_letterhead_zone": 0,
        "D3_markup_residue": 0,
        "D4_language_marker_mismatch": 0,
    }
    assert doc["false_reject_count"] == 0
    rule = doc["ordered_work_2_success_rule"]
    assert rule["met"] is True
    assert rule["false_reject_count"] == 0
    assert rule["defect_histogram_zero_D2_D3_D4"] is True
    assert rule["confirmed_sound_row_still_verified"] is True


def test_report_of_record_states_measured_claims():
    text = " ".join(REPORT.read_text(encoding="utf-8").split())
    for needle in ("40783679367", "c73d9d84", "d1f2356a", "7be4480e",
                   "2705.0 s", "exit code 78", "SIXTH audit-side quantum death",
                   "25 files", "CACHE_REFRESH", "product_work=false",
                   "22", "3", "0 manifest-covered", "UNADJUDICATED",
                   "PASS", "70 assertions", "2.512 s",
                   "55 bundles / 5500 decisions / 64 verified",
                   "success rule", "DO-NOT-SERVE", "2700 s",
                   "business-judgment-rule", "71 assertions"):
        assert needle in text, needle
    # The predecessor report is append-only evidence and must still exist.
    assert PREV_REPORT.is_file()


def test_audit_route_artifact_if_present():
    if ROUTE.exists():
        route = json.loads(ROUTE.read_text(encoding="utf-8"))
        assert route["schema"] == "product-audit-route/1"
        assert route["run_id"] == "40783679367"
        assert route["quantum_budget_s"] == 2700
        assert route["audit_target"]["audit_target_ref"] == \
            "origin/cycle/core/product/40783679367/team"
        ids = [s["id"] for s in route["steps"]]
        assert "state_contract" in ids
        assert "chain_cycle_tests" in ids
        assert "never a verdict" in route["contract"]
        if route.get("mode") == "bootstrap":
            assert "self_reference" in route
            failed = set(route["failed_steps"])
            assert failed <= {"chain_cycle_tests"}, failed
        else:
            assert route["overall_status"] == "PASS"
            assert route["failed_steps"] == []
            assert route["total_seconds"] < route["quantum_budget_s"]


def test_dossier_generated_if_present():
    if DOSSIER.exists():
        dossier = json.loads(DOSSIER.read_text(encoding="utf-8"))
        assert dossier["run_id"] == "40783679367"
        assert dossier["overall_status"] == "PASS"
        assert dossier["failed_checks"] == []
        assert dossier["skipped_checks"] == []


def test_audit_route_never_writes_a_gate():
    proc = subprocess.run(
        [sys.executable, "product/audit_route.py", "--for-auditor",
         "--run-id", "40783679367"],
        cwd=str(ROOT), capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0
    assert "AUDIT TARGET" in proc.stdout
    assert not (ROOT / "results" / "audit" / "product"
                / "CYCLE_40783679367_GATE.json").exists()
