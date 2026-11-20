"""Operational resume 44723775560: finish snapshot 44711032839.

The resumed run's team job was green and persisted a 9-file durable delta
(c03dbab5 over 6fc88265), while its independent audit died on the workflow's
own work quantum before the gate step could run.  The mechanism is OBSERVED
from public check-run annotations (not inferred): ``LEX_WORK_QUANTUM_EXPIRED
seconds=2700 pid=3440`` and ``Process completed with exit code 78`` on the
audit job's Independent audit step after 2706.0 s.  No gate file, no audit ref
and no promotion exist for 44711032839; the run is UNADJUDICATED.

This cycle also repairs the VALIDATION failure found on that snapshot: its
report and state claimed an audit-readiness dossier
(``CYCLE_44711032839_audit_readiness.json``) that was never committed, and the
old cycle test's unconditional skip let the claim pass.  This test re-derives
the orchestration diagnosis from the committed raw snapshot, pins the recorded
validation finding, proves the claim is now backed, and fail-closes on any
unbacked dossier claim in reports/ or state.  No gate verdict is minted here:
the independent auditor owns ``results/audit/product/CYCLE_44723775560_GATE.json``.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
for _p in (str(ROOT), str(ROOT / "product")):
    if _p not in sys.path:
        sys.path.insert(0, str(ROOT))

RUN = "44723775560"
RESUMED = "44711032839"
PREDECESSOR = "44700830021"
SNAPSHOT_SHA = "c03dbab5fb9dfdbbb612ef2d2061fe1507bffc2b"
PREDECESSOR_SHA = "6fc8826545ed333d3a8f5c5816e2e2170b8eb71d"

STATE = ROOT / "state" / "product.json"
RAW = ROOT / "results" / "product" / "orchestration" / (
    f"CYCLE_{RESUMED}_run_jobs_raw.json")
DIAG = ROOT / "results" / "product" / "orchestration" / (
    f"CYCLE_{RESUMED}_resume_diagnosis.json")
VERIF = ROOT / "results" / "product" / "answer_sourcing" / (
    f"CYCLE_{RUN}_verification.json")
DOSSIER = ROOT / "results" / "product" / "audit_readiness" / (
    f"CYCLE_{RUN}_audit_readiness.json")
DOSSIER_RESUMED = ROOT / "results" / "product" / "audit_readiness" / (
    f"CYCLE_{RESUMED}_audit_readiness.json")
REPORT = ROOT / "reports" / "product" / f"CYCLE_{RUN}.md"
GATE = ROOT / "results" / "audit" / "product" / f"CYCLE_{RUN}_GATE.json"
GATE_RESUMED = ROOT / "results" / "audit" / "product" / (
    f"CYCLE_{RESUMED}_GATE.json")
DOSSIER_CLAIM_RE = re.compile(
    r"audit_readiness/CYCLE_([0-9]+)_audit_readiness\.json")

GENERATING = os.environ.get("LEX_DOSSIER_GENERATING") == "1"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True,
                          text=True, check=check)


# --- 1. orchestration diagnosis re-derived from committed bytes ----------

def test_raw_snapshot_observes_the_quantum_expiry():
    snap = _load(RAW)
    assert snap["schema"] == "github-actions-run-jobs-snapshot/1"
    jobs = {j["name"]: j for j in snap["jobs"]}
    assert jobs["team"]["conclusion"] == "success"
    assert jobs["audit"]["conclusion"] == "failure"
    steps = {s["name"]: s for s in jobs["audit"]["steps"]}
    assert steps["Independent audit"]["conclusion"] == "failure"
    assert steps["Enforce audit scope and read gate"]["conclusion"] == "skipped"
    assert steps["Persist audit snapshot"]["conclusion"] == "skipped"
    assert snap["run"]["conclusion"] == "failure"
    assert snap["logs_endpoint_status"] == 403
    # annotations are the observation source, keyed by job id
    messages = [
        a.get("message", "")
        for anns in snap["annotations"].values()
        for a in (anns or [])
    ]
    assert any("LEX_WORK_QUANTUM_EXPIRED seconds=2700" in m
               for m in messages), messages
    assert any("exit code 78" in m for m in messages), messages


def test_resume_diagnosis_re_derives_classification_mechanism_and_delta():
    diag = _load(DIAG)
    assert diag["schema"] == "product-resume-snapshot-diagnosis/1"
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
    assert orch["audit"]["failed_step"] == "Independent audit"
    delta = diag["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["snapshot_head"] == SNAPSHOT_SHA
    assert delta["predecessor_head"] == PREDECESSOR_SHA
    assert delta["changed_files"] == 9
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["accepted"] is False
    # no audit half exists for either run on origin
    for run in (RUN, RESUMED):
        assert not (ROOT / "results" / "audit" / "product"
                    / f"CYCLE_{run}_GATE.json").exists()


# --- 2. validation failure diagnosed AND repaired -------------------------

def test_diagnosis_records_the_unbacked_dossier_claim():
    """The prior snapshot's claim failure is preserved as point-in-time evidence."""
    findings = _load(DIAG)["validation_findings"]
    missing = findings["missing_claimed_dossiers"]
    paths = [row["path"] for row in missing]
    assert f"results/product/audit_readiness/CYCLE_{RESUMED}_audit_readiness.json" in paths, missing
    row = next(r for r in missing if r["run_id"] == RESUMED)
    assert "reports/product/CYCLE_44711032839.md" in row["claimed_by"]
    assert "state/product.json" in row["claimed_by"]
    # nothing else in the corpus was unbacked at diagnosis time
    assert len(missing) == 1, missing
    assert findings["missing_claimed_cycle_tests"] == []


def test_every_dossier_claim_in_reports_and_state_is_backed():
    """Fail closed on the defect class this cycle repaired.

    While the enclosing audit_readiness run is generating THIS cycle's
    dossier, that one path is allowed to be pending; every other claim --
    including the backfilled 44711032839 dossier -- must already exist.
    """
    sources = [STATE, *sorted((ROOT / "reports" / "product").glob("CYCLE_*.md"))]
    claimed: dict[str, set[str]] = {}
    for src in sources:
        if not src.is_file():
            continue
        for rid in DOSSIER_CLAIM_RE.findall(
                src.read_text(encoding="utf-8", errors="replace")):
            claimed.setdefault(rid, set()).add(str(src.relative_to(ROOT)))
    assert claimed, "no dossier claims found; the scanner is broken"
    missing = []
    for rid, where in sorted(claimed.items()):
        path = (ROOT / "results" / "product" / "audit_readiness"
                / f"CYCLE_{rid}_audit_readiness.json")
        if path.is_file():
            continue
        if GENERATING and rid == RUN:
            continue  # written at the end of the enclosing run
        missing.append({"run_id": rid, "claimed_by": sorted(where)})
    assert not missing, f"unbacked dossier claims: {missing}"
    # the repaired claim specifically is backed now
    assert DOSSIER_RESUMED.is_file()


def test_backfilled_dossier_passes():
    art = _load(DOSSIER_RESUMED)
    assert art["schema"] == "product-audit-readiness/1"
    assert art["run_id"] == RESUMED
    assert art["resumed_run_id"] == PREDECESSOR
    assert art["overall_status"] == "PASS", art["failed_checks"]
    assert art["failed_checks"] == []
    assert art["skipped_checks"] == []
    statuses = {c["id"]: c["status"] for c in art["checks"]}
    for mandatory in ("runtime_preflight", "state_contract", "posture",
                      "resumed_diagnosis", "claim_artifacts", "cycle_test",
                      "progressive_smoke", "mvp_core_tests",
                      "audit_namespace"):
        assert statuses[mandatory] == "PASS", (mandatory, statuses)


# --- 3. this cycle's dossier (fail closed outside its own generation) -----

def test_this_cycle_dossier_passes():
    if not DOSSIER.is_file():
        if GENERATING:
            pytest.skip("dossier written at the end of the enclosing "
                        "audit_readiness run")
        raise AssertionError(
            f"unbacked dossier claim: {DOSSIER.relative_to(ROOT)} is named "
            f"by the report/state but is absent from the tree")
    art = _load(DOSSIER)
    assert art["schema"] == "product-audit-readiness/1"
    assert art["run_id"] == RUN
    assert art["resumed_run_id"] == RESUMED
    assert art["direction_version"] == 68
    assert art["overall_status"] == "PASS", art["failed_checks"]
    assert art["failed_checks"] == []
    assert art["skipped_checks"] == []
    statuses = {c["id"]: c["status"] for c in art["checks"]}
    for mandatory in ("runtime_preflight", "state_contract", "posture",
                      "resumed_diagnosis", "claim_artifacts", "cycle_test",
                      "progressive_smoke", "mvp_core_tests",
                      "audit_namespace"):
        assert statuses[mandatory] == "PASS", (mandatory, statuses)
    assert art["posture"]["gate_minted"] is False
    assert art["posture"]["run_label"] == "UNADJUDICATED"
    c1 = next(c for c in art["claims"] if c["id"] == "C1")
    assert "work quantum" in c1["claim"] and "2700" in c1["claim"]


# --- 4. inherited deliverable preserved, report of record honest ----------

def test_inherited_answer_sourcing_deliverable_still_passes():
    art = _load(VERIF)
    assert art["run_id"] == RUN
    assert (art.get("resumed_snapshot_run_id")
            or art.get("resumed_run_id")) == RESUMED
    assert art.get("verdict") == "PASS", art.get("verdict")
    checks = art.get("checks") or {}
    assert checks, art.keys()
    failed = [name for name, ok in checks.items() if ok is not True]
    assert not failed, failed
    assert art.get("validate_bundle_errors") == []


def test_report_of_record_names_the_observed_mechanism_and_both_dossiers():
    text = REPORT.read_text(encoding="utf-8")
    assert RUN in text and RESUMED in text
    assert "LEX_WORK_QUANTUM_EXPIRED" in text
    assert "2706" in text
    assert "exit 78" in text or "exit code 78" in text
    assert "UNADJUDICATED" in text
    assert f"CYCLE_{RESUMED}_audit_readiness.json" in text
    assert f"CYCLE_{RUN}_audit_readiness.json" in text
    # the report must not claim a verdict of its own for this run
    assert "gate=REVISE" not in text and "gate=BLOCKED" not in text
    assert "human_gate_ready: true" not in text.lower()


def test_state_posture_and_pointer_are_fail_closed():
    st = _load(STATE)
    assert st["lane"] == "product"
    assert st["direction_version"] == 68
    assert st["continue_recommended"] is True
    assert st["human_gate_ready"] is False
    assert st["machine_gate_ready"] is False
    assert st["packet_admitted"] is False
    assert st["ready_for_owner_session"] is False
    assert st["owner_decision_required"] is False
    assert st["accepted_run_id"] == "CYCLE_40284658455"
    from product.state_contract import accepted_pointer_evidence
    pointer = accepted_pointer_evidence(st, ROOT)
    assert pointer["problems"] == [], pointer
    block = st.get(f"cycle_{RUN}_operational_resume")
    assert block, "state must carry this cycle's operational-resume block"
    assert block["resumed_snapshot"]["run_id"] == RESUMED


def test_producer_never_wrote_the_auditor_namespace():
    assert not GATE.exists() and not GATE_RESUMED.exists()
    pending = subprocess.run(
        ["git", "status", "--porcelain", "-uall"], cwd=str(ROOT),
        capture_output=True, text=True, check=False,
    ).stdout.splitlines()
    offenders = [ln[3:] for ln in pending
                 if ln[3:].startswith(("results/audit/", "reports/audit/"))]
    assert not offenders, offenders
