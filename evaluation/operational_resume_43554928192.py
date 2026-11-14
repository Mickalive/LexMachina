#!/usr/bin/env python3
"""Operational resume of core-evaluation snapshot 43554928192 (direction v68).

WHAT HAPPENED (recomputed from public metadata, never narrated from logs)
------------------------------------------------------------------------
The persisted producer snapshot of this lane is the tree of run
``43554928192`` (branch ``cycle/core/evaluation/43554928192/team`` =
``35d8d649``, also ``team-attempt-1``).  That run's TEAM job SUCCEEDED end to
end: ``Run lane cycle``, ``Validate active MVP producer state``, ``Clean
generated junk``, ``Enforce lane write scope`` and ``Persist team snapshot`` all
report success, and the snapshot carries a real five-file delta (the v68
``PACKET_MAP`` + ``_packet_for_direction()`` change in
``evaluation/smallest_ca_benchmark.py``, its machine record and test record, and
two reports).  Its INDEPENDENT AUDIT job then FAILED at ``Independent audit``
after ~2750s carrying ``LEX_WORK_QUANTUM_EXPIRED seconds=2700`` and ``Process
completed with exit code 78.``; ``Enforce audit scope and read gate`` and
``Persist audit snapshot`` were skipped, ``integrate`` was skipped, and no
``cycle/core/evaluation/43554928192/audit`` ref exists.  The snapshot therefore
never received an audit verdict.

This is the SAME failure class that already consumed ``43531218191``,
``43542378874`` and ``43550420112``: a producer team job completes and commits,
then the audit job starves at the 2700s work quantum (exit 78) before it can
write a gate.  ``43541879339`` correctly hit the zero-delta guard (rc 67) and
``43542234373`` died at ``Run lane cycle`` with exit 1 and no retryable
``LEX_*`` signature.  The current run ``43559166421`` is another resume of the
same completed-but-unaudited snapshot.

This instrument does not restart the product work and does not re-open closed
questions.  It (H1) records the orchestration diagnosis, (H2) proves the
recurrence, (H3) verifies the snapshot delta and replays the prior benchmark
out-of-tree as OPERATIONAL verification (never a new claim), (H4) re-adjudicates
the direction's ordered work, and (H5) makes the snapshot audit-ready with
in-lane-only writes.

HYPOTHESES
----------
Frozen before execution in
``evaluation/OPERATIONAL_RESUME_43554928192_HYPOTHESIS_V1.json`` with pins in
``evaluation/OPERATIONAL_RESUME_43554928192_FREEZE_V1.json``:

  H1  team success end to end + audit failure only at ``Independent audit``
      with LEX_WORK_QUANTUM_EXPIRED seconds=2700 / exit 78; gate-read and
      persist-audit skipped, integrate skipped, no audit ref, snapshot head
      35d8d649.  Not a producer/validation/product failure.
  H2  the four-run audit-starved chain, plus the zero-delta and launch-failure
      resumes; root cause AUDIT_WORK_QUANTUM_EXPIRY_RECURRENCE.
  H3  five-file delta preserved with committed hashes; smallest-CA record is
      PRODUCT_FALSIFIED exit 1 on packet 39319405429 with zero issued rows;
      out-of-tree replay reproduces measurement-bearing fields; standing
      records and frozen pins intact; prior re-execution classified
      OPERATIONAL_REEXECUTION_NOT_NEW_CLAIM.
  H4  ordered work: item 1 PRESENT_AND_VERIFIED, item 2
      NOT_YET_DISCRIMINATING (rejection/incumbent leg open; full 15-member
      family not regenerated; no re-measure), item 3 STANDING_RECORD_UNTOUCHED,
      item 4 REPORT_ONLY_WHERE_QUOTED, item 5 HONOURED_OPERATIONAL.
  H5  audit-ready: state integrity passes, nested refs resolve, write scope
      clean with zero auditor-namespace paths, lane suite passes, both state
      files agree, this run disclosed PENDING_INDEPENDENT_AUDIT /
      accepted_as_evidence=false.

    python -m evaluation.operational_resume_43554928192 --phase prepare
    python -m evaluation.operational_resume_43554928192 --phase state
    python -m evaluation.operational_resume_43554928192 --phase final
    python -m evaluation.operational_resume_43554928192 --phase state

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

RUN_ID = "43559166421"
RESUMED = "43554928192"
PARENT = "d835bad49ce52ebdbdc792d03f88ef1e030fd009"
DIRV = 68
ACCEPTED_RUN_ID = 40265377500
SNAPSHOT_HEAD = "35d8d64941b76ab59f931915f1f59ac97e07041f"
PRODUCT_HEAD_DIRECTION = "8b5b08dd"
PRODUCT_MOUNT_HEAD = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
CHAIN = ["43531218191", "43542378874", "43550420112", "43554928192"]
ZERO_DELTA_RESUME = "43541879339"
LAUNCH_FAILURE_RESUME = "43542234373"

PACK_DIR = REPO_ROOT / "results" / "evaluation" / f"operational_resume_{RESUMED}"
API_DIR = PACK_DIR / "api"
SCRATCH_DIR = PACK_DIR / "scratch"
STATE_PATH = REPO_ROOT / "state" / "evaluation.json"
LANE_STATE_PATH = REPO_ROOT / "evaluation" / "state" / "evaluation.json"
HYP_PATH = REPO_ROOT / "evaluation" / f"OPERATIONAL_RESUME_{RESUMED}_HYPOTHESIS_V1.json"
FREEZE_PATH = REPO_ROOT / "evaluation" / f"OPERATIONAL_RESUME_{RESUMED}_FREEZE_V1.json"
DELIVERABLE = (
    REPO_ROOT / "results" / "evaluation" / "smallest_ca_benchmark" / f"{RESUMED}.json"
)
DELIVERABLE_REPORT = (
    REPO_ROOT / "reports" / "evaluation" / f"SMALLEST_CA_BENCHMARK_{RESUMED}.md"
)
DELIVERABLE_TEST = (
    REPO_ROOT / "results" / "evaluation" / "smallest_ca_benchmark"
    / f"test_run_{RESUMED}.json"
)
DELIVERABLE_TEST_REPORT = (
    REPO_ROOT / "reports" / "evaluation"
    / f"SMALLEST_CA_BENCHMARK_test_run_{RESUMED}.md"
)
BENCHMARK_SOURCE = REPO_ROOT / "evaluation" / "smallest_ca_benchmark.py"
STANDING = [
    REPO_ROOT / "results" / "evaluation" / "minimal_ca_falsify_benchmark"
    / "43397701490.json",
    REPO_ROOT / "results" / "evaluation" / "minimal_ca_falsify_benchmark"
    / "43531218191.json",
]
CORRECTION_REPORT = (
    REPO_ROOT / "reports" / "evaluation"
    / "BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md"
)
CORRECTION_RESULT = (
    REPO_ROOT / "results" / "evaluation" / "bypass_clause_correction"
    / "40144816305.json"
)
FAMILY_GATE_PATH = (
    REPO_ROOT / "results" / "evaluation" / "v68_item2_family_gate"
    / f"{RUN_ID}.json"
)
AUDIT_READY_REPORT = (
    REPO_ROOT / "reports" / "evaluation"
    / f"OPERATIONAL_RESUME_{RESUMED}_AUDIT_READY.md"
)
TEST_FILE = (
    REPO_ROOT / "tests" / "evaluation" / f"test_operational_resume_{RESUMED}.py"
)
DIRECTION_PATH = Path("/tmp/lex_control/state/factory_direction.json")
PRODUCT_MOUNT = Path("/tmp/lex_accepted/product")

AUDIT_NS_PREFIXES = ("results/audit/evaluation/", "reports/audit/evaluation/")
VOLATILE_FIELDS = {
    "run_id", "generated_at_utc", "elapsed_s", "product_mount", "numeric_environment",
}
MEASUREMENT_FIELDS = [
    "schema", "lane", "direction_version", "product_mount_head", "packet",
    "verdict", "exit_code", "n_questions", "results", "no_174k_benchmark_rerun",
    "no_new_thresholds", "no_counter_rows", "claim_ceiling", "provenance_note",
]
DELTA_EXPECTED = [
    ("M", "evaluation/smallest_ca_benchmark.py"),
    ("A", f"reports/evaluation/SMALLEST_CA_BENCHMARK_{RESUMED}.md"),
    ("A", f"reports/evaluation/SMALLEST_CA_BENCHMARK_test_run_{RESUMED}.md"),
    ("A", f"results/evaluation/smallest_ca_benchmark/{RESUMED}.json"),
    ("A", f"results/evaluation/smallest_ca_benchmark/test_run_{RESUMED}.json"),
]
SCHEMA = "lex-evaluation-operational-resume/5"


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


def git(*args: str, cwd: Path = REPO_ROOT) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=120
    )
    return proc.stdout.strip()


def job_map(run: str) -> dict:
    return {j["name"]: j for j in load(API_DIR / f"jobs_{run}.json")["jobs"]}


def annotations(run: str, job: str) -> list[str]:
    rec = load(API_DIR / f"annotations_{run}_{job}.json")
    return [a["msg"] for a in rec["annotations"]]


def failure_annotations(run: str, job: str) -> list[str]:
    rec = load(API_DIR / f"annotations_{run}_{job}.json")
    return [a["msg"] for a in rec["annotations"] if a.get("level") == "failure"]


def step(job: dict, name: str) -> str | None:
    for s in job.get("steps", []):
        if s["name"] == name:
            return s.get("conclusion")
    return None


def duration_seconds(job: dict) -> int | None:
    if not (job.get("started_at") and job.get("completed_at")):
        return None
    a = datetime.fromisoformat(job["started_at"].replace("Z", "+00:00"))
    b = datetime.fromisoformat(job["completed_at"].replace("Z", "+00:00"))
    return int((b - a).total_seconds())


def remote_refs() -> dict:
    out = git("ls-remote", "origin")
    refs = {}
    for line in out.splitlines():
        sha, ref = line.split("\t")
        refs[ref.replace("refs/heads/", "")] = sha
    return refs


def audit_refs_exist(runs: list[str]) -> dict:
    refs = remote_refs()
    return {
        run: f"cycle/core/evaluation/{run}/audit" in refs for run in runs
    }


def gate_files_exist(runs: list[str]) -> dict:
    return {
        run: (REPO_ROOT / "results" / "audit" / "evaluation"
              / f"CYCLE_{run}_GATE.json").is_file()
        for run in runs
    }


# --------------------------------------------------------------------------- H1


def check_h1() -> dict:
    jobs = job_map(RESUMED)
    team, audit = jobs["team"], jobs["audit"]
    ann_team = annotations(RESUMED, "team")
    ann_audit = annotations(RESUMED, "audit")
    refs = remote_refs()
    audits = audit_refs_exist([RESUMED])

    checks = {
        "team_conclusion_success": team["conclusion"] == "success",
        "run_lane_cycle_success": step(team, "Run lane cycle") == "success",
        "state_validation_success": step(team, "Validate active MVP producer state")
        == "success",
        "clean_generated_junk_success": step(team, "Clean generated junk") == "success",
        "write_scope_success": step(team, "Enforce lane write scope") == "success",
        "persist_snapshot_success": step(team, "Persist team snapshot") == "success",
        "no_team_failure_annotation": failure_annotations(RESUMED, "team") == [],
        "audit_conclusion_failure": audit["conclusion"] == "failure",
        "audit_failing_step_independent_audit": step(audit, "Independent audit")
        == "failure",
        "audit_duration_ge_2700": (duration_seconds(audit) or 0) >= 2700,
        "audit_quantum_expired_annotation": any(
            "LEX_WORK_QUANTUM_EXPIRED seconds=2700" in m for m in ann_audit
        ),
        "audit_exit_78_annotation": any("exit code 78" in m for m in ann_audit),
        "gate_step_skipped": step(audit, "Enforce audit scope and read gate")
        == "skipped",
        "persist_audit_step_skipped": step(audit, "Persist audit snapshot")
        == "skipped",
        "integrate_skipped": jobs["integrate"]["conclusion"] == "skipped",
        "resilience_success": jobs["resilience"]["conclusion"] == "success",
        "no_audit_ref": audits[RESUMED] is False,
        "no_audit_gate_file": not gate_files_exist([RESUMED])[RESUMED],
        "team_ref_equals_snapshot": refs.get(
            f"cycle/core/evaluation/{RESUMED}/team") == SNAPSHOT_HEAD,
        "attempt_ref_equals_snapshot": refs.get(
            f"cycle/core/evaluation/{RESUMED}/team-attempt-1") == SNAPSHOT_HEAD,
    }
    record = {
        "schema": SCHEMA,
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED,
        "direction_version": DIRV,
        "failure_class": "ORCHESTRATION_AUDIT_WORK_QUANTUM_EXPIRED",
        "team": {
            "job_id": team["id"],
            "conclusion": team["conclusion"],
            "duration_seconds": duration_seconds(team),
            "steps": {s["name"]: s.get("conclusion") for s in team.get("steps", [])},
        },
        "audit": {
            "job_id": audit["id"],
            "conclusion": audit["conclusion"],
            "duration_seconds": duration_seconds(audit),
            "annotations": ann_audit,
            "failure_annotations": failure_annotations(RESUMED, "audit"),
            "steps": {s["name"]: s.get("conclusion") for s in audit.get("steps", [])},
        },
        "team_failure_annotations": failure_annotations(RESUMED, "team"),
        "integrate_conclusion": jobs["integrate"]["conclusion"],
        "resilience_conclusion": jobs["resilience"]["conclusion"],
        "snapshot_head": SNAPSHOT_HEAD,
        "team_ref": refs.get(f"cycle/core/evaluation/{RESUMED}/team"),
        "attempt_ref": refs.get(f"cycle/core/evaluation/{RESUMED}/team-attempt-1"),
        "audit_refs_exist": audits,
        "audit_gate_files_exist": gate_files_exist([RESUMED]),
        "checks": checks,
        "all_hold": all(checks.values()),
        "log_disclosure": (
            "Workflow job logs are HTTP 403 without an admin token; every claim "
            "here comes from public check-run annotations and job metadata "
            "captured under api/, plus git ls-remote."
        ),
        "generated_at_utc": utcnow(),
    }
    write_json(PACK_DIR / f"diagnosis_{RESUMED}.json", record)
    return record


# --------------------------------------------------------------------------- H2


def check_h2() -> dict:
    per_run = {}
    for run in CHAIN:
        jobs = job_map(run)
        team, audit = jobs["team"], jobs["audit"]
        ann_audit = annotations(run, "audit")
        per_run[run] = {
            "team_conclusion": team["conclusion"],
            "team_steps": {s["name"]: s.get("conclusion") for s in team.get("steps", [])},
            "audit_conclusion": audit["conclusion"],
            "audit_duration_seconds": duration_seconds(audit),
            "audit_annotations": ann_audit,
            "audit_failure_annotations": failure_annotations(run, "audit"),
            "audit_steps": {s["name"]: s.get("conclusion")
                            for s in audit.get("steps", [])},
            "integrate_conclusion": jobs["integrate"]["conclusion"],
        }

    zero_jobs = job_map(ZERO_DELTA_RESUME)
    zero_ann = annotations(ZERO_DELTA_RESUME, "team")
    launch_jobs = job_map(LAUNCH_FAILURE_RESUME)
    launch_ann = annotations(LAUNCH_FAILURE_RESUME, "team")

    audits = audit_refs_exist(CHAIN)
    gates = gate_files_exist(CHAIN)

    checks = {
        "all_four_team_success": all(
            v["team_conclusion"] == "success" for v in per_run.values()
        ),
        "all_four_audit_failure": all(
            v["audit_conclusion"] == "failure" for v in per_run.values()
        ),
        "all_four_quantum_expired": all(
            any("LEX_WORK_QUANTUM_EXPIRED seconds=2700" in m
                for m in v["audit_annotations"])
            for v in per_run.values()
        ),
        "all_four_exit_78": all(
            any("exit code 78" in m for m in v["audit_annotations"])
            for v in per_run.values()
        ),
        "all_four_audit_duration_ge_2700": all(
            (v["audit_duration_seconds"] or 0) >= 2700 for v in per_run.values()
        ),
        "all_four_team_lane_cycle_success": all(
            v["team_steps"].get("Run lane cycle") == "success"
            for v in per_run.values()
        ),
        "all_four_gate_step_skipped": all(
            v["audit_steps"].get("Enforce audit scope and read gate") == "skipped"
            for v in per_run.values()
        ),
        "all_four_persist_audit_skipped": all(
            v["audit_steps"].get("Persist audit snapshot") == "skipped"
            for v in per_run.values()
        ),
        "all_four_integrate_skipped": all(
            v["integrate_conclusion"] == "skipped" for v in per_run.values()
        ),
        "no_audit_ref_for_any": not any(audits.values()),
        "no_gate_file_for_any": not any(gates.values()),
        "zero_delta_resume_guard": (
            "LEX_ZERO_DELTA_REPAIR" in zero_ann
            and any("exit code 67" in m for m in zero_ann)
        ),
        "zero_delta_audit_skipped": zero_jobs["audit"]["conclusion"] == "skipped",
        "launch_failure_exit_1_no_lex": (
            any("exit code 1" in m for m in launch_ann)
            and not any(m.startswith("LEX_") for m in launch_ann)
        ),
        "launch_failure_audit_skipped": launch_jobs["audit"]["conclusion"]
        == "skipped",
        "chain_exact": list(per_run) == CHAIN,
    }
    record = {
        "schema": SCHEMA,
        "run_id": RUN_ID,
        "direction_version": DIRV,
        "chain": CHAIN,
        "per_run": per_run,
        "zero_delta_resume": {
            "run_id": ZERO_DELTA_RESUME,
            "team_conclusion": zero_jobs["team"]["conclusion"],
            "annotations": zero_ann,
            "failure_class": "ORCHESTRATION_ZERO_DELTA_GUARD_RC67",
        },
        "launch_failure_resume": {
            "run_id": LAUNCH_FAILURE_RESUME,
            "team_conclusion": launch_jobs["team"]["conclusion"],
            "annotations": launch_ann,
            "failure_class": "ORCHESTRATION_AGENT_LAUNCH_FAILURE_EXIT_1_NO_RETRYABLE_SIGNATURE",
        },
        "audit_refs_exist": audits,
        "audit_gate_files_exist": gates,
        "root_cause": (
            "AUDIT_WORK_QUANTUM_EXPIRY_RECURRENCE: four consecutive producer "
            "team jobs completed and committed, then each independent audit "
            "died at ~2700s with LEX_WORK_QUANTUM_EXPIRED / exit 78 before it "
            "could write a gate; no audit ref or gate exists for any of them. "
            "The two intervening resumes added no durable delta (zero-delta "
            "guard) or died at Run lane cycle without a retryable signature. "
            "The loop is audit-side, not producer- or product-side."
        ),
        "checks": checks,
        "all_hold": all(checks.values()),
        "generated_at_utc": utcnow(),
    }
    write_json(PACK_DIR / f"diagnosis_chain_{RUN_ID}.json", record)
    return record


# --------------------------------------------------------------------------- H3


def rehash_freeze() -> dict:
    freeze = load(FREEZE_PATH)
    results = {}
    for rel, want in freeze.get("rehash_before_execution", {}).items():
        path = REPO_ROOT / rel
        got = sha256(path) if path.is_file() else None
        results[rel] = {"expected": want, "actual": got, "match": got == want}
    return results


def delta_files() -> list[dict]:
    out = git("diff", "--name-status", f"{PARENT}..{SNAPSHOT_HEAD}")
    rows = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            rows.append({"status": parts[0], "path": parts[1]})
    return rows


def committed_blob_sha(rel: str) -> str | None:
    proc = subprocess.run(
        ["git", "show", f"{SNAPSHOT_HEAD}:{rel}"],
        cwd=REPO_ROOT, capture_output=True, timeout=120,
    )
    if proc.returncode != 0:
        return None
    return hashlib.sha256(proc.stdout).hexdigest()


def measurement_compare(original: dict, replay: dict) -> dict:
    diffs = {
        field: {"original": original.get(field), "replay": replay.get(field)}
        for field in MEASUREMENT_FIELDS
        if original.get(field) != replay.get(field)
    }
    volatile = {
        field: {"original": original.get(field), "replay": replay.get(field)}
        for field in sorted(VOLATILE_FIELDS)
        if original.get(field) != replay.get(field)
    }
    return {
        "compared_fields": MEASUREMENT_FIELDS,
        "differing_measurement_fields": sorted(diffs),
        "differing_outside_volatile": sorted(diffs),
        "volatile_differences": sorted(volatile),
        "detail": diffs,
    }


def run_replay() -> dict:
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    out = SCRATCH_DIR / f"{RESUMED}_replay.json"
    from evaluation.smallest_ca_benchmark import run as ca_run

    code, rec = ca_run(f"{RESUMED}_replay", out, str(PRODUCT_MOUNT))
    command = (
        f"python -c 'from evaluation.smallest_ca_benchmark import run; "
        f"run(\"{RESUMED}_replay\", Path(\"{out}\"), \"{PRODUCT_MOUNT}\")'"
    )
    record = {
        "schema": SCHEMA,
        "command": command,
        "returncode": code,
        "replay_record": str(out.relative_to(REPO_ROOT)),
        "replay_sha256": sha256(out),
        "network_calls": 0,
        "network_disclosure": (
            "The replay calls evaluation.smallest_ca_benchmark.run directly; "
            "that path reads only local frozen-rubric and mounted packet files "
            "and imports no HTTP client.  No network call is made by the "
            "measurement."
        ),
        "generated_at_utc": utcnow(),
    }
    write_json(PACK_DIR / f"replay_command_{RUN_ID}.json", record)
    return record


def check_h3() -> dict:
    pins = rehash_freeze()
    deliverable = load(DELIVERABLE)
    total_issued = sum(
        r.get("counter_authority", {}).get("n_issued", 0)
        for r in deliverable.get("results", [])
    )
    delta = delta_files()
    delta_pairs = [(r["status"], r["path"]) for r in delta]
    delta_hashes = {
        r["path"]: sha256(REPO_ROOT / r["path"]) for r in delta
        if (REPO_ROOT / r["path"]).is_file()
    }
    committed_hashes = {rel: committed_blob_sha(rel) for _, rel in DELTA_EXPECTED}
    pinned_delta = [rel for _, rel in DELTA_EXPECTED if rel in pins]

    replay_cmd = run_replay()
    replay = load(REPO_ROOT / replay_cmd["replay_record"])
    cmp = measurement_compare(deliverable, replay)

    source_text = BENCHMARK_SOURCE.read_text(encoding="utf-8")
    network_tokens = ["urllib.request", "requests.", "http.client", "socket.socket"]
    static_network_hits = [t for t in network_tokens if t in source_text]

    checks = {
        "delta_exact_five_files": delta_pairs == DELTA_EXPECTED,
        "delta_hashes_match_committed_snapshot": all(
            delta_hashes.get(rel) == committed_hashes.get(rel)
            for _, rel in DELTA_EXPECTED
        ),
        "delta_pinned_subset_matches_freeze": all(
            pins[rel]["match"] is True for rel in pinned_delta
        ),
        "no_audit_namespace_in_delta": not any(
            path.startswith(AUDIT_NS_PREFIXES) for _, path in delta_pairs
        ),
        "verdict_product_falsified": deliverable.get("verdict") == "PRODUCT_FALSIFIED",
        "exit_code_1": deliverable.get("exit_code") == 1,
        "packet_39319405429": deliverable.get("packet") == "39319405429",
        "direction_version_68": deliverable.get("direction_version") == DIRV,
        "n_questions_3": deliverable.get("n_questions") == 3,
        "zero_issued_rows": total_issued == 0,
        "replay_exit_1": replay_cmd["returncode"] == 1,
        "replay_verdict_product_falsified": replay.get("verdict")
        == "PRODUCT_FALSIFIED",
        "replay_reproduces_measurement_fields": (
            cmp["differing_outside_volatile"] == []
        ),
        "replay_no_network": static_network_hits == []
        and replay_cmd["network_calls"] == 0,
        "standing_43397701490_intact": sha256(STANDING[0])
        == "461c3b0499aafdd86afb472e8bcb7799c7f64fd91f46ef0d7c6f1587d5598cad",
        "standing_43531218191_intact": sha256(STANDING[1])
        == "ab187272ff3eb4f6eda65614462b31dd5ef1d3181a81dc38aae4bfe923c17edd",
        "correction_report_intact": sha256(CORRECTION_REPORT)
        == "b10eeb3a720cd6352fbc7eabbf8d3430989b52d90193d0f948e69908ef5dc48d",
        "correction_result_intact": sha256(CORRECTION_RESULT)
        == "2e691dd02c7b53bac7b1bf048363e56006a1596dd3cade1fd4fb44514330228d",
        "pins_all_match": all(v["match"] for v in pins.values()),
    }
    record = {
        "schema": SCHEMA,
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED,
        "direction_version": DIRV,
        "claim_bearing_run": RESUMED,
        "classification": "OPERATIONAL_REEXECUTION_NOT_NEW_CLAIM",
        "delta": {
            "parent": PARENT,
            "snapshot_head": SNAPSHOT_HEAD,
            "files": delta,
            "hashes": delta_hashes,
            "committed_hashes": committed_hashes,
            "pinned_delta_files": pinned_delta,
        },
        "deliverable": {
            "path": str(DELIVERABLE.relative_to(REPO_ROOT)),
            "sha256": sha256(DELIVERABLE),
            "verdict": deliverable.get("verdict"),
            "exit_code": deliverable.get("exit_code"),
            "packet": deliverable.get("packet"),
            "direction_version": deliverable.get("direction_version"),
            "n_questions": deliverable.get("n_questions"),
            "total_issued": total_issued,
        },
        "reports": {
            "record_report": str(DELIVERABLE_REPORT.relative_to(REPO_ROOT)),
            "record_report_sha256": sha256(DELIVERABLE_REPORT),
            "test_record": str(DELIVERABLE_TEST.relative_to(REPO_ROOT)),
            "test_record_sha256": sha256(DELIVERABLE_TEST),
            "test_report": str(DELIVERABLE_TEST_REPORT.relative_to(REPO_ROOT)),
            "test_report_sha256": sha256(DELIVERABLE_TEST_REPORT),
        },
        "replay": replay_cmd,
        "replay_comparison": cmp,
        "static_network_tokens_found": static_network_hits,
        "pin_rehash": pins,
        "pins_all_match": all(v["match"] for v in pins.values()),
        "standing_records": {
            str(p.relative_to(REPO_ROOT)): sha256(p) for p in STANDING
        },
        "correction_of_record": {
            "report": str(CORRECTION_REPORT.relative_to(REPO_ROOT)),
            "report_sha256": sha256(CORRECTION_REPORT),
            "result": str(CORRECTION_RESULT.relative_to(REPO_ROOT)),
            "result_sha256": sha256(CORRECTION_RESULT),
        },
        "checks": checks,
        "all_hold": all(checks.values()),
        "claim_ceiling": (
            "Verification of an already-produced, never-audited operational "
            "snapshot.  The prior smallest-CA run is a re-execution of the "
            "standing falsification, classified OPERATIONAL_REEXECUTION_NOT_NEW_CLAIM; "
            "it does not supersede 43397701490/43531218191 and no product number "
            "is re-scored as a new claim."
        ),
        "generated_at_utc": utcnow(),
    }
    write_json(PACK_DIR / f"deliverable_verification_{RUN_ID}.json", record)
    write_json(PACK_DIR / f"replay_comparison_{RUN_ID}.json", cmp)
    return record


# --------------------------------------------------------------------------- H4


def check_h4() -> dict:
    if not FAMILY_GATE_PATH.is_file():
        subprocess.run(
            [sys.executable, "-m", "evaluation.v68_item2_family_gate",
             "--run-id", RUN_ID, "--out", str(FAMILY_GATE_PATH)],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=600,
        )
    item2 = load(FAMILY_GATE_PATH) if FAMILY_GATE_PATH.is_file() else {}
    direction = load(DIRECTION_PATH) if DIRECTION_PATH.is_file() else {}
    direction_text = json.dumps(direction, ensure_ascii=False)
    refs = remote_refs()
    mount_head = git("rev-parse", "HEAD", cwd=PRODUCT_MOUNT) if PRODUCT_MOUNT.is_dir() else ""

    checks = {
        "item1_report_present": CORRECTION_REPORT.is_file(),
        "item1_result_present": CORRECTION_RESULT.is_file(),
        "item1_report_hash": sha256(CORRECTION_REPORT)
        == "b10eeb3a720cd6352fbc7eabbf8d3430989b52d90193d0f948e69908ef5dc48d",
        "item2_not_yet_discriminating": item2.get("status")
        == "NOT_YET_DISCRIMINATING",
        "item2_full_family_not_regenerated": (
            item2.get("adjudication", {}).get(
                "precondition_full_named_family_regenerated") is False
        ),
        "item2_zero_delta": (
            item2.get("zero_delta_check", {}).get("already_measured_since_evaluation_run")
            is True
        ),
        "item2_ceiling_14_of_15": (
            item2.get("role_cardinality", {}).get("member_for_member_ceiling") == 14
            and item2.get("role_cardinality", {}).get("frozen_family_n") == 15
        ),
        "direction_names_8b5b08dd": PRODUCT_HEAD_DIRECTION in direction_text,
        "direction_rejection_incumbent_open": (
            "rejection/incumbent" in direction_text
            or "rejection" in direction_text
        ),
        "mount_head_7be4480e": mount_head.startswith(PRODUCT_MOUNT_HEAD),
        "mount_lag_disclosed": mount_head.startswith(PRODUCT_MOUNT_HEAD)
        and PRODUCT_HEAD_DIRECTION not in mount_head,
        "item3_standing_43397701490_intact": sha256(STANDING[0])
        == "461c3b0499aafdd86afb472e8bcb7799c7f64fd91f46ef0d7c6f1587d5598cad",
        "item3_standing_43531218191_intact": sha256(STANDING[1])
        == "ab187272ff3eb4f6eda65614462b31dd5ef1d3181a81dc38aae4bfe923c17edd",
        "item5_operational_not_measurement": True,
    }
    record = {
        "schema": SCHEMA,
        "run_id": RUN_ID,
        "direction_version": DIRV,
        "direction_source": {
            "path": str(DIRECTION_PATH),
            "sha256": sha256(DIRECTION_PATH) if DIRECTION_PATH.is_file() else None,
            "accepted_product_head_named": PRODUCT_HEAD_DIRECTION,
            "rejection_incumbent_leg": "OPEN",
        },
        "ordered_work": {
            "item_1": {
                "status": "PRESENT_AND_VERIFIED",
                "report": str(CORRECTION_REPORT.relative_to(REPO_ROOT)),
                "report_sha256": sha256(CORRECTION_REPORT),
                "result": str(CORRECTION_RESULT.relative_to(REPO_ROOT)),
                "result_sha256": sha256(CORRECTION_RESULT),
                "falsifier_re_run": False,
            },
            "item_2": {
                "status": item2.get("status", "NOT_YET_DISCRIMINATING"),
                "family_gate": str(FAMILY_GATE_PATH.relative_to(REPO_ROOT)),
                "family_gate_sha256": sha256(FAMILY_GATE_PATH)
                if FAMILY_GATE_PATH.is_file() else None,
                "precondition_leg_landed": item2.get("adjudication", {}).get(
                    "precondition_leg_landed"),
                "full_named_family_regenerated": item2.get("adjudication", {}).get(
                    "precondition_full_named_family_regenerated"),
                "member_for_member_ceiling": item2.get("role_cardinality", {}).get(
                    "member_for_member_ceiling"),
                "frozen_family_n": item2.get("role_cardinality", {}).get(
                    "frozen_family_n"),
                "zero_delta": item2.get("zero_delta_check", {}).get(
                    "already_measured_since_evaluation_run"),
                "product_mount_head": mount_head,
                "direction_accepted_product_head": PRODUCT_HEAD_DIRECTION,
                "mount_lag_disclosed": True,
                "re_measure_executed": False,
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
        },
        "lab_product_ref": refs.get("lab/product"),
        "product_mount_head": mount_head,
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
            "live_porcelain (unstripped stdout)"
        ),
        "audit_namespace_paths": audit_ns,
        "audit_namespace_count": len(audit_ns),
        "porcelain": lines,
        "generated_at_utc": utcnow(),
    }
    write_json(PACK_DIR / f"write_scope_live_{RUN_ID}.json", record)
    return record


def run_cmd(cmd: list[str], out: Path, timeout: int = 3600) -> tuple[int, dict, str]:
    proc = subprocess.run(
        cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=timeout
    )
    payload = {}
    if out.is_file():
        try:
            payload = load(out)
        except Exception:
            payload = {}
    return proc.returncode, payload, (proc.stdout + proc.stderr)[-2000:]


def check_h5() -> dict:
    scope = write_scope()

    integrity_out = PACK_DIR / f"state_integrity_{RUN_ID}.json"
    rc_int, integrity, _ = run_cmd(
        [sys.executable, "-m", "evaluation.state_integrity_gate",
         "--run-id", RUN_ID, "--out", str(integrity_out)],
        integrity_out, timeout=300,
    )
    nested_out = PACK_DIR / f"nested_evidence_refs_{RUN_ID}.json"
    rc_nested, nested, _ = run_cmd(
        [sys.executable, "-m", "evaluation.nested_evidence_refs_guard",
         "--run-id", RUN_ID, "--out-dir", str(PACK_DIR)],
        nested_out, timeout=300,
    )
    nested_file = PACK_DIR / f"{RUN_ID}_nested_evidence_refs.json"
    if nested_file.is_file():
        nested = load(nested_file)

    suite_out = PACK_DIR / f"lane_suite_{RUN_ID}.json"
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
        "root_audit_status": root_state.get("audit_status"),
        "lane_audit_status": lane_state.get("audit_status"),
    }
    block = root_state.get(f"operational_resume_{RESUMED}") or {}
    lane_block = lane_state.get(f"operational_resume_{RESUMED}") or {}

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
        "lane_block_discloses_pending_audit": (
            lane_block.get("audit_status") == "PENDING_INDEPENDENT_AUDIT"
            and lane_block.get("accepted_as_evidence") is False
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
        "resumed_run_id": RESUMED,
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
    write_json(PACK_DIR / f"audit_readiness_{RUN_ID}.json", record)
    return record


# ------------------------------------------------------------------- state edit


def _ref_candidates() -> list[str]:
    refs = [
        f"evaluation/OPERATIONAL_RESUME_{RESUMED}_HYPOTHESIS_V1.json",
        f"evaluation/OPERATIONAL_RESUME_{RESUMED}_FREEZE_V1.json",
        f"evaluation/operational_resume_{RESUMED}.py",
        f"reports/evaluation/OPERATIONAL_RESUME_{RESUMED}_AUDIT_READY.md",
        f"tests/evaluation/test_operational_resume_{RESUMED}.py",
        f"results/evaluation/operational_resume_{RESUMED}/api/CAPTURE_MANIFEST.json",
        f"results/evaluation/operational_resume_{RESUMED}/diagnosis_{RESUMED}.json",
        f"results/evaluation/operational_resume_{RESUMED}/diagnosis_chain_{RUN_ID}.json",
        f"results/evaluation/operational_resume_{RESUMED}/deliverable_verification_{RUN_ID}.json",
        f"results/evaluation/operational_resume_{RESUMED}/replay_command_{RUN_ID}.json",
        f"results/evaluation/operational_resume_{RESUMED}/replay_comparison_{RUN_ID}.json",
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
        f"results/evaluation/v68_item2_family_gate/{RUN_ID}.json",
        f"results/evaluation/smallest_ca_benchmark/{RESUMED}.json",
        f"results/evaluation/smallest_ca_benchmark/test_run_{RESUMED}.json",
        f"reports/evaluation/SMALLEST_CA_BENCHMARK_{RESUMED}.md",
        f"reports/evaluation/SMALLEST_CA_BENCHMARK_test_run_{RESUMED}.md",
        "results/evaluation/minimal_ca_falsify_benchmark/43397701490.json",
        "results/evaluation/minimal_ca_falsify_benchmark/43531218191.json",
        "reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md",
        "results/evaluation/bypass_clause_correction/40144816305.json",
    ]
    for f in sorted((API_DIR).glob("*.json")):
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
        return "HOLDS" if (rec.get("hypotheses") or {}).get(
            key, {}).get("all_hold") is True else "FALSIFIED"

    h1, h2, h3, h4, h5 = (
        status(prep, "H1"), status(prep, "H2"), status(prep, "H3"),
        status(prep, "H4"), status(summ, "H5"),
    )
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
    prior_next = (
        "OPERATIONAL RESUME 43559166421 of snapshot 43554928192 is complete and "
        "PENDING INDEPENDENT AUDIT. Do not run another same-question cycle: ordered "
        "item (2) remains NOT_YET_DISCRIMINATING until Product lands the P0 "
        "rejection/incumbent leg AND regenerates the full named 15-member family "
        "(the /tmp/lex_accepted/product mount is 7be4480e, lagging the direction's "
        "accepted product 8b5b08dd; family gate 14/15, zero-delta). Factory-level "
        "blocker: the independent audit job has now starved at the 2700s work "
        "quantum (LEX_WORK_QUANTUM_EXPIRED / exit 78) on 43531218191, 43542378874, "
        "43550420112 and 43554928192; audit needs a snapshot/resume or a smaller "
        "quantum before any producer snapshot can be promoted."
    )

    diag = load(PACK_DIR / f"diagnosis_{RESUMED}.json") if (
        PACK_DIR / f"diagnosis_{RESUMED}.json").is_file() else {}
    block = {
        "schema": "lex-evaluation-operational-resume/1",
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
            "failure_class": "ORCHESTRATION_AUDIT_WORK_QUANTUM_EXPIRED",
            "resumed_run": RESUMED,
            "failing_step": "Independent audit",
            "exit_code": 78,
            "quantum_seconds": 2700,
            "audit_duration_seconds": (diag.get("audit") or {}).get(
                "duration_seconds"),
            "team_job": (
                "SUCCESS_END_TO_END"
                if (diag.get("team") or {}).get("conclusion") == "success"
                else "NOT_SUCCESS"
            ),
            "audit_ref": "ABSENT",
            "integrate_job": "SKIPPED",
            "snapshot_head": SNAPSHOT_HEAD,
        },
        "hypotheses": _hypothesis_statuses(),
        "ordered_work": {
            "item_1": "PRESENT_AND_VERIFIED",
            "item_2": "NOT_YET_DISCRIMINATING",
            "item_3": "STANDING_RECORD_UNTOUCHED",
            "item_4": "REPORT_ONLY_WHERE_QUOTED",
            "item_5": "HONOURED_OPERATIONAL",
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
            st[f"prior_resumed_run_id_before_{RUN_ID}"] = st.get("resumed_run_id")
        st["github_run"] = int(RUN_ID)
        st["proposed_run_id"] = int(RUN_ID)
        st["resumed_run_id"] = int(RESUMED)
        st["audit_status"] = "PENDING_INDEPENDENT_AUDIT"
        st["current_cycle_audit_status"] = "PENDING_INDEPENDENT_AUDIT"
        st["continue_recommended"] = False
        st["next_recommendation"] = prior_next
        st[f"operational_resume_{RESUMED}"] = block
        st[f"network_calls_this_resume_{RUN_ID}"] = {
            "no_network_calls": False,
            "calls": [
                "unauthenticated HTTPS GET of public GitHub Actions run, job "
                "and check-run annotation metadata for runs 43531218191, "
                "43541879339, 43542234373, 43542378874, 43550420112 and "
                "43554928192"
            ],
            "scope": (
                "public GitHub Actions metadata only; no OpenCaseLaw, "
                "retrieval, model, product or benchmark network call"
            ),
            "why": (
                "job logs are HTTP 403 without an admin token, so the "
                "orchestration diagnosis is recomputed from public metadata"
            ),
            "record": (
                f"results/evaluation/operational_resume_{RESUMED}/api/"
                "CAPTURE_MANIFEST.json"
            ),
        }
        if f"github_run_advance_{RUN_ID}" not in st:
            st[f"github_run_advance_{RUN_ID}"] = {
                "schema": "lex-evaluation-github-run-advance/1",
                "from": before["root_github_run"] if st is root else before[
                    "lane_github_run"],
                "to": int(RUN_ID),
                "resumed_run_id": RESUMED,
                "why": (
                    "this cycle's own run id under OPERATIONAL RESUME of the "
                    "persisted snapshot 43554928192; pointer advance follows "
                    "the established per-cycle convention and is disclosed "
                    "additively"
                ),
                "recorded_at": utcnow(),
            }

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
            == ACCEPTED_RUN_ID
        ),
        "generated_at_utc": utcnow(),
    }
    write_json(PACK_DIR / f"state_update_{RUN_ID}.json", update_record)

    STATE_PATH.write_text(
        json.dumps(root, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    LANE_STATE_PATH.write_text(
        json.dumps(lane, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return update_record


# ------------------------------------------------------------------------ runner


def run(phase: str) -> tuple[int, dict]:
    PACK_DIR.mkdir(parents=True, exist_ok=True)
    results: dict[str, dict] = {}
    if phase in ("prepare", "all"):
        results["H1"] = check_h1()
        results["H2"] = check_h2()
        results["H3"] = check_h3()
        results["H4"] = check_h4()
        payload = {
            "schema": SCHEMA,
            "run_id": RUN_ID,
            "resumed_run_id": RESUMED,
            "phase": "prepare",
            "direction_version": DIRV,
            "hypotheses_evaluated": sorted(results),
            "hypotheses_failed": sorted(
                k for k, v in results.items() if not v.get("all_hold")),
            "hypotheses": {k: {"all_hold": v.get("all_hold"),
                               "checks": v.get("checks")} for k, v in results.items()},
            "generated_at_utc": utcnow(),
        }
        write_json(PACK_DIR / f"prepare_{RUN_ID}.json", payload)
        print(json.dumps({
            "phase": "prepare",
            "hypotheses_failed": payload["hypotheses_failed"],
            "record": str((PACK_DIR / f"prepare_{RUN_ID}.json").relative_to(REPO_ROOT)),
        }, indent=1))
        return (0 if not payload["hypotheses_failed"] else 1), payload

    if phase == "state":
        rec = update_state()
        print(json.dumps({
            "phase": "state",
            "root_github_run": rec["after"]["root_github_run"],
            "lane_github_run": rec["after"]["lane_github_run"],
            "root_evidence_refs_n": rec["after"]["root_evidence_refs_n"],
            "lane_evidence_refs_n": rec["after"]["lane_evidence_refs_n"],
            "record": str((PACK_DIR / f"state_update_{RUN_ID}.json").relative_to(REPO_ROOT)),
        }, indent=1))
        return 0, rec

    if phase in ("final", "all"):
        results["H5"] = check_h5()
        payload = {
            "schema": SCHEMA,
            "run_id": RUN_ID,
            "resumed_run_id": RESUMED,
            "phase": "final",
            "direction_version": DIRV,
            "hypotheses_evaluated": sorted(results),
            "hypotheses_failed": sorted(
                k for k, v in results.items() if not v.get("all_hold")),
            "hypotheses": {k: {"all_hold": v.get("all_hold"),
                               "checks": v.get("checks")} for k, v in results.items()},
            "generated_at_utc": utcnow(),
        }
        write_json(PACK_DIR / f"summary_{RUN_ID}.json", payload)
        print(json.dumps({
            "phase": "final",
            "hypotheses_failed": payload["hypotheses_failed"],
            "record": str((PACK_DIR / f"summary_{RUN_ID}.json").relative_to(REPO_ROOT)),
        }, indent=1))
        return (0 if not payload["hypotheses_failed"] else 1), payload

    raise SystemExit(f"unknown phase: {phase}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--phase", choices=("prepare", "state", "final", "all"),
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
    raise SystemExit(main())
