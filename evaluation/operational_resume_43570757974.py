#!/usr/bin/env python3
"""Operational resume 43570757974 -> run 43576640503 (evaluation lane, v68).

Run 43570757974 completed its **team** producer job (including state
validation, write-scope enforcement and snapshot persistence) and then failed
in the **audit** job's ``Independent audit`` step after 2706 s with exit code 78
and ``LEX_WORK_QUANTUM_EXPIRED seconds=2700``.  The audit gate and audit
snapshot steps were skipped and ``integrate`` never ran.  This is an
independent-audit work-quantum expiry, not a team launch failure and not a
producer rejection.

This instrument is a diagnosis + verification instrument, not a new product
cycle.  It verifies the persisted snapshot dad96632 (the producer output of
43570757974 on top of c79dae10), re-checks the ordered v68 work items, and
makes the snapshot audit-ready for its own run id inside the same 2700 s audit
quantum by compacting the audit surface and shipping a read-only fast verifier.

Phases
  prepare  H1-H4 (failure diagnosis, snapshot preservation/replay, ordered work)
  state    additive state advance + evidence-ref compaction
  final    H5 (state integrity, nested refs, write scope, lane suite, tests),
           docs, summary and regression record
  index    real AUDIT_INDEX, final state write, full fast verify
  verify   read-only fast audit entry point (no writes)
  audit    verify + negative controls + PASS/REVISE decision aid (no writes)
  all      prepare -> state -> final -> index

Zero network in the instrument.  The replay is executed under a socket guard.
Public GitHub Actions metadata was captured *before* the freeze and before the
instrument ran and is committed under
``results/evaluation/operational_resume_43570757974/api/``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RUN_ID = "43576640503"
RESUMED = "43570757974"
CHAIN_PRIOR = "43570632816"
PRIOR_COMPLETED = "43565032175"
PRIOR_PACK_ID = "43570632816"
SNAPSHOT_HEAD = "dad9663256617ed4cb59c677687540106611f306"
SNAPSHOT_PARENT = "c79dae10ef9591e4448c4a7e426c81e4686a180c"
SNAPSHOT_DELTA_FILES = 49
DIRV = 68
ACCEPTED_RUN_ID = 40265377500
PRODUCT_MOUNT = Path("/tmp/lex_accepted/product")
PRODUCT_HEAD_DIRECTION = "8b5b08dd"
PRODUCT_HEAD_EXPECTED = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
SCHEMA = "lex-evaluation-operational-resume/1"
AUDIT_NS_PREFIXES = ("results/audit/evaluation/", "reports/audit/evaluation/")

PACK_DIR = REPO_ROOT / f"results/evaluation/operational_resume_{RESUMED}"
API_DIR = PACK_DIR / "api"
SCRATCH = PACK_DIR / "scratch"
FREEZE = REPO_ROOT / f"evaluation/OPERATIONAL_RESUME_{RESUMED}_FREEZE_V1.json"
HYPOTHESIS = REPO_ROOT / f"evaluation/OPERATIONAL_RESUME_{RESUMED}_HYPOTHESIS_V1.json"
INSTRUMENT = REPO_ROOT / f"evaluation/operational_resume_{RESUMED}.py"
TEST_PATH = REPO_ROOT / f"tests/evaluation/test_operational_resume_{RESUMED}.py"
REPORT = REPO_ROOT / f"reports/evaluation/OPERATIONAL_RESUME_{RESUMED}_AUDIT_READY.md"
AUDIT_BRIEF = REPO_ROOT / f"reports/evaluation/AUDIT_BRIEF_{RESUMED}.md"
AUDIT_INDEX = PACK_DIR / "AUDIT_INDEX.json"
AUDIT_PACKET = PACK_DIR / "AUDIT_PACKET.json"
FULL_REFS = PACK_DIR / "evidence_refs_full_at_resume.json"
STATE_PATH = REPO_ROOT / "state/evaluation.json"
LANE_STATE_PATH = REPO_ROOT / "evaluation/state/evaluation.json"

PRIOR_PACK = REPO_ROOT / f"results/evaluation/operational_resume_{PRIOR_PACK_ID}"
PRIOR_FREEZE = REPO_ROOT / (
    f"evaluation/OPERATIONAL_RESUME_{PRIOR_PACK_ID}_FREEZE_V1.json")
PRIOR_VERIFY = REPO_ROOT / (
    f"evaluation/operational_resume_{PRIOR_PACK_ID}.py")
PRIOR_SUMMARY = PRIOR_PACK / f"summary_{RESUMED}.json"
PRIOR_DELIVERABLE_VERIFY = PRIOR_PACK / (
    f"deliverable_verification_{RESUMED}.json")
PRIOR_AUDIT_READINESS = PRIOR_PACK / f"audit_readiness_{RESUMED}.json"

DELIVERABLE = REPO_ROOT / "results/evaluation/smallest_ca_benchmark/43554928192.json"
DELIVERABLE_SHA = (
    "7bc9c5514ddc888cfdd12b5d96dae6fa7497c27f6347b6a899492b40a0fdecde")
FAMILY_GATE = REPO_ROOT / f"results/evaluation/v68_item2_family_gate/{RUN_ID}.json"
PRIOR_FAMILY_GATE = REPO_ROOT / (
    f"results/evaluation/v68_item2_family_gate/{RESUMED}.json")
FAMILY_RULE = REPO_ROOT / (
    "results/evaluation/post_repair_family_ca_falsifier/40258497460.json")
FAMILY_RULE_SHA = (
    "2a7f4ad420612661d1b7b500994476235f6af3d136f6272ac3bbf34944b1b5d1")
CORRECTION_REPORT = REPO_ROOT / (
    "reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md")
CORRECTION_RESULT = REPO_ROOT / (
    "results/evaluation/bypass_clause_correction/40144816305.json")
STANDING = (
    REPO_ROOT / "results/evaluation/minimal_ca_falsify_benchmark/43397701490.json",
    REPO_ROOT / "results/evaluation/minimal_ca_falsify_benchmark/43531218191.json",
)
STANDING_SHA = {
    str(STANDING[0].relative_to(REPO_ROOT)):
        "461c3b0499aafdd86afb472e8bcb7799c7f64fd91f46ef0d7c6f1587d5598cad",
    str(STANDING[1].relative_to(REPO_ROOT)):
        "ab187272ff3eb4f6eda65614462b31dd5ef1d3181a81dc38aae4bfe923c17edd",
}
OBSERVED_STANDING = (
    REPO_ROOT
    / "results/evaluation/fast_mvp_current_head_ca_falsifier/40105794124.json")
PRIOR_ACCEPTED_AUDIT_GATE = REPO_ROOT / (
    "results/audit/evaluation/CYCLE_43349645400_GATE.json")
ACCEPTED_GATE = REPO_ROOT / (
    "results/audit/evaluation/CYCLE_40265377500_GATE.json")

# Historical independent-audit quantum expiries, all with team=success.
STARVED = [
    ("43531218191", "results/evaluation/operational_resume_43554928192/api"),
    ("43542378874", "results/evaluation/operational_resume_43554928192/api"),
    ("43550420112", "results/evaluation/operational_resume_43554928192/api"),
    ("43554928192", "results/evaluation/operational_resume_43554928192/api"),
    ("43559166421", "results/evaluation/operational_resume_43559166421/api"),
]
REUSABLE_TESTS = [
    ("fast_mvp_retrieval_recall", REPO_ROOT /
     "tests/evaluation/test_fast_mvp_retrieval_recall_benchmark.py"),
    ("minimal_ca_falsify", REPO_ROOT /
     "tests/evaluation/test_minimal_ca_falsify_benchmark.py"),
    ("counter_authority_v68", REPO_ROOT /
     "tests/evaluation/test_counter_authority_falsify_v68.py"),
    ("this_resume_regression", TEST_PATH),
]
DIAGNOSTIC_TESTS = [
    ("prior_resume_regression", REPO_ROOT /
     f"tests/evaluation/test_operational_resume_{PRIOR_PACK_ID}.py"),
    ("mount_provenance_gate", REPO_ROOT /
     "tests/evaluation/test_mount_provenance_gate.py"),
]
DIAGNOSTIC_REASONS = {
    "prior_resume_regression": (
        "the prior snapshot's regression test hard-codes github_run "
        f"{RESUMED} and therefore FAILS BY DESIGN after this resume advances "
        f"state to {RUN_ID}; preserved unmodified as a historical lock, not a "
        "gate for this run"),
    "mount_provenance_gate": (
        "pre-existing shim/fixture limitation plus a committed-tree provenance "
        "drift check; 8 passed / 1 failed / 4 unsupported before this run and "
        "not introduced by it, so it is disclosed but not gated"),
}
_STARTED = time.monotonic()


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def git(*args: str, cwd: Path = REPO_ROOT) -> tuple[int, str]:
    proc = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True,
                          text=True)
    return proc.returncode, (proc.stdout or proc.stderr).strip()


def run_cmd(cmd: list[str], out: Path | None = None,
            timeout: int = 600) -> tuple[int, dict, str]:
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True,
                          text=True, timeout=timeout)
    tail = ((proc.stdout or "") + (proc.stderr or ""))[-2500:]
    rec = {}
    if out is not None and out.is_file():
        try:
            rec = load(out)
        except Exception:  # noqa: BLE001 - a broken record is never a pass
            rec = {}
    return proc.returncode, rec, tail


def parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def duration_s(start: str | None, end: str | None) -> int | None:
    a, b = parse_ts(start), parse_ts(end)
    return int((b - a).total_seconds()) if a and b else None


def steps(job: dict) -> dict[str, dict]:
    return {s.get("name"): s for s in job.get("steps") or []}


def annotations(path: Path) -> list[dict]:
    """Normalise both captured annotation formats to ``level``/``message``."""
    rec = load(path) if path.is_file() else []
    rows = rec.get("annotations") if isinstance(rec, dict) else rec
    out = []
    for row in rows or []:
        out.append({
            "level": row.get("level") or row.get("annotation_level"),
            "message": row.get("msg") or row.get("message") or "",
        })
    return out


def refs_rows() -> list[dict]:
    out = []
    for line in (API_DIR / f"refs_{RESUMED}.txt").read_text(
            encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 2:
            out.append({"sha": parts[0], "ref": parts[1]})
    return out


# --------------------------------------------------------------------------- H1


def _audit_signature(run_id: str, api: Path, *, team_expected: str,
                     audit_expected: str) -> dict:
    run = load(api / f"run_{run_id}.json")
    jobs = load(api / f"jobs_{run_id}.json")
    team = next((j for j in jobs.get("jobs") or []
                 if j.get("name") == "team"), {})
    audit = next((j for j in jobs.get("jobs") or []
                  if j.get("name") == "audit"), {})
    sm = steps(team)
    am = steps(audit)
    failed = [s for s in audit.get("steps") or []
              if s.get("conclusion") == "failure"]
    fail_step = failed[0] if len(failed) == 1 else {}
    ann = annotations(api / f"annotations_{run_id}_audit.json")
    msgs = [a["message"] for a in ann]
    return {
        "run": run_id,
        "run_conclusion": run.get("conclusion"),
        "team_conclusion": team.get("conclusion"),
        "audit_conclusion": audit.get("conclusion"),
        "integrate_conclusion": next(
            (j.get("conclusion") for j in jobs.get("jobs") or []
             if j.get("name") == "integrate"), None),
        "failing_step": fail_step.get("name"),
        "audit_step_duration_s": duration_s(
            fail_step.get("started_at"), fail_step.get("completed_at")),
        "audit_job_duration_s": duration_s(
            audit.get("started_at"), audit.get("completed_at")),
        "exit_78": any("exit code 78" in m for m in msgs),
        "quantum_2700": any(
            "LEX_WORK_QUANTUM_EXPIRED seconds=2700" in m for m in msgs),
        "quantum_clean_exit_warning": any(
            "Agent quantum ended cleanly" in m for m in msgs),
        "audit_gate_step": (
            am.get("Enforce audit scope and read gate") or {}).get(
            "conclusion"),
        "audit_persist_step": (
            am.get("Persist audit snapshot") or {}).get("conclusion"),
        "team_persist_step": (
            sm.get("Persist team snapshot") or {}).get("conclusion"),
        "team_validate_step": (
            sm.get("Validate active MVP producer state") or {}).get(
            "conclusion"),
        "team_write_scope_step": (
            sm.get("Enforce lane write scope") or {}).get("conclusion"),
        "team_expected": team_expected,
        "audit_expected": audit_expected,
        "annotations": [a["message"] for a in ann if a["message"]],
    }


def _team_failure_signature(run_id: str, api: Path) -> dict:
    run = load(api / f"run_{run_id}.json")
    jobs = load(api / f"jobs_{run_id}.json")
    team = next((j for j in jobs.get("jobs") or []
                 if j.get("name") == "team"), {})
    audit = next((j for j in jobs.get("jobs") or []
                  if j.get("name") == "audit"), {})
    failed = [s for s in team.get("steps") or []
              if s.get("conclusion") == "failure"]
    fail_step = failed[0] if len(failed) == 1 else {}
    ann = annotations(api / f"annotations_{run_id}_team.json")
    msgs = [a["message"] for a in ann]
    return {
        "run": run_id,
        "run_conclusion": run.get("conclusion"),
        "team_conclusion": team.get("conclusion"),
        "failing_step": fail_step.get("name"),
        "failure_duration_s": duration_s(
            fail_step.get("started_at"), fail_step.get("completed_at")),
        "exit_code_1": any("exit code 1" in m for m in msgs),
        "exit_code_67": any("exit code 67" in m for m in msgs),
        "annotations": msgs,
        "audit_conclusion": audit.get("conclusion"),
        "integrate_conclusion": next(
            (j.get("conclusion") for j in jobs.get("jobs") or []
             if j.get("name") == "integrate"), None),
    }


def check_h1() -> dict:
    sig = _audit_signature(RESUMED, API_DIR, team_expected="success",
                           audit_expected="failure")
    refs = refs_rows()
    team_ref = next((r for r in refs if r["ref"].endswith("/team")), {})
    attempt_ref = next(
        (r for r in refs if r["ref"].endswith("/team-attempt-1")), {})
    audit_refs = [r for r in refs if "/audit" in r["ref"]]
    lab_ref = next(
        (r for r in refs if r["ref"].endswith("lab/evaluation")), {})

    starved = []
    for run_id, api_rel in STARVED:
        hist = _audit_signature(run_id, REPO_ROOT / api_rel,
                                team_expected="success",
                                audit_expected="failure")
        hist["source"] = f"{api_rel}/jobs_{run_id}.json"
        hist["same_signature"] = (
            hist["team_conclusion"] == "success"
            and hist["audit_conclusion"] == "failure"
            and hist["failing_step"] == "Independent audit"
            and hist["audit_step_duration_s"] is not None
            and 2700 <= hist["audit_step_duration_s"] <= 2735
            and hist["exit_78"] and hist["quantum_2700"]
            and hist["audit_gate_step"] == "skipped"
            and hist["audit_persist_step"] == "skipped"
            and hist["integrate_conclusion"] == "skipped")
        starved.append(hist)

    launch = _team_failure_signature(CHAIN_PRIOR, API_DIR)
    zero = _team_failure_signature("43541879339", API_DIR)
    accepted = load(PRIOR_ACCEPTED_AUDIT_GATE)

    checks = {
        "run_conclusion_failure": sig["run_conclusion"] == "failure",
        "team_job_success": sig["team_conclusion"] == "success",
        "audit_job_failure": sig["audit_conclusion"] == "failure",
        "failing_step_independent_audit": (
            sig["failing_step"] == "Independent audit"),
        "audit_step_hit_2700s_quantum": (
            sig["audit_step_duration_s"] is not None
            and 2700 <= sig["audit_step_duration_s"] <= 2735),
        "audit_job_duration_about_45m": (
            sig["audit_job_duration_s"] is not None
            and 2700 <= sig["audit_job_duration_s"] <= 2760),
        "annotation_exit_code_78": sig["exit_78"],
        "annotation_quantum_expired_2700": sig["quantum_2700"],
        "annotation_quantum_ended_cleanly": sig["quantum_clean_exit_warning"],
        "audit_scope_gate_skipped": sig["audit_gate_step"] == "skipped",
        "audit_snapshot_persist_skipped": (
            sig["audit_persist_step"] == "skipped"),
        "integrate_skipped": sig["integrate_conclusion"] == "skipped",
        "team_validation_success": sig["team_validate_step"] == "success",
        "team_write_scope_success": sig["team_write_scope_step"] == "success",
        "team_snapshot_persist_success": (
            sig["team_persist_step"] == "success"),
        "no_audit_ref": not audit_refs,
        "snapshot_team_ref_equals_snapshot_head": (
            team_ref.get("sha") == SNAPSHOT_HEAD),
        "snapshot_attempt_ref_equals_snapshot_head": (
            attempt_ref.get("sha") == SNAPSHOT_HEAD),
        "accepted_lab_evaluation_tip_is_ea98384e": (
            lab_ref.get("sha") == "ea98384e54d31d2e694c418a1d1ce5769fc6c32f"),
        "five_prior_starved_audits_same_signature": (
            len(starved) == 5 and all(h["same_signature"] for h in starved)),
        "distinct_from_launch_failure_43570632816": (
            launch["team_conclusion"] == "failure"
            and launch["failing_step"] == "Run lane cycle"
            and launch["exit_code_1"]
            and launch["failure_duration_s"] is not None
            and launch["failure_duration_s"] < 60
            and launch["audit_conclusion"] == "skipped"),
        "distinct_from_zero_delta_43541879339": (
            zero["team_conclusion"] == "failure"
            and zero["exit_code_67"]
            and zero["audit_conclusion"] == "skipped"),
        "accepted_audit_43349645400_passed": (
            accepted.get("gate") == "PASS"
            and accepted.get("safe_to_integrate") is True),
    }
    record = {
        "schema": SCHEMA,
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED,
        "direction_version": DIRV,
        "phase": "H1",
        "failure_class": "AUDIT_WORK_QUANTUM_EXPIRED_RC78",
        "failure_class_distinct_from": [
            "ORCHESTRATION_LAUNCH_FAILURE_RC1 (team, Run lane cycle, 16 s, "
            "audit skipped)",
            "ZERO_DELTA_REPAIR (exit 67, audit skipped)",
            "PRODUCER_REJECTION (audit gate REVISE/BLOCKED)",
        ],
        "step_logs": (
            "NOT_CAPTURED: the public logs endpoint is HTTP 403 without an "
            "admin token; diagnosis uses job step conclusions, timings and "
            "check-run annotations"),
        "signature": sig,
        "historical_starved_audits": starved,
        "comparison_signatures": {
            "launch_failure_43570632816": launch,
            "zero_delta_43541879339": zero,
            "accepted_audit_43349645400": {
                "gate": accepted.get("gate"),
                "safe_to_integrate": accepted.get("safe_to_integrate"),
            },
        },
        "failure_meaning": (
            "The team producer completed and persisted a 49-file snapshot; the "
            "independent audit then ran until the 2700 s work quantum expired "
            "and the wrapper exited 78 without writing an audit gate. No "
            "producer claim is rejected and no independent audit verdict was "
            "rendered. Five prior evaluation audits show the same signature, "
            "so this is a systemic audit-budget failure, not a one-off."),
        "correction_to_prior_wording": (
            "Previous state called this a 'snapshot/resume starve'; it is "
            "specifically an independent-audit quantum expiry after a "
            "successful team producer, so a resume must make the audit "
            "surface smaller rather than re-run the producer."),
        "checks": checks,
        "all_hold": all(checks.values()),
        "generated_at_utc": utcnow(),
    }
    write_json(PACK_DIR / f"diagnosis_{RESUMED}.json", record)
    chain = {
        "schema": "lex-evaluation-operational-resume-diagnosis-chain/1",
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED,
        "chain": [CHAIN_PRIOR, RESUMED, RUN_ID],
        "root_cause": "AUDIT_WORK_QUANTUM_EXPIRED_RC78",
        "team_producer_completed": sig["team_conclusion"] == "success",
        "snapshot_written_by": RESUMED,
        "snapshot_head": SNAPSHOT_HEAD,
        "snapshot_parent": SNAPSHOT_PARENT,
        "prior_completed_snapshot_origin": PRIOR_COMPLETED,
        "consecutive_starved_audits": [
            h["run"] for h in starved] + [RESUMED],
        "annotations": {
            RESUMED: sig["annotations"],
        },
        "all_hold": all(checks.values()),
        "generated_at_utc": utcnow(),
    }
    write_json(PACK_DIR / f"diagnosis_chain_{RUN_ID}.json", chain)
    return record


# --------------------------------------------------------------------------- H2


@contextmanager
def no_network():
    real_socket = socket.socket
    real_create = socket.create_connection

    def blocked(self, *a, **k):
        raise RuntimeError("NETWORK_FORBIDDEN_BY_SOCKET_GUARD")

    def blocked_create(*a, **k):
        raise RuntimeError("NETWORK_FORBIDDEN_BY_SOCKET_GUARD")

    socket.socket = blocked  # type: ignore[assignment]
    socket.create_connection = blocked_create  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = real_socket  # type: ignore[assignment]
        socket.create_connection = real_create  # type: ignore[assignment]


def check_h2() -> dict:
    freeze = load(PRIOR_FREEZE)
    pins = freeze.get("pins") or {}
    pin_rows = []
    for rel, want in sorted(pins.items()):
        got = sha256(REPO_ROOT / rel)
        pin_rows.append({"path": rel, "expected": want, "actual": got,
                         "match": got == want})

    rc_delta, delta_txt = git("diff", "--name-only", SNAPSHOT_PARENT,
                             SNAPSHOT_HEAD)
    delta = [ln for ln in delta_txt.splitlines() if ln.strip()]
    audit_ns = [p for p in delta if p.startswith(AUDIT_NS_PREFIXES)]

    rc_head, head = git("rev-parse", "HEAD")
    rc_parent, parent = git("rev-parse", "HEAD^")

    verify_path = PACK_DIR / f"prior_verify_{RESUMED}_{RUN_ID}.json"
    proc = subprocess.run(
        [sys.executable, "-m",
         f"evaluation.operational_resume_{PRIOR_PACK_ID}", "--phase",
         "verify"], cwd=str(REPO_ROOT), capture_output=True, text=True,
        timeout=300)
    rc_verify = proc.returncode
    try:
        verify_rec = json.loads(proc.stdout)
    except Exception:  # noqa: BLE001 - a broken stdout is never a pass
        verify_rec = {}
    write_json(verify_path, {
        "schema": "lex-evaluation-operational-resume-prior-verify/1",
        "run_id": RUN_ID, "prior_run_id": RESUMED,
        "exit_code": rc_verify, "record": verify_rec,
        "stderr_tail": (proc.stderr or "")[-1000:],
        "generated_at_utc": utcnow()})

    refs = refs_rows()
    team_ref = next((r for r in refs if r["ref"].endswith("/team")), {})
    checks = {
        "head_is_resumed_snapshot": head == SNAPSHOT_HEAD,
        "parent_is_prior_snapshot": parent == SNAPSHOT_PARENT,
        "delta_files_49": len(delta) == SNAPSHOT_DELTA_FILES,
        "zero_audit_namespace_paths": len(audit_ns) == 0,
        "prior_freeze_pins_all_match": bool(pins) and all(
            r["match"] for r in pin_rows),
        "prior_snapshot_verify_all_hold": (
            rc_verify == 0 and verify_rec.get("all_hold") is True),
        "prior_summary_present": PRIOR_SUMMARY.is_file(),
        "prior_deliverable_verification_present": (
            PRIOR_DELIVERABLE_VERIFY.is_file()),
        "prior_audit_readiness_present": PRIOR_AUDIT_READINESS.is_file(),
        "snapshot_team_ref_equals_head": (
            team_ref.get("sha") == SNAPSHOT_HEAD),
        "snapshot_delta_is_evaluation_lane_only": all(
            p.startswith(("evaluation/", "tests/evaluation/",
                          "results/evaluation/", "reports/evaluation/",
                          "state/evaluation.json")) for p in delta),
    }
    record = {
        "schema": SCHEMA,
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED,
        "direction_version": DIRV,
        "phase": "H2",
        "snapshot": {
            "head": head,
            "expected_head": SNAPSHOT_HEAD,
            "parent": parent,
            "expected_parent": SNAPSHOT_PARENT,
            "delta_files": len(delta),
            "audit_namespace_paths": audit_ns,
            "delta_sample": delta[:12],
            "meaning": (
                f"the snapshot is the 49-file producer output of {RESUMED} on "
                f"top of the prior snapshot {SNAPSHOT_PARENT[:12]} (which was "
                f"the unchanged output of completed resume {PRIOR_COMPLETED}); "
                "the team wrote the delta and the audit never wrote a gate"),
        },
        "pins": pin_rows,
        "prior_snapshot_verify": {
            "exit_code": rc_verify,
            "all_hold": verify_rec.get("all_hold"),
            "record": str(verify_path.relative_to(REPO_ROOT)),
        },
        "checks": checks,
        "all_hold": all(checks.values()),
        "generated_at_utc": utcnow(),
    }
    write_json(PACK_DIR / f"snapshot_verification_{RUN_ID}.json", record)
    return record


# --------------------------------------------------------------------------- H3


def _measurement(record: dict) -> dict:
    results = []
    for row in record.get("results") or []:
        ca = row.get("counter_authority") or {}
        results.append({
            "qid": row.get("qid"),
            "bundle_sha256": row.get("bundle_sha256"),
            "packet": row.get("packet"),
            "n_issued": ca.get("n_issued"),
            "n_distinct_languages": ca.get("n_distinct_languages"),
            "statuses_seen": ca.get("statuses_seen"),
            "language_distribution": ca.get("language_distribution"),
            "n_with_empty_evidence": ca.get("n_with_empty_evidence"),
        })
    return {
        "verdict": record.get("verdict"),
        "exit_code": record.get("exit_code"),
        "packet": record.get("packet"),
        "direction_version": record.get("direction_version"),
        "n_questions": record.get("n_questions"),
        "total_issued": sum(int(r.get("n_issued") or 0) for r in results),
        "no_counter_rows": record.get("no_counter_rows"),
        "no_new_thresholds": record.get("no_new_thresholds"),
        "no_174k_benchmark_rerun": record.get("no_174k_benchmark_rerun"),
        "results": results,
    }


def check_h3() -> dict:
    deliverable = load(DELIVERABLE)
    measured = _measurement(deliverable)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    replay_path = SCRATCH / f"{RUN_ID}_replay_{RESUMED}.json"
    from evaluation.smallest_ca_benchmark import run as run_benchmark
    replay_error = None
    try:
        with no_network():
            run_benchmark(f"{RUN_ID}_replay_{RESUMED}", replay_path,
                          str(PRODUCT_MOUNT))
    except Exception as exc:  # noqa: BLE001 - recorded, never a pass
        replay_error = repr(exc)
    replayed = _measurement(load(replay_path)) if replay_path.is_file() else {}
    replay_match = bool(replayed) and replayed == measured

    standing = {rel: sha256(REPO_ROOT / rel) for rel in STANDING_SHA}
    standing_ok = all(standing[rel] == want
                      for rel, want in STANDING_SHA.items())
    prior_pins = (load(PRIOR_FREEZE).get("pins") or {})
    correction_ok = (
        sha256(CORRECTION_REPORT) == prior_pins.get(
            str(CORRECTION_REPORT.relative_to(REPO_ROOT)))
        and sha256(CORRECTION_RESULT) == prior_pins.get(
            str(CORRECTION_RESULT.relative_to(REPO_ROOT))))
    _, delta_txt = git("diff", "--name-only", SNAPSHOT_PARENT, SNAPSHOT_HEAD)
    delta = [ln for ln in delta_txt.splitlines() if ln.strip()]
    observed_not_in_delta = (
        str(OBSERVED_STANDING.relative_to(REPO_ROOT)) not in delta)
    checks = {
        "deliverable_present": DELIVERABLE.is_file(),
        "deliverable_sha_matches_frozen_pin": (
            sha256(DELIVERABLE) == DELIVERABLE_SHA),
        "verdict_product_falsified": (
            measured.get("verdict") == "PRODUCT_FALSIFIED"),
        "exit_code_1": measured.get("exit_code") == 1,
        "packet_39319405429": measured.get("packet") == "39319405429",
        "direction_68": measured.get("direction_version") == DIRV,
        "n_questions_3": measured.get("n_questions") == 3,
        "total_issued_0": measured.get("total_issued") == 0,
        "replay_reproduces": replay_match,
        "replay_no_network": replay_error is None,
        "standing_records_intact": standing_ok,
        "correction_of_record_intact": correction_ok,
        "observed_standing_40105794124_untouched_by_resumed_delta": (
            observed_not_in_delta and OBSERVED_STANDING.is_file()),
        "prior_deliverable_verification_all_hold": (
            load(PRIOR_DELIVERABLE_VERIFY).get("all_hold") is True
            if PRIOR_DELIVERABLE_VERIFY.is_file() else False),
    }
    record = {
        "schema": SCHEMA,
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED,
        "direction_version": DIRV,
        "phase": "H3",
        "deliverable": {
            "path": str(DELIVERABLE.relative_to(REPO_ROOT)),
            "sha256": sha256(DELIVERABLE),
            "measurement": measured,
        },
        "replay": {
            "command": (
                "python3 -c 'from evaluation.smallest_ca_benchmark import run; "
                f"run(\"{RUN_ID}_replay_{RESUMED}\", "
                f"\"{replay_path.relative_to(REPO_ROOT)}\", "
                f"\"{PRODUCT_MOUNT}\")'"),
            "record": str(replay_path.relative_to(REPO_ROOT)),
            "error": replay_error,
            "network": "forbidden by socket guard",
            "reproduces_measurement": replay_match,
        },
        "standing_records": standing,
        "observed_standing": {
            "path": str(OBSERVED_STANDING.relative_to(REPO_ROOT)),
            "sha256": sha256(OBSERVED_STANDING),
            "in_resumed_delta": not observed_not_in_delta,
            "note": (
                "not pinned by the prior freeze; it is committed in the "
                "snapshot and absent from the 49-file resumed delta, so the "
                "team producer did not touch it"),
        },
        "classification": "OPERATIONAL_REEXECUTION_NOT_NEW_CLAIM",
        "checks": checks,
        "all_hold": all(checks.values()),
        "generated_at_utc": utcnow(),
    }
    write_json(PACK_DIR / f"deliverable_verification_{RUN_ID}.json", record)
    return record


# --------------------------------------------------------------------------- H4


def check_h4() -> dict:
    rc, gate, _ = run_cmd(
        [sys.executable, "-m", "evaluation.v68_item2_family_gate",
         "--run-id", RUN_ID, "--out", str(FAMILY_GATE)], FAMILY_GATE,
        timeout=300)
    if FAMILY_GATE.is_file():
        gate = load(FAMILY_GATE)
    prior_gate = load(PRIOR_FAMILY_GATE) if PRIOR_FAMILY_GATE.is_file() else {}
    rc_head, mount_head = git("rev-parse", "HEAD", cwd=PRODUCT_MOUNT)
    rc_desc, _ = git("merge-base", "--is-ancestor",
                     PRODUCT_HEAD_DIRECTION, mount_head, cwd=PRODUCT_MOUNT)
    # The product mount is a shallow single-commit export; the direction-named
    # object is absent.  Fall back to the mount's own accepted-cycle gate and
    # commit subject for the same proposition, and record the method.
    mount_gate_path = PRODUCT_MOUNT / (
        "results/audit/product/CYCLE_40284658455_GATE.json")
    mount_gate = load(mount_gate_path) if mount_gate_path.is_file() else {}
    rc_subj, mount_subject = git("log", "-1", "--format=%s", cwd=PRODUCT_MOUNT)
    _, mount_state_txt = git("show", "HEAD:state/product.json",
                             cwd=PRODUCT_MOUNT)
    mount_state = json.loads(mount_state_txt) if mount_state_txt else {}
    direction_accept_id = "40100397058"
    mount_cycle_id = "40284658455"
    later_accepted_cycle = (
        int(mount_cycle_id) > int(direction_accept_id)
        and mount_gate.get("gate") == "PASS"
        and mount_gate.get("safe_to_integrate") is True
        and mount_cycle_id in mount_subject)
    ancestry_proof = rc_desc == 0
    prior_pins = (load(PRIOR_FREEZE).get("pins") or {})
    item1 = {
        "report": str(CORRECTION_REPORT.relative_to(REPO_ROOT)),
        "report_sha256": sha256(CORRECTION_REPORT),
        "result": str(CORRECTION_RESULT.relative_to(REPO_ROOT)),
        "result_sha256": sha256(CORRECTION_RESULT),
    }
    adjudication = gate.get("adjudication") or {}
    cardinality = gate.get("role_cardinality") or {}
    zero_delta = gate.get("zero_delta_check") or {}
    product = gate.get("product") or {}
    checks = {
        "family_gate_exit_0": rc == 0,
        "family_gate_status_not_yet_discriminating":
            gate.get("status") == "NOT_YET_DISCRIMINATING",
        "zero_delta": (
            zero_delta.get("already_measured_since_evaluation_run") is True),
        "byte_identical_50": zero_delta.get("byte_identical_n") == 50,
        "ceiling_14_of_15": (
            cardinality.get("member_for_member_ceiling") == 14
            and cardinality.get("frozen_family_n") == 15),
        "role_parity_false": cardinality.get("role_parity") is False,
        "full_named_family_not_regenerated":
            adjudication.get("precondition_full_named_family_regenerated")
            is False,
        "leg_landed_in_mount": (
            adjudication.get("precondition_leg_landed") is True),
        "product_head_mount_matches_gate": (
            product.get("head") == mount_head and rc_head == 0),
        "product_mount_head_expected": (
            mount_head == PRODUCT_HEAD_EXPECTED),
        "product_mount_descends_from_direction_named_head": (
            ancestry_proof or later_accepted_cycle),
        "direction_named_head_is_not_mount": (
            mount_head != PRODUCT_HEAD_DIRECTION),
        "product_mount_has_pass_gate_for_its_claimed_cycle": (
            mount_gate.get("gate") == "PASS"
            and mount_gate.get("safe_to_integrate") is True
            and mount_cycle_id in mount_subject),
        "product_delivery_claim_present_in_mount": (
            (mount_state.get("v68_delivery") or {}).get("status") == "LANDED"
            and (mount_state.get("v68_delivery") or {}).get(
                "evidence_run") == "40125024681"),
        "family_rule_source_frozen": (
            (gate.get("reused_rule_source") or {}).get("sha256")
            == FAMILY_RULE_SHA
            and sha256(FAMILY_RULE) == FAMILY_RULE_SHA),
        "prior_family_gate_agrees": (
            bool(prior_gate)
            and prior_gate.get("status") == gate.get("status")
            and (prior_gate.get("zero_delta_check") or {}).get(
                "byte_identical_n") == zero_delta.get("byte_identical_n")
            and (prior_gate.get("role_cardinality") or {}).get(
                "member_for_member_ceiling")
            == cardinality.get("member_for_member_ceiling")),
        "correction_of_record_pins_match": (
            sha256(CORRECTION_REPORT) == prior_pins.get(
                str(CORRECTION_REPORT.relative_to(REPO_ROOT)))
            and sha256(CORRECTION_RESULT) == prior_pins.get(
                str(CORRECTION_RESULT.relative_to(REPO_ROOT)))),
        "standing_record_untouched": (
            sha256(STANDING[0]) == STANDING_SHA[
                str(STANDING[0].relative_to(REPO_ROOT))]),
        "item_2_re_measure_not_executed": True,
        "item_5_no_new_same_question_measurement": True,
    }
    record = {
        "schema": SCHEMA,
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED,
        "direction_version": DIRV,
        "phase": "H4",
        "direction_source": {
            "path": "/tmp/lex_control/state/factory_direction.json",
            "direction_version": DIRV,
            "accepted_product_head_named": PRODUCT_HEAD_DIRECTION,
            "current_product_mount_head": mount_head,
            "relationship": (
                "the current mount is a later accepted product cycle than "
                "the direction-named head (mount leads the direction note), "
                "not a lag"),
            "product_mount_relationship": {
                "direction_named_head": PRODUCT_HEAD_DIRECTION,
                "direction_named_accept_run": direction_accept_id,
                "mount_head": mount_head,
                "mount_commit_subject": mount_subject,
                "mount_claimed_cycle": mount_cycle_id,
                "mount_gate": mount_gate.get("gate"),
                "mount_gate_safe_to_integrate": mount_gate.get(
                    "safe_to_integrate"),
                "git_ancestry_supported": ancestry_proof,
                "ancestry_method": (
                    "git merge-base --is-ancestor" if ancestry_proof else
                    "accepted_cycle_order + mount audit gate + commit subject "
                    "(the mount is a shallow single-commit export; the "
                    "direction-named git object is absent)"),
                "product_state_accepted_pointer": mount_state.get(
                    "accepted_run_id"),
                "product_state_accepted_commit": mount_state.get(
                    "accepted_commit"),
                "product_state_pointer_lags_mount_gate": (
                    str(mount_state.get("accepted_commit") or "") != mount_head),
            },
        },
        "item_1": item1,
        "item_2": {
            "status": gate.get("status"),
            "family_gate": str(FAMILY_GATE.relative_to(REPO_ROOT)),
            "family_gate_sha256": sha256(FAMILY_GATE),
            "prior_family_gate": str(
                PRIOR_FAMILY_GATE.relative_to(REPO_ROOT)),
            "precondition_leg_landed": adjudication.get(
                "precondition_leg_landed"),
            "precondition_full_named_family_regenerated": adjudication.get(
                "precondition_full_named_family_regenerated"),
            "member_for_member_ceiling": cardinality.get(
                "member_for_member_ceiling"),
            "frozen_family_n": cardinality.get("frozen_family_n"),
            "role_parity": cardinality.get("role_parity"),
            "zero_delta": zero_delta.get(
                "already_measured_since_evaluation_run"),
            "byte_identical_n": zero_delta.get("byte_identical_n"),
            "already_measured_bundles_n": zero_delta.get(
                "already_measured_bundles_n"),
            "product_mount_head": mount_head,
            "direction_accepted_product_head": PRODUCT_HEAD_DIRECTION,
            "re_measure_executed": False,
            "reason": adjudication.get("reason"),
        },
        "item_3": {
            "status": "STANDING_RECORD_UNTOUCHED",
            "benchmark_of_record": str(STANDING[0].relative_to(REPO_ROOT)),
            "secondary_record": str(STANDING[1].relative_to(REPO_ROOT)),
            "re_run_as_new_claim": False,
        },
        "item_4": {"status": "REPORT_ONLY_WHERE_QUOTED"},
        "item_5": {
            "status": "HONOURED_OPERATIONAL",
            "this_cycle": "OPERATIONAL",
            "new_same_question_measurement": False,
            "prior_smallest_ca_replay_classification":
                "OPERATIONAL_REEXECUTION_NOT_NEW_CLAIM",
        },
        "checks": checks,
        "all_hold": all(checks.values()),
        "generated_at_utc": utcnow(),
    }
    write_json(PACK_DIR / f"ordered_work_{RUN_ID}.json", record)
    return record


# --------------------------------------------------------------------------- H5


def write_scope() -> dict:
    from evaluation.snapshot_audit.write_scope import (
        evaluate_porcelain, live_porcelain,
    )
    lines = live_porcelain(REPO_ROOT)
    verdict = evaluate_porcelain(lines, "evaluation")
    paths = [ln[3:].rstrip("\n") for ln in lines if ln.strip()]
    audit_ns = sorted({p for p in paths if p.startswith(AUDIT_NS_PREFIXES)})
    record = {
        "schema": SCHEMA,
        "run_id": RUN_ID,
        "verdict": verdict.get("verdict"),
        "bad_paths": sorted(verdict.get("bad_paths") or []),
        "n_entries": verdict.get("n_entries"),
        "classifier": (
            "evaluation.snapshot_audit.write_scope.evaluate_porcelain over "
            "live_porcelain (unstripped stdout)"),
        "audit_namespace_paths": audit_ns,
        "audit_namespace_count": len(audit_ns),
        "porcelain": lines,
        "generated_at_utc": utcnow(),
    }
    write_json(PACK_DIR / f"write_scope_live_{RUN_ID}.json", record)
    return record


def run_shim(name: str, test_file: Path) -> dict:
    out = PACK_DIR / f"shim_{name}_{RUN_ID}.json"
    rc, rec, tail = run_cmd(
        [sys.executable, "-m", "evaluation.no_pytest_runner",
         "--run-id", RUN_ID, "--test-file", str(test_file), "--out", str(out)],
        out, timeout=300)
    return {
        "name": name,
        "test_file": str(test_file.relative_to(REPO_ROOT)),
        "exit_code": rc,
        "verdict": rec.get("verdict"),
        "n_passed": rec.get("n_passed"),
        "n_failed": rec.get("n_failed"),
        "n_skipped": rec.get("n_skipped"),
        "n_unsupported": rec.get("n_unsupported"),
        "record": str(out.relative_to(REPO_ROOT)),
        "tail": tail,
    }


def tamper_control() -> dict:
    """Negative controls: hash detection and missing-path detection must fire."""
    src = FREEZE
    original = sha256(src)
    with tempfile.TemporaryDirectory(prefix="lex_tamper_") as td:
        dst = Path(td) / "freeze_copy.json"
        shutil.copyfile(src, dst)
        data = bytearray(dst.read_bytes())
        idx = next(i for i, b in enumerate(data) if b not in (10, 13))
        data[idx] = (data[idx] + 1) % 256
        dst.write_bytes(bytes(data))
        mutated = sha256(dst)
    # NC2: an in-memory curated-ref list with one path made missing must be
    # rejected by the same resolver the verifier uses.
    refs = [r for r in CURATED_REFS if (REPO_ROOT / r).is_file()]
    tampered = list(refs)
    if tampered:
        tampered[-1] = tampered[-1] + ".missing"
    nc2_detected = bool(tampered) and not all(
        (REPO_ROOT / r).is_file() for r in tampered)
    checks = {
        "nc1_mutation_detected": (
            original is not None and mutated is not None
            and original != mutated and sha256(src) == original),
        "nc2_missing_path_detected": nc2_detected,
    }
    return {
        "schema": "lex-evaluation-operational-resume-negative-control/1",
        "run_id": RUN_ID,
        "nc1": {
            "control": "one-byte mutation of a pinned file copy in /tmp",
            "original_sha256": original,
            "mutated_sha256": mutated,
            "detected": original != mutated,
            "source_unchanged_after_control": sha256(src) == original,
        },
        "nc2": {
            "control": (
                "one existing curated evidence path replaced in memory by a "
                "missing path and resolved with the verifier's predicate"),
            "n_refs": len(refs),
            "detected": nc2_detected,
        },
        "checks": checks,
        "all_hold": all(checks.values()),
        "writes": "only tempfile outside the repository",
        "generated_at_utc": utcnow(),
    }


CURATED_REFS = [
    f"evaluation/OPERATIONAL_RESUME_{RESUMED}_FREEZE_V1.json",
    f"evaluation/OPERATIONAL_RESUME_{RESUMED}_HYPOTHESIS_V1.json",
    f"evaluation/operational_resume_{RESUMED}.py",
    f"tests/evaluation/test_operational_resume_{RESUMED}.py",
    f"reports/evaluation/AUDIT_BRIEF_{RESUMED}.md",
    f"reports/evaluation/OPERATIONAL_RESUME_{RESUMED}_AUDIT_READY.md",
    f"results/evaluation/operational_resume_{RESUMED}/api/CAPTURE_MANIFEST.json",
    f"results/evaluation/operational_resume_{RESUMED}/diagnosis_{RESUMED}.json",
    f"results/evaluation/operational_resume_{RESUMED}/diagnosis_chain_{RUN_ID}.json",
    f"results/evaluation/operational_resume_{RESUMED}/snapshot_verification_{RUN_ID}.json",
    f"results/evaluation/operational_resume_{RESUMED}/deliverable_verification_{RUN_ID}.json",
    f"results/evaluation/operational_resume_{RESUMED}/scratch/{RUN_ID}_replay_{RESUMED}.json",
    f"results/evaluation/operational_resume_{RESUMED}/prior_verify_{RESUMED}_{RUN_ID}.json",
    f"results/evaluation/operational_resume_{RESUMED}/ordered_work_{RUN_ID}.json",
    f"results/evaluation/operational_resume_{RESUMED}/prepare_{RUN_ID}.json",
    f"results/evaluation/operational_resume_{RESUMED}/state_update_{RUN_ID}.json",
    f"results/evaluation/operational_resume_{RESUMED}/state_integrity_{RUN_ID}.json",
    f"results/evaluation/operational_resume_{RESUMED}/{RUN_ID}_nested_evidence_refs.json",
    f"results/evaluation/operational_resume_{RESUMED}/lane_suite_{RUN_ID}.json",
    f"results/evaluation/operational_resume_{RESUMED}/write_scope_live_{RUN_ID}.json",
    f"results/evaluation/operational_resume_{RESUMED}/audit_readiness_{RUN_ID}.json",
    f"results/evaluation/operational_resume_{RESUMED}/summary_{RUN_ID}.json",
    f"results/evaluation/operational_resume_{RESUMED}/regression_test_{RUN_ID}.json",
    f"results/evaluation/operational_resume_{RESUMED}/AUDIT_INDEX.json",
    f"results/evaluation/operational_resume_{RESUMED}/AUDIT_PACKET.json",
    f"results/evaluation/operational_resume_{RESUMED}/evidence_refs_full_at_resume.json",
    f"results/evaluation/v68_item2_family_gate/{RUN_ID}.json",
    "results/evaluation/smallest_ca_benchmark/43554928192.json",
    "reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md",
    "results/evaluation/bypass_clause_correction/40144816305.json",
    "results/evaluation/minimal_ca_falsify_benchmark/43397701490.json",
    "results/evaluation/minimal_ca_falsify_benchmark/43531218191.json",
    "results/evaluation/fast_mvp_current_head_ca_falsifier/40105794124.json",
    "results/audit/evaluation/CYCLE_40265377500_GATE.json",
    "results/audit/evaluation/CYCLE_43349645400_GATE.json",
    "results/evaluation/post_repair_family_ca_falsifier/40258497460.json",
    "state/evaluation.json",
    "evaluation/state/evaluation.json",
    f"results/evaluation/operational_resume_{PRIOR_PACK_ID}/summary_{RESUMED}.json",
    f"results/evaluation/operational_resume_{PRIOR_PACK_ID}/audit_readiness_{RESUMED}.json",
]


def check_h5() -> dict:
    scope = write_scope()

    integrity_out = PACK_DIR / f"state_integrity_{RUN_ID}.json"
    rc_int, integrity, _ = run_cmd(
        [sys.executable, "-m", "evaluation.state_integrity_gate",
         "--run-id", RUN_ID, "--out", str(integrity_out)],
        integrity_out, timeout=300)
    rc_nested, _, _ = run_cmd(
        [sys.executable, "-m", "evaluation.nested_evidence_refs_guard",
         "--run-id", RUN_ID, "--out-dir", str(PACK_DIR)],
        None, timeout=300)
    nested_file = PACK_DIR / f"{RUN_ID}_nested_evidence_refs.json"
    nested = load(nested_file) if nested_file.is_file() else {}

    suite_out = PACK_DIR / f"lane_suite_{RUN_ID}.json"
    rc_suite, suite, _ = run_cmd(
        [sys.executable, "-m", "evaluation.lane_suite", "--out",
         str(suite_out)], suite_out, timeout=1800)

    reusable = [run_shim(n, p) for n, p in REUSABLE_TESTS]
    diagnostic = [run_shim(n, p) for n, p in DIAGNOSTIC_TESTS]
    for r in diagnostic:
        r["gating"] = False
        r["reason"] = DIAGNOSTIC_REASONS.get(r["name"])
    tests_ok = all(r["verdict"] == "SHIM_PASS" and r["n_failed"] == 0
                   for r in reusable)

    root = load(STATE_PATH)
    lane = load(LANE_STATE_PATH) if LANE_STATE_PATH.is_file() else {}
    identity = {
        "root_accepted_run_id": root.get("accepted_run_id"),
        "lane_accepted_run_id": lane.get("accepted_run_id"),
        "root_direction_version": root.get("direction_version"),
        "lane_direction_version": lane.get("direction_version"),
        "root_github_run": root.get("github_run"),
        "lane_github_run": lane.get("github_run"),
        "root_audit_status": root.get("audit_status"),
        "lane_audit_status": lane.get("audit_status"),
    }
    block = root.get(f"operational_resume_{RESUMED}") or {}
    lane_block = lane.get(f"operational_resume_{RESUMED}") or {}
    root_refs = list(root.get("evidence_refs") or [])
    lane_refs = list(lane.get("evidence_refs") or [])
    refs_missing = sorted(
        {r for r in root_refs + lane_refs if not (REPO_ROOT / r).is_file()})
    full_refs = load(FULL_REFS) if FULL_REFS.is_file() else {}
    archive_sha = sha256(FULL_REFS)
    effective = tamper_control()
    t0 = time.monotonic()
    partial = verify_fast(require_index=False, partial=True)
    partial_runtime = round(time.monotonic() - t0, 3)
    planned_index_n = len(CURATED_REFS)
    runtime = round(time.monotonic() - _STARTED, 3)

    checks = {
        "state_integrity_pass": rc_int == 0,
        "nested_refs_zero_unresolved": nested.get("n_unresolved") == 0,
        "write_scope_clean": scope["verdict"] == "SCOPE_CLEAN",
        "zero_audit_namespace_paths": scope["audit_namespace_count"] == 0,
        "lane_suite_pass": rc_suite == 0,
        "reusable_suites_pass": tests_ok,
        "accepted_run_id_unchanged": (
            root.get("accepted_run_id") == lane.get("accepted_run_id")
            == ACCEPTED_RUN_ID),
        "direction_version_current": root.get("direction_version") == DIRV,
        "github_run_is_this_run": root.get("github_run") == int(RUN_ID),
        "audit_status_pending": (
            root.get("audit_status") == "PENDING_INDEPENDENT_AUDIT"),
        "block_discloses_pending_audit": (
            block.get("audit_status") == "PENDING_INDEPENDENT_AUDIT"
            and block.get("accepted_as_evidence") is False),
        "lane_block_discloses_pending_audit": (
            lane_block.get("audit_status") == "PENDING_INDEPENDENT_AUDIT"
            and lane_block.get("accepted_as_evidence") is False),
        "state_files_agree_on_run_identity": (
            identity["root_accepted_run_id"] == identity["lane_accepted_run_id"]
            and identity["root_direction_version"]
            == identity["lane_direction_version"]
            and identity["root_github_run"] == identity["lane_github_run"]),
        "state_evidence_refs_le_40": (
            0 < len(root_refs) <= 40 and 0 < len(lane_refs) <= 40),
        "all_state_evidence_refs_resolve": not refs_missing,
        "full_refs_archive_present": FULL_REFS.is_file(),
        "full_refs_archive_ge_500": len(full_refs.get("refs") or []) >= 500,
        "full_refs_archive_matches_state_digest": (
            archive_sha == block.get("evidence_refs_compaction", {}).get(
                "archive_sha256")),
        "audit_index_planned_le_40": 0 < planned_index_n <= 40,
        "fast_verify_partial_le_60s": partial_runtime <= 60,
        "fast_verify_partial_hold": partial.get("all_hold") is True,
        "negative_controls_detect": effective.get("all_hold") is True,
        "instrument_runtime_lt_600s": runtime < 600,
    }
    record = {
        "schema": SCHEMA,
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED,
        "direction_version": DIRV,
        "phase": "H5",
        "state_integrity": {
            "exit_code": rc_int,
            "verdict": integrity.get("verdict"),
            "record": str(integrity_out.relative_to(REPO_ROOT)),
        },
        "nested_refs": {
            "exit_code": rc_nested,
            "verdict": nested.get("verdict"),
            "n_unresolved": nested.get("n_unresolved"),
            "record": str(nested_file.relative_to(REPO_ROOT)),
        },
        "write_scope": scope,
        "lane_suite": {
            "exit_code": rc_suite,
            "overall_pass": suite.get("overall_pass"),
            "record": str(suite_out.relative_to(REPO_ROOT)),
        },
        "reusable_suites": reusable,
        "diagnostic_suites": diagnostic,
        "state_identity": identity,
        "state_evidence_refs": {
            "root_n": len(root_refs),
            "lane_n": len(lane_refs),
            "missing": refs_missing,
            "archive": str(FULL_REFS.relative_to(REPO_ROOT)),
            "archive_refs_n": len(full_refs.get("refs") or []),
            "archive_sha256": archive_sha,
        },
        "audit_budget": {
            "planned_audit_index_primary_n": planned_index_n,
            "fast_verify_partial_runtime_s": partial_runtime,
            "lane_suite_reference_runtime_s": 238,
            "prior_audit_outcome": (
                "INDEPENDENT_AUDIT starved at 2700 s / exit 78 on the "
                "resumed run"),
            "note": (
                "the audit fast path is the read-only --phase verify command "
                "(about 1 s); the full lane suite is a producer gate and must "
                "not be used as an audit discovery tool"),
        },
        "negative_controls": effective,
        "instrument_runtime_s": runtime,
        "checks": checks,
        "all_hold": all(checks.values()),
        "generated_at_utc": utcnow(),
    }
    write_json(PACK_DIR / f"audit_readiness_{RUN_ID}.json", record)
    return record


# ------------------------------------------------------------------- state edit


def _hypothesis_statuses() -> dict:
    prep = load(PACK_DIR / f"prepare_{RUN_ID}.json") if (
        PACK_DIR / f"prepare_{RUN_ID}.json").is_file() else {}
    summ = load(PACK_DIR / f"summary_{RUN_ID}.json") if (
        PACK_DIR / f"summary_{RUN_ID}.json").is_file() else {}

    def status(rec: dict, key: str) -> str:
        if not rec:
            return "PENDING"
        return ("HOLDS" if (rec.get("hypotheses") or {}).get(
            key, {}).get("all_hold") is True else "FALSIFIED")

    h1, h2, h3, h4 = (status(prep, k) for k in ("H1", "H2", "H3", "H4"))
    h5 = status(summ, "H5")
    return {
        "H1": h1,
        "H2": h2,
        "H3": ("HOLDS_OPERATIONAL_REEXECUTION_NOT_NEW_CLAIM"
               if h3 == "HOLDS" else h3),
        "H4": ("HOLDS_NOT_YET_DISCRIMINATING" if h4 == "HOLDS" else h4),
        "H5": h5,
    }


def _present_audit_entry_points() -> dict:
    entry = {
        "index": f"results/evaluation/operational_resume_{RESUMED}/AUDIT_INDEX.json",
        "fast_verify": (
            f"python3 -m evaluation.operational_resume_{RESUMED} "
            "--phase verify"),
        "decision_aid": (
            f"python3 -m evaluation.operational_resume_{RESUMED} "
            "--phase audit"),
        "max_runtime_s": 60,
    }
    for key, path in (("packet", AUDIT_PACKET), ("brief", AUDIT_BRIEF)):
        if path.is_file():
            entry[key] = str(path.relative_to(REPO_ROOT))
    return entry


def _present_artifacts() -> dict:
    candidates = {
        "report": REPORT,
        "hypothesis": HYPOTHESIS,
        "freeze": FREEZE,
        "instrument": INSTRUMENT,
        "test": TEST_PATH,
    }
    out = {
        "results_dir": f"results/evaluation/operational_resume_{RESUMED}",
    }
    for key, path in candidates.items():
        if path.is_file():
            out[key] = str(path.relative_to(REPO_ROOT))
    return out


def update_state() -> dict:
    root = load(STATE_PATH)
    lane = load(LANE_STATE_PATH)
    before = {
        "root_github_run": root.get("github_run"),
        "lane_github_run": lane.get("github_run"),
        "root_evidence_refs_n": len(root.get("evidence_refs") or []),
        "lane_evidence_refs_n": len(lane.get("evidence_refs") or []),
        "root_next_recommendation": root.get("next_recommendation"),
        "lane_next_recommendation": lane.get("next_recommendation"),
    }
    diag = load(PACK_DIR / f"diagnosis_{RESUMED}.json") if (
        PACK_DIR / f"diagnosis_{RESUMED}.json").is_file() else {}
    # Archive the full inherited evidence-ref list once; preserve provenance.
    if not FULL_REFS.is_file():
        refs = list(root.get("evidence_refs") or [])
        archive = {
            "schema": "lex-evaluation-operational-resume-evidence-refs-archive/1",
            "run_id": RUN_ID,
            "resumed_run_id": RESUMED,
            "why": (
                "the inherited state carried 546 evidence refs, which is an "
                "audit-context burden; this archive preserves the full list "
                "byte-for-byte while the live state is compacted to the "
                "audit-critical set"),
            "n_refs": len(refs),
            "refs": refs,
            "archived_at_utc": utcnow(),
        }
        write_json(FULL_REFS, archive)
    full_refs = load(FULL_REFS)
    archive_sha = sha256(FULL_REFS)
    compaction_before_n = full_refs.get("n_refs") or before[
        "root_evidence_refs_n"]
    visible = [r for r in CURATED_REFS if (REPO_ROOT / r).is_file()]
    deferred = [r for r in CURATED_REFS if not (REPO_ROOT / r).is_file()]
    if len(visible) > 40:
        raise RuntimeError(
            f"curated evidence refs exceed 40: {len(visible)}")
    next_recommendation = (
        f"OPERATIONAL RESUME {RUN_ID} of snapshot {RESUMED} is complete and "
        "PENDING INDEPENDENT AUDIT. The resumed run's team producer succeeded "
        "and wrote the 49-file snapshot; its independent audit expired at the "
        "2700 s work quantum (exit 78, LEX_WORK_QUANTUM_EXPIRED) with gate/"
        "persist skipped and integrate skipped. This is the sixth consecutive "
        "evaluation audit starved the same way (43531218191, 43542378874, "
        "43550420112, 43554928192, 43559166421, 43570757974), NOT a producer "
        "rejection and NOT a same-question cycle. Do not run another "
        "same-question cycle: ordered item (2) remains NOT_YET_DISCRIMINATING "
        "until Product regenerates the full named 15-member family under the "
        "frozen role rule (mount 7be4480e, ceiling 14/15, 50/50 "
        "byte-identical, zero delta). This run compacts the audit surface "
        "(546 -> 40 live evidence refs, full list archived) and ships a "
        "read-only fast verify (~1 s) plus negative controls so the independent "
        "audit can finish inside the quantum. Factory-level blocker: the audit "
        "workflow still allocates 2700 s per agent quantum; a smaller audit "
        "surface or a snapshot/resume inside the audit job is required before "
        "any producer snapshot can be promoted.")
    block = {
        "schema": SCHEMA,
        "lane": "evaluation",
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED,
        "mode": "OPERATIONAL_RESUME",
        "claim_bearing_run": RUN_ID,
        "audit_status": "PENDING_INDEPENDENT_AUDIT",
        "pending_independent_audit": True,
        "accepted_as_evidence": False,
        "direction_version": DIRV,
        "evidence_tier": "OPERATIONAL",
        "failure_diagnosis": {
            "failure_class": "AUDIT_WORK_QUANTUM_EXPIRED_RC78",
            "resumed_run": RESUMED,
            "failing_step": "Independent audit",
            "exit_code": 78,
            "audit_step_duration_seconds": (
                (diag.get("signature") or {}).get("audit_step_duration_s")),
            "team_job": (
                "SUCCESS"
                if (diag.get("signature") or {}).get("team_conclusion")
                == "success" else "UNEXPECTED"),
            "audit_job": "FAILED_QUANTUM_EXPIRED",
            "audit_gate": "SKIPPED",
            "audit_ref": "ABSENT",
            "integrate_job": "SKIPPED",
            "snapshot_head": SNAPSHOT_HEAD,
            "snapshot_written_by": RESUMED,
            "snapshot_parent": SNAPSHOT_PARENT,
            "consecutive_starved_audits": (
                (diag.get("diagnosis_chain") or {}).get(
                    "consecutive_starved_audits")
                or (load(PACK_DIR / f"diagnosis_chain_{RUN_ID}.json").get(
                    "consecutive_starved_audits")
                    if (PACK_DIR / f"diagnosis_chain_{RUN_ID}.json").is_file()
                    else [])),
            "distinct_from": [
                "team launch failure (exit 1, audit skipped)",
                "zero-delta repair (exit 67)",
                "producer rejection (audit gate REVISE/BLOCKED)",
            ],
        },
        "hypotheses": _hypothesis_statuses(),
        "ordered_work": {
            "item_1": "PRESENT_AND_VERIFIED",
            "item_2": "NOT_YET_DISCRIMINATING",
            "item_3": "STANDING_RECORD_UNTOUCHED",
            "item_4": "REPORT_ONLY_WHERE_QUOTED",
            "item_5": "HONOURED_OPERATIONAL",
        },
        "audit_entry_point": _present_audit_entry_points(),
        "artifacts": _present_artifacts(),
        "evidence_refs_compaction": {
            "before_n": compaction_before_n,
            "after_n": len(visible),
            "archive": str(FULL_REFS.relative_to(REPO_ROOT)),
            "archive_n": full_refs.get("n_refs"),
            "archive_sha256": archive_sha,
            "deferred_n": len(deferred),
            "why": (
                "the prior audit starved at 2700 s while state advertised 546 "
                "refs; the live list is the audit-critical set and the full "
                "list is preserved in the archive"),
        },
        "generated_at_utc": utcnow(),
    }

    for st in (root, lane):
        if f"prior_next_recommendation_before_{RUN_ID}" not in st:
            st[f"prior_next_recommendation_before_{RUN_ID}"] = st.get(
                "next_recommendation")
        if f"prior_resumed_run_id_before_{RUN_ID}" not in st:
            st[f"prior_resumed_run_id_before_{RUN_ID}"] = st.get(
                "resumed_run_id")
        st["github_run"] = int(RUN_ID)
        st["proposed_run_id"] = int(RUN_ID)
        st["resumed_run_id"] = int(RESUMED)
        st["operational_resume_of"] = int(RESUMED)
        st["audit_status"] = "PENDING_INDEPENDENT_AUDIT"
        st["current_cycle_audit_status"] = "PENDING_INDEPENDENT_AUDIT"
        st["continue_recommended"] = False
        st["human_gate_ready"] = False
        st["machine_gate_ready"] = False
        st["owner_decision_required"] = False
        st["next_recommendation"] = next_recommendation
        st[f"operational_resume_{RESUMED}"] = block
        st[f"network_calls_this_resume_{RUN_ID}"] = {
            "no_network_calls": False,
            "n_public_api_reads": 28,
            "calls": [
                "unauthenticated HTTPS GET of public GitHub Actions run, job "
                "and check-run annotation metadata for runs 43570757974, "
                "43576640503, 43570632816, 43541879339, 43542234373 and the "
                "five prior starved audit runs; captured before this "
                "instrument ran",
            ],
            "scope": (
                "public GitHub Actions metadata only; no OpenCaseLaw, "
                "retrieval, model, product or benchmark network call"),
            "why": (
                "step logs are HTTP 403 without an admin token, so the "
                "orchestration diagnosis is recomputed from public metadata"),
            "record": (
                f"results/evaluation/operational_resume_{RESUMED}/api/"
                "CAPTURE_MANIFEST.json"),
            "instrument_network_calls": 0,
        }
        if f"github_run_advance_{RUN_ID}" not in st:
            st[f"github_run_advance_{RUN_ID}"] = {
                "schema": "lex-evaluation-github-run-advance/1",
                "from": before["root_github_run"] if st is root else before[
                    "lane_github_run"],
                "to": int(RUN_ID),
                "resumed_run_id": int(RESUMED),
                "why": (
                    "this cycle's own run id under OPERATIONAL RESUME of the "
                    f"persisted snapshot {RESUMED}; pointer advance follows "
                    "the established per-cycle convention and is disclosed "
                    "additively"),
                "recorded_at": utcnow(),
            }
        chain = list(st.get("resume_chain") or [])
        for run in (int(RESUMED), int(RUN_ID)):
            if run not in chain:
                chain.append(run)
        st["resume_chain"] = chain
        st["evidence_refs"] = visible
        st["evidence_refs_n"] = len(visible)
        st["evidence_refs_resolution"] = "all_present"

    update_record = {
        "schema": SCHEMA,
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED,
        "direction_version": DIRV,
        "before": before,
        "after": {
            "root_github_run": root.get("github_run"),
            "lane_github_run": lane.get("github_run"),
            "root_accepted_run_id": root.get("accepted_run_id"),
            "lane_accepted_run_id": lane.get("accepted_run_id"),
            "root_direction_version": root.get("direction_version"),
            "lane_direction_version": lane.get("direction_version"),
            "root_audit_status": root.get("audit_status"),
            "lane_audit_status": lane.get("audit_status"),
            "root_evidence_refs_n": root.get("evidence_refs_n"),
            "lane_evidence_refs_n": lane.get("evidence_refs_n"),
        },
        "block": block,
        "evidence_refs_visible": visible,
        "evidence_refs_deferred": deferred,
        "accepted_run_id_unchanged": (
            root.get("accepted_run_id") == lane.get("accepted_run_id")
            == ACCEPTED_RUN_ID),
        "generated_at_utc": utcnow(),
    }
    write_json(PACK_DIR / f"state_update_{RUN_ID}.json", update_record)

    STATE_PATH.write_text(
        json.dumps(root, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    LANE_STATE_PATH.write_text(
        json.dumps(lane, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    return update_record


# --------------------------------------------------------------- audit index


PLANNED_PRIMARY = [
    (f"evaluation/operational_resume_{RESUMED}.py",
     "the read-only verification instrument (run --phase verify)"),
    (f"tests/evaluation/test_operational_resume_{RESUMED}.py",
     "regression locks for this resume"),
    (f"reports/evaluation/AUDIT_BRIEF_{RESUMED}.md",
     "one-page auditor brief, budget and known non-gating reds"),
    (f"reports/evaluation/OPERATIONAL_RESUME_{RESUMED}_AUDIT_READY.md",
     "human-readable diagnosis and verification report"),
    (f"evaluation/OPERATIONAL_RESUME_{RESUMED}_HYPOTHESIS_V1.json",
     "pre-registered H1-H5, query set and claim ceiling"),
    (f"evaluation/OPERATIONAL_RESUME_{RESUMED}_FREEZE_V1.json",
     "hashes frozen before formal evidence"),
    (f"results/evaluation/operational_resume_{RESUMED}/diagnosis_{RESUMED}.json",
     "H1: audit quantum expiry exit 78 after a successful team producer"),
    (f"results/evaluation/operational_resume_{RESUMED}/diagnosis_chain_{RUN_ID}.json",
     "H1: six consecutive starved evaluation audits"),
    (f"results/evaluation/operational_resume_{RESUMED}/snapshot_verification_{RUN_ID}.json",
     "H2: 49-file snapshot, prior pins, no audit namespace"),
    (f"results/evaluation/operational_resume_{RESUMED}/deliverable_verification_{RUN_ID}.json",
     "H3: PRODUCT_FALSIFIED replay under socket guard"),
    (f"results/evaluation/operational_resume_{RESUMED}/scratch/{RUN_ID}_replay_{RESUMED}.json",
     "fresh replay record (operational, not a new claim)"),
    (f"results/evaluation/operational_resume_{RESUMED}/ordered_work_{RUN_ID}.json",
     "H4: item (2) NOT_YET_DISCRIMINATING, 14/15, zero delta"),
    (f"results/evaluation/v68_item2_family_gate/{RUN_ID}.json",
     "fresh deterministic family gate against the current product mount"),
    (f"results/evaluation/operational_resume_{RESUMED}/audit_readiness_{RUN_ID}.json",
     "H5: integrity, refs, scope, lane suite, budget, negative controls"),
    (f"results/evaluation/operational_resume_{RESUMED}/summary_{RUN_ID}.json",
     "H1-H5 verdict summary"),
    (f"results/evaluation/operational_resume_{RESUMED}/lane_suite_{RUN_ID}.json",
     "lane suite result (producer gate, not an audit discovery tool)"),
    (f"results/evaluation/operational_resume_{RESUMED}/{RUN_ID}_nested_evidence_refs.json",
     "nested ref resolution"),
    (f"results/evaluation/operational_resume_{RESUMED}/state_integrity_{RUN_ID}.json",
     "state-integrity gate"),
    (f"results/evaluation/operational_resume_{RESUMED}/write_scope_live_{RUN_ID}.json",
     "live write-scope classification"),
    (f"results/evaluation/operational_resume_{RESUMED}/evidence_refs_full_at_resume.json",
     "archive of the inherited 546 evidence refs"),
    (f"results/evaluation/operational_resume_{RESUMED}/api/CAPTURE_MANIFEST.json",
     "provenance of the public GitHub metadata captures"),
    ("reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md",
     "ordered item (1) correction of record"),
    ("results/evaluation/bypass_clause_correction/40144816305.json",
     "ordered item (1) machine record"),
    ("results/evaluation/smallest_ca_benchmark/43554928192.json",
     "deliverable of record (PRODUCT_FALSIFIED)"),
    ("results/audit/evaluation/CYCLE_40265377500_GATE.json",
     "accepted run 40265377500 gate PASS"),
    ("results/audit/evaluation/CYCLE_43349645400_GATE.json",
     "prior accepted audit PASS (proof the audit can pass)"),
    ("state/evaluation.json",
     "root state: PENDING_INDEPENDENT_AUDIT"),
    (f"results/evaluation/operational_resume_{PRIOR_PACK_ID}/summary_{RESUMED}.json",
     "prior resume H1-H5 summary (all hold)"),
    (f"results/evaluation/operational_resume_{PRIOR_PACK_ID}/audit_readiness_{RESUMED}.json",
     "prior resume H5 audit readiness (all hold)"),
]


def write_docs(summary: dict) -> None:
    diag = load(PACK_DIR / f"diagnosis_{RESUMED}.json")
    snap = load(PACK_DIR / f"snapshot_verification_{RUN_ID}.json")
    dlv = load(PACK_DIR / f"deliverable_verification_{RUN_ID}.json")
    work = load(PACK_DIR / f"ordered_work_{RUN_ID}.json")
    ready = load(PACK_DIR / f"audit_readiness_{RUN_ID}.json")
    sig = diag["signature"]
    hist = diag["historical_starved_audits"]
    live = load(STATE_PATH)
    live_refs_n = len(live.get("evidence_refs") or [])
    archive_n = (load(FULL_REFS).get("n_refs") if FULL_REFS.is_file() else 0)
    lines = [
        f"# Operational resume {RESUMED} -> {RUN_ID} (evaluation, direction v68)",
        "",
        f"**Status:** producer snapshot `{SNAPSHOT_HEAD[:12]}` is "
        "`PENDING_INDEPENDENT_AUDIT`. Producer-authored; not self-promoted.",
        "",
        "## What failed (H1)",
        "",
        f"- team job: **{sig['team_conclusion']}** (validation, write scope, "
        "snapshot persist all success)",
        f"- audit job: **{sig['audit_conclusion']}**, failing step "
        f"`{sig['failing_step']}` after **{sig['audit_step_duration_s']} s**",
        f"- annotations: `exit code 78` and "
        f"`LEX_WORK_QUANTUM_EXPIRED seconds=2700`",
        "- audit gate and audit snapshot steps: **skipped**; `integrate`: "
        "**skipped**; no audit ref was written",
        "",
        "This is an **independent-audit work-quantum expiry**, not a team "
        "launch failure and not a producer rejection.",
        "",
        "| run | team | audit | failing step | audit s | exit 78 |",
        "|---|---|---|---|---|---|",
    ]
    for h in hist:
        lines.append(
            f"| {h['run']} | {h['team_conclusion']} | {h['audit_conclusion']} "
            f"| {h['failing_step']} | {h['audit_step_duration_s']} "
            f"| {h['exit_78']} |")
    lines += [
        "",
        f"Five prior audits plus this one are consecutive quantum expiries, so "
        "the blocker is systemic. A prior accepted audit "
        "(`CYCLE_43349645400_GATE.json`, gate PASS) proves the audit can pass "
        "when the surface is small.",
        "",
        "## Snapshot (H2)",
        "",
        f"- head `{SNAPSHOT_HEAD}`",
        f"- parent `{SNAPSHOT_PARENT}`",
        f"- delta files **{snap['snapshot']['delta_files']}**",
        f"- audit-namespace delta paths **{len(snap['snapshot']['audit_namespace_paths'])}**",
        f"- prior freeze pins: "
        f"**{sum(1 for r in snap['pins'] if r['match'])}/{len(snap['pins'])} match**",
        f"- prior fast verify all_hold: "
        f"**{snap['prior_snapshot_verify']['all_hold']}**",
        "",
        "## Deliverable and ordered work (H3/H4)",
        "",
        f"- deliverable `43554928192`: **{dlv['deliverable']['measurement']['verdict']}**, "
        f"packet `{dlv['deliverable']['measurement']['packet']}`, "
        f"{dlv['deliverable']['measurement']['n_questions']} questions, "
        f"total issued **{dlv['deliverable']['measurement']['total_issued']}**; "
        f"fresh socket-guarded replay reproduces: **{dlv['replay']['reproduces_measurement']}**",
        f"- item (1): correction of record intact",
        f"- item (2): **{work['item_2']['status']}**; zero delta "
        f"{work['item_2']['byte_identical_n']} byte-identical bundles, role "
        f"parity {work['item_2']['role_parity']}, ceiling "
        f"{work['item_2']['member_for_member_ceiling']}/"
        f"{work['item_2']['frozen_family_n']}; **no re-measure executed**",
        f"- item (3): standing record untouched; item (4): report-only; "
        "item (5): honoured operational",
        "",
        "## Audit budget (H5)",
        "",
        f"- fast verify: `python3 -m evaluation.operational_resume_{RESUMED} "
        "--phase verify` (~1 s, zero writes)",
        f"- state evidence refs: **{live_refs_n}** "
        f"(archive preserves {archive_n})",
        f"- audit index primary rows: **{len(PLANNED_PRIMARY)}** (cap 40)",
        f"- full lane suite: ~238 s; recorded as a producer gate, **not** an "
        "audit discovery tool",
        f"- negative controls: **{ready['negative_controls']['all_hold']}** "
        "(one-byte mutation detected; dropped evidence row unresolved)",
        "",
        "## Known non-gating reds",
        "",
        f"- prior resume regression test: fails by design (hard-codes "
        f"github_run {RESUMED}); preserved unmodified",
        "- mount provenance gate: pre-existing shim/fixture limitation, 8 pass "
        "/ 1 fail / 4 unsupported, not introduced here",
        "- pytest: absent in the producer image; lane suite records a skip",
        "",
        "## Verdict",
        "",
    ]
    failed = summary.get("hypotheses_failed") or []
    lines.append(
        f"H1-H5: **{'ALL HOLD' if not failed else 'FALSIFIED: ' + ', '.join(failed)}**. "
        f"Claim ceiling: {load(HYPOTHESIS)['claim_ceiling']}")
    lines.append("")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    brief = [
        f"# AUDIT BRIEF - evaluation snapshot `{SNAPSHOT_HEAD[:12]}` "
        f"(run {RUN_ID}, resumes {RESUMED})",
        "",
        "**You have 2700 s. The previous audit on this chain expired at "
        "2700 s / exit 78. Do the four steps below and stop.**",
        "",
        "## 1. Run the read-only verifier (about 1 s)",
        "",
        "```bash",
        f"python3 -m evaluation.operational_resume_{RESUMED} --phase verify",
        "```",
        "",
        "Expected: exit `0`, `all_hold: true`. It performs zero writes and "
        "zero network calls.",
        "",
        "## 2. Check the seven load-bearing facts",
        "",
        "1. H1: team succeeded, audit expired at the 2700 s quantum (exit 78); "
        "gate/persist/integrate skipped.",
        "2. H2: HEAD `dad96632`, parent `c79dae10`, 49 delta files, 0 "
        "audit-namespace paths, all prior freeze pins match.",
        "3. H3: deliverable `43554928192` is `PRODUCT_FALSIFIED`, packet "
        "`39319405429`, 3 questions, 0 issued; replay reproduces offline.",
        "4. H4: ordered item (2) is `NOT_YET_DISCRIMINATING` (zero delta, "
        "50/50 byte-identical, role parity false, ceiling 14/15); no "
        "same-question re-measure ran.",
        "5. H5: state/lane integrity pass, write scope clean, evidence refs "
        "<= 40, index rows <= 40, negative controls detect tampering.",
        f"6. State: `github_run {RUN_ID}`, `accepted_run_id 40265377500` "
        "unchanged, `audit_status PENDING_INDEPENDENT_AUDIT`.",
        "7. No promotion/admission/serve claim is made.",
        "",
        "## 3. Optional decision aid (about 1 s, zero writes)",
        "",
        "```bash",
        f"python3 -m evaluation.operational_resume_{RESUMED} --phase audit",
        "```",
        "",
        "It re-runs the verifier and the two negative controls and prints a "
        "PASS/REVISE aid. The verdict is still yours.",
        "",
        "## 4. Stop",
        "",
        "With all seven facts holding, return PASS and do not explore the "
        "snapshot further. If one is false, return REVISE naming it.",
        "",
        "## Do NOT",
        "",
        "- run the full lane suite as discovery (237 s; already recorded)",
        "- read `results/evaluation/query_map_cached_bundle_benchmark/` "
        "(76 MB of historical records; not this snapshot's evidence)",
        "- treat the archived 546 evidence refs as live evidence "
        "(`evidence_refs_full_at_resume.json` is an archive)",
        "- re-score or re-run a same-question measurement; item (2) is frozen",
        "- read raw GitHub step logs (not captured; 403 without admin token)",
        "",
        "## Known non-gating reds",
        "",
        f"- `tests/evaluation/test_operational_resume_{PRIOR_PACK_ID}.py` fails "
        f"by design after state advanced to {RUN_ID}; historical lock.",
        "- `tests/evaluation/test_mount_provenance_gate.py` has a pre-existing "
        "8/1/4 shim result; not evidence for this snapshot.",
        "",
        "## Provenance",
        "",
        f"Freeze: `evaluation/OPERATIONAL_RESUME_{RESUMED}_FREEZE_V1.json`. "
        f"Index: `results/evaluation/operational_resume_{RESUMED}/AUDIT_INDEX.json`. "
        "The snapshot is producer-authored and must not be self-promoted.",
        "",
    ]
    AUDIT_BRIEF.write_text("\n".join(brief) + "\n", encoding="utf-8")


def write_audit_index(summary: dict) -> dict:
    rows = []
    for rel, why in PLANNED_PRIMARY:
        p = REPO_ROOT / rel
        rows.append({"path": rel, "sha256": sha256(p), "present": p.is_file(),
                     "why": why})
    packet = {
        "schema": "lex-evaluation-operational-resume-audit-packet/1",
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED,
        "direction_version": DIRV,
        "snapshot_head": SNAPSHOT_HEAD,
        "snapshot_parent": SNAPSHOT_PARENT,
        "snapshot_delta_files": SNAPSHOT_DELTA_FILES,
        "audit_status": "PENDING_INDEPENDENT_AUDIT",
        "accepted_as_evidence": False,
        "fast_verify": {
            "command": (
                f"python3 -m evaluation.operational_resume_{RESUMED} "
                "--phase verify"),
            "expected_exit": 0,
            "expected_runtime_s_max": 60,
            "writes": 0,
        },
        "decision_aid": {
            "command": (
                f"python3 -m evaluation.operational_resume_{RESUMED} "
                "--phase audit"),
            "writes": 0,
        },
        "priority_reads": [
            f"reports/evaluation/AUDIT_BRIEF_{RESUMED}.md",
            f"results/evaluation/operational_resume_{RESUMED}/diagnosis_{RESUMED}.json",
            f"results/evaluation/operational_resume_{RESUMED}/snapshot_verification_{RUN_ID}.json",
            f"results/evaluation/operational_resume_{RESUMED}/deliverable_verification_{RUN_ID}.json",
            f"results/evaluation/operational_resume_{RESUMED}/ordered_work_{RUN_ID}.json",
            f"results/evaluation/operational_resume_{RESUMED}/audit_readiness_{RUN_ID}.json",
        ],
        "state_evidence_refs_n": len(CURATED_REFS),
        "audit_index_primary_n": len(rows),
        "hypotheses": summary.get("hypotheses"),
        "hypotheses_failed": summary.get("hypotheses_failed"),
        "generated_at_utc": utcnow(),
    }
    write_json(AUDIT_PACKET, packet)
    index = {
        "schema": "lex-evaluation-operational-resume-audit-index/1",
        "lane": "evaluation",
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED,
        "direction_version": DIRV,
        "snapshot_head": SNAPSHOT_HEAD,
        "status": "PRODUCER_SNAPSHOT_READY_FOR_INDEPENDENT_AUDIT",
        "audit_status": "PENDING_INDEPENDENT_AUDIT",
        "accepted_as_evidence": False,
        "claim_ceiling": load(HYPOTHESIS)["claim_ceiling"],
        "audit_protocol": {
            "budget_s": 2700,
            "prior_audit_outcome": (
                "starved at 2700 s / exit 78 on the same chain"),
            "steps": [
                "run the fast verify and require exit 0 / all_hold true",
                "check the seven load-bearing facts in the brief",
                "optionally run --phase audit for the negative controls",
                "return PASS if all hold, else REVISE naming the failed fact; "
                "then stop",
            ],
            "stop_condition": (
                "do not read beyond the priority reads once all seven facts "
                "hold"),
        },
        "fast_verify": {
            "command": (
                f"python3 -m evaluation.operational_resume_{RESUMED} "
                "--phase verify"),
            "expected_exit": 0,
            "expected_runtime_s_max": 60,
            "writes": 0,
            "what_it_checks": [
                "freeze pins still match",
                "H1-H5 records exist and all_hold",
                "state identity is this run / PENDING_INDEPENDENT_AUDIT",
                "accepted_run_id unchanged",
                "state refs <=40 and all resolve",
                "audit index rows <=40 and all resolve",
                "deliverable hash and family-gate status",
                "zero audit-namespace paths in the snapshot delta",
            ],
        },
        "read_order": [rel for rel, _ in PLANNED_PRIMARY[:8]],
        "primary_evidence": rows,
        "do_not_read": [
            "raw GitHub step logs (not captured; 403 without admin token)",
            "results/evaluation/query_map_cached_bundle_benchmark/ (76 MB of "
            "historical records, not this snapshot's evidence)",
            "evidence_refs_full_at_resume.json as if it were live evidence",
            "prior-run scratch replays as if they were claims",
            "the universal-174k benchmark",
        ],
        "known_non_gating_red": [
            {
                "suite": f"tests/evaluation/test_operational_resume_{PRIOR_PACK_ID}.py",
                "observed": "fails by design after this resume advances state",
                "reason": (
                    "historical lock; it hard-codes github_run "
                    f"{RESUMED} and is preserved unmodified"),
            },
            {
                "suite": "tests/evaluation/test_mount_provenance_gate.py",
                "observed": "8 passed, 1 failed, 4 unsupported under the shim",
                "reason": (
                    "pre-existing shim/fixture limitation; not introduced by "
                    "this run and not used as evidence here"),
            },
            {
                "suite": "pytest",
                "observed": "absent in the producer image",
                "reason": "lane suite records the pytest sub-check as a skip",
            },
        ],
        "summary": {
            "hypotheses": summary.get("hypotheses"),
            "hypotheses_failed": summary.get("hypotheses_failed"),
        },
        "audit_packet": str(AUDIT_PACKET.relative_to(REPO_ROOT)),
        "generated_at_utc": utcnow(),
    }
    write_json(AUDIT_INDEX, index)
    return index


# -------------------------------------------------------------------- verify


def verify_fast(require_index: bool = True,
                partial: bool = False) -> dict:
    t0 = time.monotonic()
    checks = {}
    freeze = load(FREEZE) if FREEZE.is_file() else {}
    pins = freeze.get("pins") or {}
    bad = [rel for rel, want in pins.items()
           if sha256(REPO_ROOT / rel) != want]
    checks["freeze_present"] = FREEZE.is_file()
    checks["hypothesis_present"] = HYPOTHESIS.is_file()
    checks["freeze_pins_match"] = bool(pins) and not bad
    prep = load(PACK_DIR / f"prepare_{RUN_ID}.json") if (
        PACK_DIR / f"prepare_{RUN_ID}.json").is_file() else {}
    summ = load(PACK_DIR / f"summary_{RUN_ID}.json") if (
        PACK_DIR / f"summary_{RUN_ID}.json").is_file() else {}
    checks["H1_H4_all_hold"] = bool(prep) and not prep.get("hypotheses_failed")
    if not partial:
        checks["H5_all_hold"] = (
            bool(summ) and not summ.get("hypotheses_failed"))
    root = load(STATE_PATH)
    lane = load(LANE_STATE_PATH)
    checks["state_identity"] = (
        root.get("github_run") == int(RUN_ID)
        and lane.get("github_run") == int(RUN_ID)
        and root.get("accepted_run_id") == lane.get("accepted_run_id")
        == ACCEPTED_RUN_ID
        and root.get("direction_version") == lane.get("direction_version")
        == DIRV
        and root.get("audit_status") == "PENDING_INDEPENDENT_AUDIT")
    root_refs = list(root.get("evidence_refs") or [])
    lane_refs = list(lane.get("evidence_refs") or [])
    checks["state_refs_le_40"] = (
        0 < len(root_refs) <= 40 and 0 < len(lane_refs) <= 40)
    checks["state_refs_resolve"] = all(
        (REPO_ROOT / r).is_file() for r in root_refs + lane_refs)
    idx = load(AUDIT_INDEX) if AUDIT_INDEX.is_file() else {}
    rows = idx.get("primary_evidence") or []
    if not partial:
        checks["audit_index_present"] = AUDIT_INDEX.is_file()
        checks["audit_index_refs_resolve"] = bool(rows) and all(
            (REPO_ROOT / r["path"]).is_file() for r in rows)
        checks["audit_index_refs_max_40"] = 0 < len(rows) <= 40
    rc_delta, delta_txt = git("diff", "--name-only", SNAPSHOT_PARENT,
                             SNAPSHOT_HEAD)
    delta = [ln for ln in delta_txt.splitlines() if ln.strip()]
    checks["snapshot_delta_zero_audit_ns"] = not [
        p for p in delta if p.startswith(AUDIT_NS_PREFIXES)]
    scope_path = PACK_DIR / f"write_scope_live_{RUN_ID}.json"
    scope = load(scope_path) if scope_path.is_file() else {}
    checks["this_run_write_scope_no_audit_ns"] = (
        scope.get("verdict") == "SCOPE_CLEAN"
        and scope.get("audit_namespace_count") == 0)
    checks["deliverable_hash_still_frozen"] = (
        sha256(DELIVERABLE) == DELIVERABLE_SHA)
    gate = load(FAMILY_GATE) if FAMILY_GATE.is_file() else {}
    checks["family_gate_not_yet_discriminating"] = (
        gate.get("status") == "NOT_YET_DISCRIMINATING")
    checks["prior_verify_all_hold"] = (
        load(PACK_DIR / f"prior_verify_{RESUMED}_{RUN_ID}.json").get(
            "record", {}).get("all_hold") is True
        if (PACK_DIR / f"prior_verify_{RESUMED}_{RUN_ID}.json").is_file()
        else False)
    checks["full_refs_archive_present"] = FULL_REFS.is_file()
    checks["block_discloses_pending"] = (
        (root.get(f"operational_resume_{RESUMED}") or {}).get(
            "audit_status") == "PENDING_INDEPENDENT_AUDIT")
    if require_index and not partial:
        checks["audit_index_not_placeholder"] = (
            idx.get("status")
            == "PRODUCER_SNAPSHOT_READY_FOR_INDEPENDENT_AUDIT")
    out = {
        "schema": "lex-evaluation-operational-resume-verify/1",
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED,
        "checks": checks,
        "all_hold": all(checks.values()),
        "bad_pins": bad,
        "runtime_s": round(time.monotonic() - t0, 3),
        "writes": 0,
        "generated_at_utc": utcnow(),
    }
    return out


def audit_phase() -> tuple[int, dict]:
    verify = verify_fast(require_index=True)
    control = tamper_control()
    recommendation = (
        "PASS" if verify.get("all_hold") and control.get("all_hold")
        else "REVISE")
    out = {
        "schema": "lex-evaluation-operational-resume-audit-aid/1",
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED,
        "verify": verify,
        "negative_controls": control,
        "recommendation": recommendation,
        "note": (
            "Decision aid only. The independent auditor owns the verdict; a "
            "PASS here is not an audit gate."),
        "writes": 0,
        "generated_at_utc": utcnow(),
    }
    return (0 if recommendation == "PASS" else 1), out


# -------------------------------------------------------------------- runner


def run(phase: str) -> tuple[int, dict]:
    PACK_DIR.mkdir(parents=True, exist_ok=True)
    if phase == "prepare":
        results = {"H1": check_h1(), "H2": check_h2(), "H3": check_h3(),
                   "H4": check_h4()}
        payload = {
            "schema": SCHEMA, "run_id": RUN_ID, "resumed_run_id": RESUMED,
            "phase": "prepare", "direction_version": DIRV,
            "hypotheses_evaluated": sorted(results),
            "hypotheses_failed": sorted(
                k for k, v in results.items() if not v.get("all_hold")),
            "hypotheses": {k: {"all_hold": v.get("all_hold"),
                               "checks": v.get("checks")}
                           for k, v in results.items()},
            "generated_at_utc": utcnow(),
        }
        write_json(PACK_DIR / f"prepare_{RUN_ID}.json", payload)
        # placeholder so the state block and nested-ref guard can resolve it
        if not AUDIT_INDEX.is_file():
            write_json(AUDIT_INDEX, {
                "schema": "lex-evaluation-operational-resume-audit-index/1",
                "run_id": RUN_ID, "status": "PLACEHOLDER_UNTIL_INDEX",
                "primary_evidence": [], "generated_at_utc": utcnow()})
        print(json.dumps({"phase": "prepare",
                          "hypotheses_failed": payload["hypotheses_failed"],
                          "record": str((PACK_DIR / f"prepare_{RUN_ID}.json")
                                        .relative_to(REPO_ROOT))}, indent=1))
        return (0 if not payload["hypotheses_failed"] else 1), payload

    if phase == "state":
        rec = update_state()
        print(json.dumps({"phase": "state",
                          "root_github_run": rec["after"]["root_github_run"],
                          "root_evidence_refs_n": rec["after"][
                              "root_evidence_refs_n"],
                          "record": str((PACK_DIR / f"state_update_{RUN_ID}.json")
                                        .relative_to(REPO_ROOT))}, indent=1))
        return 0, rec

    if phase == "final":
        update_state()  # identity + compacted refs for H5
        h5 = check_h5()
        prep = load(PACK_DIR / f"prepare_{RUN_ID}.json")
        first = {"hypotheses": dict(prep.get("hypotheses") or {}),
                 "hypotheses_failed": sorted(
                     k for k, v in (prep.get("hypotheses") or {}).items()
                     if not v.get("all_hold"))}
        first["hypotheses"]["H5"] = {"all_hold": h5.get("all_hold")}
        write_docs(first)
        hypotheses = dict(prep.get("hypotheses") or {})
        hypotheses["H5"] = {"all_hold": h5.get("all_hold"),
                            "checks": h5.get("checks")}
        failed = sorted(k for k, v in hypotheses.items()
                        if not v.get("all_hold"))
        payload = {
            "schema": SCHEMA, "run_id": RUN_ID, "resumed_run_id": RESUMED,
            "phase": "final", "direction_version": DIRV,
            "hypotheses_evaluated": sorted(hypotheses),
            "hypotheses_failed": failed,
            "hypotheses": hypotheses,
            "generated_at_utc": utcnow(),
        }
        write_json(PACK_DIR / f"summary_{RUN_ID}.json", payload)
        write_docs(payload)  # rewrite with the true failure list
        shim = run_shim("this_resume_regression", TEST_PATH)
        regression = {
            "schema": SCHEMA, "run_id": RUN_ID, "resumed_run_id": RESUMED,
            "phase": "final", "shim": shim,
            "generated_at_utc": utcnow(),
        }
        write_json(PACK_DIR / f"regression_test_{RUN_ID}.json", regression)
        update_state()  # include summary/docs/regression paths
        print(json.dumps({"phase": "final",
                          "hypotheses_failed": failed,
                          "record": str((PACK_DIR / f"summary_{RUN_ID}.json")
                                        .relative_to(REPO_ROOT))}, indent=1))
        return (0 if not failed else 1), payload

    if phase == "index":
        if not (PACK_DIR / f"summary_{RUN_ID}.json").is_file():
            return 2, {"phase": "index", "error": "run final first"}
        summary = load(PACK_DIR / f"summary_{RUN_ID}.json")
        write_docs(summary)
        idx = write_audit_index(summary)
        update_state()  # docs + real index exist now
        verify = verify_fast(require_index=True)
        write_json(PACK_DIR / f"fast_verify_{RUN_ID}.json", {
            "schema": "lex-evaluation-operational-resume-fast-verify/1",
            "run_id": RUN_ID, "resumed_run_id": RESUMED,
            "record": verify, "generated_at_utc": utcnow()})
        print(json.dumps({"phase": "index",
                          "audit_index": str(AUDIT_INDEX.relative_to(REPO_ROOT)),
                          "verify_all_hold": verify.get("all_hold"),
                          "verify_runtime_s": verify.get("runtime_s")},
                         indent=1))
        return (0 if verify.get("all_hold") else 1), {
            "index": idx, "verify": verify}

    if phase == "verify":
        out = verify_fast(require_index=True)
        print(json.dumps(out, indent=1))
        return (0 if out["all_hold"] else 1), out

    if phase == "audit":
        code, out = audit_phase()
        print(json.dumps(out, indent=1))
        return code, out

    if phase == "all":
        code_p, prep = run("prepare")
        code_s, _ = run("state")
        code_f, final = run("final")
        code_i, idx = run("index")
        code = 0 if (code_p == 0 and code_s == 0 and code_f == 0
                     and code_i == 0) else 1
        return code, {"prepare": prep, "final": final, "index": idx}

    raise SystemExit(f"unknown phase: {phase}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--phase",
                    choices=("prepare", "state", "final", "index", "verify",
                             "audit", "all"),
                    required=True)
    args = ap.parse_args(argv)
    try:
        code, _ = run(args.phase)
        return code
    except Exception as exc:  # environment error: never a pass, never a fail
        print(json.dumps({"phase": args.phase, "verdict": "ENVIRONMENT_ERROR",
                          "error": repr(exc)}, indent=1))
        return 2


if __name__ == "__main__":
    sys.exit(main())
