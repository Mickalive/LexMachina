"""Cycle 43373102286: resume 43363900852, repair family population, audit-ready.

The resumed snapshot (run ``43363900852``, team ref ``756fa4e3``) had already
diagnosed and verified the lane deliverable, but its independent-audit job died
at the same workflow work quantum as its predecessor and its own validation
surface had a latent inconsistency:

* every cycle writes a ``*_verify/`` bundle carrying the same fixed-path
  provenance as a flagship bundle, so the frozen fixed-path family silently
  grew on each verification cycle (49 -> 50 -> 51).  That contradicts the
  published 49-bundle / 4900-decision baseline the audit dossier pins;
* the new historical cycle test equality-pinned the live
  ``current_cycle_run_id`` pointer, so it would fail on this successor cycle.

This cycle fixes both in the product's own instruments (not by re-scoring a
frozen bar) and re-verifies the end-to-end slice on current bytes.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "product"
for _p in (str(ROOT), str(PRODUCT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

EXECUTING_RUN_ID = "43373102286"
RESUMED_RUN_ID = "43363900852"
PREDECESSOR_RUN_ID = "43357207555"
SNAPSHOT_HEAD = "756fa4e3a7732744b07986ba329135b235193045"
ACCEPTED_HEAD = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
ACCEPTED_RUN_ID = "CYCLE_40284658455"
CHANGED_FILES = 46

STATE = ROOT / "state" / "product.json"
REPORT = ROOT / "reports" / "product" / f"CYCLE_{EXECUTING_RUN_ID}.md"
ORCH = ROOT / "results" / "product" / "orchestration"
RAW = ORCH / f"CYCLE_{RESUMED_RUN_ID}_run_jobs_raw.json"
LOGS = ORCH / f"CYCLE_{RESUMED_RUN_ID}_job_logs"
DIAG = ORCH / f"CYCLE_{RESUMED_RUN_ID}_resume_diagnosis.json"
FAMILY = (ROOT / "results" / "product" / "counter_content_family"
          / f"CYCLE_{EXECUTING_RUN_ID}.json")
SLICE = ROOT / "results" / "product" / "offline_slice" / f"{EXECUTING_RUN_ID}_verify"
BUNDLE = SLICE / "rent-default.bundle.json"
ACCEPT_GATE = (ROOT / "results" / "audit" / "product"
               / "CYCLE_40284658455_GATE.json")
CREDENTIAL_RE = re.compile(
    r"gh[somp]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+", re.IGNORECASE)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_resumed_stop_is_observed_quantum_expiry_with_committed_delta():
    diag = _load(DIAG)
    assert diag["run_id"] == RESUMED_RUN_ID
    assert diag["predecessor_run_id"] == PREDECESSOR_RUN_ID
    assert diag["raw_snapshot"] == str(RAW.relative_to(ROOT))

    orch = diag["orchestration"]
    assert orch["classification"] == (
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE")
    assert orch["team"]["conclusion"] == "success"
    assert orch["team"]["team_snapshot_persisted"] is True
    assert orch["team"]["producer_state_validation_step_conclusion"] == "success"
    assert orch["team"]["write_scope_step_conclusion"] == "success"
    assert orch["audit"]["failed_step"] == "Independent audit"
    assert orch["audit"]["gate_step"] == "skipped"
    assert orch["audit"]["persist_step"] == "skipped"
    assert orch["audit"]["gate_file_written"] is False
    assert orch["integrate"]["conclusion"] == "skipped"

    mech = orch["mechanism"]
    assert mech["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert mech["quantum_expired"] is True
    assert mech["quantum_seconds"] == 2700
    assert mech["exit_code"] == 78
    assert mech["annotations_available"] is True
    assert mech["logs_available"] is True
    assert mech["logs_endpoint_status"] == 200
    observed = orch["observed_failure"]
    assert observed["source"] == "github_actions_check_run_annotations"
    assert observed["quantum_message"] == (
        "LEX_WORK_QUANTUM_EXPIRED seconds=2700 pid=3075")
    assert "No provider or auth cause is claimed" in mech["claim"]

    delta = diag["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["changed_files"] == CHANGED_FILES
    assert delta["snapshot_head"] == SNAPSHOT_HEAD
    assert delta["predecessor_head"] == ACCEPTED_HEAD
    assert "product/content_family_probe.py" in delta["changed_paths_sample"]

    adj = diag["adjudication"]
    assert adj["status"] == "UNADJUDICATED"
    assert adj["accepted"] is False
    assert adj["product_defect"] is False
    assert adj["verdict_written"] is False


def test_raw_snapshot_and_logs_are_committed_and_credential_free():
    raw = _load(RAW)
    assert raw["schema"] == "github-actions-run-jobs-snapshot/1"
    assert raw["run"]["id"] == int(RESUMED_RUN_ID)
    assert raw["logs_endpoint_status"] == 200
    assert raw["token_material_in_artifact"] is False
    jobs = {j["name"]: j for j in raw["jobs"]}
    assert jobs["team"]["conclusion"] == "success"
    assert jobs["audit"]["conclusion"] == "failure"
    assert jobs["integrate"]["conclusion"] == "skipped"
    audit_ann = raw["annotations"][str(jobs["audit"]["id"])]
    joined = " | ".join(a.get("message", "") for a in audit_ann)
    assert "LEX_WORK_QUANTUM_EXPIRED seconds=2700" in joined
    assert "exit code 78" in joined

    manifest = _load(LOGS / "MANIFEST.json")
    by_name = {e["job_name"]: e for e in manifest["logs"]}
    for job in ("team", "audit", "resilience"):
        assert by_name[job]["http_status"] == 200, job
        assert (LOGS / by_name[job]["file"]).is_file()
    assert (LOGS / "audit.log").read_text(encoding="utf-8").count(
        "LEX_WORK_QUANTUM_EXPIRED seconds=2700") >= 1

    for path in [RAW, LOGS / "audit.log", LOGS / "team.log",
                 LOGS / "resilience.log", LOGS / "MANIFEST.json"]:
        assert not CREDENTIAL_RE.search(path.read_text(encoding="utf-8")), path


def test_fixed_path_family_excludes_verification_outputs_but_keeps_history():
    from product import content_family_probe as cfp

    sample = "results/product/offline_slice/43373102286_verify/rent-default.bundle.json"
    flagship = "results/product/offline_slice/20261024T142517Z/rent-default.bundle.json"
    assert cfp.is_verification_bundle(sample) is True
    assert cfp.is_verification_bundle(flagship) is False
    all_paths = {str(p.relative_to(ROOT)) for p in cfp.all_bundle_paths()}
    fixed_paths = {str(p.relative_to(ROOT)) for p in cfp.bundle_paths()}
    assert sample in all_paths
    assert sample not in fixed_paths
    assert all_paths - fixed_paths == {
        p for p in all_paths if cfp.is_verification_bundle(p)
    }

    rec = _load(FAMILY)
    totals = rec["fixed_path_family"]["totals"]
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
    assert all(not cfp.is_verification_bundle(b["path"])
               for b in rec["fixed_path_family"]["bundles"])
    # Every bundle committed when this artifact was generated - including
    # ad-hoc verification output - stays in the historical/all-committed
    # population, so excluding verify dirs from the family does not delete
    # evidence.  The count is pinned to the artifact's OWN bundle list, not to
    # the live tree: a later cycle's verification output is evidence for a new
    # run-id artifact and must never be inserted into this historical record
    # (append-only rule; the 43406325896 in-place rewrite was reverted).
    assert rec["all_committed"]["totals"]["n_bundles"] == 149
    assert rec["all_committed"]["totals"]["n_bundles"] == len(
        rec["all_committed"]["bundles"])
    assert rec["all_committed"]["totals"]["defect_histogram"] == {
        "D1_empty_evidence": 0,
        "D2_letterhead_zone": 44,
        "D3_markup_residue": 31,
        "D4_language_marker_mismatch": 7,
    }
    assert rec["false_reject_count"] == 0
    assert rec["confirmed_set"]["decision_id"] == "bstger_SK.2023.49"
    assert rec["confirmed_set"]["still_verified"] is True
    assert rec["ordered_work_2_full_success_rule"]["met"] is True


def test_end_to_end_slice_and_page_contract_on_current_bytes():
    summary = _load(SLICE / "summary.json")
    assert summary["bundle"] == str(BUNDLE.relative_to(ROOT))
    assert summary["mode"] == "full_loop"
    assert summary["degraded"] is False
    assert summary["page_contract"] is True
    assert summary["page_contract_detail"] == "PASS 70 assertions"
    stats = summary["stats"]
    assert stats["n_decisions"] == 100
    assert stats["n_clusters"] == 8
    assert stats["rows_with_source_link"] == 100
    assert stats["rows_with_xy"] == 100
    assert stats["rows_with_cluster_id"] == 100
    assert stats["answer_status"] == "ready"
    assert stats["cited_decision_ids"] == 4
    assert stats["geometry_preserved_by_enrich"] is True
    assert stats["fixture_replay"]["network"] == "none"

    bundle = _load(BUNDLE)
    rows = bundle["decisions"]
    assert len(rows) == 100
    assert len(bundle.get("clusters") or []) == 8
    assert all(r.get("x") is not None and r.get("y") is not None for r in rows)
    assert all(r.get("cluster_id") is not None for r in rows)
    assert all(r.get("canonical_url") for r in rows)
    answer = bundle.get("answer") or {}
    assert answer.get("status") == "ready"
    assert len(answer.get("cited_decision_ids") or []) == 4
    offline = bundle["provenance"]["offline_slice"]
    assert offline["network"] == "none"
    assert offline["geometry_preserved"] is True

    from offline_slice import verify_page
    ok, detail = verify_page(BUNDLE)
    assert ok, detail


def test_pointer_pin_amendment_covers_the_resumed_cycle_test():
    """Predecessor cycle test must not equality-pin the live pointer."""
    src = (ROOT / "product/tests/test_cycle_43363900852.py").read_text(
        encoding="utf-8")
    assert not re.search(
        r'assert st\["current_cycle_run_id"\] == int\(EXECUTING_RUN_ID\)',
        src), "stale live-pointer equality pin returned"
    assert 'st["current_cycle_run_id"] >= int(EXECUTING_RUN_ID)' in src
    assert "POINTER-PIN AMENDMENT" in src
    proc = subprocess.run(
        [sys.executable, "-m", "pytest",
         "product/tests/test_cycle_43363900852.py",
         "product/tests/test_cycle_43357207555.py", "-q", "--maxfail=1"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=900,
        check=False)
    assert proc.returncode == 0, proc.stdout[-4000:] + proc.stderr[-1500:]


def test_audit_readiness_profile_is_registered_for_this_run():
    from product import audit_readiness as ar

    prof = ar.select_profile(EXECUTING_RUN_ID)
    assert prof["resumed_run_id"] == RESUMED_RUN_ID
    assert prof["predecessor_run_id"] == PREDECESSOR_RUN_ID
    assert prof["mechanism_kind"] == "observed"
    assert prof["delta_kind"] == "committed"
    assert prof["classification"] == (
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE")
    assert prof["changed_files"] == CHANGED_FILES
    assert prof["cycle_test"] == f"product/tests/test_cycle_{EXECUTING_RUN_ID}.py"
    assert Path(prof["raw"]).is_file()
    assert Path(prof["resume_diag"]).is_file()
    assert Path(prof["current_report"]).is_file()
    assert Path(prof["content_family"]).is_file()


def test_accepted_pointer_satisfies_both_halves():
    st = _load(STATE)
    assert st["accepted_run_id"] == ACCEPTED_RUN_ID
    assert st["accepted_commit"] == ACCEPTED_HEAD
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
    assert st["cycle_status"] == "COMPLETE"
    for flag in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                 "ready_for_owner_session"):
        assert st[flag] is False, f"{flag} must stay fail-closed"
    # POINTER-PIN AMENDMENT: this is the live pointer's cycle, but a later
    # successor may legitimately advance it without regressing anything.
    assert st["current_cycle_run_id"] >= int(EXECUTING_RUN_ID)
    block = st[f"cycle_{EXECUTING_RUN_ID}_operational_resume"]
    assert block["run_id"] == int(EXECUTING_RUN_ID)
    assert block["direction_version"] == 68
    assert block["resumed_snapshot"]["run_id"] == int(RESUMED_RUN_ID)
    assert block["validation_failure_repaired"]["family_population"] is not None
    assert REPORT.is_file()
    assert not (ROOT / "results" / "audit" / "product"
                / f"CYCLE_{EXECUTING_RUN_ID}_GATE.json").exists()
    assert not (ROOT / "reports" / "audit" / "product"
                / f"CYCLE_{EXECUTING_RUN_ID}.md").exists()
