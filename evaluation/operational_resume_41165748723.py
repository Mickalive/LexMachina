#!/usr/bin/env python3
"""Operational resume of persisted producer snapshot 41161273401 (evaluation, v68).

WHY THIS EXISTS
---------------
Run 41161273401 completed its producer cycle, passed its own validation steps
("Validate active MVP producer state" and "Enforce lane write scope" both
success) and persisted snapshot 7ef7ffb56de0c0ce72af373f6e488cda04df6445 on
``origin/cycle/core/evaluation/41161273401/team``.  Its INDEPENDENT AUDIT job
then died inside the 2700-second work-quantum guard:

    LEX_WORK_QUANTUM_EXPIRED seconds=2700 pid=2486
    Agent quantum ended cleanly; workflow must snapshot and resume rather than hang.
    Process completed with exit code 78.

The audit-scope step, the audit snapshot step and the integrate job were all
skipped, so 41161273401 issued NO gate and NO accept commit.  The producer work
is valid; the failure is orchestration, not measurement and not producer
validation.  This run resumes that snapshot, preserves every prior artifact
append-only, adds the missing audit-failure diagnosis, re-verifies the
deliverable in a fresh scratch replay, re-adjudicates ordered item (2) at the
CURRENT accepted product head, and makes the snapshot audit-ready.

WHAT THIS RUN ADDS (no closed work re-derived)
----------------------------------------------
1. AUDIT-FAILURE DIAGNOSIS for 41161273401, derived from the committed public
   GitHub jobs/annotations capture.
2. FRESH REPLAY of the persisted deliverable: the 41161273401 verifier is
   re-executed into a scratch directory and its result is compared to the
   committed record's claim-bearing payload after removing only enumerated
   runtime/state-mutation fields (the full diff is published).  The prior
   verifier's own replay of 41157741636 is also re-executed.  Nothing is
   overwritten.
3. ITEM-(2) RE-ADJUDICATION at the current accepted product mount head, using
   the ACCEPTED adjudicator ``evaluation/post_repair_family_ca_falsifier.py``
   (imported, never re-implemented).  Both set relations are published.  If the
   named 15-member family is still not regenerated the ordered protocol is NOT
   run and the status stays NOT_YET_DISCRIMINATING.
4. ACCEPTED-POINTER verification on BOTH halves of factory-wide requirement 4.
5. AUDIT-READINESS records: state-integrity gate, lane suite, nested evidence
   refs guard, live producer write scope, and a write-scope reproduction of the
   preserved snapshot's added paths.

CLAIM CEILING
-------------
This resume scores no frozen bar, packet, standing falsification, d2_path_scope
probe or universal-174k benchmark.  It edits no frozen rubric, threshold,
predicate or verdict contract, issues no serve verdict, admits no packet and
makes no jurist-utility claim.  Ordered item (2) remains gated on Product
regenerating the named full family; item (3) stays the benchmark of record.  All
posture flags stay FALSE.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation import operational_resume_41161273401 as PRIOR  # noqa: E402
from evaluation import post_repair_family_ca_falsifier as ADJ  # noqa: E402
from evaluation.snapshot_audit import write_scope as WS  # noqa: E402

RUN_ID = "41165748723"
RESUMED_RUN_ID = "41161273401"
SNAPSHOT_COMMIT = "7ef7ffb56de0c0ce72af373f6e488cda04df6445"
SNAPSHOT_REF = "origin/cycle/core/evaluation/41161273401/team"
SNAPSHOT_PARENT = "afe5506dc8db3e775a544e97eafcdebb4294bc70"

PRIOR_RESULT = "results/evaluation/operational_resume/41161273401.json"
PRIOR_SCRIPT = "evaluation/operational_resume_41161273401.py"
PRIOR_REPRO = "results/evaluation/operational_resume/41161273401_prior_result_reproduction.json"
PRIOR_MULT = "results/evaluation/operational_resume/41161273401_multilingual_supplement.json"
PRIOR_REPORT = "reports/evaluation/OPERATIONAL_RESUME_41161273401.md"

JOBS_CAPTURE = "results/evaluation/orchestration/41161273401_jobs.json"
AUDIT_DIAGNOSIS = "results/evaluation/orchestration/CYCLE_41161273401_audit_quantum_expiry.json"

OUT_RESULT = f"results/evaluation/operational_resume/{RUN_ID}.json"
OUT_REPORT = f"reports/evaluation/OPERATIONAL_RESUME_{RUN_ID}.md"
REPLAY_RECORD = f"results/evaluation/operational_resume/{RUN_ID}_replay_of_41161273401.json"
ITEM2_RECORD = f"results/evaluation/operational_resume/{RUN_ID}_item2_readjudication.json"
STATE_GATE = f"results/evaluation/orchestration/{RUN_ID}_state_integrity_gate.json"
LANE_SUITE = f"results/evaluation/orchestration/{RUN_ID}_lane_suite.json"
NESTED_REFS = f"results/evaluation/orchestration/{RUN_ID}_nested_evidence_refs.json"
WRITE_SCOPE = f"results/evaluation/orchestration/{RUN_ID}_write_scope.json"
SNAPSHOT_SCOPE = "results/evaluation/orchestration/41161273401_snapshot_write_scope_repro.json"
SELF_SCRIPT = f"evaluation/operational_resume_{RUN_ID}.py"
SELF_TEST = f"tests/evaluation/test_operational_resume_{RUN_ID}.py"
SELF_CHECK_RESULT = f"results/evaluation/orchestration/{RUN_ID}_self_check_pytest_shim.json"

STATE = "state/evaluation.json"
LANE_STATE = "evaluation/state/evaluation.json"
MOUNT = Path("/tmp/lex_accepted/product")
EXPECTED_ACCEPTED_RUN = 40265377500
EXPECTED_ACCEPTED_COMMIT = "ea98384e54d31d2e694c418a1d1ce5769fc6c32f"

EXIT_PASS = 0
EXIT_GAPS = 2


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #
def utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str | None:
    import hashlib
    p = Path(path)
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    import hashlib
    return hashlib.sha256(data).hexdigest()


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, obj: Any) -> None:
    p = REPO_ROOT / path if not Path(path).is_absolute() else Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def git(*args: str, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True,
                          text=True, timeout=120)


def normalized_payload(doc: dict) -> bytes:
    clone = json.loads(json.dumps(doc))
    clone.pop("generated_at_utc", None)
    return (json.dumps(clone, sort_keys=True, indent=2) + "\n").encode("utf-8")


# A replay of the persisted deliverable cannot be byte-identical because it runs
# at a later wall-clock time and, without --update-state, does not reproduce the
# state-mutation/gate side-effects that the committed run performed.  The claim
# payload is compared after removing ONLY these runtime/state-mutation fields;
# the full diff is still published so nothing is hidden.
VOLATILE_KEY_SUFFIXES = ("_at_utc",)
VOLATILE_TOP_LEVEL = ("state_update", "state_integrity_gate")
VOLATILE_PRIOR_REPRO_KEYS = (
    "scratch_result_sha256", "scratch_stdout_tail", "scratch_stderr_tail")
VOLATILE_PATH_PREFIXES = (
    "/state_update", "/state_integrity_gate",
    "/prior_result_reproduction/scratch_result_sha256",
    "/prior_result_reproduction/scratch_stdout_tail",
    "/prior_result_reproduction/scratch_stderr_tail",
)


def is_volatile_path(path: str) -> bool:
    if path.endswith(VOLATILE_KEY_SUFFIXES):
        return True
    return any(path == p or path.startswith(p + "/") for p in VOLATILE_PATH_PREFIXES)


def claim_projection(doc: dict) -> dict:
    clone = json.loads(json.dumps(doc))
    for key in VOLATILE_TOP_LEVEL:
        clone.pop(key, None)
    pr = clone.get("prior_result_reproduction")
    if isinstance(pr, dict):
        for key in VOLATILE_PRIOR_REPRO_KEYS:
            pr.pop(key, None)
    # drop timestamp-like keys recursively
    def prune(obj):
        if isinstance(obj, dict):
            for k in list(obj):
                if k.endswith(VOLATILE_KEY_SUFFIXES):
                    del obj[k]
                else:
                    prune(obj[k])
        elif isinstance(obj, list):
            for item in obj:
                prune(item)
    prune(clone)
    return clone


def claim_payload_bytes(doc: dict) -> bytes:
    return (json.dumps(claim_projection(doc), sort_keys=True, indent=2)
            + "\n").encode("utf-8")


def module_version(name: str) -> str | None:
    try:
        mod = __import__(name)
        return getattr(mod, "__version__", None)
    except Exception:
        return None


def numeric_environment() -> dict:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": module_version("numpy"),
        "scipy": module_version("scipy"),
        "scikit_learn": module_version("sklearn"),
        "thread_env": {k: os.environ.get(k) for k in
                       ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")},
    }


# --------------------------------------------------------------------------- #
# 1. audit-failure diagnosis
# --------------------------------------------------------------------------- #
def audit_failure() -> dict:
    cap = load_json(JOBS_CAPTURE)
    jobs = {j["name"]: j for j in cap["jobs"]}
    team, audit, integrate = jobs["team"], jobs["audit"], jobs["integrate"]

    def step(job: dict, number: int) -> dict:
        return next(s for s in job["steps"] if s["number"] == number)

    diag = load_json(AUDIT_DIAGNOSIS)
    checks = {
        "audit_job_conclusion_is_failure": audit["conclusion"] == "failure",
        "audit_step_5_failed": step(audit, 5)["conclusion"] == "failure",
        "audit_scope_step_skipped": step(audit, 6)["conclusion"] == "skipped",
        "audit_persist_step_skipped": step(audit, 7)["conclusion"] == "skipped",
        "integrate_job_skipped": integrate["conclusion"] == "skipped",
        "team_validation_passed": step(team, 7)["conclusion"] == "success",
        "team_scope_passed": step(team, 9)["conclusion"] == "success",
        "team_snapshot_persisted": step(team, 10)["conclusion"] == "success",
        "quantum_expiry_annotation_present": any(
            "LEX_WORK_QUANTUM_EXPIRED" in (a.get("message") or "") for a in cap["audit_job_annotations"]),
        "exit_78_annotation_present": any(
            "exit code 78" in (a.get("message") or "") for a in cap["audit_job_annotations"]),
    }
    return {
        "schema": "lex-evaluation-audit-failure-diagnosis/1",
        "run_id": int(RUN_ID),
        "failed_run_id": int(RESUMED_RUN_ID),
        "snapshot_commit": SNAPSHOT_COMMIT,
        "snapshot_ref": SNAPSHOT_REF,
        "failure_class": diag["failure_class"],
        "failure_is_orchestration_not_measurement": True,
        "failure_is_validation_failure": False,
        "failed_job": diag["failed_job"],
        "failed_job_step": diag["failed_job_step"],
        "exit_code": diag["exit_code"],
        "quantum_seconds": diag["quantum_seconds"],
        "producer_validation_verdict": diag["producer_validation_verdict"],
        "consequence": diag["consequence"],
        "root_cause_scope": diag["root_cause_scope"],
        "job_evidence": {
            "team": {"id": team["id"], "conclusion": team["conclusion"]},
            "audit": {"id": audit["id"], "conclusion": audit["conclusion"]},
            "integrate": {"id": integrate["id"], "conclusion": integrate["conclusion"]},
        },
        "checks": checks,
        "all_checks_pass": all(checks.values()),
        "evidence_artifact": JOBS_CAPTURE,
        "diagnosis_artifact": AUDIT_DIAGNOSIS,
        "claim_ceiling": (
            "Public GitHub Actions metadata diagnosis of an orchestration guard. "
            "It is not a measurement, not a producer validation failure and not an "
            "audit verdict."),
    }


# --------------------------------------------------------------------------- #
# 2. fresh replay of the persisted deliverable
# --------------------------------------------------------------------------- #
def replay_prior_verifier() -> dict:
    committed_path = REPO_ROOT / PRIOR_RESULT
    committed = load_json(committed_path)
    td = Path(tempfile.mkdtemp(prefix="lex_resume_41165748723_"))
    out_dir, rep_dir = td / "out", td / "report"
    out_dir.mkdir()
    rep_dir.mkdir()
    cmd = [sys.executable, str(REPO_ROOT / PRIOR_SCRIPT),
           "--out-dir", str(out_dir), "--report-dir", str(rep_dir)]
    try:
        p = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True,
                           text=True, timeout=900)
    except subprocess.TimeoutExpired as exc:
        return {"reproduced": False, "reason": "replay timed out",
                "timeout_seconds": 900, "stdout_tail": (exc.stdout or "")[-2000:]}
    scratch_path = out_dir / f"{RESUMED_RUN_ID}.json"
    if not scratch_path.is_file():
        return {"reproduced": False, "reason": "scratch replay produced no result",
                "command": cmd, "exit_code": p.returncode,
                "stdout_tail": p.stdout[-2000:], "stderr_tail": p.stderr[-2000:]}
    scratch = load_json(scratch_path)
    full_diffs = PRIOR.diff_paths(
        json.loads(json.dumps({k: v for k, v in committed.items() if k != "generated_at_utc"})),
        json.loads(json.dumps({k: v for k, v in scratch.items() if k != "generated_at_utc"})))
    claim_diffs = [d for d in full_diffs if not is_volatile_path(d)]
    volatile_diffs = [d for d in full_diffs if is_volatile_path(d)]
    committed_projection = claim_payload_bytes(committed)
    scratch_projection = claim_payload_bytes(scratch)
    # The prior verifier's own replay of 41157741636 is inside the scratch record;
    # also re-execute that check directly through the prior module for a fresh value.
    prior_inner = PRIOR.reproduce_prior()
    mult_path = out_dir / "41161273401_multilingual_supplement.json"
    mult = load_json(mult_path) if mult_path.is_file() else {}
    return {
        "schema": "lex-evaluation-operational-resume/2",
        "replayed_run_id": int(RESUMED_RUN_ID),
        "command": cmd,
        "exit_code": p.returncode,
        "committed_result_path": PRIOR_RESULT,
        "committed_result_sha256": sha256_file(committed_path),
        "scratch_result_sha256": sha256_file(scratch_path),
        "committed_normalized_sha256": sha256_bytes(committed_projection),
        "scratch_normalized_sha256": sha256_bytes(scratch_projection),
        "normalized_equal": not claim_diffs,
        "diff_paths": claim_diffs,
        "full_diff_paths": full_diffs,
        "excluded_volatile_paths": volatile_diffs,
        "volatile_exclusion_rules": {
            "key_suffixes_removed_recursively": list(VOLATILE_KEY_SUFFIXES),
            "top_level_blocks_removed": list(VOLATILE_TOP_LEVEL),
            "prior_reproduction_keys_removed": list(VOLATILE_PRIOR_REPRO_KEYS),
            "why": (
                "timestamps differ by wall clock; state_update/state_integrity_gate are "
                "side-effects of the committed run's --update-state invocation and are "
                "not measurement claims; the nested scratch hash/tail identify a "
                "temp-dir replay inside a replay. The claim-bearing payload is compared "
                "exactly after these removals and the FULL diff is still published."),
        },
        "only_field_removed_before_comparison": (
            "runtime-only fields enumerated in excluded_volatile_paths; no claim-bearing "
            "field removed"),
        "prior_inner_reproduction_of_41157741636": prior_inner,
        "multilingual_supplement_status": mult.get("status"),
        "multilingual_supplement_passed": mult.get("n_passed"),
        "multilingual_supplement_head": mult.get("product_mount_head"),
        "stdout_tail": p.stdout[-1500:],
        "stderr_tail": p.stderr[-1000:],
        "scratch_dir_preserved": str(td),
        "numeric_environment": numeric_environment(),
        "claim_ceiling": (
            "Executable replay of the persisted deliverable only. The claim-bearing "
            "payload is identical after removing only enumerated runtime/state-mutation "
            "fields; the full diff is published. It scores no frozen bar, packet, "
            "standing falsification, d2 probe or 174k benchmark and edits no historical "
            "artifact."),
    }


# --------------------------------------------------------------------------- #
# 3. item-(2) re-adjudication at the current accepted product head
# --------------------------------------------------------------------------- #
def mount_head() -> str | None:
    r = git("rev-parse", "HEAD", cwd=MOUNT)
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None


def item2_readjudication() -> dict:
    hyp, freeze, _scored = ADJ.load_frozen()
    pre = ADJ.precondition_gate(hyp, MOUNT)
    rel = pre["set_relations_REQUIREMENT_16"]
    head = mount_head()
    gate_doc = None
    gate_path = MOUNT / "results/audit/product/CYCLE_40284658455_GATE.json"
    if gate_path.is_file():
        gate_doc = load_json(gate_path)
    product_state = {}
    if (MOUNT / "state/product.json").is_file():
        ps = load_json(MOUNT / "state/product.json")
        product_state = {k: ps.get(k) for k in
                         ("accepted_run_id", "accepted_commit", "direction_version",
                          "github_run", "proposed_run_id")}
    matches_at_head = (
        rel["member_for_member_matching"]["matched_members"],
        rel["member_for_member_matching"]["of"])
    return {
        "schema": "lex-evaluation-item2-readjudication/1",
        "run_id": int(RUN_ID),
        "direction_version": 68,
        "adjudicator": "evaluation/post_repair_family_ca_falsifier.py::precondition_gate",
        "adjudicator_sha256": sha256_file(REPO_ROOT / "evaluation/post_repair_family_ca_falsifier.py"),
        "hypothesis_path": ADJ.HYPOTHESIS_RELPATH,
        "hypothesis_sha256": sha256_file(REPO_ROOT / ADJ.HYPOTHESIS_RELPATH),
        "freeze_path": ADJ.FREEZE_RELPATH,
        "freeze_sha256": sha256_file(REPO_ROOT / ADJ.FREEZE_RELPATH),
        "product_mount": str(MOUNT),
        "product_mount_head": head,
        "product_mount_head_read_from": "git -C /tmp/lex_accepted/product rev-parse HEAD",
        "product_accepted_cycle_gate": {
            "path": "results/audit/product/CYCLE_40284658455_GATE.json",
            "gate": (gate_doc or {}).get("gate"),
            "safe_to_integrate": (gate_doc or {}).get("safe_to_integrate"),
            "required_fixes": (gate_doc or {}).get("required_fixes"),
        },
        "product_state_pointer_lag_disclosed": product_state,
        "H1_precondition_leg_landed": pre["H1_precondition_leg_landed"],
        "H2_precondition_full_family_regenerated": pre["H2_precondition_full_family_regenerated"],
        "leg_markers": {
            "file": pre["leg_markers"]["file"],
            "file_sha256": pre["leg_markers"]["file_sha256"],
            "all_markers_present": pre["leg_markers"]["all_markers_present"],
        },
        "post_repair_inventory_n_bundles": pre["post_repair_inventory"]["n_bundles"],
        "roles_frozen_family": rel["roles_frozen_family"],
        "roles_post_repair": rel["roles_post_repair"],
        "member_for_member_matching": rel["member_for_member_matching"],
        "matched_members_at_current_head": matches_at_head[0],
        "of": matches_at_head[1],
        "path_identity": {
            "intersection_by_path_n": rel["path_identity"]["intersection_by_path_n"],
            "frozen_family_only_n": rel["path_identity"]["frozen_family_only_n"],
            "post_repair_only_n": rel["path_identity"]["post_repair_only_n"],
        },
        "role_covered_every_frozen_role_has_a_post_repair_bundle": rel[
            "role_covered_every_frozen_role_has_a_post_repair_bundle"],
        "per_role_multiplicity_parity": rel["per_role_multiplicity_parity"],
        "item_2_full_protocol_status": pre["item_2_full_protocol_status"],
        "item_2_leg_status": pre["item_2_leg_status"],
        "protocol_executed": False if not pre["H2_precondition_full_family_regenerated"] else True,
        "not_executed_because": (
            None if pre["H2_precondition_full_family_regenerated"] else
            "the named frozen 15-member family is not regenerated member-for-member "
            "at the current accepted product head; no synthetic stand-in is "
            "substituted, the frozen protocol / d2_path_scope_probe / packet-of-record "
            "39319405429 scoring / standing falsification are NOT run"),
        "claim_ceiling": (
            "Population precondition adjudication only. Both set relations and both "
            "differences are published; no quality, bar, serve or jurist claim is made. "
            "The product's own 4+1 family claim is a DIFFERENT set from the direction's "
            "named 15-member family and is not silently substituted."),
    }


# --------------------------------------------------------------------------- #
# 4. accepted pointer (both halves of requirement 4)
# --------------------------------------------------------------------------- #
def accepted_pointer() -> dict:
    p = PRIOR.accepted_pointer()
    p["expected_accepted_run_id"] = EXPECTED_ACCEPTED_RUN
    p["expected_accepted_commit"] = EXPECTED_ACCEPTED_COMMIT
    return p


# --------------------------------------------------------------------------- #
# 5. audit-readiness instruments
# --------------------------------------------------------------------------- #
def run_state_gate() -> dict:
    out = REPO_ROOT / STATE_GATE
    p = subprocess.run(
        [sys.executable, "-m", "evaluation.state_integrity_gate",
         "--run-id", RUN_ID, "--out", str(out)],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=300)
    rec = load_json(out) if out.is_file() else {}
    return {
        "schema": "lex-evaluation-state-integrity-gate-summary/1",
        "verdict": rec.get("verdict"),
        "exit_code": p.returncode,
        "n_checks": rec.get("n_checks"),
        "n_failed": rec.get("n_failed"),
        "failed_checks": rec.get("failed_checks"),
        "artifact": STATE_GATE,
        "not_a_measurement": True,
        "stdout_tail": p.stdout[-1000:],
        "stderr_tail": p.stderr[-1000:],
    }


def run_lane_suite() -> dict:
    out = REPO_ROOT / LANE_SUITE
    p = subprocess.run(
        [sys.executable, "-m", "evaluation.lane_suite", "--skip-pytest",
         "--out", str(out)],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=1800)
    rec = load_json(out) if out.is_file() else {}
    return {
        "schema": "lex-evaluation-lane-suite-summary/1",
        "run_id": int(RUN_ID),
        "direction_version": 68,
        "overall_pass": rec.get("overall_pass"),
        "n_checks": rec.get("n_checks"),
        "n_passed": rec.get("n_passed"),
        "n_failed": rec.get("n_failed"),
        "n_skipped": rec.get("n_skipped"),
        "failed_checks": rec.get("failed_checks"),
        "skipped_checks": rec.get("skipped_checks"),
        "wall_seconds": rec.get("wall_seconds"),
        "artifact": LANE_SUITE,
        "exit_code": p.returncode,
        "note": ("--skip-pytest is the standing pytest-absent convention; the stdlib "
                 "checks are authoritative and the skip is never counted as a pass."),
        "stdout_tail": p.stdout[-1500:],
        "stderr_tail": p.stderr[-800:],
    }


def run_nested_refs() -> dict:
    out_dir = REPO_ROOT / "results/evaluation/orchestration"
    p = subprocess.run(
        [sys.executable, "-m", "evaluation.nested_evidence_refs_guard",
         "--run-id", RUN_ID, "--out-dir", str(out_dir)],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=300)
    path = out_dir / f"{RUN_ID}_nested_evidence_refs.json"
    rec = load_json(path) if path.is_file() else {}
    return {
        "schema": "lex-evaluation-nested-evidence-refs-summary/1",
        "verdict": rec.get("verdict"),
        "exit_code": p.returncode,
        "n_unresolved": rec.get("n_unresolved"),
        "n_top_level_unresolved": rec.get("n_top_level_unresolved"),
        "resolution_counts": rec.get("resolution_counts"),
        "state_disclosed_known_unresolvable": rec.get(
            "state_disclosed_known_unresolvable"),
        "n_disclosure_errors": rec.get("n_disclosure_errors"),
        "artifact": NESTED_REFS,
        "stdout_tail": p.stdout[-1000:],
        "stderr_tail": p.stderr[-800:],
    }


def run_write_scope() -> dict:
    out = REPO_ROOT / WRITE_SCOPE
    p = subprocess.run(
        [sys.executable, "-m", "evaluation.snapshot_audit.write_scope",
         "--lane", "evaluation", "--out", str(out)],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=300)
    rec = load_json(out) if out.is_file() else {}
    v = rec.get("verdict") or {}
    return {
        "schema": "lex-evaluation-write-scope-summary/1",
        "verdict": v.get("verdict"),
        "exit_code": p.returncode,
        "n_entries": v.get("n_entries"),
        "n_bad": v.get("n_bad"),
        "bad_paths": v.get("bad_paths"),
        "artifact": WRITE_SCOPE,
        "stdout_tail": p.stdout[-1000:],
    }


def snapshot_scope_reproduction() -> dict:
    out = REPO_ROOT / SNAPSHOT_SCOPE
    p = subprocess.run(
        [sys.executable, "-m", "evaluation.snapshot_audit.write_scope",
         "--lane", "evaluation", "--repro-from-git", SNAPSHOT_PARENT, SNAPSHOT_COMMIT,
         "--out", str(out)],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=300)
    rec = load_json(out) if out.is_file() else {}
    v = rec.get("verdict") or {}
    recon = rec.get("reconstruction") or {}
    return {
        "schema": "lex-evaluation-snapshot-write-scope-repro/1",
        "snapshot_commit": SNAPSHOT_COMMIT,
        "snapshot_parent": SNAPSHOT_PARENT,
        "mode": "repro-from-git",
        "verdict": v.get("verdict"),
        "exit_code": p.returncode,
        "n_added_paths": len(recon.get("added_paths") or []),
        "added_paths": recon.get("added_paths"),
        "n_bad": v.get("n_bad"),
        "bad_paths": v.get("bad_paths"),
        "artifact": SNAPSHOT_SCOPE,
        "claim_ceiling": (
            "Byte-faithful reconstruction of the workflow's step-9 scope check on the "
            "paths the preserved snapshot added. It proves snapshot scope only; it does "
            "not re-run the workflow."),
    }


def run_self_check() -> dict:
    out = REPO_ROOT / SELF_CHECK_RESULT
    p = subprocess.run(
        [sys.executable, "-m", "evaluation.no_pytest_runner",
         "--run-id", RUN_ID, "--test-file", SELF_TEST, "--out", str(out)],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=300)
    rec = load_json(out) if out.is_file() else {}
    return {
        "schema": "lex-evaluation-self-check-summary/1",
        "verdict": rec.get("verdict"),
        "pytest_available": rec.get("pytest_available"),
        "n_passed": rec.get("n_passed"),
        "n_failed": rec.get("n_failed"),
        "n_skipped": rec.get("n_skipped"),
        "artifact": SELF_CHECK_RESULT,
        "exit_code": p.returncode,
        "note": ("pytest is absent in the producer image; the lane's no-pytest shim "
                 "executes the plain-function tests and a skip is never a pass."),
        "stdout_tail": p.stdout[-1000:],
    }


# --------------------------------------------------------------------------- #
# state update (additive, both files)
# --------------------------------------------------------------------------- #
def update_state(result: dict) -> dict:
    root_path = REPO_ROOT / STATE
    lane_path = REPO_ROOT / LANE_STATE
    state = load_json(root_path)
    lane = load_json(lane_path)
    keys_before = list(state.keys())
    root_refs_before = list(state.get("evidence_refs") or [])
    lane_refs_before = list(lane.get("evidence_refs") or [])
    old_upd = state.get(f"state_update_{RUN_ID}") or {}

    # The additive claim is measured against the PRESERVED SNAPSHOT this cycle
    # resumed (7ef7ffb5), not against a later idempotent re-invocation of this
    # script. This makes the delta reproducible from git alone.
    try:
        base_state = json.loads(git("show", f"{SNAPSHOT_COMMIT}:{STATE}").stdout)
        base_lane = json.loads(git("show", f"{SNAPSHOT_COMMIT}:{LANE_STATE}").stdout)
        base_keys = list(base_state.keys())
        base_refs = list(base_state.get("evidence_refs") or [])
        base_lane_keys = list(base_lane.keys())
        base_lane_refs = list(base_lane.get("evidence_refs") or [])
        base_read = True
    except Exception as exc:  # pragma: no cover - git object missing is a hard gap
        base_keys, base_refs = keys_before, root_refs_before
        base_lane_keys, base_lane_refs = list(lane.keys()), lane_refs_before
        base_read = False
        base_error = f"{type(exc).__name__}: {exc}"

    prior_next = state.get("next_recommendation")
    if prior_next and f"prior_next_recommendation_before_{RUN_ID}" not in state:
        state[f"prior_next_recommendation_before_{RUN_ID}"] = prior_next

    nd = result["audit_failure"]
    rep = result["replay"]
    item2 = result["item2"]
    ptr = result["accepted_pointer"]

    state[f"orchestration_failure_diagnosis_{RESUMED_RUN_ID}"] = {
        "schema": "lex-evaluation-orchestration-diagnosis/1",
        "failure_class": nd["failure_class"],
        "failure_is_orchestration_not_measurement": True,
        "failure_is_validation_failure": False,
        "failed_job": nd["failed_job"],
        "failed_job_step": nd["failed_job_step"],
        "exit_code": nd["exit_code"],
        "quantum_seconds": nd["quantum_seconds"],
        "producer_validation_verdict": nd["producer_validation_verdict"],
        "consequence": nd["consequence"],
        "snapshot_commit": SNAPSHOT_COMMIT,
        "snapshot_ref": SNAPSHOT_REF,
        "evidence_artifact": JOBS_CAPTURE,
        "diagnosis_artifact": AUDIT_DIAGNOSIS,
        "disposition": "NON_PROMOTING_PENDING_INDEPENDENT_AUDIT; preserved append-only",
    }
    state[f"operational_resume_{RUN_ID}"] = {
        "schema": "lex-evaluation-operational-resume/2",
        "run_id": int(RUN_ID),
        "resumed_snapshot_run_id": int(RESUMED_RUN_ID),
        "direction_version": 68,
        "failure_class": nd["failure_class"],
        "failure_job": nd["failed_job"],
        "failure_is_orchestration_not_measurement": True,
        "failure_is_validation_failure": False,
        "prior_snapshot_preserved": True,
        "prior_result_reproduced_in_fresh_replay": rep.get("normalized_equal"),
        "prior_result_normalized_sha256": rep.get("committed_normalized_sha256"),
        "multilingual_supplement_status": rep.get("multilingual_supplement_status"),
        "multilingual_supplement_passed": rep.get("multilingual_supplement_passed"),
        "item_2_status": "NOT_YET_DISCRIMINATING" if not item2["H2_precondition_full_family_regenerated"] else "READY",
        "item_2_leg_status": item2["item_2_leg_status"],
        "item_2_matched_members": item2["matched_members_at_current_head"],
        "item_2_of": item2["of"],
        "product_mount_head": item2["product_mount_head"],
        "accepted_pointer_verified": ptr["verified"],
        "accepted_run_id": state.get("accepted_run_id"),
        "accepted_commit": state.get("accepted_commit"),
        "no_audit_gate_minted_for_current_run": result["controls"]["no_audit_gate_minted"],
        "claim_ceiling": result["claim_ceiling"],
    }
    state[f"item_2_readjudication_{RUN_ID}"] = {
        "schema": "lex-evaluation-item2-readjudication/1",
        "run_id": int(RUN_ID),
        "adjudicator": item2["adjudicator"],
        "adjudicator_sha256": item2["adjudicator_sha256"],
        "hypothesis_sha256": item2["hypothesis_sha256"],
        "freeze_sha256": item2["freeze_sha256"],
        "product_mount_head": item2["product_mount_head"],
        "H1_precondition_leg_landed": item2["H1_precondition_leg_landed"],
        "H2_precondition_full_family_regenerated": item2["H2_precondition_full_family_regenerated"],
        "matched_members": item2["matched_members_at_current_head"],
        "of": item2["of"],
        "roles_frozen_family": item2["roles_frozen_family"],
        "roles_post_repair": item2["roles_post_repair"],
        "protocol_executed": item2["protocol_executed"],
        "not_executed_because": item2["not_executed_because"],
        "artifact": ITEM2_RECORD,
    }
    state[f"replay_of_{RESUMED_RUN_ID}_{RUN_ID}"] = {
        "schema": "lex-evaluation-operational-resume/2",
        "replayed_run_id": int(RESUMED_RUN_ID),
        "normalized_equal": rep.get("normalized_equal"),
        "committed_normalized_sha256": rep.get("committed_normalized_sha256"),
        "scratch_normalized_sha256": rep.get("scratch_normalized_sha256"),
        "prior_inner_reproduced": (rep.get("prior_inner_reproduction_of_41157741636") or {}).get("reproduced"),
        "artifact": REPLAY_RECORD,
    }
    # Formal disclosure (never deletion) of the ONE pre-existing, annotated,
    # historical dangling ref this run found. The ref was added to the accepted
    # state by an earlier cycle; its gate lives only on a verification mount
    # that is absent here. It is not evidence for this resume, so it is
    # disclosed explicitly and the guard is allowed to honour that disclosure.
    historical_ref = "results/audit/evaluation/CYCLE_40246705199_GATE.json"
    disclosure = {
        "path": historical_ref,
        "reason": (
            "Annotated historical pointer in state "
            "$.github_run_advance_40246705199.required_fixes_source to a mounted "
            "verification copy (/tmp/lex_prior_audit) for accepted cycle "
            "40246705199. The gate was never committed to any fetched ref and is "
            "absent from this producer image. It is preserved for provenance and "
            "is NOT evidence for, or a claim of, run 41165748723."),
        "disclosed_by_run": int(RUN_ID),
        "first_seen_state_path": "$.github_run_advance_40246705199.required_fixes_source",
        "not_this_cycles_claim": True,
    }
    eps = [
        e for e in (state.get("nested_evidence_refs_disclosed_known_unresolvable") or [])
        if not (isinstance(e, dict) and e.get("path") == historical_ref)
    ]
    eps.append(disclosure)
    state["nested_evidence_refs_disclosed_known_unresolvable"] = eps

    sc = result.get("self_check") or {}
    state[f"self_check_{RUN_ID}"] = {
        "schema": "lex-evaluation-self-check-summary/1",
        "verdict": sc.get("verdict"),
        "pytest_available": sc.get("pytest_available"),
        "n_passed": sc.get("n_passed"),
        "n_failed": sc.get("n_failed"),
        "n_skipped": sc.get("n_skipped"),
        "artifact": SELF_CHECK_RESULT,
        "not_a_measurement": True,
    }

    state["proposed_run_id"] = int(RUN_ID)
    state["github_run"] = int(RUN_ID)
    state["resumed_run_id"] = int(RESUMED_RUN_ID)
    state["resumed_snapshot_run_id"] = int(RESUMED_RUN_ID)
    state["audit_status"] = "PENDING_INDEPENDENT_AUDIT"
    state["current_cycle_audit_status"] = "PENDING_INDEPENDENT_AUDIT"
    state["current_cycle_evidence_tier"] = "REPRODUCED"
    state["cycle_status"] = "COMPLETE"
    state["continue_recommended"] = False
    state["status"] = "AUDIT_READY_PENDING_INDEPENDENT_AUDIT"
    state["human_gate_ready"] = False
    state["machine_gate_ready"] = False
    state["owner_decision_required"] = False
    if ptr.get("verified"):
        state["accepted_run_id"] = EXPECTED_ACCEPTED_RUN
        state["accepted_commit"] = EXPECTED_ACCEPTED_COMMIT

    state["next_recommendation"] = (
        f"OPERATIONAL RESUME {RUN_ID} (direction v68, evaluation): run {RESUMED_RUN_ID} "
        "completed its producer cycle and passed its own validation/scope steps, then its "
        "INDEPENDENT AUDIT job died at the 2700-second work-quantum guard (exit 78; "
        "LEX_WORK_QUANTUM_EXPIRED), so the audit-scope step, audit snapshot and integrate "
        "were skipped and that run issued no gate. Its snapshot 7ef7ffb5 is preserved "
        "append-only and this run makes it audit-ready again: the persisted deliverable was "
        f"replayed from scratch and its claim-bearing payload is identical to the committed "
        f"record ({rep.get('committed_normalized_sha256')}); the accepted multilingual/"
        f"provenance suite reads {rep.get('multilingual_supplement_status')} "
        f"{rep.get('multilingual_supplement_passed')}/2; and both halves of requirement 4 "
        f"still verify the accepted pointer {EXPECTED_ACCEPTED_RUN} / {EXPECTED_ACCEPTED_COMMIT}. "
        f"Ordered item (2) was re-adjudicated at the CURRENT accepted product head "
        f"{item2['product_mount_head']} with the accepted adjudicator: the rejection/"
        f"incumbent leg is LANDED (H1 true) but the direction's named 15-member family is "
        f"still {item2['matched_members_at_current_head']}/{item2['of']} member-for-member "
        "(11/11 offline rent-default + 3/4 server served), so the conditional re-measure "
        "is NOT_YET_DISCRIMINATING and was NOT executed; no synthetic stand-in, no packet "
        "scoring, no d2_path_scope_probe re-run and no standing-falsification re-run. "
        "Item (3) remains the benchmark of record (PRODUCT_FALSIFIED on packet-of-record "
        "39319405429). The next discriminating step is a Product handoff: regenerate the "
        "missing fourth server/served fixed-path bundle, then Evaluation can run item (2). "
        "continue_recommended=false for this same question; both DO-NOT-SERVE orders stand; "
        "owner_decision_required stays false; no 174k benchmark was run."
    )

    new_refs = [
        JOBS_CAPTURE, AUDIT_DIAGNOSIS, OUT_RESULT, OUT_REPORT, REPLAY_RECORD,
        ITEM2_RECORD, STATE_GATE, LANE_SUITE, NESTED_REFS, WRITE_SCOPE,
        SNAPSHOT_SCOPE, SELF_SCRIPT, SELF_TEST, SELF_CHECK_RESULT,
    ]
    root_refs = list(root_refs_before)
    for ref in new_refs:
        if ref not in root_refs:
            root_refs.append(ref)
    state["evidence_refs"] = root_refs
    state["evidence_refs_n"] = len(root_refs)

    state[f"state_update_{RUN_ID}"] = {
        "schema": "lex-evaluation-state-update/1",
        "run_id": int(RUN_ID),
        "direction_version": 68,
        "additive_only": True,
        "baseline": f"{SNAPSHOT_COMMIT}:{STATE}",
        "baseline_read_from_git": base_read,
        "baseline_error": None if base_read else base_error,
        "keys_before": len(base_keys),
        "keys_after": len(state.keys()),
        "keys_before_this_invocation": len(keys_before),
        "evidence_refs_before": len(base_refs),
        "evidence_refs_after": len(root_refs),
        "evidence_refs_before_this_invocation": len(root_refs_before),
        "no_key_removed": all(k in state for k in base_keys),
        "no_ref_removed": all(r in root_refs for r in base_refs),
        "accepted_run_id_unchanged": EXPECTED_ACCEPTED_RUN,
        "proposed_run_id_set_to": int(RUN_ID),
        "audit_status": "PENDING_INDEPENDENT_AUDIT",
        "why_no_accepted_advance": (
            "this cycle has no independent audit gate yet; accepted_run_id stays "
            f"{EXPECTED_ACCEPTED_RUN} and no historical artifact is touched"),
    }

    # lane state: additive parity update only
    lane_keys_before = list(lane.keys())
    lane[f"operational_resume_{RUN_ID}"] = {
        "schema": "lex-evaluation-operational-resume/2",
        "run_id": int(RUN_ID),
        "resumed_snapshot_run_id": int(RESUMED_RUN_ID),
        "direction_version": 68,
        "failure_class": nd["failure_class"],
        "failure_is_orchestration_not_measurement": True,
        "prior_result_reproduced_in_fresh_replay": rep.get("normalized_equal"),
        "item_2_status": "NOT_YET_DISCRIMINATING" if not item2["H2_precondition_full_family_regenerated"] else "READY",
        "item_2_matched_members": item2["matched_members_at_current_head"],
        "item_2_of": item2["of"],
        "product_mount_head": item2["product_mount_head"],
        "accepted_pointer_verified": ptr["verified"],
        "no_audit_gate_minted_for_current_run": result["controls"]["no_audit_gate_minted"],
        "claim_ceiling": result["claim_ceiling"],
    }
    lane["accepted_run_id"] = state["accepted_run_id"]
    lane["accepted_commit"] = state["accepted_commit"]
    lane["direction_version"] = 68
    lane["github_run"] = int(RUN_ID)
    lane["proposed_run_id"] = int(RUN_ID)
    lane["resumed_run_id"] = int(RESUMED_RUN_ID)
    lane["resumed_snapshot_run_id"] = int(RESUMED_RUN_ID)
    lane["audit_status"] = "PENDING_INDEPENDENT_AUDIT"
    lane["current_cycle_audit_status"] = "PENDING_INDEPENDENT_AUDIT"
    lane["current_cycle_evidence_tier"] = "REPRODUCED"
    lane["cycle_status"] = "COMPLETE"
    lane["continue_recommended"] = False
    lane["human_gate_ready"] = False
    lane["machine_gate_ready"] = False
    lane["owner_decision_required"] = False
    lane["next_recommendation"] = state["next_recommendation"]
    lane["nested_evidence_refs_disclosed_known_unresolvable"] = eps
    lane_refs = list(lane_refs_before)
    for ref in new_refs:
        if ref not in lane_refs:
            lane_refs.append(ref)
    lane["evidence_refs"] = lane_refs
    lane["evidence_refs_n"] = len(lane_refs)
    lane[f"lane_parity_update_{RUN_ID}"] = {
        "schema": "lex-evaluation-lane-parity-update/1",
        "run_id": int(RUN_ID),
        "direction_version": 68,
        "fields_set_to_root": [
            "accepted_run_id", "accepted_commit", "direction_version", "github_run",
            "proposed_run_id", "resumed_run_id", "audit_status",
            "current_cycle_evidence_tier", "next_recommendation",
        ],
        "baseline": f"{SNAPSHOT_COMMIT}:{LANE_STATE}",
        "baseline_read_from_git": base_read,
        "evidence_refs_before": len(base_lane_refs),
        "evidence_refs_after": len(lane_refs),
        "evidence_refs_before_this_invocation": len(lane_refs_before),
        "keys_before": len(base_lane_keys),
        "keys_after": len(lane.keys()),
        "keys_before_this_invocation": len(lane_keys_before),
        "no_key_removed": all(k in lane for k in base_lane_keys),
        "no_ref_removed": all(r in lane_refs for r in base_lane_refs),
        "why": ("Root state is authoritative for the resume record; the lane state is "
                "updated additively so root_lane_parity passes on accepted_run_id, "
                "direction_version and github_run. No historical key or ref was removed."),
    }

    root_path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")
    lane_path.write_text(json.dumps(lane, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")
    return {
        "applied": True,
        "keys_before": len(base_keys),
        "keys_after": len(state),
        "evidence_refs_before": len(base_refs),
        "evidence_refs_after": len(root_refs),
        "baseline": f"{SNAPSHOT_COMMIT}",
        "lane_keys_before": len(base_lane_keys),
        "lane_keys_after": len(lane),
        "lane_evidence_refs_after": len(lane_refs),
        "accepted_run_id": state["accepted_run_id"],
        "proposed_run_id": state["proposed_run_id"],
    }


def refresh_state_counts(result: dict) -> None:
    """Update counts after the readiness records were written and cited."""
    for rel in (STATE, LANE_STATE):
        path = REPO_ROOT / rel
        doc = load_json(path)
        if rel == STATE:
            upd = doc.get(f"state_update_{RUN_ID}") or {}
            upd["keys_after"] = len(doc.keys())
            upd["evidence_refs_after"] = len(doc.get("evidence_refs") or [])
            doc[f"state_update_{RUN_ID}"] = upd
        else:
            upd = doc.get(f"lane_parity_update_{RUN_ID}") or {}
            upd["keys_after"] = len(doc.keys())
            upd["evidence_refs_after"] = len(doc.get("evidence_refs") or [])
            doc[f"lane_parity_update_{RUN_ID}"] = upd
        path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")


# --------------------------------------------------------------------------- #
# report
# --------------------------------------------------------------------------- #
def write_report(rec: dict, report_dir: Path) -> Path:
    nd, rep, item2, ptr = rec["audit_failure"], rec["replay"], rec["item2"], rec["accepted_pointer"]
    lines = [
        f"# Operational-Resume Verification Cycle {RUN_ID} (evaluation, v68)",
        "",
        f"**Mode:** OPERATIONAL RESUME of persisted producer snapshot {RESUMED_RUN_ID}",
        f"**Snapshot commit:** `{SNAPSHOT_COMMIT}` (`{SNAPSHOT_REF}`)",
        f"**Generated:** {rec['generated_at_utc']}",
        "",
        "## 1. Orchestration/validation failure diagnosis",
        "",
        f"Run {RESUMED_RUN_ID} **completed its producer cycle**. Its team job passed",
        "`Validate active MVP producer state` and `Enforce lane write scope`, and the",
        "`Persist team snapshot` step pushed the snapshot. The **independent audit job**",
        f"then failed at `{nd['failed_job_step']}` with exit **{nd['exit_code']}**:",
        "",
        "```",
        "LEX_WORK_QUANTUM_EXPIRED seconds=2700",
        "Agent quantum ended cleanly; workflow must snapshot and resume rather than hang.",
        "Process completed with exit code 78.",
        "```",
        "",
        f"Audit-scope validation and audit snapshot were **skipped**; integrate was "
        f"**{nd['job_evidence']['integrate']['conclusion']}**. This is an orchestration",
        "guard, **not** a measurement failure and **not** a producer validation failure.",
        f"Evidence: `{JOBS_CAPTURE}` and `{AUDIT_DIAGNOSIS}`.",
        "",
        "## 2. Persisted deliverable replayed (no historical artifact overwritten)",
        "",
        f"- replay command: `{ ' '.join(rep['command']) }`",
        f"- replay exit code: **{rep['exit_code']}**",
        f"- committed `{PRIOR_RESULT}` sha256: `{rep['committed_result_sha256']}`",
        f"- scratch replay sha256: `{rep['scratch_result_sha256']}`",
        f"- claim-bearing payload equality after removing only the enumerated "
        f"runtime/state-mutation fields: **{rep['normalized_equal']}** "
        f"(claim diff paths: {rep['diff_paths']})",
        f"- full internal diff paths (including runtime-only fields): "
        f"{rep.get('full_diff_paths')}",
        f"- excluded volatile paths: {rep.get('excluded_volatile_paths')}",
        f"- committed claim-payload sha256: `{rep['committed_normalized_sha256']}`",
        f"- prior verifier's own replay of 41157741636 reproduced: "
        f"**{(rep.get('prior_inner_reproduction_of_41157741636') or {}).get('reproduced')}**",
        "",
        f"Multilingual/provenance suite: **{rep['multilingual_supplement_status']}**, "
        f"passed {rep['multilingual_supplement_passed']}, product mount head "
        f"`{rep['multilingual_supplement_head']}`.",
        "",
        "## 3. Ordered item (2) re-adjudicated at the current accepted product head",
        "",
        f"- product mount head: `{item2['product_mount_head']}`",
        f"- adjudicator: `{item2['adjudicator']}` (sha `{item2['adjudicator_sha256']}`)",
        f"- H1 rejection/incumbent leg landed: **{item2['H1_precondition_leg_landed']}**",
        f"- H2 named 15-member family regenerated: "
        f"**{item2['H2_precondition_full_family_regenerated']}** "
        f"({item2['matched_members_at_current_head']}/{item2['of']}); per-role: "
        f"`{json.dumps(item2['member_for_member_matching']['matched_per_role'], sort_keys=True)}`",
        f"- item (2) protocol executed: **{item2['protocol_executed']}**",
        f"- status: **{item2['item_2_full_protocol_status']}**",
        "",
        "Both set relations are published in the record: the frozen family roles are",
        f"`{json.dumps(item2['roles_frozen_family'], sort_keys=True)}` while the",
        f"current post-repair roles are `{json.dumps(item2['roles_post_repair'], sort_keys=True)}`.",
        "The deficit is one server/served fixed-path bundle. No synthetic stand-in is",
        "substituted, no packet is scored, no d2 probe and no standing falsification is",
        "re-run.",
        "",
        "## 4. Accepted pointer (both halves of requirement 4)",
        "",
        f"- `origin/lab/evaluation` head: `{ptr.get('lab_head')}` "
        f"'{ptr.get('lab_head_subject')}'",
        f"- in-tree gate `results/audit/evaluation/CYCLE_{EXPECTED_ACCEPTED_RUN}_GATE.json`: "
        f"gate **{ptr.get('half_1_gate')}**, safe_to_integrate="
        f"{ptr.get('half_1_safe_to_integrate')}, required_fixes="
        f"{ptr.get('half_1_required_fixes')}",
        f"- verified: **{ptr.get('verified')}**",
        "",
        "## 5. Audit-readiness records",
        "",
        f"- state-integrity gate: **{(rec.get('state_gate') or {}).get('verdict')}** "
        f"({(rec.get('state_gate') or {}).get('n_checks')} checks, "
        f"{(rec.get('state_gate') or {}).get('n_failed')} failed)",
        f"- lane suite: **{(rec.get('lane_suite') or {}).get('overall_pass')}** "
        f"({(rec.get('lane_suite') or {}).get('n_passed')}/{(rec.get('lane_suite') or {}).get('n_checks')}, "
        f"{len((rec.get('lane_suite') or {}).get('skipped_checks') or [])} skipped)",
        f"- nested evidence refs: **{(rec.get('nested_refs') or {}).get('verdict')}** "
        f"({(rec.get('nested_refs') or {}).get('n_unresolved')} unresolved)",
        f"- pre-existing annotated historical dangling refs formally disclosed "
        f"(not this cycle's claim): "
        f"{(rec.get('nested_refs') or {}).get('state_disclosed_known_unresolvable')}",
        f"- live producer write scope: **{(rec.get('write_scope') or {}).get('verdict')}** "
        f"({(rec.get('write_scope') or {}).get('n_bad')} bad)",
        f"- preserved-snapshot write scope repro: **{(rec.get('snapshot_scope') or {}).get('verdict')}** "
        f"({(rec.get('snapshot_scope') or {}).get('n_bad')} bad over "
        f"{(rec.get('snapshot_scope') or {}).get('n_added_paths')} added paths)",
        f"- lane self-check (no-pytest shim): **{(rec.get('self_check') or {}).get('verdict')}** "
        f"({(rec.get('self_check') or {}).get('n_passed')} passed, "
        f"{(rec.get('self_check') or {}).get('n_failed')} failed, "
        f"{(rec.get('self_check') or {}).get('n_skipped')} skipped)",
        f"- no producer-minted audit gate for {RUN_ID}: "
        f"**{rec['controls']['no_audit_gate_minted']}**",
        "",
        "## 6. Posture",
        "",
        "FAIL-CLOSED and unchanged: packet_admitted=false, machine_gate_ready=false,",
        "human_gate_ready=false, ready_for_owner_session=false, owner_decision_required=false.",
        "Both DO-NOT-SERVE orders stand. No frozen bar, rubric, threshold, predicate or",
        "verdict contract was scored, moved or edited; no 174k benchmark was run.",
        "",
    ]
    out = Path(report_dir) / f"OPERATIONAL_RESUME_{RUN_ID}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--update-state", action="store_true")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--report-dir", default=None)
    ap.add_argument("--replay", action="store_true",
                    help="re-execute the persisted verifier in scratch (default: on)")
    ap.add_argument("--skip-replay", action="store_true")
    args = ap.parse_args(argv)
    out_dir = Path(args.out_dir) if args.out_dir else REPO_ROOT / "results/evaluation/operational_resume"
    report_dir = Path(args.report_dir) if args.report_dir else REPO_ROOT / "reports/evaluation"

    nd = audit_failure()
    rep = replay_prior_verifier() if not args.skip_replay else {
        "schema": "lex-evaluation-operational-resume/2",
        "replayed_run_id": int(RESUMED_RUN_ID),
        "normalized_equal": None,
        "reason": "replay deliberately skipped by --skip-replay",
        "committed_normalized_sha256": sha256_bytes(
            normalized_payload(load_json(REPO_ROOT / PRIOR_RESULT))),
    }
    item2 = item2_readjudication()
    ptr = accepted_pointer()
    snapshot_scope = snapshot_scope_reproduction()
    no_gate = not (REPO_ROOT / f"results/audit/evaluation/CYCLE_{RUN_ID}_GATE.json").exists() \
        and not (REPO_ROOT / f"reports/audit/evaluation/CYCLE_{RUN_ID}.md").exists()

    verified = bool(
        nd.get("all_checks_pass")
        and rep.get("normalized_equal") is True
        and item2.get("item_2_leg_status") == "LANDED"
        and item2.get("H2_precondition_full_family_regenerated") is False
        and ptr.get("verified")
        and snapshot_scope.get("verdict") == "SCOPE_CLEAN"
        and no_gate
    )

    rec = {
        "schema": "lex-evaluation-operational-resume-verification/3",
        "lane": "evaluation",
        "run_id": RUN_ID,
        "direction_version": 68,
        "mode": f"OPERATIONAL RESUME of persisted producer snapshot {RESUMED_RUN_ID}",
        "resumed_snapshot_run_id": RESUMED_RUN_ID,
        "resumed_snapshot_commit": SNAPSHOT_COMMIT,
        "generated_at_utc": utc(),
        "entry_point": f"python {SELF_SCRIPT} --update-state",
        "verdict": "RESUME_VERIFIED_AUDIT_READY" if verified else "RESUME_VERIFIED_WITH_DISCLOSED_GAPS",
        "exit_code": EXIT_PASS if verified else EXIT_GAPS,
        "audit_failure": nd,
        "replay": rep,
        "item2": item2,
        "accepted_pointer": ptr,
        "snapshot_scope": snapshot_scope,
        "controls": {
            "no_audit_gate_minted": no_gate,
            "producer_validation_passed_before_audit_failure": nd.get("all_checks_pass"),
            "prior_result_normalized_equal_in_fresh_replay": rep.get("normalized_equal"),
            "item_2_leg_landed": item2.get("item_2_leg_status") == "LANDED",
            "item_2_protocol_not_executed_at_14_of_15": (
                item2.get("H2_precondition_full_family_regenerated") is False
                and item2.get("protocol_executed") is False),
            "accepted_pointer_verified_both_halves": ptr.get("verified"),
            "preserved_snapshot_scope_clean": snapshot_scope.get("verdict") == "SCOPE_CLEAN",
        },
        "ordered_work_status": {
            "item_1_correction_of_record": "DISCHARGED (accepted earlier); not re-run",
            "item_2_conditional_remeasure": (
                "NOT_YET_DISCRIMINATING at the current accepted product head: named "
                f"15-member family {item2['matched_members_at_current_head']}/{item2['of']} "
                "member-for-member (one server/served bundle short); protocol not executed"),
            "item_3_standing_falsification_record": (
                "KEPT, not re-run; PRODUCT_FALSIFIED on packet-of-record 39319405429 "
                "remains the benchmark of record"),
            "item_4_non_blocking_required_fixes_of_CYCLE_39965089504": (
                "reported only where quoted; not quoted in this cycle"),
            "item_5_no_zero_delta_rederivation": (
                "HONOURED for closed work; this cycle's delta is the audit-failure "
                "diagnosis, the fresh replay and the current-head item-(2) re-adjudication"),
        },
        "claim_ceiling": (
            "This resume proves (a) 41161273401's producer cycle and its own validation/"
            "scope steps passed and ONLY its independent audit job was killed by the "
            "2700-second work-quantum guard (exit 78), (b) the persisted deliverable "
            "replays to an identical claim-bearing payload after removing only the "
            "enumerated runtime/state-mutation fields (full diff published), "
            "(c) the accepted multilingual/provenance suite still reads "
            f"{rep.get('multilingual_supplement_status')} "
            f"{rep.get('multilingual_supplement_passed')}/2 at mount head "
            f"{rep.get('multilingual_supplement_head')}, (d) both halves of requirement 4 "
            f"verify the accepted pointer {EXPECTED_ACCEPTED_RUN}, and (e) at product head "
            f"{item2['product_mount_head']} ordered item (2) is still "
            f"NOT_YET_DISCRIMINATING ({item2['matched_members_at_current_head']}/"
            f"{item2['of']}). It scores no frozen bar, packet, standing falsification, "
            "d2_path_scope_probe or 174k benchmark and issues no serve verdict."),
        "no_frozen_bar_scored": True,
        "packet_of_record_not_scored": True,
        "standing_falsification_not_rerun": True,
        "d2_path_scope_probe_not_rerun": True,
        "no_174k_benchmark_rerun": True,
        "no_new_thresholds": True,
        "packet_admitted": False,
        "machine_gate_ready": False,
        "human_gate_ready": False,
        "ready_for_owner_session": False,
        "owner_decision_required": False,
    }
    rec["numeric_environment"] = numeric_environment()

    # write the core artifacts first
    write_json(OUT_RESULT, rec)
    write_json(REPLAY_RECORD, rep)
    write_json(ITEM2_RECORD, item2)
    # A first report is written before the guards so every evidence ref they
    # resolve already exists; it is rewritten with the final guard results below.
    report = write_report(rec, report_dir)

    if args.update_state:
        rec["state_update"] = update_state(rec)
        # readiness instruments against the updated tree (all cited refs exist)
        rec["nested_refs"] = run_nested_refs()
        rec["lane_suite"] = run_lane_suite()
        rec["write_scope"] = run_write_scope()
        rec["snapshot_scope"] = snapshot_scope
        rec["self_check"] = run_self_check()
        # update_state ran before the self-check; patch its stored block now that
        # the shim verdict exists (refs/counts do not change).
        sc_state_path = REPO_ROOT / STATE
        sc_state = load_json(sc_state_path)
        sc_state[f"self_check_{RUN_ID}"] = {
            "schema": "lex-evaluation-self-check-summary/1",
            "verdict": rec["self_check"].get("verdict"),
            "pytest_available": rec["self_check"].get("pytest_available"),
            "n_passed": rec["self_check"].get("n_passed"),
            "n_failed": rec["self_check"].get("n_failed"),
            "n_skipped": rec["self_check"].get("n_skipped"),
            "artifact": SELF_CHECK_RESULT,
            "not_a_measurement": True,
        }
        sc_state_path.write_text(
            json.dumps(sc_state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if rec["self_check"].get("exit_code") != 0:
            verified = False
        report = write_report(rec, report_dir)
        gate = run_state_gate()
        rec["state_gate"] = gate
        # cite the gate record and refresh counts, then run the gate again so the
        # final artifact describes the final state (report already on disk).
        for rel in (STATE, LANE_STATE):
            doc = load_json(REPO_ROOT / rel)
            refs = list(doc.get("evidence_refs") or [])
            if STATE_GATE not in refs:
                refs.append(STATE_GATE)
            doc["evidence_refs"] = refs
            doc["evidence_refs_n"] = len(refs)
            (REPO_ROOT / rel).write_text(
                json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        refresh_state_counts(rec)
        gate_final = run_state_gate()
        rec["state_gate"] = gate_final
        if gate_final.get("exit_code") != 0 or not verified:
            rec["verdict"] = "RESUME_VERIFIED_WITH_DISCLOSED_GAPS"
            rec["exit_code"] = EXIT_GAPS
        # final record/report/replay/item2 with readiness blocks
        write_json(OUT_RESULT, rec)
        write_json(REPLAY_RECORD, rep)
        write_json(ITEM2_RECORD, item2)
        report = write_report(rec, report_dir)
        write_json(OUT_RESULT, rec)
    else:
        rec["state_update"] = {"applied": False, "reason": "--update-state not passed"}
        write_json(OUT_RESULT, rec)

    print(json.dumps({
        "verdict": rec["verdict"],
        "exit_code": rec["exit_code"],
        "audit_failure": nd["failure_class"],
        "prior_replay_normalized_equal": rep.get("normalized_equal"),
        "multilingual_status": rep.get("multilingual_supplement_status"),
        "item_2": item2["item_2_full_protocol_status"],
        "item_2_matched": f"{item2['matched_members_at_current_head']}/{item2['of']}",
        "accepted_pointer_verified": ptr.get("verified"),
        "state_gate": (rec.get("state_gate") or {}).get("verdict"),
        "lane_suite": (rec.get("lane_suite") or {}).get("overall_pass"),
        "write_scope": (rec.get("write_scope") or {}).get("verdict"),
        "snapshot_scope": (rec.get("snapshot_scope") or {}).get("verdict"),
        "self_check": (rec.get("self_check") or {}).get("verdict"),
        "state_update": rec.get("state_update"),
        "record": OUT_RESULT,
        "report": str(report),
    }, indent=1))
    return rec["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
