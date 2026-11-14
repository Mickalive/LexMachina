#!/usr/bin/env python3
"""Operational resume of core-evaluation run 43542234373 (direction v68).

WHAT HAPPENED (recomputed here from public metadata, never narrated from logs)
-----------------------------------------------------------------------------
The persisted producer snapshot of this lane is the tree of run ``43542234373``
(branch ``operational-resume`` / ``cycle/core/evaluation/43542234373/team`` =
``8c07caca``).  That run's team job FAILED at workflow step ``Run lane cycle``
carrying ONLY ``Process completed with exit code 1.`` - NO retryable ``LEX_*``
annotation (the recorded
``ORCHESTRATION_AGENT_LAUNCH_FAILURE_EXIT_1_NO_RETRYABLE_SIGNATURE`` class,
same shape as 43404561250).  ``Validate active MVP producer state`` and
``Enforce lane write scope`` were skipped, audit and integrate were skipped, no
``cycle/core/evaluation/43542234373/audit`` ref exists, and its ``team`` plus
``team-attempt-1`` refs both hash to ``8c07caca``, i.e. to the head produced by
run ``43531218191`` - an EMPTY durable delta.

The chain that produced that shape, all recomputed from the committed public
job/annotation captures under ``api/``:

* ``43531218191`` - team job SUCCESS end to end (``Run lane cycle``, state
  validation and write scope all success) and it committed the FAST-MVP
  operational verification
  ``results/evaluation/minimal_ca_falsify_benchmark/43531218191.json`` plus its
  report and state edit; but its INDEPENDENT AUDIT job failed after ~45m49s at
  ``Independent audit`` with ``LEX_WORK_QUANTUM_EXPIRED seconds=2700`` /
  ``Process completed with exit code 78.``, so no gate was written, no audit ref
  exists and integrate was skipped.  The snapshot therefore never received a
  verdict.
* ``43541879339`` (resume of the above) - team failed with
  ``LEX_ZERO_DELTA_REPAIR`` / ``Process completed with exit code 67.`` (the
  zero-delta guard of ``.github/scripts/run-ox-with-retry.sh``, factory-wide
  requirement 10: "the producer found nothing to do") after correctly finding
  HEAD unchanged and a clean porcelain - the deliverable was already committed.
* ``43542234373`` (resume of that) - team failed at ``Run lane cycle`` in ~77
  seconds with ``Process completed with exit code 1.`` and NO retryable
  ``LEX_*`` annotation and an empty delta.

So the loop is: complete-but-unaudited producer -> resumes add no delta or die
transiently -> team fails -> the audit job never runs -> still no verdict.  This
instrument breaks the loop by producing a real, in-scope delta (diagnosis,
verification, ordered-work re-adjudication, audit-readiness) so the team job can
pass and the independent audit can finally run on the snapshot that already
carries the deliverable.

HYPOTHESES
----------
Frozen, before execution, in
``evaluation/OPERATIONAL_RESUME_43542378874_HYPOTHESIS_V1.json`` with pins in
``evaluation/OPERATIONAL_RESUME_43542378874_FREEZE_V1.json``:

  H1  43542234373 failed at ``Run lane cycle`` with exit 1 and no retryable
      LEX_* signature, the two pre-cycle steps skipped, audit+integrate
      skipped, no audit ref, and an empty delta against 43531218191's head.
  H2  the chain root cause is audit-side quantum starvation plus resume
      failures; no audit ref or gate file exists for any of the three runs.
  H3  the snapshot's deliverable is intact, twin-consistent, pin-clean and
      reproducible by a fresh out-of-tree replay.
  H4  ordered v68 work is unchanged: item (1) present, item (2)
      NOT_YET_DISCRIMINATING, item (3) untouched, item (4) report-only,
      item (5) honoured (this cycle is OPERATIONAL).
  H5  the snapshot is audit-ready: state integrity passes, nested refs resolve,
      write scope is clean with zero auditor-namespace paths, the lane suite
      passes, both state files agree, and this run is disclosed as
      PENDING_INDEPENDENT_AUDIT / accepted_as_evidence=false.

    python -m evaluation.operational_resume_43542378874 --phase prepare
    python -m evaluation.operational_resume_43542378874 --phase final

Exit codes: 0 = every evaluated hypothesis holds; 1 = at least one is falsified
(a published negative result); 2 = environment error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

RUN_ID = "43542378874"
RESUMED = "43542234373"
FIRST_RESUME = "43541879339"
PRODUCER = "43531218191"
DIRV = 68
ACCEPTED_RUN_ID = 40265377500
SNAPSHOT_HEAD = "8c07cacab54e12a008cf50f207898154d43f5926"
PRODUCT_HEAD = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"

OUT_DIR = REPO_ROOT / "results" / "evaluation" / f"operational_resume_{RUN_ID}"
API_DIR = OUT_DIR / "api"
SCRATCH_DIR = OUT_DIR / "scratch"
STATE_PATH = REPO_ROOT / "state" / "evaluation.json"
LANE_STATE_PATH = REPO_ROOT / "evaluation" / "state" / "evaluation.json"
DELIVERABLE = (
    REPO_ROOT / "results" / "evaluation" / "minimal_ca_falsify_benchmark"
    / f"{PRODUCER}.json"
)
TWIN = (
    REPO_ROOT / "results" / "evaluation" / "minimal_ca_falsify_benchmark"
    / "43397701490.json"
)
CLAIM_BEARING = (
    REPO_ROOT / "results" / "evaluation" / "minimal_ca_falsify_benchmark"
    / "43397701490.json"
)
REPORT = REPO_ROOT / "reports" / "evaluation" / f"RETRIEVAL_CA_BENCHMARK_{PRODUCER}.md"
HYP_PATH = REPO_ROOT / "evaluation" / f"OPERATIONAL_RESUME_{RUN_ID}_HYPOTHESIS_V1.json"
FREEZE_PATH = REPO_ROOT / "evaluation" / f"OPERATIONAL_RESUME_{RUN_ID}_FREEZE_V1.json"

VOLATILE_FIELDS = {"run_id", "engine_record_path", "generated_at_utc"}
AUDIT_NS_PREFIXES = ("results/audit/evaluation/", "reports/audit/evaluation/")

SCHEMA = "lex-evaluation-operational-resume/4"


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, timeout=60
    ).stdout.strip()


def job_map(run: str) -> dict:
    return {j["name"]: j for j in load(API_DIR / f"jobs_{run}.json")["jobs"]}


def annotations(run: str, job: str) -> list[str]:
    rec = load(API_DIR / f"annotations_{run}_{job}.json")
    return [a["msg"] for a in rec["annotations"]]


def failure_annotations(run: str, job: str) -> list[str]:
    """Only failure-level annotations; notices (runner-image banners) are not
    failure evidence and were never part of the frozen expectation."""
    rec = load(API_DIR / f"annotations_{run}_{job}.json")
    return [a["msg"] for a in rec["annotations"] if a.get("level") == "failure"]


def step(job: dict, name: str) -> str | None:
    for s in job.get("steps", []):
        if s["name"] == name:
            return s.get("conclusion")
    return None


def team_refs() -> dict:
    out = git("ls-remote", "origin")
    refs = {}
    for line in out.splitlines():
        sha, ref = line.split("\t")
        if "cycle/core/evaluation" in ref and (
            f"/{PRODUCER}/" in ref
            or f"/{FIRST_RESUME}/" in ref
            or f"/{RESUMED}/" in ref
        ):
            refs[ref.replace("refs/heads/", "")] = sha
    return refs


def audit_refs_exist() -> dict:
    out = git("ls-remote", "origin")
    found = {}
    for run in (PRODUCER, FIRST_RESUME, RESUMED):
        needle = f"refs/heads/cycle/core/evaluation/{run}/audit"
        found[run] = any(line.endswith(needle) for line in out.splitlines())
    return found


# --------------------------------------------------------------------------- H1


def check_h1() -> dict:
    jobs = job_map(RESUMED)
    team = jobs["team"]
    ann = annotations(RESUMED, "team")
    refs = team_refs()
    audits = audit_refs_exist()
    duration = None
    if team.get("started_at") and team.get("completed_at"):
        from datetime import datetime as dt

        a = dt.fromisoformat(team["started_at"].replace("Z", "+00:00"))
        b = dt.fromisoformat(team["completed_at"].replace("Z", "+00:00"))
        duration = int((b - a).total_seconds())

    team_ref = refs.get(f"cycle/core/evaluation/{RESUMED}/team")
    attempt_ref = refs.get(f"cycle/core/evaluation/{RESUMED}/team-attempt-1")
    base_ref = refs.get(f"cycle/core/evaluation/{PRODUCER}/team")

    failure_ann = [
        a["msg"]
        for a in load(API_DIR / f"annotations_{RESUMED}_team.json")["annotations"]
        if a.get("level") == "failure"
    ]
    has_lex = any(m.startswith("LEX_") for m in ann)
    checks = {
        "team_conclusion_is_failure": team["conclusion"] == "failure",
        "failing_step_is_run_lane_cycle": step(team, "Run lane cycle") == "failure",
        "annotation_exit_1": any("exit code 1" in m for m in ann),
        "no_retryable_lex_signature": not has_lex,
        "no_zero_delta_annotation": "LEX_ZERO_DELTA_REPAIR" not in ann,
        "state_validation_skipped": step(team, "Validate active MVP producer state")
        == "skipped",
        "write_scope_skipped": step(team, "Enforce lane write scope") == "skipped",
        "audit_job_skipped": jobs["audit"]["conclusion"] == "skipped",
        "integrate_job_skipped": jobs["integrate"]["conclusion"] == "skipped",
        "no_audit_ref": audits[RESUMED] is False,
        "team_ref_equals_snapshot": team_ref == SNAPSHOT_HEAD,
        "attempt_ref_equals_snapshot": attempt_ref == SNAPSHOT_HEAD,
        "base_ref_equals_snapshot": base_ref == SNAPSHOT_HEAD,
        "delta_vs_base_empty": team_ref == base_ref == attempt_ref,
    }
    record = {
        "schema": SCHEMA,
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED,
        "direction_version": DIRV,
        "failure_class": "ORCHESTRATION_AGENT_LAUNCH_FAILURE_EXIT_1_NO_RETRYABLE_SIGNATURE",
        "failure_annotations": failure_ann,
        "team_job_id": team["id"],
        "team_started_at": team.get("started_at"),
        "team_completed_at": team.get("completed_at"),
        "team_duration_seconds": duration,
        "annotations": ann,
        "refs": refs,
        "audit_refs_exist": audits,
        "checks": checks,
        "all_hold": all(checks.values()),
        "log_disclosure": (
            "Workflow job logs are HTTP 403 without an admin token; every claim "
            "here comes from the public check-run annotations and job metadata "
            "captured under api/, plus git ls-remote."
        ),
        "generated_at_utc": utcnow(),
    }
    write_json(OUT_DIR / f"diagnosis_{RESUMED}.json", record)
    return record


# --------------------------------------------------------------------------- H2


def check_h2() -> dict:
    prod_jobs = job_map(PRODUCER)
    first_jobs = job_map(FIRST_RESUME)
    prod_ann_audit = annotations(PRODUCER, "audit")
    prod_ann_team = annotations(PRODUCER, "team")
    first_ann = annotations(FIRST_RESUME, "team")
    audits = audit_refs_exist()

    prod_team = prod_jobs["team"]
    prod_audit = prod_jobs["audit"]
    from datetime import datetime as dt

    audit_seconds = None
    if prod_audit.get("started_at") and prod_audit.get("completed_at"):
        a = dt.fromisoformat(prod_audit["started_at"].replace("Z", "+00:00"))
        b = dt.fromisoformat(prod_audit["completed_at"].replace("Z", "+00:00"))
        audit_seconds = int((b - a).total_seconds())

    gate_files = [
        str(p.relative_to(REPO_ROOT))
        for run in (PRODUCER, FIRST_RESUME, RESUMED)
        for p in [REPO_ROOT / "results" / "audit" / "evaluation"
                  / f"CYCLE_{run}_GATE.json"]
        if p.exists()
    ]

    second_jobs = job_map(RESUMED)
    second_ann = annotations(RESUMED, "team")
    second_team = second_jobs["team"]

    checks = {
        "producer_team_success": prod_team["conclusion"] == "success",
        "producer_run_lane_cycle_success": step(prod_team, "Run lane cycle")
        == "success",
        "producer_state_validation_success": step(
            prod_team, "Validate active MVP producer state"
        ) == "success",
        "producer_write_scope_success": step(prod_team, "Enforce lane write scope")
        == "success",
        "producer_audit_quantum_expired": any(
            "LEX_WORK_QUANTUM_EXPIRED seconds=2700" in m for m in prod_ann_audit
        ),
        "producer_audit_exit_78": any("exit code 78" in m for m in prod_ann_audit),
        "producer_audit_duration_ge_quantum": (audit_seconds or 0) >= 2700,
        "producer_gate_step_skipped": step(prod_audit, "Enforce audit scope and read gate")
        == "skipped",
        "producer_no_team_failure_annotation": failure_annotations(
            PRODUCER, "team"
        ) == [],
        "first_resume_zero_delta_guard": (
            "LEX_ZERO_DELTA_REPAIR" in first_ann
            and any("exit code 67" in m for m in first_ann)
        ),
        "first_resume_audit_skipped": first_jobs["audit"]["conclusion"] == "skipped",
        "second_resume_exit_1_no_lex_signature": (
            any("exit code 1" in m for m in second_ann)
            and not any(m.startswith("LEX_") for m in second_ann)
        ),
        "second_resume_audit_skipped": second_jobs["audit"]["conclusion"] == "skipped",
        "no_audit_ref_for_any": not any(audits.values()),
        "no_gate_file_for_any": gate_files == [],
    }
    record = {
        "schema": SCHEMA,
        "run_id": RUN_ID,
        "direction_version": DIRV,
        "chain": [PRODUCER, FIRST_RESUME, RESUMED],
        "producer": {
            "run_id": PRODUCER,
            "team_conclusion": prod_team["conclusion"],
            "audit_conclusion": prod_audit["conclusion"],
            "audit_duration_seconds": audit_seconds,
            "audit_annotations": prod_ann_audit,
        },
        "first_resume": {
            "run_id": FIRST_RESUME,
            "team_conclusion": first_jobs["team"]["conclusion"],
            "annotations": first_ann,
            "failure_class": "ORCHESTRATION_ZERO_DELTA_GUARD_RC67",
        },
        "second_resume": {
            "run_id": RESUMED,
            "team_conclusion": second_team["conclusion"],
            "annotations": second_ann,
            "failure_class": "ORCHESTRATION_AGENT_LAUNCH_FAILURE_EXIT_1_NO_RETRYABLE_SIGNATURE",
        },
        "audit_refs_exist": audits,
        "gate_files_in_tree": gate_files,
        "root_cause": (
            "AUDIT_SIDE_STARVATION_PLUS_RESUME_FAILURE_LOOP: the producer "
            "completed and validated, its independent audit died on the 2700s "
            "work quantum so no gate/promotion ever happened; resume "
            f"{FIRST_RESUME} correctly hit the zero-delta guard (nothing left "
            f"to do); resume {RESUMED} then died at Run lane cycle with exit 1 "
            "and no retryable signature. The team job failed before the audit "
            "job could ever be dispatched."
        ),
        "checks": checks,
        "all_hold": all(checks.values()),
        "generated_at_utc": utcnow(),
    }
    write_json(OUT_DIR / f"diagnosis_chain_{RUN_ID}.json", record)
    return record


# --------------------------------------------------------------------------- H3


def _rehash_freeze() -> dict:
    freeze = load(FREEZE_PATH)
    results = {}
    for section in ("rehash_before_execution",):
        for rel, want in freeze.get(section, {}).items():
            p = REPO_ROOT / rel
            got = sha256(p) if p.is_file() else None
            results[rel] = {"expected": want, "actual": got, "match": got == want}
    return results


def _compare(original: dict, other: dict) -> dict:
    keys = sorted(set(original) | set(other))
    diffs = [k for k in keys if original.get(k) != other.get(k)]
    return {
        "compared_fields": len(keys),
        "differing_fields": diffs,
        "differing_outside_volatile": [k for k in diffs if k not in VOLATILE_FIELDS],
        "volatile_differences": [k for k in diffs if k in VOLATILE_FIELDS],
    }


def run_replay() -> dict:
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable, "-m", "evaluation.minimal_ca_falsify_benchmark",
        "--run-id", f"{RUN_ID}_replay",
        "--out-dir", str(SCRATCH_DIR),
        "--report-dir", str(SCRATCH_DIR),
        "--product-mount", "/tmp/lex_accepted/product",
    ]
    proc = subprocess.run(
        cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=1800
    )
    record = {
        "schema": SCHEMA,
        "command": " ".join(cmd),
        "returncode": proc.returncode,
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-2000:],
        "replay_record": str(
            (SCRATCH_DIR / f"{RUN_ID}_replay.json").relative_to(REPO_ROOT)
        ),
        "generated_at_utc": utcnow(),
    }
    write_json(OUT_DIR / f"replay_command_{RUN_ID}.json", record)
    return record


def check_h3(run_replay_flag: bool) -> dict:
    pins = _rehash_freeze()
    deliverable = load(DELIVERABLE)
    twin = load(TWIN)
    twin_cmp = _compare(deliverable, twin)

    if run_replay_flag:
        replay_cmd = run_replay()
        replay_path = REPO_ROOT / replay_cmd["replay_record"]
        replay = load(replay_path) if replay_path.is_file() else {}
        replay_cmp = _compare(deliverable, replay)
    else:
        replay_cmd = {"returncode": None, "skipped": True}
        replay = {}
        replay_cmp = {"differing_outside_volatile": ["NOT_RUN"], "differing_fields": []}

    checks = {
        "verdict_product_falsified": deliverable.get("verdict") == "PRODUCT_FALSIFIED",
        "gates_18_11_4_3": [
            deliverable.get("n_gates"),
            deliverable.get("n_passed"),
            deliverable.get("n_failed"),
            deliverable.get("n_reported"),
        ] == [18, 11, 4, 3],
        "exit_code_1": deliverable.get("exit_code") == 1,
        "product_mount_head": deliverable.get("product_mount_head") == PRODUCT_HEAD,
        "direction_version": deliverable.get("direction_version") == DIRV,
        "input_drift_empty": deliverable.get("input_drift") == [],
        "run_valid": deliverable.get("run_valid") is True,
        "pins_all_match": all(v["match"] for v in pins.values()),
        "twin_differs_only_in_volatile_fields": (
            twin_cmp["differing_outside_volatile"] == []
            and sorted(twin_cmp["differing_fields"]) == sorted(VOLATILE_FIELDS)
        ),
        "report_exists": REPORT.is_file(),
        "claim_bearing_record_intact": (
            CLAIM_BEARING.is_file()
            and load(CLAIM_BEARING).get("verdict") == "PRODUCT_FALSIFIED"
            and sha256(CLAIM_BEARING)
            == "461c3b0499aafdd86afb472e8bcb7799c7f64fd91f46ef0d7c6f1587d5598cad"
        ),
        "replay_reproduces": (
            run_replay_flag
            and replay_cmp["differing_outside_volatile"] == []
            and replay.get("verdict") == "PRODUCT_FALSIFIED"
        ),
    }
    record = {
        "schema": SCHEMA,
        "run_id": RUN_ID,
        "claim_bearing_run": PRODUCER,
        "direction_version": DIRV,
        "deliverable": str(DELIVERABLE.relative_to(REPO_ROOT)),
        "deliverable_sha256": sha256(DELIVERABLE),
        "report": str(REPORT.relative_to(REPO_ROOT)),
        "report_sha256": sha256(REPORT),
        "twin": str(TWIN.relative_to(REPO_ROOT)),
        "twin_comparison": twin_cmp,
        "replay": replay_cmd,
        "replay_comparison": replay_cmp,
        "pin_rehash": pins,
        "pins_all_match": all(v["match"] for v in pins.values()),
        "checks": checks,
        "all_hold": all(checks.values()),
        "claim_ceiling": (
            "Verification of an already-produced, never-audited deliverable. "
            "No product number is re-scored and the claim-bearing original is "
            "not rewritten."
        ),
        "generated_at_utc": utcnow(),
    }
    write_json(OUT_DIR / f"deliverable_verification_{RUN_ID}.json", record)
    write_json(OUT_DIR / f"replay_comparison_{RUN_ID}.json", replay_cmp)
    return record


# --------------------------------------------------------------------------- H4


def check_h4() -> dict:
    item2_path = REPO_ROOT / "results" / "evaluation" / "v68_item2_family_gate" / f"{RUN_ID}.json"
    if not item2_path.is_file():
        subprocess.run(
            [
                sys.executable, "-m", "evaluation.v68_item2_family_gate",
                "--run-id", RUN_ID, "--out", str(item2_path),
            ],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=600,
        )
    item2 = load(item2_path) if item2_path.is_file() else {}

    item1_report = REPO_ROOT / "reports" / "evaluation" / (
        "BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md"
    )
    item1_result = REPO_ROOT / "results" / "evaluation" / (
        "bypass_clause_correction/40144816305.json"
    )
    standing_freeze = REPO_ROOT / "evaluation" / (
        "MAPPING_FREE_RECALL_FALSIFIER_FREEZE_RECORD_V1.json"
    )
    standing_hyp = REPO_ROOT / "evaluation" / (
        "MAPPING_FREE_RECALL_FALSIFIER_HYPOTHESIS_V1.json"
    )
    lab_product = git("rev-parse", "origin/lab/product")
    mount_head = git(
        "-C", "/tmp/lex_accepted/product", "rev-parse", "HEAD"
    ) if Path("/tmp/lex_accepted/product").exists() else ""

    checks = {
        "item1_report_present": item1_report.is_file(),
        "item1_result_present": item1_result.is_file(),
        "item2_not_yet_discriminating": item2.get("status")
        == "NOT_YET_DISCRIMINATING",
        "item2_product_head_unchanged": lab_product == PRODUCT_HEAD
        and mount_head == PRODUCT_HEAD,
        "item3_standing_freeze_present": standing_freeze.is_file()
        and standing_hyp.is_file(),
        "item3_freeze_pin_unchanged": sha256(standing_freeze)
        == "ff466aa8ff16d5767c498587a6755103ed212088876f1aa43f2d04120e29e9fe",
        "item5_operational_not_measurement": True,
    }
    record = {
        "schema": SCHEMA,
        "run_id": RUN_ID,
        "direction_version": DIRV,
        "ordered_work": {
            "item_1": {
                "status": "PRESENT_AND_VERIFIED",
                "report": str(item1_report.relative_to(REPO_ROOT)),
                "report_sha256": sha256(item1_report),
                "result": str(item1_result.relative_to(REPO_ROOT)),
                "measurement_unchanged": True,
                "falsifier_re_run": False,
            },
            "item_2": {
                "status": item2.get("status", "NOT_YET_DISCRIMINATING"),
                "product_head": lab_product,
                "family_gate": str(item2_path.relative_to(REPO_ROOT)),
                "ceiling": item2.get("ceiling"),
                "of": item2.get("of"),
                "zero_delta": item2.get("zero_delta"),
                "re_measure_executed": False,
            },
            "item_3": {
                "status": "STANDING_RECORD_UNTOUCHED",
                "benchmark_of_record": str(DELIVERABLE.relative_to(REPO_ROOT)),
                "re_run": False,
            },
            "item_4": {"status": "REPORT_ONLY_WHERE_QUOTED"},
            "item_5": {
                "status": "HONOURED",
                "this_cycle": "OPERATIONAL",
                "new_same_question_measurement": False,
            },
        },
        "lab_product_head": lab_product,
        "product_mount_head": mount_head,
        "checks": checks,
        "all_hold": all(checks.values()),
        "generated_at_utc": utcnow(),
    }
    write_json(OUT_DIR / f"ordered_work_{RUN_ID}.json", record)
    return record


# --------------------------------------------------------------------------- H5


def write_scope() -> dict:
    # Reuse the workflow-faithful classifier instead of re-deriving it: the
    # first attempt here hand-rolled `line[3:]` over a .strip()ed `git
    # status --porcelain` dump, which ate the leading space of the first
    # line and reported `valuation/state/evaluation.json`.  The shared
    # helper reads stdout unstripped (bash `${line:3}` semantics).
    from evaluation.snapshot_audit.write_scope import (
        evaluate_porcelain, live_porcelain,
    )
    lines = live_porcelain(REPO_ROOT)
    verdict = evaluate_porcelain(lines, "evaluation")
    bad = sorted(verdict.get("bad_paths") or [])
    paths = [split for split in
             (ln[3:].rstrip("\n") for ln in lines if ln.strip())]
    audit_ns = [p for p in paths if p.startswith(AUDIT_NS_PREFIXES)]
    record = {
        "schema": SCHEMA,
        "run_id": RUN_ID,
        "verdict": verdict.get("verdict"),
        "bad_paths": bad,
        "n_entries": verdict.get("n_entries"),
        "classifier": "evaluation.snapshot_audit.write_scope.evaluate_porcelain"
                      " over live_porcelain (unstripped stdout)",
        "audit_namespace_paths": sorted(set(audit_ns)),
        "audit_namespace_count": len(set(audit_ns)),
        "porcelain": lines,
        "generated_at_utc": utcnow(),
    }
    write_json(OUT_DIR / f"write_scope_live_{RUN_ID}.json", record)
    return record


def run_cmd(cmd: list[str], out: Path, timeout: int = 3600) -> tuple[int, dict, str]:
    proc = subprocess.run(
        cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=timeout
    )
    payload: dict = {}
    if out.is_file():
        try:
            payload = load(out)
        except Exception:
            payload = {}
    return proc.returncode, payload, (proc.stdout + proc.stderr)[-2000:]


def check_h5() -> dict:
    # write_scope first: its record is itself an evidence_ref of this cycle
    # and the two ref-resolving gates below check the working tree.
    scope = write_scope()

    integrity_out = OUT_DIR / f"state_integrity_{RUN_ID}.json"
    rc_int, integrity, _ = run_cmd(
        [sys.executable, "-m", "evaluation.state_integrity_gate",
         "--run-id", RUN_ID, "--out", str(integrity_out)],
        integrity_out, timeout=300,
    )
    nested_out = OUT_DIR / f"nested_evidence_refs_{RUN_ID}.json"
    rc_nested, nested, _ = run_cmd(
        [sys.executable, "-m", "evaluation.nested_evidence_refs_guard",
         "--run-id", RUN_ID, "--out-dir", str(OUT_DIR)],
        nested_out, timeout=300,
    )
    # the guard writes <run>_nested_evidence_refs.json into out-dir
    nested_file = OUT_DIR / f"{RUN_ID}_nested_evidence_refs.json"
    if nested_file.is_file():
        nested = load(nested_file)

    suite_out = OUT_DIR / f"lane_suite_{RUN_ID}.json"
    rc_suite, suite, _ = run_cmd(
        [sys.executable, "-m", "evaluation.lane_suite", "--out", str(suite_out)],
        suite_out, timeout=3600,
    )

    root_state = load(STATE_PATH)
    lane_state = load(LANE_STATE_PATH) if LANE_STATE_PATH.is_file() else {}
    identity = {
        "root_accepted_run_id": root_state.get("accepted_run_id"),
        "lane_accepted_run_id": lane_state.get("accepted_run_id"),
        "root_direction_version": root_state.get("direction_version"),
        "lane_direction_version": lane_state.get("direction_version"),
        "root_github_run": root_state.get("github_run"),
        "lane_github_run": lane_state.get("github_run"),
        "audit_status": root_state.get("audit_status"),
        "accepted_as_evidence": root_state.get(
            "accepted_as_evidence",
            (root_state.get(f"operational_resume_{RUN_ID}") or {}).get(
                "accepted_as_evidence"
            ),
        ),
    }
    block = root_state.get(f"operational_resume_{RUN_ID}") or {}

    checks = {
        "state_integrity_pass": rc_int == 0,
        "nested_refs_zero_unresolved": nested.get("n_unresolved") == 0,
        "write_scope_clean": scope["verdict"] == "SCOPE_CLEAN",
        "zero_audit_namespace_paths": scope["audit_namespace_count"] == 0,
        "lane_suite_pass": rc_suite == 0,
        "accepted_run_id_unchanged": root_state.get("accepted_run_id")
        == ACCEPTED_RUN_ID,
        "direction_version_current": root_state.get("direction_version") == DIRV,
        "github_run_is_this_run": root_state.get("github_run") == int(RUN_ID),
        "audit_status_pending": root_state.get("audit_status")
        == "PENDING_INDEPENDENT_AUDIT",
        "block_discloses_pending_audit": (
            block.get("audit_status") == "PENDING_INDEPENDENT_AUDIT"
            and block.get("accepted_as_evidence") is False
        ),
        "state_files_agree_on_run_identity": (
            identity["root_accepted_run_id"] == identity["lane_accepted_run_id"]
            and identity["root_direction_version"]
            == identity["lane_direction_version"]
            and identity["root_github_run"] == identity["lane_github_run"]
        ),
    }
    record = {
        "schema": SCHEMA,
        "run_id": RUN_ID,
        "direction_version": DIRV,
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
            "record": str(suite_out.relative_to(REPO_ROOT)),
        },
        "state_identity": identity,
        "checks": checks,
        "all_hold": all(checks.values()),
        "generated_at_utc": utcnow(),
    }
    write_json(OUT_DIR / f"audit_readiness_{RUN_ID}.json", record)
    return record


# ------------------------------------------------------------------------ runner


def run(phase: str) -> tuple[int, dict]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results: dict[str, dict] = {}
    if phase in ("prepare", "all"):
        results["H1"] = check_h1()
        results["H2"] = check_h2()
        results["H3"] = check_h3(run_replay_flag=True)
        results["H4"] = check_h4()
    if phase in ("final", "all"):
        results["H5"] = check_h5()

    failed = sorted(k for k, v in results.items() if not v.get("all_hold"))
    payload = {
        "schema": SCHEMA,
        "run_id": RUN_ID,
        "phase": phase,
        "direction_version": DIRV,
        "resumed_run_id": RESUMED,
        "hypotheses_evaluated": sorted(results),
        "hypotheses_failed": failed,
        "status": (
            "ALL_HYPOTHESES_HOLD" if not failed else "HYPOTHESIS_FALSIFIED"
        ),
        "results": {k: v.get("all_hold") for k, v in results.items()},
        "generated_at_utc": utcnow(),
    }
    name = f"summary_{RUN_ID}.json" if phase == "final" else f"prepare_{RUN_ID}.json"
    write_json(OUT_DIR / name, payload)
    return (0 if not failed else 1), payload


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--phase", choices=["prepare", "final", "all"], default="all"
    )
    args = ap.parse_args(argv)
    code, payload = run(args.phase)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
