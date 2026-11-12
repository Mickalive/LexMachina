"""Operational resume 42745308078 of snapshot 42738229187: diagnosis + quick-pick.

The resumed producer run's team job succeeded with a real 7-file delta, but its
independent-audit agent consumed the whole 2700 s work quantum (exit 78) before
writing a gate, so the run is UNADJUDICATED with no /audit ref.  This test
re-derives, from committed artifacts only:

* the orchestration classification from the public run/jobs snapshot
  (audit job, `Independent audit` step, annotation
  `LEX_WORK_QUANTUM_EXPIRED seconds=2700`, exit 78, gate steps skipped);
* the resume diagnosis: COMMITTED_DELTA 7 files over `origin/lab/product`,
  UNADJUDICATED, no audit ref;
* the inherited fixture-question replay deliverable (both the resumed run's
  artifact and this cycle's re-verification) — all five questions PASS with
  full row integrity and no network;
* the new frozen-question quick-pick: `FROZEN_QUICKPICK` byte-exact against
  `reality_check.LEGS`, a shipped button per slug, and the driver instrument;
* state hygiene: this run recorded in `run_history`, `current_cycle_run_id`
  names the EXECUTING run, posture flags FALSE, the advanced accepted pointer
  satisfies both halves of requirement 4, and the evidence refs resolve;
* the audit-readiness profile for this failure mode (mechanism_kind
  `observed`, fail-closed on unknown run ids);
* the audit namespace stays clean: the producer minted no gate and no
  auditor-namespace path is pending.

No frozen gate, rubric, threshold, verdict contract or serve verdict is read,
edited or re-scored; no run is labelled accepted or rejected.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "product"))

EXECUTING_RUN_ID = "42745308078"
RESUMED_RUN_ID = "42738229187"
ACCEPTED_RUN_ID = "40284658455"
ACCEPTED_COMMIT = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
QUANTUM_SECONDS = 2700
EXIT_CODE = 78
DELTA_FILES = 7

STATE = ROOT / "state" / "product.json"
ORCH = ROOT / "results" / "product" / "orchestration"
RAW = ORCH / f"CYCLE_{RESUMED_RUN_ID}_run_jobs_raw.json"
DIAG = ORCH / f"CYCLE_{RESUMED_RUN_ID}_resume_diagnosis.json"
REPLAY_RESUMED = (ROOT / "results" / "product" / "fixture_question_replay"
                  / f"CYCLE_{RESUMED_RUN_ID}.json")
REPLAY_THIS = (ROOT / "results" / "product" / "fixture_question_replay"
               / f"CYCLE_{EXECUTING_RUN_ID}.json")
REPORT = ROOT / "reports" / "product" / f"CYCLE_{EXECUTING_RUN_ID}.md"
QUICKPICK_HTML = ROOT / "product" / "static" / "query.html"
DRIVER = ROOT / "product" / "verify_quickpick.js"
QUICKPICK_TEST = ROOT / "product" / "tests" / "test_frozen_question_quickpick.py"
DOSSIER = (ROOT / "results" / "product" / "audit_readiness"
           / f"CYCLE_{EXECUTING_RUN_ID}_audit_readiness.json")
SLUGS = ("rent-default", "petty-theft-dismissal",
         "corporate-criminal-liability", "business-judgment-rule")


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(ROOT), capture_output=True, text=True,
        check=False).stdout


def test_raw_snapshot_records_the_audit_quantum_expiry_not_a_product_failure():
    from product import audit_step_diagnosis as asd
    snap = _load(RAW)
    assert snap["schema"] == "github-actions-run-jobs-snapshot/1"
    assert snap["run"]["id"] == int(RESUMED_RUN_ID)
    assert snap["run"]["conclusion"] == "failure"
    assert snap["logs_endpoint_status"] == 403  # no log text is claimed

    jobs = {j["name"]: j for j in snap["jobs"]}
    assert jobs["team"]["conclusion"] == "success"
    team_steps = {s["name"]: s["conclusion"] for s in jobs["team"]["steps"]}
    assert team_steps["Run lane cycle"] == "success"
    assert team_steps["Validate active MVP producer state"] == "success"
    assert team_steps["Enforce lane write scope"] == "success"
    assert team_steps["Persist team snapshot"] == "success"

    audit_steps = {s["name"]: s["conclusion"] for s in jobs["audit"]["steps"]}
    assert audit_steps["Independent audit"] == "failure"
    assert audit_steps["Enforce audit scope and read gate"] == "skipped"
    assert audit_steps["Persist audit snapshot"] == "skipped"
    assert jobs["integrate"]["conclusion"] == "skipped"

    rec = asd.classify(snap)
    assert rec["classification"] == "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    assert rec["audit"]["failed_step"] == "Independent audit"
    assert rec["audit"]["gate_file_written"] is False
    mech = rec["mechanism"]
    assert mech["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert mech["quantum_expired"] is True
    assert mech["quantum_seconds"] == QUANTUM_SECONDS
    assert mech["exit_code"] == EXIT_CODE
    assert "LEX_WORK_QUANTUM_EXPIRED" in (mech.get("claim") or "")
    # The audit step ran the full quantum, not a fast failure.
    assert rec["audit"]["independent_audit_step_seconds"] >= QUANTUM_SECONDS


def test_resume_diagnosis_classifies_committed_delta_and_unadjudicated():
    diag = _load(DIAG)
    assert diag["run_id"] == RESUMED_RUN_ID
    orch = diag["orchestration"]
    assert orch["classification"] == "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    assert orch["mechanism"]["status"] == "OBSERVED_QUANTUM_EXPIRED"
    delta = diag["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["changed_files"] == DELTA_FILES
    sample = delta["changed_paths_sample"]
    for needle in ("product/fixture_question_replay_probe.py",
                   "product/query/cache_replay.py",
                   "reports/product/CYCLE_42738229187.md"):
        assert any(needle in p for p in sample), needle
    adj = diag["adjudication"]
    assert adj["status"] == "UNADJUDICATED"
    assert adj["accepted"] is False
    assert adj["audit"]["audit_ref_present"] is False
    assert adj["audit"]["gate_file_present"] is False
    assert diag["orchestration"]["adjudication"]["product_defect"] is False


def test_inherited_fixture_replay_deliverable_reproduces_for_both_runs():
    for path in (REPLAY_RESUMED, REPLAY_THIS):
        art = _load(path)
        assert art["all_ok"] is True, path
        assert art["network"].startswith("none"), path
        questions = art["questions"]
        assert len(questions) == 5, path
        for q in questions:
            assert q["ok"] is True, (path, q["question"][:40])
            assert q["validation_errors"] == [], (path, q["question"][:40])
            assert q["rows_with_xy"] == q["n_decisions"] > 0
            assert q["rows_with_cluster_id"] == q["n_decisions"]
            assert q["rows_with_source_link"] == q["n_decisions"]
            assert q["replay_source"].startswith("product_query_cache_")
            assert q["network"] == "none"


def test_quickpick_is_byte_exact_with_frozen_legs_and_shipped():
    from reality_check import LEGS
    html = QUICKPICK_HTML.read_text(encoding="utf-8")
    m = re.search(r"const FROZEN_QUICKPICK=(\{.*?\});", html, re.S)
    assert m, "query.html must define FROZEN_QUICKPICK"
    qp = json.loads(m.group(1))
    assert set(qp) == set(LEGS) == set(SLUGS)
    for slug in SLUGS:
        assert qp[slug] == LEGS[slug], slug
        assert f'id="qp-{slug}"' in html, slug
    # One pipeline only: the click fills #q and calls the SAME run().
    assert 'getElementById("qp-"+slug)' in html
    assert 'document.getElementById("q").value=FROZEN_QUICKPICK[slug]' in html
    # The click listener must stay AFTER the harness attach() block, which the
    # first addEventListener("click",...) ordering contract depends on.
    assert html.index("LexGateSwitch.attach({") < html.index(
        'addEventListener("click",function(){')
    assert DRIVER.is_file(), "driver instrument missing"
    assert QUICKPICK_TEST.is_file(), "quick-pick test file missing"
    driver = DRIVER.read_text(encoding="utf-8")
    assert "/api/query/start with the frozen question" in driver
    assert "source-linked panel" in driver


def test_state_records_this_resume_fail_closed_with_a_current_pointer():
    st = _load(STATE)
    # POINTER-PIN AMENDMENT (product cycle 42983901071), following
    # ``test_cycle_40263666190_resume.py``: later cycles legitimately
    # advance the pointer past this cycle's era; only regression below this
    # cycle's executing run is a defect.
    assert st["current_cycle_run_id"] >= int(EXECUTING_RUN_ID), (
        "current_cycle_run_id regressed below this cycle's executing run",
        st["current_cycle_run_id"], EXECUTING_RUN_ID)
    assert st["direction_version"] == 68
    assert st["continue_recommended"] is True
    for flag in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                 "ready_for_owner_session"):
        assert st[flag] is False, flag

    hist = {str(h.get("run_id")): h for h in st.get("run_history") or []}
    assert EXECUTING_RUN_ID in hist
    entry = hist[EXECUTING_RUN_ID]
    assert "UNADJUDICATED" in entry["summary"]
    assert "QUANTUM" in entry["status"]
    assert entry["audit_gate"] == "NONE_YET"
    assert RESUMED_RUN_ID in hist
    assert "QUANTUM" in hist[RESUMED_RUN_ID]["status"]

    block = st["cycle_42745308078_operational_resume"]
    assert block["resumed_run"] == RESUMED_RUN_ID
    assert block["orchestration_failure_of_record"]["classification"] == (
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE")
    assert block["continue_recommended"] is True

    # Both halves of requirement 4 for the advanced pointer.
    from product.state_contract import accepted_pointer_evidence
    pointer = accepted_pointer_evidence(st, ROOT)
    assert pointer["problems"] == [], pointer
    assert st["accepted_run_id"] == f"CYCLE_{ACCEPTED_RUN_ID}"
    assert st["accepted_commit"] == ACCEPTED_COMMIT
    assert pointer["gate_ok"] is True and pointer["accept_commit_present"] is True
    # The audit ref for the accepted run is pruned; the report discloses it.
    assert "pruned" in REPORT.read_text(encoding="utf-8")

    refs = "\n".join(st.get("evidence_refs") or [])
    for needle in (
        f"CYCLE_{RESUMED_RUN_ID}_run_jobs_raw.json",
        f"CYCLE_{RESUMED_RUN_ID}_resume_diagnosis.json",
        f"CYCLE_{EXECUTING_RUN_ID}.json",
        "verify_quickpick.js",
        "test_frozen_question_quickpick.py",
        f"CYCLE_{EXECUTING_RUN_ID}.md",
        f"CYCLE_{EXECUTING_RUN_ID}_audit_readiness.json",
    ):
        assert needle in refs, needle
    for rel in (
        f"results/product/orchestration/CYCLE_{RESUMED_RUN_ID}_run_jobs_raw.json",
        f"results/product/orchestration/CYCLE_{RESUMED_RUN_ID}_resume_diagnosis.json",
        f"results/product/fixture_question_replay/CYCLE_{EXECUTING_RUN_ID}.json",
        f"reports/product/CYCLE_{EXECUTING_RUN_ID}.md",
        f"results/product/audit_readiness/CYCLE_{EXECUTING_RUN_ID}_audit_readiness.json",
    ):
        assert (ROOT / rel).is_file(), rel
    assert st["capabilities"]["frozen_question_quickpick"] is True


def test_audit_readiness_profile_models_this_failure_mode():
    from product import audit_readiness as ar
    prof = ar.select_profile(EXECUTING_RUN_ID)
    assert prof == ar.select_profile(RESUMED_RUN_ID)  # alias resolves identically
    assert prof["mechanism_kind"] == "observed"
    assert prof["failed_job"] == "audit"
    assert prof["quantum_seconds"] == QUANTUM_SECONDS
    assert prof["exit_code"] == EXIT_CODE
    assert prof["changed_files"] == DELTA_FILES
    assert prof["resumed_run_id"] == RESUMED_RUN_ID
    assert prof["cycle_test"] == "product/tests/test_cycle_42745308078.py"
    diag = _load(DIAG)
    sample = diag["durable_delta"]["changed_paths_sample"]
    for needle in prof["changed_paths_include"]:
        assert any(needle in p for p in sample), needle
    try:
        ar.select_profile("99999999999")
    except SystemExit:
        pass
    else:  # pragma: no cover - defensive
        raise AssertionError("select_profile must fail closed on unknown runs")


def test_dossier_and_report_exist_and_no_gate_was_minted():
    text = REPORT.read_text(encoding="utf-8")
    assert EXECUTING_RUN_ID in text and RESUMED_RUN_ID in text
    assert "UNADJUDICATED" in text
    assert "mints no gate" in text
    assert DOSSIER.is_file(), "audit-readiness dossier missing"
    dossier = _load(DOSSIER)
    assert dossier["resumed_run_id"] == RESUMED_RUN_ID
    assert dossier["direction_version"] == 68

    # The producer minted no auditor-namespace artifact for either run.
    for run in (RESUMED_RUN_ID, EXECUTING_RUN_ID):
        assert not (ROOT / "results" / "audit" / "product"
                    / f"CYCLE_{run}_GATE.json").exists(), run
        assert not (ROOT / "reports" / "audit" / "product"
                    / f"CYCLE_{run}.md").exists(), run
    pending = [ln[3:] for ln in _git("status", "--porcelain", "-uall").splitlines()
               if ln[3:].startswith(("results/audit/product/",
                                     "reports/audit/product/"))]
    assert pending == [], pending
