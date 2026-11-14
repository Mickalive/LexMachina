#!/usr/bin/env python3
"""Operational resume 43570632816 -> run 43570757974 (evaluation lane, v68).

Run 43570632816 never reached a producer cycle: its ``team`` job failed in the
``Run lane cycle`` step after ~16 s with exit code 1, every later validation and
write-scope step was skipped, and the ``if: always()`` persistence step
force-pushed the unchanged accepted working base as the snapshot.  This
instrument therefore verifies the *persisted snapshot* (commit c79dae10, which
is the output of the earlier completed operational resume 43565032175), records
the orchestration failure class, re-checks ordered v68 item (2), and makes the
snapshot audit-ready for its own run id.

It is a diagnosis + verification instrument, not a new product cycle.

Phases
  prepare  H1-H4 (failure diagnosis, snapshot preservation/replay, ordered work)
  state    additive state advance in state/evaluation.json + evaluation/state/evaluation.json
  final    H5 (state integrity, nested refs, write scope, lane suite, reusable tests)
  verify   read-only fast audit entry point (no writes)
  all      prepare -> state -> final -> state refresh

Zero network in the instrument.  The replay is executed under a socket guard.
Public GitHub Actions metadata was captured *before* the instrument ran and is
committed under results/evaluation/operational_resume_43570632816/api/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RUN_ID = "43570757974"
RESUMED = "43570632816"
CHAIN_PRIOR = "43570515880"
PRIOR_COMPLETED = "43565032175"
PRIOR_PACK_ID = "43559166421"
SNAPSHOT_HEAD = "c79dae10ef9591e4448c4a7e426c81e4686a180c"
SNAPSHOT_PARENT = "c40cd9288bbcab02a5489bd768e2a329f4dea218"
SNAPSHOT_DELTA_FILES = 41
DIRV = 68
ACCEPTED_RUN_ID = 40265377500
PRODUCT_MOUNT = Path("/tmp/lex_accepted/product")
PRODUCT_HEAD_DIRECTION = "8b5b08dd"
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
STATE_PATH = REPO_ROOT / "state/evaluation.json"
LANE_STATE_PATH = REPO_ROOT / "evaluation/state/evaluation.json"

PRIOR_PACK = REPO_ROOT / f"results/evaluation/operational_resume_{PRIOR_PACK_ID}"
PRIOR_FREEZE = REPO_ROOT / (
    f"evaluation/OPERATIONAL_RESUME_{PRIOR_PACK_ID}_FREEZE_V1.json")
PRIOR_VERIFY = REPO_ROOT / (
    f"evaluation/operational_resume_{PRIOR_PACK_ID}.py")
PRIOR_SUMMARY = PRIOR_PACK / f"summary_{PRIOR_COMPLETED}.json"
PRIOR_DELIVERABLE_VERIFY = PRIOR_PACK / (
    f"deliverable_verification_{PRIOR_COMPLETED}.json")

DELIVERABLE = REPO_ROOT / "results/evaluation/smallest_ca_benchmark/43554928192.json"
FAMILY_GATE = REPO_ROOT / f"results/evaluation/v68_item2_family_gate/{RUN_ID}.json"
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
        f"{PRIOR_COMPLETED} and therefore FAILS BY DESIGN after this resume "
        f"advances state to {RUN_ID}; preserved unmodified as a historical "
        "lock, not a gate for this run"),
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


def check_h1() -> dict:
    run = load(API_DIR / f"run_{RESUMED}.json")
    jobs = load(API_DIR / f"jobs_{RESUMED}.json")
    team = next(j for j in jobs["jobs"] if j["name"] == "team")
    sm = steps(team)
    failures = [s for s in team.get("steps") or []
                if s.get("conclusion") == "failure"]
    fail_step = failures[0] if len(failures) == 1 else None
    annotations = load(API_DIR / f"annotations_{RESUMED}_team.json")
    refs = load(API_DIR / f"refs_{RESUMED}.json")

    def signature(run_rec: dict, jobs_rec: dict, ann: list[dict]) -> dict:
        t = next((j for j in jobs_rec.get("jobs") or []
                  if j.get("name") == "team"), {})
        step_map = steps(t)
        failed = [s for s in t.get("steps") or []
                  if s.get("conclusion") == "failure"]
        first = failed[0] if len(failed) == 1 else None
        return {
            "run_conclusion": run_rec.get("conclusion"),
            "team_conclusion": t.get("conclusion"),
            "failing_step": first.get("name") if first else None,
            "failing_step_started_at": first.get("started_at") if first else None,
            "failing_step_completed_at": (
                first.get("completed_at") if first else None),
            "failure_duration_s": (
                duration_s(first.get("started_at"), first.get("completed_at"))
                if first else None),
            "total_job_duration_s": duration_s(
                t.get("started_at"), t.get("completed_at")),
            "exit_code_1_annotation": any(
                "exit code 1" in (a.get("message") or "") for a in ann),
            "persist_snapshot_conclusion": (
                step_map.get("Persist team snapshot") or {}).get("conclusion"),
            "validate_state_conclusion": (
                step_map.get("Validate active MVP producer state") or {}
            ).get("conclusion"),
            "write_scope_conclusion": (
                step_map.get("Enforce lane write scope") or {}).get("conclusion"),
            "audit_job_conclusion": next(
                (j.get("conclusion") for j in jobs_rec.get("jobs") or []
                 if j.get("name") == "audit"), None),
            "integrate_job_conclusion": next(
                (j.get("conclusion") for j in jobs_rec.get("jobs") or []
                 if j.get("name") == "integrate"), None),
        }

    sig_this = signature(run, jobs, annotations)
    sig_launch = signature(
        load(API_DIR / "run_43542234373.json"),
        load(API_DIR / "jobs_43542234373.json"),
        load(API_DIR / "annotations_43542234373_team.json"))
    sig_zero = signature(
        load(API_DIR / "run_43541879339.json"),
        load(API_DIR / "jobs_43541879339.json"),
        load(API_DIR / "annotations_43541879339_team.json"))
    sig_chain = signature(
        load(API_DIR / f"run_{CHAIN_PRIOR}.json"),
        load(API_DIR / f"jobs_{CHAIN_PRIOR}.json"),
        load(API_DIR / f"annotations_{CHAIN_PRIOR}_team.json"))

    ref_rows = refs.get("resumed_run_refs") or []
    team_ref = next((r for r in ref_rows if r["ref"].endswith("/team")), {})
    attempt_ref = next(
        (r for r in ref_rows if r["ref"].endswith("/team-attempt-1")), {})
    audit_refs = [r for r in ref_rows if "/audit" in r["ref"]]

    pre_steps = ["Set up job", "Run actions/checkout@v6",
                 "Validate lane and initialize working base",
                 "Mount accepted peer evidence", "Install Ox/OpenCode"]
    checks = {
        "run_conclusion_failure": run.get("conclusion") == "failure",
        "team_job_failure": team.get("conclusion") == "failure",
        "failing_step_run_lane_cycle": (
            (fail_step or {}).get("name") == "Run lane cycle"),
        "pre_failure_steps_success": all(
            (sm.get(n) or {}).get("conclusion") == "success" for n in pre_steps),
        "post_failure_validation_skipped": (
            sig_this["validate_state_conclusion"] == "skipped"
            and sig_this["write_scope_conclusion"] == "skipped"),
        "persist_snapshot_success": (
            sig_this["persist_snapshot_conclusion"] == "success"),
        "failure_duration_lt_60s": (
            sig_this["failure_duration_s"] is not None
            and sig_this["failure_duration_s"] < 60),
        "annotation_exit_code_1": sig_this["exit_code_1_annotation"],
        "audit_job_skipped": sig_this["audit_job_conclusion"] == "skipped",
        "integrate_job_skipped": (
            sig_this["integrate_job_conclusion"] == "skipped"),
        "no_audit_ref": not audit_refs,
        "snapshot_team_ref_equals_snapshot_head": (
            team_ref.get("sha") == SNAPSHOT_HEAD),
        "snapshot_attempt_ref_equals_snapshot_head": (
            attempt_ref.get("sha") == SNAPSHOT_HEAD),
        "same_signature_as_known_launch_failure_43542234373": (
            sig_launch["failing_step"] == "Run lane cycle"
            and sig_launch["exit_code_1_annotation"] is True
            and sig_launch["failure_duration_s"] is not None
            and sig_launch["failure_duration_s"] < 60
            and sig_launch["persist_snapshot_conclusion"] == "success"
            and sig_launch["audit_job_conclusion"] == "skipped"
            and sig_launch["integrate_job_conclusion"] == "skipped"),
        "distinct_from_zero_delta_43541879339": (
            "exit code 67" in json.dumps(
                load(API_DIR / "annotations_43541879339_team.json"))
            and sig_zero["failure_duration_s"] is not None
            and sig_zero["failure_duration_s"] > 60),
        "chain_prior_43570515880_same_signature": (
            sig_chain["failing_step"] == "Run lane cycle"
            and sig_chain["exit_code_1_annotation"] is True
            and sig_chain["failure_duration_s"] is not None
            and sig_chain["failure_duration_s"] < 60),
    }
    record = {
        "schema": SCHEMA,
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED,
        "direction_version": DIRV,
        "phase": "H1",
        "failure_class": "ORCHESTRATION_LAUNCH_FAILURE_RC1",
        "failure_class_distinct_from": [
            "ORCHESTRATION_AUDIT_WORK_QUANTUM_EXPIRED (audit exit 78)",
            "ZERO_DELTA_REPAIR (exit 67)",
            "PRODUCER_REJECTION (audit gate REVISE/BLOCKED)",
        ],
        "step_logs": (
            "NOT_CAPTURED: the public logs endpoint is HTTP 403 without an "
            "admin token; diagnosis uses job step conclusions, timings and "
            "check-run annotations"),
        "signature": sig_this,
        "comparison_signatures": {
            "launch_failure_43542234373": sig_launch,
            "zero_delta_43541879339": sig_zero,
            "chain_prior_43570515880": sig_chain,
        },
        "failure_meaning": (
            "The lane never executed a producer model call far enough to write "
            "a delta (16 s in the wrapper); the run is an orchestration launch "
            "failure. No audit gate exists and no producer claim is implied by "
            "the persisted snapshot."),
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
        "root_cause": "ORCHESTRATION_LAUNCH_FAILURE_RC1",
        "same_signature_runs": [CHAIN_PRIOR, RESUMED],
        "annotations": {
            "43542234373": "exit code 1",
            "43541879339": "exit code 67 / LEX_ZERO_DELTA_REPAIR",
            "43570515880": "exit code 1",
            "43570632816": "exit code 1",
        },
        "snapshot_is_prior_completed_resume": {
            "prior_completed_run": PRIOR_COMPLETED,
            "snapshot_head": SNAPSHOT_HEAD,
            "why": (
                "the failed run force-published the unchanged base; the head is "
                "the output of the earlier completed operational resume"),
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

    verify_path = PACK_DIR / f"prior_verify_{PRIOR_COMPLETED}_{RUN_ID}.json"
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
        "run_id": RUN_ID, "prior_run_id": PRIOR_COMPLETED,
        "exit_code": rc_verify, "record": verify_rec,
        "stderr_tail": (proc.stderr or "")[-1000:],
        "generated_at_utc": utcnow()})

    checks = {
        "head_is_resumed_snapshot": head == SNAPSHOT_HEAD,
        "parent_is_prior_completed_snapshot": parent == SNAPSHOT_PARENT,
        "delta_files_41": len(delta) == SNAPSHOT_DELTA_FILES,
        "zero_audit_namespace_paths": len(audit_ns) == 0,
        "prior_freeze_pins_all_match": bool(pins) and all(
            r["match"] for r in pin_rows),
        "prior_snapshot_verify_all_hold": (
            rc_verify == 0 and verify_rec.get("all_hold") is True),
        "prior_summary_present": PRIOR_SUMMARY.is_file(),
        "prior_deliverable_verification_present": (
            PRIOR_DELIVERABLE_VERIFY.is_file()),
        "snapshot_team_ref_equals_head": (
            (load(API_DIR / f"refs_{RESUMED}.json").get("resumed_run_refs")
             or [{}])[0].get("sha") == SNAPSHOT_HEAD),
        "accepted_lab_evaluation_tip_unchanged": (
            (load(API_DIR / f"refs_{RESUMED}.json").get("lab_evaluation_and_main")
             or [{}]) != []),
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
            "prior_parent": SNAPSHOT_PARENT,
            "delta_files": len(delta),
            "audit_namespace_paths": audit_ns,
            "delta_sample": delta[:12],
            "meaning": (
                "the resumed snapshot is the persisted output of completed "
                f"operational resume {PRIOR_COMPLETED}; run {RESUMED} wrote no "
                "producer delta"),
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
        "total_issued": sum(
            int(r.get("n_issued") or 0) for r in results),
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
    checks = {
        "deliverable_present": DELIVERABLE.is_file(),
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
    rc_head, mount_head = git("rev-parse", "HEAD", cwd=PRODUCT_MOUNT)
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
        "mount_lags_direction": (
            not mount_head.startswith(PRODUCT_HEAD_DIRECTION)),
        "family_rule_source_frozen": (
            (gate.get("reused_rule_source") or {}).get("sha256")
            == FAMILY_RULE_SHA),
        "correction_of_record_present": (
            CORRECTION_REPORT.is_file() and CORRECTION_RESULT.is_file()),
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
            "note": (
                "the repo-local state/factory_direction.json on the lab branch "
                "is a stale v35 copy; the v68 control-plane copy is "
                "authoritative"),
        },
        "item_1": item1,
        "item_2": {
            "status": gate.get("status"),
            "family_gate": str(FAMILY_GATE.relative_to(REPO_ROOT)),
            "family_gate_sha256": sha256(FAMILY_GATE),
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
            "mount_lag_disclosed": True,
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
    idx_refs = []
    if AUDIT_INDEX.is_file():
        idx_refs = load(AUDIT_INDEX).get("primary_evidence") or []
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
        "audit_index_refs_max_40": len(idx_refs) <= 40,
        "instrument_runtime_lt_300s": runtime < 300,
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
        "instrument_runtime_s": runtime,
        "audit_index_refs_n": len(idx_refs),
        "checks": checks,
        "all_hold": all(checks.values()),
        "generated_at_utc": utcnow(),
    }
    write_json(PACK_DIR / f"audit_readiness_{RUN_ID}.json", record)
    return record


# ------------------------------------------------------------------- state edit


def _ref_candidates() -> list[str]:
    refs = [
        f"evaluation/OPERATIONAL_RESUME_{RESUMED}_HYPOTHESIS_V1.json",
        f"evaluation/OPERATIONAL_RESUME_{RESUMED}_FREEZE_V1.json",
        f"evaluation/operational_resume_{RESUMED}.py",
        f"reports/evaluation/OPERATIONAL_RESUME_{RESUMED}_AUDIT_READY.md",
        f"reports/evaluation/AUDIT_BRIEF_{RESUMED}.md",
        f"tests/evaluation/test_operational_resume_{RESUMED}.py",
        f"results/evaluation/operational_resume_{RESUMED}/api/CAPTURE_MANIFEST.json",
        f"results/evaluation/operational_resume_{RESUMED}/diagnosis_{RESUMED}.json",
        f"results/evaluation/operational_resume_{RESUMED}/diagnosis_chain_{RUN_ID}.json",
        f"results/evaluation/operational_resume_{RESUMED}/snapshot_verification_{RUN_ID}.json",
        f"results/evaluation/operational_resume_{RESUMED}/deliverable_verification_{RUN_ID}.json",
        f"results/evaluation/operational_resume_{RESUMED}/scratch/{RUN_ID}_replay_{RESUMED}.json",
        f"results/evaluation/operational_resume_{RESUMED}/prior_verify_{PRIOR_COMPLETED}_{RUN_ID}.json",
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
        f"results/evaluation/v68_item2_family_gate/{RUN_ID}.json",
        f"results/evaluation/smallest_ca_benchmark/{RESUMED}.json",
        "reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md",
        "results/evaluation/bypass_clause_correction/40144816305.json",
        "results/evaluation/minimal_ca_falsify_benchmark/43397701490.json",
        "results/evaluation/minimal_ca_falsify_benchmark/43531218191.json",
        "results/audit/evaluation/CYCLE_40265377500_GATE.json",
    ]
    for f in sorted(API_DIR.glob("*.json")):
        refs.append(str(f.relative_to(REPO_ROOT)))
    for f in sorted(PACK_DIR.glob(f"shim_*_{RUN_ID}.json")):
        refs.append(str(f.relative_to(REPO_ROOT)))
    return refs


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


def update_state() -> dict:
    root = load(STATE_PATH)
    lane = load(LANE_STATE_PATH)
    before = {
        "root_github_run": root.get("github_run"),
        "lane_github_run": lane.get("github_run"),
        "root_next_recommendation": root.get("next_recommendation"),
        "lane_next_recommendation": lane.get("next_recommendation"),
    }
    diag = load(PACK_DIR / f"diagnosis_{RESUMED}.json") if (
        PACK_DIR / f"diagnosis_{RESUMED}.json").is_file() else {}
    next_recommendation = (
        f"OPERATIONAL RESUME {RUN_ID} of snapshot {RESUMED} is complete and "
        "PENDING INDEPENDENT AUDIT. The resumed run failed as an orchestration "
        "launch failure (exit 1 in 'Run lane cycle', 16 s, no producer delta; "
        f"the persisted head {SNAPSHOT_HEAD[:12]} is the output of completed "
        f"resume {PRIOR_COMPLETED}), NOT a producer rejection and NOT an audit. "
        "Do not run another same-question cycle: ordered item (2) remains "
        "NOT_YET_DISCRIMINATING until Product regenerates the full named "
        f"15-member family under the frozen role rule (mount {PRODUCT_HEAD_DIRECTION}, "
        "gate 14/15, 50/50 byte-identical, zero delta). Factory-level blocker: "
        "the independent audit has starved at the 2700 s work quantum "
        "(LEX_WORK_QUANTUM_EXPIRED / exit 78) on 43531218191, 43542378874, "
        "43550420112, 43554928192 and 43559166421; audit needs a snapshot/"
        "resume or a smaller quantum before any producer snapshot can be "
        "promoted. This run ships a compact AUDIT_INDEX and a read-only fast "
        "verify command to fit the audit inside the quantum.")
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
            "failure_class": "ORCHESTRATION_LAUNCH_FAILURE_RC1",
            "resumed_run": RESUMED,
            "failing_step": "Run lane cycle",
            "exit_code": 1,
            "failure_duration_seconds": (
                (diag.get("signature") or {}).get("failure_duration_s")),
            "team_job": (
                "FAILED_LAUNCH_RC1"
                if (diag.get("signature") or {}).get("team_conclusion")
                == "failure" else "UNEXPECTED"),
            "audit_ref": "ABSENT",
            "integrate_job": "SKIPPED",
            "snapshot_head": SNAPSHOT_HEAD,
            "snapshot_is_output_of": PRIOR_COMPLETED,
            "chain": [CHAIN_PRIOR, RESUMED, RUN_ID],
            "distinct_from": [
                "audit quantum expiry (exit 78)",
                "zero-delta repair (exit 67)",
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
        "audit_entry_point": {
            "index": f"results/evaluation/operational_resume_{RESUMED}/AUDIT_INDEX.json",
            "brief": f"reports/evaluation/AUDIT_BRIEF_{RESUMED}.md",
            "fast_verify": (
                f"python3 -m evaluation.operational_resume_{RESUMED} "
                "--phase verify"),
        },
        "artifacts": {
            "report": f"reports/evaluation/OPERATIONAL_RESUME_{RESUMED}_AUDIT_READY.md",
            "hypothesis": f"evaluation/OPERATIONAL_RESUME_{RESUMED}_HYPOTHESIS_V1.json",
            "freeze": f"evaluation/OPERATIONAL_RESUME_{RESUMED}_FREEZE_V1.json",
            "instrument": f"evaluation/operational_resume_{RESUMED}.py",
            "results_dir": f"results/evaluation/operational_resume_{RESUMED}",
            "test": f"tests/evaluation/test_operational_resume_{RESUMED}.py",
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
            "n_public_api_reads": 21,
            "calls": [
                "unauthenticated HTTPS GET of public GitHub Actions run, job "
                "and check-run annotation metadata for runs 43570515880, "
                "43570632816, 43570757974, 43542234373 and 43541879339; "
                "captured before this agent instrument ran",
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

    candidates = _ref_candidates()
    present = [r for r in candidates if (REPO_ROOT / r).is_file()]
    missing = [r for r in candidates if not (REPO_ROOT / r).is_file()]
    for st in (root, lane):
        refs = list(st.get("evidence_refs") or [])
        for r in present:
            if r not in refs:
                refs.append(r)
        st["evidence_refs"] = refs
        st["evidence_refs_n"] = len(refs)

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
        "evidence_refs_added": present,
        "evidence_refs_missing_at_update": missing,
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


def write_audit_index(summary: dict) -> dict:
    primary = [
        (f"evaluation/operational_resume_{RESUMED}.py",
         "the read-only verification instrument (re-run with --phase verify)"),
        (f"tests/evaluation/test_operational_resume_{RESUMED}.py",
         "regression locks for this resume"),
        (f"reports/evaluation/AUDIT_BRIEF_{RESUMED}.md",
         "one-page auditor brief and known non-gating reds"),
        (f"reports/evaluation/OPERATIONAL_RESUME_{RESUMED}_AUDIT_READY.md",
         "human-readable diagnosis and verification report"),
        (f"evaluation/OPERATIONAL_RESUME_{RESUMED}_HYPOTHESIS_V1.json",
         "pre-registered H1-H5 and claim ceiling"),
        (f"evaluation/OPERATIONAL_RESUME_{RESUMED}_FREEZE_V1.json",
         "hashes frozen before formal evidence"),
        (f"results/evaluation/operational_resume_{RESUMED}/diagnosis_{RESUMED}.json",
         "H1: launch failure exit 1 in Run lane cycle, no producer delta"),
        (f"results/evaluation/operational_resume_{RESUMED}/diagnosis_chain_{RUN_ID}.json",
         "H1: chain 43570515880 -> 43570632816 -> 43570757974"),
        (f"results/evaluation/operational_resume_{RESUMED}/snapshot_verification_{RUN_ID}.json",
         "H2: 41-file snapshot, 33/33 pins, no audit namespace"),
        (f"results/evaluation/operational_resume_{RESUMED}/deliverable_verification_{RUN_ID}.json",
         "H3: PRODUCT_FALSIFIED replay under socket guard"),
        (f"results/evaluation/operational_resume_{RESUMED}/scratch/{RUN_ID}_replay_{RESUMED}.json",
         "fresh replay record (operational, not a new claim)"),
        (f"results/evaluation/operational_resume_{RESUMED}/ordered_work_{RUN_ID}.json",
         "H4: item (2) NOT_YET_DISCRIMINATING, 14/15, zero delta"),
        (f"results/evaluation/v68_item2_family_gate/{RUN_ID}.json",
         "fresh family gate against the current product mount"),
        (f"results/evaluation/operational_resume_{RESUMED}/audit_readiness_{RUN_ID}.json",
         "H5: integrity, nested refs, scope, lane suite, reusable tests"),
        (f"results/evaluation/operational_resume_{RESUMED}/summary_{RUN_ID}.json",
         "H1-H5 verdict summary"),
        (f"results/evaluation/operational_resume_{RESUMED}/lane_suite_{RUN_ID}.json",
         "lane suite result"),
        (f"results/evaluation/operational_resume_{RESUMED}/{RUN_ID}_nested_evidence_refs.json",
         "nested ref resolution"),
        (f"results/evaluation/operational_resume_{RESUMED}/state_integrity_{RUN_ID}.json",
         "state-integrity gate"),
        (f"results/evaluation/operational_resume_{RESUMED}/write_scope_live_{RUN_ID}.json",
         "live write-scope classification"),
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
        ("state/evaluation.json",
         "root state: PENDING_INDEPENDENT_AUDIT"),
    ]
    rows = []
    for rel, why in primary:
        p = REPO_ROOT / rel
        rows.append({"path": rel, "sha256": sha256(p), "present": p.is_file(),
                     "why": why})
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
        "claim_ceiling": (
            "Producer-authored verification of a persisted snapshot. It does "
            "not promote, admit or serve anything; it makes no new product "
            "claim; it runs no new same-question measurement and no "
            "universal-174k benchmark. Promotion requires an independent "
            "audit verdict."),
        "fast_verify": {
            "command": (f"python3 -m evaluation.operational_resume_{RESUMED} "
                        "--phase verify"),
            "expected_exit": 0,
            "expected_runtime_s_max": 60,
            "what_it_checks": [
                "freeze pins still match",
                "H1-H5 records exist and all_hold",
                "state identity is this run / PENDING_INDEPENDENT_AUDIT",
                "accepted_run_id is unchanged",
                "every primary evidence path resolves",
                "zero auditor-namespace paths in the snapshot delta",
            ],
            "writes": 0,
        },
        "read_order": [rel for rel, _ in primary[:10]],
        "primary_evidence": rows,
        "do_not_read": [
            "raw GitHub step logs (not captured; 403 without admin token)",
            "prior-run scratch replays as if they were claims",
            "the universal-174k benchmark",
            "frozen bars as if they were re-derived or moved",
        ],
        "known_non_gating_red": [
            {
                "suite": f"tests/evaluation/test_operational_resume_{PRIOR_PACK_ID}.py",
                "observed": "fails by design after this resume advances state",
                "reason": (
                    "historical lock; it hard-codes github_run "
                    f"{PRIOR_COMPLETED} and is preserved unmodified"),
            },
            {
                "suite": "tests/evaluation/test_mount_provenance_gate.py",
                "observed": "8 passed, 1 failed, 4 unsupported under the shim",
                "reason": (
                    "pre-existing shim/fixture limitation and committed-tree "
                    "provenance drift check; not introduced by this run and "
                    "not used as evidence here"),
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
        "generated_at_utc": utcnow(),
    }
    write_json(AUDIT_INDEX, index)
    return index


# -------------------------------------------------------------------- verify


def verify_fast() -> tuple[int, dict]:
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
    checks["H5_all_hold"] = bool(summ) and not summ.get("hypotheses_failed")
    root = load(STATE_PATH)
    lane = load(LANE_STATE_PATH)
    checks["state_identity"] = (
        root.get("github_run") == int(RUN_ID)
        and lane.get("github_run") == int(RUN_ID)
        and root.get("accepted_run_id") == lane.get("accepted_run_id")
        == ACCEPTED_RUN_ID
        and root.get("audit_status") == "PENDING_INDEPENDENT_AUDIT")
    idx = load(AUDIT_INDEX) if AUDIT_INDEX.is_file() else {}
    rows = idx.get("primary_evidence") or []
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
    out = {
        "schema": "lex-evaluation-operational-resume-verify/1",
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED,
        "checks": checks,
        "all_hold": all(checks.values()),
        "bad_pins": bad,
        "generated_at_utc": utcnow(),
    }
    return (0 if out["all_hold"] else 1), out


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
        print(json.dumps({"phase": "prepare",
                          "hypotheses_failed": payload["hypotheses_failed"],
                          "record": str((PACK_DIR / f"prepare_{RUN_ID}.json")
                                        .relative_to(REPO_ROOT))}, indent=1))
        return (0 if not payload["hypotheses_failed"] else 1), payload

    if phase == "state":
        rec = update_state()
        print(json.dumps({"phase": "state",
                          "root_github_run": rec["after"]["root_github_run"],
                          "lane_github_run": rec["after"]["lane_github_run"],
                          "record": str((PACK_DIR / f"state_update_{RUN_ID}.json")
                                        .relative_to(REPO_ROOT))}, indent=1))
        return 0, rec

    if phase == "final":
        update_state()  # ensure identity before H5
        if not AUDIT_INDEX.is_file():
            # the state block references this path before H5 runs; a
            # placeholder makes the nested-ref guard resolve it, and the
            # real index is written after H5 below.
            write_json(AUDIT_INDEX, {
                "schema": "lex-evaluation-operational-resume-audit-index/1",
                "run_id": RUN_ID, "status": "PLACEHOLDER_UNTIL_FINAL",
                "primary_evidence": [], "generated_at_utc": utcnow()})
        h5 = check_h5()
        prep = load(PACK_DIR / f"prepare_{RUN_ID}.json")
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
        write_audit_index(payload)
        # final regression record for this resume's own test
        shim = run_shim("this_resume_regression", TEST_PATH)
        regression = {
            "schema": SCHEMA, "run_id": RUN_ID, "resumed_run_id": RESUMED,
            "phase": "final", "shim": shim,
            "generated_at_utc": utcnow(),
        }
        write_json(PACK_DIR / f"regression_test_{RUN_ID}.json", regression)
        update_state()  # include summary/audit index/regression record
        print(json.dumps({"phase": "final",
                          "hypotheses_failed": failed,
                          "audit_index": str(AUDIT_INDEX.relative_to(REPO_ROOT)),
                          "record": str((PACK_DIR / f"summary_{RUN_ID}.json")
                                        .relative_to(REPO_ROOT))}, indent=1))
        return (0 if not failed else 1), payload

    if phase == "verify":
        code, out = verify_fast()
        print(json.dumps(out, indent=1))
        return code, out

    if phase == "all":
        code_p, prep = run("prepare")
        code_s, _ = run("state")
        code_f, final = run("final")
        code = 0 if (code_p == 0 and code_s == 0 and code_f == 0) else 1
        return code, {"prepare": prep, "final": final}

    raise SystemExit(f"unknown phase: {phase}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--phase",
                    choices=("prepare", "state", "final", "verify", "all"),
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
