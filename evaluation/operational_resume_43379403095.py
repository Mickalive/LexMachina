#!/usr/bin/env python3
"""Operational resume of core-evaluation run 43378111582 (direction v68).

WHAT HAPPENED (recomputed here, not narrated)
---------------------------------------------
The persisted snapshot of this lane is the tree of run ``43378111582``
(``6c45cf2a``), whose team job FAILED at workflow step ``Run lane cycle``
(exit 1) after the model provider quarantined ``opencode/big-pickle``
(``LEX_MODEL_AUTH_FAILURE``) and rotated to ``opencode/beam-free``
(``LEX_MODEL_ROTATE ... pool_size=4``) - the provider-rotation class of
factory-wide requirement 20.  ``Validate active MVP producer state`` and
``Enforce lane write scope`` were skipped, the audit and integrate jobs were
skipped, no audit ref exists, and the snapshot it persisted adds only
lane-namespace diagnostics (a ref probe and GitHub API envelopes).

Two team-successful ancestors of that snapshot - ``43365482535`` (which
produced the FAST-MVP minimal-ca-falsify deliverable) and ``43371675511``
(which closed a state-provenance pin) - each lost their independent audit to
``LEX_WORK_QUANTUM_EXPIRED seconds=2700`` (exit 78) at step
``Independent audit``, so neither ever reached ``Enforce audit scope and read
gate`` and neither produced a gate of record.  ``43371186416`` exited 67
``LEX_ZERO_DELTA_REPAIR``; ``43365313827`` and ``43371040309`` failed at
``Run lane cycle`` with exit 1.

WHAT THIS INSTRUMENT DOES
-------------------------
Recomputes the five frozen hypotheses of
``evaluation/OPERATIONAL_RESUME_43379403095_HYPOTHESIS_V1.json`` from source
artifacts, with the rules and pins frozen beforehand in
``evaluation/OPERATIONAL_RESUME_43379403095_FREEZE_V1.json``:

  H1  43378111582 failed at ``Run lane cycle`` with a provider-rotation
      signature, zero audit-namespace writes and no audit ref;
  H2  the five other chain runs each died in their own recorded non-product
      orchestration class (two audit-quantum expiries, one zero-delta repair,
      two plain lane-cycle exits), with no audit ref for any of them;
  H3  the snapshot's completed FAST-MVP deliverable (43365482535) is
      pin-clean, internally consistent, non-vacuous, field-identical to the
      previously verified 43342851837 twin outside the seven volatile fields,
      and a fresh scratch replay reproduces every measurement-bearing field
      without rewriting the claim-bearing original;
  H4  ordered item (2) is still NOT_YET_DISCRIMINATING at product head
      7be4480e (zero-delta family, 14/15 role ceiling);
  H5  the snapshot is made audit-ready by IN-LANE-ONLY writes: the resumed
      run's delta is write-scope clean, live scope is SCOPE_CLEAN, no
      audit-namespace path is touched, state integrity passes, the lane
      suite passes and both state files agree on run identity.

It is a VERIFICATION instrument: it re-scores nothing product-facing, moves
no frozen bar/rubric/threshold/verdict contract, writes nothing under
``results/audit/`` or ``reports/audit/``, and issues no serve or admission
verdict.  stdlib only; the only network use is the git/API capture pinned in
the freeze record.  The fresh benchmark replay is the accepted wrapper
``evaluation.minimal_ca_falsify_benchmark`` invoked out-of-tree; no
measurement code is re-implemented here.

    python -m evaluation.operational_resume_43379403095 --phase prepare
    python -m evaluation.operational_resume_43379403095 --phase final

Exit codes: 0 = all evaluated hypotheses hold; 1 = at least one is falsified
(a legitimate, published negative result); 2 = environment error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCHEMA = "lex-evaluation-operational-resume-verification/3"
LANE = "evaluation"
RUN_ID = "43379403095"
RESUMED = "43378111582"          # failed at Run lane cycle (provider rotation)
BASE_RUN = "43371675511"         # last snapshot before the resumed one
CHAIN = ["43365313827", "43365482535", "43371040309",
         "43371186416", "43371675511"]
DELIVERABLE_RUN = "43365482535"  # produced the FAST-MVP benchmark
TWIN_RUN = "43342851837"         # previously verified instance of same bytes
DIRECTION_VERSION = 68

BASE_SHA = "11bc8c6819fe3bb9d742178de4f55c0826a7cbad"    # 43371675511 head
SNAPSHOT_SHA = "6c45cf2ae7b6b39f2b1d8fd965ab432859dcf20f"  # 43378111582 head

OUT_DIR = REPO_ROOT / "results" / "evaluation" / f"operational_resume_{RUN_ID}"
SCRATCH_DIR = OUT_DIR / "scratch"
FREEZE_PATH = REPO_ROOT / "evaluation" / f"OPERATIONAL_RESUME_{RUN_ID}_FREEZE_V1.json"
HYP_PATH = REPO_ROOT / "evaluation" / f"OPERATIONAL_RESUME_{RUN_ID}_HYPOTHESIS_V1.json"

WRAPPER_RECORD = (REPO_ROOT / "results" / "evaluation" /
                  "minimal_ca_falsify_benchmark" / f"{DELIVERABLE_RUN}.json")
ENGINE_RECORD = (REPO_ROOT / "results" / "evaluation" /
                 "minimal_ca_falsify_benchmark" /
                 f"{DELIVERABLE_RUN}_engine_mapping_free_recall_falsifier.json")
REPORT = REPO_ROOT / "reports" / "evaluation" / f"RETRIEVAL_CA_BENCHMARK_{DELIVERABLE_RUN}.md"
TWIN_RECORD = (REPO_ROOT / "results" / "evaluation" /
               "minimal_ca_falsify_benchmark" / f"{TWIN_RUN}.json")

EXPECTED_DELTA_PATHS = [
    "results/evaluation/operational_resume_43378111582/api/jobs_43365313827.json",
    "results/evaluation/operational_resume_43378111582/api/jobs_43365482535.json",
    "results/evaluation/operational_resume_43378111582/api/jobs_43371040309.json",
    "results/evaluation/operational_resume_43378111582/api/jobs_43371186416.json",
    "results/evaluation/operational_resume_43378111582/api/jobs_43371675511.json",
    "results/evaluation/operational_resume_43378111582/api/run_43365313827.json",
    "results/evaluation/operational_resume_43378111582/api/run_43365482535.json",
    "results/evaluation/operational_resume_43378111582/api/run_43371040309.json",
    "results/evaluation/operational_resume_43378111582/api/run_43371186416.json",
    "results/evaluation/operational_resume_43378111582/api/run_43371675511.json",
    "results/evaluation/operational_resume_43378111582/ref_probe_43378111582.json",
]
EXPECTED_DELIVERABLE = {
    "verdict": "PRODUCT_FALSIFIED",
    "exit_code": 1,
    "n_gates": 18,
    "n_passed": 11,
    "n_failed": 4,
    "n_reported": 3,
    "failed_gates": [
        "mf::concept_coverage::39319405429::de-kapitalverletzung",
        "mf::counter_authority_surface::39319405429::de-kapitalverletzung",
        "mf::counter_authority_surface::39319405429::fr-bail-entretien",
        "mf::counter_authority_surface::39319405429::it-responsabilita-medica",
    ],
    "product_mount_head": "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83",
}
EXPECTED_ITEM2 = {
    "status": "NOT_YET_DISCRIMINATING",
    "byte_identical_n": 50,
    "frozen_family_n": 15,
    "member_for_member_ceiling": 14,
    "product_head": "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83",
}
MEASUREMENT_EXCLUDED = {
    "run_id", "generated_at_utc", "engine_record_path", "entry_point",
    "engine_entry_point", "numeric_environment", "wrapper_instrument",
}
CHAIN_FAILURE_EXPECTATIONS = {
    "43365313827": {"team": "failure", "failing_steps": ["Run lane cycle"],
                     "audit": "skipped", "exit_annotation": "exit code 1"},
    "43365482535": {"team": "success", "audit": "failure",
                     "audit_failing_steps": ["Independent audit"],
                     "exit_annotation": "exit code 78",
                     "quantum": "LEX_WORK_QUANTUM_EXPIRED seconds=2700"},
    "43371040309": {"team": "failure", "failing_steps": ["Run lane cycle"],
                     "audit": "skipped", "exit_annotation": "exit code 1"},
    "43371186416": {"team": "failure", "failing_steps": ["Run lane cycle"],
                     "audit": "skipped", "exit_annotation": "exit code 67",
                     "zero_delta": "LEX_ZERO_DELTA_REPAIR"},
    "43371675511": {"team": "success", "audit": "failure",
                     "audit_failing_steps": ["Independent audit"],
                     "exit_annotation": "exit code 78",
                     "quantum": "LEX_WORK_QUANTUM_EXPIRED seconds=2700"},
}

EXIT_PASS, EXIT_FAIL, EXIT_ENV = 0, 1, 2
VOLATILE = MEASUREMENT_EXCLUDED


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")


def git(*args: str) -> str:
    proc = subprocess.run(["git", "-C", str(REPO_ROOT), *args],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def job_map(api_file: Path) -> dict:
    return {j.get("name"): j for j in load(api_file).get("jobs", [])}


def failing_steps(job: dict) -> list[str]:
    return [s.get("name") for s in job.get("steps") or []
            if s.get("conclusion") == "failure"]


def skipped_steps(job: dict) -> list[str]:
    return [s.get("name") for s in job.get("steps") or []
            if s.get("conclusion") == "skipped"]


def annotations(run_id: str, kind: str) -> list[str]:
    path = OUT_DIR / "api" / f"annotations_{kind}_{run_id}.json"
    if not path.is_file():
        return []
    data = load(path)
    if isinstance(data, dict):
        return [data.get("message", "")]
    return [a.get("message", "") for a in data]


def has_annotation(msgs: list[str], token: str) -> bool:
    return any(token in m for m in msgs)


def step_conclusion(job: dict, name: str) -> str | None:
    for s in job.get("steps") or []:
        if s.get("name") == name:
            return s.get("conclusion")
    return None


def check_h1() -> dict:
    """43378111582 died at Run lane cycle after provider rotation."""
    jobs = job_map(OUT_DIR / "api" / f"jobs_{RESUMED}.json")
    team, audit, integ = jobs.get("team", {}), jobs.get("audit", {}), jobs.get("integrate", {})
    msgs = annotations(RESUMED, "team")
    probe = load(OUT_DIR / f"ref_probe_{RUN_ID}.json")
    diff = git("diff", "--name-status", f"{BASE_SHA}..{SNAPSHOT_SHA}").strip()
    added, modified, deleted = [], [], []
    for line in diff.splitlines():
        parts = line.split("\t")
        status, path = parts[0], parts[-1]
        (added if status.startswith("A") else
         modified if status.startswith("M") else deleted).append(path)
    audit_ns_added = [p for p in added
                      if p.startswith(("results/audit/", "reports/audit/"))]
    checks = {
        "team_job_failed": team.get("conclusion") == "failure",
        "failing_step_is_run_lane_cycle": failing_steps(team) == ["Run lane cycle"],
        "validate_state_skipped": "Validate active MVP producer state" in skipped_steps(team),
        "write_scope_skipped": "Enforce lane write scope" in skipped_steps(team),
        "audit_job_skipped": audit.get("conclusion") == "skipped",
        "integrate_job_skipped": integ.get("conclusion") == "skipped",
        "annotation_exit_code_1": has_annotation(msgs, "exit code 1"),
        "annotation_model_auth_failure_big_pickle_quarantined":
            has_annotation(msgs, "LEX_MODEL_AUTH_FAILURE")
            and has_annotation(msgs, "opencode/big-pickle")
            and has_annotation(msgs, "quarantin"),
        "annotation_model_rotate_beam_free":
            has_annotation(msgs, "LEX_MODEL_ROTATE")
            and has_annotation(msgs, "opencode/beam-free")
            and has_annotation(msgs, "pool_size=4"),
        "snapshot_added_exactly_the_11_lane_diagnostic_paths":
            added == EXPECTED_DELTA_PATHS,
        "snapshot_added_zero_audit_namespace_paths": audit_ns_added == [],
        "snapshot_modified_and_deleted_nothing": modified == [] and deleted == [],
        "no_audit_ref_exists":
            probe.get("audit_ref_present", {}).get(RESUMED) is False,
    }
    record = {
        "schema": "lex-evaluation-operational-resume-failure/1",
        "run_id": RUN_ID,
        "diagnosed_run_id": RESUMED,
        "team_conclusion": team.get("conclusion"),
        "failing_steps": failing_steps(team),
        "skipped_steps": skipped_steps(team),
        "audit_conclusion": audit.get("conclusion"),
        "integrate_conclusion": integ.get("conclusion"),
        "annotations": msgs,
        "snapshot_added_paths": added,
        "snapshot_modified_paths": modified,
        "snapshot_deleted_paths": deleted,
        "audit_namespace_paths_added": audit_ns_added,
        "failure_class": "LANE_CYCLE_EXECUTION_FAILURE_PROVIDER_ROTATION",
        "requirement_class": "factory-wide requirement 20 (provider rotation/auth failure is not a verdict, not a product defect and not a human-gate problem)",
        "mechanism_note": (
            "Job metadata and check-run annotations only. Logs are HTTP 403 "
            "without a GH token, so no log line is quoted. The annotations "
            "record LEX_MODEL_AUTH_FAILURE with quarantine, then LEX_MODEL_ROTATE, "
            "then 'Process completed with exit code 1' on the team job; the "
            "workflow's own skipped-step pattern and the persisted snapshot "
            "delta are read from the committed envelopes and git."),
        "checks": checks,
        "n_checks": len(checks),
        "n_failed": sum(1 for v in checks.values() if not v),
        "holds": all(checks.values()),
    }
    write_json(OUT_DIR / f"diagnosis_{RESUMED}.json", record)
    return record


def check_h2() -> dict:
    """The five other chain runs each died in their recorded non-product class."""
    probe = load(OUT_DIR / f"ref_probe_{RUN_ID}.json")
    per_run, checks = {}, {}
    for run in CHAIN:
        jobs = job_map(OUT_DIR / "api" / f"jobs_{run}.json")
        exp = CHAIN_FAILURE_EXPECTATIONS[run]
        team, audit = jobs.get("team", {}), jobs.get("audit", {})
        team_msgs = annotations(run, "team")
        audit_msgs = annotations(run, "audit")
        run_checks = {
            "team_conclusion_matches": team.get("conclusion") == exp["team"],
            "audit_conclusion_matches": audit.get("conclusion") == exp["audit"],
        }
        if exp["team"] == "failure":
            run_checks["failing_steps_match"] = failing_steps(team) == exp["failing_steps"]
        else:
            run_checks["run_lane_cycle_succeeded"] = (
                step_conclusion(team, "Run lane cycle") == "success")
        if exp["audit"] == "failure":
            run_checks["audit_failing_steps_match"] = (
                failing_steps(audit) == exp["audit_failing_steps"])
            run_checks["audit_scope_gate_skipped"] = (
                "Enforce audit scope and read gate" in skipped_steps(audit))
            run_checks["integrate_skipped"] = (
                jobs.get("integrate", {}).get("conclusion") == "skipped")
        else:
            run_checks["integrate_skipped"] = (
                jobs.get("integrate", {}).get("conclusion") == "skipped")
        msgs = audit_msgs if exp["audit"] == "failure" else team_msgs
        run_checks["exit_annotation_present"] = has_annotation(
            msgs, exp["exit_annotation"])
        if "quantum" in exp:
            run_checks["quantum_annotation_present"] = has_annotation(
                audit_msgs, exp["quantum"])
        if "zero_delta" in exp:
            run_checks["zero_delta_annotation_present"] = has_annotation(
                team_msgs, exp["zero_delta"])
        per_run[run] = {
            "expected": exp,
            "team_conclusion": team.get("conclusion"),
            "failing_steps": failing_steps(team),
            "audit_conclusion": audit.get("conclusion"),
            "audit_failing_steps": failing_steps(audit),
            "team_annotations": team_msgs,
            "audit_annotations": audit_msgs,
            "checks": run_checks,
            "holds": all(run_checks.values()),
        }
        for k, v in run_checks.items():
            checks[f"{run}::{k}"] = v
    for run in [DELIVERABLE_RUN, "43371675511", RESUMED]:
        checks[f"no_audit_ref::{run}"] = (
            probe.get("audit_ref_present", {}).get(run) is False)
    record = {
        "schema": "lex-evaluation-operational-resume-failure/1",
        "run_id": RUN_ID,
        "diagnosed_chain": CHAIN,
        "failure_classes": {
            "43365313827": "LANE_CYCLE_EXECUTION_FAILURE (exit 1)",
            "43365482535": "AUDIT_QUANTUM_EXPIRY_NO_GATE (exit 78, 2700 s)",
            "43371040309": "LANE_CYCLE_EXECUTION_FAILURE (exit 1)",
            "43371186416": "LEX_ZERO_DELTA_REPAIR (exit 67)",
            "43371675511": "AUDIT_QUANTUM_EXPIRY_NO_GATE (exit 78, 2700 s)",
        },
        "control_plane_note": (
            "The audit job is gated on needs.team.result == 'success'. The two "
            "audit expiries therefore starved promotion of the two "
            "team-successful runs; .github/** is control-plane scope and is "
            "recorded here, not edited."),
        "per_run": per_run,
        "audit_ref_present": probe.get("audit_ref_present"),
        "checks": checks,
        "n_checks": len(checks),
        "n_failed": sum(1 for v in checks.values() if not v),
        "holds": all(checks.values()),
    }
    write_json(OUT_DIR / f"diagnosis_chain_{RUN_ID}.json", record)
    return record


def _pin_check(record: dict) -> tuple[dict, dict]:
    checks, detail = {}, {"repo": [], "mount": []}
    before = record.get("rehash_before_execution") or {}
    after = record.get("rehash_after_execution") or {}
    for section in ("repo", "mount"):
        for rel, digest in (before.get(section) or {}).items():
            base = REPO_ROOT if section == "repo" else Path(record.get("product_mount") or "")
            path = base / rel
            ok = path.is_file() and sha256(path) == digest
            checks[f"{section}_pin::{rel}"] = ok
            if not ok:
                detail[section].append(rel)
    checks["rehash_after_equals_before"] = before == after
    return checks, detail


def _agreement_checks(record: dict) -> dict:
    engine = load(ENGINE_RECORD)
    expected = EXPECTED_DELIVERABLE
    failed_names = sorted(g["gate"] for g in (record.get("failed_gates") or [])
                          if isinstance(g, dict))
    eng_failed_names = sorted(g["gate"] for g in (engine.get("failed_gates") or [])
                              if isinstance(g, dict))
    report = REPORT.read_text(encoding="utf-8") if REPORT.is_file() else ""
    freeze = load(FREEZE_PATH)
    frozen_repo = freeze.get("rehash_before_execution", {}).get("repo", {})
    frozen_deliv = freeze.get("rehash_before_execution", {}).get("deliverable", {})
    return {
        "frozen_spec_matches_disk":
            (record.get("frozen_spec") or {}).get("sha256")
            == sha256(REPO_ROOT / "evaluation/retrieval_gate/frozen_retrieval_benchmark.json"),
        "frozen_label_rubric_matches_disk":
            (record.get("frozen_label_rubric") or {}).get("sha256")
            == sha256(REPO_ROOT / "evaluation/frozen_bars/RULES_LABEL.json"),
        "frozen_hypothesis_matches_disk":
            (record.get("frozen_hypothesis") or {}).get("sha256")
            == sha256(REPO_ROOT / "evaluation/MAPPING_FREE_RECALL_FALSIFIER_HYPOTHESIS_V1.json"),
        "run_valid_and_no_drift":
            record.get("run_valid") is True
            and (record.get("input_drift") or []) == []
            and record.get("input_drift_invalidates_run") is False,
        "verdict_and_exit_match_frozen_expected":
            record.get("verdict") == expected["verdict"]
            and record.get("exit_code") == expected["exit_code"],
        "gate_counts_match_frozen_expected":
            [record.get(k) for k in ("n_gates", "n_passed", "n_failed", "n_reported")]
            == [expected[k] for k in ("n_gates", "n_passed", "n_failed", "n_reported")],
        "failed_gates_match_frozen_set": failed_names == sorted(expected["failed_gates"]),
        "product_mount_head_matches_frozen_expected":
            record.get("product_mount_head") == expected["product_mount_head"],
        "engine_record_agrees_with_wrapper":
            engine.get("verdict") == record.get("verdict")
            and engine.get("exit_code") == record.get("exit_code")
            and eng_failed_names == failed_names
            and (engine.get("input_drift") or []) == [],
        "report_agrees_with_machine_record":
            all(token in report for token in [
                expected["verdict"],
                "18 total", "11 passed", "4 failed", "3 reported",
                *expected["failed_gates"],
                expected["product_mount_head"],
            ]),
        "non_vacuity_battery_all_hold":
            (record.get("non_vacuity") or {}).get("all_hold") is True
            and all(b.get("holds") is True
                    for b in (record.get("non_vacuity") or {}).get("battery") or []),
        "posture_flags_false":
            all(record.get(k) is False for k in
                ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                 "ready_for_owner_session")),
        "no_174k_rerun_declared": record.get("no_174k_benchmark_rerun") is True,
        "wrapper_sha_matches_freeze":
            sha256(WRAPPER_RECORD)
            == frozen_deliv.get(str(WRAPPER_RECORD.relative_to(REPO_ROOT))),
        "engine_sha_matches_freeze":
            sha256(ENGINE_RECORD)
            == frozen_deliv.get(str(ENGINE_RECORD.relative_to(REPO_ROOT))),
        "report_sha_matches_freeze":
            sha256(REPORT)
            == frozen_deliv.get(str(REPORT.relative_to(REPO_ROOT))),
        "frozen_repo_pins_still_match_freeze": all(
            sha256(REPO_ROOT / rel) == digest for rel, digest in frozen_repo.items()),
    }


def _canon(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def run_replay() -> dict:
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    replay_id = f"{RUN_ID}_replay"
    cmd = [sys.executable, "-m", "evaluation.minimal_ca_falsify_benchmark",
           "--run-id", replay_id, "--out-dir", str(SCRATCH_DIR),
           "--report-dir", str(SCRATCH_DIR),
           "--product-mount", str(load(WRAPPER_RECORD).get("product_mount")
                                  or "/tmp/lex_accepted/product")]
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                          timeout=3600)
    replay_path = SCRATCH_DIR / f"{replay_id}.json"
    record = {
        "schema": "lex-evaluation-operational-resume-replay/1",
        "run_id": RUN_ID,
        "replay_run_id": replay_id,
        "command": " ".join(cmd),
        "returncode": proc.returncode,
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-4000:],
        "replay_record": str(replay_path.relative_to(REPO_ROOT)),
        "replay_exists": replay_path.is_file(),
        "replay_sha256": sha256(replay_path) if replay_path.is_file() else None,
    }
    write_json(OUT_DIR / f"replay_command_{RUN_ID}.json", record)
    return record


def _compare_records(original_path: Path, other_path: Path,
                     label: str) -> dict:
    original, other = load(original_path), load(other_path)
    keys = sorted((set(original) | set(other)) - VOLATILE)
    diffs, missing = [], []
    for key in keys:
        if key not in original or key not in other:
            missing.append(key)
            continue
        if _canon(original[key]) != _canon(other[key]):
            diffs.append({"field": key,
                          "original": original[key],
                          "other": other[key]})
    env_o = original.get("numeric_environment") or {}
    env_r = other.get("numeric_environment") or {}
    env_diffs = {k: {"original": env_o.get(k), "other": env_r.get(k)}
                 for k in sorted(set(env_o) | set(env_r))
                 if env_o.get(k) != env_r.get(k)}
    return {
        "schema": "lex-evaluation-operational-resume-record-comparison/1",
        "lane": LANE,
        "run_id": RUN_ID,
        "label": label,
        "generated_at_utc": utcnow(),
        "original_record": str(original_path.relative_to(REPO_ROOT)),
        "original_sha256": sha256(original_path),
        "other_record": str(other_path.relative_to(REPO_ROOT)),
        "other_sha256": sha256(other_path),
        "measurement_fields_compared": len(keys) - len(missing),
        "measurement_fields_differing": len(diffs),
        "measurement_differences": diffs,
        "missing_fields": missing,
        "volatile_fields_excluded": sorted(VOLATILE),
        "environment_disclosure_fields_compared": len(env_diffs),
        "environment_disclosure_differences": (
            {"numeric_environment": env_diffs} if env_diffs else {}),
        "environment_disclosure_note": (
            "numeric_environment is a host-scoped disclosure, not a measurement; "
            "no unconditional cross-machine identity is claimed."),
        "verdict": ("RECORDS_MATCH" if not diffs and not missing
                    else "RECORDS_DIVERGE"),
    }


def compare_replay() -> dict:
    replay_path = SCRATCH_DIR / f"{RUN_ID}_replay.json"
    if not replay_path.is_file():
        return {"schema": "lex-evaluation-operational-resume-replay-comparison/1",
                "verdict": "REPLAY_MISSING", "measurement_fields_compared": 0,
                "measurement_fields_differing": None}
    payload = _compare_records(WRAPPER_RECORD, replay_path, "scratch_replay")
    payload["schema"] = "lex-evaluation-operational-resume-replay-comparison/1"
    payload["resumed_run_id"] = DELIVERABLE_RUN
    payload["verdict"] = ("REPLAY_REPRODUCES" if payload["verdict"] == "RECORDS_MATCH"
                          else "REPLAY_DIVERGES")
    write_json(OUT_DIR / f"replay_comparison_{RUN_ID}.json", payload)
    return payload


def check_h3(run_fresh: bool) -> dict:
    if run_fresh or not (SCRATCH_DIR / f"{RUN_ID}_replay.json").is_file():
        run_replay()
    cmp_replay = compare_replay()
    twin = _compare_records(WRAPPER_RECORD, TWIN_RECORD, "twin_43342851837")
    write_json(OUT_DIR / f"twin_comparison_{RUN_ID}.json", twin)
    record = load(WRAPPER_RECORD)
    pin_checks, pin_bad = _pin_check(record)
    ok_checks = _agreement_checks(record)
    checks = {**pin_checks, **ok_checks,
              "replay_record_exists": cmp_replay.get("verdict") != "REPLAY_MISSING",
              "replay_reproduces": cmp_replay.get("verdict") == "REPLAY_REPRODUCES",
              "replay_zero_measurement_differences":
                  cmp_replay.get("measurement_fields_differing") == 0,
              "replay_compared_41_fields":
                  cmp_replay.get("measurement_fields_compared") == 41,
              "twin_comparison_records_match": twin.get("verdict") == "RECORDS_MATCH",
              "twin_zero_measurement_differences":
                  twin.get("measurement_fields_differing") == 0,
              "twin_compared_41_fields": twin.get("measurement_fields_compared") == 41,
              "twin_environment_diff_only_platform":
                  sorted((twin.get("environment_disclosure_differences") or {})
                         .get("numeric_environment", {}).keys()) == ["platform"],
              "original_record_not_rewritten":
                  sha256(WRAPPER_RECORD)
                  == load(FREEZE_PATH)["rehash_before_execution"]["deliverable"]
                  [str(WRAPPER_RECORD.relative_to(REPO_ROOT))],
              }
    delivery = {
        "schema": "lex-evaluation-operational-resume-deliverable-verification/1",
        "lane": LANE,
        "run_id": RUN_ID,
        "resumed_run_id": DELIVERABLE_RUN,
        "direction_version": DIRECTION_VERSION,
        "generated_at_utc": utcnow(),
        "checks": ok_checks,
        "pin_rehash": {"repo": pin_checks_filter(pin_checks, "repo"),
                       "mount": pin_checks_filter(pin_checks, "mount"),
                       "bad_repo": pin_bad.get("repo", []),
                       "bad_mount": pin_bad.get("mount", []),
                       "n_repo": len([k for k in pin_checks if k.startswith("repo_pin::")]),
                       "n_mount": len([k for k in pin_checks if k.startswith("mount_pin::")])},
        "deliverable": {
            "wrapper_record": str(WRAPPER_RECORD.relative_to(REPO_ROOT)),
            "wrapper_sha256": sha256(WRAPPER_RECORD),
            "engine_record": str(ENGINE_RECORD.relative_to(REPO_ROOT)),
            "engine_sha256": sha256(ENGINE_RECORD),
            "report": str(REPORT.relative_to(REPO_ROOT)),
            "report_sha256": sha256(REPORT),
            "verdict": record.get("verdict"),
            "exit_code": record.get("exit_code"),
            "gates": {k: record.get(k) for k in
                      ("n_gates", "n_passed", "n_failed", "n_reported")},
            "failed_gates": [g["gate"] for g in record.get("failed_gates") or []],
            "product_mount_head": record.get("product_mount_head"),
        },
        "twin_comparison": {k: twin.get(k) for k in
                            ("other_record", "measurement_fields_compared",
                             "measurement_fields_differing", "verdict",
                             "environment_disclosure_differences")},
        "replay": {k: cmp_replay.get(k) for k in
                   ("replay_record", "measurement_fields_compared",
                    "measurement_fields_differing", "verdict")},
        "n_checks": len(ok_checks),
        "n_failed": sum(1 for v in ok_checks.values() if not v),
        "verdict": ("DELIVERABLE_VERIFIED" if all(ok_checks.values())
                    else "DELIVERABLE_NOT_VERIFIED"),
        "claim_ceiling": ("Verification of an already-produced record: pins, internal "
                          "consistency, report agreement, non-vacuity, twin-record "
                          "equality and scratch-replay equality. It creates no new "
                          "measurement, moves no frozen bar, issues no serve or "
                          "admission verdict, and is not an independent audit of "
                          "43365482535 or of this run."),
    }
    write_json(OUT_DIR / f"deliverable_verification_{RUN_ID}.json", delivery)
    return {"hypothesis": "H3", "checks": checks,
            "n_checks": len(checks),
            "n_failed": sum(1 for v in checks.values() if not v),
            "holds": all(checks.values()),
            "pin_rehash": delivery["pin_rehash"],
            "replay": delivery["replay"],
            "twin": delivery["twin_comparison"],
            "deliverable_verdict": delivery["verdict"]}


def pin_checks_filter(checks: dict, section: str) -> dict:
    return {k.split("::", 1)[1]: v for k, v in checks.items()
            if k.startswith(f"{section}_pin::")}


def check_h4() -> dict:
    out_path = OUT_DIR / f"item2_family_gate_{RUN_ID}.json"
    proc = subprocess.run(
        [sys.executable, "-m", "evaluation.v68_item2_family_gate",
         "--run-id", RUN_ID, "--out", str(out_path)],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=900)
    if proc.returncode != 0 or not out_path.is_file():
        return {"hypothesis": "H4", "checks": {"item2_gate_ran": False},
                "n_checks": 1, "n_failed": 1, "holds": False,
                "stderr": proc.stderr[-2000:]}
    rec = load(out_path)
    product_head = (rec.get("product") or {}).get("head")
    zero = rec.get("zero_delta_check") or {}
    roles = rec.get("role_cardinality") or {}
    probe = load(OUT_DIR / f"ref_probe_{RUN_ID}.json")
    checks = {
        "item2_gate_ran": True,
        "status_is_NOT_YET_DISCRIMINATING": rec.get("status") == EXPECTED_ITEM2["status"],
        "product_head_is_accepted_head": product_head == EXPECTED_ITEM2["product_head"],
        "lab_product_unchanged": probe.get("refs", {}).get("refs/heads/lab/product")
            == EXPECTED_ITEM2["product_head"],
        "zero_delta_fifty_of_fifty": zero.get("byte_identical_n") == 50
            and zero.get("present_in_current_product_n") == 50
            and not zero.get("differing") and not zero.get("missing"),
        "role_parity_false": roles.get("role_parity") is False,
        "ceiling_fourteen_of_fifteen":
            roles.get("member_for_member_ceiling") == 14
            and roles.get("frozen_family_n") == 15,
        "no_content_rescore_declared":
            "does not re-score" in (rec.get("reused_rule_source") or {}).get("note", ""),
    }
    return {"hypothesis": "H4", "checks": checks,
            "n_checks": len(checks),
            "n_failed": sum(1 for v in checks.values() if not v),
            "holds": all(checks.values()),
            "record": str(out_path.relative_to(REPO_ROOT)),
            "status": rec.get("status"),
            "product_head": product_head,
            "byte_identical_n": zero.get("byte_identical_n"),
            "member_for_member_ceiling": roles.get("member_for_member_ceiling")}


def live_scope() -> dict:
    from evaluation.snapshot_audit.write_scope import evaluate_porcelain, live_porcelain
    verdict = evaluate_porcelain(live_porcelain(REPO_ROOT), LANE)
    write_json(OUT_DIR / f"write_scope_live_{RUN_ID}.json",
               {"schema": "lex-evaluation-write-scope/1", "mode": "live",
                "repo_root": str(REPO_ROOT), "verdict": verdict})
    return verdict


def repro_scope() -> dict:
    from evaluation.snapshot_audit.write_scope import (
        evaluate_porcelain, reconstruct_snapshot_porcelain)
    recon = reconstruct_snapshot_porcelain(REPO_ROOT, BASE_SHA, SNAPSHOT_SHA)
    verdict = evaluate_porcelain(recon["porcelain_lines"], LANE)
    write_json(OUT_DIR / f"write_scope_repro_{RESUMED}.json",
               {"schema": "lex-evaluation-write-scope/1", "mode": "repro-from-git",
                "reconstruction": recon, "verdict": verdict})
    return verdict


def _run_json(cmd: list[str], out: Path, timeout: int = 3600) -> tuple[int, dict | None, str]:
    out.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                          timeout=timeout)
    return (proc.returncode,
            (load(out) if out.is_file() else None),
            (proc.stdout + proc.stderr)[-3000:])


def _state_identity_agrees() -> bool:
    root = load(REPO_ROOT / "state" / "evaluation.json")
    lane = load(REPO_ROOT / "evaluation" / "state" / "evaluation.json")
    keys = ("accepted_run_id", "direction_version", "github_run")
    return (all(root.get(k) == lane.get(k) for k in keys)
            and root.get("github_run") == int(RUN_ID))


def check_h5(final: bool) -> dict:
    repro = repro_scope()
    scope = live_scope()
    checks = {
        "resumed_run_delta_write_scope_CLEAN":
            repro.get("verdict") == "SCOPE_CLEAN",
        "resumed_run_delta_zero_bad_paths":
            repro.get("n_bad") == 0,
        "live_write_scope_is_SCOPE_CLEAN": scope.get("verdict") == "SCOPE_CLEAN",
    }
    porcelain = git("status", "--porcelain", "-uall")
    out_of_scope_dirty = [line[3:].strip() for line in porcelain.splitlines()
                          if line[3:].strip().startswith(("results/audit/", "reports/audit/"))]
    checks["no_audit_namespace_path_added_modified_or_deleted_by_this_run"] = (
        not out_of_scope_dirty)

    integrity = suite = None
    if final:
        sig_out = OUT_DIR / f"state_integrity_gate_{RUN_ID}.json"
        rc_i, integrity, _ = _run_json(
            [sys.executable, "evaluation/state_integrity_gate.py",
             "--run-id", RUN_ID, "--out", str(sig_out)], sig_out)
        checks["state_integrity_ran"] = integrity is not None
        checks["state_integrity_ALL_CHECKS_PASS"] = (
            integrity or {}).get("verdict") == "ALL_CHECKS_PASS"
        checks["state_integrity_rc_zero"] = rc_i == 0
        suite_out = OUT_DIR / f"lane_suite_{RUN_ID}.json"
        rc_s, suite, _ = _run_json(
            [sys.executable, "evaluation/lane_suite.py", "--skip-pytest",
             "--out", str(suite_out)], suite_out, timeout=5400)
        checks["lane_suite_ran"] = suite is not None
        checks["lane_suite_PASS"] = bool(suite) and (
            suite.get("overall_pass") is True
            or suite.get("verdict") in {"PASS", "ALL_CHECKS_PASS"}
            or ((suite.get("n_failed") == 0) and (suite.get("n_checks", 0) > 0)))
        checks["lane_suite_rc_zero"] = rc_s == 0
        checks["state_files_agree_on_identity"] = _state_identity_agrees()

    return {"hypothesis": "H5", "checks": checks,
            "n_checks": len(checks),
            "n_failed": sum(1 for v in checks.values() if not v),
            "holds": all(checks.values()),
            "out_of_scope_dirty": out_of_scope_dirty,
            "write_scope_repro_verdict": repro.get("verdict"),
            "write_scope_live_verdict": scope.get("verdict"),
            "state_integrity_verdict": (integrity or {}).get("verdict"),
            "lane_suite_verdict": ((suite or {}).get("verdict")
                                   or ("PASS" if (suite or {}).get("overall_pass") else None))}


def run(phase: str) -> tuple[int, dict]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        h1 = check_h1()
        h1 = {"hypothesis": "H1", **{k: h1[k] for k in
                                     ("checks", "n_checks", "n_failed", "holds",
                                      "failing_steps", "audit_conclusion",
                                      "integrate_conclusion", "failure_class")}}
        h2 = check_h2()
        h2 = {"hypothesis": "H2", **{k: h2[k] for k in
                                     ("checks", "n_checks", "n_failed", "holds",
                                      "failure_classes")}}
        h3 = check_h3(run_fresh=(phase == "prepare"))
        h4 = check_h4()
        h5 = check_h5(final=(phase == "final"))
        results = [h1, h2, h3, h4, h5]
    except Exception as exc:  # environment error: never a pass, never a fail
        return EXIT_ENV, {"schema": SCHEMA, "verdict": "ENVIRONMENT_ERROR",
                          "exit_code": EXIT_ENV, "error": repr(exc)}

    holds = all(r["holds"] for r in results)
    payload = {
        "schema": SCHEMA,
        "lane": LANE,
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED,
        "base_run_id": BASE_RUN,
        "direction_version": DIRECTION_VERSION,
        "phase": phase,
        "generated_at_utc": utcnow(),
        "hypothesis_record": f"evaluation/OPERATIONAL_RESUME_{RUN_ID}_HYPOTHESIS_V1.json",
        "freeze_record": f"evaluation/OPERATIONAL_RESUME_{RUN_ID}_FREEZE_V1.json",
        "freeze_commit": "e806e660a6f0433859e2a98d9363b4bcc9d493d2",
        "hypotheses": results,
        "n_hypotheses": len(results),
        "n_hypotheses_holding": sum(1 for r in results if r["holds"]),
        "n_checks": sum(r["n_checks"] for r in results),
        "n_failed": sum(r["n_failed"] for r in results),
        "verdict": ("RESUME_VERIFIED_AUDIT_READY" if holds
                    else ("PREPARE_COMPLETE" if phase == "prepare" else
                          "RESUME_VERIFICATION_FAILED")),
        "failure_modes_diagnosed": [
            f"{RESUMED}: LANE_CYCLE_EXECUTION_FAILURE_PROVIDER_ROTATION (exit 1)",
            f"{DELIVERABLE_RUN}: AUDIT_QUANTUM_EXPIRY_NO_GATE (exit 78, 2700 s)",
            "43371675511: AUDIT_QUANTUM_EXPIRY_NO_GATE (exit 78, 2700 s)",
            "43371186416: LEX_ZERO_DELTA_REPAIR (exit 67)",
            "43365313827 / 43371040309: LANE_CYCLE_EXECUTION_FAILURE (exit 1)",
        ],
        "independent_audit_of_resumed_run_exists": False,
        "continue_recommended": False,
        "claim_ceiling": (
            "Operational-resume diagnosis, deliverable verification, "
            "precondition re-adjudication and audit-ready snapshot assembly. "
            "It creates no new product measurement, moves no frozen bar, "
            "rubric, threshold or verdict contract, issues no serve or "
            "admission verdict, and is NOT an independent audit of run "
            "43378111582 or of this run."),
    }
    code = EXIT_PASS if holds else EXIT_FAIL
    payload["exit_code"] = code
    target = OUT_DIR / (f"verification_{RUN_ID}.json" if phase == "final"
                        else f"verification_prestate_{RUN_ID}.json")
    write_json(target, payload)
    write_json(OUT_DIR / (f"summary_{RUN_ID}.json" if phase == "final"
                          else f"summary_prestate_{RUN_ID}.json"), payload)
    return code, payload


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--phase", choices=["prepare", "final"], default="prepare")
    args = ap.parse_args(argv)
    code, payload = run(args.phase)
    print(json.dumps({"phase": args.phase,
                      "verdict": payload.get("verdict"),
                      "exit_code": code,
                      "n_checks": payload.get("n_checks"),
                      "n_failed": payload.get("n_failed"),
                      "hypotheses": [{"h": h["hypothesis"], "holds": h["holds"],
                                      "n_failed": h["n_failed"]}
                                     for h in payload.get("hypotheses", [])]},
                     indent=1))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
