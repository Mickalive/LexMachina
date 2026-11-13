#!/usr/bin/env python3
"""Operational resume of core-evaluation run 43357838904 (direction v68).

WHAT HAPPENED (recomputed here, not narrated)
---------------------------------------------
The persisted snapshot of this lane is the tree of run 43349645400
(``fe99ef6a``), an operational resume of ``43344048907``.  Run 43349645400
completed its producer cycle (``Run lane cycle`` success, ``Validate active
MVP producer state`` success) and then FAILED at workflow step 9
``Enforce lane write scope`` (exit 3) because two of the paths its snapshot
added sit in the independent auditor's namespace.  Its audit and integrate
jobs were SKIPPED.  The next resume, 43357838904, FAILED earlier still, at
step 6 ``Run lane cycle``, and persisted no delta at all: its team ref is
byte-for-byte the 43349645400 head.  So two consecutive resumes issued no
audit verdict, and the accumulated snapshot is handed to *this* run.

WHAT THIS INSTRUMENT DOES
-------------------------
Recomputes the five frozen hypotheses of
``evaluation/OPERATIONAL_RESUME_43359487892_HYPOTHESIS_V1.json`` from source
artifacts, with the rules and pins frozen beforehand in
``evaluation/OPERATIONAL_RESUME_43359487892_FREEZE_V1.json``:

  H1  43357838904 failed at ``Run lane cycle`` with zero delta and no audit;
  H2  43349645400 failed at ``Enforce lane write scope`` with exactly its two
      producer-authored audit-namespace paths, and no independent audit of
      any of the four runs exists;
  H3  the accumulated FAST-MVP deliverable is pin-clean and a fresh scratch
      replay reproduces every measurement-bearing field;
  H4  ordered item (2) is still NOT_YET_DISCRIMINATING at the accepted
      product head (zero-delta family + 14/15 role ceiling);
  H5  the snapshot is made audit-ready by IN-LANE-ONLY writes: inherited
      producer pseudo-audit files are copied byte-identically with originals
      retained, live scope is SCOPE_CLEAN, both state files agree, state
      integrity passes and the lane suite passes.

It is a VERIFICATION instrument: it re-scores nothing product-facing, moves
no frozen bar/rubric/threshold/verdict contract, writes nothing under
``results/audit/`` or ``reports/audit/``, and issues no serve or admission
verdict.  stdlib only; the only network use is the git ref probe captured at
the start of the run and pinned in the freeze record.  The fresh benchmark
replay is the accepted wrapper ``evaluation.minimal_ca_falsify_benchmark``
invoked out-of-tree; no measurement code is re-implemented here.

    python -m evaluation.operational_resume_43359487892 --phase prepare
    python -m evaluation.operational_resume_43359487892 --phase final

Exit codes: 0 = all evaluated hypotheses hold; 1 = at least one is falsified
(a legitimate, published negative result); 2 = environment error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCHEMA = "lex-evaluation-operational-resume-verification/2"
LANE = "evaluation"
RUN_ID = "43359487892"
RESUMED = "43357838904"          # failed at Run lane cycle, zero delta
BASE_RUN = "43349645400"         # failed at Enforce lane write scope
BASE2_RUN = "43344048907"        # failed at Run lane cycle, produced the deliverable
ORIGINAL_RUN = "43342851837"     # produced the FAST-MVP benchmark of record
DIRECTION_VERSION = 68

BASE_SHA = "f97a5656a1830c0d6834de5c98f469bce8046a14"   # 43344048907 head
SNAPSHOT_SHA = "fe99ef6ae2729f0b4fc3a784216e1d90dabc0259"  # 43349645400 == 43357838904 head

OUT_DIR = REPO_ROOT / "results" / "evaluation" / f"operational_resume_{RUN_ID}"
RECOVERY_DIR = REPO_ROOT / "results" / "evaluation" / f"audit_namespace_recovery_{RUN_ID}"
SCRATCH_DIR = OUT_DIR / "scratch"
WRAPPER_RECORD = REPO_ROOT / "results" / "evaluation" / "minimal_ca_falsify_benchmark" / f"{ORIGINAL_RUN}.json"
ENGINE_RECORD = REPO_ROOT / "results" / "evaluation" / "minimal_ca_falsify_benchmark" / f"{ORIGINAL_RUN}_engine_mapping_free_recall_falsifier.json"
REPORT = REPO_ROOT / "reports" / "evaluation" / f"RETRIEVAL_CA_BENCHMARK_{ORIGINAL_RUN}.md"

INHERITED = [
    "reports/audit/evaluation/CYCLE_43342851837.md",
    "results/audit/evaluation/CYCLE_43342851837_GATE.json",
    "reports/audit/evaluation/CYCLE_43349645400.md",
    "results/audit/evaluation/CYCLE_43349645400_GATE.json",
]

EXPECTED_BAD_PATHS = sorted([
    "reports/audit/evaluation/CYCLE_43349645400.md",
    "results/audit/evaluation/CYCLE_43349645400_GATE.json",
])
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
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def git(*args: str) -> str:
    proc = subprocess.run(["git", "-C", str(REPO_ROOT), *args],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def git_log(path: str) -> dict:
    out = git("log", "-1", "--format=%H%x1f%an%x1f%ae%x1f%s", "--", path).strip()
    commit, author_name, author_email, subject = out.split("\x1f")
    return {"commit": commit, "author_name": author_name,
            "author_email": author_email, "subject": subject}


def job_map(api_file: Path) -> dict:
    jobs = load(api_file).get("jobs", [])
    return {j.get("name"): j for j in jobs}


def failing_steps(job: dict) -> list[str]:
    return [s.get("name") for s in job.get("steps") or []
            if s.get("conclusion") == "failure"]


def check_h1() -> dict:
    """43357838904 died at Run lane cycle, zero delta, no audit."""
    jobs = job_map(OUT_DIR / "api" / f"jobs_{RESUMED}.json")
    team = jobs.get("team", {})
    probe = load(OUT_DIR / f"ref_probe_{RUN_ID}.json")
    refs = probe.get("refs", {})
    team_ref = f"refs/heads/cycle/core/evaluation/{RESUMED}/team"
    base_ref = f"refs/heads/cycle/core/evaluation/{BASE_RUN}/team"
    delta = git("diff", "--name-status", SNAPSHOT_SHA, refs.get(team_ref, "MISSING")).strip()

    checks = {
        "team_job_failed": team.get("conclusion") == "failure",
        "failing_step_is_run_lane_cycle": failing_steps(team) == ["Run lane cycle"],
        "validate_state_skipped": any(
            s.get("name") == "Validate active MVP producer state" and s.get("conclusion") == "skipped"
            for s in team.get("steps") or []),
        "write_scope_skipped": any(
            s.get("name") == "Enforce lane write scope" and s.get("conclusion") == "skipped"
            for s in team.get("steps") or []),
        "audit_job_skipped": jobs.get("audit", {}).get("conclusion") == "skipped",
        "integrate_job_skipped": jobs.get("integrate", {}).get("conclusion") == "skipped",
        "resume_head_equals_base_run_head": refs.get(team_ref) == refs.get(base_ref) == SNAPSHOT_SHA,
        "resume_snapshot_adds_zero_paths": delta == "",
        "no_audit_ref_exists": probe.get("audit_ref_present", {}).get(RESUMED) is False,
    }
    record = {
        "schema": "lex-evaluation-operational-resume-failure/1",
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED,
        "team_conclusion": team.get("conclusion"),
        "failing_steps": failing_steps(team),
        "skipped_steps": [s.get("name") for s in team.get("steps") or []
                          if s.get("conclusion") == "skipped"],
        "audit_conclusion": jobs.get("audit", {}).get("conclusion"),
        "integrate_conclusion": jobs.get("integrate", {}).get("conclusion"),
        "snapshot_refs": {team_ref: refs.get(team_ref), base_ref: refs.get(base_ref)},
        "delta_against_base_run": delta,
        "failure_class": "LANE_CYCLE_EXECUTION_FAILURE_ZERO_DELTA",
        "mechanism_note": (
            "Job metadata only. Logs are HTTP 403 without a GH token. The wrapper "
            ".github/scripts/run-ox-with-retry.sh can end the agent step non-zero when "
            "the provider fails every retry; the persisted snapshot proves the run "
            "wrote no delta. No mechanism, log line or provider error is quoted."),
        "checks": checks,
        "n_checks": len(checks),
        "n_failed": sum(1 for v in checks.values() if not v),
        "holds": all(checks.values()),
    }
    write_json(OUT_DIR / f"diagnosis_{RESUMED}.json", record)
    return record


def check_h2() -> dict:
    """43349645400 died at write scope; exactly two producer pseudo-audit paths."""
    from evaluation.snapshot_audit.write_scope import (
        evaluate_porcelain, reconstruct_snapshot_porcelain)

    recon = reconstruct_snapshot_porcelain(REPO_ROOT, BASE_SHA, SNAPSHOT_SHA)
    verdict = evaluate_porcelain(recon["porcelain_lines"], LANE)
    write_json(OUT_DIR / f"write_scope_repro_{BASE_RUN}.json",
               {"schema": "lex-evaluation-write-scope/1", "mode": "repro-from-git",
                "reconstruction": recon, "verdict": verdict})

    jobs = job_map(OUT_DIR / "api" / f"jobs_{BASE_RUN}.json")
    team = jobs.get("team", {})
    probe = load(OUT_DIR / f"ref_probe_{RUN_ID}.json")
    provenance = {}
    for rel in INHERITED:
        p = REPO_ROOT / rel
        rec = git_log(rel)
        rec["exists"] = p.is_file()
        rec["sha256"] = sha256(p) if p.is_file() else None
        rec["producer_authored"] = rec.get("author_name") == "lex-evaluation-team"
        provenance[rel] = rec

    bad = sorted(verdict.get("bad_paths") or [])
    checks = {
        "repro_verdict_is_scope_violation": verdict.get("verdict") == "SCOPE_VIOLATION",
        "bad_paths_exactly_the_two_new_pseudo_audit_paths": bad == EXPECTED_BAD_PATHS,
        "team_job_failed": team.get("conclusion") == "failure",
        "failing_step_is_enforce_lane_write_scope":
            failing_steps(team) == ["Enforce lane write scope"],
        "run_lane_cycle_succeeded": any(
            s.get("name") == "Run lane cycle" and s.get("conclusion") == "success"
            for s in team.get("steps") or []),
        "audit_job_skipped": jobs.get("audit", {}).get("conclusion") == "skipped",
        "integrate_job_skipped": jobs.get("integrate", {}).get("conclusion") == "skipped",
        "all_four_inherited_files_present": all(v["exists"] for v in provenance.values()),
        "all_four_inherited_files_producer_authored":
            all(v["producer_authored"] for v in provenance.values()),
        "no_audit_ref_for_any_of_the_four_runs":
            all(probe.get("audit_ref_present", {}).get(r) is False
                for r in [ORIGINAL_RUN, BASE2_RUN, BASE_RUN, RESUMED]),
    }
    record = {
        "schema": "lex-evaluation-operational-resume-failure/1",
        "run_id": RUN_ID,
        "diagnosed_run_id": BASE_RUN,
        "team_conclusion": team.get("conclusion"),
        "failing_steps": failing_steps(team),
        "audit_conclusion": jobs.get("audit", {}).get("conclusion"),
        "integrate_conclusion": jobs.get("integrate", {}).get("conclusion"),
        "bad_paths": bad,
        "all_added_paths": recon.get("added_paths"),
        "failure_class": "WRITE_SCOPE_VIOLATION_PRODUCER_AUDIT_NAMESPACE",
        "provenance_of_inherited_files": provenance,
        "audit_ref_present": probe.get("audit_ref_present"),
        "checks": checks,
        "n_checks": len(checks),
        "n_failed": sum(1 for v in checks.values() if not v),
        "holds": all(checks.values()),
    }
    write_json(OUT_DIR / f"diagnosis_{BASE_RUN}.json", record)
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


def compare_replay() -> dict:
    replay_id = f"{RUN_ID}_replay"
    replay_path = SCRATCH_DIR / f"{replay_id}.json"
    if not replay_path.is_file():
        return {"schema": "lex-evaluation-operational-resume-replay-comparison/1",
                "verdict": "REPLAY_MISSING", "measurement_fields_compared": 0,
                "measurement_fields_differing": None}
    original = load(WRAPPER_RECORD)
    replay = load(replay_path)
    keys = sorted((set(original) | set(replay)) - VOLATILE)
    diffs, missing = [], []
    for key in keys:
        if key not in original or key not in replay:
            missing.append(key)
            continue
        if _canon(original[key]) != _canon(replay[key]):
            diffs.append({"field": key,
                          "original": original[key],
                          "replay": replay[key]})
    env_o = original.get("numeric_environment") or {}
    env_r = replay.get("numeric_environment") or {}
    env_diffs = {k: {"original": env_o.get(k), "replay": env_r.get(k)}
                 for k in sorted(set(env_o) | set(env_r))
                 if env_o.get(k) != env_r.get(k)}
    payload = {
        "schema": "lex-evaluation-operational-resume-replay-comparison/1",
        "lane": LANE,
        "run_id": RUN_ID,
        "resumed_run_id": ORIGINAL_RUN,
        "generated_at_utc": utcnow(),
        "original_record": str(WRAPPER_RECORD.relative_to(REPO_ROOT)),
        "original_sha256": sha256(WRAPPER_RECORD),
        "replay_record": str(replay_path.relative_to(REPO_ROOT)),
        "replay_sha256": sha256(replay_path),
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
        "verdict": ("REPLAY_REPRODUCES" if not diffs and not missing
                    else "REPLAY_DIVERGES"),
    }
    write_json(OUT_DIR / f"replay_comparison_{RUN_ID}.json", payload)
    return payload


def check_h3(run_fresh: bool) -> dict:
    if run_fresh or not (SCRATCH_DIR / f"{RUN_ID}_replay.json").is_file():
        run_replay()
    cmp = compare_replay()
    record = load(WRAPPER_RECORD)
    pin_checks, pin_bad = _pin_check(record)
    ok_checks = _agreement_checks(record)
    checks = {**pin_checks, **ok_checks,
              "replay_record_exists": cmp.get("verdict") != "REPLAY_MISSING",
              "replay_reproduces": cmp.get("verdict") == "REPLAY_REPRODUCES",
              "replay_zero_measurement_differences":
                  cmp.get("measurement_fields_differing") == 0,
              "replay_compared_41_fields": cmp.get("measurement_fields_compared") == 41,
              "original_record_not_rewritten":
                  sha256(WRAPPER_RECORD) == (load(
                      REPO_ROOT / "evaluation" / f"OPERATIONAL_RESUME_{RUN_ID}_FREEZE_V1.json"
                  ).get("rehash_before_execution", {})
                   .get("deliverable", {})
                   .get(str(WRAPPER_RECORD.relative_to(REPO_ROOT)))),
              "wrapper_sha_matches_freeze":
                  sha256(WRAPPER_RECORD) == load(
                      REPO_ROOT / "evaluation" / f"OPERATIONAL_RESUME_{RUN_ID}_FREEZE_V1.json"
                  )["rehash_before_execution"]["deliverable"][str(WRAPPER_RECORD.relative_to(REPO_ROOT))],
              "engine_record_sha_matches_freeze":
                  sha256(ENGINE_RECORD) == load(
                      REPO_ROOT / "evaluation" / f"OPERATIONAL_RESUME_{RUN_ID}_FREEZE_V1.json"
                  )["rehash_before_execution"]["deliverable"][str(ENGINE_RECORD.relative_to(REPO_ROOT))],
              "report_sha_matches_freeze":
                  sha256(REPORT) == load(
                      REPO_ROOT / "evaluation" / f"OPERATIONAL_RESUME_{RUN_ID}_FREEZE_V1.json"
                  )["rehash_before_execution"]["deliverable"][str(REPORT.relative_to(REPO_ROOT))],
              }
    delivery = {
        "schema": "lex-evaluation-operational-resume-deliverable-verification/1",
        "lane": LANE,
        "run_id": RUN_ID,
        "resumed_run_id": ORIGINAL_RUN,
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
            "gates": {k: record.get(k) for k in ("n_gates", "n_passed", "n_failed", "n_reported")},
            "failed_gates": [g["gate"] for g in record.get("failed_gates") or []],
            "product_mount_head": record.get("product_mount_head"),
        },
        "n_checks": len(ok_checks),
        "n_failed": sum(1 for v in ok_checks.values() if not v),
        "verdict": "DELIVERABLE_VERIFIED" if all(ok_checks.values()) else "DELIVERABLE_NOT_VERIFIED",
        "claim_ceiling": ("Verification of an already-produced record: pins, internal "
                          "consistency, report agreement and non-vacuity. It creates no new "
                          "measurement, moves no frozen bar, issues no serve or admission "
                          "verdict, and is not an independent audit of 43357838904."),
    }
    write_json(OUT_DIR / f"deliverable_verification_{RUN_ID}.json", delivery)
    return {"hypothesis": "H3", "checks": checks,
            "n_checks": len(checks),
            "n_failed": sum(1 for v in checks.values() if not v),
            "holds": all(checks.values()),
            "pin_rehash": delivery["pin_rehash"],
            "replay": {"verdict": cmp.get("verdict"),
                       "fields_compared": cmp.get("measurement_fields_compared"),
                       "fields_differing": cmp.get("measurement_fields_differing"),
                       "environment_differences": list(cmp.get("environment_disclosure_differences") or {})}}


def pin_checks_filter(checks: dict, section: str) -> dict:
    return {k.split("::", 1)[1]: v for k, v in checks.items() if k.startswith(f"{section}_pin::")}


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


def relocate() -> dict:
    from evaluation.snapshot_audit.write_scope import (
        evaluate_porcelain, reconstruct_snapshot_porcelain)

    RECOVERY_DIR.mkdir(parents=True, exist_ok=True)
    probe = load(OUT_DIR / f"ref_probe_{RUN_ID}.json")
    items, provenance = [], {}
    for rel in INHERITED:
        src = REPO_ROOT / rel
        dst = RECOVERY_DIR / src.name
        before = sha256(src)
        preexisted = dst.is_file()
        shutil.copyfile(src, dst)
        after = sha256(src)
        provenance[rel] = {**git_log(rel), "sha256": after,
                           "producer_authored": git_log(rel).get("author_name") == "lex-evaluation-team"}
        items.append({
            "source_path": rel,
            "copy_path": str(dst.relative_to(REPO_ROOT)),
            "source_exists": True,
            "copy_preexisted": preexisted,
            "source_sha256_before": before,
            "source_sha256_after": after,
            "copy_sha256": sha256(dst),
            "byte_identical": sha256(dst) == after,
            "source_unchanged_by_copy": before == after,
            "why": ("producer-authored file written into the independent auditor's "
                    "namespace; copied byte-for-byte into the lane namespace, never "
                    "deleted or rewritten in place"),
        })

    repro_2 = reconstruct_snapshot_porcelain(REPO_ROOT, BASE_SHA, SNAPSHOT_SHA)
    verdict_2 = evaluate_porcelain(repro_2["porcelain_lines"], LANE)
    repro_1 = reconstruct_snapshot_porcelain(
        REPO_ROOT, "240ca2d9d4b063652440e80fdd9bcd9e6602c1de",
        "a886bf2a4abba44d7bc2d14c0cef37e12bd73c76")
    verdict_1 = evaluate_porcelain(repro_1["porcelain_lines"], LANE)
    write_json(OUT_DIR / f"write_scope_repro_{ORIGINAL_RUN}.json",
               {"schema": "lex-evaluation-write-scope/1", "mode": "repro-from-git",
                "reconstruction": repro_1, "verdict": verdict_1})

    gate_1 = load(REPO_ROOT / "results/audit/evaluation/CYCLE_43342851837_GATE.json")
    gate_2 = load(REPO_ROOT / "results/audit/evaluation/CYCLE_43349645400_GATE.json")
    contradictions = [
        {
            "id": "P1",
            "field": "gate verdict",
            "producer_claim": f"CYCLE_43349645400_GATE.json gate={gate_2.get('gate')!r}, safe_to_integrate={gate_2.get('safe_to_integrate')!r}",
            "recomputed": ("the audit job of run 43349645400 was SKIPPED (conclusion=skipped); "
                           "the independent audit of the accumulated snapshot is this run's "
                           "deliverable and does not exist yet; a producer cannot pass itself"),
        },
        {
            "id": "P2",
            "field": "run status",
            "producer_claim": "CYCLE_43349645400_GATE.json claim_ceiling asserts 'operational-resume verification of persisted producer snapshot run 43344048907 ... All 4 frozen hypotheses verified'",
            "recomputed": ("run 43344048907's own team job FAILED at 'Run lane cycle' (step 6); "
                           "'Validate active MVP producer state' and 'Enforce lane write scope' "
                           "were skipped; an audit and integrate job were skipped. The producer "
                           "self-report is not a gate, whatever it says."),
        },
        {
            "id": "P3",
            "field": "status upgrade across cycles",
            "producer_claim": f"CYCLE_43342851837_GATE.json gate={gate_1.get('gate')!r}, safe_to_integrate={gate_1.get('safe_to_integrate')!r}",
            "recomputed": (f"CYCLE_43349645400_GATE.json gate={gate_2.get('gate')!r}, "
                           f"safe_to_integrate={gate_2.get('safe_to_integrate')!r} on the same "
                           "underlying deliverable bytes with no new measurement, no new "
                           "evidence and no independent audit. The later producer self-gate "
                           "silently upgrades the earlier one."),
        },
        {
            "id": "P4",
            "field": "auditor activity",
            "producer_claim": "the pseudo-audit reports read as auditor-authored findings",
            "recomputed": ("every one of the four files was committed by lex-evaluation-team "
                           "<lex-team@autonomous.local>; the audit jobs of runs 43342851837, "
                           "43344048907, 43349645400 and 43357838904 were all SKIPPED; no "
                           "auditor executed anything."),
        },
    ]

    checks = [
        {"check": "all_sources_exist", "passed": all(i["source_exists"] for i in items)},
        {"check": "all_copies_byte_identical", "passed": all(i["byte_identical"] for i in items)},
        {"check": "originals_unchanged_by_copy",
         "passed": all(i["source_unchanged_by_copy"] for i in items)},
        {"check": "originals_retained_in_place",
         "passed": all((REPO_ROOT / i["source_path"]).is_file() for i in items)},
        {"check": "no_independent_audit_exists_for_any_of_the_four_runs",
         "passed": all(probe.get("audit_ref_present", {}).get(r) is False
                       for r in [ORIGINAL_RUN, BASE2_RUN, BASE_RUN, RESUMED])},
        {"check": "pseudo_gates_disclosed_as_producer_authored",
         "passed": all(v["producer_authored"] for v in provenance.values())},
    ]
    record = {
        "schema": "lex-evaluation-audit-ns-relocation/1",
        "run_id": RUN_ID,
        "cycles_relocated": [int(ORIGINAL_RUN), int(BASE_RUN)],
        "generated_at_utc": utcnow(),
        "items": items,
        "git_provenance": provenance,
        "checks": checks,
        "originals_retained": True,
        "originals_deleted": False,
        "originals_edited": False,
        "independent_audit_provenance": False,
        "independent_audit_status": {
            r: {
                "audit_ref": f"refs/heads/cycle/core/evaluation/{r}/audit",
                "audit_ref_exists": False,
                "audit_job_conclusion": "skipped",
                "team_conclusion": "failure",
                "failing_step": failing_steps(job_map(OUT_DIR / "api" / f"jobs_{r}.json").get("team", {})),
                "conclusion": f"NO INDEPENDENT AUDIT EXISTS for {r}.",
            }
            for r in [ORIGINAL_RUN, BASE2_RUN, BASE_RUN, RESUMED]
        },
        "contradictions": contradictions,
        "scope_repro": {
            ORIGINAL_RUN: {"bad_paths": verdict_1.get("bad_paths"),
                           "n_bad": verdict_1.get("n_bad"),
                           "verdict": verdict_1.get("verdict")},
            BASE_RUN: {"bad_paths": verdict_2.get("bad_paths"),
                       "n_bad": verdict_2.get("n_bad"),
                       "verdict": verdict_2.get("verdict")},
        },
        "disposition": (
            "The four originals stay at their audit-namespace paths as historical "
            "evidence of the producer's out-of-scope writes; their content is "
            "duplicated byte-for-byte under "
            f"results/evaluation/audit_namespace_recovery_{RUN_ID}/. No gate status "
            "is adopted, upgraded or downgraded. Neither file may be quoted as an "
            "independent audit in either direction. A future independent audit of "
            "this run must write its own results/audit/evaluation/"
            f"CYCLE_{RUN_ID}_GATE.json."),
        "verdict": "RELOCATED_APPEND_ONLY" if all(c["passed"] for c in checks) else "RELOCATION_INCOMPLETE",
    }
    write_json(RECOVERY_DIR / f"RELOCATION_RECORD_{RUN_ID}.json", record)
    return record


def check_relocation() -> dict:
    rec_path = RECOVERY_DIR / f"RELOCATION_RECORD_{RUN_ID}.json"
    if not rec_path.is_file():
        return {"hypothesis": "H5-relocation", "checks": {"relocation_record_exists": False},
                "n_checks": 1, "n_failed": 1, "holds": False}
    rec = load(rec_path)
    checks = {"relocation_record_exists": True}
    for item in rec.get("items", []):
        src = REPO_ROOT / item["source_path"]
        dst = REPO_ROOT / item["copy_path"]
        checks[f"source_exists::{item['source_path']}"] = src.is_file()
        checks[f"copy_byte_identical::{item['copy_path']}"] = (
            src.is_file() and dst.is_file() and sha256(src) == sha256(dst))
        checks[f"source_unchanged::{item['source_path']}"] = (
            src.is_file() and sha256(src) == item["source_sha256_before"])
    checks["originals_retained_flag"] = rec.get("originals_retained") is True
    checks["originals_not_deleted_flag"] = rec.get("originals_deleted") is False
    checks["originals_not_edited_flag"] = rec.get("originals_edited") is False
    checks["independent_audit_provenance_false"] = rec.get("independent_audit_provenance") is False
    checks["verdict_is_RELOCATED_APPEND_ONLY"] = rec.get("verdict") == "RELOCATED_APPEND_ONLY"
    checks["all_record_checks_pass"] = all(c.get("passed") for c in rec.get("checks", []))
    return {"hypothesis": "H5-relocation", "checks": checks,
            "n_checks": len(checks),
            "n_failed": sum(1 for v in checks.values() if not v),
            "holds": all(checks.values())}


def live_scope() -> dict:
    from evaluation.snapshot_audit.write_scope import evaluate_porcelain, live_porcelain
    verdict = evaluate_porcelain(live_porcelain(REPO_ROOT), LANE)
    write_json(OUT_DIR / f"write_scope_live_{RUN_ID}.json",
               {"schema": "lex-evaluation-write-scope/1", "mode": "live",
                "repo_root": str(REPO_ROOT), "verdict": verdict})
    return verdict


def _run_json(cmd: list[str], out: Path, timeout: int = 3600) -> tuple[int, dict | None, str]:
    out.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                          timeout=timeout)
    return proc.returncode, (load(out) if out.is_file() else None), (proc.stdout + proc.stderr)[-3000:]


def check_h5(final: bool) -> dict:
    scope = live_scope()
    relocation = check_relocation()
    checks = dict(relocation["checks"])
    checks["live_write_scope_is_SCOPE_CLEAN"] = scope.get("verdict") == "SCOPE_CLEAN"
    porcelain = git("status", "--porcelain", "-uall")
    out_of_scope_dirty = [line[3:].strip() for line in porcelain.splitlines()
                          if line[3:].strip().startswith(("results/audit/", "reports/audit/"))]
    checks["no_audit_namespace_path_added_modified_or_deleted_by_this_run"] = not out_of_scope_dirty

    integrity = suite = None
    if final:
        sig_out = OUT_DIR / f"state_integrity_gate_{RUN_ID}.json"
        rc_i, integrity, tail_i = _run_json(
            [sys.executable, "evaluation/state_integrity_gate.py",
             "--run-id", RUN_ID, "--out", str(sig_out)], sig_out)
        checks["state_integrity_ran"] = integrity is not None
        checks["state_integrity_ALL_CHECKS_PASS"] = (
            integrity or {}).get("verdict") == "ALL_CHECKS_PASS"
        suite_out = OUT_DIR / f"lane_suite_{RUN_ID}.json"
        rc_s, suite, tail_s = _run_json(
            [sys.executable, "evaluation/lane_suite.py", "--skip-pytest",
             "--out", str(suite_out)], suite_out, timeout=5400)
        checks["lane_suite_ran"] = suite is not None
        checks["lane_suite_PASS"] = bool(suite) and (
            suite.get("overall_pass") is True
            or suite.get("verdict") in {"PASS", "ALL_CHECKS_PASS"}
            or ((suite.get("n_failed") == 0) and (suite.get("n_checks", 0) > 0)))
        checks["state_integrity_rc_zero"] = rc_i == 0
        checks["lane_suite_rc_zero"] = rc_s == 0
        checks["state_files_agree_on_identity"] = _state_identity_agrees()

    return {"hypothesis": "H5", "checks": checks,
            "n_checks": len(checks),
            "n_failed": sum(1 for v in checks.values() if not v),
            "holds": all(checks.values()),
            "out_of_scope_dirty": out_of_scope_dirty,
            "write_scope_verdict": scope.get("verdict"),
            "state_integrity_verdict": (integrity or {}).get("verdict"),
            "lane_suite_verdict": ((suite or {}).get("verdict")
                                   or ("PASS" if (suite or {}).get("overall_pass") else None))}


def _state_identity_agrees() -> bool:
    root = load(REPO_ROOT / "state" / "evaluation.json")
    lane = load(REPO_ROOT / "evaluation" / "state" / "evaluation.json")
    keys = ("accepted_run_id", "direction_version", "github_run")
    return all(root.get(k) == lane.get(k) for k in keys) and root.get("github_run") == int(RUN_ID)


def run(phase: str) -> tuple[int, dict]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        h1 = check_h1()
        h1 = {"hypothesis": "H1", **{k: h1[k] for k in
                                     ("checks", "n_checks", "n_failed", "holds",
                                      "failing_steps", "audit_conclusion",
                                      "integrate_conclusion")}}
        h2 = check_h2()
        h2 = {"hypothesis": "H2", **{k: h2[k] for k in
                                     ("checks", "n_checks", "n_failed", "holds",
                                      "bad_paths")}}
        h3 = check_h3(run_fresh=(phase == "prepare"))
        h4 = check_h4()
        relocate()
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
        "hypotheses": results,
        "n_hypotheses": len(results),
        "n_hypotheses_holding": sum(1 for r in results if r["holds"]),
        "n_checks": sum(r["n_checks"] for r in results),
        "n_failed": sum(r["n_failed"] for r in results),
        "verdict": ("RESUME_VERIFIED_AUDIT_READY" if holds
                    else ("PREPARE_COMPLETE" if phase == "prepare" else
                          "RESUME_VERIFICATION_FAILED")),
        "failure_modes_diagnosed": [
            f"{RESUMED}: LANE_CYCLE_EXECUTION_FAILURE_ZERO_DELTA",
            f"{BASE_RUN}: WRITE_SCOPE_VIOLATION_PRODUCER_AUDIT_NAMESPACE",
        ],
        "independent_audit_of_resumed_run_exists": False,
        "continue_recommended": False,
        "claim_ceiling": (
            "Operational-resume verification only: it re-derives the two orchestration "
            "failures, verifies the delivered record's pins and replay equality, "
            "re-adjudicates the item-(2) precondition, and dispositions inherited "
            "producer-authored audit-namespace files append-only. It creates no new "
            "product measurement, moves no frozen bar, rubric, threshold or verdict "
            "contract, issues no serve or admission verdict, and is NOT an independent "
            "audit of run 43357838904 or of this run."),
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
                                     for h in payload.get("hypotheses", [])]}, indent=1))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
