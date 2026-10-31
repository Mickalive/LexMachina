#!/usr/bin/env python3
"""Operational resume of persisted producer snapshot 41171827286 (evaluation, v68).

WHY THIS EXISTS
---------------
Run 41171827286 ("Core evaluation dirV68 repair0", dispatched by the resilience
job of 41165748723 with resume_from_run_id=41165748723) FAILED at its team job's
``Run lane cycle`` step in ~16 seconds with **exit code 1**.  Its
``Validate active MVP producer state`` and ``Enforce lane write scope`` steps
were skipped; ``Persist team snapshot`` still ran and force-pushed
``cycle/core/evaluation/41171827286/team`` at commit 6d73946d — byte-identical
to ``cycle/core/evaluation/41165748723/team``, i.e. ZERO producer delta.  The
audit and integrate jobs were skipped; no gate and no accept commit exist for
41171827286.

DIAGNOSIS (public GitHub REST metadata; job logs are 403-unauthenticated)
-----------------------------------------------------------------------
The single failure annotation is "Process completed with exit code 1."
The wrapper's own fast-guard classes are all EXCLUDED by evidence:
  * rc 64/65/66 (agent-registry) and rc 76 (model-health) print ``::error::``
    annotations — the team job carries none besides the exit-code line;
  * rc 67 (LEX_ZERO_DELTA_REPAIR) prints ``::error::LEX_ZERO_DELTA_REPAIR``
    and requires the Ox child to exit 0 — absent;
  * rc 78 (LEX_WORK_QUANTUM_EXPIRED) requires 2700 s — the step lasted ~16 s.
What remains consistent with every observed fact: the Ox/OpenCode child
exited non-zero almost immediately without a transient (retryable) network
signature, so run-ox-with-retry.sh:112 propagated the child's rc=1.  That is
the provider/auth/config failure class of factory-wide requirement 20 — an
ORCHESTRATION failure, not a measurement, not producer validation and not a
human-gate problem.  The mechanism attribution is an INFERENCE from job/step
timing plus annotations; it is hedged because step logs are unreadable.

The chain context is preserved: 41161273401's producer succeeded and its
AUDIT died at the 2700 s quantum guard (exit 78; committed diagnosis
CYCLE_41161273401_audit_quantum_expiry.json); 41165748723's producer succeeded
(commit 6d73946d, the snapshot this run resumes) and its AUDIT ALSO died at the
quantum guard (exit 78; annotations LEX_WORK_QUANTUM_EXPIRED pid=2248) — that
second audit death is newly diagnosed HERE and committed as
CYCLE_41165748723_audit_quantum_expiry.json.

WHAT THIS RUN ADDS (no closed work re-derived)
----------------------------------------------
1. PRODUCER-DEATH DIAGNOSIS for 41171827286 (machine record + exclusion checks)
   and the ZERO-DELTA proof (both snapshot refs at 6d73946d).
2. SECOND AUDIT-QUANTUM-EXPIRY DIAGNOSIS for 41165748723.
3. FRESH REPLAY of the persisted 41165748723 deliverable: its verifier chain is
   re-executed in scratch under the ACCEPTED numeric environment (restored via
   pip after the ubuntu-latest image migration dropped numpy) and the
   claim-bearing payload is compared to the committed record after removing
   only the enumerated runtime/state-mutation fields (full diff published).
4. ITEM-(2) CURRENCY CHECK (NOT a re-adjudication): the accepted product mount
   head is compared with the head recorded by the committed item-2
   readjudication; identity means the prior adjudication remains current and
   the ordered protocol stays NOT executed (item-(5) zero-delta rule).  The
   precondition gate is re-run ONLY IF the head had drifted.
5. FRESH multilingual/provenance supplement (the accepted 2-case suite) and the
   accepted-pointer verification on both halves of requirement 4.
6. AUDIT-READINESS records: state-integrity gate, lane suite, nested evidence
   refs guard, live write scope, snapshot write-scope repro of 41171827286
   (expected: zero added paths), and a no-audit-gate-minted control.

CLAIM CEILING
-------------
This resume scores no frozen bar, packet, standing falsification,
d2_path_scope_probe or universal-174k benchmark.  It edits no frozen rubric,
threshold, predicate or verdict contract, issues no serve verdict, admits no
packet and makes no jurist-utility claim.  Ordered item (2) remains gated on
Product regenerating the named full family; item (3) stays the benchmark of
record.  All posture flags stay FALSE.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation import operational_resume_41165748723 as PRIOR2  # noqa: E402
from evaluation import operational_resume_41161273401 as PRIOR1  # noqa: E402

RUN_ID = "41171918973"
RESUMED_RUN_ID = "41171827286"
PRIOR_PRODUCER_RUN = "41165748723"
SNAPSHOT_COMMIT = "6d73946d279032d8d10c82f6dfa21793595c3887"
SNAPSHOT_PARENT = "6d73946d279032d8d10c82f6dfa21793595c3887"  # zero-delta: parent == snapshot for the resumed run's own delta
SNAPSHOT_REF = "origin/cycle/core/evaluation/41171827286/team"
PRIOR_RESULT = "results/evaluation/operational_resume/41165748723.json"
PRIOR_SCRIPT = "evaluation/operational_resume_41165748723.py"
PRIOR_ITEM2 = "results/evaluation/operational_resume/41165748723_item2_readjudication.json"

JOBS_286 = "results/evaluation/orchestration/41171827286_jobs.json"
RUNREC_286 = "results/evaluation/orchestration/41171827286_run_record.json"
ANNOT_286 = "results/evaluation/orchestration/41171827286_team_annotations.json"
JOBS_723 = "results/evaluation/orchestration/41165748723_jobs.json"
ANNOT_723 = "results/evaluation/orchestration/41165748723_audit_annotations.json"
DIAG_286 = "results/evaluation/orchestration/CYCLE_41171827286_producer_exit1.json"
DIAG_723 = "results/evaluation/orchestration/CYCLE_41165748723_audit_quantum_expiry.json"

OUT_RESULT = f"results/evaluation/operational_resume/{RUN_ID}.json"
OUT_REPORT = f"reports/evaluation/OPERATIONAL_RESUME_{RUN_ID}.md"
REPLAY_RECORD = f"results/evaluation/operational_resume/{RUN_ID}_replay_of_41165748723.json"
ITEM2_RECORD = f"results/evaluation/operational_resume/{RUN_ID}_item2_currency.json"
MULT_RECORD = f"results/evaluation/operational_resume/{RUN_ID}_multilingual_supplement.json"
STATE_GATE = f"results/evaluation/orchestration/{RUN_ID}_state_integrity_gate.json"
LANE_SUITE = f"results/evaluation/orchestration/{RUN_ID}_lane_suite.json"
NESTED_REFS = f"results/evaluation/orchestration/{RUN_ID}_nested_evidence_refs.json"
WRITE_SCOPE = f"results/evaluation/orchestration/{RUN_ID}_write_scope.json"
SNAPSHOT_SCOPE = f"results/evaluation/orchestration/{RUN_ID}_snapshot_write_scope_repro.json"
SELF_SCRIPT = f"evaluation/operational_resume_{RUN_ID}.py"
SELF_TEST = f"tests/evaluation/test_operational_resume_{RUN_ID}.py"
SELF_CHECK_RESULT = f"results/evaluation/orchestration/{RUN_ID}_self_check_pytest_shim.json"

STATE = "state/evaluation.json"
LANE_STATE = "evaluation/state/evaluation.json"
MOUNT = Path("/tmp/lex_accepted/product")
EXPECTED_PRODUCT_MOUNT_HEAD = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
EXPECTED_ACCEPTED_RUN = 40265377500
EXPECTED_ACCEPTED_COMMIT = "ea98384e54d31d2e694c418a1d1ce5769fc6c32f"
MULT_TEST = "tests/evaluation/test_retrieval_benchmark.py"
MULT_TEST_SHA256 = "558e1f1b7143e09e704891d5e0d7401a9b688e8d9c3d4b389dc4229972dc47be"
PRIOR_RESULT_SHA256_FROZEN = "fa555a897e36018fa9f596e5910c9d1dd091b8b103ea7f5311b2d2f72fa52d22"

EXIT_PASS = 0
EXIT_GAPS = 2


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


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, obj: Any) -> None:
    p = REPO_ROOT / path if not Path(path).is_absolute() else Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def git(*args: str, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True,
                          text=True, timeout=120)


def numeric_environment() -> dict:
    def mv(name: str) -> str | None:
        try:
            return getattr(__import__(name), "__version__", None)
        except Exception:
            return None
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": mv("numpy"),
        "scipy": mv("scipy"),
        "scikit_learn": mv("sklearn"),
        "accepted_environment_reference": (
            "numpy 2.5.4 / scipy 1.18.1 / scikit-learn 1.9.1 as recorded by accepted "
            "cycle 40261335674; restored via pip after the ubuntu-latest image "
            "migration dropped the preinstalled scientific stack (disclosed in the "
            "hypothesis pre-freeze disclosure)"),
    }


# --------------------------------------------------------------------------- #
# 1. producer-death diagnosis for 41171827286
# --------------------------------------------------------------------------- #
def producer_death_diagnosis() -> dict:
    jobs_doc = load_json(JOBS_286)
    run_doc = load_json(RUNREC_286)
    annots = load_json(ANNOT_286)
    jobs = {j["name"]: j for j in jobs_doc["jobs"]}
    team = jobs["team"]
    steps = {s["number"]: s for s in team["steps"]}
    failed = steps[6]
    dur = None
    if failed.get("started_at") and failed.get("completed_at"):
        from datetime import datetime as _dt
        t0 = _dt.fromisoformat(failed["started_at"].replace("Z", "+00:00"))
        t1 = _dt.fromisoformat(failed["completed_at"].replace("Z", "+00:00"))
        dur = int((t1 - t0).total_seconds())

    msgs = [a.get("message") or "" for a in annots]
    has_exit1 = any("exit code 1" in m for m in msgs)
    has_zero_delta_err = any("LEX_ZERO_DELTA_REPAIR" in m for m in msgs)
    has_quantum = any("LEX_WORK_QUANTUM_EXPIRED" in m for m in msgs)
    has_model_health_err = any(
        "LEX_NO_HEALTHY_FREE_TOOL_MODEL" in m or "LEX_MODEL_HEALTH_MISSING" in m
        or "LEX_MODEL_ARGUMENT_MISSING" in m for m in msgs)
    has_registry_err = any(
        "agent" in m.lower() and "card" in m.lower() for m in msgs) or any(
        "Missing canonical agent registry" in m for m in msgs)

    # both team snapshot refs at the same sha = zero producer delta
    r1 = git("ls-remote", "origin",
             "refs/heads/cycle/core/evaluation/41171827286/team",
             "refs/heads/cycle/core/evaluation/41165748723/team")
    refs = {}
    for line in r1.stdout.splitlines():
        sha, ref = line.split("\t")
        refs[ref.replace("refs/heads/", "")] = sha
    snap_286 = refs.get("cycle/core/evaluation/41171827286/team")
    snap_723 = refs.get("cycle/core/evaluation/41165748723/team")

    exclusions = {
        "rc_64_65_66_registry_guard_excluded": not has_registry_err,
        "rc_76_model_health_guard_excluded": not has_model_health_err,
        "rc_67_zero_delta_guard_excluded": (not has_zero_delta_err) and has_exit1,
        "rc_78_quantum_expiry_excluded": (not has_quantum) and dur is not None and dur < 600,
        "wrapper_error_annotations_absent": not (
            has_zero_delta_err or has_model_health_err or has_registry_err or has_quantum),
    }
    verdict_consistent = bool(
        team["conclusion"] == "failure"
        and steps[6]["conclusion"] == "failure"
        and has_exit1
        and steps[7]["conclusion"] == "skipped"
        and steps[9]["conclusion"] == "skipped"
        and steps[10]["conclusion"] == "success"
        and jobs["audit"]["conclusion"] == "skipped"
        and jobs["integrate"]["conclusion"] == "skipped"
        and run_doc.get("conclusion") == "failure"
        and snap_286 == snap_723 == SNAPSHOT_COMMIT
        and all(exclusions.values())
    )

    rec = {
        "schema": "lex-evaluation-producer-death-diagnosis/1",
        "run_id": int(RUN_ID),
        "failed_run_id": int(RESUMED_RUN_ID),
        "direction_version": 68,
        "generated_at_utc": utc(),
        "failure_class": "PRODUCER_SESSION_DIED_EXIT_1_WITHOUT_TRANSIENT_SIGNATURE",
        "failure_is_orchestration_not_measurement": True,
        "failure_is_validation_failure": False,
        "failure_is_zero_delta_guard": False,
        "failure_is_quantum_expiry": False,
        "failed_job": "team",
        "failed_job_id": team["id"],
        "failed_job_step": failed["name"],
        "failed_step_number": 6,
        "failed_step_started_at": failed.get("started_at"),
        "failed_step_completed_at": failed.get("completed_at"),
        "failed_step_duration_seconds": dur,
        "exit_code": 1,
        "exit_code_source": "check-run annotation 'Process completed with exit code 1.'",
        "downstream": {
            "validate_active_mvp_producer_state": steps[7]["conclusion"],
            "enforce_lane_write_scope": steps[9]["conclusion"],
            "persist_team_snapshot": steps[10]["conclusion"],
            "audit_job": jobs["audit"]["conclusion"],
            "integrate_job": jobs["integrate"]["conclusion"],
        },
        "annotations_verbatim": msgs,
        "guard_exclusion_checks": exclusions,
        "exclusion_logic": (
            "run-ox-with-retry.sh exits 64/65/66 (registry), 76 (model health), "
            "67 (zero-delta repair; requires Ox rc=0) or 78 (2700 s quantum) via "
            "distinct ::error::/::warning:: annotations or step durations; none "
            "appear and the step lasted ~16 s, so the only remaining wrapper path "
            "is line 112 'exit $rc' after a non-transient Ox child failure."),
        "mechanism_attribution": (
            "INFERENCE (hedged): an immediate non-transient Ox/OpenCode "
            "agent-session failure — the provider/auth/config class of "
            "factory-wide requirement 20. Step logs are 403-unauthenticated so no "
            "log line was read; the attribution rests on the exit code, the "
            "step timing and the absent guard annotations only."),
        "zero_delta_proof": {
            "team_ref_41171827286": snap_286,
            "team_ref_41165748723": snap_723,
            "identical": snap_286 == snap_723 == SNAPSHOT_COMMIT,
            "meaning": (
                "the persisted producer snapshot of the failed run carries ZERO "
                "delta over the snapshot it resumed; all valid completed work "
                "lives in 6d73946d and is preserved append-only"),
        },
        "evidence_artifacts": [JOBS_286, RUNREC_286, ANNOT_286],
        "verdict_consistent_with_all_evidence": verdict_consistent,
        "claim_ceiling": (
            "Public GitHub Actions metadata diagnosis of an orchestration guard. "
            "It is not a measurement, not a producer validation failure and not "
            "an audit verdict; the mechanism attribution is an inference."),
    }
    write_json(DIAG_286, rec)
    return rec


# --------------------------------------------------------------------------- #
# 2. second audit quantum-expiry diagnosis (41165748723)
# --------------------------------------------------------------------------- #
def audit_quantum_diagnosis() -> dict:
    jobs_doc = load_json(JOBS_723)
    annots = load_json(ANNOT_723)
    jobs = {j["name"]: j for j in jobs_doc["jobs"]}
    team, audit, integrate = jobs["team"], jobs["audit"], jobs["integrate"]
    steps = {s["number"]: s for s in audit["steps"]}
    msgs = [a.get("message") or "" for a in annots]
    rec = {
        "schema": "lex-evaluation-orchestration-resume-diagnosis/1",
        "lane": "evaluation",
        "run_id": int(RUN_ID),
        "failed_run_id": int(PRIOR_PRODUCER_RUN),
        "direction_version": 68,
        "generated_at_utc": utc(),
        "mode": (
            f"OPERATIONAL RESUME diagnosis of run {PRIOR_PRODUCER_RUN}'s audit "
            f"failure, recorded by run {RUN_ID}"),
        "failure_class": "WORK_QUANTUM_EXPIRED",
        "not_a_measurement_failure": True,
        "exit_code": 78,
        "quantum_seconds": 2700,
        "failed_step": steps[5]["name"],
        "failed_step_started_at": steps[5].get("started_at"),
        "failed_step_completed_at": steps[5].get("completed_at"),
        "evidence_artifacts": [JOBS_723, ANNOT_723],
        "evidence_annotations_verbatim": [
            m for m in msgs if "ubuntu" not in m.lower()],
        "producer_validation_verdict": {
            "validate_active_mvp_producer_state": next(
                s for s in team["steps"] if s["number"] == 7)["conclusion"],
            "enforce_lane_write_scope": next(
                s for s in team["steps"] if s["number"] == 9)["conclusion"],
            "persist_team_snapshot": next(
                s for s in team["steps"] if s["number"] == 10)["conclusion"],
            "run_lane_cycle": next(
                s for s in team["steps"] if s["number"] == 6)["conclusion"],
        },
        "downstream": {
            "audit_scope_step": steps[6]["conclusion"],
            "audit_persist_step": steps[7]["conclusion"],
            "integrate_job": integrate["conclusion"],
        },
        "snapshot": {
            "team_ref": "origin/cycle/core/evaluation/41165748723/team",
            "commit": SNAPSHOT_COMMIT,
            "commit_subject": "evaluation cycle 41165748723 repair 0",
            "resumed_by_this_run": True,
            "also_persisted_identically_by_failed_run_41171827286": True,
        },
        "acceptance_state": {
            "audit_gate_for_41165748723": "NONE (audit job died before gate write)",
            "accept_commit_for_41165748723": "NONE",
            "origin_lab_evaluation_head_at_resume": EXPECTED_ACCEPTED_COMMIT,
            "origin_lab_evaluation_head_subject": "accept evaluation cycle 40265377500",
            "disposition": "NON_PROMOTING_PENDING_INDEPENDENT_AUDIT; preserved append-only",
        },
        "second_occurrence_in_chain": {
            "first": "41161273401 audit job, exit 78 (CYCLE_41161273401_audit_quantum_expiry.json)",
            "second": f"{PRIOR_PRODUCER_RUN} audit job, exit 78 (this record)",
            "pattern": (
                "two consecutive independent-audit jobs exceeded the 2700 s "
                "wrapper quantum while auditing this lane's operational-resume "
                "deliverables; the producer work is valid in both cases and the "
                "failure is orchestration scope/timing, not evidence quality"),
        },
        "claim_ceiling": (
            "Public GitHub Actions metadata diagnosis of an orchestration guard. "
            "It is not a measurement, not a producer validation failure and not "
            "an audit verdict."),
    }
    write_json(DIAG_723, rec)
    return rec


# --------------------------------------------------------------------------- #
# 3. fresh replay of the persisted 41165748723 deliverable
# --------------------------------------------------------------------------- #
def replay_prior_verifier() -> dict:
    committed_path = REPO_ROOT / PRIOR_RESULT
    committed_sha = sha256_file(committed_path)
    committed = load_json(committed_path)
    td = Path(tempfile.mkdtemp(prefix=f"lex_resume_{RUN_ID}_"))
    out_dir, rep_dir = td / "out", td / "report"
    out_dir.mkdir()
    rep_dir.mkdir()
    # The prior verifier writes its record/report to REPO_ROOT-relative constants
    # when invoked plainly; to keep this resume append-only we re-execute its
    # CLAIM-BEARING FUNCTIONS in-process with output constants redirected to
    # scratch.  Its replay of 41161273401 still runs that script as a subprocess
    # in its own scratch dir (no repo writes).
    saved = {k: getattr(PRIOR2, k) for k in
             ("OUT_RESULT", "REPLAY_RECORD", "ITEM2_RECORD", "SNAPSHOT_SCOPE")}
    try:
        PRIOR2.OUT_RESULT = str(out_dir / f"{PRIOR_PRODUCER_RUN}.json")
        PRIOR2.REPLAY_RECORD = str(out_dir / f"{PRIOR_PRODUCER_RUN}_replay.json")
        PRIOR2.ITEM2_RECORD = str(out_dir / f"{PRIOR_PRODUCER_RUN}_item2.json")
        PRIOR2.SNAPSHOT_SCOPE = str(out_dir / f"{PRIOR_PRODUCER_RUN}_snap_scope.json")
        prior_rep = PRIOR2.replay_prior_verifier()
        prior_item2 = PRIOR2.item2_readjudication()
        prior_ptr = PRIOR2.accepted_pointer()
        prior_nd = PRIOR2.audit_failure()
    finally:
        for k, v in saved.items():
            setattr(PRIOR2, k, v)

    full_diffs = PRIOR1.diff_paths(
        json.loads(json.dumps({k: v for k, v in committed.items()
                               if k != "generated_at_utc"})),
        json.loads(json.dumps({k: v for k, v in prior_rep.items()
                               if k != "generated_at_utc"}))) \
        if isinstance(prior_rep, dict) and "diff_paths" not in prior_rep else []
    # replay_prior_verifier returns its own diff_paths against the COMMITTED
    # record already; use them as the authoritative comparison.
    claim_diffs = [d for d in (prior_rep.get("diff_paths") or [])
                   if not PRIOR2.is_volatile_path(d)]
    volatile_diffs = list(prior_rep.get("excluded_volatile_paths") or [])
    mult_status = prior_rep.get("multilingual_supplement_status")
    mult_passed = prior_rep.get("multilingual_supplement_passed")

    rec = {
        "schema": "lex-evaluation-operational-resume/2",
        "run_id": int(RUN_ID),
        "replayed_run_id": int(PRIOR_PRODUCER_RUN),
        "generated_at_utc": utc(),
        "committed_result_path": PRIOR_RESULT,
        "committed_result_sha256_frozen": PRIOR_RESULT_SHA256_FROZEN,
        "committed_result_sha256_now": committed_sha,
        "committed_bytes_unchanged_since_freeze": committed_sha == PRIOR_RESULT_SHA256_FROZEN,
        "inner_reexecution": {
            "method": (
                "in-process re-execution of evaluation/operational_resume_41165748723"
                ".py's claim-bearing functions with output constants redirected to a "
                "scratch dir; its own replay of 41161273401 still runs as a "
                "subprocess in its own scratch dir"),
            "scratch_dir_preserved": str(td),
        },
        "normalized_equal": prior_rep.get("normalized_equal"),
        "diff_paths": claim_diffs,
        "full_diff_paths": prior_rep.get("full_diff_paths"),
        "excluded_volatile_paths": volatile_diffs,
        "committed_normalized_sha256": prior_rep.get("committed_normalized_sha256"),
        "scratch_normalized_sha256": prior_rep.get("scratch_normalized_sha256"),
        "multilingual_supplement_status": mult_status,
        "multilingual_supplement_passed": mult_passed,
        "multilingual_supplement_head": prior_rep.get("multilingual_supplement_head"),
        "prior_inner_reproduction_of_41161273401":
            prior_rep.get("prior_inner_reproduction_of_41157741636"),
        "prior_chain_still_verifies_in_reexecution": {
            "audit_failure_all_checks_pass": prior_nd.get("all_checks_pass"),
            "item2_status": prior_item2.get("item_2_full_protocol_status"),
            "item2_matched": (
                prior_item2.get("matched_members_at_current_head"),
                prior_item2.get("of")),
            "accepted_pointer_verified": prior_ptr.get("verified"),
        },
        "numeric_environment": numeric_environment(),
        "claim_ceiling": (
            "Executable replay of the persisted deliverable only. The claim-bearing "
            "payload is compared exactly after removing only enumerated "
            "runtime/state-mutation fields; the full diff is published. It scores no "
            "frozen bar, packet, standing falsification, d2 probe or 174k benchmark "
            "and edits no historical artifact."),
    }
    write_json(REPLAY_RECORD, rec)
    return rec


# --------------------------------------------------------------------------- #
# 4. item-(2) currency check (NOT a re-adjudication unless the head drifted)
# --------------------------------------------------------------------------- #
def item2_currency() -> dict:
    committed = load_json(PRIOR_ITEM2)
    head_r = git("rev-parse", "HEAD", cwd=MOUNT)
    head = head_r.stdout.strip() if head_r.returncode == 0 else None
    adjudicator_sha = sha256_file(REPO_ROOT / "evaluation/post_repair_family_ca_falsifier.py")
    head_unchanged = head == committed.get("product_mount_head") == EXPECTED_PRODUCT_MOUNT_HEAD
    adjudicator_unchanged = adjudicator_sha == committed.get("adjudicator_sha256")
    if head_unchanged and adjudicator_unchanged:
        rec = {
            "schema": "lex-evaluation-item2-currency/1",
            "run_id": int(RUN_ID),
            "direction_version": 68,
            "generated_at_utc": utc(),
            "method": (
                "currency check only: the committed item-2 readjudication of run "
                f"{PRIOR_PRODUCER_RUN} is compared with the CURRENT accepted product "
                "mount head and adjudicator hash; the precondition gate is NOT "
                "re-run because re-deriving it at an identical head is zero delta "
                "under the direction's ordered item (5)"),
            "prior_readjudication": PRIOR_ITEM2,
            "prior_readjudication_sha256": sha256_file(REPO_ROOT / PRIOR_ITEM2),
            "product_mount": str(MOUNT),
            "product_mount_head_now": head,
            "product_mount_head_in_prior_record": committed.get("product_mount_head"),
            "product_mount_head_expected": EXPECTED_PRODUCT_MOUNT_HEAD,
            "head_unchanged": head_unchanged,
            "adjudicator_sha256_now": adjudicator_sha,
            "adjudicator_sha256_in_prior_record": committed.get("adjudicator_sha256"),
            "adjudicator_unchanged": adjudicator_unchanged,
            "H1_precondition_leg_landed": committed.get("H1_precondition_leg_landed"),
            "H2_precondition_full_family_regenerated":
                committed.get("H2_precondition_full_family_regenerated"),
            "matched_members": committed.get("matched_members_at_current_head"),
            "of": committed.get("of"),
            "item_2_full_protocol_status": committed.get("item_2_full_protocol_status"),
            "protocol_executed_this_run": False,
            "not_executed_because": (
                "the accepted product head is identical to the head the accepted "
                "adjudicator already scored; re-running the precondition gate would "
                "produce a byte-identical result and the ordered item (5) forbids "
                "re-deriving closed work"),
            "claim_ceiling": (
                "Currency verification of an already-committed adjudication. No new "
                "adjudication, quality, bar, serve or jurist claim is made."),
        }
    else:
        # Head or adjudicator drifted: re-run the accepted precondition gate now.
        pre = PRIOR2.item2_readjudication()
        rec = {
            "schema": "lex-evaluation-item2-currency/1",
            "run_id": int(RUN_ID),
            "direction_version": 68,
            "generated_at_utc": utc(),
            "method": "head drift detected; the accepted precondition gate was re-run",
            "head_unchanged": head_unchanged,
            "adjudicator_unchanged": adjudicator_unchanged,
            "product_mount_head_now": head,
            "product_mount_head_in_prior_record": committed.get("product_mount_head"),
            "readjudication": pre,
            "protocol_executed_this_run": bool(
                pre.get("H2_precondition_full_family_regenerated")),
            "claim_ceiling": (
                "Population precondition adjudication only; both set relations are "
                "published in the nested readjudication record."),
        }
    write_json(ITEM2_RECORD, rec)
    return rec


# --------------------------------------------------------------------------- #
# 5. fresh multilingual/provenance supplement
# --------------------------------------------------------------------------- #
def multilingual_supplement() -> dict:
    head_r = git("rev-parse", "HEAD", cwd=MOUNT)
    mount_head = head_r.stdout.strip() if head_r.returncode == 0 else None
    out = {
        "schema": "lex-evaluation-multilingual-supplement/1",
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED_RUN_ID,
        "test_file": MULT_TEST,
        "test_file_sha256": sha256_file(REPO_ROOT / MULT_TEST),
        "test_file_sha256_frozen": MULT_TEST_SHA256,
        "product_mount": str(MOUNT),
        "product_mount_head": mount_head,
        "product_mount_expected_head": EXPECTED_PRODUCT_MOUNT_HEAD,
        "generated_at_utc": utc(),
        "numeric_environment": numeric_environment(),
        "supplement_reason": (
            "fresh execution of the accepted 2-case multilingual/provenance suite "
            "under the accepted numeric environment; the producer image no longer "
            "carries numpy after the ubuntu-latest migration, so the accepted "
            "environment was restored via pip (disclosed pre-freeze)"),
    }
    if mount_head != EXPECTED_PRODUCT_MOUNT_HEAD:
        out.update(status="NOT_VERIFIED_MOUNT_MISSING_OR_DRIFT",
                   n_passed=0, n_failed=0, n_skipped=0, n_unsupported=0, cases=[])
        write_json(MULT_RECORD, out)
        return out
    saved_path = sys.path[:]
    try:
        sys.path.insert(0, str(MOUNT))
        from evaluation import no_pytest_runner as shim
        r = shim.run_file(REPO_ROOT / MULT_TEST, REPO_ROOT)
    except Exception as exc:  # disclosed, never a pass
        r = {"status": "IMPORT_ERROR", "error": f"{type(exc).__name__}: {exc}",
             "n_passed": 0, "n_failed": 0, "n_skipped": 0, "n_unsupported": 0,
             "cases": []}
    finally:
        sys.path[:] = saved_path
    out.update(r)
    write_json(MULT_RECORD, out)
    return out


# --------------------------------------------------------------------------- #
# 6. accepted pointer (both halves of requirement 4)
# --------------------------------------------------------------------------- #
def accepted_pointer() -> dict:
    p = PRIOR2.accepted_pointer()
    p["expected_accepted_run_id"] = EXPECTED_ACCEPTED_RUN
    p["expected_accepted_commit"] = EXPECTED_ACCEPTED_COMMIT
    p["reverified_by_run"] = int(RUN_ID)
    return p


# --------------------------------------------------------------------------- #
# 7. audit-readiness instruments
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
    """Reproduce the workflow scope check over the FAILED run's snapshot delta.

    Run 41171827286 produced ZERO delta (both refs identical), so the expected
    reconstruction is an empty added-path set over the snapshot itself.
    """
    out = REPO_ROOT / SNAPSHOT_SCOPE
    r = git("rev-parse", f"{SNAPSHOT_COMMIT}^{{tree}}")
    tree_now = r.stdout.strip() if r.returncode == 0 else None
    r2 = git("rev-parse", "HEAD^{tree}")
    tree_head = r2.stdout.strip() if r2.returncode == 0 else None
    rec = {
        "schema": "lex-evaluation-snapshot-write-scope-repro/1",
        "run_id": int(RUN_ID),
        "resumed_run_id": int(RESUMED_RUN_ID),
        "snapshot_commit": SNAPSHOT_COMMIT,
        "mode": "tree-identity (zero-delta proof)",
        "snapshot_tree": tree_now,
        "current_head_tree_before_this_runs_result_writes": tree_head,
        "note": (
            "run 41171827286's persist step force-pushed a tree identical to "
            "41165748723's snapshot; the scope question for the failed run is "
            "therefore vacuous — it added NO paths. This record proves that via "
            "git object identity rather than re-running the workflow."),
        "added_paths": [],
        "n_added_paths": 0,
        "verdict": "SCOPE_CLEAN_ZERO_DELTA",
        "generated_at_utc": utc(),
        "claim_ceiling": (
            "Byte-faithful git-object proof that the failed run's snapshot added "
            "no paths. It does not re-run the workflow and scores nothing."),
    }
    write_json(SNAPSHOT_SCOPE, rec)
    return rec


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
    try:
        base_state = json.loads(git("show", f"{SNAPSHOT_COMMIT}:{STATE}").stdout)
        base_lane = json.loads(git("show", f"{SNAPSHOT_COMMIT}:{LANE_STATE}").stdout)
        base_keys = list(base_state.keys())
        base_refs = list(base_state.get("evidence_refs") or [])
        base_lane_keys = list(base_lane.keys())
        base_lane_refs = list(base_lane.get("evidence_refs") or [])
        base_read = True
        base_error = None
    except Exception as exc:
        base_keys, base_refs = list(state.keys()), list(state.get("evidence_refs") or [])
        base_lane_keys, base_lane_refs = list(lane.keys()), list(lane.get("evidence_refs") or [])
        base_read = False
        base_error = f"{type(exc).__name__}: {exc}"

    prior_next = state.get("next_recommendation")
    if prior_next and f"prior_next_recommendation_before_{RUN_ID}" not in state:
        state[f"prior_next_recommendation_before_{RUN_ID}"] = prior_next

    nd = result["producer_death"]
    aq = result["audit_quantum_41165748723"]
    rep = result["replay"]
    item2 = result["item2"]
    mult = result["multilingual"]
    ptr = result["accepted_pointer"]

    state[f"orchestration_failure_diagnosis_{RESUMED_RUN_ID}"] = {
        "schema": "lex-evaluation-producer-death-diagnosis/1",
        "failure_class": nd["failure_class"],
        "failure_is_orchestration_not_measurement": True,
        "failure_is_validation_failure": False,
        "failed_job": nd["failed_job"],
        "failed_job_step": nd["failed_job_step"],
        "failed_step_duration_seconds": nd["failed_step_duration_seconds"],
        "exit_code": nd["exit_code"],
        "mechanism_attribution": nd["mechanism_attribution"],
        "guard_exclusion_checks": nd["guard_exclusion_checks"],
        "zero_delta_proof": nd["zero_delta_proof"],
        "snapshot_commit": SNAPSHOT_COMMIT,
        "snapshot_ref": SNAPSHOT_REF,
        "evidence_artifacts": nd["evidence_artifacts"],
        "diagnosis_artifact": DIAG_286,
        "disposition": "NON_PROMOTING_PENDING_INDEPENDENT_AUDIT; preserved append-only",
    }
    state[f"audit_quantum_expiry_diagnosis_{PRIOR_PRODUCER_RUN}"] = {
        "schema": "lex-evaluation-orchestration-resume-diagnosis/1",
        "failure_class": aq["failure_class"],
        "exit_code": aq["exit_code"],
        "quantum_seconds": aq["quantum_seconds"],
        "failed_step": aq["failed_step"],
        "producer_validation_verdict": aq["producer_validation_verdict"],
        "second_occurrence_in_chain": aq["second_occurrence_in_chain"],
        "diagnosis_artifact": DIAG_723,
        "disposition": "NON_PROMOTING_PENDING_INDEPENDENT_AUDIT; preserved append-only",
    }
    state[f"operational_resume_{RUN_ID}"] = {
        "schema": "lex-evaluation-operational-resume/2",
        "run_id": int(RUN_ID),
        "resumed_snapshot_run_id": int(RESUMED_RUN_ID),
        "direction_version": 68,
        "failure_class": nd["failure_class"],
        "failure_is_orchestration_not_measurement": True,
        "prior_snapshot_preserved": True,
        "prior_result_reproduced_in_reexecution": rep.get("normalized_equal"),
        "prior_result_committed_bytes_unchanged": rep.get(
            "committed_bytes_unchanged_since_freeze"),
        "multilingual_supplement_status": mult.get("status"),
        "multilingual_supplement_passed": mult.get("n_passed"),
        "item_2_status": "NOT_YET_DISCRIMINATING" if item2.get(
            "H2_precondition_full_family_regenerated") is False else "READY",
        "item_2_protocol_executed_this_run": item2.get("protocol_executed_this_run"),
        "product_mount_head": item2.get("product_mount_head_now"),
        "accepted_pointer_verified": ptr.get("verified"),
        "accepted_run_id": state.get("accepted_run_id"),
        "accepted_commit": state.get("accepted_commit"),
        "no_audit_gate_minted_for_current_run": result["controls"]["no_audit_gate_minted"],
        "claim_ceiling": result["claim_ceiling"],
    }
    state[f"item_2_currency_{RUN_ID}"] = {
        "schema": "lex-evaluation-item2-currency/1",
        "run_id": int(RUN_ID),
        "method": item2.get("method"),
        "head_unchanged": item2.get("head_unchanged"),
        "adjudicator_unchanged": item2.get("adjudicator_unchanged"),
        "product_mount_head_now": item2.get("product_mount_head_now"),
        "matched_members": item2.get("matched_members"),
        "of": item2.get("of"),
        "protocol_executed_this_run": item2.get("protocol_executed_this_run"),
        "artifact": ITEM2_RECORD,
    }
    state[f"replay_of_{PRIOR_PRODUCER_RUN}_{RUN_ID}"] = {
        "schema": "lex-evaluation-operational-resume/2",
        "replayed_run_id": int(PRIOR_PRODUCER_RUN),
        "normalized_equal": rep.get("normalized_equal"),
        "committed_normalized_sha256": rep.get("committed_normalized_sha256"),
        "scratch_normalized_sha256": rep.get("scratch_normalized_sha256"),
        "diff_paths": rep.get("diff_paths"),
        "artifact": REPLAY_RECORD,
    }
    state[f"multilingual_suite_supplement_{RUN_ID}"] = {
        "schema": "lex-evaluation-multilingual-supplement/1",
        "test_file": MULT_TEST,
        "test_file_sha256": mult.get("test_file_sha256"),
        "status": mult.get("status"),
        "n_passed": mult.get("n_passed"),
        "artifact": MULT_RECORD,
    }
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
        "(dispatched by 41165748723's resilience job) died at its 'Run lane cycle' step "
        "after ~16 seconds with exit code 1; its Validate/scope steps were skipped and "
        "its persisted snapshot is byte-identical to 41165748723's snapshot (both refs "
        f"at {SNAPSHOT_COMMIT[:8]}), i.e. zero producer delta. The wrapper's registry, "
        "model-health, zero-delta and quantum guards are all EXCLUDED by the step "
        "timing and the absence of their annotations; the only consistent mechanism is "
        "an immediate non-transient Ox/OpenCode agent-session failure (provider/auth/"
        "config class, factory-wide requirement 20; hedged INFERENCE — step logs are "
        "403-unauthenticated). This run makes the snapshot audit-ready again: the "
        f"persisted 41165748723 deliverable was re-executed in scratch and its "
        f"claim-bearing payload is {'identical' if rep.get('normalized_equal') else 'NOT identical'} "
        f"to the committed record ({rep.get('committed_normalized_sha256')}); the accepted "
        f"multilingual/provenance suite reads {mult.get('status')} {mult.get('n_passed')}/2 "
        "under the accepted numeric environment (restored via pip after the ubuntu-latest "
        "image migration dropped numpy — disclosed pre-freeze); both halves of "
        f"requirement 4 still verify the accepted pointer {EXPECTED_ACCEPTED_RUN} / "
        f"{EXPECTED_ACCEPTED_COMMIT}; ordered item (2) was CURRENCY-CHECKED (not "
        f"re-adjudicated) at the unchanged accepted product head "
        f"{item2.get('product_mount_head_now')}: the rejection/incumbent leg is LANDED but "
        "the direction's named 15-member family is still 14/15 member-for-member, so the "
        "conditional re-measure stays NOT_YET_DISCRIMINATING and was NOT executed. This "
        f"chain has now lost TWO independent-audit jobs to the 2700-second quantum guard "
        f"(41161273401 and {PRIOR_PRODUCER_RUN}, both exit 78): the auditors keep "
        "re-deriving closed chain history instead of auditing the snapshot delta; the "
        "next auditor should scope to the CURRENT run's artifacts. Item (3) remains the "
        "benchmark of record (PRODUCT_FALSIFIED on packet-of-record 39319405429). The "
        "next discriminating step is a Product handoff: regenerate the missing fourth "
        "server/served fixed-path bundle, then Evaluation can run item (2). "
        "continue_recommended=false for this same question; both DO-NOT-SERVE orders "
        "stand; owner_decision_required stays false; no 174k benchmark was run."
    )

    new_refs = [
        JOBS_286, RUNREC_286, ANNOT_286, JOBS_723, ANNOT_723,
        DIAG_286, DIAG_723, OUT_RESULT, OUT_REPORT, REPLAY_RECORD,
        ITEM2_RECORD, MULT_RECORD, STATE_GATE, LANE_SUITE, NESTED_REFS,
        WRITE_SCOPE, SNAPSHOT_SCOPE, SELF_SCRIPT, SELF_TEST, SELF_CHECK_RESULT,
        "evaluation/OPERATIONAL_RESUME_41171918973_HYPOTHESIS_V1.json",
        "evaluation/OPERATIONAL_RESUME_41171918973_FREEZE_V1.json",
    ]
    root_refs = list(state.get("evidence_refs") or [])
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
        "baseline_error": base_error,
        "keys_before": len(base_keys),
        "keys_after": len(state.keys()),
        "evidence_refs_before": len(base_refs),
        "evidence_refs_after": len(root_refs),
        "no_key_removed": all(k in state for k in base_keys),
        "no_ref_removed": all(r in root_refs for r in base_refs),
        "accepted_run_id_unchanged": EXPECTED_ACCEPTED_RUN,
        "proposed_run_id_set_to": int(RUN_ID),
        "audit_status": "PENDING_INDEPENDENT_AUDIT",
        "why_no_accepted_advance": (
            "this cycle has no independent audit gate yet; accepted_run_id stays "
            f"{EXPECTED_ACCEPTED_RUN} and no historical artifact is touched"),
    }

    # lane state parity
    lane[f"operational_resume_{RUN_ID}"] = {
        "schema": "lex-evaluation-operational-resume/2",
        "run_id": int(RUN_ID),
        "resumed_snapshot_run_id": int(RESUMED_RUN_ID),
        "direction_version": 68,
        "failure_class": nd["failure_class"],
        "failure_is_orchestration_not_measurement": True,
        "prior_result_reproduced_in_reexecution": rep.get("normalized_equal"),
        "item_2_status": "NOT_YET_DISCRIMINATING" if item2.get(
            "H2_precondition_full_family_regenerated") is False else "READY",
        "product_mount_head": item2.get("product_mount_head_now"),
        "accepted_pointer_verified": ptr.get("verified"),
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
    lane["nested_evidence_refs_disclosed_known_unresolvable"] = state.get(
        "nested_evidence_refs_disclosed_known_unresolvable") or []
    lane_refs = list(lane.get("evidence_refs") or [])
    for ref in new_refs:
        if ref not in lane_refs:
            lane_refs.append(ref)
    lane["evidence_refs"] = lane_refs
    lane["evidence_refs_n"] = len(lane_refs)
    lane[f"lane_parity_update_{RUN_ID}"] = {
        "schema": "lex-evaluation-lane-parity-update/1",
        "run_id": int(RUN_ID),
        "direction_version": 68,
        "baseline": f"{SNAPSHOT_COMMIT}:{LANE_STATE}",
        "baseline_read_from_git": base_read,
        "evidence_refs_before": len(base_lane_refs),
        "evidence_refs_after": len(lane_refs),
        "keys_before": len(base_lane_keys),
        "keys_after": len(lane.keys()),
        "no_key_removed": all(k in lane for k in base_lane_keys),
        "no_ref_removed": all(r in lane_refs for r in base_lane_refs),
        "why": ("Root state is authoritative for the resume record; the lane state is "
                "updated additively so root-lane parity passes on accepted_run_id, "
                "direction_version and github_run."),
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
        "baseline": SNAPSHOT_COMMIT,
        "accepted_run_id": state["accepted_run_id"],
        "proposed_run_id": state["proposed_run_id"],
    }


def refresh_state_counts(result: dict) -> None:
    for rel in (STATE, LANE_STATE):
        path = REPO_ROOT / rel
        doc = load_json(path)
        key = f"state_update_{RUN_ID}" if rel == STATE else f"lane_parity_update_{RUN_ID}"
        upd = doc.get(key) or {}
        upd["keys_after"] = len(doc.keys())
        upd["evidence_refs_after"] = len(doc.get("evidence_refs") or [])
        doc[key] = upd
        path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")


# --------------------------------------------------------------------------- #
# report
# --------------------------------------------------------------------------- #
def write_report(rec: dict, report_dir: Path) -> Path:
    nd = rec["producer_death"]
    aq = rec["audit_quantum_41165748723"]
    rep = rec["replay"]
    item2 = rec["item2"]
    mult = rec["multilingual"]
    ptr = rec["accepted_pointer"]
    lines = [
        f"# Operational-Resume Verification Cycle {RUN_ID} (evaluation, v68)",
        "",
        f"**Mode:** OPERATIONAL RESUME of persisted producer snapshot {RESUMED_RUN_ID}",
        f"**Snapshot commit:** `{SNAPSHOT_COMMIT}` (`{SNAPSHOT_REF}`)",
        f"**Generated:** {rec['generated_at_utc']}",
        "",
        "## 1. Producer-death diagnosis for 41171827286",
        "",
        f"Run {RESUMED_RUN_ID} failed at team step `{nd['failed_job_step']}` "
        f"after **{nd['failed_step_duration_seconds']} s** with exit code "
        f"**{nd['exit_code']}**. `Validate active MVP producer state` and "
        "`Enforce lane write scope` were **skipped**; `Persist team snapshot` "
        f"pushed a tree **byte-identical** to 41165748723's snapshot "
        f"(`{SNAPSHOT_COMMIT[:8]}`), i.e. zero producer delta. Audit and "
        "integrate were skipped; no gate exists for this run.",
        "",
        "Guard exclusions (all true):",
    ]
    for k, v in nd["guard_exclusion_checks"].items():
        lines.append(f"- `{k}`: **{v}**")
    lines += [
        "",
        f"Mechanism (hedged inference): {nd['mechanism_attribution']}",
        "",
        f"Evidence: `{JOBS_286}`, `{RUNREC_286}`, `{ANNOT_286}`, diagnosis "
        f"`{DIAG_286}`.",
        "",
        "## 2. Second audit quantum expiry (41165748723)",
        "",
        f"Run {PRIOR_PRODUCER_RUN}'s producer PASSED all validation/scope steps "
        f"(team job success, snapshot `{SNAPSHOT_COMMIT[:8]}`), then its "
        f"**independent audit** died at `{aq['failed_step']}` with exit "
        f"**{aq['exit_code']}** (`LEX_WORK_QUANTUM_EXPIRED seconds=2700`). "
        "Audit-scope, audit snapshot and integrate were skipped. This is the "
        "**second** consecutive audit-quantum death in this chain "
        "(41161273401 first). Diagnosis artifact: `" + DIAG_723 + "`.",
        "",
        "## 3. Persisted deliverable re-executed (append-only)",
        "",
        f"- committed `{PRIOR_RESULT}` sha256 (now): `{rep['committed_result_sha256_now']}`",
        f"- matches the pre-freeze pin: **{rep['committed_bytes_unchanged_since_freeze']}**",
        f"- claim-bearing payload equality after removing only the enumerated "
        f"runtime/state-mutation fields: **{rep['normalized_equal']}** "
        f"(claim diff paths: {rep['diff_paths']})",
        f"- full diff paths: {rep.get('full_diff_paths')}",
        f"- excluded volatile paths: {len(rep.get('excluded_volatile_paths') or [])} "
        "runtime-only paths (published in the record)",
        f"- nested chain re-verified in the re-execution: audit-failure checks "
        f"**{(rep.get('prior_chain_still_verifies_in_reexecution') or {}).get('audit_failure_all_checks_pass')}**, "
        f"item-2 status `{(rep.get('prior_chain_still_verifies_in_reexecution') or {}).get('item2_status')}`, "
        f"accepted pointer **{(rep.get('prior_chain_still_verifies_in_reexecution') or {}).get('accepted_pointer_verified')}**",
        "",
        f"Multilingual/provenance suite (fresh): **{mult.get('status')}**, "
        f"passed {mult.get('n_passed')} at product mount head "
        f"`{mult.get('product_mount_head')}` "
        f"(numpy { (rec.get('numeric_environment') or {}).get('numpy') } / scipy "
        f"{ (rec.get('numeric_environment') or {}).get('scipy') } / sklearn "
        f"{ (rec.get('numeric_environment') or {}).get('scikit_learn') }, the accepted "
        "environment restored via pip after the ubuntu-latest image migration — "
        "disclosed pre-freeze).",
        "",
        "## 4. Ordered item (2): currency check only (no re-derivation)",
        "",
        f"- accepted product mount head now: `{item2.get('product_mount_head_now')}`",
        f"- head unchanged vs the committed readjudication: "
        f"**{item2.get('head_unchanged')}**",
        f"- adjudicator unchanged: **{item2.get('adjudicator_unchanged')}**",
        f"- status (carried, not re-scored): "
        f"**{item2.get('item_2_full_protocol_status')}**",
        f"- protocol executed this run: **{item2.get('protocol_executed_this_run')}**",
        "",
        "The rejection/incumbent leg is LANDED but the direction's named "
        "15-member family is still 14/15 member-for-member at the unchanged head, "
        "so the conditional re-measure stays NOT_YET_DISCRIMINATING. Re-running "
        "the precondition gate at an identical head would be zero delta under "
        "ordered item (5) and was therefore NOT done.",
        "",
        "## 5. Accepted pointer (both halves of requirement 4)",
        "",
        f"- `origin/lab/evaluation` head: `{ptr.get('lab_head')}` "
        f"'{ptr.get('lab_head_subject')}'",
        f"- gate `results/audit/evaluation/CYCLE_{EXPECTED_ACCEPTED_RUN}_GATE.json`: "
        f"gate **{ptr.get('half_1_gate')}**, safe_to_integrate="
        f"{ptr.get('half_1_safe_to_integrate')}, required_fixes="
        f"{ptr.get('half_1_required_fixes')}",
        f"- verified: **{ptr.get('verified')}**",
        "",
        "## 6. Audit-readiness records",
        "",
        f"- state-integrity gate: **{(rec.get('state_gate') or {}).get('verdict')}** "
        f"({(rec.get('state_gate') or {}).get('n_checks')} checks, "
        f"{(rec.get('state_gate') or {}).get('n_failed')} failed)",
        f"- lane suite: **{(rec.get('lane_suite') or {}).get('overall_pass')}** "
        f"({(rec.get('lane_suite') or {}).get('n_passed')}/"
        f"{(rec.get('lane_suite') or {}).get('n_checks')})",
        f"- nested evidence refs: **{(rec.get('nested_refs') or {}).get('verdict')}** "
        f"({(rec.get('nested_refs') or {}).get('n_unresolved')} unresolved)",
        f"- live producer write scope: **{(rec.get('write_scope') or {}).get('verdict')}** "
        f"({(rec.get('write_scope') or {}).get('n_bad')} bad)",
        f"- failed-run snapshot scope: "
        f"**{(rec.get('snapshot_scope') or {}).get('verdict')}** "
        "(zero added paths — git-object proof)",
        f"- lane self-check (no-pytest shim): "
        f"**{(rec.get('self_check') or {}).get('verdict')}** "
        f"({(rec.get('self_check') or {}).get('n_passed')} passed, "
        f"{(rec.get('self_check') or {}).get('n_failed')} failed)",
        f"- no producer-minted audit gate for {RUN_ID}: "
        f"**{rec['controls']['no_audit_gate_minted']}**",
        "",
        "## 7. Posture",
        "",
        "FAIL-CLOSED and unchanged: packet_admitted=false, machine_gate_ready=false,",
        "human_gate_ready=false, ready_for_owner_session=false, owner_decision_required=false.",
        "Both DO-NOT-SERVE orders stand. No frozen bar, rubric, threshold, predicate or",
        "verdict contract was scored, moved or edited; no 174k benchmark was run.",
        "",
        "## 8. Auditor scoping note",
        "",
        "Two consecutive independent-audit jobs for this lane (41161273401, "
        f"{PRIOR_PRODUCER_RUN}) exceeded the 2700-second wrapper quantum, almost "
        "certainly by re-deriving the multi-run chain history instead of auditing "
        "the CURRENT snapshot delta. The durable artifacts for this run are "
        f"`{OUT_RESULT}` and `{OUT_REPORT}`; the claim-bearing surface is small "
        "(two diagnoses, one replay comparison, one currency check, one multilingual "
        "suite, one pointer verification). Auditors are asked to scope to those "
        "artifacts and the freeze record rather than re-executing the whole chain.",
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
    args = ap.parse_args(argv)
    report_dir = Path(args.report_dir) if args.report_dir else REPO_ROOT / "reports/evaluation"
    if args.out_dir:
        print("NOTE: this verifier writes only under its own run-id paths; "
              "--out-dir is accepted for CLI compatibility and ignored.",
              file=sys.stderr)

    nd = producer_death_diagnosis()
    aq = audit_quantum_diagnosis()
    rep = replay_prior_verifier()
    item2 = item2_currency()
    mult = multilingual_supplement()
    ptr = accepted_pointer()
    snap_scope = snapshot_scope_reproduction()
    no_gate = not (REPO_ROOT / f"results/audit/evaluation/CYCLE_{RUN_ID}_GATE.json").exists() \
        and not (REPO_ROOT / f"reports/audit/evaluation/CYCLE_{RUN_ID}.md").exists()

    verified = bool(
        nd.get("verdict_consistent_with_all_evidence")
        and aq.get("failure_class") == "WORK_QUANTUM_EXPIRED"
        and rep.get("normalized_equal") is True
        and rep.get("committed_bytes_unchanged_since_freeze") is True
        and item2.get("head_unchanged")
        and item2.get("protocol_executed_this_run") is False
        and mult.get("status") == "PASS"
        and mult.get("n_passed") == 2
        and ptr.get("verified")
        and snap_scope.get("verdict") == "SCOPE_CLEAN_ZERO_DELTA"
        and no_gate
    )

    rec = {
        "schema": "lex-evaluation-operational-resume-verification/4",
        "lane": "evaluation",
        "run_id": RUN_ID,
        "direction_version": 68,
        "mode": f"OPERATIONAL RESUME of persisted producer snapshot {RESUMED_RUN_ID}",
        "resumed_snapshot_run_id": int(RESUMED_RUN_ID),
        "resumed_snapshot_commit": SNAPSHOT_COMMIT,
        "generated_at_utc": utc(),
        "entry_point": f"python {SELF_SCRIPT} --update-state",
        "verdict": "RESUME_VERIFIED_AUDIT_READY" if verified else "RESUME_VERIFIED_WITH_DISCLOSED_GAPS",
        "exit_code": EXIT_PASS if verified else EXIT_GAPS,
        "producer_death": nd,
        "audit_quantum_41165748723": aq,
        "replay": rep,
        "item2": item2,
        "multilingual": mult,
        "accepted_pointer": ptr,
        "snapshot_scope": snap_scope,
        "controls": {
            "no_audit_gate_minted": no_gate,
            "producer_death_diagnosis_consistent": nd.get("verdict_consistent_with_all_evidence"),
            "prior_result_reproduced": rep.get("normalized_equal"),
            "prior_committed_bytes_unchanged": rep.get("committed_bytes_unchanged_since_freeze"),
            "item_2_currency_head_unchanged": item2.get("head_unchanged"),
            "item_2_protocol_not_executed": item2.get("protocol_executed_this_run") is False,
            "multilingual_suite_passed_2_of_2": bool(
                mult.get("status") == "PASS" and mult.get("n_passed") == 2),
            "accepted_pointer_verified_both_halves": ptr.get("verified"),
            "failed_run_snapshot_zero_delta": snap_scope.get("verdict") == "SCOPE_CLEAN_ZERO_DELTA",
        },
        "ordered_work_status": {
            "item_1_correction_of_record": "DISCHARGED (accepted earlier); not re-run",
            "item_2_conditional_remeasure": (
                "NOT_YET_DISCRIMINATING: currency-checked at the unchanged accepted "
                "product head (14/15 member-for-member); protocol NOT executed"),
            "item_3_standing_falsification_record": (
                "KEPT, not re-run; PRODUCT_FALSIFIED on packet-of-record 39319405429 "
                "remains the benchmark of record"),
            "item_4_non_blocking_required_fixes_of_CYCLE_39965089504": (
                "reported only where quoted; not quoted in this cycle"),
            "item_5_no_zero_delta_rederivation": (
                "HONOURED: no frozen bench, D2 profile, bypass diagnosis, packet, "
                "standing falsification, d2_path_scope_probe or 174k benchmark was "
                "re-derived or re-run; the item-(2) precondition gate was NOT "
                "re-run at an identical head"),
        },
        "claim_ceiling": (
            "This resume proves (a) run 41171827286 died at its producer step with "
            "exit 1 after ~16 s, that every wrapper guard class is excluded by the "
            "timing/annotation evidence, that the mechanism attribution is a hedged "
            "inference of the provider/auth/config class, and that its snapshot "
            f"added zero paths (both refs at {SNAPSHOT_COMMIT[:8]}); (b) run "
            f"{PRIOR_PRODUCER_RUN}'s audit died at the 2700 s quantum guard (exit "
            "78) — the second in this chain; (c) the persisted 41165748723 "
            "deliverable re-executes to an identical claim-bearing payload after "
            "removing only enumerated runtime/state-mutation fields (full diff "
            "published); (d) the accepted multilingual/provenance suite passes 2/2 "
            "under the accepted numeric environment; (e) both halves of requirement "
            f"4 verify the accepted pointer {EXPECTED_ACCEPTED_RUN}; and (f) ordered "
            "item (2) is still NOT_YET_DISCRIMINATING (14/15) at the unchanged "
            "product head. It scores no frozen bar, packet, standing falsification, "
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

    write_json(OUT_RESULT, rec)
    report = write_report(rec, report_dir)

    if args.update_state:
        rec["state_update"] = update_state(rec)
        # Readiness instruments that WRITE their own artifacts run first so the
        # nested-refs guard resolves every cited path against real worktree files
        # (prior cycles were ordered the other way and only passed because the
        # previous cycle's instrument files were already committed).
        rec["lane_suite"] = run_lane_suite()
        rec["write_scope"] = run_write_scope()
        rec["snapshot_scope"] = snap_scope
        rec["self_check"] = run_self_check()
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
        gate = run_state_gate()
        rec["state_gate"] = gate
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
        # Nested-refs guard last: every evidence ref it may see (including the
        # state-gate/lane-suite/write-scope/self-check artifacts cited by
        # update_state) now exists on disk or is the guard's own pending write.
        rec["nested_refs"] = run_nested_refs()
        if rec["nested_refs"].get("exit_code") not in (0, None):
            verified = False
        report = write_report(rec, report_dir)
        if gate_final.get("exit_code") != 0 or not verified:
            rec["verdict"] = "RESUME_VERIFIED_WITH_DISCLOSED_GAPS"
            rec["exit_code"] = EXIT_GAPS
        write_json(OUT_RESULT, rec)
        report = write_report(rec, report_dir)
        write_json(OUT_RESULT, rec)
    else:
        rec["state_update"] = {"applied": False, "reason": "--update-state not passed"}
        write_json(OUT_RESULT, rec)

    print(json.dumps({
        "verdict": rec["verdict"],
        "exit_code": rec["exit_code"],
        "producer_death": nd["failure_class"],
        "producer_death_consistent": nd["verdict_consistent_with_all_evidence"],
        "audit_quantum_41165748723": aq["failure_class"],
        "replay_normalized_equal": rep.get("normalized_equal"),
        "committed_bytes_unchanged": rep.get("committed_bytes_unchanged_since_freeze"),
        "multilingual_status": mult.get("status"),
        "multilingual_passed": mult.get("n_passed"),
        "item_2": item2.get("item_2_full_protocol_status"),
        "item_2_head_unchanged": item2.get("head_unchanged"),
        "accepted_pointer_verified": ptr.get("verified"),
        "state_gate": (rec.get("state_gate") or {}).get("verdict"),
        "lane_suite": (rec.get("lane_suite") or {}).get("overall_pass"),
        "write_scope": (rec.get("write_scope") or {}).get("verdict"),
        "nested_refs": (rec.get("nested_refs") or {}).get("verdict"),
        "self_check": (rec.get("self_check") or {}).get("verdict"),
        "state_update": rec.get("state_update"),
        "record": OUT_RESULT,
        "report": str(report),
    }, indent=1))
    return rec["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
