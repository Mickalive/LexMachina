"""Operational resume 44711032839: finish snapshot 44700830021.

The resumed run's team job was green (10/10) with an 8-file durable delta,
while its independent audit died on the workflow's own work quantum before
the gate step could run.  The mechanism is OBSERVED from public check-run
annotations (not inferred): ``LEX_WORK_QUANTUM_EXPIRED seconds=2700 pid=2391``
and ``Process completed with exit code 78`` on the audit job's Independent
audit step after 2705.0 s.  No gate file, no audit ref and no promotion exist
for 44700830021; the run is UNADJUDICATED.

This test re-derives that diagnosis from the committed raw snapshot and the
resume diagnosis, pins the re-verified answer-sourcing deliverable, the
audit-readiness dossier, the accepted-pointer hygiene and the fail-closed
posture.  No gate verdict is minted here: the independent auditor owns
``results/audit/product/CYCLE_44711032839_GATE.json``.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
for _p in (str(ROOT), str(ROOT / "product")):
    if _p not in sys.path:
        sys.path.insert(0, str(ROOT))

RUN = "44711032839"
RESUMED = "44700830021"
PREDECESSOR = "44694975109"
SNAPSHOT_SHA = "6fc8826545ed333d3a8f5c5816e2e2170b8eb71d"
PREDECESSOR_SHA = "3928818e7fd6e38ff3eb85206cf3ab9e9faef0bf"

STATE = ROOT / "state" / "product.json"
RAW = ROOT / "results" / "product" / "orchestration" / (
    f"CYCLE_{RESUMED}_run_jobs_raw.json")
DIAG = ROOT / "results" / "product" / "orchestration" / (
    f"CYCLE_{RESUMED}_resume_diagnosis.json")
VERIF = ROOT / "results" / "product" / "answer_sourcing" / (
    f"CYCLE_{RUN}_verification.json")
DOSSIER = ROOT / "results" / "product" / "audit_readiness" / (
    f"CYCLE_{RUN}_audit_readiness.json")
REPORT = ROOT / "reports" / "product" / f"CYCLE_{RUN}.md"
GATE = ROOT / "results" / "audit" / "product" / f"CYCLE_{RUN}_GATE.json"
GATE_RESUMED = ROOT / "results" / "audit" / "product" / (
    f"CYCLE_{RESUMED}_GATE.json")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True,
                          text=True, check=check)


def test_raw_snapshot_records_the_observed_quantum_expiry():
    raw = _load(RAW)
    assert raw["schema"] == "github-actions-run-jobs-snapshot/1"
    assert raw["run"]["id"] == int(RESUMED)
    assert raw["run"]["conclusion"] == "failure"
    # The job logs were NOT downloadable; only the annotations are public.
    assert raw["logs_endpoint_status"] == 403

    jobs = {j["name"]: j for j in raw["jobs"]}
    team = jobs["team"]
    assert team["conclusion"] == "success"
    steps = {s["name"]: s["conclusion"] for s in team["steps"]}
    assert steps["Run lane cycle"] == "success"
    assert steps["Validate active MVP producer state"] == "success"
    assert steps["Enforce lane write scope"] == "success"
    assert steps["Persist team snapshot"] == "success"

    audit = jobs["audit"]
    assert audit["conclusion"] == "failure"
    asteps = {s["name"]: s["conclusion"] for s in audit["steps"]}
    assert asteps["Independent audit"] == "failure"
    assert asteps["Enforce audit scope and read gate"] == "skipped"
    assert asteps["Persist audit snapshot"] == "skipped"
    assert jobs["integrate"]["conclusion"] == "skipped"

    ann = raw["annotations"][str(audit["id"])]
    messages = " | ".join(a.get("message", "") for a in ann)
    assert "LEX_WORK_QUANTUM_EXPIRED seconds=2700" in messages
    assert "exit code 78" in messages
    # the independent audit step ran 2705.0 s, past the 2700 s quantum
    ind = next(s for s in audit["steps"]
               if s["name"] == "Independent audit")
    assert ind["started_at"] == "2026-11-20T08:43:20Z"
    assert ind["completed_at"] == "2026-11-20T09:28:25Z"


def test_resume_diagnosis_classifies_and_preserves_the_delta():
    diag = _load(DIAG)
    assert diag["run_id"] == RESUMED
    assert diag["predecessor_run_id"] == PREDECESSOR
    orch = diag["orchestration"]
    assert orch["classification"] == (
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE")
    mech = orch["mechanism"]
    assert mech["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert mech["quantum_expired"] is True
    assert mech["quantum_seconds"] == 2700
    assert mech["exit_code"] == 78
    assert orch["audit"]["gate_file_written"] is False
    assert orch["audit"]["independent_audit_step_seconds"] == 2705.0
    assert orch["team"]["team_snapshot_persisted"] is True
    assert orch["team"]["producer_state_validation_ran"] is True

    delta = diag["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["snapshot_head"] == SNAPSHOT_SHA
    assert delta["predecessor_head"] == PREDECESSOR_SHA
    assert delta["changed_files"] == 8
    sample = " ".join(delta["changed_paths_sample"])
    for needle in ("product/tests/test_answer_sourcing.py",
                   "reports/product/CYCLE_44700830021.md",
                   "results/product/answer_sourcing/"
                   "CYCLE_44700830021_verification.json"):
        assert needle in sample, needle

    adj = diag["adjudication"]
    assert adj["status"] == "UNADJUDICATED"
    assert adj["accepted"] is False
    assert adj["verdict_written"] is False
    assert adj["product_defect"] is False


def test_snapshot_lineage_and_no_gate_minted():
    # the resumed snapshot is an ancestor of this checkout's lineage
    anc = _git("merge-base", "--is-ancestor", SNAPSHOT_SHA, "HEAD",
               check=False)
    assert anc.returncode == 0, "snapshot commit is not in this lineage"
    # no auditor-namespace file for either run is present in the tree
    tree = _git("ls-tree", "-r", "--name-only", "HEAD").stdout
    for run in (RUN, RESUMED):
        assert f"results/audit/product/CYCLE_{run}_GATE.json" not in tree
        assert f"reports/audit/product/CYCLE_{run}.md" not in tree
    assert not GATE.exists() and not GATE_RESUMED.exists()
    # nothing pending in the auditor namespace either
    pending = _git("status", "--porcelain", "-uall").stdout.splitlines()
    bad = [ln for ln in pending
           if ln[3:].startswith(("results/audit/product/",
                                 "reports/audit/product/"))]
    assert bad == [], bad
    # no /audit ref exists for the resumed or executing run on origin
    # (network assertion; tolerate an unreachable remote by recording it)
    for run in (RESUMED, RUN):
        proc = _git("ls-remote", "--heads", "origin",
                    f"refs/heads/cycle/core/product/{run}/audit",
                    check=False)
        if proc.returncode != 0:
            continue  # remote unreachable: local absence above still holds
        assert proc.stdout.strip() == "", (run, proc.stdout)


def test_answer_sourcing_deliverable_reverified_this_cycle():
    v = _load(VERIF)
    assert v["run_id"] == RUN
    assert v["resumed_snapshot_run_id"] == RESUMED
    assert v["verdict"] == "PASS"
    checks = v["checks"]
    assert len(checks) >= 10 and all(checks.values())
    assert v["bundle"]["n_decisions"] >= 40
    assert v["bundle"]["answer_status"] == "ready"
    assert v["bundle"]["geometry_preserved"] is True
    src = v["writers"]["answer_fixture_source"]
    note = v["writers"]["answer_counter_note"]
    assert src["applied"] is True and src["n_quotes"] >= 1
    assert note["applied"] is True and note["n_counter_rows"] >= 1
    assert v["citation_validity"]["n_unresolved"] == 0
    assert v["validate_bundle_errors"] == []
    assert v["frozen_content_predicates"]["status"] == (
        "REPORTED_ONLY_NOT_EDITED_NOR_REDERIVED")
    assert all(not r["frozen_defects"]
               for r in v["frozen_content_predicates"]["verified_rows_scanned"])


def test_state_attribution_pointer_hygiene_and_posture():
    from product.state_contract import accepted_pointer_evidence
    st = _load(STATE)
    assert isinstance(st["current_cycle_run_id"], int)
    assert st["current_cycle_run_id"] == int(RUN)
    hist = {str(h.get("run_id")): h for h in st.get("run_history") or []}
    assert RUN in hist
    assert hist[RUN]["status"] == "OPERATIONAL_RESUME_AUDIT_READINESS_DOSSIER"
    assert hist[RUN]["audit_gate"] == "NONE_YET"
    # the resumed run's own history entry is preserved, never re-labelled
    assert RESUMED in hist
    assert hist[RESUMED]["status"] == "OPERATIONAL_RESUME_SOURCE_WRITER_VERIFICATION"

    block = st.get(f"cycle_{RUN}_operational_resume") or {}
    assert block.get("run_id") == int(RUN)
    assert block["resumed_snapshot"]["run_id"] == int(RESUMED)
    assert block["resumed_snapshot"]["team_ref_head"] == SNAPSHOT_SHA
    assert block["verification_verdict"] == "PASS (10/10 checks)"
    assert block["no_gate_minted"] is True
    assert block["no_frozen_artifact_touched"] is True
    adv = block["accepted_pointer_advance"]
    assert adv["from"] == "CYCLE_40269774540 / 5adaa66d"
    assert adv["to"] == "CYCLE_40284658455 / 7be4480e"
    assert adv["both_halves_reverified"] is True

    # accepted pointer hygiene (ordered work item 4): the pointer names the
    # LATEST accept and satisfies both halves of requirement 4
    ev = accepted_pointer_evidence(st, ROOT)
    assert ev["problems"] == [], ev
    assert st["accepted_run_id"] == "CYCLE_40284658455"
    assert st["accepted_commit"].startswith("7be4480e")
    assert "CYCLE_40269774540" in st["accepted_run_supersession"]
    gate = _load(ROOT / "results" / "audit" / "product"
                 / "CYCLE_40284658455_GATE.json")
    assert gate["gate"] == "PASS" and gate["safe_to_integrate"] is True
    introducing = _git("log", "--diff-filter=A", "--format=%s", "--",
                       "results/audit/product/CYCLE_40284658455_GATE.json")
    assert introducing.stdout.strip() == "accept product cycle 40284658455"

    for flag in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                 "ready_for_owner_session", "owner_decision_required"):
        assert st.get(flag) is False, flag
    assert st.get("continue_recommended") is True
    assert st.get("direction_version") == 68
    assert "UNADJUDICATED" in st["next_recommendation"]


def test_audit_readiness_profile_is_pinned_for_both_run_ids():
    from product import audit_readiness as ar
    for run_id in (RUN, RESUMED):
        prof = ar.select_profile(run_id)
        assert prof["resumed_run_id"] == RESUMED
        assert prof["predecessor_run_id"] == PREDECESSOR
        assert prof["classification"] == (
            "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE")
        assert prof["failed_job"] == "audit"
        assert prof["delta_kind"] == "committed"
        assert prof["quantum_seconds"] == 2700
        assert prof["exit_code"] == 78
        assert prof["changed_files"] == 8
        assert (ROOT / prof["raw"]).is_file()
        assert (ROOT / prof["resume_diag"]).is_file()
        assert (ROOT / prof["cycle_test"]).is_file()
        assert (ROOT / prof["current_report"]).is_file()
    try:
        ar.select_profile("99999999999")
    except SystemExit:
        pass
    else:  # pragma: no cover - defensive
        raise AssertionError("select_profile must fail closed on unknown runs")


def test_audit_readiness_dossier_passes():
    if not DOSSIER.is_file():
        pytest.skip("dossier not yet written (written at the end of the cycle)")
    art = _load(DOSSIER)
    assert art["schema"] == "product-audit-readiness/1"
    assert art["run_id"] == RUN
    assert art["resumed_run_id"] == RESUMED
    assert art["direction_version"] == 68
    assert art["overall_status"] == "PASS", art["failed_checks"]
    assert art["failed_checks"] == []
    statuses = {c["id"]: c["status"] for c in art["checks"]}
    for mandatory in ("runtime_preflight", "state_contract", "posture",
                      "resumed_diagnosis", "claim_artifacts", "cycle_test",
                      "progressive_smoke", "mvp_core_tests",
                      "audit_namespace"):
        assert statuses[mandatory] == "PASS", (mandatory, statuses)
    c1 = next(c for c in art["claims"] if c["id"] == "C1")
    assert "work quantum" in c1["claim"] and "2700" in c1["claim"]
    assert art["posture"]["gate_minted"] is False
    assert art["posture"]["run_label"] == "UNADJUDICATED"
    # the dossier must not be an audit artifact
    assert "results/audit/" not in json.dumps(art.get("audit_entry_points", {}))


def test_report_of_record_names_both_runs_and_the_observed_mechanism():
    text = REPORT.read_text(encoding="utf-8")
    assert RUN in text and RESUMED in text
    assert "LEX_WORK_QUANTUM_EXPIRED" in text
    assert "2705" in text
    assert "exit 78" in text or "exit code 78" in text
    assert "UNADJUDICATED" in text
    assert "gate=PASS" in text  # cites the accepted pointer's gate as evidence
    # the report must not claim a verdict of its own for this run
    assert "gate=REVISE" not in text and "gate=BLOCKED" not in text
    # it must name the dossier as the auditor's entry point
    assert f"CYCLE_{RUN}_audit_readiness.json" in text
