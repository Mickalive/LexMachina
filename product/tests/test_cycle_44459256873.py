"""Operational resume 44459256873: rc-78 audit-quantum snapshot 44452532371.

Runs 44444791517 and 44452532371 both ended in ``failure`` with the team job
green and the audit job dying at ``Independent audit`` under the workflow's own
``LEX_WORK_QUANTUM_EXPIRED seconds=2700`` annotation (exit 78): the audit agent
burned its 45-minute quantum before writing a gate, so integrate never ran and
no ``/audit`` ref exists.  This test locks that mechanism
(OBSERVED_QUANTUM_EXPIRED), the committed 40-file durable delta of the resumed
snapshot, and the six-run failure-chain facts, keeping the run UNADJUDICATED
with no producer-minted gate.

It also pins the inherited v68 rejection-leg repair adopted from snapshot
44444791517 (``a20915d8``): a content-FAIL row that was already
``verified=false`` must never be published in ``retained_content_sound`` (which
asserts the opposite) — it goes to ``defective_already_unverified`` with its
true defect list — while a verified row still downgrades through the ordinary
leg with ``before.counter_evidence_verified is True``.
"""
import copy
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

EXECUTING_RUN_ID = "44459256873"
RESUMED_RUN_ID = "44452532371"
PREDECESSOR_RUN_ID = "44444791517"
ACCEPTED_RUN_ID = "40284658455"
ACCEPTED_COMMIT = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
SNAPSHOT_HEAD = "294f1cfc847a584d3099c04a1f5a95322661d88c"
PREDECESSOR_HEAD = "a20915d8e42483c00f1591d5ecde5f7786cd534a"

STATE = ROOT / "state" / "product.json"
ORCH = ROOT / "results" / "product" / "orchestration"
RAW = ORCH / f"CYCLE_{RESUMED_RUN_ID}_run_jobs_raw.json"
DIAG = ORCH / f"CYCLE_{RESUMED_RUN_ID}_resume_diagnosis.json"
CHAIN = ORCH / f"CYCLE_{EXECUTING_RUN_ID}_failure_chain.json"
SMOKE = (ROOT / "results" / "product" / "progressive_smoke"
         / f"CYCLE_{EXECUTING_RUN_ID}_progressive_smoke.json")
REPORT = ROOT / "reports" / "product" / f"CYCLE_{EXECUTING_RUN_ID}.md"
DOSSIER = (ROOT / "results" / "product" / "audit_readiness"
           / f"CYCLE_{EXECUTING_RUN_ID}_audit_readiness.json")
GATE = ROOT / "results" / "audit" / "product" / (
    f"CYCLE_{ACCEPTED_RUN_ID}_GATE.json")

BEFORE_BUNDLE = (ROOT / "results" / "product" / "offline_slice"
                 / "20261024T142517Z" / "rent-default.bundle.json")
AFTER_BUNDLE = (ROOT / "results" / "product" / "offline_slice"
                / "20261025T070356Z" / "rent-default.bundle.json")
D2_DECISION = "gr_gerichte_ERZ 2010 25"
QID = "fr-bail-entretien"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_public_snapshot_shows_rc78_quantum_at_the_independent_audit_step():
    raw = _load(RAW)
    assert raw["schema"] == "product-actions-run-jobs-snapshot/1"
    assert raw["run"]["id"] == int(RESUMED_RUN_ID)
    assert raw["run"]["conclusion"] == "failure"
    assert raw["run"]["head_sha"].startswith("e1592f44")
    assert raw["logs_endpoint_status"] == 403  # logs are NOT available
    jobs = {j["name"]: j for j in raw["jobs"]}
    team_steps = {s["name"]: s["conclusion"]
                  for s in jobs["team"]["steps"]}
    assert jobs["team"]["conclusion"] == "success"
    assert team_steps["Run lane cycle"] == "success"
    assert team_steps["Validate active MVP producer state"] == "success"
    assert team_steps["Enforce lane write scope"] == "success"
    assert team_steps["Persist team snapshot"] == "success"
    audit_steps = {s["name"]: s["conclusion"]
                   for s in jobs["audit"]["steps"]}
    assert jobs["audit"]["conclusion"] == "failure"
    assert audit_steps["Independent audit"] == "failure"
    assert audit_steps["Enforce audit scope and read gate"] == "skipped"
    assert audit_steps["Persist audit snapshot"] == "skipped"
    assert jobs["integrate"]["conclusion"] == "skipped"
    ann_text = json.dumps(raw["annotations"])
    assert "Process completed with exit code 78." in ann_text
    assert "LEX_WORK_QUANTUM_EXPIRED seconds=2700" in ann_text
    assert "LEX_ZERO_DELTA_REPAIR" not in ann_text


def test_classifier_reproduces_the_observed_audit_quantum_mechanism():
    from product import audit_step_diagnosis as asd

    fresh = asd.classify(_load(RAW))
    assert fresh["classification"] == (
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE")
    mech = fresh["mechanism"]
    assert mech["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert mech["quantum_expired"] is True
    assert mech["quantum_seconds"] == 2700
    assert mech["exit_code"] == 78
    assert mech["annotations_available"] is True
    assert mech["logs_available"] is False
    assert "LEX_WORK_QUANTUM_EXPIRED" in mech["claim"]
    # A quantum expiry claims no provider/auth cause.
    assert "No provider or auth cause is claimed." in mech["claim"]
    assert fresh["observed_failure"]["quantum_expired"] is True
    assert fresh["adjudication"]["product_defect"] is False
    assert fresh["adjudication"]["verdict_written"] is False
    assert fresh["adjudication"]["team_work_preserved"] is True


def test_resume_diagnosis_proves_committed_delta_and_no_verdict():
    diag = _load(DIAG)
    assert diag["run_id"] == RESUMED_RUN_ID
    assert diag["predecessor_run_id"] == PREDECESSOR_RUN_ID
    orch = diag["orchestration"]
    assert orch["classification"] == (
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE")
    assert orch["mechanism"]["status"] == "OBSERVED_QUANTUM_EXPIRED"
    audit = orch["audit"]
    assert audit["failed_step"] == "Independent audit"
    assert audit["independent_audit_step_seconds"] == 2706.0
    assert audit["gate_file_written"] is False
    delta = diag["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["changed_files"] == 40
    assert delta["snapshot_head"] == SNAPSHOT_HEAD
    assert delta["predecessor_head"] == PREDECESSOR_HEAD
    sample = delta["changed_paths_sample"]
    assert sample, "changed_paths_sample must not be empty"
    for path in sample:
        assert path.startswith("results/product/query_cache/"), path
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["accepted"] is False
    assert diag["adjudication"]["audit"]["gate_file_present"] is False


def test_inherited_span_repair_keeps_defective_unverified_rows_out_of_sound():
    """Direction v68 P0 pin: the mislabel repaired on snapshot 44444791517.

    A content-FAIL row that was ALREADY verified=false has no flag to flip, so
    it must be published under ``defective_already_unverified`` with its true
    defect list — never under ``retained_content_sound``, whose note claims the
    row passes the frozen D1-D4 content predicates.  A verified row still
    downgrades through the ordinary leg with ``before`` showing verified=True.
    """
    from product.query import counter_evidence_span as ces

    before = ces.apply_verified_span_selection(
        copy.deepcopy(_load(BEFORE_BUNDLE)), qid=QID)
    prov_b = before["provenance"]["counter_evidence_span"]
    row_b = next(r for r in before["decisions"]
                 if r["decision_id"] == D2_DECISION)
    assert row_b["counter_evidence_verified"] is False
    assert row_b["counter_evidence_unevidenced_reason"] == "d2_letterhead_zone"
    downs = prov_b.get("downgrades") or []
    assert len(downs) == 1
    assert downs[0]["decision_id"] == D2_DECISION
    assert downs[0]["before"]["counter_evidence_verified"] is True
    assert downs[0]["reason_code"] == "d2_letterhead_zone"
    assert "D2_letterhead_zone" in downs[0]["defects"]
    assert prov_b["n_defective_already_unverified"] == 0

    after = ces.apply_verified_span_selection(
        copy.deepcopy(_load(AFTER_BUNDLE)), qid=QID)
    prov_a = after["provenance"]["counter_evidence_span"]
    row_a = next(r for r in after["decisions"]
                 if r["decision_id"] == D2_DECISION)
    assert row_a["counter_evidence_verified"] is False
    assert row_a["counter_evidence_unevidenced"] is True
    assert row_a["counter_evidence_unevidenced_reason"] == "d2_letterhead_zone"
    # No verified flag existed to downgrade: zero downgrades, one published
    # defective-already-unverified record with the TRUE defect list.
    assert prov_a["n_downgraded"] == 0
    assert prov_a["n_defective_already_unverified"] == 1
    bad = prov_a["defective_already_unverified"]
    assert bad[0]["decision_id"] == D2_DECISION
    assert bad[0]["leg"] == "seam_abstention_defective_already_unverified"
    assert bad[0]["defects"] == ["D2_letterhead_zone"]
    assert bad[0]["counter_evidence_verified"] is False
    # THE BUG PIN: nothing content-defective is ever retained as sound.
    retained = prov_a["retained_content_sound"]
    assert prov_a["n_retained_content_sound"] == len(retained)
    assert all(entry.get("defects") == [] for entry in retained)
    assert D2_DECISION not in {e["decision_id"] for e in retained}
    # Idempotent: re-applying changes no counts (repair is deterministic).
    again = ces.apply_verified_span_selection(copy.deepcopy(after), qid=QID)
    prov_again = again["provenance"]["counter_evidence_span"]
    assert prov_again["n_defective_already_unverified"] == 1
    assert prov_again["n_downgraded"] == 0


def test_failure_chain_records_six_failed_runs_and_zero_audit_refs():
    chain = _load(CHAIN)
    assert chain["schema"] == "product-failure-chain/1"
    assert chain["run_id"] == EXECUTING_RUN_ID
    assert chain["resumed_run_id"] == RESUMED_RUN_ID
    facts = chain["chain_facts"]
    assert facts["n_runs"] == 6
    assert facts["all_failed"] is True
    assert facts["audit_refs_present"] == 0
    assert facts["runs_with_zero_durable_delta"] == [
        "44444510847", "44452000258", "44452272852"]
    assert facts["distinct_team_heads"] == [
        SNAPSHOT_HEAD, PREDECESSOR_HEAD,
        "d8a3b7c58dfa97df1c9b984a7f2b1c8ba5734e91"]
    by_id = {str(r["run_id"]): r for r in chain["runs"]}
    assert set(by_id) == {"44435078310", "44444510847", "44444791517",
                          "44452000258", "44452272852", "44452532371"}
    for run in chain["runs"]:
        assert run["conclusion"] == "failure"
        assert run["audit_ref_present"] is False
    # The three team-green rounds died at the audit step with rc-78 quantum
    # annotations; the three zero-delta rounds died at the lane-cycle step.
    for rid in ("44435078310", "44444791517", "44452532371"):
        anns = json.dumps(by_id[rid]["failure_annotations"])
        assert "exit code 78" in anns, rid
        assert "LEX_WORK_QUANTUM_EXPIRED" in anns, rid
        assert by_id[rid]["team_head"] in (SNAPSHOT_HEAD, PREDECESSOR_HEAD,
                                           "d8a3b7c58dfa97df1c9b984a7f2b1c8ba5734e91")
    for rid in ("44444510847", "44452000258", "44452272852"):
        assert by_id[rid]["failure_annotations"]["team"] == [
            "Process completed with exit code 1."], rid
    # Claim ceiling: logs were unavailable, so no provider/auth mechanism is
    # claimed for the exit-1 rounds, and nothing here is adjudicated.
    ceiling = chain["claim_ceiling"]
    assert "logs endpoint HTTP 403" in ceiling
    assert "no provider, auth or gateway mechanism is claimed" in ceiling
    assert "not a verdict" in ceiling


def test_inherited_snapshot_delta_is_cache_only_and_repair_is_ancestor():
    """Snapshot 294f1cfc vs predecessor a20915d8 is a cache refresh only."""
    out = subprocess.run(
        ["git", "diff", "--name-only",
         f"{PREDECESSOR_HEAD}..{SNAPSHOT_HEAD}"],
        cwd=str(ROOT), capture_output=True, text=True, check=True).stdout
    paths = [p for p in out.splitlines() if p]
    assert len(paths) == 40
    assert all(p.startswith("results/product/query_cache/") for p in paths)
    # The inherited rejection-leg work (and this branch) descend from both.
    for sha in (PREDECESSOR_HEAD, SNAPSHOT_HEAD):
        rc = subprocess.run(
            ["git", "merge-base", "--is-ancestor", sha, "HEAD"],
            cwd=str(ROOT), capture_output=True).returncode
        assert rc == 0, f"{sha} must be an ancestor of HEAD"


def test_state_records_this_resume_and_stays_fail_closed():
    st = _load(STATE)
    # The pointer names the executing cycle. A later operational resume
    # (44464605045) advances it; this run's own block and history stay intact.
    assert st["current_cycle_run_id"] in (int(EXECUTING_RUN_ID), 44464605045)
    assert st["accepted_run_id"] == f"CYCLE_{ACCEPTED_RUN_ID}"
    assert st["accepted_commit"] == ACCEPTED_COMMIT
    blk = st[f"cycle_{EXECUTING_RUN_ID}_operational_resume"]
    assert blk["resumed_snapshot"]["run_id"] == int(RESUMED_RUN_ID)
    assert blk["predecessor_run_id"] == int(PREDECESSOR_RUN_ID)
    assert blk["mechanism"] == "OBSERVED_QUANTUM_EXPIRED"
    assert blk["durable_delta"] == "COMMITTED_DELTA"
    assert blk["team_ref_head"] == SNAPSHOT_HEAD
    assert "UNADJUDICATED" in blk["status"].upper()
    assert (ROOT / blk["diagnosis"]).is_file()
    assert (ROOT / blk["raw_snapshot"]).is_file()
    assert (ROOT / blk["report"]).is_file()
    assert blk["verdict"] == "NONE_UNADJUDICATED"
    assert st["direction_version"] == 68
    assert st["cycle_status"] == "COMPLETE"
    for key in ("continue_recommended",):
        assert st[key] is True
    for key in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                "ready_for_owner_session"):
        assert st[key] is False
    hist = {str(h.get("run_id")): h for h in st["run_history"]}
    assert RESUMED_RUN_ID in hist
    assert "QUANTUM" in hist[RESUMED_RUN_ID]["status"].upper()
    assert PREDECESSOR_RUN_ID in hist
    assert EXECUTING_RUN_ID in hist
    assert hist[EXECUTING_RUN_ID]["audit_gate"] == "NONE_YET"


def test_accepted_pointer_has_both_halves_of_requirement_4():
    gate = _load(GATE)
    assert gate["gate"] == "PASS"
    assert gate["safe_to_integrate"] is True
    assert gate["required_fixes"] == []
    head = subprocess.run(
        ["git", "ls-remote", "--heads", "origin", "refs/heads/lab/product"],
        cwd=str(ROOT), capture_output=True, text=True, check=True).stdout
    assert head.startswith(ACCEPTED_COMMIT), (head, ACCEPTED_COMMIT)


def test_no_gate_or_verdict_was_minted_for_either_run():
    for run in (EXECUTING_RUN_ID, RESUMED_RUN_ID):
        assert not (ROOT / "results" / "audit" / "product" / (
            f"CYCLE_{run}_GATE.json")).exists()
        refs = subprocess.run(
            ["git", "ls-remote", "--heads", "origin",
             f"refs/heads/cycle/core/product/{run}/audit"],
            cwd=str(ROOT), capture_output=True, text=True,
            check=True).stdout
        assert refs == "", f"unexpected /audit ref for {run}"


def test_audit_readiness_instrument_models_this_failure_mode():
    from product import audit_readiness as ar

    prof = ar.select_profile(EXECUTING_RUN_ID)
    assert prof["mechanism_kind"] == "observed"
    assert prof["failed_job"] == "audit"
    assert prof["quantum_seconds"] == 2700
    assert prof["exit_code"] == 78
    assert prof["resumed_run_id"] == RESUMED_RUN_ID
    assert prof["predecessor_run_id"] == PREDECESSOR_RUN_ID
    assert prof["changed_files"] == 40
    assert prof["cycle_test"] == (
        f"product/tests/test_cycle_{EXECUTING_RUN_ID}.py")
    # Alias for the resumed run id must resolve to the same executing profile.
    assert ar.select_profile(RESUMED_RUN_ID)["resumed_run_id"] == RESUMED_RUN_ID
    dossier = _load(DOSSIER)
    # NOTE: the dossier runs THIS test (check_cycle_test), so the test must
    # only pin checks that are independent of its own run — asserting the
    # dossier's overall/cycle_test status from in here would deadlock the
    # fixpoint (the previous dossier on disk is the one being graded).
    by_id = {c["id"]: c for c in dossier["checks"]}
    for check_id in ("runtime_preflight", "state_contract", "posture",
                     "resumed_diagnosis", "claim_artifacts",
                     "progressive_smoke", "mvp_core_tests",
                     "audit_namespace"):
        assert by_id[check_id]["status"] == "PASS", (check_id,
                                                     by_id[check_id])
    rec = by_id["resumed_diagnosis"]
    assert rec["detail"]["mechanism_kind"] == "observed"
    assert rec["detail"]["delta_kind"] == "committed"
    assert rec["detail"]["changed_files"] == 40
    assert by_id["cycle_test"]["detail"]["present"] is True
    assert by_id["cycle_test"]["detail"]["path"] == (
        f"product/tests/test_cycle_{EXECUTING_RUN_ID}.py")
    assert dossier["resumed_run_id"] == RESUMED_RUN_ID
    assert dossier["predecessor_run_id"] == PREDECESSOR_RUN_ID
    try:
        ar.select_profile("99999999999")
    except SystemExit:
        pass
    else:  # pragma: no cover - defensive
        raise AssertionError("select_profile must fail closed on unknown runs")


def test_progressive_smoke_artifact_is_committed_and_pass():
    art = _load(SMOKE)
    assert art["schema"] == "product-progressive-smoke/1"
    assert art["run_id"] == EXECUTING_RUN_ID
    assert art["verdict"] == "PASS"
    assert art["checks_passed"] == art["checks_total"]
    assert art["checks_passed"] >= 20
    by_name = {c["check"]: c for c in art["checks"]}
    assert by_name["answer_has_citations"]["detail"] >= 1
    assert art["timings_s"]["server_boot_s"] < 3.0


def test_report_of_record_names_the_mechanism_and_the_route_around():
    text = REPORT.read_text(encoding="utf-8")
    assert EXECUTING_RUN_ID in text
    assert RESUMED_RUN_ID in text
    assert PREDECESSOR_RUN_ID in text
    assert "OBSERVED_QUANTUM_EXPIRED" in text
    assert "LEX_WORK_QUANTUM_EXPIRED" in text
    assert "UNADJUDICATED" in text
    assert "294f1cfc" in text
    assert "defective_already_unverified" in text
