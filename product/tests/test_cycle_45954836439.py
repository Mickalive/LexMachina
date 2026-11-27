"""Cycle 45954836439 — re-derive the operational-resume diagnosis and the
audit-ready package for producer snapshot 45947662468.

Every number in reports/product/CYCLE_45954836439.md must be reproducible from
the committed tree with the product's own instruments.  This file is the next
auditor's entry point; it mints no gate and cites no unadjudicated work as
accepted.

Deliberately does NOT call ``audit_readiness.run()``: that function runs this
file as its ``cycle_test`` check, so calling it from here would recurse.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import product.audit_readiness as ar  # noqa: E402

RESUMED = "45947662468"
RESUMING = "45954836439"
RAW = ROOT / "results/product/orchestration" / f"CYCLE_{RESUMED}_run_jobs_raw.json"
DIAG = ROOT / "results/product/orchestration" / f"CYCLE_{RESUMED}_resume_diagnosis.json"
REPORT = ROOT / "reports/product" / f"CYCLE_{RESUMING}.md"
STATE = json.loads((ROOT / "state/product.json").read_text(encoding="utf-8"))


def _raw() -> dict:
    return json.loads(RAW.read_text(encoding="utf-8"))


def _diag() -> dict:
    return json.loads(DIAG.read_text(encoding="utf-8"))


def _job(doc: dict, name: str) -> dict:
    return next(j for j in doc["jobs"] if j["name"] == name)


def _step(doc: dict, job: str, name: str) -> dict:
    for s in _job(doc, job)["steps"]:
        if s["name"] == name:
            return s
    raise AssertionError(f"step {job}/{name} absent")


# --------------------------------------------------------------------------
# 1. the raw run/jobs snapshot re-derives the diagnosis
# --------------------------------------------------------------------------
def test_raw_snapshot_shows_team_success_and_audit_quantum_signature():
    raw = _raw()
    assert raw["schema"] == "github-actions-run-jobs-snapshot/1"
    assert raw["logs_endpoint_status"] == 403
    assert raw["annotations_endpoint_status"] == 404
    assert _job(raw, "team")["conclusion"] == "success"
    assert _job(raw, "audit")["conclusion"] == "failure"
    assert _job(raw, "integrate")["conclusion"] == "skipped"
    lane = _step(raw, "team", "Run lane cycle")
    assert lane["conclusion"] == "success" and lane["seconds"] == 1173.0
    assert _step(raw, "team", "Validate active MVP producer state")["conclusion"] == "success"
    assert _step(raw, "team", "Enforce lane write scope")["conclusion"] == "success"
    ind = _step(raw, "audit", "Independent audit")
    assert ind["conclusion"] == "failure"
    # the 2700 s quantum poll fires at elapsed >= 2700 on a 15 s cadence, so a
    # quantum kill lands in [2700, 2715]; 2705.0 s is the observed value.
    assert 2700.0 <= ind["seconds"] <= 2715.0
    assert ind["seconds"] == 2705.0
    assert _step(raw, "audit", "Enforce audit scope and read gate")["conclusion"] == "skipped"
    assert _step(raw, "audit", "Persist audit snapshot")["conclusion"] == "skipped"


def test_diagnosis_matches_the_raw_snapshot_field_by_field():
    raw, diag = _raw(), _diag()
    orch = diag["orchestration"]
    assert diag["run_id"] == RESUMED
    assert diag["predecessor_run_id"] == "40284658455"
    assert diag["resuming_run_id"] == RESUMING
    assert diag["direction_version"] == 68
    assert orch["classification"] == "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    assert orch["failed_job"] == "audit" and orch["failed_step"] == "Independent audit"
    assert orch["raw_snapshot"].endswith(f"CYCLE_{RESUMED}_run_jobs_raw.json")
    mech = orch["mechanism"]
    assert mech["status"] == "OBSERVED_STEP_TIMING_QUANTUM_SIGNATURE"
    assert mech["evidence_basis"] == "step_timing"
    assert mech["annotation_observed"] is False
    assert mech["logs_endpoint_status"] == 403
    assert mech["annotations_endpoint_status"] == 404
    assert mech["quantum_expired"] is True
    assert mech["quantum_seconds"] == 2700
    assert mech["exit_code"] == 78
    assert mech["independent_audit_step_seconds"] == 2705.0
    assert mech["in_kill_window"] is True
    assert orch["audit"]["gate_file_written"] is False
    assert orch["audit"]["enforce_gate_step"] == "skipped"
    assert orch["audit"]["persist_step"] == "skipped"
    assert orch["audit"]["audit_ref_exists"] is False
    assert orch["integrate"]["conclusion"] == "skipped"
    assert "resume_from_run_id=45947662468" in orch["resilience"]["dispatched"]
    # never assert a log-level cause the evidence cannot support
    assert "no log-level cause is asserted" in mech["log_level_cause"] or \
        mech["log_level_cause"] == "UNAVAILABLE_HTTP_403"
    assert "no job-log text was read" in mech["not_claimed"]
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["accepted"] is False


def test_durable_delta_is_the_inherited_19_file_post_hydration_delta():
    diag = _diag()
    delta = diag["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["changed_files"] == 19
    assert delta["predecessor_head"].startswith("7be4480e")
    assert delta["snapshot_head"].startswith("21e2bfa2")
    sample = delta["changed_paths_sample"]
    assert len(sample) == 19
    for needle in ("product/query/counter_evidence_span.py",
                   "results/product/post_hydration_recheck/CYCLE_45947662468.json",
                   "product/tests/test_post_hydration_content_recheck.py"):
        assert any(needle in s for s in sample), needle
    # the delta really is a diff between those two commits
    got = subprocess.run(
        ["git", "diff", "--name-only", delta["predecessor_head"],
         delta["snapshot_head"]],
        cwd=str(ROOT), capture_output=True, text=True, check=True,
    ).stdout.split()
    assert sorted(got) == sorted(sample)


# --------------------------------------------------------------------------
# 2. the audit-readiness instrument wires the new failure mode correctly
# --------------------------------------------------------------------------
def test_profile_resolves_for_both_the_resumed_and_the_resuming_run():
    for run_id in (RESUMED, RESUMING):
        prof = ar.select_profile(run_id)
        assert prof["resumed_run_id"] == RESUMED
        assert prof["mechanism_kind"] == "observed_step_timing"
        assert prof["classification"] == (
            "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE")
        assert prof["failed_job"] == "audit"
        assert prof["quantum_seconds"] == 2700
        assert prof["exit_code"] == 78
        assert prof["independent_audit_step_seconds"] == 2705.0
        assert prof["changed_files"] == 19
        assert Path(prof["raw"]).is_file()
        assert Path(prof["resume_diag"]).is_file()
        assert (ROOT / prof["cycle_test"]).is_file()
    # unknown ids still fail closed instead of inheriting another run's claims
    try:
        ar.select_profile("00000000000")
    except SystemExit:
        pass
    else:
        raise AssertionError("unknown run id must fail closed")


def test_resumed_diagnosis_check_passes_on_the_committed_bytes():
    ar.PROFILE.clear()
    ar.PROFILE.update(ar.select_profile(RESUMED))
    check = ar.check_resumed_diagnosis()
    assert check["status"] == "PASS", check["detail"]
    assert check["detail"]["mechanism_kind"] == "observed_step_timing"
    assert check["detail"]["problems"] == []
    assert check["detail"]["audit_step_seconds"] == 2705.0
    assert check["detail"]["changed_files"] == 19


def test_claim_artifacts_check_passes_on_the_committed_bytes():
    ar.PROFILE.clear()
    ar.PROFILE.update(ar.select_profile(RESUMED))
    check = ar.check_claim_artifacts()
    assert check["status"] == "PASS", check["detail"]
    assert check["detail"]["missing"] == []
    assert check["detail"]["problems"] == []
    assert check["detail"]["content_family"]["n_bundles"] == 54
    assert check["detail"]["content_family"]["n_verified_defective"] == 0


def test_posture_check_stays_fail_closed():
    ar.PROFILE.clear()
    ar.PROFILE.update(ar.select_profile(RESUMED))
    check = ar.check_posture()
    assert check["status"] == "PASS", check["detail"]
    assert check["detail"]["mismatches"] == {}
    assert check["detail"]["accepted_pointer"]["problems"] == []


# --------------------------------------------------------------------------
# 3. audit namespace and posture are honest
# --------------------------------------------------------------------------
def test_no_producer_minted_gate_or_audit_report_exists():
    for run_id in (RESUMED, RESUMING):
        assert not (ROOT / f"results/audit/product/CYCLE_{run_id}_GATE.json").exists()
        assert not (ROOT / f"reports/audit/product/CYCLE_{run_id}.md").exists()
    check = ar.check_audit_namespace(RESUMED)
    assert check["status"] == "PASS", check["detail"]
    assert check["detail"]["pending_audit_paths"] == []


def test_state_block_and_posture_flags_are_fail_closed():
    assert STATE["direction_version"] == 68
    assert STATE["cycle_status"] == "COMPLETE"
    assert STATE["continue_recommended"] is True
    for flag in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                 "ready_for_owner_session"):
        assert STATE[flag] is False, flag
    block = STATE["cycle_45947662468_operational_resume"]
    assert block["direction_version"] == 68
    assert block["continue_recommended"] is True
    assert "OBSERVED_STEP_TIMING_QUANTUM_SIGNATURE" in (
        block["orchestration_failure_of_record"]["mechanism"])
    assert block["validation_failure_of_record"].startswith("NONE")
    assert block["validation_finding"]["status"] == "NOT_REPRODUCIBLE_AS_STATED"
    assert block["audit_ready_package"]["quantum_seconds"] == 2700
    budget = block["audit_ready_package"]["measured_budget_s"]
    assert budget["total_estimate"] < block["audit_ready_package"]["quantum_seconds"]
    # the producer's own block is preserved, not overwritten
    assert STATE["cycle_45947662468"]["status"] == "PRODUCER_DELIVERED_UNADJUDICATED"


def test_every_state_evidence_ref_resolves():
    """Factory-wide requirement 38: nested evidence_refs must resolve."""
    missing = []
    for ref in STATE["evidence_refs"]:
        # forms seen: "path", "path (N tests)", "path ::node", "a -> b",
        # "path --raw artifact", "path (comment)"
        body = re.sub(r"\s*\(.*$", "", ref).strip()
        tokens: list[str] = []
        for part in body.split(" -> "):
            part = part.strip()
            if " --raw " in part:
                tokens.extend(t.strip() for t in part.split(" --raw ") if t.strip())
            else:
                tokens.append(part.split("::")[0].strip())
        for token in tokens:
            if not token or "/" not in token:
                continue
            if not (ROOT / token).exists():
                missing.append((ref, token))
    assert missing == [], missing


# --------------------------------------------------------------------------
# 4. the report's published numbers re-derive
# --------------------------------------------------------------------------
def test_report_publishes_the_observed_timings_and_the_supersession():
    text = REPORT.read_text(encoding="utf-8")
    assert f"CYCLE_{RESUMED}" in text or RESUMED in text
    for needle in ("2705.0", "2700", "HTTP 403", "HTTP 404",
                   "213 passed", "170 passed", "23/23", "234 passed",
                   "222 passed", "not re-derivable", "UNENUMERATED",
                   "observed_step_timing", "21e2bfa2", "59.7 s"):
        assert needle in text, needle
    # the report must disclose the supersession rather than repeat the figure
    # as its own measurement
    assert "supersede" in text.lower()
    assert "UNENUMERATED" in text
    assert "no gate was written by anyone" in text


def test_inherited_recheck_artifact_still_carries_all_true_success_flags():
    art = json.loads((ROOT / "results/product/post_hydration_recheck"
                      / f"CYCLE_{RESUMED}.json").read_text(encoding="utf-8"))
    assert art["success"] and all(art["success"].values()), art["success"]
    rep = art["reproduction"]
    assert rep["defective_row"]["after"]["counter_evidence_verified"] is False
    assert rep["sound_row"]["after"]["counter_evidence_verified"] is True
    assert rep["geometry_unchanged"] is True
